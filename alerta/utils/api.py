
import logging
from typing import Optional, Tuple

from flask import Request, current_app, g

from alerta.app import plugins
from alerta.exceptions import (ApiError, BlackoutPeriod, RateLimit,
                               RejectException)
from alerta.models.alert import Alert


def assign_customer(wanted: str, permission: str='admin:alerts') -> Optional[str]:
    customers = g.get('customers', [])
    if wanted:
        if 'admin' in g.scopes or permission in g.scopes:
            return wanted
        if wanted not in customers:
            raise ApiError("not allowed to set customer to '%s'" % wanted, 400)
        else:
            return wanted
    if customers:
        if len(customers) > 1:
            raise ApiError('must define customer as more than one possibility', 400)
        else:
            return customers[0]
    return None


def add_remote_ip(req: Request, alert: Alert) -> None:
    if req.headers.getlist('X-Forwarded-For'):
        alert.attributes.update(ip=req.headers.getlist('X-Forwarded-For')[0])
    else:
        alert.attributes.update(ip=req.remote_addr)


def process_alert(alert: Alert) -> Alert:

    skip_plugins = False
    for plugin in plugins.routing(alert):
        if alert.is_suppressed:
            skip_plugins = True
            break
        try:
            alert = plugin.pre_receive(alert)
        except (RejectException, BlackoutPeriod, RateLimit):
            raise
        except Exception as e:
            if current_app.config['PLUGINS_RAISE_ON_ERROR']:
                raise RuntimeError("Error while running pre-receive plug-in '{}': {}".format(plugin.name, str(e)))
            else:
                logging.error("Error while running pre-receive plug-in '{}': {}".format(plugin.name, str(e)))
        if not alert:
            raise SyntaxError("Plug-in '%s' pre-receive hook did not return modified alert" % plugin.name)

    try:
        if alert.is_duplicate():
            alert = alert.deduplicate()
        elif alert.is_correlated():
            alert = alert.update()
        else:
            alert = alert.create()
    except Exception as e:
        raise ApiError(str(e))

    updated = None
    for plugin in plugins.routing(alert):
        if skip_plugins:
            break
        try:
            updated = plugin.post_receive(alert)
        except Exception as e:
            if current_app.config['PLUGINS_RAISE_ON_ERROR']:
                raise ApiError("Error while running post-receive plug-in '{}': {}".format(plugin.name, str(e)))
            else:
                logging.error("Error while running post-receive plug-in '{}': {}".format(plugin.name, str(e)))
        if updated:
            alert = updated

    if updated:
        alert.tag(alert.tags)
        alert.update_attributes(alert.attributes)

    return alert


def process_action(alert: Alert, action: str, text: str) -> Tuple[Alert, str, str]:

    updated = None
    for plugin in plugins.routing(alert):
        if alert.is_suppressed:
            break
        try:
            updated = plugin.take_action(alert, action, text)
        except NotImplementedError:
            pass  # plugin does not support action() method
        except RejectException:
            raise
        except Exception as e:
            if current_app.config['PLUGINS_RAISE_ON_ERROR']:
                raise ApiError("Error while running action plug-in '{}': {}".format(plugin.name, str(e)))
            else:
                logging.error("Error while running action plug-in '{}': {}".format(plugin.name, str(e)))
        if updated:
            try:
                alert, action, text = updated
            except Exception:
                alert = updated

    # remove keys from attributes with None values
    new_attrs = {k: v for k, v in alert.attributes.items() if v is not None}
    alert.attributes = new_attrs

    return alert, action, text


def process_status(alert: Alert, status: str, text: str) -> Tuple[Alert, str, str]:

    updated = None
    for plugin in plugins.routing(alert):
        if alert.is_suppressed:
            break
        try:
            updated = plugin.status_change(alert, status, text)
        except RejectException:
            raise
        except Exception as e:
            if current_app.config['PLUGINS_RAISE_ON_ERROR']:
                raise ApiError("Error while running status plug-in '{}': {}".format(plugin.name, str(e)))
            else:
                logging.error("Error while running status plug-in '{}': {}".format(plugin.name, str(e)))
        if updated:
            try:
                alert, status, text = updated
            except Exception:
                alert = updated

    # remove keys from attributes with None values
    new_attrs = {k: v for k, v in alert.attributes.items() if v is not None}
    alert.attributes = new_attrs

    return alert, status, text
