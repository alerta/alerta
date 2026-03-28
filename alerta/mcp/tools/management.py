from alerta.mcp.server import get_client, mcp


@mcp.tool()
async def health_check() -> dict:
    """Check system health. Returns 'ok' if the Alerta server and database are healthy."""
    return await get_client().get('/management/healthcheck')


@mcp.tool()
async def get_status() -> dict:
    """Get Alerta server status including uptime, metrics, and version info."""
    return await get_client().get('/management/status')
