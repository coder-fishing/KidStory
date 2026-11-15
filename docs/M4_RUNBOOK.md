# Chạy từ pool 10.000 ứng viên đến pilot M4

## Thứ tự trên Colab

1. `notebooks/m2_eda_colab.ipynb`: mặc định SAMPLE_SIZE=10000.
   EDA dùng CPU. AI tên là tùy chọn cần GPU; kết quả vẫn pending.
2. `notebooks/m2_review_colab.ipynb`: điền ROOT trỏ tới run EDA trong Drive.
   Chạy chuẩn hóa, xuất bảng sửa text, dừng để đọc và điền bảng.
3. Áp dụng bảng sửa. `before` phải xuất hiện đúng một lần trong text hiện tại;
   dùng cả câu nếu tên lặp nhiều lần. Nhiều sửa trong cùng truyện cần edit_id riêng.
   Không sửa ID/hash. Quyết định: pending/apply/keep/reject.
   Mỗi quyết định cần reviewer, reviewed_at có múi giờ và reason.
4. Duyệt metadata/text cuối theo M2_REVIEW_GUIDE. Mọi truyện sửa quay lại pending.
   Có thể sửa nhiều vòng; mỗi vòng dùng output-dir mới.
5. Chạy gần trùng trên bản cuối. Điền confirmed/distinct cho từng cặp,
   kèm lý do/người duyệt/thời điểm. Pending chặn SFT.
6. Xuất SFT. Exporter kế thừa cổng quyền nguồn, approval, metadata, nhóm nguồn,
   exact và near đã xác nhận. Không ghi đè artifact cũ.
7. `notebooks/m4_qlora_colab.ipynb`: chọn GPU, điền SFT_DIR; chạy preflight
   trước cài dependencies. 100 bước là smoke/pilot, chưa phải train hết pool.
8. Nạp adapter trong process mới, sinh dev. Dùng cùng rubric với baseline;
   con người đọc/chấm kết quả. Không dùng final test để chọn cấu hình.

Pool 10.000 chưa phải 10.000 train: loại mẫu, trùng và validation làm giảm số cuối.
M4 đòi ít nhất 300 mẫu đã duyệt cho pilot. Có thể dùng pool lớn hơn sau pilot,
nhưng sampler hiện giới hạn 10.000 mỗi lần. Không tự lấy bổ sung toàn bộ nguồn.

## Artifact M4

Để xuất bảng chấm dev A/B, dùng lệnh sau (hướng dẫn, chưa chạy trên output thật):

```text
python -m kids_story.compare_dev --base BASE_GENERATIONS.jsonl --tuned TUNED_GENERATIONS.jsonl --output-dir outputs/dev_blind_v1
```

Chỉ gửi dev_blind_review.csv cho người chấm; giữ PRIVATE_mapping_do_not_share.json
riêng. R1–R5/S1 để trống, review_status pending. Đọc rubric trước khi điền;
kiểm tra cùng đề/prompt/cấu hình sinh của hai run trước diễn giải điểm.

- run_config.json: model/revision, SFT hash, seed, GPU và phiên bản packages.
- token_label_audit.json: số token và nhãn ví dụ train/validation.
- checkpoints/: checkpoint Trainer có thể resume; không đưa vào Git.
- adapter/: adapter và tokenizer; adapter_hashes.json kiểm tra khi reload.
- training_log.json, TRAINED.json: validation loss và checkpoint tốt nhất.
- FAILED.json: lỗi training; không được coi là run hoàn tất.
- dev_reload/: outputs gốc, input messages, cấu hình sinh và hash.

Đặt resume_from_checkpoint trỏ tới checkpoint cũ và output_dir mới.
Code kiểm tra cùng snapshot/seed/độ dài/số bước; không tự chọn checkpoint.
Không hỗ trợ đổi cấu hình trong lúc resume.

## Giới hạn phải biết

Chưa chạy GPU/Unsloth trong lần triển khai này; chưa xác nhận tổ hợp dependency
trên Colab. Notebook cài bản hiện có và lưu pip freeze, chưa phải lock đã kiểm chứng.
Sau smoke thật, cần khóa đúng phiên bản đã chạy trước thí nghiệm so sánh.
Training từ chối mẫu vượt max_length thay vì âm thầm cắt target.
Gần trùng inverted Jaccard cho cùng kết quả exhaustive ở ngưỡng dương;
chi phí vẫn có thể cao khi rất nhiều truyện chung n-gram. Không chứng nhận trùng ngữ nghĩa.
Phản hồi rubric, quyền nguồn và holdout độc lập vẫn cần bằng chứng người duyệt.
Không coi loss giảm là bằng chứng chất lượng truyện tốt hơn.

## Kiểm tra cục bộ đã chạy

`python -m unittest discover -s tests`: 54 tests đạt, gồm fixture 10.000 bản ghi
tổng hợp với n-gram riêng biệt. Đây không phải benchmark nguồn thực hay GPU.
Test vòng sửa xác nhận giữ original, reset approval và chặn review lỗi thời;
test tokenizer giả lập kiểm tra mask/truncation; test SFT chặn hash và rò nhóm.
