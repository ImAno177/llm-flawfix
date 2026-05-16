from __future__ import annotations

from dataclasses import dataclass
from json import JSONDecoder
from pathlib import Path
import json
import re
from urllib.request import urlopen


SECURITYEVAL_URL = "https://raw.githubusercontent.com/s2e-lab/SecurityEval/main/dataset.jsonl"


@dataclass(frozen=True)
class SecurityTask:
    sample_id: str
    prompt: str
    target_cwe: str
    insecure_code: str | None = None

    @property
    def slug(self) -> str:
        return slugify(self.sample_id)


def normalize_cwe(value: str | None) -> str:
    if not value:
        return ""
    match = re.search(r"CWE[-_/ ]*0*(\d+)", value, flags=re.IGNORECASE)
    if not match:
        return value.upper()
    return f"CWE-{int(match.group(1))}"


def slugify(value: str) -> str:
    value = Path(value).name
    value = re.sub(r"[^A-Za-z0-9_.-]+", "_", value)
    return value.removesuffix(".py")


def download_securityeval(data_dir: Path, force: bool = False) -> Path:
    out_dir = data_dir / "securityeval"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / "dataset.jsonl"
    if out_file.exists() and not force:
        return out_file
    with urlopen(SECURITYEVAL_URL, timeout=60) as response:
        content = response.read()
    out_file.write_bytes(content)
    return out_file


def iter_json_objects(text: str) -> list[dict]:
    decoder = JSONDecoder()
    idx = 0
    objects: list[dict] = []
    length = len(text)
    while idx < length:
        while idx < length and text[idx].isspace():
            idx += 1
        if idx >= length:
            break
        obj, idx = decoder.raw_decode(text, idx)
        objects.append(obj)
    return objects


def load_securityeval(path: Path) -> list[SecurityTask]:
    text = path.read_text(encoding="utf-8")
    try:
        records = [json.loads(line) for line in text.splitlines() if line.strip()]
    except json.JSONDecodeError:
        records = iter_json_objects(text)

    tasks: list[SecurityTask] = []
    for record in records:
        sample_id = record["ID"]
        tasks.append(
            SecurityTask(
                sample_id=sample_id,
                prompt=record["Prompt"].strip(),
                target_cwe=normalize_cwe(sample_id),
                insecure_code=record.get("Insecure_code"),
            )
        )
    return tasks
