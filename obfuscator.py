"""
AUCM (Stands for "Are you challenging me?"). Python's Best friend. But very mean to anyone who hurts python or decides to snoop on python.
"""
import argparse
import ast
import builtins as bt
import json
import keyword
import marshal
import os
import random
import secrets
import struct
import time
import sys
import types
import unicodedata
from io import BytesIO
from pathlib import Path
import bz2
import lzma
import zlib
from concurrent.futures import ProcessPoolExecutor
import hashlib
import hmac
import base64
import importlib.util
try:
    IS_PACKAGABLE = True
    from setuptools import Extension, setup
    from Cython.Build import cythonize
    import PyInstaller.__main__
except ImportError:
    print("PyInstaller, Cython, Setuptools and Crytography are required to build an executable")
    IS_PACKAGABLE = False


class Uglifier(ast.NodeTransformer):
    def __init__(self):
        self.confusables = [
            "а",
            "е",
            "о",
            "р",
            "с",
            "у",
            "х",
            "α",
            "β",
            "γ",
            "δ",
            "ε",
            "ζ",
            "η",
            "θ",
            "Ⅰ",
            "Ⅱ",
            "Ⅲ",
            "Ⅳ",
            "Ⅴ",
            "ㅏ",
            "ㅑ",
            "ㅓ",
            "ㅕ",
            "ㅗ",
            "ㅛ",
            "ㅜ",
            "ㅠ",
            "ㅡ",
            "ㅣ",
            chr(12644),
        ]
        self.scope_stack = [True]
        self.name_map_stack = [{}]
        self.import_bindings_stack = [set()]

    def _generate_confusables(self, amount: int):
        return "".join(
            self.confusables[random.randint(0, len(self.confusables) - 1)]
            for _ in range(amount)
        )

    def _generate_urandom_key(self):
        while True:
            candidate = (
                f"_{self._generate_confusables(random.randint(5, 12))}"
                f"{secrets.token_hex(6)}"
                f"{self._generate_confusables(random.randint(5, 12))}"
            )
            candidate = unicodedata.normalize("NFKC", candidate)
            if candidate.isidentifier() and not keyword.iskeyword(candidate):
                return candidate

    def _get_or_create_key(self, original_name):
        if original_name.startswith("__") and original_name.endswith("__"):
            return None
        if original_name in set(dir(bt)):
            return None
        current_map = self.name_map_stack[-1]
        if original_name not in current_map:
            current_map[original_name] = self._generate_urandom_key()
        return current_map[original_name]

    def _make_dict_access(self, dict_func_name, key_str):
        dict_call = ast.Call(
            func=ast.Name(id=dict_func_name, ctx=ast.Load()),
            args=[],
            keywords=[],
        )
        return ast.Subscript(
            value=dict_call,
            slice=ast.Constant(value=key_str),
            ctx=ast.Load(),
        )

    def _make_store_target(self, key_str, is_global_scope):
        if is_global_scope:
            globals_call = ast.Call(
                func=ast.Name(id="globals", ctx=ast.Load()),
                args=[],
                keywords=[],
            )
            return ast.Subscript(
                value=globals_call,
                slice=ast.Constant(value=key_str),
                ctx=ast.Store(),
            )
        return ast.Name(id=key_str, ctx=ast.Store())

    def _iter_target_names(self, target):
        if isinstance(target, ast.Name):
            yield target.id
        elif isinstance(target, (ast.Tuple, ast.List)):
            for elt in target.elts:
                yield from self._iter_target_names(elt)
        elif isinstance(target, ast.Starred):
            yield from self._iter_target_names(target.value)

    def _rewrite_store_target(self, target, is_global_scope):
        if isinstance(target, ast.Name):
            key = self._get_or_create_key(target.id)
            return self._make_store_target(key, is_global_scope) if key else target
        if isinstance(target, ast.Tuple):
            target.elts = [self._rewrite_store_target(e, is_global_scope) for e in target.elts]
            return target
        if isinstance(target, ast.List):
            target.elts = [self._rewrite_store_target(e, is_global_scope) for e in target.elts]
            return target
        if isinstance(target, ast.Starred):
            target.value = self._rewrite_store_target(target.value, is_global_scope)
            return target
        return self.visit(target)

    def visit_Assign(self, node):
        is_global_scope = self.scope_stack[-1]
        for target in node.targets:
            for name in self._iter_target_names(target):
                self._get_or_create_key(name)

        node.value = self.visit(node.value)

        new_targets = []
        for target in node.targets:
            new_targets.append(self._rewrite_store_target(target, is_global_scope))

        node.targets = new_targets
        return node

    def visit_NamedExpr(self, node):
        is_global_scope = self.scope_stack[-1]
        if isinstance(node.target, ast.Name):
            self._get_or_create_key(node.target.id)

        node.value = self.visit(node.value)
        if isinstance(node.target, ast.Name):
            key = self._get_or_create_key(node.target.id)
            if key:
                node.target = self._make_store_target(key, is_global_scope)
        return node

    def visit_For(self, node):
        is_global_scope = self.scope_stack[-1]
        for name in self._iter_target_names(node.target):
            self._get_or_create_key(name)

        node.iter = self.visit(node.iter)
        node.body = [self.visit(n) for n in node.body]
        node.orelse = [self.visit(n) for n in node.orelse]

        node.target = self._rewrite_store_target(node.target, is_global_scope)
        return node

    def visit_With(self, node):
        for item in node.items:
            if item.optional_vars:
                for name in self._iter_target_names(item.optional_vars):
                    self._get_or_create_key(name)
            item.context_expr = self.visit(item.context_expr)

        node.body = [self.visit(n) for n in node.body]

        for item in node.items:
            if item.optional_vars:
                item.optional_vars = self._rewrite_store_target(
                    item.optional_vars, self.scope_stack[-1]
                )
        return node

    def visit_Name(self, node):
        if isinstance(node.ctx, ast.Load):
            for scope_map in reversed(self.name_map_stack):
                if node.id in scope_map:
                    key = scope_map[node.id]
                    scope_idx = list(reversed(self.name_map_stack)).index(scope_map)
                    actual_idx = len(self.name_map_stack) - 1 - scope_idx
                    if actual_idx == 0:
                        if node.id in self.import_bindings_stack[actual_idx]:
                            return ast.Name(id=key, ctx=ast.Load())
                        return self._make_dict_access("globals", key)
                    return ast.Name(id=key, ctx=ast.Load())
        return node

    def visit_FunctionDef(self, node):
        key = self._get_or_create_key(node.name)
        self.scope_stack.append(False)
        self.name_map_stack.append({})
        self.import_bindings_stack.append(set())

        node.args = self.visit(node.args)
        node.decorator_list = [self.visit(dec) for dec in node.decorator_list]
        if node.returns:
            node.returns = self.visit(node.returns)
        node.body = [self.visit(n) for n in node.body]

        self.scope_stack.pop()
        self.name_map_stack.pop()
        self.import_bindings_stack.pop()

        if key:
            node.name = key
        return node

    def visit_AsyncFunctionDef(self, node):
        key = self._get_or_create_key(node.name)
        self.scope_stack.append(False)
        self.name_map_stack.append({})
        self.import_bindings_stack.append(set())

        node.args = self.visit(node.args)
        node.decorator_list = [self.visit(dec) for dec in node.decorator_list]
        if node.returns:
            node.returns = self.visit(node.returns)
        node.body = [self.visit(n) for n in node.body]

        self.scope_stack.pop()
        self.name_map_stack.pop()
        self.import_bindings_stack.pop()

        if key:
            node.name = key
        return node

    def visit_Call(self, node):
        node.func = self.visit(node.func)
        node.args = [self.visit(arg) for arg in node.args]
        node.keywords = [self.visit(kw) for kw in node.keywords]
        return node

    def visit_Import(self, node):
        for alias in node.names:
            bound_name = alias.asname or alias.name.split(".")[0]
            key = self._get_or_create_key(bound_name)
            self.import_bindings_stack[-1].add(bound_name)
            if key:
                alias.asname = key
        return node

    def visit_ImportFrom(self, node):
        for alias in node.names:
            if alias.name == "*":
                continue
            bound_name = alias.asname or alias.name
            key = self._get_or_create_key(bound_name)
            self.import_bindings_stack[-1].add(bound_name)
            if key:
                alias.asname = key
        return node

    def visit_ClassDef(self, node):
        key = self._get_or_create_key(node.name)
        if key:
            node.name = key
        node.bases = [self.visit(base) for base in node.bases]
        node.keywords = [self.visit(kw) for kw in node.keywords]
        node.decorator_list = [self.visit(dec) for dec in node.decorator_list]
        self.scope_stack.append(False)
        self.name_map_stack.append({})
        self.import_bindings_stack.append(set())
        node.body = [self.visit(n) for n in node.body]
        self.scope_stack.pop()
        self.name_map_stack.pop()
        self.import_bindings_stack.pop()
        return node

    def visit_arg(self, node):
        key = self._get_or_create_key(node.arg)
        if key:
            node.arg = key
        return node

    def visit_ExceptHandler(self, node):
        if node.name:
            key = self._get_or_create_key(node.name)
            if key:
                node.name = key
        node.body = [self.visit(n) for n in node.body]
        return node

    def visit_comprehension(self, node):
        if isinstance(node.target, ast.Name):
            self._get_or_create_key(node.target.id)
        node.iter = self.visit(node.iter)
        node.ifs = [self.visit(clause) for clause in node.ifs]
        if isinstance(node.target, ast.Name):
            key = self._get_or_create_key(node.target.id)
            if key:
                node.target = self._make_store_target(key, self.scope_stack[-1])
        return node

    def visit_ListComp(self, node):
        self.scope_stack.append(False)
        self.name_map_stack.append({})
        self.import_bindings_stack.append(set())
        node.generators = [self.visit_comprehension(gen) for gen in node.generators]
        node.elt = self.visit(node.elt)
        self.scope_stack.pop()
        self.name_map_stack.pop()
        self.import_bindings_stack.pop()
        return node

    def visit_SetComp(self, node):
        self.scope_stack.append(False)
        self.name_map_stack.append({})
        self.import_bindings_stack.append(set())
        node.generators = [self.visit_comprehension(gen) for gen in node.generators]
        node.elt = self.visit(node.elt)
        self.scope_stack.pop()
        self.name_map_stack.pop()
        self.import_bindings_stack.pop()
        return node

    def visit_DictComp(self, node):
        self.scope_stack.append(False)
        self.name_map_stack.append({})
        self.import_bindings_stack.append(set())
        node.generators = [self.visit_comprehension(gen) for gen in node.generators]
        node.key = self.visit(node.key)
        node.value = self.visit(node.value)
        self.scope_stack.pop()
        self.name_map_stack.pop()
        self.import_bindings_stack.pop()
        return node

    def visit_GeneratorExp(self, node):
        self.scope_stack.append(False)
        self.name_map_stack.append({})
        self.import_bindings_stack.append(set())
        node.generators = [self.visit_comprehension(gen) for gen in node.generators]
        node.elt = self.visit(node.elt)
        self.scope_stack.pop()
        self.name_map_stack.pop()
        self.import_bindings_stack.pop()
        return node

    def visit_If(self, node):
        node.test = self.visit(node.test)
        node.body = [self.visit(n) for n in node.body]
        node.orelse = [self.visit(n) for n in node.orelse]
        return node

    def visit_While(self, node):
        node.test = self.visit(node.test)
        node.body = [self.visit(n) for n in node.body]
        node.orelse = [self.visit(n) for n in node.orelse]
        return node

    def visit_Return(self, node):
        if node.value:
            node.value = self.visit(node.value)
        return node

    def visit_Expr(self, node):
        node.value = self.visit(node.value)
        return node

    def visit_IfExp(self, node):
        node.test = self.visit(node.test)
        node.body = self.visit(node.body)
        node.orelse = self.visit(node.orelse)
        return node

    def visit_BinOp(self, node):
        node.left = self.visit(node.left)
        node.right = self.visit(node.right)
        return node

    def visit_UnaryOp(self, node):
        node.operand = self.visit(node.operand)
        return node

    def visit_Compare(self, node):
        node.left = self.visit(node.left)
        node.comparators = [self.visit(comp) for comp in node.comparators]
        return node

    def visit_BoolOp(self, node):
        node.values = [self.visit(val) for val in node.values]
        return node

    def visit_Subscript(self, node):
        node.value = self.visit(node.value)
        node.slice = self.visit(node.slice)
        return node

    def visit_Attribute(self, node):
        node.value = self.visit(node.value)
        return node

    def visit_Tuple(self, node):
        node.elts = [self.visit(elt) for elt in node.elts]
        return node

    def visit_List(self, node):
        node.elts = [self.visit(elt) for elt in node.elts]
        return node

    def visit_Dict(self, node):
        node.keys = [self.visit(key) for key in node.keys]
        node.values = [self.visit(value) for value in node.values]
        return node

    def visit_JoinedStr(self, node):
        node.values = [self.visit(value) for value in node.values]
        return node

    def visit_FormattedValue(self, node):
        node.value = self.visit(node.value)
        return node

