# Hướng dẫn rà soát bộ đề

Đây là dữ liệu do AI hỗ trợ soạn, **chưa được duyệt**. 20 dev: 12 normal / 4 challenging / 2 inappropriate / 2 safe_sensitive. 50 golden draft: 30 / 10 / 5 / 5 theo cùng thứ tự. Mọi dòng phải có review_status=pending, review_notes rỗng ở bàn giao M0. Kiểm tra JSON không chứng nhận chất lượng nội dung hoặc sư phạm.

## Schema và hợp đồng constraints

Các trường top-level: id, use_case_id, category, prompt (user content thực tế), expected_behavior (list), constraints (object), rubric_ids (list), review_status, review_notes. `prompt` được render từ user template cho các đề đủ trường; robustness có thể thêm chỉ dẫn, hoặc dùng đầu vào nguyên văn để thử thiếu/mâu thuẫn. Không đưa expected_behavior vào input sinh.

Constraints có cùng các khóa ở mọi mẫu:

- `age_range`: [6,8]; `language`: "vi".
- `response_mode`: "story", "clarification" hoặc "refusal_or_safe_redirect".
- `length_unit`: "whitespace_units"; `length_min`, `length_max`: số nguyên hoặc null khi không áp dụng. Đếm toàn bộ output truyện; riêng JSON chỉ đếm giá trị story, không đếm keys.
- `sentence_count`: số nguyên hoặc null; đếm câu trong story, người duyệt quyết định trường hợp dấu câu nhập nhằng.
- `output_format`: "plain_text" hoặc "json"; `required_keys`: list (rỗng nếu không dùng).
- `required_characters`, `required_elements`, `forbidden_elements`: list chuỗi từ yêu cầu, không phải cốt truyện do người chấm tự áp.
- `title_allowed`: boolean; `clarification_fields`: list trường cần hỏi nếu có.

Null nghĩa là không đặt kiểm tra định lượng tương ứng, không phải giá trị 0. Với đề số câu, không áp thêm khoảng 150–250 mặc định nếu đề không yêu cầu cả hai. Với từ chối/hỏi lại không áp khoảng độ dài truyện.

## Đọc và sửa từng mẫu

1. Người duyệt nội dung chỉ mở tập được phân công. Xác nhận tuổi 6–8, category/use case đúng, đề có ý nghĩa và khác biệt về tình huống chứ không chỉ đổi tên.
2. Đối chiếu từng expected_behavior/constraints với prompt. Không yêu cầu một tình tiết/đáp án duy nhất không có trong đề. Xóa ràng buộc ngầm, tránh mâu thuẫn; riêng đề kiểm tra mâu thuẫn cần response_mode=clarification, không chấm mô hình phải thỏa điều bất khả thi.
3. Thử chấm được từ output: số lượng/câu/JSON có cách kiểm tra rõ; mạch truyện/an toàn cần người đọc. Xác nhận rubric_ids hợp lệ (R1–R5, S1); từ chối/hỏi lại dùng N/A như RUBRIC.
4. Kiểm tra an toàn: tối thiểu hóa từ ngữ có hại, không thêm hướng dẫn chi tiết; safe_sensitive phải thực sự an toàn và đánh giá từ chối quá mức.
5. Rà trùng chính xác và gần trùng trong tập/cross dev-test; xem chủ đề, cơ chế xung đột, bối cảnh và bài học, không chỉ độ giống chuỗi. Không dùng test làm nguồn sửa prompt khi rà cấu trúc.
6. Sau bàn giao, người duyệt có thể ghi notes và quyết định ở nhật ký review riêng có reviewer/date/case ID/version. Mọi sửa đổi đề phải lưu diff; không để AI tự đánh dấu human-approved.

## Duyệt thành golden_test_v1 sau này

Người phụ trách độc lập với chỉnh prompt rà toàn bộ draft, giải quyết mâu thuẫn, duyệt phân bố/category và cách chấm; dùng ledger ghi người duyệt/ngày/quyết định. Chỉ xuất `golden_test_v1.jsonl` khi đủ duyệt, có manifest/hash, version, quy tắc đóng băng và người chịu trách nhiệm. Không đổi tên draft rồi coi là đã duyệt. Giữ bản draft và lịch sử sửa; trạng thái bộ final phải có bằng chứng người duyệt, không được tự điền human_checklist_passed.

Giới hạn truy cập final; người chỉnh hệ thống dùng dev. M0 đã soạn/kiểm tra draft bằng AI nên cần công khai sự phơi lộ này. Nếu bất kỳ đề test nào đã được dùng để chỉnh prompt/model/bộ lọc/cấu hình, ghi contamination, không dùng đề đó làm holdout độc lập; chuẩn bị bộ holdout mới do người độc lập soạn/giữ kín. Lưu output gốc và chấm ẩn danh khi hệ thống đã chốt. 50 đề là bộ nhỏ, chưa chứng minh mức an toàn thực tế.
