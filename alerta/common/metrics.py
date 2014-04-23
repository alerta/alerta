
import time
import threading

lock = threading.Lock()
_registry = []


class Gauge(object):

    def __init__(self, group, name, title=None, description=None):

        _registry.append(self)

        self.group = group
        self.name = name
        self.title = title
        self.description = description
        self.value = 0
        self.type = 'gauge'

    def set(self, value):

        with lock:
            self.value = value

    @classmethod
    def get_gauges(cls):

        return [
            {
                "group": gauge.group,
                "name": gauge.name,
                "title": gauge.title,
                "description": gauge.description,
                "type": gauge.type,
                "value": gauge.value,
            } for gauge in _registry if gauge.type == 'gauge'
        ]


class Counter(object):

    def __init__(self, group, name, title=None, description=None):

        _registry.append(self)

        self.group = group
        self.name = name
        self.title = title
        self.description = description
        self.count = 0
        self.type = 'counter'

    def inc(self):

        with lock:
            self.count += 1

    @classmethod
    def get_counters(cls):

        return [
            {
                "group": counter.group,
                "name": counter.name,
                "title": counter.title,
                "description": counter.description,
                "type": counter.type,
                "count": counter.count,
            } for counter in _registry if counter.type == 'counter'
        ]


class Timer(object):

    def __init__(self, group, name, title=None, description=None):

        _registry.append(self)

        self.group = group
        self.name = name
        self.title = title
        self.description = description
        self.count = 0
        self.total_time = 0
        self.type = 'timer'

        self.start = None

    @staticmethod
    def _time_in_millis():

        return int(round(time.time() * 1000))

    def start_timer(self):

        return self._time_in_millis()

    def stop_timer(self, start):

        with lock:
            self.count += 1
            self.total_time += self._time_in_millis() - start

    @classmethod
    def get_timers(cls):

        return [
            {
                "group": timer.group,
                "name": timer.name,
                "title": timer.title,
                "description": timer.description,
                "type": timer.type,
                "count": timer.count,
                "totalTime": timer.total_time,
            } for timer in _registry if timer.type == 'timer'
        ]
