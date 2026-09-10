# Cold read seven — findings

**Read-only.** Nothing in this repository was changed by this reader except this file.
`docs/SECOND-READER.md` section 5 retired the fix clause; no user-facing page, no gate, no config
and no ledger row was edited. Every finding below carries the command that refutes it and the
output that command produced in this checkout.

**Pre-registration** was written before any finding was drafted, to
`scratchpad/COLD-READ-5-PREREG.txt`, and is reproduced verbatim in section 5. **Three of its four
falsifiers fired**, which means three of the four things this read bet on being wrong were right.
That is reported as the headline rather than softened.

---

## 0. Triggers, and the gates as I found them

```
python tools/second_reader.py --trigger
  trigger A: 3 user-facing file(s) changed in the working tree
    docs/CLAIMS-LEDGER.md
    docs/EVALUATION.md
    docs/GATES.md

python tools/second_reader.py --check
  rotation: 25 file(s); trigger B serves docs/SECOND-READER.md next
```

Trigger B is followed, not chosen. **It served `docs/SECOND-READER.md`, which is the file cold read
six was also served**, because the ledger was never written and the cursor did not move. That is
finding `F-7-07` and it is the most load-bearing thing in this document.

### The gates. All ten green, and the one red I saw was a race in a shared checkout

`CONTRIBUTING.md` lists **ten** commands, not the nine the standing brief lists; the tenth is
`python tools/run_summary.py --check`, which runs at `.github/workflows/ci.yml:190`.

```
rc=0  python -m pytest tests                            6200 collected
rc=0  python -m ruff check src tests tools bench        All checks passed!
rc=0  python -m ruff format --check src tests tools bench   186 files already formatted
rc=0  python -m mypy                                    124 source files
rc=0  python tools/check_claims.py     unbacked 0 | value-matched 64 of 64 | deferred 189 of 189
rc=0  python tools/splits.py --check
rc=0  python tools/gates.py --check    in-situ 21 of 42 | debt 21, ceiling 21 | owes 1 forward
rc=0  python tools/second_reader.py --check
rc=0  python tools/run_summary.py --check
rc=0  python tools/run_summary.py --check-agent-summary
```

**The first `pytest` run of this session exited `1`.** Before diagnosing it I ran `git fetch`:
`HEAD == origin/main == 1e0d6d5`, `git rev-list --left-right --count HEAD...origin/main` returns
`0 0`, so this is not `D-119`'s unmerged branch. I then read the sibling summaries in the
scratchpad `run_summary` directory — the mechanism `D-119` records as correct, present and unread —
and two of them describe the same class of transient on this checkout. The two failures were

```
FAILED tests/test_claims_gate_coverage.py::test_the_positive_control_fails_the_build
FAILED tests/test_claims_gate_coverage.py::test_the_residue_the_closure_left_behind_is_still_uncaught[plural keyword]
```

`git status --porcelain -- README.md` was empty and `grep -c` for the probe marker in `README.md`
returned `0` at the moment I looked, and `python -m pytest tests/test_claims_gate_coverage.py`
returned `12 passed` minutes later, and the whole suite then returned `rc=0`. `pyproject.toml` sets
`addopts = "-q --strict-markers --strict-config"` and `import xdist` fails, so my own run was
sequential and cannot have raced itself. **A sibling process was running the same module against
the same checkout.** That is `F-7-10`, and it is a defect in the test module rather than in the
tree.

---

## 1. Findings

### F-7-01 — `docs/EVALUATION.md:2853-2854` — the caveat the round was commissioned to retire, still standing, in the file the same round rewrote

**Severity: high.** This is the brief's "obsolete caveat is as wrong as a missing one", arriving in
the strongest available form: the sentence predicts a future that has now happened *and* predicts it
wrongly, and its twin in the source tree was rewritten this round while this copy was not.

> Bounding the selective rate needs risk-controlled selective classification, which is not
> implemented; when it lands, this gate tightens.

**Two independent falsehoods.**

*It is implemented.* `src/acronymkit/core/selective.py` ships `SelectiveRiskGate` in this working
tree, and `docs/EVALUATION.md` itself documents it `1,105` lines earlier under *"Risk-controlled
selective classification"* — added by the same workstream, in the same file, in the same
uncommitted change.

*And it did not tighten this gate.* The new section says so in its own words — *"It landed, and it
is a second bound rather than a repair of the joint one"* — and so does the twin copy of this exact
sentence in the source:

