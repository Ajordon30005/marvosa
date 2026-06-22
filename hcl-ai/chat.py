"""
Live conversation with the HCL-AI organism.

There are no commands. Every line you type IS experience the organism lives —
it stores what you said, then answers from the pond your words just changed.
Teaching and asking are the same act here, because in this system they always
were: input is experience, and the answer falls out of the experience.

  (just type — anything. press Enter on an empty line or Ctrl-D to leave.)

Nothing is written to disk unless you exit with 'save' on its own line; the
organism updates live in RAM as you talk.
"""
import socket, json, sys

SOCK = '/tmp/hclai.sock'

def call(op, text=''):
    s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    s.connect(SOCK)
    s.sendall(json.dumps({'op': op, 'text': text}).encode())
    r = json.loads(s.recv(65536).decode()); s.close()
    return r

def main():
    try:
        st = call('status')
    except Exception:
        print("No running organism. Start it first:  ./chat.sh")
        sys.exit(1)
    a = st.get('integrity', {}).get('engine_alpha_inv', '?')
    print("─" * 56)
    print("  HCL-AI — live. Just type. Every line is experience.")
    print(f"  age {st.get('age','?')} traces · integrity {a}")
    print("─" * 56)
    print("(empty line or Ctrl-D to leave; type 'save' alone to persist)\n")
    while True:
        try:
            line = input("» ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n(left — the organism stays alive in the daemon)")
            break
        if line == '':
            print("(left — the organism stays alive in the daemon)")
            break
        if line == 'save':
            r = call('save'); print(f"  · saved to one line ({r.get('saved','?')} chars)\n"); continue
        r = call('live', line)
        ans = (r.get('answer') or '').strip()
        print(f"  {ans if ans else '…'}\n")

if __name__ == '__main__':
    main()
