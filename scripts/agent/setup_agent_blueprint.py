#!/usr/bin/env python3
"""Setup script for creating agent blueprint configuration.

This script creates an agent blueprint that defines the capabilities
and configuration for an agent.
"""

import os
import sys
import logging
from dotenv import load_dotenv

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from src.enterprise_mcp_auth.agent_framework import AgentBlueprintManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def main():
    """Create agent blueprint configuration."""
    print("=" * 60)
    print("Agent Blueprint Setup")
    print("=" * 60)
    print()
    
    # Load environment variables
    load_dotenv()
    
    # Get configuration from environment
    blueprint_name = os.getenv("AGENT_BLUEPRINT_NAME", "enterprise-blueprint")
    
    print(f"Blueprint Name: {blueprint_name}")
    print()
    
    try:
        # Initialize agent blueprint manager
        print("Initializing Agent Blueprint Manager...")
        blueprint_manager = AgentBlueprintManager(blueprint_name=blueprint_name)
        print("✓ Blueprint manager initialized")
        print()
        
        # Create blueprint with capabilities
        print(f"Creating agent blueprint: {blueprint_name}...")
        capabilities = [
            "search_documents",
            "retrieve_document",
            "authenticate_to_azure",
            "query_azure_ai_search",
        ]
        
        blueprint = blueprint_manager.create_blueprint(
            name=blueprint_name,
            description="Enterprise agent blueprint for Azure AI Search access",
            capabilities=capabilities,
            metadata={
                "version": "1.0.0",
                "environment": os.getenv("ENVIRONMENT", "development"),
                "target_services": ["Azure AI Search"],
            },
        )
        
        print("✓ Agent blueprint created successfully")
        print()
        
        # Display blueprint info
        blueprint_info = blueprint_manager.get_blueprint_info()
        print("Blueprint Details:")
        print(f"  Name: {blueprint_info['name']}")
        print(f"  Description: {blueprint_info['description']}")
        print(f"  Capabilities:")
        for cap in blueprint_info['capabilities']:
            print(f"    - {cap}")
        print()
        
        # Validate blueprint
        print("Validating agent blueprint...")
        if blueprint_manager.validate_blueprint():
            print("✓ Agent blueprint is valid")
        else:
            print("✗ Agent blueprint validation failed")
            return 1
        
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
