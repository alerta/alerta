#!/usr/bin/env python
########################################
#
# alert-webapp.py - Alert Console
#
########################################

import os
import sys
import time
import curses
try:
    import json
except ImportError:
    import simplejson as json
try:
    import stomp
except ImportError:
    print >>sys.stderr, 'ERROR: You need to install the stomp python module'
    sys.exit(1)
import signal
import datetime
import pytz

__title__ = 'Alert Console'
__program__ = 'alert-webapp'
__version__ = '1.0.2'

BROKER_LIST  = [('monitoring.guprod.gnl', 61613),('localhost', 61613)] # list of brokers for failover
NOTIFY_TOPIC = '/topic/notify'

# Minimum screen size
SCREEN_MIN_X = 80
SCREEN_MIN_Y = 24

SCREEN_NODE_TABLE_START = 2
SCREEN_NODE_LIST_START = 2

ALERT_TABLE_COLUMNS = (
  {'name': 'lastReceiveId',   'label': 'alertid',  'width': 8,  'align': 'right'},
  {'name': 'severity',        'label': 'severity', 'width': 9,  'align': 'right'},
  {'name': 'status',          'label': 'status',   'width': 7,  'align': 'right'},
  {'name': 'lastReceiveTime', 'label': 'time',     'width': 19, 'align': 'center'},
  {'name': 'duplicateCount',  'label': 'dupl.',    'width': 5,  'align': 'right'},
  {'name': 'environment',     'label': 'env', 'width': 8, 'align': 'center'},
  {'name': 'service',         'label': 'service',  'width': 12, 'align': 'center'},
  {'name': 'resource',        'label': 'resource', 'width': 20, 'align': 'center'},
  {'name': 'group',           'label': 'group',    'width': 10, 'align': 'center'},
  {'name': 'event',           'label': 'event',    'width': 15, 'align': 'center'},
  {'name': 'value',           'label': 'value',    'width': 12, 'align': 'center'},
  {'name': 'text',            'label': 'text',     'width': 54, 'align': 'left'},
)
TOTAL_WIDTH = float(8 + 9 + 7 + 19 + 5 + 40 + 10 + 15 + 12 + 54)

SCREEN_REDRAW_INTERVAL = 0.1

alerts = list()

class MessageHandler(object):
    global alerts

    def on_error(self, headers, body):
        pass

    def on_message(self, headers, body):
        alert = dict()
        alert = json.loads(body)

        alerts.append(alert)

    def on_disconnected(self):
        global conn
        print >>sys.err, 'Connection lost. Attempting auto-reconnect to %s', NOTIFY_TOPIC
        conn.start()
        conn.connect(wait=True)
        # conn.subscribe(destination=NOTIFY_TOPIC, ack='auto', headers={'selector': "repeat = 'false'"})
        conn.subscribe(destination=NOTIFY_TOPIC, ack='auto', headers={})

