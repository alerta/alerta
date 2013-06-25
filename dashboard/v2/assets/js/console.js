
var API_HOST = document.domain + ':' + window.api_port;
var REFRESH_INTERVAL = 30; // seconds

var show_hb_alerts = true;
var lookup;
var gEnvFilter;
var filter = '';
var status = '&status=open';
var limit = '';
var from = '';
var timer;

var CRITICAL_SEV_CODE = 1;
var MAJOR_SEV_CODE = 2;
var MINOR_SEV_CODE = 3;
var WARNING_SEV_CODE = 4;
var INDETER_SEV_CODE = 5;
var CLEARED_SEV_CODE = 5;
var NORMAL_SEV_CODE = 5;
var INFORM_SEV_CODE = 6;
var DEBUG_SEV_CODE = 7;
var AUTH_SEV_CODE = 8;
var UNKNOWN_SEV_CODE = 9;

var CRITICAL = 'critical';
var MAJOR = 'major';
var MINOR = 'minor';
var WARNING = 'warning';
var INDETERMINATE = 'indeterminate';
var CLEARED = 'cleared';
var NORMAL = 'normal';
var INFORM = 'informational';
var DEBUG = 'debug';
var AUTH = 'security';
var UNKNOWN = 'unknown';

// var ALL = [CRITICAL, MAJOR, MINOR, WARNING, INDETERMINATE, CLEARED, NORMAL, INFORM, DEBUG, AUTH, UNKNOWN];

var SEVERITY_MAP = {
    'critical': 1,
    'major': 2,
    'minor': 3,
    'warning': 4,
    'indeterminate': 5,
    'cleared': 5,
    'normal': 5,
    'informational': 6,
    'debug': 7,
    'auth': 8,
    'unknown': 9
};

function sev2label(severity) {
    var label;
    switch (severity) {
        case CRITICAL:
            label = 'label-critical';
            break;
        case MAJOR:
            label = 'label-major';
            break;
        case MINOR:
            label = 'label-minor';
            break;
        case WARNING:
            label = 'label-warning';
            break;
        case NORMAL:
            label = 'label-normal';
            break;
        case DEBUG:
            label = 'label-inverse';
            break;
        default:
            label = '';
    }
    severity = severity.charAt(0).toUpperCase() + severity.slice(1).toLowerCase();

    return('<span class="label ' + label + '">' + severity + '</span>');
}

var OPEN = 'open';
var ACK = 'ack';
var CLOSED = 'closed';
var EXPIRED = 'expired';
var UNKNOWN = 'unknown';

// var ALL = [OPEN, ACK, CLOSED, EXPIRED, UNKNOWN];

function stat2label(status) {

    var label;

    switch (status) {
        case OPEN:
            label = 'label-open';
            break;
        case ACK:
            label = 'label-ack';
            break;
        case CLOSED:
            label = 'label-closed';
            break;
        case EXPIRED:
            label = 'label-expired';
            break;
        case UNKNOWN:
            label = 'label-unknown';
            break;
        default:
            label = '';
    }
    status = status.charAt(0).toUpperCase() + status.slice(1).toLowerCase();

    return('<span class="label ' + label + '">' + status + '</span>');
}

function date2iso8601(datetime) {
    var d = new Date(datetime);
    return d.getFullYear() + '/' + (d.getMonth() + 1) + '/' + d.getDate() + ' ' + d.toTimeString().split(' ')[0]
}

function date2str(datetime) {
    var d = new Date(datetime);
    return d.toLocaleString();
}

function heartbeatAlerts() {

    $.getJSON('http://' + API_HOST + '/alerta/api/v2/heartbeats?callback=?', function (data) {

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

            if (diff > hb.timeout * 4 && show_hb_alerts) {
                hbalerts += '<div class="alert alert-error">' +
                        '<a class="close" data-dismiss="alert" href="#">&times;</a>' +
                        '<strong>Important!</strong> ' + hb.origin + ' has not sent a heartbeat for ' + since +
                        '</div>';
            }
        });
        $('#heartbeat-alerts').html(hbalerts);
    });
};

