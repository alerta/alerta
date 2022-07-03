import json
import unittest
from datetime import datetime
from unittest.mock import patch

from werkzeug.datastructures import MultiDict

from alerta.app import create_app, db, qb

# service, tags (=, !=, =~, !=~)
# attributes (=, !=, =~, !=~)
# everything else (=, !=, =~, !=~)


class SearchTestCase(unittest.TestCase):

    def setUp(self):
        self.app = create_app()

    def test_alerts_filter(self):

        self.maxDiff = None

        search_params = MultiDict([
            ('id', '8b4e22b7-58b3-4c7c-9d00-1d50ca412b0e'),
            ('resource', 'res1'),
            ('event', 'event1'),
            ('environment', 'Development'),
            ('severity', 'major'),
            ('correlate', 'event2'),
            ('status', 'closed'),
            ('service', 'Network'),
            ('service', 'Shared'),
            ('group', 'OS'),
            ('value', '100rps'),
            ('text', 'this is text'),
            ('tag', 'tag1'),
            ('tag', 'tag2'),
            ('attributes.foo', 'bar'),
            ('attributes.baz', 'quux'),
            ('origin', 'origin/foo'),
            ('type', 'exceptionAlert'),
            ('createTime', ''),
            ('timeout', '3600'),
            ('rawData', '/Volumes/GoogleDrive'),
            ('customer', 'cust1'),
            ('duplicateCount', '3'),
            ('repeat', 'true'),
            ('previousSeverity', 'warning'),
            ('trendIndication', 'moreSevere'),
            ('receiveTime', ''),
            ('lastReceiveId', '69dbf798-0dad-475a-9375-18d2471ae08b'),
            ('lastReceiveTime', ''),
            ('updateTime', '')
        ])

        try:
            with self.app.test_request_context():
                query = qb.alerts.from_params(search_params)  # noqa
        except Exception as e:
            self.fail(f'Unexpected exception in alerts filter query: {e}')

    def test_alerts_sort_by(self):

        sort_params = MultiDict([
            ('sort-by', 'resource'),
            ('sort-by', 'event'),
            ('sort-by', 'environment'),
            ('sort-by', 'severity'),
            ('sort-by', 'correlate'),
            ('sort-by', 'status'),
            ('sort-by', 'service'),
            ('sort-by', 'service'),
            ('sort-by', 'group'),
            ('sort-by', 'value'),
            ('sort-by', 'text'),
            ('sort-by', 'tags'),
            ('sort-by', 'attributes.foo'),
            ('sort-by', 'attributes.bar'),
            ('sort-by', 'origin'),
            ('sort-by', 'type'),
            ('sort-by', 'createTime'),
            ('sort-by', 'timeout'),
            ('sort-by', 'rawData'),
            ('sort-by', 'customer'),
            ('sort-by', 'duplicateCount'),
            ('sort-by', 'repeat'),
            ('sort-by', 'previousSeverity'),
            ('sort-by', 'trendIndication'),
            ('sort-by', 'receiveTime'),
            ('sort-by', 'lastReceiveId'),
            ('sort-by', 'lastReceiveTime'),
            ('sort-by', 'updateTime')
        ])

        try:
            with self.app.test_request_context():
                query = qb.alerts.from_params(sort_params)  # noqa
        except Exception as e:
            self.fail(f'Unexpected exception in alerts sort-by query: {e}')

    def test_alerts_query(self):

        self.maxDiff = None

        search_params = MultiDict([
            ('status', 'open'),
            ('status', 'ack'),
            ('environment', '~DEV'),
            ('group!', 'Network'),
            ('sort-by', '-severity'),
            ('sort-by', '-lastReceiveTime'),
        ])

        with self.app.test_request_context():
            query = qb.alerts.from_params(search_params)  # noqa

        if self.app.config['DATABASE_URL'].startswith('postgres'):
            self.assertEqual(query.where, '1=1\nAND "status"=ANY(%(status)s)\nAND "environment" ILIKE %(environment)s\nAND "group"!=%(not_group)s')
            self.assertEqual(query.vars, {'status': ['open', 'ack'], 'environment': '%DEV%', 'not_group': 'Network'})
            self.assertEqual(query.sort, 's.code DESC,last_receive_time ASC')
        else:
            import re
            self.assertEqual(query.where, {'status': {'$in': ['open', 'ack']}, 'environment': {'$regex': re.compile('DEV', re.IGNORECASE)}, 'group': {'$ne': 'Network'}})
            self.assertEqual(query.sort, [('code', -1), ('lastReceiveTime', 1)])

    def test_alerts_attributes(self):

        search_params = MultiDict([('attributes.country_code', 'US')])
        with self.app.test_request_context():
            query = qb.alerts.from_params(search_params)

        if self.app.config['DATABASE_URL'].startswith('postgres'):
            self.assertIn('AND attributes @> %(attr_country_code)s', query.where)
            self.assertEqual(query.vars, {'attr_country_code': {'country_code': 'US'}})
        else:
            self.assertEqual(query.where, {'attributes.country_code': 'US'})

    def test_blackouts_filter(self):

        self.maxDiff = None

        search_params = MultiDict([
            ('id', 'd1340d76-2277-4d47-937f-571bc1da6411'),
            ('priority', '1'),
            ('environment', 'Development'),
            ('service', 'svc1'),
            ('resource', 'res1'),
            ('event', 'evt1'),
            ('group', 'grp1'),
            ('tag', 'tag1'),
            ('customer', 'cust1'),
            ('startTime', ''),
            ('endTime', ''),
            ('duration', '100'),
            ('status', 'pending'),
            ('remaining', '100'),
            ('user', 'admin@alerta.dev'),
            ('createTime', ''),
            ('text', 'reason'),
        ])

        try:
            with self.app.test_request_context():
                query = qb.blackouts.from_params(search_params)  # noqa
        except Exception as e:
            self.fail(f'Unexpected exception in blackouts filter query: {e}')

    def test_blackouts_sort_by(self):

        sort_params = MultiDict([
            ('sort-by', 'priority'),
            ('sort-by', 'environment'),
            ('sort-by', 'service'),
            ('sort-by', 'resource'),
            ('sort-by', 'event'),
            ('sort-by', 'group'),
            ('sort-by', 'tags'),
            ('sort-by', 'customer'),
            ('sort-by', 'startTime'),
            ('sort-by', 'endTime'),
            ('sort-by', 'duration'),
            ('sort-by', 'status'),
            ('sort-by', 'remaining'),
            ('sort-by', 'user'),
            ('sort-by', 'createTime'),
            ('sort-by', 'text'),
        ])

        try:
            with self.app.test_request_context():
                query = qb.blackouts.from_params(sort_params)  # noqa
        except Exception as e:
            self.fail(f'Unexpected exception in blackouts sort-by query: {e}')

    @patch('alerta.database.backends.mongodb.utils.datetime')
    def test_blackouts_query(self, mock_datetime):

        now = datetime(2021, 1, 17, 20, 58, 0)
        mock_datetime.utcnow.return_value = now

        # ?status=expired&status=pending&page=2&page-size=20&sort-by=-startTime
        search_params = MultiDict([
            ('status', 'expired'),
            ('status', 'pending'),
            ('sort-by', '-startTime'),
            ('page', '2'),
            ('page-size', '20'),
        ])

        with self.app.test_request_context():
            query = qb.blackouts.from_params(search_params)  # noqa

            if self.app.config['DATABASE_URL'].startswith('postgres'):
                self.assertEqual(query.where, "1=1\nAND (start_time > NOW() at time zone 'utc' OR end_time <= NOW() at time zone 'utc')")
                self.assertEqual(query.vars, {})
                self.assertEqual(query.sort, 'start_time ASC')
            else:
                self.assertEqual(query.where, {'$or': [{'startTime': {'$gt': now}}, {'endTime': {'$lte': now}}]})
                self.assertEqual(query.sort, [('startTime', 1)])

    def test_heartbeats_filter(self):

        self.maxDiff = None

        search_params = MultiDict([
            ('id', 'd1340d76-2277-4d47-937f-571bc1da6411'),
            ('origin', 'origin/foo'),
            ('tag', 'tag1'),
            ('tag', 'tag2'),
            ('attributes', 'attributes.foo'),
            ('attributes', 'attributes.bar'),
            ('type', 'exceptionAlert'),
            ('createTime', ''),
            ('timeout', '3600'),
            ('receiveTime', ''),
            ('customer', 'cust1'),
            ('latency', '200'),
            ('since', ''),
            ('status', 'expired'),
        ])

        try:
            with self.app.test_request_context():
                query = qb.heartbeats.from_params(search_params)  # noqa
        except Exception as e:
            self.fail(f'Unexpected exception in heartbeats filter query: {e}')

    def test_heartbeats_sort_by(self):

        sort_params = MultiDict([
            ('sort-by', 'origin'),
            ('sort-by', 'tags'),
            ('sort-by', 'attributes'),
            ('sort-by', 'type'),
            ('sort-by', 'createTime'),
            ('sort-by', 'timeout'),
            ('sort-by', 'receiveTime'),
            ('sort-by', 'customer'),
            ('sort-by', 'latency'),
            ('sort-by', 'since'),
        ])

        try:
            with self.app.test_request_context():
                query = qb.heartbeats.from_params(sort_params)  # noqa
        except Exception as e:
            self.fail(f'Unexpected exception in heartbeats sort-by query: {e}')

    def test_heartbeats_query(self):

        self.maxDiff = None

        # ?status=slow&page=1&page-size=20&sort-by=-latency
        search_params = MultiDict([
            ('status', 'slow'),
            ('sort-by', '-latency'),
            ('page', '1'),
            ('page-size', '20'),
        ])

        with self.app.test_request_context():
            query = qb.heartbeats.from_params(search_params)  # noqa

        if self.app.config['DATABASE_URL'].startswith('postgres'):
            self.assertEqual(query.where, '1=1')
            self.assertEqual(query.vars, {})
            self.assertEqual(query.sort, 'latency DESC')
        else:
            self.assertEqual(query.where, {})  # heartbeat status is a special case
            self.assertEqual(query.sort, [('latency', -1)])

    def test_keys_filter(self):

        self.maxDiff = None

        search_params = MultiDict([
            ('id', 'd1340d76-2277-4d47-937f-571bc1da6411'),
            ('key', 'rgLq9QJqsTK1nJVew6KM54IFRbnmrQbgSQr0X5tQ'),
            ('status', 'expired'),
            ('user', 'user@alerta.dev'),
            ('scope', 'read:alerts'),
            ('type', 'read-write'),
            ('text', 'test key'),
            ('expireTime', ''),
            ('count', '123'),
            ('lastUsedTime', ''),
            ('customer', 'cust1'),
        ])

        try:
            with self.app.test_request_context():
                query = qb.keys.from_params(search_params)  # noqa
        except Exception as e:
            self.fail(f'Unexpected exception in API keys filter query: {e}')

    def test_keys_sort_by(self):

        sort_params = MultiDict([
            ('sort-by', 'key'),
            ('sort-by', 'status'),
            ('sort-by', 'user'),
            ('sort-by', 'scopes'),
            ('sort-by', 'type'),
            ('sort-by', 'text'),
            ('sort-by', 'expireTime'),
            ('sort-by', 'count'),
            ('sort-by', 'lastUsedTime'),
            ('sort-by', 'customer'),
        ])

        try:
            with self.app.test_request_context():
                query = qb.keys.from_params(sort_params)  # noqa
        except Exception as e:
            self.fail(f'Unexpected exception in API keys sort-by query: {e}')

    @patch('alerta.database.backends.mongodb.utils.datetime')
    def test_keys_query(self, mock_datetime):

        now = datetime(2021, 1, 17, 20, 58, 0)
        mock_datetime.utcnow.return_value = now
        mock_datetime.strftime = datetime.strftime

        self.maxDiff = None

        # ?status=active&page=1&page-size=20&sort-by=count
        search_params = MultiDict([
            ('status', 'active'),
            ('sort-by', '-count'),
            ('page', '2'),
            ('page-size', '20'),
        ])

        with self.app.test_request_context():
            query = qb.keys.from_params(search_params)  # noqa

        if self.app.config['DATABASE_URL'].startswith('postgres'):
            self.assertEqual(query.where, "1=1\nAND (expire_time >= NOW() at time zone 'utc')")
            self.assertEqual(query.vars, {})
            self.assertEqual(query.sort, 'count DESC')
        else:
            self.assertEqual(query.where, {'$or': [{'expireTime': {'$gte': now}}]}, query.where)
            self.assertEqual(query.sort, [('count', -1)])

    def test_users_filter(self):

        self.maxDiff = None

        search_params = MultiDict([
            ('id', 'd1340d76-2277-4d47-937f-571bc1da6411'),
            ('name', 'Dev Ops'),
            ('login', 'ops'),
            ('email', 'ops@alerta.dev'),
            ('domain', 'alerta.dev'),
            ('status', 'inactive'),
            ('role', 'ops'),
            ('attributes.prefs', ''),
            ('createTime', ''),
            ('lastLogin', ''),
            ('text', 'devops'),
            ('updateTime', ''),
            ('email_verified', 'true'),
        ])

        try:
            with self.app.test_request_context():
                query = qb.users.from_params(search_params)  # noqa
        except Exception as e:
            self.fail(f'Unexpected exception in users filter query: {e}')

    def test_users_sort_by(self):

        sort_params = MultiDict([
            ('sort-by', 'name'),
            ('sort-by', 'login'),
            ('sort-by', 'email'),
            ('sort-by', 'domain'),
            ('sort-by', 'status'),
            ('sort-by', 'roles'),
            ('sort-by', 'attributes'),
            ('sort-by', 'createTime'),
            ('sort-by', 'lastLogin'),
            ('sort-by', 'text'),
            ('sort-by', 'updateTime'),
            ('sort-by', 'email_verified'),
        ])

        try:
            with self.app.test_request_context():
                query = qb.users.from_params(sort_params)  # noqa
        except Exception as e:
            self.fail(f'Unexpected exception in users sort-by query: {e}')

    def test_users_query(self):

        self.maxDiff = None

        # ?status=inactive&page=1&page-size=20&sort-by=lastLogin
        search_params = MultiDict([
            ('status', 'inactive'),
            ('sort-by', '-lastLogin'),
            ('page', '1'),
            ('page-size', '20'),
        ])

        with self.app.test_request_context():
            query = qb.users.from_params(search_params)  # noqa

        if self.app.config['DATABASE_URL'].startswith('postgres'):
            self.assertEqual(query.where, '1=1\nAND "status"=%(status)s')
            self.assertEqual(query.vars, {'status': 'inactive'})
            self.assertEqual(query.sort, 'last_login ASC')
        else:
            self.assertEqual(query.where, {'status': 'inactive'})
            self.assertEqual(query.sort, [('lastLogin', 1)])

    def test_groups_filter(self):

        self.maxDiff = None

        search_params = MultiDict([
            ('id', 'd1340d76-2277-4d47-937f-571bc1da6411'),
            ('name', 'devops-team'),
            ('text', 'Devops Team'),
            ('count', '5'),
        ])

        try:
            with self.app.test_request_context():
                query = qb.groups.from_params(search_params)  # noqa
        except Exception as e:
            self.fail(f'Unexpected exception in groups filter query: {e}')

    def test_groups_sort_by(self):

        sort_params = MultiDict([
            ('sort-by', 'name'),
            ('sort-by', 'text'),
            ('sort-by', 'count'),
        ])

        try:
            with self.app.test_request_context():
                query = qb.groups.from_params(sort_params)  # noqa
        except Exception as e:
            self.fail(f'Unexpected exception in groups sort-by query: {e}')

    def test_groups_query(self):

        self.maxDiff = None

        # ?page=1&page-size=20&sort-by=count
        search_params = MultiDict([
            ('sort-by', '-count'),
            ('page', '1'),
            ('page-size', '20'),
        ])

        with self.app.test_request_context():
            query = qb.groups.from_params(search_params)  # noqa

        if self.app.config['DATABASE_URL'].startswith('postgres'):
            self.assertEqual(query.where, '1=1')
            self.assertEqual(query.vars, {})
            self.assertEqual(query.sort, 'count DESC')
        else:
            self.assertEqual(query.where, {})
            self.assertEqual(query.sort, [('count', -1)])

    def test_perms_filter(self):

        self.maxDiff = None

        search_params = MultiDict([
            ('id', 'd1340d76-2277-4d47-937f-571bc1da6411'),
            ('match', 'read-write'),  # FIXME: role, group, org?
            ('scope', 'read'),
            ('scope', 'write'),
        ])

        try:
            with self.app.test_request_context():
                query = qb.perms.from_params(search_params)  # noqa
        except Exception as e:
            self.fail(f'Unexpected exception in perms filter query: {e}')

    def test_perms_sort_by(self):

        sort_params = MultiDict([
            ('sort-by', 'match'),  # FIXME: role, group, org?
            ('sort-by', 'scopes'),
        ])

        try:
            with self.app.test_request_context():
                query = qb.perms.from_params(sort_params)  # noqa
        except Exception as e:
            self.fail(f'Unexpected exception in perms sort-by query: {e}')

    def test_perms_query(self):

        self.maxDiff = None

        # ?scope=read&page=1&page-size=20&sort-by=match
        search_params = MultiDict([
            ('scope', 'read'),
            ('sort-by', 'match'),  # FIXME: role, group, org?
            ('page', '1'),
            ('page-size', '20'),
        ])

        with self.app.test_request_context():
            query = qb.perms.from_params(search_params)  # noqa

        if self.app.config['DATABASE_URL'].startswith('postgres'):
            self.assertEqual(query.where, '1=1\nAND "scopes"=%(scopes)s')
            self.assertEqual(query.vars, {'scopes': 'read'})
            self.assertEqual(query.sort, 'match ASC')
        else:
            self.assertEqual(query.where, {'scopes': 'read'})
            self.assertEqual(query.sort, [('match', 1)])

    def test_customers_filter(self):

        self.maxDiff = None

        search_params = MultiDict([
            ('id', 'd1340d76-2277-4d47-937f-571bc1da6411'),
            ('match', 'read-write'),  # FIXME: ??
            ('customer', 'cust1'),
            ('customer', 'cust2'),
        ])

        try:
            with self.app.test_request_context():
                query = qb.customers.from_params(search_params)  # noqa
        except Exception as e:
            self.fail(f'Unexpected exception in customers filter query: {e}')

    def test_customers_sort_by(self):

        sort_params = MultiDict([
            ('sort-by', 'match'),  # FIXME: ??
            ('sort-by', 'customer'),
        ])

        try:
            with self.app.test_request_context():
                query = qb.customers.from_params(sort_params)  # noqa
        except Exception as e:
            self.fail(f'Unexpected exception in customers sort-by query: {e}')

    def test_customers_query(self):

        self.maxDiff = None

        search_params = MultiDict([
            ('match', 'keycloak-role'),
            ('match', 'github-org'),
            ('match', 'gitlab-group'),
            ('sort-by', '-customer'),
            ('page', '2'),
            ('page-size', '50'),
        ])

        with self.app.test_request_context():
            query = qb.customers.from_params(search_params)  # noqa

        if self.app.config['DATABASE_URL'].startswith('postgres'):
            self.assertEqual(query.where, '1=1\nAND "match"=ANY(%(match)s)')
            self.assertEqual(query.vars, {'match': ['keycloak-role', 'github-org', 'gitlab-group']})
            self.assertEqual(query.sort, 'customer DESC')
        else:
            self.assertEqual(query.where, {'match': {'$in': ['keycloak-role', 'github-org', 'gitlab-group']}})
            self.assertEqual(query.sort, [('customer', -1)])


