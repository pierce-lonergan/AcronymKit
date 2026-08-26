# Cold read 3 — findings, 2026-08-25

The third execution of [`docs/SECOND-READER.md`](../SECOND-READER.md), and **the first under the
read-only rule.** The reader wrote nothing except this file. No page was edited, no gate was
relaxed, no figure was moved into a fence, and `docs/cold-reads.toml` was **not** written — which
is itself finding `P-1` below, because the policy says the ledger is the reader's whole output and
the read-only rule forbids writing it.

**How numbers are handled on this page.** Every figure here is a property of *these documents* or of
a command's output, not a measurement of the library, and no benchmark runner can `--save` a
property of a document. So they appear as fenced or code-spanned output **with the command printed
beside them**, which is the convention [`docs/CLAIMS-LEDGER.md`](../CLAIMS-LEDGER.md) and
[`docs/SOURCING.md`](../SOURCING.md) already use. D-052 is explicit that fencing silences the claims
gate completely; the command is printed with every block so a reader can re-derive rather than
trust. A figure here you cannot re-derive from a command on this page is a defect in this page.

---

## 0. What was read, and the state it was read in

```
git rev-parse HEAD                      61cf933   (working tree dirty, mid-round)
python tools/second_reader.py --trigger 9 user-facing file(s)
python tools/second_reader.py --check   cursor -> docs/SUPPORT_MATRIX.md  (verified; matches
                                        section 8's <!-- rotation-cursor --> block)
```

Trigger A served nine files: `CHANGELOG.md`, `CONTRIBUTING.md`, `README.md`,
`docs/DEFINITION-OF-DONE.md`, `docs/EVALUATION.md`, `docs/GATES.md`, `docs/POSITIONING.md`,
`docs/SECOND-READER.md`, `docs/SOURCING.md`. Trigger B served `docs/SUPPORT_MATRIX.md`.
`docs/AUDIT-PROHIBITIONS-2026-08.md` and `docs/cold-reads.toml` were correctly **not** served —
both halves of section 3's exclusion rule exercised on files nobody wrote for the test.

**The cursor moves to [`docs/GATES.md`](../GATES.md)**, entry six of the twenty-one in section 3's
`<!-- rotation-set -->` block, `docs/SUPPORT_MATRIX.md` being entry five. That is the whole of this
read's contribution to the rotation state, and **somebody else has to write it**, per `P-1`.

Gates, run at the start and again at the end of the read, unchanged in between:

```
python -m pytest tests                      rc=0   5208 passed, 10 skipped, 1 xfailed
python -m ruff check src tests tools bench  rc=0
python -m ruff format --check ...           rc=0
python -m mypy                              rc=0
python tools/check_claims.py                rc=0   value-matched 64 of 64, deferred 213 of 213
python tools/splits.py --check              rc=0
python tools/gates.py --check               rc=0   CARRYING IN-SITU EVIDENCE: 13 of 36
python tools/second_reader.py --check       rc=0   open 6, blocked 1, of 7
```

**Two deviations from the baseline this read was briefed with, neither a defect.** The brief said
`4883 passed` and `0 of 36` carrying in-situ evidence. Both moved under sibling workstreams during
the round: the suite is `5208` (six new test files, `172` new test functions), and the gate register
recorded the first in-situ harvest. `docs/SECOND-READER.md` section 6's own timing block says
`4980 passed`, a third value. That block is dated and environment-stamped, so it is a snapshot
rather than an error — but the page applies *"quote the command, not the figures"* to its `--cost`
block and not to the timing block one screen above it, and the timing block is the one that has
already drifted by `228` tests.

```
python -m pytest tests | tail -1
for f in tests/test_byoc_eval.py tests/test_check_external.py tests/test_genre.py \
         tests/test_governed_catalog.py tests/test_prohibitions.py \
         tests/test_second_reader_policy.py; do grep -c '^def test' $f; done
  40  23  34  20  14  41       -> 172
```

**No file changed under this reader.** `md5sum -c` over all twenty-five user-facing files plus
`docs/cold-reads.toml`, taken before the first probe and re-checked after the last, reported no
mismatch. `docs/SECOND-READER.md` did **not** change while this policy was being executed against
it.

---

## P. Findings against the policy itself

### P-1 — The read-only rule and section 5.1 cannot both be obeyed. The rotation stalls.

`docs/SECOND-READER.md` section 5.1: *"Report everything. The reader's whole output is a row in
`docs/cold-reads.toml`."* Section 3: *"the cursor is derived from it rather than typed."* Section
5.3: *"At every cold read, its `reviewed_in` must name the newest read, or the gate is red."*

All three require the reader to **write** `docs/cold-reads.toml`. This reader was given no write
access to it. The consequences are mechanical, not hypothetical:

- **The cursor cannot advance.** `--check` derives it from the newest `rotation_served`. With no new
  `[[reads]]` row the newest remains `2026-08-25` / `docs/GOVERNED_NAMING.md`, so the next reader is
  told to serve `docs/SUPPORT_MATRIX.md` — **the file this read just served.** Trigger B degenerates
  from a rotation into a fixed point, silently, with `--check` green throughout.
- **The six open findings cannot be re-affirmed.** `reviewed_in` still reads `2026-08-25`. Five of
  the six are printed as `OPEN AND AT THE LIMIT`, meaning the *next* cold read must refuse them as
  open. This read is that next cold read, and it cannot touch them.
- **Nothing in this document is in the ledger.** Section 5.2's schema, section 5.3's decay clock and
  `--check`'s `refutation`-non-empty rule all apply to entries in that file. Findings living in a
  note in `docs/notes/` are outside every one of them.

**Disposition: blocked on a named decision** — whether the read-only boundary is *prose* (the reader
may write the ledger and nothing else, which is what section 5 designed the `applied_by` rule for)
or *filesystem* (the reader writes only a note, and a second party transcribes). Section 5.1 already
says plainly that the boundary "is not a filesystem permission"; the rule handed to this reader made
it one. Section 3 of this document carries the ledger rows in paste-ready TOML so the second party's
job is transcription, not authoring.

### P-2 — Section 4.3 requires a mutation the read-only rule forbids, and the workaround is not in situ

