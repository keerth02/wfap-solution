# HMAC Signature Validation Logging Guide

## Overview
This guide documents the comprehensive logging system implemented for HMAC signature validation in the WFAP solution. All signature operations are logged with detailed information for debugging, auditing, and security monitoring.

## 🔐 Signature Generation Logging

### Location: `signature_utils.py` - `generate_signature()`

**Example Output:**
```
🔐 SIGNATURE GENERATION:
   📝 Message Type: credit_intent
   🔑 Secret Key Length: 18 characters
   📏 Message Length: 185 characters
   ✅ Generated Signature: IBFA83CVS2wQHIn+...50F2KQE=
```

**Information Logged:**
- Message type being signed
- Secret key length (for validation)
- Message content length
- Generated signature (truncated for security)

## 🔍 Signature Validation Logging

### Location: `signature_utils.py` - `validate_signature()`

**Example Output:**
```
🔐 SIGNATURE VALIDATION:
   📝 Message Type: credit_intent
   🔑 Received Signature: IBFA83CVS2wQHIn+...50F2KQE=
   🔑 Secret Key Length: 18 characters
   🔑 Expected Signature: IBFA83CVS2wQHIn+...50F2KQE=
   ✅ VALIDATION RESULT: SIGNATURES MATCH
```

**Information Logged:**
- Message type being validated
- Received signature (truncated)
- Secret key length
- Expected signature (truncated)
- Validation result (MATCH/NO MATCH)

## 🗝️ Secret Key Management Logging

### Location: `secrets_manager.py` - `get_secret()`

**Success Example:**
```
🔐 SECRETS: SECRET KEY RETRIEVED
   👤 Agent ID: company-agent
   🔑 Key Length: 18 characters
   ✅ Status: SUCCESS
```

**Failure Example:**
```
❌ SECRETS: SECRET KEY NOT FOUND
   👤 Agent ID: unknown-agent
   📋 Available Agents: ['company-agent', 'wells-fargo-agent', 'boa-agent', 'chase-bank-agent', 'rogue-agent', 'broker-agent']
   ❌ Status: FAILED
```

## 🛡️ Broker Signature Validation Logging

### Location: `broker_agent/broker_executor.py`

### 1. Validation Start
```
🔐 BROKER: Starting signature validation for company-agent
   📝 Message Type: credit_intent
   📏 Message Length: 245 characters
```

### 2. Validation Success
```
✅ BROKER SIGNATURE VALIDATION SUCCESS:
   🔐 Agent: company-agent
   📝 Message Type: credit_intent
   🔑 Signature: IBFA83CVS2wQHIn+...50F2KQE=
   ⏰ Timestamp: 2024-01-01T12:00:00.000000
```

### 3. Validation Failure
```
❌ BROKER SIGNATURE VALIDATION FAILED:
   🔐 Agent: company-agent
   📝 Message Type: credit_intent
   🔑 Signature: INVALID_SIGNATURE...ABCD123=
   ⏰ Timestamp: 2024-01-01T12:00:00.000000
   ⚠️  Reason: HMAC signature validation failed
```

### 4. Missing Signature
```
❌ BROKER SIGNATURE VALIDATION FAILED:
   🔐 Agent: company-agent
   📝 Message Type: credit_intent
   ⚠️  Reason: No signature found in message
   ⏰ Timestamp: 2024-01-01T12:00:00.000000
```

### 5. Missing Secret Key
```
❌ BROKER SIGNATURE VALIDATION FAILED:
   🔐 Agent: unknown-agent
   📝 Message Type: credit_intent
   ⚠️  Reason: No secret key found for agent
   ⏰ Timestamp: 2024-01-01T12:00:00.000000
```

### 6. Message Acceptance/Rejection
```
🎉 BROKER: MESSAGE ACCEPTED - SIGNATURE VALIDATION PASSED
   🔐 Agent: company-agent
   📝 Message Type: credit_intent
   ✅ Action: Proceeding with message routing
```

