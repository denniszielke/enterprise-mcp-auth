"""Azure AI Search MCP Server with AzureProvider and OBO authentication.

This module implements an MCP server that exposes Azure AI Search functionality
through MCP tools while enforcing document-level access control using OAuth
tokens and the On-Behalf-Of (OBO) flow.
"""

import os
import json
import base64
import logging
from typing import Any, Dict, List, Optional
from dotenv import load_dotenv
import msal
from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from fastmcp import FastMCP
from fastmcp.server.auth.providers.azure import AzureProvider
from fastmcp.server.dependencies import get_access_token

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)
logging.getLogger('azure.core.pipeline.policies.http_logging_policy').setLevel(logging.WARNING)

# Load environment variables
load_dotenv()

# Environment variables
AZURE_SEARCH_ENDPOINT = os.getenv("AZURE_SEARCH_ENDPOINT", "")
AZURE_SEARCH_INDEX = os.getenv("AZURE_SEARCH_INDEX", "documents")
AZURE_SEARCH_ADMIN_KEY = os.getenv("AZURE_SEARCH_ADMIN_KEY", "")
AZURE_CLIENT_ID = os.getenv("AZURE_CLIENT_ID", "")
AZURE_CLIENT_SECRET = os.getenv("AZURE_CLIENT_SECRET", "")
AZURE_TENANT_ID = os.getenv("AZURE_TENANT_ID", "")

# Initialize Auth via AzureProvider
auth_provider = None

if AZURE_CLIENT_ID and AZURE_TENANT_ID and AZURE_CLIENT_SECRET:
    logger.info(f"Configuring AzureProvider:")
    logger.info(f"  Tenant ID: {AZURE_TENANT_ID}")
    logger.info(f"  Client ID: {AZURE_CLIENT_ID}")
    
    auth_provider = AzureProvider(
        client_id=AZURE_CLIENT_ID,
        client_secret=AZURE_CLIENT_SECRET,
        tenant_id=AZURE_TENANT_ID,
        base_url=os.getenv("MCP_SERVER_PUBLIC_URL", "http://localhost:8000"),
        required_scopes=["user_impersonation"],
    )

# Initialize FastMCP
mcp = FastMCP(
    "Azure AI Search MCP Server",
    auth=auth_provider,
)

# Global variables for deferred initialization
msal_app = None


def initialize_msal():
    """Initialize MSAL app for OBO flow."""
    global msal_app
    
    if msal_app is not None:
        return  # Already initialized

    # Initialize MSAL confidential client for OBO
    if AZURE_CLIENT_ID and AZURE_TENANT_ID:
        msal_app = msal.ConfidentialClientApplication(
            AZURE_CLIENT_ID,
            authority=f"https://login.microsoftonline.com/{AZURE_TENANT_ID}",
            client_credential=AZURE_CLIENT_SECRET,
        )


def decode_jwt_payload(token: str) -> dict:
    """Decode JWT payload without verification (for logging only)."""
    try:
        parts = token.split('.')
        if len(parts) != 3:
            return {}
        
        # Add padding if needed
        payload = parts[1]
        padding = 4 - len(payload) % 4
        if padding != 4:
            payload += '=' * padding
        
        decoded = base64.urlsafe_b64decode(payload)
        return json.loads(decoded)
    except Exception as e:
        logger.error(f"Failed to decode JWT: {e}")
        return {}


def get_obo_token(user_token: str) -> str:
    """Acquire Azure AI Search token using OBO flow.
    
    Args:
        user_token: The user's access token from the incoming request
        
    Returns:
        Access token for Azure AI Search
    """
    initialize_msal()
    
    if msal_app is None:
        raise Exception("MSAL app not initialized. Check AZURE_CLIENT_ID and AZURE_TENANT_ID.")
    
    # Log token details for debugging
    token_claims = decode_jwt_payload(user_token)
    logger.info("=== OBO Token Exchange ===")
    logger.info(f"User token claims:")
    logger.info(f"  iss: {token_claims.get('iss', 'N/A')}")
    logger.info(f"  aud: {token_claims.get('aud', 'N/A')}")
    logger.info(f"  oid: {token_claims.get('oid', 'N/A')}")
    logger.info(f"  scp: {token_claims.get('scp', 'N/A')}")
    logger.info(f"  azp: {token_claims.get('azp', 'N/A')}")
    
    logger.info(f"Requesting OBO token for Azure AI Search...")
    logger.info(f"  Scopes: https://search.azure.com/.default")
    
    result = msal_app.acquire_token_on_behalf_of(
        user_assertion=user_token,
        scopes=["https://search.azure.com/.default"],
    )
    
    if "access_token" in result:
        obo_claims = decode_jwt_payload(result["access_token"])
        logger.info("OBO token acquired successfully!")
        logger.info(f"OBO token claims:")
        logger.info(f"  iss: {obo_claims.get('iss', 'N/A')}")
        logger.info(f"  aud: {obo_claims.get('aud', 'N/A')}")
        logger.info(f"  oid: {obo_claims.get('oid', 'N/A')}")
        return result["access_token"]
    else:
        error = result.get("error", "unknown_error")
        error_desc = result.get("error_description", "Failed to acquire OBO token")
        logger.error(f"OBO token acquisition failed!")
        logger.error(f"  Error: {error}")
        logger.error(f"  Description: {error_desc}")
        logger.error(f"  Full result: {json.dumps(result, indent=2)}")
        raise Exception(f"OBO token acquisition failed: {error}: {error_desc}")


