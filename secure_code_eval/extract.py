from __future__ import annotations

import re


FENCE_RE = re.compile(r"```(?P<label>[A-Za-z0-9_+-]*)\s*\n(?P<body>.*?)```", re.DOTALL)


def extract_python_code(text: str) -> str:
    """Extract the most likely Python source from an LLM response."""
    text = text.strip()
    if not text:
        return ""

    fenced = list(FENCE_RE.finditer(text))
    if fenced:
        python_blocks = [
            match.group("body").strip()
            for match in fenced
            if match.group("label").lower() in {"python", "py"}
        ]
        if python_blocks:
            return python_blocks[0]
        return fenced[0].group("body").strip()

    lines = text.splitlines()
    for idx, line in enumerate(lines):
        stripped = line.lstrip()
        if stripped.startswith(("import ", "from ", "def ", "class ", "@")):
            return "\n".join(lines[idx:]).strip()
    return text
