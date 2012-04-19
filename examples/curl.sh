#!/bin/sh

curl -XPOST http://${1:-'monitoring.gudev.gnl'}/alerta/api/v1/alerts/alert.json -d '{
    "resource": "host5",
    "event": "HostAvail",
    "group": "Network",
    "value": "Down",
    "severity": "Critical",
    "environment": "REL",
    "service": "SharedSvcs",
    "tags": [
        "location=London",
        "region=EU"
    ],
    "text": "Host is not responding to ping"
}'
echo
