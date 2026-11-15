# Bàn giao công cụ M2 — 2026-11-14

## Cập nhật trạng thái — 2026-11-15

Người dùng xác nhận đã xin và được phép sử dụng, đồng thời yêu cầu ghi `training_use=confirmed` cho phạm vi đồ án học tập/thi cử phi thương mại. Ledger và SOURCE_AUDIT đã được cập nhật theo xác nhận đó. Tài liệu cấp phép, danh tính bên cấp phép và chi tiết phạm vi chưa có trong repo hoặc được kiểm chứng độc lập.

### Cập nhật artifact và kiểm tra — 2026-11-15

- `outputs/m2_batch_approved_import_v3/reviewed_records.jsonl`: 100/100 mẫu `approved`; kiểm tra `validate_approval` không có lỗi; 12 cờ `possible_truncation_review` đều có `flags_resolved=true`; 100 source group riêng, 0 exact duplicate. Đây là batch được người dùng duyệt trước đó, không phải batch 30 đã chỉnh sau này.
- Near screening CPU trên đủ 100 mẫu: Jaccard n-gram 3, ngưỡng 0.65, 0 cặp và 0 nhóm ứng viên. Đây không phải bằng chứng rằng dataset lớn sạch gần trùng; chưa có cặp dương để hiệu chuẩn trên dữ liệu thật.
- SFT CPU nguồn thực đã xuất tại `outputs/m2_reviewed_sft_100_v1/`: 90 train, 10 validation, seed 42, tỷ lệ yêu cầu 0.1. Kiểm tra schema 100 dòng đạt; source ID và source group không giao giữa hai tập; assistant khớp text đã duyệt; user prompt không chứa target; hash `COMPLETE.json` hợp lệ. Chưa kiểm tra tokenizer/model tokens, chat template của model, EOS hoặc loss masking; chưa train model.
- Batch chỉnh sửa 30 mẫu riêng: `outputs/m2_user_approved_import_01/` có 24 approved và 6 pending vì chưa có bài học được nội dung hỗ trợ. Không ghép batch này với batch 100 trong SFT.
- `python -m unittest discover -s tests -v`: 22 tests đạt. Các lệnh `near` và `sft` được chạy trên CPU.
- Phiếu gốc `data/review/rubric_feedback.csv` vẫn pending; có bản góp ý AI tách riêng `data/review/rubric_ai_review_draft.csv`, chưa được xem là quyết định người chấm.
- Bộ dev có 20 đề và golden draft có 50 đề. Không mở golden draft trong lượt này; chưa có người độc lập duyệt/niêm phong final holdout, chưa có `golden_test_v1`.

**M2 vẫn chưa hoàn tất** vì rubric chưa được người duyệt phản hồi, final holdout chưa được người độc lập duyệt/niêm phong, và căn cứ cấp phép chi tiết chưa có trong repo. Batch 100 và SFT là artifact M2 có điều kiện, không phải bằng chứng chất lượng mô hình hay đủ dữ liệu cho pilot 300–500 mẫu ở M4.

## Trạng thái

Đã thực hiện phần công cụ độc lập của M2. Một batch 100 mẫu đã được người dùng duyệt và có SFT CPU 90/10; batch chỉnh sửa 30 mẫu riêng có 24 approved/6 pending. **M2 chưa hoàn tất**: rubric còn pending, final holdout chưa được người độc lập duyệt/niêm phong, và tài liệu quyền nguồn chi tiết chưa được kiểm chứng độc lập. Ledger ghi `confirmed` theo xác nhận người dùng. Chưa train GPU, chưa notebook/demo hoặc push. Python 3.12.10/Windows, chỉ thư viện chuẩn. Workspace có Git cục bộ; nhiều file dự án vẫn chưa được theo dõi. Hướng dẫn cụ thể ở M2_REVIEW_GUIDE, rà nguồn ở SOURCE_AUDIT.

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

`outputs/m2_survey30/` là lần khảo sát trước khi bổ sung baseline so sánh no-op và hash mã nguồn; bản `m2_survey30_review` là bàn giao hiện tại. Giữ nguyên các artifact chạy thử để không ghi đè. Mọi đường dẫn raw/outputs được Git ignore; ledger/docs/fixture/code nhỏ có thể quản lý phiên bản sau khi người dùng khởi tạo Git.

## Kiểm tra logic và giới hạn

22 tests gồm 12 regression M1 và 10 tests M2: phát hiện cặp gần trùng bằng fixture, phân biệt pending/distinct/confirmed, cap/ngưỡng; roundtrip/lịch sử/approval hash; thay revision/flags/ID làm review cũ hết hiệu lực; chặn metadata thiếu/flags chưa xử lý/người duyệt thiếu; text edit phải pending và review lại; seed lấy mẫu/tái lập/đảo input; no-op không bịa lịch sử; schema messages/prompt; cạnh confirmed giữ cùng split; chặn chưa duyệt/quyền unresolved và không cho nguồn thực dùng chế độ synthetic. Các reviewer/nhãn “synthetic-test…” trong tests chỉ là dữ liệu minh họa, không phải người đã duyệt nguồn thực.

