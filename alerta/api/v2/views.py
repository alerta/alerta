from alerta.api.v2 import app

@app.route('/here')
def hello_world():
    return "Hello World, too three!"
