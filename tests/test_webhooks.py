import json
import unittest

from uuid import uuid4
from alerta.app import app


class AlertTestCase(unittest.TestCase):

    def setUp(self):

        app.config['TESTING'] = True
        app.config['AUTH_REQUIRED'] = False
        self.app = app.test_client()

        self.prometheus_alert = """
            {
              "status": "firing",
              "groupLabels": {
                "service": "Web",
                "alertname": "WebRequestsAlert"
              },
              "groupKey": 5216802543683841573,
              "commonAnnotations": {
                "summary": "alert triggered",
                "runbook": "http://wiki.alerta.io"
              },
              "alerts": [
                {
                  "status": "firing",
                  "labels": {
                    "code": "200",
                    "group": "Apache",
                    "monitor": "codelab-monitor",
                    "service": "Web",
                    "timeout": "600",
                    "value": "51",
                    "instance": "localhost:9090",
                    "job": "prometheus",
                    "handler": "prometheus",
                    "alertname": "WebRequestsAlert",
                    "__name__": "http_requests_total",
                    "method": "get",
                    "severity": "minor"
                  },
                  "endsAt": "0001-01-01T00:00:00Z",
                  "generatorURL": "http://macbookpro.home:9090/graph#%5B%7B%22expr%22%3A%22http_requests_total%20%3E%200%22%2C%22tab%22%3A0%7D%5D",
                  "startsAt": "2016-08-02T00:09:37.809+01:00",
                  "annotations": {
                    "summary": "alert triggered",
                    "description": "complete alert triggered at 51",
                    "runbook": "http://wiki.alerta.io"
                  }
                }
              ],
              "version": "3",
              "receiver": "alerta",
              "externalURL": "http://macbookpro.home:9093",
              "commonLabels": {
                "code": "200",
                "group": "Apache",
                "monitor": "codelab-monitor",
                "service": "Web",
                "timeout": "600",
                "instance": "localhost:9090",
                "job": "prometheus",
                "handler": "prometheus",
                "alertname": "WebRequestsAlert",
                "__name__": "http_requests_total",
                "method": "get",
                "severity": "minor"
              }
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
        self.assertEqual(data['alert']['resource'], "localhost:9090")
        self.assertEqual(data['alert']['event'], "WebRequestsAlert")
        self.assertEqual(data['alert']['status'], 'open')
        self.assertEqual(data['alert']['severity'], 'minor')
        self.assertEqual(data['alert']['timeout'], 600)
