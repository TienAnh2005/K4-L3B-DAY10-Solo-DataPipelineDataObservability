# Danh Sách Thành Viên & Báo Cáo Phân Công Nhóm

- **Tên Nhóm / Cá nhân:** `Tien Anh (Solo)`
- **Mã Nhóm / Lớp:** `K4-L3B-DAY10`
- **Tên Repository Nộp Bài:** `K4-L3B-DAY10-Solo-DataPipelineDataObservability`
- **GitHub URL:** `https://github.com/TienAnh2005/K4-L3B-DAY10-Solo-DataPipelineDataObservability`

---

## # Thành viên

| STT | Họ và tên | MSSV | Email | Vai trò & Phân công công việc | Báo cáo cá nhân |
|---:|---|---|---|---|---|
| 1 | Tien Anh | [Điền MSSV của bạn] | tienanh03042005@gmail.com | End-to-End Pipeline & Data Observability Lead (CP0 - CP6, Bonus B1, B2, B3) | `report/TienAnh_Report.md` |

---

## # Cá nhân

### ## Tien Anh
- **Vai trò:** Toàn quyền phụ trách luồng Pipeline, Observability, RAG Index & Self-Healing.
- **Công việc chi tiết đã hoàn thành:**
  - **CP0:** Thiết lập môi trường ảo `.venv`, cấu hình `.env`, hoàn thiện parser `parse_crossref_payload`, fetch và load raw records đảm bảo Data Lineage.
  - **CP1:** Xây dựng module làm sạch dữ liệu `src/ingestion/cleaning.py` (loại bỏ JATS XML, tính `age_days`, ghép `text_for_embedding`, dedup). Thiết lập Data Quality Gate bằng **Great Expectations 1.x** và giám sát **Freshness SLA** trong `src/observability/quality.py`.
  - **CP2:** Xây dựng bộ test benchmark 10 câu hỏi (`testset.py`) qua 4 nhóm nghiệp vụ và hoàn thành Vector Store Indexing trên ChromaDB với mô hình `all-MiniLM-L6-v2`.
  - **CP3:** Hoàn thành Baseline Pipeline End-to-End (`phase1.py`), chạy kiểm thử và xuất báo cáo `phase1_report.md` đạt Hit Rate 100% và Token F1 1.0000.
  - **CP4:** Thiết kế bộ tiêm 6 lỗi dữ liệu `src/ingestion/corruption.py`, đo lường sự suy giảm chất lượng RAG (hiện tượng **Silent Failure**) khiến Hit Rate giảm về 60% và GX báo lỗi.
  - **CP5:** Thực thi cơ chế phục hồi **Idempotent Repair** từ raw snapshot gốc, đưa hệ thống trở lại phong độ 100% và xuất bảng đối chiếu 3 trạng thái tại `corruption_report.md`.
  - **Bonus (B1, B2, B3):**
    - B1: Thiết kế giao diện HTML Dashboard trực quan quan sát chất lượng dữ liệu (`report/observability_dashboard.html`).
    - B2: Xây dựng cơ chế tự động phát hiện vi phạm và kích hoạt phục hồi tự động (`src/pipelines/auto_heal.py`).
    - B3: Bộ test tự động kiểm thử toàn diện `pytest` đạt 8/8 passed (`tests/test_pipeline.py`).
- **Điều học được / Đóng góp chính:**
  - Nắm vững kiến trúc Data Observability cho hệ thống AI/RAG trong sản xuất, hiểu rõ sự nguy hiểm của hiện tượng Silent Failure và cách dùng Quality Gates kết hợp Idempotent Pipeline để bảo vệ hệ thống.
