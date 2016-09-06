
import time

try:
    import simplejson as json
except ImportError:
    import json

from pymongo import ReturnDocument

from alerta.app import app
from alerta.app.database import Mongo


LOG = app.logger

db = Mongo().get_db()


class MetricEncoder(json.JSONEncoder):

    def default(self, o):
        return o.__dict__


class Gauge(object):

    def __init__(self, group, name, title=None, description=None, value=0):

        self.group = group
        self.name = name
        self.title = title
        self.description = description
        self.value = value

    def set(self, value):

        self.value = db.metrics.find_one_and_update(
            {
                "group": self.group,
                "name": self.name
            },
            {
                '$set': {
                    "group": self.group,
                    "name": self.name,
                    "title": self.title,
                    "description": self.description,
                    "value": value,
                    "type": "gauge"
                }
            },
            upsert=True,
            return_document=ReturnDocument.AFTER
        )['value']

    def to_json(self):
        return json.dumps(self, cls=MetricEncoder)

    @classmethod
    def get_gauges(cls, format=None):
        if format == 'json':
            return list(db.metrics.find({"type": "gauge"}, {"_id": 0}))
        elif format == 'prometheus':
            gauges = list()
            for g in Gauge.get_gauges():
                gauges.append(
                    '# HELP alerta_{group}_{name} {description}\n'
                    '# TYPE alerta_{group}_{name} gauge\n'
                    'alerta_{group}_{name} {value}\n'.format(
                            group=g.group, name=g.name, description=g.description, value=g.value
                    )
                )
            return "".join(gauges)
        else:
            return [
                Gauge(
                    group=g.get('group'),
                    name=g.get('name'),
                    title=g.get('title', ''),
                    description=g.get('description', ''),
                    value=g.get('value', 0)
                ) for g in db.metrics.find({"type": "gauge"}, {"_id": 0})
            ]


class Counter(object):

    def __init__(self, group, name, title=None, description=None, count=0):

        self.group = group
        self.name = name
        self.title = title
        self.description = description
        self.count = count

    def inc(self, count=1):

        self.count = db.metrics.find_one_and_update(
            {
                "group": self.group,
                "name": self.name
            },
            {
                '$set': {
                    "group": self.group,
                    "name": self.name,
                    "title": self.title,
                    "description": self.description,
                    "type": "counter"
                },
                '$inc': {"count": count}
            },
            upsert=True,
            return_document=ReturnDocument.AFTER
        )['count']

    def to_json(self):
        return json.dumps(self, cls=MetricEncoder)

    @classmethod
    def get_counters(cls, format=None):
        if format == 'json':
            return list(db.metrics.find({"type": "counter"}, {"_id": 0}))
        elif format == 'prometheus':
            counters = list()
            for c in Counter.get_counters():
                counters.append(
                    '# HELP alerta_{group}_{name} {description}\n'
                    '# TYPE alerta_{group}_{name} counter\n'
                    'alerta_{group}_{name}_total {count}\n'.format(
                            group=c.group, name=c.name, description=c.description, count=c.count
                    )
                )
            return "".join(counters)
        else:
            return [
                Counter(
                    group=c.get('group'),
                    name=c.get('name'),
                    title=c.get('title', ''),
                    description=c.get('description', ''),
                    count=c.get('count', 0)
                ) for c in db.metrics.find({"type": "counter"}, {"_id": 0})
            ]


class Timer(object):

    def __init__(self, group, name, title=None, description=None, count=0, total_time=0):

        self.group = group
        self.name = name
        self.title = title
        self.description = description

        self.start = None
        self.count = count
        self.total_time = total_time

    @staticmethod
    def _time_in_millis():

        return int(round(time.time() * 1000))

    def start_timer(self):

        return self._time_in_millis()

    def stop_timer(self, start, count=1):

        now = self._time_in_millis()

        r = db.metrics.find_one_and_update(
            {
                "group": self.group,
                "name": self.name
            },
            {
                '$set': {
                    "group": self.group,
                    "name": self.name,
                    "title": self.title,
                    "description": self.description,
                    "type": "timer"
                },
                '$inc': {"count": 1, "totalTime": now - start}
            },
            upsert=True,
            return_document=ReturnDocument.AFTER
        )
        self.count, self.total_time = r['count'], r['totalTime']

    def to_json(self):
        return json.dumps(self, cls=MetricEncoder)

    @classmethod
    def get_timers(cls, format=None):
        if format == 'json':
            return list(db.metrics.find({"type": "timer"}, {"_id": 0}))
        elif format == 'prometheus':
            timers = list()
            for t in Timer.get_timers():
                timers.append(
                    '# HELP alerta_{group}_{name} {description}\n'
                    '# TYPE alerta_{group}_{name} summary\n'
                    'alerta_{group}_{name}_count {count}\n'
                    'alerta_{group}_{name}_sum {total_time}\n'.format(
                            group=t.group, name=t.name, description=t.description, count=t.count, total_time=t.total_time
                    )
                )
            return "".join(timers)
        else:
            return [
                Timer(
                    group=t.get('group'),
                    name=t.get('name'),
                    title=t.get('title', ''),
                    description=t.get('description', ''),
                    count=t.get('count', 0),
                    total_time=t.get('totalTime', 0)
                ) for t in db.metrics.find({"type": "timer"}, {"_id": 0})
            ]
