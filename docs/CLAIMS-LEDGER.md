# The claims ledger: what is on it, and the rate it comes off

`tools/check_claims.py` counts every number in the scanned documents and says, for each one, how it
is backed. Two registers hold the ones it has **not** verified, and both are ratchets that may fall
and may not rise:

- **`VALUE_MATCHED_BASELINE`** — numbers the gate could already see before D-052, backed only by the
  fact that some measurement happens to equal them. Closed. Nothing new may join.
- **`DEFERRED_BASELINE`** — numbers the D-052 coverage widening revealed. Also closed.

Beside them sits an **unexamined** residue: prose numbers no arming rule reaches. It is uncapped, on
purpose, so that "uncapped" is a figure somebody can read rather than a silence.

D-052 opened both registers and D-057 recorded the result: the instrument got better and the reading
got worse. That is correct and it must not be undone. What was missing is this page — **a rate.** An
honest ledger with no trajectory is a backlog with better manners.

**How numbers are handled on this page.** Every figure here is a property of *these documents*, not
of the library, and no benchmark runner can `--save` a property of a document. So they appear as
**fenced command output with the command printed above them**, which is the convention
[`docs/DEFINITION-OF-DONE.md`](DEFINITION-OF-DONE.md) already uses and which re-derives in one line.
D-052 is explicit that fencing silences the gate completely; that is exactly why the command is
printed with every block, and why the trajectory below separates migrations achieved by fencing from
migrations achieved by adjudication. A figure you cannot re-derive from a command on this page is a
defect in this page.

---

## 1. The classification

Every unverified number is bucketed by `python tools/check_claims.py --classify`. Four buckets were
scoped; two more exist because the residue is not what the scoping assumed.

| Bucket | Meaning | How it is assigned |
|---|---|---|
| `gate-able` | a measurement with this value exists, so a citation can be written today | derived |
| `no-number` | the sentence is better without the figure — delete it | judged only |
| `stale` | describes something that is no longer true | judged only |
| `blocked` | reads as a metric and cannot be gated | derived, or judged with a reason |
| `not-a-claim` | a year, a date part, a version, a byte size, a section number | derived |
| `unclassified` | no derived rule fired and nobody has judged it | derived |

**`not-a-claim` had to be added, and the scoping bucket nearest it is wrong about its contents.**
"Prose that should not carry a number at all" does not describe `Verified 2026-08-23`, where the
number is the point of the sentence. Calling those deletable would have been a false statement about
several hundred of them.

**`unclassified` is published rather than absorbed.** A classification with no residue of its own is
a classification that has been made to come out even.

### The counts

```
$ python tools/check_claims.py --classify        # output, not a benchmark measurement
                                                 # re-run after the M2-P4 migration

bucket          deferred  unexamined   total
gate-able             92         200     292
no-number              0           0       0
stale                  0           0       0
blocked              135          10     145
not-a-claim            4         377     381
unclassified           0         939     939
ALL                  231        1526    1757

judged 104 of 1757 (96 of them under one whole-file entry, 8 one at a time)
  | derived 1653 of 1757
not-a-claim by detector:
  byte-size 56 | iso-date-fragment 141 | section-or-list-ordinal 43
  version-number 99 | year-shaped 41
```

The `deferred`/`gate-able` cell is the one to watch: it was `123` when this page was written and is
`92` after the round that bound the record file. Thirty-one of that fall is the migration recorded
below; nothing else moved it.

**Only the `deferred` column is stable.** It is the ratcheted one: it cannot rise, and it falls only
in a commit that lowers a baseline and records a round. Every other column moves whenever anybody
edits any scanned document, because the unexamined residue is uncapped by design. The block above
drifted by fifteen numbers while this page was being written, from a document another workstream
added in the same session — nothing regressed, the tree simply grew. Read the `deferred` column as a
fact and the rest as a reading taken at a moment.

`--classify` prints the same table broken down per file. It is not repeated here, because a per-file
table copied into a document goes stale the first time anybody edits a document.

### What the classification is not

**`gate-able` does not mean the number is right.** It means a measurement somewhere has that value,
which is precisely the property D-052 refused to treat as a backing. Hand-checked on the nineteen
`UNIQUE`/`REPLICATED` deferred numbers of `docs/EVALUATION.md` before this round's migration, **four
rows carrying three distinct values** matched a measurement of something else entirely: three
competitors' cold-import times in milliseconds, against a short-form F1 delta, an abstention recall
and an ablation score. (`3.6` appears on two lines, which is why the row count and the value count
differ — the compressed phrasing "three of nineteen" was wrong about the rows and is corrected here.)
So `gate-able` is a *candidate* bucket, and every migration out of it is a reading, not a lookup.

