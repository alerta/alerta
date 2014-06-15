
import time
import threading

from alerta.common import config
from alerta.common import log as logging

LOG = logging.getLogger(__name__)
CONF = config.CONF
lock = threading.Lock()


class LeakyBucket(threading.Thread):

    token_opts = {
        'token_limit': 20,
        'token_rate': 2,
    }

    def __init__(self, tokens=None, limit=None, rate=None):

        config.register_opts(LeakyBucket.token_opts)

        self.tokens = tokens or CONF.token_limit
        self.limit = limit or tokens or CONF.token_limit
        self.rate = rate or float(CONF.token_rate)

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

            if self.tokens < self.limit:
                with lock:
                    self.tokens += 1
                LOG.debug('Token top-up! Now %s tokens', self.tokens)

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
                LOG.debug('Got a token! There are %s left', self.tokens)
                return True
            else:
                LOG.debug('Sorry, no tokens left')
                return False

    def get_count(self):
        return self.tokens
