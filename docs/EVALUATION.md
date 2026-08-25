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
python bench/run_backronym.py --save                      # backronym properties and coverage
python tools/fetch_data.py plod-cw-test plod-cw-dev plod-cw-train sdu22-ae-legal-dev sdu22-ae-scientific-dev
python bench/run_monoculture.py --save     --interpreter /path/to/python3.12  # the S&H monoculture
python bench/run_monoculture.py --demo                    # the independence demonstration, no corpus needed

# competitor rows (pyab3p and scispacy need Python <3.13)
python bench/run_extraction.py --save     --system acronymkit --system abbreviations     --system abbreviation_extractor --system pyab3p     --interpreter /path/to/python3.12
```

Every number on this page is written into [`bench/results.json`](../bench/results.json) by those
runners, and `tools/check_claims.py` fails the build if a performance figure
**that the gate can recognise** is not traceable back to it. It used to say *any* figure, in this
file and in `README.md`, and that was false in both: the gate arms a number by metric-keyword
proximity or a trailing unit, so an uncited latency in microseconds passes and an uncited accuracy
percentage in the same position fails. What it cannot recognise it counts and publishes — see the residue line
that `tools/check_claims.py` prints on every run.

The two copies of that sentence are now checked against each other by
`tests/test_claims_gate_coverage.py`, because *one sentence written in two places and corrected in
one* is the defect shape this repository has hit four times and is the only part of the
stale-rationale class with an available gate.

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

**Which of these numbers leads, and which are supporting.** The governed cut-placement figures and
the monoculture measurement are what this project stands on. Extraction, generation, backronym
alignment and disambiguation are measured beside them and are **supporting** numbers that nobody
optimises for. That is a positioning decision rather than a property of the measurements, and it is
stated, costed and given its reversal conditions in [docs/POSITIONING.md](POSITIONING.md). It changes
nothing about how any figure below is derived or reported: every one of them keeps its losing
comparison in the same table either way.

**MED1250 is a tuning set, not a held-out one, and every number below is labelled accordingly.**
Its miss taxonomy has been read in full, a boundary experiment was run and reverted against it, and
the configuration knobs responsible for 17.6<!--claim:analysis.med1250.miss_taxonomy.config_attributable_pct:.1f--> % of its misses were identified from it. Nothing about
it is blind any more.

There is currently **no held-out short-form/long-form corpus**, and that is a stated gap rather than
an oversight — see [`bench/splits.toml`](../bench/splits.toml) for why (the BioC conversions of
BIOADI/MEDSTRACT/S&H are no longer fetchable, and the corpora that *are* reachable label spans
without pairing them, so deriving pairs would make part of the gold standard mine). Until that is
closed, treat the comparison as sound and the absolute level as provisional.

## What each runner sweeps, and what the library ships

**A benchmark runner that does not cover the shipped configuration surface reports a number about a
slice while wearing the name of the whole.** That is not a wrong measurement and no runner here has
ever produced one; it is a *scope* that has to be read off the source rather than off the table, and
it has now cost this project twice. `bench/run_shortform.py --spans` swept `HIGH_PRECISION` alone
while three extraction profiles ship, and the omission hid a sign change on the one held-out corpus
in the repository — the legend rule improves PLOD short-form exact precision under `HIGH_PRECISION`
and costs it under `BIOMEDICAL`. So every runner was enumerated rather than assumed clean, and the
result is below.

The axes are the ones a caller can actually change: `ExtractionProfile` (`HIGH_PRECISION`, `GENERAL`,
`BIOMEDICAL`, exported as `EXTRACTION_PROFILES`), `ScoringStrategy` (four presets plus `CUSTOM`,
which is not a preset), the detokenisation style PLOD forces a choice about, `min_margin` on the
disambiguator, and the catalog handed to the governed subsystem.

| Runner | Axis a caller can change | Swept | Reading |
|---|---|---|---|
| `run_extraction.py` | extraction profile | **one** — `Config()`, which is `HIGH_PRECISION` | **the gap that matters.** The flagship extraction figure this page leads with is one profile of three, and nothing on the row says so |
| `run_profiles.py` | extraction profile | **all three** | this is the runner whose whole subject is the axis; it covers it |
| `run_spans.py` | extraction profile × detokenisation | **all three × both** | complete, and it is the runner that established why reporting one style hides a choice |
| `run_shortform.py --variants` | extraction profile | **all three** | complete since it shipped |
| `run_shortform.py --spans` | extraction profile | **all three** | **fixed this round.** One before, and the one it swept was not the one that shows the cost |
| `run_shortform.py --legend` | extraction profile | **all three** | **fixed this round.** One before on PLOD and SDU-22, two on MED1250 |
| `run_shortform.py --legend-cost` | extraction profile | **all three** | complete since it shipped, which is why the profile-dependence was visible there first |
| `run_shortform.py --spend-legal-train` | extraction profile | **all three** | new this round |
| `run_shortform.py --gates` | extraction profile | **one** — `BIOMEDICAL` | defensible and *recorded*: the subject is what the admission gate admits, so the loosest gate is the instrument, and each run carries its own `profile` field |
| `run_cascade.py` | extraction profile | **one** — `Config()` | the subject is the cascade tier, not the gate; the profile is nonetheless a silent constant |
| `run_rerank.py` | extraction profile | **one** — `Config()` | as above, and its candidate space is fixed by construction |
| `run_termfreq.py` | extraction profile | **one** — `Config()` | as above |
| `run_oracle.py` | extraction profile | **one** for this library's row; its own candidate harvest hard-codes `min_length=1, max_length=14, require_uppercase=False` | those bounds are `BIOMEDICAL`'s exactly, which the runner nowhere says: it is the loosest shipped profile transcribed as three literals, so the reachability ceiling is a `BIOMEDICAL` ceiling while the row beside it is a `HIGH_PRECISION` score |
| `run_generation.py` | scoring strategy | **all four presets** | complete. `CUSTOM` is a caller-supplied weight vector, not a configuration this project can enumerate |
| `run_backronym.py` | scoring strategy | **one** — `Config()`, which is `STRICT_INITIALISM` | the subject is constraint satisfaction, which the weights cannot change; the strategy is still a silent constant |
| `run_disambiguation.py` | `min_margin` | **one** — off, which is the default | complete only when read with the runner below, which sweeps the gate ladder |
| `run_disambiguation_diagnosis.py` | `min_margin` | **a gate ladder** | this is where the axis is covered |
| `run_governed.py` | catalog | **one** — empty | stated in the runner |
| `run_governed_gold.py` | catalog | **one** — empty, and it refuses any other | argued at length rather than defaulted: a populated catalog scores the caller's table, not the library |
| `run_micro.py` | config preset | **two** — `Config.fast()` and `Config()` | partial by design; the subject is latency, and the presets that differ in cost are the two measured |

**Two runners are missing from the table on purpose.** `bench/run_monoculture.py` and
`bench/run_shortform_contest.py` were being written by other workstreams while this enumeration was
taken. Both were read once and both carry `PROFILES = ("high_precision", "general", "biomedical")`
and loop over it, so both were covering the axis at that moment — and a row asserting that about a
file somebody else is still editing is a sentence that goes stale before the commit lands, which is
this project's most-recorded failure. They are named here so the next enumeration knows to include
them rather than inheriting a table that silently omits them.

**What this table is and is not.** It is a statement about *source*, re-derivable by reading each
runner's construction of `Config`, and every cell was read rather than inferred from a run id.
It is not a claim that the uncovered cells would move — four of the runners marked **one** measure
something the profile cannot change, and saying so is different from having checked. The one place
the omission was checked, it moved, and it moved on the held-out corpus.

**The unfixed gap is named rather than fixed, and it is the largest one.**
`bench/run_extraction.py` produces the figure this page leads with, and sweeping it is not a runner
edit: `extraction.med1250.acronymkit` is cited by run id in this document, in `README.md` and in
`docs/DECISIONS.md`, so a sweep either adds a profile segment to a cited id or publishes three rows
under one name. That is a decision about the flagship number's identity and it belongs in a record,
not in a diff.

## Extraction: measured against four systems

Every row is produced by **this** harness — same reader, same scorer, same corpus — because numbers
from different harnesses are not comparable. Nothing here is quoted from a paper.

| System | Implementation | P % | R % | F1 % | docs/s | Install | Cold import | Deps | Python |
|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| `pyab3p` | compiled C++ | 96.91 | 82.06 | **88.87** | 3,646 | 0.3 MB | 3.6 ms | 0 | **≤ 3.12** |
| `abbreviation_extractor` | compiled Rust | 96.42 | 75.10 | **84.44** | 24,603 | 3.0 MB | 22.9 ms | 0 | 3.8+ |
| **`acronymkit`** | pure Python | 92.46<!--claim:extraction.med1250.acronymkit.exact_precision:.2f--> | 77.31<!--claim:extraction.med1250.acronymkit.exact_recall:.2f--> | **84.21<!--claim:extraction.med1250.acronymkit.exact_f1:.2f-->** | 5,496<!--claim:extraction.med1250.acronymkit.docs_per_second:,.0f--> | 1.3 MB | 2.3<!--claim:micro.import.cold_import_ms--> ms † | 1 (pydantic) | **3.9 – 3.13** |
| `abbreviations` | pure Python | 94.03 | 73.46 | **82.48** | 10,746 | 0.03 MB | 31.1 ms | 1 (regex) | 3.x |
| `scispacy` | spaCy pipeline | 90.45 | 72.89 | **80.73** | 52 | ~400 MB | n/a | many (spaCy) | **< 3.13** |

Footprint is measured on the installed distribution: unpacked size, cold `import` in a subprocess
(median of five, so it cannot be flattered by a warm module cache), and runtime dependency count.

**Reading this honestly:**

- `pyab3p` wins, and it should — it is the original NLM implementation, and Ab3P was developed
  against this very corpus, so it enjoys a home advantage no other row has. Through this harness it
  scores 96.91<!--claim:extraction.med1250.pyab3p.exact_precision:.2f--> /
  82.06<!--claim:extraction.med1250.pyab3p.exact_recall:.2f-->.

  **CORRECTED IN PLACE, AND THE CORRECTION MATTERS MORE THAN THE NUMBERS.** This sentence used to
  read *"Its 96.96 / 83.62 also lands within half a point of the figures published for Ab3P on
  MED1250, which is the strongest available evidence that this harness, reader and scorer are
  correct."* Three things were wrong with it. The pair `96.96 / 83.62` matches neither
  `bench/results.json` nor **the table five lines above it**, and appeared nowhere else in the
  repository. It was uncited, so no ratchet could see it. And it appealed to "the figures published
  for Ab3P" in a section whose own header states that **nothing here is quoted from a paper** —
  there is no such citation in this repository, and the argument rested on it.

  It had stood since the commit that created this file, through six audits, two adversarial passes
  and four documentation sweeps, and it was found by reading the document cold rather than by any
  gate. **The harness-correctness argument it carried is now withdrawn**, not restated at corrected
  values: an agreement between this harness and a paper nobody in this repository has read is not
  evidence of anything, and re-deriving "within half a point" from the real recall would fail by
  roughly a point and a half in any case. What the row supports is narrower and is all it ever
  supported — the reference implementation runs through this harness and posts the best score in the
  table. Whether the harness *matches Ab3P's own published evaluation* is **unestablished and is
  named in the standing unknowns**, because closing it needs the paper's numbers read from the paper
  and cited, which is one afternoon nobody has spent.
- We beat the other pure-Python Schwartz & Hearst implementation (84.21<!--claim:extraction.med1250.acronymkit.exact_f1:.2f--> against 82.48),
  on higher recall (77.31<!--claim:extraction.med1250.acronymkit.exact_recall:.2f--> against 73.46).
- We lose narrowly to the Rust implementation (84.21<!--claim:extraction.med1250.acronymkit.exact_f1:.2f--> against 84.44), and the gap is
  now 0.23 of a point rather than
  the 0.59 it was before `balanced_trim` shipped (D-032). It buys precision
  (96.42 against 92.46<!--claim:extraction.med1250.acronymkit.exact_precision:.2f-->) at the cost of recall (75.10 against 77.31<!--claim:extraction.med1250.acronymkit.exact_recall:.2f-->) — a different
  operating point, not a different league.
- **† The import column needs a caveat, and refusing it would be dishonest.** `import acronymkit`
  now costs 2.3<!--claim:micro.import.cold_import_ms--> ms because the package resolves its re-exports lazily. But
  `from acronymkit import AcronymEngine` still costs 128.1<!--claim:micro.import.cold_import_engine_ms--> ms, and import-plus-first-result is
  196.0<!--claim:micro.import.cold_first_result_ms--> ms — essentially unchanged. Lazy re-export **moves** the pydantic cost to first use; it
  does not remove it. Quoting 2.3<!--claim:micro.import.cold_import_ms--> ms against `pyab3p`'s 3.6 ms would compare their working API
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
| **`strict_initialism`** | 75.5<!--claim:generation.med1250.strict_initialism.initialism_recall_at_1:.1f--> % | 87.9<!--claim:generation.med1250.strict_initialism.initialism_recall_at_5:.1f--> % | 88.3<!--claim:generation.med1250.strict_initialism.initialism_recall_at_10:.1f--> % | 89.7<!--claim:generation.med1250.strict_initialism.initialism_recall_at_25:.1f--> % |
| `balanced_pronounceable` | 63.4<!--claim:generation.med1250.balanced_pronounceable.initialism_recall_at_1:.1f--> % | 88.1<!--claim:generation.med1250.balanced_pronounceable.initialism_recall_at_5:.1f--> % | 88.6<!--claim:generation.med1250.balanced_pronounceable.initialism_recall_at_10:.1f--> % | 89.7<!--claim:generation.med1250.balanced_pronounceable.initialism_recall_at_25:.1f--> % |
| `max_pronounceable` | 10.3<!--claim:generation.med1250.max_pronounceable.initialism_recall_at_1:.1f--> % | 38.3<!--claim:generation.med1250.max_pronounceable.initialism_recall_at_5:.1f--> % | 65.6<!--claim:generation.med1250.max_pronounceable.initialism_recall_at_10:.1f--> % | 89.2<!--claim:generation.med1250.max_pronounceable.initialism_recall_at_25:.1f--> % |
| `dictionary_backronym` | 13.0<!--claim:generation.med1250.dictionary_backronym.initialism_recall_at_1:.1f--> % | 62.8<!--claim:generation.med1250.dictionary_backronym.initialism_recall_at_5:.1f--> % | 84.2<!--claim:generation.med1250.dictionary_backronym.initialism_recall_at_10:.1f--> % | 89.2<!--claim:generation.med1250.dictionary_backronym.initialism_recall_at_25:.1f--> % |

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

Categorised over all 261<!--claim:analysis.med1250.miss_taxonomy.total_misses--> pairs missed under the relaxed convention. Regenerate with
`python bench/analyse_misses.py --save`; the counts below come from `bench/results.json`:

| Share | Count | Category |
|---:|---:|---|
| 28.7<!--claim:analysis.med1250.miss_taxonomy.pct_long_form_boundary_disagreement:.1f--> % | 75<!--claim:analysis.med1250.miss_taxonomy.n_long_form_boundary_disagreement--> | long-form boundary chosen differently from the annotator |
| 18.8<!--claim:analysis.med1250.miss_taxonomy.pct_digits_in_short_form:.1f--> % | 49<!--claim:analysis.med1250.miss_taxonomy.n_digits_in_short_form--> | digits in the short form (`2D`, `T3`, `FEV(1.0)`) |
| 14.6<!--claim:analysis.med1250.miss_taxonomy.pct_characters_not_present_in_order:.1f--> % | 38<!--claim:analysis.med1250.miss_taxonomy.n_characters_not_present_in_order--> | short-form characters not present in order in the long form |
| 11.1<!--claim:analysis.med1250.miss_taxonomy.pct_brackets_inside_short_form:.1f--> % | 29<!--claim:analysis.med1250.miss_taxonomy.n_brackets_inside_short_form--> | brackets inside the short form (`[Ca2+]i`, `k(a)`, `P(2)/P(1)`) |
| 8.8<!--claim:analysis.med1250.miss_taxonomy.pct_no_uppercase_in_short_form_config:.1f--> % | 23<!--claim:analysis.med1250.miss_taxonomy.n_no_uppercase_in_short_form_config--> | no uppercase letter in the short form (`aa`, `h2`) — **configuration** |
| 8.8<!--claim:analysis.med1250.miss_taxonomy.pct_multi_word_short_form:.1f--> % | 23<!--claim:analysis.med1250.miss_taxonomy.n_multi_word_short_form--> | multi-word short form (`MEF cells`) |
| 8.8<!--claim:analysis.med1250.miss_taxonomy.pct_short_form_2_chars_config:.1f--> % | 23<!--claim:analysis.med1250.miss_taxonomy.n_short_form_2_chars_config--> | short form shorter than two characters (`M`, `P`, `T`) — **configuration** |
| 0.4<!--claim:analysis.med1250.miss_taxonomy.pct_long_form_exceeds_word_budget:.1f--> % | 1<!--claim:analysis.med1250.miss_taxonomy.n_long_form_exceeds_word_budget--> | long form exceeds the algorithm's word budget |

Two of these are **configuration**, not algorithm: 46<!--claim:analysis.med1250.miss_taxonomy.config_attributable--> pairs (17.6<!--claim:analysis.med1250.miss_taxonomy.config_attributable_pct:.1f--> % of misses) are rejected by
`extraction_min_short_form_length=2` and by the requirement that a short form contain an uppercase
letter. Both defaults exist to protect precision on general prose, where single lowercase letters in
brackets are almost never abbreviation definitions. Biomedical text is the case where that trade
costs the most.

The `//!ord`-style category (14.6<!--claim:analysis.med1250.miss_taxonomy.pct_characters_not_present_in_order:.1f--> %) is out of scope by construction: the algorithm requires the
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

- **51<!--claim:generation.med1250.coverage.ceiling.never_produced--> of 546<!--claim:generation.med1250.coverage.ceiling.initialism_n--> pairs (9.34<!--claim:generation.med1250.coverage.ceiling.never_produced_pct:.2f--> %) are never generated at all.** That is the ceiling.
- A further 5<!--claim:generation.med1250.coverage.ceiling.beyond_rank_25--> are generated but sit beyond rank 25 under every preset. That is ranking, not
  coverage, and is deliberately excluded from the ceiling.
- **All four presets have an identical pool** (90.66<!--claim:generation.med1250.coverage.ceiling.strict_initialism_pool_recall:.2f--> % each, union 90.66<!--claim:generation.med1250.coverage.ceiling.union_pool_recall:.2f--> %). That is direct
  confirmation of the claim the presets have always made and never demonstrated: they re-rank one
  shared candidate set rather than searching differently.

### Cause taxonomy

| Share | n | Cause |
|---:|---:|---|
| 31.4<!--claim:generation.med1250.coverage.taxonomy.pct_compound_capped_by_max_letters_per_token_config:.1f--> % | 16<!--claim:generation.med1250.coverage.taxonomy.n_compound_capped_by_max_letters_per_token_config--> | compound capped by `max_letters_per_token` — `NMDA ← N-methyl-D-aspartate` |
| 25.5<!--claim:generation.med1250.coverage.taxonomy.pct_one_letter_word_dropped_by_min_word_length_config:.1f--> % | 13<!--claim:generation.med1250.coverage.taxonomy.n_one_letter_word_dropped_by_min_word_length_config--> | one-letter word dropped by `min_word_length` — `HBV ← hepatitis B virus` |
| 21.6<!--claim:generation.med1250.coverage.taxonomy.pct_word_suppressed_as_a_stop_word_config:.1f--> % | 11<!--claim:generation.med1250.coverage.taxonomy.n_word_suppressed_as_a_stop_word_config--> | word suppressed as a stop word — `QOL ← quality of life` |
| 7.8<!--claim:generation.med1250.coverage.taxonomy.pct_compound_donates_prefixes_only:.1f--> % | 4<!--claim:generation.med1250.coverage.taxonomy.n_compound_donates_prefixes_only--> | compound donates prefixes only — `ERK ← extracellular signal-related kinase` |
| 5.9<!--claim:generation.med1250.coverage.taxonomy.pct_existing_acronym_is_atomic:.1f--> % | 3<!--claim:generation.med1250.coverage.taxonomy.n_existing_acronym_is_atomic--> | existing acronym is atomic — `hTR ← human telomerase RNA` |
| 2.0<!--claim:generation.med1250.coverage.taxonomy.pct_search_budget_beam_pruning:.1f--> % | 1<!--claim:generation.med1250.coverage.taxonomy.n_search_budget_beam_pruning--> | **search budget / beam pruning** |
| 0.0<!--claim:generation.med1250.coverage.taxonomy.pct_unrepresentable_from_any_token_stream:.1f--> % | 0<!--claim:generation.med1250.coverage.taxonomy.n_unrepresentable_from_any_token_stream--> | unrepresentable from any token stream |

**82.3<!--claim:generation.med1250.coverage.taxonomy.config_attributable_pct:.1f--> % of the ceiling is configuration defaults, not the algorithm.** Beam width accounts for
exactly 1 pair, and nothing at all is genuinely unrepresentable.

### The experiment that settles it

