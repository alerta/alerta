
import datetime
import pytz
import re

try:
    import simplejson as json
except ImportError:
    import json

from functools import wraps
from flask import request, g, current_app

try:
    from urllib.parse import urljoin
except ImportError:
    from urlparse import urljoin

from alerta.app import app, db
from alerta.app.metrics import Counter, Timer
from alerta.plugins import Plugins, RejectException

LOG = app.logger

plugins = Plugins()

reject_counter = Counter('alerts', 'rejected', 'Rejected alerts', 'Number of rejected alerts')
error_counter = Counter('alerts', 'errored', 'Errored alerts', 'Number of errored alerts')
duplicate_timer = Timer('alerts', 'duplicate', 'Duplicate alerts', 'Total time to process number of duplicate alerts')
correlate_timer = Timer('alerts', 'correlate', 'Correlated alerts', 'Total time to process number of correlated alerts')
create_timer = Timer('alerts', 'create', 'Newly created alerts', 'Total time to process number of new alerts')
pre_plugin_timer = Timer('plugins', 'prereceive', 'Pre-receive plugins', 'Total number of pre-receive plugins')
post_plugin_timer = Timer('plugins', 'postreceive', 'Post-receive plugins', 'Total number of post-receive plugins')


def jsonp(func):
    """Wraps JSONified output for JSONP requests."""
    @wraps(func)
    def decorated(*args, **kwargs):
        callback = request.args.get('callback', False)
        if callback:
            data = str(func(*args, **kwargs).data)
            content = str(callback) + '(' + data + ')'
            mimetype = 'application/javascript'
            return current_app.response_class(content, mimetype=mimetype)
        else:
            return func(*args, **kwargs)
    return decorated


def absolute_url(path=''):
    return urljoin(request.base_url.rstrip('/'), app.config.get('BASE_URL', '') + path)


PARAMS_EXCLUDE = [
    '_',
    'callback',
    'token',
    'api-key'
]


def parse_fields(r):

    query_time = datetime.datetime.utcnow()

    params = r.args.copy()

    for s in PARAMS_EXCLUDE:
        if s in params:
            del params[s]

    if params.get('q', None):
        query = json.loads(params['q'])
        del params['q']
    else:
        query = dict()

    if g.get('customer', None):
        query['customer'] = g.get('customer')

    page = params.get('page', 1)
    if 'page' in params:
        del params['page']
    page = int(page)

    if params.get('from-date', None):
        try:
            from_date = datetime.datetime.strptime(params['from-date'], '%Y-%m-%dT%H:%M:%S.%fZ')
        except ValueError as e:
            LOG.warning('Could not parse from-date query parameter: %s', e)
            raise
        from_date = from_date.replace(tzinfo=pytz.utc)
        del params['from-date']
    else:
        from_date = None

    if params.get('to-date', None):
        try:
            to_date = datetime.datetime.strptime(params['to-date'], '%Y-%m-%dT%H:%M:%S.%fZ')
        except ValueError as e:
            LOG.warning('Could not parse to-date query parameter: %s', e)
            raise
        to_date = to_date.replace(tzinfo=pytz.utc)
        del params['to-date']
    else:
        to_date = query_time
        to_date = to_date.replace(tzinfo=pytz.utc)

    if from_date and to_date:
        query['lastReceiveTime'] = {'$gt': from_date, '$lte': to_date}
    elif to_date:
        query['lastReceiveTime'] = {'$lte': to_date}

    if params.get('duplicateCount', None):
        query['duplicateCount'] = int(params.get('duplicateCount'))
        del params['duplicateCount']

    if params.get('repeat', None):
        query['repeat'] = True if params.get('repeat', 'true') == 'true' else False
        del params['repeat']

    sort = list()
    direction = 1
    if params.get('reverse', None):
        direction = -1
        del params['reverse']
    if params.get('sort-by', None):
        for sort_by in params.getlist('sort-by'):
            if sort_by in ['createTime', 'receiveTime', 'lastReceiveTime']:
                sort.append((sort_by, -direction))  # reverse chronological
            else:
                sort.append((sort_by, direction))
        del params['sort-by']
    else:
        sort.append(('lastReceiveTime', -direction))

    group = list()
    if 'group-by' in params:
        group = params.get('group-by')
        del params['group-by']

    if 'limit' in params:
        limit = params.get('limit')
        del params['limit']
    else:
        limit = app.config['QUERY_LIMIT']
    limit = int(limit)

    ids = params.getlist('id')
    if len(ids) == 1:
        query['$or'] = [{'_id': {'$regex': '^' + ids[0]}}, {'lastReceiveId': {'$regex': '^' + ids[0]}}]
        del params['id']
    elif ids:
        query['$or'] = [{'_id': {'$regex': re.compile('|'.join(['^' + i for i in ids]))}}, {'lastReceiveId': {'$regex': re.compile('|'.join(['^' + i for i in ids]))}}]
        del params['id']

    if 'fields' in params:
        fields = dict([(field, True) for field in params.get('fields').split(',')])
        fields.update({'resource': True, 'event': True, 'environment': True, 'createTime': True, 'receiveTime': True, 'lastReceiveTime': True})
        del params['fields']
    elif 'fields!' in params:
        fields = dict([(field, False) for field in params.get('fields!').split(',')])
        del params['fields!']
    else:
        fields = dict()

    for field in params:
        value = params.getlist(field)
        if len(value) == 1:
            value = value[0]
            if field.endswith('!'):
                if value.startswith('~'):
                    query[field[:-1]] = dict()
                    query[field[:-1]]['$not'] = re.compile(value[1:], re.IGNORECASE)
                else:
                    query[field[:-1]] = dict()
                    query[field[:-1]]['$ne'] = value
            else:
                if value.startswith('~'):
                    query[field] = dict()
                    query[field]['$regex'] = re.compile(value[1:], re.IGNORECASE)
                else:
                    query[field] = value
        else:
            if field.endswith('!'):
                if '~' in [v[0] for v in value]:
                    value = '|'.join([v.lstrip('~') for v in value])
                    query[field[:-1]] = dict()
                    query[field[:-1]]['$not'] = re.compile(value, re.IGNORECASE)
                else:
                    query[field[:-1]] = dict()
                    query[field[:-1]]['$nin'] = value
            else:
                if '~' in [v[0] for v in value]:
                    value = '|'.join([v.lstrip('~') for v in value])
                    query[field] = dict()
                    query[field]['$regex'] = re.compile(value, re.IGNORECASE)
                else:
                    query[field] = dict()
                    query[field]['$in'] = value

    return query, fields, sort, group, page, limit, query_time


