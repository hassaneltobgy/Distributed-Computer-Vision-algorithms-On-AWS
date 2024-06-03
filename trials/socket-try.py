import socket

s = socket.socket()
host = socket.gethostbyaddr('13.38.14.212')[0]
port = 10240

s.connect((host, port))
print(s.recv(1024).decode())
s.close()