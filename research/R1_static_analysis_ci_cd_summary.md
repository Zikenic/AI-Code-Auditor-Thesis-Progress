# Nghiên cứu R1: Khảo sát Công cụ Phân tích Tĩnh (Static Analysis) và Tích hợp CI/CD

> **Đề tài**: Hệ thống review mã nguồn và phát hiện lỗi tự động (AI Code Auditor)  
> **Tài liệu**: Tổng hợp kết quả nghiên cứu R1 — Ruff vs. Semgrep & GitHub Actions CI/CD  
> **Đối tượng khảo sát**: Các ứng dụng Python Web (FastAPI, Flask)  

---

## 1. Mục tiêu và Câu hỏi Nghiên cứu

Nghiên cứu khảo sát năng lực kỹ thuật, mô hình phân tích cú pháp/ngữ nghĩa, độ sâu bảo mật, khả năng mở rộng, khả năng tích hợp pipeline CI/CD và các giới hạn thực tế của hai công cụ phân tích tĩnh tiêu biểu trong hệ sinh thái Python:
* **Ruff** (Astral Software Inc.)
* **Semgrep** (Semgrep Inc. / r2c)

Câu hỏi trọng tâm: *Trong hệ thống tự động kiểm thử mã nguồn Pull Request (PR) cho các backend Python nhỏ và vừa, Ruff và Semgrep có thể đóng góp những năng lực phân tích cụ thể nào, và đâu là giới hạn kỹ thuật cần được bù đắp bởi tầng LLM kết hợp ngữ cảnh kho mã nguồn (Repo-level Context)?*

---

## 2. Nguồn Minh chứng Sơ cấp (Primary Sources)

Nghiên cứu tuân thủ nghiêm ngặt hệ thống thứ bậc nguồn tin, chỉ sử dụng tài liệu kỹ thuật chính thức và kho mã nguồn gốc:
1. **Ruff**: Tài liệu chính thức (`docs.astral.sh/ruff`), kho mã nguồn `astral-sh/ruff` trên GitHub, các issue theo dõi kiến trúc (`#283`: Hệ thống plugin bên thứ ba; `#7447`: Phân tích ngữ nghĩa đa tệp).
2. **Semgrep**: Tài liệu chính thức (`semgrep.dev/docs`), kho mã nguồn `semgrep/semgrep`, hệ thống luật Semgrep Registry, và tài liệu đặc tả CWE/OWASP.
3. **CI/CD**: Tài liệu chính thức GitHub Actions (`docs.github.com/en/actions`), các action chính thức `astral-sh/ruff-action` và `semgrep/semgrep-action`.

---

## 3. So sánh Năng lực Kỹ thuật Cốt lõi

| Tiêu chí | Ruff (v0.6+) | Semgrep (Community Edition v1.80+) |
| :--- | :--- | :--- |
| **Công nghệ lõi** | Rust (trình phân tích cú pháp `ruff_python_ast` chuyên dụng) | OCaml / Python (dựa trên Tree-sitter CST và AST nội bộ) |
| **Mô hình phân tích** | Single-pass intra-file AST visitor & token stream | Pattern-matching ngữ nghĩa đa ngôn ngữ & Intra-file Taint Analysis |
| **Phạm vi phân tích** | Từng tệp độc lập (Intra-file strictly) | Từng tệp độc lập trong bản Community (Cross-file thuộc bản Pro thương mại) |
| **Hệ thống luật** | Tích hợp sẵn >900 luật (tương đương Flake8, Bandit, Pyupgrade) | Luật mở viết bằng YAML theo cú pháp mẫu mã nguồn gốc |
| **Theo dõi dòng dữ liệu (Taint)** | Không hỗ trợ (Chỉ kiểm tra mẫu cú pháp bề mặt) | Hỗ trợ theo dõi luồng dữ liệu Source -> Sink -> Sanitizer trong nội bộ tệp |
| **Ánh xạ lỗ hổng (CWE / OWASP)** | Cần tự ánh xạ từ mã lỗi Flake8-Bandit (`S` series) | Tích hợp trực tiếp metadata chuẩn CWE và OWASP trong từng luật |
| **Thời gian thực thi** | Cực nhanh (mức mili-giây, phù hợp gating pre-commit/PR) | Nhanh đối với tệp đơn (chậm hơn Ruff do phân tích luồng dữ liệu) |

---

## 4. Phân tích Chi tiết Từng Công cụ