| Arm (`strict_initialism`) | recall@25 | pool recall |
|---|---:|---:|
| control | 89.74<!--claim:generation.med1250.coverage.budget_experiment.control_strict_initialism_recall_at_25:.2f--> % | 90.66<!--claim:generation.med1250.coverage.budget_experiment.control_strict_initialism_pool_recall:.2f--> % |
| beam 100,000 / 5 M nodes / bounds 1–12 | 89.74<!--claim:generation.med1250.coverage.budget_experiment.budget_strict_initialism_recall_at_25:.2f--> % | 90.84<!--claim:generation.med1250.coverage.budget_experiment.budget_strict_initialism_pool_recall:.2f--> % |
| the same, plus relaxed tokenisation | 91.58<!--claim:generation.med1250.coverage.budget_experiment.budget_tokenisation_strict_initialism_recall_at_25:.2f--> % | **98.90<!--claim:generation.med1250.coverage.budget_experiment.budget_tokenisation_strict_initialism_pool_recall:.2f--> %** |

A search budget four orders of magnitude larger moves recall@25 by **0.00<!--claim:generation.med1250.coverage.budget_experiment.budget_recall_at_25_delta:.2f-->**. Relaxing tokenisation
moves pool recall by **8.24<!--claim:generation.med1250.coverage.budget_experiment.tokenisation_pool_recall_delta:.2f--> points**. The ceiling is tokenisation, and no amount of search
will touch it.

### The subword bucket, reported separately for the first time

Pool recall over the 398<!--claim:generation.med1250.coverage.subword.subword_n--> subword pairs is 5.78<!--claim:generation.med1250.coverage.subword.strict_initialism_pool_recall:.2f--> %. `MappingKind.CONTIGUOUS` exists to let one
token donate several characters, and on this corpus it recovers very little — worth knowing before
anyone invests further in sub-word matching for generation.

## Disambiguation: measured for the first time, and it loses to a trivial baseline

A third of this library's surface had no evidence behind it for three rounds. It does now, and the
number is bad.

SDU@AAAI-21 shared task 2, dev split: 6,189<!--claim:disambiguation.sdu21.acronymkit.instances:,.0f--> instances, 2,212<!--claim:disambiguation.sdu21.acronymkit.instances_per_second:,.0f--> instances/second.
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

**The default path is not what this table measures.** Every row above has `diction.json` supplied.
With no dictionary the engine returns no candidate at all on
97.45<!--claim:disambiguation.sdu21.diagnosis.default_path.no_candidate_pct:.2f--> % of these same
instances and has two candidates to choose between on
1<!--claim:disambiguation.sdu21.diagnosis.default_path.two_or_more_candidates:,--> of
6,189<!--claim:disambiguation.sdu21.diagnosis.default_path.instances:,--> — it is an inline-definition
lookup that performs no selection, and it is the path the README's short example takes.
`disambiguation.sdu21.diagnosis.default_path` is the run.

### Abstention: a precision instrument, and where it is worse than doing nothing

`DisambiguationResult.margin` — the score gap between the top two candidates — is reported on every
result, and `LexicalDisambiguator(config, vocab, min_margin=x)` declines to answer below a threshold
the caller names. It is **off by default**, and this is the table that says why. D-030 in
[docs/DECISIONS.md](DECISIONS.md) records what shipped and what was refused.

"Doing nothing" here means the shared task's own most-frequent-expansion baseline: ignore the context
completely and return whichever expansion was commonest in `train.json`. It is scored **on the very
same answered subset** at every gate — not on the whole split — so the last column and the one before
it answer an identical question about an identical set of instances. Publishing the curve without
that column is what makes abstention look like an improvement.

Nothing in these tables is capped by retrieval. The gold expansion is among the candidates on
6,189<!--claim:disambiguation.sdu21.ceiling.gold_in_candidates:,--> of
6,189<!--claim:disambiguation.sdu21.ceiling.instances:,--> instances, a ceiling of
100.00<!--claim:disambiguation.sdu21.ceiling.ceiling_accuracy:.2f--> %, so every miss below is a
selection error and not a missing candidate.

| margin gate | coverage % | accuracy when answered % | recall % | F1 % | `most_frequent`, same answered subset % |
|---|---:|---:|---:|---:|---:|
| **0.00** — shipped default, gate off | 100.00<!--claim:disambiguation.sdu21.abstention_curve.gate_0.00_coverage_pct:.2f--> | 41.65<!--claim:disambiguation.sdu21.abstention_curve.gate_0.00_accuracy_when_answered:.2f--> | 41.65<!--claim:disambiguation.sdu21.abstention_curve.gate_0.00_recall:.2f--> | **41.65<!--claim:disambiguation.sdu21.abstention_curve.gate_0.00_f1:.2f-->** | **72.84<!--claim:disambiguation.sdu21.abstention_curve.gate_0.00_most_frequent_accuracy_same_subset:.2f-->** |
| 0.01 | 70.53<!--claim:disambiguation.sdu21.abstention_curve.gate_0.01_coverage_pct:.2f--> | 46.32<!--claim:disambiguation.sdu21.abstention_curve.gate_0.01_accuracy_when_answered:.2f--> | 32.67<!--claim:disambiguation.sdu21.abstention_curve.gate_0.01_recall:.2f--> | 38.32<!--claim:disambiguation.sdu21.abstention_curve.gate_0.01_f1:.2f--> | **72.78<!--claim:disambiguation.sdu21.abstention_curve.gate_0.01_most_frequent_accuracy_same_subset:.2f-->** |
| 0.02 | 50.91<!--claim:disambiguation.sdu21.abstention_curve.gate_0.02_coverage_pct:.2f--> | 52.27<!--claim:disambiguation.sdu21.abstention_curve.gate_0.02_accuracy_when_answered:.2f--> | 26.61<!--claim:disambiguation.sdu21.abstention_curve.gate_0.02_recall:.2f--> | 35.27<!--claim:disambiguation.sdu21.abstention_curve.gate_0.02_f1:.2f--> | **72.14<!--claim:disambiguation.sdu21.abstention_curve.gate_0.02_most_frequent_accuracy_same_subset:.2f-->** |
| 0.05 | 29.52<!--claim:disambiguation.sdu21.abstention_curve.gate_0.05_coverage_pct:.2f--> | 64.81<!--claim:disambiguation.sdu21.abstention_curve.gate_0.05_accuracy_when_answered:.2f--> | 19.13<!--claim:disambiguation.sdu21.abstention_curve.gate_0.05_recall:.2f--> | 29.54<!--claim:disambiguation.sdu21.abstention_curve.gate_0.05_f1:.2f--> | **69.40<!--claim:disambiguation.sdu21.abstention_curve.gate_0.05_most_frequent_accuracy_same_subset:.2f-->** |
| 0.10 — the run's reference gate | 22.78<!--claim:disambiguation.sdu21.abstention_curve.gate_0.10_coverage_pct:.2f--> | **70.00<!--claim:disambiguation.sdu21.abstention_curve.gate_0.10_accuracy_when_answered:.2f-->** | 15.95<!--claim:disambiguation.sdu21.abstention_curve.gate_0.10_recall:.2f--> | 25.98<!--claim:disambiguation.sdu21.abstention_curve.gate_0.10_f1:.2f--> | 68.30<!--claim:disambiguation.sdu21.abstention_curve.gate_0.10_most_frequent_accuracy_same_subset:.2f--> |
| 0.15 | 16.77<!--claim:disambiguation.sdu21.abstention_curve.gate_0.15_coverage_pct:.2f--> | 72.93<!--claim:disambiguation.sdu21.abstention_curve.gate_0.15_accuracy_when_answered:.2f--> | 12.23<!--claim:disambiguation.sdu21.abstention_curve.gate_0.15_recall:.2f--> | 20.95<!--claim:disambiguation.sdu21.abstention_curve.gate_0.15_f1:.2f--> | 66.09<!--claim:disambiguation.sdu21.abstention_curve.gate_0.15_most_frequent_accuracy_same_subset:.2f--> |
| 0.20 | 11.33<!--claim:disambiguation.sdu21.abstention_curve.gate_0.20_coverage_pct:.2f--> | 74.04<!--claim:disambiguation.sdu21.abstention_curve.gate_0.20_accuracy_when_answered:.2f--> | 8.39<!--claim:disambiguation.sdu21.abstention_curve.gate_0.20_recall:.2f--> | **15.07<!--claim:disambiguation.sdu21.abstention_curve.gate_0.20_f1:.2f-->** | 64.05<!--claim:disambiguation.sdu21.abstention_curve.gate_0.20_most_frequent_accuracy_same_subset:.2f--> |

Bold marks the two ends of the F1 column, the one accuracy figure the reference gate buys, and every
row where ignoring the context outscores the gated system on the gated system's own answered
subset.

**F1 falls at every step.** From 41.65<!--claim:disambiguation.sdu21.abstention_curve.gate_0.00_f1:.2f--> %
ungated to 15.07<!--claim:disambiguation.sdu21.abstention_curve.gate_0.20_f1:.2f--> % at the tightest
gate measured, monotonically, with no turning point anywhere on the curve. Gating never produces more
right answers. It produces fewer answers, a larger share of which are right. Accuracy-when-answered
and F1 are different quantities and only one of them is an improvement, which is why both are
printed.

**Below the reference gate, ignoring the context wins outright.** At every threshold under 0.10 —
including the shipped default of 0.00, where the gate does nothing at all — the most-frequent
baseline is more accurate on the identical answered subset. The gate is not producing better answers
there; it is selecting easier questions. A caller who can count expansion frequencies is better off
counting them. That is the losing comparison, and it belongs in this table rather than in a paragraph
somewhere below it.

#### The crossover at 0.10 is real, and it is not uniform

At the reference gate the pooled numbers finally favour the gate. Decomposed by candidate-set size
they do not, in two of six buckets:

| candidates | instances | coverage % | accuracy when answered % | `most_frequent`, same subset % | more accurate here |
|---|---:|---:|---:|---:|---|
| 2 | 2,178<!--claim:disambiguation.sdu21.abstention_curve.by_arity.2.instances:,--> | 23.74<!--claim:disambiguation.sdu21.abstention_curve.by_arity.2.gate_0.10_coverage_pct:.2f--> | 76.98<!--claim:disambiguation.sdu21.abstention_curve.by_arity.2.gate_0.10_accuracy_when_answered:.2f--> | 75.63<!--claim:disambiguation.sdu21.abstention_curve.by_arity.2.gate_0.10_most_frequent_accuracy_same_subset:.2f--> | the gate |
| **3** | 1,150<!--claim:disambiguation.sdu21.abstention_curve.by_arity.3.instances:,--> | 21.57<!--claim:disambiguation.sdu21.abstention_curve.by_arity.3.gate_0.10_coverage_pct:.2f--> | 79.44<!--claim:disambiguation.sdu21.abstention_curve.by_arity.3.gate_0.10_accuracy_when_answered:.2f--> | **82.26<!--claim:disambiguation.sdu21.abstention_curve.by_arity.3.gate_0.10_most_frequent_accuracy_same_subset:.2f-->** | **the baseline** |
| **4** | 854<!--claim:disambiguation.sdu21.abstention_curve.by_arity.4.instances:,--> | 14.87<!--claim:disambiguation.sdu21.abstention_curve.by_arity.4.gate_0.10_coverage_pct:.2f--> | 70.08<!--claim:disambiguation.sdu21.abstention_curve.by_arity.4.gate_0.10_accuracy_when_answered:.2f--> | **70.87<!--claim:disambiguation.sdu21.abstention_curve.by_arity.4.gate_0.10_most_frequent_accuracy_same_subset:.2f-->** | **the baseline** |
| 5 | 424<!--claim:disambiguation.sdu21.abstention_curve.by_arity.5.instances:,--> | 26.18<!--claim:disambiguation.sdu21.abstention_curve.by_arity.5.gate_0.10_coverage_pct:.2f--> | 66.67<!--claim:disambiguation.sdu21.abstention_curve.by_arity.5.gate_0.10_accuracy_when_answered:.2f--> | 63.06<!--claim:disambiguation.sdu21.abstention_curve.by_arity.5.gate_0.10_most_frequent_accuracy_same_subset:.2f--> | the gate |
| 6–9 | 1,026<!--claim:disambiguation.sdu21.abstention_curve.by_arity.6-9.instances:,--> | 23.39<!--claim:disambiguation.sdu21.abstention_curve.by_arity.6-9.gate_0.10_coverage_pct:.2f--> | 57.92<!--claim:disambiguation.sdu21.abstention_curve.by_arity.6-9.gate_0.10_accuracy_when_answered:.2f--> | 57.50<!--claim:disambiguation.sdu21.abstention_curve.by_arity.6-9.gate_0.10_most_frequent_accuracy_same_subset:.2f--> | the gate, barely |
| **10+** — worst row | 557<!--claim:disambiguation.sdu21.abstention_curve.by_arity.10+.instances:,--> | 29.98<!--claim:disambiguation.sdu21.abstention_curve.by_arity.10+.gate_0.10_coverage_pct:.2f--> | **53.89<!--claim:disambiguation.sdu21.abstention_curve.by_arity.10+.gate_0.10_accuracy_when_answered:.2f-->** | 41.92<!--claim:disambiguation.sdu21.abstention_curve.by_arity.10+.gate_0.10_most_frequent_accuracy_same_subset:.2f--> | the gate |

The three- and four-candidate buckets are
2,004<!--claim:disambiguation.sdu21.abstention_curve.instances_in_those_arities:,--> instances,
32.38<!--claim:disambiguation.sdu21.abstention_curve.instances_in_those_arities_pct:.2f--> % of the
split. A caller whose acronyms live there gains nothing the pooled row appears to promise. The worst
answered-accuracy row is the ten-or-more bucket at
53.89<!--claim:disambiguation.sdu21.abstention_curve.worst_arity_accuracy_at_reference_gate:.2f--> %,
printed here rather than left to be derived.

The obvious repair — one threshold per bucket — was measured and refused. The premise that a margin
shrinks as the candidate set grows is false of this scorer, and six in-sample parameters bought
0.59<!--claim:disambiguation.sdu21.abstention_curve.per_arity_gain_over_global_gate:.2f--> of a point
against a four-point spread between two halves of the same split. D-030 has the working; that is
experiment eight, and it is spent.

#### What the gate is actually detecting

Verbatim evidence. The share of answered instances whose gold expansion has a word in the sentence
rises from a base rate of
18.15<!--claim:disambiguation.sdu21.abstention_curve.gold_word_in_sentence_base_rate_pct:.2f--> % to
64.82<!--claim:disambiguation.sdu21.abstention_curve.gate_0.10_share_of_answered_that_is_gold_verbatim_pct:.2f--> %
at the reference gate and
89.44<!--claim:disambiguation.sdu21.abstention_curve.gate_0.20_share_of_answered_that_is_gold_verbatim_pct:.2f--> %
at 0.20. Split the corpus on that property and the gate's value splits with it:

| subset | instances | gate | coverage % | accuracy when answered % | `most_frequent`, same subset % |
|---|---:|---|---:|---:|---:|
| gold words in the sentence | 1,123<!--claim:disambiguation.sdu21.abstention_curve.by_gold_evidence.gold_word_in_sentence.instances:,--> | 0.00 | 100.00<!--claim:disambiguation.sdu21.abstention_curve.by_gold_evidence.gold_word_in_sentence.gate_0.00_coverage_pct:.2f--> | 81.48<!--claim:disambiguation.sdu21.abstention_curve.by_gold_evidence.gold_word_in_sentence.gate_0.00_accuracy_when_answered:.2f--> | 66.16<!--claim:disambiguation.sdu21.abstention_curve.by_gold_evidence.gold_word_in_sentence.gate_0.00_most_frequent_accuracy_same_subset:.2f--> |
| | | 0.10 | 81.39<!--claim:disambiguation.sdu21.abstention_curve.by_gold_evidence.gold_word_in_sentence.gate_0.10_coverage_pct:.2f--> | 85.78<!--claim:disambiguation.sdu21.abstention_curve.by_gold_evidence.gold_word_in_sentence.gate_0.10_accuracy_when_answered:.2f--> | 66.85<!--claim:disambiguation.sdu21.abstention_curve.by_gold_evidence.gold_word_in_sentence.gate_0.10_most_frequent_accuracy_same_subset:.2f--> |
| **gold absent from the sentence** | 5,066<!--claim:disambiguation.sdu21.abstention_curve.by_gold_evidence.gold_absent_from_sentence.instances:,--> | 0.00 | 100.00<!--claim:disambiguation.sdu21.abstention_curve.by_gold_evidence.gold_absent_from_sentence.gate_0.00_coverage_pct:.2f--> | 32.83<!--claim:disambiguation.sdu21.abstention_curve.by_gold_evidence.gold_absent_from_sentence.gate_0.00_accuracy_when_answered:.2f--> | **74.32<!--claim:disambiguation.sdu21.abstention_curve.by_gold_evidence.gold_absent_from_sentence.gate_0.00_most_frequent_accuracy_same_subset:.2f-->** |
| | | 0.10 | **9.79<!--claim:disambiguation.sdu21.abstention_curve.by_gold_evidence.gold_absent_from_sentence.gate_0.10_coverage_pct:.2f-->** | 40.93<!--claim:disambiguation.sdu21.abstention_curve.by_gold_evidence.gold_absent_from_sentence.gate_0.10_accuracy_when_answered:.2f--> | **70.97<!--claim:disambiguation.sdu21.abstention_curve.by_gold_evidence.gold_absent_from_sentence.gate_0.10_most_frequent_accuracy_same_subset:.2f-->** |

Four fifths of this split is text where the expansion's words are not in the sentence, and there the
baseline is thirty to forty points ahead **both before and after gating**. Coverage in that subset does
not degrade under the gate, it collapses. So the practical statement for a caller is: on prose that
defines or echoes its abbreviations, the gate raises answered accuracy above the frequency baseline
and keeps most of its coverage; on prose that does not, it refuses nearly everything and is still
worse than counting.

**One more thing that is only true pooled.** "Answers get better as the gate rises" is a statement
about the pooled column. Inside the four-candidate bucket answered accuracy turns down between gate
`0.15` and gate `0.20`, and inside the gold-absent subset it peaks at gate `0.05` and falls away. A
caller reading a single pooled curve would see neither.

#### What this is measured on

Every figure above is `disambiguation.sdu21.abstention_curve` in
[bench/results.json](../bench/results.json), on the **dictionary path** — `diction.json` supplied, so
there are competing candidates to have a margin between. The engine's no-dictionary default path is a
different measurement, in the section above: on that path a margin is defined on
1<!--claim:disambiguation.sdu21.abstention_curve.default_path_margin_defined:,--> of
6,189<!--claim:disambiguation.sdu21.abstention_curve.default_path_instances:,--> instances, so none of
this reaches a caller who does not pass a dictionary.

The sweep reproduces the *shipped* gate, exemptions included (`harness_reproduces_shipped_gate`),
which is why its rows differ slightly from the August 2026 audit's earlier
`disambiguation.sdu21.diagnosis.abstention`. **Cite this run id, not that one.**

**SDU@AAAI-21 AD dev is a tuning split, and `bench/splits.toml` declares it contaminated.** Its
per-candidate-count breakdown has been read, an ablation and a ceiling study have been run against it,
and the reference gate is read off the very split it is scored on. Nothing here is evidence of
generalisation, and no threshold on this curve is a default this library adopts. The only
corroboration offered is a split-half check at the reference gate:
72.16<!--claim:disambiguation.sdu21.abstention_curve.split_half_a_gate_0.10_accuracy_when_answered:.2f--> %
against
67.85<!--claim:disambiguation.sdu21.abstention_curve.split_half_b_gate_0.10_accuracy_when_answered:.2f--> %
answered accuracy — a four-point spread from resampling one frozen shuffle, which is the scale at
which any cut-point here should be trusted. `test.json` is fetchable from the same pin and is
deliberately unspent.

The dataset is CC BY-NC-SA 4.0, read from the shared task's own README at the URL and date pinned in
[`bench/splits.toml`](../bench/splits.toml); MIT covers only its scorer and baseline. The
`most_frequent` control is derived from `train.json` as a measurement instrument, and is never
shipped, vendored or committed.

## PLOD: a second corpus, and a premise of mine that was wrong

PLOD was added to close the domain-generalisation gap. **It does not, because PLOD is not
non-biomedical.** It is PLOS journal text dominated by the life sciences — SDS-PAGE, shRNA,
eicosapentaenoic acid. It is a different corpus, genre, annotation provenance and task, and that is
worth having, but it is not a different domain. Every place this project called it a
"non-biomedical counterweight" — including `bench/splits.toml` — was wrong and has been corrected.
**The domain-generalisation gap remains open.**

Evaluated on PLOD's *own* task. It labels short-form and long-form spans without pairing them, and a
gold standard we partly invented cannot adjudicate our own system, so no pairing was derived. Two
independent span-detection scores instead, in token space, PLOD-CW test split. **The fourth column is
the same short-form score restricted to the gold spans a definition extractor can stand in front of
at all**, and it is in this table rather than in a section underneath it because the third column is
not a like-for-like comparison and has been quoted as one:

