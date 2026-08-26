# Definition of done — the twenty criteria, swept

Eight criteria governed what "finished" means for this library, a second mandate added six
more, and a third mandate added six more again. **The met-count did not rise with them, and the
proportion fell**: `11` of `20` at the sixth sweep against `10` of `14` at the fifth, which is the
first time this page's own answer to *"a definition of done whose met-count rises when new criteria
arrive is scoped by the same people it grades"* has been a number rather than a defence. They have been carried in mandates and answered one at a time in `docs/DECISIONS.md`; they had
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

**How much of this page was re-derived, sweep by sweep, because the answer got worse.** The first
two sweeps ran on 2026-08-24 and re-derived every verdict by running the check or reading the code.
The third, across 2026-08-24 and 2026-08-25, re-derived twelve of fourteen and carried `6` and `7`.
The fourth sweep re-derived seven of fourteen and carried seven. **The fifth sweep re-derived nine of
fourteen — `3`, `4`, `8`, `9`, `10`, `11`, `12`, `13` and `14` — and carried `1`, `2`, `5`, `6` and
`7` from an earlier sweep.** **The sixth sweep re-derived eleven of twenty — `3`, `4`, `9`, `13`,
`14` and all six of the new `15` to `20`, each by running the command in its own row — and carried
nine: `1`, `2`, `5`, `6`, `7`, `8`, `10`, `11` and `12`.** Nine of twenty still rest on an answer
somebody else gave on an earlier tree, and five of those nine (`1`, `2`, `5`, `6`, `7`) have now
been carried for four sweeps running. The table says so per row, in the verdict column, because a page whose whole purpose is to stop
a stale verdict being repeated is the last page that gets to be vague about which of its verdicts are
stale. D-073, D-083.

**`2026-08-26` — THIS IS A CORRECTION PASS AND NOT A SEVENTH SWEEP. Read it as strictly weaker than
a sweep.** No verdict was re-derived and no criterion was re-adjudicated. What happened is that a
cold read found three of this page's cells false or stale and the recorder corrected them in place
along with three cells its own round moved: criterion `3`'s trajectory (two rounds stale, in the row
whose whole subject is stale figures), criterion `9`'s evidence cell (contradicting the verdict cell
beside it for a round, after D-090 recorded amending exactly that figure), the *"nothing else
appears"* sentence in **How to read the numbers** (false, and the reason the first two went stale
invisibly), and then criteria `13`, `14` and `16` for what this round's own records establish.
**Every other row on this page carries the sweep number it last carried**, and nine of twenty still
rest on an answer somebody else gave on an earlier tree. **A page that gets corrected in the gaps
between sweeps and reports its met-count as though it had been swept is doing the thing it grades
others for**, so the count above is the sixth sweep's count and is labelled as such.

**No verdict moved at the fourth sweep, and two evidence cells were wrong.** Criterion `11`'s cell
was comparing a proposals-side figure against a gold-side one and therefore contradicted its own
section five hundred lines below; criterion `13`'s cell had been falsified by the very trajectory it
describes. Both are corrected below, both were inside code spans the whole time they stood, and both
were found by reading this page against `bench/results.json` rather than by any check.

**No verdict moved at the fifth sweep either, no criterion closed, and therefore none closed by
narrowing. One cell was an outright falsehood.** Criterion `3` said two sentences overstating the
claims gate's reach were "still standing"; both had been corrected in the **same commit** that wrote
that down, and it then survived a cold read covering one of the two files. Two criteria moved a long
way inside an unchanged verdict — `9` from `0` to `13` of `36`, and `11`'s open item halved when the
genre half of its confound was measured — and two sentences on this page asserting that genre and
provenance cannot be separated were stale in the round that separated one of them. D-083.

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
figure. ~~Nothing else appears.~~

**CORRECTED `2026-08-26`: a third category appears, it is the largest of the three, and it is the
reason two cells of this table went stale invisibly.** The fourth cold read counted the
**code-spanned bare numerics outside any fence** on this page — figures with no command above them
and no run id beside them — against the citations. Re-derived here rather than carried:

```
python -- fenced blocks stripped, then inline code spans matched against a bare-numeric
pattern; rendered citations counted as occurrences of "<!--claim:". Command output, not a
benchmark measurement. Re-run this before quoting either figure; both move on any edit.
  inline code spans on this page          721
    of them, a bare numeric and nothing else   291
  rendered run-id citations                 53
```

`tools/check_claims.py` masks an inline code span exactly as it masks a fence, so
every one of them is invisible to the gate. That is how criterion `9`'s evidence cell went on saying
`13 of 36` for a round after the verdict cell beside it said `12`, and how criterion `3`'s
trajectory went two rounds stale. **The sentence "nothing else appears" was the strongest claim on
this page and it was false**; what replaces it is the disclosure that this page's own numbers are
mostly ungated by construction, which is uncomfortable on a page whose criterion `3` is about
exactly that.

---

## The table

