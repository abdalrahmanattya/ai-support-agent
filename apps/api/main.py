"""Local FastAPI façade for CircuitCare's AWS-backed customer portal."""

from __future__ import annotations

import os
import secrets
from datetime import date
from pathlib import Path

from fastapi import Depends, FastAPI, Header, HTTPException, Request, Response
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field

from domain.dynamo import DynamoRepository
from domain.models import Actor, CaseStatus, ReturnRequest
from domain.service import DomainError, SupportService

from .agent import invoke
from .auth import actor_from_request, begin_login, finish_login

app = FastAPI(title="CircuitCare API", version="1.0.0")
repository = DynamoRepository(os.getenv("BUSINESS_TABLE_NAME", "ai-support-agent-business"))
scenario_date = date.fromisoformat(os.environ["SCENARIO_DATE"]) if os.getenv("SCENARIO_DATE") else None
service = SupportService(repository, today=scenario_date)


class Input(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class ChatInput(Input):
    prompt: str = Field(min_length=1, max_length=8000)
    conversation_id: str = Field(min_length=33, max_length=100)


class ReturnInput(Input):
    order_id: str
    reason: str = Field(min_length=3, max_length=500)


class ConfirmInput(Input):
    proposal: ReturnRequest


class CaseInput(Input):
    subject: str = Field(min_length=3, max_length=120)
    summary: str = Field(min_length=3, max_length=2000)


class CaseUpdate(Input):
    status: CaseStatus
    resolution: str | None = Field(default=None, max_length=2000)


def actor(request: Request) -> Actor:
    return actor_from_request(request)


def csrf(request: Request, x_csrf_token: str = Header(default="")) -> None:
    if not secrets.compare_digest(request.cookies.get("circuitcare_csrf", ""), x_csrf_token):
        raise HTTPException(403, "Invalid CSRF token")


@app.exception_handler(DomainError)
async def domain_error(_request: Request, exc: DomainError):
    from fastapi.responses import JSONResponse

    status = 404 if exc.code == "NOT_FOUND" else 403 if exc.code == "FORBIDDEN" else 422
    return JSONResponse(status_code=status, content={"error": {"code": exc.code, "message": str(exc)}})


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/auth/login")
def login() -> RedirectResponse:
    url, state = begin_login()
    response = RedirectResponse(url)
    response.set_cookie("circuitcare_login", state, httponly=True, samesite="lax", max_age=600)
    return response


@app.get("/auth/callback")
async def callback(request: Request, code: str, state: str) -> RedirectResponse:
    session = await finish_login(code, state, request.cookies.get("circuitcare_login", ""))
    response = RedirectResponse("/")
    response.set_cookie("circuitcare_session", session, httponly=True, samesite="lax", max_age=3600)
    response.set_cookie("circuitcare_csrf", secrets.token_urlsafe(24), samesite="lax", max_age=3600)
    response.delete_cookie("circuitcare_login")
    return response


@app.post("/auth/logout", dependencies=[Depends(csrf)])
def logout() -> Response:
    response = Response(status_code=204)
    response.delete_cookie("circuitcare_session")
    response.delete_cookie("circuitcare_csrf")
    return response


@app.get("/api/me")
def me(current: Actor = Depends(actor)) -> Actor:
    return current


@app.get("/api/orders")
def orders(current: Actor = Depends(actor)):
    return service.list_orders(current)


@app.post("/api/returns/proposals", dependencies=[Depends(csrf)])
def propose(body: ReturnInput, current: Actor = Depends(actor)):
    return service.propose_return(current, body.order_id, body.reason)


@app.get("/api/returns")
def returns(current: Actor = Depends(actor)):
    return service.list_returns(current)


@app.post("/api/returns/confirm", dependencies=[Depends(csrf)])
def confirm(
    body: ConfirmInput,
    idempotency_key: str = Header(alias="Idempotency-Key"),
    current: Actor = Depends(actor),
):
    return service.confirm_return(current, body.proposal, idempotency_key)


@app.get("/api/cases")
def cases(current: Actor = Depends(actor)):
    return service.list_cases(current)


@app.post("/api/cases", dependencies=[Depends(csrf)])
def create_case(body: CaseInput, current: Actor = Depends(actor)):
    return service.create_case(current, body.subject, body.summary)


@app.patch("/api/cases/{case_id}", dependencies=[Depends(csrf)])
def update_case(case_id: str, body: CaseUpdate, current: Actor = Depends(actor)):
    return service.update_case(current, case_id, body.status, body.resolution)


@app.post("/api/chat", dependencies=[Depends(csrf)])
def chat(body: ChatInput, current: Actor = Depends(actor)):
    if current.role.value != "customer" or not current.customer_id:
        raise HTTPException(403, "Customer chat access is required")
    return {"answer": invoke(body.prompt, current.subject, body.conversation_id)}


web_dist = Path(__file__).resolve().parents[1] / "web" / "dist"
if web_dist.exists():
    app.mount("/assets", StaticFiles(directory=web_dist / "assets"), name="assets")

    @app.get("/{path:path}")
    def spa(path: str):
        candidate = web_dist / path
        return FileResponse(candidate if candidate.is_file() else web_dist / "index.html")
