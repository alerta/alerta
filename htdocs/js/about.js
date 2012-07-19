
function date2str(datetime) {
        var d = new Date(datetime);
        return d.toLocaleString();
}

// Update Registered Components
function getHeartbeats(refresh) {

  $.getJSON('http://'+ document.domain + '/alerta/management/healthcheck?callback=?', function(data) {

      var rows ='';
      $.each(data.heartbeats, function(i, hb) {

        var diff = new Date().getTime() - new Date(hb.receiveTime).getTime();

        rows += '<tr class="">' +
                  '<td>' + hb.origin + '</td>' +
                  '<td>' + hb.version + '</td>' +
                  '<td>' + date2str(hb.createTime) + '</td>' +
                  '<td>' + Math.floor(diff / 1000) + ' seconds</td>' +
                '</tr>';
      });

      $('#Heartbeat-info').html(rows);

    if (refresh) {
      timer = setTimeout(function() { getHeartbeats(refresh); }, 120000);
    }
  });
};
