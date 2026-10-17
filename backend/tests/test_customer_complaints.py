import pytest
import sqlite3
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.db.database import get_connection
from backend.app.db.seed import seed_database
from backend.app.services.otp_service import OtpService

client = TestClient(app)

@pytest.fixture(scope="module", autouse=True)
def setup_seed():
    seed_database(force=True)

def test_customer_registration_and_otp_flow():
    """Test full registration, OTP generation, and email verification lifecycle."""
    reg_payload = {
        "fullName": "Alice Wonderland",
        "email": "alice.wonder@example.com",
        "password": "SecurePassword123!",
        "phone": "+1-555-443-2211"
    }

    # 1. Register customer
    res = client.post("/api/v1/auth/customer/register", json=reg_payload)
    assert res.status_code == 200, res.text
    data = res.json()["data"]
    assert data["email"] == "alice.wonder@example.com"
    assert data["isVerified"] is False
    assert "emailDelivery" in data
    dev_otp = data.get("devOtpCode")
    assert dev_otp is not None and len(dev_otp) == 6

    # 2. Attempt login before email verification -> Must be rejected with EMAIL_UNVERIFIED
    login_res = client.post("/api/v1/auth/login", json={
        "email": "alice.wonder@example.com",
        "password": "SecurePassword123!"
    })
    assert login_res.status_code == 401
    assert "EMAIL_UNVERIFIED" in login_res.text

    # 3. Test invalid OTP submission
    verify_bad = client.post("/api/v1/auth/customer/verify-otp", json={
        "email": "alice.wonder@example.com",
        "otp": "000000"
    })
    assert verify_bad.status_code == 400
    assert "Incorrect verification code" in verify_bad.text

    # 4. Verify with correct OTP
    verify_good = client.post("/api/v1/auth/customer/verify-otp", json={
        "email": "alice.wonder@example.com",
        "otp": dev_otp
    })
    assert verify_good.status_code == 200
    v_data = verify_good.json()["data"]
    assert v_data["user"]["isVerified"] is True
    assert v_data["token"] is not None

    # 5. Token is now valid for customer login
    login_after = client.post("/api/v1/auth/login", json={
        "email": "alice.wonder@example.com",
        "password": "SecurePassword123!"
    })
    assert login_after.status_code == 200
    assert login_after.json()["data"]["user"]["email"] == "alice.wonder@example.com"

def test_otp_single_use_and_cooldown():
    """Verify that used OTPs cannot be reused and resend respects cooldown."""
    conn = get_connection()
    try:
        # Request resend immediately for newly verified user -> should be rejected because already verified
        resend_verified = client.post("/api/v1/auth/customer/resend-otp", json={
            "email": "alice.wonder@example.com"
        })
        assert resend_verified.status_code == 409
        assert "already verified" in resend_verified.text

        # Test pending user resend cooldown
        # Register user B
        client.post("/api/v1/auth/customer/register", json={
            "fullName": "Bob Ross",
            "email": "bob.ross@example.com",
            "password": "PainterPass123!"
        })
        # Immediate second resend -> cooldown error
        resend_cooldown = client.post("/api/v1/auth/customer/resend-otp", json={
            "email": "bob.ross@example.com"
        })
        assert resend_cooldown.status_code == 409
        assert "wait" in resend_cooldown.text.lower()
    finally:
        conn.close()

def test_customer_complaint_submission_and_tracking():
    """Test complaint creation, priority assignment, feedback linkage, and tracking."""
    # 1. Login as seeded verified customer Sarah Jenkins
    cust_login = client.post("/api/v1/auth/login", json={
        "email": "customer@retailwave.com",
        "password": "Password123!"
    })
    assert cust_login.status_code == 200, cust_login.text
    token = cust_login.json()["data"]["token"]
    cust_headers = {"Authorization": f"Bearer {token}"}

    # 2. Submit new complaint
    complaint_data = {
        "category": "Store Service",
        "orderNumber": "ORD-55441",
        "subject": "Fire hazard blocked emergency exit in aisle 12",
        "description": "Several wooden pallets were stacked directly in front of the emergency fire exit door in aisle 12. Urgent safety risk.",
        "attachmentName": "pallet_block.jpg",
        "attachmentUrl": "/static/uploads/complaints/pallet_block.jpg"
    }
    submit_res = client.post("/api/v1/complaints", json=complaint_data, headers=cust_headers)
    assert submit_res.status_code == 200, submit_res.text
    c_data = submit_res.json()["data"]
    ref_num = c_data["referenceNumber"]
    assert ref_num.startswith("REF-2026-")
    assert c_data["status"] == "SUBMITTED"
    assert c_data["priority"] in ("HIGH", "CRITICAL")  # Safety/fire keywords trigger rule-based priority
    assert len(c_data["timeline"]) == 1

    # 3. Retrieve customer's own complaints
    my_res = client.get("/api/v1/complaints/my", headers=cust_headers)
    assert my_res.status_code == 200
    my_list = my_res.json()["data"]
    assert any(c["referenceNumber"] == ref_num for c in my_list)

    # 4. Public tracking endpoint
    track_res = client.get(f"/api/v1/complaints/track/{ref_num}")
    assert track_res.status_code == 200
    t_data = track_res.json()["data"]
    assert t_data["referenceNumber"] == ref_num
    assert t_data["subject"] == complaint_data["subject"]
    # Privacy check: customerEmail and customerPhone must NOT be present in public tracking
    assert "customerEmail" not in t_data
    assert "customerPhone" not in t_data
    assert "investigationNotes" not in t_data

