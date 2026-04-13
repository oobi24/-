"""
量价与情绪因子库 (Volume & Price)
A股散户博弈特征明显，微观量价因子的IC（信息系数）通常优于基本面因子。
"""

import pandas as pd
import numpy as np
import logging
from typing import Dict, Any
from .base import Factor

logger = logging.getLogger(__name__)


class VolumePriceFactors:
    """量价因子库"""

    @staticmethod
    def get_factors() -> Dict[str, Factor]:
        """获取所有量价因子"""
        return {
            "volume_momentum": VolumeMomentumFactor(),
            "volume_h1_breakout": H1BreakoutFactor(),
            "volume_turnover": TurnoverRateFactor(),
            "volume_volatility": VolatilityFactor(),
            "volume_idiosyncratic_return": IdiosyncraticReturnFactor(),
            "volume_money_flow": MoneyFlowFactor(),
            "volume_vwap": VWAPFactor(),
        }


class VolumeMomentumFactor(Factor):
    """交易量动量因子"""

    def __init__(self):
        super().__init__(
            name="volume_momentum",
            description="交易量动量，基于量比异动捕捉资金流入"
        )
        self.required_data = ["volume"]

    def calculate(self, data: pd.DataFrame, short_period: int = 5, long_period: int = 20) -> pd.Series:
        """
        计算交易量动量

        Parameters
        ----------
        data : pd.DataFrame
            必须包含:
            - volume: 成交量
        short_period : int
            短期均线周期，默认5日
        long_period : int
            长期均线周期，默认20日

        Returns
        -------
        pd.Series
            交易量动量因子值（短期均量/长期均量）
        """
        # 计算成交量短期和长期移动平均
        volume_short_ma = data["volume"].rolling(window=short_period, min_periods=1).mean()
        volume_long_ma = data["volume"].rolling(window=long_period, min_periods=1).mean()

        # 计算量比（短期均量/长期均量）
        volume_ratio = volume_short_ma / volume_long_ma

        # 处理异常值
        volume_ratio = volume_ratio.replace([np.inf, -np.inf], np.nan)

        # 去极值
        median = volume_ratio.median()
        mad = (volume_ratio - median).abs().median()
        upper = median + 3 * 1.4826 * mad
        lower = median - 3 * 1.4826 * mad
        volume_ratio = volume_ratio.clip(lower, upper)

        return volume_ratio


class H1BreakoutFactor(Factor):
    """H-1突破因子（突破昨日高点）"""

    def __init__(self):
        super().__init__(
            name="volume_h1_breakout",
            description="突破昨日高点(H-1)且放量，配合价格趋势过滤放量下跌，精准捕捉主升浪启动点"
        )
        self.required_data = ["high", "close", "volume"]

    def calculate(self, data: pd.DataFrame) -> pd.Series:
        """
        计算H-1突破因子

        Parameters
        ----------
        data : pd.DataFrame
            必须包含:
            - high: 当日最高价
            - close: 当日收盘价
            - volume: 当日成交量

        Returns
        -------
        pd.Series
            H-1突破因子值（1表示突破，0表示未突破）
        """
        # 昨日高点
        prev_high = data["high"].shift(1)

        # 今日收盘价是否突破昨日高点
        breakout = (data["close"] > prev_high).astype(int)

        # 计算量比（今日成交量/昨日成交量）
        volume_ratio = data["volume"] / data["volume"].shift(1)

        # 结合放量条件（量比>1.5）
        volume_condition = (volume_ratio > 1.5).astype(int)

        # 计算价格趋势（今日收盘价>开盘价假设为上涨）
        # 如果没有开盘价数据，使用收盘价>昨日收盘价
        if "open" in data.columns:
            price_trend = (data["close"] > data["open"]).astype(int)
        else:
            price_trend = (data["close"] > data["close"].shift(1)).astype(int)

        # 综合信号：突破昨日高点 + 放量 + 上涨趋势
        signal = breakout * volume_condition * price_trend

        return signal


