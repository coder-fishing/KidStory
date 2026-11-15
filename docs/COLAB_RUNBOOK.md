# Runbook Colab cho M3–M5

## M3 baseline: đã có notebook, chưa chạy trên Colab

Notebook [m3_baseline_colab.ipynb](../notebooks/m3_baseline_colab.ipynb) clone repo public trực tiếp từ nhánh `main`, ghi commit, yêu cầu GPU CUDA, cài các dependency pin trong [m3-colab.lock.txt](../requirements/m3-colab.lock.txt), mount Drive theo mặc định rồi gọi `kids_story.baseline.run_baseline`. PyTorch do Colab cung cấp được giữ nguyên và ghi vào `run_config.json`. Notebook không cài Unsloth, không cần Hugging Face token cho model public và không đọc golden draft.

Trước khi mở notebook:

1. Notebook lấy code từ nhánh `main` hiện có trên GitHub. Để chạy commit khác, cập nhật nhánh `main` trước.
2. Repo hiện public nên không cần cấu hình GitHub Secret hoặc token.
3. Chọn runtime có GPU. Notebook sẽ dừng nếu CUDA không có; loại GPU/VRAM được ghi nhận khi có.
4. Chạy cell tuần tự. Mặc định Drive được mount qua giao diện Colab và artifacts lưu ở `MyDrive/kids-story-runs/m3/<run_id>`. Nếu tắt `SAVE_TO_DRIVE`, output nằm trong runtime tạm thời.
5. Chỉ coi artifact hợp lệ khi `COMPLETE.json` có mặt và các hash trong đó được notebook xác minh. `completed_with_errors` không phải baseline đầy đủ.

Dependency pins hiện có phiên bản cụ thể nhưng **chưa được smoke test trên runtime Colab**. Notebook phải được chạy thực tế để xác nhận tương thích PyTorch/CUDA/GPU; nếu cài đặt hoặc nạp model lỗi, ghi đúng lỗi và cập nhật lock bằng một lần chạy có truy vết. Không cài Unsloth trong M3; Unsloth thuộc thử nghiệm QLoRA M4.

## M4–M5: quy trình dự kiến

1. Trước train, khóa phiên bản tương thích torch/CUDA/Unsloth/Transformers/TRL/PEFT/bitsandbytes theo runtime được cấp.
2. Smoke test: kiểm tra token-label mask, finite loss trên batch, lưu/nạp adapter và inference; chỉ dùng dữ liệu phù hợp, không dùng final test.
3. Ghi run_id, cấu hình hiệu lực, seed, manifest, output thô và log. Giữ adapter/config/tokenizer/chat template cùng checksum. Nếu cần resume train, lưu optimizer, scheduler, step, RNG và sampler state theo khả năng stack.
4. Kiểm tra artifacts được ghi đủ và thử nạp lại trước khi xóa bản runtime. Chỉ có adapter thường không thể khôi phục chính xác trạng thái optimizer/step.
5. Khi đánh giá, khóa base revision, adapter, tokenizer/template và generation config. Không dùng final test chọn prompt, checkpoint hoặc model.

## Khi OOM hoặc mất phiên

OOM: ghi bước lỗi và cấu hình; giải phóng phiên lỗi, thử giảm sequence length theo phân bố token, micro-batch; dùng gradient accumulation để giữ effective batch nếu phù hợp, cân nhắc gradient checkpointing/packing chỉ sau xác minh mask. Không âm thầm cắt assistant mất kết truyện. Mỗi thay đổi tạo run config mới; không tuyên bố cấu hình bảo đảm vừa GPU khác.

Mất runtime: khôi phục commit, môi trường khóa, dataset manifest/hash; kiểm tra checkpoint cuối đầy đủ. Nếu chỉ có adapter, chạy inference hoặc khởi tạo run mới và ghi mất trạng thái resume. Không ghi đè checkpoint tốt bằng file dang dở; đề xuất ghi thư mục tạm, kiểm tra rồi đánh dấu complete.

[FAQ Colab chính thức](https://research.google.com/colaboratory/faq.html) mô tả tài nguyên/giới hạn thay đổi và không được bảo đảm. Không hứa loại GPU hay thời lượng cố định cho Colab Free.
