#!/usr/bin/env python
from alerta import create_app

activate_this = '/opt/alerta/bin/activate_this.py'
execfile(activate_this, dict(__file__=activate_this))
application = create_app()
