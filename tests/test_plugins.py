import json
import os
import unittest
from uuid import uuid4

from alerta.app import create_app, db, plugins
from alerta.plugins import PluginBase, app


class PluginsTestCase(unittest.TestCase):

    def setUp(self):

        test_config = {
            'TESTING': True,
            'AUTH_REQUIRED': False,
            'PLUGINS': ['reject']
        }
        os.environ['ALLOWED_ENVIRONMENTS'] = 'Production,Staging,Development'

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
            'service': ['Network'],  # alert will be accepted because service defined
            'severity': 'warning',
            'correlate': ['node_down', 'node_marginal', 'node_up'],
            'tags': ['three', 'four']
        }

        self.critical_alert = {
            'event': 'node_down',
            'resource': self.resource,
            'environment': 'Production',
            'service': ['Network'],
            'severity': 'critical',
            'correlate': ['node_down', 'node_marginal', 'node_up'],
            'tags': []
        }

        self.headers = {
            'Content-type': 'application/json'
        }

        plugins.plugins['old1'] = OldPlugin1()
        plugins.plugins['test1'] = CustPlugin1()
        plugins.plugins['test2'] = CustPlugin2()
        plugins.plugins['test3'] = CustPlugin3()

    def tearDown(self):

        del plugins.plugins['test1']
        del plugins.plugins['test2']
        del plugins.plugins['test3']

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
        self.assertRegex(data['id'], '[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}')

    def test_status_update(self):

        # create alert that will be accepted
        response = self.client.post('/alert', data=json.dumps(self.accept_alert), headers=self.headers)
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data.decode('utf-8'))
        self.assertEqual(data['status'], 'ok')
        self.assertRegex(data['id'], '[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}')
        self.assertEqual(data['alert']['attributes']['aaa'], 'post1')

        alert_id = data['id']

        # ack alert
        response = self.client.put('/alert/' + alert_id + '/status',
                                   data=json.dumps({'status': 'ack', 'text': 'input'}), headers=self.headers)
        self.assertEqual(response.status_code, 200)
        response = self.client.get('/alert/' + alert_id)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data.decode('utf-8'))
        self.assertEqual(data['alert']['attributes']['old'], 'post1')
        self.assertEqual(data['alert']['attributes']['aaa'], 'post1')

        # alert status, tags, attributes and history text modified by plugin1 & plugin2
        self.assertEqual(data['alert']['status'], 'assign')
        self.assertEqual(sorted(data['alert']['tags']), sorted(
            ['Development', 'Production', 'more', 'other', 'that', 'the', 'this']))
        self.assertEqual(data['alert']['attributes']['foo'], 'bar')
        self.assertEqual(data['alert']['attributes']['baz'], 'quux')
        self.assertNotIn('abc', data['alert']['attributes'])
        self.assertEqual(data['alert']['attributes']['xyz'], 'down')
        self.assertEqual(data['alert']['history'][-1]['text'], 'input-plugin1-plugin3')

    def test_take_action(self):

        plugins.plugins['action1'] = CustActionPlugin1()

        # create alert
        response = self.client.post('/alert', json=self.critical_alert, headers=self.headers)
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data.decode('utf-8'))
        self.assertEqual(data['alert']['tags'], ['Production', 'Development'])
        self.assertEqual(data['alert']['attributes'], {'aaa': 'post1', 'ip': '127.0.0.1', 'old': 'post1'})

        alert_id = data['id']

        # create ticket for alert
        payload = {
            'action': 'createTicket',
            'text': 'ticket created by bob'
        }
        response = self.client.put('/alert/' + alert_id + '/action', json=payload, headers=self.headers)
        self.assertEqual(response.status_code, 200)

        # check status=assign
        response = self.client.get('/alert/' + alert_id)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data.decode('utf-8'))
        self.assertEqual(data['alert']['status'], 'assign')
        self.assertEqual(sorted(data['alert']['tags']), sorted(
            ['Development', 'Production', 'more', 'other', 'that', 'the', 'this', 'aSingleTag', 'a:Triple:Tag']))
        self.assertEqual(data['alert']['history'][1]['text'],
                         'ticket created by bob (ticket #12345)-plugin1-plugin3', data['alert']['history'])

        # update ticket for alert
        payload = {
            'action': 'updateTicket',
            'text': 'ticket updated by bob'
        }
        response = self.client.put('/alert/' + alert_id + '/action', json=payload, headers=self.headers)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data.decode('utf-8'))

        # check no change in status, new alert text
        response = self.client.get('/alert/' + alert_id)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data.decode('utf-8'))
        self.assertEqual(data['alert']['status'], 'assign')
        self.assertEqual(data['alert']['attributes']['up'], 'down')
        self.assertEqual(data['alert']['history'][2]['text'],
                         'ticket updated by bob (ticket #12345)-plugin1-plugin3', data['alert']['history'])

        # update ticket for alert
        payload = {
            'action': 'resolveTicket',
            'text': 'ticket resolved by bob'
        }
        response = self.client.put('/alert/' + alert_id + '/action', json=payload, headers=self.headers)
        self.assertEqual(response.status_code, 200)

        # check status=closed
        response = self.client.get('/alert/' + alert_id)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data.decode('utf-8'))
        self.assertEqual(data['alert']['status'], 'closed')
        self.assertIn('true', data['alert']['tags'])
        self.assertEqual(data['alert']['history'][3]['text'],
                         'ticket resolved by bob (ticket #12345)-plugin1-plugin3', data['alert']['history'])

    def test_delete(self):

        plugins.plugins['delete1'] = CustDeletePlugin1()
        plugins.plugins['delete2'] = CustDeletePlugin2()

        # create alert
        response = self.client.post('/alert', json=self.critical_alert, headers=self.headers)
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data.decode('utf-8'))

        alert_id = data['id']

        # delete alert
        response = self.client.delete('/alert/' + alert_id, headers=self.headers)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data.decode('utf-8'))

        # check deleted
        response = self.client.get('/alert/' + alert_id)
        self.assertEqual(response.status_code, 404)

    def test_heartbeat_alert(self):

        self.heartbeat_alert = {
            'event': 'Heartbeat',
            'resource': 'hb01',
            'environment': 'Production',
            'service': ['Svc1'],
            'severity': 'informational',
        }

        # create alert
        response = self.client.post('/alert', json=self.heartbeat_alert, headers=self.headers)
        self.assertEqual(response.status_code, 202)
        data = json.loads(response.data.decode('utf-8'))
        self.assertEqual(data['message'], 'Alert converted to Heartbeat')

    def test_add_and_remove_tags(self):

        plugins.plugins['action1'] = CustActionPlugin1()
        plugins.plugins['action2'] = CustActionPlugin2()

        # create alert
        response = self.client.post('/alert', json=self.critical_alert, headers=self.headers)
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data.decode('utf-8'))

        alert_id = data['id']

        payload = {
            'action': 'ack',
            'text': 'this is a test'
        }
        response = self.client.put('/alert/' + alert_id + '/action', json=payload, headers=self.headers)
        self.assertEqual(response.status_code, 200)

        response = self.client.get('/alert/' + alert_id)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data.decode('utf-8'))
        self.assertIn('aSingleTag', data['alert']['tags'])
        self.assertIn('a:Triple:Tag', data['alert']['tags'])
        self.assertNotIn('aDouble:Tag', data['alert']['tags'])


