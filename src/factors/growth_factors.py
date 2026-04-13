"""
成长因子库 (Growth Factors)
适合科技、新能源、医药等爆发力极强的板块。
"""

import pandas as pd
import numpy as np
import logging
from typing import Dict, Any
from .base import Factor

logger = logging.getLogger(__name__)


class GrowthFactors:
    """成长因子库"""

    @staticmethod
    def get_factors() -> Dict[str, Factor]:
        """获取所有成长因子"""
        return {
            "growth_revenue_yoy": RevenueYOYFactor(),
            "growth_net_profit_yoy": NetProfitYOYFactor(),
            "growth_operating_profit_yoy": OperatingProfitYOYFactor(),
            "growth_gross_margin_yoy": GrossMarginYOYFactor(),
            "growth_peg": PEG_Factor(),
            "growth_asset_growth": AssetGrowthFactor(),
            "growth_equity_growth": EquityGrowthFactor(),
        }


class RevenueYOYFactor(Factor):
    """营业收入同比增长因子"""

    def __init__(self):
        super().__init__(
            name="growth_revenue_yoy",
            description="营业收入同比增长率，反映业务扩张速度"
        )
        self.required_data = ["revenue", "revenue_prev_year"]

    def calculate(self, data: pd.DataFrame) -> pd.Series:
        """
        计算营业收入同比增长率

        Parameters
        ----------
        data : pd.DataFrame
            必须包含:
            - revenue: 当期营业收入
            - revenue_prev_year: 上年同期营业收入

        Returns
        -------
        pd.Series
            营业收入同比增长率
        """
        # 计算同比增长率
        revenue_yoy = (data["revenue"] - data["revenue_prev_year"]) / data["revenue_prev_year"].abs()

        # 处理异常值
        revenue_yoy = revenue_yoy.replace([np.inf, -np.inf], np.nan)

        # 去极值
        median = revenue_yoy.median()
        mad = (revenue_yoy - median).abs().median()
        upper = median + 3 * 1.4826 * mad
        lower = median - 3 * 1.4826 * mad
        revenue_yoy = revenue_yoy.clip(lower, upper)

        return revenue_yoy


class NetProfitYOYFactor(Factor):
    """净利润同比增长因子"""

    def __init__(self):
        super().__init__(
            name="growth_net_profit_yoy",
            description="净利润同比增长率，业绩驱动的核心"
        )
        self.required_data = ["net_profit", "net_profit_prev_year"]

    def calculate(self, data: pd.DataFrame) -> pd.Series:
        """
        计算净利润同比增长率

        Parameters
        ----------
        data : pd.DataFrame
            必须包含:
            - net_profit: 当期净利润
            - net_profit_prev_year: 上年同期净利润

        Returns
        -------
        pd.Series
            净利润同比增长率
        """
        # 计算同比增长率
        net_profit_yoy = (data["net_profit"] - data["net_profit_prev_year"]) / data["net_profit_prev_year"].abs()

        # 处理分母为0的情况
        net_profit_yoy = net_profit_yoy.replace([np.inf, -np.inf], np.nan)

        # 去极值
        median = net_profit_yoy.median()
        mad = (net_profit_yoy - median).abs().median()
        upper = median + 3 * 1.4826 * mad
        lower = median - 3 * 1.4826 * mad
        net_profit_yoy = net_profit_yoy.clip(lower, upper)

        return net_profit_yoy


class OperatingProfitYOYFactor(Factor):
    """营业利润同比增长因子"""

    def __init__(self):
        super().__init__(
            name="growth_operating_profit_yoy",
            description="营业利润同比增长率"
        )
        self.required_data = ["operating_profit", "operating_profit_prev_year"]

    def calculate(self, data: pd.DataFrame) -> pd.Series:
        """
        计算营业利润同比增长率

        Parameters
        ----------
        data : pd.DataFrame
            必须包含:
            - operating_profit: 当期营业利润
            - operating_profit_prev_year: 上年同期营业利润

        Returns
        -------
        pd.Series
            营业利润同比增长率
        """
        # 计算同比增长率
        operating_profit_yoy = (
            data["operating_profit"] - data["operating_profit_prev_year"]
        ) / data["operating_profit_prev_year"].abs()

        # 处理异常值
        operating_profit_yoy = operating_profit_yoy.replace([np.inf, -np.inf], np.nan)

        # 去极值
        median = operating_profit_yoy.median()
        mad = (operating_profit_yoy - median).abs().median()
        upper = median + 3 * 1.4826 * mad
        lower = median - 3 * 1.4826 * mad
        operating_profit_yoy = operating_profit_yoy.clip(lower, upper)

        return operating_profit_yoy


