---
name: summarize
track: bonus
kind: local_formatter
provider: ""
requires_env: []
inputs: [items, mode, query, limit]
outputs: [items, input_count, output_count]
side_effect: false
---
# summarize

Lọc và xếp hạng danh sách `items` đã lấy từ các tool khác trước khi trình bày bằng `format`.

## Các chế độ (`mode`)

- `highlights` — giữ top `limit` item có field `score` cao nhất; nếu không có `score` thì giữ N item đầu tiên.
- `by_date` — sắp xếp theo field `date` hoặc `published` giảm dần (mới nhất trước).
- `dedupe` — loại bỏ item trùng `source` domain, chỉ giữ item đầu tiên của mỗi nguồn.
- `score` — xếp hạng theo số từ của `query` xuất hiện trong `title` + `summary`.

## Tham số

- `items`: danh sách dict từ tool khác (`lookup`, `papers`, `hn_search`...). Mỗi item có thể có các field: `title`, `url`, `source`, `summary`, `score`, `date`/`published`.
- `mode`: một trong `highlights`, `by_date`, `dedupe`, `score` (mặc định `highlights`).
- `query`: từ khóa để xếp hạng — chỉ dùng khi `mode="score"`.
- `limit`: số item đầu ra, từ 1 đến 20 (mặc định 5).

## Khi nào dùng

Agent đã có nhiều items từ nhiều tool và cần lọc/xếp hạng trước khi truyền
vào `format`. Ví dụ:

- Lấy 15 kết quả `lookup` rồi chỉ giữ 5 bài từ 5 nguồn khác nhau → `dedupe`
- Muốn hiển thị bài mới nhất → `by_date`
- Có nhiều bài, muốn ưu tiên bài liên quan nhất với từ khóa → `score`
- Muốn hiển thị top bài điểm cao nhất (khi items có field `score`) → `highlights`

## Khi nào KHÔNG dùng

- Muốn **lấy dữ liệu mới** → dùng `lookup` / `papers` / `hn_search`
- Muốn **trình bày trực tiếp** mà không cần lọc → dùng `format`

## Ghi chú kỹ thuật

Không gọi mạng. Không cần API key. Không raise: mọi lỗi đều trả về
`{"tool": "summarize", "error": ..., "message": ...}`.

