"""AgentCore Memory integration for session history and durable customer context."""

from __future__ import annotations

import logging
from typing import Any

from strands.hooks import AfterInvocationEvent, HookProvider, HookRegistry, MessageAddedEvent

logger = logging.getLogger(__name__)


def get_namespaces(memory_client: Any, memory_id: str) -> dict[str, str]:
    """Map memory strategy type to its first namespace template."""

    response = memory_client.get_memory_strategies(memory_id)
    if isinstance(response, list):
        strategies = response
    else:
        strategies = response.get("memoryStrategies", response.get("strategies", []))
    result: dict[str, str] = {}
    for strategy in strategies or []:
        templates = strategy.get("namespaceTemplates") or strategy.get("namespaces") or []
        if templates and strategy.get("type"):
            result[strategy["type"]] = templates[0]
    return result


def _text_blocks(message: Any) -> str:
    content = message.get("content", [])
    if isinstance(content, str):
        return content
    texts = [part.get("text", "") for part in content if isinstance(part, dict) and "text" in part]
    return "\n".join(text for text in texts if text).strip()


def session_messages(
    memory_client: Any, memory_id: str, actor_id: str, session_id: str
) -> list[dict]:
    """Reconstruct recent raw session turns in Strands message format."""

    if not all((memory_client, memory_id, actor_id, session_id)):
        return []
    try:
        events = memory_client.list_events(memory_id, actor_id, session_id, max_results=100)
    except Exception:
        logger.exception("Unable to load session events")
        return []

    messages: list[dict] = []
    for event in events:
        payload = event.get("payload", event.get("eventPayload", []))
        if isinstance(payload, dict):
            payload = payload.get("messages", payload.get("conversational", []))
        for item in payload or []:
            if isinstance(item, (list, tuple)) and len(item) == 2:
                text, role = item
            elif isinstance(item, dict):
                text = item.get("content", item.get("text", ""))
                role = item.get("role", "")
            else:
                continue
            normalized_role = str(role).lower()
            if normalized_role in {"user", "assistant"} and text:
                messages.append({"role": normalized_role, "content": [{"text": str(text)}]})
    return messages


class MemoryHook(HookProvider):
    """Retrieve relevant long-term context and persist completed support turns."""

    def __init__(self, actor_id: str, session_id: str, memory_client: Any, memory_id: str) -> None:
        self.actor_id = actor_id
        self.session_id = session_id
        self.memory_client = memory_client
        self.memory_id = memory_id
        try:
            self.namespaces = get_namespaces(memory_client, memory_id)
        except Exception:
            logger.exception("Unable to load memory namespaces")
            self.namespaces = {}

    def retrieve_customer_context(self, event: MessageAddedEvent) -> None:
        messages = event.agent.messages
        if not messages:
            return
        message = messages[-1]
        if message.get("role") != "user" or any(
            isinstance(part, dict) and "toolResult" in part for part in message.get("content", [])
        ):
            return
        query = _text_blocks(message)
        if not query:
            return

        memories: list[str] = []
        for strategy_type, template in self.namespaces.items():
            namespace = template.format(actorId=self.actor_id, sessionId=self.session_id)
            try:
                results = self.memory_client.retrieve_memories(
                    self.memory_id, namespace, query, top_k=5
                )
            except Exception:
                logger.exception("Memory retrieval failed for %s", strategy_type)
                continue
            for result in results or []:
                text = result.get("content", result.get("text", ""))
                if isinstance(text, dict):
                    text = text.get("text", "")
                if text:
                    memories.append(f"[{strategy_type}] {text}")

        if memories:
            original = message["content"]
            context = "Customer Context:\n" + "\n".join(memories) + "\n\n"
            message["content"] = [{"text": context}, *original]

    def save_support_interaction(self, event: AfterInvocationEvent) -> None:
        user_text = ""
        assistant_text = ""
        for message in reversed(event.agent.messages):
            text = _text_blocks(message)
            if not text:
                continue
            if message.get("role") == "assistant" and not assistant_text:
                assistant_text = text
            elif message.get("role") == "user" and not user_text:
                user_text = text.split("\n\n", 1)[-1].strip()
            if user_text and assistant_text:
                break
        if not user_text or not assistant_text:
            return
        try:
            self.memory_client.create_event(
                self.memory_id,
                self.actor_id,
                self.session_id,
                messages=[(user_text, "USER"), (assistant_text, "ASSISTANT")],
            )
        except Exception:
            logger.exception("Unable to persist support interaction")

    def register_hooks(self, registry: HookRegistry, **kwargs: Any) -> None:
        del kwargs
        registry.add_callback(MessageAddedEvent, self.retrieve_customer_context)
        registry.add_callback(AfterInvocationEvent, self.save_support_interaction)
