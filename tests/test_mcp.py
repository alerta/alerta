import contextlib
import json
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from alerta.mcp.client import AlertaClient
from alerta.mcp.utils import filter_params


class FilterParamsTestCase(unittest.TestCase):

    def test_empty_params(self):
        assert filter_params() == []

    def test_none_values_excluded(self):
        result = filter_params(a=None, b='hello')
        assert result == [('b', 'hello')]

    def test_string_values(self):
        result = filter_params(environment='Production', severity='critical')
        assert ('environment', 'Production') in result
        assert ('severity', 'critical') in result

    def test_list_values_expand(self):
        result = filter_params(status=['open', 'ack'])
        assert result == [('status', 'open'), ('status', 'ack')]

    def test_bool_values_lowercase(self):
        result = filter_params(flag=True)
        assert result == [('flag', 'true')]

    def test_int_values_stringify(self):
        result = filter_params(page=2)
        assert result == [('page', '2')]


class AlertaClientTestCase(unittest.TestCase):

    def test_init_with_api_key(self):
        client = AlertaClient(base_url='http://localhost:8080', api_key='test-key')
        assert client.client.headers['x-api-key'] == 'test-key'
        assert str(client.client.base_url) == 'http://localhost:8080'

    def test_init_without_api_key(self):
        client = AlertaClient(base_url='http://localhost:8080', api_key='')
        assert 'x-api-key' not in client.client.headers

    def test_init_strips_trailing_slash(self):
        client = AlertaClient(base_url='http://localhost:8080/', api_key='')
        assert str(client.client.base_url) == 'http://localhost:8080'


def _mock_response(status_code=200, json_data=None):
    resp = MagicMock(spec=httpx.Response)
    resp.status_code = status_code
    resp.json.return_value = json_data or {'status': 'ok'}
    resp.raise_for_status = MagicMock()
    if status_code >= 400:
        resp.raise_for_status.side_effect = httpx.HTTPStatusError(
            'error', request=MagicMock(), response=resp
        )
    return resp


@contextlib.contextmanager
def _patch_get_client(mock_client):
    targets = [
        'alerta.mcp.tools.alerts.get_client',
        'alerta.mcp.tools.blackouts.get_client',
        'alerta.mcp.tools.heartbeats.get_client',
        'alerta.mcp.tools.bulk.get_client',
        'alerta.mcp.tools.management.get_client',
        'alerta.mcp.tools.admin.get_client',
        'alerta.mcp.resources.get_client',
    ]
    with contextlib.ExitStack() as stack:
        for target in targets:
            stack.enter_context(patch(target, return_value=mock_client))
        yield


def _make_mock_client():
    client = MagicMock(spec=AlertaClient)
    client.get = AsyncMock(return_value={'status': 'ok'})
    client.post = AsyncMock(return_value=({'status': 'ok', 'id': 'abc123'}, 201))
    client.put = AsyncMock(return_value={'status': 'ok'})
    client.delete = AsyncMock(return_value={'status': 'ok'})
    return client


# --- Async client tests ---

@pytest.mark.asyncio
async def test_client_get():
    client = AlertaClient(base_url='http://localhost:8080', api_key='key')
    client.client.get = AsyncMock(return_value=_mock_response(200, {'status': 'ok', 'total': 0}))

    result = await client.get('/alerts', params={'page': '1'})
    assert result == {'status': 'ok', 'total': 0}
    client.client.get.assert_called_once_with('/alerts', params={'page': '1'})


@pytest.mark.asyncio
async def test_client_post():
    client = AlertaClient(base_url='http://localhost:8080', api_key='key')
    client.client.post = AsyncMock(return_value=_mock_response(201, {'status': 'ok', 'id': 'abc123'}))

    result, status = await client.post('/alert', json={'resource': 'web01', 'event': 'HighCPU'})
    assert result == {'status': 'ok', 'id': 'abc123'}
    assert status == 201


@pytest.mark.asyncio
async def test_client_put():
    client = AlertaClient(base_url='http://localhost:8080', api_key='key')
    client.client.put = AsyncMock(return_value=_mock_response(200, {'status': 'ok'}))

    result = await client.put('/alert/abc123/action', json={'action': 'ack'})
    assert result == {'status': 'ok'}


