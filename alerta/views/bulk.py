from flask import jsonify, request
from flask_cors import cross_origin

from alerta.app import qb
from alerta.auth.decorators import permission
from alerta.exceptions import ApiError, RejectException
from alerta.models.alert import Alert
from alerta.models.enums import Scope
from alerta.models.metrics import timer
from alerta.utils.api import process_status
from alerta.utils.response import absolute_url, jsonp
from alerta.views.alerts import (attrs_timer, delete_timer, status_timer,
                                 tag_timer)

from . import api


@api.route('/_bulk/task/<task_id>', methods=['OPTIONS', 'GET'])
@cross_origin()
@permission(Scope.read_alerts)
@timer(status_timer)
@jsonp
def task_status(task_id):
    from alerta.tasks import action_alerts
    task = action_alerts.AsyncResult(task_id)

    return jsonify(status=task.status.lower(), id=task.id)


@api.route('/_bulk/alerts/status', methods=['OPTIONS', 'PUT'])
@cross_origin()
@permission(Scope.write_alerts)
@timer(status_timer)
@jsonp
def bulk_set_status():
    status = request.json.get('status', None)
    text = request.json.get('text', 'bulk status update')
    timeout = request.json.get('timeout', None)

    if not status:
        raise ApiError("must supply 'status' as json data", 400)

    query = qb.from_params(request.args)
    alerts = Alert.find_all(query)

    if not alerts:
        raise ApiError('not found', 404)

    updated = []
    errors = []
    for alert in alerts:
        try:
            alert, status, text = process_status(alert, status, text)
        except RejectException as e:
            errors.append(str(e))
            continue
        except Exception as e:
            errors.append(str(e))
            continue

        if alert.set_status(status, text, timeout):
            updated.append(alert.id)

    if errors:
        raise ApiError('failed to bulk set alert status', 500, errors=errors)
    else:
        return jsonify(status='ok', updated=updated, count=len(updated))


@api.route('/_bulk/alerts/action', methods=['OPTIONS', 'PUT'])
@cross_origin()
@permission(Scope.write_alerts)
@timer(status_timer)
@jsonp
def bulk_action_alert():
    from alerta.tasks import action_alerts

    action = request.json.get('action', None)
    text = request.json.get('text', 'bulk status update')
    timeout = request.json.get('timeout', None)

    if not action:
        raise ApiError("must supply 'action' as json data", 400)

    query = qb.from_params(request.args)
    alerts = [alert.id for alert in Alert.find_all(query)]

    if not alerts:
        raise ApiError('not found', 404)

    task = action_alerts.delay(alerts, action, text, timeout)

    return jsonify(status='ok', message='{} alerts queued for action'.format(len(alerts))), 202, {'Location': absolute_url('/_bulk/task/' + task.id)}


@api.route('/_bulk/alerts/tag', methods=['OPTIONS', 'PUT'])
@cross_origin()
@permission(Scope.write_alerts)
@timer(tag_timer)
@jsonp
def bulk_tag_alert():
    if not request.json.get('tags', None):
        raise ApiError("must supply 'tags' as json list")

    query = qb.from_params(request.args)
    updated = Alert.tag_find_all(query, tags=request.json['tags'])

    return jsonify(status='ok', updated=updated, count=len(updated))


@api.route('/_bulk/alerts/untag', methods=['OPTIONS', 'PUT'])
@cross_origin()
@permission(Scope.write_alerts)
@timer(tag_timer)
@jsonp
def bulk_untag_alert():
    if not request.json.get('tags', None):
        raise ApiError("must supply 'tags' as json list")

    query = qb.from_params(request.args)
    updated = Alert.untag_find_all(query, tags=request.json['tags'])

    return jsonify(status='ok', updated=updated, count=len(updated))


@api.route('/_bulk/alerts/attributes', methods=['OPTIONS', 'PUT'])
@cross_origin()
@permission(Scope.write_alerts)
@timer(attrs_timer)
@jsonp
def bulk_update_attributes():
    if not request.json.get('attributes', None):
        raise ApiError("must supply 'attributes' as json data", 400)

    query = qb.from_params(request.args)
    updated = Alert.update_attributes_find_all(query, request.json['attributes'])

    return jsonify(status='ok', updated=updated, count=len(updated))


@api.route('/_bulk/alerts', methods=['OPTIONS', 'DELETE'])
@cross_origin()
@permission(Scope.write_alerts)
@timer(delete_timer)
@jsonp
def bulk_delete_alert():
    query = qb.from_params(request.args)
    deleted = Alert.delete_find_all(query)

    return jsonify(status='ok', deleted=deleted, count=len(deleted))
