#!/usr/bin/env python3
"""Test script for direct Azure AI Search authentication with agent identity.

This script demonstrates how to authenticate with agent identity and query
Azure AI Search directly without using the MCP server.
"""

import os
import sys
import logging
import json
from dotenv import load_dotenv

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from src.enterprise_mcp_auth.agent_framework import AgentIdentityManager
from azure.search.documents import SearchClient
from azure.core.credentials import AccessToken

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


class TokenCredential:
    """Simple token credential for Azure SDK."""
    
    def __init__(self, token: str):
        """Initialize with access token."""
        self.token = token
    
    def get_token(self, *scopes, **kwargs) -> AccessToken:
        """Get access token."""
        import time
        return AccessToken(self.token, int(time.time()) + 3600)


def main():
    """Test direct Azure AI Search access with agent identity."""
    print("=" * 60)
    print("Direct Azure AI Search Test with Agent Identity")
    print("=" * 60)
    print()
    
    # Load environment variables
    load_dotenv()
    
    # Get configuration from environment
    endpoint = os.getenv("AZURE_SEARCH_ENDPOINT")
    index_name = os.getenv("AZURE_SEARCH_INDEX", "documents")
    search_query = sys.argv[1] if len(sys.argv) > 1 else "security"
    
    if not endpoint:
        print("✗ Error: AZURE_SEARCH_ENDPOINT environment variable is required")
        return 1
    
    print(f"Endpoint: {endpoint}")
    print(f"Index: {index_name}")
    print(f"Search Query: {search_query}")
    print()
    
    try:
        # Initialize agent identity manager
        print("Initializing Agent Identity Manager...")
        identity_manager = AgentIdentityManager()
        
        identity_info = identity_manager.get_identity_info()
        print(f"✓ Tenant ID: {identity_info['tenant_id']}")
        print(f"✓ Client ID: {identity_info['client_id']}")
        print()
        
        # Acquire token for Azure AI Search
        print("Acquiring access token for Azure AI Search...")
        token = identity_manager.get_agent_token(
            scopes=["https://search.azure.com/.default"]
        )
        print(f"✓ Token acquired (length: {len(token)})")
        print()
        
        # Create Azure Search client with token
        print(f"Creating Azure Search client for index: {index_name}...")
        credential = TokenCredential(token)
        search_client = SearchClient(
            endpoint=endpoint,
            index_name=index_name,
            credential=credential,
        )
        print("✓ Search client created")
        print()
        
        # Perform search
        print(f"Searching for: '{search_query}'...")
        results = search_client.search(
            search_text=search_query,
            top=5,
            include_total_count=True,
        )
        
        # Collect and display results
        documents = []
        for result in results:
            documents.append(dict(result))
        
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
                
                # Show permission fields if present
                if 'oid' in doc:
                    print(f"   User IDs: {doc['oid']}")
                if 'group' in doc:
                    print(f"   Group IDs: {doc['group']}")
        else:
            print("No documents found.")
        
        print()
        
        # Test getting a specific document
        if documents:
            doc_id = documents[0].get('id')
            if doc_id:
                print(f"Testing document retrieval for ID: {doc_id}...")
                try:
                    document = search_client.get_document(key=doc_id)
                    print(f"✓ Document retrieved successfully")
                    print(f"   Title: {document.get('title', 'N/A')}")
                except Exception as e:
                    print(f"✗ Failed to retrieve document: {e}")
                print()
        
        print("=" * 60)
        print("Test completed successfully!")
        print("=" * 60)
        print()
        print("Note: This test bypasses the MCP server and authenticates")
        print("directly to Azure AI Search using the agent identity.")
        
        return 0
        
    except Exception as e:
        logger.error(f"Test failed: {e}", exc_info=True)
        print(f"\n✗ Error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
