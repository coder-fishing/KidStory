# Bàn giao công cụ M2 — 2026-11-14

## Cập nhật trạng thái — 2026-11-15

Người dùng xác nhận đã xin và được phép sử dụng, đồng thời yêu cầu ghi `training_use=confirmed` cho phạm vi đồ án học tập/thi cử phi thương mại. Ledger và SOURCE_AUDIT ghi nhận đúng xác nhận đó. Tài liệu cấp phép, danh tính bên cấp phép và chi tiết phạm vi chưa có trong repo hoặc được kiểm chứng độc lập; trạng thái này không dựa riêng vào nhãn MIT trên Hub.

### Cập nhật artifact và kiểm tra — 2026-11-15

- `outputs/m2_batch_approved_import_v3/reviewed_records.jsonl`: 100/100 mẫu `approved`; kiểm tra `validate_approval` không có lỗi; 12 cờ `possible_truncation_review` đều có `flags_resolved=true`; 100 source group riêng, 0 exact duplicate. Đây là batch được người dùng duyệt trước đó, không phải batch 30 đã chỉnh sau này.
- Near screening CPU trên đủ 100 mẫu: Jaccard n-gram 3, ngưỡng 0.65, 0 cặp và 0 nhóm ứng viên. Đây không phải bằng chứng rằng dataset lớn sạch gần trùng; chưa có cặp dương để hiệu chuẩn trên dữ liệu thật.
- SFT CPU nguồn thực đã xuất tại `outputs/m2_reviewed_sft_100_v1/`: 90 train, 10 validation, seed 42, tỷ lệ yêu cầu 0.1. Kiểm tra schema 100 dòng đạt; source ID và source group không giao giữa hai tập; assistant khớp text đã duyệt; user prompt không chứa target; hash `COMPLETE.json` hợp lệ. Chưa kiểm tra tokenizer/model tokens, chat template của model, EOS hoặc loss masking; chưa train model.
- Batch chỉnh sửa 30 mẫu riêng: `outputs/m2_user_approved_import_01/` có 24 approved và 6 pending vì chưa có bài học được nội dung hỗ trợ. Không ghép batch này với batch 100 trong SFT.
- Kiểm tra cuối ngày 2026-11-15: `python -m unittest discover -s tests -v` đạt 22/22; `COMPLETE.json` khớp hash của cả ba artifact SFT, có 90 train/10 validation và schema messages system/user/assistant trên đủ 100 dòng. Các lệnh `near` và `sft` chạy trên CPU.
- Phiếu gốc `data/review/rubric_feedback.csv` vẫn pending; có bản góp ý AI tách riêng `data/review/rubric_ai_review_draft.csv`, chưa được xem là quyết định người chấm.
- Bộ dev có 20 đề và golden draft có 50 đề. Không mở golden draft trong lượt này; chưa có người độc lập duyệt/niêm phong final holdout, chưa có `golden_test_v1`.

**M2 vẫn chưa hoàn tất** vì rubric chưa được người duyệt phản hồi, final holdout chưa được người độc lập duyệt/niêm phong, và căn cứ cấp phép chi tiết chưa có trong repo. Batch 100 và SFT là artifact M2 có điều kiện, không phải bằng chứng chất lượng mô hình hay đủ dữ liệu cho pilot 300–500 mẫu ở M4.

## Trạng thái

Đã thực hiện phần công cụ độc lập của M2. Batch 100 mẫu đã được người dùng duyệt và có SFT CPU 90/10; batch chỉnh sửa 30 mẫu riêng có 24 approved/6 pending. **M2 chưa hoàn tất**: rubric còn pending và final holdout chưa được người độc lập duyệt/niêm phong; hồ sơ quyền nguồn chi tiết cũng chưa có trong repo. Ledger ghi `confirmed` theo xác nhận người dùng. Chưa train/inference model hoặc làm notebook/demo. Mã nguồn được commit `ed7860c` và push lên `origin/main`; artifact chạy trong `outputs/` bị Git ignore. Python 3.12.10/Windows, chỉ thư viện chuẩn. Hướng dẫn ở M2_REVIEW_GUIDE, rà nguồn ở SOURCE_AUDIT.

## File thay đổi

Thêm `src/kids_story/data/review.py`, `near.py`, `sft.py`, `m2.py`; tests/test_m2.py và fixture tổng hợp tests/fixtures/m2_stories.jsonl. Thêm ledger quyền nguồn unresolved và phiếu phản hồi rubric trong data/review/. Thêm báo cáo/hướng dẫn/audit này; cập nhật README, AGENTS, ROADMAP, DATA_PLAN, EVALUATION_PLAN. Giữ module/fixture M1, system/user prompt và nội dung hai tập đánh giá nguyên vẹn.

## Artifact và số liệu thật

