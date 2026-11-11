# Báo cáo cá nhân — HoVaTen-MSSV

Đổi tên file theo quy tắc `MSSV_HoTen.md`.

Ví dụ: `20241234_NguyenVanAn.md`.

## 1. Thông tin thành viên

- Họ tên: Trần Phú Thái
- MSSV: 2A202604001
- Email:

## 2. Phần việc phụ trách

- Viết lại description và convention args trong `starter_v0/artifacts/tools.yaml`.
- Viết ≥ 3 unit test cho tool mới trong `starter_v0/tests/test_tools_todo.py`.
- Cấu hình bot và private channel Telegram.

## 3. Đóng góp cụ thể

- Tóm tắt các tool có sẵn cho nhóm.
- Cập nhật `tools.yaml` cho v2.
- Viết tool mới: `summarize` để tóm tắt và trích xuất thông tin có cấu trúc từ danh sách items đã có, có thể lọc, xếp hạng và tổng hợp insight từ nội dung. Đây là một local formatter tool, có thể test hoàn toàn offline
- Tạo eval case cho tool mới `G10_summarize_dedupe_after_lookup`
- Tạo bot Telegram và cấu hình `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`.

## 4. Bằng chứng

- File/commit/PR:
    - Commit `eba2518`
    - tools/summarize
    - Eval case `G10_summarize_dedupe_after_lookup` trong eval_group.json

- AI/công cụ đã dùng và cách tự kiểm tra kết quả:
    - Sử dụng Antigravity để giải thích cấu trúc báo cáo, gợi ý tool mới và triển khai tool
    - Tự đối chiếu hướng gợi ý với yêu cầu đề bài

## 5. Tự đánh giá

- Hoàn thành nhiệm vụ được giao
- Chưa đánh giá được hiệu quả cụ thể của tool

