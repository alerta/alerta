import re
from typing import Any

ISO8601 = re.compile(r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z$')

NoneType = type(None)

TIMESTAMP = 'timestamp'
NULLABLE_TIMESTAMP = 'nullable-timestamp'

ALERT: dict[str, Any] = {
    'id': str,
    'href': str,
    'resource': str,
    'event': str,
    'environment': str,
    'severity': str,
    'correlate': list,
    'status': str,
    'service': list,
    'group': str,
    'value': (str, NoneType),
    'text': str,
    'tags': list,
    'attributes': dict,
    'origin': str,
    'type': str,
    'createTime': TIMESTAMP,
    'timeout': int,
    'rawData': (str, NoneType),
    'customer': (str, NoneType),
    'duplicateCount': int,
    'repeat': bool,
    'previousSeverity': str,
    'trendIndication': str,
    'receiveTime': TIMESTAMP,
    'lastReceiveId': str,
    'lastReceiveTime': TIMESTAMP,
    'updateTime': TIMESTAMP,
    'history': list,
}

HISTORY: dict[str, Any] = {
    'id': str,
    'href': str,
    'event': str,
    'severity': (str, NoneType),
    'status': (str, NoneType),
    'value': (str, NoneType),
    'text': str,
    'type': str,
    'updateTime': TIMESTAMP,
    'user': (str, NoneType),
    'timeout': (int, NoneType),
}

NOTE: dict[str, Any] = {
    'id': str,
    'href': str,
    'text': str,
    'user': (str, NoneType),
    'attributes': dict,
    'type': str,
    'createTime': TIMESTAMP,
    'updateTime': NULLABLE_TIMESTAMP,
    'related': dict,
    'customer': (str, NoneType),
}

HEARTBEAT: dict[str, Any] = {
    'id': str,
    'href': str,
    'origin': str,
    'tags': list,
    'attributes': dict,
    'type': str,
    'createTime': TIMESTAMP,
    'timeout': int,
    'maxLatency': int,
    'receiveTime': TIMESTAMP,
    'customer': (str, NoneType),
    'latency': int,
    'since': int,
    'status': str,
}

BLACKOUT: dict[str, Any] = {
    'id': str,
    'href': str,
    'priority': int,
    'environment': str,
    'service': list,
    'resource': (str, NoneType),
    'event': (str, NoneType),
    'group': (str, NoneType),
    'tags': list,
    'origin': (str, NoneType),
    'customer': (str, NoneType),
    'startTime': TIMESTAMP,
    'endTime': TIMESTAMP,
    'duration': int,
    'status': str,
    'user': (str, NoneType),
    'createTime': TIMESTAMP,
    'text': (str, NoneType),
}

PAGED: dict[str, Any] = {
    'status': str,
    'total': int,
    'page': int,
    'pageSize': int,
    'pages': int,
    'more': bool,
}

COUNTS: dict[str, Any] = {
    'status': str,
    'total': int,
    'severityCounts': dict,
    'statusCounts': dict,
    'autoRefresh': bool,
}

ERROR: dict[str, Any] = {
    'status': str,
    'message': str,
    'code': int,
    'errors': (list, NoneType),
    'requestId': str,
}


def assert_shape(body: Any, shape: dict[str, Any], where: str = 'body') -> None:
    assert isinstance(body, dict), f'{where}: expected object, got {type(body).__name__}'
    missing = sorted(set(shape) - set(body))
    assert not missing, f'{where}: missing keys {missing}'
    for key, expected in shape.items():
        value = body[key]
        if expected == TIMESTAMP:
            assert isinstance(value, str) and ISO8601.match(value), f'{where}.{key}: not an ISO 8601 UTC timestamp: {value!r}'
        elif expected == NULLABLE_TIMESTAMP:
            assert value is None or (isinstance(value, str) and ISO8601.match(value)), f'{where}.{key}: not a timestamp or null: {value!r}'
        else:
            assert isinstance(value, expected) and not (expected is int and isinstance(value, bool)), \
                f'{where}.{key}: expected {expected}, got {type(value).__name__} {value!r}'


def assert_error(r, code: int) -> None:
    assert r.status == code, f'expected {code}, got {r.status}: {r.json}'
    assert_shape(r.json, ERROR, 'error')
    assert r.json['status'] == 'error'
    assert r.json['code'] == code