### 4.1 Ruff
* **Thế mạnh**: Tốc độ xử lý vượt trội nhờ viết bằng Rust; thay thế toàn diện các linter truyền thống (Flake8, Pylint, isort); phát hiện nhanh các vi phạm chuẩn mã nguồn (PEP 8), các mẫu cú pháp lỗi thời (`UP` rules), và các "mùi mã nguồn" bảo mật cơ bản thông qua bộ luật `flake8-bandit` (`S101`–`S703`).
* **Hạn chế kỹ thuật**:
  * Không xây dựng Đồ thị luồng điều khiển (Control Flow Graph - CFG) và không theo dõi dòng dữ liệu (Data-flow / Taint tracking). Ví dụ: luật `S608` cảnh báo việc nối chuỗi trong câu lệnh SQL, nhưng Ruff không thể xác định biến đó là hằng số an toàn hay dữ liệu từ người dùng.
  * Chỉ phân tích cục bộ trong từng tệp đơn lẻ; không giải quyết được các phụ thuộc hoặc định nghĩa symbol xuyên tệp (Issue `#7447`).
  * Chưa hỗ trợ hệ thống plugin bên thứ ba tùy biến (Issue `#283`).

### 4.2 Semgrep Community Edition
* **Thế mạnh**: Khả năng biểu đạt mẫu kiểm tra ngữ nghĩa mạnh mẽ; cú pháp viết luật trực quan (`$X == $X`, `...`); hỗ trợ chế độ `mode: taint` cho phép phát hiện các lỗ hổng tiêm mã (SQL Injection, Path Traversal, Command Injection) khi dữ liệu chưa qua khử nhiễm (sanitizer) đi vào điểm nhạy cảm (sink).
* **Hạn chế kỹ thuật**:
  * Bản mã nguồn mở (Community Edition) chỉ hỗ trợ phân tích luồng dữ liệu liên thủ tục trong nội bộ tệp (inter-procedural intra-file). Phân tích liên tệp (inter-file taint tracking) bị giới hạn trong phiên bản thương mại Semgrep Pro.
  * Không thể suy luận ngữ cảnh nghiệp vụ phức tạp hoặc hiểu được các ràng buộc logic đa bước xuyên suốt repository.

---

## 5. Tích hợp Pipeline CI/CD (GitHub Actions)

Cả hai công cụ đều hỗ trợ tích hợp native và hiệu quả trong môi trường CI/CD:
1. **Triggering**: Kích hoạt trên sự kiện `pull_request` (đặc biệt là các action `opened`, `synchronize`).
2. **Scoping**:
   * Ruff hỗ trợ kiểm tra chỉ trên các tệp thay đổi trong PR: `git diff --name-only origin/main | xargs ruff check`.
   * Semgrep hỗ trợ chế độ `semgrep scan --diff` để chỉ quét các đoạn thay đổi.
3. **Định dạng xuất kết quả**: Cả hai đều hỗ trợ định dạng JSON và SARIF (Static Analysis Results Interchange Format), cho phép nạp trực tiếp kết quả vào GitHub Code Scanning Alert hoặc chuyển tiếp tới module tổng hợp (Findings Aggregator).

---

## 6. Kết luận & Định hướng Tích hợp Hệ thống (Hybrid Audit)

Kết quả khảo sát khẳng định:
1. **Tính bổ trợ cao**: Ruff đóng vai trò "bộ lọc bước đầu" (first-line filter) dọn dẹp các lỗi cú pháp, vi phạm style và smell cơ bản với độ trễ tối thiểu. Semgrep đóng vai trò "bộ quét bảo mật ngữ nghĩa cục bộ" (local semantic SAST) phát hiện các mẫu vi phạm luồng dữ liệu đã biết trong tệp.
2. **Khoảng trống ngữ cảnh đa tệp**: Cả hai công cụ mã nguồn mở đều không thể xử lý suy luận xuyên tệp hoặc phân tích các lỗi logic nghiệp vụ phức tạp trên Pull Request.
3. **Vai trò của LLM & Repo RAG**: Tầng LLM Orchestration kết hợp với cơ chế truy xuất ngữ cảnh repository (Repo-level Context) là thành phần bắt buộc để lấp đầy khoảng trống phân tích đa tệp, thực hiện rà soát các danh mục lỗi logic biên, ủy quyền (BOLA/IDOR), và xác thực phức tạp.
