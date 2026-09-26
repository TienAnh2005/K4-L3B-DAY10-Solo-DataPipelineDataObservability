# Individual Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin cá nhân

| Thông tin         | Nội dung                  |
| ------------------ | -------------------------- |
| Họ và tên       | Tien Anh                   |
| MSSV               | [Điền MSSV của bạn]        |
| Khóa/Lớp         | K4 - Lớp B (Ca Sáng)       |
| Tên nhóm         | Tien Anh (Solo)            |
| Vai trò chính    | Pipeline Lead & Data Observability Engineer |
| Repository         | https://github.com/TienAnh2005/K4-L3B-DAY10-Solo-DataPipelineDataObservability |
| Ngày hoàn thành | 2026-09-26                 |

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao  | Trạng thái |
| ------------------ | --------------------- | ---------------- | ----------------- | ---------- |
| **Ingestion** | `src/ingestion/crossref.py` | Crossref API / `crossref_response.json` | `data/raw/crossref_records.json` | Hoàn thành |
| **Cleaning** | `src/ingestion/cleaning.py` | List `PaperRecord` | `papers_clean.csv`, `papers_clean.json` | Hoàn thành |
| **Observability** | `src/observability/quality.py` | Cleaned/Corrupted DataFrame | GX 1.x Reports & Freshness SLA Reports | Hoàn thành |
| **Evaluation** | `src/evaluation/testset.py` | Cleaned DataFrame | `data/eval/test_set.json` (10 câu hỏi) | Hoàn thành |
| **Corruption & Repair** | `src/ingestion/corruption.py`, `src/pipelines/corruption_flow.py` | Clean DataFrame, Raw Snapshot | 6 kịch bản lỗi, bảng đối chiếu 3 trạng thái | Hoàn thành |
| **Bonus Features** | `src/pipelines/auto_heal.py`, `script/run_dashboard.py`, `tests/` | Pipeline artifacts | Self-healing incident log, HTML Dashboard, Pytest suite | Hoàn thành |

## 3. Kết quả kỹ thuật đạt được

1. **Thực thi trọn vẹn Baseline:**
   - Hoàn thành thu thập 24 tài liệu học thuật từ Crossref.
   - Làm sạch toàn bộ dữ liệu, chuẩn hóa trường `text_for_embedding` và tính trường `age_days`.
   - Index thành công vào ChromaDB collection `papers-baseline`.
   - Đạt Retrieval Hit Rate: **100.00%**, Mean Token F1: **1.0000**, Judge Accuracy: **100.00%**.
2. **Chứng minh hiện tượng Silent Failure & Data Observability:**
   - Tiêm 6 kịch bản lỗi: xóa 20% bản ghi mới nhất, làm rỗng tóm tắt, chèn nhiễu, cắt ngắn tiêu đề, lùi ngày xuất bản và nhân bản dòng.
   - Thấy rõ sự sụt giảm của RAG Agent: Hit Rate giảm từ **100% xuống 60%**, F1 giảm từ **1.0000 xuống 0.6000**.
   - Great Expectations 1.x phát hiện vi phạm và trả về `success = False`. Freshness SLA cảnh báo tỷ lệ stale lên tới `50.00% > 25%`.
3. **Cơ chế Idempotent Self-Healing / Repair:**
   - Tự động reload từ snapshot raw gốc bất biến (`data/raw/crossref_records.json`), chạy quy trình làm sạch và nạp lại ChromaDB.
   - Chỉ số phục hồi hoàn toàn: Hit Rate: **100.00%**, Mean Token F1: **1.0000**, GX: **Passed**.

## 4. Bằng chứng kiểm thử và xác minh

- Lệnh `python script/run_phase1.py` chạy thành công (exit code 0).
- Lệnh `python script/run_corruption_flow.py` chạy thành công (exit code 0).
- Lệnh `python script/run_auto_heal.py` chạy thành công (exit code 0).
- Lệnh `pytest tests -v` đạt **8/8 tests passed**.
- Dashboard trực quan được tạo tại `report/observability_dashboard.html`.

## 5. Điều học được (Key Learnings)

- **Hiểu sâu sắc về Data Observability:** Trong các hệ thống RAG và LLM Agents, dữ liệu bẩn thường không gây crash code mà gây ra Silent Failure (mô hình trả lời sai, hallucination). Do đó, Data Quality Gate (GX 1.x) và Freshness SLA là chốt chặn bắt buộc trước khi dữ liệu được vector hóa.
- **Nguyên lý Idempotency & Data Lineage:** Luôn bảo toàn dữ liệu gốc (Raw Lineage bất biến) để có thể kích hoạt rollback và phục hồi trạng thái hệ thống một cách an toàn, tin cậy.
