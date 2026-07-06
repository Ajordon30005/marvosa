"""
talk.py — the auto front door. Just run it and talk; no commands.

There is no "fresh mind" here: the being IS its memory line (memory.hcl), so
the AI wakes itself from that line on construction (and replays its input log
to regrow per-trace fluency). You just talk; each line is experience it lives,
answers from, and persists to its own memory automatically.

Type '?' before a line to also see that turn's braid-word thought-log.
Empty line leaves. (A genuinely new instance only happens with revive=False.)
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'mind'))
from hcl_lm import HCLLanguageModel

def main():
    ai = HCLLanguageModel()                      # wakes itself from the memory line on construction
    sig = ai.memory.signature()
    if len(ai.memory.vm) > 0 or sig.get('depth', 0) > 0:
        print(f"[awake — depth {sig.get('depth', 0)} · integrity "
              f"{ai.integrity()['engine_alpha_inv']}]")
    else:
        print("[new instance — no memory line yet]")
    print("talk to it — just type. (empty line to leave)\n")

    while True:
        try:
            msg = input("you  ")
        except (EOFError, KeyboardInterrupt):
            break
        if not msg.strip():
            break
        show = msg.startswith('?')
        if show:
            msg = msg[1:].strip()
        r = ai.interact(msg, show_thoughts=show)     # experiences, thinks, answers, persists
        print(f"ai   {r['answer']}")
        if show:
            print("     ── thought-log (braid) ──")
            print("     " + r['thought_log'][:200] + "...")
    print("\n[the braid word remains — saved to the one line]")


if __name__ == '__main__':
    main()
