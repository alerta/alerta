#!/bin/sh

snmptrap -v2c -c ${2:-'public'} ${1:-'monitoring.gudev.gnl'} "" .1.3.6.1.6.3.1.1.5.1.0 0 s "This is a test coldStart trap"
snmptrap -v2c -c ${2:-'public'} ${1:-'monitoring.gudev.gnl'} "" .1.3.6.1.6.3.1.1.5.2.0 0 s "This is a test warmStart trap"
snmptrap -v2c -c ${2:-'public'} ${1:-'monitoring.gudev.gnl'} "" .1.3.6.1.6.3.1.1.5.3.0 0 s "This is a test linkDown trap"
snmptrap -v2c -c ${2:-'public'} ${1:-'monitoring.gudev.gnl'} "" .1.3.6.1.6.3.1.1.5.4.0 0 s "This is a test linkUp trap"
snmptrap -v2c -c ${2:-'public'} ${1:-'monitoring.gudev.gnl'} "" .1.3.6.1.6.3.1.1.5.5.0 0 s "This is a test authenticationFailure trap"

