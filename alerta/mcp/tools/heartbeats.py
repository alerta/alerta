from alerta.mcp.server import get_client, mcp


@mcp.tool()
async def list_heartbeats(
    status: list[str] | None = None,
    page: int = 1,
    page_size: int = 50,
) -> dict:
    """List heartbeats with optional status filtering.

    Args:
        status: Filter by status (e.g. ["ok", "slow", "expired"])
        page: Page number (1-based)
        page_size: Results per page
    """
    params: list[tuple[str, str]] = [
        ('page', str(page)),
        ('page-size', str(page_size)),
    ]
    if status:
        for s in status:
            params.append(('status', s))

    return await get_client().get('/heartbeats', params=params)


@mcp.tool()
async def send_heartbeat(
    origin: str,
    tags: list[str] | None = None,
    attributes: dict | None = None,
    timeout: int | None = None,
    customer: str = '',
) -> dict:
    """Send a heartbeat to indicate a service is alive.

    Args:
        origin: Origin of the heartbeat (e.g. service name)
        tags: List of tags
        attributes: Custom key-value attributes
        timeout: Heartbeat timeout in seconds
        customer: Customer name
    """
    body: dict = {'origin': origin}
    if tags:
        body['tags'] = tags
    if attributes:
        body['attributes'] = attributes
    if timeout is not None:
        body['timeout'] = timeout
    if customer:
        body['customer'] = customer

    result, _ = await get_client().post('/heartbeat', json=body)
    return result


@mcp.tool()
async def delete_heartbeat(heartbeat_id: str) -> dict:
    """Delete a heartbeat.

    Args:
        heartbeat_id: The heartbeat ID
    """
    return await get_client().delete(f'/heartbeat/{heartbeat_id}')
