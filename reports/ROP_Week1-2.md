# BÁO CÁO TIẾN ĐỘ THỰC HIỆN ĐỀ TÀI KHÓA LUẬN TỐT NGHIỆP
## Giai đoạn: Tuần 1 – Tuần 2 (07/09/2026 – 20/09/2026)

---

## I. THÔNG TIN CHUNG

- **Tên đề tài tiếng Việt**: Nghiên cứu, xây dựng hệ thống tự động đánh giá và phát hiện lỗi trong mã nguồn trên môi trường Pull Request
- **Tên đề tài tiếng Anh**: Research and Development of an Automated Code Review and Bug Detection System for Pull Request Environments
- **Sinh viên thực hiện**: Bùi Vạn Khải — MSSV: 24520719
- **Giảng viên hướng dẫn**: ThS. Trần Thị Hồng Yến
- **Đơn vị đào tạo**: Khoa Kỹ thuật Phần mềm — Trường Đại học Công nghệ Thông tin, ĐHQG-HCM
- **Thời gian thực hiện**: Học kỳ 1, Năm học 2026–2027
- **Kho lưu trữ minh chứng báo cáo (GitHub)**: [AI-Code-Auditor-Thesis-Progress](https://github.com/Zikenic/AI-Code-Auditor-Thesis-Progress)

---

## II. MỤC TIÊU VÀ KẾ HOẠCH GIAI ĐOẠN TUẦN 1–2

Giai đoạn 2 tuần đầu tiên tập trung hoàn thiện toàn bộ nền tảng lý thuyết, khảo sát công nghệ, xác lập yêu cầu kỹ thuật và chuẩn hóa phương pháp luận đánh giá thực nghiệm cho đề tài. Mục tiêu cụ thể bao gồm:

1. **Khảo sát công cụ phân tích tĩnh (Static Analysis)**: So sánh đối sánh giữa Ruff và Semgrep Community Edition để tối ưu hóa tầng kiểm tra cú pháp và phát hiện lỗi bảo mật nội bộ trong tệp.
2. **Khảo sát cơ chế thu thập ngữ cảnh toàn kho mã nguồn (Repository Context Retrieval)**: Nghiên cứu các phương pháp trích xuất đồ thị gọi AST, phân tích phụ thuộc module và kỹ thuật RAG (Retrieval-Augmented Generation) kết hợp vector embedding (pgvector).
3. **Phân loại lỗi và điểm yếu bảo mật (CWE Taxonomy)**: Khảo sát chuẩn MITRE CWE nhằm xác định ánh xạ chính xác cho 6 nhóm lỗi mục tiêu trong môi trường ứng dụng web Python (FastAPI và Flask).
4. **Xây dựng đặc tả yêu cầu hệ thống**: Soạn thảo tài liệu đặc tả yêu cầu chức năng (FR) và phi chức năng (NFR) cho hệ thống AI Code Auditor tích hợp GitHub Actions.
5. **Thiết kế bộ dữ liệu Benchmark & Phương pháp luận đánh giá**: Xây dựng lược đồ kiểm thử, tiêu chí ground-truth, quy tắc phân chia tập Dev/Test (30/70) và chuẩn hóa dung sai so khớp locus ($\pm 10$ dòng) theo tiêu chuẩn Real-Vuln-Benchmark.
6. **Khóa phương pháp luận nghiên cứu**: Xác định rõ ràng phạm vi đã được Giảng viên hướng dẫn xác nhận và các quyết định kỹ thuật chuyên môn do sinh viên hoàn thiện.

---

## III. BẢNG TỔNG HỢP TIẾN ĐỘ THỰC HIỆN TUẦN 1–2

Dưới đây là bảng tổng hợp tiến độ và đánh giá kết quả thực hiện của 8 khối công việc trọng tâm trong mốc thời gian Tuần 1–2:

| STT | Nội dung công việc | Trạng thái | Đánh giá | Minh chứng |
| :---: | :--- | :---: | :--- | :--- |
| **1** | **Xác lập phạm vi đề tài & Kế hoạch tổng thể**<br>- Định hình kiến trúc 4 cấu hình thử nghiệm (A, B, C, D).<br>- Phân bổ lộ trình thực hiện theo tuần. | **Hoàn thành** | Kế hoạch chi tiết, định rõ mục tiêu nghiên cứu và sự khác biệt giữa các cấu hình đánh giá thực nghiệm. | [benchmark_methodology.md](https://github.com/Zikenic/AI-Code-Auditor-Thesis-Progress/blob/main/methodology/benchmark_methodology.md) |
| **2** | **Khảo sát công cụ phân tích tĩnh (Static Analysis)**<br>- Đánh giá Ruff vs. Semgrep CE.<br>- Đo đạc hiệu năng, độ trễ và khả năng tích hợp CI/CD. | **Hoàn thành** | Phân tích sâu 10 tiêu chí kỹ thuật; kết luận mô hình phân lớp kết hợp: Ruff quét nhanh cú pháp/Bandit, Semgrep quét taint/AST nội tệp. | [R1_static_analysis_ci_cd_summary.md](https://github.com/Zikenic/AI-Code-Auditor-Thesis-Progress/blob/main/research/R1_static_analysis_ci_cd_summary.md) |
| **3** | **Khảo sát truy xuất ngữ cảnh Repository (Repo RAG & AST)**<br>- Khảo sát AST Call Graph, Jedi, Tree-sitter.<br>- Khảo sát Vector RAG (pgvector, text-embedding-3-small). | **Hoàn thành** | Xác lập kiến trúc ngữ cảnh hybrid: AST Graph phục vụ phân giải định nghĩa/call-site chính xác, Vector RAG phục vụ ngữ cảnh tài liệu và framework. | [R2_repo_context_rag_summary.md](https://github.com/Zikenic/AI-Code-Auditor-Thesis-Progress/blob/main/research/R2_repo_context_rag_summary.md) |
| **4** | **Nghiên cứu phân loại điểm yếu bảo mật (CWE Taxonomy)**<br>- Ánh xạ 6 nhóm lỗi mục tiêu sang chuẩn MITRE CWE.<br>- Phân định ranh giới giữa kiểm tra đầu vào và lỗi tiêm lệnh (injection). | **Hoàn thành** | Ánh xạ chi tiết 17 mã CWE cụ thể; giải quyết triệt để ranh giới nhập nhằng giữa CWE-20 và CWE-89/22; loại bỏ CWE-285 quá trừu tượng. | [CWE_taxonomy_summary.md](https://github.com/Zikenic/AI-Code-Auditor-Thesis-Progress/blob/main/research/CWE_taxonomy_summary.md) |
| **5** | **Xây dựng đặc tả yêu cầu hệ thống (FR & NFR)**<br>- Soạn thảo 10 yêu cầu chức năng (FR-01 đến FR-10).<br>- Soạn thảo 7 yêu cầu phi chức năng (NFR-01 đến NFR-07). | **Hoàn thành** | Đặc tả hoàn chỉnh theo mẫu kiểm thử được (testable schema), xác định rõ luồng xử lý PR, chi phí token, độ trễ CI và ngưỡng đánh giá. | [functional_nonfunctional_requirements.md](https://github.com/Zikenic/AI-Code-Auditor-Thesis-Progress/blob/main/requirements/functional_nonfunctional_requirements.md) |
| **6** | **Thiết kế bộ dữ liệu Benchmark & Lược đồ ca kiểm thử**<br>- Xác lập quy mô tối thiểu 100 ca (50 Buggy / 50 Clean).<br>- Thiết kế lược đồ metadata 16 trường chuẩn. | **Hoàn thành** | Bộ khung benchmark chặt chẽ, cân bằng 6 nhóm lỗi, phân bổ độ phức tạp đơn tệp/đa tệp (~50/50), quy định kiểm tra hồi quy độc lập. | [dataset_design_test_case_list.md](https://github.com/Zikenic/AI-Code-Auditor-Thesis-Progress/blob/main/dataset/dataset_design_test_case_list.md) |
| **7** | **Xác lập quy tắc so khớp & Tiêu chí đo lường**<br>- Áp dụng dung sai $\pm 10$ dòng locus theo chuẩn Real-Vuln.<br>- Xác lập quy tắc tiêu thụ 1-1 và tính lỗi FP. | **Hoàn thành** | Quy tắc so khớp khách quan, cơ chế tính điểm tự động hóa dựa trên file chuẩn hóa, CWE pre-declared và tọa độ dòng lỗi. | [benchmark_methodology.md](https://github.com/Zikenic/AI-Code-Auditor-Thesis-Progress/blob/main/methodology/benchmark_methodology.md) |
| **8** | **Khóa phương pháp luận nghiên cứu (Methodology Finalization)**<br>- Đồng bộ hóa toàn bộ tài liệu dự án.<br>- Phân định rõ phạm vi GVHD xác nhận và phương pháp luận kỹ thuật. | **Hoàn thành** | Toàn bộ các quyết định phương pháp luận làm việc đã được chuyển trạng thái chính thức, tạo tiền đề vững chắc cho việc thu thập ca kiểm thử. | [benchmark_methodology.md](https://github.com/Zikenic/AI-Code-Auditor-Thesis-Progress/blob/main/methodology/benchmark_methodology.md) |

---

## IV. CHI TIẾT CÁC KẾT QUẢ ĐẠT ĐƯỢC TRONG TUẦN 1–2

### 1. Khảo sát công cụ phân tích tĩnh (Static Analysis: Ruff vs. Semgrep CE)
- **Ruff**: Thể hiện tốc độ vượt trội (vài chục mili-giây trên toàn kho mã), tối ưu cho việc kiểm tra chất lượng mã (linting), chuẩn phong cách (PEP 8) và tích hợp các luật Flake8-bandit.
- **Semgrep Community Edition**: Cung cấp khả năng phân tích ngữ nghĩa nội tệp mạnh mẽ qua cây cú pháp trừu tượng (AST) và khả năng theo vết luồng dữ liệu (taint tracking `mode: taint`).
- **Kết luận kiến trúc**: Hệ thống không lựa chọn thay thế mà triển khai mô hình **phân tầng cộng tác**: Ruff đóng vai trò "người gác cổng" tốc độ cao lọc bỏ các lỗi cú pháp cơ bản; Semgrep CE tập trung phát hiện các mẫu vi phạm bảo mật và luồng dữ liệu bẩn nội bộ trước khi chuyển ngữ cảnh lên tầng LLM.

### 2. Khảo sát thu thập ngữ cảnh mã nguồn (Repository Context Retrieval)
- **Hạn chế của phương pháp đơn lẻ**: Gửi toàn bộ repository vào LLM gây bùng nổ chi phí token, vượt cửa sổ ngữ cảnh và làm tăng hiện tượng "ảo giác" (hallucination); trong khi chỉ đọc file diff đơn lẻ khiến LLM không thể phát hiện các lỗi vi phạm phụ thuộc xuyên tệp (cross-file).
- **Giải pháp Hybrid**: Kết hợp phân tích cấu trúc tất định (AST / Call Graph qua Jedi/Tree-sitter để trích xuất chữ ký hàm, lớp cha, định nghĩa kiểu) và truy xuất ngữ nghĩa (pgvector embedding để tìm kiếm tài liệu dự án, cấu hình bảo mật liên quan).

### 3. Phân loại 6 nhóm lỗi mục tiêu và ánh xạ CWE
Sáu nhóm lỗi mục tiêu được xác định và bảo toàn tính toàn vẹn:
1. **Lỗi biên, điều kiện và logic điều khiển** (*Boundary / Conditional / Logic*): CWE-193 (Off-by-one), CWE-476 (Null/None Dereference), CWE-670 (Control Flow). Bổ sung thuộc tính trực giao $\text{impact} \in \{\text{functional}, \text{security}\}$ để phân tách lỗi tính đúng đắn chức năng và lỗi bảo mật.
2. **Kiểm tra và làm sạch dữ liệu đầu vào** (*Input Validation & Sanitization*): CWE-20, CWE-116, CWE-1287. Xác lập nguyên tắc phân định: chỉ gán CWE-20 khi lỗi nằm ở tầng kiểm tra cấu trúc/schema dữ liệu; nếu dữ liệu dẫn trực tiếp tới sink SQL hoặc tệp tin thì phải gán mã lỗi injection tương ứng.
3. **Tiêm lệnh SQL / ORM** (*SQL / ORM Injection*): CWE-89, CWE-943. Xác nhận việc sử dụng ORM (SQLAlchemy `session.execute(text(...))`) nhưng ghép chuỗi thô vẫn được định danh chính thức là CWE-89.
4. **Duyệt đường dẫn và thao tác tệp không an toàn** (*Path Traversal / Unsafe File Ops*): CWE-22, CWE-73, CWE-434. Phân định rõ giữa việc thoát khỏi thư mục chỉ định (CWE-22) và việc kiểm soát tên tệp gây ghi đè tệp nhạy cảm (CWE-73).
5. **Lỗi xác thực** (*Missing / Broken Authentication*): CWE-306, CWE-287, CWE-347. Phân biệt rõ điểm cuối thiếu cơ chế xác thực (CWE-306) và xác thực sai quy cách (CWE-347 trong kiểm tra JWT).
6. **Lỗi phân quyền** (*Missing / Broken Authorization*): CWE-862 (Missing AuthZ), CWE-863 (Incorrect AuthZ), CWE-639 (IDOR/BOLA). Tránh sử dụng mã bao trùm CWE-285 do khuyến nghị của MITRE.

### 4. Đặc tả yêu cầu kỹ thuật & Thiết kế Benchmark
- **Đặc tả 10 yêu cầu chức năng (FR-01 đến FR-10)**: Bao quát toàn trình từ tiếp nhận Pull Request qua webhook, trích xuất diff, thực thi phân tích tĩnh, truy xuất ngữ cảnh, gọi mô hình ngôn ngữ lớn, khử trùng lặp và phản hồi nhận xét trực tiếp lên GitHub PR.
- **Đặc tả 7 yêu cầu phi chức năng (NFR-01 đến NFR-07)**: Quy định nghiêm ngặt về độ trễ quy trình CI ($\le 180$ giây), giới hạn chi phí token ($\le 0.05$ USD/PR), tính tái lập của benchmark và bảo mật an toàn thông tin (không để lọt mã nguồn hay API key).
- **Quy chuẩn Benchmark**: Sàn quy mô tối thiểu 100 ca kiểm thử, tỷ lệ 50% lỗi / 50% mã sạch; tỷ lệ phân chia 30% tập Phát triển (Dev) / 70% tập Kiểm thử (Test); áp dụng quy tắc gom nhóm theo họ repository để chống rò rỉ dữ liệu (data leakage).

---

## V. ĐỊNH HƯỚNG XÁC NHẬN CỦA GVHD VS. PHƯƠNG PHÁP LUẬN ĐÃ KHÓA

Nhằm đảm bảo tính minh bạch và tính chuẩn xác trong nghiên cứu khoa học, đề tài phân định rõ ràng giữa các định hướng cơ bản đã được Giảng viên hướng dẫn xác nhận và các quyết định kỹ thuật chuyên môn do sinh viên hoàn thiện:

### 1. Định hướng cốt lõi đã được GVHD phê duyệt / xác nhận
- **Tên và mục tiêu đề tài**: Xây dựng hệ thống tự động kiểm tra và đánh giá mã nguồn trong môi trường Pull Request.
- **Môi trường ứng dụng mục tiêu**: Mã nguồn ứng dụng web viết bằng Python (trọng tâm là FastAPI và Flask).
- **Khung thực nghiệm so sánh 4 cấu hình**:
  - Cấu hình A: Chỉ phân tích tĩnh tất định (Ruff + Semgrep CE).
  - Cấu hình B: Chỉ LLM với ngữ cảnh tệp đơn.
  - Cấu hình C: Kết hợp Static + LLM nhưng không có ngữ cảnh toàn kho.
  - Cấu hình D: Kết hợp Static + LLM và có truy xuất ngữ cảnh repository (AST + Vector RAG).
- **Phương thức tích hợp thực tế**: Tích hợp trực tiếp qua GitHub Actions CI/CD nhằm đánh giá tính khả thi trong thực tế phát triển phần mềm.

### 2. Phương pháp luận kỹ thuật đã được sinh viên khóa chính thức
- **Phân loại 6 nhóm lỗi**: Khóa danh mục 6 nhóm lỗi cụ thể, không tùy tiện mở rộng trừ khi xuất hiện bằng chứng thực tế thuyết phục trong quá trình thu thập.
- **Quy tắc so khớp locus $\pm 10$ dòng**: Tiếp thu trực tiếp từ phương pháp luận của Real-Vuln-Benchmark ([Real-Vuln-Benchmark](https://github.com/kolega-ai/Real-Vuln-Benchmark)), đảm bảo so khớp tự động, khách quan và loại trừ thiên vị chủ quan.
- **Quy mô và tỷ lệ tập dữ liệu**: Xác lập sàn tối thiểu 100 ca kiểm thử; chia 30% Dev (30 ca) và 70% Test (70 ca) độc lập, cô lập theo repository.
- **Mục tiêu định lượng thực nghiệm**: Thiết lập các ngưỡng kỳ vọng kỹ thuật: Precision $\ge 75\%$, Recall $\ge 60\%$, $F_1 \ge 0.67$, False Positive Rate trên PR sạch $\le 20\%$.

---

## VI. TIẾN ĐỘ TRIỂN KHAI BỔ SUNG SAU MỐC TUẦN 2 (POST-WEEK 2 EXPANSION)

Sau khi hoàn thành và khóa toàn bộ tài liệu phương pháp luận của mốc Tuần 1–2, sinh viên đã chủ động tiến hành ngay các bước chuẩn bị thực địa cho Giai đoạn 2 (Xây dựng Bộ dữ liệu Benchmark). Các kết quả đạt được bao gồm:

### 1. Thiết lập quy trình tiếp nhận ứng viên (Candidate-Ingestion Workflow)
- Xây dựng quy trình 5 bước nghiêm ngặt: Phát hiện ứng viên $\rightarrow$ Đối chiếu mã nguồn gốc (Primary Source) $\rightarrow$ Tách biệt vị trí lỗi (Locus Isolation) $\rightarrow$ Kiểm tra tái lập lỗi (Regression Reproducer) $\rightarrow$ Phê duyệt vào hàng đợi.
- Thiết lập cổng kiểm soát chất lượng (Quality Gate): Chỉ tiếp nhận các ứng viên có commit sửa lỗi nguyên tử (atomic fix), có mã nguồn công khai, và có kiểm thử hồi quy độc lập (Level A/B).

### 2. Thu thập và sàng lọc sơ bộ 36 ứng viên (Phase 1 Candidate Discovery)
- Khảo sát các kho mã nguồn Python mã nguồn mở phổ biến (FastAPI, Flask, Starlette, Tornado, Jinja2, Django, Zulip, Authlib, PyJWT, v.v.).
- Lập hồ sơ chi tiết cho **36 ứng viên lỗi tiềm năng** (`CAND-0001` đến `CAND-0036`) trải đều trên cả 6 nhóm lỗi mục tiêu.
- Thẳng thắn loại bỏ **7 ứng viên không đạt chuẩn** (`REJ-0001` đến `REJ-0007`) do các lý do: commit quá lớn/refactor diện rộng, thiếu test tái lập lỗi, hoặc ngoài phạm vi công nghệ Python web backend.

### 3. Thử nghiệm kiểm chứng thực địa trên 12 ca thí điểm (Phase 2 Pilot Validation)
- Triển khai thí điểm xác thực Ground-Truth trên **12 ứng viên (đúng 2 ca cho mỗi nhóm lỗi)** để kiểm tra tính khả thi của quy trình đo đạc:
  - **Nhóm 1 (Logic)**: `CAND-0001` (Tornado - lỗi cờ chunking HTTP), `CAND-0002` (FastAPI - bỏ quên dependency override trên WebSocket).
  - **Nhóm 2 (Validation)**: `CAND-0007` (FastAPI - bỏ lọt Content-Type validation dẫn tới CSRF qua JSON body), `CAND-0009` (Jinja2 - tiêm thuộc tính HTML/XML qua bộ lọc `xmlattr`).
  - **Nhóm 3 (SQL Injection)**: `CAND-0014` (Django - tiêm SQL qua datetime truncate), `CAND-0017` (Tortoise ORM - ghép chuỗi SQL thô trong MySQL executor).
  - **Nhóm 4 (Path Traversal)**: `CAND-0019` (aiohttp - directory traversal qua URL dispatcher), `CAND-0021` (Starlette - path traversal qua static files).
  - **Nhóm 5 (Authentication)**: `CAND-0025` (PyJWT - bypass xác thực khóa bất đối xứng), `CAND-0027` (Authlib - lỗi xác thực chữ ký cryptographic).
  - **Nhóm 6 (Authorization)**: `CAND-0031` (JupyterHub - phân quyền người dùng không an toàn), `CAND-0032` (Zulip - lỗi kiểm tra quyền truy cập tin nhắn IDOR/BOLA).

### 4. Đánh giá và điều chỉnh phân loại chuyên sâu (Audit CAND-0036 & CAND-0032)
- Trong quá trình rà soát chi tiết, ca `CAND-0036` (Django CVE-2020-13254) ban đầu được xếp vào Nhóm 6 (Authorization). Tuy nhiên, khi đối chiếu commit gốc, lỗi bản chất là do Memcached cache key không được kiểm tra ký tự đặc biệt dẫn tới xung đột khóa nhớ đệm (cache key collision).
- Do đó, sinh viên đã **tái phân loại chính xác CAND-0036 về Nhóm 2 (Input Validation & Sanitization)** với mã CWE-20, và lựa chọn **CAND-0032 (Zulip message access control — CWE-863 / CWE-639)** làm ca thí điểm chuẩn mực cho Nhóm 6.
- Minh chứng chi tiết: [ground_truth_validation_pilot.md](https://github.com/Zikenic/AI-Code-Auditor-Thesis-Progress/blob/main/dataset/ground_truth_validation_pilot.md).

---

## VII. KẾ HOẠCH TRIỂN KHAI GIAI ĐOẠN TIẾP THEO

Trong các tuần tiếp theo, sinh viên sẽ tiếp tục triển khai các nội dung:

1. **Mở rộng thu thập bộ dữ liệu Benchmark (Giai đoạn 2 toàn diện)**:
   - Tiếp tục xử lý 24 ứng viên còn lại trong hàng đợi `candidate_queue.md`.
   - Thu thập thêm các ứng viên mới từ các kho mã nguồn thực tế để đạt sàn **100 ca kiểm thử** (bao gồm 50 ca lỗi và 50 ca sạch).
   - Đóng gói các tệp patch diff, môi trường kiểm thử Docker/pytest cho từng ca kiểm thử.
2. **Xây dựng khung thực nghiệm tự động hóa (Test Harness Engine)**:
   - Lập trình module nạp diff và tương tác với GitHub API/mock webhook.
   - Hiện thực hóa bộ so khớp finding tự động (Automated Ground-Truth Matcher) theo chuẩn $\pm 10$ dòng và ma trận CWE.
3. **Hiện thực hóa 4 cấu hình thử nghiệm (Configs A, B, C, D)**:
   - Tích hợp bộ quy tắc Ruff và Semgrep CE vào pipeline CI (Cấu hình A).
   - Xây dựng prompt template tối ưu và client tương tác mô hình LLM (Cấu hình B & C).
   - Tích hợp module phân tích AST Call Graph và pgvector để truy xuất ngữ cảnh dự án (Cấu hình D).

---

## VIII. KẾT LUẬN & ĐỀ XUẤT Ý KIẾN TỪ GIẢNG VIÊN HƯỚNG DẪN

Giai đoạn Tuần 1–2 đã hoàn thành 100% khối lượng công việc đặt ra với chất lượng học thuật và kỹ thuật cao. Các tài liệu nghiên cứu cơ sở, đặc tả yêu cầu và phương pháp luận đánh giá đã được chuẩn hóa, thẩm định chéo và lưu trữ an toàn.

Sinh viên kính mong nhận được ý kiến đánh giá và đóng góp từ Giảng viên hướng dẫn:
- Đánh giá tổng thể về cơ sở phương pháp luận và tính khả thi của quy chuẩn đo lường thực nghiệm.
- Ý kiến chỉ đạo về quy mô bộ dữ liệu benchmark (sàn 100 ca hiện tại) và định hướng thu thập các ca kiểm thử chuyên sâu cho framework FastAPI/Flask.
