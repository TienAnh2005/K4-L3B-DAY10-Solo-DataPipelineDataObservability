# Group Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin bài nộp

| Thông tin         | Nội dung                  |
| ------------------ | -------------------------- |
| Khóa/Lớp         | K4 - Lớp B (Ca Sáng)      |
| Tên nhóm         | Tien Anh (Solo)            |
| Repository         | https://github.com/TienAnh2005/K4-L3B-DAY10-Solo-DataPipelineDataObservability |
| Ngày hoàn thành | 2026-09-26               |

### Thành viên và phân công

| STT | Họ và tên | MSSV | Vai trò chính | Module/deliverable sở hữu |
| --: | --- | --- | --- | --- |
| 1 | Tien Anh | [MSSV của bạn] | Pipeline Lead & Data Observability Engineer | Toàn bộ CP0 - CP6: `core/`, `ingestion/`, `retrieval/`, `observability/`, `evaluation/`, `pipelines/` |

## 2. Tóm tắt kết quả

Nhóm (Solo) đã hoàn thành 100% tất cả các hạng mục từ Checkpoint 0 đến Checkpoint 6 cùng 3 tiêu chí điểm thưởng Bonus (B1, B2, B3):

- **Baseline Pipeline:** Thu thập thành công 24 bản ghi Crossref API (với cơ chế Fallback offline `data/raw/crossref_response.json`). Dữ liệu được làm sạch, khử XML JATS, tính toán `age_days` và định dạng `text_for_embedding`. Kết quả kiểm định Great Expectations 1.x đạt `success=True`, Freshness SLA đạt chuẩn `is_fresh=True` (chỉ 4.17% bản ghi cũ). Vector index ChromaDB được tạo lập với mô hình `all-MiniLM-L6-v2`. Đánh giá trên bộ 10 câu hỏi benchmark chuẩn đạt Retrieval Hit Rate 100%, Mean Token F1 1.0000 và Judge Accuracy 100%.
- **Data Corruption & Silent Failure:** Tiêm 6 kịch bản lỗi (mất 20% bản ghi mới, rỗng tóm tắt, nhiễu văn bản, cắt ngắn tiêu đề < 8 ký tự, lùi ngày xuất bản > 1000 ngày, trùng lặp bản ghi). Hiện tượng Silent Failure được chứng minh rõ rệt: Retrieval Hit Rate sụt giảm từ 100% xuống 60%, Mean Token F1 tụt xuống 0.6000 mà không phát sinh runtime exception. Data Quality Gate GX 1.x đã cảnh báo vi phạm (`success=False`) và Freshness SLA kích hoạt báo động (`is_fresh=False`, 50% stale).
- **Idempotent Repair & Self-Healing:** Phục hồi sạch toàn diện từ snapshot raw lineage gốc (`data/raw/crossref_records.json`), đưa toàn bộ chỉ số Retrieval Hit Rate và F1 về lại mức 100%. Bảng đối chiếu 3 trạng thái đã được xuất tự động ra `data/reports/corruption_report.md`.
- **Bonus hoàn thành:**
  - B1: Interactive Observability Dashboard tại `report/observability_dashboard.html`.
  - B2: Automated Self-Healing Pipeline tại `src/pipelines/auto_heal.py`.
  - B3: Automated Test Suite (Pytest) tại `tests/test_pipeline.py` (8/8 passed).

## 3. Kiến trúc và luồng dữ liệu

### Luồng end-to-end

```text
Crossref API (hoặc Snapshot Offline Fallback)
    -> data/raw/crossref_records.json (Raw Lineage Bất Biến)
    -> Cleaning & Pre-embedding Modeling (data/clean/papers_clean.csv/.json)
    -> Sentence-Transformers (all-MiniLM-L6-v2) + ChromaDB Index (papers-baseline)
    -> Evaluation Benchmark (data/eval/test_set.json - 10 câu hỏi)
    -> Data Observability: Great Expectations 1.x + Freshness SLA
    -> Phase 1 Report (data/reports/phase1_report.md)
    -> Synthetic Data Corruption (6 kịch bản lỗi -> data/results/corruption_log.json)
    -> Corrupted Index (papers-corrupted) & Evaluation (Silent Failure)
    -> Idempotent Self-Healing / Repair từ Raw Records
    -> Repaired Index (papers-repaired) & Evaluation
    -> 3-State Comparison Report (data/reports/corruption_report.md)
```

### Trách nhiệm của từng khối

