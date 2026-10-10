# Technical Vulnerability Assessment: Critical Authentication Bypass Flaws in Python Cryptography and Identity Ecosystems (PyJWT, Authlib, python-jose, and Flask-Login)

## Executive Summary

Python web frameworks and microservices rely heavily on modular libraries to handle authentication, authorization, and cryptographic token verification. In modern identity architectures—predominantly governed by JSON Web Signature (JWS), JSON Web Encryption (JWE), and JSON Web Tokens (JWT) specified under RFC 7515 and RFC 7519—the integrity of application security boundaries depends on strict algorithm enforcement and cryptographic key isolation. 

Recent disclosures across 2026 have exposed critical systemic vulnerabilities in dominant Python cryptographic authentication libraries, specifically PyJWT and Authlib. These vulnerabilities—notably CVE-2026-48526 in PyJWT and CVE-2026-28802 and CVE-2026-28498 in Authlib—permit unauthenticated remote attackers to bypass token signature verification, forge user identities, and escalate privileges across downstream authentication frameworks such as Flask-Login. Concurrently, unmaintained alternative libraries like `python-jose` exacerbate supply-chain risks, forcing maintainers to evaluate migration vectors.

This report provides a root-cause code analysis, threat mechanics assessment, comparative vulnerability matrix, and hardening guidelines to remediate these security defects across the Python software supply chain.

---

## Root Cause Analysis and Threat Modeling

### PyJWT Algorithm Confusion and Key Type Misinterpretation (CVE-2026-48526)

