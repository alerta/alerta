import os
import sys
import argparse
import ConfigParser

from alerta.common.utils import Bunch

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

    SYSTEM_DEFAULTS = {

        'server_threads': 1,
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

        'syslog_udp_port': 514,
        'syslog_tcp_port': 514,
        'syslog_facility': 'local7',
    }
    CONF.Load(SYSTEM_DEFAULTS)

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

    defaults = dict()
    if args.conf_file:
        config = ConfigParser.SafeConfigParser()
        config.read([args.conf_file])
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

    print 'FIXME %s' % CONF
