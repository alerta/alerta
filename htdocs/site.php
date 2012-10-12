<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <title>Alert Console</title>
    <link href="css/bootstrap.css" rel="stylesheet">
    <link href="css/bootstrap-responsive.css" rel="stylesheet">
    <link href="css/custom.css" rel="stylesheet">
  </head>

  <body>
  <?php require($DOCUMENT_ROOT . "includes/menu.php"); ?>

  <div class="container">
    <?php require($DOCUMENT_ROOT . "includes/alerts.php"); ?>
    <?php require($DOCUMENT_ROOT . "includes/buttons.php"); ?>

      <div class="row show-grid">
        <div class="span12">
          <strong>Alert Summary</strong>
        <div class="row show-grid">
          <div class="span3">
            <table class="table table-bordered table-condensed summary" id="KPL" data-label="KPL">
              <thead>
                <tr> <th colspan="6" id="KPL-status">Kings Place</th> </tr>
              </thead>
              <tbody>
                <tr id="KPL-warnings" class="warnings">
                  <td id="KPL-critical">0</td>
                  <td id="KPL-major">0</td>
                  <td id="KPL-minor">0</td>
                  <td id="KPL-warning">0</td>
                  <td id="KPL-normal">0</td>
                </tr>
              </tbody>
            </table>
          </div>
          <div class="span3">
            <table class="table table-bordered table-condensed summary" id="BRK" data-label="BRK">
              <thead>
                <tr> <th colspan="6" id="BRK-status">Bracknell</th> </tr> 
              </thead>
              <tbody>
                <tr id="BRK-warnings" class="warnings">
                  <td id="BRK-critical">0</td>
                  <td id="BRK-major">0</td>
                  <td id="BRK-minor">0</td>
                  <td id="BRK-warning">0</td>
                  <td id="BRK-normal">0</td>
                </tr>
              </tbody>
            </table>
          </div>
          <div class="span3">
            <table class="table table-bordered table-condensed summary" id="eu-west-1" data-label="eu-west-1">
              <thead>
                <tr> <th colspan="6" id="eu-west-1-status">eu-west-1</th> </tr>
              </thead>
              <tbody>
                <tr id="eu-west-1-warnings" class="warnings">
                  <td id="eu-west-1-critical">0</td>
                  <td id="eu-west-1-major">0</td>
                  <td id="eu-west-1-minor">0</td>
                  <td id="eu-west-1-warning">0</td>
                  <td id="eu-west-1-normal">0</td>
                </tr>
              </tbody>
            </table>
          </div>
          <div class="span3">
            <table class="table table-bordered table-condensed summary" id="dev" data-label="dev">
              <thead>
                <tr> <th colspan="6" id="dev-status">GUDEV</th> </tr>
              </thead>
              <tbody>
                <tr id="dev-warnings" class="warnings">
                  <td id="dev-critical">0</td>
                  <td id="dev-major">0</td>
                  <td id="dev-minor">0</td>
                  <td id="dev-warning">0</td>
                  <td id="dev-normal">0</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
        <div class="row show-grid">
          <div class="span3">
            <table class="table table-bordered table-condensed summary" id="Physical" data-label="Physical">
              <thead>
                <tr> <th colspan="6" id="Physical-status">Physical</th> </tr>
              </thead>
              <tbody>
                <tr id="Physical-warnings" class="warnings">
                  <td id="Physical-critical">0</td>
                  <td id="Physical-major">0</td>
                  <td id="Physical-minor">0</td>
                  <td id="Physical-warning">0</td>
                  <td id="Physical-normal">0</td>
                </tr>
              </tbody>
            </table>
          </div>
          <div class="span3">
            <table class="table table-bordered table-condensed summary" id="VMware" data-label="VMware">
              <thead>
                <tr> <th colspan="6" id="VMware-status">VMware</th> </tr>
              </thead>
              <tbody>
                <tr id="VMware-warnings" class="warnings">
                  <td id="VMware-critical">0</td>
                  <td id="VMware-major">0</td>
                  <td id="VMware-minor">0</td>
                  <td id="VMware-warning">0</td>
                  <td id="VMware-normal">0</td>
                </tr>
              </tbody>
            </table>
          </div>
          <div class="span3">
            <table class="table table-bordered table-condensed summary" id="Xen" data-label="Xen">
              <thead>
                <tr> <th colspan="6" id="Xen-status">Xen</th> </tr>
              </thead>
              <tbody>
                <tr id="Xen-warnings" class="warnings">
                  <td id="Xen-critical">0</td>
                  <td id="Xen-major">0</td>
                  <td id="Xen-minor">0</td>
                  <td id="Xen-warning">0</td>
                  <td id="Xen-normal">0</td>
                </tr>
              </tbody>
            </table>
          </div>
          <div class="span3">
            <table class="table table-bordered table-condensed summary" id="KVM" data-label="KVM">
              <thead>
                <tr> <th colspan="6" id="KVM-status">KVM</th> </tr> 
              </thead>
              <tbody>
                <tr id="KVM-warnings" class="warnings">
                  <td id="KVM-critical">0</td>
                  <td id="KVM-major">0</td>
                  <td id="KVM-minor">0</td>
                  <td id="KVM-warning">0</td>
                  <td id="KVM-normal">0</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
        <div class="row show-grid">
          <div class="span3">
            <table class="table table-bordered table-condensed summary" id="Linux" data-label="Linux">
              <thead>
                <tr> <th colspan="6" id="Linux-status">Linux</th> </tr>
              </thead>
              <tbody>
                <tr id="Linux-warnings" class="warnings">
                  <td id="Linux-critical">0</td>
                  <td id="Linux-major">0</td>
                  <td id="Linux-minor">0</td>
                  <td id="Linux-warning">0</td>
                  <td id="Linux-normal">0</td>
                </tr>
              </tbody>
            </table>
          </div>
          <div class="span3">
            <table class="table table-bordered table-condensed summary" id="Solaris" data-label="Solaris">
              <thead>
                <tr> <th colspan="6" id="Solaris-status">Solaris</th> </tr>
              </thead>
              <tbody>
                <tr id="Solaris-warnings" class="warnings">
                  <td id="Solaris-critical">0</td>
                  <td id="Solaris-major">0</td>
                  <td id="Solaris-minor">0</td>
                  <td id="Solaris-warning">0</td>
                  <td id="Solaris-normal">0</td>
                </tr>
              </tbody>
            </table>
          </div>
          <div class="span3">
            <table class="table table-bordered table-condensed summary" id="Syslog" data-label="Syslog">
              <thead>
                <tr> <th colspan="6" id="Syslog-status">Syslog</th> </tr>
              </thead>
              <tbody>
                <tr id="Syslog-warnings" class="warnings">
                  <td id="Syslog-critical">0</td>
                  <td id="Syslog-major">0</td>
                  <td id="Syslog-minor">0</td>
                  <td id="Syslog-warning">0</td>
                  <td id="Syslog-normal">0</td>
                </tr>
              </tbody>
            </table>
          </div>
          <div class="span3">
            <table class="table table-bordered table-condensed summary" id="Network" data-label="Network">
              <thead>
                <tr> <th colspan="6" id="Network-status">Network</th> </tr>
              </thead>
              <tbody>
                <tr id="Network-warnings" class="warnings">
                  <td id="Network-critical">0</td>
                  <td id="Network-major">0</td>
                  <td id="Network-minor">0</td>
                  <td id="Network-warning">0</td>
                  <td id="Network-normal">0</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
        </div>
      </div>

      <!-- Alert Details -->
      <div class="row show-grid">
        <div class="span12">
          <table class="table table-bordered table-condensed" id="alert-details">
            <caption class="alerts-caption">
              Infrastructure - <span id="alert-details-caption">KPL</span> alert details
            </caption>
            <thead>
              <tr> <th></th><th>Severity</th><th>Status</th><th>Last Receive Time</th><th>Dupl. Count</th><th>Env.</th><th>Service</th><th>Cluster</th><th>Resource</th><th>Event</th><th>Value</th><th>Text</th></tr> 
            </thead>
            <tbody id="KPL-alerts" class="serviceAlerts initially-hidden">
            </tbody>
            <tbody id="BRK-alerts" class="serviceAlerts initially-hidden">
            </tbody>
            <tbody id="eu-west-1-alerts" class="serviceAlerts initially-hidden">
            </tbody>
            <tbody id="dev-alerts" class="serviceAlerts initially-hidden">
            </tbody>
            <tbody id="Physical-alerts" class="serviceAlerts initially-hidden">
            </tbody>
            <tbody id="VMware-alerts" class="serviceAlerts initially-hidden">
            </tbody>
            <tbody id="Xen-alerts" class="serviceAlerts initially-hidden">
            </tbody>
            <tbody id="KVM-alerts" class="serviceAlerts initially-hidden">
            </tbody>
            <tbody id="Linux-alerts" class="serviceAlerts initially-hidden">
            </tbody>
            <tbody id="Solaris-alerts" class="serviceAlerts initially-hidden">
            </tbody>
            <tbody id="Syslog-alerts" class="serviceAlerts initially-hidden">
            </tbody>
            <tbody id="Network-alerts" class="serviceAlerts initially-hidden">
            </tbody>
          </table>

        </div>
      </div>
      <!-- end Alert Details -->

    </div> <!-- end container -->
    <?php require($DOCUMENT_ROOT . "includes/scripts.php"); ?>

    <script>
      $(document).ready(function() {

        heartbeatAlerts();

        var env = "";
        var statusfilter = '&status=OPEN|ACK|CLOSED';
        var services = { 'KPL':       statusfilter+'&tags=datacentre:dc1',
                         'BRK':       statusfilter+'&tags=datacentre:dc2',
                         'eu-west-1': statusfilter+'&tags=datacentre:eu-west-1',
                         'dev':       statusfilter+'&tags=datacentre:dev',

                         'Physical':  statusfilter+'&tags=virtual:physical',
                         'VMware':    statusfilter+'&tags=virtual:vmware',
                         'Xen':       statusfilter+'&tags=virtual:xen',
                         'KVM':       statusfilter+'&tags=virutal:kvm',

                         'Linux':     statusfilter+'&tags=os:linux',
                         'Solaris':   statusfilter+'&tags=os:sunos',
                         'Syslog':    statusfilter+'&group=Syslog',
                         'Network':   statusfilter+'&service=Network',
                       };

        loadStatus(statusfilter, true);
        loadAlerts(services, true);

        $('#refresh-all').click(function() {
          loadStatus(statusfilter, false);
          loadAlerts(services, false)
        });
      });
    </script>
    
  </body>
</html>
