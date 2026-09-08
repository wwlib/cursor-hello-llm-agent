# Project Status — September 7, 2026

Re-entry notes after a multi-month pause. Goal remains: a **local Ollama agent memory system** whose interesting core is a **rudimentary knowledge graph paired with RAG**.

This document captures assessment, priorities, the planned self-improvement loop, and how to test. Prefer this (and the code) over older phase docs where they conflict.

---

## Current posture

Maturity: late prototype / research framework. Substantial working subsystems; docs and code sometimes drift.

**Trust for “what is current”:**
- Code under `src/memory/` and `src/memory/graph_memory/`
- `launcher.py` / `graph_manager_process.py`
- `docs/phase-6/GRAPH_MANAGER_STANDALONE_ARCHITECTURE.md`
- Component READMEs (especially `tests/graph_memory/README-graph-memory-tests.md`)

**Treat as archaeology / often stale:**
- Week-3 in-process background-processor / profile docs
- Mentions of `AsyncMemoryManager` (gone; API uses `MemoryManager`)
- MCP as “next” / “ready”
- CLAUDE.md language that still frames standalone GraphManager as only a *plan* (core path is implemented)

Going forward, focus on **graph-RAG memory**, not MCP, STT/TTS, or more API/UI surface.

---

## What already works

1. **Segment memory + RAG** — digests, importance filtering, embeddings, compression, prompt injection (`MemoryManager`, `DigestGenerator`, `EmbeddingsManager`, `RAGManager`)
2. **Rudimentary knowledge graph** — entity/relationship extraction, similarity-based entity resolution, JSON graph files
3. **Graph isolation** — agent writes `conversation_queue.jsonl` via `QueueWriter`; standalone process updates graph files; agent reads via `StandaloneGraphQueries` and can run even if the process is down
4. **Thin agent + domain configs** — `src/agent/agent.py`, `examples/domain_configs.py` (dnd, lab_assistant, user_story)

### Key paths

| Role | Path |
|------|------|
| Agent | `src/agent/agent.py` |
| Memory | `src/memory/memory_manager.py` |
| Simple memory | `src/memory/simple_memory_manager.py` |
| Digest / RAG / embeddings / compress | `digest_generator.py`, `rag_manager.py`, `embeddings_manager.py`, `memory_compressor.py` |
| Graph queue / queries | `graph_memory/queue_writer.py`, `standalone_graph_queries.py` |
| Graph core | `graph_manager.py`, `entity_extractor.py`, `relationship_extractor.py`, `entity_resolver.py`, `graph_storage.py` |
| Standalone process | `graph_manager_process.py`, `launcher.py` |
| Domains / CLI | `examples/domain_configs.py`, `examples/agent_usage_example.py` |

---

## Architectural debt / gaps

- Doc/code drift (AsyncMemoryManager, week-3 in-process profiles, MCP, missing `populate_queue_from_conversations.py` referenced in docs)
- Orphaned / unwired graph helpers (`config.py`, `monitor.py`, `context_retriever.py`, in-process `background_processor.py`)
- Obsolete sync APIs marked `TODO: OBSOLETE - REMOVE` in `graph_manager.py` and `entity_extractor.py`
- Inconsistent graph queue payload helpers (filtered segments vs raw content)
- `has_pending_operations` appears broken (pending digests/embeddings never tracked)
- Sync `create_task` from `query_memory` can be fragile without a running event loop
- Watchdog-based graph reload not implemented (TTL/cache only)
- Standalone graph path under-tested relative to its importance
- README “production-ready” tone overstated for a research codebase

---

## What merits further development

Ranked for local Ollama + KG + RAG:

1. **Harden the graph ↔ agent loop** (highest value)  
   Single clean write path into the queue; stronger process recovery/batching/logging; better graph reload for queries; real E2E test: queue → process → files → `get_graph_context`.

2. **Graph quality for small models**  
   Tighter domain prompts/schemas; entity resolution thresholds/merges; observability of extract/merge/drop decisions. EntityResolver quality (useful nodes, few duplicates) is the north star.

3. **Prune dual-era graph code**  
   Remove obsolete sync paths and unwired week-3 modules as they block clarity—not as a separate mega-cleanup.

