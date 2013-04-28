
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

        self.event_id_cursor = 0

    def get_events(self):

        query = 'SELECT MAX(EventID) AS MaxEventID FROM Orion.Events'

        max = self.client.service.QueryXml(query)
        last_event_id = max.queryResult.data.row.c0

        LOG.debug('%s -> %s', self.event_id_cursor, last_event_id)

        if last_event_id == self.event_id_cursor:
            return []

        query = 'SELECT EventID, EventTime, NetworkNode, NetObjectID, ET.Name, Message, Acknowledged, ET.Icon ' + \
                'FROM Orion.Events E ' + \
                'INNER JOIN Orion.EventTypes AS ET ON E.EventType = ET.EventType ' + \
                'WHERE EventID > %s AND EventID <= %s ' % (self.event_id_cursor, last_event_id) + \
                'ORDER BY EventID'

        LOG.debug('query = %s', query)

        self.event_id_cursor = last_event_id
        x = self.client.service.QueryXml(query)

        LOG.debug(x)

        return x.queryResult.data.row

