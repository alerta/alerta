import pytest

from .shapes import ALERT, HISTORY, NOTE, assert_error, assert_shape


def create(api, alert):
    r = api.post('/alert', alert)
    assert r.status == 201, r.json
    return r.json


def test_receive_new_alert(api, alert):
    body = create(api, alert)

    assert body['status'] == 'ok'
    assert body['id'] == body['alert']['id']
    a = body['alert']
    assert_shape(a, ALERT, 'alert')
    for key in ('resource', 'event', 'environment', 'severity', 'correlate', 'service', 'group',
                'value', 'text', 'tags', 'origin', 'type', 'timeout', 'rawData'):
        assert a[key] == alert[key], key
    assert a['attributes']['region'] == 'eu-west-1'
    assert a['status'] == 'open'
    assert a['duplicateCount'] == 0
    assert a['repeat'] is False
    assert a['trendIndication'] == 'moreSevere'
    assert a['href'].endswith('/alert/' + a['id'])


def test_new_alert_history(api, alert):
    a = create(api, alert)['alert']

    assert len(a['history']) == 1
    h = a['history'][0]
    assert_shape(h, HISTORY, 'history')
    assert h['type'] == 'new'
    assert h['severity'] == 'major'
    assert h['status'] == 'open'


def test_minimal_alert_defaults(api, resource):
    a = create(api, {'resource': resource, 'event': 'cpu_high', 'environment': 'Production', 'service': ['Web']})['alert']

    assert_shape(a, ALERT, 'alert')
    assert a['severity'] == 'normal'
    assert a['tags'] == []
    assert a['correlate'] == []
    assert a['status'] == 'closed'


def test_duplicate_alert(api, alert):
    first = create(api, alert)
    second = create(api, alert)

    assert second['id'] == first['id']
    a = second['alert']
    assert a['duplicateCount'] == 1
    assert a['repeat'] is True
    assert a['lastReceiveId'] != first['alert']['lastReceiveId']

    third = create(api, alert)
    assert third['alert']['duplicateCount'] == 2


def test_severity_change_correlates(api, alert):
    first = create(api, alert)
    second = create(api, dict(alert, severity='critical'))

    assert second['id'] == first['id']
    a = second['alert']
    assert a['severity'] == 'critical'
    assert a['previousSeverity'] == 'major'
    assert a['trendIndication'] == 'moreSevere'
    assert a['duplicateCount'] == 0
    assert a['repeat'] is False

    third = create(api, dict(alert, severity='minor'))
    assert third['alert']['previousSeverity'] == 'critical'
    assert third['alert']['trendIndication'] == 'lessSevere'


def test_correlated_event_replaces_event(api, alert):
    first = create(api, alert)
    second = create(api, dict(alert, event='node_marginal', severity='minor'))

    assert second['id'] == first['id']
    assert second['alert']['event'] == 'node_marginal'


def test_uncorrelated_event_is_new_alert(api, alert):
    first = create(api, alert)
    other = create(api, dict(alert, event='disk_full', correlate=[]))

    assert other['id'] != first['id']


def test_normal_severity_closes_alert(api, alert):
    first = create(api, alert)
    cleared = create(api, dict(alert, event='node_up', severity='normal'))

    assert cleared['id'] == first['id']
    assert cleared['alert']['status'] == 'closed'
    assert cleared['alert']['event'] == 'node_up'


def test_closed_alert_reopens_on_new_severity(api, alert):
    create(api, alert)
    create(api, dict(alert, event='node_up', severity='normal'))
    reopened = create(api, alert)

    assert reopened['alert']['status'] == 'open'


def test_get_alert(api, alert):
    alert_id = create(api, alert)['id']

    r = api.get(f'/alert/{alert_id}')
    assert r.status == 200
    assert r.json['status'] == 'ok'
    assert r.json['total'] == 1
    assert_shape(r.json['alert'], ALERT, 'alert')
    assert r.json['alert']['id'] == alert_id


def test_get_alert_by_short_id(api, alert):
    alert_id = create(api, alert)['id']

    r = api.get(f'/alert/{alert_id[:8]}')
    assert r.status == 200
    assert r.json['alert']['id'] == alert_id


def test_get_unknown_alert(api):
    assert_error(api.get('/alert/00000000-0000-0000-0000-000000000000'), 404)


def test_delete_alert(api, alert):
    alert_id = create(api, alert)['id']

    r = api.delete(f'/alert/{alert_id}')
    assert r.status == 200
    assert r.json['status'] == 'ok'
    assert_error(api.get(f'/alert/{alert_id}'), 404)


def test_delete_unknown_alert(api):
    assert_error(api.delete('/alert/00000000-0000-0000-0000-000000000000'), 404)


