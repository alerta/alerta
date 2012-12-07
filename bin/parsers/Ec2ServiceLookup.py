# contentapimq -> ContentAPI
if any(tag.startswith('cluster:contentapimq') for tag in alert['tags']):
    alert['service'] = [ 'ContentAPI' ]
# discussion-app -> Discussion
elif any(tag.startswith('cluster:discussion') for tag in alert['tags']):
    alert['service'] = [ 'Discussion' ]
# mobile-aggregator -> Mobile
elif any(tag.startswith('cluster:mobile') for tag in alert['tags']):
    alert['service'] = [ 'Mobile' ]
# content-authorisation -> Mobile
elif any(tag.startswith('cluster:content-authorisation') for tag in alert['tags']):
    alert['service'] = [ 'Mobile' ]
# ios-purchases -> Mobile
elif any(tag.startswith('cluster:ios-purchases') for tag in alert['tags']):
    alert['service'] = [ 'Mobile' ]
# ipad-ad-preview -> Mobile
elif any(tag.startswith('cluster:ipad-ad-preview') for tag in alert['tags']):
    alert['service'] = [ 'Mobile' ]
# mongo-cluster -> SharedSvcs
elif any(tag.startswith('cluster:mongo-cluster') for tag in alert['tags']):
    alert['service'] = [ 'SharedSvcs' ]
# outboundproxy -> SharedSvcs
elif any(tag.startswith('cluster:outboundproxy') for tag in alert['tags']):
    alert['service'] = [ 'SharedSvcs' ]
# arts-books -> Arts
# arts-music -> Arts
elif any(tag.startswith('cluster:arts') for tag in alert['tags']):
    alert['service'] = [ 'Arts' ]
# lists-service -> Arts
elif any(tag.startswith('cluster:lists-service') for tag in alert['tags']):
    alert['service'] = [ 'Arts' ]
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
else:
    alert['service'] = [ 'Unknown' ]
