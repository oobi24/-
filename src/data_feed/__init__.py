"""
Data Feed Layer - handles all A-share data input
"""

from .base import DataFeed, DataSource
from .local_data import LocalData

# Optional data sources
try:
    from .akshare_data import AkShareData
except ImportError:
    AkShareData = None

try:
    from .tushare_data import TushareData
except ImportError:
    TushareData = None

__all__ = [
    "DataFeed",
    "DataSource",
    "LocalData",
]

if AkShareData:
    __all__.append("AkShareData")
if TushareData:
    __all__.append("TushareData")