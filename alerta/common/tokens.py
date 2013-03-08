
import time
import threading

from alerta.alert.common import config

CONF = config.CONF
lock = threading.Lock()


class LeakyBucket(threading.Thread):

    def __init__(self, tokens=None, rate=None):

        self.tokens = tokens or CONF.token_limit
        self.rate = rate or CONF.token_rate

        threading.Thread.__init__(self)

        self.running = False
        self.shuttingdown = False

    def shutdown(self):

        self.shuttingdown = True

        if not self.running:
            return
        self.join()

    def run(self):

        self.running = True

        while not self.shuttingdown:

            if self.shuttingdown:
                break

            if self.tokens < CONF.token_limit:
                with lock:
                    self.tokens += 1

            if not self.shuttingdown:
                time.sleep(self.rate)

        self.running = False

    def is_token(self):
        if self.tokens > 0:
            return True
        else:
            return False

    def get_token(self):
        with lock:
            if self.is_token():
                self.tokens -= 1
                return True
            else:
                return False
