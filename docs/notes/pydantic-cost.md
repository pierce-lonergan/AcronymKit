# What pydantic costs, measured

The claim under test, from the phase-4 mandate:

> a library whose pitch is pure Python, no compiled extension, works anywhere,
> with a heavyweight validation dependency in its critical path, is arguing
> against itself.

**The claim survives the test, but not in the shape it was made.** Three of its
four parts are supported by measurement and one is not:

- *Heavyweight* — yes, and by more than expected. **21.6 %** of
  `from acronymkit import AcronymEngine` is importing `pydantic`, and a further
  **63.0 %** is a single fixed cost paid when the first `BaseModel` subclass in
  the process is built. Together: **84.6 %** of the import belongs to the
  dependency, not to this library.
- *In the critical path* — yes, but the number is smaller than the import
  figure and depends on what the caller asks for: **22.4 %** of a warm
  `generate()`, **29.4 %** of `generate()` followed by `to_dict()`.
- *No compiled extension* — already conceded in the docs, at length.
  `docs/OFFLINE.md` section 3 parses `_pydantic_core.cp313-win_amd64.pyd`
  (5,309,440 B, a figure this note re-measured and agrees with) to show it links
  no networking DLL, and `docs/ENTERPRISE.md` carries a caveat longer than the
  claim it qualifies. `acronymkit`'s own wheel is `py3-none-any`; its dependency
  closure contains native code.
- *Works anywhere* — **this part of the premise is wrong, or at least far
  weaker than it sounds.** `pydantic-core` 2.33.2 publishes 98 wheels across 20
  platform tags, including musl, s390x, ppc64le, armv7l and Windows on ARM.
  Mainstream targets get a binary. The gap is a long tail, and its failure mode
  is severe rather than graceful — see section 4.

The counterweight the mandate asked to protect is real and was measured in both
directions: pydantic's Rust serialiser writes JSON text **2.24×** faster than
building a dict and calling `json.dumps`, while its Python-object dump is
**2.65×** slower than a hand-written `to_dict`. End to end the two cancel almost
exactly (section 2).

An earlier measurement, quoted in the mandate, found `generate` + `to_dict`
about 30 % *slower* under dataclasses. Nothing in this repository records it, so
it could not be inspected. It is **refuted**: measured here, with a
dataclass layer that keeps every range check and emits a byte-identical payload,
`generate` + `to_dict` is **29.4 % faster**. Same magnitude, opposite sign.

---

## How these numbers were produced

Windows 11 Pro (26200), CPython 3.13.4, `pydantic` 2.11.7 / `pydantic-core`
2.33.2, on the same machine as `bench/results.json`.

Every figure is a median over fresh interpreters — nine for the steady-state
arms, fifteen for the import arms — because the thing being measured is
sensitive to process state in two ways that both flatter whichever arm runs
second:

- **One arm per interpreter.** CPython 3.11+ specialises call sites per code
  object. Measuring pydantic and dataclasses in one process was tried first and
  produced a *reversed* result for the default configuration: the second arm ran
  through call sites already adapted to the first arm's classes and paid for it.
- **One metric per interpreter.** Measuring five metrics in sequence lets the
  machine drift into the later ones, and the pydantic arm has a sixth metric the
  others do not. Splitting them, and interleaving every (arm, metric) pair
  before repeating any of them, brought the spread on every steady-state figure
  below 2 % of its median.

Session-to-session drift is larger than that. `from acronymkit import
AcronymEngine` measured 134.7, 139.6, 150.4 and 154.7 ms in four sessions on the
same machine on the same day, against 128.1 ms recorded in
`bench/results.json`. **Only within-session ratios are used below**, and the
whole import table comes from one interleaved session. `bench/results.json`
remains the figure of record; nothing here supersedes it.

### The comparison arm

The counterfactual is a frozen-dataclass shadow of `models.py`, field for field,
with `to_dict()` hand-written to emit exactly what `model_dump(mode="json")`
emits — computed `length` field included, enums rendered as their values.

Two things make it a fair arm rather than a flattering one:

1. **The whole engine runs on it.** Every module on the generation path binds
   its model classes with `from .models import X`, so rebinding those module
   globals swaps the entire DTO layer without touching a line of algorithm. The
   swapped engine's payload is **identical** to the pydantic engine's, key for
   key and value for value, once the wall-clock `execution_time_ms` field is
   removed. This is an end-to-end measurement, not a projection from component
   costs.
