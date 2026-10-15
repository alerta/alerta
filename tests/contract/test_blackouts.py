import pytest

from .shapes import BLACKOUT, PAGED, assert_error, assert_shape


def test_blackout_lifecycle(api, alert, resource):
    r = api.post('/blackout', {'environment': 'Production', 'resource': resource, 'text': 'maintenance'})
    assert r.status == 201, r.json
    assert r.json['status'] == 'ok'
    bo = r.json['blackout']
    assert_shape(bo, BLACKOUT, 'blackout')
    assert bo['id'] == r.json['id']
    assert bo['resource'] == resource
    assert bo['status'] == 'active'
    assert bo['duration'] > 0
    blackout_id = bo['id']

    r = api.get(f'/blackout/{blackout_id}')
    assert r.status == 200
    assert_shape(r.json['blackout'], BLACKOUT, 'blackout')

    r = api.get('/blackouts')
    assert r.status == 200
    assert_shape(r.json, PAGED, 'blackouts')
    assert blackout_id in {b['id'] for b in r.json['blackouts']}

    r = api.post('/alert', alert)
    assert r.status == 202, r.json
    assert r.json['status'] == 'ok'
    assert 'blackout' in r.json['message'].lower()

    r = api.put(f'/blackout/{blackout_id}', {'text': 'extended'})
    assert r.status == 200, r.json
    assert api.get(f'/blackout/{blackout_id}').json['blackout']['text'] == 'extended'

    r = api.delete(f'/blackout/{blackout_id}')
    assert r.status == 200
    assert_error(api.get(f'/blackout/{blackout_id}'), 404)

    assert api.post('/alert', alert).status == 201


def test_blackout_does_not_match_other_resource(api, alert, resource):
    api.post('/blackout', {'environment': 'Production', 'resource': resource + '-other'})

    assert api.post('/alert', alert).status == 201


def test_blackout_requires_environment(api, resource):
    assert_error(api.post('/blackout', {'resource': resource}), 400)


@pytest.mark.xfail(strict=True, reason='9.x: remaining is a decimal string on GET (Postgres) and null (MongoDB)')
def test_blackout_remaining_is_numeric(api, resource):
    r = api.post('/blackout', {'environment': 'Production', 'resource': resource})
    blackout_id = r.json['id']

    for remaining in (r.json['blackout']['remaining'], api.get(f'/blackout/{blackout_id}').json['blackout']['remaining']):
        assert isinstance(remaining, (int, float)) and not isinstance(remaining, bool)
