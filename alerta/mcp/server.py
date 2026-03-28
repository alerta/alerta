import sys
from contextlib import asynccontextmanager

from mcp.server.fastmcp import FastMCP

from alerta.mcp.client import AlertaClient


@asynccontextmanager
async def lifespan(server: FastMCP):
    client = AlertaClient()
    server._alerta_client = client
    try:
        yield
    finally:
        await client.close()


mcp = FastMCP(
    name='Alerta',
    instructions='MCP server for Alerta alert monitoring system. Query, manage, and interact with alerts, blackouts, heartbeats, and admin resources.',
    lifespan=lifespan,
)


def get_client() -> AlertaClient:
    return mcp._alerta_client


from alerta.mcp import resources  # noqa: E402, F401
# Register all tools
from alerta.mcp.tools import (admin, alerts, blackouts,  # noqa: E402, F401
                              bulk, heartbeats, management)


def main():
    transport = sys.argv[1] if len(sys.argv) > 1 else 'stdio'
    if transport == 'http':
        mcp.run(transport='streamable-http')
    else:
        mcp.run(transport='stdio')


if __name__ == '__main__':
    main()
