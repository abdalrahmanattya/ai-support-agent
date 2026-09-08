from types import SimpleNamespace

from support_agent.memory import MemoryHook, get_namespaces, session_messages


class FakeMemory:
    def __init__(self):
        self.saved = None

    def get_memory_strategies(self, memory_id):
        return {
            "memoryStrategies": [
                {"type": "SEMANTIC", "namespaceTemplates": ["circuitcare/{actorId}/facts"]},
                {"type": "USER_PREFERENCE", "namespaces": ["circuitcare/{actorId}/preferences"]},
            ]
        }

    def retrieve_memories(self, memory_id, namespace, query, top_k):
        return [{"content": {"text": "Prefers text updates"}}]

    def create_event(self, memory_id, actor_id, session_id, messages):
        self.saved = messages

    def list_events(self, memory_id, actor_id, session_id, max_results):
        return [{"payload": [["Earlier question", "USER"], ["Earlier answer", "ASSISTANT"]]}]


def test_namespace_helper_supports_both_shapes() -> None:
    assert get_namespaces(FakeMemory(), "memory") == {
        "SEMANTIC": "circuitcare/{actorId}/facts",
        "USER_PREFERENCE": "circuitcare/{actorId}/preferences",
    }


def test_namespace_helper_supports_direct_list() -> None:
    memory = FakeMemory()
    memory.get_memory_strategies = lambda memory_id: [
        {"type": "SEMANTIC", "namespaceTemplates": ["circuitcare/{actorId}/facts"]}
    ]
    assert get_namespaces(memory, "memory") == {
        "SEMANTIC": "circuitcare/{actorId}/facts"
    }


def test_session_events_are_reconstructed() -> None:
    messages = session_messages(FakeMemory(), "memory", "CUST-123", "s1")
    assert [message["role"] for message in messages] == ["user", "assistant"]


def test_hook_prepends_context_and_saves_turn() -> None:
    memory = FakeMemory()
    hook = MemoryHook("CUST-123", "s1", memory, "memory")
    agent = SimpleNamespace(messages=[{"role": "user", "content": [{"text": "Where is it?"}]}])
    hook.retrieve_customer_context(SimpleNamespace(agent=agent))
    assert "Prefers text updates" in agent.messages[-1]["content"][0]["text"]
    agent.messages.append({"role": "assistant", "content": [{"text": "It shipped."}]})
    hook.save_support_interaction(SimpleNamespace(agent=agent))
    assert memory.saved == [("Where is it?", "USER"), ("It shipped.", "ASSISTANT")]
