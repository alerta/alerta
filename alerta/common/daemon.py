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
import pwd
import grp
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
    def __init__(self, prog, user=None, pidfile=None, disable_flag=None, stdin='/dev/null', stdout='/dev/null', stderr='/dev/null'):

        self.prog = prog

        self.stdin = stdin
        self.stdout = stdout
        self.stderr = stderr

        self.user = user or CONF.user_id
        try:
            pw = pwd.getpwnam(self.user)
        except KeyError:
            self.uid = None
        else:
            self.uid = pw.pw_uid

        try:
            gr = grp.getgrnam(self.user)
        except KeyError:
            self.gid = -1
        else:
            self.gid = gr.gr_gid

        self.pidfile = pidfile or '%s/%s.pid' % (CONF.pid_dir, self.prog)
        self.disable_flag = disable_flag or CONF.disable_flag

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
            LOG.critical("Fork #1 failed: %d (%s)" % (e.errno, e.strerror))
            sys.exit(1)

        # change user
        if self.uid:
            try:
                logging.set_owner(self.uid, self.gid)
                if self.gid != -1:
                    os.setgid(self.gid)
                os.setuid(self.uid)
            except OSError, e:
                LOG.error('Could not run %s as user %s: %s', self.prog, self.user, e)
                sys.exit(1)
            LOG.info('Running %s as user %s', self.prog, self.user)

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
            LOG.critical("Fork #2 failed: %d (%s)" % (e.errno, e.strerror))
            sys.exit(1)

        # redirect standard file descriptors
        sys.stdout.flush()
        sys.stderr.flush()

        si = file(self.stdin, 'r')
        so = file(self.stdout, 'a+')
        if not CONF.use_stderr:
            se = file(self.stderr, 'a+', 0)

        os.dup2(si.fileno(), sys.stdin.fileno())
        os.dup2(so.fileno(), sys.stdout.fileno())
        if not CONF.use_stderr:
            os.dup2(se.fileno(), sys.stderr.fileno())

        LOG.debug('Redirected stdout%s and stdin' % (', stderr' if not CONF.use_stderr else ''))

        # write pidfile
        atexit.register(self.delpid)
        self.pid = str(os.getpid())
        try:
            file(self.pidfile, 'w+').write("%s\n" % self.pid)
        except Exception, e:
            LOG.error('Failed to write pid to file: %s', e)
            sys.exit(1)

        LOG.debug('Wrote PID %s to %s' % (self.pid, self.pidfile))

    def wait_on_disable(self):
        try:
            while os.path.isfile(self.disable_flag):
                LOG.info('Disable flag %s exists. Sleeping 120 seconds...', self.disable_flag)
                time.sleep(120)
        except (KeyboardInterrupt, SystemExit):
            sys.exit(0)

    def delpid(self):
        os.remove(self.pidfile)
        LOG.info('Deleted pid file %s' % self.pidfile)

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
        You should override this method when you subclass Daemon. It will be called after the process has been
        daemonized by start() or restart().
        """
        LOG.error('Something went wrong. This method is meant to be re-implemented by Daemon subclass.')
        pass
