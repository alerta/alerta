
from alerta.common import log as logging
from alerta.common import config
from alerta.alert import Alert, Heartbeat
from alerta.common.api import ApiClient

Version = '2.0.2'

LOG = logging.getLogger(__name__)
CONF = config.CONF

DEFAULT_TIMEOUT = 3600

LOG = logging.getLogger(__name__)
CONF = config.CONF


class SenderClient(object):

    def main(self):

        if CONF.heartbeat:
            vtag = ''.join(CONF.tags) if CONF.tags else None

            heartbeat = Heartbeat(
                origin=CONF.origin,
                version=vtag or Version
            )
            if CONF.dry_run:
                print heartbeat
            else:
                LOG.debug(repr(heartbeat))

                api = ApiClient()
                api.send(heartbeat)

            return heartbeat.get_id()

        else:
            exceptionAlert = Alert(
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
                threshold_info='n/a',   # TODO(nsatterl): make this configurable?
                timeout=CONF.timeout,
                raw_data='n/a',  # TODO(nsatterl): make this configurable?
            )

            if CONF.dry_run:
                print exceptionAlert
            else:
                LOG.debug(repr(exceptionAlert))

                api = ApiClient()
                api.send(exceptionAlert)

            return exceptionAlert.get_id()