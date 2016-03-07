
import socket

from alerta.app import app
from alerta.plugins import PluginBase

LOG = app.logger


class LogStashOutput(PluginBase):

    def __init__(self):
        self.sock = None

    def pre_receive(self, alert):
        return alert

    def post_receive(self, alert):
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.connect((app.config['LOGSTASH_HOST'], app.config['LOGSTASH_PORT']))
        except Exception as e:
            raise RuntimeError("Logstash TCP connection error: %s" % str(e))

        try:
            self.sock.send("%s\r\n" % alert)
        except Exception as e:
            LOG.exception(e)
            raise RuntimeError("logstash exception")

        self.sock.close()

    def status_change(self, alert, status, text):
        return
