# Enterprise MCP Auth

Enterprise MCP Auth with Azure AI Search MCP server/client and ingestion app.

## Overview

This project implements a Model Context Protocol (MCP) server and client for Azure AI Search with OAuth authentication and document-level permission filtering. It includes:

- **MCP Server**: FastMCP server with OAuth Proxy authentication and On-Behalf-Of (OBO) flow for Azure AI Search
- **MCP Client**: CLI client with device code flow authentication
- **LangGraph ReAct Agent**: Multi-agent client using LangGraph for intelligent document search and retrieval
- **Ingestion Tool**: Creates Azure AI Search index with permission filtering and uploads sample documents

## Features

- ✅ OAuth Proxy authentication with JWT verification
- ✅ On-Behalf-Of (OBO) token flow for Azure AI Search
- ✅ Document-level access control via `x-ms-query-source-authorization` header
- ✅ Three MCP tools: `search_documents`, `get_document`, `suggest`
- ✅ Permission filtering with USER_IDS (`oid` field) and GROUP_IDS (`group` field)
- ✅ Search suggester support
- ✅ LangGraph ReAct agent for intelligent query processing
- ✅ Supervisor graph with identity validation and MCP client management

## Installation

1. Clone the repository:
```bash
git clone https://github.com/denniszielke/enterprise-mcp-auth.git
cd enterprise-mcp-auth
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set up Azure AD applications:

   **Option A: Automated (Recommended)**
   ```bash
   # Create MCP Server app
   ./scripts/create-server-app.sh
   
   # Create MCP Client app
   ./scripts/create-client-app.sh
   ```
   
   See [scripts/README.md](scripts/README.md) for detailed instructions.

   **Option B: Manual**
   - Follow the manual configuration steps in [scripts/README.md](scripts/README.md)

4. Configure environment variables:
```bash
cp .env.example .env
# Edit .env with values from the app registration scripts
```

## Configuration

Edit `.env` file with your Azure credentials:

```env
# Azure Search Configuration
AZURE_SEARCH_ENDPOINT=https://your-search-service.search.windows.net
AZURE_SEARCH_INDEX=documents
AZURE_SEARCH_ADMIN_KEY=your-admin-key

# Azure AD Configuration
AZURE_CLIENT_ID=your-client-id
AZURE_CLIENT_SECRET=your-client-secret
AZURE_TENANT_ID=your-tenant-id

# JWT Configuration (for server)
JWT_ISSUER=https://login.microsoftonline.com/your-tenant-id/v2.0
JWT_AUDIENCE=api://your-client-id

# MCP Client Configuration
MCP_BASE_URL=http://localhost:8000
MCP_SCOPE=api://your-server-client-id/.default

# OpenAI Configuration (for LangGraph agents)
OPENAI_API_KEY=your-openai-api-key
```

## Usage

### 1. Create Index and Ingest Documents

First, create the Azure AI Search index with permission filtering and upload sample documents:

```bash
python -m enterprise_mcp_auth.ingestion.create_index_and_documents
```

This will:
- Create an index named `documents` with permission filtering fields
- Add a suggester named `sg`
- Upload 8 sample documents with various permission settings

### 2. Start the MCP Server

Start the MCP server with OAuth Proxy authentication:

```bash
python -m enterprise_mcp_auth.server.ai_search_mcp_server
```

The server will:
- Listen on port 8000 (default)
- Enforce JWT authentication
- Use OBO flow to acquire Azure AI Search tokens
- Apply document-level permission filtering

### 3. Use the MCP Client

Interact with the MCP server using the CLI client:

```bash
# List available tools
python -m enterprise_mcp_auth.client.ai_search_mcp_client list-tools

# Search documents
python -m enterprise_mcp_auth.client.ai_search_mcp_client search --query "security" --top 5

# Get a specific document
python -m enterprise_mcp_auth.client.ai_search_mcp_client get --id "doc1"

# Get suggestions
python -m enterprise_mcp_auth.client.ai_search_mcp_client suggest --query "sec" --top 5
```

The client will:
- Prompt for device code authentication
- Acquire a token for the MCP server audience
- Execute the requested tool via the MCP server

### 4. Use the LangGraph ReAct Agent

For intelligent query processing with natural language, use the LangGraph ReAct agent:

```bash
# Set PYTHONPATH to include src directory
export PYTHONPATH=/path/to/enterprise-mcp-auth/src:$PYTHONPATH

# Run a query
python -m enterprise_mcp_auth.cli "What documents mention security policies?"

# Use verbose mode to see reasoning steps
python -m enterprise_mcp_auth.cli "Find documents about authentication" --verbose

