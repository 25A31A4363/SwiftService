import urllib.request
import json
import sys
import time

base = 'http://127.0.0.1:8000'

def test_live_workflow():
    print("Beginning Live E2E Verification against http://127.0.0.1:8000 ...\n")
    unique_email = f"alice.test.{int(time.time())}@example.com"

    # 1. Test Static Landing Page
    req = urllib.request.urlopen(f'{base}/')
    print('1. GET / -> Status:', req.status)
    assert req.status == 200

    # 2. Test Public Tracking
    req = urllib.request.urlopen(f'{base}/api/v1/complaints/track/REF-2026-A8K92')
    res = json.loads(req.read().decode())['data']
    print(f"2. Public Tracking -> Ref: {res['referenceNumber']} | Status: {res['status']} | Timeline steps: {len(res['timeline'])}")
    assert res['referenceNumber'] == 'REF-2026-A8K92'
    assert res['status'] == 'IN_PROGRESS'

    # 3. Test Customer Registration + OTP
    reg_payload = json.dumps({
        'fullName': 'Alice Wonderland',
        'email': unique_email,
        'password': 'Password123!',
        'phone': '+1-555-0199'
    }).encode()
    req = urllib.request.Request(f'{base}/api/v1/auth/customer/register', data=reg_payload, headers={'Content-Type': 'application/json'})
    res = json.loads(urllib.request.urlopen(req).read().decode())['data']
    print(f"3. Customer Register -> Email: {res['email']} | Verification Required: {res['isVerified'] is False}")
    dev_otp = res.get('devOtpCode')

    # 4. Verify OTP
    otp_payload = json.dumps({'email': unique_email, 'otp': dev_otp}).encode()
    req = urllib.request.Request(f'{base}/api/v1/auth/customer/verify-otp', data=otp_payload, headers={'Content-Type': 'application/json'})
    res = json.loads(urllib.request.urlopen(req).read().decode())['data']
    print(f"4. OTP Verified -> isVerified: {res['user']['isVerified']} | Token generated: {bool(res['token'])}")
    cust_token = res['token']

    # 5. Customer Submits Complaint
    cmp_payload = json.dumps({
        'category': 'Returns and Refunds',
        'subject': 'Unprocessed refund for returned vacuum cleaner',
        'description': 'Returned vacuum cleaner at Seattle store 5 days ago with receipt. Refund not yet credited to credit card.',
        'orderNumber': 'ORD-99211'
    }).encode()
    req = urllib.request.Request(f'{base}/api/v1/complaints', data=cmp_payload, headers={'Content-Type': 'application/json', 'Authorization': f'Bearer {cust_token}'})
    new_cmp = json.loads(urllib.request.urlopen(req).read().decode())['data']
    ref_num = new_cmp['referenceNumber']
    cmp_id = new_cmp['id']
    print(f"5. Customer Complaint Created -> Ref: {ref_num} | Status: {new_cmp['status']}")
    assert ref_num.startswith('REF-2026-')

    # 6. Customer Reads History
    req = urllib.request.Request(f'{base}/api/v1/complaints/my', headers={'Authorization': f'Bearer {cust_token}'})
    my_list = json.loads(urllib.request.urlopen(req).read().decode())['data']
    print(f"6. Customer Complaint History Count -> {len(my_list)}")
    assert len(my_list) == 1

    # 7. Staff Login & Review
    staff_login = json.dumps({'email': 'storemanager@apex.com', 'password': 'Password123!'}).encode()
    req = urllib.request.Request(f'{base}/api/v1/auth/login', data=staff_login, headers={'Content-Type': 'application/json'})
    staff_auth = json.loads(urllib.request.urlopen(req).read().decode())['data']
    staff_token = staff_auth['token']
    print(f"7. Staff Login -> Role: {staff_auth['user']['role']}")

    # 8. Staff Views All Complaints
    req = urllib.request.Request(f'{base}/api/v1/complaints', headers={'Authorization': f'Bearer {staff_token}'})
    staff_res = json.loads(urllib.request.urlopen(req).read().decode())['data']
    staff_list = staff_res['items']
    print(f"8. Staff Views Complaints -> Total Complaints: {staff_res['total']}")
    assert any(c['referenceNumber'] == ref_num for c in staff_list)

    # 9. Staff Updates Complaint Status to IN_PROGRESS
    update_payload = json.dumps({
        'status': 'IN_PROGRESS',
        'assignedTeamId': 'team-hvac-pnw',
        'investigationNotes': 'Finance desk contacted regarding refund transaction ref #ORD-99211.',
        'resolutionSummary': 'Refund processed manually by store accounting. Expected in 2 business days.'
    }).encode()
    req = urllib.request.Request(f'{base}/api/v1/complaints/{cmp_id}/status', data=update_payload, headers={'Content-Type': 'application/json', 'Authorization': f'Bearer {staff_token}'}, method='PATCH')
    updated_cmp = json.loads(urllib.request.urlopen(req).read().decode())['data']
    print(f"9. Staff Status Update -> Status: {updated_cmp['status']} | Assigned Team: {updated_cmp['assignedTeamName']}")
    assert updated_cmp['status'] == 'IN_PROGRESS'

    # 10. Public / Customer Live Tracking Re-Check
    req = urllib.request.urlopen(f'{base}/api/v1/complaints/track/{ref_num}')
    track_res = json.loads(req.read().decode())['data']
    print(f"10. Live Public Tracking Re-Check -> Status: {track_res['status']} | Resolution Note: {track_res['resolutionSummary']}")
    assert track_res['status'] == 'IN_PROGRESS'
    assert track_res['resolutionSummary'] is not None

    print("\n=======================================================")
    print("[OK] SUCCESS: 10/10 COMPLETE END-TO-END WORKFLOW VERIFIED!")
    print("=======================================================")

if __name__ == '__main__':
    test_live_workflow()
