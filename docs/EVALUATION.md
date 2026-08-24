# Evaluation

Until now `acronymkit`'s extractor could only claim to be a *faithful transcription* of Schwartz &
Hearst (2003). This page replaces that claim with a measurement.

## Reproduce

```bash
python tools/fetch_data.py med1250
python bench/run_extraction.py --save                     # our row
python bench/run_generation.py --all-presets --save       # generation recall@k
python bench/run_micro.py --save                          # latency and cold import
python bench/run_governed_gold.py --save                  # governed cut placement

# competitor rows (pyab3p and scispacy need Python <3.13)
python bench/run_extraction.py --save     --system acronymkit --system abbreviations     --system abbreviation_extractor --system pyab3p     --interpreter /path/to/python3.12
```

Every number on this page is written into [`bench/results.json`](../bench/results.json) by those
runners, and `tools/check_claims.py` fails the build if any performance figure in the docs or the
source is not traceable back to it.

The first four take about a second between them. The corpus is not committed — it is fetched into
the git-ignored `data/` and verified against a SHA-256 pinned in `tools/fetch_data.py`.

`run_governed_gold.py` is the exception: it fetches its own two corpora from live endpoints and
takes a few minutes on a cold cache. It walks the SEC archive's ZIP central directory with range
requests rather than downloading it, and caches both payloads under `data/governed_gold/`.

## Corpus

**MED1250** (the Ab3P gold standard): 1,250 randomly selected MEDLINE records — 1,252 in the file,
because two PubMed IDs appear twice — carrying **1,221** manually annotated short-form/long-form
pairs.

It is a *United States Government Work*: public domain, no restrictions on use or reproduction. It is
still fetch-only rather than vendored, because it is a 1.6 MB evaluation corpus and nothing in the
library reads it.

Annotation lines beginning `//` are **excluded**, per the Ab3P README. That matters: `//*` marks
synonyms the annotators found but deliberately left out of the gold standard, and `//!syn`, `//!out`,
`//!ord`, `//!num`, `//!nch` and `//!cnj` mark categories the corpus explicitly does not ask a system
to find. Counting them as gold would inflate recall against a target that does not exist.

> Attribution: Sohn S, Comeau DC, Kim W, Wilbur WJ. *Abbreviation definition identification based on
> automatic precision estimates.* BMC Bioinformatics. 2008;9:402.

## Status of these numbers

**MED1250 is a tuning set, not a held-out one, and every number below is labelled accordingly.**
Its miss taxonomy has been read in full, a boundary experiment was run and reverted against it, and
the configuration knobs responsible for 17.6 % of its misses were identified from it. Nothing about
it is blind any more.

There is currently **no held-out short-form/long-form corpus**, and that is a stated gap rather than
an oversight — see [`bench/splits.toml`](../bench/splits.toml) for why (the BioC conversions of
BIOADI/MEDSTRACT/S&H are no longer fetchable, and the corpora that *are* reachable label spans
without pairing them, so deriving pairs would make part of the gold standard mine). Until that is
closed, treat the comparison as sound and the absolute level as provisional.

## Extraction: measured against four systems

Every row is produced by **this** harness — same reader, same scorer, same corpus — because numbers
from different harnesses are not comparable. Nothing here is quoted from a paper.

| System | Implementation | P % | R % | F1 % | docs/s | Install | Cold import | Deps | Python |
|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| `pyab3p` | compiled C++ | 96.91 | 82.06 | **88.87** | 3,646 | 0.3 MB | 3.6 ms | 0 | **≤ 3.12** |
| `abbreviation_extractor` | compiled Rust | 96.42 | 75.10 | **84.44** | 24,603 | 3.0 MB | 22.9 ms | 0 | 3.8+ |
| **`acronymkit`** | pure Python | 92.46<!--claim:extraction.med1250.acronymkit.exact_precision:.2f--> | 77.31<!--claim:extraction.med1250.acronymkit.exact_recall:.2f--> | **84.21<!--claim:extraction.med1250.acronymkit.exact_f1:.2f-->** | 5,496<!--claim:extraction.med1250.acronymkit.docs_per_second:,.0f--> | 1.3 MB | 2.3 ms † | 1 (pydantic) | **3.9 – 3.13** |
| `abbreviations` | pure Python | 94.03 | 73.46 | **82.48** | 10,746 | 0.03 MB | 31.1 ms | 1 (regex) | 3.x |
| `scispacy` | spaCy pipeline | 90.45 | 72.89 | **80.73** | 52 | ~400 MB | n/a | many (spaCy) | **< 3.13** |

Footprint is measured on the installed distribution: unpacked size, cold `import` in a subprocess
(median of five, so it cannot be flattered by a warm module cache), and runtime dependency count.

**Reading this honestly:**

- `pyab3p` wins, and it should — it is the original NLM implementation, and Ab3P was developed
  against this very corpus, so it enjoys a home advantage no other row has. Its 96.96 / 83.62 also
  lands within half a point of the figures published for Ab3P on MED1250, which is the strongest
  available evidence that **this harness, reader and scorer are correct**.
- We beat the other pure-Python Schwartz & Hearst implementation (84.21<!--claim:extraction.med1250.acronymkit.exact_f1:.2f--> against 82.48),
  on higher recall (77.31<!--claim:extraction.med1250.acronymkit.exact_recall:.2f--> against 73.46).
