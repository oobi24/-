"""
策略基类和具体策略实现
"""

import backtrader as bt
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import logging

logger = logging.getLogger(__name__)


class BaseStrategy(bt.Strategy):
    """策略基类"""

    params = (
        ("print_log", False),  # 是否打印日志
    )

    def __init__(self):
        """初始化策略"""
        # 数据引用
        self.datas = self.datas
        self.data = self.datas[0]  # 主数据

        # 指标计算
        self._init_indicators()

        # 订单跟踪
        self.order = None
        self.buy_price = None
        self.buy_comm = None

        # 日志
        self.log_list = []

    def _init_indicators(self):
        """初始化技术指标"""
        # 移动平均线
        self.sma_fast = bt.indicators.SimpleMovingAverage(
            self.data.close, period=10
        )
        self.sma_slow = bt.indicators.SimpleMovingAverage(
            self.data.close, period=30
        )

        # 成交量
        self.volume_sma = bt.indicators.SimpleMovingAverage(
            self.data.volume, period=20
        )

        # ATR用于仓位管理
        self.atr = bt.indicators.ATR(self.data, period=14)

    def log(self, txt: str, dt=None):
        """日志记录"""
        if self.params.print_log:
            dt = dt or self.data.datetime.date(0)
            log_msg = f"{dt.isoformat()}, {txt}"
            print(log_msg)
            self.log_list.append(log_msg)

    def notify_order(self, order):
        """订单状态通知"""
        if order.status in [order.Submitted, order.Accepted]:
            # 订单已提交/接受，无需操作
            return

        if order.status in [order.Completed]:
            # 订单已完成
            if order.isbuy():
                self.log(
                    f"买入执行: 价格={order.executed.price:.2f}, "
                    f"数量={order.executed.size}, "
                    f"成本={order.executed.value:.2f}, "
                    f"佣金={order.executed.comm:.2f}"
                )
                self.buy_price = order.executed.price
                self.buy_comm = order.executed.comm
            else:  # Sell
                self.log(
                    f"卖出执行: 价格={order.executed.price:.2f}, "
                    f"数量={order.executed.size}, "
                    f"收入={order.executed.value:.2f}, "
                    f"佣金={order.executed.comm:.2f}"
                )

            self.bar_executed = len(self)

        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            self.log(f"订单取消/拒绝: {order.status}")
            if hasattr(self, 'buy_price'):
                self.buy_price = None

        # 重置订单
        self.order = None

    def notify_trade(self, trade):
        """交易通知"""
        if not trade.isclosed:
            return

        self.log(
            f"交易盈亏: 毛利润={trade.pnl:.2f}, "
            f"净利润={trade.pnlcomm:.2f}"
        )

    def next(self):
        """策略逻辑（每个bar执行）"""
        # 检查是否有未完成订单
        if self.order:
            return

        # 策略逻辑由子类实现
        pass

    def stop(self):
        """策略结束"""
        self.log(f"策略结束，期末资金: {self.broker.getvalue():.2f}")


