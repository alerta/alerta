import os
import sys
import argparse
import ConfigParser

from alerta.common.utils import Bunch

CONF = Bunch()  # config options can be accessed using CONF.verbose or CONF.use_syslog


def parse_args(argv, prog=None, version='unknown', cli_parser=None, daemon=True):

    if prog is None:
        prog = os.path.basename(sys.argv[0])

    OPTION_DEFAULTS = {
        'config': '/etc/alerta/alerta.conf',
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

        'api_host': 'localhost',
        'api_port': 80,
        'api_endpoint': '/alerta/api/v2',   # eg. /Services/API
        'dashboard_dir': '/dashboard',  # eg. /home/username/git/alerta/dashboard

        'http_proxy': None,
        'https_proxy': None,

        'user_id': 'alerta',
        'server_threads': 4,
        'disable_flag': '/var/run/alerta/%s.disable' % prog,
        'alert_timeout': 86400,  # seconds
        'parser_dir': '/etc/alerta/parsers',
        'loop_every': 30,   # seconds

        'token_limit': 20,
        'token_rate': 2,

        'mongo_host': 'localhost',
        'mongo_port': 27017,
        'mongo_db': 'monitoring',
        'mongo_collection': 'alerts',

        'console_limit': 1000,  # max number of alerts sent to console
        'history_limit': -10,   # show last x most recent history entries

        'stomp_host': 'localhost',
        'stomp_port': 61613,

        'inbound_queue': '/exchange/alerts',
        'outbound_queue': '/queue/logger',
        'outbound_topic': '/topic/notify',
        'forward_duplicate': False,

        'rabbit_host': 'localhost',
        'rabbit_port': 5672,
        'rabbit_use_ssl': False,
        'rabbit_userid': 'guest',
        'rabbit_password': 'guest',
        'rabbit_virtual_host': '/',

        'syslog_udp_port': 514,
        'syslog_tcp_port': 514,
        'syslog_facility': 'local7',

        'ping_max_timeout': 15,  # seconds
        'ping_max_retries': 2,
        'ping_slow_warning': 5,    # ms
        'ping_slow_critical': 10,  # ms

        'urlmon_max_timeout': 15,  # seconds
        'urlmon_slow_warning': 2000,   # ms
        'urlmon_slow_critical': 5000,  # ms

        'smtp_host': 'smtp',
        'smtp_port': 25,
        'mail_user': 'alerta@guardian.co.uk',
        'mail_list': 'websys@guardian.co.uk',

        'irc_host': 'irc.gudev.gnl',
        'irc_port': 6667,
        'irc_channel': '#alerts',
        'irc_user': 'alerta',

        'solarwinds_host': 'solarwinds',
        'solarwinds_username': 'admin',
        'solarwinds_password': '',
        'solarwinds_group': 'websys',

        'es_host': 'localhost',
        'es_port': 9200,
        'es_index': 'alerta-%Y.%m.%d',  # NB. Kibana config must match this index

        'pagerduty_endpoint': 'https://events.pagerduty.com/generic/2010-04-15/create_event.json',
        'pagerduty_api_key': '',

        'dynect_customer': 'theguardian',
        'dynect_username': '',
        'dynect_password': '',

        'fog_file': '/etc/fog/alerta.conf',  # used by alert-aws
        'ec2_regions': ['eu-west-1', 'us-east-1'],

        'gmetric_host': 'localhost',
        'gmetric_port': 8649,
        'gmetric_protocol': 'udp',
        'gmetric_spoof': '10.1.1.1:%s' % prog,

        'carbon_host': 'localhost',
        'carbon_port': 2003,
        'carbon_protocol': 'udp',

        'statsd_host': 'localhost',
        'statsd_port': 8125,

        'nagios_plugins': '/usr/lib64/nagios/plugins',
    }
    CONF.update(SYSTEM_DEFAULTS)

    cfg_parser = argparse.ArgumentParser(
        add_help=False
    )
    cfg_parser.add_argument(
        '-c', '--conf-file',
        help="Specify config file (default: %s)" % OPTION_DEFAULTS['config'],
        metavar="FILE",
        default=OPTION_DEFAULTS['config']
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
            '--foreground',
            default=OPTION_DEFAULTS['foreground'],
            action='store_true',
            help="Run in foreground"
        )
    parser.set_defaults(**defaults)

    args, argv = parser.parse_known_args(argv_left)
    CONF.update(vars(args))

    if CONF.show_settings:
        print '[DEFAULT]'
        for k, v in sorted(CONF.iteritems()):
            print '%s = %s' % (k, v)
        sys.exit(0)
