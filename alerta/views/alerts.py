
from datetime import datetime

from flask import g, jsonify, request
from flask_cors import cross_origin

from alerta.app import qb
from alerta.auth.decorators import permission
from alerta.exceptions import (ApiError, BlackoutPeriod, RateLimit,
                               RejectException)
from alerta.models.alert import Alert
from alerta.models.metrics import Timer, timer
from alerta.models.switch import Switch
from alerta.utils.api import (add_remote_ip, assign_customer, process_action,
                              process_alert, process_status)
from alerta.utils.paging import Page
from alerta.utils.response import jsonp

from . import api

receive_timer = Timer('alerts', 'received', 'Received alerts', 'Total time and number of received alerts')
gets_timer = Timer('alerts', 'queries', 'Alert queries', 'Total time and number of alert queries')
status_timer = Timer('alerts', 'status', 'Alert status change', 'Total time and number of alerts with status changed')
tag_timer = Timer('alerts', 'tagged', 'Tagging alerts', 'Total time to tag number of alerts')
untag_timer = Timer('alerts', 'untagged', 'Removing tags from alerts', 'Total time to un-tag and number of alerts')
attrs_timer = Timer('alerts', 'attributes', 'Alert attributes change',
                    'Total time and number of alerts with attributes changed')
delete_timer = Timer('alerts', 'deleted', 'Deleted alerts', 'Total time and number of deleted alerts')
count_timer = Timer('alerts', 'counts', 'Count alerts', 'Total time and number of count queries')


@api.route('/alert', methods=['OPTIONS', 'POST'])
@cross_origin()
@permission('write:alerts')
@timer(receive_timer)
@jsonp
def receive():
    try:
        incomingAlert = Alert.parse(request.json)
    except ValueError as e:
        raise ApiError(str(e), 400)

    incomingAlert.customer = assign_customer(wanted=incomingAlert.customer)
    add_remote_ip(request, incomingAlert)

    try:
        alert = process_alert(incomingAlert)
    except RejectException as e:
        raise ApiError(str(e), 403)
    except RateLimit as e:
        return jsonify(status='error', message=str(e), id=incomingAlert.id), 429
    except BlackoutPeriod as e:
        return jsonify(status='ok', message=str(e), id=incomingAlert.id), 202
    except Exception as e:
        raise ApiError(str(e), 500)

    if alert:
        return jsonify(status='ok', id=alert.id, alert=alert.serialize), 201
    else:
        raise ApiError('insert or update of received alert failed', 500)


@api.route('/alert/<alert_id>', methods=['OPTIONS', 'GET'])
@cross_origin()
@permission('read:alerts')
@timer(gets_timer)
@jsonp
def get_alert(alert_id):
    customers = g.get('customers', None)
    alert = Alert.find_by_id(alert_id, customers)

    if alert:
        return jsonify(status='ok', total=1, alert=alert.serialize)
    else:
        raise ApiError('not found', 404)


# set status
@api.route('/alert/<alert_id>/status', methods=['OPTIONS', 'PUT'])
@cross_origin()
@permission('write:alerts')
@timer(status_timer)
@jsonp
def set_status(alert_id):
    status = request.json.get('status', None)
    text = request.json.get('text', '')
    timeout = request.json.get('timeout', None)

    if not status:
        raise ApiError("must supply 'status' as json data", 400)

    customers = g.get('customers', None)
    alert = Alert.find_by_id(alert_id, customers)

    if not alert:
        raise ApiError('not found', 404)

    try:
        alert, status, text = process_status(alert, status, text)
        alert = alert.from_status(status, text, timeout)
    except RejectException as e:
        raise ApiError(str(e), 400)
    except Exception as e:
        raise ApiError(str(e), 500)

    if alert:
        return jsonify(status='ok')
    else:
        raise ApiError('failed to set status', 500)


# action alert
@api.route('/alert/<alert_id>/action', methods=['OPTIONS', 'PUT'])
@cross_origin()
@permission('write:alerts')
@timer(status_timer)
@jsonp
def action_alert(alert_id):
    action = request.json.get('action', None)
    text = request.json.get('text', '%s operator action' % action)
    timeout = request.json.get('timeout', None)

    if not action:
        raise ApiError("must supply 'action' as json data", 400)

    customers = g.get('customers', None)
    alert = Alert.find_by_id(alert_id, customers)

    if not alert:
        raise ApiError('not found', 404)

    try:
        previous_status = alert.status
        alert, action, text = process_action(alert, action, text)
        alert = alert.from_action(action, text, timeout)
    except RejectException as e:
        raise ApiError(str(e), 400)
    except Exception as e:
        raise ApiError(str(e), 500)

    if previous_status != alert.status:
        try:
            alert, status, text = process_status(alert, alert.status, text)
        except RejectException as e:
            raise ApiError(str(e), 400)
        except Exception as e:
            raise ApiError(str(e), 500)

    if alert:
        return jsonify(status='ok')
    else:
        raise ApiError('failed to action alert', 500)


