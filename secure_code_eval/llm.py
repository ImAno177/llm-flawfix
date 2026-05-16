from __future__ import annotations

from dataclasses import dataclass, asdict
import asyncio
import json
import os
import random
from pathlib import Path
from typing import Protocol

from .config import GenerationConfig, ModelConfig
from .rate_limit import AsyncStartRateLimiter


@dataclass
class LLMResponse:
    model: str
    text: str
    raw: dict


class LLMClient(Protocol):
    async def generate(self, model: str, prompt: str, generation: GenerationConfig) -> LLMResponse:
        ...


class GoogleGenAIClient:
    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        if not self.api_key:
            raise RuntimeError("Missing GEMINI_API_KEY or GOOGLE_API_KEY")
        self.timeout_seconds = int(os.getenv("GOOGLE_GENAI_TIMEOUT_MS", "90000")) / 1000.0

    async def generate(self, model: str, prompt: str, generation: GenerationConfig) -> LLMResponse:
        return await asyncio.to_thread(self._generate_sync, model, prompt, generation)

    def _generate_sync(self, model: str, prompt: str, generation: GenerationConfig) -> LLMResponse:
        import requests

        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": generation.temperature,
                "maxOutputTokens": generation.max_output_tokens,
            },
        }
        response = requests.post(
            url,
            params={"key": self.api_key},
            json=payload,
            timeout=self.timeout_seconds,
        )
        if response.status_code >= 400:
            raise RuntimeError(f"Gemini API error {response.status_code}: {response.text[:500]}")
        raw = response.json()
        text = _extract_rest_text(raw)
        return LLMResponse(model=model, text=text, raw=raw)


class MockLLMClient:
    async def generate(self, model: str, prompt: str, generation: GenerationConfig) -> LLMResponse:
        await asyncio.sleep(0.01)
        if "List exactly 5 potential security vulnerabilities" in prompt:
            text = "\n".join(
                [
                    "CWE-20: Improper input validation",
                    "CWE-22: Path traversal",
                    "CWE-78: OS command injection",
                    "CWE-79: Cross-site scripting",
                    "CWE-502: Unsafe deserialization",
                ]
            )
        elif "secure Python code review expert" in prompt:
            text = "Validate untrusted input, avoid unsafe APIs, and use safe library alternatives."
        else:
            text = (
                "```python\n"
                "def generated_placeholder(*args, **kwargs):\n"
                "    return None\n"
                "```\n"
            )
        return LLMResponse(model=model, text=text, raw={"mock": True, "model": model})


class ScheduledLLM:
    def __init__(self, client: LLMClient, model_configs: list[ModelConfig], generation: GenerationConfig):
        self.client = client
        self.generation = generation
        self.models = {cfg.alias: cfg for cfg in model_configs}
        self.limiters = {cfg.alias: AsyncStartRateLimiter(cfg.rpm) for cfg in model_configs}

    async def generate(self, alias: str, prompt: str, cache_file: Path) -> LLMResponse:
        cfg = self.models[alias]
        if cache_file.exists():
            data = json.loads(cache_file.read_text(encoding="utf-8"))
            return LLMResponse(model=data["model"], text=data["text"], raw=data.get("raw", {}))

        cache_file.parent.mkdir(parents=True, exist_ok=True)
        response = await self._generate_with_retries(alias, cfg.model, prompt)
        _write_json_atomic(cache_file, _jsonable(asdict(response)))
        return response

    async def _generate_with_retries(self, alias: str, model: str, prompt: str) -> LLMResponse:
        max_attempts = int(os.getenv("LLM_MAX_ATTEMPTS", "12"))
        for attempt in range(max_attempts):
            await self.limiters[alias].wait()
            try:
                return await self.client.generate(model=model, prompt=prompt, generation=self.generation)
            except Exception as exc:
                if attempt >= max_attempts - 1:
                    raise
                delay = _retry_delay(exc, attempt)
                await asyncio.sleep(delay)
        raise RuntimeError("unreachable retry state")


def _retry_delay(exc: Exception, attempt: int) -> float:
    retry_after = getattr(exc, "retry_after", None)
    if retry_after:
        try:
            return float(retry_after)
        except (TypeError, ValueError):
            pass
    return min(60.0, (2**attempt) + random.uniform(0.0, 1.0))


def _response_to_dict(response) -> dict:
    for method_name in ("model_dump", "to_json_dict"):
        method = getattr(response, method_name, None)
        if callable(method):
            try:
                return _jsonable(method())
            except Exception:
                pass
    return {"text": getattr(response, "text", "")}


def _extract_rest_text(raw: dict) -> str:
    parts = []
    fallback_parts = []
    for candidate in raw.get("candidates", []):
        for part in candidate.get("content", {}).get("parts", []):
            text = part.get("text")
            if not text:
                continue
            fallback_parts.append(text)
            if not part.get("thought"):
                parts.append(text)
    return "\n".join(parts or fallback_parts)


def _jsonable(value):
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_jsonable(item) for item in value]
    if hasattr(value, "model_dump"):
        try:
            return _jsonable(value.model_dump())
        except Exception:
            pass
    return str(value)


def _write_json_atomic(path: Path, data: dict) -> None:
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    tmp_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp_path.replace(path)
