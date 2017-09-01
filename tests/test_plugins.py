
import unittest

try:
    import simplejson as json
except ImportError:
    import json

from uuid import uuid4

from alerta.app import create_app, db
from alerta.plugins import PluginBase
from alerta.app import plugins


class PluginsTestCase(unittest.TestCase):

    def setUp(self):

        test_config = {
            'TESTING': True,
            'AUTH_REQUIRED': False,
            'PLUGINS': ['reject']
        }
        self.app = create_app(test_config)
        self.client = self.app.test_client()

        self.resource = str(uuid4()).upper()[:8]

        self.reject_alert = {
            'event': 'node_marginal',
            'resource': self.resource,
            'environment': 'Production',
            'service': [],  # alert will be rejected because service not defined
            'severity': 'warning',
            'correlate': ['node_down', 'node_marginal', 'node_up'],
            'tags': ['one', 'two']
        }

        self.accept_alert = {
            'event': 'node_marginal',
            'resource': self.resource,
            'environment': 'Production',
            'service': ['Network'],  # alert will be accepted because service not defined
            'severity': 'warning',
            'correlate': ['node_down', 'node_marginal', 'node_up'],
            'tags': ['three', 'four']
        }

        self.headers = {
            'Content-type': 'application/json'
        }

        plugins.plugins['test1'] = TestPlugin1()
        plugins.plugins['test2'] = TestPlugin2()
        plugins.plugins['test3'] = TestPlugin3()

    def tearDown(self):

        del plugins.plugins['test1']
        del plugins.plugins['test2']
        del plugins.plugins['test3']

        with self.app.app_context():
            db.destroy()

    def test_reject_alert(self):

        # create alert that will be rejected
        response = self.client.post('/alert', data=json.dumps(self.reject_alert), headers=self.headers)
        self.assertEqual(response.status_code, 403)
        data = json.loads(response.data.decode('utf-8'))
        self.assertEqual(data['status'], 'error')
        self.assertEqual(data['message'], '[POLICY] Alert must define a service')

        # create alert that will be accepted
        response = self.client.post('/alert', data=json.dumps(self.accept_alert), headers=self.headers)
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data.decode('utf-8'))
        self.assertEqual(data['status'], 'ok')
        self.assertRegexpMatches(data['id'], '[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}')

    def test_status_update(self):

        # create alert that will be accepted
        response = self.client.post('/alert', data=json.dumps(self.accept_alert), headers=self.headers)
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data.decode('utf-8'))
        self.assertEqual(data['status'], 'ok')
        self.assertRegexpMatches(data['id'], '[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}')
        self.assertEqual(data['alert']['attributes']['aaa'], 'post1')

        alert_id = data['id']

        # ack alert
        response = self.client.put('/alert/' + alert_id + '/status', data=json.dumps({'status': 'ack', 'text': 'input'}), headers=self.headers)
        self.assertEqual(response.status_code, 200)
        response = self.client.get('/alert/' + alert_id)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data.decode('utf-8'))
        self.assertEqual(data['alert']['attributes']['aaa'], 'post1')

        # alert status, tags, attributes and history text modified by plugin1 & plugin2
        self.assertEqual(data['alert']['status'], 'owned')
        self.assertListEqual(data['alert']['tags'], ['three', 'four', 'this', 'that', 'the', 'other', 'more'])
        self.assertEqual(data['alert']['attributes']['foo'], 'bar')
        self.assertEqual(data['alert']['attributes']['baz'], 'quux')
        self.assertNotIn('abc', data['alert']['attributes'])
        self.assertEqual(data['alert']['attributes']['xyz'], 'down')
        self.assertEqual(data['alert']['history'][-1]['text'], 'input-plugin1-plugin3')


class TestPlugin1(PluginBase):

    def pre_receive(self, alert):
        alert.attributes['aaa'] = 'pre1'
        return alert

    def post_receive(self, alert):
        alert.attributes['aaa'] = 'post1'
        return alert

    def status_change(self, alert, status, text):
        alert.tags.extend(['this', 'that', 'the', 'other'])
        alert.attributes['foo'] = 'bar'
        alert.attributes['abc'] = 123
        alert.attributes['xyz'] = 'up'
        status = 'assign'
        text = text + '-plugin1'
        return alert, status, text


class TestPlugin2(PluginBase):

    def pre_receive(self, alert):
        return alert

    def post_receive(self, alert):
        return alert

    def status_change(self, alert, status, text):
        # alert.tags.extend(['skip?'])
        status = 'skipped'
        text = text + '-plugin2'
        return # does not return alert, status, text


class TestPlugin3(PluginBase):

    def pre_receive(self, alert):
        return alert

    def post_receive(self, alert):
        return alert

    def status_change(self, alert, status, text):
        alert.tags.extend(['this', 'that', 'more'])
        alert.attributes['baz'] = 'quux'
        if alert.attributes['abc'] == 123:
            alert.attributes['abc'] = None
        alert.attributes['xyz'] = 'down'
        status = 'owned'
        text = text + '-plugin3'
        return alert, status, text