Those three are also the clearest instances of the `blocked` bucket: this project measured three
competitors' cold-import times for a published table and **no runner ever saved them**, so there is
nothing to cite and the value match is noise.

**`no-number` and `stale` read zero, and that is a fact about the judgements, not about the tree.**
Both are judged-only: no rule can derive "the sentence is better without this figure" or "this is no
longer true", so an empty bucket means nobody has written an entry, not that no such number exists.
The instrument ran: `judgement_for` was evaluated once for each of the 1,727 unverified numbers and
matched 8. The round's two `no-number` cases were *deleted* rather than recorded, so they left the
tree instead of filling the bucket — which is the order of preference working, and it is also why a
reader must not take the zero as a measurement.

**`not-a-claim` is derived from the token's shape and has a known false-positive mode**: a real count
that happens to be four digits in the 1900–2100 range. One such mode was found and fixed during this
round by sampling the detector's own output: the ordered-list rule made the trailing `.` optional, so
a sentence opening `26 to 39 symbols that never appear …` was read as list item 26. Twenty numbers
were mislabelled that way; the counts above are post-fix, and `section-or-list-ordinal` fell from 60
to 40. The `year-shaped` detector is the loosest of
the five and is named so that the loosest one is the one a reader checks first.

**The whole total inherits `iter_claim_numbers`'s idea of what a number is.** A different tokenizer
gives a different residue: an ISO date is split into three numbers by the hyphenated-range rule, which
is where the largest single detector count comes from. **These totals are a floor under one unit
vocabulary, not a measure of the debt.**

### The blind spot the classification found

```
$ python tools/check_claims.py --classify | tail        # output, not a benchmark measurement

210 number(s) no arming rule reaches sit in a table cell under a metric column heading.
```

A published table names its metric once, in the header, and then writes bare numbers underneath.
Proximity measures characters and the unit rule reads the number's own tail, so **neither can see a
column heading**. `--classify` reads the heading as a third rule, and uses it only to *size* the blind
spot. Moving it into `_KEYWORDS` would put every number it finds onto the deferred ledger, which is a
ratchet-raising commit and needs its own decision. It is not taken here.

---

## 2. The policy

**A round that lowers a ratchet appends a `LedgerRound` to `LEDGER_TRAJECTORY` in
`tools/check_claims.py`, in the same commit.** The gate checks it and fails if it does not add up.

Six rules. Four are machine-checked by `trajectory_problems`, which reads only the source; the last
two are the record-file binding, and the sixth is the only check in this policy that reads the tree:

1. **The last row must equal the live baselines.** Lowering `DEFERRED_BASELINE` or
   `VALUE_MATCHED_BASELINE` without appending a row turns the gate red. A burn-down nobody can audit
   is not a burn-down.
2. **The deferred column may never rise.**
3. **`by_citation + by_deletion + by_fencing + by_other` must equal the fall the row claims.** A round
   says where every migrated number went, and the arithmetic is checked rather than trusted.
   `by_other` requires a note.
4. **A round must move at least `MIGRATION_QUOTA`, or record a `waiver` saying why it could not.**
5. **A round must move at least `RECORD_FILE_FLOOR` numbers out of `docs/DECISIONS.md`** — recorded
   in `from_record_file` — **or record a `waiver`.** Only `by_citation` and `by_deletion` may be
   counted toward it: fencing a number inside a decision record hides it from the gate without
   deciding anything about it, so counting fencing here would make the binding worse than the
   carve-out it replaced. Checked by `trajectory_problems` on every row from
   `RECORD_BINDING_LABEL` onward; rows before it predate the binding and are not retro-judged.
6. **`RECORD_FILE_PIN` must name the newest round and hold the live `## D-` record count.** Adding a
   decision record turns the gate red until a round is appended and the pin re-taken. Checked by
   `record_file_problems`.

The quota is deliberately far below what the round that installed it achieved. A quota is a floor on
a system, not a target for one workstream, and setting it at one round's number guarantees the first
waiver — and a waiver granted every round is a rubber stamp, which is the failure mode D-052 rejected
a residue ratchet for.

### Rule 5 and rule 6 are one decision, and rule 6 is the half that makes rule 5 reachable

The quota shipped with a carve-out saying `docs/DECISIONS.md` was "not reachable by the quota"
because no workstream may edit it. The arithmetic of that is fatal, and the recorder wrote the
objection down itself: the exempt file held **115 of the 262** deferred numbers and **217 of the
323** citation candidates, so the trajectory asymptotes at 115 and the quota starts being waived for
a reason nobody chose — which is D-052's residue-ratchet objection arriving through the one door the
policy left open. The maintainer withdrew the carve-out.

