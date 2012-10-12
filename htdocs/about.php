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
      <div class="row show-grid">
        <div class="span12">
        <strong>Registered Components</strong>
        <table class="table table-bordered table-condensed" id="Heartbeats">
          <thead>
            <tr><th>Origin</th><th>Version</th><th>Heartbeat Sent</th><th>Time Since Received</th></tr>
          </thead>
          <tbody id="heartbeat-info">
            <tr><td>...</td><td>...</td><td>...</td><td>...</td></tr>
          </tbody>
        </table>

        </div> <!-- end span12 -->
      </div> <!-- end row -->
    </div> <!-- end container -->

  <?php require($DOCUMENT_ROOT . "includes/scripts.php"); ?>

    <script>
      $(document).ready(function() {

        getHeartbeats(true);
      });
    </script>

  </body>
</html>
