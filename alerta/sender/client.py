
from alerta.common import log as logging
from alerta.common import config
from alerta.alert import Alert, Heartbeat
from alerta.common.mq import Messaging

__version__ = '2.0.0'

DEFAULT_TIMEOUT = 3600

LOG = logging.getLogger(__name__)
CONF = config.CONF


def main():

    if CONF.heartbeat:
        msg = Heartbeat(
            origin=CONF.origin,
            version=__version__,
        )
    else:
        msg = Alert(
            resource=CONF.resource,
            event=CONF.event,
            correlate=CONF.correlate,
            group=CONF.group,
            value=CONF.value,
            severity=CONF.severity,
            environment=CONF.environment,
            service=CONF.service,
            text=CONF.text,
            event_type='exceptionAlert',  # TODO(nsatterl): make this configurable?
            tags=CONF.tags,
            origin=CONF.origin,
            threshold_info='n/a',   #TODO(nsatterl): make this configurable?
            timeout=CONF.timeout,
        )

    if CONF.dry_run:
        print msg
    else:
        LOG.debug('Message => %s', repr(msg))

        mq = Messaging()
        mq.connect()
        mq.send(msg)
        mq.disconnect()

    return msg.get_id()