Three shapes were available and one was chosen:

| | why not | |
|---|---|---|
| **a whole-register floor with the record file merely *counted*** | this is what the policy already had. Nothing stopped a round paying its twelve out of the eleven other files forever, which is exactly how the record file reached 115 of 262 while the trajectory reported healthy movement. | rejected |
| **a waiver that must be written down** | a waiver is free text and nothing grades it. Without a floor underneath, the first inconvenient round becomes a permanent exemption granted one sentence at a time. | kept, but as the escape and not as the mechanism |
| **a per-file floor on the record file** | it is the only one of the three that produces a red build for the case actually decided against: a round that adds records and migrates none of them. | **chosen** |

The floor alone is not enough and that gap is why rule 6 exists. `trajectory_problems` only ever
judges rounds that *exist*, so a round that adds records and appends no row satisfies the floor
**vacuously**. The pin closes it by making growth of the record file itself a red build. It counts
`## D-<n>` headings rather than lines or bytes, so a typo fix or a reflow does not spend a waiver;
only the recorder's actual unit of work moves it.

All four checks were mutation-tested against this checkout, red, before this page was written; the
record-added case is also an automated test that mutates the real file and asserts the real gate
goes red (`tests/test_check_claims.py::TestTheBindingCanFailWhereItRuns`).

**Fencing is counted apart from citation and deletion, and it is not adjudication.** D-052 records
that a fenced number leaves the gate's view entirely. A deferred count that falls by fencing is a
burn-down of the measurement, not of the debt, and the trajectory has a column for it so that reading
is available without re-deriving it.

### The order of preference

1. **Delete the number.** Most prose does not need a figure, and the cheapest way to satisfy R1 is to
   make the sentence stop being a claim.
2. **Cite it** — `{{claim:<run-id>.<field>}}`, which names its source and can therefore be *wrong*,
   which is the only property that makes a check worth running.
3. **Mark it** `measured: <run-id>` if it is a recorded historical result — but read §4 first.
4. **Fence it** only when the number is command output, and say so in the trajectory row.

### What migrating a decision record does and does not license

`docs/DECISIONS.md` is now the file the quota is spent *first*, not the file it cannot reach. Two
constraints hold at the same time and neither is negotiable:

- **A record's numbers may be migrated. A record may not be changed.** No record may be added,
  renumbered, or made to say something different. If citing a figure would change what a record
  asserts, the figure stays and the round says so — a historical record whose figure was right when
  it was written is not a defect, and D-037's retire-in-place pattern exists for that case.
- **Citing a decision record is already the established practice in it**, which is what separates it
  from `CHANGELOG.md` in §4: the file carries rendered `<!--claim:...-->` citations in D-036, D-032
  and D-034's tables today, and the records that carry them name the run in their own **Evidence**
  line. A `{{claim:...}}` re-renders to the current value, so it is honest exactly where the record
  is arguing about a measurement the tree still holds, and dishonest where the record is arguing
  about a superseded one. That distinction, not the file, is the line.

---

## 3. The trajectory

Read `LEDGER_TRAJECTORY` in `tools/check_claims.py` for the live table; it is the checked copy. The
shape of a row is:

```
LedgerRound(
    label="...",            # unique, never rewritten
    deferred=...,           # sum(DEFERRED_BASELINE.values()) as the round left it
    value_matched=...,      # sum(VALUE_MATCHED_BASELINE.values()) likewise
    by_citation=...,        # became {{claim:<run-id>.<field>}}
    by_deletion=...,        # removed from the prose entirely
    by_fencing=...,         # moved inside a code span or fence -- NOT adjudication
    by_other=...,           # anything else; requires a note
    from_record_file=...,   # how many came out of docs/DECISIONS.md; citation and
                            # deletion only, and it is checked against rule 5
    note="...",
    waiver="...",           # only when the round missed the quota or the floor
)

RECORD_FILE_PIN = RecordPin(
    label="...",            # must name the newest LedgerRound
    records=...,            # count of "## D-<n>" in docs/DECISIONS.md at that round
)
```

The gate prints the last row on every run, so the trajectory is visible without opening a file:

```
$ python tools/check_claims.py            # output, not a benchmark measurement

ledger trajectory: 3 rounds | M2-P4 (the recorder is bound) moved 31
  (citation 30, deletion 1, fencing 0, other 0) | 31 of them out of docs/DECISIONS.md
  | deferred 231, value-matched 64 | quota 12 per round, record-file floor 12
```

