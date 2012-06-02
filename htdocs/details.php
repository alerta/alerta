<?php
  if (isset($_GET['environment'])) {
      $env = $_GET['environment'];
      $tag_arr[] = $env;
  }
  if (isset($_GET['service'])) {
      $svc = $_GET['service'];
      $tag_arr[] = $svc;
  }
  if (isset($_GET['group'])) {
      $grp = $_GET['group'];
      $tag_arr[] = $grp;
  }
  if (isset($_GET['id'])) {
      $id = $_GET['id'];
      $tag_arr[] = $id;
      $_GET['label'] = $id;
  }
  $tag = implode('-', $tag_arr);
  if (isset($_GET['label']))
      $label = $_GET['label'];
  else
      $label = implode(' ', $tag_arr);
?>

<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <title>Alert Console - <?php echo $label; ?></title>

    <link href="css/bootstrap.css" rel="stylesheet">
    <link href="css/docs.css" rel="stylesheet">
    <link href="css/custom.css" rel="stylesheet">
  </head>

  <body>
    <div class="container">
      
      <!-- Alert Details -->
      <div class="row show-grid">
        <div class="span12">
          <table class="table table-bordered table-condensed" id="alert-details">
            <caption class="alerts-caption">
              Production - <span id="alert-details-caption"><?php echo $label; ?></span> alert details
            </caption>
            <thead>
              <tr> <th></th><th>Severity</th><th>Last Receive Time</th><th>Dupl. Count</th><th>Resource</th><th>Event</th><th>Value</th><th>Text</th></tr> 
            </thead>
            <tbody id="<?php echo $tag; ?>-alerts" class="serviceAlerts">
            </tbody>
          </table>

        </div>
      </div>
      <!-- end Alert Details -->

    </div> <!-- end container -->
    <script src="js/jquery-1.7.1.min.js"></script>
    <script src="js/bootstrap.js"></script>
    <script src="js/bootstrap-tooltip.js"></script>
    <script src="js/console.js"></script>

    <script>
      $(document).ready(function() {

        var services = { '<?php echo $tag; ?>': 'sort-by=lastReceiveTime<?php if ($env != "") echo "&environment=".$env; ?><?php if ($svc != "") echo "&service=".$svc; ?><?php if ($grp != "") echo "&group=".$grp; ?><?php if ($id != "") echo "&id=".$id; ?>' };
        loadAlerts(services, true);

        $('#refresh-all').click(function() {
          loadAlerts(services, false)
        });
      });
    </script>
    
  </body>
</html>
