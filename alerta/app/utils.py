import json
import datetime
import requests
import pytz
import re

from datetime import timedelta
from functools import wraps
from flask import make_response, request, current_app
from functools import update_wrapper

from alerta.app import app, db
from alerta.app.metrics import Timer
from alerta.plugins import load_plugins, RejectException

LOG = app.logger

plugins = load_plugins()

duplicate_timer = Timer('alerts', 'duplicate', 'Duplicate alerts', 'Total time to process number of duplicate alerts')
correlate_timer = Timer('alerts', 'correlate', 'Correlated alerts', 'Total time to process number of correlated alerts')
create_timer = Timer('alerts', 'create', 'Newly created alerts', 'Total time to process number of new alerts')


class DateEncoder(json.JSONEncoder):
    def default(self, obj):

        if isinstance(obj, (datetime.date, datetime.datetime)):
            return obj.replace(microsecond=0).strftime('%Y-%m-%dT%H:%M:%S') + ".%03dZ" % (obj.microsecond // 1000)
        else:
            return json.JSONEncoder.default(self, obj)


# Over-ride jsonify to support Date Encoding
def jsonify(*args, **kwargs):
    return current_app.response_class(json.dumps(dict(*args, **kwargs), cls=DateEncoder,
                                                 indent=None if request.is_xhr else 2), mimetype='application/json')


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


def authenticate():
    return jsonify(status="error", message="authentication required"), 401


def verify_token(token):
    if db.is_token_valid(token):
        return True

    url = 'https://www.googleapis.com/oauth2/v1/tokeninfo?access_token=' + token
    response = requests.get(url)
    token_info = response.json()

    if 'error' in token_info:
        LOG.warning('Token authentication failed: %s', token_info['error'])
        return False

    if 'audience' in token_info:
        if token_info['audience'] != app.config['OAUTH2_CLIENT_ID']:
            LOG.warning('Token supplied was for different web application')
            return False

    if 'email' in token_info:
        if not ('*' in app.config['ALLOWED_EMAIL_DOMAINS']
                or token_info['email'].split('@')[1] in app.config['ALLOWED_EMAIL_DOMAINS']
                or db.is_user_valid(token_info['email'])):
            LOG.info('User %s not authorized to access API', token_info['email'])
            return False
    else:
        LOG.warning('No email address present in token info')
        return False

    db.save_token(token)
    return True


def verify_api_key(key):
    if not db.is_key_valid(key):
        return False
    db.update_key(key)
    return True


def get_user_info(token):
    url = 'https://www.googleapis.com/oauth2/v1/userinfo?access_token=' + token
    response = requests.get(url)
    user_info = response.json()

    if 'error' in user_info:
        LOG.warning('Token authentication failed: %s', user_info['error'])
        return None

    return user_info


def auth_required(func):
    @wraps(func)
    def decorated(*args, **kwargs):

        if not app.config['AUTH_REQUIRED']:
            return func(*args, **kwargs)

        if 'Authorization' in request.headers:
            auth = request.headers['Authorization']
            if auth.startswith('Token'):
                token = auth.replace('Token ', '')
                if not verify_token(token):
                    return authenticate()
            elif auth.startswith('Key'):
                key = auth.replace('Key ', '')
                if not verify_api_key(key):
                    return authenticate()
            else:
                return authenticate()
        elif 'token' in request.args:
            token = request.args['token']
            if not verify_token(token):
                return authenticate()
        elif 'api-key' in request.args:
            key = request.args['api-key']
            if not verify_api_key(key):
                return authenticate()
        else:
            return authenticate()
        return func(*args, **kwargs)
    return decorated


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

    if params.get('from-date', None):
        try:
            from_date = datetime.datetime.strptime(params['from-date'], '%Y-%m-%dT%H:%M:%S.%fZ')
        except ValueError, e:
            LOG.warning('Could not parse from_date query parameter: %s', e)
            raise
        from_date = from_date.replace(tzinfo=pytz.utc)
        to_date = query_time
        to_date = to_date.replace(tzinfo=pytz.utc)
        query['lastReceiveTime'] = {'$gt': from_date, '$lte': to_date}
        del params['from-date']

    if params.get('id', None):
        query['$or'] = [{'_id': {'$regex': '^' + params['id']}},
                        {'lastReceiveId': {'$regex': '^' + params['id']}}]
        del params['id']

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

    return query, sort, group, limit, query_time


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


def process_alert(incomingAlert):

    for plugin in plugins:
        try:
            incomingAlert = plugin.pre_receive(incomingAlert)
        except RejectException:
            raise
        except Exception as e:
            raise RuntimeError('Error while running pre-receive plug-in: %s', e)
        if not incomingAlert:
            raise SyntaxError('Plug-in pre-receive hook did not return modified alert')

    try:
        if db.is_duplicate(incomingAlert):
            started = duplicate_timer.start_timer()
            alert = db.save_duplicate(incomingAlert)
            duplicate_timer.stop_timer(started)
        elif db.is_correlated(incomingAlert):
            started = correlate_timer.start_timer()
            alert = db.save_correlated(incomingAlert)
            correlate_timer.stop_timer(started)
        else:
            started = create_timer.start_timer()
            alert = db.create_alert(incomingAlert)
            create_timer.stop_timer(started)
    except Exception as e:
        raise RuntimeError(e)

    for plugin in plugins:
        try:
            plugin.post_receive(alert)
        except Exception as e:
            raise RuntimeError('Error while running post-receive plug-in: %s', e)

    return alert
