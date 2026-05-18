"""RetroDoc Bot — entry point.

Usage
-----
  # Single file, RAG approach (default)
  python -m agents.main path/to/module.py

  # Single file, prompt-based approach
  python -m agents.main path/to/module.py --approach prompt

  # Benchmark both approaches side-by-side
  python -m agents.main path/to/module.py --approach benchmark

  # Resume / continue an existing Cosmos DB session
  python -m agents.main path/to/module.py --session-id <uuid>
"""
import argparse
from pathlib import Path

from backend.agents.rag.rag import RAGApproach
from backend.agents.prompt_based.prompt_based import PromptBasedApproach
from backend.agents.memory.cosmos_history import CosmosSessionHistory
# from eval.runner import BenchmarkRunner


def _read_code(path: Path) -> str:
    if path.is_file():
        return path.read_text(encoding="utf-8")
    raise ValueError(f"{path} is not a readable file. Pass a single source file.")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="RetroDoc Bot – AI documentation generator for code."
    )
    parser.add_argument("input", help="Path to the source code file to document")
    parser.add_argument(
        "--approach",
        choices=["rag", "prompt", "benchmark"],
        default="rag",
        help="Generation strategy (default: rag)",
    )
    parser.add_argument(
        "--session-id",
        default=None,
        help="Cosmos DB session ID to resume (creates a new one if omitted)",
    )
    args = parser.parse_args()

    source_path = Path(args.input)
    if not source_path.exists():
        print(f"[error] File not found: {source_path}")
        return

    code = _read_code(source_path)

    if args.approach == "benchmark":
        # runner = BenchmarkRunner()
        # results = runner.run(code, label=source_path.name)
        # runner.print_summary(results)
        # for name, data in results.items():
        #     out_path = source_path.parent / f"{source_path.stem}_doc_{name}.md"
        #     out_path.write_text(data["output"], encoding="utf-8")
        #     print(f"[{name}] → {out_path}")
        return

    history = CosmosSessionHistory(session_id=args.session_id)
    approach_name = args.approach  # "rag" or "prompt"

    approach = RAGApproach() if approach_name == "rag" else PromptBasedApproach()
    documentation = approach.generate_documentation(code)

    out_path = source_path.parent / f"{source_path.stem}_doc.md"
    out_path.write_text(documentation, encoding="utf-8")
    print(f"[{approach_name}] Documentation saved → {out_path}")
    history.save(approach=approach_name, code=code, documentation=documentation)
    print(f"Session ID: {history.session_id}")


if __name__ == "__main__":
    main()
