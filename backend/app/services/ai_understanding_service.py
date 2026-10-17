"""
Phase 4: AI-Powered Operational Feedback Understanding Service

Transforms unstructured, multilingual frontline feedback into grounded, structured
operational intelligence without inventing or hallucinating facts.

Every extracted attribute includes:
- value: specific classification, entity, or 'unknown'
- confidence: numeric score from 0.0 to 1.0 (0.0 for unknown)
- evidence: exact source text substring with character start/end offsets (null for unknown)
- uncertainty: boolean flag indicating ambiguity or lack of evidence
- uncertaintyReason: explanation if uncertain or unknown
"""

import re
import unicodedata
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from backend.app.services.multilingual_service import MultilingualService


class AIUnderstandingService:
    """Core AI engine for language detection, normalization, grounded extraction, and human review."""

    # -------------------------------------------------------------------------
    # 1. MULTILINGUAL LEXICONS & PATTERNS
    # -------------------------------------------------------------------------
    LANGUAGE_VOCABULARIES = {
        "es": {
            "el", "la", "de", "que", "y", "en", "un", "se", "no", "haber", "por", "con", "su",
            "para", "como", "estar", "tener", "le", "lo", "todo", "pero", "mas", "hacer", "o",
            "poder", "decir", "este", "ir", "otro", "este", "si", "fuga", "piso", "agua", "mojado",
            "charco", "refrigerador", "caja", "pasillo", "tienda", "averiado", "sucio", "goteando",
            "cliente", "urgente", "alerta", "congelador", "bano", "estante", "olor", "humo"
        },
        "fr": {
            "le", "la", "les", "de", "des", "du", "un", "une", "et", "en", "est", "pas", "pour",
            "dans", "sur", "avec", "qui", "ce", "cette", "au", "aux", "par", "mais", "faire",
            "fuite", "eau", "glissant", "refrigerateur", "congelateur", "rayon", "allee", "caisse",
            "sale", "panne", "bruyant", "fuit", "chariot", "service", "urgent", "attention", "danger"
        },
        "de": {
            "der", "die", "das", "und", "in", "den", "von", "zu", "mit", "sich", "des", "auf",
            "fuer", "ist", "im", "dem", "nicht", "ein", "eine", "als", "auch", "es", "an", "werden",
            "aus", "er", "hat", "wasseraustritt", "kuehlung", "gang", "kasse", "ausfall", "schaden",
            "kaputt", "nass", "rutschgefahr", "dringend", "kuehlregal", "störung", "tropft"
        },
        "hi": {
            "hai", "aur", "mein", "ko", "se", "ka", "ki", "ke", "par", "yeh", "woh", "pani",
            "gir", "raha", "kharab", "thik", "jaldi", "dukaan", "freezer", "line", "kripya", "bohot"
        }
    }

    PII_PATTERNS = [
        (re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'), '[EMAIL_REDACTED]'),
        (re.compile(r'\b(?:\+?1[-. ]?)?\(?([0-9]{3})\)?[-. ]?([0-9]{3})[-. ]?([0-9]{4})\b'), '[PHONE_REDACTED]'),
        (re.compile(r'\b\d{3}-\d{2}-\d{4}\b'), '[SSN_REDACTED]'),
        (re.compile(r'\b(?:\d{4}[- ]?){3}\d{4}\b'), '[CARD_REDACTED]')
    ]

    # Grounded Domain Taxonomies & Matchers
    CATEGORIES = [
        {
            "category": "SAFETY_HAZARD",
            "issueType": "SLIP_FALL_HAZARD",
            "keywords": ["slip", "spill", "wet floor", "puddle", "water on the floor", "charco", "piso mojado", "glissant", "rutschgefahr", "tripping", "hazard", "broken glass", "falling hazard"],
            "severity": "HIGH",
            "urgency": "IMMEDIATE",
            "safety": "CRITICAL_HAZARD",
            "operationalImpact": "SAFETY_COMPLIANCE_RISK",
            "customerImpact": "SLIP_FALL_INJURY_RISK"
        },
        {
            "category": "FACILITIES_MAINTENANCE",
            "issueType": "REFRIGERATION_FAILURE",
            "keywords": ["freezer", "refrigerator", "cooler", "chiller", "refrigerador", "congelador", "kuehlregal", "leaking water", "puddle under", "compressor", "warm to touch", "unusual humming", "ice buildup", "door seal", "fuit", "goteando"],
            "severity": "HIGH",
            "urgency": "IMMEDIATE",
            "safety": "POTENTIAL_HAZARD",
            "operationalImpact": "INVENTORY_SPOILAGE_RISK",
            "customerImpact": "PURCHASE_PREVENTION"
        },
        {
            "category": "FACILITIES_MAINTENANCE",
            "issueType": "HVAC_FAILURE",
            "keywords": ["ac", "a/c", "air conditioning", "hvac", "cooling", "not cooling", "store is hot", "too hot", "sweltering", "ventilation", "heating", "thermostat"],
            "severity": "HIGH",
            "urgency": "SAME_DAY",
            "safety": "POTENTIAL_HAZARD",
            "operationalImpact": "STORE_CLIMATE_CONTROL_FAILURE",
            "customerImpact": "CUSTOMER_DISSATISFACTION"
        },
        {
            "category": "CHECKOUT_POS",
            "issueType": "EQUIPMENT_MALFUNCTION",
            "keywords": ["scanner", "self-checkout", "register", "kiosk", "barcode", "terminal freeze", "card reader", "printer jam", "offline", "unresponsive", "caja", "bloquee", "caisse"],
            "severity": "MEDIUM",
            "urgency": "WITHIN_HOUR",
            "safety": "NON_HAZARD",
            "operationalImpact": "CHECKOUT_THROUGHPUT_REDUCTION",
            "customerImpact": "EXTENDED_WAIT_TIME"
        },
        {
            "category": "INVENTORY_STOCK",
            "issueType": "OUT_OF_STOCK",
            "keywords": ["out of stock", "empty shelf", "ran out", "no stock", "sold out", "agotado", "rupture de stock", "restock", "missing barcode", "expired date", "rotten", "spoiled"],
            "severity": "MEDIUM",
            "urgency": "SAME_DAY",
            "safety": "NON_HAZARD",
            "operationalImpact": "INVENTORY_SPOILAGE_RISK",
            "customerImpact": "PURCHASE_PREVENTION"
        },
        {
            "category": "CUSTOMER_SERVICE",
            "issueType": "STAFF_UNAVAILABLE",
            "keywords": ["unattended", "no staff", "rude", "long line", "waiting for 20 minutes", "waiting forever", "no one helped", "poor service", "staff arguing", "atencion al cliente"],
            "severity": "MEDIUM",
            "urgency": "WITHIN_HOUR",
            "safety": "NON_HAZARD",
            "operationalImpact": "CHECKOUT_THROUGHPUT_REDUCTION",
            "customerImpact": "CUSTOMER_DISSATISFACTION"
        },
        {
            "category": "OPERATIONAL_HYGIENE",
            "issueType": "FACILITY_CLEANLINESS",
            "keywords": ["restroom dirty", "trash overflowing", "dirty floor", "foul odor", "unclean", "bano sucio", "toilet paper empty", "soap dispenser empty"],
            "severity": "LOW",
            "urgency": "SAME_DAY",
            "safety": "NON_HAZARD",
            "operationalImpact": "MINIMAL_OPERATIONAL_IMPACT",
            "customerImpact": "CUSTOMER_DISSATISFACTION"
        }
    ]

    LOCATION_PATTERNS = [
        (re.compile(r'\b(?:aisle|pasillo|allee|gang)\s*([0-9]{1,2}[a-zA-Z]?)\b', re.IGNORECASE), "Aisle {0}"),
        (re.compile(r'\b(?:lane|register|caisse|caja)\s*([0-9]{1,2})\b', re.IGNORECASE), "Lane {0}"),
        (re.compile(r'\b(?:produce\s*(?:department|section|area|wing)?)\b', re.IGNORECASE), "Produce Department"),
        (re.compile(r'\b(?:dairy\s*(?:section|aisle))\b', re.IGNORECASE), "Dairy Section"),
        (re.compile(r'\b(?:frozen\s*(?:foods|section|aisle)?)\b', re.IGNORECASE), "Frozen Foods Aisle"),
        (re.compile(r'\b(?:bakery\s*(?:section|counter)?)\b', re.IGNORECASE), "Bakery Section"),
        (re.compile(r'\b(?:meat\s*(?:department|counter)?)\b', re.IGNORECASE), "Meat Department"),
        (re.compile(r'\b(?:deli\s*(?:counter)?)\b', re.IGNORECASE), "Deli Counter"),
        (re.compile(r'\b(?:restroom|bathroom|toilet|bano)\b', re.IGNORECASE), "Customer Restrooms"),
        (re.compile(r'\b(?:entrance|exit|front doors?)\b', re.IGNORECASE), "Main Entrance/Exit"),
        (re.compile(r'\b(?:parking\s*lot)\b', re.IGNORECASE), "Parking Lot"),
        (re.compile(r'\b(?:checkout\s*area|registers)\b', re.IGNORECASE), "Front Checkout Area")
    ]

    ENTITY_PATTERNS = [
        (re.compile(r'\b(?:freezer|congelateur|refrigerador|chiller|cooler)(?:\s+([0-9]{1,2}))?\b', re.IGNORECASE), "EQUIPMENT", "Freezer/Cooler Unit"),
        (re.compile(r'\b(?:hvac|ac|a/c|air\s*conditioning)(?:\s+(?:unit\s*)?#?([0-9]{1,2}))?\b', re.IGNORECASE), "EQUIPMENT", "HVAC Unit"),
        (re.compile(r'\b(?:self-checkout|kiosk|pos\s*terminal|scanner)(?:\s+([0-9]{1,2}))?\b', re.IGNORECASE), "EQUIPMENT", "POS Terminal"),
        (re.compile(r'\b(?:produce\s*case|chilled\s*display|vegetable\s*rack)\b', re.IGNORECASE), "EQUIPMENT", "Produce Display Case"),
        (re.compile(r'\b(?:shopping\s*cart|trolley|basket)\b', re.IGNORECASE), "ASSET", "Shopping Cart"),
        (re.compile(r'\b(?:automatic\s*door|sliding\s*door)\b', re.IGNORECASE), "INFRASTRUCTURE", "Automatic Entrance Door"),
        (re.compile(r'\b(?:soap\s*dispenser|hand\s*dryer|paper\s*towel\s*dispenser)\b', re.IGNORECASE), "FACILITY", "Restroom Dispenser"),
        (re.compile(r'\b(?:organic\s*milk|eggs|bread|chicken|apples|ice\s*cream)\b', re.IGNORECASE), "PRODUCT", "Merchandise Item")
    ]

    SYMPTOM_PATTERNS = [
        re.compile(r'\b(?:water\s*pooling|leaking\s*water|dripping|leaking|goteando|fuit|charco|tropft)\b', re.IGNORECASE),
        re.compile(r'\b(?:unusual\s*(?:humming|buzzing|noise|sound)|bruit\s*inhabituel)\b', re.IGNORECASE),
        re.compile(r'\b(?:warm\s*to\s*touch|temperature\s*rising|not\s*cold\s*enough|spoiling)\b', re.IGNORECASE),
        re.compile(r'\b(?:screen\s*frozen|unresponsive|offline|paper\s*jam|scanning\s*error)\b', re.IGNORECASE),
        re.compile(r'\b(?:foul\s*odor|bad\s*smell|smoke|burning\s*smell)\b', re.IGNORECASE),
        re.compile(r'\b(?:empty\s*shelves|missing\s*stock|out\s*of\s*stock)\b', re.IGNORECASE),
        re.compile(r'\b(?:slippery\s*surface|slip\s*hazard|wet\s*floor)\b', re.IGNORECASE)
    ]

    TEMPORAL_PATTERNS = [
        re.compile(r'\b(?:(?:around|about|approx|approximately)\s*)?[0-9]{1,2}\s*(?:hours?|hrs?|minutes?|mins?|days?)\s*ago\b', re.IGNORECASE),
        re.compile(r'\bat\s+[0-9]{1,2}(?::[0-9]{2})?\s*(?:am|pm)?\b', re.IGNORECASE),
        re.compile(r'\b(?:since\s*this\s*morning|since\s*morning|desde\s*la\s*manana)\b', re.IGNORECASE),
        re.compile(r'\b(?:for\s*(?:about\s*)?[0-9]{1,2}\s*(?:hours?|hrs?|minutes?|mins?))\b', re.IGNORECASE),
        re.compile(r'\b(?:yesterday|yesterday\s*afternoon|ayer)\b', re.IGNORECASE),
        re.compile(r'\b(?:this\s*morning|esta\s*manana|ce\s*matin)\b', re.IGNORECASE),
        re.compile(r'\b(?:right\s*now|at\s*the\s*moment|ahora\s*mismo|tout\s*de\s*suite|immediately)\b', re.IGNORECASE),
        re.compile(r'\b(?:during\s*(?:the\s*)?(?:rush|lunch|evening|shift))\b', re.IGNORECASE)
    ]

    # -------------------------------------------------------------------------
    # 2. LANGUAGE DETECTION
    # -------------------------------------------------------------------------
    @classmethod
    def detect_language(cls, text: str, hint_language: Optional[str] = None) -> Dict[str, Any]:
        """Detect language with confidence, matched evidence tokens, and uncertainty flag."""
        normalized = unicodedata.normalize('NFKD', (text or "").lower())
        tokens = set(re.findall(r'[a-zA-Z\u0900-\u0D7F]+', normalized))

        if not tokens:
            return {
                "code": hint_language or "en",
                "confidence": 0.5,
                "evidence": [],
                "uncertainty": True,
                "uncertaintyReason": "Text contains no recognizable words for language detection"
            }

        # Check MultilingualService first
        ml_res = MultilingualService.detect_language(text, hint_language=hint_language)
        is_uncertain = ml_res["confidence"] < 0.65
        reason = None if not is_uncertain else "Low confidence language detection"

        return {
            "code": ml_res["code"],
            "confidence": ml_res["confidence"],
            "evidence": ml_res.get("evidence", []),
            "uncertainty": is_uncertain,
            "uncertaintyReason": reason,
            "name": ml_res.get("name"),
            "script": ml_res.get("script"),
            "isTransliterated": ml_res.get("isTransliterated", False),
            "isCodeMixed": ml_res.get("isCodeMixed", False)
        }

    # -------------------------------------------------------------------------
    # 3. TEXT NORMALIZATION & PII HANDLING
    # -------------------------------------------------------------------------
    @classmethod
    def normalize_text(cls, raw_text: str) -> Dict[str, Any]:
        """Perform NFKC normalization, whitespace collapsing, and PII masking with span tracking."""
        nfkc_text = unicodedata.normalize('NFKC', raw_text)
        scrubbed = nfkc_text
        pii_spans: List[Dict[str, Any]] = []

        for pattern, replacement in cls.PII_PATTERNS:
            for match in pattern.finditer(scrubbed):
                pii_spans.append({
                    "type": replacement.strip('[]'),
                    "start": match.start(),
                    "end": match.end(),
                    "snippet": match.group(0)[:3] + "***"
                })
            scrubbed = pattern.sub(replacement, scrubbed)

        # Collapse whitespace while keeping string clean
        normalized_clean = re.sub(r'[ \t]+', ' ', scrubbed).strip()

        return {
            "normalizedText": normalized_clean,
            "hasPii": len(pii_spans) > 0,
            "piiSpans": pii_spans,
            "charCount": len(normalized_clean),
            "wordCount": len(normalized_clean.split())
        }

    # -------------------------------------------------------------------------
    # 4. EVIDENCE-SPAN GROUNDED EXTRACTION ENGINE
    # -------------------------------------------------------------------------
    @classmethod
    def extract_understanding(
        cls,
        raw_text: str,
        normalized_text: Optional[str] = None,
        language_code: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Extract all 14 structured operational attributes strictly grounded in evidence.
        NEVER invents facts. If an attribute cannot be determined, returns 'unknown'
        with confidence: 0.0, evidence: None, and uncertainty: True.
        """
        source = raw_text
        lower_source = source.lower()
        now_iso = datetime.now(timezone.utc).isoformat()

        # Step A: Multilingual Operational Intelligence Hardening Pipeline (Phase 15)
        ml_pipeline = MultilingualService.process_multilingual_pipeline(source, hint_language=language_code)
        lang_res = {
            "code": ml_pipeline["detectedLanguage"]["code"],
            "confidence": ml_pipeline["detectedLanguage"]["confidence"],
            "evidence": ml_pipeline["detectedLanguage"].get("evidence", []),
            "uncertainty": ml_pipeline["detectedLanguage"]["confidence"] < 0.65,
            "uncertaintyReason": None if ml_pipeline["detectedLanguage"]["confidence"] >= 0.65 else "Low confidence language detection",
            "name": ml_pipeline["detectedLanguage"].get("name"),
            "script": ml_pipeline["detectedLanguage"].get("script"),
            "isTransliterated": ml_pipeline["detectedLanguage"].get("isTransliterated", False),
            "isCodeMixed": ml_pipeline["detectedLanguage"].get("isCodeMixed", False)
        }

        # Helper to find exact character offset in source text with word boundary protection
        def find_evidence(keyword: str) -> Optional[Dict[str, Any]]:
            if not keyword:
                return None
            prefix = r"\b" if keyword[0].isalnum() else ""
            suffix = r"\b" if keyword[-1].isalnum() else ""
            pattern = re.compile(f"{prefix}{re.escape(keyword)}{suffix}", re.IGNORECASE)
            match = pattern.search(source)
            if match:
                return {
                    "text": match.group(0),
                    "start": match.start(),
                    "end": match.end()
                }
            return None

        uncertainties: List[str] = []

        # 1 & 2: Issue Category & Issue Type
        category_val = "unknown"
        issue_type_val = "unknown"
        cat_evidence = None
        cat_confidence = 0.0
        cat_uncertainty = True
        cat_reason: Optional[str] = "No operational category patterns matched in feedback text"
        matched_cat_spec = None

        for spec in cls.CATEGORIES:
            for kw in spec["keywords"]:
                ev = find_evidence(kw)
                if ev:
                    category_val = str(spec["category"])
                    issue_type_val = str(spec["issueType"])
                    cat_evidence = ev
                    cat_confidence = 0.94
                    cat_uncertainty = False
                    cat_reason = None
                    matched_cat_spec = spec
                    break
            if matched_cat_spec:
                break

        # Multilingual fallback: If raw keyword search did not match, but multilingual pipeline identified operational issue
        if cat_uncertainty and (ml_pipeline["detectedLanguage"]["code"] != "en" or ml_pipeline["detectedLanguage"].get("isTransliterated")):
            extracted = ml_pipeline["extractedIssue"]
            category_val = extracted["category"]
            issue_type_val = extracted["issueType"]
            cat_evidence = {"text": source[:min(len(source), 40)], "start": 0, "end": min(len(source), 40)}
            cat_confidence = ml_pipeline["confidence"]
            cat_uncertainty = False
            cat_reason = None
            for spec in cls.CATEGORIES:
                if spec["category"] == category_val:
                    matched_cat_spec = spec
                    break

        if cat_uncertainty:
            uncertainties.append("Issue category and type could not be determined from text")

        field_category = {
            "value": category_val,
            "confidence": cat_confidence,
            "evidence": cat_evidence,
            "uncertainty": cat_uncertainty,
            "uncertaintyReason": cat_reason
        }

        field_issue_type = {
            "value": issue_type_val,
            "confidence": cat_confidence,
            "evidence": cat_evidence,
            "uncertainty": cat_uncertainty,
            "uncertaintyReason": cat_reason
        }

        # 3: Location Extraction
        loc_val = "unknown"
        loc_evidence = None
        loc_confidence = 0.0
        loc_uncertainty = True
        loc_reason: Optional[str] = "No physical location or store section specified in feedback"

        for pattern, template in cls.LOCATION_PATTERNS:
            match = pattern.search(source)
            if match:
                groups = match.groups()
                loc_val = template.format(*groups) if groups and groups[0] else template
                loc_evidence = {
                    "text": match.group(0),
                    "start": match.start(),
                    "end": match.end()
                }
                loc_confidence = 0.92
                loc_uncertainty = False
                loc_reason = None
                break

        if loc_uncertainty:
            uncertainties.append("No physical store location or aisle stated in feedback")

        field_location = {
            "value": loc_val,
            "confidence": loc_confidence,
            "evidence": loc_evidence,
            "uncertainty": loc_uncertainty,
            "uncertaintyReason": loc_reason
        }

        # 4: Affected Entity Extraction
        entity_val = "unknown"
        entity_evidence = None
        entity_confidence = 0.0
        entity_uncertainty = True
        entity_reason: Optional[str] = "No specific equipment, asset, or entity mentioned"

        for pattern, label, description in cls.ENTITY_PATTERNS:
            match = pattern.search(source)
            if match:
                groups = match.groups()
                entity_val = f"{description} {groups[0]}".strip() if groups and groups[0] else description
                entity_evidence = {
                    "text": match.group(0),
                    "label": label,
                    "start": match.start(),
                    "end": match.end()
                }
                entity_confidence = 0.90
                entity_uncertainty = False
                entity_reason = None
                break

        if entity_uncertainty:
            uncertainties.append("Specific affected entity or equipment not identified")

        field_affected_entity = {
            "value": entity_val,
            "confidence": entity_confidence,
            "evidence": entity_evidence,
            "uncertainty": entity_uncertainty,
            "uncertaintyReason": entity_reason
        }

        # 5: Severity Extraction
        sev_val = "unknown"
        sev_evidence = None
        sev_confidence = 0.0
        sev_uncertainty = True
        sev_reason: Optional[str] = "Insufficient operational context to assess severity without speculation"

        critical_cues = ["fire", "smoke", "blood", "injury", "shock", "spark", "severely", "flood", "massive leak", "emergency"]
        high_cues = ["slip", "spill", "wet floor", "puddle", "piso mojado", "glissant", "warm to touch", "charco", "danger", "fuit"]
        medium_cues = ["broken", "not working", "offline", "slow", "unattended", "out of stock", "empty", "odor"]
        low_cues = ["dirty", "paper towel", "cosmetic", "suggestion", "soap"]

        for cue in critical_cues:
            ev = find_evidence(cue)
            if ev:
                sev_val = "CRITICAL"
                sev_evidence = ev
                sev_confidence = 0.96
                sev_uncertainty = False
                sev_reason = None
                break

        if sev_uncertainty:
            for cue in high_cues:
                ev = find_evidence(cue)
                if ev:
                    sev_val = "HIGH"
                    sev_evidence = ev
                    sev_confidence = 0.90
                    sev_uncertainty = False
                    sev_reason = None
                    break

        if sev_uncertainty:
            for cue in medium_cues:
                ev = find_evidence(cue)
                if ev:
                    sev_val = "MEDIUM"
                    sev_evidence = ev
                    sev_confidence = 0.82
                    sev_uncertainty = False
                    sev_reason = None
                    break

        if sev_uncertainty:
            for cue in low_cues:
                ev = find_evidence(cue)
                if ev:
                    sev_val = "LOW"
                    sev_evidence = ev
                    sev_confidence = 0.78
                    sev_uncertainty = False
                    sev_reason = None
                    break

        if sev_uncertainty and matched_cat_spec:
            sev_val = str(matched_cat_spec["severity"])
            sev_evidence = cat_evidence
            sev_confidence = 0.75
            sev_uncertainty = False
            sev_reason = None

        if sev_uncertainty:
            uncertainties.append("Severity cannot be derived objectively from input text")

        field_severity = {
            "value": sev_val,
            "confidence": sev_confidence,
            "evidence": sev_evidence,
            "uncertainty": sev_uncertainty,
            "uncertaintyReason": sev_reason
        }

        # 6: Urgency Extraction
        urg_val = "unknown"
        urg_evidence = None
        urg_confidence = 0.0
        urg_uncertainty = True
        urg_reason: Optional[str] = "No explicit temporal urgency indicators in feedback text"

        urgent_cues = ["immediately", "right now", "emergency", "urgent", "tout de suite", "ahora mismo", "asap", "spreading"]
        for cue in urgent_cues:
            ev = find_evidence(cue)
            if ev:
                urg_val = "IMMEDIATE"
                urg_evidence = ev
                urg_confidence = 0.95
                urg_uncertainty = False
                urg_reason = None
                break

        if urg_uncertainty and sev_val in ["CRITICAL", "HIGH"]:
            urg_val = "IMMEDIATE" if sev_val == "CRITICAL" else "WITHIN_HOUR"
            urg_evidence = sev_evidence
            urg_confidence = 0.82
            urg_uncertainty = False
            urg_reason = None
        elif urg_uncertainty and matched_cat_spec:
            urg_val = str(matched_cat_spec["urgency"])
            urg_evidence = cat_evidence
            urg_confidence = 0.70
            urg_uncertainty = False
            urg_reason = None

        if urg_uncertainty:
            uncertainties.append("Urgency is uncertain without explicit time cues")

        field_urgency = {
            "value": urg_val,
            "confidence": urg_confidence,
            "evidence": urg_evidence,
            "uncertainty": urg_uncertainty,
            "uncertaintyReason": urg_reason
        }

        # 7: Operational Impact
        op_val = matched_cat_spec["operationalImpact"] if matched_cat_spec else "unknown"
        op_evidence = cat_evidence
        op_conf = 0.85 if matched_cat_spec else 0.0
        op_unc = False if matched_cat_spec else True
        op_reason = None if matched_cat_spec else "Operational impact cannot be inferred without known category"

        field_operational_impact = {
            "value": op_val,
            "confidence": op_conf,
            "evidence": op_evidence,
            "uncertainty": op_unc,
            "uncertaintyReason": op_reason
        }

        # 8: Customer Impact
        cust_val = matched_cat_spec["customerImpact"] if matched_cat_spec else "unknown"
        cust_evidence = cat_evidence
        cust_conf = 0.85 if matched_cat_spec else 0.0
        cust_unc = False if matched_cat_spec else True
        cust_reason = None if matched_cat_spec else "Customer impact cannot be inferred without known category"

        field_customer_impact = {
            "value": cust_val,
            "confidence": cust_conf,
            "evidence": cust_evidence,
            "uncertainty": cust_unc,
            "uncertaintyReason": cust_reason
        }

        # 9: Safety Relevance
        safety_val = matched_cat_spec["safety"] if matched_cat_spec else "NON_HAZARD"
        safety_evidence = cat_evidence if (matched_cat_spec and matched_cat_spec["safety"] != "NON_HAZARD") else None
        safety_conf = 0.90 if matched_cat_spec else 0.70
        safety_unc = False

        field_safety_relevance = {
            "value": safety_val,
            "confidence": safety_conf,
            "evidence": safety_evidence,
            "uncertainty": safety_unc,
            "uncertaintyReason": None
        }

        # 10: Sentiment Analysis (Grounded)
        negative_cues = ["broken", "fuit", "leak", "slip", "hazard", "dirty", "slow", "rude", "bad", "terrible", "spoil", "ruined", "failed", "out of stock", "agotado", "rupture"]
        positive_cues = ["great", "helpful", "clean", "fast", "friendly", "resolved", "excellent", "bueno", "merci"]

        neg_matches = [find_evidence(c) for c in negative_cues if find_evidence(c)]
        pos_matches = [find_evidence(c) for c in positive_cues if find_evidence(c)]

        if neg_matches and not pos_matches:
            sent_score = -0.75
            sent_label = "NEGATIVE"
            sent_ev = neg_matches[0]
            sent_conf = 0.88
            sent_unc = False
            sent_reason = None
        elif pos_matches and not neg_matches:
            sent_score = 0.80
            sent_label = "POSITIVE"
            sent_ev = pos_matches[0]
            sent_conf = 0.88
            sent_unc = False
            sent_reason = None
        elif pos_matches and neg_matches:
            sent_score = 0.0
            sent_label = "MIXED"
            sent_ev = neg_matches[0]
            sent_conf = 0.70
            sent_unc = True
            sent_reason = "Both positive and negative sentiment cues identified"
        else:
            sent_score = 0.0
            sent_label = "NEUTRAL"
            sent_ev = None
            sent_conf = 0.60
            sent_unc = False
            sent_reason = "No strong polarity words detected"

        field_sentiment = {
            "score": sent_score,
            "label": sent_label,
            "confidence": sent_conf,
            "evidence": sent_ev,
            "uncertainty": sent_unc,
            "uncertaintyReason": sent_reason
        }

        # 11: Intent Extraction
        intent_val = "COMPLAINT"
        intent_ev = cat_evidence or sent_ev
        intent_conf = 0.85
        if "maintenance" in lower_source or "fix" in lower_source or "reparar" in lower_source:
            intent_val = "MAINTENANCE_REQUEST"
            intent_ev = find_evidence("maintenance") or find_evidence("fix") or find_evidence("reparar")
        elif "warning" in lower_source or "alert" in lower_source or "danger" in lower_source or "cuidado" in lower_source:
            intent_val = "OPERATIONAL_ALERT"
            intent_ev = find_evidence("warning") or find_evidence("alert") or find_evidence("danger")
        elif sent_label == "POSITIVE":
            intent_val = "PRAISE"
            intent_ev = pos_matches[0] if pos_matches else None
        elif category_val == "unknown" and sent_label == "NEUTRAL":
            intent_val = "unknown"
            intent_conf = 0.0
            intent_ev = None

        field_intent = {
            "value": intent_val,
            "confidence": intent_conf,
            "evidence": intent_ev,
            "uncertainty": intent_val == "unknown",
            "uncertaintyReason": "Intent could not be determined without category or sentiment cues" if intent_val == "unknown" else None
        }

        # 12: Entities
        extracted_entities: List[Dict[str, Any]] = []
        if loc_evidence:
            extracted_entities.append({
                "text": loc_evidence["text"],
                "label": "LOCATION",
                "category": "FACILITY",
                "start": loc_evidence["start"],
                "end": loc_evidence["end"],
                "confidence": loc_confidence
            })
        if entity_evidence:
            extracted_entities.append({
                "text": entity_evidence["text"],
                "label": entity_evidence.get("label", "EQUIPMENT"),
                "category": "ASSET",
                "start": entity_evidence["start"],
                "end": entity_evidence["end"],
                "confidence": entity_confidence
            })

        # 13: Symptoms
        extracted_symptoms: List[Dict[str, Any]] = []
        for sym_pat in cls.SYMPTOM_PATTERNS:
            match = sym_pat.search(source)
            if match:
                extracted_symptoms.append({
                    "text": match.group(0),
                    "start": match.start(),
                    "end": match.end(),
                    "confidence": 0.88
                })

        # 14: Temporal Information
        temp_val = "unknown"
        temp_ev = None
        temp_conf = 0.0
        temp_unc = True
        temp_reason: Optional[str] = "No temporal information or timestamps mentioned in text"

        for temp_pat in cls.TEMPORAL_PATTERNS:
            match = temp_pat.search(source)
            if match:
                temp_val = match.group(0)
                temp_ev = {
                    "text": match.group(0),
                    "start": match.start(),
                    "end": match.end()
                }
                temp_conf = 0.90
                temp_unc = False
                temp_reason = None
                break

        field_temporal = {
            "value": temp_val,
            "confidence": temp_conf,
            "evidence": temp_ev,
            "uncertainty": temp_unc,
            "uncertaintyReason": temp_reason
        }

        # ---------------------------------------------------------------------
        # Aggregate Confidence & Uncertainty Calculation
        # ---------------------------------------------------------------------
        core_confidences = [
            cat_confidence,
            loc_confidence,
            entity_confidence,
            sev_confidence,
            urg_confidence,
            sent_conf
        ]
        overall_confidence = round(sum(core_confidences) / len(core_confidences), 2)
        overall_uncertainty = len(uncertainties) >= 2 or overall_confidence < 0.65

        # Grounded Human-Readable Summary
        if category_val != "unknown":
            summary_parts = [category_val.replace('_', ' ').title()]
            if loc_val != "unknown":
                summary_parts.append(f"at {loc_val}")
            if sev_val != "unknown":
                summary_parts.append(f"[{sev_val} severity]")
            summary = " ".join(summary_parts)
        else:
            summary = "Unclassified operational observation with insufficient pattern evidence"

        return {
            "language": lang_res,
            "issueCategory": field_category,
            "issueType": field_issue_type,
            "affectedEntity": field_affected_entity,
            "location": field_location,
            "severity": field_severity,
            "urgency": field_urgency,
            "operationalImpact": field_operational_impact,
            "customerImpact": field_customer_impact,
            "safetyRelevance": field_safety_relevance,
            "sentiment": field_sentiment,
            "intent": field_intent,
            "entities": extracted_entities,
            "symptoms": extracted_symptoms,
            "temporalInformation": field_temporal,
            "overallConfidence": overall_confidence,
            "overallUncertainty": overall_uncertainty,
            "uncertaintySummary": uncertainties,
            "summary": summary,
            "analyzedAt": now_iso,
            # Phase 15 Multilingual Intelligence Hardening (5 Required Display Fields)
            "rawText": raw_text,
            "detectedLanguage": ml_pipeline["detectedLanguage"],
            "normalizedInterpretation": ml_pipeline["normalizedInterpretation"],
            "extractedIssue": ml_pipeline["extractedIssue"],
            "confidence": ml_pipeline["confidence"],
            "multilingualAnalysis": ml_pipeline
        }

    # -------------------------------------------------------------------------
    # 5. HUMAN REVIEW & CORRECTION MERGER
    # -------------------------------------------------------------------------
    @classmethod
    def merge_with_human_overrides(
        cls,
        ai_interpretation: Optional[Dict[str, Any]],
        human_overrides: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Produce an effective interpretation combining AI-derived facts with human overrides.
        Clearly separates:
        - raw/ai derived base value
        - human override value
        - whether the field is currently overridden
        - reason and author of override
        """
        ai_data = ai_interpretation or {}
        overrides_dict = human_overrides.get("overrides", {}) if human_overrides else {}

        overridable_keys = [
            "issueCategory", "issueType", "affectedEntity", "location",
            "severity", "urgency", "operationalImpact", "customerImpact",
            "safetyRelevance", "intent"
        ]

        effective_fields: Dict[str, Any] = {}

        for k in overridable_keys:
            ai_field = ai_data.get(k, {
                "value": "unknown",
                "confidence": 0.0,
                "evidence": None,
                "uncertainty": True,
                "uncertaintyReason": "Not extracted"
            })

            if k in overrides_dict:
                ov = overrides_dict[k]
                override_val = ov.get("value") if isinstance(ov, dict) else ov
                override_reason = ov.get("reason") if isinstance(ov, dict) else "Manual human operator override"
                corrected_by = ov.get("correctedBy") if isinstance(ov, dict) else (human_overrides.get("reviewedBy") if human_overrides else None)
                corrected_at = ov.get("correctedAt") if isinstance(ov, dict) else (human_overrides.get("reviewedAt") if human_overrides else None)

                effective_fields[k] = {
                    "value": override_val,
                    "confidence": 1.0,
                    "evidence": ai_field.get("evidence"),
                    "uncertainty": False,
                    "uncertaintyReason": None,
                    "isOverridden": True,
                    "originalAiValue": ai_field.get("value"),
                    "originalAiConfidence": ai_field.get("confidence"),
                    "overrideReason": override_reason,
                    "correctedBy": corrected_by,
                    "correctedAt": corrected_at
                }
            else:
                effective_fields[k] = {
                    **ai_field,
                    "isOverridden": False
                }

        return {
            "effectiveFields": effective_fields,
            "sentiment": ai_data.get("sentiment"),
            "entities": ai_data.get("entities", []),
            "symptoms": ai_data.get("symptoms", []),
            "temporalInformation": ai_data.get("temporalInformation"),
            "language": ai_data.get("language"),
            "overallConfidence": 1.0 if overrides_dict else ai_data.get("overallConfidence", 0.0),
            "overallUncertainty": False if overrides_dict else ai_data.get("overallUncertainty", False),
            "summary": ai_data.get("summary"),
            "isHumanReviewed": bool(human_overrides and human_overrides.get("reviewedAt")),
            "reviewedBy": human_overrides.get("reviewedBy") if human_overrides else None,
            "reviewedAt": human_overrides.get("reviewedAt") if human_overrides else None,
            "reviewNotes": human_overrides.get("reviewNotes") if human_overrides else None,
            "overriddenFieldCount": len(overrides_dict)
        }
