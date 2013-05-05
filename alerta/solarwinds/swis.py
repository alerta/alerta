
import os
import sys
import urllib2

from suds.client import Client

from alerta.common import config
from alerta.common import log as logging

LOG = logging.getLogger(__name__)
CONF = config.CONF

SOLAR_WINDS_STATUS_LEVELS = {
    '0': 'Unknown',
    '1': 'Up',
    '2': 'Down',
    '3': 'Warning',
    '4': 'Shutdown',
    '5': 'Testing',
    '6': 'Dormant',
    '7': 'Not Present',
    '8': 'Lower Layer Down',
    '9': 'Unmanaged',
    '10': 'Unplugged',
    '11': 'External',
    '12': 'Unreachable',
    '14': 'Critical',
    '15': 'Mixed Availability',
    '16': 'Misconfigured',
    '17': 'Could Not Poll',
    '19': 'Unconfirmed',
    '22': 'Active',
    '24': 'Inactive',
    '25': 'Expired',
    '26': 'Monitoring Disabled',
    '27': 'Disabled',
    '28': 'Not Licensed'
}

SOLAR_WINDS_SEVERITY_LEVELS = {
    # SolarWinds icon severity
    'Add': 'informational',
    'Critical': 'critical',
    'Disabled': 'warning',
    'External': 'informational',
    'Green': 'normal',
    'Red': 'critical',
    'RedAlert': 'major',
    'RedYield': 'minor',
    'Shutdown': 'warning',
    'Start': 'informational',
    'Testing': 'debug',
    'Undefined': 'informational',
    'Unknown': 'informational',
    'Unmanage': 'informational',
    'Unmanged': 'informational',
    'Unplugged': 'warning',
    'Unreachable': 'minor',
    'Warn': 'warning',

    # Cisco UCS fault severity
    'critical': 'critical',
    'major': 'major',
    'minor': 'minor',
    'warning': 'warning',
    'info': 'informational',
    'cleared': 'normal'
}


