# Definition of done — the fourteen criteria, swept

Eight criteria governed what "finished" means for this library, and a second mandate added six
more. They have been carried in mandates and answered one at a time in `docs/DECISIONS.md`; they had
never been read together, and a list nobody reads as a list is how a verdict that was true when it
was written goes on being repeated after it stops being true. This page reads them together, states
a verdict on each, names the evidence, and says what would close the ones that are open.

**Renumbering, third sweep — read this before following a cross-reference.** The second mandate
numbers its six additions `9` to `14`. This page already carried a *proposed* ninth, which is not one
of the standing eight, and the new tenth is that same question restated with a costing clause. The
mandate's numbering is adopted and **the criterion previously cited as "criterion 9" or "the ninth
criterion" is criterion `10` from this round on.** Four places still cite it by the old number and
are deliberately not rewritten, because three of them are historical records:
[`docs/AUDIT-2026-08.md`](AUDIT-2026-08.md) line `23`, [`docs/DECISIONS.md`](DECISIONS.md) D-051 and
D-057, and [`docs/EVALUATION.md`](EVALUATION.md) line `688`. D-069 records the decision and its
cost.

**Almost nothing here is asserted on the strength of a previous round's answer.** Every verdict was
re-derived by running the check or reading the code — the first two sweeps on 2026-08-24, the third
across 2026-08-24 and 2026-08-25 — including the five that were expected to come back met. Two came back differently from the standing read, and one of those is the
flagship criterion. **The exception, stated rather than papered over: at the third sweep criteria `6`
and `7` were not re-derived** and their verdicts are carried from the second. Two of fourteen carry a
verdict this round did not check, and the table says so in its own column.

**Second sweep, same day, after five workstreams landed.** Three verdicts moved and the movement is
recorded in D-057. Criterion 2 was closed there by making the criterion smaller, with the narrowing
published in the verdict column; **a third sweep re-opened it**, because the reason the narrowing
gave turned out to be false for half the subsystem it excused — see criterion 2 below. Criterion 3
stays open **and its evidence got worse**,
because the gate now counts the numbers it cannot check instead of omitting them — a better
instrument giving a worse reading is the outcome this page exists to keep visible, and it is the one
most likely to be argued away next round. Criterion 4 is met more strongly and its residual has been
replaced by a new one of the same class.

**How to read the numbers.** A figure written as a plain number in prose is a citation into
`bench/results.json` by run id — that is operating rule 1, and this document holds no exceptions to
it. A figure inside a fenced block is **command output, not a benchmark measurement**: the command
is printed above it, it re-derives in one line, and it is deliberately not quotable as a gated
figure. Nothing else appears.

---

## The table

| # | Criterion | Verdict | Evidence | What would close it |
|---|---|---|---|---|
| 1 | The disambiguator can say "I don't know" — abstention exposed, curve published decomposed, **policy confirmed on held-out data** | **met with qualification** — mechanism and publication, not value | `min_margin`, `margin`, `abstained` ship; `disambiguation.sdu21.abstention_curve`; `docs/EVALUATION.md` | An on-by-default `min_margin` proposal with a threshold and a cost model, then D-043's single spend of SDU-21 AD `test.json` |
| 2 | Every shipped subsystem carries an accuracy number — **RE-SCOPED, see below; the previous amendment is withdrawn** | **partly met** — `align` now carries an accuracy number over about half of each corpus; `synthesize` carries none and is **permanently unmeetable** | `backronym.{med1250,sdu21_ad}.accuracy` and `.{alignment,synthesis}`; `docs/EVALUATION.md`; D-054 as corrected | For `align`, a gold that reaches the undecidable pairs. For `synthesize`, **nothing** — the task has no correct answer for any gold to record |
| 3 | Every number gated, cited by run id, re-derivable offline from the sdist; **zero un-gated figures in user-facing prose** | **not met — and the evidence got worse, correctly** | `tools/check_claims.py --residue` now counts a deferred ledger and an unexamined residue that no earlier run had ever reported; two of the three named coverage gaps are closed | Migrate the deferred ledger, lowering the baseline in the same commit; widen the scan to `tools/` and `bench/`; widen the unit vocabulary — each one its own measurement |
| 4 | `bench/splits.toml` parses, is loaded by a tool, checked in CI for role/task/licence, mutation-tested | **met, and strengthened** | `tools/splits.py --check` in CI, now reporting reserved arms; `Corpus.require_unreserved` refuses a read; mutation-test class in `tests/test_splits_manifest.py` | Nothing. The stale `status` residual is fixed; a new residual of the same class is named below |
| 5 | At least one non-biomedical annotated corpus registered and reported, **with its short-form recall ceiling in the same table as its recall figure** | **met with qualification** | SDU@AAAI-22 AE registered, scored, gated; ceiling column present beside the recall figures in D-039 and, as of this round, in `docs/EVALUATION.md` | Nothing for the literal criterion. The corpus is a different *genre*, not a different domain, so the domain-generalisation gap is a separate item and stays open |
| 6 | Two documented-but-absent extension points exist, or the documentation stops claiming them | **met — carried, NOT re-derived at the third sweep** | Four injectable collaborators ship (D-035); the `acronymkit.data` entry-point group is deleted (D-038) | Nothing. The standing risk is re-declaring a pack group before a pack exists to load |
| 7 | No known defect where a report claims clean while data is lost | **met — carried, NOT re-derived at the third sweep** | All three governed defects re-probed live through the public API and all three are fixed | Nothing for the known set. "Known" is the whole content of the claim |
| 8 | The do-not list has grown, not shrunk | **met** | Nine audit-derived items carried forward unchanged, one added since, plus a class-level closure and a reservation discipline | Nothing |
| 9 | **NEW (Mandate II).** Every CI gate has a recorded in-situ mutation test, stored as an artifact | **not met — and now counted rather than assumed** | `.github/gates.toml`, `tools/gates.py --check`, `docs/GATES.md`; D-061. The register prints `CARRYING IN-SITU EVIDENCE: 0 of 36` on every CI run | One push that dispatches `gate-mutation.yml`, one red run log per gate, stored and dated. The mechanism ships; the evidence does not exist for a single gate |
| 10 | **RENUMBERED — this was "criterion 9, proposed".** The two tasks the README leads with can be adjudicated by a corpus this project did not tune on; or the reason it cannot is a permanent property of the task, with the filling instrument costed | **not met — the row is empty by construction, and the price is now known** | `headline_capable('extraction')` and `('disambiguation')` both empty; `tools/splits.py --check` prints both gaps; D-056's five promotion conditions; D-063 | D-056's five conditions in order, the first being a second adjudicator who authored none of the pooled systems. The reason is a **resource** limit, not a property of the task, so the second clause does not apply |
| 11 | **NEW (Mandate II).** The monoculture is measured, not assumed — union gain from a non-Schwartz-&-Hearst proposer, published, on a named corpus | **met** | `monoculture.*` (`103` run ids); `shapecue`, independence measured on two axes; PLOD-CW, `held_out`, uncontaminated; union gain `32.04 %` against a control of `0.00 %` on MED1250; full pairwise matrix in `docs/EVALUATION.md`; D-065 | Nothing for the literal criterion. The genre-versus-provenance confound in the *interpretation* is named, costed and open, and needs a corpus nobody publishes |
| 12 | **NEW (Mandate II).** The shipped extractor's short-form detection is shown competitive with `predict_all_caps` on held-out data, or the gap is published and explained in the same table as the flagship figure | **met by the first clause** | `shortform_contest.plod.*` (`14` run ids); on comparable gold the ordering reverses by `10.60` points pooled and `14.86` on test; the qualifier column is in the PLOD table; D-066 | Nothing for the literal criterion. What it does **not** show is extraction quality: the span scorer cannot tell correct pairing from random pairing, demonstrated at `1,054` wrong pairs |
| 13 | **NEW (Mandate II).** The deferred ledger has a written policy and a measured trajectory | **met — mechanism and policy; the trajectory is one observation** | `docs/CLAIMS-LEDGER.md`; `LEDGER_TRAJECTORY`, `MIGRATION_QUOTA = 12` and `trajectory_problems()` in `tools/check_claims.py`, mutation-tested red four ways; D-059 | A second and third round of movement. Two rows, one of them the baseline, is a rate with one observation — and `docs/DECISIONS.md` holds `115` of the `262`, which only the recorder may migrate |
| 14 | **NEW (Mandate II).** A second reader exists, in some form, for anything user-facing | **met, and the criterion is modest about itself** | `docs/SECOND-READER.md` — two triggers, six checks, costed at one agent slot; wired into `CONTRIBUTING.md`; first pass found `15` defects, `6` material, `7` of `15` in files the round never touched; D-060 | Nothing for the literal criterion. Nothing enforces it: the enforcing CI job is specified in one paragraph and not built, and until it exists and has been mutated red on a real push the policy is a document asking to be followed |

