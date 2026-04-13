"""
因子计算基础抽象类
"""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
import pandas as pd
import numpy as np
import logging

logger = logging.getLogger(__name__)


class Factor(ABC):
    """因子基类"""

    def __init__(self, name: str, description: str = ""):
        self.name = name
        self.description = description
        self.required_data: List[str] = []

    @abstractmethod
    def calculate(self, data: pd.DataFrame) -> pd.Series:
        """
        计算因子值

        Parameters
        ----------
        data : pd.DataFrame
            输入数据，至少包含所需的数据列

        Returns
        -------
        pd.Series
            因子值序列，索引与data相同
        """
        pass

    def __str__(self):
        return f"Factor({self.name})"


class FactorCalculator:
    """因子计算器"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.factors: Dict[str, Factor] = {}
        self._init_factors()

    def _init_factors(self):
        """初始化所有因子"""
        # 估值因子
        from .value_factors import ValueFactors
        self.factors.update(ValueFactors.get_factors())

        # 质量因子
        from .quality_factors import QualityFactors
        self.factors.update(QualityFactors.get_factors())

        # 成长因子
        from .growth_factors import GrowthFactors
        self.factors.update(GrowthFactors.get_factors())

        # 动量因子
        from .momentum_factors import MomentumFactors
        self.factors.update(MomentumFactors.get_factors())

        # 量价因子
        from .volume_price_factors import VolumePriceFactors
        self.factors.update(VolumePriceFactors.get_factors())

    def calculate_factor(
        self,
        factor_name: str,
        data: pd.DataFrame,
        **kwargs
    ) -> pd.Series:
        """
        计算单个因子

        Parameters
        ----------
        factor_name : str
            因子名称
        data : pd.DataFrame
            输入数据
        **kwargs
            额外参数

        Returns
        -------
        pd.Series
            因子值
        """
        factor = self.factors.get(factor_name)
        if factor is None:
            raise ValueError(f"因子 {factor_name} 未找到")

        # 检查所需数据
        missing_cols = []
        for col in factor.required_data:
            if col not in data.columns:
                missing_cols.append(col)

        if missing_cols:
            raise ValueError(f"缺失所需数据列: {missing_cols}")

        try:
            result = factor.calculate(data, **kwargs)
            return result
        except Exception as e:
            logger.error(f"计算因子 {factor_name} 失败: {e}")
            raise

    def calculate_factors(
        self,
        factor_names: List[str],
        data: pd.DataFrame,
        **kwargs
    ) -> pd.DataFrame:
        """
        批量计算因子

        Parameters
        ----------
        factor_names : List[str]
            因子名称列表
        data : pd.DataFrame
            输入数据
        **kwargs
            额外参数

        Returns
        -------
        pd.DataFrame
            因子值DataFrame，每列一个因子
        """
        results = {}
        for factor_name in factor_names:
            try:
                factor_values = self.calculate_factor(factor_name, data, **kwargs)
                results[factor_name] = factor_values
            except Exception as e:
                logger.warning(f"跳过因子 {factor_name}: {e}")
                # 创建NaN序列作为占位符
                results[factor_name] = pd.Series(
                    np.nan, index=data.index, name=factor_name
                )

        return pd.DataFrame(results)

    def get_factor_info(self, factor_name: str) -> Dict[str, Any]:
        """
        获取因子信息

        Parameters
        ----------
        factor_name : str
            因子名称

        Returns
        -------
        Dict[str, Any]
            因子信息
        """
        factor = self.factors.get(factor_name)
        if factor is None:
            raise ValueError(f"因子 {factor_name} 未找到")

        return {
            "name": factor.name,
            "description": factor.description,
            "required_data": factor.required_data,
        }

    def list_factors(self) -> List[Dict[str, Any]]:
        """
        列出所有可用因子

        Returns
        -------
        List[Dict[str, Any]]
            因子信息列表
        """
        factors_info = []
        for name, factor in self.factors.items():
            factors_info.append({
                "name": name,
                "description": factor.description,
                "required_data": factor.required_data,
            })
        return factors_info

    def get_factor_categories(self) -> Dict[str, List[str]]:
        """
        按类别获取因子列表

        Returns
        -------
        Dict[str, List[str]]
            类别到因子列表的映射
        """
        categories = {
            "value": [],
            "quality": [],
            "growth": [],
            "momentum": [],
            "volume_price": [],
        }

        for name in self.factors.keys():
            if name.startswith("value_"):
                categories["value"].append(name)
            elif name.startswith("quality_"):
                categories["quality"].append(name)
            elif name.startswith("growth_"):
                categories["growth"].append(name)
            elif name.startswith("momentum_"):
                categories["momentum"].append(name)
            elif name.startswith("volume_"):
                categories["volume_price"].append(name)

        return categories