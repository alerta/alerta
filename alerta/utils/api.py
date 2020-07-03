import logging
from typing import Optional, Tuple

from flask import current_app, g

from alerta.app import plugins
from alerta.exceptions import (ApiError, BlackoutPeriod, ForwardingLoop,
                               HeartbeatReceived, RateLimit, RejectException)
from alerta.models.alert import Alert
from alerta.models.enums import Scope


def assign_customer(wanted: str = None, permission: Scope = Scope.admin_alerts) -> Optional[str]:
    customers = g.get('customers', [])
    if wanted:
        if Scope.admin in g.scopes or permission in g.scopes:
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


def process_alert(alert: Alert) -> Alert:

    wanted_plugins, wanted_config = plugins.routing(alert)

    skip_plugins = False
    for plugin in wanted_plugins:
        if alert.is_suppressed:
            skip_plugins = True
            break
        try:
            alert = plugin.pre_receive(alert, config=wanted_config)
        except TypeError:
            alert = plugin.pre_receive(alert)  # for backward compatibility
        except (RejectException, HeartbeatReceived, BlackoutPeriod, RateLimit, ForwardingLoop):
            raise
        except Exception as e:
            if current_app.config['PLUGINS_RAISE_ON_ERROR']:
                raise RuntimeError("Error while running pre-receive plugin '{}': {}".format(plugin.name, str(e)))
            else:
                logging.error("Error while running pre-receive plugin '{}': {}".format(plugin.name, str(e)))
        if not alert:
            raise SyntaxError("Plugin '%s' pre-receive hook did not return modified alert" % plugin.name)

    try:
        is_duplicate = alert.is_duplicate()
        if is_duplicate:
            alert = alert.deduplicate(is_duplicate)
        else:
            is_correlated = alert.is_correlated()
            if is_correlated:
                alert = alert.update(is_correlated)
            else:
                alert = alert.create()
    except Exception as e:
        raise ApiError(str(e))

    updated = None
    for plugin in wanted_plugins:
        if skip_plugins:
            break
        try:
            updated = plugin.post_receive(alert, config=wanted_config)
        except TypeError:
            updated = plugin.post_receive(alert)  # for backward compatibility
        except Exception as e:
            if current_app.config['PLUGINS_RAISE_ON_ERROR']:
                raise ApiError("Error while running post-receive plugin '{}': {}".format(plugin.name, str(e)))
            else:
                logging.error("Error while running post-receive plugin '{}': {}".format(plugin.name, str(e)))
        if updated:
            alert = updated

    if updated:
        alert.tag(alert.tags)
        alert.update_attributes(alert.attributes)

    return alert


def process_action(alert: Alert, action: str, text: str, timeout: int = None) -> Tuple[Alert, str, str, Optional[int]]:
    wanted_plugins, wanted_config = plugins.routing(alert)

    updated = None
    for plugin in wanted_plugins:
        if alert.is_suppressed:
            break
        try:
            updated = plugin.take_action(alert, action, text, timeout=timeout, config=wanted_config)
        except NotImplementedError:
            pass  # plugin does not support action() method
        except (RejectException, ForwardingLoop):
            raise
        except Exception as e:
            if current_app.config['PLUGINS_RAISE_ON_ERROR']:
                raise ApiError("Error while running action plugin '{}': {}".format(plugin.name, str(e)))
            else:
                logging.error("Error while running action plugin '{}': {}".format(plugin.name, str(e)))

        if isinstance(updated, Alert):
            updated = updated, action, text, timeout
        if isinstance(updated, tuple):
            if len(updated) == 4:
                alert, action, text, timeout = updated
            elif len(updated) == 3:
                alert, action, text = updated

    # remove keys from attributes with None values
    new_attrs = {k: v for k, v in alert.attributes.items() if v is not None}
    alert.attributes = new_attrs

    return alert, action, text, timeout


def process_status(alert: Alert, status: str, text: str) -> Tuple[Alert, str, str]:

    wanted_plugins, wanted_config = plugins.routing(alert)

    updated = None
    for plugin in wanted_plugins:
        if alert.is_suppressed:
            break
        try:
            updated = plugin.status_change(alert, status, text, config=wanted_config)
        except TypeError:
            updated = plugin.status_change(alert, status, text)  # for backward compatibility
        except RejectException:
            raise
        except Exception as e:
            if current_app.config['PLUGINS_RAISE_ON_ERROR']:
                raise ApiError("Error while running status plugin '{}': {}".format(plugin.name, str(e)))
            else:
                logging.error("Error while running status plugin '{}': {}".format(plugin.name, str(e)))
        if updated:
            try:
                alert, status, text = updated
            except Exception:
                alert = updated

    # remove keys from attributes with None values
    new_attrs = {k: v for k, v in alert.attributes.items() if v is not None}
    alert.attributes = new_attrs

    return alert, status, text


def process_delete(alert: Alert) -> bool:

    wanted_plugins, wanted_config = plugins.routing(alert)

    delete = True
    for plugin in wanted_plugins:
        try:
            delete = delete and plugin.delete(alert, config=wanted_config)
        except NotImplementedError:
            pass  # plugin does not support delete() method
        except RejectException:
            raise
        except Exception as e:
            if current_app.config['PLUGINS_RAISE_ON_ERROR']:
                raise ApiError("Error while running delete plugin '{}': {}".format(plugin.name, str(e)))
            else:
                logging.error("Error while running delete plugin '{}': {}".format(plugin.name, str(e)))

    return delete and alert.delete()
