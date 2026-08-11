# Decisions, and things deliberately not done

Negative results are the easiest thing in a project to lose and often the most useful thing to keep.
This file records what was tried and abandoned, what was considered and cut, and why — so nobody
re-litigates a settled question from scratch, and so the settled questions can be re-opened on
evidence rather than on vibes.

Newest first.

---

## D-026 — Five optimisations that change no answer, and a sixth that was reverted

**Status:** shipped; the passthrough memo reverted · **Evidence:** `governed.*` in
[`bench/results.json`](../bench/results.json), `bench/run_governed.py`, `tests/test_governed_perf.py`

The consumer described in D-025 walks tens of thousands of column names inside one process, so the
figure that decides anything is the cost of a corpus, not the cost of a call. `bench/run_governed.py`
is the only writer of these numbers and it runs two arms deliberately: a `schema` arm whose
token-frequency distribution is the fixture corpus's, and a `novel` arm in which no token repeats and
nothing can be reused between names. The two answer different questions and their figures must not be
read against each other; each is compared against itself across a change.

```
schema arm, medians, one machine          before      after
  expand_identifier                        62.30      10.70   us per call
  to_physical_name                         99.90      41.50   us per call
  is_compliant                             62.40      38.60   us per call
  corpus throughput                       15,607     96,532   identifiers/sec
```

The **after** column is what `bench/results.json` holds and is the figure of record; the corpus row
is the one to quote for a pipeline, because it carries no per-sample timer overhead. The **before**
column is not in that file and cannot be — a runner records the tree it is run against, so a baseline
survives only as far as somebody writes it down. It is written down here, it is one machine, and
D-023's warning applies unchanged: session-to-session drift on this host is larger than several of
the differences this project has argued about elsewhere, so a ratio of this size is what carries the
argument and a decimal is not.

### The five, and what makes each one unobservable

**An ASCII fast path in the splitter.** Splitting is the largest single cost in expanding an
identifier, and reading `TXN_APPLNT_ID` character by character is an expensive way to spend it. An
all-ASCII name — very nearly every name — is now one call into the regex engine. That is two readings
of one set of rules, which is exactly the drift `tokenizer.py` warns about everywhere else, so the
split is drawn where it can be policed: rules 2, 7 and 8 keep a single statement in `_classify`, from
which the unaccounted-character pattern is *derived* at import, and rules 3 to 6 genuinely are stated
twice and are property-tested against the scan over arbitrary ASCII text plus exhaustively to length
four over the alphabets where the rules interact. When the two disagree the scan is right by
definition and the pattern is the bug; the test says so rather than leaving it to be argued.

**A memo of resolved entries and token expansions, per (dictionary, policy).** A schema repeats
tokens enormously — every table has an id, a date and a code column — and `resolve` is a pure
function of dictionary, token and policy, so the answer is remembered on the dictionary. All three
parts of the key are honoured: the memo lives on the instance and `with_custom` builds a new instance
with an empty one, memos are kept per policy and matched by value, and the key is the surface token
because `raw` reports the spelling that was given. The bound is structural rather than a number:
only governed answers are remembered, so the key space is the vocabulary the dictionary fixed at
construction. `_MEMO_LIMIT` is a second bound for the residue a case-insensitive lookup leaves
behind, since `TXN`, `Txn` and `tXn` are three keys for one row.

**A length rejection in `abbreviate`.** A word longer than the catalog's longest long form cannot be
in the reverse index, so the lookup is skipped before the key is built.

**Memoised `NamingPolicy` presets.** Each preset names a fixed set of field values, so every call was
building an object equal to the last — once per verb call, since this is the default a caller gets
when they omit `policy=` — and the resolver then keys its memo on the policy *by value*, so the cost
was paid twice, once to construct and once to discover the construction had been unnecessary. The
models are frozen, so one shared instance is unobservable except by `is`.

**Bounding `naming._render`'s longest-match scan by the catalog rather than by the name.** It used to
scan from the end of the name back to the current position, which is quadratic in the words: an
eighteen-word name costs 18 × 19 / 2 = 171 lookups, and nearly all of them ask whether a reverse
index whose wordiest key is two words long contains an eighteen-word key. That answer is fixed at
construction, so the window is now `GovernedDictionary.longest_long_form_words`. A run longer than
the wordiest key cannot match anything, which is why the outcome cannot change — and rather than
leave that as an argument, the output was compared byte for byte over the whole corpus and is
identical. This step alone took `to_physical_name` from 76.15 to 41.50 us; the second figure is the
recorded one and the first is an intermediate reading of the same un-recorded kind as the baseline
column above. Names get longer; catalog terms do not.

### Reverted: remembering the tokens the catalog is silent about

A real schema repeats its *unknown* tokens as thoroughly as its known ones, so memoising the
passthrough path was tried and was faster on such a corpus. It was reverted on what it does to the
key space rather than on the size of the win, and both ways of bounding it are worse than not doing
it at all:

- **Clear the memo when it fills** — the `novel` arm, where nothing repeats, lost about 44 %. The
  bookkeeping is then paid on every token and returns nothing, and the periodic clear discards the
  governed answers alongside the useless ones. That figure is not in `bench/results.json` either,
  for the same reason the baseline is not: a reverted arm leaves no row behind.
- **Stop writing when it fills** — the memo fills with arbitrary caller strings and stops learning,
  so a service that runs for a month ends up holding the first few thousand column names it ever saw
  and nothing since.

There is a second reason and it is the stronger one, because it is about correctness rather than
memory. `UnknownPolicy.REJECT` *raises* on an unknown token, and a cache in front of that path would
put a policy-dependent raise behind a lookup. The one thing a cache must never do is answer a
question that was supposed to stop the pipeline.

**The rule that replaced it: the memo remembers what the catalog said; the catalog saying nothing is
not something to remember.** That is also what keeps the key space equal to the vocabulary rather
than to whatever names the caller happens to have, which is the shape that grows without limit.

### What is not claimed

No accuracy figure appears anywhere near this work, because the whole justification of every item
above is that it changes no answer. `tests/test_governed_perf.py` is where that is asserted and it
times nothing; wall-clock budgets belong in `bench/`, where the environment is pinned and dispersion
is reported.

The `schema` arm flatters anything memoised per token, and it should: 2,000 generated names resolve
31,926 token occurrences out of 117 distinct tokens, which is the shape a governed vocabulary
imposes. A caller whose names are genuinely one-offs should read the `novel` arm instead, which is
recorded for exactly that reason and is why the runner will not publish only the good half:

```
novel arm, medians, current tree      (no baseline was kept)
  expand_identifier                    44.80   us per call
  to_physical_name                     42.20   us per call
  is_compliant                         44.00   us per call
  corpus throughput                   22,467   identifiers/sec
```

Those figures must not be read against the `schema` column: a `novel` token is unknown to the
catalog and takes the passthrough path, which is a different amount of work from resolving a
governed row. Every measurement gets a freshly built vocabulary, because a dictionary that remembers
what it has been asked is not being asked the same question twice — the first draft of the runner
shared one dictionary and reported a `novel` arm partly served from the previous arm's answers.

---

## D-025 — The consumer is on the other side of a process boundary, and per-call invocation is what would have ended it

**Status:** shipped · **Evidence:** `src/acronymkit/governed/namer.py`, `loaders.py`, `audit.py`,
`src/acronymkit/cli.py`, [`QUICKSTART_GOVERNED.md`](QUICKSTART_GOVERNED.md)

The subsystem answered every question correctly and was still not adoptable, and the reason had
nothing to do with the answers. The consumer this was built for is a schema-governance pipeline
written in another language: it holds a list of column names and needs them back expanded, checked
and corrected. Reaching a Python library from there means a process, and the only shape of API on
offer was one call per name.

That is not a small tax, it is the entire cost. One interleaved session on this machine, medians of
five, each arm run once per pass:

```
bare interpreter, nothing imported                        50.1 ms
one expand-identifier invocation                         281.0 ms
one governed-batch over 2,000 names                      432.5 ms
the same 2,000 names as 2,000 invocations            562,000    ms   (arithmetic)
```

Both invocation rows include reading the fixture bundle, which is what a real caller pays too — the
batch pays it once and the per-call pipeline pays it per column, and that is part of the point rather
than a confound to be stripped out.

Roughly **1,300 times**, and the ratio rather than the milliseconds is the durable part: a second
session on the same host put the same comparison at about 1,354, while every absolute figure in it
moved. Set against that, the answers themselves are
0.021<!--claim:governed.throughput.elapsed_seconds--> s of the batch run, at
96,532<!--claim:governed.throughput.identifiers_per_second:,--> identifiers per second. Almost none
of what a per-call pipeline pays for is the work.

### What was built, and what each piece is for

- **`GovernedNamer`** binds a vocabulary and a policy once and exposes the five verbs with the
  subject as their only argument, plus `expand_many` / `check_many` for a corpus and
  `with_custom` / `with_policy` for a variant. `from_bundle`, `from_csv` and `from_json` are the
  constructors, so start-up is one line. It is built once and never written to afterwards, holds no
  cache and reads no clock.
- **Loaders** — `load_bundle`, `load_csv`, `load_long_to_short_csv`, `load_term_index_csv` and
  `BUNDLE_FILES` — because a standard is not one file. It is a catalog, three allow-lists, a
  class-word map, a pin sheet and a term glossary, and the section names each accept several
  spellings so a standard exported by somebody who never read the docs usually loads unchanged.
- **`audit_identifiers` / `render_audit` / `suggest_catalog_additions`** turn a corpus into one
  report. The unknown-token table is the part that earns its place: it converts "our catalog is
  incomplete" into a finite list of rows to write, ranked by how often each token appears and in how
  many of the corpus's identifiers, with one column to go and look at. A suggestion is a request for a decision
  from whoever owns the catalog, never a wording this library invented.
- **`governed-batch` and `governed-audit`** are the process-boundary surface. Records stream in and
  out one at a time so memory is flat in the size of the corpus; every record carries `line`, `input`
  and any `id` it arrived with, so a caller correlates without relying on order.
- **Everything above is exported from `acronymkit.governed`** as well as from its own module, 42
  public names in one place, resolved lazily so a caller who wants one enum still does not pay for
  the Pydantic schemas.

### Three contract decisions inside the batch, each of which could have gone the other way

**A bad record is a record, not an exit.** Losing forty-nine thousand answers to one unparseable line
is a worse outcome than any error message, so the failure rides on the record and the run continues.
The process still exits non-zero when anything failed, so it remains usable as a gate.

**A finding is not a failure.** Under `--op check`, a name that does not conform comes back
`"ok": true` with `compliant` false inside the result and the exit status unchanged. Reporting
non-conformance is the job the command was given; making it an error would mean a pipeline could not
tell "your schema has findings" from "the tool broke".

**Stdout carries records and nothing else.** The one-line summary goes to standard error and the
record stream is ASCII-escaped, so a consumer parses stdout without knowing to skip anything and a
record survives whatever encoding is on the far side.

### Limits, and one that is a real cost

`governed-batch` catches **every** exception a record raises, not a named set. That is right for a
`LexiconError` from a policy that rejects unknown tokens, which is a documented outcome; it also
means a systematic bug arrives as forty-nine thousand error records rather than as one loud crash.
The `failed` count and the exit status are what a caller should watch.

`--op audit` costs four verb calls and a pile of model construction per record where `--op expand`
costs one, because it runs the corpus audit over a single name. A schema-wide sweep is much cheaper
as one `governed-audit` than as fifty thousand `--op audit` records, and the flag is opt-in for that
reason.

An audit describes the corpus it was given and not the standard. An empty backlog means the corpus
exercised no token the catalog is silent about — not that the catalog is complete.

And the JVM consumer is still hypothetical. No `acronym4j` artifact exists; what exists is a wire
contract with golden files (`docs/notes/governed-json-contract.md`) and a command that a pipeline in
any language can drive. That is the thing this record claims, and nothing beyond it has been
demonstrated.

---

## D-024 — A subsystem whose thesis is that it refuses to guess was discarding characters and reporting a complete answer

