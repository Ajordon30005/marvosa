"""
tutor_batch.py — replay every 'ask' line in gradebook.txt through the
running student daemon and print the answers (regression over the syllabus).

    python3 tutor_batch.py            # requires student_daemon.py running
"""
import sys, socket, json
SOCK='/tmp/hclai.sock'
def send(op, text=''):
    s=socket.socket(socket.AF_UNIX, socket.SOCK_STREAM); s.connect(SOCK)
    s.sendall(json.dumps({'op':op,'text':text}).encode())
    r=json.loads(s.recv(65536).decode()); s.close(); return r
def main():
    import os
    if not os.path.exists('gradebook.txt'):
        print(__doc__); print('(no gradebook.txt here — run from hcl-ai/ after teaching)'); return
    gb=open('gradebook.txt','a'); al=open('answers.log','a')
    for line in open(sys.argv[1]):
        line=line.strip()
        if not line or line.startswith('#'): continue
        op,_,text=line.partition('|')
        r=send(op,text)
        if op=='ask':
            print(f'S: {r["answer"]}'); al.write(json.dumps({'q':text,'a':r['answer']})+'\n')
        elif op=='teach':
            gb.write(text+'\n')
        elif op=='cycle': print(f'-- day end (age {r["age"]}) --')
        else: print(r)
    gb.close(); al.close()


if __name__ == '__main__':
    main()
