import json
import unittest

from uuid import uuid4

from alerta.app import app


class PluginsTestCase(unittest.TestCase):

    def setUp(self):

        app.config['TESTING'] = True
        app.config['AUTH_REQUIRED'] = False
        app.config['PLUGINS'] = ['amqp', 'enhance', 'logstash', 'normalise', 'reject', 'sns']
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

        self.headers = {
            'Content-type': 'application/json'
        }

    def tearDown(self):

        pass

    def test_reject_alert(self):

        # create alert
        response = self.app.post('/alert', data=json.dumps(self.reject_alert), headers=self.headers)
        self.assertEqual(response.status_code, 403)