| System | SF exact P / R / F1 | SF exact F1, definitional gold | LF exact P / R / F1 | LF overlap F1 |
|---|---|---:|---|---:|
| `allcaps` | 60.13 / 69.26 / **64.37** | 72.36<!--claim:shortform_contest.plod.test.allcaps.definitional.exact_f1:.2f--> | — | — |
| **`acronymkit HIGH_PRECISION`** | 97.06 / 36.67 / **53.23** | **87.22<!--claim:shortform_contest.plod.test.acronymkit.high_precision.definitional.exact_f1:.2f-->** | 88.24 / 59.21<!--claim:spans.plod.test.tight.acronymkit.high_precision.long_form.exact_recall:.2f--> / 70.87<!--claim:spans.plod.test.tight.acronymkit.high_precision.long_form.exact_f1:.2f--> | 75.59<!--claim:spans.plod.test.tight.acronymkit.high_precision.long_form.overlap_f1:.2f--> |
| `acronymkit BIOMEDICAL` | 93.52 / 37.41 / **53.44** | 86.70<!--claim:shortform_contest.plod.test.acronymkit.biomedical.definitional.exact_f1:.2f--> | 83.33<!--claim:spans.plod.test.tight.acronymkit.biomedical.long_form.exact_precision:.2f--> / 59.21<!--claim:spans.plod.test.tight.acronymkit.biomedical.long_form.exact_recall:.2f--> / 69.23<!--claim:spans.plod.test.tight.acronymkit.biomedical.long_form.exact_f1:.2f--> | 73.85<!--claim:spans.plod.test.tight.acronymkit.biomedical.long_form.overlap_f1:.2f--> |
| `pyab3p` | 95.15 / 36.30 / **52.55** | not run | 85.44 / 57.89 / 69.02 | 74.51 |
| `abbreviation_extractor` | 94.68 / 32.96 / **48.90** | not run | 87.23 / 53.95 / 66.67 | 70.73 |
| `abbreviations` | 95.65 / 32.59 / **48.62** | not run | 90.22 / 54.61 / 68.03 | 70.49 |
| `scispacy` | 95.65 / 32.59 / **48.62** | not run | 84.78 / 51.32 / 63.93 | 69.67 |

*`not run` is a firing count of zero, not a dash.* The four external baselines need an interpreter
older than this project's — `docs/EVALUATION.md`'s own reproduce block says so — and the
decomposition executed against them **zero times**. Nothing here says how they behave in that
column, and a reader who assumes they behave like our rows is assuming, not reading.

**A one-line all-caps rule beats every definition extractor on short forms**, 64.37 against our
53.23. On PLOD's task a capitalisation heuristic is simply a better answer, and the reason is
structural: PLOD annotates every *mention* of an abbreviation while a Schwartz & Hearst extractor
returns every *definition*. Only 37.78 % of gold short-form spans are reachable by any
definition-based method at all. That is the same lesson as the disambiguation result — measure
against the stupid baseline first, because sometimes it wins. **And then decompose the comparison,
because sometimes it wins for a reason that is not about either system.** The next section does
that, and the order flips.

### The one-line rule's win is the annotation convention, and restricted to comparable gold it reverses

**The raw comparison is real, it is in the record, and it is not like-for-like.** Pooled over every
PLOD split, `allcaps` scores
68.62<!--claim:spans.plod.all.tight.allcaps.short_form.exact_f1:.2f--> short-form exact F1 against
52.56<!--claim:spans.plod.all.tight.acronymkit.high_precision.native.short_form.exact_f1:.2f--> for
`HIGH_PRECISION` — a sixteen-point deficit, on the only held-out corpus that can see this label. Both
figures are right. What they measure is the **sum of two different disabilities**, because the two
systems are handicapped on disjoint parts of the same gold:

* `extract()` emits a `(short, long)` **pair**, and D-041 closed the class of change that would let it
  do otherwise: `long_form=None` is a `ValidationError`, and any filter keyed on the long form
  deletes the short form standing beside it. So **this library cannot say "that is an abbreviation
  and I do not know what it stands for"**, and every gold occurrence standing in no definitional
  arrangement is a false negative no setting of any knob can convert.
* `predict_all_caps` admits a single token of length 2+ equal to its own uppercase, and nothing else.
  Every gold short form outside that shape is a false negative *it* can never convert.

`bench/run_shortform_contest.py` scores both systems inside four regions — the 2×2 of those two
factors — filtering **gold and predictions by the same predicate**, so precision inside a region is
a real precision and not a recall-only rescoring. Pooled corpus, tight join, native spans:

| Gold short-form spans kept | spans | `acronymkit HIGH_PRECISION` P / R / F1 | `allcaps` P / R / F1 |
|---|---:|---|---|
| all — every annotated occurrence | 2,869<!--claim:shortform_contest.plod.all.regions.all.gold_spans:,--> | 93.66<!--claim:shortform_contest.plod.all.acronymkit.high_precision.native.all.exact_precision:.2f--> / 36.53<!--claim:shortform_contest.plod.all.acronymkit.high_precision.native.all.exact_recall:.2f--> / **52.56<!--claim:shortform_contest.plod.all.acronymkit.high_precision.native.all.exact_f1:.2f-->** | 64.45<!--claim:shortform_contest.plod.all.allcaps.all.exact_precision:.2f--> / 73.37<!--claim:shortform_contest.plod.all.allcaps.all.exact_recall:.2f--> / **68.62<!--claim:shortform_contest.plod.all.allcaps.all.exact_f1:.2f-->** |
| all-caps token only — the baseline's own rule | 2,105<!--claim:shortform_contest.plod.all.regions.caps.gold_spans:,--> | 95.64<!--claim:shortform_contest.plod.all.acronymkit.high_precision.native.caps.exact_precision:.2f--> / 38.57<!--claim:shortform_contest.plod.all.acronymkit.high_precision.native.caps.exact_recall:.2f--> / **54.98<!--claim:shortform_contest.plod.all.acronymkit.high_precision.native.caps.exact_f1:.2f-->** | 64.45<!--claim:shortform_contest.plod.all.allcaps.caps.exact_precision:.2f--> / 100.00<!--claim:shortform_contest.plod.all.allcaps.caps.exact_recall:.2f--> / **78.38<!--claim:shortform_contest.plod.all.allcaps.caps.exact_f1:.2f-->** |
| bracket-adjacent only — definitional gold | 1,323<!--claim:shortform_contest.plod.all.regions.definitional.gold_spans:,--> | 93.72<!--claim:shortform_contest.plod.all.acronymkit.high_precision.native.definitional.exact_precision:.2f--> / 78.99<!--claim:shortform_contest.plod.all.acronymkit.high_precision.native.definitional.exact_recall:.2f--> / **85.73<!--claim:shortform_contest.plod.all.acronymkit.high_precision.native.definitional.exact_f1:.2f-->** | 76.31<!--claim:shortform_contest.plod.all.allcaps.definitional.exact_precision:.2f--> / 74.00<!--claim:shortform_contest.plod.all.allcaps.definitional.exact_recall:.2f--> / **75.13<!--claim:shortform_contest.plod.all.allcaps.definitional.exact_f1:.2f-->** |
| both conditions | 979<!--claim:shortform_contest.plod.all.regions.definitional_caps.gold_spans:,--> | 95.63<!--claim:shortform_contest.plod.all.acronymkit.high_precision.native.definitional_caps.exact_precision:.2f--> / 82.64<!--claim:shortform_contest.plod.all.acronymkit.high_precision.native.definitional_caps.exact_recall:.2f--> / **88.66<!--claim:shortform_contest.plod.all.acronymkit.high_precision.native.definitional_caps.exact_f1:.2f-->** | 76.31<!--claim:shortform_contest.plod.all.allcaps.definitional_caps.exact_precision:.2f--> / 100.00<!--claim:shortform_contest.plod.all.allcaps.definitional_caps.exact_recall:.2f--> / **86.56<!--claim:shortform_contest.plod.all.allcaps.definitional_caps.exact_f1:.2f-->** |

**The `HIGH_PRECISION` row above is the native-offset row, which is not this harness's headline
path.** `bench/run_spans.py` puts every system's spans through one string localiser on purpose, so
that ours is not scored through a privileged one, and it records the native row beside it as the
localiser's price. D-049 quoted the native row, and this table matches that quote so the two can be
laid against each other. Through the localiser the same configuration scores
52.31<!--claim:shortform_contest.plod.all.acronymkit.high_precision.all.exact_f1:.2f--> on the whole gold and
85.32<!--claim:shortform_contest.plod.all.acronymkit.high_precision.definitional.exact_f1:.2f--> on
definitional gold. The privileged path is worth about a quarter of a point, it moves in our favour,
and it changes nothing about the direction of anything below. Both rows are recorded under their own
run ids.

**The two factors do not split the gap between them; one of them is the whole gap.** Removing the
baseline's handicap alone — scoring only gold the all-caps rule could ever admit — makes our deficit
*larger*, not smaller. Removing this library's handicap alone reverses the result. Read down the two
F1 columns rather than across, because the row that flips is the one that names the cause:

```
python bench/run_shortform_contest.py --split all   -- command output, abridged, not a measurement
  region               acronymkit   allcaps   lead
  all                       52.56     68.62   allcaps    +16.06
  caps                      54.98     78.38   allcaps    +23.40
  definitional              85.73     75.13   acronymkit +10.60
  definitional_caps         88.66     86.56   acronymkit  +2.10
```

`allcaps` scores exactly 100.00<!--claim:shortform_contest.plod.all.allcaps.caps.exact_recall:.2f--> recall in both caps regions **by construction** — those regions are
defined by its own admission rule, so it cannot have a false negative inside them and only its
precision column carries information there. That is stated rather than quietly enjoyed, and it is
why the `definitional` row rather than the `definitional_caps` row is the honest headline.

**What the definitional region is, and what it is not.** It is
`bench.run_spans.corpus_statistics`'s `short_form_spans_bracket_adjacent` predicate, unchanged: a
bracket immediately before the span, or either kind of bracket immediately after it. That function's
docstring already called the count "a hard ceiling on its recall here, imposed by the corpus's
annotation convention rather than by the algorithm", and it deliberately takes the **generous**
reading — both parenthetical arrangements — which keeps
46.11<!--claim:shortform_contest.plod.all.regions.definitional.gold_share_pct:.2f--> % of the gold in the
denominator against the
37.50<!--claim:spans.plod.all.tight.oracle_definitional.short_form.exact_recall:.2f--> % that the
pooled definition extractors actually reach. The larger region is the one that costs this library recall,
so the choice is not self-serving. It is corpus-side rather than system-side, it was fixed before any
of these numbers were seen, and no individual miss was read: D-049 permits PLOD to be *scored* and
forbids it being *diagnosed*, because reading a miss taxonomy is precisely what turned MED1250 and
both SDU-22 dev splits into tuning sets. The runner therefore ships no error-listing mode.

That pool is also not a set of independent opinions. It unions seven rows, and three of the seven are
configurations of this library. Of the
1,076<!--claim:spans.plod.all.tight.oracle_definitional.short_form.exact_true_positives:,--> gold
short forms the whole pool finds between them, the single shipped default row finds
1,043<!--claim:spans.plod.all.tight.acronymkit.high_precision.short_form.exact_true_positives:,--> on
its own — same corpus, same convention, same localiser as every other member. Every member is a
Schwartz & Hearst descendant, so "reachable by any definition-based method" is a statement about one
algorithm with several spellings, and the pooled ceiling is very nearly one system's ceiling.

### The scoring type is the conclusion, not a caveat

**This whole comparison is conducted under a metric that is native to neither system, and that fact
outranks the direction of the result.**

`bench.run_spans.SpanPrediction` has a field for short-form spans and a field for long-form spans and
**no slot for the edge between them**. Replaying PLOD's own gold as a prediction, and then rotating
each document's long forms against its short forms before coarsening, produces byte-identical
scores — `100.00` on all four span metrics either way. The rotation is not a no-op: it fired on
342<!--claim:shortform_contest.plod.all.pairing_blind.documents_rotated:,--> of
1,351<!--claim:shortform_contest.plod.all.pairing_blind.documents:,--> documents and made
1,054<!--claim:shortform_contest.plod.all.pairing_blind.pairs_mispaired:,--> pairs wrong. D-048 found this by
permuting most of PLOD's long forms; it is re-derived inside the runner that publishes the contested
figures so that the null arrives with its firing count attached.

Two consequences, and neither is small:

* **The winning column is short-form detection, not extraction.** It says this library puts
  abbreviation spans in the right places on definitional gold. It says nothing whatever about
  whether the expansions it pairs them with are right, because the scorer cannot see a pairing at
  all. The claim the README leads with is an *edge* claim, and no corpus in `bench/splits.toml`
  contains edges — that is the ninth criterion in
  [docs/DEFINITION-OF-DONE.md](DEFINITION-OF-DONE.md), and it stays open.
* **`allcaps` can be scored here only because the metric admits an unpaired short form.** Our
  extractor cannot emit one. So the trivial baseline is being scored on an output shape this library
  is forbidden to produce, which is the reverse asymmetry and the one that makes the raw row
  misleading in the first place. Whether to lift that restriction is
  [the W11 question](notes/w11-emission-model.md); it is a design change, this section is a
  measurement, and the measurement does not decide it.

**What this does not do.** It does not close the domain gap, it does not turn PLOD into an extraction
corpus, and it does not retire the raw row above — that row is what PLOD's own task rewards and it is
kept in the table for exactly that reason. The `overlap` convention is recorded for every region and
is deliberately not the headline: under `exact` a prediction equal to an in-region gold span is
in-region by construction, whereas under `overlap` a prediction touching one can itself fail the
predicate, so the overlap columns of a restricted region are not a clean restriction.

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

## The extraction monoculture, and what it does to the corpora

Every abbreviation extractor in this project's tables descends from Schwartz & Hearst. So does
every one it is compared against. D-056 found that pooling four of them over Federal Register
rules produced a union that was almost entirely one system's, and gave the reason: it is one
algorithm with four implementations. That is a claim about the *field's* instruments, not about
this library, and it is worth more than any of the accuracy numbers above if it holds.

**This section is the argument [docs/POSITIONING.md](POSITIONING.md) rests on**, which is why the
genre confound under *What this does not establish* is part of the finding rather than a caveat
appended to it. Anything quoted out of here into a positioning claim has to carry both halves.

`bench/run_monoculture.py` measures it. Two commitments define the algorithm and both are
executable here: candidates are generated only from a **bracketed window**, and a candidate is
accepted only if the short form is a **character subsequence of the long form under a word-initial
anchor** — the right-to-left greedy walk transcribed as `sh_alignable`. Nine proposers run over
five corpora: `acronymkit` at three operating points, `abbreviations`, `abbreviation_extractor`,
`pyab3p` and `scispacy` (all seven make both commitments), plus two that make neither — the
all-caps rule and `shapecue`, described below.

### Adding another implementation of the same algorithm buys almost nothing

Proposals are counted as distinct `(passage, short form, long form)` edges, the same unit D-056
used. **Union gain** is what the union loses if that proposer is removed.

| Corpus | Edges in union | `acronymkit BIOMEDICAL` share % | Largest union gain by any single S&H row % | Union gain from the two independent proposers % |
|---|---:|---:|---:|---:|
| MED1250 | 1,304<!--claim:monoculture.med1250.proposals.edges.union_total:,--> | 87.04<!--claim:monoculture.med1250.proposals.edges.share_pct_acronymkit/biomedical:.2f--> | 5.83<!--claim:monoculture.med1250.proposals.edges.union_gain_pct_acronymkit/biomedical:.2f--> | **0.23<!--claim:monoculture.med1250.proposals.edges.independent_gain_pct:.2f-->** |
| PLOD-CW, all | 1,826<!--claim:monoculture.plod_all.proposals.edges.union_total:,--> | 63.58<!--claim:monoculture.plod_all.proposals.edges.share_pct_acronymkit/biomedical:.2f--> | 1.15<!--claim:monoculture.plod_all.proposals.edges.union_gain_pct_pyab3p:.2f--> | **32.04<!--claim:monoculture.plod_all.proposals.edges.independent_gain_pct:.2f-->** |
| PLOD-CW, test | 144<!--claim:monoculture.plod_test.proposals.edges.union_total:,--> | 75.00<!--claim:monoculture.plod_test.proposals.edges.share_pct_acronymkit/biomedical:.2f--> | 2.08<!--claim:monoculture.plod_test.proposals.edges.union_gain_pct_acronymkit/biomedical:.2f--> | **18.75<!--claim:monoculture.plod_test.proposals.edges.independent_gain_pct:.2f-->** |
| SDU@AAAI-22 AE legal, dev | 687<!--claim:monoculture.sdu22_legal_dev.proposals.edges.union_total:,--> | 72.05<!--claim:monoculture.sdu22_legal_dev.proposals.edges.share_pct_acronymkit/biomedical:.2f--> | 9.90<!--claim:monoculture.sdu22_legal_dev.proposals.edges.union_gain_pct_pyab3p:.2f--> | **9.17<!--claim:monoculture.sdu22_legal_dev.proposals.edges.independent_gain_pct:.2f-->** |
| SDU@AAAI-22 AE scientific, dev | 665<!--claim:monoculture.sdu22_scientific_dev.proposals.edges.union_total:,--> | 89.32<!--claim:monoculture.sdu22_scientific_dev.proposals.edges.share_pct_acronymkit/biomedical:.2f--> | 1.95<!--claim:monoculture.sdu22_scientific_dev.proposals.edges.union_gain_pct_scispacy:.2f--> | **4.96<!--claim:monoculture.sdu22_scientific_dev.proposals.edges.independent_gain_pct:.2f-->** |

The fourth column is the one to read: it is the most any *one* of the seven descendants adds to
what the other six already propose. On three of the five corpora that best case is about two points
or less. Two are not, and both are worth recording, because a blanket "they are all the same" is the
over-statement this table exists to avoid: `pyab3p` adds
9.90<!--claim:monoculture.sdu22_legal_dev.proposals.edges.union_gain_pct_pyab3p:.2f--> on the SDU
legal split, and `acronymkit BIOMEDICAL` adds
5.83<!--claim:monoculture.med1250.proposals.edges.union_gain_pct_acronymkit/biomedical:.2f--> on
MED1250 — the latter being the loosest operating point in the table, so most of that gain is
precision it has already spent elsewhere. What does not vary is the conclusion D-056 drew, and the
cleanest form of it is the same matrix computed over the **seven descendants alone** — the
arrangement D-056 measured, whose Federal Register answer was `93.74 %`:

| Corpus | S&H-only edge union | `acronymkit BIOMEDICAL` share of it % |
|---|---:|---:|
| PLOD-CW, all | 1,241<!--claim:monoculture.plod_all.proposals.edges_sh_only.union_total:,--> | **93.55<!--claim:monoculture.plod_all.proposals.edges_sh_only.share_pct_acronymkit/biomedical:.2f-->** |
| SDU@AAAI-22 AE scientific, dev | 632<!--claim:monoculture.sdu22_scientific_dev.proposals.edges_sh_only.union_total:,--> | **93.99<!--claim:monoculture.sdu22_scientific_dev.proposals.edges_sh_only.share_pct_acronymkit/biomedical:.2f-->** |
| PLOD-CW, test | 117<!--claim:monoculture.plod_test.proposals.edges_sh_only.union_total:,--> | 92.31<!--claim:monoculture.plod_test.proposals.edges_sh_only.share_pct_acronymkit/biomedical:.2f--> |
| MED1250 | 1,301<!--claim:monoculture.med1250.proposals.edges_sh_only.union_total:,--> | 87.24<!--claim:monoculture.med1250.proposals.edges_sh_only.share_pct_acronymkit/biomedical:.2f--> |
| SDU@AAAI-22 AE legal, dev | 624<!--claim:monoculture.sdu22_legal_dev.proposals.edges_sh_only.union_total:,--> | 79.33<!--claim:monoculture.sdu22_legal_dev.proposals.edges_sh_only.share_pct_acronymkit/biomedical:.2f--> |

Two of the five land within half a point of the Federal Register figure, on biomedical and mixed
scientific prose rather than on agency rulemaking, with a partly different set of pooled systems.
**`93.74 %` was a property of the pool, not of the substrate.** The spread across corpora is real —
`79.33<!--claim:monoculture.sdu22_legal_dev.proposals.edges_sh_only.share_pct_acronymkit/biomedical:.2f-->`
on the SDU legal split is the low end, and it is the same split where `pyab3p` has its one large
gain — so the honest statement is a range, not a constant.

**The matrix itself, published rather than summarised** (R13). Command output, PLOD-CW all, so it
re-derives in one line and is deliberately not quotable as a gated figure:

