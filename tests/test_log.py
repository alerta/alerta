from logging import getLogger
from alerta import log as logging

from alerta.mymodule import MyClass

logging.setup()

LOG = getLogger(__name__)
LOG.critical('test critical')

A = MyClass()

LOG.critical('test critical2')
