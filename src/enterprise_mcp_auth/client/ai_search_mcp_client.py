"""Azure AI Search MCP Client with device code flow authentication.

This module implements a CLI client that authenticates using device code flow
and connects to the Azure AI Search MCP server.
"""

import os
import sys
import argparse
import asyncio
from typing import Optional
from dotenv import load_dotenv
import msal
from fastmcp import Client
from fastmcp.client.transports import StreamableHttpTransport

# Load environment variables
load_dotenv()

# Environment variables
AZURE_CLIENT_ID = os.getenv("AZURE_CLIENT_ID", "")
AZURE_TENANT_ID = os.getenv("AZURE_TENANT_ID", "")
MCP_SERVER_URL = os.getenv("MCP_SERVER_URL", "http://localhost:8000")
MCP_SERVER_AUDIENCE = os.getenv("MCP_SERVER_AUDIENCE", "")


def acquire_token_via_device_code(client_id: str, tenant_id: str, scopes: list) -> str:
    """Acquire access token using device code flow.
    
    Args:
        client_id: Azure AD client ID
        tenant_id: Azure AD tenant ID
        scopes: List of OAuth scopes to request
        
    Returns:
        Access token string
    """
    app = msal.PublicClientApplication(
        client_id,
        authority=f"https://login.microsoftonline.com/{tenant_id}",
    )
    
    # Check if we have a cached token
    accounts = app.get_accounts()
    if accounts:
        result = app.acquire_token_silent(scopes, account=accounts[0])
        if result and "access_token" in result:
            print("Token acquired from cache")
            return result["access_token"]
    
    # Initiate device code flow
    flow = app.initiate_device_flow(scopes=scopes)
    
    if "user_code" not in flow:
        raise ValueError(
            f"Failed to create device flow: {flow.get('error_description', 'Unknown error')}"
        )
    
    print(flow["message"])
    sys.stdout.flush()
    
    # Wait for the user to authenticate
    result = app.acquire_token_by_device_flow(flow)
    
    if "access_token" in result:
        print("Authentication successful!")
        return result["access_token"]
    else:
        error = result.get("error", "unknown_error")
        error_desc = result.get("error_description", "Failed to acquire token")
        raise Exception(f"Authentication failed: {error} - {error_desc}")


async def search_documents_command(client: Client, query: str, top: int):
    """Execute search_documents tool."""
    print(f"\n🔍 Searching for: '{query}' (top {top} results)")
    print("-" * 60)
    
    try:
        result = await client.call_tool("search_documents", query=query, top=top)
        
        if not result:
            print("No results found.")
            return
        
        for i, doc in enumerate(result, 1):
            print(f"\nResult {i}:")
            for key, value in doc.items():
                print(f"  {key}: {value}")
    except Exception as e:
        print(f"Error: {e}")


async def get_document_command(client: Client, doc_id: str):
    """Execute get_document tool."""
    print(f"\n📄 Getting document with ID: '{doc_id}'")
    print("-" * 60)
    
    try:
        result = await client.call_tool("get_document", id=doc_id)
        
        if "error" in result:
            print(f"Error: {result['error']}")
            return
        
        print("\nDocument:")
        for key, value in result.items():
            print(f"  {key}: {value}")
    except Exception as e:
        print(f"Error: {e}")


async def suggest_command(client: Client, query: str, top: int):
    """Execute suggest tool."""
    print(f"\n💡 Getting suggestions for: '{query}' (top {top} results)")
    print("-" * 60)
    
    try:
        result = await client.call_tool("suggest", query=query, top=top)
        
        if not result:
            print("No suggestions found.")
            return
        
        for i, doc in enumerate(result, 1):
            print(f"\nSuggestion {i}:")
            for key, value in doc.items():
                print(f"  {key}: {value}")
    except Exception as e:
        print(f"Error: {e}")


