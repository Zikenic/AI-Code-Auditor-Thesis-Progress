import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

import pytest
from storage import save_user_upload


def test_save_user_upload_safe(tmp_path: Path):
    saved = save_user_upload(tmp_path, "report_2026.pdf", b"pdf content")
    assert Path(saved).exists()
    assert Path(saved).read_bytes() == b"pdf content"
    assert Path(saved).name == "report_2026.pdf"


def test_save_user_upload_traversal_neutralized(tmp_path: Path):
    # Attempt directory traversal
    saved = save_user_upload(tmp_path, "../../../etc/passwd", b"malicious")
    saved_path = Path(saved)
    assert saved_path.parent == tmp_path.resolve()
    assert "etc" not in saved_path.parts
    assert saved_path.name == "passwd"
