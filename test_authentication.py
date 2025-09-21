#!/usr/bin/env python3
"""
Authentication Test Script for WFAP Broker
Tests various rogue agent scenarios to verify authentication security
"""

import sys
import os
import json
import asyncio
import httpx
from datetime import datetime

# Add current directory to path
sys.path.append('.')

# Import authentication configuration
try:
    from auth_config import auth_manager, AUTH_CONFIG
except ImportError:
    print("❌ Error: auth_config.py not found")
    sys.exit(1)

class AuthenticationTester:
    def __init__(self, broker_url="http://localhost:8000"):
        self.broker_url = broker_url
        self.test_results = []
        
    def log_test(self, test_name: str, success: bool, details: str):
        """Log test results"""
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {test_name}")
        print(f"   📋 Details: {details}")
        print()
        
        self.test_results.append({
            "test_name": test_name,
            "success": success,
            "details": details,
            "timestamp": datetime.now().isoformat()
        })
    
    async def test_rogue_agent_no_auth(self):
        """Test 1: Rogue agent with no authentication"""
        print("🧪 Test 1: Rogue Agent - No Authentication")
        print("=" * 50)
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.broker_url,
                    json={
                        "jsonrpc": "2.0",
                        "id": "rogue-no-auth",
                        "method": "message/send",
                        "params": {
                            "id": "rogue-task",
                            "message": {
                                "messageId": "rogue-msg",
                                "role": "user",
                                "parts": [{
                                    "type": "text",
                                    "text": "I am a rogue agent trying to access the system without authentication"
                                }]
                            }
                        }
                    },
                    timeout=10.0
                )
                
                # Should be rejected
                if response.status_code == 200:
                    result = response.json()
                    if "result" in result and "artifacts" in result["result"]:
                        for artifact in result["result"]["artifacts"]:
                            if artifact.get("name") == "auth_error":
                                self.log_test(
                                    "Rogue Agent No Auth",
                                    True,
                                    "Successfully rejected unauthorized request"
                                )
                                return
                
                self.log_test(
                    "Rogue Agent No Auth",
                    False,
                    f"Unexpected response: {response.text}"
                )
                
        except Exception as e:
            self.log_test(
                "Rogue Agent No Auth",
                False,
                f"Exception occurred: {str(e)}"
            )
    
    async def test_rogue_agent_invalid_token(self):
        """Test 2: Rogue agent with invalid token"""
        print("🧪 Test 2: Rogue Agent - Invalid Token")
        print("=" * 50)
        
        try:
            # Create message with invalid token
            invalid_message = {
                "auth_token": "Bearer invalid-token-12345",
                "client_id": "rogue-agent",
                "message_type": "credit_intent",
                "data": {
                    "company_name": "Rogue Corp",
                    "requested_amount": 1000000
                },
                "timestamp": datetime.now().isoformat()
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.broker_url,
                    json={
                        "jsonrpc": "2.0",
                        "id": "rogue-invalid-token",
                        "method": "message/send",
                        "params": {
                            "id": "rogue-task",
                            "message": {
                                "messageId": "rogue-msg",
                                "role": "user",
                                "parts": [{
                                    "type": "text",
                                    "text": json.dumps(invalid_message)
                                }]
                            }
                        }
                    },
                    timeout=10.0
                )
                
                # Should be rejected
                if response.status_code == 200:
                    result = response.json()
                    if "result" in result and "artifacts" in result["result"]:
                        for artifact in result["result"]["artifacts"]:
                            if artifact.get("name") == "auth_error":
                                self.log_test(
                                    "Rogue Agent Invalid Token",
                                    True,
                                    "Successfully rejected request with invalid token"
                                )
                                return
                
                self.log_test(
                    "Rogue Agent Invalid Token",
                    False,
                    f"Unexpected response: {response.text}"
                )
                
        except Exception as e:
            self.log_test(
                "Rogue Agent Invalid Token",
                False,
                f"Exception occurred: {str(e)}"
            )
    
    async def test_rogue_agent_expired_token(self):
        """Test 3: Rogue agent with expired token"""
        print("🧪 Test 3: Rogue Agent - Expired Token")
        print("=" * 50)
        
        try:
            # Create an expired token (expired 1 hour ago)
            expired_payload = {
                "client_id": "rogue-agent",
                "iat": datetime.utcnow().timestamp() - 7200,  # 2 hours ago
                "exp": datetime.utcnow().timestamp() - 3600,  # 1 hour ago
                "scope": "wfap:credit",
                "iss": "wfap-broker",
                "aud": "wfap-agents"
            }
            
            # Generate expired token
            import jwt
            expired_token = jwt.encode(expired_payload, auth_manager.jwt_secret, algorithm="HS256")
            
            expired_message = {
                "auth_token": f"Bearer {expired_token}",
                "client_id": "rogue-agent",
                "message_type": "credit_intent",
                "data": {
                    "company_name": "Rogue Corp",
                    "requested_amount": 1000000
                },
                "timestamp": datetime.now().isoformat()
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.broker_url,
                    json={
                        "jsonrpc": "2.0",
                        "id": "rogue-expired-token",
                        "method": "message/send",
                        "params": {
                            "id": "rogue-task",
                            "message": {
                                "messageId": "rogue-msg",
                                "role": "user",
                                "parts": [{
                                    "type": "text",
                                    "text": json.dumps(expired_message)
                                }]
                            }
                        }
                    },
                    timeout=10.0
                )
                
                # Should be rejected
                if response.status_code == 200:
                    result = response.json()
                    if "result" in result and "artifacts" in result["result"]:
                        for artifact in result["result"]["artifacts"]:
                            if artifact.get("name") == "auth_error":
                                self.log_test(
                                    "Rogue Agent Expired Token",
                                    True,
                                    "Successfully rejected request with expired token"
                                )
                                return
                
                self.log_test(
                    "Rogue Agent Expired Token",
                    False,
                    f"Unexpected response: {response.text}"
                )
                
        except Exception as e:
            self.log_test(
                "Rogue Agent Expired Token",
                False,
                f"Exception occurred: {str(e)}"
            )
    
    async def test_rogue_agent_wrong_client_id(self):
        """Test 4: Rogue agent with valid token but wrong client_id"""
        print("🧪 Test 4: Rogue Agent - Valid Token, Wrong Client ID")
        print("=" * 50)
        
        try:
            # Get a valid token for company-agent
            company_token = auth_manager.generate_access_token("company-agent", "company-secret-456")
            if not company_token:
                self.log_test(
                    "Rogue Agent Wrong Client ID",
                    False,
                    "Failed to generate valid token for testing"
                )
                return
            
            # Use valid token but claim to be a different client
            wrong_client_message = {
                "auth_token": f"Bearer {company_token['access_token']}",
                "client_id": "rogue-agent",  # Wrong client ID
                "message_type": "credit_intent",
                "data": {
                    "company_name": "Rogue Corp",
                    "requested_amount": 1000000
                },
                "timestamp": datetime.now().isoformat()
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.broker_url,
                    json={
                        "jsonrpc": "2.0",
                        "id": "rogue-wrong-client",
                        "method": "message/send",
                        "params": {
                            "id": "rogue-task",
                            "message": {
                                "messageId": "rogue-msg",
                                "role": "user",
                                "parts": [{
                                    "type": "text",
                                    "text": json.dumps(wrong_client_message)
                                }]
                            }
                        }
                    },
                    timeout=10.0
                )
                
                # Should be rejected due to client_id mismatch
                if response.status_code == 200:
                    result = response.json()
                    if "result" in result and "artifacts" in result["result"]:
                        for artifact in result["result"]["artifacts"]:
                            if artifact.get("name") == "auth_error":
                                self.log_test(
                                    "Rogue Agent Wrong Client ID",
                                    True,
                                    "Successfully rejected request with client_id mismatch"
                                )
                                return
                
                self.log_test(
                    "Rogue Agent Wrong Client ID",
                    False,
                    f"Unexpected response: {response.text}"
                )
                
        except Exception as e:
            self.log_test(
                "Rogue Agent Wrong Client ID",
                False,
                f"Exception occurred: {str(e)}"
            )
    
    async def test_rogue_agent_malformed_message(self):
        """Test 5: Rogue agent with malformed authentication message"""
        print("🧪 Test 5: Rogue Agent - Malformed Authentication Message")
        print("=" * 50)
        
        try:
            # Create malformed message (missing required fields)
            malformed_message = {
                "auth_token": "Bearer some-token",
                # Missing client_id
                "message_type": "credit_intent",
                "data": {
                    "company_name": "Rogue Corp"
                }
                # Missing timestamp
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.broker_url,
                    json={
                        "jsonrpc": "2.0",
                        "id": "rogue-malformed",
                        "method": "message/send",
                        "params": {
                            "id": "rogue-task",
                            "message": {
                                "messageId": "rogue-msg",
                                "role": "user",
                                "parts": [{
                                    "type": "text",
                                    "text": json.dumps(malformed_message)
                                }]
                            }
                        }
                    },
                    timeout=10.0
                )
                
                # Should be rejected
                if response.status_code == 200:
                    result = response.json()
                    if "result" in result and "artifacts" in result["result"]:
                        for artifact in result["result"]["artifacts"]:
                            if artifact.get("name") == "auth_error":
                                self.log_test(
                                    "Rogue Agent Malformed Message",
                                    True,
                                    "Successfully rejected malformed authentication message"
                                )
                                return
                
                self.log_test(
                    "Rogue Agent Malformed Message",
                    False,
                    f"Unexpected response: {response.text}"
                )
                
        except Exception as e:
            self.log_test(
                "Rogue Agent Malformed Message",
                False,
                f"Exception occurred: {str(e)}"
            )
    
    async def test_legitimate_agent(self):
        """Test 6: Legitimate agent with valid authentication (should pass)"""
        print("🧪 Test 6: Legitimate Agent - Valid Authentication")
        print("=" * 50)
        
        try:
            # Get a valid token
            company_token = auth_manager.generate_access_token("company-agent", "company-secret-456")
            if not company_token:
                self.log_test(
                    "Legitimate Agent Valid Auth",
                    False,
                    "Failed to generate valid token"
                )
                return
            
            # Create valid authenticated message
            valid_message = {
                "auth_token": f"Bearer {company_token['access_token']}",
                "client_id": "company-agent",
                "message_type": "credit_intent",
                "data": {
                    "company_name": "TechCorp Inc",
                    "requested_amount": 2000000,
                    "purpose": "Equipment purchase"
                },
                "timestamp": datetime.now().isoformat()
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.broker_url,
                    json={
                        "jsonrpc": "2.0",
                        "id": "legitimate-agent",
                        "method": "message/send",
                        "params": {
                            "id": "legitimate-task",
                            "message": {
                                "messageId": "legitimate-msg",
                                "role": "user",
                                "parts": [{
                                    "type": "text",
                                    "text": json.dumps(valid_message)
                                }]
                            }
                        }
                    },
                    timeout=10.0
                )
                
                # Should be accepted
                if response.status_code == 200:
                    result = response.json()
                    if "result" in result and "artifacts" in result["result"]:
                        for artifact in result["result"]["artifacts"]:
                            if artifact.get("name") == "broker_result":
                                self.log_test(
                                    "Legitimate Agent Valid Auth",
                                    True,
                                    "Successfully processed legitimate authenticated request"
                                )
                                return
                
                self.log_test(
                    "Legitimate Agent Valid Auth",
                    False,
                    f"Unexpected response: {response.text}"
                )
                
        except Exception as e:
            self.log_test(
                "Legitimate Agent Valid Auth",
                False,
                f"Exception occurred: {str(e)}"
            )
    
    async def run_all_tests(self):
        """Run all authentication tests"""
        print("🔐 WFAP Broker Authentication Security Tests")
        print("=" * 60)
        print(f"🎯 Target Broker: {self.broker_url}")
        print(f"🕐 Test Started: {datetime.now().isoformat()}")
        print()
        
        # Run all tests
        await self.test_rogue_agent_no_auth()
        await self.test_rogue_agent_invalid_token()
        await self.test_rogue_agent_expired_token()
        await self.test_rogue_agent_wrong_client_id()
        await self.test_rogue_agent_malformed_message()
        await self.test_legitimate_agent()
        
        # Print summary
        self.print_summary()
    
    def print_summary(self):
        """Print test summary"""
        print("📊 TEST SUMMARY")
        print("=" * 60)
        
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results if result["success"])
        failed_tests = total_tests - passed_tests
        
        print(f"📈 Total Tests: {total_tests}")
        print(f"✅ Passed: {passed_tests}")
        print(f"❌ Failed: {failed_tests}")
        print(f"📊 Success Rate: {(passed_tests/total_tests)*100:.1f}%")
        print()
        
        if failed_tests > 0:
            print("❌ FAILED TESTS:")
            for result in self.test_results:
                if not result["success"]:
                    print(f"   • {result['test_name']}: {result['details']}")
            print()
        
        print("🔐 SECURITY STATUS:")
        if failed_tests == 0:
            print("   ✅ ALL SECURITY TESTS PASSED - Broker is secure!")
        else:
            print("   ⚠️  SOME SECURITY TESTS FAILED - Review authentication implementation")
        
        print(f"🕐 Test Completed: {datetime.now().isoformat()}")

async def main():
    """Main function"""
    print("🚀 Starting WFAP Broker Authentication Tests...")
    print()
    
    # Check if broker is running
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get("http://localhost:8000", timeout=5.0)
            print("✅ Broker is running and accessible")
    except Exception as e:
        print("❌ Error: Broker is not running or not accessible")
        print(f"   Details: {str(e)}")
        print()
        print("💡 Make sure to start the broker first:")
        print("   cd wfap-solution/broker_agent && python3 __main__.py --port 8000")
        return
    
    print()
    
    # Run tests
    tester = AuthenticationTester()
    await tester.run_all_tests()

if __name__ == "__main__":
    asyncio.run(main())