**Status:** fixed, shipped · **Evidence:** `src/acronymkit/governed/tokenizer.py`,
`tests/test_governed_edge_cases.py::test_nothing_leaves_without_being_kept_or_reported`,
[`GOVERNED_NAMING.md`](GOVERNED_NAMING.md#what-the-splitter-accounts-for)

`_classify` sorted every character that was neither a letter nor a digit into one bucket:
*separator*. Separators end a token and then vanish, which is correct for the underscore in `TXN_ID`
and wrong for everything else. So an emoji pasted out of a spreadsheet, a stray comma from a
hand-edited CSV of column names, a currency sign, a combining accent left behind by a decomposed
Unicode spelling — each was silently deleted, and the name that came back was the name somebody
*should* have written:

```
before        TXN_<emoji>_ID  ->  'Transaction Identifier',  is_fully_known True
after         TXN_<emoji>_ID  ->  'Transaction Identifier',  is_fully_known False
                                  unaccounted ('<emoji>',)
```

The phrase is not the defect. The phrase is unavoidable — no catalog row can expand a character that
is not a word — and it is identical to what a clean `TXN_ID` produces, which is precisely the
problem. The defect is the second column. `is_fully_known` is the one bit a pipeline gates on, and it
was reporting that a governed vocabulary had accounted for the whole of a name it had not read the
whole of. Every other unknown in this package is recoverable because it is reported: an unknown
token is `is_known=False` with zero confidence and a row somebody owes. A dropped character was
reported as nothing at all, which makes a governance tool a confident source of names nobody wrote —
the exact failure the rest of the design exists to prevent.

### The design, which is a three-way split rather than a two-way one

**Accounted separators still vanish, silently, and that is deliberate.** Nine characters — the
underscore, hyphen, dot and slash, then the double quote, apostrophe, backtick and the two square
brackets — plus every character `str.isspace()` accepts, printed from the published constant rather
than transcribed:

```python
sorted(ACCOUNTED_SEPARATORS)   # ['"', "'", '-', '.', '/', '[', ']', '_', '`']
```

The first four are what a physical name is *made of*, and a caller who wrote `TXN_ID` does not need
to be told it contained an underscore. The rest are how the common SQL dialects quote an identifier,
so `"TXN_ID"`, `[TXN_ID]` and a backtick-quoted name read exactly like the bare one; a name that made
a round trip through a catalog query is the same name. Reporting those would make the field noise,
and a field that is usually noise is a field nobody reads.

**Everything else is reported**, one entry per occurrence, in input order, in a new
`IdentifierExpansion.unaccounted` field, and `is_fully_known` is now `all tokens known` **and**
`unaccounted` empty.

**An unaccounted character is deliberately not made into a token of its own**, and this is the choice
most likely to be revisited by somebody who has not thought about it. Turning it into a token would
have been less code and would have made the character visible through machinery that already exists.
It is refused because a token is two things at once: a lookup key, and a work item. A token that
misses is a catalog row somebody owes. "This name holds a character I could not read" is a different
fact, it is not fixable by writing a catalog row, and the token list is also what `normalize`
rebuilds a corrected name out of — so a stray character promoted to a token would be a permanent
member of the backlog *and* would appear in a name the tool proposed. Two facts, two fields, one
clean work queue. `unaccounted` is separate from `unknown_tokens` for the same reason.

### The guarantee that replaced "lossless"

"Lossless" was the word the first draft reached for and it does not survive contact with the accounted
separators, which are lost on purpose. What is stated instead is countable:

> For any input string, and for any character that is not one of the accounted separators and is not
> whitespace, the number of times that character occurs in the input equals the number of times it
> occurs across the returned tokens plus the number of times it appears in `unaccounted`.

That is a property, so it is property-tested rather than exampled —
`test_nothing_leaves_without_being_kept_or_reported` under Hypothesis, with the separator set itself
asserted against the published constant so the guarantee cannot be widened by editing one file. It
also settles a question that was previously answered by implication: the splitter applies no Unicode
normalisation, because NFKC rewrites text, a normalising splitter would return tokens that are not
substrings of the identifier, and the guarantee would then have nothing left to count.

### The ordinal fix, which landed with it and has the same shape

`1ST_TXN_DT` split to `1|ST|TXN|DT` and expanded to "1 St Transaction Date". `ST` is a token no
catalog carries and "1 St" is not what the column is called, so rule 5's letter↔digit boundary now
has one exception: a closed suffix set (`st`, `nd`, `rd`, `th`), matched without regard to case, and
only when those two letters *end* the token.

```
1ST_TXN_DT   -> ('1ST', 'TXN', 'DT')     '1st Transaction Date'
1STATE       -> ('1', 'STATE')
ADDR_1_ST    -> ('ADDR', '1', 'ST')
1sT          -> ('1', 's', 'T')
```

It is English-only and says so — a catalog whose ordinals are written `1ER` or `1E` gets rule 5 and
nothing else — and it does not reach across a separator, so `ADDR_1_ST` keeps the two tokens somebody
wrote separately.

**The last line was `('1s', 'T')` when this record was first written, and that was a bug, not a
quirk.** The reasoning at the time was that rule 6 keeps the suffix with its digits, rule 4 then cuts
between a lowercase letter and the capital after it, nobody writes an ordinal that way, and there was
no obviously better answer to give it — so the odd answer was pinned rather than tidied, because a
port reading rule 6 "cleanly" would answer `('1sT',)` and diverge.

It was not answer-neutral. `'1s'.upper()` is `'1S'`, which splits back into `('1', 'S')`, and
`normalize` rebuilds a name by upper-casing the tokens the splitter found and joining them with `_`.
So `normalize('1sT')` was `'1S_T'` and `normalize('1S_T')` was `'1_S_T'` — the invariant this project
states as holding *by construction* was false for every name containing one, and the test carrying it
runs over a 40-line fixture corpus that has no such name in it.

The rule now has a third condition: it does not fire across a camelCase boundary, so `1sT` is three
tokens. A capital after a lowercase letter is the writer saying a new word starts there, which is what
that signal means everywhere else in the splitter, and rule 6 exists because `1ST` is one *word*. The
port-divergence note stands, with a different answer on this side of it.

What is worth keeping from the mistake is the shape of it: an input nobody writes was pinned as
correct because the two readings of the rules agreed about it, and "the two implementations agree" is
not the same claim as "the answer composes with everything downstream". The property that would have
caught it is now asserted directly — every ASCII token, upper-cased, splits back to exactly itself —
and it is the premise `normalize`'s idempotence rests on.
`test_an_ascii_token_upper_cased_splits_back_to_exactly_itself` is the name to search for.

### What this changes for existing callers, and what is still missing

`is_fully_known` means something narrower than it did. A caller gating on it will now see `False` for
names it previously waved through — which is the point, and is a behaviour change worth a release
note rather than a footnote. `unaccounted` defaults to empty, so a consumer that has never heard of
the field reads the same payload it always did.

The accounting is visible **in one direction only**. `expand_identifier` writes it;
`ComplianceResult` and `PhysicalName` carry no equivalent, so a character the splitter could not read
reaches `is_compliant` as a `NOT_UPPER_SNAKE` finding — or as nothing at all, when the rest of the
name is well formed — and reaches `to_physical_name` as nothing. That is a gap in the DTO surface
rather than a decision, and `GOVERNED_NAMING.md` records it in place so it is not mistaken for one.

One vacuous case stands and is left alone: `expand_identifier("")` returns `is_fully_known=True`,
because no token failed and nothing went unaccounted for. The empty `tokens` tuple is what says
nothing was expanded, and raising on a blank cell would push a `try` into every caller walking a
schema export.

---

## D-023 — pydantic is 84.6 % of the engine import. Migrate, and before the package is published.

**Status:** decided, not executed · **Evidence:**
[`notes/pydantic-cost.md`](notes/pydantic-cost.md)

D-013 ended with "Not attempted: moving the DTO layer off pydantic. That is a breaking change to the
public type surface and needs its own decision." This is that decision, and it is taken on a note
rather than on `bench/results.json` — see the last section, which is the reason to read the rest with
one eye half closed.

### How it was measured, because two confounds decided the answer

Windows 11 Pro (26200), CPython 3.13.4, `pydantic` 2.11.7 / `pydantic-core` 2.33.2. Medians over
fresh interpreters — 15 for import arms, 9 for steady-state arms — one arm and one metric per
interpreter, every (arm, metric) pair interleaved before any repeat.

Both restrictions are load-bearing rather than fastidious. Measuring the two arms in one process
produced a **reversed** result, because CPython 3.11+ specialises call sites per code object and the
second arm inherited call sites adapted to the first arm's classes. Measuring several metrics per
process let machine drift settle into the later ones, and the pydantic arm has an extra metric.

The counterfactual is end-to-end, not a projection. Every module on the generation path binds its
models with `from .models import X`, so rebinding those globals swaps the whole DTO layer for frozen
dataclasses without touching an algorithm — and the swapped engine emits an **identical payload**. A
third arm carries every `Field` constraint on that path in `__post_init__`; it costs 2.1 %, so this
is not pydantic measured against no validation at all.

| | pydantic | dataclasses, constraints kept |
|---|---:|---:|
| `from acronymkit import AcronymEngine` | 139.60 ms | — |
| — importing `pydantic` and its dependencies | 30.09 ms (21.6 %) | |
| — pydantic's one-time model-building machinery | 87.96 ms (63.0 %) | |
| — everything this library itself does | 21.55 ms (15.4 %) | |
| `import acronymkit.config`, pydantic already resident | 89.08 ms | 9.21 ms |
| warm `generate()`, `Config()` | 347.60 µs | 269.80 µs (−22.4 %) |
| warm `generate()` + `to_dict()`, `Config()` | 422.80 µs | 298.70 µs (−29.4 %) |
| installed footprint of the dependency stack | 7,573,125 B | — |
| wheel bytes downloaded to install it | 2,473,817 B | — |

**The largest single line item is not importing pydantic.** The first `BaseModel` subclass built in a
process costs 87.96 ms; the second costs 0.26 ms; a frozen dataclass costs 0.35 ms. That toll is
fixed and independent of how many models this library declares — one would cost what sixteen cost.
The 21.55 ms attributed to us is an upper bound, since roughly 7.6 ms of it is pydantic building
`models.py`.

### The counterweight was tested in both directions and does not save it

Asked for a Python dict, pydantic is **2.65× slower** than a hand-written walker (67.50 µs against
25.50 µs). Asked for JSON text, its Rust serialiser is **2.24× faster** than dict-then-`json.dumps`
(56.80 µs against 127.30 µs). End to end the two nearly cancel: `generate()` + `model_dump_json()` is
412.60 µs against 406.20 µs for the dataclass arm. Pydantic loses by 1.6 %, which is a tie.

Two by-products worth keeping whichever way the decision goes:

- `_Frozen.to_json` takes the slow half of both worlds. It is `json.dumps(self.to_dict(), ...)`,
  169.40 µs, where `model_dump_json()` produces the same document in 56.80 µs — **2.98× on a public
  method**. The text differs only in separators, and `json.dumps(payload, separators=(",", ":"))`
  reproduces the Rust output byte for byte, so it is a small and declarable break.
- `model_construct()` is **slower** than validating construction (236.70 µs against 180.80 µs).
  "Keep pydantic, skip validation in the hot path" is therefore not an available option.

An earlier measurement, cited in the phase-4 mandate, put `generate` + `to_dict` about 30 % *slower*
under dataclasses. Nothing in this repository records it, so it could not be inspected before being
contradicted at the same magnitude and the opposite sign. If it exists elsewhere, the in-process arm
ordering described above is exactly the method that produces that reversal.

### The portability argument for migrating is wrong and is not being used

The mandate's premise included "works anywhere". **That part does not survive contact with PyPI.**
`pydantic-core` 2.33.2 publishes 98 wheels across 20 platform tags — musl on x86-64/aarch64/armv7l,
glibc on s390x/ppc64le/armv7l/i686, Windows on ARM, both macOS architectures — for CPython 3.9–3.13
and PyPy. The current release adds riscv64, Emscripten and GraalPy. Alpine, ARM and s390x are
covered; anyone migrating for portability alone is migrating on a misconception.

What remains is a long tail with a severe failure mode. No wheel means the sdist, whose build backend
is `maturin>=1,<2` with `rust-version = "1.75"` and 93 packages in `Cargo.lock` — a Rust toolchain
plus reachable crates.io, neither of which the hash-pinned offline wheelhouse of `docs/OFFLINE.md`
can supply. `acronymkit`'s own wheel is `py3-none-any` and installs anywhere Python runs; its
dependency decides where it actually can. The narrower gaps are real: musl on three architectures
only, no BSD/illumos/AIX ever, three wheels for free-threaded 3.13t, `win_arm64` only from cp311, and
`pydantic-core` 2.48.0 declares `requires-python >=3.10`, so this project's 3.9 floor is being
dropped upstream (fine today — `pydantic` 2.13.4 pins core 2.46.4, which still has cp39 wheels).

### The migration is smaller than D-013 assumed, and the reason is a surprise

`schemas/acronym-engine-result.schema.json` is **hand-written, not generated**. It differs from
`export_model_schema()` in title, `$id`, `$defs` and `required`, and that function exists to *diff*
against the contract rather than to produce it. So the cross-language interchange contract — the
thing that keeps the `acronym4j` port possible, and the reason D-013 called this risky — does not
depend on pydantic at all. The swap experiment then demonstrated it by emitting an identical
document.

The rest of the surface is small: 16 `BaseModel` subclasses, 136 fields, 27 constraints (26 range
bounds and one length bound), one `computed_field`, one cross-field validator, no aliases, no custom
`field_validator`, no discriminated unions. 44 of 930 test functions touch a pydantic API.

### Decision

**Migrate to dataclasses with explicit validation, and do it before the package is published.** The
decisive fact is not a measurement: PyPI returns 404 for the name, because D-001 cut publishing
deliberately. Every breakage listed below is a cost paid by users who do not exist yet, and that cost
rises monotonically from the first successful `pip install`. A 22.4 % steady-state regression is also
far larger than the differences that got seven experiments in this file reverted; applying the same
standard to a dependency rather than only to our own code gives one answer.

**Rejected: optional pydantic with a stdlib fallback.** Not on cost — it is the only option that
makes the public type surface a function of what else is installed. `isinstance(result, BaseModel)`
and `result.model_dump()` would work or not depending on whether an unrelated package pulled pydantic
in. For a project shipping an air-gap review document, that is worse than either fixed choice.

**Keeping pydantic remains defensible.** Hand-written validation is where bugs live, and these DTOs
are the public contract. What is not defensible is keeping it silently: the honest form of that
option requires `docs/ARCHITECTURE.md`'s "Pydantic is a hard dependency, but nothing else is" to
carry the import attribution and the platform gaps beside it.

### What breaks, and in what order it should be done

Breaks: `model_dump()`, `model_dump_json()`, `model_validate()`, `model_copy()`, `model_fields` and
`model_json_schema()` on 15 public classes — `model_copy(update=...)` is recommended in `models.py`'s
own module docstring, so it is a documented promise; `isinstance(result, pydantic.BaseModel)`, which
is how a DTO reaches a FastAPI `response_model` and is not shimmable; `export_model_schema()`, which
has no meaning without pydantic; constructor coercion (`"3"` → `3`, `5` → `5.0`, `list` →
`frozenset`, `str` → `Path`, none of them documented); and constraint enforcement moving from "always,
at construction" to wherever `validate()` is called. Enum coercion gets *wider* rather than narrower,
since `_StrEnum.coerce` already accepts names, mixed case and hyphens where pydantic accepts only the
exact value. `model_dump` and `model_copy` are three-line shims and should live for one minor
release.

One consequence is easy to miss: the `pydantic` entry-point plugin hole disappears, and with it
`_enforce_offline`'s plugin check, the `OfflineError` it raises, and `docs/OFFLINE.md`'s only
"detection, not prevention" caveat.

Order: (1) land the `to_json` → `model_dump_json()` change on its own, because it is a win if
pydantic stays and wasted if it goes, which is what keeps the decision honest should the migration
slip; (2) migrate `models.py` alone — it carries 10 of the 27 constraints and all of the
serialisation, while `config.py` carries the other 17 and all of the coercion; (3)
`python bench/run_micro.py --save --only import` after each half, and stop if the import figure does
not move as predicted, which is the rule that reverted the other seven experiments; (4) migrate
`Config`, routing enum coercion through `_StrEnum.coerce`.

### Noticed in passing, not fixed

Assigning to a frozen field raises raw `pydantic.ValidationError`, not an `AcronymKitError`.
`config.py` takes real trouble to unwrap validation errors at *construction* so that one
`except AcronymKitError` at a service boundary catches everything; the assignment path leaks around
it. Pydantic is already visible in the public error surface in a way the docstrings say it is not.

### What this record is not

**None of these figures is gate-backed.** Nothing was written to `bench/results.json` and no arm was
added to `bench/run_micro.py`, deliberately: the comparison arm is a throwaway shadow DTO layer, and
a runner that benchmarks code the project does not ship is dead weight the moment the decision is
executed. The consequence is that these numbers must not escape into user-facing prose, where the
claims gate could not check them. They are one machine, one operating system, one interpreter, and
session-to-session drift on that machine is larger than several of the differences being attributed:
`from acronymkit import AcronymEngine` measured 134.7, 139.6, 150.4 and 154.7 ms across four sessions
on the same day, against the 128.1 ms in `bench/results.json`. Only ratios carry the argument, which
is why the whole import table comes from one interleaved session and `bench/results.json` remains the
figure of record.

The shadow covers the generation path only — 6 of the 15 public classes and only the fields those
classes carry. Extraction, backronym, disambiguation and batch results were never shadowed, so a real
migration is larger than what was priced. And no effort estimate in the note comes from a
measurement; "mechanical" is a judgement sized from the inventory.

---

## D-022 — The buyer-facing pair, and how to measure around a tier the host cannot run

**Status:** shipped · **Evidence:** [`ENTERPRISE.md`](ENTERPRISE.md),
[`SUPPORT_MATRIX.md`](SUPPORT_MATRIX.md)

`docs/OFFLINE.md` answers a security reviewer. It does not answer the two people who arrive before
one: the manager deciding whether the package may be installed at all, and the engineer asking
whether the capability they need survives an air gap. Folding those into OFFLINE.md would have made a
41 KB document longer and served none of the three readers better. So `ENTERPRISE.md` is the
decision, `SUPPORT_MATRIX.md` is the capability detail, `OFFLINE.md` stays the method; each links the
other two and none restates them.

### The problem the matrix ran into

`SUPPORT_MATRIX.md` has four tier columns and the measurement host could run exactly one. spaCy is
not installed; NLTK is installed with no `averaged_perceptron_tagger` corpus.

Three options. **Download a model** — rejected: a network fetch made on a user's machine to make a
document look more complete is the wrong trade in a repository whose whole discipline is that a
number is either measured or absent. **Train a perceptron tagger locally on a hand-made corpus** —
rejected for a worse reason: it produces *real* measurements of a *fabricated* backend, which reads
as evidence and is not. **Mark the Tier 1 columns unknown** — rejected as needlessly weak, because
most of what a reader needs about Tier 1 is measurable without a tagger.

What was done instead is to split each Tier 1 cell along the line the host can actually see. Which
backend resolves, what is raised when it cannot, what warning is emitted, and *whether the annotator
is consulted at all* — measured. The content of a real tagger's output — not measured, said so in the
cell, with the six `nlp`-marked assertions that do cover it named by full node id and the note that
all six skipped here. A reader who needs that evidence now knows which command produces it.

### The measurement that made the rest of the matrix decidable

Wrapping the resolved backend's `annotate()` with a counter and driving each public method once:

```
tokenize 1 · generate 1 · score 1 · generate_backronym 1 · agenerate 1
batch_generate 2 · abatch_generate 2
synthesize_backronym 0 · extract_definitions 0 · extract 0 · disambiguate 0
```

A method that never consults the annotator cannot be changed by which annotator was resolved. That
turns four of the eleven rows from "presumably the same at Tier 1" into "the same code, and the tier
changes only the metadata envelope" — cheaply, on a host with no Tier 1 runtime at all. It also
answers plainly a question the docs had never answered: **installing spaCy does not improve
extraction or disambiguation.** That is worth knowing before an image admits that dependency closure.

The general rule is the part worth carrying: when you cannot run the configuration you are
documenting, look for the property of the *call graph* that makes the configuration irrelevant. It is
often measurable when the configuration is not.

### Two claims deliberately narrowed

**"No compiled extension"** would have been false as written. `acronymkit`'s own wheel is
`py3-none-any` with `Root-Is-Purelib: true` and no `.so`/`.pyd`/`.dll`/`.dylib` among its entries —
but `pydantic-core` is a base dependency and does ship a compiled Rust extension. The row states both
in the same breath and says the consequence out loud: a "no binaries in the image" policy is a policy
against pydantic, not against this package. A reviewer who discovers that unaided, after reading a
page that did not mention it, discounts everything else on the page.

**"No `pickle`"** was narrowed the same way. `src/acronymkit/` imports no `pickle` and calls none, and
the word appears twice, both in comments — but the result DTOs are pydantic models and are therefore
picklable if a caller chooses, which
`tests/test_package.py::test_results_and_config_survive_a_pickle_round_trip` exists to prove. The
honest claim is about what the library does, not about what its types permit.

### The suite total is not quoted, on purpose

Both documents originally carried a pass count. It moved from 3,392 to 3,395 to 3,423 during the
hours they were being written, while other work landed on the same tree. Both now report "green, 10
skipped" and say why the total is omitted. The 10 is the load-bearing figure: those skips are exactly
the Tier 1 real-backend tests, so the skip count is a structural consequence of the host rather than
an accident of the day. This is OFFLINE.md section 9's own lesson — on an unpinned tree, a test count
is a timestamp — applied one step earlier, by not writing the number down.

### Left open

`docs/INSTALL.md` did not exist when these two pages were finished, so `ENTERPRISE.md` carries a
conditional forward reference to it rather than duplicating install mechanics. D-021 has since landed
that file, and the reference reads correctly; what is still missing is a link from `README.md` and a
sibling cross-reference from `docs/OFFLINE.md`.

`--require-hashes` is documented in `ENTERPRISE.md` and labelled as an operator step CI does not
exercise, because the `air-gap` job tests `--no-index --find-links` and nothing here tests hash
pinning. Presenting the two as equally proven would have been the error these pages exist to prevent.

Neither Tier 1 column is fully measured, and that is the single largest limitation of the deliverable.
`SUPPORT_MATRIX.md` carries a "What is not measured here" section naming the six skipped tests where
that evidence lives; filling the columns means staging a spaCy model or `averaged_perceptron_tagger`,
re-running those six, and re-deriving the tokenisation and scoring rows. One string in
`ENTERPRISE.md` — spaCy's "model not installed" message — is quoted from source rather than from a
run, because it cannot be produced on a host without spaCy, and the sentence after it says so. Every
other quoted failure message came from an actual run.

---

## D-021 — Installable without PyPI: per-platform bundles, and the checks that make them worth trusting

**Status:** shipped · **Evidence:** `tools/make_offline_bundle.py`, [`INSTALL.md`](INSTALL.md),
`.github/workflows/publish.yml`

PyPI is a single point of failure this project's users do not control, and D-001 cut publishing
anyway, so for now it is the *only* point of failure that does not exist yet. The release page now
carries a complete alternative: wheel, sdist, an offline install bundle per platform, both SBOM
formats, and one `SHA256SUMS` covering all of them. What follows is the decisions inside that, and
the two bugs found by taking them seriously.

### Per-platform bundles, with the target in the filename

`pydantic-core` is a compiled Rust extension published as one wheel per (CPython minor × operating
system × architecture × libc), and it is not `abi3`, so it does not even carry across CPython minor
versions. A single universal bundle is therefore impossible, and the alternative — one bundle whose
target is implicit — is worse than no bundle, because it fails on the user's machine rather than on
ours.

So: seven declared targets (`linux-x86_64`, `linux-aarch64`, `linux-musl-x86_64`, `macos-arm64`,
`macos-x86_64`, `windows-amd64`, `windows-arm64`), each named in the archive filename, each carrying
one `pydantic-core` wheel per CPython minor version it serves. `--target host` is the escape hatch for
anything outside the registry: it passes no `--platform` to pip at all, so the running interpreter's
own tag set — the ground truth a hand-written platform tag can only approximate — decides what is
downloaded.

**`windows-arm64` serves CPython 3.11 to 3.13 and not 3.9 or 3.10, and how that was discovered is the
part to keep.** `pip download pydantic-core --platform win_arm64 --python-version 3.9` does not fail.
It resolves all the way back to a `0.0.1` placeholder release and reports success, leaving a bundle
that installs a package containing nothing. Rooting every download at `acronymkit[cli]==<version>`
closes it, because pydantic pins its core with `==` and pip then has no version to backtrack to: the
same request becomes a loud `ResolutionImpossible`. The narrowing is written into the target registry
so nobody rediscovers it from a bug report.

The same trap explains why `linux-musl-x86_64` names several tags: `--platform` disables pip's
automatic tag-compatibility expansion, so `musllinux_1_2_x86_64` alone matches nothing even where
`musllinux_1_1` wheels would install. Each target lists its tags least-demanding first, because pip
treats the order as a preference and the wheel with the lowest platform floor runs on the most
machines.

### The bundle is re-resolved offline, not merely assembled

A directory of wheels somebody hoped were the right ones is not a bundle. After staging, every
archive is re-resolved with `pip install --dry-run --no-index --find-links=<bundle>`, once per served
interpreter, twice over — the documented install command, and the hash-pinned requirements file — and
the build fails if any resolution does not succeed. A dependency that stops publishing a wheel for a
declared target therefore breaks a release, loudly, rather than breaking an air-gapped install six
months later.

### Two bugs found by taking the checks seriously

**pip evaluates requirements-file markers against the running interpreter, not against
`--python-version`.** A bundle spanning CPython 3.9 to 3.13 genuinely contains several versions of
some dependencies — `annotated-types` 0.7.0 for 3.9 and 0.8.0 above it — and one `requirements.txt`
expresses that with disjoint `python_version` markers. Asked to dry-run a 3.9 target from a 3.13
host, pip reported `Ignoring typing-inspection: markers 'python_version == "3.9"' don't match your
environment` and then failed on a `Requires-Python` conflict it had created itself. `--python-version`
governs wheel selection and `Requires-Python`; requirement markers are evaluated against the
interpreter actually running. That is not a defect in the shipped file — a user installing into an
interpreter always runs pip under it — but it makes the file uncheckable cross-target, so the build
pre-evaluates markers per interpreter for its own verification and exercises the shipped file only
for the interpreter it is running on.

**`Path.write_text` translates `\n` to `\r\n` on Windows, and `sha256sum -c` reports every line of a
CRLF file as a *missing file*** — it looks for a name ending in a carriage return. The bundle's own
README tells the reader to run that command, so every bundle built on Windows would have shipped a
verification step that failed completely on the machine it was aimed at, and the bundle's `verify.py`
would not have caught it, because `splitlines()` absorbs the difference. All generated text is now
written with an explicit `newline="\n"`.

That second one is D-018's lesson in another costume: **measure the artefact, not your copy of it.**
The artefact is for someone else's machine, so its line endings are a property of the artefact rather
than of the machine that produced it.

### SBOMs from two tools, for two different reasons

CycloneDX comes from `cyclonedx-bom==7.3.1` run against a `--without-pip` virtual environment holding
only the built wheel: an SBOM of this distribution should list this distribution's dependencies, and
an ordinary venv also contains pip, which would appear as a component of a library that does not
depend on it.

SPDX comes from `anchore/sbom-action`, pinned by commit SHA with `syft-version` pinned too. The Python
alternative, `sbom4python`, was tried and rejected on availability rather than preference: it reaches
`libmagic` through `python-magic` and does not run on Windows at all, and choosing a tool a maintainer
cannot execute locally is a choice never to check its output by hand.

Because the SPDX step cannot be run locally, a step that can was added: both documents are parsed and
asserted to name `acronymkit` as the root component and to list `pydantic`, `pydantic-core` and
`typing-extensions`. An SBOM generator pointed at the wrong directory produces a valid, well-formed
document describing nothing, and a release asset that is valid and empty is worse than a missing one,
because it reads as evidence.

### Signing and writing are separate jobs

`attest` holds `id-token: write` and `attestations: write` and cannot write to the repository;
`release-assets` holds `contents: write` and holds no signing identity. Neither can do the other's
damage, and `release-assets` runs after `attest`, so nothing reaches the release page without
provenance. The attestation covers `subject-checksums: release/SHA256SUMS` — the same file the release
publishes — so the set of attested artifacts and the set of published digests cannot drift apart,
because there is only one list.

### What is not solved, and what is not proven

spaCy and NLTK **models**. A wheel bundle solves distributions; language data is not a distribution.
The library does not paper over it — it raises rather than fetching — and `docs/INSTALL.md` gives the
two separate recipes, including the measured detail that NLTK 3.10.2 rejects its own `-d <directory>`
flag with `Security Violation ... Unauthorized path` and needs `NLTK_DATA` instead.

Nothing in `publish.yml` has been executed. Every action is pinned by SHA and every pinned action's
input names were checked against its `action.yml` at that SHA, and the local equivalents of the shell
steps were run — version extraction, the `SHA256SUMS` block verified afterwards with `sha256sum -c`,
the SBOM assertion against real CycloneDX output including its failure path, the `--without-pip`
install. What was not run: the `anchore/sbom-action` step, `gh release upload`, and the attestation
step. **Treat the first release under this workflow as the real test.** `gh attestation verify` has
never returned a success here — run against the current release wheel it correctly returns HTTP 404
for the digest — and `docs/INSTALL.md` says so in place rather than implying the check works today.
The PEP 740 section is likewise documented and not demonstrated: `pypi-attestations` could not
complete on this host, failing to refresh Sigstore's TUF trust root for a local and unidentified
reason.

Three costs accepted rather than solved. The seven bundles total roughly 78 MB per release and add
several minutes plus a comparable download to every publish run; `--all` fails the whole release if
any single target loses upstream wheel coverage, which is deliberate, since a silently skipped target
is the failure mode the design exists to prevent, but it does make releases depend on other people's
publishing decisions; and the `colorama` wheel is staged into every bundle including the Linux ones,
because a cross-platform `pip download` cannot evaluate `platform_system == "Windows"`. It is pure
Python and inert off Windows, it is named in the manifest, and both the module docstring and the
generated README say so.

`DEFAULT_PYTHON_VERSIONS` mirrors the classifiers in `pyproject.toml` as a constant with a comment
rather than a value derived from it, because deriving it needs `tomllib` and this project's floor is
3.9. If the project starts claiming 3.14, that tuple must be updated or the bundles quietly
under-serve.

---

## D-020 — There is no permissively-licensed source of expansion frequency counts. Ten were checked.

**Status:** closed as unavailable; one route costed and blocked on the wheel · **Evidence:**
`tools/fetch_data.py`, `data/LICENSES.md`

D-015 ended by naming a frequency prior as the obvious next experiment, because always picking the
most common expansion scores 72.84 where our context scorer scores 41.65. The gap is real. This entry
records that the fix is unavailable, and that the unavailability is a licence fact rather than an
engineering one.

| Source | Has counts | Licence | Fails on |
|---|---|---|---|
| SDU@AAAI-21 `train.json` | yes | CC BY-NC-SA 4.0 | non-commercial **and** share-alike |
| ADAM | yes | non-commercial, no redistribution | *"you will not distribute the software to anyone else"* |
| NLM SPECIALIST `LRABR` | **no** | permissive (US Government terms) | five fields, none of them a count |
| UMLS Metathesaurus | not established | UMLS licence agreement | per-user agreement; constituent vocabularies keep their own copyrights |
| MSH WSD | capped per sense | UMLS licence agreement | *"cannot be redistributed"* |
| CASI (UMN) | yes | mixed | aligned to UMLS, ADAM and Stedman's; inherits all three |
| MED1250 | yes | public domain | too sparse to carry a prior |
| Ab3P `SingTermFreq.dat` | yes | public domain | the wrong statistic |
| Wikipedia / Wiktionary | senses, not counts | CC BY-SA 4.0 | share-alike bars the corpus *and* anything derived from it |
| PLOD-CW | no | CC BY-SA 4.0 | span annotation; no expansion frequency at all |

Three of those deserve a sentence, because two look like the answer and the third is the one already
on disk.

**`LRABR` is permissive and large and has no counts.** NLM's own field documentation gives it five
columns — `EUI`, `BAS`, `ABR`, `EUI`, `BAS` — identifiers and surface forms, nothing statistical. It
can tell you that `DM` expands to `diabetes mellitus`; it cannot tell you that it usually does, which
is the entire content of a prior. Stated with its limit: the file could not be re-fetched for this
audit, because `lsg3.nlm.nih.gov` answers HTTP 403 to an unauthenticated client on both HEAD and
ranged GET, so the column list comes from NLM's published table definition rather than from bytes on
disk. That settles the question asked here — a column absent from the specification is absent from
the file — but the row count and coverage figure recorded previously are deliberately **not** repeated
as though they had been re-measured.

**`SingTermFreq.dat` is public domain, is a frequency table, and is still the wrong one.** It is
`word|count` over MEDLINE, 30,991,015 bytes:

```
'lacz|10
's|1912
000bp|4
```

It answers "how common is this word", not "which expansion of this short form is meant here". D-012
wanted it for per-candidate extraction evidence and that remains open; it is no help to
disambiguation.

**MED1250 has counts and they are empty of information:**

```
gold pairs                                                1221
distinct short forms                                      1010
short forms occurring exactly once                         867
short forms with more than one distinct expansion     76 of 997
```

Nothing was shipped and nothing was invented. That is the deliverable.

### The one route that clears the licence bar, costed

**Derive the counts ourselves from the PMC Open Access commercial-use collection.** Every article in
it carries a machine-readable CC BY or CC0 licence, neither share-alike, and CC BY permits Adapted
Material under other terms provided attribution is given — an MIT wheel with a corpus-level notice,
exactly the shape `lexicon_en.txt` already has for SCOWL. Measured against the 2026-06-17 baseline on
the NCBI FTP host:

```
oa_comm plain-text baseline packages                          14
total compressed                                        ~80.6 GB
per-article licence column in the shipped filelist.csv       yes
licence mix, 30,546-article sample of the two smallest ranges
  CC BY                                                   28,285
  CC0                                                      2,261
  anything else                                                0
```

Four things stand between that and a shipped prior, in order of how likely each is to stop it:

1. **The output must fit the wheel, and that is the binding constraint** — not the licence, not the
   compute. Headroom today is 113,269 bytes and SDU-21's own candidate dictionary is 76,910 bytes for
   732 acronyms, so a prior scoped to a comparable inventory fits and a general one does not. A prior
   that ships is therefore a prior that has already decided which acronyms it covers, and nobody has
   proposed how.
2. **The compute is not measured.** 80 GB, once, by a maintainer, with our own Schwartz & Hearst
   matcher run over full texts rather than abstracts. Nobody has timed that, so it is recorded as
   untimed rather than guessed at. It is not what would stop this.
3. **The pin has a deadline.** PMC retires this FTP service on 24 August 2026 in favour of an
   AWS-hosted distribution, so the pinned-URL-plus-digest pattern `tools/fetch_data.py` relies on has
   to be re-established against the new host.
4. **Attribution at corpus scale.** CC BY 4.0 permits attribution by reference to a resource, so
   citing the collection and shipping the filelist reference is workable — but it is a term of the
   grant rather than a courtesy, and the wheel would carry an obligation it does not carry today.

**Open, with a precondition:** worth doing only if item 1 is answered first. Downloading 80 GB to
build a table that cannot ship is D-016's mistake one order of magnitude larger.

---

## D-019 — A reliability table now ships. `Lf1chSf` was measured, helps, and was refused.

**Status:** table shipped, `Lf1chSf` rejected · **Evidence:** `tools/build_reliability_table.py`,
`src/acronymkit/resources/pseudo_precision_en.json`, `tests/test_pseudo_precision.py`,
`data/LICENSES.md`

### The table

D-012 closed pseudo-precision as a *selection* mechanism and kept it as *calibrated confidence*.
Calibrated confidence still cost the user a corpus: `estimate_precisions` was the only route to a
table, so an air-gapped installation had an estimator and nothing to put in it.
`acronymkit/resources/pseudo_precision_en.json` is that table — loadable with
`_pseudo_precision.bundled_table()`, used automatically when `best_alignment` is called without one,
and `estimate_precisions` is untouched and remains the documented route for anyone with text.

**Which corpus, and may we?** The estimator reads raw text, so a derived table inherits that text's
licence. Two of the three corpora on disk are barred: SDU-21 is CC BY-NC-SA (D-015), and PLOD-CW is
CC BY-SA whose section 3(b) reaches Adapted Material (D-017). MED1250 is a United States Government
Work whose notice places no restriction on use or reproduction, so it is the one that can be used.

**Ab3P's published `Ab3P_prec.dat` was therefore not needed as the shipped table, and would not have
worked as one.** It is keyed by Ab3P's seventeen rule names; our matching rules are a parameterised
family with names of their own, so every lookup would miss, and bridging the two taxonomies means
inventing a mapping no measurement backs. It is registered and fetched as the `--cross-check`
yardstick instead, which compares our derived *spread* per bucket against Ab3P's — only the spread,
because a rule-against-rule comparison at the bottom of the range is the error D-010 already
corrected. The buckets with real support agree and the thin ones do not:

```
group     ours max  ours min  Ab3P max  Ab3P min   rules ours/Ab3P
al:3        1.0000    0.5221    0.9998    0.3035          30/15
al:4        1.0000    0.6835    1.0000    0.6965          30/15
al:5        1.0000    0.7273    1.0000    0.7386          30/15
num:4       1.0000    0.9630    0.9999    0.9531          30/13
spec:5      1.0000    0.7500    0.9999    0.7456          30/13
al:1        0.8000    0.0000    0.9672    0.9672           30/1
spec:2      0.1667    0.0000    0.8544    0.6575           18/3
```

A second, independent argument backs the licence reading, and it is the one that survives if the
reading is ever disputed: **the shipped table contains no text from the corpus.** Every key is one of
our own short-form group labels or one of our own strategy names; every value is a count or a float.
`tests/test_pseudo_precision.py` asserts that rather than trusting it.

**Which half.** The development half only, under `bench/run_cascade.py`'s frozen split seed, imported
from that module rather than copied. Deriving from the whole corpus would have been easier and would
have poisoned every MED1250 figure this project publishes. Because it is the dev half, the shipped
table *is* the table D-010's sweep describes: driving `predict_cascade` from the file reproduces that
recorded run, 85.43 / 74.56 / 79.63 at no abstention through 91.62 / 72.97 / 81.24 at 0.90, and
rounding the estimates to six decimals changes no strategy ordering in any bucket.
`tools/build_reliability_table.py --check` rebuilds the table from the fetched corpus and diffs it
against the shipped bytes, which is how a hand edit is caught.

**What it is not.** A prior on English biomedical prose, not a calibration for the reader's domain,
and how far it transfers is unmeasured. The docstring says so; the JSON says so in a provenance block
— JSON has no comment syntax, so the header every other bundled resource carries is data here — and
`bundled_table_provenance()` puts the source URL, digest, licence and split seed in reach at run time.

Bundling exposed a latent defect and it is the kind worth recording. `PrecisionTable.ordered()` did a
bare `strictness[name]` lookup, so a table written by a build with a since-renamed strategy raised
`KeyError` from inside a sort key. That could not happen while every table was built in the same
process that consumed it; it becomes possible the moment a table arrives from a file, so tables and
the strategy family are versioned separately now.

### `Lf1chSf` helps by a fifth of a point, on a corpus it is probably contaminated by

Public domain, 48,126 bytes, 4,991 lower-case words consumed as a set. Ab3P's `FirstLetOneChSF` uses
it to gate the head word of a one-character short form's definition (D-010's correction). Applied the
same way, as a post-filter over one-character predictions:

```
MED1250, exact match          P %     R %    F1 %    TP    FP    FN
--------------------------------------------------------------------
full corpus, 1,221 gold
  default (min length 2)    92.07   76.99   83.85   940    81   281
  min length 1, no gate     90.47   78.54   84.09   959   101   262
  min length 1, gated       91.32   78.38   84.35   957    91   264
test half, 629 gold
  default (min length 2)    92.32   76.47   83.65   481    40   148
  min length 1, no gate     91.11   78.22   84.17   492    48   137
  min length 1, gated       91.93   77.90   84.34   490    43   139
```

It works — the gate removes 12 of 41 one-character predictions, 10 of them false positives — and the
larger move is admitting one-character short forms at all, not the gate.

The reason it is not shipped is the control measurement:

```
share whose head word is in Lf1chSf
  MED1250 one-character gold definitions      21 /    23  = 91.3 %
  MED1250 multi-character gold definitions   591 /  1198  = 49.3 %
  MED1250 distinct word types               2938 / 19215  = 15.3 %
```

A general biomedical word list has no reason to be twice as dense on exactly the pairs it is meant to
help. Ab3P's gold standard *is* MED1250 and the same authors built both, so the list overlaps the pool
MED1250 was drawn from, every figure in the first block is an upper bound of unknown tightness rather
than an estimate of what a user's corpus would see, and a fifth of a point resting on evidence that
leaky does not buy a permanent 48 KB resource. Registered, pinned, checksummed and fetch-only,
following the med1250 precedent; the note in `data/LICENSES.md` records plainly that **the licence was
never the objection** — the same public-domain notice covers it, and it would have fitted the budget.

### A registry field that used to be answered from memory

`Asset` gains `derivable`: may a resource *derived* from this asset ship, when the asset itself may
not? It comes apart from `vendorable` in both directions — MED1250 is public domain and fetch-only for
size alone, PLOD-CW is freely redistributable and taints anything derived — and
`tools/build_reliability_table.py` enforces it the way `tools/build_lexicons.py` enforces
`vendorable`. It denies by default, because an asset added without a licence reading must not silently
become the source of a shipped resource; a wrong `True` is how share-alike gets into an MIT wheel.
`Asset` also gains `size_bytes`, recorded rather than read from `data/`, so the ledger says the same
thing on a machine that has fetched nothing and the wheel budget can be argued from the registry.

`data/LICENSES.md` is regenerated with source URL, pinned commit, licence, SHA-256, size and
vendor-or-derive reasoning for all 20 assets, plus a new section covering the three derived files that
actually ship in the wheel.

### Costs and limits

The wheel is 411,019 bytes of the 524,288-byte budget (78.4 %), leaving 113,269 bytes; the new
resource is 34,096 bytes on disk and costs 3,779 compressed. The figures in the two code blocks above
are **not** in `bench/results.json` — no bench runner writes them — so they live here and in
`data/LICENSES.md` and nowhere a claims gate can check them. If they should become citable, a runner
has to be written. And `tools/build_reliability_table.py --check` is not wired into CI, because the
check needs a fetched MED1250 and the `resources` job fetches no corpora; today only a maintainer
running it locally catches a hand-edited resource, while `tests/test_pseudo_precision.py` carries the
weaker corpus-free half.

---

## D-018 — `load_schema()` read from directories this package does not own

**Status:** fixed, shipped · **Evidence:** `src/acronymkit/serialization.py`,
`tests/test_serialization.py::test_schema_path_points_at_the_checkout_copy`

`load_schema()` used to look for `acronym-engine-result.schema.json` in a `schemas/` directory under
two ancestors of the package directory — `parents[1]` first, then `parents[0]` — falling back to the
copy bundled in `acronymkit.resources` only if neither was a readable file. In a checkout those two
are `<repo>/schemas/` and `<repo>/src/schemas/`: the developer's own files. In an installed wheel
they are `<venv>/Lib/schemas/` (`<venv>/lib/pythonX.Y/schemas/` on POSIX) and
`<site-packages>/schemas/`.

Three facts turn that from untidy into a supply-chain hole:

- This package owns neither directory, and a file placed in either carries no hash in any
  distribution's `RECORD`. Such a file is not a modified `acronymkit`; it is a document
  `acronymkit` chose to prefer over its own.
- Either directory can be created by a dependency. Any distribution that ships a top-level
  `schemas` package materialises `<site-packages>/schemas/` on install, and that is the candidate
  reached whenever the first one is empty, which is the ordinary case. Owning it on a target
  machine therefore does not require write access to the machine — it requires one line in a
  requirements file. (The distribution name `schemas` is already taken on PyPI by an unrelated
  validation library, so an attacker would publish under some other name. That costs nothing: the
  directory a distribution creates has no connection to the name it is installed under.)
- A JSON Schema may carry a remote `$ref`, and `jsonschema` resolves those by fetching them.

The audit ran the chain end to end. A planted schema was returned by `load_schema()` in preference
to the bundled copy; `jsonschema` then made a real outbound HTTP GET to resolve the remote `$ref`;
and `validate_result` reported the attacker's document as valid. A library that authors no network
code of its own issued a request to a host chosen by whoever populated that directory.

### Resolution

The search is gone. `load_schema()` reads the bundled resource and nothing else — the same document
in a checkout, a wheel and an sdist, and once installed it carries a hash in the distribution's
`RECORD` like every other packaged file. `SCHEMA_PATH` still names the checkout copy, because the
tooling and the planned `acronym4j` port need something to point at, but no load path consults it.

The second half is a refusal rather than a statement about today's file: `_remote_refs()` walks the
decoded schema and `validate_result` raises `AcronymKitError` if any `$ref` names a remote scheme.
"Our schema happens to contain no remote reference" is an accident, and `validate_result` is the
place where an accident would have become a request.

### The second-order finding, which is the more useful half

The invariant that the two copies agree was never actually being checked. It was asserted by

    assert json.loads(SCHEMA_PATH.read_text(encoding="utf-8")) == load_schema()

and under the old lookup `load_schema()` preferred `SCHEMA_PATH`, so that line compared the checkout
copy with itself and passed unconditionally. Removing the search is what gave the assertion a
second operand; the line is unchanged and now genuinely cross-checks the two copies.

**CORRECTION, and it is a correction of this file's own first draft.** That draft said the two
copies "had already drifted", citing 6,569 bytes against 6,408. They had not. Both blobs are 6,408
bytes in git with the same SHA-256, and have never differed. The 161-byte gap was 161 CRLF pairs in
a Windows working copy under `core.autocrlf=true` — an artefact of the machine the measurement was
taken on, not a property of the repository. `git show HEAD:<path>` for both paths returns identical
bytes, which is the check that should have been run before the claim was written.

The irony is the point. This entry is about a lookup that could not see what it was falling back
to, and the first draft of it reported a difference that existed only in the observer's checkout.
**Measure the artefact, not your copy of it** — for line endings that means comparing git blobs or
normalising first, and it is the same class of error as trusting a stale `dist/`.

**A lookup with a fallback cannot be used to test the thing it falls back to.** That is the rule
worth carrying forward, and it is not specific to schemas.

---

## D-017 — A second corpus at last, and it is not the corpus the roadmap promised

**Status:** measured, shipped unchanged · **Evidence:** `spans.plod.*` in `bench/results.json`,
`bench/run_spans.py`, `bench/corpora.py:read_plod_cw`

Every extraction number in this project came from MED1250. PLOD was named in three places as the
counterweight — `bench/splits.toml` reserved a slot for it, `docs/EVALUATION.md` called it "the
natural counterweight", D-001 listed it beside Ab3P. It has now been fetched, read and scored, and
the first thing to record is that **the premise was wrong**.

### Correction: PLOD is not the non-biomedical corpus this project has been waiting for

`bench/splits.toml` files PLOD as the "non-biomedical counterweight". The dataset card says
otherwise, and so does the text. PLOD is built from PLOS journal articles and its own summary calls
it scientific-domain; the test split is dominated by life-sciences prose — SDS-PAGE gels, shRNA
knockdowns, eicosapentaenoic acid, `p53`. A handful of sentences are not (`VIP, ventilated improved
pit`), and that is a handful.

So PLOD is a genuinely different **corpus**, **genre** (article body text rather than abstracts),
**annotation provenance** (semi-automatic, from PLOS's own abbreviation index, versus manual NLM
annotation) and **task**. It is not a different **domain**. The domain-generalisation question —
how does an extractor whose defaults are tuned for general prose behave on legal, financial or
general-web text — remains open, and nothing below answers it. Claiming otherwise would be the
easiest and most damaging sentence in this file.

`bench/splits.toml` should be corrected on that point; the entry is not mine to edit here.

### The task is different, and that decides everything else

PLOD is BIO token classification. It tags abbreviation spans (`B-AC`) and long-form spans
(`B-LF`/`I-LF`) and never pairs them. `bench/splits.toml` already ruled that deriving pairs from
adjacency would make part of the gold standard ours, and a gold standard we partly invented cannot
adjudicate our own system. That stands, so nothing was derived. The harness scores PLOD's own task:
short-form span detection and long-form span detection, two separate scores, no pairing.

The second difference is larger than the first and it is not a defect in either corpus. **PLOD tags
every mention; we return every definition.** `SDS` is tagged in "a discontinuous SDS gel" with no
expansion in sight, `wk` is tagged as an abbreviation of "week", `pY232` is tagged four times in one
sentence. Of the 270 gold abbreviation spans in the test split, **125 (46.30 %)** stand in one of
Schwartz & Hearst's two parenthetical arrangements. That is a ceiling on recall for any
definition-based algorithm, imposed by the annotation convention rather than by the algorithm, and
the looser of the two possible readings was used so as not to flatter the denominator.

Read the recall column against 46.30, not against 100.

### The result, PLOD-CW test split, 153 sentences

Every system through the same reader, the same detokenisation and the same scorer. Exact = predicted
token-index set equals gold; overlap = non-empty intersection, matched one-to-one.

| System (test split, `tight` join) | SF exact P/R/F1 | SF overlap F1 | LF exact P/R/F1 | LF overlap F1 |
|---|---|---:|---|---:|
| **all-caps token, length 2+ (trivial)** | 60.13 / **69.26** / **64.37** | **64.37** | — | — |
| **`acronymkit` `BIOMEDICAL`** | 93.52 / 37.41 / 53.44 | 53.44 | 83.33 / 59.21 / 69.23 | 73.85 |
| **`acronymkit` `HIGH_PRECISION`** | **97.06** / 36.67 / 53.23 | 53.23 | 88.24 / **59.21** / **70.87** | **75.59** |
| `acronymkit` `GENERAL` | 97.06 / 36.67 / 53.23 | 53.23 | 88.24 / 59.21 / 70.87 | 75.59 |
| `pyab3p` | 95.15 / 36.30 / 52.55 | 52.55 | 85.44 / 57.89 / 69.02 | 74.51 |
| `abbreviation_extractor` | 94.68 / 32.96 / 48.90 | 49.45 | 87.23 / 53.95 / 66.67 | 70.73 |
| `abbreviations` | 95.65 / 32.59 / 48.62 | 48.62 | 90.22 / 54.61 / 68.03 | 70.49 |
| `scispacy` | 95.65 / 32.59 / 48.62 | 48.62 | 84.78 / 51.32 / 63.93 | 69.67 |

**A rule anyone could write in one line beats every real system on short-form F1: 64.37 against our
53.23.** It gets there on recall (69.26 against 36.67) while giving up precision (60.13 against
97.06), and it produces no long forms at all, so its long-form row is zero. That is the honest scale
of the thing. On a corpus that asks "which tokens are abbreviations", a capitalisation heuristic is
a better answer than a definition extractor, and no amount of framing changes it.

Two things cut the other way and are worth as much:

- **Among the definition extractors we lead on both labels**, including against `pyab3p`, which beat
  us on MED1250 (88.87 against 83.85 F1 there). The ordering is not stable across corpora, which is
  itself the first evidence this project has that one corpus was never enough.
- **Precision is 97.06 %.** The highest precision any configuration of this library has ever
  recorded, on a corpus it has never seen. When we do fire, we are almost always on a token PLOD
  agrees is an abbreviation.

### Confirming on four times the data

153 sentences is a thin sample, so the pooled corpus — train + dev + test, 1,351 sentences, 2,869
abbreviation spans — was run as well. Nothing in acronymkit is fitted to any of it; the split
boundary carries no contamination meaning for a library that reads no training data.

| System (pooled, `tight` join) | SF exact F1 | LF exact F1 |
|---|---:|---:|
| all-caps token (trivial) | **68.62** | — |
| `acronymkit` `BIOMEDICAL` | 52.56 | 64.28 |
| `acronymkit` `GENERAL` | 52.37 | 64.32 |
| `acronymkit` `HIGH_PRECISION` | 52.31 | 64.25 |
| `pyab3p` | 51.20 | **64.36** |
| `scispacy` | 48.20 | 59.46 |
| `abbreviation_extractor` | 47.70 | 60.14 |
| `abbreviations` | 47.26 | 59.14 |

Same ordering, same story, tighter estimates. The bracketed ceiling is 46.11 % here against the test
split's 46.30 %, so the sampling is not what produced it.

### Detokenisation is the honest difficulty, and it is measured rather than asserted

PLOD ships tokens; our extractor takes prose. Text is reconstructed with each token's character
offsets recorded, the extractor runs on it, and its character spans are mapped back to token index
sets so the comparison happens in token space where the annotation lives. Two joins are implemented
and **every system is reported under both**:

- `spaced` — one space between every pair of tokens. Invents nothing, the same reasoning the
  disambiguation harness gives, but it is not prose: it produces `( DTT )` and
  `1,4 - dithiothreitol`.
- `tight` — punctuation, brackets, clitics, hyphens and slashes welded back on. The inverse of what
  spaCy did to produce these tokens.

`tight` is primary, on reconstruction fidelity, and the cost of that choice is the following table
rather than a paragraph of reassurance:

| Short-form exact F1, test split | `tight` | `spaced` |
|---|---:|---:|
| `acronymkit` `HIGH_PRECISION` | 53.23 | 53.76 |
| `pyab3p` | 52.55 | 52.69 |
| `scispacy` | 48.62 | 48.75 |
| `abbreviation_extractor` | 48.90 | **0.74** |
| `abbreviations` | 48.62 | **0.74** |

**Two of the five baselines are destroyed by the join alone.** `abbreviations` and
`abbreviation_extractor` require the bracket to abut the abbreviation, so under a space join they
return essentially nothing — 1 pair out of 153 sentences. That settles the choice: a join that
zeroes two systems is measuring the join. It also shows the choice was not made in our favour, since
our own figure is *higher* under the join that was rejected (53.76 against 53.23).

What the approximation can still cost, stated because it is not measurable from inside: the tight
join welds a compound the author may have spaced, and drops any whitespace the original had around
an em dash. It cannot be validated, because PLOD ships no source text to validate against.

### Two conventions, and the localiser, both quantified rather than assumed

Short-form exact and overlap are identical for most rows because every `AC` span in this release is
a single token and our predicted short forms are single tokens too. Long-form spans are where the
conventions separate: 70.87 exact against 75.59 overlap for the defaults, so roughly a fifth of our
long-form successes are boundary-approximate. Quoting the overlap figure alone would be five points
of flattery.

The external baselines return `(short, long)` strings and no offsets, so their spans must be located
in the text by string search. Our headline rows go through **the same localiser**, because scoring
our own row through a privileged path would flatter it, and the native-offset rows are recorded
beside them to price the difference:

| Pooled corpus, `HIGH_PRECISION` | SF exact P | SF exact R | SF exact F1 |
|---|---:|---:|---:|
| native character offsets | 93.66 | 36.53 | 52.56 |
| string localiser (headline) | 93.21 | 36.35 | 52.31 |

Not zero, and small. `unlocated_pairs` is 0 in every run recorded, so the localiser never loses a
prediction; the gap is entirely about which occurrence of a repeated form it attributes a prediction
to. The headline uses the pessimistic path.

### The profile question was asked and cannot be answered here

The interesting test would have been whether `BIOMEDICAL` underperforms on non-biomedical text —
which would mean the profile names carry information. PLOD is not non-biomedical, so that test was
not run. What the corpus does show is that the profiles behave *consistently*: `BIOMEDICAL` buys
recall with precision here (37.41 / 93.52) exactly as it does on MED1250 (79.65 / 86.23), and
`HIGH_PRECISION` and `GENERAL` are numerically identical on the test split, separating only on the
pooled corpus (52.31 against 52.37). A distinction that needs 1,351 sentences to become visible is
a distinction worth being modest about.

**Nothing was tuned.** No file in `src/acronymkit` changed, no default moved, no threshold was
swept. The numbers above are what ships.

### Deliberately not done

- **No pairs derived.** The route `bench/splits.toml` lists second — derive by adjacency, label it
  "derived pairing" — is still available and still not taken.
- **PLOD-filtered not fetched.** The larger variant would give a better estimate, but the pooled CW
  corpus already carries 2,869 abbreviation spans, the ordering is identical between the 270-span
  and 2,869-span arms, and the finding is a task mismatch rather than a decimal. Fetch it when
  someone needs the decimal.
- **The share-alike consequence is registered, and it reaches further than the wheel.** PLOD is
  CC BY-SA 4.0, verified from the repository's own `LICENSE` file rather than from the card's badge
  — the SDU-21 entry in this file is the standing reminder of why that matters. Fetch-only, like
  every other corpus. The clause worth noting is that BY-SA travels to *Adapted Material*: a
  term-frequency table derived from PLOD, of exactly the shape D-016 concluded the extractor would
  need, would inherit BY-SA. So PLOD is barred from the "derive statistics from a large unlabelled
  corpus" route as well, not merely from the wheel. Whoever runs experiment eight should pick a
  differently licensed corpus.

### What this actually establishes

1. **The extraction number was never one number.** Two corpora, two orderings. `pyab3p`'s MED1250
   lead is at least partly a home-field effect, and this is the first evidence of that from
   measurement rather than from argument.
2. **A trivial baseline is the incumbent on the span task**, exactly as `most_frequent` turned out
   to be the incumbent for disambiguation in D-015. Two subsystems, two corpora, the same lesson:
   measure against the stupid thing first.
3. **Domain generalisation is still unevidenced.** The gap `docs/EVALUATION.md` names is narrower
   than it was — we now know how the extractor behaves on a different genre, a different annotation
   convention and a different task — and it is not closed. A general-prose or legal-text corpus is
   the thing still missing, and PLOD was not it.

---

## D-016 — Derived term statistics: the signal is right, the corpus is far too small

**Status:** rejected · **Evidence:** `bench/run_termfreq.py`, `termfreq.med1250_test.*` in
`bench/results.json`

Experiment seven on the same gap, and the first one to carry a signal of the shape D-012 said was
required: **per-candidate**, so it can differ between two spans the same matching rule explains.
`acronymkit._term_stats` derives three such statistics from raw text with no annotation — document
frequency, adjacent-word association (normalised PMI with a count floor), and left-branching entropy
as a boundary statistic. Built on the dev half, reported on the test half, over
`bench/run_rerank.py`'s candidate enumeration unchanged.

| System (MED1250 test half) | dev F1 % | P % | R % | F1 % |
|---|---:|---:|---:|---:|
| **Tier 0 greedy (Schwartz & Hearst)** | **84.07** | 92.32 | **76.47** | **83.65** |
| `shortest` — the gate alone, no statistics | 81.81 | 93.35 | 75.83 | 83.68 |
| `extend/association ≥ 0.25` — dev-selected | 81.81 | 93.15 | 75.68 | 83.51 |
| `extend/content-word` — stop list, no statistics | 43.89 | 50.97 | 41.97 | 46.03 |
| `argmax/cohesion` | 32.35 | 42.03 | 34.82 | 38.09 |
| `argmax/contrast` | 27.39 | 36.85 | 30.52 | 33.39 |
| `argmax/full` — all three statistics | 24.63 | 28.49 | 23.69 | 25.87 |

Nothing beats the baseline on either half, and the dev-selected arm loses on the half it was selected
on. Reverted. Nothing in the extraction path changed.

### The measurement that actually matters, and it is not the F1 table

Three ceilings over the test half, which have been conflated until now:

    gold pairs                                          615
    gold present among the enumerated start boundaries  525    <- what D-011 measured
    gold that also survives the admissibility gate      488
    gold that IS already the shortest admissible span   477    <- what greedy returns for free

**The headroom for any rule that only moves the left edge is 488 against 477.** D-011's
121-pair figure is real, but the overwhelming majority of it is *not* reachable by choosing a
different start: 525 against 488 is gold that no alignment anchored on that span's own head word can
explain, so no rule respecting the matching constraint may return it at all. Every future selection
experiment should be reported against 488, not against 525, and certainly not against 615.

### Why it fails, and the cause is not the idea

The extension rule moves the left edge outward while every adjacency it introduces clears a
threshold. On the test half it made **zero** moves that reached gold at any threshold, while
destroying answers that were already right. The junction counts say why:

```
IIEF   want "International Index of Erectile Function"   international|index   seen 0 times   0.0000
PPIs   want "proton pump inhibitors"                     proton|pump           seen 1 time    0.0000
MPO    want "medial preoptic nucleus", not more          the|medial            seen 3 times   0.0688
                                                         into|the             seen 32 times   0.1950
```

**The thresholds are in the wrong order.** Admitting the truncation fixes needs a threshold at or
below 0.0000; holding off the over-extension needs one above 0.0688. There is no value that does
both, so the two error shapes cannot be fixed by one setting of this signal — which is the failure
mode D-008 and D-010 each hit by a different route.

And the reason is corpus size, not signal design. On the dev half only 22 brackets need a left
extension to reach gold at all, and for 19 of them the weakest adjacency the extension would
introduce has **no observation whatsoever**. 626 abstracts contain the function-word collocations
that drive over-extension (`into|the`, 32 observations) dozens of times over, and contain the
technical collocations that would drive correct extension either once or never. The statistic is
measuring the wrong half of the language because that is the only half a corpus this size holds.

That is the sharpest available argument for why Ab3P ships 31 MB rather than deriving from its
evaluation set — and it narrows the open question rather than closing it. What is refuted is
*self-derivation from the dev half of the evaluation corpus*. Deriving the same statistics from a
large unlabelled corpus is untested, and is the obvious experiment eight, with a concrete
precondition: it is worth running only if the corpus is large enough that pairs like `proton|pump`
clear the evidence floor.

### A methodological trap worth recording

The first implementation gated candidates with `extractor.find_best_long_form(sf, span) == span`,
reading it as "the reference matcher validates this span from its own head". It does not. That
function is the *greedy* matcher — it returns the first alignment it reaches walking right-to-left —
so the test actually asks "is the greedy answer this span", and used as a gate it discards every
candidate longer than the greedy one. That is exactly the set a truncation fix must choose from:
`proton pump inhibitors` and `International Index of Erectile Function` were absent from the
candidate set entirely, and no signal could have recovered them.

It did not look broken. It beat the baseline on the test half — on five recovered pairs that were
all chemical nomenclature — while losing to it on the dev half, and that arm would have been
reported had the two named error shapes not been checked case by case and found still wrong. Its
figures are deliberately not quoted here and were never written to `bench/results.json`: they
measure a gate that discards most of the candidate space, so they are not a result about anything.
The gate is now the strategy matcher anchored at the span's head
(`anchInit_placeWithin_skipAny`), and the lesson is the standing one: an arm that wins on the
reported half and loses on the half it was selected on is a bug until proven otherwise.

---

## D-015 — Disambiguation now has evidence, and the evidence is bad

**Status:** measured, shipped unchanged · **Evidence:** `disambiguation.sdu21.*` in
`bench/results.json`, `bench/run_disambiguation.py`

A third of the public surface — `LexicalDisambiguator`, `ExpansionDictionary` — had no external
evaluation and had been deferred three times. It has one now. SDU@AAAI-21 shared task 2 ships
`diction.json`, a candidate set per acronym, so the task is pure *selection*: no pairing assumption,
no derived gold, nothing invented. That is the objection `bench/splits.toml` raised against the span
corpora, and it is why this corpus was the one to use.

### The result

Development set, 6,189 instances, 611 distinct acronyms, mean 4.57 candidates. Exact string equality
against the gold expansion, which is the shared task's own convention.

| System | accuracy % | macro P % | macro R % | macro F1 % |
|---|---:|---:|---:|---:|
| ceiling (gold is always among the candidates) | **100.00** | | | |
| most-frequent expansion (shared task baseline) | **72.84** | 89.03 | 44.94 | 59.73 |
| **`acronymkit` `LexicalDisambiguator`** | **41.65** | 68.07 | 44.85 | 54.07 |
| random choice, seed 20260809 | 31.72 | 55.73 | 32.40 | 40.98 |

**We lose to the majority-class prior, badly: 41.65 % against 72.84 %.** That was the question worth
asking and it has the unflattering answer. It is recorded rather than tuned away, and nothing in
`src/` changed as a result of running it.

Two qualifications, both of which cut the other way from each other:

- The context scoring is **not** doing nothing. Random choice scores 31.72 % (analytic expectation
  31.62 %), so bag-of-words overlap is genuinely above chance.
- But it is doing least where the decision is easiest. On two-way acronyms it scores 55.28 % against
  a coin-flip's 50.32 %; on ten-or-more-way acronyms it scores 27.11 % against a random 7.72 %. The
  lexical signal separates a wide field slightly, and a narrow one barely at all.

### What the breakdown by candidate count is for

One accuracy hides two different problems. Ours falls 55.28 % → 44.43 % → 35.13 % → 35.14 % →
25.63 % → 27.11 % across arities 2, 3, 4, 5, 6–9, 10+; the most-frequent baseline falls
82.09 % → 79.74 % → 78.57 % → 66.27 % → 61.70 % → 39.14 %. The baseline's advantage is largest
exactly where the candidate set is small, which is where a prior is most informative and a
one-sentence context least so.

### Diagnosis, and it is a design fact rather than a bug

The disambiguator has **no prior at all**. Its blend is `0.55·overlap + 0.30·initials +
0.15·register`, and every term is a property of the *pair* (acronym, expansion) or of the context.
Nothing in it knows that "support vector machine" is a hundred times more common than "state vector
machine". A frequency table is exactly the per-candidate evidence D-012 concluded was missing for
extraction selection, and this is the same conclusion reached independently on the other half of the
library: **per-candidate discrimination needs per-candidate evidence, and frequency is the cheapest
source of it.** Two subsystems, two corpora, one finding.

A second, smaller defect is real and measured: an inline definition takes the top slot for 158 of
the 6,189 instances, and in 29 of them it overrides a dictionary candidate that was correct. Inline
expansions are copied verbatim out of the sentence, so under exact-match scoring against a
lower-cased dictionary key they nearly always miss. Preferring them is the right default for a
caller reading a document and the wrong one for this benchmark; the cost is quantified above and the
default is unchanged, because a benchmark is not a caller.

### The harness is validated, which is why the numbers above are worth reading

The shared task publishes official scores for its own most-frequent baseline. Reimplementing that
baseline and scoring it with our reimplementation of `scorer.py` reproduces them to the digit:
89.03 / 44.94 / 59.73. That is the same kind of check `pyab3p` provides for the extraction harness —
if the reader or the scorer were wrong, this would not land.

Two conventions of the official scorer are reproduced deliberately rather than corrected. The
headline metric is *macro*-averaged over gold expansion classes, and a gold class that was never
predicted is credited with a precision of 1.0. That is why a baseline can post 89.03 % precision at
44.94 % recall. Silently fixing someone else's metric would make our numbers incomparable with every
published one.

The one arbitrary choice in the harness is how to turn the corpus's token list back into a string.
Space-joining scores 41.65 %; attaching punctuation instead scores 41.57 %. The choice does not
carry the result, which is why it is stated rather than assumed.

### The licence claim in `bench/splits.toml` is wrong, and this is how

`splits.toml` records `corpora.sdu21_ad` as MIT. The repository root does ship an MIT `LICENSE`
file — and the README narrows it explicitly: the MIT grant covers "the evaluation script and the
baseline", while "the dataset provided for this shared task is licensed under CC BY-NC-SA 4.0". The
specific statement governs. `tools/fetch_data.py` records the data files as CC BY-NC-SA-4.0 and the
scorer as MIT, with the discrepancy written into `vendor_note` so nobody re-derives it from the
badge. Practically nothing changes — an evaluation corpus is fetch-only regardless, per the med1250
precedent — but "SDU-21 is the MIT alternative to the non-commercial SDU-22 data" is not a true
sentence and should not be repeated. The README is pinned as an asset so the finding is checkable.

### Correction to the headroom figure (added after D-016)

The 121-pair headroom counts gold spans present among the enumerated starts. Experiment seven
measured the chain more carefully on the test half:

    gold                                        615
    among the enumerated starts                 525
    surviving the admissibility gate            488
    already the shortest admissible span        477

So most of the apparent headroom is **not** addressable by a selection rule: the step from 525 to
488 is gold that no alignment anchored on the span's own head can explain, and 477 of the remaining
488 are already what the greedy rule returns. Future selection experiments should be reported
against **488**, not 525, and the realistic prize is far smaller than 121 pairs. The conclusion of
D-011 stands — the problem is selection rather than coverage — but its magnitude was overstated.

### Consequences

- **The Tier 2 seam from D-001 is now measurable.** The line item said "revisit when an eval harness
  exists to measure it against". It exists. Any neural disambiguator must clear 72.84 %, not
  41.65 %, because the trivial baseline is the real incumbent.
- **A frequency prior is the obvious next experiment**, and it is cheap: the shipped blend has no
  slot for one, so adding it is an API question before it is an accuracy question. **D-020 searched
  for the counts and found none that may be redistributed**, so the cheap version of this experiment
  does not exist; the one route that clears the licence bar is costed there and blocked on the wheel
  budget.
- **This is a tuning corpus from now on.** The breakdown above has been read. Anything selected
  against it must be reported on `test.json`, which is fetchable from the same pin and deliberately
  not fetched here.

---

## D-013 — Lazy import: kept, with the flattering comparison refused

**Status:** kept · **Evidence:** `micro.import` in `bench/results.json`

`import acronymkit` cost 149.3 ms, against `pyab3p`'s 3.6 ms. For a library whose positioning is
"Tier 0, pure Python, no compiled extension", being the slowest import in its own comparison table
contradicted the pitch. `__init__.py` now resolves its re-exports lazily (:pep:`562`).

| | before | after |
|---|---:|---:|
| `import acronymkit` | 149.3 ms | **2.3 ms** |
| `from acronymkit import AcronymEngine` | 149.3 ms | 128.1 ms |
| import + construct + first `generate()` | 191.3 ms | 196.0 ms |

**The third row is why this is written down.** Lazy re-export *moves* the pydantic cost to first use;
it does not remove it, and time-to-first-answer is unchanged. Quoting 2.3 ms next to `pyab3p`'s
3.6 ms would compare their working API against our shell, so the docs carry all three figures and
say so. The genuine win is narrower than the headline: a process that imports the package without
using the engine — for `__version__`, for a `TYPE_CHECKING` reference, or because a dependency pulls
it in — no longer pays 149 ms.

Rejected inside the same task: deferring `from importlib import import_module` to a helper. A/B over
31 fresh interpreters × 2 alternating rounds put it inside noise, so it went back to the simpler
form and the docstring claiming the win was deleted.

Not attempted: moving the DTO layer off pydantic. That is a breaking change to the public type
surface and needs its own decision. **It has one now: D-023**, which measures what the remaining
128.1 ms is made of and recommends the migration.

---

## D-014 — The generation ceiling is tokenisation, and it is mostly configuration

**Status:** decided · **Evidence:** `generation.med1250.coverage.*` in `bench/results.json`

All four presets converge to ~89.7 % recall@25, so a slice of the initialism bucket is never produced
at any rank. With the pool opened to depth 100,000: **51 of 546 pairs (42 of them, 82.3 %,
attributable to configuration defaults rather than the algorithm)**.

The decisive experiment:

- Beam 100,000 and 5 M nodes — four orders of magnitude more search — moves recall@25 by
  **0.00**.
- Relaxing tokenisation moves pool recall by **8.24 points** (90.66 % to 98.90 %).

So the ceiling is **tokenisation**, not search, and the largest single cause is
`max_letters_per_token` capping compounds such as `NMDA ← N-methyl-D-aspartate`. Beam width accounts
for one pair; nothing is genuinely unrepresentable.

Two by-products worth keeping:

- **All four presets have an identical candidate pool.** That is the first direct confirmation of a
  claim the preset design has always made and never demonstrated — they re-rank one shared set
  rather than searching differently.
- Pool recall over the subword bucket is only 5.78 %, which is a caution against investing further
  in sub-word matching for generation before someone has a reason to.

The fix is deliberately *not* bundled with the diagnosis: relaxing tokenisation defaults would trade
precision for recall across every caller, and this project's rule is that such a trade becomes a
named operating point with published costs, not a silent default change.

---

## D-012 — Pseudo-precision cannot select. It rates rules, not spans.

**Status:** decided, and it closes a line of attack · **Evidence:** `bench/run_rerank.py`

D-011 established that selection, not coverage, is the problem: our own candidate space holds
88.49 % of gold while the greedy rule returns 78.40 %, so the right span is present and
discarded 121 times. This is the experiment that tried to capture that, holding the candidate
space fixed at exactly the set the oracle measured and changing only the selection rule.

| System | P % | R % | F1 % |
|---|---:|---:|---:|
| **Tier 0 greedy (Schwartz & Hearst)** | 92.32 | **76.47** | **83.65** |
| Re-rank by pseudo-precision, min 0.95 | **95.15** | 71.70 | 81.78 |

Not shipped as a default: F1 loses. But note it is **not dominated** — 95.15 % precision is the
highest any pure-Python configuration in this project has reached, above Tier 0 and above every
competitor except `pyab3p`. It is a real Pareto point on the precision axis, recorded rather than
shipped because nobody has asked for it and it costs an estimator in the extraction path.

### Why it cannot work, measured

For every bracket where the gold span *is* in the candidate space:

    gold span ties with the top-scoring span : 518 of 537   (96.5 %)
    gold span scores strictly below the top  :  19 of 537   ( 3.5 %)

**96.5 % ties.** Pseudo-precision estimates the reliability of a *strategy*. Every span the same
strategy explains receives the same score, so within a rule the estimator is blind — and the
competing spans in the cases we get wrong are almost always explained by the same rule.
`"International Index of Erectile Function"` and `"Index of Erectile Function"` are both plain
word-initial alignments; no per-strategy number can separate them, because there is no per-strategy
difference between them.

That is a category error, and it is the same one twice: the cascade (D-010) and this re-ranker both
consume a per-rule signal to make a per-span decision.

### What this actually implies

The selection headroom from D-011 is real and remains unclaimed, but capturing it requires a
**per-candidate** feature — something that differs between two spans the same rule explains. Length,
head-noun agreement, and above all *how often the span's words actually co-occur in the language*
are all per-candidate.

That is precisely what Ab3P's `SingTermFreq.dat` is: 31 MB of subword and term-frequency statistics,
consulted per candidate. So the resource hypothesis returns — but for a sharper reason than the one I
gave when I first raised it. It is not that coverage is missing (D-011 disproved that). It is that
per-candidate discrimination needs per-candidate evidence, and frequency statistics are the cheapest
source of it. Deriving such a table from unlabelled text is the same shape of problem the
pseudo-precision estimator already solves.

**Closed:** pseudo-precision as a selection mechanism, in any arrangement. Two implementations, four
threshold sweeps. It remains valuable as *calibrated confidence*, which is what it actually is.

---

## D-011 — The gap is selection, not data. My prediction was wrong.

**Status:** decided · **Evidence:** `bench/run_oracle.py`, `oracle.med1250` in `bench/results.json`

After four failed attempts to close the gap to `pyab3p`, I predicted the remainder lived in Ab3P's
curated resources — 31 MB of subword-frequency data and `Lf1chSf`, which I described at the time as
a table of long forms for one-character short forms — rather than in the algorithm. **That was
wrong**, and one measurement settles it. The description of `Lf1chSf` was wrong too; it is a word
list, not a table of long forms, and the correction is recorded under D-010.

### Cross-system ceiling

| | correct | recall % | exclusive |
|---|---:|---:|---:|
| `pyab3p` | 1002 | 83.57 | 33 |
| `acronymkit` | 940 | 78.40 | 7 |
| `abbreviation_extractor` | — | 76.48 | 0 |
| `abbreviations` | — | 74.81 | 6 |
| `scispacy` | — | 74.23 | 0 |
| **oracle union** | 1031 | **85.99** | |
| universal miss | 168 | 14.01 | |

Two things fall straight out. **14.01 % of gold pairs are found by no system at all** — that is
the corpus's irreducible floor and every headline should be read against 85.99 %, not 100 %.
And we find 7 pairs **no other system finds**, so we are not strictly dominated —
while `abbreviation_extractor` and `scispacy` find 0 and 0 such pairs respectively, and are.

### The measurement that actually decides it

A cross-system union conflates selection with generation: a pair only `pyab3p` finds may be outside
our reach entirely. So the decisive quantity is our *own* candidate space — every long-form span our
Schwartz & Hearst matcher could legitimately return, which is exactly the set its greedy walk picks
one element from.

    gold reachable in our own candidate space : 1061 of 1199  (88.49 %)
    we currently return                       : 940  (78.40 %)
    headroom for a better selector            : 121 pairs (10.09 points)

**Our candidate space already contains 88.49 % of gold — more than `pyab3p` actually returns
(83.57 %).** The right answer is being generated and then discarded. Every point of the gap to
the leader is available without one byte of new data.

### Consequences

- **Move 2 (pseudo-precision as a re-ranker over the fixed candidate space) is the correct shot**, and
  it now has a measured ceiling to aim at rather than a hope.
- **Move 3 (vendoring or deriving Ab3P's resources) is deprioritised.** It was predicated on a
  coverage story the data does not support. `Lf1chSf` may still help the single-character bucket
  specifically, but it is no longer the main event. **D-019 measured that: it does help, by a fifth
  of a point, on evidence too contaminated to trust, and it was refused.**
- Any future selection experiment should report against 88.49 %, not 100 %, because that is what a
  perfect selector over this candidate space would actually achieve.

---

## D-010 — Pseudo-precision estimator: shipped. Cascade built on it: not shipped.

**Status:** estimator kept, cascade rejected · **Evidence:** `bench/run_cascade.py`, `bench/results.json`

Phase B was to close the 5-point gap to Ab3P by doing what Ab3P does: apply many matching strategies,
ordered by estimated reliability, and take the first that fits. Half of it worked.

### The estimator works, and it is the part worth having

`acronymkit._pseudo_precision` estimates each strategy's precision from **raw text with no
annotation at all**, following Sohn et al. (2008): measure how often a rule fires on real candidates,
subtract how often it fires on short forms paired with windows that cannot define them, and the
remainder is the rate at which it fires for a reason.

Three independent checks that it is doing something real:

1. **The derived ordering matches Ab3P's published one.** Word-initial anchoring with word-initial
   placement estimates at 1.000 on three-letter alphabetic short forms; the loosest rule
   (any anchor, any placement, any skipping) estimates at 0.534. Over the same bucket, Ab3P's own
   table runs from `Al 3 FirstLet 0.999808` down to `Al 3 AnyLet 0.303503`. Same ordering, derived
   independently, no labels.

   **CORRECTION.** This bullet used to end "Ab3P's own table runs `FirstLet` 0.999 to `AnyLet`
   0.681", and the second figure is not in the file. `WordData/Ab3P_prec.dat` was re-fetched from
   the Ab3P commit `tools/fetch_data.py` pins — 4,050 bytes, 145 rows, no blank lines, four
   whitespace-separated fields each (character class, short-form length, strategy name, estimate):

       sha256 77903769069451f67095b8aa677ac19b4074e86cf165519c3cd1cb02734db5c3

   The string `0.681` does not occur anywhere in it. What does occur is eight `AnyLet` rows, and
   their unweighted mean is `0.680631`. So the figure was an average taken across three character
   classes (`Al`, `Num`, `Spec`) and short-form lengths 3 to 5 — eight of those nine combinations,
   since `Spec 3 AnyLet` has no row — written as though it were a published row, and then set
   against a figure of ours measured on three-letter alphabetic short forms alone.

   The `FirstLet` half checks out: `Al 3 FirstLet 0.999808` is a real row, and it is the maximum of
   the `Al 3` bucket exactly as `Al 3 AnyLet 0.303503` is its minimum, so "runs from … down to" is
   literal rather than a figure of speech. The quoted `0.999` was that row truncated, not rounded —
   0.999808 rounds to 1.000 at three decimals — which is why the bullet now carries the full values
   instead of shortened ones.

   Two things the corrected numbers still do not say. Ab3P's `AnyLet` and our "any anchor, any
   placement, any skipping" are not the same rule, so the distance between 0.534 and `0.303503`
   measures a difference in rule definitions as much as anything else — a numeric comparison at the
   bottom of the range was never sound and is not being repaired here. And the check this bullet
   makes is about *rank*: a rule derived from unlabelled text lands where Ab3P's labelled estimate
   lands relative to its neighbours. That is what stands.
2. **Reliability falls with shorter short forms** — max 0.962 at length 3 against 0.833 at length 2 —
   which is the structure Ab3P's per-length table encodes.
3. **The confidence is calibrated.** Sweeping the abstention threshold on held-out data moves
   precision monotonically 85.43 -> 86.83 -> 88.97 -> 90.94 -> 91.62 while recall falls only
   74.56 -> 72.97. Higher-confidence pairs really are more often right, which is the property that
   makes abstention meaningful.

That estimator is usable on any domain where no gold standard exists and never will — legal,
financial, internal documentation. Nothing else in this library can be tuned that way.

### The cascade does not beat the single greedy rule

Held out (MED1250 test half, frozen split seed 20260809, estimated on the dev half):

| System | P % | R % | F1 % |
|---|---:|---:|---:|
| **Tier 0, Schwartz & Hearst** | **92.32** | **76.47** | **83.65** |
| Tier 1 cascade, no abstention | 85.43 | 74.56 | 79.63 |
| Tier 1 cascade, abstain < 0.90 | 91.62 | 72.97 | 81.24 |

Tier 0 dominates at every threshold — better precision *and* better recall. Not shipped.

### Why, and it is the same mistake as D-008

The first cascade preferred the **earliest** valid long-form start, on the theory that S&H's
truncation is the thing to fix. It is not, or at least not by that route:

    ARC   got "and arcuate nucleus"                              want "arcuate nucleus"
    MPO   got "male rats following infusion into the medial ..." want "medial preoptic nucleus"

`ARC` aligned its `a` to "**a**nd". Preferring longer spans buys a few genuine recoveries and pays
for them many times over — which is exactly what the hyphen-boundary experiment in D-008 found.
Switching to latest-start improved every abstention threshold — the shipped table below is
that variant, the better of the two — and it still lost.

The lesson is consistent across two independent attempts: **the greedy shortest-match rule is a much
stronger baseline than its visible truncation suggests.** Beating it is not a matter of choosing
better boundaries. Ab3P's advantage must come from somewhere else in its design — most likely its
much larger curated resources (`SingTermFreq.dat` is 31 MB of subword-frequency data, `Lf1chSf`
48 KB of vocabulary used as a membership gate), not from the cascade structure alone. That is
testable and is the obvious next experiment.

**CORRECTION.** This paragraph used to call `Lf1chSf` "long forms for one-character short forms",
which reads as a short-form-to-long-form table. It is not one, and anyone who went looking for
pairs in it would find none. The file was fetched and read: 48,126 bytes, 4,991 lines, exactly one
whitespace-free token per line, all lower-case, ASCII, sorted ascending, no duplicates, no
delimiter and no second column. 350 of the 4,991 entries are not purely alphabetic — they carry a
hyphen, slash, digit or trailing punctuation (`long-wavelength-sensitive`, `al(2)o(3)`, `aims:`,
`analysis,`), which is what an automatically harvested word list looks like rather than a curated
mapping.

It is consumed as a **set**. Ab3P's `Makefile` target `data` runs
`./make_wordSet WordData/Lf1chSf Lf1chSf`, and `make_wordSet.C` opens with the comment "make a hash
set for a set of strings" and builds a hash table with no values attached. Exactly one strategy
consults it: `FirstLetOneChSF` in `lib/AbbrStra.C`, which lower-cases the final token of the text
preceding the short form and gives up if that token is absent from the set —
`if(!wData->lfs.find(phrl)) return 0;`. That is the file's whole role, a gate on one rule, and
`Ab3P_prec.dat` carries exactly one row for the rule it gates: `Al 1 FirstLetOneChSF 0.967224`.

The misreading came from upstream's own wording — Ab3P's `README.md` says "Long forms for
1-character short forms are in the file `Lf1chSf`" — so it is an easy one to repeat. The
consequence for D-011's "`Lf1chSf` may still help the single-character bucket" is that adopting it
means adopting a vocabulary filter, not importing anyone's answers.

---

## D-009 — A preset is a point on a frontier, not an answer

**Status:** open · **Evidence:** [`notes/scoring-objective.md`](notes/scoring-objective.md)

Section 2 of the technical note shows that no single coefficient vector can both
weight dictionary hits meaningfully and reproduce conventional initialisms, once the lexicon is
real. That is not a tuning problem to be solved; it is a trade-off to be exposed.

Presenting one vector as *the* balanced answer hides that trade inside a constant. The successor API
returns the **Pareto frontier** — the non-dominated operating points over (initialism fidelity,
pronounceability) — and lets the caller pick. Someone naming a product wants a different point from
someone indexing a document store, and neither is wrong.

Not built yet. Recorded here so the design consequence of a proved result does not evaporate.

The same reframing applies to the extraction configuration: we sit at 92.07 precision / 76.99 recall,
which is precision to spend, and the knobs that cost 17.6 % of the misses are operating points rather
than defects. An `ExtractionProfile` enum with published per-corpus numbers is the same idea applied
to the other half of the library.

---

## D-008 — Boundary-maximising long-form selection: tried, measured, reverted

**Status:** rejected · **Evidence:** `docs/EVALUATION.md`

The largest single category of extraction misses (28.7 %) is the reference matcher truncating the
long form: it walks right-to-left and accepts the first alignment it reaches, which is the shortest
one. `IIEF` yields `"Index of Erectile Function"` rather than `"International Index of Erectile
Function"`, because the second `I` and the `E` are consumed from inside `"Erectile"`. Each such case
costs a false negative *and* a false positive.

Tried: enumerate every plausible starting boundary, keep those the reference matcher validates from
their first character, and pick the one maximising word-initial alignment.

| Variant | Exact F1 on MED1250 |
|---|---:|
| Reference algorithm (kept) | **84.78** |
| Maximise initial alignment, word + hyphen starts | 83.36 |
| Same, count rather than fraction | 83.36 (identical — monotonically related) |
| Same, hyphen starts restricted to alphabetic prefixes | 84.69 |

Reverted: nothing beat the baseline.

The diagnosis is worth more than the attempt. Hyphen-boundary starts fixed 3 pairs (`HDL →
high-density lipoprotein`, where `non-` is a qualifier rather than part of the term) and broke 18,
almost all chemical nomenclature (`2,6-diaminopurine → diaminopurine`). Locants belong to the
compound's name; a `non-` prefix does not. Restricting hyphen starts to alphabetic prefixes separates
those cases and recovers nearly all the loss — but "nearly" is not "beats", so it did not ship.

Conclusion: the greedy match is a stronger baseline than its visible truncation suggests, and beating
it probably needs what Ab3P actually did — per-candidate precision estimates learned from data — not
a better boundary heuristic.

---

## D-007 — `BALANCED_PRONOUNCEABLE` is not the default, and cannot reproduce the canonical corpus

**Status:** decided · **Supersedes:** the v0.1.0 default

Replacing the model-authored lexicon with real SCOWL data dropped
`BALANCED_PRONOUNCEABLE` from 16/16 to 13/16 on the canonical corpus (SQL→SQUL, QA→QUA, TCP→TCOP).
Re-running the sweep found only **8 of 768** vectors reaching 16/16, all on the edge of the grid — a
spike, not a plateau.

Diagnosing the three failures showed the problem is structural:

| case | margin | mechanism |
|---|---|---|
| QA → QUA | +14.2 | "qua" is genuinely in SCOWL, so Λ fires |
| SQL → SQUL | **+0.066** | neither is a word; inserting a vowel improves Φ by ~4 log units |
| TCP → TCOP | **+0.52** | same |

Two of the three are decided by margins indistinguishable from noise. Φ's dynamic range (≈ 6.5 log
units) is comparable to a whole initial-letter match (ω = 10), so at β = 1 the phonotactic term alone
decides the ranking.

