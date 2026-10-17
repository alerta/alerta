import json
from typing import Any, List, Optional, Tuple

DEDUP_KEY_MAX_LENGTH = 255

TEMPLATE_FIELDS = {
    'resource': 'resource',
    'event': 'event',
    'group': 'group',
    'service': 'service',
    'origin': 'origin',
    'type': 'event_type',
}


def is_attribute_field(field: str) -> bool:
    return field.startswith('attributes.') and len(field) > len('attributes.')


def validate_template(fields: List[str]) -> None:
    if not fields:
        raise ValueError('DEDUP_KEY_FIELDS must not be empty')
    for field in fields:
        if field not in TEMPLATE_FIELDS and not is_attribute_field(field):
            raise ValueError(f"DEDUP_KEY_FIELDS: unsupported field '{field}'")
    if len(set(fields)) != len(fields):
        raise ValueError('DEDUP_KEY_FIELDS must not repeat a field')


def field_value(alert, field: str) -> Any:
    if is_attribute_field(field):
        return alert.attributes.get(field[len('attributes.'):])
    return getattr(alert, TEMPLATE_FIELDS[field])


def encode(values: List[Any]) -> str:
    # must match jsonb_build_array(...)::text for the 0002 backfill
    return json.dumps(values, ensure_ascii=False)


def alert_keys(alert, fields: List[str]) -> Tuple[str, str, Optional[str]]:
    """
    Return (dedup_key, key_source, correlate_key). correlate_key is the template key without
    event, so the correlate list only applies to template keys that include event. Keys already
    set, by the sender or when the alert was stored, are kept so a template change does not
    re-key existing alerts.
    """
    if alert.dedup_key is not None:
        return alert.dedup_key, alert.key_source, alert.correlate_key
    dedup_key = encode([field_value(alert, f) for f in fields])
    correlate_key = encode([field_value(alert, f) for f in fields if f != 'event']) if 'event' in fields else None
    return dedup_key, 'template', correlate_key
