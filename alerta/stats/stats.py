import os

import statsd

STATS_URL = os.environ['STATS_URL']
STATS_PORT = int(os.environ['STATS_PORT'])

stats_client = statsd.StatsClient(STATS_URL, STATS_PORT)


class StatsD:
    stats_client = stats_client

    @staticmethod
    def timer(stat_name, start_time, tags: dict = {}):
        stats_client.timing(stat_name, start_time, {**tags, })

    @staticmethod
    def gauge():
        pass

    @staticmethod
    def counter():
        pass

    @staticmethod
    def increment(stat_name, value, tags: dict = {}):
        stats_client.incr(stat_name, value, {**tags, })
