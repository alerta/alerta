
import json
import unittest
from io import BytesIO
from uuid import uuid4

from alerta.app import create_app, custom_webhooks, db
from alerta.models.alert import Alert
from alerta.webhooks import WebhookBase


class WebhooksTestCase(unittest.TestCase):

    def setUp(self):

        test_config = {
            'TESTING': True,
            'AUTH_REQUIRED': False
        }
        self.app = create_app(test_config)
        self.client = self.app.test_client()

        # alert templates
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

        self.cloudwatch_subscription_confirmation = r"""
            {
              "Type" : "SubscriptionConfirmation",
              "MessageId" : "8a14e4f3-f3ab-4be0-a12f-681ee8fe214f",
              "Token" : "2336412f37fb687f5d51e6e241da92fd72d769c5b4ca6fd6cd6d30949d5a51abf7e21aae199b52813b6f2ea51b41e3119b599532d25df4e6aea368b3a6d8272d38688f73c116b04204e9afb2f5b1d8c4bdb823103299a9f1da7409f1dcf4096ba20a0b0222cc493586e76450e3be6715",
              "TopicArn" : "arn:aws:sns:eu-west-1:1234567890:alerta-test",
              "Message" : "You have chosen to subscribe to the topic arn:aws:sns:eu-west-1:1234567890:alerta-test.\nTo confirm the subscriptionDataBuilder, visit the SubscribeURL included in this message.",
              "SubscribeURL" : "https://sns.eu-west-1.amazonaws.com/?Action=ConfirmSubscription&TopicArn=arn:aws:sns:eu-west-1:1234567890:alerta-test&Token=2336412f37fb687f5d51e6e241da92fd72d769c5b4ca6fd6cd6d30949d5a51abf7e21aae199b52813b6f2ea51b41e3119b599532d25df4e6aea368b3a6d8272d38688f73c116b04204e9afb2f5b1d8c4bdb823103299a9f1da7409f1dcf4096ba20a0b0222cc493586e76450e3be6715",
              "Timestamp" : "2018-07-08T21:33:44.782Z",
              "SignatureVersion" : "1",
              "Signature" : "os7PC+SYxz+6Ms92k5T6QDEHOJ8SIgKYL2vR987rSgTk91qqVoY1wTa0kl4SD4Abwb8oAdeL5bXAeoWjwOe8wD88GTEmYRwgGALC2tgrMZP9fBg/5WlHpbUPkcI8Ch8OMxAS8Lmn3ZUq814Vmvse8jqCNyNPquBIxT8KUaka0wFivaVTMKa43OWEWoHKlEfriFD1dtkmI2kKpsJpH7x2Az/izJMpWX9hJpA6aeiuzeeO2LOlLAzH2qD1PmUguPZCUVwbcEiySOD2tL+uwDDiN22h3QxYd9Je8ZfNSwimSbdpQzyumOtoogP9dAHcua8sSo3glPuakNzdFhrWywBVFQ==",
              "SigningCertURL" : "https://sns.eu-west-1.amazonaws.com/SimpleNotificationService-eaea6120e66ea12e88dcd8bcbddca752.pem"
            }
        """

        self.pingdom_down = """
            {
                "second_probe": {
                    "ip": "185.39.146.214",
                    "location": "Stockholm 2, Sweden",
                    "ipv6": "2a02:752:100:e::4002"
                },
                "check_type": "HTTP",
                "first_probe": {
                    "ip": "85.93.93.123",
                    "location": "Strasbourg 5, France",
                    "ipv6": ""
                },
                "tags": [],
                "check_id": 803318,
                "current_state": "DOWN",
                "check_params": {
                    "url": "/",
                    "encryption": false,
                    "hostname": "api.alerta.io",
                    "basic_auth": false,
                    "port": 80,
                    "header": "User-Agent:Pingdom.com_bot_version_1.4_(http://www.pingdom.com/)",
                    "ipv6": false,
                    "full_url": "http://api.alerta.io/"
                },
                "previous_state": "UP",
                "check_name": "Alerta API on OpenShift",
                "version": 1,
                "state_changed_timestamp": 1498861543,
                "importance_level": "HIGH",
                "state_changed_utc_time": "2017-06-30T22:25:43",
                "long_description": "HTTP Server Error 503 Service Unavailable",
                "description": "HTTP Error 503"
            }
        """

        self.pingdom_up = """
            {
                "second_probe": {},
                "check_type": "HTTP",
                "first_probe": {
                    "ip": "185.70.76.23",
                    "location": "Athens, Greece",
                    "ipv6": ""
                },
                "tags": [],
                "check_id": 803318,
                "current_state": "UP",
                "check_params": {
                    "url": "/",
                    "encryption": false,
                    "hostname": "api.alerta.io",
                    "basic_auth": false,
                    "port": 80,
                    "header": "User-Agent:Pingdom.com_bot_version_1.4_(http://www.pingdom.com/)",
                    "ipv6": false,
                    "full_url": "http://api.alerta.io/"
                },
                "previous_state": "DOWN",
                "check_name": "Alerta API on OpenShift",
                "version": 1,
                "state_changed_timestamp": 1498861843,
                "importance_level": "HIGH",
                "state_changed_utc_time": "2017-06-30T22:30:43",
                "long_description": "OK",
                "description": "OK"
            }
        """

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

        self.riemann_alert = """
          {
            "host": "hostbob",
            "service": "servicejane",
            "state": "ok",
            "description": "This is a description",
            "metric": 1
          }
        """

        self.stackdriver_open = """
        {
            "incident": {
                "incident_id": "f2e08c333dc64cb09f75eaab355393bz",
                "resource_id": "i-4a266a2d",
                "resource_name": "webserver-85",
                "state": "open",
                "started_at": 1499368214,
                "ended_at": null,
                "policy_name": "Webserver Health",
                "condition_name": "CPU usage",
                "url": "https://app.stackdriver.com/incidents/f2e08c333dc64cb09f75eaab355393bz",
                "summary": "CPU (agent) for webserver-85 is above the threshold of 1% with a value of 28.5%"
            },
            "version": "1.1"
        }
        """

        self.stackdriver_closed = """
        {
            "incident": {
                "incident_id": "f2e08c333dc64cb09f75eaab355393bz",
                "resource_id": "i-4a266a2d",
                "resource_name": "webserver-85",
                "state": "closed",
                "started_at": 1499368214,
                "ended_at": 1499368836,
                "policy_name": "Webserver Health",
                "condition_name": "CPU usage",
                "url": "https://app.stackdriver.com/incidents/f2e08c333dc64cb09f75eaab355393bz",
                "summary": "CPU (agent) for webserver-85 is above the threshold of 1% with a value of 28.5%"
            },
            "version": "1.1"
        }
        """

        self.prometheus_v3_alert = """
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

        self.prometheus_v4_alert = """
            {
                "receiver": "alerta",
                "status": "firing",
                "alerts": [
                    {
                        "status": "firing",
                        "labels": {
                            "alertname": "thing_dead"
                        },
                        "annotations": {
                            "description": "No things have been recorded for over 10 minutes. Something terrible is happening.",
                            "severity": "critical",
                            "summary": "No things for over 10 minutes"
                        },
                        "startsAt": "2017-08-03T15:17:37.804-04:00",
                        "endsAt": "0001-01-01T00:00:00Z",
                        "generatorURL": "http://somehost:9090/graph?g0.expr=sum%28irate%28messages_received_total%5B5m%5D%29%29+%3D%3D+0&g0.tab=0"
                    }
                ],
                "groupLabels": {
                    "alertname": "thing_dead"
                },
                "commonLabels": {
                    "alertname": "thing_dead"
                },
                "commonAnnotations": {
                    "description": "No things have been recorded for over 10 minutes. Something terrible is happening.",
                    "severity": "critical",
                    "summary": "No things for over 10 minutes"
                },
                "externalURL": "http://somehost:9093",
                "version": "4",
                "groupKey": "{}:{alertname=thing_dead}"
            }
        """

        self.grafana_alert_alerting = """
        {
            "evalMatches": [
                {
                    "value": 97.007606,
                    "metric": "user",
                    "tags": {
                        "__name__": "netdata_cpu_cpu_percentage_average",
                        "chart": "cpu.cpu0",
                        "dimension": "user",
                        "family": "utilization",
                        "instance": "zeta.domain",
                        "job": "monitoring",
                        "info.host_id": "i-0d0721c7f97545d43"
                    }
                }
            ],
            "message": "boom!",
            "ruleId": 7,
            "ruleName": "Zeta CPU alert",
            "ruleUrl": "https://grafana.domain.tld/dashboard/db/alarms?fullscreen&edit&tab=alert&panelId=1&orgId=1",
            "state": "alerting",
            "title": "[Alerting] CPU alert"
        }
        """

        self.grafana_alert_ok = """
        {
            "evalMatches": [],
            "message": "boom!",
            "ruleId": 7,
            "ruleName": "Zeta CPU alert",
            "ruleUrl": "https://grafana.domain.tld/dashboard/db/alarms?fullscreen&edit&tab=alert&panelId=1&orgId=1",
            "state": "ok",
            "title": "[OK] CPU alert"
        }
        """

        self.telegram_alert = {
            'event': 'node_down',
            'resource': str(uuid4()).upper()[:8],
            'environment': 'Production',
            'service': ['Network'],
            'severity': 'critical',
            'correlate': ['node_down', 'node_marginal', 'node_up'],
            'tags': ['foo'],
            'attributes': {'foo': 'abc def', 'bar': 1234, 'baz': False}
        }

        self.telegram_ack = """
        {
            "update_id": 913527394,
            "callback_query": {
                "id": "688111769854308995",
                "from": {
                    "id": 160213506,
                    "first_name": "Nick",
                    "last_name": "Satterly",
                    "username": "satterly"
                },
                "message": {
                    "message_id": 37,
                    "from": {
                        "id": 264434259,
                        "first_name": "alerta-bot",
                        "username": "alertaio_bot"
                    },
                    "chat": {
                        "id": -163056465,
                        "title": "Alerta Telegram",
                        "type": "group",
                        "all_members_are_administrators": true
                    },
                    "date": 1481841548,
                    "text": "",
                    "entities": [
                        {
                            "type": "text_link",
                            "offset": 0,
                            "length": 8,
                            "url": "https://try.alerta.io/#/alert/a2b47856-1779-49a9-a2aa-5cbd2e539b56"
                        }
                    ]
                },
                "chat_instance": "-428019502972440238",
                "data": "/ack %s"
            }
        }
        """

        self.graylog_notification = """
         {
             "check_result": {
                 "result_description": "Stream had 2 messages in the last 1 minutes with trigger condition more than 1 messages. (Current grace time: 1 minutes)",
                 "triggered_condition": {
                     "id": "5e7a9c8d-9bb1-47b6-b8db-4a3a83a25e0c",
                     "type": "MESSAGE_COUNT",
                     "created_at": "2015-09-10T09:44:10.552Z",
                     "creator_user_id": "admin",
                     "grace": 1,
                     "parameters": {
                         "grace": 1,
                         "threshold": 1,
                         "threshold_type": "more",
                         "backlog": 5,
                         "time": 1
                     },
                     "description": "time: 1, threshold_type: more, threshold: 1, grace: 1",
                     "type_string": "MESSAGE_COUNT",
                     "backlog": 5
                 },
                 "triggered_at": "2015-09-10T09:45:54.749Z",
                 "triggered": true,
                 "matching_messages": [
                     {
                         "index": "graylog2_7",
                         "message": "WARN: System is failing",
                         "fields": {
                             "gl2_remote_ip": "127.0.0.1",
                             "gl2_remote_port": 56498,
                             "gl2_source_node": "41283fec-36b4-4352-a859-7b3d79846b3c",
                             "gl2_source_input": "55f15092bee8e2841898eb53"
                         },
                         "id": "b7b08150-57a0-11e5-b2a2-d6b4cd83d1d5",
                         "stream_ids": [
                             "55f1509dbee8e2841898eb64"
                         ],
                         "source": "127.0.0.1",
                         "timestamp": "2015-09-10T09:45:49.284Z"
                     },
                     {
                         "index": "graylog2_7",
                         "message": "ERROR: This is an example error message",
                         "fields": {
                             "gl2_remote_ip": "127.0.0.1",
                             "gl2_remote_port": 56481,
                             "gl2_source_node": "41283fec-36b4-4352-a859-7b3d79846b3c",
                             "gl2_source_input": "55f15092bee8e2841898eb53"
                         },
                         "id": "afd71342-57a0-11e5-b2a2-d6b4cd83d1d5",
                         "stream_ids": [
                             "55f1509dbee8e2841898eb64"
                         ],
                         "source": "127.0.0.1",
                         "timestamp": "2015-09-10T09:45:36.116Z"
                     }
                 ]
             },
             "stream": {
                 "creator_user_id": "admin",
                 "outputs": [],
                 "matching_type": "AND",
                 "description": "test stream",
                 "created_at": "2015-09-10T09:42:53.833Z",
                 "disabled": false,
                 "rules": [
                     {
                         "field": "gl2_source_input",
                         "stream_id": "55f1509dbee8e2841898eb64",
                         "id": "55f150b5bee8e2841898eb7f",
                         "type": 1,
                         "inverted": false,
                         "value": "55f15092bee8e2841898eb53"
                     }
                 ],
                 "alert_conditions": [
                     {
                         "creator_user_id": "admin",
                         "created_at": "2015-09-10T09:44:10.552Z",
                         "id": "5e7a9c8d-9bb1-47b6-b8db-4a3a83a25e0c",
                         "type": "message_count",
                         "parameters": {
                             "grace": 1,
                             "threshold": 1,
                             "threshold_type": "more",
                             "backlog": 5,
                             "time": 1
                         }
                     }
                 ],
                 "id": "55f1509dbee8e2841898eb64",
                 "title": "test",
                 "content_pack": null
             }
         }
        """

        self.headers = {
            'Content-type': 'application/json',
            'X-Forwarded-For': ['10.1.1.1', '172.16.1.1', '192.168.1.1'],
        }

    def tearDown(self):
        db.destroy()

    def test_cloudwatch_webhook(self):

        # subscription confirmation
        response = self.client.post('/webhooks/cloudwatch',
                                    data=self.cloudwatch_subscription_confirmation, headers=self.headers)
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data.decode('utf-8'))
        self.assertEqual(data['alert']['resource'], 'arn:aws:sns:eu-west-1:1234567890:alerta-test')

    def test_pingdom_webhook(self):

        # http down
        response = self.client.post('/webhooks/pingdom', data=self.pingdom_down, headers=self.headers)
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data.decode('utf-8'))
        self.assertEqual(data['alert']['resource'], 'Alerta API on OpenShift')
        self.assertEqual(data['alert']['event'], 'DOWN')
        self.assertEqual(data['alert']['severity'], 'critical')
        self.assertEqual(data['alert']['text'], 'HIGH: HTTP Server Error 503 Service Unavailable')
        self.assertEqual(data['alert']['value'], 'HTTP Error 503')

        # http up
        response = self.client.post('/webhooks/pingdom', data=self.pingdom_up, headers=self.headers)
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data.decode('utf-8'))
        self.assertEqual(data['alert']['resource'], 'Alerta API on OpenShift')
        self.assertEqual(data['alert']['event'], 'UP')
        self.assertEqual(data['alert']['severity'], 'normal')
        self.assertEqual(data['alert']['text'], 'HIGH: OK')
        self.assertEqual(data['alert']['value'], 'OK')

    def test_pagerduty_webhook(self):

        # trigger alert
        response = self.client.post('/alert', data=json.dumps(self.trigger_alert), headers=self.headers)
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data.decode('utf-8'))
        trigger_alert_id = data['id']

        # resolve alert
        response = self.client.post('/alert', data=json.dumps(self.resolve_alert), headers=self.headers)
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data.decode('utf-8'))
        resolve_alert_id = data['id']

        response = self.client.post('/webhooks/pagerduty', data=self.pagerduty_alert %
                                    (trigger_alert_id, resolve_alert_id), headers=self.headers)
        self.assertEqual(response.status_code, 200)

        # get alert
        response = self.client.get('/alert/' + trigger_alert_id)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data.decode('utf-8'))
        self.assertIn(trigger_alert_id, data['alert']['id'])
        self.assertEqual(data['alert']['status'], 'ack')

        # get alert
        response = self.client.get('/alert/' + resolve_alert_id)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data.decode('utf-8'))
        self.assertIn(resolve_alert_id, data['alert']['id'])
        self.assertEqual(data['alert']['status'], 'closed')

    def test_prometheus_webhook(self):

        # create v3 alert
        response = self.client.post('/webhooks/prometheus', data=self.prometheus_v3_alert, headers=self.headers)
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data.decode('utf-8'))
        self.assertEqual(data['alert']['resource'], "host2")
        self.assertEqual(data['alert']['event'], "failedConnect")
        self.assertEqual(data['alert']['status'], 'open')
        self.assertEqual(data['alert']['severity'], 'critical')
        self.assertEqual(data['alert']['timeout'], 600)
        self.assertEqual(data['alert']['createTime'], "2016-08-01T10:27:08.008Z")
        self.assertEqual(data['alert']['attributes']['ip'], '192.168.1.1')

        # create v4 alert
        response = self.client.post('/webhooks/prometheus', data=self.prometheus_v4_alert, headers=self.headers)
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data.decode('utf-8'))
        self.assertEqual(data['alert']['resource'], "n/a")
        self.assertEqual(data['alert']['event'], "thing_dead")
        self.assertEqual(data['alert']['status'], 'open')
        self.assertEqual(data['alert']['severity'], 'warning')
        self.assertEqual(data['alert']['timeout'], 86400)
        self.assertEqual(data['alert']['createTime'], "2017-08-03T19:17:37.804Z")
        self.assertEqual(data['alert']['attributes']['ip'], '192.168.1.1')

    def test_riemann_webhook(self):

        # create alert
        response = self.client.post('/webhooks/riemann', data=self.riemann_alert, headers=self.headers)
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data.decode('utf-8'))
        self.assertEqual(data['alert']['resource'], 'hostbob-servicejane')
        self.assertEqual(data['alert']['event'], 'servicejane')
        self.assertEqual(data['alert']['severity'], 'ok')
        self.assertEqual(data['alert']['text'], 'This is a description')
        self.assertEqual(data['alert']['value'], '1')

    def test_stackdriver_webhook(self):

        # open alert
        response = self.client.post('/webhooks/stackdriver', data=self.stackdriver_open, headers=self.headers)
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data.decode('utf-8'))
        self.assertEqual(data['alert']['resource'], 'webserver-85')
        self.assertEqual(data['alert']['event'], 'CPU usage')
        self.assertEqual(data['alert']['severity'], 'critical')
        self.assertEqual(data['alert']['service'], ['Webserver Health'])
        self.assertEqual(data['alert']['text'],
                         'CPU (agent) for webserver-85 is above the threshold of 1% with a value of 28.5%')

        # closed alert
        response = self.client.post('/webhooks/stackdriver', data=self.stackdriver_closed, headers=self.headers)
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data.decode('utf-8'))
        self.assertEqual(data['alert']['resource'], 'webserver-85')
        self.assertEqual(data['alert']['event'], 'CPU usage')
        self.assertEqual(data['alert']['severity'], 'ok')
        self.assertEqual(data['alert']['service'], ['Webserver Health'])
        self.assertEqual(data['alert']['text'],
                         'CPU (agent) for webserver-85 is above the threshold of 1% with a value of 28.5%')

    def test_grafana_webhook(self):

        # state=alerting
        response = self.client.post('/webhooks/grafana', data=self.grafana_alert_alerting, headers=self.headers)
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data.decode('utf-8'))
        self.assertEqual(data['status'], "ok")

        # check tags with dots are replaced with underscores ie. 'info.host_id' => 'info_host_id'
        self.assertEqual(data['alert']['attributes']['info_host_id'], 'i-0d0721c7f97545d43')

        alert_id = data['id']

        # state=ok
        response = self.client.post('/webhooks/grafana', data=self.grafana_alert_ok, headers=self.headers)
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data.decode('utf-8'))
        self.assertEqual(data['status'], "ok")

        # get alert
        response = self.client.get('/alert/' + alert_id)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data.decode('utf-8'))
        self.assertIn(alert_id, data['alert']['id'])
        self.assertEqual(data['alert']['status'], 'closed')

    def test_telegram_webhook(self):

        # telegram alert
        response = self.client.post('/alert', data=json.dumps(self.telegram_alert), headers=self.headers)
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data.decode('utf-8'))
        telegram_alert_id = data['id']

        # command=/ack
        response = self.client.post('/webhooks/telegram', data=self.telegram_ack %
                                    telegram_alert_id, headers=self.headers)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data.decode('utf-8'))
        self.assertEqual(data['status'], "ok")

    def test_graylog_webhook(self):
        # graylog alert
        response = self.client.post('/webhooks/graylog', data=self.graylog_notification, headers=self.headers)
        self.assertEqual(response.status_code, 201)

    def test_custom_webhook(self):

        # setup custom webhook
        custom_webhooks.webhooks['json'] = TestJsonWebhook()
        custom_webhooks.webhooks['text'] = TestTextWebhook()
        custom_webhooks.webhooks['form'] = TestFormWebhook()
        custom_webhooks.webhooks['multipart'] = TestMultiPartFormWebhook()

        # test json payload
        response = self.client.post('/webhooks/json?foo=bar', json={'baz': 'quux'}, content_type='application/json')
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data.decode('utf-8'))
        self.assertEqual(data['alert']['resource'], 'bar')
        self.assertEqual(data['alert']['event'], 'quux')

        # test text data
        response = self.client.post('/webhooks/text?foo', data='this is raw data', content_type='text/plain')
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data.decode('utf-8'))
        self.assertEqual(data['alert']['resource'], 'nofoo')
        self.assertEqual(data['alert']['event'], 'this is raw data')

        # test form data
        response = self.client.post('/webhooks/form?foo=1', data='say=Hi&to=Mom',
                                    content_type='application/x-www-form-urlencoded')
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data.decode('utf-8'))
        self.assertEqual(data['alert']['resource'], '1')
        self.assertEqual(data['alert']['event'], 'Say Hi to Mom', response.data)

        # test multipart form data
        form_data1 = dict(
            field1='value1',
            file1=(BytesIO(b'my file contents'), "file1.txt"),
        )
        response = self.client.post('/webhooks/multipart?foo=1', data=form_data1,
                                    content_type='multipart/form-data;boundary="boundary"')
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data.decode('utf-8'))
        self.assertEqual(data['alert']['resource'], '1')
        self.assertEqual(data['alert']['event'], 'value1')


class TestJsonWebhook(WebhookBase):

    def incoming(self, query_string, payload):
        return Alert(
            resource=query_string['foo'],
            event=payload['baz'],
            environment='Production',
            service=['Foo']
        )


class TestTextWebhook(WebhookBase):

    def incoming(self, query_string, payload):
        return Alert(
            resource=query_string.get('foo') or 'nofoo',
            event=payload,
            environment='Production',
            service=['Foo']
        )


class TestFormWebhook(WebhookBase):

    def incoming(self, query_string, payload):
        return Alert(
            resource=query_string['foo'],
            event='Say {} to {}'.format(payload['say'], payload['to']),
            environment='Production',
            service=['Foo']
        )


class TestMultiPartFormWebhook(WebhookBase):

    def incoming(self, query_string, payload):
        return Alert(
            resource=query_string['foo'],
            event=payload['field1'],
            environment='Production',
            service=['Foo']
        )
