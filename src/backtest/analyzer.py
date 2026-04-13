"""
回测绩效分析器
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
import logging
import matplotlib.pyplot as plt
import seaborn as sns

logger = logging.getLogger(__name__)


class PerformanceAnalyzer:
    """绩效分析器"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config

    def analyze(self, backtest_results: Dict[str, Any]) -> Dict[str, Any]:
        """
        分析回测结果

        Parameters
        ----------
        backtest_results : Dict[str, Any]
            回测结果

        Returns
        -------
        Dict[str, Any]
            分析结果
        """
        analysis = {}

        # 基础绩效指标
        analysis["basic_metrics"] = self._calculate_basic_metrics(backtest_results)

        # 风险指标
        analysis["risk_metrics"] = self._calculate_risk_metrics(backtest_results)

        # 交易分析
        analysis["trade_analysis"] = self._analyze_trades(backtest_results.get("trades", []))

        # 时间序列分析
        analysis["time_series"] = self._analyze_time_series(backtest_results)

        # 基准比较（如果有）
        analysis["benchmark_comparison"] = self._compare_with_benchmark(backtest_results)

        return analysis

    def _calculate_basic_metrics(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """计算基础绩效指标"""
        initial_cash = results.get("initial_cash", 0)
        final_value = results.get("final_value", 0)
        total_return = results.get("total_return", 0)

        # 计算年化收益率
        start_date = results.get("start_date")
        end_date = results.get("end_date")

        if start_date and end_date:
            if isinstance(start_date, str):
                start_date = datetime.strptime(start_date, "%Y-%m-%d")
            if isinstance(end_date, str):
                end_date = datetime.strptime(end_date, "%Y-%m-%d")

            days = (end_date - start_date).days
            years = days / 365.25
        else:
            # 默认假设1年
            years = 1.0

        if years > 0:
            cagr = (1 + total_return) ** (1 / years) - 1
        else:
            cagr = total_return

        # 从回测结果中获取其他指标
        summary = results.get("summary", {})

        basic_metrics = {
            "initial_cash": initial_cash,
            "final_value": final_value,
            "total_return": total_return,
            "cagr": cagr,
            "sharpe_ratio": summary.get("sharpe_ratio", 0),
            "calmar_ratio": summary.get("calmar_ratio", 0),
            "max_drawdown": summary.get("max_drawdown", 0),
            "win_rate": summary.get("win_rate", 0),
            "profit_factor": summary.get("profit_factor", 0),
            "total_trades": summary.get("total_trades", 0),
        }

        return basic_metrics

    def _calculate_risk_metrics(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """计算风险指标"""
        summary = results.get("summary", {})

        # 从交易数据计算更多风险指标
        trades = results.get("trades", [])

        if trades:
            returns = []
            for trade in trades:
                if "pnl_percent" in trade:
                    returns.append(trade["pnl_percent"] / 100)  # 转换为小数

            if returns:
                returns_series = pd.Series(returns)

                # 波动率
                volatility = returns_series.std() * np.sqrt(252)

                # 下行波动率
                negative_returns = returns_series[returns_series < 0]
                downside_volatility = negative_returns.std() * np.sqrt(252) if len(negative_returns) > 1 else 0

                # Sortino比率（假设无风险利率3%）
                risk_free_rate = 0.03
                excess_return = returns_series.mean() * 252 - risk_free_rate
                sortino_ratio = excess_return / downside_volatility if downside_volatility > 0 else 0

                # 最大连续亏损
                cumulative = returns_series.cumsum()
                underwater = cumulative - cumulative.expanding().max()
                max_consecutive_loss = underwater.min() if not underwater.empty else 0

                # VaR (95%)
                var_95 = returns_series.quantile(0.05)

                # CVaR (95%)
                cvar_95 = returns_series[returns_series <= var_95].mean()
            else:
                volatility = downside_volatility = sortino_ratio = 0
                max_consecutive_loss = var_95 = cvar_95 = 0
        else:
            volatility = downside_volatility = sortino_ratio = 0
            max_consecutive_loss = var_95 = cvar_95 = 0

        risk_metrics = {
            "volatility": volatility,
            "downside_volatility": downside_volatility,
            "sortino_ratio": sortino_ratio,
            "max_consecutive_loss": max_consecutive_loss,
            "var_95": var_95,
            "cvar_95": cvar_95,
            "max_drawdown_duration": summary.get("max_drawdown_period", 0),
        }

        return risk_metrics

    def _analyze_trades(self, trades: List[Dict[str, Any]]) -> Dict[str, Any]:
        """分析交易"""
        if not trades:
            return {"total_trades": 0}

        df_trades = pd.DataFrame(trades)

        # 计算交易统计
        total_trades = len(df_trades)
        winning_trades = len(df_trades[df_trades["status"] == "win"])
        losing_trades = len(df_trades[df_trades["status"] == "loss"])
        win_rate = winning_trades / total_trades if total_trades > 0 else 0

        # 计算盈亏统计
        if "pnl" in df_trades.columns:
            total_pnl = df_trades["pnl"].sum()
            avg_pnl = df_trades["pnl"].mean()
            std_pnl = df_trades["pnl"].std()

            winning_pnl = df_trades[df_trades["status"] == "win"]["pnl"]
            losing_pnl = df_trades[df_trades["status"] == "loss"]["pnl"]

            avg_win = winning_pnl.mean() if not winning_pnl.empty else 0
            avg_loss = losing_pnl.mean() if not losing_pnl.empty else 0
            max_win = winning_pnl.max() if not winning_pnl.empty else 0
            max_loss = losing_pnl.min() if not losing_pnl.empty else 0

            # 盈利因子
            gross_profit = winning_pnl.sum() if not winning_pnl.empty else 0
            gross_loss = abs(losing_pnl.sum()) if not losing_pnl.empty else 0
            profit_factor = gross_profit / gross_loss if gross_loss > 0 else np.inf
        else:
            total_pnl = avg_pnl = std_pnl = 0
            avg_win = avg_loss = max_win = max_loss = 0
            profit_factor = 0

        # 计算持仓时间
        if "entry_date" in df_trades.columns and "exit_date" in df_trades.columns:
            df_trades["entry_date"] = pd.to_datetime(df_trades["entry_date"])
            df_trades["exit_date"] = pd.to_datetime(df_trades["exit_date"])
            df_trades["holding_days"] = (df_trades["exit_date"] - df_trades["entry_date"]).dt.days

            avg_holding_days = df_trades["holding_days"].mean()
            median_holding_days = df_trades["holding_days"].median()
        else:
            avg_holding_days = median_holding_days = 0

        trade_analysis = {
            "total_trades": total_trades,
            "winning_trades": winning_trades,
            "losing_trades": losing_trades,
            "win_rate": win_rate,
            "total_pnl": total_pnl,
            "avg_pnl": avg_pnl,
            "std_pnl": std_pnl,
            "avg_win": avg_win,
            "avg_loss": avg_loss,
            "max_win": max_win,
            "max_loss": max_loss,
            "profit_factor": profit_factor,
            "avg_holding_days": avg_holding_days,
            "median_holding_days": median_holding_days,
        }

        return trade_analysis

    def _analyze_time_series(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """分析时间序列"""
        # 这里需要从回测引擎获取净值曲线数据
        # 简化处理，返回空字典
        return {}

    def _compare_with_benchmark(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """与基准比较"""
        # 这里需要基准数据（如沪深300）
        # 简化处理，返回空字典
        return {}

    def generate_report(self, analysis: Dict[str, Any]) -> str:
        """生成文本报告"""
        report_lines = []

        # 标题
        report_lines.append("=" * 80)
        report_lines.append("A股量化策略回测报告")
        report_lines.append("=" * 80)
        report_lines.append("")

        # 基础绩效指标
        basic_metrics = analysis.get("basic_metrics", {})
        report_lines.append("1. 基础绩效指标")
        report_lines.append("-" * 40)
        report_lines.append(f"初始资金: {basic_metrics.get('initial_cash', 0):,.2f}")
        report_lines.append(f"最终净值: {basic_metrics.get('final_value', 0):,.2f}")
        report_lines.append(f"总收益率: {basic_metrics.get('total_return', 0)*100:.2f}%")
        report_lines.append(f"年化收益率: {basic_metrics.get('cagr', 0)*100:.2f}%")
        report_lines.append(f"夏普比率: {basic_metrics.get('sharpe_ratio', 0):.3f}")
        report_lines.append(f"卡玛比率: {basic_metrics.get('calmar_ratio', 0):.3f}")
        report_lines.append(f"最大回撤: {basic_metrics.get('max_drawdown', 0)*100:.2f}%")
        report_lines.append("")

        # 风险指标
        risk_metrics = analysis.get("risk_metrics", {})
        report_lines.append("2. 风险指标")
        report_lines.append("-" * 40)
        report_lines.append(f"年化波动率: {risk_metrics.get('volatility', 0)*100:.2f}%")
        report_lines.append(f"下行波动率: {risk_metrics.get('downside_volatility', 0)*100:.2f}%")
        report_lines.append(f"索提诺比率: {risk_metrics.get('sortino_ratio', 0):.3f}")
        report_lines.append(f"最大连续亏损: {risk_metrics.get('max_consecutive_loss', 0)*100:.2f}%")
        report_lines.append(f"VaR (95%): {risk_metrics.get('var_95', 0)*100:.2f}%")
        report_lines.append(f"CVaR (95%): {risk_metrics.get('cvar_95', 0)*100:.2f}%")
        report_lines.append("")

        # 交易分析
        trade_analysis = analysis.get("trade_analysis", {})
        report_lines.append("3. 交易分析")
        report_lines.append("-" * 40)
        report_lines.append(f"总交易次数: {trade_analysis.get('total_trades', 0)}")
        report_lines.append(f"盈利交易: {trade_analysis.get('winning_trades', 0)}")
        report_lines.append(f"亏损交易: {trade_analysis.get('losing_trades', 0)}")
        report_lines.append(f"胜率: {trade_analysis.get('win_rate', 0)*100:.2f}%")
        report_lines.append(f"总盈亏: {trade_analysis.get('total_pnl', 0):,.2f}")
        report_lines.append(f"平均盈亏: {trade_analysis.get('avg_pnl', 0):,.2f}")
        report_lines.append(f"平均盈利: {trade_analysis.get('avg_win', 0):,.2f}")
        report_lines.append(f"平均亏损: {trade_analysis.get('avg_loss', 0):,.2f}")
        report_lines.append(f"盈利因子: {trade_analysis.get('profit_factor', 0):.3f}")
        report_lines.append(f"平均持仓天数: {trade_analysis.get('avg_holding_days', 0):.1f}")
        report_lines.append("")

        # 总结
        report_lines.append("4. 策略评价")
        report_lines.append("-" * 40)

        # 简单评价
        sharpe = basic_metrics.get("sharpe_ratio", 0)
        max_dd = basic_metrics.get("max_drawdown", 0)
        win_rate = trade_analysis.get("win_rate", 0)

        if sharpe > 1.5 and max_dd < 0.2 and win_rate > 0.5:
            evaluation = "优秀策略：高夏普比率，低回撤，高胜率"
        elif sharpe > 1.0 and max_dd < 0.3:
            evaluation = "良好策略：表现稳健"
        elif sharpe > 0.5:
            evaluation = "一般策略：有一定盈利能力"
        else:
            evaluation = "待优化策略：需要改进"

        report_lines.append(evaluation)
        report_lines.append("=" * 80)

        return "\n".join(report_lines)

    def plot_performance(
        self,
        analysis: Dict[str, Any],
        save_path: Optional[str] = None
    ):
        """绘制绩效图表"""
        # 这里实现图表绘制逻辑
        # 简化处理，仅输出消息
        logger.info("绩效图表绘制功能需要实现")

        if save_path:
            logger.info(f"图表将保存到: {save_path}")