# Sinh truyện ngắn thiếu nhi tiếng Việt

Đồ án NLP cho trẻ **6–8 tuổi**, nghiên cứu câu hỏi: fine-tuning bằng QLoRA có cải thiện chất lượng sinh truyện theo yêu cầu so với **cùng mô hình gốc + System Prompt được thiết kế tốt** hay không? Kết quả có thể tốt hơn, tương đương hoặc kém hơn; chưa có thực nghiệm.

Đầu vào: chủ đề, nhân vật, bài học, độ dài tùy chọn. Đầu ra: truyện tiếng Việt có mở đầu, diễn biến, kết thúc và bài học qua hành động. Mặc định đề xuất **150–250 đơn vị cách trắng**, không phải số từ đã phân đoạn tiếng Việt hoặc chuẩn sư phạm. Ràng buộc cụ thể của đề được ưu tiên.

## Hiện trạng M2 — có SFT CPU, còn cổng đánh giá chờ duyệt

Đã có pipeline M1 và công cụ M2 CPU. Batch 100 mẫu được duyệt đã xuất SFT tại `outputs/m2_reviewed_sft_100_v1/` (90 train/10 validation, seed 42); chưa train model. **M2 chưa hoàn tất** vì phiếu rubric còn pending, final holdout chưa được người độc lập duyệt/niêm phong và tài liệu quyền nguồn chưa được kiểm chứng độc lập trong repo. 20 đề dev và 50 golden draft vẫn là draft/pending; chưa có human-calibrated scores hoặc `golden_test_v1` được duyệt. M3 baseline đã chạy trên Colab; run chi tiết ở [nhật ký thí nghiệm](docs/EXPERIMENT_LOG.md). Xem [báo cáo M2](docs/M2_REPORT.md) và lịch sử [M1](docs/M1_REPORT.md).

**Bạn đọc tiếp:** [báo cáo M2](docs/M2_REPORT.md). Batch chỉnh sửa 30 mẫu mới có 24 approved và 6 pending tại `outputs/m2_user_approved_import_01/`; batch SFT 100 mẫu là artifact riêng. Ledger ghi quyền sử dụng `confirmed` theo xác nhận của người phụ trách; tài liệu và phạm vi cấp phép chưa được kiểm chứng độc lập trong repo ([rà nguồn](docs/SOURCE_AUDIT.md)).

## Đọc theo thứ tự

1. [PROJECT_BRIEF](docs/PROJECT_BRIEF.md): phạm vi và giả định.
2. [USE_CASE_MATRIX](docs/USE_CASE_MATRIX.md), [RUBRIC](docs/RUBRIC.md), [EVALUATION_PLAN](docs/EVALUATION_PLAN.md): hành vi và cách đánh giá.
3. [SYSTEM_DESIGN](docs/SYSTEM_DESIGN.md), [AI_DESIGN](docs/AI_DESIGN.md), [DATA_PLAN](docs/DATA_PLAN.md): thiết kế dự kiến.
4. [ROADMAP](docs/ROADMAP.md), [COLAB_RUNBOOK](docs/COLAB_RUNBOOK.md), [EXPERIMENT_LOG](docs/EXPERIMENT_LOG.md): thực hiện và ghi nhận.

## Cấu trúc hiện có

```text
README.md, AGENTS.md, .gitignore
docs/                  thiết kế/quy trình + báo cáo M1/M2, hướng dẫn review, audit nguồn
prompts/               system, user template, nhiệm vụ M1
data/evaluation/       dev_cases.jsonl, golden_test_draft.jsonl, REVIEW_GUIDE.md
src/kids_story/data/   M1 pipeline; M2 review, near, sft, m2 CLI
data/review/           rights_ledger.json (confirmed per user attestation), rubric_feedback.csv (pending), rubric_ai_review_draft.csv
tests/                 unittest và fixture tổng hợp
data/raw/              snapshot khảo sát HF (bị Git ignore)
outputs/               kết quả chạy và báo cáo (bị Git ignore)
```

