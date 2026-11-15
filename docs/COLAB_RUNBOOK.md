# Runbook Colab dự kiến cho M3–M5

**Chưa có notebook hoặc CLI triển khai. Chưa chạy bước nào dưới đây trong M0.** Không sao chép tên module dự kiến thành lệnh được cho là tồn tại.

1. Khi repo từ xa đã được người dùng tạo/cho phép: clone hoặc pull rồi checkout commit định dùng. Ghi `git rev-parse HEAD` và `git status --porcelain`; nếu dirty lưu diff/hash. Không tự push hoặc đưa token vào URL/notebook. Dùng cơ chế secrets khi cần truy cập riêng.
2. Chọn runtime có GPU nếu được cấp; kiểm tra GPU/VRAM thực bằng công cụ môi trường (ví dụ `nvidia-smi`, lệnh khảo sát dự kiến). Nếu không có GPU thì không cố train GPU. Ghi GPU, driver, Python và VRAM khả dụng.
3. Cài dependencies từ bộ phiên bản sẽ được xác minh bằng smoke test sau này, ghi toàn bộ version lock; không đưa một lệnh pip latest thành môi trường tái lập. Kiểm tra tương thích torch/CUDA/Unsloth/transformers/TRL/PEFT/bitsandbytes. M0 chưa chốt bộ phiên bản.
4. Mount Drive qua giao diện Colab có xác thực. Đường dẫn từ config, kiểm tra quyền ghi và dung lượng. Chỉ copy snapshot cần thiết vào runtime; giữ bản nguồn bất biến trên Drive, xác minh hash.
5. Smoke test trước run dài: import, nạp tokenizer/model revision, render hội thoại, sinh một mẫu; training phải kiểm tra token-label mask, một batch finite loss, lưu rồi nạp lại adapter. Mẫu smoke không lấy từ final test.
6. Chạy baseline hoặc train bằng entry point **sẽ triển khai** ở milestone tương ứng. Lưu run_id, effective config, seed, manifest, output thô và log. Không có lệnh `python -m ...` chạy được ở M0.
7. Lưu định kỳ vào Drive: adapter/config, tokenizer/chat template, checksum, run config. Nếu cần resume train lưu thêm optimizer, scheduler, trainer step, RNG state và trạng thái sampler theo khả năng stack. Kiểm tra file đầy đủ và thử nạp trước xóa bản runtime. Không coi upload xong là đã xác minh.
8. Inference: nạp đúng base revision và adapter tương thích, tokenizer/template, generation config. **Resume training** cần checkpoint đầy đủ và stack tương thích; chỉ có adapter thì thường là warm start run mới, không phải tiếp tục chính xác optimizer/step. Ghi rõ giới hạn.

## Khi OOM hoặc mất phiên

OOM: ghi bước lỗi và cấu hình; giải phóng phiên lỗi, thử giảm sequence length theo phân bố token, micro-batch; dùng gradient accumulation để giữ effective batch nếu phù hợp, cân nhắc gradient checkpointing/packing chỉ sau xác minh mask. Không âm thầm cắt assistant mất kết truyện. Mỗi thay đổi tạo run config mới; không tuyên bố cấu hình bảo đảm vừa GPU khác.

Mất runtime: khôi phục commit, môi trường khóa, dataset manifest/hash; kiểm tra checkpoint cuối đầy đủ. Nếu chỉ có adapter, chạy inference hoặc khởi tạo run mới và ghi mất trạng thái resume. Không ghi đè checkpoint tốt bằng file dang dở; đề xuất ghi thư mục tạm, kiểm tra rồi đánh dấu complete.

[FAQ Colab chính thức](https://research.google.com/colaboratory/faq.html) mô tả tài nguyên/giới hạn thay đổi và không được bảo đảm. Không hứa loại GPU hay thời lượng cố định cho Colab Free. Quy trình này phải được cập nhật bằng lệnh thực đã chạy ở M3.
