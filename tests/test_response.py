import json
import unittest

from alerta.app import create_app, db


class ApiResponseTestCase(unittest.TestCase):

    def setUp(self):
        test_config = {
            'TESTING': True,
            'BASE_URL': 'https://api.alerta.dev:9898/_'
        }
        self.app = create_app(test_config)
        self.client = self.app.test_client()

        self.prod_alert = {
            'id': 'custom-alert-id',
            'resource': 'node404',
            'event': 'node_down',
            'environment': 'Production',
            'severity': 'major',
            'correlate': ['node_down', 'node_marginal', 'node_up'],
            'service': ['Core', 'Web', 'Network'],
            'group': 'Network',
            'tags': ['level=20', 'switch:off']
        }

    def tearDown(self):
        db.destroy()

    def test_response_href(self):

        # create alert
        response = self.client.post('/alert', json=self.prod_alert)
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data.decode('utf-8'))
        self.assertEqual(data['alert']['href'], 'https://api.alerta.dev:9898/_/alert/custom-alert-id')