2. **A second dataclass arm keeps the validation.** A shadow that validates
   nothing beats pydantic by deleting work rather than by being cheaper, so
   there is a third arm carrying every `Field` constraint on the generation path
   — `Token`'s three `ge=0`, `LetterMapping`'s `ge=0` and one-character length
   bound, `EngineMetadata`'s three `ge=0` — in `__post_init__`. It costs
   **2.1 %**. Wherever the two dataclass arms differ, the *checked* one is the
   one to read.

Type checking is deliberately not reproduced in either shadow. "Dataclasses plus
an explicit `validate()`" means types are checked where untrusted data enters,
not 129 times per call on values the engine computed itself a microsecond
earlier. That is the design being priced, and section 6 is honest about what it
gives up.

### Why none of this is in `bench/results.json`

The comparison arm is a throwaway. A runner committed to `bench/` would have to
carry a second DTO layer forever to keep these numbers reproducible, and a
benchmark that only runs against code the project does not ship is dead weight
the moment the decision is taken. So the numbers live here, with the method
written out in enough detail to rebuild the harness — about 200 lines — and
`bench/results.json` is untouched. No published figure moves, and the wheel is
unchanged, so the size budget is unaffected.

**Which means none of the figures below is backed by `tools/check_claims.py`,
and that is deliberate rather than an oversight.** The gate exists so that a
*published* claim traces to a run id. These are inputs to a decision, not
claims the package makes about itself, and nothing here is quoted in the README,
`docs/EVALUATION.md` or a docstring. If any figure from this note is ever
promoted into one of those, it has to be re-measured through a runner and saved
first. Treat a number from this page that has escaped into user-facing prose as
a defect.

---

## 1. Cold import: 84.6 % of it is not this library

Median of 15 fresh interpreters per arm, all arms interleaved in one session.
The timer starts after interpreter start-up, so CPython's own cost is excluded.

| measured in a fresh interpreter | median | min | max |
|---|---:|---:|---:|
| `import pydantic` | 29.95 ms | 29.32 | 31.14 |
| `import pydantic_core` | 20.74 ms | 20.11 | 22.03 |
| `import acronymkit` | 2.14 ms | 2.02 | 2.36 |
| `from acronymkit import AcronymEngine` | **139.60 ms** | 137.75 | 143.34 |
| `from acronymkit import AcronymEngine`, `pydantic` already resident | 109.51 ms | 107.56 | 114.22 |
| import + construct engine + one `generate()` | 213.88 ms | 210.69 | 218.83 |

The lazy re-export from D-013 is doing exactly what D-013 said it does: 2.14 ms
to have the package present, 139.60 ms to have the engine.

### Where the 139.60 ms goes

Two independent decompositions agree, which is why the attribution is worth
trusting.

**By differential.** `pydantic` resident beforehand removes 30.09 ms, so that is
the import subtree — and it matches `import pydantic` measured alone (29.95 ms).

**By construction cost.** The single largest line item is not importing pydantic
at all. It is building the first model class:

| measured in a fresh interpreter | median |
|---|---:|
| first `BaseModel` subclass built in the process (one `int` field) | **87.96 ms** |
| second `BaseModel` subclass built in the same process | 0.26 ms |
| first frozen dataclass built in the process (one `int` field) | 0.35 ms |

87.96 ms for a class with one field, and 0.26 ms for the next one. That cost is
pydantic bringing up its schema-generation machinery — a fixed toll, paid by
whichever module happens to define a model first, and **independent of how many
models `acronymkit` declares**. Declaring one model would cost the same as
declaring sixteen.

The per-module figures confirm it. `acronymkit.config` defines two models and
`acronymkit.models` defines fourteen; whichever is imported first pays ~88 ms
and the other pays for its classes only:

| measured in a fresh interpreter | median |
|---|---:|
| `import acronymkit.config` (pydantic resident, first models built) | 89.08 ms |
| the frozen-dataclass shadow of the same module, same preamble | **9.21 ms** |
| `import acronymkit.models` as the first model-defining module | 95.67 ms |
| `import acronymkit.models` after `acronymkit.config` | 7.57 ms |
| `import acronymkit.tokenizer` (regex compilation; no models) | 5.60 ms |

