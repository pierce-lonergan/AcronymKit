# Security Policy

## Supported versions

| Version | Supported |
|---|---|
| `main` | ✅ |
| 0.1.x | ⚠️ pre-release; fixes land on `main` only |

`acronymkit` has not reached 1.0. Until it does, security fixes are applied to `main` and released in
the next version rather than backported.

## Reporting a vulnerability

Please report privately via
[GitHub Security Advisories](https://github.com/pierce-lonergan/AcronymKit/security/advisories/new).
Do not open a public issue for an unpatched vulnerability.

Expect an acknowledgement within 7 days and an assessment within 14. If a fix is warranted, you will
be credited in the advisory unless you ask otherwise.

## Threat model

`acronymkit` parses untrusted text. The realistic risks are therefore denial of service and resource
exhaustion, not code execution:

- **Algorithmic complexity attacks.** A crafted document that makes extraction or generation
  superlinear. One such defect has already been found and fixed (a nested-bracket path that took 43 s
  on a 112 KB document). Reports of new ones are in scope and welcome.
- **Unbounded memory.** Inputs that make the candidate search or the token stream grow without limit.
  `Config.max_search_nodes`, `search_beam_width` and `search_time_budget_ms` exist to bound this; a
  way around them is a bug.
- **Catastrophic regex backtracking** in the tokenizer or extractor patterns.

Out of scope: the library performs no network I/O, executes no user-supplied code, and writes no
files. `tools/fetch_data.py` does download pinned assets, but it is a maintainer tool, is not
importable from the package, and verifies every download against a SHA-256 recorded in the source.

## Supply chain

- All GitHub Actions are pinned to commit SHAs, not tags.
- Workflows run with `contents: read` unless a job explicitly needs more.
- Publishing uses PyPI Trusted Publishing (OIDC); no long-lived token is stored in the repository.
- Dependabot monitors `pip` and `github-actions`.
- Third-party data assets are pinned and checksummed; see [`data/LICENSES.md`](data/LICENSES.md).