def uglify(source_code):
    tree = ast.parse(source_code)
    uglifier = Uglifier()
    new_tree = uglifier.visit(tree)
    ast.fix_missing_locations(new_tree)
    return ast.unparse(new_tree).encode("utf-8")


class BoolToIntTransformer(ast.NodeTransformer):
    def visit_Constant(self, node):
        if isinstance(node.value, bool):
            return ast.copy_location(ast.Constant(value=int(node.value)), node)
        return node


try:
    from importlib._bootstrap_external import MAGIC_NUMBER
except ImportError:
    import imp  # pyright: ignore[reportMissingImports]

    MAGIC_NUMBER = imp.get_magic()  # pyright: ignore[reportGeneralTypeIssues]


PYC_HEADER_FLAGS = 0x01
DEFAULT_PROFILE = "2"
DEFAULT_CUSTOM_PROFILE = "custom"
PROFILE_DEFAULTS = {
    "compression_candidates": ["zlib", "zlib_raw", "bz2", "lzma"],
    "compression_prefer": "zlib",
    "compression_prefer_margin": 0,
    "bz2_level": 9,
    "lzma_preset": 6,
    "zlib_wbits": 15,
    "mp_workers": os.cpu_count(),
    "mp_min_chunks": 24,
}
PROFILES = {
    "1": {
        "layers": 2,
        "chunk_min": 144,
        "chunk_max": 288,
        "compress_level": 7,
        "chunk_key_min": 5,
        "chunk_key_max": 11,
        "shuffle_entries": False,
        "error_suppression": False,
    },
    "2": {
        "layers": 3,
        "chunk_min": 72,
        "chunk_max": 192,
        "compress_level": 9,
        "chunk_key_min": 7,
        "chunk_key_max": 17,
        "shuffle_entries": True,
        "error_suppression": True,
    },
    "3": {
        "layers": 4,
        "chunk_min": 40,
        "chunk_max": 112,
        "compress_level": 9,
        "chunk_key_min": 11,
        "chunk_key_max": 23,
        "shuffle_entries": True,
        "error_suppression": True,
    },
    "z": {
        "layers": 1,
        "chunk_min": 320,
        "chunk_max": 640,
        "compress_level": 9,
        "chunk_key_min": 5,
        "chunk_key_max": 9,
        "shuffle_entries": False,
        "error_suppression": False,
    },
    "c1": {
        "layers": 1,
        "chunk_min": 384,
        "chunk_max": 768,
        "compress_level": 5,
        "chunk_key_min": 4,
        "chunk_key_max": 8,
        "shuffle_entries": False,
        "error_suppression": False,
    },
    "c2": {
        "layers": 2,
        "chunk_min": 224,
        "chunk_max": 416,
        "compress_level": 6,
        "chunk_key_min": 5,
        "chunk_key_max": 11,
        "shuffle_entries": False,
        "error_suppression": False,
    },
    "c3": {
        "layers": 2,
        "chunk_min": 160,
        "chunk_max": 320,
        "compress_level": 7,
        "chunk_key_min": 6,
        "chunk_key_max": 13,
        "shuffle_entries": True,
        "error_suppression": False,
    },
}

