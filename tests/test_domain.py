import pytest

from domain.fixtures import ORDERS, SCENARIO_DATE
from domain.models import Actor, CaseStatus, Role
from domain.repository import MemoryRepository
from domain.service import (
    ForbiddenError,
    IneligibleError,
    NotFoundError,
    SupportService,
    ValidationError,
)


@pytest.fixture
def setup():
    repository = MemoryRepository(ORDERS)
    service = SupportService(repository, today=SCENARIO_DATE)
    jane = Actor(subject="jane", customer_id="CUST-123", role=Role.CUSTOMER, display_name="Jane")
    bob = Actor(subject="bob", customer_id="CUST-456", role=Role.CUSTOMER, display_name="Bob")
    staff = Actor(subject="staff", customer_id="STAFF", role=Role.STAFF, display_name="Staff")
    return repository, service, jane, bob, staff


def test_customer_only_sees_owned_orders(setup) -> None:
    _, service, jane, bob, _ = setup
    assert {item.order_id for item in service.list_orders(jane)} == {"ORD-001", "ORD-002"}
    with pytest.raises(NotFoundError):
        service.get_order(bob, "ORD-002")


def test_return_requires_eligibility_and_confirmation(setup) -> None:
    repository, service, jane, bob, _ = setup
    proposal = service.propose_return(jane, "ORD-002", "Changed my mind")
    assert proposal.status == "PROPOSED"
    assert repository.list_returns("CUST-123") == []
    confirmed = service.confirm_return(jane, proposal, "one-request")
    assert confirmed.status == "CONFIRMED"
    assert service.confirm_return(jane, proposal, "one-request") == confirmed
    with pytest.raises(IneligibleError):
        service.propose_return(bob, "ORD-003", "No longer needed")


def test_idempotency_key_cannot_change_payload(setup) -> None:
    _, service, jane, _, _ = setup
    proposal = service.propose_return(jane, "ORD-002", "Changed my mind")
    service.confirm_return(jane, proposal, "same-key")
    changed = proposal.model_copy(update={"reason": "Different reason"})
    with pytest.raises(ValidationError):
        service.confirm_return(jane, changed, "same-key")


def test_proposal_amount_cannot_be_tampered_with(setup) -> None:
    _, service, jane, _, _ = setup
    proposal = service.propose_return(jane, "ORD-002", "Changed my mind")
    changed = proposal.model_copy(update={"amount": proposal.amount + 100})
    with pytest.raises(ValidationError):
        service.confirm_return(jane, changed, "tampered")


def test_second_return_for_same_order_is_rejected(setup) -> None:
    _, service, jane, _, _ = setup
    first = service.propose_return(jane, "ORD-002", "Changed my mind")
    service.confirm_return(jane, first, "first")
    second = service.propose_return(jane, "ORD-002", "Different reason")
    with pytest.raises(IneligibleError):
        service.confirm_return(jane, second, "second")


def test_only_staff_resolves_cases(setup) -> None:
    _, service, jane, _, staff = setup
    case = service.create_case(jane, "Battery damage", "The battery is swollen")
    with pytest.raises(ForbiddenError):
        service.update_case(jane, case.case_id, CaseStatus.RESOLVED, "Handled")
    resolved = service.update_case(staff, case.case_id, CaseStatus.RESOLVED, "Safe disposal arranged")
    assert resolved.status is CaseStatus.RESOLVED
