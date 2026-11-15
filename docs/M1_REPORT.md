# Bàn giao M1 — 2026-11-14

## Hiện trạng và phạm vi

Môi trường thực: Windows/PowerShell, Python 3.12.10. `git status --short` báo thư mục không phải Git repository; chưa có commit, không khởi tạo Git/push. Không cài thư viện, GPU stack hoặc tải weights. Đã thực hiện đường dữ liệu CPU và khảo sát nguồn nhỏ; chưa xuất SFT. Tất cả nhãn/review còn null/pending.

Đọc AGENTS, ROADMAP, nhiệm vụ M1, DATA_PLAN, EVALUATION_PLAN, README và SYSTEM_DESIGN trước khi sửa. Giữ prompt và hai bộ đề đánh giá, không dùng chúng làm fixture hay nguồn chọn bộ lọc.

## Mã nguồn và hợp đồng

| File | Vai trò |
|---|---|
| `src/kids_story/data/io.py` | UTF-8 strict, JSONL strict (không NaN/khóa JSON lặp), giữ raw line; ghi artifact/hash |
| `process.py` | Schema, NFC/khoảng trắng, giữ original_record/original_text, flags/edit_reasons |
| `split.py` | Hợp nhất bắc cầu nhóm nguồn + exact hash, đại diện và split có seed |
| `pipeline.py`, `__main__.py` | API `run_pipeline` và CLI offline; báo cáo, manifest, marker hoàn tất |
| `source.py` | CLI tải prefix nhỏ riêng biệt, kiểm tra revision/schema và lưu bằng chứng |
| `tests/test_data.py`, `tests/fixtures/` | Kiểm tra offline và dữ liệu hoàn toàn tổng hợp |

Input JSONL mỗi dòng là object. Bắt buộc `source_id` và `source_group_id` là chuỗi không rỗng; `text` là chuỗi (tùy chọn tên bằng `--text-field`). Các trường provenance bổ sung được giữ nguyên trong original_record; source_revision/source_split/source_row_id cũng được đưa ra trường riêng. ID nguồn phải ổn định. Không tự đoán schema hoặc gán nhóm độc lập khi thiếu nhóm: cách ly. ID trùng khiến toàn run thất bại để tránh chọn ngẫu nhiên một bản.

Mỗi dòng có audit_id, input_line và raw_line. JSON hỏng, dòng trắng, giá trị không phải object, thiếu/sai kiểu/rỗng text và ID/nhóm không hợp lệ được ghi quarantine. UTF-8 lỗi là lỗi toàn file. Metadata topic/characters/lesson/label_source/reviewer vẫn null, review_status=pending; dữ liệu đầu vào được giữ trong original_record nhưng không tự coi nhãn nguồn là đã duyệt.

NFC; CRLF/CR về LF; Unicode line/paragraph separator về xuống dòng; gọn khoảng trắng ngang, trim từng dòng, giữ tối đa một dòng trắng giữa đoạn. Không gộp mọi đoạn thành một dòng; không thay tên/đại từ, không xóa ngoại ngữ hoặc ký tự lạ để che lỗi. Ghi riêng lý do thay Unicode, line ending và whitespace. Cờ review: ngắn hơn ngưỡng cấu hình (mặc định 20 đơn vị cách trắng, không phải bộ lọc độ dài sản phẩm), thiếu dấu kết câu, ký tự control/format, lặp dòng, tỷ lệ n-gram 5 đơn vị lặp ít nhất 0.3. Đây là heuristic chưa hiệu chỉnh trên dữ liệu đại diện; không đánh giá ngữ nghĩa, đại từ, an toàn hay tiếng Việt tự nhiên.

## Khử trùng và chia nhóm

SHA-256 của processed_text dùng để khử trùng **chính xác**; giữ nguyên hoa/thường, dấu câu và đoạn. Không coi hai văn bản gần giống là trùng. Đại diện là source_id nhỏ nhất theo thứ tự chuỗi; `duplicate_source_ids` giữ mọi ID, processed/manifest giữ từng bản gốc và duplicate_of.