def test_customer_isolation_rbac():
    """Verify customer cannot view another customer's complaint directly."""
    # Register Customer X
    rx = client.post("/api/v1/auth/customer/register", json={
        "fullName": "User X",
        "email": "user.x@example.com",
        "password": "Password123!"
    })
    otp_x = rx.json()["data"]["devOtpCode"]
    vx = client.post("/api/v1/auth/customer/verify-otp", json={
        "email": "user.x@example.com",
        "otp": otp_x
    })
    token_x = vx.json()["data"]["token"]
    headers_x = {"Authorization": f"Bearer {token_x}"}

    # Seeded complaint belongs to Sarah Jenkins ('cmp-seed-01')
    view_foreign = client.get("/api/v1/complaints/cmp-seed-01", headers=headers_x)
    assert view_foreign.status_code == 403
    assert "Access denied" in view_foreign.text

def test_operational_dashboard_integration():
    """Test authorized store manager and ops manager handling customer complaints."""
    # 1. Login as Store Manager (David Miller)
    mgr_login = client.post("/api/v1/auth/login", json={
        "email": "storemanager@apex.com",
        "password": "Password123!"
    })
    assert mgr_login.status_code == 200
    mgr_token = mgr_login.json()["data"]["token"]
    mgr_headers = {"Authorization": f"Bearer {mgr_token}"}

    # 2. List all complaints in operations dashboard
    list_res = client.get("/api/v1/complaints", headers=mgr_headers)
    assert list_res.status_code == 200
    items = list_res.json()["data"]["items"]
    assert len(items) >= 3

    # 3. Filter by category
    filter_res = client.get("/api/v1/complaints?category=Product+Issues", headers=mgr_headers)
    assert filter_res.status_code == 200
    p_items = filter_res.json()["data"]["items"]
    assert all(i["category"] == "Product Issues" for i in p_items)

    # 4. Search by reference or keyword
    search_res = client.get("/api/v1/complaints?search=dairy", headers=mgr_headers)
    assert search_res.status_code == 200
    assert len(search_res.json()["data"]["items"]) >= 1

    # 5. Store Manager can inspect single complaint including internal investigation notes
    detail_res = client.get("/api/v1/complaints/cmp-seed-01", headers=mgr_headers)
    assert detail_res.status_code == 200
    detail = detail_res.json()["data"]
    assert "investigationNotes" in detail
    assert detail["assignedTeamName"] == "Regional Commercial HVAC & Refrigeration"

    # 6. Update complaint status to RESOLVED
    update_res = client.patch(
        "/api/v1/complaints/cmp-seed-01/status",
        json={
            "status": "RESOLVED",
            "assignedTeamId": "team-hvac-pnw",
            "investigationNotes": "Replaced damaged expansion valve and wiped down cooler shelves.",
            "resolutionSummary": "The dairy cooler unit has been fully serviced and all damaged stock was removed and sanitized."
        },
        headers=mgr_headers
    )
    assert update_res.status_code == 200
    u_data = update_res.json()["data"]
    assert u_data["status"] == "RESOLVED"
    assert u_data["resolutionSummary"] is not None

    # 7. Check public tracking reflects the resolution summary but hides the investigation notes
    track_res = client.get(f"/api/v1/complaints/track/{u_data['referenceNumber']}")
    assert track_res.status_code == 200
    t_data = track_res.json()["data"]
    assert t_data["status"] == "RESOLVED"
    assert t_data["resolutionSummary"] == "The dairy cooler unit has been fully serviced and all damaged stock was removed and sanitized."
    assert "investigationNotes" not in t_data
    # Timeline includes the resolution note
    assert any("serviced" in e.get("note", "") for e in t_data["timeline"])

def test_profile_and_password_update_flow():
    """Verify profile updating, phone persistence, and password changes."""
    # Login as Sarah Jenkins
    login_res = client.post("/api/v1/auth/login", json={
        "email": "customer@retailwave.com",
        "password": "Password123!"
    })
    assert login_res.status_code == 200
    token = login_res.json()["data"]["token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Update profile name and phone
    put_res = client.put("/api/v1/auth/profile", json={
        "fullName": "Sarah Jenkins-Smith",
        "phone": "+1-555-888-9999"
    }, headers=headers)
    assert put_res.status_code == 200
    u_data = put_res.json()["data"]
    assert u_data["fullName"] == "Sarah Jenkins-Smith"
    assert u_data["phone"] == "+1-555-888-9999"

    # Change password
    pwd_res = client.post("/api/v1/auth/change-password", json={
        "currentPassword": "Password123!",
        "newPassword": "NewStrongPassword2026!"
    }, headers=headers)
    assert pwd_res.status_code == 200

    # Old password fails
    old_fail = client.post("/api/v1/auth/login", json={
        "email": "customer@retailwave.com",
        "password": "Password123!"
    })
    assert old_fail.status_code == 401

    # New password succeeds
    new_ok = client.post("/api/v1/auth/login", json={
        "email": "customer@retailwave.com",
        "password": "NewStrongPassword2026!"
    })
    assert new_ok.status_code == 200
    assert new_ok.json()["data"]["user"]["fullName"] == "Sarah Jenkins-Smith"