@pytest.mark.asyncio
async def test_client_delete():
    client = AlertaClient(base_url='http://localhost:8080', api_key='key')
    client.client.delete = AsyncMock(return_value=_mock_response(200, {'status': 'ok'}))

    result = await client.delete('/alert/abc123')
    assert result == {'status': 'ok'}


@pytest.mark.asyncio
async def test_client_get_error_raises():
    client = AlertaClient(base_url='http://localhost:8080', api_key='key')
    client.client.get = AsyncMock(return_value=_mock_response(404, {'status': 'error', 'message': 'not found'}))

    with pytest.raises(httpx.HTTPStatusError):
        await client.get('/alert/nonexistent')


@pytest.mark.asyncio
async def test_client_close():
    client = AlertaClient(base_url='http://localhost:8080', api_key='key')
    client.client.aclose = AsyncMock()

    await client.close()
    client.client.aclose.assert_called_once()


# --- Alert tools ---

@pytest.mark.asyncio
async def test_search_alerts_default():
    mock = _make_mock_client()
    with _patch_get_client(mock):
        from alerta.mcp.tools.alerts import search_alerts
        result = await search_alerts()

    assert result == {'status': 'ok'}
    mock.get.assert_called_once()
    args, kwargs = mock.get.call_args
    assert args[0] == '/alerts'
    params = kwargs['params']
    assert ('page', '1') in params
    assert ('page-size', '50') in params


@pytest.mark.asyncio
async def test_search_alerts_with_filters():
    mock = _make_mock_client()
    with _patch_get_client(mock):
        from alerta.mcp.tools.alerts import search_alerts
        await search_alerts(
            environment='Production',
            severity='critical',
            status='open',
            page=2,
            page_size=10,
        )

    args, kwargs = mock.get.call_args
    params = kwargs['params']
    assert ('environment', 'Production') in params
    assert ('severity', 'critical') in params
    assert ('status', 'open') in params
    assert ('page', '2') in params
    assert ('page-size', '10') in params


@pytest.mark.asyncio
async def test_get_alert():
    mock = _make_mock_client()
    with _patch_get_client(mock):
        from alerta.mcp.tools.alerts import get_alert
        await get_alert('abc123')

    mock.get.assert_called_once_with('/alert/abc123')


@pytest.mark.asyncio
async def test_create_alert_minimal():
    mock = _make_mock_client()
    with _patch_get_client(mock):
        from alerta.mcp.tools.alerts import create_alert
        await create_alert(resource='web01', event='HighCPU')

    mock.post.assert_called_once()
    args, kwargs = mock.post.call_args
    assert args[0] == '/alert'
    body = kwargs['json']
    assert body['resource'] == 'web01'
    assert body['event'] == 'HighCPU'
    assert body['severity'] == 'normal'


@pytest.mark.asyncio
async def test_create_alert_full():
    mock = _make_mock_client()
    with _patch_get_client(mock):
        from alerta.mcp.tools.alerts import create_alert
        await create_alert(
            resource='db01',
            event='DiskFull',
            environment='Production',
            severity='critical',
            service=['Database'],
            group='Storage',
            value='95%',
            text='Disk is almost full',
            tags=['disk', 'storage'],
            attributes={'region': 'us-east-1'},
            origin='monitoring',
            timeout=3600,
        )

    body = mock.post.call_args[1]['json']
    assert body['environment'] == 'Production'
    assert body['severity'] == 'critical'
    assert body['service'] == ['Database']
    assert body['group'] == 'Storage'
    assert body['value'] == '95%'
    assert body['tags'] == ['disk', 'storage']
    assert body['attributes'] == {'region': 'us-east-1'}
    assert body['timeout'] == 3600


@pytest.mark.asyncio
async def test_create_alert_omits_empty_fields():
    mock = _make_mock_client()
    with _patch_get_client(mock):
        from alerta.mcp.tools.alerts import create_alert
        await create_alert(resource='web01', event='HighCPU')

    body = mock.post.call_args[1]['json']
    assert 'environment' not in body
    assert 'service' not in body
    assert 'tags' not in body
    assert 'attributes' not in body


@pytest.mark.asyncio
async def test_action_alert():
    mock = _make_mock_client()
    with _patch_get_client(mock):
        from alerta.mcp.tools.alerts import action_alert
        await action_alert('abc123', action='ack', text='acknowledged')

    args, kwargs = mock.put.call_args
    assert args[0] == '/alert/abc123/action'
    assert kwargs['json']['action'] == 'ack'
    assert kwargs['json']['text'] == 'acknowledged'


