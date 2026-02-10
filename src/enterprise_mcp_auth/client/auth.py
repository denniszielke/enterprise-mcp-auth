"""Authentication module for acquiring Entra tokens using MSAL.

This module provides functions to acquire tokens using device code flow
(for local development) or confidential client flow (when client secret is available).
"""

import os
import sys
from typing import Optional
import msal


def acquire_token(
    client_id: str,
    tenant_id: str,
    scopes: list[str],
    client_secret: Optional[str] = None,
    use_cache: bool = True
) -> str:
    """Acquire access token using MSAL.
    
    If client_secret is provided, uses confidential client flow.
    Otherwise, uses device code flow for interactive authentication.
    
    Args:
        client_id: Azure AD client ID
        tenant_id: Azure AD tenant ID
        scopes: List of OAuth scopes to request
        client_secret: Optional client secret for confidential client flow
        use_cache: Whether to use token cache (default: True)
        
    Returns:
        Access token string
        
    Raises:
        Exception: If token acquisition fails
    """
    authority = f"https://login.microsoftonline.com/{tenant_id}"
    
    if client_secret:
        # Use confidential client flow
        return _acquire_token_confidential(
            client_id, authority, client_secret, scopes, use_cache
        )
    else:
        # Use device code flow
        return _acquire_token_device_code(
            client_id, authority, scopes, use_cache
        )


def _acquire_token_confidential(
    client_id: str,
    authority: str,
    client_secret: str,
    scopes: list[str],
    use_cache: bool
) -> str:
    """Acquire token using confidential client flow."""
    app = msal.ConfidentialClientApplication(
        client_id,
        authority=authority,
        client_credential=client_secret,
    )
    
    # Try cache first if enabled
    if use_cache:
        accounts = app.get_accounts()
        if accounts:
            result = app.acquire_token_silent(scopes, account=accounts[0])
            if result and "access_token" in result:
                print("Token acquired from cache")
                return result["access_token"]
    
    # Acquire token
    result = app.acquire_token_for_client(scopes=scopes)
    
    if "access_token" in result:
        print("Token acquired using client credentials")
        return result["access_token"]
    else:
        error = result.get("error", "unknown_error")
        error_desc = result.get("error_description", "Failed to acquire token")
        raise Exception(f"Token acquisition failed: {error} - {error_desc}")


def _acquire_token_device_code(
    client_id: str,
    authority: str,
    scopes: list[str],
    use_cache: bool
) -> str:
    """Acquire token using device code flow."""
    app = msal.PublicClientApplication(
        client_id,
        authority=authority,
    )
    
    # Try cache first if enabled
    if use_cache:
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


def get_user_info_from_token(token: str) -> dict:
    """Extract user information from JWT token.
    
    Note: This performs basic decoding without verification.
    For production use, tokens should be verified.
    
    Args:
        token: JWT access token
        
    Returns:
        Dictionary with user claims (oid, preferred_username, etc.)
    """
    import base64
    import json
    
    try:
        # JWT tokens have 3 parts separated by dots
        parts = token.split('.')
        if len(parts) != 3:
            return {}
        
        # Decode the payload (second part)
        # Add padding if necessary
        payload = parts[1]
        payload += '=' * (4 - len(payload) % 4)
        
        decoded = base64.urlsafe_b64decode(payload)
        claims = json.loads(decoded)
        
        return claims
    except Exception:
        return {}