Hợp nhất nhóm nguồn và nhóm exact theo thành phần liên thông **trước khi loại đại diện/chia**. Một bản trùng có thể nối hai nhóm nguồn; toàn bộ thành phần phải đi cùng split. Sắp xếp thành phần theo hash danh sách member IDs đã sort, shuffle bằng `random.Random(seed)` rồi lấy số nhóm validation làm tròn gần nhất, chặn trong [1, số nhóm−1]. Tỷ lệ là theo **nhóm**, không bảo đảm tỷ lệ dòng; báo cả tỷ lệ dòng thực và nhóm lớn nhất. Ít hơn hai nhóm: exit 2, giữ processed/quarantine và report status=failed, không tạo train/validation hoặc COMPLETE.

Manifest logic giống nhau khi chạy lại cùng input/config/seed. Với bản ghi có source_id hợp lệ, thay thứ tự dòng đầu vào không đổi manifest; processed/raw_line/input_line và input file hash có thể khác. Dòng JSON lỗi/không có source_id dùng audit ID có số dòng nên đổi vị trí sẽ đổi audit manifest; split của truyện hợp lệ vẫn độc lập thứ tự. Tái lập giữa phiên bản Python chưa được khẳng định; report ghi Python và hash mã nguồn để truy vết.

## Đầu ra

- `processed.jsonl`: mọi dòng, original/provenance, lý do và trạng thái.
- `quarantine.jsonl`: dòng không đủ điều kiện cấu trúc.
- `train.jsonl`, `validation.jsonl`: ứng viên duy nhất chưa duyệt, không phải hội thoại SFT.
- `split_manifest.json`: từng ID/hash/nhóm/trạng thái/duplicate/split và thuật toán/config.
- `report.json`: counts, flags, độ dài codepoint và đơn vị cách trắng, hash input/artifact/mã nguồn, môi trường và giới hạn; model_tokens=null.
- `COMPLETE.json`: hash report, chỉ ghi cuối khi thành công. Nếu I/O lỗi có thể còn thư mục dang dở không có marker; không dùng nó như run hoàn tất. Không ghi đè thư mục đã tồn tại.

Pipeline hiện giữ dữ liệu trong RAM, phù hợp fixture/snapshot nhỏ ở M1; chưa benchmark cho toàn bộ nguồn nhiều triệu hàng. Paths/seed/tỷ lệ/tên trường/ngưỡng ngắn cấu hình qua CLI; không phụ thuộc CUDA/mạng khi xử lý cục bộ.

## Nguồn Hugging Face đã khảo sát

