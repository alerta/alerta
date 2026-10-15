from .shapes import ALERT, COUNTS, PAGED, assert_shape


def create(api, alert):
    r = api.post('/alert', alert)
    assert r.status == 201, r.json
    return r.json['id']


def test_list_alerts(api, alert, resource):
    alert_id = create(api, alert)

    r = api.get(f'/alerts?resource={resource}')
    assert r.status == 200
    assert_shape(r.json, PAGED, 'alerts')
    assert_shape(r.json, COUNTS, 'alerts')
    assert r.json['total'] == 1
    assert [a['id'] for a in r.json['alerts']] == [alert_id]
    assert_shape(r.json['alerts'][0], ALERT, 'alerts[0]')


def test_list_alerts_empty(api, resource):
    r = api.get(f'/alerts?resource={resource}')
    assert r.status == 200
    assert r.json['total'] == 0
    assert r.json['alerts'] == []


def test_filter_by_field(api, alert, resource):
    create(api, alert)
    create(api, dict(alert, event='disk_full', correlate=[], severity='minor'))

    assert api.get(f'/alerts?resource={resource}&severity=minor').json['total'] == 1
    assert api.get(f'/alerts?resource={resource}&event=node_down').json['total'] == 1
    assert api.get(f'/alerts?resource={resource}&severity=minor&severity=major').json['total'] == 2


def test_filter_excludes_with_negation(api, alert, resource):
    create(api, alert)
    create(api, dict(alert, event='disk_full', correlate=[], severity='minor'))

    r = api.get(f'/alerts?resource={resource}&severity!=minor')
    assert r.json['total'] == 1
    assert r.json['alerts'][0]['severity'] == 'major'


def test_filter_by_status(api, alert, resource):
    alert_id = create(api, alert)
    create(api, dict(alert, event='disk_full', correlate=[]))
    api.put(f'/alert/{alert_id}/action', {'action': 'ack'})

    r = api.get(f'/alerts?resource={resource}&status=ack')
    assert [a['id'] for a in r.json['alerts']] == [alert_id]


def test_lucene_query(api, alert, resource):
    create(api, alert)
    create(api, dict(alert, event='disk_full', correlate=[]))

    r = api.get(f'/alerts?q=resource:{resource} AND event:disk_full')
    assert r.status == 200, r.json
    assert r.json['total'] == 1
    assert r.json['alerts'][0]['event'] == 'disk_full'


def test_paging(api, alert, resource):
    for event in ('e1', 'e2', 'e3'):
        create(api, dict(alert, event=event, correlate=[]))

    first = api.get(f'/alerts?resource={resource}&page=1&page-size=2').json
    assert first['total'] == 3
    assert first['pageSize'] == 2
    assert first['pages'] == 2
    assert first['more'] is True
    assert len(first['alerts']) == 2

    second = api.get(f'/alerts?resource={resource}&page=2&page-size=2').json
    assert second['more'] is False
    assert len(second['alerts']) == 1
    assert {a['id'] for a in first['alerts']}.isdisjoint(a['id'] for a in second['alerts'])


def test_sort_by(api, alert, resource):
    create(api, dict(alert, event='e1', correlate=[], severity='minor'))
    create(api, dict(alert, event='e2', correlate=[], severity='critical'))
    create(api, dict(alert, event='e3', correlate=[], severity='warning'))

    r = api.get(f'/alerts?resource={resource}&sort-by=event')
    assert [a['event'] for a in r.json['alerts']] == ['e1', 'e2', 'e3']

    r = api.get(f'/alerts?resource={resource}&sort-by=-event')
    assert [a['event'] for a in r.json['alerts']] == ['e3', 'e2', 'e1']


def test_count(api, alert, resource):
    alert_id = create(api, alert)
    create(api, dict(alert, event='disk_full', correlate=[], severity='minor'))
    api.put(f'/alert/{alert_id}/action', {'action': 'ack'})

    r = api.get(f'/alerts/count?resource={resource}')
    assert r.status == 200
    assert_shape(r.json, COUNTS, 'count')
    assert r.json['total'] == 2
    assert r.json['severityCounts'] == {'major': 1, 'minor': 1}
    assert r.json['statusCounts'] == {'ack': 1, 'open': 1}


def test_history(api, alert, resource):
    create(api, alert)
    create(api, dict(alert, severity='critical'))

    r = api.get(f'/alerts/history?resource={resource}')
    assert r.status == 200
    assert r.json['status'] == 'ok'
    history = r.json['history']
    assert len(history) == 2
    for h in history:
        assert h['resource'] == resource
        assert h['environment'] == 'Production'
    assert {h['type'] for h in history} == {'new', 'severity'}


def test_top10(api, alert, resource):
    create(api, alert)
    create(api, alert)

    for kind in ('count', 'flapping', 'standing'):
        r = api.get(f'/alerts/top10/{kind}?resource={resource}')
        assert r.status == 200, kind
        assert r.json['status'] == 'ok'
        assert isinstance(r.json['top10'], list)
        assert isinstance(r.json['total'], int)

    top = api.get(f'/alerts/top10/count?resource={resource}').json['top10']
    assert top[0]['event'] == 'node_down'
    assert top[0]['count'] == 1
    assert top[0]['duplicateCount'] == 1
    assert top[0]['environments'] == ['Production']
    assert top[0]['services'] == ['Network']
    assert top[0]['resources'][0]['resource'] == resource
    assert {'id', 'href'} <= set(top[0]['resources'][0])


def test_environments(api, alert, resource):
    create(api, alert)

    r = api.get(f'/environments?resource={resource}')
    assert r.status == 200
    assert_shape(r.json, PAGED, 'environments')
    env = next(e for e in r.json['environments'] if e['environment'] == 'Production')
    assert env['count'] == 1
    assert {'severityCounts', 'statusCounts'} <= set(env)


def test_services(api, alert, resource):
    create(api, alert)

    r = api.get(f'/services?resource={resource}')
    assert r.status == 200
    svc = next(s for s in r.json['services'] if s['service'] == 'Network' and s['environment'] == 'Production')
    assert svc['count'] == 1
    assert svc['severityCounts'] == {'major': 1}
    assert svc['statusCounts'] == {'open': 1}


def test_groups(api, alert, resource):
    create(api, alert)

    r = api.get(f'/alerts/groups?resource={resource}')
    assert r.status == 200
    grp = r.json['groups'][0]
    assert grp['group'] == 'Contract'
    assert grp['environment'] == 'Production'
    assert grp['count'] == 1


def test_tags(api, alert, resource):
    create(api, alert)

    r = api.get(f'/alerts/tags?resource={resource}')
    assert r.status == 200
    tag = r.json['tags'][0]
    assert tag['tag'] == 'contract'
    assert tag['environment'] == 'Production'
    assert tag['count'] == 1
