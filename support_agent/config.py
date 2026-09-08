"""Runtime configuration loaded from environment variables."""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    region: str = os.getenv("AWS_REGION", "us-east-1")
    model_id: str = os.getenv("MODEL_ID", "us.amazon.nova-2-lite-v1:0")
    gateway_url: str = os.getenv("GATEWAY_URL", "")
    knowledge_base_id: str = os.getenv("KNOWLEDGE_BASE_ID", "")
    memory_id: str = os.getenv("MEMORY_ID", "")


settings = Settings()
