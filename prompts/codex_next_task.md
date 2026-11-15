# Giao M1: đường xử lý dữ liệu CPU

Đọc AGENTS.md, README.md và docs, đặc biệt DATA_PLAN/ROADMAP/EVALUATION_PLAN trước khi thay đổi. Kiểm tra môi trường và hiện trạng repo, đọc file trước sửa và giữ thay đổi người dùng. Chỉ triển khai M1; chưa train GPU, chưa demo, chưa push GitHub hoặc sử dụng dịch vụ trả phí.

Tạo đường xử lý JSONL chạy được trên CPU bằng module Python. Notebook không chứa logic chính. Tách phần tải mẫu nguồn khỏi phần xử lý file cục bộ: pipeline và tests phải chạy offline bằng fixture minh họa, không cần CUDA, weights hoặc truy cập Hub. Không tự tải toàn bộ nguồn.

Trước khi dùng nguồn thực nampdn-ai/tinystories-vietnamese, xác minh schema/kiểu dữ liệu, nguồn gốc, giấy phép và revision bất biến; ghi kết quả và phần chưa rõ. Không coi quan sát viewer ở M0 là xác minh hoàn tất. Nếu không truy cập/xác minh được, tiếp tục phần cục bộ với fixture tổng hợp ghi rõ, báo phần nguồn bị chặn thay vì giả dữ liệu thực.

Thực hiện chuẩn hóa Unicode NFC và khoảng trắng có chính sách rõ, giữ original_text, processed_text, source_id/provenance và lý do sửa. Ghi cờ rỗng/sai kiểu/cắt/lặp/cần rà soát; heuristic không thay người duyệt. Khử trùng chính xác trên text chuẩn hóa trước chia, giữ ánh xạ mọi source IDs. Chia train/validation theo nhóm nguồn hợp nhất với nhóm exact duplicate, seed/đường dẫn/tỷ lệ cấu hình được, lưu manifest và hash. Không khẳng định xử lý gần trùng nếu chưa có phương pháp, ngưỡng được kiểm tra và bằng chứng; ghi residual risk. Không thay tên/đại từ hàng loạt hoặc xóa ngoại ngữ để che lỗi. Metadata thiếu để null/pending, chưa xuất SFT.

Dùng fixture nhỏ được ghi rõ là tổng hợp, có trường hợp Unicode composed/decomposed, khoảng trắng khác nhau, dữ liệu rỗng/sai kiểu, trùng exact và nhiều bản ghi cùng nhóm nguồn. Kiểm tra logic quan trọng: giữ original, idempotence chuẩn hóa, phát hiện exact, không rò nhóm nguồn/nhóm exact giữa split, thứ tự đầu vào được xử lý theo chính sách công khai, cùng seed tái lập manifest. Xử lý trường hợp quá ít nhóm để chia; không báo thành công khi một split rỗng ngoài dự kiến. Không dùng dev/golden test làm fixture train hoặc để chọn bộ lọc.

Chạy các kiểm tra thực tế trên CPU. Cập nhật README bằng lệnh thực sự đã chạy và đầu ra mẫu có nhãn fixture; không ghi lệnh dự kiến như đã hoạt động. Báo file sửa, kết quả thật, phần chưa chạy và lý do, rủi ro còn lại trước M2. Không tạo module rỗng chỉ để đủ kiến trúc.