### What the first bound round actually did, and what it did not

All 31 came out of `docs/DECISIONS.md`, which took its ledger from **115 to 84**. Thirty became
run-id citations and one was deleted. **No number was fenced**, and no record was added, renumbered
or reworded.

**The composition is the honest part, and it is not flattering.** Twenty-nine of the thirty-one were
*mechanical*: the record's own **Evidence** line already named the run, the field name restates the
sentence's own words, and the stored value renders to the text already on the page —
`disambiguation.sdu21.{acronymkit,most_frequent,random}` for D-015's `24`, and `oracle.med1250` for
D-011's `3` and D-012's `2`. The remaining two each needed a judgement: D-008's `28.7 %` against
`analysis.med1250.miss_taxonomy.pct_long_form_boundary_disagreement`, which the runner stores as
`28.74` and which is cited at one decimal; and the deletion, D-013's rounded `149 ms` restating the
`149.3 ms` of a table nine lines above it. So this round paid the quota out of the debt's *easy*
half, and the hard core is untouched. §4 says what the hard core is.

Those per-record counts are re-derived by counting the rendered citations in the file, not carried
over from the plan the round started with. The plan said `6` for D-011 and D-012 together; two of its
citations were withdrawn mid-round for the reason in §5, and the compressed sentence written from the
plan therefore added up to `32`. A phrasing tighter than the measurement is a false phrasing.

---

## 4. What is blocked, and on what

Three groups account for most of the `blocked` bucket, and none of them is blocked on effort. A
fourth section follows them: what is left in the record file now that it is bound.

### What is left in `docs/DECISIONS.md`, with the reason

`84` deferred numbers remain, and the residue is not evenly spread. **Forty-eight of the eighty-four
sit in two records**, and both are blocked for a reason already written on this page:

| where | left | of which no measurement anywhere matches | why |
|---|---:|---:|---|
| **D-023**, pydantic import attribution | 37 | 22 | the same ad-hoc session as `docs/notes/pydantic-cost.md`, and the same blocker: **no runner saves it.** `bench/run_micro.py` measures this library's import and nothing else. The value matches the classifier finds on the other 15 are coincidences against unrelated F1s and legend percentages. |
| **D-013**, the lazy-import before/after table | 11 | 4 | the four are the *before* column — `149.3`, `191.3` — which no run holds and no run may re-hold, because re-recording `micro.import` is itself prohibited by this record. Citing only the *after* halves would leave a two-column table with one live column and one frozen one: a table that never happened. This is `CHANGELOG.md`'s refusal arriving inside a decision record. |
| **D-048**, span-corpus invention rates | 7 | 5 | the record says of the figures itself that they exist "in the workstream's report" and are **not quotable**. There is nothing to cite. |
| everything else, 14 records | 29 | 0 | one judgement each. This is the reachable remainder and it is where the next round's floor should be spent. |

Two further groups are small and worth naming because their reason is *mechanical* rather than
evidentiary:

- **Four numbers cannot carry a citation without changing what the record shows.** They sit in
  4-space-indented display blocks (`docs/DECISIONS.md` lines `6807`, `6808`, `6873`, `6874`). Only
  fenced blocks and inline code spans are masked from the scanner, so those lines *are* prose to the
  gate — but a comment-form citation inside an indented block renders visibly to a reader. Blocked
  on the citation syntax, not on evidence.
- **Two numbers are blocked by the gate itself.** See §5.

**The binding is not symbolic, and the arithmetic says so rather than a phrase does.** `115 → 84` is
a fall of `31` in one round against a floor of `12`, and it is `27 %` of the record file's ledger.
But `55` of the `84` that remain are in three records whose blocker is a runner that does not exist
or a figure the record itself declares un-quotable, so a reader who expects the next three rounds to
repeat `31` is reading this wrong. The reachable remainder is `29`, which is two rounds at the floor
and then a waiver — and that waiver, unlike the one the carve-out would have produced, will name a
missing runner rather than a policy.

**`docs/notes/pydantic-cost.md` — blocked on a runner that does not exist.** The whole note is one
ad-hoc measurement session. `bench/run_micro.py` saves `micro.import` and `micro.generate_*` and
nothing else: no runner measures pydantic's import attribution, the frozen-dataclass shadow arms, or
the serialisation microseconds. Roughly half of its ledger matches no measurement at all, and the
other half's value matches are coincidences against short-form F1s and generation percentages. One
figure in the file is genuinely gated and carries its own judgement so the whole-file entry cannot
bury it. Note that re-recording `micro.import` is itself prohibited (D-013), so the obvious shortcut
is closed too.

