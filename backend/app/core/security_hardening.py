import re
import os
import time
import unicodedata
from typing import Dict, Any, List, Tuple

class PromptInjectionGuard:
    """
    Detects and mitigates prompt injection, jailbreak attempts,
    delimiter attacks, and system prompt exfiltration attempts.
    """

    INJECTION_PATTERNS = [
        # Instruction overrides & jailbreaks
        r"(?i)\bignore\s+(all\s+)?(previous|prior|above|system)\s+instructions\b",
        r"(?i)\bdisregard\s+(all\s+)?(previous|prior|above|system)\s+instructions\b",
        r"(?i)\bforget\s+(all\s+)?(previous|prior|above|system)\s+instructions\b",
        r"(?i)\boverride\s+(the\s+)?(previous|prior|above|system)\s+instructions\b",
        r"(?i)\byou\s+are\s+now\s+(dan|an\s+unrestricted|in\s+developer\s+mode|jailbroken|godmode)\b",
        r"(?i)\bbypass\s+(all\s+)?(safety|content|security|policy)\s+(filters|rules|safeguards)\b",
        r"(?i)\bdo\s+anything\s+now\b",
        
        # System prompt exfiltration
        r"(?i)\breveal\s+(the|your)\s+(system\s+prompt|secret\s+key|internal\s+instructions|core\s+prompt)\b",
        r"(?i)\bprint\s+(the|your)\s+(system\s+prompt|initial\s+instructions)\b",
        r"(?i)\boutput\s+(the|your)\s+(exact\s+system\s+prompt|developer\s+instructions)\b",
        r"(?i)\bwhat\s+(is|are)\s+your\s+(initial|original|system)\s+instructions\b",

        # Delimiter & Role hijack attacks
        r"(?i)---+\s*END\s+(SYSTEM\s+)?PROMPT\s*---+",
        r"(?i)```+\s*(system|admin|override|instructions)",
        r"(?i)<\s*/?\s*(system|instructions|admin)\s*>",
        r"(?i)\[SYSTEM_PROMPT\]",
        r"(?i)system:\s*you\s+must",
    ]

    COMPILED_PATTERNS = [re.compile(p) for p in INJECTION_PATTERNS]

    @classmethod
    def inspect_prompt(cls, text: str) -> Dict[str, Any]:
        """
        Inspect prompt text for malicious injection patterns.
        Returns detection metadata and risk score.
        """
        if not text:
            return {
                "is_injection": False,
                "risk_score": 0.0,
                "flagged_patterns": [],
                "sanitized_text": text
            }

        flagged = []
        for pattern in cls.COMPILED_PATTERNS:
            match = pattern.search(text)
            if match:
                flagged.append(match.group(0))

        risk_score = min(1.0, len(flagged) * 0.4)
        is_injection = len(flagged) > 0

        # Neutralize matched injections by neutralizing delimiter/override phrases
        sanitized = text
        for pattern in cls.COMPILED_PATTERNS:
            sanitized = pattern.sub("[BLOCKED_INJECTION_PATTERN]", sanitized)

        return {
            "is_injection": is_injection,
            "risk_score": round(risk_score, 2),
            "flagged_patterns": flagged,
            "sanitized_text": sanitized
        }


class InputSanitizer:
    """
    Sanitizes user and API inputs:
    - Strips null bytes and control chars
    - Strips dangerous HTML and JavaScript injection payloads (<script>, onerror=, etc.)
    - Unicode NFKC normalization
    - Enforces length bounds
    """

    DANGEROUS_HTML_PATTERNS = [
        re.compile(r"<\s*script[^>]*>.*?<\s*/\s*script\s*>", re.IGNORECASE | re.DOTALL),
        re.compile(r"<\s*iframe[^>]*>.*?<\s*/\s*iframe\s*>", re.IGNORECASE | re.DOTALL),
        re.compile(r"javascript\s*:", re.IGNORECASE),
        re.compile(r"on\w+\s*=\s*[\"'].*?[\"']", re.IGNORECASE),
        re.compile(r"<\s*object[^>]*>.*?<\s*/\s*object\s*>", re.IGNORECASE | re.DOTALL),
        re.compile(r"<\s*embed[^>]*>", re.IGNORECASE),
    ]

    @classmethod
    def sanitize_string(cls, text: str, max_length: int = 10000, strip_html: bool = True) -> str:
        if not text:
            return ""

        # Strip null bytes
        cleaned = text.replace("\x00", "")

        # Unicode normalization
        cleaned = unicodedata.normalize("NFKC", cleaned)

        # Strip dangerous HTML/scripts
        if strip_html:
            for pat in cls.DANGEROUS_HTML_PATTERNS:
                cleaned = pat.sub("", cleaned)
            # Strip simple raw HTML tags if they contain unescaped angle brackets with tags
            cleaned = re.sub(r"<\/?(script|img|iframe|style|svg|body|html|meta|link)[^>]*>", "", cleaned, flags=re.IGNORECASE)

        # Enforce max length bound
        if len(cleaned) > max_length:
            cleaned = cleaned[:max_length]

        return cleaned.strip()