**Two verdicts differed from the standing read at the first sweep.** Criterion 2 was carried as met
and was not: the backronym subsystem ships in the public API, in the CLI and in the architecture map,
and had no accuracy number anywhere. Criterion 5 was carried as needing confirmation, and it
confirms — the ceiling really is printed in the same table as the recall figures — but the thing that
remains open underneath it is not the ceiling, it is that the corpus is a different *genre* and not a
different *domain*, which `bench/splits.toml` establishes by counting rather than by asserting.

**And criterion 9 is still not met, now on evidence rather than on absence.** The first instrument in
this project capable of producing a corpus of *edges* was built and run this round, and its own report
is that the substrate it was funded on does not supply the arbiter the plan was costed on. The gap did
not close; it acquired a price. D-056.

**Third sweep, after eight workstreams, a sampled-verification pass and a cold second reader.** Six
criteria are added and the page is renumbered; see the note at the head. What was the ninth is now
the tenth, and its verdict is unchanged while the *reason* for it moved: the Federal Register corpus
is now registered, at a third role — `single_annotator_reference`, which can never be
headline-capable for any task — so `headline_capable('extraction')` is empty because a
mutation-tested rule says so, rather than because the slot happens to be unfilled. The refusal D-056
recorded was right; what was never argued was its permanence, and a refusal persisting because a
two-element tuple was not extended is not a decision. **Criterion `2` moved backwards**: D-057 closed
it by narrowing, the narrowing's stated reason was refuted for half the subsystem, and it is now
*partly met* with one half permanently unmeetable. **Three of the six new criteria close, `9` does
not and is measured at `0 of 36`, and `10` does not and is now costed.** D-059 to D-069.

---

## 1. The disambiguator can say "I don't know"

**Met in mechanism and publication. Not met in value, and not confirmed on held-out data.**
D-044 adjudicated this and its verdict survives re-reading.

The mechanism is complete: `DisambiguationResult` carries a read-only `margin` and a derived
`abstained`, `LexicalDisambiguator(config, dictionary, tokenizer, min_margin=...)` refuses below the
threshold, and the default is off. The curve ships decomposed, with the shared task's own
most-frequent-expansion baseline scored **on the identical answered subset** in a column of the same
table rather than a paragraph underneath it, plus a per-candidate-set-size table and a gold-evidence
table.

What is not met is value, and the exact statement matters because two weaker ones have been in
circulation. Against the full-coverage `most_frequent` baseline at
72.84<!--claim:disambiguation.sdu21.abstention_curve.gate_0.00_most_frequent_accuracy_same_subset:.2f-->,
**no coverage level on the published curve wins until gate `0.15`**, where the system answers
16.77<!--claim:disambiguation.sdu21.abstention_curve.gate_0.15_coverage_pct:.2f--> % of the split at
accuracy 72.93<!--claim:disambiguation.sdu21.abstention_curve.gate_0.15_accuracy_when_answered:.2f-->
— and F1 falls monotonically the whole way, from
41.65<!--claim:disambiguation.sdu21.abstention_curve.gate_0.00_f1:.2f--> ungated to
15.07<!--claim:disambiguation.sdu21.abstention_curve.gate_0.20_f1:.2f--> at the tightest gate
measured. "Loses at every threshold" is false on that curve. "Loses at every threshold below `0.10`"
is true of a *different* comparison — the same-subset one — and reads as the full statement when it
is not.

The third clause of the criterion, **confirmed on held-out data**, has not been attempted and should
not be. D-043 gives SDU-21 AD `test.json` one named use, one trigger, and an explicit not-a-trigger
list; the trigger is a proposed on-by-default `min_margin` with a stated cost model, and D-044
records that no such proposal is currently defensible. So the split stays shut, and this criterion
stays open by design rather than by neglect.

---

## 2. Every shipped subsystem carries an accuracy number — re-scoped

**Partly met.** The previous amendment said the fifth subsystem *cannot* carry an accuracy number.
It is withdrawn, because that is false for one of the subsystem's two operations and was refuted with
functions the amending round had already written. What replaces it is a split verdict:

> **The criterion, as re-scoped.** Four subsystems carry an accuracy number. The fifth,
> `BackronymGenerator`, is **two operations and they are not alike**.
> `align` — read a real pair and say which word supplied which letter — **carries an accuracy
> number**, scored against the reading the alignment constraint settles by itself, published with
> the share of the corpus it reaches and with a bound over the share it does not.
> `synthesize` — invent a phrase for a target word with no source phrase — **carries none and is
> marked permanently unmeetable**: the task has no correct answer, so accuracy there is *undefined*
> rather than unmeasured, and no corpus, annotation or judge would define one.

### The half that is met, and how far it reaches

`backronym.<corpus>.accuracy` scores `align`'s top candidate against a gold nobody selected: on a
pair whose componentwise-earliest and componentwise-latest complete alignments read out the same
words, every complete alignment reads out those words, so the pair has exactly one reading. The
figure is exact match against it.

```
python bench/run_backronym.py --arm accuracy      -- command output, abridged
  med1250 / all     1,221 pairs    671 decidable   54.95 of corpus   ACCURACY 98.66
  sdu21_ad / all    2,308 pairs  1,300 decidable   56.33 of corpus   ACCURACY 100.00
```

**The same two figures, cited rather than left inside a block the gate cannot read:**
98.66<!--claim:backronym.med1250.accuracy.all.exact_match_pct:.2f--> % over
671<!--claim:backronym.med1250.accuracy.all.decidable_n:,--> decidable MED1250 pairs, which is
54.95<!--claim:backronym.med1250.accuracy.all.decidable_pct_of_pairs:.2f--> % of that corpus, and
100.00<!--claim:backronym.sdu21_ad.accuracy.all.exact_match_pct:.2f--> % over
1,300<!--claim:backronym.sdu21_ad.accuracy.all.decidable_n:,--> SDU-21 AD pairs, which is
56.33<!--claim:backronym.sdu21_ad.accuracy.all.decidable_pct_of_pairs:.2f--> % of that one.

Two things keep that from being a closed verdict on the subsystem. The denominator is a little over
half of each corpus, and over **all** feasible pairs the figure is a bound rather than a point:
61.87<!--claim:backronym.med1250.accuracy.all.accuracy_lower_pct:.2f--> to
99.16<!--claim:backronym.med1250.accuracy.all.accuracy_upper_pct:.2f--> on MED1250 and
57.50<!--claim:backronym.sdu21_ad.accuracy.all.accuracy_lower_pct:.2f--> to
100.00<!--claim:backronym.sdu21_ad.accuracy.all.accuracy_upper_pct:.2f--> on SDU-21 AD. An accuracy
whose interval is 37.29<!--claim:backronym.med1250.accuracy.all.accuracy_interval_width_pct:.2f-->
points wide exists, and it is not by itself an answer to *does this subsystem work*.

**And the figure it is not.** `generation.med1250.dictionary_backronym` sits beside these runs in
`bench/results.json` and is **forward generation** — long form in, acronym out — under a preset that
happens to be named `DICTIONARY_BACKRONYM`. It calls neither `align` nor `synthesize`. It is not this
subsystem's accuracy number, it was very nearly "corrected" into counting as one, and the accuracy
number is `backronym.<corpus>.accuracy.<subset>.exact_match_pct` and nothing else. The runner prints
that above its own table, `docs/EVALUATION.md` says it twice, and the saved entry carries it as a
field, because this is the trap the next reader walks into.

