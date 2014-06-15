
import datetime

from alerta.common import config
from alerta.common import log as logging

CONF = config.CONF
LOG = logging.getLogger(__name__)


class DeDup(object):
    """
    By default, DeDup will de-duplicate alerts based on severity. ie. if the severity of an alert changes it will
    allow the alert to be resent. To modify this behaviour to send an alert each time the alert value changes set
    the "by_value" parameter to True.

     Example. Create different de-duplication rules for different events.

    >>> dedup_by_value = DeDup(by_value=True)
    >>> if dedup_by_value.is_send(gangliaAlert):
    >>>     api.send(gangliaAlert)

    >>> send_every_5 = DeDup(threshold=5)
    >>> resend_every_2hrs = DeDup(duration=7200)

    """

    current = {}
    previous = {}
    count = {}
    last_create_time = {}

    dedup_opts = {
        'dedup_by_value': 'false',
        'dedup_threshold': '1',
        'dedup_duration': '600',
    }

    def __init__(self, by_value=None, threshold=None, duration=None):

        config.register_opts(DeDup.dedup_opts)

        self.__class__.by_value = by_value or CONF.dedup_by_value
        self.__class__.threshold = threshold or CONF.dedup_threshold
        self.__class__.duration = duration or CONF.dedup_duration

        LOG.info('De-duplicate alerts based on: by_value=%s, threshold=%s, duration=%s',
                 self.__class__.by_value, self.__class__.threshold, self.__class__.duration)

    @classmethod
    def update(cls, dedupAlert):

        if not dedupAlert:
            return

        dedup_by = (tuple(dedupAlert.environment), dedupAlert.resource, dedupAlert.event)
        dedup_value = dedupAlert.severity
        dedup_count = (tuple(dedupAlert.environment), dedupAlert.resource, dedupAlert.event, dedupAlert.severity)

        if cls.by_value:
            dedup_by = (tuple(dedupAlert.environment), dedupAlert.resource, dedupAlert.event, dedupAlert.severity)
            dedup_value = dedupAlert.value
            dedup_count = (tuple(dedupAlert.environment), dedupAlert.resource, dedupAlert.event, dedupAlert.severity, dedupAlert.value)

        if dedup_by not in DeDup.current:
            DeDup.previous[dedup_by] = dedup_value
            DeDup.current[dedup_by] = dedup_value
            DeDup.count[dedup_count] = 1
            return

        if DeDup.current[dedup_by] != dedup_value:
            previous = DeDup.current[dedup_by]
            DeDup.previous[dedup_by] = previous
            DeDup.current[dedup_by] = dedup_value

            DeDup.count[(dedup_by, previous)] = 0
            DeDup.count[dedup_count] = 1
        else:
            DeDup.count[dedup_count] += 1

    @classmethod
    def is_duplicate(cls, dedupAlert):

        if not dedupAlert:
            return False

        dedup_by = (tuple(dedupAlert.environment), dedupAlert.resource, dedupAlert.event)

        if cls.by_value:
            dedup_by = (tuple(dedupAlert.environment), dedupAlert.resource, dedupAlert.event, dedupAlert.severity)

        if dedup_by not in DeDup.current:
            return False

        if DeDup.current[dedup_by] != dedupAlert.severity:
            return False
        else:
            return True

    @classmethod
    def is_send(cls, dedupAlert):

        if not dedupAlert:
            return False

        if dedupAlert.event_type == 'Heartbeat':
            return True

        dedup_by = (tuple(dedupAlert.environment), dedupAlert.resource, dedupAlert.event)
        dedup_count = (tuple(dedupAlert.environment), dedupAlert.resource, dedupAlert.event, dedupAlert.severity)

        if cls.by_value:
            dedup_by = (tuple(dedupAlert.environment), dedupAlert.resource, dedupAlert.event, dedupAlert.severity)
            dedup_count = (tuple(dedupAlert.environment), dedupAlert.resource, dedupAlert.event, dedupAlert.severity, dedupAlert.value)

        if not DeDup.is_duplicate(dedupAlert):
            DeDup.last_create_time[dedup_by] = dedupAlert.create_time
            cls.update(dedupAlert)
            return True
        elif (DeDup.is_duplicate(dedupAlert) and
                DeDup.count[dedup_count] % cls.threshold == 0):
            DeDup.last_create_time[dedup_by] = dedupAlert.create_time
            cls.update(dedupAlert)
            return True
        elif datetime.datetime.utcnow() - DeDup.last_create_time[dedup_by] > datetime.timedelta(seconds=cls.duration):
            DeDup.last_create_time[dedup_by] = dedupAlert.create_time
            cls.update(dedupAlert)
            return True
        else:
            cls.update(dedupAlert)
            LOG.debug('Alert de-duplicated %s', dedupAlert)
            return False

    def __repr__(self):

        str = ''
        for dedup_by in DeDup.current.keys():

            str += 'DeDup(key=%r, severity_or_value=%r, previous=%r, count=%r, last=%s)' % (
                dedup_by,
                DeDup.current[dedup_by],
                DeDup.previous.get(dedup_by, 'n/a'),
                DeDup.count[dedup_by + (DeDup.current[dedup_by],)],
                DeDup.last_create_time[dedup_by].replace(microsecond=0).isoformat() + ".%03dZ" % (DeDup.last_create_time[dedup_by].microsecond // 1000))
        return str if str != '' else 'DeDup()'