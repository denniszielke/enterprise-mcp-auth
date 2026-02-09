# Azure AD (Entra ID) App Registration Scripts

This directory contains bash scripts to automate the creation and configuration of Azure AD applications for the Enterprise MCP Auth system.

## Prerequisites

- Azure CLI installed and configured
- Appropriate permissions to create Azure AD applications
- `jq` command-line JSON processor installed

### Install Prerequisites

**Azure CLI:**
```bash
# macOS
brew install azure-cli

# Linux
curl -sL https://aka.ms/InstallAzureCLIDeb | sudo bash

# Windows
# Download from https://aka.ms/installazurecliwindows
```

**jq:**
```bash
# macOS
brew install jq

# Linux (Ubuntu/Debian)
sudo apt-get install jq

# Linux (RHEL/CentOS)
sudo yum install jq
```

## Scripts

### 1. create-server-app.sh

Creates and configures the MCP Server Azure AD application (confidential client).

**What it does:**
- Creates an Azure AD app registration
- Generates a client secret
- Exposes an API with `user_impersonation` scope
- Adds required API permissions for Azure AI Search
- Attempts to grant admin consent

**Usage:**
```bash
./scripts/create-server-app.sh
```

**Outputs:**
- `AZURE_CLIENT_ID` - Server app client ID
- `AZURE_CLIENT_SECRET` - Server app secret (save immediately!)
- `AZURE_TENANT_ID` - Your Azure AD tenant ID
- `JWT_ISSUER` - JWT token issuer URL
- `JWT_AUDIENCE` - JWT token audience (API URI)
- `MCP_SERVER_AUDIENCE` - Scope for client to request

### 2. create-client-app.sh

Creates and configures the MCP Client Azure AD application (public client).

**What it does:**
- Creates an Azure AD app registration as a public client
- Enables device code flow (public client)
- Adds API permissions to access the MCP Server
- Attempts to grant admin consent (optional for public clients)

**Prerequisites:**
- MCP Server app must be created first (run `create-server-app.sh`)
- You'll need the server's Client ID

**Usage:**
```bash
./scripts/create-client-app.sh
```

**Outputs:**
- `AZURE_CLIENT_ID` - Client app client ID (different from server)
- `AZURE_TENANT_ID` - Your Azure AD tenant ID (same as server)
- `MCP_SERVER_URL` - MCP server endpoint URL
- `MCP_SERVER_AUDIENCE` - Server API scope to request

## Complete Setup Workflow

### Step 1: Create Server App
```bash
./scripts/create-server-app.sh
```

When prompted:
- Enter a name for the server app (default: `mcp-server`)
- Save the generated `AZURE_CLIENT_SECRET` immediately (cannot be retrieved later)

### Step 2: Update .env for Server
Copy the output values to your `.env` file:
```bash
# Azure AD Configuration
AZURE_CLIENT_ID=<server-client-id>
AZURE_CLIENT_SECRET=<server-secret>
AZURE_TENANT_ID=<tenant-id>

# JWT Configuration (for server)
JWT_ISSUER=https://login.microsoftonline.com/<tenant-id>/v2.0
JWT_AUDIENCE=api://<server-client-id>

# Azure Search Configuration (add your values)
AZURE_SEARCH_ENDPOINT=https://your-search-service.search.windows.net
AZURE_SEARCH_INDEX=documents
AZURE_SEARCH_ADMIN_KEY=your-admin-key
```

### Step 3: Create Client App
```bash
./scripts/create-client-app.sh
```

When prompted:
- Enter the MCP Server Client ID (from step 1)
- Enter a name for the client app (default: `mcp-client`)

### Step 4: Update .env for Client
Add the client values to your `.env` file:
```bash
# MCP Client uses a different AZURE_CLIENT_ID
# (For testing, you can create a separate .env.client file)
AZURE_CLIENT_ID=<client-client-id>
AZURE_TENANT_ID=<tenant-id>

# MCP Server Configuration
MCP_SERVER_URL=http://localhost:8000
MCP_SERVER_AUDIENCE=api://<server-client-id>/.default
```

### Step 5: Verify Setup
Start the server and test with the client:
```bash
# Terminal 1: Start server
python -m enterprise_mcp_auth.server.ai_search_mcp_server

# Terminal 2: Test client
python -m enterprise_mcp_auth.client.ai_search_mcp_client search --query "test"
```

## Environment Variables Reference

The scripts generate values for these environment variables used across all tools:

| Variable | Used By | Description |
|----------|---------|-------------|
| `AZURE_CLIENT_ID` | Server & Client | App registration client ID (different for each) |
| `AZURE_CLIENT_SECRET` | Server only | Confidential client secret |
| `AZURE_TENANT_ID` | Server & Client | Azure AD tenant ID (same for both) |
| `JWT_ISSUER` | Server | Token issuer URL |
| `JWT_AUDIENCE` | Server | Expected token audience (API URI) |
| `MCP_SERVER_URL` | Client | MCP server endpoint |
| `MCP_SERVER_AUDIENCE` | Client | Scope to request from server |

## Troubleshooting

### Admin Consent Required
If admin consent cannot be granted automatically:
1. Go to Azure Portal → Azure Active Directory → App registrations
2. Select your app
3. Go to "API permissions"
4. Click "Grant admin consent for [Your Tenant]"

### Client Cannot Authenticate
Verify:
- Both apps are in the same tenant
- Server app has exposed API with `user_impersonation` scope
- Client app has been granted permission to access server API
- `MCP_SERVER_AUDIENCE` matches the server's API URI + `/.default`

### Permission Denied Errors
Ensure:
- Admin consent has been granted for both apps
- User account has necessary permissions in Azure AD
- Azure AI Search permissions are granted to the server app

## Manual Configuration

If you prefer to configure manually via Azure Portal:

### Server App
1. Azure Portal → Azure Active Directory → App registrations → New registration
2. Set as "Web" app type
3. Generate client secret under "Certificates & secrets"
4. Expose API under "Expose an API"
5. Add scope: `user_impersonation`
6. Add API permissions: Azure AI Search → user_impersonation

### Client App
1. Azure Portal → Azure Active Directory → App registrations → New registration
2. Set as "Public client/native"
3. Enable "Allow public client flows"
4. Add API permissions: Select your MCP Server app → user_impersonation
5. No secret needed (public client)

## Security Notes

- **Never commit** the `.env` file or client secrets to source control
- Store secrets in Azure Key Vault for production deployments
- Rotate client secrets regularly
- Use managed identities when possible for Azure resources
- Grant minimum necessary permissions (least privilege principle)

## Additional Resources

- [Azure AD app registration docs](https://docs.microsoft.com/en-us/azure/active-directory/develop/quickstart-register-app)
- [OAuth 2.0 On-Behalf-Of flow](https://docs.microsoft.com/en-us/azure/active-directory/develop/v2-oauth2-on-behalf-of-flow)
- [Azure CLI reference](https://docs.microsoft.com/en-us/cli/azure/ad/app)
