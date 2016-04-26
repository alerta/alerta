import datetime

from flask import g, request, render_template
from flask.ext.cors import cross_origin
from uuid import uuid4

from alerta.app import app, db
from alerta.app.switch import Switch
from alerta.app.auth import auth_required, admin_required
from alerta.app.utils import absolute_url, jsonify, jsonp, parse_fields, process_alert
from alerta.app.metrics import Timer
from alerta.alert import Alert
from alerta.heartbeat import Heartbeat
from alerta.plugins import load_plugins, RejectException

LOG = app.logger

plugins = load_plugins()

# Set-up metrics
gets_timer = Timer('alerts', 'queries', 'Alert queries', 'Total time to process number of alert queries')
receive_timer = Timer('alerts', 'received', 'Received alerts', 'Total time to process number of received alerts')
delete_timer = Timer('alerts', 'deleted', 'Deleted alerts', 'Total time to process number of deleted alerts')
status_timer = Timer('alerts', 'status', 'Alert status change', 'Total time and number of alerts with status changed')
tag_timer = Timer('alerts', 'tagged', 'Tagging alerts', 'Total time to tag number of alerts')
untag_timer = Timer('alerts', 'untagged', 'Removing tags from alerts', 'Total time to un-tag number of alerts')


@app.route('/_', methods=['OPTIONS', 'PUT', 'POST', 'DELETE', 'GET'])
@cross_origin()
@jsonp
def test():

    return jsonify(
        status="ok",
        method=request.method,
        json=request.json,
        data=request.data.decode('utf-8'),
        args=request.args,
        app_root=app.root_path,
    )


@app.route('/')
def index():

    rules = []
    for rule in app.url_map.iter_rules():
        if rule.endpoint not in ['test', 'static']:
            rules.append(rule)
    return render_template('index.html', base_url=absolute_url(), rules=rules)


