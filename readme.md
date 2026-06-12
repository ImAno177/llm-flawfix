# llm-flawfix

## Table Of Contents

- [Overview](#overview)
- [Related Documents](#related-documents)
- [Key Features](#key-features)
- [Repository Layout](#repository-layout)
- [Notebook Demos](#notebook-demos)
- [Full Run Results](#full-run-results)
- [Quick Commands](#quick-commands)
- [Secrets And Generated Data](#secrets-and-generated-data)

## Overview

This repository automates SecurityEval experiments for evaluating how **Gemini 3.1 Flash-Lite** and **Gemma 4 31B IT** generate secure Python code and repair security issues. The Docker pipeline calls the models, stores responses and extracted code, runs CodeQL, parses SARIF, and exports Markdown/CSV reports.

Everything in the core pipeline runs through Docker so the host does not need a local Python, CodeQL CLI, or CodeQL query installation. The repository also includes Colab notebook code for Llama 3.2 3B and Qwen3.5 4B SecurityEval runs.

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
- Supports selecting model aliases with `--target-models` for generation and reporting.
- Caches responses and generated code so runs can resume without repeating completed API calls.
- Runs CodeQL inside Docker and exports SARIF.
- Exports `summary.md`, `metrics.csv`, and `findings.csv`.
- Includes output-free Colab notebooks for Llama 3.2 3B and Qwen3.5 4B experiment code.

## Repository Layout

```text
.
|-- Dockerfile
|-- docker-compose.yml
|-- config.example.toml
|-- run_experiments.py
|-- notebooks/
|   |-- securityeval_llama32_3b_full.ipynb
|   |-- securityeval_llama32_3b_one_sample_codeql_demo.ipynb
|   `-- securityeval_qwen35_4b_full.ipynb
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

Local-only artifacts such as `demo/`, `reports/`, extracted CodeQL databases, and downloaded tool archives should not be committed.

## Notebook Demos

Tracked notebooks are code templates only. Their outputs and execution counts are cleared before commit.

| Notebook | Purpose |
|---|---|
| [notebooks/securityeval_llama32_3b_full.ipynb](notebooks/securityeval_llama32_3b_full.ipynb) | Full SecurityEval workflow for `meta-llama/Llama-3.2-3B-Instruct`. |
| [notebooks/securityeval_llama32_3b_one_sample_codeql_demo.ipynb](notebooks/securityeval_llama32_3b_one_sample_codeql_demo.ipynb) | One-sample Llama 3.2 3B demo with real CodeQL scans. |
| [notebooks/securityeval_qwen35_4b_full.ipynb](notebooks/securityeval_qwen35_4b_full.ipynb) | Full SecurityEval workflow for Qwen3.5 4B. |

## Full Run Results

Full-run outputs are generated locally under:

```text
runs/full-securityeval/reports/summary.md
runs/full-securityeval/reports/metrics.csv
runs/full-securityeval/reports/findings.csv
```

Those files are not tracked in Git because they are generated results. Latest local result snapshot:

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

Run only one model alias:

```powershell
docker compose run --rm runner python run_experiments.py all --run-id gemma-only --target-models gemma --models gemma --max-concurrency 64
```

Regenerate the report from existing artifacts:

```powershell
docker compose run --rm runner python run_experiments.py report --run-id full-securityeval
```

Regenerate a selected-model report:

```powershell
docker compose run --rm runner python run_experiments.py report --run-id gemma-only --target-models gemma
```

## Secrets And Generated Data

- `.env` stores the API key and is ignored by [.gitignore](.gitignore).
- `data/`, `runs/`, and `.cache/` are not tracked to avoid committing datasets, raw model responses, CodeQL databases, and large reports.
- `notebooks/` is tracked as code, but notebook outputs and execution counts should stay empty.
- `demo/`, `reports/`, downloaded presentation tooling, and extracted CodeQL/database artifacts are local generated files and should stay out of commits.
- If an API key has been shared through chat or logs, rotate it in Google AI Studio before long-term use.
