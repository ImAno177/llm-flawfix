from __future__ import annotations

import argparse
import asyncio
from pathlib import Path
import sys
from time import strftime

from secure_code_eval.config import load_config
from secure_code_eval.datasets import download_securityeval, load_securityeval
from secure_code_eval.pipeline import Pipeline, parse_experiments


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    root = Path(__file__).resolve().parent

    if args.command == "prepare":
        dataset_path = download_securityeval(root / "data", force=args.force)
        tasks = load_securityeval(dataset_path)
        print(f"Prepared SecurityEval: {len(tasks)} tasks at {dataset_path}")
        return 0

    config = load_config(Path(args.config) if args.config else None)
    run_id = getattr(args, "run_id", None) or strftime("%Y%m%d-%H%M%S")
    pipeline = Pipeline(
        root=root,
        config=config,
        run_id=run_id,
        mock_llm=getattr(args, "mock_llm", False),
        max_concurrency=getattr(args, "max_concurrency", 16),
    )

    if args.command == "run":
        experiments = parse_experiments(args.experiments)
        asyncio.run(
            pipeline.run_experiments(
                experiments=experiments,
                limit=args.limit,
                skip_codeql=args.skip_codeql,
            )
        )
        print(f"Run complete: runs/{run_id}")
        return 0

    if args.command == "scan":
        experiments = parse_experiments(args.experiments)
        models = parse_models(args.models)
        outputs = pipeline.scan_many(experiments, models=models)
        print(f"Scan complete: {len(outputs)} SARIF files")
        return 0

    if args.command == "report":
        rows = pipeline.write_report(limit=args.limit)
        print(f"Report complete: {len(rows)} metric rows at runs/{run_id}/reports")
        return 0

    if args.command == "all":
        experiments = parse_experiments(args.experiments)
        download_securityeval(root / "data", force=args.force)
        asyncio.run(
            pipeline.run_experiments(
                experiments=experiments,
                limit=args.limit,
                skip_codeql=args.skip_codeql,
            )
        )
        if not args.skip_codeql:
            pipeline.scan_many(experiments, models=parse_models(args.models), skip_existing=True)
        pipeline.write_report(limit=args.limit)
        print(f"All done: runs/{run_id}")
        return 0

    parser.print_help()
    return 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run SecurityEval LLM security experiments.")
    sub = parser.add_subparsers(dest="command", required=True)

    prepare = sub.add_parser("prepare", help="Download SecurityEval.")
    prepare.add_argument("--force", action="store_true", help="Re-download the dataset.")

    def add_common(command_parser: argparse.ArgumentParser) -> None:
        command_parser.add_argument("--config", default="config.example.toml")
        command_parser.add_argument("--run-id", default=None)
        command_parser.add_argument("--limit", type=int, default=None)
        command_parser.add_argument("--mock-llm", action="store_true")
        command_parser.add_argument("--max-concurrency", type=int, default=16)

    run = sub.add_parser("run", help="Generate code and repair outputs.")
    add_common(run)
    run.add_argument("--experiments", default="all")
    run.add_argument("--skip-codeql", action="store_true", help="Skip CodeQL-dependent repair steps.")

    scan = sub.add_parser("scan", help="Run CodeQL over generated code.")
    scan.add_argument("--config", default="config.example.toml")
    scan.add_argument("--run-id", required=True)
    scan.add_argument("--experiments", default="all")
    scan.add_argument("--models", default="gemini,gemma", help="Comma-separated model aliases to scan.")

    report = sub.add_parser("report", help="Write CSV and Markdown reports.")
    report.add_argument("--config", default="config.example.toml")
    report.add_argument("--run-id", required=True)
    report.add_argument("--limit", type=int, default=None)

    all_cmd = sub.add_parser("all", help="Prepare, run, scan, and report.")
    add_common(all_cmd)
    all_cmd.add_argument("--experiments", default="all")
    all_cmd.add_argument("--models", default="gemini,gemma", help="Comma-separated model aliases to scan.")
    all_cmd.add_argument("--force", action="store_true")
    all_cmd.add_argument("--skip-codeql", action="store_true")

    return parser


def parse_models(value: str) -> list[str] | None:
    value = value.strip()
    if value == "all":
        return None
    models = [item.strip() for item in value.split(",") if item.strip()]
    unknown = sorted(set(models) - {"gemini", "gemma"})
    if unknown:
        raise ValueError(f"Unknown models: {', '.join(unknown)}")
    return models


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
