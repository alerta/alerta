#!/bin/sh

ENDPOINT=${1:-http://localhost:8080}

curl -s -XPOST -H "Content-type: application/json" -H "Authorization: Key demo-key" ${ENDPOINT}/alert -d '
{
  "resource": "host678:eth0",
  "event": "HW:NIC:FAILED",
  "group": "Hardware",
  "severity": "major",
  "environment": "Production",
  "service": [
      "Network"
  ],
  "text": "Network interface eth0 is down.",
  "value": "error"
}'
echo

curl -s -XPOST -H "Content-type: application/json" -H "Authorization: Key demo-key" ${ENDPOINT}/alert -d '
{
    "resource": "fw010",
    "event": "NodeDown",
    "group": "Firewall",
    "value": "Down",
    "severity": "major",
    "environment": "Development",
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

curl -s -XPOST -H "Content-type: application/json" -H "Authorization: Key demo-key" ${ENDPOINT}/alert -d '
{
    "resource": "router0011",
    "event": "node_up",
    "group": "Network",
    "value": "UP",
    "severity": "normal",
    "environment": "Production",
    "service": [
        "Shared"
    ],
    "tags": [
        "location=London",
         "region=EU"
    ],
    "text": "Router is up."
}'
echo

curl -s -XPOST -H "Content-type: application/json" -H "Authorization: Key demo-key" ${ENDPOINT}/alert -d '
{
    "resource": "mydb",
    "event": "OraError",
    "group": "Oracle",
    "value": "ERROR 011",
    "severity": "warning",
    "environment": "Development",
    "service": [
        "Database"
    ],
    "tags": [
        "location=London",
         "region=EU"
    ],
    "text": "Oracle 011 error."
}'
echo

curl -s -XPOST -H "Content-type: application/json" -H "Authorization: Key demo-key" ${ENDPOINT}/alert -d '
{
    "resource": "myapp",
    "event": "SlowResponse",
    "group": "Application",
    "value": "5005ms",
    "severity": "critical",
    "environment": "Development",
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

curl -s -XPOST -H "Content-type: application/json" -H "Authorization: Key demo-key" ${ENDPOINT}/alert -d '
{
    "resource": "host44",
    "event": "SwapUtil",
    "group": "OS",
    "value": "94%",
    "severity": "minor",
    "environment": "Production",
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
