"""
Test script for Incident Responder API
Run this after starting the server: uvicorn main:app --reload
"""
import requests
import json
import time

BASE_URL = "http://localhost:8000"


def print_response(title, response):
    """Pretty print API response"""
    print("\n" + "="*60)
    print(title)
    print("="*60)
    print(f"Status Code: {response.status_code}")
    print(f"Response:")
    print(json.dumps(response.json(), indent=2))


def test_1_new_incident():
    """Test 1: Report a new Lambda timeout incident"""
    print("\n🔵 TEST 1: NEW INCIDENT (Lambda Timeout)")
    
    payload = {
        "log": "Lambda function timeout after 30 seconds. Function: payment-processor. Error: Task timed out after 30.00 seconds",
        "service": "payment-service"
    }
    
    response = requests.post(f"{BASE_URL}/incident", json=payload)
    print_response("NEW INCIDENT", response)
    
    result = response.json()
    return result.get("incident_id")


def test_2_existing_incident():
    """Test 2: Report the same incident again (should be deduplicated)"""
    print("\n🟡 TEST 2: EXISTING INCIDENT (Same Lambda Timeout)")
    
    time.sleep(2)  # Wait a bit
    
    payload = {
        "log": "Lambda timeout after 30s. Function: payment-processor. Task timed out",
        "service": "payment-service"
    }
    
    response = requests.post(f"{BASE_URL}/incident", json=payload)
    print_response("EXISTING INCIDENT (Should add comment to S3)", response)


def test_3_resolve_incident(incident_id):
    """Test 3: Resolve the incident"""
    print("\n🟢 TEST 3: RESOLVE INCIDENT")
    
    time.sleep(2)
    
    payload = {
        "incident_id": incident_id,
        "resolution": "Increased Lambda timeout to 60s and optimized database query. Issue resolved.",
        "resolved_by": "john@company.com"
    }
    
    response = requests.post(f"{BASE_URL}/resolve", json=payload)
    print_response("RESOLVE INCIDENT", response)


def test_4_regression():
    """Test 4: Report the same incident after resolution (regression)"""
    print("\n🔴 TEST 4: REGRESSION (Same incident after resolution)")
    
    time.sleep(2)
    
    payload = {
        "log": "Lambda function timeout after 30 seconds. Function: payment-processor. Error: Task timed out after 30.00 seconds",
        "service": "payment-service"
    }
    
    response = requests.post(f"{BASE_URL}/incident", json=payload)
    print_response("REGRESSION (Should create new incident with HIGH severity)", response)


def test_5_different_incident():
    """Test 5: Report a completely different incident"""
    print("\n🔵 TEST 5: DIFFERENT INCIDENT (DynamoDB Throttling)")
    
    time.sleep(2)
    
    payload = {
        "log": "DynamoDB throttling exception. Table: orders. ProvisionedThroughputExceededException. Read capacity exceeded.",
        "service": "order-service"
    }
    
    response = requests.post(f"{BASE_URL}/incident", json=payload)
    print_response("DIFFERENT INCIDENT", response)


def test_6_no_runbook_match():
    """Test 6: Report incident with no matching runbook"""
    print("\n🔵 TEST 6: NO RUNBOOK MATCH (Custom Error)")
    
    time.sleep(2)
    
    payload = {
        "log": "Custom application error: User authentication failed due to invalid JWT token signature",
        "service": "auth-service"
    }
    
    response = requests.post(f"{BASE_URL}/incident", json=payload)
    print_response("NO RUNBOOK MATCH", response)


def test_7_list_incidents():
    """Test 7: List all incidents"""
    print("\n📋 TEST 7: LIST ALL INCIDENTS")
    
    time.sleep(1)
    
    response = requests.get(f"{BASE_URL}/incidents")
    print_response("LIST ALL INCIDENTS", response)


def test_8_list_open_incidents():
    """Test 8: List only OPEN incidents"""
    print("\n📋 TEST 8: LIST OPEN INCIDENTS")
    
    response = requests.get(f"{BASE_URL}/incidents?status=OPEN")
    print_response("LIST OPEN INCIDENTS", response)


def test_9_get_incident_details(incident_id):
    """Test 9: Get specific incident details"""
    print("\n📄 TEST 9: GET INCIDENT DETAILS")
    
    response = requests.get(f"{BASE_URL}/incidents/{incident_id}")
    print_response(f"GET INCIDENT {incident_id}", response)


if __name__ == "__main__":
    print("\n" + "="*60)
    print("INCIDENT RESPONDER API - TEST SUITE")
    print("="*60)
    print("\nMake sure the server is running:")
    print("  uvicorn main:app --reload")
    print("\nWaiting 3 seconds...")
    time.sleep(3)
    
    try:
        # Check if server is running
        response = requests.get(f"{BASE_URL}/health")
        if response.status_code != 200:
            print("❌ Server is not responding")
            exit(1)
        
        print("✅ Server is running\n")
        
        # Run tests
        incident_id = test_1_new_incident()
        test_2_existing_incident()
        
        if incident_id:
            test_3_resolve_incident(incident_id)
        
        test_4_regression()
        test_5_different_incident()
        test_6_no_runbook_match()
        test_7_list_incidents()
        test_8_list_open_incidents()
        
        if incident_id:
            test_9_get_incident_details(incident_id)
        
        print("\n" + "="*60)
        print("✅ ALL TESTS COMPLETE")
        print("="*60)
        print("\nKey Observations:")
        print("1. New incidents: Created in S3 + Pinecone")
        print("2. Existing incidents: Comment added to S3 ticket")
        print("3. Resolved incidents: Status updated in S3")
        print("4. Regressions: New incident created with HIGH severity")
        print("5. Runbook matching: Similarity > 0.7 = matched")
        print("\nCheck your S3 bucket for ticket files!")
        
    except requests.exceptions.ConnectionError:
        print("\n❌ ERROR: Could not connect to server")
        print("Please start the server: uvicorn main:app --reload")
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