class RateLimiter:
    """
    In-memory sliding-window rate limiter.
    Provides tier-based throttling:
    - AUTH: 10 requests / 60 seconds (prevents credential stuffing)
    - AI: 30 requests / 60 seconds (prevents LLM DoS / quota exhaustion)
    - INGEST: 120 requests / 60 seconds (feedback ingestion)
    - DEFAULT: 300 requests / 60 seconds
    """

    LIMITS = {
        "AUTH": (10, 60),      # (max_requests, window_seconds)
        "AI": (30, 60),
        "INGEST": (120, 60),
        "DEFAULT": (300, 60),
    }

    _storage: Dict[str, List[float]] = {}

    @classmethod
    def check_rate_limit(cls, key: str, tier: str = "DEFAULT") -> Tuple[bool, int, int]:
        """
        Check if request under key is allowed.
        Returns: (allowed: bool, remaining_requests: int, retry_after_seconds: int)
        """
        max_requests, window_sec = cls.LIMITS.get(tier, cls.LIMITS["DEFAULT"])
        now = time.time()
        bucket_key = f"{tier}:{key}"

        timestamps = cls._storage.get(bucket_key, [])
        # Expire old entries outside window
        cutoff = now - window_sec
        valid_timestamps = [t for t in timestamps if t > cutoff]

        if len(valid_timestamps) >= max_requests:
            # Rate limit exceeded
            oldest = valid_timestamps[0]
            retry_after = max(1, int(oldest + window_sec - now))
            cls._storage[bucket_key] = valid_timestamps
            return False, 0, retry_after

        # Record new request
        valid_timestamps.append(now)
        cls._storage[bucket_key] = valid_timestamps
        remaining = max_requests - len(valid_timestamps)
        return True, remaining, 0

    @classmethod
    def reset(cls) -> None:
        """Clear all rate limit records (useful for testing)."""
        cls._storage.clear()


