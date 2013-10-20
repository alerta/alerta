import os
import sys
import argparse
import ConfigParser

from alerta.common.utils import Bunch

CONF = Bunch()  # config options can be accessed using CONF.verbose or CONF.use_syslog


DEFAULTS = {
    'config_file': '/etc/alerta/alerta.conf',
    'timezone': 'Europe/London',  # Australia/Sydney, America/Los_Angeles, etc.
    'version': 'unknown',
    'debug': 'no',
    'verbose': 'no',
    'log_dir': '/var/log/alerta',
    'log_file': '%(prog)s.log',
    'pid_dir': '/var/run/alerta',
    'use_syslog': 'yes',
    'use_stderr': 'no',
    'foreground': 'no',
    'user_id': 'alerta',
    'server_threads': '4',
    'disable_flag': '/var/run/alerta/%(prog)s.disable',
    'loop_every': '30',
    'global_timeout': '86400',  # seconds
    'console_limit': '1000',  # max number of alerts sent to console
    'history_limit': '-10',   # show last x most recent history entries
    'dashboard_dir': '/',
}

_TRUE = {'yes': True, 'true': True, 'on': True}
_FALSE = {'no': False, 'false': False, 'off': False}


def register_opts(opts):

    DEFAULTS.update(dict((k, str(v)) for k, v in opts.iteritems()))

    parse_args()


def parse_args(args=None, prog=None, version='unknown', cli_parser=None, daemon=True):

    if args is None:
        args = sys.argv[1:]

    if prog is None:
        prog = os.path.basename(sys.argv[0])

    # get config file from command line, if defined
    cfg_parser = argparse.ArgumentParser(
        add_help=False
    )
    cfg_parser.add_argument(
        '-c',
        '--config-file',
        help="Specify config file (default: %s)" % DEFAULTS['config_file'],
        metavar="FILE",
        default=DEFAULTS['config_file']
    )
    c, args = cfg_parser.parse_known_args(args)

    config_file_order = [
        c.config_file,
        os.path.expanduser('~/.alerta.conf'),
        os.environ.get('ALERTA_CONF', ''),
    ]

    # read in system-wide defaults
    config = ConfigParser.SafeConfigParser(DEFAULTS)
    config.set('DEFAULT', 'prog', prog)
    config_files = config.read(config_file_order)

    defaults = config.defaults()  # read in [DEFAULTS] section
    defaults['config_file'] = ','.join(config_files)

    if config_files:
        if config.has_section(prog):  # read in program-specific sections
            for name in config.options(prog):
                try:
                    defaults[name] = config.getint(prog, name)
                except ValueError:
                    if defaults[name].lower() in [_TRUE, _FALSE]:
                        defaults[name] = config.getboolean(prog, name)
                    else:
                        defaults[name] = config.get(prog, name)

    # read in command line options
    parents = [cfg_parser]
    if cli_parser:
        parents.append(cli_parser)

    parser = argparse.ArgumentParser(
        prog=prog,
        # description='', # TODO(nsatterl): pass __doc__ from calling program?
        parents=parents,
    )
    parser.add_argument(
        '--version',
        action='version',
        version=version
    )
    parser.add_argument(
        '--debug',
        action='store_true',
        help="Log level DEBUG and higher (default: WARNING)"
    )
    parser.add_argument(
        '--verbose',
        action='store_true',
        help="Log level INFO and higher (default: WARNING)"
    )
    parser.add_argument(
        '--log-dir',
        metavar="DIR",
        help="Log directory, prepended to --log-file"
    )
    parser.add_argument(
        '--log-file',
        metavar="FILE",
        help="Log file name"
    )
    parser.add_argument(
        '--pid-dir',
        metavar="DIR",
        help="PID directory"
    )
    parser.add_argument(
        '--use-syslog',
        action='store_true',
        help="Send errors to syslog"
    )
    parser.add_argument(
        '--use-stderr',
        action='store_true',
        help="Send to console stderr"
    )
    parser.add_argument(
        '--yaml-config',
        metavar="FILE",
        action="store",
        help="Path to the YAML configuration",
    )

    if daemon:
        parser.add_argument(
            '-f',
            '--foreground',
            action='store_true',
            help="Do not fork, run in the foreground"
        )
    parser.set_defaults(**defaults)

    args, extra = parser.parse_known_args(args)

    copy = vars(args)
    for k, v in vars(args).iteritems():
        try:
            v = int(v)
            copy[k] = v
        except ValueError:
            if v.lower() in _TRUE:
                copy[k] = True
            elif v.lower() in _FALSE:
                copy[k] = False
        except TypeError:
            pass
    CONF.update(copy)