async def list_tools_command(client: Client):
    """List available tools."""
    print("\n🛠️  Available Tools:")
    print("-" * 60)
    
    try:
        tools = await client.list_tools()
        
        for tool in tools:
            print(f"\n• {tool.name}")
            if hasattr(tool, 'description') and tool.description:
                print(f"  {tool.description}")
            if hasattr(tool, 'inputSchema') and tool.inputSchema:
                schema = tool.inputSchema
                if 'properties' in schema:
                    print("  Parameters:")
                    for param_name, param_info in schema['properties'].items():
                        param_type = param_info.get('type', 'any')
                        param_desc = param_info.get('description', '')
                        print(f"    - {param_name} ({param_type}): {param_desc}")
    except Exception as e:
        print(f"Error: {e}")


async def run_client(token: str, command: str, **kwargs):
    """Run the MCP client with specified command."""
    # Create transport with authentication
    transport = StreamableHttpTransport(
        url=MCP_SERVER_URL,
        headers={"Authorization": f"Bearer {token}"}
    )
    
    # Create client
    async with Client(transport=transport) as client:
        if command == "search":
            await search_documents_command(client, kwargs.get("query"), kwargs.get("top", 5))
        elif command == "get":
            await get_document_command(client, kwargs.get("id"))
        elif command == "suggest":
            await suggest_command(client, kwargs.get("query"), kwargs.get("top", 5))
        elif command == "list-tools":
            await list_tools_command(client)
        else:
            print(f"Unknown command: {command}")
            sys.exit(1)


def main():
    """Main entry point for the MCP client CLI."""
    parser = argparse.ArgumentParser(
        description="Azure AI Search MCP Client",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # List available tools
  python -m enterprise_mcp_auth.client.ai_search_mcp_client list-tools
  
  # Search documents
  python -m enterprise_mcp_auth.client.ai_search_mcp_client search --query "security" --top 5
  
  # Get a specific document
  python -m enterprise_mcp_auth.client.ai_search_mcp_client get --id "doc1"
  
  # Get suggestions
  python -m enterprise_mcp_auth.client.ai_search_mcp_client suggest --query "sec" --top 5
        """
    )
    
    parser.add_argument(
        "command",
        choices=["search", "get", "suggest", "list-tools"],
        help="Command to execute"
    )
    parser.add_argument(
        "--query",
        help="Search query or suggestion query"
    )
    parser.add_argument(
        "--id",
        help="Document ID for get command"
    )
    parser.add_argument(
        "--top",
        type=int,
        default=5,
        help="Maximum number of results (default: 5)"
    )
    parser.add_argument(
        "--server-url",
        default=os.getenv("MCP_SERVER_URL", "http://localhost:8000"),
        help="MCP server URL"
    )
    
    args = parser.parse_args()
    
    # Validate command-specific arguments
    if args.command == "search" and not args.query:
        parser.error("--query is required for search command")
    if args.command == "get" and not args.id:
        parser.error("--id is required for get command")
    if args.command == "suggest" and not args.query:
        parser.error("--query is required for suggest command")
    
    # Validate required environment variables
    if not AZURE_CLIENT_ID:
        print("Error: AZURE_CLIENT_ID environment variable is required")
        sys.exit(1)
    if not AZURE_TENANT_ID:
        print("Error: AZURE_TENANT_ID environment variable is required")
        sys.exit(1)
    
    # Determine scope
    if MCP_SERVER_AUDIENCE:
        scopes = [MCP_SERVER_AUDIENCE]
    else:
        # Default scope pattern
        scopes = [f"api://{AZURE_CLIENT_ID}/.default"]
    
    print(f"Authenticating to Azure AD...")
    print(f"Client ID: {AZURE_CLIENT_ID}")
    print(f"Tenant ID: {AZURE_TENANT_ID}")
    print(f"Scope: {scopes[0]}")
    
    # Acquire token via device code flow
    try:
        token = acquire_token_via_device_code(AZURE_CLIENT_ID, AZURE_TENANT_ID, scopes)
    except Exception as e:
        print(f"Authentication failed: {e}")
        sys.exit(1)
    
    # Update server URL if provided via argument
    global MCP_SERVER_URL
    MCP_SERVER_URL = args.server_url
    
    print(f"\nConnecting to MCP server at {MCP_SERVER_URL}...")
    
    # Run the client
    try:
        asyncio.run(run_client(
            token=token,
            command=args.command,
            query=args.query,
            id=args.id,
            top=args.top
        ))
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