def get_search_client_with_obo(user_token: str) -> tuple[SearchClient, str]:
    """Create a SearchClient with OBO token for document-level access control.
    
    Args:
        user_token: The user's access token from the incoming request
        
    Returns:
        Tuple of (SearchClient, OBO token string)
    """
    obo_token = get_obo_token(user_token)
    
    # Use admin key credential for the SearchClient, and pass the OBO token
    # via x_ms_query_source_authorization to enforce document-level ACLs.
    search_client = SearchClient(
        endpoint=AZURE_SEARCH_ENDPOINT,
        index_name=AZURE_SEARCH_INDEX,
        credential=AzureKeyCredential(AZURE_SEARCH_ADMIN_KEY),
    )
    
    return search_client, obo_token


@mcp.tool()
async def search_documents(query: str, top: int = 5) -> List[Dict[str, Any]]:
    """Search documents in Azure AI Search with permission filtering.
    
    This tool searches the Azure AI Search index and enforces document-level
    access control using the user's OBO token.
    
    Args:
        query: Search query string
        top: Maximum number of results to return (default: 5)
        
    Returns:
        List of matching documents with their fields
    """
    # Get user token from OAuth context
    access_token = get_access_token()
    if not access_token:
        return [{"error": "Not authenticated"}]
    user_token = access_token.token
    
    # Create search client with OBO token
    search_client, obo_token = get_search_client_with_obo(user_token)
    
    # Perform search with OBO token for permission filtering
    results = search_client.search(
        search_text=query,
        top=top,
        x_ms_query_source_authorization=obo_token,
    )
    
    # Convert results to JSON-serializable format
    documents = []
    for result in results:
        doc = {k: v for k, v in result.items() if not k.startswith("@")}
        documents.append(doc)
    
    return documents


@mcp.tool()
async def get_document(id: str) -> Dict[str, Any]:
    """Get a specific document by ID with permission filtering.
    
    This tool retrieves a document by its ID and enforces document-level
    access control using the user's OBO token.
    
    Args:
        id: Document ID (key field)
        
    Returns:
        Document fields as a dictionary
    """
    # Get user token from OAuth context
    access_token = get_access_token()
    if not access_token:
        return {"error": "Not authenticated"}
    user_token = access_token.token
    
    # Create search client with OBO token
    search_client, obo_token = get_search_client_with_obo(user_token)
    
    # Get document with OBO token for permission filtering
    try:
        document = search_client.get_document(
            key=id,
            x_ms_query_source_authorization=obo_token,
        )
        
        # Convert to JSON-serializable format
        return {k: v for k, v in document.items() if not k.startswith("@")}
    except Exception as e:
        return {"error": str(e), "id": id}


@mcp.tool()
async def suggest(query: str, top: int = 5) -> List[Dict[str, Any]]:
    """Get search suggestions using the 'sg' suggester with permission filtering.
    
    This tool provides search suggestions based on the query and enforces
    document-level access control using the user's OBO token.
    
    Args:
        query: Query text for suggestions
        top: Maximum number of suggestions to return (default: 5)
        
    Returns:
        List of suggested documents with their fields
    """
    # Get user token from OAuth context
    access_token = get_access_token()
    if not access_token:
        return [{"error": "Not authenticated"}]
    user_token = access_token.token
    
    # Create search client with OBO token
    search_client, obo_token = get_search_client_with_obo(user_token)
    
    # Get suggestions with OBO token for permission filtering
    results = search_client.suggest(
        search_text=query,
        suggester_name="sg",
        top=top,
        x_ms_query_source_authorization=obo_token,
    )
    
    # Convert results to JSON-serializable format
    suggestions = []
    for result in results:
        doc = {k: v for k, v in result.items() if not k.startswith("@")}
        suggestions.append(doc)
    
    return suggestions


@mcp.tool()
async def get_user_info() -> dict:
    """Returns information about the authenticated Azure user."""
    token = get_access_token()
    if not token:
        return {"error": "Not authenticated"}
    return {
        "azure_id": token.claims.get("sub"),
        "email": token.claims.get("email"),
        "name": token.claims.get("name"),
        "job_title": token.claims.get("job_title"),
        "office_location": token.claims.get("office_location"),
    }


def main():
    """Run the MCP server."""
    # Validate required environment variables
    required_vars = [
        "AZURE_SEARCH_ENDPOINT",
        "AZURE_SEARCH_INDEX",
        "AZURE_SEARCH_ADMIN_KEY",
        "AZURE_CLIENT_ID",
        "AZURE_CLIENT_SECRET",
        "AZURE_TENANT_ID",
    ]
    
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    if missing_vars:
        raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")
    
    # Initialize authentication components
    initialize_msal()
    
    logger.info("=" * 80)
    logger.info("Starting Azure AI Search MCP Server")
    logger.info("=" * 80)
    logger.info(f"Search Endpoint: {AZURE_SEARCH_ENDPOINT}")
    logger.info(f"Search Index: {AZURE_SEARCH_INDEX}")
    logger.info(f"Azure Client ID: {AZURE_CLIENT_ID}")
    logger.info(f"Azure Tenant ID: {AZURE_TENANT_ID}")
    logger.info("=" * 80)
    
    print(f"Starting Azure AI Search MCP Server...")
    print(f"Search Endpoint: {AZURE_SEARCH_ENDPOINT}")
    print(f"Search Index: {AZURE_SEARCH_INDEX}")
    
    mcp.run(transport="streamable-http")


if __name__ == "__main__":
    main()
