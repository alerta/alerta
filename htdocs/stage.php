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
            <table class="table table-bordered table-condensed summary" id="R2" data-label="R2">
              <thead>
                <tr> <th colspan="6" id="R2-status">R2</th> </tr> 
              </thead>
              <tbody>
                <tr id="R2-warnings" class="warnings">
                  <td id="R2-critical">0</td>
                  <td id="R2-major">0</td>
                  <td id="R2-minor">0</td>
                  <td id="R2-warning">0</td>
                  <td id="R2-normal">0</td>
                </tr>
              </tbody>
            </table>
          </div>
          <div class="span3">
            <table class="table table-bordered table-condensed summary" id="Discussion" data-label="Discussion">
              <thead>
                <tr> <th colspan="6" id="Discussion-status">Discussion</th> </tr> 
              </thead>
              <tbody>
                <tr id="Discussion-warnings" class="warnings">
                  <td id="Discussion-critical">0</td>
                  <td id="Discussion-major">0</td>
                  <td id="Discussion-minor">0</td>
                  <td id="Discussion-warning">0</td>
                  <td id="Discussion-normal">0</td>
                </tr>
              </tbody>
            </table>
          </div>
          <div class="span3">
            <table class="table table-bordered table-condensed summary" id="ContentAPI" data-label="Content API">
              <thead>
                <tr> <th colspan="6" id="ContentAPI-status">Content API</th> </tr> 
              </thead>
              <tbody>
                <tr id="ContentAPI-warnings" class="warnings">
                  <td id="ContentAPI-critical">0</td>
                  <td id="ContentAPI-major">0</td>
                  <td id="ContentAPI-minor">0</td>
                  <td id="ContentAPI-warning">0</td>
                  <td id="ContentAPI-normal">0</td>
                </tr>
              </tbody>
            </table>
          </div>
          <div class="span3">
            <table class="table table-bordered table-condensed summary" id="Identity" data-label="Identity">
              <thead>
                <tr> <th colspan="6" id="Identity-status">Identity</th> </tr> 
              </thead>
              <tbody>
                <tr id="Identity-warnings" class="warnings">
                  <td id="Identity-critical">0</td>
                  <td id="Identity-major">0</td>
                  <td id="Identity-minor">0</td>
                  <td id="Identity-warning">0</td>
                  <td id="Identity-normal">0</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
        <div class="row show-grid">
          <div class="span3">
            <table class="table table-bordered table-condensed summary" id="R1" data-label="R1">
              <thead>
                <tr> <th colspan="6" id="R1-status">R1</th> </tr> 
              </thead>
              <tbody>
                <tr id="R1-warnings" class="warnings">
                  <td id="R1-critical">0</td>
                  <td id="R1-major">0</td>
                  <td id="R1-minor">0</td>
                  <td id="R1-warning">0</td>
                  <td id="R1-normal">0</td>
                </tr>
              </tbody>
            </table>
          </div>
          <div class="span3">
            <table class="table table-bordered table-condensed summary" id="FlexibleContent" data-label="Flexible Content">
              <thead>
                <tr> <th colspan="6" id="FlexibleContent-status">Flexible Content</th> </tr> 
              </thead>
              <tbody>
                <tr id="FlexibleContent-warnings" class="warnings">
                  <td id="FlexibleContent-critical">0</td>
                  <td id="FlexibleContent-major">0</td>
                  <td id="FlexibleContent-minor">0</td>
                  <td id="FlexibleContent-warning">0</td>
                  <td id="FlexibleContent-normal">0</td>
                </tr>
              </tbody>
            </table>
          </div>
          <div class="span3">
            <table class="table table-bordered table-condensed summary" id="Soulmates" data-label="Soulmates">
              <thead>
                <tr> <th colspan="6" id="Soulmates-status">Soulmates</th> </tr> 
              </thead>
              <tbody>
                <tr id="Soulmates-warnings" class="warnings">
                  <td id="Soulmates-critical">0</td>
                  <td id="Soulmates-major">0</td>
                  <td id="Soulmates-minor">0</td>
                  <td id="Soulmates-warning">0</td>
                  <td id="Soulmates-normal">0</td>
                </tr>
              </tbody>
            </table>
          </div>
          <div class="span3">
            <table class="table table-bordered table-condensed summary" id="SharedSvcs" data-label="Shared Services">
              <thead>
                <tr> <th colspan="6" id="SharedSvcs-status">Shared Services</th> </tr> 
              </thead>
              <tbody>
                <tr id="SharedSvcs-warnings" class="warnings">
                  <td id="SharedSvcs-critical">0</td>
                  <td id="SharedSvcs-major">0</td>
                  <td id="SharedSvcs-minor">0</td>
                  <td id="SharedSvcs-warning">0</td>
                  <td id="SharedSvcs-normal">0</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
        <div class="row show-grid">
          <div class="span3">
            <table class="table table-bordered table-condensed summary" id="MicroApp" data-label="MicroApp">
              <thead>
                <tr> <th colspan="6" id="MicroApp-status">Micro App</th> </tr> 
              </thead>
              <tbody>
                <tr id="MicroApp-warnings" class="warnings">
                  <td id="MicroApp-critical">0</td>
                  <td id="MicroApp-major">0</td>
                  <td id="MicroApp-minor">0</td>
                  <td id="MicroApp-warning">0</td>
                  <td id="MicroApp-normal">0</td>
                </tr>
              </tbody>
            </table>
          </div>
          <div class="span3">
            <table class="table table-bordered table-condensed summary" id="Mutualisation" data-label="Mutualisation">
              <thead>
                <tr> <th colspan="6" id="Mutualisation-status">Mutualisation</th> </tr> 
              </thead>
              <tbody>
                <tr id="Mutualisation-warnings" class="warnings">
                  <td id="Mutualisation-critical">0</td>
                  <td id="Mutualisation-major">0</td>
                  <td id="Mutualisation-minor">0</td>
                  <td id="Mutualisation-warning">0</td>
                  <td id="Mutualisation-normal">0</td>
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
              Stage - <span id="alert-details-caption">R2</span> alert details
            </caption>
            <thead>
              <tr> <th></th><th>Severity</th><th>Status</th><th>Last Receive Time</th><th>Dupl. Count</th><th>Env.</th><th>Service</th><th>Cluster</th><th>Resource</th><th>Event</th><th>Value</th><th>Text</th></tr>
            </thead>
            <tbody id="R2-alerts" class="serviceAlerts">
            </tbody>
            <tbody id="Discussion-alerts" class="serviceAlerts initially-hidden">
            </tbody>
            <tbody id="ContentAPI-alerts" class="serviceAlerts initially-hidden">
            </tbody>
            <tbody id="Identity-alerts" class="serviceAlerts initially-hidden">
            </tbody>
            <tbody id="R1-alerts" class="serviceAlerts initially-hidden">
            </tbody>
            <tbody id="FlexibleContent-alerts" class="serviceAlerts initially-hidden">
            </tbody>
            <tbody id="Soulmates-alerts" class="serviceAlerts initially-hidden">
            </tbody>
            <tbody id="SharedSvcs-alerts" class="serviceAlerts initially-hidden">
            </tbody>
            <tbody id="MicroApp-alerts" class="serviceAlerts initially-hidden">
            </tbody>
            <tbody id="Mutualisation-alerts" class="serviceAlerts initially-hidden">
            </tbody>
            <tbody id="EC2-alerts" class="serviceAlerts initially-hidden">
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

        var env = "STAGE";
        var statusfilter = 'environment='+env+'&status=OPEN|ACK|CLOSED';
        var services = { 'R2':              statusfilter+'&service=R2',
                         'Discussion':      statusfilter+'&service=Discussion',
                         'ContentAPI':      statusfilter+'&service=ContentAPI',
                         'Identity':        statusfilter+'&service=Identity',
                         'R1':              statusfilter+'&service=R1',
                         'FlexibleContent': statusfilter+'&service=FlexibleContent',
                         'Soulmates':       statusfilter+'&service=Soulmates',
                         'SharedSvcs':      statusfilter+'&service=SharedSvcs',
                         'MicroApp':        statusfilter+'&service=MicroApp',
                         'Mutualisation':   statusfilter+'&service=Mutualisation',
                         'EC2':             statusfilter+'&service=EC2',
                         'Network':         statusfilter+'&service=Network' };

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
