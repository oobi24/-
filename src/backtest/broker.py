"""
A股专用经纪人，适配A股交易规则
"""

import backtrader as bt
import pandas as pd
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)


class ABroker(bt.brokers.BackBroker):
    """A股经纪人基类"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.tplus1_enabled = kwargs.get("tplus1", True)
        self.limit_up_down_enabled = kwargs.get("limit_up_down", True)

    def _execute_order(self, order, price, dt):
        """执行订单（重写以加入A股规则检查）"""
        # 检查涨跌停限制
        if self.limit_up_down_enabled:
            if not self._check_limit_up_down(order, price):
                order.reject()
                return

        # 检查T+1规则
        if self.tplus1_enabled:
            if not self._check_tplus1(order):
                order.reject()
                return

        # 执行父类逻辑
        super()._execute_order(order, price, dt)

    def _check_limit_up_down(self, order, price) -> bool:
        """检查涨跌停限制"""
        data = order.data
        symbol = data._name

        # 获取涨跌停价格（简化处理）
        # 实际中需要根据股票类型、板块等确定涨跌停幅度
        limit_up = data.close[-1] * 1.1  # 涨停价
        limit_down = data.close[-1] * 0.9  # 跌停价

        if order.isbuy():
            # 买入订单检查涨停价
            if price >= limit_up:
                logger.warning(f"买入订单 {symbol} 触及涨停价: {price:.2f} >= {limit_up:.2f}")
                return False
        else:
            # 卖出订单检查跌停价
            if price <= limit_down:
                logger.warning(f"卖出订单 {symbol} 触及跌停价: {price:.2f} <= {limit_down:.2f}")
                return False

        return True

    def _check_tplus1(self, order) -> bool:
        """检查T+1规则"""
        if order.isbuy():
            # 买入订单不受T+1限制
            return True

        # 卖出订单检查持仓是否满足T+1
        position = self.getposition(order.data)
        if position is None:
            return False

        # 检查持仓是否满足T+1（简化处理）
        # 实际中需要跟踪每笔买入的时间
        # 这里假设所有持仓都满足T+1
        return True


class AShareBroker(ABroker):
    """A股完整经纪人"""

    params = (
        ("commission", 0.00025),  # 佣金万分之2.5
        ("stamp_tax", 0.001),     # 印花税千分之一
        ("slippage", 0.001),      # 滑点千分之一
        ("tplus1", True),         # T+1规则
        ("limit_up_down", True),  # 涨跌停限制
    )

    def __init__(self, **kwargs):
        # 设置佣金
        comm = bt.commissions.CommInfoBase(
            commission=kwargs.get("commission", 0.00025),
            mult=1.0,
            margin=0.0,
            stocklike=True,
            commtype=bt.commissions.CommInfoBase.COMM_PERC,
        )

        # 设置印花税（仅卖出时收取）
        stamp_tax_rate = kwargs.get("stamp_tax", 0.001)
        comm._stamp_duty = stamp_tax_rate

        # 设置滑点
        slippage = kwargs.get("slippage", 0.001)

        # 初始化父类
        super().__init__(**kwargs)

        # 设置佣金和滑点
        self.addcommissioninfo(comm)
        self.set_slippage_perc(perc=slippage)

        logger.info(
            f"A股经纪人初始化: "
            f"佣金={self.params.commission*10000}‱, "
            f"印花税={self.params.stamp_tax*1000}‰, "
            f"滑点={self.params.slippage*1000}‰"
        )

    def _execute_order(self, order, price, dt):
        """执行订单（加入印花税和滑点）"""
        # 计算实际成交价（加入滑点）
        if self.params.slippage > 0:
            slippage = price * self.params.slippage
            if order.isbuy():
                price += slippage  # 买入时价格上滑
            else:
                price -= slippage  # 卖出时价格下滑

        # 执行父类逻辑
        super()._execute_order(order, price, dt)

    def get_commission_info(self, data):
        """获取佣金信息（重写以加入印花税）"""
        comminfo = super().get_commission_info(data)

        # 如果是卖出订单，添加印花税
        if hasattr(self, '_current_order') and self._current_order is not None:
            if not self._current_order.isbuy():
                # 计算印花税
                value = self._current_order.executed.price * self._current_order.executed.size
                stamp_duty = value * self.params.stamp_tax

                # 添加到佣金
                comminfo.commission += stamp_duty

        return comminfo

    def _process_commission(self, order):
        """处理佣金（重写以支持印花税）"""
        # 获取佣金信息
        comminfo = self.get_commission_info(order.data)

        # 计算佣金
        commission = comminfo._getcommission(
            order.executed.size,
            order.executed.price,
            order.executed.value
        )

        # 记录佣金
        order.executed.comm = commission

        # 更新现金
        self.cash -= commission

        logger.debug(
            f"佣金计算: "
            f"数量={order.executed.size}, "
            f"价格={order.executed.price:.2f}, "
            f"佣金={commission:.2f}"
        )

    def set_slippage_perc(self, perc: float = 0.001):
        """设置百分比滑点"""
        self._slip_perc = perc

    def get_slippage_price(self, price: float, is_buy: bool) -> float:
        """获取考虑滑点的价格"""
        if self._slip_perc <= 0:
            return price

        slippage = price * self._slip_perc
        if is_buy:
            return price + slippage
        else:
            return price - slippage

    def get_trade_summary(self) -> Dict[str, Any]:
        """获取交易摘要"""
        trades = self._trades
        positions = self.positions

        # 计算总交易统计
        total_trades = len(trades)
        winning_trades = 0
        losing_trades = 0
        total_pnl = 0
        total_commission = 0

        for trade in trades.values():
            if trade.pnl > 0:
                winning_trades += 1
            else:
                losing_trades += 1

            total_pnl += trade.pnl
            total_commission += trade.commission or 0

        # 计算胜率
        win_rate = winning_trades / max(total_trades, 1)

        # 计算平均盈亏
        avg_win = 0
        avg_loss = 0

        if winning_trades > 0:
            avg_win = sum(t.pnl for t in trades.values() if t.pnl > 0) / winning_trades
        if losing_trades > 0:
            avg_loss = sum(t.pnl for t in trades.values() if t.pnl < 0) / losing_trades

        summary = {
            "total_trades": total_trades,
            "winning_trades": winning_trades,
            "losing_trades": losing_trades,
            "win_rate": win_rate,
            "total_pnl": total_pnl,
            "total_commission": total_commission,
            "net_pnl": total_pnl - total_commission,
            "avg_win": avg_win,
            "avg_loss": avg_loss,
            "profit_factor": abs(avg_win * winning_trades) / max(abs(avg_loss * losing_trades), 1),
            "current_positions": len(positions),
        }

        return summary

    def get_position_summary(self) -> pd.DataFrame:
        """获取持仓摘要"""
        position_data = []

        for data, position in self.positions.items():
            if position.size != 0:
                position_data.append({
                    "symbol": data._name,
                    "size": position.size,
                    "price": position.price,
                    "value": position.size * position.price,
                    "pnl": position.adjbase,
                })

        return pd.DataFrame(position_data)