"""
交易执行引擎
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
import logging
import time
import threading

from .risk_manager import RiskManager
from .position_manager import PositionManager
from .order_manager import OrderManager
from .broker_adapter import BrokerAdapterFactory

logger = logging.getLogger(__name__)


class ExecutionEngine:
    """交易执行引擎"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.running = False

        # 初始化组件
        self.risk_manager = RiskManager(config)
        self.position_manager = PositionManager(config)
        self.order_manager = OrderManager(config)

        # 券商适配器
        self.broker_adapter = BrokerAdapterFactory.create_adapter(config)

        # 执行状态
        self.execution_state = {
            "last_update": None,
            "total_trades": 0,
            "successful_trades": 0,
            "failed_trades": 0,
            "current_capital": 0,
            "current_positions": {},
        }

        # 信号队列
        self.signal_queue = []

        # 执行线程
        self.execution_thread = None

    def start(self) -> bool:
        """
        启动执行引擎

        Returns
        -------
        bool
            是否启动成功
        """
        if self.running:
            logger.warning("执行引擎已在运行")
            return False

        # 连接券商
        if not self.broker_adapter.connect():
            logger.error("券商连接失败")
            return False

        # 启动执行线程
        self.running = True
        self.execution_thread = threading.Thread(target=self._execution_loop, daemon=True)
        self.execution_thread.start()

        logger.info("交易执行引擎已启动")
        return True

    def stop(self):
        """停止执行引擎"""
        self.running = False

        if self.execution_thread and self.execution_thread.is_alive():
            self.execution_thread.join(timeout=5)

        self.broker_adapter.disconnect()
        logger.info("交易执行引擎已停止")

    def add_signal(self, signal: Dict[str, Any]):
        """
        添加交易信号

        Parameters
        ----------
        signal : Dict[str, Any]
            交易信号
        """
        required_fields = ["symbol", "action", "confidence", "strategy"]
        for field in required_fields:
            if field not in signal:
                logger.error(f"信号缺少必要字段: {field}")
                return

        # 添加时间戳
        signal["timestamp"] = datetime.now()
        signal["signal_id"] = f"SIG_{datetime.now().strftime('%Y%m%d%H%M%S%f')}"

        self.signal_queue.append(signal)
        logger.info(f"交易信号添加: {signal['symbol']} {signal['action']} (置信度: {signal['confidence']})")

    def process_signal(self, signal: Dict[str, Any]) -> bool:
        """
        处理交易信号

        Parameters
        ----------
        signal : Dict[str, Any]
            交易信号

        Returns
        -------
        bool
            是否成功处理
        """
        symbol = signal["symbol"]
        action = signal["action"]
        confidence = signal.get("confidence", 0.5)

        # 检查交易时间
        if not self.broker_adapter.is_trading_time():
            logger.warning(f"非交易时间，跳过信号: {symbol}")
            return False

        # 获取账户信息
        account_info = self.broker_adapter.get_account_info()
        if not account_info:
            logger.error("获取账户信息失败")
            return False

        current_capital = account_info.get("available_cash", 0)
        total_asset = account_info.get("total_asset", 0)

        # 获取当前持仓
        positions = self.broker_adapter.get_positions()
        current_positions = {}
        for pos in positions:
            current_positions[pos["symbol"]] = {
                "size": pos["size"],
                "value": pos.get("market_value", pos["size"] * pos.get("market_price", 0)),
                "avg_price": pos.get("cost_price", 0),
            }

        # 获取市场数据
        market_data = self.broker_adapter.get_market_data(
            [symbol], ["last_price", "bid1", "ask1", "volume"]
        )

        if symbol not in market_data:
            logger.error(f"获取市场数据失败: {symbol}")
            return False

        price_data = market_data[symbol]
        current_price = price_data.get("last_price", 0)

        if current_price <= 0:
            logger.error(f"无效价格: {symbol} {current_price}")
            return False

        # 计算建议仓位
        # 这里简化处理，使用固定比例
        position_ratio = 0.05  # 单笔仓位5%
        target_value = total_asset * position_ratio * confidence

        # 如果是卖出信号，检查持仓
        if action == "sell":
            position = current_positions.get(symbol, {"size": 0})
            if position["size"] == 0:
                logger.warning(f"无持仓可卖: {symbol}")
                return False

            # 卖出全部持仓
            size = position["size"]
        else:
            # 买入信号
            size = int(target_value / current_price)

            # A股最小交易单位
            size = (size // 100) * 100
            size = max(size, 100)

        # 风险检查
        risk_check, risk_reason = self.risk_manager.check_position_risk(
            symbol, size, current_price, current_positions, total_asset
        )

        if not risk_check:
            logger.warning(f"风险检查失败: {symbol}, 原因: {risk_reason}")
            return False

        # 创建订单
        order = self.order_manager.create_order(
            symbol=symbol,
            action=action,
            size=size,
            price_type="limit",
            limit_price=current_price,
            reason=f"signal_{signal['strategy']}",
            confidence=confidence,
            signal_id=signal["signal_id"],
        )

        # 提交订单
        success = self.order_manager.submit_order(order["order_id"], self.broker_adapter)

        if success:
            logger.info(f"信号处理成功: {symbol} {action} {size}股")
            self.execution_state["successful_trades"] += 1
        else:
            logger.error(f"信号处理失败: {symbol}")
            self.execution_state["failed_trades"] += 1

        self.execution_state["total_trades"] += 1
        return success

    def execute_order(self, order_params: Dict[str, Any]) -> Dict[str, Any]:
        """
        直接执行订单

        Parameters
        ----------
        order_params : Dict[str, Any]
            订单参数

        Returns
        -------
        Dict[str, Any]
            执行结果
        """
        required_fields = ["symbol", "action", "size"]
        for field in required_fields:
            if field not in order_params:
                return {"success": False, "error": f"缺少必要字段: {field}"}

        symbol = order_params["symbol"]
        action = order_params["action"]

        # 检查交易时间
        if not self.broker_adapter.is_trading_time():
            return {"success": False, "error": "非交易时间"}

        # 获取市场数据
        market_data = self.broker_adapter.get_market_data(
            [symbol], ["last_price", "bid1", "ask1"]
        )

        if symbol not in market_data:
            return {"success": False, "error": "获取市场数据失败"}

        price_data = market_data[symbol]
        current_price = price_data.get("last_price", 0)

        if current_price <= 0:
            return {"success": False, "error": "无效价格"}

        # 创建订单
        order = self.order_manager.create_order(
            symbol=symbol,
            action=action,
            size=order_params["size"],
            price_type=order_params.get("price_type", "limit"),
            limit_price=order_params.get("limit_price", current_price),
            reason=order_params.get("reason", "manual"),
        )

        # 提交订单
        success = self.order_manager.submit_order(order["order_id"], self.broker_adapter)

        result = {
            "success": success,
            "order_id": order["order_id"],
            "symbol": symbol,
            "action": action,
            "size": order_params["size"],
            "price": current_price,
        }

        if not success:
            result["error"] = "订单提交失败"

        return result

    def get_execution_status(self) -> Dict[str, Any]:
        """
        获取执行状态

        Returns
        -------
        Dict[str, Any]
            执行状态
        """
        # 更新状态
        account_info = self.broker_adapter.get_account_info()
        positions = self.broker_adapter.get_positions()

        self.execution_state.update({
            "last_update": datetime.now(),
            "current_capital": account_info.get("available_cash", 0),
            "total_asset": account_info.get("total_asset", 0),
            "current_positions": positions,
            "signal_queue_size": len(self.signal_queue),
            "pending_orders": len(self.order_manager.get_pending_orders()),
        })

        return self.execution_state.copy()

    def get_performance_report(self) -> Dict[str, Any]:
        """
        获取绩效报告

        Returns
        -------
        Dict[str, Any]
            绩效报告
        """
        # 获取订单摘要
        order_summary = self.order_manager.get_order_summary()

        # 获取风险报告
        risk_report = self.risk_manager.get_risk_report()

        # 计算总体绩效
        account_info = self.broker_adapter.get_account_info()
        total_asset = account_info.get("total_asset", 0)

        # 这里可以添加更复杂的绩效计算
        performance = {
            "total_asset": total_asset,
            "available_cash": account_info.get("available_cash", 0),
            "market_value": account_info.get("market_value", 0),
            "total_profit": account_info.get("total_profit", 0),
            "order_summary": order_summary,
            "risk_report": risk_report,
            "execution_stats": {
                "total_trades": self.execution_state["total_trades"],
                "successful_trades": self.execution_state["successful_trades"],
                "failed_trades": self.execution_state["failed_trades"],
                "success_rate": self.execution_state["successful_trades"] / max(self.execution_state["total_trades"], 1),
            },
        }

        return performance

    def _execution_loop(self):
        """执行循环"""
        logger.info("执行循环开始")

        while self.running:
            try:
                # 检查并处理过期订单
                self.order_manager.check_order_validity()

                # 处理信号队列
                if self.signal_queue:
                    signal = self.signal_queue.pop(0)
                    self.process_signal(signal)

                # 更新执行状态
                self._update_execution_state()

                # 休眠一段时间
                time.sleep(1)  # 1秒间隔

            except Exception as e:
                logger.error(f"执行循环异常: {e}")
                time.sleep(5)  # 异常后稍长休眠

        logger.info("执行循环结束")

    def _update_execution_state(self):
        """更新执行状态"""
        # 这里可以添加定期状态更新逻辑
        pass

    def save_state(self, filepath: str):
        """保存引擎状态"""
        import pickle

        state = {
            "execution_state": self.execution_state,
            "signal_queue": self.signal_queue,
            "timestamp": datetime.now(),
        }

        # 保存子组件状态
        self.order_manager.save_state(filepath + ".orders")
        # 可以添加其他组件的状态保存

        with open(filepath, "wb") as f:
            pickle.dump(state, f)

        logger.info(f"执行引擎状态已保存: {filepath}")

    def load_state(self, filepath: str):
        """加载引擎状态"""
        import pickle

        try:
            with open(filepath, "rb") as f:
                state = pickle.load(f)

            self.execution_state = state.get("execution_state", self.execution_state)
            self.signal_queue = state.get("signal_queue", [])

            # 加载子组件状态
            self.order_manager.load_state(filepath + ".orders")

            logger.info(f"执行引擎状态已加载: {filepath}")
        except Exception as e:
            logger.error(f"加载执行引擎状态失败: {e}")