- We lose narrowly to the Rust implementation (84.21<!--claim:extraction.med1250.acronymkit.exact_f1:.2f--> against 84.44), and the gap is
  now 0.23 of a point rather than
  the 0.59 it was before `balanced_trim` shipped (D-032). It buys precision
  (96.42 against 92.46<!--claim:extraction.med1250.acronymkit.exact_precision:.2f-->) at the cost of recall (75.10 against 77.31<!--claim:extraction.med1250.acronymkit.exact_recall:.2f-->) — a different
  operating point, not a different league.
- **† The import column needs a caveat, and refusing it would be dishonest.** `import acronymkit`
  now costs 2.3 ms because the package resolves its re-exports lazily. But
  `from acronymkit import AcronymEngine` still costs 128.1 ms, and import-plus-first-result is
  196.0 ms — essentially unchanged. Lazy re-export **moves** the pydantic cost to first use; it
  does not remove it. Quoting 2.3 ms against `pyab3p`'s 3.6 ms would compare their working API
  against our shell. The honest reading is that we no longer punish a process that merely imports
  the package, and that our time-to-first-answer is still the slowest here.

**The Python column is the one row where we are alone.** `pyab3p` publishes no wheels past CPython
3.12 and `scispacy` declares `requires-python <3.13`; both had to be driven from a separate 3.12
interpreter to appear in this table at all. Compiled bindings around 2008 C++ will lag every CPython
release, structurally and permanently. That is not a benchmark result, it is an architectural fact,
and it is worth more than a point of F1 to anyone on a current interpreter.

The hypothesis that a zero-dependency pure-Python library would win on footprint is **not supported
by this table**: `pyab3p` is smaller, imports faster, has no runtime dependencies *and* scores
higher. The honest differentiation is elsewhere — no compiled extension to build or trust, MIT
throughout with no binary blobs, typed schema-validated output, and a generation/backronym/
disambiguation surface that none of these three have at all. Speed and size are not the argument.

### Three implementations truncate identically

Fed `"...proton pump inhibitors (PPIs)..."`, `acronymkit`, `abbreviations` and
`abbreviation_extractor` all return `"pump inhibitors"`. `pyab3p` alone returns
`"proton pump inhibitors"`.

Three independent Schwartz & Hearst implementations agreeing on the same wrong answer is good
evidence that the transcription here is faithful and that the truncation is a property of the
published algorithm, not a bug in any one of them. It is also precisely the gap Ab3P was built to
close.

## Generation: recall@k over 1,221 real pairs

Generation previously had no external evaluation — sixteen textbook initialisms, which is a smoke
test wearing an evaluation's clothes. A pair corpus is a generation gold standard read backwards:
feed the long form in and ask at what rank the human's short form comes back.

Pairs are bucketed first, because MED1250 is full of abbreviations no initialism generator can
produce by construction (`DAP → 2,6-diaminopurine`, `T3`, `[Ca2+]i`). Scoring those as failures
would measure the corpus, not the generator:

| Bucket | n | Meaning |
|---|---:|---|
| initialism | 546 | every short-form letter is the initial of a long-form word, in order — the fair target |
| subword | 398 | the short form draws on characters *inside* words — out of reach by design |
| unreachable | 277 | non-alphabetic or outside the length bounds |

Recall over the **initialism** bucket:

| Preset | R@1 | R@5 | R@10 | R@25 |
|---|---:|---:|---:|---:|
| **`strict_initialism`** | 75.5 % | 87.9 % | 88.3 % | 89.7 % |
| `balanced_pronounceable` | 63.4 % | 88.1 % | 88.6 % | 89.7 % |
| `max_pronounceable` | 10.3 % | 38.3 % | 65.6 % | 89.2 % |
| `dictionary_backronym` | 13.0 % | 62.8 % | 84.2 % | 89.2 % |

`recall@1` is a lower bound on quality, not an accuracy score: gold acronyms are what humans chose,
and several expansions have more than one defensible abbreviation. The rank distribution matters
more than any single figure — the median rank for the default preset is 1.

Two things fall out of this table that sixteen test cases could never have shown:

1. **The presets differ enormously at rank 1 and converge at rank 25** (89.2–89.7 % for all four).
   They are re-ranking a shared candidate pool rather than searching differently, which is exactly
   what they claim to do. That is the first direct evidence the preset design works.
2. **About 10 % of the initialism bucket never appears at all**, even at rank 25. That is a
   *coverage* ceiling in the search, not a ranking failure, and no amount of re-weighting will move
   it. It is the most concrete generator defect this project has ever had a number for.

### Two match conventions, both reported

Published numbers in this area are not directly comparable, because papers disagree about what counts
as correct. Two conventions are scored here and always labelled:

- **exact** — predicted long form equals the annotation after whitespace collapse and case folding.
- **relaxed** — additionally tolerates a leading determiner and edge punctuation.

The gap is 0.09 points, which is itself informative: boundary disagreement is *not* what limits this
system. The misses are real misses.

### Where the misses come from

Categorised over all 261 pairs missed under the relaxed convention. Regenerate with
`python bench/analyse_misses.py --save`; the counts below come from `bench/results.json`:

