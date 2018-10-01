
from datetime import datetime

from flask import g, jsonify, request
from flask_cors import cross_origin

from alerta.auth.decorators import permission
from alerta.exceptions import (ApiError, BlackoutPeriod, RateLimit,
                               RejectException)
from alerta.models.alert import Alert
from alerta.models.metrics import Timer, timer
from alerta.models.switch import Switch
from alerta.utils.api import (add_remote_ip, assign_customer, jsonp,
                              process_action, process_alert, process_status)
from alerta.utils.paging import Page

from . import api

receive_timer = Timer('alerts', 'received', 'Received alerts', 'Total time and number of received alerts')
gets_timer = Timer('alerts', 'queries', 'Alert queries', 'Total time and number of alert queries')
status_timer = Timer('alerts', 'status', 'Alert status change', 'Total time and number of alerts with status changed')
tag_timer = Timer('alerts', 'tagged', 'Tagging alerts', 'Total time to tag number of alerts')
untag_timer = Timer('alerts', 'untagged', 'Removing tags from alerts', 'Total time to un-tag and number of alerts')
attrs_timer = Timer('alerts', 'attributes', 'Alert attributes change',
                    'Total time and number of alerts with attributes changed')
delete_timer = Timer('alerts', 'deleted', 'Deleted alerts', 'Total time and number of deleted alerts')
count_timer = Timer('alerts', 'counts', 'Count alerts', 'Total time and number of count queries')


@api.route('/alert/<alert_id>', methods=['OPTIONS', 'GET'])
@cross_origin()
@permission('read:alerts')
@timer(gets_timer)
@jsonp
def get_alert(alert_id):
    customers = g.get('customers', None)
    alert = Alert.find_by_id(alert_id, customers)

    if alert:
        return jsonify(status='ok', total=1, alert=alert.serialize)
    else:
        raise ApiError('not found', 404)

