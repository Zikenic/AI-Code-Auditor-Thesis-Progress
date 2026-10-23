import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

import pytest
from reports import build_metric_query


def test_build_metric_query_allowed_table():
    sql, params = build_metric_query("daily_active_users", "web")
    assert "daily_active_users" in sql
    assert params == ["web"]


def test_build_metric_query_injection_attempt_rejected():
    with pytest.raises(ValueError):
        build_metric_query("users; DROP TABLE users; --", "web")
