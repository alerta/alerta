from alerta.api.v2 import app

@app.route('/management/status')
def mgmt_status():
    return "management status output!"
