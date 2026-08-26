# Decisions, and things deliberately not done

Negative results are the easiest thing in a project to lose and often the most useful thing to keep.
This file records what was tried and abandoned, what was considered and cut, and why — so nobody
re-litigates a settled question from scratch, and so the settled questions can be re-opened on
evidence rather than on vibes.

Newest first.

---

## D-097 — **The waiver arrived**, three rounds after D-084 forecast it and two after the floor became a target. It is the first one this project has written, and the residue that owes it was **measured** rather than asserted: every value match left in `docs/DECISIONS.md` is a coincidence, in the wrong unit, about something else

**Status:** shipped — `docs/DECISIONS.md`, `tools/check_claims.py`'s trajectory row and pin ·
**Amends:** D-091's *"two rounds at exactly `12` is what a floor looks like when it becomes the
target, and the next round should be read with that in mind"* — read with that in mind, and the
answer is that the floor was not a target, it was the last of the reachable debt ·
**Evidence:** `python tools/check_claims.py`; the probe below ·
**No experiment number spent — experiment eleven is still free**

Six records were added to this file — D-092 through D-097 — so the pin went red before a word of
migration was written. That is the binding working for the fourth round running.

```
python tools/check_claims.py -- command output, run by the recorder while adding these records
  docs/DECISIONS.md now holds 97 record(s); RECORD_FILE_PIN says 91.
    Adding a record IS a round. Append a LedgerRound that migrates at least
    12 number(s) out of docs/DECISIONS.md -- or that records a waiver
    saying why it could not -- and re-take the pin in the same commit.
  rc=1
```

### The payment: `0`, and a waiver

`docs/DECISIONS.md` stays at `42`. Nothing was cited, nothing was deleted, nothing was fenced. **Three
rounds have now walked this residue and the previous two found reachable numbers in it that a
per-record verdict had written off. This one did not, and it went looking with an instrument rather
than by reading.**

### The waiver is a measurement, because a waiver that is an opinion is a rubber stamp

The classification's `gate-able` bucket means *some measurement somewhere has this value* — a candidate
for citation, never a backing. So the question "is anything here citable" reduces to: for each of the
`42`, does any field in `bench/results.json` carry that value at the precision written, and is that
field a measurement of what the sentence is about?

```
a probe over the 42 deferred numbers in docs/DECISIONS.md against bench/results.json.
DERIVED -- every field carrying the value at the written precision, no judgement applied.
Run by the recorder; the probe is a scratch script and is NOT committed.

  numbers in the residue                                    42
    with at least one field carrying that value             16
    with NO field carrying that value anywhere              26

  the 16, with how many fields match and what the nearest one measures
    D-051  30      48 fields   e.g. admission.med1250.no_uppercase.false_positives
    D-048  31      44 fields   e.g. backronym.med1250.alignment.all.infeasible_by_cause.out_of_order
    D-048  29.73    1 field    monoculture.plod_all.proposals.vertices.jaccard_...__shapecue
    D-026  44      35 fields   e.g. admission.med1250.one_character.false_positives
    D-023  84.6     9 fields   e.g. genre.pmc_oa.body.proposals.vertices.jaccard_...__pyab3p
    D-023  2.1     16 fields   e.g. genre.pmc_oa.body.gold.long_form.overlap.class...._pct_of_gold
    D-023  30.09    1 field    genre.pmc_oa.abstract.proposals.vertices.jaccard_...__allcaps
    D-023  0.26     3 fields   e.g. backronym.sdu21_ad.accuracy.elapsed_seconds
    D-023  0.35     9 fields   e.g. genre.pmc_oa.body_matched.proposals.edges.jaccard_...
    D-023  7.6      4 fields   e.g. governed_catalog.socrata.sweep....voted_correct_pct
    D-023  25.50    1 field    shortform_contest.plod.all.convention.swing.definitional_at_caps_gold
    D-023  56.80    1 field    monoculture.sdu22_legal_dev.proposer.scispacy.long_form.overlap_recall
    D-023  30      48 fields   e.g. admission.med1250.no_uppercase.false_positives
    D-023  22.4     4 fields   e.g. disambiguation.sdu21.abstention_curve...gate_0.15_f1
    D-013  3.6     10 fields   e.g. governed_catalog.socrata.sweep....voted_correct_pct
    D-007  100    276 fields   e.g. admission.med1250.over_ten_characters.gate_lf1chsf_head_precision
```

**Not one of the sixteen is a measurement of the thing its sentence is about.** The residue is
milliseconds, microseconds and percentages of an import; the matches are Jaccard indices between
proposer vertex sets, false-positive counts, gate precisions, an elapsed-seconds field and a
percent-of-gold. **A millisecond has matched a Jaccard.** That is what `gate-able` has meant all along
and this is the first round in which the whole bucket was resolved to field names rather than to a
count.

**And the other twenty-six match nothing at all.** For those there is no candidate to adjudicate: the
measurement does not exist in this repository, which is exactly what the per-record reasons said and
which two rounds of walking had shown to be too wide *per number* on records where it happened to be
false. **This round tested that suspicion instead of inheriting it, and this time the verdict holds.**

### Deletion was walked too, and refused with reasons

Four deletion clauses stand: arithmetic over two numbers the reader still has (D-084 clause one), a
notional bound (two), a figure the sentence itself calls unquotable (three), and a verbatim restatement
inside the same record where the original stays (D-091 clause four). The reachable instances of all
four were taken by the previous two rounds. What remains:

- **`D-023`'s table total is a sum of the three rows beneath it**, which is clause one in spirit.
  Deleting a total leaves an empty cell in a rendered table and changes what the table asserts.
  **Refused on the surgery**, the same ground D-091 refused D-026's figure on.
- **Two duplicated figures survive inside `D-023`** — each restating a table cell in prose a few lines
  below it, which is clause four exactly. In both cases the number is the grammatical subject of its
  sentence: removing it requires rewriting the sentence, and the rule licenses deleting a number, not
  rewording a closed record. **Refused on the same ground**, and named here so a later round can hold
  this one to it rather than rediscover it.
- **`D-007`'s and `D-048`'s range endpoints** are the upper half of `50–100 %` and `22–31 %`, whose
  lower halves carry no unit and are invisible to the gate. Deleting one endpoint leaves a malformed
  range. **This is a one-sided arming rule and not a property of those sentences**, unchanged from
  D-091, and it is the only item on this list whose fix is a change to the gate rather than to the
  prose.

**A refusal ships with a disposition.** All three above are *refused, with the reason*, not *deferred*.

### R11: what the gate can and cannot see on the six records added here

Seven mutations, one at a time, each restored from bytes read before it and md5-verified, with an
unmutated control before and after. **All seven fire red and all seven name the thing that moved.**
`A` and `B` are the pin; `C` is the waiver itself; `D` is a fall claimed without accounting; `E`, `F`
and `G` are this round's own new citations and prose.

```
python tools/check_claims.py -- command output, not a benchmark measurement.
The messages go to stderr; the summary block stays on stdout and stays green-looking, which
is itself worth knowing.
  rc=0  control, unmutated                                    <nothing named>
  rc=1  A  pin left at the previous round's count       "now holds 97 record(s); pin says 91"
  rc=1  B  pin label left naming M3-PA                  "the newest round is 'M3-PB (the salvage)'"
  rc=1  C  the waiver set to the empty string           TWO problems: "moved 0 against a quota of
                                                        12" and "moved 0 out of docs/DECISIONS.md
                                                        against a floor of 12"
  rc=1  D  deferred 189 -> 188 with no accounting       "fell by 1 and the round accounts for 0"
  rc=1  E  a new one_sense citation edited by one       "stale rendered value: file says '247,501'"
  rc=1  F  a new differential citation repointed        "...documents_nope is not in
                                                        bench/results.json. Did you mean:"
  rc=1  G  prose added: "recall reached 99.94 %"        "1 unbacked claim(s): docs/DECISIONS.md:423"
  restored, both files md5 identical              rc=0  <nothing named>
```

**`C` is the mutation that matters**, because the waiver is the whole of this round's compliance and
it is the one thing here that a gate cannot grade on content. What `C` proves is only that its
*absence* is detected — that a round cannot silently skip the quota — and **not** that its presence
means anything. That is the honest limit and it is the same limit `docs/CLAIMS-LEDGER.md` §2 names.

**`G`'s red is worth reading beside D-091's `E`.** One round ago a prose insertion of a median
latency in spelled-out microseconds went green, because `latency` is not in the arming vocabulary and
a spelled-out `microseconds` is not in the unit vocabulary — the fifth measurement of that hole with
no fix. `recall` and a bare `%` are both in the vocabulary, so `G` reds. **The hole is unchanged; this
round simply did not step in it**, and a sixth measurement of it would still be worth less than the
first attempt to close it.

**And quoting D-091's counter-example verbatim was itself a red build, which is the best thing that
happened to this paragraph.** The sentence above originally reproduced that insertion word for word,
bare number included. `python tools/check_claims.py` stayed green — the number is invisible to the
shipped rules, which is the whole point of the example — but
`tests/test_claims_gate_coverage.py::test_the_measured_price_of_closing_the_blind_spot_is_still_zero`
went red: **the narrow widening D-052 refused now armed one number that the shipped rules do not, and
that number was this recorder's quotation of the example about the arming rules.** The refusal to
take that widening rests on its measured price being exactly zero on this tree, so a record
*describing* the hole would have raised the price of *closing* it. The quotation was paraphrased
instead. **A test that guards a decision's premise caught a document about that decision breaking the
premise**, and it did it in the round that had just finished congratulating itself for resolving
sixteen field names by hand.

### The ledger's seventh observation

```
python tools/check_claims.py -- the record file's own ledger, by round
  before the binding             115
  M2-P4 (the recorder is bound)   84    -31
  M2-P5 (the recorder pays)       66    -18
  M2-P6 (the walk)                54    -12
  M3-PA (the second walk)         42    -12
  M3-PB (the salvage)             42      0    WAIVER
```

`73` of `115` in five bound rounds. **The shape D-091 warned about — a floor that has become a target —
is not what happened.** Two rounds paid exactly `12` because `12` was what the walk found, and the
third found nothing because the walk had finished. **The distinction matters for how the next round
reads this row**: a waiver taken at the end of a burn-down is a different object from a waiver taken to
avoid one, and the probe above is the only thing that separates them.

**What the waiver does not license.** It is written for one round and names one reason. The register may
still not grow; the pin still moves with every record added; and **the next round owes the same probe
before it may take the same waiver**, because the residue becomes citable the moment somebody writes a
runner that saves an import attribution — which is `29` of the `42` in one record.

### No pre-registration was written, and that is stated rather than back-filled

Every workstream in the previous phase wrote a falsifier down before measuring, and D-091 scored six
of them together and concluded that **the value of a pre-registration here has not been that it
predicts; it is that it makes the surprise legible.** **This round wrote none.** It began from a
brief rather than from a question, and a retrospective "here is what I would have predicted" written
after the outcome is worth nothing and would be worse than the omission, because it would look like
the thing it is not.

What is available instead is that **the brief itself made three checkable assertions and two of them
were wrong**, which is a base rate of the same kind arriving from the other direction:

```
the commissioning brief's own claims, scored against the tree
  1  U3's adjudicated share of genuinely-distinct groups is 40.83 %      WRONG -- that is the
                                                                        artefact share; genuine
                                                                        is 4.17 %  (D-092)
  2  record the third R15 round and its brief-premise correction         ALREADY DONE -- all four
                                                                        elements are in D-088
                                                                        (D-095)
  3  D1 corrected ten stated reasons, not nine                           RIGHT -- re-derived
                                                                        against both audit pages
                                                                        (D-094)
```

**Two of three is worse than the `20.8`–`25.0` % this project measures about its own claims**, on a
denominator of three, which is far too small to mean anything and is reported because a round that
declines to pre-register owes the reader *some* falsifiable statement about its own reliability.

### How it fails

**No pre-registration, so nothing in this round can have been surprising in a way a reader can
check.** The three brief-claims scored above were checked because they were checkable, not because
anybody committed in advance to checking them, and a recorder who verifies exactly the claims that
turn out to be verifiable is selecting on the outcome.

**The probe's judgement is a reading and it was taken by one person, once.** "Not one of the sixteen is
a measurement of the thing its sentence is about" is an adjudication over sixteen field names. It is
strongly supported — a Jaccard is not a millisecond — but it is the same *kind* of claim the two
previous rounds got wrong in the opposite direction, and it is not machine-checkable.

**The probe is not committed.** It is a scratch script; `tools/` is not this round's to edit, for the
same reason D-091 recorded when it edited `tools/check_claims.py` anyway. **So the waiver's evidence is
a fenced block with a described method and no artifact**, which is weaker than every other measurement
in this phase, and the honest name for it is a re-derivable command that nobody can re-run without
rewriting it.

**The recorder edited `tools/check_claims.py` again**, and that file is not on this round's list of
files this workstream owns. Two data constants — the trajectory row and the pin — with no behaviour
change. **A round that edits its own scorer says so in the record rather than in the diff**, and the
alternative is a red build with no route to green.

**A waiver is free text and nothing grades it.** `docs/CLAIMS-LEDGER.md` §2 says so, in the paragraph
explaining why the floor exists underneath it: *"a waiver is free text and nothing grades it. Without a
floor underneath, the first inconvenient round becomes a permanent exemption granted one sentence at a
time."* **This is the first inconvenient round.** The only thing standing between this waiver and that
prediction is that the next round has to write its own, and nothing in the gate makes the next one
harder to grant than this one.

**And the pin remains a deterrent where it is not a mechanism**, unchanged: a recorder who adds records
may bump the count and leave the label naming the round that is already newest, and the floor passes,
because that round's migrations satisfied it once. The defence is that it is a visible source edit in a
file the gate reads.

---

## D-096 — The fourth cold read ran, found `11` new defects including **three copies of one false sentence about what the sdist ships**, and **could not write its ledger row for the second consecutive round.** The gate stayed green throughout, because it cannot tell "no read happened" from "a read happened and could not record it"

**Status:** read-only; findings in `docs/notes/cold-read-4-findings.md`, `docs/cold-reads.toml`
**unwritten** · **Decides:** nothing; it reports · **Amends:** nothing this recorder owns; it names
false sentences in five files, three of which no workstream in this round owns ·
**Evidence:** `docs/notes/cold-read-4-findings.md`; `python tools/second_reader.py --check`, green ·
**No experiment number spent — experiment eleven is still free**

**This is the read Mandate III Phase A owed and did not deliver**, run one round late against `387f739`
plus the working tree. Both triggers were re-derived rather than assumed: trigger A served six files,
trigger B served `docs/SUPPORT_MATRIX.md` — **for the second read running, because the cursor has not
moved.**

### The three findings a maintainer should read first

1. **Three shipped documents say the sdist omits two registers it ships.** `docs/GATES.md`,
   `docs/SECOND-READER.md` and `tools/second_reader.py` each state that `.github/gates.toml` and
   `docs/cold-reads.toml` are absent from a distribution. `387f739` added both to `MANIFEST.in`.
   **The refutation was executed against a real sdist built from this tree, not against `MANIFEST.in`**
   — both members present. Exact replacement paragraphs are written for all three copies.
   **The third copy is in a source file no trigger on the policy page can reach**, which is D-089's
   structural finding arriving with a live instance attached.
2. **Every published `deferred` figure in `docs/CLAIMS-LEDGER.md` is stale, including the column that
   page instructs the reader to treat as the stable one.** Its classification table publishes a
   three-round total; its trajectory block publishes a three-round row; its section `4` publishes a
   record-file residue more than double the live one. **The round that added the sixth trajectory row
   edited that page in the same commit and did not update it.** The page's own instruction is to read
   the deferred column as a fact and the rest as a reading taken at a moment.
3. **`docs/CLAIMS-LEDGER.md` §6 says the R15 sampler has run twice; D-088 and `CHANGELOG.md`, written
   the same round, say three.** D-088's own **Status** line names §6 as a shipped site for that
   correction, and `CHANGELOG.md`'s entry points the reader at §6 — where the pointer lands on the
   opposite claim. **A correction that names its own destination and does not arrive there is the worst
   available outcome**, because it is invisible to everybody except a reader who follows the pointer.

Eight further findings are in the note, four of them outright falsehoods with replacement text written.
Two land on `docs/DEFINITION-OF-DONE.md`, which this recorder owns, and are **fixed in this round**; one
lands on `src/acronymkit/__init__.py`, one on `docs/EVALUATION.md`, and one is a `git ls-files --eol`
count published as a repository property when it is a per-machine, per-checkout one.

### The read's own verdict on the front door, because it is the sentence this project's positioning rests on

The rewritten package docstring D-089 shipped **does** say what the library is for and did **not** trade
one overclaim for the opposite one; the paragraph that would have made it a new slogan is the one that
saves it, by disclosing on the front door that a caller reading only the phrase gets a governed-looking
string. All doctests pass, `import acronymkit` binds no submodule, and the star-import surface equals
`__all__`.

**One sentence in it is false, and it is the governance-flavoured one:** *"each keeps its losing
comparison in the same table as its own figure"*, counted over the four capabilities the same sentence
enumerates. Two of the four hold. Generation's only comparison is between this library's own presets,
and the backronym subsystem has an accuracy number for one half and none for the other. **The same
sentence is in `docs/POSITIONING.md`, so fixing one copy leaves the other false** — the two-copy shape
D-091 counted at six instances and did not stop counting.

### The policy's own failure, and it is a decision nobody has taken

`docs/cold-reads.toml` was **not** written, for the second consecutive read. The consequences are
mechanical: the cursor has not advanced, so the rotation served the same file twice; six open findings'
`reviewed_in` still names the previous date; and eleven new findings live only in a note that
`docs/notes/*.md` exclusions, the register's schema, the refutation-non-empty rule and the decay clock
all fail to reach.

**`python tools/second_reader.py --check` is green throughout, and it is green precisely because no read
row was written.** The gate cannot distinguish *no cold read happened* from *a cold read happened and
could not record it*. `docs/SECOND-READER.md` §7 already says this in terms; it now has two consecutive
instances.

**The blocking decision is one sentence and nobody has taken it:** is the read-only boundary **prose** —
the reader may write `docs/cold-reads.toml` and nothing else, which is what §5.1's `applied_by` field
was designed for — or **filesystem**, with the reader writing a note and a second party transcribing?
§5.1 says in terms that the boundary *"is not a filesystem permission"*. **Two consecutive briefs have
made it one.** This record does not take the decision either, because the policy page is not this
recorder's file; it takes the position that the prose reading is the one §5.1 describes and that a brief
which converts it into a filesystem rule is overriding a policy without amending it.

**Warning for whoever pastes the read row:** the row alone turns `--check` **red**, because five of the
six open findings are already at the open-read limit and a third read row makes them span three. **The
row and the five dispositions must be pasted together. That is the mechanism working and must not be
read as the paste being wrong.**

### What the read verified clean, because a read that only ever finds defects is not a measurement

- `docs/EVALUATION.md`'s new performance section is the best R17/R18 handling in the tree: work counts
  gated per cell, wall clock fenced with the machine named and its three-run spread printed beside it,
  and three cross-checks separating *a stage that does less work* from *a stage that measures less
  work*. Its arithmetic ties out.
- D-093's falsifiable claim re-derives at the commit preceding the work: `git grep` for the reference
  artifact's identifiers at `387f739` returns nothing, so *"never read by this repository before this
  round"* holds.
- `docs/GATES.md`'s headline survives in every part — the in-situ count, the gate and environment
  census, the four-way decomposition summing to the total, and the jobs carrying a `no_gates_reason`.
- Three fixes cold read 3 specified landed in the words it specified.

### How it fails

**One reader, and this one had a brief that named two things to look at hardest.** Both produced
findings, which is what a good pointer does and is **also indistinguishable from a reader that found
what it was sent to find.** Eight documents' worth of the policy's four questions were answered in one
sitting; `docs/SECOND-READER.md` §7 already calls that a sample.

**`docs/EVALUATION.md` is the largest document in the tree and the read covered five diff hunks and two
sections.** Everything else on that page is unchecked and is not claimed to be.

**No mutation was taken in the tree.** The read-only rule forbids a write and §4.3 requires one, so
nothing in this read demonstrates a gate failing where it runs. Cold read 3 at least worked around this
against a byte-identical copy and recorded that such a table's return codes are not comparable to one
taken in the tree; this read did not do even that.

**The note added `68` numbers to the unexamined residue.** Every one is fenced or code-spanned, so no
ratchet moved and no gate can see any of them — **the exact D-052 property this repository keeps
cataloguing, arriving through a document written to catalogue it.** The command is printed beside every
block, and that convention is the only thing separating it from hiding.

**One finding is stated as unreproducible rather than as wrong, on purpose.** A `w/crlf` count is a
property of a working tree on a machine; the read's machine disagrees with the page's, and the read
cannot establish that the page was wrong when it was written — only that it ships a per-checkout fact as
a repository property with no stamp. D-091 recorded the same quantity taking five values inside two
rounds.

**One finding's direction is arguable and the read resolved it one way.** The false docstring sentence
could be read as merely loose if a hedge in the preceding clause carries into it. The read treats it as
unqualified because it is a separate independent clause with its own subject, and because
`docs/POSITIONING.md` states the same thing with no hedge at all. **If the hedge does carry, the finding
drops from "false" to "a phrasing tighter than the measurement"** — the same rule one notch lower, and
not a clean bill.

**The structural proposal is a costing and not a measurement of whether prose review works.** It prices
what widening the rotation to source files costs; it does not measure what that buys, and the strongest
argument against it survives the costing: `tools/check_claims.py` already scans the package's Python, so
numbers in module docstrings are gated today and what the widening adds is prose review — the thing this
repository has the least evidence works. **And the proposal does not reach the false sentence in
`tools/second_reader.py`**, which neither the current policy nor the proposed one covers.

**Nothing was applied by the read, by design**, and four `docs/POSITIONING.md` findings from cold read 3
remain unapplied with that page out of both triggers this round. **`docs/INSTALL.md` and
`docs/ENTERPRISE.md` still pin a version the packaging metadata has moved past** — cold read 3 called
that the most directly user-damaging thing it found, and it is unaltered.

---

## D-095 — **Four of ten agents finished their work and died formatting the final report.** Three left green, tested, gated work with no self-assessment, the recorder wrote seven records without them, and at least one conclusion was wrong as a result. **D-092, D-093 and D-094 rest on salvage and a reader must know that**

**Status:** a process finding, and a property of three records rather than a change to any file ·
**Decides:** how D-092, D-093 and D-094 are to be read · **Amends:** D-085's A2 verdict (retired in
place there), D-091's pre-registration `P6` (annotated there), and D-091's *"Carried on trust"* list,
which did not know it was missing three workstreams · **Evidence:** `bench/results.json`'s
`one_sense.*` and `differential.*` run ids, present in the tree with nothing pointing at them for a
round; the corrections dated `2026-08-25` in the two audit pages · **No experiment number spent**

### What happened

Mandate III Phase A ran ten agents. Six completed. **Four finished their work and failed on the final
structured report:** the one-sense-per-document measurement, the prohibition-reasons pass, the harness
validation, and the cold read. Of those four, three had already written their output into the tree —
`18` run ids, `5` run ids, and corrections in two shipped documents — and the fourth, the cold read,
had produced nothing yet and did not run at all until the round after.

**The recorder then wrote D-085 through D-091 without them.** D-085 recorded A2 as stopping for two
reasons and named the second *"the workstream commissioned to decide A2 did not report to this
recorder at all"*. That sentence was true about the reporting channel and false about the work, and it
is retired in place at D-085. D-091's own pre-registration scored `P6` **RIGHT** partly on the clause
*"and U3 will not have reported"* — a prediction that came true about a report and false about a
measurement, and is annotated there.

### The gap this leaves, stated as a property of the records rather than as an apology

**Nobody has said how those three fail.** Every other record in this file carries a *How it fails*
section written by the workstream that did the work — the person who knows which arm was not re-run,
which figure rests on a small denominator, which claim was carried on trust. For D-092, D-093 and
D-094 there is no such person available, and the sections those records carry were written by this
recorder from `bench/results.json`, a runner and two audit pages.

**That is a weaker artifact and it is weaker in a specific direction.** A recorder reading stored
fields can see what was measured. It cannot see:

- what the workstream tried first and abandoned;
- which of its own numbers it distrusted;
- the arm it did not run and would have named;
- the near-miss it caught by hand, which is the class of finding that has been the most valuable single
  item in four consecutive rounds of pre-registration scoring.

**Every one of those is a category this project's records have been most useful for**, and for three
records this round they are absent. Each of the three says so, in its own *How it fails*, in the first
sentence.

### The salvage found two errors the salvage brief itself carried

Recorded because they bear on how much confidence a reader should place in a reconstruction.

1. **A share was handed to this recorder under the wrong label.** The brief reported the
   `one_sense` adjudication as putting the *genuinely-distinct* share at
   40.83<!--claim:one_sense.pmc_oa.audit.distinct.label_artefact_pct:.2f--> %. That is the **artefact**
   share. The genuine share is
   4.17<!--claim:one_sense.pmc_oa.audit.distinct.label_genuine_pct:.2f--> %, and the two labels have
   opposite consequences for the mechanism being priced. D-092 carries the correction.
2. **A coverage multiple was described one notch tighter than it measures.**
   5.95<!--claim:one_sense.pmc_oa.a2.high_precision.a2_new_coverage_multiple_of_current:.2f-->× is the
   *new* occurrences over the currently-reached ones, not total coverage over current coverage. Also
   in D-092.

**A reconstruction that is checked against the stored fields catches this; one that is not, does not.**
Both were caught by resolving every figure to a run id and field before writing the sentence around it,
which is the only reason this record can name them.

### The brief that commissioned this salvage carried a third defect: it asked for a record that already exists

Its second explicit instruction was to record the third R15 sampling round — the `25.0` % not-true
and `20.8` % strictly-false rates, the observation that `20.8` % has now presented itself in three
different cells across three rounds, the `20.8`–`29.2` % sensitivity band, and the refutation of the
brief's own premise about which round measured the failure-mode split. **All four are already in
D-088**, written the round before, including the refutation and including D-088's own title clause
recording that `20.8` % reappeared in a different cell.

**Nothing is added here and no duplicate record was written.** It is recorded as a finding because
of what it is an instance of: **a brief about stale citations, carrying a stale instruction, in a
phase whose sharpest single result was a sampler catching its own brief citing the wrong round.**
D-088 recorded that as *"the most valuable thing this round produced"*. This is the same shape one
level up — the instruction layer is not outside the failure class it commissions measurements of
either — and the correct disposition for an instruction whose work is already done is to say so and
decline, not to write a second record that agrees with the first.

### The mechanism question, asked rather than left implicit

**Nothing in this repository can tell "a workstream produced no result" from "a workstream produced a
result and could not report it".** The two are identical from the outside: a green tree, a passing gate
suite, and no record. `tools/check_claims.py` measures whether numbers on a page resolve; it has nothing
to say about measurements in `bench/results.json` that no page cites. **`one_sense.*` and
`differential.*` sat in the tree for a round with zero citations pointing at them**, which is precisely
the failure mode `docs/GATES.md` opens with, and D-091 flagged the same shape for `roundtrip.*` one
round earlier — *"nineteen run ids sat in `bench/results.json` with nothing pointing at them"*.

**That is now three occurrences of the same shape in two rounds**, and it is the first time it has been
caused by the reporting channel rather than by a recorder's attention. A check that lists run ids no
scanned document cites is one function and nobody has written it. **Named here as a specific, cheap
thing to build, not as an aspiration** — and not built in this round, which owns `docs/DECISIONS.md`,
`docs/DEFINITION-OF-DONE.md` and `CHANGELOG.md` and not `tools/`.

### How it fails

**This record is written by the party with the strongest interest in its framing.** The recorder is
reporting on a failure whose consequence was that the recorder published a wrong conclusion. "Four
agents died formatting a report" is one available account; "the recorder shipped a verdict on an
absence without checking `bench/results.json` for the absent workstream's run ids" is another, and it
is the sharper one. **Both are true and the second one is this recorder's.** A `git diff` on
`bench/results.json` at the time D-085 was written would have shown `one_sense.*` and `differential.*`
present; nobody looked.

**The count of ten and four is carried on trust.** This recorder was told how many agents ran and how
many died. Nothing in the tree records an agent roster, so the arithmetic of this record's own headline
is the one figure in it that cannot be re-derived from the repository — which is a fair description of
most process findings and is worth saying anyway.

**"Nobody has said how those three fail" is itself unfalsifiable from inside.** If one of the three
workstreams did write a self-assessment somewhere that did not reach this tree, this record is wrong in
the same way D-085 was wrong, for the same reason, one round later. **The defence is that D-085's error
is what taught this recorder to look in `bench/results.json` first**, and there is no equivalent place
to look for a prose report.

**No mechanism was added.** The check that would have caught this — run ids no document cites — is
described in one paragraph above and does not exist, which is the same disposition
`docs/SECOND-READER.md` §7 has carried for its CI job across three rounds. **A finding whose remedy is
specified and unbuilt for a second round running is a backlog item wearing a record's clothes**, and
this is that finding's first round.

---

## D-094 — The do-not list survived its own audit: **ten stated reasons corrected, not nine, seven markers in place, and no conclusion fell.** One figure with no derivation has drifted into being arithmetically true, which is a worse state than staleness

**Status:** shipped — `docs/AUDIT-2026-08.md` (a new *Corrections to the do-not list* section, a
front-matter pointer and seven in-place markers), `docs/AUDIT-PROHIBITIONS-2026-08.md` section `12`,
`tools/prohibitions.py` · **Decides:** what D-077 left open — whether any prohibition falls when its
reason is corrected · **Amends:** D-077's *"nine stated reasons need correcting"*, which is `10` ·
**Evidence:** the two audit pages and the counts re-derived below ·
**No experiment number spent — experiment eleven is still free**

### The count, re-derived by this recorder rather than quoted

```
grep, run by the recorder against the working tree -- command output, not a measurement
  git grep -c "^### C[0-9]" -- docs/AUDIT-2026-08.md                     10   corrections
  git grep -n "^> \*\*\(REASON\|REASONS\|FIGURE\|FIGURES\)[A-Z ]*CORRECTED 2026-08-25"
    -- docs/AUDIT-2026-08.md                                              5   blockquote markers
  the same page, table-cell markers linking to #corrections-to-the-do-not-list
                                                                          2   cell markers
  git grep -c "THE PROHIBITION STANDS" -- docs/AUDIT-2026-08.md           5
  git grep -c "STRONGER THAN WRITTEN" -- docs/AUDIT-2026-08.md            2
  prohibitions lifted                                                     0
  conclusions that fell                                                   0
```

**Ten corrections, seven markers, nothing lifted.** The arithmetic of `10` against D-077's `9` is
itemised on the page and is worth restating because it runs in both directions: one of the nine did
**not** land here — the stale wheel-headroom constraint in D-020 item `1`, which lives in a decision
record and was reported to its owner instead — and **two were added**, because D-077's own list left
two of its own `FALSE` verdicts with no correction aimed at the document a reader actually meets them
in. So `9 − 1 + 2 = 10`.

### Nothing lifted, and the two outcomes are kept apart

**Not one prohibition's conclusion falls.** Where a figure fell, the conclusion it supported had margin
to spare — twice by three orders of magnitude. **Two came out stronger than they were written**, and a
do-not list that only ever weakens under audit is a list nobody will trust.

The strongest instance is the one that reduces this project's own prize: the per-candidate lever was
priced against a comparator of `83.85`, the shipped baseline is now
84.21<!--claim:extraction.med1250.acronymkit.exact_f1:.2f-->, the oracle selector reaches
85.44<!--claim:analysis.med1250.selection_ceiling.oracle_selector_exact_f1:.2f-->, and the whole prize
is therefore about a point and a quarter rather than about a point and a half. **A correction that
makes the refusal easier is the one most likely to be right**, and it is recorded as `C8` rather than
buried.

### One item is *reported* rather than lifted, and the recommendation is to measure it

After `C4`, the refusal to vendor `SecureFinAI-Lab/Regulations_abbreviation` rests on a **qualitative**
claim alone: its quantitative half — a coverage percentage — has no corpus, no command, no read date
and exactly one occurrence in this repository, which is the assertion itself. What remains is *the
matches are homographs*, and for this library's positioning that is decisive on its own. **It is also
unmeasured.** Nobody has counted how many of that catalogue's entries are homographs against a real
schema's vocabulary.

**So the recommendation is to measure it, not to lift it**, and the decision is the maintainer's. That
distinction is the whole point of the exercise: the reason is not wrong, it is unquantified, and a
future round tempted to reopen the item on the ground that "the reason was refuted" would be making
exactly the error this pass exists to prevent.

### A figure with no derivation has drifted into being true, and that is worse than staleness

`A10.003` — a count of the package's public symbols — was graded `UNREPRODUCIBLE` at the audit's own
commit on all seven readings anybody could construct, and that verdict was right at that commit. At
`HEAD` one of the seven now returns the published figure, because one public name was added in between.

**A reader spot-checking it today finds agreement and stops.** It is still not a derivation: under the
reading that reproduces it the governed sub-count is a different number from the one published beside
it, and one of the seven readings is not a function of the tree at all — the same command returns two
different values at the same commit depending on which submodules the harness has already imported.
**This page published a reading whose value depends on the process that took it**, and the drift is what
makes that visible.

### Two things were reported to this recorder rather than corrected by that workstream

Both live in `docs/DECISIONS.md`, which no workstream but this one may edit. Both are recorded here so
they are dispositioned rather than filed.

- **D-020 item `1` states a wheel headroom that is stale**, and the record's own footnote is about that
  exact recurrence. **Corrected in place in this round, D-037 style** — the previous figures are left
  visible with the reason beside them. See the retirement note now in D-020.
- **`C7`: the instruction to retire D-011's headroom figure was never carried out.** The audit's reason
  for retiring it reproduces —
  65<!--claim:analysis.med1250.selection_ceiling.wrong_gold_explained_by_no_strategy:,--> of the
  131<!--claim:analysis.med1250.selection_ceiling.greedy_wrong:,--> wrong answers have a start boundary
  and no strategy that can reach them. **This round does not execute it either, and says why:** D-084 cited that
  figure rather than retiring it, on the ground that a citation makes it checkable, and retiring a
  *recommendation* inside a closed record changes what the record asserts. **R14 disposition: refused,
  on the ground that it is a maintainer's call and not a recorder's**, and it is now named in two places
  instead of one so the next reader cannot mistake "nobody executed it" for "somebody withdrew it".

### How it fails

**THIS RECORD HAS NO `how_it_fails` FROM THE PERSON WHO DID THE WORK.** D-095 records why. The counts
above were re-derived by this recorder against the tree; the *judgement* that no conclusion fell is the
workstream's, carried on trust, and it is the load-bearing claim of the whole exercise.

**"Nothing lifted" is the outcome an auditor is structurally most likely to reach.** A pass that
corrects ten reasons and lifts nothing looks like diligence and is indistinguishable, from outside,
from a pass that could not bring itself to conclude against the list it was auditing. The one item that
came closest — the vendoring refusal, now standing on a qualitative claim alone — was **reported**
rather than lifted, which is the right call and is also the comfortable one.

**The corrections are prose and nothing enforces them.** `tools/check_claims.py` cannot read a
sentence. A future round that restates a corrected reason in different words, or in a file the pathspec
excludes, walks straight past every mechanism here — the same hole D-088 recorded about the retirement
it shipped, arriving through a different page.

**The page's own population moved under it.** Its enumerator now reports more closed records and more
stratum-B figures than the page published, because records were added to `docs/DECISIONS.md` after the
draw — including, this round, six more. **Every marker inserted into the audit was deliberately phrased
to carry no free-standing number**, so that the frame a re-run draws is still the frame the page drew;
phrasing chosen to protect a denominator is worth disclosing and is disclosed there.

**One correction changes nothing on the page it is written on.** `C7` is accurate as written; what is
stale is the tree's compliance with it. An instruction nobody executed and nobody withdrew is
indistinguishable, to the next reader, from one that was — and after this record it is at least
indistinguishable *out loud*.

---

## D-093 — **The harness validation hole is closed**, and the record did not know it was closed. `1,252` of `1,252` documents agree with the original NLM implementation's own published output — which is evidence the harness reads a system correctly and is **not** evidence the convention matches the literature

**Status:** measured, nothing changed in `bench/scoring.py` — `bench/run_scorer_differential.py`,
`tests/test_scorer_differential.py`, `5` new run ids · **Decides:** the standing "is the harness
itself right" question, in the direction of yes, on one corpus and one axis ·
**Amends:** nothing this recorder wrote; it supplies the evidence for a sentence about the harness
that was withdrawn for want of it · **Evidence:**
`differential.med1250.{reference_output,reference_output_mutations,scorer_agreement,specification,harness_ceiling}`
· **No experiment number spent — experiment eleven is still free**

### There is no reference scorer, so it obtained reference *output* instead

The obvious validation — run somebody else's scorer over the same predictions and compare — is not
available, and the run establishes that mechanically rather than assuming it:
`shared_task_scorers_expressing_pair_extraction` is
0<!--claim:differential.med1250.reference_output.shared_task_scorers_expressing_pair_extraction:,-->
against
2<!--claim:differential.med1250.reference_output.shared_task_scorers_in_tree:,--> shared-task scorers
present in the tree, and Ab3P's own build has
0<!--claim:differential.med1250.reference_output.ab3p_makefile_scoring_targets:,--> scoring targets in
7<!--claim:differential.med1250.reference_output.ab3p_makefile_recipe_targets:,--> recipe targets.
The `pyab3p` binding this repository actually calls exposes
0<!--claim:differential.med1250.reference_output.pyab3p_scoring_entry_points:,--> scoring entry points
across
2<!--claim:differential.med1250.reference_output.pyab3p_public_names:,--> public names. **Nobody in
this ecosystem ships a scorer for this task**, which is itself worth recording.

So the run took the next best thing: **the original implementation's own output file**, at a pinned
commit, hashed, read from a URL and not vendored.

```
the reference artifact, as recorded in differential.med1250.reference_output
  source     https://raw.githubusercontent.com/ncbi-nlp/Ab3P/
             41130cddfcba1449ba612905d4a51274f8f565a8/identify_abbr-out
  commit     41130cddfcba1449ba612905d4a51274f8f565a8
  sha256     c4b85fa6e30658a430a4910fa8038a6dec59c2072d58dd60d9b1ddbe6c365dbd
  licence    Public domain (United States Government Work), read from that commit's README
  vendored   False
  attributed Sohn S, Comeau DC, Kim W, Wilbur WJ. BMC Bioinformatics. 2008;9:402. NLM.
```

### The result, with the split that makes it readable

| | |
|---|---:|
| documents compared | 1,252<!--claim:differential.med1250.reference_output.documents_compared:,--> |
| documents agreeing | 1,252<!--claim:differential.med1250.reference_output.documents_agreeing:,--> |
| documents disagreeing | 0<!--claim:differential.med1250.reference_output.documents_disagreeing:,--> |
| pairs agreeing | 1,053<!--claim:differential.med1250.reference_output.pairs_agreeing:,--> |
| pairs only in this harness | 0<!--claim:differential.med1250.reference_output.pairs_only_in_harness:,--> |
| pairs only in the reference | 0<!--claim:differential.med1250.reference_output.pairs_only_in_reference:,--> |
| reproduces the gated row `extraction.med1250.pyab3p` | `True` |

**And the split that stops this being read as bigger than it is:**
515<!--claim:differential.med1250.reference_output.documents_discriminating:,--> of the `1,252`
documents are **discriminating** — they carry at least one pair, so agreement on them is information —
and 737<!--claim:differential.med1250.reference_output.documents_vacuous:,--> are **vacuous**, both
sides finding nothing. *"1,252 of 1,252 agree"* is true, and `737` of that `1,252` is two systems
agreeing that an abstract contains no abbreviation at all. **The discriminating count is the one to
quote and it is published beside the total for that reason.**

**The reader is mutation-tested, not merely run.**
5<!--claim:differential.med1250.reference_output_mutations.mutations_run:,--> mutations of the
reference reader,
5<!--claim:differential.med1250.reference_output_mutations.mutations_detected:,--> detected, with a
control at zero:

```
differential.med1250.reference_output_mutations -- documents differing, of 1,252
  control            0     unmutated; the agreement above is this row
  brackets_removed 512
  casefold         508
  first_half       121
  spaces_removed   515
  words_reversed   517
```

`515` is the discriminating count exactly, which is what a mutation that changes every non-empty
record should produce, and `first_half` at `121` is the one that would have been missed by a weaker
control.

### Two further arms, because "the harness agrees with itself" is the objection

- **An independently written counter.**
  12<!--claim:differential.med1250.scorer_agreement.verdicts_compared:,--> verdicts across
  6<!--claim:differential.med1250.scorer_agreement.prediction_sets:,--> prediction sets,
  12<!--claim:differential.med1250.scorer_agreement.verdicts_agreeing_on_figures:,--> agreeing,
  0<!--claim:differential.med1250.scorer_agreement.verdicts_disagreeing:,--> disagreeing, over
  5,159<!--claim:differential.med1250.scorer_agreement.pairs_scored:,--> pairs. The run records
  `shares_code_with_scorer_under_test = False` and — the field that matters —
  **`written_by_a_second_author = False`.** One person wrote both counters. That is a check on a
  transcription error and not on a shared misreading of the task.
- **The specification's own sensitivity.** Pooling across the corpus versus averaging per document
  moves F1 by
  0.0<!--claim:differential.med1250.specification.axis_pooling_max_abs_f1_delta:.1f--> on every one of
  the twelve cells. Scoring short forms under the relaxed rule moves exactly one system —
  `acronymkit`, by
  0.8<!--claim:differential.med1250.specification.axis_relaxed_short_form_max_f1_delta:.1f--> points,
  reclassifying `9` pairs — and moves the other five by zero. **A scoring choice that moves only the
  system whose repository the scorer lives in is the finding**, and it is a small one pointing in the
  unflattering direction.

### The ceiling: this harness cannot score a perfect system as perfect

A gold-as-prediction arm run through the harness returns precision
100.0<!--claim:differential.med1250.harness_ceiling.max_precision_pct:.1f--> % and recall
98.2<!--claim:differential.med1250.harness_ceiling.max_recall_pct:.1f--> %, F1
99.09<!--claim:differential.med1250.harness_ceiling.max_f1_pct:.2f--> %:
22<!--claim:differential.med1250.harness_ceiling.unreachable_pairs:,--> of
1,221<!--claim:differential.med1250.harness_ceiling.gold_pairs:,--> gold pairs are unreachable, across
22<!--claim:differential.med1250.harness_ceiling.documents_affected:,--> documents. **Every extraction
recall figure this project has published is measured against a scale whose top is `98.2` and not
`100`**, and nothing said so before this run.

### What this establishes, and — said as plainly as possible — what it does not

**Establishes.** The harness reads one external system's output correctly, converts it to pairs
correctly, and produces the row this repository publishes for that system. A transcription or parsing
defect in the `pyab3p` path would have to be present identically in the NLM binary's own output file to
survive this, which is not a coherent way for a defect to exist. On that axis the harness is validated,
and it is the axis that was open.

**Does not establish, and the distinction is the whole reason this record is written carefully:**

- **It is not evidence that this project's scoring convention matches the literature.** The withdrawn
  sentence this run was commissioned to replace appealed to *the literature*; what arrived is agreement
  with *one implementation's output*, at one commit, on one corpus. Exact-match on
  `(short form, long form)` after this repository's own normalisation is this repository's convention.
  Agreeing with Ab3P about which pairs are in a document says nothing about whether the published F1 is
  computed the way the papers compute theirs — **and D-076 already measured what an annotation
  convention alone is worth on a neighbouring task, at `26.66` points.**
- **It validates the reader, not the scorer.** The `1,252`-document agreement is between two readings of
  what `pyab3p` found. The arithmetic that turns pairs into precision, recall and F1 is checked by the
  second arm, whose own record says one author wrote both.
- **One corpus, and a contaminated one.** MED1250 is `role = "tuning"`, `contaminated = true`. Nothing
  here is quotable as a headline and none of it is offered as one.

### How it fails

**THIS RECORD HAS NO `how_it_fails` FROM THE PERSON WHO DID THE WORK**, for the reason D-095 records.
What follows is read off five run ids and a runner.

**The reference is an output file, so the comparison is only as good as the pinning.** `sha256` and a
commit are recorded, the licence was read from that commit's README rather than assumed, and nothing was
vendored — which is right for the licence question and means **the artifact is fetched over the network
every time anybody re-derives this.** If that URL moves, this record becomes unreproducible in exactly
the way `docs/AUDIT-PROHIBITIONS-2026-08.md` catalogues.

**The two interpreters differ.** The harness comparison ran under
`3.12.13`, and every other figure in this phase was taken on `3.13.4`. Nothing here depends on the
interpreter, and that is an argument rather than a measurement.

**`reference_pairs_raw` is
1,053<!--claim:differential.med1250.reference_output.reference_pairs_raw:,--> and
`reference_pairs_scored` is
1,034<!--claim:differential.med1250.reference_output.reference_pairs_scored:,-->.** Nineteen pairs are
read and then not scored. The agreement figure is over the raw set and the F1 is over the scored set;
the run stores both, and nobody has written down what the nineteen are. **That is the loosest thread in
this record.**

**The specification arm found the one axis that moves, and moved it in this project's own favour to
notice it.** `9` pairs of `acronymkit`'s and nothing else. A reader entitled to be suspicious would ask
whether the relaxed short-form rule was chosen because it flatters, and the honest answer is that the
run reports the delta rather than adopting it, which is a disposition and not a defence.

**The runner is not registered in `.github/gates.toml`** and no CI job re-derives any of it, for the
third time in this phase and for the same in-situ debt reason.

---

## D-092 — **One sense per document was measured, the workstream did report, and A2's second stopping reason is withdrawn.** The rule that still stops A2 stops it by its letter and not by its reason: **A5 widens candidate generation and A2 does not**

**Status:** measured, not built — `bench/run_one_sense.py`, `tests/test_one_sense.py`,
`18` new run ids · **Decides:** nothing on its own; it supplies the evidence D-085 recorded as
missing · **Amends:** D-085's A2 row and its *"the workstream commissioned to decide A2 did not
report to this recorder at all"*, both retired in place at D-085; and D-091's pre-registration `P6`,
which scored *"U3 will not have reported"* RIGHT · **Evidence:**
`one_sense.pmc_oa.{roster.{raw,admitted}.{case_sensitive,case_folded},resolver.*,a2.*,bridge.*,a2_projected_genuine,audit,sample,splitter_agreement,splitter_cost}`
· **No experiment number spent — experiment eleven is still free**

**This record exists because the previous one was written without it.** D-085 recorded A2 as stopping
for two independent reasons and named the second an absence. The absence was a reporting failure, not
a measurement failure: the work ran, it saved `18` run ids into `bench/results.json`, and its answer
is not a kill. What follows is the answer, and then the argument about whether the remaining reason
reaches A2 at all.

### Two instruments, and the one everybody would have quoted is the wrong one

| instrument | what it can answer | rate |
|---|---|---|
| **roster** — each article's own `<def-list>` | do authors *declare* two senses for one short form | 0.0371<!--claim:one_sense.pmc_oa.roster.admitted.case_sensitive.violation_pct:.4f--> % of 2,695<!--claim:one_sense.pmc_oa.roster.admitted.case_sensitive.short_form_groups:,--> groups |
| **resolver** — every definition the extractor finds in the text | does a short form *carry* two expansions A2 would have to arbitrate | 5.75<!--claim:one_sense.pmc_oa.resolver.high_precision.term_shaped.violation_pct:.2f--> % of 25,616<!--claim:one_sense.pmc_oa.resolver.high_precision.term_shaped.short_form_groups:,--> groups |

**The run's own note says the roster rate is a FLOOR and not an estimate, and that caveat is carried
here because it is the run's own and not this recorder's.** A roster is a curated one-to-one table.
Asking it how often a short form has two senses is asking a table built to have one row per short form
how often it has two, and the answer it gives —
1<!--claim:one_sense.pmc_oa.roster.admitted.case_sensitive.groups_with_two_or_more_expansions:,-->
group in
2,695<!--claim:one_sense.pmc_oa.roster.admitted.case_sensitive.short_form_groups:,--> over
1,839<!--claim:one_sense.pmc_oa.roster.admitted.case_sensitive.articles:,--> articles — is a fact about
declaration habits. **A one-in-three-thousand headline was available here and the workstream refused
it.** That refusal is the most defensible thing in this record.

**And a third instrument proves the refusal was right rather than merely cautious.** The `bridge` arm
takes the short forms the roster carries exactly once and asks whether the extractor finds a competing
expansion for them in the same article's text:
403<!--claim:one_sense.pmc_oa.bridge.high_precision.with_an_expansion_the_roster_does_not_carry:,--> of
2,694<!--claim:one_sense.pmc_oa.bridge.high_precision.singly_rostered_short_forms:,--> singly-rostered
short forms have one —
23.58<!--claim:one_sense.pmc_oa.bridge.high_precision.competing_pct_of_reached:.2f--> % of those the
extractor reaches. A competitor is not proof of a second sense; the extractor has no gold. **It is
proof that the roster does not settle the question**, which is exactly what the roster's own rate would
otherwise have been read as doing.

### What A2 buys and what it pays, bounded on both sides

The model measured is the one A2 proposes: *commit to the first definition in document order, license
every whole-token occurrence of that short form at or after it.* On the `HIGH_PRECISION` profile:

| | |
|---|---:|
| occurrences A2 would license | 247,500<!--claim:one_sense.pmc_oa.a2.high_precision.licensed_occurrences:,--> |
| of them, outside every definition sentence — i.e. **new** | 211,913<!--claim:one_sense.pmc_oa.a2.high_precision.licensed_occurrences_outside_every_definition_sentence:,--> |
| the new share of what A2 licenses | 85.62<!--claim:one_sense.pmc_oa.a2.high_precision.a2_new_coverage_pct_of_licensed:.2f--> % |
| the new occurrences as a multiple of what the sentence-scoped mechanism reaches today | 5.95<!--claim:one_sense.pmc_oa.a2.high_precision.a2_new_coverage_multiple_of_current:.2f-->× |
| licensed occurrences under a short form with only one expansion | 86.37<!--claim:one_sense.pmc_oa.a2.high_precision.licensed_occurrences_unambiguous_pct:.2f--> % |
| correctness cost, **floor** | 0.581<!--claim:one_sense.pmc_oa.a2.high_precision.wrong_floor_correctness_pct_of_licensed:.3f--> % of licensed |
| correctness cost, **ceiling** | 9.68<!--claim:one_sense.pmc_oa.a2.high_precision.wrong_ceiling_correctness_pct_of_licensed:.2f--> % of licensed |

**`5.95×` is a multiple of the *new* occurrences over the current ones and not of total coverage**, and
this recorder's first draft of that row said "`5.95×` current coverage", which is the wrong sentence for
the right number. Total coverage goes up by about seven times; the *new* half is `5.95` times the old
half. A phrasing tighter than the measurement is a false phrasing, and this one was tighter in the
flattering direction.

The three shipped profiles agree to within noise on all of it —
0.5775<!--claim:one_sense.pmc_oa.a2.biomedical.wrong_floor_correctness_pct_of_licensed:.4f--> /
0.5795<!--claim:one_sense.pmc_oa.a2.general.wrong_floor_correctness_pct_of_licensed:.4f--> /
0.581<!--claim:one_sense.pmc_oa.a2.high_precision.wrong_floor_correctness_pct_of_licensed:.3f--> % on the
floor and
9.62<!--claim:one_sense.pmc_oa.a2.biomedical.wrong_ceiling_correctness_pct_of_licensed:.2f--> /
9.66<!--claim:one_sense.pmc_oa.a2.general.wrong_ceiling_correctness_pct_of_licensed:.2f--> /
9.68<!--claim:one_sense.pmc_oa.a2.high_precision.wrong_ceiling_correctness_pct_of_licensed:.2f--> % on the
ceiling — so nothing here turns on which profile a caller runs.

**The comparator, verbatim from the run rather than paraphrased:** *"the mechanism A2 replaces answers
at NONE of the 211913 out-of-sentence occurrences, so its error rate there is 0 by declining rather than
by being right. A2 buys coverage and pays in correctness."* That sentence is the whole trade and it is
the workstream's own.

### The decomposition, and the number this recorder was handed wrong

Groups with more than one expansion decompose three ways —
`distinct` (two different things),
`refinement` (one is a longer form of the other),
`surface` (the same thing spelled differently):

| class | groups | |
|---|---:|---|
| `distinct` | 746<!--claim:one_sense.pmc_oa.a2.high_precision.groups_distinct:,--> | |
| `refinement` | 318<!--claim:one_sense.pmc_oa.a2.high_precision.groups_refinement:,--> | |
| `surface` | 409<!--claim:one_sense.pmc_oa.a2.high_precision.groups_surface:,--> | |

`distinct` is the class that matters, and it was adjudicated on a sample of
120<!--claim:one_sense.pmc_oa.audit.distinct.sample_size:,--> drawn from a frame of
738<!--claim:one_sense.pmc_oa.audit.distinct.frame_size:,-->.

**THE BRIEF THAT COMMISSIONED THIS RECORD REPORTED THAT SAMPLE AS PUTTING THE GENUINELY-DISTINCT SHARE
AT `40.83` % WITH A CI OF `[31.95, 50.18]`. IT IS NOT THE GENUINE SHARE. IT IS THE ARTEFACT SHARE.**
The adjudication has four labels and the run stores all four:

| label | share of the `distinct` sample | what it means |
|---|---:|---|
| `artefact` | 40.83<!--claim:one_sense.pmc_oa.audit.distinct.label_artefact_pct:.2f--> % | one of the two "expansions" is not an expansion at all |
| `variant` | 53.33<!--claim:one_sense.pmc_oa.audit.distinct.label_variant_pct:.2f--> % | the same referent under two surfaces |
| `genuine` | 4.17<!--claim:one_sense.pmc_oa.audit.distinct.label_genuine_pct:.2f--> % | two senses, really |
| `unclear` | 1.67<!--claim:one_sense.pmc_oa.audit.distinct.label_unclear_pct:.2f--> % | the annotator could not tell |

The genuine share carries a Clopper-Pearson interval of
[1.37<!--claim:one_sense.pmc_oa.a2_projected_genuine.genuine.distinct.share_ci_low_pct:.2f-->,
9.46<!--claim:one_sense.pmc_oa.a2_projected_genuine.genuine.distinct.share_ci_high_pct:.2f-->] %; the
`[31.95, 50.18]` the brief attached to it is
[31.95<!--claim:one_sense.pmc_oa.a2_projected_genuine.artefact.distinct.share_ci_low_pct:.2f-->,
50.18<!--claim:one_sense.pmc_oa.a2_projected_genuine.artefact.distinct.share_ci_high_pct:.2f-->], the
artefact interval. **The two labels point in opposite directions for A2**: a `genuine` group is a group
A2 can get wrong, and an `artefact` group is one where A2's exposure is real but its *error* is
somewhere between zero and the ceiling, because the label says one expansion is spurious and does not
say which one A2 committed to. The run says this itself, in `artefact_note`, and projects the two
separately —
0.355<!--claim:one_sense.pmc_oa.a2_projected_genuine.genuine.projected_wrong_ceiling_pct_of_licensed:.3f--> %
of licensed for `genuine` against
3.211<!--claim:one_sense.pmc_oa.a2_projected_genuine.artefact.projected_wrong_ceiling_pct_of_licensed:.3f--> %
for `artefact`.

**A recorder correcting a record for having been written without a workstream's report was one
paste away from publishing that workstream's numbers under the wrong label.** That is the round's
sharpest instance of its own theme and it is recorded rather than quietly fixed.

### **A5 widens. A2 extends.** The rule that stops A2 does not reach it, and this record takes a position

Mandate III says *"do not ship A2 or A5 without A1 measured first"*, and gives its reason:
*"widening candidate generation costs precision; an independent verifier is what buys it back."*
Three things bear on whether that still stops A2, and the record must engage all three rather than
restate the rule.

- **The instruction was satisfied, not violated.** A1 *is* measured — D-085, `19` run ids, a go/no-go
  written before the evidence. "Do not ship without A1 measured first" is a sequencing rule and the
  sequence happened. What D-085 established is that A1 comes back NO-GO as a verifier; that is a
  result of the instruction being obeyed, not a reason the instruction is still outstanding.
- **A2 does not widen candidate generation.** A2 proposes no pair that some other mechanism has not
  already confirmed. It takes a definition the extractor already found and licenses it to later
  occurrences of the same short form in the same document. The candidate set is unchanged; what
  changes is how far an accepted candidate reaches. **A5 widens and A2 extends**, and the rule's
  stated reason — precision lost at proposal time, bought back by a verifier — is a statement about
  widening. Applied to A2 it is applied to a mechanism it does not describe.
- **So A1's NO-GO binds A5 tightly and binds A2 only by the rule's letter.**

**The position: A2 is not blocked by A1, and it is blocked by two other things, both of which are this
record's own.** Stating them out loud rather than leaving the reader with a clearance:

1. **Its own measured correctness cost.** `0.581` % to `9.68` % of licensed occurrences is a wide band
   and its ceiling is not small. The comparator makes it worse, not better: the mechanism A2 replaces
   has an error rate of exactly zero on the `211,913` occurrences in question, because it declines to
   answer at all. **A2 replaces a mechanism that is never wrong with one that is sometimes wrong**, and
   whether that is a good trade is a product judgement about what a caller does with an unanswered
   occurrence — which nobody here has measured.
2. **The blast radius on every published recall figure.** Licensing `211,913` new occurrences changes
   what `extract()` returns on almost every biomedical document. Every recall number this project has
   published is measured against a mechanism that answers inside definition sentences. Shipping A2
   without re-measuring them republishes them as figures about a different system.

**Neither of those is A1's NO-GO, and the record should stop saying that it is.** The decision to ship
or not ship A2 is the maintainer's; what this record removes is a reason that was never about A2 and an
absence that was never real.

### R17 and R18 on the one perf figure this workstream produced

The sentence splitter is **quadratic in document length**, and the evidence is a ratio and not a
duration:

```
one_sense.pmc_oa.splitter_cost -- work counts gated, wall clock unarmed. Only the RATIO
between rows is read; a linear splitter shows about 2, a quadratic one about 4.
  characters   sentences   splitter calls   seconds (unarmed)   ratio to previous row
       6,700         100                1              0.0325   --
      13,400         200                1              0.1293   3.98
      26,800         400                1              0.5172   4.00
      53,600         800                1              2.0823   4.03
```

Doubling the input doubles the sentence count and roughly quadruples the time, on three consecutive
doublings. The seconds are an unarmed note on one machine; **the ratio is the finding and the ratio is
machine-independent in the only sense that matters, which is that all four rows were taken on the same
one.** This is why the corpus run chunks documents at a
20,000<!--claim:one_sense.pmc_oa.splitter_agreement.document_character_ceiling:,-->-character ceiling
rather than splitting whole articles.

### How it fails

**THIS RECORD HAS NO `how_it_fails` FROM THE PERSON WHO DID THE WORK.** The workstream completed its
measurements and died formatting its final report, so what follows is the recorder reading run ids and
a runner, not a self-assessment. D-095 records that failure as a process finding; the consequence here
is that the failure modes below are the ones visible from `bench/results.json`, and a workstream knows
things about its own run that its output does not carry.

**The adjudication is one annotator, one operating point, one domain, and the annotator wrote the
ladder being adjudicated.** The run says so in its own `note`. A four-label vocabulary applied by the
person who defined the four labels is not an independent judgement, and every projected figure in this
record inherits that.

**The projection's denominators and the A2 figures quoted here come from different profiles.** The
adjudication and `a2_projected_genuine` ran on `biomedical`
(`frame_size` 738<!--claim:one_sense.pmc_oa.audit.distinct.frame_size:,-->, matching
`resolver.biomedical.term_shaped.class_distinct`); the coverage and cost table above is
`HIGH_PRECISION` (`groups_distinct`
746<!--claim:one_sense.pmc_oa.a2.high_precision.groups_distinct:,-->). The two differ by eight groups
and nothing here turns on the difference, but **a projected share was multiplied against a frame from a
neighbouring arm**, and that is stated rather than smoothed.

**Every frame is `term_shaped` only.** Single-letter short forms and discourse markers — the keys an
extractor collides most often — are excluded by construction from the adjudication frame. The
`all` rows in `one_sense.pmc_oa.resolver.*` show what that costs: the unrestricted violation rate is
5.74<!--claim:one_sense.pmc_oa.resolver.high_precision.all.violation_pct:.2f--> % against
5.75<!--claim:one_sense.pmc_oa.resolver.high_precision.term_shaped.violation_pct:.2f--> % restricted, so
the *rate* barely moves — but the excluded population is the one a reader would most want a number
about, and this run does not have one.

**The corpus is `single_annotator_reference` and PMC-OA only.** No conclusion here transfers to any
other genre, and the same-article PMC set is the corpus D-075 built to hold provenance constant for a
different question entirely.

**The two sentence splits disagree on where a definition lives, and the run measured it rather than
assuming it away.** On the
40<!--claim:one_sense.pmc_oa.splitter_agreement.documents:,--> sampled documents short enough to split
whole, the chunked and whole-document splits agree on the definition's sentence
78.64<!--claim:one_sense.pmc_oa.splitter_agreement.definition_sentence_agreement_pct:.2f--> % of the
time —
88<!--claim:one_sense.pmc_oa.splitter_agreement.definitions_whose_sentence_differs_from_the_engines:,-->
definitions land in a different sentence. The *pair set* is identical on
40<!--claim:one_sense.pmc_oa.splitter_agreement.documents_whose_pair_set_is_identical_with_capture_on:,-->
of `40`, so what A2 licenses does not move; **what moves is the boundary between "inside a definition
sentence" and "new", which is the denominator of the `85.62` % headline.** That sample is also the
short half of the corpus by construction.

**The runner is not registered in `.github/gates.toml`.** Nothing in CI re-derives any of this, for the
same reason D-085's runner is unregistered: registering it raises an in-situ debt already at its
ceiling. Neither new file has ever run outside this laptop.

---

## D-085 — **The round trip cannot verify, and the number that kills it is not the beam.** A1 is NO-GO as commissioned and A2 and A5 stop with it; the mechanism survives only under a framing nobody wrote down

**Status:** measured, not built — `bench/run_roundtrip_verifier.py`, `tests/test_roundtrip_verifier.py`,
`19` new run ids · **Decides:** Mandate III's A1, and through A1 its dependants A2 and A5 ·
**Amends:** the commissioning brief's premise that `_beam_bound` is a fatal precondition ·
**Evidence:** `roundtrip.independence`; `roundtrip.{med1250,pmc_oa}.{census,ceiling,recall,misses,disagreement,correlation,extractor_proposed,beam_bound_disposition,verdict_arm_work}`
· **No experiment number spent — experiment eleven is still free**

**This is the record that decides the phase's architecture.** Three of Mandate III's workstreams are
bets stated in prose and one measurement was supposed to settle the first of them. It did, in the
negative, and the number that settled it is not the one anybody was arguing about.

### The go/no-go, stated before the evidence rather than after it

| workstream | verdict | the number it rests on |
|---|---|---|
| **A1** — the forward generator as a round-trip **verifier** of extractor output | **NO-GO** | recall at an unpruned search is 42.09<!--claim:roundtrip.med1250.recall.beam_control_never_cuts.recall_pct:.2f--> % on MED1250 and 51.75<!--claim:roundtrip.pmc_oa.recall.beam_control_never_cuts.recall_pct:.2f--> % on PMC-OA |
| **A1′** — the same mechanism as a precision **filter** on proposals | **GO, conditionally** — and nobody commissioned it | 25.60<!--claim:roundtrip.med1250.extractor_proposed.high_precision.discrimination_points:.2f--> points of discrimination; precision 92.01<!--claim:roundtrip.med1250.extractor_proposed.high_precision.precision_before_filter_pct:.2f--> → 95.86<!--claim:roundtrip.med1250.extractor_proposed.high_precision.precision_after_filter_pct:.2f--> |
| **A2** — gated by A1 | ~~**STOP**, for two independent reasons~~ **AMENDED — see the retirement below** | ~~A1 is NO-GO; **and the workstream commissioned to decide A2 did not report to this recorder at all**~~ |
| **A5** — gated by A1 | **STOP** | A1 is NO-GO |

**A2 stops twice over and the second reason is an absence, not a result.** The phase brief names a
workstream as the one that decides A2. No report from it reached the recorder, and nothing in this
tree is its output. **An undelivered measurement is not a negative measurement**, and A2 is recorded
here as undecided-for-want-of-evidence rather than as refuted. If that workstream ran and its report
was lost, this record is the thing that says so.

> **THE PARAGRAPH ABOVE AND THE `A2` ROW ARE RETIRED, `2026-08-26`. THE WORKSTREAM RAN.** It saved
> `18` run ids under `one_sense.*` into `bench/results.json` before this record was written, and its
> report died on the way to the recorder rather than never existing. *"Nothing in this tree is its
> output"* was false of the tree at the moment it was published, and a `git diff` on
> `bench/results.json` would have said so. **The retired sentences are left in place because a record
> that quietly acquires the right answer teaches nobody how it got the wrong one**, and because this
> is the class of error — a verdict on an absence, written without grepping for the thing said to be
> absent — that this file exists to keep visible.
>
> **What replaces them.** A2's *second* reason is withdrawn outright: it was never a result. A2's
> *first* reason survives only by the letter of the rule that states it. Mandate III's *"do not ship
> A2 or A5 without A1 measured first"* gives its reason as *"widening candidate generation costs
> precision; an independent verifier is what buys it back"* — and **A2 does not widen candidate
> generation.** It licenses already-confirmed definitions to later occurrences of the same short
> form; it proposes nothing new. **A5 widens; A2 extends.** So A1's NO-GO binds A5 tightly and binds
> A2 only by a rule whose stated reason does not describe it.
>
> **A2 is still not clear to ship, and for two reasons that are its own rather than A1's**: a measured
> correctness cost of `0.581` % to `9.68` % of licensed occurrences against a mechanism whose error
> rate on those occurrences is zero by declining; and the breaking-change blast radius on every recall
> figure this project has published. **The decision is the maintainer's.** D-092 carries the
> measurement and the argument; D-095 carries why this record was written without it.

### Why the beam question was the wrong question, established with a control

The brief's premise was that `_beam_bound` is a fatal precondition. It is not, and the measurement
that shows it is a firing count.

At shipped defaults the generator consults its beam for
2<!--claim:roundtrip.med1250.beam_bound_disposition.shipped_pairs_where_the_beam_is_read:,--> of
`1,112` gold pairs —
0.18<!--claim:roundtrip.med1250.beam_bound_disposition.shipped_pairs_where_the_beam_is_read_pct:.2f--> % —
because `_fits_exhaustively` decides first. So "recall at beam *b*" is not a property any caller
exercises on this corpus, and the runner had to *force* beam mode with a per-pair node budget to
answer the question at all. **The most generous repair conceivable — a bound that never cut the
eventual optimum — is worth
0.18<!--claim:roundtrip.med1250.beam_bound_disposition.max_points_an_oracle_bound_could_recover_at_shipped_defaults:.2f-->
points on MED1250 and
0.13<!--claim:roundtrip.pmc_oa.beam_bound_disposition.max_points_an_oracle_bound_could_recover_at_shipped_defaults:.2f-->
on PMC.** `_beam_bound` is a real defect and it is worth two pairs in eleven hundred.

The brief's own reproduction — *"at `beam=4` it returned `3` candidates against `500` at an
effectively unbounded beam"* — reproduces exactly **and only once `max_search_nodes` is cut below the
space's own enumeration count**. At the shipped `50,000` nodes, `beam=4` and `beam=1,000,000` return
the identical `2,809` candidates. The observation is about a configuration in which the node budget
was lowered, and it was carried forward as a statement about the defaults.

**The sweep is readable at all because of a control aimed at something else.**
`beam_control_never_cuts` runs the forcing budget behind a beam of `1,000,000` and returns
`truncated_pairs` = 0<!--claim:roundtrip.med1250.recall.beam_control_never_cuts.truncated_pairs:,--> on
both corpora, byte-identical to the exhaustive arm on MED1250. **That control also caught the arm
named `exhaustive` not being exhaustive**: on PMC one roster definition overflows five million nodes,
drops into beam mode and loses a hit. The ceiling and the miss decomposition are read off the control
for that reason.

### The finding that was on nobody's list, including the workstream's own

The ceiling is not a search fact and it is not a configuration fact. **The generator emits only
prefixes of successive words; the Schwartz & Hearst aligner places a character anywhere inside a
word.** That single asymmetry accounts for
442<!--claim:roundtrip.med1250.misses.misses_architectural:,--> of MED1250's `644` misses —
39.75<!--claim:roundtrip.med1250.misses.misses_architectural_pct_of_corpus:.2f--> % of the whole
corpus — and 756<!--claim:roundtrip.pmc_oa.misses.misses_architectural:,--> of PMC's `1,156`,
31.55<!--claim:roundtrip.pmc_oa.misses.misses_architectural_pct_of_corpus:.2f--> %. It is unreachable
at every setting of every knob.

The configuration-free ceiling confirms it: with **unlimited** letters per word and no search at all,
60.25<!--claim:roundtrip.med1250.ceiling.prefix_alignable_at_inf_letters_pct:.2f--> % of MED1250 pairs
and 68.20<!--claim:roundtrip.pmc_oa.ceiling.prefix_alignable_at_inf_letters_pct:.2f--> % of PMC pairs
are prefix-cuttable. The aligner accepts
85.70<!--claim:roundtrip.med1250.ceiling.aligner_accepts_pct:.2f--> % and
90.69<!--claim:roundtrip.pmc_oa.ceiling.aligner_accepts_pct:.2f--> % of the same pairs — it beats the
architectural prefix ceiling by
25.45<!--claim:roundtrip.med1250.ceiling.aligner_minus_prefix_ceiling_points:.2f--> points on MED1250.
**A round-trip verifier cannot exceed roughly six pairs in ten on this corpus at any setting of any
knob**, and the workstream's own pre-registered culprit — `max_acronym_length = 6` — was measured and
raising it from `6` to `24` changed recall by exactly zero.

### The two standing unknowns behind A1, both closed

**Are the two signals empirically correlated anyway? No.** Pearson
0.2862<!--claim:roundtrip.med1250.correlation.pearson_score_vs_confidence:.4f--> and Spearman
0.3345<!--claim:roundtrip.med1250.correlation.spearman_score_vs_confidence:.4f--> between the
generator's score and the aligner's confidence; phi
0.5604<!--claim:roundtrip.med1250.disagreement.pooled.phi_between_verdicts:.4f--> between the binary
verdicts on a pool that includes seeded negatives. All well under the `0.70` and `0.85` redundancy
thresholds written down in advance. The
9<!--claim:roundtrip.med1250.disagreement.gold_positives.roundtrip_only:,--> pairs per corpus where
the round trip accepts and the aligner rejects are the direct evidence that a second opinion is a
second opinion — against
494<!--claim:roundtrip.med1250.disagreement.gold_positives.aligner_only:,--> going the other way.

**Is structural independence real? At module scope yes, at runtime one word short.** On the default
paths the two closures share `0` resource modules. With `extraction_capture_sentences=True` the
extractor lazily builds a `Tokenizer` and shares exactly one — `acronymkit.stopwords`, used for
sentence splitting and never for eligibility. The brief's *"no lexicon, no n-grams, no stopwords"* is
right at module scope and wrong on a non-default path. `roundtrip.independence`.

### The R14 disposition, honoured against a pre-commitment

The workstream wrote down in advance that it would add an admissible `bound(state)` to `Scorer`
**only if** the beam turned out to be consulted on real inputs — below `90` % running exhaustive. It
came back at `99.82` %, so no `bound(state)` was added, `src/` was not touched, and **no R19
byte-identity obligation arose**. What shipped instead is a verification-only configuration with its
own gated figure: recall
49.10<!--claim:roundtrip.med1250.recall.verification_only.recall_pct:.2f--> % for `29×` the states and
about four minutes, explicitly **not** proposed as a shipped default. Option (a) is refused with
arithmetic, not with effort: it is worth `0.18` points against `57.91` points of distance to a
perfect verifier.

### The pre-registration against its outcome

`4` of `8` predictions wrong, and the two biggest wrong in opposite directions.

```
pre-registration vs outcome -- scratchpad/PREREG-roundtrip.md, written before any measurement
  P1  ceiling 55-75 %, kill below 50 %      WRONG   42.09 -- and it FIRED ITS OWN KILL CONDITION
  P2  top-N truncation costs 15-25 points   WRONG   0.27 points; the named mechanism was innocent
  P3  >= 99 % run exhaustive at defaults    RIGHT   99.82 % -- and it re-scoped deliverable 1
  P4  beam sweep monotone, b=1 in 20-35 %   RIGHT   monotone on both corpora; b=1 at 33.00
  P5  round trip rejects 25-40 % of         HALF    direction right, magnitude 51.8 %; the
      aligner-accepted positives                    "worthless if 0" cell is 9, just outside 10-60
  P6  rejects 20-35 % of proposals          WRONG   51.12 % (HIGH_PRECISION), 55.43 % (BIOMEDICAL)
  P7  Pearson r in 0.10-0.40                RIGHT   0.2862 / 0.2606, guard passed at 8 distinct
  P8  phi in 0.3-0.6                        RIGHT   0.5604 / 0.6239
  R14 pre-commitment                        HONOURED -- P3 above 90 %, so no Scorer hook
```

**And the finding that reverses the verdict's sign was never pre-registered at all.** The workstream
wrote down *how many* rejections there would be and never *whether the rejections correlate with the
pair being wrong*. Measured after the fact, they do: on extractor proposals the round trip rejects
`74.67` % of non-gold pairs against `49.07` % of gold ones. **"A1 does not ship" is the right call on
the verification framing and the wrong call on a filtering framing nobody wrote down**, and this
record carries both rather than picking the one that reads better.

### How it fails

**Both corpora are contaminated and no figure here may be quoted as a headline.** MED1250 is
declared `role = "tuning"`, `contaminated = true`; PMC-OA is `single_annotator_reference`,
`contaminated = true`. `python tools/splits.py --check` prints that no uncontaminated corpus carries
`role = "held_out"` for extraction. The `42.09` that stops three workstreams is a supporting number
about two tuning corpora, and it is being used to stop work rather than to claim any.

**MED1250's gold was annotated by the authors of a Schwartz & Hearst system to Schwartz & Hearst
criteria** — the exact confound this measurement exists to avoid. PMC-OA is in the run for that
reason, and the two corpora disagree by `9.66` points on the ceiling while agreeing on every
ordering. **The disagreement is unexplained.** Genre, chemistry-heavy short forms and annotation
convention are all live and nothing separates them.

**The number the go/no-go turns on and the number most likely to be quoted are different numbers, and
the second is the weaker one.** `92.01 → 95.86` rests on `75` non-gold proposals out of `939`.
Seventy-five items is a small denominator for a two-decimal claim, and *not matching gold* is not the
same as *wrong* — MED1250's gold deliberately excludes synonym and non-aligning definitions a reader
would call correct. The discrimination is a floor with an unquantified bias, and it is unreplicated.

**`prefix_alignable` is the workstream's arithmetic and not the generator's.** It is an upper bound
computed over maximal alphanumeric runs rather than over `Tokenizer` output, and it ignores hyphen
policy, numeral policy and every filter. Where it and the generator disagree the gap is attributed to
"configuration", which is right in aggregate and could be wrong on an individual pair.

**The correlation is computed on the subset the round trip accepted** —
468<!--claim:roundtrip.med1250.correlation.pairs_with_both_signals:,--> of
1,112<!--claim:roundtrip.med1250.correlation.pairs_offered:,--> — because the generator's score does
not exist where the short form was not generated. So `r` describes the accepted `42` % and is silent
about the `58` % where the mechanism would actually be deciding. And the aligner's confidence has
8<!--claim:roundtrip.med1250.correlation.distinct_aligner_confidences:,--> distinct values on that
pool, so Spearman is the coefficient to read and both are published together.

**The verification-only arm was not run on PMC**, so
`roundtrip.pmc_oa.misses.recovered_by_verification_config` is `null` and the recovery figure stands
on one corpus. **The runner is not registered in `.github/gates.toml`** and no CI job re-derives any
of this, because registering it would raise an in-situ debt already at its ceiling. **And neither new
file has ever run outside this laptop.**

---

## D-086 — **Provenance construction is the governed hot path**, larger than the other three cost centres put together on all four arms. P2 to P6 are re-ranked on that, one of them is nearly dead, and the premise the top-ranked bet rests on is false against the only callers that exist

**Status:** measured, nothing optimised — `bench/run_governed_perf.py`,
`tests/test_governed_perf_runner.py`, `10` new run ids, `docs/EVALUATION.md` ·
**Decides:** the ranking of Mandate III's P2 through P6 · **Amends:** the audit's
`164,652`-pair Socrata count and its `107,012`-identifier corpus, both taken on trust and both wrong ·
**Evidence:** `governed_perf.{socrata,sec_xbrl,fixture_schema}.census`;
`governed_perf.{socrata.empty,socrata.fixture,sec_xbrl.empty,fixture_schema.fixture}`;
`governed_perf.{caller_census,inherited_counts,profiler_overhead}` ·
**No experiment number spent — experiment eleven is still free**

Mandate III lists five optimisations for the governed subsystem and ranks them in prose. Nobody had
measured what the hot path spends its time on. This record is the measurement and the re-ranking it
forces.

### The go/no-go on each, with the number

| bet | verdict | the number it rests on |
|---|---|---|
| **P2** — lazy provenance | **GO, rank 1, wider than predicted, with a named design constraint** | provenance is 70.15<!--claim:governed_perf.socrata.empty.stage_provenance_pct:.2f--> % of the Socrata call, 73.55<!--claim:governed_perf.sec_xbrl.empty.stage_provenance_pct:.2f--> % on SEC XBRL, 49.85<!--claim:governed_perf.fixture_schema.fixture.stage_provenance_pct:.2f--> % on the memo-saturated arm |
| **P3** — memoisation | **GO, rank 2, shape changed: the ceiling is an eviction policy, not a second memo** | 24,536<!--claim:governed_perf.socrata.census.distinct_tokens:,--> distinct tokens against a `_MEMO_LIMIT` of 4,096<!--claim:governed_perf.socrata.census.memo_limit:,-->, 5.99<!--claim:governed_perf.socrata.census.distinct_tokens_per_memo_limit:.2f-->× over, and the memo **clears** when full |
| **P4** — streaming batch | **DOWNGRADED to a delivery mechanism for P2, not an optimisation** | `_prepare` runs once per identifier out of `139.87` Python calls — `0.7` % of the call graph |
| **P5** — a tokenizer automaton | **NO-GO, near-dead** | tokenisation is 9.82<!--claim:governed_perf.socrata.empty.stage_tokenise_pct:.2f--> % on Socrata, the path is already a C regex, and `_scan` executed `0` times across `245,927` real identifiers |
| **P6** — free-threading | **UNMEASURED, and given no number** | nothing in this phase bears on it, and the workstream said so instead of inventing a figure |

**Provenance is not merely first, it is larger than everything else combined, on every arm.**
`70.15` against `30.13` on Socrata; `73.55` against `26.43` on SEC XBRL; `49.85` against `43.14` even
on the fixture arm where the expansion memo serves
92.98<!--claim:governed_perf.fixture_schema.fixture.expansion_memo_hit_pct:.2f--> % of token
expansions. `expand_identifier` builds
578,816<!--claim:governed_perf.socrata.empty.provenance_records_constructed:,--> frozen records for
`155,272` Socrata identifiers —
3.728<!--claim:governed_perf.socrata.empty.provenance_records_per_identifier:.3f--> per call — and a
phrase-only reimplementation that emits byte-identical phrases runs `3.35×` faster.

### The premise under rank 1 is false against the only caller population that exists

The lazy-provenance bet has two halves: *provenance is expensive* and *most callers do not read it*.
The first is measured above. **The second is measured and it is false.**

0<!--claim:governed_perf.caller_census.library_phrase_only:,--> of
3<!--claim:governed_perf.caller_census.library_classified:,--> classified `expand_identifier` call
sites inside `src/acronymkit` read only `.phrase` —
0.00<!--claim:governed_perf.caller_census.library_phrase_only_pct:.2f--> % — and `0` of `2` in
`tools/`. Every phrase-only site in the repository is benchmark code scoring segmentation. The
pre-registration predicted `>= 60` % and set its falsifier at `< 40` %; the measurement is zero.

**That is a constraint on P2 and not a refutation of it.** Inside this library an
`IdentifierExpansion` is used as a provenance record, and `is_fully_known` is a property over every
token's `is_known` — so a design that deferred the records makes the library's own audit path slower
rather than faster. **A lazy-provenance design must therefore keep `is_fully_known` eager or it makes
the governance instrument slower at being a governance instrument**, which is the one thing it may
not do.

### Two inherited counts, both verified rather than quoted, and both wrong

The commissioning brief carried two corpus sizes forward from the audit. Neither holds.

- **Socrata is 155,272<!--claim:governed_perf.inherited_counts.socrata_pairs_measured:,--> pairs
  here, not 164,652<!--claim:governed_perf.inherited_counts.socrata_pairs_claimed:,-->** — short by
  9,380<!--claim:governed_perf.inherited_counts.socrata_pairs_shortfall:,-->. That is the **third**
  independent re-derivation to land away from the audit's figure; D-074 recorded the second.
- **The 107,012<!--claim:governed_perf.inherited_counts.identifier_corpus_claimed:,-->-identifier
  corpus does not exist in this tree.**
  2<!--claim:governed_perf.inherited_counts.identifier_corpus_sources_present:,--> of its
  8<!--claim:governed_perf.inherited_counts.identifier_corpus_sources_claimed:,--> named sources are
  present, there is no fetcher for `fhir` or `openfda` anywhere in `tools/`, and no corpus in
  `bench/splits.toml` is declared at that size. It is reported **unreconstructible** rather than
  replaced with the `137,720`-identifier union of the two populations this tree does hold, because
  that is a different population.

### The Zipfian premise is half right and its named tokens are wrong

Reuse is high — `94.21` % of Socrata token occurrences are repeats, and only
5.79<!--claim:governed_perf.socrata.census.distinct_tokens_pct:.2f--> % of occurrences are distinct —
but the head is **flat** and it is not `ID`/`DT`/`TXN`/`AMT`/`CD`. The five commonest Socrata tokens
carry 6.07<!--claim:governed_perf.socrata.census.top5_token_occurrence_pct:.2f--> % of occurrences
against a predicted `>= 10` %, and SEC XBRL's commonest tokens are English function words. Only the
fixture corpus looks like the premise, and it is built from the fixture catalog's own token pool.

**What survives is a re-shaped bet with a structural ceiling.** The commonest
`4,096` Socrata tokens carry
88.32<!--claim:governed_perf.socrata.census.tokens_within_memo_limit_occurrence_pct:.2f--> % of all
occurrences — so the headroom is real — and the shipped memo **clears when full rather than
evicting**, so the current structure cannot reach it. **P3's ceiling is an eviction policy.**

### R17 and R18, applied

Every figure ships with a work count: tokenizer passes, catalog lookups split by origin
(`423,544` from the token path, `27,719` from the digit rejoin on Socrata), index decisions, both
memo hit rates, provenance records constructed, class-word lookups, `_prepare` calls, validation
calls and total Python calls. Wall-clock is printed in a fenced block with the machine named and is
**never armed** — and the fence carries the three-run comparison that motivates the rule: `8,118` /
`11,597` / `8,895` ns per identifier with **every count identical to the unit**. A second reader
reproduced that structure independently, getting `12,342` / `11,994` / `8,375` ns with the work-count
lines md5-identical across all three passes.

**Both memos fire `0` times on every published governed configuration, and that is a derivation, not
a measurement**: `_Memo` records no misses and every published governed figure uses an empty catalog,
so neither map can ever hold anything. The cost is paid anyway — `_memo(policy)` ran `874,807` times
on the Socrata pass. On the one arm where a catalog answers, the `resolve` memo serves `3` of
`23,934` lookups because the expansion memo in front of it short-circuits everything else.

### The pre-registration against its outcome

`3` of `7` falsified, and every magnitude wrong again.

```
pre-registration vs outcome -- scratchpad/PREREG-hotpath-dominance.md
  P1a provenance >= 35 % of self-time      RIGHT, under-predicted by half   70.15
  P1b phrase-only path >= 1.6x faster      RIGHT, under-predicted by half   3.35x
  P2a distinct token ratio <= 15 %         RIGHT                            5.79
  P2b top-5 token share >= 10 %            WRONG, and NOT falsified         6.07  (falsifier was < 5)
  P4  tokenisation <= 25 %                 RIGHT                            9.82
  --  catalog lookup smallest, <= 10 %     FALSIFIED  13.88, SECOND LARGEST
  --  >= 60 % of call sites phrase-only    FALSIFIED  0.00 % inside src/acronymkit
```

**One mechanism change after pre-registration, declared rather than buried.** The pre-registration
said cost-centre shares would come from `cProfile` `tottime` attributed by a function-to-centre
table. That was replaced with **staged ablation** before anything ran, because attributing a
generated dataclass `__init__` by caller is exactly the judgement call the measurement existed to
remove. The falsifier thresholds were written against "self-time" and are adjudicated against the
ablation share, which is the same quantity measured better. **No prediction was adjusted.**

**And P2b is the interesting one, because it survived on a threshold set too loosely.** The
prediction was `>= 10` %, the measurement is `6.07` %, and the falsifier was `< 5` % — so a wrong
prediction did not fire its own falsifier. That is a defect in the pre-registration and not in the
measurement, and it is the reason this record prints the prediction, the outcome **and** the
falsifier in three separate columns.

### How it fails

**The only arm where a catalog answers is a fixture, so nothing here measures the hot path a real
governed vocabulary would produce.** No public catalog exists for Socrata or SEC XBRL — the standing
unknown this project has carried for four phases — so the `92.98` % memo-hit arm is a synthetic
corpus drawn from the fixture catalog's own token pool, and the two real-name arms have a memo hit
rate of zero because their catalog is empty. **The gap between them is twenty points of provenance
share.** A reader taking the fixture arm as "the governed case" is reading a corpus built to make the
memo look good; a reader taking the empty-catalog arms as the governed case is reading a
configuration in which half the subsystem is switched off.

**Three of the four cost centres are differences of two large, similar timings and inherit both their
noise.** Only provenance is large enough for its magnitude to survive; one round put the fixture
arm's assembly centre below zero at
-3.06<!--claim:governed_perf.fixture_schema.fixture.stage_assembly_pct_min:.2f--> %. **Take the
ordering. The magnitude of any centre but provenance is not quotable.**

**P5's near-death rests on the two real-name arms and the fixture arm disagrees with it by a factor
of two.** Tokenisation is `9.82` % on Socrata and
23.02<!--claim:governed_perf.fixture_schema.fixture.stage_tokenise_pct:.2f--> % on the fixture
schema, whose identifiers average `16.069` tokens against Socrata's `2.728`. **The automaton is dead
on schema identifiers of the length real portals publish and not obviously dead on long ones**, and
the sentence "tokenisation is `9.82` %" is a fact about one corpus being used to close a workstream.

**The caller census counts sites, not calls, and there are eleven of them in one repository.** A site
inside a loop over ten million columns weighs the same as a one-shot CLI command. It cannot speak for
strangers, and this project has zero confirmed adopters on two independent instruments.

**"Allocations" here means object constructions counted exactly — not bytes.** The gated figure is
`__post_init__` calls. `tracemalloc` was rejected with a reason (it traces live blocks, not
allocation events) rather than used and caveated, and a design that reduced records while raising
bytes would be invisible in these numbers. **Memory was not measured at all.**

**Both corpora are schema corpora and nothing here says what a prose caller's hot path looks like.**
`extract`, `disambiguate` and generation have entirely different ones. The decomposition is of
`expand_identifier` alone; `is_compliant` and `to_physical_name` are three to five times dearer per
call by the existing `governed.*` runs and no decomposition of them exists.

**And the instrument is audited by nothing but its own tests.** The parity checks compare each
ablation stage against the shipped code — byte-identical phrases over `421,199` calls per pass with
`0` mismatches, identical `resolve` and `class_word_for` counts on all four arms, three positive
controls proving each check can report non-zero. **Nothing compares this ablation design against a
differently-conceived one**, which is precisely the reproduction property
`governed_catalog.socrata.scorer_agreement` was built to give the segmentation figure.

---

## D-087 — Three CI gates come out of workflow heredocs and become invocable; one gate's in-situ evidence is **withdrawn**; and the count went **down**, from `13 of 36` to `12 of 36`. This is also the round that made a rule this register called not waivable, waivable

**Status:** shipped — `tools/gate_{schema_copies,tier_zero,import_ceiling,installed_suite,sdist_files}.py`,
`.github/gates.toml`, `.github/workflows/{ci,gate-mutation}.yml`, `tools/gates.py`,
`tests/test_gate_scripts.py`, `tests/test_gate_manifest.py`, `docs/GATES.md` ·
**Amends:** D-079's `13 of 36`, and this register's own costing of the inline gates ·
**Evidence:** `python tools/gates.py --check`; `python tools/gates.py --mutate <gate>`;
`docs/GATES.md` · **No experiment number spent — experiment eleven is still free**

D-079 moved criterion `9` from `0 of 36` to `13 of 36` by reading a CI run nobody had read, and named
three of the eight inline refusals as "one afternoon of extracting heredocs into `tools/`". This is
that afternoon. It did not go the way the costing said.

```
python tools/gates.py --check -- command output, not a benchmark measurement
  gate manifest: 36 gate(s) across 23 environment(s) in 5 workflow file(s)
  mutation kind: automated 16, control 2, inline 5, manual 13
  demonstrable by this harness: 16 of 36, 4 of them still owed
  CARRYING IN-SITU EVIDENCE:   12 of 36
  top of the cost ranking:     2 of 3 demonstrated  (1 claims, 2 splits_manifest, 3 suite)
  in-situ quota: debt 24, ceiling 24 | M3-PA (the heredoc extraction) cut -1,
                 withdrew ['suite'], owes 4 forward
```

### The count went down, and that is the round's best outcome

`gates.suite` carried a recorded in-situ demonstration. Re-checked, its harness verdict was decided
from a return code alone, and with `data/` present and the mutation applied the **only** failing test
is the probe's own side effect on the register anchor. `rc=1` was reachable with the declared defect
uncaught, in both environments. **The evidence is withdrawn.** `13 of 36` becomes `12 of 36`, the
debt rises `23` to `24`, and four gates are owed forward on a promise.

**A register that can only go up is a register nobody can correct.** The machinery that makes the
withdrawal *expressible* — `withdrawn_gates`, `owed_forward`, a debt rise permitted only when
attributed **and** waived, a withdrawn name checked against the live register, a refusal to withdraw
a gate still carrying a run id, and a check that the round after one owing evidence shows the debt
fell by that much or says why not — **is more defensible than the withdrawal itself.** A reader who
accepts the captured artifact's transcription would say the withdrawal was unnecessary. Nothing in
this repository can check that transcription, which is the actual reason it went.

### What was extracted, and the one that needed a new register field

`tools/gate_schema_copies.py`, `tools/gate_tier_zero.py` and `tools/gate_import_ceiling.py` are real
scripts now, invoked from `ci.yml`, moved in the register from `kind = "inline"` to automated with
declared edits, an artifact and a failure marker. `inline` falls `8` → `5`; automated rises `13` →
`16`.

**And the newly-invocable schema-copy gate fired on its first run against an unmutated tree.** It had
been red in this working tree the whole time and unobservable, because it was a heredoc. Repaired by
rewriting the working copy to LF, byte-identical to `HEAD`.

**Two of the three needed an environment the ambient interpreter does not provide, and only one of
those was predicted.** `tier_zero_purity` returns INERT against an interpreter with `acronymkit`
installed non-editably and DEMONSTRATED in a venv built with `pip install -e "."` and no extras.
`import_ceiling`'s job installs **non-editably**, so no source edit reaches it at all — which needed
a new `mutation.setup` field that reinstalls after the edit and again after the restore, and returns
UNRESTORED rather than a verdict when the setup fails. **Extraction alone would have left it inert in
its own environment by construction.** The register's costing said three gates, one afternoon; it was
wrong about one of the three it named.

### Two two-copy problems, one closed and one created

`EXPECTED_NON_PASSING`, `PASS_FLOOR`, the installed-suite log parser and the five `test -f` names
lived in the packaging-mutation harness **and** in the workflow. They now live once each, in
`tools/gate_installed_suite.py` and `tools/gate_sdist_files.py`; `ci.yml` runs them and the harness
imports them. Four copied objects deleted. What remains — a multi-step `run:` block no tool can
invoke from outside the workflow — is checked by `sequence_drift()`: `11` literal fragments asserted
fatally against `ci.yml` before any case runs, plus `4` declared divergences. **That replaces a guard
that printed `"WARNING:"` and continued.**

**The extraction adds its own two-copy problem and it is tested rather than hoped.** Each script's
`FAILURE_MARKER` must equal the register's `expect_failure_matching` or every future demonstration
silently becomes INERT. The new field is required on every automated `expect="fail"` mutation and a
positive control shows that pointing it at a line the gate never prints turns the verdict INERT
instead of green.

**The workstream's own count of how many carry it is wrong, and the recorder found it by parsing the
register rather than by reading the report.** The report says *"all `12` carry one"*. Parsed with
`tomllib`, `.github/gates.toml` holds `36` gates of which `16` are automated, `15` of those declare
`expect = "fail"`, and **all `15` carry an `expect_failure_matching`** — one automated mutation
declares `expect = "pass"` and correctly carries none. The mechanism is exactly as strong as claimed
and the denominator is `15`, not `12`. **This is the only figure in the four workstream reports that
this recorder checked and found wrong**, and it was not one of the four headline claims that were
checked on purpose; it was a secondary count picked up while writing the paragraph above it.

### The rule that got softer, named rather than buried

`in_situ_problems()` appended the debt-ROSE problem and then `continue`d, so the waiver
`docs/GATES.md` advertises — *"a round that adds an automated gate it could not run in CI in the same
commit"* — **could never apply.** Driven as a counterfactual against `HEAD`'s own code with a
synthetic trajectory, the returned problem set is identical with and without the waiver.

So this round replaced a not-waivable rule with one that yields to an attribution **plus** a waiver.
An unattributed rise is still refused and still tested. **But this is the round that made a hard rule
softer, and that is the shape people regret.** It is written down here at that strength so a later
round can hold it to the escape rather than to the intention.

### The pre-registration against its outcome

```
pre-registration vs outcome -- scratchpad/PREREGISTRATION.md, written at HEAD 387f739
  B1  all three extract and demonstrate    HALF WRONG, and wrong about WHICH one was fragile:
                                           import_ceiling was fragile for a different reason
                                           (non-editable install), and tier_zero_purity, not
                                           flagged at all, came back INERT for the same class
  B2  count stays 13 of 36, debt 23        WRONG -- 12 of 36, debt 24. It moved DOWN
  B3a 6-9 of 13 have a changed dependency  RIGHT   8 of 13, inside the band, and --check prints it
  B3b re-running contradicts 0 of the 13   RIGHT ON ITS LETTER, WRONG ON ITS SPIRIT: none was inert
                                           on its declared defect; one had a verdict that could not
                                           go red, which is worse than the defect being looked for
  B3c retiring evidence is impossible      RIGHT, and the phase's most consequential prediction
  B4  the sequence cannot be invoked;      RIGHT, exactly as split
      expect a SPLIT outcome
  B5  the 5 remaining inline are not the   RIGHT, and understated -- it was also wrong about one
      same afternoon's work                of the three it named
```

### How it fails

**No in-situ evidence was taken. Everything here is local, and a local demonstration is exactly what
R11 says is not evidence.** The three new gates carry a developer-machine demonstration and nothing
else. `owed_forward = 4` is a mechanism for making the next round check that a push happened; it is
not a payment.

**Every extraction number was taken on a developer machine and one had to be taken twice to be
right.** `tier_zero_purity` flipped INERT → DEMONSTRATED on install mode alone. Any of the three
could differ on a runner for a reason nobody has thought of.

**The sequence half of the packaging drift is checked, not closed.** Eleven literal fragments catch a
rename or a flag change. They cannot catch a reordering, an added step, or a `run:` block that means
something different with the same words in it. **And the packaging harness has still never produced a
green run on a runner** — the coverage figures still rest on a `2026-08-24` Windows measurement, and
this round did not run it at all.

**`gates.suite`'s confound is not removed.** It needs a probe that does not edit the file the register
anchors on, and the defect lives in that file. `rc=1` there stays over-determined.

**Two new `gate-mutation.yml` jobs carry a `no_gates_reason` rather than a gate**, because
`--assert-environment` checks path globs and their premise — *no optional dependency installed* — is a
property of the interpreter. That hole is registered, not closed. So is
`gates.tier_zero_purity`'s inability to distinguish *the package leaked click* from *the runner has
click installed*.

**And the concurrency contaminated the measurements.** At least two other workstreams were writing
this tree throughout; two runs of the same suite an hour apart gave different skip counts, one test
failed once on a probe file another agent's mutation created, and the claims gate was red for one run
on a record-file pin this workstream does not own.

---

## D-088 — **Both R15 decompositions are retired in the same commit, for the same reason**, and the round that retired the second one was handed the first as a premise that had already been measured not to replicate. `20.8` % reappeared in a different cell

**Status:** shipped — `docs/CLAIMS-LEDGER.md` §6, `docs/AUDIT-PROHIBITIONS-2026-08.md` (three sites),
`CHANGELOG.md`, `tools/prohibitions.py` · **This is a methodological correction, not a cleanup** ·
**Amends:** D-068's kind-of-check decomposition (`7.7` % against `36.4` %, ratio `4.7×`) and its
failure-mode decomposition (`3` of `5` staleness); D-082's carry-forward of the second one ·
**Evidence:** `docs/CLAIMS-LEDGER.md` §6 and its census command; the third R15 round at seed
`20260827` · **No experiment number spent — experiment eleven is still free**

**This project has three times retired somebody else's most-quoted statistic for being under-checked.
This is the round it did it to its own.**

### What is retired, and what is kept

**Retired:** the kind-of-check decomposition — *claims settled by one lookup fail at `7.7` %, claims
needing a derivation fail at `36.4` %, a `4.7×` ratio*. **Retired with it:** the failure-mode
decomposition — *`3` of `5` failures are staleness*.

**Kept:** the headline rate. Three rounds now read `20.8` %, `20.8` % and `25.0` % not-true.

The retirement is **in place** at every site, with the reason attached — not deleted, so nobody
re-derives it, and not caveated, so nobody keeps quoting it.

### Three points, and neither decomposition has a direction

```
the two decompositions, round over round
  kind of check     D-068  7.7 vs 36.4   4.70x
                    D-082  ratio                     0.75x   (reversed)
                    round three  25.0 vs 25.0        1.00x   (dead flat, equal denominators)
  failure mode      D-068  staleness 3 of 5
                    D-082  staleness 1 of 5
                    round three  staleness 1 of 6
```

The third round wrote its retirement bar down **before** grading — three or more failures concentrated
in one arm with the others at zero, denominators of at least eight each — which is the gap D-082
identified in the previous sampler. It is nowhere near it. `1.00×` on equal denominators is the
cleanest possible non-result.

### The premise the third round was handed had already been refuted by the record it cited

The sampler's brief instructed it to report the failure-mode split on the stated ground that it *"did
survive"*, citing *"last round `3` of `5` failures were staleness"*. **Last round is D-082.** D-082
says staleness was `1` of `5`, and its own title reads *"The dominant failure mode moved from
staleness to an unmeasured premise stated as a measurement"*. The `3`-of-`5` figure is D-068, one
round earlier.

**So a decomposition that had already been measured not to replicate was passed forward as the one
that had — which is the exact defect class that accounts for `4` of the round's `6` failures.** Had
the sampler followed its brief without opening D-082, it would have published a third round of a dead
decomposition and the round after would have inherited it with two rounds of apparent support. **The
sampler is not outside the failure class it measures**, and that sentence is the most valuable thing
this round produced.

### `20.8` % reappeared in a different cell, and quoting it would be quoting the wrong row

Round three is `6` of `24` **not-true** = `25.0` %, and `5` of `24` **strictly false** = `20.8` %.
Anybody who reads "`20.8` % again" off this round is reading the false-only row against two prior
rounds' not-true rows. **That is the third distinct way this figure has presented itself**, and it is
the clearest available argument that it is a draw from a distribution rather than a property.

Sensitivity, with the boundary written down before grading rather than reconstructed after: moving one
verdict in either direction gives `20.8` %–`29.2` %, about `±4` points on one grader's boundary. D-082
measured `±8`. **Every between-round difference so far is smaller than the within-round grader
uncertainty.** Three rounds sit inside each other's error bars.

The honest reading after three rounds: **this project's reporting fails somewhere in the low-to-mid
twenties per cent, and no round has been powered to say more than that.** What three rounds bought is
one number with a wide interval and two retired hypotheses, and **the retirement is worth more than
the number.**

### The census, its command, and the two near misses that would have been miscorrected

```
git grep -n "36\.4" -- "*.md" "*.py" ":!docs/DECISIONS.md" ":!build/*"
  before this round   4 lines in 3 files
  after this round    7 lines in 4 files, none of which is a claim
```

Four **sites** in three files, not three copies: `docs/AUDIT-PROHIBITIONS-2026-08.md` carries it in
three places — including the opening clause that chose that page's whole frame, and a `D-068's rate`
comparator column struck from its section-3 table — plus `CHANGELOG.md`'s D-068 note and
`tools/prohibitions.py`'s module docstring. **The fourth site carries no `36.4` at all and was found
by reading, not by the command.** The registering workstream predicted three copies; its own
instrument would have missed one of them.

**And the census would have miscorrected two sentences that were right.**
`docs/AUDIT-PROHIBITIONS-2026-08.md:94` and `tools/prohibitions.py:104` each carry a `7.7` that is the
sensitivity of a stratum to one further failure — **not** D-068's single-lookup rate. A value-match
sweep would have "corrected" both. That near miss is published beside the census, because it is the
honest limit of the instrument.

### What a third revival would need, stated so it is a decision rather than a re-derivation

Four conditions, in `docs/CLAIMS-LEDGER.md` §6: a boundary written before the draw; a pre-registered
or stratified mix (the two rounds moved `13`/`11` to `8`/`16` and nobody chose that); enough failures
for a cell to mean anything; and a second grader. **Condition three is the only one that cannot be
satisfied inside a single round** — with five or six failures a single reclassification moves a cell
by six to twenty points — and it is the load-bearing sentence of the leave-behind rather than a
footnote.

### How it fails

**A two-point rule was applied to kill a two-point finding, and that objection is correct.** Two
rounds disagreeing is evidence that this instrument cannot see a relationship, not that none exists.
The word shipped is *retired*, not *refuted*, and the four conditions are written so a third round can
revive it.

**The retirement is prose and the only thing enforcing it matches on a literal.** The claims gate
cannot read a sentence. The census matches `36.4`; a paraphrase — *about a third*, *five times more
likely*, *the derivation-heavy half* — walks straight past it, and so does any restatement in a file
the pathspec excludes. **A fifth copy stated without the number would still be in the tree and nobody
would know.** The fourth site was found by reading, which is the instrument this project distrusts.

**The prohibitions page still splits on the same axis and is marked as not a replication rather than
re-argued.** Its `3.2` % against `52.0` % looks like a third observation and is not: a different
population, a **census** rather than a seeded sample, and a three-valued grading scale
(`TRUE`/`FALSE`/`UNREPRODUCIBLE`) that both R15 rounds recorded `0` of. A stricter reader would want
that page's whole frame re-argued; that is a re-audit, not an edit.

**Nobody re-derived the census independently.** One reader, one grep, one manual read. R15's own
framing is that the sampler's verdicts are claims too, and **the error rate of the error-rate
measurement is unmeasured for a third round running.**

**And the round that retired the decomposition mis-transcribed one command's output twice inside five
minutes**, in the section that retires a statistic for being under-checked. Both wrong drafts are left
visible in the shipped page with the corrected `-c` output beside them, which is the only defensible
thing to do with them.

---

## D-089 — The retired breadth pitch is gone from the package's front door, and the reason it survived three reports is that **no second-reader trigger can reach a source file at all.** The recorder then found the retired sentence still importable on this machine

**Status:** shipped — `src/acronymkit/__init__.py` docstring, `docs/SECOND-READER.md` §5.3/§7/§8/§9,
`docs/DEFINITION-OF-DONE.md` criterion `14` · **Amends:** `docs/POSITIONING.md`'s *"Retired here, and
still shipping in one place this workstream did not own"* and D-070's *"The retirement is incomplete
in a file the gate scans"*, both of which are now false of the tree and neither of which was that
workstream's to edit · **Evidence:** `python tools/second_reader.py --check` and `--trigger`;
`git log -S` on the retired tagline; the probe below ·
**No experiment number spent — experiment eleven is still free**

D-070 retired three breadth sentences. One kept shipping in `src/acronymkit/__init__.py`'s module
docstring — the first prose a reader meets in an editor — and it was reported **three** times, not
twice: `docs/POSITIONING.md`, D-070's own *How it fails*, and `docs/cold-reads.toml`'s
`F-2026-08-25-01`. All three named the same disposition and none of them fixed it.

### The answer is structural, and it is not an attribution

**No trigger in the second-reader policy can reach a source file.**

```
python tools/second_reader.py -- command output, not a benchmark measurement
  PATHSPEC                                    6 entries, none under src/
  user_facing_files()                         21 paths, 0 under src/
  is_user_facing("src/acronymkit/__init__.py")  False
  --check                                     rotation: 21 file(s)
  find src/acronymkit -name '*.py' | wc -l    40      -> admitting it takes the rotation 21 -> 61
```

Demonstrated in situ rather than argued, in the tree that rewrote the file:

```
git status --porcelain             ->   M src/acronymkit/__init__.py   (among others)
python tools/second_reader.py --trigger
                                   ->   4 user-facing file(s) changed
                                        CHANGELOG.md, docs/CLAIMS-LEDGER.md,
                                        docs/DEFINITION-OF-DONE.md, docs/EVALUATION.md
                                        -- and NOT the source file it just changed
```

So both reports that *did* reach it arrived by check C5 — following a pointer out of
`docs/POSITIONING.md` — and neither round fixed it because `owner` read `unowned`. **The docstring's
survival was not an oversight by anybody; it was a coverage hole wearing an ownership problem's
clothes.**

**The file is unowned in the strongest sense.** `git log --oneline -- src/acronymkit/__init__.py`
returns `6` commits in a `53`-commit history, newest `12` commits ago; `git log -S "bi-directional,
multi-tiered acronym engine"` on that path returns the **initial commit only**. The retired tagline
was written on day one and never edited. The registering workstream predicted the opposite — that the
file was touched every round for its lazy-export table, which would have made the finding *owned by a
mechanism rather than by a reader* — and that prediction was wrong, which is what turned the finding
into a coverage argument instead of an ownership one.

**And the claims gate was never watching it.** `SCAN_GLOBS` does include `src/acronymkit/*.py` and
`src/acronymkit/**/*.py`, and `iter_claim_numbers` finds **zero** claim-shaped numbers in that file
before the rewrite and after. `docs/POSITIONING.md`'s *"That file is scanned by the claims gate"* is
true and load-bears nothing.

### What the docstring says now

It leads with governance. The governed doctest shows the **refusal** as well as the answer —
`is_fully_known` → `False`, `unknown_tokens` → `['KYC']` — and says plainly that the default
`UnknownPolicy` still returns `'Transaction Kyc Identifier'` at `is_known=False`, confidence `0.0`,
so a caller reading only `phrase` gets a governed-looking string for a token no catalog approved.
Generation, backronym, extraction and disambiguation are kept and demoted honestly, with extraction
named as beaten by two compiled systems and both empty headline rows named beside the command that
prints them. The lazy export table, `_EXPORT_ALIASES`, `__all__` and the `TYPE_CHECKING` block were
not touched.

### The recorder's own check found the sentence still importable on this machine

Verifying the retirement produced a **false FALSE verdict** and then the reason for it. The probe
below is the recorder's, run after the rewrite landed:

```
python -- session transcript, not a benchmark measurement. CPython 3.13.4 on win32.
ambient interpreter, cwd = the repo root:
  import acronymkit  ->  ~\AppData\Roaming\Python\Python313\site-packages\acronymkit\__init__.py
  'bi-directional' in acronymkit.__doc__       ->  True
  >>> examples in acronymkit.__doc__           ->  9
same interpreter, src/ first on sys.path:
  import acronymkit  ->  ~\Documents\GitHub\acronymkit\src\acronymkit\__init__.py
  'bi-directional' in acronymkit.__doc__       ->  False
  >>> examples in acronymkit.__doc__           ->  11
```

**`acronymkit` is installed non-editably on this machine, so `import acronymkit` at the repo root
still returns the retired breadth pitch.** Compared file by file, the installed copy and the working
tree differ in **exactly one** of `40` modules — `__init__.py`, the file this round rewrote — and the
other `39` are byte-identical modulo line endings. The suite is safe: `tests/conftest.py` inserts
`src` at `sys.path[0]`, and both new bench runners insert it too. **What is not safe is any hand-run
`python -c "import acronymkit"`, any `help(acronymkit)`, and the first thing a developer on this
machine sees.**

That is the same class as D-087's `tier_zero_purity` INERT verdict and it was found the same way — by
running the thing rather than reading it. It is a property of the machine, not of the code, so
**nothing in this repository can gate it**, and this record is the only place it exists. It also means
the workstream's own claim of `9` → `11` doctest examples is true of the tree and false of the
interpreter, and a reader checking it the obvious way gets the wrong answer.

### The pre-registration against its outcome

```
pre-registration vs outcome -- scratchpad/prereg-mandate3-phaseA.md
  P1  more than one copy outside DECISIONS  RIGHT, and UNDER-COUNTED: 4 sites in 3 files,
                                            one of them invisible to the census
  P2  unowned: (a) no commit in the         RIGHT on (a) and (b). WRONG on (c) in the direction
      reporting rounds (b) no brief          that matters: reported THREE times, not twice
      assigns it (c) reported twice
  P3  the file IS touched every round for   WRONG -- 6 commits in 53, none in 12. THIS IS THE ONE
      the export table                       THAT CHANGED THE FINDING from ownership to coverage
  P4  no gate moves on these edits          RIGHT on the ratchets (0 armed numbers added or removed,
                                            measured line-number-independently), WRONG on "all seven
                                            stay green" -- and the reason was five other workstreams
  P5  the headline rate is separable        RIGHT, and the flagged risk was the real one
  P6  a third round is statable             RIGHT; one correction -- power is the ONLY condition not
                                            satisfiable inside a round, not the second
```

### How it fails

**The ownership half is measured and the assignment half rests on the record's word.** *No trigger
reaches `src/`* is measured and demonstrated in situ. *No workstream was assigned it* rests on D-070
and `cold-reads.toml` saying so, plus a `git log` showing zero touches in twelve commits. **Absence of
a touch is not proof of absence of an assignment**, and there is no artifact in this tree recording
what any round assigned to whom — which is itself the finding, and is also why the finding cannot be
checked.

**`docs/cold-reads.toml` is now wrong about the tree and the gate is green about it.**
`F-2026-08-25-01` still reads `blocked`, with a `blocked_on` that says in its own words *"It is not
blocked on knowing what to write."* The blocker is gone and the edit is made. Closing it needs a
`disposition = "fixed"` with an `applied_by` that is not the reader, and that file was not the
applying workstream's to write. `--check` stays green because the decay clock runs on `open` findings
only. **The mechanism built to stop findings rotting silently has a disposition it does not clock**,
and this round is standing in it.

**The docstring that is now the package's front door is unexecuted by CI.** Its `11` doctests pass by
hand. Nothing under `tests/` runs them — doctest runners exist in four test modules covering
seventeen `acronymkit` modules, and neither `acronymkit` itself nor `acronymkit.generator` (which
carries `9` uncovered examples of its own) is among them. **A five-line test module alongside the four
that already exist would close it**, and `tests/` was not that workstream's.

**The coverage hole is reported and not fixed.** Widening `user_facing_files()` to
`src/acronymkit/**/*.py` reddens `--check` until all `40` modules are in the rotation block, taking it
`21` → `61` and roughly tripling trigger B's latency. A special case for `__init__.py` alone is the
rule-free exception §3 of that page refuses for CI jobs. That is a scope decision for whoever owns the
policy.

**And `docs/SECOND-READER.md` was wrong about its own rotation count for the third time of asking** —
§8 said *"entry four of the fifteen"* and §9 said *"the rotation set is twenty files"* about a set of
`21`. Corrected, with the count derived from `--check` rather than remembered.

---

## D-090 — The definition of done, sixth sweep: **six criteria added, five of them not met, and the met-count rose by one while the proportion fell.** One criterion reads *met* on a measurement that came back negative, and one has zero live instances to be not-started about

**Status:** shipped — `docs/DEFINITION-OF-DONE.md`, criteria `15` to `20` added, criteria `9`, `13`
and `14` corrected inside unchanged verdicts · **Amends:** that page's *"the fourteen criteria"*
throughout, and criterion `9`'s `13 of 36` · **Evidence:** `docs/DEFINITION-OF-DONE.md`; the commands
printed in each new section · **No experiment number spent — experiment eleven is still free**

Mandate III adds six criteria. **Five of the six read *not met*, and four of those five read *not
started*.** They are recorded at that status rather than omitted, because a criterion list that only
lists what is in progress hides the distance.

```
docs/DEFINITION-OF-DONE.md -- the sixth sweep's own arithmetic
  fifth sweep   10 of 14 met    71 %
  sixth sweep   11 of 20 met    55 %
  the six new:  15 not met/not started   16 MET   17 partly met
                18 not met/not started   19 not met/not started
                20 half met, and the half that matters is not
```

**The count rose by one and the proportion fell by sixteen points.** That page's own *How this
document fails* has said since the fourth sweep that *"a definition of done whose met-count rises when
six new criteria arrive is scoped by the same people it grades"*, and offered no answer. **This is the
first sweep where the answer is a number**, and it is stated at the head rather than left to be
computed by a reader who thinks to.

### The two rows worth arguing about

**Criterion `16` reads *met* and the thing it measured came back negative.** The round trip was
measured as a verifier and it cannot verify —
42.09<!--claim:roundtrip.med1250.recall.beam_control_never_cuts.recall_pct:.2f--> % against an aligner
at 85.70<!--claim:roundtrip.med1250.ceiling.aligner_accepts_pct:.2f--> % — and the criterion asks for
*measured, with a go/no-go recorded*, which is exactly what happened. **A criterion that closes on a
measurement regardless of which way the measurement went is a criterion about diligence, not about
the library**, and the page now carries five of those out of eleven. That is written into the verdict
rather than into a footnote.

**Criterion `15` has nothing to be not-started about, and saying so is more informative than saying
*not started*.** `find` over the tree returns `0` image files of any kind. R16 — *a figure inside an
image is an unchecked claim* — is a pre-commitment with no instance, so nothing demonstrates it can
fire, which is the objection criterion `9` makes about CI jobs arriving here about a rule.

### What moved inside the fourteen without a verdict moving

- **Criterion `9`'s count went down for the first time**: `13 of 36` to `12 of 36`, debt `23` to `24`,
  because one gate's in-situ evidence was re-checked and withdrawn. `inline` fell `8` → `5` and
  automated rose `13` → `16` in the same round, so the register got better and the count got worse.
  D-087.
- **Criterion `13`'s predicted waiver did not arrive for a second consecutive round.** `54` → `42`,
  `3` citations and `9` deletions. D-091.
- **Criterion `14` acquired a mechanism where it had only had an attribution**: `PATHSPEC` has `6`
  entries with none under `src/`, `user_facing_files()` returns `21` paths with `0` under `src/`, and
  in situ the trigger names four files and not the source file the round had just changed. D-089.
- **Eleven of twenty verdicts were re-derived and nine carried**, which is up as a count and down as a
  proportion: every one of the six new criteria was re-derived by running the command in its own row,
  and **not one of the five that have been carried since the third sweep** — `1`, `2`, `5`, `6`, `7` —
  was touched. **The number that has been going up is the number of criteria nobody had a verdict on
  yet.**

### The gate armed an ordinal, and it took three code spans to stop it

`throughput` is one of the claims gate's eleven arming keywords. Criterion `17` is *a gated
throughput baseline in machine-independent counts*, so its own index — a bare `17` — shares a line
with the keyword in the table row, the section heading and the blockquote. On the first run after
the section was written the gate read all three as throughput claims of seventeen and put them on
the **closed** value-matched ledger: `3 value-matched claim(s), baseline 0`.

**This is the citation-arms-neighbour class from the other side.** D-071 routed around it by
choosing field names with no arming keyword; D-084 could not, and deleted the neighbour instead,
publishing a second workaround and calling the defect unfixed. **This is the third published
workaround and the first where the arming word is not in a citation at all** — it is in the
criterion's own title, and the number it armed is an index rather than a measurement. Silencing an
ordinal is correct rather than evasive, and the reason is written on the page beside the code spans,
because a code span with no explanation is what D-052 says is indistinguishable from hiding.

### How it fails

**Five of twenty verdicts are still carried from an earlier sweep** — `1`, `2`, `5`, `6` and `7` —
and they have now been carried for four sweeps running. **The ones still being re-derived are the ones
that keep moving, and a verdict that never moves is exactly the verdict a stale reading hides in.**

**The six new criteria were written by the mandate that graded itself against them, and five of them
came back not met in the same document.** That is the direction that makes the addition credible and
it is not a defence: a mandate that writes its own bar and misses it has still written its own bar.
The one that reads *met* is the one whose bar is *measured*.

**Criterion `20`'s verdict is the sharpest thing on the page and it is not this project's to fix.**
The catalog-gap report ships with an owner, three dated actions and a `2026-11-23` expiry, and its own
log reads **approaches made: `0`**. `U-0` has been open across four phases. Shipping the report is the
part this repository controls; it is also the part that settles nothing.

**And this sweep was taken on a tree several workstreams were writing to**, which is the confound the
page has recorded against every sweep since the second. Every command in the new sections is printed
so it can be re-derived; none of them was re-derived by a second reader.

---

## D-091 — The waiver D-084 forecast did not arrive either. `12` more out of `docs/DECISIONS.md`, `3` by citation and `9` by deletion, **no waiver** — and *blocked* was a per-record verdict for a **fourth** time, this time for a reason that can never be discharged

**Status:** shipped — `docs/DECISIONS.md`, `tools/check_claims.py`'s three ledger constants ·
**Amends:** D-084's forecast that *"the next bound round will need a waiver"* and its per-record
verdict on D-013 (*"a before/after table cannot have one live column and one frozen one"*);
`DEFERRED_BASELINE`, `LEDGER_TRAJECTORY` and `RECORD_FILE_PIN` · **Evidence:**
`python tools/check_claims.py`; `python tools/check_claims.py --residue`; the diff of
`docs/DECISIONS.md` · **No experiment number spent — experiment eleven is still free**

Seven records were added to this file — D-085 through D-091 — so the pin went red before a word of
migration was written. That is the binding working for the third round running.

```
python tools/check_claims.py -- command output, run by the recorder while adding these records
  docs/DECISIONS.md now holds 91 record(s); RECORD_FILE_PIN says 84.
    Adding a record IS a round. Append a LedgerRound that migrates at least
    12 number(s) out of docs/DECISIONS.md -- or that records a waiver
    saying why it could not -- and re-take the pin in the same commit.
  rc=1
```

### The payment

```
docs/DECISIONS.md, 54 -> 42.  Three citations, nine deletions, NO fencing.
  CITED -- the whole "after" column of D-013's before/after table
    D-013  2.3    micro.import.cold_import_ms
    D-013  128.1  micro.import.cold_import_engine_ms
    D-013  196.0  micro.import.cold_first_result_ms
  DELETED -- arithmetic over two numbers the reader still has (D-084's clause one)
    D-023  21.6   = 30.09 / 139.60, both in the same table
    D-023  63.0   = 87.96 / 139.60, both in the same table
    D-023  15.4   = 21.55 / 139.60, both in the same table
    D-023  22.4   = (347.60 - 269.80) / 347.60, both on the line
    D-023  29.4   = (422.80 - 298.70) / 422.80, both on the line
    D-023  1.6    = (412.60 - 406.20) / 406.20, both on the line
  DELETED -- verbatim restatement inside the same record, the original kept (clause FOUR, new)
    D-023  56.80  restates the same figure six lines up
    D-048  16.59  restates the same figure one line up, in a sentence that disclaims it
    D-013  3.6    restates the same figure twelve lines up
```

`python tools/check_claims.py --render --dry-run` reports **"up to date, nothing would change"**, so
all three citations render byte-identically to the text already on the page.

**A fourth deletion clause was added and is stated so a later round can hold this one to it.** D-084's
rule permits deleting a number that is arithmetic over two numbers the reader still has, or a notional
bound, or a figure the sentence itself calls unquotable. The extension: **a number that is a verbatim
restatement of a figure elsewhere in the same record, where the original stays.** That is strictly
weaker than clause one — a restatement asks the reader to do nothing at all, where clause one asks
them to divide — so it is implied *a fortiori* rather than smuggled. It is named as an extension
because a rule that grows without being named is not a rule.

### "Blocked" was a per-record verdict for a fourth time, and this instance is the worst

D-084 counted D-013's residue as blocked because *"a before/after table cannot have one live column
and one frozen one"*. `micro.import` holds exactly three fields —
`cold_import_ms`, `cold_import_engine_ms`, `cold_first_result_ms` — and they are exactly the three
cells of that table's **after** column. All three are now cited.

**The reason given can never be discharged, which is what separates this instance from the previous
three.** The *before* column describes a version of the code that no longer exists: eager re-exports,
removed by the very decision D-013 records. **No runner can ever regenerate it.** So *one live column
beside one frozen one* is not a hazard that citation creates; it is the table's permanent nature, and
the verdict treated a permanent property as a reason not to check the half that is checkable. D-071
found this shape, D-084 found it twice more and called it a pattern rather than an anecdote. This is
the fourth, and the first where the stated reason had no route to ever becoming false.

**And there is a mechanism argument on top of the pattern.** D-051 records that the three import
figures *"are one entry"* — the only way to re-record the flattering one is to re-record all three —
and that they are quoted as a triple in five places no runner regenerates, D-013's table among them.
**One of those five now regenerates**, so a `--save` that moved them turns this file red instead of
staling it silently.

### The verdict was not merely too wide. The record it was applied to already carried a live citation to the same field

```
git grep -n "micro.import.cold_import_engine_ms" -- docs/DECISIONS.md
  -- command output, not a benchmark measurement; run BEFORE this round's migration
  :8954  D-023   "...against the 128.1 ms in `bench/results.json`..."
  :9948  D-013   "...measures what the remaining 128.1 ms is made of..."
```

**D-013's own prose already cited `micro.import.cold_import_engine_ms`, seventeen lines below the
table cell that was called blocked**, and D-023 cited it too. So the round that ruled the table's
after column uncitable was reading a record that already contained a live figure from exactly that
field. The three citations added here did not make anything live that was not already live; they
finished a job the record had started and nobody had noticed. **A per-record verdict is written by
looking at a record and this one was written without grepping it.**

### R11: what the gate can and cannot see on the seven records added here

Nine mutations, one at a time, each restored from bytes read before it and md5-verified, with a
tenth run of `python tools/check_claims.py` as the unmutated control and an eleventh after the
restore. **Eight fire red and name the file; one is a measured zero.** A and B
mutate a citation this round created in D-013; C mutates one of the `roundtrip.*` citations D-085
created; D and E are prose inserted into D-085; F puts back one of this round's nine deletions; G, H
and I mutate `tools/check_claims.py`'s three ledger constants. Line numbers are the mutated file's and
move with any edit above them; `rc` and *is the file named* do not.

```
python tools/check_claims.py -- command output, not a benchmark measurement
  rc=0  control, unmutated                                       <file not named>
  rc=1  A  a migrated citation's value edited 128.1 -> 128.2     docs/DECISIONS.md:9932
  rc=1  B  that citation repointed at run id micro.nope.engine   docs/DECISIONS.md:9932
  rc=1  C  a roundtrip citation edited 42.09 -> 42.10            docs/DECISIONS.md:28
  rc=1  D  prose added: "... accuracy reached 99.94 % ..."       docs/DECISIONS.md:20
  rc=0  E  prose added: "Median latency ... 41 microseconds"     <file not named>
  rc=1  F  one of the nine deletions put back (a bare "21.6 %")  deferred 43, baseline 42
  rc=1  G  the pin left at the previous round's record count     91 record(s); pin says 84
  rc=1  H  from_record_file dropped from 12 to 11                "against a floor of 12"
  rc=1  I  by_deletion dropped 9 -> 8                            "fell by 12, accounts for 11"
  restored, both files md5 identical                    rc=0     <file not named>
```

**C is the one that matters most**, because `roundtrip.*` had never been cited by any document before
this round: nineteen run ids sat in `bench/results.json` with nothing pointing at them, and a
measurement nobody cites is the failure mode `docs/GATES.md` opens with. **F is what makes nine
deletions a ratchet rather than a claim** — putting one back is a red build. **G, H and I are the
binding checking itself**, red in situ rather than in a fixture.

**E's green is a measured zero and it is the fifth time this hole has been measured rather than
carried.** `latency` is not in the arming vocabulary and a spelled-out `microseconds` is not in the
unit vocabulary. D-060 found it in `README.md`, `docs/POSITIONING.md` found it in itself, D-071 and
D-084 each found it here, and D-079 found a live instance on the front page. **It is now a hole with
five measurements and no fix**, and the sixth measurement of a hole is worth less than the first
attempt to close it.

### What is left, counted per record rather than estimated

```
python tools/check_claims.py -- per-record count of the deferred residue, after this round
  D-023  29   no runner saves pydantic import attribution; docs/notes/pydantic-cost.md
              holds the measurements and no bench runner writes any of them
  D-048   5   figures the record itself labels un-gated, from a workstream report
  D-013   5   the before column, plus pyab3p's import cost -- a third party's figure
  D-051   1   a CI threshold quoted as the NAME of a code comment
  D-026   1   a rounded "about 44 %" the record says leaves no row behind
  D-007   1   a perturbation-range endpoint whose twin sentence lives in README.md
```

**This block's first draft was wrong, in the exact way D-084's was.** It read `27` / `6` / `5`, and it
had been written by subtracting the round's migrations from remembered per-record totals rather than
by re-counting against the file's own record boundaries. **The subtraction was right and the totals it
was applied to were not.** It was caught by re-deriving the breakdown before publishing, which is the
check D-084 installed after committing the identical error, and it is left recorded here because a
recorder who publishes a measured error rate and then does arithmetic from memory in the same commit
has learned nothing from either.

### Three numbers were walked and **refused**, with the reason, because a refusal with no reason is a backlog

- **D-023's title, `84.6` %.** It *is* arithmetic over numbers the reader still has —
  `(30.09 + 87.96) / 139.60` — and it is deletable under clause one. It has **five twins outside this
  file**: four in `docs/notes/pydantic-cost.md`, one in `src/acronymkit/governed/models.py`, and a
  sixth as a test fixture in `tools/check_claims.py`. Editing one copy and not the others is the
  defect this project has now hit six times, and it would additionally retitle a record. **Refused for
  the twin, not for the arithmetic.**
- **D-026's `44`.** *"the `novel` arm, where nothing repeats, lost about `44` %"*, in a sentence whose
  next clause says the figure is not in `bench/results.json` and cannot be. That is clause three
  exactly. **Removing the number requires rewriting the sentence**, and the rule licenses deleting a
  number, not rewording a closed record. Refused on the surgery.
- **D-007's `100` and D-048's `31`.** Both are the upper endpoint of a range — `50–100 %`, `22–31 %` —
  where the lower endpoint carries no unit and is therefore invisible to the gate. Deleting the
  endpoint alone leaves `50–%`. **The gate's residue is one-sided about ranges**, which is a defect in
  the arming rule and not a property of these sentences.

### The ledger's sixth observation

```
python tools/check_claims.py -- the record file's own ledger, by round
  before the binding             115
  M2-P4 (the recorder is bound)   84    -31
  M2-P5 (the recorder pays)       66    -18
  M2-P6 (the walk)                54    -12
  M3-PA (the second walk)         42    -12
```

`73` of `115` in four bound rounds against a floor of `12`. **The rate stopped falling and sat on the
floor for a second consecutive round**, which is a different shape from the deceleration the previous
three rounds described: two rounds at exactly `12` is what a floor looks like when it becomes the
target, and the next round should be read with that in mind.

### The recorder's own pre-registration against its outcome

```
pre-registration vs outcome -- scratchpad/PREREG-recorder-M3PA.md, written before the walk
  P1  the waiver is not needed; split      RIGHT on both halves: 12 paid, no waiver,
      0-3 citations and 9-12 deletions      3 citations and 9 deletions
  P2  the pin reds first; only the claims  RIGHT -- ruff, mypy, splits and gates stayed green on
      gate reds on my own diff              this diff; the pin was the only thing that moved
  P3  my new records add ZERO deferred     RIGHT -- the fall is exactly 12, so nothing was armed
      numbers                               on the way in
  P4  exactly one of four verified claims  WRONG -- ZERO of four failed, and the near-miss is the
      will be wrong                         finding: the recorder's own probe imported the wrong
                                            copy of the package and nearly published a false FALSE
  P5  at least two of criteria 15-20 are   HALF -- exactly two are (16 met, 17 partly), which is
      partly met; 15 is vacuous             the bottom of the predicted band; 15 is vacuous as
                                            predicted, at 0 image files
  P6  the go/no-go is a STOP, A1 survives  RIGHT on all three, including that U3 would not report
      under a framing nobody commissioned,
      and U3 will not have reported
```

> **`P6`'s THIRD CLAUSE IS REGRADED, `2026-08-26`: RIGHT ABOUT A REPORT, WRONG ABOUT A
> MEASUREMENT.** U3's report never reached this recorder and U3's *work* was in the tree the whole
> time — `18` run ids under `one_sense.*`, saved before this record was written. The prediction was
> scored against the arrival of a document and read as a statement about whether a measurement
> existed, which are two different propositions that this phase's reporting failure made look like
> one. **Scored honestly the row is a HALF, and the totals in the six-workstream table below are
> therefore one `RIGHT` too generous to the recorder** — the table is left as published, because a
> scorecard silently re-scored after the fact is worth nothing. D-092 carries U3's measurement;
> D-095 carries the failure that made this misgrading possible.

**P4 is the one to read.** The prediction was a base rate — three R15 rounds put not-true between
`20.8` % and `25.0` %, so four claims is one expected failure — and the four headline claims came back
clean while **the first claim checked outside the plan came back wrong** (D-087's `12`, which is `15`).
Two readings compete and this round gives the first one some support: workstreams hold their own
*headline* figures to a higher standard than the incidental counts R15 samples, or four is simply too
few to see a one-in-four rate. **Nothing here separates them cleanly**, and the honest statement is
that a four-item check is a coin flip with a hypothesis attached — which is why the fifth item, chosen
by accident, is worth more than the four chosen on purpose.

### What the recorder verified against running code, and what it carried on trust

One load-bearing claim per workstream, re-derived rather than read off the workstream's own artifact.

```
verification -- command output, not a benchmark measurement. CPython 3.13.4 on win32.
  A1   re-ran bench/run_roundtrip_verifier.py --corpus med1250 --no-verification-arm
       unpruned_ceiling_pct 42.09, misses_architectural 442 (39.75 % of corpus),
       max_points_an_oracle_bound_could_recover_at_shipped_defaults 0.18   REPRODUCED
       and the brief's beam=4 observation re-driven from scratch through Config/Tokenizer/
       ForwardGenerator/Scorer on the same phrase:
         nodes= 50000 beam=      4  candidates=2809  evaluated=6411  truncated=False
         nodes= 50000 beam=1000000  candidates=2809  evaluated=6411  truncated=False
         nodes=  6410 beam=      4  candidates=   3  evaluated=  65  truncated=True
         nodes=  6410 beam=1000000  candidates=2809  evaluated=6410  truncated=True
       the 3-against-2809 collapse is real and it needs the node budget cut first   REPRODUCED
  P1   re-ran bench/run_governed_perf.py --only census
       155,272 identifiers 44.88 % distinct; 423,544 token occurrences 5.79 % distinct   REPRODUCED
       and the "larger than the other three put together" claim recomputed on all four arms:
       70.15 > 30.13, 73.55 > 26.43, 67.56 > 31.84, 49.85 > 43.14                        HOLDS
  D4   ran tools/gates.py --check, tools/gate_schema_copies.py, tools/gate_tier_zero.py
       12 of 36, debt 24 at ceiling 24, withdrew ['suite'], owes 4 forward; both
       extracted scripts exit 0 against the clean tree                                   REPRODUCED
  D5   the retired tagline is absent from src/acronymkit/__init__.py and the docstring
       carries 11 doctest examples, 0 failing                                            REPRODUCED
       -- but only once src/ is on sys.path; see D-089
  D4   AND, outside the plan: the report's "all 12 carry one" is 15 when .github/gates.toml
       is parsed with tomllib -- 36 gates, 16 automated, 15 declaring expect="fail", all 15
       carrying expect_failure_matching                                              WRONG, corrected
  R15  git log -S "include .github/gates.toml" -- MANIFEST.in returns 387f739 only, and
       the line is absent at a62f99a: the sampler's FALSE verdict on D4's commit
       attribution is correct                                                            REPRODUCED
       grep -c doctest tests/test_generator.py = 0 and generator carries 9 examples:
       the sampler's FALSE verdict on D5's doctest enumeration is correct                REPRODUCED
```

**Zero of the four workstream headlines failed to re-derive**, against a pre-registered expectation of
exactly one. **The fifth claim did.** D-087's *"all `12` carry one"*, about how many automated
mutations declare an `expect_failure_matching`, is `15` when the register is parsed with `tomllib` —
`36` gates, `16` automated, `15` declaring `expect = "fail"`, all `15` carrying the field. It was
picked up incidentally while writing that record's paragraph, not by the verification plan. **So the
base rate arrived on the first claim outside the plan**, which is a sharper reading of R15's three
rounds than the plan produced: a workstream's headline is the figure it re-ran three times, and its
secondary counts are the ones nobody re-ran at all. **And the near-miss is the other finding.** The `D5` check was first run with the ambient
interpreter and came back FALSE — `bi-directional` present, `9` examples not `11` — and the recorder
was one keystroke from publishing a false FALSE verdict. The cause is in D-089: `acronymkit` is
installed non-editably on this machine and `import acronymkit` at the repo root returns a copy of
`__init__.py` that predates the rewrite. **A verification that imports the wrong artifact is a
verification of nothing**, and nothing in the harness would have said so.

**Carried on trust, named rather than left implicit:** every mutation transcript in D-087 (the gate
harness was not re-driven); every wall-clock figure in D-086; `roundtrip.pmc_oa.*` in full (only
MED1250 was re-run); the extractor-proposal precision figures in D-085 (the runner was re-run without
`--save` and those arms were not separately audited); the four-site census in D-088; and every
statement any workstream makes about what it did rather than about what the tree contains. **The
`beam=4` probe is the one thing in D-085 the recorder re-derived from primitives rather than from the
workstream's runner**, and it is also the only claim in this phase that contradicted the brief that
commissioned it, which is why it was the one worth re-driving.

### Six pre-registrations, scored together, because the pattern is worth more than any of them

Every workstream in this phase wrote a falsifier down before measuring. Five did it because the phase
brief made them; the sampler did it because the previous round's record said it was the gap. **Scored
together for the first time**, one row per numbered item as each workstream's own scorecard reported
it:

```
pre-registration, all six, this phase.  A "half" is a prediction right in direction and wrong
in magnitude, or right on its letter and wrong on its spirit -- each workstream's own grading.

  workstream                items   right   half   wrong    the finding that mattered was...
  A1  round-trip verifier       8       4      1       3    NOT pre-registered (the filter framing)
  P1  cost model                7       4      0       3    NOT pre-registered (the memo's eviction
                                                            ceiling; the caller premise WAS, and was
                                                            falsified at 0 % against a 40 % floor)
  D4  gate debt                 7       4      2       1    NOT the defect looked for (a verdict that
                                                            could not go red, not one that was inert)
  D5  R15 retirement            6       3      2       1    ARRIVED BY A FALSIFIER FIRING (P3 wrong ->
                                                            the finding changed from ownership to
                                                            second-reader coverage)
  R15 sampler, round 3          8       4      1       3    NOT pre-registered (its own brief's
                                                            premise was refuted by the record it cited)
  --  the recorder              6       4      1       1    NOT pre-registered (the retired sentence is
                                                            still importable on this machine)
  TOTAL                        42      23      7      12
```

**Direction mostly right, magnitude mostly wrong, and in six of six the most valuable finding was
not on the list.** That is now three rounds of the same shape — D-082 and D-084 each recorded it for
one workstream, this is the first phase in which every workstream produced it independently. **The
value of a pre-registration here has not been that it predicts; it is that it makes the surprise
legible.** Two of the twelve wrong predictions fired a kill condition their own author had written
(`A1`'s ceiling, `P1`'s caller premise), and one wrong prediction changed what its round was about.

**Two counting caveats, because this table is itself a claim.** Each workstream graded its own
scorecard and the recorder counted the rows rather than re-adjudicating them, so a workstream that
graded generously is counted generously. And `P1`'s `P2b` is the clearest instance of a prediction
that was wrong and did not fire its own falsifier — predicted `>= 10` %, measured `6.07` %, falsifier
set at `< 5` % — so `12` wrong is a floor on how many bets missed and not a count of how many were
caught missing.

### How it fails

**The pin is a deterrent where it is not a mechanism, unchanged.** A recorder who adds records may
bump the pin's count and leave its label naming the round that is already newest; the floor passes,
because that round's migrations satisfied it once. The defence is that it is a visible source edit in
a file the gate reads.

**The recorder edited `tools/check_claims.py` again**, and that file is not on this phase's list of
files this workstream owns. Three data constants — the per-file baseline, the trajectory row and the
pin — with no behaviour change. **A round that edits its own scorer says so in the record rather than
in the diff**, and the alternative is a red build with no route to green.

**Deletion outnumbers citation three to one for a second consecutive round.** A cited number can be
wrong and be caught; a deleted number cannot be wrong and cannot be checked, because it is not there.
**A future round reading `-12` twice without reading the split would be reading progress that is
three-quarters subtraction, twice.**

**Rule 6 counts records and is blind to everything else a record can hold.** These seven records add
several thousand words and a great many code-spanned numbers to this file, and only the seven `## D-`
headings cost anything. Every code span in them is invisible to the gate by construction, which D-052
says is mechanically indistinguishable from hiding.

**One of the three citations makes a permanently frozen column sit beside a live one.** That is the
objection D-071 raised and this record overrules, on the ground that the frozen column can never
become live and the choice was therefore between checking half the table and checking none of it. **A
reader who prefers none of it is reading D-071 correctly and disagreeing with this round on a
judgement, not on a fact.**

**And every gate reading in this record is a snapshot of a tree five workstreams were writing to.**
The suite was green at `5,406` collected with `0` failures when this round started and again after the
migrations; the claims gate went red exactly once, on this round's own ratchet, and green on the
constant. Nothing about that was independently re-derived.

**The recorder moved a working-tree count another workstream had published, by editing files.**
`git ls-files --eol` read `58` w/crlf when this round opened, `61` after the record edits landed —
Python's `write_text` translates `
` to `

` on Windows — and `57` after the four edited files were
normalised back to LF, which is what `.gitattributes` mandates and what git stores either way.
**That figure has now taken five values inside two rounds**: `66` when D-087's workstream published
it, `57` when the sampler re-measured it forty minutes later and graded the `66` stale, `58` when this
recorder took it, `61` mid-edit, and `57` again at close. `tools/check_claims.py` is one of the four
and was CRLF before this round touched it, so the recorder normalised a file it does not own — a
whitespace change git discards on read, recorded here rather than left in the diff. **A count over a
shared working tree is not a claim a stranger can check**, and this is the third round in which that
sentence has had to be written about the same command.

---

## D-074 — The one measurement that pointed against the governance lead measured a catalog's **cost**, not its **worth**. The decomposition that reverses the reading also prices the win at `1.22` points, and that price is not on the positioning page

**Status:** shipped — `bench/run_governed_catalog.py`, `8` new run ids, `docs/EVALUATION.md`,
`docs/POSITIONING.md` reversal one rewritten · **Amends:** `docs/AUDIT-2026-08.md` §1's *reading* of
its own pooled comparison — the comparison reproduces, the conclusion drawn from it does not — the
audit's `87.3 %` and `78.9 %`, and `docs/POSITIONING.md`'s *How this fails*, which no longer says the
evidence and the conclusion point in opposite directions · **Evidence:**
`governed_catalog.socrata.{census,scorer_agreement,voted.fold_ab,voted.fold_ba,eager.fold_ab,eager.fold_ba,sweep,null_control}`;
`bench/run_governed_catalog.py`; `tests/test_governed_catalog.py`; `docs/EVALUATION.md` ·
**No experiment number spent — experiment eleven is still free**

**This is the record that governs the phase.** D-070 committed the library to being a governance
instrument. A governance instrument's product *is* the governed subsystem's numbers, and every
published governed number is taken with an **empty** catalog — so the flagship figures measure where
an identifier is cut and say nothing about what a governed vocabulary is worth. The only measurement
anybody had of whether a catalog is worth anything on a real schema was the audit's, and it had the
empty catalog winning. **The positioning was committed to a claim with one measurement, and the
measurement went the wrong way.**

Pooled, it still does. **It was never a measurement of the thing it was read as measuring**, and that
is now derived rather than argued.

### First, two premises corrected before anything is built on them

**The figures the commissioning brief quoted — `98.03` and `93.37` — are audit-era**, from
`docs/AUDIT-2026-08.md` lines `197`-`198`, on `2,999` and `17,210` aligned pairs. The current gated
Socrata figure is 91.37<!--claim:governed_gold.socrata.columns.all.exact_pct:.2f--> % on
26,536<!--claim:governed_catalog.socrata.scorer_agreement.admitted_pairs:,--> pairs. **The exposure
survives the correction unchanged**: the gated figures are still empty-catalog cut-placement figures,
and correcting them changes the size of a number and not one word of the argument.

**And the audit's own `87.3 %` does not reproduce on anything in this tree.** Two workstreams
re-derived it independently this round and both landed near
79.9<!--claim:governed_catalog.socrata.census.unabbreviated_occurrences_pct:.1f--> % of occurrences,
with 76.53<!--claim:governed_catalog.socrata.census.unabbreviated_pairs_pct:.2f--> % of *distinct*
pairs already unabbreviated. The audit's population was never saved, so nobody can say whether it
fetched a different slice or applied the rule differently. The direction survives; the figure does
not.

### The pooled result reproduces, and the loss is structurally confined

Under a portal-disjoint split of real Socrata schemas, scored through `expand_identifier`, a voted
catalog is worse than an empty one in
79<!--claim:governed_catalog.socrata.sweep.cells_where_voted_loses_pooled:,--> of
80<!--claim:governed_catalog.socrata.sweep.cells_run:,--> configurations. The single exception is the
one cell whose catalog has **no acting rows at all** — the empty arm under another name.

Then the split nobody had made:

- 76.53<!--claim:governed_catalog.socrata.census.unabbreviated_pairs_pct:.2f--> % of distinct pairs are
  **already unabbreviated** — the caption re-cuts the identifier and nothing else. On those a catalog
  can only do damage.
- 11.31<!--claim:governed_catalog.socrata.census.live_pairs_pct:.2f--> % carry an expansion at all.
  That is the only place the question is live.
- The whole of the pooled loss lands in the first bucket. The audit-shaped catalog broke
  97<!--claim:governed_catalog.socrata.voted.fold_ab.identical.empty_only_correct:,--> and
  283<!--claim:governed_catalog.socrata.voted.fold_ba.identical.empty_only_correct:,-->
  already-correct pairs across the two folds and fixed
  0<!--claim:governed_catalog.socrata.voted.fold_ab.identical.voted_only_correct:,--> and
  0<!--claim:governed_catalog.socrata.voted.fold_ba.identical.voted_only_correct:,-->.

**That confinement is a derivation and not four observations.** The empty arm's output carries the
identifier's own alphanumerics, re-checked live for this record:

```
python -- session transcript, not a benchmark measurement
>>> from acronymkit.governed import expand_identifier, GovernedDictionary
>>> expand_identifier("acct_bal_amt", GovernedDictionary({})).expanded
'Acct Bal Amt'
```

So the empty arm can be exactly right only where the caption is the identifier re-cut. It is
therefore right zero times on every non-identical subset, for every catalog in the grid, and the
pooled figure is a damage figure by construction. **The audit measured a catalog's cost and the
record read it as a catalog's worth.**

### The number this round is most at risk of being read as saying more than it does

On the live subset a catalog **cannot lose** — the empty arm is at zero there by construction — so
"the voted catalog loses
0<!--claim:governed_catalog.socrata.sweep.cells_where_voted_loses_live:,--> times" is arithmetic and
not evidence. The readable figure is that it *wins* in
51<!--claim:governed_catalog.socrata.sweep.cells_where_voted_beats_empty_live:,--> of
80<!--claim:governed_catalog.socrata.sweep.cells_run:,--> cells and recovers nothing at all in the
other 29<!--claim:governed_catalog.socrata.sweep.cells_where_voted_ties_live:,-->.

**"Wins in 51 of 80" is a phrasing tighter than the measurement unless the margin sits beside it, and
the margin is small.** The third cold read raised exactly this and nothing had applied it. This record
promotes it from a note to a headline qualification:

> The best cell in the entire eighty-cell grid recovers
> 40<!--claim:governed_catalog.socrata.eager.fold_ab.live.voted_exact:,--> of
> 3,276<!--claim:governed_catalog.socrata.eager.fold_ab.live.pairs:,--> live pairs —
> 1.22<!--claim:governed_catalog.socrata.eager.fold_ab.live.delta_points:.2f--> points — while costing
> -17.79<!--claim:governed_catalog.socrata.eager.fold_ab.all.delta_points:.2f--> points on the pooled
> figure.

The token metric and the pair metric differ by an order of magnitude, and the page carried a magnitude
for only one of them. **A reader who takes "wins in 51 of 80" as meaningfully positive is reading the
sentence as written and not the measurement.**

### Where a catalog is worth something, and how thin that evidence is

On the token positions where the identifier's token differs from the caption's word —
1,100<!--claim:governed_catalog.socrata.census.abbreviated_tokens:,--> of them across the corpus — the
empty catalog is right zero times, again by derivation. The best catalog inferable from the corpus
itself is right
12.35<!--claim:governed_catalog.socrata.eager.fold_ab.abbreviated_tokens.voted_correct_pct:.2f--> % on
486<!--claim:governed_catalog.socrata.eager.fold_ab.abbreviated_tokens.tokens:,--> atoms in one fold
and
9.22<!--claim:governed_catalog.socrata.eager.fold_ba.abbreviated_tokens.voted_correct_pct:.2f--> % on
618<!--claim:governed_catalog.socrata.eager.fold_ba.abbreviated_tokens.tokens:,--> in the other. Two
folds, two catalogs, two populations, never pooled: `12.35` against `9.22` **is** the honest width of
this measurement, and it has exactly two points in it.

### The segmentation figure is now checkable by something other than its own runner

`governed_catalog.socrata.scorer_agreement` re-scores every admitted pair under a second,
independently written metric.
26,536<!--claim:governed_catalog.socrata.scorer_agreement.verdicts_agreeing:,--> of
26,536<!--claim:governed_catalog.socrata.scorer_agreement.admitted_pairs:,--> verdicts agree and both
metrics report
91.37<!--claim:governed_catalog.socrata.scorer_agreement.word_tuple_exact_pct:.2f--> %, reproducing
`governed_gold.socrata.columns.all.exact_pct` to the digit. That is the first time a flagship governed
figure has been reproduced by anything but the runner that wrote it.

### Two workstreams counted the same cached corpus differently, and neither noticed

Re-derived by the recorder rather than carried. `docs/SOURCING.md` publishes `155,272` occurrences and
`124,055` identical over the cached Socrata fetch; `governed_catalog.socrata.census` records `155,261`
and `124,046` over the same file.

```
python -- command output, not a benchmark measurement, run by the recorder for this record
  loose rule (non-blank field and caption)                      155272
  tight rule (both also have a non-empty alphanumeric key)      155261
  occurrences the tight rule drops                                  11
  of those, counted IDENTICAL by the loose rule                      9
  examples dropped:  ('_', '%')   ('_', '_')   ('_', '% ')
```

Both figures are right under their own admission rule and both round to `79.9`, so nothing published
is wrong. What is wrong is that **nine pairs one workstream counts as "already unabbreviated" have an
empty alphanumeric key on both sides** — a string equality between two nothings. The runner that
refuses them is right, and the disagreement was invisible because the rounded percentage agreed.

R15's sample found the same class independently and larger: the two workstreams' word rules split on
`[^0-9a-z]+` against `str.isalnum()`, and they disagree on the exact-match verdict for `1,244` of
`78,374` distinct pairs. **That verdict is what assigns a pair to *identical* or to *live*, which is
the split this whole record rests on.** Reported, not reconciled; neither runner is the recorder's
file, and the reconciliation is a measurement rather than a rename.

### What this does to the commitment

**It removes the evidence pointing against the lead and supplies none for it.** That is weaker than a
defender of the positioning would want and it is the true statement. The adversary's reason for
refusing to assert the original figure as a result stands and now cuts both ways: Socrata display
labels are a noisy gold, `':@computed_region_92fq_4b7q'` is captioned `'City Council Districts 2'`,
and 82.86<!--claim:governed_catalog.socrata.census.token_word_count_mismatch_pct:.2f--> % of
non-identical pairs have a token count that does not match the caption's word count.

### How it fails

**The gold on the live subset is materially worse than on the segmentation table.** There the
admission rule guaranteed the two strings were the same characters. Here nothing guarantees a caption
is an expansion of its identifier rather than a different name for the same column. The expansion
bucket is a character-subsequence test — necessary, not sufficient — and only about a hundredth of the
corpus reaches the strict bucket where token alignment is well defined, which is why the token figures
rest on `486` and `618` atoms.

**Every catalog scored is inferred by the harness from labels of the very kind being scored.** The
portal-disjoint split moves that circularity from the pair to the corpus and does not remove it. So
`12.35` % is a floor on what a real glossary could do and not an estimate of one.

**The corpus's own contamination declaration is now false and was not amended.** `bench/splits.toml`
declares `socrata` `contaminated = false` on the stated ground that "the runner has no thresholds, no
configuration and no arms to choose between". This round quotes a maximum over an eighty-cell grid on
that corpus, and every saved entry carries `selection_on_this_corpus = true`. Whether
`governed_gold.socrata.*` is still held-out evidence is open. **Disposition: blocked on ownership of
`bench/splits.toml`** — reported in `docs/EVALUATION.md` and in every saved entry, and it is the
sharpest unresolved consequence of this round.

**Nothing here transfers.** The corpus is `snake_lower` and `flat_lower`; nothing is said about
`UPPER_SNAKE`. One corpus, one portal ecosystem, public display labels. **And the positioning's
central question is about a proprietary glossary nobody has handed over** — see D-078, which puts a
date on that rather than closing it.

---

## D-075 — The genre half of the monoculture confound is separated on `1,839` same-article PMC pairs, six ways, all six excluding zero — and the sentence saying it could not be separated was stale in four documents at once

**Status:** shipped — `bench/run_genre.py`, `50` new run ids, `bench/splits.toml`,
`tools/fetch_data.py`, `data/LICENSES.md`, `docs/EVALUATION.md` · **Amends:** D-065's confound
paragraph, which was too strong as written; `docs/EVALUATION.md`'s sentence that separating the two
"would need a corpus of article body text annotated by pooling Schwartz & Hearst systems — which
nobody has published"; `docs/AUDIT-2026-08.md`'s reserved PMC decision, taken here one day after its
deadline took it by default · **Evidence:** `genre.pmc_oa.*` in `bench/results.json`;
`bench/run_genre.py`; `tests/test_genre.py`; `bench/splits.toml`
`[corpora.pmc_oa_same_article_genre]` · **No experiment number spent — experiment eleven is still
free**

D-065 measured the extraction monoculture and then published the confound that stops its strong
reading: the cross-corpus ordering — MED1250 abstracts against PLOD body text — is equally consistent
with *the corpora were drawn around the pool* and with *abstracts do not contain the hard cases*.
**Half of that is now measured, and it is the genre half.**

### The instrument, which holds provenance constant by construction

`2,000` pinned PMC Open Access articles, `1,839` of them carrying both halves. Each article
contributes its own `<abstract>` and its own `<body>`, so provenance, domain, author, journal and
deposit route are constant **within** every unit of comparison and only genre varies. The gold is each
article's own `<def-list>` abbreviation roster from `<back>` — in neither measured half — admitted by
a rule that compares no character of a term against its definition. The proposer pool is
`bench/run_monoculture.py`'s, unchanged; no Schwartz & Hearst descendant was added.

Six paired cluster-bootstrap contrasts over articles. All six exclude zero and all six point the way
the genre account predicts:

- bracket-adjacency of located gold long forms:
  84.54<!--claim:genre.pmc_oa.contrast.abstract_minus_body.bracket_adjacency_of_located_gold_long_forms.left_pct:.2f--> %
  in abstracts against
  75.85<!--claim:genre.pmc_oa.contrast.abstract_minus_body.bracket_adjacency_of_located_gold_long_forms.right_pct:.2f--> %
  in bodies —
  8.69<!--claim:genre.pmc_oa.contrast.abstract_minus_body.bracket_adjacency_of_located_gold_long_forms.difference_pct:.2f--> points,
  interval
  3.29<!--claim:genre.pmc_oa.contrast.abstract_minus_body.bracket_adjacency_of_located_gold_long_forms.difference_ci_low_pct:.2f-->
  to
  13.85<!--claim:genre.pmc_oa.contrast.abstract_minus_body.bracket_adjacency_of_located_gold_long_forms.difference_ci_high_pct:.2f-->.
- Schwartz & Hearst family reach:
  87.11<!--claim:genre.pmc_oa.contrast.abstract_minus_body.sh_family_recall_of_located_gold_long_forms.left_pct:.2f--> %
  against
  80.92<!--claim:genre.pmc_oa.contrast.abstract_minus_body.sh_family_recall_of_located_gold_long_forms.right_pct:.2f--> %.
- the independent proposer's union gain, which reads **no gold at all**:
  0.82<!--claim:genre.pmc_oa.contrast.abstract_minus_body.independent_gain_on_proposal_edges.left_pct:.2f--> %
  against
  9.55<!--claim:genre.pmc_oa.contrast.abstract_minus_body.independent_gain_on_proposal_edges.right_pct:.2f--> %.

**Verdict: genre.** The cross-corpus ordering no longer requires the provenance explanation, so the
monoculture's strong reading stays dead — but it stays dead rather than being refuted, because nothing
here measures the provenance main effect.

### Three adversaries the design had to survive, all measured rather than argued

**"Bodies simply have fewer parentheses."** They are bracket-*richer* than their own abstracts —
`412.4` open brackets per `100,000` characters against `301.9`, `408.0` against `301.9` after
deducting `2,596` punctuation-only citation-sweep brackets — and their definitions are nonetheless
less often beside one.

**"Bodies are twenty times longer."** A `body_matched` arm cuts a contiguous body window to the
abstract's own length at a seeded offset. On the proposal row the difference moves *further* from
zero, `-12.51` against `-8.73`. Length is not manufacturing the effect.

**The runner's own `body_matched` arm, on the gold rows.** A window holding a pair's two strings
without holding its definition site locates a non-definitional co-occurrence, which is almost never
beside a bracket. It is published as a robustness arm for the proposal rows and explicitly
**disqualified** for the gold rows, in the record that carries it.

**And the tempting arithmetic was refused.** Every same-article difference is smaller than the
MED1250-to-PLOD difference it is offered against, and the two were not subtracted: different passage
units (one article here, one sentence in PLOD), different corpora, different annotation conventions,
and PLOD's gold carries a published error rate.

### Firing counts, because the instrument's value is that it fired

`shapecue` — the proposer that reads no bracket — fired `32` times across `2,974,657` characters of
abstract and `5,694` across `59,486,201` characters of body: `1.08` against `9.57` per `100,000`
characters, at identical provenance. Located gold pairs: `388` in abstracts, `1,892` in bodies. Of
`1,839` articles, `220` ship a roster at all, declaring `2,696` pairs. Bootstrap: `2,000` replicates
requested and `2,000` used in every one of the six comparisons, seed `31337`. Mutation battery on the
new tests: `9` mutations, `9` red, restored and digest-verified against a pristine copy held outside
the repository; a tenth attempt came back **inert** and was replaced rather than counted.

### Two facts about PMC that fell out of it

**The bulk mirror the audit reserved a decision about is gone.** `docs/AUDIT-2026-08.md` said to take
that decision deliberately and log it rather than let a deadline take it by default. Nobody did. On
`2026-08-25` `ftp.ncbi.nlm.nih.gov/pub/pmc/` holds two files and a readme; every bulk path the audit
probed returns `404`, including the `deprecated/` mirror the audit recorded as up. **The decision is
now taken and logged: mirror `2,000` articles through the Cloud Service for one contrast, not `5.27`
M for a held-out corpus that was never achievable** — PMC ships no adjudicated abbreviation benchmark,
and a corpus this project builds and adjudicates is `single_annotator_reference` by rule.

**The Open Access Subset is not uniformly permissive.** Measured on the runner's own `5,376`-probe
draw, `26.96` % of licence-carrying articles are not permissively licensed, including exactly one
CC BY-ND — the trap the audit flagged, live. Read from terms at a URL on a date and recorded in
`data/LICENSES.md` and `bench/splits.toml`.

### The correction the cold read caught, and why it is the more useful half of this record

`docs/POSITIONING.md`, `README.md` and this project's own definition of done all still carried the
sentence that genre and provenance "cannot be separated" and are "equally consistent" — **in the same
round, and in one case in the same commit, as the measurement that falsifies half of it.** Four
documents describing one thing, three of them older than the mechanism. The direction matters and it
is worth being exact: the genre result *weakens* the provenance story, which is the story
`docs/POSITIONING.md` already declines to lean on, so the positioning's conclusion is unaffected.
**What was wrong is a statement of fact about what can be measured** — a stranger was being told a
question is unanswerable on public data, in the tree where half of it had just been answered.

`docs/DEFINITION-OF-DONE.md`'s two copies are corrected in this round (D-083). `docs/POSITIONING.md`
and `README.md` are **reported, not fixed: blocked on ownership**, and they are the round's largest
outstanding cross-copy divergence.

### How it fails

**The gold arm rests on `220` articles, not `1,839`, and on `157` of them for the abstract side.** The
bracket-adjacency interval is `10.55` points wide on a difference of `8.69`. It excludes zero and that
is all it does; a reader who quotes `8.69` as *the* genre effect is quoting the midpoint of a wide
interval.

**The roster is not a recall corpus in either direction.** Authors declare the abbreviations they
choose to declare. The design survives that only because both halves are scored against the same
declarations, so the selection bias is identical on both sides and cancels in the *difference*. No
absolute number off it is a recall claim about anything.

**Only the genre main effect is measured.** Genre being a *sufficient* cause of the ordering does not
make provenance a non-cause; it removes the need to invoke it. Reversal three in
`docs/POSITIONING.md` is unchanged and still needs a corpus nobody publishes.

**It is biomedical against biomedical, which is one domain again**, and the sampling frame is uniform
over PMC identifier integers, which is a stated frame and not a representative one — it lands on both
halves equally, so it does not touch the contrast and it touches every absolute number.

**One figure in the published section is a convention rather than a measurement and the gate cannot
tell.** The confidence level is written in words, because writing it as a percentage arms the claims
gate and the deferred ledger may not grow. The section says so in the sentence itself. That is a hole
in the gate reproduced in the open rather than exploited quietly — and it is the same hole D-060
found, now in a fourth document.

---

## D-076 — "Roughly eighteen points" is the **net** of two effects with opposite signs. The annotation convention alone is `26.66` and reverses the ranking by itself

**Status:** shipped — `docs/EVALUATION.md`, `README.md`, `4` new derived run ids, `CHANGELOG.md` ·
**Amends:** D-066's compressed sentence *"the sixteen points were never a statement about either
system — they were the corpus's annotation convention"*, which is the **strong** reading of a figure
this record shows is a net; and D-066's pairing-control sentence, which had a numerator and no
denominator · **Evidence:**
`shortform_contest.plod.{all,test}.convention`, `shortform_contest.plod.{all,test}.pairing_denominator`;
`docs/EVALUATION.md`; `README.md` · **No experiment number spent — experiment eleven is still free**

D-066 recorded that this library's `16`-point deficit against a one-line all-caps rule on PLOD-CW
dissolves and reverses once the gold is restricted to comparable definitions. The reversal shipped.
**What had never been computed anywhere in the tree is what the annotation convention is actually
worth**, and the number everybody was carrying — "roughly eighteen" — is the wrong subtraction.

### The 2x2, and why the obvious repair is also wrong

The four-region margin is a 2x2 whose two axes are **not the same kind of thing**. The `definitional`
axis is an annotation convention: PLOD labels every occurrence, D-041 forbids an unpaired short form.
The `caps` axis is not a convention at all — it is `predict_all_caps`'s own admission rule turned into
a gold filter, a property of the baseline.

```
bench/results.json, shortform_contest.plod.all.convention -- re-derivation command stored in the record
  margin, all gold                 -16.06        margin, definitional gold        +10.60
  margin, caps gold                -23.40        margin, definitional+caps        + 2.10

  convention effect at all gold      +26.66   <- reverses the sign on its own
  convention effect at caps gold     +25.50
  admission-rule effect at all gold   -7.34
  admission-rule effect at defnl gold -8.50
  interaction                         -1.16
  corner to corner                   +18.16
```

`18.16` is the corner-to-corner swing. **The convention axis alone is `26.66` and reverses the sign
by itself**; netting it against the `-8.50` the admission rule costs inside definitional gold is what
leaves `18.16`. And the obvious repair — adding the two headline effects — gives `19.32`, not
`18.16`; the `1.16`-point gap is the interaction, which is why the record stores four conditional
effects rather than two main ones.

**"About eighteen" is also a value two different quantities share.** `allcaps`'s own F1 rises `17.94`
across the same two rows, within `0.22` of the corner-to-corner figure and a different measurement
entirely. This library's rises `36.10`. `36.10 - 17.94 = 18.16`, which is how one number comes to
look like three.

### The pairing control now has a denominator, and it is weaker than the sentence that quoted it

D-066 shipped `pairs_mispaired: 1054` with nothing to divide it by, and the round summary that
carried it said "mis-pairing three quarters of PLOD's gold". Under the same zip-order pairing the
control uses, PLOD-CW pooled holds `1,778` replayed pairs and `1,054` are wrong — **`59.28` %, three
in five, not three in four.** The three-quarters figure is on the same run and is the wrong end of it:
`1,009` of `1,351` documents — `74.69` % — carry at most one long form, so the rotation could not
touch them. On the test split the control is weaker again: `61` of `149` pairs, `83.66` % of documents
untouched.

**The null result is unchanged. The strength of the evidence for it is smaller than the sentence
said**, and that is the correction.

### What was actually missing, and it was not the reversal

The brief that commissioned this work said the reversal was unpublished. It was not: commit
`3173126` shipped the full 2x2 into `docs/EVALUATION.md`, D-066 records it, and criterion `12` of the
definition of done already read *met*. **Three things were genuinely absent** and are what this round
is: the convention delta, which had never been computed anywhere; the join between this result and the
monoculture section; and **any PLOD span figure at all on `README.md`**, which carried zero.

The join is stated with its own limit in the same paragraph: the monoculture section measures what the
field's extractors can *see*; this one measures what the field's corpora *count*; and neither half
licenses the other, because nothing measures that they have a common cause.

### How it fails

**The four new run ids have no runner, and that is a real weakening of operating rule 1.**
`bench/run_extraction.save_results`'s own docstring says runners are the only writers, and
`bench/run_shortform_contest.py` explicitly refuses to store derived deltas — "a delta stored beside
its operands is a third number that can go stale on its own". The records were written through
`save_results` from a script, each carrying a `command` field holding a one-liner that re-derives it,
and both one-liners were run verbatim and reproduce. **But `--save` will never regenerate them**: move
an operand and the build reddens because the document cites it, while nothing at all reddens if the
derived record drifts. The runner was right that a stored delta is a third number. It was stored
anyway, because rule 1 prefers citing to fencing, and that trade is this record's main exposure. **The
right fix — a `--convention` arm on the runner — reverses that runner's stated policy and therefore
needs a decision rather than an edit. Disposition: blocked on a named decision.**

**One corpus, in the wrong domain, and its only replication is a subset of itself.** PLOD-CW is PLOS
journal text dominated by the life sciences, and the `test` split is inside `all`, so `26.00` and
`15.27` are one corpus reported twice.

**The `definitional` region is a proxy for "definitional" and is not one.** It admits parenthetical
*mentions* nobody should extract and excludes bracket-free definitions such as the legend form. D-066
recorded this; nothing about it changed; and `26.66` inherits it entirely. **If the region is wrong,
`26.66` is wrong.**

**Every figure in the `CHANGELOG.md` block that publishes this is inside a code span**, which D-052
says is mechanically indistinguishable from hiding: change `26.66` to `99.99` there and the gate exits
zero without naming the file. The reason is that `CHANGELOG.md` carries no citations anywhere and a
live citation would silently rewrite release history on the next `--render`. That is a reason, not a
defence.

**And two files still carry the superseded phrasing.** `docs/DECISIONS.md` D-066 and
`docs/DEFINITION-OF-DONE.md` criterion `12` are amended by this record and by D-083 respectively;
`docs/notes/w11-emission-model.md` still asserts D-049's old framing including "it is not the
explanation for a ten-to-sixteen-point gap", which D-066 already flagged as the last place carrying it
and which is still there. **Disposition: blocked on ownership.**

---

## D-077 — The do-not list, audited: **nothing is lifted**, `13` of `35` of its figures are not true today or cannot be re-derived, and the reason a prohibition's figure is unreproducible is usually the prohibition itself

**Status:** measured; recommendations recorded and **not** applied · **Amends:** nothing — no
prohibition, mandate text or decision record was edited by the audit; nine stated *reasons* are named
for correction below and the decision to act on any of them is the maintainer's · **Evidence:**
`docs/AUDIT-PROHIBITIONS-2026-08.md`; `tools/prohibitions.py`; `tests/test_prohibitions.py`; seed
`20260825` · **No experiment number spent — experiment eleven is still free**

Every recorded prohibition in the tree was enumerated by published mechanical rules — `55` across
three strata, both hand edits to the denominator published — a seeded sample drawn, and `56` claims
re-derived from source rather than from the record. **Stratum A, the audit's own do-not list, was a
census of all `35` of its figures.**

```
python tools/prohibitions.py --list   -- command output, re-run for this record
  stratum A  13 prohibition(s) /  35 figures      the audit's do-not list
  stratum B  35 record(s)     / 564 figures       closed records, fenced evidence
  stratum P  35 record(s)     / 738 figures       closed records, prose
  stratum C   7 live prohibitions                 mandate and positioning
  population: 55 prohibitions across 3 strata
```

### The finding, and it is not the headline rate

**Lift: nothing.** No sampled figure overturns any prohibition's conclusion. Twice the conclusion had
three orders of magnitude of margin. **A reader looking for a reopening in this pass will not find
one, and that is the result rather than a disappointment.**

**Two prohibitions came out stronger than they were written.** The per-candidate-evidence lever was
priced against a `83.85` baseline; `balanced_trim` has since shipped, the baseline is
84.21<!--claim:extraction.med1250.acronymkit.exact_f1:.2f-->, and the whole prize is now `1.23` points
rather than `1.59`. And the PMC mirror the audit priced returns `404` at that host as of `2026-08-25`,
so the route it refused no longer exists.

**Correct the reason; the prohibition stands: nine of them.** These are a different outcome from
lifting and conflating the two is the worst available error here. In brief: "four orders of magnitude"
is three, in every reading; D-020's binding wheel-headroom constraint is stale; the audit line
describing a live defect describes a closed one; `87` public symbols has no reproducible derivation;
`1.124` % is the weakest-evidenced figure on the list and is the **entire** quantitative case for
refusing to vendor a governed catalogue; `2,474,596` "rows" is a count of distinct dictionary keys;
four external figures carry no source and no read date; the audit's own instruction to retire D-011's
`88.49` was never carried out; and one comparator is superseded by a shipped figure. **The
recommendation is recorded here; the decision to act on any of it is the maintainer's.**

### The rate, with the decomposition that matters

| stratum | n | not true | not true or unreproducible |
|---|---:|---:|---:|
| **A** — the do-not list, census | `35` | `14.3` % | **`37.1` %** |
| **B** — closed records, fenced evidence | `13` | `0.0` % | `0.0` % |
| **P** — closed records, prose | `8` | `0.0` % | `12.5` % |

| kind of check | n | either | D-068's rate |
|---|---:|---:|---:|
| settled by one lookup | `31` | `3.2` % | `7.7` % |
| needing a derivation | `25` | **`52.0` %** | `36.4` % |

**The structural reason is the useful part.** D-068 recorded `0` of `24` unchecked items; this pass
records `9` of `25` derivation-requiring figures that cannot be re-derived **at all**, and the cause
is not sloppiness. A prohibition is very often justified by a measurement taken against a resource the
project then deliberately did not acquire — Ab3P's `31` MB frequency table, a Hugging Face dataset, a
PMC sample. **The refusal to acquire the resource is the result, and it is also what makes the number
backing it permanently uncheckable by anybody standing in this checkout.** A figure about a thing you
decided not to obtain is a figure nobody can re-derive.

### Stratum C: the seven live prohibitions all stand, and two of them have no mechanism

Checked against the artefacts they constrain rather than against their own wording. All `7` stand. C4
— no re-recording `micro.import` against a foreign environment — is **unenforceable by inspection**:
nothing in `bench/results.json` records which machine any individual run used, so a foreign re-record
leaves no trace. C7 — nobody optimises the MED1250 figure again — is the one `docs/POSITIONING.md`
already admits has no mechanism, and that reproduces: no gate in the seven would redden. C5 is the
counter-example that shows the shape a mechanism takes: `EXPECTED_NON_PASSING` holds `6` node-keyed
entries and `0` file-keyed, and **the job that reads it also polices it**.

### Four attempted refutations died, three of them the auditor's own, and all four had one shape

The harness was misconfigured relative to the thing under test, and the first result agreed with the
hypothesis. A cascade claim was fed non-case-folded input to a matcher whose docstring says the inputs
are case-folded. A gold-pair count was taken over raw pairs where the record's own key deduplicates. A
firing count was taken by monkey-patching a **property** as a method, so the patch never ran and the
counter read zero. And a suspected test breakage was a concurrent process changing the tree's claim
count by one between two scans inside a single test. **All four are recorded rather than deleted**,
which is what makes the `42` surviving TRUE verdicts worth anything.

### The audit's own recommendation carries a figure this round's sampler graded FALSE

Correction 2 above states the stale wheel headroom as `190,210` B against a `596,222` B wheel. R15's
independent pass rebuilt the artefact rather than reasoning about it and got `593,682` B and `192,750`
B **under the command the correction itself names** — the published figure came from a CRLF checkout
at a `README.md` state that no longer exists. **A correction to a stale figure that is itself stale is
the exact recurrence D-020's own footnote is about**, and it happened inside the document written to
find that class. Both figures are published; neither moves any prohibition's conclusion, because the
budget is `786,432` B either way.

### How it fails

**Stratum B's `0` of `13` is a result about fenced blocks, not about closed records.** The span rule —
title, status block, fenced blocks, deliberately not prose — selects exactly the text this project
writes a run id above. It was chosen before the draw and it narrows the denominator on purpose. The
`8`-item prose probe exists because of that and `8` is too few to separate `0` % from `10` %.

**The census is `35` figures but only `10` prohibitions**, so it is not `35` independent observations:
one contributes `11` and another `8`, and three of the five FALSE verdicts are one wheel figure
restated three ways. Per prohibition the failure count is `2` of `13`. Both readings are published;
neither dominates.

**"Unreproducible" is partly a statement about this environment.** Four of the nine could in principle
be settled by fetching an external resource, and this pass did not fetch one — downloading a file is
not an action it was authorised to take. A better-resourced reader converts some of those nine into a
verdict.

**The pooled `25.0` % is not a population estimate.** The three strata were sampled at `100` %, `2.3`
% and `1.1` %; pooling deliberately over-weights the do-not list.

**The verdicts are the auditor's claims and their error rate is unmeasured.** Three attempted
refutations died to the auditor's own harness errors and are reported. Nobody re-derived the `42`
TRUE verdicts. D-068 closed on exactly this and it is still true.

**And the largest class of prohibition has no denominator at all.** Every stratum here is a population
of **recorded** refusals. A direction abandoned without a record is invisible to this method, and
nothing in this pass estimates how many there are.

---

## D-078 — The standing glossary unknown gets an owner, a checklist, a legal envelope and an expiry date; the ask is sized at `22.73` of every hundred identifiers; and reversal two has **not** fired, measured on the instrument it names

**Status:** shipped — `docs/SOURCING.md`, `tools/byoc_eval.py`, `tests/test_byoc_eval.py`. **Zero
approaches made, and that is deliberate** · **Amends:** nothing; it is the first artefact attached to
the unknown D-070 ranked first and `docs/AUDIT-2026-08.md` ranked first before it · **Evidence:**
`docs/SOURCING.md`; `tools/byoc_eval.py`; `tests/test_byoc_eval.py`; PyPI and GitHub reads dated
`2026-08-25` · **No experiment number spent — experiment eleven is still free**

D-070's first consequence is that the governance positioning requires a real proprietary glossary and
this project does not have one — **a people problem, not a code problem, and no work inside this
repository moves it.** That sentence is true and it was being used as a reason to do nothing. This
round did the part that is a code problem: it made the ask cheap to say yes to.

### The artifact that changes the ask

`tools/byoc_eval.py` is a stranger-runnable, network-free bring-your-own-catalog kit. Two arms — the
empty catalog against the caller's — over the caller's own schema, scored on the label that schema
already carries. **Report order is deliberate and is the R12 discipline in code**: the firing count
first, then the two exact figures, then McNemar exact over discordant pairs, then a circularity check
for the defect that killed the last attempt, then a closed-set verdict that separates
*catalog-never-fired-nothing-measured* from *catalog-fired-no-detectable-difference*. **R12's null
case cannot be dressed as a result by a caller who does not know to look.**

A redaction guard refuses to write a report carrying any string from the input. It is declared by
report path plus an enumerated key set, and it is the second design: the first was a character-class
pattern that contained an underscore, so `PATIENT_MRN_HASHED` passed redaction and the kit's own
leaked-value test caught it on first run. A test asserts the source names no network import at all.

### Three things that are now specified instead of gestured at

**The ask.** `13` acceptance criteria across three artifacts — glossary, schema, gold — including the
one criterion no code can check, that the gold is not derived from the glossary, which is asked for in
prose *because* it cannot be measured.

**The sample size, derived and not chosen.** At an effect of `0.70` the exact binomial test first
reaches power `0.80` at `n = 49`, then **dips below at `50` and `53`**, so the criterion is the stable
column, `54`. Re-derived independently by the recorder against a separately written implementation of
the same test and reproduced at every one of those points.

**The size of the prize.** On `69,682` distinct real Socrata identifiers only `15,842` — `22.73` of
every hundred — carry a label that expands the identifier, and on exactly that subset the empty
catalog is exactly right on `6.22` of every hundred against `64.98` over the whole population. **That
is the headroom a real glossary competes for, and it is the number a schema-owner conversation should
quote.**

### Reversal two has not fired, and that is measured on two instruments

`docs/POSITIONING.md` names the instrument for reversal two: evidence that names a person or a
repository, never a download count. Read `2026-08-25`:

```
gh api / PyPI, read 2026-08-25 -- command output, not a benchmark measurement
  PyPI non-mirror downloads 2026-08-11..08-24        223, with spikes of 34, 17 and 50
  GitHub traffic/views, same window                   38 views / 25 uniques
    2026-08-11  37 / 25      2026-08-12  1 / 1      every other day  0 / 0
  ZERO views on each of the three PyPI spike days;  only referrer github.com
  stars 0, forks 0, subscribers 0;  all 6 open items are dependabot pull requests
```

**A second instrument disagrees with the people-shaped read of the first.** The GitHub traffic
verified live by the recorder against the same endpoint on the same day, field for field. Any sourcing
from here is cold outbound.

### The date, which is the part with teeth and the part with none

`2026-11-23` is written down as the date on which failure to obtain a glossary **re-opens reversal one
rather than renewing the request**. Three dated actions start `2026-08-31`. An outreach log opens at
`0` approaches, on purpose: a plan that also executed itself would have spent the maintainer's
scarcest resource without asking.

### How it fails

**The plan has one owner, one channel and zero executions, and nothing on it has been tested against a
human being.** Section 2's "why they say yes" is five guesses about other people's incentives written
by somebody who has spoken to none of them, and no gate in this repository can read a word of it. The
kit has been run by **zero strangers**; every execution is on one machine by its author.

**`MIN_DISCORDANT_PAIRS = 54` is anti-conservative and it is the worst defect shipped.** McNemar
assumes discordant pairs are independent and columns in one schema are not — measured on the real
Socrata population, `56.99` of every hundred identifiers contain at least one of the `100` commonest
token types, verified by the recorder by re-running the page's own published script. One catalog entry
decides many identifiers together, so **the printed p-value is optimistic by an unmeasured amount**.
The clustered test that would fix it is scoped and not built. **Disposition: blocked on a decision**
about whether the kit should carry a second statistic a stranger has to interpret.

**The circularity check is a proxy defeated by paraphrase, not by intent**, and the redaction guard
protects strings rather than the information in counts — a small schema's counts are a smaller
anonymity set than they look, and nobody bounded it.

**The `2026-11-23` fallback is a promise about future behaviour with no mechanism**, the same shape
`docs/POSITIONING.md` already names as unmechanised for extraction tuning, and worse here: **the
person who must execute the reversal is the person whose decision it reverses.**

**And the sizing comes from public portal data**, which D-074 has just shown is the wrong shape for
this question. The plan's own premise is that public substitutes cannot answer it; its sizing figures
come from a public substitute.

**One action of the plan is not done because the file is not this workstream's.** A `README.md` front
door for the kit was specified and not written, so the kit currently has no discoverable entry point.
**Disposition: blocked on ownership**, and the document says so where a reader meets it.

---

## D-079 — `0 of 36` becomes `13 of 36` by reading a CI run nobody had read; the register said that workflow had never executed while the run sat in the Actions tab; and the one job that was **green** measured nothing

**Status:** shipped — `.github/gates.toml`, `tools/gates.py`, `tools/gate_packaging_mutation.py`,
`.github/workflows/gate-mutation.yml`, `tests/test_gate_manifest.py`,
`tests/test_claims_gate_coverage.py`, `docs/GATES.md` · **Amends:** D-061's register with a cost
ranking and a per-round quota; `docs/GATES.md`'s sentence *"nothing in `gate-mutation.yml` has ever
run"*, which was false when it was written · **Evidence:** run `32808357572` at commit `3173126`;
`.github/gates.toml`; `tools/gates.py --check` and `--ranking`; `docs/GATES.md` · **No experiment
number spent — experiment eleven is still free**

Criterion `9` of the definition of done had read `CARRYING IN-SITU EVIDENCE: 0 of 36` since the
register shipped. **The thirteen that now carry it were not new work.** `gate-mutation.yml` ran green
on `2026-08-25`, uploaded all five artifact bundles, and nothing in the repository had ever read it.

Verified independently by the recorder against the live API rather than carried:

```
gh run view 32808357572 -- command output, read 2026-08-25
  name "Gate mutation"  conclusion success  headSha 3173126...  createdAt 2026-08-25T04:16:51Z
  jobs: controls / lint / resources / ci-test-cell / packaging / report   -- all six "success"
  log: 13 gates DEMONSTRATED (mutated rc=1, restored rc=0), 0 INERT, 0 UNRESTORED
       packaging job:  "build/extracted tree catches 0 of 5"
                       "installed-suite catches      0 of 5"
```

**The failure mode was not a broken mechanism. It was an unread output.** Nothing in this repository
detects a scheduled workflow whose result nobody harvests, and a run that happens and is never read is
indistinguishable from a run that never happened.

Harvesting it required proving the evidence still describes the shipped gates:
`git diff 3173126 61cf933` over `.github/`, `tools/gates.py`, `bench/splits.toml`,
`tests/test_splits_manifest.py`, `src/acronymkit/resources/`, `bench/results.json` and
`docs/GATES.md` is **empty — not one byte**. R15 re-ran that command verbatim and confirmed it.

### What was built so the count cannot go up by adding gates

**A cost-if-inert ranking, as fields.** All `36` gates carry a `cost_rank` that must be a permutation
of `1..36`, derived from two declared factors, plus a required `cost_if_inert` sentence. The validator
refuses a rank set that is not a permutation and refuses any adjacent pair whose ranks invert their own
factors, so **moving a gate up costs an argument in a field rather than a nudged integer**.
`redundancy` was built as a third ordering factor, measured, and **withdrawn**: as a lexicographic
third key it ranked a resource-consistency check above the whole test suite. It is kept as a declared,
printed field and a test pins the withdrawal.

**A quota stated as a ceiling on the debt, not a floor on coverage.** `IN_SITU_TRAJECTORY` is built the
way `MIGRATION_QUOTA` is. The debt is `gates - in_situ`; it may never rise; the last row must equal the
live register; and every gate ranked at or above `3` must carry evidence. A floor on coverage is
satisfied by a round adding five gates and demonstrating none — `13 of 36` becomes `13 of 41` and the
floor is still met. **Both doors are shut and both were demonstrated red**: a thirty-seventh gate plus
a round claiming it makes the debt rise from `23` to `24`, and the check says so.

**`verified_in_situ_commit` as a required companion to the date.** A run id says a demonstration
happened; only the commit says *which* gate was demonstrated.

### Two real defects in the harness, found by reading the artifact rather than the verdict

`tools/gate_packaging_mutation.py` built with `--no-isolation` instead of the gate's own command —
the drift the register already warned about, realised. Every one of six sdist builds died on
`BackendUnavailable`, the table printed `0 of 5` twice against a void control, **and the job was
green**, because a `| tee` swallowed the script's non-zero exit under `bash -e` without `pipefail`.
Both are fixed. The `[[defect_coverage]]` table's `4 of 5` and `2 of 5` are still **not** re-derived:
the one CI attempt measured nothing and the one local attempt with the fixed build command was refused
by the script's own control.

### The claims gate's hole: measured, priced at zero, refused with a disposition, and pinned

The narrow widening — `latency` and `duration` as arming keywords, spelled-out time units — **fires
zero times on this tree.** Not one prose number in any scanned file sits within the proximity window
of those keywords, and not one is followed by a spelled-out time unit. **Zero firings means nothing
was measured about whether the widened rule is well calibrated**; what was measured is that this tree
contains no latency-shaped claim, which is a different statement. Positive controls prove the
comparison is not simply broken: arming on the word *the* moves `617` claims, and a unit rule matching
anything moves `1526`.

What the widening costs is not the ledger — no number changes arming class, so no build reddens. It is
that **six shipped files immediately state something false**, and three of them print a measured
mutation battery whose green row would invert. **Refused this round, with the measurement shipped and
pinned by a test plus its own positive control. Disposition: blocked on ownership of six documents**,
and if a later round writes a latency figure into a scanned document the widening stops being free,
that test goes red, and the decision is re-taken rather than inherited.

### And the hole was found live, not staged

`README.md` was found carrying the sentence
`Median latency for a governed expansion fell to 41 microseconds in this release.` — this
repository's own test probe, leaked by two concurrent runs interleaving — and
`python tools/check_claims.py` exited **zero without naming the file**. Every gate in the repository
was green with an invented performance figure on the front page. Removed in the same round (D-084).

**And quoting that sentence in prose is what made the refusal above stop being free.** Writing it out
here, un-fenced, turned `tests/test_claims_gate_coverage.py::test_the_measured_price_of_closing_the_blind_spot_is_still_zero`
red on the first suite run of this round: the widened rule armed exactly one number the shipped rules
do not, and it was this record's own `41`. The pin fired on the round that wrote the pin down, which is
the strongest evidence available that it is a live check rather than a formality. **The sentence is now
a code span, which is a correct typography for a quoted literal and is also D-052's hazard**: the gate
is silent about it either way, and the only thing separating the two readings is that the string is
quoted as a defect rather than asserted as a figure. The price of the widening is zero on this tree
**for as long as nobody writes a latency figure into a scanned document**, and this round demonstrated
how easily that happens.

### How it fails

**`13 of 36` is not a third of the way, and the page leads with that.** All thirteen are the gates
that were always demonstrable by this harness. The other twenty-three are eight inline, thirteen
manual and two control refusals, none of which this harness can mutate. **The honest reading is "all
of the easy ones".**

**The quota can be paid by deleting checks and arithmetic cannot tell that from progress.** Removing
an undemonstrated gate lowers the debt exactly as demonstrating one does. A shrinking register now
needs a waiver naming the gate that left — a sentence somebody writes, graded by nobody. That converts
a silent repudiation into a visible one and does no more.

**The ranking is a judgement with a validator attached, not a measurement.** Nobody has counted what a
silent lexicon-consistency failure costs against a silent import-ceiling one, and no data in this
repository could settle the middle of the order.

**Five of the thirteen demonstrated gates run `tools/gates.py`, and this round edited it**, so their
evidence describes the previous revision, with no field saying so and no check that could notice. The
workflow's path trigger re-takes it on the landing commit.

**The validator rules shipped here have never run on a runner.** The eight-case battery was taken on a
developer machine, which is precisely the evidence R11 says does not count. What stands behind them is
a test module that runs inside a gate that *does* carry in-situ evidence — one level of indirection,
and not the same thing.

**And nothing was pushed.** Pushing to a public repository is modifying public content and needs the
user's explicit permission, which no agent message can supply. The consequence, stated plainly: **this
round's own validator rules have no in-situ run**, and cannot until the commit lands.

---

## D-080 — D-063's refusal is discharged as **fixed by exercising**, and the reason the code gave for keeping it was measurably wrong: two rules mask that filter, not one. And the claim class the claims gate cannot see now has a gate, which found a second live instance of itself in the same document

**Status:** shipped — `tools/check_external.py`, `tests/test_check_external.py`,
`tests/test_splits_manifest.py`, `tools/splits.py`, `bench/corpora.py`, `docs/EVALUATION.md`,
`docs/DEFINITION-OF-DONE.md` · **Amends:** D-063's stated reason for keeping the never-headline
filter; `tools/splits.py`'s docstring sentence *"the second one is not redundant"*; `bench/corpora.py`'s
`SystemExit` message · **Evidence:** `tools/check_external.py`; `tests/test_check_external.py`;
`tests/test_splits_manifest.py::test_the_never_headline_filter_fires_in_a_shipped_command_that_never_validates`;
`docs/DEFINITION-OF-DONE.md` *Standing unknowns* · **No experiment number spent — experiment eleven is
still free**

### Part one: a filter with a firing count of zero, kept, and the reason replaced

D-063 disclosed that the never-headline filter inside `headline_capable()` fires **zero times** on the
shipped manifest, because `[policy] headline_requires = "held_out"` excludes the corpus one step
earlier. **True, and not the whole reason.** `federal_register_rules_2024q1` is also
`contaminated = true`, so deleting the clause changes no output under *any* of the three values
`ROLES` admits, not just the shipped one. **D-063 named one masking rule; there are two.**

That kills the comfortable "belt and braces" answer. It does not establish deletion either, and the
two reasons that survive are now demonstrations rather than design arguments:

```
python tools/splits.py --json --path <manifest>  -- command output, not a benchmark measurement
  rc=0, headline_capable = {disambiguation: [], extraction: [],
                            identifier_segmentation: [], span_detection: []}
  ... on a manifest whose [policy] the validator refuses with 3 problems.
  --json returns from main() BEFORE validate() is ever called.
```

A shipped command reaches `headline_capable` without validating. And contamination is a fact about
**this one pilot**, not about the role: the next single-adjudicator pilot is uncontaminated by
construction, and this clause is then the only rule left. Two tests were added — one drives the
shipped CLI, one pins the masking measurement and goes red the day the filter becomes load-bearing.
Before this round exactly one test of `4,883` failed when the clause was deleted, and it drove a
hand-built manifest; now two do, and one of them drives a command a user can run.

**Disposition: FIXED — kept and exercised, with the reason restated as a measurement.**

**And D-063's own figure does not reproduce.** It states the filter evaluates `48` times across the
four held-out corpora on one full manifest pass. Instrumented as a descriptor and counted, the answer
is `16` evaluations inside `headline_capable` and `41` across a full `validate + notes + as_dict`
pass, of which the single `False` comes from a per-corpus field and **not** from the clause. `48` was
not reproducible under any counting that could be constructed. Reported here; the figure is D-063's
and this record amends the reason rather than editing that record's evidence block.

### Part two: the one claim class the claims gate was never able to see

`tools/check_claims.py` adjudicates numbers against `bench/results.json`. **A number borrowed from
somebody else's paper resolves against nothing**, and operating rule 4 — an external figure carries its
source and the date it was read — had no instrument at all. That is why a sentence in
`docs/EVALUATION.md` offering agreement with an unread publication as *"the strongest available
evidence that this harness, reader and scorer are correct"* survived six audits, two adversarial passes
and four documentation sweeps.

`tools/check_external.py` is that instrument: an appeal phrase from a closed vocabulary **and** a
figure surviving the masking of fenced blocks, code spans and cited values. `UNCITED_LEDGER` is keyed
by a sentence digest rather than by a count, so swapping one uncited appeal for another is still red.

**It found a second live instance of itself in the same document.** `docs/EVALUATION.md`'s bold
*"Harness validated."* — a reimplementation reproducing a shared task's published official scores to
the digit — carries no citation and no read date. `bench/run_disambiguation.py` names its source and
records no date anybody read it on, which is the half-compliance rule 4 exists for. Both are entered in
the ledger with dispositions: the first **blocked on a decision outside the round's scope**, the second
reported.

**And a dangling promise closed on the way.** `docs/EVALUATION.md` had been saying the Ab3P hole was
"named in the standing unknowns" while `docs/DEFINITION-OF-DONE.md` had **no such section**. It has one
now, with three entries. An appeal to something the repository does not contain is the same defect as
the sentence that created the entry.

### Four designs killed before shipping, and one artefact removed by hand

A key-into-a-registry marker was designed and dropped: **no sentence in this tree can be marked**,
because no external paper here has been read on a recorded date, so the registry's only exercised path
would have been its tests — an indirection with zero live users, which is the shape this round was sent
to delete. A phrase-only linter fired `18` times with two or three real hits, about `83` % false
positive, and was replaced by the two-condition rule, which fires `3` times with `1` false positive. An
attribution pattern compiled case-insensitively matched lowercase and ate an unbounded word run,
firing on **this project's own** number; that exact sentence is now a regression test. And a test that
pinned the count of *all* armed appeals would have gone red the day somebody cited a new external
figure correctly — it punished the right behaviour, and was rekeyed to the uncited population.

Removed by hand: a concurrent write raced an in-place mutation restore and left an injected sentence
at the end of `docs/EVALUATION.md`. It was deleted and the mutation class rewritten to **create** a
probe file and unlink it, so a concurrent writer's work cannot be lost.

### How it fails

**The positive path of the new marker has zero live users.** No sentence in this tree carries a
compliant marker, because no external paper has been read on a recorded date. The syntax, the date
parsing, the future-date refusal and the malformed-body refusal are exercised only by fixtures and by a
probe file the tests create and delete. **That is the same criticism this round was sent to make of the
never-headline filter, reproduced one level up.** The difference on offer is that the marker has two
named users waiting in the standing-unknowns table and the filter had none — which is an argument, not
a measurement.

**The largest hole is inherited on purpose and there is a live miss.** A figure inside a code span is
invisible, so `CHANGELOG.md`'s code-spanned Schwartz & Hearst range is a genuine uncited external appeal
the gate cannot see. The alternative arms every configuration value in the tree. D-052 already ruled
that fencing is indistinguishable from hiding; this gate makes that hole one document wider.

**The appeal vocabulary is a list, so a paraphrase walks past it.** "The authors measured `99.9` %"
fires nothing. That is D-060's latency blind spot in a second gate, built in knowingly.

**The gate's one false positive is a judgement and the denominator is three.** Calling a retraction
that quotes its own withdrawn figures a false positive is a call; one reclassification moves the rate by
a third. **Do not quote a rate as a property of this instrument.**

**The filter that was kept still protects only a printed advisory.** The only shipped consumers of
`headline_capable` are `notes()` and `as_dict()`, both inside `tools/splits.py`; **no bench runner calls
it**, verified by grep for this record. So the harm the clause prevents today is that a JSON dump or a
`--check` advisory would name a self-adjudicated corpus — not that a number would be published. A reader
who calls the whole clause ceremony is not obviously wrong, and the docstring now says so.

**And the gate is not registered.** The `.github/gates.toml` entry was drafted, mutation-verified in
situ (mutated `rc=1` with exactly one problem, control `rc=0`, restore digest-checked) and **handed to
the register's owner rather than written**. Until it lands the only thing running this check is its own
test module under the suite — which is a real gate and is not a CI job, and criterion `9` is the
criterion that cares about the difference. **Disposition: blocked on ownership.**

---

## D-081 — The cold reader is made read-only by schema and its trigger becomes executable code with a test. Then the first read under the rule could not write the ledger the rule requires, so the rotation is now a **fixed point** and the gate is green throughout

**Status:** shipped — `tools/second_reader.py`, `docs/cold-reads.toml`,
`tests/test_second_reader_policy.py`, `docs/SECOND-READER.md`, `CONTRIBUTING.md`. The third cold read
ran and **wrote no ledger row** · **Amends:** D-072's three findings against the policy; the policy's
"oldest-read first" cursor rule, replaced by rotation order; `docs/SECOND-READER.md` §4.1's gate count
and §8's duplicate rotation list · **Evidence:** `tools/second_reader.py --trigger|--check|--open|--cost`;
`docs/cold-reads.toml`; `tests/test_second_reader_policy.py`; `docs/notes/cold-read-3-findings.md` ·
**No experiment number spent — experiment eleven is still free**

D-072 found three defects in the second-reader policy, of which the sharpest was that **trigger A's
published command returns an empty list at the exact moment the trigger fires**. All three are closed.

### What is now code rather than prose

`trigger_a()` reads the **working tree** — `git status --porcelain -z --untracked-files=all` over a
published pathspec — and the page's copy of that pathspec is parsed and compared against the module's,
refused on mismatch. Demonstrated in situ on this checkout rather than argued:

```
tools/second_reader.py -- command output, not a benchmark measurement
  state 1, clean worktree of the same commit          trigger returns 0 file(s)
  state 2, this round's tree
      git diff --name-only HEAD..HEAD -- <pathspec>   0 file(s)   <- the superseded command
      git diff --name-only          -- <pathspec>     5 file(s)   <- and it misses the new page
      trigger_a()                                     6 file(s)
```

A test asserts all three of those results in one dirty fixture, so a future round reintroducing the
range has to delete an assertion on purpose. The cursor is **derived** by rotation order and
cross-checked three ways; a read whose `rotation_served` is not what the previous cursor pointed at is
refused, so the cursor is followed rather than announced. The rotation set had **two copies that had
already diverged** — one said fourteen files, the other fifteen, and the amendment appending
`docs/POSITIONING.md` had never reached the first. There is one copy now, and `user_facing_files()`
refuses any user-facing page the rotation cannot serve.

**That last rule closed a hole in the gate itself and then caught a real page within minutes.** The
first version of the rule checked the rotation only against itself; deleting an entry left every check
green, because **a set checked only against itself agrees with itself perfectly** — D-061's "shrinking
a list is not the same as growing coverage", in a second place. Rebuilt against the tree, it went red
naming `docs/SOURCING.md`, a page another workstream had created minutes earlier and nobody had
remembered. `docs/AUDIT-PROHIBITIONS-2026-08.md` appeared in the same window and was correctly not
named.

### The read-only boundary, and the two rules that have never fired on real data

`disposition = "fixed"` requires an `applied_by`, and `--check` refuses an `applied_by` equal to the
reader who raised the finding. An `open` finding must be re-affirmed at every cold read and may survive
at most two, after which it must be applied, blocked on a named decision, or made permanent with a
reason.

**Both of the rules that matter most have a firing count of zero on real data, and that must be said in
those words.** The shipped ledger contains **no `fixed` finding at all**, because the six fixes the
second read shipped were made by that reader and entering them would require naming that reader as
`applied_by` — which the rule refuses on purpose. `--check` prints `fixed 0` on every run so the absence
is visible. The escalation likewise: five findings sit at exactly the limit and the rule bites at the
next read. **Nothing about either rule has been measured against a real finding.**

### And then the round demonstrated the mechanism's cost on itself

The third cold read ran, served `docs/SUPPORT_MATRIX.md`, read ten documents, raised six findings and
re-derived six existing ones — and **wrote nothing**, because the round's own instruction made the
reader read-only in the filesystem sense rather than in the schema sense.

```
python tools/second_reader.py --check   -- command output, after the third cold read
  cold reads: 2 recorded; newest 2026-08-25
  rotation: 21 file(s); trigger B serves docs/SUPPORT_MATRIX.md next
  findings: open 6, fixed 0, blocked 1, permanent 0  (of 7)
  OPEN AND AT THE LIMIT: 5 of 6
  rc=0
```

**The newest `rotation_served` is still the file the *second* read served, so the next reader will
serve the file the third reader just served. Trigger B has degenerated from a rotation into a fixed
point, with the gate green throughout.** Five findings at the limit stay at the limit. Six new findings
sit in `docs/notes/cold-read-3-findings.md`, outside the schema, outside the decay clock and outside
`--check`'s reach.

The policy's own section 5.1 says the boundary "is not a filesystem permission". **The rule the round
was given made it one**, and the `applied_by` mechanism — built specifically so a reader can write the
ledger without authoring prose — was never reached. This record is the disposition: **the read-only
instruction and the ledger requirement cannot both be obeyed, and the failure is silent.**

Two of the third read's findings were applied by the recorder in this round, which is the mechanism
working as designed — a different name in `applied_by` than the one that raised them: the falsehood in
`docs/DEFINITION-OF-DONE.md` about two sentences that were corrected in the same commit that called
them unfixed, and the two stale genre sentences (D-083). The rest are named for their owners.

### How it fails

**`--check` cannot tell whether a cold read happened, and that is still the largest hole.** It
adjudicates state — cursor, rotation coverage, finding shape, dispositions. A round that rewrites
`README.md`, writes no finding and runs the gate goes green. **Disposition: blocked on ownership, not
on design**; the CI job is one paragraph and belongs in files this workstream did not own.

**And registering the gate is not free.** `tools/gates.py --check` prints `debt 23, ceiling 23`; a
thirty-seventh gate with no in-situ evidence makes the debt `24` and turns that check red. The register
entry and the workflow step must land together. The entry is drafted verbatim and handed over rather
than written.

**The read-only boundary is a schema rule, not a permission.** A reader determined to edit a page can
still edit it. What the rule removes is the quiet route — a fix that lands in a diff and is recorded
nowhere. Calling it "the cold reader cannot write" would be a phrasing tighter than the mechanism.

**`docs/cold-reads.toml` is not in `MANIFEST.in`, so it is absent from an sdist** exactly as
`.github/gates.toml` is, while `tools/second_reader.py` does ship. That is the D-058 shape — whatever
the gate reads, the sdist ships — for a fourth time. Reported, not fixed; `MANIFEST.in` is not this
workstream's file.

**The rotation set grew by two fifths and trigger B's latency grew with it.** Twenty-one files instead
of fifteen. The never-read pages were inserted after the cursor rather than appended, so they are
reached within six rounds; the turnover for everything else is a third longer.

**Publishing a new user-facing page now reddens this gate until somebody edits
`docs/SECOND-READER.md`.** That is the anti-rot rule applied to documents, deliberately, and it couples
every documentation workstream to a file it may not own. `docs/SOURCING.md` cost exactly that.

**The ledger's two recorded reads are transcribed, not re-derived.** Reader names, coverage lists and
dates come from D-060 and D-072; only the findings were re-run. If those records are wrong about who
read what, the ledger inherits it.

**And the cursor rule is a policy change, not a discovery.** "Oldest-read first" was uncomputable, so
it was replaced with rotation order. Rotation order happens to reproduce both executed reads exactly
and it is checkable — but nobody voted for it, and a later round may prefer least-recently-read now
that read dates exist.

---

## D-082 — The measured error rate is `20.8` % for a second round with the same `5` of `24` split, and **neither decomposition replicated**. The dominant failure mode moved from staleness to an unmeasured premise stated as a measurement

**Status:** measured; second observation against the baseline D-068 established · **Amends:** nothing.
D-068 said one round of this is a baseline rather than a trend, and two rounds are two points ·
**Evidence:** the R15 sampled pass, seed `20260826`, `24` of `210` submitted claims, each checked
against running code, a live endpoint or a mutation rather than against the document that states it;
two of the five failing verdicts independently re-derived by the recorder · **No experiment number
spent — experiment eleven is still free**

```
24 checked | 19 TRUE | 3 FALSE | 2 MISLEADING | 0 UNCHECKABLE
  not-true rate    5 of 24    20.8 %      <- identical split to D-068
  strictly false   3 of 24    12.5 %
```

**The identical rate is a coincidence and must not be reported as a stable measurement.** The
sampler's own sensitivity analysis is the reason: four claims contain a clause imprecise in the same
way and were split two and two. Grade the two borderline TRUE verdicts the other way and the rate is
`7` of `24`, `29.2` %; grade the two borderline failures TRUE and it is `3` of `24`, `12.5` %. **The
rate is roughly plus or minus eight points on one grader's boundary, which is wider than the gap
between the two rounds.**

### Both decompositions were re-taken, and neither replicated

**By kind of check — this is the finding.**

| kind | this round | D-068 |
|---|---|---|
| settled by one lookup | `2` of `8` — `25.0` % | `1` of `13` — `7.7` % |
| needing a derivation | `3` of `16` — `18.8` % | `4` of `11` — `36.4` % |

D-068's decomposition had a `4.7x` ratio and read as a rule: *the round-level rate is a function of
the sampler's mix*. **This round the ratio is `0.75x` and the gap is gone.** A sensitivity check moving
the two `git`-invoking claims across the boundary gives `16.7` % and `22.2` %, still flat — so the
collapse survives the boundary choice, and the individual cell rates do not.

**Two cautions the reader needs before using either row.** The *mix* also moved, from `13`/`11` to
`8`/`16`, so the two rounds partition their samples differently. And the previous round's boundary was
never written down, so this may be a comparison of two partitions rather than a non-replication. **What
survives both worries is only the direction**: under every boundary tried this round, the two rates sit
within six points of each other, where last round they differed by twenty-nine.

**By failure mode.** D-068 found staleness in `3` of `5`. This round staleness is `1` of `5`, and the
dominant mode is **a premise asserted as fact and never measured** — `2` of `5`. The other two are a
stated method that does not produce the stated number, and an identifier that has never existed in any
committed revision.

### What the three strictly-false claims cost, because two of them damage their own workstream

**An identifier that was never real.** One workstream named an attribute and attributed a reference to
it to another workstream's test module. Re-derived by the recorder rather than carried:
`git log -S"never_headline_capable" --all` returns **nothing**, so the name has never existed in any
committed revision; the same search for the real attribute finds the commit that introduced it, so the
search works; and the test module in question references the real one. **A claim about somebody else's
file, checked against neither.**

**A rebuild that does not reproduce under its own command.** A wheel size and a headroom figure were
published against a named `git archive` plus build invocation. The sampler ran that invocation and got
different bytes; the published figure came from a CRLF checkout at a `README.md` state that no longer
exists. The conclusion it supports is unaffected — the budget has margin either way — but **the figure
appears inside a document written specifically to catch stale figures** (D-077).

**An equivalence between two metrics that is not one, and it is the most expensive of the three.** One
workstream asserted its scorer was equivalent to another's and recommended reconciling field names. The
two split words on different rules and **disagree on the exact-match verdict for `1,244` of `78,374`
distinct real Socrata pairs**. That verdict assigns a pair to *identical* or to *live*, which is the
split the whole of D-074 rests on. The recommendation it supported is withdrawn by its own evidence.

The two `MISLEADING` grades are both self-critical claims a curator would have dropped: a word count
that was true when written and is now `1,824` words short, re-derived by the recorder against
`git show HEAD:` and the working tree; and a premise — "PMC ships no abbreviation gold" — refuted by
the claiming workstream's **own runner**, which takes its entire gold from author-deposited rosters
shipped inside PMC article XML. The conclusion survives on the corrected reason: what PMC does not ship
is an **adjudicated benchmark** gold.

### The pool was not curated, on the same test D-068 applied

`0` of `24` were `UNCHECKABLE`, which is the opposite of a pool padded with unfalsifiable items. Three
failures are outright false, two of the three damage the conclusion of the workstream that offered
them, and two of the five failing claims are self-critical entries. **A pool curated for safety shows
up as an implausibly low rate; this one does not.**

### How it fails

**Two points is not a trend and neither decomposition is powered.** With `5` failures, reclassifying
one claim moves a cell rate by six to twenty points. Both decompositions are recorded so they can be
compared round over round; neither should be read as a direction.

**The sampler graded one claim TRUE on the strength of a docstring written by the claimant.** The file
in question is untracked, so there is no history to search, and the only attestation of the earlier
design is a comment the same author wrote. Everything material about the claim reproduces; a stricter
reader uses `UNCHECKABLE`.

**One test failure was attributed to concurrency without proof.** One of three full-suite runs failed
on a claims-gate coverage test; that run was launched alongside a second pytest process and the test
passes alone. If the flake is real, one `TRUE` becomes at best `MISLEADING` and the round's rate is
`25` %. **The flake is in the gate this project ranks first.**

**The sampler did not re-execute the draw.** The sample is `24` of `210` and the seeded shuffle was
taken on the sampler's word — the one premise in the exercise checked least. And an uncurated draw from
a curated frame looks exactly like an uncurated draw from an uncurated one.

**And the recorder re-derived two of the five failures, not five.** The other three, and all nineteen
`TRUE` verdicts, are carried on the sampler's word. **The error rate of the error-rate measurement is
still unmeasured**, for the second round running.

---

## D-083 — The definition of done, fifth sweep: **no verdict moved**, two criteria moved a long way inside an unchanged verdict, and the page was carrying an outright falsehood about two sentences that had been corrected in the commit that called them unfixed

**Status:** swept; `9` of `14` criteria re-derived, `5` carried and named as carried ·
**Amends:** `docs/DEFINITION-OF-DONE.md` criteria `3`, `4`, `8`, `9`, `11`, `12`, `13`, `14` and the
*Standing unknowns* table; two findings from the third cold read applied, with the applier different
from the reader who raised them · **Evidence:** `docs/DEFINITION-OF-DONE.md`; `tools/gates.py --check`;
`tools/check_claims.py`; `tools/splits.py --check`; D-074 through D-082 · **No experiment number spent
— experiment eleven is still free**

**No criterion closed and none opened, so no criterion closed by narrowing this round.** Two moved a
long way inside an unchanged verdict, and one cell on the page was simply false.

### The falsehood, which is the most useful thing this sweep found

Criterion `3` asserted that `README.md` and `docs/EVALUATION.md` "both promise that CI fails the build
when a performance claim *anywhere in the docs or the source* cannot be traced to a run", and that the
two sentences overstating the gate's reach "are still standing".

```
git log -S "that the gate can recognise" -- README.md docs/EVALUATION.md      -> 3173126
git log -S "still standing, because the right wording" -- docs/DEFINITION-OF-DONE.md  -> 3173126
grep -rn "anywhere in the docs" README.md docs/EVALUATION.md                  -> no match
```

**Same commit.** Two workstreams in one round: one corrected the sentences, the other wrote down that
they were unfixed. It then survived a cold read that covered `README.md`. Corrected here to say the
sentences *used to* promise it, that both were corrected at `3173126`, and that the part still open is
the clause about un-gated figures in user-facing prose.

### The two criteria that moved a long way without moving their verdict

**Criterion `9`** read `CARRYING IN-SITU EVIDENCE: 0 of 36` since the register shipped. It now reads
`13 of 36`, with the top `3` of a published cost ranking demonstrated and a per-round quota stated as
a **ceiling on the debt** so that adding gates cannot dilute the count. **The verdict is still *not
met*, and the honest reading of the thirteen is "all of the gates this harness could ever mutate"** —
the other twenty-three are inline, manual or control refusals. D-079.

**Criterion `11`'s open item halved.** The genre-versus-provenance confound in the interpretation is
no longer a single open question: the genre half is measured on `1,839` same-article PMC pairs, six
ways, all six intervals excluding zero, and it points away from provenance. What remains open is the
provenance half alone, which still needs a corpus nobody publishes. **The page carried the old sentence
in two places and both are corrected.** D-075.

### The rest, in one pass

**Criterion `3`** — not met, and the ledger has a fifth observation: `316`, `262`, `231`, `213`, `201`.
**Criterion `4`** — met and strengthened; the fenced `--check` transcript was stale, because registering
a second `single_annotator_reference` corpus moved the extraction line from *"2 declared"* to *"3
declared"* and added a note. Both the transcript and the prose that reads it are updated, and the
paragraph's point is now stronger, not weaker: **a declared count rose again without the gap moving at
all.** **Criterion `8`** — met, and for the first time the do-not list has a measured error rate rather
than an assumed one: nothing lifted, `13` of `35` of the audit's figures not true today or
unreproducible, nine reasons named for correction. D-077. **Criterion `10`** — not met, re-probed live,
unchanged. **Criterion `12`** — met by the first clause, and the second clause is now satisfied on the
surface that matters, `README.md`, which carried no PLOD span figure at all; the "roughly eighteen
points" framing is superseded by D-076. **Criterion `13`** — met; four observations `54`, `31`, `18`,
`12`, and **the waiver the previous round predicted did not arrive.** D-084. **Criterion `14`** — met,
and the criterion is now less modest and more exposed: the trigger is executable code with a test, the
hand-off is a validated ledger — and the first read under the read-only rule wrote no row, so the
rotation is a fixed point. D-081.

**Carried, not re-derived at this sweep: `1`, `2`, `5`, `6`, `7`.** Five of fourteen now rest on an
answer somebody else gave on an earlier tree, down from seven. The verdict column says so per row,
because a page whose whole purpose is to stop a stale verdict being repeated is the last page that gets
to be vague about which of its verdicts are stale.

### The standing unknown that had to be rewritten rather than ticked

`U-0` — *does a governed catalog add anything on a real schema* — carried the reason *"the one
measurement anybody has taken points the other way"*. **That is no longer true and the unknown is no
smaller.** D-074 shows the measurement measured a catalog's cost on pairs that needed no catalog. So
`U-0`'s cell now says the evidence against has been withdrawn, none for it has been supplied, and the
unknown is unchanged: it still needs one organisation. `U-1` and `U-2` are unchanged and both now have
a gate watching their class.

### How it fails

**Five of fourteen verdicts are carried and this is the second sweep in a row that has carried them.**
A carried verdict is somebody else's reading of an older tree, labelled. Labelling is not checking.

**Every figure in this page's fenced blocks is invisible to the claims gate**, which D-052 says is
mechanically indistinguishable from hiding. The stale `--check` transcript corrected above sat inside
one for a whole round, and the falsehood in criterion `3` sat in prose the gate cannot read at all,
because no rule arms an English sentence.

**The page still cannot tell a criterion that got easier from one that got done.** Criterion `9` moved
from `0` to `13` and the moving part was reading a CI log, not demonstrating a gate; criterion `11`'s
open item halved because a corpus was built, which is the other kind. Both read the same way in the
table.

**And two of the corrections applied here were raised by the third cold read and are the only two of
its six findings anybody applied.** The other four sit in a notes file outside the ledger, outside the
decay clock and outside every gate. D-081.

---

## D-084 — The residue the last round called uncitable was walked number by number, and it paid the floor exactly: `12` out of `docs/DECISIONS.md`, `3` by citation and `9` by deletion, **with no waiver**. The predicted waiver did not arrive, and the reason it did not is that "blocked" was a per-record verdict for a third time

**Status:** shipped — `docs/DECISIONS.md`, `tools/check_claims.py`'s three ledger constants ·
**Amends:** D-071's forecast that *"the next bound round will very likely need a waiver"* and its
sentence that *"outside the three blocked records the citable remainder is zero"*; `DEFERRED_BASELINE`,
`LEDGER_TRAJECTORY` and `RECORD_FILE_PIN` · **Evidence:** `tools/check_claims.py`;
`python tools/check_claims.py --residue`; the diff of `docs/DECISIONS.md` · **No experiment number
spent — experiment eleven is still free**

`11` records were added to this file — D-074 through D-084 — so the pin went red before anything else
was written. That is the binding working, and it is the second round in which adding a record cost its
author something:

```
python tools/check_claims.py -- command output, run by the recorder while adding these records
  docs/DECISIONS.md now holds 83 record(s); RECORD_FILE_PIN says 73.
    Adding a record IS a round. Append a LedgerRound that migrates at least
    12 number(s) out of docs/DECISIONS.md -- or that records a waiver
    saying why it could not -- and re-take the pin in the same commit.
  rc=1
```

### What the walk found, against a forecast that said there was nothing left

D-071 walked the residue of `66` and classified it: `53` inside three records it called blocked, `4`
in indented display blocks a comment-form citation cannot enter without rendering visibly to a reader,
`4` blocked by the gate's own citation-arms-neighbour defect, and `5` that are not measurements of this
library at all. Its conclusion was that the citable remainder was zero and the next round owed a
waiver. **It also said, in the same paragraph, that the blocked verdicts had already proved too wide
per number twice, and that walking them was what the next round's floor should buy.** It bought
exactly that.

```
docs/DECISIONS.md, 66 -> 54.  Three citations, nine deletions, NO fencing.
  CITED
    D-013 :7433  2.3   micro.import.cold_import_ms       prose OUTSIDE the frozen table
    D-011 :7559  85.99 oracle.med1250.oracle_union_recall
    D-011 :7586  88.49 oracle.med1250.own_space_recall
  DELETED -- arithmetic restatement, numerator and denominator both left in place
    D-019 :6922  78.4   restates 411,019 of 524,288 on the same line
    D-014 :7454  82.3   restates 42 of 51 inside the same parenthesis
    D-012 :7504  96.5   restates 518 of 537 on the same line
    D-012 :7505  3.5    restates  19 of 537 on the same line
    D-011 :7570  88.49  restates 1,061 of 1,199 on the same line
    D-011 :7571  78.40  restates 940 of the same 1,199, one line up
  DELETED -- a notional maximum, not a measurement of anything
    D-011 :7559  100    "read against 85.99 %, not 100 %"
    D-011 :7586  100    "report against 88.49 %, not 100 %"
  DELETED -- a figure the record's own sentence declares unquotable
    D-048 :3300  49.72  "...is labelled a two-line heuristic ... and is not quotable"
```

`python tools/check_claims.py --render --dry-run` reports **"up to date, nothing would change"**, so
all three citations render byte-identically to the text already on the page. That is the property that
makes a citation a check rather than a rewrite.

### The three findings the walk produced, which are worth more than the twelve

**"Blocked" was a per-record verdict for a third time.** D-013's whole residue was called blocked
because citing the *after* column of a before/after table leaves one live column beside one frozen one.
That reason is right and it does not reach `2.3` at line `7433`, which is prose **outside** the table
saying what the import costs today. D-071 recorded the same discovery twice and predicted nothing from
it; this is the third instance and it is now a pattern rather than an anecdote. **A verdict written per
record and applied per number will be too wide, and the only way to find out is to read the numbers.**

**The gate defect that blocked four numbers is dissolved by deleting a neighbour, not by fixing the
gate.** Citing `85.99` puts the word *recall* inside the raw line, which arms a bare `100 %` ten
characters later onto a closed value ledger. D-071 routed around it by choosing field names with no
arming keyword. This round could not: the two fields that back these numbers both carry *recall* in
their names. **So the `100 %` went instead** — and it should have gone anyway, because it is a notional
maximum and not a measurement. The defect is unfixed and now has a second published workaround.

**Nine deletions is more than any previous round has taken, and deletion needs a rule or it is
laundering.** The rule applied, stated so a later round can hold this one to it: *a number may be
deleted only when it is arithmetic over two numbers the reader still has, or when it is a notional
bound rather than a measurement, or when the sentence containing it already says it is not quotable.*
Six, two and one. **No number was deleted because it was inconvenient, and no number was fenced** —
fencing cannot count toward this floor by construction, and it did not have to.

### The ledger's fifth observation

```
python tools/check_claims.py -- the record file's own ledger, by round
  before the binding             115
  M2-P4 (the recorder is bound)   84    -31
  M2-P5 (the recorder pays)       66    -18
  M2-P6 (the walk)                54    -12
```

`61` of `115` in three bound rounds against a floor of `12`. **The rate is still falling and this round
sat exactly on the floor**, which is what the last two rounds' arithmetic predicted. What is left is
`54`, counted per record against the file's own boundaries rather than estimated:

```
python tools/check_claims.py -- per-record count of the deferred residue, after this round
  D-023  36   no runner saves pydantic import attribution
  D-013   9   a before/after table cannot have one live column and one frozen one
  D-048   6   figures the record itself labels un-gated, from a workstream report
  D-051   1   a CI threshold quoted as the NAME of a code comment
  D-026   1   a rounded "about 44 %" the record says leaves no row behind
  D-007   1   a perturbation-range endpoint whose twin sentence lives in README.md
```

**The next bound round will need a waiver, and this record states in advance what it must name**: no
runner saves pydantic import attribution; a before/after table cannot have one live column and one
frozen one; a record may label its own figures un-gated and mean it; and three numbers should be
judged `not-a-claim` rather than migrated — one of them with a twin in `README.md`, where editing one
copy and not the other is the defect this project has now hit six times. That is four mechanisms, the
same count D-071 named, and only the composition moved.

### R11: what the gate can and cannot see on the eleven records added here

Eight runs of `python tools/check_claims.py`, one mutation at a time, each restored from bytes read
before it and md5-verified. Six fire red and name the file; one is a measured zero. The line numbers
are the mutated file's and move with any edit above them; `rc` and *is the file named* do not. A and B
mutate a citation this round created; C and D are inserted inside D-074; E puts back one of this
round's nine deletions; F and G mutate `tools/check_claims.py`'s two ledger constants.

```
python tools/check_claims.py -- command output, not a benchmark measurement
  rc=0  control, unmutated                                        <file not named>
  rc=1  A  a migrated citation's value edited 85.99 -> 85.98      docs/DECISIONS.md:8997
  rc=1  B  that citation repointed at run id oracle.nope.union    docs/DECISIONS.md:8997
  rc=1  C  prose added: "... accuracy reached 99.94 % ..."        docs/DECISIONS.md:23
  rc=0  D  prose added: "Median latency ... 41 microseconds"      <file not named>
  rc=1  E  one of the nine deletions put back (a bare "100 %")    deferred 202, baseline 201
  rc=1  F  the pin left at the previous round's record count      84 record(s); pin says 83
  rc=1  G  from_record_file dropped from 12 to 11                 "against a floor of 12"
  restored, both files md5 identical                    rc=0      <file not named>
```

**A and B are what makes three citations worth anything**: a citation can be wrong about its value and
wrong about its run, and both are caught and located. **E is what makes nine deletions worth anything**
— putting one back is a red build, so the migration is a ratchet and not a claim. **F and G are the
binding checking itself**, and both were red in situ rather than in a test fixture.

**D's green is a measured zero, and it is the fourth time this hole has been measured rather than
carried.** `latency` is not in the arming vocabulary and a spelled-out `microseconds` is not in the
unit vocabulary. D-060 found it in `README.md`, `docs/POSITIONING.md` found it in itself, D-071 found
it here, and this round found a **live** instance of it sitting on the front page (D-079). The
widening that would close it is priced at zero and refused with a disposition; see D-079.

### How it fails

**The pin is a deterrent where it is not a mechanism, and that is unchanged.** A recorder who adds a
record may bump the pin's record count and leave its label naming the round that is already newest; the
floor passes, because that round's migrations satisfied it once. Nothing detects a second spend of the
same credit. The defence is that it is a visible source edit in a file the gate reads.

**Rule 6 counts records and is blind to everything else a record can hold.** These eleven records add
several thousand words and a great many code-spanned numbers to this file, and **only the eleven `##
D-` headings cost anything.** Every code span in them is invisible to the gate by construction, which
D-052 says is mechanically indistinguishable from hiding. The honest statement of what the binding
prices is *the recorder's unit of work*, not *the recorder's output*.

**Deletion is a weaker outcome than citation and this round took three times as many.** A cited number
can be wrong and be caught. A deleted number cannot be wrong and cannot be checked, because it is not
there. The trajectory's `by_deletion` column exists so that this trade is visible per round rather than
folded into a single falling total, and this is the first round in which that column carries most of
the movement. **A future round reading `-12` without reading the split would be reading progress that
is nine parts subtraction.**

**The recorder edited `tools/check_claims.py`.** Three data constants — the per-file baseline, the
trajectory row and the pin — with no behaviour change. That file is the instrument this round is
scored by, and a round that edits its own scorer should say so in the record rather than in the diff.
The alternative is a red build with no route to green, and the constants are a source edit **on
purpose**, so that the direction of every migration is in the diff.

**This record's own first draft of the residue breakdown was wrong, and it was wrong in the exact way
D-082 measures.** It said `52` of the `54` sat in two records; the per-record count is `45`, and the
sentence had been written by subtracting from a remembered total rather than by re-counting the rows.
It was caught by re-deriving the breakdown against the file's own record boundaries before publishing,
which is the check D-082's failing claims did not get. **A round that publishes an error rate and then
writes an arithmetic summary from memory has learned nothing from its own measurement**, and the
corrected figures are the ones in the block above.

**And one of the three citations entrenches a figure another workstream recommends retiring.**
D-077's correction `8` says the audit's instruction to retire D-011's `88.49` was never carried out.
This round cited it instead. Citing makes it checkable and says nothing about whether the instruction
should stand; **retiring a recommendation inside a closed record is a maintainer's decision and not a
recorder's**, and it is named here so the next reader meets both facts at once.

---

## D-070 — `acronymkit` is a governance instrument. Three positionings were on the table, the maintainer refused to be handed a least-bad one, and the option taken is the one whose central question is still unanswered

**Status:** shipped — `docs/POSITIONING.md`, and four user-facing surfaces rewritten to match it ·
**Amends:** `README.md`'s tagline and the conclusion of its `## Why` table, the same conclusion in
`docs/ARCHITECTURE.md`, `pyproject.toml`'s `description`; D-042, which recorded the
adoption-versus-technical fork and explicitly declined to answer it · **Evidence:**
`docs/POSITIONING.md`; `README.md`; `docs/ARCHITECTURE.md`; `docs/EVALUATION.md`; `pyproject.toml`;
`governed_gold.socrata.*` and `monoculture.*` in `bench/results.json` · **No experiment number spent
— experiment eleven is still free**

This is the record a reader arriving in a year should find when they ask *why is this library shaped
like this*. D-042 posed the question — technical artifact, or adopted library — and closed without
answering it, on the grounds that nobody had asked the person who gets to decide. This round asked.

**Three positionings were put up with a recommendation attached, and the recommendation was
declined.** The options were (a) a governance instrument, (b) a research artifact about the
extraction monoculture, and (c) a general adoption-seeking library. The maintainer's instruction was:

> pick the right choice for the long term success of the project even if it is hardest

**(a) was taken, and it is recorded here as the right answer rather than as the least bad one.** That
distinction is the whole content of this paragraph. An argument for (a) by elimination would say (c)
has no readable success metric and (b) rests on a claim public data may never settle — both true, and
both are reasons to *not* pick something. The argument that carries (a) is positive and it is a
measurement, and it did not exist before this round. It is in the next section but one.

### The decision, and the two reasons that survive

**The governed half leads.** Generation, backronym synthesis, extraction and contextual
disambiguation all ship, all are measured wherever they can be measured at all, and none of them
leads.

The reason `README.md` used to give was *"the larger half of the package"*, backed by a share of the
source, of the public symbols and of the CLI commands. **That reason is retired as wrong, not as
weak.** Size is not an argument for anything, and a project that leads with its biggest subsystem
would have led with a different one two refactors ago. The two reasons that survive:

- **It is the one acronym task here that the ecosystem table has no row for.** The table in
  `README.md` has four rows and not one of them addresses a bare column token with no sentence around
  it, a catalog somebody else owns, and a requirement to refuse rather than guess. Note the shape of
  that claim: the governed case is not a *row* of the table, so "it is the row with no competitor"
  — which is what an earlier draft said — is false about the table it names.
- **It is the half the refuse-to-guess property is *about*.** A column name is not a sentence, so
  there is no context to weigh and the answer comes from the catalog or not at all. Everywhere else
  in this package refusing is a tuning knob; here it is the design.

**The price of refusing is published in the same paragraph as the commitment.** Against Socrata
field/caption pairs written by the publishers themselves the identifier is cut exactly where the
human cut it on
91.37<!--claim:governed_gold.socrata.columns.all.exact_pct:.2f--> % of them, and on pairs carrying no
boundary mark at all on
34.93<!--claim:governed_gold.socrata.columns.unmarked.exact_pct:.2f--> %. Both are
measured-before-declared rather than held out, and both are taken with an **empty** catalog — see the
first consequence below, which is where that fact now lives.

### Four consequences, not three

The brief that commissioned this record said three. `docs/POSITIONING.md` names four, under a heading
that says softening them later has to be visible. Counted rather than carried:

1. **It requires a real proprietary glossary and this project does not have one.** Everything
   governed is measured against public substitutes, and no catalog is in any published governed
   figure: `bench/run_governed_gold.py` builds `GovernedDictionary({})` and the run record's own
   `system` field says `empty catalog`. Those numbers measure where an identifier is *cut*. They say
   nothing about what a governed vocabulary is worth. **This is a people problem — one organisation
   handing over one glossary and the schema it governs — and no work inside this repository moves
   it.**
2. **The breadth pitch is retired, not softened.** Three sentences left the tree and are quoted
   verbatim in `docs/POSITIONING.md` as retired, so the retirement is auditable rather than
   invisible: the `README.md` tagline, the `## Why` table's *missing single library* conclusion in
   two files, and `pyproject.toml`'s `description` — the line PyPI renders, which led with generation
   and did not mention governance at all.
3. **Extraction F1 is a supporting number and nobody optimises it again.** On MED1250 this library
   scores
   84.21<!--claim:extraction.med1250.acronymkit.exact_f1:.2f--> %, third of five, behind two compiled
   systems that are both named on the front page. Demoting is not hiding: the number stays where a
   reader meets it, because a governance instrument that concealed a middling figure about itself
   would refute its own thesis on its own front page.
4. **The two empty rows are standing properties, not emergencies**, and each is costed rather than
   listed. See D-073, criterion `10`, and the denominator correction below.

### The argument that makes this a decision rather than a preference

**The field's extractors share a blind spot and it has a size.** Across the Schwartz & Hearst family
scored through one harness on PLOD-CW, a single implementation — this library's `BIOMEDICAL` profile
— accounts for
93.55<!--claim:monoculture.plod_all.proposals.edges_sh_only.share_pct_acronymkit/biomedical:.2f--> %
of everything the whole family proposes. The family together reaches
57.65<!--claim:monoculture.plod_all.gold.long_form.overlap.class.sh_family_recall_pct:.2f--> % of
PLOD's gold long forms, rising to
79.60<!--claim:monoculture.plod_all.gold.long_form.overlap.class.all_proposers_recall_pct:.2f--> %
once two proposers that make neither Schwartz & Hearst commitment are added. So a number from that
family is a number about the part of the problem the family can see, and a system that reports what
it cannot see is worth more to somebody governing data than a system that reports a bigger number
over the same blind spot.

**The strong reading of that measurement is confounded and the page publishes the confound in the
same section.** MED1250 is abstracts, PLOD is article body text, and abstracts carry no figure
legends or table footnotes — which is exactly where the unproposed class lives. Every figure above is
equally consistent with *the corpora were built by these systems* and with *abstracts do not contain
the hard cases*. Separating them needs a corpus nobody publishes on purpose. **That absence is a
result, not a task**, and it is why (b) was refused.

**A denominator correction to D-065, made by re-reading the runs rather than the record.** D-065's
compressed sentence is that on MED1250 the independent gain is `0.00`. Two fields carry an
independent gain on that corpus and they do not agree:

```
bench/results.json -- re-read for this record, not carried from D-065
  monoculture.med1250.gold.pairs.independent_gain_pct          0.00
  monoculture.med1250.proposals.edges.independent_gain_pct     0.23
  monoculture.plod_all.proposals.edges.independent_gain_pct   32.04   <- the headline
```

The headline `32.04` is a **proposals/edges** figure, so the control that is denominator-comparable
with it is `0.23` and not `0.00`. `0.00` is the **gold/pairs** control, which is the right one to set
beside the gold-reach percentages above and is what `docs/POSITIONING.md` cites. D-065 is not wrong;
its compression is, and it has already been re-quoted once against the wrong denominator — see D-073,
criterion `11`, where that re-quote is corrected.

### Three reversal conditions, each naming the evidence that fires it

A positioning with no stated reversal condition is a mood. These are stated in full in
`docs/POSITIONING.md`; in one line each:

- **One — the lead is wrong if a catalog is worth nothing on a real schema.** Settled by one real
  proprietary glossary measured against the schema it governs, catalog against empty catalog, on gold
  the auditor did not infer from the labels being scored.
- **Two — adoption-seeking unblocks the day adoption becomes legible.** Settled by evidence that
  names a person or a repository. **No threshold on a download count will be accepted**, because a
  counter cannot separate a human from a scanner for any package on any index.
- **Three — the research artifact stops resting on an unprovable claim.** Settled by article body
  text whose gold was pooled from Schwartz & Hearst descendants, and the run. Not by a better
  argument about the corpora that already exist.

### Where the file lives, and why that is mechanical

`docs/POSITIONING.md` and not `POSITIONING.md`. `tools/check_claims.py`'s `SCAN_GLOBS` holds seven
patterns and its only root-level coverage is `README.md` and `CHANGELOG.md`, **by name** — verified by
reading the tuple, not inferred. A root-level positioning statement would be the one user-facing
document the claims gate never reads, which is the document class most likely to acquire a flattering
figure nothing checks. `MANIFEST.in`'s `recursive-include docs *.md` ships it in the sdist.

The page carries its own R11 evidence: six runs of `python tools/check_claims.py`, one mutation each,
restored and md5-verified. Three fire red and name the file; two of the greens are **measured** zeros
with a positive control in the same battery, so they are the arming vocabulary genuinely failing to
reach a latency claim and fencing genuinely removing a number from view — D-060's blind spot
reproduced on a second page rather than carried on that record's word, and reproduced a third time on
`README.md` by the cold read (D-072).

### How it fails

**The lead was chosen before its central question was answered, and the one measurement bearing on it
points the other way.** Under a portal-disjoint split of real Socrata schemas an adversarial pass
found a voted catalog scoring no better than an empty one, because real schemas are largely already
spelled out. That result is un-gated and its gold is noisy, which is a real defence and is the
adversary's own. It remains true that reversal one exists for exactly the question the commitment
assumes an answer to. A reader who calls the whole positioning provisional on that basis is reading
it correctly, and `docs/POSITIONING.md` says so in its own words.

**The load-bearing sentence is a bridge nothing measured.** `monoculture.*` measures what a family of
extractors proposes and what gold it reaches. It does not measure that anybody prefers a refusal to a
guess. One sentence in `README.md` and one in `docs/POSITIONING.md` assert that bridge and the whole
argument for (a) rests on it. No gate here can read either sentence, which is the class
`docs/SECOND-READER.md` exists for and the class it cannot mechanise.

**"Nobody optimises extraction again" is a promise about future behaviour with no mechanism.**
Nothing turns red if a later round tunes the extractor and publishes a better F1. The gates check
that a number is cited; they cannot check that a project stopped caring about it.

**Two of the three reversal conditions can only be fired by an outsider.** One needs an organisation,
three needs a corpus nobody publishes. The only one under this project's control, two, is satisfied
by a single stranger opening a single issue — which makes it the loosest of the three. A commitment
device whose triggers are mostly not yours is weaker than it looks.

**The retirement is incomplete in a file the gate scans, and this record cannot fix it.**
`src/acronymkit/__init__.py` lines `1` and `3` still open with *"bi-directional, multi-tiered acronym
engine"* and *"One library for the three things production systems do with acronyms"* — two of the
three retired sentences, shipping in the module docstring. Confirmed still present by the cold read
after the positioning workstream reported it. **Disposition: blocked on ownership.** It is one edit
in a source file, and the reason it has survived two workstreams is that neither was assigned it.

**Three near-duplicate copies of the no-row sentence now exist**, in `README.md`,
`docs/POSITIONING.md` and `docs/ARCHITECTURE.md`. That is D-062's cross-copy divergence mechanism,
created deliberately and at least the fifth instance in this repository. They were made
non-identical so that a diverging reader is not misled by false agreement, which is a mitigation and
not a fix, and no lint catches a commit that edits one and not the others.

---

## D-071 — The recorder is bound by the quota it enforces on everybody else: a per-file floor, a record-count pin, and a first bound round that paid `18` more out of the file the carve-out used to protect

**Status:** shipped (mechanism by a sibling workstream, first two bound rounds performed) ·
**Amends:** D-059's carve-out sentence, withdrawn; `docs/CLAIMS-LEDGER.md` §2 · **Evidence:**
`tools/check_claims.py` — `RECORD_FILE`, `RECORD_FILE_FLOOR`, `RECORD_FILE_PIN`,
`LedgerRound.from_record_file`, `record_file_problems()`, `count_records()`;
`tests/test_check_claims.py::TestTheBindingCanFailWhereItRuns`; `docs/CLAIMS-LEDGER.md` ·
**No experiment number spent — experiment eleven is still free**

D-059 ended with the recorder's own escalation against itself: `docs/DECISIONS.md` held `115` of the
`262` deferred numbers and `217` of the `323` citation candidates, no workstream but the recorder may
edit it, and the recorder had migrated none of them. The prediction was that the trajectory would
asymptote at roughly `115` and start being waived for a reason nobody chose. **The maintainer
withdrew the carve-out.** A sibling workstream built the binding and performed the first bound round;
this record is the second, and it is the first one written by the agent the binding is aimed at.

### What the binding is, and why a floor rather than the two alternatives

`LedgerRound` gains `from_record_file`. `trajectory_problems` checks, for every row from
`RECORD_BINDING_LABEL` onward, that it is at least `RECORD_FILE_FLOOR` or that the round writes a
waiver — and that it does not exceed `by_citation + by_deletion`, so **fencing and `by_other` cannot
be counted toward it**. Fencing a number inside a decision record removes it from the gate's view
without deciding anything about it, which is the move the column exists to refuse.

Three shapes were available. A whole-register floor with the record file merely *counted* is what the
policy already had, and nothing stopped a round paying its twelve out of the other files forever —
which is precisely how the record file reached `115` of `262` while the trajectory reported healthy
movement. A waiver-only rule fails the other way: a waiver is free text nothing grades, so without a
floor underneath it the first inconvenient round becomes a permanent exemption granted one sentence
at a time. **The floor is the only one of the three that reddens the build for the case actually
decided against.** The waiver survives underneath it as the named escape rather than as the
mechanism.

### The pin is not a second mechanism; it is the half that makes the floor reachable

`trajectory_problems` only judges rounds that **exist**. A round that adds records and appends no row
satisfies the floor *vacuously* — which is exactly the trajectory the maintainer refused.
`RECORD_FILE_PIN` closes it by pinning the live `## D-<n>` count to the newest round, so growth of
the record file is itself a red build. It counts **records**, not lines or bytes, so a typo fix or a
reflow does not spend a waiver.

**Demonstrated in situ by this round, on the way to writing it.** Four records were added to
`docs/DECISIONS.md` and the gate was run before the pin was re-taken:

```
python tools/check_claims.py -- command output, run by the recorder while adding this record
  docs/DECISIONS.md now holds 73 record(s); RECORD_FILE_PIN says 69.
    Adding a record IS a round. Append a LedgerRound that migrates at least
    12 number(s) out of docs/DECISIONS.md -- or that records a waiver
    saying why it could not -- and re-take the pin in the same commit.
  rc=1
```

That is not a mutation staged to prove a point. It is what the round did, and it is the first time
this file has cost its author anything.

### What this round migrated, re-derived from the file rather than from a plan

`18` numbers, across `15` lines and `10` records, all by citation, **none by fencing and none by
deletion**. `docs/DECISIONS.md` falls from `84` to `66`; the whole register from `231` to `213`.

```
python tools/check_claims.py --render --dry-run   -- command output
  render: up to date, nothing would change
```

Every one of the `18` renders to the text already on the page, which is the property that makes a
citation a check rather than a rewrite. Where they came from:

```
docs/DECISIONS.md, counted by walking the file's own record boundaries
  D-005  2   CMUdict syllable validation, exact and within-one
  D-013  1   the remaining engine import cost, quoted in prose outside the frozen table
  D-017  3   PLOD bracket-adjacency ceilings, test and all
  D-023  1   the session-drift paragraph's own figure of record
  D-026  1   the to_physical_name median after the window fix
  D-030  3   the arity share and the two gate-0.10 verbatim figures
  D-039  2   the two independent arms' legend capability
  D-045  2   PLOD capability, and the equation-surface floor
  D-046  1   PLOD capability again
  D-047  2   the legal train/dev recall-ceiling pair
```

**Two of the eighteen came out of records `docs/CLAIMS-LEDGER.md` §4 classifies as blocked, and that
is the finding of this migration.** D-023 is blocked because no runner saves pydantic import
attribution; D-013 is blocked because citing only the *after* column of a before/after table leaves
one live column beside one frozen one. Neither reason reaches the two numbers taken. D-023's sentence
names `bench/results.json` as the figure of record in its own words, and D-013's `128.1` appears once
more in prose *outside* the table, recommending the migration. **The blocked verdicts were written
per record and applied per number, and per number they were too wide.** The remaining `36` in D-023
and `10` in D-013 are still blocked for the stated reasons.

Two of the eighteen needed a judgement rather than a lookup: the equation-surface floor, whose value
is replicated identically across all three shipped profiles so the citation names one of three
indistinguishable measurements; and the `0.00` capability of the MED1250 arm, which value-matches
over a thousand fields and was resolved by reading the census block the sentence sits under. The
other sixteen are mechanical.

### R11 on what this round added, and D-060's blind spot reproduced a third time

Six runs of `python tools/check_claims.py`, one mutation each, restored from bytes read before the
first and md5-verified identical. Three of the six fire red and name this file:

```
python tools/check_claims.py -- command output, not a benchmark measurement. The line numbers
are the mutated file's and move with any edit above them -- they moved once while this record was
being written, were re-run against the file as shipped, and will be wrong again the moment anybody
inserts a line above D-017. rc and "is the file named" do not move. A and B mutate the PLOD
bracket-adjacency citation in D-017; C and D are inserted immediately above D-070's heading.

  rc=0  control, unmutated                                       <file not named>
  rc=1  A  a migrated citation's value edited 46.30 -> 46.31     docs/DECISIONS.md:7046
  rc=1  B  that citation repointed at run id spans.nope.*        docs/DECISIONS.md:7046
  rc=1  C  prose added: "Extraction accuracy reached 99.94 %"    docs/DECISIONS.md:12
  rc=0  D  prose added: "Median latency ... 41 microseconds"     <file not named>
  restored, md5 identical                            rc=0       <file not named>
```

**A and B are what makes an `18`-number migration worth anything**: a citation can be wrong about its
value and wrong about its run, and both are caught and located. C is the positive control, fired in
the same battery and inside the block this round added. **So D's green is a measured zero.** `latency`
is not in the arming vocabulary and a spelled-out `microseconds` is not in the unit vocabulary, so an
invented latency claim inside a decision record is never seen. That is D-060's finding on `README.md`,
`docs/POSITIONING.md`'s finding on itself, and now this file — **three pages, one hole, and it is the
hole nearest this project's oldest performance claims.**

### Is the binding symbolic? No. And it is about to hit its floor, which is the more useful answer

Two bound rounds have run:

```
python tools/check_claims.py -- the record file's own ledger, by round
  before the binding            115
  M2-P4 (the recorder is bound)  84    -31
  M2-P5 (the recorder pays)      66    -18
```

`49` of `115` in two rounds, against a floor of `12`. The rate is **falling**, and both rounds paid
out of the debt's easy half. **The exact composition of what is left was derived for this record
rather than estimated, and it changes the forecast in `docs/CLAIMS-LEDGER.md` §4:**

```
docs/DECISIONS.md deferred residue, 66, walked against the file's own record boundaries
  53   D-023 (36), D-013 (10), D-048 (7)   -- no runner saves it, or a frozen
                                              before/after column, or the record's
                                              own words say the figure is not quotable
   4   D-011 :6873 :6874, D-012 :6807 :6808 -- 4-space-indented display blocks, where a
                                              comment-form citation renders visibly to a
                                              reader. Blocked on citation syntax.
   4   D-011 :6862 x2, :6889 x2             -- blocked by the gate's own arming defect
                                              (below): each line pairs a citable figure
                                              with a bare 100 % that would move onto the
                                              closed value ledger.
   5   D-051 :2179, D-026 :5324, D-019 :6225, D-014 :6757, D-007 :7091
                                           -- and NONE of the five is a measurement of
                                              this library: a CI threshold, a rounded
                                              "about 44 %", arithmetic over two byte
                                              counts, arithmetic over two pair counts,
                                              and the endpoint of a range. Every one
                                              value-matches something unrelated.
```

**Outside the three blocked records the citable remainder is zero, and that is verified number by
number rather than estimated.** `docs/CLAIMS-LEDGER.md` §4 forecast that the reachable remainder was
`29` — "two rounds at the floor and then a waiver". That population was `29` and this round took `16`
of it; the `13` left are the eight the gate or the citation syntax blocks and the five that are not
measurements of this library at all. So the `29` was never `29` reachable numbers. It was `16`
reachable numbers and `13` that would each have failed for a stated mechanical reason on contact.

Inside the three blocked records the remaining `53` rest on a **per-record** verdict, and this round
has already shown that verdict to be too wide per number, twice. **This record does not claim they
are unreachable; it claims nobody has walked them.** That is the honest state, and walking them is
what the next round's floor should buy.

**The next bound round will very likely need a waiver, and this record states in advance what it must
name**: a runner that does not save pydantic import attribution, a citation syntax that cannot appear
inside an indented display block, a gate defect that arms a neighbour onto a closed ledger, and five
numbers that should be judged `no-number` or `not-a-claim` rather than migrated. That is a waiver
naming four mechanisms rather than a policy, which is the difference the maintainer's decision
bought — and it arrives one round earlier than the ledger page predicted.

### How it fails

**The pin is a deterrent where it is not a mechanism, and this round is the demonstration.** The gate
sees one tree, not a history. A recorder who adds a record may bump `RECORD_FILE_PIN.records` and
leave `label` naming the round that is already newest; the floor passes, because that round's
migrations satisfied it once already. **Nothing detects a second spend of the same credit.** One line
of source. The defence is the one every ratchet here has — a visible edit in a file the gate reads,
with `label` putting *which round paid for this* into the diff.

**Rule 6 counts records and is blind to everything else a record can hold.** Unlimited prose,
unlimited fenced numbers and unlimited citations may be added to an **existing** record without
moving the pin. Fenced numbers are exactly what D-052 warns is indistinguishable from hiding. Only a
new `## D-<n>` heading costs anything, so the honest statement of what the binding priced is *the
recorder's unit of work*, not *the recorder's output*.

**Citing a number arms its neighbour onto a closed ledger, and this recorder reproduced it rather
than taking the report's word.** Applying the two citations the previous round withdrew, in the real
tree:

```
python tools/check_claims.py, both withdrawn citations applied to D-011, then restored
  docs/DECISIONS.md  44 value-matched claim(s), baseline 42
  docs/DECISIONS.md  80 uncited bare number(s) on the deferred ledger, baseline 84
  rc=1        restored, md5 identical, rc=0
```

`keyword_positions` reads the **raw** line, and a rendered citation is raw text, so `recall` inside a
citation body lands within the proximity window of a bare `100 %` further along the same line — and
both `100`s move onto the value-matched ledger, which is closed. **This round routed around it rather
than fixing it**: every one of the `18` citations was chosen with a field name carrying no arming
keyword, which is why the value ledger reads `64 of 64` unchanged. That is a workaround a future
recorder has to know about, and it is written here because nothing in the tool says it.

**`from_record_file` is asserted, not derived.** Nothing verifies that the numbers actually came out
of `docs/DECISIONS.md`. The per-file `DEFERRED_BASELINE` diff catches it in the same commit, but the
two are checked separately.

**The record-floor check judges rows by list index.** Insert a row above `RECORD_BINDING_LABEL` and
every later row silently becomes bound; rename the binding row and **nothing** is bound, with no
message. The second behaviour is pinned by a test, which means the vacuous case is tested rather than
prevented.

**And one claim on the page describing all of this is false.** `docs/CLAIMS-LEDGER.md` §2 says the
record file "carries rendered `<!--claim:...-->` citations in D-036, D-032 and D-034's tables today".
Counted by walking the file's record boundaries: D-032 carries `8`, **D-034 and D-036 carry none**,
and the records that actually carry pre-existing citations are D-031 with `32`, D-039 with `14`,
D-032 with `8` and D-025 with `2`. The argument the sentence supports — that citing inside a decision
record is established practice here — survives on the corrected roster. Reported, not fixed: that
page is not this record's file.

**And this round falsified that page's own stable column, which the page said could not happen.**
`docs/CLAIMS-LEDGER.md` tells its reader to *"read the `deferred` column as a fact and the rest as a
reading taken at a moment"*. After this round §1's `deferred` column reads `231` against a live `213`,
§3's trajectory block reads three rounds against a live four, and §4 opens *"`84` deferred numbers
remain"* against a live `66`. Nothing regressed — the page went stale because the ledger **moved**,
which is the one direction it was built to record. The `deferred` column is stable against *other
workstreams* and not against the ledger's own burn-down, and the sentence promising a reader
otherwise is the sharpest instance yet of D-052's fencing hazard: every one of those figures is
inside a fence, so the gate is silent about all of them and a reader has no signal at all.
**Reported, not fixed**, for the same reason as the roster above and with the same discomfort:
D-059 recorded this page going stale inside the session that wrote it, and it has now gone stale
again, in the session that spent the quota the page exists to govern.

---

## D-072 — The second-reader policy's first execution as policy: it found the front page silent about the empty catalog, and it found three defects in itself, one of which makes its own trigger unexecutable at the moment it fires

**Status:** executed; six fixes shipped by the reader; policy defects recorded and **not** fixed ·
**Amends:** D-060's account of what the policy costs and what it can reach ·
**Evidence:** `docs/SECOND-READER.md` §8; `README.md`; `docs/POSITIONING.md`;
`docs/GOVERNED_NAMING.md`; `bench/run_governed_gold.py` lines `544` and `610` ·
**No experiment number spent — experiment eleven is still free**

D-060 shipped `docs/SECOND-READER.md` and ran one pass against it as a one-off. This is the first
execution **as policy**, and the policy is now carrying state.

**Rotation cursor, carried forward as this record's first duty.** Trigger B served
`docs/GOVERNED_NAMING.md`. **The cursor now stands at `docs/SUPPORT_MATRIX.md`.** The rotation set
was amended from fourteen files to fifteen: `docs/POSITIONING.md` was appended, at that page's own
request, because it was the one user-facing document no trigger could ever reach. Both facts are
written into §8 of the policy page, which is where the state lives.

**Was the policy followable? Partly, and the failures are structural rather than clerical.** The six
mechanical checks and the four questions were followed as written and every one of them produced
something. **The two triggers were not followable as written**: trigger A's command returns an empty
list at the moment it is supposed to fire, and its pathspec cannot reach the file the round changed
that most strangers will read. The reader executed the *intent* of both triggers by falling back to
the working tree and by being told, in the round's brief, to look at `pyproject.toml` — neither of
which the page provides. **A policy that only works because the reader knew what it meant is a policy
that has not been tested yet**, and this is the first round in which it was.

### The finding: the front page was silent about the fact the positioning lists first

`README.md` did not positively overclaim the governed subsystem — it says catalog lookup is *"exact
by construction, which is a tautology rather than a measurement"*, twice. **The defect is an omission,
and calling it an overclaim would have been a phrasing tighter than the measurement.** What it
omitted is that every published governed figure was taken with an empty catalog:

```
grep -n "GovernedDictionary({})" bench/run_governed_gold.py   -- command output
  544:    catalog = GovernedDictionary({})
bench/run_governed_gold.py:610
  "system": "acronymkit.governed.expand_identifier, empty catalog",
```

So the exact-cut percentage on the front page is the splitter with the catalog switched off, and a
reader could take *"it is measured"* plus that percentage as evidence about the governed pipeline.
The reader judged the omission material enough to fix rather than report, and added it to the
README's honest-scope list with the reversal condition linked. **This is the first cost of the
commitment in D-070 arriving on the page a stranger reads first.**

Five more fixes shipped, each with the command that refutes the old text: the README's *"eight
criteria ... and the ninth criterion"* corrected to fourteen and the tenth (a fifth stale
cross-reference the renumbering note did not list); *"one structural count is left"* corrected to
three, each with its re-derivation command; a false sentence in `docs/POSITIONING.md` about inferred
catalogs replaced with the empty-catalog fact; *"seven implementations, one algorithm"* corrected in
two files to five implementations at seven operating points, which is what
`bench/run_monoculture.py`'s own roster says; and `SCAN_GLOBS` corrected from six patterns to seven.
One broken in-page anchor in `docs/GOVERNED_NAMING.md`, out of six files swept.

### Three defects in the policy itself, found by executing it

**Trigger A's published command returns nothing at the moment the trigger fires.** §3 says the cold
read happens *before the recorder writes the round's D-record*, and its command reads committed
history with `<round-base>..HEAD`. At that moment the round is still in the working tree and
`<round-base>` **is** `HEAD`, so the command printed an empty list on a round that had rewritten the
front page. Worse for this round specifically: a new file is invisible to `git diff` under any
revision range, and the round's headline document was a new file. **A reader who trusted the command
would have concluded the round touched nothing and stopped.**

**Trigger A's pathspec cannot see the line PyPI renders.** It scans `README.md`, `CHANGELOG.md`,
`CONTRIBUTING.md`, `SECURITY.md` and `docs`. `pyproject.toml`'s `description` was rewritten this
round and is the sentence most strangers meet first. No trigger on that page would have looked at it.

**"Report everything else" did not produce a fix.** The first pass's C1 finding — `docs/OFFLINE.md`
and `docs/ENTERPRISE.md` claiming the air-gap job drives *"every CLI subcommand"* while the probe
drives thirteen of the sixteen commands `acronymkit --help` lists — is unaltered in all three places
one round later. §5 draws the report/fix line to keep the reader cold; the measured consequence is
that a defect in a file nobody owns waits for a rotation slot **even after somebody has found it and
written down where it is**. That is a cost of the design and it belongs in §6's costing rather than
being rediscovered every round.

### The reader crossed its own boundary, and the recorder is asked to rule on it

§5 says a cold reader who starts editing another workstream's page *"stops being cold and starts
being a seventh author of it"*. The reader made four edits to `docs/POSITIONING.md`, this round's new
page. **The ruling recorded here: three of the four were correct and inside §5's own fix clause** —
they were sentences false against runner source, and §5 permits fixing an outright falsehood in
user-facing prose. **The fourth, the README honest-scope bullet, is authoring and not correction**,
and the reader flagged it as such. It stays, because the fact it adds is the one D-070 lists as the
first cost of the commitment, and a positioning whose first cost is absent from the front page is a
positioning stated only where a reader has already been convinced. A later maintainer who disagrees
should revert that one bullet and nothing else.

### The nomination that does not reproduce, and it is this record's own adversary

Question 4 admits no abstention, so the reader nominated a sentence in `docs/GOVERNED_NAMING.md` as
most likely false — the four-invariant table's *"No policy, argument or code path shortens a name or
drops a token"* — and published two commands as its refutation. **Both were re-run for this record
and neither refutes it as written:**

```
PYTHONPATH=src python -- command output, re-run by the recorder
  normalize("TXN_(c)_ID", GovernedDictionary())   ->  'TXN_C_ID'     not 'TXN_ID'
  normalize("(square-m)",  GovernedDictionary())  ->  'SQUARE_M'     not ''
  normalize("TXN_©_ID",   GovernedDictionary())   ->  'TXN_ID'
  normalize("㎡",          GovernedDictionary())   ->  ''
```

The literal ASCII spellings `(c)` and `(square-m)` keep their letters. **The finding is real and the
published refutation was not**: it holds for the copyright *sign* and for the CJK compatibility
square, not for the ASCII strings the report named. So the invariant's compressed phrasing is still
the right nomination — a name does come back shorter and a character does vanish with no signal on
the `normalize` path — and the commands that show it are two characters, not two spellings. Reported,
not fixed; `docs/GOVERNED_NAMING.md` is not this record's file either.

**This is the round's cleanest instance of its own rule.** A refutation command published beside a
finding is the mechanism that makes the finding checkable, and it is subject to exactly the same
failure as the claim it refutes. It was caught by running it.

### How it fails

**The rotation pick is a judgement the policy leaves undecidable.** §3 says oldest-read-first and no
per-file read dates are recorded anywhere; the first pass left none. The reader read it as *first
entry in rotation order no previous cold read covered*, which is defensible and is not what the page
says. **The policy's only state is a cursor it does not define**, and §8 now carries the cursor
without fixing the definition.

**`docs/GOVERNED_NAMING.md` came back almost clean and that should be read with suspicion rather than
relief.** Eleven thousand words, roughly forty pasted values, four invariants and a `48,000`-call
idempotence fuzz with a positive control, and the only mechanical defect was a broken anchor. Either
it is the best-verified document here, or six checks are aimed at the classes its author already
defended against. The one substantive finding is a compression in a summary table, which is the class
none of the six checks would have caught either.

**No benchmark was re-derived.** Every cited value in three files was checked to resolve against
`bench/results.json` at the printed precision, and the citation mechanism was shown to fail on a
wrong value and a dead run id. **A number that is wrong in `bench/results.json` is invisible to all
of it**, which is §7's second paragraph, still true and now true of a second pass.

**Nothing enforces any of this.** The enforcing CI job is still the one paragraph §7 specifies and
nobody has built, and `python tools/gates.py --check` still prints `0 of 36` carrying in-situ
evidence. **Disposition: blocked on ownership, not on design.** Whoever writes it owes a mutation — a
push touching `README.md` with no `Second-reader:` trailer, red, captured.

---

## D-073 — The definition of done, fourth sweep: no verdict moved, half the criteria were not re-derived and the table now says which, and criterion `11`'s evidence cell was comparing two different denominators

**Status:** swept and reconciled · **Amends:** D-069's head claim that almost nothing is carried, and
D-069's *How it fails* met-count of `9`, which is `10`; criterion `11`'s evidence cell (D-065's
compression, re-quoted against the wrong denominator); criterion `13`'s evidence cell, which had gone
stale inside one round · **Evidence:** `docs/DEFINITION-OF-DONE.md`; the seven gates
re-run on the tree as it is left; D-070 to D-072 above · **No experiment number spent — experiment
eleven is still free**

### Nothing flipped, and that is the least interesting thing here

```
docs/DEFINITION-OF-DONE.md, fourth sweep -- a reading, not a measurement
   met 10 | partly met 1 | not met 3     (met-with-qualification counted as met)
     met:        1, 4, 5, 6, 7, 8, 11, 12, 13, 14
     partly met: 2
     not met:    3, 9, 10
   verdict changes this round: 0
   re-derived this round:  3, 4, 9, 10, 11, 13, 14        (7 of 14)
   carried from an earlier sweep: 1, 2, 5, 6, 7, 8, 12    (7 of 14)
```

**That count was `9` on this page and in D-069, and it does not reconcile with the table under any
rule.** Counting `met with qualification` as met gives `10`; refusing to count it gives `8`. `9` is
neither, it appeared in D-069's *How it fails* — the one paragraph a hostile reader goes to first —
and it flattered the page by one. Corrected here and on the page. The class is the one D-068
measured: a summary written from the previous summary rather than re-counted from the rows.

**Half of this page's verdicts were not checked this round, and the previous sweep's head claimed
almost none were carried.** D-069 said *"almost nothing here is asserted on the strength of a
previous round's answer"* with a named exception of two criteria. This sweep carries seven. The head
of the page is amended to say so and the table carries it per row, because a page whose whole purpose
is to stop a stale verdict being repeated is the last page that gets to be vague about which of its
verdicts are stale.

### Criterion `10` did not move, and it did not close by writing the row off

The brief for this sweep asked whether criterion `10` had closed, and specifically whether it had
closed **by writing the row off rather than filling it**. It did neither. Probed live rather than
read off the previous verdict:

```
tools/splits.py, live probe against the real manifest -- command output
  headline_capable('extraction')               []
  headline_capable('span_detection')           ['plod', 'sdu21_ai']
  headline_capable('disambiguation')           []
  headline_capable('identifier_segmentation')  ['sec_xbrl', 'socrata']
```

Two of the four registered tasks have an empty headline slot, which is the criterion's own subject.
**What moved is where the costing lives, not the verdict.** D-056 and D-063 already held both prices;
this round put them where a user meets them — `README.md`'s honest-scope list names both empty rows
with their denominator, and `docs/POSITIONING.md` costs each in full. The criterion's second clause
still does not apply: the blocker is a **resource** limit and not a property of the task, so the
"permanent property, with the instrument costed" escape remains closed. **Verdict: not met,
unchanged, and the reason for it is unchanged.**

The denominator is worth stating because a compressed version of it was in circulation. "Two of the
five things this library does have no corpus that could adjudicate them" is false: `TASKS` has four
members, the two enforced empty rows are two of four **tasks**, and generation and backronym
synthesis are not tasks at all, so no empty row can exist for them. Both user-facing pages now
publish the denominator.

### Criterion `11`'s evidence cell was comparing a proposals figure against a gold figure

The cell read *union gain `32.04 %` against a control of `0.00 %` on MED1250*. Both figures are real
and they are not comparable: `32.04` is `monoculture.plod_all.proposals.edges.independent_gain_pct`
and the MED1250 field that reads `0.00` is `monoculture.med1250.gold.pairs.independent_gain_pct`. The
denominator-comparable control is `monoculture.med1250.proposals.edges.independent_gain_pct`, which
reads `0.23`. The cell is corrected to name both sides of one comparison. **The criterion stays met**
— the corrected control is still an order of magnitude below the headline, and the confound in the
interpretation is what was already open.

Both figures sat inside code spans, so the claims gate was silent about the mismatch for the whole
time it stood. That is D-052's fencing hazard, on this page, in the round that renumbered it.

### Criterion `13`'s evidence cell went stale inside one round

It said `docs/DECISIONS.md` holds `115` of the `262`. Live at the end of this round: the register is
`213` and the record file holds `66`. Both moved because of D-071, which is the criterion's own
subject — so the cell describing the trajectory was falsified by the trajectory. **The verdict
strengthens.** The trajectory is no longer one observation:

```
python tools/check_claims.py -- the trajectory, four rows
  M2-P2 (register opened)          316    origin, no migration
  M2-P3 X4 (first burn-down)       262    moved 54
  M2-P4 (the recorder is bound)    231    moved 31, all 31 from the record file
  M2-P5 (the recorder pays)        213    moved 18, all 18 from the record file
```

Three observations and a **falling** rate — `54`, `31`, `18`. A rate that falls is what paying out of
the easy half looks like, and the honest reading of three points is that the next one is smaller
again. That is stated in the verdict rather than left for a reader to notice.

### How this sweep fails

**Seven of fourteen carry a verdict this round did not check**, and one of the seven — criterion `12`
— is one of the three that closed in the last round, which is exactly when a verdict is least tested.

**Two of the three corrections on this page were found by reading it against `bench/results.json`,
which is a check nothing runs.** Criterion `11`'s denominator mismatch and criterion `13`'s stale
counts were both inside code spans, invisible to the gate by construction. **Every other fenced
figure on this page has the same exposure**, and the page's own convention — print the command above
the block — is the whole defence, exactly as `docs/CLAIMS-LEDGER.md` says of itself and exactly as
D-068 measured failing.

**The met-count did not fall in a round that added no criteria**, which is the first time that has
been true, and it should not be read as progress. Nothing closed either.

**And this sweep was taken on a tree three workstreams had been editing throughout.** `README.md`,
`docs/POSITIONING.md`, `docs/ARCHITECTURE.md`, `docs/EVALUATION.md`, `docs/GOVERNED_NAMING.md`,
`docs/SECOND-READER.md`, `docs/CLAIMS-LEDGER.md`, `pyproject.toml`, `tools/check_claims.py` and
`tests/test_check_claims.py` were all uncommitted at hand-off. Every command in this record was run
against that tree and none of it is anchored to a commit — the same weakness D-069 recorded, one
round later, unfixed.

---

## D-059 — The deferred ledger gets a written policy, a quota and a trajectory the gate enforces; the four buckets the mandate scoped needed six; and the page describing all of it went stale inside the session that wrote it

**Status:** shipped · **Amends:** D-052 (the residue is classified and the ledger now has a rate),
D-057 (criterion 3's evidence) · **Evidence:** `tools/check_claims.py` — `LEDGER_TRAJECTORY`,
`MIGRATION_QUOTA`, `trajectory_problems()`, `--classify`; `docs/CLAIMS-LEDGER.md`;
`tests/test_check_claims.py` · **No experiment number spent — experiment eleven is still free**

This record is first because it changes the rule every other record in this round publishes under.
A commit that lowers either ratchet without appending a round to `LEDGER_TRAJECTORY` now turns the
CI gate red, and the round it appends must say where every migrated number went.

```
python tools/check_claims.py -- command output, re-run by the recorder for this record
  value-matched ratchet:  64 of 64 budgeted across 3 file(s)
  deferred ratchet:      262 of 262 budgeted across 10 file(s)
  ledger trajectory: 2 rounds | M2-P3 X4 (first burn-down)
                     moved 54 (citation 52, deletion 2, fencing 0, other 0)
                     deferred 262, value-matched 64 | quota 12 per round
```

**The fencing column is the load-bearing one and it reads zero.** D-052 established that a fenced
number leaves the gate's view entirely, so a falling ledger is not evidence of adjudication unless
the fencing column is published beside it. It is now a checked field: `trajectory_problems()`
refuses a round whose four columns do not add up to the fall it claims, demonstrated red by
mutation.

### Value matching is unsound in the direction nobody had measured

D-052 established that value-matching the residue would relabel invisible numbers "backed". The
converse was measured this round on a real population: of the nineteen `UNIQUE`/`REPLICATED`
deferred numbers in `docs/EVALUATION.md`, **four rows carrying three distinct values** match a
measurement of something else entirely — three competitor cold-import times matching a short-form
F1 delta, an abstention recall and an ablation score. So `gate-able` is a **candidate** label
wherever it appears, in the tool, the report and the page.

That coincidence is what hid the underlying defect, and it is the sharper finding: **the whole
"Cold import" column of the flagship extraction comparison table in `docs/EVALUATION.md` has never
been saved by any runner.** `bench/run_micro.py` measures this library's import and nothing else.
Reported, not fixed — that table is not the recorder's file either.

### The classification needed six buckets, and the debt is the ledger, not the residue

```
python tools/check_claims.py --classify -- command output, re-run for this record
  bucket          deferred  unexamined   total
  gate-able            123         200     323
  no-number              0           0       0
  stale                  0           0       0
  blocked              135          10     145
  not-a-claim            4         365     369
  unclassified           0         919     919
  ALL                  262        1494    1756
```

`not-a-claim` and `unclassified` are not editorial hedges. Forcing several hundred calendar years,
ISO-date fragments and interpreter versions into "prose that should not carry a number" would have
been a false statement about them. **The debt is the ledger column, not the total.**

### The page describing this went stale before this record was written, and only one column held

Three readings of the same `ALL` row, all inside one session, on one tree:

```
docs/CLAIMS-LEDGER.md as shipped, fenced          ALL  262  1480  1742
the sampled-verification pass, hours later        ALL  262  1483  1745
this record, re-run by the recorder               ALL  262  1494  1756
```

The `deferred` column is identical in all three because it is the ratcheted one. The other two move
whenever any workstream adds a scanned document — `docs/SECOND-READER.md` landing is enough. The
page says of itself that its counts drift; it is fenced, so the gate is silent about it; and it
became false within hours of being written. **That is D-052's warning arriving on the document that
quotes D-052's warning**, and it is the reason this record publishes the drift rather than a
corrected snapshot.

### Two migrations that are corrections rather than migrations

`README.md` and `docs/ARCHITECTURE.md` both claimed `F₁ > 96 %` for rule-based extractors in a
comparison row. That is a precision figure labelled F1: this file records the published
Schwartz & Hearst range as `~86–89 % F1 on Ab3P` and this project's own harness scores the two
shipped descendants at `88.87` and `80.73`. Both rows now carry no figure. **Deleting a number
created one**: the first replacement wording put the keyword `precision` inside the proximity window
of a `2003` citation year and armed a number in two files whose value baseline is zero. The gate
caught it. That failure mode was not predicted by anyone and belongs in this record.

### How it fails

**The quota is gameable in exactly one way and nothing detects it.** `trajectory_problems()`
compares the last row to the baselines, not to a live scan — deliberate, because a live comparison
would redden on any edit by any workstream — so a round that adds debt in one file and migrates the
same amount in another nets to zero and passes. Only the per-file ratchets catch that, and the
trajectory has no per-file column.

**A waiver is free text and nothing grades it.** The quota was set at `12` against a round that
moved `54`, which avoids guaranteeing the first waiver and is unfalsifiable until a round misses.

**And the structural ceiling is now the recorder's problem, which is a conflict of interest worth
writing down.** `docs/DECISIONS.md` holds `115` of the `262` deferred numbers and `217` of the
`323` `gate-able` ones — nearly half the ledger and two thirds of its citable half — and no
workstream may edit this file. **I am the only agent who can migrate them and I migrated none of
them this round.** The trajectory will asymptote at roughly `115` and start being waived for a
reason nobody chose, unless the recorder is bound by the same policy as everybody else. That should
be the next round's first question about this record.
---

## D-060 — The gate that adjudicates this project's claims cannot see a latency claim, and two user-facing pages promise that it can. A second reader now exists, and it found the flagship page's correctness argument citing numbers that are not in the file

**Status:** finding published and reproduced; policy shipped; the two overstated sentences **not**
corrected · **Amends:** the claims-gate scope sentence in `README.md` and in `docs/EVALUATION.md`;
D-059's account of its own instrument's reach · **Evidence:** `docs/SECOND-READER.md`,
`CONTRIBUTING.md`, the mutation below, `docs/EVALUATION.md` line `144` ·
**No experiment number spent — experiment eleven is still free**

`README.md` and `docs/EVALUATION.md` both say CI fails the build when a performance claim *anywhere
in the docs or the source* cannot be traced to a benchmark run. **The recorder reproduced the
counter-example rather than carrying it on a report's word:**

```
one prose bullet inserted at README.md line 577, then `python tools/check_claims.py`
  A  "- Median latency for a governed expansion fell to 41 microseconds in this release."
       rc=0    every checked number is backed by bench/results.json, a citation, or the allowlist
  B  "- Extraction accuracy reached 99.94 % in this release."      <- positive control, same line
       rc=1    README.md:577   '99.94' in: - Extraction accuracy reached 99.94 % ...
  restored     rc=0
```

`latency` is not in the gate's keyword vocabulary and a spelled-out `microseconds` is not in its
unit vocabulary, so the sentence is never armed and never seen. Not corrected here: the right
wording is a judgement about how strong a promise the project wants to make, and `SCAN_GLOBS`
excludes `CONTRIBUTING.md`, `SECURITY.md`, `tools/*.py` and `bench/*.py` besides.

**A recorder's own null result, with its firing count, because it nearly went into this record as a
finding.** My first attempt inserted both sentences at `README.md` line `101` and **both** returned
`rc=0` — which reads as "the gate misses its own control too". Line `101` is inside a fenced Python
block. The instrument fired **zero times** on both runs; I had measured nothing. The mutation is
evidence only at a prose line, and the gap between those two attempts is the entire content of R12
demonstrated on the person writing the rule down.

### The flagship page's harness-correctness argument cites two numbers that are not in the results file

`docs/EVALUATION.md` line `144` reads that pyab3p's `96.96 / 83.62` "lands within half a point of
the figures published for Ab3P on MED1250, which is the strongest available evidence that this
harness, reader and scorer are correct". Verified by the recorder:

```
the table twelve lines above  pyab3p  P 96.91  R 82.06
grep -c "83.62" bench/results.json                       0
extraction.med1250.pyab3p     exact 96.91 / 82.06        relaxed 97.10 / 82.23
```

`96.96` does occur in `bench/results.json` — as a long-form overlap precision on unrelated SDU-22
scientific legend rows, which is to say it would value-match by coincidence, which is D-059's
finding arriving on the sentence that argues the harness is correct. Both the sentence and the
table row entered in the commit that created the file. **Six audits, two adversarial passes and
four documentation sweeps did not read the sentence against the table five lines above it.** Not
fixed: repairing the numbers collapses the "within half a point" conclusion the sentence exists to
carry, and rewriting that argument is a decision for whoever owns the page. The comparison is also
**unmeasurable from this repository in either direction** — no published Ab3P figure appears
anywhere in the tree.

### The deliverable, and why the trigger has two halves

`docs/SECOND-READER.md` is a two-trigger cold-read policy, wired into `CONTRIBUTING.md` as a
required step and costed at one agent slot or about ninety minutes. **Trigger A** cold-reads the
user-facing files a round actually touched. **Trigger B** rotates one untouched file per round, and
it exists on a count rather than a hunch: `7` of the `15` findings in the first pass were in files
this round's diff never touched, so a diff-only trigger has a measured miss of `7` in `15` on this
round's own evidence. Six mechanical checks ship, each named for the live defect it caught.

`CONTRIBUTING.md` itself carried three false statements and is corrected: it listed four gates and
omitted the two that fail on a *document* rather than on code; it said mypy runs over
`src/acronymkit`; and its non-negotiable 6 forbade network access "in the library or in `tools/`",
which is false of the three tools whose entire purpose is fetching. Two outright errors in
`README.md` are fixed — a documented backronym output the shipped library does not produce, and a
four-verb dependency-isolation claim for a CI job that runs two verbs.

### How it fails

**The policy has no gate, and this repository has learned to distrust exactly that object.** Eleven
places cited `bench/splits.toml` in prose, none parsed it, and it was invalid TOML for months. The
enforcing check is specified in one paragraph and was declined, because it belongs in files nobody
this round owned and because a gate never demonstrated failing where it runs is D-058's shape. A
reader who calls the deliverable aspirational until that job exists and has been mutated red on a
real push is reading it correctly.

**A second reader who fixes things stops being cold, and three things were fixed.** The line drawn
was "the correct text is fully determined by a command I ran"; a reader may reasonably call that
line arbitrary.

**The yield is self-graded.** `15` findings and `6` material is one reader's classification of one
reader's output, with no second adjudicator — the circular structure this criterion exists to
break, one level up.

**Trigger B bounds nothing.** One untouched file per round over a fourteen-file rotation means a
defect in a quiet document waits seven rounds on average. The two oldest defects it found had been
wrong for far longer than that.

**And three of the fourteen rotation files were never read** — `docs/GOVERNED_NAMING.md`,
`docs/QUICKSTART_GOVERNED.md`, `docs/INSTALL.md`, about `2,400` lines between them. Absence of
findings there is absence of looking, and the page says so rather than reporting a clean read.
---

## D-061 — R11 made executable: a gate register, a mutation harness, and the finding that shrinking a list is not the same as growing coverage

**Status:** shipped — register, validator, mutation harness, scheduled workflow, docs, `51` tests,
two `ci.yml` steps · **Amends:** D-050's `[[defect_coverage]]` reasoning for breakage `e`; D-058's
closing note on its two ad-hoc checks · **Evidence:** `.github/gates.toml`, `tools/gates.py`,
`tools/gate_packaging_mutation.py`, `.github/workflows/gate-mutation.yml`,
`tests/test_gate_manifest.py`, `docs/GATES.md`; exports of `4f812e1` and `a62f99a` ·
**No experiment number spent — experiment eleven is still free**

R11 says a gate must be demonstrated capable of failing **in the environment where it runs**. This
round made the premise executable for the first time. Re-derived by the recorder:

```
python tools/gates.py --check -- command output, re-run for this record
  gate manifest: 36 gate(s) across 21 environment(s) in 5 workflow file(s)
  mutation kind: automated 13, control 2, inline 8, manual 13
  demonstrable by this harness: 13 of 36
  CARRYING IN-SITU EVIDENCE:   0 of 36   <- R11 is not satisfied for any gate here
  gate manifest OK
```

**That last line is the state of the deliverable and it is printed on every CI run.** The mechanism
ships; the evidence does not exist for a single gate, because nothing in this round could push,
dispatch a workflow or read a run log. A count that makes the absence unmissable is not a table
that implies coverage, and it is also not evidence.

### The finding: D-050's coverage numbers reproduce exactly and the reason for one of them has changed

`installed-suite` still misses breakage `e`. It used to miss it because of a file-keyed
`EXPECTED_NON_PASSING` entry; D-058 deleted both file-keyed entries; it is still missed, now because
`tests/test_splits_manifest.py` fires a module-level skip at line `133` before the unguarded load at
line `143`. **The blind spot moved out of a list of names in `ci.yml` and into a skip condition in a
test file. It did not shrink: `2` of `5` before, `2` of `5` after.**

```
tools/gate_packaging_mutation.py -- five historical breakages on a real sdist
  case    test -f   extracted tree   installed-suite   label
  control passes    passes           passes            unmutated control
  a       FAILS     FAILS            passes            bench/results.json out of the sdist
  b       FAILS     passes           passes            data/LICENSES.md out of the sdist
  c       passes    FAILS            FAILS             tests/fixtures/* out of the sdist
  d       passes    FAILS            FAILS             test_governed_gold.py loads bench/ unguarded
  e       passes    FAILS            passes            test_splits_manifest.py, same defect
  build/extracted tree catches 4 of 5  |  installed-suite catches 2 of 5
```

**Reading "the list shrank" as "the coverage grew" is the error to book**, and the workstream that
found it had reasoned its way to the opposite answer before measuring.

### A transcript-only check went green to red in one commit and nothing noticed

D-058's `4348 passed, 112 skipped, zero collection errors` for a checkout with `tools/` and `bench/`
moved aside is exact at `4f812e1` and red at `a62f99a` on
`tests/test_packaging_manifest.py::test_every_file_the_claims_gate_reads_is_shipped_by_the_manifest`
— a test **added by `a62f99a` itself**, the commit that fixed the previous instance of a check that
cannot fail where it runs. The record was right; the tree moved under it in one commit. The
workstream's first draft said the record was wrong, and exporting the commit is what stopped it.

### R11 demonstrated in two runs of one command

With D-058's cause one restored on one export of HEAD: `88 passed` with `data/` present,
`1 failed, 87 passed` with `data/` absent. Same tree, same suite, same defect, opposite verdicts,
and no local gate could have said so.

### What the register buys, and its unit

`--assert-environment` makes the environment premise executable — `holds`/`lacks` as repo-relative
globs rather than prose — generalising the `air-gap` job's namespace control, which was the only
positive control in the repository and had never been applied to a second job. **Splitting one YAML
step into three gates was a finding, not tidiness**: "verify the sdist ships the files its own suite
reads" runs a `test -f` list *and* a whole pytest run, catching `2` of `5` and `4` of `5`
respectively. Registered as one gate it would have published a single number true of neither. **The
register's unit is the assertion, not the step.**

### How it fails

**Zero of thirty-six gates carry in-situ evidence, and that is the whole objection.**
`.github/workflows/gate-mutation.yml` has never executed — `260` lines of YAML written blind, which
is precisely the state every workflow file in this repository that has ever been wrong was in. Expect
the first scheduled run to be red.

**Twenty-one of thirty-six gates carry no mutation at all** — `8` refused `inline`, `13` `manual`.
Each carries a reason, which is R14 satisfied, and R14 satisfied is not R11 satisfied. Three of the
eight fall to one afternoon of extracting heredocs into `tools/`, and the architectural argument for
refusing them is also a very comfortable place to stop.

**The mypy probe's demonstration is the least transferable thing on the page** — Windows, CPython
`3.13`, `click 8.1.8`. The gate most worth demonstrating is the one whose demonstration depends most
on the environment nobody could enter.

**`installed-suite` and `build` are reproduced, not invoked.** Drift between `ci.yml` and the
harness is undetected except for the `EXPECTED_NON_PASSING` half.

**The anti-rot rule rests on a single point of failure that is an indentation matcher.** The PyYAML
cross-check is an `importorskip`; on a runner without PyYAML the scanner is checked only against
itself.

**The mutation runner writes to files outside its brief and restores from bytes read at apply time.**
In a tree several agents were editing, a write landing between the read and the restore is silently
lost. Nothing was lost — the two resource files were md5-verified — but the hazard is structural.

**`docs/GATES.md` ships in the sdist and `.github/gates.toml` does not**, so a shipped page links to
an absent file: the `data/LICENSES.md` shape, fifth instance, arriving through a door this round
opened and could not close because `MANIFEST.in` belonged to another workstream.
---

## D-062 — The paragraph refusing to extend the type checker was measured with the checker configured not to see the defect, and three more of that defect were still shipping

**Status:** fixed · **Amends:** D-058 (its "what is not done" measurement, and its commit message's
"all five bad calls"), the `[tool.mypy]` comment in `pyproject.toml`, the `installed-suite`
composition list in `.github/workflows/ci.yml`, `MANIFEST.in`'s `data/` size, `CHANGELOG.md`'s
`[Unreleased]` note on the mypy floor · **Evidence:** `python -m mypy`;
`python -m mypy tools bench --python-version {3.9,3.10,3.13}`; the mutation battery; the
`click 8.4.2` MYPYPATH reproduction · **No experiment number spent — experiment eleven is still
free**

D-058 refused to extend `files` and priced the refusal at `51 errors in 14 files`. That is the
`python_version = "3.10"` reading — **the setting the same commit deleted three lines above it.**

```
python -m mypy tools bench --no-incremental, re-derived
  --python-version 3.9    Found 54 errors in 17 files (checked 31 source files)   <- the configured floor
  --python-version 3.10   Found 51 errors in 14 files (checked 31 source files)   <- the deleted setting
  --python-version 3.13   Found 50 errors in 13 files (checked 31 source files)
```

The `3.9`-to-`3.10` delta is exactly three errors in three files: the three surviving
`Path.write_text(newline=...)` calls in `tools/fetch_data.py`, `tools/build_lexicons.py` and
`tools/build_reliability_table.py`. D-058's commit message says "`tools/` — where all five bad calls
were". Five were, all in the one file that round had just written; three older ones in three other
files were never looked for. **The class was named correctly and the search was scoped to the
symptom.**

All three are fixed. `files` is now `["src/acronymkit", "tools", "bench"]`, all `54` errors are
cleared, and the recorder confirms `python -m mypy` reports `Success: no issues found in 75 source
files` against `40` before.

### Two rules this bought, both of which will be re-litigated

**`warn_unused_ignores` is only as trustworthy as the file set it runs over.** Ten suppressions in
`bench/` read as dead under `mypy tools bench` at every version tried, and two came straight back
under the configured run, because including `src/acronymkit` changes import resolution. Two adjacent
monkeypatch sites that had **never** carried a suppression needed one for the first time — that
patching had been invisible while `bench/` sat outside `files`. **A suppression audit taken on a
subset is not an audit.**

**`disallow_untyped_defs = false` without `check_untyped_defs = true` is a weakened check that
reports green.** The one relaxation is three named `bench` analysis runners; dropping the signature
requirement alone would have removed sixteen function bodies from analysis while the run printed
success. Turning `check_untyped_defs` on immediately surfaced two further real errors inside
previously unreadable bodies. `tools/` takes the library's strictness with **no override of any
kind**, because every defect of this class so far has been in `tools/`.

### The number-free assertion class now has a measured error rate

A mechanically harvested population — a comment block, docstring or paragraph naming a repository
artefact *and* carrying an assertion verb — gives `757` candidate units in `99` files. A census of
the configuration stratum plus a seeded sample of the rest plus a targeted grep for the exact shape
that had gone false twice gives `43` assertions checked and `5` false: **`11.6 %`, or `7.0 %`
excluding the two this round's own work falsified.** Two of the five were the same sentence written
twice and updated once — `pyproject.toml` against this file, and `ci.yml` against itself sixty lines
apart — which with D-058's two makes **four instances of one mechanism.**

**`.github/workflows/ci.yml` contradicted itself about the same two test modules for a whole round**
and nothing could turn red over it. It is still wrong, in the other direction, and the recorder
verified it live: the file's own prescribed re-derivation `grep -l allow_module_level tests/*.py`
names **five** files while the comment beside it says "which names exactly the three files above".
Two new test modules landed this round carrying that skip. Reported, not fixed — the file is not
the recorder's.

### The one mechanically checkable sub-class, named because "no gate exists" would be too broad

Path existence and symbol existence would have caught **none** of the five found here. Re-running
fenced `$ command` blocks and diffing the output would have caught the headline one, in both copies,
and needs an opt-in marker — which is D-052's fencing problem with the sign reversed. **Cross-copy
divergence detection** is the one that matches the actual defect pattern: four instances of one
mechanism is a shape, and a lint that flags a commit changing one copy of a near-duplicate sentence
and not the other is a real gate rather than a wish. None of the three was built.

### How it fails

**The headline rests on an identification, not a reproduction.** Nobody checked out the commit that
published `51 errors in 14 files` and re-ran it there. What exists is: today's tree reads exactly
`51 errors in 14 files` at `3.10`, `54 in 17` at `3.9`, and the difference is precisely the three
version-sensitive errors. That is strong and it is still an identification.

**The mutation battery ran locally, which R11 says is not the environment.** Four of five mutations
applied and all four were killed; the fifth was skipped for a non-unique anchor and not re-anchored.
The `click 8.4.2` reproduction is the one substitute that uses the mechanism CI has actually broken
this gate with.

**The `11.6 %` is a rate over the easy-to-find half.** The harvester requires an artefact token
*and* an assertion verb in one unit, so a sentence that says "the checker only looks at the library"
without naming a file is invisible to it. `757` is a lower bound on the population and the in-class
denominator on the sampled stratum is `18`, not `40`.

**`bench/` is now inside `files`, and four other workstreams had that cost imposed on them without
being asked.** The first instance arrived within minutes.
---

## D-063 — A refusal with no disposition is an unclosed ticket wearing principle's coat: `ROLES` gains a third member, and the corpus that could never back a headline now cannot even by policy edit

**Status:** shipped · **Amends:** D-056 (the registration refusal), D-057 (criterion 9's evidence) ·
**Evidence:** `tools/splits.py`, `bench/splits.toml`, `bench/corpora.py`,
`tests/test_splits_manifest.py`, `tests/test_build_gold_corpus.py`;
`python tools/splits.py --check`; `python tools/build_gold_corpus.py fetch --refresh --mirror-check`
· **No experiment number spent — experiment eleven is still free**

D-056 refused to register the Federal Register reference set because `ROLES` could not say what it
was, and that refusal was correct on its merits. **Its permanence was never argued.** It persisted
because a two-element tuple had not been extended. The disposition is now *fixed*, not *permanent*.

Re-derived by the recorder against running code:

```
tools.splits.ROLES                  ('tuning', 'held_out', 'single_annotator_reference')
tools.splits.NEVER_HEADLINE_ROLES   ('single_annotator_reference',)
bench.corpora.UNREGISTERED_READERS  {}
python tools/splits.py --check      9 corpora, 3 reserved arm(s), 0 problem(s)
```

**Three enforced properties, not one label.** `NEVER_HEADLINE_ROLES` is enforced twice — the
validator refuses a `[policy] headline_requires` naming such a role, *and* `headline_capable()`
filters it out unconditionally — so the exclusion survives a bad policy, a bypassed gate or a caller
that never validated. `ROLE_REQUIRED_FIELDS` makes `adjudicators` and `pooling_recipe` mandatory,
and a bare string is refused rather than coerced to an empty tuple that would report as *missing*.
`ROLE_LABEL` replaces a two-branch conditional that was correct for two roles and would have printed
**"held out"** for the third in every runner header on the commit that added it.

**The opposing reading, stated fairly because it is good.** `Corpus.is_tuning`'s docstring defines
the field as a statement about *figures*, so `role = "tuning"` was available on day one with no enum
change. That reading is right about the label and wrong about the field: `role` is read by
`headline_capable`, `require_role`, `bench/corpora.py` and every runner header, where `tuning` means
*the system has seen this* — false here — and it carries no obligation to record the adjudicator at
all.

### The R12 line this record must carry, and it cuts against the work

Under the shipped `[policy] headline_requires = "held_out"`, the new filter inside
`headline_capable()` evaluates **zero times** on the corpus it was written for: `with_role` excludes
it upstream. One full pass over the real manifest evaluates it `48` times across the four held-out
corpora and `0` times on the Federal Register set. **The braces have only ever fired in a test.**
The defence is a design argument — D-056's whole finding is that the wrong filing is one word away,
and an exclusion depending on a *different* word staying put is one word away too — and a design
argument is not a measurement.

### Two false greens, kept because they are the shape

A reader-role assertion with **no test that failed when it was deleted** — the test drove
`Corpus.require_role` directly rather than the wiring, so removing the reader's branch left `81`
tests passing at `rc=0`. And a never-headline test whose fixture was **also contaminated**, so a
different rule did the excluding and deleting the role filter left `101` tests passing. Both were
found by mutation, both rebuilt, all eight mutations now red. A vacuous tripwire was caught in the
same commit that would have made it vacuous: a loop over `UNREGISTERED_READERS` runs zero times once
the map is empty, so the check became a function driven against both the real empty map and a
synthetic one.

### A correction to nobody's fault, and a rule that was never written down

D-056's four-way proposer table reproduces **exactly** — but only under **case-folded** edge
identity. Under exact-case identity the same frozen pool gives `588 / 182 / 598` where the record
publishes `584 / 179 / 594`. The identity rule was never stated, and two readers reproducing the
same file with different dedup rules get different tables. The entry now publishes both, labelled.
The workstream was one edit away from accusing D-056 of not reproducing.

### How it fails

**A governance vocabulary was widened to hold exactly one corpus, and that corpus is a pilot nothing
can score.** A reader who says a role with one occupant is a special case wearing a vocabulary's
clothes is making a fair point.

**Reproduction was verified and mistaken for verifying the corpus.** `30` of `30` documents re-fetch
to matching digests against both the pin and an independent government mirror, with both failure
branches demonstrated firing. That says the *text* is stable. It says nothing about whether the
payload documents' pairs are right or whether one adjudicator's verdicts would survive a second
reader — and this criterion is about adjudication, not provenance.

**Three published fenced blocks were made stale on purpose and none were fixed by their author.**
`--check` moved from `8 corpora` to `9`, and from `(1 declared, none eligible)` to
`(2 declared, 0 in that role, none eligible)`. `docs/DEFINITION-OF-DONE.md` criterion 4 quoted the
old text; so do D-057 and D-053 in this file. **The recorder has corrected the first and
deliberately left the other two standing**, because a D-record is a historical document and
rewriting one to match a later tree is how a record stops being evidence. Which means this file
knowingly carries two false blocks, marked nowhere except here.

**Two rows of the proposer table cannot be re-derived from this repository at all** — the two
proposers behind the Tier 0 `93.74 %` share are not in `PROPOSERS`, not in the frozen pool, and need
an external interpreter no test exercises. They are labelled as carried, and one round from now
nothing will remember they need an external environment unless somebody reads that entry.
---

## D-064 — The legend flag's cost on the arm nobody had mined is not a cost; and the runner that was supposed to have measured it was covering a third of the shipped configuration surface

**Status:** allocation discharged, arm spent once, coverage gaps closed for two runners and refused
for a third · **Amends:** D-047 (the allocation, and its loser clause), D-045 (its unclosed hole for
the legal genre only), D-039 (the "unmeasured cost" half of the shipping rationale is retired; the
"no uncontaminated structurally-capable corpus" half is untouched and is now the *whole* reason the
default is off), D-046 (its firing-count rule is now satisfied at full profile coverage) ·
**Evidence:** `shortform.sdu22_ae_legal_train.*` — `28` run ids;
`shortform.plod_*.{tight,spaced}.{general,biomedical}.*`; `bench/splits.toml`
`[[corpora.sdu22_ae_legal.reservations]]`; `docs/EVALUATION.md` ·
**No experiment number spent — experiment eleven is still free**

SDU-22 AE legal `train.json` is spent, once, through the declared door, by the workstream that owned
the read, with all three of D-047's conditions met. Re-derived by the recorder from
`bench/results.json`:

```
shortform.sdu22_ae_legal_train.<profile>.{baseline,legend} -- precision deltas, four cells each
  profile          SF exact   SF overlap   LF exact   LF overlap
  high_precision    +0.80       +0.03       +1.54       +0.53
  general           +0.81       +0.03       +1.55       +0.54
  biomedical        +0.66       -0.10       +1.61       +0.68
  SF exact recall  38.76 -> 45.91  against a ceiling of 55.04
  LF exact F1      70.43 -> 78.37
  corpus: 3,564 documents, 9,532 gold short-form spans
```

**Eleven of twelve precision cells rise and the single negative move anywhere on the arm is
`-0.10`.** No F1 falls. The rule fired: `688` legend pairs at `high_precision` and `general`, `703`
at `biomedical`, in `270` of `3,564` documents — this is a measurement, not a null. The phrase "the
legend flag is shipped with an unmeasured cost" is retired.

**The free ride was saved as D-047 required.** Experiment nine, the two-word bracketed short form,
wins at every profile — at `high_precision`, `+61` true positives and `-53` false positives on
short-form exact spans, on a corpus with `200` multi-token gold short forms where PLOD has none.
**It is still held.** Nothing is shipped on it.

### The second, separable finding, and it is a class rather than a rule

**A benchmark runner that does not cover the shipped configuration surface reports a slice under the
name of the whole.** `--spans` swept one profile of three. Swept across all three it reverses a sign
on PLOD-CW, the only held-out corpus here — and closing the gap exposed a sentence in
`docs/EVALUATION.md`, "it emits `12` predictions across the whole corpus and improves every field",
that was **already false against data sitting in `bench/results.json`**: on the pooled PLOD split at
the very profile the sentence was measured at, three fields fall under `tight` and four under
`spaced`. Nothing was checking.

**D-052's warning generalises, and this is the instance.** A ratchet counting numbers cannot see a
scope. "Improves every field" contains no number. Nothing turned red for it and nothing would have.

Firing counts are now known at every shipped profile on every corpus this repository reads:
`MED1250 0/0/0` on `401` separators — D-046's vacuity finding surviving at full coverage —
`PLOD dev 2/2/5`, `PLOD test 3/3/3`, `PLOD all 12/12/16`, `SDU-22 legal dev 83/83/88`,
`scientific dev 39/39/52`, `legal train 688/688/703`.

### The refusal, with its disposition (R14)

`bench/run_extraction.py` is still one profile of three and is **blocked on a named decision**:
whether `extraction.med1250.acronymkit` gains a profile segment or publishes three rows under one
name. That run id is the figure `README.md` leads the extraction section with; it is cited in three
documents; and `profile.med1250_test.*` already shows the three profiles differing by more than a
point of F1. **That is a decision about the flagship number's identity and it belongs in a record
rather than in a diff.** Two closed-experiment runners and the backronym runner are named in the
published coverage table with the same constant and are not fixed, for stated reasons.

### How it fails

**The spend bought a number on a corpus that cannot answer the question the flag is off for, and
D-047 said so in advance.** The legal split is UN institutional prose; its equation surface is `27`
separators of `1,063` on train and `0` of `138` on dev. The genre the risk is named for is still
unmeasured. Anyone reading "eleven of twelve precision cells rise" as "the equation risk is
measured" has repeated D-045's finding one corpus over. **The default does not move and this result
is not an argument that it should.**

**`-0.10` is quoted as "the worst move anywhere on this arm" and is not distinguishable from zero on
any principle the same workstream applied elsewhere** — it refused a `-2.23` on PLOD dev as three
false positives and did not compute the equivalent count for `-0.10`. The asymmetry is unresolved.

**The arm is contaminated the moment it is read, and it cannot be spent again.** If the legend
question ever needs an unmined arm on this corpus, there is not one. Scientific `train.json` is
unallocated and D-047 refuses first-come.

**The miss decomposition's bucket rule is the workstream's, not the audit's.** The `30`-character
window is the audit's; the four *ordered* buckets are not, and that ordering is the likely reason
its `=` bucket reads `131` on dev against the audit's `127`. The recovered column is
order-independent and is the load-bearing one.

**The coverage table is one reader's reading of source on one afternoon, on a tree four other
workstreams were editing, and nothing in CI asserts any cell.** Two runners appeared mid-round and
were deliberately left out of it. `check_claims` catches a stale number; nothing catches a stale
table.

**An assignment overrun, declared.** `tests/test_splits_manifest.py` was edited by that workstream
without being assigned it, because three tests encoded the pre-spend state and had to move with the
manifest. The edits were kept to those assertions, each test's stated intent preserved, and the
result mutation-tested in situ. The recorder judges this correct and records it as an overrun
anyway.

### Corrections owed on the manifest, one taken here

`[corpora.sdu22_ae_legal]`'s corpus-level `contamination_reason` ended "Only `train.json` is
unread", and `status` named only the dev runs. Both went false with the spend. They are corpus-level
fields, the reservation workstream was scoped to the reservation, and the workstream editing that
file this round was scoped elsewhere — so nobody owned them. **The recorder has corrected both, in
`bench/splits.toml`, and that is the only edit made to the governance file this round.**
`tools/splits.py --check` still prints "`3 reserved arm(s) -- no runner may open one without
declaring a spend`" above a list that now includes a `spent` arm, which opens without any
declaration; and `bench/corpora.py`'s `_sdu22_ae_source` docstring still says both train arms
refuse. Both are reported and not fixed.
---

## D-065 — The proposer pool is one algorithm on five corpora, the corpora that reward it were drawn around it, and the second half of that sentence is confounded and says so

**Status:** measured and published; no behaviour changed; `103` new run ids under `monoculture.*` ·
**Amends:** D-056 (its `93.74 %` is generalised off the Federal Register and shown to be a property
of the *pool*, not the substrate) · **Bears on:** D-048, D-051 and D-057's criterion 9, D-017
(PLOD's provenance is now read from the paper rather than from the dataset card), D-039 and D-047
(the largest recoverable sub-class of the blind spot is legend-shaped) ·
**Evidence:** `bench/run_monoculture.py`, `tests/test_monoculture.py`, `docs/EVALUATION.md` ·
**No experiment number spent — experiment eleven is still free**

**The monoculture is real and it reproduces off its original substrate.** On the Schwartz & Hearst
descendants alone, one implementation is `93.55 %` of the edge union on PLOD-CW and `93.99 %` on
SDU-22 scientific — within `0.19` and `0.25` points of D-056's Federal Register `93.74 %`, on
different substrates with a partly different pool. So `93.74 %` was a property of the pool, not of
the substrate.

**R13 is satisfied with a published matrix, not an assertion.** Pairwise overlap, Jaccard, share,
unique and union gain are saved per corpus on two units, and the full square matrix for PLOD-CW is
printed into `docs/EVALUATION.md` as command output. Two proposers are labelled decoration **in a
column**: `acronymkit GENERAL` and `HIGH_PRECISION` have union gain `0.00` on every corpus, from
`1,119` and `1,122` proposed edges respectively — they proposed plenty and none of it was unique.

**The blind spot has a size, on gold with an author arbiter.** Re-derived by the recorder from
`bench/results.json`:

```
monoculture.plod_all.gold.long_form.overlap.class
  gold long-form spans                                            1,804
  reached by the S&H family                              1,040    57.65 %
  unreached                                                764    42.35 %
  unreached AND alignable with a gold short form in the passage   34.98 % of gold
  reached once the independent proposers are added                79.60 %
  gold provenance: PLOS article Abbreviations sections, matched onto body text
```

The third figure separates the two Schwartz & Hearst commitments empirically: those pairs pass the
validator and are never offered by the candidate generator. **C1, the bracket, is the binding
constraint; C2, the alignment, is not** — and the two are now separable on evidence rather than by
argument.

Control, and it is the one that matters: on MED1250, `sh_family_recall_pct` is `86.41` and the
independent gain is `0.00`. **On the corpus these systems were built against, a proposer that cannot
be one of them is worth exactly nothing.**

### The independent proposer, and why its independence is a measurement

`shapecue` makes neither S&H commitment. Independence is argued three ways: by construction and
tested (it proposes a pair sharing no character with its own abbreviation, and proposes **nothing**
on `World Health Organization (WHO)`); mechanically on C1 —
`bracketless_edges_pct_shapecue` is `99.83` on PLOD-CW against a descendant maximum of `4.75` on any
corpus, re-derived by the recorder; and mechanically on C2, which the document names as the weaker
axis because most real abbreviations *are* alignable.

**The criterion the workstream built the runner around was killed by its own measurement.**
`sh_unalignable_pct` has a noise floor — descendants report surfaces their internal alignment never
saw, a truncation artefact — and it asks a sufficient indicator to carry a necessary claim. Replaced
as load-bearing by the C1 axis, which separates cleanly and whose separation is not an artefact of
what the corpora happen to contain.

### The premise that was checked instead of inherited

The brief asserted PLOD's gold is not pooled from these systems. The dataset card says only
"automatically annotated" — the exact shape of the NameGuess and GLADIS failures this project has
already paid for twice. Two fetches of the paper were needed; the second returned the verbatim
sentence about extracting short and long forms from each article's *Abbreviations* section, which is
the glossary the journal requires authors to submit. **Had the answer come back "scispaCy", the
deliverable would have had no corpus and that would have been the report.** A dataset card is not a
provenance: fourth door, same shape.

### How it fails

**The control corpus differs from the treatment corpus on two variables at once, and the workstream
killed its own headline for it.** MED1250 is abstracts; PLOD is article body text. Abstracts carry
no figure legends and no table footnotes, which is exactly where the un-proposed class lives, so
every number offered as evidence of *provenance* is equally consistent with *genre*. Separating them
needs article body text whose gold was pooled from S&H descendants, and nobody publishes one on
purpose. **That absence is itself a publishable result and is recorded as one, not as a to-do.**

**The independent proposer's coverage is post-hoc and its independence is not.** Its `585` unique
roster edges come from a rule written *after looking at the misses*, on a corpus that is `held_out`.
The independence claim is design-level and survives; the coverage number is not held-out evidence of
anything, and its short-form F1 beating every extractor is not a new finding — the one-line all-caps
rule already did that.

**PLOD's own authors report wrong annotation in one segment in twenty and missing annotation in more
than a quarter**, so every "unreached" figure has an incomplete denominator in an unknown direction.

**Family membership is a claim about mechanism, tested for three of seven rows and argued for four.**
The bracketless percentage is strong circumstantial evidence and is not a proof.

**`SDU AE legal, dev` is the row that spoils the pattern and nobody chased it** — `pyab3p` gains
`10.90` there, five times its gain anywhere else, and the shipped extractor's share drops to the low
end at `79.33`.

**The refusal, with its disposition (R14): no LLM proposer was built — permanent for the shipped
library, open as a corpus-construction route.** Non-deterministic, network-touching, cannot pass the
air-gap job, and decisively **not needed**: every deliverable was answered without one. The
reachability guard that would catch one being smuggled in exists and was mutation-tested red.
---

## D-066 — The sixteen-point deficit against the one-line all-caps rule dissolves and then reverses, and the whole reversal is one factor — measured under a metric that cannot see what the library actually claims

**Status:** measurement; no behaviour changed; `14` new run ids under `shortform_contest.plod.*` ·
**Amends:** D-049's framing of the `68.62` / `52.56` pair · **Affirms:** D-048 (the span scorer has
no slot for the edge), re-derived inside the new runner with a firing count ·
**Evidence:** `bench/run_shortform_contest.py`, `docs/EVALUATION.md`, `README.md` ·
**No experiment number spent — experiment eleven is still free**

The comparison was decomposed on a `2 x 2` of the two structural handicaps — PLOD annotates every
occurrence while `extract()` can only emit a *paired* short form (D-041), and `predict_all_caps` can
only emit an all-caps token. **The deficit is not shared between them.** Re-derived by the recorder:

```
shortform_contest.plod.all.* -- short-form exact F1, native offsets
  region              gold spans   acronymkit HIGH_PRECISION   allcaps      lead
  all                     2,869              52.56              68.62    allcaps +16.06
  caps                    2,105              54.98              78.38    allcaps +23.40
  definitional            1,323              85.73              75.13    acronymkit +10.60
  definitional_caps         979              88.66              86.56    acronymkit  +2.10
  test split, definitional:                  87.22              72.36    acronymkit +14.86
```

Removing the *baseline's* handicap alone makes it worse; removing *this library's* handicap alone
flips it. **The sixteen points were never a statement about either system — they were the corpus's
annotation convention measured against a pair-emitting extractor.** The brief's conditional, that a
surviving gap would be the most important open defect in the library, **does not fire**.

**The regions filter gold and predictions by the same predicate**, so precision inside a region is a
real precision and not a recall-only rescoring, and the filter does real work on one side only:
`1,115` of `1,119` acronymkit predictions survive `definitional` against `1,283` of `3,266` for the
baseline — and it still leaves the extractor ahead.

### The conclusion that undercuts the result, published in the same document

`bench.run_spans.SpanPrediction` has no slot for the edge. Replaying PLOD's gold with each
sentence's long forms rotated against its short forms produced **byte-identical `100.00` on all four
span metrics**, honest and rotated alike — with the firing count beside it, `342` of `1,351`
documents rotated and `1,054` pairs made wrong, both saved as fields on the run so the null can
never be read without them. **So `85.73` is not a defence of the extractor; it is a defence of its
short-form spans**, and a reader who quotes it as "acronymkit beats the baseline on extraction" will
still be wrong and will still find the number. Criterion 9 is untouched by this result.

### The replacement constraint on how W11 may be pitched

D-049 placed a constraint on W11 derived from the undecomposed comparison; it does not survive
decomposition in the form D-049 states. **This does not revive W11** — it removes one argument
against it and supplies none for it. The honest replacement: *the all-caps rule's advantage is
confined to gold the pair model structurally cannot address, so "we can emit unpaired short forms"
remains a capability claim and not a quality claim, and W11 must still be sold on the precision of
what it would add.* `README.md`'s bullet is amended; the corresponding passage in
`docs/notes/w11-emission-model.md` is **not**, and is now the last place asserting the old framing
without qualification.

### A premise inside the brief itself, checked

The brief cited "definition-of-done criterion 12". There was no criterion 12 — the requirement
described, a qualifier in the same table as the figure it qualifies, is criterion 5's clause. The
substance was complied with; the misnumbering was an inherited premise nobody had checked, arriving
in the instruction rather than in the tree. **This round's numbering of criteria 9 to 14 is recorded
in D-069, and it does not retrospectively make that citation correct.**

### How it fails

**The premise handed down was subtly wrong and only half of it was caught.** `52.56` is the
**native-offset** row; `bench/run_spans.py` says in its own docstring that headline rows go through
the string localiser "because scoring our own row through a privileged path would flatter it".
D-049 quoted the privileged row and the brief inherited it. The localised figures are `52.31` and
`85.32`. Both are published, and the main table was still built on the native row to stay comparable
with the quote — so somebody rebuilding this from the localised row gets a slightly larger raw
deficit and a slightly smaller reversal.

**"Scored, not diagnosed" is a claim about intent that nothing enforces.** D-049 permits PLOD to be
scored and forbids it being diagnosed. The predicates are corpus-side and were fixed before the
numbers were seen — and they were chosen knowing what a Schwartz & Hearst extractor does, which is a
weak form of the thing the rule exists to stop. No test would catch a future round adding a
`--misses` flag to this runner.

**Everything rests on one corpus and it is the wrong domain**, and the only replication available
(`test` against `all`) is not independent, because `test` is a subset of `all`.

**The `definitional` region is a proxy for "definitional" and is not one.** It admits parenthetical
*mentions* nobody should extract and excludes bracket-free definitions such as the legend form —
which is nearly empty today only because `legend_syntax` ships off. **The published number is
specific to the shipped configuration in a way the region name does not advertise**, which is
D-064's class arriving inside a different runner in the same round.

**The four external baselines have no `definitional` column and the firing count is stated as zero
rather than dashed.** None imports under the interpreter on PATH. The specific unanswered question
is whether `pyab3p`, which beats this library on MED1250, also loses to it in that column — so the
cross-corpus ordering claim in `docs/EVALUATION.md` still rests on the undecomposed comparison.

**The runner's own gate was demonstrated capable of failing exactly twice**, and the `caps` predicate
has no gated counterpart to check against and is guarded by nothing but reading.
---

## D-067 — The amendment that closed criterion 2 was refuted by functions the amending round had already written: `align` carries an accuracy number, `synthesize` never will

**Status:** measured and published; the criterion-2 amendment is **withdrawn** ·
**Amends:** D-054 (the amendment), D-057 (criterion 2's verdict moves from "met, AMENDED" to
"partly met") · **Evidence:** `bench/run_backronym.py --arm accuracy`;
`backronym.{med1250,sdu21_ad}.accuracy`; `docs/EVALUATION.md`; `docs/DEFINITION-OF-DONE.md`
criterion 2 · **No experiment number spent — experiment eleven is still free**

D-054's central word was *cannot*, and it is false for half the subsystem. On a pair whose
componentwise-earliest and componentwise-latest complete alignments read out the same words, every
complete alignment reads out those words — so the pair has exactly one reading that no annotator,
convention or opinion selected. `earliest_fit` and `latest_fit` are functions **D-054's own round
wrote**, and used only to count the complement. Re-derived by the recorder:

```
backronym.{med1250,sdu21_ad}.accuracy.all
                       MED1250    SDU-21 AD
  pairs                  1,221        2,308
  feasible               1,070        2,261
  decidable                671        1,300      (54.95 % / 56.33 % of pairs)
  EXACT MATCH           98.66 %     100.00 %
  accuracy bound over all feasible pairs   [61.87, 99.16]   [57.50, 100.00]
  interval width          37.29        42.50
  returned_incomplete        9            0
  unadjudicable            203 (18.97 %)  31 (1.37 %)
```

**The interval is the deliverable, not the point estimate.** Its width is the underdetermined share
expressed in accuracy units, which is what makes its size legible: an accuracy figure whose
uncertainty spans thirty-seven points exists and is not, on its own, an answer to "does this
subsystem work".

**`synthesize` cannot carry one, ever.** A target word with no source phrase has no correct
expansion, so accuracy there is *undefined* rather than unmeasured. That half of criterion 2 is
closed as **permanently unmeetable with the reason**, rather than left open — R14 applied to a
refusal that is genuinely permanent.

### The collision inside the existing evidence, which is the sharpest thing here

D-054 re-scored its fourteen feasible-but-incomplete MED1250 pairs with the library's **own**
`Scorer`, found all fourteen "objective_preferred" with zero search shortfalls, and concluded no
defect. **Nine of those fourteen are pairs whose correct reading is unique and was not returned.**
Same rows, opposite verdict, and the difference is which arbiter was consulted — the tautology the
runner's own docstring says it exists to avoid, reappearing one section later.

### Corrections this forces on the published record

The judge-shaped hole is much smaller than D-054 states. `37.29 %` and `42.50 %` is the share the
*constraint* does not settle; the share nothing settles is `18.97 %` and `1.37 %` of feasible pairs.

And word-level determinacy is **unsound**, demonstrated against the shipped unmutated aligner:
`'AA' <- "alpha acid alpha"` has earliest and latest both reading *alpha alpha* while `align`
returns *alpha acid*. So the existing published `backronym.*.alignment.all.underdetermined_n`
figures are lower bounds in a stronger sense than their document states. A provably sound
position-unique variant ships beside the headline at `98.11 %` and `100.00 %`.

### Guards, with firing counts, because every one of these is a zero

`returned_other_words_n` is `0` and executed on **all `1,971` decidable pairs**, not only the misses,
and was demonstrated firing on a constructed pair. `convention_cross_check_conflict_n` is `0` over
`1,505` executions — `1,505` agreements out of `1,505` is the strongest independent evidence the
uniqueness gold is right on real data. `convention_conflict_n` is `0` over `1,126` applicable pairs
and fires at `196` and `930` under a second-best-candidate mutation. **`returned_nothing_n` is `0`
and was never demonstrated firing** — an honest gap, stated. The metric itself is not one that
cannot fail: it reports nine failures on real data with no mutation, and drops to `1.94 %` and
`0.00 %` under mutation.

### How it fails

**The number is high and the high part is the easy part.** `98.66 %` and `100.00 %` are over the
subset where the constraint already forces the answer. A reader who wants "how good is this at
aligning acronyms" gets a bound thirty-seven points wide and no point estimate inside it. Publishing
the interval is the honest answer; calling it an accuracy number that answers a question nobody
asked is a criticism that lands.

**On decidable pairs the metric collapses to one question about weights, not search.** All nine
failures are `returned_incomplete` — the objective spent letters covering more words rather than
take the unique complete reading — so on the shipped configuration `exact_match_pct` is very nearly
"does `unmapped_penalty : delta` come out the human's way", measured `671` times.

**The gold is this library's own constraint restated.** Reject the constraint and you reject the
gold; the eligibility filter is *inside* it, so widening `token_ineligible` moves the feasible set,
the decidable set and the figure together. One of the nine misses has a likely human reading that is
out of order and therefore inexpressible under the constraint at all.

**Both corpora are `tuning, contaminated`, and unlike D-054's properties this actually matters.**
D-054's defence — no held-out split makes a *property* more trustworthy — does not transfer to an
accuracy number. The figure that most needs a strong label carries the weakest one.

**Seven new top-level objects ship with no unit tests**, because `tests/` was not that brief's file.
The exact cases are written down and verified by hand and should be pasted in next round.

**And nothing in `src/acronymkit` was changed.** The nine misses are the objective doing what its
weights say — a design trade, not a bug, and R6 forbids changing it on a measurement taken in the
same round. **It is a lever with a number on it now**: nine real MED1250 pairs where a caller gets a
reading no reader would give. Pulling it invalidates this table and moves forward generation's
numbers too.
---

## D-068 — The first measured error rate this project has on its own reporting: `5` of `24` sampled claims are not true, the failure rate is `5x` higher on claims that needed a command run, and most of the failures are staleness rather than error

**Status:** measured; first-class finding, not an appendix · **Amends:** nothing; **establishes** a
baseline every future round's reporting will be read against · **Evidence:** the R15 sampled pass,
seed `20260825`, `24` of `187` submitted claims, checked against running code rather than against
any report; two of its verdicts independently re-derived by the recorder ·
**No experiment number spent — experiment eleven is still free**

R15 required every workstream to submit at least twelve **non-load-bearing** checkable claims,
uncurated, including the ones it was least sure of. A seeded sample was drawn and each was attacked.

```
24 checked | 19 TRUE | 4 FALSE | 1 MISLEADING | 0 UNCHECKABLE
  not-true rate      5 of 24    20.8 %
  strictly-false     4 of 24    16.7 %
```

**The rate is plausible and it is not zero, which is the first thing to check.** A pool curated for
safety shows up as an implausibly low rate; this one does not.

### The two decompositions matter more than the headline

**By kind of check.** The thirteen claims settled by one file read or one stored-number lookup
failed `1` in `13` — `7.7 %`. The eleven that needed a command run or a multi-step derivation failed
`4` in `11` — `36.4 %`. **The round-level error rate is therefore a function of the sampler's mix,
and `20.8 %` is a lower bound for the claims that required judgement.**

**By failure mode.** Three of the five are **staleness** — a count that was probably right when its
workstream measured it and went wrong because the tree kept moving under eight concurrent
workstreams. Two are hard errors independent of drift, and one is an unreproducible wall-clock
figure. Excluding staleness the rate is `8` to `13 %`; counting it, `20.8 %` stands. **This record
counts it**, because R15's own framing is that a claim a stranger cannot reproduce is not a claim.

### The two hard errors, both confirmed independently by the recorder

**A count anchored to the wrong commit.** One workstream published `bench/results.json` holding
`282` runs at `6cc9a01`. It holds `278`; `282` is the count at `a62f99a`. The arithmetic in that
sentence was internally consistent and the anchor was wrong — **the sentence was re-checked against
the previous sentence rather than against `git show`**, which is exactly the compression failure the
mandate warns about.

**A claim already false on its own author's tree.** One workstream named three test modules calling
`pytest.skip(..., allow_module_level=True)`. The recorder ran the re-derivation that
`.github/workflows/ci.yml` itself prescribes:

```
grep -l allow_module_level tests/*.py
  tests/test_build_gold_corpus.py   tests/test_check_claims.py   tests/test_gate_manifest.py
  tests/test_monoculture.py         tests/test_splits_manifest.py                    -- five
```

Two of the five landed during this round, one of them from the very workstream making the claim.
**And `ci.yml`'s comment beside that command still says "which names exactly the three files
above"** — a file refuted by its own recipe, sixty lines from its own comment describing this exact
rot. That is D-062's cross-copy mechanism appearing for a fifth time, inside the round that named it.

### The staleness finding, and why it is the useful one

The most-repeated failure is a number that was true when written. `docs/CLAIMS-LEDGER.md` published
`ALL 262 1480 1742`; the sampler measured `262 1483 1745`; the recorder measured `262 1494 1756`.
Three readings, one session, one tree, and **only the ratcheted column held.** The lesson generalises
past this round: **a present-tense count about a shared tree, published with no commit and no run id,
is not a claim a stranger can check** — and this project's discipline for that (cite a run id, or
fence and name the command) exists precisely because of it, and was not applied to any of the three.

### How it fails

**The sample is not uniformly hard and the rate is diluted by that.** Eight of the twenty-four are
one grep or one dictionary lookup from certain. `36.4 %` on the execution-shaped subset is the
number worth carrying forward.

**One verdict is a judgement call that moves the headline.** The `MISLEADING` grade was given to a
claim whose structural half reproduced exactly and whose wall-clock half did not — six timed runs
spanning `8.26` to `8.94` seconds against a quoted `11.352`, no overlap. A stricter grader calls it
FALSE and the strictly-false rate becomes `20.8 %` too.

**One `TRUE` deserves an asterisk and the sampler flagged it.** A measured zero that is a
*structural* impossibility — a filter never reached because an earlier filter excludes the corpus —
is literally true and reads as evidence the filter was exercised there. That is the same shape as
D-063's own R12 disclosure, arriving as a sampled claim.

**The sampler measured a tree that moved while it measured.** Two files changed inside the same
minute as its checks. That implicates three of its five failures directly, and it declined to curate
them away. A reader who wants the harsher-on-the-sampler reading drops those three and reads `8` to
`13 %`; a reader who holds that reproducibility is the standard reads `20.8 %`. **Both numbers are
published and neither is hidden behind the other.**

**And the sampler's own verdicts are claims.** The recorder re-derived two of the four FALSE
verdicts against running code and both held. The other two, and all nineteen TRUE verdicts, are
carried on the sampler's word. **The error rate of the error-rate measurement is unmeasured**, and
one round of this is a baseline rather than a trend.
---

## D-069 — The definition of done, third sweep: fourteen criteria, a renumbering that breaks four cross-references on purpose, and the recorder's own account of what was verified and what was carried on trust

**Status:** swept and reconciled · **Amends:** D-051 and D-057 (the criteria are renumbered; the
criterion those records call "the ninth" is criterion `10` from this round on), D-057's verdicts on
criteria 2, 3 and 4 · **Evidence:** `docs/DEFINITION-OF-DONE.md`; the six gates re-run on the tree
as it is left; D-059 to D-068 above · **No experiment number spent — experiment eleven is still
free, and see the reservation below**

### The renumbering, which is a defect I am creating deliberately

Mandate II adds six criteria and numbers them `9` to `14`. This document already carried a
**proposed** ninth — "the two tasks the README leads with can be adjudicated by a corpus this
project did not tune on" — which is not one of the standing eight and which four places cite **by
number**. Mandate II's tenth is the same question restated with a costing clause, so the two merge.

**Resolution: the mandate's numbering is adopted. The criterion formerly cited as "criterion 9" or
"the ninth criterion" is criterion `10` from this round on.** These four cross-references are now
stale and are **not** being rewritten, because three of them are historical records:
`docs/AUDIT-2026-08.md` line `23`, `docs/DECISIONS.md` D-051 and D-057, `docs/EVALUATION.md` line
`688`. A renumbering note ships at the head of `docs/DEFINITION-OF-DONE.md` naming all four. This is
the stale-sentence class D-062 measured at `11.6 %`, created on purpose, in the round that measured
it — and the alternative was renumbering six new criteria to avoid a collision the mandate itself
had already resolved.

### The fourteen verdicts

```
docs/DEFINITION-OF-DONE.md, third sweep -- a reading, not a measurement
   1  abstention                       met with qualification   unchanged (D-044)
   2  every subsystem scored           PARTLY MET               amendment withdrawn (D-067)
   3  everything gated                 not met, better instrument  policy + quota + classification
   4  splits.toml governance           met, strengthened again  third role; a spent arm; new residual
   5  non-biomedical + ceiling         met with qualification   unchanged; discipline applied twice more
   6  extension points                 met                      unchanged; NOT re-derived this round
   7  clean-report-data-loss           met                      unchanged; NOT re-derived this round
   8  do-not list grew                 met                      seven new items this mandate
   9  every gate mutation-tested in situ   NOT MET              0 of 36 carry evidence (D-061)
  10  an empty row filled, or costed   not met, now costed      was "criterion 9, proposed"
  11  monoculture measured             MET                      union gain 32.04 % on PLOD-CW (D-065)
  12  short-form detection vs allcaps  MET                      reversal on comparable gold (D-066)
  13  deferred ledger policy + rate    met, one observation     trajectory is two rows (D-059)
  14  a second reader exists           MET, and it is small     no gate enforces it (D-060)
```

**Three criteria closed this round and two of the three closed against the workstream that opened
them**, which is the outcome this sweep exists to make visible. Criterion `2` went the other way:
D-057 closed it by narrowing, and the narrowing's stated reason turned out to be false for half the
subsystem, so it is re-opened as **partly met** — a criterion may be closed by being narrowed, and
this is what it costs when the narrowing is wrong.

**Criterion `14` is met and it is small.** "A second reader exists, in some form" is satisfied by a
policy document and one performed pass. Nothing enforces it, and the wording is exactly the kind
that closes by being modest about itself. That is stated in the verdict column rather than in a
footnote, which is house style and exists because criterion `2` closed that way once already.

**Criterion `9` is the one that will be argued about.** The register, the harness, the scheduled
workflow and `51` tests all ship, and the count that matters reads `0 of 36`. Under R11 the verdict
cannot be anything but **not met**, and a reader who says "the mechanism is the hard part" is making
a real argument that R11 was written to refuse.

### Reconciliation: what collided and what did not

**No D-number collisions.** All nine workstreams declined to pick one and `docs/DECISIONS.md` was
untouched at hand-off — verified by `git status`, not by their word. Numbering here is by
dependency: the rules under which numbers are published (D-059), then the scope of the instrument
that checks them (D-060), then what a green gate means (D-061), then what the type checker covers
(D-062), then the governance vocabulary (D-063), then the measurements, then the error rate.

**One finding was claimed twice and is booked once.** The staleness of `docs/CLAIMS-LEDGER.md`'s own
table is reported by the sampled pass and is a property of the ledger workstream's deliverable; it
is recorded in D-059 with the sampler's reading and the recorder's third reading beside it, and
D-068 carries it only as an instance of the class.

**Two workstreams reported the same underlying defect from opposite ends** — a runner reporting a
slice under the name of the whole (D-064) and a region proxy that is specific to the shipped
configuration (D-066). They are the same shape and each record points at the other.

**`experiment eleven` is free, and that is not the whole answer.** Verified by grep rather than
assumed: seven occurrences across `docs/DECISIONS.md` and `docs/notes/w11-emission-model.md`, none
of them spending it — five assert it is free, one is the naming-hazard note distinguishing it from
workstream W11, and one is a **conditional reservation**. Nine reports re-derived the free half
independently. **But D-039 has reserved it**: its revert criterion says that if MED1250 precision
moves at all under the legend flag, the revert is logged as experiment eleven. The number is unspent
*and* spoken for. Anybody spending it on something else should say so against D-039 first, and no
round so far has noticed that clause while reporting the number free.

### What the recorder verified, and what was carried on trust

**Verified against running code, one load-bearing claim per workstream, on the tree as it is left:**
`tools/gates.py --check` printing `36` gates across `21` environments in `5` workflow files and
`0 of 36` in-situ (D-061); `ROLES`, `NEVER_HEADLINE_ROLES` and an empty `UNREGISTERED_READERS`
imported live, and `--check` reporting `9 corpora, 3 reserved arm(s), 0 problem(s)` (D-063); the
monoculture class table and the independence percentage read out of `bench/results.json` (D-065);
the `definitional` region's `85.73` against `75.13` and the pairing-blind firing counts (D-066); the
backronym accuracy record in full, both corpora (D-067); the twelve legend precision cells, the
two-word counts, the corpus totals and `state = "spent"` in the manifest (D-064); `python -m mypy`
reporting `75` source files (D-062); the claims gate's ratchets, trajectory line and `--classify`
table (D-059); and **the claims-gate blind spot reproduced by mutation with a positive control**
(D-060). The six gates were re-run whole.

**Carried on trust, and named because a recorder who pretends otherwise is this role's failure
mode:** every mutation ledger reported by a workstream, including all eight of D-063's and all
thirteen of D-061's; the `4f812e1` and `a62f99a` exports behind D-061's green-to-red finding; the
cold re-fetch of `30` Federal Register documents and both its demonstrated failure branches; the
`click 8.4.2` MYPYPATH reproduction; the timing of D-060's cold-read pass; every figure in the
`docs/EVALUATION.md` sections written this round that is not one of the run ids listed above; and
`19` of the `24` sampled verdicts in D-068. **I re-derived two of the sampler's four FALSE verdicts
and no TRUE ones**, which is the weakest part of D-068 and is stated there.

### How it fails

**Every figure in every record above is inside a fenced block or a code span, and D-052 is explicit
that fencing is mechanically indistinguishable from hiding.** That was done because
`docs/DECISIONS.md` is grandfathered onto a deferred ledger that may not grow, so the discipline
that keeps the gate green is the same discipline that removes these numbers from its view. **The
recorder's own records went in under a rule that is, to the tool, identical to concealment.** The
only thing separating them is this sentence, which nothing checks. That self-implication is house
style and it is load-bearing: the day it stops being written down, the fencing is just hiding.

**Nothing in CI asserts any of the fourteen**, which is unchanged from two sweeps ago and is still
the largest weakness of the page.

**Criteria `6` and `7` were not re-derived this round.** Their verdicts are carried from D-057. The
page claims every verdict is re-derived; for two of fourteen, this round's is not, and the table
says so rather than letting the claim stand.

**Nine of fourteen read met, and that is the highest this page has ever read, in the round that also
measured a `20.8 %` error rate on the project's own reporting.** Those two facts are in tension and
a hostile reader should put them side by side. The defence is that four of the nine were closed by
criteria that are modest about themselves — `11`, `12`, `13` and `14` each say "measured",
"published" or "exists", not "good" — and the criteria that ask for something hard (`3`, `9`, `10`)
are all open. **A definition of done whose met-count rises when six new criteria arrive is a
definition of done that was scoped by the same people it grades**, and that objection is not
answered here.

**And the whole sweep was taken on a tree eight workstreams had been editing**, uncommitted, with
`34` modified and `11` untracked paths at hand-off. Every command in this record was re-run at the
end against that tree, and none of it is anchored to a commit.

---

## D-058 — The round that shipped W10 also reddened `14` of `17` CI jobs, and both causes were invisible to every local gate

**Status:** fixed · **Amends:** D-052 (the gate's coverage), the `[tool.mypy]` rationale in
`pyproject.toml` · **Evidence:** run `32794319528`; `python -m mypy --python-version 3.9`;
`python -m pytest tests` with `data/` moved aside · **No experiment number spent** —
**experiment eleven is still free**

Five workstreams and a recorder landed green on the author's machine and broke almost every cell of
the matrix on push. Neither cause was a mistake in the work; both were **properties of the local
environment that no gate in this repository models**. That is the finding worth keeping, and it is
the same shape twice.

### Cause one: three tests needed a corpus that CI does not vendor

`tests/test_splits_manifest.py` grew controls showing the new reservations are arm-scoped — that an
arm carrying no reservation is *not* refused by one. The controls asserted on a returned path:

```python
assert corpora._sdu22_ae_source(None, "legal", "dev").name.endswith("legal_dev.json")
```

`data/` is fetched, never committed. On a runner that call raises `SystemExit: missing ...` before it
can return anything, so the control failed for a reason that has nothing to do with what it tests.

**The docstring above it already said the fix.** It read: *"The refusal fires inside
`_sdu22_ae_source` before the path is resolved, which is why this test can assert it without opening
the file."* The prose described a test that needed no data; the code underneath needed data. The
controls now assert on the filename, which both outcomes name — the resolved path when the corpus is
present, the fetch refusal when it is not — and assert positively that the refusal was **not** the
reservation. Verified in both environments: green normally, and green with `data/` moved aside.

### Cause two: a `3.10`-only stdlib call, in a package whose floor is `3.9`

`Path.write_text` grew a `newline` parameter in `3.10`. `requires-python` is `>=3.9`. Five calls
shipped. They pass `ruff`, pass `mypy`, pass the suite on `3.13`, and fail only on the `3.9` cells.
Replaced with an explicit `path.open(..., newline=...)` helper, which every supported interpreter
has. The endings are not cosmetic: a pinned digest is taken over the normalised text, so a CRLF
checkout writing CRLF would change every hash and make the corpus look un-refetchable.

### The reason cause two could exist was a stale comment that had already changed a setting

`[tool.mypy]` set `python_version = "3.10"` against a `requires-python` of `>=3.9`, and justified it
at length: mypy had *dropped* `python_version = "3.9"`, printed `Python 3.9 is not supported (must be
3.10 or higher)`, and silently used the running interpreter's typeshed — so the override was the
honest choice, a checker saying plainly which version it models.

Re-tested against the pinned mypy, `1.19.0`, rather than assumed:

```
$ mypy --config-file <python_version = 3.9> probe.py
error: Unexpected keyword argument "newline" for "write_text" of "Path"  [call-arg]

$ mypy --no-incremental          # with python_version = "3.9", real tree
Success: no issues found in 40 source files
```

No warning. `3.9`'s typeshed is used. The tree is clean at the floor, so the `type: ignore` collision
that forced the move has been resolved elsewhere since. **The setting bought nothing and cost the
floor, and it names the exact defect the moment it is restored.** Floor restored; both copies of the
stale claim — one in `[tool.mypy]`, one in the dev-dependency pinning rationale — retired in place
rather than deleted, because a wrong sentence in a config comment is not decoration. This one
changed a setting, and the setting let a defect ship.

This is the second time in two rounds that a prose claim about a tool's configuration went false and
nothing turned red — the first being the `socrata` entry's note that `tools/check_claims.py` does not
scan `bench/splits.toml`, corrected in the same commit. **A ratchet counting numbers cannot see a
number-free assertion about what a tool does.** No mechanism is proposed here; the pattern is
recorded because two instances in two rounds is a shape, not a coincidence.

### What is not done, with its cost measured rather than guessed

Restoring the floor helps `src/acronymkit` and **does not close the hole that broke this build**.
`files` is `src/acronymkit` only, so `tools/` — where all five bad calls were — is unchecked at any
version. Extending `files`:

```
$ mypy tools bench
Found 51 errors in 14 files (checked 31 source files)
```

That is real work and its own decision, not a line to slip into a version bump. Until it is taken,
the `3.9` floor is modelled for the shipped library and enforced for everything else only by the
`3.9` cells of the test matrix — which is what caught this, three minutes after it could have been
caught locally for free.

### Second red round: the real reason for the `3.10` floor was neither the comment's nor mine

Restoring the floor turned `15` of `17` jobs green and reddened `Lint and type-check` in a way that
had never appeared locally:

```
click/utils.py:310: error: Pattern matching is only supported in Python 3.10 and greater  [syntax]
Found 1 error in 1 file (errors prevented further checking)
```

At `3.9` mypy follows imports into installed third-party *source*, and current `click` uses `match`.
It is a hard stop — `errors prevented further checking` — so the run dies on a dependency's syntax
rather than on ours. **It did not reproduce locally because the resolved `click` there is `8.1.8`,
which predates the `match`.** So the floor override was load-bearing after all, for a third reason:
not the one its comment gave, and not the typeshed collision I found when I removed it.

This is the same class as the linter-pinning note a few lines above it in `pyproject.toml` — a
floating dependency deciding whether the build passes — and that note now reads as advice its own
file did not take.

Fixed with `follow_imports = "skip"` for `click.*`, which keeps the floor for our code and treats
`click` as `Any`. **Verified against the version CI resolves rather than by analogy**: `click 8.4.2`
installed to a scratch target and put on `MYPYPATH` reproduces the error at the same line, `310`, and
the override clears it while the tree stays clean. The cost is that calls into `click` are no longer
type-checked; `src/acronymkit/cli.py` imports it inside a function, so the surface is one optional
path in one module.

### `EXPECTED_NON_PASSING` lost both of its file-keyed entries

The installed-suite job also failed, because the new test file executes a `tools/` script at module
level and `tools/` is no part of an installed distribution. The obvious fix was a third name in
`EXPECTED_NON_PASSING`. **That list's own comment argues against it**, and it argues from a
measurement: an entry is keyed on the FILE, so while a name sits there the job cannot see a second
defect anywhere in it — demonstrated by reintroducing a real breakage into a listed file and getting
a run identical to a clean one. It closed by calling that *"the argument for shrinking the list, not
for trusting it"*.

So the list shrank instead. All three files now carry `pytest.skip(..., allow_module_level=True)` on
the one named condition, placed **before** the load — a decorator cannot help, because marks are
consulted at collection and a module body runs at import, which is the lesson of the fifth historical
breakage. A skip on one condition absorbs that condition and nothing else, so any other error in
those files now reaches the job. Both names are deleted; the remaining entries are node-keyed and do
not carry the blind spot.

Verified by running the suite with `tools/` and `bench/` both moved aside: `4348` passed, `112`
skipped, **zero collection errors**, against a floor of `4000`.

### What this incident says about the local gates, stated plainly

Three defects shipped in one round. Every one was invisible locally for the same structural reason —
**the developer machine differs from the runner in ways nothing in the repository asserts**: it has
`data/`, it has `tools/`, it resolves an older `click`. Two rounds of CI were the instrument. The
suite-with-`data/`-moved-aside and suite-with-`tools/`-moved-aside checks used here are ad-hoc shell
moves, not gates; making either a gate is not done, and until it is, the runner is still the first
place these are caught.


### Third red round: the sdist shipped a gate it could not satisfy, for the fourth time, and hid `74` tests doing it

`Build distribution` had been *skipped* in both earlier rounds — an upstream job failed first — so its
first actual run this round was its first look at any of the work. It failed inside the extracted
tree, and the gate named its own problem:

```
scanned 59 files, found 1656 claim-shaped numbers (1 scan target(s) absent: bench/splits.toml)
deferred ratchet: 284 of 316 budgeted across 11 file(s)
1 file(s) break the value-matched ratchet:
  bench/splits.toml
```

D-052 added `bench/splits.toml` to `SCAN_GLOBS`. `MANIFEST.in` did not ship it. So the distribution
carried a checker that could not pass — **green in a checkout by construction, because every scan
target is present there.** `MANIFEST.in`'s own comment already recorded three instances of this exact
shape: `bench/results.json`, then `data/LICENSES.md`, then a fixture. This is the fourth, and the
recorder had listed it as a known gap the round before it became load-bearing.

Shipped, and then the rule was **derived rather than remembered**:
`tests/test_packaging_manifest.py` now walks `check_claims.SCAN_GLOBS`, expands each against the
tree, and requires a `MANIFEST.in` line for every file it finds — plus an error for a glob matching
nothing, since a scan target naming no file is a gate reading nothing. Mutation-tested rather than
assumed to work: deleting the new manifest line fails the guard with
`MANIFEST.in does not ship them ... ['bench/splits.toml']`, and restoring it goes green.

### Shipping that one file un-skipped a module that had never run there

`tests/test_splits_manifest.py` opens with
`pytest.mark.skipif(not SPLITS.is_file(), reason="not a source checkout")`, and `SPLITS` **is**
`bench/splits.toml`. While that file was unshipped, the mark skipped the **entire module** in the
extracted-tree job — every test in it, silently, for as long as the file has existed. The build job
was green because it was not looking.

Shipping `splits.toml` turned the module on and surfaced `14` tests that reach through the manifest
into `bench/corpora.py`, which the sdist deliberately does not ship and should not. Those `14` now
carry a narrow `needs_corpora` mark; the module reports `74 passed, 14 skipped` in the extracted tree
where it previously reported nothing at all. **The narrow mark is the whole point** — a module-wide
skip is what hid these, and replacing one blanket with another would have kept the rest dark.

Whole sdist, built and run: `4604` passed, `140` skipped, zero failures, zero collection errors.

### The pattern across three rounds

Four defects, one shape: **a check that cannot fail where it is run.** The claims gate cannot fail in
a checkout that has every file it scans. The suite cannot fail on a machine that has `data/` and
`tools/`. The type checker cannot fail against a `click` that predates `match`. The build job could
not fail while an upstream job kept it skipped, and a skipped module cannot fail at all. **Each was
found by the one environment that differs, and in every case the environment was CI rather than a
gate.** Two of the four are now derived checks that fail locally; the other two are not, and that is
recorded above rather than implied.


---

## D-057 — The definition of done, second sweep: one criterion closes by amendment, one gets worse by being measured, and the flagship gap now has a costed route

**Status:** swept · **Amends:** D-051 (criteria 2, 3, 4 and the ninth) ·
**Evidence:** `docs/DEFINITION-OF-DONE.md`; `python tools/check_claims.py`;
`python tools/check_claims.py --residue`; `python tools/splits.py --check`;
`backronym.*` in `bench/results.json`; D-052 to D-056 below

D-051 read the criteria together for the first time and left three open. Five workstreams landed in
one round and three of the open verdicts move. **Two of the three move in the direction the sweep is
built to make visible: one closes only because the criterion was made smaller, and one gets worse
because a blind spot was measured rather than because anything regressed.**

```
docs/DEFINITION-OF-DONE.md, re-derived for this record -- reading, not a measurement
  1  abstention                  met with qualification   unchanged (D-044)
  2  every subsystem scored      met, AMENDED             the fifth carries properties, not accuracy
  3  everything gated            NOT MET, worse evidence  the gate now counts what it cannot check
  4  splits.toml governance      met, strengthened        reservations validate and refuse a read
  5  non-biomedical + ceiling    met with qualification   unchanged
  6  extension points            met                      unchanged
  7  clean-report-data-loss      met                      unchanged
  8  do-not list grew            met                      unchanged
  9  headline corpus per task    NOT MET                  first instrument built; premise refuted
```

### Criterion 2 closes because the criterion shrank, and that is written on the face of it

D-051 offered two routes and said inventing a number would be worse than the open verdict. D-054 took
the second — properties and coverage for the backronym subsystem, with an explicit refusal to call
any of them accuracy — and the criterion is now:

> Four of five subsystems carry an accuracy number. The fifth — backronym synthesis and alignment —
> carries constraint-satisfaction, coverage and underdetermination figures, and **cannot** carry an
> accuracy number, because scoring a backronym requires a judgement no corpus records and this
> project has no judge.

**This is a met that is smaller than the one it replaces, and the page says so in the verdict column
rather than in a footnote.** The reopening condition ships with it: a published backronym gold, or a
judge whose agreement against humans is measured before any figure it produces is quoted.

### Criterion 3 went backwards, and that is the correct result

D-052 widened the gate's coverage and the debt it revealed is now counted rather than absent. Nothing
regressed; the instrument got better and the reading got worse, which is the outcome a coverage sweep
is supposed to produce and the one most likely to be argued away next round.

```
python tools/check_claims.py --residue, run for this record -- command output
  numbers on the deferred ledger              316   across 11 files
  ... matching NO measurement at all           76
  numbers no arming rule reaches            1,468
  value-matched ratchet                        71   across 4 files, unmoved
```

Two of D-051's three named coverage gaps are closed — `CHANGELOG.md` and `bench/splits.toml` are
scanned — and the third is answered by a different mechanism than the one proposed, because widening
proximity could never have reached the figure that motivated it. The clause **zero un-gated figures in
user-facing prose** is further from true than it looked, and it is further from true *by measurement*.

**One new counter-example belongs on this criterion and is booked here rather than under the
workstream that produced it.** D-055 moved two resource byte counts out of prose and into code spans
so the gate would stop firing on them. The reasoning is sound — they are properties of shipped files
and no runner measures a file size — and the effect is still that two published figures left the
gate's view by an author's choice. That is the shape criterion 3 exists to catch, and it now has one
instance inside the same round that improved the gate.

### Criterion 4 is met more strongly than it was, and its residual moved

Reservations are a validated structure with an accessor that raises, and two readers call it. Both
halves of D-051's evidence still hold, and one line of its fenced output is now stale:

```
python tools/splits.py --check, run for this record -- command output
  bench/splits.toml: 8 corpora, 3 reserved arm(s), 0 problem(s)
  sdu21_ad:test              allocated    D-043
  sdu22_ae_legal:train       allocated    D-047
  sdu22_ae_scientific:train  unallocated  D-047
```

D-051's residual — both SDU-22 AE entries carrying a `status` string saying they were not yet scored —
has been corrected in the manifest and is retired here. **A new residual of exactly the same class
replaced it, in the same file**, and it is recorded below rather than fixed, because that entry was
not this round's file.

### Criterion 9 did not move, and for the first time it is refused on evidence rather than on absence

`headline_capable('extraction')` and `headline_capable('disambiguation')` both still return empty and
`--check` still prints both gaps. What changed is that the first instrument capable of producing an
edge corpus exists, has been run end to end, and has reported that the substrate chosen for it does
not supply the arbiter the plan was costed on (D-056). **The gap is now costed rather than merely
open**, and the cost is five conditions, none of which this project can meet alone.

### How it fails

Nothing in CI asserts any of the nine, which is unchanged and is still the largest weakness of the
page. Criterion 2's met rests entirely on an amendment written in the same round by the workstream
that benefits from it, and the disagreement worth having is whether a criterion may be closed by being
narrowed — this record says yes when the narrowing is published in the verdict, and a reader who says
no is reading it correctly. Criterion 3's new figures were produced by the same tool whose coverage
they describe, so they are circular in the way D-052 states about itself. Four verdicts were taken
against a tree five workstreams were editing in one session, and the suite total moved repeatedly
inside it. And the sweep is again one reader on one day: `check_claims` catches a stale number and
nothing catches a stale sentence — this round found two of those, both in files nobody was assigned.

---

## D-056 — W10 built the instrument, ran the pilot, and the corpus is NOT registered: `ROLES` cannot say what it is, and no entry beats a comfortable one

**Status:** pipeline shipped, pilot run · **no corpus registered, no number published, no run id
created** · **no experiment number spent; experiment eleven remains free** ·
**Bears on:** D-048 (which made W10 the lead item), D-043, D-047 ·
**Evidence:** `tools/build_gold_corpus.py`, `tests/test_build_gold_corpus.py`,
`bench.corpora.ReferenceSet`, `bench.corpora.UNREGISTERED_READERS`,
`tools/fetch_data.py::SUBSTRATES`, `bench/splits.toml`; every figure below is **un-gated**,
re-derivable by running the tool, and none of it may be quoted until a runner saves it

D-048 established that the flagship claim is an edge claim and that no held-out corpus here contains
edges. This is the first instrument in the project that could produce one. It ships, it runs, and its
verdict on itself is the useful part.

### The premise the substrate was chosen on is half false, and the operative half is the false one

The August 2026 audit chose the Federal Register because its rules "routinely carry their own
abbreviation legends, so the arbiter is the agency rather than us". Measured on the pinned draw:

```
un-gated -- python tools/build_gold_corpus.py pool, thirty pinned final rules
  documents carrying a Table of Abbreviations            3 of 30
  legend rows parsed                                     39
  legend rows no proposer put forward                    28
  acronymkit pairs, legend_syntax OFF                    719
  acronymkit pairs, legend_syntax ON                     719
```

Legends exist, and where present they really are agency-asserted edges. They are in a minority of
rules, and their syntax is `SF LF` or `SF--LF`, never the `SF = LF` that
`AbbreviationExtractor(legend_syntax=True)` reads — so **the shipped legend reader sees none of
them**, and a plan that costed an agency arbiter was costing something this library cannot consume.
What survives is smaller and real: a legend row is *evidence* for a human, carried as `legend_support`
rather than as a label.

### Pooling three parenthesis scanners is pooling one algorithm

```
un-gated -- same corpus, distinct (document, short form, long form) edges
  acronymkit_high_recall     584
  abbreviation_extractor     330   overlap 302   adds  28
  abbreviations              217   overlap 207   adds  10
  pyab3p                     179   overlap 169   adds  10
  union of all four          623   acronymkit share 93.74 %
```

Every one descends from Schwartz & Hearst, so the union is one algorithm with three implementations,
and reporting its agreement as corroboration would overstate it badly. The recipe publishes the
asymmetry instead, and the all-caps one-liner sits in the pool as a proposer of **vertices** — short
forms with no long form — because a pool of bracket scanners can only ever contain abbreviations that
were defined in brackets.

The audit's `~120 pairs per MB` was **not reconciled and not copied**: it does not say whether it
counts candidates or adjudicated pairs, so it is not reproducible as written.

### The unproposed sample is the load-bearing step, and thirty items cannot carry it

```
un-gated -- 120-item pilot, ONE adjudicator, stratified, seed 20260824
  stratum                     sampled  population  definitions  contested  upper95
  proposed_by_several              30         172           26          5      170
  proposed_by_one                  30         426           18          6      330
  unpaired_short_form              20       2,278            0          2      342
  unproposed_parenthetical         30       3,503            0          5      350
  unproposed_legend_row            10          28           10         10       28
```

Zero definitions in the two heuristic-invisible strata, and re-weighted upper bounds of the same order
as the true-edge estimate in the proposed strata. **The pilot cannot distinguish a nearly complete
pool from one missing as much as it holds.** That is the result. `_rule_of_three_upper` exists so the
point estimate of zero can never be printed alone; it is crude by construction, labelled crude, and no
figure from it may be published.

### Five defects found before anything was published off them

Two legend-parser defects (a short-form class admitting `-` swallowing a dash run; a blank-line-only
parser running past its own table into prose) and one evidence-anchor defect (a window anchored on the
first occurrence of a short form, which is a page masthead) reached a worklist. The fourth reached a
population count and is the one that matters: the Federal Register writes a quoted short form with
doubled backticks and doubled apostrophes, the membership test compared raw inner text, and surfaces
`acronymkit` **had** proposed therefore landed in the *unproposed* stratum — where each would
adjudicate as a definition and re-weight into a false-negative rate for definitions the systems did in
fact find. A fifth, `all()` over an empty pool marking a document exhaustively annotated, was caught by
a test written to assert the opposite; it is D-051's vacuous criterion in a new place.

**Four of the five would have been invisible in a finished set. That is the argument for piloting, and
it is worth more than the corpus.**

One design decision was reversed on evidence inside the work: `freeze` originally admitted only
`verdict == "definition"`, discarding every `wrong_long_form` — that is, every pair a proposer got the
*boundary* wrong on. Those are not a random sample; they are precisely the hard cases, and a gold
standard assembled that way contains only the pairs the systems already got right.

### The registration decision, which is this record's operative half

The artifact labels itself, and the labels are checkable:

```
data/federal_register/reference_set.json, read for this record -- command output
  artifact_kind      'single-annotator reference set'
  is_gold_standard   False
  scorable           False
  headline_eligible  False
  adjudicator_count  1
  requested_role     'single_annotator_reference'
```

`tools/splits.py` `ROLES` is `('tuning', 'held_out')` and **neither is honest**. `held_out` makes a
self-adjudicated corpus headline-eligible through `Manifest.headline_capable`, which is the one thing
it must never be. `tuning` asserts something was fitted to it when nothing was. The documented
fallback fails too: `role = "held_out"` with `contaminated = true` is a hard validation error by
`validate()`'s own rule, because a contaminated corpus may not hold the headline role.

**So no `[corpora.…]` table was written, and the refusal is the decision.** Three things were weighed,
recorded so the next round does not re-litigate them:

* Filing it `held_out` would put a corpus adjudicated by the author of the extractor that proposed
  most of its pool into `headline_capable('extraction')` — turning the project's one honestly-empty
  slot into a filled and dishonest one. This is the outcome the whole W10 effort exists to avoid, and
  it is one word away at all times.
* Filing it `tuning` states a false cause, and it also fails a gate: `bench/corpora.py` carries
  `UNREGISTERED_READERS` and `tests/test_build_gold_corpus.py` asserts that every name in it is absent
  from the manifest, so a registration under any role turns that test red — the tripwire firing
  exactly as designed, in a file this round was not assigned.
* The artifact is a **pilot and is not scorable in either direction**: recall is undefined because the
  denominator is unknown, and precision is understated because an unsampled correct pair scores as a
  false positive. Registering a non-scorable instrument in the file that governs which corpora may
  back numbers puts it one `--save` from a table.

What `bench/splits.toml` gained instead is a named subsection in its held-out-for-extraction block:
the reference set exists, it is deliberately undeclared, the role token it needs is
`single_annotator_reference`, `[policy] headline_requires` needs no change because `headline_capable`
filters on the headline role and would exclude the new one automatically, and the five conditions
below must be met before any promotion. **A comment cannot be mistaken for a declaration, and that is
the property being bought.**

### What would make it a gold standard a headline could cite

Five conditions, in order, none optional: a second adjudicator who authored none of the pooled
systems, with agreement computed and published; a written guideline settling long-form boundaries,
contractions in legends, non-initialism defined terms and typesetting artefacts; **exhaustive**
adjudication of every pooled candidate in the documents to be scored; an unproposed sample whose upper
bound is small against the definitions found — hundreds of items, not thirty; and
`single_annotator_reference` in `ROLES`, taken as its own decision, before any promotion to
`held_out`.

### One thing recorded rather than routed around

`federalregister.gov`'s reader-aids pages answer an automated request with an interstitial saying
programmatic access is limited to the API. **It was not defeated**, and the instruction not to defeat
it is written into the substrate entry. The licence is read from GPO's Public Domain & Copyright
Notice — reachable, stating the same statute, and the terms of the host serving the mirror — and
pinned as an asset, so the finding rests on text rather than on a badge. That notice carries a caveat
a one-word licence field would destroy: a Government publication may contain third-party copyrighted
material used with permission, and Federal Register rules incorporate industry standards by reference
and quote them. `vendorable = false` rests on two grounds, not one.

**Amends `tools/fetch_data.py` in one general way.** `Asset` gains `licence_read_on`. Operating rule 4
has two halves and that registry enforced only the URL half: every existing asset records where a
conclusion came from and none records when. The field is deliberately **not** back-filled — inventing
read dates is worse than the gap — and the ledger prints that the entry predates the field.

### How it fails

**The adjudicator wrote the extractor that proposes most of the pool.** Every refusal in the pipeline
is a mitigation of that and none is a fix; the labels are on the artifact so nobody can forget it, and
that is the most the code can do. Thirty documents from one quarter cannot represent Federal Register
house style, which is agency-specific — three legend defects in one pilot suggest more are waiting,
and the legend heading regex, the row patterns and the section-heading stop are all heuristics over a
whitespace-delimited table. **The stratum definitions are themselves a design**:
`unproposed_parenthetical` reaches only balanced single-line `(...)` regions, so a definition
introduced by an em dash, by "means", by a quoted defined term outside brackets, or spanning a line
break is in no stratum at all and is therefore invisible to the estimator that exists to catch
invisibility. Three live behaviours have no test — `discover` paging the API, `fetch --mirror-check`,
and `select` reporting drift — and **the drift branch has never fired**, which is the branch protecting
the corpus's identity. The pin protects the text and not the licence reading: a site rebuild will fire
the terms asset's checksum for a cosmetic reason and the next person will be tempted to update the
digest without re-reading. `_defining_occurrence` chooses a window to read and is documented as not
being an assertion about which occurrence is the definition — that distinction is prose, and a future
reader could mistake it for a localiser and use it to derive spans, which is the gold-side derivation
D-048 closed on arithmetic. `data/LICENSES.md` is generated from the registry, is now stale, and
nothing in CI compares the two. And every verdict is Windows / CPython 3.13, with the external
proposer driven under a 3.12 interpreter at a hard-coded path that no test exercises.

**`VERDICTS` has no `wrong_short_form`.** The Federal Register quotes a short form inside doubled
punctuation and the proposers truncate it; that is decidable and unsayable in the current vocabulary,
so the item was recorded `undecidable` with the reason. Widening it is a worklist-format change and
belongs with the guideline work (R8).

---

## D-055 — Four documentation debts, and re-reading one page against the code found three defects nobody had listed

**Status:** shipped; documentation only, no behaviour changed · **no experiment number spent** ·
**Amends:** D-039 (the `pattern` gap it recorded in its own *how it fails*), D-037 (the adjacent
finding it reported and did not fix) · **Bears on:** D-034, D-038, D-051 ·
**Evidence:** `src/acronymkit/models.py`, `README.md`, `docs/AUDIT-2026-08.md`,
`docs/GOVERNED_NAMING.md`, `docs/OFFLINE.md`, `docs/SUPPORT_MATRIX.md`;
`acronymkit.resources.bundled_resources()`; `governed_gold.*` in `bench/results.json`

Four debts were carried as small ones, each a claim the code did not match. Three were, one was
already half paid, and the fourth — *re-read the page against the code* — returned three defects the
list did not name. **The re-read was worth more than the three specified fixes together.**

Verified for this record, straight out of the installed package:

```
PYTHONPATH=src python -c "..."           -- command output, re-derivable
  len(bundled_resources())                                        8
  AcronymPair.model_fields['pattern'].description
    "Which arrangement matched. 'long(short)' or 'short(long)' for a bracketed
     definition -- the brackets may be (), [] or {} -- and 'short=long' for a
     legend, which only an extractor built with legend_syntax=True ever emits."
```

Two words of the old description were wrong and one value was missing: `[CNS]` yields `long(short)`,
so "parenthetical" was already inaccurate before D-039 and independently of the legend flag. No schema
enum constrains the field, so nothing else needed changing. `docs/OFFLINE.md` said seven resources in
four places and `docs/SUPPORT_MATRIX.md` in two; both tables now carry the eighth with its digest and
provenance, `SUPPORT_MATRIX` has the provenance column it never had, and both say that if they
disagree with `doctor`, `doctor` is right.

**The inbound-link debt was half wrong on inspection**, which cost one grep: `README.md` has linked
`docs/DEFINITION-OF-DONE.md` since D-051 shipped, so writing the briefed link would have produced a
duplicate. The orphan was `docs/notes/w11-emission-model.md` alone.

### The three the list did not name

**A section documenting a defect the code had fixed.** `docs/GOVERNED_NAMING.md` told callers that a
JSON dict overlay needs one line of construction or it stringifies into a repr. `_custom_index` grew a
`Mapping` branch five commits after that section was written, and the branch's own comment names that
exact failure as the one it prevents. **A stale workaround is worse than a missing one**: the reader
writes the code, it works, and nothing ever tells them it is dead.

**The page shadowed its own catalog.** A `load_bundle(...)` binding re-pointed every later example, so
three printed outputs disagreed with what the page produces when pasted — on a page whose whole claim
is that it is executable.

**"No figure belongs next to this" said no corpus was scored.** One was:
`headline_capable('identifier_segmentation')` returns both governed corpora, held out and
uncontaminated, and `governed_gold.*` is gated. The distinction had to be made rather than assumed —
the *lookup* is a tautology and still carries no number; the *cut* is not, and is measured — and the
section now points at `docs/EVALUATION.md` rather than transcribing a figure onto a page whose claim
is that it carries none.

Plus a fourth, aimed outward: `docs/notes/governed-json-contract.md` §6 still classifies `[` and `]`
as separators unconditionally and carries no `value[x]` row, so a port built from it contradicts the
shipped tokenizer. D-034 recorded that as an open follow-up; the reader who would be misled is now
warned at the point of the link, and the contract file is untouched (R8).

### One number changed shape rather than value, and it is recorded here rather than left in a diff

A bundled resource's byte count, published as bare prose, fails `check_claims`: the filename contains
`precision`, underscore is deliberately not a welding character, and the proximity window reaches it.
It is a file size, not a performance claim. Neither the allowlist nor a citation applies, so the byte
columns in both tables became code spans, with a sentence saying those columns are literals from
`capabilities()` rather than prose figures. **Changing text so a check stops firing is exactly what
the claims gate exists to make expensive**, so it is written down — and D-057 above books it against
criterion 3 rather than leaving it filed under the workstream that did it.

### How it fails

The block executor that swept the page does not read outputs written as a following comment, which is
where the shadowing hid — the three were found by eye, so three is a lower bound, and only one of six
assigned files was swept this way. **The rewritten overlay section has no test behind it**: nothing in
`tests/` builds an overlay from a mapping, and the error string it quotes appears only in the
implementation and now in one sentence of prose, so it can regress silently in the same way the
section it replaces did. Nothing in CI compares either resource table to `bundled_resources()`, so the
ninth resource drifts the same way — and the byte column is now invisible to the claims gate as well.
`docs/OFFLINE.md`'s wheel figures are labelled as predating the eighth resource on commit ordering
rather than refreshed by a build. And two verdicts rest on a grep and a read rather than on a check:
that `AcronymEngine` never consults the reliability table, and that nothing bundled is copyleft.

---

## D-054 — A backronym has no gold, so the fifth subsystem gets properties and a scoped criterion instead of an invented number

**Status:** measured and published · **Closes:** definition-of-done criterion 2, **by scoping it** ·
**Amends:** D-051 (criterion 2's verdict), D-037 (one more retired sentence of the same shape) ·
**Evidence:** `bench/run_backronym.py`; `backronym.{med1250,sdu21_ad}.{alignment,synthesis}` in
`bench/results.json`; `docs/EVALUATION.md`; 47 new cases in `tests/test_backronym.py`

`BackronymGenerator` is a box in the architecture map, two facade methods, two CLI commands and a
README section, and it carried no external number of any kind. D-051 recorded criterion 2 as NOT MET
and said inventing a number would be worse than the open verdict. It would. **So the number that was
invented is not an accuracy number, and the criterion is amended to say so out loud.**

### What a backronym number can be, and the one it cannot be

Forward generation has gold because a corpus records what a human *chose*. Backronym synthesis is
handed a target and asked to *invent*. No annotator has judged an invented phrase and no backronym
gold is published, so building one here would mean writing the standard this library is then scored
against. The metrics split, and keeping them apart is the whole content of the work: **properties**
(every word starts with its letter, in order; the letter is really at the offset claimed; the
constraint can be satisfied at all) are checkable and are checked; **quality** (meaningful, apt,
preferred by a person) needs a judge, and there is none.

### The two devices that stop it being a tautology

The alignment constraint is exactly strict increase in the lexicographic `(token, offset)` order, so
"a complete alignment exists" is "the letters are a subsequence of the eligible-token character
stream" — decided by a two-pointer walk with no weights, no search and no library code. That is the
oracle, and it shares nothing with the aligner.

The second device matters more. **Coverage is not the objective.** Leaving a letter unmapped costs
`unmapped_penalty`; stepping over a critical token costs `delta`, which ships four times larger. So
the objective sometimes prefers an incomplete alignment and is right to:

```
un-gated -- shipped engine, stock Config(), the case that killed the first draft of this metric
  BIS <- "bispectral index"
    oracle's complete path   b,i,s inside "bispectral"            scores -1
    what align returns       B<-bispectral, I<-index, S unmapped  scores 16
```

Reporting that as a shortfall would publish a design trade as a bug. Every feasible-but-incomplete
pair is therefore re-scored against the oracle's complete path using the library's own `Scorer`, and
all of them come back objective-preferred with zero search shortfalls.

```
bench/results.json, backronym.med1250.alignment.all -- MED1250, tuning split, contaminated
  pairs                    1,221      feasible %              87.63
  complete %               86.49      complete of feasible    98.69
  letter coverage %        94.81      letter ceiling %        95.38
  incomplete_feasible_n       14      objective_preferred_n      14
  search_shortfall_n           0      oracle_contradictions_n     0
  validity %              100.00      over 4,815 alignments
  worst row  with_digit    119 pairs   feasible 56.30   complete 56.30
```

```
bench/results.json, backronym.sdu21_ad.alignment.all -- tuning split, contaminated
  pairs                    2,308      feasible %              97.96
  complete %               97.96      validity %             100.00  over 10,237 alignments
  with_digit                   0 pairs -- COUNTED zero; this corpus cannot show the digit failure
  incomplete_feasible_n        0 -- the search-optimality guard FIRES ZERO TIMES here
```

The ceiling is decomposed, one cause per pair, under committed precedence. **The largest single cause
is the same on both corpora and it is not the data:**

```
bench/results.json, backronym.*.alignment.all.infeasible_by_cause
                          med1250   sdu21_ad
  token_ineligible             50         43    "POS" <- part OF speech;  "vitD" <- vitamin D
  digit_absent                 40          0    "T3"  <- triiodothyronine
  character_absent             30          4    "DPH" <- phenytoin
  out_of_order                 31          0    "FasL ICD" <- intracellular FasL domain
```

Nothing was changed in response (R6).

### The share of the task no property can settle

```
bench/results.json, backronym.*.alignment.all
  med1250    1,070 feasible    399 admit more than one reading    37.29 %
  sdu21_ad   2,261 feasible    961 admit more than one reading    42.50 %
```

`TAI <- "timed artificial insemination"` admits *timed artificial artificial*, *artificial insemination
insemination*, and the obvious human reading. On roughly four pairs in ten the constraint does not
determine the answer, the objective picks one, and nothing here can say whether it picked the reading
a person would have. **That is the judge-shaped hole, counted**, and it is the argument for the
amendment rather than a gap to be closed by more effort. Both counts are lower bounds: alignments are
compared on the words read out, not on token indices.

### Coverage is not quality, and the run says so about itself

```
bench/results.json, backronym.med1250.synthesis
  all          1,010 targets   complete 89.70 %   letters 96.34 %   mean word length 3.00
  alphabetic     906 targets   complete 100.00 %  letters 100.00 %
  with_digit     104 targets   complete   0.00 %  letters  72.36 %
  every unserved character on both corpora is a digit; no letter of the alphabet fails once
```

```
python bench/run_backronym.py --examples          -- command output
  'ABC' -> 'aah baa cab'      'ACE' -> 'aah cab ear'      '1D' -> 'dab'
```

Every letter served, every word a real dictionary word, every initial correct, every alternative
distinct — and the output is unusable. **That row scores full marks on every property this project can
check**, which is the single strongest argument for scoping the criterion rather than inventing a
metric. The mean word length is the same on every row because the ranking key prefers a mid-length
band then shorter before longer, and the shipped lexicon's short band is the obscure tail of a list
D-004 graded for recognisability *as a word*, not aptness *as an expansion*.

### The amendment, and one retired sentence

> **Four of five subsystems carry an accuracy number. The fifth — backronym synthesis and alignment —
> carries constraint-satisfaction, coverage and underdetermination figures, and cannot carry an
> accuracy number, because scoring a backronym requires a judgement no corpus records and this project
> has no judge.**

It reopens on a published backronym gold, or on a judge this project is willing to defend with its
agreement against humans measured first. **`generation.med1250.dictionary_backronym` is not this
subsystem's number** — it is forward generation under a preset that happens to be named that way, and
nothing in it calls `align` or `synthesize`; the runner and `docs/EVALUATION.md` both say so, because
it sits next to this gap in the same results file and is exactly the figure a hurried reader reaches
for. `docs/EVALUATION.md`'s "Backronym alignment has no external evaluation at all" is retired **in
place** rather than deleted, with the note that the *quality* half of it still stands — D-037's
mechanism, one more time.

### What the workstream's own adversarial pass killed

Three metrics were built and removed before anything was saved: `alternatives_mean`, which read the
same value on every row because the generator round-robins to the cap and so measured the cap;
`forced_agreement_pct`, which is `validity` wearing a second name once you know the aligner may legally
return an incomplete alignment; and an index-level definition of underdetermination, switched to
comparing the words read out because two token indices can carry the same surface word — the
conservative direction, and it moved the SDU-21 count by one. And `tools/check_claims.py` caught a
stale transcription into `docs/EVALUATION.md` from the earlier index-level prototype: **exactly the
failure R1 exists for, caught by the machine rather than by the author.**

### How it fails

**Every figure is a property, and `'aah baa cab'` satisfies all of them.** If any of these numbers is
quoted as evidence that this library writes good backronyms, this record has failed, which is why the
refusal is printed above the numbers in both the runner and the doc. MED1250's own annotation guide
excludes non-matching and out-of-order pairs from gold, so the population is **already pre-selected
toward alignable pairs** and the feasibility column overstates arbitrary prose — the cause table is the
informative half. Both corpora are tuning and contaminated, and the argument that a held-out split
would not make a *property* more trustworthy is an argument, not a rule this project has adopted. Two
domains, neither of which is the product-and-project naming use case `synthesize` exists for. The
search-optimality guard has a fourteen-case denominator on one corpus and none at all on the other.
**The largest infeasibility cause is a lever nobody has pulled**, and pulling it would invalidate this
table and move forward generation's numbers too. Nothing in CI runs the runner, so these four entries
stale the same silent way any gated figure does. `oracle_contradictions_n` catches disagreement in only
one direction, so a shared misunderstanding of eligibility between oracle and aligner would pass
unnoticed. And `--save` overwrites four entries with **no diff preview**, unlike `bench/run_micro.py`,
which D-051 required to print every field it is about to overwrite — on a first write that costs
nothing, on a re-run after a library change it silently replaces numbers `docs/EVALUATION.md` cites.

---

## D-053 — A reservation that refuses a read, because two records each said they could not have one

**Status:** shipped (validator + accessor + two wired readers) · **no experiment number spent** ·
**Amends:** D-043 (adds a lapse trigger), D-047 (`train_allocation` prose becomes a structure) ·
**Discharges:** D-048's "one change recommended and not made" ·
**Evidence:** `tools/splits.py`, `bench/splits.toml`, `tests/test_splits_manifest.py`,
`bench/corpora.py`; `python tools/splits.py --check`

D-043 and D-047 each allocate a corpus arm, and each says the same thing about itself in its own *How
it fails*: **an allocation in a D-record is not a mechanism; nothing refuses a run against the split,
and the guard is that somebody reads a note.** That is the shape this repository has already paid for
at the file level — eleven places cited `bench/splits.toml` in prose, none parsed it, and it had been
invalid TOML for months. This record closes it one level up.

### What a reservation is now

```
[[corpora.sdu22_ae_legal.reservations]]
  arm            the split token a RUNNER passes ("train"), never a filename
  state          allocated | unallocated | spent
  decided_in     the D-record that put it in that state
  allocated_to   the question it answers and who owns the read   (allocated)
  spend_trigger  the event that would fire the spend             (required)
  lapse_trigger  the event that releases it again                (allocated)
  not_a_trigger  the near-misses, written down in advance        (optional)
```

`validate()` fails CI on a reservation with no `spend_trigger`, an allocation with no `lapse_trigger`,
two reservations claiming one arm, `allocated_to` or `lapse_trigger` on something that is not an
allocation, `spent` with no `spent_in`, one event given as both triggers, a `decided_in` that is not a
record id, an arm written as a filename, an array that is not tables, and **an unrecognised key**. The
last is the asymmetry worth keeping: a corpus table preserves unknown keys in `Corpus.extra` and a
reservation refuses them, because `train_allocation` was itself such a key — valid TOML the loader
neither validated nor rendered — and a misspelt `laps_trigger` would silently drop the one field the
structure exists to require.

**`unallocated` is a state, not the absence of one.** D-047 kept SDU-22 scientific `train.json`
unassigned on purpose, and the validator holds the distinction: an unallocated arm must still carry the
trigger that would let it be spent and must not name something it is allocated to, and `declare_spend`
refuses it outright. First-come is refused; the first spend needs its own record and an `allocated`
entry before a runner can claim it.

### The refusal, verified live rather than described

```
verified for this record, no reserved file opened -- command output, abridged
  read_sdu22_ae(domain="legal", split="train")
    -> SystemExit: arm 'train' is RESERVED ... state allocated, decided in D-047
  read_sdu21_ad(split="test")
    -> SystemExit: arm 'test' is RESERVED ... state allocated, decided in D-043
  python tools/splits.py --check
    -> 8 corpora, 3 reserved arm(s), 0 problem(s)
```

`data/sdu22_ae_legal_train.json` was already fetched, so before this a single call mined the corpus's
last unmined arm and printed nothing. In `_sdu21_ad_source` the check runs **before** the unknown-split
refusal: `test` is in no registry, so it was previously refused as a typo — an accident that reads like
a guard — and asking the manifest first means whoever adds the entry meets D-043's reservation instead
of quietly deleting the only thing standing in front of the project's last blind disambiguation arm.

**The ergonomics are the design, not a footnote.** One unconditional line at the reader; a silent no-op
on every unreserved arm, so a reader need not know what is spoken for; no flag, no environment
variable, no config — a `--force` is typed without reading and an env var never reaches a log; and it
asks only for the record id and one line of purpose, never for the trigger restated, because
duplication is what D-045 warns goes stale. Complying costs one line and bypassing costs writing your
own reader.

### `TASK_GOLD_UNIT`, the edit D-048 said was owed

`extraction` now says each record asserts an **EDGE** and the edge is the whole of the gold, so a
system emitting both surfaces and pairing them wrongly is wrong; `span_detection` says the gold is two
**UNLINKED** vertex sets carrying no edge at all, over a wider extension. Both strings flow into
`require_task`'s error, into `--json` and into the ceiling refusal, and a test pins the words so they
cannot be compressed out — which is how both dead phrasings of the abstention finding were produced.
No figure was added, so R1's value-matched ratchet did not move.

### Four designs killed before shipping

Wiring only one reader — killed by decomposition, because that leaves D-043's reservation declared and
unenforced, and D-043's is the spend that is permanent. `declare_spend` writing `state = "spent"` back
into the manifest — killed, because a runner that can mark its own arm spent is spending it with no
commit, no review and no record. Failing **closed** when the manifest cannot be parsed — killed on
arithmetic: on interpreters without a TOML parser that would refuse every split of every corpus to
protect two files, so it fails open with a non-suppressible banner. And a validator check that every
reserved arm is a split its reader knows — killed as a check that needs its own exception, because it
fails on `sdu21_ad:test`, the reservation that most needs to exist, and carving an exemption for it is
the `EXPECTED_NON_PASSING` shape D-050 found fatal.

### How it fails

**It binds the readers, not the filesystem.** A scratch script that opens the JSON spends the arm and
nothing notices — and scratch runners are how the audit's un-gated SDU-22 figures and D-048's own
probes were produced. The honest claim is that this stops an *accidental* spend through the registered
path and raises a deliberate one from free to writing your own reader. **It refuses an undeclared spend
and does not record a declared one**: `declare_spend` prints the manifest edit to make and nothing
enforces it, so the manifest can now be stale about what was actually spent — D-045's own duplication
warning arriving inside the fix for it. **D-043's lapse trigger is a reading, not a transcription**:
D-043 wrote no release condition, the validator requires one on an allocation, so it was derived from
D-043's own *How it fails* and labelled as such inside the field — a validator forcing a sentence into
existence is precisely the failure mode this file watches for. **A misspelt arm validates and guards
nothing**, which is the same shape as the defect being fixed, one level down. `sdu21_ad:test` is
guarded on a path nobody currently walks, so its refusal is prospective. **Two ledgers exist**, because
`tools/splits.py` is imported by path twice, and `bench.corpora.declare_spend` being the single door is
an instruction rather than a mechanism. The reservation module is skipped entirely on interpreters that
cannot parse the manifest. And everything here is Windows / CPython 3.13.

---

## D-052 — The claims gate was declining to look at most of the numbers, and a total over the armed subset was being read as a total over the document

**Status:** shipped · **Amends:** D-051 (criterion 3, and its "ten measured figures" reading) ·
**Evidence:** `tools/check_claims.py`; `tests/test_check_claims.py`;
`python tools/check_claims.py --residue`

D-051 recorded that `check_claims` arms only within a short window of eleven keywords, so a figure
further away "is not merely un-cited — it is counted in no total and reported in no summary". Three
holes were listed. They are one mechanism: **the gate's coverage was implicit.** `SCAN_GLOBS` said
which files were read and nothing said which were not; `_PROXIMITY` said which numbers were armed and
nothing said which were not. Both printed a total over what was examined, and it read as a total over
what exists.

### Proximity is not the failure. Vocabulary is.

The README miss D-051 found is `F₁ > 96 %`, and that line carries **no metric keyword at all**: `F₁` is
U+2081 SUBSCRIPT ONE, not the ASCII `f1` in `_KEYWORDS`. Widening the window by an order of magnitude
would never have armed it. So proximity is kept — it is a precision device and it works — and a second,
orthogonal rule is added that reads the number's own shape: a number immediately followed by a metric
unit (`%`, `µs`, `ms`, `docs/s`) arms with no keyword required. Proximity is checked first and wins
ties, which is what guarantees the old value ledger could not move.

### Arming on everything was measured and refused

```
un-gated -- python tools/check_claims.py --residue, replayed for this record
  prose numbers no rule arms                                1,468
  ... that would value-match if routed through the fallback 1,144
  ... of those, AMBIGUOUS under classify()                    792
  `100` equals 117 distinct measurements; `2` equals 97; `0.00` equals 208
```

Value-matching the residue would have relabelled over a thousand invisible numbers "backed" —
publication years, scoring-weight defaults, rank cutoffs. **An invisible number does not claim to be
backed; a number the summary calls `value` does.** So unexamined numbers are recorded, counted, listed
by `--residue`, and never value-matched.

### Two registers, because widening may not launder into the old one

`VALUE_MATCHED_BASELINE` is untouched at `71` across four files. Everything the widening revealed goes
on a new `DEFERRED_BASELINE` with the same semantics — exact match in both directions, absent reads as
zero, lower it in the commit that migrates.

```
python tools/check_claims.py --residue, run for this record   deferred   matching NO measurement
  docs/DECISIONS.md                                              115              35
  docs/notes/pydantic-cost.md                                     70              34
  docs/EVALUATION.md                                              60               0
  bench/splits.toml                                               32               3
  CHANGELOG.md                                                    28               4
  ... six more files, 11 in total                                316              76
```

**The concrete find.** `CHANGELOG.md` publishes an `is_compliant` before-figure in microseconds that
**matches no measurement in `bench/results.json` at any precision**, and it has been in a release note
the whole time. Conversely, `bench/splits.toml`'s two recall ceilings — the figures the audit flagged
as un-gated — both resolve. The file was right about itself. Nothing was checking, and "right about
itself" is exactly the state value matching cannot distinguish from luck.

**A coverage change may reveal a verdict; it may not soften one already reached.** The first draft
routed every uncited number in a file outside the value ledger to the deferred register. While it was
being written, another workstream added a resource byte count to two documents; it is keyword-armed,
matches nothing, and the *unmodified* gate fails on it. The draft would have turned that red into a
grandfathered ledger row. Only the unit rule and two named newly-scanned files reach the deferred
register now, and a test pins it. The discrepancy was found because two runs of the *same* code
disagreed and the author chased it instead of assuming a bug in the instrumentation.

### A ratchet on the raw residue was checked and rejected

```
un-gated -- this file's scanner replayed over the eight commits before the change
  docs/DECISIONS.md  unarmed   485  485  498  531  531  560  560  595
  docs/DECISIONS.md  armed      44   44   44   44   44   44   44   44
```

An exact ratchet on the residue would fire on every commit that adds a D-record and would be bumped
mechanically; a ratchet bumped every round is a rubber stamp. The armed count did not move once across
the same eight commits, which is why both ratchets sit on the armed population.

### D-051's "ten previously-invisible measured figures" is corrected

Of README's fifteen invisible numbers, one is a claim — a figure published by Schwartz & Hearst — and
the rest are publication years, scoring-weight defaults, a rank cutoff, a plateau range, a word-list
size cut and three illustrative values. Nine value-match, and **every one of the nine is AMBIGUOUS**.
The count of invisible *numbers* was right; the word "measured" was doing work the evidence does not
support, and it is the same value-matching unsoundness the ratchet exists for, arriving as prose.

### How it fails

**The gate still does not check most numbers**, and the honest claim is "nothing is dropped silently",
not "everything is checked": the unit rule reaches about one number in six of what proximity misses.
**The deferred total is a floor on the debt, not a measure of it** — it is the count under this unit
vocabulary, and adding `KB`, `MB`, `bytes` or a speedup `x` moves more across, each widening being
another ratchet-lowering commit rather than a free win. A seventh of the residue is ISO-date fragments,
because `iter_claim_numbers` splits a date into three numbers under a rule shared with the armed path,
so fixing it would move the value ledger too (R6). **The residue was measured with the same tokenizer
that defines it**; cross-checking against a clean `git archive` export checks arithmetic, not the
notion of "a number". **Fencing still silences the gate completely**, so a falling deferred count is
not by itself evidence that a figure was adjudicated. The gate got materially slower, because it
examines every number rather than the armed few. And **this makes the next round's `docs/DECISIONS.md`
edit red on arrival** — that file's deferred count rose over the eight commits before the change, so
the next record containing a bare percentage finds the gate refusing. That friction is R1's actual
price, previously absorbed by a blind spot, and it is imposed on workstreams that could not be
consulted; it is the most likely reason for someone to want this reverted.

**One defect in the new report, found while verifying this record and not fixed here.** `--residue`
echoes the source line of every number it lists, and those lines contain characters outside the Windows
console's default code page, so `python tools/check_claims.py --residue > file` dies with a
`UnicodeEncodeError` partway through and exits non-zero. The summary path is unaffected because it
prints no source lines. It is reproducible on this box, it is in `tools/`, and it belongs to whoever
owns that file next.

---

## D-051 — The definition of done, read together for the first time: five met, three not, and both flips were scoping errors

**Status:** swept and published · **Amends:** D-044 (criterion 1), D-013 (the import triple) ·
**Evidence:** `docs/DEFINITION-OF-DONE.md`; `micro.import` in `bench/results.json`;
`tools/check_claims.py`; `bench/run_micro.py`; `python tools/splits.py --check`

Eight criteria have governed what "finished" means here and have been answered one at a time, each in
the round that touched it. Read together against the tree rather than against the last reading, two
verdicts move — and neither moves because a number changed.

```
docs/DEFINITION-OF-DONE.md, re-derived 2026-08-24
  1  abstention                  met with qualification   mechanism + publication, not value
  2  every subsystem scored      NOT MET                  BackronymGenerator has no number
  3  everything gated            NOT MET                  the gate cannot see every number
  4  splits.toml governance      met                      parses, loaded, in CI, 26 mutation tests
  5  non-biomedical + ceiling    met with qualification   ceiling IS in the table; genre != domain
  6  extension points            met                      four injectable; pack group deleted
  7  clean-report-data-loss      met                      three defects re-probed, all fixed
  8  do-not list grew            met                      nine carried, one added, none withdrawn
```

**Criterion 2 was carried as met and is not, and the failure is one of scope, not of evidence.**
`BackronymGenerator` is a box in the architecture map, two facade methods, two CLI commands and a
README section with worked output, and it carries no accuracy number of any kind.
`docs/EVALUATION.md` says as much in its own words. Reading "every shipped subsystem" as "every
subsystem with a registered corpus" makes the criterion true by construction, which is exactly the
move this file exists to make expensive. Closing it needs either a backronym gold — a phrase, a
target word and a human's judgement that the alignment is good, which nobody has published — or an
amendment that names the excluded subsystem out loud. **Inventing a number for it would be worse
than the open verdict.**

**Criterion 5 confirms on its wording, and the qualification underneath it moved.** The short-form
recall ceiling really is printed in the same table as the recall it bounds, in D-039 and now in
`docs/EVALUATION.md`, which is R9.6 satisfied. What stays open is not the ceiling: `bench/splits.toml`
establishes by counting that the split the corpus calls "legal" is UN institutional prose with zero
occurrences of six basic terms of legal practice. A different genre is worth having and it is not a
different domain, so the domain-generalisation gap this criterion was written about is untouched.

### The import claim: already gated, and the re-record refused

The instruction was to gate `import acronymkit`, described as `1.8 ms` against a documented `7.71 ms`
and therefore a large un-gated win. All three parts fail on checking. Verified for this record
straight out of the results file:

```
bench/results.json, micro.import -- gated since D-013
  cold_import_ms         2.3
  cold_import_engine_ms  128.1
  cold_first_result_ms   196.0
  iterations             9
```

`7.71` is the audit's eight-distribution virtual environment, measured to argue against scanning
entry points on the import path; it was never this project's import figure, and reading it as a
"before" compares two environments. And the movement is the machine, not the package:

```
un-gated -- five consecutive medians-of-nine, 2026-08-24, development box, NOT saved
  import acronymkit               1.9  2.0  1.9  2.1  2.1 ms    recorded 2.3     DOWN
  from acronymkit import Engine   140.1 143.4 143.3 144.5 151.1  recorded 128.1   UP
  import + first generate         206.3 209.0 209.0 208.8 216.9  recorded 196.0   UP
```

Nothing this project did makes the shell cheaper and the engine dearer in the same measurement. D-038
already A/B'd the only recent change to the import path — deleting the entry-point scan — and
recorded it as a non-result on purpose, because the scan was never on that path.

**What saving anyway would have cost, and why `--only import` does not prevent it.** The flag
protects the per-call latency arms; it does not protect the three import figures from each other,
because they are one entry. The only way to re-record the flattering figure is to re-record the other
two, and those three are quoted as a triple in five places no runner regenerates — D-013's
before/after table, `docs/EVALUATION.md`'s import-column caveat, `docs/notes/pydantic-cost.md`,
`CHANGELOG.md`, and the "why 30 ms" comment in the CI `import-time` job. The third row exists
precisely to stop the first being read as a win. **A `--save` would have published drift as a win in
README while staling, in the opposite direction, the caveat that prevents that reading.** That is
D-013's flattering comparison arriving through the runner rather than through the prose.
`bench/run_micro.py` now prints, at the moment `--save` is used, every field being overwritten with
its old and new value, and names the five documents when `micro.import` is among them.

### R1: README is the first document at zero, and the ratchet moved with it

```
python tools/check_claims.py, run for this record, 2026-08-24
  scanned 58 files, 535 claims | cited 462 | value-matched 71 | allowlisted 2 | unbacked 0
  value-matched ratchet: 71 of 71 budgeted across 4 file(s)
  VALUE_MATCHED_BASELINE   README.md  5 -> ABSENT   (absent reads as zero)
```

Five value-matched claims migrated to run-id citations and the baseline lowered in the same commit,
which is what R1 requires and what stops a freed slot being occupied quietly by the next bare number.
Ten further measured figures were found in README that the gate had never seen at all: `check_claims`
arms only within 48 characters of eleven keywords, so a figure written further away is not merely
un-cited — it is counted in no total and reported in no summary. One README sentence held both
states: two figures on the same line, both about the same measurement, one inside the window from
`mean absolute error` and counted, the other a few words further along and invisible. (Writing the
two character distances out here would itself have added two value-matched claims to this file, for
numbers that are not claims at all. The gate is doing its job and the failure mode cuts both ways.)

### Criterion 9, proposed and not met

**"The two tasks the README leads with can be adjudicated by a corpus this project did not tune on."**
Verified live for this record: `headline_capable('extraction')` and `headline_capable('disambiguation')`
both return empty, and `python tools/splits.py --check` prints both gaps. The flagship number and the
worst number are the two with nothing behind them.

The collision worth carrying forward: **criterion 9's disambiguation half cannot be closed with any
corpus currently registered.** The only capable instrument is SDU-21 AD `test.json`, which D-043 has
already assigned to a different question. One unread split, two questions — the same shape as D-047
below, one task over. It needs a new corpus, not a re-run.

### How it fails

Nothing in CI asserts any of the eight, and four verdicts rest on prose read on one day by one
reader; `check_claims` catches a stale number and nothing catches a stale sentence, which is how
D-037's three retired sentences survived. Two verdicts were taken against a tree other workstreams
were still editing — criterion 5's location half depends on a concurrent `docs/EVALUATION.md` edit,
and if that is reverted the criterion re-opens — which is also why the sweep transcribes no
project-wide claim total and prints the command instead. Criterion 3's evidence is circular: the
invisible figures were found by eye, so ten is a lower bound, and no document other than README was
swept the same way. Criterion 7 quantifies over *known* defects and all three originals were found by
a person driving the public API rather than by a check. And the import refusal is a reading of three
figures moving in two directions, not an A/B across a commit; if the three are ever re-recorded
together with a change that explains all three, this record is what should be cited against the story
where the import cost fell alone.

**One out-of-assignment edit landed with this work and is recorded rather than buried.**
`tools/check_claims.py` was not the workstream's file, but `baseline_problems()` fails the build on a
*decrease* as loudly as on an increase, so migrating README's five claims and leaving the entry alone
would have left the claims gate red. The edit is confined to the README key. R1 mandates exactly that
pairing; the note is here because "the rule told me to" is a reason to record an out-of-scope edit,
not a reason to omit it.

---

## D-050 — The AST guard is retired, and the job that subsumes it is not the one everybody assumed

**Status:** shipped (tests + CI comments) · **no experiment number spent** ·
**Evidence:** `tests/test_packaging_manifest.py`, the `installed-suite` and `build` job comments in
`.github/workflows/ci.yml`

`tests/test_packaging_manifest.py` held an AST scan for test modules that load an unshipped path at
import. It failed in the shape it was installed to prevent twice, each fix resolving one more level
of indirection. D-040 built a structural job — `installed-suite` — and the question was whether it
subsumes the pattern. Each of the five historical breakages was reintroduced one at a time on a
scratch clone and run through that job's literal command sequence.

```
un-gated, workstream measurement, 2026-08-24, CPython 3.13, Windows
(`Scripts/python.exe` for `bin/python`), gate exactly as written in ci.yml
                                              installed  extracted  test -f
                                              -suite     tree       lines
  a  bench/results.json out of the sdist      passes     FAILS      FAILS
  b  data/LICENSES.md out of the sdist        passes     passes     FAILS
  c  tests/fixtures/*.json out of the sdist   FAILS      FAILS      --
  d  test_governed_gold.py loads bench/       FAILS      FAILS      --
  e  test_splits_manifest.py loads bench/     passes     FAILS      --
```

### `installed-suite` catches two of five, and misses the one that matters

`a` and `b` are invisible because the run directory holds `tests/` and `pyproject.toml` and nothing
else, and the only test reading `bench/results.json` is one of the two that cannot collect at all.

**`e` is the finding.** It is the *same defect as `d`*, in a file already on `EXPECTED_NON_PASSING`,
and it produced a log identical to a clean run — same pass, skip, failure and error counts, the same
eight checkout-only entries "accounted for exactly", gate `rc=0`. **While a file is on that list the
job cannot see a second defect inside it**, because the entry is keyed on the file and the file was
already going to error. D-040 anticipated the opposite direction: a future workstream *guarding* a
listed file and firing the stale-entry branch. This direction was recorded nowhere.

So the premise the retirement was proposed on — that `installed-suite` catches this class by
construction — is false on the printed table. **Structural-by-construction stops at the boundary of a
list of names.** Had the guard been retired on that reasoning alone, the one breakage that motivated
the last two fixes would have had no check on it in the `test` job at all, and the fact that `build`
still covers it would have been true by accident rather than by anyone's decision.

### What does subsume it is `build`'s extracted-tree step

```
un-gated, same session, with tests/test_packaging_manifest.py DELETED from the
extracted tree so the failure cannot be the guard firing inside that run:
  d  extracted-tree `pytest -q -x`   rc=1
  e  extracted-tree `pytest -q -x`   rc=1
     unmutated baseline              rc=0
```

That step catches four of five, by **executing the import rather than matching a pattern**, so no
spelling hides from it — which is precisely how the guard was beaten twice. The guard is deleted:
`_UNSHIPPED_ROOTS`, the two AST helpers, the check and its now-unused `import ast`. Verified for this
record: `tests/test_packaging_manifest.py` contains zero occurrences of either name.

D-018's rule appears once more, one level up. A pattern that describes the bug cannot be used to test
for the bug; only running the thing can.

### The manifest-vs-tree half stays, on its own measurement

```
un-gated, same session. Add tests/fixtures/governed/policies.yaml, a file the
`recursive-include tests/fixtures *.json *.jsonl *.csv *.txt *.md` format does
not name:
  absent from the built sdist                            (confirmed at the artifact)
  build / extracted-tree `pytest -q -x`     rc=0          PASSES
  installed-suite                           gate rc=0     PASSES
  test_every_fixture_data_file_is_named...  names it      FAILS
```

Both structural runs are silent, because a fixture is caught only through a test that runs and reads
it, and no such test exists yet. This is not "keep both to be safe": it is a coverage gap measured in
the same session as the retirement.

### The suite count, and why it is not the number the mandate carried

```
python -m pytest tests, run for this record on the shared tree
  4,537 passed, 10 skipped, 1 xfailed
  = 4,531 (mandate) - 1 (this guard) + 7 (D-045's new extractor tests)
```

Two workstreams moved the count in one round and neither number alone reconciles. Recorded here so
the next mandate quotes 4,537 rather than either workstream's local arithmetic.

### How it fails

**The retirement rests on `bench/*.py` staying out of the sdist.** That absence is what makes the
import raise in the extracted tree. `MANIFEST.in` ships `bench/results.json` and nothing else from
`bench/`; if a future commit ships the runners, `build` stops seeing this class and the only net left
is the job that is blind in two files. That is now written into `ci.yml` beside the retirement, and
it is a coupling between a manifest line and a check that nothing enforces.

Coverage also moves from the `test` job to `build`, which needs `[lint, test, resources]` — so the
class is caught later in the same run and never on a laptop before a push, and the message degrades
from one naming the offending file and line to a raw `FileNotFoundError` from a tarball under `/tmp`.
`data/LICENSES.md` is now held by one `test -f` line and nothing else, measured rather than assumed.
`EXPECTED_NON_PASSING` was documented, not shrunk. And every verdict here is Windows/CPython 3.13;
ubuntu/3.12 under GitHub's `bash -e` is unexecuted, as it was for D-040.

**Three of these measurements were wrong the first time and the reason is worth carrying.** A stale
`src/acronymkit.egg-info/SOURCES.txt` made setuptools ship files `MANIFEST.in` no longer named, so
cases `a`, `b` and `c` were run against unmutated artifacts and all reported "not caught". Every case
was re-run after `rm -rf src/*.egg-info`, and each mutation was then confirmed *at the artifact*
before a verdict was recorded. The uncaught version of that error reaches the same conclusion by
luck, on false evidence.

---

## D-049 — W11: the emission-model question is scoped, and the corpus that would sell it already has a one-line rule beating this library on the same label

**Status:** workstream scoped, **not adopted**; no decision taken · **Promotes:** the API question
posed and refused in D-041 · **Evidence:** `docs/notes/w11-emission-model.md`; `spans.plod.all.*` in
`bench/results.json`; `bench/splits.toml`; `src/acronymkit/models.py`, `bench/run_spans.py`

D-041 closed long-form-keyed precision filtering and found a larger question underneath it: **should
`extract()` be able to emit a short form with an absent or low-confidence long form?** It recorded
the question and declined to answer it. W11 is that question promoted to a workstream, scoped and
costed in `docs/notes/w11-emission-model.md`. **This record does not adopt it.** It fixes three
things a future round would otherwise re-derive, and one of them changes the case.

*A naming hazard, because it will bite:* **W11 is a workstream and experiment eleven is an experiment
number, and they are unrelated.** Experiment eleven is still free and W11 has not spent it.

### The number that decides how W11 is allowed to be pitched

Verified for this record out of the results file, not transcribed:

```
bench/results.json, spans.plod.all.tight.*   PLOD-CW, HELD OUT, uncontaminated,
exact convention, native offsets
  system                              sfP      sfR     sfF1
  acronymkit.high_precision.native   93.66    36.53    52.56
  allcaps  (one-line rule)           64.45    73.37    68.62   <- baseline wins
  oracle_definitional (no allcaps)            37.50
  oracle              (all rows)              82.36
  and the allcaps long-form row is printed as 0.00 rather than hidden
```

`predict_all_caps` in `bench/run_spans.py` **already emits short forms with no long forms**, and the
span harness scores it without complaint. So the emission model W11 proposes is not a capability this
library lacks — it is a floor this library is already below on the short-form label, on the only
held-out corpus that can see it.

**This is the D-044 shape arriving in the extraction half.** D-044 shipped a mechanism for the
disambiguator to decline to answer and then found the curve losing to counting words. W11's mechanism
would ship into a table where the trivial control already has the better F1. The consequence is
recorded as a constraint on the pitch rather than as a kill: **W11's product claim can never be "we
can emit unpaired short forms"** — only "we emit them at a precision materially above the all-caps
rule while adding recall the pair model cannot reach". `allcaps` is scored in token space with no
detokenisation, an advantage `bench/run_spans.py` states and calls small; it is small, and it does
not explain a gap of this size.

### The wire-contract cost, corrected downward

D-041 named the governed JSON contract, the golden fixtures and a JVM port as the R8 surfaces at
risk. Checked for this record, **none of the three is affected**:

```
docs/notes/governed-json-contract.md   AcronymPair appears ZERO times; §1 excludes
                                       the generation-side DTOs
tests/fixtures/governed/golden/        8 .jsonl files, all governed verbs.
                                       NO golden fixture for extract()
schemas/                               one file, acronym-engine-result.schema.json.
                                       AcronymPair has no published JSON Schema
docs/JAVA_INTEROP.md                   no JVM artifact exists and GraalPy cannot host
                                       extraction, so no JVM caller can break
```

What does bind is the Python wire, and it binds precisely: `extra="forbid"` makes any added key a
`ValidationError` for a consumer reconstructing the model from JSON, and `long_form=None` is a
`ValidationError` today. **R8 still applies — one Python package and one CLI JSON mode is a public
contract — but the change is narrow, not wide, and pricing it as wide would have killed W11 for the
wrong reason.**

### Two options refused on shipped evidence

**A long-form confidence answers nothing.** `_confidence(short, long)` is a *pair* confidence bounded
in `[0.6, 1.0]`; a low-confidence long form is still a long-form string and still a long-form false
positive, so pair atomicity is untouched. It reduces to a threshold on the long form alone, which
D-041 already lists as closed in advance.

**A `(0, 0)` sentinel corrupts output silently.** `_pair_anchor` and `_attach_sentences` both compute
`min(short_form_span[0], long_form_span[0])`, so every unpaired emission would sort to the front of
its document and be handed the document's first sentence. Both failures produce plausible output,
which is the worse kind. The surviving shape is a separate mention type behind an off-by-default
emission mode.

### What W11 may spend, and what it may not

W11 scores as `span_detection` on the short-form label and **needs no new `task`**, so the closed
vocabulary `bench/corpora.py` depends on is untouched. Its measurements belong on the two already
contaminated SDU-22 dev splits. `sdu21_ai` stays shut — D-043 calls it the only unspent capable
instrument for a span claim — and SDU-22 `train.json` is allocated elsewhere by D-047. **PLOD may be
scored and must not be diagnosed**: reading which short forms are missed and why is the act that
contaminated MED1250 and both SDU-22 dev splits, and PLOD is the only uncontaminated span corpus this
project has scored.

And `bench/scoring.py` keys MED1250 on `short\x00fold(long)`, so on the only corpus registered under
`task = "extraction"` an unpaired emission is a pure false positive: **the benefit is structurally
invisible there and the cost is fully charged.** R9's corpus-capability question, asked of W11 and
answered against it.

### How it fails

**The strongest number is one corpus.** PLOD is PLOS life-sciences text, already corrected once in
`bench/splits.toml` after being filed as a non-biomedical counterweight and cited as domain evidence
in two documents. Everything the pitch constraint rests on rests on it.

**The discriminator that would settle whether W11 is a real gap is specified and unrun**,
deliberately, because running it would have put a new un-gated figure into a `docs/*.md` page — which
is what R1 exists to stop. So this record scopes a workstream whose decision point has been defined
and not reached.

**The manifest's `18`-in-samples-with-zero-long-forms count hints against W11 and cannot settle it.**
It counts *samples* where nothing is defined; the question is over *surfaces*. A draft of the note
read it as proof the excess is repeat occurrences of locally defined abbreviations, which it is not,
and the note records the over-read rather than deleting it — it is the same compress-out-a-qualifier
failure that produced both dead phrasings of the abstention finding.

**"Scope W11 before W10" could not be fully checked**, because W10 is named nowhere in this
repository. The note states the reading it used — the held-out extraction corpus D-042 names as the
lead item on its adopted-library arm — and flags the one section that depends on it. D-048 takes the
same reading, independently.

**The note is unlinked.** Nothing in `docs/DECISIONS.md` pointed at `docs/notes/w11-emission-model.md`
until this record did. An unlinked design note is how a scoped workstream becomes an unscoped one two
rounds later.

---

## D-048 — `extraction` gold is an edge claim and `span_detection` gold has no edges. The empty row is real, and W10 is the lead item.

**Status:** analysis; taxonomy affirmed, no code changed · **Amends:** D-036 · **Bears on:** D-041,
D-042, D-043 · **Evidence:** `bench/run_spans.py::SpanPrediction`; `shortform.med1250_all.legend_exposure`,
`shortform.plod_all.corpus` in `bench/results.json`; un-gated probes in the workstream's scratch

`headline_capable("extraction")` returns empty. The question this round was whether that is a fact
about the world or an artifact of a vocabulary that split one task in two — because if MED1250 pairs
and SDU/PLOD spans were the same task under two names, `plod` and `sdu21_ai` would *already* be the
instrument and W10 would be unnecessary. **They are not the same task, and the empty row is real.**

### What one gold record is, and the half `TASK_GOLD_UNIT` leaves implicit

`TASK_GOLD_UNIT` is correct and states the *shape* of a record. The load-bearing property is
*relational*:

```
  task             gold carries an edge?                      vertices are
  extraction       YES, and the edge IS the whole gold        definitions only, NOT localised
  span_detection   NO, by the annotators' own convention      every occurrence, localised
```

MED1250's gold is `sf|lf` strings with no offsets anywhere in the file. PLOD and SDU-22 tag every
acronym occurrence, defined or not, and never say which long form belongs to which acronym. **Each
corpus holds exactly what the other lacks**, which is why neither derives from the other.

### The adversary the span corpora cannot catch

Two systems emitting exactly PLOD's gold spans, differing only in the pairing, scored through the
shipped `bench.run_spans.score` unmodified:

```
un-gated -- plod_cw all, 650 of 1,351 documents permuted, 1,376 of 1,804 gold
long forms mis-paired
  metric                 honest   permuted   delta
  long_form.exact        100.00     100.00    0.00
  long_form.overlap      100.00     100.00    0.00
  short_form.exact       100.00     100.00    0.00
  short_form.overlap     100.00     100.00    0.00
```

A system wrong about three quarters of PLOD's definitions is indistinguishable from a perfect one.
**The type that carries a prediction into the span scorer has no slot for the edge** — verified for
this record directly against the shipped dataclass, whose fields are exactly `short_forms` and
`long_forms`. `locate_pair` computes the edge and `localise` throws it away.

### Which derivations are legitimate, and which are invention

Coarsening a **prediction** from a pair to two span sets is mechanical and honest — the thing being
reshaped is our own output — and `run_spans.py` already does it. Enriching **gold** in either
direction is invention:

```
un-gated -- corpus structure only, no extractor run
                                        plod_cw all   sdu22 legal dev   sdu22 sci dev
  SFs with NO preceding LF at all       576  22.07%     365  30.54%     223  23.11%
  two defensible pairing rules DISAGREE 433  16.59%     134  11.21%      87   9.02%

  med1250, 1,221 gold pairs
    LONG form not a verbatim substring          24    1.97%
    SHORT form occurs more than once         1,018   83.37%
```

Nearest-preceding-long-form and best-character-alignment are both what an implementer reaches for,
and they disagree on one PLOD short form in six. The first is *undefined* on 22–31%. Going the other
way, localising a MED1250 pair to a span is a choice on five records in six.

### The escape hatch, and the arithmetic that closes it

Restricting to documents holding exactly one acronym and one long form forces the edge by counting
rather than by assumption — no invention. It still fails.

```
un-gated -- forced subset; Schwartz & Hearst validity implemented locally, deliberately
NOT acronymkit's own matcher, which would make the corpus answer with our own code
  documents with exactly one AC and one LF     plod 411    legal 158   sci 258
    do not align, lenient                       15  3.65%   5  3.16%    8  3.10%
    residue: 'UK' <- 'University of Manchester'    'SDS' <- 'system'
             'be' <- 'slip coefficient'           'r'   <- 'correlation'

on a 411-pair derived corpus:
  a 0.36-point movement (83.85 -> 84.21)      =   1.5 pairs
  invented / non-definitional gold at 3.65 %  =  ~15 pairs
```

**The noise floor of the derived gold is an order of magnitude larger than the effect it would
adjudicate.** That closes `bench/splits.toml`'s route 2 — "derive pairs by adjacency and label the
corpus derived pairing" — on arithmetic rather than on principle. Route 1 was already taken and is
gated.

### The repository's own practice already agreed

It coarsens predictions freely and has never once enriched gold. The single gold-side derivation is
`run_shortform.py::_text_and_gold_starts`, which feeds a corpus-capability count and never a scored
claim. That was hunted for a false zero, since `str.find` takes the first occurrence while — un-gated
— 29.73% of MED1250 gold long forms occur more than once: FIRST-occurrence 0, ANY-occurrence 0.
Confirmed for this record against the gated field — `shortform.med1250_all.legend_exposure` records
`gold_long_form_spans_after_a_separator = 0` of 1,221, and it is a true zero.

### The consequence for W10, stated plainly

**W10 — a held-out extraction corpus with annotator-asserted edges — is the LEAD ITEM, not the long
pole, and this record removes the only route by which it could have been avoided.** The two empty
rows invite "this project has no held-out number", and that is false:
`headline_capable('span_detection')` returns `['plod','sdu21_ai']` and
`spans.plod.all.tight.acronymkit.high_precision` is gated, held out and uncontaminated. What is
missing is a held-out number **for the shape of claim the README leads with**. The correct sentence
is: *the flagship claim is an edge claim, and no held-out corpus in this project contains edges.* The
weaker version invites "but PLOD is held out", whose answer is the adversary above.

Two limits on that, both load-bearing:

**One W10 does not close both empty rows.** The `disambiguation` row is empty for the same type
reason and a pair corpus does nothing for it (D-043). Anyone costing W10 as "closes the two gaps
`--check` prints" is costing the wrong artefact.

**The verdict is contingent on one open design question.** D-041's fork — should `extract()` emit an
unpaired short form? — is the single fact that would change which corpus the headline needs, because
answering it *yes* is the only route by which `plod` and `sdu21_ai` could become the flagship
instrument. D-049 scopes that question and does not answer it. **If it is ever answered yes, re-read
this record before funding W10.**

### How it fails

The 16.59% depends on which two pairing rules were picked; the claim is that two defensible rules
disagree materially at all, not that it is *the* invention rate. The forced-subset alignment test
is a proxy — character alignment is the field's criterion for a definition, not the definition of one
— and its residue contains errors of both signs; a first pass flagged 6.33% and inspection showed a
chunk of that was the aligner's strictness on plurals and hyphens rather than a corpus fact, so 3.65%
is published as a lower bound with the strict figure beside it. A crude "acronym-shaped
surface not in gold" figure exists in the workstream's report, is labelled a two-line heuristic rather
than PLOD's guideline, and **is not quotable**. Two of the three span corpora here are contaminated
tuning splits, used only for annotation *structure* — the same class of statistic as
`sdu22_ae_recall_ceiling`, selecting nothing — so the load-bearing adversary rests on PLOD alone.
`sdu21_ai` was not opened: its manifest entry declares "no annotator pairing", which is the
disqualifying property, so the adversary applies to it by type; writing its reader would buy exact
proportions and cannot change the verdict.

### One change recommended and not made

`TASK_GOLD_UNIT`'s `extraction` and `span_detection` entries state the shape of a record and not the
edge. One clause each — extraction's gold *is* an edge; span detection's is two unlinked vertex sets
with a wider extension — would put this whole argument where the next person finds it, in the same
place the `identifier_segmentation` entry already does that job well. That is a `tools/splits.py`
edit and it is owed.

---

## D-047 — SDU-22 legal `train.json` is allocated to the legend flag's cost, experiment nine loses, and one runner invocation answers both arms anyway

**Status:** allocation made; loser named; trigger recorded · **Resolves the collision found in:**
D-043 · **Amends:** D-032 (experiment nine's precondition), D-039 (the precondition for flipping the
legend default) · **Evidence:** `bench/splits.toml` `[corpora.sdu22_ae_legal]`,
`[corpora.sdu22_ae_scientific]`; `bench/run_shortform.py` `_VARIANTS`;
`shortform.sdu22_ae_*_dev.corpus` and `.legend_cost` in `bench/results.json`

D-043 recorded that SDU-22 `train.json` is claimed twice — it is D-039's named precondition for
flipping the legend default and D-032's named precondition for reopening experiment nine — and that
whichever runner touches it first spends it incidentally. **Leaving both claims live is how a budget
gets spent by accident, so this record allocates it rather than letting priority be inferred from
whoever runs first.** The allocation is written into `bench/splits.toml` as well, because the person
about to spend it will have that file open and not this one.

### First, what is actually scarce, because it is less than R3's language implies

Both SDU-22 AE entries are **already** `role = "tuning"` and `contaminated = true`; the corpus offers
no held-out arm and never did, since both English test splits carry zero labels. So spending
`train.json` costs no blind split. **What it costs is the last UNMINED arm of the corpus** — a
within-corpus arm whose misses nobody has read, which can be run against once before it becomes as
contaminated as the dev splits it sits beside. That is a real budget and a smaller one than "a
held-out corpus", and an allocation that over-states the stake invites the next round to over-pay for
it.

### The allocation

```
[corpora.sdu22_ae_legal] train.json -- 3,564 unread samples, ONE unmined read
  ALLOCATED TO   the legend flag's precision cost on an arm that was not mined
                 to invent it (D-039, D-045). W8 owns the read: it decides when
                 the split is read, which miss decomposition is published, and
                 what may be concluded.
  LOSER          experiment nine, the two-word bracketed short form (D-032).
                 It stays HELD. Holding it costs nothing; the legend flag is
                 SHIPPED and its cost is unmeasured on any unmined corpus,
                 which is a live liability rather than a parked one.
  FREE RIDE      `bench/run_shortform.py --variants` scores `two_word` and
                 `legend` in ONE invocation over the same corpus. The run that
                 spends this split MUST save the `two_word` row too: it costs
                 zero additional reads and it is the only way experiment nine
                 is ever answered once the arm is mined.
  NOT PERMITTED  experiment nine commissioning a read of its own, or a miss
                 decomposition of its own. If the two arms disagree about what
                 to publish, W8's question governs.
```

The free-ride clause is the part that is checkable rather than argued, and it was verified for this
record: `_VARIANTS` in `bench/run_shortform.py` carries `("two_word", ...)` and `("legend", ...)` as
rows of the same tuple, with `two_word` compared against `baseline` and `legend` against
`balanced_trim`, which is the comparator D-039 requires. **The collision D-043 named is genuine, and
it is a collision over who owns the read and the decomposition — not over which arm gets scored.**

### The split can answer both questions, and that is a counted fact rather than an assumption

R9's corpus-capability question, asked *before* the spend rather than after it:

```
bench/results.json, shortform.sdu22_ae_legal_dev.corpus and .legend_cost
  gold short-form spans                        1,213
  of them MULTI-TOKEN  (experiment nine)          26     2.14 %
  separators           (the legend rule)         138
  legend pairs emitted, high_precision            83
  separators opening a number                      0     0.00 %

  compare PLOD, on which experiment nine was refused:
  shortform.plod_all.corpus.gold_short_form_spans_multi_token   0 of 2,869
```

**PLOD carries zero multi-token gold short-form spans, so it could not score experiment nine even in
principle; the legal split can.** That is why D-032's precondition named this file, and it is why the
free-ride clause is worth writing rather than waving at.

Scaling from the ceiling basis already in the manifest — legal train holds 9,532 gold acronym spans
against dev's 1,213, a factor of 7.86 — dev density projects roughly 200 multi-token spans and about
1,100 separators on train. **Those two figures are arithmetic on a gated dev count and are not
measurements**; they are here to say the arm is worth spending, not to be quoted.

### What the spend can buy, and what it cannot — this is the part that must not be lost

**It cannot license flipping the legend default on its own.** D-039's first reason for shipping the
flag off is that *no uncontaminated, structurally capable corpus exists in this repository*, and a
within-corpus tuning arm does not answer that. D-039 says so itself: this split "buys within-corpus
corroboration and not generalisation".

**And it cannot answer the risk the flag is actually off for.** D-045 measures the census: legal dev
has `0 of 138` separators opening a number. The legal split is where the legend class is dense and
where the equation surface is *absent*. So spending this arm measures the legend class's precision
cost in institutional prose and says nothing whatever about `Tsat=Tamb`. Somebody who spends it and
then reports "the equation risk is measured" has repeated D-045's own finding one corpus over.

Stated positively, so the spend is not merely fenced: what it buys is the one thing nothing else in
this repository can buy — **an honest precision delta for a shipped flag, on an arm that was not
mined to invent it.** That is exactly the hole D-045 opens and cannot close, and it is worth one
unmined split.

### The trigger that reverses the allocation

```
  the allocation LAPSES and experiment nine inherits the split when either:
    (a) a corpus that annotates legend definitions, is structurally capable,
        and can be declared uncontaminated is registered -- which is D-039's
        real precondition and makes this arm redundant for W8; or
    (b) `legend_syntax` is deleted rather than defaulted, at which point W8's
        question no longer exists.
  NOT a trigger: experiment nine being older; a workstream needing a number
  this round; the legend work stalling. Priority does not transfer by default.
```

### How it fails

**An allocation in a D-record is not a mechanism**, which is D-043's own complaint about the AD
`test.json` reservation and it applies here in full. Nothing in `tools/splits.py` refuses a run
against `train.json`; the guard is that somebody reads the manifest note this record puts in front of
them. Writing it in two places — here and in `bench/splits.toml` — is deliberate and is also exactly
the duplication D-045 warns turns one description stale without anybody noticing.

**The free-ride clause could be read as making the allocation moot.** It does not: whoever owns the
read owns the *decomposition*, and the decomposition is what mines the arm. But a reader who takes
only the fenced block could conclude the collision was imaginary, and it was not — D-043 was right
that first-touch was deciding it.

**The scaling figures are extrapolation from one dev split** and the recall-ceiling basis is the only
evidence that legal train resembles legal dev in structure. It decomposes well there (55.04<!--claim:shortform.sdu22_ae_legal_train.corpus.ceiling_pct:.2f-->% against
55.15<!--claim:shortform.sdu22_ae_legal_dev.corpus.ceiling_pct:.2f-->%), which is why the extrapolation is offered at all, and it is still an extrapolation.

**Scientific `train.json` is left unallocated on purpose, and that is the weakest line in this
record.** Both live claims name the legal split, so allocating the scientific one now would mean
inventing a use for it — which is the failure D-043 corrected when the AD reservation attracted a
proposal it could not serve. What is written instead is a *rule*: the first spend of scientific
`train.json` requires its own record, and first-come is refused. That is a checkable state rather than
a drift, and it is not a use.

---

## D-046 — A revert criterion must name a corpus where the mechanism fires, and the firing count is what establishes that

**Status:** project rule, no code changed · **Generalises:** D-045 · **Bears on:** D-032, D-033,
D-039 · **Evidence:** `shortform.med1250_all.legend_firing` and
`shortform.med1250_all.legend_exposure` in `bench/results.json`; D-039, D-032, D-033

D-045 is a finding about one flag. This record is the transferable half, separated because the next
person to write a revert criterion will not be reading about legend syntax.

### The rule

**A revert criterion is only a test if it is evaluated on a corpus structurally capable of exhibiting
the phenomenon the criterion is about, and the thing that establishes capability is the number of
times the mechanism FIRES — not the number of documents, not the corpus's reputation, and not the
fact that the score did not move.**

The failure mode is specific and it is quiet:

```
  the criterion       "if MED1250 precision moves at all, revert"
  the outcome         precision did not move, on any split, under any profile
  the reason          the rule emitted 0 pairs on 1,252 documents
                      -- shortform.med1250_all.legend_firing, verified for this
                         record: legend_pairs_emitted = 0 for all three profiles
  what was reported   the criterion passed
```

Bit-identical output was evidence the rule never ran, and it was read as evidence the rule is
harmless. Nobody was careless: the criterion was written by a mandate, accepted by a workstream and
reported as passed, and D-039 even carried `gate_a_prefix_aligns = 0` in its own evidence block
without reading it as the reason the criterion held.

### Be exact, because the strong version of this is false

**The criterion was not literally untestable.** A rule that fired on MED1250 and was wrong would have
failed it. What it tested is far narrower than what it was read as testing: *that the gates refuse a
numeric assignment*. On that corpus 394 of 401 separators open a number and, under the loosest shipped
profile, 396 reach the alignment, which refuses every one. **A gate under load is real evidence.** It
is not evidence about what the rule costs when it emits, because on that corpus it never does.

So the rule above has a second clause: **a criterion evaluated where the mechanism does not fire is
testing the gate, not the cost, and must say which of the two it tested.**

### Was this already recorded? Partly, and in the wrong shape

Grepped for the mechanism before writing this, as R9 requires. Three neighbours exist and none of
them is this rule:

```
  D-032   PLOD "cannot show the upside even in principle" (0 multi-token gold
          short-form spans) -- recorded as a CORPUS PROPERTY qualifying a
          result, not as a defect in a decision procedure
  D-039   legend_exposure's zeros are published in the record itself, as a
          caveat under the table -- "that table alone says almost nothing"
  D-033   R9's fifth question asked of a TEST SUITE: an idempotence test that
          varied identifiers and policies but never catalogs, and so was
          structurally incapable of firing however long it ran
```

D-033 is the closest and it is about a test that could not fail. This one is about a *criterion* that
could not fail — the same arithmetic, applied to the decision procedure rather than to the assertion.
The distinction is worth its own number because the two are found by different searches: a person
auditing tests finds D-033, and a person writing "revert if X" finds nothing.

### What a criterion has to carry from here

```
  1. the corpus, and the count of times the mechanism fires on it. Zero is a
     valid answer and it INVALIDATES the criterion rather than satisfying it.
  2. which of two things is being tested -- that the gate refuses, or what the
     rule costs when it emits. They need different corpora and only one of them
     is a safety property.
  3. the INCREMENT, not the corpus total, wherever the mechanism touches a
     minority of predictions. A corpus total dominated by predictions the
     change cannot reach will report "no movement" for a change that is wrong
     about everything it touches.
```

And the negative half, which D-045 observed rather than invented: **a replacement threshold must not
be fitted to the data that has just been collected.** D-045 deliberately wrote no numeric cut-point
to replace the retired criterion, because a cut-point chosen after seeing the measurement is a tuned
parameter wearing a rule's clothes — D-044's own objection, and D-032's reason for using the
project's existing 16-word `SKIPPABLE` set rather than a set chosen after seeing the corpus. The
worst measured values are the reference points instead.

### How it fails

**This rule is more expensive than it looks.** Establishing a firing count means building an
instrument before writing the criterion, and D-045 needed a new runner mode over 1,252 documents and
six full corpus passes to produce one. A round under time pressure will write the criterion first and
call the instrument a nice-to-have, which is exactly what happened.

**"Structurally capable" is not binary and this record states it as if it were.** MED1250 is blind to
the legend *class* and loads the *gate* heavily; PLOD has 0.89<!--claim:shortform.plod_all.legend_exposure.gold_long_form_spans_after_a_separator_pct:.2f-->% capability and 12 predictions, which
is neither zero nor useful. A count with no threshold beside it invites the next person to declare
`n = 12` sufficient, and no threshold is offered here on purpose — see the fitting objection above,
which cuts both ways.

**It cannot be enforced.** Nothing in `tools/` reads a revert criterion, and the criteria live in
mandates and D-records rather than in code. This is prose defending against prose, which is the
weakest instrument this project has and the only one available for a rule about how decisions are
worded.

---

## D-045 — A revert criterion evaluated on a corpus the rule never fires on tests the gate, not the cost

**Status:** criterion retired and replaced; feature kept, default unchanged ·
**no experiment number spent — experiment eleven is still free** · **Amends:** D-039 ·
**Generalised by:** D-046 · **Evidence:** `shortform.med1250_all.legend_firing`,
`shortform.sdu22_ae_{legal,scientific}_dev.{high_precision,general,biomedical}.legend_cost` in
`bench/results.json`; `bench/run_shortform.py --legend-cost`; `docs/EVALUATION.md`;
`tests/test_extractor.py`

D-039 shipped `legend_syntax` against an absolute criterion — *if MED1250 precision moves at all,
revert* — and recorded that the `legend` row was bit-identical to `balanced_trim` on every field, all
three profiles, both splits. That is true. It is also the wrong thing to have been reassured by.

### The rule emits nothing there, and now that is a number rather than an inference

```
bench/results.json, shortform.med1250_all.legend_firing
through extract() itself, 1,252 documents, MED1250 -- TUNING SPLIT
  profile          legend pairs emitted   docs firing   exact P off -> on
  high_precision            0                  0          92.46 -> 92.46
  general                   0                  0          92.39 -> 92.39
  biomedical                0                  0          86.43 -> 86.43
  separators 401, of which 394 open a number (98.25 %)
and, from shortform.med1250_all.legend_exposure:
  gold long forms beginning after a separator: 0 of 1,221
```

D-039 already carried `gate_a_prefix_aligns = 0` in `legend_exposure`; what it did not do was read
that number as the reason the criterion held. **Bit-identical output was evidence the rule never ran,
and it was read as evidence the rule is harmless.** The transferable form of that is D-046; what
follows is this flag.

**Be exact, because the strong version of the correction is false.** The criterion was not literally
untestable — a rule that fired on MED1250 and was wrong would have failed it. What it tested is far
narrower than what it was read as testing: that the gates refuse a numeric assignment. It cannot test
what the rule costs *when it fires*, because there it never does. That narrow test is worth
something and this record keeps it: 394 numeric right-hand sides, 396 walked to the alignment under
`biomedical`, every one refused. A gate under load is evidence. It is not evidence about emission.

### The cost, measured where the rule fires

```
bench/results.json, shortform.sdu22_ae_*_dev.*.legend_cost
SDU@AAAI-22 AE dev -- TUNING, CONTAMINATED for exactly this change: the audit
decomposed both splits' misses by legend separator to rank this proposal.
Comparator balanced_trim, as D-039 requires.

  split / profile              added   SF exact P        SF overlap P
  scientific / high_precision     39   95.90 -> 95.67    97.78 -> 97.44
  scientific / general            39   95.90 -> 95.67    97.78 -> 97.44
  scientific / BIOMEDICAL         52   94.29 -> 92.27    96.30 -> 94.13   <- worst
  legal      / high_precision     83   93.66 -> 94.41    99.80 -> 99.83
  legal      / general            83   93.67 -> 94.42    99.80 -> 99.83
  legal      / biomedical         88   92.56 -> 92.65    98.59 -> 97.95
  In this table no F1 falls, on either label, either convention. Neither that
  nor anything else here extends past these six runs -- PLOD and MED1250 were
  not re-measured for it.
  Recall ceilings 74.23 % and 55.15 %; every recall stays under its own.
```

**The worst row is a row the shipping table did not contain.** `--spans` runs `high_precision` only
and three profiles ship, so D-039's "worst move anywhere `0.34` points" is scoped correctly by its own
code fence and is still incomplete: over all three profiles the worst move is `-2.18`. Nothing was
mis-stated; one profile was measured, three ship, and the phrase "worst move anywhere" invites a
reading the table does not support. That phrase is what needs amending, not the number, and D-039 now
carries a pointer here.

### R9.5, asked of this measurement rather than only of the last one

The proposal reaching this round was that the precision risk lives in scientific text, because that is
where equations and legends are both dense. **On the corpora this repository reads they are
anti-correlated, and the census is what shows it.**

```
separators opening a number (a digit, or a signed digit, after the blanks)
  MED1250                  394 / 401   98.25 %    legend pairs emitted:   0
  SDU-22 AE scientific       5 / 147    3.40 %    legend pairs emitted:  39
  SDU-22 AE legal            0 / 138    0.00 %    legend pairs emitted:  83
```

So measuring the scientific split does not close the hole D-039 left; it **relocates** it. The corpus
that loads the gate cannot show the class, the corpora that show the class barely load the gate, and
PLOD — the one held-out arm — has 0.89<!--claim:shortform.plod_all.legend_exposure.gold_long_form_spans_after_a_separator_pct:.2f--> % capability and 12 predictions. **The genre the risk was named
for, engineering and physics body text, is still unmeasured**, which is the same reason the flag
shipped off and the reason it stays off. D-047 records what the one remaining unmined arm can and
cannot buy against this, because the answer is "not this".

Exactly one added pair across all six runs is an equation: `X -> x|W1`, from
`P (X = x|W1 = w1, . . . , WN = wN )`, and it needs `biomedical` — the only shipped profile admitting
a one-character short form with no uppercase requirement — to exist at all. The rest of the residue is
single-letter legends the corpus does not tag.
`tests/test_extractor.py::test_the_one_equation_a_loosened_gate_admits` pins both halves, so the loose
profile's behaviour is a decision rather than a rediscovery: pinning only the refusal would leave the
loose profile a surprise, and pinning only the admission would read as approval.

### One property that got stronger

`increment_accounts_for_every_new_false_positive` is true on all six records: in every
label/convention cell the corpus's false-positive count rises by exactly the number of added pairs
that missed gold. "The flag adds candidates and re-ranks none" was asserted on synthetic documents in
D-039; it now holds at corpus scale, which is the region where D-012's pseudo-precision diagnosis does
not bite. The `high_precision` scientific row also reproduces the already-published
`.legend`/`.balanced_trim` figures to the digit, so the new instrument agrees with the existing
`--spans` scorer rather than being a second, flattering implementation of it.

### What is retired, and what replaces it

"MED1250 precision does not move" is not a safety property of this rule and must not be quoted as one.
A replacement must be evaluated on a corpus where `legend_pairs_emitted > 0` and must name the
**increment**, because the corpus total is dominated by predictions the flag cannot change. **No
numeric cut-point is written here on purpose**: a threshold fitted to the data that just produced it
is a tuned parameter wearing a rule's clothes. The worst values above are the reference points.

Note what is *not* retired. The flag stays, defaulted off. Deleting it would have been a revert
justified by the same corpus that could not justify shipping it — the identical error with one sign
flipped — and "a feature nobody can evaluate is a maintenance liability" is answered by evaluating it,
which is what this record does.

### How it fails

**Every new figure is a tuning number** from the two splits `bench/splits.toml` declares contaminated
for precisely this change, and the worst row rests on 52 predictions — 16 of which are predictions the
corpus does not tag as acronyms. No split-half was run, so `-2.18` has no stability estimate.

**`_numeric_right_hand_side` is a proxy and it under-counts.** It scores only digit-initial right-hand
sides, so `Dbest = argmaxD P (D|B)` and `Nu' (a) = Nu (a) A(P (a)~ P' (a))` count as prose. The
narrow definition was chosen on purpose — a wider one stops matching the gate the code implements, and
widening the gate to match a sentence is what D-039 refused — but **3.40<!--claim:shortform.sdu22_ae_scientific_dev.high_precision.legend_cost.separators_numeric_right_hand_side_pct:.2f--> % is a FLOOR on the equation
surface, not a measurement of it**, and a reader who takes it as the equation density is being
under-informed by the instrument.

**The attribution of the false positives is an explanation and not a deduction.** Most of the residue
is unannotated legends, and it would be convenient to call the precision loss an annotation artifact.
The tables report the raw delta with nothing adjusted, and the residue list is in `bench/results.json`
so the classification can be disagreed with. An extractor scored against a corpus is scored against
that corpus's decisions.

**`--legend-cost` is char-span only**, so PLOD — token-indexed, and the one held-out arm — contributes
nothing beyond its exposure figure. `legend_firing` re-runs the extractor six times over 1,252
documents and records the settings it measured rather than what the shipped enum means, so a drift in
`_PROFILES` would go unremarked.

**And this decision is now described in five places** — D-039, this record, the CHANGELOG, the
extractor docstrings and `docs/EVALUATION.md`. That is one more than the four the workstream counted,
because this record is itself the fifth. Four descriptions of one decision is how one of them goes
stale without anybody noticing; five is worse, and the honest mitigation is that the numbers all cite
run ids and only the prose can rot.

---

## D-044 — Definition of Done 1: abstention exists, defaults off, and loses to a word-count baseline across most of its range

**Status:** met in mechanism, not met in value · **Amends:** D-030 ·
**Evidence:** `disambiguation.sdu21.abstention_curve` in `bench/results.json`,
`src/acronymkit/disambiguation.py`, `docs/EVALUATION.md`, CHANGELOG `[Unreleased]`

The first item on the definition of done was "the disambiguator can decline to answer". It can. The
field ships, the threshold ships, the curve is published with its losing comparison in the same
table, and the CHANGELOG says in user terms what the trade is. **Recording that as "done" without the
second half would be the exact move this file exists to make expensive**, so here is the second half.

### What was actually delivered

`DisambiguationResult` carries a read-only `margin` and a derived `abstained`;
`LexicalDisambiguator(config, dictionary, tokenizer, min_margin=...)` refuses below the threshold;
the default is off and D-030 argues it stays off. That is a mechanism, and it is complete.

### And here is the curve it produces

```
bench/results.json, disambiguation.sdu21.abstention_curve
SDU@AAAI-21 AD dev -- TUNING, CONTAMINATED. Every threshold below is read off
the split it is scored on. `most_frequent` is scored on the IDENTICAL answered
subset at each gate, so the last column is not a different question.

  gate   coverage %   accuracy answered   F1      most_frequent, same subset
  0.00     100.00          41.65        41.65           72.84   <- baseline wins
  0.01      70.53          46.32        38.32           72.78   <- baseline wins
  0.02      50.91          52.27        35.27           72.14   <- baseline wins
  0.05      29.52          64.81        29.54           69.40   <- baseline wins
  0.10      22.78          70.00        25.98           68.30
  0.15      16.77          72.93        20.95           66.09
  0.20      11.33          74.04        15.07           64.05

  at the reference gate, most_frequent STILL wins on candidate-set sizes ['3','4']
    -- 2,004 instances, 32.38 % of the split
```

Two readings, both true, and the second decides the status.

**The gate does what it says.** Answered accuracy rises monotonically with the threshold and gains
more than thirty points end to end. As a precision instrument it works.

**It does not beat counting words.** `most_frequent` at full coverage scores 72.84. The gated system
does not reach that answering *any* fraction of the split until gate 0.15, where it answers under a
sixth of the questions, and its F1 falls monotonically the entire way. Below the crossover the
trivial baseline is ahead on the very same answered questions. There is no threshold on this curve at
which turning abstention on makes the library better at the shared task than a frequency table would
be.

### Why that is not simply "the feature failed"

`most_frequent` is not free and this record will not pretend it is. It needs the shared task's
counted training instances — precisely the data D-020 established this project cannot obtain under a
licence it can ship. **A caller with no counts cannot run the control that beats the gate**, which is
what makes abstention a real option for a real caller and simultaneously means the comparison is not
a like-for-like defeat. D-029 sharpens it from the other side: on the default no-dictionary path a
margin is defined on one instance in 6,189, so the feature is inert for anybody who has not already
brought a dictionary.

### The status this earns

```
Definition of Done 1 -- "the disambiguator can decline to answer"
  mechanism      SHIPPED   margin field, abstained flag, min_margin, default off
  documentation  SHIPPED   docs/EVALUATION.md carries the curve WITH the losing column
  value          NOT MET   no gate on the measured curve beats a frequency table,
                           and the measurement is a tuning split
```

**Met in mechanism, not yet in value.** Closing it in value needs one of: a frequency prior this
project can legally ship (D-020, still open across ten checked sources); a cost model from the caller
that makes precision-at-low-coverage the right objective, which the library cannot see; or a
confirmation on a blind split, which is D-043's reserved resource and its stated trigger.

### How it fails

Reading the mechanism half as the whole item is the failure, and only prose stops it. The curve is
one corpus, one domain, one contaminated tuning split with a four-point split-half spread — wider
than several differences the tables invite a reader to weigh. And "loses to a trivial baseline" is a
deliberately unfair headline for a control that needs data D-020 says is unavailable; the fair
version is in the paragraph above, and a reader who quotes the heading alone has been misled by this
record rather than by the numbers.

---

## D-043 — SDU-21 AD `test.json` gets a named use and a trigger, and the corpus that would confirm D-039 is a different one

**Status:** reservation restated with a trigger; one proposed re-designation refused as a category
error · **Amends:** D-029 · **Evidence:** `bench/splits.toml` `[corpora.sdu21_ad]`,
`[corpora.sdu21_ai]`, `[corpora.plod]`; `tools/splits.py`

SDU@AAAI-21 AD `test.json` has been reserved and unspent since D-017, and R3 has protected it every
round since. A reserved resource with no assigned use is how a budget drifts: each round it survives
because nobody had a reason to spend it, which is not the same as it being reserved *for* something.
This record gives it one, with the condition that fires it.

### The re-designation that was proposed, and why it does not fit

The proposal reaching this round was to spend AD `test.json` confirming D-039's legend-syntax
precision claim out of sample. **That is a category error and it is recorded as a correction rather
than transcribed as a plan.**

```
tools/splits.py, the manifest as it stands
  sdu21_ad             task = disambiguation           role = tuning     contaminated = true
  sdu21_ai             task = span_detection           role = held_out   contaminated = false
  plod                 task = span_detection           role = held_out   contaminated = false
  med1250              task = extraction               role = tuning     contaminated = true
  sdu22_ae_legal       task = span_detection           role = tuning     contaminated = true
  sdu22_ae_scientific  task = span_detection           role = tuning     contaminated = true
  sec_xbrl             task = identifier_segmentation  role = held_out   contaminated = false
  socrata              task = identifier_segmentation  role = held_out   contaminated = false
```

D-039 changes which *surfaces the extractor scans* and is scored as span detection. `sdu21_ad`
annotates one occurrence plus a fixed candidate set — it holds no spans to score and no short forms
to extract. Its `test.json` could not confirm a precision claim about a span rule if it were spent
tomorrow. This is the hole D-036 closed one call earlier in the pipeline: a corpus being `held_out`
and unspent says nothing about whether it can adjudicate *this* claim, and the task is the missing
half of the question. The proposal reached this file because the reservation had a role and no
purpose attached to it, so any unspent thing looked like the right instrument.

### The named use, and the trigger that spends it

```
[corpora.sdu21_ad] test.json -- reserved, unspent, ONE spend
  named use      confirm the cut-point of an abstention policy proposed for
                 ON-BY-DEFAULT shipping
  trigger        a `min_margin` default other than "off" is proposed, with a
                 specific threshold and a stated cost model behind it
  NOT a trigger  a sanity check; a second look at the curve; a re-run after a
                 tokenizer change; confirming that abstention "still works";
                 any figure whose absence would not block a decision
  on spend       the corpus becomes contaminated for disambiguation permanently,
                 and this project has NO remaining blind arm for that task
```

The manifest already carried the first line of this in prose — reserved for confirming a shipped
abstention policy, and not available for a sanity check, a curiosity or a second look. What it lacked
was the trigger, which is the part that makes a reservation checkable: **until somebody proposes
turning abstention on by default with a number attached, there is nothing to confirm and the split
stays shut.** D-044 records that no such proposal is currently defensible, so the trigger is not
close to firing.

The cost of spending it is not abstract. `tools/splits.py --check` already prints that no
uncontaminated corpus carries `role = "held_out"` for `task = "disambiguation"`. AD `test.json` is
the only thing that could ever change that line, and spending it removes the possibility rather than
using it.

### What D-039's confirmation would actually cost, recorded separately

The right instruments for an out-of-sample span claim are `sdu21_ai` and `plod` — both
`task = "span_detection"`, both `role = "held_out"`, both `contaminated = false`.

```
plod        already scored for D-039. Held out, honest, and nearly blind:
              16 of 1,804 gold long forms begin after a separator   (0.89 %)
              -- bench/results.json, shortform.plod_all.legend_exposure
            It agrees on every field and the agreement is worth little.
sdu21_ai    role = held_out, contaminated = false, status = "reader_not_written".
            The only unspent capable instrument this project has for a span
            claim. Spending it on a default-off flag burns the arm that a
            DEFAULT change would need.
```

So D-039's confirmation is available, it is not free, and it should not be taken now: the flag is off
by default, so nothing downstream depends on the answer. **The precondition D-039 itself names —
SDU-22 `train.json`, unread, but `role = "tuning"` for the whole corpus — buys within-corpus
corroboration and not generalisation**, and it is also the arm D-032 reserved for reopening
experiment nine. One unread split cannot settle two questions; whichever is asked first spends it.

### How it fails

A trigger written into a D-record is not a mechanism. Nothing in `tools/splits.py` refuses a run
against AD `test.json`, and the file is fetchable from the same pin as the dev split — the guard is
that somebody has to read this entry, which is the same guard that has held for six rounds and is
still only a convention. The named use also assumes the next question worth a blind split is an
abstention default; if the disambiguator changes shape entirely, this reservation will look like it
was held for a question nobody ended up asking, and re-designating it needs its own record rather
than a quiet edit to the manifest note.

---

## D-042 — Zero external users is a strategy question, not a descope, and this record does not answer it

**Status:** open fork, recorded rather than decided · **Amends:** D-029 ·
**Evidence:** `docs/DECISIONS.md` D-029, `tools/splits.py --check`, `bench/splits.toml`

D-029 found that this project has no external users and used the finding to descope one workstream.
Then the finding was absorbed. Over the following rounds it has been cited as a reason not to worry
about compatibility and as a reason not to build a default blend, and in both cases it did useful
local work — but its largest consequence is not local, and leaving it unstated is how it disappears.

### The fork

**Is "world class" a technical target or an adopted-library target?** The two answers do not share a
queue.

```
If the target is TECHNICAL -- "the extractor and the governed subsystem are as
good as the state of the art, and the evidence for that is public"
  the queue is roughly the one being executed: extraction quality, span rules,
  the governed segmentation figures, offline guarantees, wire contracts.
  D-029 is then a fact about the calendar and nothing more.

If the target is ADOPTED-LIBRARY -- "people who have this problem use this"
  the queue is wrong at the top. The blocking item is not a rule or a flag; it
  is that a prospective adopter cannot check the central claim. Per
  `python tools/splits.py --check`, run for this record:
      extraction               no uncontaminated held-out corpus
      disambiguation           no uncontaminated held-out corpus
      span_detection           plod, sdu21_ai              held out
      identifier_segmentation  sec_xbrl, socrata           held out, D-036
  A citable, uncontaminated, held-out gold standard for the tasks the README
  leads with is then the LEAD ITEM, not the long pole.
```

### Two consequences that already landed, named so they are not re-derived

**The kill fired on the weighted-dictionary default blend.** D-029 descoped it on the strength of
zero external users and it is on the prohibited list. That is the *correct* action under either arm
of the fork, and it is the cheap case: the work served callers who do not exist and it had no
independent technical argument either.

**A resolver hook drops below a span rule, and the reason differs by arm.** Work whose value is "an
existing integrator can now do X" is worth less than work whose value is "the library is more
accurate" when the integrator count is zero, so on the adopted-library arm a resolver hook sits below
D-039's legend work. **What the fork actually changes is neither of those two items.** It changes
whether the next several rounds go into rules and flags at all, or into a corpus somebody outside
this repository would accept.

### What would settle it, stated so it can be checked rather than argued

```
Evidence that the target is ADOPTED-LIBRARY
  a named prospective adopter, or one human-filed issue, or one downstream
  dependent -- D-029's re-runnable block is the instrument, and it MUST be
  re-run, because D-029 says of itself that its numbers decay fast
  any request for a number this project cannot currently produce blind

Evidence that the target is TECHNICAL
  the author states it. That is not a cop-out: on this arm the audience is the
  author and the artefact, and no external instrument can distinguish "nobody
  wants this" from "nobody has been told about it" -- D-029's own words about
  absence of evidence apply here in full.
```

**This record does not decide the fork and will not pretend to.** The evidence available cannot: the
whole content of D-029 is that public instruments cannot see private use, so "no adopters" is not
observable, only "no observable adopters". What is decidable is that the question should be asked
before the next round's queue is set, and that it has been answered implicitly — by continuing to
execute the technical queue — for four rounds without anyone writing down that a choice was made.

### How it fails

Framing this as a binary is the first thing wrong with it: a project can pursue a held-out gold
standard *and* ship rules, and the real question is ordering under a fixed budget rather than
exclusion. The fork inherits every weakness of D-029 — a two-week-old repository, live counters, one
reading, and a design that explicitly targets air-gapped deployments leaving no trace by
construction. And the second consequence above is the softest: "a resolver hook serves callers who do
not exist" is an argument about priority that would survive being wrong about the user count, because
the hook has no technical argument either way. If this record is used to kill a resolver hook
outright rather than to rank it, it has been over-read.

---

## D-041 — This library emits pairs, so deleting a bad long form deletes a good short form. That closes long-form-only precision filtering, not one rule.

**Status:** structural constraint, derived from experiment ten's evidence ·
**Supersedes the log-entry reading of:** D-032 experiment ten ·
**Evidence:** `shortform.sdu22_ae_legal_dev.function_word_exposure`,
`shortform.sdu22_ae_scientific_dev.function_word_exposure`,
`shortform.med1250_all.function_word_exposure`, `shortform.plod_all.corpus` in `bench/results.json`

D-032 recorded experiment ten as a rule that was measured and reverted. That is true and it
under-sells the evidence by a wide margin. **The mechanism that refused the rule is not a property of
the rule.** It is a property of what `extract()` returns, and it refuses in advance every rule of the
same shape — which is why it needs a number of its own that a future round will hit when it greps for
the mechanism instead of for "function word".

### The constraint

**`AbbreviationExtractor` emits a pair. The pair is atomic. So any filter that rejects a candidate
because of its LONG form also deletes the SHORT form standing beside it — and on every corpus that
scores the two labels separately, a long-form false positive removed is a short-form true positive
destroyed at the same instant.**

Experiment ten measured that at full strength, and it is not a near-miss. Re-derived from the gated
`cases` arrays for this record rather than transcribed:

```
bench/results.json, shortform.*.function_word_exposure
  the rule: reject a long form whose first word is in _strategies.SKIPPABLE

  corpus                          deletes   short form correct   long form correct
  SDU-22 legal dev (tuning)        6 of 489          6                   1
  SDU-22 scientific dev (tuning)   5 of 585          5                   2
                                  -----            ---
                                  11 of 11 deletions carried a correct short-form span
  MED1250 (tuning)                 3 of 1,021        0                   0
```

Eleven of eleven. Not most, not a majority — every single deletion on both corpora that can see the
class removed an acronym token the annotators had marked. MED1250 shows zero collateral because it
scores pairs, not labels: the collateral is invisible there by construction, which is precisely why
the rule looked free on the one corpus that was asked first.

### Why the ratio is structural rather than a bad draw

An acronym token is the least ambiguous annotation these corpora carry; a long-form boundary is the
most contested. So a filter keyed on the long form is keyed on the noisy half of the pair and pays in
the clean half. The arithmetic does not depend on which words are in the rejection set, on how the
set was chosen, or on whether the underlying long form was genuinely wrong. It depends only on the
fact that one prediction carries both labels.

```
Rules this closes in advance -- all long-form-keyed, all pair-atomic:
  reject a long form beginning with a function word     -- experiment ten, reverted
  reject a long form over or under a length threshold
  reject a long form whose head word is not a noun
  reject a long form failing a stopword-density or readability filter
  reject a long form the pseudo-precision estimator rates poorly
    -- and D-012 separately establishes that estimator rates rules, not spans
  any confidence threshold applied to the long form alone
```

Each will look free on a pair-scored corpus and cost short-form recall on a label-scored one. **The
D-032 result is the general case already measured: a variant does not need re-measuring to be
refused, it needs a different shape.**

The escape D-008 already closed is worth restating so it is not re-attempted as a fix. The correct
span for `OHCHR` starts to the *left* of `of`, so recovering the deleted pairs means moving the
long-form starting boundary — which is boundary-maximising selection, built, measured and reverted in
D-008.

### The design question this surfaces, posed and deliberately not answered

The constraint only binds because the pair is atomic. So:

**Should `extract()` be able to emit a short form with an absent, or low-confidence, long form?**

That is a public API question and it is bigger than any of the rules above. The evidence that it is
worth asking is that the corpora this project scores against already disagree with the library's
output shape:

```
bench/results.json -- gold spans per label, three corpora, re-derived for this record
  PLOD-CW all             short forms 2,869      long forms 1,804
                          and only 46.11 % of gold short forms stand in a
                          parenthetical arrangement at all
                          -- shortform.plod_all.corpus
  SDU-22 legal dev        short forms 1,213      long forms   669
  SDU-22 scientific dev   short forms   970      long forms   720
                          -- tp + fn per label, shortform.sdu22_ae_*.high_precision.legend
```

In every case the annotators marked more abbreviations than definitions, because most abbreviations
in running text are never defined there. A library that can only report a *pair* cannot report those
at all: the shipped extractor is architecturally unable to say "this is an acronym and I do not know
what it stands for", which on the evidence above is the majority case in at least one held-out
corpus.

**What answering it would cost, so the question is honest rather than rhetorical.** `AcronymPair`
would need a long form that can be absent or low-confidence, which is a wire-contract change and
therefore R8 territory — a design, not a patch. Every consumer of `extract()` would see candidates it
has never seen. Precision on the short-form label would become the dominant risk, and this project
has one uncontaminated span corpus and no uncontaminated extraction corpus with which to measure it.
And D-042's fork bears on whether it is worth doing at all, since the caller who benefits is the one
scoring against a span corpus.

Not answered here. Recorded so the next person who proposes a long-form precision filter finds both
the refusal and the question that is actually underneath it.

### How it fails

**The eleven deletions are on two contaminated tuning splits.** Both SDU-22 dev splits had their miss
taxonomy read by the August 2026 audit, which is what `bench/splits.toml` records as having
contaminated them. The ratio is arithmetic rather than fitted — a deletion either carried a correct
short form or it did not — but it is eleven events, and eleven events on contaminated splits is a
thin base for a constraint stated this broadly.

**Three of the eleven long forms were themselves scored correct**, and D-032 records that three more
look like annotation artefacts. The revert survives discounting the artefacts entirely, and so does
this constraint, because the short-form spans are what the constraint is about. Somebody arguing the
other way would need the *short* forms to be artefacts, and `and Pacific -> APC` and
`an adverb -> AA` are the two cases where the long form was scored correct and the deletion was pure
loss on both labels.

**"Closed in advance" is a claim about rules nobody has written.** A long-form filter that also
re-emitted the short form unpaired would sit outside this constraint entirely — which is the design
question above, and is why it is posed rather than dismissed.

**The corpus asymmetry argues for the question, not for an answer.** More gold short forms than long
forms is partly an annotation convention: PLOD tags abbreviation tokens wherever they occur, not only
where they are defined. That is a real difference in what the corpus is for, and reading it directly
as "the library is missing two thirds of the work" would be the same error as reading MED1250's zero
collateral as "the rule is free".

---

## D-040 — Four sdist fixes, and the job that was meant to catch them was importing `src/`

**Status:** shipped (CI only) · **Evidence:** `.github/workflows/ci.yml` job `installed-suite`,
`tests/conftest.py`, the renamed sdist step in `build`

The distribution has broken four times on one shape: it shipped an assertion without the file that
backs it — `bench/results.json`, then `data/LICENSES.md`, then `tests/fixtures/*.json`, then a test
that executed a `bench/` script while being imported. Each fix named the file that had just broken. A
fifth guard of the same kind was proposed. What was found instead is that the check those guards were
meant to complement has never run against a distribution.

### The finding

`build`'s "Verify the sdist can run its own test suite" step extracts the sdist, installs it, and
runs pytest **inside the extracted tree**. `tests/conftest.py` opens with `SRC = REPO_ROOT / "src"`
and inserts it at the front of `sys.path`. The extracted tree has a `src/`. So the install on the
previous line is never imported.

```
un-gated, workstream measurement -- the real conftest, run inside a built and
extracted sdist, against a venv holding that sdist installed
  python -c "import sys; sys.path.insert(0,'.'); import conftest, acronymkit; print(acronymkit.__file__)"
  ->  <extracted-sdist>/src/acronymkit/__init__.py
```

D-018's closing rule is this one level up: a lookup with a fallback cannot be used to test the thing
it falls back to. Here the fallback is `sys.path` and the thing it falls back to is the installed
package.

### The job

`installed-suite` builds an sdist, installs it into a clean venv, and runs the artefact's own
`tests/` from a directory holding no `src/`, no `bench/` and no `tools/` — after **asserting
`acronymkit.__file__` resolves under `sysconfig.get_paths()["purelib"]`**. That assertion is the
load-bearing step: without it the job degrades silently into the state the old one has been in all
along.

Eight test ids cannot run from an installed package and are pinned **as an exact set, compared in
both directions** — a listed test that starts passing reds the build and must be deleted from the
list, so the list cannot rot into a blanket exemption. Two files execute a `tools/` script at import
and therefore fail to *collect* rather than skipping, taking 120 tests with them, because `skipif` is
consulted at collection and the module body at import; two `test_package.py` tests parse the source
of `__init__.py`; four `test_serialization.py` tests assert on `SCHEMA_PATH`, which D-018 established
names the checkout copy by construction.

### What it proves that nothing else did

```
un-gated, workstream measurement, 2026-08-24 -- delete
acronymkit/resources/pseudo_precision_en.json from an installed distribution.
It is read at run time and it is NOT in build's hand-written `required = [...]`:
  the `required = [...]` wheel-resource guard   no missing entries       PASSES
  the extracted-tree sdist run                  no new failures          PASSES
  installed-suite                               11 unexpected failures   FAILS
```

The hand-written list is therefore already incomplete and already passes on a distribution that is
already broken. Appending that filename would have been the fifth symptom fix.

**Both jobs stay, and the old one was renamed to what it verifies** — "Verify the sdist ships the
files its own test suite reads". That is real, and it is the only place `bench/results.json`,
`data/LICENSES.md` and `tools/` reachability are exercised, which is two of the four historical
incidents.

### How it fails

The green tick does not mean "the suite passes from an installed package"; it means "the non-passing
set is exactly these eight", and only a comment says so. `EXPECTED_NON_PASSING` is still a list of
names, defended by being exact and self-cleaning rather than by not being a list — a reviewer under
time pressure can turn a red run green by adding one line. `PASS_FLOOR` is a hard-coded number in the
file whose wheel-budget comment is a monument to hard-coded numbers going stale. The gate parses
pytest's width-truncated short-summary lines and is pinned to a fixed `COLUMNS`. `pyproject.toml`
travels with the tests — withholding it costs 28 failures, 26 of them lost `asyncio_mode` — which
lets one test read a file an installed user does not have. The job rebuilds its own sdist rather than
downloading `build`'s artefact, so it tests the same commit and not the same bytes. And the whole
thing was verified on Windows with `Scripts/python.exe` substituted for `bin/python`; the POSIX venv
layout, `$RUNNER_TEMP` and GitHub's `bash -e` wrapper are unexecuted.

**It is coupled to whatever else is in flight.** `tests/test_splits_manifest.py` is one of the two
files pinned as a collection failure. If a future workstream guards its module-level load, the
stale-entry branch fires and their commit goes red on this job with a message about a file they did
not think they had touched. That is the ratchet working, and it will not look like it.

**Eight tests should stop being exceptions.** The right fix for all of them is the `skipif` their
neighbours already carry, after which the matching lines must be deleted from
`EXPECTED_NON_PASSING`. That is a `tests/` change and it was out of scope for the workstream that
found this. The hand-written `required = [...]` list should then be *deleted* rather than extended,
in its own commit, since this job subsumes it.

---

## D-039 — A definition no bracket introduces. Shipped, and shipped switched off.

**Status:** shipped, default off · **no experiment number spent — experiment eleven is still free** ·
**Evidence:** `bench/run_shortform.py --variants --spans --legend`, `shortform.*.legend` and
`shortform.*.legend_exposure` in `bench/results.json`, `src/acronymkit/extractor.py`,
`tests/test_extractor.py`

`GEF = Global Environment Facility` is a definition, and every version of this library has walked
past it, because the whole extractor is a scan over balanced bracket regions. On the newest corpus
this project reads it is the largest single miss class, near-equal across both splits — a
corpus-convention gap rather than evidence about a domain. `AbbreviationExtractor(config,
legend_syntax=True)` now reads it. The default is `False`.

### The revert criterion was absolute, and it was not triggered

`X = Y` is also the surface of every equation and assignment. The criterion was: if MED1250 precision
moves at all, revert and log it as experiment eleven. It does not move by any amount, on any split,
under any profile.

```
bench/results.json, shortform.med1250_all.*.{balanced_trim,legend}
MED1250 exact, `all` -- TUNING SPLIT
  profile          balanced_trim (ships)      legend
  high_precision   P 92.46   F1 84.21         P 92.46   F1 84.21
  general          P 92.39   F1 84.33         P 92.39   F1 84.33
  biomedical       P 86.43   F1 83.28         P 86.43   F1 83.28
  Identical on dev and test, and on every recorded field including tp/fp/fn.
  Verified for this record: the ONLY fields that differ between the two saved
  entries are `variant`, `comparator` and `legend_syntax`.
```

The comparator on the legend row is **`balanced_trim`, not `baseline`** — `balanced_trim` is what
ships, and a shipping decision has to be one change away from what ships. Reading it against
`baseline` would bundle it with a fix that landed a session ago, which is the error R6 exists to
prevent.

**That table alone says almost nothing, and the more useful half of this entry is why.** R9's fifth
question again:

```
bench/results.json, shortform.med1250_all.legend_exposure
  separators in the corpus                                     401
  gold long forms beginning after a separator              0 of 1,221
  reaching a window under high_precision                        48
```

The corpus cannot show the upside even in principle; it can only show harm, and under the shipped
profile most separators are never approached, so "no change" is mostly "nothing happened". The
load-bearing row is `legend_exposure_biomedical`, where the loosest admission gate the library ships
— one character, no uppercase required — lets **396 of 401** separators through to a window and the
alignment refuses **every one**, emitting zero pairs. `n = 523`, `P = 0.05`, `r = 0.78`,
`Ki = 1 microM`. A `=` in an abstract introduces a number, and a number does not align with the
letters of an abbreviation. That is a gate tested under load rather than a gate never approached.

### The gate is not the matcher the audit named, and the reason matters

The audit said to gate the long form on "the existing character-alignment test". Read as
`find_best_long_form`, that loses the dominant class: it scans right-to-left from the end of its
window and returns a *suffix*, so on `AOS` over `administrative and operational services` it takes
the `A` from `and` and answers `and operational services`. That is correct for a bracketed
arrangement, where the long form ends at the bracket and only its left edge is in dispute. A legend
is the mirror image — the expansion begins at the separator and only its right edge is in dispute —
so the alignment must be anchored at the first word. The shipped gate is `_initial_match_fraction`
plus a check that the first character landed on word zero: an existing function, no new alignment
logic in the module, and a different function from the one the sentence named.

The cost is a deliberate miss class. `INT -> interrupted`, `TRUN -> truncated` and
`TRANS -> transposed` are gold legends in the scientific split and are refused, because a truncation
of one word starts one word. Loosening to the inside-a-word alignment is exactly the reading under
which `Tsat=Tamb` and `wC = carbon mass fraction` become definitions. A test pins the miss so it
stays a decision rather than a surprise.

### What it buys, decomposed, never pooled

**Read the provenance before the numbers.** `bench/splits.toml` records that the August 2026 audit
decomposed *these two dev splits' misses by legend separator* and used the result to rank *this*
proposal. They are the two corpora whose miss taxonomy selected the idea, and both are declared
tuning and contaminated.

| SDU-22 dev (**tuning, contaminated**) | label | balanced_trim | legend | SF recall ceiling |
|---|---|---:|---:|---:|
| legal | SF exact F1 | 53.82<!--claim:shortform.sdu22_ae_legal_dev.high_precision.balanced_trim.short_form.exact_f1:.2f--> | **60.50<!--claim:shortform.sdu22_ae_legal_dev.high_precision.legend.short_form.exact_f1:.2f-->** | 55.15<!--claim:shortform.sdu22_ae_legal_dev.corpus.ceiling_pct:.2f--> %, recall 37.76<!--claim:shortform.sdu22_ae_legal_dev.high_precision.balanced_trim.short_form.exact_recall:.2f--> -> 44.52<!--claim:shortform.sdu22_ae_legal_dev.high_precision.legend.short_form.exact_recall:.2f--> |
| legal | LF exact F1 | 70.00<!--claim:shortform.sdu22_ae_legal_dev.high_precision.balanced_trim.long_form.exact_f1:.2f--> | **78.20<!--claim:shortform.sdu22_ae_legal_dev.high_precision.legend.long_form.exact_f1:.2f-->** | |
| scientific | SF exact F1 | 72.15<!--claim:shortform.sdu22_ae_scientific_dev.high_precision.balanced_trim.short_form.exact_f1:.2f--> | **74.91<!--claim:shortform.sdu22_ae_scientific_dev.high_precision.legend.short_form.exact_f1:.2f-->** | 74.23<!--claim:shortform.sdu22_ae_scientific_dev.corpus.ceiling_pct:.2f--> %, recall 57.84<!--claim:shortform.sdu22_ae_scientific_dev.high_precision.balanced_trim.short_form.exact_recall:.2f--> -> 61.55<!--claim:shortform.sdu22_ae_scientific_dev.high_precision.legend.short_form.exact_recall:.2f--> |
| scientific | LF exact F1 | 75.10<!--claim:shortform.sdu22_ae_scientific_dev.high_precision.balanced_trim.long_form.exact_f1:.2f--> | **77.83<!--claim:shortform.sdu22_ae_scientific_dev.high_precision.legend.long_form.exact_f1:.2f-->** | |

Both recalls stay under their ceilings, which `bench/corpora.py` re-derives live and the runner
prints in the same table. Neither ceiling is a bound: every point above it is bought by emitting a
definition the corpus does not annotate, paid for in long-form precision.

**The losing rows, beside the headline as R5 requires.**

```
bench/results.json, .balanced_trim -> .legend, high_precision
  SDU-22 scientific dev   SF exact precision      95.90 -> 95.67
                          SF overlap precision    97.78 -> 97.44
                          LF overlap precision    97.26 -> 96.96
  PLOD all / tight        SF exact precision      93.66 -> 93.63
                          LF overlap precision    90.17 -> 90.10
  worst move anywhere     0.34 points.   No F1 falls anywhere.

  Note the shape: PLOD POOLED precision falls while PLOD dev and test precision
  RISE. The pooled split includes `train`, which contributes the only new false
  positives. On the two frozen halves the rule adds true positives on both
  labels and no false positive at all.
```

**Amended by D-045.** That block is scoped to `high_precision` by its own header and is correct there.
`--spans` runs only that profile and three profiles ship: over all three the worst move is `-2.18`,
and "worst move anywhere" is the phrase that needs reading narrowly. The number is right.

**PLOD-CW — the one held-out corpus, improves everywhere, and is nearly blind.**

```
bench/results.json, shortform.plod_all.legend_exposure
  gold long forms beginning after a separator      16 of 1,804    0.89 %
  predictions emitted across the whole corpus      12, in 8 of 1,351 documents
```

Every F1 rises on both labels, both detokenisations, all three splits. And it is twelve predictions.
This is D-032's PLOD problem arriving through the other door: the corpus is structurally almost
incapable of scoring the class, so its agreement on every field is worth much less than the fact that
it agrees.

### Why the default is off, given all of that

The first reason decides it. **There is no uncontaminated, structurally capable corpus in this
repository.** The two that show the gain are contaminated for precisely this change; the independent
arms have 0.00<!--claim:shortform.med1250_all.legend_exposure.gold_long_form_spans_after_a_separator_pct:.2f--> % and 0.89<!--claim:shortform.plod_all.legend_exposure.gold_long_form_spans_after_a_separator_pct:.2f--> % capability. Shipping on by default would set a default on the split that
selected the idea. Beyond that: it widens what `extract()` means for every existing caller and emits
a third `pattern` value no consumer has seen; `X = Y` is also the surface of source code,
configuration, spreadsheet formulae and query strings, none of which were measured; the gain is 83,
39 and 12 predictions on three corpora; off keeps every downstream run valid, where flipping the
default would stale `admission.*`, `analysis.*`, `oracle.*`, `cascade.*`, `rerank.*`, `termfreq.*`,
`spans.*` and `extraction.*` at once; and off is cheap to reverse while on is not.

`tests/test_extractor.py::test_the_flag_only_ever_adds_pairs` is what makes the flag safe to reason
about: over every corpus document, strip the legend pairs out and what remains equals the shipped
default's output pair for pair and span for span. **The flag adds candidates and re-ranks none**,
which is the region where D-012's pseudo-precision diagnosis does not bite.

### One correction made during review, recorded because the class recurs

A comment claimed the operator guard removes `= -0.62`. It does not — the guard tests only the two
*immediately* adjacent characters, and there the minus is one space away. The surface is refused, by
the alignment two steps later. The comment was fixed rather than the guard widened: widening it to
"an operator appears somewhere nearby" would have been changing code to protect a sentence. A comment
describing a gate it does not implement is the same failure as a headline describing a corpus it was
not measured on, at a smaller scale.

### Precondition for flipping the default, and the collision it runs into

A corpus that annotates legend definitions, has not been mined, and can be declared uncontaminated.
SDU-22 `train.json` — 3,564 unread legal samples — is the obvious candidate, is declared
`role = "tuning"` for the whole corpus so it buys within-corpus corroboration rather than
generalisation, **and is the same split D-032 reserved as the precondition for reopening experiment
nine.** One unread split, two questions. D-043 records what the alternative instruments would cost
and why AD `test.json` is not one of them.

**Resolved by D-047:** the split is allocated to this question, experiment nine is the loser and the
run that spends it must save the `two_word` row anyway. D-047 also records what spending it cannot
buy — it is a tuning arm, so it does not answer the sentence above about an *uncontaminated* corpus,
and legal dev carries zero separators opening a number, so it says nothing about the equation risk.

### How it fails, beyond the above

`AcronymPair.pattern`'s field description in `src/acronymkit/models.py` still names only the two
bracketed arrangements, and an opted-in caller now sees a third value; no enum exists in
`schemas/acronym-engine-result.schema.json`, so nothing validates against it and the default output
never carries it, but the description is incomplete. `bench/splits.toml` defines PLOD's short-form
recall ceiling as the share of gold short forms in one of the **two parenthetical arrangements**, and
this variant emits from a third — nothing is currently mis-stated, and the basis text should be
widened before anyone quotes it beside a legend figure. `_legend_long_form` takes the shortest prefix
that spends every short-form character, so a longer expansion whose trailing words carry no
short-form letter is truncated; `SD -> Stanford De` in the scientific dump is that failure visible.
Fullwidth `＝` is not read at all. There is no `Config` field: the flag is reachable only by injecting
an extractor, which is a deliberate scope boundary rather than a design. And every corpus measured is
academic or institutional prose, so the statistical-prose load test is one genre, not "arbitrary
text".

---

## D-038 — The data pack group was a public name with no referent, and the honest fix was the cheap one

**Status:** shipped; closes audit recommendation 7C · **Evidence:** `src/acronymkit/diagnostics.py`,
`tests/test_diagnostics.py`, `docs/AUDIT-2026-08.md` section 7C

`acronymkit.data` was declared as an entry-point group, exported as `DATA_PACK_GROUP`, discovered by
`capabilities()` under a `data_packs` key, printed by `doctor` as `data packs : none` — and consumed
by nothing. The audit proposed finishing it and, to its credit, wrote its own kill criterion: the
load-bearing assumption is that somebody would publish a pack, and the honest test is whether this
project would ship one within a release or two. It would not. The declaration is deleted.

### The argument it rests on, and the one it does not

D-029 measured the population that might publish a pack and found it empty. That is the reason not to
*build* the loader. It is deliberately **not** the reason the declaration goes: D-029 says of itself
that its numbers decay fast and that anything citing it against compatibility must re-run the checks
first, and those checks were not re-run for this record.

The argument that needs no census: **with no loader anywhere in the library, `data_packs` could only
ever be `[]` — for a user who exists exactly as much as for one who does not.** It was a report field
that never varied, a `doctor` line describing a mechanism no code could act on, and a public name
with no referent. A single downstream adopter inverts D-029; none of them makes the key non-empty.

### The same shape D-035 reverted, one commit earlier, in the same package

D-035 shipped injectable collaborators because the documentation described a plug-in rule the code
did not implement, and specified the new seam as "no registry, no entry-point group, no discovery,
nothing reachable at import time". The one entry-point group that already existed was left standing.
This closes it.

### What was checked before deleting, because "no consumer" is a claim

```
un-gated -- grep over src/ tests/ tools/ bench/ docs/ and every .md/.toml/.json/.jsonl/.yml
  DATA_PACK_GROUP | data_packs | acronymkit\.data
    src/acronymkit/diagnostics.py   3 lines    tests/test_diagnostics.py   4 lines
    docs/AUDIT-2026-08.md           the proposal itself
  loader, golden fixture, schema, pyproject entry-point table          none
  top-level re-export in __init__.py's _EXPORT_SOURCES                 not present
  docs/GOVERNED_NAMING.md, docs/ENTERPRISE.md, docs/OFFLINE.md         advertise
    no pack in any wording; their `jq` examples select .network, .tiers
    and .resources.digests, never .data_packs
```

Verified for this record: `capabilities()` no longer reports `data_packs`, and
`acronymkit.diagnostics` exposes no `DATA_PACK_GROUP`.

### R10: the scan was never on the import path, and the deletion did not make it faster

Reported as a non-result on purpose. The scan was already lazy, so removing it could not move import
cost, and saying otherwise would sell a deletion as a speedup.

```
un-gated, workstream measurement -- 11 subprocess runs each, PYTHONPATH=src
  import acronymkit    before min 1.998 ms    after min 1.927 ms    gate 30 ms
un-gated -- spy on importlib.metadata.entry_points installed before any acronymkit import
  import acronymkit / .cli / .governed, Config(), AcronymEngine(), GovernedNamer()
                       before  []               after  []
  capabilities()       before  ['pydantic','acronymkit.data']   after  ['pydantic']
```

Two call sites remain for the surviving `pydantic` scan — `capabilities()` and
`config._enforce_offline`, the latter only when a caller asks for strict offline mode. Neither is on
an import path. A first draft of the source comment said "capabilities and nowhere else"; a grep
found the second caller and the sentence was corrected rather than kept.

### The wire consequence, stated rather than absorbed

`capabilities()` loses the top-level key `data_packs`; `acronymkit doctor --format json` loses
`.data_packs`; the text report loses one line; `acronymkit.diagnostics.DATA_PACK_GROUP` no longer
exists and is out of `__all__`. `acronymkit.__all__` is unchanged — the constant was never a
top-level export. The function's `Returns:` promised only that an existing key would not *change
meaning* under a patch release; it now also says a key may be removed, that removal is a
minor-release event, and names this one, so a CI asserting on it finds the reason beside the report.
**The CHANGELOG flags it as breaking for anyone who asserts on the report's key set**, because "the
value was always `[]`" is a reason the break is cheap, not a reason it is not a break.

### Why a deletion needed three tests

The file's shape assertions are supersets by design, because the documented contract permits
additions — so re-adding `data_packs` would have passed every existing check.
`test_capabilities_does_not_report_a_withdrawn_key` makes revival a failure;
`test_capabilities_scans_exactly_one_entry_point_group` asserts the enumerated groups are exactly
`["pydantic"]`, which also catches scanning it twice; `test_format_report_has_no_data_pack_line`
keeps the rendered report free of the advertisement.

### How it fails

**The capability is genuinely gone.** A pack published tomorrow is invisible to `capabilities()`. The
discovery half survives as `_entry_point_names(group)` and re-declaring is three lines; the comment
beside `_PYDANTIC_PLUGIN_GROUP` argues against writing them before a pack exists to load, and is
written to be found by someone reading the audit's recommendation without its kill criterion.

**Absence of evidence, again.** A vendored or air-gapped deployment asserting on the report leaves no
public trace and would break. The defence is that the key is `[]` there too, not that no such
deployment exists.

**`WITHDRAWN_TOP_LEVEL_KEYS` is a convention, not a mechanism** — nothing forces the next removal into
it. **`test_format_report_has_no_data_pack_line` asserts on the substring "pack"** across the whole
report and would fire on an unrelated future resource whose name contains it; that false-positive
shape was taken deliberately, because the true positive it guards is a re-added line. And **the
docstring calls this a minor-release event without naming a version**: if it ships in a 0.3.x patch,
the change violates the rule it wrote.

**An adjacent finding, reported and not fixed.** The bundled-resource tables in `docs/OFFLINE.md` §7
and `docs/SUPPORT_MATRIX.md` list seven files; `bundled_resources()` and `doctor` both report eight.
`pseudo_precision_en.json` is missing from both, and `OFFLINE.md` invites an enterprise reviewer to
compare their installation against its table directly. `tools/check_claims.py` cannot catch it
because "seven" is a word, not a claim-shaped number. The missing row is the fitted, shipped
precision table, so it owes a licence and provenance column — which is exactly what that table
carries.

---

## D-037 — The abstention curve now ships with the column that reverses its meaning, and the README leads with the half that has an integration story

**Status:** accepted; documentation only, no behaviour changed · **Amends:** D-030 ·
**Evidence:** `disambiguation.sdu21.abstention_curve`, `disambiguation.sdu21.diagnosis.default_path`,
`disambiguation.sdu21.ceiling` in `bench/results.json`; `docs/EVALUATION.md`, `README.md`,
`src/acronymkit/disambiguation.py`, `src/acronymkit/engine.py`

D-030 measured the abstention finding and recorded it. It reached no document a user reads.
`docs/EVALUATION.md` now carries it as three decomposed tables, each with the shared task's own
most-frequent-expansion baseline scored **on the same answered subset**, in a column of the same
table rather than a paragraph underneath it. That is R5 in the strict sense. D-044 states what the
curve means for the definition of done; this record is about the publication.

The three tables are the pooled coverage/accuracy/recall/F1 curve with the baseline column and every
losing row marked; a per-candidate-set-size table at the reference gate, with the worst answered
accuracy printed rather than left derivable; and a gold-evidence table showing the gate is
substantially a verbatim-evidence detector — the gold-verbatim share of answered instances rises from
roughly a sixth to nearly nine tenths across the range, while in the gold-absent subset the baseline
is thirty to forty points ahead both before and after gating and coverage collapses. The recall
ceiling is printed in the same section per R9.6: gold is among the candidates on 6,189 of 6,189, so
nothing in these tables is capped by retrieval. A provenance block states that the split is tuning
and contaminated, that the reference gate is read off the split it is scored on, and — closing
D-030's re-quote hazard — which run id to cite and which not to.

`disambiguate` is now labelled in all four places a reader can land: the README section, a README
honest-scope bullet, `docs/EVALUATION.md`, and the module and method docstrings. The documented
default path returns no candidate on the overwhelming majority of the measured split and has two
candidates to choose between on one instance in 6,189 — it performs no selection at all. D-029
established there are no external users, so the first reader who ever arrives hits exactly that path.

### The framing change nobody had made

The README led with generation. The governed subsystem is a little over a third of the source, close
to half the public symbols, seven of the sixteen CLI commands, and the only half with a streaming
batch mode another runtime can drive. It now leads — lede, hero example, first `###` under "What it
does", first subsection of "Command line". D-028 argued against *splitting* the package; it says
nothing against ordering it, and the August 2026 audit recommended the inversion explicitly as free
and reversible.

### Three published sentences this record retires

* README: "no accuracy figure is attached to it anywhere in this project" — D-031 attached one.
* EVALUATION: "Extraction only. Generation, backronym alignment and disambiguation have no external
  evaluation at all" — contradicted three sections above it in the same file.
* EVALUATION: "Neither corpus is registered in `bench/splits.toml` yet", plus its two named blockers —
  both blockers were removed and both corpora registered during the same session, by D-036.

All three were value-preserving statements that had quietly become false. **The mechanism is the one
that produced the stale headroom figure the ratchet exists to prevent: a true sentence, published,
and never re-read against a repository that had moved underneath it.** `tools/check_claims.py`
catches a stale *number*. Nothing catches a stale *sentence*, and these three were caught by hand.

One stale figure went with them: the governed half was published as 9,370 of 25,210 source lines and
re-derives to 9,647 of 26,149. The re-derived counts ship with the command that produces them, and
the README carries word-form fractions instead of digits.

Rather than assert the newly-registered state, which was uncommitted and could still move, the
EVALUATION paragraph was rewritten around the immutable fact: every governed run in
`bench/results.json` records `splits_declaration = UNDECLARED` and none has been re-measured.
**Measured-before-declared, not held-out** — and a declaration written after the fact does not make a
number blind. That objection is written into the doc; D-036 is where it is adjudicated.

### How it fails

Docstring citations name run ids and fields but quote no values, because `check_claims` renders a
`.py` citation as a literal a caller would see in `help()`. That keeps the digits in the Markdown
where they are checked and leaves the pointers in `src/` unchecked: rename a field and nothing fails.
The README's structural counts have the same property in the other direction — word-form fractions
stay out of the ratchet's reach and out of its protection, and nothing will ever say they went stale.
The bolding convention in the tables is a sentence about the author's own formatting that no tool
checks; edit a cell and it silently goes wrong. The anchor from README into the new EVALUATION
heading is a hand-built GitHub slug that dies silently if the heading is renamed. And the prose
asserts a monotonicity that holds pooled and not inside every bucket: answered accuracy turns down
between two gates inside the 4-way bucket and peaks early inside the gold-absent subset. That
qualification is published; a reader skimming the headline paragraph will still take away a monotone
story.

### Not closed by this record

No claim was migrated off the value-matched path, so no baseline was lowered: `README.md` carries 5
and `docs/EVALUATION.md` 24, unchanged, and both are trivially migratable. R1 forbids freeing a slot
without closing it in the same commit, and `tools/check_claims.py` belonged to no workstream this
round. `disambiguation.sdu21.diagnosis.abstention` is still live and is a re-quote hazard — it gates
on the raw margin where the shipped gate exempts different-source pairs, so its rows differ from the
shipped curve; retiring it is a `bench/results.json` change. `AcronymEngine.disambiguate` still has
no gate at all, and D-030 names the clean fix. And `ExpansionDictionary`'s class docstring still
calls insertion order "weak evidence" while the scorer ignores it entirely — either implement it or
delete the sentence.

---

## D-036 — `identifier_segmentation` is a task, and `headline_capable` now has to be told what the headline is about

**Status:** shipped · **Amends:** D-031 · **Evidence:** `tools/splits.py`, `bench/corpora.py`,
`bench/splits.toml`, `tests/test_splits_manifest.py`

D-031 published the governed subsystem's first accuracy figures behind run-id citations throughout,
off two corpora that were not in `bench/splits.toml`. Every saved figure carried
`splits_declaration: "UNDECLARED"`, which is exemption from R2 *by omission* — the failure the
manifest exists to prevent, produced by the workstream that satisfied the goal. Registration was
blocked on `TASKS`, and `TASKS` is a closed vocabulary for a reason that makes widening it a
decision.

### What the closed vocabulary was protecting, and why a fourth string is not the change

`bench/corpora.py` returns a **different type per task**. That sentence had been in two docstrings
for months and was checked by nothing: a corpus declared `disambiguation` could have been registered
in the span readers with no complaint from anywhere. The vocabulary was closed against a hazard it
could not detect.

`TASK_GOLD_UNIT` now states, beside the tuple, what one gold record IS per task. The first three all
annotate *inside a passage*. The fourth does not:

| task | one record is |
|---|---|
| `extraction` | a passage plus the pairs a human annotated in it |
| `span_detection` | a passage plus index ranges, never paired |
| `disambiguation` | one occurrence plus its fixed candidate set |
| `identifier_segmentation` | two surface strings of the *same characters*, gold = cut positions |

An identifier/caption record has no text, no span, no candidate set and **no annotator**: the caption
is production metadata written by whoever wrote the identifier. That is why this gold survives the
question that killed NameGuess in the audit's section 0 — there is nobody to have instructed.

The type separation is stronger than the ones already here. `read_plod_cw_text` documents a *soft*
trap: it returns a real document with no pairs, so a pair runner reports a meaningless zero and only
the gold-pair count gives it away. `SegmentationCorpus` is not a list and its records have no text
and no tokens, so a pair or span consumer dies rather than producing a number. A crash is a better
failure than a plausible figure.

**The gold construction is not duplicated.** The admission rule and the cut metric stay in the
runner; the reader returns raw rows and says so in its docstring. Two implementations of an admission
rule are two definitions of a gold standard. A reader that re-applied the rule so it could return the
*scored* population was designed and then not built, for exactly that reason.

`read_governed_gold` also **refuses to choose between two cached snapshots**. Two Socrata caches are
two populations of a live catalog, not two files; picking the newest would put the choice of which
corpus was measured inside a number. Both are on this disk, so it is a designed failure rather than a
hypothetical, and it is tested.

### The quieter hole, which was already costing something

`headline_capable()` was task-blind. It now takes the task the headline is a claim about,
**required** — a permissive default leaves the hole open under a shorter call, and the caller who
most needs the question asked is the one who would omit the argument.

```
un-gated mechanism probe, real manifest, after registration -- re-run for this record
  task-blind (the old function)               ['plod','sdu21_ai','sec_xbrl','socrata']
  headline_capable('extraction')              []
  headline_capable('span_detection')          ['plod','sdu21_ai']
  headline_capable('disambiguation')          []
  headline_capable('identifier_segmentation') ['sec_xbrl','socrata']
  headline_capable()  ->  TypeError, missing 1 required positional argument: 'task'
```

With the corpora registered, the old function would have handed `sec_xbrl` and `socrata` to a caller
asking whether it may publish an *extraction* headline, and nothing would have failed.

**The pooled advisory was not a future risk; it was suppressing two true statements today.** The
single "no uncontaminated held-out corpus" note went quiet as soon as `plod` and `sdu21_ai` qualified
for span detection, and this project still has no held-out corpus for extraction and none for
disambiguation. `python tools/splits.py --check` now prints both gaps — confirmed for this record —
and the registration provably does not silence them. The comment block at the head of
`bench/splits.toml` claiming no number in this project satisfies the headline rule had gone false the
same way and is corrected.

`validate()` also refuses a short-form recall ceiling on a task whose gold holds no short forms. A
segmentation corpus annotates no abbreviation anywhere; a ceiling there is not a cautious extra, it
is a number that would be printed beside a recall figure measuring something else. `as_dict()`
reports `headline_capable` per task and offers no pooled list, because the pooled list was the hole.

### The binding check found something on its first run

`TASK_REGISTRIES` maps each task to the registries that may hold it, and a test walks every registry
key through the manifest. It failed immediately: `plod_cw_test` is in the pair-document registry
while `plod` is declared `span_detection`. That is deliberate — `bench/external.py` needs
text-bearing documents for an out-of-process baseline — and it had been warned about in prose since
it was written. Prose is not consultable. The exception is now `TEXT_ONLY_VIEWS`, built in the same
loop that registers the keys, with its own test asserting the exemption still describes something
true. `span_detection` maps to two registries and that is modelled as a set rather than tidied into a
bijection nobody could honestly claim: one carries token indices, the other character offsets, and
indexing one with the other's numbers is why they are separate types.

### Licences, re-read from the terms rather than transcribed, 2026-08-24

**SEC.** `sec.gov/privacy`, "Website Dissemination": information on sec.gov is public and may be
copied or further distributed without permission. The same paragraph withholds the seal, the logos
and the EDGAR trademarks, so the grant is not unconditional and reading only the first sentence would
say it was. The label caveat was read out of the 2025q1 archive itself, through the range-request
path the runner uses: `tlabel` is the label text provided by the taxonomy, or the text provided by
the filer, and §5.2 sources standard tags to FASB and the IFRS Foundation. The SEC cannot license
text it does not own. `readme.htm` contains **zero** occurrences of "copyright", "license" or
"licence" — the audit's EDGAR row is right about the archive and wrong about sec.gov.

**Socrata.** `dev.socrata.com/docs/other/discovery`: zero occurrences of "copyright", and exactly one
licence string on the page, in the footer, covering the documentation. **The trap is sharper than the
parked draft said:** the page's substance is rendered client-side, so the static HTML a fetcher
receives is navigation and footer and almost nothing else. The only licence-shaped string a machine
sees on that page is the one that is wrong about the data. That is the fourth entry in this manifest
with that property, after both SDU-21 repositories and SDU-22 AE. R4 is not a formality.

### `contaminated = false`, and the trip-wire that flips it

D-031 published a full miss decomposition, four worked failures and a named candidate fix, and the
manifest's own words are that reading a miss taxonomy is exactly what made MED1250 a tuning split.
The declaration nearly went the other way. What decided it was reading all three existing
contamination reasons literally: each records the misses being read **and** the corpus being used to
choose — MED1250 had a boundary-selection experiment run and reverted against it, `sdu21_ad` an
ablation, a ceiling study and an abstention sweep, `sdu22_ae` a recall proposal ranked on its result.
Only the first conjunct holds here: the runner has no thresholds, no configuration and no arms, and
no D-record selected a tokenizer change on this evidence.

The trip-wire is written into the manifest in advance. The first time anyone changes the identifier
splitter on the strength of the published false-positive taxonomy, both corpora become contaminated,
the validator forces `role = "tuning"`, and **`bench/run_governed_gold.py` hard-fails on that role
rather than labelling its output** — so the runner stops working until that refusal becomes a label.
That consequence lives in a file nobody editing the manifest will have open, which is why it is
written where the declaration is.

**This is the load-bearing judgement of the record and it is the one to attack.** Someone applying
the file's stated definition — looked at closely enough that it can no longer adjudicate anything
blind — reaches `contaminated = true`, and they have a case, because the false-positive taxonomy is a
standing gated field, so the failure modes are not merely known but published. If that view wins, the
validator forces `tuning` and the runner refuses to run.

### One correction to D-031's own entry text

The drafted entry said "every admitted identifier is CamelCase". Checked against the gated shape
counts rather than transcribed: true of us_gaap and ifrs, false of `filer_extension`, which carries
snake, dotted and flat-upper shapes alongside tens of thousands of camel ones. The claim worth
keeping survives — `snake_upper` is a bucket the shape function really emits and it is **zero on
every arm of both corpora**, so there is no UPPER_SNAKE identifier in this gold at all, which is the
shape this package's own fixtures are written in. A counted zero is a stronger caveat than a hedge;
an over-stated "every" is weaker than both, because the first person to find the counterexamples
stops believing the rest.

### How it fails

`held_out` here does not mean frozen, and the word invites the wrong reading: nothing was withheld,
the whole admitted population was scored in one pass and its anatomy published, and Socrata's catalog
re-orders under the scroll, so a re-run months from now reports a different population under the same
run id. `SegmentationCorpus` carries `fetched_on` and `source` for exactly that reason, and the
manifest field is still a word that reads as "frozen split" to anyone who does not open the note.
`TEXT_ONLY_VIEWS` is a hole by construction — anything added to it is exempt, and adding to it is one
line; the guard is that it is built in the registration loop and has its own test, but "deliberately"
is not "correctly". Nothing checks that a cache is the snapshot a gated figure was measured on; the
two-snapshot refusal narrows that and does not close it. `headline_capable(task)` is a per-task
filter and not a per-claim one: it stops a segmentation corpus backing a pair claim and does nothing
about a segmentation corpus backing a segmentation claim about a shape it holds zero of.
`tests/test_splits_manifest.py` now imports `bench/corpora.py` rather than regex-parsing it, which is
more robust than a second weaker parser and means an import error there kills collection of the whole
manifest test file. Both entries carry a great deal of prose and prose goes stale. And
`bench/splits.toml` sits outside `check_claims`'s scan globs, so every figure in the governance file
— including the two recall ceilings that predate this record — is named by run id but not gated.

### Not closed

**The saved runs still read `splits_declaration: "UNDECLARED"`.** The mechanism is fixed — the
runner's `declared_role()` returns `held_out` for both corpora — but the string in
`bench/results.json` is a literal written at `--save` time and nothing rewrites a saved entry. It was
not re-saved for three independent reasons, any one of them sufficient: `bench/results.json` was
being written by another workstream during the same session, so a concurrent `--save` would have
clobbered one of them; `--save` re-fetches, and the Socrata catalog is live, so a re-save measures a
different population from the one the 67 published citations were taken on, and every cited figure
would move with nothing visible to say why; and D-031 already requires that re-run to happen *after*
the tokenizer work lands, so baking a half-finished tokenizer into the gated table would be worse
than an UNDECLARED string. The handoff is unchanged and the manifest no longer blocks it: whoever
finalises the tokenizer work runs the governed-gold runner with `--save` and then
`tools/check_claims.py --render`, and the entries will carry `held_out`.

`bench/run_governed_gold.py` does not yet call the new `require_task()` accessor, which is shipped
and tested and should be adopted. Its hard-fail on `role = "tuning"` was left alone: the right
behaviour is to *label* a tuning figure rather than refuse to produce one, and that is a change to
that file with its own record owed. **R3 was honoured throughout** — SDU-21 AD `test.json` was not
fetched, not spent, and its designation was not touched; D-043 assigns it one.

---

## D-035 — Collaborators are injected, not discovered; and a custom `Scorer` re-ranks without re-searching

**Status:** shipped · **Evidence:** `src/acronymkit/engine.py`, `src/acronymkit/scoring.py`,
`src/acronymkit/nlp/base.py`, `tests/test_engine.py`, [`ARCHITECTURE.md`](ARCHITECTURE.md)

README.md and `docs/ARCHITECTURE.md` both advertised "plug in your own tagger — implement the
`NlpBackend` protocol". The protocol was real and `isinstance` passed against it, but
`AcronymEngine.__init__` took `config` and nothing else. The documentation described a rule the code
did not implement, and the only route in was assigning to an underscore slot on a `__slots__` class.

### The seam

```
AcronymEngine(config=None, *, backend=None, tokenizer=None, extractor=None, scorer=None)
```

Keyword-only, plain constructor wiring. No registry, no entry-point group, no discovery, nothing
reachable at import time — R10 is not negotiable here and a seam that scans the environment to find
its collaborators would have breached it. The default `extractor` is built from the *effective*
tokenizer, so injecting only `tokenizer` propagates into extraction and disambiguation rather than
being quietly half-applied. An injected `scorer` is the resolved value of the existing lazy slot, so
the lexicon and the n-gram model are never read on its behalf. `NlpBackend` is exported as
`acronymkit.NlpBackend` through the lazy `_EXPORT_SOURCES` table, so the import cost is unchanged.

**A premise in the audit's proposal is false and was not made true by inventing the missing pieces.**
It said to promote `NlpBackend` "alongside `SupportsLexicon` and `SupportsPronounceability`, which
`Scorer` already duck-types". Those two protocols do not exist. A grep of the whole repository
returns exactly one hit, the audit's own sentence at `docs/AUDIT-2026-08.md:687`. Writing them into
existence to satisfy the phrasing would have widened the pinned public surface for a promise nobody
had documented. The gap they gesture at is real and is recorded below as still open.

### An injected backend replaces tier *resolution*, not merely its result

`resolve_backend` is not called, `is_available` is never consulted, no degradation warning is
produced, and `Config.strict` / `TierUnavailableError` do not apply. Supplying the annotator is
itself the availability decision. `engine_tier` is recomputed from `backend.name` so the metadata
never describes an annotator that did not run, and `requested_tier` is preserved, so the two fields
together remain an honest account of what was asked for and what happened.

Raising under `strict` was considered and rejected: it would key a `TierUnavailableError` off the
magic string `"heuristic"` appearing in a name the *caller* chose, which is a policy nobody can
predict from outside the library.

### No `bound(state)` hook on `Scorer`; the limit is documented instead

`ForwardGenerator._beam_bound` re-derives the objective in closed form from `ScoringWeights` and
never calls the scorer. So a custom scoring term re-ranks the frontier the search retained and
cannot enlarge it — it changes the ordering, not the search *space*. Four reasons the hook was
refused rather than built: the audit's `bound(state) -> float` signature is unimplementable without
also publishing `_State`, `_completion_table` and `_PrefixProbe`; admissibility cannot be enforced on
a caller's override, so a stated library property would become a promise about unverifiable code; the
exhaustive regime already hands any objective the complete space, reached by raising
`max_search_nodes`; and a new public hook on the search needs its own D-number and its own `--save`,
which is precisely the bundle R6 forbids.

`metadata.truncated` is the runtime signal for when that limit binds, **with one documented
exception found by reading `_search` for a path that discards states without setting the flag**:

```
allow_token_skipping = False, plus a max_acronym_length every remaining branch overflows
  -> successors comes back empty, the whole frontier is abandoned unscored,
     the result is the injected plain initialism alone,
     and truncated stays False, because neither a cut nor a budget was responsible
  measured on three such configurations: the scorer was called exactly once each time
```

That is a `generator.py` wart, described rather than fixed because `generator.py` was not in scope.
**If someone repairs it by setting `truncated = True` there, the paragraph in `Scorer`'s docstring
and its test become stale and must be deleted rather than edited.**

### The thread-safety guarantee is now conditional, and says so in four places

It held *because* the engine built everything it held. An injected collaborator may carry state the
engine cannot inspect at construction time, so the guarantee is stated conditionally in the engine
module docstring, the `AcronymEngine` class docstring, the `NlpBackend` docstring and
`ARCHITECTURE.md`. Injecting nothing keeps the unconditional guarantee.

### Two false sentences this workstream wrote and then killed with its own tests

Recorded because both were already in a docstring when the test that killed them ran, and both are
the flattering reading of a mechanism nobody had checked.

*"Supplying a `backend` imports less, because the spaCy and NLTK adapter modules are never touched."*
False: `src/acronymkit/nlp/__init__.py` imports `heuristic`, `nltk_backend` and `spacy_backend`
eagerly, so `from .nlp.base import ...` binds all three whatever the engine does. Replaced with the
true statement — injection skips the *availability probe*, the part that tries to import spaCy or
NLTK and load a model — and pinned by a monkeypatch test asserting `resolve_backend` is not called,
which is machine-independent where a `sys.modules` assertion would only have measured which optional
runtimes happen to be installed on the box that ran it.

*"`Config.fast()` ships `beam=32`, so the footgun bites at shipped settings."* True and inverted.
`fast()` also sets `allow_multi_letter_tokens=False`, which collapses the branching factor:

```
un-gated mechanism probe -- phrase-length ladder, published nowhere
  stock Config()     runs exhaustively up to  9 eligible tokens, beam mode at 10
  Config.fast()      runs exhaustively up to 14 eligible tokens, beam mode at 15
```

Naming a beam width without the node budget beside it reverses which configuration is exposed.

### How it fails

The thread-safety warning is prose, and prose does not fail a build: nothing stops a caller injecting
a mutable spaCy pipeline and sharing the engine across `batch_generate`'s pool. `_achieved_tier` on
an injected backend is a string comparison, so a caller who names their Tier 0 wrapper
`"my-heuristic"` gets `STATISTICAL_NLP` in the metadata — a magic string that is now load-bearing on
caller-supplied data rather than on three names the package controls. `strict` is silently
inapplicable under injection, which is argued for above and is still a behaviour change hidden behind
a keyword argument. And `acronymkit.NlpBackend` is now in the pinned `EXPECTED_ALL`, so removing it
later is a downstream `ImportError`.

---

## D-034 — A square bracket is accounted for because it *can* be quoting, not because every bracket is

**Status:** reporting half fixed and shipped; the tokenisation half deliberately open ·
**Amends:** D-024 · **Evidence:** `src/acronymkit/governed/tokenizer.py`,
`tests/test_governed_edge_cases.py::test_a_bracket_is_discarded_only_where_it_is_quoting`,
`::test_a_discarded_bracket_is_always_half_of_a_pair`,
[`GOVERNED_NAMING.md`](GOVERNED_NAMING.md#what-the-splitter-accounts-for)

D-024 drew a line between the characters a physical name is made of and everything else, and put
nine characters on the silent side of it. Two of those nine were on the wrong side unconditionally:

```
before   split_identifier_parts('value[x]')  ->  tokens ('value','x')   unaccounted ()
after    split_identifier_parts('value[x]')  ->  tokens ('value','x')   unaccounted ('[', ']')
```

Two characters were discarded and the report said the whole name had been read. That is D-024's own
headline arriving through the one door D-024 left open, and the fix is the same fix: not the tokens,
which are unavoidable, but the accounting, which is the bit a pipeline gates on.

### Why the obvious fix is wrong, and why the next one is worse

Strip brackets only when they wrap the whole identifier — auditor 1's proposal, on the *do not build*
list at the end of the audit's question 1 — and `[db].[schema].[TXN_ID]`, the case the rule exists
for, stops reading, because the brackets do not wrap the whole of that either. The next reading, a
matched-pair test per dot-segment, fails more subtly: it decides on the caller's behalf that a dot
introduces a path, which is the one thing this subsystem refuses to decide, and it makes
`[my.column]` unreadable when brackets exist in T-SQL precisely so a dot can sit inside a name.

### The rule

A bracket is quoting when it is *positioned* as quoting: an unnested matched pair, opening where a
name could open and closing where a name could close. The test is on the character before an opener
and the character after a closer, and it is the same test the splitter already applies to decide a
token has ended — a separator, whitespace, or a character it could not read. `.` is not privileged;
it ends a name exactly as `_` and `/` do.

```
re-derived here against the shipped tokenizer, not quoted from the workstream
  [TXN_ID]                 ()                    [a][b]      ('[', ']', '[', ']')
  [db].[schema].[TXN_ID]   ()                    [TXN_ID     ('[',)
  [my.column]              ()                    TXN_ID]     (']',)
  TXN_[ID]                 ()                    value[x]    ('[', ']')
                                                 TXN_ID[0]   ('[', ']')
```

`ACCOUNTED_SEPARATORS` keeps all nine characters and keeps its published value. What changes is what
membership *means*: "may be discarded without a signal" rather than "is". The direction a caller
actually checks against is unqualified and unchanged — a character outside the set is always
reported.

### What a pipeline sees

```
catalog {TXN: Transaction, ID: Identifier, 0: Zero}
  expand_identifier('TXN_ID')      phrase 'Transaction Identifier'        is_fully_known True
  expand_identifier('TXN_ID[0]')   phrase 'Transaction Identifier Zero'   is_fully_known False
```

Every token resolved in both. The second is not fully known because two characters were dropped and
are now said to have been dropped. That is the same behaviour change D-024 shipped, one door further
in, and it deserves a release note rather than a footnote.

### The tokens do not move, and that is the deferral

A bracket separates whichever branch it takes, so `value[x]` is `('value', 'x')` before and after.
Whether `x` should be a token of its own — a lookup key, a row somebody owes the catalog — is the
larger question, and it is the dot-as-path-separator question wearing different clothes. That half is
not answered here. What could not be deferred, and was not, is a guarantee reporting a clean result
while a character is gone.

### The guarantee, restated rather than weakened

Seven of the nine accounted separators are accounted for unconditionally. The two brackets are
accounted for **per occurrence**, so for those two the counting equation holds as a bound in both
directions — nothing invented, nothing both kept and reported — rather than as a flat exemption. The
property test states it that way instead of re-deriving the positional rule, which would be the
implementation written twice; beside it sits a property that does not depend on the rule at all: a
bracket is discarded only as one end of a matched pair, so openers and closers are discarded in equal
numbers. The rule itself is a table of inputs and expected reports, and the module's two readings —
the reference scan and the ASCII pattern — are checked against each other exhaustively over
`[]A1_.` up to length four, because a positional rule goes wrong at the ends of a string and where
two brackets meet.

### What a port must change, and has not yet

`docs/notes/governed-json-contract.md` §6 classifies `[` and `]` as SEPARATOR unconditionally and
carries the worked line `"[TXN_ID]" -> ["TXN","ID"] unaccounted []`. It needs the positional test
above and the `value[x]` row beside that line. **The contract file is not updated, so a port built
from it diverges from this implementation on exactly this rule.** R8 says a wire-contract change gets
a design first; this record is that design, and applying it is the open follow-up.

### How it fails

The rule is over-permissive in one direction — `TXN_[ID]` reads as quoting, because an opener after
any separator is treated as a place a name can open — and it reads `[]` as an empty quoted name,
reporting nothing, which inherits the vacuous-empty-name case D-024 already left standing. Both are
pinned rather than hidden. D-024's recorded DTO gap is also untouched: `ComplianceResult` and
`PhysicalName` carry no accounting, so a bracket reaching `is_compliant` still surfaces only as a
`NOT_UPPER_SNAKE` finding.

---

## D-033 — The digit rejoin was gluing two numbers together, and `normalize` moved the name every time it did

**Status:** fixed, shipped · **Evidence:** `src/acronymkit/governed/expansion.py::_rejoin_digit_tokens`,
`tests/test_governed.py::test_normalize_is_idempotent_over_catalog_shapes`,
`tests/test_governed_edge_cases.py::test_a_join_that_would_make_one_longer_number_is_refused`,
[`GOVERNED_NAMING.md`](GOVERNED_NAMING.md#idempotence)

Two catalog rows and pure ASCII were enough to break an invariant this project states as holding *by
construction*:

```
before -- catalog {'11': 'Eleven', '911': 'Emergency'}
  normalize('E_9_1_1')          ->  'E_9_11'  ->  'E_911'
  expand_identifier('E_9_1_1')      'E 9 Eleven'
  expand_identifier('E_911')        'E Emergency'

after -- re-derived here against the shipped code, same catalog
  expand_identifier('E_9_1_1')      'E 9 1 1'
  normalize('E_9_1_1')          ->  'E_9_1_1'  ->  'E_9_1_1'
  expand_identifier('E_911')        'E Emergency'
```

The meaning of the column moved with the name, which is what makes this worse than a cosmetic
wobble. `11` and `911` are not a contrived pair; a municipal or emergency-services standard
plausibly carries both.

### Why the test suite could not see it

`test_normalize_is_idempotent_under_every_policy` parametrises over every identifier in the fixture
corpus and every named policy — and varies everything except the dimension the defect lives in.
Idempotence is a joint property of a name *and a catalog*: between the split and the judgement sits a
dictionary-aware pass, so what the second call sees depends on which rows exist. No identifier in the
forty-line fixture corpus carries two adjacent all-digit tokens and no fixture catalog has nesting
digit-leading rows, so the test was structurally incapable of firing however long it ran. This is
R9's fifth question — *is the corpus capable of showing the phenomenon* — asked of a test suite
rather than of a benchmark, and it is the more useful place to ask it.

The invariant is now also parametrised over catalog *shapes*, with the nesting catalog among them,
and a companion test asserts that the normal form expands to what its source expanded to — so
idempotence cannot be satisfied by a rewrite that moves a name once and then stands still.

### The rule that changed, and the mechanical reason for it

A joined form that is itself all digits is refused. One condition, in one pass, so all four verbs
keep running it identically and `naming.py` needed no edit.

Every verb here rebuilds a name out of its tokens and the next call splits that name again, so **a
joined token is safe only while splitting it returns the pieces it was joined from.** `1MM` does: it
reads back as two tokens and is rejoined, unchanged, every time. `911` does not — a digit run has no
internal boundary, so it reads back as one token — and that is how the first pass's output handed the
second pass a `9` sitting beside a new `11`.

There is a second argument for the same line and it is the stronger one. This pass exists to undo a
split *the tokenizer* made. The tokenizer never puts two digit tokens next to each other, because a
run of digits is one token — so two adjacent digit tokens mean a separator, a space or an unreadable
character stood between them, and joining across that is not a repair. It is the catalog reaching
across a boundary somebody typed.

### What was refused

**Running the pass to a fixed point.** It terminates — the pass strictly reduces token count — and
the fixed point is idempotent. It also makes `E_9_1_1` mean "E Emergency", which is the catalog
reaching across two writer-placed separators in the one subsystem whose whole thesis is refusing to
guess.

**Rejecting nesting digit-leading keys at dictionary build time.** It breaks the catalog that
motivates the rule. Under the shipped fix that catalog keeps both rows and both stay reachable —
`expand_token('911')` is Emergency and `E_911` is fully known — and only `9_1_1` stops silently
becoming it.

**The rule its author preferred, which is better than the one that shipped.** Join only tokens that
were contiguous in the *source*, so the pass undoes only splits the tokenizer itself made. That is
the rule the docstrings already claim the pass follows, it is a strict superset of what shipped
(an all-digit adjacency always crosses a separator), and it would also stop `TXN_1_MM` becoming
`1MM`. It was not built for two reasons, both worth keeping: it needs token spans threaded through
`_rejoin_digit_tokens`, whose third caller is `naming.py::to_physical_name`, and splitting the
behaviour across the four verbs would break the contract's "all four, identically"; and it is not
required for idempotence, which the shipped fix restores on its own. It is the open question here
rather than a thing done quietly.

### What a port must change, and has not yet

`docs/notes/governed-json-contract.md` §6.4's pseudocode has no all-digit condition and its
"consequence a port must reproduce" line is unchanged, so it now describes an algorithm this code
does not run. The pseudocode gains one condition:

```
i = 0
while i < len(tokens):
    if tokens[i] is all digits and i + 1 < len(tokens):
        joined = tokens[i] + tokens[i + 1]
        if joined is NOT all digits and dictionary.resolve(joined, policy) is not None:
            emit joined; i += 2; continue
    emit tokens[i]; i += 1
```

and the consequence paragraph gains a sentence: a join whose result is itself all digits is refused,
because two digit tokens can only be adjacent across a separator and a joined digit run does not
split back into the tokens it was made from. "All digits" is the Unicode digit test in both places.

### How it fails

A catalog carrying `2020` no longer turns `FY_20_20` into it, and that two-token case *was* already
idempotent — so a working behaviour was removed to close a three-token one. It was taken because the
mechanism is the same, because a decimal point manufactures the same adjacency in real identifiers
(`9.875` splits at the dot into two digit tokens, and the old rule would have joined them for any
catalog carrying that row), and because a rule that fired on three tokens but not two would be tuned
to the example rather than to the cause. If a caller wants `FY_20_20` to mean 2020, the honest fix is
to write the name `FY_2020`.

Idempotence also still rests on a premise about rewrite targets: an approved token that itself
re-splits and re-joins to something other than itself would move a name. No fixture or plausible
catalog carries such a row. It is stated in the code and the docs rather than enforced, because the
enforcement point would be dictionary build time — the design refused above.

**One figure that exists and is deliberately unpublished.** A scratch sweep over the
identifier-shaped strings in the governed gold showed adjacent all-digit tokens are common there,
which is what turned this from a two-row curiosity into a live hazard for real schemas. That sweep
went through no runner, so its counts appear in no document. If they are wanted in `docs/`, the work
is building the runner.

---

## D-032 — Two short-form-span fixes that looked like one change, and a long-form rule that was free on exactly one corpus

**Status:** one shipped, one held, one reverted · **experiments nine and ten** ·
**Evidence:** `bench/run_shortform.py --variants --spans`, `shortform.*` in `bench/results.json`,
`src/acronymkit/extractor.py::_trim_span`, `tests/test_extractor.py`

Three candidates arrived together. Measured together they are 85.18<!--claim:shortform.med1250_all.high_precision.both.exact_f1:.2f--> exact F1 on MED1250
against a baseline of 83.85<!--claim:shortform.med1250_all.high_precision.baseline.exact_f1:.2f-->, and they look like one change. They are not: alone they are
84.21<!--claim:shortform.med1250_all.high_precision.balanced_trim.exact_f1:.2f--> and 84.74<!--claim:shortform.med1250_all.high_precision.two_word.exact_f1:.2f-->, and only one of them is free. That is what R6 is for and this is the record of it.

### Shipped: `_trim_span` no longer leaves a bracket open

The trim stripped trailing non-alphanumerics unconditionally, turning the bracketed region `FEV(1)`
into a candidate with an unmatched opener — a string that equals no annotation under any convention.
The long form was unaffected either way, because the matcher skips non-alphanumeric short-form
characters, so the defect cost a pair outright rather than mis-scoring one. The right edge is now
restored exactly far enough to close what the trim opened, all-or-nothing, never past the span handed
in, with the balance scan bounded at 32 characters and short-circuited unless the first character
removed was a closing bracket. That guard is not cosmetic: without it the balance scan runs on every
call and costs measurable extraction throughput. The cost was found by interleaved re-measurement —
twelve alternating passes in one process — after a naive before/after in one direction had reported
the fix as *faster*, an ordering effect larger than the effect. No throughput figure is quoted here
because none of them went through a runner.

| MED1250 exact F1 (tuning split, `all`, high_precision) | value |
|---|---:|
| baseline | 83.85<!--claim:shortform.med1250_all.high_precision.baseline.exact_f1:.2f--> |
| **balanced trim (shipped)** | **84.21<!--claim:shortform.med1250_all.high_precision.balanced_trim.exact_f1:.2f-->** |
| two-word short form (held) | 84.74<!--claim:shortform.med1250_all.high_precision.two_word.exact_f1:.2f--> |
| both, as first measured together | 85.18<!--claim:shortform.med1250_all.high_precision.both.exact_f1:.2f--> |

On PLOD-CW (dev, test and pooled, both detokenisations) and on both SDU@AAAI-22 AE dev splits the
shipped fix is bit-identical to the baseline on every recorded field. **That is weaker evidence than
it looks and this entry says so.** R9's fifth question again:

```
bench/results.json, shortform.*.corpus -- how much of each corpus the fix can even touch
  PLOD-CW all      gold short-form spans carrying a bracket    43 of 2,869    1.50 %
  SDU-22 legal dev                                              7 of 1,213    0.58 %
  SDU-22 scientific dev                                         6 of   970    0.62 %
```

Four corpora agreeing on "no change" is mostly four corpora saying there was almost nothing to see.
The defensible claim is the narrow one: it stops the extractor emitting an unbalanced string, and it
takes nothing away anywhere measured. It is **not** "validated on held-out data". The MED1250 gain
also rides on an annotator convention — Ab3P's annotators wrote the parenthetical subscript into the
short form, and annotators who wrote `FEV1` would make the fix neutral rather than positive.

Two behaviours a reader could be surprised by, both deliberate and both tested: restoration is
all-or-nothing, so `A((b` stays as it is rather than becoming a third string that is neither balanced
nor what the trim decided; and a caller who raises `extraction_max_short_form_length` past the
32-character scan bound gets the old behaviour on longer candidates. That loses a candidate rather
than inventing one.

### Experiment nine — preferring the whole two-word bracketed text. Held, not shipped.

```
bench/results.json, shortform.*.two_word against .baseline
  MED1250 all, exact F1        high_precision 83.85 -> 84.74
                               general        83.97 -> 84.94
                               biomedical     82.94 -> 84.08
  SDU-22 legal dev, short form exact P 93.66 -> 96.11, R 37.76 -> 38.75, F1 53.82 -> 55.23
                               long form unchanged; overlap unchanged
  SDU-22 scientific dev, PLOD dev, PLOD test (both styles)   every field identical
  PLOD all / tight, the only held-out measurement
    short form   1048/71/1821 -> 1045/74/1824  tp/fp/fn
    long  form    939/180/865 ->  938/181/866
```

Every point in its favour is a tuning point, which R2 forbids presenting as generalisation, and the
one held-out corpus declines. Held under R7.

**The complication is worth more than the verdict.** PLOD carries zero multi-token gold short-form
spans in 2,869, so every two-word short form emitted there is a guaranteed false positive and the
corpus cannot show the upside even in principle. Its decline is a measurement of an annotation
convention, not of the fix — which means there is no held-out evidence about this change in either
direction, and none is available from PLOD. One part of the loss *is* adjudicable: long-form spans
are not structurally blind and one long-form true positive becomes a false positive. It is one span.

Precondition for reopening: a corpus that annotates multi-token acronym spans and has not been mined.
SDU-22 legal `train.json`, 3,564 unread samples, is the obvious candidate.

**Amended by D-047:** that split is allocated to the legend flag's cost and experiment nine is the
loser — it stays held, because holding it costs nothing and the legend flag is shipped with an
unmeasured cost. It is not starved: `--variants` scores `two_word` and `legend` in one invocation, so
the run that spends the split must save this arm too. The capability question is settled in its
favour and against PLOD's: legal dev carries 26 multi-token gold short-form spans against PLOD's 0.

### Experiment ten — rejecting a long form that begins with a function word. Reverted.

`find_best_long_form` returns a suffix starting at the word that supplied the short form's first
character, so `OMB -> of Management and Budget` is a parse in which the `O` came from `of`.
Rejecting those is free on MED1250 and that fact does not survive being asked anywhere else. The
rejection set is the project's own 16-word `_strategies.SKIPPABLE`, deliberately, because a set
chosen after seeing the corpus is a tuned parameter wearing a rule's clothes.

| Corpus (`shortform.*.function_word_exposure`) | predictions the rule deletes | carrying a correct short form | a correct long form |
|---|---:|---:|---:|
| MED1250 (tuning) | 3 of 1,021 | 0 | 0 |
| SDU-22 legal dev (tuning) | 6 of 489 | 6 | 1 |
| SDU-22 scientific dev (tuning) | 5 of 585 | 5 | 2 |

**The mechanism is structural, not incidental. This library emits pairs, so a rule that rejects a
long form deletes the short form standing beside it** — and on corpora that score the two labels
separately, every long-form false positive it removes costs a short-form true positive at the same
moment. Eleven of eleven deletions across the two SDU-22 splits carried a correct short-form span.

```
bench/results.json, shortform.*.function_word against .baseline
  SDU-22 legal      SF exact F1 53.82 -> 53.30, SF overlap R 40.23 -> 39.74
                    LF exact F1 70.00 -> 70.19 but LF overlap R 71.00 -> 70.10
  SDU-22 scientific SF exact F1 72.15 -> 71.74, LF overlap R 79.03 -> 78.33
  PLOD all / tight  SF 1048/71/1821 -> 1044/68/1825, LF 939/180/865 -> 937/175/867
                    removes 3 SF and 5 LF false positives; destroys 4 SF and 2 LF true positives
```

It buys a little long-form exact precision and pays for it in recall on every label of every corpus
that can see it. **And it recovers nothing.** `OHCHR` should expand to `Office of the United Nations
High Commissioner for Human Rights`; the correct span starts to the *left* of `of`, so reaching it
means choosing a different long-form starting boundary — which is exactly what D-008 built, measured
and reverted. Four gold MED1250 long forms do begin with a function word and the rule would cap them
permanently; that count is recorded at `shortform.med1250_all.function_word_exposure` rather than
asserted in a test, because nothing under `tests/` reads a corpus. `tests/test_extractor.py` pins the
counterexamples instead, so the rule cannot be re-added without a failing test.

Three of the SDU-22 long-form golds the rule would delete look like annotation artefacts. The revert
survives discounting them entirely: even thrown out, the rule still deletes 11 correct short-form
spans on SDU-22 and 4 on PLOD, and an acronym token is the least ambiguous annotation these corpora
carry.

### Recall ceilings, printed here because R9.6 says they belong beside the scores

```
bench/results.json
  shortform.plod_all.corpus.short_form_spans_bracket_adjacent_pct       46.11
    -- share of PLOD gold short forms standing in a parenthetical arrangement at all
  shortform.sdu22_ae_legal_dev.corpus.ceiling_pct                       55.15
  shortform.sdu22_ae_scientific_dev.corpus.ceiling_pct                  74.23
```

Neither SDU figure is a bound: every point above it is bought by emitting a definition the corpus
does not annotate, paid for in long-form precision.

### This is not the bracket fix on the *do not build* list

Auditor 1's proposal strips `[` and `]` when they wrap a whole identifier, in the governed subsystem,
and breaks `[db].[schema].[TXN_ID]` — see D-034, which reaches the same problem from the other side.
This one restores a closer inside `extractor._trim_span`, which is private to `extractor.py`, used in
three places there, and not imported by `acronymkit.governed`. Different mechanism, different module.

### The methodological point, which outlives all three results

A bundle hides which half is free. A single corpus hides which convention you are fitting. The rule
that is free on MED1250 is a recall regression on institutional prose, and the fix that gains on
biomedical abstracts cannot be scored at all on the one corpus this project treats as held out. Both
facts required measuring one change at a time on more than one corpus, and neither was visible from
the number the batch arrived with.

### How it fails, and one thing that must not be dropped

**The published MED1250 headline is now stale.** Shipping the trim fix moved the shipped extractor's
score, and `extraction.med1250.acronymkit` was not re-saved, because saving it alone would red
`tools/check_claims.py` — `README.md`, `docs/EVALUATION.md` and this file carry the old figures on
the value-matched path, and the results file and the prose have to move in one change. Two ways to
close it: re-run `bench/run_extraction.py --save` and `bench/run_profiles.py --save` and update the
prose sites in the same commit; or cite the already-gated successor by run id, which the ratchet
prefers anyway. `docs/EVALUATION.md`'s sentence comparing this library to the Rust implementation
must be re-read rather than find-and-replaced, because the gap it describes has narrowed.
`spans.plod.*` is **not** stale — the shipped fix is bit-identical to baseline on every PLOD field.

Several runs downstream of the extractor — `admission.*`, `analysis.med1250.*`, `oracle.med1250`,
`cascade.*`, `rerank.*`, `termfreq.*`, `relaxation.med1250_*` — were not re-derived and may have
moved. Someone should sweep them after the headline is fixed.

The reverts could be wrong in the other direction. Experiment nine is the largest improvement in the
batch and was held on the strength of one held-out corpus that cannot score it positively even in
principle. Someone weighting "two corpora in two genres improve" above R7 as written would ship it,
and the run ids are there to argue from. Nothing here was measured outside biomedical abstracts, PLOS
article text, UN institutional prose and mixed-discipline paper abstracts — no legal, financial or
general-web prose, and the SDU-22 split named "legal" is not legal text, which `bench/splits.toml`
already records.

---

## D-031 — The governed subsystem now has an accuracy number, and it is a number about one function

**Status:** shipped; both corpora still undeclared in the manifest · **Evidence:**
`bench/run_governed_gold.py`, `tests/test_governed_gold.py`, [`EVALUATION.md`](EVALUATION.md),
`governed_gold.*` in `bench/results.json`

The governed half is a little over a third of the library by volume and carried no accuracy figure
for three releases. The justification on file was "exact by construction", which is a tautology: a
lookup table is exact about whatever the caller put in it.

```
re-derived for this record, 2026-08-23
  find src -name '*.py' | xargs wc -l                     26,117 lines
  find src/acronymkit/governed -name '*.py' | xargs wc -l  9,647 lines
```

(The workstream that built the runner quoted 9,370 of 25,210. Both halves have grown during this
session's edits, which is exactly why a line count belongs in a fenced block with the command beside
it rather than in a sentence.)

There is exactly one thing in the subsystem that decides anything on its own, and `tokenizer.py` says
so in its own docstring — where the identifier is cut. Everything else is a lookup against a
caller-supplied catalog. So the accuracy question is: **does it cut identifiers where the people who
named them cut them?**

### The gold, and why it is not the corpus section 0 killed

Two public sources publish, for the same column, a machine identifier and a human caption written by
the same organisation: SEC XBRL `tag`/`tlabel` and Socrata `columns_field_name`/`columns_name`. A
caption is admitted only when its alphanumerics case-fold equal the identifier's **and** it contains
whitespace. That discards every pair where the caption expands or abbreviates — the catalog's job,
not the splitter's — and leaves a population where only cut placement can differ. Nobody was
commissioned to write this gold, which is the point: section 0 of the August 2026 audit killed a
corpus whose annotators were instructed to *invent* abbreviations. Scored through
`expand_identifier(x, GovernedDictionary({}))` — public API, empty catalog, which the admission rule
forces rather than merely permits.

| Gold author | Subset | Pairs | exact % | bP % | bR % | ceiling % |
|---|---|---:|---:|---:|---:|---:|
| SEC us-gaap taxonomy | all | 3,090<!--claim:governed_gold.sec_xbrl.us_gaap.all.pairs:,--> | **98.25<!--claim:governed_gold.sec_xbrl.us_gaap.all.exact_pct:.2f-->** | 99.98<!--claim:governed_gold.sec_xbrl.us_gaap.all.boundary_precision_pct:.2f--> | 99.62<!--claim:governed_gold.sec_xbrl.us_gaap.all.boundary_recall_pct:.2f--> | 99.62<!--claim:governed_gold.sec_xbrl.us_gaap.all.boundary_recall_ceiling_pct:.2f--> |
| SEC IFRS taxonomy | all | 939<!--claim:governed_gold.sec_xbrl.ifrs.all.pairs:,--> | **85.52<!--claim:governed_gold.sec_xbrl.ifrs.all.exact_pct:.2f-->** | 100.00<!--claim:governed_gold.sec_xbrl.ifrs.all.boundary_precision_pct:.2f--> | 97.50<!--claim:governed_gold.sec_xbrl.ifrs.all.boundary_recall_pct:.2f--> | 97.50<!--claim:governed_gold.sec_xbrl.ifrs.all.boundary_recall_ceiling_pct:.2f--> |
| SEC filing registrants | all | 57,580<!--claim:governed_gold.sec_xbrl.filer_extension.all.pairs:,--> | 94.73<!--claim:governed_gold.sec_xbrl.filer_extension.all.exact_pct:.2f--> | 99.73<!--claim:governed_gold.sec_xbrl.filer_extension.all.boundary_precision_pct:.2f--> | 98.76<!--claim:governed_gold.sec_xbrl.filer_extension.all.boundary_recall_pct:.2f--> | 98.76<!--claim:governed_gold.sec_xbrl.filer_extension.all.boundary_recall_ceiling_pct:.2f--> |
| | **unmarked** | 268<!--claim:governed_gold.sec_xbrl.filer_extension.unmarked.pairs:,--> | **0.75<!--claim:governed_gold.sec_xbrl.filer_extension.unmarked.exact_pct:.2f-->** | 77.78<!--claim:governed_gold.sec_xbrl.filer_extension.unmarked.boundary_precision_pct:.2f--> | **0.47<!--claim:governed_gold.sec_xbrl.filer_extension.unmarked.boundary_recall_pct:.2f-->** | 0.47<!--claim:governed_gold.sec_xbrl.filer_extension.unmarked.boundary_recall_ceiling_pct:.2f--> |
| Socrata publishers | all | 26,536<!--claim:governed_gold.socrata.columns.all.pairs:,--> | 91.37<!--claim:governed_gold.socrata.columns.all.exact_pct:.2f--> | 97.63<!--claim:governed_gold.socrata.columns.all.boundary_precision_pct:.2f--> | 98.82<!--claim:governed_gold.socrata.columns.all.boundary_recall_pct:.2f--> | 98.82<!--claim:governed_gold.socrata.columns.all.boundary_recall_ceiling_pct:.2f--> |
| | **unmarked** | 959<!--claim:governed_gold.socrata.columns.unmarked.pairs:,--> | **34.93<!--claim:governed_gold.socrata.columns.unmarked.exact_pct:.2f-->** | 61.29<!--claim:governed_gold.socrata.columns.unmarked.boundary_precision_pct:.2f--> | **2.25<!--claim:governed_gold.socrata.columns.unmarked.boundary_recall_pct:.2f-->** | 2.25<!--claim:governed_gold.socrata.columns.unmarked.boundary_recall_ceiling_pct:.2f--> |

### Three things this establishes that the audit's un-gated version did not

**Every miss anywhere is a boundary the identifier does not mark.** `false_negatives_marked` is 0 on
all four arms and boundary recall equals its ceiling to the digit on every row. Half of that is
arithmetic — the ceiling is the union of the four rules the splitter reads, so a spurious cut at an
unsignalled position is impossible by construction — and saying only the empirical half is the
difference between a discovery and a definition. The empirical half: rule 6 (ordinal suffix stays
with its digits) and rule 9 (two-pass catalog join) can each *suppress* a signalled cut, and across
every pair measured neither did once.

**Pooling "SEC XBRL" hides twelve points.** us-gaap and IFRS come out of the same file, the same
fetch and the same scorer. us-gaap capitalises after stripping a hyphen (`Paid-in` -> `PaidIn`, the
cut survives); IFRS does not (`paid-in` -> `Paidin`, the cut is destroyed by the naming convention
before this package sees the string). Same lesson as PLOD and NameGuess arriving through a third
door: what the corpus's author was doing decides what the number means.

**The unmarked row is a bound, not a failure.** Boundary recall of 2.25<!--claim:governed_gold.socrata.columns.unmarked.boundary_recall_pct:.2f--> % on unmarked Socrata
identifiers is the whole of the 2.25<!--claim:governed_gold.socrata.columns.unmarked.boundary_recall_ceiling_pct:.2f--> % that is reachable without guessing. It is the price of the
refuse-to-guess design, and it is printed beside the headline rather than below it.

### The largest error class is a deliberate rule and was not changed

```
bench/results.json, governed_gold.*.false_positives_by_signal
  socrata.columns.letter_digit         1,818   _2013_q1_actual -> '2013 Q 1 Actual', gold '2013 Q1 Actual'
  socrata.columns.separator               16
  sec_xbrl.filer_extension.acronym_run    581   ATMandDebitCardExpense -> 'At Mand Debit Card Expense'
  sec_xbrl.filer_extension.letter_digit   362
  sec_xbrl.us_gaap.camel_case               2   .acronym_run 1
```

Rule 5 exists because `ADDRESS2` really is `Address 2`; publishers write `Q1` as one word. It is a
measured cost of a documented decision (D-024), recorded rather than acted on. If anyone takes it up,
the cheap version — do not split between a single letter and a digit run when the letter is the last
of its token — needs measuring against MED1250's `2D` / `T3` gold too, where the same shape means the
opposite thing.

### The gold's own noise floor, which the audit did not measure

```
bench/results.json, governed_gold.socrata.gold_conflict
  identifiers captioned with two different cut placements by two publishers
    contested_identifiers        68 of 25,117      0.27 %
    contested_occurrences_pct                      2.62 %
```

That is a floor under the disagreement any system can record against this gold, and it turns "the
gold is only one publisher's opinion" from an unfalsifiable caveat into a number. It was built
deliberately *instead of* re-deriving the audit's hand-annotated pass: a hand pass over this system's
own output is the gold-standard-I-partly-invented problem `bench/splits.toml` already refuses, and
its figure is not re-derivable by a runner, so R1 keeps it out of the docs entirely.

One decomposition the headline survives: a publisher-disjoint split, 111 portals against 105 with no
portal in both, lands within a third of a point of itself. Not an artifact of a handful of large
portals. A robustness check, not a train/test split — nothing was fitted.

### Licences, read from terms on 2026-08-23, and one correction back to the audit

**SEC.** `https://www.sec.gov/privacy`, "Website Dissemination": information presented on sec.gov is
public and may be copied or further distributed without the SEC's permission. That is **broader than
the audit's licence-table row for EDGAR**, which said no licence and no copyright statement is
published. It does not make the labels vendorable: the archive's own `readme.htm` §5.2 makes `tlabel`
taxonomy-authored (FASB, IFRS Foundation) or filer-authored, and the SEC cannot license text it does
not own.

**Socrata.** `https://dev.socrata.com/docs/other/discovery`. No licence covers the catalog metadata
at all. The one licence statement in sight — a CC BY-NC-SA 3.0 footer on the developer site — covers
the **documentation**, not the API responses. Recording it as the data's licence would be GLADIS
again with a different badge, which is the mistake R4 exists to stop.

### Both corpora are still UNDECLARED, and that is the open blocker

Every saved figure carries `splits_declaration: "UNDECLARED"`. The runner asks the manifest and hard-
fails on `role = "tuning"`, but only *warns* on a corpus nobody declared — which is exemption from R2
by omission, the failure the manifest exists to prevent. Registration is blocked on `tools/splits.py`,
which was not in the recorder's file scope either:

* `TASKS` is a closed vocabulary of `extraction`, `span_detection`, `disambiguation`. Neither corpus
  is any of those, and identifier segmentation is a genuinely different task — `bench/corpora.py`
  returns a different type per task, so widening the vocabulary is a decision about that contract and
  not a one-word patch.
* `headline_capable()` is task-blind: it returns any uncontaminated `held_out` corpus regardless of
  what task it is for. **The workstream's stated consequence — that registering here would silence
  the "no uncontaminated held-out corpus" advisory — is wrong today and was checked rather than
  inherited: `plod` and `sdu21_ai` already satisfy it, so the advisory is already silent.** The
  design gap is real; the specific harm claimed for it is not. What the task-blindness would actually
  buy is worse and quieter: a segmentation corpus would become an eligible source for a *pair*
  headline.

The drafted entries, with their licence URLs and read dates, are parked as a comment block in
`bench/splits.toml` so nothing is lost while the vocabulary question is decided.

### How it fails

**The SEC arms measure inverting LC3, not segmentation.** XBRL element names follow Label CamelCase
Concatenation — the element name *is* the standard label with spaces and punctuation removed — and
FRTA requires element names to be based on a presentation label. Both halves of each pair are real
production strings, so this is not the NameGuess failure; but it is a documented mechanical rule
being inverted, which is far more regular than an identifier somebody typed. us-gaap is close to a
ceiling effect for the same reason: LC3 guarantees a case change at every word cut.

**Zero UPPER_SNAKE identifiers in the entire gold**, and 29 dotted ones on one arm. UPPER_SNAKE is
what this package's own fixtures, docstrings and `REFERENCE_IDENTIFIER` are written in. These figures
say nothing about `TXN_APPLNT_DOB_DT`. Do not let anyone quote them as governed accuracy generally:
catalog resolution, class-word detection, compliance and naming are not in this table at all.

**The Socrata corpus is not frozen.** The Discovery API is live and re-orders under the scroll; only
`fetched_on` and the page count make that visible. `identifier_shapes.dotted` in particular is a thin
citation that could vanish on a different SEC quarter, which is the intended failure mode of a
citation and a thing whoever changes `--quarter` must expect.

**The admission rule keeps a biased third of Socrata columns** — only pairs whose caption is a
re-spacing of the identifier. That is by design the single-variable experiment, and it means the
population is unabbreviated columns whose publisher bothered to caption them, not a sample of schema
columns.

**The gold is a publisher's caption, not a governance ruling.** A data-governance function ruling on
`_2013_q1_actual` might side with the splitter against the publisher on all 1,818 rule-5
disagreements, which would move Socrata several points in the direction this table does not report.

**Re-run required after the in-flight tokenizer change lands.** D-034's bracket work touches
`tokenizer.py`. Re-running against it produced byte-identical entries, but whoever finalises it must
run `python bench/run_governed_gold.py --save` then `python tools/check_claims.py --render`, or
`docs/EVALUATION.md` carries stale figures behind correct-looking citations.

**The audit's own un-gated leads did not fully reproduce**, and nobody can say why: close on us-gaap
and Socrata, far apart on the unmarked row. The auditor's derivation is not recorded. This one's is,
in the runner, and this one is what is gated.

---

## D-030 — The disambiguator can say "I don't know". The number that makes that worth doing is the one nobody had measured.

**Status:** margin shipped as a read-only field; gate shipped opt-in and defaulted off; per-arity
thresholds measured and refused (**experiment eight**) · **Evidence:**
`disambiguation.sdu21.abstention_curve` in `bench/results.json`,
`src/acronymkit/disambiguation.py`, `src/acronymkit/models.py`, `tests/test_disambiguation.py`

### What shipped

`DisambiguationResult.margin` — top1 minus top2, `None` below two candidates — and `.abstained` are
computed fields on every result. `LexicalDisambiguator(..., min_margin=x)` answers only when
`margin >= x`, rejecting anything outside `[0.0, 1.0]`, non-numbers, `bool` and NaN with
`ConfigurationError`.

**It is off by default and the default is the decision, not an oversight.** Gating is a
coverage/accuracy trade, and where a caller sits on it depends on what a refusal is worth to them,
which the library cannot observe. D-029 establishes there are no external users, which removes the
compatibility argument for keeping it off but not the epistemic one.

### The measurement that reframes it

The audit's abstention table showed accuracy rising as the gate rose and called it the largest
measured improvement in the batch. Read as an improvement, that is wrong twice over.

First, F1 falls monotonically. Second — and this is the control that was missing — score the shared
task's own most-frequent baseline **on the same answered subset**:

```
bench/results.json, disambiguation.sdu21.abstention_curve
SDU@AAAI-21 AD dev, split_role = "tuning split, contaminated"

  gate   coverage %   accuracy when answered   F1      most_frequent on the same subset
  0.00      100.00            41.65            41.65             72.84
  0.02       50.91            52.27            35.27             72.14
  0.05       29.52            64.81            29.54             69.40
  0.10       22.78            70.00            25.98             68.30
  0.20       11.33            74.04            15.07             64.05
```

Below gate 0.10 the gate is not producing better answers, it is selecting easier questions. The
crossover at 0.10 is the whole case for gating at all, and R5 requires saying it is not uniform: on
3-way and 4-way candidate sets — 2,004 instances, 32.38<!--claim:disambiguation.sdu21.abstention_curve.instances_in_those_arities_pct:.2f--> % of the split — the trivial baseline is
still at least as accurate on the very same answered subset. Abstention is a **precision instrument,
not an accuracy fix**.

### Experiment eight — per-arity thresholds. Measured, refused, recorded.

The audit proposed them and gave a reason: "a margin on a two-candidate set is mechanically larger
than on a fifteen-candidate one". That is true of a normalised distribution and false of this scorer,
which blends three unnormalised terms.

```
bench/results.json, disambiguation.sdu21.abstention_curve
  median_margin_falls_as_candidate_count_rises        false
  median margins        2 -> 0.0244   3 -> 0.0221   4 -> 0.0149
                        5 -> 0.0214   6-9 -> 0.0171  10+ -> 0.0201
  coverage at a fixed gate is HIGHEST on 10+ sets (29.98 %), not lowest

  per_arity_coverage_pct                22.80    (global gate 0.10: 22.78)
  per_arity_accuracy_when_answered      70.59    (global gate 0.10: 70.00)
  per_arity_gain_over_global_gate       +0.59
  per_arity_thresholds_tuning_split     {2: 0.1069, 3: 0.0911, 4: 0.0392,
                                         5: 0.1512, 6-9: 0.1102, 10+: 0.1512}
  split_half_a / split_half_b accuracy at the same single global gate   72.16 / 67.85
```

Six free parameters, fitted in-sample, on a split declared `role = "tuning"`, for six tenths of a
point — and that is an **upper bound**, not an estimate, because nothing was held out. Against a
4.3-point spread from nothing but resampling one frozen shuffle, it is inside the noise. Not shipped.

*(The threshold vector above is the one in the results file. The workstream's own report quoted a
different vector for the same field; the gated file wins, and the discrepancy is recorded rather than
silently reconciled.)*

What *does* vary with arity is accuracy:

```
bench/results.json, disambiguation.sdu21.abstention_curve.by_arity, at the reference gate
  2-way   76.98      3-way   79.44      4-way   70.08
  5-way   66.67      6-9     57.92      10+     53.89
```

which is why a per-arity **table** ships beside the headline instead of a per-arity **threshold**.
`worst_arity_accuracy_at_reference_gate` is a recorded field for exactly this reason: R5 wants the
worst row printed beside the headline, not derivable from it.

### The gate is substantially a verbatim-evidence detector

At gate 0.10 the answered set is 64.82<!--claim:disambiguation.sdu21.abstention_curve.gate_0.10_share_of_answered_that_is_gold_verbatim_pct:.2f--> % gold-verbatim against an 18.15<!--claim:disambiguation.sdu21.abstention_curve.gold_word_in_sentence_base_rate_pct:.2f--> % base rate. Not entirely:
within the gold-absent subset the gate does still lift the system's own score, at a tenth of the
coverage.

**That consolation does not survive its own control, and this record applies R9.2 to the workstream
that wrote it.** Read the next field along in the same run:

```
bench/results.json, disambiguation.sdu21.abstention_curve.by_gold_evidence.gold_absent_from_sentence
  n = 5,066
  gate 0.00   accuracy 32.83   most_frequent on the same subset  74.32
  gate 0.10   accuracy 40.93   most_frequent on the same subset  70.97
```

Where the evidence the gate detects is absent, the trivial baseline is roughly thirty points ahead
both before and after gating. "It still helps inside the gold-absent subset" is true of the gated
system against itself and false of the gated system against the only control anyone would use. The
honest statement is that the gate is a verbatim-evidence detector nearly all the way down, and a
caller should expect coverage to **collapse**, not degrade, on text where expansions do not appear
near their acronyms.

### The inline/dictionary cap is not a margin

`INLINE_SCORE - MAX_DICTIONARY_SCORE` bounds the gap between the document's own definition and a
dictionary candidate at 0.01. A dictionary entry whose every word appears in the sentence reaches the
cap, so a naive gate above 0.01 would refuse the document's own definition of its own abbreviation —
the one answer this module documents as authoritative. **This was found by running the workstream's
own first docstring example and watching it abstain.** The gate therefore skips pairs whose top two
candidates differ in source; the exemption can only turn a refusal into an answer, never the reverse,
and the genuinely ambiguous case (two competing inline definitions, same source, margin 0.0) still
abstains.

**It assumes exactly two sources ordered by the cap.** "Top two differ in source" implies "the winner
is inline" only because inline is capped above dictionary. The Phase-3 `"neural"` source this module
explicitly plans for has no such ordering, and a neural/dictionary pair one point apart is a close
call rather than an artifact. **Re-derive this when that source lands; do not inherit it.**

### Scope, stated plainly

This is a dictionary-path feature.

```
bench/results.json, disambiguation.sdu21.abstention_curve
  instances_with_a_margin_pct                                        100.0   (dictionary path)
  default_path_margin_defined_pct                                     0.02   (1 of 6,189)
  default_path_derived_dictionary_candidates_not_already_inline          0
```

The audit's "the engine already computes a top1-top2 margin and discards it" is true of the path a
caller reaches by supplying a dictionary, and effectively vacuous on the path the README's
no-dictionary example takes. That correction came from D-029's re-derivation and is what descoped the
weighted-dictionary work this feature was supposed to arrive alongside.

### How it fails

**One corpus, one domain, one tuning split, and no second corpus exists for this task.** SDU-21 AD
`test.json` is R3-locked, so the only corroboration offered is the split-half check above, and a
4.3-point spread from resampling is the scale at which any threshold choice here should be trusted.
The reference gate is itself read off the split it is scored on — a defensible construction and still
a tuning-split observation. Nothing in `src/` reads it.

Two computed fields are now in the wire payload, so `model_dump()` / `to_dict()` / `to_json()` carry
them and a consumer round-tripping `DisambiguationResult(**result.to_dict())` will fail on extra
fields, exactly as it already does for `AcronymCandidate.length`. `DisambiguationResult` is not in
`schemas/acronym-engine-result.schema.json` and the governed contract and golden fixtures are
untouched, so R8 does not bite. `abstained` is inferred rather than recorded — nothing the library
produces can have that shape without having abstained, but a caller hand-constructing a result with
candidates and no primary will read as having abstained when they did not.

`AcronymEngine.disambiguate` has no gate: `min_margin` lives only on `LexicalDisambiguator`, and the
facade is the path the README advertises. The clean fix is a `Config` field, which would propagate
through `AcronymEngine(config)` with no signature change at all. Worth its own D-number and one line
in each of two files.

`disambiguation.sdu21.diagnosis.abstention` is left in place with its pre-exemption figures because
the audit cites it. Its rows differ slightly from this run — it gates on the raw margin where the
shipped gate exempts different-source pairs — and two runs measuring nearly-but-not-quite the same
thing is exactly the re-quote hazard `tools/check_claims.py` exists to catch. Someone should decide
whether to retire the old id.

---

## D-029 — Nobody passes a dictionary to `disambiguate`, because nobody uses the package yet

**Status:** accepted; descopes the weighted-dictionary work · **Evidence:** live public signals
re-verified for this record on 2026-08-23 (below), plus
`disambiguation.sdu21.abstention_curve.default_path_*` in `bench/results.json`

Three workstreams were about to spend effort on backward compatibility, on a default blend, and on
the last unspent held-out split, all on behalf of users. The question nobody had asked was whether
there are any.

### What is checkable, and was re-checked for this record rather than inherited

```
un-gated -- GitHub REST API, api.github.com/repos/pierce-lonergan/AcronymKit, read 2026-08-23
  stargazers_count   0     forks_count     0     subscribers_count  0     network_count  0
  open_issues_count  6     -- and all 7 issues/PRs ever opened, state=all, are dependabot[bot]
                              dependency bumps. Zero human-filed issues, zero human PRs.
  created_at 2026-08-09     first PyPI release 0.3.0, the only release
```

The repository is two weeks old and has no human outside its author in its history. That much is
first-hand.

### What the workstream reported and this record could not re-derive

```
reported by W1, NOT reproduced here -- the traffic and download endpoints need
credentials this recorder does not hold
  GitHub dependents                                     0
  external code-search hits                             0
  PyPI downloads                                      156, of which ~27 carry a real interpreter signature
  repository "clones"                                1,338, at 6.5-7.0 per workflow run -- i.e. this project's own CI
```

The clone figure is the interesting one and it is the shape of the whole finding: a number that reads
as adoption and decomposes into the project measuring itself.

### The consequence that changed other people's work

The abstention curve is a **dictionary-path** measurement, and the default path almost never has two
candidates to put a margin between. That is now gated:

```
bench/results.json, disambiguation.sdu21.abstention_curve
  instances_with_a_margin_pct                                     100.0    dictionary supplied
  default_path_margin_defined_pct                                  0.02    1 of 6,189
  default_path_derived_dictionary_candidates_not_already_inline       0
```

W1 reports the same shape at a larger scale — 56,223 instances across both splits, every candidate
the default path produced carrying `source == "inline"`, not one from a dictionary — but that sweep
went through no runner, so the gated figures above are the ones to cite. So "abstention ships today
and is free"
survives only as *the field is free*, and the audit's headline gate accuracy is the shipped blend
**with** `diction.json` supplied. The weighted-dictionary work is descoped on the strength of this:
no default blend shipped, and SDU-21 AD `test.json` stays unspent under R3.

It also removes the compatibility argument from three decisions at once — there is nobody to break —
without removing the epistemic ones. D-030 keeps its gate off by default anyway, and says why.

### How this finding fails, which matters more than the finding

**No public instrument can distinguish a caller who passes a dictionary from one who does not.** The
`default_path_*` figures above are a fact about a benchmark corpus and about what the library's own
code paths can produce; they are not observations of anybody's usage. The inference from "the default
path cannot form a margin" to "callers are not getting abstention" is sound; the inference from
"downloads are mostly CI" to "nobody has a private deployment" is not available to any instrument.

**Private use leaves no trace.** A vendored copy, an internal mirror, a corporate index, an air-gapped
install — the package is explicitly designed to work in the last of those — produce zero public
signal by construction. Absence of evidence is the only kind of evidence this finding has.

**It decays, and fast.** Every number above is a reading of a live counter on one day of a two-week-
old project. A single downstream adopter inverts the conclusion, and nothing in this repository will
notice. **Anything that cites this record as a reason not to preserve compatibility must re-run the
checks first.** The block at the top of this entry is the re-runnable half; the block below it is
not, and needs credentials.

**One thing it is not.** "No users" is not "no obligation". It is the removal of one specific
argument — that a change would break somebody — from decisions that mostly turn on other things.

---

## D-028 — The JVM can now host this library directly. Measured, that is still the worse route.

**Status:** spike; not adopted. `governed-batch` remains the supported JVM route · **Evidence:**
[`JAVA_INTEROP.md`](JAVA_INTEROP.md), `examples/java/`, `src/acronymkit/governed/models.py`,
[`notes/governed-json-contract.md`](notes/governed-json-contract.md), and the phase-1 GraalPy spike —
which left no artifact in this tree, and whose figures are marked below as the second-hand ones they
are

The consumer D-025 was built for is a Java Maven project. It drives `acronymkit governed-batch` as a
co-process and asked whether it could instead take a Maven dependency and call the library in-process.
GraalVM's Python — GraalPy — is distributed as Maven artifacts and runs Python inside a JVM through
the Polyglot API, so the question was answerable rather than rhetorical.

### The blocker was real, and it is gone

GraalPy runs pure Python well and compiled extensions badly. `pydantic` v2 ships `pydantic_core`, a
compiled Rust extension — on this machine, `_pydantic_core.cp313-win_amd64.pyd` — and four governed
modules imported pydantic. D-027 removed it. What is checkable today, and what makes the rest of this
record possible:

```
extension modules (.pyd/.so/.dll) in the import graph of
  from acronymkit.governed import GovernedNamer, audit_identifiers, load_bundle
                                                        none
the five verbs, plus audit_identifiers / render_audit /
  suggest_catalog_additions, run with pydantic, pydantic_core
  and _pydantic_core raising ImportError from sys.meta_path    all answer
negative control, same interpreter: import acronymkit.config   ImportError: blocked: pydantic
```

That is the precondition, not the result. It says the subsystem is now the *kind* of code GraalPy is
good at; it says nothing about whether hosting it there is a good idea.

### What the spike found, and which half of it can be re-run here

The spike ran the real `acronymkit.governed` inside a JVM-hosted GraalPy and diffed its output
against CPython 3.13 over the contract's Unicode edge cases. **Its figures are recorded here because
losing them would cost the next person the same spike, and they are second-hand: nothing in this
repository reproduces them, and this record's author did not re-run the GraalPy arm.**

```
reported by the spike -- NOT reproduced in this tree
  five verbs, 56 identifiers, CPython vs in-JVM GraalPy   byte-identical (327,754 chars)
  best in-JVM throughput                                  21,482 identifiers/sec
  the same, in the configuration a consumer gets by
    default on JDK 21                                      3,513 identifiers/sec
  jars                                                   143.2 MiB
  runtime unpacked into %LOCALAPPDATA%                     65   MiB
  cold start, best configuration                        7,047.9 ms
  cold start, optimising configuration                 13,033.8 ms
```

The other arm — the co-process, driven from a real JVM — is reproducible on this machine, and was
re-measured independently for this record: a single-file JDK 21 harness spawning
`acronymkit governed-batch` on the installed wheel, feeding 20,000 identifiers cycled from
`corpus_sample.txt` down one warm pipe, five runs.

```
measured here, JDK 21.0.7, CPython 3.13.4, one machine
  cold start: spawn to first record on the pipe   228.9 ms   median of 5
  steady state                                  18,022      identifiers/sec, median of 5
```

That lands within ordinary session drift of the spike's own subprocess figure, which is the check
that matters: the denominator of every ratio below is one both halves of this project measured
separately and agreed on.

### The decision, and the arithmetic behind it

**Keep `governed-batch`.** Against a co-process that starts in about a fifth of a second and holds
its throughput, the best in-JVM configuration buys roughly a tenth more throughput for two orders of
magnitude more start-up, a hundred-odd megabytes of jars against a wheel budget of 786,432 B, a
version-pinned JDK, two experimental VM flags and an extra jar. Take the flags away — which is what a
consumer who simply adds the dependency gets — and it is several times *slower* than the process
boundary it was meant to remove. Nothing about that is close enough to argue over, which is why this
is recorded as settled rather than as a preference.

**Record that it is now possible.** It was not, before D-027, and "we tried and the extension blocked
it" is the wrong thing for this file to say if it has stopped being true. If a JVM-native answer is
ever actually required, GraalPy is the low-risk route to it, for a reason that has nothing to do with
performance: it runs *this* implementation, so the answers are this implementation's answers. A
hand-written Java port cannot promise that. It would have to re-derive every rule in section 8 of the
wire contract by hand — locale-independent case mapping, full case folding, code points rather than
UTF-16 units, code-point ordering, Python's digit test, Python's 29-code-point whitespace set — and
each of those is a place where the obvious Java translation is silently wrong on inputs a clean
corpus never contains.

### What is not claimed

No figure here is in `bench/results.json` and none may be quoted in user-facing prose; they are in
fenced blocks so `tools/check_claims.py` reads them as the un-gated numbers they are. The GraalPy
column is not this author's measurement and is labelled as such. Throughput on the co-process arm was
measured with the fixture catalog and the fixture corpus, which repeats tokens the way a real schema
does — D-026's `schema`/`novel` warning applies to it unchanged.

And no `acronym4j` exists, still. The contract note's opening paragraph is unchanged and remains
true: what this repository ships towards the JVM is a wire contract, a golden replay set, a command
that any language can drive, and now `examples/java/` — a client, not a port.

---

## D-027 — pydantic is out of `acronymkit.governed`, and 940 payloads say the wire did not move

**Status:** shipped, for one subsystem only — D-023's larger decision is still open · **Evidence:**
`src/acronymkit/governed/models.py`, `policy.py`, `dictionary.py`, `audit.py`,
[`notes/pydantic-cost.md`](notes/pydantic-cost.md),
[`notes/governed-json-contract.md`](notes/governed-json-contract.md)

D-023 ended "**Migrate to dataclasses with explicit validation, and do it before the package is
published**", with a status of *decided, not executed*. This is the first half of that execution and
it stops at the subsystem boundary.

### Read the scope before the numbers

**The dependency is not gone.** `pyproject.toml` still declares `pydantic>=2.0.0`;
`acronymkit.config`, `acronymkit.models` and the whole generation path still build Pydantic models;
`[tool.mypy]` still loads `pydantic.mypy`; and `publish.yml`'s SBOM check still asserts that
`pydantic` and `pydantic-core` appear as components of this distribution — which they do, and a
release would fail if they stopped. What changed is one import graph: nothing under
`src/acronymkit/governed/` imports pydantic, so a process that only wants to expand `TXN_ID` no
longer pays for it and no longer loads a compiled extension. D-023's own ordering asked for exactly
this — the DTO layer first, `Config` second — and the second half has not been done.

### What it bought

Medians of 15 fresh interpreters per arm, one arm and one metric per interpreter, every arm sampled
once before any repeat so drift lands on all four rather than on the later ones. The bare-package arm
is the control: it was not touched by this change and it did not move.

```
                                       with pydantic   without    sys.modules
  from acronymkit.governed import
    GovernedNamer, audit_identifiers,
    load_bundle                          161.88 ms     26.27 ms    216 -> 117
  import acronymkit  (control)             2.73 ms      2.39 ms     86 ->  86
```

`pydantic` and `pydantic_core` are absent from `sys.modules` in the second column, which is the
structural half of the result and the half that cannot be flaky. The timing half is one machine and
one session; D-023's warning about drift on this host applies unchanged, and the ratio is what
carries the argument.

### The proof that the payloads did not move

The whole point of a DTO layer is the bytes it emits, so the check was the bytes. `git archive HEAD`
into a scratch tree gives the pydantic implementation; the working tree gives the dataclass one; the
same script runs against both.

```
940 payloads: 40 corpus identifiers + 7 hand-picked edge cases
              (emoji, empty, separators-only, NBSP, eszett, an fi ligature)
              x 4 policy presets
              x expand_identifier / to_physical_name / is_compliant / normalize / expand_token,
                each rendered three ways (to_dict, to_json(), to_json(indent=2))

  pydantic HEAD    3,996,282 chars   sha256 72614c77766ca06b...4328d46151a1
  dataclasses      3,996,282 chars   sha256 72614c77766ca06b...4328d46151a1
```

Identical, and the section 3 examples in the wire contract were re-checked against the running code
character by character on top of that.

### The one thing that did change, stated rather than buried

Every non-`bool` spelling of a boolean is now refused where pydantic coerced it. On `GovernedEntry`
and on `NamingPolicy` alike, `"false"`, `"no"`, `"yes"`, `"true"`, `1`, `0` and `1.0` used to become
booleans and now raise, naming the field. Nothing else narrowed: `confidence=1` still becomes `1.0`,
`max_name_length="30"` and `max_name_length=30.0` are still read as `30`, and every loader-path error
message is byte-identical to the one it replaces — which matters, because several of them are quoted
in the loaders' own errors and read by whoever is fixing a catalog file.

The narrowing is deliberate and `_flag`'s docstring argues it: JSON and CSV both have a spelling for
true, a catalog is authored by hand, and `"keep_as_abbrev": "false"` is a row somebody got wrong.
Reading it as `False` happens to be right; reading `"no"` as `True`, which is what pydantic did, is
wrong, and nothing at the point of use can tell those two cases apart. A named field and a refusal is
the outcome that can be fixed.

The exception class also changed on the DTOs, and in the direction D-023 asked for. A bad field value
on a model in `models.py` used to surface as `pydantic.ValidationError`, which is a `ValueError` but
is **not** an `AcronymKitError`, so it walked straight past the single `except AcronymKitError` that
`acronymkit.exceptions` promises catches everything this library raises. It is now
`GovernedValidationError`, which derives from `ConfigurationError` and therefore from both. D-023
recorded that leak under "noticed in passing, not fixed"; it is fixed here, for this subsystem.

`NamingPolicy` never had that leak and does not gain anything here: it wrapped its validation errors
in `ConfigurationError` under pydantic and still does, with the same message text. Its only
observable change is the boolean narrowing above.

### What was kept on purpose

`model_dump` and `model_copy` survive as methods on the new base class, and `model_copy(update=...)`
keeps its Pydantic semantics exactly — values written as given, not re-validated — because the
resolver rewrites three fields of an already-validated catalog row on the hot path and `models.py`'s
own module docstring documented the behaviour. Field *order* is untouched everywhere, because the
order is the emitted key order and the wire contract numbers it. `GovernedEntry` still checks every
field, because it is the one model built from data nobody in this package wrote; the result DTOs
normalise their sequences and keep their range bounds and check nothing else, because they are built
by this package out of values it computed itself and re-deriving a type check per field per record on
a path that answers tens of thousands of identifiers a second is paying pydantic's price without
pydantic.

### What is not claimed

No figure above is in `bench/results.json`, no bench runner was added, and none of it may be quoted
in user-facing prose — same footing as D-023's table, and for the same reason: the comparison arm is
a tree that no longer exists. The payload comparison is a different kind of evidence and does not
have that problem, because it is an equality rather than a magnitude.

This record does not claim the migration is complete, that the dependency count fell, that the
installed footprint fell, or that anything outside `acronymkit.governed` got faster. It claims one
import graph is clear and the bytes on the wire are the same bytes.

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
identical. This step alone took `to_physical_name` from 76.15 to 41.50<!--claim:governed.to_physical_name.median:.2f--> us; the second figure is the
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
| — importing `pydantic` and its dependencies | 30.09 ms | |
| — pydantic's one-time model-building machinery | 87.96 ms | |
| — everything this library itself does | 21.55 ms | |
| `import acronymkit.config`, pydantic already resident | 89.08 ms | 9.21 ms |
| warm `generate()`, `Config()` | 347.60 µs | 269.80 µs |
| warm `generate()` + `to_dict()`, `Config()` | 422.80 µs | 298.70 µs |
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
412.60 µs against 406.20 µs for the dataclass arm. Pydantic loses, and that is a tie.

Two by-products worth keeping whichever way the decision goes:

- `_Frozen.to_json` takes the slow half of both worlds. It is `json.dumps(self.to_dict(), ...)`,
  169.40 µs, where `model_dump_json()` produces the same document — **2.98× on a public
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
on the same day, against the 128.1<!--claim:micro.import.cold_import_engine_ms:.1f--> ms in `bench/results.json`. Only ratios carry the argument, which
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
   compute. Headroom is 220,702 bytes: the wheel measures 565,730 bytes against the 786,432-byte
   `BUDGET_BYTES` in `ci.yml`, re-derived from `python -m build --wheel` on 2026-08-23. SDU-21's own
   candidate dictionary is 76,910 bytes for 732 acronyms, so a prior scoped to a comparable
   inventory fits and a general one does not. A prior that ships is therefore a prior that has
   already decided which acronyms it covers, and nobody has proposed how.

   *This paragraph previously read "Headroom today is 113,269 bytes". That figure was derived under
   the 524,288-byte budget, which `ci.yml` replaced, and two independent auditors re-quoted it as
   current — which is how a stale number in a decision record does its damage. The conclusion above
   is unchanged, because 455 MB of PMC-derived counts clears either figure by four orders of
   magnitude. `ci.yml` now computes and prints headroom on every run rather than recording it in a
   comment, so the same drift cannot recur silently, and `tools/check_claims.py` no longer admits a
   new number backed only by the fact that some measurement happens to equal it.*

   *And the replacement has itself gone stale, which is the recurrence the footnote above is about
   arriving a second time in the same paragraph. Reported to this recorder on `2026-08-25` by the
   prohibitions pass (`docs/AUDIT-PROHIBITIONS-2026-08.md` correction `C3`) and retired here on
   `2026-08-26` rather than overwritten. The two byte counts in the sentence above describe a build
   this repository no longer produces; that page's section `12` re-ran the command at `HEAD` and
   records a larger wheel and a smaller headroom, still comfortably inside `BUDGET_BYTES`.*

   ***The more useful half of the correction is that neither figure was ever citable.*** *A wheel
   byte count is not a stable quantity: the same tree built twice gives the same size and different
   digests, because a zip stores mtimes, and a line-ending-normalised export of the same commit
   differs from the working checkout by over a kilobyte. **A wheel byte count published without
   naming its checkout is unreproducible by construction**, so the right form of this constraint is
   a ratio with a floor under it and not a figure. `ci.yml` prints headroom on every run, which is
   where a reader should take it from. **The conclusion is untouched and was never close**: the
   largest live ratio anywhere in this paragraph's arithmetic is three orders of magnitude, not four,
   and it clears either wheel figure regardless.*
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

At the time of this decision the wheel was 411,019 bytes of the then 524,288-byte budget,
leaving 113,269 bytes; the new resource is 34,096 bytes on disk and costs 3,779 compressed. The
figures in the two code blocks above
are **not** in `bench/results.json` — no bench runner writes them — so they live here and in
`data/LICENSES.md` and nowhere a claims gate can check them. If they should become citable, a runner
has to be written. And `tools/build_reliability_table.py --check` is not wired into CI, because the
check needs a fetched MED1250 and the `resources` job fetches no corpora; today only a maintainer
running it locally catches a hand-edited resource, while `tests/test_pseudo_precision.py` carries the
weaker corpus-free half.

*The first three figures in that paragraph are history and are marked as such, because the 113,269
was re-quoted as current by two auditors — from here and from D-020. Re-derived 2026-08-23: the
budget is 786,432 bytes, the wheel 565,730, so headroom is 220,702.*

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
sentence. Of the 270 gold abbreviation spans in the test split, **125 (46.30<!--claim:spans.plod.test.corpus.short_form_spans_bracket_adjacent_pct:.2f--> %)** stand in one of
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

Same ordering, same story, tighter estimates. The bracketed ceiling is 46.11<!--claim:spans.plod.all.corpus.short_form_spans_bracket_adjacent_pct:.2f--> % here against the test
split's 46.30<!--claim:spans.plod.test.corpus.short_form_spans_bracket_adjacent_pct:.2f--> %, so the sampling is not what produced it.

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

**We lose to the majority-class prior, badly: 41.65<!--claim:disambiguation.sdu21.acronymkit.accuracy:.2f--> % against 72.84<!--claim:disambiguation.sdu21.most_frequent.accuracy:.2f--> %.** That was the question worth
asking and it has the unflattering answer. It is recorded rather than tuned away, and nothing in
`src/` changed as a result of running it.

Two qualifications, both of which cut the other way from each other:

- The context scoring is **not** doing nothing. Random choice scores 31.72<!--claim:disambiguation.sdu21.random.accuracy:.2f--> % (analytic expectation
  31.62<!--claim:disambiguation.sdu21.random.expected_accuracy:.2f--> %), so bag-of-words overlap is genuinely above chance.
- But it is doing least where the decision is easiest. On two-way acronyms it scores 55.28<!--claim:disambiguation.sdu21.acronymkit.accuracy_by_candidate_count.2:.2f--> % against
  a coin-flip's 50.32<!--claim:disambiguation.sdu21.random.accuracy_by_candidate_count.2:.2f--> %; on ten-or-more-way acronyms it scores 27.11<!--claim:disambiguation.sdu21.acronymkit.accuracy_by_candidate_count.10+:.2f--> % against a random 7.72<!--claim:disambiguation.sdu21.random.accuracy_by_candidate_count.10+:.2f--> %. The
  lexical signal separates a wide field slightly, and a narrow one barely at all.

### What the breakdown by candidate count is for

One accuracy hides two different problems. Ours falls 55.28<!--claim:disambiguation.sdu21.acronymkit.accuracy_by_candidate_count.2:.2f--> % → 44.43<!--claim:disambiguation.sdu21.acronymkit.accuracy_by_candidate_count.3:.2f--> % → 35.13<!--claim:disambiguation.sdu21.acronymkit.accuracy_by_candidate_count.4:.2f--> % → 35.14<!--claim:disambiguation.sdu21.acronymkit.accuracy_by_candidate_count.5:.2f--> % →
25.63<!--claim:disambiguation.sdu21.acronymkit.accuracy_by_candidate_count.6-9:.2f--> % → 27.11<!--claim:disambiguation.sdu21.acronymkit.accuracy_by_candidate_count.10+:.2f--> % across arities 2, 3, 4, 5, 6–9, 10+; the most-frequent baseline falls
82.09<!--claim:disambiguation.sdu21.most_frequent.accuracy_by_candidate_count.2:.2f--> % → 79.74<!--claim:disambiguation.sdu21.most_frequent.accuracy_by_candidate_count.3:.2f--> % → 78.57<!--claim:disambiguation.sdu21.most_frequent.accuracy_by_candidate_count.4:.2f--> % → 66.27<!--claim:disambiguation.sdu21.most_frequent.accuracy_by_candidate_count.5:.2f--> % → 61.70<!--claim:disambiguation.sdu21.most_frequent.accuracy_by_candidate_count.6-9:.2f--> % → 39.14<!--claim:disambiguation.sdu21.most_frequent.accuracy_by_candidate_count.10+:.2f--> %. The baseline's advantage is largest
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
Space-joining scores 41.65<!--claim:disambiguation.sdu21.acronymkit.accuracy:.2f--> %; attaching punctuation instead scores 41.57<!--claim:disambiguation.sdu21.acronymkit.accuracy_punctuation_attached_context:.2f--> %. The choice does not
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
  exists to measure it against". It exists. Any neural disambiguator must clear 72.84<!--claim:disambiguation.sdu21.most_frequent.accuracy:.2f--> %, not
  41.65<!--claim:disambiguation.sdu21.acronymkit.accuracy:.2f--> %, because the trivial baseline is the real incumbent.
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
| `import acronymkit` | 149.3 ms | **2.3<!--claim:micro.import.cold_import_ms:.1f--> ms** |
| `from acronymkit import AcronymEngine` | 149.3 ms | 128.1<!--claim:micro.import.cold_import_engine_ms:.1f--> ms |
| import + construct + first `generate()` | 191.3 ms | 196.0<!--claim:micro.import.cold_first_result_ms:.1f--> ms |

**The third row is why this is written down.** Lazy re-export *moves* the pydantic cost to first use;
it does not remove it, and time-to-first-answer is unchanged. Quoting 2.3<!--claim:micro.import.cold_import_ms:.1f--> ms next to `pyab3p`'s
import cost would compare their working API against our shell, so the docs carry all three figures and
say so. The genuine win is narrower than the headline: a process that imports the package without
using the engine — for `__version__`, for a `TYPE_CHECKING` reference, or because a dependency pulls
it in — no longer pays the full import cost.

Rejected inside the same task: deferring `from importlib import import_module` to a helper. A/B over
31 fresh interpreters × 2 alternating rounds put it inside noise, so it went back to the simpler
form and the docstring claiming the win was deleted.

Not attempted: moving the DTO layer off pydantic. That is a breaking change to the public type
surface and needs its own decision. **It has one now: D-023**, which measures what the remaining
128.1<!--claim:micro.import.cold_import_engine_ms:.1f--> ms is made of and recommends the migration.

---

## D-014 — The generation ceiling is tokenisation, and it is mostly configuration

**Status:** decided · **Evidence:** `generation.med1250.coverage.*` in `bench/results.json`

All four presets converge to ~89.7 % recall@25, so a slice of the initialism bucket is never produced
at any rank. With the pool opened to depth 100,000: **51 of 546 pairs (42 of them
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
88.49<!--claim:oracle.med1250.own_space_recall:.2f--> % of gold while the greedy rule returns 78.40<!--claim:oracle.med1250.recall_acronymkit:.2f--> %, so the right span is present and
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

    gold span ties with the top-scoring span : 518 of 537
    gold span scores strictly below the top  :  19 of 537

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

Two things fall straight out. **14.01<!--claim:oracle.med1250.universal_miss_pct:.2f--> % of gold pairs are found by no system at all** — that is
the corpus's irreducible floor and every headline should be read against
85.99<!--claim:oracle.med1250.oracle_union_recall:.2f--> %, not against a perfect score.
And we find 7 pairs **no other system finds**, so we are not strictly dominated —
while `abbreviation_extractor` and `scispacy` find 0 and 0 such pairs respectively, and are.

### The measurement that actually decides it

A cross-system union conflates selection with generation: a pair only `pyab3p` finds may be outside
our reach entirely. So the decisive quantity is our *own* candidate space — every long-form span our
Schwartz & Hearst matcher could legitimately return, which is exactly the set its greedy walk picks
one element from.

    gold reachable in our own candidate space : 1061 of 1199
    we currently return                       : 940
    headroom for a better selector            : 121 pairs (10.09 points)

**Our candidate space already contains 88.49<!--claim:oracle.med1250.own_space_recall:.2f--> % of gold — more than `pyab3p` actually returns
(83.57<!--claim:oracle.med1250.recall_pyab3p:.2f--> %).** The right answer is being generated and then discarded. Every point of the gap to
the leader is available without one byte of new data.

### Consequences

- **Move 2 (pseudo-precision as a re-ranker over the fixed candidate space) is the correct shot**, and
  it now has a measured ceiling to aim at rather than a hope.
- **Move 3 (vendoring or deriving Ab3P's resources) is deprioritised.** It was predicated on a
  coverage story the data does not support. `Lf1chSf` may still help the single-character bucket
  specifically, but it is no longer the main event. **D-019 measured that: it does help, by a fifth
  of a point, on evidence too contaminated to trust, and it was refused.**
- Any future selection experiment should report against
  88.49<!--claim:oracle.med1250.own_space_recall:.2f--> %, because that is what a perfect selector over
  this candidate space would actually achieve.

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

The largest single category of extraction misses (28.7<!--claim:analysis.med1250.miss_taxonomy.pct_long_form_boundary_disagreement:.1f--> %) is the reference matcher truncating the
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
  counts, which turns "the heuristic seems about right" into a number: **84.1<!--claim:validation.syllables_cmudict.exact_match_pct:.1f--> % exact, 99.5<!--claim:validation.syllables_cmudict.within_one_pct:.1f--> % within
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