| Khối             | Input          | Xử lý chính             | Output/artifact          | Owner          |
| ----------------- | -------------- | -------------------------- | ------------------------ | -------------- |
| Ingestion         | Crossref API / Snapshot JSON | Fetch, retry fallback, parse payload, load records | `data/raw/crossref_records.json` | Tien Anh |
| Cleaning          | Raw `PaperRecord` objects | Strip JATS XML, tính `age_days`, tạo `text_for_embedding`, dedup | `data/clean/papers_clean.csv/.json` | Tien Anh |
| Embedding/index   | Clean DataFrame | Vectorize qua `all-MiniLM-L6-v2`, build ChromaDB collection | `data/chroma/`, `data/embeddings/*.json` | Tien Anh |
| Evaluation        | Clean DataFrame, Vector Index | Sinh 10 câu hỏi (summary, authors, date, categories), QA & Judge | `data/eval/test_set.json`, `data/results/*_metrics.json` | Tien Anh |
| Observability     | Clean/Corrupted DataFrame | GX 1.x Ephemeral Context (4 checks), Freshness SLA check | `data/quality/*_report.json` | Tien Anh |
| Corruption/repair | Clean DataFrame, Raw Snapshot | Tiêm 6 lỗi dữ liệu, log audit; reload raw snapshot để idempotent repair | `data/results/corruption_log.json`, `repaired_clean.*` | Tien Anh |
| Orchestration     | Toàn bộ module | Điều phối luồng `run_phase1.py`, `run_corruption_flow.py`, `run_auto_heal.py` | `data/reports/*.md`, `dashboard.html` | Tien Anh |

## 4. Cách tái hiện kết quả

### Cấu hình không chứa secret

| Biến/cấu hình             | Giá trị sử dụng |
| ---------------------------- | ------------------- |
| `LLM_PROVIDER`             | `mock` (Hỗ trợ switch sang `gemini`, `openai`) |
| `LLM_MODEL`                | `mock` (hoặc `gemini-2.5-flash`) |
| Embedding model              | `sentence-transformers/all-MiniLM-L6-v2` |
| Số lượng Crossref records | 24 |
| Retrieval `top_k`           | 4 |
| Freshness threshold          | 180 ngày |
| Random seed, nếu có        | Deterministic selection |

### Lệnh cài đặt

```bash
uv venv
.venv\Scripts\activate
uv pip install -r requirements.txt
uv pip install pytest pytest-cov
```

### Lệnh chạy

Baseline Pipeline:
```bash
python script/run_phase1.py
```

Corruption & Repair Flow:
```bash
python script/run_corruption_flow.py
```

Automated Self-Healing Pipeline (Bonus B2):
```bash
python script/run_auto_heal.py
```

Pytest Automated Test Suite (Bonus B3):
```bash
pytest tests -v
```

Visual Observability Dashboard (Bonus B1):
```bash
python script/run_dashboard.py
```

### Kết quả tái hiện

| Lệnh             | Trạng thái                                    | Thời điểm chạy gần nhất | Bằng chứng                         |
| ----------------- | ----------------------------------------------- | ----------------------------- | ------------------------------------ |
| Baseline pipeline | Thành công (Exit code 0) | 2026-09-26 10:47:57 | `data/results/baseline_metrics.json`, `data/reports/phase1_report.md` |
| Corruption flow   | Thành công (Exit code 0) | 2026-09-26 10:48:50 | `data/results/corrupted_metrics.json`, `data/reports/corruption_report.md` |
| Automated heal    | Thành công (Exit code 0) | 2026-09-26 10:50:35 | `data/quality/self_healing_incident_log.json` |
| Pytest suite      | Thành công (8/8 passed)  | 2026-09-26 10:49:44 | `tests/test_pipeline.py` |

## 5. Ingestion, cleaning và data contract

### Nguồn dữ liệu

| Thuộc tính                | Giá trị                             |
| --------------------------- | ------------------------------------- |
| Source                      | Crossref REST API / Snapshot `data/raw/crossref_response.json` |
| Query/filter                | query="agentic retrieval augmented generation large language model", filter="from-pub-date:...,has-abstract:true" |
| Thời điểm lấy dữ liệu | 2026-09-26 |
| Số record nhận được    | 24 |
| Cơ chế retry/backoff      | Timeout 20s, graceful offline fallback vào snapshot raw khi gặp HTTP error/network issue |

### Raw và clean schema

