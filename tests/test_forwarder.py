import json
import unittest
from uuid import uuid4

import requests_mock

from alerta.app import create_app, db, plugins
from alerta.models.enums import Scope
from alerta.models.key import ApiKey
from alerta.utils.response import base_url


class ForwarderTestCase(unittest.TestCase):

    def setUp(self):

        test_config = {
            'DEBUG': False,
            'TESTING': True,
            'AUTH_REQUIRED': True,
            'BASE_URL': 'http://localhost:8080',
            'PLUGINS': ['forwarder']
        }

        HMAC_AUTH_CREDENTIALS = [
            {  # http://localhost:9001
                'key': 'e3b8afc0-db18-4c51-865d-b95322742c5e',
                'secret': 'MDhjZGMyYTRkY2YyNjk1MTEyMWFlNmM3Y2UxZDU1ZjIK',
                'algorithm': 'sha256'
            },
        ]

        FWD_DESTINATIONS = [
            ('http://localhost:9000', {'username': 'user', 'password': 'pa55w0rd', 'timeout': 10}, ['alerts', 'actions']),  # BasicAuth
            # ('https://httpbin.org/anything', dict(username='foo', password='bar', ssl_verify=False), ['*']),
            ('http://localhost:9001', {
                'key': 'e3b8afc0-db18-4c51-865d-b95322742c5e',
                'secret': 'MDhjZGMyYTRkY2YyNjk1MTEyMWFlNmM3Y2UxZDU1ZjIK'
            }, ['actions']),  # Hawk HMAC
            ('http://localhost:9002', {'key': 'demo-key'}, ['delete']),  # API key
            ('http://localhost:9003', {'token': 'bearer-token'}, ['*']),  # Bearer token
        ]

        test_config['HMAC_AUTH_CREDENTIALS'] = HMAC_AUTH_CREDENTIALS
        test_config['FWD_DESTINATIONS'] = FWD_DESTINATIONS

        self.app = create_app(test_config)
        self.client = self.app.test_client()

        self.resource = str(uuid4()).upper()[:8]

        self.major_alert = {
            'id': 'b528c6f7-0925-4f6d-b930-fa6c0bba51dc',
            'event': 'node_marginal',
            'resource': self.resource,
            'environment': 'Production',
            'service': ['Network'],
            'severity': 'major',
            'correlate': ['node_down', 'node_marginal', 'node_up'],
            'timeout': 40
        }
        self.repeated_major_alert = {
            'id': '4ba2b0d6-ff4a-4fc0-8d93-45939c819465',
            'event': 'node_marginal',
            'resource': self.resource,
            'environment': 'Production',
            'service': ['Network'],
            'severity': 'major',
            'correlate': ['node_down', 'node_marginal', 'node_up'],
            'timeout': 40
        }
        self.warn_alert = {
            'id': '67344228-bd03-4660-9c45-ff9c8f1d53d0',
            'event': 'node_marginal',
            'resource': self.resource,
            'environment': 'Production',
            'service': ['Network'],
            'severity': 'warning',
            'correlate': ['node_down', 'node_marginal', 'node_up'],
            'timeout': 50
        }
        self.normal_alert = {
            'id': 'cb12250d-42ed-42cc-97ef-592f3a49618c',
            'event': 'node_up',
            'resource': self.resource,
            'environment': 'Production',
            'service': ['Network'],
            'severity': 'normal',
            'correlate': ['node_down', 'node_marginal', 'node_up'],
            'timeout': 100
        }

        with self.app.test_request_context('/'):
            self.app.preprocess_request()
            self.api_key = ApiKey(
                user='admin@alerta.io',
                scopes=[Scope.admin, Scope.read, Scope.write],
                text='demo-key'
            )
            self.api_key.create()

    def tearDown(self):
        plugins.plugins.clear()
        db.destroy()

    @requests_mock.mock()
    def test_forward_alert(self, m):

        ok_response = """
        {"status": "ok"}
        """
        m.post('http://localhost:9000/alert', text=ok_response)
        m.post('http://localhost:9001/alert', text=ok_response)
        m.post('http://localhost:9002/alert', text=ok_response)
        m.post('http://localhost:9003/alert', text=ok_response)

        headers = {
            'Authorization': f'Key {self.api_key.key}',
            'Content-type': 'application/json',
            'Origin': 'http://localhost:5000',
            'X-Alerta-Loop': 'http://localhost:5000',
        }
        response = self.client.post('/alert', data=json.dumps(self.major_alert), headers=headers)
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data.decode('utf-8'))
        self.assertEqual(data['status'], 'ok')

        history = m.request_history
        self.assertEqual(history[0].port, 9000)
        self.assertEqual(history[1].port, 9003)

    @requests_mock.mock()
    def test_forward_action(self, m):

        ok_response = """
        {"status": "ok"}
        """
        m.post('http://localhost:9000/alert', text=ok_response)
        m.post('http://localhost:9003/alert', text=ok_response)

        # create alert
        headers = {
            'Authorization': f'Key {self.api_key.key}',
            'Content-type': 'application/json'
        }
        response = self.client.post('/alert', data=json.dumps(self.warn_alert), headers=headers)
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data.decode('utf-8'))
        self.assertEqual(data['alert']['status'], 'open')

        alert_id = data['id']

        m.put(f'http://localhost:9000/alert/{alert_id}/action', text=ok_response)
        m.put(f'http://localhost:9001/alert/{alert_id}/action', text=ok_response)
        m.put(f'http://localhost:9002/alert/{alert_id}/action', text=ok_response)
        m.put(f'http://localhost:9003/alert/{alert_id}/action', text=ok_response)

        headers = {
            'Authorization': f'Key {self.api_key.key}',
            'Content-type': 'application/json',
            'Origin': 'http://localhost:8000'
        }
        response = self.client.put(f'/alert/{alert_id}/action', data=json.dumps({'action': 'ack'}), headers=headers)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data.decode('utf-8'))
        self.assertEqual(data['status'], 'ok')

        history = m.request_history
        self.assertEqual(history[0].port, 9000)
        self.assertEqual(history[1].port, 9003)
        self.assertEqual(history[2].port, 9000)
        self.assertEqual(history[3].port, 9001)
        self.assertEqual(history[4].port, 9003)

    @requests_mock.mock()
    def test_forward_delete(self, m):

        ok_response = """
        {"status": "ok"}
        """
        m.post('http://localhost:9000/alert', text=ok_response)
        m.post('http://localhost:9003/alert', text=ok_response)

        # create alert
        headers = {
            'Authorization': f'Key {self.api_key.key}',
            'Content-type': 'application/json'
        }
        response = self.client.post('/alert', data=json.dumps(self.warn_alert), headers=headers)
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data.decode('utf-8'))
        self.assertEqual(data['alert']['status'], 'open')

        alert_id = data['id']

        m.delete(f'http://localhost:9002/alert/{alert_id}', text=ok_response)
        m.delete(f'http://localhost:9003/alert/{alert_id}', text=ok_response)

        headers = {
            'Authorization': f'Key {self.api_key.key}',
            'Content-type': 'application/json',
            'Origin': 'http://localhost:8000'
        }
        response = self.client.delete(f'/alert/{alert_id}', headers=headers)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data.decode('utf-8'))
        self.assertEqual(data['status'], 'ok')

        history = m.request_history
        self.assertEqual(history[0].port, 9000)
        self.assertEqual(history[1].port, 9003)
        self.assertEqual(history[2].port, 9002)
        self.assertEqual(history[3].port, 9003)

    @requests_mock.mock()
    def test_forward_heartbeat(self, m):
        # FIXME: currently not possible
        pass

    @requests_mock.mock()
    def test_already_processed(self, m):
        # Alert is not processed locally or forwarded when an Alerta server
        # receives an alert which it has already processed. This is
        # determined by checking to see if the BASE_URL of the server
        # is already in the X-Alerta-Loop header. A 202 is returned because
        # the alert was accepted, even though it wasn't processed.

        ok_response = """
        {"status": "ok"}
        """
        m.post('http://localhost:9000/alert', text=ok_response)
        m.post('http://localhost:9001/alert', text=ok_response)
        m.post('http://localhost:9002/alert', text=ok_response)
        m.post('http://localhost:9003/alert', text=ok_response)

        headers = {
            'Authorization': f'Key {self.api_key.key}',
            'Content-type': 'application/json',
            'Origin': 'http://localhost:5000',
            'X-Alerta-Loop': 'http://localhost:8080,http://localhost:5000',
        }
        response = self.client.post('/alert', data=json.dumps(self.major_alert), headers=headers)
        self.assertEqual(response.status_code, 202)
        data = json.loads(response.data.decode('utf-8'))
        self.assertEqual(data['status'], 'ok')
        self.assertEqual(data['message'], 'Alert forwarded by http://localhost:5000 already processed by http://localhost:8080')

        self.assertEqual(m.called, False)

    @requests_mock.mock()
    def test_forward_loop(self, m):
        # Alert is processed locally but not forwarded on to the remote
        # because it is already in the X-Alerta-Loop header. A 201 is
        # returned because the alert has been received and processed.

        ok_response = """
        {"status": "ok"}
        """
        m.post('http://localhost:9000/alert', text=ok_response)
        m.post('http://localhost:9001/alert', text=ok_response)
        m.post('http://localhost:9002/alert', text=ok_response)
        m.post('http://localhost:9003/alert', text=ok_response)

        headers = {
            'Authorization': f'Key {self.api_key.key}',
            'Content-type': 'application/json',
            'X-Alerta-Loop': 'http://localhost:9000,http://localhost:9001,http://localhost:9002,http://localhost:9003',
        }
        response = self.client.post('/alert', data=json.dumps(self.warn_alert), headers=headers)
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data.decode('utf-8'))
        self.assertEqual(data['status'], 'ok')

        self.assertEqual(m.called, False)

    def test_do_not_forward(self):
        # check forwarding rule for remote
        pass

    def test_base_url(self):

        with self.app.test_request_context('/'):
            self.assertEqual(base_url(), 'http://localhost:8080')
