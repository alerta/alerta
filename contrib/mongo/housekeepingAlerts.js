// Run this script from cron like so:
// * * * * * /usr/bin/mongo --quiet monitoring housekeepingAlerts.js

now = new Date();

// mark timed out alerts as EXPIRED and update alert history
db.alerts.aggregate([
    { $project: { event: 1, status: 1, lastReceiveId: 1, timeout: 1, expireTime: { $add: [ "$lastReceiveTime", { $multiply: [ "$timeout", 1000 ]} ]} } },
    { $match: { status: { $ne: 'expired' }, expireTime: { $lt: now }, timeout: { $ne: 0 }}}
]).forEach( function(alert) {
    db.alerts.update(
        { _id: alert._id },
        {
            $set: { status: 'expired' },
            $push: {
                history: {
                    event: alert.event,
                    status: 'expired',
                    text: "alert timeout status change",
                    id: alert.lastReceiveId,
                    updateTime: now
                }
            }
        }, false, true);
})

// delete CLOSED or EXPIRED alerts older than 2 hours
two_hrs_ago = new Date(new Date() - 2*60*60*1000);
db.alerts.remove({status: {$in: ['closed', 'expired']}, lastReceiveTime: {$lt: two_hrs_ago}});

// delete INFORM alerts older than 12 hours
twelve_hrs_ago = new Date(new Date() - 12*60*60*1000);
db.alerts.remove({severity: 'informational', lastReceiveTime: {$lt: twelve_hrs_ago}});
