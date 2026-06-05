import unittest

from alerta.app import create_app, db


class PostgresAutocommitTestCase(unittest.TestCase):
    """
    Postgres backend should open connections in autocommit mode so that
    read-only requests (``_fetchone`` / ``_fetchall``, which never COMMIT)
    do not leave the connection sitting ``idle in transaction`` for the rest
    of the request. See contrib/loadtest: leaving connections idle in
    transaction holds back the xmin horizon (blocks HOT-pruning of the hot
    de-dup row) and adds GetSnapshotData/ProcArray overhead under load.
    """

    def setUp(self):
        self.app = create_app({'TESTING': True})
        if not self.app.config['DATABASE_URL'].startswith('postgres'):
            self.skipTest('Postgres backend only')

    def tearDown(self):
        db.destroy()

    def test_connection_opens_in_autocommit(self):
        # a freshly opened connection must already be in autocommit mode
        conn = db.connect()
        try:
            self.assertTrue(conn.autocommit, 'Postgres connection should open with autocommit=True')
        finally:
            conn.close()

    def test_read_does_not_leave_idle_in_transaction(self):
        # the regression this guards: a read must not leave a dangling txn open
        from psycopg2.extensions import TRANSACTION_STATUS_IDLE

        with self.app.test_request_context():
            conn = db.get_db()
            # a read goes through _fetchall, which does NOT issue a COMMIT
            db._fetchall('SELECT 1 AS n', {})
            self.assertEqual(
                conn.get_transaction_status(),
                TRANSACTION_STATUS_IDLE,
                'connection left idle in transaction after a read — autocommit is off',
            )


if __name__ == '__main__':
    unittest.main()
