#!/usr/bin/env python3
"""Setup script for creating agent identity configuration.

This script creates an agent identity that can be used for authentication
with Azure services.
"""

import os
import sys
import logging
from dotenv import load_dotenv

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from src.enterprise_mcp_auth.agent_framework import AgentIdentityManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def main():
    """Create agent identity configuration."""
    print("=" * 60)
    print("Agent Identity Setup")
    print("=" * 60)
    print()
    
    # Load environment variables
    load_dotenv()
    
    # Get configuration from environment
    agent_name = os.getenv("AGENT_NAME", "enterprise-agent")
    blueprint_name = os.getenv("AGENT_BLUEPRINT_NAME", "enterprise-blueprint")
    
    print(f"Agent Name: {agent_name}")
    print(f"Blueprint Name: {blueprint_name}")
    print()
    
    try:
        # Initialize agent identity manager
        print("Initializing Agent Identity Manager...")
        identity_manager = AgentIdentityManager()
        
        # Display identity info
        identity_info = identity_manager.get_identity_info()
        print(f"✓ Tenant ID: {identity_info['tenant_id']}")
        print(f"✓ Client ID: {identity_info['client_id']}")
        print(f"✓ Audience: {identity_info['audience']}")
        print()
        
        # Validate identity
        print("Validating agent identity...")
        if identity_manager.validate_identity():
            print("✓ Agent identity is valid")
        else:
            print("✗ Agent identity validation failed")
            return 1
        
        print()
        
        # Create agent identity
        print(f"Creating agent identity: {agent_name}...")
        identity = identity_manager.create_agent_identity(
            agent_name=agent_name,
            blueprint_name=blueprint_name,
            description=f"Enterprise agent for Azure AI Search access",
            metadata={
                "environment": os.getenv("ENVIRONMENT", "development"),
                "version": "1.0.0",
            },
        )
        
        print("✓ Agent identity created successfully")
        print()
        print("Identity Details:")
        print(f"  Name: {identity.get('name', agent_name)}")
        print(f"  Tenant: {identity.get('tenant_id', identity_info['tenant_id'])}")
        print(f"  Client: {identity.get('client_id', identity_info['client_id'])}")
        print()
        
        print("=" * 60)
        print("Setup completed successfully!")
        print("=" * 60)
        
        return 0
        
    except Exception as e:
        logger.error(f"Setup failed: {e}", exc_info=True)
        print(f"\n✗ Error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
