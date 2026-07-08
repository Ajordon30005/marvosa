"""
tutor.py — one teaching exchange with the running student daemon.

    python3 tutor.py feed  <text>     # give the student experience
    python3 tutor.py ask   <prompt>   # ask; prints the student's answer
    python3 tutor.py grade <text>     # record a grade line in gradebook.txt
Requires the daemon: python3 student_daemon.py (or just use ../chat.sh).
"""
import sys, socket, json
SOCK = '/tmp/hclai.sock'
def main():
    if len(sys.argv) < 2:
        print(__doc__); return
    op = sys.argv[1]
    text = sys.argv[2] if len(sys.argv) > 2 else ''
    s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    s.connect(SOCK)
    s.sendall(json.dumps({'op': op, 'text': text}).encode())
    print(json.loads(s.recv(65536).decode()))


if __name__ == '__main__':
    main()
