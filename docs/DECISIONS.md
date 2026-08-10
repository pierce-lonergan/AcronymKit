# Decisions, and things deliberately not done

Negative results are the easiest thing in a project to lose and often the most useful thing to keep.
This file records what was tried and abandoned, what was considered and cut, and why — so nobody
re-litigates a settled question from scratch, and so the settled questions can be re-opened on
evidence rather than on vibes.

Newest first.

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
  slot for one, so adding it is an API question before it is an accuracy question.
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
surface and needs its own decision.

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
curated resources — 31 MB of subword-frequency data and a table of long forms for one-character short
forms — rather than in the algorithm. **That was wrong**, and one measurement settles it.

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
  specifically, but it is no longer the main event.
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
   (any anchor, any placement, any skipping) estimates at 0.534. Ab3P's own table runs `FirstLet`
   0.999 to `AnyLet` 0.681. Same shape, derived independently, no labels.
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
48 KB of long forms for one-character short forms), not from the cascade structure alone. That is
testable and is the obvious next experiment.

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
