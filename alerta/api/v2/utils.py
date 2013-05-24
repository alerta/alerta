import json
import datetime
import pytz
import re

# from flask import request

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
        from_date = datetime.datetime.strptime(from_date, '%Y-%m-%dT%H:%M:%S.%fZ')
        from_date = from_date.replace(tzinfo=pytz.utc)
        to_date = query_time
        to_date = to_date.replace(tzinfo=pytz.utc)
        query['lastReceiveTime'] = {'$gt': from_date, '$lte': to_date}

    if request.args.get('id', None):
        query['$or'] = [{'_id': {'$regex': '^' + request.args['id']}},
                        {'lastReceiveId': {'$regex': '^' + request.args['id']}}]

    for field in [fields for fields in request.args if fields.lstrip('-') in ATTRIBUTES]:
        if field == 'id':
            # Don't process queries on "id" twice
            continue
        value = request.args.getlist(field)
        if len(value) == 1:
            if field.startswith('-'):
                query[field[1:]] = dict()
                query[field[1:]]['$not'] = re.compile(value[0])
            else:
                query[field] = dict()
                query[field]['$regex'] = value[0]
                query[field]['$options'] = 'i'  # case insensitive search
        else:
            if field.startswith('-'):
                query[field[1:]] = dict()
                query[field[1:]]['$nin'] = value
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