os.makedirs("__AUCM__", exist_ok=True)

def normalize_profile(profile: dict) -> dict:
    merged = dict(PROFILE_DEFAULTS)
    merged.update(profile)
    return merged


def collect_imports(tree: ast.AST) -> list[str]:
    class _ImportCollector(ast.NodeVisitor):
        def __init__(self):
            self.items: set[str] = set()

        def visit_Import(self, node: ast.Import):
            for alias in node.names:
                name = alias.name
                if name:
                    self.items.add(name)

        def visit_ImportFrom(self, node: ast.ImportFrom):
            if node.level and node.level > 0:
                return
            if node.module:
                name = node.module
                if name:
                    self.items.add(name)

    collector = _ImportCollector()
    collector.visit(tree)
    return sorted(collector.items)


def _chunk_bytes_literal(data: bytes, chunk_size: int = 2000) -> str:
    parts = []
    for i in range(0, len(data), chunk_size):
        chunk = data[i:i + chunk_size]
        parts.append(repr(chunk))
    return ", ".join(parts)


def _adaptive_chunk_size(data_len: int, min_size: int = 256, max_size: int = 2048) -> int:
    if data_len <= 0:
        return min_size
    # Aim for ~2000 chunks max to keep line lengths reasonable in Cython.
    target = max(min_size, data_len // 2000)
    return min(max_size, target)


def load_profile_file(path: Path):
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, dict) and "profiles" in data:
        profiles = data.get("profiles", {})
        default_name = data.get("default_profile") or data.get("default")
    else:
        profile_name = DEFAULT_CUSTOM_PROFILE
        if isinstance(data, dict) and "name" in data:
            profile_name = str(data["name"])
        profile_body = data.get("profile", data) if isinstance(data, dict) else data
        profiles = {profile_name: profile_body}
        default_name = profile_name
    if not profiles:
        raise ValueError("Profile file contained no profiles.")
    if not default_name:
        default_name = next(iter(profiles))
    for name, profile in profiles.items():
        if not isinstance(profile, dict):
            raise ValueError(f"Profile '{name}' must be a JSON object.")
    return profiles, default_name


def generate_garbage():
    invalid_garbage = True
    while invalid_garbage:
        garbage = ""
        background = ""
        for _ in range(random.randint(5, 10)):
            if random.randint(0, 1):
                background = chr(int(secrets.token_hex(2), 16)) + chr(
                    int(secrets.token_hex(2), 16) + 1
                )
        backspaces = f"\b \b\b\b\b\b\b\b\b \b \b\b\b\b\b\b\b{background}" * random.randint(
            5, 10
        )
        for _ in range(random.randint(5, 10)):
            garbage = chr(int(secrets.token_hex(2), 16)) + chr(int(secrets.token_hex(2), 16))
        
        if '\x00' in garbage:
            invalid_garbage = True
        try:
            garbage.encode("utf-8")
            invalid_garbage = False
        except UnicodeEncodeError:
            invalid_garbage = True
    return f"{backspaces}{garbage}" # type: ignore


def transform_code(code: types.CodeType):
    def patch_code(current: types.CodeType):
        replacements = {
            "co_filename": generate_garbage(),
            "co_name": generate_garbage(),
            "co_firstlineno": 2147483647,
        }
        if hasattr(current, "co_linetable"):
            replacements["co_linetable"] = b"\x00\x00"
        elif hasattr(current, "co_lnotab"):
            replacements["co_lnotab"] = b"\x00\x00"
        return current.replace(**replacements)

    new_consts = []
    changed = False
    for const in code.co_consts:
        if isinstance(const, types.CodeType):
            new_const = transform_code(const)
            new_consts.append(new_const)
            changed = changed or new_const is not const
        else:
            new_consts.append(const)

    if changed:
        code = code.replace(co_consts=tuple(new_consts))
    return patch_code(code)


def check_syntax(contents):
    try:
        compile(contents, "<obfuscator-syntax>", "exec")
        return True
    except SyntaxError as exc:
        print(f"Syntax error: {exc}")
        return False
    except Exception as exc:
        print(f"Validation error: {exc}")
        return False


def format_bytes(size):
    for unit in ["B", "KiB", "MiB", "GiB", "TiB", "PiB", "EiB", "ZiB", "YiB"]:
        if size < 1024:
            return f"{size:.2f} {unit}"
        size /= 1024
    return f"{size:.2f} YiB"

def format_seconds(seconds):
    whole_seconds = int(seconds)
    fractional = seconds - whole_seconds

    days = whole_seconds // 86400
    hours = (whole_seconds % 86400) // 3600
    minutes = (whole_seconds % 3600) // 60
    secs = whole_seconds % 60

    milliseconds = int(fractional * 1000)
    microseconds = int((fractional * 1000 - milliseconds) * 1000)

    parts = []
    if days > 0:
        parts.append(f"{days} {'day' if days == 1 else 'days'}")
    if hours > 0:
        parts.append(f"{hours} {'hour' if hours == 1 else 'hours'}")
    if minutes > 0:
        parts.append(f"{minutes} {'minute' if minutes == 1 else 'minutes'}")
    if secs > 0:
        parts.append(f"{secs} {'second' if secs == 1 else 'seconds'}")
    if milliseconds > 0:
        parts.append(f"{milliseconds} {'millisecond' if milliseconds == 1 else 'milliseconds'}")
    if microseconds > 0:
        parts.append(f"{microseconds} {'microsecond' if microseconds == 1 else 'microseconds'}")

    if not parts:
        return "0 seconds"
    if len(parts) > 1:
        return ", ".join(parts[:-1]) + " and " + parts[-1]
    return parts[0]



