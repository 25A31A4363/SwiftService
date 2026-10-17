# R5 Operational Intelligence Platform: Security, Privacy, and AI Governance
## Security Assumptions, Threat Model, and Operational Limitations

### 1. Executive Security Architecture Overview

The R5 Enterprise Physical Operational Intelligence Core is designed with a defense-in-depth security model specifically tailored for multi-location physical retail, grocery, and facility operations. The platform ingests noisy, multilingual operational feedback, translates it into deterministic operational issues, routes work orders, and synthesizes executive intelligence briefs.

Because physical operations interface with real human customers and frontline employees, security, privacy, and algorithmic governance are fundamental operational requirements.

---

### 2. Core Security Controls Implemented (Phase 16)

| Security Control | Implementation Mechanism | Enforcement Point |
| :--- | :--- | :--- |
| **RBAC Enforcement** | Strict role-to-permission mapping (`ROLE_PERMISSIONS`) with dynamic DB override capability | Every sensitive API router via `require_permission(Permission.*)` |
| **Store Scope Isolation** | Multi-tenant and regional isolation (`can_access_store`) | Store-level and region-level queries and mutation handlers |
| **Input Validation & Sanitization** | `InputSanitizer`: UTF-8 NFKC normalization, null byte removal, script/HTML tag stripping, length bounding | Input gateway on all API payloads |
| **Prompt Injection Guard** | `PromptInjectionGuard`: Regular-expression heuristic matrix detecting overrides, role hijack, delimiters, and exfiltration | Before AI Gateway invocation (`/security/ai/execute`) |
| **PII Minimization / Redaction** | `PIIMinimizer`: Masks emails, phone numbers, payment card numbers, Aadhaar/SSN | Automated before any AI model call; role-based record minimization |
| **Secret & Token Handling** | Salted PBKDF2-HMAC-SHA256 password hashing; HS256 JWT tokens; constant-time `hmac.compare_digest` | `backend/app/core/security.py` |
| **Safe Logging** | `StructuredFormatter` with `LogScrubber` filter masking Bearer JWTs, passwords, secrets, card numbers | Log output on `sys.stdout` and file streams |
| **Security Audit Logging** | `SecurityAuditService` recording security events into `security_audit_events` | Injection attempts, rate limit breaches, unsafe uploads, purges, overrides |
| **Data Retention Engine** | `RetentionService` with configurable policies (`FEEDBACK_ITEMS`, `INVESTIGATION_QUESTIONS`, `ALERTS`, `AUDIT_LOGS`) | Scheduled / on-demand compliance sweeps (`PURGE` or `ANONYMIZE`) |
| **Model / Provider Abstraction** | `AIProviderInterface` decoupling business logic from `LOCAL_DETERMINISTIC` and `EXTERNAL_ENTERPRISE_LLM` | `AIModelGateway` |
| **AI Governance & Auditability** | Grounded evidence tracking, bounded confidence `[0.0, 1.0]`, explicit uncertainty flags, human override audit trail | `ai_governance_logs` table & `/security/governance/override` API |
| **Rate Limiting** | In-memory sliding-window `RateLimiter` with tier limits: `AUTH` (10/min), `AI` (30/min), `INGEST` (120/min) | API endpoints returning `429 Too Many Requests` |
| **Secure File Upload** | `SecureUploadValidator`: path traversal neutralization, dangerous extension blocklist, magic byte verification | `POST /api/v1/security/upload` |
| **Database Security** | Parameterized SQL queries (`?`) throughout all services; schema foreign key constraints; transaction rollbacks | All SQLite / SQL interaction layers |
| **Error Message Hardening** | `_sanitize_error_detail`: Strips database table/column names, query fragments, and file system paths | Global exception handlers (`errors.py`) |
| **HTTP Security Headers** | `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `X-XSS-Protection: 1; mode=block`, `Referrer-Policy` | Global FastAPI middleware (`main.py`) |

---

### 3. AI Governance & Human-in-the-Loop Safeguards

1. **Deterministic Grounding First**:
   - The platform never invents metrics, statistics, or incident records.
   - All numerical claims in briefs and dashboards originate from verified database records.
2. **Explicit Uncertainty**:
   - When evidence is sparse or ambiguous, the AI governance layer explicitly sets `uncertainty = True` with an explanatory reason.
3. **No Unnecessary External Data Egress**:
   - The default provider is `LOCAL_DETERMINISTIC`, keeping all operational data within the local infrastructure.
   - When external LLMs are configured, all PII (names, emails, phone numbers, card numbers, government IDs) is scrubbed **prior** to outbound transmission.
   - Prompt texts are audited via SHA-256 hashes (`prompt_hash`) to avoid persisting confidential text in audit logs.
4. **Auditable Human Override**:
   - Any automated AI classification or recommendation can be overridden by an authorized human operator (`GOVERNANCE_MANAGE`).
   - Overrides require a written justification (min 5 characters) and are permanently logged in both `ai_governance_logs` and `security_audit_events`.

---

### 4. Security Assumptions

1. **Secure Hosting Perimeter**:
   - The backend is assumed to run behind a trusted reverse proxy (e.g., NGINX, Cloudflare, AWS ALB) that terminates TLS/HTTPS and forwards client IP addresses via `X-Forwarded-For`.
2. **Secret Key Confidentiality**:
   - `SECRET_KEY` is loaded from secure environment variables or a key vault. It is never checked into version control or hardcoded in client bundles.
3. **Internal Network Trust**:
   - Communication between the application server and the database engine (SQLite or managed PostgreSQL) occurs within a private VPC or isolated container network.
4. **Clock Synchronization**:
   - System servers maintain synchronized clocks via NTP to ensure accurate token expiration, sliding-window rate limiting, and retention purge cutoff calculations.

---

### 5. Known Security Limitations & Future Roadmap

1. **Distributed Rate Limiting**:
   - The current `RateLimiter` utilizes an in-memory sliding-window store suitable for single-node instances. In multi-replica clustered environments, an external Redis or Valkey cluster is recommended for distributed quota tracking.
2. **DLP Heuristics vs. Deep ML PII Models**:
   - The PII minimizer employs comprehensive regex patterns for credit cards, phone numbers, emails, and government IDs. For complex unstructured human names (e.g. contextual named entity recognition across 20+ dialects), integrating an on-premise NER model (e.g. spaCy or HuggingFace NER) will provide enhanced precision.
3. **Client-Side Encryption for At-Rest Customer Feedback**:
   - Customer feedback text is stored in SQLite tables with column-level anonymization upon retention expiry. Full field-level encryption with AES-GCM-256 can be layered for high-compliance healthcare or financial deployments.
4. **External LLM Network Egress Controls**:
   - When external AI providers are used, egress network policies should be enforced at the container firewall level (e.g., iptables or AWS Security Groups) restricting outbound TCP port 443 only to approved enterprise LLM endpoints.

---

### 6. Compliance & Data Retention Lifecycle

Data retention policies allow organizations to automatically comply with privacy standards (GDPR Art. 5(1)(e), CCPA, Indian Digital Personal Data Protection Act):
- **Feedback Items**: Default 365 days &rarr; action: `ANONYMIZE` (masks raw text to `[ANONYMIZED_EXPIRED_DATA]` and removes submitter contact).
- **Investigation Questions**: Default 180 days &rarr; action: `PURGE`.
- **Alerts**: Default 90 days &rarr; action: `PURGE`.
- **Security & Audit Logs**: Default 730 days (2 years) &rarr; action: `PURGE`.
