"""
demo_one_go.py — an ENTIRE PROJECT, IN GO, IN ONE GO.

The claim, executed literally: a standard AI answers a request with ONE
HVP utterance; the transducer completes and verifies it; the exact bytes
come back as a whole multi-file Go project — which then COMPILES and RUNS.
Nothing streams. The utterance is the project.

The speaker here is the harness pattern any standard AI uses (the
repo's own law, mind/hcl_lm.py speak(): the mind composes the content,
the organ voices it as the signature): content -> spoken utterance ->
complete() -> FULL wire -> expand -> files -> `go build` -> execute.
The same FULL wire also demonstrates the receiving direction of the
phrasebook: what an API model taught the speaker's card would emit is
exactly the SPOKEN line printed below.

    python3 hvp-standard/demo_one_go.py
"""
import sys, os, subprocess, hashlib

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
import transducer as T

# The project a speaker composes: a real Go module, three files.
PROJECT = {
    'go.mod': "module hvpdemo\n\ngo 1.22\n",
    'main.go': (
        "package main\n\n"
        "import (\n\t\"fmt\"\n\t\"hvpdemo/braid\"\n)\n\n"
        "func main() {\n"
        "\tfmt.Println(\"hello from a project spoken as ONE HVP "
        "utterance\")\n"
        "\tfmt.Printf(\"alpha seal: %d\\n\", braid.AlphaInverse())\n"
        "}\n"),
    'braid/braid.go': (
        "package braid\n\n"
        "// AlphaInverse returns the integer part of the repo's seal.\n"
        "func AlphaInverse() int {\n\treturn 137\n}\n"),
}


def main():
    raw = T.project_to_bytes(PROJECT)
    spoken = T.spoken_hex(raw)
    print(f"[speak] the whole Go project as ONE utterance: "
          f"{len(spoken)} chars, {len(PROJECT)} files, {len(raw)} bytes")
    print(f"        {spoken[:72]}…END")

    full = T.complete(spoken)                  # the vocal cords: derive
    outdir = '/tmp/hvp_one_go'
    names = T.expand_project(full, outdir)     # the processor: verify
    sha = all(hashlib.sha256(
        open(os.path.join(outdir, n), 'rb').read()).hexdigest()
        == hashlib.sha256(PROJECT[n].encode()).hexdigest() for n in PROJECT)
    print(f"[expand] {names} materialized, sha-exact={sha}")

    r = subprocess.run(['go', 'build', '-o', 'hvpdemo', '.'],
                       cwd=outdir, capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    r = subprocess.run(['./hvpdemo'], cwd=outdir,
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    print(f"[run] compiled and executed:\n" +
          '\n'.join('        ' + l for l in r.stdout.strip().splitlines()))
    assert 'alpha seal: 137' in r.stdout
    print("[verdict] one utterance -> whole Go project -> builds -> runs")


if __name__ == '__main__':
    main()