So `config.py` — same fields, same defaults, same five preset instances built at
module scope, differing only in the base class — costs **89.08 ms** with
pydantic and **9.21 ms** without.

**Attribution of `from acronymkit import AcronymEngine`, 139.60 ms:**

| | ms | share |
|---|---:|---:|
| importing `pydantic` and its dependencies | 30.09 | 21.6 % |
| pydantic's one-time model-building machinery | 87.96 | 63.0 % |
| everything else, including 5.60 ms of regex compilation and 7.57 ms for the 14 classes in `models.py` | 21.55 | 15.4 % |

The residual is an upper bound on this library's own cost: about a third of it
is still pydantic, building the fourteen classes in `models.py`. A migrated
import is bounded below by that 21.55 ms — **6.5×** less than the 139.60 ms paid
today — and that bound is the only thing worth saying until it has been built
and measured.

---

## 2. Steady state: 22.4 % of a warm call, and a serialiser that pulls the other way

A warm `generate("Portable Document Format")` builds **129** models under
`Config()` — 3 `Token`, 78 `LetterMapping`, 23 `ScoreBreakdown`, 23
`AcronymCandidate`, 1 `EngineMetadata`, 1 `AcronymResult` — and **22** under
`Config.fast()`. Counted by wrapping `BaseModel.__init__` for exactly one call.

Median of 9 fresh interpreters per (arm, metric) pair, 3,000 timed iterations
after 500 warm-up iterations in each. Payloads verified identical across arms.

| microseconds, warm | pydantic | dataclass | dataclass + range checks | pydantic's share |
|---|---:|---:|---:|---:|
| `generate()`, `Config()` | 347.60 | 264.30 | 269.80 | 77.80 (**22.4 %**) |
| `generate()`, `Config.fast()` | 95.30 | 83.00 | 84.10 | 11.20 (11.8 %) |
| `generate()` + `to_dict()`, `Config()` | 422.80 | 295.70 | 298.70 | 124.10 (**29.4 %**) |
| `generate()` + `to_dict()`, `Config.fast()` | 108.40 | 89.60 | 90.50 | 17.90 (16.5 %) |
| `generate()` + `to_json()`, `Config()` | 534.60 | 403.20 | 406.20 | 128.40 (24.0 %) |
| `generate()` + `model_dump_json()`, `Config()` | 412.60 | — | — | see below |

The share the library pays scales with how much of the result it builds:
`Config.fast()` returns 5 candidates instead of 25, and pydantic's share falls
from 22.4 % to 11.8 %. Keeping the range checks costs 5.5 µs of the 264.30, so
the fair comparison is 269.80 against 347.60.

### Components, isolated

Same object graph, built and serialised both ways. Median of 9 fresh
interpreters; the empty-call noise floor is 0.0–0.1 µs.

| microseconds | pydantic | dataclass |
|---|---:|---:|
| build the whole 129-model result graph | 180.80 | 98.50 |
| build the 22-model `Config.fast()` graph | 27.40 | 15.60 |
| build one `Token` | 1.60 | 0.80 |
| build one `LetterMapping` | 1.10 | 0.50 |
| build one `ScoreBreakdown` | 1.20 | 0.60 |
| `to_dict()` — dict out | **67.50** | **25.50** |
| `to_json()` as the library implements it — dict, then `json.dumps` | 169.40 | 127.30 |
| `model_dump_json()` — Rust serialiser straight to text | **56.80** | not available |
| `model_dump()` — Python-object mode | 59.60 | — |
| `Config()` | 3.10 | — |
| `Config.with_overrides(...)` | 8.00 | — |

**The counterweight, stated in both directions so it cannot be buried.**

- Asked for a **Python dict**, pydantic is **2.65× slower** than a hand-written
  walker: 67.50 against 25.50.
- Asked for **JSON text**, pydantic is **2.24× faster** than the dict-then-dumps
  route: 56.80 against 127.30. The Rust serialiser is genuinely good, and it
  beats CPython's `json` module at the job `json` exists for.

Two consequences, and they point in different directions.

**One is a free win available today, without deciding anything.**
`_Frozen.to_json` goes through `model_dump(mode="json")` and then `json.dumps`,
which is the slow half of both worlds: 169.40 µs where `model_dump_json()`
delivers the same document in 56.80 µs. That is **2.98×** on a public method.

