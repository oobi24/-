"""
质量与基本面因子库 (Quality Factors)
用于筛选财务健康、具有持续盈利能力的优质标的。
"""

import pandas as pd
import numpy as np
import logging
from typing import Dict, Any
from .base import Factor

logger = logging.getLogger(__name__)


class QualityFactors:
    """质量因子库"""

    @staticmethod
    def get_factors() -> Dict[str, Factor]:
        """获取所有质量因子"""
        return {
            "quality_roe": ROE_Factor(),
            "quality_gross_margin": GrossMarginFactor(),
            "quality_operating_margin": OperatingMarginFactor(),
            "quality_cashflow_to_revenue": CashflowToRevenueFactor(),
            "quality_current_ratio": CurrentRatioFactor(),
            "quality_debt_to_assets": DebtToAssetsFactor(),
            "quality_asset_turnover": AssetTurnoverFactor(),
        }


class ROE_Factor(Factor):
    """净资产收益率因子 (ROE)"""

    def __init__(self):
        super().__init__(
            name="quality_roe",
            description="净资产收益率 (ROE)，衡量核心资本使用效率"
        )
        self.required_data = ["net_profit", "total_equity"]

    def calculate(self, data: pd.DataFrame) -> pd.Series:
        """
        计算ROE

        Parameters
        ----------
        data : pd.DataFrame
            必须包含:
            - net_profit: 净利润
            - total_equity: 净资产

        Returns
        -------
        pd.Series
            ROE值
        """
        # 计算ROE
        roe = data["net_profit"] / data["total_equity"]

        # 处理异常值
        roe = roe.replace([np.inf, -np.inf], np.nan)

        # 去极值
        median = roe.median()
        mad = (roe - median).abs().median()
        upper = median + 3 * 1.4826 * mad
        lower = median - 3 * 1.4826 * mad
        roe = roe.clip(lower, upper)

        return roe


class GrossMarginFactor(Factor):
    """毛利率因子"""

    def __init__(self):
        super().__init__(
            name="quality_gross_margin",
            description="毛利率，反映企业在产业链中的核心定价权与护城河"
        )
        self.required_data = ["gross_profit", "revenue"]

    def calculate(self, data: pd.DataFrame) -> pd.Series:
        """
        计算毛利率

        Parameters
        ----------
        data : pd.DataFrame
            必须包含:
            - gross_profit: 毛利润
            - revenue: 营业收入

        Returns
        -------
        pd.Series
            毛利率
        """
        # 计算毛利率
        gross_margin = data["gross_profit"] / data["revenue"]

        # 处理异常值
        gross_margin = gross_margin.replace([np.inf, -np.inf], np.nan)

        # 去极值
        median = gross_margin.median()
        mad = (gross_margin - median).abs().median()
        upper = median + 3 * 1.4826 * mad
        lower = median - 3 * 1.4826 * mad
        gross_margin = gross_margin.clip(lower, upper)

        return gross_margin


class OperatingMarginFactor(Factor):
    """营业利润率因子"""

    def __init__(self):
        super().__init__(
            name="quality_operating_margin",
            description="营业利润率，反映主营业务盈利能力"
        )
        self.required_data = ["operating_profit", "revenue"]

    def calculate(self, data: pd.DataFrame) -> pd.Series:
        """
        计算营业利润率

        Parameters
        ----------
        data : pd.DataFrame
            必须包含:
            - operating_profit: 营业利润
            - revenue: 营业收入

        Returns
        -------
        pd.Series
            营业利润率
        """
        # 计算营业利润率
        operating_margin = data["operating_profit"] / data["revenue"]

        # 处理异常值
        operating_margin = operating_margin.replace([np.inf, -np.inf], np.nan)

        # 去极值
        median = operating_margin.median()
        mad = (operating_margin - median).abs().median()
        upper = median + 3 * 1.4826 * mad
        lower = median - 3 * 1.4826 * mad
        operating_margin = operating_margin.clip(lower, upper)

        return operating_margin


