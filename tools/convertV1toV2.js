// Usage: mongo monitoring ./convertV1toV2.js

// convert severity to lowercase
db.alerts.update({severity:'CRITICAL'},{$set:{severity: 'critical'}},false, true);
db.alerts.update({severity:'MAJOR'},{$set:{severity: 'major'}},false, true);
db.alerts.update({severity:'MINOR'},{$set:{severity: 'minor'}},false, true);
db.alerts.update({severity:'WARNING'},{$set:{severity: 'warning'}},false, true);
db.alerts.update({severity:'NORMAL'},{$set:{severity: 'normal'}},false, true);
db.alerts.update({severity:'INFORM'},{$set:{severity: 'informational'}},false, true);
db.alerts.update({severity:'DEBUG'},{$set:{severity: 'debug'}},false, true);

// conver status to lowercase
db.alerts.update({status:'OPEN'},{$set:{status: 'open'}},false, true);
db.alerts.update({status:'ACK'},{$set:{status: 'ack'}},false, true);
db.alerts.update({status:'CLOSED'},{$set:{status: 'closed'}},false, true);
db.alerts.update({status:'EXPIRED'},{$set:{status: 'expired'}},false, true);

// add missing attributes
db.alerts.update({},{$set:{'trendIndication': 'noChange'}},false,true);
db.alerts.update({rawData: {$exists: false}},{$set:{'rawData': null}},false,true);
db.alerts.update({correlatedEvents: {$exists: false}}, {$set: {correlatedEvents: null}},false,true);