| # | Criterion | Verdict | Evidence | What would close it |
|---|---|---|---|---|
| 1 | The disambiguator can say "I don't know" — abstention exposed, curve published decomposed, **policy confirmed on held-out data** | **met with qualification** — mechanism and publication, not value; **carried, NOT re-derived at the fourth sweep** | `min_margin`, `margin`, `abstained` ship; `disambiguation.sdu21.abstention_curve`; `docs/EVALUATION.md` | An on-by-default `min_margin` proposal with a threshold and a cost model, then D-043's single spend of SDU-21 AD `test.json` |
| 2 | Every shipped subsystem carries an accuracy number — **RE-SCOPED, see below; the previous amendment is withdrawn** | **partly met** — `align` now carries an accuracy number over about half of each corpus; `synthesize` carries none and is **permanently unmeetable**; **carried, NOT re-derived at the fourth sweep** | `backronym.{med1250,sdu21_ad}.accuracy` and `.{alignment,synthesis}`; `docs/EVALUATION.md`; D-054 as corrected | For `align`, a gold that reaches the undecidable pairs. For `synthesize`, **nothing** — the task has no correct answer for any gold to record |
| 3 | Every number gated, cited by run id, re-derivable offline from the sdist; **zero un-gated figures in user-facing prose** | **not met — and the evidence got worse, correctly**; ~~re-derived at the fifth sweep~~ **CORRECTED `2026-08-26`: the sixth sweep re-derived this row too and did not update its evidence cell, which is why the cell below was two rounds stale** | `tools/check_claims.py --residue` now counts a deferred ledger and an unexamined residue that no earlier run had ever reported; two of the three named coverage gaps are closed; ~~the ledger has fallen `316` to `262` to `231` to `213` to `201` across five recorded rounds~~ — **live at the seventh round: `316` to `262` to `231` to `213` to `201` to `189` to `189`, the last of those a waiver rather than a payment (D-097)** | Migrate the deferred ledger, lowering the baseline in the same commit; widen the scan to `tools/` and `bench/`; widen the unit vocabulary — each one its own measurement |
| 4 | `bench/splits.toml` parses, is loaded by a tool, checked in CI for role/task/licence, mutation-tested | **met, and strengthened** | `tools/splits.py --check` in CI, now reporting reserved arms; `Corpus.require_unreserved` refuses a read; mutation-test class in `tests/test_splits_manifest.py` | Nothing. The stale `status` residual is fixed; a new residual of the same class is named below |
| 5 | At least one non-biomedical annotated corpus registered and reported, **with its short-form recall ceiling in the same table as its recall figure** | **met with qualification** — carried, NOT re-derived at the fourth sweep | SDU@AAAI-22 AE registered, scored, gated; ceiling column present beside the recall figures in D-039 and, as of this round, in `docs/EVALUATION.md` | Nothing for the literal criterion. The corpus is a different *genre*, not a different domain, so the domain-generalisation gap is a separate item and stays open |
| 6 | Two documented-but-absent extension points exist, or the documentation stops claiming them | **met — carried, NOT re-derived at the third or fourth sweep** | Four injectable collaborators ship (D-035); the `acronymkit.data` entry-point group is deleted (D-038) | Nothing. The standing risk is re-declaring a pack group before a pack exists to load |
| 7 | No known defect where a report claims clean while data is lost | **met — carried, NOT re-derived at the third or fourth sweep** | All three governed defects re-probed live through the public API and all three are fixed | Nothing for the known set. "Known" is the whole content of the claim |
| 8 | The do-not list has grown, not shrunk | **met — and for the first time the list has a measured error rate rather than an assumed one**; re-derived at the fifth sweep | Nine audit-derived items carried forward unchanged, one added since, plus a class-level closure and a reservation discipline; `docs/AUDIT-PROHIBITIONS-2026-08.md` audits `55` prohibitions across three strata at seed `20260825`: **nothing lifted**, `13` of the do-not list's `35` figures not true today or unreproducible, two prohibitions stronger than written; D-077 | Nothing for the literal criterion. Nine stated *reasons* need correcting, which is a different outcome from lifting one, and the decision on each is the maintainer's |
| 9 | **NEW (Mandate II).** Every CI gate has a recorded in-situ mutation test, stored as an artifact | **not met — and at the sixth sweep the count moved DOWN, `13` of `36` to `12` of `36`, the first fall this page has recorded**; re-derived at the fifth and sixth sweeps | `.github/gates.toml`, `tools/gates.py --check`, `docs/GATES.md`; D-061, D-079. The register now prints ~~`CARRYING IN-SITU EVIDENCE: 13 of 36`~~ **`CARRYING IN-SITU EVIDENCE: 12 of 36`, corrected `2026-08-26` — D-090 recorded amending this row's `13 of 36` and amended the verdict cell only, leaving this cell contradicting the verdict beside it for a round**, a `cost_rank` on every gate with the top `3` demonstrated, and a per-round quota stated as a **ceiling on the debt** so that adding gates cannot dilute the count | A push per remaining gate. The thirteen are **every gate this harness could ever mutate**; the other `23` are `8` inline, `13` manual and `2` control refusals. Three of the eight inline refusals fall to one afternoon of extracting heredocs into `tools/`. **That afternoon happened and the costing was wrong about one of the three**: `inline` is now `5`, automated `16`, debt `24` at a ceiling of `24`, `4` gates owed forward, and one gate's evidence withdrawn because its recorded verdict was reachable with the declared defect uncaught. D-087 |
| 10 | **RENUMBERED — this was "criterion 9, proposed".** The two tasks the README leads with can be adjudicated by a corpus this project did not tune on; or the reason it cannot is a permanent property of the task, with the filling instrument costed | **not met — the row is empty by construction, the price is now known, and it did NOT close by writing the row off** | `headline_capable('extraction')` and `('disambiguation')` both empty, re-probed live at the fourth sweep; `tools/splits.py --check` prints both gaps; D-056's five promotion conditions; D-063; the costing is now published where a user meets it, in `README.md`'s honest scope and `docs/POSITIONING.md` (D-070) | D-056's five conditions in order, the first being a second adjudicator who authored none of the pooled systems. The reason is a **resource** limit, not a property of the task, so the second clause does not apply |
| 11 | **NEW (Mandate II).** The monoculture is measured, not assumed — union gain from a non-Schwartz-&-Hearst proposer, published, on a named corpus | **met; and the open item in the *interpretation* halved at the fifth sweep** | `monoculture.*` (`103` run ids); `shapecue`, independence measured on two axes; PLOD-CW, `held_out`, uncontaminated; independent union gain `32.04 %` on PLOD-CW against the denominator-comparable MED1250 control `0.23 %` — both `proposals.edges.independent_gain_pct`, corrected at the fourth sweep from a `0.00 %` that is the *gold/pairs* control and belongs beside the gold-reach figures instead; full pairwise matrix in `docs/EVALUATION.md`; D-065 | Nothing for the literal criterion. **The genre half of the confound is now measured** on `1,839` same-article PMC pairs, six ways, all six intervals excluding zero, and it points away from provenance (`genre.pmc_oa.*`, D-075). What is open is the **provenance** half alone, and that still needs a corpus nobody publishes |
| 12 | **NEW (Mandate II).** The shipped extractor's short-form detection is shown competitive with `predict_all_caps` on held-out data, or the gap is published and explained in the same table as the flagship figure | **met by the first clause**; re-derived at the fifth sweep, and the second clause is now satisfied on `README.md` too, which carried no PLOD span figure at all | `shortform_contest.plod.*` (`14` run ids); on comparable gold the ordering reverses by `10.60` points pooled and `14.86` on test; the qualifier column is in the PLOD table; **the annotation convention is now priced at `26.66` points on its own, and `18.16` is the *net* of that against a `-8.50` admission-rule effect** (`shortform_contest.plod.*.convention`); D-066, D-076 | Nothing for the literal criterion. What it does **not** show is extraction quality: the span scorer cannot tell correct pairing from random pairing, demonstrated at `1,054` wrong pairs |
| 13 | **NEW (Mandate II).** The deferred ledger has a written policy and a measured trajectory | **met — four observations now, still falling, and the waiver the previous round predicted did not arrive**; re-derived at the fifth sweep | `docs/CLAIMS-LEDGER.md`; `LEDGER_TRAJECTORY`, `MIGRATION_QUOTA = 12`, `RECORD_FILE_FLOOR = 12`, `RECORD_FILE_PIN` and `trajectory_problems()` in `tools/check_claims.py`, mutation-tested red; D-059, D-071 | Nothing for the literal criterion. Four migrations of `54`, `31`, `18` and `12` are a rate and it is decelerating. `docs/DECISIONS.md` is down from `115` to `54` and the recorder is bound by a per-file floor. **The forecast that the `66` remaining held no citable measurement was wrong**: the walk found `3` citations and `9` deletions and paid the floor exactly, because *blocked* had again been a per-record verdict applied per number. `54` remain and the *next* round owes a waiver naming three mechanisms; D-084. **At the sixth sweep the predicted waiver did not arrive for a second consecutive round**: `12` more came out by `3` citations and `9` deletions, `54` → `42`, and *blocked* had again been a per-record verdict applied per number — this time for a reason that can never be discharged. D-091. **At the seventh round the waiver finally arrived, and it is the first this project has written.** `0` migrated, `42` remaining, and the reason is a measurement rather than an opinion: all `42` were resolved against every field in `bench/results.json` and `26` match nothing anywhere while the other `16` match only unrelated quantities in unrelated units. Deletion was walked and refused three times with reasons. **Read the row as a waiver at the end of a burn-down and not one taken to avoid one — the probe is the only thing separating those two objects, and the next round owes the same probe.** D-097 |
| 14 | **NEW (Mandate II).** A second reader exists, in some form, for anything user-facing | **met, and the criterion is less modest and more exposed than it was**; re-derived at the fifth sweep | `docs/SECOND-READER.md` — two triggers, six checks, costed at one agent slot; wired into `CONTRIBUTING.md`; first pass found `15` defects, `6` material, `7` of `15` in files the round never touched; a second pass has now run **as policy**, shipped six fixes, carried the rotation cursor in §8 and found three defects in the policy itself; the trigger is now executable code with a test, the hand-off is a validated ledger, and `disposition = "fixed"` requires a second name; D-060, D-072, D-081 | Nothing for the literal criterion. Nothing enforces it: the enforcing CI job is specified in one paragraph and not built. **And the third read wrote no ledger row**, because the read-only instruction and the ledger requirement could not both be obeyed — so the cursor did not advance and the next reader serves the file the third reader just served. **At the sixth sweep the two-round survival of a retired sentence in `src/acronymkit/__init__.py` acquired a mechanical answer rather than an attribution**: `PATHSPEC` has `6` entries with none under `src/`, `user_facing_files()` returns `21` paths with `0` under `src/`, and in situ the trigger returns four files and not the source file the round had just changed. D-089. **A fourth read has now run and written no ledger row either — the second consecutive time**, so the cursor has not advanced for two reads, the rotation served the same file twice, and `11` new findings live only in a note that no rule in the policy reaches. `python tools/second_reader.py --check` is green throughout, **and it is green precisely because no row was written**: the gate cannot tell *no cold read happened* from *a cold read happened and could not record it*. The blocking decision is one sentence nobody has taken — whether the read-only boundary is prose or filesystem — and §5.1 says in terms that it is not a filesystem permission. D-096 |
| 15 | **NEW (Mandate III).** No figure ships in a document unless a committed script regenerates it from `bench/results.json` and CI diffs it (R16) | **not met, not started — and there is no live instance to be not-started about** | `find . \( -name '*.svg' -o -name '*.png' -o -name '*.jpg' -o -name '*.gif' \)` outside `.git/` and `build/` returns `0` files. No figure of any kind ships in this repository, so no unchecked figure exists and no regenerating script does either | A script, a CI diff step and a registered gate — written *before* the first figure, because the rule exists so that the first one cannot ship unchecked. Nothing is owed until somebody wants a chart |
| 16 | **NEW (Mandate III).** The forward generator's round trip is measured as a verifier of extractor output, with a go/no-go recorded | **met as a measurement, and the answer is no** — re-derived by the recorder from a fresh run of the runner | `roundtrip.{med1250,pmc_oa}.*`, `19` run ids; `bench/run_roundtrip_verifier.py`, `24` tests; the go/no-go and its dependants in D-085. Unpruned recall is 42.09<!--claim:roundtrip.med1250.recall.beam_control_never_cuts.recall_pct:.2f--> % and 51.75<!--claim:roundtrip.pmc_oa.recall.beam_control_never_cuts.recall_pct:.2f--> %, against an aligner that accepts 85.70<!--claim:roundtrip.med1250.ceiling.aligner_accepts_pct:.2f--> % of the same pairs | Nothing for the literal criterion. What is **not** met is gating: the runner is in no CI job and `.github/gates.toml` does not know it exists, so nothing re-derives these figures but a person. **And one half of the go/no-go's dependants was recorded on evidence that did not exist**: D-085 stopped `A2` for two reasons and named the second an absence, when the deciding workstream had already saved `18` run ids into `bench/results.json`. That sentence is retired in place at D-085; the measurement is D-092; **`A5` widens candidate generation and `A2` does not, so A1's NO-GO binds `A5` tightly and binds `A2` only by the letter of a rule whose reason does not reach it.** The decision on `A2` is the maintainer's |
| `17` | **NEW (Mandate III).** A gated throughput baseline for the governed hot path, published in machine-independent counts with wall-clock unarmed (R17, R18) | **partly met** — one entry point, two real corpora, and the counts re-derived by the recorder | `governed_perf.*`, `10` run ids; `bench/run_governed_perf.py`, `28` tests; `docs/EVALUATION.md`. Tokenizer passes, catalog lookups split by origin, both memo hit rates, provenance records, `_prepare` calls and total Python calls are all gated; wall-clock is fenced with the machine named and never armed | The other three entry points. This decomposes `expand_identifier` alone — `is_compliant` and `to_physical_name` have none, `extract`, `disambiguate` and generation have none, and **memory is not measured at all** |
| 18 | **NEW (Mandate III).** Every optimisation is proven behaviour-identical byte for byte, forced on and forced off, over the full corpus, by a gate (R19) | **not met, not started** — and no obligation arose, because nothing was optimised | No byte-identity gate exists in `.github/gates.toml`. The one place R19 was applied is to an *instrument*: `bench/run_governed_perf.py`'s ablation stages are proven byte-identical to the shipped path over `421,199` calls per pass with `0` mismatches and three positive controls | The first optimisation, and the gate shipped in the same commit. A rule with no instances is a rule with no evidence that it can fire |
| 19 | **NEW (Mandate III).** W11 — whether `extract()` may emit a short form with an absent or low-confidence long form — is decided | **not met, not started** | [`docs/notes/w11-emission-model.md`](notes/w11-emission-model.md) opens *"Status: scoping note. No decision, no behaviour change, nothing shipped."* It scopes the question, costs it and gives it a failure mode. Nothing in this phase touched it | A product decision, taken out loud in a record. It bears on criterion `10`: answering it *yes* is the only route by which a span corpus could adjudicate the flagship claim |
| 20 | **NEW (Mandate III).** The catalog-gap report is shipped **and has been run by a stranger** | **half met, and the half that matters is not** | [`docs/SOURCING.md`](SOURCING.md) ships with an owner, three dated actions, a `2026-11-23` expiry and a stranger-runnable kit. Its own log reads **approaches made: `0`** | One organisation saying yes. This is `U-0` with a delivery date attached, and it is the same people problem — no amount of work inside this repository moves it |

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
not and was measured at `0 of 36` — it reads `13 of 36` from the fifth sweep on — and `10` does not
and is now costed.** D-059 to D-069.

