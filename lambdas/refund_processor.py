"""Validated mock refund tools invoked directly by AgentCore Gateway."""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from types import SimpleNamespace

from pydantic import ValidationError

from support_agent.schemas import RefundInitiated, RefundStatus, ReturnLabel, ToolError


def _response(status_code: int, model) -> dict:
    return {"statusCode": status_code, "body": model.model_dump_json()}


def _tool_name(context) -> str:
    custom = getattr(getattr(context, "client_context", None), "custom", {}) or {}
    raw = custom.get("bedrockAgentCoreToolName", "")
    return raw.split("___", 1)[-1] if "___" in raw else raw


def lambda_handler(event, context):
    """Dispatch and validate one simulated refund operation."""

    tool_name = _tool_name(context or SimpleNamespace(client_context=None))
    try:
        if tool_name == "initiate_refund":
            order_id = str(event.get("order_id", "")).upper()
            amount = Decimal(str(event.get("amount", 0)))
            if not order_id or amount <= 0:
                raise ValueError("order_id and a positive amount are required")
            digest = hashlib.sha256(f"{order_id}:{amount}".encode()).hexdigest()[:8].upper()
            return _response(
                200,
                RefundInitiated(
                    refund_id=f"REF-{digest}",
                    order_id=order_id,
                    status="APPROVED",
                    amount=amount,
                    message=(
                        "Simulated refund approved; a real credit would take "
                        "3–5 business days."
                    ),
                    created_at=datetime.now(UTC),
                ),
            )
        if tool_name == "check_refund_status":
            refund_id = str(event.get("refund_id", "")).upper()
            if not refund_id:
                raise ValueError("refund_id is required")
            return _response(
                200, RefundStatus(refund_id=refund_id, status="PROCESSING", eta="2–3 business days")
            )
        if tool_name == "get_return_label":
            order_id = str(event.get("order_id", "")).upper()
            if not order_id:
                raise ValueError("order_id is required")
            return _response(
                200,
                ReturnLabel(
                    order_id=order_id,
                    label_url=f"https://returns.circuitcare.example/labels/{order_id}",
                    carrier="UPS",
                    valid_until=str(datetime.now(UTC).date() + timedelta(days=14)),
                ),
            )
    except (ValueError, ValidationError) as exc:
        return _response(400, ToolError(error=str(exc), code="VALIDATION_ERROR"))
    return _response(400, ToolError(error=f"Unknown tool: {tool_name}", code="UNKNOWN_TOOL"))
