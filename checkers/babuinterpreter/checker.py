#!/usr/bin/env python3

import base64
import os
import random
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
DEBUG = False


def random_seed() -> str:
    return secrets.token_hex(16)


def random_storage_id() -> str:
    return "storageID-" + secrets.token_hex(12)


def random_storage_key() -> str:
    return "storageKEY-" + secrets.token_hex(14)


def pack_private_flag_data(storage_id: str, storage_key: str) -> str:
    return storage_id + "|" + storage_key


def unpack_private_flag_data(private_flag_data: str) -> tuple[str, str]:
    parts = private_flag_data.split("|", 1)
    if len(parts) == 2 and parts[0] and parts[1]:
        return parts[0], parts[1]
    raise ValueError("private flag data must contain storage_id|storage_key")


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
        payload = base64.b64encode(program_text.encode("utf-8")).decode("ascii") + "\n"
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
        if not DEBUG:
            self.checker.cquit(status, public)
        self.checker.cquit(status, public, "\n\n".join(details))

    def build_flagstore_program(self, storage_id: str, storage_key: str, flag: str) -> str:
        source = generate_flagstore_program(
            storage_id=storage_id,
            storage_key=storage_key,
            flag=flag,
            seed=random_seed(),
        )
        return self.obfuscate(source, random_seed())

    def build_flagload_program(self, storage_id: str, storage_key: str) -> str:
        source = generate_flagload_program(
            storage_id=storage_id,
            storage_key=storage_key,
            seed=random_seed(),
        )
        return self.obfuscate(source, random_seed())

    def run_basic_sanity_case(self) -> None:
        output_text = secrets.token_hex(8)
        seed = random_seed()
        source = generate_basic_program(output_text, seed=seed)
        _, output = self.run_program(source)
        expected = output_text + "\n"
        if output != expected:
            self.fail_with_program(
                "Language tests failed",
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

    def run_error_sanity_case(self) -> None:
        seed = random_seed()
        source, error_text = generate_error_program(seed=seed)
        _, output = self.run_program(source)
        if error_text not in output:
            self.fail_with_program(
                "Language tests failed",
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

    def run_mixed_sanity(self) -> None:
        jobs = (["basic"] * BASIC_CHECK_COUNT) + (["error"] * ERROR_CHECK_COUNT)
        random.shuffle(jobs)
        for job in jobs:
            if job == "basic":
                self.run_basic_sanity_case()
            else:
                self.run_error_sanity_case()


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
        self.mch.run_mixed_sanity()
        self.cquit(Status.OK)

    def fail_storage_io(
        self,
        public: str,
        status: Status,
        expected: str,
        actual: str,
        storage_id: str,
        storage_key: str,
        program_text: str,
        extra: list[str] | None = None,
    ) -> None:
        details = [
            f"expected_stdout: {expected!r}",
            f"actual_output: {actual!r}",
            f"storage_id: {storage_id}",
            f"storage_key: {storage_key}",
        ]
        if extra:
            details.extend(extra)
        details.extend(["program:", program_text])
        self.mch.fail_with_program(public, details, status)

    def put(self, flag_id, flag, vuln):
        del flag_id, vuln
        storage_id = random_storage_id()
        storage_key = random_storage_key()
        program_text = self.mch.build_flagstore_program(storage_id, storage_key, flag)
        _, output = self.mch.run_program(program_text)
        expected = f"{flag}\n"
        if output != expected:
            self.fail_storage_io(
                public="Store failed",
                status=Status.MUMBLE,
                expected=expected,
                actual=output,
                storage_id=storage_id,
                storage_key=storage_key,
                program_text=program_text,
            )
        self.cquit(Status.OK, storage_id, pack_private_flag_data(storage_id, storage_key))

    def get(self, flag_id, flag, vuln):
        del vuln
        try:
            storage_id, storage_key = unpack_private_flag_data(flag_id)
        except ValueError as exc:
            self.cquit(Status.ERROR, "Invalid private flag data", repr(exc))
        program_text = self.mch.build_flagload_program(storage_id, storage_key)
        _, output = self.mch.run_program(program_text)
        expected = f"{flag}\n"
        if output != expected:
            self.fail_storage_io(
                public="Load failed",
                status=Status.CORRUPT,
                expected=expected,
                actual=output,
                storage_id=storage_id,
                storage_key=storage_key,
                program_text=program_text,
                extra=[f"private_flag_data: {flag_id!r}"],
            )
        self.cquit(Status.OK)


if __name__ == "__main__":
    c = Checker(sys.argv[2])
    try:
        c.action(sys.argv[1], *sys.argv[3:])
    except c.get_check_finished_exception():
        cquit(Status(c.status), c.public, c.private)
