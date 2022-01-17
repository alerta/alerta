import logging

from flask import request, jsonify
from flask_cors import cross_origin

from alerta.auth.decorators import permission
from alerta.models.enums import Scope
from alerta.utils.response import jsonp

from . import api
from ..exceptions import ApiError
from ..models.Rules import Rule
from ..models.channel import CustomerChannel
from ..models.channel_rule import CustomerChannelRuleMap

log_object = logging.getLogger('alerta.views.customer_channel')


@api.route("/channel", methods=['POST'])
@cross_origin()
@permission(Scope.write_rules)
@jsonp
def create_channel():
    try:
        channel = CustomerChannel.parse(request.json)
        channel = channel.create()
    except Exception as e:
        return jsonify(status='error', message=str(e)), 400
    if not channel:
        raise ApiError("Cannot create customer channel")
    return jsonify(status='ok', channel=channel.serialize)


@api.route("/channels", methods=['GET'])
@cross_origin()
@permission(Scope.read_rules)
@jsonp
def get_channels():
    customer_id = request.args.get('customer_id')
    if not customer_id:
        raise ApiError('customer_id not present in query parameters', 400)
    sort_by = request.args.get('sort_by', 'id')
    limit = int(request.args.get('limit', 10))
    offset = int(request.args.get('offset', 0))
    ascending = request.args.get('sort_order', 'asc') == 'asc'
    rules = CustomerChannel.find_all(customer_id, sort_by, ascending, limit, offset)
    return jsonify(channels=[r.serialize for r in rules])


@api.route("/channel/<channel_id>", methods=['GET'])
@cross_origin()
@permission(Scope.read_rules)
@jsonp
def get_channel_by_id(channel_id):
    customer_id = request.args.get('customer_id')
    if not customer_id:
        raise ApiError('customer_id not present in query parameters', 400)
    channel = CustomerChannel.find_by_id(customer_id, channel_id)
    if not channel:
        raise ApiError('not found', 404)
    return jsonify(channel=channel.serialize)


@api.route("/channel/<channel_id>", methods=['PUT'])
@cross_origin()
@permission(Scope.write_rules)
@jsonp
def update_channel_by_id(channel_id):
    customer_id = request.args.get('customer_id')
    if not customer_id:
        raise ApiError('customer_id not present in query parameters', 400)
    try:
        channel = CustomerChannel.update_by_id(customer_id, channel_id, **request.json)
    except Exception as e:
        raise ApiError(str(e), 400)
    if not channel:
        raise ApiError("not found", 404)
    return jsonify(channel=channel.serialize)


@api.route("/channel/<channel_id>", methods=['DELETE'])
@cross_origin()
@permission(Scope.write_rules)
@jsonp
def delete_channel_by_id(channel_id):
    customer_id = request.args.get('customer_id')
    if not customer_id:
        raise ApiError('customer_id not present in query parameters', 400)
    try:
        channel = CustomerChannel.delete_by_id(customer_id, channel_id)
    except Exception as e:
        raise ApiError(str(e), 400)
    if not channel:
        raise ApiError("not found", 404)
    return jsonify(status='ok')


@api.route("/channel-rule", methods=['POST'])
@cross_origin()
@permission(Scope.write_rules)
@jsonp
def link_channel_rule():
    customer_id = request.args.get('customer_id')
    if not customer_id or customer_id.strip() == "":
        raise ApiError("'customer_id' query parameter is missing for the request", 400)
    try:
        channel_id = int(request.json['channel_id'])
    except KeyError as e:
        raise Exception("'channel_id' is missing in the request body", 400)
    except ValueError as e:
        raise Exception("'channel_id' must be an integer", 400)
    try:
        rule_id = request.json['rule_id']
    except KeyError as e:
        raise Exception("'rule_id' is missing in the request body", 400)
    except ValueError as e:
        raise Exception("'rule_id' must be an integer", 400)
    rule = Rule.find_by_id(rule_id, customer_id)
    if not rule:
        raise ApiError(f"Rule not found {rule_id} for the customer {customer_id}", 400)
    customer_channel = CustomerChannel.find_by_id(customer_id, channel_id)
    if not customer_channel:
        raise ApiError(f"Channel {channel_id} not found", 400)
    if customer_channel.customer_id != rule.customer_id:
        raise ApiError(f"Channel {channel_id} and Rule {rule_id} cannot be mapped.", 400)
    channel_rule_map = CustomerChannelRuleMap(channel_id, rule_id)
    channel_rule_map = channel_rule_map.create()
    if not channel_rule_map:
        raise ApiError("not found", 404)
    return jsonify(status='ok')


@api.route("/channel-rule/<channel_rule_map_id>", methods=['DELETE'])
@cross_origin()
@permission(Scope.write_rules)
@jsonp
def unlink_channel_rule(channel_rule_map_id):
    customer_id = request.args.get('customer_id')
    if not customer_id or customer_id.strip() == "":
        raise ApiError("'customer_id' query parameter is missing for the request", 400)
    channel_rule_map = CustomerChannelRuleMap.delete_by_id(customer_id, int(channel_rule_map_id))
    if channel_rule_map:
        return jsonify(status='ok')
    raise ApiError('not found', 404)


@api.route("/channel-rules", methods=['GET'])
@cross_origin()
@permission(Scope.write_rules)
@jsonp
def get_channel_rules():
    customer_id = request.args.get('customer_id')
    if not customer_id or customer_id.strip() == "":
        raise ApiError("'customer_id' query parameter is missing for the request", 400)
    channel_rules = CustomerChannelRuleMap.get_channel_rules(customer_id)
    return jsonify([c.serialize for c in channel_rules])
