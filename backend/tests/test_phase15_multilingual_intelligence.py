"""
Phase 15: Multilingual Operational Intelligence Hardening Test Suite
Validates:
1. Pipeline execution: Original Text -> Language Detection -> Normalization -> Semantic Understanding -> Structured Extraction -> Evidence Preservation
2. Evidence preservation constraint: Never destroy original feedback (raw_text is immutable)
3. 5 required display fields: original text, detected language, normalized interpretation, extracted issue, confidence
4. Multi-language coverage: English, Indian languages in native scripts (Hindi, Tamil, Telugu, Bengali, Gujarati), transliterated text (Hinglish, Tanglish, Tenglish, Kanglish, Benglish), mixed-language text, spelling errors/phonetic typos, and informal language
5. Cross-lingual semantic clustering: Equivalent issues in different languages cluster together with correlationType == 'SAME_ISSUE'
6. Empirical evaluation data: No unsubstantiated accuracy claims without evaluation data (runs evaluation benchmark suite)
"""

import json
import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.db.database import get_connection
from backend.app.db.seed import seed_database
from backend.app.services.multilingual_service import MultilingualService
from backend.app.services.clustering_service import ClusteringService
from backend.app.core.security import create_access_token

client = TestClient(app)


@pytest.fixture(scope="module", autouse=True)
def setup_test_db():
    seed_database(force=True)
    yield


@pytest.fixture
def auth_headers():
    token = create_access_token({
        "userId": "usr-ops",
        "email": "opsmanager@apex.com",
        "role": "OPERATIONS_MANAGER",
        "organizationId": "org-apex-01"
    })
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def store_headers():
    token = create_access_token({
        "userId": "usr-store",
        "email": "storemanager@apex.com",
        "role": "STORE_MANAGER",
        "organizationId": "org-apex-01",
        "storeId": "store-104"
    })
    return {"Authorization": f"Bearer {token}"}


