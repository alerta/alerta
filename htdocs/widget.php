<?php
  $label = '';
  $tag = '';
  $query = '';

  foreach ($_GET as $key => $value) {
      if ($key != 'label') {
          $query_arr[] = $key . '=' . $value;
          $label_arr[] = $value;
      }
  }
  if (isset($_GET['label'])) {
      $label = $_GET['label'];
  } else {
      $label = implode(' ', $label_arr);
  }
  $query = implode('&', $query_arr);
  $tag = implode('-', $label_arr);
  $tag = preg_replace("/[^a-zA-Z-]/", "", $tag);
?>

<html lang="en">
 <head>
   <link href="css/bootstrap.css" rel="stylesheet">
   <link href="css/bootstrap-responsive.css" rel="stylesheet">
   <link href="css/custom.css" rel="stylesheet">
 </head>
 <body class="widget">
   <div class="row show-grid">
     <div class="span3">
       <a href="./details.php?<?php echo $query; ?><?php if ($label != "") echo "&label=".$label; ?>" target="_blank">
       <table class="table table-bordered table-condensed summary" id="<?php echo $tag; ?>" data-label="<?php echo $tag; ?>">
         <thead>
           <tr> <th colspan="6" id="<?php echo $tag; ?>-status"><?php echo $label; ?></th> </tr>
         </thead>
         <tbody>
           <tr id="<?php echo $tag; ?>-warnings" class="warnings">
             <td id="<?php echo $tag; ?>-critical">0</td>
             <td id="<?php echo $tag; ?>-major">0</td>
             <td id="<?php echo $tag; ?>-minor">0</td>
             <td id="<?php echo $tag; ?>-warning">0</td>
             <td id="<?php echo $tag; ?>-normal">0</td>
           </tr>
         </tbody>
       </table>
       </a>
     </div>
   </div>
   <script src="js/jquery-1.7.1.min.js"></script>
   <script src="js/bootstrap.js"></script>
   <script src="js/console.js"></script>
   <script>
     $(document).ready(function() {
       var services = { '<?php echo $tag; ?>': 'sort-by=lastReceiveTime&hide-alert-details=true&<?php echo $query; ?>' };
       loadAlerts(services, true);
     });
   </script>
 </body>
</html>
