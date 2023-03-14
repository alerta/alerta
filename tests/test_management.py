import json
import time
import unittest
from uuid import uuid4

from alerta.app import create_app, db
from tests.helpers.utils import mod_env


class ManagementTestCase(unittest.TestCase):

    def setUp(self):

        self.maxDiff = None

        test_config = {
            'DEBUG': False,
            'TESTING': True,
            'AUTH_REQUIRED': False,
            # 'ACK_TIMEOUT': 2,
            # 'SHELVE_TIMEOUT': 3,
            'SERVER_VERSION': 'off',
            # 'SERVER_VERSION': 'major'
        }

        with mod_env(
            DELETE_EXPIRED_AFTER='2',
            DELETE_INFO_AFTER='3'
        ):
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

        self.info_alert = {
            'event': 'node_init',
            'resource': random_resource(),
            'environment': 'Production',
            'service': ['Network'],
            'severity': 'informational',
            'correlate': ['node_down', 'node_marginal', 'node_up'],
            'timeout': 3
        }

    def tearDown(self):
        db.destroy()

    def test_manifest(self):

        response = self.client.get('/management/manifest')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data.decode('utf-8'))
        self.assertEqual(data['release'], None)

    def test_properties(self):

        response = self.client.get('/management/properties')
        self.assertEqual(response.status_code, 200)

    def test_good_to_go(self):

        response = self.client.get('/management/gtg')
        self.assertEqual(response.status_code, 200)

    def test_health_check(self):

        response = self.client.get('/management/healthcheck')
        self.assertEqual(response.status_code, 200)

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

        # create an info alert that should be deleted
        response = self.client.post('/alert', data=json.dumps(self.info_alert), headers=self.headers)
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data.decode('utf-8'))

        info_id = data['id']

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

        # run housekeeping (1st time)
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

        response = self.client.get('/alert/' + info_id)
        self.assertEqual(response.status_code, 404)

        time.sleep(5)

        # run housekeeping (2nd time)
        response = self.client.get('/management/housekeeping', headers=self.headers)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data.decode('utf-8'))
        self.assertEqual(data['count'], 1)
        self.assertListEqual(data['expired'], [])
        self.assertListEqual(data['unshelve'], [])
        self.assertListEqual(data['unack'], [acked_and_shelved_id])

        response = self.client.get('/alert/' + expired_id)
        self.assertEqual(response.status_code, 404)

        # run housekeeping (3rd time)
        response = self.client.get('/management/housekeeping', headers=self.headers)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data.decode('utf-8'))
        self.assertEqual(data['count'], 0)
        self.assertListEqual(data['expired'], [])
        self.assertListEqual(data['unshelve'], [])
        self.assertListEqual(data['unack'], [])

    def test_status(self):

        # create alert
        response = self.client.post('/alert', data=json.dumps(self.expired_alert), headers=self.headers)
        self.assertEqual(response.status_code, 201)

        response = self.client.get('/management/status', headers=self.headers)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data.decode('utf-8'))
        self.assertEqual(data['version'], None)
        for metric in data['metrics']:
            if metric['name'] == 'total':
                self.assertGreaterEqual(metric['value'], 1)

    def test_prometheus(self):

        response = self.client.get('/management/metrics')
        self.assertEqual(response.status_code, 200)
