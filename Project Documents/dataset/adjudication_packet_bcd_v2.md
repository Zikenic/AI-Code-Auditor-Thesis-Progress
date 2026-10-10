# Human Adjudication Packet — Configurations B, C, and D (Version 2.0)

> Purpose: Forensic human root-cause adjudication of all mechanical true-positive detections across Configurations B, C, and D.
> Note: Mechanical matches are not validated semantic discoveries until human adjudication.

- **Unique Ground-Truth Defects Represented:** 9
- **Total Matched Rows:** 21
  - Config B: 6
  - Config C: 8
  - Config D: 7

---

## CAND-0006-DEF-1 (CAND-0006 — Category 1)
- **Target Locus:** `scrapy/utils/datatypes.py:318-319`
- **CWE:** CWE-476 (alt: ['CWE-670'])
- **Description:** Missing NoneType boundary check on self.limit before relational comparison len(self) >= self.limit in LocalCache.__setitem__
- **Matching Configurations (3):** Config B, Config C, Config D

| Config | Finding ID | Finding Lines | Match Type | Finding CWE | Finding Title | Notes / Flag |
| :--- | :--- | :---: | :--- | :---: | :--- | :--- |
| Config B | `llm-e5318502e2` | 317-319 | Direct Overlap | CWE-476 | LocalCache.__setitem__ crashes with | Clean direct match |
| Config C | `llm-98ecf4d1f2` | 317-319 | Direct Overlap | CWE-476 | LocalCache.__setitem__ crashes with | Clean direct match |
| Config D | `llm-34ab7f41ca` | 317-319 | Direct Overlap | CWE-476 | LocalCache.__setitem__ raises TypeE | Clean direct match |

### Adjudication Decision Table
| Configuration | Human Verdict (`ROOT_CAUSE_ALIGNED` / `PROXIMITY_ONLY` / `INDETERMINATE`) | Adjudicator Rationale |
| :--- | :--- | :--- |
| Config B | `[PENDING]` | |
| Config C | `[PENDING]` | |
| Config D | `[PENDING]` | |

---

## CAND-0007-DEF-1 (CAND-0007 — Category 2)
- **Target Locus:** `fastapi/routing.py:182-184`
- **CWE:** CWE-352 (alt: ['CWE-20', 'CWE-345'])
- **Description:** Ground-truth locus 182-184
- **Matching Configurations (2):** Config C, Config D

| Config | Finding ID | Finding Lines | Match Type | Finding CWE | Finding Title | Notes / Flag |
| :--- | :--- | :---: | :--- | :---: | :--- | :--- |
| Config C | `llm-b884c5f510` | 182-184 | Direct Overlap | CWE-20 | JSON body parsed without size limit | REVIEW FLAG: Finding reports JSON parsing DoS (CWE-400) at CSRF defect locus (CWE-352/20) |
| Config D | `llm-89945e4935` | 184-184 | Direct Overlap | CWE-20 | Raw JSON body parsed without size o | REVIEW FLAG: Finding reports JSON parsing DoS (CWE-400) at CSRF defect locus (CWE-352/20) |

### Adjudication Decision Table
| Configuration | Human Verdict (`ROOT_CAUSE_ALIGNED` / `PROXIMITY_ONLY` / `INDETERMINATE`) | Adjudicator Rationale |
| :--- | :--- | :--- |
| Config C | `[PENDING]` | |
| Config D | `[PENDING]` | |

---

## CAND-0009-DEF-2 (CAND-0009 — Category 2)
- **Target Locus:** `src/jinja2/filters.py:292-293`
- **CWE:** CWE-79 (alt: ['CWE-116', 'CWE-20'])
- **Description:** Ground-truth locus 292-293
- **Matching Configurations (1):** Config B

| Config | Finding ID | Finding Lines | Match Type | Finding CWE | Finding Title | Notes / Flag |
| :--- | :--- | :---: | :--- | :---: | :--- | :--- |
| Config B | `llm-ae88f3f255` | 292-293 | Direct Overlap | CWE-116 | do_xmlattr only checks for space ch | Clean direct match |