The two are not byte-identical, and the difference is exactly the separators:
`json.dumps` writes `", "` and `": "`, pydantic writes `","` and `":"`. Parsed,
the documents are equal; and `json.dumps(payload, separators=(",", ":"))`
reproduces `model_dump_json()` byte for byte, which is how that was checked. So
the change is a real if minor break in the emitted text — 19,585 characters
becomes 17,684 for the standard result — and belongs in `CHANGELOG.md` rather
than being slipped in. If pydantic stays, it is still worth making.

**The other is that even the fast path does not rescue the end-to-end.** With
the Rust serialiser doing the work, `generate()` + `model_dump_json()` is
412.60 µs, against 406.20 µs for the checked dataclass arm building a dict and
calling `json.dumps`. Pydantic loses by 1.6 % — a tie. The construction penalty
(77.80 µs) is very slightly larger than the serialisation advantage it buys
back. On the dict path, which is what `to_dict()` and every non-JSON caller use,
there is no advantage to buy back at all.

### One measurement that surprised, recorded because it closes an escape hatch

`model_construct()` — pydantic's documented way to skip validation — makes the
graph build **slower**, not faster: 236.70 µs against 180.80 µs for ordinary
validating construction. Whatever it saves in the Rust validator it more than
spends computing defaults and `model_fields_set` in Python. "Keep pydantic but
turn validation off in the hot path" is not an available option.

---

## 3. Footprint

Installed, `__pycache__` and `.pyc` excluded:

| installed | bytes |
|---|---:|
| `pydantic_core` | 5,512,365 |
| — of which `_pydantic_core.cp313-win_amd64.pyd` | 5,309,440 |
| `pydantic` | 1,693,591 |
| `typing_extensions` | 165,012 |
| `.dist-info` metadata for the five | 133,292 |
| `typing_inspection` | 48,625 |
| `annotated_types` | 20,240 |
| **total** | **7,573,125** (7.22 MiB) |
| `acronymkit`, wheel contents uncompressed | 1,388,777 (1.32 MiB) |

Downloaded, as wheels from PyPI:

| wheel | bytes |
|---|---:|
| `pydantic_core-2.33.2-cp313-cp313-win_amd64` | 1,955,269 |
| `pydantic-2.11.7-py3-none-any` | 444,782 |
| `typing_extensions-4.16.0-py3-none-any` | 45,571 |
| `typing_inspection-0.4.1-py3-none-any` | 14,552 |
| `annotated_types-0.7.0-py3-none-any` | 13,643 |
| **dependency total** | **2,473,817** |
| `acronymkit-0.2.0-py3-none-any` | 404,650 |

**6.11× the download and 5.45× the installed size of the library itself.** The
project enforces a 512 KiB wheel budget on its own artifact and reviews every
resource against it; the dependency it does not measure downloads 4.72 times
that whole budget. The Rust extension alone is 5.06 MiB — 13.1× the wheel the
budget governs.

---

## 4. The compiled extension against "works anywhere"

This is the argument the mandate did not make, and it turns out to cut mostly
*against* the mandate.

`pydantic-core` 2.33.2 publishes **98 wheels and one sdist** (435,195 B) across
**20 distinct platform tags**, for CPython 3.9–3.13 and PyPy 3.9–3.11:

`macosx_10_12_x86_64`, `macosx_11_0_arm64`, `manylinux_2_17_{x86_64, aarch64,
armv7l, ppc64le, s390x}`, `manylinux_2_5_i686`, `musllinux_1_1_{x86_64,
aarch64, armv7l}`, `win32`, `win_amd64`, `win_arm64` (plus the
`manylinux2014_*`/`manylinux1_*` aliases for the same files).

**Alpine, ARM and s390x are all covered.** Alpine on x86-64, aarch64 or armv7
gets a musl wheel. s390x and ppc64le get glibc wheels. Windows on ARM gets a
wheel on 3.11 and newer. The current release (2.48.0, 136 wheels) adds
`manylinux_2_31_riscv64`, `pyemscripten_2026_0_wasm32` and GraalPy, so the
matrix is broadening, not narrowing. Anyone asserting that pydantic breaks
portability on those targets is wrong, and this note says so.

**The gaps that remain, exhaustively:**

