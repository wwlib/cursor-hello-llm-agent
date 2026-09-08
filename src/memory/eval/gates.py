"""Three quality gates for memory evaluation: digest, RAG, graph."""

from __future__ import annotations

import logging
import uuid
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Set

from src.memory.digest_generator import DigestGenerator
from src.memory.embeddings_manager import EmbeddingsManager
from src.memory.eval.digest_judge import create_evaluation_prompt, parse_evaluation_response
from src.memory.graph_memory.graph_manager import GraphManager
from src.memory.rag_manager import RAGManager

logger = logging.getLogger(__name__)

GRAPH_SEGMENT_TYPES = {"information", "action"}
MIN_IMPORTANCE = 3


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _node_name(node: Any) -> str:
    if hasattr(node, "name"):
        return str(node.name)
    if isinstance(node, dict):
        return str(node.get("name", ""))
    return ""


def _node_type(node: Any) -> str:
    if hasattr(node, "type"):
        return str(node.type)
    if isinstance(node, dict):
        return str(node.get("type", ""))
    return ""


def eligible_graph_segments(entries: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Extract memory-worthy, high-importance information/action segments."""
    segments: List[Dict[str, Any]] = []
    for entry in entries:
        digest = entry.get("digest") or {}
        for idx, seg in enumerate(digest.get("rated_segments") or []):
            if not seg.get("memory_worthy", True):
                continue
            if int(seg.get("importance", 0)) < MIN_IMPORTANCE:
                continue
            if seg.get("type") not in GRAPH_SEGMENT_TYPES:
                continue
            segments.append(
                {
                    "text": seg["text"],
                    "guid": f"{entry.get('guid', 'entry')}_seg_{idx}",
                    "importance": seg.get("importance"),
                    "type": seg.get("type"),
                }
            )
    return segments


def run_digest_gate(
    fixture: Dict[str, Any],
    digest_llm,
    judge_llm,
    *,
    logger_: Optional[logging.Logger] = None,
) -> Dict[str, Any]:
    """Generate digests and score them with an LLM judge."""
    log = logger_ or logger
    thresholds = fixture.get("thresholds", {})
    overall_min = float(thresholds.get("digest_overall_min", 6.0))
    topic_rel_min = float(thresholds.get("digest_topic_relevance_min", 6.0))
    topic_con_min = float(thresholds.get("digest_topic_consistency_min", 6.0))
    domain_name = fixture.get("domain_name", "general")
    domain_config = fixture.get("domain_config") or {}

    generator = DigestGenerator(
        digest_llm,
        domain_name=domain_name,
        domain_config=domain_config,
        logger=log,
    )

    case_results: List[Dict[str, Any]] = []
    failures: List[str] = []

    for case in fixture.get("digest_cases") or []:
        entry = {
            "guid": case.get("id") or str(uuid.uuid4()),
            "role": case.get("role", "system"),
            "content": case["content"],
            "timestamp": _utc_now(),
        }
        digest = generator.generate_digest(entry)
        segments = digest.get("rated_segments") or []

        prompt = create_evaluation_prompt(case["content"], digest, domain_name)
        raw = judge_llm.generate(prompt, options={"temperature": 0.1})
        evaluation = parse_evaluation_response(raw if isinstance(raw, str) else str(raw))

        overall = float(evaluation.get("overall_score") or 0)
        scores = evaluation.get("scores") or {}
        topic_rel = float(scores.get("topic_relevance") or 0)
        topic_con = float(scores.get("topic_consistency") or 0)

        case_ok = (
            len(segments) > 0
            and overall >= overall_min
            and topic_rel >= topic_rel_min
            and topic_con >= topic_con_min
        )
        if not case_ok:
            failures.append(
                f"{case.get('id')}: overall={overall}, topic_relevance={topic_rel}, "
                f"topic_consistency={topic_con}, segments={len(segments)}"
            )

        case_results.append(
            {
                "id": case.get("id"),
                "passed": case_ok,
                "segment_count": len(segments),
                "overall_score": overall,
                "scores": scores,
                "strengths": evaluation.get("strengths"),
                "weaknesses": evaluation.get("weaknesses"),
            }
        )

    passed = len(failures) == 0 and len(case_results) > 0
    return {
        "gate": "digest",
        "passed": passed,
        "failures": failures,
        "cases": case_results,
        "thresholds": {
            "digest_overall_min": overall_min,
            "digest_topic_relevance_min": topic_rel_min,
            "digest_topic_consistency_min": topic_con_min,
        },
    }


def run_rag_gate(
    fixture: Dict[str, Any],
    embeddings_llm,
    *,
    work_dir: Path,
    logger_: Optional[logging.Logger] = None,
) -> Dict[str, Any]:
    """Index seed digests and check top-k retrieval for fixed queries."""
    log = logger_ or logger
    thresholds = fixture.get("thresholds", {})
    min_matching = int(thresholds.get("rag_min_matching_queries", 4))

    entries = (fixture.get("seed_conversations") or {}).get("entries") or []
    if not entries:
        return {
            "gate": "rag",
            "passed": False,
            "failures": ["No seed_conversations.entries in fixture"],
            "queries": [],
        }

    work_dir.mkdir(parents=True, exist_ok=True)
    embeddings_file = work_dir / "eval_embeddings.jsonl"
    if embeddings_file.exists():
        embeddings_file.unlink()

    embeddings_manager = EmbeddingsManager(str(embeddings_file), llm_service=embeddings_llm, logger=log)
    ok = embeddings_manager.update_embeddings(entries)
    if not ok:
        return {
            "gate": "rag",
            "passed": False,
            "failures": ["EmbeddingsManager.update_embeddings failed"],
            "queries": [],
        }

    rag = RAGManager(embeddings_llm, embeddings_manager, logger=log)
    query_results: List[Dict[str, Any]] = []
    failures: List[str] = []
    matched = 0

    for q in fixture.get("rag_queries") or []:
        limit = int(q.get("limit", 5))
        hits = rag.query(q["query"], limit=limit, min_importance=MIN_IMPORTANCE)
        texts = [str(h.get("text", "")) for h in hits]
        combined = " ".join(texts).lower()
        expected = q.get("expected_substrings") or []
        missing = [s for s in expected if s.lower() not in combined]
        hit_ok = len(missing) == 0 and len(hits) > 0
        if hit_ok:
            matched += 1
        else:
            failures.append(
                f"{q.get('id')}: missing={missing}, hit_count={len(hits)}"
            )

        query_results.append(
            {
                "id": q.get("id"),
                "query": q["query"],
                "passed": hit_ok,
                "expected_substrings": expected,
                "missing_substrings": missing,
                "hit_count": len(hits),
                "top_texts": texts[:3],
                "top_scores": [h.get("score") for h in hits[:3]],
            }
        )

    passed = matched >= min_matching and len(query_results) > 0
    if matched < min_matching:
        failures.append(f"matched_queries={matched} < required={min_matching}")

    return {
        "gate": "rag",
        "passed": passed,
        "failures": failures,
        "matched_queries": matched,
        "total_queries": len(query_results),
        "queries": query_results,
        "thresholds": {"rag_min_matching_queries": min_matching},
        "embeddings_file": str(embeddings_file),
    }


async def run_graph_gate(
    fixture: Dict[str, Any],
    llm_service,
    embeddings_llm,
    *,
    work_dir: Path,
    logger_: Optional[logging.Logger] = None,
) -> Dict[str, Any]:
    """In-process graph extraction; assert required entities and low duplicates."""
    log = logger_ or logger
    thresholds = fixture.get("thresholds", {})
    max_dup_groups = int(thresholds.get("graph_max_duplicate_groups", 0))
    max_haven = int(thresholds.get("graph_max_nodes_named_haven", 1))
    domain_config = fixture.get("domain_config") or {}

    entries = (fixture.get("seed_conversations") or {}).get("entries") or []
    segments = eligible_graph_segments(entries)
    if not segments:
        return {
            "gate": "graph",
            "passed": False,
            "failures": ["No eligible segments for graph processing"],
            "entities_found": [],
        }

    work_dir.mkdir(parents=True, exist_ok=True)
    storage_path = work_dir / "graph_data"
    storage_path.mkdir(parents=True, exist_ok=True)
    embeddings_file = work_dir / "graph_embeddings.jsonl"
    if embeddings_file.exists():
        embeddings_file.unlink()

    embeddings_manager = EmbeddingsManager(str(embeddings_file), llm_service=embeddings_llm, logger=log)
    graph_manager = GraphManager(
        storage_path=str(storage_path),
        embeddings_manager=embeddings_manager,
        llm_service=llm_service,
        embeddings_llm_service=embeddings_llm,
        domain_config=domain_config,
        logger=log,
        memory_guid=f"eval_graph_{uuid.uuid4().hex[:8]}",
    )

    processed = 0
    process_errors: List[str] = []
    for seg in segments:
        result = await graph_manager.process_conversation_entry_with_resolver_async(
            conversation_text=seg["text"],
            digest_text="",
            conversation_guid=seg["guid"],
        )
        if result.get("error"):
            process_errors.append(f"{seg['guid']}: {result['error']}")
        else:
            processed += 1

    nodes = list(graph_manager.nodes.values())
    names_lower = [_node_name(n).strip().lower() for n in nodes if _node_name(n).strip()]

    # Duplicate groups: same (type, name.lower()) appearing more than once
    type_name_counts: Dict[tuple, int] = defaultdict(int)
    for n in nodes:
        key = (_node_type(n).lower(), _node_name(n).strip().lower())
        if key[1]:
            type_name_counts[key] += 1
    duplicate_groups = [
        {"type": t, "name": name, "count": count}
        for (t, name), count in type_name_counts.items()
        if count > 1
    ]

    haven_count = sum(1 for name in names_lower if name == "haven")

    required = fixture.get("required_entities") or []
    missing_required: List[str] = []
    found_required: List[str] = []
    name_set: Set[str] = set(names_lower)
    for req in required:
        req_name = str(req.get("name", "")).strip()
        if not req_name:
            continue
        if req_name.lower() in name_set:
            found_required.append(req_name)
        else:
            # soft alias: substring match on node names (e.g. "Lost Valley")
            if any(req_name.lower() in n or n in req_name.lower() for n in name_set):
                found_required.append(req_name)
            else:
                missing_required.append(req_name)

    failures: List[str] = []
    if process_errors:
        failures.extend(process_errors)
    if len(duplicate_groups) > max_dup_groups:
        failures.append(
            f"duplicate_groups={len(duplicate_groups)} > max={max_dup_groups}: {duplicate_groups}"
        )
    if haven_count > max_haven:
        failures.append(f"Haven nodes={haven_count} > max={max_haven}")
    if missing_required:
        failures.append(f"missing_required_entities={missing_required}")
    if processed == 0:
        failures.append("No segments processed successfully")

    return {
        "gate": "graph",
        "passed": len(failures) == 0,
        "failures": failures,
        "segments_eligible": len(segments),
        "segments_processed": processed,
        "node_count": len(nodes),
        "edge_count": len(graph_manager.edges),
        "entities_found": sorted({_node_name(n) for n in nodes if _node_name(n)}),
        "required_found": found_required,
        "required_missing": missing_required,
        "duplicate_groups": duplicate_groups,
        "haven_node_count": haven_count,
        "thresholds": {
            "graph_max_duplicate_groups": max_dup_groups,
            "graph_max_nodes_named_haven": max_haven,
        },
        "storage_path": str(storage_path),
    }
