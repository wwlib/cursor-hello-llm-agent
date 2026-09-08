#!/usr/bin/env python3
"""
Memory quality eval loop: digest → RAG → graph.

Run from project root. Requires Ollama unless --validate-only.

Examples:
  python scripts/eval_rag_graph_loop.py --validate-only
  python scripts/eval_rag_graph_loop.py --gates rag
  export DEV_MODE=true OLLAMA_BASE_URL=http://192.168.10.28:11434 \\
    OLLAMA_MODEL=gemma3 OLLAMA_EMBED_MODEL=mxbai-embed-large
  python scripts/eval_rag_graph_loop.py --verbose

Designed for the memory package; safe to move with a future memory-only repo.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

project_root = str(Path(__file__).resolve().parent.parent)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.memory.eval.runner import EvalRunner, write_summary  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run digest / RAG / graph memory quality gates"
    )
    parser.add_argument(
        "--fixture",
        default="lost_valley_dnd",
        help="Fixture name under src/memory/eval/fixtures/ (default: lost_valley_dnd)",
    )
    parser.add_argument(
        "--gates",
        default="digest,rag,graph",
        help="Comma-separated gates to run: digest,rag,graph",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="JSON summary path (default: logs/eval_summary_<timestamp>.json)",
    )
    parser.add_argument(
        "--work-dir",
        default=None,
        help="Working directory for temp embeddings/graph files",
    )
    parser.add_argument(
        "--validate-only",
        action="store_true",
        help="Load fixture and print structure without calling Ollama",
    )
    parser.add_argument("--verbose", action="store_true", help="Console logging")
    args = parser.parse_args()

    gates = [g.strip() for g in args.gates.split(",") if g.strip()]
    unknown = [g for g in gates if g not in {"digest", "rag", "graph"}]
    if unknown:
        print(f"Unknown gates: {unknown}", file=sys.stderr)
        return 2

    work_dir = Path(args.work_dir) if args.work_dir else None
    runner = EvalRunner(
        fixture_name=args.fixture,
        gates=gates,
        work_dir=work_dir,
        verbose=args.verbose,
    )

    if args.validate_only:
        summary = runner.validate_only()
    else:
        summary = runner.run()

    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    output = Path(args.output) if args.output else Path("logs") / f"eval_summary_{stamp}.json"
    write_summary(summary, output)

    print(json.dumps(
        {
            "passed": summary.get("passed"),
            "failed_gates": summary.get("failed_gates", []),
            "fixture": summary.get("fixture"),
            "output": str(output),
            "work_dir": summary.get("work_dir"),
            "validate_only": summary.get("validate_only", False),
        },
        indent=2,
    ))

    if summary.get("failed_gates"):
        print("\nFailing gate details:", file=sys.stderr)
        for name in summary["failed_gates"]:
            gate = (summary.get("gates") or {}).get(name) or {}
            print(f"  [{name}] {gate.get('failures')}", file=sys.stderr)

    return 0 if summary.get("passed") else 1


if __name__ == "__main__":
    raise SystemExit(main())
