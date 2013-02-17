#!/bin/bash

# Script to delete all ACK'ed alerts

/opt/alerta/sbin/alert-query.py --status ACK --no-header --no-footer | awk -F"|" ' { print $1 } ' | while read id
do
    curl -XDELETE http://${1:-'monitoring.gudev.gnl'}/alerta/api/v1/alerts/alert/$id
done
