#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tushare数据源模块
用于从Tushare获取A股历史数据
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
import logging
import time
import os

# 禁用代理（Tushare不需要代理，代理可能导致连接问题）
os.environ['NO_PROXY'] = '*'
os.environ['no_proxy'] = '*'

logger = logging.getLogger(__name__)

# 尝试导入tushare
try:
    import tushare as ts
    _HAS_TUSHARE = True
except ImportError:
    _HAS_TUSHARE = False
    logger.warning("Tushare未安装，请运行: pip install tushare")


class TushareDataFeed:
    """Tushare数据获取类"""

    def __init__(self, token: str):
        """
        初始化Tushare数据接口

        Parameters
        ----------
        token : str
            Tushare API token
        """
        if not _HAS_TUSHARE:
            raise ImportError("请安装tushare: pip install tushare")

        self.token = token
        try:
            # 设置Tushare pro_api，增加超时
            self.pro = ts.pro_api(token, timeout=60)
            logger.info("Tushare数据接口初始化成功")
        except Exception as e:
            logger.error(f"Tushare API初始化失败: {e}")
            raise RuntimeError(f"api init error: {e}") from e

    def get_daily_data(
        self,
        symbol: str,
        start_date: str,
        end_date: str,
        adjust: str = "qfq"
    ) -> pd.DataFrame:
        """
        获取股票日线数据

        Parameters
        ----------
        symbol : str
            股票代码，如 '000001.SZ' 或 '000001'
        start_date : str
            开始日期，格式 '20230101' 或 '2023-01-01'
        end_date : str
            结束日期，格式同上
        adjust : str
            复权方式: 'qfq'(前复权), 'hfq'(后复权), None(不复权)

        Returns
        -------
        pd.DataFrame
            包含OHLCV的日线数据
        """
        # 标准化股票代码
        ts_code = self._format_symbol(symbol)

        # 标准化日期格式
        start = self._format_date(start_date)
        end = self._format_date(end_date)

        try:
            # 获取日线数据
            df = self.pro.daily(
                ts_code=ts_code,
                start_date=start,
                end_date=end
            )

            if df is None or df.empty:
                logger.warning(f"未获取到数据: {symbol}")
                return pd.DataFrame()

            # 处理数据
            df['trade_date'] = pd.to_datetime(df['trade_date'])
            df.set_index('trade_date', inplace=True)
            df.sort_index(inplace=True)

            # 重命名列
            df = df.rename(columns={
                'open': 'open',
                'high': 'high',
                'low': 'low',
                'close': 'close',
                'vol': 'volume',
                'amount': 'amount'
            })

            # 获取复权因子
            if adjust:
                df = self._adjust_price(df, ts_code, adjust)

            # 添加symbol列
            df['symbol'] = symbol

            logger.info(f"成功获取 {symbol} 数据，共 {len(df)} 条")
            return df

        except Exception as e:
            logger.error(f"获取数据失败 {symbol}: {e}")
            raise

    def get_stock_list(self, exchange: str = None) -> pd.DataFrame:
        """
        获取股票列表

        Parameters
        ----------
        exchange : str, optional
            交易所: 'SSE'(上交所), 'SZSE'(深交所)

        Returns
        -------
        pd.DataFrame
            股票列表
        """
        try:
            df = self.pro.stock_basic(
                exchange=exchange,
                list_status='L',
                fields='ts_code,symbol,name,area,industry,market,list_date'
            )
            return df
        except Exception as e:
            logger.error(f"获取股票列表失败: {e}")
            raise

    def search_stock(self, keyword: str) -> pd.DataFrame:
        """
        搜索股票（从Tushare获取全部列表）
        注意：此接口需要较高积分，120积分可能无法使用
        """
        try:
            df = self.pro.stock_basic(
                fields='ts_code,symbol,name,area,industry,market'
            )

            # 模糊匹配
            mask = (
                df['symbol'].str.contains(keyword) |
                df['name'].str.contains(keyword) |
                df['ts_code'].str.contains(keyword)
            )
            return df[mask]
        except Exception as e:
            logger.error(f"Tushare搜索股票失败: {e}")
            # 返回空DataFrame，让调用方使用本地列表
            return pd.DataFrame()

    def _format_symbol(self, symbol: str) -> str:
        """转换为Tushare格式的ts_code"""
        symbol = symbol.strip()

        # 已经是ts_code格式
        if '.' in symbol:
            return symbol.upper()

        # 根据代码规则判断交易所
        if symbol.startswith('6'):
            return f"{symbol}.SH"
        elif symbol.startswith('0') or symbol.startswith('3'):
            return f"{symbol}.SZ"
        elif symbol.startswith('8') or symbol.startswith('4'):
            return f"{symbol}.BJ"
        else:
            return f"{symbol}.SZ"

    def _format_date(self, date_str: str) -> str:
        """统一日期格式为YYYYMMDD"""
        date_str = date_str.replace('-', '').replace('/', '')
        return date_str

    def _adjust_price(
        self,
        df: pd.DataFrame,
        ts_code: str,
        adjust: str
    ) -> pd.DataFrame:
        """
        价格复权处理

        Parameters
        ----------
        df : pd.DataFrame
            原始日线数据
        ts_code : str
            Tushare代码
        adjust : str
            'qfq' 或 'hfq'

        Returns
        -------
        pd.DataFrame
            复权后的数据
        """
        try:
            # 获取复权因子
            adj_df = self.pro.adj_factor(ts_code=ts_code)

            if adj_df is None or adj_df.empty:
                logger.warning(f"未获取到复权因子: {ts_code}")
                return df

            adj_df['trade_date'] = pd.to_datetime(adj_df['trade_date'])
            adj_df.set_index('trade_date', inplace=True)

            # 合并数据
            df = df.merge(
                adj_df[['adj_factor']],
                left_index=True,
                right_index=True,
                how='left'
            )

            # 获取最新复权因子
            latest_adj = adj_df['adj_factor'].iloc[0]

            # 计算复权价格
            if adjust == 'qfq':
                # 前复权: 以最新价格为基准
                adj_ratio = df['adj_factor'] / latest_adj
            else:  # hfq
                # 后复权
                adj_ratio = df['adj_factor']

            for col in ['open', 'high', 'low', 'close']:
                df[col] = df[col] * adj_ratio

            # 删除复权因子列
            df = df.drop(columns=['adj_factor'])

            return df

        except Exception as e:
            logger.warning(f"复权处理失败: {e}")
            return df


