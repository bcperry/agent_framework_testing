"""MCP server generated directly from the FastAPI app.

FastMCP derives the tools from the API's OpenAPI spec, so the REST API stays the
single source of truth -- routes, schemas, and authorization rules are never
duplicated between the two transports.

The caller's bearer token is forwarded from the inbound MCP request through to the
FastAPI app, which then makes exactly the same claims-based decision it makes for a
direct REST caller. fastmcp strips ``authorization`` by default, so it is opted
back in explicitly.

Run with:  uv run python -m user_api.mcp_server
"""

import httpx
from fastmcp import FastMCP
from fastmcp.server.dependencies import get_http_headers

from .api import app


async def _forward_bearer_token(request: httpx.Request) -> None:
    """Copy the MCP caller's Authorization header onto the upstream API request."""
    authorization = get_http_headers(include={"authorization"}).get("authorization")
    if authorization:
        request.headers["authorization"] = authorization


mcp = FastMCP.from_fastapi(
    app=app,
    name="Records MCP",
    httpx_client_kwargs={"event_hooks": {"request": [_forward_bearer_token]}},
)


if __name__ == "__main__":
    mcp.run(transport="http", host="127.0.0.1", port=8098)
