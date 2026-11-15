# Nhật ký thí nghiệm

## M3 baseline Colab — run đầu tiên hoàn tất

| Trường | Giá trị |
|---|---|
| run_id / loại run / mục đích | `qwen25_3b_20261115T045801Z` / baseline model gốc / sinh trên 20 đề dev |
| Thời điểm | `2026-11-15T04:58:01.234057+00:00` |
| Mã nguồn | commit `acaa150e9e5824c17a10e8fc652715894b81e295`; working tree lúc chạy sạch |
| Input | `data/evaluation/dev_cases.jsonl`; SHA-256 `a7285d2d32eaa590541085ac2681ecb681a36c3886acba69c9c76f8e0b8ad007` |
| Model / tokenizer | `Qwen/Qwen2.5-3B-Instruct`, revision `aa8e72537993ba99e69dfaafa59ed015b17504d1` |
| System prompt | `prompts/story_system_v1.txt`; SHA-256 `4d8ae94ba6ddb0d24dd687d44f298409eac82fd2a94969a6eda975dff26339a7` |
| Generation | seed 42; `do_sample=true`, temperature 0.7, top_p 0.9, repetition_penalty 1.0, max_new_tokens 512 |
| Runtime | Colab; Python 3.13.16, PyTorch 2.14.1+cu130, Transformers 4.57.3, Accelerate 1.12.0, CUDA 13.0, Tesla T4; `gpu_memory_bytes=15637086208` |
| Kết quả chạy | `complete`; 20/20 success, 0 lỗi; 19 kết thúc `stop`, `DEV019` kết thúc `length` ở 512 token |
| Artifact Drive | `/content/drive/MyDrive/kids-story-runs/m3/qwen25_3b_20261115T045801Z` |
| Hash artifact | `generations.jsonl`: `53f7231f4a00ed32e08628a3385b2333249bde6d73d5b219d708abc16bfa7204`; `run_config.json`: `8c89b123af82ec033825076c382dfce20db6dd586d283d7f2654730efc5f2ae2`; manifest báo hash verified |
| Đánh giá | Có bảng điểm R1–R5 do AI đề xuất trên rubric nháp và người dùng cho biết đã review. Bảng chi tiết nằm ngoài repo; không có metric tổng hợp hoặc đánh giá độc lập được lưu ở đây. |

Đây là baseline inference trên dev, **không phải fine-tune** và không xử lý dataset huấn luyện. Run xác nhận notebook hoạt động trong runtime Colab/T4 ghi trên; không bảo đảm runtime hoặc phiên bản tài nguyên Colab khác sẽ giống hệt. Cảnh báo thiếu `HF_TOKEN` là tùy chọn với model public; cảnh báo `torch_dtype` deprecated không làm run thất bại.

Không dùng run này làm bằng chứng chất lượng tổng quát. Lưu output nguyên bản; mọi chỉnh prompt/cấu hình dựa trên dev phải được ghi ở run riêng. Final holdout và các cổng M2 vẫn cần xử lý theo `docs/EVALUATION_PLAN.md`.

## Mẫu cho run tiếp theo

Khi ghi run mới, lưu run ID, thời gian, commit/working tree, input và prompt hashes, model/tokenizer revision, generation/training config hiệu lực, runtime/GPU, đường dẫn artifact và hashes, lỗi/finish reasons, cách chấm, giới hạn tái lập và quyết định tiếp theo. Không tự điền metric chưa đo; giữ `completed_with_errors` tách khỏi baseline đầy đủ.
