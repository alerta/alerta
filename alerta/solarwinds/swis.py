
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

SOLAR_WINDS_CORRELATED_EVENTS = {
    'AlertReset':     ['AlertReset', 'AlertTriggered'],  # 5001
    'AlertTriggered': ['AlertReset', 'AlertTriggered'],  # 5000

    'ApplicationRestart': ['ApplicationRestart', 'ApplicationStopped'],  # 31
    'ApplicationStopped': ['ApplicationRestart', 'ApplicationStopped'],  # 30

    'CoreBLServiceStarted': ['CoreBLServiceStarted', 'CoreBLServiceStopped', 'CoreBLLicensing'],  # 1500
    'CoreBLServiceStopped': ['CoreBLServiceStarted', 'CoreBLServiceStopped', 'CoreBLLicensing'],  # 1501
    'CoreBLLicensing':      ['CoreBLServiceStarted', 'CoreBLServiceStopped', 'CoreBLLicensing'],  # 1502

    'Critical':      ['Critical', 'Warning', 'Informational'],  # 1002
    'Warning':       ['Critical', 'Warning', 'Informational'],  # 1001
    'Informational': ['Critical', 'Warning', 'Informational'],  # 1000

    'CriticalSystemError': [],  # 15

    'FailBack': ['FailBack', 'FailOver'],  # 26
    'FailOver': ['FailBack', 'FailOver'],  # 25

    'GroupCreated':        ['GroupCreated', 'GroupCritical', 'GroupDisabled', 'GroupDown', 'GroupExternal',
                            'GroupMembersChanged', 'GroupRemoved', 'GroupShutdown', 'GroupTesting', 'GroupUnknown',
                            'GroupUnmanaged', 'GroupUnplugged', 'GroupUnreachable', 'GroupUp', 'GroupWarning'],  # 56
    'GroupCritical':       ['GroupCreated', 'GroupCritical', 'GroupDisabled', 'GroupDown', 'GroupExternal',
                            'GroupMembersChanged', 'GroupRemoved', 'GroupShutdown', 'GroupTesting', 'GroupUnknown',
                            'GroupUnmanaged', 'GroupUnplugged', 'GroupUnreachable', 'GroupUp', 'GroupWarning'],  # 58
    'GroupDisabled':       ['GroupCreated', 'GroupCritical', 'GroupDisabled', 'GroupDown', 'GroupExternal',
                            'GroupMembersChanged', 'GroupRemoved', 'GroupShutdown', 'GroupTesting', 'GroupUnknown',
                            'GroupUnmanaged', 'GroupUnplugged', 'GroupUnreachable', 'GroupUp', 'GroupWarning'],  # 66
    'GroupDown':           ['GroupCreated', 'GroupCritical', 'GroupDisabled', 'GroupDown', 'GroupExternal',
                            'GroupMembersChanged', 'GroupRemoved', 'GroupShutdown', 'GroupTesting', 'GroupUnknown',
                            'GroupUnmanaged', 'GroupUnplugged', 'GroupUnreachable', 'GroupUp', 'GroupWarning'],  # 50
    'GroupExternal':       ['GroupCreated', 'GroupCritical', 'GroupDisabled', 'GroupDown', 'GroupExternal',
                            'GroupMembersChanged', 'GroupRemoved', 'GroupShutdown', 'GroupTesting', 'GroupUnknown',
                            'GroupUnmanaged', 'GroupUnplugged', 'GroupUnreachable', 'GroupUp', 'GroupWarning'],  # 59
    'GroupMembersChanged': ['GroupCreated', 'GroupCritical', 'GroupDisabled', 'GroupDown', 'GroupExternal',
                            'GroupMembersChanged', 'GroupRemoved', 'GroupShutdown', 'GroupTesting', 'GroupUnknown',
                            'GroupUnmanaged', 'GroupUnplugged', 'GroupUnreachable', 'GroupUp', 'GroupWarning'],  # 53
    'GroupRemoved':        ['GroupCreated', 'GroupCritical', 'GroupDisabled', 'GroupDown', 'GroupExternal',
                            'GroupMembersChanged', 'GroupRemoved', 'GroupShutdown', 'GroupTesting', 'GroupUnknown',
                            'GroupUnmanaged', 'GroupUnplugged', 'GroupUnreachable', 'GroupUp', 'GroupWarning'],  # 57
    'GroupShutdown':       ['GroupCreated', 'GroupCritical', 'GroupDisabled', 'GroupDown', 'GroupExternal',
                            'GroupMembersChanged', 'GroupRemoved', 'GroupShutdown', 'GroupTesting', 'GroupUnknown',
                            'GroupUnmanaged', 'GroupUnplugged', 'GroupUnreachable', 'GroupUp', 'GroupWarning'],  # 60
    'GroupTesting':        ['GroupCreated', 'GroupCritical', 'GroupDisabled', 'GroupDown', 'GroupExternal',
                            'GroupMembersChanged', 'GroupRemoved', 'GroupShutdown', 'GroupTesting', 'GroupUnknown',
                            'GroupUnmanaged', 'GroupUnplugged', 'GroupUnreachable', 'GroupUp', 'GroupWarning'],  # 61
    'GroupUnknown':        ['GroupCreated', 'GroupCritical', 'GroupDisabled', 'GroupDown', 'GroupExternal',
                            'GroupMembersChanged', 'GroupRemoved', 'GroupShutdown', 'GroupTesting', 'GroupUnknown',
                            'GroupUnmanaged', 'GroupUnplugged', 'GroupUnreachable', 'GroupUp', 'GroupWarning'],  # 62
    'GroupUnmanaged':      ['GroupCreated', 'GroupCritical', 'GroupDisabled', 'GroupDown', 'GroupExternal',
                            'GroupMembersChanged', 'GroupRemoved', 'GroupShutdown', 'GroupTesting', 'GroupUnknown',
                            'GroupUnmanaged', 'GroupUnplugged', 'GroupUnreachable', 'GroupUp', 'GroupWarning'],  # 63
    'GroupUnplugged':      ['GroupCreated', 'GroupCritical', 'GroupDisabled', 'GroupDown', 'GroupExternal',
                            'GroupMembersChanged', 'GroupRemoved', 'GroupShutdown', 'GroupTesting', 'GroupUnknown',
                            'GroupUnmanaged', 'GroupUnplugged', 'GroupUnreachable', 'GroupUp', 'GroupWarning'],  # 65
    'GroupUnreachable':    ['GroupCreated', 'GroupCritical', 'GroupDisabled', 'GroupDown', 'GroupExternal',
                            'GroupMembersChanged', 'GroupRemoved', 'GroupShutdown', 'GroupTesting', 'GroupUnknown',
                            'GroupUnmanaged', 'GroupUnplugged', 'GroupUnreachable', 'GroupUp', 'GroupWarning'],  # 64
    'GroupUp':             ['GroupCreated', 'GroupCritical', 'GroupDisabled', 'GroupDown', 'GroupExternal',
                            'GroupMembersChanged', 'GroupRemoved', 'GroupShutdown', 'GroupTesting', 'GroupUnknown',
                            'GroupUnmanaged', 'GroupUnplugged', 'GroupUnreachable', 'GroupUp', 'GroupWarning'],  # 52
    'GroupWarning':        ['GroupCreated', 'GroupCritical', 'GroupDisabled', 'GroupDown', 'GroupExternal',
                            'GroupMembersChanged', 'GroupRemoved', 'GroupShutdown', 'GroupTesting', 'GroupUnknown',
                            'GroupUnmanaged', 'GroupUnplugged', 'GroupUnreachable', 'GroupUp', 'GroupWarning'],  # 51

    'HardwareCritical':      ['HardwareCritical', 'HardwareDown', 'HardwareManaged', 'HardwareUndefined',
                              'HardwareUnknown', 'HardwareUnmanaged', 'HardwareUnreachable', 'HardwareUp',
                              'HardwareWarning'],  # 521
    'HardwareDown':          ['HardwareCritical', 'HardwareDown', 'HardwareManaged', 'HardwareUndefined',
                              'HardwareUnknown', 'HardwareUnmanaged', 'HardwareUnreachable', 'HardwareUp',
                              'HardwareWarning'],  # 522
    'HardwareManaged':       ['HardwareCritical', 'HardwareDown', 'HardwareManaged', 'HardwareUndefined',
                              'HardwareUnknown', 'HardwareUnmanaged', 'HardwareUnreachable', 'HardwareUp',
                              'HardwareWarning'],  # 517
    'HardwareUndefined':     ['HardwareCritical', 'HardwareDown', 'HardwareManaged', 'HardwareUndefined',
                              'HardwareUnknown', 'HardwareUnmanaged', 'HardwareUnreachable', 'HardwareUp',
                              'HardwareWarning'],  # 515
    'HardwareUnknown':       ['HardwareCritical', 'HardwareDown', 'HardwareManaged', 'HardwareUndefined',
                              'HardwareUnknown', 'HardwareUnmanaged', 'HardwareUnreachable', 'HardwareUp',
                              'HardwareWarning'],  # 514
    'HardwareUnmanaged':     ['HardwareCritical', 'HardwareDown', 'HardwareManaged', 'HardwareUndefined',
                              'HardwareUnknown', 'HardwareUnmanaged', 'HardwareUnreachable', 'HardwareUp',
                              'HardwareWarning'],  # 516
    'HardwareUnreachable':   ['HardwareCritical', 'HardwareDown', 'HardwareManaged', 'HardwareUndefined',
                              'HardwareUnknown', 'HardwareUnmanaged', 'HardwareUnreachable', 'HardwareUp',
                              'HardwareWarning'],  # 518
    'HardwareUp':            ['HardwareCritical', 'HardwareDown', 'HardwareManaged', 'HardwareUndefined',
                              'HardwareUnknown', 'HardwareUnmanaged', 'HardwareUnreachable', 'HardwareUp',
                              'HardwareWarning'],  # 519
    'HardwareWarning':       ['HardwareCritical', 'HardwareDown', 'HardwareManaged', 'HardwareUndefined',
                              'HardwareUnknown', 'HardwareUnmanaged', 'HardwareUnreachable', 'HardwareUp',
                              'HardwareWarning'],  # 520

    'HardwareSensorCritical': ['HardwareSensorCritical', 'HardwareSensorDown', 'HardwareSensorUnknown',
                               'HardwareSensorUp', 'HardwareSensorWarning'],  # 531
    'HardwareSensorDown':     ['HardwareSensorCritical', 'HardwareSensorDown', 'HardwareSensorUnknown',
                               'HardwareSensorUp', 'HardwareSensorWarning'],  # 532
    'HardwareSensorUnknown':  ['HardwareSensorCritical', 'HardwareSensorDown', 'HardwareSensorUnknown',
                               'HardwareSensorUp', 'HardwareSensorWarning'],  # 528
    'HardwareSensorUp':       ['HardwareSensorCritical', 'HardwareSensorDown', 'HardwareSensorUnknown',
                               'HardwareSensorUp', 'HardwareSensorWarning'],  # 529
    'HardwareSensorWarning':  ['HardwareSensorCritical', 'HardwareSensorDown', 'HardwareSensorUnknown',
                               'HardwareSensorUp', 'HardwareSensorWarning'],  # 530

    'HardwareTypeCritical': ['HardwareTypeCritical', 'HardwareTypeDown', 'HardwareTypeUnknown', 'HardwareTypeUp',
                             'HardwareTypeWarning'],  # 526
    'HardwareTypeDown':     ['HardwareTypeCritical', 'HardwareTypeDown', 'HardwareTypeUnknown', 'HardwareTypeUp',
                             'HardwareTypeWarning'],  # 527
    'HardwareTypeUnknown':  ['HardwareTypeCritical', 'HardwareTypeDown', 'HardwareTypeUnknown', 'HardwareTypeUp',
                             'HardwareTypeWarning'],  # 523
    'HardwareTypeUp':       ['HardwareTypeCritical', 'HardwareTypeDown', 'HardwareTypeUnknown', 'HardwareTypeUp',
                             'HardwareTypeWarning'],  # 524
    'HardwareTypeWarning':  ['HardwareTypeCritical', 'HardwareTypeDown', 'HardwareTypeUnknown', 'HardwareTypeUp',
                             'HardwareTypeWarning'],  # 525

    'InterfaceAdded':       ['InterfaceAdded', 'InterfaceChanged', 'InterfaceDisappeared', 'InterfaceDown',
                             'InterfaceEnabled', 'InterfaceReappeared', 'InterfaceRemapped', 'InterfaceRemoved',
                             'InterfaceShutdown', 'InterfaceUnknown', 'InterfaceUp'],  # 16
    'InterfaceChanged':     ['InterfaceAdded', 'InterfaceChanged', 'InterfaceDisappeared', 'InterfaceDown',
                             'InterfaceEnabled', 'InterfaceReappeared', 'InterfaceRemapped', 'InterfaceRemoved',
                             'InterfaceShutdown', 'InterfaceUnknown', 'InterfaceUp'],  # 19
    'InterfaceDisappeared': ['InterfaceAdded', 'InterfaceChanged', 'InterfaceDisappeared', 'InterfaceDown',
                             'InterfaceEnabled', 'InterfaceReappeared', 'InterfaceRemapped', 'InterfaceRemoved',
                             'InterfaceShutdown', 'InterfaceUnknown', 'InterfaceUp'],  # 23
    'InterfaceDown':        ['InterfaceAdded', 'InterfaceChanged', 'InterfaceDisappeared', 'InterfaceDown',
                             'InterfaceEnabled', 'InterfaceReappeared', 'InterfaceRemapped', 'InterfaceRemoved',
                             'InterfaceShutdown', 'InterfaceUnknown', 'InterfaceUp'],  # 10
    'InterfaceEnabled':     ['InterfaceAdded', 'InterfaceChanged', 'InterfaceDisappeared', 'InterfaceDown',
                             'InterfaceEnabled', 'InterfaceReappeared', 'InterfaceRemapped', 'InterfaceRemoved',
                             'InterfaceShutdown', 'InterfaceUnknown', 'InterfaceUp'],  # 22
    'InterfaceReappeared':  ['InterfaceAdded', 'InterfaceChanged', 'InterfaceDisappeared', 'InterfaceDown',
                             'InterfaceEnabled', 'InterfaceReappeared', 'InterfaceRemapped', 'InterfaceRemoved',
                             'InterfaceShutdown', 'InterfaceUnknown', 'InterfaceUp'],  # 24
    'InterfaceRemapped':    ['InterfaceAdded', 'InterfaceChanged', 'InterfaceDisappeared', 'InterfaceDown',
                             'InterfaceEnabled', 'InterfaceReappeared', 'InterfaceRemapped', 'InterfaceRemoved',
                             'InterfaceShutdown', 'InterfaceUnknown', 'InterfaceUp'],  # 18
    'InterfaceRemoved':     ['InterfaceAdded', 'InterfaceChanged', 'InterfaceDisappeared', 'InterfaceDown',
                             'InterfaceEnabled', 'InterfaceReappeared', 'InterfaceRemapped', 'InterfaceRemoved',
                             'InterfaceShutdown', 'InterfaceUnknown', 'InterfaceUp'],  # 17
    'InterfaceShutdown':    ['InterfaceAdded', 'InterfaceChanged', 'InterfaceDisappeared', 'InterfaceDown',
                             'InterfaceEnabled', 'InterfaceReappeared', 'InterfaceRemapped', 'InterfaceRemoved',
                             'InterfaceShutdown', 'InterfaceUnknown', 'InterfaceUp'],  # 12
    'InterfaceUnknown':     ['InterfaceAdded', 'InterfaceChanged', 'InterfaceDisappeared', 'InterfaceDown',
                             'InterfaceEnabled', 'InterfaceReappeared', 'InterfaceRemapped', 'InterfaceRemoved',
                             'InterfaceShutdown', 'InterfaceUnknown', 'InterfaceUp'],  # 13
    'InterfaceUp':          ['InterfaceAdded', 'InterfaceChanged', 'InterfaceDisappeared', 'InterfaceDown',
                             'InterfaceEnabled', 'InterfaceReappeared', 'InterfaceRemapped', 'InterfaceRemoved',
                             'InterfaceShutdown', 'InterfaceUnknown', 'InterfaceUp'],  # 11

    'UnManageInterface': ['UnManageInterface', 'ManageInterface'],  # 140
    'ManageInterface':   ['UnManageInterface', 'ManageInterface'],  # 141

    'UnManageNode': ['UnManageNode', 'ManageNode'],  # 40
    'ManageNode':   ['UnManageNode', 'ManageNode'],  # 41

    'MonitoringStarted': ['MonitoringStarted', 'MonitoringStopped'],  # 20
    'MonitoringStopped': ['MonitoringStarted', 'MonitoringStopped'],  # 21

    'NodeAdded':    ['NodeAdded', 'NodeChanged', 'NodeDown', 'NodeRebooted', 'NodeRemoved', 'NodeUp', 'NodeWarning'],  # 9
    'NodeChanged':  ['NodeAdded', 'NodeChanged', 'NodeDown', 'NodeRebooted', 'NodeRemoved', 'NodeUp', 'NodeWarning'],  # 100
    'NodeDown':     ['NodeAdded', 'NodeChanged', 'NodeDown', 'NodeRebooted', 'NodeRemoved', 'NodeUp', 'NodeWarning'],  # 1
    'NodeRebooted': ['NodeAdded', 'NodeChanged', 'NodeDown', 'NodeRebooted', 'NodeRemoved', 'NodeUp', 'NodeWarning'],  # 14
    'NodeRemoved':  ['NodeAdded', 'NodeChanged', 'NodeDown', 'NodeRebooted', 'NodeRemoved', 'NodeUp', 'NodeWarning'],  # 8
    'NodeUp':       ['NodeAdded', 'NodeChanged', 'NodeDown', 'NodeRebooted', 'NodeRemoved', 'NodeUp', 'NodeWarning'],  # 5
    'NodeWarning':  ['NodeAdded', 'NodeChanged', 'NodeDown', 'NodeRebooted', 'NodeRemoved', 'NodeUp', 'NodeWarning'],  # 2

    'NPMBLServiceStarted': ['NPMBLServiceStarted', 'NPMBLServiceStopped', 'NPMBLLicensing'],  # 150
    'NPMBLServiceStopped': ['NPMBLServiceStarted', 'NPMBLServiceStopped', 'NPMBLLicensing'],  # 151
    'NPMBLLicensing':      ['NPMBLServiceStarted', 'NPMBLServiceStopped', 'NPMBLLicensing'],  # 152

    'NPMModuleEngineStarted': ['NPMModuleEngineStarted', 'NPMModuleEngineStopped', 'NPMLicensing'],  # 600
    'NPMModuleEngineStopped': ['NPMModuleEngineStarted', 'NPMModuleEngineStopped', 'NPMLicensing'],  # 601
    'NPMLicensing':           ['NPMModuleEngineStarted', 'NPMModuleEngineStopped', 'NPMLicensing'],  # 602

    'PollingMethodChanged': [],  # 99

    'RogueDetected': [],  # 603
    'ThinAPDisappeared': [],  # 604

    'VIMServiceStarted': ['VIMServiceStarted', 'VIMServiceStopped'],  # 700
    'VIMServiceStopped': ['VIMServiceStarted', 'VIMServiceStopped'],  # 701

    'VolumeAdded':       ['VolumeAdded', 'VolumeChanged', 'VolumeDisappeared', 'VolumeReappeared', 'VolumeRemapped',
                          'VolumeRemoved'],  # 202
    'VolumeChanged':     ['VolumeAdded', 'VolumeChanged', 'VolumeDisappeared', 'VolumeReappeared', 'VolumeRemapped',
                          'VolumeRemoved'],  # 201
    'VolumeDisappeared': ['VolumeAdded', 'VolumeChanged', 'VolumeDisappeared', 'VolumeReappeared', 'VolumeRemapped',
                          'VolumeRemoved'],  # 210
    'VolumeReappeared':  ['VolumeAdded', 'VolumeChanged', 'VolumeDisappeared', 'VolumeReappeared', 'VolumeRemapped',
                          'VolumeRemoved'],  # 211
    'VolumeRemapped':    ['VolumeAdded', 'VolumeChanged', 'VolumeDisappeared', 'VolumeReappeared', 'VolumeRemapped',
                          'VolumeRemoved'],  # 200
    'VolumeRemoved':     ['VolumeAdded', 'VolumeChanged', 'VolumeDisappeared', 'VolumeReappeared', 'VolumeRemapped',
                          'VolumeRemoved'],  # 203

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
        self.npm_event_id_cursor = None
        self.ucs_event_id_cursor = None

        if os.path.isfile(self.cursor_file):
            try:
                self.npm_event_id_cursor, self.ucs_event_id_cursor = open(self.cursor_file).read().splitlines()
                LOG.info('Event IDs cursor read from file: %s, %s', self.npm_event_id_cursor, self.ucs_event_id_cursor)
            except Exception, e:
                LOG.error('Failed to read event IDs from cursor file: %s', e)

        if not self.npm_event_id_cursor:
            self.npm_event_id_cursor = self._get_max_npm_event_id()
            LOG.info('NPM Event ID cursor queried from db: %s', self.npm_event_id_cursor)

        if not self.ucs_event_id_cursor:
            self.ucs_event_id_cursor = self._get_max_ucs_event_id()
            LOG.info('UCS Event ID cursor queried from db: %s', self.ucs_event_id_cursor)

    def get_npm_events(self):

        last_event_id = self._get_max_npm_event_id()

        if not last_event_id:
            raise IOError
        if last_event_id == self.npm_event_id_cursor:
            LOG.debug('No new events since event id %s. Skipping NPM event query...', last_event_id)
            self._save_cursor()
            return []

        LOG.debug('Get network events in range %s -> %s', self.npm_event_id_cursor, last_event_id)

        query = (
            "SELECT EventID, EventTime, N.NodeName, N.ObjectSubType AS Object, ET.Name, Message, ET.Icon, ET.Icon " +
            "FROM Orion.Events E " +
            "INNER JOIN Orion.EventTypes AS ET ON E.EventType = ET.EventType " +
            "INNER JOIN Orion.Nodes AS N ON E.NetworkNode = N.NodeID " +
            "WHERE EventID > %s AND EventID <= %s " % (self.npm_event_id_cursor, last_event_id) +
            "AND NetObjectType = 'N' " +
            "UNION ALL "
        )

        query += (
            "(SELECT EventID, EventTime, N.NodeName, I.IfName AS Object, ET.Name, Message, ET.Icon, ET.Icon " +
            "FROM Orion.Events E " +
            "INNER JOIN Orion.EventTypes AS ET ON E.EventType = ET.EventType " +
            "INNER JOIN Orion.Nodes AS N ON E.NetworkNode = N.NodeID " +
            "INNER JOIN Orion.NPM.Interfaces AS I ON E.NetObjectID = I.InterfaceID " +
            "WHERE EventID > %s AND EventID <= %s " % (self.npm_event_id_cursor, last_event_id) +
            "AND NetObjectType = 'I') " +
            "UNION ALL "
        )

        query += (
            "(SELECT EventID, EventTime, N.NodeName, V.DisplayName AS Object, ET.Name, Message, ET.Icon, ET.Icon " +
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

        self._save_cursor()
        try:
            return x.queryResult.data.row
        except AttributeError:
            return []

    def get_ucs_events(self):

        last_event_id = self._get_max_ucs_event_id()

        if not last_event_id:
            raise IOError
        if last_event_id == self.ucs_event_id_cursor:
            LOG.debug('No new events since event id %s. Skipping UCS event query...', last_event_id)
            self._save_cursor()
            return []

        LOG.debug('Get UCS events in range %s -> %s', self.ucs_event_id_cursor, last_event_id)

        query = (
            "SELECT E.EventID, E.Created, M.Name, F.DistinguishedName, E.Name, E.Description, F.Status, E.Severity " +
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

        self._save_cursor()
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

    def _save_cursor(self):

        try:
            f = open(self.cursor_file, 'w')
            f.write('%s\n%s\n' % (self.npm_event_id_cursor, self.ucs_event_id_cursor))
            f.close()
            LOG.info('Wrote event ID cursors to file %s: %s, %s', self.cursor_file, self.npm_event_id_cursor, self.ucs_event_id_cursor)
        except IOError, e:
            LOG.error('Failed to write event ID cursor to file %s: %s', self.cursor_file, e)

