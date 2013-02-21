#!/usr/bin/env python

"""
See http://www.jejik.com/articles/2007/02/a_simple_unix_linux_daemon_in_python/

Example:

import sys, time
from daemon import Daemon

class MyDaemon(Daemon):
        def run(self):
                while True:
                        time.sleep(1)

if __name__ == "__main__":
        daemon = MyDaemon('/tmp/daemon-example.pid')
        if len(sys.argv) == 2:
                if 'start' == sys.argv[1]:
                        daemon.start()
                elif 'stop' == sys.argv[1]:
                        daemon.stop()
                elif 'restart' == sys.argv[1]:
                        daemon.restart()
                else:
                        print "Unknown command"
                        sys.exit(2)
                sys.exit(0)
        else:
                print "usage: %s start|stop|restart" % sys.argv[0]
                sys.exit(2)

"""

import os
import sys
import time
import atexit

from alerta.common import log as logging
from alerta.common import config

from signal import SIGTERM

_DEFAULT_WAIT_ON_DISABLE = 120  # number of seconds to idle before checking disable flag again

LOG = logging.getLogger(__name__)
CONF = config.CONF


class Daemon:
    """
    A generic daemon class.

    Usage: subclass the Daemon class and override the run() method
    """
    def __init__(self, prog, pidfile=None, disable_flag=None, stdin='/dev/null', stdout='/dev/null', stderr='/dev/null'):

        logging.setup(__name__)

        self.prog = prog

        self.stdin = stdin
        self.stdout = stdout
        self.stderr = stderr

        self.pidfile = pidfile or '/var/run/alerta/%s.pid' % self.prog
        self.disable_flag = disable_flag or '/var/run/alerta/%s.disable' % self.prog

        self.running = False
        self.shuttingdown = False

    def daemonize(self):
        """
        do the UNIX double-fork magic, see Stevens' "Advanced
        Programming in the UNIX Environment" for details (ISBN 0201563177)
        http://www.erlenstar.demon.co.uk/unix/faq_2.html#SEC16
        """
        try:
            pid = os.fork()
            if pid > 0:
                # exit first parent
                sys.exit(0)
        except OSError, e:
            LOG.critical("fork #1 failed: %d (%s)" % (e.errno, e.strerror))
            sys.exit(1)

        LOG.debug('Success fork #1...')

        # decouple from parent environment
        os.chdir("/")
        os.setsid()
        os.umask(0)

        # do second fork
        try:
            pid = os.fork()
            if pid > 0:
                # exit from second parent
                sys.exit(0)
        except OSError, e:
            LOG.critical("fork #2 failed: %d (%s)" % (e.errno, e.strerror))
            sys.exit(1)

        LOG.debug("Success fork #2...")

        # redirect standard file descriptors
        sys.stdout.flush()
        sys.stderr.flush()
        si = file(self.stdin, 'r')
        so = file(self.stdout, 'a+')
        se = file(self.stderr, 'a+', 0)
        os.dup2(si.fileno(), sys.stdin.fileno())
        os.dup2(so.fileno(), sys.stdout.fileno())
        os.dup2(se.fileno(), sys.stderr.fileno())

        LOG.debug('Redirected stdout, stderr, stdin')

        # write pidfile
        atexit.register(self.delpid)
        self.pid = str(os.getpid())
        file(self.pidfile, 'w+').write("%s\n" % self.pid)

        LOG.debug('Wrote PID %s to %s' % (self.pid, self.pidfile))

    def wait_on_disable(self):
        #TODO(nsattel): daemon should wait in a loop if disable flag exists
        pass

    def delpid(self):
        os.remove(self.pidfile)
        LOG.debug('Deleted pid file %s' % self.pidfile)

    def start(self):
        """
        Start the daemon
        """
        # Check for a pidfile to see if the daemon already runs
        if os.path.isfile(self.pidfile):
            self.pid = open(self.pidfile).read().strip()
            try:
                os.kill(int(self.pid), 0)
                LOG.critical('Process with pid %s already exists, exiting' % self.pid)
                sys.exit(1)
            except OSError:
                pass

        # Start the daemon
        LOG.info('Starting %s...' % self.prog)
        if not CONF.foreground:
            self.daemonize()
        self.wait_on_disable()
        self.run()

    def stop(self):
        """
        Stop the daemon
        """
        self.shuttingdown = True

        # Get the pid from the pidfile
        try:
            pf = file(self.pidfile, 'r')
            self.pid = int(pf.read().strip())
            pf.close()
        except IOError:
            self.pid = None

        if not self.pid:
            LOG.error("pidfile %s does not exist. Daemon not running?")
            return  # not an error in a restart

        # Try killing the daemon process
        try:
            while 1:
                os.kill(self.pid, SIGTERM)
                time.sleep(0.1)
        except OSError, err:
            err = str(err)
            if err.find("No such process") > 0:
                if os.path.exists(self.pidfile):
                    os.remove(self.pidfile)
            else:
                print str(err)
                sys.exit(1)

    def restart(self):
        """
        Restart the daemon
        """
        self.stop()
        self.start()

    def getpid(self):
        return self.pid

    def run(self):
        """
Y       ou should override this method when you subclass Daemon. It will be called after the process has been
        daemonized by start() or restart().
        """
        pass