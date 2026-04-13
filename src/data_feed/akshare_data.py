"""
AkShare数据源实现
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
import logging
import akshare as ak

from .base import DataSource

logger = logging.getLogger(__name__)


class AkShareData(DataSource):
    """AkShare数据源"""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.timeout = config.get("timeout", 30)
        self.retry_times = config.get("retry_times", 3)

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
            股票代码，如 '000001'（不需要市场后缀）
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
        try:
            # 解析股票代码和市场
            if "." in symbol:
                code, market = symbol.split(".")
                if market == "SZ":
                    code = f"sz{code}"
                elif market == "SH":
                    code = f"sh{code}"
                elif market == "BJ":
                    code = f"bj{code}"
            else:
                code = symbol

            # 根据复权类型选择接口
            if adjust == "qfq":
                # 前复权数据
                df = ak.stock_zh_a_hist(
                    symbol=code,
                    period="daily",
                    start_date=start_date,
                    end_date=end_date,
                    adjust="qfq"
                )
            elif adjust == "hfq":
                # 后复权数据
                df = ak.stock_zh_a_hist(
                    symbol=code,
                    period="daily",
                    start_date=start_date,
                    end_date=end_date,
                    adjust="hfq"
                )
            else:
                # 不复权数据
                df = ak.stock_zh_a_hist(
                    symbol=code,
                    period="daily",
                    start_date=start_date,
                    end_date=end_date,
                    adjust=""
                )

            # 重命名列以统一格式
            if not df.empty:
                # 检查列名并重命名
                column_mapping = {
                    "日期": "date",
                    "开盘": "open",
                    "收盘": "close",
                    "最高": "high",
                    "最低": "low",
                    "成交量": "volume",
                    "成交额": "amount",
                    "振幅": "amplitude",
                    "涨跌幅": "pct_chg",
                    "涨跌额": "change",
                    "换手率": "turnover"
                }

                # 只重命名存在的列
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

                # 计算前收盘价（用于涨跌幅验证）
                if "close" in df.columns:
                    df["pre_close"] = df["close"].shift(1)

            return df

        except Exception as e:
            logger.error(f"获取日线数据失败 {symbol}: {e}")
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
            报告期，格式 'YYYY-MM-DD'

        Returns
        -------
        pd.DataFrame
            财务数据
        """
        try:
            # 解析股票代码
            if "." in symbol:
                code = symbol.split(".")[0]
            else:
                code = symbol

            # 获取年报数据
            year = report_date[:4]

            # 获取利润表
            income_df = ak.stock_financial_report_sina(
                stock=code, symbol="利润表", date=year
            )

            # 获取资产负债表
            balance_df = ak.stock_financial_report_sina(
                stock=code, symbol="资产负债表", date=year
            )

            # 获取现金流量表
            cashflow_df = ak.stock_financial_report_sina(
                stock=code, symbol="现金流量表", date=year
            )

            # 合并财务数据
            financial_data = {}

            # 从利润表提取关键指标
            if not income_df.empty:
                income_dict = dict(zip(income_df["项目"], income_df[year]))
                financial_data.update({
                    "revenue": income_dict.get("营业收入", np.nan),
                    "net_profit": income_dict.get("净利润", np.nan),
                    "gross_profit": income_dict.get("营业利润", np.nan),
                    "operating_profit": income_dict.get("营业利润", np.nan),
                })

            # 从资产负债表提取关键指标
            if not balance_df.empty:
                balance_dict = dict(zip(balance_df["项目"], balance_df[year]))
                financial_data.update({
                    "total_assets": balance_dict.get("资产总计", np.nan),
                    "total_liabilities": balance_dict.get("负债合计", np.nan),
                    "equity": balance_dict.get("所有者权益合计", np.nan),
                    "current_assets": balance_dict.get("流动资产合计", np.nan),
                    "current_liabilities": balance_dict.get("流动负债合计", np.nan),
                })

            # 从现金流量表提取关键指标
            if not cashflow_df.empty:
                cashflow_dict = dict(zip(cashflow_df["项目"], cashflow_df[year]))
                financial_data.update({
                    "operating_cashflow": cashflow_dict.get(
                        "经营活动产生的现金流量净额", np.nan
                    ),
                    "investing_cashflow": cashflow_dict.get(
                        "投资活动产生的现金流量净额", np.nan
                    ),
                    "financing_cashflow": cashflow_dict.get(
                        "筹资活动产生的现金流量净额", np.nan
                    ),
                })

            # 计算财务比率
            if financial_data:
                # ROE
                if financial_data.get("net_profit") and financial_data.get("equity"):
                    financial_data["roe"] = (
                        financial_data["net_profit"] / financial_data["equity"]
                    )

                # 毛利率
                if financial_data.get("gross_profit") and financial_data.get("revenue"):
                    financial_data["gross_margin"] = (
                        financial_data["gross_profit"] / financial_data["revenue"]
                    )

                # 资产负债率
                if financial_data.get("total_liabilities") and financial_data.get("total_assets"):
                    financial_data["debt_to_assets"] = (
                        financial_data["total_liabilities"] / financial_data["total_assets"]
                    )

                # 流动比率
                if financial_data.get("current_assets") and financial_data.get("current_liabilities"):
                    financial_data["current_ratio"] = (
                        financial_data["current_assets"] / financial_data["current_liabilities"]
                    )

                # 经营现金流/营业收入
                if financial_data.get("operating_cashflow") and financial_data.get("revenue"):
                    financial_data["cashflow_to_revenue"] = (
                        financial_data["operating_cashflow"] / financial_data["revenue"]
                    )

            # 创建DataFrame
            df = pd.DataFrame([financial_data])
            df["symbol"] = symbol
            df["report_date"] = report_date

            return df

        except Exception as e:
            logger.error(f"获取财务数据失败 {symbol}: {e}")
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
            指数代码，如 '000001.SH'（上证指数）
        start_date : str
            开始日期
        end_date : str
            结束日期

        Returns
        -------
        pd.DataFrame
            指数数据
        """
        try:
            # 解析指数代码
            if "." in index_code:
                code = index_code.split(".")[0]
            else:
                code = index_code

            # 获取指数数据
            df = ak.stock_zh_index_daily(
                symbol=code,
                start_date=start_date,
                end_date=end_date
            )

            if not df.empty:
                # 重命名列
                column_mapping = {
                    "date": "date",
                    "open": "open",
                    "close": "close",
                    "high": "high",
                    "low": "low",
                    "volume": "volume"
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

            return df

        except Exception as e:
            logger.error(f"获取指数数据失败 {index_code}: {e}")
            return pd.DataFrame()

    def get_stock_basic(self) -> pd.DataFrame:
        """
        获取股票基本信息

        Returns
        -------
        pd.DataFrame
            股票基本信息
        """
        try:
            # 获取A股列表
            df = ak.stock_info_a_code_name()

            if not df.empty:
                # 重命名列
                df = df.rename(columns={
                    "code": "symbol",
                    "name": "name"
                })

                # 添加市场信息
                def get_market(code):
                    if code.startswith("6"):
                        return "SH"
                    elif code.startswith("0") or code.startswith("3"):
                        return "SZ"
                    elif code.startswith("8") or code.startswith("4"):
                        return "BJ"
                    else:
                        return ""

                df["market"] = df["symbol"].apply(get_market)
                df["symbol"] = df["symbol"] + "." + df["market"]

                # 获取更多详细信息
                try:
                    detail_df = ak.stock_info_sz_name_code(indicator="A股列表")
                    if not detail_df.empty:
                        # 合并详细信息
                        pass
                except:
                    pass

            return df

        except Exception as e:
            logger.error(f"获取股票基本信息失败: {e}")
            return pd.DataFrame()

    def get_trade_calendar(self) -> pd.DataFrame:
        """
        获取交易日历

        Returns
        -------
        pd.DataFrame
            交易日历
        """
        try:
            # 获取当前年份的交易日历
            current_year = datetime.now().year
            start_date = f"{current_year-1}-01-01"
            end_date = f"{current_year+1}-12-31"

            # AkShare的交易日历接口
            df = ak.tool_trade_date_hist_sina()

            if not df.empty:
                df = df.rename(columns={"trade_date": "date"})
                df["date"] = pd.to_datetime(df["date"])
                df["is_trading_day"] = True

                # 筛选日期范围
                df = df[
                    (df["date"] >= pd.Timestamp(start_date)) &
                    (df["date"] <= pd.Timestamp(end_date))
                ]

            return df

        except Exception as e:
            logger.error(f"获取交易日历失败: {e}")
            # 返回一个简单的交易日历（周一至周五）
            start_date = "2020-01-01"
            end_date = "2025-12-31"
            dates = pd.date_range(start=start_date, end=end_date, freq="B")
            df = pd.DataFrame({"date": dates})
            df["is_trading_day"] = True
            return df