Exporter tính lineage trên toàn bộ candidate, bao gồm duplicate và thành viên pending/rejected, rồi mới chọn approved và dedup/chia lại. Metadata/provenance/text/flags gắn approval hash; thay đổi sau duyệt bị chặn. Manifest SFT lưu hash review/rights/near/prompts/mã nguồn, lineage và source IDs riêng, không đưa thông tin người duyệt vào messages. Chỉ bài học/chủ đề/nhân vật được duyệt dùng làm user input, không tự rút tình tiết đáp án. Kiểm tra không lộ đáp án vẫn cần người đọc. Các trạng thái human là khai báo cục bộ, không phải hệ thống xác thực người ký.

Chưa chạy exporter trên dữ liệu thực được duyệt do không có approval và quyền chưa rõ. Exporter synthetic đã được kiểm tra trong thư mục test tạm rồi tự dọn; không có bộ SFT nguồn thực được phát hành. Chat template/tokenization/EOS/loss masking vẫn chưa kiểm tra bằng tokenizer model. Chưa có human scores, benchmark mô hình hay kết luận cải thiện.

## Việc chờ người dùng

Đọc SOURCE_AUDIT và xác nhận cách giải quyết nguồn/quyền với người hướng dẫn; chưa chỉ đổi ledger để qua cổng. Điền bản sao metadata_review.csv theo M2_REVIEW_GUIDE, trước mắt có thể duyệt một số mẫu rồi phản hồi lỗi. Hiệu chỉnh phương pháp near trên cặp người đọc; phiếu rubric còn pending. Final holdout chưa được người độc lập duyệt/giữ kín. M3 chưa bắt đầu cho đến khi các cổng dữ liệu/đánh giá phù hợp được chốt.

30 mẫu hiện tại chỉ khảo sát chất lượng và quy trình duyệt, chưa phải tập đủ cho pilot 300–500 mẫu ở M4. Việc mở rộng phạm vi lấy mẫu phải ghi phương pháp, ngân sách tải, quyền nguồn và ngân sách người duyệt trước khi thực hiện.

Kiểm tra bàn giao cuối: hash raw snapshot, survey/review roundtrip và mã nguồn khớp manifest; artifact/mã nguồn M1 gốc không đổi; bảng 30 mẫu vẫn pending và thiếu nhãn chưa tự điền; UTF-8/link cục bộ hợp lệ; hai tập đánh giá vẫn 20/50 pending, không có golden_test_v1 hoặc thư mục SFT thực bị chặn.

## Cập nhật vòng review v2 sau góp ý về tên nhân vật

Bảng ban đầu chỉ hiện truyện tiếng Việt; cột en nằm trong dữ liệu gốc nhưng không được đưa vào phiếu. Tạo `outputs/m2_survey30_names_v2/` mới, giữ nguyên `outputs/m2_survey30_review/`. Exporter thêm source_text_en (chỉ đọc), source_character_names_en, character_name_notes và character_names_reviewed; cột characters ghi tên dùng trong prompt Việt. Tất cả nhãn/quyết định vẫn trống hoặc false/pending; không tự dịch tên. Importer yêu cầu xác nhận đã rà tên trước khi approved và approval hash bao gồm các trường mới.

README và M2_REVIEW_GUIDE đã chuyển bảng chính sang v2. Baseline cũ không dùng cho bảng v2. Sau khi cập nhật, `python -m unittest discover -s tests -q` đạt 22 tests. Đã kiểm tra bảng v2 có đủ cột Anh/Việt, 30 dòng pending và hash artifact hợp lệ. Không xuất SFT.

Sau yêu cầu thử công cụ gợi ý: thêm `names.py`, chạy khi tạo review sheet. Mẫu mới `outputs/m2_survey30_names_tool_v3/` trích ứng viên theo các mẫu từ/cụm như `named X`, `I am X`, lời chào, và từ viết hoa lặp lại; bảng lưu cả tên ứng viên, danh sách gợi ý Việt hóa dạng JSON và quy tắc đã dùng. Các ví dụ Sue→Xuân, Tom→Tâm, Jerry→Gia Huy, Amy→Trà My, Lily→Ly chỉ là ánh xạ minh họa theo câu hỏi của người dùng; được ghi nguồn `illustrative_user_mapping`, chỉ đề xuất và không ghi đè `characters` hay truyện. Tên khác được gợi ý giữ nguyên. Heuristic có thể bỏ sót hoặc nhặt nhầm tên; người duyệt sửa. Toàn bộ trạng thái v3 vẫn pending. Đã chạy lại 22 tests, đạt.
