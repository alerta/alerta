#!/bin/sh

ENDPOINT=${1:-http://localhost:8080}
KEY=${2:-demo-key}

curl -H "Authorization: Key ${KEY}" "${ENDPOINT}/webhooks/pingdom?message=%7B%22check%22%3A%20%22803318%22%2C%20%22checkname%22%3A%20%22Alerta%20API%22%2C%20%22host%22%3A%20%22api.alerta.io%22%2C%20%22action%22%3A%20%22notify_of_close%22%2C%20%22incidentid%22%3A%201262%2C%20%22description%22%3A%20%22up%22%7D"