| Share | Count | Category |
|---:|---:|---|
| 28.7 % | 75 | long-form boundary chosen differently from the annotator |
| 18.8 % | 49 | digits in the short form (`2D`, `T3`, `FEV(1.0)`) |
| 14.6 % | 38 | short-form characters not present in order in the long form |
| 11.1 % | 29 | brackets inside the short form (`[Ca2+]i`, `k(a)`, `P(2)/P(1)`) |
| 8.8 % | 23 | no uppercase letter in the short form (`aa`, `h2`) — **configuration** |
| 8.8 % | 23 | multi-word short form (`MEF cells`) |
| 8.8 % | 23 | short form shorter than two characters (`M`, `P`, `T`) — **configuration** |
| 0.4 % | 1 | long form exceeds the algorithm's word budget |

Two of these are **configuration**, not algorithm: 46 pairs (17.6 % of misses) are rejected by
`extraction_min_short_form_length=2` and by the requirement that a short form contain an uppercase
letter. Both defaults exist to protect precision on general prose, where single lowercase letters in
brackets are almost never abbreviation definitions. Biomedical text is the case where that trade
costs the most.

The `//!ord`-style category (14.6 %) is out of scope by construction: the algorithm requires the
short form's characters to appear *in order*.

## A negative result: long-form boundary selection

The largest miss category is boundary disagreement, and it is expensive twice over. The reference
matcher walks right-to-left and accepts the first alignment it reaches, which is by construction the
*shortest*. On real text that truncates:

```
IIEF   gold "International Index of Erectile Function"
       got  "Index of Erectile Function"
PPIs   gold "proton pump inhibitors"
       got  "pump inhibitors"
```

The second `I` and the `E` are consumed from *inside* `"Erectile"` before the scan ever reaches
`"International"`. Each such case produces a false negative **and** a false positive, so fixing it
should raise precision and recall together.

**Hypothesis.** Instead of taking the greedy match, enumerate every plausible starting boundary, keep
the candidates the reference matcher validates from their first character, and choose the one where
the most short-form characters land on word initials — which is what an abbreviation actually is.

**Result: rejected. It made things worse.**

| Variant | Exact F1 | Δ |
|---|---:|---:|
| Reference algorithm (shipped) | **84.78** | — |
| Maximise initial alignment, word + hyphen boundaries | 83.36 | −1.42 |
| Same, count instead of fraction | 83.36 | −1.42 |
| Same, hyphen boundaries restricted to alphabetic prefixes | 84.69 | −0.09 |

The diagnosis is more useful than the attempt. Allowing a long form to begin after a hyphen fixed
exactly three pairs (`HDL → high-density lipoprotein`, and two like it, where a qualifier such as
`non-` is not part of the term) and broke **eighteen**, essentially all of them chemical nomenclature:

```
DAP    gold "2,6-diaminopurine"                    got "diaminopurine"
TMP    gold "4,5',8-trimethylpsoralen"             got "trimethylpsoralen"
CNQX   gold "6-cyano-7-nitroquinoxaline-2,3-dione" got "cyano-7-nitroquinoxaline-2,3-dione"
```

Locants are part of a compound's name; a `non-` prefix is not. Restricting hyphen starts to purely
alphabetic prefixes separates the two cases and recovers almost all of the loss — but only *almost*.
At 84.69 it still fails to beat the reference algorithm, so it was reverted rather than shipped:
complexity that cannot be justified with a number is a liability.

What this shows is that the greedy right-to-left match is a stronger baseline than it looks. Its
truncation is visible and annoying, and the obvious fix does not pay for itself. Beating it likely
needs what Ab3P actually did — per-candidate precision estimates learned from data — rather than a
better boundary heuristic.

## The generation coverage ceiling is tokenisation, not search

All four presets converge to about 89.74 % recall@25, which means a slice of the initialism
bucket is never produced *at any rank by any preset*. Diagnosing that is the generation analogue of
the extraction miss taxonomy.

Measured with the candidate pool opened to depth 100,000, so "produced" means *present in the pool*
rather than *in the top 25*:

- **51 of 546 pairs (9.34 %) are never generated at all.** That is the ceiling.
- A further 5 are generated but sit beyond rank 25 under every preset. That is ranking, not
  coverage, and is deliberately excluded from the ceiling.
- **All four presets have an identical pool** (90.66 % each, union 90.66 %). That is direct
  confirmation of the claim the presets have always made and never demonstrated: they re-rank one
  shared candidate set rather than searching differently.

### Cause taxonomy

| Share | n | Cause |
|---:|---:|---|
| 31.4 % | 16 | compound capped by `max_letters_per_token` — `NMDA ← N-methyl-D-aspartate` |
| 25.5 % | 13 | one-letter word dropped by `min_word_length` — `HBV ← hepatitis B virus` |
| 21.6 % | 11 | word suppressed as a stop word — `QOL ← quality of life` |
| 7.8 % | 4 | compound donates prefixes only — `ERK ← extracellular signal-related kinase` |
| 5.9 % | 3 | existing acronym is atomic — `hTR ← human telomerase RNA` |
| 2.0 % | 1 | **search budget / beam pruning** |
| 0.0 % | 0 | unrepresentable from any token stream |

**82.3 % of the ceiling is configuration defaults, not the algorithm.** Beam width accounts for
exactly 1 pair, and nothing at all is genuinely unrepresentable.

### The experiment that settles it

| Arm (`strict_initialism`) | recall@25 | pool recall |
|---|---:|---:|
| control | 89.74 % | 90.66 % |
| beam 100,000 / 5 M nodes / bounds 1–12 | 89.74 % | 90.84 % |
| the same, plus relaxed tokenisation | 91.58 % | **98.90 %** |

