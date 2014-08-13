import json
import datetime
import requests

from collections import defaultdict
from functools import wraps
from flask import request, current_app, render_template, redirect, abort

from alerta.app import app, db, status_code
from alerta.app.switch import Switch
from alerta.app.utils import parse_fields, crossdomain
from alerta.app.metrics import Timer
from alerta.alert import Alert
from alerta.heartbeat import Heartbeat
from alerta.plugins import load_plugins

LOG = app.logger

@app.before_first_request
def setup():
    global plugins
    plugins = load_plugins()
    LOG.debug('Loaded plug-ins: %s', plugins)


# Set-up metrics
gets_timer = Timer('alerts', 'queries', 'Alert queries', 'Total time to process number of alert queries')
receive_timer = Timer('alerts', 'received', 'Received alerts', 'Total time to process number of received alerts')
duplicate_timer = Timer('alerts', 'duplicate', 'Duplicate alerts', 'Total time to process number of duplicate alerts')
correlate_timer = Timer('alerts', 'correlate', 'Correlated alerts', 'Total time to process number of correlated alerts')
create_timer = Timer('alerts', 'create', 'Newly created alerts', 'Total time to process number of new alerts')
delete_timer = Timer('alerts', 'deleted', 'Deleted alerts', 'Total time to process number of deleted alerts')
status_timer = Timer('alerts', 'status', 'Alert status change', 'Total time and number of alerts with status changed')
tag_timer = Timer('alerts', 'tagged', 'Tagging alerts', 'Total time to tag number of alerts')
untag_timer = Timer('alerts', 'untagged', 'Removing tags from alerts', 'Total time to un-tag number of alerts')


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


def authenticate():

    response = jsonify(status="error", message="authentication required")
    response.status_code = 401

    return response


def verify_token(token):

    if db.is_token_valid(token):
        return True

    url = 'https://www.googleapis.com/oauth2/v1/tokeninfo?access_token=' + token
    response = requests.get(url)
    token_info = response.json()
    LOG.debug('Token info %s', json.dumps(token_info))

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

    LOG.debug('we got a api key %s, verify key internally', key)

    if not db.is_key_valid(key):
        return False

    db.update_key(key)
    return True


def get_user_info(token):

    url = 'https://www.googleapis.com/oauth2/v1/userinfo?access_token=' + token
    response = requests.get(url)
    user_info = response.json()
    LOG.debug('User info %s', json.dumps(user_info))

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
            LOG.debug(auth)
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


@app.route('/_', methods=['OPTIONS', 'PUT', 'POST', 'DELETE', 'GET'])
@crossdomain(origin='*', headers=['Origin', 'X-Requested-With', 'Content-Type', 'Accept'])
@jsonp
def test():

    return jsonify(
        status="ok",
        method=request.method,
        json=request.json,
        data=request.data,
        args=request.args,
        app_root=app.root_path,
    )

@app.route('/')
def root():
    return redirect('/api', code=302)

@app.route('/api', methods=['GET'])
def index():

    rules = []
    for rule in app.url_map.iter_rules():
        if rule.endpoint not in ['test', 'static']:
            rules.append(rule)
    return render_template('index.html', rules=rules)


@app.route('/api/alerts', methods=['OPTIONS', 'GET'])
@crossdomain(origin='*', headers=['Origin', 'X-Requested-With', 'Content-Type', 'Accept', 'Authorization'])
@auth_required
@jsonp
def get_alerts():

    gets_started = gets_timer.start_timer()
    try:
        query, sort, _, limit, query_time = parse_fields(request)
    except Exception, e:
        gets_timer.stop_timer(gets_started)
        return jsonify(status="error", message=str(e))

    fields = dict()
    fields['history'] = {'$slice': app.config['HISTORY_LIMIT']}

    if 'status' not in query:
        query['status'] = {'$ne': "expired"}  # hide expired if status not in query

    alerts = db.get_alerts(query=query, fields=fields, sort=sort, limit=limit)
    total = db.get_count(query=query)  # because total may be greater than limit

    found = 0
    severity_count = defaultdict(int)
    status_count = defaultdict(int)

    alert_response = list()
    if len(alerts) > 0:

        last_time = None

        for alert in alerts:
            body = alert.get_body()
            found += 1
            severity_count[body['severity']] += 1
            status_count[body['status']] += 1

            if not last_time:
                last_time = body['lastReceiveTime']
            elif body['lastReceiveTime'] > last_time:
                last_time = body['lastReceiveTime']

            alert_response.append(body)

        gets_timer.stop_timer(gets_started)
        return jsonify(
            status="ok",
            total=found,
            more=total > limit,
            alerts=alert_response,
            severityCounts=severity_count,
            statusCounts=status_count,
            lastTime=last_time,
            autoRefresh=Switch.get('auto-refresh-allow').is_on(),
        )
    else:
        gets_timer.stop_timer(gets_started)
        return jsonify(
            status="ok",
            message="not found",
            total=0,
            more=False,
            alerts=[],
            severityCounts=severity_count,
            statusCounts=status_count,
            lastTime=query_time,
            autoRefresh=Switch.get('auto-refresh-allow').is_on()
        )

