# What this library is for

**`acronymkit` is a governance instrument.** The subject it is built around is a name somebody else
owns: a schema column, a data-standard identifier, a token from a vocabulary the caller supplies and
this library may not extend. Its first obligation on that subject is to report *unknown* rather than
return a plausible answer — because an unknown reported as unknown is recoverable and an unknown
quietly guessed is not.

Generation, backronym synthesis, extraction and contextual disambiguation all ship, all are measured
wherever they can be measured at all, and none of them leads.

Three positionings were on the table — a governance instrument, a research artifact about the
extraction monoculture, and a general adoption-seeking library. This page states which one was taken,
what taking it costs, why the argument for it is a measurement rather than a preference, the two
questions this project cannot currently answer at all, and **what would reverse the decision.** A
positioning with no stated reversal condition is a mood rather than a decision, and it gets revisited
on evidence rather than on how anybody feels about it in six months.

---

## The commitment

**The governed half leads, and the reason is not that it is bigger.**

"It is the larger half of the package" was the reason `README.md` gave, backed by a share of the
source, a share of the public symbols and a share of the CLI commands. That is a weak reason and it
is the wrong one: size is not an argument for anything. The two reasons that survive are:

- **It is the half with no competitor.** The ecosystem table in [`README.md`](../README.md#why) has
  four rows and not one of them addresses a bare column token with no sentence around it, a catalog
  somebody else owns, and a requirement to refuse rather than guess. Every other acronym task this
  package performs has a row in that table aimed at it; this one has no row at all. That is a
  statement about the ecosystem and not about quality — and the honest reading of an empty space is
  that it may be empty because nobody needs it, which is what the first reversal condition below is
  for.
- **It is the half the refuse-to-guess property is *about*.** A column name is not a sentence. There
  is no context to weigh, so the answer comes from the catalog or it does not come at all, and
  `is_fully_known` is false the moment anything went unaccounted for. Everywhere else in this package,
  refusing is a tuning knob. Here it is the design.

**Refusal has a measured price and that price is published beside the headline, not beneath it.**
Against Socrata field/caption pairs written by the publishers themselves, the identifier is cut
exactly where the human cut it on
91.37<!--claim:governed_gold.socrata.columns.all.exact_pct:.2f--> % of them, and on the pairs that
carry no boundary mark at all, on
34.93<!--claim:governed_gold.socrata.columns.unmarked.exact_pct:.2f--> %. The second number is what
this design costs, and it is in the same table as the first —
[docs/EVALUATION.md](EVALUATION.md#the-governed-subsystem-its-first-accuracy-figures). Those runs
were all taken before their corpora were declared, and none has been re-measured since, so they are
measured-before-declared rather than held out.

Everything else this package does is a **supporting** number. Supporting does not mean hidden:
**where a losing comparison exists it sits in the same table as the figure it loses to**, which is
the whole of what a governance instrument can offer about itself.

This sentence used to read *each one keeps its losing comparison*, and that counted four capabilities
and was true of two. Extraction is beaten by two compiled systems and disambiguation loses to a
trivial frequency baseline, both in their own tables. **Generation has no external comparison to
lose** — nothing else in the category generates, which is a fact about the category and not a
distinction this package earned — and **backronym synthesis has no figure at all**, marked
permanently unmeetable because scoring one needs a judgement no corpus records. An exhaustive word
over an enumeration is a claim, and this one was checked by counting both sides.

---

## What this costs, stated so that softening it later is visible

Four consequences follow. None is comfortable, and the first is not solvable with code.

### It requires a real proprietary glossary, and this project does not have one

Everything governed is currently measured against **public substitutes** — Socrata captions and SEC
XBRL filer extensions — because a real data-standards glossary is proprietary by nature. Substitutes
are the wrong shape in a specific way: they are captions somebody wrote for a portal, not a standard
somebody governs a schema with.

**And no catalog is in those figures at all.** `bench/run_governed_gold.py` scores every published
governed row through `expand_identifier(identifier, GovernedDictionary({}))` — an **empty** catalog,
which the corpus admission rule forces rather than merely permits, because a populated catalog would
rewrite the identifier and the two strings would stop sharing a character stream
([docs/EVALUATION.md](EVALUATION.md#the-governed-subsystem-its-first-accuracy-figures)). So those
figures measure where an identifier is cut and say nothing whatever about what a governed vocabulary
is worth. Every experiment that *does* build a catalog — the audit's, and the gated re-run that
replaced it — infers that catalog from labels of the very kind used as gold, and that whole line of
work is [reversal one](#reversal-one-the-lead-is-wrong-if-a-catalog-is-worth-nothing-on-a-real-schema).

This is the standing unknown that has gone unclosed across three phases; it is ranked first in
[docs/AUDIT-2026-08.md](AUDIT-2026-08.md#1-does-a-governed-catalog-add-anything-on-a-real-schema),
and closing it needs one organisation to hand over one glossary and the schema it governs, under NDA
if necessary. **That is a people problem, not a code problem**, and no amount of work inside this
repository moves it.

### The breadth pitch is retired, not softened

Three sentences are gone from the tree and are not coming back in a gentler form:

- *"Bi-directional, multi-tiered acronym processing for production systems"* — the `README.md`
  tagline.
- *"`acronymkit` is the missing single library"* — the conclusion of the `## Why` table, and the same
  sentence in [docs/ARCHITECTURE.md](ARCHITECTURE.md).
- *"Enterprise-grade text-to-acronym generation, extraction, and disambiguation engine"* —
  `pyproject.toml`'s `description`, which is the line PyPI shows and which led with generation and
  did not mention governance at all. It is the sentence most strangers meet first and it was the
  furthest from what this library is for.

All three are adoption claims. They say *use this instead of stitching three codebases together*,
which is an argument about convenience, and convenience is not what this project has evidence for.
The table those sentences concluded is accurate and stays; what it concludes changed.

Retired here, and **still shipping in one place this workstream did not own**:
`src/acronymkit/__init__.py`'s module docstring opens *"bi-directional, multi-tiered acronym engine"*
and *"One library for the three things production systems do with acronyms"*. That file is scanned by
the claims gate and is somebody else's to edit. Reported, not fixed.

### The extraction figure is a supporting number and nobody optimises it again

On MED1250 this library scores
84.21<!--claim:extraction.med1250.acronymkit.exact_f1:.2f--> % F1 — **third of five**, behind
`pyab3p` at 88.87<!--claim:extraction.med1250.pyab3p.exact_f1:.2f--> and `abbreviation_extractor` at
84.44<!--claim:extraction.med1250.abbreviation_extractor.exact_f1:.2f-->, both of which are compiled.
That is now fine and it is stated rather than framed away. It is also **one extraction profile of
three**: `bench/run_extraction.py` sweeps `HIGH_PRECISION` alone, three profiles ship, and resolving
that is a decision about the number's identity rather than a runner edit — recorded, open, and not
being closed by tuning.

Demoting is not hiding. The number stays on the front page with the two systems that beat it named,
because a governance instrument that concealed a middling number about itself would be refuting its
own thesis on its own front page.

### The two empty rows are standing properties, not emergencies

Extraction and disambiguation have no corpus that could adjudicate them. Both are
[written down and costed below](#the-two-rows-that-are-empty-and-what-filling-each-costs) rather
than carried as a to-do list, because a to-do list implies somebody is about to do it.

---

## Why refusal is worth more than a bigger number — and the half of that argument that is confounded

This argument did not exist before this round, and it is the reason the governance positioning wins
on evidence rather than by elimination.

**The field's extractors share a blind spot, and it has a size.** Across seven Schwartz & Hearst
descendants scored through one harness on PLOD-CW, a single implementation — this library's
`BIOMEDICAL` profile — accounts for
93.55<!--claim:monoculture.plod_all.proposals.edges_sh_only.share_pct_acronymkit/biomedical:.2f--> %
of everything the whole family proposes, and
93.99<!--claim:monoculture.sdu22_scientific_dev.proposals.edges_sh_only.share_pct_acronymkit/biomedical:.2f--> %
on SDU-22 scientific. **Five implementations at seven operating points, one algorithm** — the run's
`sh_family` is `abbreviation_extractor`, `abbreviations`, `pyab3p`, `scispacy` and this library at
three profiles, so three of the seven points are one codebase. All seven together reach
57.65<!--claim:monoculture.plod_all.gold.long_form.overlap.class.sh_family_recall_pct:.2f--> % of
PLOD's gold long-form spans, rising to
79.60<!--claim:monoculture.plod_all.gold.long_form.overlap.class.all_proposers_recall_pct:.2f--> %
once the two proposers that make neither Schwartz & Hearst commitment — a trivial all-caps rule and
`shapecue` — are added. And
34.98<!--claim:monoculture.plod_all.gold.long_form.overlap.class.unproposed_alignable_from_gold_short_form_pct_of_gold:.2f--> %
of gold long forms go unreached **while cleanly alignable with a gold short form in the same
passage** — they are not hard pairs, they are pairs no bracket scanner ever offers.

So a number from this family is a number about the part of the problem the family can see. A system
that reports what it cannot see is worth more to somebody governing data than a system that reports
a bigger number over the same blind spot. That is the argument, and it is measured:
`monoculture.*`, decomposed in
[docs/EVALUATION.md](EVALUATION.md#the-extraction-monoculture-and-what-it-does-to-the-corpora).

**The measurement is strong. Its strong reading was confounded with genre, and the genre half has
since been separated — against the expectation recorded here.** The tempting conclusion — that the
corpora themselves were drawn around the pool, so the benchmarks certify the blind spot — competed
with "abstracts do not contain the hard cases". MED1250 is abstracts and PLOD is article body text,
and abstracts carry no figure legends or table footnotes, which is exactly where the unproposed
class lives. Every figure above was equally consistent with both, including the control: on MED1250
the independent proposer's gain over gold is
0.00<!--claim:monoculture.med1250.gold.pairs.independent_gain_pct:.2f--> %, which is what
*provenance* predicts and also what *genre* predicts.

**CORRECTED IN PLACE, AND THE PARAGRAPH THIS REPLACES WAS WRONG WITHIN ONE ROUND OF BEING WRITTEN.**
It said separating them needed article body text whose gold was pooled from Schwartz & Hearst
descendants, that nobody publishes one on purpose, and that **"that absence is a result, not a
task"**. That was the wrong instrument, confidently named. The right one holds provenance constant
instead of varying it: each PMC Open Access article's own abstract against its own body, same
authors, same journal, same deposit route, gold taken from the article's own `<def-list>` roster
which sits in neither measured half. Gold long forms are bracket-adjacent in 84.54<!--claim:genre.pmc_oa.abstract.corpus.gold_pairs_long_form_bracket_adjacent_pct:.2f--> % of abstracts
against 75.85<!--claim:genre.pmc_oa.body.corpus.gold_pairs_long_form_bracket_adjacent_pct:.2f--> % of bodies; all six paired contrasts exclude zero and all six point the way genre
predicts. **The verdict is genre**, run ids `genre.pmc_oa.*`.

This **kills the strong reading rather than refuting it**: nothing in that instrument measures the
provenance effect on its own, only that the ordering does not require it. Reversal three is
unchanged. But the sentence calling the absence "a result, not a task" is retired, because a
workstream took it as a task and it took one round — and it is left visible here because a
*permanently unprovable* label applied to something provable is the most expensive kind of wrong
this project can write, and the reason the research-artifact positioning was rejected rested partly
on it. The rejection stands on the remaining ground: provenance itself is still unmeasured, and it
forecloses the adoption that would make the
discipline matter to anybody.

---

## The two rows that are empty, and what filling each costs

`tools/splits.py` recognises four tasks. Two of them — extraction and disambiguation — have **no
corpus that could adjudicate a headline number**. This is not a backlog item; it is a property of the
project as it is resourced, and both halves are enforced in code rather than asserted in prose:

```
$ python        # session transcript, not a benchmark measurement
>>> import sys; sys.path.insert(0, ".")
>>> import tools.splits as splits
>>> manifest = splits.load()
>>> [c.name for c in manifest.headline_capable("extraction")]
[]
>>> [c.name for c in manifest.headline_capable("disambiguation")]
[]
```

```
$ python tools/splits.py --check        # output, not a benchmark measurement
                                        # two lines quoted verbatim; the rest elided

  note: no uncontaminated corpus carries role='held_out' for task='extraction' (2 declared, 0 in that role, none eligible), so no extraction number in this project currently satisfies the headline rule
  note: no uncontaminated corpus carries role='held_out' for task='disambiguation' (1 declared, 0 in that role, none eligible), so no disambiguation number in this project currently satisfies the headline rule
```

**Read "two" with its denominator, because the denominator flatters us.** `TASKS` holds
`extraction`, `span_detection`, `disambiguation` and `identifier_segmentation`; generation and
backronym alignment are not among them, so no empty row can exist for those two and the question is
never asked. What follows is the **enforced** part of the gap and not the whole of it: generation and
backronym alignment are scored only on corpora declared tuning and contaminated — a weaker statement
than an empty row that reads like a stronger one — and extraction's held-out evidence covers
`span_detection` rather than the pairing its headline figure reports (D-048).

**Permanent is not the same as impossible, and the difference is the whole reason to state a price.**
[docs/DEFINITION-OF-DONE.md](DEFINITION-OF-DONE.md) criterion 10 records the cause as a **resource**
limit rather than a property of the task, and that verdict stands. What makes both rows standing
properties rather than emergencies is that neither resolves by anybody in this repository working
harder.

### Extraction — the instrument exists, the adjudicator does not

`tools/build_gold_corpus.py` is the pipeline. It ran, on pinned Federal Register final rules, and
produced a **single-annotator reference set** that labels itself `is_gold_standard = False`,
`scorable = False`, `headline_eligible = False`. It is registered at the role
`single_annotator_reference`, which `headline_capable()` is written to exclude for every task
unconditionally.

**Read that with its firing count.** Under the shipped `[policy] headline_requires = "held_out"` the
never-headline filter evaluates **zero times** on the corpus it was written for, because the
held-out requirement excludes it one step earlier; D-063 records that it has only ever fired in a
test. Two independent rules keep this row empty and only the outer one has ever run on real data. So
the row is empty by policy *and* by role, which is stronger than either alone and weaker than the
sentence "a mutation-tested rule says so" would have implied.

The price of promotion is four remaining conditions, in order, none optional (D-056):

1. **A second adjudicator who authored none of the pooled systems**, with agreement computed and
   published. The one adjudicator available wrote the extractor that proposed most of the pool. This
   is the binding constraint and it is a person, not an afternoon.
2. A written guideline settling long-form boundaries, contractions in legends, non-initialism defined
   terms and typesetting artefacts — because two readers with no guideline produce two golds.
3. **Exhaustive** adjudication of every pooled candidate in the documents to be scored. Not sampling.
4. An unproposed sample in the **hundreds** of items rather than the dozens the pilot could afford;
   the pilot's own verdict on itself is that it cannot distinguish a nearly complete pool from one
   missing as much as it holds.

The fifth condition — `single_annotator_reference` as a real role — is met.

### Disambiguation — the corpus exists, and spending it costs the last blind split

SDU@AAAI-21 AD `test.json` is the one genuinely blind split still available to this project. It is
fetchable from the same pin, it has deliberately never been read, and it can be spent **once**.
`tools/splits.py --check` prints it as a reserved arm, allocated under D-043 to confirming the
cut-point of an abstention policy proposed for on-by-default.

So the cost of filling the disambiguation row is not effort. It is **the only irreversible spend this
project has left, and it is already allocated to something else.** Redirecting it to a headline
accuracy number is a trade somebody would have to choose out loud, in a record, against the
abstention question it is reserved for. Nobody has.

---

## What would reverse this

Three conditions. Each names the evidence that would settle it, so that reversing is an argument
about a measurement rather than about a preference.

### Reversal one: the lead is wrong if a catalog is worth nothing on a real schema

The governance positioning rests on the governed half being the half worth leading with. **The one
measurement that bore on it used to point the other way. It has been re-run under the harness, and
it does not measure what it was read as measuring.**

The pooled result reproduces. Under a portal-disjoint split of real Socrata schemas a voted catalog
scores worse than an empty one in
79<!--claim:governed_catalog.socrata.sweep.cells_where_voted_loses_pooled:,--> of
80<!--claim:governed_catalog.socrata.sweep.cells_run:,--> catalog configurations, and the single
exception is the one cell whose catalog has no acting rows at all — the empty arm under another
name. That is the audit's finding, now gated: `governed_catalog.socrata.*`, decomposed in
[docs/EVALUATION.md](EVALUATION.md#does-a-governed-catalog-add-anything-on-a-real-schema-not-as-the-pooled-figure-asks-it),
and the un-gated original is still at
[docs/AUDIT-2026-08.md](AUDIT-2026-08.md#1-does-a-governed-catalog-add-anything-on-a-real-schema).

**The decomposition reverses the reading of it, and nobody had ever computed it.**
76.53<!--claim:governed_catalog.socrata.census.subsets.identical.pairs_pct:.2f--> % of that corpus's
distinct field/caption pairs are already unabbreviated — the caption re-cuts the identifier and
nothing else — and on those a catalog can only do damage. Only
11.31<!--claim:governed_catalog.socrata.census.live_pairs_pct:.2f--> % carry an expansion at all, and that
is the only place the question is live. Split on that line, the same runs say:

- **The whole of the pooled loss is damage to pairs that needed no catalog.** The audit-shaped
  catalog broke 97<!--claim:governed_catalog.socrata.voted.fold_ab.identical.empty_only_correct:,--> and
  283<!--claim:governed_catalog.socrata.voted.fold_ba.identical.empty_only_correct:,--> already-correct
  pairs across the two folds, and fixed
  0<!--claim:governed_catalog.socrata.voted.fold_ab.identical.voted_only_correct:,--> and
  0<!--claim:governed_catalog.socrata.voted.fold_ba.identical.voted_only_correct:,-->.
- **On the live pairs a catalog cannot lose, so the readable number is how often it wins.** The
  empty arm is zero there *by construction* — it cannot emit characters the identifier does not
  carry — so "the voted catalog loses
  0<!--claim:governed_catalog.socrata.sweep.cells_where_voted_loses_live:,--> times" is arithmetic
  and not evidence. What is evidence: it *wins* in
  51<!--claim:governed_catalog.socrata.sweep.cells_where_voted_beats_empty_live:,--> of
  80<!--claim:governed_catalog.socrata.sweep.cells_run:,--> configurations, and in the other
  29<!--claim:governed_catalog.socrata.sweep.cells_where_voted_ties_live:,--> it recovers nothing
  at all.
- **And on the atoms the empty catalog provably cannot touch, a catalog is worth something.** On the
  token positions where the identifier's token differs from the caption's word, the empty catalog is
  right 0<!--claim:governed_catalog.socrata.eager.fold_ab.abbreviated_tokens.empty_correct:,--> of
  486<!--claim:governed_catalog.socrata.eager.fold_ab.abbreviated_tokens.tokens:,--> and
  0<!--claim:governed_catalog.socrata.eager.fold_ba.abbreviated_tokens.empty_correct:,--> of
  618<!--claim:governed_catalog.socrata.eager.fold_ba.abbreviated_tokens.tokens:,--> — **a derivation and
  not a result**, because an empty catalog cannot emit characters the identifier does not carry. The
  best catalog inferable from the corpus itself is right
  12.35<!--claim:governed_catalog.socrata.eager.fold_ab.abbreviated_tokens.voted_correct_pct:.2f--> % and
  9.22<!--claim:governed_catalog.socrata.eager.fold_ba.abbreviated_tokens.voted_correct_pct:.2f--> % there.

So the pooled comparison cannot answer this question at any setting in the grid. A catalog
aggressive enough to reach the live subset moves the pairs that needed nothing by
-22.60<!--claim:governed_catalog.socrata.eager.fold_ab.identical.delta_points:.2f--> points; a catalog cautious enough to protect the pooled figure fires on
23<!--claim:governed_catalog.socrata.voted.fold_ab.live.catalog_fired_pairs:,--> of
3,276<!--claim:governed_catalog.socrata.voted.fold_ab.live.pairs:,--> live pairs and so measures nothing.
**The audit measured a catalog's cost and the record read it as a catalog's worth.**

**What that does to the commitment: it removes the evidence pointing against the lead, and supplies
none for it.** The adversary's own reason for refusing to assert the original figure as a result
stands unchanged and now cuts both ways — Socrata display labels are a noisy gold,
`':@computed_region_92fq_4b7q'` is captioned `'City Council Districts 2'`, and
82.86<!--claim:governed_catalog.socrata.census.token_word_count_mismatch_pct:.2f--> % of the
non-identical pairs have a token count that does not match the caption's word count. Every catalog
scored above is still inferred by the harness from labels of the kind being scored, which is
circular by construction; the portal-disjoint split moves that circularity from the pair to the
corpus and does not remove it.

**What would settle it:** unchanged, and more urgent rather than less. One real proprietary glossary
measured against the schema it governs, catalog against empty catalog, on gold the auditor did not
infer from the labels being scored — and **decomposed on the already-unabbreviated line above rather
than pooled**, because a pooled figure on a real schema will be dominated by the same population and
will be just as unreadable. If a catalog adds essentially nothing *on the live subset there*, this
subsystem's value is provenance and compliance — the entry id, the source, the rule that fired, the
unknown-token worklist — and **not** expansion accuracy, and the README has to say so and lead with
something else.

### Reversal two: adoption-seeking unblocks the day adoption becomes legible

Adoption-seeking was not rejected for being hard. It was rejected because **its success metric is
unreadable**: a download counter cannot distinguish a human from a scanner, for any package on any
index, so a positioning whose progress no instrument can read is not a plan. This project has no
better instrument and did not invent one.

**What would settle it:** evidence that names a person or a repository. An issue or a pull request
from somebody who did not author this library; a public downstream dependent; a bug report that could
only come from having passed a real dictionary to `disambiguate`. Any one of those is an instrument.
A download count is not, and no threshold on one will be accepted as this condition being met.

### Reversal three: the research artifact stops resting on an unprovable claim

If a corpus of article body text whose gold was pooled from Schwartz & Hearst descendants ever
appears, `bench/run_monoculture.py` runs against it unchanged, and the provenance reading either
survives or dies on that corpus. If it survives, the research-artifact positioning has the empirical
spine it currently lacks and deserves a fresh hearing — with the confound paragraph above deleted
rather than argued around.

**What would settle it:** that corpus, and the run. Not a stronger argument about the corpora that
already exist.

---

## Where this file lives, and why

In `docs/`, and the reason is mechanical rather than aesthetic.

`tools/check_claims.py`'s `SCAN_GLOBS` names seven patterns: `README.md`, `CHANGELOG.md`,
`docs/*.md`, `docs/notes/*.md`, `src/acronymkit/*.py`, `src/acronymkit/**/*.py` and
`bench/splits.toml`. **A root-level `POSITIONING.md`
would be in none of them** — the gate would never read it, and a positioning statement is exactly the
document most likely to acquire a flattering figure that nothing checks. Here, every number in prose
cites a run id from its first line, because a file absent from the deferred ledger admits zero
uncited armed numbers. `MANIFEST.in`'s `recursive-include docs *.md` ships it in the sdist, so a
reader holding a distribution rather than a checkout gets it too. `README.md` links it from the first
screen, which is the part that makes it findable.

### What that gate can and cannot see on this page, demonstrated rather than asserted

R11 says a gate must be shown capable of failing where it runs. Six runs of
`python tools/check_claims.py`, one mutation at a time, against this file:

```
python tools/check_claims.py, six runs -- one mutation applied to this file each time, the
gate run, the file restored from bytes read before the first mutation and md5-verified.
CPython 3.13.4 on win32; command output, not a benchmark measurement. The line numbers are
the mutated file's and move with any edit to this page; rc and "is the file named" do not.

  rc=0  control, unmutated                                            <file not named>
  rc=1  A  a cited value edited: 93.55 -> 99.99                       docs/POSITIONING.md:129
  rc=1  B  that citation repointed at run id monoculture.nope.*       docs/POSITIONING.md:129
  rc=1  C  prose line added: "... accuracy reached 99.94 % ..."       docs/POSITIONING.md:70
  rc=0  D  prose line added: "Median latency ... 41 microseconds"     <file not named>
  rc=0  E  "(2 declared" -> "(9 declared" inside the fenced block above   <file not named>
```

**A, B and C are the gate working**: a wrong value, a dead run id and a bare accuracy percentage all
turn the build red and name the line. **D and E are the two holes, and they are in this page's own
floor.** `latency` is not in the gate's arming vocabulary and a spelled-out `microseconds` is not in
its unit vocabulary, so an invented latency claim on this page would never be seen — the blind spot
`docs/DECISIONS.md` D-060 found in `README.md`, reproduced here rather than carried on that record's
word. And the two fenced blocks above are outside the gate entirely, which D-052 says is
mechanically indistinguishable from hiding: the command is printed with each one so that a reader
can re-derive it, and that convention is the only thing separating them.

**One consequence, reported here and closed by the next reader:** `docs/SECOND-READER.md`'s
trigger-B rotation was a fixed list of fourteen files and this was not one of them, so the rotation
could never have served this page. That file was not this workstream's to edit. The cold read of
2026-08-25 appended it, and the rotation now runs to fifteen — a positioning statement nobody
re-reads is how a commitment becomes a slogan.

---

## How this fails

**A positioning statement is prose, and no gate in this repository can read a sentence.**
`tools/check_claims.py` adjudicates the numbers on this page and nothing adjudicates the argument
between them. The claim that the governed half "has no competitor" is a reading of a four-row table
somebody assembled by hand; the claim that refusal is worth more than a higher F1 is a judgement
about users this project has never measured. Both are the number-free assertion class
`docs/SECOND-READER.md` exists for, and both are unguarded by construction.

**The lead was chosen before its central question was answered, and it is still not answered.** The
commitment above says the governed half is what this library is for. The one measurement that
appeared to contradict it has been re-run and decomposed, and it turns out to have measured what a
catalog *costs* on the pairs that need no catalog rather than what a catalog is *worth* — so the
contradiction is gone and the evidence is not. What replaced it is a floor: on the token positions
an empty catalog provably cannot reach, the best catalog this project can build from public data
recovers about a tenth of them, and every one of those catalogs is inferred from labels of the kind
being scored. Reversal one carries the figures. A reader who says the positioning rests on a
question nobody has answered is reading this correctly, and the honest change since the last
revision of this page is that the question is now open rather than answered against us.

**Two of the three reversal conditions cannot be triggered by anybody working on this repository.**
Reversal one needs an organisation and reversal three needs a corpus nobody publishes. A reversal
condition only an outsider can fire is a weaker commitment device than it looks, and the one under
this project's own control — reversal two — is satisfied by a single stranger opening a single
issue, which makes it the loosest of the three.

**"Nobody optimises extraction again" is a promise about future behaviour with no mechanism behind
it.** Nothing turns red if a later round tunes the extractor and publishes a better F1. The gates can
check that the number is cited; they cannot check that the project stopped caring about it.

**And the monoculture argument is being used one step past where it was measured.** `monoculture.*`
measures what a family of extractors proposes and what gold it reaches. It does not measure that
anybody prefers a refusal to a guess, or that a governed caller is better served by an unknown than
by a best effort. The refusal argument above asserts the bridge between those two things in one
sentence, and that sentence is the load-bearing one on this page.

---

**See also:** [`README.md`](../README.md) · [`docs/EVALUATION.md`](EVALUATION.md) — the measured
numbers, each with its losing comparison · [`docs/DEFINITION-OF-DONE.md`](DEFINITION-OF-DONE.md) — the
fourteen criteria and which are open · [`docs/DECISIONS.md`](DECISIONS.md) — what was tried and
rejected, newest first · [`docs/AUDIT-2026-08.md`](AUDIT-2026-08.md) — the audit, and the section on
what did not survive it.
