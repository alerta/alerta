
import datetime


from alerta.common import log as logging

LOG = logging.getLogger(__name__)


class DeDup(object):
    """
    by_severity = alert will be raised on change of severity (event if event name stays the same)
    by_value = alert will be raised whenever the value changes

    Can call multiple time to create different de-duplication rules for different events.
    eg.
    >>> dedup_by_value = DeDup(by_value=True)
    >>> send_every_5 = DeDup(threshold=5)
    >>> resend_every_2hrs = DeDup(duration=7200)

    """

    current = {}
    previous = {}
    count = {}
    last_create_time = {}

    by_value = False
    threshold = 1
    duration = 7200

    def __init__(self, by_value=False, threshold=1, duration=600):

        self.__class__.by_value = by_value
        self.__class__.threshold = threshold
        self.__class__.duration = duration

    @classmethod
    def update(cls, dedupAlert):

        dedup_by = (tuple(dedupAlert.environment), dedupAlert.resource, dedupAlert.event)
        dedup_value = dedupAlert.severity
        dedup_count = (tuple(dedupAlert.environment), dedupAlert.resource, dedupAlert.event, dedupAlert.severity)

        if cls.by_value:
            dedup_by = (tuple(dedupAlert.environment), dedupAlert.resource, dedupAlert.event, dedupAlert.severity)
            dedup_value = dedupAlert.value
            dedup_count = (tuple(dedupAlert.environment), dedupAlert.resource, dedupAlert.event, dedupAlert.severity, dedupAlert.value)

        print 'dedup by %s value %s' % (dedup_by, dedup_value)
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