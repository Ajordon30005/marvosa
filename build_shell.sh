#!/usr/bin/env bash
# build_shell.sh — compile the optional shell. One cc call. Without it,
# everything runs identically on the pure-Python path.
cd "$(dirname "$0")"
cc -O2 -shared -fPIC -o shell/libmarvosa_shell.so shell/marvosa_shell.c && \
  echo "shell built: shell/libmarvosa_shell.so" || \
  echo "no C compiler — the pure path serves everything"
