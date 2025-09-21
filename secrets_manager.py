"""
Secrets Manager for WFAP Agent Communication
Manages shared secret keys for HMAC signature validation
"""

import json
import os
from typing import Dict, Optional


class SecretsManager:
    """Manages shared secret keys for agent authentication"""
    
    def __init__(self, secrets_file: str = "shared_secrets.json"):
        """
        Initialize secrets manager
        
        Args:
            secrets_file: Path to the secrets JSON file
        """
        self.secrets_file = secrets_file
        self._secrets = self._load_secrets()
        print(f"🔐 SECRETS: Loaded {len(self._secrets)} secret keys from {secrets_file}")
    
    def _load_secrets(self) -> Dict[str, str]:
        """
        Load secrets from JSON file
        
        Returns:
            Dictionary mapping agent_id to secret_key
        """
        try:
            # Get absolute path to secrets file
            secrets_path = os.path.join(os.path.dirname(__file__), self.secrets_file)
            
            with open(secrets_path, 'r') as f:
                secrets = json.load(f)
                print(f"✅ SECRETS: Successfully loaded secrets for agents: {list(secrets.keys())}")
                return secrets
                
        except FileNotFoundError:
            print(f"❌ SECRETS: Secrets file {secrets_path} not found")
            return {}
        except json.JSONDecodeError as e:
            print(f"❌ SECRETS: Invalid JSON in secrets file: {e}")
            return {}
        except Exception as e:
            print(f"❌ SECRETS: Error loading secrets: {e}")
            return {}
    
    def get_secret(self, agent_id: str) -> Optional[str]:
        """
        Get secret key for agent
        
        Args:
            agent_id: Identifier for the agent
            
        Returns:
            Secret key if found, None otherwise
        """
        secret = self._secrets.get(agent_id)
        if secret:
            print(f"🔐 SECRETS: SECRET KEY RETRIEVED")
            print(f"   👤 Agent ID: {agent_id}")
            print(f"   🔑 Key Length: {len(secret)} characters")
            print(f"   ✅ Status: SUCCESS")
        else:
            print(f"❌ SECRETS: SECRET KEY NOT FOUND")
            print(f"   👤 Agent ID: {agent_id}")
            print(f"   📋 Available Agents: {list(self._secrets.keys())}")
            print(f"   ❌ Status: FAILED")
        return secret
    
    def has_agent(self, agent_id: str) -> bool:
        """
        Check if agent has a secret key
        
        Args:
            agent_id: Identifier for the agent
            
        Returns:
            True if agent has secret key, False otherwise
        """
        has_secret = agent_id in self._secrets
        print(f"🔐 SECRETS: Agent {agent_id} {'has' if has_secret else 'does not have'} secret key")
        return has_secret
    
    def list_agents(self) -> list[str]:
        """
        List all agents with secret keys
        
        Returns:
            List of agent IDs
        """
        agents = list(self._secrets.keys())
        print(f"🔐 SECRETS: Available agents: {agents}")
        return agents
    
    def reload_secrets(self) -> bool:
        """
        Reload secrets from file
        
        Returns:
            True if successful, False otherwise
        """
        try:
            self._secrets = self._load_secrets()
            print(f"✅ SECRETS: Successfully reloaded secrets")
            return True
        except Exception as e:
            print(f"❌ SECRETS: Error reloading secrets: {e}")
            return False
