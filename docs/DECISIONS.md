# Decisions, and things deliberately not done

Negative results are the easiest thing in a project to lose and often the most useful thing to keep.
This file records what was tried and abandoned, what was considered and cut, and why — so nobody
re-litigates a settled question from scratch, and so the settled questions can be re-opened on
evidence rather than on vibes.

Newest first.

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
disagree materially at all, not that 16.59% is *the* invention rate. The forced-subset alignment test
is a proxy — character alignment is the field's criterion for a definition, not the definition of one
— and its residue contains errors of both signs; a first pass flagged 6.33% and inspection showed a
chunk of that was the aligner's strictness on plurals and hyphens rather than a corpus fact, so 3.65%
is published as a lower bound with the strict figure beside it. A crude 49.72% "acronym-shaped
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
evidence that legal train resembles legal dev in structure. It decomposes well there (55.04% against
55.15%), which is why the extrapolation is offered at all, and it is still an extrapolation.

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
the legend *class* and loads the *gate* heavily; PLOD has 0.89% capability and 12 predictions, which
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
PLOD — the one held-out arm — has 0.89 % capability and 12 predictions. **The genre the risk was named
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
widening the gate to match a sentence is what D-039 refused — but **3.40 % is a FLOOR on the equation
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
arms have 0.00 % and 0.89 % capability. Shipping on by default would set a default on the split that
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
3-way and 4-way candidate sets — 2,004 instances, 32.38 % of the split — the trivial baseline is
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

At gate 0.10 the answered set is 64.82 % gold-verbatim against an 18.15 % base rate. Not entirely:
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

At the time of this decision the wheel was 411,019 bytes of the then 524,288-byte budget (78.4 %),
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