Đã triển khai phần dữ liệu và xuất hội thoại SFT có điều kiện trong `src/kids_story/data/`. Fine-tune/QLoRA và `app/` Gradio **chưa triển khai**. M3 có module baseline Transformers và notebook Colab mỏng; baseline Qwen2.5-3B-Instruct đã sinh 20/20 đề dev trong một run Colab. Có bảng điểm AI hỗ trợ trên rubric nháp; chưa có metric chất lượng được hiệu chuẩn hoặc kết luận tổng quát. Không có module rỗng mô phỏng tiến độ.

## Chạy M1 trên CPU

Môi trường đã chạy: Windows PowerShell, Python 3.12.10, không cài dependencies, không GPU. Mã nguồn và tài liệu hiện được theo dõi trên Git; commit `ed7860c` đã push lên `origin/main` của repository riêng. Dữ liệu chạy trong `data/raw/` và `outputs/` vẫn bị Git ignore. [Nhiệm vụ M1 gốc](prompts/codex_next_task.md) được giữ để truy vết.

Các lệnh dưới đây **đã chạy thành công** từ thư mục dự án:

```powershell
$env:PYTHONPATH = (Resolve-Path src).Path
python -m unittest discover -s tests -v
python -m kids_story.data --input tests/fixtures/stories.jsonl --output-dir outputs/m1_fixture_verified --seed 42 --validation-ratio 0.25
python -m kids_story.data.source --revision eb37a7aa8cc44ad9841175163a460fed5c2c1b24 --limit 10 --output-dir data/raw/hf_prefix10_m1
python -m kids_story.data --input data/raw/hf_prefix10_m1/sample.jsonl --text-field vi --output-dir outputs/m1_hf_prefix10_verified --seed 42 --validation-ratio 0.1
```

Kết quả: **12 tests đạt**; fixture 14 dòng → 6 ứng viên duy nhất (3 train/3 validation), 1 duplicate, 7 quarantine; nguồn HF 10 dòng → 9 train/1 validation, 1 cờ cần rà soát. Mẫu HF là prefix 0–9, **không ngẫu nhiên**. Các đường dẫn đầu ra trên hiện đã tồn tại: khi chạy lại phải chọn thư mục mới vì CLI từ chối ghi đè. Lệnh `.source` cần mạng; xử lý cục bộ và tests không cần mạng.

Input cục bộ cần JSON object mỗi dòng với `source_id`, `source_group_id` là chuỗi không rỗng và trường văn bản (`text` mặc định, đổi bằng `--text-field`). Chọn `source_group_id` từ nguồn truyện chung, không tự gán mỗi bản sửa một nhóm mới. Dòng lỗi/rỗng được cách ly với raw line và lý do; ID trùng làm run thất bại. Các cờ heuristic chỉ dẫn đến review, không kết luận chất lượng/an toàn. Schema chi tiết, chính sách chia và đầu ra xem [M1_REPORT](docs/M1_REPORT.md).

Đọc `report.json`, `quarantine.jsonl` và `split_manifest.json` trong output. Chỉ coi run hoàn tất khi có `COMPLETE.json` và hash hợp lệ. `train.jsonl`/`validation.jsonl` ở M1 chưa có metadata được duyệt, **chưa được dùng train**. M1 chưa phát hiện gần trùng; M2 có sàng lọc ứng viên, chưa có xác nhận của người đọc.

## M2: các lệnh đã chạy

Các lệnh dưới đây đã chạy thành công bằng Python chuẩn (không cài thêm dependencies):

