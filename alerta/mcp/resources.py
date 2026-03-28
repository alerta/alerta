import json

from alerta.mcp.server import get_client, mcp


@mcp.resource('alerta://alert/{alert_id}')
async def alert_resource(alert_id: str) -> str:
    """Get alert details by ID."""
    result = await get_client().get(f'/alert/{alert_id}')
    return json.dumps(result, indent=2)


@mcp.resource('alerta://blackout/{blackout_id}')
async def blackout_resource(blackout_id: str) -> str:
    """Get blackout details by ID."""
    result = await get_client().get(f'/blackout/{blackout_id}')
    return json.dumps(result, indent=2)


@mcp.resource('alerta://heartbeat/{heartbeat_id}')
async def heartbeat_resource(heartbeat_id: str) -> str:
    """Get heartbeat details by ID."""
    result = await get_client().get(f'/heartbeat/{heartbeat_id}')
    return json.dumps(result, indent=2)


@mcp.resource('alerta://config')
async def config_resource() -> str:
    """Get Alerta server configuration."""
    result = await get_client().get('/config')
    return json.dumps(result, indent=2)
