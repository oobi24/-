"""
估值因子库 (Value Factors)
A股具有明显的估值均值回归特征，低估值策略在熊市/震荡市表现稳健。
"""

import pandas as pd
import numpy as np
import logging
from typing import Dict, Any
from .base import Factor

logger = logging.getLogger(__name__)


class ValueFactors:
    """估值因子库"""

    @staticmethod
    def get_factors() -> Dict[str, Factor]:
        """获取所有估值因子"""
        return {
            "value_pe_ttm": PE_TTM_Factor(),
            "value_ep": EP_Factor(),
            "value_pb_lf": PB_LF_Factor(),
            "value_dividend_yield": DividendYieldFactor(),
            "value_ps_ttm": PS_TTM_Factor(),
            "value_pcf": PCF_Factor(),
        }


class PE_TTM_Factor(Factor):
    """市盈率因子 (PE-TTM)"""

    def __init__(self):
        super().__init__(
            name="value_pe_ttm",
            description="滚动市盈率 (PE-TTM)，剔除季节性影响"
        )
        self.required_data = ["close", "net_profit_ttm"]

    def calculate(self, data: pd.DataFrame) -> pd.Series:
        """
        计算PE-TTM

        Parameters
        ----------
        data : pd.DataFrame
            必须包含:
            - close: 收盘价
            - net_profit_ttm: 滚动净利润（TTM）

        Returns
        -------
        pd.Series
            PE-TTM值
        """
        # 计算每股收益
        # 假设net_profit_ttm是总净利润，需要除以总股本得到每股收益
        # 这里简化处理，假设数据已包含每股收益或使用市值估算
        if "eps_ttm" in data.columns:
            eps = data["eps_ttm"]
        else:
            # 如果没有每股收益，使用净利润/市值估算
            if "market_cap" in data.columns:
                eps = data["net_profit_ttm"] / data["market_cap"] * data["close"]
            else:
                # 简化：假设总股本为1
                eps = data["net_profit_ttm"]

        # 计算PE
        pe = data["close"] / eps

        # 处理异常值
        pe = pe.replace([np.inf, -np.inf], np.nan)

        # 去极值（MAD方法）
        median = pe.median()
        mad = (pe - median).abs().median()
        upper = median + 3 * 1.4826 * mad
        lower = median - 3 * 1.4826 * mad
        pe = pe.clip(lower, upper)

        return pe


class EP_Factor(Factor):
    """盈利率因子 (EP = 1/PE)"""

    def __init__(self):
        super().__init__(
            name="value_ep",
            description="盈利率 (EP = 1/PE)，在量化平滑处理中有效避免负值异常"
        )
        self.required_data = ["close", "net_profit_ttm"]

    def calculate(self, data: pd.DataFrame) -> pd.Series:
        """
        计算EP (1/PE)

        Parameters
        ----------
        data : pd.DataFrame
            同PE_TTM_Factor

        Returns
        -------
        pd.Series
            EP值
        """
        # 先计算PE
        pe_factor = PE_TTM_Factor()
        pe = pe_factor.calculate(data)

        # 计算EP
        ep = 1 / pe

        # 处理异常值
        ep = ep.replace([np.inf, -np.inf], np.nan)

        return ep


class PB_LF_Factor(Factor):
    """市净率因子 (PB-LF)"""

    def __init__(self):
        super().__init__(
            name="value_pb_lf",
            description="市净率 (PB-LF)，银行、周期等重资产行业的定价锚"
        )
        self.required_data = ["close", "book_value_per_share"]

    def calculate(self, data: pd.DataFrame) -> pd.Series:
        """
        计算PB-LF

        Parameters
        ----------
        data : pd.DataFrame
            必须包含:
            - close: 收盘价
            - book_value_per_share: 每股净资产

        Returns
        -------
        pd.Series
            PB-LF值
        """
        if "book_value_per_share" not in data.columns:
            # 如果没有每股净资产，尝试计算
            if "total_equity" in data.columns and "total_shares" in data.columns:
                bvps = data["total_equity"] / data["total_shares"]
            else:
                # 使用简化估计
                bvps = data["close"] * 0.5  # 假设市净率为2
        else:
            bvps = data["book_value_per_share"]

        # 计算PB
        pb = data["close"] / bvps

        # 处理异常值
        pb = pb.replace([np.inf, -np.inf], np.nan)

        # 去极值
        median = pb.median()
        mad = (pb - median).abs().median()
        upper = median + 3 * 1.4826 * mad
        lower = median - 3 * 1.4826 * mad
        pb = pb.clip(lower, upper)

        return pb


