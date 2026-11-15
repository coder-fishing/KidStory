# Mẫu nhật ký thí nghiệm

Chưa có run baseline hoặc QLoRA. Bảng dưới là **mẫu trống**, không phải kết quả. Sao chép cho mỗi run ở các milestone sau; giá trị chưa có để trống/null, không điền số minh họa như số thực.

## Trạng thái triển khai M3 — 2026-11-15

Runner CPU-testable, notebook Colab và dependency pins đã được thêm vào repo. **Chưa chạy trên Colab, chưa tải weights, chưa có generation output hay metric.** Không có run_id, GPU hoặc artifact để ghi ở bảng bên dưới. Phiên bản dependency pin hiện tại chưa được xác nhận bằng smoke test Colab. Sau lần chạy thật, ghi commit, dependency, GPU, model revision, hash prompt/input, output path, trạng thái `COMPLETE.json` và lỗi nếu có; giữ kết quả `completed_with_errors` tách khỏi baseline đầy đủ.

| Trường | Giá trị |
|---|---|
| run_id / loại run / mục đích | |
| Ngày giờ ISO 8601 + múi giờ | |
| Git commit / working tree clean hay dirty / diff hash | |
| Dataset ID / revision / snapshot hash | |
| Split manifest / hash / nhóm trùng / sample method | |
| Model ID / revision / tokenizer revision | |
| Prompt version / file hash / rendered messages hash | |
| Seed / seed list / deterministic options | |
| Dependencies lock / Python / driver / CUDA | |
| GPU / VRAM / tài nguyên khả dụng | |
| Training config / lượng tử hóa / LoRA / mask / context | |
| Generation config hiệu lực / stop / max_new_tokens | |
| Checkpoint được chọn / quy tắc validation / step | |
| Drive artifact path / checksum / trạng thái reload | |
| Resume đầy đủ hay adapter warm start | |
| Outputs thô / lỗi / attempts / finish reasons | |
| Metric / n áp dụng / N/A / khoảng bất định | |
| Nguồn chấm / scorer ID hoặc judge version / rubric hash | |
| Safety / over-refusal / bất đồng và phân xử | |
| Nhận xét / confound / giới hạn tái lập | |
| Thay đổi tiếp theo trên dev / người quyết định | |

Không mở khóa ánh xạ A/B cho người chấm trước khi hoàn tất phiếu. Không đưa thông tin cá nhân người chấm hoặc secrets vào Git. Run không thành công cũng cần ghi lỗi, config và artifact còn lại; không tự điền metric khi chưa đo.
