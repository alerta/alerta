import os
import sys
import argparse
import ConfigParser

from alerta.common.utils import Bunch


CONF = Bunch()  # config options can be accessed using CONF.verbose or CONF.use_syslog

prog = os.path.basename(sys.argv[0])

DEFAULTS = {
    'config_file': '/etc/alerta/alerta.conf',
    'timezone': 'Europe/London',  # Australia/Sydney, America/Los_Angeles, etc.
    'version': 'unknown',
    'debug': 'no',
    'verbose': 'no',
    'log_dir': '/var/log/alerta',
    'log_file': '%s.log' % prog,
    'pid_dir': '/var/run/alerta',
    'use_syslog': 'yes',
    'use_stderr': 'no',
    'foreground': 'no',
    'user_id': 'alerta',
    'server_threads': 4,
    'disable_flag': '/var/lib/alerta/%s.disable' % prog,
    'loop_every': 30,
    'global_timeout': 86400,  # seconds
    'console_limit': 10000,   # max number of alerts sent to console
    'history_limit': -20,     # show last x most recent history entries
}

config = ConfigParser.RawConfigParser(DEFAULTS)
config.set('DEFAULT', 'prog', prog)

_TRUE = ['yes', 'true', 'on']
_FALSE = ['no', 'false', 'off']
_boolean = _TRUE + _FALSE


def register_opts(opts, section=None):
    '''
        Options are registered to the 'DEFAULT' section
        unless specified because it is assumed they are
        system defaults eg. debug, verbose
    '''

    if not section:
        section = 'DEFAULT'
    elif not config.has_section(section):
        config.add_section(section)

    # True, False, numbers & lists
    for k, v in opts.iteritems():
        if type(v) == int:
            v = str(v)
        if type(v) == bool:
            v = 'yes' if v else 'no'
        if type(v) == list:
            v = ','.join(v)
        config.set(section, k, v)

    parse_args(section=prog)


def parse_args(args=None, section=None, version='unknown', cli_parser=None, daemon=True):

    if args is None:
        args = sys.argv[1:]

    section = section or prog

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
    config_files = config.read(config_file_order)

    defaults = config.defaults().copy()  # read in [DEFAULTS] section
    defaults['config_file'] = ','.join(config_files)

    if config_files:
        if config.has_section(section):  # read in program-specific sections
            for name in config.options(section):
                try:
                    defaults[name] = config.getint(section, name)
                except ValueError:
                    if config.get(section, name).lower() in _boolean:
                        defaults[name] = config.getboolean(section, name)
                    else:
                        defaults[name] = config.get(section, name)
                except TypeError:
                    defaults[name] = config.get(section, name)

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
        if type(v) == bool:
            continue
        try:
            copy[k] = int(v)
            continue
        except TypeError:
            continue  # skip nulls
        except ValueError:
            pass
        if v.lower() in _TRUE:
            copy[k] = True
            continue
        elif v.lower() in _FALSE:
            copy[k] = False
            continue
        if ',' in v:
            copy[k] = v.split(',')

    CONF.update(copy)

    #print '[%s] %s' % (section, CONF)
