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
            <table class="table table-bordered table-condensed summary" id="R2R1" data-label="R2R1">
              <thead>
                <tr> <th colspan="6" id="R2R1-status">R2 &amp; R1</th> </tr> 
              </thead>
              <tbody>
                <tr id="R2R1-warnings" class="warnings">
                  <td id="R2R1-critical">0</td>
                  <td id="R2R1-major">0</td>
                  <td id="R2R1-minor">0</td>
                  <td id="R2R1-warning">0</td>
                  <td id="R2R1-normal">0</td>
                </tr>
              </tbody>
            </table>
          </div>
          <div class="span3">
            <table class="table table-bordered table-condensed summary" id="Frontend" data-label="Frontend">
              <thead>
                <tr> <th colspan="6" id="Frontend-status">Frontend</th> </tr> 
              </thead>
              <tbody>
                <tr id="Frontend-warnings" class="warnings">
                  <td id="Frontend-critical">0</td>
                  <td id="Frontend-major">0</td>
                  <td id="Frontend-minor">0</td>
                  <td id="Frontend-warning">0</td>
                  <td id="Frontend-normal">0</td>
                </tr>
              </tbody>
            </table>
          </div>
          <div class="span3">
            <table class="table table-bordered table-condensed summary" id="Mobile" data-label="Mobile">
              <thead>
                <tr> <th colspan="6" id="Mobile-status">Mobile</th> </tr> 
              </thead>
              <tbody>
                <tr id="Mobile-warnings" class="warnings">
                  <td id="Mobile-critical">0</td>
                  <td id="Mobile-major">0</td>
                  <td id="Mobile-minor">0</td>
                  <td id="Mobile-warning">0</td>
                  <td id="Mobile-normal">0</td>
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
            <table class="table table-bordered table-condensed summary" id="Network" data-label="Network Services">
              <thead>
                <tr> <th colspan="6" id="Network-status">Network Services</th> </tr> 
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
        <div class="row show-grid">
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
          <div class="span3">
            <table class="table table-bordered table-condensed summary" id="MicroApp" data-label="Micro App">
              <thead>
                <tr> <th colspan="6" id="MicroApp-status">Micro Apps</th> </tr> 
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
            <table class="table table-bordered table-condensed summary" id="Other" data-label="Other">
              <thead>
                <tr> <th colspan="6" id="Other-status">Other</th> </tr> 
              </thead>
              <tbody>
                <tr id="Other-warnings" class="warnings">
                  <td id="Other-critical">0</td>
                  <td id="Other-major">0</td>
                  <td id="Other-minor">0</td>
                  <td id="Other-warning">0</td>
                  <td id="Other-normal">0</td>
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
              Code - <span id="alert-details-caption">R2</span> alert details
            </caption>
            <thead>
              <tr> <th></th><th>Severity</th><th>Status</th><th>Last Receive Time</th><th>Dupl. Count</th><th>Env.</th><th>Service</th><th>Cluster</th><th>Resource</th><th>Event</th><th>Value</th><th>Text</th></tr>
            </thead>
            <tbody id="R2R1-alerts" class="serviceAlerts">
            </tbody>
            <tbody id="Frontend-alerts" class="serviceAlerts initially-hidden">
            </tbody>
            <tbody id="Mobile-alerts" class="serviceAlerts initially-hidden">
            </tbody>
            <tbody id="SharedSvcs-alerts" class="serviceAlerts initially-hidden">
            </tbody>
            <tbody id="Discussion-alerts" class="serviceAlerts initially-hidden">
            </tbody>
            <tbody id="FlexibleContent-alerts" class="serviceAlerts initially-hidden">
            </tbody>
            <tbody id="Soulmates-alerts" class="serviceAlerts initially-hidden">
            </tbody>
            <tbody id="Network-alerts" class="serviceAlerts initially-hidden">
            </tbody>
            <tbody id="ContentAPI-alerts" class="serviceAlerts initially-hidden">
            </tbody>
            <tbody id="Identity-alerts" class="serviceAlerts initially-hidden">
            </tbody>
            <tbody id="MicroApp-alerts" class="serviceAlerts initially-hidden">
            </tbody>
            <tbody id="Other-alerts" class="serviceAlerts initially-hidden">
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

        var envfilter = 'environment=CODE';
        var statusfilter = envfilter;
        var services = { 'R2R1':            envfilter+'&service=R2|R1',
                         'Frontend':        envfilter+'&service=Frontend',
                         'Mobile':          envfilter+'&service=Mobile',
                         'SharedSvcs':      envfilter+'&service=SharedSvcs',
                         'Discussion':      envfilter+'&service=Discussion',
                         'FlexibleContent': envfilter+'&service=FlexibleContent',
                         'Soulmates':       envfilter+'&service=Soulmates',
                         'Network':         envfilter+'&service=^Network',
                         'ContentAPI':      envfilter+'&service=ContentAPI',
                         'Identity':        envfilter+'&service=Identity',
                         'MicroApp':        envfilter+'&service=MicroApp',
                         'Other':           envfilter+'&service=Arts|Other'
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
