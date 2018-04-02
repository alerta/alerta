
import json
import unittest

from alerta.app import create_app, db
from alerta.models.key import ApiKey
from alerta.models.token import Jwt


class AuthTestCase(unittest.TestCase):

    def setUp(self):

        test_config = {
            'TESTING': True,
            'AUTH_REQUIRED': True,
            'CUSTOMER_VIEWS': True,
            'ADMIN_USERS': ['admin@alerta.io'],
            'ALLOWED_EMAIL_DOMAINS': ['alerta.io', 'foo.com', 'bar.com']
        }
        self.app = create_app(test_config)
        self.client = self.app.test_client()

        self.foo_alert = {
            'event': 'foo1',
            'resource': 'foo1',
            'environment': 'Production',
            'service': ['Web']
        }

        self.bar_alert = {
            'event': 'bar1',
            'resource': 'bar1',
            'environment': 'Production',
            'service': ['Web']
        }

        with self.app.test_request_context('/'):
            self.app.preprocess_request()
            self.api_key = ApiKey(
                user='admin@alerta.io',
                scopes=['admin', 'read', 'write'],
                text='admin-key'
            )
            self.api_key.create()

        self.headers = {
            'Authorization': 'Key %s' % self.api_key.key,
            'Content-type': 'application/json'
        }

    def tearDown(self):
        db.destroy()

    def test_blackouts(self):

        # add customer mappings
        payload = {
            'customer': 'Foo Corp',
            'match': 'foo.com'
        }
        response = self.client.post('/customer', data=json.dumps(payload), content_type='application/json', headers=self.headers)
        self.assertEqual(response.status_code, 201)

        payload = {
            'customer': 'Bar Corp',
            'match': 'bar.com'
        }
        response = self.client.post('/customer', data=json.dumps(payload), content_type='application/json', headers=self.headers)
        self.assertEqual(response.status_code, 201)

        # create users
        payload = {
            'name': 'Foo User',
            'email': 'user@foo.com',
            'password': 'f00f00',
            'text': ''
        }

        response = self.client.post('/auth/signup', data=json.dumps(payload), content_type='application/json', headers=self.headers)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data.decode('utf-8'))
        self.assertIsNotNone(data, 'Failed to create user')

        foo_user_headers = {
            'Authorization': 'Bearer %s' % data['token'],
            'Content-type': 'application/json'
        }

        payload = {
            'name': 'Bar User',
            'email': 'user@bar.com',
            'password': 'b8rb8r',
            'text': ''
        }

        response = self.client.post('/auth/signup', data=json.dumps(payload), content_type='application/json', headers=self.headers)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data.decode('utf-8'))
        self.assertIsNotNone(data, 'Failed to create user')

        bar_user_headers = {
            'Authorization': 'Bearer %s' % data['token'],
            'Content-type': 'application/json'
        }

        # create customer blackout by foo user
        response = self.client.post('/blackout', data=json.dumps({"environment": "Production"}), headers=foo_user_headers)
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data.decode('utf-8'))

        blackout_id = data['id']

        # new alert by foo user should be suppressed
        response = self.client.post('/alert', data=json.dumps(self.foo_alert), headers=foo_user_headers)
        self.assertEqual(response.status_code, 202)

        # new alert by bar user should not be suppressed
        response = self.client.post('/alert', data=json.dumps(self.bar_alert), headers=bar_user_headers)
        self.assertEqual(response.status_code, 201)

        # delete blackout by id
        response = self.client.delete('/blackout/' + blackout_id, headers=self.headers)
        self.assertEqual(response.status_code, 200)

        # create global blackout by admin user
        response = self.client.post('/blackout', data=json.dumps({"environment": "Production"}), headers=self.headers)
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data.decode('utf-8'))

        blackout_id = data['id']

        # new alert by foo user should be suppressed
        response = self.client.post('/alert', data=json.dumps(self.foo_alert), headers=foo_user_headers)
        self.assertEqual(response.status_code, 202)

        # new alert by bar user should be suppressed
        response = self.client.post('/alert', data=json.dumps(self.bar_alert), headers=bar_user_headers)
        self.assertEqual(response.status_code, 202)

        # delete blackout by id
        response = self.client.delete('/blackout/' + blackout_id, headers=self.headers)
        self.assertEqual(response.status_code, 200)
