Alerta monitoring system and console
====================================

The alerta monitoring tool was developed with the following aims in mind:

*   distributed and de-coupled so that it is **SCALABLE**
*   minimal **CONFIGURATION** that easily accepts alerts from any source
*   quick at-a-glance **VISUALISATION** with drill-down to detail

![console](/guardian/alerta/raw/master/images/alerta-console-small.png)

More screenshots are available [here](/guardian/alerta/tree/master/images/)

Installation
------------

The backend components are written in Python and the web frontend in JavaScript so there is nothing to compile.

An RPM is available for Linux [here](/guardian/alerta/tree/master/rpm/). **TBC**

Requirements
------------

- [Apache ActiveMQ][1]
- [MongoDB][2]
- [elasticsearch][3]
- [Kibana][4]

> Note: None of these packages require special configuration to work with Alerta.

Contribute
----------

If you'd like to hack on Alerta, start by forking this repo on GitHub.

http://github.com/guardian/alerta

License
-------

    Alerta monitoring system and console
    Copyright 2012 Guardian News & Media

    Licensed under the Apache License, Version 2.0 (the "License");
    you may not use this file except in compliance with the License.
    You may obtain a copy of the License at

        http://www.apache.org/licenses/LICENSE-2.0

    Unless required by applicable law or agreed to in writing, software
    distributed under the License is distributed on an "AS IS" BASIS,
    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
    See the License for the specific language governing permissions and
    limitations under the License.

[1]: <http://activemq.apache.org/> "Apache ActiveMQ"
[2]: <http://www.10gen.com/> "10gen MongoDB"
[3]: <http://www.elasticsearch.org/> "elasticsearch"
[4]: <https://github.com/rashidkpc/Kibana> "Kibana"
