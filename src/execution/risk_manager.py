"""
风险管理模块
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
import logging

logger = logging.getLogger(__name__)


class RiskManager:
    """风险管理器"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.risk_config = config.get("risk_control", {})

        # 仓位限制
        self.position_config = self.risk_config.get("position", {})
        self.stop_loss_config = self.risk_config.get("stop_loss", {})
        self.limits_config = self.risk_config.get("limits", {})

        # 风险状态
        self.risk_state = {
            "max_drawdown": 0,
            "current_drawdown": 0,
            "var_95": 0,
            "position_risk": 0,
            "violations": [],
        }

    def check_position_risk(
        self,
        symbol: str,
        size: int,
        price: float,
        current_positions: Dict[str, Dict[str, Any]],
        account_value: float
    ) -> Tuple[bool, str]:
        """
        检查仓位风险

        Parameters
        ----------
        symbol : str
            股票代码
        size : int
            计划交易数量
        price : float
            计划交易价格
        current_positions : Dict[str, Dict[str, Any]]
            当前持仓
        account_value : float
            账户总值

        Returns
        -------
        Tuple[bool, str]
            (是否通过, 拒绝原因)
        """
        # 计算计划交易价值
        trade_value = size * price

        # 1. 检查单笔交易仓位限制
        max_single_position_ratio = self.position_config.get("max_single_position", 0.1)
        if trade_value > account_value * max_single_position_ratio:
            return False, f"单笔交易超过仓位限制: {trade_value:.2f} > {account_value * max_single_position_ratio:.2f}"

        # 2. 检查总仓位限制
        total_position_value = sum(pos.get("value", 0) for pos in current_positions.values())
        max_position_ratio = self.position_config.get("max_position_ratio", 0.95)
        if total_position_value + trade_value > account_value * max_position_ratio:
            return False, f"总仓位超过限制: {total_position_value + trade_value:.2f} > {account_value * max_position_ratio:.2f}"

        # 3. 检查单只股票仓位限制
        if symbol in current_positions:
            current_position_value = current_positions[symbol].get("value", 0)
            if current_position_value + trade_value > account_value * max_single_position_ratio:
                return False, f"单只股票仓位超过限制: {current_position_value + trade_value:.2f} > {account_value * max_single_position_ratio:.2f}"

        # 4. 检查流动性风险（简化处理）
        # 假设交易价值不能超过日均成交额的1%
        # 实际中需要从市场数据获取

        return True, ""

    def calculate_position_size(
        self,
        symbol: str,
        price: float,
        atr: float,
        account_value: float,
        risk_per_trade: float = 0.01
    ) -> int:
        """
        基于风险计算仓位大小

        Parameters
        ----------
        symbol : str
            股票代码
        price : float
            当前价格
        atr : float
            平均真实波幅
        account_value : float
            账户总值
        risk_per_trade : float
            单笔交易风险比例

        Returns
        -------
        int
            建议仓位大小
        """
        # 计算风险资金
        risk_capital = account_value * risk_per_trade

        # 计算每份风险（基于ATR）
        if atr > 0:
            risk_per_share = atr * self.position_config.get("atr_multiplier", 2.0)
        else:
            # 如果没有ATR，使用价格百分比
            risk_per_share = price * 0.02  # 2%风险

        # 计算数量
        size = int(risk_capital / risk_per_share / price)

        # 应用仓位限制
        max_single_position_ratio = self.position_config.get("max_single_position", 0.1)
        max_size_by_capital = int(account_value * max_single_position_ratio / price)

        size = min(size, max_size_by_capital)

        # A股最小交易单位（100股）
        size = (size // 100) * 100

        # 确保至少100股
        size = max(size, 100)

        logger.debug(
            f"仓位计算: {symbol}, "
            f"价格={price:.2f}, "
            f"ATR={atr:.4f}, "
            f"建议数量={size}"
        )

        return size

    def check_stop_loss(
        self,
        symbol: str,
        entry_price: float,
        current_price: float,
        entry_date: datetime,
        current_date: datetime
    ) -> Tuple[bool, str]:
        """
        检查止损条件

        Parameters
        ----------
        symbol : str
            股票代码
        entry_price : float
            入场价格
        current_price : float
            当前价格
        entry_date : datetime
            入场日期
        current_date : datetime
            当前日期

        Returns
        -------
        Tuple[bool, str]
            (是否触发止损, 止损类型)
        """
        # 价格止损
        price_stop_ratio = self.stop_loss_config.get("price_stop", 0.08)
        price_loss = (entry_price - current_price) / entry_price

        if price_loss >= price_stop_ratio:
            return True, f"价格止损: 亏损{price_loss*100:.1f}% >= {price_stop_ratio*100:.1f}%"

        # 时间止损
        time_stop_days = self.stop_loss_config.get("time_stop", 10)
        holding_days = (current_date - entry_date).days

        if holding_days >= time_stop_days:
            # 检查是否脱离成本区
            if current_price <= entry_price * 1.02:  # 未上涨2%以上
                return True, f"时间止损: 持仓{holding_days}天未脱离成本区"

        # 移动止损
        trailing_stop_ratio = self.stop_loss_config.get("trailing_stop", 0.15)
        # 这里需要跟踪最高价，简化处理
        # 实际中需要维护每只股票的最高价跟踪

        return False, ""

    def check_portfolio_risk(
        self,
        portfolio_value_history: pd.Series,
        current_value: float
    ) -> Tuple[bool, str]:
        """
        检查组合风险

        Parameters
        ----------
        portfolio_value_history : pd.Series
            组合价值历史
        current_value : float
            当前组合价值

        Returns
        -------
        Tuple[bool, str]
            (是否触发风险限制, 风险类型)
        """
        if len(portfolio_value_history) < 2:
            return False, ""

        # 计算当前回撤
        peak = portfolio_value_history.max()
        current_drawdown = (peak - current_value) / peak

        # 更新风险状态
        self.risk_state["current_drawdown"] = current_drawdown
        self.risk_state["max_drawdown"] = max(
            self.risk_state["max_drawdown"], current_drawdown
        )

        # 检查最大回撤限制
        max_drawdown_limit = self.limits_config.get("max_drawdown", 0.3)
        if current_drawdown >= max_drawdown_limit:
            return True, f"组合回撤限制: {current_drawdown*100:.1f}% >= {max_drawdown_limit*100:.1f}%"

        # 计算VaR（简化版）
        returns = portfolio_value_history.pct_change().dropna()
        if len(returns) >= 20:
            var_95 = returns.quantile(0.05)
            self.risk_state["var_95"] = var_95

            var_limit = self.limits_config.get("var_95", 0.05)
            if var_95 <= -var_limit:
                return True, f"VaR限制: {var_95*100:.1f}% <= -{var_limit*100:.1f}%"

        return False, ""

    def calculate_var(
        self,
        portfolio_returns: pd.Series,
        confidence_level: float = 0.95
    ) -> float:
        """
        计算在险价值 (VaR)

        Parameters
        ----------
        portfolio_returns : pd.Series
            组合收益率序列
        confidence_level : float
            置信水平

        Returns
        -------
        float
            VaR值
        """
        if len(portfolio_returns) < 20:
            return 0

        # 历史模拟法
        var = portfolio_returns.quantile(1 - confidence_level)
        return var

    def calculate_cvar(
        self,
        portfolio_returns: pd.Series,
        confidence_level: float = 0.95
    ) -> float:
        """
        计算条件在险价值 (CVaR)

        Parameters
        ----------
        portfolio_returns : pd.Series
            组合收益率序列
        confidence_level : float
            置信水平

        Returns
        -------
        float
            CVaR值
        """
        if len(portfolio_returns) < 20:
            return 0

        var = self.calculate_var(portfolio_returns, confidence_level)
        cvar = portfolio_returns[portfolio_returns <= var].mean()

        return cvar

    def get_risk_report(self) -> Dict[str, Any]:
        """
        获取风险报告

        Returns
        -------
        Dict[str, Any]
            风险报告
        """
        report = {
            "risk_state": self.risk_state,
            "config": {
                "position": self.position_config,
                "stop_loss": self.stop_loss_config,
                "limits": self.limits_config,
            },
            "violations": self.risk_state["violations"],
        }

        return report

    def reset_risk_state(self):
        """重置风险状态"""
        self.risk_state = {
            "max_drawdown": 0,
            "current_drawdown": 0,
            "var_95": 0,
            "position_risk": 0,
            "violations": [],
        }
        logger.info("风险状态已重置")

    def log_violation(self, violation_type: str, details: str):
        """记录风险违规"""
        violation = {
            "timestamp": datetime.now(),
            "type": violation_type,
            "details": details,
        }
        self.risk_state["violations"].append(violation)
        logger.warning(f"风险违规: {violation_type} - {details}")