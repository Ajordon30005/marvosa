"""
HCL-AI — the organism, delivered.
==================================
One front door. Everything behind it is the session's verified build:
hcl-pure substrate (verbatim), the three memory engines (verbatim),
the LM as pure arrangement, substrate-verdict halting (TERMINATED /
BRAID CLOSED / MCL COLLAPSE).

The memory IS the one α-tagged line (memory.hcl) — a holographic composite,
not a file of records. lifebook.txt is NOT memory and NOT needed for the AI
to run: it is a plain append-only text log of the inputs fed in, kept only
for transparency (you can read what the organism was given). Every line it
logs is transcribed and resolved on the hcl-pure substrate; the log is a
human-readable record of that, never the computation itself.

Commands:
  feed <text>     give it experience (stored both senses, reinforced on repeats;
                  the input is also appended to lifebook.txt — the plain log)
  ask <prompt>    one answer: iterated MCL collapse, reinforcement on used traces
  talk <seed>     self-talk until a substrate verdict fires (TERMINATED /
                  BRAID CLOSED / MCL COLLAPSE)
  solve <eq>      exact arithmetic organ, e.g.  solve E = m * c^2 ; m=2 c=3
  status          age, signature, integrity (α must read 137 everywhere)
  save            checkpoint the memory: ONE α-tagged line (memory.hcl)
  load            wake from the one α-tagged line (memory.hcl) — the line IS
                  the memory; its composite resonates as the whole being
                  (nothing else is read; the lifebook is never replayed)
  quit
"""
import sys, os
_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(_HERE, 'mind'))

from hcl_lm import HCLLanguageModel
from teach import self_talk
import hcl_memory as VM

LIFEBOOK = os.path.join(_HERE, 'lifebook.txt')
CHECKPOINT = os.path.join(_HERE, 'memory.hcl')   # the one line

ai = HCLLanguageModel()


def cmd_feed(text):
    r1 = ai.train(text); r2 = ai.train(text)       # walk twice = reinforcement
    with open(LIFEBOOK, 'a') as f:
        f.write(text.strip() + '\n')
    print(f"  fed: stored={r1['stored']} reinforced={r1['reinforced']+r2['reinforced']}"
          f"  age={len(ai.memory.vm)} traces")


def cmd_ask(prompt):
    out = ai.generate(prompt)
    ai.experience_cycle()
    print(f"  {out['text']}")
    print(f"  [collapse depths: {[e['w'] for e in out['events']]}]")


def cmd_talk(seed):
    words, reason = self_talk(ai, seed, max_rounds=10, tokens_per_round=10)
    print(f"  {len(words)} words — {reason or 'talked through — resonated to the end'}")
    print(f"  last said: ...{' '.join(words[-10:])}")


def cmd_solve(arg):
    if ';' in arg:
        eq, vars_str = arg.split(';', 1)
        env = {}
        for pair in vars_str.replace(',', ' ').split():
            k, v = pair.split('=')
            env[k.strip()] = int(v) if v.strip().lstrip('-').isdigit() else float(v)
    else:
        eq, env = arg, {}
    r = ai.reason(eq.strip(), **env)
    print(f"  {r.name} = {r.display[:24]}   (n_w={r.n_w}, w={r.w_level})")


def cmd_status():
    print(f"  age: {len(ai.memory.vm)} live traces")
    print(f"  signature: {ai.memory.signature()}")
    print(f"  integrity: {ai.integrity()}")


def cmd_save():
    line = ai.memory.vm.to_expression()
    with open(CHECKPOINT, 'w') as f:
        f.write(line + '\n')
    print(f"  checkpoint: {len(line)} chars (one line, α-tagged) -> memory.hcl")
    print(f"  lifebook: {os.path.getsize(LIFEBOOK) if os.path.exists(LIFEBOOK) else 0} bytes")


def cmd_load():
    global ai
    if not os.path.exists(CHECKPOINT):
        print('  no checkpoint'); return
    ai = HCLLanguageModel()                       # constructs and wakes from the one line
    rev = ai.load()
    if rev.get('revived'):
        sig = rev['signature']
        print(f"  awake from the one line (the memory) — depth {sig['depth']}, "
              f"integrity {rev['integrity']['engine_alpha_inv']}")
    else:
        print(f"  {rev.get('reason', 'no memory line')}")


COMMANDS = {'feed': cmd_feed, 'ask': cmd_ask, 'talk': cmd_talk,
            'solve': cmd_solve}

def main():
    print('HCL-AI ready. Commands: feed/ask/talk/solve <...>, status, save, load, quit')
    for raw in sys.stdin:
        raw = raw.strip()
        if not raw: continue
        if raw == 'quit': break
        if raw == 'status': cmd_status(); continue
        if raw == 'save':   cmd_save();   continue
        if raw == 'load':   cmd_load();   continue
        cmd, _, arg = raw.partition(' ')
        fn = COMMANDS.get(cmd)
        if fn and arg: fn(arg)
        else: print('  ? feed/ask/talk/solve <...>, status, save, load, quit')
    print('goodbye — the braid word remains.')

if __name__ == '__main__':
    main()
