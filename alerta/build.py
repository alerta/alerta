
import os
import datetime

BUILD_NUMBER = os.environ.get('BUILD_NUMBER', 'DEV')
BUILD_DATE = datetime.datetime.utcnow()
BUILD_VCS_NUMBER = os.environ.get('BUILD_VCS_NUMBER', '')
BUILT_BY = os.environ.get('USER', '')
HOSTNAME = os.environ.get('HOSTNAME', '')
