# Thiết kế mô hình và prompt

## Ứng viên và trạng thái

Ứng viên **Qwen/Qwen2.5-3B-Instruct** được đề xuất để thử mô hình instruction quy mô nhỏ trước; chưa có bằng chứng chạy vừa GPU Colab hoặc đạt yêu cầu tiếng Việt. Tra cứu sơ bộ ngày 2026-11-14: [model card chính thức](https://huggingface.co/Qwen/Qwen2.5-3B-Instruct) gắn nhãn `qwen-research`. Cần đọc toàn bộ điều khoản tại revision sẽ dùng, không coi đây là giấy phép Apache hoặc quyền thương mại mặc định. Chưa tải weights, chưa pin revision; M3 chỉ bắt đầu sau kiểm tra quyền sử dụng và môi trường.

## Hợp đồng prompt và SFT dự kiến

System dùng nguyên văn `prompts/story_system_v1.txt`; user được render từ `prompts/story_user_template_v1.txt`. Lưu cả giá trị trường, messages thực tế và hash file. Với đề robustness có chỉ dẫn bổ sung, lưu user content nguyên vẹn sau render và dùng giống nhau ở hai nhánh; không chèn tình tiết đáp án. Không dùng `expected_behavior` làm đầu vào sinh.

Schema hội thoại dự kiến là object có `messages`: danh sách ba object `{role, content}` theo thứ tự system, user, assistant. System là file prompt; user là template đã điền metadata **được duyệt**; assistant là `processed_text` được duyệt. Provenance, metadata và split lưu bên cạnh hoặc manifest, không đưa nhãn review vào nội dung hội thoại. Không có mẫu SFT thực ở M0; không tự suy ra bài học chỉ để lấp trường.

## Huấn luyện dự kiến

QLoRA dùng base lượng tử hóa và học tham số adapter LoRA; Unsloth là công cụ hỗ trợ nạp/huấn luyện tiết kiệm tài nguyên; TRL SFTTrainer điều phối SFT. Phiên bản tương thích và hỗ trợ thực tế phải được smoke test, không lấy tên công cụ làm bảo đảm VRAM. Tài liệu [SFTTrainer](https://huggingface.co/docs/trl/sft_trainer) mô tả assistant-only loss phụ thuộc hỗ trợ assistant mask của chat template. Không chỉ đặt một flag rồi giả định đúng.

M4 phải kiểm tra batch token/label trực quan: system, user và padding có label -100; phần assistant có label được học, có kết thúc phù hợp; không có mẫu toàn -100. Nếu dùng template khác, so sánh token IDs và role boundary với template chính thức; không đồng thời áp dụng hai cơ chế mask mà chưa kiểm tra. Học trên role marker nào phải ghi rõ và kiểm chứng theo phiên bản đang dùng.

Chat template của tokenizer phải cố định revision. Inference thêm generation prompt đúng cách; training không thêm đoạn assistant rỗng sau câu trả lời. Kiểm tra EOS/end-of-turn theo tokenizer thực tế, tránh thêm EOS hai lần hoặc dừng quá sớm. Padding token, attention mask, phía padding phải được kiểm tra riêng cho train và batch inference; không dùng padding làm target loss. Độ dài chuỗi dựa trên token của **toàn bộ hội thoại**. Đề xuất loại/đưa review mẫu vượt giới hạn thay vì cắt mất kết thúc truyện; báo tỷ lệ bị loại. Packing chỉ bật sau khi xác minh ranh giới mẫu/mask, không để truyện nối nhau gây học lẫn.

Pilot đề xuất 300–500 mẫu chất lượng ở M4; chưa chốt rank, batch size, learning rate, context length hay dtype. Chọn theo GPU thực, thống kê token và smoke test; ghi cấu hình trước chạy. Theo dõi validation loss để chọn checkpoint trong số ứng viên đã định, xử lý NaN và overfit. Không dùng golden test chọn checkpoint. Evaluation dev có thể dùng phân tích chất lượng/chỉnh prompt trong giai đoạn phát triển; phải ghi lịch sử thay đổi.

## So sánh sinh công bằng

Đề xuất ban đầu để thử trên dev: temperature 0.7, top_p 0.9, do_sample true, repetition_penalty 1.0, max_new_tokens 512, seed 42. Đây là cấu hình **chưa kiểm chứng**, không phải ngân sách token chắc đủ 150–250 đơn vị cách trắng. Xác minh phân bố độ dài/truncation rồi chốt trước final. Giữ cùng prompt, tokenizer, cách lượng tử hóa base, token budget, stop rules và config tương ứng cho hai nhánh; ghi cả giá trị mặc định hiệu lực. Nếu cần khác môi trường/dtype thì báo confound. Seed giống nhau không bảo đảm output tái lập bitwise; có thể dùng danh sách seed định trước để đo biến thiên.

## Giả thuyết lỗi và phép kiểm chứng

| Giả thuyết | Kiểm chứng dự kiến |
|---|---|
| Bản dịch làm sai đại từ/tên | Người đọc đối chiếu original/processed, gắn cờ và R2/R3 |
| Fine-tune học rao giảng, quên ràng buộc | So sánh cặp R1/R5 trên dev và xem lỗi |
| Mask sai làm học lại prompt | Kiểm tra token-label, overfit một fixture nhỏ được ghi rõ |
| Mất kết truyện do token budget | Log finish reason, token count, R2; chỉnh trên dev |
| Suy giảm an toàn hoặc từ chối quá mức | UC05/UC06, S1 riêng và người chấm |
| VRAM không đủ | Smoke test trên GPU thực, giảm cấu hình có ghi log |

Các phép kiểm chứng trên chưa chạy ở M0.
