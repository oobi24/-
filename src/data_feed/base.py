"""
数据获取基础抽象类
定义统一的数据接口规范
"""

from abc import ABC, abstractmethod
from datetime import datetime, date
from typing import List, Optional, Dict, Any
import pandas as pd
import logging

logger = logging.getLogger(__name__)


class DataSource(ABC):
    """数据源抽象基类"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.cache_enabled = config.get("cache_enabled", True)
        self.cache_days = config.get("cache_days", 30)

    @abstractmethod
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
            开始日期，格式 'YYYY-MM-DD'
        end_date : str
            结束日期，格式 'YYYY-MM-DD'
        adjust : str
            复权类型: 'qfq'(前复权), 'hfq'(后复权), 'None'(不复权)

        Returns
        -------
        pd.DataFrame
            日线数据，包含以下列：
            - date: 日期
            - open: 开盘价
            - high: 最高价
            - low: 最低价
            - close: 收盘价
            - volume: 成交量
            - amount: 成交额
            - turnover: 换手率
        """
        pass

    @abstractmethod
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
            报告期，如 '2023-12-31'

        Returns
        -------
        pd.DataFrame
            财务数据
        """
        pass

    @abstractmethod
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
        pass

    @abstractmethod
    def get_stock_basic(self) -> pd.DataFrame:
        """
        获取股票基本信息

        Returns
        -------
        pd.DataFrame
            股票基本信息，包含以下列：
            - symbol: 股票代码
            - name: 股票名称
            - industry: 行业
            - market: 市场（SH/SZ/BJ）
            - list_date: 上市日期
        """
        pass

    @abstractmethod
    def get_trade_calendar(self) -> pd.DataFrame:
        """
        获取交易日历

        Returns
        -------
        pd.DataFrame
            交易日历
        """
        pass


class DataFeed:
    """数据获取管理器"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.data_sources: Dict[str, DataSource] = {}
        self._init_data_sources()

    def _init_data_sources(self):
        """初始化数据源"""
        data_source_config = self.config.get("data_sources", {})

        # 初始化AkShare数据源
        if "akshare" in data_source_config:
            from .akshare_data import AkShareData
            self.data_sources["akshare"] = AkShareData(
                data_source_config["akshare"]
            )

        # 初始化Tushare数据源
        if "tushare" in data_source_config:
            from .tushare_data import TushareData
            self.data_sources["tushare"] = TushareData(
                data_source_config["tushare"]
            )

        # 初始化本地数据源
        from .local_data import LocalData
        storage_config = data_source_config.get("storage", {})
        self.data_sources["local"] = LocalData(storage_config)

        # 设置默认数据源
        default_source = data_source_config.get("default", "akshare")
        self.default_source = self.data_sources.get(default_source)

        if not self.default_source:
            logger.warning(f"默认数据源 {default_source} 未找到，使用第一个可用数据源")
            self.default_source = next(iter(self.data_sources.values()))

    def get_source(self, source_name: Optional[str] = None) -> DataSource:
        """
        获取数据源实例

        Parameters
        ----------
        source_name : str, optional
            数据源名称，如 'akshare', 'tushare', 'local'

        Returns
        -------
        DataSource
            数据源实例
        """
        if source_name is None:
            return self.default_source

        source = self.data_sources.get(source_name)
        if source is None:
            raise ValueError(f"数据源 {source_name} 未找到")

        return source

    def get_daily_data(
        self,
        symbol: str,
        start_date: str,
        end_date: str,
        adjust: str = "qfq",
        source: Optional[str] = None
    ) -> pd.DataFrame:
        """
        获取日线数据（统一接口）

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
        source : str, optional
            数据源名称

        Returns
        -------
        pd.DataFrame
            日线数据
        """
        data_source = self.get_source(source)

        # 尝试从本地缓存获取
        if self.config.get("data_sources", {}).get("storage", {}).get("cache_enabled", True):
            local_source = self.data_sources.get("local")
            if local_source:
                try:
                    cached_data = local_source.get_daily_data(
                        symbol, start_date, end_date, adjust
                    )
                    if not cached_data.empty:
                        logger.info(f"从缓存加载数据: {symbol}")
                        return cached_data
                except Exception as e:
                    logger.warning(f"缓存读取失败: {e}")

        # 从远程数据源获取
        data = data_source.get_daily_data(symbol, start_date, end_date, adjust)

        # 保存到本地缓存
        if not data.empty and self.config.get("data_sources", {}).get("storage", {}).get("cache_enabled", True):
            local_source = self.data_sources.get("local")
            if local_source:
                try:
                    local_source.save_daily_data(symbol, data, adjust)
                except Exception as e:
                    logger.warning(f"缓存保存失败: {e}")

        return data

    def get_financial_data(
        self,
        symbol: str,
        report_date: str,
        source: Optional[str] = None
    ) -> pd.DataFrame:
        """获取财务数据"""
        data_source = self.get_source(source)
        return data_source.get_financial_data(symbol, report_date)

    def get_index_data(
        self,
        index_code: str,
        start_date: str,
        end_date: str,
        source: Optional[str] = None
    ) -> pd.DataFrame:
        """获取指数数据"""
        data_source = self.get_source(source)
        return data_source.get_index_data(index_code, start_date, end_date)

    def get_stock_basic(self, source: Optional[str] = None) -> pd.DataFrame:
        """获取股票基本信息"""
        data_source = self.get_source(source)
        return data_source.get_stock_basic()

    def get_trade_calendar(self, source: Optional[str] = None) -> pd.DataFrame:
        """获取交易日历"""
        data_source = self.get_source(source)
        return data_source.get_trade_calendar()