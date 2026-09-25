# Nghiên cứu R2: Khảo sát Ngữ cảnh Repository (Repo-level Context) & RAG cho Đánh giá Pull Request

> **Đề tài**: Hệ thống review mã nguồn và phát hiện lỗi tự động (AI Code Auditor)  
> **Tài liệu**: Tổng hợp kết quả nghiên cứu R2 — Repo-level Context, Code Graph & Repo RAG  
> **Đối tượng khảo sát**: Ứng dụng Python Web (FastAPI, Flask, SQLAlchemy)  

---

## 1. Đặt vấn đề và Mục tiêu Nghiên cứu

Khi lập trình viên mở một Pull Request (PR), các thay đổi thường liên quan đến nhiều tệp: sửa đổi hàm xử lý, thay đổi cấu trúc bảng cơ sở dữ liệu (ORM), cập nhật phụ thuộc ủy quyền hoặc giao thức mạng. Việc chỉ đưa đoạn mã sửa đổi (diff hunk) hoặc từng tệp đơn lẻ vào LLM sẽ dẫn đến hiện tượng thiếu ngữ cảnh (context starvation), khiến mô hình đưa ra cảnh báo sai (False Positive) hoặc bỏ sót lỗi nghiêm trọng (False Negative).

Nghiên cứu R2 khảo sát có hệ thống các phương pháp thu thập và biểu diễn ngữ cảnh repository có định hướng cho PR review:
1. **Trích xuất ký hiệu và cây cú pháp trừu tượng (AST & Symbol Extraction)**
2. **Đồ thị cấu trúc kho mã nguồn (Code Graphs: Import, Dependency & Call Graph)**
3. **Truy xuất ngữ nghĩa dựa trên nhúng véc-tơ (Dense Semantic Retrieval & pgvector)**
4. **Phương pháp kết hợp lai (Hybrid Retrieval: Structure-first + Semantic Expansion)**

---

## 2. Nguồn Minh chứng Học thuật & Kỹ thuật Sơ cấp

Nghiên cứu đã trải qua quy trình kiểm tra đối chiếu nguồn nghiêm ngặt, loại bỏ các tài liệu chưa xác minh và chuẩn hóa các trích dẫn học thuật sơ cấp:
* **Tài liệu đặc tả CPython `ast`**: Python Software Foundation (2026), tài liệu chính thức về ngữ pháp ASDL và cấu trúc nút AST.
* **Tài liệu `pgvector`**: PostgreSQL Global Development Group (2026), thông số kỹ thuật về chỉ mục HNSW/IVFFlat và tìm kiếm véc-tơ định danh trong cơ sở dữ liệu quan hệ.
* **AACR-Bench** (Zhang et al., 2026): *Evaluating Agentic Automated Code Review with Repository-Level Context*, arXiv:2603.21852.
* **DyRetriever** (Liu et al., 2026): *Dynamic Context-Aware Retrieval for Code Review via Structural Dependency Traversal*, arXiv:2602.14890.

---

## 3. Tổng hợp Kết quả Nghiên cứu Theo Bốn Trục Kỹ thuật

### 3.1 Trích xuất Ký hiệu Dựa trên AST (AST & Symbol Extraction)
* **Khả năng**:
  * Sử dụng thư viện `ast` chuẩn của Python hoặc `tree-sitter` để trích xuất các thành phần cú pháp chính xác: định nghĩa hàm (`FunctionDef`), lớp (`ClassDef`), chữ ký tham số, kiểu dữ liệu trả về (`annotation`), docstring, và danh sách các câu lệnh import (`Import`, `ImportFrom`).
  * **Slicing diff theo AST**: Bằng cách đối chiếu khoảng dòng thay đổi trong Git diff (`@@ -start,len +start,len @@`) với tọa độ dòng (`lineno`, `end_lineno`) của các nút AST, hệ thống có thể neo chính xác dòng thay đổi vào đúng hàm/lớp bao chứa thay vì gửi các đoạn mã rời rạc.
* **Giới hạn**:
  * AST chỉ phân tích trong phạm vi một tệp đơn. AST biết tên hàm được gọi nhưng không biết hàm đó được định nghĩa ở tệp nào trong kho mã nguồn nếu không có bảng ký hiệu toàn cục (global symbol table).
  * AST nguyên bản của Python bỏ qua comment và định dạng; nếu cần tái cấu trúc chính xác thì cần tới Concrete Syntax Tree (CST như `libcst` hoặc `tree-sitter`).

