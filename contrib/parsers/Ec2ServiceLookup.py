
# contentapimq -> ContentAPI
if any(tag.startswith('cluster:contentapimq') for tag in tags):
    service = ['ContentAPI']

# frontend-* -> Frontend
elif any(tag.startswith('cluster:frontend') for tag in tags):
    service = ['Frontend']

# soulmates-* -> Soulmates
# geolocation -> Soulmates
elif any(tag.startswith('cluster:soulmates') for tag in tags):
    service = ['Soulmates']
elif any(tag.startswith('cluster:geolocation-app') for tag in tags):
    service = ['Soulmates']

# discussion-app -> Discussion
# renderer -> Discussion
elif any(tag.startswith('cluster:discussion') for tag in tags):
    service = ['Discussion']
elif any(tag.startswith('cluster:renderer') for tag in tags):
    service = ['Discussion']

# mobile-aggregator -> Mobile
elif any(tag.startswith('cluster:mobile') for tag in tags):
    service = ['Mobile']

# content-authorisation -> Mobile
elif any(tag.startswith('cluster:content-authorisation') for tag in tags):
    service = ['Mobile']

# ios-purchases -> Mobile
elif any(tag.startswith('cluster:ios_purchases') for tag in tags):
    service = ['Mobile']

# ipad-ad-preview -> Mobile
elif any(tag.startswith('cluster:ipad_ad_preview') for tag in tags):
    service = ['Mobile']

# pushy_galore -> Mobile
elif any(tag.startswith('cluster:pushy_galore') for tag in tags):
    service = ['Mobile']

# mongo-cluster -> SharedSvcs
elif any(tag.startswith('cluster:mongo-cluster') for tag in tags):
    service = ['SharedSvcs']

# outboundproxy -> SharedSvcs
elif any(tag.startswith('cluster:outboundproxy') for tag in tags):
    service = ['SharedSvcs']

# arts-books -> Mutualisation
# arts-music -> Mutualisation
elif any(tag.startswith('cluster:arts') for tag in tags):
    service = [ 'Mutualisation' ]

# lists-service -> Mutualisation
elif any(tag.startswith('cluster:lists-service') for tag in tags):
    service = ['Mutualisation']

# cutswatch-db -> Other
# cutswatch-frontend -> Other
elif any(tag.startswith('cluster:cutswatch') for tag in tags):
    service = ['Other']

# gov-spending -> Other
elif any(tag.startswith('cluster:gov-spending') for tag in tags):
    service = ['Other']

# interactive-traffic-stats -> Other
elif any(tag.startswith('cluster:interactive') for tag in tags):
    service = ['Other']

# ganglia-* -> SharedSvcs
# puppet-* -> SharedSvcs
# zabbix-* -> SharedSvcs
elif any(tag.startswith('cluster:ganglia') for tag in tags):
    service = ['SharedSvcs']
elif any(tag.startswith('cluster:puppet') for tag in tags):
    service = ['SharedSvcs']
elif any(tag.startswith('cluster:zabbix') for tag in tags):
    service = ['SharedSvcs']
else:
    service = ['Unknown']

# Redo summary because service has changed
summary = '%s - %s %s is %s on %s %s' % (','.join(environment), severity, event, value, ','.join(service), resource)
