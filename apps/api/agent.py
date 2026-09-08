"""Server-side AgentCore client; AWS credentials never reach the browser."""

from __future__ import annotations

import json
import os
from typing import Any

import boto3


def response_text(response: dict[str, Any]) -> str:
    body = response["response"].read()
    decoded = body.decode() if isinstance(body, bytes) else str(body)
    try:
        value = json.loads(decoded)
    except json.JSONDecodeError:
        return decoded
    return value if isinstance(value, str) else str(value.get("response") or value.get("output") or value)


def invoke(prompt: str, actor_id: str, session_id: str) -> str:
    runtime_arn = os.environ.get("AGENT_RUNTIME_ARN", "")
    if not runtime_arn:
        raise RuntimeError("AGENT_RUNTIME_ARN is not configured")
    client = boto3.client("bedrock-agentcore", region_name=os.getenv("AWS_REGION", "us-east-1"))
    response = client.invoke_agent_runtime(
        agentRuntimeArn=runtime_arn,
        runtimeSessionId=session_id,
        runtimeUserId=actor_id,
        qualifier="DEFAULT",
        contentType="application/json",
        accept="application/json",
        payload=json.dumps({"prompt": prompt, "user_id": actor_id, "session_id": session_id}).encode(),
    )
    return response_text(response)
