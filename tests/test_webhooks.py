
import unittest

try:
    import simplejson as json
except ImportError:
    import json

from alerta.app import app


class AlertTestCase(unittest.TestCase):

    def setUp(self):

        app.config['TESTING'] = True
        app.config['AUTH_REQUIRED'] = False
        self.app = app.test_client()

        self.prometheus_alert = """
            {
                "alerts": [
                    {
                        "annotations": {
                            "description": "Connect to host2 fails",
                            "summary": "Connect fail"
                        },
                        "endsAt": "0001-01-01T00:00:00Z",
                        "generatorURL": "http://prometheus.host:9090/...",
                        "labels": {
                            "__name__": "ping_success",
                            "alertname": "failedConnect",
                            "environment": "Production",
                            "instance": "host2",
                            "job": "pinger",
                            "monitor": "testlab",
                            "service": "System",
                            "severity": "critical",
                            "timeout": "600"
                        },
                        "startsAt": "2016-08-01T13:27:08.008+03:00",
                        "status": "firing"
                    }
                ],
                "commonAnnotations": {
                    "summary": "Connect fail"
                },
                "commonLabels": {
                    "__name__": "ping_success",
                    "alertname": "failedConnect",
                    "environment": "Production",
                    "job": "pinger",
                    "monitor": "testlab",
                    "service": "System",
                    "severity": "critical",
                    "timeout": "600"
                },
                "externalURL": "http://alertmanager.host:9093",
                "groupKey": 5615590933959184469,
                "groupLabels": {
                    "alertname": "failedConnect"
                },
                "receiver": "alerta",
                "status": "firing",
                "version": "3"
            }
        """
        self.headers = {
            'Content-type': 'application/json'
        }

    def tearDown(self):

        pass

    def test_alert(self):

        # create alert
        response = self.app.post('/webhooks/prometheus', data=self.prometheus_alert, headers=self.headers)
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data.decode('utf-8'))
        self.assertEqual(data['alert']['resource'], "host2")
        self.assertEqual(data['alert']['event'], "failedConnect")
        self.assertEqual(data['alert']['status'], 'open')
        self.assertEqual(data['alert']['severity'], 'critical')
        self.assertEqual(data['alert']['timeout'], 600)
        self.assertEqual(data['alert']['createTime'], "2016-08-01T10:27:08.008Z")
