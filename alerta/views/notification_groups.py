from flask import current_app, g, jsonify, request
from flask_cors import cross_origin

from alerta.app import qb
from alerta.auth.decorators import permission
from alerta.exceptions import ApiError
from alerta.models.enums import Scope
from alerta.models.notification_group import NotificationGroup
from alerta.utils.api import assign_customer
from alerta.utils.audit import write_audit_trail
from alerta.utils.paging import Page
from alerta.utils.response import absolute_url, jsonp

from . import api


@api.route('/notificationgroups', methods=['OPTIONS', 'POST'])
@cross_origin()
@permission(Scope.write_notification_groups)
@jsonp
def create_notification_group():
    try:
        notification_group = NotificationGroup.parse(request.json)
    except Exception as e:
        raise ApiError(str(e), 400)

    try:
        notification_group = notification_group.create()
    except Exception as e:
        raise ApiError(str(e), 500)

    write_audit_trail.send(
        current_app._get_current_object(),
        event='notification_group-created',
        message='',
        user=g.login,
        customers=g.customers,
        scopes=g.scopes,
        resource_id=notification_group.id,
        type='notification_group',
        request=request,
    )

    if notification_group:
        return (
            jsonify(status='ok', id=notification_group.id, notificationGroup=notification_group.serialize),
            201,
            {'Location': absolute_url('/notificationgroup/' + notification_group.id)},
        )
    else:
        raise ApiError('insert notificationgroup failed', 500)


@api.route('/notificationgroups/<notification_group_id>', methods=['OPTIONS', 'GET'])
@cross_origin()
@permission(Scope.read_notification_groups)
@jsonp
def get_notification_group(notification_group_id):
    notification_group = NotificationGroup.find_by_id(notification_group_id)

    if notification_group:
        return jsonify(status='ok', total=1, notificationGroup=notification_group.serialize)
    else:
        raise ApiError('not found', 404)


@api.route('/notificationgroups', methods=['OPTIONS', 'GET'])
@cross_origin()
@permission(Scope.read_notification_groups)
@jsonp
def list_notification_groups():
    query = qb.notification_groups.from_params(request.args, customers=g.customers)
    total = NotificationGroup.count(query)
    paging = Page.from_params(request.args, total)
    notification_groups = NotificationGroup.find_all(query, page=paging.page, page_size=paging.page_size)

    if notification_groups:
        return jsonify(
            status='ok',
            page=paging.page,
            pageSize=paging.page_size,
            pages=paging.pages,
            more=paging.has_more,
            notificationGroups=[notification_group.serialize for notification_group in notification_groups],
            total=total,
        )
    else:
        return jsonify(
            status='ok',
            page=paging.page,
            pageSize=paging.page_size,
            pages=paging.pages,
            more=paging.has_more,
            message='not found',
            notificationGroups=[],
            total=0,
        )


@api.route('/notificationgroups/<notification_group_id>', methods=['OPTIONS', 'PUT'])
@cross_origin()
@permission(Scope.write_notification_groups)
@jsonp
def update_notification_group(notification_group_id):
    if not request.json:
        raise ApiError('nothing to change', 400)

    if not current_app.config['AUTH_REQUIRED']:
        notification_group = NotificationGroup.find_by_id(notification_group_id)
    elif Scope.admin in g.scopes or Scope.admin_notification_groups in g.scopes:
        notification_group = NotificationGroup.find_by_id(notification_group_id)
    else:
        notification_group = NotificationGroup.find_by_id(notification_group_id, g.customers)

    if not notification_group:
        raise ApiError('not found', 404)

    update = request.json
    update['user'] = g.login
    update['customer'] = assign_customer(wanted=update.get('customer'), permission=Scope.admin_notification_groups)

    write_audit_trail.send(
        current_app._get_current_object(),
        event='notification_group-updated',
        message='',
        user=g.login,
        customers=g.customers,
        scopes=g.scopes,
        resource_id=notification_group.id,
        type='notification_group',
        request=request,
    )

    updated = notification_group.update(**update)
    if updated:
        return jsonify(status='ok', notificationGroup=updated.serialize)
    else:
        raise ApiError('failed to update notificationgroup', 500)


@api.route('/notificationgroups/<notification_group_id>', methods=['OPTIONS', 'DELETE'])
@cross_origin()
@permission(Scope.write_notification_groups)
@jsonp
def delete_notification_group(notification_group_id):
    customer = g.get('customer', None)
    notification_group = NotificationGroup.find_by_id(notification_group_id, customer)

    if not notification_group:
        raise ApiError('not found', 404)

    write_audit_trail.send(
        current_app._get_current_object(),
        event='notification_group-deleted',
        message='',
        user=g.login,
        customers=g.customers,
        scopes=g.scopes,
        resource_id=notification_group.id,
        type='notification_group',
        request=request,
    )

    if notification_group.delete():
        return jsonify(status='ok')
    else:
        raise ApiError('failed to delete notificationgroup', 500)
