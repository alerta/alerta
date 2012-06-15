// To remove expired alerts from the alerta database run this script from cron like so: 
// * * * * * /usr/bin/mongo --quiet monitoring /opt/alerta/sbin/removeExpiredAlerts.js
now = new Date();
db.alerts.remove({ 'expireTime': { $lt: now }});
