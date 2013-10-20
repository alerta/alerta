import os
import sys
import argparse
import ConfigParser

from alerta.common.utils import Bunch

CONF = Bunch()  # config options can be accessed using CONF.verbose or CONF.use_syslog


DEFAULTS = {
    'config_file': '/etc/alerta/alerta.conf',
    'version': 'unknown',
    'debug': 'no',
    'verbose': 'no',
    'log_dir': '/var/log/alerta',
    'log_file': '%(prog)s.log',
    'pid_dir': '/var/run/alerta',
    'use_syslog': 'yes',
    'use_stderr': 'no',
    'foreground': 'no',
    'yaml_config': '/etc/alerta/%(prog)s.yaml',
    'user_id': 'alerta',
    'server_threads': '4',
    'disable_flag': '/var/run/alerta/%(prog)s.disable',
    'loop_every': '30',
}

# -        'timezone': 'Europe/London',
# -
# -        'global_timeout': 86400,  # seconds
# -        'parser_dir': '/etc/alerta/parsers',
# -
# -        'token_limit': 20,
# -        'token_rate': 2,
# -
# -        'console_limit': 1000,  # max number of alerts sent to console
# -        'history_limit': -10,   # show last x most recent history entries
# -        'dashboard_dir': '/',


def register_opts(opts):

    DEFAULTS.update(dict((k, str(v)) for k, v in opts.iteritems()))

    parse_args()


def parse_args(args=None, prog=None, version=None, cli_parser=None, daemon=True):

    if args is None:
        args = sys.argv[1:]

    if prog is None:
        prog = os.path.basename(sys.argv[0])

    # read in system-wide defaults
    config = ConfigParser.SafeConfigParser(DEFAULTS)

    config.set('DEFAULT', 'prog', prog)

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
    cli, args = cfg_parser.parse_known_args(args)

    config_file_order = [
        os.path.expanduser('~/.alerta.conf'),
        os.environ.get('ALERTA_CONF', ''),
        cli.config_file,
    ]

    config_files_read = config.read(config_file_order)
    for section in config.sections():
        print '6. ConfigParser [%s] %s' % (section, config.items(section))

    cli_defaults = config.defaults()  # read in [DEFAULTS] section

    if config_files_read:
        if config.has_section(prog):  # read in program-specific sections
            for name in config.options(prog):
                cli_defaults[name] = config.get(prog, name)

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
    parser.set_defaults(**cli_defaults)

    args, argv = parser.parse_known_args(args)
    CONF.update(vars(args))

    for k in CONF.keys():
        try:
            v = int(CONF[k])
            CONF[k] = v
        except ValueError:
            pass
