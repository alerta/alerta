#/usr/bin/env python

activate_this = '/opt/alerta/bin/activate_this.py'
execfile(activate_this, dict(__file__=activate_this))

from alerta.dashboard.v2 import app as application