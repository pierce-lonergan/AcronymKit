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

bucket          deferred  unexamined   total
gate-able            123         200     323
no-number              0           0       0
stale                  0           0       0
blocked              135          10     145
not-a-claim            4         355     359
unclassified           0         915     915
ALL                  262        1480    1742

judged 104 of 1742 (96 of them under one whole-file entry, 8 one at a time)
  | derived 1638 of 1742
not-a-claim by detector:
  byte-size 56 | iso-date-fragment 123 | section-or-list-ordinal 40
  version-number 98 | year-shaped 41
```

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

Four rules, all machine-checked by `trajectory_problems`:

1. **The last row must equal the live baselines.** Lowering `DEFERRED_BASELINE` or
   `VALUE_MATCHED_BASELINE` without appending a row turns the gate red. A burn-down nobody can audit
   is not a burn-down.
2. **The deferred column may never rise.**
3. **`by_citation + by_deletion + by_fencing + by_other` must equal the fall the row claims.** A round
   says where every migrated number went, and the arithmetic is checked rather than trusted.
   `by_other` requires a note.
4. **A round must move at least `MIGRATION_QUOTA`, or record a `waiver` saying why it could not.**

The quota is deliberately far below what the round that installed it achieved. A quota is a floor on
a system, not a target for one workstream, and setting it at one round's number guarantees the first
waiver — and a waiver granted every round is a rubber stamp, which is the failure mode D-052 rejected
a residue ratchet for.

**Fencing is counted apart from citation and deletion, and it is not adjudication.** D-052 records
that a fenced number leaves the gate's view entirely. A deferred count that falls by fencing is a
burn-down of the measurement, not of the debt, and the trajectory has a column for it so that reading
is available without re-deriving it.

### The order of preference

1. **Delete the number.** Most prose does not need a figure, and the cheapest way to satisfy R1 is to
   make the sentence stop being a claim. Two of this round's migrations are deletions.
2. **Cite it** — `{{claim:<run-id>.<field>}}`, which names its source and can therefore be *wrong*,
   which is the only property that makes a check worth running.
3. **Mark it** `measured: <run-id>` if it is a recorded historical result — but read §4 first.
4. **Fence it** only when the number is command output, and say so in the trajectory row.

### Where the quota should be spent first

`docs/DECISIONS.md` carries the largest ledger and **no workstream may edit it**; a recorder writes
that file. Its share of the ledger is therefore not reachable by the quota, and a round that ignores
that will report a shortfall it could not have avoided. The reachable population is everything else.

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
    note="...",
    waiver="...",           # only when the round moved less than the quota
)
```

The gate prints the last row on every run, so the trajectory is visible without opening a file:

```
$ python tools/check_claims.py            # output, not a benchmark measurement

ledger trajectory: 2 rounds | M2-P3 X4 (first burn-down) moved 54
  (citation 52, deletion 2, fencing 0, other 0) | deferred 262, value-matched 64
  | quota 12 per round
```

---

## 4. What is blocked, and on what

Three groups account for most of the `blocked` bucket, and none of them is blocked on effort.

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