**Fourth sweep, after the positioning decision, the recorder's own binding and a cold read run as
policy. No verdict moved.** That is the least interesting thing in it. What the sweep is for is what
it found while not moving anything: criterion `11`'s evidence cell had been comparing two different
denominators and contradicting its own section; criterion `13`'s cell had been falsified inside one
round by the trajectory it describes; and criterion `10` was checked specifically for whether it had
closed **by writing the empty row off rather than filling it**, and it had not — the live probe below
still returns two empty slots, and the criterion's escape clause is still shut because the blocker is
a resource limit rather than a property of the task. **Seven of fourteen verdicts were re-derived and
seven were carried**, which is worse than the third sweep and is stated at the head rather than
inferred from the table. D-070 to D-073.

**Fifth sweep, after the round that answered the positioning's central question in the negative and
then showed the question had been misread. No verdict moved, no criterion closed, and therefore none
closed by narrowing.** Nine of fourteen were re-derived, which is the first time this number has gone
up. What the sweep found: **criterion `3` was carrying an outright falsehood** — it said two sentences
overstating the claims gate's reach were "still standing" when both had been corrected in the same
commit that wrote that cell, and it then survived a cold read covering one of the two files. Criterion
`9` moved from `0` to `13` of `36` **without a single new demonstration being taken**, by reading a CI
run that had been sitting unread while the register asserted that workflow had never executed.
Criterion `11`'s open item halved when the genre half of its confound was measured — and two sentences
on this page asserting that genre and provenance cannot be separated were stale in the same round that
separated one of them. Criterion `13`'s predicted waiver did not arrive. Criterion `4`'s fenced
transcript had gone stale in the direction it exists to warn about: a declared count rose again
without the gap moving. D-074 to D-084.

**Sixth sweep, after the phase that measured what Mandate III's architecture rests on. Six criteria
are added, `15` to `20`, and five of the six read *not met*.** No verdict among the original fourteen
moved. Criterion `9`'s count went **down** — `13` of `36` to `12` of `36`, the first fall this page
has recorded, because a gate's in-situ evidence was re-checked and **withdrawn** (D-087). Criterion
`13`'s waiver did not arrive for a second consecutive round (D-091). Criterion `14` acquired a
mechanical answer to the question it had only had an attribution for: **no second-reader trigger can
reach a source file at all** (D-089). **Four of the six new criteria are recorded at *not started*
rather than omitted**, and one of those four — `15` — is recorded with the fact that this tree
contains **zero** figures of any kind, so the rule it states has nothing to bind. A criterion list
that only lists what is in progress hides the distance. D-085 to D-091.


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

`README.md` and `docs/EVALUATION.md` **used to** promise that CI fails the build when a performance
claim *anywhere in the docs or the source* cannot be traced to a run. **A latency claim in plain prose
is never armed and never seen**, so both sentences were false — and **both were corrected at
`3173126`** to say *a performance claim that the gate can recognise*.

**This page then said they were "still standing" for a whole round, in a cell written in the same
commit that fixed them**, and that survived a cold read which covered `README.md`. Re-derived at the
fifth sweep:

```
git log --oneline -S "that the gate can recognise" -- README.md docs/EVALUATION.md   -> 3173126
git log --oneline -S "still standing, because the right wording" \
                     -- docs/DEFINITION-OF-DONE.md                                   -> 3173126
grep -rn "anywhere in the docs" README.md docs/EVALUATION.md                          -> no match
```