### Adjudication Decision Table
| Configuration | Human Verdict (`ROOT_CAUSE_ALIGNED` / `PROXIMITY_ONLY` / `INDETERMINATE`) | Adjudicator Rationale |
| :--- | :--- | :--- |
| Config B | `[PENDING]` | |

---

## CAND-0015-DEF-1 (CAND-0015 — Category 3)
- **Target Locus:** `django/contrib/postgres/aggregates/general.py:54-58`
- **CWE:** CWE-89 (alt: ['CWE-943'])
- **Description:** Raw string interpolation of delimiter in StringAgg SQL template
- **Matching Configurations (2):** Config C, Config D

| Config | Finding ID | Finding Lines | Match Type | Finding CWE | Finding Title | Notes / Flag |
| :--- | :--- | :---: | :--- | :---: | :--- | :--- |
| Config C | `llm-82bb619df2` | 54-58 | Direct Overlap | CWE-89 | StringAgg delimiter injected unsani | Clean direct match |
| Config D | `llm-a03cfc86c4` | 54-54 | Direct Overlap | CWE-89 | StringAgg delimiter inserted unesca | Clean direct match |

### Adjudication Decision Table
| Configuration | Human Verdict (`ROOT_CAUSE_ALIGNED` / `PROXIMITY_ONLY` / `INDETERMINATE`) | Adjudicator Rationale |
| :--- | :--- | :--- |
| Config C | `[PENDING]` | |
| Config D | `[PENDING]` | |

---

## CAND-0017-DEF-1 (CAND-0017 — Category 3)
- **Target Locus:** `tortoise/backends/mysql/executor.py:19-45`
- **CWE:** CWE-89 (alt: ['CWE-20', 'CWE-943'])
- **Description:** Ground-truth locus 19-45
- **Matching Configurations (3):** Config B, Config C, Config D

| Config | Finding ID | Finding Lines | Match Type | Finding CWE | Finding Title | Notes / Flag |
| :--- | :--- | :---: | :--- | :---: | :--- | :--- |
| Config B | `llm-df2e870ccf` | 20-44 | Direct Overlap | CWE-89 | SQL injection via unsanitized LIKE  | Clean direct match |
| Config C | `llm-661f1ee46d` | 19-44 | Direct Overlap | CWE-89 | LIKE pattern injection via unescape | Clean direct match |
| Config D | `llm-607b19bc01` | 19-44 | Direct Overlap | CWE-89 | LIKE-pattern injection via unsaniti | Clean direct match |

### Adjudication Decision Table
| Configuration | Human Verdict (`ROOT_CAUSE_ALIGNED` / `PROXIMITY_ONLY` / `INDETERMINATE`) | Adjudicator Rationale |
| :--- | :--- | :--- |
| Config B | `[PENDING]` | |
| Config C | `[PENDING]` | |
| Config D | `[PENDING]` | |

---

## CAND-0019-DEF-1 (CAND-0019 — Category 4)
- **Target Locus:** `aiohttp/web_urldispatcher.py:643-645`
- **CWE:** CWE-22 (alt: ['CWE-20', 'CWE-59'])
- **Description:** Ground-truth locus 643-645
- **Matching Configurations (2):** Config C, Config D

| Config | Finding ID | Finding Lines | Match Type | Finding CWE | Finding Title | Notes / Flag |
| :--- | :--- | :---: | :--- | :---: | :--- | :--- |
| Config C | `llm-18e60f4b15` | 634-654 | Direct Overlap | CWE-22 | Potential path traversal when follo | Clean direct match |
| Config D | `llm-d4ef6fda4b` | 634-670 | Direct Overlap | CWE-22 | Potential path traversal when follo | Clean direct match |

### Adjudication Decision Table
| Configuration | Human Verdict (`ROOT_CAUSE_ALIGNED` / `PROXIMITY_ONLY` / `INDETERMINATE`) | Adjudicator Rationale |
| :--- | :--- | :--- |
| Config C | `[PENDING]` | |
| Config D | `[PENDING]` | |

