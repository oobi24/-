"""数据验证工具"""

import pandas as pd
from typing import Dict, Any, List, Optional


class Validation:
    """验证工具类"""

    @staticmethod
    def validate_ohlcv_data(data: pd.DataFrame) -> tuple[bool, Optional[str]]:
        """验证OHLCV数据"""
        required_columns = ["open", "high", "low", "close", "volume"]

        # 检查列是否存在
        missing_cols = [col for col in required_columns if col not in data.columns]
        if missing_cols:
            return False, f"缺少列: {missing_cols}"

        # 检查数据类型
        numeric_cols = ["open", "high", "low", "close", "volume"]
        for col in numeric_cols:
            if not pd.api.types.is_numeric_dtype(data[col]):
                return False, f"列 {col} 不是数值类型"

        # 检查价格逻辑
        if (data["low"] > data["high"]).any():
            return False, "low > high"

        if (data["close"] > data["high"]).any():
            return False, "close > high"

        if (data["close"] < data["low"]).any():
            return False, "close < low"

        return True, None

    @staticmethod
    def validate_config(config: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        """验证配置"""
        # 检查必需配置项
        required_sections = ["data_sources", "backtest"]

        for section in required_sections:
            if section not in config:
                return False, f"缺少配置项: {section}"

        return True, None

    @staticmethod
    def validate_factor_values(factor_values: pd.Series) -> tuple[bool, Optional[str]]:
        """验证因子值"""
        if factor_values.empty:
            return False, "因子值为空"

        if factor_values.isna().all():
            return False, "因子值全为NaN"

        # 检查无穷值
        if factor_values.isin([float("inf"), float("-inf")]).any():
            return False, "因子值包含无穷值"

        return True, None
