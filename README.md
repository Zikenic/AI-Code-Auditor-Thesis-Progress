# AI Code Auditor — Research and Development

**Đề tài**: Nghiên cứu, xây dựng hệ thống tự động đánh giá và phát hiện lỗi trong mã nguồn trên môi trường Pull Request  
**Sinh viên thực hiện**: Bùi Vạn Khải — MSSV: 24520719  
**Giảng viên hướng dẫn**: ThS. Trần Thị Hồng Yến  
**Đơn vị đào tạo**: Khoa Kỹ thuật Phần mềm — Trường Đại học Công nghệ Thông tin, ĐHQG-HCM  
**Học kỳ**: Học kỳ 1, Năm học 2026–2027  

---

## 1. Giới thiệu đề tài & Mục tiêu nghiên cứu (Research Overview)

Hệ thống **AI Code Auditor** được nghiên cứu và phát triển nhằm giải quyết bài toán tự động hóa quy trình rà soát mã nguồn (Automated Code Review) và phát hiện các khiếm khuyết phần mềm, lỗ hổng bảo mật trên môi trường Pull Request (PR) cho các ứng dụng web Python (trọng tâm là FastAPI và Flask).

### Câu hỏi nghiên cứu trọng tâm
1. *Hiệu quả tương đối giữa các tầng phân tích*: Tầng phân tích tĩnh tất định (Deterministic Static Analysis), mô hình ngôn ngữ lớn xử lý đơn tệp (Single-file LLM), mô hình kết hợp (Hybrid Static + LLM), và mô hình kết hợp có truy xuất ngữ cảnh toàn kho mã nguồn (Repository Context Retrieval) khác biệt như thế nào về độ chính xác (Precision), độ phủ (Recall), và tỷ lệ dương tính giả (FPR)?
2. *Tính khả thi về chi phí và độ trễ*: Liệu việc tích hợp các mô hình phân tích sâu vào CI/CD có đáp ứng được ngưỡng chi phí ($\le 0.05$ USD/PR) và độ trễ chấp nhận được trong thực tế phát triển phần mềm?

---

## 2. Trạng thái hiện tại của hệ thống (Current Implementation Status)

Dự án phân định minh bạch giữa các thành phần **đã hiện thực hóa & kiểm thử**, các thành phần **ở mức thiết kế kiến trúc**, và các thành phần **chưa triển khai**:

| Hạng mục | Trạng thái kỹ thuật | Mô tả chi tiết |
| :--- | :---: | :--- |
| **Static Analysis Engine** | **Đã hiện thực hóa** | Engine tích hợp Ruff và Semgrep CE; chuẩn hóa finding sang schema Pydantic chung; hỗ trợ cơ chế nén phát hiện lặp (suppression). |
| **Local Demo CLI** | **Đã hiện thực hóa** | Công cụ dòng lệnh `tools/demo_audit.py` cho phép quét tĩnh thư mục cục bộ với các tùy chọn `--path`, `--format`, `--severity-threshold`, `--fail-on-findings`. |
| **Core Models & Schemas** | **Đã hiện thực hóa** | Hệ thống thực thể miền Pydantic v2: `AuditRequest`, `NormalizedFinding`, `GroundTruthDefect`, `AuditResult`, ma trận phân loại CWE. |
| **Benchmark Matcher** | **Đã hiện thực hóa** | Thuật toán so khớp locus chuẩn Real-Vuln ($\pm 10$ dòng), ma trận CWE chính/phụ, ghép cặp đồ thị hai phía (bipartite matching) 1-1. |
| **LLM Adapters & Dispatcher** | **Đã hiện thực hóa** | Dispatcher điều phối 4 cấu hình A, B, C, D; bộ đo lường chi phí token và parser đầu ra. |
| **System Architecture Design** | **Đã hoàn thành thiết kế** | Tài liệu thiết kế 5 tầng tại `Project Documents/architecture/system_architecture.md`. |
| **Database Design** | **Đã hoàn thành thiết kế** | Thiết kế lược đồ thực thể quan hệ logic 5 bảng và pgvector; **chưa tạo bảng vật lý hay Alembic migrations**. |
| **REST API Specification** | **Đã hoàn thành thiết kế** | Đặc tả 4 endpoint REST chính; chuẩn hóa định dạng JSON error envelope nội bộ dự án; **chưa triển khai FastAPI routes**. |
| **GitHub Webhook / Actions** | **Chưa triển khai** | Luồng webhook GitHub PR và bot bình luận tự động đang ở giai đoạn thiết kế tích hợp. |

---

## 3. Khung thực nghiệm & Bộ dữ liệu Thí điểm (Pilot Benchmark)

### 3.1. Bộ dữ liệu thí điểm (18 ca kiểm thử)
- Bộ dữ liệu đóng băng tại [`data/pilot_cases.json`](data/pilot_cases.json) gồm **18 ca kiểm thử thực tế** (thu thập từ các kho mã nguồn mở Tornado, FastAPI, Jinja2, Django, aiohttp, Starlette, PyJWT, Authlib, JupyterHub, Zulip, Scrapy, Werkzeug, v.v.) với **23 ground-truth defects** trải đều trên 6 nhóm lỗi mục tiêu (Boundary/Logic, Input Validation, SQL Injection, Path Traversal, Authentication, Authorization).
- Mã băm SHA-256 bảo toàn tính toàn vẹn: `ca6dd7cb99c8c94f44bbbbe9e4e49bcec4800ff4183c7c9330754af806fe0a65`.

