
if resource.startswith('R1'):
    service = ['R1']
    
elif resource.startswith('R2'):
    service = ['R2']
    
elif 'content-app' in resource.lower():
    service = ['ContentAPI']
    
elif resource.startswith('frontend'):
    service = ['Frontend']
    
    if alert['event'] == 'DeployFailed':
        alert['severity'] = severity.CRITICAL
        alert['tags'].append('email:frontend')
        
elif 'flexible' in resource.lower():
    service = ['FlexibleContent']
    
elif resource.startswith('Identity'):
    service = ['Identity']
    
elif resource.startswith('Mobile'):
    service = ['Mobile']
    
elif resource.startswith('Android'):
    service = ['Mobile']
    
elif resource.startswith('iOS'):
    service = ['Mobile']
    
elif resource.startswith('Soulmates'):
    service = ['Soulmates']
    
elif resource.startswith('Microapps'):
    service = ['MicroApp']
    
elif resource.startswith('Mutualisation'):
    service = ['Mutualisation']
    
elif resource.startswith('Ophan'):
    service = ['Ophan']
    
else:
    service = ['Unknown']
