# Chỉnh sửa mẫu truyện M2 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use the qskill-executing-plans skill to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.
> This plan is intentionally written as behaviour only: it specifies files, units, rules, outcomes and test cases, NOT implementation code and NOT signatures. Read the real files before writing each task's code.

**Goal:** Tạo một vòng review mới cho 30 truyện mẫu M2 sau khi sửa các lỗi dịch, tên và tình tiết chưa phù hợp.

**Architecture:** Giữ nguyên bảng v3 và dữ liệu nguồn. Thực hiện đề xuất sửa trên một bản sao CSV, nhập qua quy trình review hiện có để lưu lịch sử, tính lại hash/cờ, rồi xuất một phiếu mới cho người dùng duyệt.

**Tech Stack:** Python CPU hiện có, CSV UTF-8 BOM, công cụ review M2.

**Spec:** none (bounded task) — yêu cầu người dùng “chỉnh hết” các vấn đề vừa được rà soát; giữ mọi quyết định là đề xuất chờ người dùng.

**Plan slug:** `2026-11-15-review-30-story-sample` — mọi commit cho kế hoạch này bắt đầu bằng `[2026-11-15-review-30-story-sample]`.

## Global Constraints

- Chỉ thực hiện công việc review dữ liệu M2; không train, không demo, không mở rộng dataset.
- Giữ nguyên `source_id`, `source_revision`, `source_group_id`, `source_text_en`, `original_text`, `flags` và `record_hash` trong bảng đầu vào.
- Giữ bản gốc `outputs/m2_survey30_names_tool_v3/review/metadata_review.csv` không đổi.
- Mọi text và metadata do AI đề xuất phải ghi rõ là đề xuất; tất cả mẫu giữ `review_status=pending`.
- `text_approved`, `flags_resolved`, `prompt_metadata_approved`, `character_names_reviewed` giữ false; `reviewer` và `reviewed_at` để trống.
- Dùng mapping đã nêu trong lịch sử dự án, gồm `Sue → Xuân`, `Tom → Tâm`, `Tim → Tín`, `Amy → Trà My`, `Lily → Ly`; tên khác giữ nguyên nếu không có quyết định đã xác nhận.
- Không tự kết luận bài học nếu truyện không hỗ trợ; để đề xuất bài học ở trạng thái cần người dùng xác nhận.

---

## File và trách nhiệm

| Đường dẫn | Trách nhiệm |
|---|---|
| `outputs/m2_survey30_names_tool_v3/review/metadata_review.csv` | Bảng gốc chỉ đọc, làm mốc so sánh. |
| `outputs/m2_survey30_names_tool_v3/review/metadata_review.filled.csv` | Bản làm việc chứa text sửa và metadata đề xuất, vẫn pending. |
| `outputs/m2_ai_review_import_01/reviewed_records.jsonl` | Lịch sử nhập các thay đổi, provenance được giữ nguyên, hash/cờ được tính lại. |
| `outputs/m2_ai_revised_30/review/metadata_review.csv` | Phiếu mới để người dùng rà lại text sau chỉnh sửa. |
| `outputs/m2_ai_near_01/near_candidates.json` | Kết quả sàng lọc gần trùng chạy lại sau khi text đổi. |

## Tasks

### Task 1 — Tạo đề xuất chỉnh sửa cho 30 mẫu

**Files:** bản sao `metadata_review.filled.csv`; không sửa bảng gốc.

- [x] Sửa lỗi dịch/ngữ pháp đã ghi nhận ở từng dòng, gồm sai nghĩa, nhầm nhân vật/loài vật, đại từ, dấu câu và cách gọi vật dụng.
- [x] Viết lại các tình tiết có nguy cơ cho trẻ ở các dòng 6, 14, 20, 28, 29 và 30 theo hướng an toàn, giữ mục đích truyện khi có thể; nếu không thể giữ nghĩa nguồn mà không bịa thêm tình tiết, ghi đề xuất là cần người dùng quyết định.
- [x] Giữ nhất quán cách Việt hóa tên theo mapping đã xác nhận; kiểm tra từng lần xuất hiện trong `processed_text`, `characters` và `character_name_notes`.
- [x] Điền `topic`, `characters`, `lesson` như nhãn đề xuất; `label_source` ghi nguồn AI đang chờ người dùng rà. Nếu không có bài học được nội dung hỗ trợ, ghi rõ chưa đề xuất thay vì tự tạo bài học.
- [x] Ghi `review_notes` cho từng dòng nêu sửa đổi và vấn đề còn cần người dùng xác nhận; mọi trường duyệt của con người vẫn giữ pending/false/trống.
- [x] Kiểm tra bảng làm việc có đủ 30 source ID duy nhất, đúng header, đúng thứ tự cột và không đổi cột chỉ đọc.