@app.route('/api/alerts/history', methods=['OPTIONS', 'GET'])
@crossdomain(origin='*', headers=['Origin', 'X-Requested-With', 'Content-Type', 'Accept', 'Authorization'])
@auth_required
@jsonp
def get_history():

    try:
        query, _, _, limit, query_time = parse_fields(request)
    except Exception, e:
        return jsonify(status="error", message=str(e))

    history = db.get_history(query=query, limit=limit)

    if len(history) > 0:
        return jsonify(
            status="ok",
            history=history,
            lastTime=history[-1]['updateTime']
        )
    else:
        return jsonify(
            status="ok",
            message="not found",
            history=[],
            lastTIme=query_time
        )

@app.route('/api/alert', methods=['OPTIONS', 'POST'])
@crossdomain(origin='*', headers=['Origin', 'X-Requested-With', 'Content-Type', 'Accept', 'Authorization'])
@auth_required
@jsonp
def receive_alert():
    #
    # A received alert can result in a duplicate, correlated or new alert
    #

    recv_started = receive_timer.start_timer()
    try:
        incomingAlert = Alert.parse_alert(request.data)
    except ValueError, e:
        receive_timer.stop_timer(recv_started)
        return jsonify(status="error", message=str(e))

    if incomingAlert:
        for plugin in plugins:
            try:
                error = plugin.pre_receive(incomingAlert)
                if error:
                    return jsonify(status="error", message=error)
            except Exception as e:
                LOG.warning('Error while running pre-receive plug-in: %s', e)

    try:
        if db.is_duplicate(incomingAlert):

            started = duplicate_timer.start_timer()
            alert = db.save_duplicate(incomingAlert)
            duplicate_timer.stop_timer(started)

            for plugin in plugins:
                try:
                    plugin.post_receive(alert)
                except Exception as e:
                    LOG.warning('Error while running post-receive plug-in: %s', e)

        elif db.is_correlated(incomingAlert):

            started = correlate_timer.start_timer()
            alert = db.save_correlated(incomingAlert)
            correlate_timer.stop_timer(started)

            for plugin in plugins:
                try:
                    plugin.post_receive(alert)
                except Exception as e:
                    LOG.warning('Error while running post-receive plug-in: %s', e)

        else:
            started = create_timer.start_timer()
            alert = db.create_alert(incomingAlert)
            create_timer.stop_timer(started)

            for plugin in plugins:
                try:
                    plugin.post_receive(alert)
                except Exception as e:
                    LOG.warning('Error while running post-receive plug-in: %s', e)

        receive_timer.stop_timer(recv_started)

    except Exception, e:
        return jsonify(status="error", message=str(e))

    if alert:
        return jsonify(status="ok", id=alert.id)
    else:
        return jsonify(status="error", message="alert insert or update failed")


@app.route('/api/alert/<id>', methods=['OPTIONS', 'GET'])
@crossdomain(origin='*', headers=['Origin', 'X-Requested-With', 'Content-Type', 'Accept', 'Authorization'])
@auth_required
@jsonp
def get_alert(id):

    alert = db.get_alert(id=id)

    if alert:
        return jsonify(status="ok", total=1, alert=alert.get_body())
    else:
        return jsonify(status="ok", message="not found", total=0, alert=None)


@app.route('/api/alert/<id>/status', methods=['OPTIONS', 'POST'])
@crossdomain(origin='*', headers=['Origin', 'X-Requested-With', 'Content-Type', 'Accept', 'Authorization'])
@auth_required
@jsonp
def set_status(id):

    status_started = status_timer.start_timer()
    data = request.json

    if data and 'status' in data:
        alert = db.set_status(id=id, status=data['status'], text=data.get('text', ''))
    else:
        status_timer.stop_timer(status_started)
        return jsonify(status="error", message="no data")

    if alert:
        for plugin in plugins:
            try:
                plugin.post_receive(alert)
            except Exception as e:
                LOG.warning('Error while running post-receive plug-in: %s', e)

        status_timer.stop_timer(status_started)
        return jsonify(status="ok")
    else:
        status_timer.stop_timer(status_started)
        return jsonify(status="error", message="failed to set alert status")


