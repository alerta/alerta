import json
import datetime
import pytz
import re

from datetime import timedelta
from flask import make_response, request, current_app
from functools import update_wrapper

from alerta.common import config
from alerta.common import log as logging
from alerta.common.alert import ATTRIBUTES

LOG = logging.getLogger(__name__)
CONF = config.CONF


def parse_fields(request):

    query_time = datetime.datetime.utcnow()

    if 'q' in request.args:
        query = json.loads(request.args.get('q'))
    else:
        query = dict()

    from_date = request.args.get('from-date', None)
    if from_date:
        try:
            from_date = datetime.datetime.strptime(from_date, '%Y-%m-%dT%H:%M:%S.%fZ')
        except ValueError, e:
            LOG.warning('Could not parse from_date query parameter: %s', e)
            raise
        from_date = from_date.replace(tzinfo=pytz.utc)
        to_date = query_time
        to_date = to_date.replace(tzinfo=pytz.utc)
        query['lastReceiveTime'] = {'$gt': from_date, '$lte': to_date}

    if request.args.get('id', None):
        query['$or'] = [{'_id': {'$regex': '^' + request.args['id']}},
                        {'lastReceiveId': {'$regex': '^' + request.args['id']}}]

    if request.args.get('repeat', None):
        query['repeat'] = True if request.args.get('repeat', 'true') == 'true' else False

    for field in [fields for fields in request.args if fields.rstrip('!') in ATTRIBUTES]:
        if field in ['id', 'repeat']:
            # Don't process queries on "id" or "repeat" twice
            continue
        value = request.args.getlist(field)
        if len(value) == 1:
            value = value[0]
            if field.endswith('!'):
                query[field[:-1]] = dict()
                query[field[:-1]]['$not'] = re.compile(value)
            elif value.startswith('~'):
                query[field] = dict()
                query[field]['$regex'] = re.compile(value[1:], re.IGNORECASE)
                #query[field]['$options'] = 'i'  # case insensitive search
            else:
                query[field] = value
        else:
            if field.endswith('!'):
                query[field[:-1]] = dict()
                query[field[:-1]]['$nin'] = value
            elif value[0].startswith('~'):
                value[0] = value[0][1:]
                query[field] = dict()
                query[field]['$regex'] = re.compile(value, re.IGNORECASE)
                #query[field]['$options'] = 'i'  # case insensitive search
            else:
                query[field] = dict()
                query[field]['$in'] = value

    sort = list()
    if request.args.get('sort-by', None):
        for sort_by in request.args.getlist('sort-by'):
            if sort_by in ['createTime', 'receiveTime', 'lastReceiveTime']:
                sort.append((sort_by, -1))  # sort by newest first
            else:
                sort.append((sort_by, 1))  # sort by newest first
    else:
        sort.append(('lastReceiveTime', -1))

    limit = request.args.get('limit', CONF.console_limit, int)

    return query, sort, limit, query_time


def crossdomain(origin=None, methods=None, headers=None,
                max_age=21600, attach_to_all=True,
                automatic_options=True):
    if methods is not None:
        methods = ', '.join(sorted(x.upper() for x in methods))
    if headers is not None and not isinstance(headers, basestring):
        headers = ', '.join(x.upper() for x in headers)
    if not isinstance(origin, basestring):
        origin = ', '.join(origin)
    if isinstance(max_age, timedelta):
        max_age = max_age.total_seconds()

    def get_methods():
        if methods is not None:
            return methods

        options_resp = current_app.make_default_options_response()
        return options_resp.headers['allow']

    def decorator(f):
        def wrapped_function(*args, **kwargs):
            if automatic_options and request.method == 'OPTIONS':
                resp = current_app.make_default_options_response()
            else:
                resp = make_response(f(*args, **kwargs))
            if not attach_to_all and request.method != 'OPTIONS':
                return resp

            h = resp.headers

            h['Access-Control-Allow-Origin'] = origin
            h['Access-Control-Allow-Methods'] = get_methods()
            h['Access-Control-Max-Age'] = str(max_age)
            if headers is not None:
                h['Access-Control-Allow-Headers'] = headers
            return resp

        f.provide_automatic_options = False
        return update_wrapper(wrapped_function, f)
    return decorator
