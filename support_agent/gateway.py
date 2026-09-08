"""IAM-authenticated MCP transport for AgentCore Gateway."""

from __future__ import annotations

import boto3
import httpx
from botocore.auth import SigV4Auth
from botocore.awsrequest import AWSRequest
from mcp.client.streamable_http import streamablehttp_client
from strands.tools.mcp import MCPClient

SERVICE = "bedrock-agentcore"
SIGNED_HEADERS = ("Authorization", "X-Amz-Date", "X-Amz-Security-Token", "X-Amz-Content-SHA256")


class SigV4HTTPXAuth(httpx.Auth):
    """Sign an httpx request using the active AWS identity."""

    requires_request_body = True

    def __init__(self, region: str) -> None:
        credentials = boto3.Session().get_credentials()
        if credentials is None:
            raise RuntimeError("No AWS credentials are available for Gateway signing")
        self._credentials = credentials
        self._region = region

    def auth_flow(self, request: httpx.Request):
        frozen = self._credentials.get_frozen_credentials()
        aws_request = AWSRequest(
            method=request.method,
            url=str(request.url),
            data=request.content,
            headers={"Content-Type": request.headers.get("Content-Type", "application/json")},
        )
        SigV4Auth(frozen, SERVICE, self._region).add_auth(aws_request)
        for header in SIGNED_HEADERS:
            if header in aws_request.headers:
                request.headers[header] = aws_request.headers[header]
        yield request


def build_mcp_client(gateway_url: str, region: str) -> MCPClient:
    """Create an MCP client for an AWS_IAM-authorized AgentCore Gateway."""

    auth = SigV4HTTPXAuth(region)
    return MCPClient(lambda: streamablehttp_client(gateway_url, auth=auth))