**Tried and rejected:** raising `length_penalty` to suppress vowel insertion. At the value required
(≈ 14+) the short acronyms break instead — API, ROM and NASA all fail. Measured across
`length_penalty ∈ {10, 14, 16, 20}` at γ = 12: 15/16, 13/16, 13/16, 12/16. There is no vector that
both weights dictionary hits meaningfully *and* returns every textbook initialism.

**Decided:** the requirement was contradictory, so the *default* changed rather than the tuning.
`STRICT_INITIALISM` is now the default — 16/16, and still 16/16 when β, γ or δ are perturbed by
50–100 %, which is a genuine plateau. `BALANCED_PRONOUNCEABLE` keeps its coefficients and is
documented as the trade it is. Demanding that the pronounceability-weighting preset also produce
pure initialisms was asking it not to do its job.

`tools/tune_presets.py --check` now encodes the two different contracts: strict must reproduce the
corpus; balanced must *trade* (mean pronounceability strictly above strict's, currently 0.625 vs
0.542). A balanced preset that behaved identically to strict would be dead weight.

---

## D-006 — fr/es/de ship no lexicon rather than a copyleft or invented one

**Status:** decided

Three options for the non-English word lists:

1. **Keep the model-authored lists.** Rejected: every Λ(A) claim is unverifiable, and the failure
   mode is a confident wrong answer the caller cannot detect.