```powershell
$env:PYTHONPATH = (Resolve-Path src).Path
python -m unittest discover -s tests -v
python -m kids_story.data.source --revision eb37a7aa8cc44ad9841175163a460fed5c2c1b24 --limit 100 --output-dir data/raw/hf_prefix100_m2
python -m kids_story.data --input data/raw/hf_prefix100_m2/sample.jsonl --text-field vi --output-dir outputs/m2_prefix100_cpu --seed 42 --validation-ratio 0.1
python -m kids_story.data.m2 prepare --input outputs/m2_prefix100_cpu/processed.jsonl --output-dir outputs/m2_survey30_review --sample-size 30 --seed 42 --threshold 0.65 --ngram 3
python -m kids_story.data.m2 import-review --input outputs/m2_survey30_review/records.jsonl --csv outputs/m2_survey30_review/review/metadata_review.csv --baseline outputs/m2_survey30_review/review/review_baseline.json --output-dir outputs/m2_pending_roundtrip
python -m kids_story.data.m2 near --input outputs/m2_pending_roundtrip/reviewed_records.jsonl --output-dir outputs/m2_near_roundtrip --threshold 0.65 --ngram 3
```

Kết quả **22 tests đạt**; chọn 30/100 hàng với seed 42 (chỉ ngẫu nhiên trong prefix 100, không đại diện toàn nguồn), 1 cờ cần rà, 0 exact duplicate và 0 cặp vượt ngưỡng near đề xuất. Roundtrip bảng chưa sửa giữ 30 pending/0 approved. Các output-dir này đã tồn tại: chọn thư mục mới khi chạy lại, không ghi đè.

Đã chạy lệnh sau để kiểm tra cổng chặn, **exit 2 đúng kỳ vọng**, không tạo output SFT:

```powershell
python -m kids_story.data.m2 sft --input outputs/m2_pending_roundtrip/reviewed_records.jsonl --output-dir outputs/m2_real_sft_blocked --near-report outputs/m2_near_roundtrip/near_candidates.json --near-review outputs/m2_near_roundtrip/near_review.csv --rights data/review/rights_ledger.json
```

Exporter SFT đã chạy thành công trên batch 100 mẫu approved; kết quả và giới hạn ghi trong [M2_REPORT](docs/M2_REPORT.md). Near scan 100 mẫu cho 0 cặp ở 0.65/ngram 3; ngưỡng chưa hiệu chuẩn bằng cặp thật. Tiếp theo là người duyệt phản hồi rubric và người độc lập duyệt/niêm phong holdout. Quyền nguồn hiện dựa trên xác nhận người dùng; tài liệu và phạm vi chi tiết chưa được kiểm chứng độc lập. Cần hoàn tất các cổng M2 theo [ROADMAP](docs/ROADMAP.md) trước M3; Colab vẫn là dự kiến.

Các lệnh mới đã chạy thành công trên batch 100 mẫu:

```powershell
$env:PYTHONPATH = (Resolve-Path src).Path
python -m kids_story.data.m2 near --input outputs/m2_batch_approved_import_v3/reviewed_records.jsonl --output-dir outputs/m2_batch_approved_near_01 --threshold 0.65 --ngram 3
python -m kids_story.data.m2 sft --input outputs/m2_batch_approved_import_v3/reviewed_records.jsonl --output-dir outputs/m2_reviewed_sft_100_v1 --near-report outputs/m2_batch_approved_near_01/near_candidates.json --near-review outputs/m2_batch_approved_near_01/near_review.csv --rights data/review/rights_ledger.json --seed 42 --validation-ratio 0.1
```

Kết quả: 0 cặp gần trùng ứng viên; SFT có 90 train/10 validation. Kiểm tra bổ sung xác nhận schema 100 dòng, không giao source ID/nhóm giữa hai split và hash manifest hợp lệ. Đây là artifact nhỏ để bàn giao M2, chưa đủ 300–500 mẫu cho pilot M4.

Không dùng golden draft để chỉnh prompt. Người duyệt cần đọc [REVIEW_GUIDE](data/evaluation/REVIEW_GUIDE.md) trước khi mở tập test.

## EDA song ngữ quy mô lớn (CPU)