```
python -c "import sys,json;sys.path[:0]=['.','src'];from bench.run_monoculture import render_matrix;print(render_matrix(json.load(open('bench/results.json',encoding='utf-8'))['runs']['monoculture.plod_all.proposals.edges']))"

                            abbreviat abbreviat acronymki acronymki acronymki   allcaps    pyab3p  scispacy  shapecue
---------------------------------------------------------------------------------------------------------------------
abbreviation_extractor            993       949       971       958       958         0       945       917         0
abbreviations                     949       969       942       930       930         0       915       888         0
acronymkit/biomedical             971       942     1,161     1,122     1,119         0     1,063       973         0
acronymkit/general                958       930     1,122     1,122     1,119         0     1,044       961         0
acronymkit/high_precision         958       930     1,119     1,119     1,119         0     1,042       961         0
allcaps                             0         0         0         0         0         0         0         0         0
pyab3p                            945       915     1,063     1,044     1,042         0     1,092       939         0
scispacy                          917       888       973       961       961         0       939       998         0
shapecue                            0         0         0         0         0         0         0         0       585

proposer                            n    share%    unique     gain%
abbreviation_extractor            993     54.38         9      0.49
abbreviations                     969     53.07        18      0.99
acronymkit/biomedical           1,161     63.58        18      0.99
acronymkit/general              1,122     61.45         0      0.00
acronymkit/high_precision       1,119     61.28         0      0.00
allcaps                             0      0.00         0      0.00
pyab3p                          1,092     59.80        21      1.15
scispacy                          998     54.65        19      1.04
shapecue                          585     32.04       585     32.04
UNION                           1,826
  Schwartz & Hearst family share of union: 67.96 %   independent gain: 32.04 %
```

Two rows deserve naming. `acronymkit GENERAL` and `HIGH_PRECISION` are **entirely inside** the
others: their union gain is zero, so on this corpus they are decoration in the pool and the table
says so in a column. And the off-diagonal cells between any two descendants are close to both
diagonals — pairs of systems agree on nearly everything either of them proposes, which is what a
monoculture looks like before anyone argues about lineage.

### The corpora do not all annotate the same thing, and that is the finding

The sharper measurement needs no proposer at all. If a corpus's gold is almost entirely
parenthetical, that corpus cannot reward — or even see — a system that reads a definition written
any other way. Every corpus here annotates a long form only where a definition is present, so the
column below compares definitions with definitions.

| Corpus | Gold long forms | How the gold was built | Beside a bracket % |
|---|---:|---|---:|
| MED1250 | 1,195<!--claim:monoculture.med1250.corpus.gold_pairs_located:,--> located | Ab3P's own evaluation corpus, and `pyab3p` in the table above **is** Ab3P | **98.91<!--claim:monoculture.med1250.corpus.gold_pairs_long_form_bracket_adjacent_pct:.2f-->** |
| SDU@AAAI-22 AE scientific, dev | 720<!--claim:monoculture.sdu22_scientific_dev.corpus.gold_long_form_spans:,--> | Human annotators, agreement published | 76.11<!--claim:monoculture.sdu22_scientific_dev.corpus.gold_long_form_spans_bracket_adjacent_pct:.2f--> |
| SDU@AAAI-22 AE legal, dev | 669<!--claim:monoculture.sdu22_legal_dev.corpus.gold_long_form_spans:,--> | Human annotators, agreement published | 73.69<!--claim:monoculture.sdu22_legal_dev.corpus.gold_long_form_spans_bracket_adjacent_pct:.2f--> |
| PLOD-CW, test | 152<!--claim:monoculture.plod_test.corpus.gold_long_form_spans:,--> | Each PLOS article's own *Abbreviations* section, matched onto its body text | 67.76<!--claim:monoculture.plod_test.corpus.gold_long_form_spans_bracket_adjacent_pct:.2f--> |
| PLOD-CW, all | 1,804<!--claim:monoculture.plod_all.corpus.gold_long_form_spans:,--> | The same | **61.36<!--claim:monoculture.plod_all.corpus.gold_long_form_spans_bracket_adjacent_pct:.2f-->** |

**The corpus this field's flagship system was developed against annotates definitions that are
98.91<!--claim:monoculture.med1250.corpus.gold_pairs_long_form_bracket_adjacent_pct:.2f--> %
parenthetical. The corpus whose arbiter is the paper's own author annotates definitions that are
61.36<!--claim:monoculture.plod_all.corpus.gold_long_form_spans_bracket_adjacent_pct:.2f--> %
parenthetical.** Ordering is by provenance and it is monotone: the further the gold's authority is
from these systems, the less of it they can see.

**This is not proof, and the confound is genre, not provenance.** MED1250 is MEDLINE titles and
abstracts, which carry no figure legends and no table footnotes; PLOD is article body text, which
carries both. A corpus of abstracts would look parenthetical however its gold was built. The
ordering is consistent with the thesis and does not establish it, and separating the two would need
a corpus of article body text annotated by pooling Schwartz & Hearst systems — which nobody has
published, because nobody builds a gold standard that way on purpose.

### The class of gold that no Schwartz & Hearst descendant proposes

Union of all seven descendants, one-to-one span matching, **overlap** convention — the generous
one, so the unreached class below is a lower bound.

| Corpus | Gold long forms reached by the family % | Unreached % | Of gold: unreached yet alignable with a gold short form % | Reached once the independent proposers are added % |
|---|---:|---:|---:|---:|
| PLOD-CW, all | 57.65<!--claim:monoculture.plod_all.gold.long_form.overlap.class.sh_family_recall_pct:.2f--> | **42.35<!--claim:monoculture.plod_all.gold.long_form.overlap.class.unproposed_pct:.2f-->** | 34.98<!--claim:monoculture.plod_all.gold.long_form.overlap.class.unproposed_alignable_from_gold_short_form_pct_of_gold:.2f--> | 79.60<!--claim:monoculture.plod_all.gold.long_form.overlap.class.all_proposers_recall_pct:.2f--> |
| PLOD-CW, test | 64.47<!--claim:monoculture.plod_test.gold.long_form.overlap.class.sh_family_recall_pct:.2f--> | 35.53<!--claim:monoculture.plod_test.gold.long_form.overlap.class.unproposed_pct:.2f--> | 27.63<!--claim:monoculture.plod_test.gold.long_form.overlap.class.unproposed_alignable_from_gold_short_form_pct_of_gold:.2f--> | 77.63<!--claim:monoculture.plod_test.gold.long_form.overlap.class.all_proposers_recall_pct:.2f--> |
| SDU AE legal, dev | 72.50<!--claim:monoculture.sdu22_legal_dev.gold.long_form.overlap.class.sh_family_recall_pct:.2f--> | 27.50<!--claim:monoculture.sdu22_legal_dev.gold.long_form.overlap.class.unproposed_pct:.2f--> | 22.57<!--claim:monoculture.sdu22_legal_dev.gold.long_form.overlap.class.unproposed_alignable_from_gold_short_form_pct_of_gold:.2f--> | 81.76<!--claim:monoculture.sdu22_legal_dev.gold.long_form.overlap.class.all_proposers_recall_pct:.2f--> |
| SDU AE scientific, dev | 80.56<!--claim:monoculture.sdu22_scientific_dev.gold.long_form.overlap.class.sh_family_recall_pct:.2f--> | 19.44<!--claim:monoculture.sdu22_scientific_dev.gold.long_form.overlap.class.unproposed_pct:.2f--> | 13.75<!--claim:monoculture.sdu22_scientific_dev.gold.long_form.overlap.class.unproposed_alignable_from_gold_short_form_pct_of_gold:.2f--> | 84.44<!--claim:monoculture.sdu22_scientific_dev.gold.long_form.overlap.class.all_proposers_recall_pct:.2f--> |

The third column separates the two commitments empirically rather than by argument.
34.98<!--claim:monoculture.plod_all.gold.long_form.overlap.class.unproposed_alignable_from_gold_short_form_pct_of_gold:.2f-->
% of PLOD's gold long forms are unreached by every descendant **and** align cleanly with a gold
short form in the same passage. The validator would have accepted those pairs. The candidate
generator never offers them, because there is no bracket. **On this corpus the binding constraint
is the bracket, not the alignment**, and it accounts for most of the miss.

The control is MED1250, whose gold is pairs rather than spans: the family reaches
86.41<!--claim:monoculture.med1250.gold.pairs.sh_family_recall_pct:.2f--> % of its gold pairs and
the independent proposers add
0.00<!--claim:monoculture.med1250.gold.pairs.independent_gain_pct:.2f--> % to that union. On the
corpus these systems were built against, a proposer that cannot be one of them is worth nothing —
which is exactly what a gold standard drawn around their reach would produce.

Reading the unreached spans says what the class is, and it is one thing:

```
python -c "import json;r=json.load(open('bench/results.json',encoding='utf-8'))['runs']['monoculture.plod_all.gold.long_form.overlap.class'];print(*r['examples_unproposed_but_alignable'][:8],sep=chr(10))"
  EPI <- Echo planar imaging
  GD <- genetic distance
  nd <- not detected
  ELF <- epithelial lining fluid
  FEV1 <- forced expiratory volume in 1 second
  FVC <- forced vital capacity
  DEFF <- Design effect
  ICC <- Intracluster correlation coefficient
```

In the text these read `EPI = Echo planar imaging.`,
`BMI: body mass index; CE: cholesteryl ester; ELF: epithelial lining fluid`, and
`Abbreviations: Ct, cycle threshold; n/a, not applicable`. Figure legends, table footnotes and
`Abbreviations:` rosters, in three separator styles. PLOD's gold contains them because PLOD's gold
came from the authors' own glossaries; a bracket scanner contains none of them because there is no
bracket to scan.

On short forms the picture is the same and larger, and it needs one caveat stated first: these
corpora tag every *occurrence* of an abbreviation while a definition extractor emits one span per
*definition*, so part of the gap below is annotation convention rather than blind spot. The
`never proposed anywhere` column removes that part — it counts only gold short forms whose surface
string no descendant proposed **anywhere in the corpus**.

| Corpus | Gold short forms reached by the family % | Never proposed anywhere, % of gold | Reached once the independent proposers are added % |
|---|---:|---:|---:|
| PLOD-CW, all | 38.10<!--claim:monoculture.plod_all.gold.short_form.overlap.class.sh_family_recall_pct:.2f--> | **40.43<!--claim:monoculture.plod_all.gold.short_form.overlap.class.unproposed_never_proposed_anywhere_pct_of_gold:.2f-->** | 88.95<!--claim:monoculture.plod_all.gold.short_form.overlap.class.all_proposers_recall_pct:.2f--> |
| PLOD-CW, test | 38.15<!--claim:monoculture.plod_test.gold.short_form.overlap.class.sh_family_recall_pct:.2f--> | 55.56<!--claim:monoculture.plod_test.gold.short_form.overlap.class.unproposed_never_proposed_anywhere_pct_of_gold:.2f--> | 87.04<!--claim:monoculture.plod_test.gold.short_form.overlap.class.all_proposers_recall_pct:.2f--> |
| SDU AE legal, dev | 41.47<!--claim:monoculture.sdu22_legal_dev.gold.short_form.overlap.class.sh_family_recall_pct:.2f--> | 46.50<!--claim:monoculture.sdu22_legal_dev.gold.short_form.overlap.class.unproposed_never_proposed_anywhere_pct_of_gold:.2f--> | 89.20<!--claim:monoculture.sdu22_legal_dev.gold.short_form.overlap.class.all_proposers_recall_pct:.2f--> |
| SDU AE scientific, dev | 60.21<!--claim:monoculture.sdu22_scientific_dev.gold.short_form.overlap.class.sh_family_recall_pct:.2f--> | 27.94<!--claim:monoculture.sdu22_scientific_dev.gold.short_form.overlap.class.unproposed_never_proposed_anywhere_pct_of_gold:.2f--> | 93.20<!--claim:monoculture.sdu22_scientific_dev.gold.short_form.overlap.class.all_proposers_recall_pct:.2f--> |

### The independent proposer, with both of its numbers

`shapecue` finds short forms by orthography and long forms two ways: a lexical cue
(`hereinafter`, `stands for`, `also known as`) and an abbreviation roster (`SF = LF`, `SF: LF;`,
`SF, LF;`). It reads no bracket and compares no character of the short form against the long form.
Independence is argued as two falsifiable properties and tested as such in
`tests/test_monoculture.py`: it proposes `QQQ <- Bureau of Weights`, which shares no character with
its own abbreviation and which every descendant must refuse; and it proposes **nothing** on
`World Health Organization (WHO)`, which is where the descendants live.

Mechanically, on PLOD-CW all:

| Measure | `shapecue` | Highest of the seven S&H rows, and which one |
|---|---:|---:|
| Edges whose short form is not beside a bracket % | **99.83<!--claim:monoculture.plod_all.independence.bracketless_edges_pct_shapecue:.2f-->** | 2.31<!--claim:monoculture.plod_all.independence.bracketless_edges_pct_scispacy:.2f--> (`scispacy`) |
| Edges the S&H validator would refuse % | 8.87<!--claim:monoculture.plod_all.independence.sh_unalignable_pct_shapecue:.2f--> | 0.50<!--claim:monoculture.plod_all.independence.sh_unalignable_pct_abbreviation_extractor:.2f--> (`abbreviation_extractor`) |

The first row is the load-bearing one. Most real abbreviations *are* alignable, so a proposer can
be entirely independent of the validator and still emit alignable pairs — a low figure on the
second row is not evidence of descent. And the second row has a **noise floor**: the descendants
are not at zero because they report surfaces their internal alignment never saw, such as
`abbreviation_extractor` returning the short form `PC, [cases]`. That floor is why the second row
is reported and not relied on.

Coverage is the other half, and the brief for this work was explicit that a high independence
number must not stand in for a useful one:

| Proposer | Short-form overlap F1 % | Long-form overlap P % | Long-form overlap R % |
|---|---:|---:|---:|
| `acronymkit HIGH_PRECISION` | 52.96<!--claim:monoculture.plod_all.proposer.acronymkit_high_precision.short_form.overlap_f1:.2f--> | 90.17<!--claim:monoculture.plod_all.proposer.acronymkit_high_precision.long_form.overlap_precision:.2f--> | 55.93<!--claim:monoculture.plod_all.proposer.acronymkit_high_precision.long_form.overlap_recall:.2f--> |
| `allcaps` | 66.80<!--claim:monoculture.plod_all.proposer.allcaps.short_form.overlap_f1:.2f--> | — | — |
| **`shapecue`** | **75.65<!--claim:monoculture.plod_all.proposer.shapecue.short_form.overlap_f1:.2f-->** | 67.92<!--claim:monoculture.plod_all.proposer.shapecue.long_form.overlap_precision:.2f--> | 22.06<!--claim:monoculture.plod_all.proposer.shapecue.long_form.overlap_recall:.2f--> |

So: independent, best-in-table on short forms, and **narrow** on long forms — precise but reaching
only about a fifth of the gold. It is not a better extractor and is not offered as one.

**Its rules' firing counts, because a null result is not a result until the instrument's firing
count is known.** Over PLOD-CW all the two rules fired
586<!--claim:monoculture.plod_all.proposer.shapecue.cue_firings_total:,--> times between them, and
the split is the finding: the comma roster
535<!--claim:monoculture.plod_all.proposer.shapecue.cue_fired_roster_comma:,-->, the colon roster
34<!--claim:monoculture.plod_all.proposer.shapecue.cue_fired_roster_colon:,-->, the equals roster
16<!--claim:monoculture.plod_all.proposer.shapecue.cue_fired_roster_equals:,-->, and every lexical cue
in the list put together, once
(1<!--claim:monoculture.plod_all.proposer.shapecue.cue_fired_referred_to_as:,-->). The first draft
had **only** the cue rule; across every corpus on this page it emitted three edges in total, which
is not a sample and could not support an independence measurement at all. That absence is itself a
result: in these corpora, definitions written out in running prose with a lexical cue are
vanishingly rare, and the class the bracket scanners actually miss is the typographic one.

### What this does not establish

- **The genre confound above is not resolved**, and it is the first thing a hostile reader will
  find. MED1250's near-zero independent gain and its
  98.91<!--claim:monoculture.med1250.corpus.gold_pairs_long_form_bracket_adjacent_pct:.2f--> %
  parenthetical gold are equally well explained by "abstracts have no figure legends".
- **PLOD's gold is noisy by its own authors' account.** Their published validation sample reports
  wrong annotation in one segment in twenty and *missing* annotation in more than a quarter, so
  every "unreached" figure here has a denominator that is itself incomplete. The direction of that
  error is unknown, and it is large enough to matter to the third table.
- **The Federal Register reference set is not in these tables and cannot be.** Its candidate pool
  was assembled by pooling three Schwartz & Hearst descendants plus the all-caps rule (D-056), so a
  union gain measured against it would be circular by construction — the gold would contain only
  what the pool proposed.
- **No LLM proposer was built.** One would be non-deterministic and network-touching, could not
  ship, and would be a corpus-construction instrument rather than a measuring one. The refusal is
  the disposition: *permanent for the shipped library, open as a corpus-construction route*, and it
  is not needed for any measurement on this page.
- **Nothing here changes the extractor.** Knowing where the field's blind spot is does not say what
  to do about it, and this page deliberately stops at the measurement.

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

## The `SF = LF` legend flag, and a revert criterion that could not fail

`AbbreviationExtractor(config, legend_syntax=True)` reads a definition that no bracket introduces —
`GEF = Global Environment Facility`. It ships **off by default**. This section is why the default has
not moved, and what changed about the reason.

It shipped against an absolute criterion: *if MED1250 precision moves at all, revert.* It did not
move — not on any split, under any profile, on any recorded field. **It could not move.**

### The rule emits nothing on MED1250

| Profile | legend pairs emitted | documents that fire | MED1250 exact P, flag off | flag on |
|---|---:|---:|---:|---:|
| `HIGH_PRECISION` | 0<!--claim:shortform.med1250_all.legend_firing.high_precision.legend_pairs_emitted--> | 0<!--claim:shortform.med1250_all.legend_firing.high_precision.documents_emitting_a_legend_pair--> | 92.46<!--claim:shortform.med1250_all.legend_firing.high_precision.exact_precision_off:.2f--> | 92.46<!--claim:shortform.med1250_all.legend_firing.high_precision.exact_precision_on:.2f--> |
| `GENERAL` | 0<!--claim:shortform.med1250_all.legend_firing.general.legend_pairs_emitted--> | 0<!--claim:shortform.med1250_all.legend_firing.general.documents_emitting_a_legend_pair--> | 92.39<!--claim:shortform.med1250_all.legend_firing.general.exact_precision_off:.2f--> | 92.39<!--claim:shortform.med1250_all.legend_firing.general.exact_precision_on:.2f--> |
| `BIOMEDICAL` | 0<!--claim:shortform.med1250_all.legend_firing.biomedical.legend_pairs_emitted--> | 0<!--claim:shortform.med1250_all.legend_firing.biomedical.documents_emitting_a_legend_pair--> | 86.43<!--claim:shortform.med1250_all.legend_firing.biomedical.exact_precision_off:.2f--> | 86.43<!--claim:shortform.med1250_all.legend_firing.biomedical.exact_precision_on:.2f--> |

MED1250 is a declared **tuning** split (`bench/splits.toml`). The count is taken through `extract()`
itself rather than through a re-implementation of its gates —
`python bench/run_shortform.py --legend-cost` — over all 1,252<!--claim:shortform.med1250_all.legend_firing.documents:,--> documents.

**Bit-identical output was never evidence that the rule is harmless. It was evidence that the rule
never ran.** Be exact about what that does and does not mean. The criterion was not literally
untestable: a rule that fired here and was wrong would have failed it. What it tested is far narrower
than what it was read as testing. It tested one property — that the gates refuse a numeric assignment
— and it cannot test what the rule costs *when it fires*, because on this corpus it never does. A
precision figure computed over a prediction set the flag does not touch cannot move whatever the
added pairs would have been worth. Reading "MED1250 precision did not move" as "the precision risk
was checked" is the same failure as PLOD being structurally unable to corroborate the short-form span
fixes, arriving through the revert criterion instead of through the evidence table.

What MED1250 *does* test is the refusal path, under real load, and that part is worth keeping:

- 401<!--claim:shortform.med1250_all.legend_firing.separators--> separators in the corpus, of which 394<!--claim:shortform.med1250_all.legend_firing.separators_numeric_right_hand_side--> open a number — 98.25<!--claim:shortform.med1250_all.legend_firing.separators_numeric_right_hand_side_pct:.2f--> % of them.
- 0<!--claim:shortform.med1250_all.legend_exposure.gold_long_form_spans_after_a_separator--> of 1,221<!--claim:shortform.med1250_all.legend_exposure.gold_long_form_spans:,--> gold long forms begin immediately after a separator, so
  the corpus cannot show the class in either direction.
- Under `BIOMEDICAL`, 396<!--claim:shortform.med1250_all.legend_exposure_biomedical.gate_a_window_follows--> of those separators reach a search
  window and the alignment refuses every one.

A corpus that cannot show the class cannot adjudicate the rule. It can still stress the gate, and
this one does.

### Where the cost actually lives, measured

Both SDU@AAAI-22 AE dev splits, all three shipped profiles. **These are TUNING splits and
`bench/splits.toml` declares them contaminated**: the audit decomposed both splits' misses by legend
separator and used the result to rank this very proposal. Every number below is a tuning number.
Legal `train.json` was unread when this table was produced; it has since been spent under D-047 and
is reported further down, in its own section, because a figure from a mined arm and a figure from an
unread one are different things and merging them into one table would erase the distinction the
reservation existed to protect. Scientific `train.json` remains unallocated and unread.