Two workstreams in one round: one corrected the sentences, the other wrote down that they were
unfixed. What **is** still open is the clause "zero un-gated figures in user-facing prose", which
remains further from true than even the deferred ledger says, and the widening that would close the
latency half is measured, priced at zero and refused with a disposition. D-059, D-060, D-079, D-083.

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
  note: [corpora.pmc_oa_same_article_genre] role='single_annotator_reference':
        2 adjudicator(s), NEVER headline-capable for any task. It raises the
        'extraction' declared count without moving the gap
  note: no uncontaminated corpus carries role='held_out' for task='extraction'
        (3 declared, 0 in that role, none eligible), so no extraction number in
        this project currently satisfies the headline rule
  note: no uncontaminated corpus carries role='held_out' for task='disambiguation'
        (1 declared, 0 in that role, none eligible), so no disambiguation number
        in this project currently satisfies the headline rule
  splits manifest OK: every corpus declares a role, a task, and a licence read
  from its terms at a recorded URL on a recorded date
```

**The extraction line went from "1 declared" to "2 declared" and gained "0 in that role" in the same
change, deliberately** — and it went to "3 declared" this round, when a second
`single_annotator_reference` corpus was registered. Registering an extraction corpus that can never
qualify makes "3 declared, none eligible" read as a near miss when the number of corpora in the
eligible role is zero. **Twice now a declared count has risen without the gap moving at all**, which
is the point the note exists to make and is the reason the transcript above is re-run rather than
re-typed at every sweep. **A new residual of the same class arrived with the spend recorded in D-064 and is not fixed:**
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

**Verdict: not met — and the count moved from `0` to `13` of `36` without one new demonstration being
taken.** R11 was written because four defects in one round were all the same shape: a check that could
not fail where it ran. An earlier round built the mechanism that makes the question askable and
answered it in the negative for every gate; this round found that the answer had been wrong since the
day it was written.

```
python tools/gates.py --check           -- command output, re-run for the fifth sweep
  gate manifest: 36 gate(s) across 21 environment(s) in 5 workflow file(s)
  mutation kind: automated 13, control 2, inline 8, manual 13
  demonstrable by this harness: 13 of 36, 0 of them still owed
  CARRYING IN-SITU EVIDENCE:   13 of 36
  top of the cost ranking:     3 of 3 demonstrated  (1 claims, 2 splits_manifest, 3 suite)
  in-situ quota: debt 23, ceiling 23 | 2 round(s) | quota 3 per round
  gate manifest OK
```

**The thirteen were not new work.** `gate-mutation.yml` had already run green on `2026-08-25`, at run
`32808357572` on commit `3173126`, demonstrated thirteen gates with zero inert and zero unrestored,
uploaded all five artifact bundles — and nothing in this repository had ever read it, while
`docs/GATES.md` asserted that workflow had never executed. **The failure mode was not a broken
mechanism; it was an unread output**, and nothing here detects a run nobody harvests. Harvesting it
required proving the evidence still describes the shipped gates: the `git diff` between the run's
commit and the register's, over every gate command and mutation target, is **empty**.

Reading the same run's log also found that the one job measuring packaging breakages measured
**nothing** — six sdist builds died, the table printed `0 of 5` twice against a void control — **and
the job was green**, because a pipe swallowed the script's non-zero exit. Both defects are fixed;
neither figure is re-derived yet. D-079.

What exists: `.github/gates.toml` registering every gate with its defect class, what it detects,
what it is **blind to**, and either a mutation or a refusal with a disposition; `tools/gates.py`
validating the register against the tree rather than against itself, so a workflow scanning to zero
jobs is an error; `tools/gate_packaging_mutation.py` reintroducing five historical breakages against
a real sdist; `.github/workflows/gate-mutation.yml`; `tests/test_gate_manifest.py`; and
[`docs/GATES.md`](GATES.md), which leads with the zero rather than burying it. Ten of thirteen
automated mutations were run and demonstrated locally.

**What still does not exist is the criterion, and `13 of 36` is not a third of the way.** All
thirteen are the gates that were **always** demonstrable by this harness. The other twenty-three are
eight refused `inline` on a real architectural argument — a heredoc has no command to mutate, and a
harness could only mutate a copy, which D-018 forbids — thirteen `manual`, and two control refusals.
R14 is satisfied for all of them and **R14 satisfied is not R11 satisfied**. The honest reading of the
thirteen is *all of the easy ones*.

**What would close it.** A push per remaining gate, and a stored dated failure for each. Three of the
eight `inline` refusals fall to one afternoon of extracting heredocs into `tools/`, which is the
currency the new per-round quota creates. **And the quota's own rules have never run on a runner**:
they were mutated red on a developer machine, which is precisely the evidence R11 says does not count.
D-061, D-079.

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
tools/splits.py, live probe against the real manifest -- command output,
re-run at the fourth sweep rather than carried from the third
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

### Fourth sweep: the costing moved to where a user meets it, and the verdict did not move

The question put to this sweep was whether criterion `10` had closed, and specifically whether it had
closed **by writing the empty row off rather than by filling it**. It did neither. The probe above
was re-run against the live manifest and both slots are still empty, so the first clause is not met;
and the second clause — *the reason is a permanent property of the task, with the filling instrument
costed* — is still inapplicable for the reason already recorded here, that the blocker is a
**resource** limit and not a property of the task. A criterion cannot be closed by an escape clause
whose own precondition this page has already refused.

What did move is where the price is published. D-056 and D-063 already held both costings; they lived
in a decision log. `README.md`'s honest-scope list now names both empty rows with their denominator,
and [`docs/POSITIONING.md`](POSITIONING.md) costs each in full — four remaining D-056 conditions for
extraction, and for disambiguation one irreversible spend of SDU-21 AD `test.json` that D-043 has
already allocated elsewhere. **A reader now meets this gap without opening `docs/DECISIONS.md`**,
which is a change in who is told rather than in what is true. D-070.

**And the denominator was being compressed wrongly in circulation.** "Two of the five things this
library does have no corpus that could adjudicate them" is false: `TASKS` has four members, the two
enforced empty rows are two of four **tasks**, and generation and backronym synthesis are not tasks
at all, so no empty row can exist for them. Extraction's held-out evidence covers `span_detection`
rather than the pairing its headline reports, which D-048 established. Both user-facing pages now
publish the denominator rather than the ratio.

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

**The summary table above this section was comparing two different denominators, and it is corrected
at the fourth sweep.** Its evidence cell read *union gain `32.04 %` against a control of `0.00 %` on
MED1250*. Both figures are real; they are not the same quantity. `32.04` is
`monoculture.plod_all.proposals.edges.independent_gain_pct` and the field on MED1250 that reads
`0.00` is `monoculture.med1250.gold.pairs.independent_gain_pct` — the *gold* control, which belongs
beside the gold-reach percentages and not beside a proposals figure. The comparable control is
`monoculture.med1250.proposals.edges.independent_gain_pct` at `0.23`, **which is the number this
section has printed all along**. So a summary cell contradicted the section it summarises, in the
same document, for a whole round, with both figures inside code spans where the claims gate cannot
see them. The verdict is unaffected: the corrected control is still two orders of magnitude below
the headline. D-070, D-073.

**What is open is the interpretation, not the criterion — and half of it closed at the fifth sweep.**
The contrast between `32.04 %` on article body text and `0.23 %` on abstracts *used* to be equally
consistent with "abstracts contain no figure legends" and with "the corpora were drawn around the
algorithm". **The genre half has now been measured and it points away from provenance**: on `1,839`
PMC articles split into their own abstract and their own body — so provenance, domain, author, journal
and deposit route are constant by construction — with the gold taken from each article's own
`<def-list>` in `<back>` and therefore in neither measured half, every quantity moves the way the genre
account predicts and all six cluster-bootstrap intervals exclude zero. `genre.pmc_oa.*`, D-075.

**The provenance half is what still cannot be separated.** It needs article body text whose gold was
pooled from Schwartz & Hearst descendants, nobody publishes one on purpose, and **that absence is
itself a result and is recorded as one.** Genre being a *sufficient* cause of the ordering does not
make provenance a non-cause; it removes the need to invoke it. D-065, D-075.

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
it. The qualifier ships in the same table as the PLOD figure it qualifies, which is criterion `5`'s
discipline applied to a second table for a second reason — and, as of this sweep, on `README.md` too,
which is the table a stranger meets and which carried **no PLOD span figure at all**.

**The compressed reading of that table is corrected at the fifth sweep.** "The deficit was the
corpus's annotation convention" is the strong form of a figure that is a **net**. The two axes are not
the same kind of thing: `definitional` is an annotation convention, `caps` is the baseline's own
admission rule turned into a gold filter. Priced apart, the convention alone is worth `26.66` points
and reverses the sign by itself; the admission rule costs `-8.50` inside definitional gold; the
interaction is `-1.16`; and `18.16` is what is left corner to corner.
`shortform_contest.plod.{all,test}.convention`, D-076.

**What this does not show, stated here because the number will be quoted.** The span scorer has no
slot for the edge: replaying gold with the pairing rotated gives byte-identical `100.00` on all four
metrics. `85.73` is a defence of this library's short-form *spans* and not of its extraction.
Criterion `10` is untouched by this result and cannot be closed by this route.

**And the control's own strength is smaller than it was reported to be.** `1,054` wrong pairs is a
numerator; the denominator shipped this round. It is `1,054` of `1,778` replayed pairs — `59.28` %,
three in five — and `1,009` of `1,351` documents carry at most one long form, so the rotation could
not touch them at all. The null result is unchanged; the evidence for it is weaker than "three
quarters" implied. `shortform_contest.plod.*.pairing_denominator`, D-066, D-076.

---

## 13. The deferred ledger has a policy and a rate — **new, Mandate II**

> **13. The deferred ledger has a written policy and a measured trajectory.**

**Verdict: met on mechanism and policy; the trajectory now has four observations.**
[`docs/CLAIMS-LEDGER.md`](CLAIMS-LEDGER.md) states the policy; `tools/check_claims.py` enforces it.

```
python tools/check_claims.py            -- command output, re-run for the fifth sweep
  value-matched ratchet:  64 of 64 budgeted across 3 file(s)
  deferred ratchet:      201 of 201 budgeted across 10 file(s)
  ledger trajectory: 5 rounds | M2-P6 (the walk)
                     moved 12 (citation 3, deletion 9, fencing 0, other 0)
                     12 of them out of docs/DECISIONS.md
                     deferred 201, value-matched 64
                     quota 12 per round, record-file floor 12