class SwisClient(object):

    def __init__(self, username=None, password=None):

        self.wsdl = 'https://%s:17778/SolarWinds/InformationService/v3?wsdl' % CONF.solarwinds_host
        LOG.debug('wsdl = %s', self.wsdl)

        self.client = Client(self.wsdl, username=username, password=password)
        self.client.set_options(port='BasicHttpBinding_InformationService')
        LOG.debug('client = %s', self.client)

        prog = os.path.basename(sys.argv[0])
        self.cursor_file = '%s/%s.cursor' % (CONF.pid_dir, prog)

        if os.path.isfile(self.cursor_file):
            npm_id, ucs_id = open(self.cursor_file).read().splitlines()
            LOG.info('Event IDs cursor read from file: %s, %s', npm_id, ucs_id)
        else:
            npm_id = self._get_max_npm_event_id()
            ucs_id = self._get_max_ucs_event_id()
            LOG.info('Event ID cursor queried from db: %s, %s', npm_id, ucs_id)

        self.npm_event_id_cursor = npm_id
        self.ucs_event_id_cursor = ucs_id

    def shutdown(self):

        try:
            f = open(self.cursor_file, 'w')
            f.write('%s\n%s\n' % (self.npm_event_id_cursor, self.ucs_event_id_cursor))
            f.close()
        except IOError, e:
            LOG.error('Failed to write event ID cursor to file %s: %s', self.cursor_file, e)

    def get_npm_events(self):

        last_event_id = self._get_max_npm_event_id()

        if not last_event_id or last_event_id == self.npm_event_id_cursor:
            LOG.debug('No new events since event id %s. Skipping NPM event query...', last_event_id)
            return []

        LOG.debug('Get network events in range %s -> %s', self.npm_event_id_cursor, last_event_id)

        query = (
            "SELECT EventID, EventTime, N.NodeName, N.ObjectSubType AS Object, ET.Name, Message, ET.Name, ET.Icon " +
            "FROM Orion.Events E " +
            "INNER JOIN Orion.EventTypes AS ET ON E.EventType = ET.EventType " +
            "INNER JOIN Orion.Nodes AS N ON E.NetworkNode = N.NodeID " +
            "WHERE EventID > %s AND EventID <= %s " % (self.npm_event_id_cursor, last_event_id) +
            "AND NetObjectType = 'N' " +
            "UNION ALL "
        )

        query += (
            "(SELECT EventID, EventTime, N.NodeName, I.IfName AS Object, ET.Name, Message, ET.Name, ET.Icon " +
            "FROM Orion.Events E " +
            "INNER JOIN Orion.EventTypes AS ET ON E.EventType = ET.EventType " +
            "INNER JOIN Orion.Nodes AS N ON E.NetworkNode = N.NodeID " +
            "INNER JOIN Orion.NPM.Interfaces AS I ON E.NetObjectID = I.InterfaceID " +
            "WHERE EventID > %s AND EventID <= %s " % (self.npm_event_id_cursor, last_event_id) +
            "AND NetObjectType = 'I') " +
            "UNION ALL "
        )

        query += (
            "(SELECT EventID, EventTime, N.NodeName, V.DisplayName AS Object, ET.Name, Message, ET.Name, ET.Icon " +
            "FROM Orion.Events E " +
            "INNER JOIN Orion.EventTypes AS ET ON E.EventType = ET.EventType " +
            "INNER JOIN Orion.Nodes AS N ON E.NetworkNode = N.NodeID " +
            "INNER JOIN Orion.Volumes AS V ON E.NetObjectID = V.VolumeID " +
            "WHERE EventID > %s AND EventID <= %s " % (self.npm_event_id_cursor, last_event_id) +
            "AND NetObjectType = 'V') "
        )
        query += (
            "ORDER BY 1"
        )

        LOG.debug('query = %s', query)

        self.npm_event_id_cursor = last_event_id
        x = self._query_xml(query)

        LOG.debug(x)

        try:
            return x.queryResult.data.row
        except AttributeError:
            return []

    def get_ucs_events(self):

        query = 'SELECT MAX(EventID) AS MaxEventID FROM Orion.NPM.UCSEvents'
        max = self._query_xml(query)

        LOG.debug('Max UCS event id query response = %s', max)

        last_event_id = max.queryResult.data.row.c0

        if not last_event_id or last_event_id == self.ucs_event_id_cursor:
            LOG.debug('No new events since event id %s. Skipping UCS event query...', last_event_id)
            return []

        LOG.debug('Get UCS events in range %s -> %s', self.ucs_event_id_cursor, last_event_id)

        query = (
            "SELECT E.EventID, E.Created, M.Name, F.DistinguishedName, E.DistinguishedName, E.Description, F.Status, E.Severity " +
            "FROM Orion.NPM.UCSEvents E " +
            "INNER JOIN Orion.NPM.UCSFabrics AS F ON E.HostNodeID = F.HostNodeID " +
            "INNER JOIN Orion.NPM.UCSManagers AS M ON F.NodeID = M.NodeID " +
            "WHERE EventID > %s AND EventID <= %s " % (self.ucs_event_id_cursor, last_event_id) +
            "ORDER BY EventID"
        )
        LOG.debug('query = %s', query)

        self.ucs_event_id_cursor = last_event_id
        x = self._query_xml(query)

        LOG.debug(x)

        try:
            return x.queryResult.data.row
        except AttributeError:
            return []

    def _query_xml(self, query):

        LOG.debug('Running SWQL query => %s', query)
        try:
            return self.client.service.QueryXml(query)
        except urllib2.URLError, e:
            LOG.warning('SWIS QueryXML() failed: %s', e)
            return None

    def _get_max_npm_event_id(self):

        query = 'SELECT MAX(EventID) AS MaxEventID FROM Orion.Events'
        max = self._query_xml(query)

        LOG.debug('Max NPM event id query response = %s', max)

        if max:
            return max.queryResult.data.row.c0

    def _get_max_ucs_event_id(self):

        query = 'SELECT MAX(EventID) AS MaxEventID FROM Orion.NPM.UCSEvents'
        max = self._query_xml(query)

        LOG.debug('Max UCS event id query response = %s', max)

        if max:
            return max.queryResult.data.row.c0



