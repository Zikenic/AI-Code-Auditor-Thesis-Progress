"""Clean Control Fixture: CTRL-0027
Paired with: CAND-0018 (Category 2: Input Validation / Sanitization)
Target Scope: XML document deserialization and parsing
Intended Behavior: Rejects DTD declarations and entity expansions.
"""

from __future__ import annotations
import xml.etree.ElementTree as ET

def parse_user_xml(xml_bytes: bytes) -> dict[str, str]:
    """Parse user XML safely rejecting entity definitions."""
    xml_str = xml_bytes.decode("utf-8", errors="replace")
    if "<!DOCTYPE" in xml_str.upper() or "<!ENTITY" in xml_str.upper():
        raise ValueError("XML containing DTD or entity declarations is forbidden.")
    root = ET.fromstring(xml_bytes)
    return {child.tag: child.text or "" for child in root}