A search budget four orders of magnitude larger moves recall@25 by **0.00**. Relaxing tokenisation
moves pool recall by **8.24 points**. The ceiling is tokenisation, and no amount of search
will touch it.

### The subword bucket, reported separately for the first time

Pool recall over the 398 subword pairs is 5.78 %. `MappingKind.CONTIGUOUS` exists to let one
token donate several characters, and on this corpus it recovers very little — worth knowing before
anyone invests further in sub-word matching for generation.

## Disambiguation: measured for the first time, and it loses to a trivial baseline

A third of this library's surface had no evidence behind it for three rounds. It does now, and the
number is bad.

SDU@AAAI-21 shared task 2, dev split: 6,189 instances, 2,212 instances/second.
Scored with a faithful reimplementation of the shared task's own `scorer.py` — exact string equality,
macro-averaged P/R/F1 as the headline, accuracy alongside.

| System | Accuracy % | macro P | macro R | macro F1 |
|---|---:|---:|---:|---:|
| ceiling (gold always among the candidates) | 100.00 | | | |
| **`most_frequent`** (shared task baseline) | **72.84** | 89.03 | 44.94 | 59.73 |
| `acronymkit`, stock `Config()` | 41.65 | 68.07 | 44.85 | 54.07 |
| random, seeded | 31.72 | 55.73 | 32.40 | 40.98 |

**Simply always picking the most common expansion beats our context scoring by a wide margin**
(72.84 % against 41.65 %). We are above random, so the context signal is not nothing — but on
this benchmark it is worth less than ignoring the context entirely and memorising frequencies.

Accuracy by number of candidate expansions:

| candidates | 2 | 3 | 4 | 5 | 6–9 | 10+ |
|---|---:|---:|---:|---:|---:|---:|
| `most_frequent` | 82.1 | 79.7 | 78.6 | 66.3 | 61.7 | 39.1 |
| `acronymkit` | 55.3 | 44.4 | 35.1 | 35.1 | 25.6 | 27.1 |
| random | 50.3 | 34.2 | 23.9 | 20.8 | 13.6 | 7.7 |

**Harness validated.** Our reimplementation of the shared task's own most-frequent baseline
reproduces its published official scores to the digit (89.03 / 44.94 / 59.73) — the same role
`pyab3p` plays for the extraction harness. The result is about the system, not the scoring.

Two diagnostics recorded rather than acted on: inline definitions take top-1 on 158 instances and
override a correct dictionary candidate on 29 of them, because an inline expansion is copied
verbatim from the sentence and cannot exact-match a lower-cased dictionary key. That is the right
default for a caller reading a document and the wrong one for this benchmark; it was left alone,
because tuning to a benchmark is how a number stops meaning anything.

**Nothing was tuned to produce this table.** Stock defaults, measured once. `EngineTier.NEURAL`
exists precisely because a bag-of-words overlap was never expected to be competitive here; this
quantifies by how much.

## PLOD: a second corpus, and a premise of mine that was wrong

PLOD was added to close the domain-generalisation gap. **It does not, because PLOD is not
non-biomedical.** It is PLOS journal text dominated by the life sciences — SDS-PAGE, shRNA,
eicosapentaenoic acid. It is a different corpus, genre, annotation provenance and task, and that is
worth having, but it is not a different domain. Every place this project called it a
"non-biomedical counterweight" — including `bench/splits.toml` — was wrong and has been corrected.
**The domain-generalisation gap remains open.**

Evaluated on PLOD's *own* task. It labels short-form and long-form spans without pairing them, and a
gold standard we partly invented cannot adjudicate our own system, so no pairing was derived. Two
independent span-detection scores instead, in token space, PLOD-CW test split:

| System | SF exact P / R / F1 | LF exact P / R / F1 | LF overlap F1 |
|---|---|---|---:|
| `allcaps` | 60.13 / 69.26 / **64.37** | — | — |
| **`acronymkit HIGH_PRECISION`** | 97.06 / 36.67 / **53.23** | 88.24 / 59.21 / 70.87 | 75.59 |
| `acronymkit BIOMEDICAL` | 93.52 / 37.41 / **53.44** | 83.33 / 59.21 / 69.23 | 73.85 |
| `pyab3p` | 95.15 / 36.30 / **52.55** | 85.44 / 57.89 / 69.02 | 74.51 |
| `abbreviation_extractor` | 94.68 / 32.96 / **48.90** | 87.23 / 53.95 / 66.67 | 70.73 |
| `abbreviations` | 95.65 / 32.59 / **48.62** | 90.22 / 54.61 / 68.03 | 70.49 |
| `scispacy` | 95.65 / 32.59 / **48.62** | 84.78 / 51.32 / 63.93 | 69.67 |

**A one-line all-caps rule beats every definition extractor on short forms**, 64.37 against our
53.23. On PLOD's task a capitalisation heuristic is simply a better answer, and the reason is
structural: PLOD annotates every *mention* of an abbreviation while a Schwartz & Hearst extractor
returns every *definition*. Only 37.78 % of gold short-form spans are reachable by any
definition-based method at all. That is the same lesson as the disambiguation result — measure
against the stupid baseline first, because sometimes it wins.

Two findings cut the other way and are real:

- **Among definition extractors we lead on both labels — including against `pyab3p`**, which beats
  us 88.87 to 83.85 on MED1250. The cross-system ordering is *corpus-dependent*. That is the first
  measured evidence that one corpus was never enough to rank these systems, and it applies to our
  own MED1250 table as much as to anyone's.
