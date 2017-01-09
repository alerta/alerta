
import argparse

from alerta.app import app
from alerta.app import db
from alerta.version import __version__

LOG = app.logger

def main():

    parser = argparse.ArgumentParser(
        prog='alertad',
        description='Alerta server (for development purposes only)',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument(
        '-H',
        '--host',
        type=str,
        default='0.0.0.0',
        help='Bind host'
    )
    parser.add_argument(
        '-P',
        '--port',
        type=int,
        default=8080,
        help='Listen port'
    )
    parser.add_argument(
        '--debug',
        action='store_true',
        default=False,
        help='Debug output'
    )
    args = parser.parse_args()

    LOG.info('Starting alerta version %s ...', __version__)
    app.run(host=args.host, port=args.port, debug=args.debug, threaded=True, use_reloader=False)
