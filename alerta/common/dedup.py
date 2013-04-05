

class DeDup(object):

    current = {}
    previous = {}
    count = {}

    @classmethod
    def update(cls, environment, resource, event):

        environment = tuple(environment)

        if (environment, resource) not in DeDup.current:
            DeDup.previous[(environment, resource)] = None
            DeDup.current[(environment, resource)] = event
            DeDup.count[(environment, resource, event)] = 1
            return

        if DeDup.current[(environment, resource)] != event:
            previous = DeDup.current[(environment, resource)]
            DeDup.previous[(environment, resource)] = previous
            DeDup.current[(environment, resource)] = event

            DeDup.count[(environment, resource, previous)] = 0
            DeDup.count[(environment, resource, event)] = 1
        else:
            DeDup.count[(environment, resource, event)] += 1

    @classmethod
    def is_duplicate(cls, environment, resource, event):

        environment = tuple(environment)

        if (environment, resource) not in DeDup.current:
            return False

        if DeDup.current[(environment, resource)] != event:
            return False
        else:
            return True

    @classmethod
    def is_send(cls, environment, resource, event, every):

        environment = tuple(environment)

        if not DeDup.is_duplicate(environment, resource, event):
            return True
        elif (DeDup.is_duplicate(environment, resource, event) and
                DeDup.count[(environment, resource, event)] % every == 0):
            return True
        else:
            return False

    def __repr__(self):

        str = ''
        for environment, resource in DeDup.current.keys():
            str += 'DeDup(environment=%s, resource= %s, event=%s, previous=%s, count=%s)' % (
                ','.join(environment),
                resource,
                DeDup.current[(environment, resource)],
                DeDup.previous.get((environment, resource), 'n/a'),
                DeDup.count[(environment, resource, DeDup.current[(environment, resource)])]) + '\n'
        return str



