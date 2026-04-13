"""
Tushare数据源实现
需要API token，如果未配置则跳过
"""

import pandas as pd
import numpy as np
from datetime import datetime
from typing import Dict, Any
import logging

from .base import DataSource

logger = logging.getLogger(__name__)


class TushareData(DataSource):
    """Tushare数据源"""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.token = config.get("token", "")
        self.timeout = config.get("timeout", 30)

        # 初始化Tushare API
        self._init_tushare()

    def _init_tushare(self):
        """初始化Tushare API"""
        if not self.token:
            logger.warning("Tushare token未配置，Tushare数据源将不可用")
            self.tushare = None
            return

        try:
            import tushare as ts
            ts.set_token(self.token)
            self.tushare = ts.pro_api()
            logger.info("Tushare数据源初始化成功")
        except Exception as e:
            logger.error(f"Tushare初始化失败: {e}")
            self.tushare = None

    def get_daily_data(
        self,
        symbol: str,
        start_date: str,
        end_date: str,
        adjust: str = "qfq"
    ) -> pd.DataFrame:
        """
        获取日线数据

        Parameters
        ----------
        symbol : str
            股票代码，如 '000001.SZ'
        start_date : str
            开始日期
        end_date : str
            结束日期
        adjust : str
            复权类型: 'qfq'(前复权), 'hfq'(后复权), 'None'(不复权)

        Returns
        -------
        pd.DataFrame
            日线数据
        """
        if self.tushare is None:
            logger.warning("Tushare未初始化，无法获取数据")
            return pd.DataFrame()

        try:
            # 解析股票代码
            if "." in symbol:
                ts_code = symbol
            else:
                # 尝试猜测市场
                if symbol.startswith("6"):
                    ts_code = f"{symbol}.SH"
                elif symbol.startswith("0") or symbol.startswith("3"):
                    ts_code = f"{symbol}.SZ"
                elif symbol.startswith("8") or symbol.startswith("4"):
                    ts_code = f"{symbol}.BJ"
                else:
                    ts_code = f"{symbol}.SH"

            # 根据复权类型选择接口
            if adjust == "qfq":
                # 前复权数据
                df = self.tushare.pro_bar(
                    ts_code=ts_code,
                    start_date=start_date,
                    end_date=end_date,
                    adj='qfq',
                    freq='D'
                )
            elif adjust == "hfq":
                # 后复权数据
                df = self.tushare.pro_bar(
                    ts_code=ts_code,
                    start_date=start_date,
                    end_date=end_date,
                    adj='hfq',
                    freq='D'
                )
            else:
                # 不复权数据
                df = self.tushare.daily(
                    ts_code=ts_code,
                    start_date=start_date,
                    end_date=end_date
                )

            if df is not None and not df.empty:
                # 重命名列以统一格式
                column_mapping = {
                    "trade_date": "date",
                    "open": "open",
                    "close": "close",
                    "high": "high",
                    "low": "low",
                    "vol": "volume",
                    "amount": "amount",
                    "pct_chg": "pct_chg",
                    "change": "change",
                    "turnover_rate": "turnover"
                }

                rename_dict = {
                    old: new for old, new in column_mapping.items()
                    if old in df.columns
                }
                df = df.rename(columns=rename_dict)

                # 确保日期列是datetime类型
                if "date" in df.columns:
                    df["date"] = pd.to_datetime(df["date"])

                # 按日期排序
                df = df.sort_values("date").reset_index(drop=True)

                # 添加股票代码列
                df["symbol"] = symbol

                # 计算前收盘价
                if "close" in df.columns:
                    df["pre_close"] = df["close"].shift(1)

            return df if df is not None else pd.DataFrame()

        except Exception as e:
            logger.error(f"Tushare获取日线数据失败 {symbol}: {e}")
            return pd.DataFrame()

    def get_financial_data(
        self,
        symbol: str,
        report_date: str
    ) -> pd.DataFrame:
        """
        获取财务数据

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
        if self.tushare is None:
            logger.warning("Tushare未初始化，无法获取数据")
            return pd.DataFrame()

        try:
            # 解析股票代码
            if "." in symbol:
                ts_code = symbol
            else:
                if symbol.startswith("6"):
                    ts_code = f"{symbol}.SH"
                else:
                    ts_code = f"{symbol}.SZ"

            # 获取财务数据
            # 这里需要根据Tushare的实际接口调整
            # 示例：获取利润表数据
            df = self.tushare.income(
                ts_code=ts_code,
                start_date=report_date,
                end_date=report_date
            )

            if df is not None and not df.empty:
                # 处理财务数据
                pass

            return df if df is not None else pd.DataFrame()

        except Exception as e:
            logger.error(f"Tushare获取财务数据失败 {symbol}: {e}")
            return pd.DataFrame()

    def get_index_data(
        self,
        index_code: str,
        start_date: str,
        end_date: str
    ) -> pd.DataFrame:
        """
        获取指数数据

        Parameters
        ----------
        index_code : str
            指数代码
        start_date : str
            开始日期
        end_date : str
            结束日期

        Returns
        -------
        pd.DataFrame
            指数数据
        """
        if self.tushare is None:
            logger.warning("Tushare未初始化，无法获取数据")
            return pd.DataFrame()

        try:
            # 获取指数数据
            df = self.tushare.index_daily(
                ts_code=index_code,
                start_date=start_date,
                end_date=end_date
            )

            if df is not None and not df.empty:
                # 重命名列
                column_mapping = {
                    "trade_date": "date",
                    "open": "open",
                    "close": "close",
                    "high": "high",
                    "low": "low",
                    "vol": "volume"
                }

                rename_dict = {
                    old: new for old, new in column_mapping.items()
                    if old in df.columns
                }
                df = df.rename(columns=rename_dict)

                # 确保日期列是datetime类型
                if "date" in df.columns:
                    df["date"] = pd.to_datetime(df["date"])

                # 按日期排序
                df = df.sort_values("date").reset_index(drop=True)

                # 添加指数代码列
                df["index_code"] = index_code

            return df if df is not None else pd.DataFrame()

        except Exception as e:
            logger.error(f"Tushare获取指数数据失败 {index_code}: {e}")
            return pd.DataFrame()

    def get_stock_basic(self) -> pd.DataFrame:
        """
        获取股票基本信息

        Returns
        -------
        pd.DataFrame
            股票基本信息
        """
        if self.tushare is None:
            logger.warning("Tushare未初始化，无法获取数据")
            return pd.DataFrame()

        try:
            # 获取股票基本信息
            df = self.tushare.stock_basic(
                exchange='',
                list_status='L',
                fields='ts_code,symbol,name,area,industry,market,list_date'
            )

            if df is not None and not df.empty:
                # 重命名列
                df = df.rename(columns={
                    "ts_code": "symbol",
                    "name": "name",
                    "industry": "industry",
                    "market": "market",
                    "list_date": "list_date"
                })

            return df if df is not None else pd.DataFrame()

        except Exception as e:
            logger.error(f"Tushare获取股票基本信息失败: {e}")
            return pd.DataFrame()

    def get_trade_calendar(self) -> pd.DataFrame:
        """
        获取交易日历

        Returns
        -------
        pd.DataFrame
            交易日历
        """
        if self.tushare is None:
            logger.warning("Tushare未初始化，无法获取数据")
            return pd.DataFrame()

        try:
            # 获取交易日历
            current_year = datetime.now().year
            start_date = f"{current_year-1}0101"
            end_date = f"{current_year+1}1231"

            df = self.tushare.trade_cal(
                exchange='SSE',
                start_date=start_date,
                end_date=end_date
            )

            if df is not None and not df.empty:
                df = df.rename(columns={"cal_date": "date"})
                df["date"] = pd.to_datetime(df["date"])
                df["is_trading_day"] = df["is_open"] == 1
                df = df[["date", "is_trading_day"]]

            return df if df is not None else pd.DataFrame()

        except Exception as e:
            logger.error(f"Tushare获取交易日历失败: {e}")
            return pd.DataFrame()