@pytest.mark.asyncio
async def test_action_alert_with_timeout():
    mock = _make_mock_client()
    with _patch_get_client(mock):
        from alerta.mcp.tools.alerts import action_alert
        await action_alert('abc123', action='shelve', timeout=7200)

    body = mock.put.call_args[1]['json']
    assert body['timeout'] == 7200


@pytest.mark.asyncio
async def test_tag_alert():
    mock = _make_mock_client()
    with _patch_get_client(mock):
        from alerta.mcp.tools.alerts import tag_alert
        await tag_alert('abc123', tags=['important', 'reviewed'])

    args, kwargs = mock.put.call_args
    assert args[0] == '/alert/abc123/tag'
    assert kwargs['json'] == {'tags': ['important', 'reviewed']}


@pytest.mark.asyncio
async def test_untag_alert():
    mock = _make_mock_client()
    with _patch_get_client(mock):
        from alerta.mcp.tools.alerts import untag_alert
        await untag_alert('abc123', tags=['old-tag'])

    args, kwargs = mock.put.call_args
    assert args[0] == '/alert/abc123/untag'
    assert kwargs['json'] == {'tags': ['old-tag']}


@pytest.mark.asyncio
async def test_update_alert_attributes():
    mock = _make_mock_client()
    with _patch_get_client(mock):
        from alerta.mcp.tools.alerts import update_alert_attributes
        await update_alert_attributes('abc123', attributes={'team': 'platform'})

    args, kwargs = mock.put.call_args
    assert args[0] == '/alert/abc123/attributes'
    assert kwargs['json'] == {'attributes': {'team': 'platform'}}


@pytest.mark.asyncio
async def test_add_alert_note():
    mock = _make_mock_client()
    with _patch_get_client(mock):
        from alerta.mcp.tools.alerts import add_alert_note
        await add_alert_note('abc123', text='investigating root cause')

    args, kwargs = mock.put.call_args
    assert args[0] == '/alert/abc123/note'
    assert kwargs['json'] == {'text': 'investigating root cause'}


@pytest.mark.asyncio
async def test_get_alert_notes():
    mock = _make_mock_client()
    with _patch_get_client(mock):
        from alerta.mcp.tools.alerts import get_alert_notes
        await get_alert_notes('abc123')

    mock.get.assert_called_once_with('/alert/abc123/notes')


@pytest.mark.asyncio
async def test_delete_alert():
    mock = _make_mock_client()
    with _patch_get_client(mock):
        from alerta.mcp.tools.alerts import delete_alert
        await delete_alert('abc123')

    mock.delete.assert_called_once_with('/alert/abc123')


@pytest.mark.asyncio
async def test_get_alert_history():
    mock = _make_mock_client()
    with _patch_get_client(mock):
        from alerta.mcp.tools.alerts import get_alert_history
        await get_alert_history(environment='Production', page=2, page_size=25)

    args, kwargs = mock.get.call_args
    assert args[0] == '/alerts/history'
    params = kwargs['params']
    assert ('environment', 'Production') in params
    assert ('page', '2') in params
    assert ('page-size', '25') in params


@pytest.mark.asyncio
async def test_get_alert_counts():
    mock = _make_mock_client()
    with _patch_get_client(mock):
        from alerta.mcp.tools.alerts import get_alert_counts
        await get_alert_counts(environment='Production')

    args, kwargs = mock.get.call_args
    assert args[0] == '/alerts/count'
    assert ('environment', 'Production') in kwargs['params']


@pytest.mark.asyncio
async def test_get_top_alerts():
    mock = _make_mock_client()
    with _patch_get_client(mock):
        from alerta.mcp.tools.alerts import get_top_alerts
        await get_top_alerts(metric='flapping', page_size=5)

    args, kwargs = mock.get.call_args
    assert args[0] == '/alerts/top10/flapping'
    assert ('page-size', '5') in kwargs['params']


@pytest.mark.asyncio
async def test_get_top_alerts_invalid_metric():
    mock = _make_mock_client()
    with _patch_get_client(mock):
        from alerta.mcp.tools.alerts import get_top_alerts
        result = await get_top_alerts(metric='invalid')

    assert result['status'] == 'error'
    mock.get.assert_not_called()


