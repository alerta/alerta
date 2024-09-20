import json
import unittest
from datetime import datetime

from alerta.app import create_app, db, plugins
from alerta.models.filter import Filter
from alerta.models.key import ApiKey
from alerta.plugins import PluginBase
from alerta.utils.format import DateTime


class FiltersTestCase(unittest.TestCase):

    def setUp(self):
        test_config = {
            'TESTING': True,
            'AUTH_REQUIRED': True,
            'CUSTOMER_VIEWS': True,
            'PLUGINS': []
        }
        self.app = create_app(test_config)
        self.client = self.app.test_client()

        self.prod_alert = {
            'resource': 'the_missing_node',
            'event': 'node_down',
            'environment': 'Production',
            'severity': 'major',
            'correlate': ['node_down', 'node_marginal', 'node_up'],
            'service': ['Core', 'Web', 'Network'],
            'group': 'Network',
            'tags': ['level=99', 'switch:off'],
            'origin': 'skynet'
        }

        with self.app.test_request_context('/'):
            self.app.preprocess_request()
            self.admin_api_key = ApiKey(
                user='admin@alerta.io',
                scopes=['admin', 'read', 'write'],
                text='demo-key'
            )
            self.customer_api_key = ApiKey(
                user='admin@alerta.io',
                scopes=['admin', 'read', 'write'],
                text='demo-key',
                customer='Foo'
            )
            self.admin_api_key.create()
            self.customer_api_key.create()

    def tearDown(self):
        plugins.plugins.clear()
        db.destroy()

    def test_filters_api(self):

        self.headers = {
            'Authorization': f'Key {self.admin_api_key.key}',
            'Content-type': 'application/json'
        }

        # Filter data
        post = {
            'environment': 'Development',
            'type': 'test',
            'attributes': {'strings': 'Mountains and fjords', 'int': 9001}
        }

        # create filter
        response = self.client.post('/filter', data=json.dumps(post), headers=self.headers)
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data.decode('utf-8'))
        filter_id = data['id']

        # list filters
        response = self.client.get('/filters', headers=self.headers)
        self.assertEqual(response.status_code, 200)

        # Update filter
        update = {
            'environment': 'Development',
            'type': 'test',
            'attributes': {'strings': 'Mountains and fjords', 'int': 9001},
            'tags': ['test']
        }
        response = self.client.put('/filter/' + filter_id, data=json.dumps(update), headers=self.headers)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data.decode('utf-8'))
        self.assertEqual(data['status'], 'ok')

        # remove filter
        response = self.client.delete('/filter/' + filter_id, headers=self.headers)
        self.assertEqual(response.status_code, 200)

    def test_filter_filters(self):
        self.headers = {
            'Authorization': f'Key {self.admin_api_key.key}',
            'Content-type': 'application/json'
        }

        # Filter data type 1
        post = {
            'environment': 'Development',
            'type': 'test1',
            'attributes': {'strings': 'Mountains and fjords', 'int': 9001}
        }

        response = self.client.post('/filter', data=json.dumps(post), headers=self.headers)
        self.assertEqual(response.status_code, 201)

        # Filter data type 2
        post = {
            'environment': 'Development',
            'type': 'test2',
            'attributes': {'strings': 'Dare not to sleep', 'int': 6000000}
        }

        response = self.client.post('/filter', data=json.dumps(post), headers=self.headers)
        self.assertEqual(response.status_code, 201)

        response = self.client.get('/filters?q=type:test2', headers=self.headers)
        self.assertEqual(response.status_code, 200)

        data = json.loads(response.data.decode('utf-8'))
        self.assertEqual(data['total'], 1)
        self.assertEqual(data['filters'][0]['type'], 'test2')

    def test_match_type(self):

        self.headers = {
            'Authorization': f'Key {self.admin_api_key.key}',
            'Content-type': 'application/json'
        }

        plugins.plugins['DummyPlugin'] = DummyPlugin()

        filter = {
            'environment': 'Production',
            'resource': 'the_missing_node',
            'service': ['Network', 'Web'],
            'type': 'test',
            'attributes': {'strings': 'Mountains and fjords', 'int': 9001}
        }

        response = self.client.post('/filter', data=json.dumps(filter), headers=self.headers)
        self.assertEqual(response.status_code, 201)

        # create alert
        response = self.client.post('/alert', data=json.dumps(self.prod_alert), headers=self.headers)
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data.decode('utf-8'))
        alert_id = data['id']

        # check if DummyPlugin match and added tags
        response = self.client.get('/alert/' + alert_id, headers=self.headers)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data.decode('utf-8'))
        self.assertEqual(data['alert']['environment'], 'Production')
        self.assertEqual(data['alert']['resource'], 'the_missing_node')
        self.assertEqual(data['alert']['service'], ['Core', 'Web', 'Network'])
        self.assertEqual(data['alert']['group'], 'Network')
        self.assertEqual(data['alert']['event'], 'node_down')
        self.assertEqual(len(data['alert']['tags']), 3)
        self.assertIn('test', data['alert']['tags'])
        self.assertEqual(data['alert']['origin'], 'skynet')

    def test_edit_filters(self):

        self.headers = {
            'Authorization': f'Key {self.admin_api_key.key}',
            'Content-type': 'application/json'
        }

        filter = {
            'environment': 'Production',
            'type': 'test',
            'attributes': {'strings': 'Mountains and fjords', 'int': 9001},
            'resource': 'node404',
            'service': ['Network', 'Web']
        }

        response = self.client.post('/filter', data=json.dumps(filter), headers=self.headers)
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data.decode('utf-8'))
        filter_id = data['id']

        update = {
            'environment': 'Development',
            'event': None,
            'tags': []
        }

        response = self.client.put('/filter/' + filter_id, data=json.dumps(update), headers=self.headers)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data.decode('utf-8'))
        self.assertEqual(data['status'], 'ok')

        # check updates worked and didn't change anything else
        response = self.client.get('/filter/' + filter_id, headers=self.headers)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data.decode('utf-8'))
        self.assertEqual(data['filter']['environment'], 'Development')
        self.assertEqual(data['filter']['type'], 'test')
        self.assertEqual(data['filter']['attributes'], {'strings': 'Mountains and fjords', 'int': 9001})
        self.assertEqual(data['filter']['resource'], 'node404')
        self.assertEqual(data['filter']['service'], ['Network', 'Web'])
        self.assertEqual(data['filter']['group'], None)
        self.assertEqual(data['filter']['event'], None)
        self.assertEqual(data['filter']['tags'], [])

    def test_edit_attributes(self):

        self.headers = {
            'Authorization': f'Key {self.admin_api_key.key}',
            'Content-type': 'application/json'
        }

        filter = {
            'environment': 'Production',
            'type': 'test',
            'attributes': {'strings': 'Mountains and fjords', 'int': 9001},
        }

        response = self.client.post('/filter', data=json.dumps(filter), headers=self.headers)
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data.decode('utf-8'))
        filter_id = data['id']

        update = {
            'attributes': {'strings': 'No fjords', 'int': 9001},
        }

        response = self.client.put('/filter/' + filter_id, data=json.dumps(update), headers=self.headers)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data.decode('utf-8'))
        self.assertEqual(data['status'], 'ok')

        # check updates worked and didn't change anything else
        response = self.client.get('/filter/' + filter_id, headers=self.headers)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data.decode('utf-8'))
        self.assertEqual(data['filter']['attributes'], {'strings': 'No fjords', 'int': 9001})

    def test_user_info(self):

        self.headers = {
            'Authorization': f'Key {self.admin_api_key.key}',
            'Content-type': 'application/json'
        }

        filter = {
            'environment': 'Production',
            'type': 'test',
            'attributes': {'strings': 'Mountains and fjords', 'int': 9001},
            'resource': 'node404',
            'service': ['Network', 'Web'],
            'text': 'test plugin'
        }

        response = self.client.post('/filter', data=json.dumps(filter), headers=self.headers)
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data.decode('utf-8'))
        self.assertEqual(data['filter']['user'], 'admin@alerta.io')
        self.assertIsInstance(DateTime.parse(data['filter']['createTime']), datetime)
        self.assertEqual(data['filter']['text'], 'test plugin')


class DummyPlugin(PluginBase):

    def pre_receive(self, alert, **kwargs):
        filters = [f.serialize for f in Filter.find_matching_filters(alert, 'test')]
        if filters:
            alert.tags.append('test')
        return alert

    def post_receive(self, alert, **kwargs):
        return alert

    def status_change(self, alert, status, text, **kwargs):
        return
