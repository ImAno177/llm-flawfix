from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import json
import re

from .datasets import normalize_cwe, slugify


@dataclass(frozen=True)
class Finding:
    sample_slug: str
    file: str
    rule_id: str
    message: str
    cwes: frozenset[str]
    start_line: int | None = None
    start_column: int | None = None


def parse_sarif(path: Path) -> list[Finding]:
    if not path.exists():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    findings: list[Finding] = []
    for run in data.get("runs", []):
        rule_cwes = _rule_cwes(run)
        for result in run.get("results", []):
            rule_id = result.get("ruleId", "")
            locations = result.get("locations") or [{}]
            location = locations[0].get("physicalLocation", {})
            artifact = location.get("artifactLocation", {})
            uri = artifact.get("uri", "")
            region = location.get("region", {})
            message = result.get("message", {}).get("text", "")
            cwes = set(rule_cwes.get(rule_id, set()))
            cwes.update(_extract_cwes(result))
            findings.append(
                Finding(
                    sample_slug=slugify(Path(uri).stem),
                    file=uri,
                    rule_id=rule_id,
                    message=message,
                    cwes=frozenset(cwes),
                    start_line=region.get("startLine"),
                    start_column=region.get("startColumn"),
                )
            )
    return findings


def group_findings_by_sample(findings: list[Finding]) -> dict[str, list[Finding]]:
    grouped: dict[str, list[Finding]] = {}
    for finding in findings:
        grouped.setdefault(finding.sample_slug, []).append(finding)
    return grouped


def _rule_cwes(run: dict) -> dict[str, set[str]]:
    rules = run.get("tool", {}).get("driver", {}).get("rules", [])
    mapping: dict[str, set[str]] = {}
    for rule in rules:
        rule_id = rule.get("id", "")
        mapping[rule_id] = _extract_cwes(rule)
    return mapping


def _extract_cwes(value) -> set[str]:
    text = json.dumps(value, ensure_ascii=False)
    return {normalize_cwe(match.group(0)) for match in re.finditer(r"CWE[-_/ ]*0*\d+", text, re.I)}