@pytest.mark.asyncio
async def test_get_environments():
    mock = _make_mock_client()
    with _patch_get_client(mock):
        from alerta.mcp.tools.alerts import get_environments
        await get_environments()

    mock.get.assert_called_once_with('/environments')


@pytest.mark.asyncio
async def test_get_services():
    mock = _make_mock_client()
    with _patch_get_client(mock):
        from alerta.mcp.tools.alerts import get_services
        await get_services()

    mock.get.assert_called_once_with('/services')


@pytest.mark.asyncio
async def test_get_alert_tags():
    mock = _make_mock_client()
    with _patch_get_client(mock):
        from alerta.mcp.tools.alerts import get_alert_tags
        await get_alert_tags()

    mock.get.assert_called_once_with('/alerts/tags')


# --- Blackout tools ---

@pytest.mark.asyncio
async def test_list_blackouts():
    mock = _make_mock_client()
    with _patch_get_client(mock):
        from alerta.mcp.tools.blackouts import list_blackouts
        await list_blackouts()

    args, kwargs = mock.get.call_args
    assert args[0] == '/blackouts'


@pytest.mark.asyncio
async def test_create_blackout():
    mock = _make_mock_client()
    with _patch_get_client(mock):
        from alerta.mcp.tools.blackouts import create_blackout
        await create_blackout(
            environment='Production',
            service=['Web'],
            text='Maintenance window',
            duration=3600,
        )

    args, kwargs = mock.post.call_args
    assert args[0] == '/blackout'
    body = kwargs['json']
    assert body['environment'] == 'Production'
    assert body['service'] == ['Web']
    assert body['duration'] == 3600
    assert body['text'] == 'Maintenance window'


@pytest.mark.asyncio
async def test_create_blackout_omits_empty_fields():
    mock = _make_mock_client()
    with _patch_get_client(mock):
        from alerta.mcp.tools.blackouts import create_blackout
        await create_blackout(environment='Development')

    body = mock.post.call_args[1]['json']
    assert body == {'environment': 'Development'}


@pytest.mark.asyncio
async def test_delete_blackout():
    mock = _make_mock_client()
    with _patch_get_client(mock):
        from alerta.mcp.tools.blackouts import delete_blackout
        await delete_blackout('blk123')

    mock.delete.assert_called_once_with('/blackout/blk123')


# --- Heartbeat tools ---

@pytest.mark.asyncio
async def test_list_heartbeats():
    mock = _make_mock_client()
    with _patch_get_client(mock):
        from alerta.mcp.tools.heartbeats import list_heartbeats
        await list_heartbeats(status=['ok', 'expired'])

    args, kwargs = mock.get.call_args
    assert args[0] == '/heartbeats'
    params = kwargs['params']
    assert ('status', 'ok') in params
    assert ('status', 'expired') in params


@pytest.mark.asyncio
async def test_list_heartbeats_no_status_filter():
    mock = _make_mock_client()
    with _patch_get_client(mock):
        from alerta.mcp.tools.heartbeats import list_heartbeats
        await list_heartbeats()

    args, kwargs = mock.get.call_args
    params = kwargs['params']
    assert not any(k == 'status' for k, v in params)


@pytest.mark.asyncio
async def test_send_heartbeat():
    mock = _make_mock_client()
    with _patch_get_client(mock):
        from alerta.mcp.tools.heartbeats import send_heartbeat
        await send_heartbeat(origin='web-monitor', tags=['prod'], timeout=120)

    args, kwargs = mock.post.call_args
    assert args[0] == '/heartbeat'
    body = kwargs['json']
    assert body['origin'] == 'web-monitor'
    assert body['tags'] == ['prod']
    assert body['timeout'] == 120


@pytest.mark.asyncio
async def test_delete_heartbeat():
    mock = _make_mock_client()
    with _patch_get_client(mock):
        from alerta.mcp.tools.heartbeats import delete_heartbeat
        await delete_heartbeat('hb123')

    mock.delete.assert_called_once_with('/heartbeat/hb123')


# --- Bulk tools ---