| Split / profile | pairs added | SF exact P | SF overlap P | LF exact P | LF overlap P |
|---|---:|---:|---:|---:|---:|
| scientific / `HIGH_PRECISION` | 39<!--claim:shortform.sdu22_ae_scientific_dev.high_precision.legend_cost.legend_pairs_emitted--> | 95.90<!--claim:shortform.sdu22_ae_scientific_dev.high_precision.legend_cost.short_form.exact.precision_off:.2f--> &rarr; 95.67<!--claim:shortform.sdu22_ae_scientific_dev.high_precision.legend_cost.short_form.exact.precision_on:.2f--> | 97.78<!--claim:shortform.sdu22_ae_scientific_dev.high_precision.legend_cost.short_form.overlap.precision_off:.2f--> &rarr; 97.44<!--claim:shortform.sdu22_ae_scientific_dev.high_precision.legend_cost.short_form.overlap.precision_on:.2f--> | 83.76<!--claim:shortform.sdu22_ae_scientific_dev.high_precision.legend_cost.long_form.exact.precision_off:.2f--> &rarr; 83.81<!--claim:shortform.sdu22_ae_scientific_dev.high_precision.legend_cost.long_form.exact.precision_on:.2f--> | 97.26<!--claim:shortform.sdu22_ae_scientific_dev.high_precision.legend_cost.long_form.overlap.precision_off:.2f--> &rarr; 96.96<!--claim:shortform.sdu22_ae_scientific_dev.high_precision.legend_cost.long_form.overlap.precision_on:.2f--> |
| scientific / `GENERAL` | 39<!--claim:shortform.sdu22_ae_scientific_dev.general.legend_cost.legend_pairs_emitted--> | 95.90<!--claim:shortform.sdu22_ae_scientific_dev.general.legend_cost.short_form.exact.precision_off:.2f--> &rarr; 95.67<!--claim:shortform.sdu22_ae_scientific_dev.general.legend_cost.short_form.exact.precision_on:.2f--> | 97.78<!--claim:shortform.sdu22_ae_scientific_dev.general.legend_cost.short_form.overlap.precision_off:.2f--> &rarr; 97.44<!--claim:shortform.sdu22_ae_scientific_dev.general.legend_cost.short_form.overlap.precision_on:.2f--> | 83.76<!--claim:shortform.sdu22_ae_scientific_dev.general.legend_cost.long_form.exact.precision_off:.2f--> &rarr; 83.81<!--claim:shortform.sdu22_ae_scientific_dev.general.legend_cost.long_form.exact.precision_on:.2f--> | 97.26<!--claim:shortform.sdu22_ae_scientific_dev.general.legend_cost.long_form.overlap.precision_off:.2f--> &rarr; 96.96<!--claim:shortform.sdu22_ae_scientific_dev.general.legend_cost.long_form.overlap.precision_on:.2f--> |
| scientific / `BIOMEDICAL` | 52<!--claim:shortform.sdu22_ae_scientific_dev.biomedical.legend_cost.legend_pairs_emitted--> | 94.29<!--claim:shortform.sdu22_ae_scientific_dev.biomedical.legend_cost.short_form.exact.precision_off:.2f--> &rarr; 92.27<!--claim:shortform.sdu22_ae_scientific_dev.biomedical.legend_cost.short_form.exact.precision_on:.2f--> | 96.30<!--claim:shortform.sdu22_ae_scientific_dev.biomedical.legend_cost.short_form.overlap.precision_off:.2f--> &rarr; 94.13<!--claim:shortform.sdu22_ae_scientific_dev.biomedical.legend_cost.short_form.overlap.precision_on:.2f--> | 82.86<!--claim:shortform.sdu22_ae_scientific_dev.biomedical.legend_cost.long_form.exact.precision_off:.2f--> &rarr; 82.84<!--claim:shortform.sdu22_ae_scientific_dev.biomedical.legend_cost.long_form.exact.precision_on:.2f--> | 96.30<!--claim:shortform.sdu22_ae_scientific_dev.biomedical.legend_cost.long_form.overlap.precision_off:.2f--> &rarr; 95.83<!--claim:shortform.sdu22_ae_scientific_dev.biomedical.legend_cost.long_form.overlap.precision_on:.2f--> |
| legal / `HIGH_PRECISION` | 83<!--claim:shortform.sdu22_ae_legal_dev.high_precision.legend_cost.legend_pairs_emitted--> | 93.66<!--claim:shortform.sdu22_ae_legal_dev.high_precision.legend_cost.short_form.exact.precision_off:.2f--> &rarr; 94.41<!--claim:shortform.sdu22_ae_legal_dev.high_precision.legend_cost.short_form.exact.precision_on:.2f--> | 99.80<!--claim:shortform.sdu22_ae_legal_dev.high_precision.legend_cost.short_form.overlap.precision_off:.2f--> &rarr; 99.83<!--claim:shortform.sdu22_ae_legal_dev.high_precision.legend_cost.short_form.overlap.precision_on:.2f--> | 82.69<!--claim:shortform.sdu22_ae_legal_dev.high_precision.legend_cost.long_form.exact.precision_off:.2f--> &rarr; 84.67<!--claim:shortform.sdu22_ae_legal_dev.high_precision.legend_cost.long_form.exact.precision_on:.2f--> | 96.74<!--claim:shortform.sdu22_ae_legal_dev.high_precision.legend_cost.long_form.overlap.precision_off:.2f--> &rarr; 97.21<!--claim:shortform.sdu22_ae_legal_dev.high_precision.legend_cost.long_form.overlap.precision_on:.2f--> |
| legal / `GENERAL` | 83<!--claim:shortform.sdu22_ae_legal_dev.general.legend_cost.legend_pairs_emitted--> | 93.67<!--claim:shortform.sdu22_ae_legal_dev.general.legend_cost.short_form.exact.precision_off:.2f--> &rarr; 94.42<!--claim:shortform.sdu22_ae_legal_dev.general.legend_cost.short_form.exact.precision_on:.2f--> | 99.80<!--claim:shortform.sdu22_ae_legal_dev.general.legend_cost.short_form.overlap.precision_off:.2f--> &rarr; 99.83<!--claim:shortform.sdu22_ae_legal_dev.general.legend_cost.short_form.overlap.precision_on:.2f--> | 82.72<!--claim:shortform.sdu22_ae_legal_dev.general.legend_cost.long_form.exact.precision_off:.2f--> &rarr; 84.70<!--claim:shortform.sdu22_ae_legal_dev.general.legend_cost.long_form.exact.precision_on:.2f--> | 96.75<!--claim:shortform.sdu22_ae_legal_dev.general.legend_cost.long_form.overlap.precision_off:.2f--> &rarr; 97.22<!--claim:shortform.sdu22_ae_legal_dev.general.legend_cost.long_form.overlap.precision_on:.2f--> |
| legal / `BIOMEDICAL` | 88<!--claim:shortform.sdu22_ae_legal_dev.biomedical.legend_cost.legend_pairs_emitted--> | 92.56<!--claim:shortform.sdu22_ae_legal_dev.biomedical.legend_cost.short_form.exact.precision_off:.2f--> &rarr; 92.65<!--claim:shortform.sdu22_ae_legal_dev.biomedical.legend_cost.short_form.exact.precision_on:.2f--> | 98.59<!--claim:shortform.sdu22_ae_legal_dev.biomedical.legend_cost.short_form.overlap.precision_off:.2f--> &rarr; 97.95<!--claim:shortform.sdu22_ae_legal_dev.biomedical.legend_cost.short_form.overlap.precision_on:.2f--> | 81.56<!--claim:shortform.sdu22_ae_legal_dev.biomedical.legend_cost.long_form.exact.precision_off:.2f--> &rarr; 83.48<!--claim:shortform.sdu22_ae_legal_dev.biomedical.legend_cost.long_form.exact.precision_on:.2f--> | 95.39<!--claim:shortform.sdu22_ae_legal_dev.biomedical.legend_cost.long_form.overlap.precision_off:.2f--> &rarr; 96.08<!--claim:shortform.sdu22_ae_legal_dev.biomedical.legend_cost.long_form.overlap.precision_on:.2f--> |

**The worst row is `scientific` / `BIOMEDICAL`, and it is a row the shipping table did not contain.**
Short-form overlap precision moves -2.18<!--claim:shortform.sdu22_ae_scientific_dev.biomedical.legend_cost.short_form.overlap.precision_delta:.2f-->
points there and exact precision -2.01<!--claim:shortform.sdu22_ae_scientific_dev.biomedical.legend_cost.short_form.exact.precision_delta:.2f-->.
The table this flag shipped on covered `HIGH_PRECISION` only, where the worst move on the same split
is -0.34<!--claim:shortform.sdu22_ae_scientific_dev.high_precision.legend_cost.short_form.overlap.precision_delta:.2f--> — a sixth
of it. Nothing was mis-stated; one profile was measured and three ship, and a table that reports the
first as the worst case is a claim about the other two that was never made.

Recall and F1 for the same six runs, with the recall ceiling in the same table because every point
above it is bought by emitting a definition the corpus does not annotate:

| Split / profile | SF exact recall | SF recall ceiling | SF exact F1 | LF exact F1 | LF overlap F1 |
|---|---:|---:|---:|---:|---:|
| scientific / `HIGH_PRECISION` | 57.84<!--claim:shortform.sdu22_ae_scientific_dev.high_precision.legend_cost.short_form.exact.recall_off:.2f--> &rarr; 61.55<!--claim:shortform.sdu22_ae_scientific_dev.high_precision.legend_cost.short_form.exact.recall_on:.2f--> | 74.23<!--claim:shortform.sdu22_ae_scientific_dev.high_precision.legend_cost.short_form_recall_ceiling_pct:.2f--> % | 72.15<!--claim:shortform.sdu22_ae_scientific_dev.high_precision.legend_cost.short_form.exact.f1_off:.2f--> &rarr; 74.91<!--claim:shortform.sdu22_ae_scientific_dev.high_precision.legend_cost.short_form.exact.f1_on:.2f--> | 75.10<!--claim:shortform.sdu22_ae_scientific_dev.high_precision.legend_cost.long_form.exact.f1_off:.2f--> &rarr; 77.83<!--claim:shortform.sdu22_ae_scientific_dev.high_precision.legend_cost.long_form.exact.f1_on:.2f--> | 87.20<!--claim:shortform.sdu22_ae_scientific_dev.high_precision.legend_cost.long_form.overlap.f1_off:.2f--> &rarr; 90.03<!--claim:shortform.sdu22_ae_scientific_dev.high_precision.legend_cost.long_form.overlap.f1_on:.2f--> |
| scientific / `GENERAL` | 57.84<!--claim:shortform.sdu22_ae_scientific_dev.general.legend_cost.short_form.exact.recall_off:.2f--> &rarr; 61.55<!--claim:shortform.sdu22_ae_scientific_dev.general.legend_cost.short_form.exact.recall_on:.2f--> | 74.23<!--claim:shortform.sdu22_ae_scientific_dev.general.legend_cost.short_form_recall_ceiling_pct:.2f--> % | 72.15<!--claim:shortform.sdu22_ae_scientific_dev.general.legend_cost.short_form.exact.f1_off:.2f--> &rarr; 74.91<!--claim:shortform.sdu22_ae_scientific_dev.general.legend_cost.short_form.exact.f1_on:.2f--> | 75.10<!--claim:shortform.sdu22_ae_scientific_dev.general.legend_cost.long_form.exact.f1_off:.2f--> &rarr; 77.83<!--claim:shortform.sdu22_ae_scientific_dev.general.legend_cost.long_form.exact.f1_on:.2f--> | 87.20<!--claim:shortform.sdu22_ae_scientific_dev.general.legend_cost.long_form.overlap.f1_off:.2f--> &rarr; 90.03<!--claim:shortform.sdu22_ae_scientific_dev.general.legend_cost.long_form.overlap.f1_on:.2f--> |
| scientific / `BIOMEDICAL` | 57.84<!--claim:shortform.sdu22_ae_scientific_dev.biomedical.legend_cost.short_form.exact.recall_off:.2f--> &rarr; 61.55<!--claim:shortform.sdu22_ae_scientific_dev.biomedical.legend_cost.short_form.exact.recall_on:.2f--> | 74.23<!--claim:shortform.sdu22_ae_scientific_dev.biomedical.legend_cost.short_form_recall_ceiling_pct:.2f--> % | 71.69<!--claim:shortform.sdu22_ae_scientific_dev.biomedical.legend_cost.short_form.exact.f1_off:.2f--> &rarr; 73.84<!--claim:shortform.sdu22_ae_scientific_dev.biomedical.legend_cost.short_form.exact.f1_on:.2f--> | 74.98<!--claim:shortform.sdu22_ae_scientific_dev.biomedical.legend_cost.long_form.exact.f1_off:.2f--> &rarr; 78.42<!--claim:shortform.sdu22_ae_scientific_dev.biomedical.legend_cost.long_form.exact.f1_on:.2f--> | 87.15<!--claim:shortform.sdu22_ae_scientific_dev.biomedical.legend_cost.long_form.overlap.f1_off:.2f--> &rarr; 90.71<!--claim:shortform.sdu22_ae_scientific_dev.biomedical.legend_cost.long_form.overlap.f1_on:.2f--> |
| legal / `HIGH_PRECISION` | 37.76<!--claim:shortform.sdu22_ae_legal_dev.high_precision.legend_cost.short_form.exact.recall_off:.2f--> &rarr; 44.52<!--claim:shortform.sdu22_ae_legal_dev.high_precision.legend_cost.short_form.exact.recall_on:.2f--> | 55.15<!--claim:shortform.sdu22_ae_legal_dev.high_precision.legend_cost.short_form_recall_ceiling_pct:.2f--> % | 53.82<!--claim:shortform.sdu22_ae_legal_dev.high_precision.legend_cost.short_form.exact.f1_off:.2f--> &rarr; 60.50<!--claim:shortform.sdu22_ae_legal_dev.high_precision.legend_cost.short_form.exact.f1_on:.2f--> | 70.00<!--claim:shortform.sdu22_ae_legal_dev.high_precision.legend_cost.long_form.exact.f1_off:.2f--> &rarr; 78.20<!--claim:shortform.sdu22_ae_legal_dev.high_precision.legend_cost.long_form.exact.f1_on:.2f--> | 81.90<!--claim:shortform.sdu22_ae_legal_dev.high_precision.legend_cost.long_form.overlap.f1_off:.2f--> &rarr; 89.78<!--claim:shortform.sdu22_ae_legal_dev.high_precision.legend_cost.long_form.overlap.f1_on:.2f--> |
| legal / `GENERAL` | 37.84<!--claim:shortform.sdu22_ae_legal_dev.general.legend_cost.short_form.exact.recall_off:.2f--> &rarr; 44.60<!--claim:shortform.sdu22_ae_legal_dev.general.legend_cost.short_form.exact.recall_on:.2f--> | 55.15<!--claim:shortform.sdu22_ae_legal_dev.general.legend_cost.short_form_recall_ceiling_pct:.2f--> % | 53.90<!--claim:shortform.sdu22_ae_legal_dev.general.legend_cost.short_form.exact.f1_off:.2f--> &rarr; 60.58<!--claim:shortform.sdu22_ae_legal_dev.general.legend_cost.short_form.exact.f1_on:.2f--> | 70.11<!--claim:shortform.sdu22_ae_legal_dev.general.legend_cost.long_form.exact.f1_off:.2f--> &rarr; 78.30<!--claim:shortform.sdu22_ae_legal_dev.general.legend_cost.long_form.exact.f1_on:.2f--> | 82.00<!--claim:shortform.sdu22_ae_legal_dev.general.legend_cost.long_form.overlap.f1_off:.2f--> &rarr; 89.87<!--claim:shortform.sdu22_ae_legal_dev.general.legend_cost.long_form.overlap.f1_on:.2f--> |
| legal / `BIOMEDICAL` | 37.92<!--claim:shortform.sdu22_ae_legal_dev.biomedical.legend_cost.short_form.exact.recall_off:.2f--> &rarr; 44.68<!--claim:shortform.sdu22_ae_legal_dev.biomedical.legend_cost.short_form.exact.recall_on:.2f--> | 55.15<!--claim:shortform.sdu22_ae_legal_dev.biomedical.legend_cost.short_form_recall_ceiling_pct:.2f--> % | 53.80<!--claim:shortform.sdu22_ae_legal_dev.biomedical.legend_cost.short_form.exact.f1_off:.2f--> &rarr; 60.29<!--claim:shortform.sdu22_ae_legal_dev.biomedical.legend_cost.short_form.exact.f1_on:.2f--> | 69.69<!--claim:shortform.sdu22_ae_legal_dev.biomedical.legend_cost.long_form.exact.f1_off:.2f--> &rarr; 78.03<!--claim:shortform.sdu22_ae_legal_dev.biomedical.legend_cost.long_form.exact.f1_on:.2f--> | 81.51<!--claim:shortform.sdu22_ae_legal_dev.biomedical.legend_cost.long_form.overlap.f1_off:.2f--> &rarr; 89.81<!--claim:shortform.sdu22_ae_legal_dev.biomedical.legend_cost.long_form.overlap.f1_on:.2f--> |

In this table no F1 falls: not on either label, under either convention, on either split, at any
profile. Every recall stays under its ceiling. Neither statement extends past these six runs.

### What the added pairs actually are

The increment is the only thing that can move precision, so its own precision is the sharper
statement. It is also the only thing that moves it: in every one of the
4<!--claim:shortform.sdu22_ae_scientific_dev.biomedical.legend_cost.label_convention_cells_checked-->
label-and-convention cells of all six runs below, the corpus's false-positive count rises by exactly
the number of added pairs that missed gold — `increment_accounts_for_every_new_false_positive` is
true on every record. "The flag adds candidates and re-ranks none" is asserted by a unit test on
synthetic documents; this is the same property holding at corpus scale, which is what keeps this
change out of the region where the pseudo-precision diagnosis bites.

| Split / profile | pairs added | SF span exactly gold | LF span exactly gold | LF span overlapping gold | matching no gold long form |
|---|---:|---:|---:|---:|---:|
| scientific / `HIGH_PRECISION` | 39<!--claim:shortform.sdu22_ae_scientific_dev.high_precision.legend_cost.legend_pairs_emitted--> | 36<!--claim:shortform.sdu22_ae_scientific_dev.high_precision.legend_cost.increment_short_form_exact_hits--> | 33<!--claim:shortform.sdu22_ae_scientific_dev.high_precision.legend_cost.increment_long_form_exact_hits--> | 36<!--claim:shortform.sdu22_ae_scientific_dev.high_precision.legend_cost.increment_long_form_overlap_hits--> | 3<!--claim:shortform.sdu22_ae_scientific_dev.high_precision.legend_cost.added_pairs_matching_no_gold_long_form_count--> |
| scientific / `GENERAL` | 39<!--claim:shortform.sdu22_ae_scientific_dev.general.legend_cost.legend_pairs_emitted--> | 36<!--claim:shortform.sdu22_ae_scientific_dev.general.legend_cost.increment_short_form_exact_hits--> | 33<!--claim:shortform.sdu22_ae_scientific_dev.general.legend_cost.increment_long_form_exact_hits--> | 36<!--claim:shortform.sdu22_ae_scientific_dev.general.legend_cost.increment_long_form_overlap_hits--> | 3<!--claim:shortform.sdu22_ae_scientific_dev.general.legend_cost.added_pairs_matching_no_gold_long_form_count--> |
| scientific / `BIOMEDICAL` | 52<!--claim:shortform.sdu22_ae_scientific_dev.biomedical.legend_cost.legend_pairs_emitted--> | 36<!--claim:shortform.sdu22_ae_scientific_dev.biomedical.legend_cost.increment_short_form_exact_hits--> | 43<!--claim:shortform.sdu22_ae_scientific_dev.biomedical.legend_cost.increment_long_form_exact_hits--> | 47<!--claim:shortform.sdu22_ae_scientific_dev.biomedical.legend_cost.increment_long_form_overlap_hits--> | 5<!--claim:shortform.sdu22_ae_scientific_dev.biomedical.legend_cost.added_pairs_matching_no_gold_long_form_count--> |
| legal / `HIGH_PRECISION` | 83<!--claim:shortform.sdu22_ae_legal_dev.high_precision.legend_cost.legend_pairs_emitted--> | 82<!--claim:shortform.sdu22_ae_legal_dev.high_precision.legend_cost.increment_short_form_exact_hits--> | 80<!--claim:shortform.sdu22_ae_legal_dev.high_precision.legend_cost.increment_long_form_exact_hits--> | 83<!--claim:shortform.sdu22_ae_legal_dev.high_precision.legend_cost.increment_long_form_overlap_hits--> | 0<!--claim:shortform.sdu22_ae_legal_dev.high_precision.legend_cost.added_pairs_matching_no_gold_long_form_count--> |
| legal / `GENERAL` | 83<!--claim:shortform.sdu22_ae_legal_dev.general.legend_cost.legend_pairs_emitted--> | 82<!--claim:shortform.sdu22_ae_legal_dev.general.legend_cost.increment_short_form_exact_hits--> | 80<!--claim:shortform.sdu22_ae_legal_dev.general.legend_cost.increment_long_form_exact_hits--> | 83<!--claim:shortform.sdu22_ae_legal_dev.general.legend_cost.increment_long_form_overlap_hits--> | 0<!--claim:shortform.sdu22_ae_legal_dev.general.legend_cost.added_pairs_matching_no_gold_long_form_count--> |
| legal / `BIOMEDICAL` | 88<!--claim:shortform.sdu22_ae_legal_dev.biomedical.legend_cost.legend_pairs_emitted--> | 82<!--claim:shortform.sdu22_ae_legal_dev.biomedical.legend_cost.increment_short_form_exact_hits--> | 83<!--claim:shortform.sdu22_ae_legal_dev.biomedical.legend_cost.increment_long_form_exact_hits--> | 88<!--claim:shortform.sdu22_ae_legal_dev.biomedical.legend_cost.increment_long_form_overlap_hits--> | 0<!--claim:shortform.sdu22_ae_legal_dev.biomedical.legend_cost.added_pairs_matching_no_gold_long_form_count--> |