class QueryParserTestCase(unittest.TestCase):

    def setUp(self):

        test_config = {
            'TESTING': True,
            'AUTH_REQUIRED': False,
            'ALERT_TIMEOUT': 120,
            'HISTORY_LIMIT': 5,
            'DEBUG': False,
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
                'attributes': {'region': 'EMEA', 'partition': '7.0'},
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
                'attributes': {'region': 'LATAM', 'partition': '72'},
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
                'attributes': {'region': 'APAC', 'partition': '727'},
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
                'attributes': {'region': 'EMEA', 'partition': '27'},
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

    def tearDown(self):
        db.destroy()

    def _search(self, q):
        response = self.client.get(f'/alerts?q={q}')
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
        self.assertEqual(self._search(q='service:"Shared"'), 4)
        self.assertEqual(self._search(q='tags:aaa'), 3)
        self.assertEqual(self._search(q='tags:"aaa"'), 3)
        self.assertEqual(self._search(q='attributes.region:EMEA'), 2)
        self.assertEqual(self._search(q='_.region:EMEA'), 2)
        self.assertEqual(self._search(q='_.region:(EMEA LATAM)'), 3)
        self.assertEqual(self._search(q='_.region:(EMEA OR LATAM)'), 3)
        self.assertEqual(self._search(q='attributes.partition:7'), 4)
        self.assertEqual(self._search(q='_.partition:7'), 4)
        self.assertEqual(self._search(q='attributes.partition:"7"'), 1)
        self.assertEqual(self._search(q='_.partition:"7"'), 1)

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
