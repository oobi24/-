"""
回测数据馈送
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import logging

logger = logging.getLogger(__name__)


class BacktestDataFeed:
    """回测数据馈送"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.data_cache = {}

    def load_data(
        self,
        symbol: str,
        start_date: str,
        end_date: str,
        adjust: str = "qfq"
    ) -> pd.DataFrame:
        """
        加载回测数据

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
            回测数据
        """
        cache_key = f"{symbol}_{start_date}_{end_date}_{adjust}"

        if cache_key in self.data_cache:
            logger.info(f"从缓存加载数据: {symbol}")
            return self.data_cache[cache_key].copy()

        # 这里应该从数据模块加载数据
        # 简化处理，创建示例数据
        logger.warning(f"数据加载未实现，创建示例数据: {symbol}")

        # 创建示例数据
        data = self._create_sample_data(symbol, start_date, end_date)

        # 缓存数据
        self.data_cache[cache_key] = data.copy()

        return data

    def _create_sample_data(
        self,
        symbol: str,
        start_date: str,
        end_date: str
    ) -> pd.DataFrame:
        """创建示例数据（用于测试）"""
        start = pd.Timestamp(start_date)
        end = pd.Timestamp(end_date)

        # 生成交易日序列
        dates = pd.date_range(start=start, end=end, freq="B")

        # 生成随机价格数据
        np.random.seed(42)  # 固定随机种子
        n_days = len(dates)

        # 基础价格
        base_price = 10.0

        # 生成随机收益率
        returns = np.random.randn(n_days) * 0.02  # 日波动率2%

        # 生成价格序列
        prices = base_price * np.exp(np.cumsum(returns))

        # 生成OHLCV数据
        data = pd.DataFrame({
            "date": dates,
            "open": prices * (1 + np.random.randn(n_days) * 0.01),
            "high": prices * (1 + np.abs(np.random.randn(n_days)) * 0.015),
            "low": prices * (1 - np.abs(np.random.randn(n_days)) * 0.015),
            "close": prices,
            "volume": np.random.randint(1000000, 10000000, n_days),
            "turnover": np.random.rand(n_days) * 0.05,  # 换手率0-5%
        })

        # 添加股票代码
        data["symbol"] = symbol

        # 设置日期索引
        data.set_index("date", inplace=True)

        logger.info(f"创建示例数据: {symbol}, 数据条数: {len(data)}")
        return data

    def load_multiple_data(
        self,
        symbols: List[str],
        start_date: str,
        end_date: str,
        adjust: str = "qfq"
    ) -> Dict[str, pd.DataFrame]:
        """
        加载多只股票数据

        Parameters
        ----------
        symbols : List[str]
            股票代码列表
        start_date : str
            开始日期
        end_date : str
            结束日期
        adjust : str
            复权类型

        Returns
        -------
        Dict[str, pd.DataFrame]
            股票数据字典
        """
        data_dict = {}

        for symbol in symbols:
            try:
                data = self.load_data(symbol, start_date, end_date, adjust)
                data_dict[symbol] = data
                logger.info(f"加载数据成功: {symbol}")
            except Exception as e:
                logger.error(f"加载数据失败 {symbol}: {e}")

        return data_dict

    def align_data(
        self,
        data_dict: Dict[str, pd.DataFrame]
    ) -> Dict[str, pd.DataFrame]:
        """
        对齐多只股票数据（统一日期索引）

        Parameters
        ----------
        data_dict : Dict[str, pd.DataFrame]
            股票数据字典

        Returns
        -------
        Dict[str, pd.DataFrame]
            对齐后的数据字典
        """
        if not data_dict:
            return {}

        # 获取所有日期索引的并集
        all_dates = pd.DatetimeIndex([])
        for data in data_dict.values():
            if hasattr(data.index, "union"):
                all_dates = all_dates.union(data.index)
            else:
                all_dates = all_dates.union(pd.DatetimeIndex(data.index))

        # 排序日期
        all_dates = all_dates.sort_values()

        # 对齐每只股票的数据
        aligned_dict = {}

        for symbol, data in data_dict.items():
            # 重新索引
            aligned_data = data.reindex(all_dates)

            # 前向填充缺失值（对于价格数据）
            # 注意：成交量等数据不应前向填充
            price_cols = ["open", "high", "low", "close"]
            for col in price_cols:
                if col in aligned_data.columns:
                    aligned_data[col] = aligned_data[col].ffill()

            # 其他列填充0或NaN
            for col in aligned_data.columns:
                if col not in price_cols and col != "symbol":
                    aligned_data[col] = aligned_data[col].fillna(0)

            aligned_dict[symbol] = aligned_data

        logger.info(f"数据对齐完成，统一日期范围: {all_dates[0]} 到 {all_dates[-1]}")
        return aligned_dict

    def add_technical_indicators(
        self,
        data: pd.DataFrame
    ) -> pd.DataFrame:
        """
        添加技术指标

        Parameters
        ----------
        data : pd.DataFrame
            原始数据

        Returns
        -------
        pd.DataFrame
            添加技术指标后的数据
        """
        if data.empty:
            return data

        df = data.copy()

        # 移动平均线
        df["sma_10"] = df["close"].rolling(window=10, min_periods=1).mean()
        df["sma_30"] = df["close"].rolling(window=30, min_periods=1).mean()
        df["sma_60"] = df["close"].rolling(window=60, min_periods=1).mean()

        # 指数移动平均线
        df["ema_12"] = df["close"].ewm(span=12, adjust=False).mean()
        df["ema_26"] = df["close"].ewm(span=26, adjust=False).mean()

        # MACD
        df["macd"] = df["ema_12"] - df["ema_26"]
        df["macd_signal"] = df["macd"].ewm(span=9, adjust=False).mean()
        df["macd_hist"] = df["macd"] - df["macd_signal"]

        # RSI
        delta = df["close"].diff()
        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)
        avg_gain = gain.rolling(window=14, min_periods=1).mean()
        avg_loss = loss.rolling(window=14, min_periods=1).mean()
        rs = avg_gain / avg_loss.replace(0, np.nan)
        df["rsi"] = 100 - (100 / (1 + rs))

        # 布林带
        df["bb_middle"] = df["close"].rolling(window=20, min_periods=1).mean()
        bb_std = df["close"].rolling(window=20, min_periods=1).std()
        df["bb_upper"] = df["bb_middle"] + 2 * bb_std
        df["bb_lower"] = df["bb_middle"] - 2 * bb_std

        # ATR
        high_low = df["high"] - df["low"]
        high_close = (df["high"] - df["close"].shift(1)).abs()
        low_close = (df["low"] - df["close"].shift(1)).abs()
        true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        df["atr"] = true_range.rolling(window=14, min_periods=1).mean()

        # 成交量指标
        df["volume_sma"] = df["volume"].rolling(window=20, min_periods=1).mean()
        df["volume_ratio"] = df["volume"] / df["volume_sma"]

        # 价格动量
        df["momentum_5"] = df["close"].pct_change(5)
        df["momentum_10"] = df["close"].pct_change(10)
        df["momentum_20"] = df["close"].pct_change(20)

        return df

    def add_fundamental_data(
        self,
        price_data: pd.DataFrame,
        fundamental_data: pd.DataFrame
    ) -> pd.DataFrame:
        """
        添加基本面数据

        Parameters
        ----------
        price_data : pd.DataFrame
            价格数据
        fundamental_data : pd.DataFrame
            基本面数据

        Returns
        -------
        pd.DataFrame
            合并后的数据
        """
        if fundamental_data.empty:
            return price_data

        # 确保基本面数据有日期索引
        if "date" in fundamental_data.columns:
            fundamental_data = fundamental_data.set_index("date")

        # 对齐索引
        aligned_fundamental = fundamental_data.reindex(price_data.index, method="ffill")

        # 合并数据
        merged_data = pd.concat([price_data, aligned_fundamental], axis=1)

        return merged_data

    def prepare_for_backtrader(
        self,
        data: pd.DataFrame
    ) -> pd.DataFrame:
        """
        准备数据用于Backtrader

        Parameters
        ----------
        data : pd.DataFrame
            原始数据

        Returns
        -------
        pd.DataFrame
            Backtrader格式数据
        """
        if data.empty:
            return data

        df = data.copy()

        # 重命名列以匹配Backtrader期望的格式
        column_mapping = {
            "open": "open",
            "high": "high",
            "low": "low",
            "close": "close",
            "volume": "volume",
            "turnover": "turnover",
        }

        # 只保留需要的列
        bt_columns = ["open", "high", "low", "close", "volume"]
        available_columns = [col for col in bt_columns if col in df.columns]

        # 创建Backtrader格式数据
        bt_data = df[available_columns].copy()

        # 确保没有NaN值
        bt_data = bt_data.fillna(method="ffill").fillna(0)

        # 重置索引（Backtrader使用整数索引）
        bt_data.reset_index(inplace=True)
        if "date" in bt_data.columns:
            bt_data.set_index("date", inplace=True)

        return bt_data