```
grep -rn "risk-controlled selective classification" docs/*.md src/acronymkit/*/*.py

  docs/EVALUATION.md:2853        <- "which is not implemented; when it lands, this gate tightens."
  src/acronymkit/nlp/propagation.py:80   <- rewritten this round
  src/acronymkit/nlp/propagation.py:162
```

`src/acronymkit/nlp/propagation.py:80-81` now reads *"Bounding the selective rate needs
risk-controlled selective classification, and this paragraph is the one that said 'when it lands,
this paragraph is what has to change'"*. **One copy of the sentence was found and fixed and the
other was not**, which is check `C2` exactly: two documents describing one mechanism, and the
shorter path to the defect was to diff them.

**Exact replacement text** for `docs/EVALUATION.md:2853-2854`, preserving the surrounding sentence:

> `0.20`. Bounding the selective rate needs risk-controlled selective classification, and that is
> what the separate `selective=` parameter now supplies — see *Risk-controlled selective
> classification* above. **`gate=` alone still bounds only the joint rate**, and this paragraph is
> about `gate=`: the new gate is a second bound beside it rather than a repair of it, so the
> multiple above is still the shipped figure for a caller who passes `gate=` and nothing else.

---

### F-7-02 — `docs/EVALUATION.md:4602` — "the same five rows to the digit", and the column that differs is the work count

**Severity: high, and it is an R17 finding rather than a tidiness one.**

> Socrata, empty catalog. SEC XBRL and the fixture schema give the same five rows to the digit.

The table above that sentence has five columns, and one of them is `records` — the work count R17
exists to require. It is different on every corpus:

```
python -c "import json; d=json.load(open('bench/results.json',encoding='utf-8'))['runs']; ..."

  run id                                          records   forcing_pct   never_read
  governed_perf.socrata.empty.reads               123675    0/0/100/100/100      0
  governed_perf.sec_xbrl.empty.reads               82546    0/0/100/100/100      0
  governed_perf.fixture_schema.fixture.reads       20000    0/0/100/100/100      0
```

`forcing_pct` and `never_read` are identical across all three. `records` is not, and the published
table prints the Socrata value. **A reader told the five rows are the same "to the digit" would take
the work count to be the same**, and it differs by `41,129` records between the two real corpora —
one of them a factor of six from the fixture arm. The claim that is true is about the two columns
the argument actually rests on.

**Exact replacement text:**

> Socrata, empty catalog. **SEC XBRL and the fixture schema give the same `forcing_pct` and the same
> `never_read` in all five rows**, on their own record counts —
> `82,546<!--claim:governed_perf.sec_xbrl.empty.reads.phrase_only.records:,-->` and
> `20,000<!--claim:governed_perf.fixture_schema.fixture.reads.phrase_only.records:,-->` against
> Socrata's `123,675`. The bimodality is what replicates; the work count is per corpus.

---

### F-7-03 — `docs/EVALUATION.md:1097` and `src/acronymkit/core/selective.py:875` — the guarantee is stated more tightly than it is proved, on two surfaces out of three

**Severity: medium-high.** This is the brief's *"read every sentence stating what is guaranteed and
ask what a caller would take it to promise"*, and the answer differs by surface.

The module docstring gets it right, and it is the **only** place in the tree that does:

```
grep -rn "expected share" src docs README.md CHANGELOG.md
  src/acronymkit/core/selective.py:39
```

`src/acronymkit/core/selective.py:37-40` — *"the selective risk of the returned threshold is at most
`alpha`: of the instances this gate answers, **the expected share** it gets wrong is at most
`alpha`"*. That is the functional the module's own derivation at `:47-62` proves: the losses are
Bernoulli with parameter `R_selective(lambda)`, the p-value is a binomial tail, and what is bounded
is the parameter — not the realisation.

Two surfaces drop the qualifier.

* **The runtime string.** `guarantee()` at `:874-875` returns *"at most `{alpha}` of the instances
  this gate ANSWERS are wrong"*. The docstring at `:34-36` says this method *"re-state[s]"* the
  guarantee above; it states a stronger one.
* **The page.** `docs/EVALUATION.md:1096-1098` — *"at most `alpha` of the instances the gate answers
  are wrong"*.

