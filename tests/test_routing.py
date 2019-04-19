import json
import unittest

import pkg_resources

from alerta.app import create_app, plugins
from alerta.models.enums import Scope
from alerta.models.key import ApiKey
from alerta.plugins import PluginBase


class RoutingTestCase(unittest.TestCase):

    def setUp(self):

        # create dummy routing rules
        self.dist = pkg_resources.Distribution(__file__, project_name='alerta-routing', version='0.1')
        s = 'rules = tests.test_routing:rules'
        self.entry_point = pkg_resources.EntryPoint.parse(s, dist=self.dist)
        self.dist._ep_map = {'alerta.routing': {'rules': self.entry_point}}
        pkg_resources.working_set.add(self.dist)

        test_config = {
            'TESTING': True,
            'AUTH_REQUIRED': True,
            'CUSTOMER_VIEWS': True,
            'ADMIN_USERS': ['admin@alerta.io'],
            'ALLOWED_EMAIL_DOMAINS': ['alerta.io', 'foo.com', 'bar.com'],
            'PD_API_KEYS': {
                'Tyrell Corporation': 'tc-key',
                'Cyberdyne Systems': 'cs-key',
                'Weyland-Yutani': 'wy-key',
                'Zorin Enterprises': 'ze-key'
            },
            'SLACK_API_KEYS': {
                'Soylent Corporation': 'sc-key',
                'Omni Consumer Products': 'ocp-key',
                # 'Dolmansaxlil Shoe Corporation': 'dsc-key'  # use default key
            },
            'API_KEY': 'default-key'
        }

        self.app = create_app(test_config)
        self.client = self.app.test_client()

        self.tier1_tc_alert = {
            'event': 'foo1',
            'resource': 'foo1',
            'environment': 'Production',
            'service': ['Web'],
            'customer': 'Tyrell Corporation'  # tier 1
        }

        self.tier1_wy_alert = {
            'event': 'foo1',
            'resource': 'foo1',
            'environment': 'Production',
            'service': ['Web'],
            'customer': 'Weyland-Yutani'  # tier 1
        }

        self.tier2_sc_alert = {
            'event': 'bar1',
            'resource': 'bar1',
            'environment': 'Production',
            'service': ['Web'],
            'customer': 'Soylent Corporation'  # tier 2
        }

        self.tier2_ocp_alert = {
            'event': 'bar1',
            'resource': 'bar1',
            'environment': 'Production',
            'service': ['Web'],
            'customer': 'Omni Consumer Products'  # tier 2
        }

        self.tier2_dsc_alert = {
            'event': 'bar1',
            'resource': 'bar1',
            'environment': 'Production',
            'service': ['Web'],
            'customer': 'Dolmansaxlil Shoe Corporation'  # tier 2
        }

        self.tier3_it_alert = {
            'event': 'bar1',
            'resource': 'bar1',
            'environment': 'Production',
            'service': ['Web'],
            'customer': 'Initech'  # tier 3
        }

        with self.app.test_request_context('/'):
            self.app.preprocess_request()
            self.api_key = ApiKey(
                user='admin@alerta.io',
                scopes=[Scope.admin, Scope.read, Scope.write],
                text='admin-key'
            )
            self.api_key.create()

        self.headers = {
            'Authorization': 'Key %s' % self.api_key.key,
            'Content-type': 'application/json'
        }

        # create dummy plugins
        plugins.plugins['pagerduty'] = DummyPagerDutyPlugin()
        plugins.plugins['slack'] = DummySlackPlugin()

    def tearDown(self):
        self.dist._ep_map.clear()

    def test_routing(self):

        # create alert (pagerduty key for Tyrell Corporation)
        response = self.client.post('/alert', data=json.dumps(self.tier1_tc_alert), headers=self.headers)
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data.decode('utf-8'))
        self.assertEqual(data['alert']['attributes']['NOTIFY'], 'pagerduty')
        self.assertEqual(data['alert']['attributes']['API_KEY'], 'tc-key')

        # create alert (pagerduty key for Weyland-Yutani)
        response = self.client.post('/alert', data=json.dumps(self.tier1_wy_alert), headers=self.headers)
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data.decode('utf-8'))
        self.assertEqual(data['alert']['attributes']['NOTIFY'], 'pagerduty')
        self.assertEqual(data['alert']['attributes']['API_KEY'], 'wy-key')

        # create alert (slack key for customer Soylent Corporation)
        response = self.client.post('/alert', data=json.dumps(self.tier2_sc_alert), headers=self.headers)
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data.decode('utf-8'))
        self.assertEqual(data['alert']['attributes']['NOTIFY'], 'slack')
        self.assertEqual(data['alert']['attributes']['API_KEY'], 'sc-key')

        # create alert (slack key for customer Omni Consumer Products)
        response = self.client.post('/alert', data=json.dumps(self.tier2_ocp_alert), headers=self.headers)
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data.decode('utf-8'))
        self.assertEqual(data['alert']['attributes']['NOTIFY'], 'slack')
        self.assertEqual(data['alert']['attributes']['API_KEY'], 'ocp-key')

        # create alert (use default slack key for Dolmansaxlil Shoe Corporation)
        response = self.client.post('/alert', data=json.dumps(self.tier2_dsc_alert), headers=self.headers)
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data.decode('utf-8'))
        self.assertEqual(data['alert']['attributes']['NOTIFY'], 'slack')
        self.assertEqual(data['alert']['attributes']['API_KEY'], 'default-key')

        # create alert (no key)
        response = self.client.post('/alert', data=json.dumps(self.tier3_it_alert), headers=self.headers)
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data.decode('utf-8'))
        self.assertNotIn('NOTIFY', data['alert']['attributes'])
        self.assertNotIn('API_KEY', data['alert']['attributes'])


