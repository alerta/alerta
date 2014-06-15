"""
Adapted from code originally developed by Nick Galbreath
See https://github.com/ganglia/ganglia_contrib/tree/master/gmetric-python
"""

# This is the MIT License
# http://www.opensource.org/licenses/mit-license.php
#
# Copyright (c) 2007,2008 Nick Galbreath
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
#

from xdrlib import Packer, Unpacker
import socket

from alerta.common import log as logging
from alerta.common import config

LOG = logging.getLogger(__name__)
CONF = config.CONF

METRIC_SLOPES = {
    'zero': 0,
    'positive': 1,
    'negative': 2,
    'both': 3,
    'unspecified': 4
}

METRIC_TYPES = {
    'int8': 131,
    'uint8': 131,
    'int16': 131,
    'uint16': 131,
    'int32': 131,
    'uint32': 132,
    'string': 133,
    'float': 134,
    'double': 135
}

PROTOCOLS = [
    'udp',
    'multicast'
]

prog = os.path.basename(sys.argv[0])


class Gmetric:
    """
    Class to send gmetric/gmond 2.X packets
    """

    ganglia_opts ={
        'gmetric_host': 'localhost',
        'gmetric_port': 8649,
        'gmetric_protocol': 'udp',
        'gmetric_spoof': '10.1.1.1:%s' % prog,
    }

    def __init__(self, host=None, port=None, protocol=None):

        config.register_opts(Gmetric.ganglia_opts)

        self.host = host or CONF.gmetric_host
        self.port = port or CONF.gmetric_port
        self.protocol = protocol or CONF.gmetric_protocol

        if self.protocol not in PROTOCOLS:
            LOG.error("Protocol must be one of: %s", ','.join(PROTOCOLS))
            return

        LOG.debug('Gmetric setup to send %s packets to %s:%s', self.protocol, self.host, self.port)

        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        if self.protocol == 'multicast':
            self.socket.setsockopt(socket.IPPROTO_IP,
                                   socket.IP_MULTICAST_TTL, 20)
        self.hostport = (self.host, int(self.port))

    def metric_send(self, name, value, metric_type, units="", slope='both', tmax=60, dmax=0, group=None, title=None,
                    description=None, spoof=None):

        if name is None or value is None or metric_type is None or slope not in METRIC_SLOPES:
            LOG.error('Invalid gmetric parameters invalid. Must supply name, value, type and slope.')
            return

        if '"' in name or '"' in value or '"' in metric_type or '"' in units:
            LOG.error('One of the gmetric parameters has an invalid character \'"\'.')
            return

        if metric_type not in METRIC_TYPES.keys():
            LOG.error('The supplied type parameter "%s" is not a valid type.', metric_type)
            return

        if metric_type != 'string':
            try:
                int(value)
            except ValueError:
                pass
            try:
                float(value)
            except ValueError:
                LOG.error('The value parameter "%s" does not represent a number.', value)
                return

        LOG.debug('gmetric name=%s, value=%s, type=%s, units=%s, slope=%s, tmax=%s, dmax=%s, group=%s title=%s, description=%s, spoof=%s',
                  name, value, metric_type, units, slope, tmax, dmax, group, title, description, spoof)

        (meta_msg, data_msg) = self._gmetric(name, value, metric_type, units, slope, tmax, dmax, group, title,
                                             description, spoof)

        count = self.socket.sendto(meta_msg, self.hostport)
        LOG.debug('Sent %s metadata packets', count)
        count = self.socket.sendto(data_msg, self.hostport)
        LOG.debug('Sent %s data packets', count)

    def _gmetric(self, name, val, metric_type, units, slope, tmax, dmax, group, title, description, spoof):

        meta = Packer()
        HOSTNAME = socket.gethostname()
        if spoof:
            SPOOF_ENABLED = 1
        else:
            SPOOF_ENABLED = 0

        # Meta data about a metric
        packet_type = 128
        meta.pack_int(packet_type)
        if SPOOF_ENABLED == 1:
            meta.pack_string(spoof)
        else:
            meta.pack_string(HOSTNAME)
        meta.pack_string(name)
        meta.pack_int(SPOOF_ENABLED)
        meta.pack_string(metric_type)
        meta.pack_string(name)
        meta.pack_string(units)
        meta.pack_int(METRIC_SLOPES[slope])  # map slope string to int
        meta.pack_uint(int(tmax))
        meta.pack_uint(int(dmax))

        extra_data = 0
        if group:
            extra_data += 1
        if title:
            extra_data += 1
        if description:
            extra_data += 1

        meta.pack_int(extra_data)
        if group:
            for g in group.split(','):
                meta.pack_string("GROUP")
                meta.pack_string(g)
        if title:
            meta.pack_string("TITLE")
            meta.pack_string(title)
        if description:
            meta.pack_string("DESC")
            meta.pack_string(description)

        # Actual data sent in a separate packet
        data = Packer()
        packet_type = METRIC_TYPES[metric_type]
        data.pack_int(packet_type)
        if SPOOF_ENABLED == 1:
            data.pack_string(spoof)
        else:
            data.pack_string(HOSTNAME)
        data.pack_string(name)
        data.pack_int(SPOOF_ENABLED)

        if metric_type in ['int8', 'uint8', 'int16', 'uint16', 'int32']:
            data.pack_string("%d")
            data.pack_int(int(val))
        if metric_type == 'uint32':
            data.pack_string("%u")
            data.pack_uint(long(val))
        if metric_type == 'string':
            data.pack_string("%s")
            data.pack_string(str(val))
        if metric_type == 'float':
            data.pack_string("%f")
            data.pack_float(float(val))
        if metric_type == 'double':
            data.pack_string("%f")
            data.pack_double(float(val))  # XXX - double or float?

        return meta.get_buffer(), data.get_buffer()
