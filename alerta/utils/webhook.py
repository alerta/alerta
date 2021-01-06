from typing import TYPE_CHECKING, Iterator

from flask import Flask
from pkg_resources import iter_entry_points

if TYPE_CHECKING:
    from typing import Dict  # noqa
    from alerta.webhooks import WebhookBase  # noqa


class WebhookRule:

    def __init__(self, rule, endpoint, methods):
        self.rule = rule
        self.endpoint = endpoint
        self.methods = methods


class CustomWebhooks:

    def __init__(self) -> None:
        self.webhooks = dict()  # type: Dict[str, WebhookBase]

    def register(self, app: Flask) -> None:
        for ep in iter_entry_points('alerta.webhooks'):
            app.logger.debug("Server webhook '{}' found.".format(ep.name))
            try:
                webhook = ep.load()
                if webhook:
                    self.webhooks[ep.name] = webhook()
                    app.logger.info("Server webhook '{}' loaded.".format(ep.name))
            except Exception as e:
                app.logger.warning("Failed to load webhook '{}': {}".format(ep.name, e))

    def iter_rules(self) -> Iterator[WebhookRule]:
        return iter([
            WebhookRule(
                rule='/webhooks/{}'.format(name),
                endpoint='webhooks.{}'.format(name),
                methods=['POST', 'GET']
            ) for name, ep in self.webhooks.items()])
