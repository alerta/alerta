<?php
  $env = "";
  $svc = "";
  $grp = "";
  $res = "";

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
  if (isset($_GET['resource'])) {
      $res = $_GET['resource'];
      $tag_arr[] = $res;
      $_GET['label'] = $res;
  }
  $tag = implode('-', $tag_arr);
  $tag = preg_replace('/\./', '', $tag);
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
    <link href="css/custom.css" rel="stylesheet">
  </head>

  <body>
    <div class="container">
      <div align="right">
        <select id="from-date-select" class="btn" name="last" onchange="updateFromDate(this.value)">
          <option value="0">All alerts</option>
          <option value="120">Last 2 minutes</option>
          <option value="300">Last 5 minutes</option>
          <option value="600">Last 10 minutes</option>
          <option value="1800">Last 30 minutes</option>
          <option value="3600">Last 1 hour</option>
        </select>
        <button class="btn" id="toggle-ACK" class="toggle-ACK"><span><i class="icon-minus"></i> Hide</span><span class="initially-hidden"><i class="icon-plus"></i> Show</span> Acknowledged</button>
        <button class="btn" id="toggle-NORMAL" class="toggle-NORMAL"><span><i class="icon-minus"></i> Hide</span><span class="initially-hidden"><i class="icon-plus"></i> Show</span> Normals</button>
        <button id="refresh-all" class="console-button btn"><i class="icon-refresh"></i> Refresh Now</button>
      </div>

      <!-- Alert Details -->
      <div class="row show-grid">
        <div class="span12">
          <table class="table table-bordered table-condensed" id="alert-details">
            <caption class="alerts-caption">
              Production - <span id="alert-details-caption"><?php echo $label; ?></span> alert details
            </caption>
            <thead>
              <tr> <th></th><th>Severity</th><th>Status</th><th>Last Receive Time</th><th>Dupl. Count</th><th>Resource</th><th>Event</th><th>Value</th><th>Text</th></tr>
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

        var services = { '<?php echo $tag; ?>': 'sort-by=lastReceiveTime<?php if ($env != "") echo "&environment=".$env; ?><?php if ($svc != "") echo "&service=".$svc; ?><?php if ($grp != "") echo "&group=".$grp; ?><?php if ($id != "") echo "&id=".$id; ?><?php if ($res != "") echo "&resource=".$res; ?>' };
        loadAlerts(services, true);

        $('#refresh-all').click(function() {
          loadAlerts(services, false)
        });
      });
    </script>
    
  </body>
</html>