**Cases:**

- Khi một lỗi chỉ là diễn đạt tiếng Việt, bản mới giữ nguyên sự kiện nguồn và sửa câu tự nhiên hơn.
- Khi bản nguồn có mâu thuẫn hoặc kết thúc không phù hợp, bản mới ghi rõ phương án đề xuất và không giả vờ là bản dịch nguyên văn.
- Khi mapping tên chưa có quyết định trong lịch sử, tên được giữ nguyên và ghi chờ duyệt.
- Khi sửa text, mọi xác nhận duyệt vẫn false và trạng thái vẫn pending.

**Kết quả:** Tạo `metadata_review.filled.csv` với 30 ID duy nhất; cả 30 text được chỉnh; cột nguồn/provenance giữ nguyên; trạng thái pending và mọi xác nhận false.

### Task 2 — Nhập có lịch sử và xuất phiếu review mới

**Files:** đầu vào review v3 hiện có; output mới `outputs/m2_ai_review_import_01/`; phiếu mới `outputs/m2_ai_revised_30/`.

- [x] Nhập bản CSV đề xuất bằng baseline v3 và lưu vào thư mục output mới, không ghi đè artifact cũ.
- [x] Xác nhận importer giữ `original_text`, ghi lịch sử trước/sau, tính lại `exact_hash` và flags cho text đã sửa.
- [x] Chạy sàng lọc near lại trên các bản ghi đã nhập vào thư mục `outputs/m2_ai_near_01/`, không dùng near report cũ sau khi text thay đổi.
- [x] Xuất phiếu review mới từ records đã nhập; người dùng phải đọc lại mọi text/nhãn và tự xác nhận trạng thái cuối.
- [x] Kiểm tra 30 mẫu vẫn pending, không có human approval hoặc reviewer giả, và provenance không đổi.

**Cases:**

- Khi một text đã sửa bị cờ mới, phiếu mới giữ cờ đó và không đánh dấu đã xử lý.
- Khi source ID, revision, hash hoặc cột chỉ đọc không khớp baseline, quy trình dừng và giữ nguyên artifact cũ.
- Khi có cặp gần trùng sau chỉnh sửa, cặp được xuất thành ứng viên pending, không tự gộp.

**Kết quả thực tế:**

- `python -m kids_story.data.m2 import-review --input outputs/m2_survey30_names_tool_v3/records.jsonl --csv outputs/m2_survey30_names_tool_v3/review/metadata_review.filled.csv --baseline outputs/m2_survey30_names_tool_v3/review/review_baseline.json --output-dir outputs/m2_ai_review_import_01` → 30 dòng nhập, 0 approved.
- `python -m kids_story.data.m2 near --input outputs/m2_ai_review_import_01/reviewed_records.jsonl --output-dir outputs/m2_ai_near_01 --threshold 0.65 --ngram 3` → 0 cặp, 0 nhóm ứng viên. Đây chỉ là kết quả sàng lọc của 30 mẫu này, không phải chứng nhận không có gần trùng.
- `python -m kids_story.data.m2 export-review --input outputs/m2_ai_review_import_01/reviewed_records.jsonl --output-dir outputs/m2_ai_revised_30/review` → xuất 30 dòng.
- Kiểm tra Python: 30 ID duy nhất; 30/30 còn pending; 0 xác nhận người duyệt; lịch sử sửa có ở 30/30; source ID/revision/source text/original text giữ nguyên; hash bảng gốc và manifest mới khớp.
- Cờ sau tái xử lý: không còn cờ cấu trúc ở 30 dòng; `flags_resolved` vẫn false để người duyệt tự rà nội dung.
- Không chạy bộ test; chỉ chạy ba lệnh CLI của quy trình dữ liệu và kiểm tra nhất quán artifact ở trên.

## Verification

- `python -m kids_story.data.m2 import-review ...` nhận bản CSV pending và tạo lịch sử sửa; lệnh từ chối ghi đè thư mục output đã tồn tại.
- `python -m kids_story.data.m2 near ...` tạo report mới cho nội dung đã chỉnh.
- `python -m kids_story.data.m2 export-review ...` xuất đúng 30 ID, mọi mẫu pending và mọi xác nhận vẫn false.
- Dữ liệu đầu ra là CSV UTF-8 BOM đọc được bằng `csv.DictReader`; cột chỉ đọc và source IDs giữ nguyên.
- Không chạy train, không xuất SFT nguồn thực và không ghi kết quả duyệt thay người dùng.

## Commit

- Kế hoạch được commit trước khi thực hiện theo quy ước commit trong skill.
- Sau khi người dùng duyệt kế hoạch, thực hiện từng task; mọi commit có subject bắt đầu bằng `[2026-11-15-review-30-story-sample]` và nêu đường dẫn kế hoạch trong phần thân.
