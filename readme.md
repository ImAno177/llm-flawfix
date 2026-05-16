# SecurityEval Gemini/Gemma Automation

## Table Of Contents

- [Overview](#overview)
- [Related Documents](#related-documents)
- [Key Features](#key-features)
- [Repository Layout](#repository-layout)
- [Full Run Results](#full-run-results)
- [Quick Commands](#quick-commands)
- [Secrets And Generated Data](#secrets-and-generated-data)

## Overview

This repository automates SecurityEval experiments for evaluating how **Gemini 3.1 Flash-Lite** and **Gemma 4 31B IT** generate secure Python code and repair security issues. The pipeline calls the models, stores responses and extracted code, runs CodeQL, parses SARIF, and exports Markdown/CSV reports.

Everything runs through Docker so the host does not need a local Python, CodeQL CLI, or CodeQL query installation.

## Related Documents

- [agent.md](agent.md): Experiment plan, agent role, model mapping, metrics, and current result status.
- [setup.md](setup.md): Environment setup, API key configuration, full dataset execution, resume, and debugging guide.

Quick summary:

| File | Summary |
|---|---|
| [agent.md](agent.md) | Experiment document: which branches run, which model does what, and which metrics are measured. |
| [setup.md](setup.md) | Operations document: build Docker, run commands, inspect outputs, and handle common failures. |

## Key Features

- Downloads the 121-task SecurityEval dataset.
- Runs 4 branches: `vanilla`, `self_hints`, `direct_repair`, and `explained_repair`.
- Runs Gemini and Gemma concurrently while respecting 15 RPM per model.
- Caches responses and generated code so runs can resume without repeating completed API calls.
- Runs CodeQL inside Docker and exports SARIF.
- Exports `summary.md`, `metrics.csv`, and `findings.csv`.

## Repository Layout

```text
.
|-- Dockerfile
|-- docker-compose.yml
|-- config.example.toml
|-- run_experiments.py
|-- secure_code_eval/
|   |-- codeql.py
|   |-- config.py
|   |-- datasets.py
|   |-- extract.py
|   |-- llm.py
|   |-- metrics.py
|   |-- pipeline.py
|   |-- prompts.py
|   |-- rate_limit.py
|   `-- sarif.py
|-- tests/
|   `-- test_core.py
|-- agent.md
|-- readme.md
`-- setup.md
```

Generated directories:

| Path | Contents |
|---|---|
| `data/` | Downloaded SecurityEval dataset. |
| `runs/` | Generated code, raw responses, CodeQL DB/SARIF files, and reports. |
| `.cache/` | Optional supporting cache. |

## Full Run Results

The completed full run is available at:

- [runs/full-securityeval/reports/summary.md](runs/full-securityeval/reports/summary.md)
- [runs/full-securityeval/reports/metrics.csv](runs/full-securityeval/reports/metrics.csv)
- [runs/full-securityeval/reports/findings.csv](runs/full-securityeval/reports/findings.csv)

Summary:

| Experiment | Model | N | TarV-R | AllV-R | Repair Rate |
|---|---:|---:|---:|---:|---:|
| vanilla | gemini | 121 | 19.83% | 19.83% | |
| vanilla | gemma | 121 | 31.40% | 31.40% | |
| self_hints | gemini | 121 | 14.05% | 14.05% | |
| self_hints | gemma | 121 | 14.05% | 14.05% | |
| direct_repair | gemini | 24 | 0.00% | 29.17% | 70.83% |
| direct_repair | gemma | 38 | 0.00% | 26.32% | 73.68% |
| explained_repair | gemma | 38 | 0.00% | 21.05% | 78.95% |

## Quick Commands

Build the Docker image:

```powershell
docker compose build
```

Download the dataset:

```powershell
docker compose run --rm runner python run_experiments.py prepare
```

Run the full dataset:

```powershell
docker compose run --rm runner python run_experiments.py all --run-id full-securityeval --max-concurrency 64
```

Regenerate the report from existing artifacts:

```powershell
docker compose run --rm runner python run_experiments.py report --run-id full-securityeval
```

## Secrets And Generated Data

- `.env` stores the API key and is ignored by [.gitignore](.gitignore).
- `data/`, `runs/`, and `.cache/` are not tracked to avoid committing datasets, raw model responses, CodeQL databases, and large reports.
- If an API key has been shared through chat or logs, rotate it in Google AI Studio before long-term use.