class TestPhase15MultilingualIntelligence:

    # -------------------------------------------------------------------------
    # 1. Five-Stage Pipeline & Evidence Preservation
    # -------------------------------------------------------------------------
    def test_pipeline_five_stages_and_evidence_preservation(self):
        """Verify the 5-stage pipeline processes noisy Indic feedback and immutably preserves original text."""
        raw_input = "डेयरी सेक्शन में दूध का फ्रिज बहुत ज्यादा लीक कर रहा है, फर्श पर फिसलन है।"

        result = MultilingualService.process_multilingual_pipeline(raw_input)

        # Stage 1: Original text preserved immutably
        assert result["rawText"] == raw_input
        assert len(result["evidence"]) > 0
        assert result["evidence"][0]["text"] == raw_input

        # Stage 2: Language detection
        assert result["detectedLanguage"]["code"] == "hi"
        assert result["detectedLanguage"]["script"] == "Devanagari"
        assert result["detectedLanguage"]["confidence"] >= 0.90

        # Stage 3: Normalization into canonical English interpretation
        assert "dairy" in result["normalizedInterpretation"].lower()
        assert any(w in result["normalizedInterpretation"].lower() for w in ["chiller", "cooler", "refrigerator", "fridge"])
        assert "leak" in result["normalizedInterpretation"].lower()

        # Stage 4: Semantic understanding & Structured extraction
        extracted = result["extractedIssue"]
        assert extracted["category"] == "FACILITIES_MAINTENANCE"
        assert extracted["issueType"] == "REFRIGERATION_FAILURE"
        assert extracted["isSafetyHazard"] is True
        assert extracted["severity"] in ["HIGH", "CRITICAL"]

        # Stage 5: Calibrated confidence
        assert result["confidence"] >= 0.85

    # -------------------------------------------------------------------------
    # 2. Mandatory Display Fields
    # -------------------------------------------------------------------------
    def test_display_five_mandatory_fields(self, auth_headers):
        """API must return the 5 mandatory display fields for operational operators."""
        payload = {
            "text": "chiller frij se pani leak ho raha hai farsh bohot geela hai",
            "languageHint": "hi-Latn"
        }

        resp = client.post("/api/v1/multilingual/parse", headers=auth_headers, json=payload)
        assert resp.status_code == 200
        data = resp.json()["data"]

        # 1. Original text
        assert "rawText" in data
        assert data["rawText"] == payload["text"]

        # 2. Detected language
        assert "detectedLanguage" in data
        assert data["detectedLanguage"]["code"] == "hi-Latn"
        assert data["detectedLanguage"]["isTransliterated"] is True

        # 3. Normalized interpretation
        assert "normalizedInterpretation" in data
        assert "water is leaking" in data["normalizedInterpretation"].lower() or "leak" in data["normalizedInterpretation"].lower()

        # 4. Extracted issue
        assert "extractedIssue" in data
        assert data["extractedIssue"]["category"] == "FACILITIES_MAINTENANCE"
        assert data["extractedIssue"]["isSafetyHazard"] is True

        # 5. Confidence
        assert "confidence" in data
        assert 0.0 <= data["confidence"] <= 1.0

    # -------------------------------------------------------------------------
    # 3. Native Indian Scripts Support
    # -------------------------------------------------------------------------
    def test_native_indic_scripts_support(self):
        """Verify native script support for Hindi, Tamil, Telugu, Kannada, Bengali, Gujarati."""
        cases = [
            # Hindi (Devanagari)
            ("डेयरी सेक्शन में दूध का फ्रिज बहुत ज्यादा लीक कर रहा है, फर्श पर फिसलन है।", "hi", "Devanagari", "FACILITIES_MAINTENANCE", True),
            # Tamil
            ("பால் பிரிவு கூலர் தண்ணீர் லீக் ஆகிறது தரை வழுக்குகிறது", "ta", "Tamil", "FACILITIES_MAINTENANCE", True),
            # Telugu
            ("పాల విభాగంలో ఫ్రిజ్ నీరు కారుతోంది నేల జారిపోతోంది", "te", "Telugu", "FACILITIES_MAINTENANCE", True),
            # Kannada
            ("ಡೈರಿ ವಿಭಾಗದಲ್ಲಿ ಕೂಲರ್ ನೀರು ಸೋರುತ್ತಿದೆ ನೆಲ ಜಾರುತ್ತಿದೆ", "kn", "Kannada", "FACILITIES_MAINTENANCE", True),
            # Bengali
            ("দুধ সেকশনে কুলার থেকে জল পড়ছে মেঝে পিছল হয়ে আছে", "bn", "Bengali", "FACILITIES_MAINTENANCE", True),
            # Gujarati
            ("ડેરી સેક્શનમાં ફ્રિજમાંથી પાણી લીક થાય છે અને ફ્લોર પર લપસણો છે", "gu", "Gujarati", "FACILITIES_MAINTENANCE", True)
        ]

        for text, exp_code, exp_script, exp_cat, exp_safety in cases:
            res = MultilingualService.process_multilingual_pipeline(text)
            det = res["detectedLanguage"]
            ext = res["extractedIssue"]

            assert det["code"] == exp_code, f"Failed language code for {exp_code}: got {det['code']}"
            assert det["script"] == exp_script, f"Failed script for {exp_script}: got {det['script']}"
            assert ext["category"] == exp_cat, f"Failed category for {exp_code}: got {ext['category']}"
            assert ext["isSafetyHazard"] == exp_safety, f"Failed safety flag for {exp_code}"
            # Verify raw text was never destroyed
            assert res["rawText"] == text

    # -------------------------------------------------------------------------
    # 4. Transliterated & Mixed-Language Support
    # -------------------------------------------------------------------------
    def test_transliterated_and_mixed_language_support(self):
        """Verify Romanized transliterated Indic feedback (Hinglish, Tanglish, etc.) and code-mixing."""
        cases = [
            # Hinglish
            ("dairy section cooler se pani leak ho raha hai farsh geela hai girne ka darr hai", "hi-Latn", True, "FACILITIES_MAINTENANCE", True),
            # Tanglish
            ("dairy fridge la thanni leak aaguthu floor romba slippery ah irukku", "ta-Latn", True, "FACILITIES_MAINTENANCE", True),
            # Tenglish
            ("dairy section fridge lo neellu leak avtundi floor meeda jaripoyela undi", "te-Latn", True, "FACILITIES_MAINTENANCE", True),
            # Kanglish
            ("dairy fridgealli neeru leak aagthide floor thumba slippery aagide", "kn-Latn", True, "FACILITIES_MAINTENANCE", True),
            # Benglish
            ("dairy section cooler theke jol porche floor pichil ache", "bn-Latn", True, "FACILITIES_MAINTENANCE", True),
            # Code-Mixed POS Malfunction
            ("billing lane 3 barcode scanner velai seyyala, romba queue aagudhu", "ta-Latn", True, "CHECKOUT_POS", False)
        ]

        for text, exp_code, exp_translit, exp_cat, exp_safety in cases:
            res = MultilingualService.process_multilingual_pipeline(text)
            det = res["detectedLanguage"]
            ext = res["extractedIssue"]

            assert det["code"] == exp_code, f"Failed translit lang code for {exp_code}: got {det['code']}"
            assert det["isTransliterated"] is exp_translit
            assert ext["category"] == exp_cat, f"Failed category for {exp_code}: got {ext['category']}"
            assert ext["isSafetyHazard"] is exp_safety

    # -------------------------------------------------------------------------
    # 5. Spelling Errors & Phonetic Typos
    # -------------------------------------------------------------------------
    def test_spelling_errors_and_phonetic_typos(self):
        """Verify phonetic typos ('frij', 'chiler', 'leeking', 'slipery', 'temprature') are repaired."""
        noisy_text = "dairy section frij and chiler is leeking wtr, floor slipery dangrous temprature high"

        res = MultilingualService.process_multilingual_pipeline(noisy_text)

        # Raw text MUST be untouched
        assert res["rawText"] == noisy_text

        # Typos recorded
        corrections = res["spellingCorrections"]
        assert "frij" in corrections
        assert corrections["frij"] == "fridge"
        assert "chiler" in corrections
        assert corrections["chiler"] == "chiller"
        assert "leeking" in corrections
        assert corrections["leeking"] == "leaking"
        assert "slipery" in corrections
        assert corrections["slipery"] == "slippery"

        # Normalized interpretation reflects canonical English
        norm = res["normalizedInterpretation"].lower()
        assert "fridge" in norm
        assert "chiller" in norm
        assert "leaking" in norm
        assert "slippery" in norm

        # Correctly classified despite heavy typos
        ext = res["extractedIssue"]
        assert ext["category"] == "FACILITIES_MAINTENANCE"
        assert ext["issueType"] == "REFRIGERATION_FAILURE"
        assert ext["isSafetyHazard"] is True

    # -------------------------------------------------------------------------
    # 6. Cross-Lingual Semantic Clustering
    # -------------------------------------------------------------------------
    def test_cross_lingual_semantic_clustering_connects_equivalent_issues(self):
        """
        Verify semantic clustering connects equivalent operational issues expressed in:
        1. English
        2. Hindi Devanagari
        3. Tamil script
        4. Hinglish (Latin)
        5. Tanglish (Latin)
        Pairwise similarity between all cross-lingual pairs must be >= 0.65 (SAME_ISSUE).
        """
        store_id = "store-104"
        timestamp = "2026-10-17T01:00:00Z"

        feedbacks = [
            {
                "id": "fb-en-01",
                "store_id": store_id,
                "channel_type": "CUSTOMER_COMPLAINT",
                "submitter_type": "CUSTOMER",
                "submitted_at": timestamp,
                "created_at": timestamp,
                "raw_text": "Water is leaking from dairy chiller floor is slippery",
                "ai_interpretation": json.dumps(MultilingualService.process_multilingual_pipeline("Water is leaking from dairy chiller floor is slippery")),
                "normalized_text": "Water is leaking from dairy chiller floor is slippery"
            },
            {
                "id": "fb-hi-01",
                "store_id": store_id,
                "channel_type": "CUSTOMER_COMPLAINT",
                "submitter_type": "CUSTOMER",
                "submitted_at": timestamp,
                "created_at": timestamp,
                "raw_text": "डेयरी सेक्शन में दूध का फ्रिज बहुत ज्यादा लीक कर रहा है, फर्श पर फिसलन है।",
                "ai_interpretation": json.dumps(MultilingualService.process_multilingual_pipeline("डेयरी सेक्शन में दूध का फ्रिज बहुत ज्यादा लीक कर रहा है, फर्श पर फिसलन है।")),
                "normalized_text": "In dairy section dairy milk refrigerator cooler is leaking water floor is very slippery slip hazard"
            },
            {
                "id": "fb-ta-01",
                "store_id": store_id,
                "channel_type": "CUSTOMER_COMPLAINT",
                "submitter_type": "CUSTOMER",
                "submitted_at": timestamp,
                "created_at": timestamp,
                "raw_text": "பால் பிரிவு கூலர் தண்ணீர் லீக் ஆகிறது தரை வழுக்குகிறது",
                "ai_interpretation": json.dumps(MultilingualService.process_multilingual_pipeline("பால் பிரிவு கூலர் தண்ணீர் லீக் ஆகிறது தரை வழுக்குகிறது")),
                "normalized_text": "In dairy section refrigerator cooler water is leaking floor is slippery slip hazard"
            },
            {
                "id": "fb-hinglish-01",
                "store_id": store_id,
                "channel_type": "CUSTOMER_COMPLAINT",
                "submitter_type": "CUSTOMER",
                "submitted_at": timestamp,
                "created_at": timestamp,
                "raw_text": "dairy section cooler se pani leak ho raha hai farsh geela hai girne ka darr hai",
                "ai_interpretation": json.dumps(MultilingualService.process_multilingual_pipeline("dairy section cooler se pani leak ho raha hai farsh geela hai girne ka darr hai")),
                "normalized_text": "In dairy section water is leaking from cooler floor is very wet slippery slip fall hazard"
            },
            {
                "id": "fb-tanglish-01",
                "store_id": store_id,
                "channel_type": "CUSTOMER_COMPLAINT",
                "submitter_type": "CUSTOMER",
                "submitted_at": timestamp,
                "created_at": timestamp,
                "raw_text": "dairy fridge la thanni leak aaguthu floor romba slippery ah irukku",
                "ai_interpretation": json.dumps(MultilingualService.process_multilingual_pipeline("dairy fridge la thanni leak aaguthu floor romba slippery ah irukku")),
                "normalized_text": "In dairy section water is leaking from dairy cooler floor is very slippery slip hazard"
            }
        ]

        # Extract features for all multilingual representations
        features = [ClusteringService.extract_semantic_features(fb) for fb in feedbacks]

        # Verify all 5 extracted features have matching category & issueType
        for f in features:
            assert f["category"] == "FACILITIES_MAINTENANCE", f"Expected FACILITIES_MAINTENANCE, got {f['category']}"
            assert f["issueType"] == "REFRIGERATION_FAILURE", f"Expected REFRIGERATION_FAILURE, got {f['issueType']}"

        # Test cross-lingual pairwise similarity across all 10 pairs
        pair_count = 0
        for i in range(len(features)):
            for j in range(i + 1, len(features)):
                pair_count += 1
                sim_score, corr_type = ClusteringService.calculate_pairwise_similarity(features[i], features[j])
                assert corr_type == "SAME_ISSUE", (
                    f"Cross-lingual pair ({features[i]['id']} vs {features[j]['id']}) failed: "
                    f"score={sim_score}, type={corr_type}"
                )
                assert sim_score >= 0.65, f"Score below threshold: {sim_score}"

        assert pair_count == 10, "Should have verified all 10 pairwise cross-lingual combinations"

    # -------------------------------------------------------------------------
    # 7. Grounded Evaluation Benchmark (No Claims Without Data)
    # -------------------------------------------------------------------------
    def test_empirical_evaluation_benchmark_data(self, auth_headers):
        """
        Verify empirical benchmark measurements adhere to:
        'Do not claim language accuracy without evaluation data.'
        """
        resp = client.get("/api/v1/multilingual/benchmark", headers=auth_headers)
        assert resp.status_code == 200
        bm = resp.json()["data"]

        # Validate grounded metrics
        assert bm["totalTestCases"] >= 15
        assert bm["detectionAccuracyPct"] >= 90.0, f"Detection accuracy too low: {bm['detectionAccuracyPct']}%"
        assert bm["categoryAccuracyPct"] >= 90.0, f"Category accuracy too low: {bm['categoryAccuracyPct']}%"
        assert bm["issueTypeAccuracyPct"] >= 90.0, f"Issue type accuracy too low: {bm['issueTypeAccuracyPct']}%"
        assert bm["safetyHazardAccuracyPct"] >= 90.0, f"Safety accuracy too low: {bm['safetyHazardAccuracyPct']}%"
        assert bm["crossLingualClusteringPrecisionPct"] >= 95.0, f"Clustering precision too low: {bm['crossLingualClusteringPrecisionPct']}%"

        # Languages covered must include English, Hindi, Tamil, and transliterated variants
        langs = bm["languagesCovered"]
        assert "en" in langs
        assert "hi" in langs
        assert "hi-Latn" in langs
        assert "ta-Latn" in langs

        # Check test cases endpoint
        tc_resp = client.get("/api/v1/multilingual/test-cases", headers=auth_headers)
        assert tc_resp.status_code == 200
        cases = tc_resp.json()["data"]
        assert len(cases) == bm["totalTestCases"]

    # -------------------------------------------------------------------------
    # 8. End-to-End Ingestion & Persistence Integrity
    # -------------------------------------------------------------------------
    def test_ingest_multilingual_feedback_end_to_end(self, store_headers):
        """
        Ingest native Hindi feedback through the public feedback endpoint.
        Verify verbatim raw storage, normalized interpretation, and 5 display fields.
        """
        raw_hindi = "डेयरी सेक्शन में दूध का फ्रिज बहुत ज्यादा लीक कर रहा है, फर्श पर फिसलन है।"

        post_resp = client.post(
            "/api/v1/feedback",
            headers=store_headers,
            json={
                "storeId": "store-104",
                "channelType": "CUSTOMER_COMPLAINT",
                "rawText": raw_hindi
            }
        )
        assert post_resp.status_code == 201
        created = post_resp.json()["data"]
        fb_id = created["id"]

        # 1. Original text MUST be verbatim and immutable
        assert created["rawText"] == raw_hindi

        # 2. Detected language
        assert created["languageCode"] == "hi"

        # 3. Normalized interpretation
        assert created["normalizedInterpretation"] is not None
        assert "dairy" in created["normalizedInterpretation"].lower()
        assert "leak" in created["normalizedInterpretation"].lower()

        # 4. Extracted issue
        ai = created["aiInterpretation"]
        extracted = ai.get("extractedIssue", {})
        assert extracted.get("category") == "FACILITIES_MAINTENANCE"
        assert extracted.get("isSafetyHazard") is True

        # 5. Confidence
        assert created["multilingualConfidence"] is not None
        assert created["multilingualConfidence"] >= 0.85

        # Direct database verification to prove raw text was NEVER corrupted or mutated
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT raw_text, normalized_text, language_code FROM feedback_items WHERE id = ?;", (fb_id,))
        row = cur.fetchone()
        conn.close()

        assert row is not None
        assert row["raw_text"] == raw_hindi, "Database raw_text was mutated or corrupted!"
        assert row["language_code"] == "hi"
        assert row["normalized_text"] is not None
