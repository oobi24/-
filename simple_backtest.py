#!/usr/bin/env python3
"""
简化版回测引擎 - 不依赖backtrader
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
import logging

logger = logging.getLogger(__name__)


class SimpleBacktestEngine:
    """简化回测引擎"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.initial_cash = config.get("backtest", {}).get("initial_cash", 1000000)
        self.commission = config.get("backtest", {}).get("commission", 0.00025)
        self.stamp_tax = config.get("backtest", {}).get("stamp_tax", 0.001)

        # 状态
        self.cash = self.initial_cash
        self.positions = {}  # symbol -> {size, avg_price}
        self.trades = []
        self.daily_values = []

    def run_backtest(
        self,
        data: pd.DataFrame,
        strategy_func,
        strategy_params: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        运行回测

        Parameters
        ----------
        data : pd.DataFrame
            股票数据，需包含OHLCV列
        strategy_func : callable
            策略函数，接收(data, current_idx, params)返回signal
        strategy_params : dict
            策略参数

        Returns
        -------
        dict
            回测结果
        """
        if strategy_params is None:
            strategy_params = {}

        logger.info(f"开始回测，数据条数: {len(data)}")

        for i in range(60, len(data)):  # 从第60条开始（有MA数据）
            current_data = data.iloc[:i+1]
            current_price = data.iloc[i]["close"]
            current_date = data.index[i]

            # 获取策略信号
            signal = strategy_func(current_data, strategy_params)

            # 执行交易
            self._execute_signal(signal, current_price, current_date, data.iloc[i]["symbol"])

            # 记录每日净值
            portfolio_value = self._calculate_portfolio_value(current_price)
            self.daily_values.append({
                "date": current_date,
                "value": portfolio_value,
                "cash": self.cash,
                "position": self.positions.get(data.iloc[i]["symbol"], {}).get("size", 0)
            })

        # 计算绩效指标
        results = self._calculate_performance()
        results["trades"] = self.trades
        results["daily_values"] = pd.DataFrame(self.daily_values)

        return results

    def _execute_signal(self, signal: int, price: float, date: datetime, symbol: str):
        """执行交易信号"""
        position = self.positions.get(symbol, {"size": 0, "avg_price": 0})

        if signal == 1 and position["size"] == 0:  # 买入
            # 计算可买入数量（使用90%资金）
            available_cash = self.cash * 0.9
            size = int(available_cash / price / 100) * 100  # A股100股为单位

            if size >= 100:
                cost = size * price * (1 + self.commission)
                if cost <= self.cash:
                    self.cash -= cost
                    self.positions[symbol] = {
                        "size": size,
                        "avg_price": price
                    }
                    self.trades.append({
                        "date": date,
                        "action": "buy",
                        "price": price,
                        "size": size,
                        "cost": cost
                    })
                    logger.info(f"买入 {symbol}: {size}股 @ {price:.2f}")

        elif signal == -1 and position["size"] > 0:  # 卖出
            size = position["size"]
            revenue = size * price
            cost = revenue * (self.commission + self.stamp_tax)  # 卖出佣金+印花税
            net_revenue = revenue - cost

            self.cash += net_revenue
            del self.positions[symbol]

            # 计算盈亏
            buy_trade = next((t for t in reversed(self.trades) if t["action"] == "buy"), None)
            pnl = net_revenue - (buy_trade["cost"] if buy_trade else revenue)

            self.trades.append({
                "date": date,
                "action": "sell",
                "price": price,
                "size": size,
                "revenue": net_revenue,
                "pnl": pnl
            })
            logger.info(f"卖出 {symbol}: {size}股 @ {price:.2f}, 盈亏: {pnl:.2f}")

    def _calculate_portfolio_value(self, current_price: float) -> float:
        """计算组合价值"""
        position_value = sum(
            pos["size"] * current_price for pos in self.positions.values()
        )
        return self.cash + position_value

    def _calculate_performance(self) -> Dict[str, Any]:
        """计算绩效指标"""
        if not self.daily_values:
            return {}

        values_df = pd.DataFrame(self.daily_values)
        values_df.set_index("date", inplace=True)

        # 收益率
        total_return = (values_df["value"].iloc[-1] - self.initial_cash) / self.initial_cash

        # 年化收益率
        days = len(values_df)
        annual_return = (1 + total_return) ** (252 / days) - 1 if days > 0 else 0

        # 最大回撤
        cummax = values_df["value"].cummax()
        drawdown = (values_df["value"] - cummax) / cummax
        max_drawdown = drawdown.min()

        # 夏普比率（简化计算）
        daily_returns = values_df["value"].pct_change().dropna()
        sharpe_ratio = 0
        if len(daily_returns) > 1 and daily_returns.std() > 0:
            sharpe_ratio = (daily_returns.mean() / daily_returns.std()) * np.sqrt(252)

        # 胜率
        winning_trades = [t for t in self.trades if t.get("pnl", 0) > 0]
        win_rate = len(winning_trades) / len([t for t in self.trades if t["action"] == "sell"]) if self.trades else 0

        return {
            "initial_cash": self.initial_cash,
            "final_value": values_df["value"].iloc[-1],
            "total_return": total_return,
            "annual_return": annual_return,
            "max_drawdown": max_drawdown,
            "sharpe_ratio": sharpe_ratio,
            "total_trades": len([t for t in self.trades if t["action"] == "sell"]),
            "win_rate": win_rate,
            "winning_trades": len(winning_trades),
        }


# ============ 策略函数 ============

def volume_momentum_strategy(data: pd.DataFrame, params: Dict) -> int:
    """
    交易量动量策略
    信号: 1买入, -1卖出, 0持仓
    """
    if len(data) < 20:
        return 0

    # 计算指标
    volume_ma20 = data["volume"].rolling(20).mean().iloc[-1]
    current_volume = data["volume"].iloc[-1]
    volume_ratio = current_volume / volume_ma20 if volume_ma20 > 0 else 1

    price = data["close"].iloc[-1]
    prev_high = data["high"].iloc[-2]

    # 计算持仓天数（简化）
    position_days = params.get("position_days", 0)
    max_hold_days = params.get("max_hold_days", 10)

    # 买入条件：放量突破昨日高点
    if volume_ratio > 1.5 and price > prev_high:
        return 1

    # 卖出条件：时间止损或价格止损
    if position_days >= max_hold_days:
        return -1

    # 价格止损（8%）
    entry_price = params.get("entry_price", price * 1.1)
    if price < entry_price * 0.92:
        return -1

    return 0


def ma_cross_strategy(data: pd.DataFrame, params: Dict) -> int:
    """
    均线交叉策略
    """
    if len(data) < 30:
        return 0

    # 计算均线
    ma5 = data["close"].rolling(5).mean().iloc[-1]
    ma20 = data["close"].rolling(20).mean().iloc[-1]
    ma5_prev = data["close"].rolling(5).mean().iloc[-2]
    ma20_prev = data["close"].rolling(20).mean().iloc[-2]

    # 金叉买入
    if ma5 > ma20 and ma5_prev <= ma20_prev:
        return 1

    # 死叉卖出
    if ma5 < ma20 and ma5_prev >= ma20_prev:
        return -1

    return 0


# ============ 示例运行 ============

if __name__ == "__main__":
    import sys
    sys.path.insert(0, "src")

    from src.utils.config_loader import ConfigLoader

    print("=" * 70)
    print("Simple Backtest Demo")
    print("=" * 70)

    # 创建示例数据
    print("\n[1] Creating sample data...")
    np.random.seed(42)
    dates = pd.date_range(start="2023-01-01", end="2023-12-31", freq="B")
    n = len(dates)

    # 生成随机价格走势
    returns = np.random.randn(n) * 0.02
    prices = 10 * np.exp(np.cumsum(returns))

    data = pd.DataFrame({
        "open": prices * (1 + np.random.randn(n) * 0.01),
        "high": prices * (1 + np.abs(np.random.randn(n)) * 0.02),
        "low": prices * (1 - np.abs(np.random.randn(n)) * 0.02),
        "close": prices,
        "volume": np.random.randint(1000000, 10000000, n),
        "symbol": "000001.SZ"
    }, index=dates)

    print(f"    Data points: {len(data)}")
    print(f"    Date range: {data.index[0].date()} to {data.index[-1].date()}")

    # 运行回测
    print("\n[2] Running backtest (Volume Momentum Strategy)...")
    config = ConfigLoader.create_default_config()
    engine = SimpleBacktestEngine(config)

    results = engine.run_backtest(
        data,
        volume_momentum_strategy,
        strategy_params={"max_hold_days": 10}
    )

    # 打印结果
    print("\n" + "=" * 70)
    print("Backtest Results")
    print("=" * 70)
    print(f"Initial Cash:     {results['initial_cash']:>15,.0f}")
    print(f"Final Value:      {results['final_value']:>15,.0f}")
    print(f"Total Return:     {results['total_return']*100:>14.2f}%")
    print(f"Annual Return:    {results['annual_return']*100:>14.2f}%")
    print(f"Max Drawdown:     {results['max_drawdown']*100:>14.2f}%")
    print(f"Sharpe Ratio:     {results['sharpe_ratio']:>15.3f}")
    print(f"Total Trades:     {results['total_trades']:>15}")
    print(f"Win Rate:         {results['win_rate']*100:>14.2f}%")
    print("=" * 70)

    # 打印交易记录
    print("\n[3] Trade Records (last 5):")
    sell_trades = [t for t in results["trades"][-10:] if t["action"] == "sell"]
    for i, trade in enumerate(sell_trades[-5:], 1):
        print(f"    {i}. {trade['date'].strftime('%Y-%m-%d')} "
              f"Sell @ {trade['price']:.2f} "
              f"PnL: {trade.get('pnl', 0):+.2f}")

    print("\n[4] Daily Value Curve (last 5 days):")
    daily = results["daily_values"]
    for _, row in daily.tail(5).iterrows():
        print(f"    {row['date'].strftime('%Y-%m-%d')} "
              f"Value: {row['value']:>12,.0f} "
              f"Position: {row['position']:>8}")

    print("\n" + "=" * 70)
    print("Backtest completed!")
    print("=" * 70)
