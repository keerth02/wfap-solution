"""Shared JWT keys for WFAP system"""
from protocols.jwt import generate_key_pair

# Generate shared key pair for the entire system
COMPANY_PRIVATE_KEY, COMPANY_PUBLIC_KEY = generate_key_pair()
WELLS_FARGO_PRIVATE_KEY, WELLS_FARGO_PUBLIC_KEY = generate_key_pair()
BOA_PRIVATE_KEY, BOA_PUBLIC_KEY = generate_key_pair()

# Export keys for use by all agents
SHARED_KEYS = {
    "company-agent-1": {
        "private": COMPANY_PRIVATE_KEY,
        "public": COMPANY_PUBLIC_KEY
    },
    "wells-fargo": {
        "private": WELLS_FARGO_PRIVATE_KEY,
        "public": WELLS_FARGO_PUBLIC_KEY
    },
    "bank-of-america": {
        "private": BOA_PRIVATE_KEY,
        "public": BOA_PUBLIC_KEY
    }
}

# Public keys for validation
PUBLIC_KEYS = {
    "company-agent-1": COMPANY_PUBLIC_KEY,
    "wells-fargo": WELLS_FARGO_PUBLIC_KEY,
    "bank-of-america": BOA_PUBLIC_KEY
}