@app.route('/api/alert/<id>/tag', methods=['OPTIONS', 'POST'])
@crossdomain(origin='*', headers=['Origin', 'X-Requested-With', 'Content-Type', 'Accept', 'Authorization'])
@auth_required
@jsonp
def tag_alert(id):

    tag_started = tag_timer.start_timer()
    data = request.json

    if data and 'tags' in data:
        response = db.tag_alert(id, data['tags'])
    else:
        tag_timer.stop_timer(tag_started)
        return jsonify(status="error", message="no data")

    tag_timer.stop_timer(tag_started)
    if response:
        return jsonify(status="ok")
    else:
        return jsonify(status="error", message="failed to tag alert")


@app.route('/api/alert/<id>/untag', methods=['OPTIONS', 'POST'])
@crossdomain(origin='*', headers=['Origin', 'X-Requested-With', 'Content-Type', 'Accept', 'Authorization'])
@auth_required
@jsonp
def untag_alert(id):

    untag_started = untag_timer.start_timer()
    data = request.json

    if data and 'tags' in data:
        response = db.untag_alert(id, data['tags'])
    else:
        untag_timer.stop_timer(untag_started)
        return jsonify(status="error", message="no data")

    untag_timer.stop_timer(untag_started)
    if response:
        return jsonify(status="ok")
    else:
        return jsonify(status="error", message="failed to un-tag alert")


@app.route('/api/alert/<id>', methods=['OPTIONS', 'DELETE', 'POST'])
@crossdomain(origin='*', headers=['Origin', 'X-Requested-With', 'Content-Type', 'Accept', 'Authorization'])
@auth_required
@jsonp
def delete_alert(id):

    if (request.method == 'DELETE' or
            (request.method == 'POST' and '_method' in request.json and request.json['_method'] == 'delete')):
        started = delete_timer.start_timer()
        response = db.delete_alert(id)
        delete_timer.stop_timer(started)

        if response:
            return jsonify(status="ok")
        else:
            return jsonify(status="error", message="failed to delete alert")


# Return severity and status counts
@app.route('/api/alerts/count', methods=['OPTIONS', 'GET'])
@crossdomain(origin='*', headers=['Origin', 'X-Requested-With', 'Content-Type', 'Accept', 'Authorization'])
@auth_required
@jsonp
def get_counts():

    try:
        query, _, _, _, query_time = parse_fields(request)
    except Exception, e:
        return jsonify(status="error", message=str(e))

    counts = db.get_counts(query=query)

    found = 0
    severity_count = defaultdict(int)
    status_count = defaultdict(int)

    for count in counts:
        found += 1
        severity_count[count['severity']] += 1
        status_count[count['status']] += 1

    return jsonify(
        status="ok",
        total=found,
        more=False,
        severityCounts=severity_count,
        statusCounts=status_count,
        lastTime=query_time,
        autoRefresh=Switch.get('auto-refresh-allow').is_on()
    )


@app.route('/api/alerts/top10', methods=['OPTIONS', 'GET'])
@crossdomain(origin='*', headers=['Origin', 'X-Requested-With', 'Content-Type', 'Accept', 'Authorization'])
@auth_required
@jsonp
def get_top10():

    try:
        query, _, group, _, query_time = parse_fields(request)
    except Exception, e:
        return jsonify(status="error", message=str(e))

    top10 = db.get_topn(query=query, group=group, limit=10)

    if top10:
        return jsonify(
            status="ok",
            total=len(top10),
            top10=top10
        )
    else:
        return jsonify(
            status="ok",
            message="not found",
            total=0,
            top10=[],
        )

@app.route('/api/environments', methods=['OPTIONS', 'GET'])
@crossdomain(origin='*', headers=['Origin', 'X-Requested-With', 'Content-Type', 'Accept', 'Authorization'])
@auth_required
@jsonp
def get_environments():

    try:
        query, _, _, limit, query_time = parse_fields(request)
    except Exception, e:
        return jsonify(status="error", message=str(e))

    environments = db.get_environments(query=query, limit=limit)

    if environments:
        return jsonify(
            status="ok",
            total=len(environments),
            environments=environments
        )
    else:
        return jsonify(
            status="ok",
            message="not found",
            total=0,
            environments=[],
        )


