# Cold read 4 — findings, 2026-08-26

The fourth execution of [`docs/SECOND-READER.md`](../SECOND-READER.md), and the second under the
read-only rule. The reader wrote nothing except this file. No page was edited, no gate was relaxed,
no figure was moved into a fence, and `docs/cold-reads.toml` was **not** written — which is
[`P-1`](#p-1--the-rotation-cursor-has-now-stalled-for-two-consecutive-reads-and-the-stall-is-observed-rather-than-predicted)
below, unchanged from the third read and now with a second observation behind it.

**How numbers are handled on this page.** Every figure here is a property of *these documents* or of
a command's output, not a measurement of the library, and no benchmark runner can `--save` a
property of a document. So they appear fenced or code-spanned **with the command printed beside
them**, which is the convention [`docs/CLAIMS-LEDGER.md`](../CLAIMS-LEDGER.md) §1 and
[`cold-read-3-findings.md`](cold-read-3-findings.md) already use. D-052 is explicit that fencing
silences the claims gate completely; the command is printed with every block so that a reader can
re-derive rather than trust. A figure here you cannot re-derive from a command on this page is a
defect in this page.

---

## 0. What was read, and the state it was read in

```
git rev-parse --short HEAD               387f739   (working tree dirty, mid-round)
python tools/second_reader.py --trigger  6 user-facing file(s)
python tools/second_reader.py --check    rotation: 21 file(s); trigger B serves
                                         docs/SUPPORT_MATRIX.md next
                                         findings: open 6, fixed 0, blocked 1, permanent 0 (of 7)
                                         OPEN AND AT THE LIMIT: 5 of 6
```

**Trigger A served six files**, and they are the whole of this read's diff scope: `CHANGELOG.md`,
`docs/CLAIMS-LEDGER.md`, `docs/DEFINITION-OF-DONE.md`, `docs/EVALUATION.md`, `docs/GATES.md`,
`docs/SECOND-READER.md`. `docs/DECISIONS.md`, both `docs/AUDIT-*.md` and `docs/cold-reads.toml` are
modified in the same tree and were correctly **not** served — three halves of section 3's exclusion
rule exercised on files nobody wrote for the test.

**Trigger B served `docs/SUPPORT_MATRIX.md`**, verified against the ledger and the tool rather than
against a sentence:

```
python tools/second_reader.py --check | grep 'trigger B'
  rotation: 21 file(s); trigger B serves docs/SUPPORT_MATRIX.md next

python - (parse_rotation over docs/SECOND-READER.md's <!-- rotation-set --> block)
  entry 5 = docs/SUPPORT_MATRIX.md   entry 6 = docs/GATES.md

sed -n '/<!-- rotation-cursor -->/,/^```$/p' docs/SECOND-READER.md
  cursor docs/SUPPORT_MATRIX.md
```

**The cursor moves to [`docs/GATES.md`](../GATES.md)**, entry six of twenty-one. That is the whole of
this read's contribution to the rotation state and **somebody else has to write it**, per `P-1`. Note
that `docs/GATES.md` is *also* in this round's trigger A, so entry six is served either way — which
is luck, not the mechanism, and is the second consecutive read where the mechanism did not decide
what was read.

**Gates, run at the start and again at the end of the read, unchanged in between.**

```
python -m pytest tests                      rc=0   5395 passed, 10 skipped, 1 xfailed
python -m ruff check src tests tools bench  rc=0   All checks passed!
python -m ruff format --check ...           rc=0   140 files already formatted
python -m mypy                              rc=0   no issues found in 90 source files
python tools/check_claims.py                rc=0   value-matched 64 of 64, deferred 189 of 189
python tools/splits.py --check              rc=0
python tools/gates.py --check               rc=0   CARRYING IN-SITU EVIDENCE: 12 of 36
python tools/second_reader.py --check       rc=0   open 6, blocked 1, of 7
```

**No file changed under this reader.** Every probe below is a read, a `git` query, an import, or a
build into a scratch directory outside the repository.

---

## P. Findings against the policy itself

### P-1 — The rotation cursor has now stalled for two consecutive reads, and the stall is observed rather than predicted

Cold read 3 raised this as a mechanical consequence. It is now a measurement.

`docs/cold-reads.toml` holds two `[[reads]]` rows, newest `2026-08-25`, `rotation_served =
"docs/GOVERNED_NAMING.md"`. Cold read 3 served `docs/SUPPORT_MATRIX.md` and could not record it. So
`--check` still derives `docs/SUPPORT_MATRIX.md` as the file trigger B serves next, and this read
served it too.

```
python -c "...load docs/cold-reads.toml..."
  reads: 2   newest id 2026-08-25   rotation_served docs/GOVERNED_NAMING.md
python tools/second_reader.py --check | grep 'trigger B'
  trigger B serves docs/SUPPORT_MATRIX.md next
```

**Trigger B has served entry five twice running while `--check` stayed green throughout.** Section 3
says the set "turns over in twenty-one rounds"; at the observed rate it turns over in never.
Section 5.3's own measurement — *"a read-only reviewer whose findings rot is worse than one who fixes
things"* — now has a second instance, and this time the rotting finding is about the rotation itself.

**Disposition: blocked on a named decision**, unchanged from cold read 3, and the decision is
one sentence: is the read-only boundary *prose* (the reader may write `docs/cold-reads.toml` and
nothing else, which is what the `applied_by` rule in section 5.1 was designed for) or *filesystem*
(the reader writes a note and a second party transcribes)? Section 5.1 says in terms that the
boundary "is not a filesystem permission". Two consecutive briefs have made it one.
[Section 3](#3-ledger-rows-paste-ready) below carries the rows in paste-ready TOML so that the second
party's job is transcription rather than authoring.

**And there is a consequence the second party must see before pasting.** Five of the six open
findings are printed `OPEN AND AT THE LIMIT`. Adding a `[[reads]]` row for this read makes those five
span three reads, which `OPEN_READ_LIMIT = 2` refuses. Pasting the read row **without** dispositioning
those five turns `python tools/second_reader.py --check` red. That is the mechanism working, and it
should not be mistaken for the paste being wrong.

### P-2 — Section 4.3's in-situ mutation is still forbidden to the reader

Unchanged from cold read 3 and re-affirmed rather than re-argued. Section 4.3 requires a mutation *in
the tree*; a mutation is a write. Every check below is a read, a `git` query, an import, or a build
into a scratch directory. The one gate demonstration this read *can* offer without writing to the
tree is the sdist build in [`F-4-1`](#f-4-1--three-documents-say-the-sdist-omits-two-registers-it-ships-and-one-of-the-three-is-a-source-file),
which is a positive observation rather than a mutation.

### P-3 — Section 6 still publishes two different medians for the same quantity, and now a third

Cold read 3's `P-4`, unaltered one round later. `docs/SECOND-READER.md:428` (inside the `--cost`
fence) reports the median file as `4,362` words; `docs/SECOND-READER.md:450` (the cost table) reports
`median 3,792 words`. Re-run today the command reports a third value:

```
python tools/second_reader.py --cost
  the full user-facing corpus   156,216 words across 21 files
  the largest single file        37,501 words   docs/EVALUATION.md
  the median file                 4,536 words   docs/POSITIONING.md
  the smallest                      770 words   SECURITY.md
```

The fenced block is dated and says *"mid-round and moving; re-run it"*, so it is a snapshot and not an
error. The table cell is typed, carries no date and no command, and is the one figure on that page
the page's own capitalised paragraph — *"neither is fixed by typing better numbers into the same
fence"* — was written to stop. **Exact correction, unchanged from cold read 3:** replace
`median 3,792 words` with `median: see the --cost block above`.

**The same asymmetry, one screen up.** Section 6's timing block reports `4980 passed`; the suite is
`5395` today and was `5208` at cold read 3. The block is environment-stamped and dated, so it is a
snapshot — but the page applies *"quote the command, not the figures"* to the `--cost` block below it
and not to this one, and this one has now drifted by `415` tests.

---

## 1. Trigger B — `docs/SUPPORT_MATRIX.md`

**Strongest claim**, line 9: *"Every cell below was produced by running the thing on the host in
[Measurement environment](#measurement-environment), **except where a cell says otherwise, which it
does explicitly**."*

**What a reader must believe.** (a) There is one host and it is described. (b) The description is
accurate about that host. (c) Every unmarked cell was produced by running something. (d) Every marked
cell marks itself.

**Whether that survives the gates.** No gate reads this page's prose. `python tools/check_claims.py`
scans it under `docs/*.md` and arms nothing in it — its figures are token counts, byte counts and
call counts rather than accuracy percentages, and `--classify` puts the whole file outside the
deferred ledger. Belief (c) was re-derived exhaustively by cold read 3 and every measured cell
reproduced; this read did not re-run that sweep and does not claim it.

**Belief (b) is the one that fails, and it fails in the same place as one round ago.**

**S-1 (carried, unfixed) — the environment row names a version this tree does not carry.** Line 169:

> | `acronymkit` | 0.2.0, source checkout (`src/` layout) |

```
grep -n '^version' pyproject.toml                                            version = "0.3.0"
PYTHONPATH=src python -c "import acronymkit; print(acronymkit.__version__)"  0.3.0
git log -1 --format=%h -- docs/SUPPORT_MATRIX.md                             d94cdf8
```

Cold read 3 raised this on 2026-08-25 with the exact replacement text attached. The page has not been
touched since `d94cdf8` and the row is unchanged. **This is the second consecutive read to raise it.**

**S-2 (carried, unfixed) — `F-2026-08-24-05`, third consecutive read.** Line 39 still names nine
commands under *"All of"*:

```
grep -c '\.command(' src/acronymkit/cli.py     16
```

Nine under an exhaustive word on a sixteen-command CLI. The seven the sentence does not reach are the
governed half — `expand-token`, `expand-identifier`, `physical-name`, `normalize-name`, `check-name`,
`governed-batch`, `governed-audit` — which is the half `docs/POSITIONING.md` commits the library to
leading with. Raised 2026-08-24, re-affirmed 2026-08-25, re-affirmed by cold read 3, unaltered.

**S-3 (carried, unfixed) — line 156, *"and until this round it listed seven"***, in a file no commit
since `d94cdf8` has touched. *"This round"* in an untouched document is a phrase that ages into a
lie. **Exact correction:** replace `and until this round it listed seven` with
`and before 2026-08-24 it listed seven`.

**Q4 nomination for this document:** `docs/SUPPORT_MATRIX.md:169`, *"0.2.0, source checkout"*.
Checked by `grep -n '^version' pyproject.toml` and by importing `acronymkit.__version__`. **False.**

---

## 2. Trigger A

### 2.1 `src/acronymkit/__init__.py` — the docstring, read as a stranger

Not in trigger A. Not in the rotation. Reachable by no mechanism on the policy page — see
[section 4](#4-should-the-rotation-cover-source-files-yes-and-the-costing-that-says-no-uses-the-wrong-denominator).
Read here because the brief pointed at it, which is the third consecutive round in which this file
arrived by pointer-chase.

**Strongest claim**, line 1 and the paragraph under it: *"acronymkit — a governance instrument for
names somebody else owns. … Its first obligation on that subject is to report *unknown* rather than
to return a plausible answer."*

**What a reader must believe.** (a) The library's subject is a name it does not control. (b) Refusal
is the design in `acronymkit.governed` rather than a setting. (c) The runnable examples run. (d) The
supporting capabilities are described without inflation. (e) The import-policy claims hold.

**Whether it survives the gates. Mostly yes, and better than the page it replaced.**

```
PYTHONIOENCODING=utf-8 PYTHONPATH=src python -m doctest src/acronymkit/__init__.py
  rc=0   -- 11 tests in 4 items, 11 passed

PYTHONPATH=src python -c "...from_mapping TXN/ID; expand_identifier('TXN_KYC_ID')..."
  phrase             'Transaction Kyc Identifier'
  is_fully_known     False
  unknown_tokens     ['KYC']
  KYC token          is_known=False  confidence=0.0

PYTHONPATH=src python -c "...expand_identifier('TXN_<emoji>_ID')..."
  phrase 'Transaction Identifier'  is_fully_known False  unaccounted ('<emoji>',)
    -> both halves of "false the moment one token went unresolved OR one character went
       unaccounted for" hold; expansion.py:589 is `not parts.unaccounted and all(...)`

PYTHONPATH=src python -c "import sys, acronymkit; print([m for m in sys.modules
                          if m.startswith('acronymkit.')])"
  []                 -- "import acronymkit binds no submodule at all" holds

PYTHONPATH=src python -c "...exec('from acronymkit import *')..."
  star == __all__    True, 49 names

PYTHONPATH=src python -c "...walk_packages, import every submodule, list non-stdlib..."
  pydantic, pydantic_core, annotated_types, typing_extensions, typing_inspection
    -- and NOT click, even after `import acronymkit.cli`. The purity sentence holds.

PYTHONPATH=src python -c "acronymkit.normalize_name is governed.compliance.normalize"
  True
```

**The docstring does not trade one overclaim for the opposite one, and the paragraph that would have
is the one that saves it.** The strongest sentence in it is *"Its first obligation … is to report
unknown rather than to return a plausible answer"*, and a reader who stopped there would take away
something false about the default. The next paragraph is titled *"Read the flag; the phrase alone
will not tell you"* and says, in terms, that the default still returns
`'Transaction Kyc Identifier'`, that `is_known` is `False` and confidence `0.0`, and that **"a caller
that reads only `phrase` gets a governed-looking string for a token no catalog approved."** That is
the foot-gun disclosed on the front door of the package, in the same screen as the pitch. It is the
single best thing in this file and it is what makes the governance framing honest rather than a new
slogan.

**F-4-4 — one sentence in it is a false phrasing, and it is the governance-flavoured overclaim the
brief was looking for.** Lines 45 and 68-70:

> *"Generation, backronym synthesis, extraction and contextual disambiguation ship in the same typed
> package, and none of them leads. … Each of these is measured wherever a corpus exists that can
> measure it, and **each keeps its losing comparison in the same table as its own figure.**"*

Count both sides — check `C1`, an exhaustive word over an enumeration. Four capabilities are
enumerated. `docs/EVALUATION.md`'s own section headings settle it:

```
grep -n '^## ' docs/EVALUATION.md
  149   Extraction: measured against four systems
  500   Generation: recall@k over 1,221 real pairs
  673   Disambiguation: measured for the first time, and it loses to a trivial baseline
  3279  The backronym subsystem: an accuracy number for `align`, none for `synthesize`
```

- **extraction** — beaten by two named systems in the same table. Holds.
- **disambiguation** — loses to a trivial baseline, in the heading. Holds.
- **generation** — the only comparison in that section is between this library's own four presets.
  The section's second sentence is *"Generation previously had no external evaluation"*. There is no
  losing comparison to keep.
- **backronym synthesis** — has no figure at all, by that heading's own words, and
  `docs/DEFINITION-OF-DONE.md` criterion `2` reads *"`synthesize` carries none and is **permanently
  unmeetable**"*.

So *each* is true of two of the four named, and of one of those two the enumerated capability
(`synthesize`) has no figure for a comparison to sit beside. The hedge in the first clause
(*"wherever a corpus exists that can measure it"*) does not reach the second clause, which is
unqualified.

**Exact replacement text**, for `src/acronymkit/__init__.py`, replacing

```
Each of these is measured wherever a corpus exists that can measure it, and each
keeps its losing comparison in the same table as its own figure. Extraction is
beaten on the corpus it is scored on by two compiled systems, and that is
published rather than tuned away.
```

with

```
Each of these is measured wherever a corpus exists that can measure it, and where
a competitor exists the losing comparison is in the same table as our own figure.
Extraction is beaten on the corpus it is scored on by two compiled systems, and
disambiguation loses to a trivial baseline; both are published rather than tuned
away. Generation has no external comparison at all, and backronym *synthesis* has
no accuracy figure at all -- ``docs/EVALUATION.md`` says so in its own section
headings, and the second is permanently unmeetable rather than merely unmeasured.
```

**The same sentence is in `docs/POSITIONING.md` line 52-54** — *"each one keeps its losing comparison
in the same table, which is the whole of what a governance instrument can offer about itself"* — so
this is a `C2` pair and a fix to one copy leaves the other false. That page is out of both triggers
this round and the finding is reported against it rather than checked further.

**Two lesser notes, neither a falsehood.** *"building the core schema for `Config` alone dominates
this package's import cost"* is a performance claim with no work count and no citation behind it;
under R17 it is a null result as stated, and `bench/run_micro.py` records the three figures that
would support it. And *"is the second-largest thing this package used to import"* is a historical
claim about a tree that no longer exists, unverifiable from this one.

**Q4 nomination:** `src/acronymkit/__init__.py`, *"each keeps its losing comparison in the same table
as its own figure"*. Checked by `grep -n '^## ' docs/EVALUATION.md` against the four capabilities the
same sentence enumerates. **False for two of the four.**

### 2.2 `docs/CLAIMS-LEDGER.md`

**Strongest claim**, line 24-25: *"A figure you cannot re-derive from a command on this page is a
defect in this page."* — resting on line 77: *"**Only the `deferred` column is stable.** It is the
ratcheted one … Read the `deferred` column as a fact and the rest as a reading taken at a moment."*

**What a reader must believe.** (a) Every figure here has its command printed beside it. (b) The
`deferred` column is stable in the sense that it does not move except in a commit that records a
round. (c) Therefore the `deferred` figures on this page are current.

**Whether that survives the gates.** (a) holds. (b) holds — the ratchet is real and
`trajectory_problems` enforces it. **(c) does not follow from (b) and does not hold**, and it is the
column the page tells you to read as a fact.

**F-4-2 — every published `deferred` figure on this page is one to five rounds stale, including the
one the page calls stable.** Three blocks, one command each:

```
python tools/check_claims.py --classify | head          -- re-derived 2026-08-26

  bucket          deferred  unexamined   total          page, line 57-64:
  gate-able             55         200     255            gate-able      92    200    292
  blocked              130          10     140            blocked       135     10    145
  not-a-claim            4         486     490            not-a-claim     4    377    381
  unclassified           0        1095    1095            unclassified    0    939    939
  ALL                  189        1791    1980            ALL           231   1526   1757

python tools/check_claims.py | grep 'ledger trajectory'  -- re-derived 2026-08-26

  ledger trajectory: 6 rounds | M3-PA (the second walk) moved 12 (citation 3, deletion 9,
  fencing 0, other 0) | 12 of them out of docs/DECISIONS.md | deferred 189, value-matched 64

  page, line 260-262:
  ledger trajectory: 3 rounds | M2-P4 (the recorder is bound) moved 31 ... deferred 231

python tools/check_claims.py --classify | grep 'docs/DECISIONS.md'
  docs/DECISIONS.md   42   ...      -- page, line 295: "`84` deferred numbers remain"
```

`docs/CLAIMS-LEDGER.md` is in this round's trigger A: it was edited to append §6 while
`tools/check_claims.py` was edited in the same tree to add `LedgerRound(label="M3-PA (the second
walk)", deferred=189)` and to move `RECORD_FILE_PIN` from `84` to `91` records. **The round that
moved the ledger did not update the page whose subject is the ledger.** Section 4's whole arithmetic
— *"`115 → 84` is a fall of `31` in one round against a floor of `12`"*, *"Forty-eight of the
eighty-four sit in two records"*, *"The reachable remainder is `29`"* — is computed from a `84` that
is now `42`.

**Exact corrections.** All three blocks are fenced command output; the honest edit is to re-run each
command and paste, not to re-type a figure. The two typed sentences that must change with them:

- line 295: replace ``` `84` deferred numbers remain, and the residue is not evenly spread. **Forty-eight of the eighty-four sit in two records** ``` with a re-derivation from
  `python tools/check_claims.py --classify | grep 'docs/DECISIONS.md'`, and re-take the per-record
  table beneath it, which no longer sums to the file's ledger.
- line 315-321: the paragraph beginning *"The binding is not symbolic"* re-states `115 → 84` and
  `27 %`; it is a statement about the `M2-P4` round and is true of it, but it is written in the
  present tense about a residue that has since fallen twice more. It needs a date or a round label.

**F-4-3 — §6 says the sampler has run twice; the record it was written to ship, and the changelog
entry that points at it, both say three. This is the sharpest finding of the read.**

`docs/CLAIMS-LEDGER.md:421`: *"**It has run twice.**"*
`docs/CLAIMS-LEDGER.md:431`: *"`20.8` % of sampled claims not true, both rounds, on an identical
`5`-of-`24` split. **That is the number to attach to a narrative sentence quoted out of this
repository.**"*

`docs/DECISIONS.md` D-088, written in the same round, whose **Status** line names
`docs/CLAIMS-LEDGER.md` §6 as a shipped site:

```
grep -n 'Three rounds now read\|Round three is' docs/DECISIONS.md
  "**Kept:** the headline rate. Three rounds now read `20.8` %, `20.8` % and `25.0` % not-true."
  "Round three is `6` of `24` **not-true** = `25.0` %, and `5` of `24` **strictly false**
   = `20.8` %. Anybody who reads \"`20.8` % again\" off this round is reading the false-only
   row against two prior rounds' not-true rows."
```

`CHANGELOG.md`, same round, same tree, pointing the reader at §6:

```
git diff CHANGELOG.md | grep -n 'has now run three times' -A2
  "A sampled audit of this project's own claims has now run three times. The **headline error
   rate stands** -- somewhere in the low-to-mid twenties per cent of sampled claims are not
   true ... `docs/CLAIMS-LEDGER.md` §6; `docs/DECISIONS.md` D-088."
```

So a reader who follows the changelog's pointer — check `C5` — arrives at a section that says the
opposite of what sent them, and the figure §6 tells them to quote is the exact figure D-088 says is
the wrong row. §6 also carries the two-round framing throughout: *"It retires a decomposition on two
observations"* (551), *"The headline rate is itself two points"* (560), *"unmeasured for the second
round running"* (541), and its transcription note names D-068 and D-082 and not D-088.

Three further sentences in §6 are superseded rather than merely incomplete: *"The identical figure is
a coincidence"* (there is no longer an identical pair to be a coincidence about); *"The ratio is
`0.75x`: it did not shrink, it inverted"* (D-088's table adds a third point at `1.00x` on equal
denominators, which is a stronger retirement than an inversion); and the sensitivity figure
*"about plus or minus eight points"* (D-088 measures `±4` for round three and says *"Every
between-round difference so far is smaller than the within-round grader uncertainty"*).

**Exact replacement text** for `docs/CLAIMS-LEDGER.md:421`, the sentence ending the opening paragraph
of §6 — replace `**It has run twice.**` with:

```
**It has run three times.**
```

and for lines 429-432, replacing the whole of *"### The headline rate stays"* and the sentence under
it:

```
### The headline rate stays, and the third round is why it is a band rather than a point

`20.8` %, `20.8` % and `25.0` % of sampled claims not true, over three rounds. **Quote the band,
not the point**: round three reads `6` of `24` not-true and `5` of `24` strictly false, so its
`20.8` % is the *false-only* row against two prior rounds' *not-true* rows, and reading "`20.8` %
again" off it compares two different quantities. Round three wrote its boundary down before
grading and measured its own sensitivity at about `±4` points; D-082 measured `±8`. **Every
between-round difference so far is smaller than the within-round grader uncertainty.** The
statement to attach to a narrative sentence quoted out of this repository is: this project's
reporting fails somewhere in the low-to-mid twenties per cent, and no round has been powered to
say more than that. `docs/DECISIONS.md` D-068, D-082, D-088.
```

The three superseded sentences at `551`, `560` and `541` need *two* changed to *three* and the
`±8` re-stated as a range across rounds; the `0.75x` paragraph needs D-088's third row
(`25.0` vs `25.0`, `1.00x`, equal denominators) appended, because a third point that is dead flat is
the strongest evidence for the retirement §6 argues for and §6 does not have it.

**Q4 nomination:** `docs/CLAIMS-LEDGER.md:431`, *"`20.8` % of sampled claims not true, both rounds …
That is the number to attach to a narrative sentence quoted out of this repository."* Checked against
`docs/DECISIONS.md` D-088 and against `CHANGELOG.md`'s own entry pointing at this section. **False,
and it is the sentence the round's own record was written to retire.**

### 2.3 `docs/GATES.md`

**Strongest claim**, the line under *Read this before the table*: *"**Twelve of the thirty-six gates
carry in-situ evidence, and the count went DOWN this round.**"*

**What a reader must believe.** (a) The register holds thirty-six gates. (b) Twelve carry a run id
and a commit. (c) The fall is a withdrawal rather than a regression. (d) The rest of the page's
claims about what is and is not shipped are current.

**(a) through (c) survive, exactly as written.**

```
python tools/gates.py --check
  gate manifest: 36 gate(s) across 23 environment(s) in 5 workflow file(s)
  mutation kind: automated 16, control 2, inline 5, manual 13
  CARRYING IN-SITU EVIDENCE:   12 of 36
  in-situ quota: debt 24, ceiling 24 | M3-PA ... withdrew ['suite'], owes 4 forward

grep -cE '^no_gates_reason' .github/gates.toml        10
  -- "Eight jobs carry no gate at all ... Two more were added this round" = 10. Holds.
```

`16 + 2 + 5 + 13 = 36`; the withdrawal is attributed in the trajectory row; the top-of-ranking rule
and the four owed-forward gates are all printed by the tool. This is the best-instrumented page in
the read.

**(d) is where it fails, and it fails on a sentence the round beside it made false.**

#### F-4-1 — three documents say the sdist omits two registers it ships, and one of the three is a source file

`docs/GATES.md:1208-1211`:

> **`.github/gates.toml` is not shipped in the sdist, and this page is.** `MANIFEST.in` ships
> `recursive-include docs *.md` and `.github/workflows/*.yml`, and nothing else from `.github/` — so a
> reader holding a distribution gets this page, follows its link to the register in the second
> paragraph, and finds nothing. … `MANIFEST.in` was not this workstream's file; one line adds it, and
> until somebody writes that line this is the fifth instance.

`docs/SECOND-READER.md:527-528`:

> **The gate that does exist has a hole with a known shape.** `MANIFEST.in` ships `docs/*.md`, so
> `docs/cold-reads.toml` is absent from an sdist exactly as `.github/gates.toml` is.

`tools/second_reader.py:79-83`, the module docstring:

> **The ledger is not in the sdist.** ``MANIFEST.in`` ships ``docs/*.md``, so
> ``docs/cold-reads.toml`` is absent from a distribution exactly as ``.github/gates.toml`` is.

**All three are false on this tree.** Somebody wrote the line — two lines — in `387f739`, the commit
titled *"two artifact-environment jobs, and the second one found five shipped documents pointing at
files the sdist never carried"*. Refuted against a real sdist rather than against `MANIFEST.in`:

```
git show HEAD:MANIFEST.in | grep -n 'gates.toml\|cold-reads'
  93:include .github/gates.toml
  94:include docs/cold-reads.toml

python -m build --sdist --outdir <scratch>            Successfully built acronymkit-0.3.0.tar.gz
python - (tarfile over the built sdist)
  .github/gates.toml      True
  docs/cold-reads.toml    True
  docs/GATES.md           True
  docs/SECOND-READER.md   True
```

This is `C2` and `C6` at once, three copies deep, and the third copy is in a source file that no
trigger on the policy page can reach — see [section 4](#4-should-the-rotation-cover-source-files-yes-and-the-costing-that-says-no-uses-the-wrong-denominator).
It is also the sharpest possible instance of the class both pages exist to catalogue: **a prose claim
about a tool's configuration, gone false because somebody fixed the thing it complains about.**

**Exact replacement text.**

For `docs/GATES.md:1208-1217`, replace the whole bullet with:

```
**`.github/gates.toml` is shipped in the sdist, and it was not until `387f739`.** For as long as
`MANIFEST.in` carried only `recursive-include docs *.md` and `.github/workflows/*.yml`, a reader
holding a distribution got this page, followed its link to the register in the second paragraph,
and found nothing -- the `data/LICENSES.md` shape, a shipped document citing evidence the
artifact omits, and the fifth instance `MANIFEST.in`'s own comment enumerates. It was closed by
the second-reader rotation's existence check running inside the extracted tree, which is the only
environment where the absence is visible, and `tests/test_packaging_manifest.py` now derives the
rule from the tree: every relative link out of every shipped markdown file must resolve to
something the sdist also ships. **This page carried the un-fixed sentence for one round after the
fix landed**, which is why it is corrected in place rather than deleted. The tests in
`tests/test_gate_manifest.py` that read the register still skip on the narrow `needs_register`
mark, which is now belt and braces rather than the only thing standing between them and an error;
how many of them there are was not re-measured this round, for the reason given above.
```

For `docs/SECOND-READER.md:527-532`, replace the whole bullet with:

```
**The gate that does exist had a hole with a known shape, and it is closed.** `MANIFEST.in`
shipped `docs/*.md` and not `docs/cold-reads.toml`, so `--check` in an extracted sdist failed
loudly on a file that was not there rather than passing vacuously -- the D-058 fourth-instance
shape, a gate that cannot fail where every file it scans is present by construction, named in
advance on this page rather than found by a red release job. `387f739` added
`include docs/cold-reads.toml` alongside `include .github/gates.toml`, and
`tests/test_packaging_manifest.py` now derives the rule rather than remembering it. What remains
true is the reason the hole mattered: this gate belongs to a checkout environment and is still
not registered in one, because no CI job invokes it. That is the paragraph above, not this one.
```

For `tools/second_reader.py:79-83`, replace the paragraph with:

```
**The ledger is now in the sdist, and it was not.** ``MANIFEST.in`` shipped ``docs/*.md`` and not
``docs/cold-reads.toml``, so ``--check`` failed loudly in an extracted distribution rather than
passing vacuously. ``387f739`` added an explicit ``include`` for it and for
``.github/gates.toml``. This gate still belongs to a checkout environment, because no CI job
invokes it; that is reported in the gate register rather than assumed.
```

#### F-4-5 — the CRLF census is a property of one working tree on one machine, published as a property of the repository

`docs/GATES.md:1130-1137`: *"`git ls-files --eol` reports **66 of 216** tracked files as `w/crlf`, and
`schemas/acronym-engine-result.schema.json` was one of them … the one gate that would notice only
notices for two files out of sixty-six."*

```
git ls-files --eol | awk '{print $2}' | sort | uniq -c
       1 w/-text
      57 w/crlf
     157 w/lf
       1 w/none
git ls-files | wc -l                                    216
```

`216` reproduces to the digit; `66` does not, and neither does the *"two files out of sixty-six"*
that hangs off it. This one is not simply stale: `w/crlf` is a property of **a** working tree on **a**
machine, and this figure ships inside the sdist as a sentence about the repository. It is the same
class as `docs/SUPPORT_MATRIX.md`'s environment row, and the page has the instrument for it — every
other measured block on it names the machine and the date. **Exact correction:** either date and
stamp the block (`57 of 216 on this checkout, CPython 3.13.4 on win32, 2026-08-26`), or replace the
count with the command and drop the derived *"two out of sixty-six"* clause. Do not re-type `57`
without a stamp; the next reader will find a third value.

**Q4 nomination:** `docs/GATES.md:1208`, *"`.github/gates.toml` is not shipped in the sdist"*.
Checked by building a real sdist and listing its members. **False.**

### 2.4 `docs/SECOND-READER.md`

**Strongest claim**, lines 17-19: *"**The parts of this page that run, run.** Its trigger is
`tools/second_reader.py`; its state is the ledger; `python tools/second_reader.py --check` is the gate
over both; and `tests/test_second_reader_policy.py` mutation-tests every rule of it."*

**What a reader must believe.** (a) The published command is the command the tool runs. (b) The
cursor is derived and checked. (c) Every rule the page states is mutation-tested. (d) The page's
description of what the mechanism cannot reach is accurate.

**(a) and (b) survive, re-derived rather than carried.**

```
python tools/second_reader.py --trigger        6 user-facing file(s)
git status --porcelain --untracked-files=all -- <the six pathspec entries>
                                               9 lines, of which 3 are the excluded
                                               DECISIONS + two AUDIT-* files
python tools/second_reader.py --check          cursor derivable, agrees with the page
python -c "...parse_rotation..."               21 entries, no repeat, entry 5 = SUPPORT_MATRIX
```

**(c) is where the round's own edits land, and they are right.** Cold read 3's `P-3` — the page
saying *twenty* in section 9 and *fifteen* in section 8 about a set of twenty-one — was applied in
this round's diff, with the history left in place rather than swapped in silently. Verified against
`git diff docs/SECOND-READER.md`: both corrections landed, in the words cold read 3 specified.

**(d) fails twice: once on the sdist sentence ([`F-4-1`](#f-4-1--three-documents-say-the-sdist-omits-two-registers-it-ships-and-one-of-the-three-is-a-source-file)),
and once on a snapshot that has moved.**

Section 7's new block:

```
python tools/second_reader.py --trigger, mid-round, with the docstring already rewritten.
  git status --porcelain    ->  M src/acronymkit/__init__.py   (among eleven others)
  trigger A                 ->  4 user-facing file(s), and that file is NOT among them
```

Re-run on the tree as it stands: `git status --porcelain --untracked-files=all` reports `19` modified
and `14` untracked before this note was written; trigger A returns `6`. The block is labelled
*"mid-round"*, so this is a snapshot
that kept moving rather than an error — **but the conclusion it exists to support is stronger than
the block, and re-derives exactly**: `trigger_a` returned `6` files and
`src/acronymkit/__init__.py` was not one of them, in a tree where it is modified.

**Q4 nomination:** `docs/SECOND-READER.md:528`, *"`docs/cold-reads.toml` is absent from an sdist
exactly as `.github/gates.toml` is"*. Checked by building an sdist and listing its members.
**False.**

### 2.5 `docs/DEFINITION-OF-DONE.md`

**Strongest claim**, line 1-6: *"# Definition of done — the twenty criteria, swept … **The met-count
did not rise with them, and the proportion fell**: `11` of `20` at the sixth sweep against `10` of
`14` at the fifth."*

**What a reader must believe.** (a) There are twenty criteria. (b) Eleven read met. (c) The
comparison to the fifth sweep is like for like. (d) Every evidence cell was either re-derived this
sweep or says it was carried.

**(a) holds.** The table carries twenty numbered rows; a naive `grep -E '^\| [0-9]+ \|'` returns
nineteen because row `17` is written `| \`17\` |` with the number inside a code span, which is worth
knowing before anybody counts them with a regex:

```
awk '/^\| *[0-9]+ *\|/{c++} END{print c}' docs/DEFINITION-OF-DONE.md      19
sed -n '87p' docs/DEFINITION-OF-DONE.md | cut -c1-12                      | `17` |
```

**(d) is the load-bearing belief and two cells fail it.**

**F-4-6 — criterion `9`'s evidence cell states a count its own verdict cell corrects, in the same
row.** Line 79: the verdict reads *"at the sixth sweep the count moved DOWN, `13` of `36` to `12` of
`36`, the first fall this page has recorded"*; four clauses later the evidence cell reads *"The
register now prints `CARRYING IN-SITU EVIDENCE: 13 of 36`"*. It prints `12 of 36`
(`python tools/gates.py --check`, quoted in §0 above). The end of the same cell then carries the
corrected `inline`/`automated`/debt figures, so the row knows. **Exact correction:** replace
`The register now prints \`CARRYING IN-SITU EVIDENCE: 13 of 36\`` with
`The register now prints \`CARRYING IN-SITU EVIDENCE: 12 of 36\``.

**F-4-7 — criterion `3`'s evidence cell publishes a five-round ledger trajectory in the round that
made it six**, and the header claims that cell was re-derived at this sweep. Line 73:

> the ledger has fallen `316` to `262` to `231` to `213` to `201` across five recorded rounds

```
python -c "...import tools.check_claims; [r.deferred for r in LEDGER_TRAJECTORY]..."
  316, 262, 231, 213, 201, 189      -- 6 rounds
python tools/check_claims.py | grep 'ledger trajectory'
  ledger trajectory: 6 rounds | M3-PA (the second walk) ... deferred 189
```

The sixth row, `M3-PA (the second walk)`, is added by `git diff tools/check_claims.py` in this same
working tree. **Exact correction:** replace
`` `316` to `262` to `231` to `213` to `201` across five recorded rounds `` with
`` `316` to `262` to `231` to `213` to `201` to `189` across six recorded rounds ``.

**And the header and the row disagree about when the row was last touched.** The header says *"The
sixth sweep re-derived eleven of twenty — `3`, `4`, `9`, `13`, `14` and all six of the new `15` to
`20`"*; criterion `3`'s own verdict cell says *"re-derived at the fifth sweep"*. One of the two is
wrong, and `F-4-7` is evidence for which: a cell re-derived at the sixth sweep would have carried six
rounds. **Exact correction:** strike `3` from the header's re-derived list, or re-derive it and
correct the verdict cell — but not both silently.

**F-4-8 — the page's stated numbering convention has three categories and the page says it has two.**
Lines 59-63:

> **How to read the numbers.** A figure written as a plain number in prose is a citation into
> `bench/results.json` by run id — that is operating rule 1, and this document holds no exceptions to
> it. A figure inside a fenced block is **command output, not a benchmark measurement**: the command
> is printed above it … **Nothing else appears.**

```
python - (over docs/DEFINITION-OF-DONE.md: count `...`-spanned bare numerics outside fences,
          and count claim: citations)
  code-spanned bare numerics outside any fence   265
  inside fences                                    0
  claim: citations                                54
```

`265` figures appear in a third form the paragraph does not name: code-spanned, outside a fence, with
no command printed above them and no run id behind them. Every figure in `F-4-6` and `F-4-7` above is
one of them, which is why both went stale invisibly — a code span is masked from
`tools/check_claims.py` exactly as a fence is. **Exact correction:** replace `Nothing else appears.`
with:

```
A figure inside a code span is a figure this page has taken out of the claims gate's view --
`tools/check_claims.py` masks code spans exactly as it masks fences (D-052) -- and there are
several hundred of them here. They are the numbers most likely to be stale on this page, and two
of them were, at the sixth sweep. Re-derive a code-spanned figure before quoting it.
```

**Q4 nomination:** `docs/DEFINITION-OF-DONE.md:73`, *"the ledger has fallen `316` to `262` to `231`
to `213` to `201` across five recorded rounds"*. Checked by reading `LEDGER_TRAJECTORY` out of
`tools/check_claims.py` in this working tree. **False by one round, added in this working tree.**

### 2.6 `docs/EVALUATION.md`

At `37,501` words (`python tools/second_reader.py --cost`) this is the file the policy's own section 7
says one cold read cannot cover. This read covered the round's five diff hunks and the two sections
cold read 3 left open. Everything else on the page is **not checked here and is not claimed to be**.

**Strongest claim** in the new material, the one-sentence answer of the perf section: *"**Provenance
construction dominates on every arm — it is the largest cost centre on all four, and on every one of
them it is larger than the other three put together.**"*

**What a reader must believe.** (a) The stages measured are the shipped path. (b) The work counts are
properties of the code. (c) The wall-clock half is not being quoted as if it were gated.

**All three survive, and this section is the best R17/R18 handling in the tree.** The work-count table
is gated per cell; the wall-clock is fenced with the machine named and the `43 %` spread across three
runs of one machine printed beside it; and the three cross-checks against the shipped path
(byte-identical phrase, zero excess `resolve` calls, zero excess `class_word_for` calls) are exactly
the check that separates a stage that measures less work from a stage that does less work. The
arithmetic ties out: `578,816 / 155,272 = 3.728`, `451,263 / 155,272 = 2.906`,
`24,536 / 4,096 = 5.99`, `27,719 / 451,263 ≈ 1/16`.

**The differential section's own falsifiable claim was re-derived and holds:**

```
git grep -n identify_abbr 387f739        (no output, rc=1)
git grep -n MED1250_unlabeled 387f739    (no output, rc=1)
  -> "Never read by this repository before this round" holds at the commit preceding the work
```

`1,252 = 515 + 737` ties out; the `517 > 515` row is explained rather than absorbed; and the
one-sense section's `4` folded collisions against `2` case-sensitive ones make its *"half of the
folded rate is an artefact"* exact rather than approximate.

**F-4-9 — cold read 3's `E-1` is unaltered, and the figure has gone stale a second time in the
sentence whose subject is that it went stale.** Line 2398:

> The governed half of this package is 9,647 of 26,149 source lines — re-counted for this revision
> with `find src/acronymkit -name '*.py' | xargs wc -l`, because the previous figure here had gone
> stale

```
find src/acronymkit -name '*.py' | xargs wc -l | tail -1              26591 total
find src/acronymkit/governed -name '*.py' | xargs wc -l | tail -1      9647 total
```

The numerator is exact. The denominator was `26,149` when written, `26,561` when cold read 3 measured
it on 2026-08-25, and `26,591` today. **Three values, three reads, one sentence — and the sentence's
own subject is that the previous figure had gone stale.** `docs/SECOND-READER.md` section 4.2 names
this as the finding that bought check `C4`, *"the highest-yield check per second spent"*.
`docs/EVALUATION.md` is in this round's trigger A and grew by `1,076` lines without this line being
touched.

**Exact correction:** replace `9,647 of 26,149 source lines` with `9,647 of 26,591 source lines`, and
— because a figure re-typed into this sentence has now gone stale three times — append to the same
sentence: `(re-derive it; this figure has been wrong at three consecutive reads)`. The structural fix
is a run id, and there is no runner that saves a source-line count, which is the honest reason it
keeps happening.

**Q4 nomination:** `docs/EVALUATION.md:2398`, *"`9,647` of `26,149` source lines"*. Checked by the
command the sentence itself publishes. **False, for the third consecutive read.**

### 2.7 `CHANGELOG.md`

**Strongest claim** in the new material: *"**Two internal statistics this project used to quote about
its own reporting are retired.** A sampled audit of this project's own claims has now run three
times. The **headline error rate stands** — somewhere in the low-to-mid twenties per cent of sampled
claims are not true."*

**What a reader must believe.** (a) The sampler ran three times. (b) The headline stands as a band.
(c) The two decompositions are retired at every site. (d) The pointers resolve.

**(a), (b) and (c) hold** against `docs/DECISIONS.md` D-088 and against the census that record
publishes. **(d) does not** — the entry points at `docs/CLAIMS-LEDGER.md` §6, and §6 says the
sampler has run twice. That is [`F-4-3`](#2-2-docsclaims-ledgermd) above, reported against the
target rather than against the pointer, because the changelog entry is the half that is right.

**C-1 (carried from cold read 3, and this round repeated it) — numbers added to a scanned file with
no citations, silenced by code spans.**

```
git diff CHANGELOG.md | grep '^+' | (count `...`-wrapped numerics, count "claim:")
  code-spanned numeric tokens added this round   11
  claim citations added this round                0
```

Run ids exist for most of them — the entry names `governed_perf.*` and `roundtrip.*` in its own
prose — and R1 prefers citing to fencing. `docs/CLAIMS-LEDGER.md` §4 records the standing refusal to
migrate this file (a `{{claim:...}}` re-renders to the current value and would rewrite release
history), and that refusal covers figures *about a release*. It does not obviously cover `4096`, the
memo limit, or `155,272`, which are properties of the tree at the moment of writing. **Disposition:
for whoever owns the changelog**, and the decision is narrower than the standing refusal makes it
look.

**One phrasing worth a second look, not a finding.** *"the generator reaches the true short form for
about **two in five** pairs on MED1250"* and *"the aligner accepts around **six in seven**"* are
prose fractions standing in for gated figures under `roundtrip.*`. That is the R1-preferred direction
(the number left the prose) and it is also the direction that makes the claim uncheckable by anything.
Both readings are defensible; it is named here so the next reader does not have to decide alone.

**Q4 nomination:** *"A sampled audit … has now run three times."* Checked against
`docs/DECISIONS.md` D-088's `Evidence` line (*"the third R15 round at seed `20260827`"*) and its
three-point table. **True — and it is the pointer, not the claim, that is broken.**

---

## 3. Ledger rows, paste-ready

Under `P-1` this reader cannot write `docs/cold-reads.toml`. These are the rows in the schema
`tools/second_reader.py` validates, for a second party to paste. **`applied_by` is deliberately
absent from every new finding**: none is `fixed`, and under section 5.1 closing one takes a second
name.

**Paste the read row and the five at-limit dispositions together.** The read row alone turns
`--check` red, by design — see `P-1`.

```toml
[[reads]]
id = "2026-08-26"
reader = "cold-read-4"
rotation_served = "docs/SUPPORT_MATRIX.md"
cursor_after = "docs/GATES.md"
covered = [
  "CHANGELOG.md", "docs/CLAIMS-LEDGER.md", "docs/DEFINITION-OF-DONE.md",
  "docs/EVALUATION.md", "docs/GATES.md", "docs/SECOND-READER.md",
  "docs/SUPPORT_MATRIX.md", "src/acronymkit/__init__.py",
]
note = """
Second execution under the read-only rule and the second in which the reader could not
write this file, so trigger B served docs/SUPPORT_MATRIX.md for the second consecutive
read -- the stall cold-read-3 predicted, now observed. Written by a second party from
docs/notes/cold-read-4-findings.md.

src/acronymkit/__init__.py is listed under `covered` although no trigger reaches it: the
brief pointed at it, which is the third consecutive round in which this file arrived by
pointer-chase rather than by mechanism. Section 4 of the findings note takes a position on
whether the rotation should cover it.
"""
```

The new findings, each carrying the file, the line, the sentence quoted exactly and the command that
refutes it, all executed:

| id | file:line | one line |
|---|---|---|
| `F-4-1` | `docs/GATES.md:1208` | *"`.github/gates.toml` is not shipped in the sdist"* — it is, since `387f739`; refuted against a built sdist |
| `F-4-1b` | `docs/SECOND-READER.md:528` | same claim about `docs/cold-reads.toml`, same refutation |
| `F-4-1c` | `tools/second_reader.py:79` | third copy of the same claim, in a source file no trigger reaches |
| `F-4-2` | `docs/CLAIMS-LEDGER.md:64,260,295` | every published `deferred` figure is stale, including the column the page calls stable |
| `F-4-3` | `docs/CLAIMS-LEDGER.md:421,431` | *"It has run twice"* / *"both rounds"* against D-088's three rounds; `CHANGELOG.md` points here for the correction |
| `F-4-4` | `src/acronymkit/__init__.py` | *"each keeps its losing comparison in the same table"* — true of two of the four capabilities it enumerates |
| `F-4-5` | `docs/GATES.md:1132` | `66 of 216` CRLF; `57 of 216` here, and it is a per-machine property published as a repository one |
| `F-4-6` | `docs/DEFINITION-OF-DONE.md:79` | evidence cell says the register prints `13 of 36`; it prints `12 of 36`, as the same row's verdict says |
| `F-4-7` | `docs/DEFINITION-OF-DONE.md:73` | five-round ledger trajectory in the round that made it six |
| `F-4-8` | `docs/DEFINITION-OF-DONE.md:63` | *"Nothing else appears"* against `265` code-spanned figures |
| `F-4-9` | `docs/EVALUATION.md:2398` | `26,149` source lines; `26,591` today — third value at the third consecutive read |

**And the seven existing findings, re-checked on this tree.**

| id | state |
|---|---|
| `F-2026-08-24-01` `-02` `-03` | reproduce; `grep -c '\.command(' src/acronymkit/cli.py` returns `16` against `13` driven. **At the limit** |
| `F-2026-08-24-04` | reproduces; `find src/acronymkit -name '*.py' \| wc -l` returns `40` against the page's `27`. **At the limit** |
| `F-2026-08-24-05` | reproduces; nine commands under *"All of"* on a sixteen-command CLI, and this read served that page. **At the limit** |
| `F-2026-08-25-01` | **the blocker is gone and the row does not say so.** The docstring was rewritten; `blocked_on` still reads *"It is not blocked on knowing what to write"*. `docs/SECOND-READER.md` §5.3's new paragraph says this row owes three fields — `disposition = "fixed"`, an `applied_by`, an `applied_in`. It still owes them. Note that the rewritten docstring carries `F-4-4`, so *fixed* is the right disposition for the sentence this row quotes and is not a verdict on the file |
| `F-2026-08-25-02` | reproduces on both characters; `normalize('TXN_\xa9_ID', D())` returns `'TXN_ID'` and `normalize('㎡', D())` returns `''`. Not re-run here; carried from cold read 3, which did re-run it |

---

## 4. Should the rotation cover source files? Yes — and the costing that says no uses the wrong denominator

**First, D5's structural finding, verified rather than taken on its word.**

```
python -c "import tools.second_reader as sr; print(len(sr.PATHSPEC), sr.PATHSPEC)"
  6 ('README.md', 'CHANGELOG.md', 'CONTRIBUTING.md', 'SECURITY.md', 'pyproject.toml', 'docs')

python -c "...print(len(sr.user_facing_files()), [p for p in sr.user_facing_files()
                                                  if p.startswith('src/')])"
  21 []

python -c "...print(sr.is_user_facing('src/acronymkit/__init__.py'))"
  False

python tools/second_reader.py --trigger        6 file(s); src/acronymkit/__init__.py is
git status --porcelain -- src/acronymkit/__init__.py   M   -- modified and not among them
```

**Confirmed in every part.** `PATHSPEC` has six entries and `src/` is not one. `user_facing_files()`
returns `21` paths, none under `src/`. The one file the whole argument is about is modified in this
tree and trigger A does not return it. And `docs/cold-reads.toml`'s `F-2026-08-25-01` reads
`owner = "unowned"` for a file with an obvious owner, because the mechanism that would have assigned
one cannot see it.

**The position: yes, and the change is four files, not forty.**

`docs/SECOND-READER.md` section 7 refuses the widening on a costing:

> `find src/acronymkit -name '*.py' | wc -l` returns `40`. Admitting the package's source would take
> the rotation from `21` entries to `61`, so the set would turn over in sixty-one rounds instead of
> twenty-one … Admitting only `__init__.py` is a special case with no rule behind it.

**`40` is the wrong denominator, and the "special case with no rule" is a rule that takes one line to
state.** The rule is: *a module is user-facing when a stranger reads its prose without opening the
repository.* `help(acronymkit)`, an editor's hover, and the rendered API docs satisfy that. A private
module's docstring does not. Mechanically that rule selects every `__init__.py` under
`src/acronymkit/` — the same shape as the existing rule, which selects every `*.md` under `docs/`,
with a different glob. It is enumerable from the tree in one line, which is the property
`user_facing_files()` exists to have.

Measured:

```
python - (ast.get_docstring over every __init__.py under src/acronymkit)
  src/acronymkit/__init__.py             867 words
  src/acronymkit/governed/__init__.py    641 words
  src/acronymkit/nlp/__init__.py         100 words
  src/acronymkit/resources/__init__.py   176 words
  total                                4 files, 1,784 words

python tools/second_reader.py --cost | head -1
  the full user-facing corpus   156,216 words across 21 files

git log --oneline -- 'src/acronymkit/**/__init__.py' | wc -l           7
git log --oneline -- 'src/acronymkit' | wc -l                         17
git log --oneline | wc -l                                             53
```

- **Rotation: `21` to `25`, not `21` to `61`.** Turnover rises by nineteen per cent, not by a
  hundred and ninety. Section 7's own weakness paragraph about trigger B's latency survives that.
- **Corpus: `+1,784` words on `156,216`, or `+1.1` %.** The single largest file already in the
  rotation is `docs/EVALUATION.md` at `37,501` words — twenty-one times the whole proposed addition.
- **"A prose trigger over Python would fire constantly" is measured false for this glob.** `7` of
  `53` commits touch one of the four; `17` of `53` touch anything under `src/acronymkit`. Trigger A
  over `docs` plus five root files fires on very nearly every round. The widening would fire *less*
  often than the pathspec already does.

**And trigger B is the half that matters here, which is the part a trigger-A-only widening gets
wrong.** `git log --oneline -- src/acronymkit/__init__.py` shows the file was last committed at
`a3f049a`, many rounds before the retired breadth pitch was first reported. Trigger A only fires on
the round that *changes* a file, so a trigger-A widening alone would have caught nothing until this
round. **The rotation is the correct instrument for this defect and the count that bought trigger B
is the same count that applies here**: a file nobody edits is a file nobody re-reads, and this one
went two rounds wrong with two people having written down where it was.

So: **both triggers.** Add `src/acronymkit/**/__init__.py` to `user_facing_files()` and to the
rotation block (taking it to `25`, which the anti-rot rule then enforces against the tree), and add
`src/acronymkit` to `PATHSPEC` with an `EXCLUDED_GLOBS` entry for `src/acronymkit/**/*.py` that is
not an `__init__.py` — declared, so the exclusion is visible and arguable rather than implied by an
omission.

**What the change costs, said plainly rather than absorbed.** It immediately puts
`src/acronymkit/governed/__init__.py` — `641` words of prose about the subsystem
`docs/POSITIONING.md` commits this library to leading with, never cold-read — into the rotation, and
the honest expectation is that it produces findings in the round it lands. That is the argument for
it, and it is also the reason nobody will enjoy the round it lands in.

**The argument against that survives, and it is not the costing.** `python tools/check_claims.py`
already scans `src/acronymkit/*.py` and `src/acronymkit/**/*.py`, so numbers in every module
docstring are gated today; what the widening adds is prose review, and prose review is the thing this
repository has the least evidence works. Section 7's own sentence stands either way: **"this policy
covers documents and says it covers anything user-facing, and the two are not the same set."** The
proposal above closes that gap for `1,784` words. It does not close it for
`tools/second_reader.py:79`, which is
[`F-4-1c`](#f-4-1--three-documents-say-the-sdist-omits-two-registers-it-ships-and-one-of-the-three-is-a-source-file)
— a false claim in a shipped source file that neither the current policy nor this proposal reaches,
and which is named here rather than solved.

---

## 5. What this read did not check

- **`docs/EVALUATION.md` was read in this round's five diff hunks and the two sections cold read 3
  left open.** At `37,501` words it is the one file in the rotation a single cold read cannot cover,
  and section 7 of the policy already names that as a weakness rather than a bound. Every citation on
  it resolves — that is `python tools/check_claims.py` speaking, not this reader.
- **No mutation was taken in the tree.** See `P-2`. The sdist in `F-4-1` was built into a scratch
  directory outside the repository and no file under it was written.
- **The suite, `mypy` and `ruff` were run, not read.** Green is evidence they pass, not evidence they
  cover anything.
- **`docs/SUPPORT_MATRIX.md`'s measured cells were not re-derived.** Cold read 3 re-derived all of
  them one round ago and every one reproduced; this read checked the environment row and the
  exhaustive-word row and carried the rest.
- **`docs/POSITIONING.md` is out of both triggers and carries four unapplied findings from cold read
  3** — `PS-2` (the `1.22`-point effect size), `PS-3` (`selection_on_this_corpus`), `PS-4` (*"the
  rotation now runs to fifteen"*, line `423`, where the rotation runs to `21`) and `PS-5` (the
  three-way population). `PS-4` was re-checked here and is unaltered. Reported, not checked further.
- **`docs/INSTALL.md` and `docs/ENTERPRISE.md` are out of both triggers** and still pin `v0.2.0` and
  `acronymkit-0.2.0-py3-none-any.whl` against a `pyproject.toml` reading `0.3.0`. Cold read 3 called
  this the most directly user-damaging thing it found; it is unaltered.
- **Nothing here re-ran a benchmark.** Every figure quoted from `bench/results.json` was resolved
  against the saved run by the claims gate, not re-measured.
