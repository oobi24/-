"""时间处理工具"""

import pandas as pd
from datetime import datetime, timedelta
from typing import List, Optional, Union


class TimeUtils:
    """时间工具类"""

    TRADE_DAYS_CACHE = None

    @staticmethod
    def is_trade_date(date: Union[str, datetime]) -> bool:
        """判断是否为交易日"""
        if isinstance(date, str):
            date = pd.Timestamp(date)

        # 周末检查
        if date.weekday() >= 5:
            return False

        # 这里可以添加节假日检查
        return True

    @staticmethod
    def get_trade_dates(start_date: str, end_date: str) -> pd.DatetimeIndex:
        """获取交易日序列"""
        dates = pd.date_range(start=start_date, end=end_date, freq='B')
        return dates

    @staticmethod
    def get_previous_trade_date(date: Union[str, datetime], n: int = 1) -> datetime:
        """获取前N个交易日"""
        if isinstance(date, str):
            date = pd.Timestamp(date)

        for _ in range(n):
            date -= timedelta(days=1)
            while not TimeUtils.is_trade_date(date):
                date -= timedelta(days=1)

        return date

    @staticmethod
    def get_next_trade_date(date: Union[str, datetime], n: int = 1) -> datetime:
        """获取后N个交易日"""
        if isinstance(date, str):
            date = pd.Timestamp(date)

        for _ in range(n):
            date += timedelta(days=1)
            while not TimeUtils.is_trade_date(date):
                date += timedelta(days=1)

        return date

    @staticmethod
    def format_date(date: Union[str, datetime], fmt: str = "%Y-%m-%d") -> str:
        """格式化日期"""
        if isinstance(date, str):
            date = pd.Timestamp(date)
        return date.strftime(fmt)

    @staticmethod
    def parse_date(date_str: str, fmt: str = "%Y-%m-%d") -> datetime:
        """解析日期字符串"""
        return datetime.strptime(date_str, fmt)
