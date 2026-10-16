import logging
import re
from pathlib import Path

LOG = logging.getLogger('alerta.database')

MIGRATION_NAME = re.compile(r'^\d{4}_\w+\.sql$')
LOCK_KEY = 0x616c7274


def migration_files(path):
    return sorted(p for p in Path(path).iterdir() if MIGRATION_NAME.match(p.name))


def applied_migrations(conn):
    with conn.cursor() as cursor:
        cursor.execute("SELECT to_regclass('schema_migrations') IS NOT NULL")
        if not cursor.fetchone()[0]:
            return set()
        cursor.execute('SELECT name FROM schema_migrations')
        return {row[0] for row in cursor.fetchall()}


def migrate(conn, path):
    """
    Apply pending migrations in filename order, one transaction each. Returns the names applied.
    """
    if conn.autocommit:
        raise ValueError('migrations need a transaction, but the connection is in autocommit mode')

    done = applied_migrations(conn)
    conn.commit()
    pending = [f for f in migration_files(path) if f.name not in done]

    applied = []
    for migration in pending:
        try:
            with conn.cursor() as cursor:
                # serialises concurrent workers; released at commit or rollback
                cursor.execute('SELECT pg_advisory_xact_lock(%s, hashtext(current_schema()))', (LOCK_KEY,))
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS schema_migrations (
                        name text PRIMARY KEY,
                        applied_at timestamptz NOT NULL DEFAULT now()
                    )
                """)
                cursor.execute('SELECT 1 FROM schema_migrations WHERE name=%s', (migration.name,))
                is_pending = cursor.fetchone() is None
                if is_pending:
                    cursor.execute(migration.read_text())
                    cursor.execute('INSERT INTO schema_migrations (name) VALUES (%s)', (migration.name,))
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        if is_pending:
            applied.append(migration.name)
            LOG.info('Applied database migration %s', migration.name)

    return applied
