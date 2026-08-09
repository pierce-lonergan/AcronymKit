# Evaluation

Until now `acronymkit`'s extractor could only claim to be a *faithful transcription* of Schwartz &
Hearst (2003). This page replaces that claim with a measurement.

## Reproduce

```bash
python tools/fetch_data.py med1250
python bench/run_extraction.py                # the table below
python bench/run_extraction.py --errors       # every missed and spurious pair
```

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

## Results

`acronymkit` 0.2.0-dev, default configuration, Python 3.13 on Windows AMD64:

| System | Match | P % | R % | F1 % | TP | FP | FN |
|---|---|---:|---:|---:|---:|---:|---:|
| `acronymkit` | exact | 92.20 | 78.46 | **84.78** | 958 | 81 | 263 |
| `acronymkit` | relaxed | 92.30 | 78.54 | **84.87** | 959 | 80 | 262 |

Throughput: 1,252 documents in 0.40 s (~3,100 docs/s, single-threaded, Tier 0).

**Precision is high and recall is the weak side.** That is the expected shape for this algorithm — it
is designed to refuse rather than guess — and it means the headline number is limited by what the
method declines to look for, not by wrong answers.

### Two match conventions, both reported

Published numbers in this area are not directly comparable, because papers disagree about what counts
as correct. Two conventions are scored here and always labelled:

- **exact** — predicted long form equals the annotation after whitespace collapse and case folding.
- **relaxed** — additionally tolerates a leading determiner and edge punctuation.

The gap is 0.09 points, which is itself informative: boundary disagreement is *not* what limits this
system. The misses are real misses.

### Where the 263 misses come from

Categorised over the 261 pairs missed under the relaxed convention:

| Share | Count | Category |
|---:|---:|---|
| 28.7 % | 75 | long-form boundary chosen differently from the annotator |
| 18.8 % | 49 | digits in the short form (`2D`, `T3`, `FEV(1.0)`) |
| 14.2 % | 37 | short-form characters not present in order in the long form |
| 11.1 % | 29 | brackets inside the short form (`[Ca2+]i`, `k(a)`, `P(2)/P(1)`) |
| 8.8 % | 23 | no uppercase letter in the short form (`aa`, `h2`) — filtered by config |
| 8.8 % | 23 | multi-word short form (`MEF cells`) |
| 8.8 % | 23 | short form shorter than two characters (`M`, `P`, `T`) — filtered by config |
| 0.8 % | 2 | long form exceeds the algorithm's word budget |

Two of these are **configuration**, not algorithm: 46 pairs (17.6 % of misses) are rejected by
`extraction_min_short_form_length=2` and by the requirement that a short form contain an uppercase
letter. Both defaults exist to protect precision on general prose, where single lowercase letters in
brackets are almost never abbreviation definitions. Biomedical text is the case where that trade
costs the most.

The `//!ord`-style category (14.2 %) is out of scope by construction: the algorithm requires the
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

## What is deliberately not claimed

**No comparison to published figures.** Numbers lifted from papers are not comparable to numbers from
this harness: different tokenisation, different match conventions, sometimes a different subset of the
corpus. Quoting someone else's F1 next to ours would be dishonest by accident, which is why the
harness runs baselines through the same reader and the same scorer instead.

`bench/run_extraction.py --system scispacy` will score scispaCy's `AbbreviationDetector` — the de
facto Python baseline — against exactly this corpus and scorer. It is not installed in the
environment that produced this page, so **no baseline row appears above**. Running it is the single
most valuable addition to this document.

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