@app.route('/api/services', methods=['OPTIONS', 'GET'])
@crossdomain(origin='*', headers=['Origin', 'X-Requested-With', 'Content-Type', 'Accept', 'Authorization'])
@auth_required
@jsonp
def get_services():

    try:
        query, _, _, limit, query_time = parse_fields(request)
    except Exception, e:
        return jsonify(status="error", message=str(e))

    services = db.get_services(query=query, limit=limit)

    if services:
        return jsonify(
            status="ok",
            total=len(services),
            services=services
        )
    else:
        return jsonify(
            status="ok",
            message="not found",
            total=0,
            services=[],
        )

@app.route('/api/pagerduty', methods=['OPTIONS', 'POST'])
@crossdomain(origin='*', headers=['Origin', 'X-Requested-With', 'Content-Type', 'Accept'])
def pagerduty():

    if not request.json or not 'messages' in request.json:
        abort(400)

    for message in request.json['messages']:

        LOG.debug('%s', json.dumps(message))

        id = message['data']['incident']['incident_key']
        html_url = message['data']['incident']['html_url']
        incident_number = message['data']['incident']['incident_number']
        incident_url = '<a href="%s">#%s</a>' % (html_url, incident_number)

        LOG.info('PagerDuty incident #%s webhook for alert %s', incident_number, id)

        LOG.error('previous status %s', db.get_alert(id=id).status)

        if message['type'] == 'incident.trigger':
            status = status_code.OPEN
            user = message['data']['incident']['assigned_to_user']['name']
            text = 'Incident %s assigned to %s' % (incident_url, user)
        elif message['type'] == 'incident.acknowledge':
            status = status_code.ACK
            user = message['data']['incident']['assigned_to_user']['name']
            text = 'Incident %s acknowledged by %s' % (incident_url, user)
        elif message['type'] == 'incident.unacknowledge':
            status = status_code.OPEN
            text = 'Incident %s unacknowledged due to timeout' % incident_url
        elif message['type'] == 'incident.resolve':
            status = status_code.CLOSED
            if message['data']['incident']['resolved_by_user']:
                user = message['data']['incident']['resolved_by_user']['name']
            else:
                user = 'n/a'
            text = 'Incident %s resolved by %s' % (incident_url, user)
        elif message['type'] == 'incident.assign':
            status = status_code.ASSIGN
            user = message['data']['incident']['assigned_to_user']['name']
            text = 'Incident %s manually assigned to %s' % (incident_url, user)
        elif message['type'] == 'incident.escalate':
            status = status_code.OPEN
            user = message['data']['incident']['assigned_to_user']['name']
            text = 'Incident %s escalated to %s' % (incident_url, user)
        elif message['type'] == 'incident.delegate':
            status = status_code.OPEN
            user = message['data']['incident']['assigned_to_user']['name']
            text = 'Incident %s reassigned due to escalation to %s' % (incident_url, user)
        else:
            status = status_code.UNKNOWN
            text = message['type']
            LOG.warn('Unknown PagerDuty message type: %s', message)

        LOG.info('PagerDuty webhook %s change status to %s', message['type'], status)

        alert = db.update_status(id=id, status=status, text=text)
        db.tag_alert(id=id, tags='incident=#%s' % incident_number)

        LOG.error('returned status %s', alert.status)
        LOG.error('current status %s', db.get_alert(id=id).status)

        # Forward alert to notify topic and logger queue
        if alert:
            alert.origin = 'pagerduty/webhook'
            for plugin in plugins:
                try:
                    plugin.post_receive(alert)
                except Exception as e:
                    LOG.warning('Error while running post-receive plug-in: %s', e)

    return jsonify(status="ok")


# Return a list of heartbeats
@app.route('/api/heartbeats', methods=['OPTIONS', 'GET'])
@crossdomain(origin='*', headers=['Origin', 'X-Requested-With', 'Content-Type', 'Accept', 'Authorization'])
@auth_required
@jsonp
def get_heartbeats():

    heartbeats = db.get_heartbeats()
    hb_list = list()
    for hb in heartbeats:
        hb_list.append(hb.get_body())

    return jsonify(
        status="ok",
        total=len(heartbeats),
        heartbeats=hb_list,
        time=datetime.datetime.utcnow()
    )

