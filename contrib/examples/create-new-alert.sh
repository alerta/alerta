#!/bin/bash

curl -XPOST -H "Content-type: application/json" 'http://localhost:5000/alerta/api/v2/alerts/alert.json' -d '
{
  "resource": "host678:eth0",
  "event": "HW:NIC:FAILED",
  "group": "Hardware",
  "severity": "major",
  "environment": ["RELEASE", "QA"],
  "service": ["Common"],
  "text": "Network interface eth0 is down.",
  "value": "error"
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

curl -XPOST -H "Content-type: application/json" 'http://localhost:5000/alerta/api/v2/alerts/alert.json' -d '{
    "resource": "router0011",
    "event": "node_up",
    "group": "Network",
    "value": "UP",
    "severity": "normal",
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
    "text": "Router is up."
}'

curl -XPOST -H "Content-type: application/json" 'http://localhost:5000/alerta/api/v2/alerts/alert.json' -d '{
    "resource": "mydb",
    "event": "OraError",
    "group": "Database",
    "value": "ERROR 011",
    "severity": "warning",
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
    "text": "Oracle 011 error."
}'

curl -XPOST -H "Content-type: application/json" 'http://localhost:5000/alerta/api/v2/alerts/alert.json' -d '{
    "resource": "myapp",
    "event": "SlowResponse",
    "group": "Application",
    "value": "5005ms",
    "severity": "critical",
    "environment": [
        "PROD"
    ],
    "service": [
        "Web"
    ],
    "tags": [
        "location=London",
         "region=EU"
    ],
    "text": "Service unavailable."
}'

curl -XPOST -H "Content-type: application/json" 'http://localhost:5000/alerta/api/v2/alerts/alert.json' -d '{
    "resource": "host44",
    "event": "SwapUtil",
    "group": "OS",
    "value": "94%",
    "severity": "minor",
    "environment": [
        "PROD"
    ],
    "service": [
        "Platform"
    ],
    "tags": [
        "location=London",
         "region=EU"
    ],
    "text": "Swap utilisation is high."
}'
echo