```

`LEDGER_TRAJECTORY`'s last row must equal the live baselines; its four movement columns must add up
to the fall it claims; and a round below `MIGRATION_QUOTA` must record a waiver. All three were
demonstrated red by mutation in this checkout. **The `fencing` column is why this is a policy rather
than a number**: D-052 established that a fenced figure leaves the gate's view entirely, so a
falling ledger is not evidence of adjudication unless the fencing column is published beside it. It
reads zero.

**The trajectory now has four observations and they are falling: `54`, `31`, `18`, `12`.** A rate that
decelerates is what paying out of the debt's easy half looks like, and the fourth round landed exactly
on the floor, which is what the third round's arithmetic predicted.

**The waiver the previous round said this one would need did not arrive, and the reason is worth more
than the twelve numbers.** That round walked the `66` remaining and concluded "the citable remainder is
zero", on per-record verdicts. Walking them per number found three that a citation reaches and nine
that a stated deletion rule reaches — a percentage restating a numerator and denominator the reader
still has, a notional maximum that is not a measurement, or a figure the record's own sentence declares
unquotable. **A verdict written per record and applied per number will be too wide, and this is the
third round in a row to discover it.** `54` remain — `45` of them in two records with no runner behind
them at all, `6` that the record carrying them already labels un-gated, and `3` that are not
measurements this project ever took — and the *next* bound round owes a waiver naming four mechanisms.
D-084.

**Nine of the twelve are deletions, and that is a weaker outcome than citation.** A cited number can be
wrong and be caught; a deleted number cannot be checked, because it is not there. The `by_deletion`
column exists so the trade is visible per round rather than folded into one falling total, and this is
the first round in which that column carries most of the movement.

**The structural ceiling this criterion named is the part that moved.** At the third sweep
`docs/DECISIONS.md` held `115` of the `262` deferred numbers, only the recorder could edit it, and
the recorder had migrated none of them. That carve-out was withdrawn by the maintainer, a per-file
floor and a record-count pin were built, and two bound rounds have taken the record file from `115`
to `66`. **Adding a decision record now reddens the build until the round is recorded and the pin
re-taken**, which is what makes this a policy the recorder is inside rather than one it administers.

**And the cell above went stale inside one round, in the direction the criterion is about.** It read
*`docs/DECISIONS.md` holds `115` of the `262`*; both halves were falsified by the burn-down this
criterion exists to measure. That is not a regression, and it is the fourth-sweep instance of the
class this page keeps recording: every figure in this block is fenced, so nothing tells a reader when
it goes out of date except somebody re-running the command. D-059, D-071.

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

**A second pass has now run, and it ran as policy rather than as a one-off.** It carried the
rotation cursor — trigger B served `docs/GOVERNED_NAMING.md`, the cursor now stands at
`docs/SUPPORT_MATRIX.md` — appended `docs/POSITIONING.md` to a rotation set that could never have
reached it, shipped six fixes to user-facing prose, and found the single most material omission of
the round: `README.md` said nothing about every published governed figure having been taken with an
**empty** catalog. It also found three defects in the policy itself, of which the sharpest is that
**trigger A's published command returns an empty list at the exact moment the trigger fires**,
because the round is still in the working tree and the round base *is* `HEAD`. A trigger that cannot
be executed when it fires is the shape this page's criterion `9` exists to refuse, arriving in a
document instead of in a workflow. D-072.

**A third pass has now run, and it is the one that found the mechanism's cost.** The policy's trigger
is executable code with a test — the superseded command that returned an empty list at the moment the
trigger fires is pinned as still-blind in the same fixture the working trigger reads two files from —
the rotation set has one copy instead of two that had already diverged, the cursor is derived rather
than typed, and the hand-off is a schema-validated ledger in which `disposition = "fixed"` requires an
`applied_by` that is **not** the reader who raised the finding.

**Then the third read wrote no row at all**, because the round's instruction made the reader read-only
in the filesystem sense while the policy requires it to write the ledger. So the newest
`rotation_served` is still the *second* read's file, the next reader will serve the file the third
reader just served, and five findings sitting at the two-read limit stay there — **with the gate green
throughout**. Six new findings live in a notes file, outside the schema, outside the decay clock and
outside every check. Two of them were applied by this sweep, which is the `applied_by` mechanism
working; the other four are named for their owners. D-081.

**And "anything user-facing" is wider than either trigger reaches — which is how a retired sentence
shipped for two rounds in the most-read file in the package.** `src/acronymkit/__init__.py`'s module
docstring is the first prose a reader meets in an editor, it is inside `tools/check_claims.py`'s
`SCAN_GLOBS`, and [docs/POSITIONING.md](POSITIONING.md) reported it as still opening with near-duplicates
of two of the three sentences that page retires. **No trigger could have found it.** Trigger A's
pathspec is six entries and `src/` is not among them; `user_facing_files()` enumerates the root files
and the Markdown under `docs/` minus the historical and note exclusions, returns `21`, and none of
them is source, so trigger B cannot serve it either. It was found both times
by check C5 — following a pointer out of `docs/POSITIONING.md` — and fixed in neither round because
`owner` read `unowned` and no workstream held the file. Demonstrated in the tree that fixed it rather
than argued:

```
python tools/second_reader.py --trigger, in the working tree that rewrote the docstring.
CPython 3.13.4 on win32; command output, not a benchmark measurement.

  git status --porcelain             ->   M src/acronymkit/__init__.py   (among others)
  python tools/second_reader.py --trigger
                                     ->   4 user-facing file(s) changed
                                          CHANGELOG.md, docs/CLAIMS-LEDGER.md,
                                          docs/DEFINITION-OF-DONE.md, docs/EVALUATION.md
                                          -- and NOT the source file it just changed