# tag
@api.route('/alert/<alert_id>/tag', methods=['OPTIONS', 'PUT'])
@cross_origin()
@permission('write:alerts')
@timer(tag_timer)
@jsonp
def tag_alert(alert_id):
    if not request.json.get('tags', None):
        raise ApiError("must supply 'tags' as json list")

    customers = g.get('customers', None)
    alert = Alert.find_by_id(alert_id, customers)

    if not alert:
        raise ApiError('not found', 404)

    if alert.tag(tags=request.json['tags']):
        return jsonify(status='ok')
    else:
        raise ApiError('failed to tag alert', 500)


# untag
@api.route('/alert/<alert_id>/untag', methods=['OPTIONS', 'PUT'])
@cross_origin()
@permission('write:alerts')
@timer(untag_timer)
@jsonp
def untag_alert(alert_id):
    if not request.json.get('tags', None):
        raise ApiError("must supply 'tags' as json list")

    customers = g.get('customers', None)
    alert = Alert.find_by_id(alert_id, customers)

    if not alert:
        raise ApiError('not found', 404)

    if alert.untag(tags=request.json['tags']):
        return jsonify(status='ok')
    else:
        raise ApiError('failed to untag alert', 500)


# update attributes
@api.route('/alert/<alert_id>/attributes', methods=['OPTIONS', 'PUT'])
@cross_origin()
@permission('write:alerts')
@timer(attrs_timer)
@jsonp
def update_attributes(alert_id):
    if not request.json.get('attributes', None):
        raise ApiError("must supply 'attributes' as json data", 400)

    customers = g.get('customers', None)
    alert = Alert.find_by_id(alert_id, customers)

    if not alert:
        raise ApiError('not found', 404)

    if alert.update_attributes(request.json['attributes']):
        return jsonify(status='ok')
    else:
        raise ApiError('failed to update attributes', 500)


# delete
@api.route('/alert/<alert_id>', methods=['OPTIONS', 'DELETE'])
@cross_origin()
@permission('write:alerts')
@timer(delete_timer)
@jsonp
def delete_alert(alert_id):
    customers = g.get('customers', None)
    alert = Alert.find_by_id(alert_id, customers)

    if not alert:
        raise ApiError('not found', 404)

    if alert.delete():
        return jsonify(status='ok')
    else:
        raise ApiError('failed to delete alert', 500)


@api.route('/alerts', methods=['OPTIONS', 'GET'])
@cross_origin()
@permission('read:alerts')
@timer(gets_timer)
@jsonp
def search_alerts():
    query_time = datetime.utcnow()
    query = qb.from_params(request.args, query_time)
    severity_count = Alert.get_counts_by_severity(query)
    status_count = Alert.get_counts_by_status(query)

    total = sum(severity_count.values())
    paging = Page.from_params(request.args, total)

    alerts = Alert.find_all(query, paging.page, paging.page_size)

    if alerts:
        return jsonify(
            status='ok',
            page=paging.page,
            pageSize=paging.page_size,
            pages=paging.pages,
            more=paging.has_more,
            alerts=[alert.serialize for alert in alerts],
            total=total,
            statusCounts=status_count,
            severityCounts=severity_count,
            lastTime=max([alert.last_receive_time for alert in alerts]),
            autoRefresh=Switch.find_by_name('auto-refresh-allow').is_on
        )
    else:
        return jsonify(
            status='ok',
            message='not found',
            page=paging.page,
            pageSize=paging.page_size,
            pages=0,
            more=False,
            alerts=[],
            total=0,
            severityCounts=severity_count,
            statusCounts=status_count,
            lastTime=query_time,
            autoRefresh=Switch.find_by_name('auto-refresh-allow').is_on
        )


