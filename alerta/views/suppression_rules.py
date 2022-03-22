import logging

from flask import request, jsonify
from flask_cors import cross_origin

from alerta.auth.decorators import permission
from alerta.models.enums import Scope
from alerta.utils.response import jsonp

from . import api
from ..exceptions import ApiError
from ..models.SuppressionRule import SuppressionRule

log_object = logging.getLogger('alerta.views.suppression_rules')


@api.route("/suppression-rule", methods=['POST'])
@cross_origin()
@permission(Scope.write_rules)
@jsonp
def create_suppression_rule():
    try:
        suppression_rule = SuppressionRule.parse(request.json)
        suppression_rule = suppression_rule.create()
    except Exception as e:
        return jsonify(status='error', message=str(e)), 400
    if not suppression_rule:
        raise ApiError("Cannot create developer channel")
    return jsonify(status='ok', channel=suppression_rule.serialize)


@api.route("/suppression-rule/<id>", methods=['PUT'])
@cross_origin()
@permission(Scope.write_rules)
@jsonp
def update_suppression_rule_by_id(id):
    try:
        suppression_rule = SuppressionRule.update_by_id(id, **request.json)
    except Exception as e:
        raise ApiError(str(e), 400)
    if not suppression_rule:
        raise ApiError("not found", 404)
    return jsonify(suppression_rule=suppression_rule.serialize)


@api.route("/suppression-rule/<id>", methods=['GET'])
@cross_origin()
@permission(Scope.read_rules)
@jsonp
def get_suppression_rule_by_id(id):
    suppression_rule = SuppressionRule.find_by_id(id)
    if not suppression_rule:
        raise ApiError('not found', 404)
    return jsonify(suppression_rule=suppression_rule.serialize)


@api.route("/suppression-rule/<id>", methods=['DELETE'])
@cross_origin()
@permission(Scope.write_rules)
@jsonp
def delete_suppression_rule_by_id(id):
    try:
        suppression_rule = SuppressionRule.delete_by_id(id)
    except Exception as e:
        raise ApiError(str(e), 400)
    if not suppression_rule:
        raise ApiError("not found", 404)
    return jsonify(status='ok')


@api.route("/suppression-rules", methods=['GET'])
@cross_origin()
@permission(Scope.read_rules)
@jsonp
def get_suppression_rules():
    sort_by = request.args.get('sort_by', 'id')
    limit = int(request.args.get('limit', 10))
    offset = int(request.args.get('offset', 0))
    ascending = request.args.get('sort_order', 'asc') == 'asc'
    rules = SuppressionRule.find_all(sort_by, ascending, limit, offset)
    return jsonify(suppression_rules=[r.serialize for r in rules])
