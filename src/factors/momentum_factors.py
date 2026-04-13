"""
动量与反转因子库 (Momentum & Reversal)
基于A股独特的"短期反转，长期动量"统计特征。
"""

import pandas as pd
import numpy as np
import logging
from typing import Dict, Any
from .base import Factor

logger = logging.getLogger(__name__)


class MomentumFactors:
    """动量因子库"""

    @staticmethod
    def get_factors() -> Dict[str, Factor]:
        """获取所有动量因子"""
        return {
            "momentum_1m_reversal": OneMonthReversalFactor(),
            "momentum_3m_momentum": ThreeMonthMomentumFactor(),
            "momentum_6m_momentum": SixMonthMomentumFactor(),
            "momentum_12m_momentum": TwelveMonthMomentumFactor(),
            "momentum_52w_high": FiftyTwoWeekHighFactor(),
            "momentum_rsi": RSIFactor(),
            "momentum_atr": ATRFactor(),
        }


class OneMonthReversalFactor(Factor):
    """1个月收益率反转因子"""

    def __init__(self):
        super().__init__(
            name="momentum_1m_reversal",
            description="1个月收益率反转，捕捉A股短期'跌多了涨、涨多了跌'的均值回归特性"
        )
        self.required_data = ["close"]

    def calculate(self, data: pd.DataFrame, lookback_days: int = 20) -> pd.Series:
        """
        计算1个月收益率反转因子

        Parameters
        ----------
        data : pd.DataFrame
            必须包含:
            - close: 收盘价
        lookback_days : int
            回溯天数，默认20个交易日（约1个月）

        Returns
        -------
        pd.Series
            反转因子值（负的过去收益率）
        """
        # 计算过去N日的收益率
        returns = data["close"].pct_change(lookback_days)

        # 反转因子 = -过去收益率（过去跌得多 -> 因子值大）
        reversal = -returns

        # 处理异常值
        reversal = reversal.replace([np.inf, -np.inf], np.nan)

        # 去极值
        median = reversal.median()
        mad = (reversal - median).abs().median()
        upper = median + 3 * 1.4826 * mad
        lower = median - 3 * 1.4826 * mad
        reversal = reversal.clip(lower, upper)

        return reversal


class ThreeMonthMomentumFactor(Factor):
    """3个月动量因子"""

    def __init__(self):
        super().__init__(
            name="momentum_3m_momentum",
            description="3个月动量，中期趋势跟踪"
        )
        self.required_data = ["close"]

    def calculate(self, data: pd.DataFrame, lookback_days: int = 60) -> pd.Series:
        """
        计算3个月动量因子

        Parameters
        ----------
        data : pd.DataFrame
            必须包含:
            - close: 收盘价
        lookback_days : int
            回溯天数，默认60个交易日（约3个月）

        Returns
        -------
        pd.Series
            动量因子值（过去收益率）
        """
        # 计算过去N日的收益率
        momentum = data["close"].pct_change(lookback_days)

        # 处理异常值
        momentum = momentum.replace([np.inf, -np.inf], np.nan)

        # 去极值
        median = momentum.median()
        mad = (momentum - median).abs().median()
        upper = median + 3 * 1.4826 * mad
        lower = median - 3 * 1.4826 * mad
        momentum = momentum.clip(lower, upper)

        return momentum


class SixMonthMomentumFactor(Factor):
    """6个月动量因子"""

    def __init__(self):
        super().__init__(
            name="momentum_6m_momentum",
            description="6个月动量，中期趋势跟踪"
        )
        self.required_data = ["close"]

    def calculate(self, data: pd.DataFrame, lookback_days: int = 120) -> pd.Series:
        """
        计算6个月动量因子

        Parameters
        ----------
        data : pd.DataFrame
            必须包含:
            - close: 收盘价
        lookback_days : int
            回溯天数，默认120个交易日（约6个月）

        Returns
        -------
        pd.Series
            动量因子值
        """
        # 计算过去N日的收益率
        momentum = data["close"].pct_change(lookback_days)

        # 处理异常值
        momentum = momentum.replace([np.inf, -np.inf], np.nan)

        # 去极值
        median = momentum.median()
        mad = (momentum - median).abs().median()
        upper = median + 3 * 1.4826 * mad
        lower = median - 3 * 1.4826 * mad
        momentum = momentum.clip(lower, upper)

        return momentum


