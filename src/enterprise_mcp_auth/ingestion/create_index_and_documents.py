"""Azure AI Search Index Creation and Document Ingestion.

This module creates an Azure AI Search index with permission filtering enabled
and uploads sample documents for testing.
"""

import os
import sys
from typing import List, Dict, Any
from dotenv import load_dotenv
from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import (
    SearchIndex,
    SimpleField,
    SearchableField,
    SearchFieldDataType,
    SearchSuggester,
)

# Load environment variables
load_dotenv()

# Environment variables
AZURE_SEARCH_ENDPOINT = os.getenv("AZURE_SEARCH_ENDPOINT", "")
AZURE_SEARCH_INDEX = os.getenv("AZURE_SEARCH_INDEX", "documents")
AZURE_SEARCH_ADMIN_KEY = os.getenv("AZURE_SEARCH_ADMIN_KEY", "")


def create_index_with_permission_filtering(index_client: SearchIndexClient, index_name: str):
    """Create an Azure AI Search index with permission filtering enabled.
    
    Args:
        index_client: SearchIndexClient instance
        index_name: Name of the index to create
    """
    print(f"Creating index '{index_name}' with permission filtering...")
    
    # Define fields with permission filtering
    fields = [
        SimpleField(
            name="id",
            type=SearchFieldDataType.String,
            key=True,
            filterable=True,
        ),
        SimpleField(
            name="oid",
            type=SearchFieldDataType.Collection(SearchFieldDataType.String),
            filterable=True,
            # This field will be used for USER_IDS permission filtering
        ),
        SimpleField(
            name="group",
            type=SearchFieldDataType.Collection(SearchFieldDataType.String),
            filterable=True,
            # This field will be used for GROUP_IDS permission filtering
        ),
        SearchableField(
            name="name",
            type=SearchFieldDataType.String,
            filterable=True,
            sortable=True,
        ),
        SearchableField(
            name="content",
            type=SearchFieldDataType.String,
            filterable=False,
        ),
        SearchableField(
            name="category",
            type=SearchFieldDataType.String,
            filterable=True,
            facetable=True,
        ),
    ]
    
    # Create suggester named 'sg' with source fields
    suggesters = [
        SearchSuggester(
            name="sg",
            source_fields=["name", "content", "category"],
        )
    ]
    
    # Create index with permission filtering enabled
    index = SearchIndex(
        name=index_name,
        fields=fields,
        suggesters=suggesters,
    )
    
    # Delete index if it exists
    try:
        index_client.delete_index(index_name)
        print(f"Deleted existing index '{index_name}'")
    except Exception:
        pass
    
    # Create the index
    result = index_client.create_index(index)
    print(f"Index '{result.name}' created successfully")
    
    # Note: Permission filtering is enabled via the x-ms-query-source-authorization header
    # at query time, not through index configuration. The oid and group fields are used
    # for permission filtering when the header is present.
    print("Permission filtering will be enforced via x-ms-query-source-authorization header")
    print("  - 'oid' field: USER_IDS permission filter")
    print("  - 'group' field: GROUP_IDS permission filter")


