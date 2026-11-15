# Bạn duyệt dữ liệu M2 như thế nào?

## Trạng thái cập nhật — 2026-11-15

- Bảng `m2_survey30_names_tool_v3` là lịch sử khảo sát, vẫn pending.
- Phiếu 30 truyện đã chỉnh nằm ở `outputs/m2_ai_revised_30/review/metadata_review.csv`; bản xác nhận của reviewer `Bin` là `metadata_review.filled.csv`. Import hiện có 24 approved và 6 pending vì lesson chưa được nội dung hỗ trợ: source row IDs 19, 21, 34, 79, 9, 94. Không sửa approved text/metadata nếu chưa đưa qua vòng review mới.
- Batch 100 mẫu riêng có 100 approved trong `outputs/m2_batch_approved_import_v3/reviewed_records.jsonl`; SFT CPU tương ứng ở `outputs/m2_reviewed_sft_100_v1/`. Không trộn hai batch vì 30 truyện sau có text đã chỉnh riêng.
- Ledger quyền nguồn ghi `confirmed` theo xác nhận người dùng; tài liệu cấp phép và phạm vi chi tiết chưa được kiểm chứng độc lập trong repo.

## File cần mở trước

Mở **`outputs/m2_survey30_names_tool_v3/review/metadata_review.csv`** bằng trình đọc CSV UTF-8 (file có BOM để Excel nhận tiếng Việt). Đây là 30 mẫu chọn bằng seed 42 trong snapshot 100 hàng đầu, không phải mẫu đại diện toàn nguồn. Chưa mẫu nào được duyệt. Mỗi truyện có thể có xuống dòng trong một ô; đừng tách ô thủ công hoặc sửa header. Các bảng cũ được giữ nguyên làm lịch sử.

Lưu **bản sao** tên `metadata_review.filled.csv` trong cùng thư mục rồi điền bản sao. Giữ file gốc, `review_baseline.json`, records.jsonl và COMPLETE.json nguyên vẹn để truy vết. Không đưa file có tên người duyệt/dữ liệu truyện thật lên Git nếu chưa được phép; outputs/ được ignore.

## Các cột bạn điền

| Cột | Cách điền |
|---|---|
| source_text_en | Văn bản nguồn tiếng Anh để so sánh; chỉ đọc |
| source_character_names_en | Tên ứng viên tự trích từ truyện Anh; kiểm tra lại, sửa nếu sai hoặc ghi `Không có tên riêng` nếu xác nhận không có |
| character_name_suggestions_vi | Gợi ý tự động dạng JSON; chỉ tham khảo, không tự chép thành tên đã duyệt |
| character_name_suggestion_method | Quy tắc heuristic đã trích tên; dùng để biết mức hạn chế của gợi ý |
| topic | Chủ đề khái quát có thật trong truyện, không kể toàn bộ cốt truyện |
| characters | Tên/vai trò nhân vật đúng truyện, có thể ngăn bằng dấu chấm phẩy |
| character_name_notes | Tên nào giữ nguyên, Việt hóa hoặc không nhất quán; ghi `Giữ nguyên tên riêng` khi không đổi |
| character_names_reviewed | true sau khi đối chiếu tên trong truyện Anh và Việt; nếu chưa rõ thì false/pending |
| lesson | Bài học được hành động/hệ quả trong truyện hỗ trợ; không tự thêm nếu truyện không có cơ sở |
| label_source | Ví dụ human_manual; nếu sửa từ gợi ý AI thì ghi ai_draft_human_reviewed |
| review_status | pending: chưa chốt; approved: đã duyệt đủ; rejected: không dùng |
| review_notes | Lý do sửa/loại, lỗi đại từ, độ tuổi, bài học, cách xử lý từng flag |
| text_approved | true chỉ sau khi bạn thực sự đọc và xác nhận text phù hợp; còn lại false |
| flags_resolved | true khi các cờ đã được rà và xử lý/giải thích, kèm notes; còn lại false |
| prompt_metadata_approved | true sau khi kiểm tra nhãn đúng truyện và không lộ tình tiết đáp án trong prompt |
| reviewer | Tên hoặc mã người duyệt thật; không ghi AI thay người |
| reviewed_at | ISO 8601 có múi giờ, ví dụ định dạng YYYY-MM-DDTHH:MM:SS+07:00; điền thời điểm thật |

Nhãn trống nghĩa là thiếu, không tự biến thành đạt. Nếu không tìm được bài học phù hợp, giữ pending hoặc rejected. Approved cần đủ topic/characters/lesson/label_source, danh sách tên nguồn (hoặc xác nhận không có tên riêng), ghi chú cách xử lý tên, xác nhận character_names_reviewed/text_approved/prompt_metadata_approved, người duyệt và thời gian. Nếu có flags thì cần flags_resolved=true và notes. Một flag không tự đồng nghĩa dữ liệu hỏng; ví dụ possible_truncation_review có thể chỉ do thiếu dấu chấm.

Các cột `source_id`, `source_revision`, `source_group_id`, `source_text_en`, `original_text`, `flags`, `record_hash` **không sửa**. Hash giúp phát hiện bảng cũ hoặc thay đổi provenance; importer không tự tin một bảng duyệt nếu text/revision của đầu vào đã đổi. Không sửa JSONL/approval_hash trực tiếp để làm dữ liệu đạt.

