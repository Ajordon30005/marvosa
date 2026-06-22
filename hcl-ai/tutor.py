import sys, socket, json
SOCK = '/tmp/hclai.sock'
op = sys.argv[1]
text = sys.argv[2] if len(sys.argv) > 2 else ''
s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
s.connect(SOCK)
s.sendall(json.dumps({'op': op, 'text': text}).encode())
print(json.loads(s.recv(65536).decode()))
