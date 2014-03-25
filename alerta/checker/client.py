
import os
import sys
import subprocess
import shlex

from alerta.common import log as logging
from alerta.common import config
from alerta.common.alert import Alert
from alerta.common.heartbeat import Heartbeat
from alerta.common import severity_code
from alerta.common.api import ApiClient

Version = '3.0.0'

LOG = logging.getLogger(__name__)
CONF = config.CONF


class CheckerClient(object):

    nagios_opts = {
        'nagios_plugins': '/usr/lib64/nagios/plugins',
    }

    def __init__(self):

        config.register_opts(CheckerClient.nagios_opts)

    def main(self):

        if CONF.heartbeat:
            msg = Heartbeat(version=Version)
        else:
            # Run Nagios plugin check
            args = shlex.split(os.path.join(CONF.nagios_plugins, CONF.nagios_cmd))
            LOG.info('Running %s', ' '.join(args))
            try:
                check = subprocess.Popen(args, stdout=subprocess.PIPE)
            except Exception, e:
                LOG.error('Nagios check did not execute: %s', e)
                sys.exit(1)

            stdout = check.communicate()[0]
            rc = check.returncode
            LOG.debug('Nagios plugin %s => %s (rc=%d)', CONF.nagios_cmd, stdout, rc)

            if rc == 0:
                severity = severity_code.NORMAL
            elif rc == 1:
                severity = severity_code.WARNING
            elif rc == 2:
                severity = severity_code.CRITICAL
            elif rc == 3:
                severity = severity_code.UNKNOWN
            else:
                rc = -1
                severity = severity_code.INDETERMINATE

            # Parse Nagios plugin check output
            text = ''
            long_text = ''
            perf_data = ''
            extra_perf_data = False

            for num, line in enumerate(stdout.split('\n'), start=1):
                if num == 1:
                    if '|' in line:
                        text = line.split('|')[0].rstrip(' ')
                        perf_data = line.split('|')[1]
                        value = perf_data.split(';')[0].lstrip(' ')
                    else:
                        text = line
                        value = 'rc=%s' % rc
                else:
                    if '|' in line:
                        long_text += line.split('|')[0]
                        perf_data += line.split('|')[1]
                        extra_perf_data = True
                    elif extra_perf_data is False:
                        long_text += line
                    else:
                        perf_data += line

            LOG.debug('Short Output: %s', text)
            LOG.debug('Long Output: %s', long_text)
            LOG.debug('Perf Data: %s', perf_data)

            msg = Alert(
                resource=CONF.resource,
                event=CONF.event,
                correlate=CONF.correlate,
                group=CONF.group,
                value=value,
                severity=severity,
                environment=CONF.environment,
                service=CONF.service,
                text=text + ' ' + long_text,
                event_type='nagiosAlert',
                tags=CONF.tags,
                attributes={
                    'thresholdInfo': CONF.nagios_cmd,
                    'moreInfo': perf_data
                },
                timeout=CONF.timeout,
                raw_data=stdout,
            )

        if CONF.dry_run:
            print msg
        else:
            LOG.debug('Message => %s', repr(msg))

            api = ApiClient()
            api.send(msg)

        return msg.get_id()