Dataset `nampdn-ai/tinystories-vietnamese`, revision **`eb37a7aa8cc44ad9841175163a460fed5c2c1b24`**, config `default`, split `train`. [Card tại revision](https://huggingface.co/datasets/nampdn-ai/tinystories-vietnamese/blob/eb37a7aa8cc44ad9841175163a460fed5c2c1b24/README.md) chỉ có metadata MIT/en/vi, chưa có mô tả chuỗi nguồn gốc hoặc phương pháp dịch. Không coi license label này là đã xác minh đầy đủ quyền sử dụng nguồn/bản dịch.

Ban đầu shell trong sandbox lỗi DNS. Sau khi thực hiện truy cập mạng được cấp, đọc được API Hub và card cố định. Một phép thăm dò đầu tiên đọc thiếu bytes của JSON đã lỗi parse, không tạo snapshot; CLI cuối dùng giới hạn 8 MiB và tải toàn bộ response nhỏ, kiểm tra kích thước trước parse.

Snapshot thực lưu ở `data/raw/hf_prefix10_m1/` (được ignore), thời điểm metadata `2026-11-14T14:43:53.534111+00:00` tức 21:43:53 Asia/Saigon. Phương pháp **prefix offset=0, limit=10, row_idx 0–9**, seed=null, không phải mẫu ngẫu nhiên/đại diện. API `/rows` trả header `x-revision` trùng commit trên; nếu thiếu/khác revision hoặc có truncated_cells, CLI từ chối. Đây là kiểm tra dữ liệu viewer hiện tại khớp revision, không giả định API `/rows` hỗ trợ truy hồi lịch sử khi nguồn đã thay đổi.

Features thực: `en`, `vi` đều `Value(dtype=large_string)`. Quan sát 10/10 giá trị mỗi cột là str. Ghi nguyên bản API/card/viewer response và sample.jsonl; source manifest lưu URL/revision, cách lấy mẫu, observed types và SHA-256. Source ID gồm dataset@revision:split:row_idx; source_group_id hash bản en chuẩn hóa để nhóm các bản gốc trùng chính xác, chưa xử lý bản nguồn gần trùng.

SHA-256 sample.jsonl: `4bfd90e728b2dda348e996bcbe2b2d548720e65bef723a3b68741aedcd68ada0`. Schema này chỉ xác minh cho revision và mẫu quan sát; không khẳng định không có null/sai kiểu trong toàn dataset. Snapshot chỉ dùng khảo sát, chưa được phê duyệt train hoặc phát hành lại.

## Kiểm tra thực tế

Lệnh chạy được ghi trong README. `python -m unittest discover -s tests -v`: **12 tests đạt** sau lần chỉnh cuối, chạy offline. Bao phủ Unicode composed/decomposed, giữ original/idempotence, rỗng/sai kiểu/JSON lỗi, khử trùng chính xác và giữ gần giống, hợp nhất bắc cầu, không giao nhóm/hash giữa split, seed và đảo thứ tự, split quá ít nhóm, không ghi đè/ID trùng, JSON strict/UTF-8, tên trường tùy chọn, hash artifact/CLI, revision mismatch/truncated viewer. Hai test source dùng mock; khảo sát HF thực được thực hiện riêng bằng CLI.

Lần test đầu lỗi quyền ghi OS TEMP trong sandbox Windows, chưa tới logic xử lý. Đã chuyển temp tests vào `outputs/test_tmp` trong workspace; temp tự dọn, thư mục outputs bị ignore. Không dùng quyền quản trị để chạy tests.

| Run CLI cuối | Input | Candidate duy nhất | Duplicate | Quarantine | Train / validation | Thành phần nhóm |
|---|---:|---:|---:|---:|---:|---:|
| `outputs/m1_fixture_verified` | 14 | 6 | 1 | 7 | 3 / 3 | 4 |
| `outputs/m1_hf_prefix10_verified` | 10 | 10 | 0 | 0 | 9 / 1 | 10 |

Fixture tỷ lệ yêu cầu 25% nhóm, thực tế 50% dòng validation do một nhóm liên thông lớn; đây là hành vi dự kiến, không ép tách nhóm để đạt tỷ lệ dòng. HF dùng tỷ lệ 10%; độ dài quan sát 142–243 đơn vị cách trắng, 630–1078 Unicode codepoints. Có **1 cờ possible_truncation_review**, không kết luận truyện thực sự bị cắt trước người đọc duyệt. Các snapshot/run trước đợt bổ sung report được giữ ở output khác; thư mục `_verified` là bản dùng bàn giao.

## Phần còn thiếu trước M2/M3

Chưa truy rõ nguồn bản dịch, quyền upstream và phương pháp tạo; chưa EDA đại diện hoặc người đọc chuyên môn; chưa rà gần trùng, gán/duyệt metadata, xuất SFT, tokenizer/token counts, đo hiệu năng dữ liệu lớn hoặc GPU. Chưa chạy baseline/fine-tune/demo. Bộ đánh giá M0 vẫn pending. Bước tiếp theo là M2 theo ROADMAP, với cổng quyền sử dụng và review dữ liệu được giải quyết trước training. Repo cục bộ cần được người dùng khởi tạo/quản lý Git trước khi có thể ghi commit và diff chính thức.
