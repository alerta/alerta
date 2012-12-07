
if 'r2' in alert['resource'].lower():
    alert['service'] = [ 'R2' ]
elif 'content-api' in alert['resource'].lower():
    alert['service'] = [ 'ContentAPI' ]
elif 'flexible' in alert['resource'].lower():
    alert['service'] = [ 'FlexibleContent' ]
elif 'frontend' in alert['resource'].lower():
    alert['service'] = [ 'Frontend' ]
elif 'mobile' in alert['resource'].lower():
    alert['service'] = [ 'Mobile' ]
elif 'android' in alert['resource'].lower():
    alert['service'] = [ 'Mobile' ]
elif 'ios' in alert['resource'].lower():
    alert['service'] = [ 'Mobile' ]
elif 'identity' in alert['resource'].lower():
    alert['service'] = [ 'Identity' ]
elif 'microapps' in alert['resource'].lower():
    alert['service'] = [ 'MicroApp' ]
else:
    alert['service'] = [ 'Unknown' ]
