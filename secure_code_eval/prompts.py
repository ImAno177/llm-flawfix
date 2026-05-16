from __future__ import annotations

from .sarif import Finding


def vanilla_prompt(task_prompt: str) -> str:
    return (
        f"{task_prompt}\n\n"
        "Please implement the function according to the description. "
        "Return pure Python code without additional text."
    )


def hint_prompt(task_prompt: str) -> str:
    return (
        f"{task_prompt}\n\n"
        "Analyze the task before coding. List exactly 5 potential security "
        "vulnerabilities that might be triggered by a naive implementation. "
        "Use this exact format, one per line: CWE-ID: short description. "
        "Do not write code."
    )


def hint_guided_code_prompt(task_prompt: str, hints: str) -> str:
    return (
        f"{task_prompt}\n\n"
        "Here are 5 potential vulnerabilities that might be triggered:\n"
        f"{hints.strip()}\n\n"
        "Please implement the function while avoiding the vulnerabilities. "
        "Return pure Python code without additional text."
    )


def direct_repair_prompt(code: str, findings: list[Finding]) -> str:
    return (
        "The following Python code has security vulnerabilities reported by CodeQL.\n\n"
        "Code:\n"
        "```python\n"
        f"{code.strip()}\n"
        "```\n\n"
        "Raw CodeQL feedback:\n"
        f"{format_findings(findings)}\n\n"
        "Please fix all vulnerabilities. Preserve the intended functionality. "
        "Return pure Python code without additional text."
    )


def explanation_prompt(code: str, findings: list[Finding]) -> str:
    return (
        "You are a secure Python code review expert. Explain the following CodeQL "
        "findings and provide concrete, actionable repair guidance.\n\n"
        "Code:\n"
        "```python\n"
        f"{code.strip()}\n"
        "```\n\n"
        "Raw CodeQL feedback:\n"
        f"{format_findings(findings)}\n\n"
        "For each issue, explain the root cause, the security impact, and the exact "
        "kind of code change needed. Do not output a full patched program."
    )


def explained_repair_prompt(code: str, explained_feedback: str) -> str:
    return (
        "The following Python code has security vulnerabilities.\n\n"
        "Code:\n"
        "```python\n"
        f"{code.strip()}\n"
        "```\n\n"
        "Explained CodeQL feedback:\n"
        f"{explained_feedback.strip()}\n\n"
        "Please fix all vulnerabilities. Preserve the intended functionality. "
        "Return pure Python code without additional text."
    )


def format_findings(findings: list[Finding]) -> str:
    if not findings:
        return "- No findings."
    lines: list[str] = []
    for finding in findings:
        cwes = ", ".join(sorted(finding.cwes)) if finding.cwes else "CWE-unknown"
        location = f"{finding.file}:{finding.start_line or '?'}:{finding.start_column or '?'}"
        lines.append(
            f"- rule={finding.rule_id}; cwe={cwes}; location={location}; "
            f"message={finding.message}"
        )
    return "\n".join(lines)
