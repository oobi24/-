"""
核心因子库与多因子引擎
系统内置符合A股市场特征的五大经典核心因子库：
1. 估值因子库 (Value Factors)
2. 质量与基本面因子库 (Quality Factors)
3. 成长因子库 (Growth Factors)
4. 动量与反转因子库 (Momentum & Reversal)
5. 量价与情绪因子库 (Volume & Price)
"""

from .base import Factor, FactorCalculator
from .value_factors import ValueFactors
from .quality_factors import QualityFactors
from .growth_factors import GrowthFactors
from .momentum_factors import MomentumFactors
from .volume_price_factors import VolumePriceFactors
from .multi_factor_engine import MultiFactorEngine
from .factor_utils import FactorUtils

__all__ = [
    "Factor",
    "FactorCalculator",
    "ValueFactors",
    "QualityFactors",
    "GrowthFactors",
    "MomentumFactors",
    "VolumePriceFactors",
    "MultiFactorEngine",
    "FactorUtils",
]