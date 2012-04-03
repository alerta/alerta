#!/bin/sh

curl -H "Content-Type: application/json" -XPOST -d '{ "group": "Misc", "severity": "MAJOR", "service": "SharedSvcs", "text": "host down", "value": "Down", "event": "HostAvail", "environment": "PROD", "resource": "server1" }' http://monitoring.gudev.gnl/alerta/api/v1/alerts/alert.json | python -mjson.tool

