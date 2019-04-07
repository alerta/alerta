
import json
import unittest
from uuid import uuid4

from alerta.app import create_app, db


class ManagementTestCase(unittest.TestCase):

    def setUp(self):

        test_config = {
            'TESTING': True,
            'AUTH_REQUIRED': False
        }
        self.app = create_app(test_config)
        self.client = self.app.test_client()

        self.headers = {
            'Content-type': 'application/json'
        }

        self.resource = str(uuid4()).upper()[:8]

        self.major_alert = {
            'event': 'node_down',
            'resource': self.resource,
            'environment': 'Production',
            'service': ['Network'],
            'severity': 'major',
            'correlate': ['node_down', 'node_marginal', 'node_up'],
            'tags': ['foo'],
            'attributes': {'foo': 'abc def', 'bar': 1234, 'baz': False}
        }

    def tearDown(self):
        db.destroy()

    def test_alert(self):

        # create alert
        response = self.client.post('/alert', data=json.dumps(self.major_alert), headers=self.headers)
        self.assertEqual(response.status_code, 201)
        response = self.client.get('/management/status', headers=self.headers)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data.decode('utf-8'))
        for metric in data['metrics']:
            if metric['name'] == 'total':
                self.assertGreaterEqual(metric['value'], 1)

    def test_housekeeping(self):

        response = self.client.get('/management/housekeeping', headers=self.headers)
        self.assertEqual(response.status_code, 200)
