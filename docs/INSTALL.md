# Installing acronymkit without PyPI

This document covers every way to install `acronymkit` that is not `pip install acronymkit` from
PyPI. It exists because PyPI is a single point of failure the installer does not control: it can be
blocked by policy, unreachable from a segmented network, rate-limited, or simply down.

Every command below was run on the machine described in
[What was actually run](#appendix-what-was-actually-run). Two of them -- both provenance checks, in
section 5 -- could not reach a success path from here, and the paragraphs that carry them say so in
place rather than in a footnote.

**As of writing, `acronymkit` is not published on PyPI at all** -- `https://pypi.org/pypi/acronymkit/json`
returns 404 -- so today these are not alternative routes, they are the only ones. That will change;
the routes will not.

## Which route do you want?

| Route | Needs an index at install time | Needs any network | Section |
|---|---|---|---|
| Wheel from a GitHub release | for the dependencies only | yes | [1](#1-a-wheel-from-a-github-release) |
| Straight from git, at a tag | for the dependencies and the build backend | yes | [2](#2-straight-from-git-at-a-tag) |
| From a source checkout | for the dependencies and the build backend | yes | [3](#3-from-a-source-checkout) |
| From an offline bundle | no | **no** | [4](#4-from-an-offline-bundle) |

Only the last one is index-free. The first three fetch `pydantic` and friends from whatever index
`pip` is configured with, and differ only in where *`acronymkit` itself* comes from. If you have no
index at all, go to section 4 and skip the rest.

---

## 1. A wheel from a GitHub release

Each release carries the wheel and the sdist as assets, plus the bundles and SBOMs described below.
Install the wheel by URL:

```
pip install "https://github.com/pierce-lonergan/AcronymKit/releases/download/v0.2.0/acronymkit-0.2.0-py3-none-any.whl"
```

The wheel is `py3-none-any` -- one file for every platform and every supported interpreter, because
`acronymkit`'s own code is pure Python. Its *dependencies* are not, which is what makes section 4
more complicated than this one.

For the command-line interface, ask for the extra. Quote it: `zsh` and `fish` treat the brackets as
a glob and will refuse an unquoted `acronymkit[cli]`.

```
pip install "acronymkit[cli] @ https://github.com/pierce-lonergan/AcronymKit/releases/download/v0.2.0/acronymkit-0.2.0-py3-none-any.whl"
```

That second form is a PEP 508 direct reference: the name, the extras and the exact file, in one
requirement. It is worth knowing because it works on a machine whose index does not carry
`acronymkit` under any name -- which is every machine, today.

To download the whole set for later without installing anything, see
[building your own bundle](#45-a-platform-we-do-not-publish-a-bundle-for).

## 2. Straight from git, at a tag

```
pip install "git+https://github.com/pierce-lonergan/AcronymKit@v0.2.0"
```

`pip` clones, builds the wheel and installs it. This needs `git` on `PATH` and a network path to
both GitHub and your index -- the build backend (`setuptools`, `wheel`) is fetched into an isolated
build environment before the build starts.

**Always name a tag.** `git+https://.../AcronymKit` with no `@ref` tracks the default branch, which
is a moving target: what you installed on Tuesday is not what you install on Thursday, and nothing
records which one you got. The tag also matters for provenance -- the release workflow refuses to
publish if the tag and the packaged version disagree.

A commit SHA works in the same position and is stricter still, since a tag can be moved. Give the
full 40 characters -- `pip` documents that, and a short ref makes it fetch more to resolve it:

```
pip install "git+https://github.com/pierce-lonergan/AcronymKit@328957c08c57727e23cb0a8d7752762112deb850"
```

## 3. From a source checkout

For running the project's own gates, or when the sdist is what you have:

```
git clone https://github.com/pierce-lonergan/AcronymKit.git
cd AcronymKit
pip install .
```

`pip install .` builds a wheel from the checkout and installs that wheel; it does not put the
checkout on `sys.path`. Contributors want the editable variant with the development extras instead
-- see `CONTRIBUTING.md`, which owns that workflow.

Two things to know about a wheel you built yourself. It will **not** be byte-identical to the
published one: `setuptools` embeds build-time metadata, and the resource files it packages come from
the commit you happen to have checked out. So verify a downloaded wheel against the release's
`SHA256SUMS` (section 5), and never against a local rebuild -- a mismatch there tells you nothing.

## 4. From an offline bundle

An offline bundle is one archive containing the `acronymkit` wheel, **every** wheel it depends on,
hash-pinned requirements, a checksum manifest and a verifier. Installing from it contacts no index
and no network:

```
pip install --no-index --find-links=. acronymkit
```

Building a bundle needs the network. Using one does not. That asymmetry is the whole point: one
connected machine builds the archive, any number of disconnected machines install from it.

### 4.1 Pick the right bundle

`pydantic` delegates its validation core to `pydantic-core`, a Rust extension published as
platform- and interpreter-specific wheels -- one file per (CPython minor version x operating system
x CPU architecture x libc), and not `abi3`, so it does not even carry across CPython minor versions.
A bundle is therefore built per platform, and the platform is in its filename.

Each release carries these:

| Asset | Serves |
|---|---|
| `acronymkit-<version>-offline-linux-x86_64-cp39-cp313.zip` | glibc Linux on x86-64, glibc 2.17+ (RHEL/CentOS 7+, Debian 8+, Ubuntu 14.04+) |
| `acronymkit-<version>-offline-linux-aarch64-cp39-cp313.zip` | glibc Linux on 64-bit ARM, glibc 2.17+ (Graviton, Ampere, 64-bit Raspberry Pi OS) |
| `acronymkit-<version>-offline-linux-musl-x86_64-cp39-cp313.zip` | musl Linux on x86-64 (Alpine 3.13+, the `python:*-alpine` images) |
| `acronymkit-<version>-offline-macos-arm64-cp39-cp313.zip` | macOS 11+ on Apple silicon, native arm64 CPython |
| `acronymkit-<version>-offline-macos-x86_64-cp39-cp313.zip` | macOS 10.12+ on Intel, or a Rosetta CPython on Apple silicon |
| `acronymkit-<version>-offline-windows-amd64-cp39-cp313.zip` | 64-bit Windows, 64-bit CPython |
| `acronymkit-<version>-offline-windows-arm64-cp311-cp313.zip` | Windows on ARM, native ARM64 CPython -- **3.11 to 3.13 only** |

The `cp39-cp313` suffix is the interpreter range, not a single version: one archive carries a
`pydantic-core` wheel for each of CPython 3.9, 3.10, 3.11, 3.12 and 3.13, and `pip` picks the
matching one. Windows on ARM is the exception, and the reason is upstream: `pydantic-core` publishes
no `win_arm64` wheel for CPython 3.9 or 3.10.

If you are unsure which one you need, the two questions that decide it are:

```
python -c "import platform, sysconfig, sys; print(sys.version_info[:2], platform.machine(), sysconfig.get_platform())"
```

and, on Linux, whether the distribution is glibc or musl (`ldd --version` naming `musl` means musl;
Alpine always does).

You do not have to get this right by inspection. The bundle checks it for you -- see 4.2.

### 4.2 Install

Unpacking needs no tool beyond the interpreter you are about to install into:

```
python -m zipfile -e acronymkit-0.2.0-offline-linux-x86_64-cp39-cp313.zip .
cd acronymkit-0.2.0-offline-linux-x86_64-cp39-cp313
```

Check the archive before you use it. `verify.py` hashes every file against `SHA256SUMS`, reports any
`.whl` sitting in the directory that is *not* listed (the install command points `pip` at this
directory, so an extra wheel here is a wheel `pip` would consider), and compares the bundled wheel
tags against the running interpreter:

```
python verify.py
```

It exits `0` if the bundle is intact and serves this interpreter, `1` if a file is missing, changed
or unlisted, and `2` if the bundle is intact but was built for a different machine. That last case is
the one worth having: it is the difference between finding out now and finding out from a resolver
error.

Then install. Either of these:

```
pip install --no-index --find-links=. acronymkit
pip install --no-index --find-links=. "acronymkit[cli]"
```

Or, with `pip` checking a pinned SHA-256 for every file as it installs -- the stronger form, and the
one to use if the archive travelled through anything you do not control:

```
pip install --no-index --find-links=. --require-hashes -r requirements.txt
```

`requirements.txt` installs the extras the bundle was built with (`cli`, by default), so it is also
the shortest way to get the whole thing.

If your `pip` is configured with an index in `pip.conf`/`pip.ini` or `PIP_INDEX_URL` and you want to
be certain none of it applies, add `--isolated`, which makes `pip` ignore its configuration files
and environment variables:

```
pip install --isolated --no-index --find-links=. "acronymkit[cli]"
```

Confirm the result:

```
acronymkit generate "Portable Document Format"
acronymkit doctor --offline
```

`doctor --offline` exits non-zero if this particular installation is not air-gap ready; see
`docs/OFFLINE.md`.

### 4.3 Extras, offline

The published bundles carry the `cli` extra and nothing else. `cli` is one small pure-Python wheel
(`click`) and it is what makes the `acronymkit` command work; `nlp` and `transformers` are excluded
because they are large and because their *models* are not solved by staging wheels (4.4).

To stage them anyway, build the bundle yourself with the extras you want:

```
python tools/make_offline_bundle.py --target linux-x86_64 --extras cli,nlp
```

Measured on the host below, for a single-interpreter host bundle: `--extras cli` produces 8
distributions in a 3.2 MB archive, `--extras cli,nlp` produces 50 distributions in a 45.3 MB archive
(spaCy, NLTK, NumPy, thinc, blis and their dependencies). A five-interpreter bundle multiplies only
the compiled wheels, not the pure-Python ones.

Install from it exactly as in 4.2; `requirements.txt` names the extras that were staged.

### 4.4 What a bundle does not solve: spaCy and NLTK models

A wheel bundle is a solution for *distributions*. spaCy and NLTK language data are not distributions
in the same sense, and they are the part that surprises people on an air-gapped host: the library
installs, imports, and then fails at first use because its model is not there.

`acronymkit` does not paper over this. On a host where the backend is installed and its data is not,
it raises rather than fetching -- there is no download path in the package (`docs/OFFLINE.md` has the
measurement). What you see is the backend's own error, immediately:

```
>>> import spacy; spacy.load("en_core_web_sm")
OSError: [E050] Can't find model 'en_core_web_sm'. ...
```

Two separate problems, two separate answers:

**spaCy models are published as wheels**, on their own GitHub releases, so they can be staged the
same way everything else is:

```
pip download --only-binary=:all: --dest models \
  "https://github.com/explosion/spacy-models/releases/download/en_core_web_sm-3.8.0/en_core_web_sm-3.8.0-py3-none-any.whl"
# then, on the air-gapped host:
pip install --no-index --find-links=models en_core_web_sm
```

Match the model's major/minor to the spaCy you installed -- a `3.8.x` model needs spaCy 3.8.

**NLTK data is not a wheel.** Fetch it into a directory on a networked machine, copy the directory
across, and point NLTK at it. Set the destination with `NLTK_DATA` rather than with the downloader's
`-d` flag:

```
mkdir nltk_data
NLTK_DATA=$PWD/nltk_data python -m nltk.downloader punkt_tab stopwords
# on the air-gapped host, after copying nltk_data across:
export NLTK_DATA=/opt/nltk_data      # setx NLTK_DATA C:\opt\nltk_data  on Windows
```

Avoiding `-d` is not a style preference. On NLTK 3.10.2, `python -m nltk.downloader -d ./nltk_data
punkt_tab` fails with `Security Violation [Downloader._download_package]: Unauthorized path` and
leaves the destination empty -- a path check in recent NLTK rejects a target that is not on
`nltk.data.path`, and `-d` does not put it there. An absolute path does not help. `NLTK_DATA` does,
and it is the variable you need on the receiving host anyway, so that is one thing to get right
instead of two.

Both sets of data carry their own licences, which are not this project's licence and not necessarily
MIT. Read them before redistributing either inside your organisation.

### 4.5 A platform we do not publish a bundle for

Anything the table in 4.1 does not list -- 32-bit Windows, musl on ARM, an interpreter newer than the
range, a BSD, a big-endian mainframe -- has a general answer: build the bundle **on a networked
machine of that platform**.

```
python tools/make_offline_bundle.py --target host
```

`--target host` passes no platform override to `pip`, so the running interpreter's own wheel tags
decide what is downloaded and the archive is correct for that machine by construction. That is
strictly more reliable than naming a platform tag, which is why it is also the right choice when you
are unsure.

Without a checkout of this project, the same thing by hand:

```
pip download --only-binary=:all: --dest bundle \
  "acronymkit[cli] @ https://github.com/pierce-lonergan/AcronymKit/releases/download/v0.2.0/acronymkit-0.2.0-py3-none-any.whl"
cd bundle && pip install --no-index --find-links=. "acronymkit[cli]"
```

`--only-binary=:all:` is not a preference. An sdist would have to be *built* during the offline
install, a build needs build dependencies, and fetching those needs an index -- so admitting one
sdist quietly reintroduces the requirement the bundle exists to remove. If it fails because some
dependency publishes no wheel for your platform, that is the finding, and no amount of staging will
hide it.

Other useful arguments: `--list-targets` prints the registry, `--target` is repeatable, `--all`
builds every target, `--python-version` (repeatable) overrides the interpreter list, and
`--output-dir` says where the archives go.

On Windows, keep `--output-dir` short. A manylinux `pydantic-core` filename is 77 characters and the
bundle directory name adds another 48, so a deep working directory clears the 260-character limit;
the script says so explicitly if it hits it, rather than passing on the operating system's
`cannot find the path specified`.

---

## 5. Verifying what you got

Three checks answering three different questions, and then a fourth section on the SBOMs, which are
not a check at all. None of the three substitutes for another.

### 5.1 Integrity: SHA-256 against `SHA256SUMS`

Every release carries a `SHA256SUMS` covering every other asset: the wheel, the sdist, each bundle,
and both SBOMs. Download it alongside whatever you took and check:

```
sha256sum -c SHA256SUMS            # Linux
shasum -a 256 -c SHA256SUMS        # macOS
```

`sha256sum -c` reports a file it was not given as `FAILED open or read`, so check from a directory
holding everything you downloaded, or pass `--ignore-missing`.

On Windows PowerShell:

```
Get-Content SHA256SUMS | ForEach-Object {
  $fields = $_ -split '\s+', 2
  $name = $fields[1].Trim()
  if (Test-Path $name) {
    $actual = (Get-FileHash -Algorithm SHA256 $name).Hash.ToLower()
    if ($actual -ne $fields[0]) { Write-Error "CHANGED: $name" } else { "OK: $name" }
  }
}
```

Inside a bundle, the same file covers the bundle's own contents, and `python verify.py` does the
check with no external tool at all.

**What this proves:** that the bytes you have are the bytes the checksum file describes. **What it
does not prove:** that either came from this project. `SHA256SUMS` travels next to the artifacts it
describes, so anyone who could replace one could replace both. That is what section 5.2 is for.

### 5.2 Provenance for the GitHub copy: `gh attestation verify`

The release workflow generates a signed SLSA build-provenance attestation over everything named in
`SHA256SUMS`, tying each artifact to the workflow, repository and commit that produced it. Verify a
downloaded asset against it:

```
gh attestation verify acronymkit-0.2.0-py3-none-any.whl --repo pierce-lonergan/AcronymKit
```

`--owner pierce-lonergan` works in the same place if you want to accept any repository under that
owner, which is looser and rarely what you want.

This needs network access to GitHub -- it is a check to run on the machine that downloads the
artifact, not on the air-gapped one that installs it.

An asset published before that step existed has no attestation, and the command says so with an
HTTP 404 naming the digest it looked for. As of writing that is the state of the `v0.2.0` assets:
the attestation step is in `.github/workflows/publish.yml` from this change onwards, so it applies to
releases made after it, not retroactively.

### 5.3 Provenance for the PyPI copy: PEP 740

PyPI publishing here uses trusted publishing (OIDC, no stored token), and
`pypa/gh-action-pypi-publish` generates PEP 740 attestations for the files it uploads. Those live on
PyPI, not on GitHub, and they are a separate claim about a separate download. PyPI serves them from
its Integrity API:

```
https://pypi.org/integrity/<project>/<version>/<filename>/provenance
```

and the `pypi-attestations` CLI verifies one:

```
pip install pypi-attestations
pypi-attestations verify pypi --repository https://github.com/pierce-lonergan/AcronymKit \
  pypi:acronymkit-0.2.0-py3-none-any.whl
```

Two honest caveats on this section. `acronymkit` is not on PyPI yet, so there is nothing to point
this at today. And the verification could not be completed from the machine these docs were written
on: `pypi-attestations` failed with `TUFError: Failed to refresh TUF metadata` while fetching the
Sigstore trust root. What *was* confirmed here is that the Integrity API endpoint above returns a
provenance document for a project that has one, and that the CLI takes exactly the arguments shown.

### 5.4 Software bills of materials

Each release also carries `acronymkit-<version>.cdx.json` (CycloneDX 1.6) and
`acronymkit-<version>.spdx.json` (SPDX), generated from a clean environment holding the built wheel
and nothing else -- so they list this distribution's runtime dependencies rather than the build
machine's. They are covered by `SHA256SUMS` and by the attestation like every other asset.

---

## 6. When it goes wrong

**`ERROR: Could not find a version that satisfies the requirement pydantic-core==...`, installing
from a bundle.** The bundle is for a different interpreter or platform. Run `python verify.py` in the
bundle directory; it names the mismatch. Then take the archive whose filename matches your platform,
or build one with `--target host` (4.5).

**`zsh: no matches found: acronymkit[cli]`.** Quote the requirement: `"acronymkit[cli]"`. `zsh` and
`fish` expand square brackets as globs.

**`ERROR: No matching distribution found for acronymkit==0.2.0` from `pip download`.** The package is
not on the index you are using. Use the PEP 508 direct-reference form in 4.5, which names the release
wheel by URL and needs no index entry for `acronymkit` at all.

**`pip` still reaching for an index despite `--no-index`.** It is not the index; `--no-index` is
absolute. Something else in the command is a network reference -- a `-r` file with a URL in it, or a
requirement with a direct URL. Add `--isolated` to rule out `pip.conf` and `PIP_*` environment
variables as well.

**`This command needs the CLI extra: pip install acronymkit[cli]`.** The library is installed but
`click` is not. From a bundle, that message's command needs the offline flags too:
`pip install --no-index --find-links=. "acronymkit[cli]"`.

**`sha256sum: ... : No such file or directory` for every line.** Either you are checking from the
wrong directory, or the checksum file has CRLF line endings, in which case `sha256sum` looks for a
filename ending in a carriage return. Bundles and releases are written with LF endings for exactly
this reason; if you see it, something re-wrote the file in transit.

**`[WinError 3] The system cannot find the path specified` while *building* a bundle on Windows.**
Path length. Use a short `--output-dir`, such as `C:\bundles`.

---

## Appendix: what was actually run

Everything below was done against `acronymkit` 0.2.0 on this host:

| | |
|---|---|
| Host | Windows 11 Pro (26200) |
| Interpreter | CPython 3.13.4 |
| `pip` | 26.0 |
| `gh` | 2.88.0 |

**Run, and succeeded.** Each of the four install routes, into its own fresh virtual environment: the
release-asset URL, `git+https` at both the tag and the full commit SHA, `pip install .` from the
checkout, and the bundle. For the bundle route specifically: an archive built for `windows-amd64`
through the *cross-platform* code path (`--platform win_amd64`, CPython 3.9 through 3.13) was
unpacked with `python -m zipfile -e`, checked with `verify.py` and with `sha256sum -c SHA256SUMS`,
and installed with `--no-index --find-links=.` in all four forms shown -- plain, with the extra, with
`--isolated`, and with `--require-hashes -r requirements.txt`. The result ran
`acronymkit generate "Portable Document Format"` (returning `PDF`) and `acronymkit doctor --offline`
(reporting OK). A `--target host` bundle and a `--extras cli,nlp` bundle were built and installed the
same way; spaCy 3.8.15 and NLTK 3.10.2 installed from the second under `--no-index` and imported.
The NLTK data recipe in 4.4 was run, including the `-d` failure it warns about, and the copied
directory then tokenised and loaded stop words with `NLTK_DATA` set. The spaCy route was run in full
too: the model wheel downloaded, installed with `--no-index --find-links=models`, and
`spacy.load("en_core_web_sm")` returned a working pipeline. `verify.py` was confirmed to reject a
truncated wheel, a deleted wheel and an unlisted one, and to exit 2 when handed a `linux-x86_64`
bundle here. Section 5.1 was run three ways -- `sha256sum -c`, the PowerShell loop, and `verify.py`.

These are `--no-index` installs, which is a claim about `pip` and not about sockets. The stronger
statement -- that nothing reaches for the network at all -- is made and enforced by the `air-gap`
job in CI, and documented in `docs/OFFLINE.md`.

**Run, but the success path could not be reached from here.** `gh attestation verify` reported
HTTP 404 for the current assets, which is the correct answer for artifacts published before the
attestation step existed; a successful verification cannot be shown until a release is made with it
in place. `pypi-attestations` failed with `TUFError: Failed to refresh TUF metadata` fetching the
Sigstore trust root from this machine. Its argument shape was read from the installed tool, and the
PyPI Integrity API endpoint was confirmed to return a provenance document for a project that has one.

Nothing here was written from memory of how these tools behave. Where a command could not be
executed from this machine, the paragraph containing it says so in place, rather than leaving the
reader to discover it.
