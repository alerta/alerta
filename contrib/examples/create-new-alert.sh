#!/bin/bash

curl -XPOST -H "Content-type: application/json" 'http://localhost:8080/alerta/api/v2/alerts/alert.json' -d '
{
  "resource": "host678:eth0",
  "event": "HW:NIC:FAILED",
  "group": "Hardware",
  "severity": "major",
  "environment": [
      "PROD",
      "INFRA"
  ],
  "service": [
      "Common"
  ],
  "text": "Network interface eth0 is down.",
  "value": "error"
}'
echo
sleep 1

curl -XPOST -H "Content-type: application/json" 'http://localhost:8080/alerta/api/v2/alerts/alert.json' -d '{
    "resource": "fw010",
    "event": "NodeDown",
    "group": "Firewall",
    "value": "Down",
    "severity": "major",
    "environment": [
        "DEV",
        "INFRA"
    ],
    "service": [
        "Network"
    ],
    "tags": [
        "location=London",
         "region=EU"
    ],
    "text": "Firewall is not responding to ping."
}'
echo
sleep 2

curl -XPOST -H "Content-type: application/json" 'http://localhost:8080/alerta/api/v2/alerts/alert.json' -d '{
    "resource": "router0011",
    "event": "node_up",
    "group": "Network",
    "value": "UP",
    "severity": "normal",
    "environment": [
        "INFRA"
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
echo
sleep 3

curl -XPOST -H "Content-type: application/json" 'http://localhost:8080/alerta/api/v2/alerts/alert.json' -d '{
    "resource": "mydb",
    "event": "OraError",
    "group": "Database",
    "value": "ERROR 011",
    "severity": "warning",
    "environment": [
        "DEV",
        "PROD"
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
echo
sleep 1

curl -XPOST -H "Content-type: application/json" 'http://localhost:8080/alerta/api/v2/alerts/alert.json' -d '{
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
echo
sleep 1

curl -XPOST -H "Content-type: application/json" 'http://localhost:8080/alerta/api/v2/alerts/alert.json' -d '{
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
