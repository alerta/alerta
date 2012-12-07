
if alert['resource'].startswith('R1'):
    alert['service'] = [ 'R1' ]
elif alert['resource'].startswith('R2'):
    alert['service'] = [ 'R2' ]
elif 'content-api' in alert['resource'].lower():
    alert['service'] = [ 'ContentAPI' ]
elif alert['resource'].startswith('frontend'):
    alert['service'] = [ 'Frontend' ]
    if alert['event'] == 'DeployFailed':
        alert['severity'] = 'CRITICAL'
elif 'flexible' in alert['resource'].lower():
    alert['service'] = [ 'FlexibleContent' ]
elif alert['resource'].startswith('Identity'):
    alert['service'] = [ 'Identity' ]
elif alert['resource'].startswith('Mobile'):
    alert['service'] = [ 'Mobile' ]
elif alert['resource'].startswith('Android'):
    alert['service'] = [ 'Mobile' ]
elif alert['resource'].startswith('iOS'):
    alert['service'] = [ 'Mobile' ]
elif alert['resource'].startswith('Soulmates'):
    alert['service'] = [ 'Soulmates' ]
elif alert['resource'].startswith('Microapps'):
    alert['service'] = [ 'MicroApp' ]
elif alert['resource'].startswith('Mutualisation'):
    alert['service'] = [ 'Mutualisation' ]
elif alert['resource'].startswith('Ophan'):
    alert['service'] = [ 'Ophan' ]
else:
    alert['service'] = [ 'Unknown' ]
