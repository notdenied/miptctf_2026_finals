#!/usr/bin/env python3
import argparse
import hashlib
import random
import secrets
import sys
from dataclasses import dataclass
from pathlib import Path


KEYWORDS = {
    "jungle",
    "babuin",
    "banana",
    "in",
    "hoard",
    "sniff",
    "shriek",
    "swing",
    "fling",
    "scamper",
    "match",
    "as",
    "truth",
    "lie",
}

BUILTINS = {
    "storage",
    "store",
    "load",
    "type",
    "hash",
    "reverse",
    "rotate",
    "xor",
    "contains",
    "find",
    "join",
    "split",
    "eval",
    "slice",
    "insert",
    "remove",
    "push",
    "pop",
    "ord",
    "chr",
    "exit",
    "input",
    "length",
    "int",
    "float",
    "string",
    "bool",
    "format",
    "print",
    "panic",
}

RESERVED = KEYWORDS | BUILTINS | {"_"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate a larger randomized babuin program that preserves behavior while making source stubbing harder"
    )
    parser.add_argument("--input", required=True, help="Input .bbn source")
    parser.add_argument("--output", help="Output .bbn source; stdout when omitted")
    parser.add_argument(
        "--seed",
        help="Deterministic seed. If omitted, a random seed is generated and printed to stderr",
    )
    parser.add_argument(
        "--junk-records",
        type=int,
        default=2,
        help="How many decoy jungle declarations to emit",
    )
    parser.add_argument(
        "--junk-functions",
        type=int,
        default=4,
        help="How many decoy helper functions to emit",
    )
    return parser.parse_args()


def split_comment(line: str) -> tuple[str, str]:
    in_string = False
    escape = False
    for i in range(len(line) - 1):
        c = line[i]
        if in_string:
            if escape:
                escape = False
            elif c == "\\":
                escape = True
            elif c == '"':
                in_string = False
            continue
        if c == '"':
            in_string = True
            continue
        if c == "/" and line[i + 1] == "/":
            return line[:i], line[i:]
    return line, ""


def read_number_token(text: str, start: int) -> int:
    i = start
    if text[i] == "0" and i + 1 < len(text):
        n = text[i + 1]
        if n in "xX":
            i += 2
            while i < len(text) and text[i].lower() in "0123456789abcdef":
                i += 1
            return i
        if n in "oO":
            i += 2
            while i < len(text) and text[i] in "01234567":
                i += 1
            return i
        if n in "bB":
            i += 2
            while i < len(text) and text[i] in "01":
                i += 1
            return i
    while i < len(text) and text[i].isdigit():
        i += 1
    if i < len(text) and text[i] == ".":
        i += 1
        while i < len(text) and text[i].isdigit():
            i += 1
    if i < len(text) and text[i] in "eE":
        i += 1
        if i < len(text) and text[i] in "+-":
            i += 1
        while i < len(text) and text[i].isdigit():
            i += 1
    return i


def parse_babuin_string(raw: str) -> tuple[str, bool]:
    assert raw.startswith('"') and raw.endswith('"')
    i = 1
    out: list[str] = []
    has_interpolation = False
    while i < len(raw) - 1:
        c = raw[i]
        if c == "\\":
            if i + 1 >= len(raw) - 1:
                raise ValueError("unterminated string escape")
            nxt = raw[i + 1]
            if nxt == "n":
                out.append("\n")
            elif nxt == "t":
                out.append("\t")
            elif nxt == "r":
                out.append("\r")
            elif nxt == "\\":
                out.append("\\")
            elif nxt == '"':
                out.append('"')
            else:
                out.append(nxt)
            i += 2
            continue
        if c == "$" and i + 1 < len(raw) - 1 and raw[i + 1] == "{":
            has_interpolation = True
        out.append(c)
        i += 1
    return "".join(out), has_interpolation


def stringify_babuin_text(value: str) -> str:
    parts: list[str] = ['"']
    for c in value:
        if c == "\n":
            parts.append("\\n")
        elif c == "\t":
            parts.append("\\t")
        elif c == "\r":
            parts.append("\\r")
        elif c == "\\":
            parts.append("\\\\")
        elif c == '"':
            parts.append('\\"')
        else:
            parts.append(c)
    parts.append('"')
    return "".join(parts)


def fnv1a_hex(text: str) -> str:
    value = 1469598103934665603
    for byte in text.encode("utf-8"):
        value ^= byte
        value = (value * 1099511628211) & 0xFFFFFFFFFFFFFFFF
    return f"{value:016x}"


def is_ident_start(c: str) -> bool:
    return c.isalpha() or c == "_"


def is_ident_char(c: str) -> bool:
    return c.isalnum() or c == "_"


@dataclass
class NameFactory:
    rng: random.Random
    prefix: str
    used: set[str]

    def fresh(self, hint: str) -> str:
        del hint
        while True:
            suffix = "".join(self.rng.choice("abcdefghijklmnopqrstuvwxyz0123456789") for _ in range(12))
            name = self.prefix + suffix
            if name not in self.used and name not in RESERVED:
                self.used.add(name)
                return name


