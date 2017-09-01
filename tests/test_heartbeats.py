
import unittest

try:
    import simplejson as json
except ImportError:
    import json

from uuid import uuid4
from alerta.app import create_app, db


class HeartbeatTestCase(unittest.TestCase):

    def setUp(self):

        test_config = {
            'TESTING': True,
            'AUTH_REQUIRED': False
        }
        self.app = create_app(test_config)
        self.client = self.app.test_client()

        self.origin = str(uuid4()).upper()[:8]

        self.heartbeat = {
            'origin': self.origin,
            'tags': ['foo', 'bar', 'baz']
        }

        self.headers = {
            'Content-type': 'application/json'
        }

    def tearDown(self):

        with self.app.app_context():
            db.destroy()

    def test_heartbeat(self):

        # create heartbeat
        response = self.client.post('/heartbeat', data=json.dumps(self.heartbeat), headers=self.headers)
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data.decode('utf-8'))
        self.assertEqual(data['heartbeat']['origin'], self.origin)
        self.assertListEqual(data['heartbeat']['tags'], self.heartbeat['tags'])

        heartbeat_id = data['id']

        # create duplicate heartbeat
        response = self.client.post('/heartbeat', data=json.dumps(self.heartbeat), headers=self.headers)
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data.decode('utf-8'))
        self.assertEquals(heartbeat_id, data['heartbeat']['id'])

        # get heartbeat
        response = self.client.get('/heartbeat/' + heartbeat_id)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data.decode('utf-8'))
        self.assertEquals(heartbeat_id, data['heartbeat']['id'])

        # delete heartbeat
        response = self.client.delete('/heartbeat/' + heartbeat_id)
        self.assertEqual(response.status_code, 200)

    def test_heartbeat_not_found(self):

        response = self.client.get('/heartbeat/doesnotexist')
        self.assertEqual(response.status_code, 404)

    def test_get_heartbeats(self):

        # create heartbeat
        response = self.client.post('/heartbeat', data=json.dumps(self.heartbeat), headers=self.headers)
        self.assertEqual(response.status_code, 201)

        response = self.client.get('/heartbeats')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data.decode('utf-8'))
        self.assertGreater(data['total'], 0, "total heartbeats > 0")
