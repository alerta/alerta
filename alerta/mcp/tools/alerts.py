from alerta.mcp.server import get_client, mcp


def _filter_params(**kwargs) -> list[tuple[str, str]]:
    """Build query params list, supporting multi-value fields."""
    params: list[tuple[str, str]] = []
    for key, value in kwargs.items():
        if value is None:
            continue
        if isinstance(value, list):
            for v in value:
                params.append((key, str(v)))
        elif isinstance(value, bool):
            params.append((key, str(value).lower()))
        else:
            params.append((key, str(value)))
    return params


@mcp.tool()
async def search_alerts(
    query: str = '',
    environment: str = '',
    severity: str = '',
    status: str = '',
    service: str = '',
    group: str = '',
    tag: str = '',
    resource: str = '',
    event: str = '',
    origin: str = '',
    customer: str = '',
    sort_by: str = '',
    page: int = 1,
    page_size: int = 50,
) -> dict:
    """Search alerts with flexible filtering.

    Returns paginated alerts with severity and status count summaries.

    Args:
        query: Free-text search (Lucene-like query syntax)
        environment: Filter by environment (e.g. "Production", "Development")
        severity: Filter by severity: security, critical, major, minor, warning, informational, normal, ok, cleared, debug, trace, unknown
        status: Filter by status: open, assign, ack, shelved, blackout, closed, expired, unknown
        service: Filter by service name
        group: Filter by alert group
        tag: Filter by tag
        resource: Filter by resource name
        event: Filter by event name
        origin: Filter by origin
        customer: Filter by customer
        sort_by: Sort field (e.g. "lastReceiveTime", "severity")
        page: Page number (1-based)
        page_size: Results per page (default 50)
    """
    params = _filter_params(
        q=query or None,
        environment=environment or None,
        severity=severity or None,
        status=status or None,
        service=service or None,
        group=group or None,
        tag=tag or None,
        resource=resource or None,
        event=event or None,
        origin=origin or None,
        customer=customer or None,
    )
    params.append(('page', str(page)))
    params.append(('page-size', str(page_size)))
    if sort_by:
        params.append(('sort-by', sort_by))

    return await get_client().get('/alerts', params=params)


@mcp.tool()
async def get_alert(alert_id: str) -> dict:
    """Get a single alert by ID.

    Args:
        alert_id: The alert ID
    """
    return await get_client().get(f'/alert/{alert_id}')


@mcp.tool()
async def create_alert(
    resource: str,
    event: str,
    environment: str = '',
    severity: str = 'normal',
    service: list[str] | None = None,
    group: str = '',
    value: str = '',
    text: str = '',
    tags: list[str] | None = None,
    attributes: dict | None = None,
    origin: str = '',
    alert_type: str = '',
    customer: str = '',
    timeout: int | None = None,
    raw_data: str = '',
) -> dict:
    """Create a new alert.

    Args:
        resource: Resource under alarm (e.g. "web01", "db-server-1")
        event: Event name (e.g. "HighCPU", "DiskFull")
        environment: Environment (e.g. "Production", "Development")
        severity: Alert severity: security, critical, major, minor, warning, informational, normal, ok, cleared, debug, trace, unknown
        service: List of affected services
        group: Alert group
        value: Event value (e.g. "98%", "512MB")
        text: Freeform description text
        tags: List of tags
        attributes: Custom key-value attributes
        origin: Source of the alert
        alert_type: Alert type
        customer: Customer name
        timeout: Timeout in seconds before alert is expired
        raw_data: Raw data associated with alert
    """
    body: dict = {
        'resource': resource,
        'event': event,
        'severity': severity,
    }
    if environment:
        body['environment'] = environment
    if service:
        body['service'] = service
    if group:
        body['group'] = group
    if value:
        body['value'] = value
    if text:
        body['text'] = text
    if tags:
        body['tags'] = tags
    if attributes:
        body['attributes'] = attributes
    if origin:
        body['origin'] = origin
    if alert_type:
        body['type'] = alert_type
    if customer:
        body['customer'] = customer
    if timeout is not None:
        body['timeout'] = timeout
    if raw_data:
        body['rawData'] = raw_data

    result, _ = await get_client().post('/alert', json=body)
    return result


@mcp.tool()
async def action_alert(
    alert_id: str,
    action: str,
    text: str = '',
    timeout: int | None = None,
) -> dict:
    """Perform an operator action on an alert.

    Args:
        alert_id: The alert ID
        action: Action to perform: open, assign, ack, unack, shelve, unshelve, close
        text: Optional reason or note for the action
        timeout: Optional timeout in seconds
    """
    body: dict = {'action': action}
    if text:
        body['text'] = text
    if timeout is not None:
        body['timeout'] = timeout

    return await get_client().put(f'/alert/{alert_id}/action', json=body)


