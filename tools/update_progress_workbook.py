"""Update cumulative progress workbook with Week 5-6 deliverables.

Ensures:
1. Preserves existing rows 1 to 28 intact.
2. Normalizes all public-facing evidence hyperlinks to:
   https://github.com/Zikenic/AI-Code-Auditor-Thesis-Progress/blob/main/...
3. Appends tasks 20, 21, 22, 23 covering:
   - 100-case benchmark expansion & provenance reconciliation
   - Model-compatible token counting (Anthropic gateway)
   - Backend API, physical SQLite persistence & webhook intake
   - Week 5-6 independent acceptance audit and gap closure
4. Applies consistent Calibri fonts, alignments, borders, and text wrapping.
"""

from __future__ import annotations

from pathlib import Path

import openpyxl
from openpyxl.styles import Alignment, Border, Font, Side

REPO_ROOT = Path(__file__).resolve().parent.parent
WORKBOOK_PATH = REPO_ROOT / "Project Documents" / "reports" / "Week_3-4_and_subsequent_progress.xlsx"
PUBLIC_PREFIX = "https://github.com/Zikenic/AI-Code-Auditor-Thesis-Progress/blob/main/"

THIN_SIDE = Side(border_style="thin", color="D3D3D3")
TABLE_BORDER = Border(left=THIN_SIDE, right=THIN_SIDE, top=THIN_SIDE, bottom=THIN_SIDE)

FONT_REGULAR = Font(name="Calibri", size=10, bold=False)
FONT_BOLD = Font(name="Calibri", size=10, bold=True)
FONT_LINK = Font(name="Calibri", size=9, bold=False, color="0000FF", underline="single")

ALIGN_CENTER = Alignment(horizontal="center", vertical="top", wrap_text=True)
ALIGN_LEFT = Alignment(horizontal="left", vertical="top", wrap_text=True)

NEW_TASKS = [
    (
        20,
        "Mở rộng bộ dữ liệu Benchmark lên 100 ca kiểm thử (100-Case Benchmark Expansion)\n"
        "- Mở rộng và khóa bộ dữ liệu chuẩn gồm đúng 100 ca kiểm thử (50 ca lỗi và 50 ca sạch đối chứng).\n"
        "- Rà soát và chuẩn hóa nguồn gốc (provenance): 18 ca lỗi trích xuất từ commit thực tế của kho mã nguồn mở "
        "(Tornado, FastAPI, Scrapy, Django, Werkzeug, v.v.) với mã băm SHA256 và tọa độ locus xác thực; "
        "32 ca lỗi tổng hợp (synthetic); 18 ca sạch thiết kế thủ công (handcrafted clean controls); 32 ca sạch tổng hợp.\n"
        "- 100% (100/100) ca kiểm thử có mã nguồn cục bộ và thực thi được, loại bỏ hoàn toàn mã giả placeholder.",
        "Đã hoàn thành",
        "Đạt toàn diện chỉ tiêu quy mô 100 ca kiểm thử (50 buggy / 50 clean). Cân đối chặt chẽ trên 6 nhóm danh mục CWE. "
        "Toàn bộ 100 ca kiểm thử đều có tệp mã nguồn cục bộ hợp lệ và độc lập trên đĩa, được kiểm chứng 100% qua runner "
        "mà không dùng bất kỳ mã giả thay thế nào (zero silent placeholder fallbacks).",
        "data/benchmark_manifest.json",
        f"{PUBLIC_PREFIX}data/benchmark_manifest.json",
    ),
    (
        21,
        "Đo lường ngữ cảnh bằng Tokenizer tương thích mô hình thực tế (Model-Compatible Tokenizer)\n"
        "- Tích hợp endpoint chuẩn POST /v1/messages/count_tokens qua local gateway với định danh mô hình `ag/claude-sonnet-4-6`.\n"
        "- Đo lường chính xác toàn bộ prompt render hoàn chỉnh (system prompt, user content, mã nguồn, static findings, repo context và schema) trong một lượt gọi duy nhất, loại bỏ cơ chế cộng dồn chuỗi rời rạc.\n"
        "- Phân định rõ số token toàn prompt và token ngữ cảnh; bảo lưu ngân sách completion tokens (16,384 tokens).\n"
        "- Các bộ đếm tiktoken BPE và character ratio được phân loại minh bạch là ước lượng gần đúng (is_heuristic=True); "
        "chế độ đánh giá nghiêm ngặt kích hoạt lỗi TokenCounterError nếu gateway thất bại, không hạ cấp ngầm.",
        "Đã hoàn thành",
        "Đo lường độ dài ngữ cảnh bằng API tokenizer native của Anthropic thay thế công thức chia ký tự heuristic. "
        "Đạt chuẩn tính toán đa ngôn ngữ (tiếng Việt, CJK) và cú pháp lập trình. Bảo lưu ngân sách completion tokens "
        "chống tràn cửa sổ ngữ cảnh khi gọi mô hình.",
        "src/auditor/llm/token_counter.py",
        f"{PUBLIC_PREFIX}src/auditor/llm/token_counter.py",
    ),
    (
        22,
        "Triển khai tầng dịch vụ backend, CSDL vật lý và tiếp nhận Webhook (Backend, Physical DB & Webhook)\n"
        "- Hiện thực hóa backend FastAPI qua 7 routers chuẩn RESTful.\n"
        "- Kiểm chứng lưu trữ CSDL vật lý SQLite cấu hình WAL mode (PRAGMA journal_mode=WAL), ràng buộc khóa ngoại và tính bền vững qua kiểm thử khởi động lại tiến trình độc lập (subprocess restart persistence).\n"
        "- Tiếp nhận Webhook GitHub xác thực chữ ký HMAC-SHA256 theo thời gian hằng số, kiểm tra tính lũy đằng dựa trên X-GitHub-Delivery chống trùng lặp, lưu trữ CSDL nguyên tử trước khi lập lịch task và cho phép truy xuất trạng thái/findings qua GET /api/v1/audits/{id}.\n"
        "- Rào chắn bảo mật: ngăn chặn duyệt thư mục hệ thống tạm (chỉ cho phép thư mục dự án và AUDITOR_ALLOWED_WORKSPACE_ROOTS), khử độc tham số kho mã và commit.\n"
        "- Giới hạn nguyên mẫu: cơ chế tác vụ nền dựa trên BackgroundTasks nội tiến trình FastAPI, chưa phải hàng đợi phân tán bền vững (Celery/Redis).",
        "Đã hoàn thành có điều kiện",
        "Hoàn thành trọn vẹn kiến trúc backend API, lưu trữ vật lý bền vững và tiếp nhận webhook an toàn. "
        "Bảo đảm tính lũy đằng và phòng chống tấn công path traversal. Giới hạn có điều kiện: ghi nhận trung thực giới hạn nguyên mẫu "
        "của BackgroundTasks nội tiến trình đối với độ bền khi tiến trình gặp sự cố (cần Celery/Redis khi triển khai phân tán quy mô lớn).",
        "src/auditor/api/webhooks.py",
        f"{PUBLIC_PREFIX}src/auditor/api/webhooks.py",
    ),
    (
        23,
        "Thẩm định độc lập & Đóng gói nghiệm thu mốc Tuần 5–6 (Week 5–6 Independent Acceptance Audit)\n"
        "- Tiến hành thẩm định độc lập toàn diện 3 yêu cầu cốt lõi của GVHD theo nguyên tắc khách quan khoa học.\n"
        "- Sửa chữa dứt điểm lỗi giả mạo placeholder trong runner, chuẩn hóa lược đồ Pydantic ManifestCase, "
        "vật lý hóa 18 snapshot kho mã nguồn mở vào data/fixtures/upstream_snapshots/, thiết lập bộ kiểm thử nguồn gốc dữ liệu test_benchmark_100_provenance.py.\n"
        "- Toàn bộ 285/285 tests dự án + 21/21 ablation tests (tổng cộng 306 tests) và Ruff lint đều đạt 100% "
        "không phát sinh chi phí suy luận trực tiếp ($0.00).\n"
        "- Xuất báo cáo nghiệm thu chi tiết và checklist nghiệm thu máy đọc được.",
        "Đã hoàn thành",
        "Báo cáo nghiệm thu độc lập đánh giá khách quan, định lượng và có minh chứng mã nguồn/kiểm thử đối chiếu cho toàn bộ 3 mục tiêu Tuần 5–6. "
        "Khóa thành công mốc tiến độ với 306 tests tự động hoàn toàn xanh.",
        "reports/week5_6_deliverables_acceptance_report.md",
        f"{PUBLIC_PREFIX}Project%20Documents/reports/week5_6_deliverables_acceptance_report.md",
    ),
]


