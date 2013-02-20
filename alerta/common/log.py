
# TODO(nsatterl): log exceptions (checkout how OpenStack do it)

import logging
import logging.handlers

from alerta.common import config

CONF = config.CONF

_DEFAULT_LOG_FORMAT = "%(asctime)s.%(msecs)d %(name)s[%(process)d] %(threadName)s %(levelname)s - %(message)s"
_DEFAULT_LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def setup(name):
    """Setup logging."""

    log_root = getLogger(name)

    if CONF.use_syslog:
        facility = 'local7'  # TODO(nsatterl): import syslog ???
        # syslog = logging.handlers.SysLogHandler(address='/dev/log', facility=facility)
        # TODO(nsatterl): set for Mac OS at the moment
        syslog = logging.handlers.SysLogHandler(address='/var/run/syslog', facility=facility)
        log_root.addHandler(syslog)

    if CONF.logpath:
        filelog = logging.handlers.WatchedFileHandler(CONF.logpath)
        log_root.addHandler(filelog)

        # TODO(nsatterl): test mode like openstack??

    if CONF.use_stderr:
        streamlog = ColorHandler()
        log_root.addHandler(streamlog)

    for handler in log_root.handlers:
        log_format = _DEFAULT_LOG_FORMAT
        date_format = _DEFAULT_LOG_DATE_FORMAT
        handler.setFormatter(logging.Formatter(fmt=log_format, datefmt=date_format))

    if CONF.debug:
        log_root.setLevel(logging.DEBUG)
    elif CONF.verbose:
        log_root.setLevel(logging.INFO)
    else:
        log_root.setLevel(logging.WARNING)


def getLogger(name=None):

    if name:
        return logging.getLogger(name)
    else:
        return logging.root


# NOTE: From OpenStack logging module
class ColorHandler(logging.StreamHandler):
    LEVEL_COLORS = {
        logging.DEBUG: '\033[00;32m',  # GREEN
        logging.INFO: '\033[00;36m',  # CYAN
        logging.WARN: '\033[01;33m',  # BOLD YELLOW
        logging.ERROR: '\033[01;31m',  # BOLD RED
        logging.CRITICAL: '\033[01;31m',  # BOLD RED
    }

    def format(self, record):
        record.color = self.LEVEL_COLORS[record.levelno]
        return logging.StreamHandler.format(self, record)