**Why this is not pedantry here.** A governance caller reads the runtime string as a bound on the
errors in *their* batch. It is a bound on the population rate, and a finite deployment sample can
exceed it without the guarantee failing. `src/acronymkit/core/conformal.py:42-43` already names the
unqualified form as the overclaim shape — *"A sentence promising 'at most `alpha` of the answers are
wrong' is an overclaim and this module does not make it"* — about the joint bound. The selective
module makes the same-shaped sentence about a different functional, where it is nearly right, and
`tests/test_conformal.py`'s `GUARANTEE_FILES` rule checks only that `exchangeab` appears in the
paragraph. **Nothing checks the expectation qualifier**, which is why one of three surfaces carries
it.

**Exact replacement text** for `src/acronymkit/core/selective.py:874-876` (the interpolated string):

> `f"With probability at least {1.0 - self._delta:.4g} over the draw of the calibration "`
> `f"set, {scope}, the EXPECTED share of the instances this gate ANSWERS that are wrong is "`
> `f"at most {self._alpha:.4g}. That is the selective risk and not the joint rate: it is "`
> `f"already divided by the answer rate, so unlike a split-conformal alpha it needs no such "`
> `f"division. It bounds the rate and not the count -- a finite batch of answers can exceed "`
> `f"it without this guarantee failing. It says nothing about the instances the gate "`
> `f"refuses, and it was bought at an answer rate of {answered}, ..."`

**Exact replacement text** for `docs/EVALUATION.md:1096-1098`:

> assumption because the two are only honest together: **with probability at least `1 - delta` over
> the draw of the calibration set, the expected share of the instances the gate answers that are
> wrong is at most `alpha`** — a bound on the rate and not on the count, so a finite batch of
> answers may exceed it without the guarantee failing — under exchangeability between the
> calibration instances and the deployment instances, and under independence of the accepted
> calibration units.

---

### F-7-04 — `docs/EVALUATION.md:1103-1104` — an exhaustive phrase over an enumeration where one member is the empty set

**Severity: medium.** Check `C1`, and the section refutes itself `24` lines later.

> **It did not fire.** Across every cell where anything was certified, on both corpora and both
> splits, the held-out error rate among answers stayed under its own nominal

`docs/EVALUATION.md:1127-1128` says *"Learn-Then-Test certifies **nothing at any of the six
alphas**"* on SDU-21. So on one of the two corpora the set of cells where anything was certified is
empty, and *"on both corpora"* reads as coverage where there is none to have. The relative clause
*"where anything was certified"* is doing all the work and the phrase after it undoes it. The
worst-ratio figure published beside it is drawn from MED1250 alone.

**Exact replacement text:**

> **It did not fire.** On MED1250, across every cell where anything was certified on either split,
> the held-out error rate among answers stayed under its own nominal — which is not the joint rate
> and is the quantity this section is about. **On SDU-21 the abort could not fire, because nothing
> was certified at any alpha and a gate that answers nothing has no error rate among answers.** A
> pre-registered abort that is vacuous on one of two corpora is reported as vacuous there rather
> than as passed. The worst ratio anywhere on the exchangeable arm is `0.4754`, and it is a MED1250
> figure.

---

### F-7-07 — `docs/SECOND-READER.md:596-601`, and section 5.3 — the anti-rot clock is driven by ledger writes, and the only reader who can trigger it is forbidden to write it

**Severity: high. This is the structural finding and it is about the policy, not a number in it.**

The page's own state:

```
python tools/second_reader.py --check
  cold reads: 4 recorded; newest 2026-09-08
  findings: open 5, fixed 10, blocked 0, permanent 0  (of 15)
  OPEN AND AT THE LIMIT: 0 of 5

grep "^reader = " docs/cold-reads.toml
  cold-read-1 / cold-read-2 / cold-read-4 / cold-read-5
```

Four rows. **Cold read six executed**: it served `docs/SECOND-READER.md`, published ten findings to
`docs/notes/cold-read-6-findings.md` (committed at `1e0d6d5`), and wrote no ledger row — its own
machine summary says so, naming itself *"the FOURTH consecutive read in that position"*. This read
is the fifth in that position, and trigger B has now served the same rotation entry twice running.

**Three mechanisms the page credits are all inert against this.**

1. *The cursor.* Section 8 says *"`--check` refused the disagreement between this line and the
   ledger the moment the ledger was finally written, which is the one failure mode section 3
   predicted this policy would have."* The gate compares the page against **the ledger**. An
   unwritten read puts nothing in the ledger to disagree with, so the cursor stalls with `--check`
   green — which is what it is doing now, for the second consecutive read.
