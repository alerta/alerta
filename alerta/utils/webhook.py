
from pkg_resources import iter_entry_points


class WebhookRule:
    def __init__(self, rule, endpoint, methods):
        self.rule = rule
        self.endpoint = endpoint
        self.methods = methods


class CustomWebhooks:
    def __init__(self):
        self.webhooks = dict()

    def register(self, app):
        for ep in iter_entry_points('alerta.webhooks'):
            try:
                webhook = ep.load()
                if webhook:
                    self.webhooks[ep.name] = webhook()
            except Exception as e:
                app.log.warn('Failed to load custom webhook {} - {}'.format(ep.name, e))

    def iter_rules(self):
        return iter([
            WebhookRule(
                rule='/webhooks/{}'.format(name),
                endpoint='webhooks.{}'.format(name),
                methods=['POST', 'GET']
            ) for name, ep in self.webhooks.items()])
