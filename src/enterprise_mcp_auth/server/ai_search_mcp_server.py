"""Azure AI Search MCP Server with OAuth Proxy and OBO authentication.

This module implements an MCP server that exposes Azure AI Search functionality
through MCP tools while enforcing document-level access control using OAuth
tokens and the On-Behalf-Of (OBO) flow.
"""

import os
import json
from typing import Any, Dict, List, Optional
from dotenv import load_dotenv
import msal
from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from fastmcp import FastMCP
from fastmcp.server.auth import OAuthProxy, JWTVerifier

# Load environment variables
load_dotenv()

# Environment variables
AZURE_SEARCH_ENDPOINT = os.getenv("AZURE_SEARCH_ENDPOINT", "")
AZURE_SEARCH_INDEX = os.getenv("AZURE_SEARCH_INDEX", "documents")
AZURE_SEARCH_ADMIN_KEY = os.getenv("AZURE_SEARCH_ADMIN_KEY", "")
AZURE_CLIENT_ID = os.getenv("AZURE_CLIENT_ID", "")
AZURE_CLIENT_SECRET = os.getenv("AZURE_CLIENT_SECRET", "")
AZURE_TENANT_ID = os.getenv("AZURE_TENANT_ID", "")
JWT_ISSUER = os.getenv("JWT_ISSUER", "")
JWT_AUDIENCE = os.getenv("JWT_AUDIENCE", "")

# Derive JWKS URI from issuer (for Azure AD v2.0 tokens)
# Azure AD JWKS URI format: https://login.microsoftonline.com/{tenant}/discovery/v2.0/keys
JWKS_URI = os.getenv("JWKS_URI", "")
if not JWKS_URI and AZURE_TENANT_ID:
    JWKS_URI = f"https://login.microsoftonline.com/{AZURE_TENANT_ID}/discovery/v2.0/keys"

# Initialize FastMCP
mcp = FastMCP(
    "Azure AI Search MCP Server"
)

# Global variables for deferred initialization
jwt_verifier = None
oauth_proxy = None
msal_app = None


def initialize_auth():
    """Initialize authentication components (JWT verifier, OAuth proxy, MSAL app)."""
    global jwt_verifier, oauth_proxy, msal_app
    
    if jwt_verifier is not None:
        return  # Already initialized
    
    # Setup JWT verifier for OAuth Proxy
    if JWKS_URI:
        jwt_verifier = JWTVerifier(
            jwks_uri=JWKS_URI,
            issuer=JWT_ISSUER,
            audience=JWT_AUDIENCE,
        )
        
        # Apply OAuth Proxy authentication
        oauth_proxy = OAuthProxy(jwt_verifier=jwt_verifier)
        mcp.use_auth(oauth_proxy)
    
    # Initialize MSAL confidential client for OBO
    if AZURE_CLIENT_ID and AZURE_TENANT_ID:
        msal_app = msal.ConfidentialClientApplication(
            AZURE_CLIENT_ID,
            authority=f"https://login.microsoftonline.com/{AZURE_TENANT_ID}",
            client_credential=AZURE_CLIENT_SECRET,
        )


def get_obo_token(user_token: str) -> str:
    """Acquire Azure AI Search token using OBO flow.
    
    Args:
        user_token: The user's access token from the incoming request
        
    Returns:
        Access token for Azure AI Search
    """
    initialize_auth()
    
    if msal_app is None:
        raise Exception("MSAL app not initialized. Check AZURE_CLIENT_ID and AZURE_TENANT_ID.")
    
    result = msal_app.acquire_token_on_behalf_of(
        user_assertion=user_token,
        scopes=["https://search.azure.com/.default"],
    )
    
    if "access_token" in result:
        return result["access_token"]
    else:
        error = result.get("error", "unknown_error")
        error_desc = result.get("error_description", "Failed to acquire OBO token")
        raise Exception(f"OBO token acquisition failed: {error} - {error_desc}")


def get_search_client_with_obo(user_token: str) -> SearchClient:
    """Create a SearchClient with OBO token for document-level access control.
    
    Args:
        user_token: The user's access token from the incoming request
        
    Returns:
        SearchClient configured with OBO token
    """
    obo_token = get_obo_token(user_token)
    
    # Create search client with admin key (for connection)
    # But we'll use OBO token in headers for permission filtering
    search_client = SearchClient(
        endpoint=AZURE_SEARCH_ENDPOINT,
        index_name=AZURE_SEARCH_INDEX,
        credential=AzureKeyCredential(AZURE_SEARCH_ADMIN_KEY),
    )
    
    # Store OBO token for use in requests
    search_client._obo_token = obo_token
    
    return search_client


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
    user_token = oauth_proxy.get_current_token()
    
    # Create search client with OBO token
    search_client = get_search_client_with_obo(user_token)
    obo_token = search_client._obo_token
    
    # Perform search with OBO token in header for permission filtering
    results = search_client.search(
        search_text=query,
        top=top,
        headers={
            "x-ms-query-source-authorization": f"Bearer {obo_token}"
        }
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
    user_token = oauth_proxy.get_current_token()
    
    # Create search client with OBO token
    search_client = get_search_client_with_obo(user_token)
    obo_token = search_client._obo_token
    
    # Get document with OBO token in header for permission filtering
    try:
        document = search_client.get_document(
            key=id,
            headers={
                "x-ms-query-source-authorization": f"Bearer {obo_token}"
            }
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
    user_token = oauth_proxy.get_current_token()
    
    # Create search client with OBO token
    search_client = get_search_client_with_obo(user_token)
    obo_token = search_client._obo_token
    
    # Get suggestions with OBO token in header for permission filtering
    results = search_client.suggest(
        search_text=query,
        suggester_name="sg",
        top=top,
        headers={
            "x-ms-query-source-authorization": f"Bearer {obo_token}"
        }
    )
    
    # Convert results to JSON-serializable format
    suggestions = []
    for result in results:
        doc = {k: v for k, v in result.items() if not k.startswith("@")}
        suggestions.append(doc)
    
    return suggestions


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
        "JWT_ISSUER",
        "JWT_AUDIENCE",
    ]
    
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    if missing_vars:
        raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")
    
    # Initialize authentication components
    initialize_auth()
    
    print(f"Starting Azure AI Search MCP Server...")
    print(f"Search Endpoint: {AZURE_SEARCH_ENDPOINT}")
    print(f"Search Index: {AZURE_SEARCH_INDEX}")
    print(f"JWT Issuer: {JWT_ISSUER}")
    print(f"JWT Audience: {JWT_AUDIENCE}")
    print(f"JWKS URI: {JWKS_URI}")
    
    mcp.run(transport="streamable-http")


if __name__ == "__main__":
    main()
