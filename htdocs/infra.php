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
            <table class="table table-bordered table-condensed summary" id="OS" data-label="OS">
              <thead>
                <tr> <th colspan="6" id="OS-status">OS</th> </tr>
              </thead>
              <tbody>
                <tr id="OS-warnings" class="warnings">
                  <td id="OS-critical">0</td>
                  <td id="OS-major">0</td>
                  <td id="OS-minor">0</td>
                  <td id="OS-warning">0</td>
                  <td id="OS-normal">0</td>
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
          <div class="span3">
            <table class="table table-bordered table-condensed summary" id="EC2" data-label="EC2">
              <thead>
                <tr> <th colspan="6" id="EC2-status">EC2 Servers</th> </tr> 
              </thead>
              <tbody>
                <tr id="EC2-warnings" class="warnings">
                  <td id="EC2-critical">0</td>
                  <td id="EC2-major">0</td>
                  <td id="EC2-minor">0</td>
                  <td id="EC2-warning">0</td>
                  <td id="EC2-normal">0</td>
                </tr>
              </tbody>
            </table>
          </div>
          <div class="span3">
            <table class="table table-bordered table-condensed summary" id="Puppet" data-label="Puppet">
              <thead>
                <tr> <th colspan="6" id="Puppet-status">Puppet</th> </tr> 
              </thead>
              <tbody>
                <tr id="Puppet-warnings" class="warnings">
                  <td id="Puppet-critical">0</td>
                  <td id="Puppet-major">0</td>
                  <td id="Puppet-minor">0</td>
                  <td id="Puppet-warning">0</td>
                  <td id="Puppet-normal">0</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
        <div class="row show-grid">
          <div class="span3">
            <table class="table table-bordered table-condensed summary" id="Linux" data-label="Linux">
              <thead>
                <tr> <th colspan="6" id="Linux-status">Linux Servers</th> </tr>
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
            <table class="table table-bordered table-condensed summary" id="Web" data-label="Web">
              <thead>
                <tr> <th colspan="6" id="Web-status">Web</th> </tr>
              </thead>
              <tbody>
                <tr id="Web-warnings" class="warnings">
                  <td id="Web-critical">0</td>
                  <td id="Web-major">0</td>
                  <td id="Web-minor">0</td>
                  <td id="Web-warning">0</td>
                  <td id="Web-normal">0</td>
                </tr>
              </tbody>
            </table>
          </div>
          <div class="span3">
            <table class="table table-bordered table-condensed summary" id="Ganglia" data-label="Ganglia">
              <thead>
                <tr> <th colspan="6" id="Ganglia-status">Ganglia</th> </tr> 
              </thead>
              <tbody>
                <tr id="Ganglia-warnings" class="warnings">
                  <td id="Ganglia-critical">0</td>
                  <td id="Ganglia-major">0</td>
                  <td id="Ganglia-minor">0</td>
                  <td id="Ganglia-warning">0</td>
                  <td id="Ganglia-normal">0</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
        <div class="row show-grid">
          <div class="span3">
            <table class="table table-bordered table-condensed summary" id="Solaris" data-label="Solaris">
              <thead>
                <tr> <th colspan="6" id="Solaris-status">Solaris Servers</th> </tr>
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
            <table class="table table-bordered table-condensed summary" id="Acknowledged" data-label="Acknowledged">
              <thead>
                <tr> <th colspan="6" id="Acknowledged-status">Acknowledged</th> </tr>
              </thead>
              <tbody>
                <tr id="Acknowledged-warnings" class="warnings">
                  <td id="Acknowledged-critical">0</td>
                  <td id="Acknowledged-major">0</td>
                  <td id="Acknowledged-minor">0</td>
                  <td id="Acknowledged-warning">0</td>
                  <td id="Acknowledged-normal">0</td>
                </tr>
              </tbody>
            </table>
          </div>
          <div class="span3">
            <table class="table table-bordered table-condensed summary" id="Deploys" data-label="Deploys">
              <thead>
                <tr> <th colspan="6" id="Deploys-status">Deploys</th> </tr>
              </thead>
              <tbody>
                <tr id="Deploys-warnings" class="warnings">
                  <td id="Deploys-critical">0</td>
                  <td id="Deploys-major">0</td>
                  <td id="Deploys-minor">0</td>
                  <td id="Deploys-warning">0</td>
                  <td id="Deploys-normal">0</td>
                </tr>
              </tbody>
            </table>
          </div>
          <div class="span3">
            <table class="table table-bordered table-condensed summary" id="Reboot" data-label="Reboot">
              <thead>
                <tr> <th colspan="6" id="Reboot-status">Server Reboots</th> </tr>
              </thead>
              <tbody>
                <tr id="Reboot-warnings" class="warnings">
                  <td id="Reboot-critical">0</td>
                  <td id="Reboot-major">0</td>
                  <td id="Reboot-minor">0</td>
                  <td id="Reboot-warning">0</td>
                  <td id="Reboot-normal">0</td>
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
              Infrastructure - <span id="alert-details-caption">R2</span> alert details
            </caption>
            <thead>
              <tr> <th></th><th>Severity</th><th>Status</th><th>Last Receive Time</th><th>Dupl. Count</th><th>Env.</th><th>Service</th><th>Cluster</th><th>Resource</th><th>Event</th><th>Value</th><th>Text</th></tr> 
            </thead>
            <tbody id="OS-alerts" class="serviceAlerts initially-hidden">
            </tbody>
            <tbody id="Linux-alerts" class="serviceAlerts initially-hidden">
            </tbody>
            <tbody id="Solaris-alerts" class="serviceAlerts initially-hidden">
            </tbody>
            <tbody id="Network-alerts" class="serviceAlerts initially-hidden">
            </tbody>
            <tbody id="EC2-alerts" class="serviceAlerts initially-hidden">
            </tbody>
            <tbody id="Puppet-alerts" class="serviceAlerts initially-hidden">
            </tbody>
            <tbody id="Syslog-alerts" class="serviceAlerts initially-hidden">
            </tbody>
            <tbody id="Web-alerts" class="serviceAlerts initially-hidden">
            </tbody>
            <tbody id="Ganglia-alerts" class="serviceAlerts initially-hidden">
            </tbody>
            <tbody id="Acknowledged-alerts" class="serviceAlerts initially-hidden">
            </tbody>
            <tbody id="Deploys-alerts" class="serviceAlerts initially-hidden">
            </tbody>
            <tbody id="Reboot-alerts" class="serviceAlerts initially-hidden">
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

        var env = "INFRA";
        var statusfilter = 'environment='+env+'&status=OPEN|ACK|CLOSED';
        var services = { 'OS':       'status=OPEN|ACK|CLOSED&group=OS',
                         'Linux':    'status=OPEN|ACK|CLOSED&tags=os:linux',
                         'Solaris':  'status=OPEN|ACK|CLOSED&tags=os:sunos',
                         'Network':  statusfilter+'&service=^Network',
                         'EC2':      statusfilter+'&service=EC2',
                         'Puppet':   'status=OPEN|ACK|CLOSED&group=Puppet',
                         'Syslog':   'status=OPEN|ACK|CLOSED&group=Syslog',
                         'Web':      'status=OPEN|ACK|CLOSED&group=Web',
                         'Ganglia':  'status=OPEN|ACK|CLOSED&group=Ganglia',
                         'Acknowledged': 'status=ACK',
                         'Deploys':  'status=OPEN|ACK|CLOSED&event=Deploy',
                         'Reboot':   'status=OPEN|ACK|CLOSED&event=ServerReboot',
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