### The half that is permanently unmeetable, and why that is not a shortage of effort

`synthesize("ABC")` is asked for a phrase, given nothing but the letters. There is no answer to
compare against, and the run says so about itself:

```
python bench/run_backronym.py --examples          -- command output
  'ABC' -> 'aah baa cab'      'ACE' -> 'aah cab ear'
```

Every letter served, every word a real dictionary word, every initial correct — **and that row scores
full marks on every property this project can check.** No annotation would fix it, because the defect
is not a missing gold: an invented phrase has no correct value, only a better or worse one, and
"better" is a judgement. **This half of criterion 2 is closed as permanently unmeetable, with that as
the reason**, and the disposition is recorded here rather than left as a standing gap.

### The adjudication of the withdrawn amendment, in terms a hostile reader would accept

The amendment was authored by the workstream it excused and ratified by a recorder who wrote that the
objection to it was unanswered. It is answered now, and the answer is that it is **closure by
narrowing in its reasoning and correct in its conclusion**:

* It **conflated two operations**. One invents and one reads. Only the first is unmeetable.
* Its central word, *cannot*, was **refuted by the runner it shipped with**. `earliest_fit` and
  `latest_fit` were used to count the pairs the constraint does not settle; the pairs it does settle
  sat in the complement, unscored, and are where the accuracy number comes from.
* Its supporting figure was **adjudicated by the objective under test**. The
  14<!--claim:backronym.med1250.alignment.all.incomplete_feasible_n:,--> feasible-but-incomplete
  MED1250 pairs were re-scored with the library's own `Scorer` and reported as the objective's
  preference with 0<!--claim:backronym.med1250.alignment.all.search_shortfall_n:,--> shortfalls.
  9<!--claim:backronym.med1250.accuracy.all.returned_incomplete_n:,--> of those fourteen are pairs
  whose correct reading is unique and was not returned. Same rows, opposite verdict, and the
  difference is which arbiter was consulted.

A reader who holds that a criterion may never be closed by being made smaller is reading the previous
amendment correctly. The re-scoping above is a different move: it does not make the criterion smaller
to fit the evidence, it splits a subsystem whose two halves have different answers, publishes a number
for the half that has one, and marks the other permanently unmeetable with a reason that is a property
of the task rather than of this project's budget.

### The original verdict, and the evidence for it, which still stands

**Not met.** This is the verdict that changed at the first sweep.

`docs/ARCHITECTURE.md`'s subsystem map names five things the engine dispatches to, and the governed
package is a sixth. Serialization makes no judgement a corpus could score. The other five do:

| Subsystem | Accuracy number | Corpus role |
|---|---|---|
| `ForwardGenerator` | `generation.med1250.strict_initialism.*` | tuning, contaminated |
| `AbbreviationExtractor` | `extraction.med1250.*`, `shortform.*` | tuning; PLOD held out, on a different task |
| `LexicalDisambiguator` | `disambiguation.sdu21.*` | tuning, contaminated |
| `acronymkit.governed` | `governed_gold.sec_xbrl.*`, `governed_gold.socrata.*` | held out, measured-before-declared |
| `BackronymGenerator.align` | `backronym.{med1250,sdu21_ad}.accuracy.*` — exact match on the decidable subset | tuning, contaminated |
| `BackronymGenerator.synthesize` | **none, and none is possible** — the task has no correct answer | tuning, contaminated |

`BackronymGenerator` is not a private helper. It is a box in the architecture map, two public methods
on the facade (`generate_backronym`, `synthesize_backronym`), two CLI commands (`backronym`,
`synthesize`), a README section with worked output, and the k-best dynamic-programming alignment that
the ACRONYM formulation is cited for. It has no external evaluation of any kind.
`docs/EVALUATION.md` says this in its own words, in the section titled *What is deliberately not
claimed* — so the gap is documented, and a documented gap is still a gap. The presets are pinned
against a sixteen-phrase canonical corpus by `tools/tune_presets.py`, which is a regression guard,
not an evaluation, and the file says that too.

**What would close it.** Either a gold standard for backronym alignment — none is registered, and
none of the four routes `bench/splits.toml` discusses for extraction produces one, because a
backronym gold is a phrase, a target word and a human's judgement that the alignment is good, which
is an annotation nobody has published — or an amendment to the criterion naming the excluded
subsystem out loud. The second is cheap and honest; silently reading "every shipped subsystem" as
"every subsystem with a corpus" is the move this file exists to make expensive.

**The second route was taken, and then re-taken differently.** The amendment it produced is
withdrawn at the head of this section, and the re-scoping that replaces it is narrower in one
direction and wider in the other: `align` carries a number after all, and `synthesize` is closed as
permanently unmeetable rather than left as an open gap. The first route — a published gold — remains
the only thing that would restore the original wording for `align`, and nothing restores it for
`synthesize`.

---

## 3. Every number gated, cited by run id, re-derivable offline

**Not met — and the evidence for it got worse this round, which is the correct result.**

Nothing regressed. `tools/check_claims.py` was widened so that its coverage is explicit instead of
implicit, and the debt it revealed is now counted rather than absent (D-052). A gate that sees more is
better even when the number looks worse, and this is the criterion where that distinction has to be
held, because the reading now available is the first one this project has ever had:

```
python tools/check_claims.py --residue     -- command output, re-derivable, not a measurement
                                           -- SECOND SWEEP reading, superseded below
  numbers on the deferred ledger              316   across 11 files
  ... matching NO measurement at all           76
  numbers no arming rule reaches            1,468
  value-matched ratchet                        71   across 4 files, unmoved
```

**Third sweep: the ledger now has a rate, a policy and a classification, and the gate's advertised
scope turns out to be wider than the gate.** The residue is bucketed by
`python tools/check_claims.py --classify`, the ledger fell by adjudication and by nothing else, and
both are enforced rather than asserted — see criterion `13`. What belongs *here*, because it is a
statement about un-gated figures in user-facing prose, is the other half:

```
one prose bullet inserted at README.md line 577, then `python tools/check_claims.py`
  "Median latency for a governed expansion fell to 41 microseconds ..."   rc=0, every number backed
  "Extraction accuracy reached 99.94 % ..."   <- control, same line       rc=1, flagged
```

`README.md` and `docs/EVALUATION.md` both promise that CI fails the build when a performance claim
*anywhere in the docs or the source* cannot be traced to a run. **A latency claim in plain prose is
never armed and never seen.** The clause "zero un-gated figures in user-facing prose" is therefore
further from true than even the deferred ledger says, and the two sentences that overstate the gate's
reach are still standing, because the right wording is a judgement about how strong a promise this
project wants to make. D-059, D-060.

Two of the three coverage gaps this section named at the first sweep are closed: `CHANGELOG.md` and
`bench/splits.toml` are scanned. The third was answered by a different mechanism than the one proposed
here, and the reason is worth carrying: **widening the proximity window could never have reached the
figure that motivated it**, because that line carries no ASCII metric keyword at all. Vocabulary, not
distance. A structural rule that reads the number's own shape — a metric unit written immediately
after it — is what reaches it.

**One published figure left the gate's view this round by an author's choice, and it is booked here.**
Two bundled-resource byte counts were moved from prose into code spans so the gate would stop firing
on them (D-055). The reasoning is sound: they are properties of shipped files, no runner measures a
file size, and neither the allowlist nor a citation applies. The effect is still that two figures a
reader sees are now invisible to the check. That is the shape this criterion exists to catch, and it
now has an instance inside the same round that improved the gate. **A falling deferred count is
therefore not by itself evidence that a figure was adjudicated** — the gate cannot distinguish a
migrated claim from a fenced or code-spanned one.

### The three clauses, and where each stands

The criterion has three clauses and they are in different states.

**Cited by run id.** The migration is real and is tracked by the ratchet in `tools/check_claims.py`.
The running totals are deliberately not transcribed here — several workstreams write them in the
same round, and a transcribed total is the exact shape of figure this project keeps finding stale.
Run `python tools/check_claims.py` for the current line.

