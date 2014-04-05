
import os
import sys
import logging
import logging.handlers
import cStringIO
import traceback

from alerta.common import config

CONF = config.CONF

_DEFAULT_LOG_FORMAT = "%(asctime)s.%(msecs).03d %(name)s[%(process)d] %(threadName)s %(levelname)s - %(message)s"
_DEFAULT_LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

log_opts = {
    'syslog_facility': 'local7',
}


def _create_logging_excepthook(name):
    def logging_excepthook(type, value, tb):

        stringbuffer = cStringIO.StringIO()
        traceback.print_exception(type, value, tb,
                                  None, stringbuffer)
        lines = stringbuffer.getvalue()
        stringbuffer.close()

        getLogger(name).critical(lines)
    return logging_excepthook


def setup(name):
    """Setup logging."""

    config.register_opts(log_opts)

    sys.excepthook = _create_logging_excepthook(name)

    log_root = getLogger(name)

    if CONF.use_syslog:
        if sys.platform == "darwin":
            socket = '/var/run/syslog'
        else:
            socket = '/dev/log'
        facility = CONF.syslog_facility

        try:
            syslog = logging.handlers.SysLogHandler(address=socket, facility=facility)
        except IOError, e:
            print >>sys.stderr, 'ERROR - Failed to log to syslog socket %s: %s' % (socket, e)
        else:
            log_root.addHandler(syslog)

    logpath = _get_log_file_path()
    if logpath:
        try:
            filelog = logging.handlers.WatchedFileHandler(logpath, encoding='utf-8')
        except IOError, e:
            print >>sys.stderr, 'ERROR - Failed to log to logfile %s: %s' % (logpath, e)
        else:
            log_root.addHandler(filelog)

        # TODO(nsatterl): test mode like openstack??

    for handler in log_root.handlers:
        log_format = _DEFAULT_LOG_FORMAT
        date_format = _DEFAULT_LOG_DATE_FORMAT
        handler.setFormatter(logging.Formatter(fmt=log_format, datefmt=date_format))

    if CONF.use_stderr:
        streamlog = ColorHandler()
        color_fmt = logging.Formatter("%(color)s" + _DEFAULT_LOG_FORMAT + "\033[0m")
        streamlog.setFormatter(color_fmt)
        log_root.addHandler(streamlog)

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


def set_owner(uid=-1, gid=-1):
    return os.chown(_get_log_file_path(), uid, gid)


def _get_prog_name():
    return os.path.basename(sys.argv[0])


def _get_log_file_path():
    logfile = CONF.log_file
    logdir = CONF.log_dir

    if logfile and not logdir:
        return logfile

    if logfile and logdir:
        return os.path.join(logdir, logfile)

    if logdir:
        prog = _get_prog_name()
        return '%s.log' % (os.path.join(logdir, prog))


class ColorHandler(logging.StreamHandler):

    # XXX - OpenStack colours for reference
    #
    # LEVEL_COLORS = {
    #     logging.NOTSET: '',
    #     logging.DEBUG: '\033[00;32m',  # GREEN
    #     logging.INFO: '\033[00;36m',  # CYAN
    #     #logging.AUDIT: '\033[01;36m',  # BOLD CYAN
    #     logging.WARN: '\033[01;33m',  # BOLD YELLOW
    #     logging.ERROR: '\033[01;31m',  # BOLD RED
    #     logging.CRITICAL: '\033[01;31m',  # BOLD RED
    # }

    LEVEL_COLORS = {
        logging.NOTSET: '',
        logging.DEBUG: '\033[90m',     # BLACK
        logging.INFO: '\033[92m',      # GREEN
        logging.WARN: '\033[96m',      # CYAN
        logging.ERROR: '\033[93m',     # YELLOW
        logging.CRITICAL: '\033[91m',  # RED
    }

    def format(self, record):
        record.color = self.LEVEL_COLORS[record.levelno]
        return logging.StreamHandler.format(self, record)