2. **Vendor Hunspell dictionaries.** Rejected on licence grounds. German is not a judgement call —
   its only permissive arm is OASIS 0.1, which grants distribution solely alongside programs whose
   primary save format is ODF, which acronymkit is not; the fallback is GPL. French (MPL) and Spanish
   (MPL-1.1 arm) are arguably vendorable, since MPL permits an MPL file inside a larger work under
   other terms — but that makes the wheel MIT-plus-MPL and obliges every downstream redistributor to
   track a second licence for one data file. Disproportionate.
3. **Ship nothing and say so.** Chosen.

The engine degrades honestly: `AcronymEngine` records a warning naming the language and the remedy
the first time a missing lexicon or n-gram model is loaded. Generation still works — French yields
SGBD, German ADAC, Spanish DNI — because positional fidelity carries it alone.

**Not done:** expanding Hunspell affix rules in `read_hunspell`. Only stems are taken; correct
expansion needs the `.aff` rules and a Hunspell implementation. For a fetch-only asset the user
installs themselves, a solid-but-not-exhaustive lexicon is the right trade.

---

## D-005 — CMUdict validates the syllable heuristic; it is not shipped as a table

**Status:** decided

CMUdict gives real pronunciations for ~134k words. Two possible uses:

- **Ship a syllable table.** Considered and cut. Roughly 1 MB of wheel for a lookup that only helps
  when a candidate acronym *is* a dictionary word — a minority of cases, since acronyms are mostly
  not words. The cost/benefit is poor and it would be the largest thing in the wheel.