`python -m kids_story.data.source` hỗ trợ thêm `--method random_blocks` để lấy mẫu cụm có seed từ revision bất biến. Dataset Viewer chỉ trả tối đa 100 dòng mỗi request; sampler chọn các block 100 dòng rải trên split, kiểm tra header revision ở từng request và giới hạn tối đa 10.000 dòng. Đây là **cluster sample**, không phải IID random sample từng dòng; report phải được hiểu theo giới hạn đó. Không tải toàn bộ dataset. Lệnh dưới đây là cách chạy sau khi xác nhận revision/quyền sử dụng; chưa chạy lấy 10.000 dòng nguồn thật trong lần cập nhật mã này:

```powershell
$env:PYTHONPATH = (Resolve-Path src).Path
# Chạy thử quy trình với 1.000 mẫu trước
python -m kids_story.data.source --revision eb37a7aa8cc44ad9841175163a460fed5c2c1b24 --method random_blocks --limit 1000 --seed 42 --output-dir data/raw/hf_random_blocks1k
python -m kids_story.data.m2 eda --input data/raw/hf_random_blocks1k/sample.jsonl --source-manifest data/raw/hf_random_blocks1k/source_manifest.json --output-dir outputs/m2_eda_random_blocks1k_v1
# Khi quy trình ổn, đổi limit/output-dir thành 10000/m2_eda_random_blocks10k_v1
python -m kids_story.data.source --revision eb37a7aa8cc44ad9841175163a460fed5c2c1b24 --method random_blocks --limit 10000 --seed 42 --output-dir data/raw/hf_random_blocks10k
python -m kids_story.data.m2 eda --input data/raw/hf_random_blocks10k/sample.jsonl --source-manifest data/raw/hf_random_blocks10k/source_manifest.json --output-dir outputs/m2_eda_random_blocks10k_v1
```

EDA chỉ phân tích snapshot đã lấy và không sửa truyện. Tạo `eda_report.json`, `eda_manifest.json`, `name_candidates.csv`, `translation_candidates.csv` và `COMPLETE.json`. CSV gợi ý dùng UTF-8 BOM, mọi dòng có `review_status=pending`; heuristic tên/dịch sát không xác nhận nội dung. Khi đổi input hoặc revision, tạo thư mục output mới; CLI từ chối ghi đè. Có thể kiểm tra logic offline bằng fixture tổng hợp `tests/fixtures/eda_stories.jsonl`, không phải dữ liệu huấn luyện.

Muốn chạy toàn bộ luồng trên Colab, mở [notebook M2 EDA](notebooks/m2_eda_colab.ipynb). EDA dùng CPU; bước AI gợi ý mapping tên là tùy chọn, cần bật `ENABLE_AI_NAME_PROPOSALS=True` và chọn GPU. Bước AI dùng Qwen2.5-3B-Instruct tại revision M3 đã khóa, chỉ tạo `ai_name_mapping_candidates.csv` pending, không sửa truyện. Notebook clone `main`, lưu snapshot/report vào Google Drive; commit cần chạy phải được push lên GitHub trước khi clone. Mỗi run có `run.log`, `run_config.json`, `COMPLETE.json` và ba ảnh PNG về độ dài, thống kê dữ liệu, tần suất ứng viên. Notebook chưa được thực thi trên runtime Colab thật.

Kiểm tra offline đã chạy trong lần cập nhật này:

```powershell
$env:PYTHONPATH = (Resolve-Path src).Path
python -m unittest discover -s tests -v
python -m kids_story.data.m2 eda --input tests/fixtures/eda_stories.jsonl --output-dir outputs/m2_eda_fixture_smoke_final
```

Kết quả: **47 tests đạt**; lệnh CLI fixture đọc 4 dòng tổng hợp và xuất 3 dòng ứng viên tên cùng 3 dòng ứng viên dịch sát. Không lấy dữ liệu nguồn thật, không tạo SFT và không chạy GPU trong lần kiểm tra này.

