# SecurityEval Gemini/Gemma Automation

## Muc Luc

- [Tong Quan](#tong-quan)
- [Tai Lieu Lien Quan](#tai-lieu-lien-quan)
- [Tinh Nang Chinh](#tinh-nang-chinh)
- [Cau Truc Repo](#cau-truc-repo)
- [Ket Qua Full Run](#ket-qua-full-run)
- [Lenh Nhanh](#lenh-nhanh)
- [Bao Mat Va Du Lieu Sinh Ra](#bao-mat-va-du-lieu-sinh-ra)

## Tong Quan

Repo này tự động hóa thí nghiệm SecurityEval để đánh giá khả năng sinh mã Python an toàn và tự sửa lỗi bảo mật của **Gemini 3.1 Flash-Lite** và **Gemma 4 31B IT**. Pipeline gọi model, lưu response/code, chạy CodeQL, parse SARIF và xuất report Markdown/CSV.

Tất cả được đóng gói bằng Docker để tránh phụ thuộc CodeQL/Python cài trên máy host.

## Tai Lieu Lien Quan

- [agent.md](agent.md): Mô tả kế hoạch thí nghiệm, vai trò agent, model mapping, metrics và trạng thái kết quả.
- [setup.md](setup.md): Hướng dẫn dựng môi trường, cấu hình API key, chạy full dataset, resume và debug.

Tóm tắt nhanh:

| File | Tóm tắt |
|---|---|
| [agent.md](agent.md) | Tài liệu nghiệp vụ/thí nghiệm: chạy nhánh nào, model nào làm gì, đo metric nào. |
| [setup.md](setup.md) | Tài liệu vận hành: build Docker, chạy command, kiểm tra output và xử lý lỗi thường gặp. |

## Tinh Nang Chinh

- Tải SecurityEval 121 task Python.
- Chạy 4 nhánh: `vanilla`, `self_hints`, `direct_repair`, `explained_repair`.
- Chạy Gemini và Gemma song song nhưng tôn trọng 15 RPM mỗi model.
- Cache response/code để resume không gọi API lại.
- Chạy CodeQL trong Docker và xuất SARIF.
- Xuất `summary.md`, `metrics.csv`, `findings.csv`.

## Cau Truc Repo

```text
.
├── Dockerfile
├── docker-compose.yml
├── config.example.toml
├── run_experiments.py
├── secure_code_eval/
│   ├── codeql.py
│   ├── config.py
│   ├── datasets.py
│   ├── extract.py
│   ├── llm.py
│   ├── metrics.py
│   ├── pipeline.py
│   ├── prompts.py
│   ├── rate_limit.py
│   └── sarif.py
├── tests/
│   └── test_core.py
├── agent.md
├── readme.md
└── setup.md
```

Các thư mục sinh ra khi chạy:

| Path | Nội dung |
|---|---|
| `data/` | Dataset SecurityEval tải về. |
| `runs/` | Code sinh ra, raw responses, CodeQL DB/SARIF, report. |
| `.cache/` | Cache phụ trợ nếu cần. |

## Ket Qua Full Run

Full run hiện có tại:

- [runs/full-securityeval/reports/summary.md](runs/full-securityeval/reports/summary.md)
- [runs/full-securityeval/reports/metrics.csv](runs/full-securityeval/reports/metrics.csv)
- [runs/full-securityeval/reports/findings.csv](runs/full-securityeval/reports/findings.csv)

Tóm tắt:

| Experiment | Model | N | TarV-R | AllV-R | Repair Rate |
|---|---:|---:|---:|---:|---:|
| vanilla | gemini | 121 | 19.83% | 19.83% | |
| vanilla | gemma | 121 | 31.40% | 31.40% | |
| self_hints | gemini | 121 | 14.05% | 14.05% | |
| self_hints | gemma | 121 | 14.05% | 14.05% | |
| direct_repair | gemini | 24 | 0.00% | 29.17% | 70.83% |
| direct_repair | gemma | 38 | 0.00% | 26.32% | 73.68% |
| explained_repair | gemma | 38 | 0.00% | 21.05% | 78.95% |

## Lenh Nhanh

Build Docker image:

```powershell
docker compose build
```

Tải dataset:

```powershell
docker compose run --rm runner python run_experiments.py prepare
```

Chạy full dataset:

```powershell
docker compose run --rm runner python run_experiments.py all --run-id full-securityeval --max-concurrency 64
```

Tạo lại report từ artifact đã có:

```powershell
docker compose run --rm runner python run_experiments.py report --run-id full-securityeval
```

## Bao Mat Va Du Lieu Sinh Ra

- `.env` chứa API key và đã nằm trong [.gitignore](.gitignore).
- `data/`, `runs/`, `.cache/` không được track trong git để tránh commit dataset, raw model responses, CodeQL DB và report lớn.
- Nếu API key từng được chia sẻ qua chat/log, nên rotate key trong Google AI Studio trước khi dùng dài hạn.
