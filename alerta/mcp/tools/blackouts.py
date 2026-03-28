from alerta.mcp.server import get_client, mcp


@mcp.tool()
async def list_blackouts(page: int = 1, page_size: int = 50) -> dict:
    """List alert suppression blackout periods.

    Args:
        page: Page number (1-based)
        page_size: Results per page
    """
    params = {'page': str(page), 'page-size': str(page_size)}
    return await get_client().get('/blackouts', params=params)


@mcp.tool()
async def create_blackout(
    environment: str,
    service: list[str] | None = None,
    resource: str = '',
    event: str = '',
    group: str = '',
    tags: list[str] | None = None,
    customer: str = '',
    start_time: str = '',
    end_time: str = '',
    duration: int | None = None,
    text: str = '',
) -> dict:
    """Create a maintenance blackout window to suppress alerts.

    Args:
        environment: Environment to blackout (required)
        service: List of services to blackout
        resource: Resource to blackout
        event: Event to blackout
        group: Group to blackout
        tags: Tags to match for blackout
        customer: Customer to scope blackout to
        start_time: Start time (ISO 8601 format). Defaults to now.
        end_time: End time (ISO 8601 format)
        duration: Duration in seconds (alternative to end_time)
        text: Description of the blackout reason
    """
    body: dict = {'environment': environment}
    if service:
        body['service'] = service
    if resource:
        body['resource'] = resource
    if event:
        body['event'] = event
    if group:
        body['group'] = group
    if tags:
        body['tags'] = tags
    if customer:
        body['customer'] = customer
    if start_time:
        body['startTime'] = start_time
    if end_time:
        body['endTime'] = end_time
    if duration is not None:
        body['duration'] = duration
    if text:
        body['text'] = text

    result, _ = await get_client().post('/blackout', json=body)
    return result


@mcp.tool()
async def update_blackout(blackout_id: str, **kwargs) -> dict:
    """Update an existing blackout.

    Args:
        blackout_id: The blackout ID
        **kwargs: Fields to update (environment, service, resource, event, group, tags, startTime, endTime, duration, text)
    """
    return await get_client().put(f'/blackout/{blackout_id}', json=kwargs)


@mcp.tool()
async def delete_blackout(blackout_id: str) -> dict:
    """Delete a blackout period.

    Args:
        blackout_id: The blackout ID
    """
    return await get_client().delete(f'/blackout/{blackout_id}')
