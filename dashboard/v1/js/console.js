// Fill-in Alert Details Template
var logger = 0,
    fromDate = "",
    limit = "",
    timer;

var hb_threshold = 300; // 5 minutes

var api_server = document.domain + ':5000';

function updateLimit(lim) {
    if (lim > 0) {
        limit = '&limit=' + lim
    } else {
        limit = '';
    }
    $('#refresh-all').trigger('click');
}

function updateFromDate(seconds) {
    if (seconds > 0) {
        fromDate = '&from-date=' + new Date(new Date() - seconds * 1000).toISOString();
    } else {
        fromDate = '';
    }
    $('#refresh-all').trigger('click');
}

function loadStatus(statusfilter, refresh) {
    setTimeout(function () {
        getStatus(statusfilter, refresh);
    }, 0);
}

function loadAlerts(services, refresh) {
    var delayer = 0;
    $.each(services, function (service, filter) {
        setTimeout(function () {
            getAlerts(service, filter, refresh);
        }, delayer);
        delayer += 100;
    });
}

CRITICAL = 'Critical';
MAJOR = 'Major';
MINOR = 'Minor';
WARNING = 'Warning';
NORMAL = 'Normal';
CLEAR = 'Clear';
INFORM = 'Informational';
DEBUG = 'Debug';
AUTH = 'Security';
UNKNOWN = 'Unknown';
INDETERMINATE = 'Indeterminate';

ALL = [CRITICAL, MAJOR, MINOR, WARNING, NORMAL, CLEAR, INFORM, DEBUG, AUTH, UNKNOWN, INDETERMINATE];


function sev2label(severity) {

    var label;

    switch (severity) {
        case CRITICAL:
            label = 'label-important';
            break;
        case MAJOR:
            label = 'label-warning';
            break;
        case MINOR:
            label = 'label-minor';
            break;
        case WARNING:
            label = 'label-info';
            break;
        case DEBUG:
            label = 'label-inverse';
            break;
        case UNKNOWN:
            label = '';
            break;
        default:
            label = 'label-success';
    }
    return('<span class="label ' + label + '">' + severity + '</span>');
}

function date2iso8601(datetime) {
    var d = new Date(datetime);
    return d.getFullYear() + '/' + (d.getMonth() + 1) + '/' + d.getDate() + ' ' + d.toTimeString().split(' ')[0]
}
function date2str(datetime) {
    var d = new Date(datetime);
    return d.toLocaleString();
}

// Update Register Components
function heartbeatAlerts() {

    $.getJSON('http://' + api_server + '/alerta/management/healthcheck?callback=?', function (data) {

        var hbalerts = '';
        $.each(data.heartbeats, function (i, hb) {

            var diff = (new Date().getTime() - new Date(hb.receiveTime).getTime()) / 1000;
            var mins = Math.floor(diff / 60);
            var secs = Math.floor(diff % 60);

            var since = '';
            if (mins > 0) {
                since = mins + ' minutes ' + secs + ' seconds';
            } else {
                since = secs + ' seconds';
            }

            if (diff > hb_threshold) {
                hbalerts += '<div class="alert alert-error">' +
                    '<button class="close" data-dismiss="alert" onclick="">&times;</button>' +
                    '<strong>Important!</strong> ' + hb.origin + ' has not sent a heartbeat for ' + since +
                    '</div>';
            }
        });
        $('#heartbeat-alerts').html(hbalerts);
    });
};

function getHeartbeats(refresh) {

    $.getJSON('http://' + api_server + '/alerta/management/healthcheck?callback=?', function (data) {

        var rows = '';
        $.each(data.heartbeats, function (i, hb) {

            var diff = (new Date().getTime() - new Date(hb.receiveTime).getTime()) / 1000;
            var mins = Math.floor(diff / 60);
            var secs = Math.floor(diff % 60);

            var since = '';
            if (mins > 0) {
                since = mins + ' minutes ' + secs + ' seconds';
            } else {
                since = secs + ' seconds';
            }

            rows += '<tr class="">' +
                '<td>' + hb.origin + '</td>' +
                '<td>' + hb.version + '</td>' +
                '<td>' + date2str(hb.createTime) + '</td>' +
                '<td>' + since + '</td>' +
                '</tr>';
        });
        $('#heartbeat-info').html(rows);

        if (refresh) {
            timer = setTimeout(function () {
                getHeartbeats(refresh);
            }, 120000);
        }
    });
};

