import os
import sys
import argparse
import ConfigParser

from alerta.common.utils import Bunch

# TODO(nsatterl): do i set lots of global defaults here?
# _DEFAULT_MONGO_CONNECTION = 'sqlite:///' + paths.state_path_def('$sqlite_db')

DEFAULT_PORT = 8765

CONF = Bunch()  # config options can be accessed using CONF.verbose or CONF.use_syslog


def parse_args(argv, prog=None, version='unknown'):

    if prog is None:
        prog = os.path.basename(sys.argv[0]).rstrip('.py')

    OPTION_DEFAULTS = {
        'version': 'unknown',
        'debug': False,
        'verbose': False,
        'logpath': '/var/log/alerta/%s.log' % prog,
        'use_syslog': True,
        'use_stderr': False,
        'foreground': False,
    }

    cfg_parser = argparse.ArgumentParser(
        add_help=False
    )
    cfg_parser.add_argument(
        '-c', '--conf-file',
        help="Specify config file",
        metavar="FILE",
        default='/opt/alerta/etc/alerta.conf'
    )
    args, argv_left = cfg_parser.parse_known_args()

    defaults = dict()
    if args.conf_file:
        config = ConfigParser.SafeConfigParser()
        config.read([args.conf_file])
        if config.has_section(prog):
            for name in config.options(prog):
                if name not in OPTION_DEFAULTS or OPTION_DEFAULTS[name] not in (True, False):
                    defaults[name] = config.get(prog, name)
                else:
                    defaults[name] = config.getboolean(prog, name)

    parser = argparse.ArgumentParser(
        prog=prog,
        # description='', # TODO(nsatterl): pass __doc__ from calling program?
        parents=[cfg_parser],
    )

    parser.add_argument(
        '--version',
        action='version',
        version=version
    )
    parser.add_argument(
        '--debug',
        default=OPTION_DEFAULTS['debug'],
        action='store_true',
        help="Log level DEBUG and higher (default: WARNING)"
    )
    parser.add_argument(
        '--verbose',
        default=OPTION_DEFAULTS['verbose'],
        action='store_true',
        help="Log level INFO and higher (default: WARNING)"
    )
    parser.add_argument(
        '--logpath',
        default=OPTION_DEFAULTS['logpath'],
        help="Path for log file"
    )
    parser.add_argument(
        '--use-syslog',
        default=OPTION_DEFAULTS['use_syslog'],
        action='store_true',
        help="Send errors to syslog"
    )
    parser.add_argument(
        '--use-stderr',
        default=OPTION_DEFAULTS['use_stderr'],
        action='store_true',
        help="Send to console stderr"
    )
    parser.add_argument(
        '--foreground',
        default=OPTION_DEFAULTS['foreground'],
        action='store_true',
        help="Run in foreground"
    )
    parser.set_defaults(**defaults)

    args = parser.parse_args(argv_left)
    CONF.Load(vars(args))