class GrossMarginYOYFactor(Factor):
    """毛利率同比增长因子"""

    def __init__(self):
        super().__init__(
            name="growth_gross_margin_yoy",
            description="毛利率同比增长率，反映盈利能力变化"
        )
        self.required_data = ["gross_margin", "gross_margin_prev_year"]

    def calculate(self, data: pd.DataFrame) -> pd.Series:
        """
        计算毛利率同比增长率

        Parameters
        ----------
        data : pd.DataFrame
            必须包含:
            - gross_margin: 当期毛利率
            - gross_margin_prev_year: 上年同期毛利率

        Returns
        -------
        pd.Series
            毛利率同比增长率（百分点变化）
        """
        # 计算毛利率变化（百分点）
        gross_margin_yoy = data["gross_margin"] - data["gross_margin_prev_year"]

        # 处理异常值
        gross_margin_yoy = gross_margin_yoy.replace([np.inf, -np.inf], np.nan)

        # 去极值
        median = gross_margin_yoy.median()
        mad = (gross_margin_yoy - median).abs().median()
        upper = median + 3 * 1.4826 * mad
        lower = median - 3 * 1.4826 * mad
        gross_margin_yoy = gross_margin_yoy.clip(lower, upper)

        return gross_margin_yoy


class PEG_Factor(Factor):
    """PEG因子 (市盈率相对盈利增长比率)"""

    def __init__(self):
        super().__init__(
            name="growth_peg",
            description="PEG (市盈率相对盈利增长比率)，兼顾绝对估值与动态成长性的经典因子"
        )
        self.required_data = ["pe", "net_profit_yoy"]

    def calculate(self, data: pd.DataFrame) -> pd.Series:
        """
        计算PEG

        Parameters
        ----------
        data : pd.DataFrame
            必须包含:
            - pe: 市盈率
            - net_profit_yoy: 净利润同比增长率（小数形式，如0.2表示20%）

        Returns
        -------
        pd.Series
            PEG值
        """
        # 计算PEG
        # PEG = PE / (净利润增长率 * 100)
        # 增长率已经是小数形式，直接使用
        growth_rate = data["net_profit_yoy"] * 100  # 转换为百分比

        # 避免除零
        growth_rate = growth_rate.replace(0, np.nan)

        peg = data["pe"] / growth_rate

        # 处理异常值
        peg = peg.replace([np.inf, -np.inf], np.nan)

        # 去极值
        median = peg.median()
        mad = (peg - median).abs().median()
        upper = median + 3 * 1.4826 * mad
        lower = median - 3 * 1.4826 * mad
        peg = peg.clip(lower, upper)

        return peg


class AssetGrowthFactor(Factor):
    """总资产增长率因子"""

    def __init__(self):
        super().__init__(
            name="growth_asset_growth",
            description="总资产增长率，反映公司规模扩张"
        )
        self.required_data = ["total_assets", "total_assets_prev_year"]

    def calculate(self, data: pd.DataFrame) -> pd.Series:
        """
        计算总资产增长率

        Parameters
        ----------
        data : pd.DataFrame
            必须包含:
            - total_assets: 当期总资产
            - total_assets_prev_year: 上年同期总资产

        Returns
        -------
        pd.Series
            总资产增长率
        """
        # 计算总资产增长率
        asset_growth = (data["total_assets"] - data["total_assets_prev_year"]) / data["total_assets_prev_year"].abs()

        # 处理异常值
        asset_growth = asset_growth.replace([np.inf, -np.inf], np.nan)

        # 去极值
        median = asset_growth.median()
        mad = (asset_growth - median).abs().median()
        upper = median + 3 * 1.4826 * mad
        lower = median - 3 * 1.4826 * mad
        asset_growth = asset_growth.clip(lower, upper)

        return asset_growth


class EquityGrowthFactor(Factor):
    """净资产增长率因子"""

    def __init__(self):
        super().__init__(
            name="growth_equity_growth",
            description="净资产增长率，反映股东权益增长"
        )
        self.required_data = ["total_equity", "total_equity_prev_year"]

    def calculate(self, data: pd.DataFrame) -> pd.Series:
        """
        计算净资产增长率

        Parameters
        ----------
        data : pd.DataFrame
            必须包含:
            - total_equity: 当期净资产
            - total_equity_prev_year: 上年同期净资产

        Returns
        -------
        pd.Series
            净资产增长率
        """
        # 计算净资产增长率
        equity_growth = (data["total_equity"] - data["total_equity_prev_year"]) / data["total_equity_prev_year"].abs()

        # 处理异常值
        equity_growth = equity_growth.replace([np.inf, -np.inf], np.nan)

        # 去极值
        median = equity_growth.median()
        mad = (equity_growth - median).abs().median()
        upper = median + 3 * 1.4826 * mad
        lower = median - 3 * 1.4826 * mad
        equity_growth = equity_growth.clip(lower, upper)

        return equity_growth