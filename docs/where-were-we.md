# Where Were We — Handoff (September 7, 2026)

**Resume here after machine switch / context compress.**  
Companion detail: [`status-september-07-2026.md`](status-september-07-2026.md). Eval how-to: [`../src/memory/eval/README.md`](../src/memory/eval/README.md).

---

## One-sentence goal

Local **Ollama** agent memory: **RAG + rudimentary knowledge graph**, with a measurement loop that decides what to change next.

---

## What we decided (do not re-litigate)

1. **Focus = graph-RAG memory**, not MCP / STT-TTS / API-UI polish.
2. **Build measurement first** — three gates (digest → RAG → graph); fix only failing gates.
3. **Near future:** extract `src/memory/` (plus `src/ai/`, logging utils, eval CLI) into its **own repo**. Keep new memory work portable; avoid new agent/API coupling.
4. Prefer **code + this doc + status-september-07-2026** over older phase “week status” / CLAUDE.md plan language when they conflict.
5. Standalone GraphManager (`launcher.py` + queue) is the **production** path; eval graph gate uses **in-process** GraphManager for deterministic scoring.

---

## Just finished (must be on the branch you pull)

| Item | Location |
|------|----------|
| Three-gate eval package | `src/memory/eval/` |
| Lost Valley fixture (self-contained `domain_config`) | `src/memory/eval/fixtures/lost_valley_dnd.json` |
| CLI | `scripts/eval_rag_graph_loop.py` |
| Unit tests (no Ollama) | `tests/memory_manager/test_memory_eval_loop.py` |
| Re-entry status notes | `docs/status-september-07-2026.md` |
| Earlier: SimpleMemoryManager ↔ `agent_usage_example` fix | commit `2a28ceb` |

**Not committed on purpose (ignore / don’t bring):** `.specstory/*`, `tests/memory_manager/test_logger.py`, `tests/test_logger.log`, local `.vscode/settings.json` unless you care.

**Full LLM eval was not run in the last session** — Ollama was unreachable from that environment. First thing on the new machine: run the loop for real.

---

## First 15 minutes on the new machine

```bash
git pull   # or clone
python3 -m venv .venv && source .venv/bin/activate
pip install -e . && pip install -r requirements.txt

export DEV_MODE=true
export OLLAMA_BASE_URL=http://192.168.10.28:11434   # change to your host
export OLLAMA_MODEL=gemma3
export OLLAMA_EMBED_MODEL=mxbai-embed-large

curl -s "$OLLAMA_BASE_URL/api/tags" | head -n 20
# Need: gemma3, mxbai-embed-large

pytest tests/memory_manager/test_memory_eval_loop.py -v
python scripts/eval_rag_graph_loop.py --validate-only
python scripts/eval_rag_graph_loop.py --verbose
```

Exit `0` = all gates green. Summaries: `logs/eval_summary_*.json`.  
Iterate: `--gates digest` | `rag` | `graph` — change only the failing subsystem.

---

## Next development steps (in order)

1. **Establish baseline** — full eval against your Ollama; save the JSON summary.
2. **Fix whatever fails** — typical order: digest quality → entity duplicates → RAG hit rate → graph context usefulness.
3. **Harden agent ↔ graph file loop** (when eval is green enough): single clean `QueueWriter` path, process recovery, better graph reload for queries, optional E2E smoke with `launcher.py`.
4. **Prune** obsolete sync graph APIs / unwired week-3 modules as you touch them.
5. **Then** consider memory-only repo split.

Deprioritize: MCP, Web UI polish, Faiss/SQLite/supervisord, persona `run_automated_tests.py` as daily signal (weekly smoke only).

---

## Golden paths (manual)

**Eval (compass):**
```bash
python scripts/eval_rag_graph_loop.py --verbose
```

**Agent + standalone graph (same `--guid` / `--config`):**
```bash
# Terminal 1
python launcher.py --verbose --guid my_session --config dnd

# Terminal 2
python examples/agent_usage_example.py --verbose --guid my_session --config dnd
```

Agent works without launcher (reads existing graph files if any).

**Subsystem pytest (graph quality):**
```bash
pytest tests/graph_memory/test_entity_resolver.py -v
OLLAMA_BASE_URL=$OLLAMA_BASE_URL OLLAMA_MODEL=gemma3 OLLAMA_EMBED_MODEL=mxbai-embed-large \
  pytest tests/graph_memory/test_entity_resolver_real_llm.py -v
```

EntityResolver quality (useful nodes, few duplicates) remains the graph north star.  
Details: `tests/graph_memory/README-graph-memory-tests.md`.

---

## Architecture snapshot

```
Agent → MemoryManager
          ├─ Digest → Embeddings → RAG → prompt
          ├─ QueueWriter → conversation_queue.jsonl
          └─ StandaloneGraphQueries ← graph_*.json (read-only)

launcher.py → graph_manager_process → GraphManager (writes graph files)
```

Eval graph gate: **in-process** `GraphManager.process_conversation_entry_with_resolver_async` (not the queue).

Known debt worth remembering:
- `has_pending_operations` looks broken (pending digests/embeddings never tracked)
- Dual/inconsistent queue helpers; obsolete sync extractors (`TODO: OBSOLETE - REMOVE`)
- Docs still mention missing `populate_queue_from_conversations.py`, AsyncMemoryManager, MCP
- CLAUDE.md still frames standalone GraphManager as a “plan” — it’s largely implemented

---

## Env / hosts (your lab)

| Role | Typical URL |
|------|-------------|
| Ollama M4 | `http://192.168.10.28:11434` |
| Ollama PC | `http://192.168.10.18:11434` |
| Local default in code | `http://localhost:11434` |

Always override with `OLLAMA_BASE_URL` on the machine you’re on.

---

## Artifacts after runs

| What | Where |
|------|--------|
| Eval summaries | `logs/eval_summary_*.json` |
| Eval temp graph/embeddings | `tests/test_files/tmp/<session_id>/` |
| Agent session memory | `agent_memories/standard/{guid}/` |
| Graph files | `.../agent_memory_graph_data/graph_nodes.json`, `graph_edges.json` |
| Graph process log | `.../agent_memory_graph_data/graph_verbose.log` / `graph_manager.log` |

---

## Docs trust ladder

1. This file + `docs/status-september-07-2026.md`
2. `src/memory/eval/README.md`, `tests/graph_memory/README-graph-memory-tests.md`
3. `docs/phase-6/GRAPH_MANAGER_STANDALONE_ARCHITECTURE.md`
4. Code under `src/memory/`
5. Older phase READMEs / week status / Medium article — archaeology; often aspirational

---

## Git note at handoff time

- Branch: `main` (was ahead of `origin/main` by at least the SimpleMemoryManager fix before this handoff commit).
- After pull on the new machine, confirm eval files exist: `ls src/memory/eval scripts/eval_rag_graph_loop.py`.
- Push from this machine before you leave if this commit isn’t on GitHub yet.

---

## Bottom line for the other machine

1. Pull.  
2. Point env at your Ollama.  
3. Run `python scripts/eval_rag_graph_loop.py --verbose`.  
4. Let the failing gate tell you what to change.  
5. Keep memory code extractable.
