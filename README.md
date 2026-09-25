# Nghiên cứu, xây dựng hệ thống tự động đánh giá và phát hiện lỗi trong mã nguồn trên môi trường Pull Request
### Research and Development of an Automated Code Review and Bug Detection System for Pull Request Environments

---

## 📌 Thông tin Đề tài

- **Sinh viên thực hiện**: Bùi Văn Khải — MSSV: **24520719**
- **Giảng viên hướng dẫn**: ThS. Trần Thị Hồng Yến
- **Đơn vị**: Khoa Kỹ thuật Phần mềm — Trường Đại học Công nghệ Thông tin, ĐHQG-HCM
- **Học kỳ**: Học kỳ 1, Năm học 2026–2027

---

## 🎯 Giới thiệu Đề tài

Đề tài tập trung nghiên cứu và hiện thực hóa một hệ thống kiểm tra và phát hiện lỗi tự động trên môi trường **GitHub Pull Request** dành cho các ứng dụng web backend viết bằng **Python (FastAPI và Flask)**.

Hệ thống kết hợp mô hình phân tầng giữa:
1. **Tầng phân tích tĩnh tất định (Deterministic Static Analysis)**: Sử dụng **Ruff** (kiểm tra cú pháp, phong cách mã nguồn, và các luật bảo mật nhẹ từ Flake8-bandit) và **Semgrep Community Edition** (phân tích cây cú pháp trừu tượng AST và theo vết luồng dữ liệu bẩn *taint tracking*).
2. **Tầng phân tích ngữ nghĩa tăng cường (Semantic Analysis with Repository Context)**: Sử dụng các mô hình ngôn ngữ lớn (LLM) được tiếp sức bởi cơ chế trích xuất ngữ cảnh toàn kho mã nguồn (Repository Context Retrieval) thông qua đồ thị gọi hàm (**AST Call Graph**) và tìm kiếm ngữ nghĩa (**pgvector embedding**).

Hiệu năng của hệ thống được đánh giá thực nghiệm so sánh đa chiều qua 4 cấu hình:
- **Cấu hình A**: Chỉ phân tích tĩnh tất định (Ruff + Semgrep CE).
- **Cấu hình B**: Chỉ LLM với ngữ cảnh diff tệp đơn.
- **Cấu hình C**: Kết hợp Phân tích tĩnh + LLM không có ngữ cảnh toàn kho.
- **Cấu hình D**: Kết hợp Phân tích tĩnh + LLM có ngữ cảnh toàn kho (AST + Vector RAG).

---

## 📑 Báo cáo Tiến độ Chính thức

👉 **Xem Báo cáo Tiến độ Tuần 1–2 tại đây**: [reports/ROP_Week1-2.md](reports/ROP_Week1-2.md)

---

## 📂 Cấu trúc Kho Lưu trữ & Minh chứng Kỹ thuật

Tất cả các tài liệu kỹ thuật, nghiên cứu đối sánh và thiết kế thực nghiệm được cấu trúc minh bạch trong kho lưu trữ này:

```text
├── README.md                                          # Tài liệu tổng quan kho lưu trữ
├── reports/
│   └── ROP_Week1-2.md                                 # Báo cáo tiến độ chi tiết Tuần 1–2
├── requirements/
│   └── functional_nonfunctional_requirements.md       # Đặc tả 10 yêu cầu FR và 7 yêu cầu NFR
├── research/
│   ├── R1_static_analysis_ci_cd_summary.md            # Khảo sát đối sánh Ruff vs Semgrep CE
│   ├── R2_repo_context_rag_summary.md                 # Khảo sát AST Call Graph & Vector RAG
│   └── CWE_taxonomy_summary.md                        # Phân loại 6 nhóm lỗi & ánh xạ MITRE CWE
├── methodology/
│   └── benchmark_methodology.md                       # Phương pháp luận đánh giá & quy tắc so khớp locus
└── dataset/
    ├── dataset_design_test_case_list.md               # Thiết kế bộ dữ liệu benchmark (sàn 100 ca)
    └── ground_truth_validation_pilot.md               # Kết quả kiểm chứng thí điểm 12 ca lỗi thực địa
```

---

## 🔍 Liên kết Nhanh tới các Tài liệu Trọng tâm

1. **Khảo sát Công cụ Phân tích tĩnh**: [R1 Summary](research/R1_static_analysis_ci_cd_summary.md)
2. **Khảo sát Ngữ cảnh Kho mã nguồn**: [R2 Summary](research/R2_repo_context_rag_summary.md)
3. **Phân loại Điểm yếu MITRE CWE**: [CWE Taxonomy Summary](research/CWE_taxonomy_summary.md)
4. **Đặc tả Yêu cầu Kỹ thuật Hệ thống**: [FR & NFR Specification](requirements/functional_nonfunctional_requirements.md)
5. **Phương pháp luận Benchmark**: [Benchmark Methodology](methodology/benchmark_methodology.md)
6. **Thiết kế Bộ dữ liệu Kiểm thử**: [Dataset Design](dataset/dataset_design_test_case_list.md)
7. **Báo cáo Thí điểm 12 Ca Ground-Truth**: [Ground-Truth Pilot Report](dataset/ground_truth_validation_pilot.md)
