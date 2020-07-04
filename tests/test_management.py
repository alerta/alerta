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
            'AUTH_REQUIRED': False,
            # 'ACK_TIMEOUT': 2,
            # 'SHELVE_TIMEOUT': 3
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

        self.acked_and_shelved_alert = {
            'event': 'node_warn',
            'resource': random_resource(),
            'environment': 'Production',
            'service': ['Network', 'Shared'],
            'severity': 'warning',
            'correlate': ['node_down', 'node_marginal', 'node_up'],
            'tags': ['foo'],
            'timeout': 240
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
                                   data=json.dumps({'action': 'shelve', 'timeout': 3}), headers=self.headers)
        self.assertEqual(response.status_code, 200)

        response = self.client.get('/alert/' + shelved_id)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data.decode('utf-8'))
        self.assertEqual(data['alert']['id'], shelved_id)
        self.assertEqual(data['alert']['timeout'], 20)
        self.assertEqual(data['alert']['history'][0]['timeout'], 20)
        self.assertEqual(data['alert']['history'][1]['timeout'], 3)

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
        self.assertEqual(data['alert']['timeout'], 86400)
        self.assertEqual(data['alert']['history'][0]['status'], 'open')
        self.assertEqual(data['alert']['history'][0]['timeout'], 86400)
        self.assertEqual(data['alert']['history'][1]['status'], 'ack')
        self.assertEqual(data['alert']['history'][1]['timeout'], 2)

        # create an alert that should be unaffected
        response = self.client.post('/alert', data=json.dumps(self.ok_alert), headers=self.headers)
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data.decode('utf-8'))

        # create an alert and ack it then shelve it
        response = self.client.post('/alert', data=json.dumps(self.acked_and_shelved_alert), headers=self.headers)
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data.decode('utf-8'))

        acked_and_shelved_id = data['id']

        response = self.client.put('/alert/' + acked_and_shelved_id + '/action',
                                   data=json.dumps({'action': 'ack', 'timeout': 4}), headers=self.headers)
        self.assertEqual(response.status_code, 200)

        response = self.client.put('/alert/' + acked_and_shelved_id + '/action',
                                   data=json.dumps({'action': 'shelve', 'timeout': 3}), headers=self.headers)
        self.assertEqual(response.status_code, 200)

        response = self.client.get('/alert/' + acked_and_shelved_id)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data.decode('utf-8'))
        self.assertEqual(data['alert']['id'], acked_and_shelved_id)
        self.assertEqual(data['alert']['timeout'], 240)
        self.assertEqual(data['alert']['history'][0]['status'], 'open')
        self.assertEqual(data['alert']['history'][0]['timeout'], 240)
        self.assertEqual(data['alert']['history'][1]['status'], 'ack')
        self.assertEqual(data['alert']['history'][1]['timeout'], 4)
        self.assertEqual(data['alert']['history'][2]['status'], 'shelved')
        self.assertEqual(data['alert']['history'][2]['timeout'], 3)

        time.sleep(5)

        response = self.client.get('/management/housekeeping', headers=self.headers)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data.decode('utf-8'))
        self.assertEqual(data['count'], 4)
        self.assertListEqual(data['expired'], [expired_id])
        self.assertListEqual(sorted(data['unshelve']), sorted([shelved_id, acked_and_shelved_id]))
        self.assertListEqual(sorted(data['unack']), sorted([acked_id]))

        response = self.client.get('/alert/' + shelved_id)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data.decode('utf-8'))
        self.assertEqual(data['alert']['id'], shelved_id)
        self.assertEqual(data['alert']['status'], 'open')
        self.assertEqual(data['alert']['timeout'], 20)
        self.assertEqual(data['alert']['history'][0]['status'], 'open')   # previous status
        self.assertEqual(data['alert']['history'][0]['timeout'], 20)  # previous timeout
        self.assertEqual(data['alert']['history'][1]['status'], 'shelved')  # status
        self.assertEqual(data['alert']['history'][1]['timeout'], 3)
        self.assertEqual(data['alert']['history'][2]['status'], 'open')
        self.assertEqual(data['alert']['history'][2]['timeout'], 20, data['alert'])

        response = self.client.get('/alert/' + acked_id)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data.decode('utf-8'))
        self.assertEqual(data['alert']['id'], acked_id)
        self.assertEqual(data['alert']['status'], 'open')
        self.assertEqual(data['alert']['timeout'], 86400)
        self.assertEqual(data['alert']['history'][0]['status'], 'open')
        self.assertEqual(data['alert']['history'][0]['timeout'], 86400)
        self.assertEqual(data['alert']['history'][1]['status'], 'ack')
        self.assertEqual(data['alert']['history'][1]['timeout'], 2)
        self.assertEqual(data['alert']['history'][2]['status'], 'open')
        self.assertEqual(data['alert']['history'][2]['timeout'], 86400)

        response = self.client.get('/alert/' + acked_and_shelved_id)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data.decode('utf-8'))
        self.assertEqual(data['alert']['id'], acked_and_shelved_id)
        self.assertEqual(data['alert']['status'], 'ack')
        self.assertEqual(data['alert']['timeout'], 240)
        self.assertEqual(data['alert']['history'][0]['status'], 'open')
        self.assertEqual(data['alert']['history'][0]['timeout'], 240)
        self.assertEqual(data['alert']['history'][1]['status'], 'ack')
        self.assertEqual(data['alert']['history'][1]['timeout'], 4)
        self.assertEqual(data['alert']['history'][2]['status'], 'shelved')
        self.assertEqual(data['alert']['history'][2]['timeout'], 3)
        self.assertEqual(data['alert']['history'][3]['status'], 'ack')
        self.assertEqual(data['alert']['history'][3]['timeout'], 4)
