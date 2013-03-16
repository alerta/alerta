
import json
import datetime
from collections import defaultdict

from flask import request, current_app
from functools import wraps
from alerta.api.v2 import app, db

from alerta.common import config
from alerta.common import log as logging
from alerta.alert import Alert, severity, status
from alerta.common.utils import DateEncoder

Version = '2.0.0'

LOG = logging.getLogger(__name__)
CONF = config.CONF

# TODO(nsatterl): put these constants somewhere appropriate
_MAX_HISTORY = -10  # 10 most recent
_LIMIT = 100

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

    found, alert = db.get_alert(alertid=alertid)
    if found:
        return jsonify(response={"alert": alert.get_body(), "status": "ok", "total": 1})
    else:
        return jsonify(response={"alert": None, "status": "error", "message": "not found", "total": 0})

@app.route('/alerta/api/v2/alerts')
def get_alerts():

    limit = request.args.get('limit', _LIMIT, int)
    alert_details = list()

    found, alerts = db.get_alerts(limit=limit)
    print 'found=%s' % found
    if found > 0:
        more = True if found > limit else False

        severity_count = defaultdict(int)
        status_count = defaultdict(int)
        last_time = None

        for alert in alerts:
            body = alert.get_body()
            alert_details.append(body)

            severity_count[body['severity']] += 1
            status_count[body['status']] += 1

            if not last_time:
                last_time = body['lastReceiveTime']
            elif body['lastReceiveTime'] > last_time:
                last_time = body['lastReceiveTime']

        return jsonify(response={
            "alerts": {
                "alertDetails": alert_details,
                "severityCounts": {
                    "critical": severity_count[severity.CRITICAL],
                    "major": severity_count[severity.MAJOR],
                    "minor": severity_count[severity.MINOR],
                    "warning": severity_count[severity.WARNING],
                    "indeterminate": severity_count[severity.INDETERMINATE],
                    "cleared": severity_count[severity.CLEARED],
                    "normal": severity_count[severity.NORMAL],
                    "informational": severity_count[severity.INFORM],
                    "debug": severity_count[severity.DEBUG],
                    "auth": severity_count[severity.AUTH],
                    "unknown": severity_count[severity.UNKNOWN],
                },
                "statusCounts": {
                    "open": status_count[status.OPEN],
                    "acknowledged": status_count[status.ACK],
                    "closed": status_count[status.CLOSED],
                    "expired": status_count[status.EXPIRED],
                    "unknown": status_count[status.UNKNOWN],
                },
                "lastTime": last_time,
            },
            "status": "ok",
            "total": found,
            "more": more
        })
    else:
        return jsonify(response={
            "alerts": {
                "alertDetails": list(),
                "severityCounts": {
                    "critical": 0,
                    "major": 0,
                    "minor": 0,
                    "warning": 0,
                    "indeterminate": 0,
                    "cleared": 0,
                    "normal": 0,
                    "informational": 0,
                    "debug": 0,
                    "auth": 0,
                    "unknown": 0,
                    },
                "statusCounts": {
                    "open": 0,
                    "acknowledged": 0,
                    "closed": 0,
                    "expired": 0,
                    "unknown": 0,
                    },
                "lastTime": None,
            },
            "status": "error",
            "error": "not found",
            "total": 0,
            "more": False,
        })

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