1. Kiểm tra hiện trạng: 12 tests M1 đạt; SHA-256 mọi artifact đã liệt kê của hai run M1 verified khớp. Chưa sửa output M1. Sau thêm M2, bộ kiểm tra hiện có **22 tests đạt**.
2. `data/raw/hf_prefix100_m2/`: chỉ 100 hàng đầu, default/train, revision `eb37a7aa8cc44ad9841175163a460fed5c2c1b24`, x-revision khớp; en/vi large_string và quan sát 100/100 str mỗi cột. Không tải cả dataset. API/card/viewer/sample và hashes được lưu. Metadata nguồn TinyStories ứng viên cũng được lưu riêng, không tải dữ liệu gốc.
3. `outputs/m2_prefix100_cpu/`: 100 ứng viên, không quarantine/exact duplicate; 12 cờ possible_truncation_review. Độ dài 94–402 đơn vị cách trắng, 416–1740 codepoints. Split 90/10 của run này chỉ là **tạm ở M1 pipeline**, không phải final split sau review gần trùng.
4. `outputs/m2_survey30_review/`: chọn 30 không hoàn lại bằng random.Random(42) từ 100 bản ghi sắp theo audit/source ID; lưu IDs, hash input, revisions, code hashes và config. Có 1 cờ possible_truncation_review, không có rỗng/exact duplicate; độ dài 94–348 đơn vị cách trắng, median 161, 416–1522 codepoints. Chưa đo model tokens. Không suy tỷ lệ cờ của 30/100 ra toàn nguồn.
5. Jaccard trên tập n-gram 3 đơn vị chữ/số Unicode (casefold, bỏ phân cách dấu câu), ngưỡng 0.65: **0 cặp ứng viên** trong 30 mẫu. Toàn cặp so sánh trên CPU, mặc định chặn quá 500 bản ghi; ngưỡng/ngram cấu hình được, chưa hiệu chỉnh sensitivity/precision trên cặp được người duyệt xác nhận. Không phát hiện trùng ngữ nghĩa sâu, không tuyên bố sạch gần trùng. Nhóm ứng viên chỉ diagnostic, không dùng làm confirmed group.
6. Bảng metadata CSV UTF-8 BOM gồm 30 mẫu, topic/characters/lesson/label_source trống; review_status=pending, các xác nhận false, reviewer/ngày trống. Không tự gán nhãn để lấp trường. Near CSV chỉ có header do 0 cặp.
7. CLI import bảng chưa sửa vào `outputs/m2_pending_roundtrip/` thành công: 30 pending, 0 approved, không tự tạo lịch sử human review. Chạy near lại ở `outputs/m2_near_roundtrip/` vẫn 0 cặp. CLI SFT trên dữ liệu chưa duyệt exit **2**, thông báo No human-approved records; không tạo thư mục output SFT.

`outputs/m2_survey30/` là lần khảo sát trước khi bổ sung baseline so sánh no-op và hash mã nguồn; bản `m2_survey30_review` là bàn giao hiện tại. Giữ nguyên các artifact chạy thử để không ghi đè. Mọi đường dẫn raw/outputs được Git ignore. Mã nguồn, fixture tổng hợp, tài liệu và review form đã được quản lý phiên bản trong Git.

## Kiểm tra logic và giới hạn

22 tests gồm 12 regression M1 và 10 tests M2: phát hiện cặp gần trùng bằng fixture, phân biệt pending/distinct/confirmed, cap/ngưỡng; roundtrip/lịch sử/approval hash; thay revision/flags/ID làm review cũ hết hiệu lực; chặn metadata thiếu/flags chưa xử lý/người duyệt thiếu; text edit phải pending và review lại; seed lấy mẫu/tái lập/đảo input; no-op không bịa lịch sử; schema messages/prompt; cạnh confirmed giữ cùng split; chặn chưa duyệt/quyền unresolved và không cho nguồn thực dùng chế độ synthetic. Các reviewer/nhãn “synthetic-test…” trong tests chỉ là dữ liệu minh họa, không phải người đã duyệt nguồn thực.

Exporter tính lineage trên toàn bộ candidate, bao gồm duplicate và thành viên pending/rejected, rồi mới chọn approved và dedup/chia lại. Metadata/provenance/text/flags gắn approval hash; thay đổi sau duyệt bị chặn. Manifest SFT lưu hash review/rights/near/prompts/mã nguồn, lineage và source IDs riêng, không đưa thông tin người duyệt vào messages. Chỉ bài học/chủ đề/nhân vật được duyệt dùng làm user input, không tự rút tình tiết đáp án. Kiểm tra không lộ đáp án vẫn cần người đọc. Các trạng thái human là khai báo cục bộ, không phải hệ thống xác thực người ký.

Cập nhật kết quả sau ngày lập báo cáo ban đầu: exporter đã chạy trên batch 100 mẫu được duyệt và quyền sử dụng được ledger xác nhận theo lời người dùng; SFT 90/10 được lưu cục bộ trong `outputs/m2_reviewed_sft_100_v1/` và không commit. Các test exporter tổng hợp vẫn chỉ kiểm tra fixture. Chat template/tokenization/EOS/loss masking chưa được kiểm tra bằng tokenizer model; chưa train model, chưa có human scores, benchmark hoặc kết luận cải thiện.

## Việc chờ người dùng

