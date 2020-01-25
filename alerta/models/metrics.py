import time
from functools import wraps

from alerta.app import db


class Gauge:

    def __init__(self, group, name, title=None, description=None, value=0):

        self.group = group
        self.name = name
        self.title = title
        self.description = description
        self.type = 'gauge'
        self.value = value

    def serialize(self, format='json'):
        if format == 'prometheus':
            return (
                '# HELP alerta_{group}_{name} {description}\n'
                '# TYPE alerta_{group}_{name} gauge\n'
                'alerta_{group}_{name} {value}\n'.format(
                    group=self.group, name=self.name, description=self.description, value=self.value
                )
            )
        else:
            return {
                'group': self.group,
                'name': self.name,
                'title': self.title,
                'description': self.description,
                'type': self.type,
                'value': self.value
            }

    def __repr__(self):
        return 'Gauge(group={!r}, name={!r}, title={!r}, value={!r})'.format(
            self.group, self.name, self.title, self.value
        )

    @classmethod
    def from_document(cls, doc):
        return Gauge(
            group=doc.get('group'),
            name=doc.get('name'),
            title=doc.get('title', None),
            description=doc.get('description', None),
            value=doc.get('value', None)
        )

    @classmethod
    def from_record(cls, rec):
        return Gauge(
            group=rec.group,
            name=rec.name,
            title=rec.title,
            description=rec.description,
            value=rec.value
        )

    @classmethod
    def from_db(cls, r):
        if isinstance(r, dict):
            return cls.from_document(r)
        elif isinstance(r, tuple):
            return cls.from_record(r)
        else:
            return

    def set(self, value):
        self.value = value
        return Gauge.from_db(db.set_gauge(self))

    @classmethod
    def find_all(cls):
        return [Gauge.from_db(gauge) for gauge in db.get_metrics(type='gauge')]


class Counter:

    def __init__(self, group, name, title=None, description=None, count=0):

        self.group = group
        self.name = name
        self.title = title
        self.description = description
        self.type = 'counter'
        self.count = count

    def serialize(self, format='json'):
        if format == 'prometheus':
            return (
                '# HELP alerta_{group}_{name} {description}\n'
                '# TYPE alerta_{group}_{name} counter\n'
                'alerta_{group}_{name}_total {count}\n'.format(
                    group=self.group, name=self.name, description=self.description, count=self.count
                )
            )
        else:
            return {
                'group': self.group,
                'name': self.name,
                'title': self.title,
                'description': self.description,
                'type': self.type,
                'count': self.count
            }

    def __repr__(self):
        return 'Counter(group={!r}, name={!r}, title={!r}, count={!r})'.format(
            self.group, self.name, self.title, self.count
        )

    @classmethod
    def from_document(cls, doc):
        return Counter(
            group=doc.get('group'),
            name=doc.get('name'),
            title=doc.get('title', None),
            description=doc.get('description', None),
            count=doc.get('count', None)
        )

    @classmethod
    def from_record(cls, rec):
        return Counter(
            group=rec.group,
            name=rec.name,
            title=rec.title,
            description=rec.description,
            count=rec.count
        )

    @classmethod
    def from_db(cls, r):
        if isinstance(r, dict):
            return cls.from_document(r)
        elif isinstance(r, tuple):
            return cls.from_record(r)
        else:
            return

    def inc(self, count=1):
        c = Counter.from_db(db.inc_counter(Counter(
            group=self.group,
            name=self.name,
            title=self.title,
            description=self.description,
            count=count
        )))
        self.count = c.count

    @classmethod
    def find_all(cls):
        return [Counter.from_db(counter) for counter in db.get_metrics(type='counter')]


class Timer:

    def __init__(self, group, name, title=None, description=None, count=0, total_time=0):

        self.group = group
        self.name = name
        self.title = title
        self.description = description
        self.type = 'timer'

        self.start = None
        self.count = count
        self.total_time = total_time

    def serialize(self, format='json'):
        if format == 'prometheus':
            return (
                '# HELP alerta_{group}_{name} {description}\n'
                '# TYPE alerta_{group}_{name} summary\n'
                'alerta_{group}_{name}_count {count}\n'
                'alerta_{group}_{name}_sum {total_time}\n'.format(
                    group=self.group, name=self.name, description=self.description, count=self.count, total_time=self.total_time
                )
            )
        else:
            return {
                'group': self.group,
                'name': self.name,
                'title': self.title,
                'description': self.description,
                'type': self.type,
                'count': self.count,
                'totalTime': self.total_time
            }

    def __repr__(self):
        return 'Timer(group={!r}, name={!r}, title={!r}, count={!r}, total_time={!r})'.format(
            self.group, self.name, self.title, self.count, self.total_time
        )

    @classmethod
    def from_document(cls, doc):
        return Timer(
            group=doc.get('group'),
            name=doc.get('name'),
            title=doc.get('title', None),
            description=doc.get('description', None),
            count=doc.get('count', None),
            total_time=doc.get('totalTime', None)
        )

    @classmethod
    def from_record(cls, rec):
        return Timer(
            group=rec.group,
            name=rec.name,
            title=rec.title,
            description=rec.description,
            count=rec.count,
            total_time=rec.total_time
        )

    @classmethod
    def from_db(cls, r):
        if isinstance(r, dict):
            return cls.from_document(r)
        elif isinstance(r, tuple):
            return cls.from_record(r)
        else:
            return

    def _time_in_millis(self):
        return int(round(time.time() * 1000))

    def start_timer(self):
        return self._time_in_millis()

    def stop_timer(self, start, count=1):
        t = Timer.from_db(db.update_timer(Timer(
            group=self.group,
            name=self.name,
            title=self.title,
            description=self.description,
            count=count,
            total_time=(self._time_in_millis() - start)
        )))
        self.count = t.count
        self.total_time = t.total_time

    @classmethod
    def find_all(cls):
        return [Timer.from_db(timer) for timer in db.get_metrics(type='timer')]


def timer(metric):
    def decorated(f):
        @wraps(f)
        def wrapped(*args, **kwargs):
            ts = metric.start_timer()
            response = f(*args, **kwargs)
            metric.stop_timer(ts)
            return response
            # return f(*args, **kwargs)
        return wrapped
    return decorated