class DummyPagerDutyPlugin(PluginBase):

    def pre_receive(self, alert, **kwargs):
        return alert

    def post_receive(self, alert, **kwargs):
        config = kwargs.pop('config', {})
        alert.attributes['NOTIFY'] = 'pagerduty'
        alert.attributes['API_KEY'] = config['API_KEY']
        return alert

    def status_change(self, alert, status, text, **kwargs):
        return alert, status, text


class DummySlackPlugin(PluginBase):

    def pre_receive(self, alert, **kwargs):
        return alert

    def post_receive(self, alert, **kwargs):
        config = kwargs.pop('config', {})
        alert.attributes['NOTIFY'] = 'slack'
        alert.attributes['API_KEY'] = config['API_KEY']
        return alert

    def status_change(self, alert, status, text, **kwargs):
        return alert, status, text


def rules(alert, plugins, **kwargs):

    TIER_ONE_CUSTOMERS = [
        'Tyrell Corporation',
        'Cyberdyne Systems',
        'Weyland-Yutani',
        'Zorin Enterprises'
    ]

    TIER_TWO_CUSTOMERS = [
        'Soylent Corporation',
        'Omni Consumer Products',
        'Dolmansaxlil Shoe Corporation'
    ]

    config = kwargs['config']
    if alert.customer in TIER_ONE_CUSTOMERS:
        # Tier 1 customer SLA needs PagerDuty to manage escalation
        return [
            plugins['remote_ip'],
            plugins['reject'],
            plugins['blackout'],
            plugins['pagerduty']
        ], dict(API_KEY=config['PD_API_KEYS'][alert.customer])

    elif alert.customer in TIER_TWO_CUSTOMERS:
        # Tier 2 customers handled via Slack
        return [
            plugins['remote_ip'],
            plugins['reject'],
            plugins['blackout'],
            plugins['slack']
        ], dict(API_KEY=config['SLACK_API_KEYS'][alert.customer])

    else:
        # Tier 3 customers get "best effort"
        return [
            plugins['remote_ip'],
            plugins['reject'],
            plugins['blackout']
        ]
