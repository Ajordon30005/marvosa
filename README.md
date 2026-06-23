# Marvosa

**Marvosa** is a newly released open-source AI framework that challenges the necessity of floating-point math in machine learning. By using the GUHCT/HCL substrate, it achieves complex composition and exact mathematical derivation using only four integers. It offers a "Glass Box" alternative to traditional neural networks.

## 1. The Core Philosophy: Exactness Over Approximation

Contemporary AI is built on a statistical foundation of billions of floating-point weights. Marvosa is a deterministic engine of integer arithmetic, waves, and resonance. 

- **Zero Floats**: No floating-point numbers in the core math path. No rounding error, no hardware subsidy.
- **The Four Params**: Every constant (π, e, √2) and the fine-structure constant (α) are derived from four axiomatic integers: η, λ, γ, and β.
- **The Alpha-Check**: The system re-derives α⁻¹ ≈ 137 at every checkpoint. This is not a hardcoded value; it is **a** structural signature of the LQT state space. If the math is tampered with, the check fails.
- **Glass Box**: Every decision, memory, and operational state is observable and verifiable against the theory's own laws.

## 2. How It Works: The Pond Metaphor

The system's thinking is the automatic mathematical resolution of a wave field.

**The braid word is the data.** Text is converted into a physical structure—a sequence of FBits (Fixed-point Bits). A sentence becomes a braided rope of these waves. The transduction is bijective: the braid word *is* the data, and the exact original text can be regenerated from it.

**The pond is the memory.** Drop a question into the pond. The system does not look anything up—it listens. Where the question's ripples align with stored ripples, the water rises (constructive interference); where they clash, it flattens. The tallest peak *is* the answer.

**Living is reinforcement.** Every path walked gets reinforced—used memories grow louder. Every path ignored fades, and what fades far enough washes out of the active pond. The two together—self-superposition reinforcement and decay—are the whole homeostasis. **Talking is learning.**

> [!NOTE]
> **Metaphor Transparency:** In this documentation, the terms **LTP** (Long-Term Potentiation) and **LTD** (Long-Term Depression) are used as descriptive metaphors for the underlying reinforcement and decay operations. They are intended for conceptual clarity and are not part of the operational specification.

## 3. The "AI" vs. The "Apparatus"

- **The Core AI (`hcl-ai/mind/hcl_lm.py`)**: The actual HCLLanguageModel. It contains the "mind" logic: perception, memory, and the MCL collapse loop.
- **The Auto Front Door (`hcl-ai/talk.py`)**: A direct script that imports the AI class and runs it in a local loop.
- **The Testing Apparatus (`chat.sh` / `chat.py`)**: Convenience wrappers that start a background daemon to host the AI.

## 4. Repository map

| Path | Contents |
|---|---|
| `skills/hcl-pure/` | The arithmetic engine skill: the four params, FBits, braid words, COMP, MCL collapse, derived constants, quantum algorithms, proofs, porting notes, lessons. |
| `skills/guhct-memory-suite/` | The memory router plus three bundled systems: `virtual-memory-hcl` (exact topological store), `guhct-processor` (bijective byte↔HVP transducer), `guhct-living-memory` (experience-tuned composite memory). |
| `hcl-ai/engine/` | Verbatim transcriptions of the skill engines. **No mechanism in these files was authored for this project.** |
| `hcl-ai/mind/hcl_lm.py` | The arrangement: the language model as pure call-ordering of engine primitives. |
| `hcl-ai/student_daemon.py`, `tutor.py`, `tutor_batch.py` | The schoolhouse: a persistent process holding the live student, and the teacher's tools. |
| `hcl-ai/talk.py` | **The auto front door:** just type, no commands. |
| `hcl-ai/teach.py`, `feed.py`, `demo.py`, `ai.py` | Self-talk with Collatz verdicts, feeding utilities, the birth demo, the REPL. |
| `hcl-ai/grade_compose.py`, `gradebook.txt`, `prior.txt` | The receipts machinery: every taught line logged, every answer graded. |
| `hcl-ai/memory.hcl` | **The graduate.** Thirteen school years compressed to one α-tagged line. |
| `docs/01–06` | Architecture, verification, education record, composition study, realizations, conversation study. |
| `docs/07–08` | The wider six-pillar theory, and the glass-box exposition. |

## 5. Licensing

This project is dual-licensed:
1. **GNU GPLv3**: Free for everyone, but any modifications or distributions must also be open-source under the same terms.
2. **Commercial License**: For use in closed-source projects, please contact the author.

**Contact**: Anthony Jordon ([xpguhct@gmail.com](mailto:xpguhct@gmail.com))