@mcp.tool()
async def tag_alert(alert_id: str, tags: list[str]) -> dict:
    """Add tags to an alert.

    Args:
        alert_id: The alert ID
        tags: List of tags to add
    """
    return await get_client().put(f'/alert/{alert_id}/tag', json={'tags': tags})


@mcp.tool()
async def untag_alert(alert_id: str, tags: list[str]) -> dict:
    """Remove tags from an alert.

    Args:
        alert_id: The alert ID
        tags: List of tags to remove
    """
    return await get_client().put(f'/alert/{alert_id}/untag', json={'tags': tags})


@mcp.tool()
async def update_alert_attributes(alert_id: str, attributes: dict) -> dict:
    """Update custom key-value attributes on an alert.

    Args:
        alert_id: The alert ID
        attributes: Dictionary of attribute key-value pairs to set
    """
    return await get_client().put(f'/alert/{alert_id}/attributes', json={'attributes': attributes})


@mcp.tool()
async def add_alert_note(alert_id: str, text: str) -> dict:
    """Add an operator note to an alert.

    Args:
        alert_id: The alert ID
        text: Note text
    """
    return await get_client().put(f'/alert/{alert_id}/note', json={'text': text})


@mcp.tool()
async def get_alert_notes(alert_id: str) -> dict:
    """List notes for an alert.

    Args:
        alert_id: The alert ID
    """
    return await get_client().get(f'/alert/{alert_id}/notes')


@mcp.tool()
async def delete_alert(alert_id: str) -> dict:
    """Delete an alert.

    Args:
        alert_id: The alert ID
    """
    return await get_client().delete(f'/alert/{alert_id}')


@mcp.tool()
async def get_alert_history(
    environment: str = '',
    severity: str = '',
    status: str = '',
    service: str = '',
    group: str = '',
    tag: str = '',
    page: int = 1,
    page_size: int = 50,
) -> dict:
    """Get alert change history.

    Args:
        environment: Filter by environment
        severity: Filter by severity
        status: Filter by status
        service: Filter by service
        group: Filter by group
        tag: Filter by tag
        page: Page number (1-based)
        page_size: Results per page
    """
    params = _filter_params(
        environment=environment or None,
        severity=severity or None,
        status=status or None,
        service=service or None,
        group=group or None,
        tag=tag or None,
    )
    params.append(('page', str(page)))
    params.append(('page-size', str(page_size)))

    return await get_client().get('/alerts/history', params=params)


@mcp.tool()
async def get_alert_counts(
    environment: str = '',
    severity: str = '',
    status: str = '',
    service: str = '',
    group: str = '',
    tag: str = '',
) -> dict:
    """Get alert counts by severity and status. Useful for dashboards and summaries.

    Args:
        environment: Filter by environment
        severity: Filter by severity
        status: Filter by status
        service: Filter by service
        group: Filter by group
        tag: Filter by tag
    """
    params = _filter_params(
        environment=environment or None,
        severity=severity or None,
        status=status or None,
        service=service or None,
        group=group or None,
        tag=tag or None,
    )
    return await get_client().get('/alerts/count', params=params)


@mcp.tool()
async def get_top_alerts(
    metric: str = 'count',
    environment: str = '',
    severity: str = '',
    status: str = '',
    service: str = '',
    group: str = '',
    tag: str = '',
    page_size: int = 10,
) -> dict:
    """Get top alerts by a given metric.

    Args:
        metric: Ranking metric: "count" (most frequent), "flapping" (most unstable), "standing" (longest open)
        environment: Filter by environment
        severity: Filter by severity
        status: Filter by status
        service: Filter by service
        group: Filter by group
        tag: Filter by tag
        page_size: Number of results (default 10)
    """
    if metric not in ('count', 'flapping', 'standing'):
        return {'status': 'error', 'message': "metric must be one of: count, flapping, standing"}

    params = _filter_params(
        environment=environment or None,
        severity=severity or None,
        status=status or None,
        service=service or None,
        group=group or None,
        tag=tag or None,
    )
    params.append(('page-size', str(page_size)))

    return await get_client().get(f'/alerts/top10/{metric}', params=params)


@mcp.tool()
async def get_environments() -> dict:
    """List all known alert environments."""
    return await get_client().get('/environments')


@mcp.tool()
async def get_services() -> dict:
    """List all known alert services."""
    return await get_client().get('/services')


@mcp.tool()
async def get_alert_tags() -> dict:
    """List all tags currently in use across alerts."""
    return await get_client().get('/alerts/tags')
