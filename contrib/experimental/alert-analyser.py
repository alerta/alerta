#!/usr/bin/env python
########################################
# 
# alert-analyser - Historical alert analyser
#
########################################

import os
import optparse
import time
import rrdtool
import re

__version__ = '1.0.0'

# Command-line options
parser = optparse.OptionParser(
                  version="%prog " + __version__,
                  description="Alert RRD Analyser Tool - run it against an RRD file to see what alerts would have been generated for given thresholds")
parser.add_option("--path",
                  dest="path",
                  default=os.getcwd(),
                  help="Fully qualified path to RRDs.")
parser.add_option("--file",
                  dest="file",
                  help="RRD metric file name (without the .rrd).")
parser.add_option("--value",
                  dest="value",
                  help="Value against which thresholds are compared. eg. $val / 100")
parser.add_option("-t",
                  "--thresholdInfo",
                  dest="thresholds",
                  help="Thresholds for each severity eg. CRITICAL:>:8;MAJOR:>:5;MINOR:>:3;NORMAL:<:3")
parser.add_option("--minutes",
                  "--mins",
                  dest="minutes",
                  default='',
                  help="Show alerts for last <x> minutes")
parser.add_option("--hours",
                  "--hrs",
                  dest="hours",
                  default='',
                  help="Show alerts for last <x> hours")
parser.add_option("--days",
                  dest="days",
                  default='1',
                  help="Show alerts for last <x> days")

options, args = parser.parse_args()

if not options.file:
    parser.print_help()
    parser.error("Must supply RRD file using --file")

if options.path:
    rrdfile = os.path.join(options.path, options.file)
else:
    rrdfile = os.path.join(os.path.cwd, options.file)

if not os.path.isfile(rrdfile):
    parser.print_help()
    parser.error("RRD file not found at %s" % rrdfile)

if not options.value:
    parser.print_help()
    parser.error("Must supply a value to be calculated using --value")

if not options.thresholds:
    parser.print_help()
    parser.error("Must supply severity thresholds using --thresholds")

start = ''
if options.minutes:
    start = '-'+options.minutes+'minutes'
if options.hours:
    start += '-'+options.hours+'hours'
if options.days:
    start += '-'+options.days+'days'

info, ds, data = rrdtool.fetch(rrdfile, 'AVERAGE', '--start', start)
ts,end,step = info

metric = dict()
previousSeverity = None

for d in data:
    if d[0] is None:
        continue

    value = re.sub(r'(\$([A-Za-z0-9-_]+))', str(d[0]), options.value)
    val_eval = eval(value)

    for ti in options.thresholds.split(';'):
        sev,op,thr = ti.split(':')
        thr_eval = '%s %s %s' % (val_eval,op,thr)
        if eval(thr_eval):
            if sev.upper() != previousSeverity:
                if sev.upper() != 'NORMAL':
                    print "%s [OPEN]   %s - %s is %s" % (
                        time.strftime('%H:%M:%S %d/%m/%y', time.localtime(ts)),
                        sev.upper(), 
                        options.value,
                        val_eval)
                else:
                    print "%s [CLOSED] %s - %s is %s" % (
                        time.strftime('%H:%M:%S %d/%m/%y', time.localtime(ts)),
                        sev.upper(),
                        options.value,
                        val_eval)
            previousSeverity = sev.upper()
            break
    ts += step

print "%s [END]    %s - %s is %s" % (
    time.strftime('%H:%M:%S %d/%m/%y', time.localtime(end)),
    previousSeverity,
    options.value,
    val_eval)