class SecureUploadValidator:
    """
    Validates file uploads to prevent:
    - Directory traversal attacks (../, absolute paths)
    - Executable file uploads (.exe, .sh, .py, .php, etc.)
    - File size limits (max 5 MB)
    - Magic byte MIME spoofing for images and documents
    """

    MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 MB

    ALLOWED_EXTENSIONS = {
        ".png", ".jpg", ".jpeg", ".webp",
        ".csv", ".json", ".txt", ".pdf"
    }

    DANGEROUS_EXTENSIONS = {
        ".exe", ".bat", ".cmd", ".sh", ".py", ".php",
        ".js", ".vbs", ".ps1", ".dll", ".so", ".html",
        ".htm", ".svg", ".bin", ".scr", ".jar", ".war"
    }

    MAGIC_SIGNATURES = {
        ".png": b"\x89PNG\r\n\x1a\n",
        ".jpg": b"\xff\xd8\xff",
        ".jpeg": b"\xff\xd8\xff",
        ".pdf": b"%PDF-",
    }

    @classmethod
    def sanitize_filename(cls, filename: str) -> str:
        """
        Strips path traversal components and returns safe basename.
        """
        if not filename:
            return "unnamed_upload.bin"

        # Strip null bytes and control chars
        clean = filename.replace("\x00", "").strip()

        # Remove Windows / Unix path elements
        clean = os.path.basename(clean.replace("\\", "/"))

        # Strip remaining traversal attempts
        clean = clean.replace("..", "").replace("/", "").replace("\\", "")

        # Safe regex: allow alphanumeric, underscore, dash, dot
        clean = re.sub(r"[^a-zA-Z0-9_\-\.]", "_", clean)

        return clean or "unnamed_upload.bin"

    @classmethod
    def validate_file(cls, filename: str, content: bytes) -> Dict[str, Any]:
        """
        Validates uploaded file against security rules.
        Returns { "is_valid": bool, "safe_filename": str, "error": Optional[str], "size": int }
        """
        if not content:
            return {
                "is_valid": False,
                "safe_filename": "",
                "error": "Uploaded file is empty.",
                "size": 0
            }

        # Size check
        if len(content) > cls.MAX_FILE_SIZE:
            return {
                "is_valid": False,
                "safe_filename": "",
                "error": f"File size exceeds maximum allowed limit of {cls.MAX_FILE_SIZE // (1024 * 1024)}MB.",
                "size": len(content)
            }

        safe_name = cls.sanitize_filename(filename)
        _, ext = os.path.splitext(safe_name.lower())

        if ext in cls.DANGEROUS_EXTENSIONS:
            return {
                "is_valid": False,
                "safe_filename": safe_name,
                "error": f"Dangerous or executable file extension '{ext}' is prohibited.",
                "size": len(content)
            }

        if ext not in cls.ALLOWED_EXTENSIONS:
            return {
                "is_valid": False,
                "safe_filename": safe_name,
                "error": f"File extension '{ext}' is not permitted. Allowed: {sorted(list(cls.ALLOWED_EXTENSIONS))}",
                "size": len(content)
            }

        # Magic byte signature check for binary types
        if ext in cls.MAGIC_SIGNATURES:
            expected_sig = cls.MAGIC_SIGNATURES[ext]
            if not content.startswith(expected_sig):
                return {
                    "is_valid": False,
                    "safe_filename": safe_name,
                    "error": f"MIME content header does not match declared extension '{ext}'. Magic byte verification failed.",
                    "size": len(content)
                }

        # For text, csv, json: verify valid UTF-8/ASCII and absence of embedded binary executables
        if ext in {".csv", ".json", ".txt"}:
            try:
                decoded = content[:4096].decode("utf-8")
                # Look for suspicious binary/executable headers or shell scripts
                if decoded.startswith("#!/") or "<?php" in decoded or "<script" in decoded.lower():
                    return {
                        "is_valid": False,
                        "safe_filename": safe_name,
                        "error": "File contains embedded executable scripts or script tags.",
                        "size": len(content)
                    }
            except UnicodeDecodeError:
                return {
                    "is_valid": False,
                    "safe_filename": safe_name,
                    "error": "Text file contains non-UTF8 binary data.",
                    "size": len(content)
                }

        return {
            "is_valid": True,
            "safe_filename": safe_name,
            "error": None,
            "size": len(content)
        }


