// Run this script from cron like so:
// * * * * * /usr/bin/mongo --quiet monitoring /opt/alerta/tools/removeExpiredAlerts.js

// mark timed out alerts as EXPIRED and update alert history
now = new Date();
db.alerts.update({ status: 'OPEN', expireTime: { $lt: now }}, { $set: { status: 'EXPIRED' }, $push: { history: {status: 'EXPIRED', updateTime: now }}}, false, true);

// delete CLOSED alerts older than 2 hours
2hrs_ago = new Date(new Date() - 2*60*60*1000);
db.alerts.remove({ status: 'CLOSED', lastReceiveTime: { $lt: 2hrs_ago }});

// delete INFORM alerts older than 12 hours
12hrs_ago = new Date(new Date() - 12*60*60*1000);
db.alerts.remove({ severity: 'INFORM', lastReceiveTime: { $lt: 12hrs_ago }});