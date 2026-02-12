"""Azure AI Search Index Creation and Document Ingestion.

This module creates an Azure AI Search index with permission filtering enabled
and uploads sample documents for testing.
"""

import os
import subprocess
import json
import sys
import asyncio
from typing import List, Dict, Any
from dotenv import load_dotenv
from azure.core.credentials import AzureKeyCredential
from azure.identity import DefaultAzureCredential
from azure.search.documents import SearchClient
from azure.search.documents.indexes import SearchIndexClient
from msgraph import GraphServiceClient
from azure.search.documents.indexes.models import (
    SearchIndex,
    SimpleField,
    SearchableField,
    SearchFieldDataType,
    SearchSuggester,
    PermissionFilter,
    SearchIndexPermissionFilterOption
)

# Load environment variables
load_dotenv()

# Environment variables
AZURE_SEARCH_ENDPOINT = os.getenv("AZURE_SEARCH_ENDPOINT", "")
AZURE_SEARCH_INDEX = os.getenv("AZURE_SEARCH_INDEX", "documents")
AZURE_SEARCH_ADMIN_KEY = os.getenv("AZURE_SEARCH_ADMIN_KEY", "")
AI_SEARCH_QUERY_USER_ID = os.getenv("AI_SEARCH_QUERY_USER_ID", "").strip()
AI_SEARCH_QUERY_GROUP_ID = os.getenv("AI_SEARCH_QUERY_GROUP_ID", "").strip()

# Set to True to delete and recreate the index; False to keep existing index
RECREATE_INDEX = False


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
            permission_filter=PermissionFilter.USER_IDS 
            # This field will be used for USER_IDS permission filtering
        ),
        SimpleField(
            name="group",
            type=SearchFieldDataType.Collection(SearchFieldDataType.String),
            filterable=True,
            permission_filter=PermissionFilter.GROUP_IDS
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
        permission_filter_option=SearchIndexPermissionFilterOption.ENABLED
    )
    
    # Only delete and recreate if RECREATE_INDEX is True
    if RECREATE_INDEX:
        try:
            index_client.delete_index(index_name)
            print(f"Deleted existing index '{index_name}'")
        except Exception:
            pass
    else:
        # Check if the index already exists; if so, skip creation
        try:
            existing = index_client.get_index(index_name)
            print(f"Index '{index_name}' already exists. Skipping creation (set RECREATE_INDEX=True to recreate).")
            return
        except Exception:
            pass  # Index doesn't exist, proceed with creation
    
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
    """Load sample documents from JSON file and inject configured user/group IDs.

    The AI_SEARCH_QUERY_USER_ID and AI_SEARCH_QUERY_GROUP_ID env vars
    are automatically added to every document's oid/group fields so the
    specified user/group always has access to all sample documents.

    Returns:
        List of sample documents with various permission settings
    """
    # Load documents from JSON file
    json_path = os.path.join(os.path.dirname(__file__), "sample_documents.json")
    with open(json_path, "r") as f:
        documents = json.load(f)

    # Collect extra IDs to inject into every document
    extra_oids: List[str] = []
  
    if AI_SEARCH_QUERY_USER_ID:
        extra_oids.append(AI_SEARCH_QUERY_USER_ID)

    extra_groups: List[str] = []
    if AI_SEARCH_QUERY_GROUP_ID:
        extra_groups.append(AI_SEARCH_QUERY_GROUP_ID)

    # Inject current user / query IDs into every document
    for doc in documents:
        for oid in extra_oids:
            if oid not in doc["oid"]:
                doc["oid"].append(oid)
        for gid in extra_groups:
            if gid not in doc["group"]:
                doc["group"].append(gid)

    return documents


async def get_current_user_info() -> tuple[str, List[str]]:
    """Fetch the current logged-in user's OID and group IDs via Microsoft Graph.
    
    Returns:
        Tuple of (user OID, list of group IDs)
    """
    credential = DefaultAzureCredential()
    client = GraphServiceClient(credentials=credential, scopes=["https://graph.microsoft.com/.default"])
    
    me = await client.me.get()
    oid = me.id
    print(f"Current user OID: {oid}")
    print(f"Current user: {me.display_name} ({me.user_principal_name})")
    
    # Get group memberships
    group_ids: List[str] = []
    member_of = await client.me.member_of.get()
    if member_of and member_of.value:
        for item in member_of.value:
            if hasattr(item, 'id') and item.id:
                group_ids.append(item.id)
    
    if group_ids:
        print(f"User belongs to {len(group_ids)} groups")
    
    return oid, group_ids


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
    asyncio.run(_async_main())


async def _async_main():
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

    if AI_SEARCH_QUERY_USER_ID:
        print(f"AI_SEARCH_QUERY_USER_ID: {AI_SEARCH_QUERY_USER_ID}")
    if AI_SEARCH_QUERY_GROUP_ID:
        print(f"AI_SEARCH_QUERY_GROUP_ID: {AI_SEARCH_QUERY_GROUP_ID}")
    
    # Fetch current user OID and groups from Microsoft Graph
    try:
        current_user_oid, current_user_groups = await get_current_user_info()
    except Exception as e:
        print(f"Warning: Could not fetch current user info from Graph: {e}")
        current_user_oid = None
        current_user_groups = []
    
    documents = get_sample_documents()
    
    # Inject current user OID and groups into every document
    if current_user_oid:
        for doc in documents:
            if current_user_oid not in doc["oid"]:
                doc["oid"].append(current_user_oid)
    for gid in current_user_groups:
        for doc in documents:
            if gid not in doc["group"]:
                doc["group"].append(gid)
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
    print("  - 'oid' field contains user IDs (from current user and AI_SEARCH_QUERY_USER_ID)")
    print("  - 'group' field contains group IDs (from AI_SEARCH_QUERY_GROUP_ID)")
    print("\nDocuments will be filtered based on the user's OBO token when querying")
    print("through the MCP server using the x-ms-query-source-authorization header.")


if __name__ == "__main__":
    main()