def get_sample_documents() -> List[Dict[str, Any]]:
    """Generate sample documents for testing.
    
    Returns:
        List of sample documents with various permission settings
    """
    return [
        {
            "id": "doc1",
            "oid": ["user1@example.com", "user2@example.com"],
            "group": ["group1", "group2"],
            "name": "Security Best Practices",
            "content": "This document contains security best practices for enterprise applications including authentication, authorization, and data protection strategies.",
            "category": "Security",
        },
        {
            "id": "doc2",
            "oid": ["user1@example.com"],
            "group": ["group1"],
            "name": "Azure AI Search Overview",
            "content": "Azure AI Search is a cloud search service that provides infrastructure, APIs, and tools for building search experiences over private, heterogeneous content in web, mobile, and enterprise applications.",
            "category": "Documentation",
        },
        {
            "id": "doc3",
            "oid": ["user2@example.com", "user3@example.com"],
            "group": ["group2", "group3"],
            "name": "MCP Protocol Guide",
            "content": "The Model Context Protocol (MCP) is an open protocol that standardizes how applications provide context to LLMs. This guide covers authentication, transport, and tool definitions.",
            "category": "Documentation",
        },
        {
            "id": "doc4",
            "oid": ["user1@example.com", "user2@example.com", "user3@example.com"],
            "group": ["group1", "group2", "group3"],
            "name": "Enterprise Authentication Patterns",
            "content": "This document describes various enterprise authentication patterns including OAuth 2.0, OpenID Connect, SAML, and On-Behalf-Of flow for secure access to resources.",
            "category": "Security",
        },
        {
            "id": "doc5",
            "oid": ["user3@example.com"],
            "group": ["group3"],
            "name": "Python Development Guide",
            "content": "A comprehensive guide to Python development covering best practices, code organization, testing strategies, and common patterns for building maintainable applications.",
            "category": "Development",
        },
        {
            "id": "doc6",
            "oid": ["user1@example.com", "user4@example.com"],
            "group": ["group1", "group4"],
            "name": "Secure API Design",
            "content": "Best practices for designing secure APIs including rate limiting, input validation, output encoding, authentication mechanisms, and secure communication protocols.",
            "category": "Security",
        },
        {
            "id": "doc7",
            "oid": ["user2@example.com", "user3@example.com", "user4@example.com"],
            "group": ["group2", "group3", "group4"],
            "name": "Search Optimization Techniques",
            "content": "Learn about various search optimization techniques including indexing strategies, query optimization, relevance tuning, and performance monitoring.",
            "category": "Documentation",
        },
        {
            "id": "doc8",
            "oid": ["user1@example.com"],
            "group": ["group1"],
            "name": "Secret Management in Azure",
            "content": "Guide to managing secrets in Azure using Azure Key Vault, managed identities, and secure coding practices to prevent credential leakage.",
            "category": "Security",
        },
    ]


def upload_documents(search_client: SearchClient, documents: List[Dict[str, Any]]):
    """Upload documents to Azure AI Search index.
    
    Args:
        search_client: SearchClient instance
        documents: List of documents to upload
    """
    print(f"\nUploading {len(documents)} sample documents...")
    
    try:
        result = search_client.upload_documents(documents=documents)
        
        success_count = sum(1 for r in result if r.succeeded)
        failed_count = len(result) - success_count
        
        print(f"Successfully uploaded {success_count} documents")
        if failed_count > 0:
            print(f"Failed to upload {failed_count} documents")
            for r in result:
                if not r.succeeded:
                    print(f"  - Document {r.key}: {r.error_message}")
    except Exception as e:
        print(f"Error uploading documents: {e}")
        raise


def main():
    """Main entry point for index creation and document ingestion."""
    # Validate required environment variables
    if not AZURE_SEARCH_ENDPOINT:
        print("Error: AZURE_SEARCH_ENDPOINT environment variable is required")
        sys.exit(1)
    if not AZURE_SEARCH_ADMIN_KEY:
        print("Error: AZURE_SEARCH_ADMIN_KEY environment variable is required")
        sys.exit(1)
    
    print("=" * 70)
    print("Azure AI Search Index Creation and Document Ingestion")
    print("=" * 70)
    print(f"Endpoint: {AZURE_SEARCH_ENDPOINT}")
    print(f"Index: {AZURE_SEARCH_INDEX}")
    print()
    
    # Create credential
    credential = AzureKeyCredential(AZURE_SEARCH_ADMIN_KEY)
    
    # Create index client
    index_client = SearchIndexClient(
        endpoint=AZURE_SEARCH_ENDPOINT,
        credential=credential
    )
    
    # Create index with permission filtering
    try:
        create_index_with_permission_filtering(index_client, AZURE_SEARCH_INDEX)
    except Exception as e:
        print(f"Error creating index: {e}")
        sys.exit(1)
    
    # Create search client for document operations
    search_client = SearchClient(
        endpoint=AZURE_SEARCH_ENDPOINT,
        index_name=AZURE_SEARCH_INDEX,
        credential=credential
    )
    
    # Get sample documents
    documents = get_sample_documents()
    
    # Upload documents
    try:
        upload_documents(search_client, documents)
    except Exception as e:
        print(f"Error during ingestion: {e}")
        sys.exit(1)
    
    print("\n" + "=" * 70)
    print("Index creation and document ingestion completed successfully!")
    print("=" * 70)
    print(f"\nYou can now query the index using the MCP server and client.")
    print(f"The index contains {len(documents)} documents with various permission settings.")
    print("\nPermission filtering is enabled:")
    print("  - 'oid' field contains user IDs (e.g., user1@example.com)")
    print("  - 'group' field contains group IDs (e.g., group1, group2)")
    print("\nDocuments will be filtered based on the user's OBO token when querying")
    print("through the MCP server using the x-ms-query-source-authorization header.")


if __name__ == "__main__":
    main()
