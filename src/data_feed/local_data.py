"""
本地数据缓存管理
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import os
import json
import pickle
from typing import Dict, Any, Optional
import logging

from .base import DataSource

logger = logging.getLogger(__name__)


class LocalData(DataSource):
    """本地数据缓存"""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.raw_data_path = config.get("raw_data", "data/raw")
        self.processed_data_path = config.get("processed_data", "data/processed")
        self.cache_days = config.get("cache_days", 30)

        # 创建数据目录
        os.makedirs(self.raw_data_path, exist_ok=True)
        os.makedirs(self.processed_data_path, exist_ok=True)

    def _get_daily_data_path(
        self,
        symbol: str,
        adjust: str = "qfq"
    ) -> str:
        """
        获取日线数据文件路径

        Parameters
        ----------
        symbol : str
            股票代码
        adjust : str
            复权类型

        Returns
        -------
        str
            文件路径
        """
        # 清理股票代码中的特殊字符
        safe_symbol = symbol.replace(".", "_").replace("/", "_")
        filename = f"{safe_symbol}_{adjust}.parquet"
        return os.path.join(self.raw_data_path, "daily", filename)

    def get_daily_data(
        self,
        symbol: str,
        start_date: str,
        end_date: str,
        adjust: str = "qfq"
    ) -> pd.DataFrame:
        """
        从本地缓存获取日线数据

        Parameters
        ----------
        symbol : str
            股票代码
        start_date : str
            开始日期
        end_date : str
            结束日期
        adjust : str
            复权类型

        Returns
        -------
        pd.DataFrame
            日线数据，如果缓存不存在或数据不全返回空DataFrame
        """
        try:
            file_path = self._get_daily_data_path(symbol, adjust)

            if not os.path.exists(file_path):
                return pd.DataFrame()

            # 读取数据
            df = pd.read_parquet(file_path)

            if df.empty:
                return pd.DataFrame()

            # 确保日期列是datetime类型
            if "date" in df.columns:
                df["date"] = pd.to_datetime(df["date"])

            # 筛选日期范围
            start_dt = pd.Timestamp(start_date)
            end_dt = pd.Timestamp(end_date)

            mask = (df["date"] >= start_dt) & (df["date"] <= end_dt)
            df_filtered = df[mask].copy()

            # 检查数据是否完整
            if df_filtered.empty:
                return pd.DataFrame()

            # 检查数据连续性（可选）
            expected_dates = pd.date_range(start=start_dt, end=end_dt, freq="B")
            actual_dates = pd.DatetimeIndex(df_filtered["date"].unique())

            # 如果缺失数据超过20%，认为缓存不完整
            missing_ratio = 1 - len(actual_dates) / len(expected_dates)
            if missing_ratio > 0.2:
                logger.warning(f"缓存数据不完整: {symbol} 缺失比例 {missing_ratio:.2%}")
                return pd.DataFrame()

            return df_filtered

        except Exception as e:
            logger.error(f"读取本地缓存数据失败 {symbol}: {e}")
            return pd.DataFrame()

    def save_daily_data(
        self,
        symbol: str,
        data: pd.DataFrame,
        adjust: str = "qfq"
    ) -> bool:
        """
        保存日线数据到本地缓存

        Parameters
        ----------
        symbol : str
            股票代码
        data : pd.DataFrame
            日线数据
        adjust : str
            复权类型

        Returns
        -------
        bool
            是否保存成功
        """
        try:
            if data.empty:
                return False

            file_path = self._get_daily_data_path(symbol, adjust)
            file_dir = os.path.dirname(file_path)

            # 创建目录
            os.makedirs(file_dir, exist_ok=True)

            # 读取现有数据（如果存在）
            existing_data = pd.DataFrame()
            if os.path.exists(file_path):
                try:
                    existing_data = pd.read_parquet(file_path)
                    if "date" in existing_data.columns:
                        existing_data["date"] = pd.to_datetime(existing_data["date"])
                except Exception as e:
                    logger.warning(f"读取现有缓存文件失败: {e}")

            # 合并数据
            if not existing_data.empty:
                # 确保数据列一致
                common_columns = list(set(data.columns) & set(existing_data.columns))
                if common_columns:
                    # 合并并去重
                    combined = pd.concat([
                        existing_data[common_columns],
                        data[common_columns]
                    ])
                    combined = combined.drop_duplicates(subset=["date"], keep="last")
                    combined = combined.sort_values("date").reset_index(drop=True)
                else:
                    combined = data
            else:
                combined = data

            # 保存数据
            combined.to_parquet(file_path, index=False)
            logger.info(f"数据保存成功: {symbol} ({adjust}), 记录数: {len(combined)}")

            # 清理过期缓存（超过cache_days）
            self._clean_old_cache()

            return True

        except Exception as e:
            logger.error(f"保存本地缓存数据失败 {symbol}: {e}")
            return False

    def _clean_old_cache(self):
        """清理过期缓存"""
        try:
            cutoff_date = datetime.now() - timedelta(days=self.cache_days)
            cutoff_timestamp = pd.Timestamp(cutoff_date)

            daily_dir = os.path.join(self.raw_data_path, "daily")
            if not os.path.exists(daily_dir):
                return

            for filename in os.listdir(daily_dir):
                if filename.endswith(".parquet"):
                    file_path = os.path.join(daily_dir, filename)
                    try:
                        # 读取文件的最后修改时间
                        mtime = os.path.getmtime(file_path)
                        file_date = datetime.fromtimestamp(mtime)

                        if file_date < cutoff_date:
                            os.remove(file_path)
                            logger.info(f"清理过期缓存文件: {filename}")
                    except Exception as e:
                        logger.warning(f"清理缓存文件失败 {filename}: {e}")

        except Exception as e:
            logger.error(f"清理过期缓存失败: {e}")

    def get_financial_data(
        self,
        symbol: str,
        report_date: str
    ) -> pd.DataFrame:
        """
        获取财务数据（从本地缓存）

        Parameters
        ----------
        symbol : str
            股票代码
        report_date : str
            报告期

        Returns
        -------
        pd.DataFrame
            财务数据
        """
        try:
            safe_symbol = symbol.replace(".", "_").replace("/", "_")
            filename = f"{safe_symbol}_financial.parquet"
            file_path = os.path.join(self.processed_data_path, "financial", filename)

            if not os.path.exists(file_path):
                return pd.DataFrame()

            df = pd.read_parquet(file_path)

            if not df.empty and "report_date" in df.columns:
                # 筛选指定报告期的数据
                df_filtered = df[df["report_date"] == report_date].copy()
                return df_filtered

            return pd.DataFrame()

        except Exception as e:
            logger.error(f"读取本地财务数据失败 {symbol}: {e}")
            return pd.DataFrame()

    def save_financial_data(
        self,
        symbol: str,
        financial_data: pd.DataFrame
    ) -> bool:
        """
        保存财务数据到本地缓存

        Parameters
        ----------
        symbol : str
            股票代码
        financial_data : pd.DataFrame
            财务数据

        Returns
        -------
        bool
            是否保存成功
        """
        try:
            if financial_data.empty:
                return False

            safe_symbol = symbol.replace(".", "_").replace("/", "_")
            filename = f"{safe_symbol}_financial.parquet"
            file_dir = os.path.join(self.processed_data_path, "financial")
            file_path = os.path.join(file_dir, filename)

            os.makedirs(file_dir, exist_ok=True)

            # 读取现有数据（如果存在）
            existing_data = pd.DataFrame()
            if os.path.exists(file_path):
                try:
                    existing_data = pd.read_parquet(file_path)
                except Exception as e:
                    logger.warning(f"读取现有财务数据失败: {e}")

            # 合并数据
            if not existing_data.empty:
                # 按报告期合并
                combined = pd.concat([existing_data, financial_data])
                combined = combined.drop_duplicates(
                    subset=["symbol", "report_date"], keep="last"
                )
                combined = combined.sort_values("report_date").reset_index(drop=True)
            else:
                combined = financial_data

            # 保存数据
            combined.to_parquet(file_path, index=False)
            logger.info(f"财务数据保存成功: {symbol}, 记录数: {len(combined)}")

            return True

        except Exception as e:
            logger.error(f"保存财务数据失败 {symbol}: {e}")
            return False

    def get_index_data(
        self,
        index_code: str,
        start_date: str,
        end_date: str
    ) -> pd.DataFrame:
        """获取指数数据（从本地缓存）"""
        # 实现类似日线数据的缓存逻辑
        return pd.DataFrame()

    def get_stock_basic(self) -> pd.DataFrame:
        """获取股票基本信息（从本地缓存）"""
        try:
            file_path = os.path.join(self.processed_data_path, "stock_basic.parquet")

            if not os.path.exists(file_path):
                return pd.DataFrame()

            df = pd.read_parquet(file_path)
            return df

        except Exception as e:
            logger.error(f"读取股票基本信息失败: {e}")
            return pd.DataFrame()

    def save_stock_basic(self, stock_basic: pd.DataFrame) -> bool:
        """保存股票基本信息到本地缓存"""
        try:
            if stock_basic.empty:
                return False

            file_path = os.path.join(self.processed_data_path, "stock_basic.parquet")
            os.makedirs(os.path.dirname(file_path), exist_ok=True)

            stock_basic.to_parquet(file_path, index=False)
            logger.info(f"股票基本信息保存成功, 记录数: {len(stock_basic)}")

            return True

        except Exception as e:
            logger.error(f"保存股票基本信息失败: {e}")
            return False

    def get_trade_calendar(self) -> pd.DataFrame:
        """获取交易日历（从本地缓存）"""
        try:
            file_path = os.path.join(self.processed_data_path, "trade_calendar.parquet")

            if not os.path.exists(file_path):
                return pd.DataFrame()

            df = pd.read_parquet(file_path)
            return df

        except Exception as e:
            logger.error(f"读取交易日历失败: {e}")
            return pd.DataFrame()

    def save_trade_calendar(self, trade_calendar: pd.DataFrame) -> bool:
        """保存交易日历到本地缓存"""
        try:
            if trade_calendar.empty:
                return False

            file_path = os.path.join(self.processed_data_path, "trade_calendar.parquet")
            os.makedirs(os.path.dirname(file_path), exist_ok=True)

            trade_calendar.to_parquet(file_path, index=False)
            logger.info(f"交易日历保存成功, 记录数: {len(trade_calendar)}")

            return True

        except Exception as e:
            logger.error(f"保存交易日历失败: {e}")
            return False