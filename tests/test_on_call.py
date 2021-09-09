from datetime import datetime, timedelta
import json
import unittest
import logging


from alerta.app import create_app, db, plugins
from alerta.models.key import ApiKey
from alerta.models.alert import Alert


LOG = logging.getLogger("test.test_notification_rule")


def get_id(object: dict):
    return object["id"]


class OnCallTestCase(unittest.TestCase):
    def setUp(self) -> None:
        test_config = {
            "TESTING": True,
            "AUTH_REQUIRED": True,
            "CUSTOMER_VIEWS": True,
            "PLUGINS": [],
        }
        self.app = create_app(test_config)
        self.client = self.app.test_client()

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

    def test_on_calls(self):

        on_call = {
            "userIds": ["test"],
            "startDate": datetime.now().strftime("%Y-%m-%d"),
            "endDate": datetime.now().strftime("%Y-%m-%d"),
        }

        data = self.create_api_obj("/oncalls", on_call, self.headers)
        on_call_id = data["id"]

        # new alert should list on_calls
        data = self.create_api_obj("/alert", self.prod_alert, self.headers)
        active_oncalls = self.create_api_obj("/oncalls/active", data["alert"], self.headers, 200)["onCalls"]
        self.assertIn(
            on_call_id,
            map(get_id, active_oncalls),
        )

        # duplicate alert should not activate notification_rule
        data = self.create_api_obj("/alert", self.prod_alert, self.headers)
        active_oncalls = self.create_api_obj("/oncalls/active", data["alert"], self.headers, 200)["onCalls"]
        self.assertIn(
            on_call_id,
            map(get_id, active_oncalls),
        )

        # duplicate alert should not activate notification_rule (again)
        data = self.create_api_obj("/alert", self.prod_alert, self.headers)
        active_oncalls = self.create_api_obj("/oncalls/active", data["alert"], self.headers, 200)["onCalls"]
        self.assertIn(
            on_call_id,
            map(get_id, active_oncalls),
        )

        # increase severity alert should activate notification_rule
        self.prod_alert["severity"] = "major"
        data = self.create_api_obj("/alert", self.prod_alert, self.headers)
        active_oncalls = self.create_api_obj("/oncalls/active", data["alert"], self.headers, 200)["onCalls"]
        self.assertIn(
            on_call_id,
            map(get_id, active_oncalls),
        )

        # increase severity alert should activate notification_rule (again)
        self.prod_alert["severity"] = "critical"
        data = self.create_api_obj("/alert", self.prod_alert, self.headers)
        active_oncalls = self.create_api_obj("/oncalls/active", data["alert"], self.headers, 200)["onCalls"]
        self.assertIn(
            on_call_id,
            map(get_id, active_oncalls),
        )

        # decrease severity alert should activate notification_rule
        self.prod_alert["severity"] = "minor"
        data = self.create_api_obj("/alert", self.prod_alert, self.headers)
        active_oncalls = self.create_api_obj("/oncalls/active", data["alert"], self.headers, 200)["onCalls"]
        self.assertIn(
            on_call_id,
            map(get_id, active_oncalls),
        )

        # decrease severity alert should activate notification_rule (again)
        self.prod_alert["severity"] = "warning"
        data = self.create_api_obj("/alert", self.prod_alert, self.headers)
        active_oncalls = self.create_api_obj("/oncalls/active", data["alert"], self.headers, 200)["onCalls"]
        self.assertIn(
            on_call_id,
            map(get_id, active_oncalls),
        )

        self.delete_api_obj("/oncalls/" + on_call_id, self.headers)

    def test_edit_on_call(self):

        self.create_api_obj("/alert", self.prod_alert, self.headers)
        now = datetime.now()
        on_call = {
            "userIds": ["test"],
            "startDate": now.date().isoformat(),
            "endDate": now.date().isoformat(),
            "repeatType": "list",
            "repeatDays": [now.strftime("%a")],
            "repeatMonths": [now.strftime("%b")]
        }

        on_call_data = self.create_api_obj("/oncalls", on_call, self.headers)
        on_call_id = on_call_data["id"]

        data = self.get_api_obj("/oncalls", self.headers)
        data = self.create_api_obj("/alert", self.prod_alert, self.headers)
        active_oncalls = self.create_api_obj("/oncalls/active", data["alert"], self.headers, 200)["onCalls"]
        self.assertIn(
            on_call_id,
            map(get_id, active_oncalls),
        )
        now_1 = datetime(now.year, now.month, now.day + 1)
        update = {
            "userIds": ["test_2"],
            "endDate": now_1.date().isoformat(),
            "endTime": "22:00",
            "repeatType": None
        }
        data = self.update_api_obj("/oncalls/" + on_call_id, update, self.headers)
        self.assertEqual(data["status"], "ok")

        data = self.get_api_obj("/oncalls/" + on_call_id, self.headers)
        self.assertEqual(data["onCall"]["userIds"], ["test_2"])
        self.assertEqual(data["onCall"]["startDate"], now.date().isoformat())
        self.assertEqual(data["onCall"]["endDate"], now_1.date().isoformat())
        self.assertEqual(data["onCall"]["startTime"], None)
        self.assertEqual(data["onCall"]["endTime"], "22:00")
        self.assertEqual(data["onCall"]["repeatType"], None)

        data = self.create_api_obj("/alert", self.dev_alert, self.headers)
        active_oncalls = self.create_api_obj("/oncalls/active", data["alert"], self.headers, 200)["onCalls"]
        self.assertIn(
            on_call_id,
            map(get_id, active_oncalls),
        )

        self.delete_api_obj("/oncalls/" + on_call_id, self.headers)

    def test_on_call_dates(self):
        now = datetime.now()
        now_minus_fail = datetime(now.year, now.month, now.day - 1)
        now_plus_fail = datetime(now.year, now.month, now.day + 1)
        on_call = {
            "userIds": ["test"],
            "startDate": now.date().isoformat(),
            "endDate": now.date().isoformat(),
        }

        range_update = {
            "startDate": now_minus_fail.date().isoformat(),
            "endDate": now_plus_fail.date().isoformat(),
        }

        minus_update = {
            "startDate": now_minus_fail.date().isoformat(),
            "endDate": now_minus_fail.date().isoformat(),
        }

        plus_update = {
            "startDate": now_plus_fail.date().isoformat(),
            "endDate": now_plus_fail.date().isoformat(),
        }

        data = self.create_api_obj("/oncalls", on_call, self.headers)
        on_call_id = data["id"]

        data = self.create_api_obj("/alert", self.prod_alert, self.headers)
        active_oncalls = self.create_api_obj("/oncalls/active", data["alert"], self.headers, 200)["onCalls"]
        self.assertIn(
            on_call_id,
            map(get_id, active_oncalls),
        )

        data = self.update_api_obj("/oncalls/" + on_call_id, range_update, self.headers)
        data = self.create_api_obj("/alert", self.prod_alert, self.headers)
        active_oncalls = self.create_api_obj("/oncalls/active", data["alert"], self.headers, 200)["onCalls"]
        self.assertIn(
            on_call_id,
            map(get_id, active_oncalls),
        )

        data = self.update_api_obj("/oncalls/" + on_call_id, minus_update, self.headers)
        data = self.create_api_obj("/alert", self.prod_alert, self.headers)
        active_oncalls = self.create_api_obj("/oncalls/active", data["alert"], self.headers, 200)["onCalls"]
        self.assertNotIn(
            on_call_id,
            map(get_id, active_oncalls),
        )

        data = self.update_api_obj("/oncalls/" + on_call_id, plus_update, self.headers)
        data = self.create_api_obj("/alert", self.prod_alert, self.headers)
        active_oncalls = self.create_api_obj("/oncalls/active", data["alert"], self.headers, 200)["onCalls"]
        self.assertNotIn(
            on_call_id,
            map(get_id, active_oncalls),
        )

    def test_on_call_repeat(self):
        now = datetime.now()
        now_minus_fail = datetime(now.year, now.month - 1, now.day - 1)
        now_plus_fail = datetime(now.year, now.month + 1, now.day + 1)
        now_week = now.isocalendar()[1]
        now_minus_fail_week = now_week - 1
        now_plus_fail_week = now_week + 1
        on_call = {
            "userIds": ["test"],
            "repeatType": "list",
            "repeatDays": None,
            "repeatWeeks": None,
            "repeatMonths": None,
        }

        repeat_update = {
            "repeatDays": [now_minus_fail.strftime("%a"), now.strftime("%a"), now_plus_fail.strftime("%a")],
            "repeatWeeks": [now_minus_fail_week, now_week, now_plus_fail_week],
            "repeatMonths": [now_minus_fail.strftime("%b"), now.strftime("%b"), now_plus_fail.strftime("%b")],
        }

        day_fail = {**repeat_update, "repeatDays": [now_minus_fail.strftime("%a"), now_plus_fail.strftime("%a")]}
        week_fail = {**repeat_update, "repeatWeeks": [now_minus_fail_week, now_plus_fail_week]}
        month_fail = {**repeat_update, "repeatMonths": [now_minus_fail.strftime("%b"), now_plus_fail.strftime("%b")]}

        data = self.create_api_obj("/oncalls", on_call, self.headers)
        on_call_id = data["id"]

        data = self.create_api_obj("/alert", self.prod_alert, self.headers)
        active_oncalls = self.create_api_obj("/oncalls/active", data["alert"], self.headers, 200)["onCalls"]
        self.assertIn(
            on_call_id,
            map(get_id, active_oncalls),
        )

        data = self.update_api_obj("/oncalls/" + on_call_id, repeat_update, self.headers)
        data = self.create_api_obj("/alert", self.prod_alert, self.headers)
        active_oncalls = self.create_api_obj("/oncalls/active", data["alert"], self.headers, 200)["onCalls"]
        self.assertIn(
            on_call_id,
            map(get_id, active_oncalls),
        )

        data = self.update_api_obj("/oncalls/" + on_call_id, day_fail, self.headers)
        data = self.create_api_obj("/alert", self.prod_alert, self.headers)
        active_oncalls = self.create_api_obj("/oncalls/active", data["alert"], self.headers, 200)["onCalls"]
        self.assertNotIn(
            on_call_id,
            map(get_id, active_oncalls),
        )

        data = self.update_api_obj("/oncalls/" + on_call_id, week_fail, self.headers)
        data = self.create_api_obj("/alert", self.prod_alert, self.headers)
        active_oncalls = self.create_api_obj("/oncalls/active", data["alert"], self.headers, 200)["onCalls"]
        self.assertNotIn(
            on_call_id,
            map(get_id, active_oncalls),
        )

        data = self.update_api_obj("/oncalls/" + on_call_id, month_fail, self.headers)
        data = self.create_api_obj("/alert", self.prod_alert, self.headers)
        active_oncalls = self.create_api_obj("/oncalls/active", data["alert"], self.headers, 200)["onCalls"]
        self.assertNotIn(
            on_call_id,
            map(get_id, active_oncalls),
        )

    def test_delete_on_call(self):
        now = datetime.now()
        on_call = {
            "userIds": ["test"],
            "startDate": now.date().isoformat(),
            "endDate": now.date().isoformat(),
        }

        on_call_data = self.create_api_obj("/oncalls", on_call, self.headers)
        on_call_id = on_call_data["id"]

        on_call_check = self.get_api_obj("/oncalls/" + on_call_id, self.headers)
        self.assertEqual(on_call_check["onCall"]["id"], on_call_id)

        self.delete_api_obj("/oncalls/" + on_call_id, self.headers)
        self.get_api_obj("/oncalls/" + on_call_id, self.headers, 404)
        self.delete_api_obj("/oncalls/" + on_call_id, self.headers, 404)

    def test_user_info(self):
        now = datetime.now()
        on_call = {
            "userIds": ["test"],
            "startDate": now.date().isoformat(),
            "endDate": now.date().isoformat(),
        }

        data = self.create_api_obj("/oncalls", on_call, self.headers)
        self.assertEqual(data["onCall"]["user"], "admin@alerta.io")
        self.delete_api_obj("/oncalls/" + data["id"], self.headers)

    def test_status_codes(self):
        now = datetime.now()
        on_call = {
            "userIds": ["test"],
            "startDate": now.date().isoformat(),
            "endDate": now.date().isoformat(),
        }

        faulty_on_call = {
            "startDate": now.date().isoformat(),
            "endDate": now.date().isoformat(),
        }

        data = self.get_api_obj("/oncalls", self.headers)
        self.assertEqual(data["onCalls"], [])

        data = self.create_api_obj("/oncalls", on_call, self.headers)
        on_call_id = data["id"]
        on_call_data = data["onCall"]

        data = self.create_api_obj("/oncalls", faulty_on_call, self.headers, 400)
        self.assertEqual(data["status"], "error")

        data = self.get_api_obj("/oncalls/" + on_call_id, self.headers)
        self.assertEqual(data["status"], "ok")
        self.assertEqual(on_call_data, data["onCall"])
        on_call_data = data["onCall"]

        data = self.get_api_obj("/oncalls", self.headers)
        self.assertIn(on_call_data, data["onCalls"])

        data = self.get_api_obj("/oncalls/" + "test", self.headers, 404)
        self.assertEqual(data["message"], "not found")

        data = self.update_api_obj("/oncalls/" + on_call_id, {}, self.headers, 400)
        self.assertEqual(data["message"], "nothing to change")
        data = self.update_api_obj(
            "/oncalls/" + "test",
            {"environment": "Development"},
            self.headers,
            404,
        )
        self.assertEqual(data["message"], "not found")

        self.delete_api_obj("/oncalls/" + on_call_id, self.headers)
