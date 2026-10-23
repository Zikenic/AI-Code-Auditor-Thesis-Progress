import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

import pytest
from documents import retrieve_tenant_document
from authz import TenantAccessDenied


def test_retrieve_tenant_document_same_tenant():
    store = {
        "doc-1": {"id": "doc-1", "title": "Confidential", "content": "secret", "tenant_id": "org-acme"}
    }
    doc = retrieve_tenant_document(store, "doc-1", requesting_user_id="u1", requesting_tenant_id="org-acme")
    assert doc["title"] == "Confidential"


def test_retrieve_tenant_document_cross_tenant_rejected():
    store = {
        "doc-1": {"id": "doc-1", "title": "Confidential", "content": "secret", "tenant_id": "org-acme"}
    }
    with pytest.raises(TenantAccessDenied):
        retrieve_tenant_document(store, "doc-1", requesting_user_id="u2", requesting_tenant_id="org-evil")
