# acronymkit offline and air-gap review

This document is written for someone who has to decide whether `acronymkit` may be installed on a
network-restricted host. It states what was measured, how, and what the measurements cannot see.

Every figure below was produced on the measurement host described in
[Measurement environment](#measurement-environment), against the working tree that carries
`acronymkit` 0.2.0. Nothing here is quoted from a README.

## 1. The one-paragraph answer

`acronymkit` runs entirely from the wheel with no network access: Tier 0 (zero-dependency) and Tier 1
(statistical NLP, when a backend is already installed) generate, extract, score and disambiguate using
eight files that ship inside the distribution, and the JSON Schema used for interchange validation is
one of the eight, read from that bundle rather than from the filesystem. Nothing downloads a model,
phones home, or reads a user's home directory. What does *not* work offline is the neural tier, which is not
implemented and which strict offline mode refuses at construction rather than at first use; and Tier 1
on a host where NLTK or spaCy is installed but its data files are not — that case fails loudly with a
typed error in under a millisecond and never attempts a fetch. The package itself contains no
network-reachable code path; it inherits two from its environment, one of which is now closed in code
(a schema-loading hijack) and one of which can only be detected, not prevented, from inside the process
(`pydantic`'s entry-point plugin loader — close it with `PYDANTIC_DISABLE_PLUGINS=1`). The claim is a
build gate rather than a promise: the `air-gap` job in CI installs from a local wheelhouse with no
index, runs the whole suite with every socket primitive patched to raise, and then drives the entire
public API and the CLI subcommands the probe drives — `13` of the `16` the CLI declares. `normalize-name`, `governed-batch` and `governed-audit` are **not** driven, and all three are on the governed half this library now leads with; the sentence used to say *every* subcommand, inside a routeless network namespace, with a positive control that
fails the job if the namespace is not really empty. To verify it yourself in about twenty minutes, read
that job and run the four commands in [section 8](#8-how-to-verify-it-yourself) — the shortest are
`PYTHONPATH=tests python -m pytest -p airgap_socket_guard -v` and `acronymkit doctor --offline`, which
exits non-zero if this particular installation is not air-gap ready.

## Measurement environment

| | |
|---|---|
| Host | Windows 11 Pro (26200), `sys.platform == "win32"` |
| Interpreter | CPython 3.13.4 |
| `acronymkit` | 0.2.0, source checkout (`src/` layout) |
| `pydantic` / `pydantic-core` | 2.11.7 / 2.33.2 |
| `typing-extensions` / `annotated-types` / `typing-inspection` | 4.16.0 / 0.7.0 / 0.4.1 |
| `nltk` | 3.9.1 (spaCy not installed on this host) |
| `pytest` | 8.4.2 |

Platform matters for two of the findings — the Windows loopback self-pipe in section 2 and the PE
import table in section 3 — and both are called out where they apply.

## 2. The headline number

**`acronymkit` authors zero network-reachable code paths. It inherits two, both now addressed.**

Three independent methods on the measurement host, each with a positive control, and a fourth that runs
in CI on every push:

**Bytecode scan.** The `27` modules under `src/acronymkit/` that existed when this scan was run were compiled and every code object
reached from each module — 573 in total, including nested functions, comprehensions and class bodies —
had its `co_names`, `co_varnames`, `co_freevars` and string constants intersected with a set of 42
network primitives (the stdlib socket/ssl/select/asyncio/http/urllib/ftplib/smtplib/poplib/imaplib/
nntplib/telnetlib/xmlrpc/socketserver/webbrowser families, the third-party clients `requests`, `httpx`,
`aiohttp`, `urllib3`, `certifi`, `pycurl`, `huggingface_hub`, and the callables `urlopen`,
`socketpair`, `create_connection`, `getaddrinfo`, `gethostbyname`, `connect`, `sendall`,
`urlretrieve`). **Three hits, all the same name:**

| Module | Code object | Name |
|---|---|---|
| `batch.py` | `arun_batch` | `asyncio` |
| `batch.py` | `_run` | `asyncio` |
| `engine.py` | `agenerate` | `asyncio` |

Those are the async wrappers. The same scan over a set of subprocess primitives (`subprocess`,
`Popen`, `os.system`, `popen`, `execv`, `execve`, `spawnv`, `fork`) returned **zero** hits. The
original audit scanned 26 modules against 40 primitives; `diagnostics.py` has been added since, so this
scan was re-run over the current tree rather than carried forward — which is what section 9 asks for on
every release.

**Runtime audit hooks.** A `sys.addaudithook` harness recorded every `socket.*`, `urllib.Request`,
`http.client.*`, `ftplib.*`, `smtplib.*`, `imaplib.*`, `poplib.*`, `nntplib.*`, `telnetlib.*` and
`webbrowser.open` event while **53 public-API steps** were driven: every method on `AcronymEngine`
(generate, score, tokenize, extract, extract_definitions, generate_backronym, synthesize_backronym,
batch_generate, disambiguate, agenerate, abatch_generate), every `EngineTier`, every `Language`, every
`ScoringStrategy`, the whole of `serialization`, `batch`, `phonetics`, `stopwords`, `lexicon`,
`resources` and `diagnostics`, and four CLI commands including `doctor --offline`. Before the drive,
the harness performed real positive controls — it opened a socket, wrote a file and spawned a
subprocess — and asserted that each was recorded; a hook that does not fire cannot produce evidence.

**Eight socket events were recorded, all of them loopback, all of them inside two steps:**

```
socket.__new__  during agenerate         (AF_INET, SOCK_STREAM)
socket.bind     during agenerate         ('127.0.0.1', 0)
socket.__new__  during agenerate
socket.connect  during agenerate         ('127.0.0.1', 51137)
socket.__new__  during abatch_generate
socket.bind     during abatch_generate   ('127.0.0.1', 0)
socket.__new__  during abatch_generate
socket.connect  during abatch_generate   ('127.0.0.1', 51139)
```

This is CPython's own `socket._fallback_socketpair`, used by `asyncio`'s `ProactorEventLoop` to build
its self-pipe. Windows has no `socketpair(2)`, so CPython synthesises one from a TCP pair on
`127.0.0.1`. On Linux and macOS the same call reaches `AF_UNIX` and no INET socket appears at all. No
`acronymkit` frame appears on the stack of any of these events; the only reason they occur is that the
two async wrappers start an event loop.

**Full suite under a socket guard.** `tests/airgap_socket_guard.py` replaces the standard library's
network entry points with functions that raise, and is loaded with `-p` so the patches are in place
before conftest import and before collection — which is where a package that phones home at import
time would be caught, and which is precisely the window `pytest-socket` leaves open (it patches in
`pytest_runtest_setup`; it also requires Python 3.10+, colliding with this project's 3.9 CI cells).
On the measurement host:

```
3391 passed, 10 skipped in 26.61s
```

The guard runs its positive control in `pytest_configure` on every session and reports it in the pytest
run header, so the evidence lands in the log rather than in a comment. One wrinkle worth stating,
because it looks like a failure and is not: `addopts` in `pyproject.toml` carries `-q`, and pytest
prints no run header below verbosity 0 — so the block below appears only when `-v` is added to the
command. The control itself runs either way and aborts the session if any probe is not blocked; `-v`
decides only whether you get to read the result. The CI job does not rely on the header at all: it runs
`python tests/airgap_socket_guard.py` as its own step, which performs the same probes and prints the
same lines followed by `air-gap socket guard: positive control passed`. From
`PYTHONPATH=tests python -m pytest -p airgap_socket_guard -v`:

```
air-gap socket guard: active
  socket.socket.connect() on a real AF_INET descriptor: blocked
  socket.socket(AF_INET, SOCK_STREAM): blocked
  socket.create_connection(): blocked
  ssl.SSLContext.wrap_socket(): blocked
  http.client.HTTPConnection.connect(): blocked
  socket.getaddrinfo(): blocked
  socket.gethostbyname(): blocked
  socket.gethostbyname_ex(): blocked
  socket.gethostbyaddr(): blocked
  socket.getnameinfo(): blocked
  socket.socketpair() (documented exemption, family=AF_INET): allowed
```

That transcript is copied from a run rather than described, and the probe set is expected to grow —
the four `gethostby*`/`getnameinfo` lines were added to the guard after this section was first drafted.
So compare the shape, not the line count: every probe must say `blocked` except the one documented
exemption. A list that has got *shorter* is the finding.

The one exemption is the Windows self-pipe described above, narrowed to frames belonging to CPython's
own `socketpair` code object, with loopback as the only reachable address.

**In CI, on every push.** The `air-gap` job in `.github/workflows/ci.yml` ("No network, and a build
that fails if that changes") runs three mechanisms that do not subsume one another: an install from a
local wheelhouse with `--no-index`, so the artifact is proven usable by someone who has no package
index; the full suite under the guard above; and the whole public API plus the CLI subcommands the probe drives — `13` of the `16` the CLI declares. `normalize-name`, `governed-batch` and `governed-audit` are **not** driven, and all three are on the governed half this library now leads with; the sentence used to say *every* subcommand, inside
`unshare -n`, a real network namespace with no route, running unprivileged with `HOME=/nonexistent`.
The namespace step is the one that closes the audit-hook gap described below, because it blocks a C
extension that opens a socket without asking Python first. The job also runs its own positive control
before anything depends on it: it connects to `pypi.org:443` outside the namespace and asserts the same
connection fails inside it, so a runner where `unshare` silently did nothing cannot turn the later
steps into a tautology.

### What these methods cannot see

Stated plainly, because a claim whose limits are hidden is worth less than a smaller claim whose limits
are not.

- **The bytecode scan matches names, not behaviour.** Code that assembles a module name at runtime —
  `getattr(__import__("so" + "cket"), "socket")` — would not appear in `co_names` as a network
  primitive. It is evidence that nothing was written normally, not proof that nothing could be written
  abnormally. It also stops at the Python boundary: it says nothing about compiled extensions.
- **Audit hooks observe CPython, not the operating system.** A C extension that calls `connect(2)`
  directly, without going through CPython's socket module, raises no audit event. `pydantic-core` is
  such an extension, which is why its import table was parsed separately (section 3) and why the
  `air-gap` CI job also runs the public API inside a routeless network namespace, where a syscall that
  bypasses Python surfaces as `ENETUNREACH` rather than as a quiet success. That namespace step runs on
  Linux only; the measurements in this document were taken on Windows, where the equivalent evidence is
  the PE import table.
- **The suite measures the paths the suite drives.** 3,391 tests is a large sample of behaviour, not a
  proof over all inputs. A path reachable only by an input no test supplies is outside it.
- **None of this describes what an operator installs alongside the package.** That is the subject of
  sections 3 and 4.

## 3. The dependency tree

The base runtime requirement closure, computed from installed distribution metadata with environment
markers evaluated and no extras selected, is **exactly five packages**:

```
acronymkit 0.2.0
├── pydantic 2.11.7
│   ├── annotated-types 0.7.0
│   ├── pydantic-core 2.33.2
│   │   └── typing-extensions
│   ├── typing-inspection 0.4.1
│   │   └── typing-extensions
│   └── typing-extensions
└── typing-extensions 4.16.0
```

`certifi`, `requests`, `urllib3`, `huggingface_hub` and `email-validator` are **not** in that closure.
In a freshly created virtual environment (`python -m venv`, pip 25.1.1, no packages installed),
`certifi`, `requests`, `urllib3` and `truststore` exist only as `pip/_vendor/certifi`,
`pip/_vendor/requests`, `pip/_vendor/urllib3` and `pip/_vendor/truststore` — they are pip's own
bootstrap, not a dependency of anything here. `huggingface_hub` is absent from the venv entirely. The
only two top-level entries in a fresh venv's `site-packages` are `pip` and `pip-25.1.1.dist-info`.

Each package was then imported alone, in a fresh interpreter, under an audit hook:

| Package | Network I/O at import | Network I/O at first use | Any reachable network path | Notes |
|---|---|---|---|---|
| `acronymkit` | none; loads no network module at all | none | none | `import acronymkit` binds no submodule (PEP 562 lazy re-exports), so it does not even pull in `pydantic` |
| `pydantic` | none | none | none reached from here | loads `_socket` transitively via `typing_extensions`; see below |
| `pydantic-core` | none | none | none | compiled extension; import table parsed below |
| `annotated-types` | none | none | none | loads `_socket` transitively via `typing_extensions` |
| `typing-inspection` | none | none | none | |
| `typing-extensions` | none | none | none | **causes `import _socket`**; see below |

Zero socket audit events fired during any of those imports.

**The compiled extension links no networking DLL.** `_pydantic_core.cp313-win_amd64.pyd` (5,309,440 B)
was parsed at the PE level — `e_lfanew` → optional header → data directory entry 1 → import directory —
and its import table names exactly eleven DLLs:

```
ADVAPI32.dll   api-ms-win-core-synch-l1-2-0.dll   api-ms-win-crt-heap-l1-1-0.dll
api-ms-win-crt-math-l1-1-0.dll   api-ms-win-crt-runtime-l1-1-0.dll
bcrypt.dll   bcryptprimitives.dll   KERNEL32.dll   ntdll.dll
python313.dll   VCRUNTIME140.dll
```

None of `ws2_32`, `wsock32`, `mswsock`, `winhttp`, `wininet`, `dnsapi`, `iphlpapi` or `secur32` is
present. Winsock is how socket I/O is performed on Windows, and this binary does not link it. The
honest caveat: `ntdll.dll` is the native syscall surface, so this is evidence that the extension does
no ordinary networking, not a proof that no syscall path exists. `bcrypt`/`bcryptprimitives` are the
Windows cryptographic primitives library — hashing and RNG, not TLS transport.

**`typing_extensions` causes CPython to import `_socket`, and no socket is ever created.** Traced to
the line:

```
typing_extensions.py:4017   _CapsuleType = getattr(_types, "CapsuleType", None)
  → Lib/types.py:336        import _socket
```

CPython's `types` module derives `CapsuleType` from `_socket.CAPI`, which happens to be a convenient
PyCapsule object. The module is imported for type introspection. Zero socket audit events fire. This
matters operationally: **a naive attestation of the form "this process never loads `_socket`" will
fail on any process that imports `pydantic`**, and it will fail for a reason that has nothing to do
with networking. Attest on socket *creation* or on connect events, not on module presence.

### Three things in `pydantic` a reviewer will find and ask about

| Finding | Location (pydantic 2.11.7) | Verdict |
|---|---|---|
| Email deliverability check (a DNS lookup) | `networks.py:1300`, `v1/networks.py:731`, `v1/_hypothesis_plugin.py:62` | Every call site passes `check_deliverability=False` literally. It is not configurable from outside and there is no fourth call site. `email-validator` is also not installed — it is pydantic's `email` extra, and nothing here selects it. |
| `git` subprocess | `_internal/_git.py` (`is_git_repo`, `have_git`, `git_revision`) | Referenced from exactly one module, `version.py`, and the import sits *inside* the body of `version_info()` (line 30 of a function beginning at line 21). `acronymkit` never calls `version_info()`; the bytecode scan found no subprocess names, and the 53-step drive produced zero `subprocess`/`exec`/`fork` audit events. |
| `pickle.loads` | `deprecated/parse.py:54`, `v1/parse.py:42` | The only two occurrences in the distribution, both in the deprecated/v1 parse API. `src/acronymkit/` imports no `pickle` and calls none of `parse_raw`, `parse_obj` or `parse_file`; the word appears in its Python sources only twice, in a comment and a docstring in `nlp/nltk_backend.py` explaining why a corrupt NLTK tagger pickle is caught rather than raised. Unreachable by default and never called here. |

### The extras, because a security team reads the metadata and not the code

The base install is the five packages above. `pyproject.toml` declares five extras; `all` and `dev` are
unions of the others, and the three that add anything are:

```
[cli]           click>=8.0.0
[nlp]           spacy>=3.5.0, nltk>=3.8.0
[transformers]  onnxruntime>=1.14.0, transformers>=4.25.0
```

`[cli]` is the small one and the one a reviewer will need: the `acronymkit` console script is declared
by the base package but every entry point routes through an import guard, so without `click` the
command exists and refuses to run. Its closure here is two distributions — `click` 8.1.8 and
`colorama` 0.4.6, the latter only because `colorama` carries a `platform_system == "Windows"` marker —
and neither carries an HTTP client. Section 8 assumes it is installed; `acronymkit.capabilities()` is
the same report with no extra at all.

Resolved from installed metadata on the measurement host, `[transformers]` reaches **26
distributions**, of which eight are a working HTTP stack: `requests`, `urllib3`, `certifi`, `idna`,
`charset-normalizer`, `huggingface-hub`, `fsspec`, `filelock`. `huggingface-hub` is a model downloader
by design. `[nlp]` could not be fully resolved here because spaCy is not installed on this host; NLTK's
own closure is six distributions (`nltk`, `click`, `colorama`, `joblib`, `regex`, `tqdm`) and contains
no HTTP client, so whatever HTTP surface `[nlp]` has arrives with spaCy. The offline audit that
motivated this document recorded 44 packages for `[nlp]` and 30 for `[transformers]`; those two counts
were **not** re-derived here, and a resolved closure depends on the index snapshot, the platform and
the Python version, so re-derive them for your own environment with:

```
pip install --dry-run --report - "acronymkit[nlp]"
pip install --dry-run --report - "acronymkit[transformers]"
```

No extra is required. Tier 0 is the default and needs none of them. If your policy is that no HTTP
client may be present in the image, install `acronymkit` with no extras — or with `[cli]`, which adds
none — and the policy holds.

`nltk` also reads the user's home directory at import: `nltk.data` reads `NLTK_DATA` and, on Windows,
`APPDATA` and `USERPROFILE`, and seeds `nltk.data.path` with a home-relative directory. That is NLTK's
behaviour, not this package's — `acronymkit` reads no home directory (section 6) — but it is visible in
a syscall trace and is worth knowing before someone reports it.

## 4. The two inherited paths

Both are real. Hiding either would make the rest of this document less credible, not more.

### (a) The `pydantic` entry-point plugin loader

`pydantic` scans the `pydantic` entry-point group and imports whatever is advertised there, on the path
that builds any model. For this library, that is the path that builds a `Config` — which is to say, the
first thing that happens when anyone uses the package. The imported code runs before any `acronymkit`
code does, and it can do anything an import can do.

This was demonstrated twice by execution during the audit: a planted plugin was imported during
`Config()` construction and opened an outbound socket. It is now a regression test —
`tests/test_offline.py::test_offline_refuses_to_run_beside_a_third_party_pydantic_plugin` plants a real
`.dist-info` directory on a fresh interpreter's `sys.path`, because `pydantic` reads distribution
metadata and caches the result on the first model build, so anything planted inside a running test
session would be discovered too late to be faithful. The planted plugin is deliberately well-formed:
the interesting case is foreign code that imports cleanly and works.

**The mitigation is `PYDANTIC_DISABLE_PLUGINS=1` in the environment.** That is prevention.

**What `acronymkit` does is detection, and the difference is the whole point.** With strict offline
mode on — `Config(offline=True)` or `ACRONYMKIT_OFFLINE=1` — `Config.__init__` calls
`_enforce_offline`, which raises `OfflineError` when `acronymkit.diagnostics.pydantic_plugins()` is
non-empty. But by the time that check runs, `pydantic` has already imported the plugin: importing it is
part of what building the model *does*. Refusing at that point stops the process from continuing under
a promise that has already been broken. It does not un-break it. `acronymkit doctor --offline` reports
the same finding and exits 1, which is the form an enterprise's own CI can assert on.

The library does not set `PYDANTIC_DISABLE_PLUGINS` for you, because doing so from inside the process
would mutate global state shared with every other `pydantic` user in it, to solve a problem those users
may not have.

`ACRONYMKIT_OFFLINE` can only tighten. A truthy value turns offline mode on for every `Config` in the
process, and there is deliberately no value that turns it off — a container-wide setting that could
silently relax a security posture would be a worse defect than the one it solves.

### (b) `load_schema()` preferring an unowned `schemas/` directory

`acronymkit.serialization.load_schema()` used to search the filesystem before falling back to its own
bundled copy: `<repo>/schemas/`, and the same directory relative to two ancestors of the package
directory. In an installed wheel those ancestors are `<site-packages>/schemas/` and
`<venv>/Lib/schemas/` — paths this package does not own and that carry no `RECORD` hash.

`schemas` is a real, installable name on PyPI. Claiming that directory does not require write access to
the machine; it requires one line in a requirements file.

The audit demonstrated the full chain by execution. A planted document was returned by `load_schema()`
in preference to the bundled one; because a JSON Schema may carry a remote `$ref` and `jsonschema`
resolves remote refs by fetching them, validation issued a real outbound HTTP GET to a host of the
planter's choosing — turning a library with no network code of its own into one that makes a request —
while `validate_result()` reported the attacker's document as valid.

**Fixed, in two places.** The filesystem search is gone: the schema is read from the bundled
`acronymkit.resources` data file and nowhere else, in a checkout, a wheel and an sdist identically.
That file is hashed in the wheel's `RECORD` like every other shipped file. `SCHEMA_PATH` still names
the checkout copy, because the cross-language `acronym4j` port and the repository tooling need to point
at it, but nothing in the load path consults it. Separately, `validate_result()` walks the decoded
schema with `_remote_refs()` and raises `AcronymKitError` if any `$ref` names an `http`, `https`, `ftp`,
`ftps` or `file` scheme — because "our schema happens to contain no remote reference today" is a
property of today's file, and that function is the line where such an accident would become a socket.

Two checks keep it honest, both in CI. The `resources` job compares the SHA-256 of
`schemas/acronym-engine-result.schema.json` against the bundled copy and fails if they have diverged.
The `test` job covers `_remote_refs()` directly — `tests/test_serialization.py` asserts that every
fetchable scheme is flagged, at any dictionary depth, inside lists, and that every hit is reported
rather than only the first.

One thing a reviewer will notice and should not be alarmed by: the schema *does* contain two `https`
URLs, in `$schema` (`https://json-schema.org/draft/2020-12/schema`) and `$id`
(`https://raw.githubusercontent.com/.../acronym-engine-result.schema.json`). Neither is a `$ref`.
`$schema` names a meta-schema that `jsonschema` ships internally, and `$id` is a base URI, not a fetch
instruction. Measured, with every socket primitive patched to raise: `load_schema()` followed by
`validate_result()` on a generated payload completes normally.

## 5. The optional backends: NLTK does not download

The common assumption — that installing NLTK means a machine will try to fetch corpora — is **wrong**,
and it matters because it is the usual reason an air-gapped deployment is told Tier 1 is impossible.

Measured on the host above, with `nltk` 3.9.1 installed and `nltk.data.path` pointed at an empty
directory so no corpus is reachable:

| Call | Outcome | Time | Network events |
|---|---|---|---|
| `nltk.pos_tag(["hello", "world"])` | raises `LookupError` | 0.28–0.49 ms over five runs | 0 |
| `NltkBackend().is_available()` | returns `False` | 0.50 ms | 0 |
| `AcronymEngine(Config(engine_tier=STATISTICAL_NLP))` | raises `TierUnavailableError` | — | 0 |

The error message is `Engine tier statistical_nlp is unavailable. Install it with: pip install
'acronymkit[nlp]'`.

NLTK raises rather than fetching because `nltk.download()` is a function a caller invokes, not
something `pos_tag` falls back to. `acronymkit` catches the `LookupError` and converts it to a typed
`TierUnavailableError`; `is_available()` answers `False` and the engine either degrades to Tier 0 or
refuses, according to `Config.strict` and the requested tier. spaCy behaves the same way — a missing
model raises `OSError` E050 and calls no downloader — though spaCy is not installed on the measurement
host, so that figure is the audit's and not re-derived here.

**What this means for an air-gapped install.** You may install `acronymkit[nlp]` into an image with no
corpora and the process will not hang, will not retry, and will not reach for a network it does not
have. Tier 1 degrades loudly, in under a millisecond, with a message naming the remedy — which is the
behaviour you want, and it is strictly better than the alternative of a Tier 1 that silently succeeds
because something downloaded a model at 3 a.m. If you do want Tier 1, ship the corpora in the image;
nothing in `acronymkit` will fetch them for you.

## 6. Filesystem and environment

The first five rows were measured across the same 53-step drive of the public API described in
section 2, under deny-all-writes and process-spawn audit hooks. The last three are source scans over
all 27 modules.

| Property | Measurement | How |
|---|---|---|
| Write-mode `open()` calls | **0** | audit hook on `open`, any of `w`, `a`, `x`, `+` in the mode |
| `tempfile.mkstemp` events | **0** | audit hook |
| `subprocess` / `exec` / `fork` events | **0** | audit hook |
| `os.environ` reads attributable to `acronymkit` | **2**, both in `diagnostics.py` | stack attribution, below |
| Home-directory reads (`HOME`, `USERPROFILE`, `HOMEDRIVE`, `XDG_*`, `APPDATA`) by `acronymkit` | **0** | stack attribution + patched `os.path.expanduser` |
| `pickle` use | none in `src/acronymkit/` | source scan |
| `hashlib.md5` use | none anywhere; SHA-256 only | source scan |
| Text I/O sites without an explicit codec | **0 of 9** | AST scan, below |

**The two environment variables.** `os.environ` reads were attributed by walking the calling stack to
the first frame outside `os` and the harness, and grouped by module:

```
acronymkit    ACRONYMKIT_OFFLINE, PYDANTIC_DISABLE_PLUGINS
asyncio       PYTHONASYNCIODEBUG
click         _ACRONYMKIT_COMPLETE
gettext       LANG, LANGUAGE, LC_ALL, LC_MESSAGES
pydantic      PYDANTIC_DISABLE_PLUGINS, PYDANTIC_VALIDATE_CORE_SCHEMAS
sysconfig     APPDATA, PYTHONUSERBASE, _PYTHON_PROJECT_BASE
zoneinfo      PYTHONTZPATH
```

`ACRONYMKIT_OFFLINE` is the package's own switch and can only tighten (section 4a).
`PYDANTIC_DISABLE_PLUGINS` is read but never written: `diagnostics.pydantic_plugins()` checks it so it
can report `()` when the plugin mechanism is already switched off, rather than misreport a machine that
is already safe. Note that the `APPDATA` read in that list belongs to `sysconfig`, not to this package.

**Writes, stated exactly.** Zero writes occurred on any path the drive touched, but "the library never
writes" would be an absolute with an exception, so here are both exceptions:

- `acronymkit._pseudo_precision.PrecisionTable.save(path)` writes JSON to a path its caller supplies.
  It is a calibration-table helper: nothing in `src/acronymkit/` calls it, and the module it lives in
  is named only twice, both times in prose (`_strategies.py` lines 9 and 328 — a module docstring and a
  comment). It is not reachable from `AcronymEngine`.
- `acronymkit.resources.resource_path()` calls `importlib.resources.as_file`, which materialises a
  temporary file when the package is loaded from a zip. Calling it over every bundled resource on an
  ordinary unzipped install produced **0** temp-file and **0** write events; it returned the real
  resource path each time. The traced run covered the seven resources that existed when this section
  was written; re-checked over all eight, every call still returns the path inside
  `acronymkit/resources/`. The temporary files, if a zip install ever creates them, are released by an
  `atexit`-registered `ExitStack`.

Nothing in the library chooses a write location for itself, and nothing writes on import, extraction or
generation.

**Locale.** All nine text I/O call sites in `src/acronymkit/` pass an explicit `encoding=` (verified by
walking the AST of all 27 modules for `open`, `read_text`, `write_text`, `TextIOWrapper`, `encode` and
`decode` calls). The 53-step drive was additionally run under `python -X warn_default_encoding` with
`EncodingWarning` promoted to an error, and no step raised one. `LANG=C` is survivable.

**FIPS.** `hashlib.md5` raises on a FIPS-enabled host, and a checksum routine is exactly where that
lands if it is going to. The digest routine in `diagnostics.py` uses SHA-256, and MD5 appears nowhere
in the package.

## 7. Every bundled resource

Eight files, and nothing else, ship inside `acronymkit/resources/`. The count is
`len(acronymkit.resources.bundled_resources())`, and the digests below are from
`acronymkit.capabilities()["resources"]["digests"]` on this working tree — the same values
`acronymkit doctor` prints, so a reviewer can compare their own installation against this table
directly. Both columns are quoted as literals from that report rather than written as prose figures,
because they are properties of the shipped files and not measurements of the library. If the two ever
disagree, the report is right and this table is stale: it is generated by nothing, and until this
round it listed seven.

| Resource | Bytes | SHA-256 | Licence | Provenance |
|---|---:|---|---|---|
| `acronym-engine-result.schema.json` | `6,408` | `9a8823ce1a4c8f2041d3e03e748ee5e4f1196de3b2fe10e1df86625b713425cf` | MIT (this project) | Authored here. Byte-identical to `schemas/acronym-engine-result.schema.json`; CI fails if the two diverge. |
| `lexicon_en.txt` | `730,496` | `919f9f1ca9485c19ffe800fcaf554ca367b999ad0f71862ab8a578a1b4a8a07b` | SCOWL (MIT-equivalent permissive) | Derived from `scowl-2020.12.07.tar.gz` (SHA-256 `5587667c…59cc`), size cut ≤ 60, categories english-words and american-words. Copyright 2000–2018 Kevin Atkinson; the notice is reproduced in the file header. |
| `ngram_en.json` | `14,357` | `1261292c01c6075745b65dd5cde3dedecc54f306955573860429ea245f2ac42b` | MIT (this project), model fitted on SCOWL-derived data | Generated from `lexicon_en.txt` by `tools/build_ngram_model.py`. CI re-trains and fails on drift. |
| `pseudo_precision_en.json` | `34,096` | `3768195b57a6da9226abf2f7eb4251e6647f97731ed056e923f234dae916a4fd` | MIT (this project), table fitted on public-domain corpus text | Generated by `tools/build_reliability_table.py` from the **raw text** of MED1250's development half (public domain, United States Government work; the NLM attribution and the full ledger entry are in `data/LICENSES.md`). The estimator opens no annotation and the file reproduces no source text: every key is one of this library's own group or strategy labels and every value is a count or a float. Its own `_provenance` block records the source URL, digest, licence and split seed; `tools/build_reliability_table.py --check` rebuilds and fails on drift. |
| `stopwords_en.json` | `6,650` | `ca409a6d81bdd36d598e27153e2d0a3da0bd656a8eff309e5f3b45617416e2dd` | MIT (this project) | Hand-authored categorised function-word list. Format validated by `tools/validate_resources.py`. |
| `stopwords_de.json` | `8,089` | `7a637cf007c3715141fb7a54baf0cdeaceeba701e2e15ee96ed423ca4db700b4` | MIT (this project) | As above, German (includes preposition-article contractions). |
| `stopwords_es.json` | `5,884` | `00466dfb3027d0025b083b88a07c264906d3d1c272a64a7b35daf00c0f108acc` | MIT (this project) | As above, Spanish (includes `al`, `del`). |
| `stopwords_fr.json` | `5,255` | `9e3beb7b688cf5cfc38278d94f9f9a12ed7553be8c99ae852eb87cd3034fc9ca` | MIT (this project) | As above, French (includes elided forms). |

Three things the table implies, stated rather than left to be inferred:

- **Only English ships a lexicon, an n-gram model and a reliability table.** The French, Spanish and
  German Hunspell dictionaries used during development are copyleft, are marked fetch-only in
  `data/LICENSES.md`, are git-ignored, and are not in the distribution. `tools/build_lexicons.py`
  refuses to vendor anything marked fetch-only, so the split is enforced by code rather than by
  diligence. The three English-only files are also the three derived ones: every other resource is
  hand-authored here.
- **Two of the eight carry an outside licence obligation, and it is attribution rather than
  distribution.** `lexicon_en.txt` and `ngram_en.json` descend from SCOWL; `pseudo_precision_en.json`
  descends from a public-domain corpus and so carries none, and its row states the attribution anyway.
  Nothing here is copyleft and nothing here is redistribution-restricted, which is the question an
  enterprise reviewer is actually asking.
- **Nothing in the distribution is downloaded at runtime, and no resource is fetched on demand.** The
  eight files above are the complete data surface. `data/LICENSES.md` is the full asset ledger,
  including the evaluation corpora (MED1250, PLOD-CW, SDU@AAAI-21) that `tools/fetch_data.py`
  downloads for benchmarking only — that tool is a maintainer script, is not importable from the
  package, is not in the wheel, and verifies every download against a SHA-256 recorded in the source.

For completeness, the 0.2.0 wheel as built (`dist/acronymkit-0.2.0-py3-none-any.whl`): 392,142 B on
disk, 40 entries, 1,313,251 B uncompressed, 386,800 B of compressed payload, of which `lexicon_en.txt`
is 205,920 B — 53.2 % of the compressed total. **That artifact predates the eighth resource**: it was
recorded one commit before `pseudo_precision_en.json` was added, so its entry count and every byte
total on this line are below what this tree builds today, and it is left as recorded rather than
refreshed by hand. See section 9 on why an artifact figure has to be re-derived per release, and
[docs/SUPPORT_MATRIX.md](SUPPORT_MATRIX.md#bundled-resources-as-the-report-lists-them) for a wheel
measured after the addition.

## 8. How to verify it yourself

Start by reading one CI job, then run four commands. On the measurement host the first three commands
take well under a minute each; the fourth is the slow one and is still a few minutes. Twenty minutes of
a security engineer's time is the target, most of it spent reading rather than waiting.

**0. Read the `air-gap` job.** In `.github/workflows/ci.yml`, job id `air-gap`, display name *"No
network, and a build that fails if that changes"*. It runs on every push and pull request against
`main`. Read its comments before its commands: they state which of the three mechanisms covers which
hole, and why none of them is redundant. Its first step is a positive control for the harness itself.

**1. Run the entire test suite with every socket primitive raising.**

```
PYTHONPATH=tests python -m pytest -p airgap_socket_guard -v
```

`-p` is load-bearing: it makes the guard the first plugin loaded, so the patches are in place before
`conftest.py` is imported and before collection begins. `-v` is load-bearing for a different reason:
this project's `addopts` is `-q`, pytest prints no run header below verbosity 0, and the guard reports
itself in that header — so without `-v` the control runs and its result is never shown. Expect a green
run — `3391 passed, 10 skipped` on the tree this document was written against — and an `air-gap socket
guard: active` block in the header listing each blocked primitive. If that block is absent from a `-v`
run, the guard did not load and the green result means nothing. The count is what matters least here:
check the header, then check that nothing failed.

**2. Run the guard's positive control on its own.**

```
python tests/airgap_socket_guard.py
```

This makes real outbound attempts — including a `connect` to RFC 5737 TEST-NET-1 through CPython's own
unpatched socket constructor — and fails if any of them is *not* blocked. A guard with no positive
control is worse than no guard, because a typo in a patch name yields a green suite that reads as
evidence.

**3. Ask this specific installation whether it is air-gap ready.**

```
acronymkit doctor --offline
acronymkit doctor --format json | jq .resources.digests
```

`doctor --offline` exits **1** when something in this environment could make the process reach the
network — today that means installed third-party `pydantic` entry-point plugins — and **0** otherwise.
The JSON form is the shape to assert on in your own CI: `.network.performs_network_io`,
`.network.third_party_import_hooks.pydantic_entry_point_plugins`, `.tiers`, and
`.resources.digests`, which you can diff against section 7 of this document. Both commands need the
`[cli]` extra: the console script ships with the base package but refuses to run without `click`
(section 3). The same report is available in-process as `acronymkit.capabilities()`, which needs no
extra, imports only the standard library, and therefore still works on an installation that is
otherwise broken.

**4. Install the sdist into a clean environment and run its suite there.**

```
python -m build                                        # produces dist/*.whl and dist/*.tar.gz
mkdir -p /tmp/sdist && tar -xzf dist/*.tar.gz -C /tmp/sdist --strip-components=1
python -m venv /tmp/review
/tmp/review/bin/pip install --no-index --find-links dist "acronymkit[dev]"
cd /tmp/sdist && PYTHONPATH=tests /tmp/review/bin/python -m pytest -p airgap_socket_guard
```

Use the venv's interpreter for the last line, not the system one, or you will test the checkout again
rather than the artifact. `--no-index` will fail unless the dev extras are already staged locally; the
`air-gap` CI job does that with `pip download --dest wheelhouse --only-binary=:all:` while the network
is still up, and then installs with `--find-links=dist --find-links=wheelhouse`. The sdist ships
`tests/`, `schemas/` and `bench/results.json`, which is what makes the shipped documentation's claims
checkable from the shipped artifact rather than only from the repository. This block is written for a
POSIX shell, which is what the `air-gap` job runs; on Windows the venv puts its interpreter in
`Scripts\` rather than `bin/`, and `VAR=value cmd` is not a thing the shell does.

**Optional, if your policy needs it:** set `PYDANTIC_DISABLE_PLUGINS=1` and `ACRONYMKIT_OFFLINE=1` in
the container and confirm that `acronymkit doctor --offline` still exits 0 and that
`Config(engine_tier=EngineTier.NEURAL)` raises `OfflineError` with a `.reason` and a `.remedy`.

## 9. What is not proven

- **No commit SHA or artifact hash is pinned to this claim.** The audit behind this document did not
  pin one, and the measurements above were taken against a working tree, not a tagged release. The
  resource digests in section 7 are a genuine pin for the *data*; the code has no equivalent pin here.
  Before this document is relied upon, restate its claim against a named revision, and re-derive the
  attestation for every release — a dependency bump, a new module, or a new bundled file each changes
  something the sections above assert.
- **`typing_extensions` makes CPython `import _socket`.** A naive attestation of the form "this process
  never loads `_socket`" will fail on any process that imports `pydantic`, even though no socket object
  is ever created and no connect is ever attempted. Attest on socket creation or connect events, not on
  module presence. This is documented in section 3 with the exact source line.
- **The CI job proves it for Linux and one interpreter, not for your platform.** The `air-gap` job runs
  on `ubuntu-latest` with Python 3.12; its network-namespace step has no Windows or macOS equivalent,
  because `unshare -n` has none. The `test` matrix covers Windows and macOS across 3.9–3.13, but
  without the namespace. If you deploy on Windows, the strongest evidence available is the socket guard
  plus the PE import table, both in this document, and neither is as strong as a routeless namespace.
- **The audit hooks and the guard are CPython-level.** They do not observe a compiled extension that
  issues syscalls directly; only the namespace step does, and only on Linux. Section 3 addresses
  `pydantic-core` by parsing its PE import table on Windows. The equivalent for a Linux deployment is
  `readelf -d` / `ldd` on the manylinux `_pydantic_core*.so`, which is **not** measured here — the
  wheel a Linux host installs is a different binary from the one inspected above.
- **The Windows loopback self-pipe is real socket activity.** It is `asyncio`'s, not this package's,
  and it never leaves the machine — but a host-based monitor configured to alert on any AF_INET socket
  will see it whenever `agenerate()` or `abatch_generate()` is called. On Linux and macOS it does not
  occur, because `socketpair` reaches AF_UNIX there.
- **The extras' resolved package counts were not re-derived.** Section 3 gives the audit's figures and
  the command to reproduce them in your own environment; a closure depends on the index snapshot, the
  platform and the interpreter version.
- **spaCy's behaviour was not re-measured here**, because spaCy is not installed on the measurement
  host. The NLTK figures in section 5 are this document's own; the spaCy figure is the audit's.
- **3,391 passing tests is a sample, not a proof.** It covers the paths the suite drives. A path
  reachable only by an input no test supplies is outside every method used above. The count itself
  moved from 3,302 to 3,389 to 3,391 over the days this document was being written and reviewed, which
  is a concrete illustration of
  the first bullet: on an unpinned tree, a test count is a timestamp, not a fact.
