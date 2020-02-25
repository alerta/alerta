import json
import unittest
from uuid import uuid4

from alerta.app import create_app, db


class ForwarderTestCase(unittest.TestCase):

    def setUp(self):

        test_config = {
            'DEBUG': True,
            'TESTING': True,
            'AUTH_REQUIRED': False,
            'BASE_URL': 'http://localhost:8080',
            'PLUGINS': ['forwarder']
        }

        FWD_DESTINATIONS = [
            # ('http://localhost:9000', {'username': 'user', 'password': 'pa55w0rd', 'timeout': 10}, ['alerts', 'actions']),  # BasicAuth
            ('https://httpbin.org/anything', dict(username='foo', password='bar', ssl_verify=False), ['*']),
            # ('http://localhost:9000', {'key': 'access-key', 'secret': 'secret-key'}, ['alerts', 'actions']),  # Hawk HMAC
            # ('http://localhost:9000', {'key': 'my-api-key'}, ['alerts', 'actions']),  # API key
            # ('http://localhost:9000', {'token': 'bearer-token'}, ['alerts', 'actions']),  # Bearer token
        ]

        test_config['FWD_DESTINATIONS'] = FWD_DESTINATIONS

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

    def tearDown(self):
        db.destroy()

    def test_forward_alert(self):

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

    def test_forward_ack(self):

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

    def test_forward_action(self):

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
            ['Development', 'Production', 'more', 'other', 'that', 'the', 'this']))
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

    def test_forward_delete(self):

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

    def test_forward_heartbeat(self):
        # FIXME: currently not possible
        pass
