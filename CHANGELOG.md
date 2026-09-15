# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.4.0] — 2026-09-15

Three mandates' work. **Three breaking changes — two in the governed naming subsystem, one in the
capability report — and the change that sounds breaking is not one.** Read the three bullets below,
the paragraph after them, and the known-open defects under that, before you upgrade; everything else
in this section is additive, opt-in, or documentation.

**The three breaking changes.** This paragraph said *two* until the tag, counting only the
governed-naming pair while a third change carried its own `BREAKING` label two screens down under
**Removed** — so the first screen contradicted the section, and it did so in the direction of
**understating** what breaks, which is the harder error to catch by reading and the worse one to
ship. Corrected here rather than in the next release. `docs/DECISIONS.md` D-142 F-1.

- **BREAKING: `catalog.normalize` raises `TokenizationError` where it returned a `str`.** A name
  holding a character that belongs to no token and to none of the accounted separators is refused,
  rather than handed back with the character deleted:
  `normalize('TXN_©_ID', GovernedDictionary({}))` returned `'TXN_ID'` and `normalize('㎡', ...)`
  returned `''`, a token gone and then a whole name gone, with no signal either time. **Who this
  reaches, measured on two real corpora before the design was chosen:** `0.4664` % of distinct
  Socrata field names and `0.0000` % of distinct SEC XBRL element names; per row rather than per
  distinct value the Socrata figure is `1.3145` %, and every hit is the portal's own
  `:@computed_region_…` family. **Two public pre-checks do not raise** — `is_compliant`, which
  returns the finding, and `split_identifier_parts`, which returns the accounting. Full entry under
  **Changed**.
- **BREAKING: `is_compliant` reports `UNREADABLE_CHARACTER` and stops offering a `fix` that would
  delete one.** The new whole-name `FAIL` finding carries `token=None` and **no** `fix`, and the
  `fix` is suppressed on the three whole-name reason codes that would otherwise have carried the
  deletion: `NOT_UPPER_SNAKE` used to answer `TXN_©_ID` with `fix='TXN_ID'`, which is a
  machine-readable instruction to delete part of a name nobody approved. `compliant` never changes
  value. Breaking if you exhaustively match the code set, or consume a whole-name finding's `fix`
  without checking for `unreadable_character` first. Full entry under **Changed**.
- **BREAKING for anyone who asserts on the capability report's key set: `data_packs` is gone.**
  `capabilities()` no longer returns a `data_packs` key, `acronymkit doctor --format json` no longer
  emits `.data_packs`, the text `doctor` report loses its `data packs : none` line, and
  `acronymkit.diagnostics.DATA_PACK_GROUP` no longer exists. **What you lose is nothing that ever
  worked** — `acronymkit.data` was declared as an entry-point group that no code in this library has
  ever loaded through, so the key could only ever report an empty list. It is a break anyway: "the
  value was always `[]`" is a reason the break is cheap, not a reason it is not a break, and a
  pipeline doing an exact key-set comparison fails on upgrade. `acronymkit.__all__` is unchanged --
  the constant was never a top-level export. Full entry under **Removed**.

**And the change that sounds breaking and is not: the package is split into three.**
`acronymkit.core`, `acronymkit.nlp` and `acronymkit.catalog`. **All `19` pre-split import paths
still work and resolve to the SAME OBJECTS** — identity, not equality — and they are kept **for the
whole of the `0.x` line**: removal needs a major version, and a `DeprecationWarning` announced a
minor release ahead of it. No warning is emitted today, deliberately. Every output is
byte-identical. What *did* move is `__module__` on every moved class, so an uncaught traceback now
prints `acronymkit.core.exceptions.ConfigurationError`; if you match on that string, read the full
entry under **Changed**.

**KNOWN-OPEN DEFECTS IN `0.4.0`.** They are listed here rather than only in `docs/`, because a
reader of a release must be able to find what is known-broken without reading the source. Each has
its full entry below, under **Notes** unless said otherwise.

- **`loaders._read_pairs` silently drops rows, and it is the shallowest defect in this list.**
  A CSV row whose key or whose value is blank is skipped with no warning, no count and **no member on
  the returned `GovernedDictionary` saying anything was dropped**: a five-data-row file with one
  blank-key row and one blank-value row loads as `3` entries and `0` warnings. It serves all three
  CSV entry points — `load_csv`, `load_long_to_short_csv` and `load_term_index_csv`. **Not fixed in
  this release**, and it is listed first because the five defects under it are reached by a caller who
  is already deep in the governed subsystem tuning thresholds or auditing a proof, while this one is
  reached by loading a CSV, which is the first thing somebody building a governed catalog does. A
  defect list that discloses the deep ones and omits the shallow one is ordered backwards, and this
  section shipped that way until the tag. Unlike the two Unicode defects below, **no incidence figure
  is attached** — nobody has measured how many callers reach these loaders, so the rank above is an
  argument and not a measurement. `docs/DECISIONS.md` D-139 item `7`, `docs/DEFINITION-OF-DONE.md`
  criterion `7`.
- **The two halves of the governed round trip disagree on `26` code points, and one of them reports
  that nothing was lost.** `to_physical_name()` emits, for those `26`, a physical name that
  `normalize()` then refuses to read back — `str.upper()` returns a base letter plus a combining
  mark, and a combining mark is a character no governed token can hold — while reporting
  `unaccounted=()`. **Not fixed in this release.** Pinned by a strict `xfail` plus positive tests,
  so a partial repair reddens rather than passes, and its incidence is `0` across the `285,839`
  distinct strings in the two published governed corpora.
- **`1,050` code points break `normalize` idempotence, and that count is a property of your
  interpreter rather than of this library.** `º` and its relatives stay lower-case under
  `str.upper()`, which manufactures a camelCase boundary the splitter then places on the second
  pass. No character is lost, so refusing would refuse a name that lost nothing. The class size
  moves with the Unicode data your interpreter carries — `890` at Unicode `13.0`, `977` at `14.0`,
  `1050` at `15.0` and `15.1`, `1048` at `16.0`, so it grows and then shrinks — while the `26` above
  are `26` at all five. The two classes are disjoint and their union is `1,076` on Unicode `15.1`.
  Also not fixed, pinned the same way.
- **A2's `5.95` x coverage multiple is withdrawn as a claim about scored data.** The scored gain is
  `+3.07` short-form exact recall points on PLOD-CW against a pre-registration that required ten,
  and the multiple survives only as an occurrence count on PMC-OA. No corpus in this project can
  score a document-scoped rule at article scope. See the `propagate()` entry under **Added**.
- **Selective risk certifies on MED1250 and refuses on SDU-21**, and the refusal is published rather
  than footnoted. `selective=` is a second bound beside the existing joint one and tightens nothing.
  On SDU-21 AD dev not one of `21` candidate thresholds certifies at any of six alphas, and the
  cause is not a small calibration set but a floor in the selection family — `17.53` % — which more
  data will not move. See the `selective=` entry under **Added**.
- **Both headline rows are still empty.** `python tools/splits.py --check` reports, per task, that
  this project has **no** uncontaminated held-out corpus for extraction and none for
  disambiguation — the two tasks the library leads with. The flagship extraction figure is a tuning
  figure and every page that prints it says so.
- **The byte-identity proof behind the package split cannot be re-run from this repository.** The
  harness that produced the `3,619,227`-record comparison is not committed and the two governed
  corpora are not distributed with the package, so the strongest claim this release makes about the
  split rests on one party's word. **Three consecutive parties have now been unable to reproduce it**,
  the release's cold read being the third.

**What else to read before upgrading.** **Positioning** changes no code and is the most important
entry this project has written: what this library says it is for has changed, and if you adopted it
for something else you should know that before the next release. **Removed** carries the third
breaking change in full — the one summarised in the third bullet at the top of this section.
**Changed** also carries three reports that get *stricter* rather than different — one will newly
flag identifiers a pipeline previously waved through, and one changes what a digit run resolves to —
and one entry that makes governed expansion substantially faster while proving, over millions of
records, that not one byte of output moved.

**And if you are here to decide whether a governed catalog is worth building**, read the entry under
**Documentation** headed *what a governed catalog is worth on a real schema*. It is the only
measurement anybody has of that question and it says less than its headline sounds like it says.

**And A2 shipped.** `acronymkit.propagation.propagate()` extends a confirmed definition across a
document, opt-in, changing no output you already had — see the `propagate()` entry under **Added**, which
also says what it is worth on the one corpus that can score it and why that is less than the round
that commissioned it expected.

**If you call `expand_identifier` in a hot loop, or you were hoping for a second-opinion verifier
on `extract()`**, the first three **Documentation** entries are the ones for you. Neither changes
any behaviour; both change what you should expect next.

### Positioning

- **`acronymkit` is now stated to be a governance instrument, and the governed half leads.** No code
  changed and no output moved. What changed is the answer to *what is this library for*, and it is
  now written down in one place — [`docs/POSITIONING.md`](docs/POSITIONING.md) — with the reasoning,
  what the choice costs, and the evidence that would reverse it.
  - **The subject this library is built around is a name somebody else owns**: a schema column, a
    data-standard identifier, a token from a vocabulary you supply and it may not extend. Its first
    obligation on that subject is to report *unknown* rather than return a plausible answer.
  - **What still ships:** everything. Generation, backronym synthesis and alignment, extraction and
    contextual disambiguation are all still here, still supported, still measured wherever they can
    be measured at all. None of them is deprecated and none is going away. What changed is which one
    the front page leads with and which numbers are presented as headline versus supporting.
  - **If you use this library for extraction or generation**, nothing breaks, but read this: the
    extraction F1 on MED1250 is now presented as a *supporting* number, third of five, with the two
    compiled systems that beat it named on the front page. That was always true; it was not always
    said in the first paragraph. Nobody on this project is going to tune it further.
  - **If you are evaluating the governed subsystem**, read the honest-scope list in the README first.
    The most important sentence there is new: **every published governed accuracy figure was measured
    with an empty catalog.** Those numbers say where an identifier gets cut. They say nothing about
    what a governed vocabulary is worth on a real schema, because no real proprietary glossary has
    ever been measured here.
  - **Three sentences are retired** and are quoted verbatim in the positioning page so the retirement
    is auditable: the old README tagline, the *"missing single library"* conclusion under the `## Why`
    table, and the old `pyproject.toml` `description` — the line PyPI shows, which led with generation
    and did not mention governance at all. The comparison table under `## Why` is accurate and stays;
    what it concludes changed.
  - **How to change this project's mind.** Three reversal conditions ship, each naming the evidence
    that fires it, and one of them is aimed at you: **an issue, a pull request or a bug report from
    somebody who did not author this library counts as evidence and a download count does not.** If
    you are using this and the positioning is wrong for your case, saying so in the issue tracker is
    the mechanism.
  - `docs/DECISIONS.md` D-070 records the decision, its four named costs and its three reversal
    conditions.

### Removed

- **BREAKING for anyone who asserts on the capability report's key set: `data_packs` is gone.**
  `capabilities()` no longer returns a `data_packs` key, `acronymkit doctor --format json` no longer
  emits `.data_packs`, the text `doctor` report loses its `data packs : none` line, and
  `acronymkit.diagnostics.DATA_PACK_GROUP` no longer exists. `acronymkit.__all__` is unchanged — the
  constant was never a top-level export.
  - **What you lose:** nothing that ever worked. `acronymkit.data` was declared as an entry-point
    group and no code in this library has ever loaded anything through it, so the key could only ever
    report an empty list. If you published a distribution declaring that group, it was never
    discovered and is not discovered now.
  - **Why it is still called breaking:** "the value was always `[]`" is a reason the break is cheap,
    not a reason it is not a break. A pipeline doing an exact key-set comparison against the report
    will fail on upgrade. `capabilities()` previously promised only that an existing key would not
    *change meaning* under a patch release; that docstring now also says a key may be **removed**, and
    that removal is a minor-release event. `docs/DECISIONS.md` D-038.

### Added

- **`selective=` on `propagate()`, and `acronymkit.core.selective` behind it — a refusal you can put
  a number on, and the number is about the answers rather than about everything.** Opt-in, off by
  default, and byte-identical when you do not pass it. The existing `gate=` bounds the **joint**
  rate — how often the library *answers and is wrong* out of everything it sees — and it does
  **not** bound how often it is wrong among the things it answers. That gap is a factor of `4.38` at
  `alpha=0.05`, and the joint bound is unchanged by this release. A
  `SelectiveRiskGate`, calibrated by Learn-Then-Test over your own labelled occurrences, bounds the
  second quantity directly. Both parameters can be set; they are two bounds side by side and the new
  one does **not** tighten the old one.
  - **Read the answer rate before you read the bound, because a gate that answers nothing satisfies
    any bound.** Every certificate carries its answer rate and the runtime `guarantee()` string
    states both. On MED1250, at `alpha=0.05` a pooled gate answers
    `99.95` % of held-out occurrences and is wrong on `2.38` % of them, which is `0.4754` times
    `alpha`. At `alpha=0.01` and `0.02` **nothing certifies and the gate answers `0.00` %.**
  - **On the corpus the `4.38` gap was measured on, the method refuses, and that is published rather
    than footnoted.** On SDU-21 AD dev not one of the `21` candidate thresholds certifies at any of
    six alphas from `0.01` to `0.20`. The reason is not a small calibration set (`3,094` units): the
    lowest selective risk *any* threshold can reach there is `17.53` %, over a base disambiguator
    that is `40.82` % accurate when it answers everything. More data will not move that. **If your
    data looks like SDU-21, this parameter will decline to give you a gate rather than give you a
    loose one.**
  - **A certificate that fails is an object, not an exception.** `StratumCertificate` carries its
    p-value, the accepted count, the required count at zero losses, and a refusal string. Three
    refusal codes are raised at the `propagate()` seam, and an uncertified stratum **refuses
    everything in that stratum** rather than quietly falling back to a pooled threshold.
  - **What it is conditional on, stated where the guarantee is stated.** Exchangeability between your
    calibration occurrences and the ones you will score; a `0`/`1` loss (a graded loss is refused
    rather than served, because the binomial argument does not apply to one); and the fact that
    document-level gold cannot see a within-document sense shift, so the loss being bounded is the
    *observable* one. All figures above are from a `role=tuning`, `contaminated=true` corpus and none
    is evidence of generalisation.
  - **Stratifying by extraction mode was measured and is not recommended.** It costs `21.82` points
    of answer rate — `78.13` % against `99.95` % — and separates no risk, because under one pooled
    threshold both inline and propagated occurrences are already under `alpha`. Stratifying by
    *arity*, which the conformal gate already does, still helps. `docs/DECISIONS.md` D-128.

