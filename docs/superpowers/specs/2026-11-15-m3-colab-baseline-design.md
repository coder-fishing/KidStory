# Đặc tả M3: baseline Qwen trên Colab

Ngày: 2026-11-15

Trạng thái: Bản thiết kế chờ người dùng duyệt

Phạm vi: chạy suy luận baseline; không huấn luyện

## Mục tiêu

Tạo một lần chạy có thể truy vết của mô hình gốc Qwen2.5-3B-Instruct trên tập phát triển, dùng đúng prompt hiện có. Kết quả dùng để khảo sát hành vi và hoàn thiện quy trình đánh giá; không phải kết luận mô hình tốt, an toàn hoặc cải thiện hơn một mô hình khác.

M2 vẫn còn các xác nhận của người chấm và người độc lập. Theo yêu cầu của người dùng, M3 có thể bắt đầu song song trên tập dev. Việc chạy này không đổi trạng thái M2, không dùng tập golden và không ảnh hưởng đến tập train/validation.

## Phạm vi

- Thêm module Python để tải tokenizer/mô hình tại revision cố định, dựng messages, sinh văn bản và lưu run artifact.
- Thêm notebook Colab mỏng cho M3 để kiểm tra runtime, lấy mã nguồn tại commit xác định, cài dependencies đã khóa, cấu hình đường dẫn và gọi module.
- Chỉ dùng `data/evaluation/dev_cases.jsonl`. Input của mô hình là trường `prompt` đã được tạo sẵn và system prompt `prompts/story_system_v1.txt`.
- Ghi output thô, cấu hình hiệu lực, môi trường, thời gian, mã nguồn và checksum vào thư mục mới trong `outputs/`.
- Kiểm thử logic không cần tải weights bằng fixture tổng hợp.

## Ngoài phạm vi

Không fine-tune/QLoRA trong M3, chọn checkpoint, chấm điểm, thay prompt, chỉnh rubric, mở hoặc dùng golden draft, xây ứng dụng Gradio, gọi API trả phí, tải model vào repo hay chạy model trên máy Windows hiện tại. Unsloth được dành cho M4 để thử QLoRA; không cài hoặc dùng nó trong baseline M3. Không khẳng định môi trường Colab/GPU đã được kiểm tra nếu notebook chưa thực sự chạy.

## Quyết định thiết kế