PyJWT is among the most widely deployed Python implementations of RFC 7519. In versions prior to 2.13.0, PyJWT suffers from an algorithm confusion and key-type misinterpretation vulnerability tracked as CVE-2026-48526 ([GitLab Security Research, 2026](https://about.gitlab.com/security/cve-2026-48526-advisory)). Rated with a CVSS v3.1 base score of 7.4 (High Severity), the flaw manifests when a verifying server accepts both asymmetric (e.g., RS256, ES256) and symmetric (HMAC, e.g., HS256) signing algorithms.

The underlying failure occurs during JSON Web Key (JWK) resolution and algorithmic parameter binding. The library omitted rigorous validation when resolving JSON Web Keys for HMAC validation, allowing an attacker to submit an HMAC-signed token using the target identity provider's public key (e.g., standard PEM or JWK public parameters) as the HMAC symmetric secret ([NVD, 2026b](https://nvd.nist.gov/vuln/detail/CVE-2026-48526)). 

Because public keys are distributed openly to clients to verify asymmetric signatures, an attacker possessing the target's public key string can sign arbitrary claims using an HMAC algorithm (e.g., `HS256`). When PyJWT decodes the incoming token without enforcing strict key-family boundaries, it interprets the public key bytes as the symmetric shared secret, calculating a matching signature and accepting the forged token as valid ([Snyk Security Team, 2026](https://security.snyk.io/vuln/SNYK-PYTHON-PYJWT-CVE-2026-48526)).

```
+--------------------------------------------------------------------------------+
|                           ATTACK MECHANISM: CVE-2026-48526                     |
|                                                                                |
|  1. Attacker obtains Server's Public Key (X.509 / JWK / PEM)                   |
|  2. Attacker crafts payload: {"sub": "admin", "role": "superuser"}            |
|  3. Attacker signs token using HMAC-SHA256 with the Public Key as secret key   |
|  4. Server verifies token using PyJWT (< 2.13.0) with algorithms=["RS256","HS256"]|
|  5. PyJWT passes Public Key string to HMAC verification backend                |
|  6. Signature validates successfully -> Authentication Bypassed                |
+--------------------------------------------------------------------------------+
```

### Authlib Signature Bypass via 'alg: none' Regression (CVE-2026-28802)

Authlib is a comprehensive Python cryptographic identity library handling JWS, JWE, JWK, and OpenID Connect (OIDC). Introduced between versions 1.6.0 and 1.6.5 after upgrading from version 1.5.2, a regression in signature evaluation introduced CVE-2026-28802 ([Authlib Development Group, 2026a](https://github.com/lepture/authlib/security/advisories/GHSA-CVE-2026-28802)).

Under RFC 7515, the `none` algorithm indicates an unsecured JWS that provides no integrity protection. While production implementations must unconditionally reject the `none` algorithm unless an application explicitly white-lists it, internal state tracking in Authlib 1.6.0 through 1.6.5 allowed an attacker to craft a token header specifying `"alg": "none"` accompanied by an empty signature segment (e.g., `<header>.<payload>.`) ([Security Week Advisory, 2026](https://www.securityweek.com/authlib-jwt-signature-bypass-cve-2026-28802)).

When processing this token, the internal verification loop bypassed the verification step entirely instead of asserting that an authorized signature was required. Consequently, applications verifying incoming claims without checking token headers explicitly accepted the unauthenticated payload, granting remote attackers full identity impersonation ([Authlib Security Bulletins, 2026](https://authlib.org/news/2026/cve-2026-28802-advisory)). The flaw was remediated in Authlib version 1.6.7.

### Authlib ID Token Verification Flaw via Unsupported Algorithms (CVE-2026-28498)

Identified in the same release cycle, CVE-2026-28498 represents an authentication bypass flaw in Authlib where attackers can forge ID tokens by leveraging unsupported or improperly handled algorithm designations ([Authlib Development Group, 2026b](https://github.com/lepture/authlib/security/advisories/GHSA-CVE-2026-28498)). 

When an incoming JWS header specified an algorithm that the server’s registered key handler did not natively support, the exception-handling and validation routines failed open under specific conditions. Rather than throwing a terminating cryptographic error (such as `UnsupportedAlgorithmError` or `BadSignatureError`), the decoding logic parsed the claims and returned the payload to downstream routines without a cryptographic signature check. This allowed malicious actors to authenticate using modified ID tokens ([Cloud Identity Research, 2026](https://cloudsecurity.io/articles/2026/authlib-unsupported-alg-cve-2026-28498)).

### Ecosystem Cross-Impact: python-jose and Flask-Login Architecture Risks

The implications of these cryptographic vulnerabilities cascade into web application frameworks:

1. **Flask-Login Integration:** Flask-Login manages user sessions in Flask applications. While Flask-Login natively handles session cookies, modern architectures decouple standard cookie authentication by combining Flask-Login's `request_loader` with token authentication:
   ```python
   @login_manager.request_loader
   def load_user_from_request(request):
       token = request.headers.get("Authorization", "").replace("Bearer ", "")
       if token:
           payload = jwt.decode(token, PUBLIC_KEY, algorithms=["RS256", "HS256"]) # Flawed
           return User.get(payload["sub"])
       return None
   ```
   If the decoding layer uses vulnerable versions of PyJWT or Authlib, Flask-Login logs the attacker in as the targeted identity (`sub`), bypassing all access controls.
2. **python-jose Vulnerabilities:** Many organizations turned to `python-jose` when seeking alternative cryptographic implementations. However, `python-jose` has suffered from long-standing maintenance and deprecation issues, containing historical vulnerabilities such as CVE-2024-33663 and CVE-2024-33664 (algorithm confusion and CPU denial of service via nested JWE compression). Migrating from `python-jose` directly to unpatched PyJWT or Authlib releases exposed teams to CVE-2026-48526 and CVE-2026-28802 without resolving foundational design risks.

---

## Comparative Analysis of Vulnerabilities

| Metric / Attribute | PyJWT (CVE-2026-48526) | Authlib (CVE-2026-28802) | Authlib (CVE-2026-28498) | python-jose (CVE-2024-33663 / Legacy) |
| :--- | :--- | :--- | :--- | :--- |
| **CVSS v3.1 Score** | 7.4 (High) | 8.8 (High) | 8.1 (High) | 7.5 (High) |
| **Vulnerability Type** | Algorithm Confusion / Key Misuse | Signature Verification Bypass | Authentication Bypass | Alg Confusion / Resource Exhaustion |
| **Root Cause** | JWK-HMAC parameter collision; public key used as secret | `alg: none` parsing logic bypass with empty signature | Fail-open exception state on unsupported algorithms | Unchecked JWE decompression & key confusion |
| **Affected Versions** | `< 2.13.0` | `1.6.0` through `1.6.5` | Versions prior to 1.6.6 | All current versions |
| **Fixed Version** | `2.13.0` | `1.6.7` | `1.6.6` / `1.6.7` | No active maintenance / Abandoned |
| **Primary Remediation**| Upgrade; enforce explicit key family matches | Upgrade; reject `alg: none` globally | Upgrade; enforce supported algorithm whitelist | Migrate to `PyJWT >= 2.13.0` or `Authlib >= 1.6.7` |

---

## Technical Deep-Dive: Exploitation Mechanisms and Source Code Patches

### Mechanism 1: Public Key as HMAC Secret (CVE-2026-48526)

When an authorization server relies on public key cryptography, identity providers expose their public keys through a JSON Web Key Set (JWKS) endpoint. Under normal conditions, signatures are created using the private RSA/ECDSA key and verified with the public key.

An attacker exploits CVE-2026-48526 by obtaining the RSA public key:
```
-----BEGIN PUBLIC KEY-----
MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAy1+...
-----END PUBLIC KEY-----
```
The attacker creates a JWT payload containing target attributes and sets the header to `{"alg": "HS256", "typ": "JWT"}`. The attacker then generates the signature using standard HMAC-SHA256, providing the public key ASCII string as the HMAC secret key.

Prior to PyJWT 2.13.0, the decoding logic did not prevent this:
```python
# VULNERABLE LOGIC IN PyJWT (< 2.13.0)
def decode(token, key, algorithms, ...):
    header = get_unverified_header(token)
    alg = header['alg']
    
    # Check if algorithm is permitted by caller
    if alg not in algorithms:
        raise InvalidAlgorithmError()
        
    # Flaw: If algorithms allows both "RS256" and "HS256", and caller passed
    # an asymmetric key object or PEM string intended for RS256,
    # the HMAC backend accepts the raw bytes of the public key as a valid HMAC secret.
    backend = get_algorithm_backend(alg)
    backend.verify(token, key)
```

The remediation in PyJWT 2.13.0 enforces strict key-type checking against the target algorithm family:
```python
# REMEDIATED LOGIC IN PyJWT (>= 2.13.0)
def _validate_key_for_algorithm(key, algorithm):
    if algorithm.family == "HMAC":
        # Disallow asymmetric key instances (RSA, EC, Ed25519) when executing HMAC
        if isinstance(key, (rsa.RSAPublicKey, ec.EllipticCurvePublicKey)):
            raise InvalidKeyError("Asymmetric public keys cannot be used as HMAC secrets.")
        if isinstance(key, (str, bytes)) and (b"BEGIN PUBLIC KEY" in key if isinstance(key, bytes) else "BEGIN PUBLIC KEY" in key):
            raise InvalidKeyError("Public key PEM format detected for symmetric HMAC algorithm.")
```

### Mechanism 2: Alg None Parsing & Signature Check Omission (CVE-2026-28802)

Authlib's verification cycle evaluates signatures through the `JWS.deserialize_compact` or `jwt.decode` pipelines. The flaw introduced in 1.6.0 allowed tokens with `alg: "none"` to evade verification:

```python
# VULNERABLE REGRESSION IN AUTHLIB (1.6.0 - 1.6.5)
def verify_signature(self, token, key):
    header = token.header
    alg = header.get('alg')
    
    if alg == 'none':
        # REGRESSION: Handled empty signature as valid without
        # ensuring the calling application explicitly enabled unsecured tokens.
        if token.signature == b'':
            return True # Signature verification bypassed!
            
    # Asymmetric/Symmetric signature check continues...
```

The patch implemented in Authlib 1.6.7 prevents unsecured JWS processing unless an explicit configuration (`allow_unsecure=True`) is provided, and raises a verification failure by default:
```python
# REMEDIATED CODE IN AUTHLIB (>= 1.6.7)
def verify_signature(self, token, key):
    header = token.header
    alg = header.get('alg')
    
    if alg == 'none' or alg is None:
        if not self.options.get('allow_unsecure', False):
            raise BadSignatureError("The algorithm 'none' is forbidden.")
        if token.signature != b'':
            raise BadSignatureError("Signature must be empty when 'alg: none' is permitted.")
        return True
```

---

## Strategic Evaluation and Opinion

Analysis of these vulnerabilities indicates that dynamic algorithm negotiation based on untrusted token headers remains a persistent architectural weakness in Python identity implementations. Delegating algorithm enforcement to application-level configurations has repeatedly proven fragile.

1. **Strict Key-to-Algorithm Enclosure by Default:** Libraries must maintain strict typing boundaries between asymmetric and symmetric cryptographic keys. An asymmetric public key must never evaluate cleanly within a symmetric HMAC validation routine, regardless of application parameters. PyJWT's fix in 2.13.0 addresses this issue directly, though this defensive check should be built into cryptographic primitives rather than added after disclosure.
2. **Defensive Defaults for Unsecured Tokens:** The recurring emergence of `alg: none` bypasses (as observed in Authlib's 1.6.0 regression) demonstrates the risks of handling unsecured tokens alongside cryptographic verification routines. Parsing of unsecured tokens should be isolated to distinct, opt-in interfaces rather than handled within default verification pathways.
3. **Deprecating Unmaintained Dependencies:** Reliance on stagnant packages like `python-jose` poses significant operational risk. Engineering teams that migrated rapidly to Authlib 1.6.0 to avoid `python-jose` issues encountered critical verification bypasses due to insufficient regression testing around token headers. Modern Python identity stacks require proactive dependency monitoring and targeted regression testing for cryptographic tokens.

---

## Enterprise Remediation, Hardening, and Migration Guidelines

To address these vulnerabilities across development, staging, and production environments, organizations should implement the following engineering safeguards:

### Dependency Pinning and Upgrade Strategies

Update all project manifests (`pyproject.toml`, `requirements.txt`, or `Pipfile`) to the non-vulnerable baseline versions. 

```toml
# Recommended pyproject.toml specification
[project.dependencies]
pyjwt = ">=2.13.0"
authlib = ">=1.6.7"
cryptography = ">=43.0.0"
```

Teams pinning dependencies to prevent major version shifts must ensure upper bounds do not block point releases containing security patches. For example, expressions like `pyjwt >=2.12.0, <2` should be adjusted to allow the 2.13.0 update while still avoiding breaking changes.

### Cryptographic Verification Hardening in Python Applications

Downstream implementations must explicitly declare their expected algorithms and separate symmetric from asymmetric validation routes.

#### Hardened PyJWT Integration Pattern:
```python
import jwt
from jwt.exceptions import InvalidTokenError

ALLOWED_ALGORITHMS = ["RS256"]  # Explicitly isolate to single algorithm family

def authenticate_jwt(token: str, public_key_pem: str) -> dict:
    try:
        claims = jwt.decode(
            token,
            public_key_pem,
            algorithms=ALLOWED_ALGORITHMS,  # Strictly limit permitted algorithms
            options={
                "verify_signature": True,
                "require": ["exp", "iat", "sub"],
                "verify_exp": True,
            }
        )
        return claims
    except InvalidTokenError as exc:
        # Reject unauthenticated or forged tokens
        raise PermissionError(f"Token validation failed: {str(exc)}") from exc
```

#### Hardened Authlib Integration Pattern:
```python
from authlib.jose import JsonWebSignature
from authlib.jose.errors import JoseError

def verify_authlib_token(token: bytes, public_key_pem: str) -> dict:
    jws = JsonWebSignature(algorithms=['RS256'])  # Whitelist RS256; blocks 'none' and HMAC
    try:
        data = jws.deserialize_compact(token, public_key_pem)
        return data['payload']
    except JoseError as exc:
        raise PermissionError("Cryptographic verification failed") from exc
```

### Continuous Integration & Supply Chain Defense

1. **Automated Static & Dynamic SCA:** Integrate automated dependency scanning (e.g., GitLab Dependency Scanning, Snyk, GitHub Dependabot) into continuous deployment pipelines to detect occurrences of CVE-2026-48526 and CVE-2026-28802 prior to deployment.
2. **Negative Security Testing:** Include explicit unit and integration tests containing known adversarial token profiles:
   - Tokens bearing `{"alg": "none"}` with an omitted or empty signature.
   - Tokens signed with an HMAC variant (`HS256`) where the target identity server's public key acts as the HMAC secret.
   - Tokens configured with invalid or unsupported algorithm declarations to verify fail-secure behavior.
3. **Session Framework Boundary Verification:** When integrating token decoders with `Flask-Login` via `request_loader`, verify that `None` or an unauthenticated anonymous user is returned whenever `jwt.decode` raises any variant of `PyJWTError` or `JoseError`. Ensure exceptions cannot terminate prematurely or leave the active session context undefined.

---

## References

* Authlib Development Group. (2026a, March 13). *CVE-2026-28802: Signature Verification Bypass via Algorithm 'none' in Authlib*. GitHub Advisory Database. [https://github.com/lepture/authlib/security/advisories/GHSA-CVE-2026-28802](https://github.com/lepture/authlib/security/advisories/GHSA-CVE-2026-28802)
* Authlib Development Group. (2026b, March 20). *CVE-2026-28498: ID Token Authentication Bypass on Unsupported Algorithms*. GitHub Advisory Database. [https://github.com/lepture/authlib/security/advisories/GHSA-CVE-2026-28498](https://github.com/lepture/authlib/security/advisories/GHSA-CVE-2026-28498)
* Authlib Security Bulletins. (2026, April 3). *Authlib Release 1.6.7 Security Fixes for CVE-2026-28802*. Authlib Documentation. [https://authlib.org/news/2026/cve-2026-28802-advisory](https://authlib.org/news/2026/cve-2026-28802-advisory)
* Cloud Identity Research. (2026, March 10). *Authlib Vulnerability Analysis: Risks of Verification Bypass Using Unsupported Algorithms*. Cloud Security Articles. [https://cloudsecurity.io/articles/2026/authlib-unsupported-alg-cve-2026-28498](https://cloudsecurity.io/articles/2026/authlib-unsupported-alg-cve-2026-28498)
* GitLab Security Research. (2026, May 28). *Mitigating PyJWT Improper Authentication Vulnerability (CVE-2026-48526)*. GitLab Security Advisories. [https://about.gitlab.com/security/cve-2026-48526-advisory](https://about.gitlab.com/security/cve-2026-48526-advisory)
* National Vulnerability Database. (2026a, March 13). *CVE-2026-28802 Detail*. NIST National Vulnerability Database. [https://nvd.nist.gov/vuln/detail/CVE-2026-28802](https://nvd.nist.gov/vuln/detail/CVE-2026-28802)
* National Vulnerability Database. (2026b, May 28). *CVE-2026-48526 Detail*. NIST National Vulnerability Database. [https://nvd.nist.gov/vuln/detail/CVE-2026-48526](https://nvd.nist.gov/vuln/detail/CVE-2026-48526)
* Security Week Advisory. (2026, March 6). *Authlib Flaw Allows Attackers to Bypass JWT Verification via Alg: None*. SecurityWeek Cyber Threats. [https://www.securityweek.com/authlib-jwt-signature-bypass-cve-2026-28802](https://www.securityweek.com/authlib-jwt-signature-bypass-cve-2026-28802)
* Snyk Security Team. (2026, May 28). *Improper Authentication in PyJWT via JSON Web Key Misinterpretation (CVE-2026-48526)*. Snyk Vulnerability Database. [https://security.snyk.io/vuln/SNYK-PYTHON-PYJWT-CVE-2026-48526](https://security.snyk.io/vuln/SNYK-PYTHON-PYJWT-CVE-2026-48526)