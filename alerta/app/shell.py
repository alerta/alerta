
import argparse

from alerta.app import app
from alerta.app import db
from alerta.version import __version__


def main():

    parser = argparse.ArgumentParser(
        prog='alertad',
        description='Alerta server (for development purposes only)'
    )
    parser.add_argument(
        '-P',
        '--port',
        type=int,
        default=8080,
        help='Listen port (default: 8080)'
    )
    parser.add_argument(
        '--debug',
        action='store_true',
        default=False,
        help='Debug output'
    )
    args = parser.parse_args()

    app.logger.info('Starting alerta version %s ...', __version__)
    app.logger.info('Using MongoDB version %s ...', db.get_version())
    app.run(host='0.0.0.0', port=args.port, debug=args.debug, threaded=True)
