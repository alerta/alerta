
import datetime

import six
from bson import ObjectId
from flask import json


class CustomJSONEncoder(json.JSONEncoder):
    def default(self, o):
        from alerta.models.alert import Alert, History
        if isinstance(o, (datetime.date, datetime.datetime)):
            return o.replace(microsecond=0).strftime('%Y-%m-%dT%H:%M:%S') + ".%03dZ" % (o.microsecond // 1000)
        elif isinstance(o, datetime.timedelta):
            return int(o.total_seconds())
        elif isinstance(o, (Alert, History)):
            return o.serialize
        elif isinstance(o, ObjectId):
            return str(o)
        else:
            return json.JSONEncoder.default(self, o)


class DateTime(object):
    @staticmethod
    def parse(date_str):
        if not isinstance(date_str, six.string_types):
            return
        try:
            return datetime.datetime.strptime(date_str, '%Y-%m-%dT%H:%M:%S.%fZ')
        except Exception:
            raise ValueError('dates must be ISO 8601 date format YYYY-MM-DDThh:mm:ss.sssZ')

    @staticmethod
    def iso8601(dt):
        return dt.replace(microsecond=0).strftime('%Y-%m-%dT%H:%M:%S') + ".%03dZ" % (dt.microsecond // 1000)
