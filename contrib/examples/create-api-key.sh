#!/bin/sh

ENDPOINT=${1:-http://localhost:8080}
KEY=${2:-demo-key}

curl -XPOST -H "Authorization: Key ${KEY}" "${ENDPOINT}/key" -d '{"user":"test"}' -H "Content-type: application/json"
