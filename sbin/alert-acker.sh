#!/bin/sh

if [ "$1" = "" ]; then
    echo "Must supply alert ID to acknowledge"
else
    ALERTID=$1
fi

curl -XPUT http://${2:-'monitoring.gudev.gnl'}/alerta/api/v1/alerts/alert/${ALERTID} -d '{ "status": "ACK" }'
echo
