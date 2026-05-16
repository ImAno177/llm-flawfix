# Agent Plan: SecurityEval LLM Security Experiments

## Muc Luc

- [Muc Dich](#muc-dich)
- [Tai Lieu Lien Quan](#tai-lieu-lien-quan)
- [Pham Vi Thi Nghiem](#pham-vi-thi-nghiem)
- [Model Va Rate Limit](#model-va-rate-limit)
- [Pipeline Tu Dong Hoa](#pipeline-tu-dong-hoa)
- [Chi So Bao Cao](#chi-so-bao-cao)
- [Trang Thai Hien Tai](#trang-thai-hien-tai)
- [Lenh Van Hanh Nhanh](#lenh-van-hanh-nhanh)

## Muc Dich

Tài liệu này mô tả vai trò của agent/pipeline trong việc tái tạo thí nghiệm từ bài báo **Guiding AI to Fix Its Own Flaws** cho bộ dữ liệu SecurityEval. Mục tiêu là đo khả năng sinh mã Python an toàn và sửa lỗi bảo mật của các LLM khi được quét bằng CodeQL.

## Tai Lieu Lien Quan

- [readme.md](readme.md): Tổng quan repo, cấu trúc mã nguồn, kết quả full run và các lệnh chính.
- [setup.md](setup.md): Hướng dẫn thiết lập Docker, API key, build image, chạy thí nghiệm, resume và debug.

Tóm tắt nhanh:

| File | Vai trò |
|---|---|
| [readme.md](readme.md) | Điểm bắt đầu cho người đọc repo, giải thích project làm gì và output nằm ở đâu. |
| [setup.md](setup.md) | Checklist vận hành chi tiết để dựng môi trường và chạy lại pipeline. |

## Pham Vi Thi Nghiem

Pipeline hiện chạy **SecurityEval only** với 121 task Python. Mỗi task có prompt lập trình và target CWE được suy ra từ `ID` của dataset.

Các nhánh thí nghiệm:

1. **Vanilla prompting**
   - Gemini và Gemma sinh code trực tiếp từ task.
   - Không có nhắc nhở bảo mật bổ sung.

2. **Self-generated hints**
   - Mỗi model tự sinh 5 gợi ý rủi ro bảo mật cho task.
   - Chính model đó dùng hints vừa sinh để sinh code mới.

3. **Direct repair**
   - Chỉ áp dụng cho các sample baseline bị CodeQL cảnh báo.
   - Model sửa code của chính nó bằng raw CodeQL feedback.

4. **Explained repair**
   - Chỉ áp dụng cho baseline Gemma bị CodeQL cảnh báo.
   - Gemini sinh explained feedback.
   - Gemma dùng explained feedback để sửa code.

## Model Va Rate Limit

Rate limit mặc định trong [config.example.toml](config.example.toml):

| Alias | Model ID | RPM |
|---|---|---:|
| `gemini` | `gemini-3.1-flash-lite` | 15 |
| `gemma` | `gemma-4-31b-it` | 15 |

Scheduler dùng `asyncio` với limiter riêng theo model. Các request của hai model được chạy song song, nhưng mỗi model vẫn được dispatch cách nhau tối thiểu khoảng 4 giây để giữ 15 RPM.

## Pipeline Tu Dong Hoa

Entry point chính là [run_experiments.py](run_experiments.py).

Các module quan trọng:

| Module | Chức năng |
|---|---|
| [secure_code_eval/datasets.py](secure_code_eval/datasets.py) | Tải và đọc SecurityEval, chuẩn hóa CWE. |
| [secure_code_eval/llm.py](secure_code_eval/llm.py) | Gọi Gemini API qua REST, timeout/retry/cache response. |
| [secure_code_eval/rate_limit.py](secure_code_eval/rate_limit.py) | Giới hạn tốc độ request theo model. |
| [secure_code_eval/prompts.py](secure_code_eval/prompts.py) | Prompt templates cho vanilla, hints, repair. |
| [secure_code_eval/codeql.py](secure_code_eval/codeql.py) | Tạo CodeQL database và chạy analyze. |
| [secure_code_eval/sarif.py](secure_code_eval/sarif.py) | Parse SARIF và map findings về sample/model. |
| [secure_code_eval/metrics.py](secure_code_eval/metrics.py) | Tính metrics và ghi CSV. |
| [secure_code_eval/pipeline.py](secure_code_eval/pipeline.py) | Điều phối toàn bộ workflow. |

## Chi So Bao Cao

Các chỉ số chính:

- `TarV-R`: tỷ lệ sample bị phát hiện đúng CWE mục tiêu.
- `AllV-R`: tỷ lệ sample có bất kỳ finding bảo mật nào.
- `Repair Rate`: tỷ lệ sample lỗi baseline được sửa sạch sau repair.
- `post_repair_AllV-R`: tỷ lệ còn lỗi sau repair trên tập sample ban đầu bị lỗi.

Output mặc định nằm trong:

- `runs/<run_id>/code/`
- `runs/<run_id>/responses/`
- `runs/<run_id>/codeql/`
- `runs/<run_id>/reports/summary.md`
- `runs/<run_id>/reports/metrics.csv`
- `runs/<run_id>/reports/findings.csv`

## Trang Thai Hien Tai

Full run đã chạy với `run_id=full-securityeval`.

Report chính:

- [runs/full-securityeval/reports/summary.md](runs/full-securityeval/reports/summary.md)
- [runs/full-securityeval/reports/metrics.csv](runs/full-securityeval/reports/metrics.csv)
- [runs/full-securityeval/reports/findings.csv](runs/full-securityeval/reports/findings.csv)

Tóm tắt kết quả:

| Experiment | Model | N | TarV-R | AllV-R | Repair Rate |
|---|---:|---:|---:|---:|---:|
| vanilla | gemini | 121 | 19.83% | 19.83% | |
| vanilla | gemma | 121 | 31.40% | 31.40% | |
| self_hints | gemini | 121 | 14.05% | 14.05% | |
| self_hints | gemma | 121 | 14.05% | 14.05% | |
| direct_repair | gemini | 24 | 0.00% | 29.17% | 70.83% |
| direct_repair | gemma | 38 | 0.00% | 26.32% | 73.68% |
| explained_repair | gemma | 38 | 0.00% | 21.05% | 78.95% |

## Lenh Van Hanh Nhanh

```powershell
docker compose build
docker compose run --rm runner python run_experiments.py prepare
docker compose run --rm runner python run_experiments.py all --run-id full-securityeval --max-concurrency 64
docker compose run --rm runner python run_experiments.py report --run-id full-securityeval
```

Chi tiết setup nằm trong [setup.md](setup.md).
