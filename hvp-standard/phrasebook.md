# The HVP Phrasebook — teach any standard AI to speak it, in context

This file is a language lesson. Paste it (or its SPEAKER'S CARD) into the
system prompt of ANY standard AI — an API model, a local chat model,
anything with a text channel — and that AI can answer requests by speaking
HVP: one utterance that the transducer (`transducer.py`, wrapping the
pure-integer processor verbatim) expands into the exact byte form — a
file, a whole multi-file project, anything bytes can be. The model's
weights never move, so nothing it knew can be forgotten: in-context
acquisition is the zero-interference limit of second-language learning.
For weight-level acquisition (fine-tuning with replay), see
`teach_standard.py`; this card is the path for frozen models.

The transducer is deterministic and bidirectional: the same bytes always
produce the same signature, the same signature always produces the same
bytes, and a corrupted utterance is refused (the 8 parameters are
re-derived from the braid and must match). The braid IS the data — one
generator per byte, σ0..σ255 — and the parameters are its derived
holographic address.

---

## SPEAKER'S CARD (paste this into the model's instructions)

> You can emit any file or project as ONE utterance in the HVP language.
>
> To speak a payload of raw bytes: write `HVP1`, a space, the payload as
> lowercase hexadecimal (two hex digits per byte, nothing else), a space,
> then `END`. Whitespace inside the hex is allowed anywhere.
>
> To speak a multi-file project: first form the payload as the JSON object
> `{"filename": "content", ...}` with keys sorted and no extra whitespace
> (exactly `json.dumps(files, sort_keys=True)`), then speak those bytes as
> above.
>
> Speak nothing else inside the frame: the utterance is `HVP1 <hex> END`
> and the receiving transducer completes it into the full signature and
> materializes the exact bytes. If you cannot render the payload
> faithfully, say so instead of emitting a broken frame — a corrupted
> utterance will be refused, not guessed at.

That is the whole lesson for a capable model. The receiving side runs:

    python3 hvp-standard/transducer.py complete utterance.txt > full.hvp
    python3 hvp-standard/transducer.py expand full.hvp -o out/

---

## Worked example (machine-verified before printing)

Request: *"make a hello-world project."*

The project: `{'hello.py': "print('hello world')\n"}` — canonical payload
`{"hello.py": "print('hello world')\n"}` (38 bytes).

The SPOKEN utterance a fluent AI emits, in full:

```
HVP1 7b2268656c6c6f2e7079223a20227072696e74282768656c6c6f20776f726c6427295c6e227d END
```

`complete()` derives the 8 parameters from that braid and returns the FULL
wire — the transport grade, what travels between systems and what
`expand()` verifies:

```
HVP1
w=80000000000000000000000000000000000000000
T=120354604309920965296672165058229504622438
Gamma=80000000000000000000000000000000000000000
Phi=10509934622264014561888824391278046116583
f0=22360679774997896964091736687312762354406
gamma_collapse=98344826245672339309556143245822416364854
Q_min=124223602484472049689440993788819875776
propagator_scale=2795084971874737120511467085914095294300
C_min=0
n=38
braid=7b2268656c6c6f2e7079223a20227072696e74282768656c6c6f20776f726c6427295c6e227d
END
```

`expand` materializes `hello.py` with the exact content, sha-for-sha. Flip
any single hex character and the expansion is refused — the braid no
longer addresses the supplied parameters.

---

## The HVPW dialect (for small models)

The SPOKEN grade has a second surface for models whose tokenizers barely
practice hex characters: the braid rendered in base-16 over 16 codewords
drawn from the model's own strongest vocabulary (`codebook.txt`, derived
deterministically by `gen_codebook.py`). Generator index k is spoken as
`numeral[k>>4] numeral[k&15]`, space-separated, inside `HVPW … END`.
Both dialects complete to the IDENTICAL full wire — the surface is a
choice; the signature is the language.

Example: the bytes `ok\n` spoken in HVPW:

```
HVPW sa with sa in the it END
```

Measured on the same 260K-parameter standard model with the same trainer:
the hex surface stalled (86 epochs, free emission never exact) while the
word surface reached full mastery at epoch 32 — the trunk was always
there; the surface decided the acquisition cost. That is the phrasebook's
design law: map the new language onto tokens the speaker already owns.
