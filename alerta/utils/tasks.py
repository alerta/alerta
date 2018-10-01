
from alerta.app import create_celery_app
from alerta.exceptions import RejectException
from alerta.utils.api import process_action, process_status

celery = create_celery_app()


@celery.task
def action_alerts(alerts, action, text, timeout):
    updated = []
    errors = []
    for alert in alerts:
        try:
            severity, status = process_action(alert, action)
            alert, status, text = process_status(alert, status, text)
        except RejectException as e:
            errors.append(str(e))
            continue
        except Exception as e:
            errors.append(str(e))
            continue

        if alert.set_severity_and_status(severity, status, text, timeout):
            updated.append(alert.id)
