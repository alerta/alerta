
import os
import build

VERSION = (3, 0, 3, 'final', 1)


def get_version():
    version = '%s.%s' % (VERSION[0], VERSION[1])
    if VERSION[2]:
        version = '%s.%s' % (version, VERSION[2])
    if VERSION[3] != 'final':
        version = '%s %s %s' % (version, VERSION[3], VERSION[4])
    if build.BUILD_NUMBER != 'DEV':
        version = '%s-build.%s' % (version, build.BUILD_NUMBER)
    return version

__version__ = get_version()
