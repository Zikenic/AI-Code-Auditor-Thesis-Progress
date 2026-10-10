# Critical Vulnerability Analysis: Modern SQL and ORM Injection Vectors in Python Database Frameworks

## Executive Summary & Analytical Assessment

The security paradigm of modern software engineering has long operated under the assumption that Object-Relational Mapping (ORM) frameworks inherently neutralize Structured Query Language (SQL) injection vulnerabilities by design. Through parameterized query execution and automated abstract syntax tree (AST) construction, ORMs effectively insulate applications from traditional first-order injection payloads residing within literal values. However, contemporary vulnerability research—culminating in high-impact disclosures across 2025 and 2026—demonstrates that this security guarantee is incomplete. ORM frameworks frequently introduce structural blind spots where user input intersects with SQL identifiers, functional aggregations, relational aliases, and internal query-construction operators.

A critical evaluation of recent vulnerabilities reveals an architectural dichotomy: while database drivers and ORM compilation engines reliably bind query *values*, they remain susceptible when untrusted input influences query *structure*. This report analyzes several critical vulnerabilities across Python database ecosystems:
1. **CVE-2026-26198** in the Ormar asynchronous ORM (CVSS 9.8), where unvalidated aggregate functions directly invoke raw engine primitives via `sqlalchemy.text()`.
2. **Django ORM Vulnerabilities (CVE-2025-57833 and related 2025–2026 advisories)**, which exposed SQL injection vectors through keyword argument unpacking into query-construction primitives, internal `_connector` parameter manipulation, and dynamic `FilteredRelation` alias definitions.
3. **Cross-Engine Architectural Hazards**, analyzing how downstream frameworks like Tortoise-ORM and Ormar interact with core execution engines such as SQLAlchemy.

The definitive conclusion of this investigation is that ORM injection is not an anomaly born of edge-case implementation errors, but a structural consequence of frameworks exposing internal query-shaping semantics to high-level dynamic APIs. When developers unpack user-controlled dictionaries (`**kwargs`) into ORM filtering or aggregation methods, they pierce the abstraction layer, turning dynamic language conveniences into severe remote code execution (RCE) and data exfiltration pathways.

---

## Comprehensive Vulnerability Analysis: Ormar ORM (CVE-2026-26198)

### Root-Cause Analysis and Architectural Flaw

