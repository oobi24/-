"""
因子计算工具函数
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Any, Tuple
import logging

logger = logging.getLogger(__name__)


class FactorUtils:
    """因子工具类"""

    @staticmethod
    def winsorize(
        series: pd.Series,
        limits: Tuple[float, float] = (0.01, 0.01)
    ) -> pd.Series:
        """
        去极值处理（Winsorization）

        Parameters
        ----------
        series : pd.Series
            输入序列
        limits : Tuple[float, float]
            左右截断比例

        Returns
        -------
        pd.Series
            去极值后的序列
        """
        if series.empty:
            return series

        # 计算分位数
        lower_limit = series.quantile(limits[0])
        upper_limit = series.quantile(1 - limits[1])

        # 截断
        winsorized = series.clip(lower=lower_limit, upper=upper_limit)

        return winsorized

    @staticmethod
    def mad_outlier_detection(
        series: pd.Series,
        threshold: float = 3.0
    ) -> pd.Series:
        """
        MAD异常值检测

        Parameters
        ----------
        series : pd.Series
            输入序列
        threshold : float
            异常值阈值

        Returns
        -------
        pd.Series
            异常值掩码（True表示异常值）
        """
        if series.empty:
            return pd.Series([], dtype=bool)

        median = series.median()
        mad = (series - median).abs().median()

        if mad == 0:
            # 如果MAD为0，使用标准差
            std = series.std()
            if std == 0:
                return pd.Series(False, index=series.index)
            outliers = (series - median).abs() > threshold * std
        else:
            outliers = (series - median).abs() > threshold * 1.4826 * mad

        return outliers

    @staticmethod
    def standardize(
        series: pd.Series,
        method: str = "zscore"
    ) -> pd.Series:
        """
        标准化处理

        Parameters
        ----------
        series : pd.Series
            输入序列
        method : str
            标准化方法: 'zscore', 'rank', 'mad'

        Returns
        -------
        pd.Series
            标准化后的序列
        """
        if series.empty:
            return series

        series = series.copy()

        if method == "zscore":
            # Z-score标准化
            mean = series.mean()
            std = series.std()
            if std > 0:
                standardized = (series - mean) / std
            else:
                standardized = series * 0  # 全为0
        elif method == "rank":
            # 排名标准化 (0-1)
            standardized = series.rank(pct=True)
        elif method == "mad":
            # MAD标准化
            median = series.median()
            mad = (series - median).abs().median()
            if mad > 0:
                standardized = (series - median) / mad
            else:
                standardized = series * 0
        else:
            raise ValueError(f"不支持的标准化方法: {method}")

        return standardized

    @staticmethod
    def calculate_ic(
        factor: pd.Series,
        forward_return: pd.Series,
        method: str = "normal"
    ) -> float:
        """
        计算信息系数 (Information Coefficient)

        Parameters
        ----------
        factor : pd.Series
            因子值
        forward_return : pd.Series
            未来收益率
        method : str
            IC计算方法: 'normal' (普通相关系数), 'rank' (秩相关系数)

        Returns
        -------
        float
            IC值
        """
        # 对齐数据
        aligned = pd.concat([factor, forward_return], axis=1).dropna()

        if aligned.empty:
            return np.nan

        factor_vals = aligned.iloc[:, 0]
        returns = aligned.iloc[:, 1]

        if method == "normal":
            # Pearson相关系数
            ic = factor_vals.corr(returns)
        elif method == "rank":
            # Spearman秩相关系数
            ic = factor_vals.corr(returns, method="spearman")
        else:
            raise ValueError(f"不支持的IC计算方法: {method}")

        return ic

    @staticmethod
    def calculate_ir(
        ic_series: pd.Series,
        annualize: bool = True
    ) -> float:
        """
        计算信息比率 (Information Ratio)

        Parameters
        ----------
        ic_series : pd.Series
            IC时间序列
        annualize : bool
            是否年化

        Returns
        -------
        float
            IR值
        """
        ic_series = ic_series.dropna()
        if len(ic_series) < 2:
            return np.nan

        mean_ic = ic_series.mean()
        std_ic = ic_series.std()

        if std_ic > 0:
            ir = mean_ic / std_ic
            if annualize:
                ir *= np.sqrt(252 / len(ic_series))  # 年化
        else:
            ir = np.nan

        return ir

    @staticmethod
    def calculate_factor_turnover(
        factor_rankings: pd.DataFrame,
        period: int = 20
    ) -> pd.Series:
        """
        计算因子换手率

        Parameters
        ----------
        factor_rankings : pd.DataFrame
            因子排名数据，每列一个时间点
        period : int
            计算换手率的周期

        Returns
        -------
        pd.Series
            因子换手率时间序列
        """
        turnover = pd.Series(index=factor_rankings.columns, dtype=float)

        for i in range(1, len(factor_rankings.columns)):
            curr_date = factor_rankings.columns[i]
            prev_date = factor_rankings.columns[i-1]

            curr_ranks = factor_rankings[curr_date]
            prev_ranks = factor_rankings[prev_date]

            # 计算重叠股票的排名变化
            common_stocks = curr_ranks.dropna().index.intersection(prev_ranks.dropna().index)
            if len(common_stocks) == 0:
                turnover[curr_date] = np.nan
                continue

            curr_common = curr_ranks[common_stocks]
            prev_common = prev_ranks[common_stocks]

            # 计算排名变化（标准化）
            rank_change = (curr_common - prev_common).abs().mean()
            max_change = len(common_stocks) - 1  # 最大可能变化
            if max_change > 0:
                normalized_change = rank_change / max_change
            else:
                normalized_change = 0

            turnover[curr_date] = normalized_change

        # 计算滚动平均换手率
        if period > 1:
            turnover = turnover.rolling(window=period, min_periods=1).mean()

        return turnover

    @staticmethod
    def calculate_factor_decay(
        factor_values: pd.Series,
        forward_returns: pd.Series,
        max_lag: int = 20
    ) -> pd.DataFrame:
        """
        计算因子衰减（IC衰减）

        Parameters
        ----------
        factor_values : pd.Series
            因子值
        forward_returns : pd.Series
            未来收益率
        max_lag : int
            最大滞后天数

        Returns
        -------
        pd.DataFrame
            IC衰减表
        """
        decay_data = []

        for lag in range(1, max_lag + 1):
            # 对齐因子和滞后收益率
            factor_aligned = factor_values.shift(lag)
            ic = FactorUtils.calculate_ic(factor_aligned, forward_returns)

            decay_data.append({
                "lag": lag,
                "ic": ic,
                "abs_ic": abs(ic)
            })

        decay_df = pd.DataFrame(decay_data)
        return decay_df

    @staticmethod
    def calculate_factor_autocorrelation(
        factor_values: pd.Series,
        max_lag: int = 10
    ) -> pd.Series:
        """
        计算因子自相关性

        Parameters
        ----------
        factor_values : pd.Series
            因子值
        max_lag : int
            最大滞后天数

        Returns
        -------
        pd.Series
            自相关性序列
        """
        autocorr = pd.Series(index=range(1, max_lag + 1), dtype=float)

        for lag in range(1, max_lag + 1):
            corr = factor_values.autocorr(lag=lag)
            autocorr[lag] = corr

        return autocorr

    @staticmethod
    def create_factor_portfolios(
        factor_values: pd.Series,
        num_groups: int = 5
    ) -> pd.Series:
        """
        创建因子分组（用于分层回测）

        Parameters
        ----------
        factor_values : pd.Series
            因子值
        num_groups : int
            分组数量

        Returns
        -------
        pd.Series
            分组标签（1到num_groups）
        """
        if factor_values.empty:
            return pd.Series(dtype=int)

        # 按因子值分组
        # 使用qcut确保每组数量大致相等
        try:
            groups = pd.qcut(factor_values, q=num_groups, labels=False, duplicates="drop")
            # qcut返回0到n-1，转换为1到n
            groups = groups + 1
        except Exception as e:
            logger.warning(f"使用qcut分组失败: {e}，改用等宽分箱")
            # 使用等宽分箱
            groups = pd.cut(factor_values, bins=num_groups, labels=False)
            groups = groups + 1

        return groups

    @staticmethod
    def calculate_group_returns(
        groups: pd.Series,
        forward_returns: pd.Series
    ) -> pd.DataFrame:
        """
        计算分组收益率

        Parameters
        ----------
        groups : pd.Series
            分组标签
        forward_returns : pd.Series
            未来收益率

        Returns
        -------
        pd.DataFrame
            分组收益率数据
        """
        # 对齐数据
        aligned = pd.concat([groups, forward_returns], axis=1).dropna()

        if aligned.empty:
            return pd.DataFrame()

        group_col = aligned.columns[0]
        return_col = aligned.columns[1]

        # 计算每组平均收益率
        group_returns = aligned.groupby(group_col)[return_col].mean()

        # 创建多空组合（第一组 - 最后一组）
        if len(group_returns) >= 2:
            long_short = group_returns.iloc[0] - group_returns.iloc[-1]
            group_returns["long_short"] = long_short

        return group_returns

    @staticmethod
    def calculate_factor_contribution(
        combined_factor: pd.Series,
        individual_factors: pd.DataFrame
    ) -> pd.DataFrame:
        """
        计算各因子对合成因子的贡献度

        Parameters
        ----------
        combined_factor : pd.Series
            合成因子值
        individual_factors : pd.DataFrame
            各因子值

        Returns
        -------
        pd.DataFrame
            因子贡献度
        """
        # 对齐数据
        aligned = pd.concat([combined_factor, individual_factors], axis=1).dropna()

        if aligned.empty:
            return pd.DataFrame()

        combined = aligned.iloc[:, 0]
        factors = aligned.iloc[:, 1:]

        # 计算相关系数作为贡献度度量
        contributions = {}
        for factor in factors.columns:
            corr = combined.corr(factors[factor])
            contributions[factor] = abs(corr)  # 使用绝对值

        # 归一化
        total_contribution = sum(contributions.values())
        if total_contribution > 0:
            normalized = {f: c / total_contribution for f, c in contributions.items()}
        else:
            normalized = contributions

        contribution_df = pd.DataFrame.from_dict(
            normalized, orient="index", columns=["contribution"]
        ).sort_values("contribution", ascending=False)

        return contribution_df