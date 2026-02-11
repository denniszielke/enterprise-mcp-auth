"""CLI entrypoint for LangGraph ReAct agent.

This module provides a Click-based CLI for running queries against the
LangGraph ReAct agent with Azure AI Search MCP server.
"""

import os
import sys
import asyncio
from typing import Optional
import click
from dotenv import load_dotenv
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

# Load environment variables
load_dotenv()


@click.command()
@click.argument('query', type=str)
@click.option(
    '--model',
    default='gpt-4o-mini',
    help='OpenAI model to use (default: gpt-4o-mini)'
)
@click.option(
    '--mcp-url',
    default=None,
    help='MCP server URL (default: from MCP_BASE_URL env var)'
)
@click.option(
    '--verbose',
    is_flag=True,
    help='Show verbose output including reasoning steps'
)
def main(query: str, model: str, mcp_url: Optional[str], verbose: bool):
    """Run a query against the LangGraph ReAct agent.
    
    QUERY: The question or search query to execute
    
    Example:
        python -m enterprise_mcp_auth.cli "What documents mention security?"
    """
    # Validate environment variables
    required_vars = {
        'AZURE_CLIENT_ID': os.getenv('AZURE_CLIENT_ID'),
        'AZURE_TENANT_ID': os.getenv('AZURE_TENANT_ID'),
        'OPENAI_API_KEY': os.getenv('OPENAI_API_KEY'),
    }
    
    missing_vars = [name for name, value in required_vars.items() if not value]
    if missing_vars:
        click.echo(f"Error: Missing required environment variables: {', '.join(missing_vars)}", err=True)
        click.echo("\nPlease set these variables in your .env file or environment.", err=True)
        sys.exit(1)
    
    # Get configuration
    client_id = os.getenv('AZURE_CLIENT_ID')
    tenant_id = os.getenv('AZURE_TENANT_ID')
    client_secret = os.getenv('AZURE_CLIENT_SECRET')
    
    # MCP configuration
    # MCP_BASE_URL is the preferred variable, with MCP_SERVER_URL as fallback for compatibility
    mcp_base_url = mcp_url or os.getenv('MCP_BASE_URL') or os.getenv('MCP_SERVER_URL', 'http://localhost:8000')
    mcp_scope = os.getenv('MCP_SCOPE') or os.getenv('MCP_SERVER_AUDIENCE')
    
    if not mcp_scope:
        # Default scope pattern
        mcp_scope = f"api://{client_id}/.default"
    
    click.echo(f"🤖 LangGraph ReAct Agent for Azure AI Search")
    click.echo(f"{'=' * 60}\n")
    
    # Acquire token
    click.echo("🔐 Acquiring access token...")
    click.echo(f"   Tenant: {tenant_id}")
    click.echo(f"   Client: {client_id}")
    click.echo(f"   Scope:  {mcp_scope}")
    
    try:
        from .client.auth import acquire_token, get_user_info_from_token
        
        token = acquire_token(
            client_id=client_id,
            tenant_id=tenant_id,
            scopes=[mcp_scope],
            client_secret=client_secret
        )
        
        # Extract user info from token
        user_info = get_user_info_from_token(token)
        user_login = user_info.get('preferred_username') or user_info.get('upn') or 'unknown'
        oid = user_info.get('oid')
        
        click.echo(f"✓ Token acquired for user: {user_login}\n")
        
    except Exception as e:
        click.echo(f"✗ Token acquisition failed: {e}", err=True)
        sys.exit(1)
    
    # Run agent
    click.echo(f"🔍 Query: {query}")
    click.echo(f"🌐 MCP Server: {mcp_base_url}")
    click.echo(f"🤖 Model: {model}\n")
    click.echo(f"{'=' * 60}\n")
    
    try:
        from .agents.supervisor import run_supervisor
        
        # Run the supervisor graph
        result = asyncio.run(
            run_supervisor(
                query=query,
                access_token=token,
                mcp_base_url=mcp_base_url,
                user_login=user_login,
                oid=oid,
                model_name=model
            )
        )
        
        # Display results
        messages = result.get('messages', [])
        
        if verbose:
            click.echo("💭 Agent Reasoning:\n")
            for msg in messages:
                if isinstance(msg, HumanMessage):
                    click.echo(f"👤 User: {msg.content}\n")
                elif isinstance(msg, AIMessage):
                    if msg.content:
                        click.echo(f"🤖 Assistant: {msg.content}\n")
                    if hasattr(msg, 'tool_calls') and msg.tool_calls:
                        for tool_call in msg.tool_calls:
                            click.echo(f"🔧 Tool Call: {tool_call.get('name', 'unknown')}")
                            click.echo(f"   Args: {tool_call.get('args', {})}\n")
                elif isinstance(msg, ToolMessage):
                    click.echo(f"📊 Tool Result: {msg.name}")
                    click.echo(f"   {msg.content[:200]}{'...' if len(str(msg.content)) > 200 else ''}\n")
        else:
            # Just show the final response
            click.echo("📝 Response:\n")
            for msg in reversed(messages):
                if isinstance(msg, AIMessage) and msg.content:
                    click.echo(msg.content)
                    break
        
        click.echo(f"\n{'=' * 60}")
        click.echo("✓ Query completed successfully")
        
    except Exception as e:
        click.echo(f"\n{'=' * 60}", err=True)
        click.echo(f"✗ Error: {e}", err=True)
        if verbose:
            import traceback
            click.echo("\nTraceback:", err=True)
            click.echo(traceback.format_exc(), err=True)
        sys.exit(1)


if __name__ == '__main__':
    main()
