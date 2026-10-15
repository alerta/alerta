from importlib.metadata import entry_points

import pytest

from alerta.exceptions import BlackoutPeriod, RateLimit, RejectException
from alerta.plugins import PluginBase

from .conftest import CONTRACT_URL
from .shapes import assert_error

pytestmark = pytest.mark.skipif(bool(CONTRACT_URL), reason='plugins load in-process only')


class Recorder(PluginBase):

    def __init__(self):
        super().__init__(name='contract-recorder')
        self.calls = []

    def pre_receive(self, alert, **kwargs):
        self.calls.append(('pre_receive', alert.resource, kwargs))
        return alert

    def post_receive(self, alert, **kwargs):
        self.calls.append(('post_receive', alert.id, kwargs))

    def status_change(self, alert, status, text, **kwargs):
        self.calls.append(('status_change', status, text))

    def take_action(self, alert, action, text, **kwargs):
        self.calls.append(('take_action', action, text, kwargs.get('timeout')))

    def post_action(self, alert, action, text, **kwargs):
        self.calls.append(('post_action', action, text))

    def take_note(self, alert, text, **kwargs):
        self.calls.append(('take_note', text))

    def delete(self, alert, **kwargs):
        self.calls.append(('delete', alert.id))
        return True


@pytest.fixture
def install(client):
    from alerta.app import plugins
    installed = []

    def _install(plugin):
        plugins.plugins[plugin.name] = plugin
        installed.append(plugin.name)
        return plugin

    yield _install
    for name in installed:
        plugins.plugins.pop(name, None)


def names(plugin, hook):
    return [c for c in plugin.calls if c[0] == hook]


def test_hooks_called_on_receive(api, alert, install):
    rec = install(Recorder())

    alert_id = api.post('/alert', alert).json['id']

    assert names(rec, 'pre_receive')[0][1] == alert['resource']
    assert 'config' in names(rec, 'pre_receive')[0][2]
    assert names(rec, 'post_receive')[0][1] == alert_id


def test_pre_receive_modifies_alert_before_storage(api, alert, install):
    class Enrich(Recorder):
        def pre_receive(self, alert, **kwargs):
            alert.tags.append('enriched')
            alert.attributes['owner'] = 'team-a'
            return alert

    install(Enrich())
    a = api.post('/alert', alert).json['alert']

    assert 'enriched' in a['tags']
    assert a['attributes']['owner'] == 'team-a'


def test_post_receive_returned_alert_is_persisted(api, alert, install):
    class Annotate(Recorder):
        def post_receive(self, alert, **kwargs):
            alert.tags.append('posted')
            alert.attributes['ticket'] = 'OPS-1'
            return alert

    install(Annotate())
    alert_id = api.post('/alert', alert).json['id']

    stored = api.get(f'/alert/{alert_id}').json['alert']
    assert 'posted' in stored['tags']
    assert stored['attributes']['ticket'] == 'OPS-1'


@pytest.mark.parametrize('exc,status', [
    (RejectException('rejected by contract'), 403),
    (RateLimit('rate limited by contract'), 429),
    (BlackoutPeriod('blackout by contract'), 202),
])
def test_pre_receive_exception_maps_to_status(api, alert, install, exc, status):
    class Raise(Recorder):
        def pre_receive(self, alert, **kwargs):
            raise exc

    install(Raise())
    r = api.post('/alert', alert)

    assert r.status == status, r.json
    assert str(exc) in r.json['message']


def test_legacy_signatures_without_kwargs(api, alert, install):
    class Legacy(PluginBase):
        def __init__(self):
            super().__init__(name='contract-legacy')
            self.calls = []

        def pre_receive(self, alert):
            self.calls.append('pre_receive')
            return alert

        def post_receive(self, alert):
            self.calls.append('post_receive')

        def status_change(self, alert, status, text):
            self.calls.append('status_change')

    legacy = install(Legacy())
    alert_id = api.post('/alert', alert).json['id']
    r = api.put(f'/alert/{alert_id}/status', {'status': 'ack', 'text': 'legacy'})

    assert r.status == 200, r.json
    assert legacy.calls == ['pre_receive', 'post_receive', 'status_change']


