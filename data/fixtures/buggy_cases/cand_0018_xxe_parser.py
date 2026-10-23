"""Buggy Fixture: CAND-0018
Category 2: Input Validation / Sanitization
Primary CWE: CWE-611 (Improper Restriction of XML External Entity Reference)
"""

from __future__ import annotations
import xml.etree.ElementTree as ET

def parse_user_xml(xml_bytes: bytes) -> dict[str, str]:
    """Parse user-uploaded XML document without entity disabling."""
    root = ET.fromstring(xml_bytes)
    return {child.tag: child.text or "" for child in root}
