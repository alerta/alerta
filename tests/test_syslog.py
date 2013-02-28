import sys

from alerta.syslog.daemon import SyslogDaemon
from alerta.common import config
from alerta.common import log as logging

__version__ = '1.0'

CONF = config.CONF

CONF.use_syslog = False
CONF.foreground = True

CONF.syslog_udp_port = 5140
CONF.syslog_tcp_port = 5140

argv = ['--use-stderr', '--foreground', '--debug']

config.parse_args(argv, version=__version__)
logging.setup('alerta')

print CONF

syslog = SyslogDaemon('alert-syslog')
syslog.start()

print 'done'