class Obfuscator:
    def __init__(self, source: str, rng: random.Random, junk_records: int, junk_functions: int):
        self.source = source
        self.rng = rng
        self.source_line_count = max(1, len(source.splitlines()))
        self.used_names = self.collect_existing_names()
        self.record_names = self.collect_record_names()
        self.prefix = f"_{''.join(self.rng.choice('abcdefghijklmnopqrstuvwxyz0123456789') for _ in range(10))}_"
        self.name_factory = NameFactory(self.rng, self.prefix, set(self.used_names))
        self.rename_map: dict[str, str] = {}
        self.junk_records, self.junk_functions = self.scale_junk_counts(junk_records, junk_functions)
        self.original_main_name = self.name_factory.fresh("main_real")
        self.relay_type = self.name_factory.fresh("relay_shape")
        self.relay_box = self.name_factory.fresh("relay_box")
        self.relay_pick = self.name_factory.fresh("relay_pick")
        self.relay_clone = self.name_factory.fresh("relay_clone")
        self.relay_spin = self.name_factory.fresh("relay_spin")
        self.relay_pushpop = self.name_factory.fresh("relay_pushpop")
        self.relay_gate = self.name_factory.fresh("relay_gate")
        self.relay_loop = self.name_factory.fresh("relay_loop")
        self.relay_match = self.name_factory.fresh("relay_match")
        self.relay_slice = self.name_factory.fresh("relay_slice")
        self.relay_state = self.name_factory.fresh("relay_state")

    def scale_junk_counts(self, base_records: int, base_functions: int) -> tuple[int, int]:
        target_multiplier = min(120, max(35, 160 // self.source_line_count))
        target_lines = min(self.source_line_count * target_multiplier, self.source_line_count * 180)
        wrapper_lines = 150
        transformed_source_lines = self.source_line_count
        remaining = max(0, target_lines - wrapper_lines - transformed_source_lines)
        extra_function_lines = 9
        extra_record_lines = 5
        scaled_functions = max(base_functions, min(40, remaining // extra_function_lines))
        remaining_after_functions = max(0, remaining - scaled_functions * extra_function_lines)
        scaled_records = max(base_records, min(16, remaining_after_functions // extra_record_lines))
        return scaled_records, scaled_functions

    def collect_existing_names(self) -> set[str]:
        names: set[str] = set()
        for line in self.source.splitlines():
            code, _ = split_comment(line)
            i = 0
            while i < len(code):
                if code[i] == '"':
                    i = self.read_string_token(code, i)[1]
                    continue
                if is_ident_start(code[i]):
                    j = i + 1
                    while j < len(code) and is_ident_char(code[j]):
                        j += 1
                    names.add(code[i:j])
                    i = j
                    continue
                i += 1
        return names

    def collect_record_names(self) -> set[str]:
        records: set[str] = set()
        for raw_line in self.source.splitlines():
            stripped = raw_line.lstrip("\t")
            if raw_line.startswith("\t"):
                continue
            code, _ = split_comment(stripped)
            code = code.strip()
            if not code.startswith("jungle "):
                continue
            name = code[len("jungle ") :].strip()
            if name:
                records.add(name)
        return records

    def read_string_token(self, text: str, start: int) -> tuple[str, int]:
        i = start + 1
        escape = False
        while i < len(text):
            c = text[i]
            if escape:
                escape = False
            elif c == "\\":
                escape = True
            elif c == '"':
                return text[start : i + 1], i + 1
            i += 1
        raise ValueError("unterminated string literal")

    def mapped_name(self, name: str) -> str:
        if name in RESERVED:
            return name
        if name in self.record_names:
            return name
        if name == "main":
            return self.original_main_name
        mapped = self.rename_map.get(name)
        if mapped is None:
            mapped = self.name_factory.fresh("id")
            self.rename_map[name] = mapped
        return mapped

    def obfuscate_int(self, value: int, depth: int = 0) -> str:
        if depth >= 2 or abs(value) <= 3:
            return str(value)
        choice = self.rng.randrange(4)
        if choice == 0:
            delta = self.rng.randint(3, 31)
            return f"(({self.obfuscate_int(value + delta, depth + 1)}) - ({self.obfuscate_int(delta, depth + 1)}))"
        if choice == 1:
            delta = self.rng.randint(3, 31)
            return f"(({self.obfuscate_int(value - delta, depth + 1)}) + ({self.obfuscate_int(delta, depth + 1)}))"
        if choice == 2:
            mul = self.rng.randint(2, 6)
            widened = value * mul
            if abs(widened) < (1 << 60):
                return f"(({self.obfuscate_int(widened, depth + 1)}) / ({mul}))"
        left = self.rng.randint(-40, 40)
        right = value - left
        return f"(({self.obfuscate_int(left, depth + 1)}) + ({self.obfuscate_int(right, depth + 1)}))"

    def encode_string(self, value: str) -> str:
        if not value:
            return 'join([], "")'
        items = [f"chr({self.obfuscate_int(ord(c))})" for c in value]
        return f'join([{", ".join(items)}], "")'

    def maybe_obfuscate_number(self, token: str) -> str:
        lowered = token.lower()
        if any(ch in lowered for ch in ".e") or lowered.startswith("0x") or lowered.startswith("0o") or lowered.startswith("0b"):
            try:
                value = int(token, 0)
            except ValueError:
                return token
            return self.obfuscate_int(value)
        try:
            value = int(token, 10)
        except ValueError:
            return token
        return self.obfuscate_int(value)

    def escape_string_chunk(self, text: str) -> str:
        out: list[str] = []
        for c in text:
            if c == "\n":
                out.append("\\n")
            elif c == "\t":
                out.append("\\t")
            elif c == "\r":
                out.append("\\r")
            elif c == "\\":
                out.append("\\\\")
            elif c == '"':
                out.append('\\"')
            else:
                out.append(c)
        return "".join(out)

    def rewrite_interpolated_string(self, raw: str) -> str:
        inner, _ = parse_babuin_string(raw)
        out: list[str] = ['"']
        i = 0
        while i < len(inner):
            c = inner[i]
            if c == "$" and i + 1 < len(inner) and inner[i + 1] == "{":
                expr, next_i = self.extract_interpolation(inner, i + 2)
                out.append("${")
                out.append(self.escape_string_chunk(self.obfuscate_code(expr)))
                out.append("}")
                i = next_i
                continue
            out.append(self.escape_string_chunk(c))
            i += 1
        out.append('"')
        return "".join(out)

    def extract_interpolation(self, text: str, start: int) -> tuple[str, int]:
        depth_paren = 0
        depth_bracket = 0
        depth_brace = 0
        in_string = False
        escape = False
        i = start
        while i < len(text):
            c = text[i]
            if in_string:
                if escape:
                    escape = False
                elif c == "\\":
                    escape = True
                elif c == '"':
                    in_string = False
                i += 1
                continue
            if c == '"':
                in_string = True
                i += 1
                continue
            if c == "(":
                depth_paren += 1
            elif c == ")":
                depth_paren -= 1
            elif c == "[":
                depth_bracket += 1
            elif c == "]":
                depth_bracket -= 1
            elif c == "{":
                depth_brace += 1
            elif c == "}":
                if depth_paren == 0 and depth_bracket == 0 and depth_brace == 0:
                    return text[start:i], i + 1
                depth_brace -= 1
            i += 1
        raise ValueError("unterminated string interpolation")

    def obfuscate_code(self, code: str) -> str:
        out: list[str] = []
        i = 0
        while i < len(code):
            c = code[i]
            if c == '"':
                raw, i = self.read_string_token(code, i)
                decoded, has_interpolation = parse_babuin_string(raw)
                if has_interpolation:
                    out.append(self.rewrite_interpolated_string(raw))
                else:
                    out.append(self.encode_string(decoded))
                continue
            if is_ident_start(c):
                j = i + 1
                while j < len(code) and is_ident_char(code[j]):
                    j += 1
                name = code[i:j]
                out.append(self.mapped_name(name))
                i = j
                if name == "eval":
                    k = i
                    while k < len(code) and code[k] == " ":
                        k += 1
                    if k < len(code) and code[k] == "(":
                        m = k + 1
                        while m < len(code) and code[m] == " ":
                            m += 1
                        if m < len(code) and code[m] == '"':
                            out.append(code[i:k])
                            out.append("(")
                            out.append(code[k + 1 : m])
                            raw, m = self.read_string_token(code, m)
                            decoded, _ = parse_babuin_string(raw)
                            out.append(stringify_babuin_text(self.obfuscate_code(decoded)))
                            i = m
                continue
            if c.isdigit():
                j = read_number_token(code, i)
                out.append(self.maybe_obfuscate_number(code[i:j]))
                i = j
                continue
            out.append(c)
            i += 1
        return "".join(out)

    def split_statements(self, code: str) -> list[str]:
        parts: list[str] = []
        start = 0
        i = 0
        in_string = False
        escape = False
        while i < len(code):
            c = code[i]
            if in_string:
                if escape:
                    escape = False
                elif c == "\\":
                    escape = True
                elif c == '"':
                    in_string = False
                i += 1
                continue
            if c == '"':
                in_string = True
                i += 1
                continue
            if c == ";":
                parts.append(code[start:i])
                start = i + 1
            i += 1
        parts.append(code[start:])
        return parts

    def find_top_level_assignment(self, text: str) -> int:
        depth_paren = 0
        depth_bracket = 0
        depth_brace = 0
        in_string = False
        escape = False
        for i, c in enumerate(text):
            if in_string:
                if escape:
                    escape = False
                elif c == "\\":
                    escape = True
                elif c == '"':
                    in_string = False
                continue
            if c == '"':
                in_string = True
                continue
            if c == "(":
                depth_paren += 1
                continue
            if c == ")":
                depth_paren -= 1
                continue
            if c == "[":
                depth_bracket += 1
                continue
            if c == "]":
                depth_bracket -= 1
                continue
            if c == "{":
                depth_brace += 1
                continue
            if c == "}":
                depth_brace -= 1
                continue
            if depth_paren != 0 or depth_bracket != 0 or depth_brace != 0:
                continue
            if c != "=":
                continue
            prev = text[i - 1] if i > 0 else ""
            nxt = text[i + 1] if i + 1 < len(text) else ""
            if prev in "=!<>" or nxt == "=":
                continue
            return i
        return -1

    def wrap_expr(self, expr: str) -> str:
        wrapped = expr.strip()
        chain = [
            self.relay_box,
            self.relay_pick,
            self.relay_clone,
            self.relay_spin,
            self.relay_pushpop,
            self.relay_gate,
            self.relay_loop,
            self.relay_match,
            self.relay_slice,
            self.relay_state,
        ]
        self.rng.shuffle(chain)
        if len(wrapped) < 16:
            depth = 5
        elif len(wrapped) < 48:
            depth = 4
        else:
            depth = 3
        for i in range(depth):
            wrapped = f"{chain[i]}({wrapped})"
        return wrapped

    def rewrite_statement_shape(self, code: str) -> str:
        stripped = code.strip()
        if not stripped:
            return code
        leading = code[: len(code) - len(code.lstrip(" "))]
        trailing = code[len(code.rstrip(" ")) :]
        core = code[len(leading) : len(code) - len(trailing) if trailing else len(code)]
        core_stripped = core.strip()

        control_prefixes = ("sniff ", "swing ", "match ", "as ", "shriek", "jungle ", "babuin ")
        if core_stripped.startswith(control_prefixes):
            return code

        if core_stripped.startswith("banana "):
            assign_idx = self.find_top_level_assignment(core_stripped)
            if assign_idx != -1:
                lhs = core_stripped[:assign_idx].rstrip()
                rhs = core_stripped[assign_idx + 1 :].strip()
                return f"{leading}{lhs} = {self.wrap_expr(rhs)}{trailing}"
            return code

        if core_stripped.startswith("hoard "):
            expr = core_stripped[len("hoard ") :].strip()
            return f"{leading}hoard {self.wrap_expr(expr)}{trailing}"

        assign_idx = self.find_top_level_assignment(core_stripped)
        if assign_idx != -1:
            lhs = core_stripped[:assign_idx].rstrip()
            rhs = core_stripped[assign_idx + 1 :].strip()
            return f"{leading}{lhs} = {self.wrap_expr(rhs)}{trailing}"
        return code

    def transform_source(self) -> str:
        lines: list[str] = []
        for raw_line in self.source.splitlines():
            prefix_len = len(raw_line) - len(raw_line.lstrip("\t"))
            indent = raw_line[:prefix_len]
            rest = raw_line[prefix_len:]
            code, comment = split_comment(rest)
            if not code and comment:
                lines.append(raw_line)
                continue
            transformed_parts: list[str] = []
            for part in self.split_statements(code):
                obfuscated = self.obfuscate_code(part)
                transformed_parts.append(self.rewrite_statement_shape(obfuscated))
            transformed = ";".join(transformed_parts)
            lines.append(indent + transformed + comment)
        return "\n".join(lines) + ("\n" if self.source.endswith("\n") else "")

    def guard_numbers(self) -> list[int]:
        digest = hashlib.sha256(self.source.encode("utf-8")).digest()
        numbers = [b + 1 for b in digest[:16]]
        numbers.extend(((digest[i] << 1) ^ digest[31 - i]) % 251 + 3 for i in range(8))
        return numbers

    def compute_guard(self, data: list[int], base: int, salt: int, mod: int) -> int:
        acc = base
        for idx, value in enumerate(data):
            step = idx + 1
            expr = ((acc + value) * (step + 3) - value)
            if expr < 0:
                expr = -expr
            expr = expr + step * 17 + salt
            expr %= mod
            if expr % 5 == 0:
                expr = expr // 5 + idx
            else:
                expr = expr + idx * 11
            expr %= mod
            acc = expr
        return acc

    def compute_feature_guard(self, seed_text: str, mod: int) -> int:
        chars = list(seed_text)
        nums: list[int] = []
        for idx, ch in enumerate(chars):
            value = ord(ch)
            if idx % 3 == 0:
                nums.append(value + idx)
                continue
            nums.insert(len(nums), value - idx)

        tail = nums.pop()
        nums.insert(0, tail)
        middle = nums.pop(1)
        nums.insert(1, middle)
        tiny = nums[: len(nums)]
        hashed = fnv1a_hex(fnv1a_hex(seed_text))
        glyphs = [f"{i}{chr((value % 26) + 65)}" for i, value in enumerate(tiny) if i < 4]
        joined = ":".join(glyphs)
        probe = [0, "", str(len(seed_text))]
        if "array" == "array" and (":" in "0:truth" or "truth" in "0:truth"):
            probe_acc = tiny[0] + tiny[1] + tiny[2] + len(glyphs) + joined.find(":")
            if probe_acc >= 0 and ("array" in "array" or "string" in "array"):
                probe = [probe_acc, joined, str(len(seed_text))]

        acc = len(seed_text)
        acc += seed_text.find(chars[0])
        acc += len(tiny)
        acc += ord(hashed[0])
        acc += hashed.find(hashed[-1])
        acc += 7 if tiny[0] in tiny else -11
        acc += tiny.index(tiny[0])
        acc += probe[0] + int(probe[2])
        acc += len(probe[1].split(":"))

        for idx, item in enumerate(tiny):
            acc = eval(f"{acc} + {item} + {idx}")
            if idx % 2 == 0:
                acc = acc + int(float(str(item)))
                continue
            acc = acc - int(float(str(idx)))
            if acc > 2000 and idx > 6:
                break
        return acc % mod

    def render_junk_records(self) -> list[str]:
        lines: list[str] = []
        for _ in range(self.junk_records):
            record_name = self.name_factory.fresh("shape")
            fields = [self.name_factory.fresh("field") for _ in range(3)]
            lines.append(f"jungle {record_name}")
            for field in fields:
                lines.append(f"\t{field}")
            lines.append("")
        return lines

    def render_junk_functions(self) -> list[str]:
        lines: list[str] = []
        for _ in range(self.junk_functions):
            func = self.name_factory.fresh("junk")
            a = self.name_factory.fresh("arg")
            b = self.name_factory.fresh("tmp")
            c = self.name_factory.fresh("idx")
            d = self.name_factory.fresh("item")
            seed = self.rng.randint(9, 77)
            payload = [self.rng.randint(5, 60) for _ in range(self.rng.randint(4, 8))]
            lines.append(f"babuin {func}({a})")
            lines.append(f"\tbanana {b} = {self.obfuscate_int(seed)}")
            lines.append(f"\tswing {c}, {d} in [{', '.join(self.obfuscate_int(x) for x in payload)}]")
            lines.append(f"\t\t{b} = {b} + ({d} * ({c} + 1)) + {a}")
            lines.append(f"\t\tsniff ({b} % 3) == 0")
            lines.append(f"\t\t\t{b} = {b} / 3 + {c}")
            lines.append(f"\t\tshriek")
            lines.append(f"\t\t\t{b} = {b} + {c} + {self.obfuscate_int(seed // 2 + 1)}")
            lines.append(f"\thoard {b}")
            lines.append("")
        return lines

    def render_alias_chain(self, target: str, argc: int, depth: int | None = None) -> tuple[list[str], str]:
        chain_depth = depth if depth is not None else self.rng.randint(1, 3)
        current = target
        lines: list[str] = []
        for _ in range(chain_depth):
            alias = self.name_factory.fresh("alias")
            args = [self.name_factory.fresh("arg") for _ in range(argc)]
            lines.append(f"babuin {alias}({', '.join(args)})")
            if args:
                lines.append(f"\thoard {current}({', '.join(args)})")
            else:
                lines.append(f"\thoard {current}()")
            lines.append("")
            current = alias
        return lines, current

    def render_wrapper(self) -> str:
        relay_value = self.name_factory.fresh("relay_value")
        relay_record = self.name_factory.fresh("relay_record")
        relay_array = self.name_factory.fresh("relay_array")
        relay_first = self.name_factory.fresh("relay_first")
        relay_second = self.name_factory.fresh("relay_second")
        relay_out = self.name_factory.fresh("relay_out")
        relay_boxed = self.name_factory.fresh("relay_boxed")
        relay_third = self.name_factory.fresh("relay_third")
        relay_tmp = self.name_factory.fresh("relay_tmp")
        relay_kind = self.name_factory.fresh("relay_kind")
        relay_idx = self.name_factory.fresh("relay_idx")
        relay_seen = self.name_factory.fresh("relay_seen")
        relay_inner = self.name_factory.fresh("relay_inner")
        relay_pool = self.name_factory.fresh("relay_pool")
        relay_cut = self.name_factory.fresh("relay_cut")
        relay_state_idx = self.name_factory.fresh("relay_state_idx")
        relay_state_out = self.name_factory.fresh("relay_state_out")
        relay_state_limit = self.name_factory.fresh("relay_state_limit")
        relay_phase = self.name_factory.fresh("relay_phase")
        relay_result = self.name_factory.fresh("relay_result")
        relay_block = self.name_factory.fresh("relay_block")
        relay_value_box = self.name_factory.fresh("relay_value_box")
        meta_type = self.name_factory.fresh("meta")
        bundle_type = self.name_factory.fresh("bundle")
        prepare = self.name_factory.fresh("prepare")
        twist = self.name_factory.fresh("twist")
        compress = self.name_factory.fresh("compress")
        mutate = self.name_factory.fresh("mutate")
        fold = self.name_factory.fresh("fold")
        guard = self.name_factory.fresh("guard")
        encoded = self.name_factory.fresh("encoded")
        seed_text = self.name_factory.fresh("seed")
        chars = self.name_factory.fresh("chars")
        data_name = self.name_factory.fresh("data")
        meta = self.name_factory.fresh("meta_inst")
        bundle = self.name_factory.fresh("bundle_inst")
        acc = self.name_factory.fresh("acc")
        idx = self.name_factory.fresh("idx")
        item = self.name_factory.fresh("item")
        expr = self.name_factory.fresh("expr")
        text = self.name_factory.fresh("text")
        parts = self.name_factory.fresh("parts")
        left = self.name_factory.fresh("left")
        right = self.name_factory.fresh("right")
        tag = self.name_factory.fresh("tag")
        values = self.name_factory.fresh("values")
        seen = self.name_factory.fresh("seen")
        hashed = self.name_factory.fresh("hashed")
        probe = self.name_factory.fresh("probe")
        glyphs = self.name_factory.fresh("glyphs")
        joined = self.name_factory.fresh("joined")
        first = self.name_factory.fresh("first")
        second = self.name_factory.fresh("second")
        third = self.name_factory.fresh("third")
        probe_acc = self.name_factory.fresh("probe_acc")
        flag = self.name_factory.fresh("flag")
        left_text = self.name_factory.fresh("left_text")
        head = self.name_factory.fresh("head")
        mid = self.name_factory.fresh("mid")
        tail = self.name_factory.fresh("tail")
        probe_text = self.name_factory.fresh("probe_text")
        probe_num = self.name_factory.fresh("probe_num")
        probe_size = self.name_factory.fresh("probe_size")
        limit = self.name_factory.fresh("limit")
        popped = self.name_factory.fresh("popped")
        removed = self.name_factory.fresh("removed")
        pieces = self.name_factory.fresh("pieces")
        rebuilt = self.name_factory.fresh("rebuilt")
        kind = self.name_factory.fresh("kind")
        numeric = self.name_factory.fresh("numeric")
        loopprobe = self.name_factory.fresh("loopprobe")
        loop_acc = self.name_factory.fresh("loop_acc")
        loop_idx = self.name_factory.fresh("loop_idx")
        loop_item = self.name_factory.fresh("loop_item")
        guard_probe = self.name_factory.fresh("guard_probe")
        mod = self.rng.randint(200_003, 900_001)
        template = self.rng.randrange(8)
        base_template = template % 2
        helper_variant = (template // 2) % 2
        guard_variant = template // 4
        seed_text_value = hashlib.sha256((self.prefix + self.source).encode("utf-8")).hexdigest()[:18]
        expected = self.compute_feature_guard(seed_text_value, mod)
        opaque_expected = expected % 17
        array_text = self.encode_string("array")
        truth_text = self.encode_string("truth")
        colon_text = self.encode_string(":")
        string_text = self.encode_string("string")
        common_prefix = [
            f"jungle {self.relay_type}",
            f"\t{relay_value}",
            f"\t{relay_array}",
            "",
            f"babuin {self.relay_box}({relay_value})",
            f"\tbanana {relay_array} = reverse(reverse([{relay_value}]))",
            f"\thoard rotate({relay_array}, length({relay_array}))[0]",
            "",
            f"babuin {self.relay_pick}({relay_value})",
            f"\tmatch [{relay_value}, truth]",
            f"\t\tas [{relay_first}, truth]",
            f"\t\t\thoard {relay_first}",
            f"\t\tshriek",
            f"\t\t\thoard {relay_value}",
            "",
            f"babuin {self.relay_clone}({relay_value})",
            f"\tbanana {relay_record} = {self.relay_type}()",
            f"\t{relay_record}.{relay_value} = {relay_value}",
            f"\t{relay_record}.{relay_array} = [{relay_value}]",
            f"\tbanana {relay_out} = {relay_record}.{relay_value}",
            f"\tbanana {relay_boxed} = {relay_record}.{relay_array}",
            f"\tbanana [{relay_second}] = {relay_boxed}",
            f"\thoard {self.relay_pick}({self.relay_box}({relay_out}))",
            "",
            f"babuin {self.relay_spin}({relay_value})",
            f"\tbanana {relay_array} = rotate([{relay_value}], length([{relay_value}]))",
            f"\tinsert({relay_array}, 0, pop({relay_array}))",
            f"\tmatch reverse(reverse({relay_array}))",
            f"\t\tas [{relay_third}]",
            f"\t\t\thoard {relay_third}",
            f"\t\tshriek",
            f"\t\t\thoard {relay_value}",
            "",
            f"babuin {self.relay_pushpop}({relay_value})",
            f"\tbanana {relay_array} = []",
            f"\tpush({relay_array}, {relay_value})",
            f"\tpush({relay_array}, {relay_value})",
            f"\tbanana {relay_tmp} = remove({relay_array}, 0)",
            f"\tinsert({relay_array}, 0, {relay_tmp})",
            f"\thoard pop({relay_array})",
            "",
            f"babuin {self.relay_gate}({relay_value})",
            f"\tbanana {relay_kind} = type([{relay_value}])",
            f"\tsniff bool({relay_kind} == {array_text}) && contains({relay_kind}, join([chr({self.obfuscate_int(ord('a'))})], \"\"))",
            f"\t\thoard {self.relay_spin}({self.relay_pushpop}({relay_value}))",
            f"\tshriek",
            f"\t\thoard {self.relay_clone}({relay_value})",
            "",
            f"babuin {self.relay_loop}({relay_value})",
            f"\tbanana {relay_array} = rotate([{relay_value}], {self.obfuscate_int(1)})",
            f"\tbanana {relay_phase} = {self.obfuscate_int(0)}",
            f"\tbanana {relay_idx} = {self.obfuscate_int(0)}",
            f"\tbanana {relay_seen} = {relay_value}",
            f"\tswing truth",
            f"\t\tsniff {relay_phase} == {self.obfuscate_int(0)}",
            f"\t\t\t{relay_idx} = {self.obfuscate_int(0)}",
            f"\t\t\t{relay_phase} = {self.obfuscate_int(1)}",
            f"\t\t\tscamper",
            f"\t\tshriek",
            f"\t\t\tsniff {relay_phase} == {self.obfuscate_int(1)}",
            f"\t\t\t\t{relay_seen} = {relay_array}[{relay_idx}]",
            f"\t\t\t\t{relay_idx} = {relay_idx} + {self.obfuscate_int(1)}",
            f"\t\t\t\t{relay_phase} = {self.obfuscate_int(2)}",
            f"\t\t\t\tscamper",
            f"\t\t\tshriek",
            f"\t\t\t\tfling",
            f"\thoard {self.relay_pick}({relay_seen})",
            "",
            f"babuin {self.relay_match}({relay_value})",
            f"\tbanana {relay_record} = {self.relay_type}()",
            f"\t{relay_record}.{relay_value} = {relay_value}",
            f"\t{relay_record}.{relay_array} = [{relay_value}]",
            f"\tmatch {relay_record}",
            f"\t\tas {self.relay_type}{{{relay_value} = {relay_out}, {relay_array} = [{relay_inner}]}} sniff truth",
            f"\t\t\thoard {self.relay_box}({relay_inner})",
            f"\t\tshriek",
            f"\t\t\thoard {relay_value}",
            "",
            f"babuin {self.relay_slice}({relay_value})",
            f"\tbanana {relay_pool} = [{relay_value}, {relay_value}]",
            f"\tbanana {relay_cut} = slice({relay_pool}, {self.obfuscate_int(0)}, length({relay_pool}))",
            f"\thoard {self.relay_pick}({relay_cut}[{self.obfuscate_int(0)}])",
            "",
            f"babuin {self.relay_state}({relay_value})",
            f"\tbanana {relay_pool} = [{relay_value}]",
            f"\tbanana {relay_state_idx} = {self.obfuscate_int(0)}",
            f"\tbanana {relay_state_limit} = length({relay_pool})",
            f"\tbanana {relay_state_out} = {relay_value}",
            f"\tbanana {relay_phase} = {self.obfuscate_int(0)}",
            f"\tbanana {relay_result} = {relay_value}",
            f"\tswing truth",
            f"\t\tsniff {relay_phase} == {self.obfuscate_int(0)}",
            f"\t\t\t{relay_phase} = {self.obfuscate_int(1)}",
            f"\t\t\tscamper",
            f"\t\tshriek",
            f"\t\t\tsniff {relay_phase} == {self.obfuscate_int(1)}",
            f"\t\t\t\tsniff {relay_state_idx} < {relay_state_limit}",
            f"\t\t\t\t\t{relay_phase} = {self.obfuscate_int(2)}",
            f"\t\t\t\tshriek",
            f"\t\t\t\t\t{relay_phase} = {self.obfuscate_int(4)}",
            f"\t\t\t\tscamper",
            f"\t\t\tshriek",
            f"\t\t\t\tsniff {relay_phase} == {self.obfuscate_int(2)}",
            f"\t\t\t\t\t{relay_state_out} = {relay_pool}[{relay_state_idx}]",
            f"\t\t\t\t\t{relay_phase} = {self.obfuscate_int(3)}",
            f"\t\t\t\t\tscamper",
            f"\t\t\t\tshriek",
            f"\t\t\t\t\tfling",
            f"\t\tsniff {relay_phase} == {self.obfuscate_int(3)}",
            f"\t\t\t{relay_result} = {relay_state_out}",
            f"\t\t\t{relay_state_idx} = {relay_state_idx} + {self.obfuscate_int(1)}",
            f"\t\t\t{relay_phase} = {self.obfuscate_int(1)}",
            f"\t\t\tscamper",
            f"\t\tshriek",
            f"\t\t\tsniff {relay_phase} == {self.obfuscate_int(4)}",
            f"\t\t\t\tfling",
            f"\thoard {self.relay_match}({relay_result})",
            "",
            f"jungle {meta_type}",
            f"\t{left}",
            f"\t{right}",
            f"\t{tag}",
            "",
            f"jungle {bundle_type}",
            f"\t{meta}",
            f"\t{values}",
            "",
            f"babuin {loopprobe}({values})",
            f"\tbanana {loop_acc} = {self.obfuscate_int(0)}",
            f"\tbanana {loop_idx} = {self.obfuscate_int(0)}",
            f"\tbanana {loop_item} = {self.obfuscate_int(0)}",
            f"\tbanana {relay_block} = {self.obfuscate_int(0)}",
            f"\tbanana {relay_value_box} = {self.obfuscate_int(0)}",
            f"\tswing truth",
            f"\t\tsniff {relay_block} == {self.obfuscate_int(0)}",
            f"\t\t\tsniff {loop_idx} < length({values})",
            f"\t\t\t\t{relay_block} = {self.obfuscate_int(1)}",
            f"\t\t\tshriek",
            f"\t\t\t\t{relay_block} = {self.obfuscate_int(4)}",
            f"\t\t\tscamper",
            f"\t\tshriek",
            f"\t\t\tsniff {relay_block} == {self.obfuscate_int(1)}",
            f"\t\t\t\t{loop_item} = {values}[{loop_idx}]",
            f"\t\t\t\t{loop_acc} = {loop_acc} + {loop_item} + {loop_idx}",
            f"\t\t\t\t{relay_block} = {self.obfuscate_int(2)}",
            f"\t\t\t\tscamper",
            f"\t\t\tshriek",
            f"\t\t\t\tsniff {relay_block} == {self.obfuscate_int(2)}",
            f"\t\t\t\t\tsniff ({loop_idx} % {self.obfuscate_int(2)}) == 0",
            f"\t\t\t\t\t\t{loop_acc} = {loop_acc} - ({loop_item} + {loop_idx})",
            f"\t\t\t\t\tshriek",
            f"\t\t\t\t\t\t{loop_acc} = {loop_acc} - {loop_item} - {loop_idx}",
            f"\t\t\t\t\t{loop_idx} = {loop_idx} + {self.obfuscate_int(1)}",
            f"\t\t\t\t\t{relay_block} = {self.obfuscate_int(0)}",
            f"\t\t\t\t\tscamper",
            f"\t\t\t\tshriek",
            f"\t\t\t\t\tfling",
            f"\thoard {loop_acc}",
            "",
        ]

        if base_template == 0:
            lines = common_prefix + [
                f"babuin {prepare}()",
                f"\tbanana {encoded} = {self.encode_string(seed_text_value)}",
                f"\tbanana {chars} = reverse(reverse(split({encoded}, join([], \"\"))))",
                f"\tbanana {seed_text} = join(rotate(slice({chars}, 0, length({chars})), length({chars})), join([], \"\"))",
                f"\tbanana {data_name} = []",
                f"\tswing {idx}, {item} in {chars}",
                f"\t\tsniff ({idx} % {self.obfuscate_int(3)}) == 0",
                f"\t\t\tpush({data_name}, ord({item}) + {idx})",
                f"\t\t\tscamper",
                f"\t\tshriek",
                f"\t\t\tinsert({data_name}, length({data_name}), ord({item}) - {idx})",
                f"\tbanana {popped} = pop({data_name})",
                f"\tinsert({data_name}, 0, {popped})",
                f"\tbanana {removed} = remove({data_name}, 1)",
                f"\tinsert({data_name}, 1, {removed})",
                f"\tbanana {text} = slice({data_name}, 0, length({data_name}))",
                f"\tbanana {meta} = {meta_type}()",
                f"\t{meta}.{left} = string(length({seed_text}))",
                f"\t{meta}.{right} = type({text})",
                f"\t{meta}.{tag} = format({stringify_babuin_text('{}:{}')}, find({seed_text}, {chars}[0]), bool(contains({seed_text}, {chars}[0])))",
                f"\tbanana {bundle} = {bundle_type}()",
                f"\t{bundle}.{meta} = {meta}",
                f"\t{bundle}.{values} = {text}",
                f"\thoard {bundle}",
                "",
                f"babuin {twist}({bundle})",
                f"\tbanana {{{meta}, {values}}} = {bundle}",
                f"\tbanana {{{left}, {right}, {tag}}} = {meta}",
                f"\tbanana [{first}, {second}, {third}] = slice({values}, 0, {self.obfuscate_int(3)})",
                f"\tbanana {glyphs} = [string({idx}) + chr(({item} % {self.obfuscate_int(26)}) + {self.obfuscate_int(65)}) swing {idx}, {item} in {values} sniff {idx} < {self.obfuscate_int(4)}]",
                f"\tbanana {joined} = join({glyphs}, {colon_text})",
                f"\tbanana {probe_acc} = {self.obfuscate_int(0)}",
                f"\tmatch [{first}, [{second}, {third}], {right}, bool(contains({tag}, {colon_text}) || contains({tag}, {truth_text}))]",
                f"\t\tas [{head}, [{mid}, {tail}], _, truth]",
                f"\t\t\t{probe_acc} = {head} + {mid} + {tail} + length({glyphs}) + find({joined}, {colon_text})",
                f"\t\tshriek",
                f"\t\t\t{probe_acc} = {self.obfuscate_int(0)}",
                f"\tsniff !({probe_acc} < {self.obfuscate_int(0)}) && (contains({right}, {array_text}) || contains({right}, {string_text}))",
                f"\t\tbanana {probe} = [{probe_acc}, {joined}, {left}]",
                f"\t\thoard {probe}",
                f"\tshriek",
                f"\t\thoard [{self.obfuscate_int(0)}, join([], \"\"), {left}]",
                "",
                f"babuin {fold}({bundle})",
                f"\tbanana {acc} = {self.obfuscate_int(len(seed_text_value))}",
                f"\tmatch {bundle}",
                f"\t\tas {bundle_type}{{{meta} = {meta_type}{{{left}, {right}, {tag}}}, {values}}} sniff {right} == {array_text}",
                f"\t\t\tbanana {parts} = split({tag}, {colon_text})",
                f"\t\t\t{acc} = {acc} + int({parts}[0])",
                f"\t\t\tsniff bool({parts}[1]) == truth",
                f"\t\t\t\t{acc} = {acc} + length({values})",
                f"\t\t\tshriek",
                f"\t\t\t\t{acc} = {acc} - {self.obfuscate_int(1)}",
                f"\t\tshriek",
                f"\t\t\t{acc} = {self.obfuscate_int(0)}",
                f"\tbanana {probe} = {twist}({bundle})",
                f"\tbanana [{probe_num}, {probe_text}, {probe_size}] = {probe}",
                f"\t{acc} = {acc} + {probe_num} + int({probe_size})",
                f"\t{acc} = {acc} + length(split({probe_text}, {colon_text}))",
                f"\t{acc} = {acc} + {loopprobe}({bundle}.{values})",
                f"\tbanana {hashed} = reverse(reverse(hash(join(split(hash({self.encode_string(seed_text_value)}), join([], \"\")), join([], \"\")))))",
                f"\t{acc} = {acc} + ord({hashed}[0]) + find({hashed}, {hashed}[length({hashed}) - 1])",
                f"\tbanana {seen} = lie",
                f"\tsniff contains({bundle}.{values}, {bundle}.{values}[0])",
                f"\t\t{seen} = truth",
                f"\tshriek",
                f"\t\t{seen} = lie",
                f"\tsniff {seen}",
                f"\t\t{acc} = {acc} + {self.obfuscate_int(7)}",
                f"\tshriek",
                f"\t\t{acc} = {acc} - {self.obfuscate_int(11)}",
                f"\t{acc} = {acc} + find({bundle}.{values}, {bundle}.{values}[0])",
                f"\tbanana {expr} = join([], \"\")",
                f"\tswing {idx}, {item} in {bundle}.{values}",
                f"\t\t{expr} = format({stringify_babuin_text('{} + {} + {}')}, {acc}, {item}, {idx})",
                f"\t\t{acc} = int(eval({expr}))",
                f"\t\tsniff ({idx} % {self.obfuscate_int(2)}) == 0",
                f"\t\t\t{acc} = xor({acc} + int(float(string({item}))), {self.obfuscate_int(0)})",
                f"\t\t\tscamper",
                f"\t\tshriek",
                f"\t\t\t{acc} = xor({acc} - int(float(string({idx}))), {self.obfuscate_int(0)})",
                f"\t\tsniff {acc} > {self.obfuscate_int(2000)} && {idx} > {self.obfuscate_int(6)}",
                f"\t\t\tfling",
                f"\t{acc} = xor({acc} % {self.obfuscate_int(mod)}, {self.obfuscate_int(0)})",
                f"\thoard {acc}",
            ]
        else:
            lines = common_prefix + [
                f"babuin {prepare}()",
                f"\tbanana {encoded} = {self.encode_string(seed_text_value)}",
                f"\tbanana {chars} = reverse(reverse(split({encoded}, join([], \"\"))))",
                f"\tbanana {seed_text} = join(rotate(slice({chars}, 0, length({chars})), length({chars})), join([], \"\"))",
                f"\tbanana {data_name} = []",
                f"\tbanana {idx} = {self.obfuscate_int(0)}",
                f"\tbanana {limit} = length({chars})",
                f"\tbanana {item} = join([], \"\")",
                f"\tswing {idx} < {limit}",
                f"\t\t{item} = {chars}[{idx}]",
                f"\t\tsniff ({idx} % {self.obfuscate_int(3)}) == 0",
                f"\t\t\tpush({data_name}, ord({item}) + {idx})",
                f"\t\t\t{idx} = {idx} + {self.obfuscate_int(1)}",
                f"\t\t\tscamper",
                f"\t\tshriek",
                f"\t\t\tinsert({data_name}, length({data_name}), ord({item}) - {idx})",
                f"\t\t{idx} = {idx} + {self.obfuscate_int(1)}",
                f"\tbanana {popped} = pop({data_name})",
                f"\tinsert({data_name}, 0, {popped})",
                f"\tbanana {removed} = remove({data_name}, 1)",
                f"\tinsert({data_name}, 1, {removed})",
                f"\tbanana {text} = slice({data_name}, 0, length({data_name}))",
                f"\tbanana {meta} = {meta_type}()",
                f"\t{meta}.{left} = string(length({seed_text}))",
                f"\t{meta}.{right} = type({text})",
                f"\t{meta}.{tag} = format({stringify_babuin_text('{}:{}')}, find({seed_text}, {chars}[0]), bool(contains({seed_text}, {chars}[0])))",
                f"\tbanana {bundle} = {bundle_type}()",
                f"\t{bundle}.{meta} = {meta}",
                f"\t{bundle}.{values} = {text}",
                f"\thoard {bundle}",
                "",
                f"babuin {twist}({bundle})",
                f"\tbanana {{{meta}, {values}}} = {bundle}",
                f"\tbanana {{{left}, {right}, {tag}}} = {meta}",
                f"\tbanana [{first}, {second}, {third}] = slice({values}, 0, {self.obfuscate_int(3)})",
                f"\tbanana {glyphs} = [string({idx}) + chr(({item} % {self.obfuscate_int(26)}) + {self.obfuscate_int(65)}) swing {idx}, {item} in {values} sniff {idx} < {self.obfuscate_int(4)}]",
                f"\tbanana {joined} = join({glyphs}, {colon_text})",
                f"\tbanana {probe_acc} = {self.obfuscate_int(0)}",
                f"\tmatch [{right}, bool(contains({tag}, {colon_text}) || contains({tag}, {truth_text})), [{first}, [{second}, {third}]]]",
                f"\t\tas [_, truth, [{head}, [{mid}, {tail}]]]",
                f"\t\t\t{probe_acc} = {head} + {mid} + {tail} + length({glyphs}) + find({joined}, {colon_text})",
                f"\t\tshriek",
                f"\t\t\t{probe_acc} = {self.obfuscate_int(0)}",
                f"\tsniff !({probe_acc} < {self.obfuscate_int(0)}) && (contains({right}, {array_text}) || contains({right}, {string_text}))",
                f"\t\thoard [{probe_acc}, {joined}, {left}]",
                f"\tshriek",
                f"\t\thoard [{self.obfuscate_int(0)}, join([], \"\"), {left}]",
                "",
                f"babuin {compress}({probe})",
                f"\tbanana [{probe_num}, {probe_text}, {probe_size}] = {probe}",
                f"\thoard [{probe_num}, length(split({probe_text}, {colon_text})), int({probe_size})]",
                "",
                f"babuin {fold}({bundle})",
                f"\tbanana {acc} = {self.obfuscate_int(len(seed_text_value))}",
                f"\tbanana {{{meta}, {values}}} = {bundle}",
                f"\tbanana {{{left}, {right}, {tag}}} = {meta}",
                f"\tbanana {parts} = split({tag}, {colon_text})",
                f"\tmatch [{right}, bool({parts}[1]), {values}]",
                f"\t\tas [{left_text}, truth, _] sniff {left_text} == {array_text}",
                f"\t\t\t{acc} = {acc} + int({parts}[0]) + length({values})",
                f"\t\tshriek",
                f"\t\t\t{acc} = {self.obfuscate_int(0)}",
                f"\tbanana [{probe_num}, {probe_text}, {probe_size}] = {compress}({twist}({bundle}))",
                f"\t{acc} = {acc} + {probe_num} + {probe_text} + {probe_size}",
                f"\t{acc} = {acc} + {loopprobe}({values})",
                f"\tbanana {hashed} = reverse(reverse(hash(join(split(hash({self.encode_string(seed_text_value)}), join([], \"\")), join([], \"\")))))",
                f"\t{acc} = {acc} + ord({hashed}[0]) + find({hashed}, {hashed}[length({hashed}) - 1])",
                f"\tbanana {seen} = lie",
                f"\tsniff contains({values}, {values}[0])",
                f"\t\t{seen} = truth",
                f"\tshriek",
                f"\t\t{seen} = lie",
                f"\tsniff {seen}",
                f"\t\t{acc} = {acc} + {self.obfuscate_int(7)}",
                f"\tshriek",
                f"\t\t{acc} = {acc} - {self.obfuscate_int(11)}",
                f"\t{acc} = {acc} + find({values}, {values}[0])",
                f"\tbanana {expr} = join([], \"\")",
                f"\tbanana {idx} = {self.obfuscate_int(0)}",
                f"\tbanana {item} = {self.obfuscate_int(0)}",
                f"\tswing {idx} < length({values})",
                f"\t\t{item} = {values}[{idx}]",
                f"\t\t{expr} = format({stringify_babuin_text('{} + {} + {}')}, {acc}, {item}, {idx})",
                f"\t\t{acc} = int(eval({expr}))",
                f"\t\tsniff ({idx} % {self.obfuscate_int(2)}) == 0",
                f"\t\t\t{acc} = xor({acc} + int(float(string({item}))), {self.obfuscate_int(0)})",
                f"\t\t\t{idx} = {idx} + {self.obfuscate_int(1)}",
                f"\t\t\tscamper",
                f"\t\tshriek",
                f"\t\t\t{acc} = xor({acc} - int(float(string({idx}))), {self.obfuscate_int(0)})",
                f"\t\tsniff {acc} > {self.obfuscate_int(2000)} && {idx} > {self.obfuscate_int(6)}",
                f"\t\t\tfling",
                f"\t\t{idx} = {idx} + {self.obfuscate_int(1)}",
                f"\t{acc} = xor({acc} % {self.obfuscate_int(mod)}, {self.obfuscate_int(0)})",
                f"\thoard {acc}",
            ]

        if helper_variant == 1:
            mutate_lines = [
                f"babuin {mutate}({probe})",
                f"\tbanana [{probe_num}, {probe_text}, {probe_size}] = {probe}",
                f"\tbanana {pieces} = [piece swing piece in split({probe_text}, {colon_text})]",
                f"\tbanana {rebuilt} = join(slice({pieces}, 0, length({pieces})), {colon_text})",
                f"\tbanana {kind} = type({pieces})",
                f"\tbanana {numeric} = int(float(string(int({probe_size}))))",
                f"\tmatch [{kind}, contains({rebuilt}, {colon_text}) || length({pieces}) == {self.obfuscate_int(1)}, [{probe_num}, {numeric}]]",
                f"\t\tas [_, truth, [{head}, {tail}]]",
                f"\t\t\thoard [{head} + {self.obfuscate_int(0)}, {rebuilt}, string({tail})]",
                f"\t\tshriek",
                f"\t\t\thoard {probe}",
                "",
            ]
            insert_at = len(lines)
            for i, line in enumerate(lines):
                if line == f"babuin {fold}({bundle})":
                    insert_at = i
                    break
            lines = lines[:insert_at] + mutate_lines + lines[insert_at:]
            for i, line in enumerate(lines):
                if line == f"\tbanana {probe} = {twist}({bundle})":
                    lines[i] = f"\tbanana {probe} = {mutate}({twist}({bundle}))"
                elif line == f"\tbanana [{probe_num}, {probe_text}, {probe_size}] = {compress}({twist}({bundle}))":
                    lines[i] = f"\tbanana [{probe_num}, {probe_text}, {probe_size}] = {compress}({mutate}({twist}({bundle})))"

        prepare_alias_lines, prepare_entry = self.render_alias_chain(prepare, 0)
        fold_alias_lines, fold_entry = self.render_alias_chain(fold, 1)
        guard_alias_lines, guard_entry = self.render_alias_chain(guard, 0)
        main_alias_lines, main_entry = self.render_alias_chain(self.original_main_name, 0)
        lines += [""] + prepare_alias_lines + fold_alias_lines + guard_alias_lines + main_alias_lines

        guard_body = [f"\thoard {fold_entry}({prepare_entry}())"]
        if guard_variant == 1:
            guard_body = [
                f"\tbanana {guard_probe} = ({fold_entry}({prepare_entry}()) % {self.obfuscate_int(17)})",
                f"\tsniff {guard_probe} == {self.obfuscate_int(opaque_expected)}",
                f"\t\thoard {fold_entry}({prepare_entry}())",
                f"\tshriek",
                f"\t\thoard {fold_entry}({prepare_entry}())",
            ]

        lines += [
            "",
            f"babuin {guard}()",
            *guard_body,
            "",
            "babuin main()",
            f"\tbanana {acc} = {guard_entry}()",
            f"\tsniff {acc} == {self.obfuscate_int(expected)}",
            f"\t\thoard {main_entry}()",
            "\tshriek",
            f"\t\thoard {self.obfuscate_int(0)}",
            "",
        ]
        return "\n".join(lines)

    def build(self) -> str:
        transformed = self.transform_source()
        prelude = ""
        junk_records = "\n".join(self.render_junk_records()).rstrip()
        junk_functions = "\n".join(self.render_junk_functions()).rstrip()
        wrapper = self.render_wrapper().rstrip()
        original = transformed.rstrip("\n")

        layout = self.rng.randrange(3)
        if layout == 0:
            blocks = [prelude, junk_records, junk_functions, wrapper, original]
        elif layout == 1:
            blocks = [prelude, junk_records, wrapper, junk_functions, original]
        else:
            blocks = [prelude, wrapper, junk_records, junk_functions, original]
        return "\n\n".join(block for block in blocks if block)


def obfuscate_source(source: str, seed: str | None = None, junk_records: int = 2, junk_functions: int = 4) -> tuple[str, str]:
    actual_seed = seed or secrets.token_hex(16)
    rng = random.Random(actual_seed)
    program = Obfuscator(source, rng, junk_records, junk_functions).build()
    return program, actual_seed


def obfuscate_file(
    input_path: Path,
    output_path: Path | None = None,
    seed: str | None = None,
    junk_records: int = 2,
    junk_functions: int = 4,
) -> tuple[str, str]:
    source = input_path.read_text(encoding="utf-8")
    program, actual_seed = obfuscate_source(source, seed=seed, junk_records=junk_records, junk_functions=junk_functions)
    if output_path is not None:
        output_path.write_text(program, encoding="utf-8")
    return program, actual_seed


def main() -> int:
    args = parse_args()
    program, seed = obfuscate_file(
        input_path=Path(args.input),
        output_path=Path(args.output) if args.output else None,
        seed=args.seed,
        junk_records=args.junk_records,
        junk_functions=args.junk_functions,
    )
    if not args.output:
        sys.stdout.write(program)
    print(f"obfuscator seed: {seed}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
