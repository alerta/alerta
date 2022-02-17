import logging

from flask import request, jsonify
from flask_cors import cross_origin

from alerta.auth.decorators import permission
from alerta.models.enums import Scope
from alerta.utils.response import jsonp

from . import api
from ..exceptions import ApiError
from ..models.channel import DeveloperChannel

log_object = logging.getLogger('alerta.views.developer_channel')


@api.route("/dev-channel", methods=['POST'])
@cross_origin()
@permission(Scope.write_rules)
@jsonp
def create_dev_channel():
    try:
        channel = DeveloperChannel.parse(request.json)
        channel = channel.create()
    except Exception as e:
        return jsonify(status='error', message=str(e)), 400
    if not channel:
        raise ApiError("Cannot create developer channel")
    return jsonify(status='ok', channel=channel.serialize)


@api.route("/dev-channels", methods=['GET'])
@cross_origin()
@permission(Scope.read_rules)
@jsonp
def get_dev_channels():
    sort_by = request.args.get('sort_by', 'id')
    limit = int(request.args.get('limit', 10))
    offset = int(request.args.get('offset', 0))
    ascending = request.args.get('sort_order', 'asc') == 'asc'
    rules = DeveloperChannel.find_all(sort_by, ascending, limit, offset)
    return jsonify(channels=[r.serialize for r in rules])


@api.route("/dev-channel/<channel_id>", methods=['GET'])
@cross_origin()
@permission(Scope.read_rules)
@jsonp
def get_dev_channel_by_id(channel_id):
    channel = DeveloperChannel.find_by_id(channel_id)
    if not channel:
        raise ApiError('not found', 404)
    return jsonify(channel=channel.serialize)


@api.route("/dev-channel/<channel_id>", methods=['PUT'])
@cross_origin()
@permission(Scope.write_rules)
@jsonp
def update_dev_channel_by_id(channel_id):
    try:
        channel = DeveloperChannel.update_by_id(channel_id, **request.json)
    except Exception as e:
        raise ApiError(str(e), 400)
    if not channel:
        raise ApiError("not found", 404)
    return jsonify(channel=channel.serialize)


@api.route("/dev-channel/<channel_id>", methods=['DELETE'])
@cross_origin()
@permission(Scope.write_rules)
@jsonp
def delete_dev_channel_by_id(channel_id):
    try:
        channel = DeveloperChannel.delete_by_id(channel_id)
    except Exception as e:
        raise ApiError(str(e), 400)
    if not channel:
        raise ApiError("not found", 404)
    return jsonify(status='ok')
