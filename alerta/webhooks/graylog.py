
from flask import request, g, jsonify
from flask_cors import cross_origin

from alerta.auth.utils import permission
from alerta.exceptions import ApiError, RejectException
from alerta.models.alert import Alert
from alerta.utils.api import process_alert, add_remote_ip
from . import webhooks


# {
#     "check_result": {
#         "result_description": "Stream had 2 messages in the last 1 minutes with trigger condition more than 1 messages. (Current grace time: 1 minutes)",
#         "triggered_condition": {
#             "id": "5e7a9c8d-9bb1-47b6-b8db-4a3a83a25e0c",
#             "type": "MESSAGE_COUNT",
#             "created_at": "2015-09-10T09:44:10.552Z",
#             "creator_user_id": "admin",
#             "grace": 1,
#             "parameters": {
#                 "grace": 1,
#                 "threshold": 1,
#                 "threshold_type": "more",
#                 "backlog": 5,
#                 "time": 1
#             },
#             "description": "time: 1, threshold_type: more, threshold: 1, grace: 1",
#             "type_string": "MESSAGE_COUNT",
#             "backlog": 5
#         },
#         "triggered_at": "2015-09-10T09:45:54.749Z",
#         "triggered": true,
#         "matching_messages": [
#             {
#                 "index": "graylog2_7",
#                 "message": "WARN: System is failing",
#                 "fields": {
#                     "gl2_remote_ip": "127.0.0.1",
#                     "gl2_remote_port": 56498,
#                     "gl2_source_node": "41283fec-36b4-4352-a859-7b3d79846b3c",
#                     "gl2_source_input": "55f15092bee8e2841898eb53"
#                 },
#                 "id": "b7b08150-57a0-11e5-b2a2-d6b4cd83d1d5",
#                 "stream_ids": [
#                     "55f1509dbee8e2841898eb64"
#                 ],
#                 "source": "127.0.0.1",
#                 "timestamp": "2015-09-10T09:45:49.284Z"
#             },
#             {
#                 "index": "graylog2_7",
#                 "message": "ERROR: This is an example error message",
#                 "fields": {
#                     "gl2_remote_ip": "127.0.0.1",
#                     "gl2_remote_port": 56481,
#                     "gl2_source_node": "41283fec-36b4-4352-a859-7b3d79846b3c",
#                     "gl2_source_input": "55f15092bee8e2841898eb53"
#                 },
#                 "id": "afd71342-57a0-11e5-b2a2-d6b4cd83d1d5",
#                 "stream_ids": [
#                     "55f1509dbee8e2841898eb64"
#                 ],
#                 "source": "127.0.0.1",
#                 "timestamp": "2015-09-10T09:45:36.116Z"
#             }
#         ]
#     },
#     "stream": {
#         "creator_user_id": "admin",
#         "outputs": [],
#         "matching_type": "AND",
#         "description": "test stream",
#         "created_at": "2015-09-10T09:42:53.833Z",
#         "disabled": false,
#         "rules": [
#             {
#                 "field": "gl2_source_input",
#                 "stream_id": "55f1509dbee8e2841898eb64",
#                 "id": "55f150b5bee8e2841898eb7f",
#                 "type": 1,
#                 "inverted": false,
#                 "value": "55f15092bee8e2841898eb53"
#             }
#         ],
#         "alert_conditions": [
#             {
#                 "creator_user_id": "admin",
#                 "created_at": "2015-09-10T09:44:10.552Z",
#                 "id": "5e7a9c8d-9bb1-47b6-b8db-4a3a83a25e0c",
#                 "type": "message_count",
#                 "parameters": {
#                     "grace": 1,
#                     "threshold": 1,
#                     "threshold_type": "more",
#                     "backlog": 5,
#                     "time": 1
#                 }
#             }
#         ],
#         "id": "55f1509dbee8e2841898eb64",
#         "title": "test",
#         "content_pack": null
#     }
# }



def parse_graylog(alert):

    return Alert(
        resource=alert['stream']['title'],
        environment='Production',
        service=[],
        value=alert['check_result']['result_description'],
        text=alert['check_result']['result_description'],
        attributes={'checkId': alert['check_result']['triggered_condition']['id']},
        origin='Graylog',
        event_type='performanceAlert',
        raw_data=alert)


@webhooks.route('/webhooks/graylog', methods=['OPTIONS', 'POST'])
@cross_origin()
@permission('write:webhooks')
def graylog():

    try:
        incomingAlert = parse_graylog(request.json)
    except ValueError as e:
        raise ApiError(str(e), 400)

    if g.get('customer', None):
        incomingAlert.customer = g.get('customer')

    add_remote_ip(request, incomingAlert)

    try:
        alert = process_alert(incomingAlert)
    except RejectException as e:
        raise ApiError(str(e), 403)
    except Exception as e:
        raise ApiError(str(e), 500)

    if alert:
        return jsonify(status="ok", id=alert.id, alert=alert.serialize), 201
    else:
        raise ApiError("insert or update of graylog check failed", 500)