@api.route('/alerts/history', methods=['OPTIONS', 'GET'])
@cross_origin()
@permission('read:alerts')
@timer(gets_timer)
@jsonp
def history():
    query = qb.from_params(request.args)
    paging = Page.from_params(request.args, items=0)
    history = Alert.get_history(query, paging.page, paging.page_size)

    if history:
        return jsonify(
            status='ok',
            history=[h.serialize for h in history],
            total=len(history)
        )
    else:
        return jsonify(
            status='ok',
            message='not found',
            history=[],
            total=0
        )


# severity counts
# status counts
@api.route('/alerts/count', methods=['OPTIONS', 'GET'])
@cross_origin()
@permission('read:alerts')
@timer(count_timer)
@jsonp
def get_counts():
    query = qb.from_params(request.args)
    severity_count = Alert.get_counts_by_severity(query)
    status_count = Alert.get_counts_by_status(query)

    return jsonify(
        status='ok',
        total=sum(severity_count.values()),
        severityCounts=severity_count,
        statusCounts=status_count,
        autoRefresh=Switch.find_by_name('auto-refresh-allow').is_on
    )


# top 10 counts
@api.route('/alerts/top10/count', methods=['OPTIONS', 'GET'])
@cross_origin()
@permission('read:alerts')
@timer(count_timer)
@jsonp
def get_top10_count():
    query = qb.from_params(request.args)
    top10 = Alert.get_top10_count(query)

    if top10:
        return jsonify(
            status='ok',
            top10=top10,
            total=len(top10),
            autoRefresh=Switch.find_by_name('auto-refresh-allow').is_on
        )
    else:
        return jsonify(
            status='ok',
            message='not found',
            top10=[],
            total=0,
            autoRefresh=Switch.find_by_name('auto-refresh-allow').is_on
        )


# top 10 flapping
@api.route('/alerts/top10/flapping', methods=['OPTIONS', 'GET'])
@cross_origin()
@permission('read:alerts')
@timer(count_timer)
@jsonp
def get_top10_flapping():
    query = qb.from_params(request.args)
    top10 = Alert.get_top10_flapping(query)

    if top10:
        return jsonify(
            status='ok',
            top10=top10,
            total=len(top10),
            autoRefresh=Switch.find_by_name('auto-refresh-allow').is_on
        )
    else:
        return jsonify(
            status='ok',
            message='not found',
            top10=[],
            total=0,
            autoRefresh=Switch.find_by_name('auto-refresh-allow').is_on
        )


# top 10 standing
@api.route('/alerts/top10/standing', methods=['OPTIONS', 'GET'])
@cross_origin()
@permission('read:alerts')
@timer(count_timer)
@jsonp
def get_top10_standing():
    query = qb.from_params(request.args)
    top10 = Alert.get_top10_standing(query)

    if top10:
        return jsonify(
            status='ok',
            top10=top10,
            total=len(top10),
            autoRefresh=Switch.find_by_name('auto-refresh-allow').is_on
        )
    else:
        return jsonify(
            status='ok',
            message='not found',
            top10=[],
            total=0,
            autoRefresh=Switch.find_by_name('auto-refresh-allow').is_on
        )


# get alert environments
@api.route('/environments', methods=['OPTIONS', 'GET'])
@cross_origin()
@permission('read:alerts')
@timer(gets_timer)
@jsonp
def get_environments():
    query = qb.from_params(request.args)
    environments = Alert.get_environments(query)

    if environments:
        return jsonify(
            status='ok',
            environments=environments,
            total=len(environments)
        )
    else:
        return jsonify(
            status='ok',
            message='not found',
            environments=[],
            total=0
        )


# get alert services
@api.route('/services', methods=['OPTIONS', 'GET'])
@cross_origin()
@permission('read:alerts')
@timer(gets_timer)
@jsonp
def get_services():
    query = qb.from_params(request.args)
    services = Alert.get_services(query)

    if services:
        return jsonify(
            status='ok',
            services=services,
            total=len(services)
        )
    else:
        return jsonify(
            status='ok',
            message='not found',
            services=[],
            total=0
        )


# get alert tags
@api.route('/tags', methods=['OPTIONS', 'GET'])
@cross_origin()
@permission('read:alerts')
@timer(gets_timer)
@jsonp
def get_tags():
    query = qb.from_params(request.args)
    tags = Alert.get_tags(query)

    if tags:
        return jsonify(
            status='ok',
            tags=tags,
            total=len(tags)
        )
    else:
        return jsonify(
            status='ok',
            message='not found',
            tags=[],
            total=0
        )
