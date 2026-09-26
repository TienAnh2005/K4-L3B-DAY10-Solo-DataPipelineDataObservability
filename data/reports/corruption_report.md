# Báo Cáo Đối Chiếu 3 Trạng Thái: Baseline vs Corrupted vs Repaired

> **Mục tiêu:** Chứng minh năng lực phát hiện dữ liệu bẩn của Data Quality Gate (Great Expectations 1.x & Freshness SLA), lượng hóa hiện tượng **Silent Failure** của RAG Agent khi dữ liệu suy giảm, và kiểm chứng cơ chế **Idempotent Self-Healing/Repair**.

---

## 1. Bảng Tổng Hợp So Sánh 3 Trạng Thái (Benchmark Comparison Table)

| Chỉ số / Tiêu chí Đánh giá | Baseline (Dữ liệu sạch) | Corrupted (Bị tiêm 6 lỗi) | Repaired (Sau phục hồi Idempotent) |
| :--- | :---: | :---: | :---: |
| **Document Count** | 10 | 22 | 24 |
| **GX 1.x Quality Gate** | **Passed (True)** | **FAILED (False)** | **Passed (True)** |
| **Freshness SLA (> 180d)** | Healthy (0.0%) | **STALE (50.0%)** | Healthy (4.2%) |
| **Retrieval Hit Rate** | **100.00%** | **60.00%** | **100.00%** |
| **Mean Token F1 Score** | **1.0000** | **0.6000** | **1.0000** |
| **Judge Accuracy** | **100.00%** | **60.00%** | **100.00%** |
| **Mean Judge Score (1-5)** | **5.00 / 5.0** | **3.40 / 5.0** | **5.00 / 5.0** |

---

## 2. Phân Tích Hiện Tượng "Silent Failure" Khi Dữ Liệu Bị Làm Bẩn

Khi 6 kịch bản lỗi dữ liệu được tiêm vào pipeline:
1. **Drop latest records (mất bản ghi mới nhất):** Làm giảm trực tiếp Recall và Hit Rate của retrieval, Agent không tìm thấy văn bản nguồn.
2. **Blank summary (xóa tóm tắt):** Vi phạm luật `ExpectColumnValueLengthsToBeBetween` của GX 1.x. Embedding vector bị suy biến do thiếu ngữ cảnh semantic.
3. **Inject noise (chèn ký tự rác):** Gây nhiễu vector không gian khiến khoảng cách cosine bị lệch, dẫn đến việc xếp hạng sai tài liệu liên quan.
4. **Truncate title (rút ngắn tiêu đề < 8 ký tự):** Vi phạm ràng buộc schema dữ liệu, làm hỏng tra cứu theo exact match.
5. **Stale date (lùi ngày xuất bản về quá khứ):** Vi phạm Freshness SLA (tỷ lệ bài báo quá hạn vượt ngưỡng cảnh báo 25%).
6. **Duplicate rows (nhân bản dữ liệu):** Vi phạm ràng buộc duy nhất `ExpectColumnValuesToBeUnique(column="paper_id")`.

> **Nhận xét cốt lõi:** Hệ sinh thái LLM/RAG **không hề ném ra Runtime Exception hay Crash**, nhưng câu trả lời trở nên sai lệch, ảo giác hoặc trả lời 'I don't know'. Đây chính là **Silent Failure** nguy hiểm nhất trong môi trường Production nếu không có Data Quality Gate chặn lại.

---

## 3. Cơ Chế Phục Hồi An Toàn (Idempotent Repair)

1. **Tính Bất Biến Của Raw Data (Data Lineage):**
   - Cơ chế repair không chỉnh sửa chắp vá trên tập dữ liệu bẩn, mà thực hiện truy vết nguồn gốc (Data Lineage) và phục hồi từ **Snapshot Thô Bất Biến (`data/raw/crossref_records.json`)**.
2. **Tính Idempotent (Khả năng lặp lại không đổi trạng thái):**
   - Chạy quy trình làm sạch `build_clean_dataframe` và tái tạo ChromaDB collection `papers-repaired`.
   - Kết quả sau Repair đưa toàn bộ chỉ số Retrieval Hit Rate, Token F1 và Judge Score về mức **100% tương đương Baseline**.
   - Great Expectations 1.x và Freshness SLA đều quay trở lại trạng thái **Passed (True)**.

---
*Báo cáo được khởi tạo tự động bởi hệ thống Data Pipeline & Observability.*
