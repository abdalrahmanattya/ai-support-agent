"""Authoritative business records and public contracts."""

from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class DomainModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class Role(StrEnum):
    CUSTOMER = "customer"
    STAFF = "staff"


class Actor(DomainModel):
    subject: str
    customer_id: str | None = None
    role: Role = Role.CUSTOMER
    display_name: str


class OrderStatus(StrEnum):
    PROCESSING = "PROCESSING"
    SHIPPED = "SHIPPED"
    DELIVERED = "DELIVERED"
    CANCELLED = "CANCELLED"


class OrderItem(DomainModel):
    sku: str
    name: str
    quantity: int = Field(ge=1)
    unit_price: Decimal = Field(ge=0)
    category: str
    opened: bool = False


class Order(DomainModel):
    order_id: str
    customer_id: str
    status: OrderStatus
    delivered_on: date | None = None
    items: list[OrderItem]
    tracking_number: str | None = None
    carrier: str | None = None

    @property
    def total(self) -> Decimal:
        return sum((item.unit_price * item.quantity for item in self.items), Decimal("0"))


class ReturnStatus(StrEnum):
    PROPOSED = "PROPOSED"
    CONFIRMED = "CONFIRMED"


class ReturnRequest(DomainModel):
    return_id: str
    order_id: str
    customer_id: str
    amount: Decimal = Field(gt=0)
    reason: str
    status: ReturnStatus
    created_at: datetime


class CaseStatus(StrEnum):
    OPEN = "OPEN"
    IN_PROGRESS = "IN_PROGRESS"
    RESOLVED = "RESOLVED"


class SupportCase(DomainModel):
    case_id: str
    customer_id: str
    subject: str
    summary: str
    status: CaseStatus
    resolution: str | None = None
    created_at: datetime
    updated_at: datetime


class AuditEvent(DomainModel):
    event_id: str
    actor_subject: str
    customer_id: str
    action: str
    resource_id: str
    occurred_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
