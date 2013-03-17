#!/bin/bash

curl -XPOST -H "Content-type: application/json" 'http://localhost:5000/alerta/api/v2/alerts/alert.json' -d '
{
  "resource": "host678",
  "event": "event111",
  "severity": "major",
  "environment": ["RELEASE", "QA"],
  "service": ["Common"],
  "text": "this is a test",
  "value": "OK"
}'

curl -XPOST -H "Content-type: application/json" 'http://localhost:5000/alerta/api/v2/alerts/alert.json' -d '{
    "resource": "host789",
    "event": "HostAvail",
    "group": "Network",
    "value": "Down",
    "severity": "major",
    "environment": [
        "RELEASE",
        "QA"
    ],
    "service": [
        "Common"
    ],
    "tags": [
        "location=London",
         "region=EU"
    ],
    "text": "Host is not responding to ping."
}'
echo