Model là `Qwen/Qwen2.5-3B-Instruct`, revision bất biến `aa8e72537993ba99e69dfaafa59ed015b17504d1`. Model card tại revision cho biết model có 3.09 tỷ tham số và liệt kê tiếng Việt trong hỗ trợ đa ngôn ngữ. Đây là thông tin nhà phát hành, không phải kiểm chứng chất lượng tiếng Việt của đồ án. LICENSE tại revision là Qwen RESEARCH LICENSE AGREEMENT: định nghĩa phi thương mại là nghiên cứu/đánh giá và chỉ cấp quyền cho mục đích phi thương mại. Dự án đã khai báo là học tập/thi cử phi thương mại; không phân phối weights hoặc model như một dịch vụ trong M3. Người dùng cần tuân thủ toàn bộ điều khoản khi sử dụng hay phân phối artifact. Nguồn: [model card](https://huggingface.co/Qwen/Qwen2.5-3B-Instruct/tree/aa8e72537993ba99e69dfaafa59ed015b17504d1), [LICENSE tại revision](https://huggingface.co/Qwen/Qwen2.5-3B-Instruct/blob/aa8e72537993ba99e69dfaafa59ed015b17504d1/LICENSE).

M3 dùng Transformers trực tiếp để baseline phản ánh đường chạy model gốc, không trộn tối ưu hóa loader/training. Unsloth được dự kiến dùng ở M4 cho QLoRA trên Colab; khi tới M4 phải kiểm tra model/GPU support và pin bộ phiên bản tương thích theo runtime thực tế. Unsloth có hướng dẫn cài đặt Colab và fine-tune; điều đó không thay cho smoke test của đồ án: [Colab](https://unsloth.ai/docs/get-started/install/google-colab), [yêu cầu hệ thống](https://unsloth.ai/docs/get-started/fine-tuning-for-beginners/unsloth-requirements).

Ba cách triển khai đã cân nhắc:

1. **Module Python + notebook mỏng (chọn):** logic chỉ có một nơi, chạy kiểm tra trên CPU được mà không tải model; Colab chỉ thiết lập môi trường và gọi module.
2. **Viết hết trong notebook:** làm nhanh trong một file nhưng logic khó kiểm thử, dễ lệch khi chuyển môi trường và khó tái sử dụng cho M4.
3. **Chỉ có CLI local:** dễ gọi lại nhưng máy hiện tại không có GPU hoặc thư viện model, nên không tạo được baseline theo M3.

## Luồng xử lý

1. Người dùng chọn một thư mục output mới và xác nhận commit làm căn cứ chạy. Notebook ghi commit, trạng thái working tree, phiên bản Python/thư viện, GPU/VRAM và đường dẫn input.
2. Runner xác thực tập input là JSONL, mỗi dòng có `id` và `prompt` dạng chuỗi. Dòng lỗi, thiếu prompt, prompt rỗng hoặc ID trùng làm run thất bại trước khi tải model; không tự bỏ qua để tránh thiếu đề âm thầm.
3. Runner đọc nguyên văn system prompt và `prompt` của từng dòng dev. `expected_behavior`, constraints dùng chấm, rubric, review notes và dữ liệu golden không được đưa vào messages.
4. Runner tải tokenizer và model theo đúng revision đã khóa. Nếu không có GPU, thiếu dung lượng hoặc tải model thất bại, dừng trước sinh; ghi lỗi, không ghi `COMPLETE.json`.
5. Mỗi dev case được sinh độc lập với cùng cấu hình. Output không bị cắt gọt, hậu xử lý hoặc tự sinh lại. Lỗi từng case được ghi cùng ID; run chỉ hoàn tất khi mọi case có kết quả hoặc lỗi được ghi rõ.
6. Runner lưu output thô và bản ghi cấu hình/checksum vào thư mục output mới. Nếu thư mục đã tồn tại thì từ chối ghi đè. Chỉ tạo `COMPLETE.json` khi mọi input có output hoặc lỗi được ghi, các file bắt buộc đã được ghi và hash khớp. Run có mọi case thành công mang trạng thái `complete`; nếu có lỗi theo từng case thì mang trạng thái `completed_with_errors`, không được báo là baseline đầy đủ.
7. Người nghiên cứu xem output trên dev và ghi nhận thay đổi prompt/cấu hình ở nhật ký thí nghiệm. Không xem kết quả này là đánh giá cuối; không dùng golden để lựa chọn cấu hình.

## Cấu hình baseline ban đầu

Giá trị ban đầu theo `docs/AI_DESIGN.md`: seed 42, lấy mẫu (`do_sample=true`), temperature 0.7, `top_p=0.9`, `repetition_penalty=1.0`, `max_new_tokens=512`. Đây là cấu hình khảo sát, chưa được hiệu chuẩn; lưu cả giá trị hiệu lực và cảnh báo rằng giới hạn 512 token có thể kết thúc trước 150–250 đơn vị cách trắng. Không tự đổi tham số giữa các đề trong một run.

Notebook yêu cầu GPU được cấp trong runtime Colab và ghi lại loại GPU/VRAM thực tế. Nếu thiếu GPU, notebook dừng ở kiểm tra môi trường, không tự chuyển sang CPU hoặc tuyên bố đã có baseline. Dependencies M3 (PyTorch runtime do Colab cung cấp cùng Transformers/Accelerate cần thiết) phải được pin hoặc ghi chính xác theo phiên bản runtime trong artifact; việc cài đặt chỉ diễn ra khi người dùng chạy notebook. Không cài Unsloth trong M3. Ở M4, pin và smoke test riêng bộ Unsloth/TRL/PEFT/quantization theo GPU được cấp. Không yêu cầu token Hugging Face cho model public. Nếu lấy code từ repo private, notebook dùng cơ chế Colab Secret được cấu hình bởi người dùng; không nhúng token vào notebook, output hoặc URL.

## Hợp đồng artifact

| Artifact | Nội dung |
|---|---|
| `generations.jsonl` | Một dòng cho mỗi dev ID: ID, trạng thái, hash messages, văn bản sinh nguyên văn, token đầu ra, finish reason, thời gian hoặc lỗi |
| `run_config.json` | Model ID/revision, tokenizer revision, hash system prompt/input, commit, Python/dependency, GPU/VRAM, seed và generation parameters hiệu lực |
| `COMPLETE.json` | Hash artifact và trạng thái `complete` hoặc `completed_with_errors`; không tồn tại khi còn input chưa được xử lý/ghi lỗi hoặc hash sai |

Không ghi `expected_behavior` vào `generations.jsonl` nếu không cần thiết để chạy; không ghi secrets hoặc nội dung golden. Các output này nằm trong `outputs/` và bị Git ignore.

## Lỗi và hành vi dự kiến

- Thư mục output có sẵn -> từ chối ghi đè và yêu cầu run ID mới.
- JSONL không hợp lệ, ID trùng hoặc thiếu prompt -> dừng validation; không tải model, không tạo `COMPLETE.json`.
- Model/revision không truy cập được hoặc thiếu bộ nhớ -> ghi lỗi môi trường và dừng, giữ lại log chẩn đoán, không tạo artifact hoàn tất.
- Một case lỗi sau khi bắt đầu sinh -> ghi record lỗi theo ID, tiếp tục case độc lập khác; run không được đánh dấu hoàn tất nếu thiếu kết quả.
- Hết ngân sách token -> giữ nguyên phần đã sinh và ghi finish reason; không tự nối tiếp.
- Máy mất kết nối hoặc notebook bị ngắt -> artifact chưa hoàn tất không được xem là run thành công; chạy lại bằng thư mục mới, không trộn hai run.

## Kiểm tra chấp nhận

- Một fixture tổng hợp hợp lệ -> dựng messages đúng system/user và không chứa `expected_behavior`.
- Prompt dev rỗng, thiếu trường hoặc ID lặp -> bị từ chối trước khi tải model.
- Revision và hashes trong config -> được ghi đúng; không có secret hay trường golden.
- Thư mục output đã tồn tại -> runner từ chối ghi đè.
- Generation record lỗi/hết token -> lỗi hoặc finish reason được lưu, không biến thành output thành công.
- Run còn input chưa xử lý -> không có `COMPLETE.json`; mọi input có output hoặc lỗi -> trạng thái tương ứng được ghi và mọi hash trong `COMPLETE.json` khớp.
- Notebook thiếu GPU hoặc dependency -> dừng ở cell kiểm tra với thông báo rõ, không tiếp tục tới sinh.
- Chạy model thật trên dev -> ghi đủ số dòng và metadata, nhưng không tính metric hoặc kết luận chất lượng nếu chưa có rubric/duyệt phù hợp.

## Điều kiện bàn giao M3

M3 chỉ được báo hoàn thành sau khi notebook chạy trên Colab có GPU thực; phiên bản dependency và model revision được ghi lại; toàn bộ dev case được xử lý hoặc lỗi nêu rõ; artifact hashes được xác minh; run config/output raw được giữ; và câu lệnh thực tế được cập nhật vào README cùng EXPERIMENT_LOG. Nếu runtime không cấp GPU hoặc license/quyền dùng phát sinh giới hạn, dừng và báo phần chưa chạy thay vì giả lập kết quả.