# Specify a different OpenAI model
python -m enterprise_mcp_auth.cli "Search for compliance documents" --model gpt-4
```

The LangGraph agent will:
- Authenticate using device code flow (or client credentials if `AZURE_CLIENT_SECRET` is set)
- Create a ReAct agent with access to MCP tools
- Process your natural language query
- Automatically call appropriate tools (search, get, suggest)
- Return a comprehensive answer based on retrieved documents

**Example interaction:**

```bash
$ python -m enterprise_mcp_auth.cli "What are the security policies mentioned in the documents?"

🤖 LangGraph ReAct Agent for Azure AI Search
============================================================

🔐 Acquiring access token...
   Tenant: your-tenant-id
   Client: your-client-id
   Scope:  api://your-server-client-id/.default
To sign in, use a web browser to open the page https://microsoft.com/devicelogin and enter the code XXXXXXXXX to authenticate.
✓ Token acquired for user: user@example.com

🔍 Query: What are the security policies mentioned in the documents?
🌐 MCP Server: http://localhost:8000
🤖 Model: gpt-4o-mini

============================================================

📝 Response:

Based on the search results, here are the security policies mentioned in the documents:

1. **Document Security Policy (doc1)**: This document outlines general security guidelines...
2. **Access Control Policy (doc3)**: Details the access control mechanisms...

These documents provide comprehensive security guidelines for the organization.

============================================================
✓ Query completed successfully
```

## Architecture

### Permission Filtering

The system enforces document-level access control through:

1. **Index Fields**:
   - `oid`: Collection of user IDs (USER_IDS permission filter)
   - `group`: Collection of group IDs (GROUP_IDS permission filter)

2. **OBO Token Flow**:
   - Client authenticates with Azure AD
   - MCP server receives client token
   - Server uses OBO to get Azure AI Search token
   - Token contains user/group claims

3. **Query-Time Filtering**:
   - Server sets `x-ms-query-source-authorization` header
   - Azure AI Search filters results based on token claims
   - Only documents matching user's `oid` or `group` are returned

### MCP Tools

1. **search_documents(query: str, top: int = 5)**
   - Full-text search across the index
   - Returns top N matching documents
   - Applies permission filtering

2. **get_document(id: str)**
   - Retrieves a specific document by ID
   - Applies permission filtering
   - Returns document or error if not found/accessible

3. **suggest(query: str, top: int = 5)**
   - Auto-complete suggestions using the `sg` suggester
   - Returns top N suggestions
   - Applies permission filtering

## Security

- OAuth 2.0 authentication required for all operations
- JWT token verification on MCP server
- On-Behalf-Of flow ensures user context is preserved
- Document-level access control enforced by Azure AI Search
- No direct admin key exposure to clients

## Development

### Project Structure

```
src/enterprise_mcp_auth/
├── __init__.py
├── cli.py                    # LangGraph ReAct agent CLI
├── server/
│   ├── __init__.py
│   ├── __main__.py
│   └── ai_search_mcp_server.py
├── client/
│   ├── __init__.py
│   ├── __main__.py
│   ├── ai_search_mcp_client.py  # Basic MCP client
│   ├── auth.py                   # MSAL authentication (device code + confidential)
│   └── mcp_client.py            # Authenticated MCP client wrapper
├── agents/
│   ├── __init__.py
│   ├── state.py                 # Graph state definitions
│   ├── tools.py                 # LangChain tool wrappers
│   ├── react_agent.py           # ReAct agent implementation
│   └── supervisor.py            # Supervisor graph
└── ingestion/
    ├── __init__.py
    ├── __main__.py
    └── create_index_and_documents.py
```

### Requirements

- Python 3.8+
- fastmcp==2.14.5
- msal>=1.31.0
- azure-search-documents>=11.6.0
- azure-core>=1.32.0
- python-dotenv>=1.0.0
- langgraph>=0.2.0
- langchain-openai>=0.2.0
- langchain-core>=0.3.0
- click>=8.1.0
- requests>=2.31.0

### LangGraph Architecture

The LangGraph ReAct agent implementation follows this architecture:

```
User Query
    ↓
Supervisor Graph
    ↓
1. Identity Validation
   - Check identity context exists
   - Validate access token
    ↓
2. ReAct Agent Node
   - Create authenticated MCP client
   - Initialize ReAct agent with MCP tools
   - Process query using reasoning + action loop
    ↓
3. Tool Execution
   - search_documents: Search index
   - get_document: Retrieve by ID
   - suggest: Get suggestions
    ↓
Response
```

**Key Components:**

- **IdentityContext**: Carries user identity and access token through the graph
- **AgentState**: Complete state including messages, identity, query, and MCP URL
- **MCPTools**: LangChain tool wrappers for MCP server tools
- **ReAct Agent**: Uses LangGraph's `create_react_agent` with OpenAI LLM
- **Supervisor**: Orchestrates identity validation and agent execution

## License

MIT