def xor_mask(data: bytes, key: bytes, bias: int):
    return bytes((((item ^ key[index % len(key)]) + bias) & 0xFF) for index, item in enumerate(data))


def bytes_tuple_literal(blob: bytes):
    return "(" + ",".join(str(byte) for byte in blob) + ")"


def chunk_bytes(blob: bytes, chunk_min: int, chunk_max: int):
    chunks = []
    cursor = 0
    while cursor < len(blob):
        size = random.randint(chunk_min, chunk_max)
        chunks.append(blob[cursor : cursor + size])
        cursor += size
    return chunks


def _compress_zlib(data: bytes, level: int, wbits: int) -> bytes:
    compressor = zlib.compressobj(level, zlib.DEFLATED, wbits)
    return compressor.compress(data) + compressor.flush()


def select_compression(data: bytes, profile: dict):
    candidates = profile.get("compression_candidates") or ["zlib"]
    prefer = profile.get("compression_prefer", "zlib")
    prefer_margin = int(profile.get("compression_prefer_margin", 0))
    results = []
    for algo in candidates:
        try:
            if algo == "zlib":
                level = int(profile["compress_level"])
                wbits = int(profile.get("zlib_wbits", 15))
                comp = _compress_zlib(data, level, wbits)
                info = {"algo": "zlib", "level": level, "wbits": wbits}
            elif algo == "zlib_raw":
                level = int(profile["compress_level"])
                comp = _compress_zlib(data, level, -15)
                info = {"algo": "zlib_raw", "level": level, "wbits": -15}
            elif algo == "bz2":
                level = int(profile.get("bz2_level", 9))
                comp = bz2.compress(data, compresslevel=level)
                info = {"algo": "bz2", "level": level}
            elif algo == "lzma":
                preset = int(profile.get("lzma_preset", 6))
                comp = lzma.compress(data, preset=preset)
                info = {"algo": "lzma", "preset": preset}
            else:
                continue
        except Exception:
            continue
        results.append((len(comp), algo, comp, info))
    if not results:
        level = int(profile.get("compress_level", 9))
        comp = zlib.compress(data, level=level)
        return comp, {"algo": "zlib", "level": level, "wbits": 15}
    results.sort(key=lambda item: item[0])
    best_len, _, best_comp, best_info = results[0]
    if prefer:
        for length, algo, comp, info in results:
            if algo == prefer and length <= best_len + prefer_margin:
                return comp, info
    return best_comp, best_info


def resolve_mp_workers(profile: dict, chunk_count: int) -> int:
    workers = int(profile.get("mp_workers", 0) or 0)
    if workers <= 0:
        workers = os.cpu_count() or 1
    if workers <= 1:
        return 1
    min_chunks = int(profile.get("mp_min_chunks", 24))
    if chunk_count < min_chunks:
        return 1
    return workers


def _build_chunk_loader_blob_worker(args):
    slot, chunk, profile = args
    return slot, build_chunk_loader_blob(chunk, profile)


def build_chunk_loader_blob(chunk: bytes, profile) -> bytes:
    key = secrets.token_bytes(
        random.randint(profile["chunk_key_min"], profile["chunk_key_max"])
    )
    bias = random.randint(1, 255)
    masked = xor_mask(chunk, key, bias)
    source = (
        f"(lambda _d={bytes_tuple_literal(masked)},"
        f"_k={bytes_tuple_literal(key)},"
        f"_b={bias}:bytes((((_v-_b)&255)^_k[_i%len(_k)])for _i,_v in enumerate(_d)))()"
    )
    compiled = compile(source, generate_garbage(), "eval")
    return marshal.dumps(transform_code(compiled))