| gap | consequence |
|---|---|
| musl only for x86_64, aarch64, armv7l | Alpine on i686, s390x or ppc64le has no wheel |
| no BSD, illumos or AIX tags at all | those platforms have never had a wheel |
| free-threaded 3.13t: 3 wheels only (`macosx_11_0_arm64`, `manylinux_2_17_x86_64`, `win_amd64`) | free-threaded builds elsewhere have no wheel |
| `win_arm64` from cp311 only | Windows on ARM with 3.9 or 3.10 has no wheel |
| `pydantic-core` 2.48.0 declares `requires-python >=3.10` | Python 3.9 — this project's declared floor — is being dropped upstream. It still works today: `pydantic` 2.13.4 pins `pydantic-core==2.46.4`, which does ship cp39 wheels. |

**What happens when there is no wheel is the part that matters.** pip falls back
to the sdist, and the sdist declares
`requires = ['maturin>=1,<2', 'typing-extensions >=4.6.0,!=4.7.0']` with
`build-backend = 'maturin'`. `Cargo.toml` declares `rust-version = "1.75"`, and
`Cargo.lock` lists **93 packages**. So the fallback needs a Rust toolchain at
1.75 or newer *and* reachable access to crates.io to fetch 92 external crates.

That failure mode is worth naming precisely, because it collides with this
project's own discipline. `docs/OFFLINE.md` documents an installation that must
work from a hash-pinned local wheelhouse with no network. On any platform in the
gap list, there is no wheel to put in that wheelhouse, and the alternative is a
compiler toolchain and a package registry — neither of which an air-gapped
installation has. `acronymkit` itself is `py3-none-any` and would install
anywhere Python runs. Its dependency decides where it actually can.

That is a real cost, but it is a *long-tail* cost, and the honest summary is:
"works anywhere" holds on every platform most users are on, and fails hard
rather than gracefully on the rest.

---

## 5. Inventory: every pydantic use in `src/`

Four modules import pydantic: `models.py`, `config.py`, `serialization.py`,
`cli.py`. Nothing else touches it.

**16 `BaseModel` subclasses, 136 declared fields.**

| module | classes |
|---|---|
| `models.py` | `_Frozen` (private base) and the 13 public DTOs: `Token`, `LetterMapping`, `ScoreBreakdown`, `AcronymCandidate`, `EngineMetadata`, `AcronymResult`, `AcronymPair`, `ExtractionResult`, `BackronymCandidate`, `BackronymResult`, `DisambiguationCandidate`, `DisambiguationResult`, `BatchResult` |
| `config.py` | `ScoringWeights` (10 fields), `Config` (37 fields) |

**`model_config`.** `_Frozen` sets `frozen=True, extra="forbid",
use_enum_values=False, validate_assignment=False, ser_json_inf_nan="constants"`
and all 13 DTOs inherit it. `ScoringWeights` sets `frozen, extra="forbid"`;
`Config` adds `validate_default=True`.

**Constraints: 27 fields carry one.** `Config` 10, `ScoringWeights` 7,
`Token` 3, `EngineMetadata` 3, `LetterMapping` 2, `AcronymPair` 1,
`BackronymCandidate` 1. Every one is a range bound (`ge`, `gt`, `le`) except
`LetterMapping.character`, which is `min_length=1, max_length=1`. There are no
regex constraints, no discriminated unions, no aliases, no custom
`field_validator`, and no `Annotated` metadata beyond these.

**Other pydantic machinery, complete list:**

| use | site |
|---|---|
| `@computed_field` | `AcronymCandidate.length` — one, and it appears in dumps and in the interchange schema |
| `@model_validator(mode="after")` | `Config._validate` — one, cross-field; it also calls `object.__setattr__` to normalise a frozen field |
| `model_dump()` | `serialization._as_payload`, `Config.with_overrides` |
| `model_json_schema()` | `serialization.export_model_schema` — public function |
| `model_copy(update=...)` | `nlp/base.annotate`, `extractor.py:978`, `ScoringWeights.scaled` |
| `isinstance(x, BaseModel)` | `serialization._as_payload`, `serialization.export_model_schema` |
| `ValidationError` caught | `config.Config.__init__` (unwrapped into `ConfigurationError`), `cli._build_config` and `cli._format_validation_error` |
| mypy plugin | `pyproject.toml`: `plugins = ["pydantic.mypy"]` |