- **Validate the heuristic.** Chosen. Counting stress-marked phonemes gives ground-truth syllable
  counts, which turns "the heuristic seems about right" into a number: **84.1 % exact, 99.5 % within
  one syllable, MAE 0.16** across 117,485 entries. Reproduce with
  `python tools/build_lexicons.py --validate-syllables`.

Revisit if a feature ever needs exact syllable counts for arbitrary words.

---

## D-004 — SCOWL size cut ≤ 60, ASCII only

**Status:** decided

SCOWL grades entries 10 (most common) to 95 (obscure). Cut at **60** (76,879 entries after
filtering) because Λ(A) is a *claim* that a generated acronym is a real word, and a false positive
is worse than a false negative: at 80+ the list admits strings no reader would recognise, which would
make the dictionary-backronym strategy confidently propose nonsense.

Proper names, abbreviations, contractions and all-caps entries are excluded — otherwise "NASA" would
count as a dictionary word and every initialism would trivially satisfy Λ(A).

The 157 accented loanwords (abbé, appliqué, attaché) are dropped too. They cannot help: candidates
take uppercased token initials, so an accented character reaches an English acronym only if an
English token starts with one. They do measurably hurt: keeping them widens the n-gram alphabet from
26 to 39 symbols that never appear in a candidate, spreading smoothing mass over dead entries.