class TurnoverRateFactor(Factor):
    """换手率因子"""

    def __init__(self):
        super().__init__(
            name="volume_turnover",
            description="换手率，识别资金分歧，'低换手'在A股长期回测中常具备极强的正向Alpha"
        )
        self.required_data = ["turnover"]

    def calculate(self, data: pd.DataFrame) -> pd.Series:
        """
        计算换手率因子

        Parameters
        ----------
        data : pd.DataFrame
            必须包含:
            - turnover: 换手率

        Returns
        -------
        pd.Series
            换手率因子值
        """
        # 直接使用换手率数据
        turnover = data["turnover"].copy()

        # 处理异常值
        turnover = turnover.replace([np.inf, -np.inf], np.nan)

        # 去极值
        median = turnover.median()
        mad = (turnover - median).abs().median()
        upper = median + 3 * 1.4826 * mad
        lower = median - 3 * 1.4826 * mad
        turnover = turnover.clip(lower, upper)

        return turnover


class VolatilityFactor(Factor):
    """波动率因子"""

    def __init__(self):
        super().__init__(
            name="volume_volatility",
            description="波动率，例如20日历史波动率，捕捉经典的低波动（Low Volatility）异象"
        )
        self.required_data = ["close"]

    def calculate(self, data: pd.DataFrame, window: int = 20) -> pd.Series:
        """
        计算历史波动率

        Parameters
        ----------
        data : pd.DataFrame
            必须包含:
            - close: 收盘价
        window : int
            波动率计算窗口，默认20日

        Returns
        -------
        pd.Series
            历史波动率
        """
        # 计算日收益率
        returns = data["close"].pct_change()

        # 计算滚动波动率（年化）
        volatility = returns.rolling(window=window, min_periods=1).std() * np.sqrt(252)

        # 处理异常值
        volatility = volatility.replace([np.inf, -np.inf], np.nan)

        # 去极值
        median = volatility.median()
        mad = (volatility - median).abs().median()
        upper = median + 3 * 1.4826 * mad
        lower = median - 3 * 1.4826 * mad
        volatility = volatility.clip(lower, upper)

        return volatility


class IdiosyncraticReturnFactor(Factor):
    """特质收益率因子"""

    def __init__(self):
        super().__init__(
            name="volume_idiosyncratic_return",
            description="特质收益率，剥离大盘与行业Beta后，个股纯粹的资金异动"
        )
        self.required_data = ["close"]

    def calculate(self, data: pd.DataFrame, market_returns: pd.Series = None, window: int = 60) -> pd.Series:
        """
        计算特质收益率

        Parameters
        ----------
        data : pd.DataFrame
            必须包含:
            - close: 收盘价
        market_returns : pd.Series, optional
            市场收益率序列，索引与data相同
        window : int
            回归窗口，默认60日

        Returns
        -------
        pd.Series
            特质收益率
        """
        # 计算个股收益率
        stock_returns = data["close"].pct_change()

        if market_returns is None:
            # 如果没有市场收益率数据，使用个股收益率自身（简化处理）
            idiosyncratic_return = stock_returns
        else:
            # 确保市场收益率与个股收益率对齐
            aligned_market_returns = market_returns.reindex(stock_returns.index)

            # 计算滚动回归残差（特质收益率）
            idiosyncratic_return = pd.Series(index=stock_returns.index, dtype=float)

            for i in range(window, len(stock_returns)):
                start_idx = i - window
                end_idx = i

                # 提取窗口数据
                stock_window = stock_returns.iloc[start_idx:end_idx]
                market_window = aligned_market_returns.iloc[start_idx:end_idx]

                # 移除NaN
                valid_mask = stock_window.notna() & market_window.notna()
                if valid_mask.sum() < 10:  # 至少需要10个有效数据点
                    idiosyncratic_return.iloc[i] = np.nan
                    continue

                stock_valid = stock_window[valid_mask]
                market_valid = market_window[valid_mask]

                # 简单线性回归
                beta = np.cov(stock_valid, market_valid)[0, 1] / np.var(market_valid)
                alpha = np.mean(stock_valid) - beta * np.mean(market_valid)

                # 计算特质收益率
                idiosyncratic_return.iloc[i] = stock_returns.iloc[i] - (
                    alpha + beta * aligned_market_returns.iloc[i]
                )

        # 处理异常值
        idiosyncratic_return = idiosyncratic_return.replace([np.inf, -np.inf], np.nan)

        # 去极值
        median = idiosyncratic_return.median()
        mad = (idiosyncratic_return - median).abs().median()
        upper = median + 3 * 1.4826 * mad
        lower = median - 3 * 1.4826 * mad
        idiosyncratic_return = idiosyncratic_return.clip(lower, upper)

        return idiosyncratic_return


