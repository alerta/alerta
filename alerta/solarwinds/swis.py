
from suds.client import Client

from alerta.common import config
from alerta.common import log as logging

LOG = logging.getLogger(__name__)
CONF = config.CONF

SOLAR_WINDS_STATUS_LEVELS = {
    0: 'Unknown',
    1: 'Up',
    2: 'Down',
    3: 'Warning',
    14: 'Critical'
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

        self.nw_event_id_cursor = 0
        self.if_event_id_cursor = 0
        self.vol_event_id_cursor = 0

    def get_nw_events(self):

        query = 'SELECT MAX(EventID) AS MaxEventID FROM Orion.Events'

        max = self.client.service.QueryXml(query)
        last_event_id = max.queryResult.data.row.c0

        LOG.debug('%s -> %s', self.nw_event_id_cursor, last_event_id)

        if last_event_id == self.nw_event_id_cursor:
            return []

        query = (
            "SELECT EventID, EventTime, N.NodeName, N.ObjectSubType, ET.Name, Message, Acknowledged, ET.Icon " +
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

        return x.queryResult.data.row

    def get_if_events(self):

        query = 'SELECT MAX(EventID) AS MaxEventID FROM Orion.Events'

        max = self.client.service.QueryXml(query)
        last_event_id = max.queryResult.data.row.c0

        LOG.debug('%s -> %s', self.if_event_id_cursor, last_event_id)

        if last_event_id == self.if_event_id_cursor:
            return []

        query = (
            "SELECT EventID, EventTime, N.NodeName, I.IfName, ET.Name, Message, Acknowledged, ET.Icon " +
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

        return x.queryResult.data.row

    def get_vol_events(self):

        query = 'SELECT MAX(EventID) AS MaxEventID FROM Orion.Events'

        max = self.client.service.QueryXml(query)
        last_event_id = max.queryResult.data.row.c0

        LOG.debug('%s -> %s', self.vol_event_id_cursor, last_event_id)

        if last_event_id == self.vol_event_id_cursor:
            return []

        query = (
            "SELECT EventID, EventTime, N.NodeName, V.DisplayName, ET.Name, Message, Acknowledged, ET.Icon " +
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

        return x.queryResult.data.row



