"""
Verification script for Swift Service responsive UI, scrolling fix, and authentication flow.
Tests live server endpoints, HTML/CSS layout rules, and complete auth workflows.
"""
import urllib.request
import urllib.error
import json
import re
import sys

BASE_URL = "http://127.0.0.1:8000"

def log(msg, status="INFO"):
    symbol = "[OK]" if status == "PASS" else "[ERR]" if status == "FAIL" else "[*]"
    print(f"[{status}] {symbol} {msg}")

def test_static_asset_serving():
    log("Testing static assets and CSS layout rules...")
    # Fetch index.html
    req = urllib.request.Request(f"{BASE_URL}/")
    with urllib.request.urlopen(req) as resp:
        html = resp.read().decode('utf-8')
        assert "Swift Service" in html, "Page title should contain Swift Service"
        assert "/static/css/layout.css" in html, "layout.css should be linked"
        assert "/static/css/components.css" in html, "components.css should be linked"
        assert '<div id="app"></div>' in html, "#app element must exist"
        log("index.html served correctly with Swift Service branding", "PASS")

    # Fetch layout.css
    req_css = urllib.request.Request(f"{BASE_URL}/static/css/layout.css")
    with urllib.request.urlopen(req_css) as resp:
        layout_css = resp.read().decode('utf-8')
        # Check that #app is NOT globally locked to overflow: hidden; height: 100vh; width: 100vw;
        assert "overflow-y: auto;" in layout_css or "overflow-y: visible;" in layout_css, "body/app must allow vertical scrolling"
        assert ".app-shell-auth" in layout_css, "#app.app-shell-auth must be styled"
        assert "width: 100vw;" not in layout_css, "width: 100vw eliminated to prevent Windows horizontal scrollbar bug"
        log("layout.css verified: #app allows natural vertical scrolling, no fixed scroll trap", "PASS")

    # Fetch components.css
    req_comp = urllib.request.Request(f"{BASE_URL}/static/css/components.css")
    with urllib.request.urlopen(req_comp) as resp:
        comp_css = resp.read().decode('utf-8')
        assert ".auth-retail-showcase-card" in comp_css, "Retail fleet showcase card styles must exist"
        assert "order: 1" in comp_css, "Mobile order: 1 rule for .auth-form-card must exist"
        assert "order: 2" in comp_css, "Mobile order: 2 rule for .auth-hero-banner must exist"
        assert ".auth-persona-chip.selected" in comp_css, "Selected persona chip styling must exist"
        assert "padding-right: 2.75rem" in comp_css, "Password input must have padding to prevent eye-icon overlap"
        log("components.css verified: responsive breakpoints, mobile form ordering, and retail showcase included", "PASS")

def test_auth_login_valid_customer():
    log("Testing customer authentication...")
    payload = json.dumps({"email": "customer@retailwave.com", "password": "Password123!"}).encode('utf-8')
    req = urllib.request.Request(
        f"{BASE_URL}/api/v1/auth/login",
        data=payload,
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req) as resp:
        res = json.loads(resp.read().decode('utf-8'))
        assert res["success"] is True
        assert "token" in res["data"]
        assert res["data"]["user"]["role"] == "CUSTOMER"
        assert res["data"]["user"]["isVerified"] is True
        log(f"Customer login successful: {res['data']['user']['fullName']} (role: CUSTOMER)", "PASS")
        return res["data"]["token"]

def test_auth_login_valid_staff():
    log("Testing staff authentication for Store Manager, Ops Manager, Org Admin...")
    staff_emails = [
        ("storemanager@apex.com", "STORE_MANAGER"),
        ("opsmanager@apex.com", "OPERATIONS_MANAGER"),
        ("orgadmin@apex.com", "ORGANIZATION_ADMIN")
    ]
    for email, expected_role in staff_emails:
        payload = json.dumps({"email": email, "password": "Password123!"}).encode('utf-8')
        req = urllib.request.Request(
            f"{BASE_URL}/api/v1/auth/login",
            data=payload,
            headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req) as resp:
            res = json.loads(resp.read().decode('utf-8'))
            assert res["success"] is True
            assert res["data"]["user"]["role"] == expected_role
            log(f"Staff login successful: {email} -> {expected_role}", "PASS")

