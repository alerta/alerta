// Fill-in Alert Details Template
var logger = 0,
    timer;

function loadAlerts(services, env, refresh) {
  var delayer = 0;
  $.each(services, function(n, service) {
    setTimeout(function() { 
      getAlerts(service, env, refresh);
    }, delayer);
    delayer += 100;
  });
}

function sev2label(severity) {

        switch (severity) {
          case 'CRITICAL': label='label-important'; break;
          case 'MAJOR':    label='label-warning'; break;
          case 'MINOR':    label='label-minor'; break;
          case 'WARNING':  label='label-info'; break;
          default:         label='label-success'; 
        }
        return('<span class="label '+label+'">' + severity + '</span>');
}

function date2str(datetime) {
        var d = /^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2}):(\d{2})(?:\.\d*)?Z?$/.exec(datetime);
        return (d[4]+':'+d[5]+':'+d[6]+' '+d[3]+'/'+d[2]+'/'+d[1]);
}

// Update Alert Summaries
function getAlerts(service, env, refresh) {

  $('#' + service +' th').addClass('loader');

  $.getJSON('http://monitoring.gudev.gnl/alerta/api/v1/alerts?callback=?&sort-by=lastReceiveTime&environment=' + env + '&service=' + service, function(data) {

    $.each(data.response.alerts, function(key, val) {

      var sev_id = '#' + env + '-' + service;

      $.each(val.severityCounts, function(sev, count) {
        $(sev_id + "-" + sev).text(count);

        switch (count) {
          case 0: $(sev_id + "-" + sev).removeClass(sev).addClass('zero'); break;
          default: $(sev_id + "-" + sev).addClass(sev); 
        }

      });

        if (val.severityCounts.critical > 0) {
          scolor = 'red';
        } else if (val.severityCounts.major > 0) {
          scolor = 'orange';
        } else if (val.severityCounts.minor > 0) {
          scolor = 'yellow';
        } else if (val.severityCounts.warning > 0) {
          scolor = 'dodgerblue';
        } else {
          scolor = 'lime';
        }
      $(sev_id + "-status").css('background-color',scolor);

      var rows ='';
      $.each(val.alertDetails, function(i, ad) {  

        var historydata = '<td colspan="2"><b>History </b>', graphsdata = tagsdata = '';

        if (ad.history) {
          var reverseHistory = ad.history.reverse();
          $.each(reverseHistory, function (y, hist) {
            historydata += '<hr/>' +
                          '<table class="table table-condensed table-striped">' +
                          '<tr><td><b>Severity</b></td><td>' + sev2label(hist.severity) + '</td></tr>' +
                          '<tr><td><b>Alert ID</b></td><td>' + hist.id + '</td></tr>' +
                          '<tr><td><b>Create time</b></td><td>' + date2str(hist.createTime) + '</td></tr>' +
                          '<tr><td><b>Receive time</b></td><td>' + date2str(hist.receiveTime) + '</td></tr>' +
                          '<tr><td><b>Text</b></td><td>' + hist.text + '</td></tr>' +
                          '</table>' +
                        '';
          });
          historydata += '</td>'
        }

        if (ad.tags) {
          tagsdata += '';
          $.each (ad.tags, function(y, tag) {
            tagsdata += tag + ' ';
          });
        }

        if (ad.graphs) {
          graphsdata += '';
          $.each (ad.graphs, function(y, graph) {
            graphsdata += '<a href="' + graph + '" target="_blank">Graph ' + y + '</a> ';
          });
          graphsdata += '</ul>';
        }

        switch (ad.severity) {
          case 'CRITICAL': label='label-important'; break;
          case 'MAJOR': label='label-warning'; break;
          case 'MINOR': label='label-warning'; break;
          case 'WARNING': label='label-info'; break;
          default: label='label-success';
        }

        var d = /^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2}):(\d{2})(?:\.\d*)?Z?$/.exec(ad.lastReceiveTime);

        rows += '<tr class="' + service + ' latest ' + ad.severity + '">' +
                  '<td class="ad-more"><a id="' + service + 'details' + i + '" class="show-details"><span class="show-d"><i class="icon-chevron-up icon-chevron-down"></i></span></a></td>' +
                  '<td class="ad-sev-td">' + sev2label(ad.severity) + '</td>' +
                  '<td>' + d[4]+':'+d[5]+':'+d[6]+' '+d[3]+'/'+d[2]+'/'+d[1] + '</td>' +
                  '<td>' + ad.duplicateCount + '</td>' +
                  '<td>' + ad.source + '</td>' +
                  '<td>' + ad.event + '</td>' +
                  '<td>' + ad.value + '</td>' +
                  '<td class="alert-text">' + ad.text + '<a id="' + ad.lastReceiveId + '" class="delete-alert" rel="tooltip" title="Delete Alert"><i class="icon-trash"></i></a></td>' +
                '</tr>' +
                '<tr id="' + service + 'details' + i +'data" class="initially-hidden">' +
                  '<td colspan="10" class="alert-more"><table class="table table-bordered table-condensed alert-more-table">' +
                     '<tr><td>' + 
                        '<table class="table table-condensed table-striped">' +
                        '<tr><td><b>Alert ID</b></td><td>' + ad.lastReceiveId + '</td></tr>' +
                        '<tr><td><b>Create Time</b></td><td>' + date2str(ad.createTime) + '</td></tr>' +
                        '<tr><td><b>Receive Time</b></td><td>' + date2str(ad.receiveTime) + '</td></tr>' +
                        '<tr><td><b>Last Receive Time</b></td><td>' + date2str(ad.lastReceiveTime) + '</td></tr>' +
                        '<tr><td><b>Source</b></td><td>' + ad.source + '</td></tr>' +
                        '<tr><td><b>Environment</b></td><td>' + ad.environment + '</td></tr>' +
                        '<tr><td><b>Service</b></td><td>' + ad.service + '</td></tr>' +
                        '<tr><td><b>Event</b></td><td>' + ad.event + '</td></tr>' +
                        '<tr><td><b>Group</b></td><td>' + ad.group + '</td></tr>' +
                        '<tr><td><b>Value</b></td><td>' + ad.value + '</td></tr>' +
                        '<tr><td><b>State</b></td><td>' + sev2label(ad.previousSeverity) + ' -> ' + sev2label(ad.severity) + '</td></tr>' +
                        '<tr><td><b>Text</b></td><td>' + ad.text + '</td></tr>' +
                        '<tr><td><b>Alert Rule</b></td><td>' + ad.alertRule + '</td></tr>' +
                        '<tr><td><b>Type</b></td><td>' + ad.type + '</td></tr>' +
                        '<tr><td><b>Repeat</b></td><td>' + ad.repeat + '</td></tr>' +
                        '<tr><td><b>Duplicate Count</b></td><td>' + ad.duplicateCount + '</td></tr>' +
                        '<tr><td><b>Summary</b> </td><td>' + ad.summary + '</td></tr>' +
                        '<tr><td><b>Origin</b></td><td>' + ad.origin + '</td></tr>' +
                        '<tr><td><b>Tags</b></td><td>' + tagsdata + '</td></tr>' +
                        '<tr><td><b>Graphs</b></td><td>' + graphsdata + '</td></tr>' +
                        '<tr><td><a class="btn" href="' + ad.moreInfo + '" target="_blank">More Info</td></tr>' +
                        '</table>' +
                      '</td>' +
                    historydata +
                  '</tr></table></td>' +
                '</tr>';

      });

      $('#' + service + '-alerts').html(rows);
      $('#' + service + ' th').removeClass('loader');

    });

    if (refresh) {
      timer = setTimeout(function() { getAlerts(service, env, refresh); }, 120000);
    }
  });
};

//listeners
$(document).ready(function() {
    $('.summary').click(function() {
      $('.serviceAlerts').hide();
      $('#' + this.id + '-alerts').fadeIn();
      $('#alert-details-caption').text($(this).attr('data-label'));
    });

    $('a[rel=tooltip]').tooltip();

    $('#toggle-NORMAL').click(function() {
      $('#alert-details').toggleClass('priority');
      $('.open-details').click();
      $(this).find('span').toggle();
    });

    $('tbody').on('click', '.show-details', function(e) {
      $('#' + this.id + 'data').toggle();
      $(this).toggleClass('open-details');
      $(this).find('i').toggleClass('icon-chevron-down');
      e.preventDefault();
    });

    $('tbody').on('click', '.delete-alert', function() {
      /* $.ajax({
        type: 'DELETE',
        url: 'http://devmonsvr01.gudev.gnl/alerta/api/v1/alerts/alert/' + this.id,
      }); */
      $.ajax({
        type: 'POST',
        url: 'http://monitoring.gudev.gnl/alerta/api/v1/alerts/alert/' + this.id,
        data: { _method: 'delete' }
      });
      $(this).parent().parent().next().remove(); // delete drop-down
      $(this).parent().parent().remove();  // delete alert
    });
});
