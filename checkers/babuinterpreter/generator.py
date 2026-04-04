#!/usr/bin/env python3
import argparse
import json
import os
import re
import random
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

try:
    from error_cases_data import ERROR_CASE_NAMES, load_error_cases
except ImportError:
    from .error_cases_data import ERROR_CASE_NAMES, load_error_cases


RESERVED_WORDS = {
    "jungle",
    "babuin",
    "banana",
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

BUILTIN_NAMES = {
    "print",
    "format",
    "panic",
    "int",
    "float",
    "string",
    "bool",
    "length",
    "type",
    "hash",
    "reverse",
    "rotate",
    "xor",
    "contains",
    "find",
    "join",
    "split",
    "storage",
    "store",
    "load",
    "push",
    "pop",
    "slice",
    "insert",
    "remove",
    "input",
    "ord",
    "chr",
    "eval",
    "exit",
}


def babuin_string(value: str) -> str:
    parts = ['"']
    for ch in value:
        if ch == "\n":
            parts.append("\\n")
        elif ch == "\t":
            parts.append("\\t")
        elif ch == "\r":
            parts.append("\\r")
        elif ch == "\\":
            parts.append("\\\\")
        elif ch == '"':
            parts.append('\\"')
        else:
            parts.append(ch)
    parts.append('"')
    return "".join(parts)


def fnv1a_hex(text: str) -> str:
    value = 1469598103934665603
    for byte in text.encode("utf-8"):
        value ^= byte
        value = (value * 1099511628211) & 0xFFFFFFFFFFFFFFFF
    return f"{value:016x}"


def rotate_left_list(items: list[str], amount: int) -> list[str]:
    if not items:
        return []
    shift = amount % len(items)
    return items[shift:] + items[:shift]


def shift_printable(text: str, delta_fn) -> str:
    out: list[str] = []
    for i, ch in enumerate(text):
        code = ord(ch)
        if code < 32 or code > 126:
            raise ValueError("generator expects printable ASCII text only")
        delta = delta_fn(i, ch)
        out.append(chr(32 + ((code - 32 + delta) % 95)))
    return "".join(out)


def unshift_printable(text: str, delta_fn) -> str:
    return shift_printable(text, lambda i, ch: -delta_fn(i, ch))


def reverse_chunks(text: str, chunk: int) -> str:
    if chunk <= 0:
        raise ValueError("chunk size must be positive")
    prefix = ""
    start = 0
    remainder = len(text) % chunk
    if remainder != 0:
        prefix = text[:remainder]
        start = remainder
    parts = [text[i : i + chunk] for i in range(start, len(text), chunk)]
    parts.reverse()
    return prefix + "".join(parts)


def swap_pairs(text: str) -> str:
    chars = list(text)
    i = 0
    while i + 1 < len(chars):
        chars[i], chars[i + 1] = chars[i + 1], chars[i]
        i += 2
    return "".join(chars)


def stride_bucket_join(text: str, stride: int) -> str:
    return "".join(text[offset::stride] for offset in range(stride))


def invert_stride_bucket(output: str, stride: int) -> str:
    total = len(output)
    bucket_lengths = [(total + stride - offset - 1) // stride for offset in range(stride)]
    buckets: list[str] = []
    cursor = 0
    for size in bucket_lengths:
        buckets.append(output[cursor : cursor + size])
        cursor += size
    rebuilt: list[str] = []
    for index in range(total):
        bucket = index % stride
        offset = index // stride
        rebuilt.append(buckets[bucket][offset])
    return "".join(rebuilt)


def block_rotate(text: str, rotate_amount: int, chunk: int) -> str:
    rotated = "".join(rotate_left_list(list(text), rotate_amount))
    return reverse_chunks(rotated, chunk)


def invert_block_rotate(output: str, rotate_amount: int, chunk: int) -> str:
    markers = "".join(chr(0xE000 + i) for i in range(len(output)))
    transformed = block_rotate(markers, rotate_amount, chunk)
    positions = {ch: index for index, ch in enumerate(markers)}
    rebuilt = [""] * len(output)
    for out_index, marker in enumerate(transformed):
        rebuilt[positions[marker]] = output[out_index]
    return "".join(rebuilt)


def mirror_swap_rotate(text: str) -> str:
    return swap_pairs("".join(rotate_left_list(list(text[::-1]), 1)))


def invert_mirror_swap_rotate(output: str) -> str:
    unswapped = swap_pairs(output)
    unrotated = "".join(rotate_left_list(list(unswapped), -1))
    return unrotated[::-1]


def source_line(name: str, text: str) -> str:
    return f"\tbanana {name} = unpack({babuin_string(text)})"


def make_program(*lines: str) -> str:
    return "\n".join(lines) + "\n"


def finish_scaffold(kind: str, seed: str, stem: str) -> list[str]:
    if kind == "flagstore":
        return [
            "babuin finish(text)",
            '\tbanana parts = split(text, "|")',
            "\tsniff parts as [storage_id, storage_key, flag, footer]",
            '\t\tbanana box = storage(storage_id, storage_key)',
            '\t\tstore(box, "FLAG", flag)',
            '\t\tbanana seen = load(box, "FLAG")',
            '\t\tprint(seen)',
            '\t\tprint("\\n")',
            '\t\tprint(footer)',
            '\t\tprint("\\n")',
            "\t\thoard 0",
            "\tshriek",
            '\t\tpanic("invalid generated store payload")',
            "",
        ]
    if kind == "flagload":
        return [
            "babuin finish(text)",
            '\tbanana parts = split(text, "|")',
            "\tsniff parts as [storage_id, storage_key, footer]",
            '\t\tbanana box = storage(storage_id, storage_key)',
            '\t\tbanana seen = load(box, "FLAG")',
            '\t\tstore(box, "FLAG", seen)',
            '\t\tprint(seen)',
            '\t\tprint("\\n")',
            '\t\tprint(footer)',
            '\t\tprint("\\n")',
            "\t\thoard 0",
            "\tshriek",
            '\t\tpanic("invalid generated load payload")',
            "",
        ]
    raise ValueError(f"unsupported generator kind: {kind}")


def shared_scaffold(kind: str, seed: str, stem: str) -> list[str]:
    return [
        "jungle Capsule",
        "\traw",
        "\tchars",
        "\ttag",
        "",
        "babuin keyword_probe()",
        "\tbanana seen = 0",
        "\tbanana state = 0",
        "\tswing truth",
        "\t\tsniff state == 0",
        "\t\t\tseen = seen + 1",
        "\t\t\tstate = 1",
        "\t\t\tscamper",
        "\t\tshriek",
        "\t\t\tsniff lie",
        "\t\t\t\tseen = seen + 7",
        "\t\t\t\tfling",
        "\t\t\tshriek",
        "\t\t\t\tfling",
        "\thoard seen",
        "",
        "babuin unpack(input_raw)",
        "\tbanana ping = keyword_probe()",
        '\tbanana stash = reverse(reverse(split(input_raw, "")))',
        '\tbanana stamp = format("{}:{}", length(input_raw), find(hash(input_raw), hash(input_raw)[0]))',
        "\tbanana box = Capsule{ raw = input_raw, chars = stash, tag = stamp }",
        "\tbanana {raw, chars, tag} = box",
        "\tmatch [raw, chars, bool(contains(tag, \":\"))]",
        "\t\tas [plain, letters_box, truth]",
        '\t\t\thoard join(letters_box, "")',
        "\t\tshriek",
        "\t\t\thoard raw",
        "",
        *finish_scaffold(kind, seed, stem),
    ]


def make_obscured_program(kind: str, seed: str, stem: str, *lines: str) -> str:
    return make_program(*shared_scaffold(kind, seed, stem), *lines)


@dataclass
class TemplateSpec:
    key: str
    summary: str
    features: list[str]
    render: Callable[[str, str, str], str]
    transform: Callable[[str], str]
    inverse: Callable[[str], str]


@dataclass
class BasicTemplateSpec:
    key: str
    summary: str
    features: list[str]
    render: Callable[[str], str]


@dataclass
class GeneratedProgram:
    kind: str
    seed: str
    template: str
    payload_text: str
    expected_stdout: str
    program_text: str
    manifest: dict


@dataclass
class GeneratedErrorProgram:
    kind: str
    seed: str
    case_name: str
    expected_stdout: str
    expected_error_substring: str
    program_text: str
    manifest: dict


def invert_odd_even(output: str) -> str:
    odd_len = len(output) // 2
    even_len = len(output) - odd_len
    odd = output[:odd_len]
    even = output[odd_len:]
    out: list[str] = []
    for i in range(even_len):
        out.append(even[i])
        if i < odd_len:
            out.append(odd[i])
    return "".join(out)


def invert_reverse_rotate_xor(output: str) -> str:
    chars = list(unshift_printable(output, lambda i, _ch: (i ^ 1) % 3))
    rotated_back = rotate_left_list(chars, -1)
    rotated_back.reverse()
    return "".join(rotated_back)


def invert_state_machine(output: str) -> str:
    even_len = (len(output) + 1) // 2
    evens = output[:even_len]
    odds = output[even_len:]
    out: list[str] = []
    for i in range(even_len):
        out.append(evens[i])
        if i < len(odds):
            out.append(odds[i])
    return "".join(out)


def invert_panic_exit(output: str) -> str:
    return output[::-1]


def template_reverse_loop(text: str, mode: str = "embedded", seed: str = "program-demo") -> str:
    return make_obscured_program(
        mode,
        seed,
        "reverse_loop",
        "babuin main()",
        source_line("source", text),
        '\tbanana chars = split(source, "")',
        "\tbanana out = []",
        "\tbanana i = 0",
        "\tswing i < length(chars)",
        "\t\tinsert(out, 0, chars[i])",
        "\t\ti = i + 1",
        '\thoard finish(join(out, ""))',
    )


def template_shift_records(text: str, mode: str = "embedded", seed: str = "program-demo") -> str:
    return make_obscured_program(
        mode,
        seed,
        "shift_records",
        "jungle Glyph",
        "\traw",
        "\tcode",
        "\tnext",
        "",
        "babuin bump(ch, delta)",
        "\tbanana base = ord(ch) - 32",
        "\tbanana shifted = 32 + ((base + delta) % 95)",
        "\thoard chr(shifted)",
        "",
        "babuin main()",
        source_line("source", text),
        "\tbanana boxes = []",
        "\tbanana glyph = Glyph()",
        "\tswing i, ch in source",
        "\t\tglyph = Glyph{ raw = ch, code = ord(ch), next = bump(ch, 1) }",
        "\t\tpush(boxes, glyph)",
        "\tbanana out = []",
        "\tswing box in boxes",
        "\t\tsniff box as Glyph{ raw, code, next }",
        "\t\t\tpush(out, next)",
        '\thoard finish(join(out, ""))',
    )


def template_odd_even_records(text: str, mode: str = "embedded", seed: str = "program-demo") -> str:
    return make_obscured_program(
        mode,
        seed,
        "odd_even_records",
        "jungle Buckets",
        "\tleft",
        "\tright",
        "",
        "babuin main()",
        source_line("source", text),
        "\tbanana even = []",
        "\tbanana odd = []",
        "\tswing i, ch in source",
        "\t\tsniff (i % 2) == 0",
        "\t\t\tpush(even, ch)",
        "\t\t\tscamper",
        "\t\tpush(odd, ch)",
        "\tbanana pack = Buckets{ left = odd, right = even }",
        '\tbanana out = ""',
        "\tmatch pack",
        "\t\tas Buckets{ left = left, right = right }",
        '\t\t\tout = join(left, "") + join(right, "")',
        "\t\tshriek",
        "\t\t\tout = source",
        "\thoard finish(out)",
    )


def template_eval_shift(text: str, mode: str = "embedded", seed: str = "program-demo") -> str:
    return make_obscured_program(
        mode,
        seed,
        "eval_shift",
        "babuin bump(ch, idx)",
        '\tbanana expr = format("{} + {}", ord(ch) - 32, idx % 3)',
        "\tbanana value = int(eval(expr))",
        "\thoard chr(32 + (value % 95))",
        "",
        "babuin main()",
        source_line("source", text),
        '\tbanana out = ""',
        "\tswing i, ch in source",
        "\t\tout = out + bump(ch, i)",
        "\thoard finish(out)",
    )


def template_chunk_reverse(text: str, mode: str = "embedded", seed: str = "program-demo") -> str:
    return make_obscured_program(
        mode,
        seed,
        "chunk_reverse",
        "babuin chunk(text, start, stop)",
        '\tbanana chars = split(text, "")',
        '\thoard join(slice(chars, start, stop), "")',
        "",
        "babuin main()",
        source_line("source", text),
        "\tbanana parts = []",
        "\tbanana i = 0",
        "\tbanana stop = 0",
        '\tbanana piece = ""',
        '\tbanana prefix = ""',
        "\tsniff (length(source) % 2) != 0",
        "\t\tprefix = chunk(source, 0, 1)",
        "\t\ti = 1",
        "\tswing i < length(source)",
        "\t\tstop = i + 2",
        "\t\tsniff stop > length(source)",
        "\t\t\tstop = length(source)",
        "\t\tpiece = chunk(source, i, stop)",
        "\t\tinsert(parts, 0, piece)",
        "\t\ti = stop",
        '\thoard finish(prefix + join(parts, ""))',
    )


def template_comprehension_rotate(text: str, mode: str = "embedded", seed: str = "program-demo") -> str:
    return make_obscured_program(
        mode,
        seed,
        "comprehension_rotate",
        "babuin main()",
        source_line("source", text),
        '\tbanana chars = rotate(split(source, ""), 1)',
        '\tbanana copied = [ch swing ch in chars sniff ch != ""]',
        '\thoard finish(join(copied, ""))',
    )


def template_splice_swap(text: str, mode: str = "embedded", seed: str = "program-demo") -> str:
    return make_obscured_program(
        mode,
        seed,
        "splice_swap",
        "babuin main()",
        source_line("source", text),
        '\tbanana chars = split(source, "")',
        "\tbanana i = 0",
        '\tbanana left = ""',
        "\tswing i + 1 < length(chars)",
        "\t\tleft = remove(chars, i)",
        "\t\tinsert(chars, i + 1, left)",
        "\t\ti = i + 2",
        '\thoard finish(join(chars, ""))',
    )


def template_reverse_rotate_xor(text: str, mode: str = "embedded", seed: str = "program-demo") -> str:
    return make_obscured_program(
        mode,
        seed,
        "reverse_rotate_xor",
        "babuin twist(text)",
        '\tbanana chars = rotate(reverse(split(text, "")), 1)',
        '\tbanana out = ""',
        "\tbanana delta = 0",
        "\tbanana shifted = 0",
        "\tswing i, ch in chars",
        "\t\tdelta = xor(i, 1) % 3",
        "\t\tshifted = 32 + ((ord(ch) - 32 + delta) % 95)",
        "\t\tout = out + chr(shifted)",
        "\thoard out",
        "",
        "babuin main()",
        source_line("source", text),
        "\thoard finish(twist(source))",
    )


def template_state_machine(text: str, mode: str = "embedded", seed: str = "program-demo") -> str:
    return make_obscured_program(
        mode,
        seed,
        "state_machine",
        "babuin weave(text)",
        '\tbanana chars = split(text, "")',
        "\tbanana state = 0",
        "\tbanana idx = 0",
        "\tbanana out = []",
        "\tswing truth",
        "\t\tsniff state == 0",
        "\t\t\tsniff idx < length(chars)",
        "\t\t\t\tstate = 1",
        "\t\t\tshriek",
        "\t\t\t\tstate = 3",
        "\t\t\tscamper",
        "\t\tshriek",
        "\t\t\tsniff state == 1",
        "\t\t\t\tpush(out, chars[idx])",
        "\t\t\t\tidx = idx + 2",
        "\t\t\t\tstate = 0",
        "\t\t\t\tscamper",
        "\t\t\tshriek",
        "\t\t\t\tsniff state == 3",
        "\t\t\t\t\tidx = 1",
        "\t\t\t\t\tstate = 4",
        "\t\t\t\t\tscamper",
        "\t\t\t\tshriek",
        "\t\t\t\t\tsniff idx < length(chars)",
        "\t\t\t\t\t\tpush(out, chars[idx])",
        "\t\t\t\t\t\tidx = idx + 2",
        "\t\t\t\t\t\tscamper",
        "\t\t\t\t\tfling",
        '\thoard join(out, "")',
        "",
        "babuin main()",
        source_line("source", text),
        "\thoard finish(weave(source))",
    )


def template_panic_exit(text: str, mode: str = "embedded", seed: str = "program-demo") -> str:
    return make_obscured_program(
        mode,
        seed,
        "panic_exit",
        "babuin main()",
        f"{source_line('source', text)}; banana out = join(reverse(split(source, \"\")), \"\"); banana code = finish(out)",
        "\tsniff lie",
        '\t\tpanic("unreachable")',
        "\texit(code)",
    )


def template_parity_comprehension(text: str, mode: str = "embedded", seed: str = "program-demo") -> str:
    return make_obscured_program(
        mode,
        seed,
        "parity_comprehension",
        "babuin main()",
        source_line("source", text),
        '\tbanana chars = split(source, "")',
        "\tbanana shifted = [chr(32 + ((ord(ch) - 32 + (i % 2)) % 95)) swing i, ch in chars]",
        '\thoard finish(join(shifted, ""))',
    )


def template_stride_buckets(text: str, mode: str = "embedded", seed: str = "program-demo") -> str:
    return make_obscured_program(
        mode,
        seed,
        "stride_buckets",
        "jungle Buckets3",
        "\tone",
        "\ttwo",
        "\tthree",
        "",
        "babuin stitch(pack)",
        '\tbanana out = ""',
        "\tmatch pack",
        "\t\tas Buckets3{ one = first, two = second, three = third } sniff bool(contains(type(pack), \"Buckets3\"))",
        '\t\t\tout = join(first, "") + join(second, "") + join(third, "")',
        "\t\tshriek",
        '\t\t\tout = ""',
        "\thoard out",
        "",
        "babuin main()",
        source_line("source", text),
        "\tbanana first = []",
        "\tbanana second = []",
        "\tbanana third = []",
        "\tswing i, ch in source",
        "\t\tsniff (i % 3) == 0",
        "\t\t\tpush(first, ch)",
        "\t\t\tscamper",
        "\t\tshriek",
        "\t\t\tsniff (i % 3) == 1",
        "\t\t\t\tpush(second, ch)",
        "\t\t\t\tscamper",
        "\t\t\tshriek",
        "\t\t\t\tpush(third, ch)",
        "\tbanana pack = Buckets3{ one = first, two = second, three = third }",
        '\tbanana tag = format("{}:{}", length(source), find(hash(source), hash(source)[0]))',
        '\tbanana out = stitch(pack)',
        '\tbanana ready = bool(contains(tag, ":"))',
        '\tsniff ready',
        "\t\thoard finish(out)",
        "\tshriek",
        "\t\thoard finish(out)",
    )


def template_quadratic_shift(text: str, mode: str = "embedded", seed: str = "program-demo") -> str:
    return make_obscured_program(
        mode,
        seed,
        "quadratic_shift",
        "jungle Step",
        "\tidx",
        "\tdelta",
        "",
        "babuin bend(ch, idx)",
        '\tbanana expr = format("{} + {}", ord(ch) - 32, ((idx * idx) + 3) % 7)',
        "\tbanana shifted = int(eval(expr))",
        "\thoard chr(32 + (shifted % 95))",
        "",
        "babuin main()",
        source_line("source", text),
        "\tbanana plan = []",
        "\tbanana slot = Step()",
        '\tbanana out = ""',
        "\tswing i, ch in source",
        "\t\tslot = Step{ idx = i, delta = ((i * i) + 3) % 7 }",
        "\t\tpush(plan, slot)",
        "\tswing slot in plan",
        "\t\tsniff slot as Step{ idx = idx, delta = delta }",
        "\t\t\tout = out + bend(source[idx], idx)",
        "\t\tshriek",
        '\t\t\tout = out + ""',
        '\thoard finish(out)',
    )


def template_block_rotate_maze(text: str, mode: str = "embedded", seed: str = "program-demo") -> str:
    return make_obscured_program(
        mode,
        seed,
        "block_rotate_maze",
        "babuin chunk(text, start, stop)",
        '\tbanana chars = split(text, "")',
        '\thoard join(slice(chars, start, stop), "")',
        "",
        "babuin main()",
        source_line("source", text),
        '\tbanana chars = rotate(split(source, ""), 2)',
        "\tbanana blocks = []",
        "\tbanana i = 0",
        "\tbanana stop = 0",
        '\tbanana piece = ""',
        '\tbanana prefix = []',
        '\tbanana offset = length(chars) % 3',
        '\tsniff offset != 0',
        '\t\tprefix = slice(chars, 0, offset)',
        '\t\ti = offset',
        "\tswing i < length(chars)",
        "\t\tstop = i + 3",
        "\t\tsniff stop > length(chars)",
        "\t\t\tstop = length(chars)",
        '\t\tpiece = join(slice(chars, i, stop), "")',
        "\t\tinsert(blocks, 0, piece)",
        "\t\ti = stop",
        '\tbanana mask = [string(length(piece)) swing piece in blocks sniff piece != ""]',
        '\tbanana joined = join(prefix, "") + join(blocks, "")',
        '\tbanana ready = bool(contains(join(mask, ":"), string(length(blocks)))) || bool(find(type(blocks), "array"))',
        '\tsniff ready',
        "\t\thoard finish(joined)",
        "\tshriek",
        "\t\thoard finish(joined)",
    )


def template_mirror_swap_match(text: str, mode: str = "embedded", seed: str = "program-demo") -> str:
    return make_obscured_program(
        mode,
        seed,
        "mirror_swap_match",
        "jungle PairBox",
        "\tleft",
        "\tright",
        "",
        "babuin main()",
        source_line("source", text),
        '\tbanana chars = rotate(reverse(split(source, "")), 1)',
        "\tbanana i = 0",
        "\tbanana boxes = []",
        "\tbanana box = PairBox()",
        "\tbanana left = \"\"",
        "\tbanana right = \"\"",
        "\tswing i < length(chars)",
        "\t\tleft = chars[i]",
        '\t\tright = ""',
        "\t\tsniff i + 1 < length(chars)",
        "\t\t\tright = chars[i + 1]",
        "\t\tbox = PairBox{ left = right, right = left }",
        "\t\tpush(boxes, box)",
        "\t\ti = i + 2",
        '\tbanana out = ""',
        "\tswing box in boxes",
        "\t\tmatch box",
        "\t\t\tas PairBox{ left = a, right = b } sniff bool(length(a) >= 0)",
        "\t\t\t\tout = out + a + b",
        "\t\t\tshriek",
        '\t\t\t\tout = out + ""',
        "\thoard finish(out)",
    )


TEMPLATES = [
    TemplateSpec("reverse_loop", "Reverse text with indexed insertion", ["split", "insert", "while_swing", "join", "length"], template_reverse_loop, lambda text: text[::-1], lambda text: text[::-1]),
    TemplateSpec("shift_records", "Shift printable characters through record fields", ["jungle", "record_literal", "record_match", "ord", "chr"], template_shift_records, lambda text: shift_printable(text, lambda _i, _ch: 1), lambda text: unshift_printable(text, lambda _i, _ch: 1)),
    TemplateSpec("odd_even_records", "Route odd and even characters through record matching", ["match", "record_literal", "indexed_swing", "join"], template_odd_even_records, lambda text: text[1::2] + text[0::2], invert_odd_even),
    TemplateSpec("eval_shift", "Compute character shifts through eval(format(...))", ["eval", "format", "int", "ord", "chr"], template_eval_shift, lambda text: shift_printable(text, lambda i, _ch: i % 3), lambda text: unshift_printable(text, lambda i, _ch: i % 3)),
    TemplateSpec("chunk_reverse", "Reverse two-byte chunks with slicing and insertion", ["slice", "insert", "split", "join", "while_swing"], template_chunk_reverse, lambda text: reverse_chunks(text, 2), lambda text: reverse_chunks(text, 2)),
    TemplateSpec("comprehension_rotate", "Rotate characters with array comprehensions", ["rotate", "array_comprehension", "split", "join"], template_comprehension_rotate, lambda text: "".join(rotate_left_list(list(text), 1)), lambda text: "".join(rotate_left_list(list(text), -1))),
    TemplateSpec("splice_swap", "Swap adjacent pairs with remove/insert", ["remove", "insert", "while_swing", "indexing"], template_splice_swap, swap_pairs, swap_pairs),
    TemplateSpec("reverse_rotate_xor", "Reverse/rotate and parity-shift through xor", ["reverse", "rotate", "xor", "indexed_swing", "ord", "chr"], template_reverse_rotate_xor, lambda text: shift_printable("".join(rotate_left_list(list(text[::-1]), 1)), lambda i, _ch: ((i ^ 1) % 3)), invert_reverse_rotate_xor),
    TemplateSpec("state_machine", "Weave characters through a dispatcher loop", ["state_machine", "truth", "fling", "scamper", "while_swing"], template_state_machine, lambda text: text[0::2] + text[1::2], invert_state_machine),
    TemplateSpec("panic_exit", "Reverse text and terminate with exit(0)", ["panic", "exit", "semicolons", "reverse"], template_panic_exit, lambda text: text[::-1], invert_panic_exit),
    TemplateSpec("parity_comprehension", "Shift printable characters with indexed comprehensions", ["array_comprehension", "ord", "chr", "indexed_swing"], template_parity_comprehension, lambda text: shift_printable(text, lambda i, _ch: i % 2), lambda text: unshift_printable(text, lambda i, _ch: i % 2)),
    TemplateSpec("stride_buckets", "Split characters into stride buckets and stitch them back through records", ["jungle", "match", "contains", "find", "hash"], template_stride_buckets, lambda text: stride_bucket_join(text, 3), lambda text: invert_stride_bucket(text, 3)),
    TemplateSpec("quadratic_shift", "Shift printable characters with quadratic indexed deltas", ["jungle", "eval", "format", "int", "indexed_swing"], template_quadratic_shift, lambda text: shift_printable(text, lambda i, _ch: ((i * i) + 3) % 7), lambda text: unshift_printable(text, lambda i, _ch: ((i * i) + 3) % 7)),
    TemplateSpec("block_rotate_maze", "Rotate characters and reverse three-byte blocks through a helper maze", ["rotate", "slice", "insert", "contains", "type"], template_block_rotate_maze, lambda text: block_rotate(text, 2, 3), lambda text: invert_block_rotate(text, 2, 3)),
    TemplateSpec("mirror_swap_match", "Mirror, rotate, and pair-swap characters through record matches", ["reverse", "rotate", "match", "jungle", "while_swing"], template_mirror_swap_match, mirror_swap_rotate, invert_mirror_swap_rotate),
]

TEMPLATE_MAP = {template.key: template for template in TEMPLATES}


def basic_direct_print(text: str) -> str:
    return make_program(
        "babuin main()",
        f"\tprint({babuin_string(text)})",
        '\tprint("\\n")',
        "\thoard 0",
    )


def basic_format_print(text: str) -> str:
    return make_program(
        "babuin main()",
        f"\tbanana text = format(\"{{}}\", {babuin_string(text)})",
        "\tprint(text)",
        '\tprint("\\n")',
        "\thoard 0",
    )


def basic_split_join(text: str) -> str:
    return make_program(
        "babuin main()",
        f"\tbanana chars = split({babuin_string(text)}, \"\")",
        '\tprint(join(chars, ""))',
        '\tprint("\\n")',
        "\thoard 0",
    )


def basic_foreach_string(text: str) -> str:
    return make_program(
        "babuin main()",
        f"\tbanana src = {babuin_string(text)}",
        '\tbanana out = ""',
        "\tswing idx, ch in src",
        "\t\tout = out + ch",
        "\tprint(out)",
        '\tprint("\\n")',
        "\thoard 0",
    )


def basic_index_loop(text: str) -> str:
    return make_program(
        "babuin main()",
        f"\tbanana src = {babuin_string(text)}",
        "\tbanana i = 0",
        '\tbanana out = ""',
        "\tswing i < length(src)",
        "\t\tout = out + src[i]",
        "\t\ti = i + 1",
        "\tprint(out)",
        '\tprint("\\n")',
        "\thoard 0",
    )


def basic_ord_chr(text: str) -> str:
    return make_program(
        "babuin main()",
        f"\tbanana src = {babuin_string(text)}",
        "\tbanana codes = []",
        "\tswing ch in src",
        "\t\tpush(codes, ord(ch))",
        '\tbanana out = ""',
        "\tswing code in codes",
        "\t\tout = out + chr(code)",
        "\tprint(out)",
        '\tprint("\\n")',
        "\thoard 0",
    )


def basic_record_box(text: str) -> str:
    return make_program(
        "jungle Message",
        "\ttext",
        "\tcount",
        "",
        "babuin main()",
        f"\tbanana box = Message{{ text = {babuin_string(text)}, count = length({babuin_string(text)}) }}",
        "\tbanana {text, count} = box",
        "\tprint(text)",
        '\tprint("\\n")',
        "\thoard count - count",
    )


def basic_match_record(text: str) -> str:
    return make_program(
        "jungle Message",
        "\ttext",
        "\ttag",
        "",
        "babuin main()",
        f"\tbanana box = Message{{ text = {babuin_string(text)}, tag = truth }}",
        '\tbanana out = ""',
        "\tmatch box",
        "\t\tas Message{ text = text, tag = truth }",
        "\t\t\tout = text",
        "\t\tshriek",
        f"\t\t\tout = {babuin_string(text)}",
        "\tprint(out)",
        '\tprint("\\n")',
        "\thoard 0",
    )


def basic_comprehension(text: str) -> str:
    return make_program(
        "babuin main()",
        f"\tbanana chars = [ch swing ch in split({babuin_string(text)}, \"\") sniff ch != \"\"]",
        '\tprint(join(chars, ""))',
        '\tprint("\\n")',
        "\thoard 0",
    )


def basic_reverse_rotate(text: str) -> str:
    return make_program(
        "babuin main()",
        f"\tbanana chars = rotate(reverse(reverse(split({babuin_string(text)}, \"\"))), length(split({babuin_string(text)}, \"\")))",
        '\tprint(join(chars, ""))',
        '\tprint("\\n")',
        "\thoard 0",
    )


def basic_slice_concat(text: str) -> str:
    mid = len(text) // 2
    return make_program(
        "babuin main()",
        f"\tbanana chars = split({babuin_string(text)}, \"\")",
        f"\tbanana left = join(slice(chars, 0, {mid}), \"\")",
        f"\tbanana right = join(slice(chars, {mid}, length(chars)), \"\")",
        "\tprint(left + right)",
        '\tprint("\\n")',
        "\thoard 0",
    )


def basic_insert_remove(text: str) -> str:
    return make_program(
        "babuin main()",
        f"\tbanana chars = split({babuin_string(text)}, \"\")",
        "\tbanana first = remove(chars, 0)",
        "\tinsert(chars, 0, first)",
        '\tprint(join(chars, ""))',
        '\tprint("\\n")',
        "\thoard 0",
    )


def basic_push_pop(text: str) -> str:
    return make_program(
        "babuin main()",
        "\tbanana chars = []",
        f"\tswing ch in {babuin_string(text)}",
        "\t\tpush(chars, ch)",
        '\tpush(chars, "")',
        "\tpop(chars)",
        '\tprint(join(chars, ""))',
        '\tprint("\\n")',
        "\thoard 0",
    )


def basic_contains_find(text: str) -> str:
    first = text[0]
    return make_program(
        "babuin main()",
        f"\tbanana src = {babuin_string(text)}",
        f"\tbanana ok = contains(src, {babuin_string(first)}) && (find(src, {babuin_string(first)}) >= 0)",
        "\tsniff ok",
        "\t\tprint(src)",
        '\t\tprint("\\n")',
        "\t\thoard 0",
        "\tshriek",
        '\t\tpanic("unexpected contains/find failure")',
    )


def basic_bool_gate(text: str) -> str:
    return make_program(
        "babuin main()",
        f"\tbanana src = {babuin_string(text)}",
        '\tbanana ok = bool("truth") && (int(truth) == 1) && (string(length(src)) != "")',
        "\tsniff ok",
        "\t\tprint(src)",
        '\t\tprint("\\n")',
        "\t\thoard 0",
        "\tshriek",
        '\t\tpanic("unexpected conversion gate failure")',
    )


def basic_type_hash(text: str) -> str:
    first = text[0]
    return make_program(
        "babuin main()",
        f"\tbanana chars = split({babuin_string(text)}, \"\")",
        '\tbanana tag = type(chars)',
        '\tbanana digest = hash(join(chars, ""))',
        f"\tsniff contains(tag, \"array\") && (find(digest, {babuin_string(first)}) >= -1)",
        '\t\tprint(join(chars, ""))',
        '\t\tprint("\\n")',
        "\t\thoard 0",
        "\tshriek",
        '\t\tpanic("unexpected type/hash failure")',
    )


def basic_state_machine(text: str) -> str:
    return make_program(
        "babuin main()",
        f"\tbanana chars = split({babuin_string(text)}, \"\")",
        "\tbanana state = 0",
        "\tbanana idx = 0",
        '\tbanana out = ""',
        "\tswing truth",
        "\t\tsniff state == 0",
        "\t\t\tsniff idx < length(chars)",
        "\t\t\t\tout = out + chars[idx]",
        "\t\t\t\tidx = idx + 1",
        "\t\t\t\tscamper",
        "\t\t\tfling",
        "\tprint(out)",
        '\tprint("\\n")',
        "\thoard 0",
    )


def basic_array_destructure(text: str) -> str:
    first = text[:1]
    second = text[1:2]
    tail = text[2:]
    return make_program(
        "babuin main()",
        f"\tbanana [first, second, tail] = [{babuin_string(first)}, {babuin_string(second)}, {babuin_string(tail)}]",
        "\tprint(first + second + tail)",
        '\tprint("\\n")',
        "\thoard 0",
    )


def basic_record_fields(text: str) -> str:
    return make_program(
        "jungle Packet",
        "\thead",
        "\tbody",
        "",
        "babuin main()",
        f"\tbanana packet = Packet{{ head = {babuin_string(text[: len(text) // 2])}, body = {babuin_string(text[len(text) // 2 :])} }}",
        "\tprint(packet.head + packet.body)",
        '\tprint("\\n")',
        "\thoard 0",
    )


def basic_eval_format(text: str) -> str:
    value = len(text)
    return make_program(
        "babuin main()",
        f'\tbanana expr = format("({{}} + {{}}) - {{}}", {value}, 2, 2)',
        "\tbanana seen = int(eval(expr))",
        f"\tsniff seen == {value}",
        f"\t\tprint({babuin_string(text)})",
        '\t\tprint("\\n")',
        "\t\thoard 0",
        "\tshriek",
        '\t\tpanic("unexpected eval result")',
    )


def basic_xor_gate(text: str) -> str:
    return make_program(
        "babuin main()",
        f"\tbanana src = {babuin_string(text)}",
        "\tbanana gate = xor(length(src), 0)",
        "\tsniff gate == length(src)",
        "\t\tprint(src)",
        '\t\tprint("\\n")',
        "\t\thoard 0",
        "\tshriek",
        '\t\tpanic("unexpected xor failure")',
    )


def basic_string_index_math(text: str) -> str:
    last = len(text) - 1
    return make_program(
        "babuin main()",
        f"\tbanana src = {babuin_string(text)}",
        f"\tbanana out = src[0] + join(slice(split(src, \"\"), 1, {last}), \"\") + src[{last}]",
        "\tprint(out)",
        '\tprint("\\n")',
        "\thoard 0",
    )


def basic_nested_match(text: str) -> str:
    return make_program(
        "jungle Wrap",
        "\titems",
        "\ttag",
        "",
        "babuin main()",
        f'\tbanana box = Wrap{{ items = split({babuin_string(text)}, ""), tag = "ok" }}',
        '\tbanana out = ""',
        "\tmatch box",
        "\t\tas Wrap{ items = items, tag = tag } sniff tag == \"ok\"",
        '\t\t\tmatch [join(items, ""), length(items) >= 0]',
        "\t\t\t\tas [value, ready] sniff ready == truth",
        '\t\t\t\t\tout = value',
        '\t\t\t\tshriek',
        f'\t\t\t\t\tout = {babuin_string(text)}',
        "\t\tshriek",
        f"\t\t\tout = {babuin_string(text)}",
        "\tprint(out)",
        '\tprint("\\n")',
        "\thoard 0",
    )


def basic_float_roundtrip(text: str) -> str:
    value = len(text) + 0.5
    return make_program(
        "babuin main()",
        f'\tbanana probe = float("{value}")',
        f"\tsniff probe > {len(text)}",
        f"\t\tprint({babuin_string(text)})",
        '\t\tprint("\\n")',
        "\t\thoard 0",
        "\tshriek",
        '\t\tpanic("unexpected float roundtrip failure")',
    )


def basic_format_segments(text: str) -> str:
    left = text[: len(text) // 2]
    right = text[len(text) // 2 :]
    return make_program(
        "babuin main()",
        f'\tbanana out = format("{{}}{{}}", {babuin_string(left)}, {babuin_string(right)})',
        "\tprint(out)",
        '\tprint("\\n")',
        "\thoard 0",
    )


def basic_match_array(text: str) -> str:
    return make_program(
        "babuin main()",
        f'\tbanana chars = split({babuin_string(text)}, "")',
        '\tbanana out = ""',
        "\tmatch chars",
        "\t\tas [first, second, tail]",
        '\t\t\tout = first + second + tail',
        "\t\tshriek",
        f"\t\t\tout = {babuin_string(text)}",
        "\tprint(out)",
        '\tprint("\\n")',
        "\thoard 0",
    )


def basic_join_format(text: str) -> str:
    pieces = [text[:1], text[1:3], text[3:]]
    return make_program(
        "babuin main()",
        f"\tbanana chunks = [{babuin_string(pieces[0])}, {babuin_string(pieces[1])}, {babuin_string(pieces[2])}]",
        '\tbanana out = format("{}", join(chunks, ""))',
        "\tprint(out)",
        '\tprint("\\n")',
        "\thoard 0",
    )


BASIC_PRINT_TEMPLATES = [
    BasicTemplateSpec("direct_print", "Direct print of the literal", ["print", "string_literal"], basic_direct_print),
    BasicTemplateSpec("format_print", "Format-based direct print", ["format", "print"], basic_format_print),
    BasicTemplateSpec("split_join", "Split and join the string", ["split", "join"], basic_split_join),
    BasicTemplateSpec("foreach_string", "Foreach loop over string characters", ["swing_foreach", "string_iteration"], basic_foreach_string),
    BasicTemplateSpec("index_loop", "While-style indexed loop over a string", ["swing_while", "indexing", "length"], basic_index_loop),
    BasicTemplateSpec("ord_chr", "Round-trip through ord/chr", ["ord", "chr", "push"], basic_ord_chr),
    BasicTemplateSpec("record_box", "Store text in a jungle record", ["jungle", "record_literal", "record_destructure"], basic_record_box),
    BasicTemplateSpec("match_record", "Recover text through record match", ["match", "as", "jungle"], basic_match_record),
    BasicTemplateSpec("comprehension", "Identity array comprehension", ["array_comprehension", "split", "join"], basic_comprehension),
    BasicTemplateSpec("reverse_rotate", "Identity reverse/rotate pipeline", ["reverse", "rotate", "length"], basic_reverse_rotate),
    BasicTemplateSpec("slice_concat", "Slice and concatenate halves", ["slice", "length"], basic_slice_concat),
    BasicTemplateSpec("insert_remove", "Mutate an array with remove/insert", ["remove", "insert"], basic_insert_remove),
    BasicTemplateSpec("push_pop", "Build array with push/pop", ["push", "pop"], basic_push_pop),
    BasicTemplateSpec("contains_find", "Guard output with contains/find", ["contains", "find", "sniff"], basic_contains_find),
    BasicTemplateSpec("bool_gate", "Guard output with conversions", ["bool", "int", "string"], basic_bool_gate),
    BasicTemplateSpec("type_hash", "Use type/hash before printing", ["type", "hash", "contains", "find"], basic_type_hash),
    BasicTemplateSpec("state_machine", "Simple dispatcher loop", ["truth", "fling", "scamper", "swing_while"], basic_state_machine),
    BasicTemplateSpec("array_destructure", "Rebuild text through array destructuring", ["array_literal", "array_destructure"], basic_array_destructure),
    BasicTemplateSpec("record_fields", "Read jungle record fields directly", ["jungle", "field_access"], basic_record_fields),
    BasicTemplateSpec("eval_format", "Validate text path through eval(format(...))", ["eval", "format", "int"], basic_eval_format),
    BasicTemplateSpec("xor_gate", "Guard print through xor identity", ["xor", "length", "sniff"], basic_xor_gate),
    BasicTemplateSpec("string_index_math", "Mix indexing, slice, and join", ["indexing", "slice", "join"], basic_string_index_math),
    BasicTemplateSpec("nested_match", "Recover text through nested match arms", ["match", "as", "truth"], basic_nested_match),
    BasicTemplateSpec("float_roundtrip", "Validate output with float conversion", ["float", "sniff"], basic_float_roundtrip),
    BasicTemplateSpec("format_segments", "Assemble text with multiple format placeholders", ["format", "string_literal"], basic_format_segments),
    BasicTemplateSpec("match_array", "Recover text through array shape matching", ["match", "array_pattern"], basic_match_array),
    BasicTemplateSpec("join_format", "Wrap join output in format", ["join", "format", "array_literal"], basic_join_format),
]

BASIC_PRINT_TEMPLATE_MAP = {template.key: template for template in BASIC_PRINT_TEMPLATES}


def random_identifier(rng: random.Random, original: str) -> str:
    alphabet = "abcdefghijklmnopqrstuvwxyz0123456789"
    head_alphabet = "abcdefghijklmnopqrstuvwxyz"
    size = rng.randint(6, 12)
    body = "".join(rng.choice(alphabet) for _ in range(size - 1))
    head = rng.choice(head_alphabet)
    token = head + body
    if original and original[0].isupper():
        token = token.capitalize()
    return token


def collect_renamable_identifiers(source: str) -> list[str]:
    identifiers: list[str] = []
    seen: set[str] = set()
    patterns = [
        re.compile(r"^\s*jungle\s+([A-Za-z_][A-Za-z0-9_]*)\s*$"),
        re.compile(r"^\s*babuin\s+([A-Za-z_][A-Za-z0-9_]*)\s*\("),
        re.compile(r"\bbanana\s+([A-Za-z_][A-Za-z0-9_]*)\b"),
    ]
    for raw_line in source.splitlines():
        line = raw_line.split("//", 1)[0]
        for pattern in patterns:
            for match in pattern.finditer(line):
                token = match.group(1)
                if token == "main":
                    continue
                if token in RESERVED_WORDS or token in BUILTIN_NAMES:
                    continue
                if token not in seen:
                    seen.add(token)
                    identifiers.append(token)
    return identifiers


def replace_identifiers_in_source(source: str, mapping: dict[str, str]) -> str:
    out: list[str] = []
    i = 0
    while i < len(source):
        ch = source[i]
        if ch == '"':
            start = i
            i += 1
            while i < len(source):
                if source[i] == "\\" and i + 1 < len(source):
                    i += 2
                    continue
                if source[i] == '"':
                    i += 1
                    break
                i += 1
            out.append(source[start:i])
            continue
        if ch == "/" and i + 1 < len(source) and source[i + 1] == "/":
            start = i
            while i < len(source) and source[i] != "\n":
                i += 1
            out.append(source[start:i])
            continue
        if ch.isalpha() or ch == "_":
            start = i
            i += 1
            while i < len(source) and (source[i].isalnum() or source[i] == "_"):
                i += 1
            token = source[start:i]
            if start > 0 and source[start - 1].isdigit():
                out.append(token)
            else:
                out.append(mapping.get(token, token))
            continue
        out.append(ch)
        i += 1
    return "".join(out)


def replace_identifiers_in_text(text: str, mapping: dict[str, str]) -> str:
    if not mapping:
        return text
    pattern = re.compile(r"\b(" + "|".join(sorted((re.escape(key) for key in mapping), key=len, reverse=True)) + r")\b")
    return pattern.sub(lambda match: mapping[match.group(0)], text)


def mutate_fail_case(source: str, err_text: str, seed: str, stem: str) -> tuple[str, str]:
    rng = random.Random(f"{seed}:{stem}")
    mapping: dict[str, str] = {}
    for name in collect_renamable_identifiers(source):
        mapping[name] = random_identifier(rng, name)
    mutated_source = replace_identifiers_in_source(source, mapping)
    mutated_err = replace_identifiers_in_text(err_text, mapping)
    return mutated_source, mutated_err


def make_basic_variant_scaffold(seed: str, stem: str) -> tuple[str, str]:
    rng = random.Random(f"basic-variant:{seed}:{stem}")
    helper_name = random_identifier(rng, "helper")
    local_seed = random_identifier(rng, "seed")
    local_chars = random_identifier(rng, "chars")
    local_tag = random_identifier(rng, "tag")
    local_gate = random_identifier(rng, "gate")
    token = fnv1a_hex(f"{seed}:{stem}")[:8]
    scaffold = make_program(
        f"babuin {helper_name}(text)",
        f'\tbanana {local_seed} = "{token}"',
        f'\tbanana {local_chars} = split(text, "")',
        f'\tbanana {local_tag} = format("{{}}:{{}}", length({local_seed}), length({local_chars}))',
        f'\tbanana {local_gate} = contains({local_tag}, ":") && bool(find(type({local_chars}), "array"))',
        f"\tsniff {local_gate}",
        '\t\thoard join(rotate(reverse(reverse(' + local_chars + ')), length(' + local_chars + ')), "")',
        "\tshriek",
        "\t\thoard text",
    )
    return scaffold, helper_name


def mutate_basic_case(source: str, seed: str, stem: str) -> str:
    rng = random.Random(f"basic-case:{seed}:{stem}")
    mapping: dict[str, str] = {}
    for name in collect_renamable_identifiers(source):
        mapping[name] = random_identifier(rng, name)
    mutated_source = replace_identifiers_in_source(source, mapping)
    helper_scaffold, helper_name = make_basic_variant_scaffold(seed, stem)
    if "babuin main()\n" not in mutated_source:
        return helper_scaffold + "\n" + mutated_source
    mutated_source = mutated_source.replace("babuin main()\n", helper_scaffold + "\n" + "babuin main()\n", 1)
    local_hook = random_identifier(rng, "hook")
    mutated_source, count = re.subn(
        r"(?m)^\tprint\((.+)\)$",
        f"\tbanana {local_hook} = {helper_name}(\\1)\n\tprint({local_hook})",
        mutated_source,
        count=1,
    )
    if count == 0:
        return helper_scaffold + "\n" + replace_identifiers_in_source(source, mapping)
    return mutated_source


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate babuin storage programs or bundles")
    parser.add_argument("--kind", choices=["flagstore", "flagload", "basic-bundle", "error-bundle"], default="flagstore", help="Program kind to generate")
    parser.add_argument("--output-text", help="Printable ASCII text that a print program must print")
    parser.add_argument("--storage-id", help="Storage ID used by flagstore and flagload programs")
    parser.add_argument("--storage-key", help="Storage access key used by flagstore and flagload programs")
    parser.add_argument("--flag", help="Flag value used by flagstore programs")
    parser.add_argument("--program", help="Path to the output .bbn program")
    parser.add_argument("--output-dir", help="Directory where a generated bundle should be written")
    parser.add_argument("--template", choices=sorted(TEMPLATE_MAP), help="Specific template to use; random if omitted")
    parser.add_argument("--seed", default="program-demo", help="Deterministic seed used when choosing a random template")
    parser.add_argument("--verify", action="store_true", help="Run the generated program with the given interpreter and check output")
    parser.add_argument("--interpreter", help="Path to babuinterpreter executable used with --verify")
    return parser.parse_args()


def validate_text(text: str, label: str = "text", forbid_pipe: bool = False) -> None:
    if not text:
        raise ValueError(f"{label} must not be empty")
    for ch in text:
        code = ord(ch)
        if code < 32 or code > 126:
            raise ValueError(f"{label} must use printable ASCII characters only")
        if forbid_pipe and ch == "|":
            raise ValueError(f"{label} must not contain '|'")


def build_generation_request(args: argparse.Namespace) -> tuple[str, str, str]:
    kind = args.kind
    if kind == "basic-bundle":
        if args.output_text is None:
            raise ValueError("--output-text is required for --kind basic-bundle")
        validate_text(args.output_text, "output text")
        return kind, args.output_text, args.output_text + "\n"
    if kind == "error-bundle":
        return kind, "", ""
    if args.storage_id is None or args.storage_key is None:
        raise ValueError(f"--storage-id and --storage-key are required for --kind {kind}")
    validate_text(args.storage_id, "storage ID", forbid_pipe=True)
    validate_text(args.storage_key, "storage key", forbid_pipe=True)
    if args.output_text is None:
        raise ValueError(f"--output-text is required for --kind {kind}")
    validate_text(args.output_text, "output text", forbid_pipe=True)
    if kind == "flagstore":
        if args.flag is None:
            raise ValueError("--flag is required for --kind flagstore")
        validate_text(args.flag, "flag", forbid_pipe=True)
        return kind, f"{args.storage_id}|{args.storage_key}|{args.flag}|{args.output_text}", args.flag + "\n" + args.output_text + "\n"
    if kind == "flagload":
        return kind, f"{args.storage_id}|{args.storage_key}|{args.output_text}", ""
    raise ValueError(f"unsupported generator kind: {kind}")


def choose_template(seed: str, key: str | None) -> TemplateSpec:
    if key is not None:
        return TEMPLATE_MAP[key]
    rng = random.Random(seed)
    return rng.choice(TEMPLATES)


def choose_basic_template(seed: str, key: str | None) -> BasicTemplateSpec:
    if key is not None:
        return BASIC_PRINT_TEMPLATE_MAP[key]
    rng = random.Random(seed)
    return rng.choice(BASIC_PRINT_TEMPLATES)


def run_program(interpreter: Path, program: Path, stdin_text: str) -> tuple[int, str, str]:
    with tempfile.TemporaryDirectory(prefix="babuinterpreter-template-storage-") as tmp:
        env = os.environ.copy()
        env["BABUIN_STORAGE_PATH"] = str(Path(tmp) / "storage.sqlite")
        proc = subprocess.run(
            [str(interpreter), str(program)],
            input=stdin_text,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=env,
        )
        return proc.returncode, proc.stdout, proc.stderr


def build_generated_program(
    kind: str,
    seed: str = "program-demo",
    template_key: str | None = None,
    output_text: str | None = None,
    storage_id: str | None = None,
    storage_key: str | None = None,
    flag: str | None = None,
) -> GeneratedProgram:
    class Request:
        pass

    req = Request()
    req.kind = kind
    req.seed = seed
    req.template = template_key
    req.output_text = output_text
    req.storage_id = storage_id
    req.storage_key = storage_key
    req.flag = flag
    req.program = None
    req.output_dir = None
    req.verify = False
    req.interpreter = None
    kind_value, payload_text, expected_stdout = build_generation_request(req)  # type: ignore[arg-type]
    if kind_value in {"basic-bundle", "error-bundle"}:
        raise ValueError(f"use bundle helpers for kind {kind_value}")
    template = choose_template(seed, template_key)
    source_text = template.inverse(payload_text)
    program_text = template.render(source_text, kind_value, seed)
    manifest = {
        "seed": seed,
        "kind": kind_value,
        "template": template.key,
        "payload_text": payload_text,
        "expected_stdout": expected_stdout,
        "features": template.features,
        "summary": template.summary,
    }
    return GeneratedProgram(
        kind=kind_value,
        seed=seed,
        template=template.key,
        payload_text=payload_text,
        expected_stdout=expected_stdout,
        program_text=program_text,
        manifest=manifest,
    )


def generate_flagstore_program(
    storage_id: str,
    storage_key: str,
    flag: str,
    output_text: str,
    seed: str = "program-demo",
    template_key: str | None = None,
) -> str:
    return build_generated_program(
        kind="flagstore",
        seed=seed,
        template_key=template_key,
        output_text=output_text,
        storage_id=storage_id,
        storage_key=storage_key,
        flag=flag,
    ).program_text


def generate_flagload_program(
    storage_id: str,
    storage_key: str,
    output_text: str,
    seed: str = "program-demo",
    template_key: str | None = None,
) -> str:
    return build_generated_program(
        kind="flagload",
        seed=seed,
        template_key=template_key,
        output_text=output_text,
        storage_id=storage_id,
        storage_key=storage_key,
    ).program_text


def generate_basic_program(
    output_text: str,
    seed: str = "program-demo",
    template_key: str | None = None,
) -> str:
    validate_text(output_text, "output text")
    template = choose_basic_template(seed, template_key)
    program_text = mutate_basic_case(template.render(output_text), seed, template.key)
    return program_text


def generate_error_program(
    seed: str = "program-demo",
    case_name: str | None = None,
) -> tuple[str, str]:
    cases = load_error_cases()
    case_map = {case["case_name"]: case for case in cases}
    if case_name is None:
        rng = random.Random(seed)
        case_name = rng.choice(ERROR_CASE_NAMES)
    if case_name not in case_map:
        raise ValueError(f"unknown error case: {case_name}")
    case = case_map[case_name]
    source_text = case["program_text"]
    err_text = case["expected_error_substring"]
    out_text = case["expected_stdout"]
    mutated_source, mutated_err = mutate_fail_case(source_text, err_text, seed, case_name)
    manifest = {
        "kind": "error-program",
        "seed": seed,
        "case_name": case_name,
        "expected_error_substring": mutated_err.strip(),
        "expected_stdout": out_text,
    }
    del out_text, manifest
    return mutated_source, mutated_err.strip()


def write_generated_program(result: GeneratedProgram, program_path: Path) -> None:
    write_program_artifacts(program_path, result.program_text, result.expected_stdout, result.manifest)


def write_generated_error_program(result: GeneratedErrorProgram, program_path: Path) -> None:
    program_path.parent.mkdir(parents=True, exist_ok=True)
    program_path.write_text(result.program_text, encoding="utf-8")
    program_path.with_suffix(".out").write_text(result.expected_stdout, encoding="utf-8")
    program_path.with_suffix(".err").write_text(result.expected_error_substring + ("\n" if result.expected_error_substring else ""), encoding="utf-8")
    in_path = program_path.with_suffix(".in")
    if in_path.exists():
        in_path.unlink()
    program_path.with_suffix(".json").write_text(json.dumps(result.manifest, indent=2), encoding="utf-8")


def write_program_artifacts(program_path: Path, program_text: str, expected_stdout: str, manifest: dict) -> None:
    program_path.parent.mkdir(parents=True, exist_ok=True)
    program_path.write_text(program_text, encoding="utf-8")
    program_path.with_suffix(".out").write_text(expected_stdout, encoding="utf-8")
    in_path = program_path.with_suffix(".in")
    if in_path.exists():
        in_path.unlink()
    program_path.with_suffix(".json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")


def generate_basic_bundle(output_dir: Path, output_text: str, seed: str, verify: bool, interpreter: str | None, announce: bool = True) -> int:
    output_dir.mkdir(parents=True, exist_ok=True)
    programs_manifest: list[dict] = []
    for index, template in enumerate(BASIC_PRINT_TEMPLATES, start=1):
        program_path = output_dir / f"{index:02d}_{template.key}.bbn"
        expected_stdout = output_text + "\n"
        manifest = {
            "seed": seed,
            "kind": "basic-bundle",
            "template": template.key,
            "payload_text": output_text,
            "expected_stdout": expected_stdout,
            "features": template.features,
            "summary": template.summary,
        }
        program_text = mutate_basic_case(template.render(output_text), seed, template.key)
        write_program_artifacts(program_path, program_text, expected_stdout, manifest)
        programs_manifest.append(
            {
                "template": template.key,
                "program": program_path.name,
                "features": template.features,
                "summary": template.summary,
            }
        )
        if verify:
            if not interpreter:
                raise ValueError("--verify requires --interpreter")
            code, out, err = run_program(Path(interpreter), program_path, "")
            if code != 0 or out != expected_stdout or err != "":
                print(
                    f"verification failed for {program_path.name}: expected exit=0 stdout={expected_stdout!r} stderr=''; got exit={code} stdout={out!r} stderr={err!r}",
                    file=sys.stderr,
                )
                return 1
    bundle_manifest = {
        "seed": seed,
        "kind": "basic-bundle",
        "payload_text": output_text,
        "count": len(BASIC_PRINT_TEMPLATES),
        "programs": programs_manifest,
    }
    (output_dir / "manifest.json").write_text(json.dumps(bundle_manifest, indent=2), encoding="utf-8")
    if announce:
        print(f"generated basic print bundle in {output_dir}")
    return 0


def generate_error_bundle(output_dir: Path, seed: str, announce: bool = True) -> int:
    output_dir.mkdir(parents=True, exist_ok=True)
    cases: list[dict] = []
    for case in load_error_cases():
        stem = case["case_name"]
        dest_program = output_dir / f"{stem}.bbn"
        source_text = case["program_text"]
        err_text = case["expected_error_substring"]
        out_text = case["expected_stdout"]
        in_text = case["stdin_text"]
        mutated_source, mutated_err = mutate_fail_case(source_text, err_text, seed, stem)
        dest_program.write_text(mutated_source, encoding="utf-8")
        (output_dir / f"{stem}.err").write_text(mutated_err, encoding="utf-8")
        (output_dir / f"{stem}.out").write_text(out_text, encoding="utf-8")
        if in_text:
            (output_dir / f"{stem}.in").write_text(in_text, encoding="utf-8")
        manifest = {
            "kind": "error-bundle",
            "seed": seed,
            "program": dest_program.name,
            "expected_error_substring": mutated_err.strip(),
            "has_stdin": bool(in_text),
        }
        (output_dir / f"{stem}.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        cases.append(manifest)
    bundle_manifest = {
        "kind": "error-bundle",
        "seed": seed,
        "count": len(cases),
        "programs": cases,
    }
    (output_dir / "manifest.json").write_text(json.dumps(bundle_manifest, indent=2), encoding="utf-8")
    if announce:
        print(f"generated error bundle in {output_dir}")
    return 0


def main() -> int:
    args = parse_args()
    kind, payload_text, expected_stdout = build_generation_request(args)
    if kind == "basic-bundle":
        if not args.output_dir:
            raise ValueError("--output-dir is required for --kind basic-bundle")
        return generate_basic_bundle(Path(args.output_dir), payload_text, args.seed, args.verify, args.interpreter)
    if kind == "error-bundle":
        if not args.output_dir:
            raise ValueError("--output-dir is required for --kind error-bundle")
        return generate_error_bundle(Path(args.output_dir), args.seed)
    if not args.program:
        raise ValueError("--program is required for this generator kind")
    program_path = Path(args.program)
    result = build_generated_program(
        kind=kind,
        seed=args.seed,
        template_key=args.template,
        output_text=args.output_text,
        storage_id=args.storage_id,
        storage_key=args.storage_key,
        flag=args.flag,
    )
    write_generated_program(result, program_path)

    if args.verify:
        if not args.interpreter:
            raise ValueError("--verify requires --interpreter")
        code, out, err = run_program(Path(args.interpreter), program_path, "")
        if code != 0 or out != result.expected_stdout or err != "":
            print(
                f"verification failed: expected exit=0 stdout={result.expected_stdout!r} stderr=''; got exit={code} stdout={out!r} stderr={err!r}",
                file=sys.stderr,
            )
            return 1

    print(f"generated {program_path} with template {result.template}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