Section 4.3: *"Not locally in principle — in the tree, with the failure captured, and reverted in the
same sitting."* Every mutation in this read was run against a **copy** of the scanned tree using
`tools/check_claims.py --repo-root`, because mutating the tree is a write.

That copy is not equivalent, and the tool says so on every run: `Project.at()` binds
`VALUE_MATCHED_BASELINE`, `DEFERRED_BASELINE` and `_COVERAGE_GRANDFATHER` only when
`root == REPO_ROOT`, and prints `ratchets: off (not this checkout)`. On a byte-identical copy the
gate therefore reports `1 unbacked claim` (`CHANGELOG.md:670`, the `62.40` governed-naming latency)
where the real checkout reports zero. **The `rc` column of any mutation table reproduced this way is
not comparable to one taken in the tree**; the *"is the file named"* column is.

Section 4.3's own asymmetry argument rescues the blindness half — a blind spot demonstrated in the
most favourable environment is a blind spot everywhere — and rescues nothing else. Reported as a
gap in the protocol, not worked around silently.

### P-3 — Section 9's mutation table and section 3's prose disagree on the size of the rotation set

Section 3: *"Fifteen to twenty-one, and the six new entries are not a widening for its own sake."*
Section 9, on mutation `D`: *"the fix is why the rotation set is **twenty** files"* and *"it took the
set from fifteen to **twenty** because **five** pages, this one included, were unreachable."*
Section 8: *"entry four of the **fifteen** in section 3."*

The block has twenty-one entries and section 3 names six additions. Section 9 says twenty and five;
section 8 says fifteen. This is the page's own C2 defect — two descriptions of one mechanism, one
older than the mechanism — in the page that defines C2, and it is the **fourth** time this page has
miscounted its own rotation set.

