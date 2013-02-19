import os
import sys
import argparse

from alerta.common.utils import Bunch

# TODO(nsatterl): do i set lots of global defaults here?
# _DEFAULT_MONGO_CONNECTION = 'sqlite:///' + paths.state_path_def('$sqlite_db')

DEFAULT_PORT = 8765

CONF = Bunch()


def parse_args(argv, prog=None, version='unknown'):
    if prog is None:
        prog = os.path.basename(sys.argv[0])

    parser = argparse.ArgumentParser(
        prog=prog,
        description='',
        epilog=''
    )
    parser.add_argument(
        '--version',
        action='version',
        version=version
    )
    parser.add_argument(
        '--debug',
        default=False,
        action='store_true',
        help="Log level DEBUG and higher"
    )
    parser.add_argument(
        '--verbose',
        default=False,
        action='store_true',
        help="Log level INFO and higher"
    )
    parser.add_argument(
        '--use-syslog',
        default=False,
        action='store_true',
        help="Send errors to syslog"
    )
    parser.add_argument(
        '--logpath',
        default='/var/log/alerta/%s.log' % prog,
        help="Path for log file"
    )
    parser.add_argument(
        '--use-stderr',
        default=False,
        action='store_true',
        help="Send to console stderr"
    )
    parser.add_argument(
        '--foreground',
        default=False,
        action='store_true',
        help="Run in foreground"
    )
    args = parser.parse_args(argv[1:])
    print args

    CONF.Load(vars(args))

