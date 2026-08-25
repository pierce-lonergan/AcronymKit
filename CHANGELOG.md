# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

Nothing here changes what the library *computes* by default. Read two sections before upgrading.
**Removed** takes a key out of the capability report, which is a breaking change if your CI asserts
on that report's key set. **Changed** carries two behaviour changes, both of which make an existing
report *stricter* rather than different, and one of which will newly flag identifiers a pipeline
previously waved through.

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
  citations.
- **The abstention curve is now published, with the comparison that reverses its meaning in the same
  table.** `docs/EVALUATION.md` carries the coverage/accuracy/recall/F1 curve, a breakdown by
  candidate-set size, and a breakdown by whether the gold expansion appears verbatim in the sentence —
  each with the shared task's own most-frequent-expansion baseline scored on the *identical answered
  subset*, in a column beside our own. Below the crossover point that baseline wins outright, and at
  the reference gate it still wins on three-way and four-way candidate sets. Read it before choosing a
  threshold.
- **The README now leads with governed naming.** It is a little over a third of the source, close to
  half the public symbols, seven of the sixteen CLI commands, and the only half with a streaming batch
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
  what it is blind to; it opens by reporting that `0` of `36` gates carry recorded evidence of having
  actually failed on purpose in the environment they guard. [`docs/CLAIMS-LEDGER.md`](docs/CLAIMS-LEDGER.md)
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
- **The published MED1250 extraction headline is stale in this working tree.** The trim fix above
  moved it, and the results file and the eleven prose sites that quote it have to move in one change.
  Do not cut a release until that has happened.
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
  holds. **No corpus was registered, no figure was published and no run id was created.** The artifact
  is a single-annotator reference set adjudicated by the author of the extractor that proposed most of
  its pool, and `tools/splits.py` has no role that says so — filing it as held out would have made it
  headline-eligible, which is the one standing it must never have. `docs/DECISIONS.md` D-056.
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
  misleading. Claims settled by one file read failed at `7.7 %`; claims needing a command run failed
  at `36.4 %`. Most failures were counts that were correct when written and went stale on a tree eight
  workstreams were editing at once. Contributor-facing, and published rather than filed:
  `docs/DECISIONS.md` D-068.
- **The definition of done is now fourteen criteria and the page has been renumbered.** Six were
  added; what four documents cite as "criterion 9" is criterion `10` from now on. Nine of fourteen
  read met, which is the highest that page has ever read, and the page says in its own words why that
  is not straightforwardly good news. `docs/DEFINITION-OF-DONE.md`, `docs/DECISIONS.md` D-069.

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

[Unreleased]: https://github.com/pierce-lonergan/AcronymKit/compare/v0.3.0...HEAD
[0.3.0]: https://github.com/pierce-lonergan/AcronymKit/releases/tag/v0.3.0
[0.2.0]: https://github.com/pierce-lonergan/AcronymKit/releases/tag/v0.2.0
[0.1.0]: https://github.com/pierce-lonergan/AcronymKit/releases/tag/v0.1.0
