
from pkg_resources import iter_entry_points


class CustomWebhooks(object):
    def __init__(self):
        self.webhooks = dict()

    def register(self, app):

        for ep in iter_entry_points('alerta.webhooks'):
            try:
                webhook = ep.load()
                if webhook:
                    self.webhooks[ep.name] = webhook()
            except Exception as e:
                app.log.warn('Failed to load custom webhook %s - %s' % (ep.name, e))
