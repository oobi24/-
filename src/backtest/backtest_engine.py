"""
回测引擎核心
基于Backtrader封装，适配A股规则
"""

import backtrader as bt
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
import logging
import warnings

from .broker import AShareBroker
from .data_feed import BacktestDataFeed
from .analyzer import PerformanceAnalyzer

logger = logging.getLogger(__name__)
warnings.filterwarnings("ignore")


class BacktestEngine:
    """回测引擎"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.cerebro = bt.Cerebro()

        # 初始化配置
        self._init_engine()

    def _init_engine(self):
        """初始化回测引擎"""
        backtest_config = self.config.get("backtest", {})

        # 设置初始资金
        initial_cash = backtest_config.get("initial_cash", 1000000)
        self.cerebro.broker.setcash(initial_cash)

        # 设置A股专用经纪人
        broker_config = {
            "commission": backtest_config.get("commission", 0.00025),
            "stamp_tax": backtest_config.get("stamp_tax", 0.001),
            "slippage": backtest_config.get("slippage", 0.001),
            "tplus1": backtest_config.get("rules", {}).get("tplus1", True),
            "limit_up_down": backtest_config.get("rules", {}).get("limit_up_down", True),
        }
        self.cerebro.broker = AShareBroker(**broker_config)

        # 设置分析器
        self.cerebro.addanalyzer(bt.analyzers.Returns, _name="returns")
        self.cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name="sharpe", riskfreerate=0.03)
        self.cerebro.addanalyzer(bt.analyzers.DrawDown, _name="drawdown")
        self.cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name="trades")
        self.cerebro.addanalyzer(bt.analyzers.PyFolio, _name="pyfolio")

        # 设置观察器
        self.cerebro.addobserver(bt.observers.Value)
        self.cerebro.addobserver(bt.observers.BuySell)
        self.cerebro.addobserver(bt.observers.DrawDown)

        logger.info("回测引擎初始化完成")

    def add_data(
        self,
        data: pd.DataFrame,
        symbol: str,
        timeframe: bt.TimeFrame = bt.TimeFrame.Days
    ):
        """
        添加数据到回测引擎

        Parameters
        ----------
        data : pd.DataFrame
            股票数据，必须包含以下列:
            - datetime: 日期时间
            - open: 开盘价
            - high: 最高价
            - low: 最低价
            - close: 收盘价
            - volume: 成交量
        symbol : str
            股票代码
        timeframe : bt.TimeFrame
            时间框架
        """
        # 确保数据列名正确
        required_columns = ["open", "high", "low", "close", "volume"]
        for col in required_columns:
            if col not in data.columns:
                raise ValueError(f"数据缺少必要列: {col}")

        # 创建Backtrader数据格式
        bt_data = bt.feeds.PandasData(
            dataname=data,
            datetime=None,  # 使用索引作为日期
            open="open",
            high="high",
            low="low",
            close="close",
            volume="volume",
            openinterest=None,
            name=symbol
        )

        self.cerebro.adddata(bt_data, name=symbol)
        logger.info(f"添加数据: {symbol}, 数据条数: {len(data)}")

    def add_strategy(
        self,
        strategy_class,
        **strategy_params
    ):
        """
        添加策略

        Parameters
        ----------
        strategy_class : class
            策略类
        **strategy_params
            策略参数
        """
        self.cerebro.addstrategy(strategy_class, **strategy_params)
        logger.info(f"添加策略: {strategy_class.__name__}")

    def run_backtest(
        self,
        start_date: str,
        end_date: str,
        plot: bool = False
    ) -> Dict[str, Any]:
        """
        运行回测

        Parameters
        ----------
        start_date : str
            开始日期
        end_date : str
            结束日期
        plot : bool
            是否绘制图表

        Returns
        -------
        Dict[str, Any]
            回测结果
        """
        # 设置回测时间范围
        self.cerebro.addsizer(bt.sizers.FixedSize, stake=100)

        # 运行回测
        logger.info(f"开始回测: {start_date} 到 {end_date}")
        results = self.cerebro.run()

        if not results:
            logger.error("回测无结果")
            return {}

        # 提取策略实例
        strategy = results[0]

        # 收集分析结果
        analysis_results = self._collect_analysis_results(strategy)

        # 获取交易记录
        trades = self._extract_trades(strategy)

        # 获取持仓记录
        positions = self._extract_positions(strategy)

        # 生成回测报告
        report = {
            "summary": analysis_results,
            "trades": trades,
            "positions": positions,
            "initial_cash": self.cerebro.broker.startingcash,
            "final_value": self.cerebro.broker.getvalue(),
            "total_return": (self.cerebro.broker.getvalue() - self.cerebro.broker.startingcash) / self.cerebro.broker.startingcash,
        }

        # 绘制图表
        if plot:
            try:
                self.cerebro.plot(style="candlestick", volume=True)
            except Exception as e:
                logger.warning(f"绘制图表失败: {e}")

        logger.info("回测完成")
        return report

    def _collect_analysis_results(self, strategy) -> Dict[str, Any]:
        """收集分析结果"""
        results = {}

        # 收益率分析
        returns_analyzer = strategy.analyzers.returns.get_analysis()
        results.update({
            "total_return": returns_analyzer.get("rtot", 0),
            "annual_return": returns_analyzer.get("rnorm", 0),
        })

        # 夏普比率
        sharpe_analyzer = strategy.analyzers.sharpe.get_analysis()
        results["sharpe_ratio"] = sharpe_analyzer.get("sharperatio", 0)

        # 最大回撤
        drawdown_analyzer = strategy.analyzers.drawdown.get_analysis()
        results.update({
            "max_drawdown": drawdown_analyzer.get("max", {}).get("drawdown", 0),
            "max_drawdown_period": drawdown_analyzer.get("max", {}).get("len", 0),
        })

        # 交易分析
        trade_analyzer = strategy.analyzers.trades.get_analysis()
        if trade_analyzer:
            results.update({
                "total_trades": trade_analyzer.get("total", {}).get("total", 0),
                "winning_trades": trade_analyzer.get("won", {}).get("total", 0),
                "losing_trades": trade_analyzer.get("lost", {}).get("total", 0),
                "win_rate": trade_analyzer.get("won", {}).get("total", 0) / max(trade_analyzer.get("total", {}).get("total", 1), 1),
                "avg_win": trade_analyzer.get("won", {}).get("pnl", {}).get("average", 0),
                "avg_loss": trade_analyzer.get("lost", {}).get("pnl", {}).get("average", 0),
                "profit_factor": trade_analyzer.get("won", {}).get("pnl", {}).get("total", 0) / max(abs(trade_analyzer.get("lost", {}).get("pnl", {}).get("total", 1)), 1),
            })

        # 计算卡玛比率
        if results.get("max_drawdown", 0) != 0:
            results["calmar_ratio"] = results.get("annual_return", 0) / results["max_drawdown"]
        else:
            results["calmar_ratio"] = 0

        return results

    def _extract_trades(self, strategy) -> List[Dict[str, Any]]:
        """提取交易记录"""
        trades = []

        # 从交易分析器中提取交易
        trade_analyzer = strategy.analyzers.trades.get_analysis()
        if not trade_analyzer or "trades" not in trade_analyzer:
            return trades

        for trade in trade_analyzer["trades"]:
            trade_info = {
                "entry_date": trade.entry.datetime.date() if hasattr(trade.entry, "datetime") else None,
                "exit_date": trade.exit.datetime.date() if hasattr(trade.exit, "datetime") else None,
                "entry_price": trade.entry.price,
                "exit_price": trade.exit.price,
                "size": trade.size,
                "pnl": trade.pnl,
                "pnl_percent": trade.pnlcomm / trade.entry.price * 100 if trade.entry.price != 0 else 0,
                "status": "win" if trade.pnl > 0 else "loss",
            }
            trades.append(trade_info)

        return trades

    def _extract_positions(self, strategy) -> List[Dict[str, Any]]:
        """提取持仓记录"""
        positions = []

        # 从经纪人处获取持仓信息
        for data in self.cerebro.datas:
            position = self.cerebro.broker.getposition(data)
            if position.size != 0:
                pos_info = {
                    "symbol": data._name,
                    "size": position.size,
                    "price": position.price,
                    "value": position.size * position.price,
                }
                positions.append(pos_info)

        return positions

    def optimize_strategy(
        self,
        strategy_class,
        param_ranges: Dict[str, List[Any]],
        start_date: str,
        end_date: str,
        max_cpus: int = 1
    ) -> pd.DataFrame:
        """
        策略参数优化

        Parameters
        ----------
        strategy_class : class
            策略类
        param_ranges : Dict[str, List[Any]]
            参数范围
        start_date : str
            开始日期
        end_date : str
            结束日期
        max_cpus : int
            最大CPU数量

        Returns
        -------
        pd.DataFrame
            优化结果
        """
        # 设置优化参数
        opt_params = []
        for param_name, param_values in param_ranges.items():
            opt_params.append(getattr(strategy_class.params, param_name, param_values))

        # 运行优化
        logger.info(f"开始策略优化: {strategy_class.__name__}")
        opt_results = self.cerebro.optstrategy(
            strategy_class,
            **param_ranges
        )

        # 运行优化回测
        self.cerebro.run(maxcpus=max_cpus)

        # 收集优化结果
        optimization_results = []

        for result in opt_results:
            for strategy_instance in result:
                # 获取参数组合
                params = {param: getattr(strategy_instance.params, param) for param in param_ranges.keys()}

                # 获取绩效指标
                analysis = self._collect_analysis_results(strategy_instance)

                # 组合结果
                result_entry = {**params, **analysis}
                optimization_results.append(result_entry)

        # 创建结果DataFrame
        results_df = pd.DataFrame(optimization_results)

        # 排序（按夏普比率降序）
        if "sharpe_ratio" in results_df.columns:
            results_df = results_df.sort_values("sharpe_ratio", ascending=False)

        logger.info(f"策略优化完成，共测试 {len(results_df)} 个参数组合")
        return results_df

    def run_walk_forward(
        self,
        strategy_class,
        strategy_params: Dict[str, Any],
        train_period: int = 252,  # 1年
        test_period: int = 63,    # 3个月
        step_size: int = 21,      # 1个月
        start_date: str = None,
        end_date: str = None
    ) -> Dict[str, Any]:
        """
        运行Walk-Forward分析

        Parameters
        ----------
        strategy_class : class
            策略类
        strategy_params : Dict[str, Any]
            策略参数
        train_period : int
            训练期长度（交易日）
        test_period : int
            测试期长度（交易日）
        step_size : int
            步长（交易日）
        start_date : str
            开始日期
        end_date : str
            结束日期

        Returns
        -------
        Dict[str, Any]
            Walk-Forward分析结果
        """
        # 实现Walk-Forward分析逻辑
        # 这里简化处理，实际需要更复杂的实现
        logger.info("Walk-Forward分析开始")

        # 收集各期结果
        results = []

        # 这里需要根据实际数据日期进行分期
        # 简化实现：运行一次回测
        self.add_strategy(strategy_class, **strategy_params)
        report = self.run_backtest(start_date, end_date, plot=False)

        results.append({
            "period": f"{start_date} 到 {end_date}",
            "report": report
        })

        wf_results = {
            "periods": results,
            "summary": {
                "avg_sharpe": np.mean([r["report"]["summary"].get("sharpe_ratio", 0) for r in results]),
                "avg_max_drawdown": np.mean([r["report"]["summary"].get("max_drawdown", 0) for r in results]),
                "avg_win_rate": np.mean([r["report"]["summary"].get("win_rate", 0) for r in results]),
            }
        }

        logger.info("Walk-Forward分析完成")
        return wf_results