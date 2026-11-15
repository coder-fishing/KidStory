# Bài toán và phạm vi

## Mục tiêu

Hỗ trợ phụ huynh, giáo viên và người chăm sóc tạo truyện tiếng Việt cho trẻ 6–8 tuổi. Người lớn đọc và duyệt trước khi dùng với trẻ. Nghiên cứu xem QLoRA có cải thiện chất lượng so với cùng base model dùng System Prompt tốt hay không, không mặc định fine-tune sẽ thắng.

## Hợp đồng sản phẩm v1

Đầu vào gồm chủ đề, nhân vật, bài học và độ dài tùy chọn. Đầu ra có mở đầu, diễn biến, kết thúc; nhân vật/sự kiện nhất quán; câu từ tự nhiên, phù hợp tuổi; bài học thể hiện qua tình huống và hành động. Không bắt buộc đoạn “Bài học rút ra”. Đề xuất mặc định 150–250 đơn vị cách trắng, đếm bằng tách khoảng trắng Unicode; đây là giới hạn kỹ thuật cần kiểm tra trên dev. Đề cụ thể được ưu tiên hơn mặc định. Không đồng nhất đơn vị này với từ tiếng Việt đã phân đoạn hoặc model token.

JSON, đúng số câu, lỗi nhập liệu và prompt injection là nhóm kiểm tra mở rộng, chưa cam kết là chức năng chính của giao diện. Cho phép tưởng tượng, nỗi sợ nhẹ, bất đồng và tình huống nguy hiểm được giải quyết an toàn. Không hướng dẫn trẻ thực hiện việc nguy hiểm.

## Giới hạn lượt này

M0 chỉ gồm tài liệu, quy tắc, prompt và bộ đánh giá bản nháp. Không tải toàn bộ dữ liệu/weights, cài GPU stack, chạy baseline/train, tạo ứng dụng, repo từ xa hoặc push. Không API trả phí, LangChain, MCP, RAG hay multi-agent trong kiến trúc sản phẩm.

## Tiêu chí thành công đề xuất

- M0: đủ artifact, JSONL hợp lệ, đúng phân bố, truy vết use case/rubric, tất cả mẫu chờ duyệt.
- Nghiên cứu: so sánh cặp ẩn danh cùng đề và điều kiện sinh, báo chất lượng, an toàn, từ chối quá mức, chi phí tài nguyên và độ bất định.
- Đề xuất cho M2: đạt trung vị ít nhất 4/5 ở từng chiều chất lượng trên đề sinh truyện; không có lỗi an toàn nghiêm trọng trong tập đã chấm. Đây là ngưỡng khởi điểm cần người hướng dẫn lý giải và chốt trên dev trước final, không phải bảo đảm an toàn.
- Chỉ kết luận có cải thiện nếu bằng chứng cặp và khoảng bất định hỗ trợ; kết quả âm hoặc chưa đủ dữ liệu vẫn có giá trị nghiên cứu.

## Giả định và việc cần xác minh

Qwen/Qwen2.5-3B-Instruct là ứng viên về quy mô, chưa xác nhận chất lượng tiếng Việt hay chạy vừa GPU được cấp. Dataset nampdn-ai/tinystories-vietnamese cần kiểm tra schema tại revision cố định, chuỗi nguồn gốc và giấy phép của cả bản dịch/nguồn gốc. Khả năng gán đúng bài học, ngân sách duyệt 300–500 mẫu pilot, độ dài phù hợp và tài nguyên Colab đều cần xác minh. Không suy ra quyền sử dụng đầy đủ chỉ từ nhãn license trên Hub.
