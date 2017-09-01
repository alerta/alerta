
import unittest

try:
    import simplejson as json
except ImportError:
    import json

from alerta.app import create_app, db
from alerta.app.models.key import ApiKey


class BlackoutsTestCase(unittest.TestCase):

    def setUp(self):

        test_config = {
            'TESTING': True,
            'AUTH_REQUIRED': True,
            'CUSTOMER_VIEWS': True
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

        with self.app.app_context():
            self.admin_api_key = db.create_key(
                ApiKey(
                    user='admin',
                    scopes=['admin', 'read', 'write'],
                    text='demo-key'
                )
            )['_id']
            self.customer_api_key = db.create_key(
                ApiKey(
                    user='admin',
                    scopes=['admin', 'read', 'write'],
                    text='demo-key',
                    customer='Foo'
                )
            )['_id']

    def tearDown(self):

        with self.app.app_context():
            db.destroy()

    def test_suppress_alerts(self):

        self.headers = {
            'Authorization': 'Key %s' % self.admin_api_key,
            'Content-type': 'application/json'
        }

        # create alert
        response = self.client.post('/alert', data=json.dumps(self.alert), headers=self.headers)
        self.assertEqual(response.status_code, 201)

        # create blackout
        response = self.client.post('/blackout', data=json.dumps({"environment": "Production"}), headers=self.headers)
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data.decode('utf-8'))

        blackout_id = data['id']

        # suppress alert
        response = self.client.post('/alert', data=json.dumps(self.alert), headers=self.headers)
        self.assertEqual(response.status_code, 202)

        self.headers = {
            'Authorization': 'Key %s' % self.customer_api_key,
            'Content-type': 'application/json'
        }

        # create alert
        response = self.client.post('/alert', data=json.dumps(self.alert), headers=self.headers)
        self.assertEqual(response.status_code, 202)


        self.headers = {
            'Authorization': 'Key %s' % self.admin_api_key,
            'Content-type': 'application/json'
        }

        response = self.client.delete('/blackout/' + blackout_id, headers=self.headers)
        self.assertEqual(response.status_code, 200)
