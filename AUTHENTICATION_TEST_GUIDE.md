# 🔐 WFAP Broker Authentication Test Guide

## Overview
The `test_authentication.py` script provides comprehensive security testing for the WFAP broker's authentication system. It simulates various rogue agent scenarios to verify that the broker properly rejects unauthorized requests while accepting legitimate ones.

## Prerequisites
1. **Broker Running**: Make sure the broker agent is running on port 8000
   ```bash
   cd wfap-solution/broker_agent
   python3 __main__.py --port 8000
   ```

2. **Dependencies**: Ensure all required packages are installed
   ```bash
   pip install httpx jwt
   ```

## Running the Tests

### Basic Usage
```bash
cd wfap-solution
python3 test_authentication.py
```

### Make Executable (Optional)
```bash
chmod +x test_authentication.py
./test_authentication.py
```

## Test Scenarios

The script tests 6 different authentication scenarios:

### ✅ Security Tests (Should Fail)
1. **Rogue Agent - No Authentication**
   - Tests: Request without any authentication
   - Expected: ❌ REJECTED

2. **Rogue Agent - Invalid Token**
   - Tests: Request with malformed/invalid JWT token
   - Expected: ❌ REJECTED

3. **Rogue Agent - Expired Token**
   - Tests: Request with expired JWT token
   - Expected: ❌ REJECTED

4. **Rogue Agent - Valid Token, Wrong Client ID**
   - Tests: Valid token but claiming to be different client
   - Expected: ❌ REJECTED

5. **Rogue Agent - Malformed Authentication Message**
   - Tests: Missing required authentication fields
   - Expected: ❌ REJECTED

### ✅ Legitimate Test (Should Pass)
6. **Legitimate Agent - Valid Authentication**
   - Tests: Proper authentication with valid token and client_id
   - Expected: ✅ ACCEPTED

## Sample Output

```
🔐 WFAP Broker Authentication Security Tests
============================================================
🎯 Target Broker: http://localhost:8000
🕐 Test Started: 2025-09-21T22:37:16.164018

🧪 Test 1: Rogue Agent - No Authentication
==================================================
✅ PASS Rogue Agent No Auth
   📋 Details: Successfully rejected unauthorized request

🧪 Test 2: Rogue Agent - Invalid Token
==================================================
✅ PASS Rogue Agent Invalid Token
   📋 Details: Successfully rejected request with invalid token

[... more tests ...]

📊 TEST SUMMARY
============================================================
📈 Total Tests: 6
✅ Passed: 6
❌ Failed: 0
📊 Success Rate: 100.0%

🔐 SECURITY STATUS:
   ✅ ALL SECURITY TESTS PASSED - Broker is secure!
```

## Understanding Results

### ✅ PASS
- **Security Tests**: Rogue agent was properly rejected
- **Legitimate Test**: Valid request was accepted

### ❌ FAIL
- **Security Tests**: Rogue agent was incorrectly accepted (SECURITY ISSUE!)
- **Legitimate Test**: Valid request was incorrectly rejected

## Troubleshooting

### Broker Not Running
```
❌ Error: Broker is not running or not accessible
```
**Solution**: Start the broker agent first
```bash
cd wfap-solution/broker_agent
python3 __main__.py --port 8000
```

### Import Errors
```
❌ Error: auth_config.py not found
```
**Solution**: Make sure you're running from the `wfap-solution` directory

### Connection Timeouts
```
❌ Exception occurred: All connection attempts failed
```
**Solution**: Check that the broker is running on the correct port (8000)

## Security Validation

A successful test run should show:
- **100% Pass Rate**: All 6 tests pass
- **All Rogue Tests Rejected**: Unauthorized requests are blocked
- **Legitimate Test Accepted**: Valid requests are processed

If any rogue agent tests fail, this indicates a **security vulnerability** that needs immediate attention.

## Customization

You can modify the test script to:
- Test different broker URLs
- Add additional rogue agent scenarios
- Test with different client credentials
- Modify timeout values

## Integration with CI/CD

This script can be integrated into automated testing pipelines:

```bash
# In CI/CD pipeline
python3 test_authentication.py
if [ $? -eq 0 ]; then
    echo "✅ Authentication security tests passed"
else
    echo "❌ Authentication security tests failed"
    exit 1
fi
```

## Security Best Practices

1. **Run Tests Regularly**: Execute before deployments
2. **Monitor Results**: Watch for any test failures
3. **Update Tests**: Add new scenarios as threats evolve
4. **Document Failures**: Investigate and fix any security issues immediately

---

**Note**: This test script validates the broker's authentication implementation. For end-to-end testing with all agents, use the main WFAP testing procedures.
