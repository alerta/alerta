from flask import current_app, g, jsonify, request
from flask_cors import cross_origin

from alerta.app import qb
from alerta.auth.decorators import permission
from alerta.exceptions import ApiError
from alerta.models.notification_rule import NotificationRule
from alerta.models.enums import Scope
from alerta.utils.api import assign_customer
from alerta.utils.audit import write_audit_trail
from alerta.utils.paging import Page
from alerta.utils.response import absolute_url, jsonp

from . import api


@api.route('/notificationrules', methods=['OPTIONS', 'POST'])
@cross_origin()
@permission(Scope.write_notification_rules)
@jsonp
def create_notification_rule():
    try:
        notification_rule = NotificationRule.parse(request.json)
    except Exception as e:
        raise ApiError(str(e), 400)

    if Scope.admin in g.scopes or Scope.admin_notification_rules in g.scopes:
        notification_rule.user = notification_rule.user or g.login
    else:
        notification_rule.user = g.login

    notification_rule.customer = assign_customer(wanted=notification_rule.customer, permission=Scope.admin_notification_rules)

    try:
        notification_rule = notification_rule.create()
    except Exception as e:
        raise ApiError(str(e), 500)

    write_audit_trail.send(
        current_app._get_current_object(),
        event='notification_rule-created',
        message='',
        user=g.login,
        customers=g.customers,
        scopes=g.scopes,
        resource_id=notification_rule.id,
        type='notification_rule',
        request=request,
    )

    if notification_rule:
        return (
            jsonify(status='ok', id=notification_rule.id, notificationRule=notification_rule.serialize),
            201,
            {'Location': absolute_url('/notificationrule/' + notification_rule.id)},
        )
    else:
        raise ApiError('insert notification rule failed', 500)


@api.route('/notificationrules/<notification_rule_id>', methods=['OPTIONS', 'GET'])
@cross_origin()
@permission(Scope.read_notification_rules)
@jsonp
def get_notification_rule(notification_rule_id):
    notification_rule = NotificationRule.find_by_id(notification_rule_id)

    if notification_rule:
        return jsonify(status='ok', total=1, notificationRule=notification_rule.serialize)
    else:
        raise ApiError('not found', 404)


@api.route('/notificationrules', methods=['OPTIONS', 'GET'])
@cross_origin()
@permission(Scope.read_notification_rules)
@jsonp
def list_notification_rules():
    query = qb.from_params(request.args, customers=g.customers)
    total = NotificationRule.count(query)
    paging = Page.from_params(request.args, total)
    notification_rules = NotificationRule.find_all(query, page=paging.page, page_size=paging.page_size)

    if notification_rules:
        return jsonify(
            status='ok',
            page=paging.page,
            pageSize=paging.page_size,
            pages=paging.pages,
            more=paging.has_more,
            notificationRules=[notification_rule.serialize for notification_rule in notification_rules],
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
            notificationRules=[],
            total=0,
        )


@api.route('/notificationrules/<notification_rule_id>', methods=['OPTIONS', 'PUT'])
@cross_origin()
@permission(Scope.write_notification_rules)
@jsonp
def update_notification_rule(notification_rule_id):
    if not request.json:
        raise ApiError('nothing to change', 400)

    if not current_app.config['AUTH_REQUIRED']:
        notification_rule = NotificationRule.find_by_id(notification_rule_id)
    elif Scope.admin in g.scopes or Scope.admin_notification_rules in g.scopes:
        notification_rule = NotificationRule.find_by_id(notification_rule_id)
    else:
        notification_rule = NotificationRule.find_by_id(notification_rule_id, g.customers)

    if not notification_rule:
        raise ApiError('not found', 404)

    update = request.json
    update['user'] = g.login
    update['customer'] = assign_customer(wanted=update.get('customer'), permission=Scope.admin_notification_rules)

    write_audit_trail.send(
        current_app._get_current_object(),
        event='notification_rule-updated',
        message='',
        user=g.login,
        customers=g.customers,
        scopes=g.scopes,
        resource_id=notification_rule.id,
        type='notification_rule',
        request=request,
    )

    updated = notification_rule.update(**update)
    if updated:
        return jsonify(status='ok', notificationRule=updated.serialize)
    else:
        raise ApiError('failed to update notification rule', 500)


@api.route('/notificationrules/<notification_rule_id>', methods=['OPTIONS', 'DELETE'])
@cross_origin()
@permission(Scope.write_notification_rules)
@jsonp
def delete_notification_rule(notification_rule_id):
    customer = g.get('customer', None)
    notification_rule = NotificationRule.find_by_id(notification_rule_id, customer)

    if not notification_rule:
        raise ApiError('not found', 404)

    write_audit_trail.send(
        current_app._get_current_object(),
        event='notification_rule-deleted',
        message='',
        user=g.login,
        customers=g.customers,
        scopes=g.scopes,
        resource_id=notification_rule.id,
        type='notification_rule',
        request=request,
    )

    if notification_rule.delete():
        return jsonify(status='ok')
    else:
        raise ApiError('failed to delete notification rule', 500)