class TwelveMonthMomentumFactor(Factor):
    """12个月动量因子"""

    def __init__(self):
        super().__init__(
            name="momentum_12m_momentum",
            description="12个月动量，长期趋势跟踪"
        )
        self.required_data = ["close"]

    def calculate(self, data: pd.DataFrame, lookback_days: int = 240) -> pd.Series:
        """
        计算12个月动量因子

        Parameters
        ----------
        data : pd.DataFrame
            必须包含:
            - close: 收盘价
        lookback_days : int
            回溯天数，默认240个交易日（约12个月）

        Returns
        -------
        pd.Series
            动量因子值
        """
        # 计算过去N日的收益率
        momentum = data["close"].pct_change(lookback_days)

        # 处理异常值
        momentum = momentum.replace([np.inf, -np.inf], np.nan)

        # 去极值
        median = momentum.median()
        mad = (momentum - median).abs().median()
        upper = median + 3 * 1.4826 * mad
        lower = median - 3 * 1.4826 * mad
        momentum = momentum.clip(lower, upper)

        return momentum


class FiftyTwoWeekHighFactor(Factor):
    """52周新高因子"""

    def __init__(self):
        super().__init__(
            name="momentum_52w_high",
            description="创52周新高，经典的右侧突破确认信号"
        )
        self.required_data = ["close", "high"]

    def calculate(self, data: pd.DataFrame, lookback_days: int = 240) -> pd.Series:
        """
        计算52周新高因子

        Parameters
        ----------
        data : pd.DataFrame
            必须包含:
            - close: 收盘价
            - high: 最高价
        lookback_days : int
            回溯天数，默认240个交易日（约52周）

        Returns
        -------
        pd.Series
            52周新高因子值（收盘价/过去52周最高价）
        """
        # 计算过去52周的最高价
        rolling_max = data["high"].rolling(window=lookback_days, min_periods=1).max()

        # 计算收盘价相对于52周高点的位置
        # 值越接近1表示越接近52周高点
        high_ratio = data["close"] / rolling_max

        # 处理异常值
        high_ratio = high_ratio.replace([np.inf, -np.inf], np.nan)

        # 去极值
        median = high_ratio.median()
        mad = (high_ratio - median).abs().median()
        upper = median + 3 * 1.4826 * mad
        lower = median - 3 * 1.4826 * mad
        high_ratio = high_ratio.clip(lower, upper)

        return high_ratio


class RSIFactor(Factor):
    """RSI因子"""

    def __init__(self):
        super().__init__(
            name="momentum_rsi",
            description="相对强弱指数 (RSI)，动量指标"
        )
        self.required_data = ["close"]

    def calculate(self, data: pd.DataFrame, period: int = 14) -> pd.Series:
        """
        计算RSI

        Parameters
        ----------
        data : pd.DataFrame
            必须包含:
            - close: 收盘价
        period : int
            RSI周期，默认14

        Returns
        -------
        pd.Series
            RSI值
        """
        # 计算价格变化
        delta = data["close"].diff()

        # 计算上涨和下跌
        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)

        # 计算平均上涨和下跌
        avg_gain = gain.rolling(window=period, min_periods=1).mean()
        avg_loss = loss.rolling(window=period, min_periods=1).mean()

        # 计算RS
        rs = avg_gain / avg_loss.replace(0, np.nan)

        # 计算RSI
        rsi = 100 - (100 / (1 + rs))

        # 处理异常值
        rsi = rsi.replace([np.inf, -np.inf], np.nan)

        # RSI范围限制在0-100
        rsi = rsi.clip(0, 100)

        return rsi


class ATRFactor(Factor):
    """ATR因子 (Average True Range)"""

    def __init__(self):
        super().__init__(
            name="momentum_atr",
            description="平均真实波动幅度 (ATR)，用于衡量波动性"
        )
        self.required_data = ["high", "low", "close"]

    def calculate(self, data: pd.DataFrame, period: int = 14) -> pd.Series:
        """
        计算ATR

        Parameters
        ----------
        data : pd.DataFrame
            必须包含:
            - high: 最高价
            - low: 最低价
            - close: 收盘价
        period : int
            ATR周期，默认14

        Returns
        -------
        pd.Series
            ATR值
        """
        # 计算真实波幅
        high_low = data["high"] - data["low"]
        high_close = (data["high"] - data["close"].shift(1)).abs()
        low_close = (data["low"] - data["close"].shift(1)).abs()

        # 真实波幅是三者中的最大值
        true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)

        # 计算ATR
        atr = true_range.rolling(window=period, min_periods=1).mean()

        # 处理异常值
        atr = atr.replace([np.inf, -np.inf], np.nan)

        # 去极值
        median = atr.median()
        mad = (atr - median).abs().median()
        upper = median + 3 * 1.4826 * mad
        lower = median - 3 * 1.4826 * mad
        atr = atr.clip(lower, upper)

        return atr