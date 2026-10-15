def test_good_to_go(api):
    status, body = api.raw('GET', '/management/gtg')
    assert status == 200
    assert body.strip() == b'OK'


def test_healthcheck(api):
    status, body = api.raw('GET', '/management/healthcheck')
    if status == 200:
        assert body.strip() == b'OK'
    else:
        assert status == 503
        assert body.startswith((b'HEARTBEAT_STALE: ', b'HEALTH_CHECK_FAILED: '))


def test_index(api):
    r = api.get('/')
    assert r.status == 200
    assert r.json['status'] == 'ok'
    assert isinstance(r.json['links'], list)


def test_config_for_web_ui(api):
    r = api.get('/config')
    assert r.status == 200
    config = r.json
    for key in ('endpoint', 'alarm_model', 'auth_required', 'provider', 'signup_enabled', 'customer_views',
                'severity', 'colors', 'timeouts', 'environments', 'columns', 'sort_by', 'refresh_interval',
                'actions', 'filter', 'dates', 'audio'):
        assert key in config, key
    assert isinstance(config['environments'], list)
    assert {'name', 'severity', 'colors', 'status', 'defaults'} <= set(config['alarm_model'])
