from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - only for Python 3.10 fallback.
    import tomli as tomllib


@dataclass(frozen=True)
class ModelConfig:
    alias: str
    model: str
    rpm: int


@dataclass(frozen=True)
class GenerationConfig:
    temperature: float = 0.2
    max_output_tokens: int = 8192


@dataclass(frozen=True)
class CodeQLConfig:
    query_suite: str = "python-security-extended.qls"


@dataclass(frozen=True)
class AppConfig:
    gemini: ModelConfig
    gemma: ModelConfig
    generation: GenerationConfig
    codeql: CodeQLConfig


def load_config(path: Path | None) -> AppConfig:
    data: dict = {}
    if path and path.exists():
        with path.open("rb") as fh:
            data = tomllib.load(fh)

    models = data.get("models", {})
    gemini = models.get("gemini", {})
    gemma = models.get("gemma", {})
    generation = data.get("generation", {})
    codeql = data.get("codeql", {})

    return AppConfig(
        gemini=ModelConfig(
            alias="gemini",
            model=gemini.get("model", "gemini-3.1-flash-lite"),
            rpm=int(gemini.get("rpm", 15)),
        ),
        gemma=ModelConfig(
            alias="gemma",
            model=gemma.get("model", "gemma-4-31b-it"),
            rpm=int(gemma.get("rpm", 15)),
        ),
        generation=GenerationConfig(
            temperature=float(generation.get("temperature", 0.2)),
            max_output_tokens=int(generation.get("max_output_tokens", 4096)),
        ),
        codeql=CodeQLConfig(
            query_suite=codeql.get("query_suite", "python-security-extended.qls")
        ),
    )
