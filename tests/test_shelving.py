import json
import unittest

from alerta.app import create_app, db
from alerta.models.key import ApiKey


class ShelvingTestCase(unittest.TestCase):

    def setUp(self):
        test_config = {
            'TESTING': True,
            'AUTH_REQUIRED': True,
            'CUSTOMER_VIEWS': True,
            'PLUGINS': ['reject']
        }
        self.app = create_app(test_config)
        self.client = self.app.test_client()

        self.alert = {
            'event': 'node_marginal',
            'resource': 'node404',
            'environment': 'Production',
            'service': ['Network'],
            'severity': 'warning',
            'correlate': ['node_down', 'node_marginal', 'node_up']
        }

        with self.app.test_request_context('/'):
            self.app.preprocess_request()
            self.admin_api_key = ApiKey(
                user='admin',
                scopes=['admin', 'read', 'write'],
                text='demo-key'
            )
            self.customer_api_key = ApiKey(
                user='admin',
                scopes=['admin', 'read', 'write'],
                text='demo-key',
                customer='Foo'
            )
            self.admin_api_key.create()
            self.customer_api_key.create()

    def tearDown(self):
        db.destroy()

    def test_alarm_shelving(self):

        self.headers = {
            'Authorization': 'Key %s' % self.admin_api_key.key,
            'Content-type': 'application/json'
        }

        # new alert should be status=open
        response = self.client.post('/alert', data=json.dumps(self.alert), headers=self.headers)
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data.decode('utf-8'))
        self.assertEqual(data['alert']['status'], 'open')

        alert_id = data['id']

        # shelve alert
        response = self.client.put('/alert/' + alert_id + '/status',
                                   data=json.dumps({'status': 'shelved'}), headers=self.headers)
        self.assertEqual(response.status_code, 200)
        response = self.client.get('/alert/' + alert_id, headers=self.headers)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data.decode('utf-8'))
        self.assertEqual(data['alert']['status'], 'shelved')

        # duplicate alert should be status=shelved
        response = self.client.post('/alert', data=json.dumps(self.alert), headers=self.headers)
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data.decode('utf-8'))
        self.assertEqual(data['alert']['status'], 'shelved')

        # duplicate alert should be status=shelved (again)
        response = self.client.post('/alert', data=json.dumps(self.alert), headers=self.headers)
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data.decode('utf-8'))
        self.assertEqual(data['alert']['status'], 'shelved')

        # increase severity alert should stay status=shelved
        self.alert['severity'] = 'major'
        response = self.client.post('/alert', data=json.dumps(self.alert), headers=self.headers)
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data.decode('utf-8'))
        self.assertEqual(data['alert']['status'], 'shelved')

        # shelve alert
        response = self.client.put('/alert/' + alert_id + '/status',
                                   data=json.dumps({'status': 'shelved'}), headers=self.headers)
        self.assertEqual(response.status_code, 200)
        response = self.client.get('/alert/' + alert_id, headers=self.headers)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data.decode('utf-8'))
        self.assertEqual(data['alert']['status'], 'shelved')

        # decrease severity alert should be status=shelved
        self.alert['severity'] = 'minor'
        response = self.client.post('/alert', data=json.dumps(self.alert), headers=self.headers)
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data.decode('utf-8'))
        self.assertEqual(data['alert']['status'], 'shelved')

        # decrease severity alert should be status=shelved (again)
        self.alert['severity'] = 'warning'
        response = self.client.post('/alert', data=json.dumps(self.alert), headers=self.headers)
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data.decode('utf-8'))
        self.assertEqual(data['alert']['status'], 'shelved')

        # normal severity alert should be status=closed
        self.alert['severity'] = 'ok'
        response = self.client.post('/alert', data=json.dumps(self.alert), headers=self.headers)
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data.decode('utf-8'))
        self.assertEqual(data['alert']['status'], 'closed')

        # normal severity alert should be status=closed (again)
        response = self.client.post('/alert', data=json.dumps(self.alert), headers=self.headers)
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data.decode('utf-8'))
        self.assertEqual(data['alert']['status'], 'closed')

        # normal severity alert should be status=closed
        response = self.client.post('/alert', data=json.dumps(self.alert), headers=self.headers)
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data.decode('utf-8'))
        self.assertEqual(data['alert']['status'], 'closed')

        ###

        # increase severity alert should be status=shelved
        self.alert['severity'] = 'critical'
        response = self.client.post('/alert', data=json.dumps(self.alert), headers=self.headers)
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data.decode('utf-8'))
        self.assertEqual(data['alert']['status'], 'shelved')

        # shelve alert
        response = self.client.put('/alert/' + alert_id + '/status',
                                   data=json.dumps({'status': 'shelved'}), headers=self.headers)
        self.assertEqual(response.status_code, 200)
        response = self.client.get('/alert/' + alert_id, headers=self.headers)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data.decode('utf-8'))
        self.assertEqual(data['alert']['status'], 'shelved')

        # duplicate alert should be status=shelved
        response = self.client.post('/alert', data=json.dumps(self.alert), headers=self.headers)
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data.decode('utf-8'))
        self.assertEqual(data['alert']['status'], 'shelved')

        # unshelve alert
        response = self.client.put('/alert/' + alert_id + '/status',
                                   data=json.dumps({'status': 'open'}), headers=self.headers)
        self.assertEqual(response.status_code, 200)
        response = self.client.get('/alert/' + alert_id, headers=self.headers)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data.decode('utf-8'))
        self.assertEqual(data['alert']['status'], 'open')

        # duplicate alert should be status=open
        response = self.client.post('/alert', data=json.dumps(self.alert), headers=self.headers)
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data.decode('utf-8'))
        self.assertEqual(data['alert']['status'], 'open')
