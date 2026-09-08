# Memory eval loop

Portable three-gate quality measurement for the memory stack (digest → RAG → graph).

Lives under `src/memory/eval/` so it can move with a future memory-only repo. It does **not** depend on agent, API, or web UI code. Graph scoring uses **in-process** `GraphManager` (not the standalone queue/launcher) for deterministic gates.

## Gates

| Gate | What it measures | Pass criteria (fixture defaults) |
|------|------------------|----------------------------------|
| `digest` | LLM-as-judge on generated digests | overall / topic scores ≥ 6 |
| `rag` | Top-k retrieval over seed digests | ≥ 4 of 5 fixed queries hit expected substrings |
| `graph` | Entity extraction + resolution | required entities present; no duplicate (type, name); ≤1 Haven |

**Iterate only on failing gates** (digest prompts/taxonomy, RAG filters, entity prompts / `similarity_threshold`).

## Run

From project root:

```bash
# Structure check (no Ollama)
python scripts/eval_rag_graph_loop.py --validate-only

# Full loop
export DEV_MODE=true
export OLLAMA_BASE_URL=http://192.168.10.28:11434   # or localhost
export OLLAMA_MODEL=gemma3
export OLLAMA_EMBED_MODEL=mxbai-embed-large

python scripts/eval_rag_graph_loop.py --verbose

# Single gate
python scripts/eval_rag_graph_loop.py --gates rag
python scripts/eval_rag_graph_loop.py --gates graph
```

Exit code `0` = all requested gates passed; `1` = failure. Summary JSON defaults to `logs/eval_summary_<timestamp>.json`. Temp artifacts under `tests/test_files/tmp/<session_id>/`.

## Fixture

`fixtures/lost_valley_dnd.json` is self-contained (includes `domain_config`) for extraction readiness.

- `digest_cases` — raw text for digest generation + judge
- `seed_conversations` — stable pre-digested entries for RAG/graph (independent of digest gate flakiness)
- `rag_queries` — fixed questions + expected substrings
- `required_entities` — names that must appear in the graph

Add new fixtures as JSON beside this file; load with `--fixture <stem>`.

## Layout

```
src/memory/eval/
  digest_judge.py   # LLM-as-judge prompt/parse
  gates.py          # digest / rag / graph gate implementations
  runner.py         # orchestration + JSON summary
  fixtures/         # fixed eval datasets
scripts/eval_rag_graph_loop.py
```