@pytest.mark.parametrize('field', ['resource', 'event'])
def test_missing_mandatory_field(api, alert, field):
    body = dict(alert)
    del body[field]

    r = api.post('/alert', body)
    assert_error(r, 400)
    assert field in r.json['message']


def test_disallowed_environment(api, alert):
    assert_error(api.post('/alert', dict(alert, environment='NotAnEnvironment')), 403)


@pytest.mark.xfail(strict=True, reason='9.x returns 500 for an invalid severity')
def test_invalid_severity(api, alert):
    assert_error(api.post('/alert', dict(alert, severity='bogus')), 400)


@pytest.mark.parametrize('action,status', [
    ('ack', 'ack'),
    ('shelve', 'shelved'),
    ('close', 'closed'),
])
def test_action_sets_status(api, alert, action, status):
    alert_id = create(api, alert)['id']

    r = api.put(f'/alert/{alert_id}/action', {'action': action, 'text': f'{action} by contract test'})
    assert r.status == 200, r.json
    assert r.json['status'] == 'ok'
    assert api.get(f'/alert/{alert_id}').json['alert']['status'] == status


@pytest.mark.parametrize('action,undo', [('ack', 'unack'), ('shelve', 'unshelve')])
def test_undo_action_reopens(api, alert, action, undo):
    alert_id = create(api, alert)['id']

    api.put(f'/alert/{alert_id}/action', {'action': action})
    r = api.put(f'/alert/{alert_id}/action', {'action': undo})
    assert r.status == 200, r.json
    assert api.get(f'/alert/{alert_id}').json['alert']['status'] == 'open'


def test_action_recorded_in_history(api, alert):
    alert_id = create(api, alert)['id']

    api.put(f'/alert/{alert_id}/action', {'action': 'ack', 'text': 'looking'})
    history = api.get(f'/alert/{alert_id}').json['alert']['history']
    last = history[-1]
    assert_shape(last, HISTORY, 'history')
    assert last['type'] == 'ack'
    assert last['status'] == 'ack'
    assert last['text'] == 'looking'


def test_invalid_action_for_status(api, alert):
    alert_id = create(api, alert)['id']
    api.put(f'/alert/{alert_id}/action', {'action': 'close'})

    assert_error(api.put(f'/alert/{alert_id}/action', {'action': 'ack'}), 409)


def test_set_status(api, alert):
    alert_id = create(api, alert)['id']

    r = api.put(f'/alert/{alert_id}/status', {'status': 'ack', 'text': 'manual'})
    assert r.status == 200, r.json
    assert r.json['status'] == 'ok'
    assert api.get(f'/alert/{alert_id}').json['alert']['status'] == 'ack'


def test_tag_and_untag(api, alert):
    alert_id = create(api, alert)['id']

    r = api.put(f'/alert/{alert_id}/tag', {'tags': ['one', 'two']})
    assert r.status == 200, r.json
    tags = api.get(f'/alert/{alert_id}').json['alert']['tags']
    assert {'contract', 'one', 'two'} <= set(tags)

    r = api.put(f'/alert/{alert_id}/untag', {'tags': ['one']})
    assert r.status == 200, r.json
    tags = api.get(f'/alert/{alert_id}').json['alert']['tags']
    assert 'one' not in tags
    assert 'two' in tags


def test_update_attributes(api, alert):
    alert_id = create(api, alert)['id']

    r = api.put(f'/alert/{alert_id}/attributes', {'attributes': {'owner': 'team-a', 'region': None}})
    assert r.status == 200, r.json
    attributes = api.get(f'/alert/{alert_id}').json['alert']['attributes']
    assert attributes['owner'] == 'team-a'
    assert 'region' not in attributes


def test_notes(api, alert):
    alert_id = create(api, alert)['id']

    r = api.put(f'/alert/{alert_id}/note', {'text': 'first note'})
    assert r.status == 201, r.json
    assert_shape(r.json['note'], NOTE, 'note')
    note_id = r.json['id']
    assert r.json['note']['text'] == 'first note'
    assert r.json['note']['related']['alert'] == alert_id

    r = api.get(f'/alert/{alert_id}/notes')
    assert r.status == 200
    assert r.json['total'] == 1
    assert r.json['notes'][0]['id'] == note_id

    r = api.put(f'/alert/{alert_id}/note/{note_id}', {'text': 'edited'})
    assert r.status == 200, r.json
    assert api.get(f'/alert/{alert_id}/notes').json['notes'][0]['text'] == 'edited'

    r = api.delete(f'/alert/{alert_id}/note/{note_id}')
    assert r.status == 200, r.json
    assert api.get(f'/alert/{alert_id}/notes').json['total'] == 0