class OldPlugin1(PluginBase):

    def pre_receive(self, alert):
        ALLOWED_ENVIRONMENTS = app.config['ALLOWED_ENVIRONMENTS']
        alert.attributes['old'] = 'pre1'
        alert.tags = ALLOWED_ENVIRONMENTS
        return alert

    def post_receive(self, alert):
        alert.attributes['old'] = 'post1'
        return alert

    def status_change(self, alert, status, text):
        return alert, status, text


class CustPlugin1(PluginBase):

    def pre_receive(self, alert, **kwargs):
        alert.attributes['aaa'] = 'pre1'
        return alert

    def post_receive(self, alert, **kwargs):
        alert.attributes['aaa'] = 'post1'
        return alert

    def status_change(self, alert, status, text, **kwargs):
        alert.tags.extend(['this', 'that', 'the', 'other'])
        alert.attributes['foo'] = 'bar'
        alert.attributes['abc'] = 123
        alert.attributes['xyz'] = 'up'

        text = text + '-plugin1'

        return alert, status, text


class CustPlugin2(PluginBase):

    def pre_receive(self, alert, **kwargs):
        return alert

    def post_receive(self, alert, **kwargs):
        return alert

    def status_change(self, alert, status, text, **kwargs):
        # alert.tags.extend(['skip?'])
        # status = 'skipped'
        # text = text + '-plugin2'
        return  # does not return alert, status, text


class CustPlugin3(PluginBase):

    def pre_receive(self, alert, **kwargs):
        return alert

    def post_receive(self, alert, **kwargs):
        return alert

    def status_change(self, alert, status, text, **kwargs):
        alert.tags.extend(['this', 'that', 'more'])
        alert.attributes['baz'] = 'quux'
        if alert.attributes['abc'] == 123:
            alert.attributes['abc'] = None
        alert.attributes['xyz'] = 'down'

        if status == 'ack':
            status = 'assign'

        text = text + '-plugin3'

        return alert, status, text


class CustActionPlugin1(PluginBase):

    def pre_receive(self, alert, **kwargs):
        return alert

    def post_receive(self, alert, **kwargs):
        return

    def status_change(self, alert, status, text, **kwargs):
        return alert, status, text

    def take_action(self, alert, action, text, **kwargs):

        if action == 'createTicket':
            alert.status = 'ack'
            text = text + ' (ticket #12345)'

        if action == 'updateTicket':
            # do not change status
            alert.attributes['up'] = 'down'
            text = text + ' (ticket #12345)'

        if action == 'resolveTicket':
            alert.status = 'closed'
            alert.tags.append('true')
            text = text + ' (ticket #12345)'

        alert.tags.append('aSingleTag')  # one tag only
        alert.tags.extend(['aDouble:Tag', 'a:Triple:Tag'])  # multiple tags as a list

        return alert, action, text


class CustActionPlugin2(PluginBase):

    def pre_receive(self, alert, **kwargs):
        return alert

    def post_receive(self, alert, **kwargs):
        return

    def status_change(self, alert, status, text, **kwargs):
        return alert, status, text

    def take_action(self, alert, action, text, **kwargs):

        alert.tags.remove('aDouble:Tag')

        return alert, action, text


class CustDeletePlugin1(PluginBase):

    def pre_receive(self, alert, **kwargs):
        return alert

    def post_receive(self, alert, **kwargs):
        return

    def status_change(self, alert, status, text, **kwargs):
        return alert, status, text

    def take_action(self, alert, action, text, **kwargs):
        return alert, action, text

    def delete(self, alert, **kwargs):
        return True


class CustDeletePlugin2(PluginBase):

    def pre_receive(self, alert, **kwargs):
        return alert

    def post_receive(self, alert, **kwargs):
        return

    def status_change(self, alert, status, text, **kwargs):
        return alert, status, text

    def take_action(self, alert, action, text, **kwargs):
        return alert, action, text

    def delete(self, alert, **kwargs):
        return True
