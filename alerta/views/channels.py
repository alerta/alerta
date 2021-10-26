from flask import request, jsonify
from flask_cors import cross_origin

from alerta.auth.decorators import permission
from alerta.models.enums import Scope
from alerta.utils.response import jsonp

from . import api
from ..exceptions import ApiError
from ..models.channel import CustomerChannel


@api.route("/channel", methods=['POST'])
@cross_origin()
@permission(Scope.write_rules)
@jsonp
def create_channel():
    channel = CustomerChannel(**request.json)
    channel = channel.create()
    if not channel:
        raise ApiError("Cannot create customer channel")
    return jsonify(status='ok', channel=channel.serialize)


@api.route("/channels", methods=['GET'])
@cross_origin()
@permission(Scope.read_rules)
@jsonp
def get_channels():
    rule_id = request.args.get('rule_id')
    if not rule_id:
        raise ApiError('rule_id not present in query parameters')
    sort_by = request.args.get('sort_by', 'id')
    limit = int(request.args.get('limit', 10))
    offset = int(request.args.get('offset', 0))
    ascending = request.args.get('sort_order', 'asc') == 'asc'
    rules = CustomerChannel.find_all(rule_id, sort_by, ascending, limit, offset)
    return jsonify(channels=[r.serialize for r in rules])


@api.route("/channel/<channel_id>", methods=['GET'])
@cross_origin()
@permission(Scope.read_rules)
@jsonp
def get_channel_by_id(channel_id):
    channel = CustomerChannel.find_by_id(channel_id)
    if not channel:
        raise ApiError('not found', 404)
    return jsonify(channel=channel.serialize)


@api.route("/channel/<channel_id>", methods=['PUT'])
@cross_origin()
@permission(Scope.write_rules)
@jsonp
def update_channel_by_id(channel_id):
    channel = CustomerChannel.update_by_id(channel_id, **request.json)
    if not channel:
        raise ApiError("not found", 404)
    return jsonify(channel=channel.serialize)


@api.route("/channel/<channel_id>", methods=['DELETE'])
@cross_origin()
@permission(Scope.write_rules)
@jsonp
def delete_channel_by_id(channel_id):
    channel = CustomerChannel.delete_by_id(channel_id)
    if not channel:
        raise ApiError("not found", 404)
    return jsonify(status='ok')
