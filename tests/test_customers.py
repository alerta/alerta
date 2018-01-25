
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
            'ALLOWED_EMAIL_DOMAINS': ['alerta.io', 'example.com']
        }
        self.app = create_app(test_config)
        self.client = self.app.test_client()

        self.alert = {
            'event': 'Foo',
            'resource': 'Bar',
            'environment': 'Production',
            'service': ['Quux']
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

        # add customer mapping
        payload = {
            'customer': 'Example Corp',
            'match': 'example.com'
        }
        response = self.client.post('/customer', data=json.dumps(payload), content_type='application/json', headers=self.headers)
        self.assertEqual(response.status_code, 201)

        # create user
        payload = {
            'name': 'Example User',
            'email': 'user@example.com',
            'password': '3x8mpl3',
            'text': ''
        }

        response = self.client.post('/auth/signup', data=json.dumps(payload), content_type='application/json', headers=self.headers)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data.decode('utf-8'))
        self.assertIsNotNone(data, 'Failed to create user')

        # use JWT token for user auth
        token = data['token']
        user_headers = {
            'Authorization': 'Bearer %s' % token,
            'Content-type': 'application/json'
        }

        # create user blackout
        response = self.client.post('/blackout', data=json.dumps({"environment": "Production"}), headers=user_headers)
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data.decode('utf-8'))

        blackout_id = data['id']

        # delete user blackout by admin
        response = self.client.delete('/blackout/' + blackout_id, headers=self.headers)
        self.assertEqual(response.status_code, 200)


