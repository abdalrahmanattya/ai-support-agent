from urllib.parse import parse_qs, urlparse

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from apps.api import main
from apps.api.auth import begin_login, finish_login, serializer
from domain.fixtures import ORDERS, SCENARIO_DATE
from domain.repository import MemoryRepository
from domain.service import SupportService


def client_for(monkeypatch, customer_id: str, groups: list[str] | None = None) -> TestClient:
    repository = MemoryRepository(ORDERS)
    monkeypatch.setattr(main, "service", SupportService(repository, today=SCENARIO_DATE))
    client = TestClient(main.app)
    session = serializer.dumps(
        {
            "claims": {
                "sub": f"subject-{customer_id}",
                "custom:customer_id": customer_id,
                "name": "Test User",
                "cognito:groups": groups or [],
            }
        }
    )
    client.cookies.set("circuitcare_session", session)
    client.cookies.set("circuitcare_csrf", "test-csrf")
    return client


def test_api_requires_session() -> None:
    assert TestClient(main.app).get("/api/orders").status_code == 401


@pytest.mark.asyncio
async def test_login_uses_pkce_and_rejects_changed_state() -> None:
    url, cookie = begin_login()
    query = parse_qs(urlparse(url).query)
    assert query["code_challenge_method"] == ["S256"]
    assert query["state"]
    with pytest.raises(HTTPException, match="Login state did not match"):
        await finish_login("code", "changed", cookie)


def test_customer_journey_and_csrf(monkeypatch) -> None:
    client = client_for(monkeypatch, "CUST-123")
    orders = client.get("/api/orders").json()
    assert {item["order_id"] for item in orders} == {"ORD-001", "ORD-002"}
    assert client.post("/api/cases", json={"subject": "Battery", "summary": "It is swollen"}).status_code == 403
    headers = {"X-CSRF-Token": "test-csrf"}
    case = client.post(
        "/api/cases",
        headers=headers,
        json={"subject": "Battery", "summary": "It is swollen"},
    )
    assert case.status_code == 200
    assert client.get("/api/cases").json()[0]["status"] == "OPEN"


def test_customer_cannot_resolve_staff_case(monkeypatch) -> None:
    customer = client_for(monkeypatch, "CUST-123")
    case_id = customer.post(
        "/api/cases",
        headers={"X-CSRF-Token": "test-csrf"},
        json={"subject": "Battery", "summary": "It is swollen"},
    ).json()["case_id"]
    response = customer.patch(
        f"/api/cases/{case_id}",
        headers={"X-CSRF-Token": "test-csrf"},
        json={"status": "RESOLVED", "resolution": "Done"},
    )
    assert response.status_code == 403


def test_chat_rejects_agentcore_session_ids_that_are_too_short(monkeypatch) -> None:
    client = client_for(monkeypatch, "CUST-123")
    response = client.post(
        "/api/chat",
        headers={"X-CSRF-Token": "test-csrf"},
        json={"prompt": "Help me", "conversation_id": "too-short"},
    )
    assert response.status_code == 422
