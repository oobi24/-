"""
订单管理模块
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
import logging
import uuid

logger = logging.getLogger(__name__)


class OrderManager:
    """订单管理器"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.orders = {}  # order_id -> order info
        self.order_history = []

    def create_order(
        self,
        symbol: str,
        action: str,
        size: int,
        price_type: str = "limit",
        limit_price: Optional[float] = None,
        validity: str = "day",
        reason: str = "",
        **kwargs
    ) -> Dict[str, Any]:
        """
        创建订单

        Parameters
        ----------
        symbol : str
            股票代码
        action : str
            操作: 'buy', 'sell'
        size : int
            数量
        price_type : str
            价格类型: 'limit', 'market'
        limit_price : float, optional
            限价价格
        validity : str
            有效期: 'day', 'gtc'
        reason : str
            订单原因
        **kwargs
            其他参数

        Returns
        -------
        Dict[str, Any]
            订单信息
        """
        order_id = str(uuid.uuid4())[:8]

        order = {
            "order_id": order_id,
            "symbol": symbol,
            "action": action,
            "size": size,
            "price_type": price_type,
            "limit_price": limit_price,
            "validity": validity,
            "status": "pending",  # pending, submitted, filled, canceled, rejected
            "created_at": datetime.now(),
            "submitted_at": None,
            "filled_at": None,
            "filled_price": None,
            "filled_size": 0,
            "reason": reason,
            "error_message": None,
            **kwargs,
        }

        self.orders[order_id] = order
        logger.info(
            f"订单创建: {order_id}, "
            f"{symbol} {action} {size}股, "
            f"价格类型={price_type}, "
            f"原因={reason}"
        )

        return order

    def submit_order(self, order_id: str, broker_adapter) -> bool:
        """
        提交订单到券商

        Parameters
        ----------
        order_id : str
            订单ID
        broker_adapter : BrokerAdapter
            券商适配器

        Returns
        -------
        bool
            是否提交成功
        """
        if order_id not in self.orders:
            logger.error(f"订单不存在: {order_id}")
            return False

        order = self.orders[order_id]

        try:
            # 通过券商适配器提交订单
            result = broker_adapter.submit_order(order)

            if result.get("success", False):
                order["status"] = "submitted"
                order["submitted_at"] = datetime.now()
                order["broker_order_id"] = result.get("broker_order_id")
                logger.info(f"订单提交成功: {order_id}")
                return True
            else:
                order["status"] = "rejected"
                order["error_message"] = result.get("error", "提交失败")
                logger.error(f"订单提交失败: {order_id}, 错误: {order['error_message']}")
                return False

        except Exception as e:
            order["status"] = "rejected"
            order["error_message"] = str(e)
            logger.error(f"订单提交异常: {order_id}, 异常: {e}")
            return False

    def update_order_status(
        self,
        order_id: str,
        status: str,
        filled_price: Optional[float] = None,
        filled_size: Optional[int] = None
    ) -> bool:
        """
        更新订单状态

        Parameters
        ----------
        order_id : str
            订单ID
        status : str
            新状态
        filled_price : float, optional
            成交价格
        filled_size : int, optional
            成交数量

        Returns
        -------
        bool
            是否更新成功
        """
        if order_id not in self.orders:
            logger.error(f"订单不存在: {order_id}")
            return False

        order = self.orders[order_id]

        # 状态转换检查
        valid_transitions = {
            "pending": ["submitted", "canceled", "rejected"],
            "submitted": ["filled", "partially_filled", "canceled", "rejected"],
            "partially_filled": ["filled", "canceled"],
        }

        if status not in valid_transitions.get(order["status"], []):
            logger.warning(f"无效状态转换: {order['status']} -> {status}")
            return False

        # 更新状态
        order["status"] = status

        if status == "filled":
            order["filled_at"] = datetime.now()
            if filled_price is not None:
                order["filled_price"] = filled_price
            if filled_size is not None:
                order["filled_size"] = filled_size
            else:
                order["filled_size"] = order["size"]

        elif status == "partially_filled":
            if filled_price is not None:
                order["filled_price"] = filled_price
            if filled_size is not None:
                order["filled_size"] = filled_size

        elif status == "canceled":
            order["canceled_at"] = datetime.now()

        elif status == "rejected":
            order["rejected_at"] = datetime.now()

        # 如果订单完成，移动到历史记录
        if status in ["filled", "canceled", "rejected"]:
            self.order_history.append(order.copy())
            del self.orders[order_id]

        logger.info(f"订单状态更新: {order_id}, {order['status']} -> {status}")
        return True

    def cancel_order(self, order_id: str, broker_adapter) -> bool:
        """
        取消订单

        Parameters
        ----------
        order_id : str
            订单ID
        broker_adapter : BrokerAdapter
            券商适配器

        Returns
        -------
        bool
            是否取消成功
        """
        if order_id not in self.orders:
            logger.error(f"订单不存在: {order_id}")
            return False

        order = self.orders[order_id]

        if order["status"] not in ["pending", "submitted", "partially_filled"]:
            logger.warning(f"订单无法取消: {order_id}, 状态={order['status']}")
            return False

        try:
            # 通过券商适配器取消订单
            result = broker_adapter.cancel_order(order)

            if result.get("success", False):
                self.update_order_status(order_id, "canceled")
                logger.info(f"订单取消成功: {order_id}")
                return True
            else:
                logger.error(f"订单取消失败: {order_id}, 错误: {result.get('error', '未知错误')}")
                return False

        except Exception as e:
            logger.error(f"订单取消异常: {order_id}, 异常: {e}")
            return False

    def get_order(self, order_id: str) -> Optional[Dict[str, Any]]:
        """
        获取订单信息

        Parameters
        ----------
        order_id : str
            订单ID

        Returns
        -------
        Dict[str, Any], optional
            订单信息
        """
        return self.orders.get(order_id)

    def get_pending_orders(self) -> List[Dict[str, Any]]:
        """
        获取待处理订单

        Returns
        -------
        List[Dict[str, Any]]
            待处理订单列表
        """
        pending_orders = []
        for order in self.orders.values():
            if order["status"] in ["pending", "submitted", "partially_filled"]:
                pending_orders.append(order)
        return pending_orders

    def get_filled_orders(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """
        获取已成交订单

        Parameters
        ----------
        start_date : datetime, optional
            开始日期
        end_date : datetime, optional
            结束日期

        Returns
        -------
        List[Dict[str, Any]]
            已成交订单列表
        """
        filled_orders = []

        # 从历史记录中查找
        for order in self.order_history:
            if order["status"] == "filled":
                filled_at = order.get("filled_at")
                if filled_at:
                    if start_date and filled_at < start_date:
                        continue
                    if end_date and filled_at > end_date:
                        continue
                filled_orders.append(order)

        # 从当前订单中查找
        for order in self.orders.values():
            if order["status"] == "filled":
                filled_at = order.get("filled_at")
                if filled_at:
                    if start_date and filled_at < start_date:
                        continue
                    if end_date and filled_at > end_date:
                        continue
                filled_orders.append(order)

        return filled_orders

    def get_order_summary(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        获取订单摘要

        Parameters
        ----------
        start_date : datetime, optional
            开始日期
        end_date : datetime, optional
            结束日期

        Returns
        -------
        Dict[str, Any]
            订单摘要
        """
        all_orders = self.order_history + list(self.orders.values())

        if start_date or end_date:
            filtered_orders = []
            for order in all_orders:
                order_time = order.get("created_at")
                if order_time:
                    if start_date and order_time < start_date:
                        continue
                    if end_date and order_time > end_date:
                        continue
                filtered_orders.append(order)
            all_orders = filtered_orders

        # 计算统计
        total_orders = len(all_orders)
        filled_orders = len([o for o in all_orders if o["status"] == "filled"])
        canceled_orders = len([o for o in all_orders if o["status"] == "canceled"])
        rejected_orders = len([o for o in all_orders if o["status"] == "rejected"])
        pending_orders = len([o for o in all_orders if o["status"] in ["pending", "submitted", "partially_filled"]])

        # 计算成交统计
        filled_buy_orders = [o for o in all_orders if o["status"] == "filled" and o["action"] == "buy"]
        filled_sell_orders = [o for o in all_orders if o["status"] == "filled" and o["action"] == "sell"]

        total_buy_value = sum(o["filled_size"] * o["filled_price"] for o in filled_buy_orders if o["filled_price"] is not None)
        total_sell_value = sum(o["filled_size"] * o["filled_price"] for o in filled_sell_orders if o["filled_price"] is not None)
        total_buy_size = sum(o["filled_size"] for o in filled_buy_orders)
        total_sell_size = sum(o["filled_size"] for o in filled_sell_orders)

        summary = {
            "total_orders": total_orders,
            "filled_orders": filled_orders,
            "canceled_orders": canceled_orders,
            "rejected_orders": rejected_orders,
            "pending_orders": pending_orders,
            "fill_rate": filled_orders / total_orders if total_orders > 0 else 0,
            "buy_orders": len(filled_buy_orders),
            "sell_orders": len(filled_sell_orders),
            "total_buy_value": total_buy_value,
            "total_sell_value": total_sell_value,
            "total_buy_size": total_buy_size,
            "total_sell_size": total_sell_size,
            "net_flow": total_buy_value - total_sell_value,
        }

        return summary

    def check_order_validity(self):
        """检查订单有效性（清理过期订单）"""
        now = datetime.now()
        orders_to_cancel = []

        for order_id, order in self.orders.items():
            if order["status"] in ["pending", "submitted"]:
                # 检查日内订单是否过期
                if order["validity"] == "day":
                    created_date = order["created_at"].date()
                    if now.date() > created_date:
                        orders_to_cancel.append(order_id)

        # 取消过期订单
        for order_id in orders_to_cancel:
            logger.info(f"取消过期订单: {order_id}")
            order = self.orders[order_id]
            order["status"] = "canceled"
            order["error_message"] = "订单过期"
            self.order_history.append(order.copy())
            del self.orders[order_id]

        if orders_to_cancel:
            logger.info(f"清理了 {len(orders_to_cancel)} 个过期订单")

    def save_state(self, filepath: str):
        """保存订单状态"""
        import pickle
        state = {
            "orders": self.orders,
            "order_history": self.order_history,
            "timestamp": datetime.now(),
        }

        with open(filepath, "wb") as f:
            pickle.dump(state, f)

        logger.info(f"订单状态已保存: {filepath}")

    def load_state(self, filepath: str):
        """加载订单状态"""
        import pickle
        try:
            with open(filepath, "rb") as f:
                state = pickle.load(f)

            self.orders = state.get("orders", {})
            self.order_history = state.get("order_history", [])
            logger.info(f"订单状态已加载: {filepath}")
        except Exception as e:
            logger.error(f"加载订单状态失败: {e}")