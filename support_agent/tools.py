"""Local Strands tools backed by AgentCore managed services."""

from __future__ import annotations

import json
import logging
import math
from decimal import Decimal
from typing import Any

import boto3
from bedrock_agentcore.tools.code_interpreter_client import code_session
from strands import tool

from .config import settings
from .schemas import DiscountBreakdown

logger = logging.getLogger(__name__)
_bedrock_runtime = boto3.client("bedrock-agent-runtime", region_name=settings.region)


@tool
def search_knowledge_base(query: str) -> str:
    """Search approved CircuitCare product, troubleshooting, warranty, and policy information."""

    if not settings.knowledge_base_id:
        return "Knowledge base not configured."
    try:
        response = _bedrock_runtime.retrieve(
            knowledgeBaseId=settings.knowledge_base_id,
            retrievalQuery={"text": query},
            retrievalConfiguration={"vectorSearchConfiguration": {"numberOfResults": 5}},
        )
    except Exception:
        logger.exception("Knowledge base retrieval failed")
        return "The support knowledge base is temporarily unavailable."
    results = response.get("retrievalResults", [])
    if not results:
        return "No relevant support information was found."
    chunks = []
    for item in results:
        text = item.get("content", {}).get("text", "").strip()
        location = item.get("location", {}).get("s3Location", {}).get("uri", "approved catalog")
        if text:
            chunks.append(f"{text}\nSource: {location}")
    return "\n---\n".join(chunks) if chunks else "No relevant support information was found."


def _discount_fallback(loyalty_points: int, tier: str, order_total: float) -> DiscountBreakdown:
    tier_rate = {"Silver": Decimal("0"), "Gold": Decimal("0.10"), "Platinum": Decimal("0.15")}[tier]
    total = Decimal(str(order_total))
    tier_discount = (total * tier_rate).quantize(Decimal("0.01"))
    final_total = (total - tier_discount).quantize(Decimal("0.01"))
    return DiscountBreakdown(
        points_redeemed=0,
        points_discount=Decimal("0"),
        tier_discount_pct=tier_rate,
        tier_discount=tier_discount,
        final_total=final_total,
        total_savings=tier_discount,
        points_earned=0,
        remaining_points=loyalty_points,
        calculation_mode="fallback",
        warning="Code Interpreter unavailable; no points were redeemed or earned.",
    )


def _extract_code_text(response: dict[str, Any]) -> str:
    for event in response.get("stream", []):
        for item in event.get("result", {}).get("content", []):
            if item.get("type") == "text" and item.get("text"):
                return item["text"].strip()
    raise ValueError("Code Interpreter returned no text result")


@tool
def calculate_loyalty_discount(
    loyalty_points: int,
    tier: str,
    order_total: float,
    product_category: str = "standard",
) -> str:
    """Calculate an exact CircuitCare loyalty discount in the AgentCore Code Interpreter sandbox."""

    if loyalty_points < 0 or not math.isfinite(order_total) or order_total <= 0:
        return json.dumps({"error": "Points and order total must be valid positive values."})
    normalized_tier = tier.title()
    normalized_category = product_category.lower()
    if normalized_tier not in {"Silver", "Gold", "Platinum"}:
        return json.dumps({"error": "Tier must be Silver, Gold, or Platinum."})
    if normalized_category not in {"standard", "device", "fresh"}:
        return json.dumps({"error": "Category must be standard, device, or fresh."})

    code = f"""
import json, math
loyalty_points = {int(loyalty_points)}
tier = {normalized_tier!r}
order_total = {float(order_total)!r}
product_category = {normalized_category!r}
earn_rates = {{"standard": 1, "device": 2, "fresh": 5}}
tier_rates = {{"Silver": 0.00, "Gold": 0.10, "Platinum": 0.15}}
available_block = (loyalty_points // 500) * 500
cap_points = (math.floor((order_total * 0.50 * 100) / 500) * 500)
points_redeemed = min(available_block, cap_points)
points_discount = round(points_redeemed / 100, 2)
subtotal = round(order_total - points_discount, 2)
tier_discount = round(subtotal * tier_rates[tier], 2)
final_total = round(subtotal - tier_discount, 2)
points_earned = math.floor(final_total * earn_rates[product_category])
result = {{
  "points_redeemed": points_redeemed,
  "points_discount": points_discount,
  "tier_discount_pct": tier_rates[tier],
  "tier_discount": tier_discount,
  "final_total": final_total,
  "total_savings": round(order_total - final_total, 2),
  "points_earned": points_earned,
  "remaining_points": loyalty_points - points_redeemed + points_earned,
  "calculation_mode": "code_interpreter",
  "warning": None,
}}
print(json.dumps(result))
""".strip()
    try:
        with code_session(settings.region) as session:
            response = session.invoke(
                "executeCode", {"language": "python", "code": code, "clearContext": True}
            )
        parsed = json.loads(_extract_code_text(response))
        return DiscountBreakdown.model_validate(parsed).model_dump_json()
    except Exception:
        logger.exception("Code Interpreter calculation failed; using tier-only fallback")
        return _discount_fallback(loyalty_points, normalized_tier, order_total).model_dump_json()
