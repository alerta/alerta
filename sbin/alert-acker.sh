#!/usr/bin/env sh

if [ "$1" = "" ]; then
    echo "Must supply alert ID to acknowledge"
    exit 1
else
    ALERTID=$1
fi

curl -XPUT http://${2:-'monitoring.guprod.gnl'}/alerta/api/v1/alerts/alert/${ALERTID} -d '{ "status": "ACK" }'
echo
