# Setup And Run Guide

## Muc Luc

- [Tong Quan Setup](#tong-quan-setup)
- [Tai Lieu Lien Quan](#tai-lieu-lien-quan)
- [Yeu Cau](#yeu-cau)
- [Cau Hinh API Key](#cau-hinh-api-key)
- [Build Docker](#build-docker)
- [Chay Pipeline](#chay-pipeline)
- [Resume Va Debug](#resume-va-debug)
- [Kiem Thu](#kiem-thu)
- [Output Bao Cao](#output-bao-cao)

## Tong Quan Setup

Pipeline được thiết kế để chạy trong Docker. Image tự cài Python dependencies, CodeQL CLI và CodeQL query repo. Host chỉ cần Docker/Compose và file `.env` chứa API key.

## Tai Lieu Lien Quan

- [readme.md](readme.md): Tổng quan project, cấu trúc repo, lệnh nhanh và kết quả full run.
- [agent.md](agent.md): Kế hoạch thí nghiệm, mapping model, metrics và trạng thái kết quả.

Tóm tắt nhanh:

| File | Tóm tắt |
|---|---|
| [readme.md](readme.md) | Nên đọc đầu tiên để hiểu repo và output chính. |
| [agent.md](agent.md) | Dùng khi cần kiểm tra logic thí nghiệm và cách tính metrics. |

## Yeu Cau

- Docker Desktop hoặc Docker Engine.
- Docker Compose v2.
- Network để tải base image, Python packages, CodeQL CLI/query repo và gọi Gemini API.
- API key có quyền gọi Gemini API.

Kiểm tra Docker:

```powershell
docker version
docker compose version
```

## Cau Hinh API Key

Tạo file `.env` ở repo root:

```env
GEMINI_API_KEY=your_api_key_here
```

Không commit `.env`. File này đã được ignore.

Model và RPM mặc định nằm trong [config.example.toml](config.example.toml):

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

Image sẽ cài:

- Python 3.12.
- `google-genai`, `requests`, `pytest`, `pytest-asyncio`.
- CodeQL CLI `v2.25.4`.
- CodeQL query repo tương ứng.

## Chay Pipeline

Tải dataset:

```powershell
docker compose run --rm runner python run_experiments.py prepare
```

Chạy full workflow:

```powershell
docker compose run --rm runner python run_experiments.py all --run-id full-securityeval --max-concurrency 64
```

Chạy từng bước:

```powershell
docker compose run --rm runner python run_experiments.py run --run-id full-securityeval --experiments vanilla,self_hints --max-concurrency 64 --skip-codeql
docker compose run --rm runner python run_experiments.py scan --run-id full-securityeval --experiments vanilla,self_hints
docker compose run --rm runner python run_experiments.py report --run-id full-securityeval
```

Mock run không gọi API thật:

```powershell
docker compose run --rm runner python run_experiments.py run --run-id smoke --limit 2 --mock-llm --experiments vanilla,self_hints --skip-codeql
```

## Resume Va Debug

Pipeline cache theo:

```text
runs/<run_id>/responses/<experiment>/<model>/<kind>/<sample>.json
runs/<run_id>/code/<experiment>/<model>/<sample>.py
```

Nếu Docker/API lỗi giữa chừng, chạy lại cùng `--run-id`; file đã có sẽ được bỏ qua.

Kiểm tra container nền:

```powershell
docker ps -a --filter "name=da-full-securityeval"
docker logs da-full-securityeval --tail 200
```

Chạy nền:

```powershell
docker compose run -d --name da-full-securityeval runner python run_experiments.py all --run-id full-securityeval --max-concurrency 64
```

Dừng và xóa container nền:

```powershell
docker stop da-full-securityeval
docker rm da-full-securityeval
```

## Kiem Thu

Chạy unit tests:

```powershell
docker compose run --rm runner python -m unittest discover -s tests
```

Compile check:

```powershell
docker compose run --rm runner python -m compileall run_experiments.py secure_code_eval tests
```

## Output Bao Cao

Report chính:

```text
runs/full-securityeval/reports/summary.md
runs/full-securityeval/reports/metrics.csv
runs/full-securityeval/reports/findings.csv
```

Tạo lại report từ artifact đã có:

```powershell
docker compose run --rm runner python run_experiments.py report --run-id full-securityeval
```
