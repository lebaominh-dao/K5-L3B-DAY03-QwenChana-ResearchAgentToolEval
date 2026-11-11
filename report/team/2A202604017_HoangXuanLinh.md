# Báo cáo cá nhân — HoangXuanLinh-2A202604017

Đổi tên file theo quy tắc `MSSV_HoTen.md`.

Ví dụ: `20241234_NguyenVanAn.md`.

## 1. Thông tin thành viên

- Họ tên: Hoàng Xuân Lĩnh
- MSSV: 2A202604017
- Email: 26ai.linhhx@vinuni.edu.vn

## 2. Phần việc phụ trách

UI Streamlit, link dùng thử cho Team showdown, Phần A của báo cáo nhóm, chat live và bảng B4.

## 3. Đóng góp cụ thể

- Viết `starter_v0/app.py`, tái dùng vòng lặp model → tool của `chat.py` và ghi transcript cùng format.
  - Trang Chat: khung chat ở giữa, sidebar liệt kê tool đọc từ `tools.yaml` (tool mới tự có nhãn MỚI), câu hỏi mẫu bấm được, hiện mọi tool call và lỗi tool.
  - Trang Eval runs: đọc `runs/*.json`, kiểm tra run hợp lệ, hiện metric, case FAIL, expected vs actual, `version_log.csv`.
- Thêm `streamlit` vào `requirements.txt` và theme `.streamlit/config.toml`.
- Mở link public bằng Cloudflare Tunnel.
- Viết Phần A (A1, A2, A3) của `group_report.md`.
- Thiết kế lại UI: chat ở giữa, sidebar tool, câu hỏi mẫu, nút Cài đặt; gộp tính năng chọn snapshot `artifacts/versions/<v>` của Minh vào UI mới khi rebase; thêm icon cho tool mới `hn_search`, `summarize`; câu hỏi mẫu đồng bộ với A3 và chỉ giữ câu đã chạy đúng ở v4.
- Chat live bằng `chat.py`: 5 lượt với v2 và 9 lượt với v4, viết bảng B4 so sánh hai version.
- Phát hiện agent v2 tự đặt `confirmed=true` khi gọi `send` dù user chưa xác nhận. Đã báo nhóm, v3 sửa bằng rule xin xác nhận trước.
- Phát hiện case R04 PASS dù URL `https://openai.com/blog/gpt-5` đã 404, vì eval chỉ chấm routing, không chấm nội dung.

## 4. Bằng chứng

- Commit:
  - `91056b6` UI Streamlit bản đầu
  - `b9c0520` thiết kế lại UI, gộp tính năng chọn snapshot
  - `21e2685` Phần A, bảng B4 v2, transcript v2
  - `8330a22` báo cáo cá nhân
  - `4824506` icon tool mới trong UI, transcript và bảng B4 v4
- Transcript:
  - `starter_v0/transcripts/v2_openrouter_20261111T004058101246.transcript.json` (chat.py, v2, 5 lượt)
  - `starter_v0/transcripts/v4_openrouter_20261111T094443610365.transcript.json` (chat.py, v4, 9 lượt)
  - `starter_v0/transcripts/v2_openrouter_ui_20261111T002104008525.transcript.json` (UI, v2)


## 5. Tự đánh giá

- Hoàn thành đúng phần được giao (UI, link dùng thử, Phần A, bảng B4), và qua chat live đã phát hiện được lỗi thật để nhóm sửa ở v3.
- Có lúc kiểm tra chưa kỹ: chọn câu hỏi mẫu chỉ dựa vào kết quả PASS mà không tự chạy lại, nên dùng nhầm URL đã chết.
- Học được rằng eval PASS chưa đủ để tin kết quả, cần tự kiểm tra thủ công những phần người dùng thực sự thấy.