class MoneyFlowFactor(Factor):
    """资金流因子"""

    def __init__(self):
        super().__init__(
            name="volume_money_flow",
            description="资金流，基于Level-2高频数据的微观资金买卖意愿刻画"
        )
        self.required_data = ["close", "volume", "high", "low"]

    def calculate(self, data: pd.DataFrame) -> pd.Series:
        """
        计算资金流因子（简化版）

        Parameters
        ----------
        data : pd.DataFrame
            必须包含:
            - close: 收盘价
            - volume: 成交量
            - high: 最高价
            - low: 最低价

        Returns
        -------
        pd.Series
            资金流因子值
        """
        # 计算典型价格
        typical_price = (data["high"] + data["low"] + data["close"]) / 3

        # 计算资金流（典型价格 * 成交量）
        money_flow = typical_price * data["volume"]

        # 计算资金流比率
        # 这里使用简化逻辑：当日资金流/过去20日平均资金流
        money_flow_ratio = money_flow / money_flow.rolling(window=20, min_periods=1).mean()

        # 处理异常值
        money_flow_ratio = money_flow_ratio.replace([np.inf, -np.inf], np.nan)

        # 去极值
        median = money_flow_ratio.median()
        mad = (money_flow_ratio - median).abs().median()
        upper = median + 3 * 1.4826 * mad
        lower = median - 3 * 1.4826 * mad
        money_flow_ratio = money_flow_ratio.clip(lower, upper)

        return money_flow_ratio


class VWAPFactor(Factor):
    """VWAP因子"""

    def __init__(self):
        super().__init__(
            name="volume_vwap",
            description="成交量加权平均价格 (VWAP)，反映当日平均成交价格"
        )
        self.required_data = ["close", "volume", "high", "low"]

    def calculate(self, data: pd.DataFrame) -> pd.Series:
        """
        计算VWAP因子

        Parameters
        ----------
        data : pd.DataFrame
            必须包含:
            - close: 收盘价
            - volume: 成交量
            - high: 最高价
            - low: 最低价

        Returns
        -------
        pd.Series
            VWAP因子值（收盘价/VWAP）
        """
        # 计算典型价格（假设为VWAP的近似）
        typical_price = (data["high"] + data["low"] + data["close"]) / 3

        # 计算VWAP（成交量加权平均价格）
        # 这里简化处理：使用典型价格作为VWAP
        vwap = typical_price

        # 计算收盘价相对于VWAP的位置
        vwap_ratio = data["close"] / vwap

        # 处理异常值
        vwap_ratio = vwap_ratio.replace([np.inf, -np.inf], np.nan)

        # 去极值
        median = vwap_ratio.median()
        mad = (vwap_ratio - median).abs().median()
        upper = median + 3 * 1.4826 * mad
        lower = median - 3 * 1.4826 * mad
        vwap_ratio = vwap_ratio.clip(lower, upper)

        return vwap_ratio