- 97.06 % short-form precision is the highest any configuration of this library has recorded, on a
  corpus it had never seen.

Detokenisation is the honest difficulty and it was priced rather than assumed. PLOD ships tokens;
our extractor takes text. Two join styles were measured: under a space join, two of the baselines
collapse to near-zero (they emit one pair across 153 sentences), so the tight join is primary — and
our own figure is *higher* under the join that was rejected, so the choice is not self-serving.

## Operating points, not a single setting

At roughly 92 % precision against 76 % recall there is precision available to spend, and a
sixth of the misses come from configuration rather than from the algorithm. Those knobs are named
rather than silently retuned, and each one's cost is published. Selected on the development half,
reported on the held-out half:

| Profile | dev F1 | test P % | test R % | test F1 % |
|---|---:|---:|---:|---:|
| `HIGH_PRECISION` (defaults) | 84.07 | 92.32 | 76.47 | 83.65 |
| `GENERAL` | 84.17 | 92.18 | 76.79 | **83.78** |
| `BIOMEDICAL` | 83.07 | 86.23 | **79.65** | 82.81 |

```python
from acronymkit import AcronymEngine, Config
from acronymkit.enums import ExtractionProfile

engine = AcronymEngine(Config.for_profile(ExtractionProfile.BIOMEDICAL))
```