Các việc còn cần con người để đóng M2: (1) người chấm phản hồi và chốt rubric trên dev qua `data/review/rubric_feedback.csv`; (2) người độc lập rà soát, ghi contamination, duyệt và giữ kín final holdout theo `data/evaluation/REVIEW_GUIDE.md`; (3) người phụ trách/hướng dẫn xác nhận hồ sơ quyền nguồn chi tiết có đủ cho phạm vi sử dụng dự kiến. Không tự đổi các trường pending thành approved. Batch 30 riêng có 24 approved/6 pending; không cần gộp vào SFT 100 đã xuất và không dùng sáu dòng pending. M3 bắt đầu sau khi các cổng áp dụng được giải quyết và báo cáo/roadmap cập nhật.

30 mẫu hiện tại chỉ khảo sát chất lượng và quy trình duyệt, chưa phải tập đủ cho pilot 300–500 mẫu ở M4. Việc mở rộng phạm vi lấy mẫu phải ghi phương pháp, ngân sách tải, quyền nguồn và ngân sách người duyệt trước khi thực hiện.

Kiểm tra bàn giao cuối: hash raw snapshot, survey/review roundtrip và mã nguồn khớp manifest; artifact/mã nguồn M1 gốc không đổi; bảng 30 mẫu vẫn pending và thiếu nhãn chưa tự điền; UTF-8/link cục bộ hợp lệ; hai tập đánh giá vẫn 20/50 pending, không có golden_test_v1 hoặc thư mục SFT thực bị chặn.

## Cập nhật vòng review v2 sau góp ý về tên nhân vật

Bảng ban đầu chỉ hiện truyện tiếng Việt; cột en nằm trong dữ liệu gốc nhưng không được đưa vào phiếu. Tạo `outputs/m2_survey30_names_v2/` mới, giữ nguyên `outputs/m2_survey30_review/`. Exporter thêm source_text_en (chỉ đọc), source_character_names_en, character_name_notes và character_names_reviewed; cột characters ghi tên dùng trong prompt Việt. Tất cả nhãn/quyết định vẫn trống hoặc false/pending; không tự dịch tên. Importer yêu cầu xác nhận đã rà tên trước khi approved và approval hash bao gồm các trường mới.

README và M2_REVIEW_GUIDE đã chuyển bảng chính sang v2. Baseline cũ không dùng cho bảng v2. Sau khi cập nhật, `python -m unittest discover -s tests -q` đạt 22 tests. Đã kiểm tra bảng v2 có đủ cột Anh/Việt, 30 dòng pending và hash artifact hợp lệ. Không xuất SFT.

Sau yêu cầu thử công cụ gợi ý: thêm `names.py`, chạy khi tạo review sheet. Mẫu mới `outputs/m2_survey30_names_tool_v3/` trích ứng viên theo các mẫu từ/cụm như `named X`, `I am X`, lời chào, và từ viết hoa lặp lại; bảng lưu cả tên ứng viên, danh sách gợi ý Việt hóa dạng JSON và quy tắc đã dùng. Các ví dụ Sue→Xuân, Tom→Tâm, Jerry→Gia Huy, Amy→Trà My, Lily→Ly chỉ là ánh xạ minh họa theo câu hỏi của người dùng; được ghi nguồn `illustrative_user_mapping`, chỉ đề xuất và không ghi đè `characters` hay truyện. Tên khác được gợi ý giữ nguyên. Heuristic có thể bỏ sót hoặc nhặt nhầm tên; người duyệt sửa. Toàn bộ trạng thái v3 vẫn pending. Đã chạy lại 22 tests, đạt.

## Cập nhật công cụ EDA song ngữ — 2026-11-15

Thêm sampler `random_blocks` có seed và giới hạn 100–10.000 hàng, lấy block 100 hàng qua Dataset Viewer, kiểm tra revision ở mọi request và ghi offset/hash/row IDs. Cách lấy là cluster sample, không phải IID row sample. Thêm `m2 eda` tạo report JSON cùng bảng CSV candidate cho tên và hai mẫu dịch sát song ngữ; bảng luôn pending, giữ context EN/VI, không ghi/sửa text. Mapping đã được người dùng xác nhận (Sue, Tom, Jerry, Amy, Lily, Tim, Buddy, Max) chỉ xuất hiện dưới dạng gợi ý để review từng truyện.

Đã chạy `python -m unittest discover -s tests -v`: **46/46 đạt**; chạy EDA CLI trên `tests/fixtures/eda_stories.jsonl`: 4 dòng fixture tổng hợp, 3 candidate tên, 3 candidate dịch sát, output hash manifest được tạo. Notebook Colab `notebooks/m2_eda_colab.ipynb` điều phối sampler/EDA, log, config và ba PNG vào Drive; notebook JSON và cú pháp 8 code cell đã được kiểm tra cục bộ, chưa chạy trên runtime Colab thật. Chưa lấy 1.000/10.000 hàng nguồn thật hoặc kiểm chứng chất lượng heuristic trên nguồn thật. M2 vẫn còn các cổng rubric, holdout và hồ sơ quyền nguồn nêu ở trên.