def test_action_hooks(api, alert, install):
    rec = install(Recorder())
    alert_id = api.post('/alert', alert).json['id']

    api.put(f'/alert/{alert_id}/action', {'action': 'shelve', 'text': 'later', 'timeout': 600})

    assert names(rec, 'take_action') == [('take_action', 'shelve', 'later', 600)]
    assert names(rec, 'post_action') == [('post_action', 'shelve', 'later')]
    assert ('status_change', 'shelved', 'later') in names(rec, 'status_change')


def test_take_action_can_rewrite_action(api, alert, install):
    class Rewrite(Recorder):
        def take_action(self, alert, action, text, **kwargs):
            return alert, 'shelve', 'rewritten', kwargs.get('timeout')

    install(Rewrite())
    alert_id = api.post('/alert', alert).json['id']
    api.put(f'/alert/{alert_id}/action', {'action': 'ack'})

    a = api.get(f'/alert/{alert_id}').json['alert']
    assert a['status'] == 'shelved'
    assert a['history'][-1]['text'] == 'rewritten'


def test_status_change_hook(api, alert, install):
    rec = install(Recorder())
    alert_id = api.post('/alert', alert).json['id']

    api.put(f'/alert/{alert_id}/status', {'status': 'ack', 'text': 'manual'})

    assert ('status_change', 'ack', 'manual') in names(rec, 'status_change')


def test_take_note_hook(api, alert, install):
    rec = install(Recorder())
    alert_id = api.post('/alert', alert).json['id']

    api.put(f'/alert/{alert_id}/note', {'text': 'hello'})

    assert names(rec, 'take_note') == [('take_note', 'hello')]


def test_delete_hook(api, alert, install):
    rec = install(Recorder())
    alert_id = api.post('/alert', alert).json['id']

    assert api.delete(f'/alert/{alert_id}').status == 200
    assert names(rec, 'delete') == [('delete', alert_id)]


def test_delete_rejected_by_plugin(api, alert, install):
    class Guard(Recorder):
        def delete(self, alert, **kwargs):
            raise RejectException('protected')

    install(Guard())
    alert_id = api.post('/alert', alert).json['id']

    assert_error(api.delete(f'/alert/{alert_id}'), 400)
    assert api.get(f'/alert/{alert_id}').status == 200


def test_optional_hooks_may_be_unimplemented(api, alert, install):
    class Minimal(PluginBase):
        def __init__(self):
            super().__init__(name='contract-minimal')

        def pre_receive(self, alert, **kwargs):
            return alert

        def post_receive(self, alert, **kwargs):
            return None

        def status_change(self, alert, status, text, **kwargs):
            return None

    install(Minimal())
    alert_id = api.post('/alert', alert).json['id']

    assert api.put(f'/alert/{alert_id}/action', {'action': 'ack'}).status == 200
    assert api.put(f'/alert/{alert_id}/note', {'text': 'n'}).status == 201
    assert api.delete(f'/alert/{alert_id}').status == 200


def test_get_config_prefers_environment(monkeypatch):
    monkeypatch.setenv('CONTRACT_SETTING', 'from-env')

    assert PluginBase.get_config('CONTRACT_SETTING', default='d', config={'CONTRACT_SETTING': 'from-config'}) == 'from-env'
    assert PluginBase.get_config('CONTRACT_OTHER', default='d', config={'CONTRACT_OTHER': 'from-config'}) == 'from-config'
    assert PluginBase.get_config('CONTRACT_MISSING', default='d', config={}) == 'd'


def test_entry_point_groups():
    assert {'reject', 'blackout', 'heartbeat'} <= {e.name for e in entry_points(group='alerta.plugins')}
    assert {'prometheus', 'grafana', 'cloudwatch'} <= {e.name for e in entry_points(group='alerta.webhooks')}
