# Definition of done — the eight criteria, swept

Eight criteria have governed what "finished" means for this library. They have been carried in
mandates and answered one at a time in `docs/DECISIONS.md`; they have never been read together, and
a list nobody reads as a list is how a verdict that was true when it was written goes on being
repeated after it stops being true. This page reads them together, states a verdict on each, names
the evidence, and says what would close the ones that are open.

**Nothing here is asserted on the strength of a previous round's answer.** Every verdict below was
re-derived on 2026-08-24 by running the check or reading the code, including the five that were
expected to come back met. Two came back differently from the standing read, and one of those is the
flagship criterion.

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
| 2 | Every shipped subsystem carries an accuracy number | **not met** | Four of five scored; backronym synthesis and alignment has none, and `docs/EVALUATION.md` says so itself | A gold standard for backronym alignment — or scope the criterion to the four and say which one it excludes |
| 3 | Every number gated, cited by run id, re-derivable offline from the sdist; **zero un-gated figures in user-facing prose** | **not met** — materially advanced this round | `tools/check_claims.py`; README now carries zero value-matched claims; the gate is keyword-armed and cannot see every number | Migrate the remaining value-matched claims; widen the scan to `bench/splits.toml` and `CHANGELOG.md`; replace keyword proximity with a rule that cannot miss |
| 4 | `bench/splits.toml` parses, is loaded by a tool, checked in CI for role/task/licence, mutation-tested | **met** | `tools/splits.py --check` in CI; `bench/corpora.py` consults it at load; a mutation-test class in `tests/test_splits_manifest.py` | Nothing. One stale `status` string is noted below and is not load-bearing |
| 5 | At least one non-biomedical annotated corpus registered and reported, **with its short-form recall ceiling in the same table as its recall figure** | **met with qualification** | SDU@AAAI-22 AE registered, scored, gated; ceiling column present beside the recall figures in D-039 and, as of this round, in `docs/EVALUATION.md` | Nothing for the literal criterion. The corpus is a different *genre*, not a different domain, so the domain-generalisation gap is a separate item and stays open |
| 6 | Two documented-but-absent extension points exist, or the documentation stops claiming them | **met** | Four injectable collaborators ship (D-035); the `acronymkit.data` entry-point group is deleted (D-038) | Nothing. The standing risk is re-declaring a pack group before a pack exists to load |
| 7 | No known defect where a report claims clean while data is lost | **met** | All three governed defects re-probed live through the public API and all three are fixed | Nothing for the known set. "Known" is the whole content of the claim |
| 8 | The do-not list has grown, not shrunk | **met** | Nine audit-derived items carried forward unchanged, one added since, plus a class-level closure and a reservation discipline | Nothing |

**Two verdicts differ from the standing read.** Criterion 2 was carried as met and is not: the
backronym subsystem ships in the public API, in the CLI and in the architecture map, and has no
accuracy number anywhere. Criterion 5 was carried as needing confirmation, and it confirms — the
ceiling really is printed in the same table as the recall figures — but the thing that remains open
underneath it is not the ceiling, it is that the corpus is a different *genre* and not a different
*domain*, which `bench/splits.toml` establishes by counting rather than by asserting.

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

## 2. Every shipped subsystem carries an accuracy number

**Not met.** This is the verdict that changed.

`docs/ARCHITECTURE.md`'s subsystem map names five things the engine dispatches to, and the governed
package is a sixth. Serialization makes no judgement a corpus could score. The other five do:

| Subsystem | Accuracy number | Corpus role |
|---|---|---|
| `ForwardGenerator` | `generation.med1250.strict_initialism.*` | tuning, contaminated |
| `AbbreviationExtractor` | `extraction.med1250.*`, `shortform.*` | tuning; PLOD held out, on a different task |
| `LexicalDisambiguator` | `disambiguation.sdu21.*` | tuning, contaminated |
| `acronymkit.governed` | `governed_gold.sec_xbrl.*`, `governed_gold.socrata.*` | held out, measured-before-declared |
| `BackronymGenerator` | **none** | — |

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

---

## 3. Every number gated, cited by run id, re-derivable offline

**Not met, and materially advanced this round.** The criterion has three clauses and they are in
different states.

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

Three further gaps in coverage, all structural:

* `bench/splits.toml` is outside the scan globs. The file's own closing note says so. Both
  short-form recall ceilings live there and are named by run id but not gated.
