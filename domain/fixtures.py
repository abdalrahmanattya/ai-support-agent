"""Deterministic product scenarios used by local tests and AWS seeding."""

from datetime import date
from decimal import Decimal

from .models import Order, OrderItem, OrderStatus

SCENARIO_DATE = date(2026, 9, 8)

ORDERS = [
    Order(
        order_id="ORD-001",
        customer_id="CUST-123",
        status=OrderStatus.SHIPPED,
        tracking_number="TRK987654321",
        carrier="UPS",
        items=[
            OrderItem(
                sku="CC-100",
                name="AeroSound ANC Headphones",
                quantity=1,
                unit_price=Decimal("129.99"),
                category="personal-electronics",
                opened=True,
            )
        ],
    ),
    Order(
        order_id="ORD-002",
        customer_id="CUST-123",
        status=OrderStatus.DELIVERED,
        delivered_on=date(2026, 9, 5),
        items=[
            OrderItem(
                sku="CC-200",
                name="LumaRead E-Reader",
                quantity=1,
                unit_price=Decimal("149.99"),
                category="device",
            )
        ],
    ),
    Order(
        order_id="ORD-003",
        customer_id="CUST-456",
        status=OrderStatus.DELIVERED,
        delivered_on=date(2026, 7, 1),
        items=[
            OrderItem(
                sku="CC-300",
                name="HomeHub Mini",
                quantity=1,
                unit_price=Decimal("49.99"),
                category="device",
            )
        ],
    ),
]
