from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import asyncio
import csv
import json

from .codeql import scan_python_dir
from .config import AppConfig
from .datasets import SecurityTask, download_securityeval, load_securityeval
from .extract import extract_python_code
from .llm import GoogleGenAIClient, MockLLMClient, ScheduledLLM
from .metrics import (
    MetricRow,
    compute_generation_metrics,
    compute_repair_metrics,
    write_metrics,
)
from .prompts import (
    direct_repair_prompt,
    explained_repair_prompt,
    explanation_prompt,
    hint_guided_code_prompt,
    hint_prompt,
    vanilla_prompt,
)
from .sarif import Finding, group_findings_by_sample, parse_sarif


GENERATION_EXPERIMENTS = {"vanilla", "self_hints"}
REPAIR_EXPERIMENTS = {"direct_repair", "explained_repair"}
ALL_EXPERIMENTS = ["vanilla", "self_hints", "direct_repair", "explained_repair"]
MODEL_ALIASES = ["gemini", "gemma"]


@dataclass
class Pipeline:
    root: Path
    config: AppConfig
    run_id: str
    mock_llm: bool = False
    max_concurrency: int = 16

    @property
    def data_dir(self) -> Path:
        return self.root / "data"

    @property
    def run_dir(self) -> Path:
        return self.root / "runs" / self.run_id

    def load_tasks(self, limit: int | None = None) -> list[SecurityTask]:
        dataset_path = self.data_dir / "securityeval" / "dataset.jsonl"
        if not dataset_path.exists():
            dataset_path = download_securityeval(self.data_dir)
        tasks = load_securityeval(dataset_path)
        return tasks[:limit] if limit else tasks

    def scheduled_llm(self) -> ScheduledLLM:
        client = MockLLMClient() if self.mock_llm else GoogleGenAIClient()
        return ScheduledLLM(
            client=client,
            model_configs=[self.config.gemini, self.config.gemma],
            generation=self.config.generation,
        )

    async def run_experiments(
        self,
        experiments: list[str],
        limit: int | None = None,
        skip_codeql: bool = False,
    ) -> None:
        tasks = self.load_tasks(limit=limit)
        llm = self.scheduled_llm()

        if "vanilla" in experiments:
            await self.run_vanilla(tasks, llm)
        if "self_hints" in experiments:
            await self.run_self_hints(tasks, llm)
        if "direct_repair" in experiments:
            await self.ensure_vanilla_ready(tasks, llm, skip_codeql)
            await self.run_direct_repair(tasks, llm, skip_codeql=skip_codeql)
        if "explained_repair" in experiments:
            await self.ensure_vanilla_ready(tasks, llm, skip_codeql)
            await self.run_explained_repair(tasks, llm, skip_codeql=skip_codeql)

    async def ensure_vanilla_ready(
        self,
        tasks: list[SecurityTask],
        llm: ScheduledLLM,
        skip_codeql: bool,
    ) -> None:
        missing = [
            task
            for alias in MODEL_ALIASES
            for task in tasks
            if not self.code_file("vanilla", alias, task).exists()
        ]
        if missing:
            await self.run_vanilla(tasks, llm)
        if not skip_codeql and not all(self.has_scan("vanilla", alias) for alias in MODEL_ALIASES):
            self.scan_experiment("vanilla")

    async def run_vanilla(self, tasks: list[SecurityTask], llm: ScheduledLLM) -> None:
        coros = [
            self._generate_code("vanilla", alias, task, vanilla_prompt(task.prompt), llm)
            for task in tasks
            for alias in MODEL_ALIASES
        ]
        await self._run_bounded(coros)

    async def run_self_hints(self, tasks: list[SecurityTask], llm: ScheduledLLM) -> None:
        coros = [self._run_self_hint_sample(alias, task, llm) for task in tasks for alias in MODEL_ALIASES]
        await self._run_bounded(coros)

    async def run_direct_repair(
        self,
        tasks: list[SecurityTask],
        llm: ScheduledLLM,
        skip_codeql: bool = False,
    ) -> None:
        if skip_codeql:
            return
        coros = []
        for alias in MODEL_ALIASES:
            baseline_findings = self.findings_for("vanilla", alias)
            grouped = group_findings_by_sample(baseline_findings)
            for task in tasks:
                findings = grouped.get(task.slug)
                if not findings:
                    continue
                code = self.code_file("vanilla", alias, task).read_text(encoding="utf-8")
                prompt = direct_repair_prompt(code, findings)
                coros.append(self._generate_code("direct_repair", alias, task, prompt, llm))
        await self._run_bounded(coros)

    async def run_explained_repair(
        self,
        tasks: list[SecurityTask],
        llm: ScheduledLLM,
        skip_codeql: bool = False,
    ) -> None:
        if skip_codeql:
            return
        baseline_findings = self.findings_for("vanilla", "gemma")
        grouped = group_findings_by_sample(baseline_findings)
        coros = []
        for task in tasks:
            findings = grouped.get(task.slug)
            if findings:
                coros.append(self._run_explained_repair_sample(task, findings, llm))
        await self._run_bounded(coros)

    async def _run_self_hint_sample(self, alias: str, task: SecurityTask, llm: ScheduledLLM) -> None:
        hints_response = await llm.generate(
            alias=alias,
            prompt=hint_prompt(task.prompt),
            cache_file=self.response_file("self_hints", alias, task, "hints"),
        )
        hint_text = hints_response.text.strip()
        hint_path = self.run_dir / "hints" / "self_hints" / alias / f"{task.slug}.txt"
        hint_path.parent.mkdir(parents=True, exist_ok=True)
        hint_path.write_text(hint_text, encoding="utf-8")
        prompt = hint_guided_code_prompt(task.prompt, hint_text)
        await self._generate_code("self_hints", alias, task, prompt, llm, response_kind="code")

    async def _run_explained_repair_sample(
        self,
        task: SecurityTask,
        findings: list[Finding],
        llm: ScheduledLLM,
    ) -> None:
        baseline_code = self.code_file("vanilla", "gemma", task).read_text(encoding="utf-8")
        explanation = await llm.generate(
            alias="gemini",
            prompt=explanation_prompt(baseline_code, findings),
            cache_file=self.response_file("explained_repair", "gemini", task, "explanations"),
        )
        explanation_path = self.run_dir / "hints" / "explained_repair" / "gemini" / f"{task.slug}.txt"
        explanation_path.parent.mkdir(parents=True, exist_ok=True)
        explanation_path.write_text(explanation.text.strip(), encoding="utf-8")
        repair_prompt = explained_repair_prompt(baseline_code, explanation.text)
        await self._generate_code(
            "explained_repair",
            "gemma",
            task,
            repair_prompt,
            llm,
            response_kind="code",
        )

    async def _generate_code(
        self,
        experiment: str,
        alias: str,
        task: SecurityTask,
        prompt: str,
        llm: ScheduledLLM,
        response_kind: str = "code",
    ) -> None:
        code_path = self.code_file(experiment, alias, task)
        if code_path.exists():
            return
        response = await llm.generate(
            alias=alias,
            prompt=prompt,
            cache_file=self.response_file(experiment, alias, task, response_kind),
        )
        code = extract_python_code(response.text)
        code_path.parent.mkdir(parents=True, exist_ok=True)
        code_path.write_text(code.rstrip() + "\n", encoding="utf-8")

    async def _run_bounded(self, coros) -> None:
        semaphore = asyncio.Semaphore(self.max_concurrency)

        async def bound(coro):
            async with semaphore:
                return await coro

        results = await asyncio.gather(*(bound(coro) for coro in coros), return_exceptions=True)
        errors = [result for result in results if isinstance(result, Exception)]
        if errors:
            first = errors[0]
            raise RuntimeError(f"{len(errors)} task(s) failed; first error: {first!r}")

    def scan_experiment(
        self,
        experiment: str,
        models: list[str] | None = None,
        skip_existing: bool = False,
    ) -> list[Path]:
        experiment_dir = self.run_dir / "code" / experiment
        if not experiment_dir.exists():
            return []
        selected = set(models) if models else set(MODEL_ALIASES)
        if selected == set(MODEL_ALIASES):
            out_dir = self.run_dir / "codeql" / experiment / "all"
            sarif = out_dir / "results.sarif"
            if skip_existing and sarif.exists():
                return [sarif]
            return [scan_python_dir(experiment_dir, out_dir, self.config.codeql.query_suite)]

        outputs: list[Path] = []
        for model_dir in sorted((self.run_dir / "code" / experiment).glob("*")):
            if selected and model_dir.name not in selected:
                continue
            if not model_dir.is_dir() or not any(model_dir.glob("*.py")):
                continue
            out_dir = self.run_dir / "codeql" / experiment / model_dir.name
            sarif = out_dir / "results.sarif"
            if skip_existing and sarif.exists():
                outputs.append(sarif)
                continue
            outputs.append(scan_python_dir(model_dir, out_dir, self.config.codeql.query_suite))
        return outputs

    def scan_many(
        self,
        experiments: list[str],
        models: list[str] | None = None,
        skip_existing: bool = False,
    ) -> list[Path]:
        outputs: list[Path] = []
        for experiment in experiments:
            outputs.extend(self.scan_experiment(experiment, models=models, skip_existing=skip_existing))
        return outputs

    def write_report(self, limit: int | None = None) -> list[MetricRow]:
        tasks = self.load_tasks(limit=limit)
        rows: list[MetricRow] = []
        for experiment in GENERATION_EXPERIMENTS:
            for alias in MODEL_ALIASES:
                if self.has_scan(experiment, alias):
                    findings = self.findings_for(experiment, alias)
                    rows.append(compute_generation_metrics(experiment, alias, tasks, findings))

        for alias in MODEL_ALIASES:
            if self.has_scan("vanilla", alias) and self.has_scan("direct_repair", alias):
                baseline = self.findings_for("vanilla", alias)
                repair = self.findings_for("direct_repair", alias)
                rows.append(compute_repair_metrics("direct_repair", alias, baseline, repair))

        if self.has_scan("vanilla", "gemma") and self.has_scan("explained_repair", "gemma"):
            baseline = self.findings_for("vanilla", "gemma")
            repair = self.findings_for("explained_repair", "gemma")
            rows.append(compute_repair_metrics("explained_repair", "gemma", baseline, repair))

        report_dir = self.run_dir / "reports"
        write_metrics(report_dir / "metrics.csv", rows)
        self.write_findings_csv(report_dir / "findings.csv", tasks)
        self.write_summary(report_dir / "summary.md", rows)
        return rows

    def write_findings_csv(self, path: Path, tasks: list[SecurityTask]) -> None:
        task_by_slug = {task.slug: task for task in tasks}
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8", newline="") as fh:
            writer = csv.DictWriter(
                fh,
                fieldnames=[
                    "experiment",
                    "model",
                    "sample_slug",
                    "target_cwe",
                    "detected_cwes",
                    "rule_id",
                    "file",
                    "start_line",
                    "start_column",
                    "message",
                ],
            )
            writer.writeheader()
            for sarif_path in sorted((self.run_dir / "codeql").glob("*/*/results.sarif")):
                experiment = sarif_path.parents[1].name
                sarif_model = sarif_path.parent.name
                for finding in parse_sarif(sarif_path):
                    model = finding_model_alias(finding) or sarif_model
                    task = task_by_slug.get(finding.sample_slug)
                    writer.writerow(
                        {
                            "experiment": experiment,
                            "model": model,
                            "sample_slug": finding.sample_slug,
                            "target_cwe": task.target_cwe if task else "",
                            "detected_cwes": ";".join(sorted(finding.cwes)),
                            "rule_id": finding.rule_id,
                            "file": finding.file,
                            "start_line": finding.start_line or "",
                            "start_column": finding.start_column or "",
                            "message": finding.message,
                        }
                    )

    def write_summary(self, path: Path, rows: list[MetricRow]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        lines = [f"# SecurityEval Run {self.run_id}", "", "| Experiment | Model | N | TarV-R | AllV-R | Repair Rate |", "|---|---:|---:|---:|---:|---:|"]
        for row in rows:
            repair = "" if row.repair_rate is None else f"{row.repair_rate:.2%}"
            lines.append(
                f"| {row.experiment} | {row.model} | {row.total_samples} | "
                f"{row.tarv_r:.2%} | {row.allv_r:.2%} | {repair} |"
            )
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    def findings_for(self, experiment: str, alias: str) -> list[Finding]:
        combined = self.run_dir / "codeql" / experiment / "all" / "results.sarif"
        if combined.exists():
            return [
                finding
                for finding in parse_sarif(combined)
                if finding_model_alias(finding) == alias
            ]
        return parse_sarif(self.run_dir / "codeql" / experiment / alias / "results.sarif")

    def has_scan(self, experiment: str, alias: str) -> bool:
        return (
            (self.run_dir / "codeql" / experiment / "all" / "results.sarif").exists()
            or (self.run_dir / "codeql" / experiment / alias / "results.sarif").exists()
        )

    def code_file(self, experiment: str, alias: str, task: SecurityTask) -> Path:
        return self.run_dir / "code" / experiment / alias / f"{task.slug}.py"

    def response_file(self, experiment: str, alias: str, task: SecurityTask, kind: str) -> Path:
        return self.run_dir / "responses" / experiment / alias / kind / f"{task.slug}.json"


def parse_experiments(value: str) -> list[str]:
    if value.strip() == "all":
        return ALL_EXPERIMENTS
    experiments = [item.strip() for item in value.split(",") if item.strip()]
    unknown = sorted(set(experiments) - set(ALL_EXPERIMENTS))
    if unknown:
        raise ValueError(f"Unknown experiments: {', '.join(unknown)}")
    return experiments


def finding_model_alias(finding: Finding) -> str:
    parts = finding.file.replace("\\", "/").split("/")
    for part in parts:
        if part in MODEL_ALIASES:
            return part
    return ""