What is stable is what moved and in which direction. **README.md now carries zero value-matched
claims** and is absent from `VALUE_MATCHED_BASELINE` entirely; the file's budget went from five to
none, and the project-wide budget fell by the same five. Each of those five was migrated to a run-id
citation in the same commit as the baseline was lowered, which is what operating rule 1 requires:
the import figure, the per-call latency figure, both CMUdict syllable figures and the disambiguation
headline. Value matching cannot tell a correct claim from a number that happens to equal an
unrelated measurement, so five claims moved off a path that could not have verified them.

**Zero un-gated figures in user-facing prose.** Not met, and the reason is a property of the gate
rather than of the documents. `tools/check_claims.py` treats a number as a claim only when it sits
within 48 characters of one of eleven metric keywords. A measured figure written further from a
keyword than that is not merely un-cited — it is **invisible to the check**, counted in no total and
reported in no summary. Ten such figures were found by eye in README alone and cited this round:

```
un-gated only because the check could not see them -- all ten now cited
  generation      recall@1, recall@25, the size of the initialism bucket,
                  and the MED1250 pair count they are measured over
  extraction      the same pair count, quoted again in the extraction section
  syllables       the CMUdict exact-match figure and the size of the set
  oracle          the universal-miss share and the practical ceiling
  disambiguation  the most-frequent-expansion baseline
```

None of them had ever appeared in any count of un-backed claims, because the check had never seen
them. The one that makes the shape clearest is the syllable pair: the *within-one-syllable* figure
sat `28` characters from "mean absolute error" and was counted, while the *exact-match* figure sat
`51` characters from the same keyword, on the same line, in the same sentence, and was not. This
paragraph tripped the ratchet on its own first draft, for the same reason it describes.

Three further gaps in coverage, all structural. **Two are closed and the third is unchanged:**

* ~~`bench/splits.toml` is outside the scan globs.~~ **Closed.** It is scanned. Its two short-form
  recall ceilings both resolve against `bench/results.json` — the file was right about itself, and
  nothing had been checking, which is precisely the state value matching cannot distinguish from
  luck. Its remaining uncited figures are on the deferred ledger.
* ~~`CHANGELOG.md` is not scanned at all.~~ **Closed, and it found something.** A microsecond
  before-figure published in a release note matches no measurement in `bench/results.json` at any
  precision, and had been there the whole time.
* A citation whose *field name* contains a metric keyword arms its own line. Unchanged, and it fired
  again this round on a bundled resource whose filename contains `precision` — see the byte-count
  note above. The arming rule is lexical, not semantic, and that cuts both ways.

**Two new gaps take their place, and neither is smaller than the ones that closed.** `tools/*.py` and
`bench/*.py` are still outside the scan globs and carry substantial prose, including the claims gate's
own docstring. And `MANIFEST.in` does not ship `bench/splits.toml`, so the checker inside an sdist
scans one document fewer than the one in a checkout; `absent_targets()` now names that on every run,
so it is visible rather than silent, but the fix is in a file nobody has opened.

**Re-derivable offline from the sdist.** True in a weaker sense than the wording suggests, and the
distinction is worth keeping. `MANIFEST.in` ships `bench/results.json`, `tools/claims_allowlist.txt`
and all of `tools/`, so anyone holding an sdist can **re-verify** that every published number matches
the recorded measurement, offline, with no network. It does *not* ship `bench/run_*.py` — the comment
in `MANIFEST.in` says why: the runners need fetched corpora and optional dependencies. So the numbers
are re-checkable offline and are **not** re-derivable offline. Both are worth having; only one is
what the criterion says.

### The import claim: gated, and a re-record refused

A standing note puts `import acronymkit` at `1.8 ms` against a documented `7.71 ms` earlier figure
and reads the difference as a large, un-gated win. Both quantities are un-gated, which is why they
appear here in code spans rather than as figures. Checked rather than accepted, the framing does not
hold and the claim was already gated.

* `micro.import` **is** in `bench/results.json` and has been since D-013. `import acronymkit` is
  recorded at 2.3<!--claim:micro.import.cold_import_ms:.1f--> ms. What was missing was the citation
  in README, and that is now written.
* The `7.71 ms` figure is from the audit's question 4, measured in an eight-distribution virtual
  environment to argue against scanning entry points on the import path. It was never this
  project's import figure, and reading it as a "before" would compare two different environments.
* The gap between `1.8 ms` and the recorded figure is not a package change. Five consecutive
  medians-of-nine were taken for this sweep, and they move the wrong way to be one:

```
python bench/run_micro.py --only import   x5   -- command output, not saved
  import acronymkit               1.9  2.0  1.9  2.1  2.1 ms   recorded 2.3    DOWN, and closing
  from acronymkit import Engine   140.1 143.4 143.3 144.5 151.1 ms  recorded 128.1  UP, and rising
  import + first generate         206.3 209.0 209.0 208.8 216.9 ms  recorded 196.0  UP, and rising
```

Nothing this project did makes the shell cheaper and the engine dearer in the same measurement, so
that is the machine and not the package. The fifth sample, taken last, is the clearest: the shell
figure had drifted back to within a rounding step of the recorded one while both engine figures were
still climbing away from theirs. D-038 already measured the only recent change to the import
path — deleting the entry-point scan — and recorded it as a non-result on purpose, because the scan
was never on the import path to begin with. **`--save` was not run.** Saving would have published
drift as a win and simultaneously staled the two companion figures, which are quoted as a triple in
five places no runner regenerates: D-013's before/after table, the import-column caveat in
`docs/EVALUATION.md`, `docs/notes/pydantic-cost.md`, `CHANGELOG.md`, and the *why 30 ms* comment in
the CI `import-time` job.

`bench/run_micro.py` now prints that comparison at the moment `--save` is used, and names the five
documents, so the next person makes the same call with the numbers in front of them rather than by
remembering this paragraph. The README's tier table also gained the companion figures —
128.1<!--claim:micro.import.cold_import_engine_ms:.1f--> ms for the engine import and
196.0<!--claim:micro.import.cold_first_result_ms:.1f--> ms to first result — because quoting the
shell figure alone is the flattering comparison D-013 refused, and it had been quoted alone in the
README ever since.

---

## 4. `bench/splits.toml` parses, is loaded, is checked, is mutation-tested

**Met, and strengthened this round.** All four clauses, verified rather than assumed.

```
python tools/splits.py --check          -- command output, wrapped, not elided
                                        -- RE-RUN at the third sweep; the block
                                           this replaces was made false by the
                                           registration below and had been quoted
                                           verbatim in three places
  bench/splits.toml: 9 corpora, 3 reserved arm(s), 0 problem(s)
  note: [corpora.federal_register_rules_2024q1] role='single_annotator_reference':
        1 adjudicator(s), NEVER headline-capable for any task. It raises the
        'extraction' declared count without moving the gap, and a declared count
        read as coverage is how a filled slot comes to look like an answered
        question
  note: no uncontaminated corpus carries role='held_out' for task='extraction'
        (2 declared, 0 in that role, none eligible), so no extraction number in
        this project currently satisfies the headline rule
  note: no uncontaminated corpus carries role='held_out' for task='disambiguation'
        (1 declared, 0 in that role, none eligible), so no disambiguation number
        in this project currently satisfies the headline rule
  splits manifest OK: every corpus declares a role, a task, and a licence read
  from its terms at a recorded URL on a recorded date
```

**The extraction line went from "1 declared" to "2 declared" and gained "0 in that role" in the same
change, deliberately.** Registering an extraction corpus that can never qualify makes
"2 declared, none eligible" read as a near miss when the number of corpora in the eligible role is
zero. **A new residual of the same class arrived with the spend recorded in D-064 and is not fixed:**
the header line above the reservation list still reads `3 reserved arm(s) -- no runner may open one
without declaring a spend`, and one of the three rows it introduces is now `spent` and opens without
any declaration. `bench/corpora.py`'s `_sdu22_ae_source` docstring says both `train` arms refuse;
only one does. Neither file was any workstream's this round.

