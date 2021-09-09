from datetime import datetime, timedelta
import json
import unittest
import logging


from alerta.utils.format import DateTime
from alerta.app import create_app, db, plugins
from alerta.models.key import ApiKey


LOG = logging.getLogger("test.test_notification_rule")


def get_id(object: dict):
    return object["id"]


class NotificationRuleTestCase(unittest.TestCase):
    def setUp(self) -> None:
        test_config = {
            "TESTING": True,
            "AUTH_REQUIRED": True,
            "CUSTOMER_VIEWS": True,
            "PLUGINS": [],
        }
        self.app = create_app(test_config)
        self.client = self.app.test_client()

        self.sms_channel = {
            "id": "SMS_Channel",
            "sender": "sender",
            "type": "twilio_sms",
            "apiToken": "api_token",
            "apiSid": "api_sid",
        }

        self.call_channel = {
            "id": "CALL_Channel",
            "sender": "sender",
            "type": "twilio_call",
            "apiToken": "api_token",
            "apiSid": "api_sid",
        }

        self.mail_channel = {
            "id": "MAIL_Channel",
            "sender": "sender",
            "type": "sendgrid",
            "apiToken": "api_token",
        }

        self.prod_alert = {
            "resource": "node404",
            "event": "node_down",
            "environment": "Production",
            "severity": "minor",
            "correlate": ["node_down", "node_marginal", "node_up"],
            "service": ["Core", "Web", "Network"],
            "group": "Network",
            "tags": ["level=20", "switch:off"],
        }

        self.dev_alert = {
            "resource": "node404",
            "event": "node_marginal",
            "environment": "Development",
            "severity": "warning",
            "correlate": ["node_down", "node_marginal", "node_up"],
            "service": ["Core", "Web", "Network"],
            "group": "Network",
            "tags": ["level=20", "switch:off"],
        }

        self.fatal_alert = {
            "event": "node_down",
            "resource": "net01",
            "environment": "Production",
            "service": ["Network"],
            "severity": "critical",
            "correlate": ["node_down", "node_marginal", "node_up"],
            "tags": ["foo"],
            "attributes": {"foo": "abc def", "bar": 1234, "baz": False},
        }
        self.critical_alert = {
            "event": "node_marginal",
            "resource": "net02",
            "environment": "Production",
            "service": ["Network"],
            "severity": "critical",
            "correlate": ["node_down", "node_marginal", "node_up"],
            "timeout": 30,
        }
        self.major_alert = {
            "event": "node_marginal",
            "resource": "net03",
            "environment": "Production",
            "service": ["Network"],
            "severity": "major",
            "correlate": ["node_down", "node_marginal", "node_up"],
            "timeout": 40,
        }
        self.normal_alert = {
            "event": "node_up",
            "resource": "net03",
            "environment": "Production",
            "service": ["Network"],
            "severity": "normal",
            "correlate": ["node_down", "node_marginal", "node_up"],
            "timeout": 100,
        }
        self.minor_alert = {
            "event": "node_marginal",
            "resource": "net04",
            "environment": "Production",
            "service": ["Network"],
            "severity": "minor",
            "correlate": ["node_down", "node_marginal", "node_up"],
            "timeout": 40,
        }
        self.ok_alert = {
            "event": "node_up",
            "resource": "net04",
            "environment": "Production",
            "service": ["Network"],
            "severity": "ok",
            "correlate": ["node_down", "node_marginal", "node_up"],
            "timeout": 100,
        }
        self.warn_alert = {
            "event": "node_marginal",
            "resource": "net05",
            "environment": "Production",
            "service": ["Network"],
            "severity": "warning",
            "correlate": ["node_down", "node_marginal", "node_up"],
            "timeout": 50,
        }

        with self.app.test_request_context("/"):
            self.app.preprocess_request()
            self.admin_api_key = ApiKey(
                user="admin@alerta.io",
                scopes=["admin", "read", "write"],
                text="demo-key",
            )
            self.customer_api_key = ApiKey(
                user="admin@alerta.io",
                scopes=["admin", "read", "write"],
                text="demo-key",
                customer="Foo",
            )
            self.admin_api_key.create()
            self.customer_api_key.create()

        self.headers = {
            "Authorization": f"Key {self.admin_api_key.key}",
            "Content-type": "application/json",
        }

    def tearDown(self) -> None:
        plugins.plugins.clear()
        db.destroy()

    def create_api_obj(self, apiurl: str, apidata: dict, apiheaders: dict, status_code: int = 201) -> dict:
        response = self.client.post(apiurl, data=json.dumps(apidata), headers=apiheaders)
        self.assertEqual(response.status_code, status_code)
        return json.loads(response.data.decode("utf-8"))

    def update_api_obj(self, apiurl: str, apidata: dict, apiheaders: dict, status_code: int = 200) -> dict:
        response = self.client.put(apiurl, data=json.dumps(apidata), headers=apiheaders)
        self.assertEqual(response.status_code, status_code)
        return json.loads(response.data.decode("utf-8"))

    def get_api_obj(self, apiurl: str, apiheaders: dict, status_code: int = 200) -> dict:
        response = self.client.get(apiurl, headers=apiheaders)
        self.assertEqual(response.status_code, status_code)
        return json.loads(response.data.decode("utf-8"))

    def delete_api_obj(self, apiurl: str, apiheaders: dict, status_code: int = 200) -> dict:
        response = self.client.delete(apiurl, headers=apiheaders)
        self.assertEqual(response.status_code, status_code)
        return json.loads(response.data.decode("utf-8"))

    def get_notification_rule_id(self, notification_rule: dict) -> str:
        return notification_rule["id"]

    def test_notification_sms(self):

        notification_rule = {
            "environment": "Production",
            "channelId": "SMS_Channel",
            "service": ["Core"],
            "receivers": [],
        }

        self.channel_id = self.create_api_obj("/notificationchannels", self.sms_channel, self.headers)["id"]
        data = self.create_api_obj("/notificationrules", notification_rule, self.headers)
        notification_rule_id = data["id"]

        # new alert should activate notification_rule
        data = self.create_api_obj("/alert", self.prod_alert, self.headers)
        active_notification_rules = self.create_api_obj("/notificationrules/active", data["alert"], self.headers, 200)["notificationRules"]
        self.assertIn(
            notification_rule_id,
            map(get_id, active_notification_rules),
        )

        # duplicate alert should not activate notification_rule
        data = self.create_api_obj("/alert", self.prod_alert, self.headers)
        active_notification_rules = self.create_api_obj("/notificationrules/active", data["alert"], self.headers, 200)["notificationRules"]
        self.assertNotIn(
            notification_rule_id,
            map(get_id, active_notification_rules),
        )

        # duplicate alert should not activate notification_rule (again)
        data = self.create_api_obj("/alert", self.prod_alert, self.headers)
        active_notification_rules = self.create_api_obj("/notificationrules/active", data["alert"], self.headers, 200)["notificationRules"]
        self.assertNotIn(
            notification_rule_id,
            map(get_id, active_notification_rules),
        )

        # increase severity alert should activate notification_rule
        self.prod_alert["severity"] = "major"
        data = self.create_api_obj("/alert", self.prod_alert, self.headers)
        active_notification_rules = self.create_api_obj("/notificationrules/active", data["alert"], self.headers, 200)["notificationRules"]
        self.assertIn(
            notification_rule_id,
            map(get_id, active_notification_rules),
        )

        # increase severity alert should activate notification_rule (again)
        self.prod_alert["severity"] = "critical"
        data = self.create_api_obj("/alert", self.prod_alert, self.headers)
        active_notification_rules = self.create_api_obj("/notificationrules/active", data["alert"], self.headers, 200)["notificationRules"]
        self.assertIn(
            notification_rule_id,
            map(get_id, active_notification_rules),
        )

        # decrease severity alert should activate notification_rule
        self.prod_alert["severity"] = "minor"
        data = self.create_api_obj("/alert", self.prod_alert, self.headers)
        active_notification_rules = self.create_api_obj("/notificationrules/active", data["alert"], self.headers, 200)["notificationRules"]
        self.assertIn(
            notification_rule_id,
            map(get_id, active_notification_rules),
        )

        # decrease severity alert should activate notification_rule (again)
        self.prod_alert["severity"] = "warning"
        data = self.create_api_obj("/alert", self.prod_alert, self.headers)
        active_notification_rules = self.create_api_obj("/notificationrules/active", data["alert"], self.headers, 200)["notificationRules"]
        self.assertIn(
            notification_rule_id,
            map(get_id, active_notification_rules),
        )

        self.delete_api_obj("/notificationrules/" + notification_rule_id, self.headers)

    def test_edit_notification_rule(self):

        self.create_api_obj("/alert", self.prod_alert, self.headers)

        notification_rule = {
            "environment": "Production",
            "channelId": "SMS_Channel",
            "resource": "node404",
            "service": ["Network", "Web"],
            "receivers": [],
            "startTime": "00:00",
            "endTime": "23:59",
        }

        self.channel_id = self.create_api_obj("/notificationchannels", self.sms_channel, self.headers)["id"]
        notification_rule_data = self.create_api_obj("/notificationrules", notification_rule, self.headers)
        notification_rule_id = notification_rule_data["id"]

        self.prod_alert["severity"] = "minor" if self.prod_alert["severity"] != "minor" else "major"
        data = self.get_api_obj("/notificationrules", self.headers)
        data = self.create_api_obj("/alert", self.prod_alert, self.headers)
        active_notification_rules = self.create_api_obj("/notificationrules/active", data["alert"], self.headers, 200)["notificationRules"]
        self.assertIn(
            notification_rule_id,
            map(get_id, active_notification_rules),
        )

        update = {
            "environment": "Development",
            "event": None,
            "tags": [],
            "endTime": "22:00",
        }
        data = self.update_api_obj("/notificationrules/" + notification_rule_id, update, self.headers)
        self.assertEqual(data["status"], "ok")

        data = self.get_api_obj("/notificationrules/" + notification_rule_id, self.headers)
        self.assertEqual(data["notificationRule"]["environment"], "Development")
        self.assertEqual(data["notificationRule"]["resource"], "node404")
        self.assertEqual(data["notificationRule"]["service"], ["Network", "Web"])
        self.assertEqual(data["notificationRule"]["group"], None)
        self.assertEqual(data["notificationRule"]["startTime"], "00:00")
        self.assertEqual(data["notificationRule"]["endTime"], "22:00")

        data = self.create_api_obj("/alert", self.dev_alert, self.headers)
        active_notification_rules = self.create_api_obj("/notificationrules/active", data["alert"], self.headers, 200)["notificationRules"]
        self.assertIn(
            notification_rule_id,
            map(get_id, active_notification_rules),
        )

        self.delete_api_obj("/notificationrules/" + notification_rule_id, self.headers)

    def test_full_notification_rule(self):
        base_alert = {
            "environment": "Production",
            "resource": "notification_net",
            "event": "notification_down",
            "severity": "minor",
            "service": ["Core", "Web", "Network"],
            "group": "Network",
            "tags": ["notification_test", "network"],
        }

        more_service_alert = {**base_alert, "service": ["Core", "Web", "Network", "More"]}
        less_service_alert = {**base_alert, "service": ["Core", "Web"]}
        none_service_alert = {**base_alert, "service": []}
        pop_service_alert = {**base_alert}
        pop_service_alert.pop("service")

        more_tags_alert = {**base_alert, "tags": ["notification_test", "network", "more"]}
        less_tags_alert = {**base_alert, "tags": ["notification_test"]}
        none_tags_alert = {**base_alert, "tags": []}
        pop_tags_alert = {**base_alert}
        pop_tags_alert.pop("tags")

        wrong_resource_alert = {**base_alert, "resource": "wrong"}
        none_resource_alert = {**base_alert, "resource": None}
        pop_resource_alert = {**base_alert}
        pop_resource_alert.pop("resource")

        wrong_event_alert = {**base_alert, "event": "wrong"}
        none_event_alert = {**base_alert, "event": None}
        pop_event_alert = {**base_alert}
        pop_event_alert.pop("event")

        wrong_environment_alert = {**base_alert, "environment": "wrong"}
        none_environment_alert = {**base_alert, "environment": None}
        pop_environment_alert = {**base_alert}
        pop_environment_alert.pop("environment")

        wrong_severity_alert = {**base_alert, "severity": "critical"}
        none_severity_alert = {**base_alert, "severity": None}
        pop_severity_alert = {**base_alert}
        pop_severity_alert.pop("severity")

        wrong_group_alert = {**base_alert, "group": "wrong"}
        none_group_alert = {**base_alert, "group": None}
        pop_group_alert = {**base_alert}
        pop_group_alert.pop("group")

        self.assertNotEqual(wrong_group_alert["group"], base_alert["group"])

        notification_rule = {
            "channelId": "SMS_Channel",
            "receivers": [],
            "environment": "Production",
            "resource": "notification_net",
            "event": "notification_down",
            "severity": ["major", "minor"],
            "service": ["Core", "Web", "Network"],
            "days": ["Mon", "Tue", "Wed", "Thu", "Fri"],
            "group": "Network",
            "tags": ["notification_test", "network"],
            "startTime": "00:00",
            "endTime": "23:59",
            "text": "Hey, this is a test of notification rules",
        }
        self.channel_id = self.create_api_obj("/notificationchannels", self.sms_channel, self.headers)["id"]
        notification_rule_data = self.create_api_obj("/notificationrules", notification_rule, self.headers)

        data = self.create_api_obj("/alert", base_alert, self.headers)
        active_notification_rules = self.create_api_obj("/notificationrules/active", data["alert"], self.headers, 200)["notificationRules"]
        self.assertIn(
            notification_rule_data["notificationRule"],
            active_notification_rules,
        )

        more_data = self.create_api_obj("/alert", more_service_alert, self.headers)
        less_data = self.create_api_obj("/alert", less_service_alert, self.headers)
        none_data = self.create_api_obj("/alert", none_service_alert, self.headers)
        pop_data = self.create_api_obj("/alert", pop_service_alert, self.headers)
        more_active_notification_rules = self.create_api_obj("/notificationrules/active", more_data["alert"], self.headers, 200)["notificationRules"]
        less_active_notification_rules = self.create_api_obj("/notificationrules/active", less_data["alert"], self.headers, 200)["notificationRules"]
        none_active_notification_rules = self.create_api_obj("/notificationrules/active", none_data["alert"], self.headers, 200)["notificationRules"]
        pop_active_notification_rules = self.create_api_obj("/notificationrules/active", pop_data["alert"], self.headers, 200)["notificationRules"]

        self.assertNotIn(notification_rule_data["notificationRule"], more_active_notification_rules)
        self.assertNotIn(notification_rule_data["notificationRule"], less_active_notification_rules)
        self.assertNotIn(notification_rule_data["notificationRule"], none_active_notification_rules)
        self.assertNotIn(notification_rule_data["notificationRule"], pop_active_notification_rules)

        more_data = self.create_api_obj("/alert", more_tags_alert, self.headers)
        less_data = self.create_api_obj("/alert", less_tags_alert, self.headers)
        none_data = self.create_api_obj("/alert", none_tags_alert, self.headers)
        pop_data = self.create_api_obj("/alert", pop_tags_alert, self.headers)
        more_active_notification_rules = self.create_api_obj("/notificationrules/active", more_data["alert"], self.headers, 200)["notificationRules"]
        less_active_notification_rules = self.create_api_obj("/notificationrules/active", less_data["alert"], self.headers, 200)["notificationRules"]
        none_active_notification_rules = self.create_api_obj("/notificationrules/active", none_data["alert"], self.headers, 200)["notificationRules"]
        pop_active_notification_rules = self.create_api_obj("/notificationrules/active", pop_data["alert"], self.headers, 200)["notificationRules"]

        self.assertNotIn(notification_rule_data["notificationRule"], more_active_notification_rules)
        self.assertNotIn(notification_rule_data["notificationRule"], less_active_notification_rules)
        self.assertNotIn(notification_rule_data["notificationRule"], none_active_notification_rules)
        self.assertNotIn(notification_rule_data["notificationRule"], pop_active_notification_rules)

        wrong_data = self.create_api_obj("/alert", wrong_resource_alert, self.headers)
        none_data = self.create_api_obj("/alert", none_resource_alert, self.headers, 400)
        pop_data = self.create_api_obj("/alert", pop_resource_alert, self.headers, 400)
        wrong_active_notification_rules = self.create_api_obj("/notificationrules/active", wrong_data["alert"], self.headers, 200)["notificationRules"]

        self.assertNotIn(notification_rule_data["notificationRule"], wrong_active_notification_rules)

        wrong_data = self.create_api_obj("/alert", wrong_event_alert, self.headers)
        none_data = self.create_api_obj("/alert", none_event_alert, self.headers, 400)
        pop_data = self.create_api_obj("/alert", pop_event_alert, self.headers, 400)
        wrong_active_notification_rules = self.create_api_obj("/notificationrules/active", wrong_data["alert"], self.headers, 200)["notificationRules"]

        self.assertNotIn(notification_rule_data["notificationRule"], wrong_active_notification_rules)

        wrong_data = self.create_api_obj("/alert", wrong_environment_alert, self.headers)
        none_data = self.create_api_obj("/alert", none_environment_alert, self.headers)
        pop_data = self.create_api_obj("/alert", pop_environment_alert, self.headers)
        wrong_active_notification_rules = self.create_api_obj("/notificationrules/active", wrong_data["alert"], self.headers, 200)["notificationRules"]
        none_active_notification_rules = self.create_api_obj("/notificationrules/active", none_data["alert"], self.headers, 200)["notificationRules"]
        pop_active_notification_rules = self.create_api_obj("/notificationrules/active", pop_data["alert"], self.headers, 200)["notificationRules"]

        self.assertNotIn(notification_rule_data["notificationRule"], wrong_active_notification_rules)
        self.assertNotIn(notification_rule_data["notificationRule"], none_active_notification_rules)
        self.assertNotIn(notification_rule_data["notificationRule"], pop_active_notification_rules)

        wrong_data = self.create_api_obj("/alert", wrong_severity_alert, self.headers)
        none_data = self.create_api_obj("/alert", none_severity_alert, self.headers)
        pop_data = self.create_api_obj("/alert", pop_severity_alert, self.headers)
        wrong_active_notification_rules = self.create_api_obj("/notificationrules/active", wrong_data["alert"], self.headers, 200)["notificationRules"]
        none_active_notification_rules = self.create_api_obj("/notificationrules/active", none_data["alert"], self.headers, 200)["notificationRules"]
        pop_active_notification_rules = self.create_api_obj("/notificationrules/active", pop_data["alert"], self.headers, 200)["notificationRules"]

        self.assertNotIn(notification_rule_data["notificationRule"], wrong_active_notification_rules)
        self.assertNotIn(notification_rule_data["notificationRule"], none_active_notification_rules)
        self.assertNotIn(notification_rule_data["notificationRule"], pop_active_notification_rules)

        data = self.delete_api_obj(f"/alert/{data['id']}", self.headers)
        wrong_data = self.create_api_obj("/alert", wrong_group_alert, self.headers)
        none_data = self.create_api_obj("/alert", none_group_alert, self.headers)
        pop_data = self.create_api_obj("/alert", pop_group_alert, self.headers)
        wrong_active_notification_rules = self.create_api_obj("/notificationrules/active", wrong_data["alert"], self.headers, 200)["notificationRules"]
        none_active_notification_rules = self.create_api_obj("/notificationrules/active", none_data["alert"], self.headers, 200)["notificationRules"]
        pop_active_notification_rules = self.create_api_obj("/notificationrules/active", pop_data["alert"], self.headers, 200)["notificationRules"]

        self.assertNotIn(notification_rule_data["notificationRule"], wrong_active_notification_rules)
        self.assertNotIn(notification_rule_data["notificationRule"], none_active_notification_rules)
        self.assertNotIn(notification_rule_data["notificationRule"], pop_active_notification_rules)

    def test_full_alert(self):
        now_time = datetime.now()
        diff_time = timedelta(hours=2)
        diff_start_time = now_time + diff_time
        diff_end_time = now_time - diff_time
        alert = {
            "environment": "Development",
            "resource": "notification_resource",
            "event": "notification_event",
            "severity": "major",
            "service": ["Core", "Web", "Network", "Notification_service"],
            "group": "Network",
            "tags": ["notification_test", "network"],
            "text": "No Descrition",
            "value": "notification_value",
            "origin": "notification_origin",
            "type": "notification_type",
            "timeout": 0,
        }

        base_rule = {
            "channelId": "SMS_Channel",
            "receivers": [],
            "environment": "Development",
            "resource": "notification_resource",
            "event": "notification_event",
            "severity": ["major", "minor"],
            "service": ["Core", "Web", "Network", "Notification_service"],
            "days": ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
            "group": "Network",
            "tags": ["notification_test", "network"],
            "startTime": "00:00",
            "endTime": "23:59",
            "text": "Hey, this is a test of notification rules",
        }

        wrong_environment_rule = {**base_rule, "environment": "wrong"}
        none_environment_rule = {**base_rule, "environment": None}
        pop_environment_rule = {**base_rule}
        pop_environment_rule.pop("environment")

        wrong_resource_rule = {**base_rule, "resource": "wrong"}
        none_resource_rule = {**base_rule, "resource": None}
        pop_resource_rule = {**base_rule}
        pop_resource_rule.pop("resource")

        wrong_event_rule = {**base_rule, "event": "wrong"}
        none_event_rule = {**base_rule, "event": None}
        pop_event_rule = {**base_rule}
        pop_event_rule.pop("event")

        more_severity_rule = {**base_rule, "severity": ["major", "minor", "critical"]}
        wrong_severity_rule = {**base_rule, "severity": ["minor"]}
        none_severity_rule = {**base_rule, "severity": []}
        pop_severity_rule = {**base_rule}
        pop_severity_rule.pop("severity")

        more_service_rule = {**base_rule, "service": ["Core", "Web", "Network", "Notification_service", "More"]}
        less_service_rule = {**base_rule, "service": ["Core", "Web", "Network"]}
        none_service_rule = {**base_rule, "service": []}
        pop_service_rule = {**base_rule}
        pop_service_rule.pop("service")

        days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        days.pop(now_time.weekday())
        wrong_days_rule = {**base_rule, "days": days}
        none_days_rule = {**base_rule, "days": None}
        pop_days_rule = {**base_rule}
        pop_days_rule.pop("days")

        wrong_group_rule = {**base_rule, "group": "wrong"}
        none_group_rule = {**base_rule, "group": None}
        pop_group_rule = {**base_rule}
        pop_group_rule.pop("group")

        more_tags_rule = {**base_rule, "tags": ["notification_test", "network", "More"]}
        less_tags_rule = {**base_rule, "tags": ["notification_test"]}
        none_tags_rule = {**base_rule, "tags": []}
        pop_tags_rule = {**base_rule}
        pop_tags_rule.pop("tags")

        wrong_startTime_rule = {**base_rule, "startTime": datetime.strftime(diff_start_time, "%H:%M")}
        none_startTime_rule = {**base_rule, "startTime": None}
        pop_startTime_rule = {**base_rule}
        pop_startTime_rule.pop("startTime")

        wrong_endTime_rule = {**base_rule, "endTime": datetime.strftime(diff_end_time, "%H:%M")}
        none_endTime_rule = {**base_rule, "endTime": None}
        pop_endTime_rule = {**base_rule}
        pop_endTime_rule.pop("endTime")

        self.channel_id = self.create_api_obj("/notificationchannels", self.sms_channel, self.headers)["id"]
        base_rule_data = self.create_api_obj("/notificationrules", base_rule, self.headers)["notificationRule"]

        wrong_environment_rule_data = self.create_api_obj("/notificationrules", wrong_environment_rule, self.headers)[
            "notificationRule"
        ]
        none_environment_rule_data = self.create_api_obj(
            "/notificationrules", none_environment_rule, self.headers, 400
        )
        pop_environment_rule_data = self.create_api_obj("/notificationrules", pop_environment_rule, self.headers, 400)

        wrong_resource_rule_data = self.create_api_obj("/notificationrules", wrong_resource_rule, self.headers)[
            "notificationRule"
        ]
        none_resource_rule_data = self.create_api_obj("/notificationrules", none_resource_rule, self.headers)[
            "notificationRule"
        ]
        pop_resource_rule_data = self.create_api_obj("/notificationrules", pop_resource_rule, self.headers)[
            "notificationRule"
        ]

        wrong_event_rule_data = self.create_api_obj("/notificationrules", wrong_event_rule, self.headers)[
            "notificationRule"
        ]
        none_event_rule_data = self.create_api_obj("/notificationrules", none_event_rule, self.headers)[
            "notificationRule"
        ]
        pop_event_rule_data = self.create_api_obj("/notificationrules", pop_event_rule, self.headers)[
            "notificationRule"
        ]

        more_severity_rule_data = self.create_api_obj("/notificationrules", more_severity_rule, self.headers)[
            "notificationRule"
        ]
        wrong_severity_rule_data = self.create_api_obj("/notificationrules", wrong_severity_rule, self.headers)[
            "notificationRule"
        ]
        none_severity_rule_data = self.create_api_obj("/notificationrules", none_severity_rule, self.headers)[
            "notificationRule"
        ]

        more_service_rule_data = self.create_api_obj("/notificationrules", more_service_rule, self.headers)[
            "notificationRule"
        ]
        less_service_rule_data = self.create_api_obj("/notificationrules", less_service_rule, self.headers)[
            "notificationRule"
        ]
        none_service_rule_data = self.create_api_obj("/notificationrules", none_service_rule, self.headers)[
            "notificationRule"
        ]

        wrong_days_rule_data = self.create_api_obj("/notificationrules", wrong_days_rule, self.headers)[
            "notificationRule"
        ]
        none_days_rule_data = self.create_api_obj("/notificationrules", none_days_rule, self.headers)[
            "notificationRule"
        ]
        pop_days_rule_data = self.create_api_obj("/notificationrules", pop_days_rule, self.headers)["notificationRule"]

        wrong_group_rule_data = self.create_api_obj("/notificationrules", wrong_group_rule, self.headers)[
            "notificationRule"
        ]
        none_group_rule_data = self.create_api_obj("/notificationrules", none_group_rule, self.headers)[
            "notificationRule"
        ]
        pop_group_rule_data = self.create_api_obj("/notificationrules", pop_group_rule, self.headers)[
            "notificationRule"
        ]

        more_tags_rule_data = self.create_api_obj("/notificationrules", more_tags_rule, self.headers)[
            "notificationRule"
        ]
        less_tags_rule_data = self.create_api_obj("/notificationrules", less_tags_rule, self.headers)[
            "notificationRule"
        ]
        none_tags_rule_data = self.create_api_obj("/notificationrules", none_tags_rule, self.headers)[
            "notificationRule"
        ]
        pop_tags_rule_data = self.create_api_obj("/notificationrules", pop_tags_rule, self.headers)["notificationRule"]

        wrong_startTime_rule_data = self.create_api_obj("/notificationrules", wrong_startTime_rule, self.headers)[
            "notificationRule"
        ]
        none_startTime_rule_data = self.create_api_obj("/notificationrules", none_startTime_rule, self.headers)[
            "notificationRule"
        ]
        pop_startTime_rule_data = self.create_api_obj("/notificationrules", pop_startTime_rule, self.headers)[
            "notificationRule"
        ]

        wrong_endTime_rule_data = self.create_api_obj("/notificationrules", wrong_endTime_rule, self.headers)[
            "notificationRule"
        ]
        none_endTime_rule_data = self.create_api_obj("/notificationrules", none_endTime_rule, self.headers)[
            "notificationRule"
        ]
        pop_endTime_rule_data = self.create_api_obj("/notificationrules", pop_endTime_rule, self.headers)[
            "notificationRule"
        ]

        data = self.create_api_obj("/alert", alert, self.headers)
        active_notification_rules = self.create_api_obj("/notificationrules/active", data["alert"], self.headers, 200)["notificationRules"]
        notification_rules = active_notification_rules

        self.assertNotIn(wrong_environment_rule_data, notification_rules)
        self.assertNotIn(none_environment_rule_data, notification_rules)
        self.assertNotIn(pop_environment_rule_data, notification_rules)

        self.assertNotIn(wrong_resource_rule_data, notification_rules)
        self.assertIn(none_resource_rule_data, notification_rules)
        self.assertIn(pop_resource_rule_data, notification_rules)

        self.assertNotIn(wrong_event_rule_data, notification_rules)
        self.assertIn(none_event_rule_data, notification_rules)
        self.assertIn(pop_event_rule_data, notification_rules)

        self.assertIn(more_severity_rule_data, notification_rules)
        self.assertNotIn(wrong_severity_rule_data, notification_rules)
        self.assertIn(none_severity_rule_data, notification_rules)

        self.assertNotIn(more_service_rule_data, notification_rules)
        self.assertIn(less_service_rule_data, notification_rules)
        self.assertIn(none_service_rule_data, notification_rules)

        self.assertNotIn(wrong_days_rule_data, notification_rules)
        self.assertIn(none_days_rule_data, notification_rules)
        self.assertIn(pop_days_rule_data, notification_rules)

        self.assertNotIn(wrong_group_rule_data, notification_rules)
        self.assertIn(none_group_rule_data, notification_rules)
        self.assertIn(pop_group_rule_data, notification_rules)

        self.assertNotIn(more_tags_rule_data, notification_rules)
        self.assertIn(less_tags_rule_data, notification_rules)
        self.assertIn(none_tags_rule_data, notification_rules)
        self.assertIn(pop_tags_rule_data, notification_rules)

        self.assertNotIn(wrong_startTime_rule_data, notification_rules)
        self.assertIn(none_startTime_rule_data, notification_rules)
        self.assertIn(pop_startTime_rule_data, notification_rules)

        self.assertNotIn(wrong_endTime_rule_data, notification_rules)
        self.assertIn(none_endTime_rule_data, notification_rules)
        self.assertIn(pop_endTime_rule_data, notification_rules)

    def test_delete_notification_rule(self):

        notification_rule = {
            "environment": "Production",
            "channelId": "SMS_Channel",
            "resource": "node404",
            "service": ["Network", "Web"],
            "receivers": [],
            "startTime": "00:00",
            "endTime": "23:59",
        }

        self.channel_id = self.create_api_obj("/notificationchannels", self.sms_channel, self.headers)["id"]
        notification_data = self.create_api_obj("/notificationrules", notification_rule, self.headers)
        notification_id = notification_data["id"]

        notification_check = self.get_api_obj("/notificationrules/" + notification_id, self.headers)
        self.assertEqual(notification_check["notificationRule"]["id"], notification_id)

        self.delete_api_obj("/notificationrules/" + notification_id, self.headers)
        self.get_api_obj("/notificationrules/" + notification_id, self.headers, 404)
        self.delete_api_obj("/notificationrules/" + notification_id, self.headers, 404)

    def test_user_info(self):

        notification_rule = {
            "environment": "Production",
            "channelId": "SMS_Channel",
            "service": ["Network"],
            "receivers": [],
            "text": "administartively sms",
        }

        self.channel_id = self.create_api_obj("/notificationchannels", self.sms_channel, self.headers)["id"]
        data = self.create_api_obj("/notificationrules", notification_rule, self.headers)
        self.assertEqual(data["notificationRule"]["user"], "admin@alerta.io")
        self.assertIsInstance(DateTime.parse(data["notificationRule"]["createTime"]), datetime)
        self.assertEqual(data["notificationRule"]["text"], "administartively sms")

        self.delete_api_obj("/notificationrules/" + data["id"], self.headers)

    def test_status_codes(self):

        minimal_notification_rule = {
            "environment": "Production",
            "channelId": "SMS_Channel",
            "service": ["Network"],
            "receivers": [],
        }

        faulty_notification_rule = {
            "environment": "Production",
            "channelId": "SMS_Channel",
            "service": ["Network"],
        }

        channel_data = self.create_api_obj("/notificationchannels", self.sms_channel, self.headers)
        data = self.get_api_obj("/notificationchannels", self.headers)
        self.assertIn(channel_data["notificationChannel"], data["notificationChannels"])

        data = self.get_api_obj("/notificationrules", self.headers)
        self.assertEqual(data["notificationRules"], [])

        data = self.create_api_obj("/notificationrules", minimal_notification_rule, self.headers)
        notification_rule_id = data["id"]
        notification_rule = data["notificationRule"]

        data = self.create_api_obj("/notificationrules", faulty_notification_rule, self.headers, 400)
        self.assertEqual(data["status"], "error")

        data = self.get_api_obj("/notificationrules/" + notification_rule_id, self.headers)
        self.assertEqual(data["status"], "ok")
        self.assertEqual(notification_rule, data["notificationRule"])
        notification_rule = data["notificationRule"]

        data = self.get_api_obj("/notificationrules", self.headers)
        self.assertIn(notification_rule, data["notificationRules"])

        data = self.get_api_obj("/notificationrules/" + "test", self.headers, 404)
        self.assertEqual(data["message"], "not found")

        data = self.update_api_obj("/notificationrules/" + notification_rule_id, {}, self.headers, 400)
        self.assertEqual(data["message"], "nothing to change")
        data = self.update_api_obj(
            "/notificationrules/" + "test",
            {"environment": "Development"},
            self.headers,
            404,
        )
        self.assertEqual(data["message"], "not found")

        self.delete_api_obj("/notificationrules/" + notification_rule_id, self.headers)
