#!/bin/bash

# Script to create and register Azure AD (Entra ID) application for MCP Server
# This script creates a confidential client application with:
# - Client secret for authentication
# - Exposed API with default scope
# - Required API permissions for Azure AI Search

set -e

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "=========================================="
echo "MCP Server Entra App Registration"
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

# Get subscription ID
SUBSCRIPTION_ID=$(az account show --query id -o tsv)
echo -e "${GREEN}Using Subscription ID: ${SUBSCRIPTION_ID}${NC}"
echo ""

# Prompt for application name
read -p "Enter MCP Server App Name (default: mcp-server): " APP_NAME
APP_NAME=${APP_NAME:-mcp-server}

echo ""
echo "Creating MCP Server application: ${APP_NAME}..."

# Create the application with web redirect URI for OAuth callback
APP_JSON=$(az ad app create \
    --display-name "${APP_NAME}" \
    --sign-in-audience AzureADMyOrg \
    --web-redirect-uris "http://localhost:8000/auth/callback")

AZURE_CLIENT_ID=$(echo $APP_JSON | jq -r '.appId')
APP_OBJECT_ID=$(echo $APP_JSON | jq -r '.id')

echo -e "${GREEN}✓ Application created${NC}"
echo "  Client ID: ${AZURE_CLIENT_ID}"
echo "  Object ID: ${APP_OBJECT_ID}"
echo ""

# Update accessTokenAcceptedVersion to 2
echo "Updating accessTokenAcceptedVersion to 2..."
az ad app update --id ${AZURE_CLIENT_ID} --set api.requestedAccessTokenVersion=2
echo -e "${GREEN}✓ Access token version updated to 2${NC}"
echo ""

# Create service principal
echo "Creating service principal..."
SP_JSON=$(az ad sp create --id ${AZURE_CLIENT_ID})
SP_OBJECT_ID=$(echo $SP_JSON | jq -r '.id')
echo -e "${GREEN}✓ Service principal created${NC}"
echo "  Service Principal Object ID: ${SP_OBJECT_ID}"
echo ""

# Create client secret
echo "Creating client secret..."
SECRET_JSON=$(az ad app credential reset \
    --id ${AZURE_CLIENT_ID} \
    --append \
    --display-name "MCP Server Secret")
AZURE_CLIENT_SECRET=$(echo $SECRET_JSON | jq -r '.password')
echo -e "${GREEN}✓ Client secret created${NC}"
echo -e "${YELLOW}  Secret will be displayed at the end. Make sure to save it!${NC}"
echo ""

# Expose an API with default scope
echo "Exposing API with default scope..."

# Set Application ID URI
APP_ID_URI="api://${AZURE_CLIENT_ID}"
az ad app update --id ${AZURE_CLIENT_ID} --identifier-uris ${APP_ID_URI}

# Define the default scope
OAUTH2_PERMISSIONS=$(cat <<EOF
[
  {
    "adminConsentDescription": "Allow the application to access MCP Server on behalf of the signed-in user.",
    "adminConsentDisplayName": "Access MCP Server",
    "id": "$(uuidgen)",
    "isEnabled": true,
    "type": "User",
    "userConsentDescription": "Allow the application to access MCP Server on your behalf.",
    "userConsentDisplayName": "Access MCP Server",
    "value": "user_impersonation"
  }
]
EOF
)

# Wrap permissions in api object to avoid "Couldn't find 'api' in ''" error
API_PAYLOAD=$(echo "${OAUTH2_PERMISSIONS}" | jq -c '{oauth2PermissionScopes: .}')
az ad app update --id ${AZURE_CLIENT_ID} --set api="${API_PAYLOAD}"

echo -e "${GREEN}✓ API exposed with scope: ${APP_ID_URI}/user_impersonation${NC}"
echo ""

# Add required API permissions for Azure AI Search
echo "Adding API permissions for Azure AI Search..."

# Azure AI Search Resource ID (Microsoft.Azure.Search)
# Using the App ID for "Azure Cognitive Search" explicitly found in tenant (https://search.azure.com)
SEARCH_APP_ID="880da380-985e-4198-81b9-e05b1cc53158"
SEARCH_SCOPE_ID="a4165a31-5d9e-4120-bd1e-9d88c66fd3b8"  # user_impersonation scope

az ad app permission add \
    --id ${AZURE_CLIENT_ID} \
    --api ${SEARCH_APP_ID} \
    --api-permissions ${SEARCH_SCOPE_ID}=Scope

echo -e "${GREEN}✓ Azure AI Search permissions added${NC}"
echo ""

# Grant admin consent
echo "Granting admin consent for API permissions..."
echo -e "${YELLOW}Note: You may need to be an admin to grant consent.${NC}"

# Try to grant admin consent
if az ad app permission admin-consent --id ${AZURE_CLIENT_ID} 2>/dev/null; then
    echo -e "${GREEN}✓ Admin consent granted${NC}"
else
    echo -e "${YELLOW}⚠ Unable to grant admin consent automatically.${NC}"
    echo -e "${YELLOW}  Please grant admin consent manually in Azure Portal:${NC}"
    echo -e "${YELLOW}  https://portal.azure.com/#view/Microsoft_AAD_RegisteredApps/ApplicationMenuBlade/~/CallAnAPI/appId/${AZURE_CLIENT_ID}${NC}"
fi
echo ""

# Generate JWT configuration
JWT_ISSUER="https://login.microsoftonline.com/${AZURE_TENANT_ID}/v2.0"
JWT_AUDIENCE="${APP_ID_URI}"

# Output configuration
echo "=========================================="
echo "MCP Server App Registration Complete!"
echo "=========================================="
echo ""
echo "Add the following to your .env file:"
echo ""
echo "# Azure AD Configuration"
echo "AZURE_CLIENT_ID=${AZURE_CLIENT_ID}"
echo "AZURE_CLIENT_SECRET=${AZURE_CLIENT_SECRET}"
echo "AZURE_TENANT_ID=${AZURE_TENANT_ID}"
echo ""
echo "# JWT Configuration (for server)"
echo "JWT_ISSUER=${JWT_ISSUER}"
echo "JWT_AUDIENCE=${JWT_AUDIENCE}"
echo ""
echo "# MCP Server Configuration (for client)"
echo "MCP_SERVER_AUDIENCE=${APP_ID_URI}/.default"
echo ""
echo "=========================================="
echo ""
echo -e "${YELLOW}IMPORTANT: Save the client secret above. It cannot be retrieved again!${NC}"
echo ""
echo "Next steps:"
echo "1. Update your .env file with the values above"
echo "2. Configure Azure Search endpoint and credentials"
echo "3. Run the client app registration script"
echo "4. Start the MCP server: python -m enterprise_mcp_auth.server.ai_search_mcp_server"
echo ""
