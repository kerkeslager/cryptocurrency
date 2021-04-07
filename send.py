 # Socket client example in python

import socket
import sys

host = 'localhost'
port = 5555

# create socket
print('# Creating socket')
try:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
except socket.error:
    print('Failed to create socket')
    sys.exit()

print('# Getting remote IP address') 
try:
    remote_ip = socket.gethostbyname( host )
except socket.gaierror:
    print('Hostname could not be resolved. Exiting')
    sys.exit()

# Connect to remote server
print('# Connecting to server, ' + host + ' (' + remote_ip + ')')
s.connect((remote_ip , port))

while True:
    request = input('>>>')

    try:
        s.sendall(request.encode('utf-8'))
    except socket.error:
        print('Send failed')
        sys.exit()

    reply = s.recv(4096)
    print('Server replied:', reply)
