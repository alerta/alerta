<?php
  $env = $_GET['environment'];
  $svc = $_GET['service'];
  $tag = $env."-".$svc;
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
       <table class="table table-bordered table-condensed summary" id="<?php echo $tag; ?>" data-label="<?php echo $tag; ?>">
         <thead>
           <tr> <th colspan="6" id="<?php echo $tag; ?>-status"><?php echo $env." ".$svc; ?></th> </tr>
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
     </div>
   </div>
   <script src="js/jquery-1.7.1.min.js"></script>
   <script src="js/bootstrap.js"></script>
   <script src="js/console.js"></script>
   <script>
     $(document).ready(function() {
       var services = { '<?php echo $tag; ?>': 'environment=<?php echo $env; ?>&service=<?php echo $svc; ?>' };
       loadAlerts(services, true);
     });
   </script>
 </body>
</html>