```

**The gap is in how work is assigned, and it is not that anybody failed to notice.** D-070 recorded
the disposition as *blocked on ownership*; the cold-read ledger carries it as `F-2026-08-25-01`,
`blocked`, whose `blocked_on` says in its own words *"It is not blocked on knowing what to write."*
Two rounds that fixed harder things left it, because the assignment mechanism has no way to hand out a
**source** file: the rotation is a list of documents, and each round's file lists are written by hand.
The docstring is rewritten this round; the coverage hole that hid it is **reported and not fixed**,
because `tools/second_reader.py` is another workstream's. Widening `user_facing_files()` to reach
`src/acronymkit/**/*.py` is not a one-line change: `--check` refuses any enumerated file the rotation
cannot reach, `find src/acronymkit -name '*.py' | wc -l` returns `40`, and the set would turn over in
`61` rounds instead of `21` — section 3 of that page already prices the current latency as a
weakness. That is a
decision about the policy's scope, and it belongs to whoever owns the policy.

**What would close it further.** Nothing for the literal criterion. Nothing enforces it: the enforcing
CI job is specified in one paragraph and was not built, because it belongs in files nobody owned and
because a gate never demonstrated failing where it runs is the shape criterion `9` exists to refuse.
**And registering it is not free** — the in-situ debt is at its ceiling, so a thirty-seventh gate with
no evidence turns `tools/gates.py --check` red. Until that job exists and has been mutated red on a
real push, this is a document asking to be followed — the object this repository has learned to
distrust. D-060, D-081.


---

## 15. No figure ships unchecked — **new, Mandate III**

> **15. No figure ships in a document unless a committed script regenerates it from
> `bench/results.json` and CI diffs it.** A figure inside an image is an unchecked claim: the claims
> gate cannot read an SVG or a PNG.

**Verdict: not met, not started — and there is no live instance to be not-started about.** That last
clause is the whole content of this row, and recording it as a bare *not started* would be less true
than recording it with its firing count.

```
find . \( -name '*.svg' -o -name '*.png' -o -name '*.jpg' -o -name '*.gif' \) \
     -not -path './.git/*' -not -path './build/*' | wc -l
  -- command output, not a benchmark measurement
  0
