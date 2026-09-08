from decimal import Decimal

from support_agent.tools import _discount_fallback, _extract_code_text


def test_gold_fallback_uses_tier_only() -> None:
    result = _discount_fallback(4250, "Gold", 200)
    assert result.final_total == Decimal("180.00")
    assert result.points_redeemed == 0
    assert result.calculation_mode == "fallback"


def test_code_interpreter_text_extraction() -> None:
    response = {"stream": [{"result": {"content": [{"type": "text", "text": '{"ok": true}'}]}}]}
    assert _extract_code_text(response) == '{"ok": true}'
