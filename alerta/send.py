import sys
import argparse
import logging

# import alerta

__version__ = '1.3.0'

DEFAULT_TIMEOUT = 3600

LOG = logging.getLogger(__name__)


def main():
    """
    Sender...

    """
    try:
        parser = argparse.ArgumentParser(
            prog='alert-sender',
            description='Alert Command-Line Tool - sends an alert to the alerting system. Alerts must have' +
                        ' a resource (including service and environment), event name, value and text. A ' +
                        'severity of "Normal" is used if none given. Tags and group are optional.',
            epilog='alert-sender.py --resource myCoolApp --event AppStatus --group Application --value Down ' +
                   '--severity critical --env PROD --svc MicroApp --tag release:134 --tag build:1005 ' +
                   '--text "Micro App X is down."'
        )
        parser.add_argument(
            '--version',
            action='version',
            version=__version__
        )
        parser.add_argument(
            '--debug',
            default=False,
            action='store_true',
            help="Print debugging output"
        )
        parser.add_argument(
            '-r', '--resource',
            help='Resource under alarm eg. hostname, network device, application, web address.'
        )
        parser.add_argument(
            '-e',
            '--event',
            help='Event name eg. NodeDown, QUEUE:LENGTH:EXCEEDED, coldStart, LOG_ERROR'
        )
        parser.add_argument(
            '-c',
            '--correlate',
            help='Comma-separated list of events to correlate together eg. NodeUp,NodeDown'
        )
        parser.add_argument(
            '-g',
            '--group',
            help='Event group eg. Application, Backup, Database, HA, Hardware, Job, Network, OS, Performance, Security'
        )
        parser.add_argument(
            '-v',
            '--value',
            help='Event value eg. 100%%, Down, PingFail, 55tps, ORA-1664'
        )
        parser.add_argument(
            '-s',
            '--severity',
            default='Normal',
            help='Severity eg. Critical, Major, Minor, Warning, Normal, Inform (default: %(default)s)'
        )
        parser.add_argument(
            '-E',
            '--environment',
            metavar='ENV',
            action='append',
            help='Environment eg. PROD, REL, QA, TEST, CODE, STAGE, DEV, LWP, INFRA'
        )
        parser.add_argument(
            '-S',
            '--svc',
            '--service',
            action='append',
            help='Service eg. R1, R2, Discussion, Soulmates, ContentAPI, MicroApp, FlexibleContent, SharedSvcs'
        )
        parser.add_argument(
            '-T',
            '--tag',
            action='append',
            default=list(),
            help='Tag the event with anything and everything.'
        )
        parser.add_argument(
            '-t',
            '--text',
            help='Freeform alert text eg. Host not responding to ping.'
        )
        parser.add_argument(
            '-o',
            '--timeout',
            type=int,
            default=DEFAULT_TIMEOUT,
            help='Timeout in seconds that OPEN alert will persist in webapp.'
        )
        parser.add_argument(
            '-H',
            '--heartbeat',
            action='store_true',
            default=False,
            help='Send heartbeat to server.'
        )
        parser.add_argument(
            '-O',
            '--origin',
            help='Origin of heartbeat. Usually an application instance.'
        )
        parser.add_argument(
            '-q',
            '--quiet',
            action='store_true',
            default=False,
            help='Do not display assigned alert id.'
        )
        parser.add_argument(
            '-d',
            '--dry-run',
            action='store_true',
            default=False,
            help='Do not send alert.'
        )

        if len(sys.argv) == 1:
            parser.print_usage()
            sys.exit(1)

        args = parser.parse_args()


    except Exception, e:
        # logger.debug(e, sys.exc_info=1)
        print >> sys.stderr, "ERROR: %s" % unicode(e)
        print e
        sys.exit(1)

if __name__ == '__main__':
    main()