```

**Zero figures ship in this repository.** So no unchecked figure exists, no regenerating script
exists, and the rule currently binds nothing. The honest reading is that R16 is a **pre-commitment**
rather than a criterion with evidence behind it: it will first be tested by whoever wants a chart,
and until then nothing here demonstrates it can fire.

**What would close it.** A script, a CI diff step and a registered gate — written *before* the first
figure rather than after it, because the rule exists precisely so that the first one cannot ship
unchecked. Registering the gate is **not free**: criterion `9`'s in-situ debt sits at its ceiling, so
a thirty-seventh gate with no evidence turns `tools/gates.py --check` red.

---

## 16. The round trip measured as a verifier — **new, Mandate III**

> **16. The forward generator's round trip is measured as a verifier of extractor output, with a
> go/no-go recorded.**

**Verdict: met as a measurement, and the answer is no.** Re-derived by the recorder from a fresh run
of the runner rather than read off `bench/results.json`.

Unpruned recall on the true short form is
42.09<!--claim:roundtrip.med1250.recall.beam_control_never_cuts.recall_pct:.2f--> % on MED1250 and
51.75<!--claim:roundtrip.pmc_oa.recall.beam_control_never_cuts.recall_pct:.2f--> % on PMC-OA, against
a Schwartz & Hearst aligner that accepts
85.70<!--claim:roundtrip.med1250.ceiling.aligner_accepts_pct:.2f--> % and
90.69<!--claim:roundtrip.pmc_oa.ceiling.aligner_accepts_pct:.2f--> % of the same pairs. **A verifier
built on it would silently reject roughly two of every five pairs the aligner had right**, and the
cause is architectural rather than configurational: the generator emits word *prefixes* and the
aligner places a character anywhere *inside* a word, which is
442<!--claim:roundtrip.med1250.misses.misses_architectural:,--> of MED1250's `644` misses.

**The go/no-go is recorded in D-085**, with A2 and A5 stopping behind it, and with the one framing
under which the mechanism survives — a precision filter worth
25.60<!--claim:roundtrip.med1250.extractor_proposed.high_precision.discrimination_points:.2f--> points
of discrimination at the cost of half the recall — recorded beside the refusal rather than instead of
it.

**What would close it further.** Nothing for the literal criterion. What is **not** met is gating:
`bench/run_roundtrip_verifier.py` appears in no CI job and `.github/gates.toml` does not know it
exists, so nothing re-derives these figures but a person with the command. Both corpora are declared
`contaminated = true`, so no figure here may ever be quoted as a headline.

---

## `17`. A gated throughput baseline in machine-independent counts — **new, Mandate III**

> **`17`. The governed hot path carries a gated throughput baseline, published in machine-independent
> counts, with wall-clock reported as an unarmed note and the machine named.** A performance number
> without a work count is a null result; a benchmark that got fast because it stopped doing work
> looks exactly like one that got fast because the work got cheaper.

**Verdict: partly met.** One entry point, two real corpora and one fixture, with the census figures
re-derived by the recorder from a fresh run.

What is gated: tokenizer passes, catalog lookups **split by origin**, index decisions, both memo hit
rates, provenance records constructed, class-word lookups, `_prepare` calls, validation calls and
total Python calls, across four arms. What is fenced and never armed: wall-clock, with the machine
named — and the fence carries the three-run comparison that motivates the rule, `8,118` / `11,597` /
`8,895` ns per identifier with **every count identical to the unit**.

The baseline's own headline is that provenance construction is
70.15<!--claim:governed_perf.socrata.empty.stage_provenance_pct:.2f--> % of the Socrata call and
larger than the other three cost centres put together on all four arms (D-086).

**What would close it.** The other three entry points. This decomposes `expand_identifier` alone:
`is_compliant` and `to_physical_name` are three to five times dearer per call by the existing
`governed.*` runs and have no decomposition, and `extract`, `disambiguate` and generation have
entirely different hot paths that nothing here touches. **And memory is not measured at all** — the
gated figure is object constructions counted exactly, not bytes.

**Why this criterion's own number is inside a code span, in three places, and no other criterion's
is.** `throughput` is one of the claims gate's eleven arming keywords, so a bare `17` sharing a line
with it is read as a throughput claim of seventeen and lands on the closed value-matched ledger. It
did, on this page, on the first run after this section was written — three times, once per line
carrying both. **The gate armed an ordinal.** That is the citation-arms-neighbour class D-071 and
D-084 each published a workaround for, seen from the other side: there the arming word arrived in a
citation's field name, here it is in the criterion's own title. The number is an index and not a
measurement, so silencing it is correct rather than evasive — and it is named here because a code
span with no explanation beside it is exactly what D-052 says is indistinguishable from hiding.

---

## 18. Byte-identity, not benchmark-equality — **new, Mandate III**

> **18. Every optimisation is proven behaviour-identical, not benchmarked-equal: full corpus, forced
> on and forced off, byte-identical output including provenance records, gated.** A cache that
> changes one `entry_id` in ten million is catastrophic for a governance instrument and invisible to
> a benchmark.

**Verdict: not met, not started — and no obligation arose, because nothing was optimised.** No
byte-identity gate exists in `.github/gates.toml`, and the phase that measured what to optimise
deliberately built none of it.

The one place R19 was applied is to an **instrument** rather than to shipped code:
`bench/run_governed_perf.py`'s ablation stages are proven byte-identical to the shipped path over the
full corpora — `421,199` `expand_identifier` calls per pass, `0` phrase mismatches, `0` lookup excess
and `0` class-word excess on all four arms, with three positive controls showing each check can
report non-zero. That is the discipline this criterion asks for, applied to the measuring device.

**What would close it.** The first optimisation, and its gate, in the same commit. **A rule with no
instances is a rule with no evidence that it can fire** — which is the objection criterion `9` exists
to make about CI jobs, arriving here about a rule instead.

---

## 19. W11 decided — **new, Mandate III**

> **19. W11 — whether `extract()` may emit a short form with an absent or low-confidence long form —
> is decided.**

**Verdict: not met, not started.** [`docs/notes/w11-emission-model.md`](notes/w11-emission-model.md)
opens with *"Status: scoping note. No decision, no behaviour change, nothing shipped."* It scopes the
question, costs it and gives it a failure mode; it does not decide it, and nothing in this phase went
near it.

**Why it is on this list rather than in the standing unknowns.** It is not an unknown — nobody is
waiting on a corpus, a licence or a stranger. It is an undecided **product** question with an owner
available, which is a different shape and belongs on the list of things that could be finished.

**What would close it.** A decision taken out loud in a record, either way. It bears on criterion
`10`: answering it *yes* is the only route by which a span corpus could adjudicate the flagship
extraction claim, so leaving it open leaves that row empty for a second reason on top of the one
already recorded.

---

## 20. The catalog-gap report, shipped and run by a stranger — **new, Mandate III**

> **20. The catalog-gap report is shipped **and has been run by a stranger.**

**Verdict: half met, and the half that matters is not.**
[`docs/SOURCING.md`](SOURCING.md) ships: an owner, three dated actions, a `2026-11-23` expiry, a
target list with categories, and a stranger-runnable kit that makes the ask cheap to say yes to. Its
own log, in its own words, reads **approaches made: `0`**.

**This is `U-0` with a delivery date attached.** The standing unknown — *does a governed catalog add
anything on a real schema?* — is the question the whole governance positioning rests on, and D-074
established that the only measurement anybody had of it measured a catalog's **cost** rather than its
**worth**. The report exists so that the ask is cheap. Nobody has made the ask.

**What would close it.** One organisation saying yes. **No amount of work inside this repository
moves it**, which is why the second clause of the criterion is the one written in bold: shipping the
report is the part this project controls, and it is the part that does not settle anything.


---

## Standing unknowns

**Things nobody is working on, that are not therefore closed.** The twenty criteria above are a
bar this project is held to. This section is the other list: questions whose answer is *we do not
know*, where nobody is scheduled to find out, and where the honest response is to write the question
down with its price rather than let it lapse into the space between a retracted sentence and the
next document sweep.

A criterion is something to meet. **A standing unknown is something to not pretend is met.**

**Counted rather than carried, because the tighter sentence was false.** Exactly **one** of the
three below — `U-1` — was already being described as "named in the standing unknowns", in
`docs/EVALUATION.md`, pointing at a section that **did not exist** for a round. That is the same
defect as the sentence which created the entry: an appeal to something the repository does not
contain. `U-0` is referred to in `docs/POSITIONING.md` as "the standing unknown", singular, and
points at `docs/AUDIT-2026-08.md` rather than here, so it was never a dangling pointer. `U-2` was new
at the fourth sweep and was found by a gate rather than by a reader. **`U-3` and `U-4` are both new
at the sixth round and there are five below, not three** — the count in the sentence above is the
fifth sweep's and is left standing rather than silently bumped, because a count that is quietly
corrected each time it goes stale is a count nobody can watch. `U-3` was found by a census, and it is
the first entry here whose fifth column reads *no instrument is available* rather than *nobody has
spent the afternoon*. `U-4` was found by building the instrument `U-1` could not have: it is the
residue an agreement test leaves behind, and its fifth column reads *nobody in this repository* for
exactly the reason the extraction row of [docs/POSITIONING.md](POSITIONING.md) is empty.

**Nothing has been added to or removed from this table at the fifth sweep, and `U-0`'s cell was
rewritten rather than ticked.** The measurement that appeared to answer it turned out to answer a
different question; the unknown is exactly as open as it was, and it now has a plan with an expiry
date attached to it rather than a closure. D-074, D-078.

**One row was added at the sixth round, and it is an addition rather than a demotion.** `U-3` did
not come out of the fourteen criteria and nothing above was moved into it; it came out of the census
of the audit's do-not list, which found `13` of `35` of that list's figures not true of this tree or
not re-derivable at all, and then found that no check in this repository could have seen any of the
thirteen. The rule this section states — a later round that demotes a criterion into this table should
say it did — is met by saying that this is not one.

**A second row was added in the same round, and it was created by an attempt to close `U-1`'s
neighbour rather than by a sweep.** `U-4` is what is left over after the extraction differential
(`differential.med1250.*`, `bench/run_scorer_differential.py`,
[docs/EVALUATION.md](EVALUATION.md#the-differential-that-replaced-the-withdrawn-argument-and-the-half-of-the-hole-it-does-not-reach)):
the reader now has an outside check and the **convention** the scorer implements still has none,
because two implementations of a convention agreeing is evidence about the implementations. Also
not a demotion — nothing above moved into it. **And `U-1` did not move**: it asks whether this
harness matches a *published evaluation*, and no differential can answer that. Its first column now
records what did change around it, which is a smaller statement than a tick and is the whole point of
keeping a row open.

| # | The unknown | Why it is not urgent | What would close it | Who can |
|---|---|---|---|---|
| `U-0` | **Does a governed catalog add anything on a real schema?** Carried, not new — ranked first in [docs/AUDIT-2026-08.md](AUDIT-2026-08.md#1-does-a-governed-catalog-add-anything-on-a-real-schema) and it is [reversal one](POSITIONING.md#reversal-one-the-lead-is-wrong-if-a-catalog-is-worth-nothing-on-a-real-schema) of the positioning | **It is urgent, and its evidential status changed at the fifth sweep without the unknown getting any smaller.** The one measurement that appeared to point the other way has been re-run and decomposed, and it measured a catalog's **cost** on the `76.53` % of pairs that needed no catalog rather than a catalog's **worth** (D-074). The evidence against the lead is withdrawn; none for it has been supplied. It is listed here because it is unowned, not because it is small | One real proprietary glossary measured against the schema it governs, catalog against empty catalog, on gold the auditor did not infer from the labels being scored, **and decomposed on the already-unabbreviated line rather than pooled** — a pooled figure on a real schema will be just as unreadable | **Nobody in this repository.** One organisation handing over one glossary. There is now a plan with an owner, three dated actions and a `2026-11-23` expiry ([docs/SOURCING.md](SOURCING.md)), and a stranger-runnable kit that makes the ask cheap to say yes to — and **zero approaches have been made** |
| `U-1` | **Does this extraction harness match Ab3P's own published evaluation?** The sentence that used to assert it — that this library's reproduction lands within half a point — cited figures that matched neither `bench/results.json` nor the table five lines above it, appealed to a paper nobody here has read, and was **withdrawn** rather than restated at corrected values (`docs/EVALUATION.md`, D-060 for the sweep that found it). **Unchanged at the sixth round, and the round that could have been read as closing it says so first.** A differential now compares this harness against the NLM's own checked-in Ab3P output over the same corpus and agrees on 1,053<!--claim:differential.med1250.reference_output.pairs_agreeing:,--> of 1,053<!--claim:differential.med1250.reference_output.reference_pairs_raw:,--> pairs. That is agreement with an *implementation's output*, not with a *published evaluation*, and this row is about the second | Extraction is a **supporting** number under [docs/POSITIONING.md](POSITIONING.md), and nobody optimises it again. The withdrawal cost the project an argument it never actually had | The paper's figures read **from the paper**, cited with the date somebody read them, and this harness's reproduction compared against them in the same table. **No differential substitutes for it**, and the one that shipped is written up as narrowing the surrounding hole rather than closing this one | **Anybody here.** One afternoon nobody has spent |
| `U-2` | **Is the disambiguation harness validated, or does it only say so?** The bold *Harness validated.* claim in [docs/EVALUATION.md](EVALUATION.md) rests on agreement with a shared task's own baseline scores. Those scores are named in `bench/run_disambiguation.py` with a source and **no read date** anywhere in the tree — found by `tools/check_external.py` in the round that built it, and held in that tool's `UNCITED_LEDGER` with a disposition | Same reason as `U-1`: disambiguation is a supporting number, and the row it validates has [no headline-capable corpus](POSITIONING.md#the-two-rows-that-are-empty-and-what-filling-each-costs) either way | Either a read date recorded against the pinned repository's own reported baseline, which makes the agreement an argument; or the sentence withdrawn the way `U-1`'s was | **Anybody here.** The source is already named; only the date is missing |
| `U-3` | **Is a prohibition's stated reason still true?** New at the sixth round. Across the audit's do-not list — a census, not a sample — `13` of `35` figures are not true of this tree today or cannot be re-derived at all, `37.1` %; ten stated reasons are corrected in place in [docs/AUDIT-2026-08.md](AUDIT-2026-08.md), and **no prohibition's conclusion fell**. D-077 | **It is un-urgent by construction, which is exactly why it persists.** A live claim is read by somebody; a prohibition is read by nobody, because the direction it closes is closed and work stopped flowing to it. So a wrong reason survives longer inside a do-not list than anywhere else in the tree, and the cost is paid once, by whoever next re-examines it | **Nothing available today, and that is the finding rather than a gap in the search.** Both checks whose shape could apply were run over all `35` figures: `tools/check_claims.py` routes `10` by run id, `tools/check_external.py` routes `0`, and **`0` of the `13` that failed are routable by either** — every figure a gate could see was already true. Closing it needs a third route nobody has built. What exists meanwhile is a convention with a measured effect: the one property separating the surviving figures from the failing ones is being written under a run id | **Anybody here**, and the entry is carried as *no gate is available* rather than as a to-do. A reader who builds a route that catches even one of the thirteen has refuted it, which is the outcome this row is written to invite |
| `U-4` | **Is the extraction scorer's matching *convention* the right one?** New at the sixth round, and created by the attempt to check the scorer rather than found by a sweep. `bench/scoring.py`'s counts are now re-derived by a second implementation that shares no code with it and agrees on 12<!--claim:differential.med1250.scorer_agreement.verdicts_agreeing_on_counts:,--> of 12<!--claim:differential.med1250.scorer_agreement.verdicts_compared:,--> verdicts over 5,159<!--claim:differential.med1250.scorer_agreement.pairs_scored:,--> pairs. **That is evidence about two implementations and none at all about the convention they both implement**, and no reference scorer for this task exists to adjudicate the convention: the search is counted in `differential.med1250.reference_output` and returned 0<!--claim:differential.med1250.reference_output.pyab3p_scoring_entry_points:,--> evaluation entry points in `pyab3p`, 0<!--claim:differential.med1250.reference_output.ab3p_makefile_scoring_targets:,--> scoring targets in Ab3P upstream, and 0<!--claim:differential.med1250.reference_output.shared_task_scorers_expressing_pair_extraction:,--> of 2<!--claim:differential.med1250.reference_output.shared_task_scorers_in_tree:,--> shared-task scorers in this tree able to express the task | **Two of its live decisions are now priced and both are small.** Corpus-pooled rather than per-document matching moves 0.00<!--claim:differential.med1250.specification.axis_pooling_max_abs_f1_delta:.2f--> points across all twelve cells measured; applying the relaxed convention to the short form as well moves 0.80<!--claim:differential.med1250.specification.axis_relaxed_short_form_max_f1_delta:.2f--> points and moves them **against** this library, over 9<!--claim:differential.med1250.specification.axis_relaxed_short_form_pairs_reclassified.acronymkit:,--> pairs. An unknown whose known live decisions are worth under a point is not an emergency | An adjudicator outside this repository: a published scorer for pair extraction, or a second annotator's reading of what counts as a correct long-form boundary. The same person `U-1`'s neighbour in [docs/POSITIONING.md](POSITIONING.md#extraction--the-instrument-exists-the-adjudicator-does-not) has been waiting for | **Nobody in this repository, and that is the same constraint as the empty extraction row.** The one adjudicator available wrote the extractor. What *is* available here is publishing each undocumented decision with its price, which this round did |

**What this section is not.** It is not a backlog — a backlog implies somebody is about to work on
it, and the fifth column says who can, which for `U-0` is nobody here. It is not a place to move a
criterion that got hard: nothing above has been demoted into it, and a later round that does so
should say it did.

**The gate for `U-1` and `U-2`'s class now exists and it did not before.** Nothing in this
repository could check that an appeal to somebody else's published numbers carried a source and a
read date; that is why the withdrawn sentence survived six audits, two adversarial passes and four
documentation sweeps. `tools/check_external.py` is that check. Its blind spots are enumerated in its
module docstring and pinned as *passing* tests in `tests/test_check_external.py`, and the largest is
that a figure inside a code span is invisible to it — the same hole D-052 recorded in the claims
gate, inherited on purpose because arming numbers inside backticks fires on every configuration
value in the tree.

**It is not in `.github/gates.toml`, and that register is not this workstream's to edit.** The entry
was reported to the owner of that file rather than written. Until it lands, the only thing running
this check is `tests/test_check_external.py` under `python -m pytest tests` — which is a real gate
and is not the same as a CI job, and criterion `9` is the criterion that cares about the difference.

**`U-3`'s answer runs the other way, and the contrast is the useful part.** `U-1` and `U-2` are a class
that turned out to be gateable the moment somebody wrote the check. `U-3` is a class that was probed
the same way and came back with nothing: the figures a check can route are the figures that were already
true, and the ones that failed are number-free assertions, quotations of other documents, properties of
a build environment, or measurements against a resource this project deliberately did not acquire. **A
figure about a thing you decided not to obtain is a figure nobody can re-derive**, and no gate fixes that.
The honest register entry is a negative result, and it is carried as one.

---

## How this document fails

**Eleven of twenty read met at the sixth sweep, against ten of fourteen at the fifth — the count rose
by one and the proportion fell from roughly seven in ten to a little over half.** That is the first
time six new criteria have arrived without the page reading better for it, and it is stated here
rather than left to be computed. The defence for the ten that stood is unchanged and is still a
defence: five of them closed on criteria that are modest about themselves — `11`, `12`, `13`, `14`
and now `16` ask for *measured*, *published*, *has a policy*, *exists in some form* and *measured,
with a go/no-go recorded*, not for *good*. **Criterion `16` is the sharpest case: it reads met and
the thing it measured came back negative.** A criterion that closes on a measurement regardless of
which way the measurement went is a criterion about diligence, not about the library, and this page
now contains five of those out of eleven.

**And the round that added six criteria measured a `20.8 %`–`25.0 %` error rate on this project's own
reporting for a third time.** Put those two facts side by side, because a hostile reader will.

**That count read `9` until the fourth sweep and it was wrong under every rule.** Counting *met with
qualification* as met gives `10`; refusing to count it gives `8`; `9` is neither. It stood in this
paragraph and in D-069, which is the paragraph a hostile reader opens first, and the error ran in
the direction that flattered the page. It was written from the previous summary rather than
re-counted from the rows above — the class D-068 measured at a fifth of sampled claims, committed by
the page that grades the project on exactly that. D-073. The criteria that ask for something hard — `3`, `9` and
`10` — are all open. **A definition of done whose met-count rises when six new criteria arrive is a
definition of done scoped by the same people it grades**, and nothing here answers that.

**Two of fourteen were not re-derived at the third sweep, seven at the fourth, five at the fifth,
nine of twenty at the sixth.** Criteria `1`, `2`, `5`, `6`, `7`, `8`, `10`, `11` and `12` carry an
earlier sweep's verdict, and the first five of those have carried for four sweeps running. The head of this page used to say
every verdict is re-derived; it no longer does, and the table names them per row. **This is the number
to watch across sweeps**: twelve of fourteen re-derived, then seven, then nine, then eleven of twenty.
It has gone up twice running as a count and **down as a proportion at the sixth sweep**, from nine in
fourteen to eleven in twenty, because six new criteria arrived and every one of them was re-derived
while none of the five long-carried ones was. A reader should hold that lightly — the five now carried have been
carried for three sweeps running, so the ones still being re-derived are the ones that keep moving, and
a verdict that never moves is exactly the verdict a stale reading hides in.

**The falsehood the fifth sweep found is the sharpest instance this page has produced of its own
thesis.** A cell of criterion `3` said two sentences were unfixed, in the commit that fixed them, in a
document whose entire purpose is to stop a verdict being repeated after it stops being true. Nothing
caught it: it is prose, and no gate in this repository can read a sentence. It was found by a cold
reader running two `git log -S` commands. **The instrument that works here is a person with a
recipe**, and this page has no way to require one.

**Two evidence cells were wrong for a whole round and no instrument could have said so.** Criterion
`11`'s cell compared a proposals-side gain against a gold-side control and therefore disagreed with
its own section; criterion `13`'s cell was falsified by the burn-down it describes. Both were found
by reading this page against `bench/results.json` by hand. **Both figures were inside code spans**,
which D-052 established is mechanically indistinguishable from hiding — so the gate was silent about
them by construction, and the page's own convention of printing the command above every fenced block
is the entire defence. D-068 measured that convention failing at a rate this page has no reason to
think it beats.

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
