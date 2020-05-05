import json
import unittest

from werkzeug.datastructures import MultiDict

from alerta.app import create_app, qb

# service, tags (=, !=, =~, !=~)
# attributes (=, !=, =~, !=~)
# everything else (=, !=, =~, !=~)


class SearchTestCase(unittest.TestCase):

    def setUp(self):
        self.app = create_app()

    def test_equal_to(self):

        search_params = MultiDict([('status', 'open'), ('environment', 'Production')])

        with self.app.test_request_context():
            query = qb.from_params(search_params)  # noqa # FIXME

        # self.assertEqual(query.where, 'foo')
        # self.assertEqual(query.sort, 'foo')
        # self.assertEqual(query.group, 'foo')

    def test_attributes(self):

        search_params = MultiDict([('attributes.country_code', 'US')])
        with self.app.test_request_context():
            query = qb.from_params(search_params)

        if self.app.config['DATABASE_URL'].startswith('postgres'):
            self.assertIn('AND attributes @> %(attr_country_code)s', query.where)
            self.assertEqual(query.vars, {'attr_country_code': {'country_code': 'US'}})
        else:
            self.assertEqual(query.where, {'attributes.country_code': 'US'})

    # def test_from_dict(self):
    #
    #     self.qb.from_dict()


class QueryParserTestCase(unittest.TestCase):

    def setUp(self):

        test_config = {
            'TESTING': True,
            'AUTH_REQUIRED': False,
            'ALERT_TIMEOUT': 120,
            'HISTORY_LIMIT': 5,
            'DEBUG': True,
            # 'PLUGINS': ['logstash']
        }
        self.app = create_app(test_config)
        self.client = self.app.test_client()

        alerts = [
            {
                'resource': 'net01',
                'event': 'node_marginal',
                'environment': 'Production',
                'severity': 'major',
                'correlate': ['node_down', 'node_marginal', 'node_up'],
                'status': 'open',
                'service': ['Network', 'Core'],
                'group': 'Network',
                'value': 'johno',
                'text': 'panic: this is a foo alert',
                'tags': ['aaa', 'bbb', 'ccc'],
                'attributes': {'region': 'EMEA'},
                'origin': 'alpha',
                'timeout': 100,
                'rawData': ''
            },
            {
                'resource': 'network02',
                'event': 'node_down',
                'environment': 'Production',
                'severity': 'major',
                'correlate': ['node_down', 'node_marginal', 'node_up'],
                'status': 'ack',
                'service': ['Network', 'Core', 'Shared'],
                'group': 'Network',
                'value': 'jonathon',
                'text': 'Kernel Panic: this is a bar test alert',
                'tags': ['bbb', 'ccc', 'ddd'],
                'attributes': {'region': 'LATAM'},
                'origin': 'bravo',
                'timeout': 200,
                'rawData': ''
            },
            {
                'resource': 'netwrk03',
                'event': 'node_up',
                'environment': 'Production',
                'severity': 'normal',
                'correlate': ['node_down', 'node_marginal', 'node_up'],
                'status': 'closed',
                'service': ['Network', 'Shared'],
                'group': 'Netperf',
                'value': 'jonathan',
                'text': 'kernel panic: this is a foo bar text alert',
                'tags': ['ccc', 'ddd', 'eee'],
                'attributes': {'region': 'APAC'},
                'origin': 'charlie',
                'timeout': 300,
                'rawData': ''
            },
            {
                'resource': 'network4',
                'event': 'node_up',
                'environment': 'Production',
                'severity': 'ok',
                'correlate': ['node_down', 'node_marginal', 'node_up'],
                'status': 'closed',
                'service': ['Core', 'Shared'],
                'group': 'Performance',
                'value': 'john',
                'text': 'kernel panick: this is a fu bar baz quux tests alert (i have a boat)',
                'tags': ['ddd', 'eee', 'aaa'],
                'attributes': {'region': 'EMEA'},
                'origin': 'delta',
                'timeout': 400,
                'rawData': ''
            },
            {
                'resource': 'net5',
                'event': 'node_down',
                'environment': 'Production',
                'severity': 'critical',
                'correlate': ['node_down', 'node_marginal', 'node_up'],
                'status': 'shelved',
                'service': ['Network', 'Core', 'Shared'],
                'group': 'Network',
                'value': 'jon',
                'text': 'don\'t panic: this is a foo bar baz quux tester alert (i have a moat)',
                'tags': ['eee', 'aaa', 'bbb'],
                'attributes': {},
                'origin': 'zulu',
                'timeout': 500,
                'rawData': ''
            },
        ]

        for alert in alerts:
            response = self.client.post('/alert', json=alert, content_type='application/json')
            self.assertEqual(response.status_code, 201)

    def _search(self, q):
        response = self.client.get('/alerts?q={}'.format(q))
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data.decode('utf-8'))
        return data['total']

    def test_single_word_terms(self):
        self.assertEqual(self._search(q='foo'), 3)
        self.assertEqual(self._search(q='bar'), 4)
        self.assertEqual(self._search(q='foo bar'), 5)
        self.assertEqual(self._search(q='foo baz'), 4)
        self.assertEqual(self._search(q='foo quux'), 4)

    def test_phrase_terms(self):
        self.assertEqual(self._search(q='"foo bar"'), 2)
        self.assertEqual(self._search(q='"foo quux"'), 0)
        self.assertEqual(self._search(q='"fu bar baz"'), 1)
        self.assertEqual(self._search(q='"bar baz"'), 2)

    def test_field_names(self):
        self.assertEqual(self._search(q='status:ack'), 1)
        self.assertEqual(self._search(q='severity:major'), 2)
        self.assertEqual(self._search(q='group:(Network OR Performance)'), 4)
        self.assertEqual(self._search(q='group:(Network Performance)'), 4)
        self.assertEqual(self._search(q='text:"kernel panic"'), 2)
        self.assertEqual(self._search(q='_exists_:region'), 4)
        self.assertEqual(self._search(q='service:Shared'), 4)
        self.assertEqual(self._search(q='tags:aaa'), 3)
        self.assertEqual(self._search(q='attributes.region:EMEA'), 2)
        self.assertEqual(self._search(q='_.region:EMEA'), 2)
        self.assertEqual(self._search(q='_.region:(EMEA LATAM)'), 3)

    def test_wildcards(self):
        self.assertEqual(self._search(q='f*'), 4)
        self.assertEqual(self._search(q='f* ba?'), 5)
        self.assertEqual(self._search(q='te?t'), 2)
        self.assertEqual(self._search(q='test*'), 3)

    def test_regex(self):
        self.assertEqual(self._search(q='/[mb]oat/'), 2)
        self.assertEqual(self._search(q='value:/joh?n(ath[oa]n)/'), 2)
        self.assertEqual(self._search(q='resource:/net(wo?rk)?[0-9]/'), 5)
        self.assertEqual(self._search(q='/f(oo|u) ba.?/'), 3)

    def test_ranges(self):
        self.assertEqual(self._search(q='timeout:[100 TO 500]'), 5)
        self.assertEqual(self._search(q='origin:{alpha TO zulu}'), 3)
        self.assertEqual(self._search(q='timeout:{* TO 300}'), 2)
        self.assertEqual(self._search(q='timeout:[500 TO *]'), 1)

        self.assertEqual(self._search(q='timeout:>500'), 0)
        self.assertEqual(self._search(q='timeout:>=500'), 1)
        self.assertEqual(self._search(q='timeout:<500'), 4)
        self.assertEqual(self._search(q='timeout:<=500'), 5)

    def test_boolean_operators(self):
        self.assertEqual(self._search(q='"foo bar" foo'), 3)
        self.assertEqual(self._search(q='"foo bar" OR foo'), 3)
        self.assertEqual(self._search(q='"foo bar" || foo'), 3)

        self.assertEqual(self._search(q='"foo bar" AND "bar baz"'), 1)
        self.assertEqual(self._search(q='"foo bar" %26%26 "bar baz"'), 1)  # URL encode ampersands i.e &=%26

        self.assertEqual(self._search(q='"foo bar" NOT "bar baz"'), 1)
        self.assertEqual(self._search(q='"foo bar" !"bar baz"'), 1)
        self.assertEqual(self._search(q='"foo bar" AND NOT "bar baz"'), 1)
        self.assertEqual(self._search(q='NOT "foo bar"'), 3)

        self.assertEqual(self._search(q='foo resource:net01'), 3)
        self.assertEqual(self._search(q='foo OR resource:net01'), 3)
        self.assertEqual(self._search(q='foo AND resource:net01'), 1)

        self.assertEqual(self._search(q='foo !resource:net01'), 2)
        self.assertEqual(self._search(q='foo NOT resource:net01'), 2)
        self.assertEqual(self._search(q='foo AND !resource:net01'), 2)
        self.assertEqual(self._search(q='foo AND NOT resource:net01'), 2)

    def test_grouping(self):
        self.assertEqual(self._search(q='(foo OR bar) AND baz'), 2)
        self.assertEqual(self._search(q='status:(open OR ack)'), 2)
        self.assertEqual(self._search(q='text:(full text search)'), 1)
