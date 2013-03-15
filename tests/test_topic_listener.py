#!/usr/bin/env python
########################################
#
# test_topic_listener
#
########################################

import os
import sys
import time
import json
import stomp
import logging

BROKER_LIST  = [('localhost', 61613)] # list of brokers for failover
NOTIFY_TOPIC = '/topic/notify'


class MessageHandler(object):

    def on_message(self, headers, body):

        logging.debug("Received alert : %s", body)
        alert = json.loads(body)
        print alert


def main():

    # Connect to message broker
    try:
        conn = stomp.Connection(
            BROKER_LIST,
            reconnect_sleep_increase = 5.0,
            reconnect_sleep_max = 120.0,
            reconnect_attempts_max = 20
        )
        conn.set_listener('', MessageHandler())
        conn.start()
        conn.connect(wait=True)
        conn.subscribe(destination=NOTIFY_TOPIC)
    except Exception, e:
        logging.error('Stomp connection error: %s', e)

    while True:
        try:
            time.sleep(1)
        except (KeyboardInterrupt, SystemExit):
            conn.disconnect()
            sys.exit(0)

if __name__ == '__main__':
    main()