On the legal split not one added pair misses gold entirely, at any profile. On the scientific split
the ones that do are worth naming rather than counting:

```
NLP = Natural Language Processing researcher    a legend this corpus does not annotate
HA  = high attachment                           a legend this corpus does not annotate
WER = word error rate                           a legend this corpus does not annotate
A   = Ambiguous                    BIOMEDICAL   a legend this corpus does not annotate
X   = x|W1                         BIOMEDICAL   from  P (X = x|W1 = w1, . . . , WN = wN )
```

**Exactly one added pair in this entire table is an equation**, and it needs `BIOMEDICAL` — the one
shipped profile admitting a single-character short form with no uppercase requirement — to exist at
all. Under the shipped bounds the same sentence yields nothing;
`tests/test_extractor.py::test_the_one_equation_a_loosened_gate_admits` pins both halves, so the
loose profile's behaviour is a decision on the record rather than something to rediscover.

That classification is a hand reading of a listed residue, not a rule, and the list is in
`results.json` under `added_pairs_not_exactly_gold` so it can be disagreed with. The worst row's
short-form precision is attributable the same way: the eleven further `BIOMEDICAL` short forms that
are not exactly gold — `R = Random`, `S = Subject`, `J = Japanese`, `F = Friendship` — are
single-letter legends this corpus does not tag as acronyms. **That is an explanation of the loss and
not a deduction from it.** The tables report the raw delta; nothing is adjusted for annotation
policy, because an extractor scored against a corpus is scored against that corpus's decisions.

### The premise this was asked to test, and what the census says about it

The reason to look at scientific text is that `=` there is equation surface. On the corpora this
repository actually reads, **the equation surface and the legend class are not in the same corpus**:

| Corpus | separators | opening a number | legend pairs emitted, `HIGH_PRECISION` |
|---|---:|---:|---:|
| MED1250 (tuning) | 401<!--claim:shortform.med1250_all.legend_firing.separators--> | 394<!--claim:shortform.med1250_all.legend_firing.separators_numeric_right_hand_side--> (98.25<!--claim:shortform.med1250_all.legend_firing.separators_numeric_right_hand_side_pct:.2f--> %) | 0<!--claim:shortform.med1250_all.legend_firing.high_precision.legend_pairs_emitted--> |
| SDU-22 AE scientific dev (tuning) | 147<!--claim:shortform.sdu22_ae_scientific_dev.high_precision.legend_cost.separators--> | 5<!--claim:shortform.sdu22_ae_scientific_dev.high_precision.legend_cost.separators_numeric_right_hand_side--> (3.40<!--claim:shortform.sdu22_ae_scientific_dev.high_precision.legend_cost.separators_numeric_right_hand_side_pct:.2f--> %) | 39<!--claim:shortform.sdu22_ae_scientific_dev.high_precision.legend_cost.legend_pairs_emitted--> |
| SDU-22 AE legal dev (tuning) | 138<!--claim:shortform.sdu22_ae_legal_dev.high_precision.legend_cost.separators--> | 0<!--claim:shortform.sdu22_ae_legal_dev.high_precision.legend_cost.separators_numeric_right_hand_side--> (0.00<!--claim:shortform.sdu22_ae_legal_dev.high_precision.legend_cost.separators_numeric_right_hand_side_pct:.2f--> %) | 83<!--claim:shortform.sdu22_ae_legal_dev.high_precision.legend_cost.legend_pairs_emitted--> |

A separator *opens a number* when the first non-blank character after it starts one — `n = 523`,
`P = 0.05`, `Ki = 1 microM`. That is deliberately the narrowest checkable reading; a wider one would
measure a different surface from the one the code refuses.

So the corpus that loads the gate cannot show the class, and the corpora that show the class barely
load the gate. **None of these three does both**, and the fourth cannot help. PLOD-CW is the one
held-out corpus, and only 0.89<!--claim:shortform.plod_all.legend_exposure.gold_long_form_spans_after_a_separator_pct:.2f--> %
of its gold long forms begin after a separator; it emits 12<!--claim:shortform.plod_all.legend_exposure.gate_a_prefix_aligns-->
predictions across the whole corpus under `HIGH_PRECISION`, which is agreement worth much less than
the fact that it agrees.

**A sentence that stood here said "and improves every field", and it was false when it was written.**
It was not false because of a later change; the run it describes was already in
`bench/results.json`. On the pooled PLOD split under `HIGH_PRECISION` — the very configuration the
sentence was measured at — short-form exact precision moves
93.66<!--claim:shortform.plod_all.tight.high_precision.balanced_trim.short_form.exact_precision:.2f--> &rarr;
93.63<!--claim:shortform.plod_all.tight.high_precision.legend.short_form.exact_precision:.2f-->, and
three fields fall under `tight` and four under `spaced`. Every one of those is a single extra false
positive on a corpus of 1,351<!--claim:shortform.plod_all.tight.high_precision.legend.documents:,-->
documents, which is why nobody noticed and is not why it was published. The `dev` and `test` halves
*do* improve every field, and quoting the halves as the corpus is the composition error this table
was pooled to prevent.

**And the profile axis reverses the sign.** `--spans` swept one profile until this round (see below);
swept across all three, the same rule on the same held-out corpus moves short-form exact precision
91.90<!--claim:shortform.plod_all.tight.biomedical.balanced_trim.short_form.exact_precision:.2f--> &rarr;
91.59<!--claim:shortform.plod_all.tight.biomedical.legend.short_form.exact_precision:.2f--> under
`BIOMEDICAL`, from 16<!--claim:shortform.plod_all.legend_exposure_biomedical.gate_a_prefix_aligns-->
emissions rather than 12<!--claim:shortform.plod_all.legend_exposure.gate_a_prefix_aligns-->. On the
`dev` half alone it reads
91.89<!--claim:shortform.plod_dev.tight.biomedical.balanced_trim.short_form.exact_precision:.2f--> &rarr;
89.66<!--claim:shortform.plod_dev.tight.biomedical.legend.short_form.exact_precision:.2f-->, which is
**three false positives** —
9<!--claim:shortform.plod_dev.tight.biomedical.balanced_trim.short_form.exact_false_positives--> to
12<!--claim:shortform.plod_dev.tight.biomedical.legend.short_form.exact_false_positives--> on
126<!--claim:shortform.plod_dev.tight.biomedical.legend.documents--> documents — and is quoted here
only to be refused as a number: a delta a corpus resolves to three spans is not a measurement of
anything, which is the reason the pooled split exists.

The genre the risk was named for — engineering and physics body text, `Tsat=Tamb [kPa]`,
`wC = carbon mass fraction`, `xH2Oexhdry` — remains unmeasured. Those surfaces are refused in
`tests/test_extractor.py`, which is a pinned decision, not corpus evidence. **That gap, not the
numbers above, is why the default is off**, and it is the same reason the flag shipped off in the
first place: the two corpora that show the gain are contaminated for precisely this change.

### The unmined arm, spent once, under D-047

Every figure above is measured on a split whose misses were read *before* this rule was proposed.
D-047 allocated the one remaining unread arm of this corpus — SDU-22 AE legal `train.json`,
3,564<!--claim:shortform.sdu22_ae_legal_train.corpus.documents:,--> samples — to exactly this
question, and `bench/splits.toml` refuses a read of it until a run declares the spend by name. It
was spent once, by `python bench/run_shortform.py --spend-legal-train --save`, and the arm is now
mined and labelled `tuning` like everything else here.

**The firing count first, because a null result without one is not a result.** The rule emitted
688<!--claim:shortform.sdu22_ae_legal_train.high_precision.legend_cost.legend_pairs_emitted-->
pairs under `HIGH_PRECISION` and
703<!--claim:shortform.sdu22_ae_legal_train.biomedical.legend_cost.legend_pairs_emitted--> under
`BIOMEDICAL`, in
270<!--claim:shortform.sdu22_ae_legal_train.high_precision.legend_cost.documents_emitting_a_legend_pair-->
documents. **This run fired, so it measured something** — unlike the MED1250 criterion at the head of
this section, which fired zero times at every profile.

| Profile | pairs added | SF exact P | SF overlap P | LF exact P | LF overlap P |
|---|---:|---:|---:|---:|---:|
| `HIGH_PRECISION` | 688<!--claim:shortform.sdu22_ae_legal_train.high_precision.legend_cost.legend_pairs_emitted--> | 93.71<!--claim:shortform.sdu22_ae_legal_train.high_precision.legend_cost.short_form.exact.precision_off:.2f--> &rarr; 94.51<!--claim:shortform.sdu22_ae_legal_train.high_precision.legend_cost.short_form.exact.precision_on:.2f--> | 99.24<!--claim:shortform.sdu22_ae_legal_train.high_precision.legend_cost.short_form.overlap.precision_off:.2f--> &rarr; 99.27<!--claim:shortform.sdu22_ae_legal_train.high_precision.legend_cost.short_form.overlap.precision_on:.2f--> | 81.92<!--claim:shortform.sdu22_ae_legal_train.high_precision.legend_cost.long_form.exact.precision_off:.2f--> &rarr; 83.46<!--claim:shortform.sdu22_ae_legal_train.high_precision.legend_cost.long_form.exact.precision_on:.2f--> | 95.85<!--claim:shortform.sdu22_ae_legal_train.high_precision.legend_cost.long_form.overlap.precision_off:.2f--> &rarr; 96.38<!--claim:shortform.sdu22_ae_legal_train.high_precision.legend_cost.long_form.overlap.precision_on:.2f--> |
| `GENERAL` | 688<!--claim:shortform.sdu22_ae_legal_train.general.legend_cost.legend_pairs_emitted--> | 93.63<!--claim:shortform.sdu22_ae_legal_train.general.legend_cost.short_form.exact.precision_off:.2f--> &rarr; 94.44<!--claim:shortform.sdu22_ae_legal_train.general.legend_cost.short_form.exact.precision_on:.2f--> | 99.19<!--claim:shortform.sdu22_ae_legal_train.general.legend_cost.short_form.overlap.precision_off:.2f--> &rarr; 99.22<!--claim:shortform.sdu22_ae_legal_train.general.legend_cost.short_form.overlap.precision_on:.2f--> | 81.79<!--claim:shortform.sdu22_ae_legal_train.general.legend_cost.long_form.exact.precision_off:.2f--> &rarr; 83.34<!--claim:shortform.sdu22_ae_legal_train.general.legend_cost.long_form.exact.precision_on:.2f--> | 95.74<!--claim:shortform.sdu22_ae_legal_train.general.legend_cost.long_form.overlap.precision_off:.2f--> &rarr; 96.28<!--claim:shortform.sdu22_ae_legal_train.general.legend_cost.long_form.overlap.precision_on:.2f--> |
| `BIOMEDICAL` | 703<!--claim:shortform.sdu22_ae_legal_train.biomedical.legend_cost.legend_pairs_emitted--> | 92.70<!--claim:shortform.sdu22_ae_legal_train.biomedical.legend_cost.short_form.exact.precision_off:.2f--> &rarr; 93.36<!--claim:shortform.sdu22_ae_legal_train.biomedical.legend_cost.short_form.exact.precision_on:.2f--> | 98.25<!--claim:shortform.sdu22_ae_legal_train.biomedical.legend_cost.short_form.overlap.precision_off:.2f--> &rarr; 98.15<!--claim:shortform.sdu22_ae_legal_train.biomedical.legend_cost.short_form.overlap.precision_on:.2f--> | 80.93<!--claim:shortform.sdu22_ae_legal_train.biomedical.legend_cost.long_form.exact.precision_off:.2f--> &rarr; 82.54<!--claim:shortform.sdu22_ae_legal_train.biomedical.legend_cost.long_form.exact.precision_on:.2f--> | 94.73<!--claim:shortform.sdu22_ae_legal_train.biomedical.legend_cost.long_form.overlap.precision_off:.2f--> &rarr; 95.41<!--claim:shortform.sdu22_ae_legal_train.biomedical.legend_cost.long_form.overlap.precision_on:.2f--> |

**Eleven of the twelve precision cells rise.** The one that falls is
`BIOMEDICAL` short-form *overlap* precision, by
-0.10<!--claim:shortform.sdu22_ae_legal_train.biomedical.legend_cost.short_form.overlap.precision_delta:.2f-->
points, and it is the worst precision move anywhere on this arm. Short-form exact recall rises
38.76<!--claim:shortform.sdu22_ae_legal_train.high_precision.legend_cost.short_form.exact.recall_off:.2f--> &rarr;
45.91<!--claim:shortform.sdu22_ae_legal_train.high_precision.legend_cost.short_form.exact.recall_on:.2f-->
against a ceiling of
55.04<!--claim:shortform.sdu22_ae_legal_train.corpus.ceiling_pct:.2f--> %, and long-form exact F1
70.43<!--claim:shortform.sdu22_ae_legal_train.high_precision.legend_cost.long_form.exact.f1_off:.2f--> &rarr;
78.37<!--claim:shortform.sdu22_ae_legal_train.high_precision.legend_cost.long_form.exact.f1_on:.2f-->.
The increment's own precision is
99.13<!--claim:shortform.sdu22_ae_legal_train.high_precision.legend_cost.increment_short_form_exact_precision:.2f--> %
on short-form spans and
99.42<!--claim:shortform.sdu22_ae_legal_train.high_precision.legend_cost.increment_long_form_overlap_precision:.2f--> %
on long-form overlap;
4<!--claim:shortform.sdu22_ae_legal_train.high_precision.legend_cost.added_pairs_matching_no_gold_long_form_count-->
of the 688 added pairs match no gold long form at all, and
`increment_accounts_for_every_new_false_positive` is true on every record, so the flag added
candidates and re-ranked none at eight times the scale the property was first checked at.

**What this does and does not settle.** It settles the thing D-047 said nothing else in this
repository could buy: an honest precision delta for a shipped flag on an arm that was not mined to
invent it, and the delta is **not a cost**. It settles nothing about the reason the default is off.
Legal `dev` had 0<!--claim:shortform.sdu22_ae_legal_dev.high_precision.legend_cost.separators_numeric_right_hand_side-->
of 138<!--claim:shortform.sdu22_ae_legal_dev.high_precision.legend_cost.separators--> separators
opening a number; `train` has
27<!--claim:shortform.sdu22_ae_legal_train.high_precision.legend_cost.separators_numeric_right_hand_side-->
of 1,063<!--claim:shortform.sdu22_ae_legal_train.high_precision.legend_cost.separators:,-->, which is
2.54<!--claim:shortform.sdu22_ae_legal_train.high_precision.legend_cost.separators_numeric_right_hand_side_pct:.2f--> %,
and **0<!--claim:shortform.sdu22_ae_legal_train.high_precision.legend_cost.legend_pairs_on_a_numeric_right_hand_side-->
of the emitted pairs sit on one**. That is a statement about what was emitted, not about which gate
refused what: the funnel does not attribute the 375 separators lost between "a window follows" and "a
prefix aligns" to any particular cause. Twenty-seven separators is a floor on an equation surface,
in the sense D-045 fixed, and it is not the engineering and physics body text the flag is off for.

### The miss decomposition, which is the other half of the spend

D-047 made the decomposition a condition rather than a courtesy, because whoever owns the read owns
what may be concluded from it. Under `HIGH_PRECISION` the shipped default misses
2,006<!--claim:shortform.sdu22_ae_legal_train.high_precision.miss_decomposition.gold_long_form_spans_missed:,-->
of 5,246<!--claim:shortform.sdu22_ae_legal_train.high_precision.miss_decomposition.gold_long_form_spans:,-->
gold long-form spans, and they decompose over the 30 characters before each miss:

| Bucket | missed | recovered by the flag |
|---|---:|---:|
| after an `=` | 1,001<!--claim:shortform.sdu22_ae_legal_train.high_precision.miss_decomposition.missed_after_equals_within_window:,--> | 635<!--claim:shortform.sdu22_ae_legal_train.high_precision.miss_decomposition.missed_after_equals_within_window_recovered_by_legend--> |
| after a `:` | 27<!--claim:shortform.sdu22_ae_legal_train.high_precision.miss_decomposition.missed_after_colon_within_window--> | 0<!--claim:shortform.sdu22_ae_legal_train.high_precision.miss_decomposition.missed_after_colon_within_window_recovered_by_legend--> |
| after an opening bracket | 291<!--claim:shortform.sdu22_ae_legal_train.high_precision.miss_decomposition.missed_after_open_bracket_within_window--> | 0<!--claim:shortform.sdu22_ae_legal_train.high_precision.miss_decomposition.missed_after_open_bracket_within_window_recovered_by_legend--> |
| neither in the window | 687<!--claim:shortform.sdu22_ae_legal_train.high_precision.miss_decomposition.missed_no_separator_or_bracket_in_window--> | 0<!--claim:shortform.sdu22_ae_legal_train.high_precision.miss_decomposition.missed_no_separator_or_bracket_in_window_recovered_by_legend--> |

The flag recovers
31.66<!--claim:shortform.sdu22_ae_legal_train.high_precision.miss_decomposition.misses_recovered_by_legend_pct:.2f--> %
of all misses and **nothing outside the `=` bucket**, which is the strongest available statement that
it does what it says and only that. The window is the audit's, not a new one, and the instrument
reproduces the audit's own dev decomposition to the span on the colon bucket — that check is what
licenses reading the train row as comparable rather than merely adjacent.

### Experiment nine rode free, and it wins on this arm

`_VARIANTS` scores `two_word` and `legend` in one invocation, so D-047 made saving the `two_word` row
a condition of the spend: it costs zero extra reads and it is the only way experiment nine (D-032) is
answered once the arm is mined. Against its own comparator, `baseline`, on all three profiles:

| Profile | SF exact P | SF exact R | SF exact F1 | LF exact F1 |
|---|---:|---:|---:|---:|
| `HIGH_PRECISION` | 93.71<!--claim:shortform.sdu22_ae_legal_train.high_precision.baseline.short_form.exact_precision:.2f--> &rarr; 95.06<!--claim:shortform.sdu22_ae_legal_train.high_precision.two_word.short_form.exact_precision:.2f--> | 38.76<!--claim:shortform.sdu22_ae_legal_train.high_precision.baseline.short_form.exact_recall:.2f--> &rarr; 39.40<!--claim:shortform.sdu22_ae_legal_train.high_precision.two_word.short_form.exact_recall:.2f--> | 54.84<!--claim:shortform.sdu22_ae_legal_train.high_precision.baseline.short_form.exact_f1:.2f--> &rarr; 55.71<!--claim:shortform.sdu22_ae_legal_train.high_precision.two_word.short_form.exact_f1:.2f--> | 70.43<!--claim:shortform.sdu22_ae_legal_train.high_precision.baseline.long_form.exact_f1:.2f--> &rarr; 70.43<!--claim:shortform.sdu22_ae_legal_train.high_precision.two_word.long_form.exact_f1:.2f--> |
| `GENERAL` | 93.63<!--claim:shortform.sdu22_ae_legal_train.general.baseline.short_form.exact_precision:.2f--> &rarr; 95.03<!--claim:shortform.sdu22_ae_legal_train.general.two_word.short_form.exact_precision:.2f--> | 38.83<!--claim:shortform.sdu22_ae_legal_train.general.baseline.short_form.exact_recall:.2f--> &rarr; 39.49<!--claim:shortform.sdu22_ae_legal_train.general.two_word.short_form.exact_recall:.2f--> | 54.89<!--claim:shortform.sdu22_ae_legal_train.general.baseline.short_form.exact_f1:.2f--> &rarr; 55.79<!--claim:shortform.sdu22_ae_legal_train.general.two_word.short_form.exact_f1:.2f--> | 70.42<!--claim:shortform.sdu22_ae_legal_train.general.baseline.long_form.exact_f1:.2f--> &rarr; 70.42<!--claim:shortform.sdu22_ae_legal_train.general.two_word.long_form.exact_f1:.2f--> |
| `BIOMEDICAL` | 92.70<!--claim:shortform.sdu22_ae_legal_train.biomedical.baseline.short_form.exact_precision:.2f--> &rarr; 94.08<!--claim:shortform.sdu22_ae_legal_train.biomedical.two_word.short_form.exact_precision:.2f--> | 39.01<!--claim:shortform.sdu22_ae_legal_train.biomedical.baseline.short_form.exact_recall:.2f--> &rarr; 39.67<!--claim:shortform.sdu22_ae_legal_train.biomedical.two_word.short_form.exact_recall:.2f--> | 54.91<!--claim:shortform.sdu22_ae_legal_train.biomedical.baseline.short_form.exact_f1:.2f--> &rarr; 55.80<!--claim:shortform.sdu22_ae_legal_train.biomedical.two_word.short_form.exact_f1:.2f--> | 70.26<!--claim:shortform.sdu22_ae_legal_train.biomedical.baseline.long_form.exact_f1:.2f--> &rarr; 70.26<!--claim:shortform.sdu22_ae_legal_train.biomedical.two_word.long_form.exact_f1:.2f--> |

