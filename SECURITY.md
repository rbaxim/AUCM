# Security Policy

We take security reports seriously and will respond as quickly as we can.

## Supported Versions

This project does not currently publish formal release versions. Security fixes are applied to the latest commit on the default branch.

## Reporting A Vulnerability

Include:
- A clear description of the issue and impact.
- Steps to reproduce.
- A minimal proof of concept, if possible.
- Your environment (OS, Python version, build mode).

## Scope

In scope:
- Vulnerabilities in the obfuscation pipeline that lead to unintended code execution during build.
- Issues that allow bypassing password gating or integrity checks in packaged outputs.
- Reproducible crashes or unsafe behavior triggered by untrusted inputs.
- Weaknesses that materially reduce obfuscation strength or expose logic more easily than expected.
- Findings that leak sensitive information or make extraction significantly easier.
- Practical fixes or mitigation ideas that improve the obscurity and resilience of outputs.

Out of scope:
- Issues inherent to obfuscation as a security boundary.
- Reverse‑engineering of protected outputs.
- Vulnerabilities in third‑party tools (report those to the upstream projects).

## Disclosure Timeline

I am a single person. I am not fast.
