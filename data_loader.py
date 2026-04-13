#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
股票数据加载器
支持CSV文件和历史数据格式
"""

import pandas as pd
import numpy as np
from pathlib import Path
from typing import Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)


class StockDataLoader:
    """股票数据加载器"""

    @staticmethod
    def load_from_csv(filepath: str, symbol: Optional[str] = None) -> pd.DataFrame:
        """
        从CSV文件加载股票数据

        Parameters
        ----------
        filepath : str
            CSV文件路径
        symbol : str, optional
            股票代码，如果不提供则从文件名推断

        Returns
        -------
        pd.DataFrame
            股票数据，包含OHLCV列
        """
        try:
            # 读取CSV
            df = pd.read_csv(filepath)

            # 检查必需列
            required_cols = ['date', 'open', 'high', 'low', 'close', 'volume']
            missing_cols = [col for col in required_cols if col not in df.columns]

            if missing_cols:
                raise ValueError(f"CSV文件缺少必需列: {missing_cols}")

            # 转换日期
            df['date'] = pd.to_datetime(df['date'])
            df.set_index('date', inplace=True)
            df.sort_index(inplace=True)

            # 推断股票代码
            if symbol is None:
                symbol = Path(filepath).stem

            df['symbol'] = symbol

            logger.info(f"成功加载数据: {filepath}, 共{len(df)}条记录")
            return df

        except Exception as e:
            logger.error(f"加载CSV失败: {e}")
            raise

    @staticmethod
    def load_from_directory(data_dir: str) -> Dict[str, pd.DataFrame]:
        """
        从目录加载所有CSV文件

        Parameters
        ----------
        data_dir : str
            数据目录路径

        Returns
        -------
        Dict[str, pd.DataFrame]
            股票代码到数据的映射
        """
        data_dir = Path(data_dir)
        if not data_dir.exists():
            raise FileNotFoundError(f"目录不存在: {data_dir}")

        result = {}
        for csv_file in data_dir.glob("*.csv"):
            try:
                symbol = csv_file.stem
                df = StockDataLoader.load_from_csv(str(csv_file), symbol)
                result[symbol] = df
            except Exception as e:
                logger.warning(f"跳过文件 {csv_file}: {e}")

        logger.info(f"从目录加载了 {len(result)} 只股票的数据")
        return result

    @staticmethod
    def generate_sample_data(start_date: str = "2023-01-01",
                            end_date: str = "2023-12-31",
                            symbol: str = "000001.SZ",
                            seed: int = 42) -> pd.DataFrame:
        """
        生成示例股票数据（用于测试）

        Parameters
        ----------
        start_date : str
            开始日期
        end_date : str
            结束日期
        symbol : str
            股票代码
        seed : int
            随机种子

        Returns
        -------
        pd.DataFrame
            示例股票数据
        """
        np.random.seed(seed)
        dates = pd.date_range(start=start_date, end=end_date, freq="B")
        n = len(dates)

        # 生成随机 walk 价格
        returns = np.random.randn(n) * 0.02
        prices = 10 * np.exp(np.cumsum(returns))

        # 添加趋势和波动
        trend = np.linspace(0, 0.3, n)
        prices = prices * (1 + trend) + np.sin(np.linspace(0, 4*np.pi, n)) * 0.5

        df = pd.DataFrame({
            "open": prices * (1 + np.random.randn(n) * 0.008),
            "high": prices * (1 + np.abs(np.random.randn(n)) * 0.015),
            "low": prices * (1 - np.abs(np.random.randn(n)) * 0.015),
            "close": prices,
            "volume": np.random.randint(5000000, 15000000, n),
            "symbol": symbol
        }, index=dates)

        # 确保OHLC逻辑正确
        df['high'] = df[['open', 'high', 'close']].max(axis=1)
        df['low'] = df[['open', 'low', 'close']].min(axis=1)

        return df

    @staticmethod
    def save_to_csv(df: pd.DataFrame, filepath: str):
        """
        保存数据到CSV

        Parameters
        ----------
        df : pd.DataFrame
            股票数据
        filepath : str
            保存路径
        """
        df_copy = df.copy()
        df_copy.reset_index(inplace=True)
        df_copy.to_csv(filepath, index=False)
        logger.info(f"数据已保存到: {filepath}")

    @staticmethod
    def resample_data(df: pd.DataFrame, freq: str = 'W') -> pd.DataFrame:
        """
        重采样数据

        Parameters
        ----------
        df : pd.DataFrame
            原始数据
        freq : str
            频率: 'D'(日), 'W'(周), 'M'(月)

        Returns
        -------
        pd.DataFrame
            重采样后的数据
        """
        resampled = pd.DataFrame({
            'open': df['open'].resample(freq).first(),
            'high': df['high'].resample(freq).max(),
            'low': df['low'].resample(freq).min(),
            'close': df['close'].resample(freq).last(),
            'volume': df['volume'].resample(freq).sum(),
            'symbol': df['symbol'].resample(freq).last()
        }).dropna()

        return resampled

    @staticmethod
    def calculate_indicators(df: pd.DataFrame) -> pd.DataFrame:
        """
        计算常用技术指标

        Parameters
        ----------
        df : pd.DataFrame
            原始数据

        Returns
        -------
        pd.DataFrame
            添加了指标的数据
        """
        df = df.copy()

        # 移动平均线
        df['ma5'] = df['close'].rolling(5).mean()
        df['ma10'] = df['close'].rolling(10).mean()
        df['ma20'] = df['close'].rolling(20).mean()
        df['ma60'] = df['close'].rolling(60).mean()

        # MACD
        ema12 = df['close'].ewm(span=12).mean()
        ema26 = df['close'].ewm(span=26).mean()
        df['macd_dif'] = ema12 - ema26
        df['macd_dea'] = df['macd_dif'].ewm(span=9).mean()
        df['macd_hist'] = 2 * (df['macd_dif'] - df['macd_dea'])

        # RSI
        delta = df['close'].diff()
        gain = delta.where(delta > 0, 0).rolling(14).mean()
        loss = -delta.where(delta < 0, 0).rolling(14).mean()
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))

        # 布林带
        df['bb_middle'] = df['close'].rolling(20).mean()
        bb_std = df['close'].rolling(20).std()
        df['bb_upper'] = df['bb_middle'] + 2 * bb_std
        df['bb_lower'] = df['bb_middle'] - 2 * bb_std

        # ATR
        tr1 = df['high'] - df['low']
        tr2 = abs(df['high'] - df['close'].shift(1))
        tr3 = abs(df['low'] - df['close'].shift(1))
        df['atr'] = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1).rolling(14).mean()

        # 成交量指标
        df['volume_ma5'] = df['volume'].rolling(5).mean()
        df['volume_ma20'] = df['volume'].rolling(20).mean()
        df['volume_ratio'] = df['volume'] / df['volume_ma20']

        # 涨跌幅
        df['change_pct'] = df['close'].pct_change() * 100

        return df


# 测试代码
if __name__ == "__main__":
    # 生成示例数据
    print("生成示例股票数据...")
    df = StockDataLoader.generate_sample_data("2023-01-01", "2023-12-31", "000001.SZ")

    # 保存到CSV
    output_path = Path(__file__).parent / "data" / "sample"
    output_path.mkdir(parents=True, exist_ok=True)

    csv_file = output_path / "000001.SZ_generated.csv"
    StockDataLoader.save_to_csv(df, str(csv_file))
    print(f"已保存到: {csv_file}")

    # 计算指标
    df_with_indicators = StockDataLoader.calculate_indicators(df)
    print(f"\n数据 shape: {df_with_indicators.shape}")
    print(f"\n前5行数据:")
    print(df_with_indicators.head())
    print(f"\n技术指标:")
    print(df_with_indicators[['close', 'ma5', 'ma20', 'rsi', 'macd_dif']].tail())
