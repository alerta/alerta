
import unittest

from uuid import uuid4

try:
    import simplejson as json
except ImportError:
    import json

from alerta.app import app, db


class WebhooksTestCase(unittest.TestCase):

    def setUp(self):

        app.config['TESTING'] = True
        app.config['AUTH_REQUIRED'] = False
        self.app = app.test_client()


        self.trigger_alert = {
            'event': 'node_down',
            'resource': str(uuid4()).upper()[:8],
            'environment': 'Production',
            'service': ['Network'],
            'severity': 'critical',
            'correlate': ['node_down', 'node_marginal', 'node_up'],
            'tags': ['foo'],
            'attributes': {'foo': 'abc def', 'bar': 1234, 'baz': False}
        }
        self.resolve_alert = {
            'event': 'node_marginal',
            'resource': str(uuid4()).upper()[:8],
            'environment': 'Production',
            'service': ['Network'],
            'severity': 'critical',
            'correlate': ['node_down', 'node_marginal', 'node_up']
        }

        self.pagerduty_alert = """
            {
              "messages": [
                {
                  "id": "bb8b8fe0-e8d5-11e2-9c1e-22000afd16cf",
                  "created_on": "2013-07-09T20:25:44Z",
                  "type": "incident.acknowledge",
                  "data": {
                    "incident": {
                      "id": "PIJ90N7",
                      "incident_number": 1,
                      "created_on": "2013-07-09T20:25:44Z",
                      "status": "triggered",
                      "html_url": "https://acme.pagerduty.com/incidents/PIJ90N7",
                      "incident_key": "%s",
                      "service": {
                        "id": "PBAZLIU",
                        "name": "service",
                        "html_url": "https://acme.pagerduty.com/services/PBAZLIU"
                      },
                      "assigned_to_user": {
                        "id": "PPI9KUT",
                        "name": "Alan Kay",
                        "email": "alan@pagerduty.com",
                        "html_url": "https://acme.pagerduty.com/users/PPI9KUT"
                      },
                      "trigger_summary_data": {
                        "subject": "45645"
                      },
                      "trigger_details_html_url": "https://acme.pagerduty.com/incidents/PIJ90N7/log_entries/PIJ90N7",
                      "last_status_change_on": "2013-07-09T20:25:44Z",
                      "last_status_change_by": "null"
                    }
                  }
                },
                {
                  "id": "8a1d6420-e9c4-11e2-b33e-f23c91699516",
                  "created_on": "2013-07-09T20:25:45Z",
                  "type": "incident.resolve",
                  "data": {
                    "incident": {
                      "id": "PIJ90N7",
                      "incident_number": 1,
                      "created_on": "2013-07-09T20:25:44Z",
                      "status": "resolved",
                      "html_url": "https://acme.pagerduty.com/incidents/PIJ90N7",
                      "incident_key": "%s",
                      "service": {
                        "id": "PBAZLIU",
                        "name": "service",
                        "html_url": "https://acme.pagerduty.com/services/PBAZLIU"
                      },
                      "assigned_to_user": "null",
                      "resolved_by_user": {
                        "id": "PPI9KUT",
                        "name": "Alan Kay",
                        "email": "alan@pagerduty.com",
                        "html_url": "https://acme.pagerduty.com/users/PPI9KUT"
                      },
                      "trigger_summary_data": {
                        "subject": "45645"
                      },
                      "trigger_details_html_url": "https://acme.pagerduty.com/incidents/PIJ90N7/log_entries/PIJ90N7",
                      "last_status_change_on": "2013-07-09T20:25:45Z",
                      "last_status_change_by": {
                        "id": "PPI9KUT",
                        "name": "Alan Kay",
                        "email": "alan@pagerduty.com",
                        "html_url": "https://acme.pagerduty.com/users/PPI9KUT"
                      }
                    }
                  }
                }
              ]
            }
        """

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
            'Content-type': 'application/json',
            'X-Forwarded-For': ['10.1.1.1', '172.16.1.1', '192.168.1.1'],
        }

        self.grafana_alert = """
        {  
           "evalMatches":[  
              {  
                 "value":100,
                 "metric":"High value",
                 "tags":null
              },
              {  
                 "value":200,
                 "metric":"Higher Value",
                 "tags":null
              }
           ],
           "imageUrl":"http://grafana.org/assets/img/blog/mixed_styles.png",
           "ruleId":0,
           "ruleName":"Test notification",
           "ruleUrl":"http://localhost:3000/",
           "state":"alerting",
           "title":"[Alerting] Test notification"
        }
        """


    def tearDown(self):

        db.destroy_db()

    def test_pagerduty_webhook(self):

        # trigger alert
        response = self.app.post('/alert', data=json.dumps(self.trigger_alert), headers=self.headers)
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data.decode('utf-8'))
        trigger_alert_id = data['id']

        # resolve alert
        response = self.app.post('/alert', data=json.dumps(self.resolve_alert), headers=self.headers)
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data.decode('utf-8'))
        resolve_alert_id = data['id']

        response = self.app.post('/webhooks/pagerduty', data=self.pagerduty_alert % (trigger_alert_id, resolve_alert_id), headers=self.headers)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(db.get_alert(trigger_alert_id).status, "ack")
        self.assertEqual(db.get_alert(resolve_alert_id).status, "closed")

    def test_prometheus_webhook(self):

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
        self.assertEqual(data['alert']['attributes']['ip'], '192.168.1.1')

        response = self.app.post('/webhooks/grafana', data=self.grafana_alert, headers=self.headers)
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data.decode('utf-8'))
        self.assertEqual(data['alert']['timeout'], 300)
        self.assertEqual(data['alert']['resource'], "Higher Value")
        self.assertEqual(data['alert']['status'], 'open')
        self.assertEqual(data['alert']['severity'], 'critical')

