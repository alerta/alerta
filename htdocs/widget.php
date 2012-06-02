<?php
  $query = "sort-by=lastReceiveTime";

  if (isset($_GET['environment'])) {
      $env = $_GET['environment'];
      $tag_arr[] = $env;
      $query = $query."&environment=".$env;
  }
  if (isset($_GET['service'])) {
      $svc = $_GET['service'];
      $tag_arr[] = $svc;
      $query = $query."&service=".$svc;
  }
  if (isset($_GET['group'])) {
      $grp = $_GET['group'];
      $tag_arr[] = $grp;
      $query = $query."&group=".$grp;
  }
  $tag = implode('-', $tag_arr);
  if (isset($_GET['label'])) {
      $label = $_GET['label'];
  } else {
      $label = implode(' ', $tag_arr);
  }
?>

<html lang="en">
 <head>
   <link href="css/bootstrap.css" rel="stylesheet">
   <link href="css/docs.css" rel="stylesheet">
   <link href="css/custom.css" rel="stylesheet">
 </head>
 <body>
   <div class="row show-grid">
     <div class="span3">
       <a href="./details.php?<?php echo $query; ?><?php if ($label !="") echo "&label=".$label; ?>" target="_blank">
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
       var services = { '<?php echo $tag; ?>': '<?php echo $query; ?>' };
       loadAlerts(services, true);
     });
   </script>
 </body>
</html>
