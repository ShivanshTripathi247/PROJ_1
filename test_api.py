#!/usr/bin/env python3
import requests
import json

def test_api():
    base_url = "http://localhost:5000"
    
    print("🧪 Testing API endpoints...")
    
    # Test basic status
    try:
        response = requests.get(f"{base_url}/")
        print(f"✅ Root endpoint: {response.status_code}")
        print(f"   Response: {response.json()}")
    except Exception as e:
        print(f"❌ Root endpoint failed: {e}")
    
    # Test API status
    try:
        response = requests.get(f"{base_url}/api/status")
        print(f"✅ Status endpoint: {response.status_code}")
        print(f"   Response: {response.json()}")
    except Exception as e:
        print(f"❌ Status endpoint failed: {e}")
    
    # Test generate report
    try:
        response = requests.get(f"{base_url}/api/generate-report")
        print(f"✅ Generate report endpoint: {response.status_code}")
        if response.status_code == 200:
            print("   Report generated successfully!")
        else:
            print(f"   Error: {response.text}")
    except Exception as e:
        print(f"❌ Generate report endpoint failed: {e}")

if __name__ == "__main__":
    test_api()
