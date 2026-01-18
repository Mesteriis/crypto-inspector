"""
MCP (Model Context Protocol) Server.

Allows AI agents to connect and query all crypto/traditional finance data.
"""

from services.mcp.server import get_mcp_server, start_mcp_server, stop_mcp_server

__all__ = ["get_mcp_server", "start_mcp_server", "stop_mcp_server"]