function getHeartbeats(refresh) {

    $.getJSON('http://' + API_HOST + '/alerta/api/v2/heartbeats?callback=?', function (data) {

        var rows = '';
        $.each(data.heartbeats, function (i, hb) {

            var diff = (new Date().getTime() - new Date(hb.receiveTime).getTime()) / 1000;
            var mins = Math.floor(diff / 60);
            var secs = Math.floor(diff % 60);

            var latency = new Date(hb.receiveTime).getTime() - new Date(hb.createTime).getTime();

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
                    '<td>' + latency + ' ms' + '</td>' +
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

$('#heartbeat-alerts').bind('closed', function () {
  show_hb_alerts = false;
});

var Alerta = {
    highlightStatusIndicator: function(statusIndicator) {
        $(".status-indicator").addClass("status-indicator-inactive").removeClass("current-filter");
        statusIndicator.addClass("current-filter");
    },
    dropDownText: function(window) {
        var currentWidth = $(window).width();
        var dropDownLabels = {
            long: {
                "#from-date-select" : {
                    "0" : "All alerts",
                    "120" : "Last two minutes",
                    "300" : "Last five minutes",
                    "600" : "Last 10 minutes",
                    "1800" : "Last 30 minutes",
                    "3600" : "Last hour"
                },
                "#limit-select" : {
                    "0" : "No limit",
                    "10" : "Only 10",
                    "50" : "Only 50",
                    "100" : "Only 100",
                    "500" : "Only 500"
                }
            },
            short: {
                "#from-date-select" : {
                    "0" : "None",
                    "120" : "2m",
                    "300" : "5m",
                    "600" : "10m",
                    "1800" : "30m",
                    "3600" : "1h"
                },
                "#limit-select" : {
                    "0" : "All",
                    "10" : "10",
                    "50" : "50",
                    "100" : "100",
                    "500" : "500"
                }
            }
        };

        var rewriteValues = function(id, labelsLookup) {
            $(id + " option").each(function(index, elem) {
                $(elem).text(labelsLookup[$(elem).val()]);
            });
        };

        var labels = currentWidth >= 300 ? dropDownLabels.long : dropDownLabels.short;

        for(var id in labels) {
            if(labels.hasOwnProperty(id)) {
                rewriteValues(id, labels[id]);
            }
        }
    },
    deleteRows: function (button, config, flash) {
        $('#alerts .active').each(function(index, elem) {
            Alerta.deleteAlert($(elem).data("alert-id"));
        });
    },
    deleteAlert: function(alertId) {
        $.ajax({
            type: 'POST',
            contentType: 'application/json',
            url: 'http://' + API_HOST + '/alerta/api/v2/alerts/alert/' + alertId,
            data: JSON.stringify({ _method: 'delete' })
        });
    }
};

$.fn.dataTableExt.oApi.fnReloadAjax = function ( oSettings, sNewSource, fnCallback, bStandingRedraw )
{
    var openRows = $("#alerts tr").filter(function () { return oTable.fnIsOpen(this); });
    var selectedRows = $("#alerts tr.active");

    if(openRows.length > 0 || selectedRows.length > 0) { return; }

    if ( typeof sNewSource != 'undefined' && sNewSource != null ) {
        oSettings.sAjaxSource = sNewSource;
    }

    // Server-side processing should just call fnDraw
    if ( oSettings.oFeatures.bServerSide ) {
        this.fnDraw();
        return;
    }

    this.oApi._fnProcessingDisplay( oSettings, true );
    var that = this;
    var iStart = oSettings._iDisplayStart;
    var aData = [];

    this.oApi._fnServerParams( oSettings, aData );

    oSettings.fnServerData.call( oSettings.oInstance, oSettings.sAjaxSource, aData, function(json) {
        /* Clear the old information from the table */
        that.oApi._fnClearTable( oSettings );

        /* Got the data - add it to the table */
        var aData =  (oSettings.sAjaxDataProp !== "") ?
            that.oApi._fnGetObjectDataFn( oSettings.sAjaxDataProp )( json ) : json;

        for ( var i=0 ; i<aData.length ; i++ )
        {
            that.oApi._fnAddData( oSettings, aData[i] );
        }

        oSettings.aiDisplay = oSettings.aiDisplayMaster.slice();

        if ( typeof bStandingRedraw != 'undefined' && bStandingRedraw === true )
        {
            oSettings._iDisplayStart = iStart;
            that.fnDraw( false );
        }
        else
        {
            that.fnDraw();
        }

        that.oApi._fnProcessingDisplay( oSettings, false );

        /* Callback user function - for event handlers etc */
        if ( typeof fnCallback == 'function' && fnCallback != null )
        {
            fnCallback( oSettings );
        }
    }, oSettings );
};

var oTable;
var autoRefresh = true;

function updateAlertsTable(env_filter, asiFilters) {

    // initialias asiFitlers
    lookup = asiFilters;
    gEnvFilter = env_filter;

    var ti;
    oTable = $('#alerts').dataTable({
        "bProcessing": true,
        "bServerSide": false,
        "bSort": true,
        "bPaginate": true,
        "bDeferRender": true,
        "bAutoWidth" :false,
        "bStateSave" : true,
        "sDom": "<'row-fluid'<'span4'l><'span4'f><'span4'T>r>t<'row-fluid'<'span6'i><'span6'p>>",
        "sAjaxSource": 'http://' + API_HOST + '/alerta/api/v2/alerts?' + gEnvFilter + filter + status + limit + from,
        "fnRowCallback": function (nRow, aData, iDisplayIndex, iDisplayIndexFull) {
            nRow.className = 'alert-summary' + ' severity-' + aData[0] + ' status-' + aData[1];
            $(nRow).attr('id', 'row-' + aData[11]).data("alert-id", aData[11]);

            if (aData[17] == "noChange") {
                ti = '<i class="icon-minus"></i>&nbsp;'
            } else if (aData[17] == "moreSevere") {
                ti = '<i class="icon-arrow-up"></i>&nbsp;'
            } else if (aData[17] == "lessSevere") {
                ti = '<i class="icon-arrow-down"></i>&nbsp;'
            } else {
                ti = '<i class="icon-random"></i>&nbsp;'
            }

            $('td:eq(0)', nRow).html(ti + sev2label(aData[0]));
            $('td:eq(1)', nRow).html(stat2label(aData[1]));

            var d = new Date(aData[2]);
            // $('td:eq(2)', nRow).html(d.toLocaleString());
            $('td:eq(2)', nRow).html(date2iso8601(d));
            var alertText = aData[9];
            if(alertText.length > 28) {
                $('td:eq(9)', nRow).html(alertText.substring(0, 40) + "...").attr("title", alertText);
            }
        },
        "fnServerData": function (sSource, aoData, fnCallback) {
            $.ajax( {
                "dataType": 'json',
                "type": "GET",
                "url": sSource,
                "data": aoData,
                "success": function (json) {
                    autoRefresh = json.response.autoRefresh;
                    var a = [];
                    $.each(json.response.alerts.alertDetails, function (i, ad) {
                        var inner = [];
                        inner.push(
                            ad.severity,       // 0
                            ad.status,
                            ad.lastReceiveTime,
                            ad.duplicateCount,
                            ad.environment,
                            ad.service,
                            // TODO(nsatterl): cluster
                            ad.resource,
                            ad.event,
                            ad.value,
                            ad.text,  // 9

                            SEVERITY_MAP[ad.severity], // severityCode to enable sorting on severity

                            ad.id, // 11
                            ad.lastReceiveId,
                            ad.createTime,
                            ad.receiveTime,
                            ad.group,
                            ad.previousSeverity,
                            ad.trendIndication,
                            ad.thresholdInfo,
                            ad.timeout,
                            ad.type,
                            ad.repeat,
                            ad.summary,
                            ad.origin,
                            ad.tags,
                            ad.moreInfo,
                            ad.graphUrls,
                            ad.history
                        );
                        a.push(inner);
                    });
                    json.aaData = a;
                    fnCallback(json);
                }
            });
        },
        "aoColumns": [
            { "iDataSort": 10, "sClass": "alert-summary-cell essential align-center no-wrap" },
            { "sClass": "alert-summary-cell optional align-center" },
            { "sType": "date", "sClass": "alert-summary-cell optional align-center" },
            { "sClass": "alert-summary-cell full align-center" },
            { "sClass": "alert-summary-cell essential align-center" },
            { "sClass": "alert-summary-cell optional align-center" },
            { "sClass": "alert-summary-cell essential align-center" },
            { "sClass": "alert-summary-cell essential align-center" },
            { "sClass": "alert-summary-cell essential align-center" },
            { "sClass" : "alert-summary-cell full" },
            { "bVisible": false }
        ],
        "aaSorting": [
            [0, 'asc'],
            [2, 'desc']
        ],
        "oTableTools" : {
            "sRowSelect" : "multi",
            "aButtons" : [
                {
                    "sExtends" : "ajax",
                    "sButtonText" : "Delete",
                    "fnClick" : Alerta.deleteRows
                },
                "select_all", "select_none"]
        }
    });

    if (autoRefresh) {
        timer = setTimeout(function() {
            refreshAlerts(true);
        }, REFRESH_INTERVAL * 1000);
    }
}

function fnFormatDetails(aData) {
    var severity = aData[0];
    var status = aData[1];
    var lastReceiveTime = aData[2];
    var duplicateCount = aData[3];
    var environment = aData[4];
    var service = aData[5];
    var cluster = '';
    var resource = aData[6];
    var event = aData[7];
    var value = aData[8];
    var text = aData[9];
    var severityCode = aData[10];
    var alertid = aData[11];
    var lastReceiveId = aData[12];
    var createTime = aData[13];
    var receiveTime = aData[14];
    var group = aData[15];
    var previousSeverity = aData[16];
    var trendIndication = aData[17];
    var thresholdInfo = aData[18];
    var timeout = aData[19];
    var type = aData[20];
    var repeat = aData[21];
    var summary = aData[22];
    var origin = aData[23];
    var tags = '';
    var moreInfo = aData[25];
    var graphUrls = '';
    var history = aData[27];

    $.each(aData[24], function (y, tag) {
        tags += '<span class="label">' + tag + '</span> ';
        var t = tag.split(':');
        if (t[0] == 'cluster') {
            cluster = t[1];
        }
    });

    $.each(aData[26], function (y, graph) {
        graphUrls += '<a href="' + graph + '" target="_blank">Graph ' + y + '</a> ';
    });

    var historydata = '<section class="history-wrapper"><table class="table table-condensed"><thead><td colspan="2"><b>History </b></td></thead><tbody><tr><td>';

    if (history) {
        var reverseHistory = history.reverse();
        $.each(reverseHistory, function (y, hist) {
            if (hist.event) {
                historydata += // '<hr/>' +
                    '<table class="table table-condensed table-striped alert-detail-history">' +
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
                historydata += // '<hr/>' +
                    '<table class="table table-condensed table-striped">' +
                        '<tr><td><b>Status</b></td><td>' + stat2label(hist.status) + '</td></tr>' +
                        '<tr><td><b>Update Time</b></td><td>' + date2str(hist.updateTime) + '</td></tr>' +
                        '</table>' +
                        '';
            }
        });
        historydata += '</td></tr></tbody></table></section>'
    }

    var sOut = "";

    sOut += '<div class="alert-detail">'; // 1

    sOut += '<section class="alert-detail-summary-wrapper">'

    sOut += '<div class="btn-group alert-summary-actions">';

    if (status == OPEN) {
        sOut += '<button id="' + alertid + '" class="btn-mini ack-alert" rel="tooltip" title="Acknowledge Alert"><i class="icon-star-empty"></i> Ack</button>';
    }
    if (status == ACK) {
        sOut += '<button id="' + alertid + '" class="btn-mini unack-alert" rel="tooltip" title="Unacknowledge Alert"><i class="icon-star"></i> Unack</button>';
    }
    sOut += '<button id="' + alertid + '" class="btn-mini delete-alert" rel="tooltip" title="Delete Alert"><i class="icon-trash"></i> Delete</button>';

    sOut += '</div>'

    sOut += '<table class="table table-condensed table-striped">';  // 2
    sOut += '<tr class="odd"><td><b>Alert ID</td><td>' + alertid;
    sOut += '</td></tr>';

    sOut += '<tr class="even"><td><b>Last Receive Alert ID</b></td><td>' + lastReceiveId + '</td></tr>';
    sOut += '<tr class="odd"><td><b>Create Time</b></td><td>' + date2str(createTime) + '</td></tr>';
    sOut += '<tr class="even"><td><b>Receive Time</b></td><td>' + date2str(receiveTime) + '</td></tr>';
    sOut += '<tr class="odd"><td><b>Last Receive Time</b></td><td>' + date2str(lastReceiveTime) + '</td></tr>';

    sOut += '<tr class="even"><td><b>Environment</b></td><td>' + environment + '</td></tr>';
    sOut += '<tr class="odd"><td><b>Service</b></td><td>' + service + '</td></tr>';
    sOut += '<tr class="even"><td><b>Resource</b></td><td>' + resource + '</td></tr>';
    sOut += '<tr class="odd"><td><b>Event</b></td><td>' + event + '</td></tr>';
    sOut += '<tr class="even"><td><b>Group</b></td><td>' + group + '</td></tr>';
    sOut += '<tr class="odd"><td><b>Severity</b></td><td>' + sev2label(previousSeverity) + ' -> ' + sev2label(severity) + '</td></tr>';
    sOut += '<tr class="even"><td><b>Status</b></td><td>' + stat2label(status) + '</td></tr>';
    sOut += '<tr class="odd"><td><b>Value</b></td><td>' + value + '</td></tr>';
    sOut += '<tr class="even"><td><b>Text</b></td><td>' + text + '</td></tr>';

    sOut += '<tr class="odd"><td><b>Trend Indication</b></td><td>' + trendIndication + '</td></tr>';
    sOut += '<tr class="even"><td><b>Threshold Info</b></td><td>' + thresholdInfo + '</td></tr>';
    sOut += '<tr class="odd"><td><b>Timeout</b></td><td>' + timeout + '</td></tr>';
    sOut += '<tr class="even"><td><b>Type</b></td><td>' + type + '</td></tr>';
    sOut += '<tr class="odd"><td><b>Repeat</b></td><td>' + repeat + '</td></tr>';
    sOut += '<tr class="even"><td><b>Summary</b></td><td>' + summary + '</td></tr>';
    sOut += '<tr class="odd"><td><b>Origin</b></td><td>' + origin + '</td></tr>';
    sOut += '<tr class="even"><td><b>Tags</b></td><td>' + tags + '<a id="' + alertid + '" class="tag-alert" rel="tooltip" title="Tag Alert"><i class="icon-tags"></i></a>' + '</td></tr>';
    sOut += '<tr class="odd"><td><b>More Info</b></td><td>' + moreInfo + '</td></tr>';
    sOut += '<tr class="even"><td><b>Graphs</b></td><td>' + graphUrls + '</td></tr>';
    sOut += '</table>'; // 2

    sOut += '</section>'
    sOut += historydata;
    sOut += '</div>'; // 1

    return sOut;
}

$('#alerts tbody tr').live('dblclick', function (event) {

    var nTr = this;

    // var i = $.inArray( nTr, anOpen );

    if (oTable.fnIsOpen(nTr)) {
        /* This row is already open - close it */
        // this.src = "../examples_support/details_open.png";
        oTable.fnClose(nTr);
        $(this).removeClass("active");
    }
    else {
        /* Open this row */
        // this.src = "../examples_support/details_close.png";
        oTable.fnOpen(nTr, fnFormatDetails(oTable.fnGetData(nTr)), 'details');
        $(this).addClass("active");
    }
});

function refreshAlerts(refresh) {
    oTable.fnReloadAjax('http://' + API_HOST + '/alerta/api/v2/alerts?' + gEnvFilter + filter + status + limit + from);
    if (refresh && autoRefresh) {
        timer = setTimeout(function() {
            refreshAlerts(refresh);
        }, REFRESH_INTERVAL * 1000);
    }
}

$('#alert-status').click(function () {
    filter = '';
    updateStatusCounts(gEnvFilter, false);
    updateAllIndicators(gEnvFilter, lookup, false);
    refreshAlerts(false);
});

$('#refresh-all').click(function () {
    updateStatusCounts(gEnvFilter, false);
    updateAllIndicators(gEnvFilter, lookup, false);
    refreshAlerts(false);
});

$('.status-indicator-overall').click(function () {
    var statusIndicator = $(this).parent(".status-indicator");

    if(statusIndicator.hasClass("current-filter")) {
        filter = '';
        refreshAlerts(false);
        statusIndicator.removeClass("current-filter")
        $(".status-indicator").removeClass("status-indicator-inactive");
    } else {
        filter = lookup[this.id.split('-')[0]];
        refreshAlerts(false);
        Alerta.highlightStatusIndicator(statusIndicator);
    }
});

$('.status-indicator-count').click(function () {
    filter = lookup[this.id.split('-')[0]];
    var severity = this.id.split('-')[1];
    filter += '&severity=' + severity;

    if (severity == NORMAL) {
        filter += '&severity=' + INFORM;
    }
    refreshAlerts(false);
    var statusIndicator = $(this).parents(".status-indicator");
    Alerta.highlightStatusIndicator(statusIndicator);
});

$('body').on('click', '#status-select .btn', function(e) {
    if (!e.shiftKey) {
        if ( $('#status-select .active').length > 1) {
            $(this).addClass('active');
        } else {
            $(this).toggleClass('active');
        }
        if ($(this).attr("value") != 'open') {
            $('#status-select-open').removeClass('active');
        }
        if ($(this).attr("value") != 'ack') {
            $('#status-select-ack').removeClass('active');
        }
        if ($(this).attr("value") != 'closed') {
            $('#status-select-closed').removeClass('active');
        }
    } else {
        $(this).toggleClass('active');
    }

    status = '';
    if ($('button#status-select-open.btn').hasClass('active')) {
        status += '&status=open';
    }
    if ($('button#status-select-ack.btn').hasClass('active')) {
        status += '&status=ack';
    }
    if ($('button#status-select-closed.btn').hasClass('active')) {
        status += '&status=closed';
    }

    updateStatusCounts(gEnvFilter, false);
    updateAllIndicators(gEnvFilter, lookup, false);
    refreshAlerts(false);
});

$('body').on('click', '#from-date-select .btn', function() {

    $('#from-date-select button').removeClass('active');
    $(this).addClass('active');

    var seconds = $(this).val();

    if (seconds > 0) {
        from = '&from-date=' + new Date(new Date() - seconds * 1000).toISOString();
    } else {
        from = '';
    }

    updateStatusCounts(gEnvFilter, false);
    updateAllIndicators(gEnvFilter, lookup, false);
    refreshAlerts(false);
});

function updateStatus(s) {
    status = '&status=' + s;
    updateStatusCounts(gEnvFilter, false);
    updateAllIndicators(gEnvFilter, lookup, false);
    refreshAlerts(false);
}

function updateStatusCounts(env_filter, refresh) {
    $.getJSON('http://' + API_HOST + '/alerta/api/v2/alerts/counts?callback=?&'
        + env_filter + from, function (data) {

        if (data.response.warning) {
            $('#warning-text').text(data.response.warning);
            $('#console-alert').toggle();
        }

        $.each(data.response.alerts.statusCounts, function (status, count) {
            $("#count-" + status).html('<b>' + count + '</b>');
        });
        if (refresh && autoRefresh) {
            timer = setTimeout(function () {
                updateStatusCounts(env_filter, refresh);
            }, REFRESH_INTERVAL * 1000);
        }
    });
}

function updateAllIndicators(env_filter, asiFilters, refresh) {
    var delayer = 0;
    $.each(asiFilters, function (service) {
        setTimeout(function () {
            updateStatusIndicator(env_filter, asiFilters[service], service, refresh);
        }, delayer);
        delayer += 100;
    });
}

function updateStatusIndicator(env_filter, asi_filter, service, refresh) {
    $('#' + service + ' th').addClass('loader');
    $.getJSON('http://' + API_HOST + '/alerta/api/v2/alerts/counts?callback=?&'
        + env_filter + asi_filter + status + limit + from, function (data) {

        var sev_id = '#' + service;

        data.response.alerts.severityCounts.normal += data.response.alerts.severityCounts.informational;

        $.each(data.response.alerts.severityCounts, function (sev, count) {
            sev = sev.toLowerCase();
            $(sev_id + "-" + sev).html('<b>' + count + '</b>');

            switch (count) {
                case 0:
                    $(sev_id + "-" + sev).removeClass("severity-" + sev).addClass('zero');
                    break;
                default:
                    $(sev_id + "-" + sev).addClass("severity-" + sev).removeClass('zero');
            }
        });
        var scolor;
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

        $('#' + service + ' th').removeClass('loader');

        if (refresh && autoRefresh) {
            timer = setTimeout(function () {
                updateStatusIndicator(env_filter, asi_filter, service, refresh);
            }, REFRESH_INTERVAL * 1000);
        }
    });
}

$(document).ready(function () {

    $('tbody').on('click', '.delete-alert', function () {
        if (confirm('IMPORTANT: Deleting this alert is a permanent operation that will '
            + 'remove the alert from all user consoles.\n\n'
            + 'Cancel to return to the console or OK to delete.')) {

            Alerta.deleteAlert(this.id);
            // FIXME(nsatterl): Should immediately delete the row from the console
            // oTable.fnDeleteRow(
            //    oTable.fnGetPosition(
            //        document.getElementById('#row-' + this.id)));
        }
    });

    $('tbody').on('click', '.ack-alert', function () {
        $.ajax({
            type: 'PUT',
            contentType: 'application/json',
            url: 'http://' + API_HOST + '/alerta/api/v2/alerts/alert/' + this.id,
            data: JSON.stringify({ status: ACK })
        });
    });

    $('tbody').on('click', '.unack-alert', function () {
        $.ajax({
            type: 'PUT',
            contentType: 'application/json',
            url: 'http://' + API_HOST + '/alerta/api/v2/alerts/alert/' + this.id,
            data: JSON.stringify({ status: OPEN })
        });
    });

    $('tbody').on('click', '.tag-alert', function () {
        var tag = prompt("Enter tag eg. london, location:london, datacentre:location=london");
        if (tag != null && tag != "") {
            $.ajax({
                type: 'PUT',
                contentType: 'application/json',
                url: 'http://' + API_HOST + '/alerta/api/v2/alerts/alert/' + this.id + '/tag',
                data: JSON.stringify({ tag: tag })
            });
        }
    });

    Alerta.dropDownText(window);

    $(window).resize(function() {
        Alerta.dropDownText(window);
    });
});