@app.route('/api/heartbeat', methods=['OPTIONS', 'POST'])
@crossdomain(origin='*', headers=['Origin', 'X-Requested-With', 'Content-Type', 'Accept', 'Authorization'])
@auth_required
@jsonp
def create_heartbeat():

    try:
        heartbeat = Heartbeat.parse_heartbeat(request.data)
    except ValueError, e:
        return jsonify(status="error", message=str(e))

    heartbeat_id = db.save_heartbeat(heartbeat)

    return jsonify(status="ok", id=heartbeat_id)

@app.route('/api/heartbeat/<id>', methods=['OPTIONS', 'DELETE', 'POST'])
@crossdomain(origin='*', headers=['Origin', 'X-Requested-With', 'Content-Type', 'Accept', 'Authorization'])
@auth_required
@jsonp
def delete_heartbeat(id):

    if request.method == 'DELETE' or (request.method == 'POST' and request.json['_method'] == 'delete'):
        response = db.delete_heartbeat(id)

        if response:
            return jsonify(status="ok")
        else:
            return jsonify(status="error", message="failed to delete heartbeat")

@app.route('/api/users', methods=['OPTIONS', 'GET'])
@crossdomain(origin='*', headers=['Origin', 'X-Requested-With', 'Content-Type', 'Accept', 'Authorization'])
@auth_required
@jsonp
def get_users():

    users = db.get_users()

    return jsonify(
        status="ok",
        total=len(users),
        users=users,
        domains=app.config['ALLOWED_EMAIL_DOMAINS'],
        time=datetime.datetime.utcnow()
    )

@app.route('/api/user', methods=['OPTIONS', 'POST'])
@crossdomain(origin='*', headers=['Origin', 'X-Requested-With', 'Content-Type', 'Accept', 'Authorization'])
@auth_required
@jsonp
def create_user():

    if request.json and 'user' in request.json:
        user = request.json["user"]
        sponsor = request.json["sponsor"]
        data = {
            "user": user,
            "sponsor": sponsor
        }

        key = db.save_user(data)
    else:
        key = None

    if key:
        return jsonify(status="ok")
    else:
        return jsonify(status="error", message="failed to create user")

@app.route('/api/user/<user>', methods=['OPTIONS', 'DELETE', 'POST'])
@crossdomain(origin='*', headers=['Origin', 'X-Requested-With', 'Content-Type', 'Accept', 'Authorization'])
@auth_required
@jsonp
def delete_user(user):

    if request.method == 'DELETE' or (request.method == 'POST' and request.json['_method'] == 'delete'):
        response = db.delete_user(user)

        if response:
            return jsonify(status="ok")
        else:
            return jsonify(status="error", message="failed to delete user")

@app.route('/api/keys', methods=['OPTIONS', 'GET'])
@crossdomain(origin='*', headers=['Origin', 'X-Requested-With', 'Content-Type', 'Accept', 'Authorization'])
@auth_required
@jsonp
def get_keys():

    keys = db.get_keys()

    return jsonify(
        status="ok",
        total=len(keys),
        keys=keys,
        time=datetime.datetime.utcnow()
    )

@app.route('/api/keys/<user>', methods=['OPTIONS', 'GET'])
@crossdomain(origin='*', headers=['Origin', 'X-Requested-With', 'Content-Type', 'Accept', 'Authorization'])
@auth_required
@jsonp
def get_user_keys(user):

    keys = db.get_keys({"user": user})

    return jsonify(
        status="ok",
        total=len(keys),
        keys=keys,
        time=datetime.datetime.utcnow()
    )

@app.route('/api/key', methods=['OPTIONS', 'POST'])
@crossdomain(origin='*', headers=['Origin', 'X-Requested-With', 'Content-Type', 'Accept', 'Authorization'])
@auth_required
@jsonp
def create_key():

    if request.json and 'user' in request.json:
        user = request.json["user"]
        data = {
            "user": user,
            "text": request.json.get("text", "API Key for %s" % user)
        }

        key = db.create_key(data)
    else:
        key = None

    if key:
        return jsonify(status="ok", key=key)
    else:
        return jsonify(status="error", message="failed to generate api key")

@app.route('/api/key/<path:key>', methods=['OPTIONS', 'DELETE', 'POST'])
@crossdomain(origin='*', headers=['Origin', 'X-Requested-With', 'Content-Type', 'Accept', 'Authorization'])
@auth_required
@jsonp
def delete_key(key):

    if request.method == 'DELETE' or (request.method == 'POST' and request.json['_method'] == 'delete'):
        response = db.delete_key(key)

        if response:
            return jsonify(status="ok")
        else:
            return jsonify(status="error", message="failed to delete api key")
