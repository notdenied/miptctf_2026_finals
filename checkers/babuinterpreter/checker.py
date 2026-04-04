#!/usr/bin/env python3

import hashlib
import os
import secrets
import socket
import sys
from pathlib import Path

from checklib import *

BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

from generator import (
    generate_basic_program,
    generate_error_program,
    generate_flagload_program,
    generate_flagstore_program,
)
from obfuscator import obfuscate_source


PORT = int(os.environ.get("BABUINTERPRETER_PORT", "31337"))
TIMEOUT = float(os.environ.get("BABUINTERPRETER_TIMEOUT", "10"))
BASIC_CHECK_COUNT = 10
ERROR_CHECK_COUNT = 3
HOST_OVERRIDE = os.environ.get("BABUINTERPRETER_HOST_OVERRIDE", "host.docker.internal")


def sha_seed(*parts: str) -> str:
    return hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()


def derive_storage_id(flag_id: str, vuln: str) -> str:
    return "storageID-" + sha_seed("storageID-", flag_id, vuln)[:24]


def derive_storage_key(flag_id: str, vuln: str) -> str:
    return "storageKEY-" + sha_seed("storageKEY-", flag_id, vuln)[:28]


def random_seed() -> str:
    return secrets.token_hex(16)


def random_footer() -> str:
    return secrets.token_hex(8)


def pack_private_flag_data(storage_id: str, storage_key: str) -> str:
    return storage_id + "|" + storage_key


def unpack_private_flag_data(flag_id: str, vuln: str) -> tuple[str, str]:
    parts = flag_id.split("|", 1)
    if len(parts) == 2 and parts[0] and parts[1]:
        return parts[0], parts[1]
    return derive_storage_id(flag_id, vuln), derive_storage_key(flag_id, vuln)


class CheckMachine:
    def __init__(self, checker):
        self.checker = checker

    def resolve_host(self) -> str:
        if self.checker.host in {"127.0.0.1", "localhost"}:
            return HOST_OVERRIDE
        return self.checker.host

    def recv_line(self, sock: socket.socket) -> str:
        chunks: list[bytes] = []
        while True:
            chunk = sock.recv(1)
            if not chunk:
                break
            chunks.append(chunk)
            if chunk == b"\n":
                break
        return b"".join(chunks).decode("utf-8", errors="replace")

    def run_program(self, program_text: str) -> tuple[str, str]:
        payload = program_text
        if not payload.endswith("\n"):
            payload += "\n"
        payload += "EOF\n"
        try:
            with socket.create_connection((self.resolve_host(), PORT), timeout=TIMEOUT) as sock:
                sock.settimeout(TIMEOUT)
                greeting = self.recv_line(sock)
                if not greeting:
                    self.checker.cquit(Status.DOWN, "Connection error", "service closed connection before greeting")
                sock.sendall(payload.encode("utf-8"))
                sock.shutdown(socket.SHUT_WR)
                chunks: list[bytes] = []
                while True:
                    chunk = sock.recv(65536)
                    if not chunk:
                        break
                    chunks.append(chunk)
        except OSError as exc:
            self.checker.cquit(Status.DOWN, "Connection error", repr(exc))
        return greeting.rstrip("\r\n"), b"".join(chunks).decode("utf-8", errors="replace")

    def obfuscate(self, program_text: str, seed: str) -> str:
        obfuscated, _ = obfuscate_source(program_text, seed=seed)
        return obfuscated

    def assert_output(self, label: str, actual: str, expected: str, status: Status) -> None:
        self.checker.assert_eq(actual, expected, f"{label} failed", status=status)

    def assert_contains(self, label: str, actual: str, expected_substr: str, status: Status) -> None:
        self.checker.assert_in(expected_substr, actual, f"{label} failed", status=status)

    def fail_with_program(self, public: str, details: list[str], status: Status) -> None:
        self.checker.cquit(status, public, "\n\n".join(details))

    def build_flagstore_program(self, storage_id: str, storage_key: str, flag: str, footer: str) -> str:
        source = generate_flagstore_program(
            storage_id=storage_id,
            storage_key=storage_key,
            flag=flag,
            output_text=footer,
            seed=random_seed(),
        )
        return self.obfuscate(source, random_seed())

    def build_flagload_program(self, storage_id: str, storage_key: str, footer: str) -> str:
        source = generate_flagload_program(
            storage_id=storage_id,
            storage_key=storage_key,
            output_text=footer,
            seed=random_seed(),
        )
        return self.obfuscate(source, random_seed())

    def run_basic_sanity(self) -> None:
        for _ in range(BASIC_CHECK_COUNT):
            output_text = secrets.token_hex(8)
            seed = random_seed()
            source = generate_basic_program(output_text, seed=seed)
            _, output = self.run_program(source)
            expected = output_text + "\n"
            if output != expected:
                self.fail_with_program(
                    "Basic language tests failed",
                    [
                        f"kind: basic",
                        f"seed: {seed}",
                        f"expected_stdout: {expected!r}",
                        f"actual_output: {output!r}",
                        "program:",
                        source,
                    ],
                    Status.MUMBLE,
                )

    def run_error_sanity(self) -> None:
        for _ in range(ERROR_CHECK_COUNT):
            seed = random_seed()
            source, error_text = generate_error_program(seed=seed)
            _, output = self.run_program(source)
            if error_text not in output:
                self.fail_with_program(
                    "Error language tests failed",
                    [
                        f"kind: error",
                        f"seed: {seed}",
                        f"expected_substring: {error_text!r}",
                        f"actual_output: {output!r}",
                        "program:",
                        source,
                    ],
                    Status.MUMBLE,
                )


class Checker(BaseChecker):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.mch = CheckMachine(self)

    def action(self, action, *args, **kwargs):
        try:
            super().action(action, *args, **kwargs)
        except socket.timeout as exc:
            self.cquit(Status.DOWN, "Connection timeout", repr(exc))
        except ConnectionError as exc:
            self.cquit(Status.DOWN, "Connection error", repr(exc))

    def check(self):
        self.mch.run_basic_sanity()
        self.mch.run_error_sanity()
        self.cquit(Status.OK)

    def put(self, flag_id, flag, vuln):
        storage_id = derive_storage_id(flag_id, vuln)
        storage_key = derive_storage_key(flag_id, vuln)
        footer = random_footer()
        _, output = self.mch.run_program(self.mch.build_flagstore_program(storage_id, storage_key, flag, footer))
        self.mch.assert_output("Store", output, f"{flag}\n{footer}\n", Status.MUMBLE)
        self.cquit(Status.OK, storage_id, pack_private_flag_data(storage_id, storage_key))

    def get(self, flag_id, flag, vuln):
        try:
            storage_id, storage_key = unpack_private_flag_data(flag_id, vuln)
        except ValueError as exc:
            self.cquit(Status.ERROR, "Invalid private flag data", repr(exc))
        footer = random_footer()
        _, output = self.mch.run_program(self.mch.build_flagload_program(storage_id, storage_key, footer))
        self.mch.assert_output("Load", output, f"{flag}\n{footer}\n", Status.CORRUPT)
        self.cquit(Status.OK)


if __name__ == "__main__":
    c = Checker(sys.argv[2])
    try:
        c.action(sys.argv[1], *sys.argv[3:])
    except c.get_check_finished_exception():
        cquit(Status(c.status), c.public, c.private)