class CashflowToRevenueFactor(Factor):
    """经营现金流/营业收入因子"""

    def __init__(self):
        super().__init__(
            name="quality_cashflow_to_revenue",
            description="经营现金流/营业收入，A股'防雷'第一因子，过滤财务造假与纸面利润"
        )
        self.required_data = ["operating_cashflow", "revenue"]

    def calculate(self, data: pd.DataFrame) -> pd.Series:
        """
        计算经营现金流/营业收入

        Parameters
        ----------
        data : pd.DataFrame
            必须包含:
            - operating_cashflow: 经营活动现金流净额
            - revenue: 营业收入

        Returns
        -------
        pd.Series
            经营现金流/营业收入比率
        """
        # 计算比率
        cashflow_ratio = data["operating_cashflow"] / data["revenue"]

        # 处理异常值
        cashflow_ratio = cashflow_ratio.replace([np.inf, -np.inf], np.nan)

        # 去极值
        median = cashflow_ratio.median()
        mad = (cashflow_ratio - median).abs().median()
        upper = median + 3 * 1.4826 * mad
        lower = median - 3 * 1.4826 * mad
        cashflow_ratio = cashflow_ratio.clip(lower, upper)

        return cashflow_ratio


class CurrentRatioFactor(Factor):
    """流动比率因子"""

    def __init__(self):
        super().__init__(
            name="quality_current_ratio",
            description="流动比率，反映短期偿债能力"
        )
        self.required_data = ["current_assets", "current_liabilities"]

    def calculate(self, data: pd.DataFrame) -> pd.Series:
        """
        计算流动比率

        Parameters
        ----------
        data : pd.DataFrame
            必须包含:
            - current_assets: 流动资产
            - current_liabilities: 流动负债

        Returns
        -------
        pd.Series
            流动比率
        """
        # 计算流动比率
        current_ratio = data["current_assets"] / data["current_liabilities"]

        # 处理异常值
        current_ratio = current_ratio.replace([np.inf, -np.inf], np.nan)

        # 去极值
        median = current_ratio.median()
        mad = (current_ratio - median).abs().median()
        upper = median + 3 * 1.4826 * mad
        lower = median - 3 * 1.4826 * mad
        current_ratio = current_ratio.clip(lower, upper)

        return current_ratio


class DebtToAssetsFactor(Factor):
    """资产负债率因子"""

    def __init__(self):
        super().__init__(
            name="quality_debt_to_assets",
            description="资产负债率，反映财务杠杆水平"
        )
        self.required_data = ["total_liabilities", "total_assets"]

    def calculate(self, data: pd.DataFrame) -> pd.Series:
        """
        计算资产负债率

        Parameters
        ----------
        data : pd.DataFrame
            必须包含:
            - total_liabilities: 总负债
            - total_assets: 总资产

        Returns
        -------
        pd.Series
            资产负债率
        """
        # 计算资产负债率
        debt_ratio = data["total_liabilities"] / data["total_assets"]

        # 处理异常值
        debt_ratio = debt_ratio.replace([np.inf, -np.inf], np.nan)

        # 去极值
        median = debt_ratio.median()
        mad = (debt_ratio - median).abs().median()
        upper = median + 3 * 1.4826 * mad
        lower = median - 3 * 1.4826 * mad
        debt_ratio = debt_ratio.clip(lower, upper)

        return debt_ratio


class AssetTurnoverFactor(Factor):
    """资产周转率因子"""

    def __init__(self):
        super().__init__(
            name="quality_asset_turnover",
            description="资产周转率，反映资产使用效率"
        )
        self.required_data = ["revenue", "total_assets"]

    def calculate(self, data: pd.DataFrame) -> pd.Series:
        """
        计算资产周转率

        Parameters
        ----------
        data : pd.DataFrame
            必须包含:
            - revenue: 营业收入
            - total_assets: 总资产

        Returns
        -------
        pd.Series
            资产周转率
        """
        # 计算资产周转率
        asset_turnover = data["revenue"] / data["total_assets"]

        # 处理异常值
        asset_turnover = asset_turnover.replace([np.inf, -np.inf], np.nan)

        # 去极值
        median = asset_turnover.median()
        mad = (asset_turnover - median).abs().median()
        upper = median + 3 * 1.4826 * mad
        lower = median - 3 * 1.4826 * mad
        asset_turnover = asset_turnover.clip(lower, upper)

        return asset_turnover