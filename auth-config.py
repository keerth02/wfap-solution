"""Authentication configuration for WFAP agents"""
import jwt
import time
from typing import Dict, Any, Optional
from datetime import datetime, timedelta

# Authentication configuration for all agents
AUTH_CONFIG = {
    "broker": {
        "client_id": "broker-server",
        "client_secret": "broker-secret-key-123",
        "token_endpoint": "http://localhost:8000/auth/token",
        "verify_endpoint": "http://localhost:8000/auth/verify",
        "jwt_secret": "wfap-jwt-secret-key-2024"
    },
    "company": {
        "client_id": "company-agent",
        "client_secret": "company-secret-456",
        "name": "TechCorp Inc"
    },
    "wells_fargo": {
        "client_id": "wells-fargo-agent", 
        "client_secret": "wf-secret-789",
        "name": "Wells Fargo Bank"
    },
    "bank_of_america": {
        "client_id": "boa-agent",
        "client_secret": "boa-secret-101",
        "name": "Bank of America"
    },
    "chase_bank": {
        "client_id": "chase-agent",
        "client_secret": "chase-secret-202",
        "name": "Chase Bank"
    }
}

# Token storage (in-memory for simplicity)
AGENT_TOKENS: Dict[str, Dict[str, Any]] = {}

class AuthManager:
    """Simple OAuth 2.0 Client Credentials flow manager"""
    
    def __init__(self):
        self.jwt_secret = AUTH_CONFIG["broker"]["jwt_secret"]
        self.token_expiry_hours = 1
    
    def generate_access_token(self, client_id: str, client_secret: str) -> Optional[Dict[str, Any]]:
        """Generate JWT access token for valid client credentials"""
        print(f"🔐 AUTH: Generating token for client_id: {client_id}")
        
        # Validate client credentials
        valid_clients = {config["client_id"]: config["client_secret"] 
                        for config in AUTH_CONFIG.values() 
                        if "client_secret" in config}
        
        if client_id not in valid_clients or valid_clients[client_id] != client_secret:
            print(f"❌ AUTH: Invalid credentials for client_id: {client_id}")
            return None
        
        # Generate JWT token
        now = datetime.utcnow()
        payload = {
            "client_id": client_id,
            "iat": now,
            "exp": now + timedelta(hours=self.token_expiry_hours),
            "scope": "wfap:credit wfap:negotiation",
            "iss": "wfap-broker",
            "aud": "wfap-agents"
        }
        
        token = jwt.encode(payload, self.jwt_secret, algorithm="HS256")
        
        token_data = {
            "access_token": token,
            "token_type": "Bearer",
            "expires_in": self.token_expiry_hours * 3600,
            "client_id": client_id,
            "scope": "wfap:credit wfap:negotiation",
            "issued_at": now.isoformat(),
            "expires_at": (now + timedelta(hours=self.token_expiry_hours)).isoformat()
        }
        
        # Store token for tracking
        AGENT_TOKENS[client_id] = token_data
        
        print(f"✅ AUTH: Token issued for {client_id}")
        print(f"   🕐 Expires at: {token_data['expires_at']}")
        
        return token_data
    
    def validate_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Validate JWT token and return payload if valid"""
        try:
            # Remove 'Bearer ' prefix if present
            if token.startswith('Bearer '):
                token = token[7:]
            
            payload = jwt.decode(token, self.jwt_secret, algorithms=["HS256"])
            
            # Check if token is expired
            if datetime.utcnow().timestamp() > payload['exp']:
                print(f"⚠️ AUTH: Token expired for client_id: {payload.get('client_id')}")
                return None
            
            print(f"🔍 AUTH: Token validated for client_id: {payload.get('client_id')}")
            return payload
            
        except jwt.ExpiredSignatureError:
            print(f"⚠️ AUTH: Token signature expired")
            return None
        except jwt.InvalidTokenError as e:
            print(f"❌ AUTH: Invalid token: {str(e)}")
            return None
        except Exception as e:
            print(f"❌ AUTH: Token validation error: {str(e)}")
            return None
    
    def get_client_info(self, client_id: str) -> Optional[Dict[str, Any]]:
        """Get client information from config"""
        for config in AUTH_CONFIG.values():
            if config.get("client_id") == client_id:
                return config
        return None
    
    def log_auth_event(self, event_type: str, client_id: str, details: Dict[str, Any] = None):
        """Log authentication events"""
        timestamp = datetime.utcnow().isoformat()
        log_entry = {
            "timestamp": timestamp,
            "event_type": event_type,
            "client_id": client_id,
            "details": details or {}
        }
        
        print(f"🔐 AUTH LOG [{event_type}]: {client_id} - {timestamp}")
        if details:
            print(f"   📋 Details: {details}")

# Global auth manager instance
auth_manager = AuthManager()
