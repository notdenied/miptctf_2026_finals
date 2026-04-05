#!/usr/bin/env python3

import base64
import os
import sys
import tempfile


INTERPRETER = os.environ.get("BABUIN_INTERPRETER", "/service/babuinterpreter")


def main() -> int:
    while True:
        try:
            encoded_source = input()
        except EOFError:
            return 1
        if encoded_source:
            break

    try:
        program_bytes = base64.b64decode(encoded_source.encode("ascii"), validate=True)
    except (ValueError, UnicodeEncodeError) as exc:
        print(f"invalid base64 payload: {exc}", file=sys.stderr)
        return 1

    fd, path = tempfile.mkstemp(prefix="babuin-service-", suffix=".bbn")
    with os.fdopen(fd, "w", encoding="utf-8", newline="") as handle:
        handle.write(program_bytes.decode("utf-8"))

    os.execve(INTERPRETER, [INTERPRETER, path], dict(os.environ))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
