

class DeDup(object):

    current = {}
    previous = {}
    count = {}

    @classmethod
    def update(cls, environment, resource, event, severity):

        environment = tuple(environment)

        if (environment, resource, event) not in DeDup.current:
            DeDup.previous[(environment, resource, event)] = severity
            DeDup.current[(environment, resource, event)] = severity
            DeDup.count[(environment, resource, event, severity)] = 1
            return

        if DeDup.current[(environment, resource, event)] != severity:
            previous = DeDup.current[(environment, resource, event)]
            DeDup.previous[(environment, resource, event)] = previous
            DeDup.current[(environment, resource, event)] = severity

            DeDup.count[(environment, resource, event, previous)] = 0
            DeDup.count[(environment, resource, event, severity)] = 1
        else:
            DeDup.count[(environment, resource, event, severity)] += 1

    @classmethod
    def is_duplicate(cls, environment, resource, event, severity):

        environment = tuple(environment)

        if (environment, resource, event) not in DeDup.current:
            return False

        if DeDup.current[(environment, resource, event)] != severity:
            return False
        else:
            return True

    @classmethod
    def is_send(cls, environment, resource, event, severity, every):

        environment = tuple(environment)

        if not DeDup.is_duplicate(environment, resource, event, severity):
            return True
        elif (DeDup.is_duplicate(environment, resource, event, severity) and
                DeDup.count[(environment, resource, event, severity)] % every == 0):
            return True
        else:
            return False

    def __repr__(self):

        str = ''
        for environment, resource, event in DeDup.current.keys():
            str += 'DeDup(environment=%s, resource= %s, event=%s, severity=%s, previous=%s, count=%s)\n' % (
                ','.join(environment),
                resource,
                event,
                DeDup.current[(environment, resource, event)],
                DeDup.previous.get((environment, resource, event), 'n/a'),
                DeDup.count[(environment, resource, event, DeDup.current[(environment, resource, event)])])
        return str if str != '' else 'DeDup()'