- **`acronymkit.propagation.propagate()` — one definition licenses the rest of the document, and it
  is opt-in.** A2 ships. Give it the text and the pairs `extract()` returned and it commits to the
  **first** definition of each short form in document order, then licenses every whole-token
  occurrence of that short form at or after it. Nothing else in the library calls it: no engine, no
  `Config` field and no default path, so upgrading changes no output you already had.
  - **Not a breaking change, and that was checked rather than reasoned about.** Every field of every
    `AcronymPair` the default path returns, over every document of every corpus `bench.corpora` can
    read — `4,260` documents at three extraction profiles, `10,625` pairs — digests identically at
    `017cb37` and on this tree, while a control that changes one character of one long form digests
    differently. The pass is quoted in
    [`docs/EVALUATION.md`](docs/EVALUATION.md#not-breaking-and-the-byte-identity-pass-that-says-so).
  - **What it buys, on the only corpus that can score it.** Short-form span exact recall on PLOD-CW
    moves from `36.53<!--claim:spans.plod.all.tight.acronymkit.high_precision.native.short_form.exact_recall:.2f-->` %
    to `39.60<!--claim:spans.plod.all.tight.acronymkit.high_precision.propagated.short_form.exact_recall:.2f-->` %
    at `HIGH_PRECISION`. **Precision holds in that cell and does not hold everywhere, and the
    narrower sentence is the true one:**
    `93.66<!--claim:spans.plod.all.tight.acronymkit.high_precision.native.short_form.exact_precision:.2f-->` %
    to `93.73<!--claim:spans.plod.all.tight.acronymkit.high_precision.propagated.short_form.exact_precision:.2f-->` %
    on the `tight` arm, where propagation gains up to `0.21` points — while on the `spaced` arm it
    costs up to `0.29`. It adds false positives in all six profile-by-convention cells; precision
    holds in the `tight` arm only because true positives grow faster.
    That is `88<!--claim:spans.plod.all.tight.acronymkit.high_precision.propagated.short_form.exact_true_positives_new_from_propagation:,-->`
    gold spans reached that were not reached before, and `0<!--claim:spans.plod.all.tight.acronymkit.high_precision.propagated.short_form.exact_true_positives_lost_versus_definitions:,-->`
    lost. **It is three points and the round pre-registered ten**, so the coverage multiple this was
    commissioned on is withdrawn as a claim about scored data — see the evaluation section.
  - **It cannot move any published extraction figure**, and both halves of that were run rather than
    argued. MED1250 scores definitions and de-duplicates repeated pairs before scoring, so
    `extraction.med1250.acronymkit_propagated` agrees with `extraction.med1250.acronymkit` on every
    compared field; and both committed figures re-render byte-identical.
  - **The optional `gate=` argument takes a `ConformalGate`, and read what it bounds before you trust
    it.** It gates the *definition*, and what it buys there is a **joint** bound: on answering and
    being wrong across all instances, the refused ones included. It does not bound the share of the
    gate's answers that are wrong, which is that rate divided by the answer rate and was measured at
    up to `4.38` times `alpha` on `conformal.sdu21.exchangeable` — the multiple at the tightest of
    five alphas, falling to `0.97` at the loosest, so the overshoot is worst where a caller would
    set it. Nor does anything it says reach the
    occurrences the definition licenses — that step is one-sense-per-discourse, priced between
    `0.581<!--claim:one_sense.pmc_oa.a2.high_precision.wrong_floor_correctness_pct_of_licensed:.3f-->` %
    and `9.68<!--claim:one_sense.pmc_oa.a2.high_precision.wrong_ceiling_correctness_pct_of_licensed:.2f-->` %
    of licensed occurrences and held by no conformal argument at all.
    `acronymkit.propagation.gate_disclosure(gate)` returns the guarantee, that gap and the second one
    in a single string, because the three are only honest together.
  - **`acronymkit.conformal` is reachable as a package attribute again.** It shipped last round
    without being added to the lazy submodule table, so `import acronymkit; acronymkit.conformal`
    raised `AttributeError` while `from acronymkit import conformal` worked. Both work now. Nothing
    asserts that table is complete against the package directory, which is how a whole module went
    missing from it silently.


- **`acronymkit governed-gap` — point it at a schema and it tells you what a catalog would have to
  cover, without a catalog.** It reads the same `identifier,label` CSV
  [`tools/byoc_eval.py`](tools/byoc_eval.py) reads, tokenises every identifier, and reports which
  tokens a governed vocabulary would have to define before this library could expand the column at
  all — with each unreachable column attributed to the tokens that made it unreachable. Text or
  `--format json`. **It is the only governed command where `--dictionary` is optional**, because what
  it reports is derived without a vocabulary. The same thing is available as
  `acronymkit.governed.catalog_gap` and `render_gap`.
  - **Read the two lines above the table before acting on the table.** On the public Socrata
    catalog — `69,682<!--claim:catalog_gap.socrata.census.columns:,-->` columns — the top
    `20<!--claim:catalog_gap.socrata.census.head_size:,-->` tokens cover
    `55.55<!--claim:catalog_gap.socrata.census.head_coverage_pct:.2f-->` % of the columns that carry a
    work item, **and `15<!--claim:catalog_gap.socrata.census.head_single_character:,-->` of those `20`
    tokens are single characters.** They are fragments of machine-generated identifiers and no catalog
    row would fix one. `--min-token-length 2 --require-letter` gives you a head you can act on and
    costs a great deal: coverage drops to
    `22.30<!--claim:catalog_gap.socrata.letters_min2.head_coverage_pct:.2f-->` % and the share of the
    gap with no work item at all rises from
    `24.32<!--claim:catalog_gap.socrata.census.unattributed_pct:.2f-->` % to
    `56.86<!--claim:catalog_gap.socrata.letters_min2.unattributed_pct:.2f-->` %. **Both filters are
    off by default, so the default output is the noisy one.**
  - **It needs labels and will say so.** A schema with no human wording gets a token count and
    nothing else. The obvious label-free shortcut — treat a token as an abbreviation if it is not in
    the shipped English word list — was measured first and is wrong about
    `77.87<!--claim:catalog_gap.socrata.word_list_control.false_positive_pct:.2f-->` % of what it
    flags, so no word list is consulted.
  - It changes no expansion: the same corpus expands byte-identically before and after, checked over
    `155,272<!--claim:catalog_gap.socrata.identity.records:,-->` records with a positive control.

- **`ConformalGate` — a refusal rule with a stated guarantee, off by default and shipped with the
  sentence it does *not* license.** `acronymkit.conformal.ConformalGate` calibrates on your own
  labelled examples and hands `LexicalDisambiguator` a `calibration=` argument; with it absent, the
  default path is byte-identical to before.
  - **The guarantee is on the joint rate of answering-and-being-wrong, not on the error rate among
    the answers, and the difference is a factor of four.** At `alpha = 0.05` the joint rate measured
    `2.07<!--claim:conformal.sdu21.exchangeable.mondrian_by_arity.alpha_0.05.joint_answered_and_wrong_pct:.2f-->`
    % against its `5.00` % bound — and
    `21.92<!--claim:conformal.sdu21.exchangeable.mondrian_by_arity.alpha_0.05.selective_error_pct:.2f-->`
    % of the answers it gave were wrong. **If you read "at most one answer in twenty is wrong", that
    is the sentence this ships to stop you writing.** `guarantee()` returns it in prose.
  - **Calibrate per candidate-set size.** Pooled calibration hits its overall target while missing
    inside every bucket; per-arity calibration cuts the worst bucket's deviation from
    `32.54<!--claim:conformal.sdu21.exchangeable.mondrian_vs_marginal.alpha_0.05.marginal_worst_arity_gap_points:.2f-->`
    points to
    `2.34<!--claim:conformal.sdu21.exchangeable.mondrian_vs_marginal.alpha_0.05.mondrian_worst_arity_gap_points:.2f-->`
    and answers far more often. Pass `group_by="arity"`.
  - **It answers rarely and it is not free accuracy.** At `alpha = 0.05` it answered
    `9.43<!--claim:conformal.sdu21.exchangeable.mondrian_vs_marginal.alpha_0.05.mondrian_answer_rate_pct:.2f-->`
    % of instances. At a matched answer rate it is a wash against the existing `min_margin` gate. It
    guarantees a property; it does not improve a score. And every figure above is on a split this
    project declares contaminated and reserved for tuning.
  - Stdlib only; refuses a calibration set too small for the `alpha` you asked for, and names which
    group was short.

- **The extractor can read `SF = Long Form` legend definitions, and it is off by default.**
  `AbbreviationExtractor(config, legend_syntax=True)` also scans for definitions introduced by an
  equals sign rather than by a bracket — `GEF = Global Environment Facility` — which no previous
  version has ever read. Pairs from that arrangement carry `pattern="short=long"`, a third value your
  consumer has not seen before. Reach it with
  `AcronymEngine(config, extractor=AbbreviationExtractor(config, legend_syntax=True))`; there is no
  `Config` field for it.
  - **The default output is byte-identical to the previous release.** A test asserts that the flag
    only ever *adds* pairs: strip the legend pairs back out and what remains matches the default path
    pair for pair and span for span.
  - **Why it is off.** On the two corpora where it helps, it is worth several F1 points on both
    labels — and those are the two corpora whose miss taxonomy is what suggested the rule in the first
    place. The independent corpora either cannot show the effect at all or contain twelve instances of
    it. `X = Y` is also the surface of every equation, assignment and config line, and no source-code
    or configuration corpus was measured. Turn it on for institutional or academic prose where you
    know legends are used; do not turn it on for arbitrary text. `docs/DECISIONS.md` D-039 has the
    decomposed tables including every row where precision falls.
  - **What it costs you depends on which profile you run, and the worst case is `BIOMEDICAL`.** The
    cost is now measured on both corpora that can show it, for all three shipped profiles, and
    published in `docs/EVALUATION.md`. Short version for someone deciding: on institutional prose the
    flag improves precision as well as recall; on scientific paper text it costs a little precision
    under `HIGH_PRECISION` and `GENERAL`, and about two points of short-form precision under
    `BIOMEDICAL`, which is the only shipped profile that will accept a one-character short form with
    no uppercase requirement and is therefore the only one that will read part of an equation as a
    definition. No F1 fell in any of the six runs. If you turn this flag on, the profile you pair it
    with is part of the decision. `docs/DECISIONS.md` D-045.

- **The disambiguator can now refuse to answer.** Every `DisambiguationResult` carries a read-only
  `margin` (the gap between the best and second-best candidate's scores, `None` when there are fewer
  than two candidates) and a derived `abstained` flag, which separates "refused" from "nothing was
  ever proposed". `LexicalDisambiguator(config, dictionary, tokenizer, min_margin=0.1)` answers only
  when the margin clears the threshold you set. **It is off by default and will stay off**: gating
  trades coverage for precision, and where you want to sit on that trade depends on what a wrong
  answer costs you, which this library cannot see. Read `docs/DECISIONS.md` D-030 before choosing a
  threshold — in particular the part where, below the crossover point, the shared task's own trivial
  baseline is *more* accurate on the same answered questions. Abstention is a precision instrument,
  not an accuracy fix.
  - Practical note: the margin is only meaningful when you supply a dictionary. On the default
    no-dictionary path the engine almost never has two candidates to compare, so nothing to gate.
  - A gate above 0.01 would otherwise have refused a document's own inline definition of its own
    abbreviation, because dictionary candidates are capped just below inline ones and the cap is not
    evidence. Pairs whose top two candidates come from different sources are exempt; the exemption
    can only turn a refusal into an answer.

- **You can now supply your own collaborators to `AcronymEngine`.** Four keyword-only arguments:
  `AcronymEngine(config, backend=..., tokenizer=..., extractor=..., scorer=...)`. The README has
  advertised "implement the `NlpBackend` protocol" since 0.1.0 and there was no way to pass one in;
  now there is. `NlpBackend` is a public export (`acronymkit.NlpBackend`). Plain constructor wiring —
  no plugin registry, no entry-point scan, nothing new at import time.
  - Supplying a backend *replaces* tier resolution rather than its result: availability is not
    probed, no degradation warning is raised, and `Config(strict=True)` does not apply, because
    handing the engine an annotator is itself the availability decision. `engine_tier` is recomputed
    from the backend you passed while `requested_tier` is preserved, so the metadata still says both
    what was asked for and what ran.
  - **The thread-safety guarantee is now conditional and says so.** It held because the engine built
    everything it held; an object you inject may carry state the engine cannot inspect. Inject
    nothing and the unconditional guarantee stands.
  - **A custom `Scorer` re-ranks; it does not re-search.** The generator's beam bound is derived in
    closed form from `ScoringWeights` and never calls your scorer, so a custom term reorders the
    candidates the search kept and cannot make it keep different ones. `metadata.truncated` tells you
    when that limit bound your result. If you need a custom objective to be decisive, raise
    `max_search_nodes` until the search runs exhaustively — that removes the cut rather than biasing
    it. Documented in full on `Scorer` and in `docs/ARCHITECTURE.md`.

- **The governed subsystem has an accuracy number for the first time.** `bench/run_governed_gold.py`
  scores identifier segmentation against two public sources that publish, for the same column, both a
  machine identifier and a human caption written by the same organisation — SEC XBRL taxonomy and
  filer labels, and Socrata open-data portal captions. Results are decomposed by gold author, by
  identifier shape and by caption length in `docs/EVALUATION.md`, with the recall ceiling printed in
  the same table as the recall it bounds and the worst row printed beside the headline. Read the
  caveats: the SEC arms measure inverting a documented naming convention, the gold contains no
  UPPER_SNAKE identifiers at all, and the Socrata catalog is live rather than frozen. No library
  behaviour changed as a result.

- **A `--spans` mode on `bench/run_shortform.py`**, which scores short-form and long-form span
  detection on the corpora that annotate spans without pairing them, each on its own task and with no
  derived pairing.

### Changed

- **The package is split at the lexer contract seam: `acronymkit.core`, `acronymkit.nlp`,
  `acronymkit.catalog`. NOT BREAKING — every existing import path still works and resolves to the
  same objects.** No behaviour changed, and that is verified rather than asserted, below.
  - **Why.** This library contains two tokenizers whose contracts are irreconcilable. Prose
    tokenisation treats punctuation as a clause boundary, leans on whitespace, extracts
    parentheticals from running morphology and NFKC-normalises what is left. Identifier
    tokenisation operates on rigid boundaries, treats `#`, `%`, `_`, `:` and `/` as *semantic
    tokens*, enforces physical column constraints, and may never lose a character. Each destroys
    the other's input — `docs/DECISIONS.md`'s B1 finding measures character loss on `14.6560` % of
    distinct Socrata captions and `36.0072` % of distinct SEC XBRL labels. **Neither figure is
    gated**: both live in fenced blocks, which `tools/check_claims.py` cannot read, and no run id
    in `bench/results.json` backs them. Stated here rather than left for a reader to discover.
  - **The shape.** `acronymkit.core` is a leaf — conformal risk arithmetic, the exception
    hierarchy, immutable span coordinates, with **no regular expression, no lexical asset and no
    string normalisation** anywhere in it, checked off the syntax tree rather than claimed in a
    docstring. `acronymkit.nlp` holds chunking, candidate extraction, parenthetical matching and
    document-scope propagation. `acronymkit.catalog` holds identifier tokenisation, symbol
    handling, casing decomposition, `to_physical_name` and dictionary conformance. **`catalog`
    never imports `nlp`, `nlp` never imports `catalog`, `core` imports neither** — enforced by an
    AST import-boundary rule registered as `gates.architecture_boundaries`.
  - **Every old path is kept, and returns the SAME OBJECTS.** `acronymkit.governed` and all
    thirteen of its submodules, `acronymkit.extractor`, `acronymkit.propagation`,
    `acronymkit.tokenizer`, `acronymkit.exceptions` and `acronymkit.conformal` all still import.
    Identity, not equality: `acronymkit.governed.expand_identifier is
    acronymkit.catalog.expand_identifier`, and `acronymkit.governed.tokenizer is
    acronymkit.catalog.tokenizer`. A shim that rebound names to fresh classes would satisfy every
    equality assertion in the suite and fail the first time somebody wrote `except` or `isinstance`
    across the two paths, so identity is what is asserted, per path, in
    `tests/test_architecture_boundaries.py`.
  - **How long the old paths are kept: through the whole of the `0.x` line.** Removal requires a
    major version, and a `DeprecationWarning` announced in a minor release at least one release
    ahead of it. **No warning is emitted today**, deliberately: nothing inside this package imports
    through the old paths any more, so the only emitter would be a caller who cannot act on it
    until that cycle opens. A shim with no stated end date is a second public API somebody
    maintains forever without ever having decided to; this one has an end attached to a version.
  - **Not one byte of output moved, and that is a measurement rather than a benchmark.** Every
    catalog surface — `split_identifier`, `split_identifier_parts`, `strip_qualifier`,
    `expand_identifier` against an empty catalog and against a populated one, `to_physical_name`,
    `is_compliant`, `normalize`, and the aggregate `catalog_gap` report — was run over every pair
    of both governed corpora, and every extraction and propagation output was run over MED1250 and
    PLOD-CW at all three extraction profiles. **`3,619,227` records, compared field by field,
    before the first line moved and after the last.** Every field of every record, provenance
    included: `entry_id`, `source`, `confidence`, `beat`, `class_word`, `kind`, `is_known`,
    `is_fully_known`, `unaccounted`, plus the `repr` of every object. Identical. The one record
    that differs is the harness's own note of which import path it used, which is what that record
    exists to say.
  - **What DID change: `__module__` on every moved class.** An uncaught traceback now prints
    `acronymkit.core.exceptions.ConfigurationError` where it printed
    `acronymkit.exceptions.ConfigurationError`. If you match on that string — in a log parser, in a
    pickle written by an older version, in a doctest — it moved. One doctest in this tree pinned
    the old spelling and was updated; nothing else in this package matches on it.
  - **What is still called `governed`, and stays that way:** every type name
    (`GovernedDictionary`, `GovernedEntry`, `GovernedNamer`), the documentation page, the CLI
    verbs, and every `governed_*` run id in `bench/results.json`. A run id is the identity of a
    measurement, and renaming one silently re-points every citation of it. "Governed" is the
    posture — refuse rather than guess; "catalog" is the thing this half is *about*.
  - **What the new rule cannot see, because a rule with an unstated blind spot is worse than no
    rule.** The facade layer — `engine.py`, `cli.py`, `disambiguation.py`, `models.py`, the package
    `__init__` — is exempt and may import both halves, so nothing stops a prose-tokenizer result
    being handed to the identifier tokenizer one module further out. Two of the rule's three edges
    are tautologies on the tree it shipped against: `catalog -> nlp` and `nlp -> catalog` never
    existed, which is precisely why the split could come out byte-identical. And
    `importlib.import_module(name)` with a computed name defeats it, which is pinned as a
    deliberately-failing-to-fire test rather than left to be rediscovered.
    [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) carries the table and the map.

- **BREAKING: `normalize` raises instead of silently returning a name with a character deleted.**
  `normalize('TXN_©_ID', GovernedDictionary({}))` returned `'TXN_ID'` and `normalize('㎡', ...)`
  returned `''` — a token gone, then a whole name gone, with no signal either time, in the subsystem
  whose whole thesis is reporting unknown rather than answering plausibly. A name holding any
  character that belongs to no token and is not one of the separators
  `acronymkit.governed.tokenizer.ACCOUNTED_SEPARATORS` covers now raises
  `acronymkit.exceptions.TokenizationError`, naming every such character with its code point.
  - **Why raising rather than a result object.** `normalize` returns a bare `str`. There is no field
    on a `str` to report on, so the only two answers available were the name with the character
    deleted or a refusal. Widening the return type is the same size of break and moves every caller;
    the exception moves only the callers whose input actually carries one.
  - **Who this reaches.** Measured before it was chosen, on the two published corpora. `0.4664` % of
    distinct Socrata field names and `0.0000` % of distinct SEC XBRL element names carry such a
    character; per row rather than per distinct value the Socrata figure is `1.3145` %. **Every one
    of the 325 Socrata hits is the portal's own `:@computed_region_…` family** — `:` and `@` are
    Socrata's namespace marker — and no other physical identifier in either corpus carries one at
    all. Figures and the derivation: [`docs/GOVERNED_NAMING.md`](docs/GOVERNED_NAMING.md#a-character-no-token-can-hold--the-defect-this-row-denied-and-the-fix).
  - **What to do if you sweep a schema export and cannot afford an exception.** Two public
    pre-checks, both already there and neither raising: `is_compliant`, which returns the finding, and
    `split_identifier_parts`, which returns the accounting.
  - **It is a break in a 0.x library and it is being taken deliberately.** Under the positioning in
    [`docs/POSITIONING.md`](docs/POSITIONING.md), silent data loss is the worst defect available to
    this package, and a caller who upgrades and sees an exception has learned something a caller who
    upgrades and sees `'TXN_ID'` never could.

- **`is_compliant` reports `unreadable_character`, and stops offering a `fix` that would delete one.**
  A new `ComplianceReasonCode.UNREADABLE_CHARACTER` — a whole-name `FAIL` finding with `token=None`
  and **no** `fix`, because every corrected name this package can build is the name with the
  character gone. It also suppresses the `fix` on the three whole-name findings that would otherwise
  have carried the deletion: `NOT_UPPER_SNAKE` used to answer `TXN_©_ID` with `fix='TXN_ID'`, which
  is a machine-readable instruction to delete part of a name nobody approved.
  - **`compliant` never changes value.** Such a name already failed `NOT_UPPER_SNAKE`, so it was
    already non-compliant; confirmed over 857,517 records across both corpora and three policies.
  - **BREAKING if you exhaustively match on the code set**, or if you consume the `fix` of a
    whole-name finding without checking for `unreadable_character` first.
  - **A name made only of such characters is no longer reported as `EMPTY_NAME`.** Its detail read
    *"it is empty, or holds only separators"*, which was a false statement about a name that was one
    character long. Genuinely empty and separator-only names are unchanged.

- **`PhysicalName` gains `unaccounted`, and `to_physical_name` fills it.** The reverse direction had
  the same defect and answers it differently: it returns a record, so it reports rather than refuses.
  The split is a measurement — this verb reads *logical* names, which are prose, and the condition
  holds for `14.6560` % of distinct Socrata captions and `36.0072` % of distinct SEC XBRL labels, so a
  refusal here would stop a third of a real schema walk over punctuation somebody's caption was always
  going to have. `physical`, `confidence`, `truncated` and `tokens` are byte-identical to before on
  every input in both corpora; only the new field carries anything. **Additive, with a default**, so
  existing constructions and JSON consumers are unaffected unless they assert on the exact field set.

- **`AcronymPair.pattern` now describes all three of its values, and the text is visible in your
  generated schema.** The field description said "Which parenthetical arrangement matched:
  'long(short)' or 'short(long)'". Two words of that were wrong and one value was missing: the
  brackets may be `()`, `[]` or `{}`, so `[CNS]` yields `long(short)` and "parenthetical" was never
  accurate; and an extractor built with `legend_syntax=True` also emits `short=long`. **No behaviour
  changed and no value changed** — only the description, which travels into `model_json_schema()` and
  into anything generated from it. Nothing constrains the field to an enum, so a consumer switching on
  it should handle the third value. `docs/DECISIONS.md` D-055.

- **`is_fully_known` is stricter about square brackets, and a pipeline gating on it will newly flag
  names it used to pass.** A bracket is treated as quoting — silently discarded — only where it is
  actually positioned as quoting: an unnested matched pair, opening where a name could open and
  closing where a name could close. So `[TXN_ID]`, `[db].[schema].[TXN_ID]` and `[my.column]` still
  read clean, while `value[x]` and `TXN_ID[0]` now report the two brackets as unaccounted and come
  back `is_fully_known=False`. Previously those characters were dropped and the report said the whole
  name had been read. **The tokens are unchanged for every input** — only the accounting moved. See
  `docs/DECISIONS.md` D-034.

- **The digit rejoin no longer glues two numbers into one.** The pass that reunites a digit token with
  the token after it now refuses any join whose result is itself all digits. The consequence you may
  notice: with a catalog carrying `2020`, the name `FY_20_20` no longer resolves to it. Write
  `FY_2020` if that is what you mean. See **Fixed** below for why this was not optional.

- **`expand_identifier` is substantially faster and not one byte of its output moved.** Two internal
  changes, both proven behaviour-identical over full real corpora before they shipped. Nothing you
  call, pass or read changed; the public `TokenExpansion(...)` and `IdentifierExpansion(...)`
  constructors are untouched and still validate everything they always did.
  - **Provenance records are built without the frozen-dataclass machinery.** Only the four
    construction sites inside governed expansion changed. Worth
    1.300<!--claim:governed_perf.socrata.empty.construction_ab.speedup:.3f--> x on a real Socrata
    schema and 1.156<!--claim:governed_perf.sec_xbrl.empty.construction_ab.speedup:.3f--> x on SEC
    XBRL — 23.06<!--claim:governed_perf.socrata.empty.construction_ab.call_removed_pct:.2f--> % and
    13.49<!--claim:governed_perf.sec_xbrl.empty.construction_ab.call_removed_pct:.2f--> % of the whole
    call. Building the record was the largest thing that call did, and most of what building it cost
    was bookkeeping over values this library had already normalised.
  - **The token memo now remembers a token your catalog did *not* answer for.** It used to record only
    what the vocabulary resolved, so on an empty catalog it recorded nothing: it was worth
    1.004<!--claim:governed_perf.memo.socrata_empty.vocabulary_speedup_over_none:.3f--> x on Socrata
    and 0.992<!--claim:governed_perf.memo.sec_xbrl_empty.vocabulary_speedup_over_none:.3f--> x on SEC
    XBRL, which on one corpus is a net loss. Remembering pass-throughs takes those to
    1.912<!--claim:governed_perf.memo.socrata_empty.token_speedup_over_none:.3f--> x and
    3.592<!--claim:governed_perf.memo.sec_xbrl_empty.token_speedup_over_none:.3f--> x, cutting catalog
    lookups on the Socrata corpus from
    451,263<!--claim:governed_perf.memo.socrata_empty.none_catalog_lookups:,--> to
    107,012<!--claim:governed_perf.memo.socrata_empty.token_catalog_lookups:,--> and provenance records
    from 578,816<!--claim:governed_perf.memo.socrata_empty.none_provenance_records_constructed:,--> to
    234,565<!--claim:governed_perf.memo.socrata_empty.token_provenance_records_constructed:,-->. A
    second, identifier-level memo is on as well and adds much less — together they reach
    2.077<!--claim:governed_perf.memo.socrata_empty.full_speedup_over_none:.3f--> x and
    3.637<!--claim:governed_perf.memo.sec_xbrl_empty.full_speedup_over_none:.3f--> x. **Both memos are
    still bounded and still clear rather than evict when they fill.**
  - **Byte-identity, forced on against forced off, because a cache that changes one `entry_id` in ten
    million is invisible to a benchmark and catastrophic to an audit trail.** Every field of every
    record was compared by `repr` and by `to_json` over
    578,857<!--claim:governed_perf.socrata.empty.identity.records_compared:,--> provenance records on
    Socrata and 745,977<!--claim:governed_perf.sec_xbrl.empty.identity.records_compared:,--> on SEC
    XBRL, on four corpus-and-catalog arms, each with a control that moves a single `entry_id` and
    reddens the comparison. Zero differences.
  - **If you run governed expansion on threads on a free-threaded build, do not share one
    `GovernedDictionary` across them.** At sixteen threads on the Socrata corpus a shared dictionary
    reaches 0.368<!--claim:governed_perf.threads.freethreaded.socrata.t16_shared_scaling:.3f--> x of
    single-thread throughput while a dictionary per thread reaches
    5.541<!--claim:governed_perf.threads.freethreaded.socrata.t16_per_thread_scaling:.3f--> x. The
    memo is not the cause: removing it entirely is *worse* than sharing it, at
    0.165<!--claim:governed_perf.threads.freethreaded.socrata.t16_none_scaling:.3f--> x. The answers
    agree either way — 40,000<!--claim:governed_perf.threads.freethreaded.socrata.thread_answer_identifiers_checked:,-->
    identifiers checked across threads, 0<!--claim:governed_perf.threads.freethreaded.socrata.thread_answer_mismatches:,-->
    mismatches.
  - **Read the speed figures as this project reads them.** They are ratios of wall-clock on one
    machine (`Python 3.13.4 on Windows AMD64`, and `3.14.5` for the free-threaded rows) and are not
    quotable. The work counts beside them — catalog lookups, memo hits, provenance records, field
    writes — are properties of the code and are what is gated. Run ids `governed_perf.*`;
    `docs/EVALUATION.md`; `docs/DECISIONS.md` D-100 and D-101.

### Fixed

- **`normalize()` is idempotent again.** With a catalog holding both `11` and `911`, `normalize` on a
  name like `E_9_1_1` used to return a *different* name each time it was called — and the meaning of
  the column moved with it, from "E 9 Eleven" to "E Emergency". A digit run has no internal boundary,
  so a joined number does not split back into the pieces it was joined from, and each pass handed the
  next one a fresh adjacency to glue. Two catalog rows and plain ASCII were enough. The existing
  idempotence test could not have caught this at any length of run: it varied identifiers and
  policies but never the catalog, and idempotence here is a joint property of a name *and* a catalog.
  It now varies catalogs too. `docs/DECISIONS.md` D-033.

- **The extractor no longer emits a short form with an unmatched bracket.** Trimming a candidate's
  trailing punctuation could turn a bracketed region such as `FEV(1)` into a string carrying an opener
  with no closer — a form that matches no annotation under any convention, so the pair was lost
  outright rather than mis-scored. The right edge is now put back exactly far enough to close what the
  trim opened, all-or-nothing, and never past the span it was handed. Measured neutral on every
  held-out and second-corpus field; the improvement is on a tuning split, and `docs/DECISIONS.md`
  D-032 says plainly how much weight that deserves.

- **`GovernedDictionary.with_custom()` keeps a subclass whole.** A subclass's own attributes were
  dropped from the copy. The base class declares `__slots__` and still carries no instance dictionary,
  so nothing got heavier.

### Documentation

- **The package's own module docstring now says what the library is for, and the first example shows
  it refusing.** `help(acronymkit)` and the docstring your editor pops up used to open with
  *"bi-directional, multi-tiered acronym engine"* and *"one library for the three things production
  systems do with acronyms"* — a breadth pitch this project retired three releases' worth of
  documentation ago and had not removed from the one file every reader opens first. It now leads with
  governance, and its governed example prints the **refusal** as well as the answer: `is_fully_known`
  → `False` and `unknown_tokens` → `['KYC']` for a token no catalog approved.
  - **Read the sentence that goes with it, because it is a live foot-gun.** The default
    `UnknownPolicy` still returns a phrase for an unknown token — `'Transaction Kyc Identifier'` — at
    `is_known=False` and confidence `0.0`. **A caller reading only `.phrase` gets a governed-looking
    string for a token nobody approved.** That is documented behaviour and it has not changed; what
    changed is that the front door now says so.
  - Generation, backronym synthesis and alignment, extraction and contextual disambiguation are all
    still there, still supported, and are now named as supporting capabilities with their losing
    comparisons attached. Nothing was deprecated and no output moved. `docs/DECISIONS.md` D-089.

- **If you were waiting for `extract()` to gain a second-opinion verifier, it is not coming — and the
  measurement that stopped it is published.** The idea was to run each extracted pair back through
  the acronym generator and reject the ones it could not reproduce. Measured against gold pairs with
  the search running fully unpruned, the generator reaches the true short form for about **two in
  five** pairs on MED1250 and **half** on a PubMed Central author-roster corpus, while the shipped
  Schwartz & Hearst aligner accepts around **six in seven** and **nine in ten** of the same pairs.
  **A verifier built on it would have silently discarded a large share of correct output.**
  - The cause is structural and no configuration fixes it: the generator emits *prefixes* of
    successive words, and the aligner is allowed to place a character anywhere inside a word. Roughly
    **two in five** of the whole MED1250 corpus is unreachable at every setting of every knob.
  - **What the mechanism is good for, if you want it:** used as a *filter* rather than a verifier it
    is a genuine precision signal — it rejects wrong pairs about half again as often as right ones —
    but it costs about half the recall to get there, and that trade is yours to make rather than a
    default anybody should ship. Nothing in the library changed either way. Run ids `roundtrip.*`;
    `docs/DECISIONS.md` D-085.

- **CORRECTION to the entry above, and it is the one to read if you were told this project had
  decided not to reuse a definition across a document.** The record that stopped the verifier also
  stopped a second idea — reusing a definition the extractor already confirmed at later occurrences
  of the same short form in the same document — and gave two reasons, the second being that the
  workstream measuring it *"did not report"*. **It did.** Its measurements were in the repository the
  whole time and the report died on the way to the record. The second reason is withdrawn outright,
  and the first does not describe the idea it was applied to: **reusing a confirmed definition
  proposes no new candidate**, so a rule about the cost of widening candidate generation is a rule
  about something else.
  - **What the measurement says, if you were hoping for it.** On a PubMed Central corpus it would
    license 247,500<!--claim:one_sense.pmc_oa.a2.high_precision.licensed_occurrences:,--> occurrences,
    85.62<!--claim:one_sense.pmc_oa.a2.high_precision.a2_new_coverage_pct_of_licensed:.2f--> % of them
    outside any definition sentence and therefore new, with a correctness cost bounded between
    0.581<!--claim:one_sense.pmc_oa.a2.high_precision.wrong_floor_correctness_pct_of_licensed:.3f--> %
    and
    9.68<!--claim:one_sense.pmc_oa.a2.high_precision.wrong_ceiling_correctness_pct_of_licensed:.2f--> %
    of what it licenses.
  - **Read the comparator before reading that as cheap.** The mechanism it would replace is wrong on
    **none** of those occurrences, because it declines to answer them at all. This buys coverage and
    pays in correctness. Run ids `one_sense.*`; `docs/DECISIONS.md` D-092, and the retirement note in
    D-085.
  - **SUPERSEDED IN THIS SAME RELEASE, and read this before the paragraph above.** When that
    correction was written the mechanism was **not shipping**, and it said so. **It ships in
    `0.4.0`** — as `acronymkit.propagation.propagate()`, its own entry under **Added**. The trade
    that was the reason against it is unchanged and is answered by *where* it ships rather than by a
    new measurement: `propagate()` is a separate opt-in module that no engine, `Config` field or
    default path calls, so `extract()` returns exactly what it returned before and no published
    recall figure is republished as a figure about a different system.

- **The extraction harness has been checked against the original implementation's own published
  output, and it agrees on every document.** If you have ever wondered whether this project's
  competitor numbers are an artifact of its own scoring code: no shared-task scorer for this task
  exists anywhere — the run establishes that mechanically rather than assuming it — so the check was
  done against the NLM reference system's own output file at a pinned commit, hashed, licence read
  from that commit, not vendored.
  1,252<!--claim:differential.med1250.reference_output.documents_compared:,--> documents compared,
  1,252<!--claim:differential.med1250.reference_output.documents_agreeing:,--> agreeing,
  0<!--claim:differential.med1250.reference_output.documents_disagreeing:,--> disagreeing.
  - **Quote the discriminating half, not the total.**
    515<!--claim:differential.med1250.reference_output.documents_discriminating:,--> of those
    documents carry at least one pair;
    737<!--claim:differential.med1250.reference_output.documents_vacuous:,--> are two systems agreeing
    that an abstract contains no abbreviation at all.
  - **What this is not.** It is agreement with one implementation's output on one corpus. **It is not
    evidence that this project's scoring convention matches the published literature**, which is a
    different claim and remains unmeasured — and a neighbouring measurement already prices an
    annotation convention alone at `26.66` points on a different task.
  - **A ceiling nobody had published:** fed the gold as a prediction, the harness returns recall
    98.2<!--claim:differential.med1250.harness_ceiling.max_recall_pct:.1f--> % rather than a clean
    hundred. Every extraction recall figure here is measured against a scale whose top is not a
    hundred. Run ids `differential.*`; `docs/DECISIONS.md` D-093.

- **Where `expand_identifier` actually spends its time, if you are tuning a governed pipeline:
  building provenance records.** On real Socrata and SEC XBRL identifier corpora, constructing the
  per-token provenance — the row that resolved each token, the rule that fired, the confidence — is
  **larger than tokenisation, catalog lookup and phrase assembly put together**, on every corpus
  measured, including one where the token memo is serving over nine calls in ten. `expand_identifier`
  builds close to four frozen records per call.
  - **Practical reading:** if you are calling it in a hot loop and only ever read `.phrase`, you are
    paying for an audit trail you never open — and there is still no way to turn that off.
    **What this measurement decided is in the last entry under Changed above, and it decided against
    the obvious answer:** building the record was made cheaper rather than optional, because no caller
    inside this library reads only `.phrase`, which is the premise deferring it would have rested on.
  - **The token memo is smaller than a real schema.** It holds `4096` entries and **clears** rather
    than evicting when it fills, and a real portal corpus carries roughly six times that many
    distinct tokens. If your identifiers are drawn from a wide vocabulary, the memo may be doing less
    for you than its hit rate on a small corpus suggests.
  - Every figure ships with a **work count** — tokenizer passes, catalog lookups, memo hit rates,
    records constructed — and every wall-clock figure is fenced with the machine named and is not
    quotable, because the same three runs produced identical work counts and wall-clock figures that
    differed by more than a third. Run ids `governed_perf.*`; `docs/EVALUATION.md`;
    `docs/DECISIONS.md` D-086.

- **Two corpus sizes this project has published are wrong, and the corrected figures are in the
  record.** The Socrata field/caption corpus is `155,272` pairs here, not the `164,652` previously
  quoted — short by `9,380`, and the third independent re-derivation to land away from the original.
  The `107,012`-identifier corpus quoted in the audit **cannot be rebuilt from this repository at
  all**: two of its eight named sources are present and there is no fetcher for the rest. It is
  reported as unreconstructible rather than quietly replaced with a different population.
  `docs/DECISIONS.md` D-086.

- **`docs/DEFINITION-OF-DONE.md` now carries twenty criteria rather than fourteen**, and the six new
  ones did not flatter it: five of the six read *not met* and four read *not started*. The met-count
  rose by one and the proportion fell from roughly seven in ten to a little over half.
  `docs/DECISIONS.md` D-090.

- **Two internal statistics this project used to quote about its own reporting are retired.** A
  sampled audit of this project's own claims has now run three times. The **headline error rate
  stands** — somewhere in the low-to-mid twenties per cent of sampled claims are not true — but the
  two decompositions that used to be quoted alongside it (which *kind* of claim fails more often, and
  which *failure mode* dominates) both failed to replicate and are retired in place, with the reason
  attached at every site rather than deleted. **This matters to a reader only in one way**: if you
  have seen a sentence from this project saying that claims needing a derivation fail about five
  times as often as claims settled by a lookup, that sentence is withdrawn.
  `docs/CLAIMS-LEDGER.md` §6; `docs/DECISIONS.md` D-088.
  - ~~**Follow the second pointer, not the first, until §6 is fixed.**~~ **Fixed before this
    release, and the mechanism that produced it is not.** A cold read had found that
    `docs/CLAIMS-LEDGER.md` §6 still said the audit had run **twice** and still attached its headline
    to "both rounds", while D-088 — written the same round, and naming §6 in its own **Status** line
    as a site of this correction — recorded **three** rounds. **The correction named its own
    destination and did not arrive there.** §6 has since been rewritten, twice, and now carries the
    closed series rather than a round count; what is unfixed is that nothing made the correction
    arrive, and the same page took two further rounds to reach its own closing figure.
    `docs/DECISIONS.md` D-088 and D-096.

- **What a governed catalog is worth on a real schema, measured for the first time — and the answer
  is "a little, in a place the pooled figure cannot see".** If you are deciding whether to build or
  buy a catalog for `expand_identifier`, this is the entry to read, and it comes with a warning about
  how easy it is to over-read.
  - **The pooled comparison says a catalog makes things worse, and it is measuring the wrong thing.**
    Across `80` catalog configurations on real portal schemas, a catalog inferred from the corpus
    loses to an **empty** catalog in `79` of them. But `76.53 %` of those field/caption pairs are
    already unabbreviated — the caption is the identifier re-cut and nothing more — and on those a
    catalog can only do damage. **The whole of the loss is there.** That is not an opinion about the
    result; the empty arm emits the identifier's own characters, so it is exactly right *only* on
    those pairs and exactly wrong on every other kind, at every setting.
  - **On the `11.31 %` of pairs where the question is live, a catalog helps — and the margin is
    small.** The best of the `80` configurations recovers `40` of `3,276` live pairs, `1.22` points,
    while costing `17.79` points on the pooled figure. On the individual tokens an empty catalog
    provably cannot reach it recovers `12.35 %` and `9.22 %` across two portal-disjoint folds against
    a structural zero. **Read the margin with the win count. "Wins in 51 of 80 configurations" on its
    own is a sentence tighter than the measurement.**
  - **What this does and does not tell you.** Every catalog measured here was inferred by the harness
    from labels of the same kind it was then scored against, so `12.35 %` is a **floor** on what a
    real curated glossary could do and not an estimate of one. The corpus is public portal metadata
    in `snake_lower` and `flat_lower`; nothing here transfers to `UPPER_SNAKE` or to a proprietary
    standard. `docs/EVALUATION.md` carries the decomposition; `docs/DECISIONS.md` D-074.
- **You can now run that comparison on your own schema, offline, and tell nobody the result.**
  `tools/byoc_eval.py` ships in the sdist. Point it at your catalog and your schema and it scores an
  empty catalog against yours through the same public API you would call, prints **how many
  identifiers your catalog fired on before it prints any accuracy figure**, runs an exact paired test
  over the disagreements, checks whether your catalog was derived from the labels it is being scored
  on, and refuses to write a report containing any string from your input. It imports nothing outside
  the standard library and this package, and a test asserts the source names no network module at all.
  `python tools/byoc_eval.py --self-test` and `python tools/byoc_eval.py --template <dir>` are the
  two commands to start with; the second writes example input files you can shape your own to.
  - **One limitation stated up front, because it is the one that would mislead you**: the paired test
    assumes the disagreeing identifiers are independent and columns in one schema are not, so the
    p-value it prints is optimistic by an amount nobody has measured. The firing count and the two raw
    figures are the numbers to trust. `docs/SOURCING.md` §4.
- **How to read this project's monoculture result got narrower, in the direction that costs us.** The
  finding that the field's abbreviation extractors share one blind spot is unchanged. What was
  previously offered alongside it — that the benchmark corpora may have been built *by* those systems
  — no longer needs to be invoked: measured on `1,839` biomedical articles split into their own
  abstract and their own body, so that everything except **genre** is held constant, every quantity
  moves the way genre alone predicts. If you were citing the provenance reading, cite the genre one.
  `docs/EVALUATION.md`; `docs/DECISIONS.md` D-075.
- **The project's own do-not list has been audited and nothing was lifted.** `55` recorded
  prohibitions were enumerated and `56` of their supporting figures re-derived from source. No
  conclusion fell; `13` of the `35` figures behind the largest list are either not true of the tree
  today or cannot be re-derived at all, and nine stated *reasons* are named for correction. If you
  have ever wondered whether a "we decided not to" in this repository is load-bearing, the answer now
  has a denominator. `docs/AUDIT-PROHIBITIONS-2026-08.md`; `docs/DECISIONS.md` D-077.
- **The one comparison that looks worst for this library is now on the front page together with its
  refutation, and the finding underneath it is about the corpora rather than about this library.**
  On PLOD-CW pooled, a one-line all-caps rule scores `68.62` short-form exact F1 against `52.56` for
  `HIGH_PRECISION` on native offsets (`52.31` through the shared localiser, which changes nothing
  below) — a gap that has been in the record since it was measured. Decomposed on the 2×2 of
  the two structural handicaps it is **not shared between them**: removing the baseline's handicap
  makes ours *worse* (`54.98` against `78.38`), removing ours reverses the result (`85.73` against
  `75.13`; `87.22` against `72.36` on the test split), and with both removed this library still leads
  (`88.66` against `86.56`). `README.md` and `docs/EVALUATION.md` now carry the decomposition in the
  same table as the figure it qualifies, because a dissolution in a section a reader can skip is not
  a dissolution.
  - **The annotation axis alone is worth `26.66` points of margin and reverses the sign by itself.**
    The identical unmodified configuration scores anywhere between `52.56` and `88.66` on one corpus,
    a `36.10`-point range decided only by which annotation convention the gold is read under, with
    nothing re-run and neither system changed. That is the same family of result as the extraction
    monoculture, and `docs/EVALUATION.md` now joins the two so they are read together: **the field's
    evaluation substrate shapes the answer at least as much as the systems do.**
  - **"About eighteen points" was the wrong subtraction and it understated the finding.** Eighteen is
    the corner-to-corner swing, which nets the `+26.66` annotation-convention effect against the
    `-8.50` that the baseline's own admission rule costs inside definitional gold — and an admission
    rule is a property of the baseline, not a convention of the corpus. It also happens to
    sit within a quarter-point of the baseline's own gain across the same two rows (`17.94`), which is
    a different quantity. The arithmetic is published rather than the adjective, under the new run ids
    `shortform_contest.plod.{all,test}.convention`.
  - **None of this is a vindication, and these notes are not going to read like one.** The span scorer
    has no slot for the edge between a short form and a long form: replaying PLOD's own gold with the
    pairings rotated scores `100.00` on all four span metrics, byte-identical to the honest replay.
    The column this library wins is short-form **detection**; `extract()` returns pairs, and it still
    cannot report *this is an abbreviation and I do not know what it stands for*.
  - **A correction to a figure that had begun circulating in summaries of that control**: it mis-pairs
    three pairs in five, not three quarters — `1,054` of `1,778` replayed pairs, `59.28 %`. The
    three-quarters reading is the wrong end of the same run: `1,009` of `1,351` documents, `74.69 %`,
    carry at most one long form and the rotation could not touch them. New run ids
    `shortform_contest.plod.{all,test}.pairing_denominator`. The null result is unchanged; the
    strength of the evidence for it is smaller than the summary said. `docs/DECISIONS.md` D-066.
- **A term defined once does not "resolve everywhere afterwards".** `README.md` and the
  `engine.disambiguate` docstring both said it did. There is no cross-call state; the docs now say so
  and show the alternative that works. The engine's example now leads with the dictionary path, where
  a selection actually happens, and labels the default path as performing none.
- **The governed round-trip report gets the sentence it was missing.** On a legacy schema, expect
  `corrected` to hold nearly everything and `round_trip_inconsistent` to read zero, and read that as
  the standard doing its job rather than as the trip coming back clean. The counter was always
  counting what the docs said it counted; what was absent was one sentence about how to read it.
- Module doctests for `acronymkit.disambiguation`, `acronymkit.engine` and `acronymkit.scoring` now
  execute in the test suite. They did not before, which is how a docstring example that abstains when
  it should answer survived being written.
- `docs/EVALUATION.md` gains a decomposed section for the governed accuracy figures, behind run-id
  citations, and now says which of its figures lead and which support.
- **`README.md` corrects five things a reader could have been misled by**, each found by a cold read
  against the code rather than against the previous draft: the governed limits bullet now says no
  catalog is in the published figures; the definition-of-done link says fourteen criteria rather than
  eight — a correction that was itself overtaken inside this release, and the link says **twenty** at
  the tag; the structural counts a reader can re-derive are named individually with their commands
  rather than summarised as one; the monoculture roster is five implementations at seven operating
  points rather than seven implementations; and the two independent proposers are named.
- **[`docs/DEFINITION-OF-DONE.md`](docs/DEFINITION-OF-DONE.md) is swept a fourth time.** No verdict
  moved. Two evidence cells were wrong and are corrected, and the page now says per row which
  verdicts were re-derived this round and which were carried — half of them were carried.
  `docs/DECISIONS.md` D-073.
- **[`docs/SECOND-READER.md`](docs/SECOND-READER.md) carries state now.** The cold-read policy has a
  rotation cursor, an amended rotation set that includes the positioning page, and a section
  recording three defects the policy found in itself the first time it was executed as policy —
  including that its own trigger command returns an empty list at the moment the trigger fires.
  `docs/DECISIONS.md` D-072.
- **[`docs/CLAIMS-LEDGER.md`](docs/CLAIMS-LEDGER.md)'s migration quota now binds the decision log
  itself.** The file only the recorder may edit held the largest share of the unadjudicated numbers
  and was exempt; the exemption is withdrawn, adding a decision record now fails the claims gate
  until the round pays for it, and two rounds have taken that file's ledger down by close to half.
  Nothing about this is visible at runtime; it is why the numbers in these documents can be trusted
  to be falsifiable. `docs/DECISIONS.md` D-071.
- **The abstention curve is now published, with the comparison that reverses its meaning in the same
  table.** `docs/EVALUATION.md` carries the coverage/accuracy/recall/F1 curve, a breakdown by
  candidate-set size, and a breakdown by whether the gold expansion appears verbatim in the sentence —
  each with the shared task's own most-frequent-expansion baseline scored on the *identical answered
  subset*, in a column beside our own. Below the crossover point that baseline wins outright, and at
  the reference gate it still wins on three-way and four-way candidate sets. Read it before choosing a
  threshold.
- **The README now leads with governed naming.** It is a little over a third of the source, close to
  half the public symbols, eight of the seventeen CLI commands, and the only half with a streaming batch
  mode another runtime can drive. Ordering and framing only — no API changed. Three sentences that had
  quietly become false were retired in the process, and `docs/DECISIONS.md` D-037 names them.
- **The `SF = LF` legend flag now has a published cost, and the safety check it shipped under has been
  retired.** `docs/EVALUATION.md` gains a section measuring what the flag costs on the two corpora
  where it actually fires — every shipped profile, both labels, both scoring conventions, with the
  worst row named as the worst row and the recall ceiling printed in the same table. The check the
  flag originally shipped under was "if MED1250 precision does not move, it is safe"; that corpus
  turns out to emit **zero** legend pairs, so the check was watching a set of predictions the flag
  cannot change. It is retired and replaced. Nothing about the flag's behaviour changed and it is
  still off by default. `docs/DECISIONS.md` D-045 and D-046.
- **`docs/DEFINITION-OF-DONE.md` is new**: the eight criteria this project treats as "finished",
  swept in one pass, each with a verdict, the evidence behind it and what would close it. Three are
  open, including one that had been carried as met — the backronym generator ships with no accuracy
  number of any kind, and reading "every subsystem" as "every subsystem with a benchmark corpus"
  would have closed it by definition rather than by measurement.
- **README figures now cite the measurement they came from.** Every performance and accuracy number
  in `README.md` names the benchmark run that produced it, so a stale or mistyped figure fails the
  build instead of sitting there. The import-cost row also now shows the two companion figures
  beside the shell-import figure, because quoting the cheap one alone is the flattering comparison
  this project already refused once.
- **`disambiguate` is labelled honestly in every place a reader lands.** The `dictionary=` argument is
  not optional decoration; it is the whole feature. On the documented default path the engine has two
  candidates to choose between on one instance in 6,189 of the measured split, so it performs no
  selection at all, and the facade has no abstention gate.
- **If you followed `docs/GOVERNED_NAMING.md`'s advice about JSON overlays, you can delete that
  code.** The page told you that an overlay loaded from JSON needs a line of construction before
  `with_custom()` will take it, or the entry stringifies into the repr of a dictionary. That has not
  been true for some time: a plain mapping is accepted directly, keys beginning with an underscore are
  skipped, and a malformed entry raises `LexiconError` naming the field that is missing. The section
  is rewritten and the snippet is now executable. **A stale workaround is worse than a missing one** —
  you write it, it works, and nothing tells you it is dead code.
- **Both bundled-resource tables are correct again, and they now say who to believe.**
  `docs/OFFLINE.md` and `docs/SUPPORT_MATRIX.md` list all eight shipped resources, with byte counts
  and digests read out of `capabilities()`, and `SUPPORT_MATRIX` gained a provenance column it never
  had. Both tables now state that if they disagree with `acronymkit doctor`, `doctor` is right. The
  byte and digest columns are written in code spans because they are properties of shipped files
  rather than measurements of the library.
- **The backronym subsystem now has a published evaluation section, and it opens with what it does
  not claim.** `docs/EVALUATION.md` carries constraint-satisfaction, coverage, infeasibility-cause and
  underdetermination figures for alignment and synthesis, produced by `bench/run_backronym.py` against
  an oracle that shares no code with the search. **None of it is an accuracy number and none of it is
  evidence that this library writes good backronyms** — the same run prints `'ABC' -> 'aah baa cab'`,
  which scores full marks on every property the project can check and is unusable. If you are choosing
  between libraries on backronym quality, this section is the honest statement that nobody here has
  measured that. `docs/DECISIONS.md` D-054.

- **Three new pages, and one of them exists to say the project cannot yet do what it claims.**
  [`docs/GATES.md`](docs/GATES.md) lists every CI gate, what it checks, and — the point of the page —
  what it is blind to; **it opened by reporting that `0` of `36` gates carried recorded evidence of
  having actually failed on purpose in the environment they guard.** That opening figure is
  historical: `python tools/gates.py --check` prints `21 of 42` at the tag, and the register is the
  authority on the live count rather than this sentence or that page's own prose. [`docs/CLAIMS-LEDGER.md`](docs/CLAIMS-LEDGER.md)
  is the written policy for paying down figures the claims gate can see but cannot check.
  [`docs/SECOND-READER.md`](docs/SECOND-READER.md) is a cold-read protocol for user-facing pages, with
  the defects that motivated each of its six checks named beside them. `docs/DECISIONS.md` D-059,
  D-060, D-061.
- **Two corrections in `README.md` that a reader could have been bitten by.** The documented output of
  `synthesize_backronym("NEXUS")` was not what the shipped library returns — it came from a
  superseded ranking, and copying it into a test would have failed. And the dependency-isolation
  claim said no optional dependency reaches `sys.modules` after a generate, extract, backronym and
  disambiguate cycle; the CI job that proves it runs **generate and extract**, which is what the
  claim now says. `docs/DECISIONS.md` D-060.
- **A comparison row that labelled a precision figure as F1 is gone from `README.md` and
  `docs/ARCHITECTURE.md`.** Both claimed `F₁ > 96 %` for rule-based extractors. The published
  Schwartz & Hearst range is `~86–89 % F1 on Ab3P`, and this project's own harness scores the two
  shipped descendants at `88.87` and `80.73`. The row now carries no figure rather than a wrong one.
  `docs/DECISIONS.md` D-059.
- **`CONTRIBUTING.md` now lists all six gates and describes them correctly.** It named four and
  omitted the two that fail on a *document* rather than on code, said the type checker covers
  `src/acronymkit` only, and forbade network access in `tools/` — which is the entire purpose of three
  tools in it. All three were false. `docs/DECISIONS.md` D-060.
- **`docs/EVALUATION.md` gained four measured sections**: the proposer-pool overlap matrix and the
  size of what no bracket-scanning extractor can see; the decomposition of this library's short-form
  score against a one-line all-caps rule; an accuracy figure for backronym *alignment* with its
  coverage and its uncertainty published beside it; and the legend flag's cost on a corpus arm nobody
  had read before. `docs/DECISIONS.md` D-064 to D-067.

### Notes

- **A known defect you can hit today: for `26` code points, `to_physical_name()` hands you a name
  that `normalize()` will refuse to read back.** `str.upper()` on those `26` returns a base letter
  plus a combining mark — `'ǰ'` becomes `J` followed by COMBINING CARON — and a combining mark is a
  character no governed token can hold. So the naming verb emits it and reports `unaccounted=()`,
  and the reading verb then rejects the name it just produced. **The two halves of the governed round
  trip disagree about these inputs and one of them tells you nothing was lost.** It is **not fixed**
  in this release; it is written down, pinned by a strict test so a future fix cannot land silently,
  and its incidence is measured: `0` occurrences across the `285,839` distinct identifiers, captions,
  element names and labels in the two published governed corpora. The pre-existing
  ordinal-indicator class (`º` and its relatives), which breaks `normalize` idempotence rather than
  the round trip, is unchanged and pinned the same way; it occurs `12` times in those `285,839`.
  Both classes were found by walking **all `1,114,112` code points** rather than by sampling.
  - **One of the two counts is a property of the defect and the other is a property of your
    interpreter, and nothing short of running all five Unicode versions would have said which.** The
    ordinal class is `890` at Unicode `13.0`, `977` at `14.0`, `1050` at `15.0` and `15.1`, and
    `1048` at `16.0` — it grows and then *shrinks* — so the `1050` this project published was true
    of two Unicode versions and of no others, and was published as though it were a fact about the
    defect. The round-trip class is `26` at all five. On Unicode `15.1` the two are disjoint and
    their union is `1,076`. **If you read a single class size off this project, read it off your own
    interpreter**; the shipped test carries a version-keyed table and reports rather than fails on a
    version it does not know. `docs/DECISIONS.md` D-130.

- **No faster governed expansion is coming from deferred provenance, and this is the measurement that
  closes that avenue.** The obvious optimisation — hand back span offsets and build the provenance
  records only when somebody reads them — was built against the shipped resolver and **rejected**.
  Where the deferral is possible it allocates *exactly* as many objects as today (`325,837` against
  `325,837` on Socrata, `176,433` against `176,433` on SEC XBRL, difference `0`); where it is not, it
  costs `3.20` to `18.02` times as many. The cause is structural: the token memo already hands one
  expansion object to every occurrence of a token — `78.20` % of Socrata resolutions and `98.12` % of
  SEC XBRL's — and a span is per-occurrence, so a deferred route cannot share what the current one
  shares. **And every consumer shape that exists reads provenance on every record** (`100.00` % on
  all three), so there is nothing to postpone. Judged in machine-independent object counts rather
  than on a clock, deliberately; the wall-clock and memory figures point the same way and are
  published unarmed beside the counts. `docs/DECISIONS.md` D-129.

- **The proof that the package split changed no output is real, and you cannot re-run it.** The
  `3,619,227`-record comparison was produced by a harness that is **not committed to this repository**,
  and the two governed corpora it reads are not distributed with the package. `git ls-files` matches no
  such script. So the strongest claim this release makes about the split rests on one party's word,
  and the independent reader who checked the rest of the round could not adjudicate it either. **Two
  parties have now been unable to reproduce it.** If you need that assurance for your own upgrade, the
  honest answer is that the repository does not currently let you obtain it. Committing the harness is
  named as owed work. `docs/DECISIONS.md` D-120.

- **One scope sentence about that proof was wrong in `docs/ARCHITECTURE.md` and is corrected here.**
  It read *"every catalog, extraction and propagation output on Socrata and SEC XBRL"*. The catalog
  records were taken on those two governed corpora; the `4,215` extraction and `4,215` propagation
  records were taken on MED1250 and PLOD-CW, and the harness runs no extraction on governed data at
  all. This changelog stated it correctly throughout; the architecture page did not. `docs/DECISIONS.md`
  D-120.

- **Three of this round's records were reconstructed after the workstreams that did the work could
  not deliver a report, and they are labelled so you can discount them.** Four of ten agents in the
  last phase finished their work and failed while formatting the final report; three of those had
  already written results into the repository. The record file was then written without them, and one
  of its conclusions was wrong as a result — the withdrawal is the *CORRECTION* entry under
  **Documentation** above.
  - **What a reader loses:** every other record in `docs/DECISIONS.md` carries a *How it fails*
    section written by whoever did the work — the arm they did not run, the figure they distrusted,
    the near-miss they caught by hand. **For three records this round there is no such person**, and
    those sections were written by the recorder from stored measurements. Each of the three says so in
    its own first sentence.
  - **The salvage caught two errors in its own source material**, both from resolving every figure to
    a stored field before writing the sentence around it: a sampled share handed over under the wrong
    one of four labels, and a coverage multiple described one notch tighter than it measures.
  - **Nothing in this repository can tell "a workstream produced no result" from "a workstream
    produced a result and could not report it".** Measurements can sit in `bench/results.json` with no
    document citing them, and have now done so three times in two rounds. The check that would catch
    it is one function and nobody has written it. `docs/DECISIONS.md` D-095.

- **The cold-read policy ran for a fourth time, found eleven new defects, and could not record them —
  for the second consecutive read.** Three shipped documents state that a source distribution omits
  two files it now ships; a policy page's own trajectory figures are two rounds stale, including the
  column that page instructs readers to treat as the stable one; and one page says an internal audit
  has run twice where two documents written the same round say three. **As filed, the register the
  policy keeps was not written**, so the rotation cursor had not advanced for two reads and the
  findings lived only in a note no rule reaches. `python tools/second_reader.py --check` stays green
  throughout, **because it cannot tell "no read happened" from "a read happened and could not record
  it"**. `docs/DECISIONS.md` D-096.
  - **PARTLY SUPERSEDED IN THIS SAME RELEASE, and the half that is fixed is the smaller half.** That
    fourth read is now in `docs/cold-reads.toml` with its findings and its disposition, and the
    cursor advanced past it. **The mechanism is not fixed**: later reads have shipped their findings
    as notes under `docs/notes/` without reaching the register, so the gate is still green over a
    read it cannot see, which is the sentence above rather than a new one.

- **The claims-migration quota took its first waiver, and the waiver is a measurement.** Every one of
  the `42` unadjudicated numbers left in the decision log was resolved against every field in
  `bench/results.json`: `26` match nothing anywhere, and the other `16` match only unrelated
  quantities in unrelated units — a millisecond matching a set-similarity index. Deletion was walked
  and refused three times with the reason attached. **Read it as a waiver at the end of a burn-down
  rather than one taken to avoid it**, and note that the next round owes the same probe before it may
  take the same waiver. `docs/DECISIONS.md` D-097.

- **The do-not list was audited against its own reasons and nothing was lifted.** Ten stated reasons
  were corrected — not nine — with the retired sentence left visible beside each correction; five
  prohibitions are marked as standing, two of them **stronger than written**, and no conclusion fell.
  One refusal now rests on a qualitative claim alone and is **reported for measurement rather than
  recommended for lifting**, which is a distinction worth keeping: the reason is not wrong, it is
  unquantified. `docs/AUDIT-2026-08.md`; `docs/DECISIONS.md` D-094.

- **This project measures the error rate of its own reporting, and it is not zero.** A seeded sample
  of `24` claims made by the round that produced these notes was re-checked against running code: `5`
  of them — `20.8 %` — are not true. That is the same rate as the previous round measured, and the
  two decompositions that made the previous rate look explainable did **not** replicate. The failing
  claims are listed and corrected in `docs/DECISIONS.md` D-082. **Nothing about the library's measured
  behaviour is implicated** — every published accuracy figure is gated against `bench/results.json` —
  but if you quote a *narrative* sentence from this project's documentation, that is the rate it comes
  with.

- **The type checker now models the Python floor this package claims.** `[tool.mypy]` targeted
  `3.10` while `requires-python` is `>=3.9`, on a rationale — that mypy had dropped
  `python_version = "3.9"` — which is not true of the pinned mypy and may never have been true of it.
  Restored to `3.9`, where the tree is clean. This is a contributor-facing change only; nothing about
  what the library computes moves. It is recorded because the override had already let a `3.10`-only
  stdlib call ship through every local gate, and both copies of the stale claim are retired in place
  rather than deleted. **That limit is closed in this same unreleased set:** `files` now names
  `src/acronymkit`, `tools` and `bench`, so the checker covers all three at the `3.9` floor.
  Extending it found three more `Path.write_text(newline=...)` calls still shipping in `tools/`,
  which is the very defect the floor was restored to catch. Still contributor-facing only.
  See D-058 and the `[tool.mypy]` comment in `pyproject.toml`.

- **New claims must now cite a run id.** `tools/check_claims.py` still accepts the existing figures
  that are backed only by matching a value somewhere in `bench/results.json` — 64 of them across three
  files, down from 87 across five when the ratchet was installed, with `README.md` now at zero and no
  longer budgeted at all — but that path is a ratchet and admits nothing new: every number added to
  the docs from
  here names the measurement it came from, so that a wrong citation can fail the build. Value matching
  cannot tell a correct claim from a coincidence, and a stale figure survived two audits on exactly
  that gap.
- **`bench/splits.toml` is now executable, and it knows about tasks.** `tools/splits.py` loads and
  validates it, CI runs `python tools/splits.py --check`, and `bench/corpora.py` consults it before a
  reader is registered. `identifier_segmentation` is now a declared task, the two corpora behind the
  governed accuracy figures are registered against it, and the question "may this corpus back a
  headline?" now requires the task the headline is a claim about — a corpus can be held out and still
  be the wrong instrument. `--check` now also reports, per task, that this project has **no**
  uncontaminated held-out corpus for extraction and none for disambiguation. Both SDU@AAAI-22 AE dev
  splits remain tuning and contaminated. `docs/DECISIONS.md` D-036.
- **CI now runs the test suite against the installed distribution.** The job that was meant to do this
  never did: it ran pytest inside the extracted sdist, where `conftest.py` puts `src/` at the front of
  `sys.path`, so every sdist check this project has run was a check on the source tree. A new
  `installed-suite` job installs the sdist into a clean venv, asserts the import resolves inside
  site-packages, and runs the suite from a directory containing no `src/`. It catches a missing
  bundled resource that the previous hand-written file list does not. `docs/DECISIONS.md` D-040.
- **Three changes were measured and not shipped**, which is the point of recording them: per-arity
  abstention thresholds (experiment eight), preferring the whole two-word bracketed text as a short
  form (experiment nine), and rejecting a long form that begins with a function word (experiment ten).
  Each is in `docs/DECISIONS.md` D-030 and D-032 with the numbers that refused it and the conditions
  under which it should be reopened.
- **Experiment ten turned out to be a constraint rather than a result, and it is worth knowing about
  if you are thinking of filtering the extractor's output.** This library emits *pairs*, and the pair
  is atomic — so any filter that rejects a candidate because of its long form also deletes the short
  form standing beside it. Every one of the eleven deletions the rule made on the two corpora that
  score the two labels separately removed a correct acronym span. That refuses a whole family of
  long-form-only precision filters in advance, not just the one that was tried.
  `docs/DECISIONS.md` D-041, which also poses the API question underneath it: should `extract()` be
  able to report an abbreviation whose expansion it does not know? Today it cannot, and in at least
  one corpus that is the majority case.
- **Abstention, honestly: the mechanism is done and the value is not.** The margin, the flag and the
  threshold all ship and are documented. No gate on the measured curve makes the library better at the
  shared task than a frequency table would be, and the measurement is a contaminated tuning split. It
  is a precision instrument for a caller who knows what a wrong answer costs them, not an accuracy
  fix, and it stays off by default. `docs/DECISIONS.md` D-044.
- ~~**The published MED1250 extraction headline is stale in this working tree.** The trim fix above
  moved it, and the results file and the eleven prose sites that quote it have to move in one change.
  Do not cut a release until that has happened.~~ **Done, and that is why this release could be
  cut.** `bench/results.json` and every prose site that quotes the figure moved together, and every
  one of those sites now names the run id it came from, so the next drift fails the build rather
  than sitting there. The note is retired in place rather than deleted, because a release section
  that had carried it unqualified would have told a reader not to cut the release they are reading.
- **The governed accuracy runs still record `splits_declaration = UNDECLARED`.** The corpora are now
  declared, but that string is written when a run is saved and nothing rewrites a saved entry. The
  re-save is deliberately queued behind the tokenizer work, because one of the two corpora is a live
  catalog and re-fetching it would move every published figure with nothing visible to say why.
- **A packaging check that matched a text pattern was replaced by one that runs the code.** The suite
  carried a scan for test files that read a path the source distribution does not ship. It was beaten
  twice by spellings it did not match, so it is gone; the sdist job that unpacks the archive and runs
  the suite inside it catches four of the five ways this has actually broken, because it executes the
  import instead of describing it. The one remaining gap and the one file now protected by a single
  line are both written into `.github/workflows/ci.yml` beside the checks concerned.
  `docs/DECISIONS.md` D-050.
- **The benchmark runner now shows you what a `--save` would overwrite.** `bench/run_micro.py` prints
  every stored figure it is about to replace, with the old value, the new value and the size of the
  move — and, for the import figures, the list of documents that quote them in prose. Re-recording a
  measurement that drifted with the machine is how a published caveat goes stale in the opposite
  direction from the number it was written to qualify. `docs/DECISIONS.md` D-051.
- **The last unread SDU@AAAI-22 split now has an owner.** Two open questions both named the same
  unread file as their next measurement, and whichever runner reached it first would have spent it
  for the other. It is allocated in `bench/splits.toml` — with the losing question named, the
  condition that would reverse the allocation, and, more usefully, the fact that one runner
  invocation answers both arms anyway. `docs/DECISIONS.md` D-047.
- **The two tasks this library leads with still have no held-out corpus, and it is now clear that no
  amount of re-using the corpora here will produce one.** A pair of definitions and a set of tagged
  spans are not the same annotation under two names: the corpora that pair a short form with its
  expansion carry no positions, and the corpora that carry positions never say which expansion
  belongs to which abbreviation. Deriving one from the other was measured and the invented gold is an
  order of magnitude noisier than the differences it would have adjudicated. If you are evaluating
  this library, `docs/EVALUATION.md` says which figures are held out and which are tuning; the
  flagship extraction figure is a tuning figure and this project says so on every page that prints
  it. `docs/DECISIONS.md` D-048.
- **A design note on whether `extract()` should report an abbreviation whose expansion it does not
  know** is now in `docs/notes/w11-emission-model.md`, scoped and costed. Nothing is decided and no
  behaviour changed. Worth reading before anybody asks for the feature, because a one-line all-caps
  rule already beats this library's short-form score on the one held-out corpus that can see it, so
  "we can emit unpaired abbreviations" would not by itself be an improvement. `docs/DECISIONS.md`
  D-049.
- ~~**Two documentation tables are wrong about the bundled resources.**~~ **Fixed this round** — both
  tables list all eight and now name `acronymkit doctor` as the authority if they ever disagree again.
  The note is retired in place rather than deleted, because the mechanism that produced it is not
  fixed: nothing in CI compares either table to `bundled_resources()`, so the ninth resource will drift
  exactly the same way.
- **The claims gate now reports what it cannot check, and the number is large.** `tools/check_claims.py`
  used to print a total over the numbers it had armed, and that total read as a total over the
  document. It now scans `CHANGELOG.md` and `bench/splits.toml` as well, arms a number written
  immediately before a metric unit even with no keyword nearby, and prints two further counts beside
  the first: figures on a **deferred ledger** the gate has surfaced but not adjudicated, and figures
  no arming rule reaches at all. Run `python tools/check_claims.py --residue` for the list with file,
  line and whether any measurement equals each one. **Nothing was migrated and nothing was hidden** —
  the point of the change is that the debt is now counted. One figure it surfaced: a microsecond
  before-figure in a release note further up this file matches no measurement in `bench/results.json`
  at any precision. `docs/DECISIONS.md` D-052.
- **Reserved corpus arms now refuse a read instead of asking nicely.** Two decision records had each
  set aside a corpus split for one named question, and each said in its own words that a note in a
  decision record is not a mechanism. `bench/splits.toml` now declares reservations as validated
  tables — the arm, its state, the record that decided it, the event that would spend it and the event
  that would release it — and `bench/corpora.py` raises rather than opening a reserved split unless
  the caller first declares a spend naming the record and the purpose. Contributor-facing only; no
  published number moved. `docs/DECISIONS.md` D-053.
- **An adjudicated pair corpus was built, piloted, and deliberately left unregistered.** A new
  pipeline fetches, pools, samples and freezes a corpus of definition *edges* over Federal Register
  rules — the first instrument here that produces the shape this project's flagship claim is made in.
  The pilot's verdicts are that the substrate does not carry the agency-authored legends the plan was
  costed on, that every available extractor to pool with is a descendant of the same algorithm, and
  that the sample is too small to distinguish a nearly complete pool from one missing as much as it
  holds. **No figure was published and no run id was created**, and neither has changed.
  - **SUPERSEDED IN THIS SAME RELEASE on the registration half.** As filed, this entry read *"no
    corpus was registered"* and gave the reason: the artifact is a single-annotator reference set
    adjudicated by the author of the extractor that proposed most of its pool, and `tools/splits.py`
    had no role that said so — filing it as held out would have made it headline-eligible, which is
    the one standing it must never have. **A role that says so now exists.** The corpus is declared
    in `bench/splits.toml` under `role = "single_annotator_reference"`, which `tools/splits.py`
    lists in `NEVER_HEADLINE_ROLES` and excludes from the headline arithmetic rather than by
    convention, and `--check` prints the reason beside it on every run. Registering it raised the
    declared count for `extraction` **without moving the gap**, which is the thing a declared count
    read as coverage would have hidden, and `--check` says that too. `docs/DECISIONS.md` D-056.
- **One definition-of-done criterion was closed by making it smaller, and it says so.** "Every shipped
  subsystem carries an accuracy number" now reads "four of five do; the fifth carries properties and
  cannot carry accuracy, because scoring a backronym needs a judge this project does not have". If you
  were relying on that criterion as written, read `docs/DEFINITION-OF-DONE.md` — the narrowing is in
  the verdict column, not in a footnote. `docs/DECISIONS.md` D-054, D-057.
- **The legend flag’s cost is now measured on a third corpus, and on that one it is not a cost.** On
  the institutional-prose arm nobody had read before, `11` of `12` precision cells rise, no F1 falls,
  and the single negative move anywhere is `-0.10`. **This does not change the recommendation and it
  is not an argument for turning the flag on.** That arm contains almost no equations — `27` of
  `1,063` separators open a number — so the risk the flag is off for is still unmeasured, and the
  reason the default stays off is unchanged: there is no uncontaminated corpus that could show it.
  `docs/DECISIONS.md` D-064.
- **The one-line all-caps baseline that beat this library on short-form spans does not beat it on
  comparable gold.** The deficit was the corpus annotating every occurrence while this library only
  ever emits a *paired* short form. On gold both systems can address, the ordering reverses. The
  qualifier is published in the same table as the figure it qualifies, and the section also says
  plainly what the number does **not** show: the span scorer cannot tell a system that pairs
  correctly from one that pairs at random. `docs/DECISIONS.md` D-066.
- **The backronym subsystem now has an accuracy number for half of itself, and a permanent refusal
  for the other half.** `align` is exactly right on `98.66 %` of MED1250 pairs whose correct reading
  is forced by the constraint, over about half of each corpus, with the bound over all feasible pairs
  published beside it. `synthesize` carries no accuracy number and never will: a target word with no
  source phrase has no correct expansion. The definition-of-done criterion that was closed last round
  by narrowing is **re-opened as partly met**, because the narrowing’s reason was false for half the
  subsystem. `docs/DECISIONS.md` D-067.
- **This project now has a measured error rate on its own reporting.** A seeded sample of `24`
  incidental claims made during this round was checked against running code: `19` true, `4` false, `1`
  misleading — `20.8 %` not true. Most failures were counts that were correct when written and went
  stale on a tree eight workstreams were editing at once. Contributor-facing, and published rather
  than filed: `docs/DECISIONS.md` D-068. **One sentence is retired in place here rather than
  deleted:** *"Claims settled by one file read failed at `7.7 %`; claims needing a command run failed
  at `36.4 %`."* A second round re-took that split and it inverted — `25.0 %` against `18.8 %` — so
  the decomposition is withdrawn and the headline rate is not. `docs/DECISIONS.md` D-082 measured it;
  `docs/CLAIMS-LEDGER.md` section 6 carries the retirement and what a third round would need.
- **Superseded within this release: the definition of done went to fourteen criteria here and the
  page was renumbered.** Six were added; what four documents cited as "criterion 9" became criterion
  `10`. Nine of fourteen read met at the time. **Both figures are historical** — this section covers
  three mandates, and by the tag the page carries **twenty** criteria with `11` met; see the
  tenth-sweep entry under **Notes**. `docs/DEFINITION-OF-DONE.md`, `docs/DECISIONS.md` D-069.

- **CI now fails the build on an invented latency or duration figure, and it did not before.**
  `tools/check_claims.py` arms a number when a metric keyword sits near it or a unit follows it, and
  that vocabulary was one-sided: a sentence naming a median latency in spelled-out microseconds passed
  untouched while an accuracy percentage in the same position failed. **`latency` and `duration` are
  metric keywords now and the spelled-out sub-second units are units.** If you write documentation for
  this project, a performance sentence of that shape now needs a run id.
  - **The widening changed nothing on this tree, and that is the measurement rather than a clean bill.**
    It moved the arming class of `0` of the `2246` claim-shaped numbers across the `72` files the gate
    scans, re-derived twice before the change and once independently after. Zero firings establishes
    that these documents contain no latency-shaped claim in prose. **It establishes nothing about
    whether the rule is well calibrated**, because the rule never fired.
  - **What it does not reach is published rather than left to be found**: the plurals `latencies` and
    `durations`, a bare `seconds` (refused on purpose — it would arm dates), a speedup written with a
    trailing `x`, a memory figure in `KB`, and any metric named in a word nobody put on the list.
    Closing two keywords and three units is not closing the class.
  - **A cost, measured on files outside the scanned set**: `4` numbers in `4,528` are newly armed and
    are not performance claims — three fragments of an ISO date and a `font-weight`, all four because
    the word `latency` sits within `48` characters. All four come from the proximity rule.
    `docs/DECISIONS.md` D-112.

- **A round of work on this project now files a machine-readable account of itself, and a gate reads
  it.** `tools/run_summary.py` ships with a schema, a validator, a six-state reader and a `--check`
  registered as the thirty-ninth CI gate. Contributor-facing; no library behaviour changes. The reason
  is in `docs/DECISIONS.md` D-095, D-098 and D-113: three consecutive rounds kept their work and lost
  their self-assessment, for three unrelated reasons, and **a round's account of itself was the only
  artefact no gate read.**
  - **It makes a lost report recoverable. It does not make a report happen.** An agent that dies before
    filing files nothing, and nothing here distinguishes that from an agent nobody launched. Closing
    that needs whatever spawns the work to write a roster, which is outside this repository.
  - **Its first live round demonstrates the limit rather than describing it.** Five parties filed a
    summary and the register reports `1`, because the roster naming who was expected was written by one
    of the workstreams instead of by whoever launched them. D-113.

- **Superseded within this release, and the successor is a payment rather than a fifth waiver:
  the quota was paid, against the register the three previous walks had never read.** Read
  `docs/DECISIONS.md` D-136 before the paragraph below; the floor is still unpayable, so a waiver
  still stands beside the payment, and the reason below is why. **As filed: the claims-migration
  quota has taken a fourth consecutive waiver, and the fourth one comes with the measurement that
  explains the other three: the quota has been counting the wrong ledger.**
  `docs/DECISIONS.md` carries `42` numbers the gate defers on *and*, separately, `42` it backs only by
  value coincidence. Three independent walks all resolved the first population and all three correctly
  measured it terminal. `13` of the second population are unambiguously citable **today**, with named
  run ids. The quota reads only the first — and the ledger schema cannot record a movement in the
  second at all, so a round that did those `13` citations honestly turns the build red while a round
  that records them as zero passes clean. **The maintainer is asked one question with a measurement
  attached, rather than a fourth restatement of the third waiver.** `docs/DECISIONS.md` D-126.

- **Superseded, kept for the record: the third waiver, and the escalation channel.** Nothing was migrated out of the deferred ledger for a third
  round. The residue in the decision log was measured unreachable by three independent walks, the
  changelog's own residue is frozen history that a citation would rewrite, and the four replacements the
  previous round escalated to the maintainer are unanswered in the tree. **A third waiver is not
  evidence about the residue; it is evidence that this project has no channel to a decision-maker.**
  `docs/DECISIONS.md` D-118.

- **The measured not-true rate of this project's own reporting is `14.88` % pooled over `SEVEN`
  rounds — `25` of `168`, Wilson `[10.29, 21.04]` — and that series is now closed.**
  **Read the round count carefully, because the tree disagreed with itself about it twice, in the same
  direction, one round apart.** The series was first declared closed at `16.67` % over five rounds
  while a sixth round was already in flight under the same rules; the correction to `15.97` % over six
  was then published while a *seventh* round was in flight under the same frame, unit and grading
  rules, and that round returned `2` of `24`. **Closing a series prospectively does not un-run a round
  performed under it** — the rule this project wrote down to settle the first instance, applied to the
  second. Per-round rates are `20.83, 20.83, 25.00, 8.33, 8.33, 12.50, 8.33`. A replacement sampling
  frame draws from a different population and **starts at `n = 0`**; no pooled figure spans the two.
  Pooling the seventh round moved the interval's half-width from `5.97` to `5.38` while the estimate
  moved `1.09`, so **the interval is still moving faster than it is shrinking** — the third
  consecutive round in which that has held, and the reason this instrument is retired rather than
  extended. Quote it as seven graders' pooled rate and not as this project's. **Nothing about the
  library's measured behaviour is implicated** — every published accuracy figure is gated against
  `bench/results.json`. `docs/DECISIONS.md` D-115, corrected by D-122 and then by D-132.

- **Superseded by the tenth sweep: the definition of done stands at twenty criteria, `11` of them
  met, and the ninth sweep moved exactly one verdict — by narrowing it rather than by progress.** The deferred-ledger criterion is
  still met as written, and what its trajectory measures turned out to be narrower than the criterion
  reads. Four more rows had their evidence corrected without their verdicts moving, including one that
  had gone stale in two of its three closing clauses. **The one thing this sweep could not check at all
  is the byte-identity proof behind the package split**: the corpora are not in the repository and the
  harness that produced it is not committed, so it is recorded as unmeasurable here rather than
  resolved into a `met`. `docs/DEFINITION-OF-DONE.md`, `docs/DECISIONS.md` D-125.

- **Superseded: no verdict moved at the eighth sweep.** The
  round's own brief forecast that the W11 criterion — whether `extract()` may emit a short form with an
  absent long form — would close, and it did not: A2 ships as a separate opt-in module and leaves
  `extract()` byte-identical, so the question is cheaper to answer and still unanswered. One criterion
  improved twice and **neither improvement was work on that criterion**; the verdict column says so.
  `docs/DEFINITION-OF-DONE.md`, `docs/DECISIONS.md` D-117.

## [0.3.0] — 2026-08-11

First release published to PyPI. Adds the governed-naming subsystem, and closes the two
network-reachable paths a security audit of the previous release found.

### Security

- **Audit result, stated plainly: `acronymkit` authors no network-reachable code path.** Nothing in
  `src/` opens a socket, resolves a name or issues a request. The audit found two paths it had
  *inherited* rather than written, and both are closed below. The base runtime dependency set is
  exactly `pydantic` + `typing-extensions`, five packages resolved. NLTK and spaCy raise rather than
  downloading when their data is missing — measured, not assumed. `docs/OFFLINE.md` is the long form,
  written for a security reviewer.
- **`load_schema()` loaded JSON Schema documents from directories this package does not own.** It
  searched `schemas/` under two ancestors of the package directory before falling back to the bundled
  copy — in an installed wheel, `<venv>/Lib/schemas/` and `<site-packages>/schemas/`. Neither is
  owned by this distribution, neither carries a hash in any `RECORD`, and either can be created by an
  unrelated dependency that ships a top-level `schemas` package. Since a JSON Schema may carry a
  remote `$ref` and `jsonschema` resolves those by fetching them, the audit ran the chain end to end:
  a planted schema was preferred over the bundled copy, `jsonschema` made a real outbound HTTP GET,
  and `validate_result` reported the attacker's document as valid. The search is gone —
  `load_schema()` reads the bundled resource and nothing else. `SCHEMA_PATH` still names the checkout
  copy for tooling, but no load path consults it. See `docs/DECISIONS.md` D-018.
- **`validate_result` now refuses a schema containing a remote `$ref`**, rather than relying on the
  fact that ours contains none. "Our document happens to be safe" is an accident, and this is where
  the accident would have become a request.
- **Strict offline mode.** `Config(offline=True)` and the `ACRONYMKIT_OFFLINE` environment variable
  put the library in a state where anything that could reach a network raises `OfflineError` instead.
  The environment variable can only *tighten* the setting, never loosen it, so an operator's
  hardening cannot be undone by a caller's argument.
- **CI now proves the offline claim rather than asserting it.** A new `air-gap` job installs the
  wheel from a local wheelhouse with `--no-index`, runs the whole suite under
  `tests/airgap_socket_guard.py` — which fails any test that constructs a socket — and exercises the
  public API under `unshare -n`. The guard documents one exemption: on Windows, `agenerate()` and
  `abatch_generate()` create loopback AF_INET sockets, because that is how asyncio's
  `ProactorEventLoop` builds its self-pipe.

### Added

- **Governed naming** (`acronymkit.governed`). Deterministic short→long expansion of a database
  identifier against a governed catalog, with the two reverse directions over the same vocabulary:
  `expand_token`, `expand_identifier`, `to_physical_name`, `is_compliant`, `normalize`. It is a
  lookup table with an audit trail around it — nothing is inferred, an unknown token comes back
  `is_known=False` at zero confidence, and **no accuracy figure is attached to it anywhere**, because
  reproducing a lookup table is a tautology rather than a result. `docs/GOVERNED_NAMING.md` is the
  contract; `docs/QUICKSTART_GOVERNED.md` is the same thing from the command line.
- **`GovernedNamer`** — the facade. Binds a dictionary and a policy once and exposes
  `expand_token` / `expand_identifier` / `to_physical_name` / `is_compliant` / `normalize` with the
  subject as their only argument, plus `expand_many` / `check_many` over a corpus and
  `with_custom` / `with_policy` for a variant. Constructors: `from_bundle`, `from_csv`, `from_json`,
  `from_long_to_short_csv`, `from_mapping`.
- **Loaders for a whole standard, not just a catalog.** `load_bundle`, `load_csv`,
  `load_long_to_short_csv`, `load_term_index_csv` and `BUNDLE_FILES`. A naming standard is a catalog,
  three allow-lists, a class-word map, a pin sheet and a term glossary; each bundle section accepts
  several conventional filenames, two files claiming one section is an error rather than a coin toss,
  and every section is optional.
- **Corpus audit.** `audit_identifiers`, `render_audit` and `suggest_catalog_additions`, with the
  `CorpusAudit`, `IdentifierAudit`, `UnknownToken`, `CatalogSuggestion`, `FindingTally` and
  `RoundTripBreak` records. The unknown-token table is the deliverable: it turns "our catalog is
  incomplete" into a ranked, finite list of rows to write. A suggestion is a request for a decision
  from whoever owns the catalog, never a wording this library invented.
- **`acronymkit governed-batch [FILE]`** — a whole schema in one process. JSONL in, JSONL out,
  streaming, so memory is flat in the size of the corpus. `--op expand|physical|check|normalize|audit`
  chooses the verb and `--flush-every` trades latency for throughput. Every record carries `line`,
  `input` and any `id` it arrived with; an error rides on its own record and never aborts the run;
  the process exits 1 if any record failed, and the one-line summary goes to standard error so every
  line of stdout is a record.
- **`acronymkit governed-audit [FILE]`** — the corpus report, with `--suggest`, `--limit` and
  `--details`.
- **`--unknown passthrough_titlecase|reject`** on every governed command, overriding the `unknown`
  field of the policy `--policy` resolved and nothing else. No preset sets `UnknownPolicy.REJECT`, so
  the one case a governed pipeline most obviously wants — a stale catalog stops the run rather than
  carrying on under a name nobody approved — was reachable only from Python. Omitting the flag leaves
  the preset alone, which matters because `neural_optin` is the one preset whose `unknown` is not
  `passthrough_titlecase`. It reaches the expansion verbs; `check-name`, `normalize-name` and
  `physical-name` accept it and still report, because an unapproved token *is* their answer, and
  `governed-audit` refuses the combination with a message, because listing the tokens a catalog is
  silent about is what an audit is for.
- **`--dictionary` now accepts a bundle directory or a CSV** on every governed command, via
  `--dictionary-format auto|bundle|catalog|short_to_long|long_to_short|csv|long_to_short_csv` with
  `--columns` and `--delimiter`. `auto` reads a directory as a bundle and **refuses** to guess a
  CSV's direction: the same two columns are a valid vocabulary read either way and mean different
  things.
- **The tokenizer surface is public**: `split_identifier_parts`, `strip_qualifier`,
  `IdentifierParts` and `ACCOUNTED_SEPARATORS`, exported from `acronymkit.governed` alongside
  everything above. `import acronymkit.governed` still binds no submodule — every name resolves
  lazily on first access.
- **First disambiguation evaluation.** SDU@AAAI-21 task 2, scored with a faithful reimplementation
  of the shared task's own `scorer.py`. `acronymkit` scores 41.65 % accuracy against 72.84 % for
  always picking the most common expansion. It beats random, so the context signal is real, but on
  that benchmark it is worth less than memorising frequencies. A third of the public API had no
  evidence behind it for three releases; it now has a number, and the number is bad.
- **Oracle ceiling analysis** (`bench/run_oracle.py`). 14.01 % of MED1250 is found by no system at
  all, so the practical ceiling is 85.99 %, not 100 %. We find 7 pairs no other system
  does and are therefore not strictly dominated.
- **Generation coverage diagnosis** (`bench/run_generation.py --coverage`). 82.3 % of the
  ceiling is configuration defaults rather than the algorithm, and a search budget four orders of
  magnitude larger moves recall@25 by 0.00. The ceiling is tokenisation.
- `bench/run_micro.py`, `bench/run_rerank.py`, `bench/run_termfreq.py`, `bench/run_profiles.py`.
- **`acronymkit.capabilities()` and `acronymkit doctor`.** A stdlib-only report of which tier
  resolved, which optional backends are importable, which bundled resources are present with their
  digests, whether offline mode is in force, and which `pydantic` entry-point plugins are installed.
  `doctor --format json` makes it machine-readable for an install-time check.
- **A bundled pseudo-precision table**, so the estimator is usable with no corpus. New public
  surface: `bundled_table()`, `bundled_table_provenance()`, `BUNDLED_TABLE_RESOURCE`, and a `table=`
  argument on `best_alignment`. `estimate_precisions()` is unchanged and remains the documented route
  for anyone with their own text. The table is derived from the development half of MED1250 — a US
  Government Work — and it is a **prior on English biomedical prose, not a calibration**; how far it
  transfers to other domains has not been measured, and the docstring, the JSON provenance block and
  `bundled_table_provenance()` all say so.
- **`tools/build_reliability_table.py`.** Builds that resource, with `--check` to prove the shipped
  bytes match a fresh build and `--cross-check` to compare our derived spread per bucket against
  Ab3P's published table.
- **`tools/make_offline_bundle.py`.** Self-contained offline install bundles, one per platform target,
  each carrying the wheel, every runtime dependency wheel, a hash-pinned `requirements.txt`,
  `SHA256SUMS`, a manifest and a stdlib-only `verify.py`. Install is
  `pip install --no-index --find-links=. acronymkit`. Seven targets are served, and every bundle is
  re-resolved offline once per served interpreter before the build will pass.
- **`docs/INSTALL.md`.** Four routes that do not go through PyPI — release-asset wheel, git at a tag
  or full SHA, source checkout, offline bundle — plus the spaCy/NLTK model problem a wheel bundle does
  not solve, and three kinds of verification.
- **`docs/ENTERPRISE.md` and `docs/SUPPORT_MATRIX.md`.** The decision page for someone approving the
  package, and capability × tier × "works offline" × "what it needs" for the engineer who has to
  live with the answer. Linked from the README.
- **`docs/notes/pydantic-cost.md`.** What the pydantic dependency costs, measured four ways.
- **The wheel has a size budget in CI**, currently 786,432 bytes, so a resource cannot be added
  without someone noticing what it costs. It was 524,288 bytes until `acronymkit/governed/` made the
  premise behind that figure false — the old budget was really a budget on how much word list ships,
  and 68,167 B of pure Python is not noise against it. The ceiling was re-derived rather than nudged,
  and the change it exists to reject still fails by construction; `.github/workflows/ci.yml` carries
  the arithmetic.
- **`.github/workflows/publish.yml` now builds the release's whole artifact set**: bundles for every
  target, a CycloneDX SBOM and an SPDX SBOM (both checked to actually describe this distribution), one
  `SHA256SUMS` over everything, and a build-provenance attestation over that file. Signing and writing
  are separate jobs, so neither holds the other's powers.
- `tools/fetch_data.py` assets gain `derivable` — may a resource *derived* from this asset ship, when
  the asset itself may not — and `size_bytes`. `derivable` denies by default and is enforced by a
  guard, mirroring the vendoring guard in `tools/build_lexicons.py`.

### Changed

- **`acronymkit.governed` no longer imports pydantic, or anything else third-party.** The DTO
  layer, the policy and the audit records are frozen dataclasses validating in `__post_init__`. The
  wire format did not move: 940 renderings — 40 corpus identifiers plus 7 Unicode edge cases, by
  four policy presets, by five verbs, by three serialisations — hash identically under both
  implementations, so a consumer written against `docs/notes/governed-json-contract.md` needs no
  edit. What this buys is recorded in D-027 and D-028: the governed working surface imports in
  26.27 ms against 161.88 ms, and the subsystem became embeddable in a JVM, which a compiled Rust
  extension had made impossible.
  **One input-acceptance change, and it is the only behavioural difference on the whole surface:**
  a non-boolean spelling of a boolean is now refused rather than coerced. `keep_as_abbrev="false"`,
  `"no"`, `"yes"`, `1`, `0` and `1.0` raise where pydantic accepted them. Numeric widening is
  unchanged — `confidence=1` still becomes `1.0`, `max_name_length="30"` still reads as `30`.
- **Governed naming is faster on a corpus, and every optimisation changes no answer.** Against the
  figure recorded before the work, on the `schema` benchmark arm: `expand_identifier` 62.30 → 10.70
  µs, `to_physical_name` 99.90 → 41.50 µs, `is_compliant` 62.40 → 38.60 µs, corpus throughput
  15,607 → 96,532 identifiers/second. The wins are an ASCII fast path in the splitter, a
  per-(dictionary, policy) memo of resolved entries whose key space is the vocabulary rather than
  caller input, a length rejection in `abbreviate`, memoised (and frozen, therefore shareable)
  `NamingPolicy` presets, and bounding the longest-match scan in `to_physical_name` by the catalog's
  wordiest term instead of by the length of the name. Only the "after" column is in
  `bench/results.json`; see `docs/DECISIONS.md` D-026 for why a baseline cannot be, and for the
  `novel` arm that exists so a per-token memo cannot be reported only where it flatters.
- **`import acronymkit` costs 2.3 ms**, down from 149.3 ms, via lazy PEP 562 re-exports.
  Note honestly: `from acronymkit import AcronymEngine` still costs 128.1 ms and
  time-to-first-result is 196.0 ms — this moves the Pydantic cost to first use rather than
  removing it.
- README leads with generation, states scope limits explicitly, and the competitive table gains a
  Python-support column.
- `best_alignment` no longer requires a `PrecisionTable` argument; called without one it uses the
  bundled table.
- `data/LICENSES.md` is regenerated with source URL, pinned commit, licence, SHA-256, size and
  vendor-or-derive reasoning for all 20 registered assets, plus a section covering the derived
  resources that actually ship in the wheel.

### Fixed

- **BEHAVIOUR CHANGE — governed identifier expansion silently discarded characters it could not read,
  and then reported the answer as complete.** The splitter sorted everything that was neither a
  letter nor a digit into one bucket, *separator*, and separators disappear. So a column name holding
  an emoji pasted out of a spreadsheet, a stray comma from a hand-edited CSV, a currency sign or a
  combining accent expanded to the phrase a clean name would have produced — `TXN_<emoji>_ID` came
  back as "Transaction Identifier" with `is_fully_known=True`. The phrase was never the problem; the
  flag was. `is_fully_known` is the one bit a pipeline gates on, and it was saying a governed catalog
  had accounted for the whole of a name it had not read the whole of.

  Now: the separators the design names — the underscore, hyphen, dot and slash, the four SQL quoting
  characters, the two square brackets, and every Unicode whitespace character — still vanish without
  comment, because that is what a physical name is made of and it is what keeps `"TXN_ID"`,
  `[TXN_ID]` and a backtick-quoted name reading as the bare one. **Every other character is reported**,
  one entry per occurrence in input order, in a new `IdentifierExpansion.unaccounted` field, and
  `is_fully_known` is `True` only when every token resolved **and** `unaccounted` is empty.

  **What existing callers must know:** `is_fully_known` is narrower than it was, so a gate on it will
  now reject names it previously waved through — which is the intent. `unaccounted` defaults to
  empty, so a consumer that has never heard of the field reads the same payload as before. The
  accounting is written by `expand_identifier` only: `ComplianceResult` and `PhysicalName` carry no
  equivalent, which is a recorded gap rather than a decision.

  An unaccounted character is deliberately *not* turned into a token. A token is a lookup key and a
  work item — a token that misses is a catalog row somebody owes — and "this name holds a character I
  could not read" is a different fact that no catalog row can settle. The vaguer "lossless" claim is
  replaced by a counting guarantee, Hypothesis-tested: for any character outside the accounted
  separators and outside whitespace, its multiplicity in the input equals its multiplicity across the
  returned tokens plus its multiplicity in `unaccounted`. See `docs/DECISIONS.md` D-024.
- **Governed expansion cut English ordinals in half.** `1ST_TXN_DT` split to `1|ST|TXN|DT` and
  expanded to "1 St Transaction Date", where `ST` is a token no catalog carries. An ordinal suffix now
  stays welded to its digits — `1ST_TXN_DT` → `1ST|TXN|DT`, "1st Transaction Date". The suffix set is
  closed (`st`, `nd`, `rd`, `th`), matched without regard to case, English-only, and applies only when
  those two letters end the token, so `1STATE` still splits and `ADDR_1_ST` keeps the two tokens
  somebody wrote separately. The rule also does not fire across a camelCase boundary, so `1sT` is
  `('1', 's', 'T')`: a capital after a lowercase letter is the writer saying a new word starts there,
  which is what that signal means everywhere else in the splitter. A port that implements the rule
  without that condition answers `('1sT',)` and diverges.
- **`normalize` was not idempotent for a name containing an ordinal written `1sT`.** The first
  reading of the rule above joined the digit to the lowercase letter and let the camelCase rule cut
  the result, giving the token `1s` — and `'1s'.upper()` is `'1S'`, which splits back into two. Since
  `normalize` returns the tokens upper-cased and `_`-joined, `normalize('1sT')` was `'1S_T'` and
  `normalize('1S_T')` was `'1_S_T'`, so a documented invariant was false for every name carrying one.
  The corpus the idempotence test runs over contains no such name. Fixed by the narrowing above, and
  the premise the invariant rests on — a token upper-cased splits back to exactly itself — is now
  asserted as a property over arbitrary ASCII text instead of left implicit. See `docs/DECISIONS.md`
  D-024.
- **The CLI printed a traceback and exited `120` when its reader hung up.** `acronymkit
  governed-batch … | head -1` is a normal thing to type. `main` caught `BrokenPipeError` but two
  things were missing: on Windows a closed pipe surfaces as a plain `OSError` with `EINVAL` and no
  `BrokenPipeError` at all, and even where it was caught the interpreter's own flush of `sys.stdout`
  on the way out failed again against the same pipe, which is what produced the `120`. Standard
  output is now pointed at the null device on the way out, and the exit status is `0` — a consumer
  that has seen enough is the command working.
- `bench/splits.toml` recorded SDU-21 AD as MIT. It is not: the MIT licence covers the scorer and
  baseline, while the dataset is CC BY-NC-SA 4.0. Corrected, and the upstream README is pinned as an
  asset so the finding stays checkable.
- The D-011 selection headroom was overstated. Measuring the full chain gives 615 gold, 525 among
  enumerated starts, 488 admissible, 477 already returned — so the realistic prize is far smaller
  than the 121 pairs first reported.
- `PrecisionTable.ordered()` raised a bare `KeyError` from inside a sort key when the table named a
  strategy the current strategy family no longer defines. That could not happen while every table was
  built in the process that consumed it; it became reachable the moment a table could arrive from a
  file, so tables and the strategy family are now versioned separately.

### Notes

- **`normalize`'s idempotence is stated for ASCII names, and the limit outside it is now written
  down.** It rebuilds a name from the tokens the splitter found, upper-cased, and `str.upper` is not
  length-preserving in Unicode: `"ΐ"` upper-cases to a capital iota and two combining marks, a
  combining mark is not part of any token, and the second pass reports it as unaccounted and drops
  it. Repairing that would mean either applying Unicode normalisation — which rewrites text, and the
  splitter deliberately does not — or declining to upper-case a word. Both are worse than a stated
  limit, so the exception is pinned by a test of its own beside the property.
- **Memoising unknown governed tokens was measured, faster, and reverted.** A real schema repeats the
  tokens its catalog is silent about as thoroughly as the ones it governs, so caching the passthrough
  path wins on such a corpus. It was rejected on what it does to the key space: a passthrough is not
  an answer the vocabulary gave, so the memo becomes keyed by whatever names the caller happens to
  have. Clearing on full cost about 44 % on a corpus with no repetition, where the bookkeeping is
  paid on every token and returns nothing; stopping on full leaves a long-running service holding the
  first few thousand names it ever saw and learning nothing after. The correctness argument is the
  stronger one: `UnknownPolicy.REJECT` raises on an unknown token, and a cache must never answer a
  question that was supposed to stop the pipeline. The rule that replaced it — the memo remembers
  what the catalog said, and the catalog saying nothing is not something to remember. See
  `docs/DECISIONS.md` D-026.
- **The adoption problem for governed naming was a process boundary, not an API.** The consumer is a
  schema-governance pipeline in another language, and the only shape on offer was one interpreter
  start per column name. Measured on one machine, answering 2,000 names in one `governed-batch`
  process is roughly 1,300 times cheaper than 2,000 invocations, and the answers themselves are
  0.021 s of it. `GovernedNamer`, the loaders, the audit and the two batch commands exist for that
  reason; D-025 records the contract decisions inside them and what is still only hypothetical.
- Four further experiments were run and reverted: a pseudo-precision cascade, a pseudo-precision
  re-ranker, derived term statistics, and a hyphen-boundary rule. Seven attempts have now failed to
  close the extraction gap, with converging diagnoses recorded in `docs/DECISIONS.md`. The most
  useful of them: pseudo-precision rates the matching *rule*, not the *span*, so for 96.5 % of
  brackets the correct span ties with the top score.
- **Ab3P's `Lf1chSf` word list was measured and refused.** Used the way Ab3P uses it — a membership
  gate on the head word of a one-character definition — it moves the MED1250 score by less than a
  fifth of a point, and only in a configuration that admits one-character short forms, which is not
  the default. It was rejected on the control measurement rather than the gain: the list is far
  denser on MED1250's one-character gold definitions than on the rest of the corpus, and Ab3P's gold
  standard *is* MED1250, so the improvement is an upper bound of unknown tightness. Registered,
  pinned and fetch-only. The licence was never the objection; it is public domain and would have fit
  the budget. See `docs/DECISIONS.md` D-019.
- **No permissively-licensed source of acronym expansion *frequency counts* exists.** Ten were
  checked; each fails on licence, on redistribution, or on not actually holding counts. Nothing was
  shipped and nothing was invented, which is the deliverable. One route does clear the licence bar —
  deriving counts from the PMC Open Access commercial-use collection — and it is costed in D-020,
  where the binding constraint turns out to be the wheel budget rather than the licence.
- **The pydantic migration was measured in D-023, then carried out for the governed subsystem
  only.** `acronymkit.governed` now imports no third-party module at all; the generation and
  extraction engine still uses pydantic and `pyproject.toml` still declares the dependency, so this
  is one import graph changing rather than the dependency going away. See Changed, above, and
  D-027. The portability argument often made for such a migration is refuted in D-023 rather than
  used — the reason this half was done is the JVM one recorded in D-028.

## [0.2.0] — 2026-08-09

Evidence release. v0.1.0 shipped a library; this one ships the measurements that
say whether it works.

### Headline numbers

- **Extraction, MED1250 gold standard:** precision 92.07 %, recall 76.99 %,
  F1 **83.85 %** — measured against four competing systems through one harness.
  `pyab3p` leads at 88.87 F1; we sit third of five and ahead of the other pure-Python
  Schwartz & Hearst implementation.
- **Generation, first evaluation ever:** recall@1 **75.5 %** over
  546 human-authored pairs, recall@25 89.7 %.
- **Calibrated confidence with no labels:** abstention sweeps precision
  85.43 → 91.62 monotonically.

### Changed

- **BREAKING — default `scoring_strategy` is now `STRICT_INITIALISM`** (was
  `BALANCED_PRONOUNCEABLE`). Pass the old value explicitly to restore v0.1.0 ranking. Generated
  acronyms may change for any caller using the default.
- **BREAKING — French, Spanish and German no longer ship a lexicon or n-gram model.** Λ(A) is
  identically zero and Φ(A) uniform for those languages; generation, extraction and disambiguation
  still work. Restore full behaviour with `tools/fetch_data.py` + `tools/build_lexicons.py` and
  `Config(lexicon_path=...)`.
- The bundled English lexicon is now derived from SCOWL (76,879 entries, size cut ≤ 60) instead of
  being model-authored. Every Λ(A) claim is now verifiable against a checksummed, permissively
  licensed source.
- `ScoringWeights` defaults follow the new default preset: β 1.0 → 0.25, γ 12.0 → 2.0, δ 15.0 → 25.0,
  `length_penalty` 6.0 → 8.0.

### Added

- `tools/fetch_data.py` — pinned, checksum-verified asset acquisition with a generated licence ledger
  (`data/LICENSES.md`). Assets are classified vendorable or fetch-only, with the reasoning recorded.
- `tools/build_lexicons.py` — builds lexicons from SCOWL/Hunspell and refuses to write a
  non-redistributable asset into the package. Also scores the syllable heuristic against CMUdict:
  **84.1 % exact, 99.5 % within one syllable** over 117,485 entries.
- `tools/tune_presets.py` — the coefficient sweep, committed so the calibration is reproducible.
- `AcronymEngine` now records a warning when a language has no bundled lexicon or n-gram model,
  instead of degrading silently.
- `docs/DECISIONS.md` — what was tried and rejected, and why.

### Fixed

- Timing assertions in the correctness suite were absolute wall-clock ceilings and failed on shared
  CI runners while the code was correct. They now assert scaling, with hang guards scaled by a
  measured machine factor.
- `.gitignore` used `data/` with a `!data/LICENSES.md` negation, which silently ignored the ledger:
  git cannot re-include a file whose parent directory is excluded.

### Notes

- The preset weights did not survive the lexicon swap, which is the expected outcome of tuning
  against invented data: `BALANCED_PRONOUNCEABLE` scored 16/16 on the canonical corpus against 9,282
  invented words and 13/16 against 76,879 real ones. Against a real dictionary there is provably no
  vector that both weights dictionary hits meaningfully and returns every textbook initialism, so the
  default moved rather than the tuning. See `docs/DECISIONS.md` D-007.

## [0.1.0] — Unreleased

Initial public release. Delivers roadmap **Phase 1** (Tier 0 engine and extractive foundation) and
**Phase 2** (statistical NLP and phonetic scoring).

### Added

#### Forward generation
- `AcronymEngine.generate()` — beam-searched candidate enumeration over tokenised input, ranked by the
  composite objective `S(A, T) = α·Σω + β·Φ(A) + γ·Λ(A) − δ·Ψ(T, A)`.
- Positional mapping weights `ω` with the 10 / 3 / 2 schedule for initial, internal-or-terminal, and
  contiguous character matches, recorded per character in `AcronymCandidate.mappings` so every score is
  auditable.
- Phonotactic pronounceability index `Φ(A)` from a character-bigram language model, plus a normalised
  `pronounceability_score` in `[0, 1]` with no-vowel and consonant-run penalties.
- Lexical match indicator `Λ(A)` against a bundled or user-supplied dictionary.
- Information-loss penalty `Ψ(T, A)` over semantically critical tokens.
- Four scoring presets via `ScoringStrategy`: strict initialism, balanced pronounceable,
  max pronounceable, dictionary backronym — plus fully custom `ScoringWeights`.

#### Backronym synthesis
- `AcronymEngine.generate_backronym()` — k-best positional alignment of a source phrase onto a fixed
  target word.
- `AcronymEngine.synthesize_backronym()` — expansion of a target word from a vocabulary with no source
  phrase required.

#### Extraction and disambiguation
- `AcronymEngine.extract_definitions()` — Schwartz & Hearst (2003) right-to-left matching for inline
  parenthetical definitions, covering both `Long Form (Short Form)` and the inverted
  `Short Form (Long Form)` arrangement, with exact source spans and a confidence estimate.
- `AcronymEngine.disambiguate()` — lexical contextual resolution of standalone acronyms against an
  `ExpansionDictionary`, preferring document-local inline definitions. This is the seam the Phase 3
  neural backend plugs into.

#### Runtime tiers
- `EngineTier.ZERO_DEPENDENCY` (Tier 0) — pure standard library plus Pydantic.
- `EngineTier.STATISTICAL_NLP` / `HYBRID_NLP` (Tier 1) — spaCy or NLTK part-of-speech evidence, with
  `HYBRID_NLP` degrading to Tier 0 and recording a warning when no backend is installed.
- `EngineTier.AUTO` — resolve to the best available tier.
- `EngineTier.NEURAL` (Tier 2) — accepted and degraded with an explicit warning; the ONNX backend
  lands in Phase 3.

#### Tokenisation
- Unicode-aware tokeniser handling hyphenated and slashed compounds, camelCase and PascalCase splitting,
  numerals and ordinals, Latin elision, existing all-caps acronyms, and exact character offsets.
- Configurable `HyphenPolicy` and `NumeralPolicy`.
- Categorised stop-word taxonomies for English, French, Spanish and German, letting articles,
  prepositions, conjunctions, pronouns and auxiliaries be toggled independently.

#### Packaging and interoperability
- `schemas/acronym-engine-result.schema.json` — the cross-language JSON Schema contract shared with the
  planned `acronym4j` port.
- Fully typed, `py.typed`-marked distribution; frozen Pydantic v2 DTOs.
- Synchronous, thread-pool and `asyncio` batch APIs.
- `acronymkit` CLI (`generate`, `backronym`, `synthesize`, `extract`, `score`, `tokens`, `schema`).
- `tools/validate_resources.py` and `tools/build_ngram_model.py` for reproducible bundled data.

### Notes
- `requires-python` is `>=3.9` rather than the `>=3.8` in the original design note: Python 3.8 reached
  end of life in October 2024 and current Pydantic v2 releases no longer support it.
- **One deliberate deviation from the published objective function.** The positional term
  `α·Σω` is a sum, so it increases monotonically with acronym length; used unmodified as a
  *generation* objective it ranks `PODOFO` above `PDF`, because each extra character adds
  `contiguous_weight` and subtracts nothing. (The published formulation is a *ranking* function over
  candidates of a given length, so it never had to address this.) `ScoringWeights.length_penalty`
  adds `− length_penalty · max(0, |A| − preferred_length)`. Its default of `6.0` sits between
  `contiguous_weight` (2) and `initial_weight` (10), making "one letter per token, cover everything"
  the optimum by construction. Set `length_penalty=0.0` to recover the published objective exactly.
- The preset coefficient vectors were grid-searched against a corpus of sixteen textbook initialisms
  rather than chosen by hand; see `tests/test_scoring_presets.py`.
- `frozen=True` on the DTOs blocks attribute rebinding but does not deep-freeze `list`/`dict` fields,
  and the models are consequently not hashable. Treat results as read-only; see the `models` module
  docstring. Converting those fields to immutable sequences is deferred because it is a breaking
  change to the type annotations.
- The Tier 2 neural disambiguation engine (Phase 3) and the `acronym4j` Java port (Phase 4) are not
  part of this release.

[Unreleased]: https://github.com/pierce-lonergan/AcronymKit/compare/v0.4.0...HEAD
[0.4.0]: https://github.com/pierce-lonergan/AcronymKit/releases/tag/v0.4.0
[0.3.0]: https://github.com/pierce-lonergan/AcronymKit/releases/tag/v0.3.0
[0.2.0]: https://github.com/pierce-lonergan/AcronymKit/releases/tag/v0.2.0
[0.1.0]: https://github.com/pierce-lonergan/AcronymKit/releases/tag/v0.1.0
