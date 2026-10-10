# Comprehensive Security Analysis of Input Validation and Sanitization Vulnerabilities in the Python Web Ecosystem: AIOHTTP, FastAPI, and Flask/Werkzeug

## Introduction and Threat Landscape

In modern Python web architectures, the handling, parsing, and sanitization of untrusted input represent one of the most critical security boundaries. Over recent years, the rapid convergence toward asynchronous event loops—exemplified by frameworks such as FastAPI (built upon Starlette and Pydantic) and asynchronous HTTP client/server engines such as AIOHTTP—has fundamentally altered the threat model for input validation flaws ([OpenCVE, 2024](https://www.opencve.io/cve?vendor=tiangolo)). In traditional synchronous WSGI paradigms (such as Flask coupled with Werkzeug), improper input validation often results in localized request failures, cross-site scripting (XSS), or isolated worker crashes. Conversely, in asynchronous ASGI and event-loop-driven engines, input validation weaknesses can degrade the operational state of the entire server process.

Improper Input Validation (classified under CWE-20 by the Common Weakness Enumeration) continues to emerge at multiple abstraction layers across the Python networking stack. These layers span from low-level protocol parsers—handling HTTP request methods, Range headers, and control character sanitization—to mid-layer multipart stream decoders, and finally to high-level schema validators and configuration parsers ([Snyk, 2023](https://security.snyk.io/vuln/SNYK-PYTHON-AIOHTTP-6091621)). Flaws at any of these layers break security invariants, permitting attacks ranging from Cross-Site Request Forgery (CSRF) and Regular Expression Denial of Service (ReDoS) to HTTP request smuggling, header injection, and unintended operational mode activation.

This technical report provides a comprehensive analysis of critical Common Vulnerabilities and Exposures (CVEs), GitHub patches, and architectural input validation issues affecting AIOHTTP, FastAPI, Starlette, Pydantic, and Flask-based systems.

---

## Vulnerability Analysis: AIOHTTP and Low-Level HTTP Protocol Parsing

AIOHTTP serves as both an asynchronous HTTP client and server library. Because it operates directly against raw TCP byte streams, strict adherence to HTTP standards (such as RFC 9110) is essential to preserve protocol boundaries. Multiple security vulnerabilities have demonstrated that insufficient input validation in method resolution, header structure, and parameter sanitization enables high-impact protocol manipulation.

### ClientSession Request Injection: CVE-2023-49082

Under CVE-2023-49082 (CVSS v3.1 Base Score: 5.4 Medium by Snyk; 5.3 by NVD), AIOHTTP versions prior to 3.9.0 suffered from an improper input validation vulnerability within the `ClientSession` request-issuing workflow ([Snyk, 2023](https://security.snyk.io/vuln/SNYK-PYTHON-AIOHTTP-6091621)). Specifically, the library failed to sufficiently validate and sanitize the HTTP method parameter passed into client-side request generation.

```
+-----------------------------------------------------------------------------+
|                            CVE-2023-49082 Workflow                          |
|                                                                             |
|  Untrusted User Input ---> [ ClientSession.request(method, ...) ]           |
|                                         |                                   |
|                                         v                                   |
|                       Unsanitized / Unchecked HTTP Verb                     |
|                                         |                                   |
|                                         v                                   |
|      Wire Payload: "USER_CONTROLLED_VERB /path HTTP/1.1\r\nHost: ...\r\n"   |
|                                         |                                   |
|           ===> Permits HTTP Request Splitting & Arbitrary Verbs ===>        |
+-----------------------------------------------------------------------------+
```

When applications dynamically incorporate untrusted user parameters to determine the outgoing HTTP method (for example, in webhooks, forward proxies, or dynamic API gateways), an attacker can supply malicious characters, arbitrary verbs, or delimiter sequences. This deficiency allows an attacker to manipulate the HTTP request structure or generate unintended secondary requests across downstream network boundaries ([Novikov, 2023](https://gist.github.com/jnovikov)).

The vulnerability was resolved in AIOHTTP 3.9.0 by introducing strict validation on acceptable HTTP methods. For legacy deployments unable to upgrade immediately, remediation requires manual sanitization: enforcing an explicit whitelist of standardized RFC-compliant HTTP methods (such as `GET`, `POST`, `PUT`, `DELETE`, `PATCH`, `HEAD`, `OPTIONS`) before passing parameters to `ClientSession` ([Snyk, 2023](https://security.snyk.io/vuln/SNYK-PYTHON-AIOHTTP-6091621)).

### Header Protocol Boundary Enforcement: RFC 9110 Violations and CVE-2026-69244

HTTP header parsing must rigorously prevent HTTP response splitting and request smuggling. In AIOHTTP releases leading up to versions 3.14.1 through 3.14.3, multiple security gaps in header validation were identified, culminating in CVE-2026-69244 and GitHub Advisory GHSA-cq5v-8q36-5273 ([GitHub Security Advisory, 2026a](https://github.com/aio-libs/aiohttp/security/advisories/GHSA-cq5v-8q36-5273)). 

This vulnerability exposed systems utilizing AIOHTTP via pip (specifically within dependencies such as `kserve` and downstream model-serving runtimes) to protocol parsing anomalies. The defect was addressed via upstream Pull Request #13223 and finalized in Git commit `49f65d54150397892f7bcc4aae887767d51c322d`, which tagged release `v3.14.3` ([AIOHTTP Commit Archive, 2026](https://github.com/aio-libs/aiohttp/commit/49f65d54150397892f7bcc4aae887767d51c322d); [AIOHTTP Release Archive, 2026](https://github.com/aio-libs/aiohttp/releases/tag/v3.14.3)). The commit implements rigorous validation of incoming headers to ensure that serialized frames conform to standard HTTP boundaries.

Earlier in 2026, related protocol compliance issues prompted sequential patch releases:
* **Version 3.13.4 (April 2, 2026):** Implemented strict RFC 9110 compliance checks. The patch added validation routines that systematically reject header values containing forbidden control characters, specifically null bytes (`\x00`) and ASCII control codes (`\x01` through `\x1F` excluding horizontal tabs). Prior to this fix, the parser permitted non-sanitized control characters to traverse into backend handlers, enabling header injection when passed downstream.
* **Version 3.13.3 (January 22, 2026):** Resolved an input validation bug in the HTTP `Range` header parser. Attackers could supply non-standard, non-ASCII numeric representations or malformed range intervals. The patch introduced strict ASCII decimal validation, discarding any non-ASCII numeric values.

### Payload Header Validation: Commit `bf88077ebb14f4c29924b8e8904cba20c55c28b8`

On June 26, 2026, security advisory GHSA-m6qw-4cw2-hm4m disclosed an input sanitization vulnerability within AIOHTTP's payload handling mechanism ([GitHub Security Advisory, 2026b](https://github.com/advisories/GHSA-cq5v-8q36-5273)). The upstream patch commit `bf88077ebb14f4c29924b8e8904cba20c55c28b8` amended `aiohttp/payload.py` to embed internal `_safe_header` validation.

Before this fix, user-controlled parameters embedded into payload headers (such as `Content-Disposition`, custom metadata fields, or MIME sub-headers) could circumvent character set restrictions. The `_safe_header` routine operates as a defensive assertion layer: it examines outgoing payload headers, verifying that values do not contain carriage return (`\r`), line feed (`\n`), or unescaped delimiter sequences. This prevents payload headers from prematurely terminating the HTTP header block and executing body injection.

---

## Vulnerability Analysis: FastAPI, Starlette, and Pydantic Ecosystem

FastAPI relies extensively on Starlette for its underlying ASGI routing and transport layer, Pydantic for data validation and parsing, and external streaming parsers like `python-multipart` for decoding form-encoded data. Deficiencies in any part of this integrated toolchain directly compromise FastAPI applications ([OpenCVE, 2024](https://www.opencve.io/cve?vendor=tiangolo)).

### Content-Type Confusion and CSRF Exploitation: CVE-2021-32677

Under CVE-2021-32677 (CVSS v3.1: 8.2 High), FastAPI versions prior to 0.65.2 exhibited a major flaw in input media type validation ([OpenCVE, 2024](https://www.opencve.io/cve?vendor=tiangolo)). Path operations designed to receive JSON payloads parsed the request body as JSON even when the incoming `Content-Type` header was set to arbitrary non-JSON values, such as `text/plain`.

```
+-----------------------------------------------------------------------------+
|                            CVE-2021-32677 Exploitation                      |
|                                                                             |
|  Attacker Domain (Evil.com)                                                  |
|         |                                                                   |
|         | Cross-Origin fetch() / sendBeacon() with credentials              |
|         | Content-Type: "text/plain" (Browser considers it a Simple Request)|
|         v                                                                   |
|  [ Browser skips CORS preflight OPTIONS check; attaches session cookies ]   |
|         |                                                                   |
|         v                                                                   |
|  FastAPI Application (< 0.65.2)                                             |
|         |                                                                   |
|         | Content-Type is text/plain, BUT FastAPI parsed payload as JSON!   |
|         v                                                                   |
|  [ State-changing JSON endpoint executes unauthorized action via CSRF ]     |
+-----------------------------------------------------------------------------+
```

Under the W3C Cross-Origin Resource Sharing (CORS) specification, HTTP requests carrying a `Content-Type` of `application/json` require a CORS preflight exchange (`OPTIONS` request) before execution. If the target server does not explicitly authorize the origin, the browser halts the request. However, `text/plain`, `application/x-www-form-urlencoded`, and `multipart/form-data` are categorized as "Simple Requests," which bypass CORS preflights and execute immediately, carrying ambient credentials such as session cookies.

Because FastAPI unreservedly extracted JSON from `text/plain` payloads, a malicious website could issue authenticated, state-changing cross-origin requests directly against FastAPI endpoints using standard browser APIs without triggering a preflight check. 

FastAPI patched this in version 0.65.2 by restricting JSON body deserialization strictly to requests declaring `application/json` or an RFC-compliant structured JSON media subtype (e.g., `application/geo+json`, `application/vnd.api+json`). For environments where immediate framework upgrades were unfeasible, mitigation required inserting ASGI middleware to validate incoming `Content-Type` headers and reject non-JSON media types prior to handler execution ([OpenCVE, 2024](https://www.opencve.io/cve?vendor=tiangolo)).

### Event-Loop Starvation via ReDoS: CVE-2024-24762 and CVE-2024-3772

In asynchronous frameworks, CPU-bound tasks execute on the main thread running the `asyncio` event loop unless explicitly dispatched to background thread pools. Consequently, regular expression catastrophic backtracking (ReDoS) represents an acute availability threat.

#### 1. CVE-2024-24762 (`python-multipart`)
FastAPI incorporates `python-multipart` as its default parser for streaming multipart/form-data payloads. Under CVE-2024-24762 (CVSS v3.1: 7.5 High), `python-multipart` utilized an unanchored, inefficient regular expression to parse options within the HTTP `Content-Type` header ([OpenCVE, 2024](https://www.opencve.io/cve?vendor=tiangolo)).

By transmitting a crafted `Content-Type` header with nested or repeated option parameters, an attacker could force the regex engine into exponential backtracking. Because header parsing occurs synchronously during request ingestion, this stalled the `asyncio` event loop indefinitely. While the worker thread remained trapped in the backtracking loop, all other concurrent network connections on that process were blocked, yielding a complete Denial of Service. The vulnerability was mitigated in `python-multipart` version 0.0.7 by replacing the vulnerable regular expression with deterministic, linear-time token parsing ([OpenCVE, 2024](https://www.opencve.io/cve?vendor=tiangolo)).

#### 2. CVE-2024-3772 (Pydantic `EmailStr`)
On April 15, 2024, CVE-2024-3772 was disclosed against Pydantic’s built-in `EmailStr` field validator. Applications utilizing Pydantic models to parse incoming JSON email structures inherited a catastrophic backtracking vulnerability. A crafted email string containing specific sequences of domain characters and delimiters could trap the internal regex engine in an exponential search path. The Pydantic maintainers resolved the issue in version 2.4.0 and backported the fix to version 1.10.13, modifying the regular expression to enforce linear-time boundary checks.

### Ecosystem Vulnerabilities and Data Exposure

Additional vulnerabilities across the broader FastAPI ecosystem emphasize that schema definitions alone do not replace comprehensive input and output sanitization:
* **`fastapi-guard` (Fixed in version 3.0.2):** This rate-limiting and route-protection module suffered from a regex pattern bypass. Flawed length boundary handling allowed attackers to bypass inspection patterns by prepending or appending specific character sequences. Version 3.0.2 introduced strict length checking and boundary anchors.
* **`fastapi-admin` (CVE-2024-42816):** Exposed administrative interfaces to Cross-Site Scripting (XSS). The vulnerability stemmed from direct HTML string concatenation of untrusted input within administrative dashboard templates. The patch enforces context-aware auto-escaping within template engines and requires sanitization of dynamic fields using explicit filters or `html.escape`.
* **FastAPI Sensitive Data Exposure (CVE-2026-2975 and CVE-2026-2976):** Identified conditions where dynamic response serialization and route parameter processing inadvertently disclosed internal memory references and unvalidated model defaults, necessitating stricter serialization filters.
* **FastAPI 0.141.1 Security Posture:** Audits cataloging vulnerabilities across FastAPI versions identify that while FastAPI core maintains a limited attack surface, downstream integrations remain highly vulnerable to deserialization and event-loop starvation when third-party components neglect sanitization.

---

## Vulnerability Analysis: Flask and Werkzeug Ecosystem Flaws

Synchronous Python web frameworks rooted in the WSGI standard—primarily Flask and its underlying library Werkzeug—encounter distinct input validation and configuration sanitization vulnerabilities.

### Configuration Parsing Flaws and Debug Mode Exposure

In security advisories disclosed between April 8 and April 9, 2026, the Unfurl framework (through version 2025.08) was found to contain an improper input validation vulnerability in configuration parsing. The parser failed to sanitize and strictly validate user-supplied configuration flags and environmental overrides.

Because of this validation omission, the application defaulted to enabling Flask's built-in interactive debug mode (`DEBUG = True`). Exposing Flask debug mode in production environments presents an immediate Remote Code Execution (RCE) risk. Werkzeug's interactive debugger enables the execution of arbitrary Python expressions directly in the browser upon unhandled exceptions. If the debugger pin is compromised, intercepted, or left unauthenticated, improper validation of configuration inputs escalates directly to full server compromise.

### Multipart File Upload Name Sanitization and Reflection Vulnerabilities

On February 27, 2026, an input sanitization vulnerability was documented in Python file upload handling workflows affecting WSGI and ASGI runtimes. The defect originated from insufficient validation and sanitization of the `filename` and `name` parameters within `multipart/form-data` payloads.

When file upload routines accept parameter values without stripping path traversal sequences (`../`, `..\`) or null bytes, attackers can bypass directory restrictions to write files to arbitrary locations on the filesystem. Furthermore, reflecting raw `name` parameters back into HTTP response headers or HTML notification banners introduces reflected Cross-Site Scripting (XSS). Remediation mandates that developers pass all filename inputs through sanitization functions (such as Werkzeug’s `secure_filename()`), validate character lengths, and enforce strict alphanumeric allowlists before reflecting parameters or executing filesystem I/O.

---

## Technical Comparison of Input Validation Deficiencies

The following structured matrix compares the input validation vulnerabilities across the Python web ecosystem, outlining the vulnerability mechanics, severity metrics, and remediation approaches.

| Vulnerability Identifier | Impacted Framework / Package | Weakness Type (CWE) | CVSS v3.1 Score | Primary Attack Vector | Technical Root Cause | Resolution / Fix Details |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **CVE-2023-49082** | `aiohttp` (< 3.9.0) | CWE-20 (Improper Input Validation) | 5.3 / 5.4 (Medium) | Client-side HTTP Request Manipulation / Injection | Unsanitized HTTP method parameter in `ClientSession` | Upgrade to `aiohttp` >= 3.9.0; enforce strict method allowlist ([Snyk, 2023](https://security.snyk.io/vuln/SNYK-PYTHON-AIOHTTP-6091621)) |
| **CVE-2026-69244** / **GHSA-cq5v-8q36-5273** | `aiohttp` (3.14.1 - 3.14.3) | CWE-20 / Protocol Parsing Violation | High | Header Injection & Smuggling in Model Serving | Non-compliant header boundary enforcement | Upstream PR #13223, Git Commit `49f65d54150397892f7bcc4aae887767d51c322d`, Tag `v3.14.3` ([AIOHTTP Commit Archive, 2026](https://github.com/aio-libs/aiohttp/commit/49f65d54150397892f7bcc4aae887767d51c322d)) |
| **AIOHTTP Range Defect** | `aiohttp` (< 3.13.3) | CWE-20 (Input Validation) | Moderate | DoS / Resource Allocation via Range Header | Range parser accepted non-ASCII numeric inputs | Patch released January 22, 2026; enforces strict ASCII decimal validation |
| **AIOHTTP RFC 9110 Violation** | `aiohttp` (< 3.13.4) | CWE-74 / RFC Non-Compliance | Moderate | Header Injection / Smuggling | Unchecked null bytes and ASCII control characters in headers | Patch released April 2, 2026; rejects control characters in headers |
| **GHSA-m6qw-4cw2-hm4m** | `aiohttp` (payload handling) | CWE-20 / Injection | Moderate | Premature Header Termination / Body Injection | Missing character validation in payload headers | Patch Commit `bf88077ebb14f4c29924b8e8904cba20c55c28b8` adding `_safe_header` checks |
| **CVE-2021-32677** | `FastAPI` (< 0.65.2) | CWE-352 / CWE-20 | 8.2 (High) | Cross-Site Request Forgery (CSRF) via `text/plain` | Deserialized JSON payloads regardless of incoming `Content-Type` | Upgraded to >= 0.65.2; enforce JSON parsing only on `application/json` or `+json` ([OpenCVE, 2024](https://www.opencve.io/cve?vendor=tiangolo)) |
| **CVE-2024-24762** | `python-multipart` (< 0.0.7) / `Starlette` / `FastAPI` | CWE-1333 (ReDoS) | 7.5 (High) | Denial of Service (Event Loop Starvation) | Catastrophic backtracking in `Content-Type` options regex | Upgrade `python-multipart` to >= 0.0.7; regex replaced with linear-time parsing ([OpenCVE, 2024](https://www.opencve.io/cve?vendor=tiangolo)) |
| **CVE-2024-3772** | `Pydantic` (< 2.4.0, < 1.10.13) | CWE-1333 (ReDoS) | Medium | CPU Exhaustion via Email Validation | Nested quantifier backtracking in `EmailStr` regex | Upgrade Pydantic to >= 2.4.0 (or >= 1.10.13); regex anchored and refactored |
| **CVE-2024-42816** | `fastapi-admin` pro | CWE-79 (Cross-Site Scripting) | Medium | Client-side Session Hijacking | Direct HTML concatenation of untrusted input in templates | Upgrade patched release; enforce automatic template escaping & `html.escape` |
| **Unfurl Flaw** | Unfurl (through 2025.08) / `Flask` | CWE-20 (Improper Input Validation) | High | Remote Code Execution via Debugger Pin | Unchecked configuration input enabled Flask debug mode | Sanitize configuration parsing; explicitly set `DEBUG = False` in production |

---

## Strategic Remediation, Architectural Hardening, and Expert Assessment

### Architectural Vulnerability: Asynchronous Amplification

Based on the technical evidence across these CVEs, asynchronous architectures amplify the severity of algorithmic complexity and input validation flaws compared to synchronous WSGI frameworks. 

In a traditional WSGI server (e.g., Gunicorn running synchronous Flask/Werkzeug workers), if an attacker triggers a catastrophic ReDoS flaw or issues a payload that causes a worker to stall, the impact is confined to that single process worker. The remaining workers continue serving incoming traffic. 

In an asynchronous ASGI architecture (e.g., Uvicorn running Starlette and FastAPI, or an AIOHTTP server loop), hundreds or thousands of concurrent requests rely on a single-threaded cooperative event loop. When a vulnerability like CVE-2024-24762 (`python-multipart`) or CVE-2024-3772 (`Pydantic`) forces the Python interpreter into an intensive CPU backtracking loop, the event loop cannot cycle. All concurrent sessions freeze, health checks fail, reverse proxies (like NGINX or Envoy) drop connections with 504 Gateway Timeouts, and the entire node collapses.

```
WSGI Architecture (Synchronous)                 ASGI Architecture (Asynchronous)
+-------------------------------+              +-------------------------------+
| Worker 1: [ReDoS Attack Hit]  |              | Event Loop Thread:            |
|   --> STALLED (1 Worker Lost) |              |   Req 1 -> Req 2 -> Req 3 ... |
|                               |              |               |               |
| Worker 2: [Normal Request]    |              |   [ReDoS Attack Triggered]    |
|   --> 200 OK (Traffic Serviced)|              |               |               |
| Worker 3: [Normal Request]    |              |   --> WHOLE LOOP BLOCKED      |
|   --> 200 OK (Traffic Serviced)|              |   --> ALL CONCURRENT USERS DIE|
+-------------------------------+              +-------------------------------+
```

Relying solely on high-level application code or declarative Pydantic schemas for input validation is insufficient. Framework developers and consumers often mistake schema conversion (type coercion) for defensive security sanitization. As evidenced by FastAPI's CVE-2021-32677, automatic parsing without strict protocol header enforcement opens avenues for severe web vulnerabilities such as preflight-less CSRF attacks.

### Practical Engineering Recommendations

To achieve robust defense-in-depth across Python web stacks, development teams must enforce security constraints across three key architectural tiers:

#### 1. Ingress and Protocol Edge Sanitization
* **Enforce Strict Character Filters:** Strip or reject ASCII control characters (`\x00` through `\x1F`) and CRLF sequences (`\r\n`) at the reverse proxy or ASGI entrypoint before payloads reach application code, mitigating HTTP splitting and smuggling.
* **Strict Media-Type Enforcement:** Ensure application endpoints validate that incoming payloads strictly match the declared `Content-Type`. Reject requests where `Content-Type` is omitted, ambiguous, or mismatched with the internal deserializer.

#### 2. Event-Loop Protection and ReDoS Mitigation
* **Regex Engine Auditing:** Audit custom validators and external parsing dependencies for catastrophic backtracking. Disallow nested quantifiers (e.g., `(a+)+$`) and unbounded greedy groups.
* **Offload Heavy Parsing:** If complex parsing or validation is required on large user payloads, offload the processing to a background execution thread (`asyncio.to_thread`) or a distributed task queue (such as Celery or RQ) to preserve the responsiveness of the primary event loop.

#### 3. Defensive Serialization and Configuration Control
* **Explicit Configuration Hardening:** Never allow dynamic user inputs, headers, or query parameters to dictate application execution modes. Explicitly hardcode `debug=False` in production Flask and FastAPI environments.
* **Safe Encoding Practices:** Contextually encode dynamic data before reflecting it back to the client. When generating administrative or API dashboard interfaces, rely on template engines with auto-escaping enabled by default, supplemented by `html.escape()` for dynamic parameter values.

---

## References

* AIOHTTP Commit Archive. (2026, May 15). *Merge pull request #13223 from aio-libs/fix-header-parsing (commit 49f65d54150397892f7bcc4aae887767d51c322d)*. GitHub. [https://github.com/aio-libs/aiohttp/commit/49f65d54150397892f7bcc4aae887767d51c322d](https://github.com/aio-libs/aiohttp/commit/49f65d54150397892f7bcc4aae887767d51c322d)
* AIOHTTP Pull Requests. (2026, May 14). *Fix header validation parsing anomalies (#13223)*. GitHub. [https://github.com/aio-libs/aiohttp/pull/13223](https://github.com/aio-libs/aiohttp/pull/13223)
* AIOHTTP Release Archive. (2026, May 16). *Release v3.14.3*. GitHub. [https://github.com/aio-libs/aiohttp/releases/tag/v3.14.3](https://github.com/aio-libs/aiohttp/releases/tag/v3.14.3)
* GitHub Security Advisory. (2026a, May 16). *GHSA-cq5v-8q36-5273: Header validation vulnerability in aiohttp*. GitHub Security Advisories. [https://github.com/aio-libs/aiohttp/security/advisories/GHSA-cq5v-8q36-5273](https://github.com/aio-libs/aiohttp/security/advisories/GHSA-cq5v-8q36-5273)
* GitHub Security Advisory. (2026b, June 26). *GHSA-m6qw-4cw2-hm4m: Safe header validation injection in aiohttp payload handling*. GitHub Security Advisories. [https://github.com/advisories/GHSA-cq5v-8q36-5273](https://github.com/advisories/GHSA-cq5v-8q36-5273)
* Novikov, I. (2023, November 27). *Proof of concept and analysis of HTTP request manipulation via ClientSession in aiohttp (CVE-2023-49082)*. GitHub Gist. [https://gist.github.com/jnovikov](https://gist.github.com/jnovikov)
* OpenCVE. (2024, May 9). *Fastapi CVEs and security vulnerabilities*. OpenCVE Guide. [https://www.opencve.io/cve?vendor=tiangolo](https://www.opencve.io/cve?vendor=tiangolo)
* Snyk. (2023, November 28). *Improper input validation in aiohttp (CVE-2023-49082)*. Snyk Vulnerability Database. [https://security.snyk.io/vuln/SNYK-PYTHON-AIOHTTP-6091621](https://security.snyk.io/vuln/SNYK-PYTHON-AIOHTTP-6091621)