**Coercions the constructors actually perform**, verified by probing rather than
by reading the annotations:

| input | result |
|---|---|
| `Config(engine_tier="hybrid_nlp")` | `EngineTier.HYBRID_NLP` |
| `Config(engine_tier="HYBRID_NLP")` | **rejected** — pydantic matches the enum *value*, case-sensitively |
| `Config(min_word_length="3")` | `3` |
| `Config(min_word_length=3.0)` | `3`; `3.5` is rejected |
| `Config(search_time_budget_ms=5)` | `5.0` |
| `Config(custom_stop_words=["a","b"])` | `frozenset({'a','b'})` |
| `Config(lexicon_path="x.txt")` | `WindowsPath('x.txt')` |
| `Token(role="content")` | `TokenRole.CONTENT` |
| `Token(subtokens=("x","y"))` | `['x', 'y']` |
| `AcronymPair(short_form_span=[1,2])` | `(1, 2)` |
| `Config(nope=1)` | rejected by `extra="forbid"` |
| `Config().engine_tier = ...` | rejected by `frozen=True` — but see below |

Two notes on that table. The str-to-enum coercion is the one the package
*documents*, in `enums.py`: "``Config(engine_tier="hybrid_nlp")`` is equivalent
to ``Config(engine_tier=EngineTier.HYBRID_NLP)``". It is also **narrower than
the library's own `_StrEnum.coerce`**, which accepts names, mixed case and
hyphens; the CLI routes through `coerce`, so the two entry points already
disagree about what a valid tier string is. Routing everything through `coerce`
during a migration would make the public surface strictly *more* permissive, not
less.

And: assigning to a frozen field raises `pydantic.ValidationError`, which is not
an `AcronymKitError`. `config.py` goes to real trouble to unwrap validation
errors at *construction* so that "one `except AcronymKitError` at a service
boundary catches everything this library raises" holds — and the assignment path
leaks around it. Pydantic is already visible in the public error surface in a
way the docstrings say it is not.

### The schema is hand-written, and that decides the difficulty

`schemas/acronym-engine-result.schema.json` is **not** generated from the
models. Compared against `export_model_schema()`:

| | bundled contract | generated from `AcronymResult` |
|---|---|---|
| `title` | `AcronymEngineResult` | `AcronymResult` |
| `$id` | present | absent |
| `$defs` | absent — everything inlined | present |
| `required` | `source_phrase, primary_acronym, alternatives, metadata` | `source_phrase, primary_acronym, metadata` |

The top-level property sets match, which is what the consistency test checks,
but the documents are independent. `export_model_schema()` exists to *diff*
against the contract, not to produce it.

**Consequence:** the cross-language interchange contract, the thing that keeps
the planned `acronym4j` port possible, does not depend on pydantic at all. A
migration changes the type that produces the payload and not the payload — which
is precisely what the swap experiment demonstrated by emitting an identical
document.

### Tests

**44 of 930 test functions** reference a pydantic name or method. Two modules
import from pydantic directly: `tests/test_config.py` (`ValidationError`) and
`tests/test_models.py` (`BaseModel`, `ValidationError`). The concentration is
`test_models.py`, where 16 of 32 functions are involved.

`tests/test_diagnostics.py` and `tests/test_offline.py` account for 8 more, but
those are about the pydantic *entry-point plugin loader* — the one hole in the
offline promise. Those tests do not migrate; they are deleted, because removing
pydantic removes the hole they guard. That is a security consequence, not a test
count: `Config(offline=True)` currently refuses to run beside a third-party
pydantic plugin because pydantic imports arbitrary advertised code while
building the model. No pydantic, no plugin loader, no `OfflineError` for it, and
`docs/OFFLINE.md` loses its only "detection, not prevention" caveat.

---

## 6. The three options

### (a) Migrate to dataclasses plus an explicit `validate()`

**Effort: moderate and almost entirely mechanical.** `models.py` (365 lines) and
`config.py` (516 lines) are rewritten; 27 constraint checks move into
`__post_init__` or into a `validate()` at the boundary; `to_dict()` is written
once per class or as one generic walker; `Config`'s coercion routes through the
existing `_StrEnum.coerce` plus a small helper for `Path` and `frozenset`; 44
test functions are touched, of which about 8 are deleted rather than updated
(see below). The `object.__setattr__` already in
`Config._validate` becomes the idiomatic `__post_init__` form rather than a
workaround. The interchange schema is untouched.