class Screen():
    global alerts

    def __init__(self):
        self.screen = self._get_screen()

        self.min_y = 0
        self.min_x = 0

        self.cursor_pos = -1

        self.hide_repeat = False

    def run(self):
        while True:
            self._redraw()
            event = self.screen.getch()

            if 0 < event < 256:
                self._handle_key_event(chr(event))
            elif event in [curses.KEY_UP, curses.KEY_DOWN, curses.KEY_PPAGE, curses.KEY_NPAGE]:
                self._handle_movement_key(event)
            else:
                self._handle_event(event)

            time.sleep(SCREEN_REDRAW_INTERVAL)

    def _get_screen(self):
        screen = curses.initscr()
        curses.noecho()

        try:
            curses.curs_set(0)
        except Exception:
            pass

        if curses.has_colors():
            curses.start_color()
            curses.use_default_colors()

            curses.init_pair(1, curses.COLOR_WHITE, -1)
            curses.init_pair(2, curses.COLOR_GREEN, -1)
            curses.init_pair(3, curses.COLOR_BLUE, -1)
            curses.init_pair(4, curses.COLOR_RED, -1)

        screen.keypad(1)
        screen.nodelay(1)

        curses.def_prog_mode()

        return screen

    def _draw_header(self):
        time = datetime.datetime.strftime(datetime.datetime.now(), '%H:%M:%S %d/%m/%y')

        self.addstr(self.min_y, 'center', __title__, curses.A_BOLD)
        self.addstr(self.min_y, self.min_x, BROKER_LIST[0][0], curses.A_BOLD)
        self.addstr(self.min_y, 'right', time, curses.A_BOLD)
        self.screen.hline(self.min_y + 1, self.min_x, '_', self.max_x)

    def _draw_table_header(self):
        columns = []
        for column in ALERT_TABLE_COLUMNS:
            name, width, align = column['label'].upper(), column['width'], column['align']

            column_string = self._get_table_column_string(name, width, align)
            columns.append(column_string)

        columns = '' . join(columns)
        self.addstr(self.min_y + SCREEN_NODE_TABLE_START, self.min_x, columns, curses.A_REVERSE)

    def _get_table_column_string(self, text, width, align):
        # width = int(self.max_x * (width / 100.0))
        width = int(self.max_x * (width / TOTAL_WIDTH))

        if align == 'center':
            column_string = text.center(width)
        elif align == 'left':
            column_string = text.ljust(width)
        else:
            column_string = text.rjust(width)

        return column_string

    def _draw_alert_list(self):
        # Draws the node list in the bottom part of the screen
        self.table_lines = []
        index = 0
        for alert in alerts:
            if self.hide_repeat and alert['repeat']:
                continue
            coord_y = (self.min_y + SCREEN_NODE_LIST_START) + (index + 2)
            index += 1
            if coord_y < self.max_y - 1:
                columns = []
                for column in ALERT_TABLE_COLUMNS:
                    width, align = column['width'], column['align']
                    if column['name'] == 'lastReceiveTime':
                        lastReceiveTime = datetime.datetime.strptime(alert['lastReceiveTime'], '%Y-%m-%dT%H:%M:%S.%fZ')
                        lastReceiveTime = lastReceiveTime.replace(tzinfo=pytz.utc)
                        value = lastReceiveTime.strftime('%T %d/%m/%y')
                    elif column['name'] == 'lastReceiveId':
                        value = alert['lastReceiveId'][0:8]
                    elif column['name'] == 'environment':
                        value = ','.join(alert['environment'])
                    elif column['name'] == 'service':
                        value = ','.join(alert['service'])
                    else:
                        value = str(alert[column['name']])
                    column_string = self._get_table_column_string(value, width, align)
                    columns.append(column_string)

                columns = '' . join(columns)
                self.table_lines.append(columns)
                self.addstr(coord_y, self.min_x, columns)

    def _draw_footer(self):
        self.addstr(self.max_y, self.min_x,
                    'Updated: now',
                     curses.A_BOLD)
        self.addstr(self.max_y, 'center',
                    'Hide Repeats: %s' % (self.hide_repeat),
                    curses.A_BOLD)
        self.addstr(self.max_y, 'right',
                    'Alerts: %d' %
                    (len(alerts)),
                    curses.A_BOLD)

    def _redraw(self):
        self._update_max_size()
        self._check_min_screen_size()
   
        self.screen.clear()
        self._draw_header()
        self._draw_table_header()
        self._draw_alert_list()
        #self._draw_selection()
        self._draw_footer()
        #self._draw_node_data()

        #self.screen.refresh()
        curses.doupdate()

    def _update_max_size(self):
        max_y, max_x = self.screen.getmaxyx()

        self._max_y = max_y - 2
        self._max_x = max_x

    def _check_min_screen_size(self):
        if self.max_x < SCREEN_MIN_X or \
            self.max_y < SCREEN_MIN_Y:
            raise RuntimeError('Minimum screen size must be %sx%s lines' % (SCREEN_MIN_X, SCREEN_MIN_Y))

    def _reset(self):
        # Resets the screen
        self.screen.keypad(0)
        curses.echo()
        curses.nocbreak()
        curses.endwin()

    def _clean(self):
        self.screen.erase()

    # Event handlers
    def _handle_key_event(self, key):
        if key in 'u':
            #self._update_node_metrics(update_now = True)
            pass
        elif key in 'rR':
            self.hide_repeat = not self.hide_repeat
        elif key in 'qQ':
            exit_handler()

    def _handle_movement_key(self, key):
        # Highlight the corresponding node in the list
        self.max_cursor_pos = len(self.table_lines) - 1
        if key == curses.KEY_UP:
            if self.cursor_pos > self.min_cursor_pos:
                self.cursor_pos -= 1

        elif key == curses.KEY_DOWN:
            if self.cursor_pos < self.max_cursor_pos:
                self.cursor_pos += 1

        elif key == curses.KEY_PPAGE:
            self.cursor_pos = 0

        elif key == curses.KEY_NPAGE:
            self.cursor_pos = self.max_cursor_pos

        self._update_node_metrics(update_now = True)

    def _handle_event(self, event):
        if event == curses.KEY_RESIZE:
            # Redraw the screen on resize
            self._redraw()

    # Helper methods
    def addstr(self, y, x, str, attr = 0):
        if x == 'center':
            x = self._get_center_offset(self.max_x, len(str))
        elif x == 'right':
            x = self._get_right_offset(self.max_x, len(str))

        if y == 'center':
            y = self._get_center_offset(self.max_y, len(str))
        elif y == 'right':
            y = self._get_right_offset(self.max_y, len(str))

        self.screen.addstr(y, x, str, attr)

    # Properties
    @property
    def max_y(self):
        return self._max_y
 
    @property
    def max_x(self):
        return self._max_x

    def _get_center_offset(self, max_offset, string_length):
        return ((max_offset / 2) - string_length / 2)
 
    def _get_right_offset(self, max_offset, string_length):
        return (max_offset - string_length)

def exit_handler(*args):
    screen._reset()
    conn.disconnect()
    sys.exit(0)
  
# Register exit signals
signal.signal(signal.SIGTERM, exit_handler)
signal.signal(signal.SIGINT, exit_handler)

def main():
    global conn, screen

    # Connect to message broker
    try:
        conn = stomp.Connection(BROKER_LIST)
        conn.set_listener('', MessageHandler())
        conn.start()
        conn.connect(wait=True)
        # conn.subscribe(destination=NOTIFY_TOPIC, ack='auto', headers={'selector': "repeat = 'false'"})
        conn.subscribe(destination=NOTIFY_TOPIC, ack='auto', headers={})
    except Exception, e:
        logging.error('Stomp connection error: %s', e)

    screen = Screen()

    try:
        screen.run()
    except RuntimeError, e:
        screen._reset()
        print e
        conn.disconnect()
        sys.exit(1)
    except Exception, e:
        screen._reset()
        print e
        conn.disconnect()
        sys.exit(1)

if __name__ == '__main__':
    main()