class PIIMinimizer:
    """
    Minimizes and redacts Personally Identifiable Information (PII)
    prior to sending prompts or contexts to external AI models or lower-privileged roles.
    Protects:
    - Emails
    - Phone numbers (Indian and international)
    - Credit and debit card numbers (13-19 digits)
    - Aadhaar / National ID / SSN numbers
    """

    EMAIL_PATTERN = re.compile(
        r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"
    )

    # Matches 10 to 14 digit phone numbers with optional +91, dashes, spaces, parens
    PHONE_PATTERN = re.compile(
        r"(?:(?:\+?91[\-\s]?)?[6-9]\d{9}\b)|(?:\b\+?[1-9]\d{0,2}[\-\s]?\(?\d{2,4}\)?[\-\s]?\d{3,4}[\-\s]?\d{3,4}\b)"
    )

    # 13 to 19 digit card numbers with optional hyphens/spaces
    CARD_PATTERN = re.compile(
        r"\b(?:\d{4}[\-\s]?){3}\d{1,4}\b|\b\d{13,19}\b"
    )

    # Aadhaar (12 digits in 4-4-4 format) or US SSN (3-2-4 format)
    AADHAAR_PATTERN = re.compile(r"\b\d{4}\s\d{4}\s\d{4}\b")
    SSN_PATTERN = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")

    @classmethod
    def redact_pii(cls, text: str) -> Tuple[str, int, List[str]]:
        """
        Redacts all identifiable PII from string.
        Returns (redacted_text, count_redacted, categories_found).
        """
        if not text:
            return "", 0, []

        categories = set()
        count = 0
        result = text

        # 1. Cards
        card_matches = cls.CARD_PATTERN.findall(result)
        if card_matches:
            # Filter matches that have at least 13 digits
            for m in card_matches:
                digits_only = re.sub(r"\D", "", m)
                if 13 <= len(digits_only) <= 19:
                    result = result.replace(m, "[CARD_REDACTED]")
                    count += 1
                    categories.add("CARD")

        # 2. Aadhaar / SSN
        aadhaar_matches = cls.AADHAAR_PATTERN.findall(result)
        if aadhaar_matches:
            for m in aadhaar_matches:
                result = result.replace(m, "[GOV_ID_REDACTED]")
                count += 1
                categories.add("GOV_ID")

        ssn_matches = cls.SSN_PATTERN.findall(result)
        if ssn_matches:
            for m in ssn_matches:
                result = result.replace(m, "[SSN_REDACTED]")
                count += 1
                categories.add("SSN")

        # 3. Emails
        email_matches = cls.EMAIL_PATTERN.findall(result)
        if email_matches:
            for m in email_matches:
                result = result.replace(m, "[EMAIL_REDACTED]")
                count += 1
                categories.add("EMAIL")

        # 4. Phones
        phone_matches = cls.PHONE_PATTERN.findall(result)
        if phone_matches:
            for m in phone_matches:
                if not any(token in m for token in ["[CARD_REDACTED]", "[GOV_ID_REDACTED]", "[SSN_REDACTED]"]):
                    result = result.replace(m, "[PHONE_REDACTED]")
                    count += 1
                    categories.add("PHONE")

        return result, count, sorted(list(categories))

    @classmethod
    def minimize_record_for_role(cls, record: Dict[str, Any], role_name: str) -> Dict[str, Any]:
        """
        Redacts customer contact info if the viewing role is operational (e.g. MAINTENANCE_TEAM or VIEWER).
        ORGANIZATION_ADMIN and OPERATIONS_MANAGER retain full view.
        """
        if role_name in ("ORGANIZATION_ADMIN", "OPERATIONS_MANAGER"):
            return record

        sanitized = dict(record)
        # Redact raw feedback or customer identity
        if "raw_text" in sanitized and isinstance(sanitized["raw_text"], str):
            sanitized["raw_text"], _, _ = cls.redact_pii(sanitized["raw_text"])

        if "submitter_contact" in sanitized and sanitized["submitter_contact"]:
            sanitized["submitter_contact"] = "[REDACTED_BY_ROLE_POLICY]"

        if "user_email" in sanitized and sanitized["user_email"]:
            sanitized["user_email"] = "[REDACTED_BY_ROLE_POLICY]"

        return sanitized


class LogScrubber:
    """
    Scrubs tokens, secrets, passwords, and sensitive keys from log messages.
    """

    BEARER_PATTERN = re.compile(r"Bearer\s+[A-Za-z0-9\-_\.]+", re.IGNORECASE)
    PASSWORD_PATTERN = re.compile(r'("password"|"secret"|"apiKey"|"api_key"|"token")\s*:\s*"[^"]+"', re.IGNORECASE)
    SECRET_KEY_PATTERN = re.compile(r"(sk-[a-zA-Z0-9_\-]{8,})", re.IGNORECASE)

    @classmethod
    def scrub(cls, message: str) -> str:
        if not message:
            return ""

        scrubbed = cls.BEARER_PATTERN.sub("Bearer [REDACTED_JWT]", message)
        scrubbed = cls.PASSWORD_PATTERN.sub(r'\1: "[REDACTED]"', scrubbed)
        scrubbed = cls.SECRET_KEY_PATTERN.sub("sk-[REDACTED_KEY]", scrubbed)

        # Also scrub any credit card patterns in log messages
        card_matches = PIIMinimizer.CARD_PATTERN.findall(scrubbed)
        for m in card_matches:
            digits = re.sub(r"\D", "", m)
            if 13 <= len(digits) <= 19:
                scrubbed = scrubbed.replace(m, "[CARD_REDACTED]")

        return scrubbed