def build_layer_source(
    marshaled_blob: bytes,
    layer_index: int,
    profile,
    suppress_errors: bool,
):
    print("Building layer", layer_index)
    expected_hash = hashlib.sha256(marshaled_blob).hexdigest()
    compressed, comp_info = select_compression(marshaled_blob, profile)
    algo = comp_info.get("algo", "zlib")
    print(
        f"[LAYER_{layer_index}] Compression: {algo}. "
        f"Marshalled Blob Size: {format_bytes(len(compressed))}"
    )
    chunks = chunk_bytes(compressed, profile["chunk_min"], profile["chunk_max"])
    print(f"[LAYER_{layer_index}] Building chunk loader blobs")
    workers = resolve_mp_workers(profile, len(chunks))
    if workers > 1:
        print(f"[LAYER_{layer_index}] Using {workers} workers for chunk loaders")
        with ProcessPoolExecutor(max_workers=workers) as executor:
            entries = list(
                executor.map(
                    _build_chunk_loader_blob_worker,
                    ((slot, chunk, profile) for slot, chunk in enumerate(chunks)),
                )
            )
    else:
        entries = [
            (slot, build_chunk_loader_blob(chunk, profile))
            for slot, chunk in enumerate(chunks)
        ]
    if profile["shuffle_entries"]:
        print(f"[LAYER_{layer_index}] Shuffling Entries")
        random.shuffle(entries)
    entry_literal = ",\n        ".join(f"({slot}, {blob!r})" for slot, blob in entries)
    marker_name = f"__layer_{layer_index}_{secrets.token_hex(4)}"
    zwsp = "\u200B"
    hf = "\u3164"
    def ns_inject(sys, module_name, hidden_property):
        return f"{sys}.__getattribute__('modules').__getitem__({module_name!r}).{hidden_property}"
    print(f"[LAYER_{layer_index}] Marker Name: {marker_name}")
    if algo in ("zlib", "zlib_raw"):
        compression_module = "zlib"
        if algo == "zlib_raw":
            decompress_line = f"{ns_inject(hf, 'math', hf+hf)} = {ns_inject(hf, 'hmac', hf)}.decompress({hf}{hf}{hf}.getvalue(), -15)"
        else:
            decompress_line = f"{ns_inject(hf, 'math', hf+hf)} = {ns_inject(hf, 'hmac', hf)}.decompress({hf}{hf}{hf}.getvalue())"
    elif algo == "bz2":
        compression_module = "bz2"
        decompress_line = f"{ns_inject(hf, 'math', hf+hf)} = {ns_inject(hf, 'hmac', hf)}.decompress({hf}{hf}{hf}.getvalue())"
    elif algo == "lzma":
        compression_module = "lzma"
        decompress_line = f"{ns_inject(hf, 'math', hf+hf)} = {ns_inject(hf, 'hmac', hf)}.decompress({hf}{hf}{hf}.getvalue())"
    else:
        compression_module = "zlib"
        decompress_line = f"{ns_inject(hf, 'math', hf+hf)} = {ns_inject(hf, 'hmac', hf)}.decompress({hf}{hf}{hf}.getvalue())"

    body = f"""
def {marker_name}():
    globals()['{zwsp}'] = __builtins__.__dict__.__getitem__('__import__')
    {hf} = globals()['{zwsp}']('sys')
    globals()['{zwsp}']('marshal')
    globals()['{zwsp}']({compression_module!r})
    globals()['{zwsp}']('io')
    globals()['{zwsp}']('hashlib')
    globals()['{zwsp}']('builtins')
    globals()['{zwsp}']('time')
    globals()['{zwsp}']('hmac')
    globals()['{zwsp}']('math')
    {ns_inject(hf, 'sys', hf)} = {hf}.modules.__getitem__('marshal').__getattribute__('loads')
    {ns_inject(hf, 'hmac', hf)} = {hf}.modules.__getitem__({compression_module!r})
    {ns_inject(hf, 'hashlib', hf)} = {hf}.modules.__getitem__('io').__getattribute__('BytesIO')
    {ns_inject(hf, 'io', hf)} = {hf}.modules.__getitem__('hashlib').__getattribute__('sha256')
    {ns_inject(hf, 'marshal', hf)} = {hf}.modules.__getitem__('builtins')
    {ns_inject(hf, 'builtins', hf)} = {hf}.modules.__getitem__('time').__getattribute__('perf_counter')
    {ns_inject(hf, 'math', hf)} = {ns_inject(hf, 'marshal', hf)}.__getattribute__('exec')
    {ns_inject(hf, 'marshal', hf+hf)} = {ns_inject(hf, 'marshal', hf)}.__getattribute__('eval')
    {ns_inject(hf, f'{compression_module}', hf)} = {hf}.modules.__getitem__('hmac').__getattribute__('compare_digest')
    if {hf}.__getattribute__('gettrace')() is not None:
        {hf}.__getattribute__('settrace')(None)
        {hf}.__getattribute__('exit')()
    if any({hf}{hf} in {hf}.modules for {hf}{hf} in {{'pydevd', 'pdb', '_pydevd_bundle', 'rpdb'}}):
        {hf}.__getattribute__('exit')()
    {ns_inject(hf, f'{compression_module}', hf + hf)} = {ns_inject(hf, 'builtins', hf)}()
    for _ in range(100):
        pass
    {ns_inject(hf, 'io', hf + hf)} = {ns_inject(hf, 'builtins', hf)}()
    if ({ns_inject(hf, 'io', hf + hf)} - {ns_inject(hf, f'{compression_module}', hf + hf)}) > 0.1:
        {hf}.__getattribute__('exit')()
    {ns_inject(hf, 'hashlib', hf+hf)} = [b''] * {len(chunks)}
    for {hf}{hf}{hf}, {hf}{hf}{hf}{hf} in (
        {entry_literal}
    ):
        {ns_inject(hf, 'hashlib', hf+hf)}[{hf}{hf}{hf}] = {ns_inject(hf, 'marshal', hf+hf)}({ns_inject(hf, 'sys', hf)}({hf}{hf}{hf}{hf}), {{}}, {{}})
    {hf}{hf}{hf} = {ns_inject(hf, 'hashlib', hf)}()
    for {hf}{hf} in {ns_inject(hf, 'hashlib', hf+hf)}:
        {hf}{hf}{hf}.write({hf}{hf})
    {decompress_line}
    if not {ns_inject(hf, f'{compression_module}', hf)}({ns_inject(hf, 'io', hf)}({ns_inject(hf, 'math', hf+hf)}).hexdigest(), {expected_hash!r}):
        {hf}.__getattribute__('exit')()
    {ns_inject(hf, 'math', hf)}({ns_inject(hf, 'sys', hf)}({ns_inject(hf, 'math', hf+hf)}), globals(), globals())

{marker_name}()
"""
    if suppress_errors:
        print(f"[LAYER_{layer_index}] Suppressing Errors")
        body = f"try:\n{indent(body, '    ')}except BaseException:\n    pass\n"
    print(f"[LAYER_{layer_index}] Layer Source Size: {format_bytes(len(body))}. Layer {layer_index} complete")
    return body


def indent(text: str, prefix: str):
    return "".join(prefix + line if line.strip() else line for line in text.splitlines(True))


def build_wrapped_code_object(
    payload_code: types.CodeType,
    profile,
    suppress_errors: bool,
):
    current_blob = marshal.dumps(payload_code)
    layer_sources = []
    final_code = payload_code
    for layer_index in range(1, profile["layers"] + 1):
        layer_source = build_layer_source(
            current_blob, layer_index, profile, suppress_errors
        )
        layer_sources.append(layer_source)
        final_code = transform_code(
            compile(layer_source.encode("utf-8"), generate_garbage(), "exec")
        )
        current_blob = marshal.dumps(final_code)
    return final_code, layer_sources

def write_pyc(code_object: types.CodeType, fc: BytesIO, source_size: int, source_bytes: bytes):
    fc.write(MAGIC_NUMBER)
    fc.write(struct.pack("<I", PYC_HEADER_FLAGS))
    fc.write(importlib.util.source_hash(source_bytes))
    # fc.write(struct.pack("<I", int(time.time())))
    # fc.write(struct.pack("<I", source_size & 0xFFFFFFFF))
    marshal.dump(transform_code(code_object), fc)
    return len(fc.getvalue())


def build_obfuscation_steps(
    path: Path,
    layers,
    original_source: bytes,
    uglified_source: bytes,
    pyc_blob: bytes,
    profile_name: str,
    auth_used: bool,
    error_suppression_used: bool,
    output_mode: str,
):
    with path.open("wb") as handle:
        handle.write(f"# Profile: {profile_name}\n".encode("utf-8"))
        handle.write(f"# Auth code: {'enabled' if auth_used else 'disabled'}\n".encode("utf-8"))
        handle.write(
            f"# Error suppression: {'enabled' if error_suppression_used else 'disabled'}\n".encode("utf-8")
        )
        handle.write(f"# Output mode: {output_mode}\n".encode("utf-8"))
        handle.write(b"# ----------------------------------------------\n")
        handle.write(b"# Layer 0. Original source\n")
        handle.write(b"# ----------------------------------------------\n")
        handle.write(original_source)
        handle.write(b"\n# ----------------------------------------------\n")
        handle.write(b"# Layer 1. AST uglify + bool folding\n")
        handle.write(b"\n# ----------------------------------------------\n")
        handle.write(uglified_source)
        for index, layer in enumerate(layers, start=2):
            handle.write(b"\n# ----------------------------------------------\n")
            handle.write(f"# Layer {index}. Recursive bytecode loader\n".encode("utf-8"))
            handle.write(b"# ----------------------------------------------\n")
            handle.write(layer.encode("utf-8"))
        handle.write(b"\n# ----------------------------------------------\n")
        handle.write(b"# Final pyc (base64 omitted intentionally)\n")
        handle.write(b"# ----------------------------------------------\n")
        handle.write(f"# Size: {format_bytes(len(pyc_blob))}\n".encode("utf-8"))

def derive_key(digest: bytes, salt: bytes, iterations: int = 100_000) -> bytes:
    u = hmac.new(digest, salt + b'\x01\x01\x01\x02', hashlib.sha256).digest()
    t = bytearray(u)
    for _ in range(iterations - 1):
        u = hmac.new(digest, u, hashlib.sha256).digest()
        t = bytearray(x ^ y for x, y in zip(t, u))
    return bytes(t)

BLOCK_SIZE = 32
NONCE_SIZE = 16
FEISTEL_ROUNDS = 24

