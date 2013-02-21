#!/usr/bin/env python

import ConfigParser
import argparse

parser = SafeConfigParser()
parser.read('./simple.ini')

def parse_args(argv, prog=None, version='unknown'):

    # 1. use ConfigParser to load section and DEFAULT values
    # 2. use argparse to read in command-line options





# print 'bug url = %s' % CONF.
    print 'bug logpath = %s' % parser.get('bug_tracker', 'logpath')
    print 'wiki logpath = %s' % parser.get('wiki', 'logpath')