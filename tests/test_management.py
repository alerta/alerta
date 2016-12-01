
import unittest

from uuid import uuid4

try:
    import simplejson as json
except ImportError:
    import json

from alerta.app import app, db


class AlertTestCase(unittest.TestCase):

    def setUp(self):

        app.config['TESTING'] = True
        app.config['AUTH_REQUIRED'] = False
        self.app = app.test_client()

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

        db.destroy_db()

    def test_alert(self):

        # create alert
        response = self.app.post('/alert', data=json.dumps(self.major_alert), headers=self.headers)
        self.assertEqual(response.status_code, 201)
        response = self.app.get('/management/status', headers=self.headers)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data.decode('utf-8'))
        for metric in data['metrics']:
            if metric['name'] == 'total':
                self.assertEqual(metric['value'], 1)