| Trường        | Kiểu dữ liệu | Bắt buộc?  | Ý nghĩa   | Xử lý khi thiếu/sai |
| --------------- | --------------- | ------------ | ----------- | ---------------------- |
| `paper_id`      | `str`           | Có           | DOI bài báo, định danh duy nhất | Bỏ qua record nếu thiếu DOI |
| `title`         | `str`           | Có           | Tiêu đề bài báo | Bỏ qua nếu tiêu đề trống hoặc < 5 ký tự |
| `summary`       | `str`           | Có           | Tóm tắt nghiên cứu | Chuẩn hóa thẻ JATS XML; cảnh báo nếu quá ngắn |
| `authors`       | `list[str]`     | Không        | Danh sách tên tác giả | Ghép given + family; để rỗng nếu không có |
| `published`     | `str`           | Có           | Ngày xuất bản (YYYY-MM-DD) | Ghép từ date-parts; mặc định 1970-01-01 nếu thiếu |
| `age_days`      | `int`           | Có           | Độ tuổi tài liệu tính theo ngày | `(run_date - pub_date).days` |
| `text_for_embedding` | `str`      | Có           | Chuỗi đại diện 5 phần dùng để embed | Tự động ghép cấu trúc Title + Authors + Published + Categories + Summary |

### Quy tắc cleaning

| Quy tắc                                 | Quality dimension liên quan | Số record bị tác động | Cách xác minh      |
| ---------------------------------------- | ---------------------------- | -------------------------: | -------------------- |
| Loại bỏ thẻ JATS XML `<jats:p>`          | Conformance / Validity       | 24 | Regex kiểm tra không còn thẻ `<...>` |
| Chuẩn hóa khoảng trắng dư thừa           | Consistency                  | 24 | `normalize_whitespace` |
| Tính toán `age_days`                     | Currency / Freshness         | 24 | So sánh với ngày chạy pipeline |
| Khử trùng lặp theo `paper_id`            | Uniqueness                   | 0 (sạch ban đầu) | `df.drop_duplicates(subset=['paper_id'])` |
| Cấu trúc hóa 5 phần `text_for_embedding` | Completeness                 | 24 | Kiểm tra format chuỗi embedding |

## 6. Evaluation setup

| Thành phần                             | Cấu hình thực tế          |
| ---------------------------------------- | ----------------------------- |
| Số câu hỏi                            | 10 câu hỏi chuẩn              |
| Các `question_type`                    | `summary` (3), `authors` (3), `date` (2), `categories` (2) |
| Ground-truth document ID                 | `paper_id` của tài liệu tương ứng |
| Embedding model                          | `sentence-transformers/all-MiniLM-L6-v2` |
| Vector store/collection                  | ChromaDB (`papers-baseline`, `papers-corrupted`, `papers-repaired`) |
| Retrieval `top_k`                       | 4                             |
| LLM provider/model                       | `mock` (kết hợp deterministic QA extractor & structured judge) |
| Test set dùng chung cho ba trạng thái | `data/eval/test_set.json` (dùng chung cố định) |

**Giải thích vì sao test set được giữ nguyên:**
Để đảm bảo tính khách quan và khoa học của phương pháp đo lường (A/B testing / Benchmark), cùng một tập câu hỏi kiểm tra phải được áp dụng trên cả 3 trạng thái. Bất kỳ sự thay đổi nào về Hit Rate hay F1 sẽ phản ánh chính xác tác động của sự suy giảm hoặc phục hồi chất lượng dữ liệu, loại bỏ nhiễu do câu hỏi khác nhau.

## 7. Kết quả baseline

### Artifact checklist

| Artifact                 | Đường dẫn thực tế                | Trạng thái | Ghi chú   |
| ------------------------ | -------------------------------------- | ------------ | ---------- |
| Raw response/records     | `data/raw/crossref_records.json`       | Có           | 24 bản ghi gốc |
| Cleaned dataset          | `data/clean/papers_clean.csv/.json`    | Có           | 24 dòng sạch hoàn chỉnh |
| Embedding manifest/index | `data/embeddings/papers_embeddings.json`| Có          | Chroma collection `papers-baseline` |
| Evaluation set           | `data/eval/test_set.json`              | Có           | 10 câu benchmark |
| Baseline metrics         | `data/results/baseline_metrics.json`   | Có           | Hit Rate 100%, F1 1.0000 |
| Quality/freshness        | `data/quality/baseline_quality_report.json` | Có      | GX 1.x: True, Fresh: True |
| Baseline report          | `data/reports/phase1_report.md`        | Có           | Markdown hoàn chỉnh |

