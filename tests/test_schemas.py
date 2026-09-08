from decimal import Decimal

import pytest
from pydantic import ValidationError

from support_agent.schemas import DiscountBreakdown, InvocationRequest


def test_invocation_request_trims_prompt() -> None:
    request = InvocationRequest(prompt="  hello  ")
    assert request.prompt == "hello"


def test_invocation_request_accepts_agentcore_cli_user_id() -> None:
    request = InvocationRequest(prompt="hello", user_id="CUST-CLI")

    assert request.user_id == "CUST-CLI"


def test_invocation_rejects_blank_prompt() -> None:
    with pytest.raises(ValidationError):
        InvocationRequest(prompt="   ")


def test_discount_contract_rejects_negative_total() -> None:
    with pytest.raises(ValidationError):
        DiscountBreakdown(
            points_redeemed=0,
            points_discount=0,
            tier_discount_pct=0,
            tier_discount=0,
            final_total=Decimal("-1"),
            total_savings=0,
            points_earned=0,
            remaining_points=0,
            calculation_mode="test",
        )
