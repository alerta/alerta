from alerta.mcp.server import get_client, mcp
from alerta.mcp.utils import filter_params


@mcp.tool()
async def bulk_action_alerts(
    action: str,
    environment: str = '',
    severity: str = '',
    status: str = '',
    service: str = '',
    group: str = '',
    tag: str = '',
    resource: str = '',
    event: str = '',
    text: str = 'bulk action',
    timeout: int | None = None,
) -> dict:
    """Perform an action on all alerts matching the filter criteria. Runs asynchronously.

    Args:
        action: Action to perform: open, assign, ack, unack, shelve, unshelve, close
        environment: Filter by environment
        severity: Filter by severity
        status: Filter by status
        service: Filter by service
        group: Filter by group
        tag: Filter by tag
        resource: Filter by resource
        event: Filter by event
        text: Reason for the action
        timeout: Optional timeout in seconds
    """
    params = filter_params(
        environment=environment or None,
        severity=severity or None,
        status=status or None,
        service=service or None,
        group=group or None,
        tag=tag or None,
        resource=resource or None,
        event=event or None,
    )
    body: dict = {'action': action, 'text': text}
    if timeout is not None:
        body['timeout'] = timeout

    return await get_client().put('/_bulk/alerts/action', json=body, params=params)


@mcp.tool()
async def bulk_tag_alerts(
    tags: list[str],
    environment: str = '',
    severity: str = '',
    status: str = '',
    service: str = '',
    group: str = '',
    tag: str = '',
    resource: str = '',
    event: str = '',
) -> dict:
    """Add tags to all alerts matching the filter criteria.

    Args:
        tags: Tags to add
        environment: Filter by environment
        severity: Filter by severity
        status: Filter by status
        service: Filter by service
        group: Filter by group
        tag: Filter by existing tag
        resource: Filter by resource
        event: Filter by event
    """
    params = filter_params(
        environment=environment or None,
        severity=severity or None,
        status=status or None,
        service=service or None,
        group=group or None,
        tag=tag or None,
        resource=resource or None,
        event=event or None,
    )
    return await get_client().put('/_bulk/alerts/tag', json={'tags': tags}, params=params)


@mcp.tool()
async def bulk_delete_alerts(
    environment: str = '',
    severity: str = '',
    status: str = '',
    service: str = '',
    group: str = '',
    tag: str = '',
    resource: str = '',
    event: str = '',
) -> dict:
    """Delete all alerts matching the filter criteria.

    Args:
        environment: Filter by environment
        severity: Filter by severity
        status: Filter by status
        service: Filter by service
        group: Filter by group
        tag: Filter by tag
        resource: Filter by resource
        event: Filter by event
    """
    params = filter_params(
        environment=environment or None,
        severity=severity or None,
        status=status or None,
        service=service or None,
        group=group or None,
        tag=tag or None,
        resource=resource or None,
        event=event or None,
    )
    return await get_client().delete('/_bulk/alerts', params=params)
