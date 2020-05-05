import datetime
import traceback
from typing import Any, Optional

from bson import ObjectId
from flask import json

dt = datetime.datetime


class CustomJSONEncoder(json.JSONEncoder):
    def default(self, o: Any) -> Any:  # pylint: disable=method-hidden
        from alerta.models.alert import Alert, History
        if isinstance(o, datetime.datetime):
            return DateTime.iso8601(o)
        elif isinstance(o, datetime.timedelta):
            return int(o.total_seconds())
        elif isinstance(o, (Alert, History)):
            return o.serialize
        elif isinstance(o, ObjectId):
            return str(o)
        elif isinstance(o, Exception):
            return traceback.format_exception_only(o.__class__, o)
        else:
            return json.JSONEncoder.default(self, o)


class DateTime:
    @staticmethod
    def parse(date_str: str) -> Optional[dt]:
        if not isinstance(date_str, str):
            return None
        try:
            return datetime.datetime.strptime(date_str, '%Y-%m-%dT%H:%M:%S.%fZ')
        except Exception:
            raise ValueError('dates must be ISO 8601 date format YYYY-MM-DDThh:mm:ss.sssZ')

    @staticmethod
    def iso8601(dt: dt) -> str:
        return dt.replace(microsecond=0).strftime('%Y-%m-%dT%H:%M:%S') + '.%03dZ' % (dt.microsecond // 1000)


def custom_json_dumps(obj: object) -> str:
    return json.dumps(obj, cls=CustomJSONEncoder)


def register_custom_serializer() -> None:
    from kombu.serialization import register  # pylint: disable=import-error
    register('customjson', custom_json_dumps, json.loads,
             content_type='application/x-customjson',
             content_encoding='utf-8')