def process_alert(alert):

    for plugin in plugins.routing(alert):
        started = pre_plugin_timer.start_timer()
        try:
            alert = plugin.pre_receive(alert)
        except RejectException:
            reject_counter.inc()
            pre_plugin_timer.stop_timer(started)
            raise
        except Exception as e:
            error_counter.inc()
            pre_plugin_timer.stop_timer(started)
            raise RuntimeError("Error while running pre-receive plug-in '%s': %s" % (plugin.name, str(e)))
        if not alert:
            error_counter.inc()
            pre_plugin_timer.stop_timer(started)
            raise SyntaxError("Plug-in '%s' pre-receive hook did not return modified alert" % plugin.name)
        pre_plugin_timer.stop_timer(started)

    if db.is_blackout_period(alert):
        raise RuntimeWarning("Suppressed alert during blackout period")

    try:
        if db.is_duplicate(alert):
            started = duplicate_timer.start_timer()
            alert = db.save_duplicate(alert)
            duplicate_timer.stop_timer(started)
        elif db.is_correlated(alert):
            started = correlate_timer.start_timer()
            alert = db.save_correlated(alert)
            correlate_timer.stop_timer(started)
        else:
            started = create_timer.start_timer()
            alert = db.create_alert(alert)
            create_timer.stop_timer(started)
    except Exception as e:
        error_counter.inc()
        raise RuntimeError(e)

    for plugin in plugins.routing(alert):
        started = post_plugin_timer.start_timer()
        try:
            plugin.post_receive(alert)
        except Exception as e:
            error_counter.inc()
            post_plugin_timer.stop_timer(started)
            raise RuntimeError("Error while running post-receive plug-in '%s': %s" % (plugin.name, str(e)))
        post_plugin_timer.stop_timer(started)

    return alert


def process_status(alert, status, text):

    for plugin in plugins.routing(alert):
        try:
            plugin.status_change(alert, status, text)
        except RejectException:
            reject_counter.inc()
            raise
        except Exception as e:
            error_counter.inc()
            raise RuntimeError("Error while running status plug-in '%s': %s" % (plugin.name, str(e)))
