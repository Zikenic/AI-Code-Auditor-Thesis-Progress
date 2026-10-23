import sys
from pathlib import Path

for mod in ["documents", "authz"]:
    if mod in sys.modules:
        del sys.modules[mod]

sys.path.insert(0, str(Path(__file__).parent))

import pytest  # noqa: E402
from authz import TenantAccessDenied  # noqa: E402
from documents import retrieve_tenant_document  # noqa: E402


def test_retrieve_tenant_document_same_tenant():
    store = {
        "doc-1": {"id": "doc-1", "title": "Confidential", "content": "secret", "tenant_id": "org-acme"}
    }
    doc = retrieve_tenant_document(store, "doc-1", requesting_tenant_id="org-acme")
    assert doc["title"] == "Confidential"


def test_retrieve_tenant_document_cross_tenant_rejected():
    store = {
        "doc-1": {"id": "doc-1", "title": "Confidential", "content": "secret", "tenant_id": "org-acme"}
    }
    with pytest.raises(TenantAccessDenied):
        retrieve_tenant_document(store, "doc-1", requesting_tenant_id="org-evil")


def test_retrieve_tenant_document_missing_tenant_in_record_rejected():
    store = {
        "doc-2": {"id": "doc-2", "title": "No Tenant Doc", "content": "secret"}
    }
    with pytest.raises(TenantAccessDenied):
        retrieve_tenant_document(store, "doc-2", requesting_tenant_id="org-acme")
