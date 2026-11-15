# Fixture M1 — hoàn toàn tổng hợp

`stories.jsonl` do người triển khai soạn để kiểm tra logic, không trích dataset Hugging Face, dev hoặc golden test. Không dùng fixture để train/đánh giá chất lượng mô hình.

14 dòng: A01/A02 trùng sau NFC và chuẩn hóa khoảng trắng; A02 thuộc nhóm B nối A01/A03 thuộc nhóm A với A04 thuộc B, nhằm kiểm tra hợp nhất bắc cầu. Các nhóm C/D/E độc lập. Có chuỗi rỗng, sai kiểu text, thiếu text, thiếu nhóm nguồn, JSON hỏng, mảng thay vì object và dòng trắng. Một truyện bị cắt, một truyện lặp và một ký tự điều khiển được giữ nguyên, chỉ gắn cờ. Fixture dùng `text`; mẫu Hugging Face dùng `vi` qua cấu hình `--text-field`.
