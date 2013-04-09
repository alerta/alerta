# Metrics checker

## Setup

Assuming you've created your virtualenv, loaded it with the requirements and installed alerta as per the top level directions...

Copy the alerta-ganglia.yaml file to `/tmp` or somewhere convenient.
	
	coilmq -b 0.0.0.0 -p 61613
	alert-ganglia --log-dir=/tmp --pid-dir=/tmp --yaml-config=/tmp/alert-ganglia.yaml --foreground

The daemon should now fail as the config file is wrong for local development.