```
python tools/second_reader.py --check | grep rotation     ->  rotation: 21 file(s)
sed -n '/<!-- rotation-set -->/,/```$/p' docs/SECOND-READER.md | tr '·' '\n' | grep -c '\S'
```

**Exact corrections, for whoever applies them.**

- Section 9, first sentence under *What the mutations found*: replace
  `**D got through on the first run, and the fix is why the rotation set is twenty files.**` with
  `**D got through on the first run, and the fix is why the rotation set is twenty-one files.**`
- Same paragraph: replace `it took the set from fifteen to twenty because five pages, this one
  included, were unreachable` with `it took the set from fifteen to twenty-one because six pages,
  this one included, were unreachable`.
- Section 8, the paragraph under the cursor block: replace `which is entry four of the fifteen in
  section 3` with `which is entry four of the twenty-one in section 3`.

### P-4 — Section 6 publishes two different medians for the same quantity, four lines apart

The `--cost` block reports `the median file 4,362 words docs/POSITIONING.md`. The cost table below it
reports `Trigger B — cold-read one untouched file from the rotation | one file, median 3,792 words`.
The block is derived and the table is typed, which is exactly the failure the block's own
capitalised paragraph was written to stop. **Exact correction:** replace `median 3,792 words` with
`median: see the --cost block above`.

---

## 1. Trigger B — `docs/SUPPORT_MATRIX.md`

**Strongest claim**, line 9: *"Every cell below was produced by running the thing on the host in
[Measurement environment](#measurement-environment), **except where a cell says otherwise, which it
does explicitly**."*

**What a reader must believe.** (a) There is one host and it is described. (b) The description is
accurate about that host. (c) Every unmarked cell was produced by running something, not by
reasoning about it. (d) Every marked cell marks itself.

**Does it survive the gates.** No gate reads this page's prose. `python tools/check_claims.py` scans
it under `docs/*.md` and arms nothing in it, because its figures are token counts, byte counts and
call counts rather than accuracy percentages. Belief (c) survives independent re-derivation better
than any other page in this read — every measured cell reproduced.

**Re-derived, and all of it holds:**

```
PYTHONPATH=src python - (annotator counter wrapped round the resolved backend, each public
                         method driven once)
  tokenize 1 · generate 1 · score 1 · generate_backronym 1 · agenerate 1
  batch_generate(2) 2 · abatch_generate(2) 2
  synthesize_backronym 0 · extract_definitions 0 · extract 0 · disambiguate 0
        -> all eleven rows of "Which capabilities consult the annotator" reproduce exactly

  generate("Portable Document Format")           -> PDF, score 20.44549525   (page: 20.445)
  score("API","Application Programming Interface") -> 21.297137625           (page: 21.297)
  generate_backronym(...,"NEXUS").candidates[0].coverage -> 1.0              (page: 1.0)
  ten cells of "How Tier 1 degrades, exactly"    -> all ten reproduce, including
        STATISTICAL_NLP raising under strict=False and AUTO warning under neither

  capabilities()["resources"]["count"]           -> 8, and all eight byte counts match the table
  StopWordRegistry.bundled(...)                  -> en 391 · fr 320 · es 353 · de 474, 8 categories
  grep -cv '^#\|^$' src/acronymkit/resources/lexicon_en.txt -> 76879        (page: 76,879)
  python -m pytest tests -rs                     -> 10 skips, at exactly the six test functions
                                                    the page names, once parametrisation is counted
```

The German `474` is worth recording because it looks wrong and is not: the raw JSON carries `481`
rows across eight categories, and `stopwords._normalise` folds `ß` to `ss`, collapsing seven pairs
(`außer`/`ausser`, `daß`/`dass`, `muß`/`muss`, `bloß`/`bloss`, `außerdem`, `außerhalb`,
`schließlich`). The page quotes the library-visible count, which is the right one.

**S-1 — the single sentence most likely to be false, and it is false.** Line 169, in *Measurement
environment*:

> | `acronymkit` | 0.2.0, source checkout (`src/` layout) |

```
grep -n '^version' pyproject.toml                 ->  version = "0.3.0"
PYTHONPATH=src python -c "import acronymkit; print(acronymkit.__version__)"  ->  0.3.0
git log --oneline -S 'version = "0.3.0"' -- pyproject.toml  ->  2b977da, dated 2026-08-11
git log -1 --date=short -- docs/SUPPORT_MATRIX.md           ->  d94cdf8, dated 2026-08-24
git tag                                                     ->  v0.2.0, v0.3.0
```

The version bumped thirteen days before this page was last edited. Either the environment row is
stale — in which case the page's opening claim ("every cell was produced by running the thing on
**the host in Measurement environment**") attributes every measured cell to a checkout that does not
exist — or the cells were measured on a tree seventeen commits behind and nothing re-ran them. Both
are defects and the page picks neither, which is the same shape as `F-2026-08-24-04`.

**Exact correction:** replace `0.2.0, source checkout (`src/` layout)` with
`0.3.0, source checkout (`src/` layout)` **only if** the cells above were in fact re-taken on the
current tree. If they were not, the honest edit is to date the row instead:
`0.2.0, source checkout (`src/` layout); the cells above were taken at that version and have not
been re-taken since`.

**S-2 — `F-2026-08-24-05` re-derived on this page and unaltered.** Line 39 still names nine commands
under *"All of"*. `grep -c '\.command(' src/acronymkit/cli.py` returns `16`; `acronymkit --help`
lists sixteen. The seven the sentence does not reach are `expand-token`, `expand-identifier`,
`physical-name`, `normalize-name`, `check-name`, `governed-batch`, `governed-audit` — the governed
half, which `docs/POSITIONING.md` now commits the library to leading with. Second cold read in a row.

**S-3 — line 156 says "until this round it listed seven"** in a file no round since `d94cdf8` has
touched. "This round" in an untouched document is a phrase that ages into a lie. Low severity;
**exact correction:** replace `and until this round it listed seven` with
`and before 2026-08-24 it listed seven`.

---

## 2. Trigger A

### 2.1 `docs/POSITIONING.md` — the phase's whole exposure

**Strongest claim**, line 3: *"**`acronymkit` is a governance instrument.**"* — and the load-bearing
support at line 41: *"Refusal has a measured price and that price is published beside the headline,
not beneath it."*

**What a reader must believe.** (a) The governed half has no competitor. (b) The refuse-to-guess
property is what the governed half is *about*. (c) The headline governed figures are real
measurements. (d) The page states what those figures do **not** measure. (e) The monoculture
argument is measured. (f) The reversal conditions are real, with real evidence attached.

**Does it survive the gates.** Yes, and more thoroughly than any other page here. Every one of the
twenty-one Reversal-one citations resolves, every monoculture citation resolves, and the page's own
six-run mutation table reproduces:

```
tools/check_claims.py --repo-root <byte-identical copy>, one mutation at a time,
file restored and md5-verified against the pre-mutation bytes (md5 14ffc386…, unchanged):

  control                                          docs/POSITIONING.md NOT named
  A  93.55 -> 99.99                                docs/POSITIONING.md named
  B  citation repointed at monoculture.nope.*      docs/POSITIONING.md named
  C  "... accuracy reached 99.94 % ..."            docs/POSITIONING.md named, unbacked 1 -> 2
  D  "Median latency ... 41 microseconds"          docs/POSITIONING.md NOT named
  E  "(2 declared" -> "(9 declared" inside a fence  docs/POSITIONING.md NOT named
```

All six rows hold. The two holes the page declares in its own floor are real.

**Belief (d) is the one the reviewer's exposure turns on, and the page carries it.** Lines 70-77 say
in terms that `bench/run_governed_gold.py` scores every published governed row through
`expand_identifier(identifier, GovernedDictionary({}))` and that *"those figures measure where an
identifier is cut and say nothing whatever about what a governed vocabulary is worth."* Verified
against the runner (`bench/run_governed_gold.py:544`, `catalog = GovernedDictionary({})`) and against
the run record (`"system": "acronymkit.governed.expand_identifier, empty catalog"`). **The page does
not overclaim here.** The gated figure is `91.37` on `26,536` admitted pairs, not the audit-era
`98.03`/`93.37`, and the page uses the gated one.

**Reversal one's arithmetic is exact, including the part that looks wrong.** A strict
`all_delta_points < 0` count over `governed_catalog.socrata.sweep.cells` returns `76`, not `79`,
because three cells round to `-0.0`. Counted the way the runner counts — raw exact-match counts, not
a rounded delta — it is `79` loses, `1` ties, `0` wins, and the tie is the `acting_rows = 0` cell,
exactly as the page says:

```
python - (over bench/results.json, run governed_catalog.socrata.sweep)
  all_voted_exact <  all_empty_exact   79
  all_voted_exact == all_empty_exact    1   consistent.v5.s90.fold_ba, acting_rows 0
  all_voted_exact >  all_empty_exact    0
  live_voted_exact > live_empty_exact  51  |  ties 29  |  loses 0
```

#### PS-1 — the confound paragraph is one round stale, and the same sentence is stale in two other pages

**This is the strongest finding of the read.** Lines 159-173:

> *"The measurement is strong. The strong reading of it is confounded… The tempting conclusion —
> that the corpora themselves were drawn around the pool, so the benchmarks certify the blind spot —
> **cannot be separated from genre**… every figure above is **equally consistent** with 'the corpora
> were built by these systems' and with 'abstracts do not contain the hard cases'… **Separating them
> needs article body text whose gold was pooled from Schwartz & Hearst descendants.** Nobody
> publishes one on purpose."*

`docs/EVALUATION.md` line 1172, added **in this same round**, opens the section
*"Genre, separated from provenance: abstracts against bodies of the same articles"* with:

> *"That is the right instrument for the **provenance** half and it still does not exist. The
> **genre** half can be measured the other way round — hold provenance constant and vary genre —
> **and it now has been.**"*

and closes it with *"**The verdict: genre.** All six intervals exclude zero… the strong reading of
the monoculture stays dead."* — on `1,839` same-article PMC pairs, gold from each article's own
`<def-list>` in `<back>` (in neither measured half), cluster-bootstrapped over articles.

So on the tree a reader is holding:

- *"cannot be separated from genre"* — **false.** The genre half was separated, this round.
- *"equally consistent"* — **false.** Genre now has a direct measurement with intervals excluding
  zero; provenance still has none. The two accounts are no longer symmetric.
- *"Separating them needs article body text whose gold was pooled from S&H descendants"* — **wrong
  by half.** That instrument is needed for the provenance half only, and `docs/EVALUATION.md` says
  so explicitly.

`git diff -U0 docs/POSITIONING.md | grep '^@@'` shows three hunks this round — the glossary
paragraph, Reversal one, and *How this fails*. **The confound paragraph was not among them**, in a
round that rewrote `docs/EVALUATION.md` by `+694` lines to add the measurement that falsifies it.

The same sentence is stale in two more Trigger A files:

```
grep -rn "cannot be separated\|Separating genre from provenance\|equally consistent" \
     README.md docs/POSITIONING.md docs/DEFINITION-OF-DONE.md
  README.md:161                     "cannot be separated from **genre**"
  README.md:165                     "Separating them needs article body text whose gold was
                                     pooled from these systems, and nobody publishes one"
  docs/POSITIONING.md:161,164,167   as quoted above
  docs/DEFINITION-OF-DONE.md:66     "needs a corpus nobody publishes"
  docs/DEFINITION-OF-DONE.md:916    "equally consistent with …"
  docs/DEFINITION-OF-DONE.md:917    "Separating genre from provenance needs article body text
                                     whose gold was pooled from S&H descendants"
```

Four documents describing one thing; three of them older than the mechanism, and the mechanism
landed in the same round. This is C2 at its largest scale in this repository.

**Direction matters and it is worth being exact about, because it is not an overclaim.** The genre
result *weakens* the provenance story, and the provenance story is the one `docs/POSITIONING.md`
declines to lean on. The positioning's conclusion is unaffected. What is wrong is a statement of
fact about what can be measured: the page tells a stranger that a question is unanswerable on public
data, in the same tree where half of it was answered.

**Exact correction, for `docs/POSITIONING.md` lines 159-173.** Replace the sentence
*"The tempting conclusion … cannot be separated from **genre**."* with:

> The tempting conclusion — that the corpora themselves were drawn around the pool, so the benchmarks
> certify the blind spot — has two halves, and only one of them is now separable. **The genre half
> has been measured and it points away from provenance**: on 1,839 PMC articles split into their own
> abstract and their own body, with the gold taken from each article's `<def-list>` in `<back>` and
> so in neither half, every quantity in this section moves the way the genre account predicts, with
> all six cluster-bootstrap intervals excluding zero
> ([docs/EVALUATION.md](EVALUATION.md#genre-separated-from-provenance-abstracts-against-bodies-of-the-same-articles)).

and replace *"Separating them needs article body text whose gold was pooled from Schwartz & Hearst
descendants. Nobody publishes one on purpose."* with:

> **The provenance half is what still cannot be separated.** It needs article body text whose gold
> was pooled from Schwartz & Hearst descendants, nobody publishes one on purpose, and that absence
> is a result rather than a task — which is [reversal three](#reversal-three-the-research-artifact-stops-resting-on-an-unprovable-claim)
> and is unchanged.

The corresponding `README.md` paragraph (lines 158-166) needs the same two substitutions. The
`docs/DEFINITION-OF-DONE.md` sentences at `66` and `916-917` need the word *genre* struck from the
open item, leaving provenance.

#### PS-2 — "wins in 51 of 80 configurations" is published without its effect size, and the effect size is 1.22 points

Line 297-301: *"What is evidence: it **wins** in `51` of `80` configurations, and in the other `29`
it recovers nothing at all."*

Both counts are exact. What is nowhere on the page is **how much it wins by**:

```
python - (over governed_catalog.socrata.sweep.cells, live_delta_points)
  max          1.22   abbrev_consistent.v1.s50.fold_ab   (live_voted_exact 40 of 3,276 live pairs)
  median win   0.21
  min win      0.02
  pooled cost of that same best cell   all_delta_points -17.79
```

The best catalog in the entire eighty-cell grid recovers `40` of `3,276` live pairs — `1.22` points
— while costing `17.79` points on the pooled figure. The page gives a magnitude for the *token*
metric (`12.35` % and `9.22` %, and *"about a tenth"* in *How this fails*) and none at all for the
*pair* metric, and the two differ by an order of magnitude. A reader who takes *"wins in 51 of 80"*
as meaningfully positive is reading the sentence as written and not the measurement. **A phrasing
tighter than the measurement is a false phrasing.**

**Exact correction:** append to that bullet:
`— and the margin is small: the best cell in the whole grid recovers 40<!--claim:governed_catalog.socrata.eager.fold_ab.live.voted_exact:,--> of 3,276<!--claim:governed_catalog.socrata.eager.fold_ab.live.pairs:,--> live pairs, 1.22<!--claim:governed_catalog.socrata.eager.fold_ab.live.delta_points:.2f--> points, while costing 17.79 points on the pooled figure.`
(All three citations resolve; the third is the negative of `governed_catalog.socrata.eager.fold_ab.all.delta_points`, so if the gate refuses a sign flip, code-span the last figure and print the field name beside it.)

#### PS-3 — the page omits that this round selected on the corpus its headline stands on

`docs/EVALUATION.md` line 2185, in that section's *How this fails*, states the problem plainly and
declines to fix it:

> *"**This round selected on this corpus, and `bench/splits.toml` says the opposite.**… Every entry
> it writes carries `selection_on_this_corpus = true`. Whether the manifest entry should still read
> `contaminated = false`, and whether `governed_gold.socrata.*` is still held-out evidence, is a
> question for whoever owns that file."*

`docs/POSITIONING.md` does not mention it. It hedges the held-out status a different way — *"those
runs were all taken before their corpora were declared… measured-before-declared rather than held
out"* — which is true and is not the same disclosure.

The exposure is structural, and it is one edit away from reddening a gate. Demonstrated **without
writing any file**, by loading the manifest and mutating the dataclass in memory:

```
python - (sys.path=['.']; tools.splits.load(); dataclasses.replace(socrata, contaminated=True))
  control  validate() problems: 0
  mutated  validate() problems: 1
    [corpora.socrata] is contaminated=true and role='held_out', which is the role
    [policy] headline_requires …

grep -n "role == 'tuning'" bench/run_governed_gold.py  ->  line 922, SystemExit
```

So: flipping `socrata` to `contaminated = true` reddens `python tools/splits.py --check` while the
role stays `held_out`, and moving it to `tuning` makes `bench/run_governed_gold.py` **refuse to
run** — that being the runner which produces `91.37`, the number on this page's front screen. The
positioning's headline figure sits behind a declaration `docs/EVALUATION.md` already argues is
wrong.

**Exact correction:** add to `docs/POSITIONING.md`'s *How this fails*:

> **And the corpus the headline stands on is declared in a way this round's own work contradicts.**
> `bench/splits.toml` declares `socrata` `contaminated = false` on the grounds that nothing was
> fitted to it. `bench/run_governed_catalog.py` has arms, thresholds and a grid, and every entry it
> writes carries `selection_on_this_corpus = true`;
> [docs/EVALUATION.md](EVALUATION.md#how-this-fails-8) reports the contradiction and does not resolve
> it. If the flag flips, `tools/splits.py --check` refuses `role = "held_out"`, and the only other
> role available makes `bench/run_governed_gold.py` refuse to run at all. That is a live dependency
> of the commitment above on a manifest entry nobody has adjudicated.

#### PS-4 — a stale sentence about the rotation, in the paragraph about being cold-read

Lines 406-410: *"`docs/SECOND-READER.md`'s trigger-B rotation was a fixed list of fourteen files and
this was not one of them… The cold read of 2026-08-25 appended it, **and the rotation now runs to
fifteen**."* The rotation runs to twenty-one
(`python tools/second_reader.py --check | grep rotation`). **Exact correction:** replace
`and the rotation now runs to fifteen` with `and the rotation now runs to twenty-one`.

#### PS-5 — the three-way population is presented as a two-way split

Line 281-285 gives `76.53` % identical and `11.31` % live and then says *"Split on that line"*. The
census carries a third subset, `other`, at `12.15` % of pairs (`subsets.other.pairs_pct`), which is
mentioned nowhere. The conclusions survive it — `other` contributes `0` to `empty_only_correct` and
`0` to `voted_only_correct` on both folds — so this is incompleteness rather than error, but a
reader who adds `76.53` and `11.31` gets `87.84` and has no way to find the rest.

**Q4 nomination for this document:** `docs/POSITIONING.md:161`, *"cannot be separated from
**genre**"*. Checked by reading `docs/EVALUATION.md:1172-1319` and `bench/splits.toml`'s
`[corpora.pmc_oa_same_article_genre]`, and by `git diff -U0 docs/POSITIONING.md`, which shows the
paragraph was not among this round's three hunks. **False.**

**On the brief's question — does the confidence match the evidence.** In the overclaiming direction,
no: this page is unusually disciplined, discloses its empty catalog, publishes its own gate's blind
spots, and refuses to assert Reversal one's evidence in either direction. In the hedging direction,
`PS-1` is a real instance — the page hedges a question that has since been half-answered, and does
not say which half. It is not, however, decorative: the commitment has three reversal conditions,
two of them with named artefacts that would fire them, and `docs/SOURCING.md` now attaches a dated
plan with an expiry to reversal one. That is a commitment, not a mood.

### 2.2 `docs/DEFINITION-OF-DONE.md`

**Strongest claim**, line 306-311: *"`README.md` and `docs/EVALUATION.md` both promise that CI fails
the build when a performance claim *anywhere in the docs or the source* cannot be traced to a run…
and the two sentences that overstate the gate's reach are **still standing**."*

**D-1 — this is an outright falsehood, and both sentences were corrected in the same commit that
wrote it.**

```
grep -rn "anywhere in the docs" README.md docs/EVALUATION.md   ->  no match
sed -n '700,703p' README.md
  "CI fails the build if a performance claim **that the gate can recognise** cannot be traced back
   to a benchmark run. The word matters and it used to say *anywhere*, which was false"
sed -n '26,29p' docs/EVALUATION.md
  "fails the build if a performance figure **that the gate can recognise** is not traceable back to
   it. It used to say *any* figure, in this file and in `README.md`, and that was false in both"

git log --oneline -S "that the gate can recognise" -- README.md docs/EVALUATION.md   ->  3173126
git log --oneline -S "still standing, because the right wording" -- docs/DEFINITION-OF-DONE.md
                                                                    ->  3173126
```

Same commit. Two workstreams in one round: one fixed the sentences, the other wrote down that they
were unfixed. It then survived the cold read of `61cf933`, which covered `README.md`.

**Exact correction.** Replace lines 306-311 with:

> `README.md` and `docs/EVALUATION.md` used to promise that CI fails the build when a performance
> claim *anywhere in the docs or the source* cannot be traced to a run. **A latency claim in plain
> prose is never armed and never seen**, so both sentences were false, and both were corrected at
> `3173126` to say *"a performance claim that the gate can recognise"*. The clause "zero un-gated
> figures in user-facing prose" is still further from true than the deferred ledger says, and that
> is the part that remains open. D-059, D-060.

**Q4 nomination:** the sentence above. **False**, by the two `git log -S` commands printed with it.

### 2.3 `docs/GATES.md`

**Strongest claim**, line 27: *"**Thirteen of the thirty-six gates now carry in-situ evidence, and
none of it was new work.**"* — resting on line 51: *"`git diff 3173126 61cf933 -- .github/
tools/gates.py bench/splits.toml tests/test_splits_manifest.py src/acronymkit/resources/
bench/results.json docs/GATES.md` is **empty**: not one byte of any gate's command, or of any
mutation's target, changed between the run and the register that records it."*

**The published command is empty. Verified, exactly as written.** And the count of five is right:

```
git diff --stat 3173126 61cf933 -- <the seven paths above>          ->  (empty)
python tools/gates.py --json | (gates with verified_in_situ_run)    ->  13
  of those, commands containing tools/gates.py                      ->  5
```

**G-1 — the staleness disclosure understates itself, and it does so inside the paragraph claiming to
be complete.** Line 62: *"**What is still open, stated where it cannot be missed.** This round edits
`tools/gates.py`, and five of the thirteen demonstrated gates run `tools/gates.py` as their command.
Their evidence therefore describes the previous revision of that tool."*

Run the same pathspec against the working tree the reader is actually holding:

```
git diff --stat 61cf933 -- .github/ tools/gates.py bench/splits.toml \
    tests/test_splits_manifest.py src/acronymkit/resources/ bench/results.json docs/GATES.md
  .github/gates.toml                    463 ++
  .github/workflows/gate-mutation.yml    50 +-
  bench/results.json                   5303 ++
  bench/splits.toml                     100 +
  docs/GATES.md                         494 ++
  tests/test_splits_manifest.py         129 +
  tools/gates.py                        518 ++
git diff --stat tools/splits.py         ->  46 insertions, 11 deletions
```

Every one of the seven paths has changed. By the page's own reasoning, at least **seven** of the
thirteen have evidence describing a superseded state, not five:

- the five `tools/gates.py` gates (`+518`), correctly named;
- `splits_manifest`, **rank 2** in the page's own cost ranking, whose entire command is
  `python tools/splits.py --check` and whose tool changed by `+46/-11`, against a
  `bench/splits.toml` that grew by `100` lines;
- `suite`, **rank 3**, against a tree carrying six new test files and `172` new test functions.

`claims` at **rank 1** reads a `bench/results.json` that grew by `5,303` lines; whether that counts
as its "mutation's target" is a judgement, which is why it is named separately rather than counted.

The reassurance that follows — *"`gate-mutation.yml` triggers on pushes touching `tools/gates.py`,
`.github/gates.toml`, `.github/workflows/*.yml` and `tests/test_gate_manifest.py`, so the commit that
lands this work re-takes the evidence on its own"* — is **true and holds more widely than it
claims**: `.github/gates.toml` is modified this round, so the workflow fires and re-takes all
thirteen. The trigger list is verbatim correct
(`sed -n '43,53p' .github/workflows/gate-mutation.yml`). Worth noting only because `tools/splits.py`
is *not* a trigger path, so had `.github/gates.toml` been untouched, the rank-2 gate's stale evidence
would not have been re-taken.

**Exact correction.** Replace *"This round edits `tools/gates.py`, and five of the thirteen
demonstrated gates run `tools/gates.py` as their command"* with:

> This round edits `tools/gates.py` (`+518`), `tools/splits.py` (`+46/-11`), `.github/gates.toml`
> (`+463`), `.github/workflows/gate-mutation.yml` (`+50`), `bench/splits.toml` (`+100`),
> `bench/results.json` (`+5,303`) and the suite (six new files, `172` new test functions). **Seven of
> the thirteen demonstrated gates therefore describe a superseded state** — the five that run
> `tools/gates.py`, plus `splits_manifest` at rank 2 and `suite` at rank 3 — and `claims` at rank 1
> reads a results file that grew by a third of this diff. Re-run the same pathspec against the
> working tree rather than against `3173126..61cf933`, which is empty by construction.

**Q4 nomination:** `docs/GATES.md:62`, *"five of the thirteen demonstrated gates"*. Checked by
`git diff --stat 61cf933 -- <pathspec>` and by `tools/gates.py --json`. **True as a count of
`tools/gates.py` gates, false as the count of stale evidence, which is what the paragraph is for.**

### 2.4 `docs/SOURCING.md`

**Strongest claim**, line 11-13: *"It is a plan with an owner, three dated actions, an acceptance
checklist tight enough to ask with, a legal envelope, and **a date on which the plan's failure
re-opens the positioning** rather than being renewed."*

**Every derivable figure on this page reproduces.** This is the best-evidenced new page in the tree.

```
python - (rebuild socrata_schema.csv from data/governed_gold/socrata_80pages_v2.json exactly
          as the page's own heredoc does)                      ->  69,682 rows
python tools/byoc_eval.py --schema socrata_schema.csv --out report.json
  population.pairs_scored                    69682     (page: 69682)
  population.pairs_where_label_expands       15842     (page: 15842)
  population.pairs_where_label_expands_pct   22.73     (page: 22.73)
  population.unknown_token_types_empty_arm   24536     (page: 24536)
  arms.all.empty.exact_pct                   64.98     (page: 64.98)
  arms.expanding.empty.exact_pct              6.22     (page: 6.22)
  wall clock                                 ~3 s      (page: "about 3 seconds")

python tools/byoc_eval.py --power     ->  all five rows reproduce; MIN_DISCORDANT_PAIRS = 54
python tools/byoc_eval.py --self-test ->  SELF-TEST PASSED, positive fixture and negative
                                          control both behave as criterion 11 describes
```

The page's sharpest claim about its own project's headline is also true. Line: *"the first half of
that rule excludes every one of the `15,842` expanding pairs by construction, so what it scores is
drawn entirely from the population a catalog **cannot** help on."* Verified against
`bench/run_governed_gold.py::admits` — the caption's alphanumerics must case-fold **equal** the
identifier's, so a caption that expands anything cannot be admitted. The page then immediately
narrows itself (*"It is a subset of that population and not the whole of it… 'the complement' is the
tighter phrasing and it is the wrong one"*), which is the discipline the rest of this tree is
sometimes missing.

**Nothing found to correct.** The two figures flagged `not verified` on the page (the ISO 20022
abbreviation-list licence) are flagged as unverified in the page's own words, which is the right
handling.

**Q4 nomination:** line 12, *"a date on which the plan's failure re-opens the positioning"*. Checked
by reading sections 6 and 7 for that date and by `grep -n '2026-1\|2027' docs/SOURCING.md`. The
claim is about future behaviour with no mechanism behind it — nothing turns red on the expiry date —
which is the same class `docs/POSITIONING.md` names for *"nobody optimises extraction again"*. Not
false; **unenforced**, and the page should say so where it makes the promise.

### 2.5 `README.md`

**Strongest claim**, line 165-171: *"a system which reports what it cannot see is worth more, to
somebody governing data, than one that reports a bigger number over the same blind spot. **That last
step is a claim about users this project has never measured**."* The claim is self-limiting and the
limit is stated in the same paragraph, which is the correct handling.

**What reproduced.**

```
PYTHONPATH=src python - (README's own examples, verbatim)
  generate_backronym(phrase=…, target_word="NEXUS").primary_expansion
                                        -> 'Network Exchange Unified Security'
  .candidates[0].coverage               -> 1.0
  [m.kind.value for m in …mappings]     -> ['initial','initial','contiguous','initial','initial']
  synthesize_backronym("NEXUS")…expansion_text -> 'nab ear xis ugh sac'
        -> the first pass's C3 finding is genuinely closed; the README now prints what ships

grep -c '\.command(' src/acronymkit/cli.py                    -> 16, of which 7 are governed
grep -cv '^#\|^$' src/acronymkit/resources/lexicon_en.txt     -> 76879
len(conftest.CANONICAL_ACRONYMS)                              -> 16, and the sixteen names
                                                                 in the prose are the sixteen
The "Why" table has 4 rows.  monoculture sh_family = 5 codebases at 7 operating points
  (proposers: abbreviation_extractor, abbreviations, acronymkit×3, pyab3p, scispacy, + allcaps
   and shapecue outside the family) — README and POSITIONING agree and both are right.
```

**R-1 — the README's own blindness claim reproduces, which means the claim is a live warning rather
than a historical note.** Line 714: *"the lexicon figure was replaced with an invented value in this
tree and `python tools/check_claims.py` exited zero without naming the file."*

```
tools/check_claims.py --repo-root <copy>, README.md 76,879 -> 91,404, file restored,
md5 9075665b… before and after
  occurrences of "README.md" in the gate's output   0
  unbacked count                                     unchanged
```

**R-2 — the stale confound paragraph, `PS-1` above, lines 158-166.** Same two substitutions.

**Q4 nomination:** `README.md:161`, *"cannot be separated from **genre**"*. Same check, same verdict:
**false**.

### 2.6 `CONTRIBUTING.md`

**Strongest claim**, line 88: *"**Seven commands. All seven must be green before you push, and CI
runs all seven.**"*

Verified both halves. All seven are green here, and all seven are registered CI gates
(`claims`, `splits_manifest`, `suite`, `mypy`, `ruff`, `ruff_format`, `gate_manifest` in
`tools/gates.py --json`). The eighth command a doc-touching contributor must run,
`python tools/second_reader.py --check`, is deliberately **not** in the block, and
`docs/SECOND-READER.md` section 6 says why in the same words. The two pages agree.

Both C6 findings from the first pass are genuinely closed and re-verified:

```
grep -n "files" pyproject.toml [tool.mypy]  ->  ["src/acronymkit","tools","bench"]
                                                and CONTRIBUTING.md:82 now says all three
non-negotiable 6 now states the tools/ rule correctly, naming tools/fetch_data.py's
  urllib.request.urlopen as the reason the old wording was wrong
```

The C2 finding is closed the right way round, too: CONTRIBUTING's *"after a generate + extract round
trip"* matches `.github/workflows/ci.yml`'s `zero-dependency` job, which drives `engine.generate`
and `engine.extract_definitions` and nothing else. The longer README version is gone.

**Nothing found to correct.**

**Q4 nomination:** line 88, *"CI runs all seven"*. Checked against `tools/gates.py --json`. **True.**

### 2.7 `CHANGELOG.md`

**Strongest claim**, in the new *Documentation* block: *"**The annotation axis alone is worth
`26.66` points of margin and reverses the sign by itself.**"*

Every figure resolves against `bench/results.json` — `shortform_contest.plod.{all,test}.convention`
and `…pairing_denominator` exist and carry `1054`, `1778`, `59.28`, `1009`, `1351`, `74.69`. Nothing
here is invented.

**C-1 — twenty-three numbers added to a scanned file this round, zero citations, every one silenced
by a code span.**

```
git diff CHANGELOG.md | grep '^+' | (count `…` -wrapped numerics, count "claim:")
  code-spanned numeric tokens added   23
  claim citations added                0
```

R1 says a number in a scanned file cites a run id **or** is fenced/code-spanned, and that fencing
*"is indistinguishable from hiding. Prefer citing."* The run ids exist; the entry even names them in
prose (`shortform_contest.plod.{all,test}.convention`). Converting the twenty-three to citations is
mechanical and would move twenty-three numbers from the silent side of D-052 to the checked side, in
the file that is a stranger's second stop after `README.md`. **Disposition: fixed, by whoever owns
the changelog** — the citation targets are already in `bench/results.json`.

**Q4 nomination:** *"it mis-pairs three pairs in five, not three quarters — `1,054` of `1,778`
replayed pairs, `59.28 %`"*. Checked against
`bench/results.json["runs"]["shortform_contest.plod.all.pairing_denominator"]`:
`pairs_mispaired 1054`, `pairs_replayed 1778`, `pairs_mispaired_pct 59.28`,
`documents_untouched 1009`, `documents_untouched_pct 74.69`. **True, and it is a correction of a
figure that had been circulating — the entry is doing the right thing.**

### 2.8 `docs/EVALUATION.md`

**Strongest claim**, line 1319: *"**The verdict: genre.** All six intervals exclude zero and all six
point the way the genre account predicts… **the strong reading of the monoculture stays dead.**"*

This is the most carefully-guarded new section in the tree. It names three things the measurement
cannot do, gives the firing counts behind every interval, refuses to subtract the same-article
difference from the MED1250-to-PLOD difference (*"arithmetic on incommensurable quantities"*),
measures the punctuation-only-bracket objection rather than arguing it, and registers the corpus at
`single_annotator_reference` with `contaminated = true` so promotion is a validation error rather
than a one-word edit. Its own *Not settled* paragraph on the catalog question, and the *How this
fails* item reporting the `selection_on_this_corpus` contradiction it declines to fix, are the two
most honest paragraphs this reader found.

**E-1 — `C4` from the first cold read is still open, still exactly as described, and is NOT in the
ledger.** Line 1723:

> *"The governed half of this package is `9,647` of `26,149` source lines — re-counted for this
> revision with `find src/acronymkit -name '*.py' | xargs wc -l`, because the previous figure here
> had gone stale"*

```
find src/acronymkit -name '*.py' | xargs wc -l | tail -1            ->  26561 total
find src/acronymkit/governed -name '*.py' | xargs wc -l | tail -1   ->   9647 total
```

The numerator is exact. The denominator is `412` lines short, in a sentence whose whole point is
that the previous figure had gone stale. `docs/SECOND-READER.md` section 4.2 names this as the
finding that *bought* check C4 — *"the highest-yield check per second spent"* — and it is not among
the seven entries in `docs/cold-reads.toml`.

**Exact correction:** replace `9,647 of 26,149 source lines` with `9,647 of 26,561 source lines`,
and re-run the published command when the sentence is next touched.

**E-2 — the ledger's completeness claim does not hold.** `docs/cold-reads.toml`'s `reads[0].note`
says *"Only the ones still live on 2026-08-25 are carried below; a ledger that re-lists closed
findings is a changelog."* `E-1` is live and is not carried. Of the first pass's six named checks,
`C1` is in the ledger (three entries), `C2`, `C3` and `C6` are genuinely closed (re-verified above),
`C5`'s second half was re-derived on this page by the policy itself, and `C4` is live and absent.
**One live finding is missing from a ledger that claims to hold all of them**, which is the exact
failure mode section 5.3 exists to prevent.

**Q4 nomination:** `docs/EVALUATION.md:1723`, *"`9,647` of `26,149` source lines"*. Checked by the
command the sentence publishes. **False.**

### 2.9 `docs/SECOND-READER.md`

Covered in section `P` above: `P-1` (the read-only rule versus section 5.1), `P-2` (section 4.3),
`P-3` (twenty-one versus twenty versus fifteen), `P-4` (two medians).

**Strongest claim**, line 17-19: *"**The parts of this page that run, run.** Its trigger is
`tools/second_reader.py`; its state is the ledger; `python tools/second_reader.py --check` is the
gate over both."* Verified: `--trigger` returns the nine files the raw `git status` returns after
exclusions, `--check` is green, `--open` prints six, and the cursor it derives matches the
`<!-- rotation-cursor -->` block. The parts that run do run.

**Q4 nomination:** section 9, *"the fix is why the rotation set is twenty files"*. Checked by
`python tools/second_reader.py --check | grep rotation` (`21`) and by counting the block. **False.**

---

## 3. Ledger rows, paste-ready

Under `P-1` this reader cannot write `docs/cold-reads.toml`. These are the rows, in the schema
`tools/second_reader.py` validates, for a second party to paste. **`applied_by` is deliberately
absent from every one**: no finding here is `fixed`, and under the section 5.1 rule closing one takes
a second name.

```toml
[[reads]]
id = "2026-08-25b"
reader = "cold-read-3"
rotation_served = "docs/SUPPORT_MATRIX.md"
cursor_after = "docs/GATES.md"
covered = [
  "CHANGELOG.md", "CONTRIBUTING.md", "README.md", "docs/DEFINITION-OF-DONE.md",
  "docs/EVALUATION.md", "docs/GATES.md", "docs/POSITIONING.md", "docs/SECOND-READER.md",
  "docs/SOURCING.md", "docs/SUPPORT_MATRIX.md",
]
note = """
First execution under the read-only rule, and the rule collides with section 5.1: the
reader's whole output is supposed to BE this file. It was written by a second party from
docs/notes/cold-read-3-findings.md. The six findings raised below were raised there; the
six pre-existing open findings could not be re-affirmed by the reader and their
reviewed_in was set by the same second party.
"""
```

The six new findings, in the same schema, are in section 2 of the findings note with the file, the
line, the sentence quoted exactly and the command that refutes it: `PS-1` / `R-2`
(`docs/POSITIONING.md:161` and `README.md:161`), `D-1` (`docs/DEFINITION-OF-DONE.md:309`), `G-1`
(`docs/GATES.md:62`), `E-1` (`docs/EVALUATION.md:1723`), `S-1` (`docs/SUPPORT_MATRIX.md:169`), `P-3`
(`docs/SECOND-READER.md`, section 9). Every one carries a non-empty refutation that was executed.

**And the six existing findings, re-checked on this tree.** All six reproduce; none is fixed.
`F-2026-08-24-01`, `-02`, `-03` and `-05` re-derive from `grep -c '\.command(' src/acronymkit/cli.py`
returning `16`. `F-2026-08-24-04` re-derives from `find src/acronymkit -name '*.py' | wc -l`
returning `40`. `F-2026-08-25-01` is still the first and third lines of
`src/acronymkit/__init__.py`. `F-2026-08-25-02` reproduces on both characters. **Five of the six are
at the limit and must be applied, blocked or made permanent at this read** — which this read cannot
do, per `P-1`.

---

## 4. What this read did not check

- **The suite, `mypy` and `ruff` were run, not read.** Green is evidence they pass, not evidence they
  cover anything.
- **No mutation was taken in the tree.** See `P-2`. Six were taken against a byte-identical copy with
  `--repo-root`, where the ratchets are off by design and the `rc` column is not comparable.
- **`docs/EVALUATION.md` was read in the sections its links and this round's diff reach** — the
  governed-catalog section, the genre section, the governed-subsystem headline and the traceability
  paragraph. At `2,694` lines it is the one file in the rotation that a single cold read cannot cover,
  and section 7 of the policy already names that as a weakness rather than a bound.
- **`docs/INSTALL.md` and `docs/ENTERPRISE.md` are out of both triggers and are reported here rather
  than checked properly.** Both publish install and audit instructions pinned to `v0.2.0` /
  `acronymkit-0.2.0-py3-none-any.whl` while `pyproject.toml` reads `0.3.0` and `git tag` lists
  `v0.3.0`. A stranger following `docs/INSTALL.md` installs the superseded release. That is the most
  directly user-damaging thing this reader found and it belongs to whoever owns those pages.
- **`bench/splits.toml`'s `[corpora.socrata]` entry** is outside every trigger and carries the
  declaration `PS-3` is about. Reported, not fixed.
- **Nothing here re-ran a benchmark.** Every figure quoted from `bench/results.json` was resolved
  against the saved run, not re-measured.