### 3.2 Đồ thị Cấu trúc (Code Graphs: Dependency & Call Graphs)
* **Mô hình biểu diễn**:
  * **Đồ thị Import (Module-level Import Graph)**: Xác định mối quan hệ phụ thuộc giữa các module trong repository.
  * **Đồ thị Gọi hàm Tĩnh (Static Call Graph)**: Biểu diễn các cạnh gọi từ caller đến callee.
* **Thách thức từ tính động của Python**:
  * Python có tính động cao: dynamic dispatch, decorator lồng nhau (đặc biệt phổ biến trong FastAPI routing `@app.get` hay Flask `@app.route`), nạp module runtime (`importlib`), và monkey patching.
  * *Kết luận*: Đồ thị tĩnh cung cấp "bộ khung xác định" nhưng không thể giải quyết tuyệt đối 100% các liên kết động; cần kết hợp với phân tích heuristic và truy xuất ngữ nghĩa mở rộng.

### 3.3 Truy xuất Ngữ nghĩa & Vai trò của PostgreSQL `pgvector`
* **Chiến lược Chunking**:
  * Không nên chia đoạn theo số dòng cố định (sliding window 200 dòng) vì làm gãy cấu trúc logic của hàm và lớp.
  * Cần áp dụng **Symbol-level Semantic Chunking**: mỗi chunk tương ứng với một đơn vị logic hoàn chỉnh (hàm, method, lớp, hoặc tài liệu cấu hình Pydantic/SQLAlchemy) kèm metadata ngữ cảnh (đường dẫn tệp, tên lớp, module).
* **Vai trò của `pgvector`**:
  * `pgvector` đóng vai trò là tầng lưu trữ và tìm kiếm véc-tơ hiệu năng cao (sử dụng chỉ mục HNSW) tích hợp trực tiếp trong PostgreSQL.
  * Lợi thế cốt lõi trong hệ thống: cho phép truy vấn kết hợp véc-tơ ngữ nghĩa với các bộ lọc thuộc tính quan hệ (Metadata Filtering: lọc theo module, đường dẫn tệp, phiên bản commit) trong cùng một câu lệnh SQL duy nhất mà không cần duy trì hai hệ quản trị riêng biệt.
* **Điểm yếu của truy xuất thuần ngữ nghĩa (Dense Retrieval Only)**:
  * Không có khả năng hiểu được quan hệ chuỗi gọi hàm (call graph path). Hai đoạn mã có thể rất tương đồng về mặt văn bản/khái niệm nhưng không hề có quan hệ phụ thuộc logic trong PR. Do đó, RAG cho code bắt buộc phải có ràng buộc cấu trúc (structural constraints).

### 3.4 Định hướng Kết hợp Lai (Hybrid Retrieval Architecture)
* **Quy trình tối ưu cho PR Review**:
  1. *Bước 1 (Gốc thay đổi)*: Xác định tập ký hiệu bị ảnh hưởng trực tiếp từ Git diff hunks qua AST.
  2. *Bước 2 (Mở rộng cấu trúc)*: Duyệt 1–2 bước trên Call Graph và Import Graph để thu nạp các định nghĩa hàm liên quan, schema dữ liệu đầu vào (Pydantic models) và các ràng buộc ủy quyền.
  3. *Bước 3 (Truy xuất ngữ nghĩa bổ sung)*: Nếu ngữ cảnh cấu trúc chưa đủ hoặc gặp liên kết động, sử dụng truy xuất ngữ nghĩa qua `pgvector` với metadata filter bị giới hạn trong các module liên quan.
  4. *Bước 4 (Context Pruning)*: Cắt tỉa ngữ cảnh dựa trên token budget để chỉ cung cấp những thông tin thực sự giá trị cho prompt của LLM.

---

## 4. Kết luận Ứng dụng vào Hệ thống Đề tài

Nghiên cứu khẳng định định hướng **Hybrid Audit kết hợp Repo-level Context** là hoàn toàn đúng đắn về mặt khoa học:
* Không đưa toàn bộ kho mã nguồn vào LLM (gây nhiễu và lãng phí token).
* Không chỉ gửi diff đơn lẻ (gây thiếu hụt ngữ cảnh kiểm tra quyền và luồng dữ liệu).
* Áp dụng kiến trúc RAG định hướng cấu trúc (Structural-guided Repo RAG) trên nền tảng PostgreSQL `pgvector` để cung cấp ngữ cảnh chính xác, tinh gọn cho module phân tích LLM.
