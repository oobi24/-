"""
多因子合成引擎
支持多因子合成（打分法/回归法）及正交化处理
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Any, Tuple
import logging

logger = logging.getLogger(__name__)


class MultiFactorEngine:
    """多因子合成引擎"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.method = config.get("method", "score")  # score, regression
        self.weights = config.get("weights", {})
        self.neutralization = config.get("neutralization", True)

    def calculate_factor_scores(
        self,
        factor_data: pd.DataFrame,
        factor_names: List[str],
        method: str = "zscore"
    ) -> pd.DataFrame:
        """
        计算因子得分

        Parameters
        ----------
        factor_data : pd.DataFrame
            因子数据，每列一个因子
        factor_names : List[str]
            因子名称列表
        method : str
            标准化方法: 'zscore', 'rank', 'mad'

        Returns
        -------
        pd.DataFrame
            标准化后的因子得分
        """
        scores = pd.DataFrame(index=factor_data.index)

        for factor in factor_names:
            if factor not in factor_data.columns:
                logger.warning(f"因子 {factor} 不在数据中，跳过")
                continue

            factor_values = factor_data[factor].copy()

            # 处理缺失值
            factor_values = factor_values.fillna(factor_values.median())

            # 标准化
            if method == "zscore":
                # Z-score标准化
                mean = factor_values.mean()
                std = factor_values.std()
                if std > 0:
                    normalized = (factor_values - mean) / std
                else:
                    normalized = factor_values * 0  # 全为0
            elif method == "rank":
                # 排名标准化 (0-1)
                normalized = factor_values.rank(pct=True)
            elif method == "mad":
                # MAD标准化
                median = factor_values.median()
                mad = (factor_values - median).abs().median()
                if mad > 0:
                    normalized = (factor_values - median) / mad
                else:
                    normalized = factor_values * 0
            else:
                raise ValueError(f"不支持的标准化方法: {method}")

            scores[factor] = normalized

        return scores

    def neutralize_factors(
        self,
        factor_scores: pd.DataFrame,
        style_factors: Optional[pd.DataFrame] = None,
        industry_dummies: Optional[pd.DataFrame] = None,
        market_cap: Optional[pd.Series] = None
    ) -> pd.DataFrame:
        """
        因子中性化处理

        Parameters
        ----------
        factor_scores : pd.DataFrame
            因子得分
        style_factors : pd.DataFrame, optional
            风格因子数据
        industry_dummies : pd.DataFrame, optional
            行业哑变量
        market_cap : pd.Series, optional
            市值数据

        Returns
        -------
        pd.DataFrame
            中性化后的因子得分
        """
        if not self.neutralization:
            return factor_scores

        neutralized = pd.DataFrame(index=factor_scores.index)

        for factor in factor_scores.columns:
            y = factor_scores[factor].values.reshape(-1, 1)

            # 构建特征矩阵
            features = []

            # 添加市值因子（如果提供）
            if market_cap is not None:
                market_cap_aligned = market_cap.reindex(factor_scores.index)
                if market_cap_aligned.notna().any():
                    # 对数市值
                    log_market_cap = np.log(market_cap_aligned.fillna(market_cap_aligned.median()))
                    features.append(log_market_cap.values.reshape(-1, 1))

            # 添加行业因子（如果提供）
            if industry_dummies is not None:
                industry_aligned = industry_dummies.reindex(factor_scores.index).fillna(0)
                if not industry_aligned.empty:
                    features.append(industry_aligned.values)

            # 添加风格因子（如果提供）
            if style_factors is not None:
                style_aligned = style_factors.reindex(factor_scores.index).fillna(0)
                if not style_aligned.empty:
                    features.append(style_aligned.values)

            if not features:
                # 没有中性化因子，直接返回原始值
                neutralized[factor] = factor_scores[factor]
                continue

            # 合并特征
            X = np.hstack(features)

            # 检查数据有效性
            valid_mask = ~np.isnan(y).flatten() & ~np.isnan(X).any(axis=1)
            if valid_mask.sum() < 10:  # 至少需要10个有效样本
                neutralized[factor] = factor_scores[factor]
                continue

            y_valid = y[valid_mask]
            X_valid = X[valid_mask]

            # 线性回归去除风格和行业影响 (使用numpy实现)
            try:
                # 添加常数项
                X_with_intercept = np.column_stack([np.ones(X_valid.shape[0]), X_valid])
                X_pred = np.column_stack([np.ones(X.shape[0]), X])

                # 最小二乘法求解
                coeffs = np.linalg.lstsq(X_with_intercept, y_valid, rcond=None)[0]
                y_pred = X_pred @ coeffs
                residual = y.flatten() - y_pred.flatten()
            except Exception as e:
                logger.warning(f"因子 {factor} 中性化失败: {e}")
                residual = y.flatten()

            neutralized[factor] = residual

        return neutralized

    def combine_factors(
        self,
        factor_scores: pd.DataFrame,
        weights: Optional[Dict[str, float]] = None,
        method: str = "score"
    ) -> pd.Series:
        """
        合成多因子

        Parameters
        ----------
        factor_scores : pd.DataFrame
            因子得分（已标准化和中性化）
        weights : Dict[str, float], optional
            因子权重
        method : str
            合成方法: 'score' (加权打分), 'regression' (回归法)

        Returns
        -------
        pd.Series
            合成因子值
        """
        if factor_scores.empty:
            return pd.Series(dtype=float)

        # 使用默认权重或传入权重
        if weights is None:
            weights = self.weights

        # 确保所有权重为正且和为1
        valid_factors = [f for f in weights.keys() if f in factor_scores.columns]
        if not valid_factors:
            logger.warning("没有有效的因子用于合成")
            return pd.Series(index=factor_scores.index, dtype=float)

        # 归一化权重
        weight_sum = sum(weights[f] for f in valid_factors)
        if weight_sum > 0:
            normalized_weights = {f: weights[f] / weight_sum for f in valid_factors}
        else:
            # 如果权重都为0，使用等权重
            normalized_weights = {f: 1.0 / len(valid_factors) for f in valid_factors}

        if method == "score":
            # 加权打分法
            combined = pd.Series(0, index=factor_scores.index)
            for factor, weight in normalized_weights.items():
                combined += factor_scores[factor] * weight

        elif method == "regression":
            # 回归法（需要未来收益率作为目标）
            # 这里简化处理，使用等权重
            logger.warning("回归法需要未来收益率数据，暂使用加权打分法")
            combined = pd.Series(0, index=factor_scores.index)
            for factor, weight in normalized_weights.items():
                combined += factor_scores[factor] * weight
        else:
            raise ValueError(f"不支持的合成方法: {method}")

        # 标准化最终合成因子
        mean = combined.mean()
        std = combined.std()
        if std > 0:
            combined = (combined - mean) / std

        return combined

    def calculate_ic(
        self,
        factor_values: pd.Series,
        forward_returns: pd.Series,
        method: str = "normal"
    ) -> float:
        """
        计算信息系数 (Information Coefficient)

        Parameters
        ----------
        factor_values : pd.Series
            因子值
        forward_returns : pd.Series
            未来收益率
        method : str
            IC计算方法: 'normal' (普通相关系数), 'rank' (秩相关系数)

        Returns
        -------
        float
            IC值
        """
        # 对齐数据
        aligned_data = pd.concat([factor_values, forward_returns], axis=1)
        aligned_data = aligned_data.dropna()

        if aligned_data.empty:
            return np.nan

        factor_vals = aligned_data.iloc[:, 0]
        returns = aligned_data.iloc[:, 1]

        if method == "normal":
            # Pearson相关系数
            ic = factor_vals.corr(returns)
        elif method == "rank":
            # Spearman秩相关系数
            ic = factor_vals.corr(returns, method="spearman")
        else:
            raise ValueError(f"不支持的IC计算方法: {method}")

        return ic

    def calculate_ir(
        self,
        ic_series: pd.Series
    ) -> float:
        """
        计算信息比率 (Information Ratio)

        Parameters
        ----------
        ic_series : pd.Series
            IC时间序列

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
            ir = mean_ic / std_ic * np.sqrt(252)  # 年化
        else:
            ir = np.nan

        return ir

    def factor_selection(
        self,
        factor_data: pd.DataFrame,
        forward_returns: pd.DataFrame,
        top_n: int = 10
    ) -> List[str]:
        """
        因子选择（基于IC排名）

        Parameters
        ----------
        factor_data : pd.DataFrame
            因子数据
        forward_returns : pd.DataFrame
            未来收益率
        top_n : int
            选择前N个因子

        Returns
        -------
        List[str]
            选中的因子列表
        """
        ic_results = {}

        for factor in factor_data.columns:
            ic = self.calculate_ic(factor_data[factor], forward_returns)
            ic_results[factor] = ic

        # 按IC绝对值排序
        sorted_factors = sorted(
            ic_results.items(),
            key=lambda x: abs(x[1]) if not np.isnan(x[1]) else 0,
            reverse=True
        )

        # 选择前N个因子
        selected = [factor for factor, ic in sorted_factors[:top_n]]

        logger.info(f"因子选择结果: {selected}")
        return selected

    def dynamic_weighting(
        self,
        factor_data: pd.DataFrame,
        forward_returns: pd.DataFrame,
        lookback_window: int = 60
    ) -> Dict[str, float]:
        """
        动态权重分配（基于滚动IC）

        Parameters
        ----------
        factor_data : pd.DataFrame
            因子数据
        forward_returns : pd.DataFrame
            未来收益率
        lookback_window : int
            回溯窗口

        Returns
        -------
        Dict[str, float]
            动态权重
        """
        weights = {}
        ic_values = {}

        for factor in factor_data.columns:
            # 计算滚动IC
            rolling_ic = pd.Series(index=factor_data.index, dtype=float)

            for i in range(lookback_window, len(factor_data)):
                start_idx = i - lookback_window
                end_idx = i

                factor_window = factor_data[factor].iloc[start_idx:end_idx]
                returns_window = forward_returns.iloc[start_idx:end_idx]

                ic = self.calculate_ic(factor_window, returns_window)
                rolling_ic.iloc[i] = ic

            # 使用最近期的IC作为权重依据
            recent_ic = rolling_ic.dropna().iloc[-1] if not rolling_ic.dropna().empty else 0
            ic_values[factor] = abs(recent_ic)

        # 基于IC绝对值分配权重
        total_ic = sum(ic_values.values())
        if total_ic > 0:
            weights = {factor: ic / total_ic for factor, ic in ic_values.items()}
        else:
            # 等权重
            weights = {factor: 1.0 / len(factor_data.columns) for factor in factor_data.columns}

        logger.info(f"动态权重: {weights}")
        return weights