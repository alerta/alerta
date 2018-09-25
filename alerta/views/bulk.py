from flask import jsonify, request
from flask_cors import cross_origin

from alerta.app import qb
from alerta.auth.decorators import permission
from alerta.exceptions import ApiError, RejectException
from alerta.models.alert import Alert
from alerta.models.metrics import timer
from alerta.utils.api import jsonp, process_action, process_status
from alerta.views.alerts import (attrs_timer, delete_timer, status_timer,
                                 tag_timer)

from . import api


@api.route('/_bulk/alerts/status', methods=['OPTIONS', 'PUT'])
@cross_origin()
@permission('write:alerts')
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
@permission('write:alerts')
@timer(status_timer)
@jsonp
def bulk_action_alert():
    action = request.json.get('action', None)
    text = request.json.get('text', 'bulk status update')
    timeout = request.json.get('timeout', None)

    if not action:
        raise ApiError("must supply 'action' as json data", 400)

    query = qb.from_params(request.args)
    alerts = Alert.find_all(query)

    if not alerts:
        raise ApiError('not found', 404)

    updated = []
    errors = []
    for alert in alerts:
        try:
            severity, status = process_action(alert, action)
            alert, status, text = process_status(alert, status, text)
        except RejectException as e:
            errors.append(str(e))
            continue
        except Exception as e:
            errors.append(str(e))
            continue

        if alert.set_severity_and_status(severity, status, text, timeout):
            updated.append(alert.id)

    if errors:
        raise ApiError('failed to bulk action alerts', 500, errors=errors)
    else:
        return jsonify(status='ok', updated=updated, count=len(updated))


@api.route('/_bulk/alerts/tag', methods=['OPTIONS', 'PUT'])
@cross_origin()
@permission('write:alerts')
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
@permission('write:alerts')
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
@permission('write:alerts')
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
@permission('write:alerts')
@timer(delete_timer)
@jsonp
def bulk_delete_alert():
    query = qb.from_params(request.args)
    deleted = Alert.delete_find_all(query)

    return jsonify(status='ok', deleted=deleted, count=len(deleted))
