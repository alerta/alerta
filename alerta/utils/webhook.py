from importlib.metadata import entry_points as _entry_points
from typing import TYPE_CHECKING, Iterator

from flask import Flask

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
        try:
            eps = _entry_points(group='alerta.webhooks')
        except TypeError:
            eps = _entry_points().get('alerta.webhooks', [])
        for ep in eps:
            app.logger.debug(f"Server webhook '{ep.name}' found.")
            try:
                webhook = ep.load()
                if webhook:
                    self.webhooks[ep.name] = webhook()
                    app.logger.info(f"Server webhook '{ep.name}' loaded.")
            except Exception as e:
                app.logger.warning(f"Failed to load webhook '{ep.name}': {e}")

    def iter_rules(self) -> Iterator[WebhookRule]:
        return iter([
            WebhookRule(
                rule=f'/webhooks/{name}',
                endpoint=f'webhooks.{name}',
                methods=['POST', 'GET']
            ) for name, ep in self.webhooks.items()])
