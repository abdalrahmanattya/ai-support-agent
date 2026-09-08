"""Validated contracts shared by the agent and its business tools."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, field_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class InvocationRequest(StrictModel):
    prompt: str = Field(min_length=1, max_length=8_000)
    customer_id: str | None = Field(default=None, max_length=100)
    user_id: str | None = Field(default=None, max_length=100)
    session_id: str | None = Field(default=None, max_length=100)

    @field_validator("prompt")
    @classmethod
    def nonblank_prompt(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("prompt must not be blank")
        return value


class OrderStatus(StrEnum):
    PROCESSING = "PROCESSING"
    SHIPPED = "SHIPPED"
    OUT_FOR_DELIVERY = "OUT_FOR_DELIVERY"
    DELIVERED = "DELIVERED"
    CANCELLED = "CANCELLED"


class OrderItem(StrictModel):
    name: str
    quantity: int = Field(ge=1)
    unit_price: Decimal = Field(ge=0)


class Order(StrictModel):
    order_id: str
    customer_id: str
    status: OrderStatus
    items: list[OrderItem]
    total: Decimal = Field(ge=0)
    tracking_number: str | None = None
    carrier: str | None = None
    estimated_delivery: str | None = None
    delivered_date: str | None = None


class CustomerProfile(StrictModel):
    customer_id: str
    name: str
    loyalty_points: int = Field(ge=0)
    tier: str


class CustomerOrders(StrictModel):
    customer_id: str
    orders: list[Order]


class RefundInitiated(StrictModel):
    refund_id: str
    order_id: str
    status: str
    amount: Decimal = Field(gt=0)
    message: str
    created_at: datetime


class RefundStatus(StrictModel):
    refund_id: str
    status: str
    eta: str


class ReturnLabel(StrictModel):
    order_id: str
    label_url: str
    carrier: str
    valid_until: str


class ToolError(StrictModel):
    error: str
    code: str


class DiscountBreakdown(StrictModel):
    points_redeemed: int = Field(ge=0)
    points_discount: Decimal = Field(ge=0)
    tier_discount_pct: Decimal = Field(ge=0, le=1)
    tier_discount: Decimal = Field(ge=0)
    final_total: Decimal = Field(ge=0)
    total_savings: Decimal = Field(ge=0)
    points_earned: int = Field(ge=0)
    remaining_points: int = Field(ge=0)
    calculation_mode: str
    warning: str | None = None
