from typing import List, Optional

from alerta.app import create_celery_app
from alerta.exceptions import InvalidAction, RejectException
from alerta.models.alert import Alert
from alerta.utils.api import process_action, process_status

celery = create_celery_app()


@celery.task
def action_alerts(alerts: List[str], action: str, text: str, timeout: Optional[int]) -> None:
    updated = []
    errors = []
    for alert_id in alerts:
        alert = Alert.find_by_id(alert_id)

        try:
            previous_status = alert.status
            alert, action, text, timeout = process_action(alert, action, text, timeout)
            alert = alert.from_action(action, text, timeout)
        except RejectException as e:
            errors.append(str(e))
            continue
        except InvalidAction as e:
            errors.append(str(e))
            continue
        except Exception as e:
            errors.append(str(e))
            continue

        if previous_status != alert.status:
            try:
                alert, status, text = process_status(alert, alert.status, text)
                alert = alert.from_status(status, text, timeout)
            except RejectException as e:
                errors.append(str(e))
                continue
            except Exception as e:
                errors.append(str(e))
                continue

        updated.append(alert.id)
