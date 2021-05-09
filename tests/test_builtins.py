import json
import os
import unittest
from uuid import uuid4

from alerta.app import create_app, db, plugins
from alerta.models.enums import Scope
from alerta.models.key import ApiKey


class BuiltinsTestCase(unittest.TestCase):

    def setUp(self):

        test_config = {
            'TESTING': True,
            'AUTH_REQUIRED': True,
            'PLUGINS': ['remote_ip', 'reject', 'heartbeat', 'blackout', 'acked_by', 'forwarder']
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

        self.ok_alert = {
            'event': 'node_up',
            'resource': self.resource,
            'environment': 'Production',
            'service': ['Network'],
            'severity': 'ok',
            'correlate': ['node_down', 'node_marginal', 'node_up'],
            'tags': []
        }
        with self.app.test_request_context('/'):
            self.app.preprocess_request()
            self.api_key = ApiKey(
                user='admin@alerta.io',
                scopes=[Scope.admin, Scope.read, Scope.write],
                text='demo-key'
            )
            self.api_key.create()

        self.headers = {
            'Authorization': f'Key {self.api_key.key}',
            'Content-type': 'application/json',
            'X-Forwarded-For': '172.217.20.36'
        }

    def tearDown(self):
        plugins.plugins.clear()
        db.destroy()

    def test_remote_ip_alert(self):

        # create alert
        response = self.client.post('/alert', json=self.critical_alert, headers=self.headers)
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data.decode('utf-8'))
        self.assertEqual(data['alert']['attributes']['ip'], '172.217.20.36')

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

    # XXX - blackout plugin tested extensively in test_blackouts.py

    def test_acked_by_plugin(self):

        # create alert
        response = self.client.post('/alert', json=self.critical_alert, headers=self.headers)
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data.decode('utf-8'))

        alert_id = data['id']

        # ack alert
        payload = {
            'action': 'ack',
            'text': 'ack the alert'
        }
        response = self.client.put('/alert/' + alert_id + '/action', json=payload, headers=self.headers)
        self.assertEqual(response.status_code, 200)

        response = self.client.get('/alert/' + alert_id, headers=self.headers)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data.decode('utf-8'))
        self.assertEqual(data['alert']['attributes']['acked-by'], 'admin@alerta.io')

        # clear alert
        response = self.client.post('/alert', json=self.ok_alert, headers=self.headers)
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data.decode('utf-8'))
        self.assertEqual(data['alert']['severity'], 'ok')
        self.assertEqual(data['alert']['status'], 'closed')
        self.assertEqual(data['alert']['attributes']['acked-by'], 'admin@alerta.io')

        # critical alert (unacked)
        response = self.client.post('/alert', json=self.critical_alert, headers=self.headers)
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data.decode('utf-8'))
        self.assertEqual(data['alert']['severity'], 'critical')
        self.assertEqual(data['alert']['status'], 'open')
        self.assertNotIn('acked-by', data['alert']['attributes'])

        # ack alert (again)
        payload = {
            'action': 'ack',
            'text': 'ack the alert, again'
        }
        response = self.client.put('/alert/' + alert_id + '/action', json=payload, headers=self.headers)
        self.assertEqual(response.status_code, 200)

        response = self.client.get('/alert/' + alert_id, headers=self.headers)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data.decode('utf-8'))
        self.assertEqual(data['alert']['attributes']['acked-by'], 'admin@alerta.io')

        # unack alert
        payload = {
            'action': 'unack',
            'text': 'unack the alert'
        }
        response = self.client.put('/alert/' + alert_id + '/action', json=payload, headers=self.headers)
        self.assertEqual(response.status_code, 200)

        response = self.client.get('/alert/' + alert_id, headers=self.headers)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data.decode('utf-8'))
        self.assertNotIn('acked-by', data['alert']['attributes'])

    # XXX - forwarder plugin tested extensively in test_forwarder.py
