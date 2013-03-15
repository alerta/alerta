
import json
import datetime

from flask import request, current_app
from functools import wraps
from alerta.api.v2 import app, db

from alerta.common import config
from alerta.common import log as logging
from alerta.alert import Alert
from alerta.common.utils import DateEncoder

Version = '2.0.0'

LOG = logging.getLogger(__name__)
CONF = config.CONF

# TODO(nsatterl): put these constants somewhere appropriate
_MAX_HISTORY = -10  # 10 most recent

# Over-ride jsonify to support Date Encoding
def jsonify(*args, **kwargs):
    return current_app.response_class(json.dumps(dict(*args, **kwargs), cls=DateEncoder,
                                                 indent=None if request.is_xhr else 2), mimetype='application/json')

# TODO(nsatterl): use @before_request and @after_request to attach a unique request id
@app.before_first_request
def before_request():
    # print "load config file with warning message"
    pass


# TODO(nsatterl): fix JSON-P
def jsonp(func):
    """Wraps JSONified output for JSONP requests."""
    @wraps(func)
    def decorated_function(*args, **kwargs):
        callback = request.args.get('callback', False)
        if callback:
            data = str(func(*args, **kwargs).data)
            content = str(callback) + '(' + data + ')'
            mimetype = 'application/javascript'
            return current_app.response_class(content, mimetype=mimetype)
        else:
            return func(*args, **kwargs)
    return decorated_function


@app.route('/alerta/api/v2/alerts/alert/<alertid>')
def get_alert(alertid):

    alert = db.get_alert(alertid=alertid)
    if alert:
        return jsonify(response={"alert": alert.get_body(), "status": "ok", "total": 1})
    else:
        return jsonify(response={"alert": None, "status": "error", "message": "not found", "total": 0})

@app.route('/alerta/api/v2/alerts')
def get_alerts():

    hide_details = request.args.get('hide-alert-details', False, bool)
    hide_alert_repeats = request.args.getlist('hide-alert-repeats')

    # TODO(nsatterl): support comma-separated fields eg. fields=event,summary
    fields = dict((k, 1) for k in request.args.getlist('fields'))

    # NOTE: if filtering on fields still always include severity and status in response
    if fields:
        fields['severity'] = 1
        fields['status'] = 1

    if request.args.get('hide-alert-history', False, bool):
        fields['history'] = 0
    else:
        fields['history'] = {'slice': _MAX_HISTORY}

    alert_limit = request.args.get('limit', 0, int)

    query = dict()
    query_time = datetime.datetime.utcnow()

    from_date = request.args.get('from-date')
    if from_date:
        from_date = datetime.datetime.strptime(from_date, '%Y-%m-%dT%H:%M:%S.%fZ')
        from_date = from_date.replace(tzinfo=pytz.utc)
        to_date = query_time
        to_date = to_date.replace(tzinfo=pytz.utc)
        query['lastReceiveTime'] = {'$gt': from_date, '$lte': to_date}

    sort_by = list()
    for s in request.args.getlist('sort-by'):
            if s in ['createTime', 'receiveTime', 'lastReceiveTime']:
                sort_by.append((s, -1))  # sort by newest first
            else:
                sort_by.append((s, 1))   # alpha-numeric sort
    if not sort_by:
        sort_by.append(('lastReceiveTime', -1))



    return jsonify(details=hide_details, repeats=hide_alert_repeats, fields=fields)


@app.route('/alerta/api/v1/alerts/alert.json', methods=['POST', 'PUT'])
def create_alert(alertid):

    pass

@app.route('/alerta/api/v2/alerts/alert/<alertid>', methods=['POST', 'PUT'])
def modify_alert(alertid):

    #db.modify_alert()

    pass


@app.route('/alerta/api/v2/alerts/alert/<alertid>/tag', methods=['POST', 'PUT'])
def tag_alert(alertid):

    pass


@app.route('/alerta/api/v2/alerts/alert/<alertid>', methods=['DELETE'])
def delete_alert(alertid):

    pass


@app.route('/alerta/api/v2/resources')
def get_resources(alertid):

    pass



def fix_id(alert):
    if '_id' in alert:
        alert['id'] = alert['_id']
        del alert['_id']
    return alert

