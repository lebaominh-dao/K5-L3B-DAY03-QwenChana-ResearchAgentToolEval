# Team

## Thông tin nhóm

- Tên nhóm: QwenChana
- Lớp: L3B
- Repo nhóm: `K5-L3B-DAY03-QwenChana-ResearchAgentToolEval`
- URL repo, nhánh nộp, commit chốt:

## Thành viên

| STT | Họ tên | MSSV | Email | GitHub | Vai trò |
| --: | ------ | ---- | ----- | ------ | ------- |
|   1 | Đào Lê Bảo Minh | 2A202604010 | 26ai.dlbminh@vinuni.edu.vn | https://github.com/lebaominh-dao | Trưởng nhóm (A) — setup, chạy eval, version log, eval nhóm |
|   2 | Trần Trung Kiên | 2A202604014 |  | https://github.com/ttkien0710 | Phân tích lỗi, hypothesis, báo cáo nhóm (B) |
|   3 | Trần Phú Thái | 2A202604001 | <Email> | <GitHub> | Tool declaration, tool mới, unit test, Telegram (C) |
|   4 | Hoàng Xuân Lĩnh | 2A202604017 | <Email> | hxlinh | UI Streamlit, demo, live chat (D) |

## Phân công tổng quan

| Hạng mục (Rubric) | Phụ trách chính | Hỗ trợ |
|---|---|---|
| C1 — Baseline v0 và phân tích lỗi | A (chạy v0) | B (bảng B2) |
| C2 — Prompt và tool declaration | A (`system_prompt.md`) | C (`tools.yaml`) |
| C3 — Vòng lặp v1 → v3 | A (chạy eval, `version_log.csv`) | B (hypothesis, bảng B1) |
| C4 — Tool mới và unit test | C | A |
| C5 — 10 case eval nhóm | A | C (case route tới tool mới) |
| C6 — UI và live chat | D | — |
| C7 — Báo cáo nhóm | B (Phần B) | D (Phần A), cả nhóm |
| Bonus Telegram | C (bot, channel) | D (transcript live) |

## Cá nhân

Mỗi thành viên đồng thời tạo một báo cáo riêng trong `report/` theo dạng:

```text
report/team/MSSV_HoTen.md
```

Ví dụ: `report/team/20241234_NguyenVanAn.md`.

## DaoLeBaoMinh-2A202604010 (Trưởng nhóm)

### Phần việc phụ trách

- Setup repo, `.env`, preflight, `pytest`.
- Chạy toàn bộ eval (v0 → v3, suite group), kiểm tra run hợp lệ, ghi `starter_v0/artifacts/version_log.csv`.
- Sửa `starter_v0/artifacts/system_prompt.md` theo hypothesis của B.
- Viết 10 case trong `starter_v0/data/eval_group.json`.
- Điều phối, merge branch, push bản nộp.

### Đóng góp cụ thể

- Chạy baseline v0 (case_accuracy 0.75) và v1 (0.85).
- Sửa prompt v1: thay chỉ dẫn tự đoán bằng rule gọi `clarify` khi thiếu account/URL.
- Viết 10 case eval nhóm (5 single turn + 5 multi turn).

### Bằng chứng

- Commit: `c23148b` (v0 run), `7d4aec7` (version log + eval nhóm), `75ef318` (v1 prompt + run).
- Run: `starter_v0/runs/v0_B_base_openrouter_20261110T173925903234.json`, `starter_v0/runs/v1_B_base_openrouter_20261110T185630444201.json`.

## TranTrungKien-2A202604014

### Phần việc phụ trách

- Đọc run JSON sau mỗi version, phân loại case FAIL theo `failure_type`.
- Viết hypothesis cho version tiếp theo.
- Viết bảng B1, B2 và hoàn thiện Phần B của `report/team/group_report.md`.

### Đóng góp cụ thể

- Bảng B2 cho v0 và v1; hypothesis v1 (bỏ tự đoán → `clarify`) và v2 (`clarify` phải truyền `response_type`).

### Bằng chứng

- Commit: `abb567f` (B1_B2_v0), `bff6f00` (v1 Hypothesis Update), `28575d9` (B1_B2_v1).

## TranPhuThai-2A202604001

### Phần việc phụ trách

- Viết lại description và convention args trong `starter_v0/artifacts/tools.yaml`.
- Viết tool mới (`tools/<tên>/tool.py` + `TOOL.md`), đăng ký trong `tools/__init__.py` và `tools.yaml`.
- Viết ≥ 3 unit test cho tool mới trong `starter_v0/tests/test_tools_todo.py`.
- Cấu hình bot và private channel Telegram.

### Đóng góp cụ thể

- Tóm tắt các tool có sẵn cho nhóm.
- Cập nhật `tools.yaml` cho v2.
- Tạo bot Telegram và cấu hình `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`.

### Bằng chứng

- Commit: `fcad954` (Update tools từ v1 lên v2).

## HoangXuanLinh-2A202604017

### Phần việc phụ trách

- UI Streamlit (`starter_v0/app.py`): tab Chat với agent và tab xem Eval runs.
- Mở link dùng thử bằng Cloudflare Tunnel cho Team showdown.
- Viết Phần A của `report/team/group_report.md`.
- Chạy `chat.py` ≥ 3 lượt live và viết bảng B4.

### Đóng góp cụ thể

- Viết UI Streamlit, thêm dependency vào `starter_v0/requirements.txt`.

### Bằng chứng

- Commit: `91056b6` (feat: ui).