class DividendYieldFactor(Factor):
    """股息率因子"""

    def __init__(self):
        super().__init__(
            name="value_dividend_yield",
            description="股息率，红利低波策略的绝对核心"
        )
        self.required_data = ["close", "dividend_per_share"]

    def calculate(self, data: pd.DataFrame) -> pd.Series:
        """
        计算股息率

        Parameters
        ----------
        data : pd.DataFrame
            必须包含:
            - close: 收盘价
            - dividend_per_share: 每股股息

        Returns
        -------
        pd.Series
            股息率
        """
        if "dividend_per_share" not in data.columns:
            # 如果没有股息数据，返回NaN
            return pd.Series(np.nan, index=data.index)

        # 计算股息率
        dividend_yield = data["dividend_per_share"] / data["close"]

        # 处理异常值
        dividend_yield = dividend_yield.replace([np.inf, -np.inf], np.nan)

        # 去极值
        median = dividend_yield.median()
        mad = (dividend_yield - median).abs().median()
        upper = median + 3 * 1.4826 * mad
        lower = median - 3 * 1.4826 * mad
        dividend_yield = dividend_yield.clip(lower, upper)

        return dividend_yield


class PS_TTM_Factor(Factor):
    """市销率因子 (PS-TTM)"""

    def __init__(self):
        super().__init__(
            name="value_ps_ttm",
            description="市销率 (PS-TTM)，适用于成长型公司"
        )
        self.required_data = ["close", "revenue_ttm"]

    def calculate(self, data: pd.DataFrame) -> pd.Series:
        """
        计算PS-TTM

        Parameters
        ----------
        data : pd.DataFrame
            必须包含:
            - close: 收盘价
            - revenue_ttm: 滚动营业收入（TTM）

        Returns
        -------
        pd.Series
            PS-TTM值
        """
        # 计算每股营业收入
        if "revenue_per_share" in data.columns:
            revenue_ps = data["revenue_per_share"]
        else:
            # 使用简化估计
            if "market_cap" in data.columns:
                revenue_ps = data["revenue_ttm"] / data["market_cap"] * data["close"]
            else:
                # 假设总股本为1
                revenue_ps = data["revenue_ttm"]

        # 计算PS
        ps = data["close"] / revenue_ps

        # 处理异常值
        ps = ps.replace([np.inf, -np.inf], np.nan)

        # 去极值
        median = ps.median()
        mad = (ps - median).abs().median()
        upper = median + 3 * 1.4826 * mad
        lower = median - 3 * 1.4826 * mad
        ps = ps.clip(lower, upper)

        return ps


class PCF_Factor(Factor):
    """市现率因子 (PCF)"""

    def __init__(self):
        super().__init__(
            name="value_pcf",
            description="市现率 (PCF)，基于经营现金流"
        )
        self.required_data = ["close", "operating_cashflow_ttm"]

    def calculate(self, data: pd.DataFrame) -> pd.Series:
        """
        计算PCF

        Parameters
        ----------
        data : pd.DataFrame
            必须包含:
            - close: 收盘价
            - operating_cashflow_ttm: 滚动经营现金流（TTM）

        Returns
        -------
        pd.Series
            PCF值
        """
        # 计算每股经营现金流
        if "cashflow_per_share" in data.columns:
            cfps = data["cashflow_per_share"]
        else:
            # 使用简化估计
            if "market_cap" in data.columns:
                cfps = data["operating_cashflow_ttm"] / data["market_cap"] * data["close"]
            else:
                # 假设总股本为1
                cfps = data["operating_cashflow_ttm"]

        # 计算PCF
        pcf = data["close"] / cfps

        # 处理异常值
        pcf = pcf.replace([np.inf, -np.inf], np.nan)

        # 去极值
        median = pcf.median()
        mad = (pcf - median).abs().median()
        upper = median + 3 * 1.4826 * mad
        lower = median - 3 * 1.4826 * mad
        pcf = pcf.clip(lower, upper)

        return pcf