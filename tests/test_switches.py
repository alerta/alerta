
import os
import sys

# If ../nova/__init__.py exists, add ../ to Python search path, so that
# it will override what happens to be installed in /usr/(local/)lib/python...
possible_topdir = os.path.normpath(os.path.join(os.path.abspath(sys.argv[0]),
                                                os.pardir,
                                                os.pardir))
if os.path.exists(os.path.join(possible_topdir, 'alerta', '__init__.py')):
    sys.path.insert(0, possible_topdir)

from alerta.api.v2.switch import Switch, SwitchState


switches = [
    Switch('switch1', 'test switch 1 default=ON', SwitchState.ON),
    Switch('switch2', 'test switch 2 default=OFF', SwitchState.OFF),
]

print switches

print Switch.get('switch1')

turn_off = Switch.get('switch1')
turn_off.set_state('OFF')

print turn_off.is_on()
print Switch.get('switch2').is_on()

print Switch.get_all()