@app.route('/alerts', methods=['OPTIONS', 'GET'])
@cross_origin()
@auth_required
@jsonp
def get_alerts():

    gets_started = gets_timer.start_timer()
    try:
        query, fields, sort, _, page, limit, query_time = parse_fields(request)
    except Exception as e:
        gets_timer.stop_timer(gets_started)
        return jsonify(status="error", message=str(e)), 400

    try:
        severity_count = db.get_counts(query=query, fields={"severity": 1}, group="severity")
    except Exception as e:
        return jsonify(status="error", message=str(e)), 500

    try:
        status_count = db.get_counts(query=query, fields={"status": 1}, group="status")
    except Exception as e:
        return jsonify(status="error", message=str(e)), 500

    if limit < 1:
        return jsonify(status="error", message="page 'limit' of %s is not valid" % limit), 416

    total = sum(severity_count.values())
    pages = ((total - 1) // limit) + 1

    if total and page > pages or page < 0:
        return jsonify(status="error", message="page out of range: 1-%s" % pages), 416

    if 'history' not in fields:
        fields['history'] = {'$slice': app.config['HISTORY_LIMIT']}

    try:
        alerts = db.get_alerts(query=query, fields=fields, sort=sort, page=page, limit=limit)
    except Exception as e:
        return jsonify(status="error", message=str(e)), 500

    alert_response = list()
    if len(alerts) > 0:

        last_time = None

        for alert in alerts:
            body = alert.get_body()
            body['href'] = absolute_url('/alert/' + alert.id)

            if not last_time:
                last_time = body['lastReceiveTime']
            elif body['lastReceiveTime'] > last_time:
                last_time = body['lastReceiveTime']

            alert_response.append(body)

        gets_timer.stop_timer(gets_started)
        return jsonify(
            status="ok",
            total=total,
            page=page,
            pageSize=limit,
            pages=pages,
            more=page < pages,
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
            total=total,
            page=page,
            pageSize=limit,
            pages=pages,
            more=False,
            alerts=[],
            severityCounts=severity_count,
            statusCounts=status_count,
            lastTime=query_time,
            autoRefresh=Switch.get('auto-refresh-allow').is_on()
        )


@app.route('/alerts/history', methods=['OPTIONS', 'GET'])
@cross_origin()
@auth_required
@jsonp
def get_history():

    try:
        query, _, _, _, _, limit, query_time = parse_fields(request)
    except Exception as e:
        return jsonify(status="error", message=str(e)), 400

    try:
        history = db.get_history(query=query, limit=limit)
    except Exception as e:
        return jsonify(status="error", message=str(e)), 500

    for alert in history:
        alert['href'] = absolute_url('/alert/' + alert['id'])

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


@app.route('/alert', methods=['OPTIONS', 'POST'])
@cross_origin()
@auth_required
@jsonp
def receive_alert():

    recv_started = receive_timer.start_timer()
    try:
        incomingAlert = Alert.parse_alert(request.data)
    except ValueError as e:
        receive_timer.stop_timer(recv_started)
        return jsonify(status="error", message=str(e)), 400

    if g.get('customer', None):
        incomingAlert.customer = g.get('customer')

    if request.headers.getlist("X-Forwarded-For"):
       incomingAlert.attributes.update(ip=request.headers.getlist("X-Forwarded-For")[0])
    else:
       incomingAlert.attributes.update(ip=request.remote_addr)

    try:
        alert = process_alert(incomingAlert)
    except RejectException as e:
        receive_timer.stop_timer(recv_started)
        return jsonify(status="error", message=str(e)), 403
    except RuntimeWarning as e:
        receive_timer.stop_timer(recv_started)
        return jsonify(status="ok", id=incomingAlert.id, message=str(e)), 202
    except Exception as e:
        receive_timer.stop_timer(recv_started)
        return jsonify(status="error", message=str(e)), 500

    receive_timer.stop_timer(recv_started)

    if alert:
        body = alert.get_body()
        body['href'] = absolute_url('/alert/' + alert.id)
        return jsonify(status="ok", id=alert.id, alert=body), 201, {'Location': body['href']}
    else:
        return jsonify(status="error", message="insert or update of received alert failed"), 500


@app.route('/alert/<id>', methods=['OPTIONS', 'GET'])
@cross_origin()
@auth_required
@jsonp
def get_alert(id):

    customer = g.get('customer', None)
    try:
        alert = db.get_alert(id=id, customer=customer)
    except Exception as e:
        return jsonify(status="error", message=str(e)), 500

    if alert:
        body = alert.get_body()
        body['href'] = absolute_url('/alert/' + alert.id)
        return jsonify(status="ok", total=1, alert=body)
    else:
        return jsonify(status="error", message="not found", total=0, alert=None), 404


@app.route('/alert/<id>/status', methods=['OPTIONS', 'POST'])
@cross_origin()
@auth_required
@jsonp
def set_status(id):

    status_started = status_timer.start_timer()
    customer = g.get('customer', None)
    try:
        alert = db.get_alert(id=id, customer=customer)
    except Exception as e:
        status_timer.stop_timer(status_started)
        return jsonify(status="error", message=str(e)), 500

    if not alert:
        status_timer.stop_timer(status_started)
        return jsonify(status="error", message="not found", total=0, alert=None), 404

    status = request.json.get('status', None)
    text = request.json.get('text', '')

    if not status:
        status_timer.stop_timer(status_started)
        return jsonify(status="error", message="must supply 'status' as parameter"), 400

    for plugin in plugins:
        try:
            plugin.status_change(alert, status, text)
        except RejectException as e:
            status_timer.stop_timer(status_started)
            return jsonify(status="error", message=str(e)), 403

    try:
        alert = db.set_status(id=id, status=status, text=text)
    except Exception as e:
        status_timer.stop_timer(status_started)
        return jsonify(status="error", message=str(e)), 500

    if alert:
        status_timer.stop_timer(status_started)
        return jsonify(status="ok")
    else:
        status_timer.stop_timer(status_started)
        return jsonify(status="error", message="not found"), 404


@app.route('/alert/<id>/tag', methods=['OPTIONS', 'POST'])
@cross_origin()
@auth_required
@jsonp
def tag_alert(id):

    # FIXME - should only allow role=user to set status for alerts for that customer

    tag_started = tag_timer.start_timer()
    data = request.json

    if data and 'tags' in data:
        try:
            response = db.tag_alert(id, data['tags'])
        except Exception as e:
            return jsonify(status="error", message=str(e)), 500
    else:
        tag_timer.stop_timer(tag_started)
        return jsonify(status="error", message="must supply 'tags' as list parameter"), 400

    tag_timer.stop_timer(tag_started)
    if response:
        return jsonify(status="ok")
    else:
        return jsonify(status="error", message="not found"), 404


@app.route('/alert/<id>/untag', methods=['OPTIONS', 'POST'])
@cross_origin()
@auth_required
@jsonp
def untag_alert(id):

    # FIXME - should only allow role=user to set status for alerts for that customer

    untag_started = untag_timer.start_timer()
    data = request.json

    if data and 'tags' in data:
        try:
            response = db.untag_alert(id, data['tags'])
        except Exception as e:
            return jsonify(status="error", message=str(e)), 500
    else:
        untag_timer.stop_timer(untag_started)
        return jsonify(status="error", message="must supply 'tags' as list parameter"), 400

    untag_timer.stop_timer(untag_started)
    if response:
        return jsonify(status="ok")
    else:
        return jsonify(status="error", message="not found"), 404


@app.route('/alert/<id>', methods=['OPTIONS', 'DELETE', 'POST'])
@cross_origin()
@auth_required
@admin_required
@jsonp
def delete_alert(id):

    if (request.method == 'DELETE' or
            (request.method == 'POST' and '_method' in request.json and request.json['_method'] == 'delete')):
        started = delete_timer.start_timer()
        try:
            response = db.delete_alert(id)
        except Exception as e:
            return jsonify(status="error", message=str(e)), 500
        delete_timer.stop_timer(started)

        if response:
            return jsonify(status="ok")
        else:
            return jsonify(status="error", message="not found"), 404


# Return severity and status counts
@app.route('/alerts/count', methods=['OPTIONS', 'GET'])
@cross_origin()
@auth_required
@jsonp
def get_counts():

    try:
        query, _, _, _, _, _, _ = parse_fields(request)
    except Exception as e:
        return jsonify(status="error", message=str(e)), 400

    try:
        severity_count = db.get_counts(query=query, fields={"severity": 1}, group="severity")
    except Exception as e:
        return jsonify(status="error", message=str(e)), 500

    try:
        status_count = db.get_counts(query=query, fields={"status": 1}, group="status")
    except Exception as e:
        return jsonify(status="error", message=str(e)), 500

    if sum(severity_count.values()):
        return jsonify(
            status="ok",
            total=sum(severity_count.values()),
            severityCounts=severity_count,
            statusCounts=status_count
        )
    else:
        return jsonify(
            status="ok",
            message="not found",
            total=0,
            severityCounts=severity_count,
            statusCounts=status_count
        )


@app.route('/alerts/top10', methods=['OPTIONS', 'GET'])
@cross_origin()
@auth_required
@jsonp
def get_top10():

    try:
        query, _, _, group, _, _, _ = parse_fields(request)
    except Exception as e:
        return jsonify(status="error", message=str(e)), 400

    try:
        top10 = db.get_topn(query=query, group=group, limit=10)
    except Exception as e:
        return jsonify(status="error", message=str(e)), 500

    for item in top10:
        for resource in item['resources']:
            resource['href'] = absolute_url('/alert/' + resource['id'])

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


@app.route('/environments', methods=['OPTIONS', 'GET'])
@cross_origin()
@auth_required
@jsonp
def get_environments():

    try:
        query, _, _, _, _, limit, _ = parse_fields(request)
    except Exception as e:
        return jsonify(status="error", message=str(e)), 400

    try:
        environments = db.get_environments(query=query, limit=limit)
    except Exception as e:
        return jsonify(status="error", message=str(e)), 500

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


@app.route('/services', methods=['OPTIONS', 'GET'])
@cross_origin()
@auth_required
@jsonp
def get_services():

    try:
        query, _, _, _, _, limit, _ = parse_fields(request)
    except Exception as e:
        return jsonify(status="error", message=str(e)), 400

    try:
        services = db.get_services(query=query, limit=limit)
    except Exception as e:
        return jsonify(status="error", message=str(e)), 500

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


@app.route('/blackouts', methods=['OPTIONS', 'GET'])
@cross_origin()
@auth_required
@admin_required
@jsonp
def get_blackouts():

    try:
        blackouts = db.get_blackouts()
    except Exception as e:
        return jsonify(status="error", message=str(e)), 500

    if len(blackouts):
        return jsonify(
            status="ok",
            total=len(blackouts),
            blackouts=blackouts,
            time=datetime.datetime.utcnow()
        )
    else:
        return jsonify(
            status="ok",
            message="not found",
            total=0,
            blackouts=[],
            time=datetime.datetime.utcnow()
        )


@app.route('/blackout', methods=['OPTIONS', 'POST'])
@cross_origin()
@auth_required
@admin_required
@jsonp
def create_blackout():

    if request.json and 'environment' in request.json:
        environment = request.json['environment']
    else:
        return jsonify(status="error", message="must supply 'environment' as parameter"), 400

    resource = request.json.get("resource", None)
    service = request.json.get("service", None)
    event = request.json.get("event", None)
    group = request.json.get("group", None)
    tags = request.json.get("tags", None)
    customer = request.json.get("customer", None)
    start_time = request.json.get("startTime", None)
    end_time = request.json.get("endTime", None)
    duration = request.json.get("duration", None)

    if start_time:
        start_time = datetime.datetime.strptime(start_time, '%Y-%m-%dT%H:%M:%S.%fZ')
    if end_time:
        end_time = datetime.datetime.strptime(end_time, '%Y-%m-%dT%H:%M:%S.%fZ')

    try:
        blackout = db.create_blackout(environment, resource, service, event, group, tags, customer, start_time, end_time, duration)
    except Exception as e:
        return jsonify(status="error", message=str(e)), 500

    return jsonify(status="ok", blackout=blackout), 201, {'Location': absolute_url('/blackout/' + blackout)}


@app.route('/blackout/<path:blackout>', methods=['OPTIONS', 'DELETE', 'POST'])
@cross_origin()
@auth_required
@admin_required
@jsonp
def delete_blackout(blackout):

    if request.method == 'DELETE' or (request.method == 'POST' and request.json['_method'] == 'delete'):
        try:
            response = db.delete_blackout(blackout)
        except Exception as e:
            return jsonify(status="error", message=str(e)), 500

        if response:
            return jsonify(status="ok")
        else:
            return jsonify(status="error", message="not found"), 404


@app.route('/heartbeats', methods=['OPTIONS', 'GET'])
@cross_origin()
@auth_required
@jsonp
def get_heartbeats():

    customer = g.get('customer', None)
    if customer:
        query = {'customer': customer}
    else:
        query = {}

    try:
        heartbeats = db.get_heartbeats(query)
    except Exception as e:
        return jsonify(status="error", message=str(e)), 500

    hb_list = list()
    for hb in heartbeats:
        body = hb.get_body()
        body['href'] = absolute_url('/heartbeat/' + hb.id)
        hb_list.append(body)

    if hb_list:
        return jsonify(
            status="ok",
            total=len(heartbeats),
            heartbeats=hb_list,
            time=datetime.datetime.utcnow()
        )
    else:
        return jsonify(
            status="ok",
            message="not found",
            total=0,
            heartbeats=hb_list,
            time=datetime.datetime.utcnow()
        )


@app.route('/heartbeat', methods=['OPTIONS', 'POST'])
@cross_origin()
@auth_required
@jsonp
def create_heartbeat():

    try:
        heartbeat = Heartbeat.parse_heartbeat(request.data)
    except ValueError as e:
        return jsonify(status="error", message=str(e)), 400

    if g.get('role', None) != 'admin':
        heartbeat.customer = g.get('customer', None)

    try:
        heartbeat = db.save_heartbeat(heartbeat)
    except Exception as e:
        return jsonify(status="error", message=str(e)), 500

    body = heartbeat.get_body()
    body['href'] = absolute_url('/heartbeat/' + heartbeat.id)
    return jsonify(status="ok", id=heartbeat.id, heartbeat=body), 201, {'Location': body['href']}


@app.route('/heartbeat/<id>', methods=['OPTIONS', 'GET'])
@cross_origin()
@auth_required
@jsonp
def get_heartbeat(id):

    customer = g.get('customer', None)

    try:
        heartbeat = db.get_heartbeat(id=id, customer=customer)
    except Exception as e:
        return jsonify(status="error", message=str(e)), 500

    if heartbeat:
        body = heartbeat.get_body()
        body['href'] = absolute_url('/hearbeat/' + heartbeat.id)
        return jsonify(status="ok", total=1, heartbeat=body)
    else:
        return jsonify(status="error", message="not found", total=0, heartbeat=None), 404


@app.route('/heartbeat/<id>', methods=['OPTIONS', 'DELETE', 'POST'])
@cross_origin()
@auth_required
@admin_required
@jsonp
def delete_heartbeat(id):

    if request.method == 'DELETE' or (request.method == 'POST' and request.json['_method'] == 'delete'):
        try:
            response = db.delete_heartbeat(id)
        except Exception as e:
            return jsonify(status="error", message=str(e)), 500

        if response:
            return jsonify(status="ok")
        else:
            return jsonify(status="error", message="not found"), 404


@app.route('/users', methods=['OPTIONS', 'GET'])
@cross_origin()
@auth_required
@admin_required
@jsonp
def get_users():

    user_id = request.args.get("id")
    name = request.args.get("name")
    login = request.args.get("login")

    if user_id:
        query = {'user': user_id}
    elif name:
        query = {'name': name}
    elif login:
        query = {'login': login}
    else:
        query = {}

    try:
        users = db.get_users(query)
    except Exception as e:
        return jsonify(status="error", message=str(e)), 500

    if len(users):
        return jsonify(
            status="ok",
            total=len(users),
            users=users,
            domains=app.config['ALLOWED_EMAIL_DOMAINS'],
            orgs=app.config['ALLOWED_GITHUB_ORGS'],
            groups=app.config['ALLOWED_GITLAB_GROUPS'],
            time=datetime.datetime.utcnow()
        )
    else:
        return jsonify(
            status="ok",
            message="not found",
            total=0,
            users=[],
            domains=app.config['ALLOWED_EMAIL_DOMAINS'],
            orgs=app.config['ALLOWED_GITHUB_ORGS'],
            time=datetime.datetime.utcnow()
        )


@app.route('/user', methods=['OPTIONS', 'POST'])
@cross_origin()
@auth_required
@admin_required
@jsonp
def create_user():

    if request.json and 'name' in request.json:
        name = request.json["name"]
        login = request.json["login"]
        password = request.json.get("password", None)
        provider = request.json["provider"]
        text = request.json.get("text", "")
        try:
            user_id = db.save_user(str(uuid4()), name, login, password, provider, text)
        except Exception as e:
            return jsonify(status="error", message=str(e)), 500
    else:
        return jsonify(status="error", message="must supply user 'name', 'login' and 'provider' as parameters"), 400

    if user_id:
        return jsonify(status="ok", user=user_id), 201, {'Location': absolute_url('/user/' + user_id)}
    else:
        return jsonify(status="error", message="User with that login already exists"), 409


@app.route('/user/<user>', methods=['OPTIONS', 'PUT'])
@cross_origin()
@auth_required
@admin_required
@jsonp
def update_user(user):
   
    if not request.json:
        return jsonify(status="ok", user=user, message="Nothing to update, request was empty")

    name = request.json.get('name', None)
    login = request.json.get('login', None)
    password = request.json.get('password', None)
    provider = request.json.get('provider', None)
    text = request.json.get('text', None)
    email_verified = request.json.get('email_verified', None)


    try:
        user = db.update_user(user, name=name, login=login, password=password, provider=provider,
                text=text, email_verified=email_verified)
    except Exception as e:
        return jsonify(status="error", message=str(e)), 500
    
    if user:
        return jsonify(status="ok", user=user)
    else:
        return jsonify(status="error", message="not found"), 404


@app.route('/user/<user>', methods=['OPTIONS', 'DELETE', 'POST'])
@cross_origin()
@auth_required
@admin_required
@jsonp
def delete_user(user):

    if request.method == 'DELETE' or (request.method == 'POST' and request.json['_method'] == 'delete'):
        try:
            response = db.delete_user(user)
        except Exception as e:
            return jsonify(status="error", message=str(e)), 500

        if response:
            return jsonify(status="ok")
        else:
            return jsonify(status="error", message="not found"), 404


@app.route('/customers', methods=['OPTIONS', 'GET'])
@cross_origin()
@auth_required
@admin_required
@jsonp
def get_customers():

    try:
        customers = db.get_customers()
    except Exception as e:
        return jsonify(status="error", message=str(e)), 500

    if len(customers):
        return jsonify(
            status="ok",
            total=len(customers),
            customers=customers,
            time=datetime.datetime.utcnow()
        )
    else:
        return jsonify(
            status="ok",
            message="not found",
            total=0,
            customers=[],
            time=datetime.datetime.utcnow()
        )


@app.route('/customer', methods=['OPTIONS', 'POST'])
@cross_origin()
@auth_required
@admin_required
@jsonp
def create_customer():

    if request.json and 'customer' in request.json and 'match' in request.json:
        customer = request.json["customer"]
        match = request.json["match"]
        try:
            cid = db.create_customer(customer, match)
        except Exception as e:
            return jsonify(status="error", message=str(e)), 500
    else:
        return jsonify(status="error", message="must supply user 'customer' and 'match' as parameters"), 400

    if cid:
        return jsonify(status="ok", id=cid), 201, {'Location': absolute_url('/customer/' + cid)}
    else:
        return jsonify(status="error", message="Customer lookup for this match already exists"), 409


@app.route('/customer/<customer>', methods=['OPTIONS', 'DELETE', 'POST'])
@cross_origin()
@auth_required
@admin_required
@jsonp
def delete_customer(customer):

    if request.method == 'DELETE' or (request.method == 'POST' and request.json['_method'] == 'delete'):
        try:
            response = db.delete_customer(customer)
        except Exception as e:
            return jsonify(status="error", message=str(e)), 500

        if response:
            return jsonify(status="ok")
        else:
            return jsonify(status="error", message="not found"), 404


@app.route('/keys', methods=['OPTIONS', 'GET'])
@cross_origin()
@auth_required
@jsonp
def get_keys():

    if g.get('role', None) == 'admin':
        try:
            keys = db.get_keys()
        except Exception as e:
            return jsonify(status="error", message=str(e)), 500
    else:
        user = g.get('user')
        try:
            keys = db.get_user_keys(user)
        except Exception as e:
            return jsonify(status="error", message=str(e)), 500

    if keys:
        return jsonify(
            status="ok",
            total=len(keys),
            keys=keys,
            time=datetime.datetime.utcnow()
        )
    else:
        return jsonify(
            status="ok",
            message="not found",
            total=0,
            keys=[],
            time=datetime.datetime.utcnow()
        )


@app.route('/key', methods=['OPTIONS', 'POST'])
@cross_origin()
@auth_required
@jsonp
def create_key():

    try:
        if g.get('role', None) != 'admin':
            user = g.user
            customer = g.get('customer', None)
        else:
            user = request.json.get('user', g.user)
            customer = request.json.get('customer', None)
    except AttributeError:
        return jsonify(status="error", message="Must supply 'user' as parameter"), 400

    type = request.json.get("type", "read-only")
    if type not in ['read-only', 'read-write']:
        return jsonify(status="error", message="API key 'type' must be 'read-only' or 'read-write'"), 400

    text = request.json.get("text", "API Key for %s" % user)
    try:
        key = db.create_key(user, type, customer, text)
    except Exception as e:
        return jsonify(status="error", message=str(e)), 500

    return jsonify(status="ok", key=key), 201, {'Location': absolute_url('/key/' + key)}


@app.route('/key/<path:key>', methods=['OPTIONS', 'DELETE', 'POST'])
@cross_origin()
@auth_required
@admin_required
@jsonp
def delete_key(key):

    query = {"key": key}
    if not db.get_keys(query):
        return jsonify(status="error", message="not found"), 404

    if request.method == 'DELETE' or (request.method == 'POST' and request.json['_method'] == 'delete'):
        try:
            response = db.delete_key(key)
        except Exception as e:
            return jsonify(status="error", message=str(e)), 500

        if response:
            return jsonify(status="ok")
        else:
            return jsonify(status="error", message="not found"), 404