## Nếu muốn sửa nội dung truyện

Sửa `processed_text`, ghi lý do, giữ review_status=pending. Import sẽ giữ original_text và lịch sử trước/sau, tính lại exact hash và cờ, hủy xác nhận text/prompt/flags. Không cho vừa sửa text vừa approved trong cùng lần import vì các cờ mới chưa được xem. Sau đó xuất bảng review mới từ reviewed_records.jsonl, đọc lại cờ/nội dung/nhãn và duyệt ở vòng tiếp theo. Sửa text cũng làm review gần trùng cũ hết hiệu lực, cần chạy near lại.

Importer cho phép nhập nhãn đề xuất còn pending nhưng không coi là human approval; chỉ bản đã được bạn xác nhận mới đủ điều kiện xuất SFT. Lịch sử sửa pending có thể chưa có tên người duyệt; quyết định approved/rejected bắt buộc có người/ngày. CSV và ledger là khai báo tin cậy cục bộ, không phải chữ ký số hay cơ chế xác thực danh tính.

## Lệnh tiếp nhận sau khi bạn điền — chưa chạy với bản duyệt thật

Các lệnh sau là hướng dẫn cho **lần chạy tương lai**; thư mục output phải mới:

```powershell
$env:PYTHONPATH = (Resolve-Path src).Path
python -m kids_story.data.m2 import-review --input outputs/m2_survey30_names_tool_v3/records.jsonl --csv outputs/m2_survey30_names_tool_v3/review/metadata_review.filled.csv --baseline outputs/m2_survey30_names_tool_v3/review/review_baseline.json --output-dir outputs/m2_human_import_01
```

Nếu có sửa text, vòng kế tiếp dùng `python -m kids_story.data.m2 export-review` với input là `outputs/m2_human_import_01/reviewed_records.jsonl` và một output-dir mới. Lấy CLI `--help` để xem tùy chọn. Không dùng bảng cũ duyệt tiếp dữ liệu đã thay đổi.

## Duyệt gần trùng và xuất SFT

`outputs/m2_survey30_review/near/near_review.csv` hiện chỉ có header vì không có cặp vượt ngưỡng 0.65 với n-gram 3. Điều này **không chứng minh sạch gần trùng**; ngưỡng là đề xuất chưa hiệu chỉnh bằng người đọc. Khi corpus thay đổi, chạy lại lệnh `near`. File near_candidates.json có nhóm ứng viên; tra truyện theo source_id trong bảng metadata.

Với mỗi cặp sau này: giữ nguyên ID/hash/score, điền decision=confirmed nếu cùng truyện/gần trùng nên ở cùng nhóm, distinct nếu thực sự khác; ghi reviewer/thời gian/notes. Pending chặn xuất SFT. Chỉ cạnh confirmed được hợp nhất với nhóm nguồn/exact; không tự gộp mọi ứng viên. Với chuỗi A–B–C, cả ba được giữ cùng nhóm nếu hai cạnh được xác nhận. Ngay cả một thành viên chưa duyệt hoặc bị loại vẫn được dùng nối lineage để ngăn rò nhóm.

Sau duyệt, xuất SFT cần ledger quyền sử dụng `confirmed` cho từng dataset/revision. Ledger hiện ghi `confirmed` theo xác nhận của người dùng; tài liệu cấp phép và chi tiết phạm vi chưa được đính kèm hoặc kiểm chứng độc lập trong repo. Exporter chỉ chọn mẫu approved, kiểm tra hash phê duyệt và metadata, khử trùng lại/chia nhóm trước khi tạo messages system/user/assistant. Độ dài user được đặt theo khoảng số đơn vị cách trắng của target ±20; đây là chính sách kỹ thuật đề xuất để không ghép target dài với mặc định sai, không phải chuẩn sư phạm. Metadata chỉ mô tả yêu cầu chung; người duyệt phải kiểm tra không tiết lộ cốt truyện/đáp án. System/user template không bị chỉnh trong M2.

## Đánh giá và holdout

Điền phản hồi từng chiều vào `data/review/rubric_feedback.csv`, đọc docs/RUBRIC.md và EVALUATION_PLAN.md. File này là phản hồi định nghĩa rubric, không phải điểm mô hình. Rubric vẫn là bản nháp cho đến khi hiệu chuẩn trên dev; S1 riêng, N/A cho từ chối/hỏi lại, theo dõi từ chối quá mức. Chưa có output mô hình để chấm.

Không mở golden draft để chọn bộ lọc, ngưỡng near, nhãn training hoặc prompt. M0 đã có phơi lộ draft khi soạn/kiểm tra; ghi việc này khi báo cáo. Nếu test từng được dùng để điều chỉnh hệ thống, phải công khai, loại khỏi holdout độc lập và nhờ người khác chuẩn bị bộ mới. Chưa xuất golden_test_v1 hoặc xác nhận final sealed ở M2 này; việc duyệt/giữ kín test do người phụ trách độc lập thực hiện theo data/evaluation/REVIEW_GUIDE.md.
