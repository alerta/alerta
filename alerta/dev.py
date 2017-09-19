
import platform

from datetime import datetime

BUILD_NUMBER = 'DEV'
BUILD_DATE = datetime.today().strftime('%Y-%m-%d')
BUILD_VCS_NUMBER = 'HEAD'
BUILT_BY = 'unknown'
HOSTNAME = platform.node()
