"""
回测执行模块
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
import logging

logger = logging.getLogger(__name__)


class BacktestExecution:
    """回测执行管理器"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config

    def run_single_strategy(
        self,
        strategy_class,
        strategy_params: Dict[str, Any],
        symbol: str,
        start_date: str,
        end_date: str,
        data_feed,
        plot: bool = False
    ) -> Dict[str, Any]:
        """
        运行单策略回测

        Parameters
        ----------
        strategy_class : class
            策略类
        strategy_params : Dict[str, Any]
            策略参数
        symbol : str
            股票代码
        start_date : str
            开始日期
        end_date : str
            结束日期
        data_feed : BacktestDataFeed
            数据馈送
        plot : bool
            是否绘制图表

        Returns
        -------
        Dict[str, Any]
            回测结果
        """
        logger.info(f"开始单策略回测: {symbol}")

        # 加载数据
        try:
            data = data_feed.load_data(symbol, start_date, end_date)
            if data.empty:
                logger.error(f"数据为空: {symbol}")
                return {}

            # 准备Backtrader格式数据
            bt_data = data_feed.prepare_for_backtrader(data)
        except Exception as e:
            logger.error(f"数据加载失败 {symbol}: {e}")
            return {}

        # 创建回测引擎
        from .backtest_engine import BacktestEngine
        engine = BacktestEngine(self.config)

        # 添加数据
        engine.add_data(bt_data, symbol)

        # 添加策略
        engine.add_strategy(strategy_class, **strategy_params)

        # 运行回测
        report = engine.run_backtest(start_date, end_date, plot=plot)

        # 添加额外信息
        report["symbol"] = symbol
        report["strategy"] = strategy_class.__name__
        report["strategy_params"] = strategy_params
        report["start_date"] = start_date
        report["end_date"] = end_date

        logger.info(f"单策略回测完成: {symbol}")
        return report

    def run_multi_strategy(
        self,
        strategy_class,
        strategy_params: Dict[str, Any],
        symbols: List[str],
        start_date: str,
        end_date: str,
        data_feed,
        plot: bool = False
    ) -> Dict[str, Any]:
        """
        运行多股票策略回测

        Parameters
        ----------
        strategy_class : class
            策略类
        strategy_params : Dict[str, Any]
            策略参数
        symbols : List[str]
            股票代码列表
        start_date : str
            开始日期
        end_date : str
            结束日期
        data_feed : BacktestDataFeed
            数据馈送
        plot : bool
            是否绘制图表

        Returns
        -------
        Dict[str, Any]
            回测结果
        """
        logger.info(f"开始多策略回测: {len(symbols)}只股票")

        results = {}

        for symbol in symbols:
            try:
                result = self.run_single_strategy(
                    strategy_class,
                    strategy_params,
                    symbol,
                    start_date,
                    end_date,
                    data_feed,
                    plot=False  # 单个不绘图
                )

                if result:
                    results[symbol] = result
                    logger.info(f"股票 {symbol} 回测完成")
                else:
                    logger.warning(f"股票 {symbol} 回测失败")

            except Exception as e:
                logger.error(f"股票 {symbol} 回测异常: {e}")

        # 汇总结果
        summary = self._summarize_multi_results(results)

        # 绘制汇总图表
        if plot and results:
            self._plot_multi_results(results)

        logger.info(f"多策略回测完成，成功: {len(results)}/{len(symbols)}")
        return {"results": results, "summary": summary}

    def _summarize_multi_results(
        self,
        results: Dict[str, Dict[str, Any]]
    ) -> Dict[str, Any]:
        """汇总多股票结果"""
        if not results:
            return {}

        # 收集所有股票的绩效指标
        all_returns = []
        all_sharpe = []
        all_max_dd = []
        all_win_rates = []

        for symbol, result in results.items():
            summary = result.get("summary", {})
            all_returns.append(summary.get("total_return", 0))
            all_sharpe.append(summary.get("sharpe_ratio", 0))
            all_max_dd.append(summary.get("max_drawdown", 0))
            all_win_rates.append(summary.get("win_rate", 0))

        # 计算统计量
        summary_stats = {
            "num_stocks": len(results),
            "avg_return": np.mean(all_returns) if all_returns else 0,
            "median_return": np.median(all_returns) if all_returns else 0,
            "std_return": np.std(all_returns) if all_returns else 0,
            "avg_sharpe": np.mean(all_sharpe) if all_sharpe else 0,
            "median_sharpe": np.median(all_sharpe) if all_sharpe else 0,
            "avg_max_dd": np.mean(all_max_dd) if all_max_dd else 0,
            "median_max_dd": np.median(all_max_dd) if all_max_dd else 0,
            "avg_win_rate": np.mean(all_win_rates) if all_win_rates else 0,
            "median_win_rate": np.median(all_win_rates) if all_win_rates else 0,
        }

        # 找出表现最好和最差的股票
        if results:
            returns_by_symbol = {
                symbol: result.get("summary", {}).get("total_return", 0)
                for symbol, result in results.items()
            }

            best_symbol = max(returns_by_symbol.items(), key=lambda x: x[1])
            worst_symbol = min(returns_by_symbol.items(), key=lambda x: x[1])

            summary_stats.update({
                "best_stock": {
                    "symbol": best_symbol[0],
                    "return": best_symbol[1],
                    "sharpe": results[best_symbol[0]].get("summary", {}).get("sharpe_ratio", 0),
                },
                "worst_stock": {
                    "symbol": worst_symbol[0],
                    "return": worst_symbol[1],
                    "sharpe": results[worst_symbol[0]].get("summary", {}).get("sharpe_ratio", 0),
                },
            })

        return summary_stats

    def _plot_multi_results(self, results: Dict[str, Dict[str, Any]]):
        """绘制多股票结果图表"""
        # 这里实现多股票结果的可视化
        # 简化处理，仅输出消息
        logger.info("多股票结果图表绘制功能需要实现")

    def run_factor_strategy(
        self,
        factor_scores: pd.DataFrame,
        symbols: List[str],
        start_date: str,
        end_date: str,
        data_feed,
        strategy_params: Optional[Dict[str, Any]] = None,
        plot: bool = False
    ) -> Dict[str, Any]:
        """
        运行因子策略回测

        Parameters
        ----------
        factor_scores : pd.DataFrame
            因子得分数据，索引为日期，列为股票代码
        symbols : List[str]
            股票代码列表
        start_date : str
            开始日期
        end_date : str
            结束日期
        data_feed : BacktestDataFeed
            数据馈送
        strategy_params : Dict[str, Any], optional
            策略参数
        plot : bool
            是否绘制图表

        Returns
        -------
        Dict[str, Any]
            回测结果
        """
        logger.info(f"开始因子策略回测: {len(symbols)}只股票")

        if strategy_params is None:
            strategy_params = {}

        from .strategy import FactorStrategy

        # 对每只股票运行回测
        results = {}

        for symbol in symbols:
            try:
                # 加载数据
                data = data_feed.load_data(symbol, start_date, end_date)
                if data.empty:
                    logger.warning(f"数据为空，跳过: {symbol}")
                    continue

                # 提取该股票的因子得分
                if symbol in factor_scores.columns:
                    symbol_factor_scores = factor_scores[symbol].reindex(data.index)
                else:
                    logger.warning(f"无因子得分，跳过: {symbol}")
                    continue

                # 准备数据
                bt_data = data_feed.prepare_for_backtrader(data)

                # 创建回测引擎
                from .backtest_engine import BacktestEngine
                engine = BacktestEngine(self.config)

                # 添加数据
                engine.add_data(bt_data, symbol)

                # 创建策略实例并设置因子得分
                def create_strategy_with_factors():
                    strategy = FactorStrategy(**strategy_params)
                    strategy.set_factor_scores(symbol_factor_scores)
                    return strategy

                # 添加策略
                engine.cerebro.addstrategy(create_strategy_with_factors)

                # 运行回测
                backtest_results = engine.cerebro.run()

                if backtest_results:
                    strategy_instance = backtest_results[0]

                    # 收集结果
                    report = {
                        "symbol": symbol,
                        "initial_cash": engine.cerebro.broker.startingcash,
                        "final_value": engine.cerebro.broker.getvalue(),
                        "total_return": (engine.cerebro.broker.getvalue() - engine.cerebro.broker.startingcash) / engine.cerebro.broker.startingcash,
                    }

                    results[symbol] = report
                    logger.info(f"股票 {symbol} 因子策略回测完成")

            except Exception as e:
                logger.error(f"股票 {symbol} 因子策略回测异常: {e}")

        # 汇总结果
        summary = self._summarize_multi_results(results)

        # 绘制因子分组收益
        if plot and results:
            self._plot_factor_results(results, factor_scores)

        logger.info(f"因子策略回测完成，成功: {len(results)}/{len(symbols)}")
        return {"results": results, "summary": summary}

    def _plot_factor_results(
        self,
        results: Dict[str, Dict[str, Any]],
        factor_scores: pd.DataFrame
    ):
        """绘制因子策略结果图表"""
        # 这里实现因子策略结果的可视化
        logger.info("因子策略结果图表绘制功能需要实现")

    def run_walk_forward_analysis(
        self,
        strategy_class,
        strategy_params: Dict[str, Any],
        symbol: str,
        start_date: str,
        end_date: str,
        data_feed,
        train_period: int = 252,
        test_period: int = 63,
        step_size: int = 21
    ) -> Dict[str, Any]:
        """
        运行Walk-Forward分析

        Parameters
        ----------
        strategy_class : class
            策略类
        strategy_params : Dict[str, Any]
            策略参数
        symbol : str
            股票代码
        start_date : str
            开始日期
        end_date : str
            结束日期
        data_feed : BacktestDataFeed
            数据馈送
        train_period : int
            训练期长度
        test_period : int
            测试期长度
        step_size : int
            步长

        Returns
        -------
        Dict[str, Any]
            Walk-Forward分析结果
        """
        logger.info(f"开始Walk-Forward分析: {symbol}")

        # 这里需要实现完整的Walk-Forward分析逻辑
        # 简化处理，返回基本结构

        wf_results = {
            "symbol": symbol,
            "train_period": train_period,
            "test_period": test_period,
            "step_size": step_size,
            "periods": [],
            "summary": {},
        }

        logger.info("Walk-Forward分析完成")
        return wf_results

    def generate_report(
        self,
        results: Dict[str, Any],
        report_type: str = "detailed"
    ) -> str:
        """
        生成回测报告

        Parameters
        ----------
        results : Dict[str, Any]
            回测结果
        report_type : str
            报告类型: 'detailed', 'summary', 'brief'

        Returns
        -------
        str
            报告文本
        """
        from .analyzer import PerformanceAnalyzer

        analyzer = PerformanceAnalyzer(self.config)

        if "summary" in results:
            # 多股票结果
            analysis = analyzer.analyze(results.get("results", {}))
        else:
            # 单股票结果
            analysis = analyzer.analyze(results)

        report = analyzer.generate_report(analysis)
        return report