
from alerta.alert import Alert


class DeDup(object):

    current = {}
    previous = {}
    count = {}

    @classmethod
    def update(cls, dedupAlert):

        environment = tuple(dedupAlert.environment)

        if (environment, dedupAlert.resource, dedupAlert.event) not in DeDup.current:
            DeDup.previous[(environment, dedupAlert.resource, dedupAlert.event)] = dedupAlert.severity
            DeDup.current[(environment, dedupAlert.resource, dedupAlert.event)] = dedupAlert.severity
            DeDup.count[(environment, dedupAlert.resource, dedupAlert.event, dedupAlert.severity)] = 1
            return

        if DeDup.current[(environment, dedupAlert.resource, dedupAlert.event)] != dedupAlert.severity:
            previous = DeDup.current[(environment, dedupAlert.resource, dedupAlert.event)]
            DeDup.previous[(environment, dedupAlert.resource, dedupAlert.event)] = previous
            DeDup.current[(environment, dedupAlert.resource, dedupAlert.event)] = dedupAlert.severity

            DeDup.count[(environment, dedupAlert.resource, dedupAlert.event, previous)] = 0
            DeDup.count[(environment, dedupAlert.resource, dedupAlert.event, dedupAlert.severity)] = 1
        else:
            DeDup.count[(environment, dedupAlert.resource, dedupAlert.event, dedupAlert.severity)] += 1

    @classmethod
    def is_duplicate(cls, dedupAlert):

        environment = tuple(dedupAlert.environment)

        if (environment, dedupAlert.resource, dedupAlert.event) not in DeDup.current:
            return False

        if DeDup.current[(environment, dedupAlert.resource, dedupAlert.event)] != dedupAlert.severity:
            return False
        else:
            return True

    @classmethod
    def is_send(cls, dedupAlert, every):

        environment = tuple(dedupAlert.environment)

        if not DeDup.is_duplicate(dedupAlert):
            return True
        elif (DeDup.is_duplicate(dedupAlert) and
                DeDup.count[(environment, dedupAlert.resource, dedupAlert.event, dedupAlert.severity)] % every == 0):
            return True
        else:
            return False

    def __repr__(self):

        str = ''
        for environment, resource, event in DeDup.current.keys():
            str += 'DeDup(environment=%s, resource=%s, event=%s, severity=%s, previous=%s, count=%s)\n' % (
                ','.join(environment),
                resource,
                event,
                DeDup.current[(environment, resource, event)],
                DeDup.previous.get((environment, resource, event), 'n/a'),
                DeDup.count[(environment, resource, event, DeDup.current[(environment, resource, event)])])
        return str if str != '' else 'DeDup()'



