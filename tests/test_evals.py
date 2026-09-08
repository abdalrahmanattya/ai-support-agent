import json
from pathlib import Path


def test_live_evaluation_manifest_is_complete_and_unique() -> None:
    manifest = json.loads(Path("evals/scenarios.json").read_text())
    scenarios = manifest["scenarios"]
    assert len(scenarios) == 30
    assert len({item["id"] for item in scenarios}) == 30
    categories = {item["category"] for item in scenarios}
    assert set(manifest["mandatory_categories"]) <= categories
    assert 0 < manifest["minimum_task_success"] <= 1
