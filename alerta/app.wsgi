#!/usr/bin/env python

try:
    from alerta import app  # alerta >= 5.0
except Exception:
    from alerta.app import app  # alerta < 5.0
