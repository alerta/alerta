import logging
import os
import re

import psycopg2
import six
from psycopg2.extras import NamedTupleCursor

from alerta.models.alert import Alert


def rule_matches(regex, value):
    if isinstance(value, list):
        logging.getLogger('').debug('%s is a list, at least one item must match %s', value, regex)
        for item in value:
            if re.match(regex, item) is not None:
                logging.getLogger('').debug('Regex %s matches item %s', regex, item)
                return True
        logging.getLogger('').debug('Regex %s matches nothing', regex)
        return False
    elif isinstance(value, six.string_types):  # pylint: disable=undefined-variable
        logging.getLogger('').debug('Trying to match %s to %s', value, regex)


def get_customer_forward_rules(customer_id):
    query = f"select * from customer_rules where customer_id='{customer_id}'"
    conn = psycopg2.connect(
        dsn=os.environ['DATABASE_URL'],
        dbname=os.environ.get('DATABASE_NAME'),
        cursor_factory=NamedTupleCursor
    )
    conn.set_client_encoding('UTF8')
    cursor = conn.cursor()
    cursor.execute(query)
    try:
        result = cursor.fetchall()
        return result
    finally:
        conn.close()


def process_forward_rules_for_alert(alert: Alert):
    from alerta.app import webhook
    rules = get_customer_forward_rules(alert.customer)
    for rule in rules:
        logging.getLogger('').debug('Evaluating rule %s', rule['name'])
        is_matching = False
        for field in rule['fields']:
            logging.getLogger('').debug('Evaluating rule field %s', field)
            value = getattr(alert, field['field'], None)
            if value is None:
                logging.getLogger('').warning('Alert has no attribute %s',
                                              field['field'])
                break
            if rule_matches(field['regex'], value):
                is_matching = True
            else:
                is_matching = False
                break
        matching_rule_id = rule.id
        if is_matching:
            for plugin in [webhook]:
                try:
                    plugin.post_receive(alert, rule_id=matching_rule_id)
                except TypeError:
                    plugin.post_receive(alert, rule_id=matching_rule_id)
                except Exception as e:
                    logging.error(f"Error while running post-receive plugin '{plugin.name}': {str(e)}")
