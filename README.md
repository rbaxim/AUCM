# AUCM Obfuscator

![License](https://img.shields.io/badge/license-Apache%202.0-green)
![GitHub repo size](https://img.shields.io/github/repo-size/rbaxim/AUCM?label=Repo%20Size)

AUCM (Are you challenging me?) is a Python obfuscator that transforms source code into a layered, compressed payload and can optionally package it into a single executable. It also supports password‑protected outputs and generates an `obfuscation_steps.py` file that records the steps for the build.

## Features

- AST‑level identifier obfuscation
- Multi‑layer wrapping with configurable profiles
- Compression selection (zlib/bz2/lzma)
- Optional password protection
- `.pyc` output mode or single‑file executable packaging (when build tools are available)
- PyInstaller integration with hidden‑import and data/binary collection flags

## Requirements

Install dependencies from `requirements.txt`. Packaging into a single executable requires PyInstaller, Cython, and setuptools. Password‑protected packaged builds require `cryptography`.

## Quick Start

```bash
python obfuscator.py input.py output.exe
```

If packaging dependencies are missing, AUCM falls back to writing a `.pyc` file.

## CLI Usage

```bash
python obfuscator.py <source> <output> [options]
```

Options:
- `--level {1,2,3,z,c1,c2,c3,custom}`: Obfuscation profile (default: `2`)
- `--profile-file PATH`: JSON file defining custom profile(s)
- `--workers N`: Override profile `mp_workers` (`0` = auto)
- `--disable-error-suppression`: Disable outer layer error suppression
- `--password TEXT`: Protect the output with a password
- `--pyc`: Write a `.pyc` file instead of an executable
- `--hidden-import MOD`: Extra hidden imports for PyInstaller (repeatable / comma‑separated)
- `--collect-submodules PKG`: Collect all submodules (repeatable / comma‑separated)
- `--collect-data SPEC`: Collect data files (repeatable / comma‑separated)
- `--add-binary SPEC`: Add binary files (repeatable / comma‑separated)
- `--no-upx`: Disable UPX compression for PyInstaller builds
- `--force-upx`: Force UPX on non‑Windows (may be unstable)

## Profiles

Built‑in profiles: `1`, `2`, `3`, `z`, `c1`, `c2`, `c3`.

Custom profiles are loaded from JSON. Two formats are supported:

Single profile:
```json
{
  "name": "my_profile",
  "profile": {
    "layers": 3,
    "chunk_min": 72,
    "chunk_max": 192,
    "compress_level": 9,
    "chunk_key_min": 7,
    "chunk_key_max": 17,
    "shuffle_entries": true,
    "error_suppression": true,
    "compression_candidates": ["zlib", "bz2", "lzma"],
    "compression_prefer": "zlib",
    "compression_prefer_margin": 0,
    "bz2_level": 9,
    "lzma_preset": 6,
    "zlib_wbits": 15,
    "mp_workers": 0,
    "mp_min_chunks": 24
  }
}
```

Multiple profiles with a default:
```json
{
  "default_profile": "fast",
  "profiles": {
    "fast": { "layers": 1, "chunk_min": 320, "chunk_max": 640, "compress_level": 9, "chunk_key_min": 5, "chunk_key_max": 9, "shuffle_entries": false, "error_suppression": false },
    "strong": { "layers": 4, "chunk_min": 40, "chunk_max": 112, "compress_level": 9, "chunk_key_min": 11, "chunk_key_max": 23, "shuffle_entries": true, "error_suppression": true }
  }
}
```

Required keys for any profile:
`layers`, `chunk_min`, `chunk_max`, `compress_level`, `chunk_key_min`, `chunk_key_max`, `shuffle_entries`, `error_suppression`.

## Outputs

- Executable (PyInstaller): `output` (no extension required)
- Bytecode: `output.pyc` (forced with `--pyc` or when packaging deps are missing)
- Obfuscation steps: `obfuscation_steps.py`
- Temporary build files in `__AUCM__`

## Troubleshooting

- `PyInstaller, Cython, Setuptools and Cryptography are required to build an executable`: Install dependencies from `requirements.txt`, then rerun. If you only need bytecode output, add `--pyc`.
- Executable build fails with missing imports: Add `--hidden-import` entries or use `--collect-submodules` for the package causing the error.
- Executable runs but crashes at startup: Make sure all runtime data files are included via `--collect-data` and native libraries via `--add-binary`.
- Obfuscated output crashes immediately: Ensure the input script passes a normal run and syntax check; AUCM will exit on syntax errors.
- UPX issues on non‑Windows: Use `--no-upx` or avoid `--force-upx` if the binary is unstable.

## Security And Threat Model

What this protects (commonly):
- Raises the effort needed to casually read or copy source code.
- Discourages drive‑by copying and superficial plagiarism.
- Slows down low‑effort reverse‑engineering and automated scraping of logic.
- Makes string‑based scanning and simple grep‑style discovery harder.
- Adds friction for novice attackers and opportunistic misuse.
- Obscures identifiers, basic control flow, and surface‑level intent.
- Reduces the value of simple static analysis and decompilation attempts.
- Forces additional time spent on dynamic analysis to understand behavior.
- Complicates quick auditing by non‑expert reviewers.
- Increases noise for bulk analysis tooling that assumes clean Python sources.

What this does not protect (explicitly not protected):
- Determined reverse‑engineering by a motivated attacker.
- Skilled debugging, instrumentation, or tracing.
- Runtime observation of inputs, outputs, and side effects.
- Extraction of secrets present at runtime (keys, tokens, API credentials).
- Reverse‑engineering of algorithms once behavior is observed.
- Theft of IP by anyone who can run the code and record its behavior.
- Attacks that use memory dumps, API hooking, or syscall tracing.
- Deobfuscation using custom tooling or manual analysis.
- Integrity of the code (tamper‑resistance) without separate signing.
- Supply‑chain compromise or malicious dependency injection.
- Vulnerabilities in the original code or unsafe runtime usage.
- Legal or contractual enforcement of IP ownership.
- Protection from insider threats with execution access.
- Protection against automated sandboxing at scale.
- Protection against model extraction from observed outputs.
- Any cryptographic guarantees of confidentiality or integrity.

## Important

[!WARNING]
This is not real protection. It is security by obscurity.

[!IMPORTANT]
If you need strong IP protection, use proper cryptographic controls such as digital signing, licensing, or secure server‑side execution.

## Notes

- If you use `--password` and packaging is enabled, AUCM verifies and decrypts before executing the payload.
- For projects with dynamic imports, pass `--hidden-import` or `--collect-submodules` to avoid PyInstaller import errors.

___

## Attribution

If you redistribute AUCM or substantial portions of it, you must preserve the LICENSE and NOTICE files as required by Apache 2.0.
Visible credit in documentation or UI is appreciated but not required.

- See [NOTICE](NOTICE).

## License

- See [LICENSE](LICENSE).