// Update Alert Status
function getStatus(statusfilter, refresh) {

    $.getJSON('http://' + api_server + '/alerta/api/v2/alerts?callback=?&hide-alert-details=true&hide-alert-repeats=NORMAL&' + statusfilter + limit + fromDate, function (data) {

        if (data.response.warning) {
            $('#warning-text').text(data.response.warning);
            $('#console-alert').toggle();
        }

        $.each(data.response.alerts.statusCounts, function (stat, count) {
            $("#alert-" + stat).text(count);
        });
        if (refresh) {
            timer = setTimeout(function () {
                getStatus(statusfilter, refresh);
            }, 120000);
        }
    });
}

// Update Alert Summaries
function getAlerts(service, filter, refresh) {

    $('#' + service + ' th').addClass('loader');

    $.getJSON('http://' + api_server + '/alerta/api/v2/alerts?callback=?&hide-alert-repeats=NORMAL&sort-by=lastReceiveTime&' + filter + limit + fromDate, function (data) {

        var sev_id = '#' + service;

        data.response.alerts.severityCounts.normal += data.response.alerts.severityCounts.inform;

        $.each(data.response.alerts.severityCounts, function (sev, count) {
            $(sev_id + "-" + sev).text(count);

            switch (count) {
                case 0:
                    $(sev_id + "-" + sev).removeClass(sev).addClass('zero');
                    break;
                default:
                    $(sev_id + "-" + sev).addClass(sev).removeClass('zero');
            }

        });

        if (data.response.alerts.severityCounts.critical > 0) {
            scolor = 'red';
        } else if (data.response.alerts.severityCounts.major > 0) {
            scolor = 'orange';
        } else if (data.response.alerts.severityCounts.minor > 0) {
            scolor = 'yellow';
        } else if (data.response.alerts.severityCounts.warning > 0) {
            scolor = 'dodgerblue';
        } else {
            scolor = '#00CC00';
        }
        $(sev_id + "-status").css('background-color', scolor);

        var rows = '';
        $.each(data.response.alerts.alertDetails, function (i, ad) {

            var historydata = '<td colspan="2"><b>History </b>', graphsdata = tagsdata = '';

            if (ad.history) {
                var reverseHistory = ad.history.reverse();
                $.each(reverseHistory, function (y, hist) {
                    if (hist.event) {
                        historydata += '<hr/>' +
                            '<table class="table table-condensed table-striped">' +
                            '<tr><td><b>Event</b></td><td>' + hist.event + '</td></tr>' +
                            '<tr><td><b>Severity</b></td><td>' + sev2label(hist.severity) + '</td></tr>' +
                            '<tr><td><b>Alert ID</b></td><td>' + hist.id + '</td></tr>' +
                            '<tr><td><b>Create Time</b></td><td>' + date2str(hist.createTime) + '</td></tr>' +
                            '<tr><td><b>Receive Time</b></td><td>' + date2str(hist.receiveTime) + '</td></tr>' +
                            '<tr><td><b>Text</b></td><td>' + hist.text + '</td></tr>' +
                            '<tr><td><b>Value</b></td><td>' + hist.value + '</td></tr>' +
                            '</table>' +
                            '';
                    }
                    if (hist.status) {
                        historydata += '<hr/>' +
                            '<table class="table table-condensed table-striped">' +
                            '<tr><td><b>Status</b></td><td><span class="label">' + hist.status + '</span></td></tr>' +
                            '<tr><td><b>Update Time</b></td><td>' + date2str(hist.updateTime) + '</td></tr>' +
                            '</table>' +
                            '';
                    }
                });
                historydata += '</td>'
            }

            var cluster = '';
            if (ad.tags) {
                tagsdata += '';
                $.each(ad.tags, function (y, tag) {
                    tagsdata += '<span class="label">' + tag + '</span> ';
                    var t = tag.split(':')
                    if (t[0] == 'cluster') {
                        cluster = t[1];
                    }
                });
            }

            if (ad.graphs) {
                graphsdata += '';
                $.each(ad.graphs, function (y, graph) {
                    graphsdata += '<a href="' + graph + '" target="_blank">Graph ' + y + '</a> ';
                });
                graphsdata += '</ul>';
            }

            switch (ad.severity) {
                case 'CRITICAL':
                    label = 'label-important';
                    break;
                case 'MAJOR':
                    label = 'label-warning';
                    break;
                case 'MINOR':
                    label = 'label-warning';
                    break;
                case 'WARNING':
                    label = 'label-info';
                    break;
                default:
                    label = 'label-success';
            }

            rows += '<tr class="' + service + ' latest ' + ad.severity + ' ' + ad.status + '">' +
                '<td class="ad-more"><a id="' + service + 'details' + i + '" class="show-details">' +
                '<span class="show-d"><i class="icon-chevron-up icon-chevron-down"></i></span></a></td>' +
                '<td class="ad-sev-td">' + sev2label(ad.severity) + '</td>' +
                '<td class="ad-stat-td"><span class="label">' + ad.status + '</span></td>' +
                '<td>' + date2iso8601(ad.lastReceiveTime) + '</td>' +
                '<td>' + ad.duplicateCount + '</td>' +
                '<td>' + ad.environment + '</td>' +
                '<td>' + ad.service + '</td>' +
                '<td>' + cluster + '</td>' +
                '<td>' + ad.resource + '</td>' +
                '<td>' + ad.event + '</td>' +
                '<td>' + ad.value + '</td>' +
                '<td class="alert-text">' + ad.text;
            if (ad.status == 'OPEN') {
                rows += '<a id="' + ad.id + '" class="ack-alert" rel="tooltip" title="Acknowledge"><i class="icon-star-empty"></i></a>';
            }
            if (ad.status == 'ACK') {
                rows += '<a id="' + ad.id + '" class="unack-alert" rel="tooltip" title="Unacknowledge"><i class="icon-star"></i></a>';
            }
            rows += '<a id="' + ad.id + '" href="mailto:?subject=' + ad.summary + '&body=' + ad.text + '%0D%0A%0D%0ASee http://' + api_server + '/alerta/details.php?id=' + ad.id + '" class="email-alert" rel="tooltip" title="Email Alert" target="_blank"><i class="icon-envelope"></i></a>';
            rows += '<a id="' + ad.id + '" class="tag-alert" rel="tooltip" title="Tag Alert"><i class="icon-tags"></i></a>';
            rows += '<a id="' + ad.id + '" class="delete-alert" rel="tooltip" title="Delete Alert"><i class="icon-trash"></i></a>';
            rows += '</td>' +
                '</tr>' +
                '<tr id="' + service + 'details' + i + 'data" class="initially-hidden">' +
                '<td colspan="12" class="alert-more"><table class="table table-bordered table-condensed alert-more-table">' +
                '<tr><td>' +
                '<table class="table table-condensed table-striped">' +
                '<tr><td><b>Alert ID</b></td><td>' + ad.id +
                ' <a href="/alerta/details.php?id=' + ad.id + '" target="_blank"><i class="icon-share"></i></a></td></tr>' +
                '<tr><td><b>Last Receive Alert ID</b></td><td>' + ad.lastReceiveId + '</td></tr>' +
                '<tr><td><b>Create Time</b></td><td>' + date2str(ad.createTime) + '</td></tr>' +
                '<tr><td><b>Receive Time</b></td><td>' + date2str(ad.receiveTime) + '</td></tr>' +
                '<tr><td><b>Last Receive Time</b></td><td>' + date2str(ad.lastReceiveTime) + '</td></tr>' +
                '<tr><td><b>Environment</b></td><td>' + ad.environment + '</td></tr>' +
                '<tr><td><b>Service</b></td><td>' + ad.service + '</td></tr>' +
                '<tr><td><b>Resource</b></td><td>' + ad.resource + '</td></tr>' +
                '<tr><td><b>Event</b></td><td>' + ad.event + '</td></tr>' +
                '<tr><td><b>Group</b></td><td>' + ad.group + '</td></tr>' +
                '<tr><td><b>Severity</b></td><td>' + sev2label(ad.previousSeverity) + ' -> ' + sev2label(ad.severity) + '</td></tr>' +
                '<tr><td><b>Status</b></td><td><span class="label">' + ad.status + '</span></td></tr>' +
                '<tr><td><b>Value</b></td><td>' + ad.value + '</td></tr>' +
                '<tr><td><b>Text</b></td><td>' + ad.text + '</td></tr>' +
                '<tr><td><b>Threshold Info</b></td><td>' + ad.thresholdInfo + '</td></tr>' +
                '<tr><td><b>Timeout</b></td><td>' + ad.timeout + ' seconds</td></tr>' +
                '<tr><td><b>Type</b></td><td>' + ad.type + '</td></tr>' +
                '<tr><td><b>Repeat</b></td><td>' + ad.repeat + '</td></tr>' +
                '<tr><td><b>Duplicate Count</b></td><td>' + ad.duplicateCount + '</td></tr>' +
                '<tr><td><b>Summary</b> </td><td>' + ad.summary + '</td></tr>' +
                '<tr><td><b>Origin</b></td><td>' + ad.origin + '</td></tr>' +
                '<tr><td><b>Tags</b></td><td>' + tagsdata + '</td></tr>' +
                '<tr><td><b>Graphs</b></td><td>' + graphsdata + '</td></tr>' +
                '<tr><td><b>More Info</b></td><td><a href="' + ad.moreInfo + '" target="_blank">' + ad.moreInfo + '</a></td></tr>' +
                '</table>' +
                '</td>' +
                historydata +
                '</tr></table></td>' +
                '</tr>';

        });

        $('#' + service + '-alerts').html(rows);
        $('#' + service + ' th').removeClass('loader');

        if (refresh) {
            timer = setTimeout(function () {
                getAlerts(service, filter, refresh);
            }, 120000);
        }
    });
};

