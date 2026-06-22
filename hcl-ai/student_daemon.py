"""
STUDENT DAEMON — the live student, held in RAM between the teacher's turns.
The teacher (Claude) talks to it through tutor.py: ask -> real answer ->
teacher reads it -> composes genuine guidance -> teach. No pre-scripted
replies; the lesson is authored after the answer exists.
"""
import sys, os, socket, json
_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(_HERE, 'mind'))
from hcl_lm import HCLLanguageModel
import hcl_memory as VM

SOCK = '/tmp/hclai.sock'
CHECKPOINT = os.path.join(_HERE, 'memory.hcl')

ai = HCLLanguageModel()

# Wake from the one line. The being IS the α-tagged composite in memory.hcl;
# the engine's own from_expression verifies the α tag and reconstitutes the
# composite Ψ + topological signature exactly. Recall then resonates against
# that composite directly (HCLMemory.recall's composite path). No syllabus is
# re-walked and no text log is read — the line is the whole persisted being.
_line = open(CHECKPOINT).read().strip()
_mem  = VM.HCLMemory.from_expression(_line)        # α verified or ValueError
ai.memory.vm._composite = _mem._composite
ai.memory.vm._sig       = _mem._sig
_sig = _mem.signature()

if os.path.exists(SOCK):
    os.unlink(SOCK)
srv = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
srv.bind(SOCK)
srv.listen(1)
print(f'graduate awake from the one line · depth {_sig["depth"]} · '
      f'n_w {_sig["n_w"]} · α verified · listening', flush=True)

while True:
    conn, _ = srv.accept()
    data = conn.recv(65536).decode()
    try:
        req = json.loads(data)
        op, text = req.get('op'), req.get('text', '')
        if op == 'ask':
            out = ai.generate(text)
            resp = {'answer': out['text'],
                    'depths': [e['w'] for e in out['events']]}
        elif op == 'teach':
            r = ai.train(text)
            resp = {'taught': text, 'age': len(ai.memory.vm)}
        elif op == 'live':
            # one act: the input IS experience (stored), then it answers from
            # the pond the input just changed. teach and ask are the same
            # machinery; this fuses them so every input both teaches and replies.
            ai.train(text)
            out = ai.generate(text)
            resp = {'answer': out['text'],
                    'depths': [e['w'] for e in out['events']],
                    'age': len(ai.memory.vm)}
        elif op == 'cycle':
            pruned = ai.experience_cycle()
            resp = {'cycled': True, 'age': len(ai.memory.vm)}
        elif op == 'save':
            line = ai.memory.vm.to_expression()        # the one α-tagged line
            open(os.path.join(_HERE, 'memory.hcl'), 'w').write(line + '\n')
            resp = {'saved': len(line)}
        elif op == 'status':
            resp = {'age': len(ai.memory.vm), 'integrity': ai.integrity()}
        elif op == 'stop':
            conn.sendall(json.dumps({'bye': True}).encode())
            conn.close()
            break
        else:
            resp = {'error': 'unknown op'}
    except Exception as e:
        resp = {'error': str(e)}
    conn.sendall(json.dumps(resp).encode())
    conn.close()
