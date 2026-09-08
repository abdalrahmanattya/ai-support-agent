"""Validated mock order API used by the AgentCore Gateway API target."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from support_agent.schemas import CustomerOrders, CustomerProfile, Order, ToolError


def _orders() -> dict[str, dict]:
    today = datetime.now(UTC).date()
    return {
        "ORD-001": {
            "order_id": "ORD-001",
            "customer_id": "CUST-123",
            "status": "SHIPPED",
            "items": [{"name": "AeroSound ANC Headphones", "quantity": 1, "unit_price": "129.99"}],
            "total": "129.99",
            "tracking_number": "TRK987654321",
            "carrier": "UPS",
            "estimated_delivery": str(today + timedelta(days=2)),
        },
        "ORD-002": {
            "order_id": "ORD-002",
            "customer_id": "CUST-123",
            "status": "DELIVERED",
            "items": [{"name": "LumaRead E-Reader", "quantity": 1, "unit_price": "149.99"}],
            "total": "149.99",
            "tracking_number": "TRK123456789",
            "carrier": "USPS",
            "delivered_date": str(today - timedelta(days=3)),
        },
        "ORD-003": {
            "order_id": "ORD-003",
            "customer_id": "CUST-456",
            "status": "PROCESSING",
            "items": [
                {"name": "HomeHub Mini", "quantity": 2, "unit_price": "49.99"},
                {"name": "Matter Smart Plug", "quantity": 1, "unit_price": "24.99"},
            ],
            "total": "124.97",
            "estimated_delivery": str(today + timedelta(days=5)),
        },
    }


CUSTOMERS = {
    "CUST-123": {
        "customer_id": "CUST-123",
        "name": "Jane Smith",
        "loyalty_points": 4250,
        "tier": "Gold",
    },
    "CUST-456": {
        "customer_id": "CUST-456",
        "name": "Bob Johnson",
        "loyalty_points": 890,
        "tier": "Silver",
    },
}


def _json_default(value):
    if isinstance(value, Decimal):
        return float(value)
    raise TypeError


def _response(status_code: int, model) -> dict:
    return {
        "statusCode": status_code,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(model.model_dump(mode="json"), default=_json_default),
    }


def lambda_handler(event, context):
    """Route IAM-authorized API Gateway proxy requests to mock order data."""

    del context
    resource = event.get("resource", "")
    method = event.get("httpMethod", "GET")
    params = event.get("pathParameters") or {}
    orders = _orders()

    if resource == "/orders/{order_id}" and method == "GET":
        order_id = params.get("order_id", "").upper()
        if order_id not in orders:
            return _response(404, ToolError(error=f"Order {order_id} not found", code="NOT_FOUND"))
        return _response(200, Order.model_validate(orders[order_id]))

    if resource == "/customers/{customer_id}/orders" and method == "GET":
        customer_id = params.get("customer_id", "").upper()
        matches = [
            Order.model_validate(order)
            for order in orders.values()
            if order["customer_id"] == customer_id
        ]
        if not matches:
            return _response(
                404, ToolError(error=f"No orders found for {customer_id}", code="NOT_FOUND")
            )
        return _response(200, CustomerOrders(customer_id=customer_id, orders=matches))

    if resource == "/customers/{customer_id}" and method == "GET":
        customer_id = params.get("customer_id", "").upper()
        if customer_id not in CUSTOMERS:
            return _response(
                404, ToolError(error=f"Customer {customer_id} not found", code="NOT_FOUND")
            )
        return _response(200, CustomerProfile.model_validate(CUSTOMERS[customer_id]))

    return _response(400, ToolError(error="Unrecognized route", code="BAD_REQUEST"))
