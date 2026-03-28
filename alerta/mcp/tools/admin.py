from alerta.mcp.server import get_client, mcp

# --- Users ---

@mcp.tool()
async def list_users(page: int = 1, page_size: int = 50) -> dict:
    """List all users (requires admin:users scope).

    Args:
        page: Page number (1-based)
        page_size: Results per page
    """
    params = {'page': str(page), 'page-size': str(page_size)}
    return await get_client().get('/users', params=params)


@mcp.tool()
async def get_user(user_id: str) -> dict:
    """Get a user by ID (requires admin:users scope).

    Args:
        user_id: The user ID
    """
    return await get_client().get(f'/user/{user_id}')


@mcp.tool()
async def create_user(
    name: str,
    email: str,
    password: str,
    roles: list[str] | None = None,
    text: str = '',
) -> dict:
    """Create a new user (requires admin:users scope, basic auth provider only).

    Args:
        name: User's display name
        email: User's email address
        password: User's password
        roles: List of roles (e.g. ["admin", "user"])
        text: Optional description
    """
    body: dict = {'name': name, 'email': email, 'password': password}
    if roles:
        body['roles'] = roles
    if text:
        body['text'] = text

    result, _ = await get_client().post('/user', json=body)
    return result


@mcp.tool()
async def update_user(user_id: str, **kwargs) -> dict:
    """Update a user (requires admin:users scope).

    Args:
        user_id: The user ID
        **kwargs: Fields to update (name, email, password, roles, text, status, attributes)
    """
    return await get_client().put(f'/user/{user_id}', json=kwargs)


@mcp.tool()
async def delete_user(user_id: str) -> dict:
    """Delete a user (requires admin:users scope).

    Args:
        user_id: The user ID
    """
    return await get_client().delete(f'/user/{user_id}')


# --- Groups ---

@mcp.tool()
async def list_groups(page: int = 1, page_size: int = 50) -> dict:
    """List all groups.

    Args:
        page: Page number (1-based)
        page_size: Results per page
    """
    params = {'page': str(page), 'page-size': str(page_size)}
    return await get_client().get('/groups', params=params)


@mcp.tool()
async def create_group(name: str, text: str = '') -> dict:
    """Create a new group.

    Args:
        name: Group name
        text: Optional description
    """
    body: dict = {'name': name}
    if text:
        body['text'] = text

    result, _ = await get_client().post('/group', json=body)
    return result


@mcp.tool()
async def update_group(group_id: str, **kwargs) -> dict:
    """Update a group.

    Args:
        group_id: The group ID
        **kwargs: Fields to update (name, text)
    """
    return await get_client().put(f'/group/{group_id}', json=kwargs)


@mcp.tool()
async def delete_group(group_id: str) -> dict:
    """Delete a group.

    Args:
        group_id: The group ID
    """
    return await get_client().delete(f'/group/{group_id}')


@mcp.tool()
async def add_user_to_group(group_id: str, user_id: str) -> dict:
    """Add a user to a group.

    Args:
        group_id: The group ID
        user_id: The user ID to add
    """
    return await get_client().put(f'/group/{group_id}/user/{user_id}')


@mcp.tool()
async def remove_user_from_group(group_id: str, user_id: str) -> dict:
    """Remove a user from a group.

    Args:
        group_id: The group ID
        user_id: The user ID to remove
    """
    return await get_client().delete(f'/group/{group_id}/user/{user_id}')


# --- Permissions ---

@mcp.tool()
async def list_permissions(page: int = 1, page_size: int = 50) -> dict:
    """List all permissions/roles.

    Args:
        page: Page number (1-based)
        page_size: Results per page
    """
    params = {'page': str(page), 'page-size': str(page_size)}
    return await get_client().get('/perms', params=params)


# --- Customers ---

@mcp.tool()
async def list_customers(page: int = 1, page_size: int = 50) -> dict:
    """List all customers.

    Args:
        page: Page number (1-based)
        page_size: Results per page
    """
    params = {'page': str(page), 'page-size': str(page_size)}
    return await get_client().get('/customers', params=params)


@mcp.tool()
async def create_customer(match: str, customer: str) -> dict:
    """Create a customer mapping.

    Args:
        match: Login email or domain to match (e.g. "example.com")
        customer: Customer name to assign
    """
    result, _ = await get_client().post('/customer', json={'match': match, 'customer': customer})
    return result


@mcp.tool()
async def delete_customer(customer_id: str) -> dict:
    """Delete a customer mapping.

    Args:
        customer_id: The customer ID
    """
    return await get_client().delete(f'/customer/{customer_id}')


# --- API Keys ---

@mcp.tool()
async def list_api_keys(page: int = 1, page_size: int = 50) -> dict:
    """List API keys.

    Args:
        page: Page number (1-based)
        page_size: Results per page
    """
    params = {'page': str(page), 'page-size': str(page_size)}
    return await get_client().get('/keys', params=params)


@mcp.tool()
async def create_api_key(
    scopes: list[str],
    text: str = '',
    customer: str = '',
    user: str = '',
) -> dict:
    """Create an API key.

    Args:
        scopes: List of scopes (e.g. ["read:alerts", "write:alerts"])
        text: Description of the key's purpose
        customer: Customer to scope the key to
        user: User to associate the key with
    """
    body: dict = {'scopes': scopes}
    if text:
        body['text'] = text
    if customer:
        body['customer'] = customer
    if user:
        body['user'] = user

    result, _ = await get_client().post('/key', json=body)
    return result


@mcp.tool()
async def delete_api_key(key: str) -> dict:
    """Delete (revoke) an API key.

    Args:
        key: The API key ID
    """
    return await get_client().delete(f'/key/{key}')