**Risk: moderate, and concentrated in one place.** Hand-written validation is
where bugs live, and these DTOs are the public contract. Mitigating that: the
constraints are 26 range bounds and one length bound; the suite is 3,423 tests
with property-based coverage; and the swapped engine produced an identical
payload on the first attempt, which is weak but real evidence that the surface
is simple. The genuine residual risk is *silent* coercion changes — a caller
passing `min_word_length="3"` today gets `3`, and would get whatever the new
code decides.

**What breaks, named:**

1. `model_dump()`, `model_dump_json()`, `model_validate()`, `model_copy()`,
   `model_fields`, `model_json_schema()` on 15 public classes.
   `model_copy(update=...)` is **explicitly recommended in `models.py`'s module
   docstring**, so it is a documented promise, not an accident of the base class.
   `model_dump` and `model_copy` are three-line shims over `to_dict` and
   `dataclasses.replace`; the rest are not worth shimming.
2. `isinstance(result, pydantic.BaseModel)`. Downstream code can hand an
   `AcronymResult` straight to a framework that special-cases pydantic models —
   a FastAPI `response_model`, for instance. FastAPI handles dataclasses too,
   but not identically, and this cannot be shimmed.
3. `export_model_schema()`, a public function in `serialization.py`, has no
   meaning without pydantic. It goes, or is reimplemented by hand.
4. Constructor coercion: every coercion row in the table above. The documented
   one (str to enum) gets *wider*; the undocumented ones (`"3"` to `3`, `5` to
   `5.0`, `list` to `frozenset`, `str` to `Path`, `list` to `tuple`) are a
   choice to make deliberately rather than inherit.
5. Constraint enforcement moves from "always, at construction" to "wherever
   `validate()` is called". A caller who builds a `Token` by hand with
   `index=-1` is currently stopped and would not be.
6. `pydantic.ValidationError` on frozen assignment becomes
   `dataclasses.FrozenInstanceError`. Both are wrong for a library that promises
   `AcronymKitError`; the change is lateral.
7. The offline plugin-loader defence and its tests become moot (section 5).

### (b) Optional pydantic with a stdlib fallback and a CI cell without it

**Effort: highest of the three.** Everything in (a), plus the pydantic layer
kept, plus a mechanism to choose between them, plus a CI cell, plus tests
asserting the two agree.

**Risk: highest, and of the worst kind.** The two layers drift, and drift in a
DTO layer is invisible until a payload differs in production. Worse, the *public
type surface would depend on what else is installed*: `isinstance(result,
BaseModel)` and `result.model_dump()` would work or not according to whether
some unrelated dependency pulled pydantic in. For a project that publishes a
security-reviewer document and an air-gap installation guide, an API whose shape
is a function of the environment is the one outcome worse than either fixed
choice. The measurements support (b) being *possible* — the swapped engine's
payload was identical — but possible is not the bar.

**Rejected.** Not because it is expensive, but because it is the only option
that makes the public surface non-deterministic.

### (c) Keep pydantic

**Effort: none, plus one cheap improvement.** Change `_Frozen.to_json` to use
`model_dump_json()`: 2.98× on a public method, for the same document written
with compact separators.

**Risk: none new, but two standing costs that do not go away.** The import
figure stays what it is, and D-013's lazy re-export remains a workaround for a
cost that could be removed rather than deferred. And the dependency keeps
deciding where `acronymkit` installs (section 4) and keeps the offline plugin
hole open (section 5).

**The honest argument for (c),** which the numbers do not refute: pydantic's
validation is free, correct and maintained by other people, and the DTOs are the
public contract, where a validation bug is a correctness bug. 22.4 % of a call
that takes 348 µs is 78 µs, and no user has complained. The project's own D-001
principle — *doing something shallowly is worse than not doing it* — applies to
rewriting a validation layer as much as to anything else.

---

## 7. Recommendation

**(a), migrate — and do it before the package is published, not after.**

The decisive fact is not any single measurement. It is that PyPI's JSON API
returns 404 for the name: **the package is not published** (D-001 cut publishing
deliberately). Every item in the "what breaks" list above is a cost paid by
existing users, and there are none. The cost of this change is
near zero today and rises monotonically from the moment the first `pip install`
succeeds. Whatever the numbers said, that asymmetry would dominate the timing.

