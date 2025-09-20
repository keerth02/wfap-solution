"""JWT Protocol Definition for WFAP"""
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
import jwt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
import json
import uuid

class JWTClaims(BaseModel):
    iss: str = Field(..., description="Issuer (agent identifier)")
    aud: str = Field(default="wfap-system", description="Audience")
    exp: datetime = Field(..., description="Expiration time")
    iat: datetime = Field(default_factory=datetime.utcnow, description="Issued at")
    jti: str = Field(default_factory=lambda: f"jwt_{uuid.uuid4().hex}", description="JWT ID")
    data: Dict[str, Any] = Field(..., description="Payload data")

class JWTSigner:
    """JWT signing utility"""
    
    def __init__(self, private_key_pem: str, issuer: str):
        self.private_key = serialization.load_pem_private_key(
            private_key_pem.encode(), password=None
        )
        self.issuer = issuer
    
    def sign(self, data: Dict[str, Any], expiration_hours: int = 1) -> str:
        """Sign data with JWT"""
        import time
        now_timestamp = int(time.time())
        exp_timestamp = now_timestamp + (expiration_hours * 3600)
        
        # Create claims dict with Unix timestamps
        claims_dict = {
            'iss': self.issuer,
            'aud': 'wfap-system',
            'exp': exp_timestamp,
            'iat': now_timestamp,
            'jti': f"jwt_{uuid.uuid4().hex}",
            'data': data
        }
        
        return jwt.encode(
            claims_dict,
            self.private_key,
            algorithm="RS256"
        )

class JWTValidator:
    """JWT validation utility"""
    
    def __init__(self, public_keys: Dict[str, str]):
        self.public_keys = {}
        for issuer, key_pem in public_keys.items():
            self.public_keys[issuer] = serialization.load_pem_public_key(
                key_pem.encode()
            )
    
    def validate(self, token: str, expected_issuer: str) -> tuple[bool, Optional[Dict[str, Any]]]:
        """Validate JWT token"""
        try:
            payload = jwt.decode(
                token,
                self.public_keys[expected_issuer],
                algorithms=["RS256"],
                audience="wfap-system"
            )
            return True, payload
        except jwt.InvalidTokenError as e:
            return False, None

def generate_key_pair() -> tuple[str, str]:
    """Generate RSA key pair for JWT signing"""
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048
    )
    
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption()
    ).decode()
    
    public_key = private_key.public_key()
    public_pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    ).decode()
    
    return private_pem, public_pem
