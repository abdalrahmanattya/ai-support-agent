"""Business rules kept outside the model and HTTP layer."""

from __future__ import annotations

import hashlib
from datetime import UTC, date, datetime

from .models import (
    Actor,
    AuditEvent,
    CaseStatus,
    Order,
    OrderStatus,
    ReturnRequest,
    ReturnStatus,
    Role,
    SupportCase,
)
from .repository import ConflictError, Repository


class DomainError(Exception):
    code = "DOMAIN_ERROR"


class NotFoundError(DomainError):
    code = "NOT_FOUND"


class ForbiddenError(DomainError):
    code = "FORBIDDEN"


class IneligibleError(DomainError):
    code = "RETURN_INELIGIBLE"


class ValidationError(DomainError):
    code = "VALIDATION_ERROR"


def _stable_id(prefix: str, value: str) -> str:
    return f"{prefix}-{hashlib.sha256(value.encode()).hexdigest()[:10].upper()}"


class SupportService:
    def __init__(self, repository: Repository, today: date | None = None) -> None:
        self.repository = repository
        self.today = today or datetime.now(UTC).date()

    def list_orders(self, actor: Actor) -> list[Order]:
        if actor.role is Role.STAFF or not actor.customer_id:
            raise ForbiddenError("A customer identity is required")
        return self.repository.list_orders(actor.customer_id)

    def get_order(self, actor: Actor, order_id: str) -> Order:
        order = self.repository.get_order(order_id.upper())
        if not order or (actor.role is not Role.STAFF and order.customer_id != actor.customer_id):
            raise NotFoundError("Order was not found")
        return order

    def list_returns(self, actor: Actor) -> list[ReturnRequest]:
        if actor.role is Role.STAFF or not actor.customer_id:
            raise ForbiddenError("A customer identity is required")
        return self.repository.list_returns(actor.customer_id)

    def propose_return(self, actor: Actor, order_id: str, reason: str) -> ReturnRequest:
        order = self.get_order(actor, order_id)
        if actor.role is Role.STAFF or not actor.customer_id:
            raise ForbiddenError("Only the owning customer can request a return")
        if order.status is not OrderStatus.DELIVERED or not order.delivered_on:
            raise IneligibleError("Only delivered orders can be returned")
        window = min(15 if item.opened and item.category == "personal-electronics" else 30 for item in order.items)
        if (self.today - order.delivered_on).days > window:
            raise IneligibleError(f"The {window}-day return window has passed")
        clean_reason = reason.strip()
        if len(clean_reason) < 3:
            raise ValidationError("Provide a return reason")
        return ReturnRequest(
            return_id=_stable_id("RET", f"proposal:{actor.customer_id}:{order.order_id}:{clean_reason}"),
            order_id=order.order_id,
            customer_id=actor.customer_id,
            amount=order.total,
            reason=clean_reason,
            status=ReturnStatus.PROPOSED,
            created_at=datetime.now(UTC),
        )

    def confirm_return(self, actor: Actor, proposal: ReturnRequest, idempotency_key: str) -> ReturnRequest:
        if not actor.customer_id or proposal.customer_id != actor.customer_id:
            raise ForbiddenError("Return proposal does not belong to this customer")
        if existing := self.repository.get_return_by_key(idempotency_key):
            expected = (proposal.order_id, proposal.customer_id, proposal.amount, proposal.reason)
            actual = (existing.order_id, existing.customer_id, existing.amount, existing.reason)
            if actual != expected:
                raise ValidationError("Idempotency key was reused with a different request")
            return existing
        canonical = self.propose_return(actor, proposal.order_id, proposal.reason)
        if (canonical.customer_id, canonical.amount) != (proposal.customer_id, proposal.amount):
            raise ValidationError("Return proposal was changed after review")
        confirmed = proposal.model_copy(
            update={
                "return_id": _stable_id("RET", idempotency_key),
                "status": ReturnStatus.CONFIRMED,
                "created_at": datetime.now(UTC),
            }
        )
        try:
            self.repository.save_return(confirmed, idempotency_key)
        except ConflictError as exc:
            raise IneligibleError("A return already exists for this order") from exc
        self.repository.append_audit(
            AuditEvent(
                event_id=_stable_id("AUD", f"return:{idempotency_key}"),
                actor_subject=actor.subject,
                customer_id=actor.customer_id,
                action="RETURN_CONFIRMED",
                resource_id=confirmed.return_id,
            )
        )
        return confirmed

    def create_case(self, actor: Actor, subject: str, summary: str) -> SupportCase:
        if not actor.customer_id or actor.role is Role.STAFF:
            raise ForbiddenError("A customer identity is required")
        now = datetime.now(UTC)
        value = SupportCase(
            case_id=_stable_id("CASE", f"{actor.customer_id}:{subject}:{summary}"),
            customer_id=actor.customer_id,
            subject=subject.strip(),
            summary=summary.strip(),
            status=CaseStatus.OPEN,
            created_at=now,
            updated_at=now,
        )
        self.repository.save_case(value)
        return value

    def list_cases(self, actor: Actor) -> list[SupportCase]:
        return self.repository.list_cases(None if actor.role is Role.STAFF else actor.customer_id)

    def update_case(self, actor: Actor, case_id: str, status: CaseStatus, resolution: str | None) -> SupportCase:
        if actor.role is not Role.STAFF:
            raise ForbiddenError("Staff access is required")
        value = self.repository.get_case(case_id)
        if not value:
            raise NotFoundError("Case was not found")
        if status is CaseStatus.RESOLVED and not (resolution or "").strip():
            raise ValidationError("A resolution is required")
        updated = value.model_copy(update={"status": status, "resolution": resolution, "updated_at": datetime.now(UTC)})
        self.repository.save_case(updated)
        return updated
