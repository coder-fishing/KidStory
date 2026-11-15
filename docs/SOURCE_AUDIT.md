# Rà nguồn dữ liệu M2 — 2026-11-14

## Kết luận hiện tại

**`training_use=confirmed` theo xác nhận của người phụ trách dự án.** Người dùng cho biết đã xin và được phép sử dụng, đồng thời yêu cầu ghi nhận trạng thái confirmed cho phạm vi đồ án học tập/thi cử phi thương mại. Đây là lời xác nhận của người dùng, chưa có văn bản cấp phép, danh tính bên cấp phép hoặc phạm vi chi tiết đính kèm trong repo và chưa được kiểm chứng độc lập. Chưa xuất SFT thực trong lượt cập nhật này. Công cụ exporter kiểm tra ledger theo dataset ID + revision, không chỉ nhãn license.

### Phạm vi đồ án được người dùng xác nhận — 2026-11-15

Người dùng cho biết dự án phục vụ học tập/thi cử, không nhằm mục đích thương mại và xác nhận đã được cho phép sử dụng. Theo chỉ đạo của người dùng, ledger ghi `training_use=confirmed`; căn cứ hiện ghi nhận là lời xác nhận của người dùng, không phải tài liệu cấp phép đã được kiểm tra. Chưa có thông tin xác nhận về việc phân phối dataset hoặc model. Quy trình dịch, mapping upstream và chi tiết phạm vi cấp phép vẫn chưa được kiểm chứng độc lập.

| Nguồn sơ cấp | Quan sát | Phần chưa xác minh |
|---|---|---|
| [Card bản Việt tại revision](https://huggingface.co/datasets/nampdn-ai/tinystories-vietnamese/blob/eb37a7aa8cc44ad9841175163a460fed5c2c1b24/README.md) | Metadata MIT, en/vi; không có mô tả quy trình dịch trong card | Ai dịch, công cụ/mô hình, điều kiện sử dụng, mapping sang bản nguồn cụ thể |
| [Card TinyStories gốc tại revision](https://huggingface.co/datasets/roneneldan/TinyStories/blob/f54c09fd23315a6f9c86f9dc80f725de7d8f9c64/README.md) | Nhãn CDLA-Sharing-1.0, mô tả truyện tổng hợp bằng GPT-3.5/GPT-4 | Chưa chứng minh bản Việt lấy từ file/revision nào của nguồn này |
| [Bài báo TinyStories](https://arxiv.org/abs/2305.07759v2) | Mô tả nguồn tổng hợp và mục tiêu từ vựng tiếng Anh đơn giản | Không xác nhận chất lượng/sư phạm hoặc quyền của bản dịch tiếng Việt |
| [Discussions của bản Việt](https://huggingface.co/datasets/nampdn-ai/tinystories-vietnamese/discussions) | Danh sách có một thảo luận; công cụ web không mở được chi tiết #1 trong lần thử này | Không có bằng chứng bổ sung được xác minh từ nội dung thảo luận |

Nguồn TinyStories gốc là **ứng viên upstream**, không khẳng định đã nối lineage đầy đủ chỉ vì tên dataset giống nhau. Chênh nhãn license và chuỗi quyền của bản dịch chưa được xác minh độc lập. Không gửi tin nhắn cho tác giả trong lượt này.

## Revision, schema và bằng chứng cục bộ

- Bản Việt: `eb37a7aa8cc44ad9841175163a460fed5c2c1b24`, config default, split train. API Hub và header x-revision của viewer trùng commit. 100 hàng đầu có en/vi kiểu large_string, 100/100 giá trị mỗi cột quan sát là str. Không suy rộng sang toàn bộ nguồn.
- Nguồn gốc ứng viên: `f54c09fd23315a6f9c86f9dc80f725de7d8f9c64`. Đã lưu API/card, kiểm tra X-Repo-Commit. Card SHA-256 `f67b71c3ffe761795b9428222444bfc1ec447d45cb13b00821b7e6c1ceecf7c5`.
- Bằng chứng tại `data/raw/hf_prefix100_m2/` và `data/raw/m2_source_audit/` (Git ignore), gồm response nguyên bản, URL, revision và hash; không commit toàn bộ bản truyện. Ledger ở `data/review/rights_ledger.json` ghi `training_use=confirmed` dựa trên xác nhận của người dùng; tài liệu cấp phép chưa được đính kèm hoặc kiểm chứng độc lập.

## Việc cần người phụ trách xác nhận

Nếu cần tăng mức độ kiểm chứng, bổ sung tài liệu về bên cấp phép, nguồn bản en, phiên bản/file sử dụng, quy trình dịch và phạm vi quyền sử dụng bản dịch; đối chiếu với điều khoản upstream và người hướng dẫn. Hiện ledger phản ánh xác nhận người phụ trách, còn các chi tiết này chưa được xác minh độc lập. Trong lúc đó có thể tiếp tục đọc/duyệt mẫu khảo sát hoặc kiểm tra bằng fixture tổng hợp theo phạm vi đã cho phép.
