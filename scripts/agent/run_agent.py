#!/usr/bin/env python3
"""Run agent with authentication using agent identity.

This script demonstrates how to run an agent with agent identity
authentication and perform operations.
"""

import os
import sys
import logging
import json
from dotenv import load_dotenv

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from src.enterprise_mcp_auth.agent_framework import (
    EnterpriseAgent,
    AgentIdentityManager,
    AgentBlueprintManager,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def main():
    """Run the enterprise agent."""
    print("=" * 60)
    print("Enterprise Agent - Running")
    print("=" * 60)
    print()
    
    # Load environment variables
    load_dotenv()
    
    # Get configuration from environment
    agent_name = os.getenv("AGENT_NAME", "enterprise-agent")
    search_query = sys.argv[1] if len(sys.argv) > 1 else "security"
    
    print(f"Agent Name: {agent_name}")
    print(f"Search Query: {search_query}")
    print()
    
    try:
        # Initialize agent
        print("Initializing Enterprise Agent...")
        agent = EnterpriseAgent(agent_name=agent_name)
        print("✓ Agent initialized")
        print()
        
        # Display agent info
        agent_info = agent.get_agent_info()
        print("Agent Information:")
        print(f"  Name: {agent_info['name']}")
        print(f"  Identity Client ID: {agent_info['identity']['client_id']}")
        print(f"  Blueprint Name: {agent_info['blueprint']['name']}")
        print()
        
        # Validate agent
        print("Validating agent configuration...")
        if not agent.validate():
            print("✗ Agent validation failed")
            return 1
        print("✓ Agent validated successfully")
        print()
        
        # Authenticate
        print("Authenticating agent...")
        token = agent.authenticate()
        print(f"✓ Agent authenticated (token length: {len(token)})")
        print()
        
        # Get Azure Search endpoint
        endpoint = os.getenv("AZURE_SEARCH_ENDPOINT")
        if not endpoint:
            print("⚠ AZURE_SEARCH_ENDPOINT not set, skipping document search")
            print()
            print("=" * 60)
            print("Agent run completed successfully!")
            print("=" * 60)
            return 0
        
        # Search documents
        print(f"Searching documents with query: '{search_query}'...")
        documents = agent.search_documents(query=search_query, top=5)
        
        print(f"✓ Found {len(documents)} documents")
        print()
        
        # Display results
        if documents:
            print("Search Results:")
            print("-" * 60)
            for i, doc in enumerate(documents, 1):
                print(f"\n{i}. Document ID: {doc.get('id', 'N/A')}")
                print(f"   Title: {doc.get('title', 'N/A')}")
                print(f"   Content: {doc.get('content', 'N/A')[:100]}...")
                if '@search.score' in doc:
                    print(f"   Score: {doc['@search.score']:.4f}")
        else:
            print("No documents found.")
        
        print()
        print("=" * 60)
        print("Agent run completed successfully!")
        print("=" * 60)
        
        return 0
        
    except Exception as e:
        logger.error(f"Agent run failed: {e}", exc_info=True)
        print(f"\n✗ Error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
