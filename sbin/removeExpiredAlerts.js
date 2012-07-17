// To mark expired and old alerts in the alerta database run this script from cron like so:
// * * * * * /usr/bin/mongo --quiet monitoring /opt/alerta/sbin/removeExpiredAlerts.js
now = new Date();
db.alerts.update({ status: 'OPEN', expireTime: { $lt: now }}, { $set: { status: 'EXPIRED' }, $push: { history: {status: 'EXPIRED', updateTime: now }}}, false, true);

ago = new Date(new Date() - 2*60*60*1000);
db.alerts.update({ status: 'CLOSED', lastReceiveTime: { $lt: ago }}, { $set: { status: 'DELETED' }, $push: { history: {status: 'DELETED', updateTime: now }}}, false, true);