**`CHANGELOG.md` — blocked on a decision, and the decision is about a missing mechanism.** A release
note records what was true at a release. Neither escape hatch fits:

- a `{{claim:...}}` citation is **re-rendered to the current value**, so citing in a changelog would
  silently rewrite history the next time a runner saves; and
- `measured: <run-id>` validates only that the run id **exists**, so attaching a live run to a
  superseded release figure points at numbers that run no longer holds.

The mechanism that would fit — a marker pinning a value *as of* a release — does not exist. Until
somebody decides to build it, migrating this file would make the document less true, not more. This
is the round's one refusal, and it ships with that disposition rather than as a silence.

**The `tune_presets` perturbation range — blocked on a script that is not a runner.** `README.md`
and `docs/notes/scoring-objective.md` both quote how far the scoring coefficients may be perturbed
while a sixteen-entry corpus still reproduces. `tools/tune_presets.py` produces it and writes no run
id. Its value match is the pathological case D-052 named: the value equals a great many unrelated
measurements.

---

## 5. How this fails

**The quota is checked against the source, not against the tree.** `trajectory_problems` compares the
last row to `DEFERRED_BASELINE`, so only a commit that edits a baseline can break it. That is
deliberate — a live-scan comparison would redden on any edit by any workstream — but it means a round
that *adds* debt somewhere and migrates the same amount elsewhere nets to zero and satisfies the
quota without the ledger having moved. Nothing here detects that; the per-file ratchets do, one file
at a time.

**A waiver is a free-text string.** Nothing checks that it is a good reason. The defence is that it
is a visible source edit in a file the gate reads, which is the same defence the baselines have.

**Citing a number can arm its neighbour, and the ledger it arms it onto is closed. This blocked two
migrations that were otherwise correct, and it is the sharpest finding of the round that bound the
record file.** `keyword_positions` reads the **raw** line so that a metric named inside a code span
still arms — and a rendered citation *is* raw text, so the field name inside
`<!--claim:oracle.med1250.oracle_union_recall-->` puts the word `recall` within the proximity window
of everything else on that line. Measured on this tree: citing `85.99` and `88.49` in D-011 moved the
two neighbouring bare `100 %` tokens off the **deferred** ledger and onto the **value-matched** one,
which is closed and may not grow. A correct migration failed the gate.

Two fixes exist and neither was taken:

- **Mask citations before reading keywords.** Correct in principle, and measured: it drops four
  numbers in `docs/EVALUATION.md` out of the register entirely — they are armed today *only* by a
  keyword inside a citation body — which is a coverage narrowing, in a file the round did not own,
  done as a side effect. That is a decision for whoever owns that page.
- **Let the unit rule win the tie when the only keyword is inside a citation body.** Zero measured
  blast radius today, but it leaves those four numbers armed for a reason that is an accident, so it
  fixes the ledger and not the cause.

So the two figures were left uncited and the defect is reported instead. It is **loud** rather than
silent — it reddens the gate at the moment somebody hits it — which is the only reason leaving it is
tolerable.

**The record-file pin is a deterrent where it is not a mechanism.** The gate sees one tree, not a
history. A recorder who adds a record can bump `RECORD_FILE_PIN.records` and leave `label` naming the
round that is already newest — and the floor passes, because that round's migrations satisfied it
once already. Nothing detects a second spend of the same credit. The defence is the one every ratchet
here has: a visible source edit in a file the gate reads, with `label` putting *which round paid for
this* into the diff.

**Rule 6 counts records, so it is blind to everything else a record can contain.** A recorder can add
unlimited prose, unlimited fenced numbers and unlimited citations to an *existing* record without
moving the pin. Fenced numbers are exactly what D-052 warns is indistinguishable from hiding, and the
pin does not see them. Only a new `## D-<n>` heading costs anything.

**The classification is a snapshot with line-numbered anchors.** Judgements are keyed
`<path>:<line>:<number>` and lines move. A judgement whose anchor no longer names a live number is
reported by `--classify` as stale rather than silently ignored, which degrades gracefully and does not
fail a build — so a tree that has drifted a long way will accumulate judgements that point nowhere and
say so quietly.

**The whole-file judgement is a summarisation, and summarisations hide exceptions.** One entry can
speak for seventy numbers. `--classify` prints how many numbers ride on whole-file entries and how
many were judged one at a time, precisely so the ratio is visible; the defence against a wrong
whole-file verdict is a specific judgement overriding it, and there is exactly one of those today.

**This page's own figures are fenced.** They are properties of the documents and no runner saves
them, so the gate cannot see them and cannot tell you when they go stale. Re-run the commands.
