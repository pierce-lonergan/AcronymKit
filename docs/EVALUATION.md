# Evaluation

Until now `acronymkit`'s extractor could only claim to be a *faithful transcription* of Schwartz &
Hearst (2003). This page replaces that claim with a measurement.

## Reproduce

```bash
python tools/fetch_data.py med1250
python bench/run_extraction.py --save                     # our row
python bench/run_generation.py --all-presets --save       # generation recall@k
python bench/run_micro.py --save                          # latency and cold import

# competitor rows (pyab3p and scispacy need Python <3.13)
python bench/run_extraction.py --save     --system acronymkit --system abbreviations     --system abbreviation_extractor --system pyab3p     --interpreter /path/to/python3.12
```

Every number on this page is written into [`bench/results.json`](../bench/results.json) by those
runners, and `tools/check_claims.py` fails the build if any performance figure in the docs or the
source is not traceable back to it.

Takes about a second. The corpus is not committed — it is fetched into the git-ignored `data/` and
verified against a SHA-256 pinned in `tools/fetch_data.py`.

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

| System | Implementation | P % | R % | F1 % | docs/s | Install | Cold import | Deps |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| `pyab3p` | compiled C++ | 96.91 | 82.06 | **88.87** | 3,646 | 0.3 MB | 3.6 ms | 0 |
| `abbreviation_extractor` | compiled Rust | 96.42 | 75.10 | **84.44** | 24,603 | 3.0 MB | 22.9 ms | 0 |
| **`acronymkit`** | pure Python | 92.07 | 76.99 | **83.85** | 4,219 | 1.3 MB | 164.6 ms | 1 (pydantic) |
| `abbreviations` | pure Python | 94.03 | 73.46 | **82.48** | 10,746 | 0.03 MB | 31.1 ms | 1 (regex) |
| `scispacy` | spaCy pipeline | 90.45 | 72.89 | **80.73** | 52 | ~400 MB | n/a | many (spaCy) |

Footprint is measured on the installed distribution: unpacked size, cold `import` in a subprocess
(median of five, so it cannot be flattered by a warm module cache), and runtime dependency count.

**Reading this honestly:**

- `pyab3p` wins, and it should — it is the original NLM implementation, and Ab3P was developed
  against this very corpus, so it enjoys a home advantage no other row has. Its 96.96 / 83.62 also
  lands within half a point of the figures published for Ab3P on MED1250, which is the strongest
  available evidence that **this harness, reader and scorer are correct**.
- We beat the other pure-Python Schwartz & Hearst implementation (83.85 against 82.48),
  on higher recall (76.99 against 73.46).
- We lose narrowly to the Rust implementation (83.85 against 84.44). It buys precision
  (96.42 against 92.07) at the cost of recall (75.10 against 76.99) — a different
  operating point, not a different league.
- **We are the slowest thing here to import, by roughly 50×.** That is pydantic, it is a real
  user-visible cost, and it is a competitive weakness rather than a rounding error.

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
text and says little about legal, financial or general-web text. PLOD (CC BY-SA, non-biomedical) is
the natural counterweight and has a reader slot waiting in `bench/corpora.py`.

**Extraction only.** Generation, backronym alignment and disambiguation have no external evaluation
at all. The generation presets are pinned against a 16-phrase canonical corpus
(`tools/tune_presets.py`), which is a regression guard, not an evaluation.

## Adding a corpus

1. Register it in `tools/fetch_data.py` with its licence, checksum and whether it may be vendored.
2. Add a reader to `bench/corpora.py` returning `GoldDocument` objects.
3. Run `python bench/run_extraction.py --corpus <name>`.

The scorer never learns which corpus it is looking at, so a new corpus is a reader, not a new
evaluation.
