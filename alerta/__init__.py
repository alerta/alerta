import sys

if sys.version_info < (3,):
    raise ImportError(
        """You are running Alerta 6.0 on Python 2

Alerta 6.0 and above are no longer compatible with Python 2.

Make sure you have pip >= 9.0 to avoid this kind  of issue,
as well as setuptools >= 24.2:

 $ pip install pip setuptools --upgrade

Your choices:

- Upgrade to Python 3.

- Install an older version of Alerta:

 $ pip install 'alerta<6.0'

See the following URL for more up-to-date information:

https://github.com/alerta/alerta/wiki/Python-3

""")

from .app import create_app  # noqa isort:skip
