
from threading import Lock


class Gauge(object):

    _registry = []

    def __init__(self, group, name, title=None, description=None):

        self._registry.append(self)

        self.group = group
        self.name = name
        self.title = title
        self.description = description
        self.value = 0

        self.lock = Lock()

    def set(self, value):

        with self.lock:
            self.value = value

    @classmethod
    def get_metrics(cls):

        metrics = list()

        for gauge in cls._registry:
            metrics.append({
                "group": gauge.group,
                "name": gauge.name,
                "title": gauge.title,
                "description": gauge.description,
                "type": "gauge",
                "value": gauge.value
            })
        return metrics


class Counter(object):

    _registry = []

    def __init__(self, group, name, title=None, description=None):

        self._registry.append(self)

        self.group = group
        self.name = name
        self.title = title
        self.description = description
        self.count = 0

        self.lock = Lock()

    def inc(self):

        with self.lock:
            self.count += 1

    @classmethod
    def get_metrics(cls):

        metrics = list()

        for counter in cls._registry:
            metrics.append({
                "group": counter.group,
                "name": counter.name,
                "title": counter.title,
                "description": counter.description,
                "type": "counter",
                "count": counter.count
            })
        return metrics


class Timer(object):

    _registry = []

    def __init__(self, group, name, title=None, description=None):

        self._registry.append(self)

        self.group = group
        self.name = name
        self.title = title
        self.description = description
        self.count = 0
        self.total_time = 0

        self.lock = Lock()

    def time(self, duration):

        with self.lock:
            self.count += 1
            self.total_time += duration

    @classmethod
    def get_metrics(cls):

        metrics = list()

        for timer in cls._registry:
            metrics.append({
                "group": timer.group,
                "name": timer.name,
                "title": timer.title,
                "description": timer.description,
                "type": "timer",
                "count": timer.count,
                "totalTime": timer.total_time
            })
        return metrics
