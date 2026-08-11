# acronymkit for enterprise review

For the person who has to decide whether this package may be installed. It is short on purpose.
[docs/OFFLINE.md](OFFLINE.md) is the long form — the security reviewer's document, with the method
behind every claim below. [docs/SUPPORT_MATRIX.md](SUPPORT_MATRIX.md) is the capability detail.
This page is the decision.

## The one-paragraph answer

`acronymkit` runs entirely from its own wheel and needs no network at any point after install. The
base install is `pydantic` plus `typing-extensions` — five packages once
resolved — and the engine reads seven data files that ship inside the distribution: an English word
list, an English character model, four stop-word files, and the JSON Schema used for interchange
validation. Nothing downloads a model, nothing writes to a cache directory, nothing reads the
user's home directory, and there is no telemetry to switch off because none was written. What does
**not** work offline: the neural tier, which is not implemented at all in this release; and Tier 1
on a host where spaCy or NLTK is installed but its model or corpus is not — that case fails with a
typed error in under a millisecond and never attempts a fetch, which is measured rather than
assumed. To check a specific installation, run `acronymkit doctor --offline`: it prints the
capability report and exits non-zero if anything in *that* environment could make the process reach
the network. To check the claim itself rather than one installation, read the `air-gap` job in
`.github/workflows/ci.yml` and run the four commands in
[OFFLINE.md section 8](OFFLINE.md#8-how-to-verify-it-yourself).

## Installing into an air-gapped environment

The wheel is `acronymkit-0.2.0-py3-none-any.whl`: pure Python, no compiled extension of its own, no
build step, no post-install hook. A wheel built from this tree while writing this page was 404,651 B
over 41 entries — a figure to re-derive per release rather than quote, which is why the `build` job
in CI re-measures it on every push against a 786,432 B budget. Three install shapes, in increasing
order of how much your policy asks for:

**A mirrored index.** Nothing special is needed. There is no first-run download to survive, so an
internal PyPI mirror serves it like any other pure-Python wheel:

```bash
pip install --index-url https://pypi.internal.example/simple acronymkit
```

**No index at all.** Stage the wheels once where a network exists, carry the directory across, and
install from it:

```bash
# on a connected host
pip download --dest wheelhouse --only-binary=:all: acronymkit

# on the air-gapped host
pip install --no-index --find-links=wheelhouse acronymkit
```

`--only-binary=:all:` is not a preference. A source distribution would have to be *built* during
the offline install, a build needs build dependencies, and fetching those needs an index — so
admitting one sdist quietly reintroduces the requirement you are trying to remove. This is the
exact shape the `air-gap` CI job runs on every push, against a wheelhouse it stages itself and then
installs from inside a network namespace with no route.

**Hash-pinned.** Add the hashes and pip will refuse anything that does not match:

```
# requirements.txt
acronymkit==0.2.0 --hash=sha256:<digest of the wheel you audited>
pydantic==2.11.7 --hash=sha256:...
pydantic-core==2.33.2 --hash=sha256:...
annotated-types==0.7.0 --hash=sha256:...
typing-inspection==0.4.1 --hash=sha256:...
typing-extensions==4.16.0 --hash=sha256:...
```

```bash
pip install --require-hashes --no-index --find-links=wheelhouse -r requirements.txt
```

Those six lines are the whole base closure — five dependencies and the package itself. Pin the
versions your own audit resolved; the ones above are what the measurement host had.
`--require-hashes` is an operator step this project's CI does not currently exercise, so treat the
flag as a recommendation and the `--no-index --find-links` form above as the tested one.

Once installed, the resources are pinned too, independently of pip: `acronymkit doctor --format
json | jq .resources.digests` prints a SHA-256 per bundled file, and
[OFFLINE.md section 7](OFFLINE.md#7-every-bundled-resource) lists the expected values to diff
against.

> **A fuller install guide, `docs/INSTALL.md`, is being written separately and did not exist when
> this page was finished.** If it is present in your checkout, prefer it for the mechanics — a
> ready-made offline bundle, the wheelhouse layout, and the per-platform details — and read this
> section only for what the policy question turns on.

## Capabilities, in brief

| Capability | Works offline | Needs |
|---|---|---|
| Tier 0 — generation, backronyms, extraction, disambiguation, scoring, tokenisation, batch, async | Yes, entirely from the wheel | Base install only |
| CLI (`acronymkit …`) | Yes | `pip install 'acronymkit[cli]'` — adds `click` (and `colorama` on Windows) |
| Schema validation (`validate_result`) | Yes | `jsonschema`, a development extra. `load_schema()` needs nothing |
| Capability report (`capabilities()`, `doctor`) | Yes | Nothing; stdlib-only, works on a broken install |
| Tier 1 — part-of-speech-aware generation | Yes, **if** the model or corpus is already in the image | `pip install 'acronymkit[nlp]'` **plus** a spaCy model or NLTK's `averaged_perceptron_tagger`, staged by you |
| Tier 2 — neural | Not implemented in this release | — |

English is the only complete language: it ships a word list and a character model. French, Spanish
and German ship stop words only, and the engine says so in `metadata.warnings` rather than
degrading silently. [docs/SUPPORT_MATRIX.md](SUPPORT_MATRIX.md) has the per-capability, per-tier
detail with the measurement behind each cell.

## Security posture

Every line states a fact and names what proves it. A claim with no proof named is not on this list.

| Claim | Proof, by name |
|---|---|
| No telemetry, no analytics, no usage reporting | `capabilities()["network"]["telemetry"]` is `False`, asserted by `tests/test_diagnostics.py::test_capabilities_states_that_no_network_io_happens`. The stronger form is the negative below: there is no socket to send it on. |
| No phone-home, no network I/O at all | `air-gap` job in `.github/workflows/ci.yml`, three independent mechanisms: install from a local wheelhouse with `--no-index`; the full suite under `tests/airgap_socket_guard.py` with every socket primitive patched to raise, loaded via `-p` so the patches precede collection; and the whole public API plus every CLI subcommand inside `unshare -n`. The job runs its own positive control first, so a runner where `unshare` did nothing fails rather than passes. |
| No model download, ever, including when a backend's data is missing | Measured in [OFFLINE.md section 5](OFFLINE.md#5-the-optional-backends-nltk-does-not-download): `nltk.pos_tag` raises `LookupError` in well under a millisecond with zero network events. `acronymkit` converts that to `TierUnavailableError` and names the remedy. |
| No `pickle` load path | `src/acronymkit/` imports no `pickle` and calls none of `pickle.load`, `loads`, `parse_raw`, `parse_obj` or `parse_file`; the word occurs twice in the sources, both in comments in `nlp/nltk_backend.py` about a corrupt NLTK tagger file. Source scan, reproducible with `grep -rn pickle src/acronymkit`. *Nuance, so this is not read as more than it is:* the result DTOs are `pydantic` models and are therefore picklable if a caller chooses to pickle them (`tests/test_package.py::test_results_and_config_survive_a_pickle_round_trip`). The library never unpickles anything itself. |
| No compiled extension **in `acronymkit`** | The wheel built from this tree is tagged `py3-none-any` with `Root-Is-Purelib: true`, and no entry in it is a `.so`, `.pyd`, `.dll` or `.dylib`: 27 `.py` modules, `py.typed`, seven data files and the `.dist-info`. **This claim is about `acronymkit`'s own code and stops there.** `pydantic-core`, a base dependency, *does* ship a compiled Rust extension, so the dependency closure contains native code and any policy of "no binaries in the image" is a policy against `pydantic`, not against this package. That binary was inspected separately — its PE import table names eleven DLLs and none of them is a networking DLL — in [OFFLINE.md section 3](OFFLINE.md#3-the-dependency-tree). |
| No optional dependency is imported by a base install | `zero-dependency` job in `.github/workflows/ci.yml` ("Tier 0 has no optional imports") installs the base package alone and asserts `sys.modules` contains none of spaCy, NLTK, click, onnxruntime, transformers or numpy after a full generate + extract cycle. Also `tests/test_package.py::test_tier_zero_imports_nothing_optional` and `::test_importing_the_package_alone_imports_nothing_optional`. |
| No file is written, no home directory is read | Measured under deny-all-write and process-spawn audit hooks across a 53-step drive of the public API: zero write-mode `open()` calls, zero `tempfile.mkstemp`, zero `subprocess`/`exec`/`fork`, zero home-directory reads. [OFFLINE.md section 6](OFFLINE.md#6-filesystem-and-environment), which also states the two exceptions by name. |
| Two environment variables are read, and only to report or to tighten | `ACRONYMKIT_OFFLINE` (can turn strict offline mode *on* for the process; no value turns it off — `tests/test_offline.py::test_no_environment_value_can_turn_offline_off`) and `PYDANTIC_DISABLE_PLUGINS`, read but never written, so `doctor` can report a machine that is already safe. |
| Schema validation cannot become a network request | `load_schema()` reads the bundled resource and nothing else, and `validate_result()` refuses any schema carrying a remote `$ref`. `tests/test_serialization.py::test_remote_refs_flags_every_fetchable_scheme`, `::test_the_shipped_schema_contains_no_remote_reference`, `::test_validate_result_refuses_a_schema_carrying_a_remote_reference`. The hijack that established the rule is D-018 in [docs/DECISIONS.md](DECISIONS.md). |

**One thing a host-based monitor will see, and it is not a finding.** On **Windows only**, calling
`agenerate()` or `abatch_generate()` creates loopback `AF_INET` sockets on `127.0.0.1`. That is
`asyncio`'s `ProactorEventLoop` self-pipe: Windows has no `socketpair(2)`, so CPython synthesises
one from a TCP pair. No `acronymkit` frame appears on the stack of those events, nothing leaves the
machine, and on Linux and macOS the same call reaches `AF_UNIX` and no INET socket appears at all.
It is the single documented exemption in `tests/airgap_socket_guard.py`, narrowed to frames
belonging to CPython's own `socketpair` code object. If your monitor alerts on any AF_INET socket,
expect it here and nowhere else — [OFFLINE.md section 2](OFFLINE.md#2-the-headline-number) has the
eight recorded events.

**The one thing this package cannot close from inside, stated plainly.** `pydantic` scans the
`pydantic` entry-point group and imports whatever advertises itself there, on the path that builds
any model — which here is the path that builds a `Config`. That import runs before any `acronymkit`
code does. The prevention is `PYDANTIC_DISABLE_PLUGINS=1` in your environment; what this package
offers is *detection*: `capabilities()["network"]["third_party_import_hooks"]` lists them, strict
offline mode refuses to start when the list is non-empty, and `acronymkit doctor --offline` exits 1.
[OFFLINE.md section 4a](OFFLINE.md#a-the-pydantic-entry-point-plugin-loader) has the demonstration
and the regression test.

### What to assert on in your own CI

`acronymkit doctor --format json` is built to be a gate rather than a description:

```bash
acronymkit doctor --offline            # exit 1 if this environment could reach the network
acronymkit doctor --format json | jq '.network, .tiers, .resources.digests'
```

`.ok` is `true` when nothing was found, `.problems` lists what was. The same report is available
in-process as `acronymkit.capabilities()`, which imports only the standard library and needs no
extra — so it still answers on an installation that is otherwise broken.

## When something is missing

Every message below was produced by running the failure, on the host described at the end. They are
quoted, not paraphrased, because "it fails with a clear error" is not a thing a reviewer can check.

**Tier 1 requested, no spaCy and no usable NLTK.** Constructing an engine at
`EngineTier.STATISTICAL_NLP` raises `acronymkit.exceptions.TierUnavailableError`, at construction
rather than at first use:

```
Engine tier statistical_nlp is unavailable. Install it with: pip install 'acronymkit[nlp]'
```

The same through the CLI exits 1: `error: Engine tier statistical_nlp is unavailable. Install it
with: pip install 'acronymkit[nlp]'`. **Install:** `pip install 'acronymkit[nlp]'`, plus the model
or corpus — see the next two entries. Or ask for `EngineTier.HYBRID_NLP`, which degrades to Tier 0
with a warning instead of raising, or `AUTO`, which degrades silently.

**spaCy installed, model missing** — and **spaCy not installed at all**, which is the case measured
here. `load_pipeline("en_core_web_sm", "en")` raises `BackendUnavailable`:

```
spaCy is not installed; install it with: pip install 'acronymkit[nlp]'
```

With spaCy present but the model absent the same call reports the model instead: `spaCy model
'en_core_web_sm' is not installed; install it with python -m spacy download en_core_web_sm`. That
second string is from the source, not from a run — spaCy is not installed on the measurement host.
**Install:** `python -m spacy download en_core_web_sm`, staged into your image; nothing in
`acronymkit` will fetch it.

**NLTK installed, tagger data missing.** This is the common air-gap case and the one people expect
to hang. It does not. `load_tagger("eng")` raises `BackendUnavailable`:

```
NLTK tagger data for 'eng' is unavailable; download it with: python -m nltk.downloader averaged_perceptron_tagger
```

**Install:** stage `averaged_perceptron_tagger` into the image and point `NLTK_DATA` at it. The
`wordnet` corpus is optional on top of that — without it the backend still works and simply leaves
`Token.lemma` unset.

**CLI without `click`.** The console script ships with the base package and refuses to run:

```
This command needs the CLI extra: pip install acronymkit[cli]
(quote the extra for zsh/fish: pip install 'acronymkit[cli]')
```

Exit status 2. **Install:** `pip install 'acronymkit[cli]'`.

**Schema validation without `jsonschema`.** `load_schema()` still works and returns the document;
only `validate_result()` refuses, with `acronymkit.exceptions.AcronymKitError`:

```
Schema validation requires the 'jsonschema' package, which is an optional development dependency.
Install it with: pip install 'acronymkit[dev]' (or: pip install jsonschema).
```

**Install:** `pip install jsonschema`.

**Neural tier under strict offline mode.** `Config(engine_tier=EngineTier.NEURAL, offline=True)`
raises `acronymkit.exceptions.OfflineError` at construction rather than at first use, and carries
`.reason` and `.remedy` separately for a caller that wants to render them:

```
Strict offline mode cannot be honoured: engine_tier=NEURAL requires a model this package does not
ship and will not fetch Use EngineTier.ZERO_DEPENDENCY, which runs entirely from the wheel, or
EngineTier.STATISTICAL_NLP if spaCy or NLTK is installed locally.
```

**Install:** nothing — Tier 2 is not implemented in this release. Use `ZERO_DEPENDENCY`, or
`STATISTICAL_NLP` if you have staged a Tier 1 backend.

**A missing language resource is a warning, not an error.** Generating in French, Spanish or German
succeeds and reports what it lost:

```
no bundled lexicon for language 'fr': Lambda(A) is always 0, so no candidate can be reported as a
dictionary word. Supply one with Config(lexicon_path=...); see tools/build_lexicons.py.
no bundled n-gram model for language 'fr': Phi(A) is uniform, so pronounceability cannot
discriminate between candidates.
```

**Install:** nothing off an index — the permissive sources do not exist. Build your own word list
with `tools/build_lexicons.py` and pass `Config(lexicon_path=...)`; the licence of a dictionary that
stays on your machine is your call. D-006 in [docs/DECISIONS.md](DECISIONS.md) records why no
French, Spanish or German word list ships.

## Measurement environment

Everything on this page was produced against the working tree carrying `acronymkit` 0.2.0, on
Windows 11 Pro (26200), CPython 3.13.4, `pydantic` 2.11.7 / `pydantic-core` 2.33.2, `nltk` 3.9.1
with no tagger corpus present, and **no spaCy installed**. The full suite passes there with **10
skips**, and passes identically under `tests/airgap_socket_guard.py` with every socket primitive
patched to raise. The 10 is the number worth reading: those skips are exactly the Tier 1
real-backend tests, a direct consequence of the host having no usable Tier 1 runtime. The *total*
is deliberately not quoted here — it moved three times while this page was being written, so on an
unpinned tree it is a timestamp rather than a fact. See
[docs/SUPPORT_MATRIX.md](SUPPORT_MATRIX.md) for which cells the 10 skips leave unmeasured.

Two limits worth carrying into a decision, both stated at greater length in
[OFFLINE.md section 9](OFFLINE.md#9-what-is-not-proven): no commit SHA or artifact hash is pinned to
these claims, so restate them against a named revision before relying on them; and the CI network
namespace runs on Linux only, because `unshare -n` has no Windows or macOS equivalent.
