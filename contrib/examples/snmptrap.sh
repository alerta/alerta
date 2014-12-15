#!/bin/sh

if [ "$1" == "-h" ]
then
  echo "Usage: snmptrap.sh [TRAP_DEST] [COMMUNITY]"
  exit 1
fi

TRAP_DEST=${1:-localhost}
COMMUNITY=${2:-public}

snmptrap -v2c -c ${COMMUNITY} ${TRAP_DEST} "" .1.3.6.1.6.3.1.1.5.1.0 0 s "This is a test coldStart trap"
snmptrap -v2c -c ${COMMUNITY} ${TRAP_DEST} "" .1.3.6.1.6.3.1.1.5.2.0 0 s "This is a test warmStart trap"
snmptrap -v2c -c ${COMMUNITY} ${TRAP_DEST} "" .1.3.6.1.6.3.1.1.5.3.0 0 s "This is a test linkDown trap"
snmptrap -v2c -c ${COMMUNITY} ${TRAP_DEST} "" .1.3.6.1.6.3.1.1.5.4.0 0 s "This is a test linkUp trap"
snmptrap -v2c -c ${COMMUNITY} ${TRAP_DEST} "" .1.3.6.1.6.3.1.1.5.5.0 0 s "This is a test authenticationFailure trap"