# ============ 快速使用函数 ============

def create_feed_from_config(config: Dict[str, Any]) -> Optional[TushareDataFeed]:
    """从配置创建数据接口"""
    token = config.get('data_sources', {}).get('tushare', {}).get('token')
    if token:
        return TushareDataFeed(token)
    return None


def download_stock_data(
    symbol: str,
    start_date: str,
    end_date: str,
    token: str,
    save_path: Optional[str] = None
) -> pd.DataFrame:
    """
    下载股票数据并保存

    Parameters
    ----------
    symbol : str
        股票代码
    start_date : str
        开始日期
    end_date : str
        结束日期
    token : str
        Tushare token
    save_path : str, optional
        保存路径

    Returns
    -------
    pd.DataFrame
        股票数据
    """
    feed = TushareDataFeed(token)
    df = feed.get_daily_data(symbol, start_date, end_date)

    if save_path and not df.empty:
        df.to_csv(save_path)
        logger.info(f"数据已保存到: {save_path}")

    return df


# ============ 测试代码 ============

if __name__ == "__main__":
    import yaml

    # 加载配置
    with open('config.yaml', 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)

    token = config['data_sources']['tushare']['token']

    print("="*70)
    print("Tushare数据接口测试")
    print("="*70)

    feed = TushareDataFeed(token)

    # 测试搜索股票
    print("\n[1] 搜索股票 '平安':")
    stocks = feed.search_stock("平安")
    print(stocks.head())

    # 测试获取日线数据
    print("\n[2] 获取平安银行(000001.SZ)日线数据:")
    df = feed.get_daily_data(
        symbol="000001.SZ",
        start_date="2023-01-01",
        end_date="2023-12-31"
    )
    print(df.head())
    print(f"\n共获取 {len(df)} 条记录")

    # 保存数据
    output_dir = Path("data/tushare")
    output_dir.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_dir / "000001.SZ.csv")
    print(f"\n数据已保存到: {output_dir / '000001.SZ.csv'}")