Ormar is an asynchronous mini-ORM designed for Python runtimes, built on top of SQLAlchemy Core and Databases, and tailored for integration with FastAPI and Pydantic models. Tracked as **CVE-2026-26198** with a Common Vulnerability Scoring System (CVSS v3.1) score of **9.8 (Critical: CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H)**, the vulnerability spans Ormar versions 0.9.9 through 0.22.0 ([National Vulnerability Database, 2026](https://nvd.nist.gov/vuln/detail/CVE-2026-26198)).

The vulnerability originates in the implementation of aggregate query construction within Ormar's query-set subsystem, specifically inside the `min()` and `max()` aggregation methods. In standard relational query construction, aggregate functions must reference validated column identifiers:

```sql
SELECT MIN(column_name) FROM table_name;
```

In Ormar versions 0.9.9 through 0.22.0, the framework allowed arbitrary string parameters passed to `Model.objects.min(columns=...)` or `Model.objects.max(columns=...)` to flow directly into raw SQLAlchemy expressions. Ormar invoked `sqlalchemy.text()` directly on user-provided strings without performing semantic validation against the model's defined fields or escaping the column tokens according to the targeted database dialect ([GitHub Security Lab, 2026](https://github.com/collerek/ormar/security/advisories)).

```python
# Vulnerable architectural implementation inside Ormar QuerySet aggregation
def _build_aggregate_clause(self, func_name: str, column: str):
    # column is accepted as an untrusted str and wrapped in raw text()
    # bypassing SQLAlchemy's compiler escaping and model schema validation
    return sqlalchemy.func[func_name](sqlalchemy.text(column))
```

Because `sqlalchemy.text()` explicitly instructs the underlying SQLAlchemy Core compiler to treat the enclosed string as a raw SQL fragment rather than a bind parameter or identifier, any syntax encapsulated within the `column` parameter is compiled and executed verbatim by the database backend ([SQLAlchemy Authors, 2024](https://docs.sqlalchemy.org/en/20/core/sqlelement.html#sqlalchemy.sql.expression.text)).

### Vulnerability Reproduction & Exploitation Vector

When exposed in an asynchronous web API (such as FastAPI), an endpoint that exposes sorting, metrics, or aggregation allows an unauthenticated remote attacker to escape the functional clause and execute arbitrary subqueries, administrative operations, or out-of-band data exfiltration.

```python
# FastAPI endpoint exposing Ormar aggregation
@app.get("/items/metrics")
async def get_item_metric(stat_field: str):
    # User input is passed directly to the Ormar aggregation method
    minimum_value = await Item.objects.min(columns=[stat_field])
    return {"minimum": minimum_value}
```

An attacker supplying the following payload through the `stat_field` query parameter can execute arbitrary SQL injection on a PostgreSQL backend:

```text
id) FROM items; DROP TABLE items; --
```

The resulting compiled SQL expression shifts from:
```sql
SELECT min(id) AS min_1 FROM items
```
to:
```sql
SELECT min(id) FROM items; DROP TABLE items; --) AS min_1 FROM items
```

In database dialects that do not permit stacked queries over individual wire protocol frames (e.g., standard asyncpg connections), an attacker can reliably pivot to time-based blind SQL injection or subquery extraction:

```text
id) || (SELECT CASE WHEN (SELECT ascii(substr(password, 1, 1)) FROM users WHERE id=1) = 97 THEN pg_sleep(5) ELSE pg_sleep(0) END) --
```

### Remediation and GitHub Patch Commit Analysis

The remediation implemented in Ormar version 0.22.1 addresses the root cause by revoking direct access to `sqlalchemy.text()` within aggregate query construction. The engine resolves column inputs against the model's internal Pydantic/SQLAlchemy field catalog:

```python
# Remediated Implementation: Model Schema Validation and Column Resolution
def _build_aggregate_clause(self, func_name: str, column: str):
    if column not in self.model_cls.Meta.model_fields:
        raise ModelError(f"Field '{column}' does not exist on model '{self.model_cls.__name__}'")
    
    # Resolve to the internal, validated SQLAlchemy Column element
    model_column = self.model_cls.Meta.table.columns[column]
    return getattr(sqlalchemy.func, func_name)(model_column)
```

By ensuring that the input is validated against `model_fields` and mapped to a strictly typed `Column` object, the query compiler constructs standard SQL identifier representations and rejects arbitrary SQL expressions before they reach the dialect compilation pipeline ([GitHub Commit Reference, 2026](https://github.com/collerek/ormar/commit/d26198f98a287bf)).

---

## Advanced Django ORM Vulnerabilities: Query-Set Deserialization and Alias Exploitation

### CVE-2025-57833: Breakdown of FilteredRelation and Model Alias Injections

Django’s ORM is widely regarded as one of the most mature database abstraction systems in web development. Nevertheless, high-severity vulnerabilities discovered throughout late 2025 and mid-2026 demonstrate that complex relational mapping mechanisms can yield severe injection vulnerabilities.

Tracked as **CVE-2025-57833**, this vulnerability impacts Django versions:
* 4.2 prior to 4.2.24
* 5.1 prior to 5.1.12
* 5.2 prior to 5.2.6

The vulnerability stemmed from insufficient validation of dynamic alias values during SQL query construction involving `FilteredRelation` objects ([Django Project, 2025a](https://www.djangoproject.com/weblog/2025/nov/05/security-releases/)). `FilteredRelation` allows developers to specify custom `ON` conditions for joined models. When applications constructed queries using dynamic keyword arguments (`**kwargs`) to map relations or aliases, user-controlled input could influence the SQL table alias identifier:

```python
# Vulnerable Query Construction Pattern
def filter_records(request):
    alias_key = request.GET.get("relation_alias")
    # Dynamic kwargs passed to annotate alongside FilteredRelation
    qs = Item.objects.annotate(
        **{alias_key: FilteredRelation("category", condition=Q(category__is_active=True))}
    ).filter(**{f"{alias_key}__name": "Electronics"})
    return qs
```

Under vulnerable versions, the Django query compiler failed to assert strict identifier semantics on the dynamic key serving as the table alias name during the resolution of `FilteredRelation`. Consequently, arbitrary SQL syntax injected into the alias token escaped table-aliasing boundaries inside the generated `LEFT OUTER JOIN` statement:

```sql
SELECT "item"."id", "item"."name" 
FROM "item" 
LEFT OUTER JOIN "category" "category" ON (...)
-- Injected alias payload breaks out into raw join conditions
```

### The `_connector` Argument Exploitation in `QuerySet` and `Q` Objects

In parallel security updates released on November 5, 2025 (addressing Django 5.2.8, 5.1.14, and 4.2.26), a critical flaw in query compilation logic was remediated regarding the treatment of internal keyword parameters ([Django Project, 2025b](https://www.djangoproject.com/weblog/2025/nov/05/security-releases-detail/)).

Django's `QuerySet.filter()`, `QuerySet.exclude()`, `QuerySet.get()`, and `Q()` objects internally use an argument named `_connector` to define how relational sub-clauses are joined—typically defaulting to the boolean string `'AND'` or `'OR'`. A pervasive Python anti-pattern involves directly passing deserialized request parameters into query filter methods:

```python
# High-risk development pattern: Dynamic unpacking of untrusted dictionaries
user_filters = json.loads(request.body)
results = Product.objects.filter(**user_filters)
```

If an attacker submitted a JSON payload containing the `_connector` key, the internal ORM compiler accepted the supplied string and appended it directly into the `WHERE` clause without sanitizing it against an allowed set of boolean operators:

```json
{
  "name": "Smartphone",
  "_connector": ") OR (1=1) --"
}
```

During compilation, Django’s `django.db.models.sql.compiler.SQLCompiler` concatenated the `_connector` value directly between where-children:

```python
# Flawed SQL compilation pattern (simplified conceptual representation)
def compile_where_node(self, where_node):
    connector = where_node.connector  # Accepted untrusted string without validation
    sql_fragments = [self.compile(child) for child in where_node.children]
    return f" {connector} ".join(sql_fragments)
```

The resulting query bypassed all intended access controls:
```sql
SELECT ... FROM "product" WHERE ("product"."name" = 'Smartphone' ) OR (1=1) -- "product"."active" = true)
```

### Django Patch Commit Analysis

The patches deployed across Django 5.2.8, 5.1.14, and 4.2.26 enforced two layers of defensive validation:
1. **Explicit Connector Whitelisting**: The `_connector` argument within `Q` objects and `WhereNode` instances is validated against an immutable set containing only `'AND'`, `'OR'`, and `None`. Any unexpected token raises an immediate `ValueError`.
2. **Identifier Character Enforcement for Relational Aliases**: The dynamic keys parsed by `FilteredRelation` and table-aliasing subsystems are routed through `django.core.validators.RegexValidator` or explicit regex checks requiring compliance with standard database identifier conventions (`^[a-zA-Z_][a-zA-Z0-9_]*$`).

```python
# django/db/models/sql/where.py (Remediated Logic)
ALLOWED_CONNECTORS = frozenset({"AND", "OR"})

class WhereNode(tree.Node):
    def __init__(self, children=None, connector=None, negated=False):
        if connector is not None and connector not in ALLOWED_CONNECTORS:
            raise ValueError(f"Invalid connector: '{connector}'. Allowed: {ALLOWED_CONNECTORS}")
        super().__init__(children, connector or "AND", negated)
```

This defense-in-depth approach ensures that dynamic dictionary unpacking cannot introduce malicious SQL operators into query evaluation trees ([Django Project Security Releases, 2025](https://docs.djangoproject.com/en/dev/releases/security/)).

---

## Cross-Framework Comparative Evaluation: SQLAlchemy, Tortoise-ORM, and Ormar

Understanding why Python ORMs encounter structural injection vulnerabilities requires analyzing the division of labor between higher-level ORMs and low-level database drivers.

| Framework | Vulnerability Identifier / Vector | Severity (CVSS) | Affected Component / Method | Underlying Architectural Root Cause |
| :--- | :--- | :--- | :--- | :--- |
| **Ormar** | CVE-2026-26198 | 9.8 (Critical) | `min()`, `max()`, Aggregate queries | Direct dynamic pass-through of column parameters to `sqlalchemy.text()` without schema validation. |
| **Django ORM** | CVE-2025-57833 | 8.8 (High) | `FilteredRelation`, Dynamic Aliases | Insufficient character sanitization of user-controlled alias keys during dynamic SQL JOIN construction. |
| **Django ORM** | Late-2025 QuerySet Injection | 9.1 (Critical) | `filter()`, `exclude()`, `Q(kwargs)` | Unsanitized `_connector` parameter processing in query tree compiler via dictionary unpacking. |
| **Tortoise-ORM** | Dynamic Ordering / Raw SQL Filters | Variable (High) | `.order_by()`, `raw()`, `Function()` | Direct string concatenation in dynamic ordering clauses; reliance on developers to avoid dynamic interpolation. |
| **SQLAlchemy** | Misuse of `text()` and Core Clauses | Dependent on Consumer Code | Core `text()`, `select().order_by()` | Developer conflation of structural clauses with literal values; engine intentionally trusts `text()` fragments. |

### The SQLAlchemy Core Abstraction Boundary

SQLAlchemy Core is not an ORM; it is an abstraction toolkit and expression compiler. It explicitly bifurcates expressions into two models:
* **Parameterized Expressions** (e.g., `column("x") == bindparam("val")`): Handled via driver-level parameter substitution (`$1`, `%s`, `?`).
* **Textual Fragments** (e.g., `text("...")`): Explicit directives instructing the dialect compiler that the enclosed string contains executable SQL.

When higher-level frameworks (such as Ormar) abstract SQLAlchemy Core to provide an active-record or async API, developers of those frameworks often misuse `text()` to bypass constructing an abstract expression. If an input originates from an untrusted source, invoking `text()` breaks the security guarantees established by the underlying database driver.

### Tortoise-ORM Architectural Considerations

Tortoise-ORM, an alternative async ORM inspired by Django's syntax, implements an independent query generator compiling to raw SQL strings executed over database drivers (such as `asyncpg`, `aiomysql`, or `aiosqlite`). 

While Tortoise-ORM isolates literal values into parameter arrays passed alongside the compiled query, dynamic column specifications in methods such as `order_by()` or custom aggregation via `tortoise.functions.Function` present structural risk profiles similar to those seen in Django and Ormar:

```python
# Risky pattern in Tortoise-ORM dynamic applications
user_order = request.GET.get("sort_by")
# If unvalidated, passing user_order into order_by() allows structural injection
# e.g., sort_by = "id; DROP TABLE users; --" (depending on driver and dialect)
results = await Item.filter(is_active=True).order_by(user_order)
```

Because database wire protocols forbid parameterizing identifiers (such as table names, column names, and sorting directions like `ASC`/`DESC`), Tortoise-ORM and Django must perform runtime string formatting. If the framework fails to validate these identifiers against an internal model schema whitelist, arbitrary SQL execution becomes possible.

---

## Defensive Engineering, Static Analysis, and Remediation

### Remediation Strategies for Framework Consumers

The vulnerabilities reviewed highlight that relying solely on an ORM is insufficient to prevent SQL injection. Software architects must enforce defensive coding practices across application boundaries:

#### 1. Prohibit Dynamic Keyword Unpacking from Untrusted Payloads
Applications must never unpack unvalidated request dictionaries directly into ORM queries:

```python
# VULNERABLE AND HIGH RISK
def update_view(request):
    data = json.loads(request.body)
    return Model.objects.filter(**data)

# REMEDIATED: Explicit Whitelisting via Schema Validation (e.g., Pydantic)
from pydantic import BaseModel, Field

class FilterSchema(BaseModel):
    category_id: int
    is_active: bool = True

def update_view(request):
    payload = FilterSchema.model_validate_json(request.body)
    return Model.objects.filter(
        category_id=payload.category_id,
        is_active=payload.is_active
    )
```

#### 2. Strict Identifier Whitelisting for Dynamic Sorting and Aggregation
When applications expose dynamic ordering or aggregation fields to end users, they must validate the requested tokens against an explicit set of permissible attributes before passing them to the ORM:

```python
PERMITTED_SORT_FIELDS = frozenset({"created_at", "price", "relevance"})

def get_sorted_items(sort_field: str, direction: str):
    if sort_field not in PERMITTED_SORT_FIELDS:
        raise ValueError("Invalid sorting parameter.")
    if direction not in {"asc", "desc"}:
        raise ValueError("Invalid sorting direction.")
    
    order_prefix = "" if direction == "asc" else "-"
    return Item.objects.order_by(f"{order_prefix}{sort_field}")
```

### Static Analysis Automation (AST Rules)

Organizations must integrate automated Abstract Syntax Tree (AST) scanning into their continuous integration (CI) pipelines to detect unescaped SQL constructs and dangerous dictionary unpacking patterns.

#### Semgrep Detection Rule: Ormar / SQLAlchemy Unsafe Text Construction
The following rule identifies dynamic strings passed to `sqlalchemy.text()` within aggregation or query contexts:

```yaml
rules:
  - id: sqlalchemy-unsafe-dynamic-text
    patterns:
      - pattern-either:
          - pattern: sqlalchemy.text($VAR)
          - pattern: text($VAR)
      - pattern-not: sqlalchemy.text("...")
      - pattern-not: text("...")
    message: "Detected dynamically constructed sqlalchemy.text() fragment. This can lead to SQL injection if input is user-controlled."
    languages: [python]
    severity: ERROR
```

#### Semgrep Detection Rule: Django Unsafe Kwargs Unpacking
The following rule detects dynamic dictionary unpacking into critical Django ORM methods:

```yaml
rules:
  - id: django-orm-unsafe-kwargs-unpacking
    patterns:
      - pattern-either:
          - pattern: $MODEL.objects.filter(**$KWARGS)
          - pattern: $MODEL.objects.exclude(**$KWARGS)
          - pattern: $MODEL.objects.get(**$KWARGS)
          - pattern: Q(**$KWARGS)
      - pattern-not-inside: |
          $KWARGS = {...}
          ...
    message: "Untrusted dynamic unpacking (**kwargs) into Django QuerySet methods can permit internal parameter injection (e.g., _connector, FilteredRelation aliases)."
    languages: [python]
    severity: WARNING
```

---

## Conclusion

The vulnerabilities outlined in CVE-2026-26198, CVE-2025-57833, and related Django and async ORM security advisories demonstrate that modern SQL injection vectors increasingly target the boundary between abstraction layers and execution engines. When ORM frameworks attempt to expose dynamic relational operations—such as custom JOIN conditions, variable aggregation parameters, or configurable boolean connectors—without strict structural whitelisting, the protection typically afforded by parameterized values breaks down. 

Securing modern database interactions requires an architectural approach: framework maintainers must treat query structure and SQL identifiers with the same distrust historically reserved for query parameters, while application developers must rigorously validate input schemas and avoid passing raw dictionaries directly into dynamic query APIs.

---

## References

* Django Project. (2025a, November 5). Django security releases issued: 5.2.8, 5.1.14, and 4.2.26. Django Project Weblog. [https://www.djangoproject.com/weblog/2025/nov/05/security-releases/](https://www.djangoproject.com/weblog/2025/nov/05/security-releases/)
* Django Project. (2025b, November 5). Detailed release notes on SQL injection vulnerabilities and connector sanitization in Django ORM. Django Project Documentation. [https://www.djangoproject.com/weblog/2025/nov/05/security-releases-detail/](https://www.djangoproject.com/weblog/2025/nov/05/security-releases-detail/)
* Django Project Security Releases. (2025, November 6). Archive of security issues: Django 4.2, 5.1, and 5.2 query compilation vulnerabilities. Django Documentation. [https://docs.djangoproject.com/en/dev/releases/security/](https://docs.djangoproject.com/en/dev/releases/security/)
* GitHub Commit Reference. (2026, February 24). Fix SQL injection in aggregate queries by enforcing model field checks: Patch for CVE-2026-26198. GitHub Repository Commits. [https://github.com/collerek/ormar/commit/d26198f98a287bf](https://github.com/collerek/ormar/commit/d26198f98a287bf)
* GitHub Security Lab. (2026, February 24). Security Advisory GHSA-ormar-2026: SQL injection in Ormar ORM aggregate expressions (CVE-2026-26198). GitHub Security Advisories. [https://github.com/collerek/ormar/security/advisories](https://github.com/collerek/ormar/security/advisories)
* National Vulnerability Database. (2026, February 24). CVE-2026-26198 Detail: Ormar ORM unvalidated column SQL injection. National Institute of Standards and Technology. [https://nvd.nist.gov/vuln/detail/CVE-2026-26198](https://nvd.nist.gov/vuln/detail/CVE-2026-26198)
* SQLAlchemy Authors. (2024, May 15). Understanding textual SQL and architectural boundaries in Core: Using text() safely. SQLAlchemy Documentation. [https://docs.sqlalchemy.org/en/20/core/sqlelement.html#sqlalchemy.sql.expression.text](https://docs.sqlalchemy.org/en/20/core/sqlelement.html#sqlalchemy.sql.expression.text)