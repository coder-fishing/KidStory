# Kế hoạch dữ liệu

Trạng thái cập nhật M2 — 2026-11-15: batch 100 mẫu tại revision `eb37a7aa8cc44ad9841175163a460fed5c2c1b24` có 100/100 approval hợp lệ; gần trùng chạy lại trên batch cho 0 cặp ở ngưỡng 0.65/ngram 3; SFT CPU đã xuất 90 train/10 validation. Một batch chỉnh sửa 30 mẫu khác có 24 approved và 6 pending. Ledger quyền dùng được đặt `confirmed` theo xác nhận người dùng, nhưng tài liệu cấp phép/chi tiết phạm vi chưa được kiểm chứng độc lập trong repo. Near trên mẫu nhỏ không chứng minh toàn nguồn sạch. Người dùng chốt mục tiêu mở rộng là 10.000 mẫu train đã duyệt; bắt đầu kiểm tra quy trình trên 1.000 mẫu. Đây là mục tiêu tương lai, chưa phải dữ liệu/artifact đã có. Xem SOURCE_AUDIT, M2_REPORT và M2_REVIEW_GUIDE.

## Cổng xác minh nguồn

Ứng viên [nampdn-ai/tinystories-vietnamese](https://huggingface.co/datasets/nampdn-ai/tinystories-vietnamese). Tra cứu card/viewer sơ bộ ngày 2026-11-14 thấy nhãn MIT và các cột `en`, `vi`; đây chỉ là quan sát giao diện, **chưa xác minh schema tại revision cố định**, nguồn bản dịch hoặc toàn bộ quyền sử dụng. Trước khi lấy dữ liệu thực: ghi commit revision bất biến, config/split/features, kiểm tra kiểu/null bằng mẫu nhỏ; đọc LICENSE/card tại revision đó, truy nguồn TinyStories gốc và quy trình dịch, ghi phần chưa rõ. Nếu chưa đủ cơ sở quyền sử dụng thì dừng xuất dữ liệu huấn luyện và xin hướng dẫn; không suy diễn nhãn Hub thành kết luận pháp lý.

## Lấy mẫu và EDA cho M1/M2

Snapshot prefix100 hiện có chỉ là dữ liệu phát triển ban đầu, không đại diện nguồn. Module nguồn hỗ trợ `random_blocks`: lấy các block 100 hàng bằng seed từ revision đã khóa, giới hạn 10.000 hàng, kiểm tra revision ở từng phản hồi và lưu row IDs/hash. Đây là cluster sample, không phải IID random sample từng hàng; cần báo cáo giới hạn cụm. Không tải toàn bộ dataset.

Mục tiêu người dùng đã chốt: EDA một pool khoảng 10.000 ứng viên hướng tới 10.000 mẫu train đã duyệt; chạy thử quy trình trên 1.000 mẫu trước. Nếu mẫu bị loại thì cần lấy bổ sung để đạt mục tiêu cuối. Chưa tạo snapshot 1.000/10.000 từ nguồn thật. Lệnh EDA hiện thống kê schema kiểu/null/rỗng, độ dài ký tự và đơn vị cách trắng, dấu câu, ký tự điều khiển/chữ ngoài Latin, exact duplicate, nhóm nguồn, dấu hiệu cắt cụt/lặp; xuất các ứng viên tên và dịch sát vào CSV pending. Các heuristic không phải nhãn chất lượng/ngôn ngữ, không thay đổi text. Dùng tokenizer đúng revision ở milestone sau để đo **model token**, không ép pipeline CPU M1 phụ thuộc model weights.

## Bản ghi trung gian dự kiến

`source_id`, `source_revision`, `source_split`, `source_row_id`, `source_group_id`, `original_text`, `processed_text`, `edit_reasons` (list), `flags` (list), `exact_hash`, `near_duplicate_group_id` (null nếu chưa xác định), `topic`, `characters`, `lesson`, `label_source`, `review_status`, `reviewer`, `reviewed_at`. Nhãn thiếu để null, trạng thái pending; không tự tạo tên/bài học để đủ schema. ID nguồn phải ổn định, không chỉ dựa vào số thứ tự sau lọc. `original_text` luôn giữ nguyên; provenance ngoài phần text không bị bỏ.

## Chuẩn hóa và kiểm soát chất lượng

Đề xuất NFC Unicode, chuẩn hóa line ending, gọn khoảng trắng theo chính sách được ghi phiên bản, giữ đoạn văn khi có ý nghĩa. Ghi lý do mỗi thay đổi; không sửa trực tiếp original. Kiểm tra rỗng, dữ liệu sai kiểu, ký tự điều khiển, truyện cắt giữa câu, lặp đoạn, tên/đại từ bất nhất, nội dung không phù hợp tuổi. Cờ heuristic dẫn đến review/quarantine, không tự khẳng định truyện hỏng hoặc an toàn. Không thay tên/đại từ hàng loạt, không xóa ngoại ngữ để che chất lượng bản dịch.

Đếm ký tự là độ dài chuỗi Unicode theo phương pháp đã ghi, đơn vị cách trắng là số phần không rỗng từ split khoảng trắng Unicode, model token do tokenizer tạo. Báo riêng ba loại, không gắn nhãn tất cả là “word count”. Mặc định đầu ra 150–250 đơn vị cách trắng là đề xuất cần thử trên dev, không dùng mù quáng làm bộ lọc mọi truyện nguồn.

## Trùng và chia tập

Trước chia: hash văn bản đã chuẩn hóa để nhóm trùng chính xác, giữ danh sách source IDs cho các bản trùng. Nếu cùng truyện có bản en/vi hoặc nhiều bản sửa, dùng source_group_id chung. M2 đề xuất ứng viên gần trùng bằng n-gram Jaccard/MinHash, hiệu chỉnh ngưỡng trên mẫu được người đọc kiểm tra rồi tạo nhóm liên thông. Chưa thực hiện thuật toán này ở M0/M1; phải công khai residual near-duplicate risk, không tuyên bố đã sạch gần trùng.

Chia theo nhóm hợp nhất nguồn + exact + near-duplicate đã xác minh; mọi thành viên một nhóm ở cùng split. Đề xuất train/validation 90/10 theo nhóm, seed 42; tỷ lệ, sai lệch số hàng và nhóm quá lớn phải báo. Lưu manifest gồm ID/hash, nhóm, split, seed, thuật toán/phiên bản, counts và lý do loại. Không dùng thứ tự set/hash ngẫu nhiên làm nền chia. Kiểm tra giao nhóm giữa train/validation bằng rỗng, tái chạy cho manifest giống nhau.

Evaluation dev và final test là bộ đề tự soạn riêng, không phải phần validation được cắt từ truyện nguồn. Duy trì cách ly với SFT; rà trùng đề/reference nếu có và ghi nguy cơ nhiễm nguồn/pretraining không thể loại hết. Không dùng nội dung test để gán nhãn train hoặc chỉnh prompt.

## Metadata và xuất SFT ở M2

Chủ đề/nhân vật/bài học phải đúng với truyện đang có. Gợi ý tự động chỉ là nhãn đề xuất với label_source và pending; người duyệt sửa/xác nhận, ghi reviewer và ngày. Chỉ xuất SFT khi text và toàn bộ metadata bắt buộc đã duyệt, không có cờ chặn chưa xử lý. User prompt chỉ dùng trường người dùng có thể cung cấp, không lộ tình tiết/đáp án rút từ truyện. Tách dữ liệu safety và review nếu cần, không tự chế truyện độc hại cho training.
