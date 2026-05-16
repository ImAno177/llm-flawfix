# Setup And Run Guide

## Table Of Contents

- [Setup Overview](#setup-overview)
- [Related Documents](#related-documents)
- [Requirements](#requirements)
- [API Key Configuration](#api-key-configuration)
- [Build Docker](#build-docker)
- [Run The Pipeline](#run-the-pipeline)
- [Resume And Debug](#resume-and-debug)
- [Tests](#tests)
- [Report Outputs](#report-outputs)

## Setup Overview

The pipeline is designed to run inside Docker. The image installs Python dependencies, the CodeQL CLI, and the CodeQL query repository. The host only needs Docker/Compose and a `.env` file containing the Gemini API key.

## Related Documents

- [readme.md](readme.md): Project overview, repository structure, quick commands, and full-run results.
- [agent.md](agent.md): Experiment plan, model mapping, metrics, and current result status.

Quick summary:

| File | Summary |
|---|---|
| [readme.md](readme.md) | Read this first to understand the repository and the primary outputs. |
| [agent.md](agent.md) | Use this when checking experiment logic and metric definitions. |

## Requirements

- Docker Desktop or Docker Engine.
- Docker Compose v2.
- Network access for base images, Python packages, CodeQL CLI/query repo downloads, and Gemini API calls.
- An API key allowed to call the Gemini API.

Check Docker:

```powershell
docker version
docker compose version
```

## API Key Configuration

Create a `.env` file at the repository root:

```env
GEMINI_API_KEY=your_api_key_here
```

Do not commit `.env`; it is already ignored.

Default model and RPM settings are in [config.example.toml](config.example.toml):

```toml
[models.gemini]
model = "gemini-3.1-flash-lite"
rpm = 15

[models.gemma]
model = "gemma-4-31b-it"
rpm = 15
```

## Build Docker

```powershell
docker compose build
```

The image installs:

- Python 3.12.
- `google-genai`, `requests`, `pytest`, and `pytest-asyncio`.
- CodeQL CLI `v2.25.4`.
- The matching CodeQL query repository.

## Run The Pipeline

Download the dataset:

```powershell
docker compose run --rm runner python run_experiments.py prepare
```

Run the full workflow:

```powershell
docker compose run --rm runner python run_experiments.py all --run-id full-securityeval --max-concurrency 64
```

Run individual steps:

```powershell
docker compose run --rm runner python run_experiments.py run --run-id full-securityeval --experiments vanilla,self_hints --max-concurrency 64 --skip-codeql
docker compose run --rm runner python run_experiments.py scan --run-id full-securityeval --experiments vanilla,self_hints
docker compose run --rm runner python run_experiments.py report --run-id full-securityeval
```

Mock run without real API calls:

```powershell
docker compose run --rm runner python run_experiments.py run --run-id smoke --limit 2 --mock-llm --experiments vanilla,self_hints --skip-codeql
```

## Resume And Debug

The pipeline caches outputs at:

```text
runs/<run_id>/responses/<experiment>/<model>/<kind>/<sample>.json
runs/<run_id>/code/<experiment>/<model>/<sample>.py
```

If Docker or the API fails mid-run, rerun with the same `--run-id`; existing files are skipped.

Inspect a background container:

```powershell
docker ps -a --filter "name=da-full-securityeval"
docker logs da-full-securityeval --tail 200
```

Run in the background:

```powershell
docker compose run -d --name da-full-securityeval runner python run_experiments.py all --run-id full-securityeval --max-concurrency 64
```

Stop and remove the background container:

```powershell
docker stop da-full-securityeval
docker rm da-full-securityeval
```

## Tests

Run unit tests:

```powershell
docker compose run --rm runner python -m unittest discover -s tests
```

Run compile checks:

```powershell
docker compose run --rm runner python -m compileall run_experiments.py secure_code_eval tests
```

## Report Outputs

Primary reports:

```text
runs/full-securityeval/reports/summary.md
runs/full-securityeval/reports/metrics.csv
runs/full-securityeval/reports/findings.csv
```

Regenerate reports from existing artifacts:

```powershell
docker compose run --rm runner python run_experiments.py report --run-id full-securityeval
```