## M3 baseline Colab — đã chạy baseline model gốc

Runner nằm ở `src/kids_story/baseline.py`; notebook là [notebooks/m3_baseline_colab.ipynb](notebooks/m3_baseline_colab.ipynb). Notebook dùng model `Qwen/Qwen2.5-3B-Instruct` tại revision cố định, dùng `data/evaluation/dev_cases.jsonl` cùng `prompts/story_system_v1.txt`, yêu cầu GPU CUDA và giữ PyTorch do Colab cung cấp. Repo hiện public và được clone trực tiếp từ nhánh `main`; không cần GitHub Secret hoặc token. Outputs mặc định ghi vào Google Drive và được kiểm tra hash. M3 không dùng Unsloth; Unsloth dự kiến cho M4 QLoRA.

Run `qwen25_3b_20261115T045801Z` trên Colab/Tesla T4 hoàn tất: 20/20 mẫu thành công, 0 lỗi, hashes được xác minh. Artifact ở `MyDrive/kids-story-runs/m3/qwen25_3b_20261115T045801Z`; model revision, runtime, cấu hình sinh và hashes được ghi trong [EXPERIMENT_LOG](docs/EXPERIMENT_LOG.md). Một mẫu (`DEV019`) dừng vì chạm `max_new_tokens=512`; trạng thái run vẫn `complete` vì không có lỗi thực thi. Kết quả chỉ là baseline trên tập dev, không phải fine-tune hay đánh giá chất lượng tổng quát. Bảng điểm AI hỗ trợ không thay thế human-calibrated scores; M2 vẫn còn các cổng review riêng.

Các lệnh kiểm tra cục bộ đã chạy trong PowerShell (không tải model, không dùng GPU):

```powershell
$env:PYTHONPATH = (Resolve-Path src).Path
python -m unittest discover -s tests -p test_baseline.py -v
python -m json.tool notebooks/m3_baseline_colab.ipynb
python -m unittest discover -s tests -v
```

Trước run thật, đã chạy trên Windows: **17 test baseline đạt**, JSON notebook hợp lệ, 6 code cells phân tích cú pháp Python được và **39 test toàn repo đạt**. Đây là kiểm tra logic cục bộ; run Colab thật ở trên xác nhận notebook và dependency hoạt động trong runtime T4 được ghi lại, nhưng không bảo đảm tương thích với runtime khác. Xem [runbook](docs/COLAB_RUNBOOK.md), [thiết kế mô hình](docs/AI_DESIGN.md) và [nhật ký thí nghiệm](docs/EXPERIMENT_LOG.md). M2 vẫn chờ các cổng đánh giá riêng; baseline dev không đóng các cổng đó.

## Kiểm tra bàn giao M0 — 2026-11-14

Đã chạy script ngắn bằng Python 3.12.10 (thư viện chuẩn, không cài thêm): đủ 19 file đọc UTF-8; JSONL parse được; 20 dev và 50 test đúng phân bố; ID tuần tự/duy nhất; schema, kiểu dữ liệu và tham chiếu use case/rubric hợp lệ; tất cả pending với notes rỗng; không có placeholder hoặc prompt trùng chính xác; link Markdown cục bộ tồn tại. Kiểm tra lại sau khi sửa đề TEST038 đã đạt.

Sàng lọc gần trùng bằng SequenceMatcher trên chủ đề/bài học/chỉ dẫn bổ sung sau khi bỏ phần template chung: không có cặp đạt ngưỡng khảo sát 0.75. Ngưỡng này chỉ phục vụ rà soát, không chứng minh khác biệt ngữ nghĩa. Rà nội dung của người soạn không thấy cặp gần trùng rõ ràng; đã đối chiếu tuổi 6–8, mặc định 150–250 đơn vị cách trắng, tên file và phạm vi M0. Toàn bộ đề vẫn cần người duyệt chuyên môn. Chưa chạy model, baseline, fine-tune hoặc kiểm nghiệm GPU.