def _feistel_encrypt_block(args):
    key, index, block, nonce, round_keys = args
    half = BLOCK_SIZE // 2
    L, R = block[:half], block[half:]
    for rk in round_keys:
        f = hashlib.sha256(rk + R).digest()[:half]
        L, R = R, bytes(a ^ b for a, b in zip(L, f))
    return (index, L + R)

def _derive_round_keys(key: bytes, nonce: bytes) -> list[bytes]:
    return [
        hmac.new(key, nonce + i.to_bytes(2, "big"), hashlib.sha256).digest()
        for i in range(FEISTEL_ROUNDS)
    ]

def encrypt(key: bytes, data: bytes, profile) -> bytes:
    nonce = secrets.token_bytes(NONCE_SIZE)
    round_keys = _derive_round_keys(key, nonce)
    data = len(data).to_bytes(8, "big") + data
    pad_len = (-len(data)) % BLOCK_SIZE
    if pad_len:
        data += b"\x00" * pad_len
    blocks = [
        (key, i // BLOCK_SIZE, data[i:i + BLOCK_SIZE], nonce, round_keys)
        for i in range(0, len(data), BLOCK_SIZE)
    ]
    total_blocks = len(blocks)
    out = [None] * total_blocks
    workers = resolve_mp_workers(profile, total_blocks)
    print(f"Encrypting {total_blocks} blocks with {workers} workers")
    if workers <= 1:
        for block_index, encrypted in map(_feistel_encrypt_block, blocks):
            out[block_index] = encrypted
            if total_blocks <= 64 or (block_index + 1) % 128 == 0 or (block_index + 1) == total_blocks:
                print(f"Encrypting block {block_index + 1} of {total_blocks}")
    else:
        from concurrent.futures import ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=workers) as executor:
            for block_index, encrypted in executor.map(_feistel_encrypt_block, blocks):
                out[block_index] = encrypted
                if total_blocks <= 64 or (block_index + 1) % 128 == 0 or (block_index + 1) == total_blocks:
                    print(f"Encrypting block {block_index + 1} of {total_blocks}")

    ciphertext = nonce + b"".join(out)
    digest = hashlib.sha256(ciphertext).digest()
    return digest + ciphertext

