"""
Test JWT Authentication
"""
import requests
import json

BASE_URL = "http://localhost:8000"


def test_login():
    """Test 1: Login and get JWT token"""
    print("\n" + "="*60)
    print("TEST 1: LOGIN")
    print("="*60)
    
    payload = {
        "username": "admin",
        "password": "secret"
    }
    
    response = requests.post(f"{BASE_URL}/login", json=payload)
    
    print(f"Status Code: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    
    if response.status_code == 200:
        token = response.json()["access_token"]
        print(f"\n✅ Login successful!")
        print(f"Token: {token[:50]}...")
        return token
    else:
        print("\n❌ Login failed!")
        return None


def test_get_current_user(token):
    """Test 2: Get current user info"""
    print("\n" + "="*60)
    print("TEST 2: GET CURRENT USER")
    print("="*60)
    
    headers = {
        "Authorization": f"Bearer {token}"
    }
    
    response = requests.get(f"{BASE_URL}/me", headers=headers)
    
    print(f"Status Code: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    
    if response.status_code == 200:
        print("\n✅ Got user info!")
    else:
        print("\n❌ Failed to get user info!")


def test_protected_endpoint_without_token():
    """Test 3: Try to access protected endpoint without token"""
    print("\n" + "="*60)
    print("TEST 3: ACCESS PROTECTED ENDPOINT WITHOUT TOKEN")
    print("="*60)
    
    payload = {
        "log": "Lambda timeout",
        "service": "test"
    }
    
    response = requests.post(f"{BASE_URL}/incident", json=payload)
    
    print(f"Status Code: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    
    if response.status_code == 401:
        print("\n✅ Correctly rejected (401 Unauthorized)")
    else:
        print("\n❌ Should have been rejected!")


def test_protected_endpoint_with_token(token):
    """Test 4: Access protected endpoint with valid token"""
    print("\n" + "="*60)
    print("TEST 4: ACCESS PROTECTED ENDPOINT WITH TOKEN")
    print("="*60)
    
    headers = {
        "Authorization": f"Bearer {token}"
    }
    
    payload = {
        "log": "Lambda function timeout after 30 seconds. Function: payment-processor",
        "service": "payment-service"
    }
    
    response = requests.post(f"{BASE_URL}/incident", json=payload, headers=headers)
    
    print(f"Status Code: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    
    if response.status_code == 200:
        print("\n✅ Successfully accessed protected endpoint!")
        return response.json().get("incident_id")
    else:
        print("\n❌ Failed to access protected endpoint!")
        return None


def test_invalid_token():
    """Test 5: Try with invalid token"""
    print("\n" + "="*60)
    print("TEST 5: ACCESS WITH INVALID TOKEN")
    print("="*60)
    
    headers = {
        "Authorization": "Bearer invalid-token-12345"
    }
    
    response = requests.get(f"{BASE_URL}/me", headers=headers)
    
    print(f"Status Code: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    
    if response.status_code == 401:
        print("\n✅ Correctly rejected invalid token")
    else:
        print("\n❌ Should have rejected invalid token!")


def test_wrong_password():
    """Test 6: Try to login with wrong password"""
    print("\n" + "="*60)
    print("TEST 6: LOGIN WITH WRONG PASSWORD")
    print("="*60)
    
    payload = {
        "username": "admin",
        "password": "wrongpassword"
    }
    
    response = requests.post(f"{BASE_URL}/login", json=payload)
    
    print(f"Status Code: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    
    if response.status_code == 401:
        print("\n✅ Correctly rejected wrong password")
    else:
        print("\n❌ Should have rejected wrong password!")


if __name__ == "__main__":
    print("\n" + "="*60)
    print("JWT AUTHENTICATION TEST SUITE")
    print("="*60)
    print("\nDefault credentials:")
    print("  Username: admin")
    print("  Password: secret")
    print("\nMake sure the server is running:")
    print("  uvicorn main:app --reload")
    
    try:
        # Test 1: Login
        token = test_login()
        
        if token:
            # Test 2: Get current user
            test_get_current_user(token)
            
            # Test 3: Try without token
            test_protected_endpoint_without_token()
            
            # Test 4: Try with valid token
            test_protected_endpoint_with_token(token)
            
            # Test 5: Try with invalid token
            test_invalid_token()
            
            # Test 6: Try wrong password
            test_wrong_password()
        
        print("\n" + "="*60)
        print("✅ ALL TESTS COMPLETE")
        print("="*60)
        print("\nKey Learnings:")
        print("1. JWT tokens are obtained via /login endpoint")
        print("2. Tokens must be included in Authorization header: Bearer <token>")
        print("3. Protected endpoints reject requests without valid token")
        print("4. Tokens expire after 1 hour (configurable)")
        print("5. Invalid tokens are rejected with 401 Unauthorized")
        
    except requests.exceptions.ConnectionError:
        print("\n❌ ERROR: Could not connect to server")
        print("Please start the server: uvicorn main:app --reload")
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
