import unittest
from types import SimpleNamespace

from flask import Flask

from alerta.database.backends.mongodb.base import Backend as MongoBackend
from alerta.database.backends.postgres.base import Backend as PostgresBackend


class CorrelateAlertQueryTestCase(unittest.TestCase):

    def setUp(self):
        self.app = Flask(__name__)
        self.app.config['HISTORY_LIMIT'] = 5
        self.alert = SimpleNamespace(
            environment='development',
            resource='synthetic-resource',
            event='incoming-state',
            severity='critical',
            status='open',
            service=['synthetic-service'],
            value='synthetic-value',
            text='synthetic text',
            create_time=None,
            timeout=60,
            raw_data={},
            duplicate_count=0,
            repeat=False,
            previous_severity='normal',
            trend_indication='moreSevere',
            receive_time=None,
            last_receive_id='synthetic-id',
            last_receive_time=None,
            tags=[],
            attributes={},
            update_time=None,
            customer=None,
        )
        self.history = [SimpleNamespace(serialize={'id': 'synthetic-history'})]

    def test_postgres_lookup_prefers_the_existing_event(self):
        backend = PostgresBackend.__new__(PostgresBackend)
        captured = {}

        def capture_fetchone(query, variables):
            captured['query'] = query
            return 'synthetic-match'

        backend._fetchone = capture_fetchone
        with self.app.app_context():
            result = backend.is_correlated(self.alert)

        self.assertEqual(result, 'synthetic-match')
        self.assertIn('ORDER BY CASE WHEN event=%(event)s THEN 0 ELSE 1 END,', captured['query'])
        self.assertIn("CASE WHEN status IN ('closed', 'expired') THEN 1 ELSE 0 END, id", captured['query'])

    def test_mongodb_lookup_prefers_the_existing_event(self):
        backend = MongoBackend.__new__(MongoBackend)
        selected = {'_id': 'selected-alert-id'}
        calls = []

        class Alerts:
            def find_one(self, query, sort=None):
                calls.append((query, sort))
                return selected

        class Database:
            alerts = Alerts()

        def get_db():
            return Database()

        backend.get_db = get_db
        with self.app.app_context():
            result = backend.is_correlated(self.alert)

        self.assertIs(result, selected)
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0][0]['event'], 'incoming-state')

    def test_mongodb_fallback_sorts_correlated_siblings(self):
        backend = MongoBackend.__new__(MongoBackend)
        sibling = {'_id': 'sibling-alert-id'}
        calls = []

        class Alerts:
            def find_one(self, query, sort=None):
                calls.append((query, sort))
                return None if len(calls) == 1 else sibling

        class Database:
            alerts = Alerts()

        def get_db():
            return Database()

        backend.get_db = get_db
        with self.app.app_context():
            result = backend.is_correlated(self.alert)

        self.assertIs(result, sibling)
        self.assertEqual(calls[1][0]['event'], {'$ne': 'incoming-state'})
        self.assertEqual(calls[1][0]['status'], {'$nin': ['closed', 'expired']})
        self.assertEqual(calls[1][1], [('_id', 1)])

    def test_postgres_correlate_update_targets_the_selected_alert(self):
        backend = PostgresBackend.__new__(PostgresBackend)
        captured = {}

        def capture_update(query, variables, returning=False):
            captured['query'] = query
            captured['variables'] = variables
            captured['returning'] = returning
            return 'synthetic-row'

        backend._updateone = capture_update
        with self.app.app_context():
            result = backend.correlate_alert(self.alert, self.history, 'selected-alert-id')

        self.assertEqual(result, 'synthetic-row')
        self.assertIn('WHERE id=%(correlated_alert_id)s', captured['query'])
        self.assertEqual(captured['variables']['correlated_alert_id'], 'selected-alert-id')
        self.assertTrue(captured['returning'])

    def test_mongodb_correlate_update_targets_the_selected_alert(self):
        backend = MongoBackend.__new__(MongoBackend)
        captured = {}

        class Alerts:
            def find_one_and_update(self, query, update, return_document):
                captured['query'] = query
                captured['update'] = update
                captured['return_document'] = return_document
                return 'synthetic-document'

        class Database:
            alerts = Alerts()

        def get_db():
            return Database()

        backend.get_db = get_db
        with self.app.app_context():
            result = backend.correlate_alert(self.alert, self.history, 'selected-alert-id')

        self.assertEqual(result, 'synthetic-document')
        self.assertEqual(captured['query']['_id'], 'selected-alert-id')
        self.assertEqual(captured['update']['$set']['event'], 'incoming-state')


if __name__ == '__main__':
    unittest.main()