2. *The decay clock.* `OPEN_READ_LIMIT = 2` and section 5.3's table both count **cold reads
   recorded in the ledger**. Five findings (`F-5-3`, `F-5-5`, `F-5-6`, `F-5-7`, `F-5-8`) were raised
   at read five. Two reads have executed since and `--check` prints `OPEN AND AT THE LIMIT: 0 of 5`.
   **Two unrecorded reads did not advance the clock**, so the bound section 5.3 calls *"at most two
   cold reads"* is a bound on recorded reads and not on rounds.
3. *`reviewed_in`.* The rule *"at every cold read its `reviewed_in` must name the newest read, or
   the gate is red"* is satisfied vacuously while the newest read stays `cold-read-5`.

**And the cause is the policy's own boundary, not neglect.** Writing a row makes the derived cursor
advance, which requires the `<!-- rotation-cursor -->` block in `docs/SECOND-READER.md` to move, or
`--check` goes red. That block is in a user-facing page in the rotation. Section 5 forbids the
reader from editing user-facing prose. **So the ledger write is a coupled two-file edit that the
only agent with the information is not permitted to make**, and section 7's *"Nothing asserts that a
cold read HAPPENED"* names the symptom while treating the cursor and the decay clock as the parts
that do work. On this evidence they do not.

**Exact replacement text** for the paragraph at `docs/SECOND-READER.md:596-601`:

> **The cursor has now stalled for four reads out of seven, and `--check` was green through every
> one of them.** Reads three and four both served `docs/SUPPORT_MATRIX.md`; reads six and seven both
> served this page. The gate compares this line against the ledger, so an executed read that writes
> no row leaves nothing to disagree with — and `OPEN_READ_LIMIT` counts recorded reads, so the decay
> clock on an open finding does not advance either. **The bound section 5.3 states is a bound on
> recorded reads, not on rounds.** The cause is this page's own boundary: advancing the cursor is a
> coupled edit to the ledger *and* to this block, and section 5 forbids the reader the second half,
> so the write needs a second agent every round and has had one twice in seven. Until a job or an
> applier is named, treat a green `--check` as evidence about the ledger's internal consistency and
> about nothing else.

**And the ledger owes rows.** Drafted for whoever applies, since a read-only reader may not write
them: a `[[reads]]` row with `read_id` for this read, `date = "2026-09-09"`,
`reader = "cold-read-7"`, `rotation_served = "docs/SECOND-READER.md"`,
`cursor_after = "docs/CLAIMS-LEDGER.md"`, plus `reviewed_in` on all five open findings, all five of
which are at `OPEN_READ_LIMIT` once two reads are recorded rather than none.

---

### F-7-05 — `docs/SECOND-READER.md:439` and `:447` — the page says twice that the eighth gate is not in CI, and it has been in CI since it was registered

**Severity: medium. Raised by cold read six as `F-6-05` and unapplied.** Re-verified rather than
re-quoted:

```
grep -rn "second_reader" .github/workflows/ci.yml
  118:  # `tools/second_reader.py --check` adjudicates the second-reader policy:
  129:  run: python tools/second_reader.py --check
```

`:439` — *"`<- new, and NOT in CI yet`"*. `:447` — *"**not** because CI does — no job invokes it
yet"*. Both false. This is `C6` on the page that wrote `C6`, and it is the third distinct thing this
page has been wrong about regarding its own gates.

**Exact replacement text** for `:439`: `` `<- the eighth; it runs in the lint job` ``. For
`:446-449`: *"and `python tools/second_reader.py --check` is listed here because a cold reader should
run it **and** because CI does — `.github/workflows/ci.yml:129`, in the `lint` job, since it was
registered as the fortieth gate. The paragraph that said otherwise stood for three rounds after the
job existed."*

---

### F-7-06 — `docs/SECOND-READER.md:431-441` — the cost block times eight commands and calls one of them the seventh; `CONTRIBUTING.md` says ten and carries the correction

**Severity: medium.** `C2`, and the interesting half is that the sibling page is already right.

`CONTRIBUTING.md:88` — *"Ten commands. All ten must be green before you push, and CI runs all ten"* —
followed by a block that lists ten and a note beginning *"This block said eight, and two of the ten
were missing from it in opposite directions"*, which explicitly warns a reader not to confuse the
list's length with the eight gate keys a run summary reports. **That page has been fixed and this
one has not.** `docs/SECOND-READER.md:431-441` times eight, annotates `gates.py --check` as *"the
seventh; the block below said six"*, and omits both `run_summary.py` commands entirely.

