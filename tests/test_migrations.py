import os
import tempfile
import threading
import unittest
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

DATABASE_URL = os.environ.get('DATABASE_URL', '')
SQL_DIR = Path(__file__).parent.parent / 'alerta' / 'sql'
ALL_MIGRATIONS = sorted(p.name for p in SQL_DIR.glob('[0-9][0-9][0-9][0-9]_*.sql'))


@unittest.skipUnless(DATABASE_URL.startswith('postgres'), 'requires PostgreSQL')
class MigrationsTestCase(unittest.TestCase):

    def setUp(self):
        import psycopg2

        from alerta.database.backends.postgres.migrate import migrate
        self.migrate = migrate
        self.psycopg2 = psycopg2

        self.schema = f'test_migrations_{uuid4().hex[:8]}'
        admin = psycopg2.connect(DATABASE_URL)
        admin.autocommit = True
        admin.cursor().execute(f'CREATE SCHEMA {self.schema}')
        admin.close()

        self.conn = self.connect()
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)

    def tearDown(self):
        self.conn.close()
        self.tmp.cleanup()
        admin = self.psycopg2.connect(DATABASE_URL)
        admin.autocommit = True
        admin.cursor().execute(f'DROP SCHEMA {self.schema} CASCADE')
        admin.close()

    def connect(self):
        conn = self.psycopg2.connect(DATABASE_URL)
        conn.cursor().execute(f'SET search_path TO {self.schema}')
        conn.commit()
        return conn

    def write(self, name, text):
        (self.dir / name).write_text(text)

    def query(self, sql):
        with self.conn.cursor() as cursor:
            cursor.execute(sql)
            rows = cursor.fetchall()
        self.conn.commit()
        return rows

    def recorded(self):
        return [r[0] for r in self.query('SELECT name FROM schema_migrations ORDER BY name')]

    def test_fresh_database(self):
        applied = self.migrate(self.conn, SQL_DIR)

        self.assertEqual(applied, ALL_MIGRATIONS)
        self.assertEqual(self.recorded(), ALL_MIGRATIONS)
        self.assertEqual(self.query("SELECT to_regclass('alerts') IS NOT NULL")[0][0], True)

    def test_rerun_applies_nothing(self):
        self.migrate(self.conn, SQL_DIR)

        self.assertEqual(self.migrate(self.conn, SQL_DIR), [])

    def test_existing_9x_database_is_adopted(self):
        with self.conn.cursor() as cursor:
            cursor.execute((SQL_DIR / '0001_schema.sql').read_text())
            cursor.execute("INSERT INTO alerts (id, resource, event, environment) VALUES ('a1', 'web01', 'node_down', 'Production')")
        self.conn.commit()

        applied = self.migrate(self.conn, SQL_DIR)

        self.assertEqual(applied, ALL_MIGRATIONS)
        self.assertEqual(self.query('SELECT id FROM alerts'), [('a1',)])

    def test_dedup_key_backfilled_from_resource_and_event(self):
        from alerta.database.backends.postgres.base import with_keys

        with self.conn.cursor() as cursor:
            cursor.execute((SQL_DIR / '0001_schema.sql').read_text())
            cursor.execute("""
                INSERT INTO alerts (id, resource, event, environment, customer) VALUES
                    ('a1', 'web01', 'node_down', 'Production', NULL),
                    ('a2', 'db "01", ü', 'disk,full', 'Production', 'acme')
            """)
        self.conn.commit()

        self.migrate(self.conn, SQL_DIR)

        for id, resource, event, dedup_key, key_source, correlate_key in self.query(
                'SELECT id, resource, event, dedup_key, key_source, correlate_key FROM alerts ORDER BY id'):
            expected = with_keys(SimpleNamespace(resource=resource, event=event))
            self.assertEqual(dedup_key, expected['dedup_key'], id)
            self.assertEqual(correlate_key, expected['correlate_key'], id)
            self.assertEqual(key_source, 'template')

        indexes = [r[0] for r in self.query("SELECT indexname FROM pg_indexes WHERE tablename='alerts'")]
        self.assertIn('alerts_env_cust_dedup_key', indexes)
        self.assertNotIn('env_res_evt_cust_key', indexes)

    def test_dedup_key_unique_when_customer_is_null(self):
        self.migrate(self.conn, SQL_DIR)
        insert = """
            INSERT INTO alerts (id, resource, event, environment, dedup_key, key_source)
            VALUES (%s, 'web01', 'node_down', 'Production', '["web01", "node_down"]', 'template')
        """
        with self.conn.cursor() as cursor:
            cursor.execute(insert, ('a1',))
            with self.assertRaises(self.psycopg2.errors.UniqueViolation):
                cursor.execute(insert, ('a2',))
        self.conn.rollback()

    def test_applied_in_filename_order_and_other_files_ignored(self):
        self.write('0010_c.sql', 'INSERT INTO log VALUES (10);')
        self.write('0002_b.sql', 'INSERT INTO log VALUES (2);')
        self.write('0001_a.sql', 'CREATE TABLE log (n int);')
        self.write('schema.sql', 'SELECT broken;')
        self.write('README', 'not a migration')

        applied = self.migrate(self.conn, self.dir)

        self.assertEqual(applied, ['0001_a.sql', '0002_b.sql', '0010_c.sql'])
        self.assertEqual(self.query('SELECT n FROM log'), [(2,), (10,)])

    def test_only_new_migrations_applied(self):
        self.write('0001_a.sql', 'CREATE TABLE log (n int);')
        self.migrate(self.conn, self.dir)
        self.write('0002_b.sql', 'INSERT INTO log VALUES (2);')

        self.assertEqual(self.migrate(self.conn, self.dir), ['0002_b.sql'])
        self.assertEqual(self.query('SELECT n FROM log'), [(2,)])

    def test_failed_migration_rolls_back_and_is_not_recorded(self):
        self.write('0001_a.sql', 'CREATE TABLE log (n int);')
        self.write('0002_b.sql', 'INSERT INTO log VALUES (2); SELEC broken;')

        with self.assertRaises(self.psycopg2.Error):
            self.migrate(self.conn, self.dir)

        self.assertEqual(self.recorded(), ['0001_a.sql'])
        self.assertEqual(self.query('SELECT n FROM log'), [])

        self.write('0002_b.sql', 'INSERT INTO log VALUES (2);')
        self.assertEqual(self.migrate(self.conn, self.dir), ['0002_b.sql'])

    def test_autocommit_connection_rejected(self):
        self.conn.autocommit = True

        with self.assertRaises(ValueError):
            self.migrate(self.conn, self.dir)

    def test_concurrent_runners_apply_each_migration_once(self):
        self.write('0001_a.sql', 'CREATE TABLE IF NOT EXISTS log (n int); SELECT pg_sleep(0.2);')
        self.write('0002_b.sql', 'INSERT INTO log VALUES (2); SELECT pg_sleep(0.2);')

        results, errors = [], []
        barrier = threading.Barrier(5)

        def run():
            conn = self.connect()
            try:
                barrier.wait()
                results.append(self.migrate(conn, self.dir))
            except Exception as e:
                errors.append(e)
            finally:
                conn.close()

        threads = [threading.Thread(target=run) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.assertEqual(errors, [])
        self.assertEqual(sorted(name for r in results for name in r), ['0001_a.sql', '0002_b.sql'])
        self.assertEqual(self.query('SELECT n FROM log'), [(2,)])
        self.assertEqual(self.recorded(), ['0001_a.sql', '0002_b.sql'])
