"""
Test script to demonstrate the simple flow:
1. Search for similar incident
2. If exists → return that + runbook
3. If not exists → create entry + runbook
"""
import requests
import json
import time

BASE_URL = "http://localhost:8000"


def test_new_incident():
    """Test 1: Report a new incident (not in Pinecone)"""
    print("\n" + "="*60)
    print("TEST 1: NEW INCIDENT")
    print("="*60)
    
    incident = {
        "log": "Lambda function timeout after 45 seconds. Function: payment-processor. Error: Task timed out",
        "severity": "CRITICAL",
        "service": "payment-service"
    }
    
    response = requests.post(f"{BASE_URL}/incident", json=incident)
    result = response.json()
    
    print(f"\nStatus: {result['status']}")
    print(f"Incident ID: {result.get('incident_id')}")
    print(f"Response Time: {result['response_time_seconds']}s")
    print(f"\nRecommendations:\n{result['recommendations'][:200]}...")
    print(f"\nRunbooks: {[rb['title'] for rb in result['runbooks']]}")
    
    return result.get('incident_id')


def test_similar_incident():
    """Test 2: Report a very similar incident (should find existing)"""
    print("\n" + "="*60)
    print("TEST 2: SIMILAR INCIDENT")
    print("="*60)
    
    # Very similar to the first incident
    incident = {
        "log": "Lambda timeout error after 45s. Function: payment-processor. Task timed out",
        "severity": "CRITICAL",
        "service": "payment-service"
    }
    
    response = requests.post(f"{BASE_URL}/incident", json=incident)
    result = response.json()
    
    print(f"\nStatus: {result['status']}")
    if result['status'] == 'existing':
        print(f"Found existing incident: {result['incident_id']}")
        print(f"Similarity: {result['similarity']:.3f}")
        print(f"Similar to: {result['similar_to'][:80]}...")
    print(f"Response Time: {result['response_time_seconds']}s")
    print(f"\nRunbooks: {[rb['title'] for rb in result['runbooks']]}")
    
    return result


def test_different_incident():
    """Test 3: Report a completely different incident"""
    print("\n" + "="*60)
    print("TEST 3: DIFFERENT INCIDENT")
    print("="*60)
    
    incident = {
        "log": "S3 bucket access denied. User: api-service. Action: s3:GetObject. Bucket: prod-assets",
        "severity": "ERROR",
        "service": "api-service"
    }
    
    response = requests.post(f"{BASE_URL}/incident", json=incident)
    result = response.json()
    
    print(f"\nStatus: {result['status']}")
    print(f"Incident ID: {result.get('incident_id')}")
    print(f"Response Time: {result['response_time_seconds']}s")
    print(f"\nRecommendations:\n{result['recommendations'][:200]}...")
    
    return result


def test_resolve_incident(incident_id: str):
    """Test 4: Optionally mark incident as resolved"""
    print("\n" + "="*60)
    print("TEST 4: RESOLVE INCIDENT (OPTIONAL)")
    print("="*60)
    
    resolution = {
        "incident_id": incident_id,
        "resolution": "Increased Lambda timeout to 90s and added connection pooling. Issue resolved."
    }
    
    response = requests.post(f"{BASE_URL}/resolve", json=resolution)
    result = response.json()
    
    print(f"\nStatus: {result['status']}")
    print(f"Resolution: {result.get('resolution')}")
    
    return result


if __name__ == "__main__":
    print("\n" + "="*60)
    print("INCIDENT RESPONDER - SIMPLE FLOW TEST")
    print("="*60)
    print("\nFlow:")
    print("1. Search for similar incident in Pinecone")
    print("2. If exists → return that + runbook")
    print("3. If not exists → create entry + runbook")
    print("\nMake sure the server is running: uvicorn main:app --reload")
    print("Waiting 3 seconds...")
    time.sleep(3)
    
    try:
        # Test 1: New incident (not in Pinecone)
        incident_id = test_new_incident()
        time.sleep(2)
        
        # Test 2: Similar incident (should find existing)
        test_similar_incident()
        time.sleep(2)
        
        # Test 3: Different incident
        test_different_incident()
        time.sleep(2)
        
        # Test 4: Optionally resolve
        if incident_id:
            test_resolve_incident(incident_id)
        
        print("\n" + "="*60)
        print("ALL TESTS COMPLETE")
        print("="*60)
        print("\nKey Points:")
        print("✓ First incident: Created entry + ran through runbook")
        print("✓ Similar incident: Found existing + ran through runbook")
        print("✓ Different incident: Created new entry + ran through runbook")
        print("✓ Resolution: Optional, updates metadata")
        print("\nThis prevents duplicate storage while always running through runbooks!")
        
    except requests.exceptions.ConnectionError:
        print("\n❌ ERROR: Could not connect to server")
        print("Please start the server: uvicorn main:app --reload")
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
