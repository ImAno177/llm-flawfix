from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import os
import shutil
import subprocess


@dataclass(frozen=True)
class CodeQLPaths:
    codeql_bin: Path
    codeql_repo: Path | None


def discover_codeql() -> CodeQLPaths:
    codeql_bin = os.getenv("CODEQL_BIN") or shutil.which("codeql")
    if not codeql_bin:
        raise RuntimeError("CodeQL not found. Run inside Docker or set CODEQL_BIN.")
    repo = os.getenv("CODEQL_REPO")
    return CodeQLPaths(codeql_bin=Path(codeql_bin), codeql_repo=Path(repo) if repo else None)


def resolve_query_suite(query_suite: str, paths: CodeQLPaths) -> str:
    candidate = Path(query_suite)
    if candidate.exists():
        return str(candidate)
    if paths.codeql_repo:
        suite = paths.codeql_repo / "python" / "ql" / "src" / "codeql-suites" / query_suite
        if suite.exists():
            return str(suite)
    return query_suite


def scan_python_dir(source_dir: Path, out_dir: Path, query_suite: str) -> Path:
    if not any(source_dir.rglob("*.py")):
        raise RuntimeError(f"No Python files found in {source_dir}")

    paths = discover_codeql()
    suite = resolve_query_suite(query_suite, paths)
    out_dir.mkdir(parents=True, exist_ok=True)
    db_dir = out_dir / "db"
    sarif_path = out_dir / "results.sarif"

    if db_dir.exists():
        shutil.rmtree(db_dir)

    create_cmd = [
        str(paths.codeql_bin),
        "database",
        "create",
        str(db_dir),
        "--language=python",
        f"--source-root={source_dir}",
        "--overwrite",
    ]
    analyze_cmd = [
        str(paths.codeql_bin),
        "database",
        "analyze",
        str(db_dir),
        suite,
        "--format=sarif-latest",
        f"--output={sarif_path}",
    ]

    _run(create_cmd)
    _run(analyze_cmd)
    return sarif_path


def _run(cmd: list[str]) -> None:
    result = subprocess.run(cmd, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    if result.returncode != 0:
        joined = " ".join(cmd)
        raise RuntimeError(f"Command failed ({joined}):\n{result.stdout}")
