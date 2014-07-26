
import socket
import logging

from alerta import settings
from alerta.plugins import PluginBase

LOG = logging.getLogger(__name__)


class LogStashOutput(PluginBase):

    def send(self, alert):

        data = {
            "@version": "1",
            "@timestamp": alert.last_receive_time,
            "message": alert.text,
            "source_host": alert.resource
        }

        data.update(dict(alert.get_body()))

        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.connect((settings.LOGSTASH_HOST, settings.LOGSTASH_PORT))
        except Exception:
            raise RuntimeError("Logstash connection error")

        try:
            self.sock.send("%s\r\n" % data)
        except Exception as e:
            LOG.exception(e)
            raise RuntimeError("logstash exception")

        self.sock.close()
