Alerta monitoring system and console
====================================

Introduction
------------
The alerta monitoring tool was developed with the following aims in mind:

*   distributed and de-coupled
*   minimal configuarion and easily accepts alerts from any source
*   use APIs and standards where possible

Basic Concepts
--------------
1. all alerts SHOULD send a corresponding 'clear' alert (ie. NORMAL severity) when the 
   alert condition is no longer active
2. alerts MUST be uniquely identifiable by the RESOURCE and EVENT NAME fields which can
   then be used for de-duplication
3. only the most recent state of an alert is shown in the console and NORMAL severity
   alerts are periodically cleared from the system

Standard Attributes
-------------------
Most alerts have the following attributes:
* id - alert id is a random UUID
* severity - one of CRITICAL, MAJOR, MINOR, WARNING, NORMAL, INFORM or DEBUG
* createTime - UTC date & time in ISO 8601 format in Zulu timezone
* resource - uniquely identifies the resource under alarm
* environment - user-defined but possible values are PROD, RELEASE, QA, DEV, TEST, STAGE etc
* service - user-defined category for grouping resources into service-related entities
* event 
* value
* group
* text 
* summary - short, pre-formatted text for SMS, IRC, email subjects etc
* tags - array of single, double or triple tags eg. [ "aTag", "aDouble:Tag", "a:Triple=Tag" ]
* type - describes type of alert ie. snmpAlert, logAlert, exceptionAlert (CLI)
* origin - script/tool/application that generated the alert

Optional Attributes
-------------------
Some alert sources as a consequence of how the alerts are generated have access to 
additional context about an alert. For example Ganglia alerts can forward links to
host and metric graphs. 

* thresholdInfo
* moreInfo
* graphs

Dervied Attributes
------------------
The following attributes are derived by the alerta server daemon based on information
determined when the alert was received and/or located in the database.

* receiveTime
* lastReceiveTime
* lastReceiveId
* duplicateCount
* repeat - if this is the first time an alert has been sent in this state then repeat is
  set to 'false'. Some alert notify subscribers discard repeat alerts eg. IRCbot, mailer 
* previousSeverity
* history - whenever an alert changes state (ie. the severity changes) then the following
  attributes for the alert are kept in a history log:
    * severity
    * lastReceiveId
    * createTime
    * receiveTime
    * text

Server
------
*   alerta - main server daemon, listens to the queue for incoming alerts, inserts them in the mongo
    database, and then forwards alerts to the logger queue and notify topic

Inputs
------
*   alert-sender - command-line tool for sending alerts from scripts, cron jobs and other monitoring
    tools that trigger actions based on errors

*   alert-checker - a wrapper script for Nagios checks that will run any check and map the Nagios plugin
    result to the format expected by alerta

*   alert-snmptrap - parses SNMP traps and forwards them as alerts

*   alert-ganglia - parses the Ganglia gmetad XML and compares current metric values against a set of
    user-defined rules for alert generation

*   alert-aws - forward EC2 instance status changes to alerta

Outputs
-------
*   alert-logger - logs all alerts to elasticsearch for long-term archiving and powerful search

*   alert-mailer - sends emails to user-defined recipients including when the issue has cleared

*   alert-ircbot - posts a message on the #alerta IRC channel whenever an alert is received

Other
-----
*    alert-twitter - listens to a twitter stream for related tweets about website availability and logs
     them to the elasticsearch search engine

Thanks
======

* 10gen for mongodb
* Apache for ActiveMQ and STOMP
* Shay Banon for elasticsearch
