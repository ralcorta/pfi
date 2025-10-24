"""
Test client for the sensor application.
"""
import requests
import json
import time
from typing import Dict, Any

API_BASE_URL = "http://localhost:8080"

def test_health_endpoint():
    """Test the health endpoint"""
    print("🔍 Testing health endpoint...")
    
    try:
        response = requests.get(f"{API_BASE_URL}/healthz")
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Health check passed")
            print(f"   Status: {data.get('status')}")
            print(f"   UDP Port: {data.get('udp_port')}")
            print(f"   HTTP Port: {data.get('http_port')}")
            print(f"   Queue Size: {data.get('queue_size')}")
            print(f"   Stats: {data.get('stats')}")
            return True
        else:
            print(f"❌ Health check failed: {response.text}")
            return False
            
    except requests.exceptions.ConnectionError:
        print("❌ Could not connect to API. Make sure the server is running on localhost:8080")
        return False
    except Exception as e:
        print(f"❌ Error testing health: {e}")
        return False

def test_stats_endpoint():
    """Test the stats endpoint"""
    print("\n🔍 Testing stats endpoint...")
    
    try:
        response = requests.get(f"{API_BASE_URL}/stats")
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Stats retrieved")
            print(f"   Queue Size: {data.get('queue_size')}")
            print(f"   Active Flows: {data.get('active_flows')}")
            print(f"   Stats: {data.get('stats')}")
            return True
        else:
            print(f"❌ Stats request failed: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Error testing stats: {e}")
        return False

def test_detections_endpoint():
    """Test the detections endpoint"""
    print("\n🔍 Testing detections endpoint...")
    
    try:
        # Test with a sample tenant ID
        tenant_id = "TENANT#100"
        start_ts = int(time.time() * 1000) - 3600000  # 1 hour ago
        end_ts = int(time.time() * 1000)  # now
        
        response = requests.get(
            f"{API_BASE_URL}/detections/{tenant_id}",
            params={
                "start_ts": start_ts,
                "end_ts": end_ts,
                "limit": 10
            }
        )
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Detections retrieved")
            print(f"   Count: {data.get('count')}")
            print(f"   Items: {len(data.get('items', []))}")
            if data.get('next_cursor'):
                print(f"   Has next cursor: Yes")
            return True
        else:
            print(f"❌ Detections request failed: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Error testing detections: {e}")
        return False

def main():
    """Run all tests"""
    print("🚀 Starting sensor application tests...")
    print(f"API Base URL: {API_BASE_URL}")
    
    tests = [
        test_health_endpoint,
        test_stats_endpoint,
        test_detections_endpoint
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
    
    print(f"\n📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("✅ All tests passed!")
    else:
        print("❌ Some tests failed!")

if __name__ == "__main__":
    main()
