"""ASGI application that mounts the MCP server for deployment with uvicorn.

This module provides an ASGI-compatible application that wraps the
Azure AI Search MCP server with additional HTTP endpoints (e.g. health
checks) so that it can be deployed as a standard web service:

    uvicorn enterprise_mcp_auth.server.app:app

The MCP protocol endpoint is available at ``/mcp`` while ``/health``
returns a simple JSON status payload.

OpenTelemetry telemetry is enabled via the telemetry module – set
``APPLICATIONINSIGHTS_CONNECTION_STRING`` to export to Application
Insights.
"""

import logging

from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Mount, Route

from enterprise_mcp_auth.server.ai_search_mcp_server import mcp

logger = logging.getLogger(__name__)


async def health(request: Request) -> JSONResponse:
    """Health-check endpoint used by load balancers and container probes."""
    return JSONResponse({"status": "ok", "service": mcp.name})


# Build the MCP ASGI sub-application using the streamable-http transport
# so that it is compatible with the existing ``mcp.run(transport="streamable-http")``
# configuration.
_mcp_asgi = mcp.http_app(transport="streamable-http")

# Compose into a Starlette application so that we can add auxiliary routes
# like /health while mounting the MCP app at /mcp.
app = Starlette(
    routes=[
        Route("/health", health, methods=["GET"]),
        Mount("/mcp", app=_mcp_asgi),
    ],
)

logger.info("MCP ASGI app created – mount at /mcp, health check at /health")
