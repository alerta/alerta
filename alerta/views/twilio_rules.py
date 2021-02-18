from flask import current_app, g, jsonify, request
from flask_cors import cross_origin

from alerta.app import qb
from alerta.auth.decorators import permission
from alerta.exceptions import ApiError
from alerta.models.twilio_rule import TwilioRule
from alerta.models.enums import Scope
from alerta.utils.api import assign_customer
from alerta.utils.audit import write_audit_trail
from alerta.utils.paging import Page
from alerta.utils.response import absolute_url, jsonp

from . import api


@api.route('/twiliorule', methods=['OPTIONS', 'POST'])
@cross_origin()
@permission(Scope.write_twilio_rules)
@jsonp
def create_twilio_rule():
    try:
        twilio_rule = TwilioRule.parse(request.json)
    except Exception as e:
        raise ApiError(str(e), 400)

    if Scope.admin in g.scopes or Scope.admin_twilio_rules in g.scopes:
        twilio_rule.user = twilio_rule.user or g.login
    else:
        twilio_rule.user = g.login

    twilio_rule.customer = assign_customer(wanted=twilio_rule.customer, permission=Scope.admin_twilio_rules)

    try:
        twilio_rule = twilio_rule.create()
    except Exception as e:
        raise ApiError(str(e), 500)

    write_audit_trail.send(
        current_app._get_current_object(),
        event='twiliorule-created',
        message='',
        user=g.login,
        customers=g.customers,
        scopes=g.scopes,
        resource_id=twilio_rule.id,
        type='twilio_rule',
        request=request,
    )

    if twilio_rule:
        return (
            jsonify(status='ok', id=twilio_rule.id, twilioRule=twilio_rule.serialize),
            201,
            {'Location': absolute_url('/twiliorule/' + twilio_rule.id)},
        )
    else:
        raise ApiError('insert twilio rule failed', 500)


@api.route('/twiliorule/<twilio_rule_id>', methods=['OPTIONS', 'GET'])
@cross_origin()
@permission(Scope.read_twilio_rules)
@jsonp
def get_twilio_rule(twilio_rule_id):
    twilio_rule = TwilioRule.find_by_id(twilio_rule_id)

    if twilio_rule:
        return jsonify(status='ok', total=1, twilioRule=twilio_rule.serialize)
    else:
        raise ApiError('not found', 404)


@api.route('/twiliorule', methods=['OPTIONS', 'GET'])
@cross_origin()
@permission(Scope.read_twilio_rules)
@jsonp
def list_twilio_rules():
    query = qb.from_params(request.args, customers=g.customers)
    total = TwilioRule.count(query)
    paging = Page.from_params(request.args, total)
    twilio_rules = TwilioRule.find_all(query, page=paging.page, page_size=paging.page_size)

    if twilio_rules:
        return jsonify(
            status='ok',
            page=paging.page,
            pageSize=paging.page_size,
            pages=paging.pages,
            more=paging.has_more,
            twilioRules=[twilio_rule.serialize for twilio_rule in twilio_rules],
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
            twilioRules=[],
            total=0,
        )


@api.route('/twiliorule/<twilio_rule_id>', methods=['OPTIONS', 'PUT'])
@cross_origin()
@permission(Scope.write_twilio_rules)
@jsonp
def update_twilio_rule(twilio_rule_id):
    if not request.json:
        raise ApiError('nothing to change', 400)

    if not current_app.config['AUTH_REQUIRED']:
        twilio_rule = TwilioRule.find_by_id(twilio_rule_id)
    elif Scope.admin in g.scopes or Scope.admin_twilio_rules in g.scopes:
        twilio_rule = TwilioRule.find_by_id(twilio_rule_id)
    else:
        twilio_rule = TwilioRule.find_by_id(twilio_rule_id, g.customers)

    if not twilio_rule:
        raise ApiError('not found', 404)

    update = request.json
    update['user'] = g.login
    update['customer'] = assign_customer(wanted=update.get('customer'), permission=Scope.admin_twilio_rules)

    write_audit_trail.send(
        current_app._get_current_object(),
        event='twilio_rule-updated',
        message='',
        user=g.login,
        customers=g.customers,
        scopes=g.scopes,
        resource_id=twilio_rule.id,
        type='twilio_rule',
        request=request,
    )

    updated = twilio_rule.update(**update)
    if updated:
        return jsonify(status='ok', twilioRule=updated.serialize)
    else:
        raise ApiError('failed to update twilio rule', 500)


@api.route('/twiliorule/<twilio_rule_id>', methods=['OPTIONS', 'DELETE'])
@cross_origin()
@permission(Scope.write_twilio_rules)
@jsonp
def delete_twilio_rule(twilio_rule_id):
    customer = g.get('customer', None)
    twilio_rule = TwilioRule.find_by_id(twilio_rule_id, customer)

    if not twilio_rule:
        raise ApiError('not found', 404)

    write_audit_trail.send(
        current_app._get_current_object(),
        event='twilio_rule-deleted',
        message='',
        user=g.login,
        customers=g.customers,
        scopes=g.scopes,
        resource_id=twilio_rule.id,
        type='twilio_rule',
        request=request,
    )

    if twilio_rule.delete():
        return jsonify(status='ok')
    else:
        raise ApiError('failed to delete twilio rule', 500)
