// Run this script from cron like so:
// * * * * * /usr/bin/mongo --quiet monitoring /opt/bin/housekeepingAlerts.js

// mark timed out alerts as EXPIRED and update alert history
now = new Date();
db.alerts.update({status: 'open', expireTime: {$lt: now}}, {$set: {status: 'expired'}, $push: {history: {status: 'expired', updateTime: now}}}, false, true);

// delete CLOSED alerts older than 2 hours
two_hrs_ago = new Date(new Date() - 2*60*60*1000);
db.alerts.remove({status: {$in: ['closed', 'expired']}, lastReceiveTime: {$lt: two_hrs_ago}});

// delete INFORM alerts older than 12 hours
twelve_hrs_ago = new Date(new Date() - 12*60*60*1000);
db.alerts.remove({severity: 'informational', lastReceiveTime: {$lt: twelve_hrs_ago}});