```
🚫 BROKER: MESSAGE REJECTED - SIGNATURE VALIDATION FAILED
   🔐 Agent: company-agent
   📝 Message Type: credit_intent
   ⚠️  Action: Marking task as failed
```

## 📤 Outgoing Message Signature Generation

### Location: `broker_agent/broker_executor.py` - `_add_signature_to_message()`

```
🔐 BROKER: SIGNATURE GENERATION SUCCESS
   📤 Direction: Outgoing message
   📝 Message Type: credit_intent
   🔑 Signature: XvAUNOFkTvw/1vwK...Snm7ABC=
   ⏰ Timestamp: 2024-01-01T12:00:00.000000
```

## 👤 Agent Signature Addition Logging

### Company Agent Example
```
🔐 COMPANY: SIGNATURE ADDED TO MESSAGE
   📝 Message Type: credit_intent
   🔑 Signature: IBFA83CVS2wQHIn+...50F2KQE=
   ✅ Status: SUCCESS
```

### Bank Agent Example
```
🔐 WELLS FARGO: SIGNATURE ADDED TO MESSAGE
   📝 Message Type: offer_response
   🔑 Signature: YSHQMJpme6A9sBTJ...F1ILXYZ=
   ✅ Status: SUCCESS
```

## 📋 Audit Trail Logging

### Location: `broker_agent/broker_executor.py` - `_log_audit()`

**Successful Validation:**
```json
{
  "action": "signature_validated",
  "details": {
    "agent_id": "company-agent",
    "message_type": "credit_intent",
    "signature_preview": "IBFA83CVS2wQHIn+...50F2KQE=",
    "validation_status": "SUCCESS",
    "timestamp": "2024-01-01T12:00:00.000000"
  }
}
```

**Failed Validation:**
```json
{
  "action": "signature_invalid",
  "details": {
    "agent_id": "company-agent",
    "message_type": "credit_intent",
    "signature_preview": "INVALID_SIGNATURE...ABCD123=",
    "validation_status": "FAILED",
    "failure_reason": "HMAC signature validation failed",
    "timestamp": "2024-01-01T12:00:00.000000"
  }
}
```

## 🔍 Message Types That Require Signature Validation

1. **`credit_intent`** - Credit requests from company agents
2. **`negotiation_request`** - Negotiation requests from company agents
3. **Offer responses** - Bank agent responses (signed but not validated by broker)
4. **Counter-offer responses** - Bank agent negotiation responses (signed but not validated by broker)

## 📊 Log Levels and Purposes

### ✅ Success Logs
- **Purpose**: Confirm successful operations
- **Use Case**: Normal operation monitoring
- **Security**: Audit trail for legitimate transactions

### ❌ Error Logs
- **Purpose**: Identify failed operations
- **Use Case**: Security monitoring, debugging
- **Security**: Detect potential attack attempts

### ℹ️ Info Logs
- **Purpose**: Operational information
- **Use Case**: Understanding message flow
- **Security**: Context for security analysis

## 🛡️ Security Benefits

1. **Attack Detection**: Failed signature validations may indicate tampering attempts
2. **Audit Trail**: Complete record of all signature operations
3. **Debugging**: Detailed information for troubleshooting signature issues
4. **Compliance**: Comprehensive logging for security audits
5. **Monitoring**: Real-time visibility into signature validation status

## 🔧 Configuration

All logging is enabled by default and outputs to console. For production deployments:

1. **Log Rotation**: Implement log rotation to manage file sizes
2. **Log Aggregation**: Send logs to centralized logging system
3. **Alert Configuration**: Set up alerts for signature validation failures
4. **Log Retention**: Configure appropriate retention policies for audit requirements

## 📈 Monitoring Recommendations

1. **Success Rate**: Monitor signature validation success rates
2. **Failed Attempts**: Alert on repeated signature validation failures
3. **Unknown Agents**: Alert on attempts from unrecognized agent IDs
4. **Performance**: Monitor signature generation/validation performance
5. **Secret Key Issues**: Alert on missing secret key errors
