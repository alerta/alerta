import os
import sys
import argparse
import ConfigParser

from bunch import Bunch

CONF = Bunch()  # config options can be accessed using CONF.verbose or CONF.use_syslog


def parse_args(argv, prog=None, version='unknown', cli_parser=None):

    if prog is None:
        prog = os.path.basename(sys.argv[0])

    OPTION_DEFAULTS = {

        'version': 'unknown',
        'debug': False,
        'verbose': False,
        'log_dir': '/var/log/alerta',
        'log_file': '%s.log' % prog,
        'use_syslog': True,
        'use_stderr': False,
        'foreground': False,
        'show_settings': False,
    }

    SYSTEM_DEFAULTS = {

        'timezone': 'Europe/London',

        'api_host': 'monitoring',
        'api_port': 80,
        'api_endpoint': '/',   # eg. /Services/API

        'server_threads': 4,
        'alert_timeout': 86400,  # seconds
        'parser_dir': '/opt/alerta/bin/parsers',

        'mongo_host': 'localhost',
        'mongo_port': 27017,
        'mongo_db': 'monitoring',
        'mongo_collection': 'alerts',

        'stomp_host': 'localhost',
        'stomp_port': 61613,

        'inbound_queue': '/queue/alerts',   # TODO(nsatterl): 'alert_queue' and 'alert_topic' ?
        'outbound_topic': '/topic/notify',
        'outbound_queue': '/queue/logger',

        'rabbit_host': 'localhost',
        'rabbit_port': 5672,
        'rabbit_use_ssl': False,
        'rabbit_userid': 'guest',
        'rabbit_password': 'guest',
        'rabbit_virtual_host': '/',

        'syslog_udp_port': 5140,
        'syslog_tcp_port': 5140,
        'syslog_facility': 'local7',
    }
    CONF.update(SYSTEM_DEFAULTS)

    cfg_parser = argparse.ArgumentParser(
        add_help=False
    )
    cfg_parser.add_argument(
        '-c', '--conf-file',
        help="Specify config file",
        metavar="FILE",
        default='/opt/alerta/etc/alerta.conf'
    )
    args, argv_left = cfg_parser.parse_known_args(argv)

    config_file_order = [
        args.conf_file,             # default config file or file -c file
        'alerta.conf',              # config file in current directory (beware daemonize() cd to /
        os.environ.get('ALERTA_CONF', ''),
    ]

    defaults = dict()
    if args.conf_file:
        config = ConfigParser.SafeConfigParser()
        config.read(config_file_order)
        if config.has_section(prog):
            for name in config.options(prog):
                if (OPTION_DEFAULTS.get(name, None) in (True, False) or
                        SYSTEM_DEFAULTS.get(name, None) in (True, False)):
                    defaults[name] = config.getboolean(prog, name)
                elif (isinstance(OPTION_DEFAULTS.get(name, None), int) or
                        isinstance(SYSTEM_DEFAULTS.get(name, None), int)):
                    defaults[name] = config.getint(prog, name)
                else:
                    defaults[name] = config.get(prog, name)
                #print '[%s] %s = %s' % (prog, name, config.get(prog, name))

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
        '--show-settings',
        default=OPTION_DEFAULTS['show_settings'],
        action='store_true',
        help="Output evaluated configuration options"
    )

    if not cli_parser:
        parser.add_argument(
            '--foreground',
            default=OPTION_DEFAULTS['foreground'],
            action='store_true',
            help="Run in foreground"
        )
    parser.set_defaults(**defaults)

    args = parser.parse_args(argv_left)
    CONF.update(vars(args))

    if CONF.show_settings:
        print '[DEFAULT]'
        for k, v in sorted(CONF.iteritems()):
            print '%s = %s' % (k, v)
        sys.exit(0)