@pytest.mark.asyncio
async def test_bulk_action_alerts():
    mock = _make_mock_client()
    with _patch_get_client(mock):
        from alerta.mcp.tools.bulk import bulk_action_alerts
        await bulk_action_alerts(
            action='ack',
            environment='Production',
            severity='critical',
            text='bulk ack',
        )

    args, kwargs = mock.put.call_args
    assert args[0] == '/_bulk/alerts/action'
    assert kwargs['json']['action'] == 'ack'
    assert kwargs['json']['text'] == 'bulk ack'
    assert ('environment', 'Production') in kwargs['params']
    assert ('severity', 'critical') in kwargs['params']


@pytest.mark.asyncio
async def test_bulk_tag_alerts():
    mock = _make_mock_client()
    with _patch_get_client(mock):
        from alerta.mcp.tools.bulk import bulk_tag_alerts
        await bulk_tag_alerts(tags=['reviewed'], environment='Production')

    args, kwargs = mock.put.call_args
    assert args[0] == '/_bulk/alerts/tag'
    assert kwargs['json'] == {'tags': ['reviewed']}


@pytest.mark.asyncio
async def test_bulk_delete_alerts():
    mock = _make_mock_client()
    with _patch_get_client(mock):
        from alerta.mcp.tools.bulk import bulk_delete_alerts
        await bulk_delete_alerts(status='closed')

    args, kwargs = mock.delete.call_args
    assert args[0] == '/_bulk/alerts'
    assert ('status', 'closed') in kwargs['params']


# --- Management tools ---

@pytest.mark.asyncio
async def test_health_check():
    mock = _make_mock_client()
    with _patch_get_client(mock):
        from alerta.mcp.tools.management import health_check
        await health_check()

    mock.get.assert_called_once_with('/management/healthcheck')


@pytest.mark.asyncio
async def test_get_status():
    mock = _make_mock_client()
    with _patch_get_client(mock):
        from alerta.mcp.tools.management import get_status
        await get_status()

    mock.get.assert_called_once_with('/management/status')


# --- Admin tools ---

@pytest.mark.asyncio
async def test_list_users():
    mock = _make_mock_client()
    with _patch_get_client(mock):
        from alerta.mcp.tools.admin import list_users
        await list_users()

    args, kwargs = mock.get.call_args
    assert args[0] == '/users'


@pytest.mark.asyncio
async def test_create_user():
    mock = _make_mock_client()
    with _patch_get_client(mock):
        from alerta.mcp.tools.admin import create_user
        await create_user(name='Test User', email='test@example.com', password='secret', roles=['user'])

    args, kwargs = mock.post.call_args
    assert args[0] == '/user'
    body = kwargs['json']
    assert body['name'] == 'Test User'
    assert body['email'] == 'test@example.com'
    assert body['roles'] == ['user']


@pytest.mark.asyncio
async def test_get_user():
    mock = _make_mock_client()
    with _patch_get_client(mock):
        from alerta.mcp.tools.admin import get_user
        await get_user('user123')

    mock.get.assert_called_once_with('/user/user123')


@pytest.mark.asyncio
async def test_delete_user():
    mock = _make_mock_client()
    with _patch_get_client(mock):
        from alerta.mcp.tools.admin import delete_user
        await delete_user('user123')

    mock.delete.assert_called_once_with('/user/user123')


@pytest.mark.asyncio
async def test_list_groups():
    mock = _make_mock_client()
    with _patch_get_client(mock):
        from alerta.mcp.tools.admin import list_groups
        await list_groups()

    args, kwargs = mock.get.call_args
    assert args[0] == '/groups'


@pytest.mark.asyncio
async def test_create_group():
    mock = _make_mock_client()
    with _patch_get_client(mock):
        from alerta.mcp.tools.admin import create_group
        await create_group(name='ops-team', text='Operations team')

    args, kwargs = mock.post.call_args
    body = kwargs['json']
    assert body['name'] == 'ops-team'
    assert body['text'] == 'Operations team'


@pytest.mark.asyncio
async def test_delete_group():
    mock = _make_mock_client()
    with _patch_get_client(mock):
        from alerta.mcp.tools.admin import delete_group
        await delete_group('grp123')

    mock.delete.assert_called_once_with('/group/grp123')


@pytest.mark.asyncio
async def test_add_user_to_group():
    mock = _make_mock_client()
    with _patch_get_client(mock):
        from alerta.mcp.tools.admin import add_user_to_group
        await add_user_to_group('grp123', 'user456')

    mock.put.assert_called_once_with('/group/grp123/user/user456')


