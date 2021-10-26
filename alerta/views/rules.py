from flask import jsonify, request
from flask_cors import cross_origin

from alerta.auth.decorators import permission
from alerta.models.enums import Scope
from alerta.utils.response import jsonp
from . import api
from ..exceptions import ApiError
from ..models.Rules import Rule


@api.route('/rule', methods=['OPTIONS', 'POST'])
@cross_origin()
@permission(Scope.write_rules)
@jsonp
def create_customer_alert_forward_rule():
    request_payload = request.json
    rule = Rule(**request_payload)
    try:
        rule = rule.create()
    except Exception as e:
        return jsonify(status='error', message=str(e)), 400
    return jsonify(status='ok', id=rule.id, rule=rule.serialize), 201


@api.route("/rules", methods=['GET'])
@cross_origin()
@permission(Scope.read_rules)
def get_customer_rules():
    customer_id = request.args.get('customer_id')
    if not customer_id:
        raise ApiError("customer_id is not present in query parameters")
    sort_by = request.args.get('sort_by', 'id')
    limit = int(request.args.get('limit', 10))
    offset = int(request.args.get('offset', 0))
    ascending = request.args.get('sort_order', 'asc') == 'asc'
    rules = Rule.find_all(customer_id, sort_by, ascending, limit, offset)
    return jsonify(rules=[r.serialize for r in rules])


@api.route('/rule/<rule_id>', methods=['OPTIONS', 'GET'])
@cross_origin()
@permission(Scope.read_rules)
@jsonp
def get_rule_by_rule_id(rule_id):
    customer_id = request.args.get('customer_id')
    if not customer_id:
        raise ApiError("Customer id is missing in query params", 400)
    rule = Rule.find_by_id(rule_id, customer_id)
    if rule:
        return jsonify(status='ok', total=1, rule=rule.serialize)
    else:
        raise ApiError('not found', 404)


@api.route('/rule/<rule_id>', methods=['OPTIONS', 'PUT'])
@cross_origin()
@permission(Scope.write_rules)
@jsonp
def update_rule_by_rule_id(rule_id):
    customer_id = request.args.get('customer_id')
    if not customer_id:
        raise ApiError('customer_id not found in query params')
    request_json = request.get_json()
    """
    Drop customer_id and id for sanity
    """
    request_json.pop('customer_id', None)
    request_json.pop('id', None)
    rule = Rule.update_by_id(rule_id, customer_id, **request_json)
    if not rule:
        raise ApiError('not found', 404)
    return jsonify(status='ok', rule=rule.serialize)


@api.route('/rule/<rule_id>', methods=['OPTIONS', 'DELETE'])
@cross_origin()
@permission(Scope.write_rules)
@jsonp
def delete_rule_by_rule_id(rule_id):
    customer_id = request.args.get('customer_id')
    if not customer_id:
        raise ApiError('customer_id not found in query params')
    rule = Rule.delete_by_id(rule_id, customer_id)
    if not rule:
        raise ApiError('not found', 404)
    return jsonify(status='ok')
