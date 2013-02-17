from flask import Flask

app = Flask(__name__)
# app.config.from_object('alerta.api')
# app.config.from_envvar('ALERTA_SETTINGS', silent=True)

import views
import management.views

if __name__ == '__main__':
    app.run(debug=True)