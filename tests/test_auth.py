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

    def tearDown(self):

        pass

    def test_401_error(self):

        response = self.app.get('/alerts')
        self.assertEqual(response.status_code, 401)

    def test_readwrite_key(self):

        headers = {
            'Authorization': 'Key %s' % self.api_key,
            'Content-type': 'application/json'
        }
        payload = {
            'user': 'rw-demo-key',
            'type': 'read-write'
        }

        response = self.app.post('/key', data=json.dumps(payload), headers=headers)
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data)
        self.assertIsNotNone(data['key'], 'Failed to create read-write key')

        read_write_key = data['key']

        response = self.app.post('/alert', data=json.dumps(self.alert), headers={'Authorization': 'Key ' + read_write_key})
        self.assertEqual(response.status_code, 201)

        response = self.app.get('/alerts', headers={'Authorization': 'Key ' + read_write_key})
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertGreater(data['total'], 1, "total alerts > 1")

        response = self.app.delete('/key/' + read_write_key, headers={'Authorization': 'Key ' + self.api_key})
        self.assertEqual(response.status_code, 200)

    def test_readonly_key(self):

        headers = {
            'Authorization': 'Key %s' % self.api_key,
            'Content-type': 'application/json'
        }
        payload = {
            'user': 'ro-demo-key',
            'type': 'read-only'
        }

        response = self.app.post('/key', data=json.dumps(payload), headers=headers)
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data)
        self.assertIsNotNone(data['key'], 'Failed to create read-only key')

        read_only_key = data['key']

        response = self.app.post('/alert', data=json.dumps(self.alert), headers={'Authorization': 'Key ' + read_only_key})
        self.assertEqual(response.status_code, 403)

        response = self.app.get('/alerts', headers={'Authorization': 'Key ' + read_only_key})
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertGreater(data['total'], 1, "total alerts > 1")

        response = self.app.delete('/key/' + read_only_key, headers={'Authorization': 'Key ' + self.api_key})
        self.assertEqual(response.status_code, 200)

    def test_users(self):

        pass
