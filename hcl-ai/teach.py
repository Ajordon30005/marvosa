"""
TEACH — learning by watching, on the substrate.
================================================
The two-cans loop with a teacher's hand. All composition, no new parts:

  self-talk     speak() → HVP signature → expand → feed back as prompt
                (composability law: output of one is valid input to the next)
  "lost"        read off the substrate, not judged from outside:
                  (a) no attractor resonates at any depth (collapse cannot
                      fire — generate returns no events), or
                  (b) the system rides ONE attractor in a circle (the same
                      trace key recurring — visible in the braid record)
  halt          free: the record IS the computation; stopping mid-run
                holds the exact state (the words so far, the live braid)
  inject        the teacher DEMONSTRATES — the lesson is expressed on the
                substrate via train() (stored on both senses, repeats
                reinforced), so watching becomes lived experience
  resume        same halted words, same loop — now the attractor exists
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'mind'))
from hcl_lm import HCLLanguageModel


def lost_reason(events):
    """Read lostness from the collapse record itself."""
    if not events:
        return 'NO ATTRACTOR — collapse cannot fire at any depth'
    keys = [e['key'] for e in events]
    for k in set(keys):
        if keys.count(k) >= 3:
            return f'CIRCLING — riding one attractor: {k[:40]}...'
    return None


def self_talk(ai, seed, max_rounds=4, tokens_per_round=8):
    """The two-cans loop. Returns (words_so_far, reason) when lost,
    or (words, None) if it talked itself to a natural stop."""
    words = seed.split()
    for r in range(max_rounds):
        out = ai.generate(' '.join(words))
        reason = lost_reason(out['events'])
        spoken = ai.speak(out['text'])          # emit as HVP signature
        words  = spoken['text'].split()         # expand → next input (bit-perfect)
        print(f"    round {r+1}: w={[e['w'] for e in out['events']] or '—'}  "
              f"text='{' '.join(words[-10:])}'")
        if reason:
            return words, reason
        ai.experience_cycle()                   # decay between rounds (lived)
    return words, None


def _demo():
    ai = HCLLanguageModel()
    # A deliberately small starting world — a baby's worth of language:
    ai.train('the braid word is the quantum state '
             'the braid word is the data ')

    print('═' * 64)
    print(' LEARNING BY WATCHING — stop mid-run, demonstrate, resume')
    print('═' * 64)

    print('\n[1] FIRST SELF-TALK (small world — it should get lost):')
    words, reason = self_talk(ai, 'the braid word')
    print(f'    >> HALTED MID-RUN: {reason}')
    print(f'    >> state held exactly at: ...{" ".join(words[-6:])!r}')

    print('\n[2] TEACHER DEMONSTRATES (the lesson is expressed on the')
    print('    substrate — watching becomes stored, reinforced experience):')
    lesson = ('the quantum state collapses to the path dominant attractor '
              'the attractor is the state of minimum mobius energy '
              'minimum mobius energy means the system found its ground '
              'the ground state closes the braid and the braid word is the data ')
    rep = ai.train(lesson)
    print(f"    stored={rep['stored']}  reinforced={rep['reinforced']}")
    rep2 = ai.train(lesson)
    print(f"    imitation pass: reinforced={rep2['reinforced']} (reinforcement in place)")

    print('\n[3] RESUME FROM THE EXACT HALTED STATE:')
    words2, reason2 = self_talk(ai, ' '.join(words[-4:]), max_rounds=3)
    print(f'    >> outcome: {reason2 or "talked through — resonated to the end"}')

    print('\n[4] THE CLIMB (same seed that got lost before):')
    out = ai.generate('the braid word')
    print(f"    '{out['text']}'")
    print(f"    collapse weights: {[e['w'] for e in out['events']]}")

    print('\n[5] WHAT IT EMBODIED (amplitudes — loud where lived):')
    amps = ai.memory.amplitudes()
    from hcl_memory import SCALE
    top = sorted(amps.items(), key=lambda kv: -kv[1])[:5]
    for k, a in top:
        print(f'    amp={a // SCALE:<8} {k[:52]}')

    print('\n[6] INTEGRITY:', ai.integrity())


if __name__ == '__main__':
    _demo()