---

## CAND-0019-DEF-2 (CAND-0019 — Category 4)
- **Target Locus:** `aiohttp/web_urldispatcher.py:574-576`
- **CWE:** CWE-22 (alt: ['CWE-20', 'CWE-59'])
- **Description:** Ground-truth locus 574-576
- **Matching Configurations (3):** Config B, Config C, Config D

| Config | Finding ID | Finding Lines | Match Type | Finding CWE | Finding Title | Notes / Flag |
| :--- | :--- | :---: | :--- | :---: | :--- | :--- |
| Config B | `llm-043f756df6` | 577-579 | Tolerance-Only (+1 lines) | CWE-22 | Path traversal check in url_for not | Tolerance-only match: distance = 1 lines (within ±10) |
| Config C | `llm-91395a191b` | 575-591 | Direct Overlap | CWE-22 | Path traversal bypass possible in u | Clean direct match |
| Config D | `llm-a38a061d03` | 575-591 | Direct Overlap | CWE-22 | Path traversal bypass in `url_for`  | Clean direct match |

### Adjudication Decision Table
| Configuration | Human Verdict (`ROOT_CAUSE_ALIGNED` / `PROXIMITY_ONLY` / `INDETERMINATE`) | Adjudicator Rationale |
| :--- | :--- | :--- |
| Config B | `[PENDING]` | |
| Config C | `[PENDING]` | |
| Config D | `[PENDING]` | |

---

## CAND-0020-DEF-1 (CAND-0020 — Category 4)
- **Target Locus:** `src/werkzeug/security.py:151-157`
- **CWE:** CWE-22 (alt: ['CWE-20'])
- **Description:** safe_join fails to block UNC / leading slash paths on Windows
- **Matching Configurations (2):** Config B, Config C

| Config | Finding ID | Finding Lines | Match Type | Finding CWE | Finding Title | Notes / Flag |
| :--- | :--- | :---: | :--- | :---: | :--- | :--- |
| Config B | `llm-3c902e8f3a` | 147-157 | Direct Overlap | CWE-22 | safe_join does not block path compo | Clean direct match |
| Config C | `llm-0bd9c334da` | 147-157 | Direct Overlap | CWE-22 | safe_join may not detect traversal  | Clean direct match |

### Adjudication Decision Table
| Configuration | Human Verdict (`ROOT_CAUSE_ALIGNED` / `PROXIMITY_ONLY` / `INDETERMINATE`) | Adjudicator Rationale |
| :--- | :--- | :--- |
| Config B | `[PENDING]` | |
| Config C | `[PENDING]` | |

---

## CAND-0021-DEF-1 (CAND-0021 — Category 4)
- **Target Locus:** `starlette/staticfiles.py:172-172`
- **CWE:** CWE-22 (alt: ['CWE-20'])
- **Description:** Ground-truth locus 172-172
- **Matching Configurations (3):** Config B, Config C, Config D

| Config | Finding ID | Finding Lines | Match Type | Finding CWE | Finding Title | Notes / Flag |
| :--- | :--- | :---: | :--- | :---: | :--- | :--- |
| Config B | `llm-0d1cdb819d` | 162-175 | Direct Overlap | CWE-22 | Path traversal check uses os.path.c | Clean direct match |
| Config C | `llm-bf2fbd812b` | 172-172 | Direct Overlap | CWE-22 | Path traversal bypass via commonpre | Clean direct match |
| Config D | `llm-6441e52b1b` | 172-172 | Direct Overlap | CWE-22 | Path traversal via os.path.commonpr | Clean direct match |

### Adjudication Decision Table
| Configuration | Human Verdict (`ROOT_CAUSE_ALIGNED` / `PROXIMITY_ONLY` / `INDETERMINATE`) | Adjudicator Rationale |
| :--- | :--- | :--- |
| Config B | `[PENDING]` | |
| Config C | `[PENDING]` | |
| Config D | `[PENDING]` | |

---
