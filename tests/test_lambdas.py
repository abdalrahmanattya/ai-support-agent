import json
from types import SimpleNamespace

from lambdas.order_tracker import lambda_handler as order_handler
from lambdas.refund_processor import lambda_handler as refund_handler


def _context(tool: str):
    return SimpleNamespace(
        client_context=SimpleNamespace(
            custom={"bedrockAgentCoreToolName": f"RefundLambda___{tool}"}
        )
    )


def test_order_lookup_returns_valid_order() -> None:
    response = order_handler(
        {
            "resource": "/orders/{order_id}",
            "httpMethod": "GET",
            "pathParameters": {"order_id": "ord-001"},
        },
        None,
    )
    assert response["statusCode"] == 200
    assert json.loads(response["body"])["status"] == "SHIPPED"


def test_unknown_order_is_structured_error() -> None:
    response = order_handler(
        {
            "resource": "/orders/{order_id}",
            "httpMethod": "GET",
            "pathParameters": {"order_id": "missing"},
        },
        None,
    )
    assert json.loads(response["body"])["code"] == "NOT_FOUND"


def test_refund_is_deterministic_and_validated() -> None:
    event = {"order_id": "ORD-002", "amount": 25, "reason": "Changed mind"}
    first = refund_handler(event, _context("initiate_refund"))
    second = refund_handler(event, _context("initiate_refund"))
    assert first["statusCode"] == 200
    assert json.loads(first["body"])["refund_id"] == json.loads(second["body"])["refund_id"]


def test_refund_rejects_nonpositive_amount() -> None:
    response = refund_handler({"order_id": "ORD-002", "amount": 0}, _context("initiate_refund"))
    assert response["statusCode"] == 400
    assert json.loads(response["body"])["code"] == "VALIDATION_ERROR"
