from uuid import uuid4

from .shapes import HEARTBEAT, PAGED, assert_error, assert_shape


def test_heartbeat_lifecycle(api):
    origin = f'contract/{uuid4().hex[:12]}'

    r = api.post('/heartbeat', {'origin': origin, 'timeout': 60, 'tags': ['contract'], 'attributes': {'k': 'v'}})
    assert r.status == 201, r.json
    assert r.json['status'] == 'ok'
    hb = r.json['heartbeat']
    assert_shape(hb, HEARTBEAT, 'heartbeat')
    assert hb['id'] == r.json['id']
    assert hb['origin'] == origin
    assert hb['timeout'] == 60
    assert hb['tags'] == ['contract']
    assert hb['attributes'] == {'k': 'v'}
    assert hb['status'] == 'ok'
    heartbeat_id = hb['id']

    again = api.post('/heartbeat', {'origin': origin, 'timeout': 60, 'tags': ['contract']})
    assert again.status == 201
    assert again.json['id'] == heartbeat_id

    r = api.get(f'/heartbeat/{heartbeat_id}')
    assert r.status == 200
    assert_shape(r.json['heartbeat'], HEARTBEAT, 'heartbeat')

    r = api.get('/heartbeats')
    assert r.status == 200
    assert_shape(r.json, PAGED, 'heartbeats')
    assert heartbeat_id in {h['id'] for h in r.json['heartbeats']}

    r = api.delete(f'/heartbeat/{heartbeat_id}')
    assert r.status == 200
    assert_error(api.get(f'/heartbeat/{heartbeat_id}'), 404)


def test_heartbeat_defaults(api):
    r = api.post('/heartbeat', {'origin': f'contract/{uuid4().hex[:12]}'})
    assert r.status == 201, r.json
    hb = r.json['heartbeat']
    assert hb['type'] == 'Heartbeat'
    assert hb['timeout'] > 0
