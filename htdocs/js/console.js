// Fill-in Alert Details Template
var logger = 0,
    timer;

function loadAlerts(services, refresh) {
  var delayer = 0;
  $.each(services, function(service, filter) {
    setTimeout(function() { 
      getAlerts(service, filter, refresh);
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
          case 'DEBUG':    label='label-inverse'; break;
          case 'UNKNOWN':  label=''; break;
          default:         label='label-success'; 
        }
        return('<span class="label '+label+'">' + severity + '</span>');
}

function date2str(datetime) {
        var d = new Date(datetime);
        return d.toLocaleString();
}

// Update Alert Summaries
function getAlerts(service, filter, refresh) {

  $('#' + service +' th').addClass('loader');

  $.getJSON('http://'+ document.domain + '/alerta/api/v1/alerts?callback=?&sort-by=lastReceiveTime&' + filter, function(data) {

    $.each(data.response.alerts, function(key, val) {

      var sev_id = '#' + service;

      val.severityCounts.normal += val.severityCounts.inform;

      $.each(val.severityCounts, function(sev, count) {
        $(sev_id + "-" + sev).text(count);

        switch (count) {
          case 0: $(sev_id + "-" + sev).removeClass(sev).addClass('zero'); break;
          default: $(sev_id + "-" + sev).addClass(sev).removeClass('zero');
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
                          '<tr><td><b>Event</b></td><td>' + hist.event + '</td></tr>' +
                          '<tr><td><b>Severity</b></td><td>' + sev2label(hist.severity) + '</td></tr>' +
                          '<tr><td><b>Alert ID</b></td><td>' + hist.id + '</td></tr>' +
                          '<tr><td><b>Create time</b></td><td>' + date2str(hist.createTime) + '</td></tr>' +
                          '<tr><td><b>Receive time</b></td><td>' + date2str(hist.receiveTime) + '</td></tr>' +
                          '<tr><td><b>Text</b></td><td>' + hist.text + '</td></tr>' +
                          '<tr><td><b>Value</b></td><td>' + hist.value + '</td></tr>' +
                          '</table>' +
                        '';
          });
          historydata += '</td>'
        }

        if (ad.tags) {
          tagsdata += '';
          $.each (ad.tags, function(y, tag) {
            tagsdata += '<span class="label">' + tag + '</span> ';
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

        var alertstatus = '';
        if (ad.status == 'INACTIVE') {
          ad.text = '[inactive] ' + ad.text;
          alertstatus = 'INACTIVE';
        }

        rows += '<tr class="' + service + ' latest ' + ad.severity + ' ' + alertstatus + '">' +
                  '<td class="ad-more"><a id="' + service + 'details' + i + '" class="show-details">' +
                    '<span class="show-d"><i class="icon-chevron-up icon-chevron-down"></i></span></a></td>' +
                  '<td class="ad-sev-td">' + sev2label(ad.severity) + '</td>' +
                  '<td>'+ date2str(ad.lastReceiveTime) + '</td>' +
                  '<td>' + ad.duplicateCount + '</td>' +
                  '<td>' + ad.resource + '</td>' +
                  '<td>' + ad.event + '</td>' +
                  '<td>' + ad.value + '</td>' +
                  '<td class="alert-text">' + ad.text +
                    '<a id="' + ad.id + '" class="delete-alert" rel="tooltip" title="Delete Alert"><i class="icon-trash"></i></a>';
        if (ad.status != 'INACTIVE') {
          rows +=     '<a id="' + ad.id + '" class="inactive-alert" rel="tooltip" title="Make Inactive"><i class="icon-volume-off"></i></a>';
        }
        rows +=  '</td>' +
                '</tr>' +
                '<tr id="' + service + 'details' + i +'data" class="initially-hidden">' +
                  '<td colspan="10" class="alert-more"><table class="table table-bordered table-condensed alert-more-table">' +
                     '<tr><td>' + 
                        '<table class="table table-condensed table-striped">' +
                        '<tr><td><b>Alert ID</b></td><td>' + ad.id +
                          ' <a href="/alerta/details.php?id=' + ad.id + '" target="_blank"><i class="icon-share"></i></a></td></tr>' +
                        '<tr><td><b>Last Receive Alert ID</b></td><td>' + ad.lastReceiveId + '</td></tr>' +
                        '<tr><td><b>Create Time</b></td><td>' + date2str(ad.createTime) + '</td></tr>' +
                        '<tr><td><b>Receive Time</b></td><td>' + date2str(ad.receiveTime) + '</td></tr>' +
                        '<tr><td><b>Last Receive Time</b></td><td>' + date2str(ad.lastReceiveTime) + '</td></tr>' +
                        '<tr><td><b>Resource</b></td><td>' + ad.resource + '</td></tr>' +
                        '<tr><td><b>Environment</b></td><td>' + ad.environment + '</td></tr>' +
                        '<tr><td><b>Service</b></td><td>' + ad.service + '</td></tr>' +
                        '<tr><td><b>Event</b></td><td>' + ad.event + '</td></tr>' +
                        '<tr><td><b>Group</b></td><td>' + ad.group + '</td></tr>' +
                        '<tr><td><b>State</b></td><td>' + sev2label(ad.previousSeverity) + ' -> ' + sev2label(ad.severity) + '</td></tr>' +
                        '<tr><td><b>Value</b></td><td>' + ad.value + '</td></tr>' +
                        '<tr><td><b>Text</b></td><td>' + ad.text + '</td></tr>' +
                        '<tr><td><b>Threshold Info</b></td><td>' + ad.thresholdInfo + '</td></tr>' +
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
      timer = setTimeout(function() { getAlerts(service, filter, refresh); }, 120000);
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

    $('#toggle-INACTIVE').click(function() {
      $('#alert-details').toggleClass('actives');
      $('.open-details').click();
      $(this).find('span').toggle();
    });

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
      if (confirm('IMPORTANT: Deleting this alert is a permanent operation that will '
                + 'remove the alert from all user consoles.\n\n'
                + 'Cancel to return to the console or OK to delete.')) {
        /* $.ajax({
          type: 'DELETE',
          url: 'http://' + document.domain + '/alerta/api/v1/alerts/alert/' + this.id,
        }); */
        $.ajax({
          type: 'POST',
          url: 'http://' + document.domain + '/alerta/api/v1/alerts/alert/' + this.id,
          data: { _method: 'delete' }
        });
        $(this).parent().parent().next().remove(); // delete drop-down
        $(this).parent().parent().remove();  // delete alert
      }
    });

    $('tbody').on('click', '.inactive-alert', function() {
      if (confirm('IMPORTANT: Making this alert inactive prevents any future updates '
                + 'of this alert from triggering external notifications.\n\n'
                + 'Cancel to return to the console or OK to make inactive.')) {
        $.ajax({
          type: 'PUT',
          url: 'http://' + document.domain + '/alerta/api/v1/alerts/alert/' + this.id,
          data: { status: 'INACTIVE' }
        });
        $(this).parent().prepend('[inactive] ');
      }
    });
});
