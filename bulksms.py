#!/usr/bin/env python3
"""
BulkSMS Authentication Test Script
Run this to test your BulkSMS credentials independently.
"""

import httpx
import base64
import asyncio
import json

# Your credentials
USERNAME = "juniorflamebet"
PASSWORD = "Mauricesitwala@12!"
API_URL = "https://api.bulksms.com/v1/messages"

async def test_bulksms_auth():
    print("=" * 60)
    print("BulkSMS Authentication Test")
    print("=" * 60)
    
    print(f"Username: {USERNAME}")
    print(f"Password: {'*' * len(PASSWORD)}")
    print(f"API URL: {API_URL}")
    print()
    
    # Step 1: Encode credentials
    print("Step 1: Encoding credentials...")
    auth_string = f"{USERNAME}:{PASSWORD}"
    print(f"Auth string length: {len(auth_string)}")
    
    try:
        auth_bytes = auth_string.encode('utf-8')
        encoded_auth = base64.b64encode(auth_bytes).decode('ascii')
        print(f"Base64 encoded: {encoded_auth[:30]}...")
        print()
    except Exception as e:
        print(f"❌ Encoding failed: {e}")
        return
    
    # Step 2: Test with different approaches
    headers = {
        "Authorization": f"Basic {encoded_auth}",
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    
    async with httpx.AsyncClient() as client:
        print("Step 2: Testing authentication...")
        
        # Test 1: GET request (should return 405 Method Not Allowed if auth works)
        try:
            print("\nTest 1: GET request to test auth...")
            response = await client.get(API_URL, headers=headers, timeout=10)
            print(f"Status: {response.status_code}")
            print(f"Response: {response.text[:200]}...")
            
            if response.status_code == 401:
                print("❌ Authentication failed!")
                print("Possible issues:")
                print("1. Username or password incorrect")
                print("2. Account not activated")
                print("3. Account suspended")
                print("4. API access not enabled")
                return False
            elif response.status_code == 405:
                print("✅ Authentication successful (405 Method Not Allowed is expected)")
            else:
                print(f"✅ Authentication appears to work (got {response.status_code})")
                
        except Exception as e:
            print(f"❌ Request failed: {e}")
            return False
        
        # Test 2: POST with minimal payload
        print("\nTest 2: POST with test payload...")
        test_payload = {
            "to": ["+27798984117"],  # Your test number
            "body": "Test message from API",
            "encoding": "UNICODE"
        }
        
        try:
            response = await client.post(
                API_URL, 
                json=test_payload, 
                headers=headers, 
                timeout=10
            )
            print(f"Status: {response.status_code}")
            print(f"Response: {response.text}")
            
            if response.status_code == 401:
                print("❌ Still getting 401 - authentication definitely failing")
                return False
            elif response.status_code == 200 or response.status_code == 201:
                print("✅ SMS API call successful!")
                try:
                    data = response.json()
                    print(f"Response data: {json.dumps(data, indent=2)}")
                except:
                    pass
                return True
            else:
                print(f"ℹ️ Got status {response.status_code} - check response for details")
                return True
                
        except Exception as e:
            print(f"❌ POST request failed: {e}")
            return False

async def test_alternative_formats():
    """Test different credential formats in case there's an encoding issue"""
    print("\n" + "=" * 60)
    print("Testing Alternative Credential Formats")
    print("=" * 60)
    
    formats_to_test = [
        ("Standard", f"{USERNAME}:{PASSWORD}"),
        ("URL Encoded", f"{USERNAME.replace('@', '%40')}:{PASSWORD.replace('@', '%40')}"),
        ("Stripped", f"{USERNAME.strip()}:{PASSWORD.strip()}"),
    ]
    
    async with httpx.AsyncClient() as client:
        for format_name, auth_string in formats_to_test:
            print(f"\nTesting {format_name} format...")
            try:
                encoded = base64.b64encode(auth_string.encode('utf-8')).decode('ascii')
                headers = {
                    "Authorization": f"Basic {encoded}",
                    "Content-Type": "application/json"
                }
                
                response = await client.get(API_URL, headers=headers, timeout=5)
                print(f"  Status: {response.status_code}")
                
                if response.status_code != 401:
                    print(f"  ✅ {format_name} format works!")
                else:
                    print(f"  ❌ {format_name} format failed")
                    
            except Exception as e:
                print(f"  ❌ Error with {format_name}: {e}")

if __name__ == "__main__":
    print("Starting BulkSMS authentication tests...\n")
    
    async def run_all_tests():
        success = await test_bulksms_auth()
        if not success:
            await test_alternative_formats()
        
        print("\n" + "=" * 60)
        print("Test Summary")
        print("=" * 60)
        print("If you're still getting 401 errors, check:")
        print("1. Login to BulkSMS web interface to verify account is active")
        print("2. Check if API access is enabled in your account settings")
        print("3. Verify username/password by logging into the web interface")
        print("4. Check if your account has credits")
        print("5. Try generating a new password in BulkSMS settings")
    
    asyncio.run(run_all_tests())