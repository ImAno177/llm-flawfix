# Agent Plan: SecurityEval LLM Security Experiments

## Table Of Contents

- [Purpose](#purpose)
- [Related Documents](#related-documents)
- [Experiment Scope](#experiment-scope)
- [Models And Rate Limits](#models-and-rate-limits)
- [Automation Pipeline](#automation-pipeline)
- [Notebook Demos](#notebook-demos)
- [Report Metrics](#report-metrics)
- [Current Status](#current-status)
- [Quick Operations](#quick-operations)

## Purpose

This document explains the role of the automation agent and pipeline for reproducing SecurityEval experiments inspired by **Guiding AI to Fix Its Own Flaws**. The goal is to measure how well LLMs generate secure Python code and repair CodeQL-detected security issues.

## Related Documents

- [readme.md](readme.md): Repository overview, source layout, full-run results, and the main commands.
- [setup.md](setup.md): Docker setup, API key configuration, image build, experiment execution, resume, and debugging guide.

Quick summary:

| File | Role |
|---|---|
| [readme.md](readme.md) | Start here to understand what the project does and where outputs are written. |
| [setup.md](setup.md) | Operational checklist for building the environment and rerunning the pipeline. |

## Experiment Scope

The pipeline currently runs **SecurityEval only**, using 121 Python tasks. Each task contains a programming prompt, and the target CWE is inferred from the dataset `ID`.

Experiment branches:

1. **Vanilla prompting**
   - Gemini and Gemma generate code directly from the task.
   - No additional security guidance is provided.

2. **Self-generated hints**
   - Each model generates 5 security-risk hints for the task.
   - The same model then uses those hints to generate new code.

3. **Direct repair**
   - Applied only to baseline samples with CodeQL findings.
   - Each model repairs its own vulnerable baseline code using raw CodeQL feedback.

4. **Explained repair**
   - Applied only to Gemma baseline samples with CodeQL findings.
   - Gemini writes explained feedback.
   - Gemma uses that explained feedback to repair the code.

The Docker pipeline defaults to Gemini and Gemma. Use `--target-models` to limit generation and reporting to selected aliases.

## Models And Rate Limits

Default limits in [config.example.toml](config.example.toml):

| Alias | Model ID | RPM |
|---|---|---:|
| `gemini` | `gemini-3.1-flash-lite` | 15 |
| `gemma` | `gemma-4-31b-it` | 15 |

The scheduler uses `asyncio` with one limiter per model. Requests for both models can run concurrently, while each model is dispatched at least about 4 seconds apart to stay within 15 RPM.

Selected-model runs must pass the same alias to generation/reporting and, for `all`, to scanning:

```powershell
docker compose run --rm runner python run_experiments.py all --run-id gemma-only --target-models gemma --models gemma --max-concurrency 64
docker compose run --rm runner python run_experiments.py report --run-id gemma-only --target-models gemma
```

## Automation Pipeline

The main entry point is [run_experiments.py](run_experiments.py).

Important modules:

| Module | Responsibility |
|---|---|
| [secure_code_eval/datasets.py](secure_code_eval/datasets.py) | Download and load SecurityEval, normalize CWE IDs. |
| [secure_code_eval/llm.py](secure_code_eval/llm.py) | Call the Gemini API through REST, with timeout, retry, and response cache support. |
| [secure_code_eval/rate_limit.py](secure_code_eval/rate_limit.py) | Enforce per-model request start-rate limits. |
| [secure_code_eval/prompts.py](secure_code_eval/prompts.py) | Prompt templates for vanilla generation, hints, and repair. |
| [secure_code_eval/codeql.py](secure_code_eval/codeql.py) | Create CodeQL databases and run analysis. |
| [secure_code_eval/sarif.py](secure_code_eval/sarif.py) | Parse SARIF and map findings back to samples and models. |
| [secure_code_eval/metrics.py](secure_code_eval/metrics.py) | Compute metrics and write CSV outputs. |
| [secure_code_eval/pipeline.py](secure_code_eval/pipeline.py) | Orchestrate the full workflow. |

## Notebook Demos

The repository tracks Colab notebook code in `notebooks/`:

| Notebook | Role |
|---|---|
| [notebooks/securityeval_llama32_3b_full.ipynb](notebooks/securityeval_llama32_3b_full.ipynb) | Full Llama 3.2 3B Instruct SecurityEval workflow. |
| [notebooks/securityeval_llama32_3b_one_sample_codeql_demo.ipynb](notebooks/securityeval_llama32_3b_one_sample_codeql_demo.ipynb) | One-sample Llama 3.2 3B CodeQL demo. |
| [notebooks/securityeval_qwen35_4b_full.ipynb](notebooks/securityeval_qwen35_4b_full.ipynb) | Full Qwen3.5 4B SecurityEval workflow. |

Notebook outputs and execution counts are cleared before commit. Notebook-generated zips, reports, CodeQL databases, and run directories are result artifacts and should remain untracked.

## Report Metrics

Main metrics:

- `TarV-R`: fraction of samples where the target CWE is detected.
- `AllV-R`: fraction of samples with any security finding.
- `Repair Rate`: fraction of vulnerable baseline samples that are clean after repair.
- `post_repair_AllV-R`: remaining vulnerable rate after repair over the initially vulnerable subset.

Default output locations:

- `runs/<run_id>/code/`
- `runs/<run_id>/responses/`
- `runs/<run_id>/codeql/`
- `runs/<run_id>/reports/summary.md`
- `runs/<run_id>/reports/metrics.csv`
- `runs/<run_id>/reports/findings.csv`

## Current Status

A full run has been completed with `run_id=full-securityeval`.

Primary reports are generated locally under:

```text
runs/full-securityeval/reports/summary.md
runs/full-securityeval/reports/metrics.csv
runs/full-securityeval/reports/findings.csv
```

These generated result files are intentionally not tracked in Git.

Result summary:

| Experiment | Model | N | TarV-R | AllV-R | Repair Rate |
|---|---:|---:|---:|---:|---:|
| vanilla | gemini | 121 | 19.83% | 19.83% | |
| vanilla | gemma | 121 | 31.40% | 31.40% | |
| self_hints | gemini | 121 | 14.05% | 14.05% | |
| self_hints | gemma | 121 | 14.05% | 14.05% | |
| direct_repair | gemini | 24 | 0.00% | 29.17% | 70.83% |
| direct_repair | gemma | 38 | 0.00% | 26.32% | 73.68% |
| explained_repair | gemma | 38 | 0.00% | 21.05% | 78.95% |

## Quick Operations

```powershell
docker compose build
docker compose run --rm runner python run_experiments.py prepare
docker compose run --rm runner python run_experiments.py all --run-id full-securityeval --max-concurrency 64
docker compose run --rm runner python run_experiments.py report --run-id full-securityeval
docker compose run --rm runner python run_experiments.py all --run-id gemma-only --target-models gemma --models gemma --max-concurrency 64
```

See [setup.md](setup.md) for the complete setup and operations guide.
