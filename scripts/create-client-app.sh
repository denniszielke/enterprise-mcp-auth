#!/bin/bash

# Script to create and register Azure AD (Entra ID) application for MCP Client
# This script creates a public client application for device code flow authentication
# It requires the MCP Server app to be created first to set up API permissions

set -e

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo "=========================================="
echo "MCP Client Entra App Registration"
echo "=========================================="
echo ""

# Check if Azure CLI is installed
if ! command -v az &> /dev/null; then
    echo -e "${RED}Error: Azure CLI is not installed. Please install it first.${NC}"
    echo "Visit: https://docs.microsoft.com/en-us/cli/azure/install-azure-cli"
    exit 1
fi

# Check if user is logged in
if ! az account show &> /dev/null; then
    echo -e "${YELLOW}Not logged in to Azure. Initiating login...${NC}"
    az login
fi

# Get tenant ID
AZURE_TENANT_ID=$(az account show --query tenantId -o tsv)
echo -e "${GREEN}Using Tenant ID: ${AZURE_TENANT_ID}${NC}"
echo ""

# Prompt for MCP Server Client ID
echo -e "${BLUE}This script requires the MCP Server app to be created first.${NC}"
echo -e "${BLUE}Run ./create-server-app.sh if you haven't done so already.${NC}"
echo ""
read -p "Enter MCP Server Client ID: " SERVER_CLIENT_ID

if [ -z "$SERVER_CLIENT_ID" ]; then
    echo -e "${RED}Error: MCP Server Client ID is required.${NC}"
    exit 1
fi

# Validate server app exists
if ! az ad app show --id ${SERVER_CLIENT_ID} &> /dev/null; then
    echo -e "${RED}Error: MCP Server app with Client ID ${SERVER_CLIENT_ID} not found.${NC}"
    echo "Please run ./create-server-app.sh first."
    exit 1
fi

echo -e "${GREEN}✓ MCP Server app found${NC}"
echo ""

# Prompt for application name
read -p "Enter MCP Client App Name (default: mcp-client): " APP_NAME
APP_NAME=${APP_NAME:-mcp-client}

echo ""
echo "Creating MCP Client application: ${APP_NAME}..."

# Create the application as a public client
APP_JSON=$(az ad app create \
    --display-name "${APP_NAME}" \
    --sign-in-audience AzureADMyOrg \
    --public-client-redirect-uris "http://localhost")

CLIENT_ID=$(echo $APP_JSON | jq -r '.appId')
APP_OBJECT_ID=$(echo $APP_JSON | jq -r '.id')

echo -e "${GREEN}✓ Application created${NC}"
echo "  Client ID: ${CLIENT_ID}"
echo "  Object ID: ${APP_OBJECT_ID}"
echo ""

# Update accessTokenAcceptedVersion to 2
echo "Updating accessTokenAcceptedVersion to 2..."
az ad app update --id ${CLIENT_ID} --set api.requestedAccessTokenVersion=2
echo -e "${GREEN}✓ Access token version updated to 2${NC}"
echo ""

# Enable public client flow
echo "Enabling public client flow..."
# Note: publicClient.redirectUris is already set by --public-client-redirect-uris in create command
az ad app update --id ${CLIENT_ID} --set isFallbackPublicClient=true

echo -e "${GREEN}✓ Public client flow enabled${NC}"
echo ""

# Create service principal
echo "Creating service principal..."
SP_JSON=$(az ad sp create --id ${CLIENT_ID})
SP_OBJECT_ID=$(echo $SP_JSON | jq -r '.id')
echo -e "${GREEN}✓ Service principal created${NC}"
echo "  Service Principal Object ID: ${SP_OBJECT_ID}"
echo ""

# Add API permissions to access MCP Server
echo "Adding API permissions for MCP Server..."

# Get the MCP Server's exposed API scope
SERVER_APP_JSON=$(az ad app show --id ${SERVER_CLIENT_ID})
SERVER_APP_ID_URI=$(echo $SERVER_APP_JSON | jq -r '.identifierUris[0]')
SERVER_OAUTH2_SCOPES=$(echo $SERVER_APP_JSON | jq -r '.api.oauth2PermissionScopes[0].id')

if [ -z "$SERVER_OAUTH2_SCOPES" ] || [ "$SERVER_OAUTH2_SCOPES" = "null" ]; then
    echo -e "${YELLOW}⚠ Warning: No OAuth2 scopes found on MCP Server app.${NC}"
    echo -e "${YELLOW}  Make sure the server app exposes an API.${NC}"
else
    # Add delegated permission to access MCP Server
    az ad app permission add \
        --id ${CLIENT_ID} \
        --api ${SERVER_CLIENT_ID} \
        --api-permissions ${SERVER_OAUTH2_SCOPES}=Scope

    echo -e "${GREEN}✓ MCP Server API permissions added${NC}"
    echo "  Scope: ${SERVER_APP_ID_URI}/user_impersonation"
fi
echo ""

# Grant admin consent (optional for delegated permissions in device code flow)
echo "Granting admin consent for API permissions..."
echo -e "${YELLOW}Note: Admin consent is optional for public client apps using device code flow.${NC}"

# Try to grant admin consent
if az ad app permission admin-consent --id ${CLIENT_ID} 2>/dev/null; then
    echo -e "${GREEN}✓ Admin consent granted${NC}"
else
    echo -e "${YELLOW}⚠ Unable to grant admin consent automatically.${NC}"
    echo -e "${YELLOW}  Users will be prompted for consent during authentication.${NC}"
fi
echo ""

# Generate configuration
MCP_SERVER_AUDIENCE="${SERVER_APP_ID_URI}/.default"

# Output configuration
echo "=========================================="
echo "MCP Client App Registration Complete!"
echo "=========================================="
echo ""
echo "Add/update the following in your .env file:"
echo ""
echo "# Azure AD Configuration (use same tenant)"
echo "MCP_CLIENT_APP_ID=${CLIENT_ID}"
echo "AZURE_TENANT_ID=${AZURE_TENANT_ID}"
echo ""
echo "# MCP Server Configuration"
echo "MCP_SERVER_URL=http://localhost:8000"
echo "MCP_SERVER_AUDIENCE=${MCP_SERVER_AUDIENCE}"
echo ""
echo "=========================================="
echo ""
echo -e "${BLUE}Note: This is a public client app - no secret is required.${NC}"
echo ""
echo "Next steps:"
echo "1. Update your .env file with the values above"
echo "2. Ensure the MCP server is configured with the same AZURE_TENANT_ID"
echo "3. Start the MCP server: python -m enterprise_mcp_auth.server.ai_search_mcp_server"
echo "4. Run the client: python -m enterprise_mcp_auth.client.ai_search_mcp_client search --query \"test\""
echo ""
echo "The client will use device code flow for authentication."
echo ""