Precision and recall both up, long-form F1 unchanged to the hundredth, on all three profiles. The
corpus can show it:
200<!--claim:shortform.sdu22_ae_legal_train.corpus.gold_short_form_spans_multi_token--> of
9,532<!--claim:shortform.sdu22_ae_legal_train.corpus.gold_short_form_spans:,--> gold short-form spans
here are multi-token, against PLOD's
0<!--claim:shortform.plod_all.corpus.gold_short_form_spans_multi_token--> of
2,869<!--claim:shortform.plod_all.corpus.short_form_spans:,-->, which is why D-032 could not decide
this on PLOD even in principle. **Nothing is shipped on the strength of this table.** Experiment nine
lost the allocation and remains held; this is the row D-047 required be saved so that the question
has an answer to be argued with rather than a corpus that was spent under it.

One corpus-capability fact belongs beside it: `balanced_trim` and `baseline` are **identical in every
recorded field** on this split at every profile, because only
43<!--claim:shortform.sdu22_ae_legal_train.corpus.gold_short_form_spans_with_bracket--> of the gold
short-form spans carry a bracket. A null result for that fix here is a fact about the corpus, exactly
as it was for PLOD.

### The verdict

**Not reverted, and the default does not move.** The objection that a feature nobody can evaluate is
a maintenance liability is answered by evaluating it, not by deleting it: where the rule fires the
cost is bounded, decomposed and reproducible from one command. On the unmined arm it is not a cost at
all. Deleting it would have been a revert justified by the same corpus that could not justify
shipping it.

**And the default still does not move, on the reason that has never changed.** The flag is off
because no uncontaminated, structurally capable corpus exists in this repository, and spending a
within-corpus tuning arm does not create one — D-047 wrote that in advance, and the result above does
not touch it. What the spend removes is the phrase "unmeasured cost", which was true and is no longer.

**What is retired is the criterion.** "MED1250 precision does not move" is not a safety property of
this rule and must not be quoted as one again. A replacement has to be evaluated on a corpus where
`legend_pairs_emitted` is greater than zero, and has to name the *increment* rather than the corpus
total, because the corpus total is dominated by predictions the flag cannot change. The worst values
in the tables above are the reference points — including
-2.18<!--claim:shortform.sdu22_ae_scientific_dev.biomedical.legend_cost.short_form.overlap.precision_delta:.2f-->
on scientific `dev` under `BIOMEDICAL`, which remains the worst move recorded anywhere for this rule.
A later run below them is a regression; a later run on a corpus that emits nothing is not a result at
all.

## The governed subsystem: its first accuracy figures

The governed half of this package is 9,647 of 26,149 source lines — re-counted for this revision with
`find src/acronymkit -name '*.py' | xargs wc -l`, because the previous figure here had gone stale —
and, until this table, carried no accuracy number at all. The justification on file was "exact by construction", which is a tautology
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

**These figures were measured before either corpus was declared, and each one says so.** The runner
asks `tools/splits.py` for the corpus's declared role and writes the answer into
`bench/results.json` as `splits_declaration`; on every governed run above that field reads
`UNDECLARED (… is not in bench/splits.toml)`. It refuses to run against a corpus declared
`role = "tuning"`. Whether the manifest has since been amended is a question for
[`bench/splits.toml`](../bench/splits.toml) itself and not for this page — but a declaration written
after the fact does not retroactively make a number blind, and **nothing above has been re-measured
under one.** Read these as measured-before-declared, and re-run before treating any of them as
held-out evidence.

**And there is a specific reason not to read them as held-out even after a re-run.** The
false-positive table two sections up decomposes this subsystem's misses by which signal produced
them. Reading a corpus's miss taxonomy is exactly the act `bench/splits.toml` records as having
contaminated MED1250 and both SDU@AAAI-22 dev splits. It happened here in the same round as the
measurement, on this page, and it should be weighed against any `contaminated = false` entry for
these two corpora rather than assumed away.

## The backronym subsystem: an accuracy number for `align`, none for `synthesize`

`BackronymGenerator` is the fifth subsystem in `docs/ARCHITECTURE.md`'s map, two public methods on
the facade, two CLI commands and a README section with worked output. It carried no external number
of any kind until the `backronym.*` runs existed, and `docs/DEFINITION-OF-DONE.md` criterion 2 —
*every shipped subsystem carries an accuracy number* — had been open on exactly that.

The round that measured it concluded the subsystem **cannot** carry an accuracy number and amended
the criterion to say so. That sentence was re-examined by a second reader with no stake in it, and
**half of it is wrong**. The subsystem's two operations are not alike, and the amendment treated
them as one thing:

| Operation | What it is asked for | Is there a correct answer? |
|---|---|---|
| `align(phrase, target)` | which word of a **real** phrase supplied which letter of a **real** short form | **Sometimes, and demonstrably.** Where the alignment constraint admits exactly one complete reading, that reading is the answer and no annotator, convention or opinion selected it. |
| `synthesize(target)` | invent a phrase spelling the target, from no source phrase at all | **No, and no annotation would create one.** Accuracy here is not unmeasured — it is undefined, because the task has no correct answer to be accurate about. |

So this section now publishes an accuracy figure for the first and refuses one for the second, and
the refusal is **permanent** rather than pending. Both halves are below, the accuracy figure ships
with the share of the corpus it reaches printed beside it, and nothing here is a quality number.

### Property, quality, and accuracy — three different questions

Forward generation has a gold standard because a corpus of real pairs records **what a human chose**:
feed the long form in, ask whether the annotator's short form comes back. Backronym *synthesis* is
handed a target word and asked to invent a phrase; there is nothing to compare the answer to.
Backronym *alignment* is a third thing, and it is the one the amendment lost sight of: it is a
**reading** task over a real pair, not an invention task, and a reading can be right or wrong.

| | What it asks | Can it be checked? |
|---|---|---|
| **Property** | Does every word start with the required letter, in order? Is the letter really there? Can the constraint be satisfied at all? Can the lexicon serve every letter? | **Yes.** A verifier that shares no code with the search recomputes it from the input. |
| **Accuracy** | Given a real pair, is the returned reading *the* reading? | **On the part of the task where one reading exists.** That is a little over half of both corpora, and the rest is bounded rather than scored. |
| **Quality** | Is the phrase meaningful? Apt for the domain? Would a person pick this reading over that one? | **No.** Every one needs a judge — a human, or a model standing in for one — and this project has neither. |

Everything in the two subsections after the next one is a property. **No property here is evidence
that this library writes good backronyms**, and the synthesis table ends with the demonstration of
why the two must not be confused.

### Where the inputs come from, and what they are not

Two corpora supply the **input distribution and nothing else**. MED1250's annotators marked
abbreviation *definitions* in MEDLINE abstracts; SDU@AAAI-21 AD's `diction.json` lists the shared
task's legal expansions per acronym. Both are real (short form, long form) pairs. **Neither
annotator was ever asked to judge an alignment**, so neither file contains a gold answer for this
task, and no figure below is scored against one.

Both are `role = "tuning"`, `contaminated = true`, and every run id carries the label. That label is
weaker than usual here for a reason worth saying rather than hiding: these are *properties, not
fitted decisions*, so no held-out split would make them more trustworthy — nothing below was tuned
on anything. What the label still buys is a reader who does not mistake the input distribution for a
blind one. No held-out budget is spent; `diction.json` is the candidate inventory, not a split.

**`generation.med1250.dictionary_backronym` is not this subsystem's number and must never be quoted
as one — including as the accuracy figure below.** It is forward generation — long form in, acronym
out — under a preset that happens to be named `DICTIONARY_BACKRONYM`. Nothing in it calls `align` or
`synthesize`. It sits beside this subsystem's runs in `bench/results.json` and is exactly the entry a
hurried reader reaches for when told the fifth subsystem has an accuracy number; the accuracy figure
is `backronym.<corpus>.accuracy.<subset>.exact_match_pct` and nothing else.

### Alignment: the ceiling is in the table, not under it

**Feasible %** is the share of pairs for which the alignment constraint admits a complete alignment
*at all*, decided by a two-pointer subsequence test with no weights and no library code. It bounds
every other column, so it is printed beside them.

| Corpus / subset | Pairs | feasible % | complete % | of feasible % | letters % | letter ceiling % | underdetermined % |
|---|---:|---:|---:|---:|---:|---:|---:|
| MED1250, all | 1,221<!--claim:backronym.med1250.alignment.all.pairs:,--> | 87.63<!--claim:backronym.med1250.alignment.all.feasible_pct:.2f--> | **86.49<!--claim:backronym.med1250.alignment.all.complete_pct:.2f-->** | 98.69<!--claim:backronym.med1250.alignment.all.complete_of_feasible_pct:.2f--> | 94.81<!--claim:backronym.med1250.alignment.all.letter_coverage_pct:.2f--> | 95.38<!--claim:backronym.med1250.alignment.all.letter_ceiling_pct:.2f--> | 37.29<!--claim:backronym.med1250.alignment.all.underdetermined_pct:.2f--> |
| MED1250, alphabetic | 1,102<!--claim:backronym.med1250.alignment.alphabetic.pairs:,--> | 91.02<!--claim:backronym.med1250.alignment.alphabetic.feasible_pct:.2f--> | 89.75<!--claim:backronym.med1250.alignment.alphabetic.complete_pct:.2f--> | 98.60<!--claim:backronym.med1250.alignment.alphabetic.complete_of_feasible_pct:.2f--> | 96.15<!--claim:backronym.med1250.alignment.alphabetic.letter_coverage_pct:.2f--> | 96.73<!--claim:backronym.med1250.alignment.alphabetic.letter_ceiling_pct:.2f--> | 38.19<!--claim:backronym.med1250.alignment.alphabetic.underdetermined_pct:.2f--> |
| MED1250, **with a digit** | 119<!--claim:backronym.med1250.alignment.with_digit.pairs:,--> | **56.30<!--claim:backronym.med1250.alignment.with_digit.feasible_pct:.2f-->** | **56.30<!--claim:backronym.med1250.alignment.with_digit.complete_pct:.2f-->** | 100.00<!--claim:backronym.med1250.alignment.with_digit.complete_of_feasible_pct:.2f--> | 85.38<!--claim:backronym.med1250.alignment.with_digit.letter_coverage_pct:.2f--> | 85.96<!--claim:backronym.med1250.alignment.with_digit.letter_ceiling_pct:.2f--> | 23.88<!--claim:backronym.med1250.alignment.with_digit.underdetermined_pct:.2f--> |
| SDU@AAAI-21 AD, all | 2,308<!--claim:backronym.sdu21_ad.alignment.all.pairs:,--> | 97.96<!--claim:backronym.sdu21_ad.alignment.all.feasible_pct:.2f--> | **97.96<!--claim:backronym.sdu21_ad.alignment.all.complete_pct:.2f-->** | 100.00<!--claim:backronym.sdu21_ad.alignment.all.complete_of_feasible_pct:.2f--> | 99.19<!--claim:backronym.sdu21_ad.alignment.all.letter_coverage_pct:.2f--> | 99.19<!--claim:backronym.sdu21_ad.alignment.all.letter_ceiling_pct:.2f--> | 42.50<!--claim:backronym.sdu21_ad.alignment.all.underdetermined_pct:.2f--> |
| SDU@AAAI-21 AD, **with a digit** | 0<!--claim:backronym.sdu21_ad.alignment.with_digit.pairs:,--> | — | — | — | — | — | — |

The worst row is **MED1250 / with a digit** and it is in the table rather than in a footnote:
56.30<!--claim:backronym.med1250.alignment.with_digit.complete_pct:.2f--> % against a pooled
86.49<!--claim:backronym.med1250.alignment.all.complete_pct:.2f--> %, over
119<!--claim:backronym.med1250.alignment.with_digit.pairs:,--> pairs. The SDU-21 digit row is empty
and that is a *counted* zero — `diction.json` contains
0<!--claim:backronym.sdu21_ad.alignment.with_digit.pairs:,--> targets carrying a digit, so that
corpus is structurally incapable of showing this failure and cannot be cited against it.

**`of feasible %` is not an achievement score, and reading it as one would be the tautology this
measurement is built to avoid.** Coverage is not the aligner's objective: leaving a letter unmapped
costs `unmapped_penalty`, and stepping over a critical token costs `delta`, which ships four times
larger — so the objective sometimes *prefers* an incomplete alignment. Every feasible-but-incomplete
pair is therefore re-scored against the oracle's complete path using the library's own `Scorer`, and
all 14<!--claim:backronym.med1250.alignment.all.incomplete_feasible_n:,--> of them on MED1250 come
back as the objective's own preference, with
0<!--claim:backronym.med1250.alignment.all.search_shortfall_n:,--> search shortfalls.
`bispectral index` / `BIS` is the shape: the complete reading takes `b`, `i`, `s` from inside
`bispectral` and abandons `index`; the aligner covers both words and drops a letter, and scores
higher for it.

### Why the ceiling is where it is

Each infeasible pair is attributed to exactly one cause, first match wins, so the counts partition.

| Cause | MED1250 | SDU-21 AD | What it looks like |
|---|---:|---:|---|
| Donor token not eligible | 50<!--claim:backronym.med1250.alignment.all.infeasible_by_cause.token_ineligible:,--> | 43<!--claim:backronym.sdu21_ad.alignment.all.infeasible_by_cause.token_ineligible:,--> | `POS` ← *part of speech*; `vitD` ← *vitamin D*. The stop-word and one-character filters removed the word the letter needed. |
| A digit occurs nowhere | 40<!--claim:backronym.med1250.alignment.all.infeasible_by_cause.digit_absent:,--> | 0<!--claim:backronym.sdu21_ad.alignment.all.infeasible_by_cause.digit_absent:,--> | `T3` ← *triiodothyronine* |
| A character occurs nowhere | 30<!--claim:backronym.med1250.alignment.all.infeasible_by_cause.character_absent:,--> | 4<!--claim:backronym.sdu21_ad.alignment.all.infeasible_by_cause.character_absent:,--> | `DPH` ← *phenytoin* |
| Present, but out of order | 31<!--claim:backronym.med1250.alignment.all.infeasible_by_cause.out_of_order:,--> | 0<!--claim:backronym.sdu21_ad.alignment.all.infeasible_by_cause.out_of_order:,--> | `FasL ICD` ← *intracellular FasL domain* |

The largest single cause on **both** corpora is the eligibility filter, not the data. That is a
measured fact about the interaction between the stop-word policy and the alignment constraint. It is
recorded here and nothing has been changed in response to it: one change, one measurement.

**A caveat that cuts against the feasibility figures themselves.** MED1250's annotation guide
excludes from the gold standard both pairs with no matching character (`//!syn`) and pairs whose
characters match out of order (`//!ord`). So the population these figures are taken over is
*already filtered toward alignable pairs*, and the feasibility column is a ceiling on a pre-selected
sample rather than on arbitrary prose. The residue is what survives that filter and fails anyway —
which is why the cause table above is the informative half.

### The guards, and their firing counts

A guard reported without the number of times it could have fired tests the gate rather than the
thing — the defect D-046 records. So both are printed with their denominators.

| Guard | MED1250 | SDU-21 AD | Fired over |
|---|---:|---:|---|
| Constraint satisfaction — order, offsets, letter really present, donor really eligible, `coverage` arithmetic | 100.00<!--claim:backronym.med1250.alignment.all.validity_pct:.2f--> % | 100.00<!--claim:backronym.sdu21_ad.alignment.all.validity_pct:.2f--> % | 4,815<!--claim:backronym.med1250.alignment.all.alignments_verified:,--> and 10,237<!--claim:backronym.sdu21_ad.alignment.all.alignments_verified:,--> alignments |
| Oracle agreement — infeasible per the oracle, complete per `align` | 0<!--claim:backronym.med1250.alignment.all.oracle_contradictions_n:,--> contradictions | 0<!--claim:backronym.sdu21_ad.alignment.all.oracle_contradictions_n:,--> contradictions | every pair |
| Search optimality | 0<!--claim:backronym.med1250.alignment.all.search_shortfall_n:,--> shortfall | **fires zero times** | 14<!--claim:backronym.med1250.alignment.all.incomplete_feasible_n:,--> pairs on MED1250, 0<!--claim:backronym.sdu21_ad.alignment.all.incomplete_feasible_n:,--> on SDU-21 |

**A passing guard is not evidence of a good backronym.** It is evidence that the payload says what
it means and that the search reaches the states it should. The third guard adjudicates nothing at
all on SDU-21 AD, and the runner prints that in place of a percentage rather than reporting a
zero-denominator rate as if it were a measurement.

### The share of the task no property can settle

`TAI` ← *timed artificial insemination* admits *timed artificial artificial* and *artificial
insemination insemination* and the obvious human reading, and the constraint permits all three. The
componentwise-earliest and componentwise-latest alignments are the extremes of the feasible set, so
they differ exactly when more than one distinct reading exists:

| Corpus | Feasible pairs | Pairs with more than one reading | Share |
|---|---:|---:|---:|
| MED1250 | 1,070<!--claim:backronym.med1250.alignment.all.feasible_n:,--> | 399<!--claim:backronym.med1250.alignment.all.underdetermined_n:,--> | 37.29<!--claim:backronym.med1250.alignment.all.underdetermined_pct:.2f--> % |
| SDU-21 AD | 2,261<!--claim:backronym.sdu21_ad.alignment.all.feasible_n:,--> | 961<!--claim:backronym.sdu21_ad.alignment.all.underdetermined_n:,--> | 42.50<!--claim:backronym.sdu21_ad.alignment.all.underdetermined_pct:.2f--> % |

**This is the judge-shaped hole, counted.** On roughly four pairs in ten the constraint does not
determine the answer, the objective picks one, and no property in this project can say whether it
picked the reading a person would have. That is the share of the alignment task an accuracy number
would have had to adjudicate, and it is why one is not offered.

**Both counts are lower bounds, and the direction is stated rather than assumed.** Two alignments are
compared on the *words* they read out, not on the token indices they use, so a pair whose two extreme
alignments happen to name the same words is counted as determined even if some intermediate
alignment names different ones. Comparing indices instead moves the SDU-21 count by one. The
conservative definition is the published one, because the visible reading is what a caller sees.

**That hazard is real and not only theoretical, and here is an instance of it.** The shipped aligner
returns the intermediate reading on a pair whose two extremes agree:

```console
$ python -c "align('AA', tokenize('alpha acid alpha'))"    -- command output
  earliest reading    alpha alpha      the two 'a's inside one word
  latest reading      alpha alpha      the same two words, the other occurrence
  align returns       alpha acid       two word initials, and it outscores both
```

So *determined at the word level* is an empirical claim rather than a structural one. The accuracy
section below carries both the counter that would catch it on real data and the subset on which the
claim is structural.

### Accuracy: scored against the reading the constraint settles by itself

**The gold is the constraint's own uniqueness, and nobody chose it.** The componentwise-earliest and
componentwise-latest complete alignments bound the feasible set, so when they read out the same words
*every* complete alignment reads out those words. Such a pair has exactly one reading. No annotator
selected it, this project did not write it down, and no convention was consulted — it is what the
constraint leaves. `align`'s top candidate either is that reading or is not, and that is an accuracy
question with an answer.

This is the figure `docs/DEFINITION-OF-DONE.md` criterion 2 asks for, for one of the subsystem's two
operations. It is **not** `generation.med1250.dictionary_backronym`, which is forward generation
under a preset that happens to be named that way and calls neither `align` nor `synthesize`.

| Corpus | Pairs | Decidable pairs | Share of corpus | **Accuracy** | Sound-gold variant |
|---|---:|---:|---:|---:|---:|
| MED1250 | 1,221<!--claim:backronym.med1250.accuracy.all.pairs:,--> | 671<!--claim:backronym.med1250.accuracy.all.decidable_n:,--> | 54.95<!--claim:backronym.med1250.accuracy.all.decidable_pct_of_pairs:.2f--> % | **98.66<!--claim:backronym.med1250.accuracy.all.exact_match_pct:.2f--> %** | 98.11<!--claim:backronym.med1250.accuracy.all.position_unique_exact_pct:.2f--> % over 370<!--claim:backronym.med1250.accuracy.all.position_unique_n:,--> |
| SDU@AAAI-21 AD | 2,308<!--claim:backronym.sdu21_ad.accuracy.all.pairs:,--> | 1,300<!--claim:backronym.sdu21_ad.accuracy.all.decidable_n:,--> | 56.33<!--claim:backronym.sdu21_ad.accuracy.all.decidable_pct_of_pairs:.2f--> % | **100.00<!--claim:backronym.sdu21_ad.accuracy.all.exact_match_pct:.2f--> %** | 100.00<!--claim:backronym.sdu21_ad.accuracy.all.position_unique_exact_pct:.2f--> % over 801<!--claim:backronym.sdu21_ad.accuracy.all.position_unique_n:,--> |

