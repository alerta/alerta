import os
import sys
import argparse
import socket
import ConfigParser

from alerta.common.utils import Bunch

CONF = Bunch()  # config options can be accessed using CONF.verbose or CONF.use_syslog


def register_opts(opts):

    CONF.update(opts)


def parse_args(argv, prog=None, version='unknown', cli_parser=None, daemon=True):

    if prog is None:
        prog = os.path.basename(sys.argv[0])

    OPTION_DEFAULTS = {
        'conf_file': '/etc/alerta/alerta.conf',
        'version': 'unknown',
        'debug': False,
        'verbose': False,
        'log_dir': '/var/log/alerta',
        'log_file': '%s.log' % prog,
        'pid_dir': '/var/run/alerta',
        'use_syslog': True,
        'use_stderr': False,
        'foreground': False,
        'yaml_config': '/etc/alerta/%s.yaml' % prog,
        'show_settings': False,
    }

    SYSTEM_DEFAULTS = {

        'timezone': 'Europe/London',

        'user_id': 'alerta',
        'server_threads': 4,
        'disable_flag': '/var/run/alerta/%s.disable' % prog,
        'global_timeout': 86400,  # seconds
        'parser_dir': '/etc/alerta/parsers',
        'loop_every': 30,   # seconds

        'token_limit': 20,
        'token_rate': 2,

        'console_limit': 1000,  # max number of alerts sent to console
        'history_limit': -10,   # show last x most recent history entries
        'dashboard_dir': '/',

        'forward_duplicate': False,
    }
    CONF.update(SYSTEM_DEFAULTS)

    cfg_parser = argparse.ArgumentParser(
        add_help=False
    )
    cfg_parser.add_argument(
        '-c',
        '--conf-file',
        help="Specify config file (default: %s)" % OPTION_DEFAULTS['conf_file'],
        metavar="FILE",
        default=OPTION_DEFAULTS['conf_file']
    )
    args, argv_left = cfg_parser.parse_known_args(argv)

    config_file_order = [
        args.conf_file,
        os.path.expanduser('~/.alerta.conf'),
        os.environ.get('ALERTA_CONF', ''),
    ]
    #DEBUG print 'CONFIG files => ', config_file_order

    config = ConfigParser.SafeConfigParser()
    conf_files = config.read(config_file_order)
    defaults = config.defaults()  # read in [DEFAULTS] section

    defaults['conf_file'] = ','.join(conf_files)
    if conf_files:
        if config.has_section(prog):  # read in program-specific sections
            for name in config.options(prog):
                if (OPTION_DEFAULTS.get(name, None) in (True, False) or
                        SYSTEM_DEFAULTS.get(name, None) in (True, False)):
                    defaults[name] = config.getboolean(prog, name)
                elif (isinstance(OPTION_DEFAULTS.get(name, None), int) or
                        isinstance(SYSTEM_DEFAULTS.get(name, None), int)):
                    defaults[name] = config.getint(prog, name)
                else:
                    defaults[name] = config.get(prog, name)
                #DEBUG print '[%s] %s = %s' % (prog, name, config.get(prog, name))
    else:
        defaults = dict()

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
        '--log-dir',
        metavar="DIR",
        default=OPTION_DEFAULTS['log_dir'],
        help="Log directory, prepended to --log-file"
    )
    parser.add_argument(
        '--log-file',
        metavar="FILE",
        default=OPTION_DEFAULTS['log_file'],
        help="Log file name"
    )
    parser.add_argument(
        '--pid-dir',
        metavar="DIR",
        default=OPTION_DEFAULTS['pid_dir'],
        help="PID directory"
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
        '--yaml-config',
        metavar="FILE",
        default=OPTION_DEFAULTS['yaml_config'],
        action="store",
        help="Path to the YAML configuration",
    )
    parser.add_argument(
        '--show-settings',
        default=OPTION_DEFAULTS['show_settings'],
        action='store_true',
        help="Output evaluated configuration options"
    )

    if daemon:
        parser.add_argument(
            '-f',
            '--foreground',
            default=OPTION_DEFAULTS['foreground'],
            action='store_true',
            help="Do not fork, run in the foreground"
        )
    parser.set_defaults(**defaults)

    args, argv = parser.parse_known_args(argv_left)
    CONF.update(vars(args))

    if CONF.show_settings:
        print '[DEFAULT]'
        for k, v in sorted(CONF.iteritems()):
            print '%s = %s' % (k, v)
        sys.exit(0)