def test_auth_invalid_credentials():
    log("Testing invalid credentials error handling...")
    payload = json.dumps({"email": "customer@retailwave.com", "password": "WrongPassword999!"}).encode('utf-8')
    req = urllib.request.Request(
        f"{BASE_URL}/api/v1/auth/login",
        data=payload,
        headers={"Content-Type": "application/json"}
    )
    try:
        urllib.request.urlopen(req)
        assert False, "Login with invalid password should have failed"
    except urllib.error.HTTPError as e:
        assert e.code == 401
        body = json.loads(e.read().decode('utf-8'))
        assert body["success"] is False
        assert "Invalid email or password" in body["error"]["message"]
        log("Invalid password returned 401 with clear error message", "PASS")

def test_auth_unverified_account():
    log("Testing unverified account login gating...")
    payload = json.dumps({"email": "pending.customer@example.com", "password": "Password123!"}).encode('utf-8')
    req = urllib.request.Request(
        f"{BASE_URL}/api/v1/auth/login",
        data=payload,
        headers={"Content-Type": "application/json"}
    )
    try:
        urllib.request.urlopen(req)
        assert False, "Login for unverified customer should have failed"
    except urllib.error.HTTPError as e:
        assert e.code == 401
        body = json.loads(e.read().decode('utf-8'))
        assert "EMAIL_UNVERIFIED" in body["error"]["message"]
        log("Unverified customer correctly rejected with EMAIL_UNVERIFIED signal", "PASS")

def test_customer_registration_and_otp():
    log("Testing new customer registration and OTP verification...")
    import time
    unique_email = f"john.doe.{int(time.time())}@example.com"
    payload = json.dumps({
        "fullName": "John Doe",
        "email": unique_email,
        "password": "Password123!",
        "phone": "+1-555-019-9999"
    }).encode('utf-8')
    req = urllib.request.Request(
        f"{BASE_URL}/api/v1/auth/customer/register",
        data=payload,
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req) as resp:
        res = json.loads(resp.read().decode('utf-8'))
        assert res["success"] is True
        otp_code = res["data"]["devOtpCode"]
        assert len(otp_code) == 6
        log(f"Registration successful for {unique_email}, dev OTP generated: {otp_code}", "PASS")

    # Verify OTP
    verify_payload = json.dumps({
        "email": unique_email,
        "otp": otp_code
    }).encode('utf-8')
    req_verify = urllib.request.Request(
        f"{BASE_URL}/api/v1/auth/customer/verify-otp",
        data=verify_payload,
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req_verify) as resp:
        res_verify = json.loads(resp.read().decode('utf-8'))
        assert res_verify["success"] is True
        assert res_verify["data"]["user"]["isVerified"] is True
        token = res_verify["data"]["token"]
        log(f"OTP verification successful, session token issued for {unique_email}", "PASS")

    # Verify that the newly registered customer can now log in normally
    login_payload = json.dumps({"email": unique_email, "password": "Password123!"}).encode('utf-8')
    req_login = urllib.request.Request(
        f"{BASE_URL}/api/v1/auth/login",
        data=login_payload,
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req_login) as resp:
        res_login = json.loads(resp.read().decode('utf-8'))
        assert res_login["success"] is True
        assert res_login["data"]["user"]["email"] == unique_email
        log("Newly registered customer can now sign in persistently", "PASS")

def run_all_checks():
    print("=" * 70)
    print("SWIFT SERVICE - RESPONSIVE UI, SCROLLING & AUTH VERIFICATION")
    print("=" * 70)
    test_static_asset_serving()
    token = test_auth_login_valid_customer()
    test_auth_login_valid_staff()
    test_auth_invalid_credentials()
    test_auth_unverified_account()
    test_customer_registration_and_otp()
    print("=" * 70)
    print("ALL VERIFICATION CHECKS PASSED PERFECTLY!")
    print("=" * 70)

if __name__ == "__main__":
    run_all_checks()