class VolumeMomentumStrategy(BaseStrategy):
    """
    交易量动量策略
    基于量比异动及"突破昨日高点(H-1)且放量"逻辑
    """

    params = (
        ("print_log", False),
        ("volume_ratio_threshold", 1.5),  # 量比阈值
        ("position_ratio", 0.1),  # 单笔仓位比例
        ("stop_loss", 0.08),  # 止损比例
        ("time_stop", 10),  # 时间止损天数
        ("atr_multiplier", 2.0),  # ATR乘数
    )

    def __init__(self):
        super().__init__()

        # 量比指标
        self.volume_ratio = self.data.volume / bt.indicators.SimpleMovingAverage(
            self.data.volume, period=20
        )

        # 突破信号
        self.prev_high = self.data.high(-1)  # 昨日高点

        # 持仓跟踪
        self.entry_date = None
        self.entry_price = None

    def next(self):
        """策略逻辑"""
        # 检查是否有未完成订单
        if self.order:
            return

        # 检查持仓
        if not self.position:
            # 没有持仓，寻找买入机会
            self._check_buy_signal()
        else:
            # 有持仓，检查卖出条件
            self._check_sell_signal()

    def _check_buy_signal(self):
        """检查买入信号"""
        # 量比条件
        volume_condition = self.volume_ratio[0] > self.params.volume_ratio_threshold

        # 突破昨日高点条件
        breakout_condition = self.data.close[0] > self.prev_high[0]

        # 价格趋势条件（收盘价 > 开盘价）
        if hasattr(self.data, 'open'):
            trend_condition = self.data.close[0] > self.data.open[0]
        else:
            trend_condition = self.data.close[0] > self.data.close[-1]

        # 综合买入信号
        buy_signal = volume_condition and breakout_condition and trend_condition

        if buy_signal:
            # 计算仓位
            size = self._calculate_position_size()
            if size > 0:
                # 执行买入
                self.order = self.buy(size=size)
                self.entry_date = len(self)
                self.entry_price = self.data.close[0]

                self.log(
                    f"买入信号触发: "
                    f"价格={self.data.close[0]:.2f}, "
                    f"量比={self.volume_ratio[0]:.2f}, "
                    f"突破={breakout_condition}, "
                    f"数量={size}"
                )

    def _check_sell_signal(self):
        """检查卖出信号"""
        current_price = self.data.close[0]
        entry_price = self.entry_price

        if entry_price is None:
            return

        # 价格止损
        price_stop_condition = current_price < entry_price * (1 - self.params.stop_loss)

        # 时间止损
        holding_days = len(self) - self.entry_date
        time_stop_condition = holding_days > self.params.time_stop

        # 止盈条件（移动止损）
        # 这里可以使用ATR跟踪止损
        atr_stop_price = entry_price + self.atr[0] * self.params.atr_multiplier
        trailing_stop_condition = current_price < atr_stop_price

        # 综合卖出信号
        sell_signal = price_stop_condition or time_stop_condition or trailing_stop_condition

        if sell_signal:
            # 执行卖出
            self.order = self.sell(size=self.position.size)

            reason = []
            if price_stop_condition:
                reason.append("价格止损")
            if time_stop_condition:
                reason.append("时间止损")
            if trailing_stop_condition:
                reason.append("移动止损")

            self.log(
                f"卖出信号触发: "
                f"价格={current_price:.2f}, "
                f"持仓天数={holding_days}, "
                f"原因={', '.join(reason)}"
            )

    def _calculate_position_size(self) -> int:
        """计算仓位大小"""
        # 基于ATR的风险管理
        if self.atr[0] == 0:
            return 0

        # 计算风险资金
        risk_capital = self.broker.getvalue() * self.params.position_ratio

        # 计算每份风险（ATR * 乘数）
        risk_per_share = self.atr[0] * self.params.atr_multiplier

        # 计算数量
        size = int(risk_capital / risk_per_share / self.data.close[0])

        # 确保不超过可用资金
        max_size = int(self.broker.getcash() / self.data.close[0])
        size = min(size, max_size)

        # 最小交易单位（A股100股）
        size = (size // 100) * 100

        return size


class FactorStrategy(BaseStrategy):
    """
    多因子策略
    结合基本面因子和量价因子
    """

    params = (
        ("print_log", False),
        ("factor_threshold", 0.5),  # 因子得分阈值
        ("position_ratio", 0.05),  # 单笔仓位比例
        ("max_positions", 10),  # 最大持仓数量
        ("stop_loss", 0.08),  # 止损比例
        ("holding_period", 20),  # 持有期
    )

    def __init__(self):
        super().__init__()

        # 因子数据（需要预先加载）
        self.factor_scores = None

        # 持仓跟踪
        self.positions_tracker = {}

    def set_factor_scores(self, factor_scores: pd.Series):
        """设置因子得分数据"""
        self.factor_scores = factor_scores

    def next(self):
        """策略逻辑"""
        # 检查是否有未完成订单
        if self.order:
            return

        # 检查持仓
        current_positions = len(self.positions_tracker)

        # 如果没有因子数据，跳过
        if self.factor_scores is None:
            return

        # 获取当前因子得分
        current_date = self.data.datetime.date(0)
        if current_date in self.factor_scores.index:
            current_score = self.factor_scores.loc[current_date]
        else:
            current_score = 0

        # 检查买入信号
        if (current_score > self.params.factor_threshold and
            current_positions < self.params.max_positions):
            self._execute_buy(current_score)

        # 检查卖出信号
        self._check_sell_signals(current_date)

    def _execute_buy(self, factor_score: float):
        """执行买入"""
        # 计算仓位
        size = self._calculate_position_size()

        if size > 0:
            # 执行买入
            self.order = self.buy(size=size)

            # 记录持仓
            current_date = self.data.datetime.date(0)
            self.positions_tracker[current_date] = {
                "entry_date": current_date,
                "entry_price": self.data.close[0],
                "size": size,
                "factor_score": factor_score,
            }

            self.log(
                f"因子买入: "
                f"价格={self.data.close[0]:.2f}, "
                f"因子得分={factor_score:.3f}, "
                f"数量={size}"
            )

    def _check_sell_signals(self, current_date):
        """检查卖出信号"""
        positions_to_sell = []

        for entry_date, position in self.positions_tracker.items():
            # 价格止损
            current_price = self.data.close[0]
            entry_price = position["entry_price"]
            price_stop = current_price < entry_price * (1 - self.params.stop_loss)

            # 时间止损
            holding_days = (current_date - entry_date).days
            time_stop = holding_days > self.params.holding_period

            # 因子得分下降（简化处理）
            factor_stop = False  # 可根据因子变化实现

            # 综合卖出信号
            sell_signal = price_stop or time_stop or factor_stop

            if sell_signal:
                positions_to_sell.append(entry_date)

        # 执行卖出
        for entry_date in positions_to_sell:
            position = self.positions_tracker[entry_date]
            size = position["size"]

            # 卖出持仓
            self.order = self.sell(size=size)

            # 计算盈亏
            pnl = (self.data.close[0] - position["entry_price"]) * size

            self.log(
                f"因子卖出: "
                f"价格={self.data.close[0]:.2f}, "
                f"持仓天数={(current_date - entry_date).days}, "
                f"盈亏={pnl:.2f}"
            )

            # 移除持仓记录
            del self.positions_tracker[entry_date]

    def _calculate_position_size(self) -> int:
        """计算仓位大小"""
        # 基于总资金和最大持仓数量
        position_value = self.broker.getvalue() * self.params.position_ratio
        size = int(position_value / self.data.close[0])

        # 确保不超过可用资金
        max_size = int(self.broker.getcash() / self.data.close[0])
        size = min(size, max_size)

        # 最小交易单位（A股100股）
        size = (size // 100) * 100

        return size

    def stop(self):
        """策略结束"""
        super().stop()

        # 输出持仓统计
        if self.positions_tracker:
            self.log(f"剩余持仓数量: {len(self.positions_tracker)}")