"""
仓位管理模块
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
import logging

logger = logging.getLogger(__name__)


class PositionManager:
    """仓位管理器"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.positions = {}  # symbol -> position info
        self.position_history = []

    def update_position(
        self,
        symbol: str,
        action: str,
        size: int,
        price: float,
        transaction_id: str
    ) -> Dict[str, Any]:
        """
        更新仓位

        Parameters
        ----------
        symbol : str
            股票代码
        action : str
            操作: 'buy', 'sell'
        size : int
            数量
        price : float
            价格
        transaction_id : str
            交易ID

        Returns
        -------
        Dict[str, Any]
            更新后的仓位信息
        """
        current_position = self.positions.get(symbol, {
            "symbol": symbol,
            "size": 0,
            "avg_price": 0,
            "market_value": 0,
            "pnl": 0,
            "pnl_percent": 0,
            "entry_date": None,
            "last_update": datetime.now(),
        })

        if action == "buy":
            # 买入更新
            new_size = current_position["size"] + size
            if new_size > 0:
                # 计算新的平均价格
                total_cost = current_position["size"] * current_position["avg_price"] + size * price
                new_avg_price = total_cost / new_size

                current_position.update({
                    "size": new_size,
                    "avg_price": new_avg_price,
                    "market_value": new_size * price,
                    "last_update": datetime.now(),
                })

                # 如果是新开仓，记录入场日期
                if current_position["size"] == size:
                    current_position["entry_date"] = datetime.now()

        elif action == "sell":
            # 卖出更新
            if current_position["size"] < size:
                logger.error(f"卖出数量超过持仓: {symbol}, 持仓={current_position['size']}, 卖出={size}")
                return current_position

            new_size = current_position["size"] - size

            # 计算盈亏
            pnl = size * (price - current_position["avg_price"])
            pnl_percent = (price - current_position["avg_price"]) / current_position["avg_price"] * 100

            current_position.update({
                "size": new_size,
                "market_value": new_size * price,
                "last_update": datetime.now(),
            })

            # 记录交易历史
            trade_record = {
                "timestamp": datetime.now(),
                "symbol": symbol,
                "action": action,
                "size": size,
                "price": price,
                "avg_cost": current_position["avg_price"],
                "pnl": pnl,
                "pnl_percent": pnl_percent,
                "transaction_id": transaction_id,
            }
            self.position_history.append(trade_record)

            # 如果仓位为0，清除平均价格
            if new_size == 0:
                current_position["avg_price"] = 0
                current_position["entry_date"] = None

        # 更新市值和盈亏
        current_position["market_value"] = current_position["size"] * price
        if current_position["avg_price"] > 0:
            current_position["pnl"] = current_position["size"] * (price - current_position["avg_price"])
            current_position["pnl_percent"] = (price - current_position["avg_price"]) / current_position["avg_price"] * 100

        # 保存更新
        self.positions[symbol] = current_position

        logger.info(
            f"仓位更新: {symbol}, "
            f"操作={action}, "
            f"数量={size}, "
            f"价格={price:.2f}, "
            f"持仓={current_position['size']}, "
            f"均价={current_position['avg_price']:.2f}"
        )

        return current_position

    def get_position(self, symbol: str) -> Dict[str, Any]:
        """
        获取仓位信息

        Parameters
        ----------
        symbol : str
            股票代码

        Returns
        -------
        Dict[str, Any]
            仓位信息
        """
        return self.positions.get(symbol, {
            "symbol": symbol,
            "size": 0,
            "avg_price": 0,
            "market_value": 0,
            "pnl": 0,
            "pnl_percent": 0,
            "entry_date": None,
            "last_update": None,
        })

    def get_all_positions(self) -> Dict[str, Dict[str, Any]]:
        """
        获取所有仓位

        Returns
        -------
        Dict[str, Dict[str, Any]]
            所有仓位信息
        """
        return self.positions.copy()

    def calculate_portfolio_value(self, current_prices: Dict[str, float]) -> float:
        """
        计算组合价值

        Parameters
        ----------
        current_prices : Dict[str, float]
            当前价格字典

        Returns
        -------
        float
            组合总价值
        """
        total_value = 0

        for symbol, position in self.positions.items():
            if position["size"] > 0:
                current_price = current_prices.get(symbol, position["avg_price"])
                position_value = position["size"] * current_price
                total_value += position_value

                # 更新市值
                self.positions[symbol]["market_value"] = position_value

        return total_value

    def calculate_portfolio_pnl(self, current_prices: Dict[str, float]) -> Dict[str, Any]:
        """
        计算组合盈亏

        Parameters
        ----------
        current_prices : Dict[str, float]
            当前价格字典

        Returns
        -------
        Dict[str, Any]
            组合盈亏统计
        """
        total_pnl = 0
        total_cost = 0
        total_market_value = 0

        for symbol, position in self.positions.items():
            if position["size"] > 0:
                current_price = current_prices.get(symbol, position["avg_price"])
                position_pnl = position["size"] * (current_price - position["avg_price"])
                position_cost = position["size"] * position["avg_price"]
                position_value = position["size"] * current_price

                total_pnl += position_pnl
                total_cost += position_cost
                total_market_value += position_value

        pnl_percent = total_pnl / total_cost * 100 if total_cost > 0 else 0

        return {
            "total_pnl": total_pnl,
            "total_cost": total_cost,
            "total_market_value": total_market_value,
            "pnl_percent": pnl_percent,
        }

    def get_position_summary(self) -> pd.DataFrame:
        """
        获取仓位摘要

        Returns
        -------
        pd.DataFrame
            仓位摘要
        """
        if not self.positions:
            return pd.DataFrame()

        summary_data = []

        for symbol, position in self.positions.items():
            if position["size"] > 0:
                summary_data.append({
                    "symbol": symbol,
                    "size": position["size"],
                    "avg_price": position["avg_price"],
                    "market_value": position["market_value"],
                    "pnl": position["pnl"],
                    "pnl_percent": position["pnl_percent"],
                    "entry_date": position["entry_date"],
                    "holding_days": (datetime.now() - position["entry_date"]).days if position["entry_date"] else 0,
                })

        df = pd.DataFrame(summary_data)
        return df

    def get_trade_history(self, start_date: Optional[datetime] = None) -> pd.DataFrame:
        """
        获取交易历史

        Parameters
        ----------
        start_date : datetime, optional
            开始日期

        Returns
        -------
        pd.DataFrame
            交易历史
        """
        if not self.position_history:
            return pd.DataFrame()

        df = pd.DataFrame(self.position_history)

        if start_date:
            df = df[df["timestamp"] >= start_date]

        return df

    def rebalance_positions(
        self,
        target_weights: Dict[str, float],
        current_prices: Dict[str, float],
        total_capital: float,
        max_transaction_ratio: float = 0.1
    ) -> List[Dict[str, Any]]:
        """
        再平衡仓位

        Parameters
        ----------
        target_weights : Dict[str, float]
            目标权重
        current_prices : Dict[str, float]
            当前价格
        total_capital : float
            总资金
        max_transaction_ratio : float
            最大交易比例

        Returns
        -------
        List[Dict[str, Any]]
            再平衡交易指令
        """
        orders = []

        # 计算当前权重
        current_values = {}
        for symbol in target_weights.keys():
            position = self.get_position(symbol)
            current_price = current_prices.get(symbol, 0)
            current_values[symbol] = position["size"] * current_price

        total_current_value = sum(current_values.values())
        if total_current_value == 0:
            total_current_value = total_capital

        # 计算目标市值
        target_values = {}
        for symbol, weight in target_weights.items():
            target_values[symbol] = total_capital * weight

        # 生成再平衡订单
        for symbol in target_weights.keys():
            current_value = current_values.get(symbol, 0)
            target_value = target_values[symbol]
            current_price = current_prices.get(symbol, 1)

            value_diff = target_value - current_value

            # 检查交易限制
            max_transaction_value = total_capital * max_transaction_ratio
            if abs(value_diff) > max_transaction_value:
                value_diff = np.sign(value_diff) * max_transaction_value

            # 计算交易数量
            if current_price > 0:
                size_diff = int(value_diff / current_price)

                # A股最小交易单位
                size_diff = (size_diff // 100) * 100

                if size_diff != 0:
                    order = {
                        "symbol": symbol,
                        "action": "buy" if size_diff > 0 else "sell",
                        "size": abs(size_diff),
                        "price": current_price,
                        "reason": "rebalance",
                        "current_value": current_value,
                        "target_value": target_value,
                    }
                    orders.append(order)

        logger.info(f"再平衡生成 {len(orders)} 个订单")
        return orders

    def clear_position(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        清仓

        Parameters
        ----------
        symbol : str
            股票代码

        Returns
        -------
        Dict[str, Any], optional
            清仓订单信息
        """
        position = self.get_position(symbol)
        if position["size"] == 0:
            return None

        order = {
            "symbol": symbol,
            "action": "sell",
            "size": position["size"],
            "price": 0,  # 需要市场价
            "reason": "clear_position",
        }

        return order

    def clear_all_positions(self) -> List[Dict[str, Any]]:
        """
        清空所有仓位

        Returns
        -------
        List[Dict[str, Any]]
            清仓订单列表
        """
        orders = []

        for symbol in list(self.positions.keys()):
            order = self.clear_position(symbol)
            if order:
                orders.append(order)

        logger.info(f"清空所有仓位，生成 {len(orders)} 个订单")
        return orders

    def save_state(self, filepath: str):
        """保存仓位状态"""
        import pickle
        state = {
            "positions": self.positions,
            "position_history": self.position_history,
            "timestamp": datetime.now(),
        }

        with open(filepath, "wb") as f:
            pickle.dump(state, f)

        logger.info(f"仓位状态已保存: {filepath}")

    def load_state(self, filepath: str):
        """加载仓位状态"""
        import pickle
        try:
            with open(filepath, "rb") as f:
                state = pickle.load(f)

            self.positions = state.get("positions", {})
            self.position_history = state.get("position_history", [])
            logger.info(f"仓位状态已加载: {filepath}")
        except Exception as e:
            logger.error(f"加载仓位状态失败: {e}")