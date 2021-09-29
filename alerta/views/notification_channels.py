from cryptography.fernet import Fernet
from flask import current_app, g, jsonify, request
from flask_cors import cross_origin

from alerta.app import qb
from alerta.auth.decorators import permission
from alerta.exceptions import ApiError
from alerta.models.notification_channel import NotificationChannel
from alerta.models.enums import Scope
from alerta.utils.api import assign_customer
from alerta.utils.audit import write_audit_trail
from alerta.utils.paging import Page
from alerta.utils.response import absolute_url, jsonp

from . import api

import logging

LOG = logging.getLogger("alerta/views/notification_channels")


@api.route('/notificationchannels', methods=['OPTIONS', 'POST'])
@cross_origin()
@permission(Scope.write_notification_channels)
@jsonp
def create_notification_channel():
    try:
        notification_channel = NotificationChannel.parse(request.json)
    except Exception as e:
        raise ApiError(str(e), 400)

    notification_channel.customer = assign_customer(wanted=notification_channel.customer, permission=Scope.admin_notification_channels)

    try:
        notification_channel = notification_channel.create()
    except Exception as e:
        raise ApiError(str(e), 500)

    write_audit_trail.send(
        current_app._get_current_object(),
        event='notification_channel-created',
        message='',
        user=g.login,
        customers=g.customers,
        scopes=g.scopes,
        resource_id=notification_channel.id,
        type='notification_channel',
        request=request,
    )

    if notification_channel:
        return (
            jsonify(status='ok', id=notification_channel.id, notificationChannel=notification_channel.serialize),
            201,
            {'Location': absolute_url('/notificationchannels/' + notification_channel.id)},
        )
    else:
        raise ApiError('insert notification channel failed', 500)


@api.route('/notificationchannels/<notification_channel_id>', methods=['OPTIONS', 'GET'])
@cross_origin()
@permission(Scope.read_notification_channels)
@jsonp
def notification_channel(notification_channel_id):
    notification_channel = NotificationChannel.find_by_id(notification_channel_id)

    if notification_channel:
        return jsonify(status='ok', total=1, notificationChannel=notification_channel.serialize)
    else:
        raise ApiError('not found', 404)


@api.route('/notificationchannels/keygen', methods=['OPTIONS', 'GET'])
@cross_origin()
@permission(Scope.read_notification_channels)
@jsonp
def keygen():
    key = Fernet.generate_key().decode()
    if notification_channel:
        return jsonify(status='ok', total=1, key=key)
    else:
        raise ApiError('not found', 404)


@api.route('/notificationchannels', methods=['OPTIONS', 'GET'])
@cross_origin()
@permission(Scope.read_notification_channels)
@jsonp
def list_notification_channels():
    query = qb.notification_channels.from_params(request.args, customers=g.customers)
    total = NotificationChannel.count(query)
    paging = Page.from_params(request.args, total)
    notification_channels = NotificationChannel.find_all(query, page=paging.page, page_size=paging.page_size)

    if notification_channels:
        return jsonify(
            status='ok',
            page=paging.page,
            pageSize=paging.page_size,
            pages=paging.pages,
            more=paging.has_more,
            notificationChannels=[notification_channel.serialize for notification_channel in notification_channels],
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
            notificationChannels=[],
            total=0,
        )


@api.route('/notificationchannels/<notification_channels_id>', methods=['OPTIONS', 'PUT'])
@cross_origin()
@permission(Scope.write_notification_channels)
@jsonp
def update_notification_channel(notification_channel_id):
    if not request.json:
        raise ApiError('nothing to change', 400)

    if not current_app.config['AUTH_REQUIRED']:
        notification_channel = NotificationChannel.find_by_id(notification_channel_id)
    elif Scope.admin in g.scopes or Scope.admin_notification_channels in g.scopes:
        notification_channel = NotificationChannel.find_by_id(notification_channel_id)
    else:
        notification_channel = NotificationChannel.find_by_id(notification_channel_id, g.customers)

    if not notification_channel:
        raise ApiError('not found', 404)

    update = request.json
    update['user'] = g.login
    update['customer'] = assign_customer(wanted=update.get('customer'), permission=Scope.admin_notification_channels)

    write_audit_trail.send(
        current_app._get_current_object(),
        event='notification_channel-updated',
        message='',
        user=g.login,
        customers=g.customers,
        scopes=g.scopes,
        resource_id=notification_channel.id,
        type='notification_channel',
        request=request,
    )

    updated = notification_channel.update(**update)
    if updated:
        return jsonify(status='ok', notificationChannel=updated.serialize)
    else:
        raise ApiError('failed to update notification channel', 500)


@api.route('/notificationchannels/<notification_channel_id>', methods=['OPTIONS', 'DELETE'])
@cross_origin()
@permission(Scope.write_notification_channels)
@jsonp
def delete_notification_channel(notification_channel_id):
    LOG.error(notification_channel_id)
    customer = g.get('customer', None)
    notification_channel = NotificationChannel.find_by_id(notification_channel_id, customer)
    LOG.error(notification_channel)

    if not notification_channel:
        raise ApiError('not found', 404)

    write_audit_trail.send(
        current_app._get_current_object(),
        event='notification_channel-deleted',
        message='',
        user=g.login,
        customers=g.customers,
        scopes=g.scopes,
        resource_id=notification_channel.id,
        type='notification_channel',
        request=request,
    )

    if notification_channel.delete():
        return jsonify(status='ok')
    else:
        raise ApiError('failed to delete notification channel rule', 500)