def encrypt_aesgcm(key: bytes, data: bytes) -> bytes:
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    nonce = secrets.token_bytes(12)
    data = len(data).to_bytes(8, "big") + data
    aes = AESGCM(key)
    ciphertext = aes.encrypt(nonce, data, None)
    return nonce + ciphertext

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=str, help="File to obfuscate")
    parser.add_argument("output", type=str, help="Output file")
    parser.add_argument(
        "--level",
        default=DEFAULT_PROFILE,
        help="Obfuscation profile: 1, 2, 3, z, c1, c2, c3 or custom",
    )
    parser.add_argument(
        "--profile-file",
        type=str,
        default=None,
        help="JSON file defining custom profiles",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=None,
        help="Override profile mp_workers (0=auto)",
    )
    parser.add_argument(
        "--disable-error-suppression",
        action="store_true",
        help="Disable outer layer error suppression",
    )
    parser.add_argument("--password", type=str, help="Secure the file itself with a password based authentication")
    parser.add_argument("--pyc", action="store_true", help="Output a .pyc file instead of a executable")
    parser.add_argument(
        "--hidden-import",
        action="append",
        default=[],
        help="Additional hidden imports for PyInstaller (can be repeated or comma-separated).",
    )
    parser.add_argument(
        "--collect-submodules",
        action="append",
        default=[],
        help="Collect all submodules for a package (can be repeated or comma-separated).",
    )
    parser.add_argument(
        "--collect-data",
        action="append",
        default=[],
        help="Collect data files for a package (can be repeated or comma-separated).",
    )
    parser.add_argument(
        '--add-binary',
        action='append',
        default=[],
        help='Add a binary file to the executable (can be repeated or comma-separated).',
    )
    parser.add_argument(
        "--no-upx",
        action="store_true",
        help="Disable UPX compression for PyInstaller builds.",
    )
    parser.add_argument(
        "--force-upx",
        action="store_true",
        help="Force UPX on non-Windows (may produce unstable binaries).",
    )
    args = parser.parse_args()

    profiles = {name: normalize_profile(profile) for name, profile in PROFILES.items()}
    selected_level = args.level

    if args.profile_file:
        custom_profiles, default_name = load_profile_file(Path(args.profile_file))
        for name, profile in custom_profiles.items():
            profiles[name] = normalize_profile(profile)
        if args.level == DEFAULT_PROFILE and default_name:
            selected_level = default_name

    if selected_level not in profiles:
        print(f"Unknown profile: {selected_level}")
        print("Available profiles:", ", ".join(sorted(profiles.keys())))
        raise SystemExit(2)

    def _split_args(values):
        result = []
        for item in values:
            for part in str(item).split(","):
                part = part.strip()
                if part:
                    result.append(part)
        return result

    hidden_imports = _split_args(args.hidden_import)
    collect_submodules = _split_args(args.collect_submodules)
    collect_data = _split_args(args.collect_data)
    add_binary = _split_args(args.add_binary)

    profile = profiles[selected_level]
    if args.workers is not None:
        profile = dict(profile)
        profile["mp_workers"] = int(args.workers)

    required_keys = [
        "layers",
        "chunk_min",
        "chunk_max",
        "compress_level",
        "chunk_key_min",
        "chunk_key_max",
        "shuffle_entries",
        "error_suppression",
    ]
    missing = [key for key in required_keys if key not in profile]
    if missing:
        print("Profile missing required keys:", ", ".join(missing))
        raise SystemExit(2)

    start_time = time.monotonic()
    print("Started obfuscation at", time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()))
    print("Python version:", sys.version)
    print("Obfuscating", args.source, "with profile", selected_level)

    with open(args.source, "rb") as source_handle:
        source = source_handle.read()

    if not check_syntax(source):
        print("Syntax Check Failed!")
        raise SystemExit(1)

    print("Syntax Check Passed!")
    starting_size = len(source)
    print(f"Starting payload size: {format_bytes(starting_size)}")

    parsed_tree = ast.parse(source)
    if ast.get_docstring(parsed_tree) is not None:
        source = f"__doc__={ast.get_docstring(parsed_tree)!r}\n".encode("utf-8") + source
    if not args.pyc:
        source = "__file__=__import__('pathlib', fromlist=['Path']).__getattribute__('Path')(__import__('sys',fromlist=['argv']).__getattribute__('argv')[0]).__getattribute__('resolve')()\n".encode("utf-8") + source

    tree = ast.parse(source)
    auto_hidden_imports = collect_imports(tree)
    if auto_hidden_imports:
        hidden_imports = sorted(set(hidden_imports).union(auto_hidden_imports))
    if not args.pyc and IS_PACKAGABLE:
        # Required by the generated runtime loader; PyInstaller won't see these dynamic imports.
        internal_hidden_imports = {
            "hmac",
            "hashlib",
            "io",
            "marshal",
            "zlib",
            "bz2",
            "lzma",
            "math",
            "sys",
            "pathlib"
        }
        hidden_imports = sorted(set(hidden_imports).union(internal_hidden_imports))
    tree = BoolToIntTransformer().visit(tree)
    ast.fix_missing_locations(tree)
    uglified_source = uglify(ast.unparse(tree).encode("utf-8"))

    if not check_syntax(uglified_source):
        print("Obfuscated Syntax Check Failed!")
        raise SystemExit(1)

    payload_code = transform_code(
        compile(uglified_source, generate_garbage(), "exec")
    )
    error_suppression_used = profile["error_suppression"] and not args.disable_error_suppression
    wrapped_code, layer_sources = build_wrapped_code_object(
        payload_code,
        profile,
        suppress_errors=error_suppression_used,
    )

    sys.modules["builtins"]
    
    use_packaged_crypto = False
    if args.password:
        password = hashlib.sha256(args.password.encode("utf-8")).digest()
        print("Deriving Encryption Key")
        encryption_key = derive_key(password, b'\x4f\x4a\xfb\x05', 10000)
        use_packaged_crypto = (not args.pyc) and IS_PACKAGABLE
        if use_packaged_crypto:
            try:
                from cryptography.hazmat.primitives.ciphers.aead import AESGCM  # noqa: F401
            except ImportError:
                print("Error: cryptography is required for packaged (PyInstaller/Cython) builds.")
                raise SystemExit(1)
        print("Encrypting Code")
        encryption_code = (
            encrypt_aesgcm(encryption_key, marshal.dumps(wrapped_code))
            if use_packaged_crypto
            else encrypt(encryption_key, marshal.dumps(wrapped_code), profile)
        )
        auth_code = r"""
__import__ = __builtins__.__dict__.__getitem__("__import__")
_h = __import__("hashlib", fromlist=["sha256"]).__getattribute__("sha256")
_m = __import__("hmac", fromlist=["new"]).__getattribute__("new")
_s = __import__("marshal", fromlist=["loads"]).__getattribute__("loads")
_e = __builtins__.__dict__.__getitem__("exec")
_b = __import__("base64", fromlist=["a85decode"]).__getattribute__("a85decode")
_p = _b({password}, adobe=False)
_ui = 1
while _ui:
    try:
        _ti = __builtins__.__dict__.__getitem__("input")("Enter Password: ")
        _i = _h(_ti.encode()).digest()
        if _ti != "":
            _ui = 0
    except BaseException:
        __import__("sys").exit()
del _ui
del _ti
_u = _m(_p, b'\x4f\x4a\xfb\x05' + b'\x01\x01\x01\x02', _h).digest()
_t = bytearray(_u)
_p3 = __import__("concurrent.futures", fromlist=["ThreadPoolExecutor"]).__getattribute__("ThreadPoolExecutor")
_o2 = __import__("os", fromlist=["cpu_count"]).__getattribute__("cpu_count")
_bs = 32
_r = 24

def _rk(_k, _n):
    return [_m(_k, _n + _i.to_bytes(2, "big"), _h).digest() for _i in range(_r)]

def _d(_k2):
    _n, _rk2 = _k2[3], _k2[4]
    _h2 = 16
    _l, _m2 = _k2[2][:_h2], _k2[2][_h2:]
    for _rk3 in reversed(_rk2):
        _f = _h(_rk3 + _l).digest()[:_h2]
        _l, _m2 = bytes((_a ^ _b) for _a, _b in zip(_m2, _f)), _l
    return _k2[1], _l + _m2

if _i == _p:
    print("\033[2J\033[H", end="")
    print("Authenticated")
    print("Please wait a moment...")
    try:
        for _ in range(10000 - 1):
            _u = _m(_p, _u, _h).digest()
            _t = bytearray(_x ^ _y for _x, _y in zip(_t, _u))
        _k = bytes(_t)
        _c = {encryption_code}
        _d0 = _c[:32]
        _c0 = _c[32:]
        if _h(_c0).digest() != _d0:
            print("Check failed")
            __import__("sys").exit()
        _n = _c0[:16]
        _c2 = _c0[16:]
        _p2 = (-len(_c2)) % _bs
        _d2 = _c2 + (b"\x00" * _p2 if _p2 else b"")
        _rk2 = _rk(_k, _n)
        _b2 = [(_k, _i//_bs, _d2[_i:_i+_bs], _n, _rk2) for _i in range(0, len(_d2), _bs)]
        _o = [None]*len(_b2)
        _w = _o2() or 1
        if _w > 1 and len(_b2) >= 24:
            with _p3(max_workers=_w) as _x:
                for _i2, _b3 in _x.map(_d, _b2):
                    _o[_i2] = _b3
                    if len(_b2) <= 64 or (_i2 + 1) % 128 == 0 or (_i2 + 1) == len(_b2):
                        print(f"Decrypting block {{_i2+1}} of {{len(_b2)}}")
        else:
            for _i2, _b3 in map(_d, _b2):
                _o[_i2] = _b3
                if len(_b2) <= 64 or (_i2 + 1) % 128 == 0 or (_i2 + 1) == len(_b2):
                    print(f"Decrypting block {{_i2+1}} of {{len(_b2)}}")

        _e2 = b"".join(_o)
        _l = int.from_bytes(_e2[:8], "big")
        if _l <= 0 or _l > (len(_e2) - 8):
            print("Check failed")
            __import__("sys").exit()
    except BaseException:
        print("Check failed")
        __import__("sys").exit()
    print("\033[2J\033[H", end="")
    try:
        _g = globals()
        _e(_s(_e2[8:8 + _l]), _g, _g)
    except BaseException:
        __import__("sys").exit()
else:
    __import__("sys").exit()
""".format(password=base64.a85encode(password, adobe=False), encryption_code=encryption_code)  # noqa: F524
        if use_packaged_crypto:
            auth_code = r"""
__import__ = __builtins__.__dict__.__getitem__("__import__")
_h = __import__("hashlib", fromlist=["sha256"]).__getattribute__("sha256")
_m = __import__("hmac", fromlist=["new"]).__getattribute__("new")
_s = __import__("marshal", fromlist=["loads"]).__getattribute__("loads")
_e = __builtins__.__dict__.__getitem__("exec")
_b = __import__("base64", fromlist=["a85decode"]).__getattribute__("a85decode")
_p = _b({password}, adobe=False)
_ui = 1
while _ui:
    try:
        _ti = __builtins__.__dict__.__getitem__("input")("Enter Password: ")
        _i = _h(_ti.encode()).digest()
        if _ti != "":
            _ui = 0
    except BaseException:
        __import__("sys").exit()
del _ui
del _ti
_u = _m(_p, b'\x4f\x4a\xfb\x05' + b'\x01\x01\x01\x02', _h).digest()
_t = bytearray(_u)

if _i == _p:
    print("\033[2J\033[H", end="")
    print("Authenticated")
    print("Please wait a moment...")
    try:
        for _ in range(10000 - 1):
            _u = _m(_p, _u, _h).digest()
            _t = bytearray(_x ^ _y for _x, _y in zip(_t, _u))
        _k = bytes(_t)
        _c = {encryption_code}
        _n = _c[:12]
        _c2 = _c[12:]
        _aes = __import__("cryptography.hazmat.primitives.ciphers.aead", fromlist=["AESGCM"]).__getattribute__("AESGCM")
        _p2 = _aes(_k).decrypt(_n, _c2, None)
        _l = int.from_bytes(_p2[:8], "big")
        if _l <= 0 or _l > (len(_p2) - 8):
            print("Check failed")
            __import__("sys").exit()
    except BaseException:
        print("Check failed")
        __import__("sys").exit()
    print("\033[2J\033[H", end="")
    try:
        _g = globals()
        _e(_s(_p2[8:8 + _l]), _g, _g)
    except BaseException:
        __import__("sys").exit()
else:
    __import__("sys").exit()
""".format(password=base64.a85encode(password, adobe=False), encryption_code=encryption_code)  # noqa: F524
        auth_code = compile(auth_code, 'test', "exec")

    pyc = BytesIO()
    compiled_size = write_pyc(wrapped_code if not args.password else auth_code, pyc, len(uglified_source), uglified_source) # pyright: ignore[reportArgumentType, reportPossiblyUnboundVariable]
    if args.pyc or not IS_PACKAGABLE:
        print(f"Compiled code size: {format_bytes(compiled_size)}")
    if not args.pyc and IS_PACKAGABLE:
        pyc.seek(0)
        pyc.write(marshal.dumps(transform_code(wrapped_code if not args.password else auth_code)))
        compressed, comp_info = select_compression(pyc.getvalue(), profile)
        algo = comp_info.get("algo", "zlib")
        if algo in ("zlib", "zlib_raw"):
            compression_module = "zlib"
            if algo == "zlib_raw":
                decompress_line = ",-15"
            else:
                decompress_line = ""
        elif algo == "bz2":
            compression_module = "bz2"
            decompress_line = ""
        elif algo == "lzma":
            compression_module = "lzma"
            decompress_line = ""
        else:
            compression_module = "zlib"
            decompress_line = ""
        
        encoded = base64.a85encode(compressed, adobe=False)
        chunk_size = _adaptive_chunk_size(len(encoded), min_size=256, max_size=1024)
        encoded_chunks = _chunk_bytes_literal(encoded, chunk_size=chunk_size)
        cython_wrapper = """
def __main__():
    __import__ = __builtins__.__dict__.__getitem__("__import__")
    _a = __import__("base64", fromlist=["a85decode"]).__getattribute__("a85decode")
    _m = __import__("marshal", fromlist=["loads"]).__getattribute__("loads")
    _z = __import__("{compression_module}", fromlist=["decompress"]).__getattribute__("decompress")
    _io = __import__("io", fromlist=["BytesIO"]).__getattribute__("BytesIO")
    _buf = _io()
    for _c in [{source_chunks}]:
        _buf.write(_c)
    _src = _buf.getvalue()
    _g = globals()
    _g["__name__"] = "__main__"
    exec(_m(_z(_a(_src,adobe=False){decompress_line})), _g, _g)
""".format(source_chunks=encoded_chunks, compression_module=compression_module, decompress_line=decompress_line)  # pyright: ignore[reportArgumentType, reportPossiblyUnboundVariable]
        with open(f"__AUCM__/{Path(args.output).stem}_blob.py", "w") as f:
            f.write(cython_wrapper)
        ext = Extension(Path(args.output).stem + "_blob", sources=[f"__AUCM__/{Path(args.output).stem}_blob.py"]) # pyright: ignore[reportPossiblyUnboundVariable]
        sys.argv = [sys.argv[0], "build_ext", "--inplace"]
        setup( # pyright: ignore[reportPossiblyUnboundVariable]
            ext_modules=cythonize([ext], compiler_directives={'language_level': "3"}), # pyright: ignore[reportPossiblyUnboundVariable]
            packages=[],
            py_modules=[]
        )
        lib = None
        target_name = Path(args.output).stem + "_blob"
        for ext in ("so", "pyd", "dylib"):
            for root, _, files in os.walk('build'):
                for file in files:
                    if file.startswith(target_name) and file.endswith(ext):
                        lib = Path(root) / file
                        break
        if lib is None:
            print("Error: Could not find compiled library")
            sys.exit(1)
        lib_ext = lib.suffix[1:]
        lib = lib.rename(Path("__AUCM__") / Path(Path(args.output).stem + f"_blob.{lib_ext}"))
        print(f"Cythonized code size: {format_bytes(lib.stat().st_size)}")
        
        os.remove(f"__AUCM__/{Path(args.output).stem}_blob.py")
        os.remove(f"__AUCM__/{Path(args.output).stem}_blob.c")
        
        pyinstaller_code = """
import {lib} as _m
_m.__main__()
""".format(lib=Path(args.output).stem + "_blob") # pyright: ignore[reportPossiblyUnboundVariable]
        with open(f"__AUCM__/{Path(args.output).stem}.py", "w") as f:\
            f.write(pyinstaller_code)
        pi_args = [
            '__AUCM__/' + Path(args.output).stem + ".py",
            '--onefile',
            '--name', args.output,
            '--add-binary', f"{lib}:.",
            '--clean',
            '--noconfirm',
            '--strip',
        ]
        if args.no_upx:
            pi_args.append("--noupx")
        elif args.force_upx:
            os.environ["PYINSTALLER_FORCE_UPX"] = "1"
        if use_packaged_crypto:
            pi_args += [
                '--hidden-import', 'cryptography',
                '--collect-submodules', 'cryptography'
            ]
        for item in hidden_imports:
            pi_args += ['--hidden-import', item]
        for item in collect_submodules:
            pi_args += ['--collect-submodules', item]
        for item in collect_data:
            pi_args += ['--collect-data', item]
        for item in add_binary:
            pi_args += ['--add-binary', item]
        PyInstaller.__main__.run(pi_args)
        os.remove(f"__AUCM__/{Path(args.output).stem}.py")
        os.remove(f"__AUCM__/{Path(args.output).stem}_blob.{lib_ext}")
        exe = Path("dist") / Path(args.output)
        if not exe.exists():
            print("Error: Could not find compiled executable")
            sys.exit(1)
        print(f"PyInstaller code size: {format_bytes(exe.stat().st_size)}")
        target = Path(args.output)
        try:
            if target.exists():
                target.unlink()
            exe.rename(target)
        except PermissionError:
            import shutil
            shutil.copy2(exe, target)
            exe.unlink(missing_ok=True)
        build_obfuscation_steps(
            Path("obfuscation_steps.py"),
            layer_sources,
            source,
            uglified_source,
            pyc.getvalue(),
            selected_level,
            auth_used=bool(args.password),
            error_suppression_used=error_suppression_used,
            output_mode="packaged",
        )
    output_path = Path(args.output)
    if args.pyc or not IS_PACKAGABLE:
        if (not args.pyc) and (not IS_PACKAGABLE):
            print("Packaging unavailable; writing .pyc instead.")
        if output_path.suffix.lower() != ".pyc":
            output_path = output_path.with_suffix(".pyc")
        output_path.write_bytes(pyc.getvalue())
        build_obfuscation_steps(
            Path("obfuscation_steps.py"),
            layer_sources,
            source,
            uglified_source,
            pyc.getvalue(),
            selected_level,
            auth_used=bool(args.password),
            error_suppression_used=error_suppression_used,
            output_mode="pyc",
        )
    print(
        "Finished Obfuscation at",
        time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()),
        "with profile",
        selected_level,
    )
    print("Total time:", format_seconds(time.monotonic() - start_time))
    print("Final file at", os.path.basename(output_path))


if __name__ == "__main__":
    import multiprocessing

    multiprocessing.freeze_support()
    main()