//listeners
$(document).ready(function () {
    $('.summary').click(function () {
        $('.serviceAlerts').hide();
        $('#' + this.id + '-alerts').fadeIn();
        $('#alert-details-caption').text($(this).attr('data-label'));
    });

    $('a[rel=tooltip]').tooltip();

    $('#toggle-ACK').click(function () {
        $('#alert-details').toggleClass('acked');
        $('.open-details').click();
        $(this).find('span').toggle();
    });

    $('#toggle-NORMAL').click(function () {
        $('#alert-details').toggleClass('priority');
        $('.open-details').click();
        $(this).find('span').toggle();
    });

    $('tbody').on('click', '.show-details', function (e) {
        $('#' + this.id + 'data').toggle();
        $(this).toggleClass('open-details');
        $(this).find('i').toggleClass('icon-chevron-down');
        e.preventDefault();
    });

    $('tbody').on('click', '.delete-alert', function () {
        if (confirm('IMPORTANT: Deleting this alert is a permanent operation that will '
            + 'remove the alert from all user consoles.\n\n'
            + 'Cancel to return to the console or OK to delete.')) {
            /* $.ajax({
             type: 'DELETE',
             url: 'http://' + api_server + '/alerta/api/v2/alerts/alert/' + this.id,
             }); */
            $.ajax({
                type: 'POST',
                url: 'http://' + api_server + '/alerta/api/v2/alerts/alert/' + this.id,
                data: JSON.stringify({ _method: 'delete' })
            });
            $(this).parent().parent().next().remove(); // delete drop-down
            $(this).parent().parent().remove();  // delete alert
        }
    });

    $('tbody').on('click', '.ack-alert', function () {
        $.ajax({
            type: 'PUT',
            url: 'http://' + api_server + '/alerta/api/v2/alerts/alert/' + this.id,
            data: JSON.stringify({ status: 'ACK' })
        });
        $(this).parent().parent().find('.ad-stat-td').html('<span class="label">ACK</td>');
    });

    $('tbody').on('click', '.unack-alert', function () {
        $.ajax({
            type: 'PUT',
            url: 'http://' + api_server + '/alerta/api/v2/alerts/alert/' + this.id,
            data: JSON.stringify({ status: 'OPEN' })
        });
        $(this).parent().parent().find('.ad-stat-td').html('<span class="label">OPEN</td>');
    });

    $('tbody').on('click', '.tag-alert', function () {
        var tag = prompt("Enter tag eg. london, location:london, datacentre:location=london");
        if (tag != null && tag != "") {
            $.ajax({
                type: 'PUT',
                url: 'http://' + api_server + '/alerta/api/v2/alerts/alert/' + this.id + '/tag',
                data: JSON.stringify({ tags: tag })
            });
        }
    });

});
