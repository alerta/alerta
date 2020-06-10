import json
import time
import unittest
from uuid import uuid4

from alerta.app import create_app, db


class ManagementTestCase(unittest.TestCase):

    def setUp(self):

        test_config = {
            'DEBUG': True,
            'TESTING': True,
            'AUTH_REQUIRED': False
        }
        self.app = create_app(test_config)
        self.client = self.app.test_client()

        self.headers = {
            'Content-type': 'application/json'
        }

        def random_resource():
            return str(uuid4()).upper()[:8]

        self.expired_alert = {
            'event': 'node_down',
            'resource': random_resource(),
            'environment': 'Production',
            'service': ['Network'],
            'severity': 'major',
            'correlate': ['node_down', 'node_marginal', 'node_up'],
            'tags': ['foo'],
            'attributes': {'foo': 'abc def', 'bar': 1234, 'baz': False},
            'timeout': 2
        }

        self.shelved_alert = {
            'event': 'node_marginal',
            'resource': random_resource(),
            'environment': 'Production',
            'service': ['Network'],
            'severity': 'warning',
            'correlate': ['node_down', 'node_marginal', 'node_up'],
            'timeout': 20
        }

        self.acked_alert = {
            'event': 'node_down',
            'resource': random_resource(),
            'environment': 'Production',
            'service': ['Network', 'Shared'],
            'severity': 'critical',
            'correlate': ['node_down', 'node_marginal', 'node_up'],
            'tags': ['foo']
        }

        self.ok_alert = {
            'event': 'node_up',
            'resource': random_resource(),
            'environment': 'Production',
            'service': ['Network'],
            'severity': 'ok',
            'correlate': ['node_down', 'node_marginal', 'node_up']
        }

    def tearDown(self):
        db.destroy()

    def test_status(self):

        # create alert
        response = self.client.post('/alert', data=json.dumps(self.expired_alert), headers=self.headers)
        self.assertEqual(response.status_code, 201)

        response = self.client.get('/management/status', headers=self.headers)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data.decode('utf-8'))
        for metric in data['metrics']:
            if metric['name'] == 'total':
                self.assertGreaterEqual(metric['value'], 1)

    def test_housekeeping(self):

        # create an alert with short timeout that will expire
        response = self.client.post('/alert', data=json.dumps(self.expired_alert), headers=self.headers)
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data.decode('utf-8'))

        expired_id = data['id']

        response = self.client.get('/alert/' + expired_id)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data.decode('utf-8'))
        self.assertEqual(data['alert']['id'], expired_id)
        self.assertEqual(data['alert']['timeout'], 2)

        # create an alert and shelve it
        response = self.client.post('/alert', data=json.dumps(self.shelved_alert), headers=self.headers)
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data.decode('utf-8'))

        shelved_id = data['id']

        response = self.client.put('/alert/' + shelved_id + '/action',
                                   data=json.dumps({'action': 'shelve', 'timeout': 2}), headers=self.headers)
        self.assertEqual(response.status_code, 200)

        response = self.client.get('/alert/' + shelved_id)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data.decode('utf-8'))
        self.assertEqual(data['alert']['id'], shelved_id)
        self.assertEqual(data['alert']['timeout'], 2)

        # create an alert and ack it
        response = self.client.post('/alert', data=json.dumps(self.acked_alert), headers=self.headers)
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data.decode('utf-8'))

        acked_id = data['id']

        response = self.client.put('/alert/' + acked_id + '/action',
                                   data=json.dumps({'action': 'ack', 'timeout': 2}), headers=self.headers)
        self.assertEqual(response.status_code, 200)

        response = self.client.get('/alert/' + acked_id)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data.decode('utf-8'))
        self.assertEqual(data['alert']['id'], acked_id)
        self.assertEqual(data['alert']['timeout'], 2)

        # create an alert that should be unaffected
        response = self.client.post('/alert', data=json.dumps(self.ok_alert), headers=self.headers)
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data.decode('utf-8'))

        time.sleep(5)

        response = self.client.get('/management/housekeeping', headers=self.headers)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data.decode('utf-8'))
        self.assertEqual(data['count'], 3)
        self.assertListEqual(data['expired'], [expired_id])
        self.assertListEqual(data['timedout'], [shelved_id, acked_id])
