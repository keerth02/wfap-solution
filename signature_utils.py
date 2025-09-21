"""
HMAC Signature Utilities for WFAP Agent Communication
Provides signature generation and validation for secure agent-to-agent communication
"""

import hmac
import hashlib
import base64
import json
from typing import Dict, Any


def generate_signature(message_content: Dict[str, Any], secret_key: str) -> str:
    """
    Generate HMAC-SHA256 signature for message content
    
    Args:
        message_content: Dictionary containing message data
        secret_key: Secret key for HMAC generation
        
    Returns:
        Base64-encoded HMAC signature
    """
    try:
        # Convert message to JSON string (sorted keys for consistency)
        message_str = json.dumps(message_content, sort_keys=True, separators=(',', ':'))
        
        print(f"🔐 SIGNATURE GENERATION:")
        print(f"   📝 Message Type: {message_content.get('message_type', 'unknown')}")
        print(f"   🔑 Secret Key Length: {len(secret_key)} characters")
        print(f"   📏 Message Length: {len(message_str)} characters")
        
        # Generate HMAC signature
        signature = hmac.new(
            secret_key.encode('utf-8'),
            message_str.encode('utf-8'),
            hashlib.sha256
        ).digest()
        
        # Return base64 encoded signature
        b64_signature = base64.b64encode(signature).decode('utf-8')
        
        print(f"   ✅ Generated Signature: {b64_signature[:16]}...{b64_signature[-8:]}")
        return b64_signature
        
    except Exception as e:
        print(f"❌ SIGNATURE GENERATION ERROR: {e}")
        return ""


def validate_signature(message_content: Dict[str, Any], signature: str, secret_key: str) -> bool:
    """
    Validate HMAC signature against message content
    
    Args:
        message_content: Dictionary containing message data
        signature: Base64-encoded signature to validate
        secret_key: Secret key for HMAC validation
        
    Returns:
        True if signature is valid, False otherwise
    """
    try:
        print(f"🔐 SIGNATURE VALIDATION:")
        print(f"   📝 Message Type: {message_content.get('message_type', 'unknown')}")
        print(f"   🔑 Received Signature: {signature[:16]}...{signature[-8:]}")
        print(f"   🔑 Secret Key Length: {len(secret_key)} characters")
        
        # Generate expected signature
        expected_signature = generate_signature(message_content, secret_key)
        
        print(f"   🔑 Expected Signature: {expected_signature[:16]}...{expected_signature[-8:]}")
        
        # Use constant-time comparison to prevent timing attacks
        is_valid = hmac.compare_digest(signature, expected_signature)
        
        if is_valid:
            print(f"   ✅ VALIDATION RESULT: SIGNATURES MATCH")
        else:
            print(f"   ❌ VALIDATION RESULT: SIGNATURES DO NOT MATCH")
            
        return is_valid
        
    except Exception as e:
        print(f"❌ SIGNATURE VALIDATION ERROR: {e}")
        return False


def extract_signature_from_message(message_content: Dict[str, Any]) -> tuple[Dict[str, Any], str]:
    """
    Extract signature from message content
    
    Args:
        message_content: Dictionary containing message data with signature
        
    Returns:
        Tuple of (message_without_signature, signature)
    """
    try:
        # Create copy to avoid modifying original
        message_copy = message_content.copy()
        
        # Extract signature
        signature = message_copy.pop('signature', '')
        
        return message_copy, signature
        
    except Exception as e:
        print(f"❌ SIGNATURE: Error extracting signature: {e}")
        return message_content, ""
