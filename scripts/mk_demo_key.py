#!/usr/bin/env python

import datetime

from alerta.app.database import Mongo

data = {
    "user": "test user",
    "key": "demo-key",
    "text": "demo key",
    "expireTime": datetime.datetime.utcnow() + datetime.timedelta(365),
    "count": 0,
    "lastUsedTime": None
}

Mongo()._db.keys.insert(data)

