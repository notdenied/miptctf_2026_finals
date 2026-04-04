#!/usr/bin/env python3

import os
import sys
import tempfile


TERMINATOR = "EOF"
INTERPRETER = os.environ.get("BABUIN_INTERPRETER", "/service/babuinterpreter")


def main() -> int:
    print('Enter your program for babuinterpreter line by line (enter "EOF" line to finish):')
    lines: list[str] = []
    while True:
        try:
            line = input()
        except EOFError:
            print("client disconnected before terminator", file=sys.stderr)
            return 1
        if line == TERMINATOR:
            break
        lines.append(line + "\n")

    fd, path = tempfile.mkstemp(prefix="babuin-service-", suffix=".bbn")
    with os.fdopen(fd, "w", encoding="utf-8", newline="") as handle:
        handle.writelines(lines)

    os.execve(INTERPRETER, [INTERPRETER, path], dict(os.environ))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