4. **Small correctness fixes in the memory pipeline**  
   Pending-ops tracking; async task creation from sync query path.

### Deprioritize for now

| Area | Why |
|------|-----|
| MCP / Phase 7 expansion | Orthogonal to memory quality |
| Web UI / API polish | Demo layer, not the research core |
| Faiss / SQLite / supervisord | Premature until file-queue path is solid |
| Broader “agent platform” ambitions | Interesting bit is the memory stack |

---

## Self-improvement loop (development compass)

**Build measurement first; let failures decide what to change.**

Do **not** lead with `run_automated_tests.py` for daily iteration. That suite is partly stale and scores structural memory/logs, not RAG hit-rate or graph quality.

### Loop

**Fixed fixture → three gates → JSON score → fix only the failing gate → re-run**

| Gate | Signal | Existing pieces |
|------|--------|-----------------|
| Digest | LLM-as-judge ≈ ≥6/10 | `tests/memory_manager/test_digest_generator.py` |
| RAG | Fixed queries hit expected segments in top-k | RAG snapshots + `test_rag_manager_integration.py` |
| Graph | Required entities present; low duplicate rate | `tests/graph_memory/` + `sample_data/` |

**Iteration rule:** only change the failing subsystem (digest prompts, embedding/RAG filters, entity/relationship prompts or `similarity_threshold` in `domain_configs.py`). Do not touch agent/API/UI while a gate is red.

**Implemented (Sep 2026):** portable package `src/memory/eval/` + CLI `scripts/eval_rag_graph_loop.py`. Fixture: `lost_valley_dnd`. See `src/memory/eval/README.md`.

```bash
python scripts/eval_rag_graph_loop.py --validate-only
python scripts/eval_rag_graph_loop.py --verbose
```

Designed to move with a future memory-only repo (no agent/API dependency; graph gate is in-process, not launcher/queue).

### Suggested build order

1. Define a fixed D&D fixture (10–20 turns + 5–10 questions with expected evidence).
2. Wire the three-gate eval.
3. Document/script the golden path: agent CLI + `launcher.py` + that eval; refresh README/CLAUDE.md to match.
4. Prune obsolete graph code only as it blocks the loop.
5. Improve where the eval fails (typical order: digest → entity duplicates → RAG hit rate → graph context in prompts).
6. Optional weekly: `python run_automated_tests.py --quick` as coarse smoke, not the optimization signal.

### “Done enough”

After months away, one command should tell you: digests still sensible, retrieval still finds the right memories, graph isn’t duplicating entities, and which gate broke if something regressed.

---

## How to test (reminder)

### Measurement loop (primary compass for graph-RAG)

```bash
python scripts/eval_rag_graph_loop.py --validate-only
export DEV_MODE=true OLLAMA_BASE_URL=http://192.168.10.28:11434 \
  OLLAMA_MODEL=gemma3 OLLAMA_EMBED_MODEL=mxbai-embed-large
python scripts/eval_rag_graph_loop.py --verbose
# Single gate while iterating:
python scripts/eval_rag_graph_loop.py --gates digest
python scripts/eval_rag_graph_loop.py --gates rag
python scripts/eval_rag_graph_loop.py --gates graph
```

No-Ollama unit checks: `pytest tests/memory_manager/test_memory_eval_loop.py -v`  
Docs: `src/memory/eval/README.md`

### Setup

```bash
source .venv/bin/activate
pip install -e .
pip install -r requirements.txt

export DEV_MODE=true
export OLLAMA_BASE_URL=http://192.168.10.28:11434   # or localhost / other host
export OLLAMA_MODEL=gemma3
export OLLAMA_EMBED_MODEL=mxbai-embed-large

curl -s "$OLLAMA_BASE_URL/api/tags" | head -n 20
```

Models needed: `gemma3`, `mxbai-embed-large`.

### Philosophy

1. Run the three-gate eval; fix only failing gates.
2. Test subsystems (digest, embeddings/RAG, graph) in isolation.
3. Then run the integrated agent.
4. Prefer real LLM tests for graph quality; mocks for fast unit checks.

