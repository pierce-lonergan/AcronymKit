# Release checklist

This distribution has never been published. `pip install acronymkit` returns 404 today, which is why
[D-001](DECISIONS.md) could cut publishing and why [D-023](DECISIONS.md) could call a breaking change
free. The first upload ends both of those, so this file is written for the person doing it at
eleven at night with nobody to ask.

Read section 1 before you start. It is the list of things that cannot be undone.

---

## 1. The one-way doors

**A version number, once uploaded, is spent forever.** PyPI does not allow a filename to be reused,
even after the release, the project or the file is deleted — see
[Project deletion](https://pypi.org/help/#file-name-reuse). Deletion is permanent and frees the
storage, not the name. If `acronymkit-0.3.0-py3-none-any.whl` reaches PyPI in a state you regret, the
fix is `0.3.1`. There is no other fix. Nothing in section 8 changes this.

**Publishing a GitHub release *is* the upload.** `.github/workflows/publish.yml` triggers on
`release: types: [published]`. A *draft* release triggers nothing; clicking **Publish release**
starts the build, the PyPI upload, the attestation and the asset upload, in that order, with no
manual gate in between unless you add a required reviewer to the `pypi` environment (section 2).

**A "pending publisher" does not reserve the name.** Until the first successful upload, anybody may
register `acronymkit` on PyPI, and if they do, your pending publisher is invalidated —
[PyPI docs](https://docs.pypi.org/trusted-publishers/creating-a-project-through-oidc/). Register it
shortly before you release, not months ahead.

**CI does not run on tags.** `ci.yml` triggers on `push` to `main`, on pull requests to `main`, and
on manual dispatch. Pushing `v0.3.0` runs nothing. Whatever green tick you are relying on has to be
the one on the commit you are about to tag.

---

## 2. One-time setup, before the first release only

Everything in this section is done by hand, in a browser, and none of it is in the repository.

### 2.1 A PyPI account that can upload

Register at <https://pypi.org/account/register/> and enable two-factor authentication, which PyPI
requires on every account. Trusted publishing means no API token is stored in this repository — the
workflow authenticates with a short-lived OIDC token — but the account still has to exist, and it
owns the project once the project is created.

### 2.2 Register the PENDING publisher on PyPI

The project does not exist yet, so there is nothing to add a publisher *to*. PyPI's answer is a
"pending publisher": a trusted-publisher configuration attached to your account rather than to a
project, which creates the project on first use and converts itself into a normal publisher.

Go to <https://pypi.org/manage/account/publishing/> — the **Publishing** entry in the account
sidebar, *not* a project's settings — and fill in the GitHub Actions form. It asks for five values.
These are read out of this repository, not remembered:

| Field on the form | Value | Where it comes from |
|---|---|---|
| PyPI Project Name | `acronymkit` | `pyproject.toml` `[project] name`; also the `url:` of the `publish-pypi` job, `https://pypi.org/p/acronymkit` |
| Owner | `pierce-lonergan` | the owner segment of `[project.urls] Repository` in `pyproject.toml` |
| Repository name | `AcronymKit` | the repository segment of the same URL |
| Workflow name | `publish.yml` | the filename of `.github/workflows/publish.yml` — the filename alone, no path |
| Environment name | `pypi` | `publish.yml`, job `publish-pypi`, `environment: name: pypi` |

The environment field is optional to PyPI and **mandatory here**, because the job declares an
environment. If it is left blank, or spelled differently, the upload fails with `invalid-publisher`
even though everything else is correct — that mismatch is the single most common cause of a failed
first release.

### 2.3 Register the TestPyPI pending publisher too, if you want the dry run

TestPyPI is a separate site with a separate account and a separate form:
<https://test.pypi.org/manage/account/publishing/>. Same four repository values; the environment name
is **`testpypi`**, from the `publish-testpypi` job.

Section 5 is the dry run. It is optional. It is also the only way to find out whether section 2.2 was
filled in correctly without spending version `0.3.0` to do it.

### 2.4 Create the two GitHub environments

Repository **Settings → Environments → New environment**, named exactly `pypi` and `testpypi`. They
need no secrets and no variables — the whole point of trusted publishing is that there is nothing to
put in them. Create them anyway: a job naming an environment that does not exist will have it created
implicitly with no protection rules, and the name has to match what PyPI was told either way.

This is also where a required reviewer goes, if you want a human gate between "release published" and
"uploaded to PyPI". Recommended for the first one.

### 2.5 Check that OIDC is not blocked

`publish.yml` requests `permissions: id-token: write`. An organisation policy that restricts the
`GITHUB_TOKEN` or disables OIDC will make that request fail at job start. Confirm under
**Settings → Actions → General** that workflows may request write permissions.

---

## 3. Pre-flight, in a clean working tree

All of this is by hand and all of it runs locally. Every command below was run against the tree this
file was written in and passed; the counts are what to expect, not what to assert.

```
git status --short                       # nothing but what you intend to release
git rev-parse --abbrev-ref HEAD          # main
git pull --ff-only                       # up to date with origin/main
```

Then the four standing gates, in the wider form (CI lints `src tests tools`; the project rule is
`src tests tools bench`, so the local run is the stricter one):

```
python -m pytest tests -q                # 4,135 passed, 10 skipped, 1 xfailed
python -m ruff check src tests tools bench
python -m ruff format --check src tests tools bench
python -m mypy                           # no issues in 40 source files
python tools/check_claims.py             # all backed by bench/results.json, a citation, or the allowlist
```

And the three resource gates the `resources` CI job runs, which nothing else covers:

```
python tools/validate_resources.py --require
python tools/build_ngram_model.py --check
```

plus the bundled-schema equality check. **Do not run it against the working tree on Windows.** The
canonical copy and the bundled copy are the same blob in git, but a checkout that predates
`.gitattributes`' `*.json text eol=lf` rule can hold one of them with CRLF line endings, and the
hashes then differ for a reason that does not exist on the Linux runner. Compare what git stores:

```
python - <<'PY'
import hashlib, subprocess
paths = ("schemas/acronym-engine-result.schema.json",
         "src/acronymkit/resources/acronym-engine-result.schema.json")
digests = {p: hashlib.sha256(subprocess.run(["git", "show", f"HEAD:{p}"],
                                            capture_output=True).stdout).hexdigest()
           for p in paths}
print(*(f"{d}  {p}" for p, d in digests.items()), sep="\n")
print("match" if len(set(digests.values())) == 1 else "DIVERGED -- fix before releasing")
PY
```

If they have genuinely diverged, `cp schemas/... src/acronymkit/resources/...` and commit; if it is
only the line endings, `git add --renormalize .` fixes the working tree and changes nothing in the
history.

**Get CI green on the commit you are about to tag**, and confirm it on GitHub rather than inferring
it. Section 1 says why: the tag will not run it for you.

---

## 4. Version, changelog, tag — the three that must agree

`pyproject.toml` `[project] version` is the only place the version is written. `__version__` is
resolved at runtime from installed distribution metadata, so there is no second constant to bump and
no risk of the two drifting.

Three things must line up, and `publish.yml` enforces one of the three:

```
pyproject.toml   version = "0.3.0"
CHANGELOG.md     ## [0.3.0] — <date>          heading, plus the [0.3.0]: link at the foot
git tag          v0.3.0                       -- the "v" is stripped and the rest must match exactly
```

The assertion, in the `build` job, is `GITHUB_REF_NAME.lstrip("v")` compared against the version
parsed out of the built wheel's filename. Simulated against this tree's wheel:

```
v0.3.0          -> "0.3.0"          OK
0.3.0           -> "0.3.0"          OK       (works, but use the v form -- CHANGELOG links assume it)
v0.3.1          -> "0.3.1"          FAILS
release-0.3.0   -> "release-0.3.0"  FAILS
```

It runs **only on a `release` event**. A `workflow_dispatch` run with `target: pypi` skips it
entirely and will happily upload whatever version is on the default branch. Treat manual dispatch to
PyPI as a thing you do not do.

Also check, by eye:

- `## [Unreleased]` is empty, and everything under it has moved into the release section;
- the release section's date is today's;
- the footer carries `[Unreleased]: .../compare/v0.3.0...HEAD` and `[0.3.0]: .../releases/tag/v0.3.0`;
- nothing in the release notes describes work that was not done. A changelog bullet saying a change
  was *considered and not made* is false the moment the change ships, and this repository has one of
  those in flight: see the note at the end of section 9.

---

## 5. Build and inspect locally

Clear the residue first. A stale `src/acronymkit.egg-info` is enough to make `importlib.metadata`
report a version that is not the one you are building, which is a confusing hour at eleven at night:

```
rm -rf dist build src/*.egg-info
python -m build
python -m twine check dist/*
```

**Never read the version out of a source checkout.** `__version__` resolves from installed
distribution metadata and falls back to a hard-coded constant when there is none — in a checkout with
no `.egg-info` and nothing installed, `import acronymkit; acronymkit.__version__` currently answers
`0.1.0`, which is neither a bug nor the version you are releasing. `pyproject.toml` is the source of
truth; the built wheel's filename is the confirmation.

Expect `Successfully built acronymkit-<version>.tar.gz and acronymkit-<version>-py3-none-any.whl`
and `PASSED` for both files. Then reproduce the four checks the `build` CI job makes, because finding
out here costs nothing and finding out during a release costs a version number:

**The wheel size budget.** `786_432` bytes, from `ci.yml`. The check prints the largest compressed
entries; read them before ever raising the ceiling.

```
python - <<'PY'
import glob, os, zipfile
BUDGET = 786_432
wheel = glob.glob("dist/*.whl")[0]
size = os.path.getsize(wheel)
print(f"{wheel}: {size} B of {BUDGET} B ({size / BUDGET:.1%})")
for item in sorted(zipfile.ZipFile(wheel).infolist(), key=lambda i: -i.compress_size)[:5]:
    print(f"  {item.compress_size:>9} B  {item.filename}")
assert size <= BUDGET, f"over budget by {size - BUDGET} B"
PY
```

**The wheel carries its resources.** `py.typed`, the bundled schema, `lexicon_en.txt`, `ngram_en.json`
and four stopword files. Only English ships a lexicon and an n-gram model; the other languages'
sources are copyleft, per `data/LICENSES.md`.

**The wheel works with no checkout present.** Install it into a throwaway environment, `cd` somewhere
else, and exercise the engine and the governed CLI:

```
python -m venv /tmp/relcheck
/tmp/relcheck/bin/python -m pip install --quiet dist/*.whl jsonschema click
cd /tmp && /tmp/relcheck/bin/python -c "
from acronymkit import AcronymEngine
from acronymkit.serialization import load_schema, validate_result
r = AcronymEngine().generate('Portable Document Format')
assert r.primary_acronym == 'PDF'
assert load_schema()['title'] == 'AcronymEngineResult'
validate_result(r.to_dict())
print('wheel OK')"
/tmp/relcheck/bin/acronymkit version          # 'acronymkit <version>'; note there is no --version flag
```

On Windows the venv's executables live in `Scripts/` rather than `bin/`.

**The sdist can run its own test suite.** This is what `MANIFEST.in` exists for and it has broken
three times:

```
mkdir -p /tmp/sdist && tar -xzf dist/*.tar.gz -C /tmp/sdist --strip-components=1
cd /tmp/sdist && python -m pip install --quiet ".[dev]" && python -m pytest -q -x
```

The five files whose absence CI checks for by name, each because leaving it out shipped a claim
without its evidence: `tests/conftest.py`, `schemas/acronym-engine-result.schema.json`,
`bench/results.json`, `data/LICENSES.md`, `tests/airgap_socket_guard.py`.

---

## 6. The dry run on TestPyPI

Optional, recommended for the first release, and the only cheap way to find out whether section 2.2
is right.

**Actions → Publish to PyPI → Run workflow**, with `target: testpypi`. Only `build` and
`publish-testpypi` run: `attest` and `release-assets` are gated on `github.event_name == 'release'`,
and the tag assertion is skipped, so this exercises the build, the SBOMs, the bundles and the OIDC
handshake without touching a tag.

Verify it landed, from a clean environment. TestPyPI does not mirror PyPI, so the real dependencies
have to come from the real index:

```
python -m venv /tmp/testpypi && /tmp/testpypi/bin/python -m pip install \
  --index-url https://test.pypi.org/simple/ \
  --extra-index-url https://pypi.org/simple/ \
  "acronymkit==<version>"
```

TestPyPI is periodically pruned and is not a backup of anything. Do not treat a successful dry run as
permission to skip section 5.

---

## 7. Tag, release, and what CI then does

By hand:

```
git tag -a v0.3.0 -m "acronymkit 0.3.0"
git push origin v0.3.0
gh release create v0.3.0 --title "acronymkit 0.3.0" --notes-file <notes>   # or the web UI
```

Publishing the release is the trigger. From here everything is CI, in this order:

| Job | What it does | Notes |
|---|---|---|
| `build` | `python -m build`, `twine check`, the tag/version assertion, one offline install bundle per platform, a CycloneDX SBOM and an SPDX SBOM, a shape check on both, and one `SHA256SUMS` over everything | The only job that needs the network for anything other than the index: bundle building downloads roughly 80 MB of third-party wheels and re-resolves each bundle offline. It has a 45-minute ceiling so a hung index fails rather than hangs |
| `publish-pypi` | Uploads `dist/` with `gh-action-pypi-publish` over OIDC, in environment `pypi` | Generates PEP 740 attestations by default; those are provenance for the *PyPI* copy |
| `attest` | `attest-build-provenance` over `SHA256SUMS` | Holds a signing identity and cannot write to the repository |
| `release-assets` | `gh release upload --clobber` for every file in `release/` | Can write to the repository and holds no signing identity. Runs after `attest`, so nothing reaches the release page unattested |

`attest` and `release-assets` run on a `release` event only. If you got here by manual dispatch, the
release page gets nothing.

---

## 8. Verify the upload

```
open https://pypi.org/project/acronymkit/<version>/     # both files listed, description renders
python -m venv /tmp/fresh && /tmp/fresh/bin/python -m pip install "acronymkit==<version>"
/tmp/fresh/bin/python -c "import acronymkit; print(acronymkit.__version__)"
/tmp/fresh/bin/acronymkit version
```

Then check the artifacts a consumer might actually audit:

- the release page carries the wheel, the sdist, seven offline bundles, both SBOMs and `SHA256SUMS`;
- `sha256sum -c SHA256SUMS` passes against the downloaded assets (the file is written with LF
  endings deliberately — `sha256sum -c` reports every line of a CRLF file as a missing file);
- `gh attestation verify <file> --repo pierce-lonergan/AcronymKit` succeeds for a release asset;
- PyPI shows attestations against the uploaded files;
- `pip install --no-binary :all: "acronymkit==<version>"` builds from the sdist without error.

Confirm the tier-0 promise survived packaging, since this is the artifact users get rather than the
checkout CI tested:

```
/tmp/fresh/bin/python -c "
import sys, acronymkit
print('optional deps resident:', [m for m in ('click','spacy','nltk','onnxruntime','transformers') if m in sys.modules] or 'none')
print('pydantic resident:', 'pydantic' in sys.modules)"
```

---

## 9. When it goes wrong

**Read section 1 first.** The version number is spent. Everything below is about limiting the damage,
not undoing it.

| What happened | What to do |
|---|---|
| The tag does not match the version | The `build` job fails the assertion and **nothing is uploaded**. Delete the release and the tag, fix `pyproject.toml`, tag again. No version is spent |
| `invalid-publisher` on the upload step | The OIDC claim did not match the pending publisher. Check all five values from section 2.2, the environment name first. Nothing is uploaded; fix and re-run the job |
| The upload succeeded, the release assets did not | Re-run the `release-assets` job. `gh release upload --clobber` is idempotent, so a partial upload is safe to repeat |
| The bundle step failed on a network hiccup | Re-run the `build` job. It is deterministic apart from the downloads |
| Uploaded, and the release is bad | **Yank it.** A yanked release is ignored by installers unless a requirement pins it exactly, so people who already depend on it are not broken and nobody new picks it up. This is the correct response and it is reversible |
| Uploaded something that must not remain public | Delete it — and understand you have burned the filename permanently, that deletion is irreversible, and that anyone who already installed it still has it. Then publish a fixed version under a new number |

Yanking and deletion are different operations for a reason: yanking is a signal, deletion frees
storage and nothing else. Prefer yanking. See
[Yanking](https://docs.pypi.org/project-management/yanking/).

---

## 10. Landmines specific to this repository

Each of these has a plausible chance of biting the first release and none of them is obvious from the
workflow file.

**The SBOM check asserts that pydantic is a dependency.** `publish.yml` fails the build unless
`pydantic`, `pydantic-core` and `typing-extensions` all appear as components in both SBOMs. That is
true today and is the right check today. [D-027](DECISIONS.md) removed pydantic from
`acronymkit.governed` only; if the rest of [D-023](DECISIONS.md)'s migration is ever finished, this
step turns into a release-blocking failure whose message will not mention the migration. Update it in
the same commit that removes the dependency.

**Manual dispatch to PyPI skips the tag assertion.** Section 4. Do not use it.

**CI does not run on tags.** Section 1.

**The schema-copy check is newline-sensitive on a Windows checkout.** Section 3.

**The offline-bundle step is the long pole and the only one that needs a working index.** If it fails
after `publish-pypi` has already run, PyPI has your release and the GitHub release page does not —
re-run `build` and `release-assets` rather than re-tagging.

**A changelog bullet in the current `0.3.0` section says the pydantic migration is "recommended, not
executed" and that "no code has changed".** [D-027](DECISIONS.md) executed it for
`acronymkit.governed`, so that sentence is false as written and the section has no `Changed` entry
for the migration. `CHANGELOG.md` is not this file's to edit; check it has been fixed before you tag,
because it is the first thing a reader of the release notes will hit.

---

## See also

- [`DECISIONS.md`](DECISIONS.md) — why the package was unpublished for three releases (D-001), what
  the first upload costs in future freedom (D-023), and what changed in the governed subsystem just
  before it (D-027, D-028).
- [`INSTALL.md`](INSTALL.md) — the four install routes that do not go through PyPI, which is what the
  release assets exist to serve.
- [`OFFLINE.md`](OFFLINE.md) — the air-gap story the sdist's shipped socket guard lets a reviewer
  re-run for themselves.