The last column is the same measurement restricted to pairs whose earliest and latest readings agree
on `(token, offset)` for **every** letter, which makes the complete alignment literally unique and
the gold sound by construction rather than empirically. It reaches roughly half as many pairs, and it
moves the figure by less than a point on MED1250 and not at all on SDU-21. That is why it is printed:
**the choice between the two golds does not drive the number.**

#### The accuracy figure covers about half the corpus, and the rest is bounded rather than scored

An accuracy over the decidable subset says nothing about the pairs the constraint does not settle.
Reporting only the first would be the flattering half. So the same run publishes a bound over **every
feasible pair**: the lower end counts each undecidable pair wrong, the upper end counts it right
unless the initialism convention below contradicts it.

| Corpus | Feasible pairs | Accuracy, lower | Accuracy, upper | Interval width |
|---|---:|---:|---:|---:|
| MED1250 | 1,070<!--claim:backronym.med1250.accuracy.all.feasible_n:,--> | 61.87<!--claim:backronym.med1250.accuracy.all.accuracy_lower_pct:.2f--> % | 99.16<!--claim:backronym.med1250.accuracy.all.accuracy_upper_pct:.2f--> % | 37.29<!--claim:backronym.med1250.accuracy.all.accuracy_interval_width_pct:.2f--> |
| SDU-21 AD | 2,261<!--claim:backronym.sdu21_ad.accuracy.all.feasible_n:,--> | 57.50<!--claim:backronym.sdu21_ad.accuracy.all.accuracy_lower_pct:.2f--> % | 100.00<!--claim:backronym.sdu21_ad.accuracy.all.accuracy_upper_pct:.2f--> % | 42.50<!--claim:backronym.sdu21_ad.accuracy.all.accuracy_interval_width_pct:.2f--> |

**The interval width is the underdetermined share, in accuracy units.** It is the same quantity the
section above reports as a share of pairs, and stating it this way is what makes its size legible: an
accuracy figure whose uncertainty spans nearly forty points is computable and is not, on its own, an
answer to *does this subsystem work*. Infeasible pairs —
151<!--claim:backronym.med1250.accuracy.all.infeasible_n:,--> on MED1250 and
47<!--claim:backronym.sdu21_ad.accuracy.all.infeasible_n:,--> on SDU-21 — are outside the interval
entirely, because a pair with no complete reading has no right answer to return either.

#### The ladder: how much each rung adjudicates, and what it assumes

| Rung | What it assumes | MED1250 | SDU-21 AD |
|---|---|---:|---:|
| 1 — the constraint admits one reading | nothing | 671<!--claim:backronym.med1250.accuracy.all.decidable_n:,--> pairs | 1,300<!--claim:backronym.sdu21_ad.accuracy.all.decidable_n:,--> pairs |
| 2 — exactly one all-initials reading exists | that a reader takes it | 196<!--claim:backronym.med1250.accuracy.all.convention_applicable_n:,--> more | 930<!--claim:backronym.sdu21_ad.accuracy.all.convention_applicable_n:,--> more |
| 3 — no gold of any kind | — | 203<!--claim:backronym.med1250.accuracy.all.unadjudicable_n:,--> | 31<!--claim:backronym.sdu21_ad.accuracy.all.unadjudicable_n:,--> |

**Rung 2 is a weak gold on purpose and it is reported apart from the accuracy figure.** Word-initial
mappings are what the aligner's own objective rewards, so agreement there is partly a restatement of
the objective rather than an independent check — and the agreement is total:
196<!--claim:backronym.med1250.accuracy.all.convention_agreement_n:,--> of
196<!--claim:backronym.med1250.accuracy.all.convention_applicable_n:,--> and
930<!--claim:backronym.sdu21_ad.accuracy.all.convention_agreement_n:,--> of
930<!--claim:backronym.sdu21_ad.accuracy.all.convention_applicable_n:,-->, with
0<!--claim:backronym.med1250.accuracy.all.convention_conflict_n:,--> and
0<!--claim:backronym.sdu21_ad.accuracy.all.convention_conflict_n:,--> conflicts. Adopting it moves
MED1250 to 98.96<!--claim:backronym.med1250.accuracy.all.initialism_conditional_accuracy_pct:.2f--> %
over 71.01<!--claim:backronym.med1250.accuracy.all.initialism_conditional_coverage_pct_of_pairs:.2f-->
% of the corpus and SDU-21 to
100.00<!--claim:backronym.sdu21_ad.accuracy.all.initialism_conditional_accuracy_pct:.2f--> % over
96.62<!--claim:backronym.sdu21_ad.accuracy.all.initialism_conditional_coverage_pct_of_pairs:.2f--> %.
Those two figures are named `initialism_conditional_accuracy_pct` in `bench/results.json` so the
assumption travels with them, and **they are not the accuracy figure**.

**Rung 3 is the honest size of the judge-shaped hole, and it is smaller than the underdetermined
share suggests.** Only 18.97<!--claim:backronym.med1250.accuracy.all.unadjudicable_pct_of_feasible:.2f-->
% of MED1250's feasible pairs and
1.37<!--claim:backronym.sdu21_ad.accuracy.all.unadjudicable_pct_of_feasible:.2f--> % of SDU-21's are
underdetermined *and* admit no single all-initials reading. The rest of the underdetermined mass is
underdetermined only in ways no reader would hesitate over — `TAI` ← *timed artificial insemination*
is in it, and the constraint's permission for *timed artificial artificial* is a fact about the
constraint rather than a question about the answer.

#### The guards on the gold, with the number of times each executed

| Guard | MED1250 | SDU-21 AD | Executed over |
|---|---:|---:|---|
| Returned a complete alignment naming words the unique reading does not | 0<!--claim:backronym.med1250.accuracy.all.returned_other_words_n:,--> | 0<!--claim:backronym.sdu21_ad.accuracy.all.returned_other_words_n:,--> | every decidable pair — 671<!--claim:backronym.med1250.accuracy.all.decidable_n:,--> and 1,300<!--claim:backronym.sdu21_ad.accuracy.all.decidable_n:,--> |
| The uniqueness gold and the all-initials gold disagree on a pair both reach | 0<!--claim:backronym.med1250.accuracy.all.convention_cross_check_conflict_n:,--> | 0<!--claim:backronym.sdu21_ad.accuracy.all.convention_cross_check_conflict_n:,--> | 250<!--claim:backronym.med1250.accuracy.all.convention_cross_check_n:,--> and 1,255<!--claim:backronym.sdu21_ad.accuracy.all.convention_cross_check_n:,--> pairs |

Both nulls are reported with the count of executions rather than as bare zeroes, and the first one is
the one that matters: it is the guard that would detect the `alpha acid alpha` unsoundness above on
real input, it compared every decidable pair rather than only the misses, and it never fired. That is
evidence the word-level gold holds on these two corpora — **not** evidence that it holds in general,
which the constructed pair already refutes.

#### The misses are all of one kind, and they are rows the alignment arm calls a design trade

MED1250's 9<!--claim:backronym.med1250.accuracy.all.returned_incomplete_n:,--> misses are every one
the same shape: the pair has exactly one complete reading, and the aligner returned an **incomplete**
alignment instead, spending letters to cover more words.

```console
$ python bench/run_backronym.py --arm accuracy      -- command output, abridged
  'BIS'    <- 'bispectral index'
      the only reading : bispectral bispectral bispectral
      returned         : bispectral index
  'log P'  <- 'log n-octanol/water partition coefficients'
      the only reading : log log log partition
      returned         : log n-octanol/water partition
  'MuSK+'  <- 'anti-MuSK antibodies'
      the only reading : anti-MuSK anti-MuSK anti-MuSK anti-MuSK
      returned         : anti-MuSK antibodies
```

**Those rows are already in this document, wearing the opposite verdict.** The alignment section
above re-scores every feasible-but-incomplete pair against the oracle's complete path *using the
library's own `Scorer`*, finds all
14<!--claim:backronym.med1250.alignment.all.incomplete_feasible_n:,--> of them objective-preferred
with 0<!--claim:backronym.med1250.alignment.all.search_shortfall_n:,--> search shortfalls, and
concludes there is no defect. Nine of those fourteen are pairs whose correct reading is unique and
was not returned. Both readings are true of the same rows and they answer different questions: that
one asks whether the search reached the state its objective ranks highest, this one asks whether the
answer is right. **A measurement that adjudicates an answer with the objective that produced it
cannot report a wrong answer**, which is the tautology the runner's own docstring says it exists to
avoid, and it had reappeared one section later.

All nine were read by hand for this section. Eight are unambiguous — `BIS` really is *BIspectral*,
`log P` really takes `L`, `O`, `G` from *log*. The ninth, `pPC` ← *phosphatidylcholine plasmalogen*,
is a pair whose likely human reading is out of order and therefore inexpressible under the constraint
at all; the gold there is the only in-order complete reading, which is the right answer to the
question this subsystem is asked and possibly not the one a chemist would give.

#### How this accuracy figure fails

**The label `tuning, contaminated` bites harder here than it does on the properties.** The
properties section argues that a held-out split would not make a *property* more trustworthy, because
nothing was fitted. **That argument does not transfer to an accuracy number.** The aligner's weights
were set against this project's own corpora, MED1250 among them, and an accuracy figure is exactly the
kind of quantity a blind split exists to protect. No blind split for this task exists, the reserved
arms are earmarked for other questions, and this figure therefore inherits the weakest label on the
page while being the figure that most needs a strong one.

**The gold is this library's constraint, restated.** A reading is "the" reading because the alignment
constraint admits one, and the constraint is `acronymkit`'s: letters in non-decreasing token order,
offsets strictly increasing inside a shared token, ineligible tokens donating nothing. A reader who
rejects the constraint rejects the gold. The `pPC` miss is the visible edge of that: its likely human
reading is out of order and the constraint cannot express it at all, so the gold there is the best
in-order reading rather than the chemist's.

**The eligibility filter is inside the gold, not outside it.** `token_ineligible` is the largest
single cause of infeasibility on both corpora, and the same filter decides which tokens the gold may
draw from. Widening it would move the feasible set, the decidable set and the accuracy figure
together, which is why it is a lever nobody has pulled and why pulling it invalidates this table.

**`exact_match_pct` reads 100.00<!--claim:backronym.sdu21_ad.accuracy.all.exact_match_pct:.2f--> % on
one corpus, which is the shape of a metric that cannot fail.** It can. It reports
9<!--claim:backronym.med1250.accuracy.all.returned_incomplete_n:,--> failures on the other corpus; it
reads zero on a constructed pair where the aligner returns a *complete* alignment naming other words,
so it is not `complete_pct` under a new name; and replacing the top candidate with the second-best one
takes SDU-21 from 100.00<!--claim:backronym.sdu21_ad.accuracy.all.exact_match_pct:.2f--> % to nothing.

**Nothing in CI runs this arm**, so these four figures stale exactly the way every other gated figure
in this repository does, and `--save` now prints the fields it is about to overwrite rather than
replacing them silently.

#### What was rejected, and why, so it is not re-proposed

The evaluation was designed before the runner was extended, and four candidate metrics were rejected
in the design rather than after building them:

* **A hand-written reference set of good alignments.** Scoring against a few dozen alignments written
  here is scoring against this project's own opinion. Refused for the reason `tools/build_gold_corpus.py`'s
  pilot was refused registration: a single annotator adjudicating the system they wrote is not a gold.
* **A model judge.** Needs a network, and the reopening condition this project set for itself requires
  the judge's agreement against humans to be measured *before* any figure it produces is quoted.
  Neither is available offline.
* **A fluency or plausibility proxy** — character-model score, word frequency, perplexity. Each scores
  the expansion with a second model and calls the result quality. That is an invented number wearing a
  metric's coat.
* **Round-tripping synthesis against the corpus** — asking whether `synthesize("AML")` returns *acute
  myeloid leukaemia*. Well defined, and it would read zero on every row, because the arm draws from a
  general English lexicon with no domain and no source phrase. A figure that is zero by construction
  measures the harness rather than the subsystem, and publishing it would look like evidence.
* **Ranking the true expansion against distractors.** Well defined, the gold is real, no judge is
  needed — and the number is a function of a distractor policy nothing outside this repository
  constrains. Rejected as a headline for that reason. It is the most defensible thing left if this arm
  is ever pushed further.

### Synthesis: full coverage, and output nobody would ship

Synthesis draws one word per letter from the shipped English lexicon.

| Corpus / subset | Targets | produced % | complete % | letters % | mean word length |
|---|---:|---:|---:|---:|---:|
| MED1250, all | 1,010<!--claim:backronym.med1250.synthesis.all.targets:,--> | 100.00<!--claim:backronym.med1250.synthesis.all.produced_pct:.2f--> | **89.70<!--claim:backronym.med1250.synthesis.all.complete_pct:.2f-->** | 96.34<!--claim:backronym.med1250.synthesis.all.letter_coverage_pct:.2f--> | 3.00<!--claim:backronym.med1250.synthesis.all.word_length_mean:.2f--> |
| MED1250, alphabetic | 906<!--claim:backronym.med1250.synthesis.alphabetic.targets:,--> | 100.00<!--claim:backronym.med1250.synthesis.alphabetic.produced_pct:.2f--> | 100.00<!--claim:backronym.med1250.synthesis.alphabetic.complete_pct:.2f--> | 100.00<!--claim:backronym.med1250.synthesis.alphabetic.letter_coverage_pct:.2f--> | 3.00<!--claim:backronym.med1250.synthesis.alphabetic.word_length_mean:.2f--> |
| MED1250, **with a digit** | 104<!--claim:backronym.med1250.synthesis.with_digit.targets:,--> | 100.00<!--claim:backronym.med1250.synthesis.with_digit.produced_pct:.2f--> | **0.00<!--claim:backronym.med1250.synthesis.with_digit.complete_pct:.2f-->** | 72.36<!--claim:backronym.med1250.synthesis.with_digit.letter_coverage_pct:.2f--> | 3.00<!--claim:backronym.med1250.synthesis.with_digit.word_length_mean:.2f--> |
| SDU-21 AD, all | 732<!--claim:backronym.sdu21_ad.synthesis.all.targets:,--> | 100.00<!--claim:backronym.sdu21_ad.synthesis.all.produced_pct:.2f--> | **100.00<!--claim:backronym.sdu21_ad.synthesis.all.complete_pct:.2f-->** | 100.00<!--claim:backronym.sdu21_ad.synthesis.all.letter_coverage_pct:.2f--> | 3.00<!--claim:backronym.sdu21_ad.synthesis.all.word_length_mean:.2f--> |

The worst row is again the digit bucket, at
0.00<!--claim:backronym.med1250.synthesis.with_digit.complete_pct:.2f--> % over
104<!--claim:backronym.med1250.synthesis.with_digit.targets:,--> targets, and the decomposition is
total: **every** unserved character across both corpora is a digit, and no letter of the alphabet
fails once. So the alphabetic row is a property of the shipped lexicon crossed with the alphabet,
and the only informative figure in the coverage column is the digit share of real short forms —
which is a fact about the corpus, not about the generator.

Two further figures are reported and are **near-vacuous by construction**, and they are printed
anyway because an unchecked guard is not a guard: every emitted word begins with its letter
(100.00<!--claim:backronym.med1250.synthesis.all.initial_constraint_pct:.2f--> % over
3,450<!--claim:backronym.med1250.synthesis.all.words_checked:,--> words), and every alternative is
distinct (100.00<!--claim:backronym.med1250.synthesis.all.distinct_alternatives_pct:.2f--> %). Both
would fire if the construction broke. Neither is an evaluation.

**And here is why none of that is a quality number.** The mean word length is
3.00<!--claim:backronym.med1250.synthesis.all.word_length_mean:.2f--> characters on every row of
the table, because the ranking key prefers 3–12 characters and then shorter before longer, so it
settles on the alphabetically-first three-letter word for each letter — and the shipped lexicon's
three-letter band is the obscure tail of a word list graded for *recognisability as a word*, which
is what D-004 cut it for, not for aptness as an expansion:

```console
$ python bench/run_backronym.py --examples
  [sdu21_ad] 'ABC' -> 'aah baa cab'
  [sdu21_ad] 'ACE' -> 'aah cab ear'
  [med1250]  '1D'  -> 'dab'
```

Every letter served, every word a real dictionary word, every initial correct, every alternative
distinct — and the output is unusable. **That row scores full marks on every property this project
can check.** No metric here distinguishes it from a good backronym, which is the case for the
scoping below rather than an argument against the measurement.

### What this does to the definition of done, and the amendment it replaces

Criterion 2 read *every shipped subsystem carries an accuracy number*. It was amended once, to say
the fifth subsystem **cannot** carry one. That amendment is adjudicated here, by a reader with no
stake in the round that wrote it, and the verdict is that **it was a correct refusal supported by a
false reason, and the false reason was doing the work**.

> **The amendment as written.** *Four of five subsystems carry an accuracy number. The fifth —
> backronym synthesis and alignment — carries constraint-satisfaction, coverage and underdetermination
> figures, and cannot carry an accuracy number, because scoring a backronym requires a judgement no
> corpus records and this project has no judge.*

Three things are wrong with it, and all three are checkable against this page:

1. **It treats two operations as one subsystem.** `synthesize` invents; `align` reads. The first has
   no correct answer; the second has one whenever the constraint admits a single complete reading.
2. **The word *cannot* is false for `align`,** and the machinery that refutes it was already in the
   runner the amendment shipped with. `earliest_fit` and `latest_fit` were used to *count* the pairs
   the constraint does not settle; the pairs it does settle were sitting in the complement, unscored.
3. **Its own supporting figure was adjudicated by the objective under test.** The fourteen
   feasible-but-incomplete MED1250 pairs were re-scored with the library's own `Scorer` and reported
   as the objective's preference with no shortfalls. Nine of them are pairs with one correct reading
   that was not returned.

What survives is the *refusal*, and it survives for a narrower reason than the one given. The
accuracy figure that now exists reaches
54.95<!--claim:backronym.med1250.accuracy.all.decidable_pct_of_pairs:.2f--> % and
56.33<!--claim:backronym.sdu21_ad.accuracy.all.decidable_pct_of_pairs:.2f--> % of the two corpora,
its bound over all feasible pairs is nearly forty points wide on MED1250, and none of it touches
`synthesize` at all. So criterion 2 is **not** met in its original sense, and the correct scoping is
the one stated in `docs/DEFINITION-OF-DONE.md`: an accuracy number for the alignment half, with its
coverage published beside it, and a **permanently unmeetable** verdict for the synthesis half.

Inventing a quality number would still have been worse than the open verdict, and so would quoting
`generation.med1250.dictionary_backronym` as the missing figure — that run is forward generation
under a preset that happens to be named after this subsystem, it calls neither `align` nor
`synthesize`, and it is the trap sitting next to this gap in `bench/results.json`. It is not the
accuracy figure above either, and that scoping has now survived being checked twice and nearly
"corrected" into counting once.

**What would reopen the original criterion for the alignment half.** Nothing short of a gold that
covers the undecidable pairs: a published set of phrase, target and a human's judgement that the
alignment is the intended one, or a judge this project is willing to defend, with its agreement
against humans measured before any figure it produces is quoted. **For the synthesis half nothing
reopens it**, because a target word with no source phrase has no correct expansion for any gold to
record.

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

**No backronym *quality* number, and there is not going to be one — but there is an accuracy
number for `align`, and it covers about half of each corpus.** The backronym section above reports
constraint satisfaction, feasibility, coverage and underdetermination, all of which are *properties*;
it also reports an accuracy figure scored against the reading the alignment constraint settles by
itself, on the pairs where it settles one. Nothing in this project can say whether a backronym is any
*good* — that needs a judge and no corpus records the judgement — and `synthesize` has no accuracy
number of any kind, because a target word with no source phrase has no correct expansion. This bullet
has now been wrong twice in the direction of claiming less than the tree supports: it once read
"backronym alignment has no external evaluation at all", retired when `backronym.*` existed, and it
then read "no backronym accuracy number, and there is not going to be one", retired when
`backronym.*.accuracy` existed. Both are kept here rather than deleted, and the surviving half —
quality — is what still stands.

**The generation presets are pinned against a 16-phrase canonical corpus** (`tools/tune_presets.py`),
which is a regression guard rather than an evaluation, and the file says so itself.

**No blind split anywhere.** This bullet used to read "extraction only", and that stopped being true
three rounds ago: generation is scored on the MED1250 pairs read backwards, disambiguation on
SDU@AAAI-21 AD, the governed segmenter on publisher-authored captions, and the backronym subsystem
on two tuning corpora that supply inputs and no gold. What none of those share is a blind split —
every one of them is a tuning or undeclared corpus, which is the sentence this bullet should have
been saying instead.

## Adding a corpus

1. Register it in `tools/fetch_data.py` with its licence, checksum and whether it may be vendored.
2. Add a reader to `bench/corpora.py` returning `GoldDocument` objects.
3. Run `python bench/run_extraction.py --corpus <name>`.

The scorer never learns which corpus it is looking at, so a new corpus is a reader, not a new
evaluation.
