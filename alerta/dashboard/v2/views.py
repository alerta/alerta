
from flask import request, render_template, send_from_directory

from alerta.dashboard.v2 import app
from alerta.common import config
from alerta.common import log as logging
from alerta.common.api import ApiClient


Version = '2.1.0'

LOG = logging.getLogger(__name__)
CONF = config.CONF

ApiClient()  # set API variables eg. api_host, api_port

# Only use when running API in stand-alone mode during testing
@app.route('/alerta/dashboard/v2/assets/<path:filename>')
def assets(filename):

    return send_from_directory(CONF.dashboard_dir, filename)


@app.route('/alerta/dashboard/v2/<name>')
def console(name):

    return render_template(name, config=CONF)


@app.route('/alerta/widgets/v2/severity')
def severity_widget():

    label = request.args.get('label', 'Alert Severity')

    return render_template('widgets/severity.html', config=CONF, label=label, query=request.query_string)


@app.route('/alerta/widgets/v2/status')
def status_widget():

    label = request.args.get('label', None)

    return render_template('widgets/status.html', config=CONF, label=label, query=request.query_string)


@app.route('/alerta/widgets/v2/details')
def details_widget():

    label = request.args.get('label', 'Alert Details')

    return render_template('widgets/details.html', config=CONF, label=label, query=request.query_string)