### Baseline metrics

| Metric                 |       Giá trị | Diễn giải                             |
| ---------------------- | --------------: | --------------------------------------- |
| `retrieval_hit_rate`   |         100.00% | Toàn bộ 10/10 câu hỏi truy xuất chính xác tài liệu nguồn |
| `mean_token_f1`        |          1.0000 | Câu trả lời trích xuất khớp chính xác với ground truth |
| `judge_accuracy`       |         100.00% | 10/10 câu được giám khảo đánh giá đạt chuẩn |
| `mean_judge_score`     |          5.00/5 | Điểm tối đa 5.0 |

## 8. Data quality và freshness

### Quality checks (Great Expectations 1.x)

| Check | Quality dimension | Ngưỡng/kỳ vọng | Kết quả baseline | Bằng chứng |
| :--- | :--- | :--- | :--- | :--- |
| `ExpectTableRowCountToBeBetween` | Completeness | 15 đến 30 dòng | Passed (24 dòng) | `baseline_quality_report.json` |
| `ExpectColumnValuesToNotBeNull` | Completeness | `paper_id`, `title` không null | Passed (0 null) | `baseline_quality_report.json` |
| `ExpectColumnValuesToBeUnique` | Uniqueness | `paper_id` là duy nhất | Passed (100% unique) | `baseline_quality_report.json` |
| `ExpectColumnValueLengthsToBeBetween` | Validity | `title` >= 8 ký tự, `summary` >= 15 ký tự | Passed | `baseline_quality_report.json` |

### Freshness SLA

| Thuộc tính               | Giá trị                             |
| -------------------------- | ----------------------------------- |
| Freshness được đo tại | Cột `age_days` trong DataFrame clean |
| Timestamp mới nhất       | 2026-05-20 |
| Ngưỡng freshness         | 180 ngày (SLA cảnh báo nếu stale > 25%) |
| Trạng thái baseline      | **Healthy (`is_fresh=True`)** |
| Tỷ lệ stale              | 4.17% (1/24 bài báo > 180 ngày) $\le$ 25% |

## 9. Corruption scenarios và repair

| Corruption | Cách tạo | Record bị tác động | Quality signal kỳ vọng | Tác động thực tế | Cách repair |
| :--- | :--- | ---: | :--- | :--- | :--- |
| **Drop latest records** | Cắt bỏ 4 bản ghi mới nhất | 4 | Vi phạm số lượng dòng | Hit Rate giảm từ 100% xuống 60% | Reload từ raw snapshot gốc |
| **Blank summary** | Gán summary = "" | 1 | Vi phạm độ dài summary | Vector embedding suy biến | Re-clean từ raw snapshot |
| **Inject noise** | Chèn ký tự rác vào summary | 1 | Lệch không gian ngữ nghĩa | Cosine distance bị nhiễu | Re-clean từ raw snapshot |
| **Truncate title** | Cắt title = "Bad" (< 8 ký tự) | 1 | Vi phạm GX title length | Tra cứu exact match thất bại | Re-clean từ raw snapshot |
| **Stale date** | Lùi ngày xuất bản về 2020 (age > 2400) | 8 | Tỷ lệ stale lên 50% | Freshness SLA báo động STALE | Re-clean từ raw snapshot |
| **Duplicate rows** | Nhân bản 2 dòng trùng paper_id | 2 | Vi phạm GX uniqueness | Ô nhiễm index với duplicate doc | Re-clean và dedup qua paper_id |

### Giải thích cơ chế Idempotent Repair:
Cơ chế repair không cố gắng vá víu trên tập dữ liệu bẩn mà quay về **Snapshot Thô Bất Biến** (`data/raw/crossref_records.json`). Nhờ nguyên lý Idempotent:
`Repair(Data_Bẩn) = Clean(Raw_Snapshot)`
Bất kể pipeline bị tiêm lỗi bao nhiêu lần, kết quả sau khi chạy hàm phục hồi luôn tạo ra một tập dữ liệu sạch duy nhất, đồng nhất và khôi phục 100% độ chính xác của hệ thống RAG.

## 10. So sánh baseline, corrupted và repaired

