"""Repository contracts and deterministic in-memory implementation."""

from __future__ import annotations

from copy import deepcopy
from typing import Protocol

from .models import AuditEvent, Order, ReturnRequest, SupportCase


class ConflictError(Exception):
    """A protected resource already exists."""


class Repository(Protocol):
    def list_orders(self, customer_id: str) -> list[Order]: ...
    def get_order(self, order_id: str) -> Order | None: ...
    def list_returns(self, customer_id: str) -> list[ReturnRequest]: ...
    def get_return_by_key(self, idempotency_key: str) -> ReturnRequest | None: ...
    def save_return(self, value: ReturnRequest, idempotency_key: str) -> None: ...
    def list_cases(self, customer_id: str | None = None) -> list[SupportCase]: ...
    def get_case(self, case_id: str) -> SupportCase | None: ...
    def save_case(self, value: SupportCase) -> None: ...
    def append_audit(self, value: AuditEvent) -> None: ...


class MemoryRepository:
    def __init__(self, orders: list[Order] | None = None) -> None:
        self.orders = {item.order_id: deepcopy(item) for item in orders or []}
        self.returns: dict[str, ReturnRequest] = {}
        self.return_keys: dict[str, str] = {}
        self.cases: dict[str, SupportCase] = {}
        self.audit: list[AuditEvent] = []

    def list_orders(self, customer_id: str) -> list[Order]:
        return [deepcopy(v) for v in self.orders.values() if v.customer_id == customer_id]

    def get_order(self, order_id: str) -> Order | None:
        value = self.orders.get(order_id)
        return deepcopy(value) if value else None

    def list_returns(self, customer_id: str) -> list[ReturnRequest]:
        return [deepcopy(v) for v in self.returns.values() if v.customer_id == customer_id]

    def get_return_by_key(self, idempotency_key: str) -> ReturnRequest | None:
        return_id = self.return_keys.get(idempotency_key)
        return deepcopy(self.returns[return_id]) if return_id else None

    def save_return(self, value: ReturnRequest, idempotency_key: str) -> None:
        if any(item.order_id == value.order_id for item in self.returns.values()):
            raise ConflictError("A return already exists for this order")
        self.returns[value.return_id] = deepcopy(value)
        self.return_keys[idempotency_key] = value.return_id

    def list_cases(self, customer_id: str | None = None) -> list[SupportCase]:
        return [deepcopy(v) for v in self.cases.values() if customer_id is None or v.customer_id == customer_id]

    def get_case(self, case_id: str) -> SupportCase | None:
        value = self.cases.get(case_id)
        return deepcopy(value) if value else None

    def save_case(self, value: SupportCase) -> None:
        self.cases[value.case_id] = deepcopy(value)

    def append_audit(self, value: AuditEvent) -> None:
        self.audit.append(deepcopy(value))