* `CHANGELOG.md` is not scanned at all, and it quotes measured figures.
* A citation whose *field name* contains a metric keyword arms its own line. `oracle_union_recall`
  in a comment made a rhetorical round number on the same line into a claim, which surfaced during
  this round's migration. The interaction is harmless here and is a reminder that the arming rule is
  lexical, not semantic.

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

**Met.** All four clauses, verified rather than assumed.

```
python tools/splits.py --check          -- command output, wrapped, not elided
  bench/splits.toml: 8 corpora, 0 problem(s)
  note: no uncontaminated corpus carries role='held_out' for task='extraction'
        (1 declared, none eligible), so no extraction number in this project
        currently satisfies the headline rule
  note: no uncontaminated corpus carries role='held_out' for task='disambiguation'
        (1 declared, none eligible), so no disambiguation number in this project
        currently satisfies the headline rule
  splits manifest OK: every corpus declares a role, a task, and a licence read
  from its terms at a recorded URL on a recorded date
```

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

**One residual, not load-bearing.** Both SDU-22 AE entries carry
`status = "registered; reader in bench/corpora.py; not yet scored through a runner"`. They have been
scored — `shortform.sdu22_ae_legal_dev.*` and `shortform.sdu22_ae_scientific_dev.*` are gated runs —
so the string is stale. `status` is free text that nothing validates, which is why it went stale
quietly, and it is the same failure class as the three published sentences D-037 retired by hand.

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

---

## Criterion 9, proposed, and not met

The eight above have one thing in common: every one of them can be closed by work inside this
repository. The deepest gap cannot, and it is not on the list — which is exactly why it has survived
being audited twice.

> **9. The two tasks the README leads with can be adjudicated by a corpus this project did not tune
> on.** `headline_capable('extraction')` and `headline_capable('disambiguation')` each return at
> least one corpus, and the flagship extraction figure and the disambiguation figure are re-measured
> against it and published with the tuning figure beside them.

**Verdict: not met.** Not partly, not in mechanism — the manifest reports the gap itself, in two
places, and the registration of four corpora since it was first written has not moved it.

```
tools/splits.py, live probe against the real manifest -- command output
  headline_capable('extraction')               []
  headline_capable('span_detection')           ['plod', 'sdu21_ai']
  headline_capable('disambiguation')           []
  headline_capable('identifier_segmentation')  ['sec_xbrl', 'socrata']
  headline_capable()   ->  TypeError, missing 1 required positional argument: 'task'
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

---

## How this document fails

**It is a snapshot, and nothing in CI asserts any of it.** Five verdicts print the command that
produced their evidence — 3, 4, 6, 7 and the ninth criterion — and can be re-derived by anybody. The
other four, 1, 2, 5 and 8, rest on prose and code read on one day, in one checkout, by one reader.
`tools/check_claims.py` catches a stale *number*; nothing catches a stale *sentence*, and D-037
records three published sentences that had quietly become false and were caught by hand. Every
verdict here is a candidate to become the fourth.

**Criterion 2 turns on a definition.** "Shipped subsystem" is my scoping, stated above: a box in the
architecture map that makes a judgement a corpus could score. A reader who scopes it to "subsystems
with a registered corpus" makes it met by construction, and that is precisely the move the verdict
is warning about — so the disagreement is real and should be argued in a decision record, not
resolved by whichever reading is written down first.

**Criterion 3's verdict is partly circular.** The evidence that figures are invisible to the gate
was produced by reading README by eye against `bench/results.json`. That method finds what a reader
notices, so "ten invisible figures in README" is a lower bound and not a count. The other documents
were not swept the same way, and on the arithmetic above they are where the rest of them are.

**Criterion 5's qualification could be read as a pass.** The literal criterion — ceiling in the same
table as the recall figure — is satisfied, and the qualification I have attached is about something
the criterion does not say: that a corpus can be non-biomedical in genre and still not close the
domain gap the README leaves open. Somebody applying the criterion strictly reaches *met*, and they
are reading it correctly. I have kept the qualification because a criterion whose whole purpose is
domain coverage is not served by a corpus whose own manifest entry says calling it legal-domain
evidence would repeat a mistake this project has already paid for — but that is a judgement about
what the criterion is *for*, and it is the one to attack.

**Two of the eight verdicts were checked against a tree other people were still editing.** Criterion
5's evaluation-document evidence and criterion 3's claim counts both moved during the session this
page was written, because concurrent work landed in `docs/EVALUATION.md` and `bench/results.json`.
The commands are printed so the numbers can be re-derived, but a verdict taken on a moving tree is
weaker than the same verdict taken on a commit, and this page does not pretend otherwise.

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