---

## D-003 — Timing assertions live in the benchmark suite, not the correctness suite

**Status:** decided

Four CI matrix cells failed on the first push while the code was correct: two tests asserted fixed
wall-clock ceilings (0.1 s, 2.0 s) that hold on the development machine and not on a shared runner.

A hard-coded threshold is a claim about somebody else's CPU. The correctness suite now asserts
**scaling** — doubling the input must not triple the time, which decides linear-versus-quadratic on
any hardware — with residual hang guards scaled by `conftest.machine_factor()`, calibrated against a
fixed interpreter-bound loop.

---

## D-002 — `length_penalty` is a deliberate deviation from the published objective

**Status:** decided · **Writeup:** pending (Phase 5.3)

The published positional term `α·Σω` is a sum, so it grows monotonically with acronym length. Used
unmodified as a *generation* objective it is degenerate: "Portable Document Format" scores `PODOFO`
above `PDF`, because every extra character adds `contiguous_weight` and subtracts nothing. The
published formulation is a *ranking* function over candidates of a given length, so it never had to
address this.

`ScoringWeights.length_penalty` (default 8.0) sits between `contiguous_weight` (2) and
`initial_weight` (10), so covering a new token nets +2 while taking a second letter from a token
already used nets −6. Set it to `0.0` to recover the published objective exactly; a test pins that
equivalence.

