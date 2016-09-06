
import unittest

try:
    import simplejson as json
except ImportError:
    import json

from uuid import uuid4

from alerta.app import app


class PluginsTestCase(unittest.TestCase):

    def setUp(self):

        app.config['TESTING'] = True
        app.config['AUTH_REQUIRED'] = False
        app.config['PLUGINS'] = ['reject']
        self.app = app.test_client()

        self.resource = str(uuid4()).upper()[:8]

        self.reject_alert = {
            'event': 'node_marginal',
            'resource': self.resource,
            'environment': 'Production',
            'service': [],  # alert will be rejected because service not defined
            'severity': 'warning',
            'correlate': ['node_down', 'node_marginal', 'node_up']
        }

        self.accept_alert = {
            'event': 'node_marginal',
            'resource': self.resource,
            'environment': 'Production',
            'service': ['Network'],  # alert will be accepted because service not defined
            'severity': 'warning',
            'correlate': ['node_down', 'node_marginal', 'node_up']
        }

        self.headers = {
            'Content-type': 'application/json'
        }

    def tearDown(self):

        pass

    def test_reject_alert(self):

        # create alert that will be rejected
        response = self.app.post('/alert', data=json.dumps(self.reject_alert), headers=self.headers)
        self.assertEqual(response.status_code, 403)
        data = json.loads(response.data.decode('utf-8'))
        self.assertEqual(data['status'], 'error')
        self.assertEqual(data['message'], '[POLICY] Alert must define a service')

        # create alert that will be accepted
        response = self.app.post('/alert', data=json.dumps(self.accept_alert), headers=self.headers)
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data.decode('utf-8'))
        self.assertEqual(data['status'], 'ok')
        self.assertRegexpMatches(data['id'], '[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}')