**Exact replacement text** for the annotation and the two missing rows: add

```
    0.09s  exit=0  python tools/run_summary.py --check
    0.09s  exit=0  python tools/run_summary.py --check-agent-summary   <- the ninth and tenth
```

and change the paragraph at `:443-449` to read *"**Three corrections in that block, and the count is
now ten.** The previous version timed six commands and called them 'the six gates'; it then timed
eight. `CONTRIBUTING.md` carries the derivation of ten and the warning that ten commands and eight
run-summary gate keys are two different eights. This page has now been wrong about its own gate
count three times, which is why the number belongs in `CONTRIBUTING.md`, which a test parses, and
not in a fence here."*

---

### F-7-08 — `docs/SECOND-READER.md:452-457`, `:477`, `:511`, `:529` — four structural counts, three already raised, and one that moved again this round

**Severity: medium.** Grouped because they are one defect class: a count the page states rather than
derives.

```
find src/acronymkit -name '*.py' | wc -l          ->  65
python tools/second_reader.py --check             ->  rotation: 25 file(s)
python tools/second_reader.py --cost
  the full user-facing corpus   206,644 words across 25 files
  the largest single file        52,832 words   docs/EVALUATION.md
  the median file                 3,470 words   docs/INSTALL.md
  the smallest                      770 words   SECURITY.md
```

* `:529` publishes `40` for the module count and derives *"the rotation from `21` entries to `61`"*
  from it. It is `65`, so the derived figure is `25` to `90`. Cold read six raised this as `F-6-03`
  measuring `64`; **the split's `core/selective.py` landed this round and moved it again**, which is
  the argument for deriving it rather than restating it.
* `:511` — *"`user_facing_files()` enumerates root files and `docs/*.md` and returns `21`, none of
  them source"*. It returns `25` and admits `docs/*.svg`; the function's own docstring at
  `tools/second_reader.py:222` announces the change in capitals. Cold read six's `F-6-04`.
* `:477` — *"one file, median `3,792` words"* — agrees with nothing: not with the `--cost` block
  eighteen lines above it (`4,362`, `docs/POSITIONING.md`), and not with the tool now (`3,470`,
  `docs/INSTALL.md`). **Three medians of one set on one page.** Cold read six's `F-6-10`.
* `:452-457` is the `--cost` snapshot. Its word counts are explicitly caveated — *"Quote the
  command, not the figures"* — and I do not raise those. **The file count is not a word count.**
  `21` there against `25` in section 3 is the same set counted twice on one page, which is `C1`, and
  the page's own history is that it has been wrong about this set's size three times.

**Exact replacement text** for `:529-532`: *"`--check` refuses any file `user_facing_files()`
enumerates that the rotation cannot reach, and the module count is derived rather than restated —
`find src/acronymkit -name '*.py' | wc -l` returned `40` when this paragraph was written, `64` after
the package split and `65` after `core/selective.py`. Admitting the package's source would take the
rotation from its current `25` entries to about `90`, so the set would turn over in ninety rounds
instead of twenty-five."* For `:477`: *"one file, median as `--cost` reports it — re-run it, and
note that the three values this row has carried came from three different files."*

---

### F-7-10 — `tests/test_claims_gate_coverage.py:193` — the module knows the difference between a live overlap and debris, and the entry guard does not use it

**Severity: medium, and it is the reason a red gate was reported to this round that is not a defect
in the tree.**

The module is explicit that a marker present may be benign. `:246-250` — *"A marker seen once may be
another process's injection, live, about to be restored ... A marker still there seconds later is
debris"* — and `test_no_probe_survived_an_earlier_run` implements exactly that at `:252-253`, waiting
ten seconds before failing. `_or_skip` at `:227-235` converts the **exit** race into a skip, with
the reasoning *"another process overwrote README.md while this injection was live, so the gate's
exit code is about a tree this test did not build"*.

`_run_gate_with_injection`'s **entry** guard at `:192-198` raises immediately, with no wait:

```
if _readme_debris():
    raise AssertionError(
        "README.md already carries a claims-gate probe marker. Either a previous run of "
        "this module died between injection and restore, or a second process is running "
        "it against this checkout right now. ..."
    )
```