| Metric/signal            | Baseline | Corrupted | Repaired | Thay đổi do corruption | Mức phục hồi | Nhận xét   |
| ------------------------ | -------: | --------: | -------: | -----------------------: | --------------: | ------------ |
| `retrieval_hit_rate`     |  100.00% |    60.00% |  100.00% |                  -40.00% |         +40.00% | Khôi phục hoàn toàn về mức 100% |
| `mean_token_f1`          |   1.0000 |    0.6000 |   1.0000 |                  -0.4000 |         +0.4000 | Khôi phục độ chính xác tuyệt đối |
| `judge_accuracy`         |  100.00% |    60.00% |  100.00% |                  -40.00% |         +40.00% | Điểm đánh giá trở lại 100% |
| `mean_judge_score`       |   5.00/5 |    3.40/5 |   5.00/5 |                  -1.60/5 |         +1.60/5 | Điểm tối đa 5/5 |
| Quality checks pass/fail |   Passed |    FAILED |   Passed | Đổi từ True sang False | Đổi lại True    | GX 1.x bắt trọn vẹn 3 lỗi schema |
| Freshness status         |  Healthy |     STALE |  Healthy | Tỷ lệ stale tăng lên 50% | Về lại 4.17%    | Freshness SLA cảnh báo chính xác |

### Hai kết luận có quan hệ nhân quả:
1. **Dữ liệu lỗi $\rightarrow$ Silent Failure:** Khi các bản ghi mới bị mất và tiêu đề bị cắt ngắn, hệ thống RAG không gặp lỗi cú pháp hay exception nhưng Hit Rate sụt giảm nghiêm trọng từ 100% xuống 60%. Nếu không có Great Expectations và Freshness SLA, lỗi này sẽ lọt ra serving layer gây ảnh hưởng đến người dùng cuối.
2. **Idempotent Repair $\rightarrow$ Khôi phục toàn diện:** Kích hoạt cơ chế làm sạch lại từ raw lineage giúp loại bỏ hoàn toàn các vector nhiễu trong ChromaDB, đưa Hit Rate và Token F1 phục hồi 100% tương đương với Baseline.

## 11. Vấn đề tích hợp quan trọng

- **Triệu chứng:** Phiên bản Great Expectations 1.x thay đổi toàn bộ kiến trúc Fluent Data Sources so với chuẩn cũ 0.18.x, các câu lệnh cũ như `context.sources.add_pandas` hoặc `ge.read_json` sẽ gây crash.
- **Nguyên nhân:** Great Expectations 1.x yêu cầu cấu hình context ephemeral: `context.data_sources.add_pandas` $\rightarrow$ `add_dataframe_asset` $\rightarrow$ `add_batch_definition_whole_dataframe` $\rightarrow$ `get_batch`.
- **Cách xử lý:** Triển khai đúng chuẩn GX 1.x Fluent API trong `src/observability/quality.py`, đóng gói validation results thành cấu trúc JSON rõ ràng.
- **Cách xác minh:** Chạy `python -c "from observability.quality import run_data_quality_checks; ..."` và toàn bộ 8 bài test `pytest tests -v` đạt passed.

## 12. Giới hạn và hướng cải thiện

| Giới hạn hiện tại | Ảnh hưởng | Hướng cải thiện có thể kiểm chứng |
| :--- | :--- | :--- |
| Corpus hiện tại có quy mô nhỏ (24 bài báo) | Chưa kiểm thử được hiệu năng khi index hàng chục nghìn bài | Mở rộng ingestion phân trang (pagination) với `rows=1000` |
| Đánh giá Judge bằng structured fallback khi không có API key | Điểm số dựa trên heuristic Token F1 thay vì LLM reasoning | Tích hợp Google Gemini 2.5 Flash qua API key khi triển khai production |

## 13. Checklist trước khi nộp

- [x] Thông tin nhóm và repository chính xác (`TienAnh2005/K4-L3B-DAY10-Solo-DataPipelineDataObservability`).
- [x] Phân công khớp với module, artifact và kết quả thực tế trong `TEAM.md`.
- [x] Lệnh tái hiện đã được chạy lại thành công: `run_phase1.py`, `run_corruption_flow.py`, `run_auto_heal.py`.
- [x] Baseline, corrupted và repaired dùng chung 10 câu hỏi test trong `data/eval/test_set.json`.
- [x] Bảng metrics khớp 100% với các file trong `data/results/`.
- [x] Quality/freshness conclusions khớp với `data/quality/`.
- [x] Không có `.env`, API key, token hoặc secret trong git history.
- [x] Có giao diện Observability Dashboard tại `report/observability_dashboard.html`.
- [x] Có bộ test tự động Pytest 8/8 passed.
