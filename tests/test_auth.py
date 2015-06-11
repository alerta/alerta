import json
import unittest

from alerta.app import app, db


class AuthTestCase(unittest.TestCase):

    def setUp(self):

        app.config['TESTING'] = True
        app.config['AUTH_REQUIRED'] = True
        self.app = app.test_client()

        self.alert = {
            'event': 'Foo',
            'resource': 'Bar',
            'environment': 'Production',
            'service': ['Quux']
        }

        self.api_key = db.create_key('demo-key', type='read-write', text='demo-key')

        self.headers = {
            'Authorization': 'Key %s' % self.api_key,
            'Content-type': 'application/json'
        }

    def tearDown(self):

        pass

    def test_401_error(self):

        response = self.app.get('/alerts')
        self.assertEqual(response.status_code, 401)

    def test_readwrite_key(self):

        payload = {
            'user': 'rw-demo-key',
            'type': 'read-write'
        }

        response = self.app.post('/key', data=json.dumps(payload), headers=self.headers)
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data)
        self.assertIsNotNone(data['key'], 'Failed to create read-write key')

        rw_api_key = data['key']

        response = self.app.post('/alert', data=json.dumps(self.alert), headers={'Authorization': 'Key ' + rw_api_key})
        self.assertEqual(response.status_code, 201)

        response = self.app.get('/alerts', headers={'Authorization': 'Key ' + rw_api_key})
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertGreater(data['total'], 1, "total alerts > 1")

        response = self.app.delete('/key/' + rw_api_key, headers=self.headers)
        self.assertEqual(response.status_code, 200)

    def test_readonly_key(self):

        payload = {
            'user': 'ro-demo-key',
            'type': 'read-only'
        }

        response = self.app.post('/key', data=json.dumps(payload), headers=self.headers)
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data)
        self.assertIsNotNone(data['key'], 'Failed to create read-only key')

        ro_api_key = data['key']

        response = self.app.post('/alert', data=json.dumps(self.alert), headers={'Authorization': 'Key ' + ro_api_key})
        self.assertEqual(response.status_code, 403)

        response = self.app.get('/alerts', headers={'Authorization': 'Key ' + ro_api_key})
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertGreater(data['total'], 1, "total alerts > 1")

        response = self.app.delete('/key/' + ro_api_key, headers=self.headers)
        self.assertEqual(response.status_code, 200)

    def test_users(self):

        payload = {
            'name': 'Napoleon Bonaparte',
            'login': 'napoleon@bonaparte.fr',
            'provider': 'google',
            'text': 'added to circle of trust'
        }

        # create user
        response = self.app.post('/user', data=json.dumps(payload), headers=self.headers)
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data)
        self.assertIsNotNone(data['user'], 'Failed to create user')

        user_id = data['user']

        # get user
        response = self.app.get('/users', headers=self.headers)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertIn(user_id, [u['id'] for u in data['users']])

        # create duplicate user
        response = self.app.post('/user', data=json.dumps(payload), headers=self.headers)
        self.assertEqual(response.status_code, 409)

        # delete user
        response = self.app.delete('/user/' + user_id, headers=self.headers)
        self.assertEqual(response.status_code, 200)

    def test_login(self):

        payload = {
            'name': 'Napoleon Bonaparte',
            'email': 'napoleon@bonaparte.fr',
            'password': 'j0s3ph1n3',
            'provider': 'basic',
            'text': 'Test login'
        }

        # sign-up user
        response = self.app.post('/auth/signup', data=json.dumps(payload), headers={'Content-type': 'application/json'})
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertIn('token', data)

        token = data['token']

        headers = {
            'Authorization': 'Bearer ' + token,
            'Content-type': 'application/json'
        }

        # get user
        response = self.app.get('/users', headers=headers)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertIn(payload['name'], [u['name'] for u in data['users']])

        user_id = [u['id'] for u in data['users'] if u['name'] == payload['name']][0]

        # delete user
        response = self.app.delete('/user/' + user_id, headers=self.headers)
        self.assertEqual(response.status_code, 200)
