from flask import current_app, g, jsonify, request
from flask_cors import cross_origin

from alerta.app import qb, alarm_model
from alerta.auth.decorators import permission
from alerta.exceptions import ApiError
from alerta.models.alert import Alert
from alerta.models.enums import Scope
from alerta.models.escalation_rule import EscalationRule
from alerta.utils.api import assign_customer
from alerta.utils.audit import write_audit_trail
from alerta.utils.paging import Page
from alerta.utils.response import absolute_url, jsonp
from alerta.models.enums import TrendIndication
from alerta.utils.api import process_alert

from . import api


@api.route('/escalationrules', methods=['OPTIONS', 'POST'])
@cross_origin()
@permission(Scope.write_escalation_rules)
@jsonp
def create_escalation_rule():
    try:
        escalation_rule = EscalationRule.parse(request.json)
    except Exception as e:
        raise ApiError(str(e), 400)

    if Scope.admin in g.scopes or Scope.admin_escalation_rules in g.scopes:
        escalation_rule.user = escalation_rule.user or g.login
    else:
        escalation_rule.user = g.login

    escalation_rule.customer = assign_customer(wanted=escalation_rule.customer, permission=Scope.admin_escalation_rules)

    try:
        escalation_rule = escalation_rule.create()
    except Exception as e:
        raise ApiError(str(e), 500)

    write_audit_trail.send(
        current_app._get_current_object(),
        event='escalation_rule-created',
        message='',
        user=g.login,
        customers=g.customers,
        scopes=g.scopes,
        resource_id=escalation_rule.id,
        type='escalation_rule',
        request=request,
    )

    if escalation_rule:
        return (
            jsonify(status='ok', id=escalation_rule.id, escalationRule=escalation_rule.serialize),
            201,
            {'Location': absolute_url('/escalationrule/' + escalation_rule.id)},
        )
    else:
        raise ApiError('insert escalation rule failed', 500)


@api.route('/escalate', methods=['OPTIONS', 'GET'])
@cross_origin()
@permission(Scope.write_alerts)
@jsonp
def escalate():
    alerts = EscalationRule.find_all_active()
    escalated_alerts = []
    for alert in alerts:
        severity_weight = alarm_model.Severity[alert.severity]
        try:
            for severity, weight in alarm_model.Severity.items():
                if weight - severity_weight == 1 or weight - severity_weight == - 1:
                    if alarm_model.trend(alert.severity, severity) == TrendIndication.More_Severe:
                        alert.severity = severity
                        escalated_alerts.append(alert)
                        process_alert(alert)
        except Exception as e:
            raise ApiError(str(e), 500)
    return jsonify(status='ok', alerts=[alert.serialize for alert in escalated_alerts]), 200


@api.route('/escalationrules/<escalation_rule_id>', methods=['OPTIONS', 'GET'])
@cross_origin()
@permission(Scope.read_escalation_rules)
@jsonp
def get_escalation_rule(escalation_rule_id):
    escalation_rule = EscalationRule.find_by_id(escalation_rule_id)

    if escalation_rule:
        return jsonify(status='ok', total=1, escalationRule=escalation_rule.serialize)
    else:
        raise ApiError('not found', 404)


@api.route('/escalationrules/active', methods=['OPTIONS', 'POST'])
@cross_origin()
@permission(Scope.read_escalation_rules)
@jsonp
def get_escalation_rules_active():
    alert_json = request.json
    if alert_json is None or alert_json.get('id') is None:
        return jsonify(status='ok', total=0, escalationrules=[])
    try:
        alert = Alert.find_by_id(alert_json.get('id'))
    except Exception as e:
        raise ApiError(str(e), 400)

    escalation_rules = [escalation_rule.serialize for escalation_rule in EscalationRule.find_all_active(alert)]
    total = len(escalation_rules)
    return jsonify(status='ok', total=total, escalationrules=escalation_rules)


@api.route('/escalationrules', methods=['OPTIONS', 'GET'])
@cross_origin()
@permission(Scope.read_escalation_rules)
@jsonp
def list_escalation_rules():
    query = qb.escalation_rules.from_params(request.args, customers=g.customers)
    total = EscalationRule.count(query)
    paging = Page.from_params(request.args, total)
    escalation_rules = EscalationRule.find_all(query, page=paging.page, page_size=paging.page_size)

    if escalation_rules:
        return jsonify(
            status='ok',
            page=paging.page,
            pageSize=paging.page_size,
            pages=paging.pages,
            more=paging.has_more,
            escalationRules=[escalation_rule.serialize for escalation_rule in escalation_rules],
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
            escalationRules=[],
            total=0,
        )


@api.route('/escalationrules/<escalation_rule_id>', methods=['OPTIONS', 'PUT'])
@cross_origin()
@permission(Scope.write_escalation_rules)
@jsonp
def update_escalation_rule(escalation_rule_id):
    if not request.json:
        raise ApiError('nothing to change', 400)

    if not current_app.config['AUTH_REQUIRED']:
        escalation_rule = EscalationRule.find_by_id(escalation_rule_id)
    elif Scope.admin in g.scopes or Scope.admin_escalation_rules in g.scopes:
        escalation_rule = EscalationRule.find_by_id(escalation_rule_id)
    else:
        escalation_rule = EscalationRule.find_by_id(escalation_rule_id, g.customers)

    if not escalation_rule:
        raise ApiError('not found', 404)

    update = request.json
    update['user'] = g.login
    update['customer'] = assign_customer(wanted=update.get('customer'), permission=Scope.admin_escalation_rules)

    write_audit_trail.send(
        current_app._get_current_object(),
        event='escalation_rule-updated',
        message='',
        user=g.login,
        customers=g.customers,
        scopes=g.scopes,
        resource_id=escalation_rule.id,
        type='escalation_rule',
        request=request,
    )

    updated = escalation_rule.update(**update)
    if updated:
        return jsonify(status='ok', escalationRule=updated.serialize)
    else:
        raise ApiError('failed to update escalation rule', 500)


@api.route('/escalationrules/<escalation_rule_id>', methods=['OPTIONS', 'DELETE'])
@cross_origin()
@permission(Scope.write_escalation_rules)
@jsonp
def delete_escalation_rule(escalation_rule_id):
    customer = g.get('customer', None)
    escalation_rule = EscalationRule.find_by_id(escalation_rule_id, customer)

    if not escalation_rule:
        raise ApiError('not found', 404)

    write_audit_trail.send(
        current_app._get_current_object(),
        event='escalation_rule-deleted',
        message='',
        user=g.login,
        customers=g.customers,
        scopes=g.scopes,
        resource_id=escalation_rule.id,
        type='escalation_rule',
        request=request,
    )

    if escalation_rule.delete():
        return jsonify(status='ok')
    else:
        raise ApiError('failed to delete escalation rule', 500)
