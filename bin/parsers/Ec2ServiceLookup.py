# contentapimq -> ContentAPI
if any(tag.startswith('cluster:contentapimq') for tag in alert['tags']):
    alert['service'] = [ 'ContentAPI' ]
# frontend-* -> Frontend
elif any(tag.startswith('cluster:frontend') for tag in alert['tags']):
    alert['service'] = [ 'Frontend' ]
# soulmates-* -> Soulmates
# geolocation -> Soulmates
elif any(tag.startswith('cluster:soulmates') for tag in alert['tags']):
    alert['service'] = [ 'Soulmates' ]
elif any(tag.startswith('cluster:geolocation-api') for tag in alert['tags']):
    alert['service'] = [ 'Soulmates' ]
# discussion-app -> Discussion
# renderer -> Discussion
elif any(tag.startswith('cluster:discussion') for tag in alert['tags']):
    alert['service'] = [ 'Discussion' ]
elif any(tag.startswith('cluster:renderer') for tag in alert['tags']):
    alert['service'] = [ 'Discussion' ]
# mobile-aggregator -> Mobile
elif any(tag.startswith('cluster:mobile') for tag in alert['tags']):
    alert['service'] = [ 'Mobile' ]
# content-authorisation -> Mobile
elif any(tag.startswith('cluster:content-authorisation') for tag in alert['tags']):
    alert['service'] = [ 'Mobile' ]
# ios-purchases -> Mobile
elif any(tag.startswith('cluster:ios_purchases') for tag in alert['tags']):
    alert['service'] = [ 'Mobile' ]
# ipad-ad-preview -> Mobile
elif any(tag.startswith('cluster:ipad_ad_preview') for tag in alert['tags']):
    alert['service'] = [ 'Mobile' ]
# pushy_galore -> Mobile
elif any(tag.startswith('cluster:pushy_galore') for tag in alert['tags']):
    alert['service'] = [ 'Mobile' ]
# mongo-cluster -> SharedSvcs
elif any(tag.startswith('cluster:mongo-cluster') for tag in alert['tags']):
    alert['service'] = [ 'SharedSvcs' ]
# outboundproxy -> SharedSvcs
elif any(tag.startswith('cluster:outboundproxy') for tag in alert['tags']):
    alert['service'] = [ 'SharedSvcs' ]
# arts-books -> Mutualisation
# arts-music -> Mutualisation
elif any(tag.startswith('cluster:arts') for tag in alert['tags']):
    alert['service'] = [ 'Mutualisation' ]
# lists-service -> Mutualisation
elif any(tag.startswith('cluster:lists-service') for tag in alert['tags']):
    alert['service'] = [ 'Mutualisation' ]
# cutswatch-db -> Other
# cutswatch-frontend -> Other
elif any(tag.startswith('cluster:cutswatch') for tag in alert['tags']):
    alert['service'] = [ 'Other' ]
# gov-spending -> Other
elif any(tag.startswith('cluster:gov-spending') for tag in alert['tags']):
    alert['service'] = [ 'Other' ]
# interactive-traffic-stats -> Other
elif any(tag.startswith('cluster:interactive') for tag in alert['tags']):
    alert['service'] = [ 'Other' ]
# ganglia-* -> SharedSvcs
# puppet-* -> SharedSvcs
# zabbix-* -> SharedSvcs
elif any(tag.startswith('cluster:ganglia') for tag in alert['tags']):
    alert['service'] = [ 'SharedSvcs' ]
elif any(tag.startswith('cluster:puppet') for tag in alert['tags']):
    alert['service'] = [ 'SharedSvcs' ]
elif any(tag.startswith('cluster:zabbix') for tag in alert['tags']):
    alert['service'] = [ 'SharedSvcs' ]
else:
    alert['service'] = [ 'Unknown' ]

alert['summary'] = '%s - %s %s is %s on %s %s' % (','.join(alert['environment']), alert['severity'], alert['event'], alert['value'], ','.join(alert['service']), alert['resource'])
