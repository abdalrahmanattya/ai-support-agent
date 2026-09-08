"""Cognito authorization-code flow and verified session handling."""

from __future__ import annotations

import base64
import hashlib
import os
import secrets
import time
from dataclasses import dataclass
from urllib.parse import urlencode

import httpx
import jwt
from fastapi import HTTPException, Request
from itsdangerous import BadSignature, URLSafeTimedSerializer

from domain.models import Actor, Role


@dataclass(frozen=True)
class AuthSettings:
    region: str = os.getenv("AWS_REGION", "us-east-1")
    user_pool_id: str = os.getenv("COGNITO_USER_POOL_ID", "")
    client_id: str = os.getenv("COGNITO_CLIENT_ID", "")
    domain: str = os.getenv("COGNITO_DOMAIN", "")
    redirect_uri: str = os.getenv("COGNITO_REDIRECT_URI", "http://127.0.0.1:8000/auth/callback")
    session_secret: str = os.getenv("SESSION_SECRET", "development-only-change-me")

    @property
    def issuer(self) -> str:
        return f"https://cognito-idp.{self.region}.amazonaws.com/{self.user_pool_id}"


settings = AuthSettings()
serializer = URLSafeTimedSerializer(settings.session_secret, salt="circuitcare-session")


def begin_login() -> tuple[str, str]:
    verifier = secrets.token_urlsafe(48)
    state = secrets.token_urlsafe(24)
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).decode().rstrip("=")
    query = urlencode(
        {
            "client_id": settings.client_id,
            "response_type": "code",
            "scope": "openid email profile",
            "redirect_uri": settings.redirect_uri,
            "code_challenge_method": "S256",
            "code_challenge": challenge,
            "state": state,
        }
    )
    return f"https://{settings.domain}/oauth2/authorize?{query}", serializer.dumps(
        {"verifier": verifier, "state": state}
    )


async def finish_login(code: str, state: str, flow_cookie: str) -> str:
    try:
        flow = serializer.loads(flow_cookie, max_age=600)
        verifier = flow["verifier"]
        if not secrets.compare_digest(flow["state"], state):
            raise HTTPException(400, "Login state did not match")
    except (BadSignature, KeyError) as exc:
        raise HTTPException(400, "Login flow expired") from exc
    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.post(
            f"https://{settings.domain}/oauth2/token",
            data={
                "grant_type": "authorization_code",
                "client_id": settings.client_id,
                "code": code,
                "redirect_uri": settings.redirect_uri,
                "code_verifier": verifier,
            },
        )
    if response.status_code != 200:
        raise HTTPException(401, "Cognito rejected the authorization code")
    claims = await verify_token(response.json()["id_token"], "id")
    return serializer.dumps({"claims": claims, "expires": int(time.time()) + 3600})


async def verify_token(token: str, token_use: str = "id") -> dict:
    async with httpx.AsyncClient(timeout=10) as client:
        jwks = (await client.get(f"{settings.issuer}/.well-known/jwks.json")).json()
    header = jwt.get_unverified_header(token)
    key = next((item for item in jwks["keys"] if item["kid"] == header["kid"]), None)
    if not key:
        raise HTTPException(401, "Unknown token signing key")
    claims = jwt.decode(
        token,
        jwt.PyJWK.from_dict(key).key,
        algorithms=["RS256"],
        audience=settings.client_id,
        issuer=settings.issuer,
    )
    if claims.get("token_use") != token_use:
        raise HTTPException(401, "Unexpected token type")
    return claims


def actor_from_request(request: Request) -> Actor:
    raw = request.cookies.get("circuitcare_session")
    if not raw:
        raise HTTPException(401, "Sign in required")
    try:
        value = serializer.loads(raw, max_age=3600)
        claims = value["claims"]
    except (BadSignature, KeyError) as exc:
        raise HTTPException(401, "Session expired") from exc
    groups = claims.get("cognito:groups", [])
    role = Role.STAFF if "support-staff" in groups else Role.CUSTOMER
    return Actor(
        subject=claims["sub"],
        customer_id=claims.get("custom:customer_id"),
        role=role,
        display_name=claims.get("name") or claims.get("email", "CircuitCare user"),
    )
