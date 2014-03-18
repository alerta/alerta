
from alerta.common import log as logging
from alerta.common import config
from alerta.common.alert import Alert
from alerta.common.heartbeat import Heartbeat
from alerta.common.api import ApiClient

Version = '3.0.0'

LOG = logging.getLogger(__name__)
CONF = config.CONF

DEFAULT_TIMEOUT = 3600

LOG = logging.getLogger(__name__)
CONF = config.CONF


class SenderClient(object):

    def main(self):

        if CONF.heartbeat:
            heartbeat = Heartbeat(
                origin=CONF.origin,
                tags=CONF.tags,
                timeout=CONF.timeout
            )

            LOG.debug(heartbeat)

            api = ApiClient()

            return api.send(heartbeat)

        else:
            exceptionAlert = Alert(
                resource=CONF.resource,
                event=CONF.event,
                environment=CONF.environment,
                severity=CONF.severity,
                correlate=CONF.correlate,
                status=CONF.status,
                service=CONF.service,
                group=CONF.group,
                value=CONF.value,
                text=CONF.text,
                tags=CONF.tags,
                attributes=CONF.attributes,
                origin=CONF.origin,
                event_type=CONF.event_type,
                timeout=CONF.timeout,
                raw_data=CONF.raw_data
            )

            LOG.debug(repr(exceptionAlert))

            api = ApiClient()

            return api.send(exceptionAlert)
