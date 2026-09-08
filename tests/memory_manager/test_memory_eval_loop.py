"""Unit tests for memory eval fixtures and helpers (no Ollama required)."""

from src.memory.eval.fixtures import list_fixtures, load_fixture
from src.memory.eval.gates import eligible_graph_segments
from src.memory.eval.runner import EvalRunner


def test_list_and_load_lost_valley_fixture():
    assert "lost_valley_dnd" in list_fixtures()
    fixture = load_fixture("lost_valley_dnd")
    assert fixture["id"] == "lost_valley_dnd"
    assert fixture.get("domain_config", {}).get("graph_memory_config")
    assert len(fixture["digest_cases"]) >= 1
    assert len(fixture["rag_queries"]) >= 5
    assert len(fixture["required_entities"]) >= 5


def test_eligible_graph_segments_from_seed():
    fixture = load_fixture("lost_valley_dnd")
    segments = eligible_graph_segments(fixture["seed_conversations"]["entries"])
    assert len(segments) >= 8
    assert all(s["type"] in {"information", "action"} for s in segments)


def test_validate_only_runner():
    summary = EvalRunner(fixture_name="lost_valley_dnd").validate_only()
    assert summary["passed"] is True
    assert summary["validate_only"] is True
    assert summary["fixture"] == "lost_valley_dnd"