### Graph-RAG tests (primary)

```bash
# Fast unit (no Ollama)
pytest tests/graph_memory/test_entity_resolver.py -v

# Real LLM — entity resolution (most important)
OLLAMA_BASE_URL=$OLLAMA_BASE_URL OLLAMA_MODEL=gemma3 OLLAMA_EMBED_MODEL=mxbai-embed-large \
  pytest tests/graph_memory/test_entity_resolver_real_llm.py -v

# Real LLM — relationships
OLLAMA_BASE_URL=$OLLAMA_BASE_URL OLLAMA_MODEL=gemma3 OLLAMA_EMBED_MODEL=mxbai-embed-large \
  pytest tests/graph_memory/test_relationship_extractor_real_llm.py -v

# All graph tests
pytest tests/graph_memory/ -v
```

Fixtures: `tests/graph_memory/sample_data/`. Temp output: `tests/test_files/tmp/`. Logs: `tests/graph_memory/logs/`.  
Details: `tests/graph_memory/README-graph-memory-tests.md`.

### RAG / memory subsystem tests

```bash
pytest tests/memory_manager/test_rag_manager_integration.py -v
pytest tests/memory_manager/test_embeddings_manager_integration.py -v
pytest tests/memory_manager/test_digest_generator.py -v
pytest tests/memory_manager/test_graph_memory_integration.py -v

# Skip Ollama-backed integration tests
pytest tests/ -v -m "not integration"
```

Integration tests that need external services use `@pytest.mark.integration` (see `pyproject.toml`).

### Manual golden path (graph + agent)

```bash
# Terminal 1 — graph process (same --guid / --config as agent)
export DEV_MODE=true OLLAMA_BASE_URL=http://192.168.10.28:11434 \
  OLLAMA_MODEL=gemma3 OLLAMA_EMBED_MODEL=mxbai-embed-large
python launcher.py --verbose --guid my_session --config dnd

# Terminal 2 — agent
export DEV_MODE=true OLLAMA_BASE_URL=http://192.168.10.28:11434 \
  OLLAMA_MODEL=gemma3 OLLAMA_EMBED_MODEL=mxbai-embed-large
python examples/agent_usage_example.py --verbose --guid my_session --config dnd
```

Agent works without the launcher (reads existing graph files if any). With the launcher running, new entries are queued and the graph updates asynchronously.

Other demos:
```bash
python examples/graph_memory_example.py
python examples/digest_generator_example.py
```

### Broader suite (secondary)

```bash
pytest tests/ -v -s

python run_automated_tests.py --quick
python run_automated_tests.py --domain dnd
```

Persona E2E is useful later as smoke; not the daily graph-RAG signal.

### Artifacts to inspect

| Artifact | Path |
|----------|------|
| Session memory | `agent_memories/standard/{guid}/` |
| Graph files | `.../agent_memory_graph_data/graph_nodes.json`, `graph_edges.json` |
| Graph logs | `.../agent_memory_graph_data/graph_verbose.log` |
| Test graph logs | `tests/graph_memory/logs/` |

---

## Recent commit note (Aug 2026 session)

Committed useful WIP; left logger scratch and `.specstory` uncommitted:

- `SimpleMemoryManager` accepts MemoryManager-compatible kwargs and reads `"query"` from query context so `--type simple` works with `agent_usage_example.py`
- README formatting fixes
- Phase 6 getting-started command refresh
- Added `tests/memory_manager/test_llm_determinism_preprocessor.py`

Left out on purpose: `tests/memory_manager/test_logger.py`, `tests/test_logger.log`, `.specstory/*`.

---

## Bottom line

Keep developing the **memory core (RAG + standalone graph)**. Use `scripts/eval_rag_graph_loop.py` as the self-improvement compass: fix failing gates before adding features. Park surrounding product surface until those scores are trustworthy after another long pause.

**Near-term extraction:** `src/memory/` (including `eval/`) is intentionally separable from agent/API/UI. When splitting to its own repo, take `src/memory/`, `src/ai/` (LLM interface), shared logging utils, the eval CLI, and fixtures; leave agent, API, and web UI behind.
