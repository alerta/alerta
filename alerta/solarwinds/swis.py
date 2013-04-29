
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
    'Warn': 'warning'
}


class SwisClient(object):

    def __init__(self, username=None, password=None):

        self.wsdl = 'https://%s:17778/SolarWinds/InformationService/v3?wsdl' % CONF.solarwinds_host
        LOG.debug('wsdl = %s', self.wsdl)

        self.client = Client(self.wsdl, username=username, password=password)
        self.client.set_options(port='BasicHttpBinding_InformationService')
        LOG.debug('client = %s', self.client)

        query = 'SELECT MAX(EventID) AS MaxEventID FROM Orion.Events'
        max = self.client.service.QueryXml(query)

        self.nw_event_id_cursor = max.queryResult.data.row.c0
        self.if_event_id_cursor = max.queryResult.data.row.c0
        self.vol_event_id_cursor = max.queryResult.data.row.c0

    def get_nw_events(self):

        query = 'SELECT MAX(EventID) AS MaxEventID FROM Orion.Events'

        max = self.client.service.QueryXml(query)
        last_event_id = max.queryResult.data.row.c0

        LOG.debug('%s -> %s', self.nw_event_id_cursor, last_event_id)

        if last_event_id == self.nw_event_id_cursor:
            return []

        query = (
            "SELECT EventID, EventTime, N.NodeName, N.ObjectSubType, ET.Name, Message, Acknowledged, ET.Icon, N.StatusDescription " +
            "FROM Orion.Events E " +
            "INNER JOIN Orion.EventTypes AS ET ON E.EventType = ET.EventType " +
            "INNER JOIN Orion.Nodes AS N ON E.NetworkNode = N.NodeID " +
            "WHERE EventID > %s AND EventID <= %s " % (self.nw_event_id_cursor, last_event_id) +
            "AND NetObjectType = 'N' " +
            "ORDER BY EventID"
        )

        LOG.debug('query = %s', query)

        self.nw_event_id_cursor = last_event_id
        x = self.client.service.QueryXml(query)

        LOG.debug(x)

        try:
            return x.queryResult.data.row
        except AttributeError:
            return []

    def get_if_events(self):

        query = 'SELECT MAX(EventID) AS MaxEventID FROM Orion.Events'

        max = self.client.service.QueryXml(query)
        last_event_id = max.queryResult.data.row.c0

        LOG.debug('%s -> %s', self.if_event_id_cursor, last_event_id)

        if last_event_id == self.if_event_id_cursor:
            return []

        query = (
            "SELECT EventID, EventTime, N.NodeName, I.IfName, ET.Name, Message, Acknowledged, ET.Icon, I.StatusDescription " +
            "FROM Orion.Events E " +
            "INNER JOIN Orion.EventTypes AS ET ON E.EventType = ET.EventType " +
            "INNER JOIN Orion.Nodes AS N ON E.NetworkNode = N.NodeID " +
            "INNER JOIN Orion.NPM.Interfaces AS I ON E.NetObjectID = I.InterfaceID " +
            "WHERE EventID > %s AND EventID <= %s " % (self.if_event_id_cursor, last_event_id) +
            "AND NetObjectType = 'I' " +
            "ORDER BY EventID"
        )

        LOG.debug('query = %s', query)

        self.if_event_id_cursor = last_event_id
        x = self.client.service.QueryXml(query)

        LOG.debug(x)

        try:
            return x.queryResult.data.row
        except AttributeError:
            return []

    def get_vol_events(self):

        query = 'SELECT MAX(EventID) AS MaxEventID FROM Orion.Events'

        max = self.client.service.QueryXml(query)
        last_event_id = max.queryResult.data.row.c0

        LOG.debug('%s -> %s', self.vol_event_id_cursor, last_event_id)

        if last_event_id == self.vol_event_id_cursor:
            return []

        query = (
            "SELECT EventID, EventTime, N.NodeName, V.DisplayName, ET.Name, Message, Acknowledged, ET.Icon, V.VolumePercentUsed " +
            "FROM Orion.Events E " +
            "INNER JOIN Orion.EventTypes AS ET ON E.EventType = ET.EventType " +
            "INNER JOIN Orion.Nodes AS N ON E.NetworkNode = N.NodeID " +
            "INNER JOIN Orion.Volumes AS V ON E.NetObjectID = V.VolumeID " +
            "WHERE EventID > %s AND EventID <= %s " % (self.vol_event_id_cursor, last_event_id) +
            "AND NetObjectType = 'V' " +
            "ORDER BY EventID"
        )

        LOG.debug('query = %s', query)

        self.vol_event_id_cursor = last_event_id
        x = self.client.service.QueryXml(query)

        LOG.debug(x)

        try:
            return x.queryResult.data.row
        except AttributeError:
            return []




