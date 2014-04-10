
from flask import request, render_template, send_from_directory

from alerta.dashboard.v2 import app
from alerta.common import config
from alerta.common import log as logging
from alerta.common.api import ApiClient


__version__ = '3.0.1'

LOG = logging.getLogger(__name__)
CONF = config.CONF

ApiClient()  # set API variables eg. endpoint

# Only use when running API in stand-alone mode during testing
@app.route('/dashboard/<path:filename>')
def assets(filename):

    return send_from_directory(CONF.dashboard_dir, filename)


@app.route('/dashboard/<name>')
def console(name):

    return render_template(name, config=CONF)


@app.route('/dashboard/severity')
def severity_widget():

    label = request.args.get('label', 'Alert Severity')

    return render_template('widgets/severity.html', config=CONF, label=label, query=request.query_string)


@app.route('/dashboard/status')
def status_widget():

    label = request.args.get('label', None)

    return render_template('widgets/status.html', config=CONF, label=label, query=request.query_string)


@app.route('/dashboard/details')
def details_widget():

    label = request.args.get('label', 'Alert Details')

    return render_template('widgets/details.html', config=CONF, label=label, query=request.query_string)
