
import socket

alert = 'test'

stomp = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
stomp.connect(('localhost', 61613))
stomp.send('CONNECT\n\n\x00')
recv = stomp.recv(4096)
if 'CONNECTED' in recv:
    stomp.send('SEND\ndestination:%s\n\n' % '/queue/test')
    stomp.send(alert)
    stomp.send('\x00')
else:
    print('Connection problem')

    
    