`BIOMEDICAL` trades precision for recall (86.23 / 79.65 against the defaults' 92.32 / 76.47) by
admitting single-character and lowercase short forms — `aa`, `h2`, `M`, `T` are real abbreviations in this domain. Whether that is
a good trade depends entirely on what happens downstream, which is the caller's information, not
ours.

**The defaults did not move.** `GENERAL` edges them on held-out data (83.78 against 83.65), a gap
inside the noise this project has previously reverted changes for, and consistency matters more than
a tenth of a point. There is also no `HIGH_RECALL` profile: the sweep produced no point that beat
`BIOMEDICAL` on recall, and inventing one would mean shipping a distinction the measurements do not
support.

## The governed subsystem: its first accuracy figures

The governed half of this package is 9,370 of 25,210 source lines and, until this table, carried no
accuracy number at all. The justification on file was "exact by construction", which is a tautology
rather than a measurement: a lookup table is exact about whatever the caller put into it.

There is exactly one thing in that subsystem which decides anything on its own, and
`src/acronymkit/governed/tokenizer.py` says so in its own docstring — where the identifier is cut
into tokens. Everything downstream is a lookup against a catalog the caller supplies, and a cut in
the wrong character position produces a token no catalog can contain. So the accuracy question for
the governed subsystem is: **does it cut identifiers where the people who named them cut them?**

### The gold, and the rule that makes it defensible

Two public sources publish, for the same column, a machine identifier *and* a human caption written
by the same organisation: SEC XBRL tag/label pairs and Socrata field/caption pairs. That caption is
the gold. Nobody was commissioned to produce it for a benchmark, which is the point — the August
2026 audit's first killed finding was a column corpus whose annotators were *instructed to invent
abbreviations*, then scored as if it were real schema text.

A caption is admitted only when **its alphanumerics case-fold equal the identifier's and it contains
whitespace.** Everything where the caption expands, abbreviates, reorders or annotates is thrown
away — `qty` / `Quantity Ordered` is not in this table, because scoring it would be scoring
expansion, which is the catalog's job. What survives is a population where the two strings are the
same characters and **only cut placement can differ**, so a disagreement is a segmentation
disagreement and nothing else.

Scored through the public API — `expand_identifier(identifier, GovernedDictionary({}))` — with an
**empty** catalog, which the admission rule forces rather than merely permits: a populated catalog
would rewrite `TXN` to `Transaction` and the two strings would no longer share a character stream.

### The table, with its ceiling in it

A cut is a position in the shared character stream; punctuation inside a caption is a cut, not only
whitespace. **Boundary recall ceiling** is the share of gold cuts sitting where the identifier
itself marks one — a separator, a camelCase change, a letter/digit change, or the end of a capital
run. Nothing that refuses to guess can exceed it, so a recall figure printed without it is
unreadable.

| Who wrote the gold | Subset | Pairs | exact % | boundary P % | boundary R % | boundary F1 % | recall ceiling % |
|---|---|---:|---:|---:|---:|---:|---:|
| SEC, us-gaap taxonomy | all | 3,090<!--claim:governed_gold.sec_xbrl.us_gaap.all.pairs:,--> | **98.25<!--claim:governed_gold.sec_xbrl.us_gaap.all.exact_pct:.2f-->** | 99.98<!--claim:governed_gold.sec_xbrl.us_gaap.all.boundary_precision_pct:.2f--> | 99.62<!--claim:governed_gold.sec_xbrl.us_gaap.all.boundary_recall_pct:.2f--> | 99.80<!--claim:governed_gold.sec_xbrl.us_gaap.all.boundary_f1_pct:.2f--> | 99.62<!--claim:governed_gold.sec_xbrl.us_gaap.all.boundary_recall_ceiling_pct:.2f--> |
| SEC, IFRS taxonomy | all | 939<!--claim:governed_gold.sec_xbrl.ifrs.all.pairs:,--> | **85.52<!--claim:governed_gold.sec_xbrl.ifrs.all.exact_pct:.2f-->** | 100.00<!--claim:governed_gold.sec_xbrl.ifrs.all.boundary_precision_pct:.2f--> | 97.50<!--claim:governed_gold.sec_xbrl.ifrs.all.boundary_recall_pct:.2f--> | 98.74<!--claim:governed_gold.sec_xbrl.ifrs.all.boundary_f1_pct:.2f--> | 97.50<!--claim:governed_gold.sec_xbrl.ifrs.all.boundary_recall_ceiling_pct:.2f--> |
| SEC, filing registrants | all | 57,580<!--claim:governed_gold.sec_xbrl.filer_extension.all.pairs:,--> | **94.73<!--claim:governed_gold.sec_xbrl.filer_extension.all.exact_pct:.2f-->** | 99.73<!--claim:governed_gold.sec_xbrl.filer_extension.all.boundary_precision_pct:.2f--> | 98.76<!--claim:governed_gold.sec_xbrl.filer_extension.all.boundary_recall_pct:.2f--> | 99.25<!--claim:governed_gold.sec_xbrl.filer_extension.all.boundary_f1_pct:.2f--> | 98.76<!--claim:governed_gold.sec_xbrl.filer_extension.all.boundary_recall_ceiling_pct:.2f--> |
| | marked | 57,312<!--claim:governed_gold.sec_xbrl.filer_extension.marked.pairs:,--> | 95.17<!--claim:governed_gold.sec_xbrl.filer_extension.marked.exact_pct:.2f--> | 99.73<!--claim:governed_gold.sec_xbrl.filer_extension.marked.boundary_precision_pct:.2f--> | 99.16<!--claim:governed_gold.sec_xbrl.filer_extension.marked.boundary_recall_pct:.2f--> | 99.44<!--claim:governed_gold.sec_xbrl.filer_extension.marked.boundary_f1_pct:.2f--> | 99.16<!--claim:governed_gold.sec_xbrl.filer_extension.marked.boundary_recall_ceiling_pct:.2f--> |
| | **flatcase** | 268<!--claim:governed_gold.sec_xbrl.filer_extension.unmarked.pairs:,--> | **0.75<!--claim:governed_gold.sec_xbrl.filer_extension.unmarked.exact_pct:.2f-->** | 77.78<!--claim:governed_gold.sec_xbrl.filer_extension.unmarked.boundary_precision_pct:.2f--> | **0.47<!--claim:governed_gold.sec_xbrl.filer_extension.unmarked.boundary_recall_pct:.2f-->** | 0.93<!--claim:governed_gold.sec_xbrl.filer_extension.unmarked.boundary_f1_pct:.2f--> | 0.47<!--claim:governed_gold.sec_xbrl.filer_extension.unmarked.boundary_recall_ceiling_pct:.2f--> |
| Socrata publishers | all | 26,536<!--claim:governed_gold.socrata.columns.all.pairs:,--> | **91.37<!--claim:governed_gold.socrata.columns.all.exact_pct:.2f-->** | 97.63<!--claim:governed_gold.socrata.columns.all.boundary_precision_pct:.2f--> | 98.82<!--claim:governed_gold.socrata.columns.all.boundary_recall_pct:.2f--> | 98.22<!--claim:governed_gold.socrata.columns.all.boundary_f1_pct:.2f--> | 98.82<!--claim:governed_gold.socrata.columns.all.boundary_recall_ceiling_pct:.2f--> |
| | marked | 25,577<!--claim:governed_gold.socrata.columns.marked.pairs:,--> | 93.49<!--claim:governed_gold.socrata.columns.marked.exact_pct:.2f--> | 97.64<!--claim:governed_gold.socrata.columns.marked.boundary_precision_pct:.2f--> | 99.90<!--claim:governed_gold.socrata.columns.marked.boundary_recall_pct:.2f--> | 98.76<!--claim:governed_gold.socrata.columns.marked.boundary_f1_pct:.2f--> | 99.90<!--claim:governed_gold.socrata.columns.marked.boundary_recall_ceiling_pct:.2f--> |
| | **flatcase** | 959<!--claim:governed_gold.socrata.columns.unmarked.pairs:,--> | **34.93<!--claim:governed_gold.socrata.columns.unmarked.exact_pct:.2f-->** | 61.29<!--claim:governed_gold.socrata.columns.unmarked.boundary_precision_pct:.2f--> | **2.25<!--claim:governed_gold.socrata.columns.unmarked.boundary_recall_pct:.2f-->** | 4.33<!--claim:governed_gold.socrata.columns.unmarked.boundary_f1_pct:.2f--> | 2.25<!--claim:governed_gold.socrata.columns.unmarked.boundary_recall_ceiling_pct:.2f--> |

The flatcase rows are published beside the headline rather than under it, because they are the price
of a subsystem whose thesis is that it refuses to guess. `casenumber` carries no mark, its publisher
captioned it `Case Number`, and there is no way to recover that cut from the characters. The two SEC
taxonomy arms have no flatcase row at all — XBRL element names are written by a convention that
capitalises every word, so a flatcase tag barely exists.

### The result that is not in the headline column

**Every miss, on every arm, is a boundary the identifier does not mark.** `false_negatives_marked`
is zero on all four arms, so boundary recall equals its ceiling to the digit on every row above.

Half of that is arithmetic and should not be sold as a discovery: the splitter only cuts where one
of its four rules fires, and the ceiling is defined as the union of those same four rules' firing
positions, so a *spurious* cut at an unsignalled position is impossible by construction. The other
half is not. Two of the splitter's rules can *suppress* a cut at a signalled position — rule 6 keeps
an English ordinal suffix with its digits, so `1ST` is one token, and rule 9's two-pass join
re-merges a split that a catalog vouches for. Either could have cost a boundary the publisher
wanted. Across every pair in the table above, neither did once.

So the whole of the recall loss is unmarked text, and the whole of the precision loss is a signal
the publisher chose not to treat as a word break. That makes the precision column the diagnostic
one, and it decomposes into named rules:

| Arm | Rule that cut where the publisher did not | Count |
|---|---|---:|
| Socrata | letter/digit, rule 5 — `_2013_q1_actual` gives `2013 Q 1 Actual`, gold `2013 Q1 Actual` | 1,818<!--claim:governed_gold.socrata.columns.false_positives_by_signal.letter_digit:,--> |
| Socrata | separator, rule 2 | 16<!--claim:governed_gold.socrata.columns.false_positives_by_signal.separator:,--> |
| SEC filer | end of a capital run, rule 4 — `ATMandDebitCardExpense` gives `At Mand Debit Card Expense` | 581<!--claim:governed_gold.sec_xbrl.filer_extension.false_positives_by_signal.acronym_run:,--> |
| SEC filer | letter/digit, rule 5 | 362<!--claim:governed_gold.sec_xbrl.filer_extension.false_positives_by_signal.letter_digit:,--> |
| SEC us-gaap | camelCase, rule 3 | 2<!--claim:governed_gold.sec_xbrl.us_gaap.false_positives_by_signal.camel_case:,--> |
| SEC us-gaap | end of a capital run, rule 4 | 1<!--claim:governed_gold.sec_xbrl.us_gaap.false_positives_by_signal.acronym_run:,--> |

Rule 5 is the single largest source of disagreement anywhere in this table and it is a *deliberate*
rule: digits in a physical name are ordinals and version markers, and `ADDRESS2` really is
`Address 2`. Publishers write `Q1` and `COVID19` as one word. Nothing was changed in response to
this — it is a measured cost of a documented decision, not a defect report.

### Two decompositions the headline does not survive, and one it does

**By who wrote the taxonomy.** `us-gaap` and IFRS tags come out of the same file, the same fetch and
the same scorer, and their exact-match scores are twelve points apart:
98.25<!--claim:governed_gold.sec_xbrl.us_gaap.all.exact_pct:.2f--> against
85.52<!--claim:governed_gold.sec_xbrl.ifrs.all.exact_pct:.2f-->. The cause is editorial. `us-gaap`
capitalises after stripping a hyphen, so `Paid-in` becomes `PaidIn` and the cut survives into the
identifier; the IFRS taxonomy does not, so `paid-in` becomes `Paidin` and the cut is destroyed by
the naming convention before this package ever sees the string. Pooling the two into one "SEC XBRL"
figure would have hidden that spread behind an average.

**By identifier shape.** The whole gold is `snake_lower`, `flat_lower` and `CamelCase`. It contains
**no UPPER_SNAKE identifier at all**, and the dotted count is
29<!--claim:governed_gold.sec_xbrl.filer_extension.identifier_shapes.dotted:,--> of
57,580<!--claim:governed_gold.sec_xbrl.filer_extension.all.pairs:,-->. UPPER_SNAKE is the shape this
package's own fixtures and documentation are built around, so the largest caveat on this table is a
counted zero rather than a hedge.

**By publisher.** The Socrata population splits disjointly by portal —
111<!--claim:governed_gold.socrata.portal_half_a.portals:,--> portals against
105<!--claim:governed_gold.socrata.portal_half_b.portals:,-->, no portal in both — and the two halves land
at 91.36<!--claim:governed_gold.socrata.portal_half_a.all.exact_pct:.2f--> and
91.65<!--claim:governed_gold.socrata.portal_half_b.all.exact_pct:.2f--> exact match. The pooled figure is
not an artifact of a handful of large portals. This is a robustness check and not a train/test
split: nothing was fitted, so there was nothing to hold out.

**By name length, which it survives in the direction it has to.** A longer name has more cuts to get
right, so a whole-identifier metric must fall with length; if it did not, it would be measuring
something other than what it says. Socrata two-word captions score
93.45<!--claim:governed_gold.socrata.columns.exact_pct_by_caption_words.2:.2f--> exact and six-word-or-longer
captions 83.95<!--claim:governed_gold.socrata.columns.exact_pct_by_caption_words.6+:.2f-->, over
9,628<!--claim:governed_gold.socrata.columns.pairs_by_caption_words.2:,--> and
4,306<!--claim:governed_gold.socrata.columns.pairs_by_caption_words.6+:,--> pairs respectively. The full
breakdown is in `bench/results.json` under `exact_pct_by_caption_words`.

### What limits these numbers, in the same paragraph as the numbers

The gold is **how a publisher captioned a column, not how a data-governance function would rule** —
and the publishers do not agree with each other. Where two portals caption the same identifier,
68<!--claim:governed_gold.socrata.gold_conflict.contested_identifiers:,--> of
25,117<!--claim:governed_gold.socrata.gold_conflict.distinct_identifiers:,--> identifiers
(0.27<!--claim:governed_gold.socrata.gold_conflict.contested_identifiers_pct--> %) are given two different
cut placements — 2.62<!--claim:governed_gold.socrata.gold_conflict.contested_occurrences_pct--> % of admitted
column occurrences sit on such an identifier — which is a floor under the disagreement any system
will record here however good it is. The August 2026 audit also ran a hand pass over a sample of these pairs and judged the automated
figure optimistic; that comparison is un-gated, is not re-derived by this runner, and its number is
therefore deliberately not quoted here — read it in [`docs/AUDIT-2026-08.md`](AUDIT-2026-08.md) and
treat the table above as the optimistic end. The SEC arms also measure something narrower than they
look: XBRL element names are written by the LC3 convention, under which the element name **is** the
label with its spaces and punctuation removed, so those rows measure inverting a documented,
mechanical name-generation rule rather than segmenting an identifier somebody typed. And the shape
counts above are the transfer limit, stated as counts rather than as a hedge: the gold is
`snake_lower` and `CamelCase`, it holds **zero** UPPER_SNAKE identifiers, and `dotted`,
`flat_upper`, `snake_mixed` and `digits_only` appear only in trace amounts. UPPER_SNAKE is what the
package's own fixtures are written in, and no dotted source publishes a caption to align against, so
**these figures do not transfer to FEC- or World-Bank-shaped input** and they say nothing at all
about the `TXN_APPLNT_DOB_DT` shape the documentation is built around.

### What is not measured here

Catalog resolution, class-word detection, compliance checking and physical-name generation are all
lookups against data the caller supplies, and none of them is in this table. Nor is expansion: the
admission rule removes every pair whose caption is longer than its identifier, which is exactly the
abbreviation-expansion task. This is the one judgement the governed subsystem makes on its own,
measured once, on the shipped code path, with stock defaults.

### Provenance

Both corpora are fetched by the runner, so the table is re-derivable by anyone with a network
connection. Neither was used to tune anything, and the runner has no thresholds and no arms to
choose between.

| Corpus | Endpoint | Licence, read from the terms |
|---|---|---|
| SEC XBRL | `www.sec.gov/files/dera/data/financial-statement-data-sets/<quarter>.zip`, member `tag.txt` | sec.gov "Website Dissemination", read 2026-08-23: information on sec.gov "may be copied or further distributed by users of the web site without the SEC's permission". The archive's own `readme.htm` carries no licence, copyright or terms statement. **But the SEC does not own these labels** — `readme.htm` section 5.2 says `tlabel` is "the label text provided by the taxonomy" for a standard tag, so us-gaap labels are FASB's and IFRS labels are the IFRS Foundation's. Benchmark use; **not vendorable.** |
| Socrata | `api.us.socrata.com/api/catalog/v1`, fields `columns_field_name` and `columns_name` | No licence covers the catalog metadata: the Discovery API indexes third-party portals whose datasets carry per-publisher terms. The one licence statement in sight — "Licensed by Tyler Technologies under CC BY-NC-SA 3.0", in the footer of `dev.socrata.com`, read 2026-08-23 — covers the **documentation**, not the API responses, and reading it as the data's licence would be the badge mistake operating rule 4 exists to stop. Column metadata only; no dataset rows are read. Benchmark use; **not vendorable.** |

The SEC archive is fetched with HTTP range requests against the ZIP central directory, so only the
one member is downloaded rather than the whole quarterly archive. The Socrata catalog is live and
moves under the runner, so a later run walks a slightly different population; the fetch date and the
page count travel with every figure in `bench/results.json`.

**Neither corpus is registered in [`bench/splits.toml`](../bench/splits.toml) yet, and every figure
above carries that fact.** The runner asks `tools/splits.py` for each corpus's declared role, prints
what it gets, and writes it into `bench/results.json` as `splits_declaration` — currently
`UNDECLARED`. It refuses to run against a corpus declared `role = "tuning"`. Two things block
registration and both are somebody else's file: the manifest's `task` vocabulary is closed and holds
no value for identifier segmentation, and `headline_capable()` in `tools/splits.py` is task-blind, so
registering a segmentation corpus as `held_out` would silence the advisory that says this project
still has no held-out short-form/long-form pair corpus. That advisory is about extraction and is
still true. Until both are settled, read these numbers as measured-but-undeclared.

## What is deliberately not claimed

**No comparison to published figures.** Numbers lifted from papers are not comparable to numbers from
this harness: different tokenisation, different match conventions, sometimes a different subset of the
corpus. Quoting someone else's F1 next to ours would be dishonest by accident, which is why the
harness runs baselines through the same reader and the same scorer instead.

scispaCy's `AbbreviationDetector` is the one baseline still missing. It requires Python <3.13 and a
spaCy model in the hundreds of megabytes; the harness supports it
(`--system scispacy --interpreter <py3.12>`) and it was not installed in time for this run.

**One corpus, one domain.** MED1250 is biomedical abstracts. The configuration defaults that cost
17.6 % of the misses here are tuned for general prose, so this number is a lower bound for biomedical
text and says little about legal, financial or general-web text. PLOD has now been evaluated (below) — but it turned out **not** to be the
non-biomedical counterweight it was assumed to be, so the domain gap is still open.

**Extraction only.** Generation, backronym alignment and disambiguation have no external evaluation
at all. The generation presets are pinned against a 16-phrase canonical corpus
(`tools/tune_presets.py`), which is a regression guard, not an evaluation.

## Adding a corpus

1. Register it in `tools/fetch_data.py` with its licence, checksum and whether it may be vendored.
2. Add a reader to `bench/corpora.py` returning `GoldDocument` objects.
3. Run `python bench/run_extraction.py --corpus <name>`.

The scorer never learns which corpus it is looking at, so a new corpus is a reader, not a new
evaluation.