@pytest.mark.asyncio
async def test_remove_user_from_group():
    mock = _make_mock_client()
    with _patch_get_client(mock):
        from alerta.mcp.tools.admin import remove_user_from_group
        await remove_user_from_group('grp123', 'user456')

    mock.delete.assert_called_once_with('/group/grp123/user/user456')


@pytest.mark.asyncio
async def test_list_api_keys():
    mock = _make_mock_client()
    with _patch_get_client(mock):
        from alerta.mcp.tools.admin import list_api_keys
        await list_api_keys()

    args, kwargs = mock.get.call_args
    assert args[0] == '/keys'


@pytest.mark.asyncio
async def test_create_api_key():
    mock = _make_mock_client()
    with _patch_get_client(mock):
        from alerta.mcp.tools.admin import create_api_key
        await create_api_key(scopes=['read:alerts'], text='read-only key', customer='Acme')

    args, kwargs = mock.post.call_args
    assert args[0] == '/key'
    body = kwargs['json']
    assert body['scopes'] == ['read:alerts']
    assert body['text'] == 'read-only key'
    assert body['customer'] == 'Acme'


@pytest.mark.asyncio
async def test_delete_api_key():
    mock = _make_mock_client()
    with _patch_get_client(mock):
        from alerta.mcp.tools.admin import delete_api_key
        await delete_api_key('key-abc')

    mock.delete.assert_called_once_with('/key/key-abc')


@pytest.mark.asyncio
async def test_list_customers():
    mock = _make_mock_client()
    with _patch_get_client(mock):
        from alerta.mcp.tools.admin import list_customers
        await list_customers()

    args, kwargs = mock.get.call_args
    assert args[0] == '/customers'


@pytest.mark.asyncio
async def test_create_customer():
    mock = _make_mock_client()
    with _patch_get_client(mock):
        from alerta.mcp.tools.admin import create_customer
        await create_customer(match='example.com', customer='Acme Corp')

    args, kwargs = mock.post.call_args
    assert args[0] == '/customer'
    assert kwargs['json'] == {'match': 'example.com', 'customer': 'Acme Corp'}


@pytest.mark.asyncio
async def test_delete_customer():
    mock = _make_mock_client()
    with _patch_get_client(mock):
        from alerta.mcp.tools.admin import delete_customer
        await delete_customer('cust123')

    mock.delete.assert_called_once_with('/customer/cust123')


@pytest.mark.asyncio
async def test_list_permissions():
    mock = _make_mock_client()
    with _patch_get_client(mock):
        from alerta.mcp.tools.admin import list_permissions
        await list_permissions()

    args, kwargs = mock.get.call_args
    assert args[0] == '/perms'


# --- Resources ---

@pytest.mark.asyncio
async def test_alert_resource():
    mock = _make_mock_client()
    mock.get = AsyncMock(return_value={'status': 'ok', 'alert': {'id': 'abc123'}})
    with _patch_get_client(mock):
        from alerta.mcp.resources import alert_resource
        result = await alert_resource('abc123')

    assert json.loads(result)['alert']['id'] == 'abc123'
    mock.get.assert_called_once_with('/alert/abc123')


@pytest.mark.asyncio
async def test_blackout_resource():
    mock = _make_mock_client()
    mock.get = AsyncMock(return_value={'status': 'ok', 'blackout': {'id': 'blk123'}})
    with _patch_get_client(mock):
        from alerta.mcp.resources import blackout_resource
        result = await blackout_resource('blk123')

    assert json.loads(result)['blackout']['id'] == 'blk123'


@pytest.mark.asyncio
async def test_heartbeat_resource():
    mock = _make_mock_client()
    mock.get = AsyncMock(return_value={'status': 'ok', 'heartbeat': {'id': 'hb123', 'origin': 'web'}})
    with _patch_get_client(mock):
        from alerta.mcp.resources import heartbeat_resource
        result = await heartbeat_resource('hb123')

    assert json.loads(result)['heartbeat']['id'] == 'hb123'
    mock.get.assert_called_once_with('/heartbeat/hb123')


@pytest.mark.asyncio
async def test_config_resource():
    mock = _make_mock_client()
    mock.get = AsyncMock(return_value={'status': 'ok', 'config': {}})
    with _patch_get_client(mock):
        from alerta.mcp.resources import config_resource
        result = await config_resource()

    assert json.loads(result)['status'] == 'ok'
    mock.get.assert_called_once_with('/config')