What the numbers add on top:

- **84.6 % of the engine import is the dependency**, and 63.0 % of it is a fixed
  toll unrelated to anything this library declares. D-013 spent real effort
  making `import acronymkit` cheap while the engine import stayed where it was,
  then published all three figures rather than the flattering one. That honesty
  is the tell: the workaround exists because the cost could not be removed from
  where it actually sits. It can be.
- **22.4 % of a warm call, 29.4 % with `to_dict()`.** This project has reverted
  seven experiments over differences far smaller than that. Applying its own
  standard to its own dependency gives one answer.
- **The counterweight was tested and does not save it.** The Rust serialiser is
  genuinely 2.24× faster at writing JSON text — and the library does not use it,
  and even using it leaves pydantic 1.6 % behind end to end. The strongest
  argument for keeping pydantic is worth about a rounding error.
- **The interchange contract is hand-written, so the port stays possible** and
  the wire format does not move. Measured, not assumed: the swapped engine's
  payload was identical.
- **The migration is small.** 16 classes, 136 fields, 27 constraint checks, one
  computed field, one cross-field validator, 44 test functions.

What the numbers do **not** support, and where this note declines to follow the
mandate: the "works anywhere" premise. pydantic-core ships wheels for musl, ARM,
s390x, ppc64le, Windows-on-ARM, riscv64 and WebAssembly. Anyone migrating for
portability alone is migrating on a misconception. The portability argument is
real but narrow — a long tail of platforms, plus the air-gap case where the
source fallback needs rustc and crates.io — and it should be made in those terms
or not at all.

**Sequencing, so this is not done shallowly:**

1. Land the `to_json` fix (`model_dump_json`) first, on its own. It is a win
   under (c) and it is wasted work under (a) — which is exactly why doing it
   first keeps the decision honest if the migration slips.
2. Migrate `models.py` alone, keeping `Config` on pydantic. The DTOs carry 10 of
   the 27 constraints and all of the serialisation; `config.py` carries the
   other 17 and all of the coercion. Splitting them lands the two risky halves
   separately.
3. Re-run `bench/run_micro.py --save` after each half. If the import figure does
   not move as predicted, that is the signal to stop — the same rule that
   reverted the other seven experiments.
4. Migrate `Config`, routing enum coercion through `_StrEnum.coerce` and
   documenting the widened acceptance in `CHANGELOG.md`.
5. Keep `model_dump()` and `model_copy()` as shims for one minor release, with a
   deprecation note. Do not shim `model_json_schema` or `model_validate`.

**If it is not migrated,** the honest position is that `docs/ARCHITECTURE.md`'s
"Pydantic is a hard dependency, but nothing else is" should carry the import
attribution from section 1 and the platform gaps from section 4 next to it. The
present wording lets a reader conclude that the dependency is a detail. It is
84.6 % of the import.

---

## 8. What this does not measure

- **One machine, one operating system, one interpreter.** Windows 11, CPython
  3.13.4. Import costs are dominated by filesystem behaviour, and Linux with a
  warm page cache will not divide the same way. The *ratios* are more portable
  than the milliseconds, and only ratios are used in the conclusions.
- **The shadow covers the generation path only** — 6 of the 15 public classes,
  and only the fields those classes carry. Extraction, backronym, disambiguation
  and batch results were not shadowed. A real migration is larger than what was
  benchmarked, and no effort estimate here comes from a measurement.
- **The shadow does no type checking.** That is the design being priced, not an
  oversight, but a maintainer who wants per-construction type validation would
  not get these numbers.
- **`model_construct` was measured on this graph only.** Its being slower than
  validating construction may not hold for wider or shallower models.
- **Platform coverage is a file listing, not an installation.** No install was
  attempted on a platform without a wheel; that pip would fall back to the sdist,
  and that the sdist needs maturin and rustc 1.75, is read from the published
  metadata rather than observed.
- **`generate` was measured on one phrase**, `"Portable Document Format"`, the
  same one `bench/run_micro.py` uses. Pydantic's share scales with the number of
  models a call builds, which is why the two configurations differ by nearly 2×;
  a longer phrase with more candidates would push the share up, not down.
