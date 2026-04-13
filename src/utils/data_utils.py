"""
数据处理工具函数
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Any, Tuple, Union
import logging

logger = logging.getLogger(__name__)


class DataUtils:
    """数据处理工具类"""

    @staticmethod
    def normalize_data(
        data: pd.DataFrame,
        method: str = "zscore",
        axis: int = 0
    ) -> pd.DataFrame:
        """
        数据标准化

        Parameters
        ----------
        data : pd.DataFrame
            输入数据
        method : str
            标准化方法: 'zscore', 'minmax', 'rank'
        axis : int
            标准化轴: 0 (按列), 1 (按行)

        Returns
        -------
        pd.DataFrame
            标准化后的数据
        """
        if data.empty:
            return data

        normalized = data.copy()

        if method == "zscore":
            # Z-score标准化
            if axis == 0:
                # 按列标准化
                mean = normalized.mean()
                std = normalized.std()
                std = std.replace(0, 1)  # 避免除零
                normalized = (normalized - mean) / std
            else:
                # 按行标准化
                mean = normalized.mean(axis=1)
                std = normalized.std(axis=1)
                std = std.replace(0, 1)
                normalized = normalized.sub(mean, axis=0).div(std, axis=0)

        elif method == "minmax":
            # Min-Max标准化到[0,1]
            if axis == 0:
                min_val = normalized.min()
                max_val = normalized.max()
                range_val = max_val - min_val
                range_val = range_val.replace(0, 1)  # 避免除零
                normalized = (normalized - min_val) / range_val
            else:
                min_val = normalized.min(axis=1)
                max_val = normalized.max(axis=1)
                range_val = max_val - min_val
                range_val = range_val.replace(0, 1)
                normalized = normalized.sub(min_val, axis=0).div(range_val, axis=0)

        elif method == "rank":
            # 排名标准化
            if axis == 0:
                normalized = normalized.rank(axis=0, pct=True)
            else:
                normalized = normalized.rank(axis=1, pct=True)

        else:
            raise ValueError(f"不支持的标准化方法: {method}")

        return normalized

    @staticmethod
    def winsorize_data(
        data: pd.Series,
        limits: Tuple[float, float] = (0.01, 0.01)
    ) -> pd.Series:
        """
        去极值处理

        Parameters
        ----------
        data : pd.Series
            输入数据
        limits : Tuple[float, float]
            左右截断比例

        Returns
        -------
        pd.Series
            去极值后的数据
        """
        if data.empty:
            return data

        # 计算分位数
        lower_limit = data.quantile(limits[0])
        upper_limit = data.quantile(1 - limits[1])

        # 截断
        winsorized = data.clip(lower=lower_limit, upper=upper_limit)

        return winsorized

    @staticmethod
    def fill_missing_values(
        data: pd.DataFrame,
        method: str = "ffill",
        **kwargs
    ) -> pd.DataFrame:
        """
        填充缺失值

        Parameters
        ----------
        data : pd.DataFrame
            输入数据
        method : str
            填充方法: 'ffill', 'bfill', 'mean', 'median', 'zero'
        **kwargs
            额外参数

        Returns
        -------
        pd.DataFrame
            填充后的数据
        """
        if data.empty:
            return data

        filled = data.copy()

        if method == "ffill":
            # 前向填充
            filled = filled.ffill(**kwargs)
        elif method == "bfill":
            # 后向填充
            filled = filled.bfill(**kwargs)
        elif method == "mean":
            # 均值填充
            filled = filled.fillna(filled.mean(), **kwargs)
        elif method == "median":
            # 中位数填充
            filled = filled.fillna(filled.median(), **kwargs)
        elif method == "zero":
            # 零填充
            filled = filled.fillna(0, **kwargs)
        elif method == "interpolate":
            # 插值填充
            filled = filled.interpolate(**kwargs)
        else:
            raise ValueError(f"不支持的填充方法: {method}")

        # 如果还有缺失值，使用前向填充
        if filled.isna().any().any():
            filled = filled.ffill().bfill()

        return filled

    @staticmethod
    def detect_outliers(
        data: pd.Series,
        method: str = "iqr",
        threshold: float = 1.5
    ) -> pd.Series:
        """
        检测异常值

        Parameters
        ----------
        data : pd.Series
            输入数据
        method : str
            检测方法: 'iqr', 'zscore', 'mad'
        threshold : float
            阈值

        Returns
        -------
        pd.Series
            异常值布尔序列
        """
        if data.empty:
            return pd.Series([], dtype=bool)

        if method == "iqr":
            # IQR方法
            q1 = data.quantile(0.25)
            q3 = data.quantile(0.75)
            iqr = q3 - q1
            lower_bound = q1 - threshold * iqr
            upper_bound = q3 + threshold * iqr
            outliers = (data < lower_bound) | (data > upper_bound)

        elif method == "zscore":
            # Z-score方法
            mean = data.mean()
            std = data.std()
            if std > 0:
                z_scores = (data - mean) / std
                outliers = abs(z_scores) > threshold
            else:
                outliers = pd.Series(False, index=data.index)

        elif method == "mad":
            # MAD方法
            median = data.median()
            mad = (data - median).abs().median()
            if mad > 0:
                modified_z_scores = 0.6745 * (data - median) / mad
                outliers = abs(modified_z_scores) > threshold
            else:
                outliers = pd.Series(False, index=data.index)

        else:
            raise ValueError(f"不支持的异常值检测方法: {method}")

        return outliers

    @staticmethod
    def calculate_returns(
        prices: pd.Series,
        method: str = "simple",
        periods: int = 1
    ) -> pd.Series:
        """
        计算收益率

        Parameters
        ----------
        prices : pd.Series
            价格序列
        method : str
            计算方法: 'simple', 'log'
        periods : int
            周期数

        Returns
        -------
        pd.Series
            收益率序列
        """
        if len(prices) < 2:
            return pd.Series([], dtype=float)

        if method == "simple":
            # 简单收益率
            returns = prices.pct_change(periods=periods)
        elif method == "log":
            # 对数收益率
            returns = np.log(prices / prices.shift(periods))
        else:
            raise ValueError(f"不支持的收益率计算方法: {method}")

        return returns

    @staticmethod
    def calculate_rolling_statistics(
        data: pd.Series,
        window: int,
        stat: str = "mean"
    ) -> pd.Series:
        """
        计算滚动统计量

        Parameters
        ----------
        data : pd.Series
            输入数据
        window : int
            滚动窗口
        stat : str
            统计量: 'mean', 'std', 'median', 'min', 'max', 'skew', 'kurt'

        Returns
        -------
        pd.Series
            滚动统计量序列
        """
        if len(data) < window:
            return pd.Series([], dtype=float)

        if stat == "mean":
            result = data.rolling(window=window, min_periods=1).mean()
        elif stat == "std":
            result = data.rolling(window=window, min_periods=1).std()
        elif stat == "median":
            result = data.rolling(window=window, min_periods=1).median()
        elif stat == "min":
            result = data.rolling(window=window, min_periods=1).min()
        elif stat == "max":
            result = data.rolling(window=window, min_periods=1).max()
        elif stat == "skew":
            result = data.rolling(window=window, min_periods=window).skew()
        elif stat == "kurt":
            result = data.rolling(window=window, min_periods=window).kurt()
        else:
            raise ValueError(f"不支持的统计量: {stat}")

        return result

    @staticmethod
    def align_dataframes(
        dfs: List[pd.DataFrame],
        how: str = "inner"
    ) -> List[pd.DataFrame]:
        """
        对齐多个DataFrame

        Parameters
        ----------
        dfs : List[pd.DataFrame]
            DataFrame列表
        how : str
            对齐方式: 'inner', 'outer'

        Returns
        -------
        List[pd.DataFrame]
            对齐后的DataFrame列表
        """
        if not dfs:
            return []

        # 获取所有索引的并集或交集
        all_indices = dfs[0].index
        for df in dfs[1:]:
            if how == "inner":
                all_indices = all_indices.intersection(df.index)
            else:  # outer
                all_indices = all_indices.union(df.index)

        # 排序索引
        all_indices = all_indices.sort_values()

        # 对齐每个DataFrame
        aligned_dfs = []
        for df in dfs:
            aligned_df = df.reindex(all_indices)

            # 前向填充缺失值（对于时间序列数据）
            aligned_df = aligned_df.ffill().bfill()

            aligned_dfs.append(aligned_df)

        return aligned_dfs

    @staticmethod
    def resample_data(
        data: pd.DataFrame,
        freq: str = "D",
        method: str = "ohlc"
    ) -> pd.DataFrame:
        """
        重采样数据

        Parameters
        ----------
        data : pd.DataFrame
            输入数据
        freq : str
            频率: 'D' (日), 'W' (周), 'M' (月)
        method : str
            重采样方法: 'ohlc', 'last', 'mean'

        Returns
        -------
        pd.DataFrame
            重采样后的数据
        """
        if data.empty:
            return data

        # 确保索引是DatetimeIndex
        if not isinstance(data.index, pd.DatetimeIndex):
            if "date" in data.columns:
                data = data.set_index("date")
            else:
                raise ValueError("数据需要日期索引或'date'列")

        if method == "ohlc":
            # OHLC重采样
            if "close" in data.columns:
                resampled = data["close"].resample(freq).ohlc()
            else:
                raise ValueError("OHLC重采样需要'close'列")
        elif method == "last":
            # 取最后值
            resampled = data.resample(freq).last()
        elif method == "mean":
            # 取均值
            resampled = data.resample(freq).mean()
        else:
            raise ValueError(f"不支持的重采样方法: {method}")

        return resampled

    @staticmethod
    def calculate_correlation_matrix(
        data: pd.DataFrame,
        method: str = "pearson"
    ) -> pd.DataFrame:
        """
        计算相关系数矩阵

        Parameters
        ----------
        data : pd.DataFrame
            输入数据，每列一个变量
        method : str
            相关系数方法: 'pearson', 'spearman', 'kendall'

        Returns
        -------
        pd.DataFrame
            相关系数矩阵
        """
        if data.empty:
            return pd.DataFrame()

        # 移除全为NaN的列
        data_clean = data.dropna(axis=1, how="all")

        if data_clean.empty:
            return pd.DataFrame()

        # 计算相关系数矩阵
        corr_matrix = data_clean.corr(method=method)

        return corr_matrix

    @staticmethod
    def calculate_autocorrelation(
        data: pd.Series,
        max_lag: int = 20
    ) -> pd.Series:
        """
        计算自相关函数

        Parameters
        ----------
        data : pd.Series
            输入序列
        max_lag : int
            最大滞后阶数

        Returns
        -------
        pd.Series
            自相关系数序列
        """
        if len(data) < 2:
            return pd.Series([], dtype=float)

        autocorr = pd.Series(index=range(1, max_lag + 1), dtype=float)

        for lag in range(1, max_lag + 1):
            autocorr[lag] = data.autocorr(lag=lag)

        return autocorr

    @staticmethod
    def calculate_rolling_beta(
        stock_returns: pd.Series,
        market_returns: pd.Series,
        window: int = 60
    ) -> pd.Series:
        """
        计算滚动Beta

        Parameters
        ----------
        stock_returns : pd.Series
            股票收益率
        market_returns : pd.Series
            市场收益率
        window : int
            滚动窗口

        Returns
        -------
        pd.Series
            Beta序列
        """
        # 对齐数据
        aligned = pd.concat([stock_returns, market_returns], axis=1).dropna()
        if len(aligned) < window:
            return pd.Series([], dtype=float)

        stock_aligned = aligned.iloc[:, 0]
        market_aligned = aligned.iloc[:, 1]

        # 计算滚动Beta
        beta_series = pd.Series(index=stock_aligned.index, dtype=float)

        for i in range(window, len(stock_aligned)):
            stock_window = stock_aligned.iloc[i-window:i]
            market_window = market_aligned.iloc[i-window:i]

            # 简单线性回归计算Beta
            cov = np.cov(stock_window, market_window)[0, 1]
            var = np.var(market_window)

            if var > 0:
                beta = cov / var
            else:
                beta = np.nan

            beta_series.iloc[i] = beta

        return beta_series

    @staticmethod
    def create_lagged_features(
        data: pd.DataFrame,
        lags: List[int],
        columns: Optional[List[str]] = None
    ) -> pd.DataFrame:
        """
        创建滞后特征

        Parameters
        ----------
        data : pd.DataFrame
            输入数据
        lags : List[int]
            滞后阶数列表
        columns : List[str], optional
            需要创建滞后特征的列

        Returns
        -------
        pd.DataFrame
            包含滞后特征的数据
        """
        if data.empty:
            return data

        if columns is None:
            columns = data.columns

        result = data.copy()

        for col in columns:
            if col in data.columns:
                for lag in lags:
                    result[f"{col}_lag{lag}"] = data[col].shift(lag)

        return result

    @staticmethod
    def remove_columns_with_missing(
        data: pd.DataFrame,
        threshold: float = 0.5
    ) -> pd.DataFrame:
        """
        移除缺失值过多的列

        Parameters
        ----------
        data : pd.DataFrame
            输入数据
        threshold : float
            缺失值比例阈值

        Returns
        -------
        pd.DataFrame
            处理后的数据
        """
        if data.empty:
            return data

        # 计算每列的缺失值比例
        missing_ratio = data.isna().mean()

        # 保留缺失值比例小于阈值的列
        columns_to_keep = missing_ratio[missing_ratio < threshold].index
        cleaned_data = data[columns_to_keep].copy()

        return cleaned_data