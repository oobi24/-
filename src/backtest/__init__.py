"""
Backtest System - based on Backtrader
"""

from .analyzer import PerformanceAnalyzer
from .data_feed import BacktestDataFeed

try:
    import backtrader
    _HAS_BACKTRADER = True
except ImportError:
    _HAS_BACKTRADER = False

if _HAS_BACKTRADER:
    from .backtest_engine import BacktestEngine
    from .strategy import BaseStrategy, FactorStrategy, VolumeMomentumStrategy
    from .broker import ABroker, AShareBroker
    from .execution import BacktestExecution
    __all__ = [
        "BacktestEngine",
        "BaseStrategy",
        "FactorStrategy",
        "VolumeMomentumStrategy",
        "ABroker",
        "AShareBroker",
        "PerformanceAnalyzer",
        "BacktestDataFeed",
        "BacktestExecution",
    ]
else:
    # Backtrader not installed - only export analyzer
    __all__ = [
        "PerformanceAnalyzer",
        "BacktestDataFeed",
    ]