The message itself names the benign cause as one of two possibilities and then treats both as
failures. **Measured here:** two tests failed under it while `README.md` was clean and carried zero
markers by the time I looked, the file passed `12 passed` alone, and the full suite then returned
`rc=0` at `6200` collected. Two sibling summaries in this round's scratchpad report the same class of
transient on this checkout from the other side.

**Exact replacement text** — reuse the wait the module already trusts:

> ```python
> deadline = time.monotonic() + 10.0
> while _readme_debris() and time.monotonic() < deadline:
>     time.sleep(0.5)
> if _readme_debris():
>     raise AssertionError(...)   # unchanged: ten seconds makes it debris, not an overlap
> ```

and add to the docstring: *"**Five guards.** The entry guard waits before it fails, for the same
reason `test_no_probe_survived_an_earlier_run` does: a marker seen once is another process's live
injection and a marker still there ten seconds later is debris. Failing on sight made a concurrent
sibling's run redden this one, which is a false red about somebody else's tree — the exact inference
`_or_skip` exists to refuse at the other end of the same function."*

---

### F-7-09 — `docs/EVALUATION.md:2864` — "all three parts", of a function that now returns three or five

**Severity: low; no number moves.** `gate_disclosure()` took one gate when this sentence was
written. It now takes two, and `src/acronymkit/nlp/propagation.py:460-469` appends
`gate.guarantee()`, `JOINT_NOT_SELECTIVE`, `selective.guarantee()`, `SELECTIVE_IS_NOT_ONE_SENSE` and
`PROPAGATION_GAP` — three parts for a conformal-only call, three for a selective-only call, five for
both. The paragraph is scoped to `gate=`, so *"all three parts"* is true of the call it is about and
does not say which call that is.

**Exact replacement text:** *"`acronymkit.nlp.propagation.gate_disclosure(gate)` returns all three
parts in one string so that no surface can quote one of them alone; passed both gates it returns
five."*

---

## 2. Question 4, per document. No abstentions.

| document | the sentence most likely to be false | the command that checked it |
|---|---|---|
| `docs/EVALUATION.md` *(trigger A)* | `:2853` "which is not implemented; when it lands, this gate tightens" | `grep` for the twin copy; read `propagation.py:80`. **F-7-01** |
| `docs/SECOND-READER.md` *(trigger B)* | `:447` "no job invokes it yet" | `grep -rn second_reader .github/workflows/ci.yml` → `:129`. **F-7-05** |
| `docs/CLAIMS-LEDGER.md` *(trigger A)* | `:490` the five-round half-width `6.64` | re-derived Wilson from `20/120` → `6.6446`. **Survives.** |
| `docs/GATES.md` *(trigger A)* | `:1727` "`36` collected, exhaustive over all `1,114,112` code points" | `pytest --collect-only` → `tests/test_unicode_properties.py: 36`. **Survives.** |

---

## 3. What I expected to find and did not. Each of these could have failed here.

**The wall clock is clean on this round's work, and that is the negative result the brief asked
for.** `bench/run_governed_deferral.py:1054` prints `"  UNARMED NOTE (R18): wall-clock and peak
traced Python allocation, over ..."`. `docs/EVALUATION.md:4700-4702` records that the commissioning
roadmap proposed two abort conditions — *"end-to-end time down `25` % and memory high-water down
`40` %"* — and that **R18 forbids both**, naming `D-013`. The falsifiers were re-adjudicated in
object counts with the unit change declared and the threshold **not** moved to suit it
(`:4770-4780`). No wall-clock figure in the new prose is a gate, a ratchet or an abort condition.

**The one armed wall-clock in this repository is pre-existing and registered as an R18 divergence,
not introduced this round.** `tools/gate_import_ceiling.py` sets `CEILING_MS = 30.0` and exits
non-zero above it, run at `.github/workflows/ci.yml:652`. The divergence is disclosed in three
places — the module docstring at `:46-49`, the workflow comment at `:646-650`, and
`docs/GATES.md:604-605`, all three saying *"R18 would have that half be an unarmed note with the
machine named"* and that changing it belongs in a commit that argues for it. I raise no finding: the
prose is accurate about the gate, which is what a cold read adjudicates.

**The suite's timing budgets are machine-scaled hang guards and say so.** `tests/conftest.py:155-168`
restricts this file to *"scaling assertions, which are machine-independent by construction"* and
*"hang guards, expressed as a multiple of this machine's measured speed"*; `machine_factor()` is
clamped below at `1.0` so a faster box tightens nothing. `tests/test_backronym.py:760` is such a
guard. Not an R18 violation and not raised.

