# Quy tắc làm việc

- Chỉ thực hiện milestone được giao; hiện trạng là công cụ M2 CPU, đang chờ duyệt dữ liệu/quyền nguồn, chưa có SFT thực/model. Đọc README và tài liệu liên quan trước khi sửa. Không tự mở rộng sang train hoặc demo.
- Đọc file hiện có trước khi sửa, giữ thay đổi của người dùng; không ghi đè dữ liệu chưa kiểm tra. Báo xung đột thay vì xóa nội dung.
- Logic chính nằm trong module Python; notebook Colab chủ yếu thiết lập và gọi module.
- Đường dẫn, seed và tham số phải cấu hình được. Module dữ liệu chạy trên CPU, không import CUDA/GPU stack bắt buộc.
- Không bịa dữ liệu, kết quả, metric hay trạng thái kiểm tra. Fixture tổng hợp phải ghi rõ là minh họa. Thông tin chưa biết ghi Đề xuất / Giả định / Cần xác minh.
- Không đưa secrets, dataset lớn, weights, checkpoint, adapter hoặc cache vào Git. Không đưa token vào notebook, log hay URL Git.
- Không dùng final test để train, chỉnh prompt, chọn checkpoint hay chọn model. Golden draft chưa được duyệt; nếu đã dùng để chỉnh hệ thống phải ghi nhận nhiễm và chuẩn bị holdout mới.
- Giữ `review_status=pending` cho đến khi người duyệt thực sự xác nhận; không tự điền `human_checklist_passed`.
- Đọc docs/M2_REVIEW_GUIDE.md trước khi nhận bảng duyệt. Không sửa ID/hash/read-only hoặc ledger thành confirmed thay người dùng; text đã sửa phải qua vòng pending rồi review mới. `--synthetic` chỉ cho fixture có provenance tổng hợp rõ ràng.
- Khử trùng và kiểm soát nhóm nguồn trước chia tập; không tuyên bố đã xử lý gần trùng nếu chưa có phương pháp và bằng chứng.
- Chạy kiểm tra có ý nghĩa cho logic quan trọng, báo lệnh và kết quả thật. Báo rõ phần chưa chạy và nguyên nhân. Kiểm tra cấu trúc không chứng nhận chất lượng sư phạm/an toàn.
- Không tự push, tạo repo từ xa, xuất bản, gửi thông tin cho người khác hoặc dùng dịch vụ trả phí.
- Không tự cài GPU stack hay tải toàn bộ dữ liệu/weights trong giai đoạn tài liệu. Xác minh giấy phép, revision và môi trường trước các milestone sử dụng thực tế.