def normalize_existing_links(ws: openpyxl.worksheet.worksheet.Worksheet) -> None:
    """Normalize any private-repo master links in rows 10 to 28 to public main repo links."""
    for r in range(10, 29):
        cell = ws.cell(r, 5)
        if cell.hyperlink and cell.hyperlink.target:
            target = cell.hyperlink.target
            if "AI-Code-Auditor-Thesis1/blob/master/" in target:
                rel_path = target.split("AI-Code-Auditor-Thesis1/blob/master/")[1]
                new_target = f"{PUBLIC_PREFIX}{rel_path}"
                cell.hyperlink = new_target


def main() -> None:
    wb = openpyxl.load_workbook(WORKBOOK_PATH)
    ws = wb.active

    # Normalize existing links
    normalize_existing_links(ws)

    # Append new tasks
    start_row = 29
    for i, (stt, content, status, evaluation, proof_text, proof_url) in enumerate(NEW_TASKS):
        row_idx = start_row + i

        cell_a = ws.cell(row_idx, 1, value=stt)
        cell_b = ws.cell(row_idx, 2, value=content)
        cell_c = ws.cell(row_idx, 3, value=status)
        cell_d = ws.cell(row_idx, 4, value=evaluation)
        cell_e = ws.cell(row_idx, 5, value=proof_text)

        cell_a.font = FONT_BOLD
        cell_a.alignment = ALIGN_CENTER
        cell_a.border = TABLE_BORDER

        cell_b.font = FONT_REGULAR
        cell_b.alignment = ALIGN_LEFT
        cell_b.border = TABLE_BORDER

        cell_c.font = FONT_BOLD
        cell_c.alignment = ALIGN_CENTER
        cell_c.border = TABLE_BORDER

        cell_d.font = FONT_REGULAR
        cell_d.alignment = ALIGN_LEFT
        cell_d.border = TABLE_BORDER

        cell_e.font = FONT_LINK
        cell_e.alignment = ALIGN_LEFT
        cell_e.border = TABLE_BORDER
        cell_e.hyperlink = proof_url

    wb.save(WORKBOOK_PATH)
    print(f"Workbook successfully updated with {len(NEW_TASKS)} new tasks! Saved to {WORKBOOK_PATH}")


if __name__ == "__main__":
    main()