**R17 on the new throughput prose: every figure carries a work count except the one `F-7-02` names.**
The timing fence is scoped *"over 20,000 identifiers of each corpus on the to_json arm"*; the object
tables carry `155,272` identifiers and `325,837` objects; the read census carries its `records`
column. The gap is that one column's cross-corpus identity claim, not a missing count.

**The sampling frame came out clean on all three of the brief's clauses, and I re-derived rather than
read.** `docs/CLAIMS-LEDGER.md:470` states the closed series at its final figure in the section
heading. The two restarts are stated in the section's own words — *"This is the second restart inside
two rounds, and that is recorded as a bad sign about the instrument rather than as a fresh start. ...
A third restart should be refused on this record alone."* Nothing implies continuation:
`tools/sample_claims.py:945` prints *"NOT comparable with the predecessor's ... different population,
different unit, different"*. And the arithmetic reproduces exactly:

```
python -c "wilson(23,144), wilson(20,120)"
  23/144  ->  15.9722 %,  [10.8852, 22.8275],  half-width 5.9712
  20/120  ->  16.6667 %,  [11.0560, 24.3453],  half-width 6.6446
  5+5+6+2+2+3 = 23        estimate move 0.694444  ->  the published 0.69
```

The page's own note that `0.70` is the difference of two rounded percentages while `0.69` is the
rounded difference of the exact values is correct in both directions.

**`CONTRIBUTING.md`'s gate list is correct and self-aware, and I expected it not to be.** It says
ten, lists ten, and warns against reading its length as the eight run-summary gate keys. Worth
recording that **the standing brief's own nine-gate list is one short of the tree**: it omits
`python tools/run_summary.py --check` at `ci.yml:190`.

**The disclosed defect in a public verb is real and reproduces in three lines.**
`docs/EVALUATION.md:4614-4619` says `audit_identifiers` has no handler for an unreadable character.
Confirmed — and my first probe was broken rather than the claim, which is the `F` mutation's lesson
arriving on schedule:

```
audit_identifiers([':@computed_region_abc'])        -> TypeError: missing 'dictionary'      (my bug)
audit_identifiers([':@computed_region_abc'], None)  -> ConfigurationError                   (a different guard)
audit_identifiers([':@computed_region_abc'], GovernedDictionary())
                                                    -> TokenizationError: normalize cannot correct
                                                       ':@computed_region_abc' without losing part of it
audit_identifiers(['CUST_ID'], GovernedDictionary()) -> CorpusAudit                          (positive control)
```

**The `4.38` figure is correctly retained everywhere it appears.** `CHANGELOG.md:128`,
`docs/EVALUATION.md:899-901` and `src/acronymkit/nlp/propagation.py:162` all scope it to `gate=`.
The obsolete-caveat sweep found exactly one stale site, `F-7-01`, and I record the negative on the
other four.

---

## 4. What this read could not check

* **`R19` byte-identity is carried on two workstreams' word.** `selective.identity` reports
  `3,882` records and `governed_perf.*.deferral.identity_*` reports zero mismatches on three arms.
  The governed corpora are absent from this checkout and re-running either harness writes to the
  tree, which section 5 forbids this reader. Same disposition as cold read six.
* **No mutation was run in situ.** Every mutation this round's documents lean on edits `src/` or
  `tests/`. `F-7-10` is refuted without one because the failure happened to me unbidden and the
  negative control — the same file passing alone, and the whole suite passing — was available for
  free.
* **The four SVG figures were not read.** Trigger B served `docs/SECOND-READER.md`; the cursor is
  followed, not chosen.
* **`docs/OFFLINE.md`'s module count is still wrong and no trigger reached it.** Cold read six left
  it recorded rather than raised; the count it should be compared against moved again this round, to
  `65`.
* **The protocol can be satisfied without being performed.** My only defence is that every finding
  above carries a command I ran in this checkout before writing it down. `F-2026-08-25-02` is this
  repository's record of that defence failing when the command, not the sentence, was broken — and
  it failed for me once this round, on the `audit_identifiers` probe in section 3.

---

## 5. The pre-registration, verbatim, and what it cost

Written to `scratchpad/COLD-READ-5-PREREG.txt` before any file was opened beyond the tool's output,
the policy page and the trigger listings.