### 3.2. Kết quả thực nghiệm 4 cấu hình thí điểm (A, B, C, D)
Kết quả thực nghiệm đã đóng băng tại `data/results/`:
- **Config A (Static Only - Ruff + Semgrep CE)**: 18 ca, phân tích tĩnh tất định lọc theo locus thay đổi.
- **Config B (LLM-Only Single File)**: 18 ca, 100 predictions, TP 6, FP 94, FN 17, Precision 6.00%, Recall 26.09%, F1 9.76%, Chi phí $1.3728.
- **Config C (Hybrid Static + LLM không repo context)**: 18 ca kế hoạch, 17 ca hoàn thành (`CAND-0008` lỗi định dạng JSON), 95 predictions, TP 8, FP 87, FN 15, Precision 8.42%, Recall 34.78%, F1 13.56%, Chi phí $1.3386.
- **So sánh cặp Cấu hình B vs. C (17 ca chung loại bỏ CAND-0008)**:
  - *Config B*: TP 6, FP 86, FN 16, Precision 6.52%, Recall 27.27%, F1 10.53%.
  - *Config C*: TP 8, FP 87, FN 14, Precision 8.42%, Recall 36.36%, F1 13.68%.
  - *Lưu ý*: Các kết quả mang tính mô tả thực nghiệm trên tập thí điểm, chưa khẳng định ý nghĩa thống kê hay quan hệ nhân quả.
- **Config D (Hybrid Static + LLM có Repository Context Retrieval)**: 18 ca, TP 7, FP 85, FN 16, Precision 7.61%, Recall 30.43%, F1 12.17%, Chi phí $1.5271.

### 3.3. Giới hạn thực nghiệm & Thẩm định căn nguyên lỗi (Phase 5E)
- **Giới hạn đo lường ngữ cảnh Config D**: Ngân sách ngữ cảnh dao động từ 607 đến 3,924 tokens dựa trên công thức ước lượng heuristic $\lfloor \text{len} / 3.2 \rfloor + 20$, chưa đo lường bằng tokenizer thực tế.
- **Thẩm định căn nguyên lỗi Phase 5E**: Hồ sơ tại [`Project Documents/dataset/adjudication_review_5e.md`](Project%20Documents/dataset/adjudication_review_5e.md) ghi nhận quyết định thẩm định căn nguyên mang tính khám phá bởi 1 sinh viên (single-student-rater) cho 21 cặp so khớp cơ học TP: **15 ROOT_CAUSE_ALIGNED**, **6 PROXIMITY_ONLY**, **0 INDETERMINATE**. Đây không phải kết quả đồng thuận chuyên gia độc lập hay thử nghiệm mù.

---

## 4. Hướng dẫn Cài đặt & Chạy Thử nghiệm (Setup & Usage)

### 4.1. Yêu cầu môi trường
- Python $\ge$ 3.12
- Quản lý gói: [`uv`](https://docs.astral.sh/uv/) (khuyến nghị) hoặc `pip`

### 4.2. Cài đặt
```bash
# Clone kho lưu trữ
git clone https://github.com/Zikenic/AI-Code-Auditor-Thesis-Progress.git
cd AI-Code-Auditor-Thesis-Progress

# Tạo môi trường ảo và cài đặt dependencies qua uv
uv sync
```

### 4.3. Chạy kiểm thử tự động (Quality Gates)
```bash
# Chạy toàn bộ 140 bài unit test và integration test
uv run pytest

# Kiểm tra chất lượng mã nguồn qua Ruff linter
uv run ruff check .
```

### 4.4. Chạy công cụ kiểm diễn kho mã nguồn cục bộ (Local Demo CLI)
```bash
# Quét tĩnh một thư mục cục bộ với định dạng bảng Rich
uv run python tools/demo_audit.py --path src/auditor/models

# Quét tĩnh và xuất báo cáo JSON
uv run python tools/demo_audit.py --path src/auditor/models --format json --output report.json

# Quét với ngưỡng nghiêm trọng (severity threshold)
uv run python tools/demo_audit.py --path src/auditor/models --severity-threshold high
```

---

## 5. Bảng Theo Dõi Tiến Độ Luận Văn (Progress Workbook)

Bảng tiến độ luận văn chi tiết từ Tuần 1 đến nay được duy trì và tự động tạo tại:  
📊 **[Project Documents/reports/Week_3-4_and_subsequent_progress.xlsx](Project%20Documents/reports/Week_3-4_and_subsequent_progress.xlsx)**

- Bảng tính gồm đầy đủ 19 mục công việc tuần tự với 5 cột chuẩn mực: `STT`, `Nội dung công việc`, `Trạng thái`, `Đánh giá`, `Minh chứng`.
- **100% liên kết minh chứng** trong tệp Excel đều trỏ trực tiếp đến các tệp tài liệu, mã nguồn và kết quả thực nghiệm có thực trên kho lưu trữ công khai này.
- Để tái tạo bảng tính:
  ```bash
  uv run python tools/generate_progress_report.py
  ```

---

## 6. Lưu ý về Bản quyền & Quy tắc An toàn Dữ liệu (Licensing & Redistribution)

- Kho lưu trữ công khai này được chuẩn bị nghiêm ngặt theo các quy tắc an toàn bảo mật và sở hữu trí tuệ:
  - **Không chứa API key, token bí mật hay biến môi trường cá nhân**.
  - **Quy tắc phân tích tĩnh Semgrep**: Tệp quy tắc bên thứ ba `python_security.yaml` (chịu sự chi phối của Semgrep Rules License v1.0) được lưu trữ riêng biệt tại môi trường nghiên cứu nội bộ và không được phân phối công khai trên kho này. Hệ thống static analysis trên bản phát hành công khai hoạt động với Ruff và bộ luật tự định nghĩa, bảo toàn 100% tính hợp lệ của bộ kiểm thử (140/140 unit tests passing).
  - Mọi số liệu thực nghiệm gốc đều được bảo toàn nguyên vẹn với mã băm SHA-256 đối chiếu chuẩn.