*Parses and is loaded by a tool:* `tools/splits.py` parses it into typed objects; `bench/corpora.py`
consults it when a corpus is loaded, so a reader cannot be registered for a corpus that was never
declared. *Checked in CI:* `.github/workflows/ci.yml` runs `python tools/splits.py --check` as its
own step, and the validator rejects a badge host as a `licence_url`, a missing `licence_read_on`, a
future read date, a ceiling with no basis, contamination with no reason, and a contaminated corpus
holding the headline role. *Mutation-tested:* `tests/test_splits_manifest.py` writes deliberately
broken manifests into a temporary directory and asserts the validator reports each one — a duplicate
key, an empty manifest, each required field removed in turn, an unknown role, an unknown task, a
badge URL, an unparseable date, a future date, a ceiling with no basis, a ceiling outside 0–100,
unexplained contamination, a contaminated corpus claiming `held_out`, a recall ceiling on a task
whose gold holds no short forms, and a segmentation corpus offered as backing for a pair headline.

```
python -m pytest tests/test_splits_manifest.py --collect-only     -- command output
  TestTheValidatorCatchesWhatItClaimsTo    26 mutation tests
  whole file                               57 tests
```

### The manifest now refuses a read, which is a fifth clause nobody asked for

D-043 and D-047 each reserved a corpus arm in prose, and each said in its own *how it fails* that a
reservation written into a decision record is not a mechanism. It is one now.
`[[corpora.<name>.reservations]]` is a validated structure — arm, state, deciding record, both
triggers, the near-misses written down in advance — and `Corpus.require_unreserved(arm)` raises unless
this process first declared a spend naming the record and the purpose. Two readers call it, so the
guard is live rather than available:

```
verified for this page, no reserved file opened          -- command output, abridged
  read_sdu22_ae(domain="legal", split="train")   -> SystemExit, D-047, both triggers printed
  read_sdu21_ad(split="test")                    -> SystemExit, D-043
  the dev/train arms beside them                 -> resolve unchanged
```

The value of this to criterion 4 is not the refusal, which is D-053's subject. It is that the file now
holds a kind of statement it could not hold before, and the validator refuses a malformed one — an
unrecognised key on a reservation table is an error, unlike on a corpus table where it is preserved,
because the field the structure exists to require is exactly the field a typo would silently drop.