```
Bet: the three areas the brief names each contain at least one sentence that is false or
obsolete against the tree, and the highest-yield defects are OBSOLETE CAVEATS rather than
missing ones.

F1 -- THE SELECTIVE-RISK PROSE. I predict docs/EVALUATION.md and/or docs/CLAIMS-LEDGER.md
     retain at least one hedge written for the joint bound (the 4.38x overshoot) applied to a
     method that now controls selective risk, OR state the new guarantee more tightly than the
     measurement supports.
     WRONG IF: every guarantee sentence in the trigger-A diff matches what the shipped code
     proves at the alphas actually measured, AND no retained caveat refers to a bound the code
     no longer computes.

F2 -- THE WALL CLOCK. I predict a wall-clock figure appears somewhere in prose in a load-bearing
     position (a gate, a ratchet, an abort condition, or a threshold a reader must not cross).
     WRONG IF: grep over the whole tree finds every wall-clock figure inside an explicitly
     unarmed NOTE with the machine named, and every throughput number carries its work count.

F3 -- THE SAMPLING FRAME. I predict docs/CLAIMS-LEDGER.md either (a) fails to state the closed
     series at its final figure, or (b) implies the new number continues it, or (c) does not say
     that the frame restarted twice in two rounds.

F4 -- THE STALE-COUNT PREDICTION ON MY OWN TRIGGER-B FILE. I predict at least three places on
     that page still say twenty-one or narrate a superseded cursor.
     WRONG IF: every count on the page is either derived at read time or carries the command.
```

**Outcomes. Three of four falsifiers fired, and the bet's own framing was half wrong.**

| | outcome |
|---|---|
| **F1** | **DID NOT FIRE, in both directions at once.** The prediction was a disjunction and both disjuncts landed: `F-7-01` is the retained hedge, `F-7-03` is the guarantee stated too tightly. The bet was right and it was right for two reasons rather than one |
| **F2** | **FIRED.** No wall-clock figure in this round's work is armed anywhere. The one armed ceiling in the tree is pre-existing and disclosed in three places. **Published as the negative result it is**, per the brief |
| **F3** | **FIRED, on all three clauses.** The closure is stated at its final figure, nothing implies continuation, and the two restarts are named as a bad sign in the page's own words. The arithmetic reproduces to four decimal places |
| **F4** | **DID NOT FIRE.** Four such places: `:452`, `:477`, `:511`, `:529`. Three were already raised by cold read six and are unapplied; `:529` moved again this round |

**What the pre-registration bought that a free-form read would not have.** F2 and F3 were the two
areas the brief pointed hardest at, and both came out clean. Without a falsifier written down first,
the cheap move is to file a weaker version of the same suspicion — *"the wall-clock note could be
clearer"* — and call it a finding. The commitment made the honest answer available, and it is the
answer for two of the three named areas. **The defects are one layer in from where the brief
pointed**: not the guarantee's substance but its phrasing on two of three surfaces, not the wall
clock but the work count in the table beside it, and not the sampling frame but the policy page that
is supposed to be reading all of it.

**The method commitment held, and cost me one probe.** *"A finding whose refutation I could not
execute is filed as UNVERIFIED and says so."* Nothing is filed UNVERIFIED. The adversarial
commitment — *"for every gate I claim is blind, I run the positive control"* — is what turned the
`audit_identifiers` probe from a finding into a bug of mine, in section 3, and what kept `F-7-10`
from being reported as a defect in the tree.

---

## 6. Drafted ledger rows

`docs/cold-reads.toml` is machine state a read-only reader may not write. Drafted for the applier:
one `[[reads]]` row (`reader = "cold-read-7"`, `date = "2026-09-09"`,
`rotation_served = "docs/SECOND-READER.md"`, `cursor_after = "docs/CLAIMS-LEDGER.md"`,
`trigger_a` naming the three files above), ten findings `F-7-01` … `F-7-10` all born `open` with the
owners implied by their files, and `reviewed_in` on `F-5-3`, `F-5-5`, `F-5-6`, `F-5-7` and `F-5-8`.

**Read `F-7-07` before writing them.** Advancing the cursor is a coupled edit to this ledger and to
`docs/SECOND-READER.md`'s cursor block, and whoever makes it is the second name
`disposition = "fixed"` requires. Two of the last four reads produced no row, and neither the cursor
check nor the decay clock noticed.
