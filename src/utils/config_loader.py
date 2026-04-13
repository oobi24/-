"""
配置加载工具
"""

import yaml
import json
import os
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


class ConfigLoader:
    """配置加载器"""

    @staticmethod
    def load_yaml(filepath: str) -> Dict[str, Any]:
        """
        加载YAML配置文件

        Parameters
        ----------
        filepath : str
            配置文件路径

        Returns
        -------
        Dict[str, Any]
            配置字典
        """
        if not os.path.exists(filepath):
            logger.error(f"配置文件不存在: {filepath}")
            raise FileNotFoundError(f"配置文件不存在: {filepath}")

        try:
            with open(filepath, "r", encoding="utf-8") as f:
                config = yaml.safe_load(f)

            logger.info(f"配置文件加载成功: {filepath}")
            return config or {}

        except yaml.YAMLError as e:
            logger.error(f"YAML解析错误: {filepath}, 错误: {e}")
            raise
        except Exception as e:
            logger.error(f"配置文件加载失败: {filepath}, 错误: {e}")
            raise

    @staticmethod
    def save_yaml(config: Dict[str, Any], filepath: str):
        """
        保存配置到YAML文件

        Parameters
        ----------
        config : Dict[str, Any]
            配置字典
        filepath : str
            文件路径
        """
        try:
            os.makedirs(os.path.dirname(filepath), exist_ok=True)

            with open(filepath, "w", encoding="utf-8") as f:
                yaml.dump(config, f, default_flow_style=False, allow_unicode=True)

            logger.info(f"配置文件保存成功: {filepath}")
        except Exception as e:
            logger.error(f"配置文件保存失败: {filepath}, 错误: {e}")
            raise

    @staticmethod
    def load_json(filepath: str) -> Dict[str, Any]:
        """
        加载JSON配置文件

        Parameters
        ----------
        filepath : str
            配置文件路径

        Returns
        -------
        Dict[str, Any]
            配置字典
        """
        if not os.path.exists(filepath):
            logger.error(f"JSON配置文件不存在: {filepath}")
            raise FileNotFoundError(f"JSON配置文件不存在: {filepath}")

        try:
            with open(filepath, "r", encoding="utf-8") as f:
                config = json.load(f)

            logger.info(f"JSON配置文件加载成功: {filepath}")
            return config

        except json.JSONDecodeError as e:
            logger.error(f"JSON解析错误: {filepath}, 错误: {e}")
            raise
        except Exception as e:
            logger.error(f"JSON配置文件加载失败: {filepath}, 错误: {e}")
            raise

    @staticmethod
    def save_json(config: Dict[str, Any], filepath: str, indent: int = 2):
        """
        保存配置到JSON文件

        Parameters
        ----------
        config : Dict[str, Any]
            配置字典
        filepath : str
            文件路径
        indent : int
            缩进空格数
        """
        try:
            os.makedirs(os.path.dirname(filepath), exist_ok=True)

            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(config, f, indent=indent, ensure_ascii=False)

            logger.info(f"JSON配置文件保存成功: {filepath}")
        except Exception as e:
            logger.error(f"JSON配置文件保存失败: {filepath}, 错误: {e}")
            raise

    @staticmethod
    def merge_configs(
        base_config: Dict[str, Any],
        override_config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        合并配置（深度合并）

        Parameters
        ----------
        base_config : Dict[str, Any]
            基础配置
        override_config : Dict[str, Any]
            覆盖配置

        Returns
        -------
        Dict[str, Any]
            合并后的配置
        """
        merged = base_config.copy()

        for key, value in override_config.items():
            if (key in merged and isinstance(merged[key], dict) and
                    isinstance(value, dict)):
                # 递归合并字典
                merged[key] = ConfigLoader.merge_configs(merged[key], value)
            else:
                # 直接覆盖
                merged[key] = value

        return merged

    @staticmethod
    def get_config_value(
        config: Dict[str, Any],
        key_path: str,
        default: Any = None
    ) -> Any:
        """
        通过路径获取配置值

        Parameters
        ----------
        config : Dict[str, Any]
            配置字典
        key_path : str
            键路径，如 'data_sources.akshare.timeout'
        default : Any
            默认值

        Returns
        -------
        Any
            配置值
        """
        keys = key_path.split(".")
        current = config

        try:
            for key in keys:
                if isinstance(current, dict) and key in current:
                    current = current[key]
                else:
                    return default
            return current
        except Exception:
            return default

    @staticmethod
    def set_config_value(
        config: Dict[str, Any],
        key_path: str,
        value: Any
    ):
        """
        通过路径设置配置值

        Parameters
        ----------
        config : Dict[str, Any]
            配置字典
        key_path : str
            键路径
        value : Any
            值
        """
        keys = key_path.split(".")
        current = config

        for i, key in enumerate(keys[:-1]):
            if key not in current or not isinstance(current[key], dict):
                current[key] = {}
            current = current[key]

        current[keys[-1]] = value

    @staticmethod
    def validate_config(config: Dict[str, Any], schema: Optional[Dict[str, Any]] = None) -> bool:
        """
        验证配置有效性

        Parameters
        ----------
        config : Dict[str, Any]
            配置字典
        schema : Dict[str, Any], optional
            配置模式

        Returns
        -------
        bool
            是否有效
        """
        # 这里可以实现配置验证逻辑
        # 简化处理，返回True
        return True

    @staticmethod
    def create_default_config() -> Dict[str, Any]:
        """
        创建默认配置

        Returns
        -------
        Dict[str, Any]
            默认配置
        """
        default_config = {
            "data_sources": {
                "default": "akshare",
                "akshare": {
                    "timeout": 30,
                    "retry_times": 3,
                },
                "tushare": {
                    "token": "",
                    "timeout": 30,
                },
                "storage": {
                    "raw_data": "data/raw",
                    "processed_data": "data/processed",
                    "cache_days": 30,
                    "cache_enabled": True,
                },
            },
            "backtest": {
                "initial_cash": 1000000,
                "commission": 0.00025,
                "stamp_tax": 0.001,
                "slippage": 0.001,
                "rules": {
                    "tplus1": True,
                    "limit_up_down": True,
                    "suspend_filter": True,
                },
            },
            "factors": {
                "windows": {
                    "short": 20,
                    "medium": 60,
                    "long": 120,
                },
                "standardization": {
                    "method": "zscore",
                    "winsorize": True,
                    "neutralization": True,
                },
                "multi_factor": {
                    "method": "score",
                    "weights": {
                        "value": 0.25,
                        "quality": 0.25,
                        "growth": 0.15,
                        "momentum": 0.20,
                        "volume_price": 0.15,
                    },
                },
            },
            "strategy": {
                "stock_pool": {
                    "min_roe": 0.10,
                    "min_gross_margin": 0.20,
                    "cash_flow_ratio": 0.10,
                    "max_pe": 50,
                    "min_dividend_yield": 0.02,
                    "min_market_cap": 3000000000,
                    "min_turnover": 10000000,
                },
                "timing": {
                    "volume_momentum": {
                        "min_volume_ratio": 1.5,
                        "breakout_h1": True,
                        "filter_downtrend": True,
                    },
                    "momentum": {
                        "lookback_days": 20,
                        "min_momentum": 0.05,
                    },
                },
            },
            "risk_control": {
                "position": {
                    "max_position_ratio": 0.95,
                    "max_single_position": 0.10,
                    "atr_multiplier": 0.01,
                },
                "stop_loss": {
                    "price_stop": 0.08,
                    "time_stop": 10,
                    "trailing_stop": 0.15,
                },
                "limits": {
                    "max_drawdown": 0.30,
                    "var_95": 0.05,
                },
            },
            "trading": {
                "broker": "qmt",
                "qmt": {
                    "path": "C:/国金证券QMT交易端/userdata_mini",
                    "account": "",
                },
                "trade_time": {
                    "morning_start": "09:30",
                    "morning_end": "11:30",
                    "afternoon_start": "13:00",
                    "afternoon_end": "15:00",
                },
                "order": {
                    "price_type": "limit",
                    "validity": "day",
                    "retry_times": 3,
                },
            },
            "logging": {
                "level": "INFO",
                "file": "logs/quant_system.log",
                "rotation": "1 day",
                "retention": "30 days",
            },
            "notification": {
                "enabled": False,
                "wechat_webhook": "",
                "email": {
                    "enabled": False,
                    "smtp_server": "",
                    "sender": "",
                    "receivers": [],
                },
            },
        }

        return default_config