**The residual moved, and the new one is the same class as the old.** The stale SDU-22 AE `status`
strings recorded at the first sweep have been corrected. In their place: the `socrata` entry's closing
note states that `tools/check_claims.py` does not scan `bench/splits.toml` and lists the scan globs
that exclude it. **That is now false** — the file is scanned, and the note's own reason for existing
("the alternative is a governance file whose own figures are the only unchecked ones in the
repository") has been answered. It is free-text prose that nothing validates, it went stale within a
day, and it is exactly the failure class as the three published sentences D-037 retired by hand. It is
recorded here rather than fixed because that entry was not this round's file, and it is the first
correction owed next round.

---

## 5. A non-biomedical corpus, reported with its recall ceiling

**Met with qualification** — and the qualification is not the one the standing read expected. The
ceiling really is printed in the same table as the recall figure, in two documents. What does not
follow is that the domain gap is closed.

SDU@AAAI-22 AE is registered as two corpora, both `task = "span_detection"`, both `role = "tuning"`,
both `contaminated = true`, each carrying a `shortform_recall_ceiling_pct` and a
`shortform_recall_ceiling_basis` long enough to say what the ceiling is *not*. Both are scored and
gated. D-039's table has a **SF recall ceiling** column standing beside the recall figures it
qualifies, every cell a run-id citation, and `docs/EVALUATION.md` now carries the same discipline
across six runs — both splits, all three shipped profiles — with the ceiling column in the table and
a sentence saying why it is there.

| SDU-22 AE dev (tuning, contaminated) | short-form exact recall, shipped default | short-form recall ceiling |
|---|---:|---:|
| legal | 37.76<!--claim:shortform.sdu22_ae_legal_dev.high_precision.balanced_trim.short_form.exact_recall:.2f--> | 55.15<!--claim:shortform.sdu22_ae_legal_dev.corpus.ceiling_pct:.2f--> |
| scientific | 57.84<!--claim:shortform.sdu22_ae_scientific_dev.high_precision.balanced_trim.short_form.exact_recall:.2f--> | 74.23<!--claim:shortform.sdu22_ae_scientific_dev.corpus.ceiling_pct:.2f--> |

Printing the ceiling is what stops the two recall figures being read as a domain gap: against their
own ceilings the two splits sit far closer together than their raw recalls suggest, and most of the
apparent difference is annotation density rather than extractor behaviour. Neither ceiling is a
bound — every point above one is bought by emitting a definition the corpus does not annotate, paid
for in long-form precision.

**The qualification, and one thing it is not.**

*Verified against the tree, and the location half moved during this round.* The `docs/EVALUATION.md`
section carrying the ceiling column landed in the same round as this page; before it, the only table
pairing a ceiling with a recall figure was D-039's, in the decision log — which is written for
whoever is re-litigating a decision and is not where a reader looks for the evaluation. If that
section is reverted, this verdict has to be re-read, and the README still does not name the corpus
at all.

*"Non-biomedical" is true of the genre and does not close the domain gap.* `bench/splits.toml`
records, from counts over all samples rather than from the folder name, that the split the corpus
calls "legal" is United Nations institutional and development-policy prose: six of the most basic
terms of legal practice occur in zero samples, against the United Nations occurring in a third of
them. Calling it legal-domain evidence would repeat the PLOD mistake, which the same file records
having cost three corrections. **No evidence exists for legal, financial or general-web text**, and
the README says so.

---

## 6. Two documented-but-absent extension points

**Met**, by one of each remedy — one built, one un-claimed. Verified live against the installed
package rather than read out of a decision record.

```
python -c "..."                          -- command output, re-derivable
  AcronymEngine.__init__  (self, config=None, *, backend=None, tokenizer=None,
                           extractor=None, scorer=None) -> None
  acronymkit.diagnostics.DATA_PACK_GROUP           absent
  capabilities() keys                              no 'data_packs'
  acronymkit.__all__ contains NlpBackend           True
```

The four collaborators the documentation had described for months are now real constructor
arguments — keyword-only, replacing exactly the object the engine would otherwise have built, with
no registry, no entry-point group and nothing resolved at import time (D-035). The
`acronymkit.data` entry-point group went the other way: it was declared, exported, discovered by
`capabilities()` and printed by `doctor`, and consumed by nothing, so with no loader anywhere it
could only ever report an empty list. The declaration was deleted rather than finished (D-038), and
the deletion was recorded as a breaking change to the report's key set even though the value was
always empty.

Both halves are guarded. A custom `Scorer` has a documented limit — it re-ranks what the search
retained and cannot make the search retain more — and the limit is stated in the same table as the
capability. Re-adding `data_packs` is a test failure, and the enumerated entry-point groups are
asserted to be exactly one.

---

## 7. No defect where a report claims clean while data is lost

**Met** for every known defect. The three the August 2026 audit named were re-probed through the
public API for this sweep:

```
PYTHONPATH=src python -c "..."           -- command output, re-derivable
  split_identifier_parts('value[x]')
      tokens ('value','x')                       unaccounted ('[', ']')      reported
  split_identifier_parts('[db].[schema].[TXN_ID]')
      tokens ('db','schema','TXN','ID')          unaccounted ()              correct
  normalize('E_9_1_1', {'11':'Eleven','911':'Emergency'})
      pass 1 'E_9_1_1'   pass 2 'E_9_1_1'   pass 3 'E_9_1_1'                idempotent
  Sub(GovernedDictionary).with_custom(...)
      type 'Sub', subclass state preserved                                   preserved
```

The first line is the criterion itself: a bracket that is not SQL quoting is now **reported as
unaccounted for** instead of silently dropped while `is_fully_known` said nothing was lost, and the
SQL case the rule exists for still accounts for its brackets, which is why the audit's proposed fix
was refused and a narrower one shipped (D-034). The second is the idempotence invariant, which the
digit-rejoin defect broke on a two-row ASCII catalog (D-033). The third is subclass state surviving
`with_custom`.

**One thing that looks like this defect and is not.** `audit_identifiers` reporting
`round_trip_inconsistent = 0` on a legacy schema is correct: the `corrected` bucket holds nearly
everything and the report counts what its documentation says it counts. Audit section 0 killed the
reading that it is a reporting hazard. Do not re-open it as one.

**What this verdict is worth.** "No *known* defect" is the whole claim. Three probes reproduce three
fixed defects; they say nothing about a fourth, and every one of the three was found by somebody
running the public API by hand rather than by a check.

---

## 8. The do-not list has grown

**Met.** Compared item by item against the audit's own two lists — the four under *Do not do these*
and the five under *Five proposals that should not be built*, which come to eight distinct items
once the per-candidate-evidence lever, which appears on both, is counted once. All eight are still
on the standing list, joined by the NameGuess corpus that section 0 killed. None has been withdrawn
and one has been added since.

The addition is the one worth naming: **the weighted-dictionary default blend**, killed by D-029 on
the finding that this project has no external users. That was the audit's own *if you only do one
thing* recommendation, minus the abstention half. A do-not list that only ever absorbs other
people's bad ideas is not a do-not list; this one has now killed its own strongest recommendation.

Two entries grew the list without being list items, and both are more valuable than an item:

* **D-041 closed a class rather than a rule.** `extract()` emits an atomic pair, so any filter
  keyed on the long form deletes the short form standing beside it. Measured at full strength:
  eleven of eleven deletions on the two corpora that score the two labels separately removed a
  short-form span the annotators had marked. That refuses in advance every long-form-keyed
  precision filter, including ones nobody has written, and it does so with a number a future round
  will find when it greps for the mechanism instead of for the rule.
* **D-043 gave a reservation a trigger.** SDU-21 AD `test.json` had a role and no purpose, which is
  how a budget drifts: it survived six rounds because nobody had a reason to spend it. It now has
  one named use, one trigger, and an explicit list of things that are *not* triggers — a sanity
  check, a second look at the curve, a re-run after a tokenizer change.

**Third sweep: the list grew again, by seven, and every one of them is a refusal to re-fund
something.** The second mandate's prohibited table carries: no re-funding of Federal Register legend
extraction (premise refuted at source); no further Schwartz & Hearst descendants in the proposer pool
(a `93.74 %` single-system union buys nothing from a sixth implementation of one algorithm); no
filing of the Federal Register set under `held_out` or `tuning`; no re-record of `micro.import`
against a foreign environment; no building of W11 on the unpaired-emission pitch; no growth of
`EXPECTED_NON_PASSING`; and no spending of the last unmined SDU-22 arm on anything but the legend
flag's cost. **Three of the seven exist because a premise died under measurement rather than because
anybody argued about them** — which is the strongest form an item on this list can take, and D-065
added an eighth of that kind by refusing an LLM proposer as permanent for the shipped library on the
ground that every deliverable was answered without one.

---

## 9. Every CI gate has a recorded in-situ mutation test — **new, Mandate II**

> **9. Every CI gate has a recorded in-situ mutation test, stored as an artifact.** A reader can
> point at any job in any workflow and find recorded evidence that it has actually failed, on
> purpose, in the environment where it runs, at a known date.

**Verdict: not met — and for the first time the shortfall is counted rather than absent.** R11 was
written because four defects in one round were all the same shape: a check that could not fail where
it ran. This round built the mechanism that makes the question askable and answered it in the
negative for every gate.

```
python tools/gates.py --check           -- command output, re-run for this sweep
  gate manifest: 36 gate(s) across 21 environment(s) in 5 workflow file(s)
  mutation kind: automated 13, control 2, inline 8, manual 13
  demonstrable by this harness: 13 of 36
  CARRYING IN-SITU EVIDENCE:   0 of 36   <- R11 is not satisfied for any gate here
  gate manifest OK
```

What exists: `.github/gates.toml` registering every gate with its defect class, what it detects,
what it is **blind to**, and either a mutation or a refusal with a disposition; `tools/gates.py`
validating the register against the tree rather than against itself, so a workflow scanning to zero
jobs is an error; `tools/gate_packaging_mutation.py` reintroducing five historical breakages against
a real sdist; `.github/workflows/gate-mutation.yml`; `tests/test_gate_manifest.py`; and
[`docs/GATES.md`](GATES.md), which leads with the zero rather than burying it. Ten of thirteen
automated mutations were run and demonstrated locally.

**What does not exist is the criterion.** Nothing in this round could push, dispatch a workflow or
read a run log, so no gate carries a dated red run in the environment it guards. A count printed on
every CI run makes the absence unmissable; it is not evidence. **`gate-mutation.yml` itself has
never executed** — written blind, which is the state every workflow file in this repository that has
ever been wrong was in.

**What would close it.** One push that dispatches the workflow, and one stored, dated failure per
gate. Twenty-one of the thirty-six carry no mutation at all — eight refused `inline` on a real
architectural argument (a heredoc has no command to mutate, and a harness could only mutate a copy,
which D-018 forbids), thirteen `manual`. R14 is satisfied for all twenty-one and R14 satisfied is
not R11 satisfied. Three of the eight `inline` refusals fall to one afternoon of extracting heredocs
into `tools/`. D-061.

---

## 10. An empty row filled, or the reason costed — **renumbered; this was "criterion 9, proposed"**

The eight above have one thing in common: every one of them can be closed by work inside this
repository. The deepest gap cannot, and it is not on the list — which is exactly why it has survived
being audited twice.

> **9. The two tasks the README leads with can be adjudicated by a corpus this project did not tune
> on.** `headline_capable('extraction')` and `headline_capable('disambiguation')` each return at
> least one corpus, and the flagship extraction figure and the disambiguation figure are re-measured
> against it and published with the tuning figure beside them.

**Verdict: not met.** Not partly, not in mechanism — the manifest reports the gap itself, in two
places, and the registration of *five* corpora since it was first written has not moved it. The fifth
is the one worth pausing on: an extraction corpus was registered this round and the extraction slot
below is exactly as empty as it was, **by construction rather than by luck**.

```
tools/splits.py, live probe against the real manifest -- command output
  headline_capable('extraction')               []
  headline_capable('span_detection')           ['plod', 'sdu21_ai']
  headline_capable('disambiguation')           []
  headline_capable('identifier_segmentation')  ['sec_xbrl', 'socrata']
  headline_capable()   ->  TypeError, missing 1 required positional argument: 'task'
  ROLES                                        ('tuning', 'held_out', 'single_annotator_reference')
  NEVER_HEADLINE_ROLES                         ('single_annotator_reference',)
  federal_register_rules_2024q1  role          single_annotator_reference
                                 may_back_a_headline   False
```

The flagship number and the worst number are the two with nothing behind them. Extraction F1 on
MED1250 — **84.21<!--claim:extraction.med1250.acronymkit.exact_f1:.2f--> %**, the figure the README
leads the extraction section with — is measured on a corpus whose miss taxonomy has been read in
full and against which an experiment was run and reverted. Disambiguation accuracy —
41.65<!--claim:disambiguation.sdu21.acronymkit.accuracy:.2f--> % against
72.84<!--claim:disambiguation.sdu21.most_frequent.accuracy:.2f--> % for counting words — is measured
on a split that has had an ablation, a ceiling study and an abstention sweep run against it. Both
are labelled tuning figures wherever they appear, which is honest and is not the same as being
answerable.

**What would close it, and the collision underneath.** For extraction, `bench/splits.toml` already
names the two honest routes and neither is free: score span detection on SDU/PLOD, which is a
different metric and is already done — it is why `span_detection` is the one task with a held-out
arm — or derive pairs by adjacency and label the corpus *derived pairing* in every table it appears
in, never mixed with annotator-pair corpora. For disambiguation there is exactly one instrument in
the manifest, SDU-21 AD `test.json`, and **D-043 has already spent it on paper for a different
question**. One unread split, two questions; whichever is asked first spends it, and spending it
removes this project's only possible blind arm for the task rather than using it. So criterion 9's
disambiguation half cannot be closed with any corpus currently registered. It needs a new one.

That is the item, and it should not be dressed as anything smaller. D-042 records the fork this sits
on: if the target is technical, criterion 9 is an honest gap in the evidence; if the target is an
adopted library, it is the lead item and the rest of the queue is mis-ordered.

### The extraction half now has a price on it, and the first attempt refuted its own premise

The lead item was worked this round. `tools/build_gold_corpus.py` fetches, pools, samples and freezes
an adjudicated corpus of **edges** over Federal Register final rules — the first instrument here that
produces the shape D-048 established the flagship claim needs. It ran end to end. Three findings bear
on this criterion and none of them closes it:

* **The substrate does not supply the arbiter the plan was costed on.** The Federal Register was
  chosen because its rules were said to routinely carry their own abbreviation legends. On the pinned
  draw a small minority do, and the ones that do use a syntax the shipped legend reader does not read.
  A legend row is evidence for a human, not a label.
* **The pool is one algorithm with three implementations.** Every available external extractor is a
  Schwartz & Hearst descendant, so agreement between them is not corroboration, and the sample of
  candidates *no* proposer put forward is the load-bearing step rather than a budget line.
* **The pilot cannot distinguish a nearly complete pool from one missing as much as it holds.** Its
  unproposed strata found no definitions, and the re-weighted upper bounds on those zeroes are of the
  same order as the true-edge estimate. That is the result, and every zero ships with its bound so the
  point estimate can never be read alone.

**No number was published, and the corpus is now registered at a role that cannot produce one.** The
artifact is a single-annotator reference set adjudicated by the author of the extractor that proposed
most of its pool, and it is a pilot that is not scorable in either direction. For one round
`tools/splits.py` `ROLES` could not express that, so `bench/splits.toml` recorded a refusal instead of
a table. **An honest refusal to register beat a comfortable mislabel** — filing it `held_out` is one
word, and it would have put a self-adjudicated corpus into `headline_capable('extraction')`, turning
the one honestly-empty slot on this page into a filled and dishonest one.

### The refusal was right and its permanence was never a decision

That is what changed. A refusal ships with a disposition — *fixed*, *blocked on a named decision*, or
*permanent, and here is why* — and this one had none of the three. It persisted because a three-line
tuple had not been extended, which is an unclosed ticket wearing principle's coat. `ROLES` now carries
`single_annotator_reference` and the corpus is declared under it.

**Registering it did not move this criterion, and the mechanism that guarantees so is not the
`[policy]` line.** `single_annotator_reference` is in `NEVER_HEADLINE_ROLES`: `headline_capable`
filters it out for every task unconditionally, and the validator refuses a `[policy]
headline_requires` that names it. Relying on `headline_requires` reading `held_out` would have made
the exclusion an accident of one editable line — the same one-word edit, one level up. Both guards are
mutation-tested: with the role filter deleted from `headline_capable`, `tests/test_splits_manifest.py`
goes red; with the exclusion tuple emptied, seven tests go red across two files.

What the entry buys this criterion is **a governance file that now states the weakness rather than
pointing at a git-ignored JSON file that states it**. The role requires two fields nothing else in the
manifest requires: `adjudicators` and `pooling_recipe`. So the file records that one person decided,
that the person authored the pooled extractor, and that three of the four proposers are Schwartz &
Hearst descendants — which is the reason the pool's agreement is not corroboration, written where a
reader of the manifest will find it. The entry also carries the refuted premises, in fenced blocks
labelled un-gated, because a corpus entry documenting why it is weak is worth more than one
documenting that it exists.

**And one property of that corpus was buried under the disappointment and is stronger than anything
else in this section.** Its thirty documents re-fetch cold and reproduce exactly: every pinned text
digest matches, and every one also matches an independent Government Publishing Office mirror. That
was re-run for this sweep rather than carried forward on report.

```
python tools/build_gold_corpus.py fetch --refresh --mirror-check   -- command output, abridged
  ok  2023-28849    15762 chars  mirror==
  ok  2024-02008   652096 chars  mirror==
  ... thirty documents, thirty digest comparisons, thirty mirror comparisons
  exit 0, no MISMATCH, no DIFFERS
```

Both branches of that check were demonstrated capable of failing here, by mutation: a pin digest
replaced with zeroes reports `MISMATCH` and exits non-zero, and the mirror URL pointed at a different
document reports `mirror=DIFFERS` and exits non-zero. A green from a check nobody has seen fail is not
evidence, and this one has now been seen to fail on this machine.

**None of that closes the criterion**, and it is worth being exact about why: reproducibility is a
property of the *text*, and this criterion is about *adjudication*. A corpus can be perfectly
re-derivable and still be answered by one interested party. D-056 has the conditions that would change
that, in order, none optional, and the first — a second adjudicator who authored none of the pooled
systems — is the one this project cannot meet alone.

---

---

## 11. The monoculture is measured, not assumed — **new, Mandate II**

> **11. Union gain from a proposer that is provably not a Schwartz & Hearst descendant, published,
> on a named corpus.**

**Verdict: met.** D-056 reported that this library alone is `93.74 %` of a four-way proposer union
and concluded that pooling cannot estimate a false-negative rate when every pooled system descends
from one algorithm. That was a finding about one corpus and one pool. It now has a measurement
behind it on five corpora, with a proposer built specifically to fail both of Schwartz & Hearst's
commitments.

```
bench/results.json, monoculture.* -- 103 run ids
  S&H-only edge union, share held by one implementation
    PLOD-CW all         93.55 %          SDU-22 scientific dev   93.99 %
    (D-056's Federal Register figure: 93.74 %)
  independent union gain on the full union
    PLOD-CW all         32.04 %          MED1250 (control)        0.23 %
  gold long forms no S&H descendant reaches, PLOD-CW all         42.35 %
    ... of which alignable with a gold short form in the passage 34.98 % of gold
```

Three things make this a measurement rather than a restatement. **The share reproduces off its
original substrate**, so `93.74 %` is a property of the pool and not of the corpus. **Independence
is measured on two axes and the weaker one is named as weaker** — the bracket-window axis separates
at `99.83` against a descendant maximum of `4.75`; the alignment axis does not separate cleanly,
because most real abbreviations are alignable, and the workstream discarded it as load-bearing after
building the runner around it. **And the control is the point**: on the corpus these systems were
built against, a proposer that cannot be one of them adds nothing.

**What is open is the interpretation, not the criterion.** The contrast between `32.04 %` on article
body text and `0.23 %` on abstracts is equally consistent with "abstracts contain no figure legends"
as with "the corpora were drawn around the algorithm". Separating genre from provenance needs
article body text whose gold was pooled from S&H descendants, and nobody publishes one on purpose —
**which is itself a result and is recorded as one.** D-065.

---

## 12. Short-form detection against the one-line rule — **new, Mandate II**

> **12. The shipped extractor's short-form detection is shown competitive with `predict_all_caps` on
> held-out data, or the gap is published and explained in the same table as the flagship figure.**

**Verdict: met by the first clause.** The `16.06`-point deficit that D-049 recorded is decomposed on
a `2 x 2` of the two structural handicaps and does not survive.

```
bench/results.json, shortform_contest.plod.all.* -- short-form exact F1
  region              gold spans   acronymkit HIGH_PRECISION   allcaps
  all                     2,869              52.56              68.62
  caps                    2,105              54.98              78.38
  definitional            1,323              85.73              75.13
  definitional_caps         979              88.66              86.56
```

Removing the baseline's handicap alone makes it worse; removing this library's handicap alone flips
it. **The deficit was the corpus's annotation convention measured against a pair-emitting
extractor**, not a statement about either system. The qualifier ships in the same table as the PLOD
figure it qualifies, which is criterion `5`'s discipline applied to a second table for a second
reason.

**What this does not show, stated here because the number will be quoted.** The span scorer has no
slot for the edge: replaying gold with the pairing rotated gives byte-identical `100.00` on all four
metrics, at a firing count of `1,054` wrong pairs. `85.73` is a defence of this library's short-form
*spans* and not of its extraction. Criterion `10` is untouched by this result and cannot be closed
by this route. D-066.

---

## 13. The deferred ledger has a policy and a rate — **new, Mandate II**

> **13. The deferred ledger has a written policy and a measured trajectory.**

**Verdict: met on mechanism and policy; the trajectory is one observation.**
[`docs/CLAIMS-LEDGER.md`](CLAIMS-LEDGER.md) states the policy; `tools/check_claims.py` enforces it.

```
python tools/check_claims.py            -- command output, re-run for this sweep
  value-matched ratchet:  64 of 64 budgeted across 3 file(s)
  deferred ratchet:      262 of 262 budgeted across 10 file(s)
  ledger trajectory: 2 rounds | M2-P3 X4 (first burn-down)
                     moved 54 (citation 52, deletion 2, fencing 0, other 0)
                     quota 12 per round
```

`LEDGER_TRAJECTORY`'s last row must equal the live baselines; its four movement columns must add up
to the fall it claims; and a round below `MIGRATION_QUOTA` must record a waiver. All three were
demonstrated red by mutation in this checkout. **The `fencing` column is why this is a policy rather
than a number**: D-052 established that a fenced figure leaves the gate's view entirely, so a
falling ledger is not evidence of adjudication unless the fencing column is published beside it. It
reads zero.

**Two rows, one of them the baseline, is a rate with one observation.** And the structural ceiling
is named rather than discovered later: `docs/DECISIONS.md` holds `115` of the `262` deferred numbers
and `217` of the `323` candidates for citation, and only the recorder may edit that file. **The
recorder migrated none of them this round.** D-059.

---

## 14. A second reader exists — **new, Mandate II**

> **14. A second reader exists, in some form, for anything user-facing.**

**Verdict: met, and the criterion is modest about itself.** "Exists, in some form" is satisfied by
[`docs/SECOND-READER.md`](SECOND-READER.md) — two triggers, four questions, six mechanical checks,
each check named for the live defect it caught — wired into `CONTRIBUTING.md` as a required step and
costed at one agent slot or about ninety minutes per round. **A criterion that closes because it
asks for existence rather than for enforcement should say so in its verdict, and this one does.**

The first pass found `15` defects, `6` of them material errors of fact, and its yield is the
argument for the shape of the trigger: **`7` of the `15` were in files the round's diff never
touched**, so a diff-scoped trigger alone has a measured miss of `7` in `15`. The oldest finding had
been in `docs/EVALUATION.md` since the commit that created the file, through six audits, two
adversarial passes and four documentation sweeps — a sentence whose numbers contradict the table
five lines above it, offered as "the strongest available evidence that this harness, reader and
scorer are correct".

**What would close it further.** Nothing for the literal criterion. Nothing enforces it: the
enforcing CI job is specified in one paragraph and was not built, because it belongs in files nobody
owned this round and because a gate never demonstrated failing where it runs is the shape criterion
`9` exists to refuse. Until that job exists and has been mutated red on a real push, this is a
document asking to be followed — the object this repository has learned to distrust. D-060.


---

## How this document fails

**Nine of fourteen read met, and that is the highest this page has ever read — in the round that also
measured a `20.8 %` error rate on this project's own reporting.** Put those two facts side by side,
because a hostile reader will. The defence is that four of the nine closed on criteria that are
modest about themselves: `11`, `12`, `13` and `14` ask for *measured*, *published*, *has a policy*
and *exists in some form*, not for *good*. The criteria that ask for something hard — `3`, `9` and
`10` — are all open. **A definition of done whose met-count rises when six new criteria arrive is a
definition of done scoped by the same people it grades**, and nothing here answers that.

**Two of fourteen were not re-derived at the third sweep.** Criteria `6` and `7` carry the second
sweep's verdicts. The head of this page used to say every verdict is re-derived; it no longer does,
and the table names the two.

**The renumbering breaks four cross-references on purpose, in the round that measured that class of
defect at `11.6 %`.** The note at the head lists them and three of the four are historical records
that must not be rewritten. There was no option that broke nothing.

**It is a snapshot, and nothing in CI asserts any of it.** Five verdicts print the command that
produced their evidence — 3, 4, 6, 7 and the ninth criterion — and can be re-derived by anybody. The
other four, 1, 2, 5 and 8, rest on prose and code read on one day, in one checkout, by one reader.
`tools/check_claims.py` catches a stale *number*; nothing catches a stale *sentence*, and D-037
records three published sentences that had quietly become false and were caught by hand. Every
verdict here is a candidate to become the fourth.

**Criterion 2 turns on a definition, and its amendment has already been wrong once.** "Shipped
subsystem" is my scoping, stated above: a box in the architecture map that makes a judgement a corpus
could score. A reader who scopes it to "subsystems with a registered corpus" makes it met by
construction, and that is precisely the move the verdict was warning about. The first amendment was a
*different* narrowing — narrower in the criterion rather than in the reading — and it was authored in
the same round by the workstream that benefited from it. That objection was recorded here as
unanswered; it has since been answered by measurement, the amendment is withdrawn, and the verdict is
now split. **The residual weakness is that the split rests on one reader's claim that `synthesize` has
no correct answer** — a claim about the nature of the task, which no measurement in this repository
can confirm or refute, and which is therefore exactly the kind of sentence this page says nothing
catches when it goes stale.

**Criterion 3's verdict is partly circular, in two ways now.** The evidence that figures are invisible
to the gate was originally produced by reading README by eye against `bench/results.json`, which finds
what a reader notices — so "ten invisible figures in README" was a lower bound and not a count, and
D-052 corrects the word "measured" in it besides: nine of the fifteen value-match and every one of the
nine is ambiguous. The new figures are circular differently: the residue was measured with the same
tokenizer that defines what a number is, so a different tokenizer gives a different residue, and the
deferred total is a floor on the debt under one unit vocabulary rather than a measure of it.

**Criterion 5's qualification could be read as a pass.** The literal criterion — ceiling in the same
table as the recall figure — is satisfied, and the qualification I have attached is about something
the criterion does not say: that a corpus can be non-biomedical in genre and still not close the
domain gap the README leaves open. Somebody applying the criterion strictly reaches *met*, and they
are reading it correctly. I have kept the qualification because a criterion whose whole purpose is
domain coverage is not served by a corpus whose own manifest entry says calling it legal-domain
evidence would repeat a mistake this project has already paid for — but that is a judgement about
what the criterion is *for*, and it is the one to attack.

**Verdicts were checked against a tree other people were still editing, and the second sweep is worse
for it than the first.** Criterion 5's evaluation-document evidence and criterion 3's claim counts
both moved during the session this page was first written. At the second sweep five workstreams landed
in one session; `bench/results.json`, `tools/check_claims.py`, `tools/splits.py`, `bench/splits.toml`,
`bench/corpora.py`, `README.md` and four documents all moved, the claims gate itself was rewritten
three times inside the session, and the test suite total moved with it. The commands are printed so
every number can be re-derived, but a verdict taken on a moving tree is weaker than the same verdict
taken on a commit, and a verdict taken on a tree where the *instrument* moved is weaker still.

**Criterion 7 is the weakest kind of met.** It quantifies over known defects, and its evidence is
three probes reproducing three fixes. Every one of the three original defects was found by a person
using the public API, not by a check, so the class is exactly as closed as somebody's attention.

**One correction carried in, and corrected here.** The settled statement of the abstention finding
says the crossover gate answers "under a sixth of the split". Coverage at gate `0.15` is
16.77<!--claim:disambiguation.sdu21.abstention_curve.gate_0.15_coverage_pct:.2f--> %, which is
marginally *over* a sixth. The fraction is the wrong instrument at that precision and the cited
figure is used above instead. The direction of the slip flatters the criticism rather than the
library, which is why it survived being quoted.

**The import decision was a judgement and it is reversible.** Refusing the re-record rests on
reading a downward move in one figure and upward moves in two others as machine drift. That is a
strong reading and not a proof: it would be settled properly by an A/B on one machine across the
commit in question, which is what D-038 did for the entry-point scan and what nobody has done for
the recorded figure as a whole. If the three are ever re-recorded together with a change that
explains all three, this paragraph is what should be cited against the version of the story where
the import cost fell on its own.