---

## D-001 — Scope deliberately cut from the v0.1.0 → v0.2.0 mandate

**Status:** decided

Ranked by credibility-per-unit-effort, and cut because doing them shallowly is worse than not doing
them. Each violates "never assert a number you did not measure" if rushed.

| Cut | Why | Revisit when |
|---|---|---|
| PyPI publishing | Requires credential/account operations, and claiming a global namespace is irreversible. Trusted-publishing workflow is wired and ready. | The maintainer runs it |
| Rust/Cython native core | The rule is *only after the pure-Python work plateaus*. It has not; no profile exists yet. | `docs/PERFORMANCE.md` shows a plateau with a clear hot kernel |
| `acronym4j` Java port | Its own project. The JSON Schema interop contract exists so it stays possible. | Python side is stable at 1.0 |
| Tier 2 neural disambiguation | Needs the SDU corpora (CC BY-NC-SA — benchmark only, never vendored) and a training loop. The `LexicalDisambiguator` contract is the seam. | An eval harness exists to measure it against |
| WASM/Pyodide playground | Strongest adoption lever, but pure packaging work with no correctness content | After v0.2.0 ships |
| MCP server | Thin wrapper; cheap once the API is stable | After 1.0 |
| Full 4-corpus × 3-baseline eval harness | One honest number beats four unfinished ones | Next, and it is the highest-value remaining item |

**The single most valuable thing not yet done:** a real extraction F1 against a real gold corpus
(Ab3P, PLOD). The published Schwartz & Hearst figures are ~86–89 % F1 on Ab3P with recall the weak
side. Landing materially below that would mean a bug; landing at it converts "faithful transcription"
from a claim into a measurement.
