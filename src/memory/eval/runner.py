"""Orchestrate digest / RAG / graph eval gates and write a JSON summary."""

from __future__ import annotations

import asyncio
import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

from src.ai.llm_ollama import OllamaService
from src.memory.eval.fixtures import load_fixture, list_fixtures
from src.memory.eval.gates import run_digest_gate, run_graph_gate, run_rag_gate
from src.utils.logging_config import LoggingConfig

DEFAULT_GATES = ("digest", "rag", "graph")


class EvalRunner:
    """Run memory quality gates against a fixed fixture."""

    def __init__(
        self,
        fixture_name: str = "lost_valley_dnd",
        gates: Optional[Sequence[str]] = None,
        work_dir: Optional[Path] = None,
        session_id: Optional[str] = None,
        verbose: bool = False,
    ):
        self.fixture_name = fixture_name
        self.gates = tuple(gates or DEFAULT_GATES)
        self.session_id = session_id or f"memory_eval_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
        self.verbose = verbose
        self.work_dir = Path(work_dir) if work_dir else Path("tests/test_files/tmp") / self.session_id
        self.logger = LoggingConfig.get_component_file_logger(
            self.session_id,
            "memory_eval",
            log_to_console=verbose,
        )

    def _make_llm(self, model: str, label: str, temperature: float = 0.0) -> OllamaService:
        base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        llm_logger = LoggingConfig.get_component_file_logger(
            self.session_id,
            f"ollama_{label}",
            log_to_console=False,
        )
        return OllamaService(
            {
                "base_url": base_url,
                "model": model,
                "temperature": temperature,
                "stream": False,
                "logger": llm_logger,
            }
        )

    def validate_only(self) -> Dict[str, Any]:
        """Load fixture and report structure without calling Ollama."""
        fixture = load_fixture(self.fixture_name)
        summary = {
            "session_id": self.session_id,
            "fixture": fixture.get("id"),
            "fixture_path": fixture.get("_fixture_path"),
            "gates_requested": list(self.gates),
            "available_fixtures": list_fixtures(),
            "digest_cases": len(fixture.get("digest_cases") or []),
            "seed_entries": len((fixture.get("seed_conversations") or {}).get("entries") or []),
            "rag_queries": len(fixture.get("rag_queries") or []),
            "required_entities": [e.get("name") for e in (fixture.get("required_entities") or [])],
            "thresholds": fixture.get("thresholds"),
            "validate_only": True,
            "passed": True,
        }
        return summary

    async def run_async(self) -> Dict[str, Any]:
        fixture = load_fixture(self.fixture_name)
        self.work_dir.mkdir(parents=True, exist_ok=True)

        llm_model = os.getenv("OLLAMA_MODEL", "gemma3")
        embed_model = os.getenv("OLLAMA_EMBED_MODEL", "mxbai-embed-large")

        digest_llm = self._make_llm(llm_model, "digest", temperature=0.0)
        judge_llm = self._make_llm(llm_model, "judge", temperature=0.1)
        embeddings_llm = self._make_llm(embed_model, "embeddings", temperature=0.0)
        graph_llm = self._make_llm(llm_model, "graph", temperature=0.0)

        gate_results: Dict[str, Any] = {}
        failures: List[str] = []

        if "digest" in self.gates:
            self.logger.info("Running digest gate")
            gate_results["digest"] = run_digest_gate(
                fixture, digest_llm, judge_llm, logger_=self.logger
            )
            if not gate_results["digest"]["passed"]:
                failures.append("digest")

        if "rag" in self.gates:
            self.logger.info("Running RAG gate")
            gate_results["rag"] = run_rag_gate(
                fixture,
                embeddings_llm,
                work_dir=self.work_dir / "rag",
                logger_=self.logger,
            )
            if not gate_results["rag"]["passed"]:
                failures.append("rag")

        if "graph" in self.gates:
            self.logger.info("Running graph gate (in-process)")
            gate_results["graph"] = await run_graph_gate(
                fixture,
                graph_llm,
                embeddings_llm,
                work_dir=self.work_dir / "graph",
                logger_=self.logger,
            )
            if not gate_results["graph"]["passed"]:
                failures.append("graph")

        summary: Dict[str, Any] = {
            "session_id": self.session_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "fixture": fixture.get("id"),
            "fixture_path": fixture.get("_fixture_path"),
            "ollama_base_url": os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
            "ollama_model": llm_model,
            "ollama_embed_model": embed_model,
            "gates_requested": list(self.gates),
            "gates": gate_results,
            "failed_gates": failures,
            "passed": len(failures) == 0,
            "work_dir": str(self.work_dir),
            "guidance": (
                "Iterate only on failing gates: digest prompts/taxonomy, "
                "RAG filters/embeddings, or graph entity prompts/similarity_threshold."
            ),
        }
        return summary

    def run(self) -> Dict[str, Any]:
        return asyncio.run(self.run_async())


def run_eval(
    fixture_name: str = "lost_valley_dnd",
    gates: Optional[Sequence[str]] = None,
    work_dir: Optional[Path] = None,
    validate_only: bool = False,
    verbose: bool = False,
) -> Dict[str, Any]:
    runner = EvalRunner(
        fixture_name=fixture_name,
        gates=gates,
        work_dir=work_dir,
        verbose=verbose,
    )
    if validate_only:
        return runner.validate_only()
    return runner.run()


def write_summary(summary: Dict[str, Any], output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)
    return output_path
