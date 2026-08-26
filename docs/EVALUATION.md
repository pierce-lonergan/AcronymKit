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
python bench/run_genre.py --fetch                         # 2,000 pinned PMC OA articles into data/
python bench/run_genre.py --save --interpreter /path/to/python3.12   # genre against provenance

python bench/run_scorer_differential.py --fetch            # 1.6 MB of Ab3P's own output, once
python bench/run_scorer_differential.py --save             # the extraction differential

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

| `run_genre.py` | extraction profile | **all three** | it imports `bench/run_monoculture.py`'s `PROFILES` and loops over it, and adds no proposer of its own — which `tests/test_genre.py` asserts rather than the runner claiming it |

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
  table. Whether the harness *matches Ab3P's own published evaluation* is **unestablished**, and it
  is standing unknown `U-1` in
  [docs/DEFINITION-OF-DONE.md](DEFINITION-OF-DONE.md#standing-unknowns),
  where until this round it was promised rather than written: that section did not exist, and this
  sentence had been pointing at it for a round. Closing it needs the paper's figures read from the
  paper and cited with the date somebody read them, which is one afternoon nobody has spent.

  **The hole the withdrawal left, named — because a retraction that names no hole reads as a fix.**
  With that sentence gone, **nothing in this repository argues that the extraction reader and scorer
  are correct rather than merely self-consistent.** Every row in the table above is produced by this
  harness, which is what makes the rows comparable to each other and is exactly why no arrangement
  of them can adjudicate the harness. The `pyab3p` row is the closest thing to an outside check and
  it is not one: it establishes that the reference implementation runs here and wins here, under our
  reader and our scorer, which is the proposition in question. Under the governance positioning
  ([docs/POSITIONING.md](POSITIONING.md)) extraction is a supporting number, so this is **not
  urgent** — it is a hole, not an emergency. Leaving it unnamed is how a withdrawn argument quietly
  becomes an argument nobody needed.

  **NARROWED, NOT CLOSED, AND THE DIFFERENCE IS THE WHOLE OF THE NEXT SECTION.** A differential now
  ships — [below](#the-differential-that-replaced-the-withdrawn-argument-and-the-half-of-the-hole-it-does-not-reach).
  It adjudicates the **reader** against an artefact this project did not produce and cannot
  influence. It does **not** adjudicate the scorer against anything external, because no external
  scorer for this task exists to adjudicate it against, and that was measured rather than assumed.
  The sentence *"nothing in this repository argues that the extraction reader and scorer are correct
  rather than merely self-consistent"* is now false of the reader and still true of the scorer.

  **And the same shape is still live further down this page.** `tools/check_external.py` — a gate
  written in the round that wrote this paragraph, because nothing in the repository could see an
  appeal to somebody else's numbers at all — fires on the disambiguation section's own
  harness-validation sentence, for the same reason: it rests on a shared task's own baseline scores,
  and no date anybody read them on is recorded anywhere in this tree. It is held in that tool's
  `UNCITED_LEDGER` with a stated disposition rather than silently exempted, and the disposition is
  that it is either cited with a real read date or withdrawn the way this one was.
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

### The differential that replaced the withdrawn argument, and the half of the hole it does not reach

The withdrawn sentence left the harness **correct by assertion**. This section is what replaced it.
Runner: `bench/run_scorer_differential.py`. Run ids: `differential.med1250.*`. Read the last
subsection first if you are only going to read one.

**Two of the five arms do not run without `--interpreter`, and no CI job supplies one.** `pyab3p`
publishes no wheel past CPython 3.12, so the prediction-level comparison and the mutation evidence
below were taken on a developer machine — CPython
3.12.13, recorded in the run entry as `harness_interpreter_version`, under
`pyab3p` 0.1.1 — and **not** in the environment the gates run in. R11 asks for a demonstration *in
situ*; this is a demonstration *somewhere*, which is weaker, and saying so is cheaper than the
alternative. The offline arms — the scorer agreement, the ceiling, the specification axes, and the
reproduction of `extraction.med1250.pyab3p` from the stored reference output — need no interpreter
and are pinned by `tests/test_scorer_differential.py`, which does run in CI.

#### There is no reference scorer. That is a measurement, not a shrug

The obvious substitute for an appeal to a paper is to run **the task's own scorer** against ours on
the same predictions. It does not exist, and here is what was actually opened to establish that:

- **`pyab3p` 0.1.1**, installed under CPython 3.12. Its wheel
  holds one compiled extension and a `word_data` directory. Its public surface is
  2<!--claim:differential.med1250.reference_output.pyab3p_public_names:,--> names — `Ab3p` and
  `AbbrOut` — and `Ab3p` carries
  1<!--claim:differential.med1250.reference_output.pyab3p_public_methods_on_ab3p:,--> method,
  `get_abbrs`. Evaluation entry points:
  0<!--claim:differential.med1250.reference_output.pyab3p_scoring_entry_points:,-->.
- **Ab3P upstream**, at the commit `tools/fetch_data.py` already pins for `MED1250_labeled`. The
  `Makefile` has 7<!--claim:differential.med1250.reference_output.ab3p_makefile_recipe_targets:,-->
  named targets carrying a recipe, of which
  0<!--claim:differential.med1250.reference_output.ab3p_makefile_scoring_targets:,--> compute a
  precision, a recall or an F-score. Its `test` target is
  `./identify_abbr MED1250_unlabeled | diff identify_abbr-out -` — a **reproduction** check against
  a stored output file. No scoring program is distributed with Ab3P at all.
- **The two shared-task scorers already in this tree**,
  2<!--claim:differential.med1250.reference_output.shared_task_scorers_in_tree:,--> of them, of which
  0<!--claim:differential.med1250.reference_output.shared_task_scorers_expressing_pair_extraction:,-->
  can express this task. `data/sdu21_ad_scorer.py` aligns one gold label per instance by id, which
  is classification. `data/sdu22_ae_scorer.py` scores token-index spans and never pairs a short form
  with a long form — and MED1250's gold carries no offsets anywhere in the file (D-048), so there is
  nothing to hand it.

**The premise this section was commissioned on is false, and it is worth stating because it is the
premise anybody would start from.** MED1250 does not ship with Ab3P's evaluation *conventions*. It
ships beside Ab3P's evaluation *outputs*, which is a different thing and — for one half of the
harness — a better one.

#### What Ab3P does ship: its own predictions, and this harness reproduces them exactly

`identify_abbr-out` is 1.6 MB of the NLM's own run of Ab3P over MED1250, checked in at the same
commit as the gold. **Never read by this repository before this round**, which is checkable rather
than asserted: `git grep identify_abbr` and `git grep MED1250_unlabeled` at the commit preceding this
work return nothing anywhere in the tree, `tools/fetch_data.py` included. Fetched by the runner,
pinned by SHA-256, parsed with the same bare-PubMed-ID record rule `bench/corpora.read_med1250` uses,
and **fetch-only on the MED1250 precedent** — not committed here and not vendored into the wheel.
Public domain (United States Government Work), the same terms `tools/fetch_data.py` already records
for the gold, carried in the run entry so the terms are findable from the number that used them.

Driving `pyab3p` through **this repository's reader** and comparing pair for pair:

| | |
|---|---:|
| documents compared | 1,252<!--claim:differential.med1250.reference_output.documents_compared:,--> |
| documents agreeing | 1,252<!--claim:differential.med1250.reference_output.documents_agreeing:,--> |
| **documents that could have disagreed** | **515<!--claim:differential.med1250.reference_output.documents_discriminating:,-->** |
| documents where both sides propose nothing | 737<!--claim:differential.med1250.reference_output.documents_vacuous:,--> |
| pairs in the reference output | 1,053<!--claim:differential.med1250.reference_output.reference_pairs_raw:,--> |
| pairs agreeing | 1,053<!--claim:differential.med1250.reference_output.pairs_agreeing:,--> |
| pairs only in the reference | 0<!--claim:differential.med1250.reference_output.pairs_only_in_reference:,--> |
| pairs only in this harness | 0<!--claim:differential.med1250.reference_output.pairs_only_in_harness:,--> |

**The two zeros in the last rows are doing more work than they look like.** They are the check on
the *parser*, not on the harness: a parser that dropped predictions would leave
`pairs only in this harness` positive, because the harness side is produced by running `pyab3p` live
and owes nothing to the parse; a parser that harvested text as predictions would leave
`pairs only in the reference` positive. Both are zero, so the reference output is read exactly, in
both directions.

**Read the third row before the second.** `1,252 of 1,252` is arithmetic over a corpus that is
mostly empty on both sides;
737<!--claim:differential.med1250.reference_output.documents_vacuous:,--> of those records agree by
proposing nothing, and the check discriminates on
515<!--claim:differential.med1250.reference_output.documents_discriminating:,-->. The pair count is
the figure with no vacuous half in it.

**This could have failed, and it is not a small thing that it did not.** NLM ran the C++ program
over `MED1250_unlabeled` **one line at a time**; this harness assembles title and abstract from the
*labelled* file into one string and hands that to a Python binding of the same code. Nothing
requires those to agree, and they agree exactly.

**Shown failing, in the environment where it runs** —
`differential.med1250.reference_output_mutations`, `--interpreter` required. Five perturbations of
the text this harness hands the extractor, the reference output untouched, each compared the same
way:

| perturbation | documents differing |
|---|---:|
| **control**, unperturbed | **0<!--claim:differential.med1250.reference_output_mutations.documents_differing.control:,-->** |
| text case-folded | 508<!--claim:differential.med1250.reference_output_mutations.documents_differing.casefold:,--> |
| brackets removed | 512<!--claim:differential.med1250.reference_output_mutations.documents_differing.brackets_removed:,--> |
| first half of the text only | 121<!--claim:differential.med1250.reference_output_mutations.documents_differing.first_half:,--> |
| spaces removed | 515<!--claim:differential.med1250.reference_output_mutations.documents_differing.spaces_removed:,--> |
| word order reversed | 517<!--claim:differential.med1250.reference_output_mutations.documents_differing.words_reversed:,--> |

5<!--claim:differential.med1250.reference_output_mutations.mutations_detected:,--> of
5<!--claim:differential.med1250.reference_output_mutations.mutations_run:,--> detected. The
perturbations are crude by design — the question is whether the comparison is sensitive to its input
at all, not whether it models a plausible reader bug. **The first version of this evidence was a
fenced block of numbers produced in a scratch directory**, which is a figure no gate can read; it is
a committed arm with a run id because R16's objection to a hand-authored chart is the same objection
to a hand-pasted code block.

**One row exceeds the discriminating count and that is not an error.**
517<!--claim:differential.med1250.reference_output_mutations.documents_differing.words_reversed:,-->
is larger than
515<!--claim:differential.med1250.reference_output_mutations.documents_discriminating:,--> because a
perturbation can *invent* a definition in a record where both sides originally proposed nothing.
`documents_discriminating` bounds the records where the comparison could detect a **loss**; it does
not bound where it can detect a gain.

And the same predictions, scored by `bench/scoring.py`, come to
96.91<!--claim:differential.med1250.reference_output.exact_precision:.2f--> /
82.06<!--claim:differential.med1250.reference_output.exact_recall:.2f--> /
88.87<!--claim:differential.med1250.reference_output.exact_f1:.2f--> exact — reproducing
`extraction.med1250.pyab3p` in the table above **to the digit**, from predictions this repository
never generated. `governed_catalog.socrata.scorer_agreement` is the other figure here reproduced by
something other than the runner that wrote it; whether these two are the only ones has not been
counted, so the sentence is left at *the other* rather than at *the first*.

#### The scorer, checked against a second implementation — and why that is the weak arm

`bench/scoring.py`'s counts were re-derived by a second scorer written in the runner from the
*documented* convention, sharing no code with it: character walks instead of regular expressions,
`Counter` intersection instead of list removal. Over
6<!--claim:differential.med1250.scorer_agreement.prediction_sets:,--> prediction sets and
5,159<!--claim:differential.med1250.scorer_agreement.pairs_scored:,--> pairs,
12<!--claim:differential.med1250.scorer_agreement.verdicts_agreeing_on_counts:,--> of
12<!--claim:differential.med1250.scorer_agreement.verdicts_compared:,--> verdicts agree on the
integer TP/FP/FN triple and
12<!--claim:differential.med1250.scorer_agreement.verdicts_agreeing_on_figures:,--> of
12<!--claim:differential.med1250.scorer_agreement.verdicts_compared:,--> on the rounded rates.
8<!--claim:differential.med1250.scorer_agreement.verdicts_from_extractors:,--> of those verdicts
come from a real extractor; the other four are the `empty` control and the gold fed back, which any
two scorers agree on trivially and which are named in the entry rather than absorbed into the total.

**This arm is weaker than the one above it and weaker than the precedent it copies, on two counts
that are recorded in the entry as fields rather than left to this paragraph.**
`governed_catalog.socrata.scorer_agreement` compared two scorers written by two workstreams in two
files for two different questions, and only then noticed they had to agree. This one compares a
scorer against a reimplementation written in the same round, by the same author, *for the purpose of
agreeing*: `written_by_a_second_author` is `false` in the saved entry. Common-author error — the two
implementations being wrong in the same way because one person held one wrong idea — is precisely
what it cannot detect. And agreement between two implementations of a convention is evidence about
the implementations and **never** about the convention, which is what the withdrawn sentence was
appealing to the literature about.

`tests/test_scorer_differential.py` mutation-tests it rather than trusting it: four perturbations of
one documented step each, all asserted to break the agreement. The first version of that fixture
detected none of them, because no record in it differed in case, and the test passed while measuring
nothing. That is recorded in the file.

#### What the differential found that nobody was looking for

**The harness cannot score 100, and nothing said so.** Feed the gold back as a prediction set:

| | |
|---|---:|
| gold pairs | 1,221<!--claim:differential.med1250.harness_ceiling.gold_pairs:,--> |
| reachable | 1,199<!--claim:differential.med1250.harness_ceiling.reachable_pairs:,--> |
| **unreachable by any system** | **22<!--claim:differential.med1250.harness_ceiling.unreachable_pairs:,--> in 22<!--claim:differential.med1250.harness_ceiling.documents_affected:,--> documents** |
| maximum precision | 100.00<!--claim:differential.med1250.harness_ceiling.max_precision_pct:.2f--> % |
| **maximum recall** | **98.20<!--claim:differential.med1250.harness_ceiling.max_recall_pct:.2f--> %** |
| **maximum F1** | **99.09<!--claim:differential.med1250.harness_ceiling.max_f1_pct:.2f--> %** |

`bench/run_extraction.py` collapses repeated pairs within a document for every system alike, and the
gold is *not* collapsed, so a record that genuinely defines the same pair twice keeps both copies in
the recall denominator with one of them unreachable. The runner's docstring already called this "a
handful" and said the cost is "small and shared". Both are true. Neither is a number, and every
recall figure in the table above is against a ceiling of
98.20<!--claim:differential.med1250.harness_ceiling.max_recall_pct:.2f--> % rather than against the
perfect score a reader assumes is up there.

**Two decisions the scorer's own documentation does not state, priced.**

- **Matching is pooled over the whole corpus, not per document.** `bench/scoring.py` accumulates one
  gold list and one prediction list across every record and matches them multiset-wise at the end,
  so a prediction in one abstract can consume a gold pair from another. Its docstring reasons about
  documents throughout and never says this. Cost, measured across every cell of six prediction sets
  by two conventions:
  0.00<!--claim:differential.med1250.specification.axis_pooling_max_abs_f1_delta:.2f--> points, the
  maximum absolute difference over all twelve. A null result with its firing count: the axis was
  evaluated twelve times and moved nothing.
- **The relaxed convention reaches the long form only.** The short form is matched under the *exact*
  convention in both modes — the docstring speaks of the long form throughout and never says what
  happens to the short one. It costs this library
  0.80<!--claim:differential.med1250.specification.axis_relaxed_short_form_max_f1_delta:.2f--> points
  of relaxed F1, over exactly
  9<!--claim:differential.med1250.specification.axis_relaxed_short_form_pairs_reclassified.acronymkit:,-->
  pairs. **The class is one thing, and it is the annotator's punctuation rather than ours** — in all
  nine the gold short form carries edge punctuation and the predicted one does not: gold `.V(E)`,
  `-SH`, `HRPO-`, `[CK]`, `M.O.I.`, `R.D.T.`, `C.A.H.`, `C.P.H.`, `C.L.H.` against predicted `V(E)`,
  `SH`, `HRPO`, `CK`, `M.O.I`, `R.D.T`, `C.A.H`, `C.P.H`, `C.L.H`.

  It moves nobody else:
  0.00<!--claim:differential.med1250.specification.axis_relaxed_short_form_f1_delta_by_system.ab3p_reference_output:.2f-->
  for the Ab3P reference output,
  0.00<!--claim:differential.med1250.specification.axis_relaxed_short_form_f1_delta_by_system.abbreviations:.2f-->
  for `abbreviations` and
  0.00<!--claim:differential.med1250.specification.axis_relaxed_short_form_f1_delta_by_system.abbreviation_extractor:.2f-->
  for `abbreviation_extractor`. **The convention as shipped costs us points and costs nobody else
  any**, which is the direction that makes reporting it cheap — and is exactly why it is worth
  writing down now rather than after somebody finds a decision that goes the other way.

#### What this establishes and what it does not

| | |
|---|---|
| the reader assembles the corpus the way the reference implementation's own run saw it | **established**, against an artefact this project did not produce |
| the record segmentation matches | **established**, same rule, same 1,252<!--claim:differential.med1250.reference_output.documents_compared:,--> keys in order |
| the `pyab3p` row is the reference implementation's real score under our scorer | **established**, from predictions we did not generate |
| `bench/scoring.py` implements the convention its docstring describes | **narrowly supported** — by one same-author reimplementation, mutation-tested |
| **the convention itself is the right one** | **not established, and not establishable this way** |
| **this harness matches Ab3P's published evaluation** | **still open — `U-1`, unchanged** |

The last two rows are the point. Two implementations agreeing prove they implement the same
convention, not that the convention is right — and the convention is the thing the withdrawn
sentence was appealing to the literature about. `U-1` in
[docs/DEFINITION-OF-DONE.md](DEFINITION-OF-DONE.md#standing-unknowns) is unchanged in scope and
closes on the same afternoon it always did: the paper's figures read from the paper, cited with the
date somebody read them.

**Should every scorer this project ships carry an agreement arm?** The two that now exist —
`governed_catalog.socrata.scorer_agreement` and `differential.med1250.scorer_agreement` — are not
equally worth having, and a blanket rule would flatten that. The proposal, recorded so a later round
can refuse it: **required for a scorer whose output is cited in prose, and required to name its own
weakness in a field**, because a same-author reimplementation is cheap to produce, always agrees,
and looks exactly like validation. The cross-workstream form is worth requiring; the same-author
form is worth publishing and worth never calling validation. Nothing in this repository enforces
either yet.

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
not a like-for-like comparison and has been quoted as one.

**Every number in this table is span *detection* and none of it is pairing**, which is stated before
the table rather than under it because the table is what gets quoted. `bench.run_spans.SpanPrediction`
holds short-form spans and long-form spans and has no slot for the edge between them: replaying
PLOD's own gold with each document's long forms rotated against its short forms scores
100.00<!--claim:shortform_contest.plod.all.pairing_blind.rotated.short_form.exact_f1:.2f--> on all
four span metrics, byte-identical to the honest replay, while
1,054<!--claim:shortform_contest.plod.all.pairing_denominator.pairs_mispaired:,--> of the
1,778<!--claim:shortform_contest.plod.all.pairing_denominator.pairs_replayed:,--> replayed pairs are
wrong. A win in any column below says this library puts abbreviation spans in the right places. It
says nothing about whether the expansions it pairs them with are right, and this library's actual
claim is the pairing. [The scoring type is the conclusion, not a caveat](#the-scoring-type-is-the-conclusion-not-a-caveat)
carries the firing counts and the two consequences.

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
*larger*, not smaller. Removing this library's handicap alone reverses the result. The signed margin
per region, cited rather than fenced, because a delta printed only inside a code block is a delta the
claims gate cannot check:

| Gold short-form spans kept | Margin, `acronymkit` − `allcaps`, exact F1 | Who leads |
|---|---:|---|
| all — every annotated occurrence | -16.06<!--claim:shortform_contest.plod.all.convention.margin.all:+.2f--> | `allcaps` |
| all-caps token only — the baseline's own rule | -23.40<!--claim:shortform_contest.plod.all.convention.margin.caps:+.2f--> | `allcaps` |
| bracket-adjacent only — definitional gold | +10.60<!--claim:shortform_contest.plod.all.convention.margin.definitional:+.2f--> | **`acronymkit`** |
| both conditions | +2.10<!--claim:shortform_contest.plod.all.convention.margin.definitional_caps:+.2f--> | **`acronymkit`** |

Those four figures are the differences of the eight cells above them, taken on the published
two-decimal values so that subtracting the table reproduces them exactly. They are recorded under
`shortform_contest.plod.all.convention`, whose `command` field is the one line that re-derives every
one of them from `bench/results.json`; the runner prints the same four rows as its `lead` column
under `python bench/run_shortform_contest.py --split all`.

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

### What the reversal costs to say: annotation convention, priced, and the subtraction that gets it wrong

**This is a finding about the corpora and not about either system, and it belongs beside
[the monoculture result](#the-extraction-monoculture-and-what-it-does-to-the-corpora) rather than
beside a vindication.** That section measures what the field's extractors can *see*. This one
measures what the field's corpora *count*, and the two are the same shape: the evaluation substrate
decides the answer at least as much as the systems do.

Nothing below re-ran anything. The same two unmodified systems are scored over the same
1,351<!--claim:shortform_contest.plod.all.convention.documents:,--> documents four times; the only
thing that changes is which gold spans PLOD's annotation convention is read as admitting.

| Quantity | Value | What moved, from the margin table above |
|---|---:|---|
| The **annotation** axis, at the full gold denominator | +26.66<!--claim:shortform_contest.plod.all.convention.swing.definitional_at_all_gold:+.2f--> | `all` → `definitional`; **the sign reverses on this axis alone** |
| The annotation axis again, inside the caps region | +25.50<!--claim:shortform_contest.plod.all.convention.swing.definitional_at_caps_gold:+.2f--> | `caps` → `definitional_caps` |
| The **admission-rule** axis, at the full gold denominator | -7.34<!--claim:shortform_contest.plod.all.convention.swing.caps_at_all_gold:+.2f--> | `all` → `caps`; it runs the other way |
| The admission-rule axis again, inside definitional gold | -8.50<!--claim:shortform_contest.plod.all.convention.swing.caps_at_definitional_gold:+.2f--> | `definitional` → `definitional_caps` |
| Interaction between the two | -1.16<!--claim:shortform_contest.plod.all.convention.swing.interaction:+.2f--> | the axes are close to additive |
| Corner to corner, raw row to doubly-restricted row | +18.16<!--claim:shortform_contest.plod.all.convention.swing.corner_to_corner:+.2f--> | `all` → `definitional_caps` |

**"Annotation convention was worth about eighteen points" is the wrong subtraction, and it
understates the finding.** Eighteen is the corner-to-corner figure, and it is the **net** of two
axes only one of which is a convention. The `definitional` axis is one — PLOD annotates every
*occurrence* of an abbreviation, defined or not, and D-041 forbids this library from emitting an
unpaired short form, so that axis prices a decision the corpus made about what to label. The `caps`
axis is not: it is `predict_all_caps`'s own admission rule turned into a gold filter, which is a
property of the baseline rather than of PLOD. Eighteen is what is left after the convention effect is
netted against that system-shape effect, and the two ways of doing that subtraction are the two
routes across the 2×2 in the table above:
+26.66<!--claim:shortform_contest.plod.all.convention.swing.definitional_at_all_gold:+.2f--> then
-8.50<!--claim:shortform_contest.plod.all.convention.swing.caps_at_definitional_gold:+.2f-->, or
-7.34<!--claim:shortform_contest.plod.all.convention.swing.caps_at_all_gold:+.2f--> then
+25.50<!--claim:shortform_contest.plod.all.convention.swing.definitional_at_caps_gold:+.2f-->. Both
reach 18.16<!--claim:shortform_contest.plod.all.convention.swing.corner_to_corner:.2f-->; the two
*headline* effects do not, because
26.66<!--claim:shortform_contest.plod.all.convention.swing.definitional_at_all_gold:.2f--> and
-7.34<!--claim:shortform_contest.plod.all.convention.swing.caps_at_all_gold:.2f--> add to `19.32`, and the
gap between `19.32` and the corner is the interaction,
-1.16<!--claim:shortform_contest.plod.all.convention.swing.interaction:.2f--> — which is the whole
reason to print the four conditional effects rather than two main ones. **The honest number for
*annotation convention* is the larger one**, taken at the full gold denominator, where it reverses
the ranking by itself.

**And "about eighteen" is a value two different quantities happen to share, which is why it is worth
publishing the arithmetic rather than the adjective.** Between the raw row and the doubly-restricted
row the baseline's own F1 rises by
17.94<!--claim:shortform_contest.plod.all.convention.span.allcaps:.2f--> points
(68.62<!--claim:shortform_contest.plod.all.allcaps.all.exact_f1:.2f--> →
86.56<!--claim:shortform_contest.plod.all.allcaps.definitional_caps.exact_f1:.2f-->) — within a
quarter of a point of the corner-to-corner swing and not the same measurement. This library's own F1
rises by 36.10<!--claim:shortform_contest.plod.all.convention.span.acronymkit:.2f-->
(52.56<!--claim:shortform_contest.plod.all.acronymkit.high_precision.native.all.exact_f1:.2f--> →
88.66<!--claim:shortform_contest.plod.all.acronymkit.high_precision.native.definitional_caps.exact_f1:.2f-->),
and this library's rise minus the baseline's is the corner-to-corner
18.16<!--claim:shortform_contest.plod.all.convention.swing.corner_to_corner:.2f-->. **That
36.10<!--claim:shortform_contest.plod.all.convention.span.acronymkit:.2f-->-point range is the
corpus statement**: one unmodified
configuration, one corpus, one metric, and a published F1 anywhere between
52.56<!--claim:shortform_contest.plod.all.acronymkit.high_precision.native.all.exact_f1:.2f--> and
88.66<!--claim:shortform_contest.plod.all.acronymkit.high_precision.native.definitional_caps.exact_f1:.2f-->
according only to which annotation convention the gold is read under.

**Through the unprivileged localiser the finding is the same size.** The convention axis reads
26.50<!--claim:shortform_contest.plod.all.convention.localised_swing.definitional_at_all_gold:.2f-->
and the corner-to-corner swing
18.25<!--claim:shortform_contest.plod.all.convention.localised_swing.corner_to_corner:.2f-->, against
26.66<!--claim:shortform_contest.plod.all.convention.swing.definitional_at_all_gold:.2f--> and
18.16<!--claim:shortform_contest.plod.all.convention.swing.corner_to_corner:.2f--> on the native
row — so nothing here depends on the span path D-066 flagged as the flattering one.

**The replication is not independent and is reported anyway.** On the `test` split the convention
axis reads
26.00<!--claim:shortform_contest.plod.test.convention.swing.definitional_at_all_gold:.2f--> and the
corner-to-corner swing
15.27<!--claim:shortform_contest.plod.test.convention.swing.corner_to_corner:.2f-->. `test` is a
subset of `all`, so that is one corpus reported twice and not a second observation — and the
corner-to-corner figure is three points off the pooled one, which is what a `153`-document
sub-sample of a `1,351`-document corpus looks like.

**What this does not say.** It does not say PLOD's convention is wrong; PLOD annotates occurrences
because a reader of PLOS text wants occurrences. It does not say this library would win under a
convention chosen by somebody else. And it does not survive contact with the next section, which is
the one that matters more than the reversal.

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

**That firing count needs its denominator, and the denominator is the part that keeps getting
overstated.** Under the same zip-order pairing the replay uses, PLOD-CW pooled holds
1,778<!--claim:shortform_contest.plod.all.pairing_denominator.pairs_replayed:,--> pairs, so the
1,054<!--claim:shortform_contest.plod.all.pairing_denominator.pairs_mispaired:,--> wrong ones are
59.28<!--claim:shortform_contest.plod.all.pairing_denominator.pairs_mispaired_pct:.2f--> % of them —
**three in five, not three quarters.** The three-quarters reading is available on this run and it is
the wrong end of it:
1,009<!--claim:shortform_contest.plod.all.pairing_denominator.documents_untouched:,--> documents,
74.69<!--claim:shortform_contest.plod.all.pairing_denominator.documents_untouched_pct:.2f--> % of the
corpus, carry at most one long form and the rotation could not touch them at all. On the `test` split
the same control is weaker again —
61<!--claim:shortform_contest.plod.test.pairing_denominator.pairs_mispaired:,--> of
149<!--claim:shortform_contest.plod.test.pairing_denominator.pairs_replayed:,--> pairs, and
83.66<!--claim:shortform_contest.plod.test.pairing_denominator.documents_untouched_pct:.2f--> % of
documents untouched. **The result is unaffected and the strength of the evidence is not**: the metric
is blind to three pairings in five and the null is exactly as null, but nobody may say the scorer was
shown three quarters of the gold mis-paired, because it was not.

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

**Read it with the convention result above, because they are one story and neither half is about a
system.** This section measures what the field's extractors can *see*: seven Schwartz & Hearst
descendants reach
57.65<!--claim:monoculture.plod_all.gold.long_form.overlap.class.sh_family_recall_pct:.2f--> % of
PLOD's gold long forms and
34.98<!--claim:monoculture.plod_all.gold.long_form.overlap.class.unproposed_alignable_from_gold_short_form_pct_of_gold:.2f--> %
of that gold is both unreached and cleanly alignable — pairs the validator would accept and the
candidate generator never offers. [The convention section](#what-the-reversal-costs-to-say-annotation-convention-priced-and-the-subtraction-that-gets-it-wrong)
measures what the field's corpora *count*: the same unmodified configuration of this library scores
anywhere between
52.56<!--claim:shortform_contest.plod.all.acronymkit.high_precision.native.all.exact_f1:.2f--> and
88.66<!--claim:shortform_contest.plod.all.acronymkit.high_precision.native.definitional_caps.exact_f1:.2f-->
on one corpus — a
36.10<!--claim:shortform_contest.plod.all.convention.span.acronymkit:.2f-->-point range decided
entirely by which annotation convention the gold is read under, and enough to reverse a head-to-head
ranking against a one-line baseline. **The evaluation substrate shapes the answer at least as much
as the systems do**, and that is the sentence this project would keep if it had to discard every
accuracy number on this page. It is also the reason the extraction figure is a supporting number:
optimising against a substrate this plastic is optimising against the substrate.

**Neither half licenses the other.** The convention result is measured on PLOD alone and says nothing
about the field's blind spot; the monoculture result is measured across five corpora and says nothing
about how much a convention is worth. They agree in shape and were measured separately, and that is
all that is being claimed by putting them together.

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
ordering is consistent with the thesis and does not establish it.

**Half of that confound is now measured, and this table is not the evidence it was read as.**
Separating the *provenance* half would still need a corpus of article body text annotated by pooling
Schwartz & Hearst systems, which nobody publishes on purpose. The *genre* half can be measured the
other way round — hold provenance constant and vary genre, by taking the abstract and the body of
the **same** articles — and it has been:
[below](#genre-separated-from-provenance-abstracts-against-bodies-of-the-same-articles). On articles
whose provenance is identical by construction, the body half is measurably less parenthetical and
hands the independent proposers measurably more. **So the ordering above does not require the
provenance explanation**, and the strong reading of it stays dead.

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

### Genre, separated from provenance: abstracts against bodies of the same articles

The confound above says separating genre from provenance needs a corpus of article body text whose
gold was pooled from Schwartz & Hearst descendants. **That is the right instrument for the
*provenance* half and it still does not exist. The *genre* half can be measured the other way
round** — hold provenance constant and vary genre — and it now has been.

`bench/run_genre.py`, corpus `[corpora.pmc_oa_same_article_genre]`, role
`single_annotator_reference`, which `headline_capable()` excludes for every task. Nothing below is
a headline number and nothing below is offered as one.

**The design, and what it holds constant.** PMC's Open Access Subset ships each article as one JATS
file carrying an `<abstract>` and a `<body>`. Taking both halves out of one file holds provenance,
domain, author, journal, register and deposit route constant, and varies genre alone. The gold is
each article's own `<def-list>` abbreviation roster — the same arbiter PLOD-CW uses, read at the
source rather than through Zilio et al.'s pipeline — and it sits in `<back>`, which is in **neither**
measured half, so it adjudicates the two symmetrically. Admission compares no character of a term
against its definition, because a gold filtered by `sh_alignable` could not measure what
`sh_alignable` misses. The proposer pool is `bench/run_monoculture.py`'s, unchanged: same nine
proposers, same edge unit, same `bracket_adjacent`, same `gold_class_record`. No descendant was
added.

**A third half, because "bodies are longer" is the obvious attack.** `body_matched` is a contiguous
body window cut to that article's own abstract length at a seeded uniform offset. It is the length
control for the **proposal** rows and it is **biased for the gold rows**: a window holding a pair's
two strings without holding its definition site locates a non-definitional co-occurrence, which is
almost never beside a bracket. Read it for the proposal rows; for the gold rows the full body is the
honest arm.

**The licence is per article, and filtering is not optional.** PMC's own page says so —
*"Within the PMC Open Access Subset articles are available for reuse, but license terms vary"* —
and the draw measured it rather than assuming it. Of
5,376<!--claim:genre.pmc_oa.sample.draw_probes:,--> probes,
3,453<!--claim:genre.pmc_oa.sample.draw_article_versions_that_exist:,--> reached an article version and
2,756<!--claim:genre.pmc_oa.sample.draw_articles_carrying_a_licence_code:,--> of those carried a licence code. Only
2,013<!--claim:genre.pmc_oa.sample.draw_articles_permissively_licensed:,--> were CC BY or CC0 —
26.96<!--claim:genre.pmc_oa.sample.draw_non_permissive_pct_of_licensed:.2f--> % of the licensed articles are **not**, split across
CC BY-NC-ND (312<!--claim:genre.pmc_oa.sample.draw_census.CC BY-NC-ND:,-->), CC BY-NC
(300<!--claim:genre.pmc_oa.sample.draw_census.CC BY-NC:,-->), CC BY-NC-SA (119<!--claim:genre.pmc_oa.sample.draw_census.CC BY-NC-SA:,-->), a
text-mining-only grant (11<!--claim:genre.pmc_oa.sample.draw_census.TDM:,-->) and exactly
1<!--claim:genre.pmc_oa.sample.draw_census.CC BY-ND:,--> CC BY-ND. That last one is the trap
[docs/AUDIT-2026-08.md](AUDIT-2026-08.md#pmc-mirror-or-do-not-but-decide-on-the-merits) flagged —
PMC groups ND under filters for commercial reuse, and commercial reuse and derivative works are not
the same permission — and it is real, if rare. Retrieval is through the PMC Cloud Service, which the
same page names as one of four services permitted to retrieve automatically. See
[data/LICENSES.md](../data/LICENSES.md), substrate `pmc-oa-same-article`.

**The sample, with its attrition.** 2,000<!--claim:genre.pmc_oa.sample.attrition_drawn:,--> articles drawn and fetched;
161<!--claim:genre.pmc_oa.sample.attrition_no_abstract_or_no_body:,--> carry no abstract or no body and are not a
same-article contrast; 0<!--claim:genre.pmc_oa.sample.attrition_unparseable:,--> failed to parse;
1,839<!--claim:genre.pmc_oa.sample.attrition_kept:,--> kept. Of those,
220<!--claim:genre.pmc_oa.sample.articles_with_a_roster:,--> ship an abbreviation roster, declaring
2,696<!--claim:genre.pmc_oa.sample.roster_pairs_declared:,--> pairs between them. **The gold arm rests on those
220<!--claim:genre.pmc_oa.sample.articles_with_a_roster:,--> articles and not on the sample**, and its denominators are
in the table.

**The result.** Every column is the same 1,839<!--claim:genre.pmc_oa.sample.attrition_kept:,--> articles.

| | Abstract | Body | Body window cut to the abstract's length |
|---|---:|---:|---:|
| Characters | 2,974,657<!--claim:genre.pmc_oa.abstract.corpus.characters:,--> | 59,486,201<!--claim:genre.pmc_oa.body.corpus.characters:,--> | 2,974,657<!--claim:genre.pmc_oa.body_matched.corpus.characters:,--> |
| Declared roster pairs located here | 388<!--claim:genre.pmc_oa.abstract.corpus.gold_pairs_located:,--> | 1,892<!--claim:genre.pmc_oa.body.corpus.gold_pairs_located:,--> | 196<!--claim:genre.pmc_oa.body_matched.corpus.gold_pairs_located:,--> |
| **Located gold long forms beside a bracket %** | **84.54<!--claim:genre.pmc_oa.abstract.corpus.gold_pairs_long_form_bracket_adjacent_pct:.2f-->** | **75.85<!--claim:genre.pmc_oa.body.corpus.gold_pairs_long_form_bracket_adjacent_pct:.2f-->** | 50.00<!--claim:genre.pmc_oa.body_matched.corpus.gold_pairs_long_form_bracket_adjacent_pct:.2f--> |
| S&H family reaches, of located gold long forms % | 87.11<!--claim:genre.pmc_oa.abstract.gold.long_form.overlap.class.sh_family_recall_pct:.2f--> | 80.92<!--claim:genre.pmc_oa.body.gold.long_form.overlap.class.sh_family_recall_pct:.2f--> | 45.92<!--claim:genre.pmc_oa.body_matched.gold.long_form.overlap.class.sh_family_recall_pct:.2f--> |
| Unreached yet alignable with a gold short form, % of gold | 9.79<!--claim:genre.pmc_oa.abstract.gold.long_form.overlap.class.unproposed_alignable_from_gold_short_form_pct_of_gold:.2f--> | 16.01<!--claim:genre.pmc_oa.body.gold.long_form.overlap.class.unproposed_alignable_from_gold_short_form_pct_of_gold:.2f--> | 46.94<!--claim:genre.pmc_oa.body_matched.gold.long_form.overlap.class.unproposed_alignable_from_gold_short_form_pct_of_gold:.2f--> |
| Proposal edges in the union | 3,794<!--claim:genre.pmc_oa.abstract.proposals.edges.union_total:,--> | 40,385<!--claim:genre.pmc_oa.body.proposals.edges.union_total:,--> | 2,214<!--claim:genre.pmc_oa.body_matched.proposals.edges.union_total:,--> |
| **Union gain from the two independent proposers %** | **0.82<!--claim:genre.pmc_oa.abstract.proposals.edges.independent_gain_pct:.2f-->** | **9.55<!--claim:genre.pmc_oa.body.proposals.edges.independent_gain_pct:.2f-->** | **13.32<!--claim:genre.pmc_oa.body_matched.proposals.edges.independent_gain_pct:.2f-->** |
| `shapecue` roster and cue firings | 32<!--claim:genre.pmc_oa.abstract.proposer.shapecue.cue_firings_total:,--> | 5,694<!--claim:genre.pmc_oa.body.proposer.shapecue.cue_firings_total:,--> | 316<!--claim:genre.pmc_oa.body_matched.proposer.shapecue.cue_firings_total:,--> |
| `shapecue` edges per 100,000 characters | 1.08<!--claim:genre.pmc_oa.abstract.proposer.shapecue.edges_per_100k_characters:.2f--> | 9.57<!--claim:genre.pmc_oa.body.proposer.shapecue.edges_per_100k_characters:.2f--> | 10.62<!--claim:genre.pmc_oa.body_matched.proposer.shapecue.edges_per_100k_characters:.2f--> |
| Open brackets per 100,000 characters | 301.9<!--claim:genre.pmc_oa.abstract.corpus.open_brackets_per_100k_characters:.1f--> | 412.4<!--claim:genre.pmc_oa.body.corpus.open_brackets_per_100k_characters:.1f--> | 418.9<!--claim:genre.pmc_oa.body_matched.corpus.open_brackets_per_100k_characters:.1f--> |

**The last row kills the cheapest counter-explanation.** Bodies are bracket-**richer** than their own
abstracts — 412.4<!--claim:genre.pmc_oa.body.corpus.open_brackets_per_100k_characters:.1f--> open brackets per 100,000
characters against 301.9<!--claim:genre.pmc_oa.abstract.corpus.open_brackets_per_100k_characters:.1f-->, after citation
brackets have been swept out of both — and their definitions are nonetheless *less* often beside
one. The genre effect is not "body text has fewer parentheses".

The obvious objection to that row is that the citation sweep leaves punctuation-only brackets
behind — `[<xref>1</xref>, <xref>2</xref>]` renders as `[, ]`, which the sweep's pattern does not
match — so it was measured rather than argued, and it does not reach the conclusion. Command output,
not a benchmark measurement; columns are characters, open brackets, punctuation-only brackets, and
open brackets per 100,000 characters **after** every punctuation-only bracket is deducted:

```
python -c "
import random,sys
sys.path[:0]=['.','src']
from bench import run_genre as g
FILLER=set(' ,;-'+chr(9)+chr(10)+chr(8211)+chr(8212))
def junk(s):
    n=0
    for i,ch in enumerate(s):
        if ch in '([':
            j=i+1
            while j<len(s) and s[j] in FILLER: j+=1
            if j<len(s) and s[j] in ')]': n+=1
    return n
a,_=g.load_articles(g.pinned_pmcids())
for h in ('abstract','body'):
    r=random.Random(g.WINDOW_SEED); t=[x.half(h,r) for x in a]; c=sum(map(len,t))
    o=sum(sum(s.count(b) for b in '([{') for s in t); k=sum(junk(s) for s in t)
    print(f'{h:<9}{c:>12,}{o:>10,}{k:>8,}{100000*(o-k)/c:>9.1f}')
"
abstract    2,974,657     8,980       0    301.9
body       59,486,201   245,306   2,596    408.0
```

Body text carries the residue and abstracts carry none of it, and deducting every last one of them
leaves the ordering exactly where it was. What body text actually carries is a class of definition
that is not written with a parenthesis at all, and the second-to-last row of the table is where that
class lives: `shapecue`'s roster rule fires
1.08<!--claim:genre.pmc_oa.abstract.proposer.shapecue.edges_per_100k_characters:.2f--> times per 100,000 characters of abstract and
10.62<!--claim:genre.pmc_oa.body_matched.proposer.shapecue.edges_per_100k_characters:.2f--> times per 100,000 characters of
length-matched body — the same articles, the same authors, the same character budget.

**The differences, paired, with cluster-bootstrap intervals over articles.** The cluster is the
article and both halves are resampled together, because an article whose author writes `CT`
everywhere contributes many correlated observations to both halves and treating them as independent
would understate every interval. 2,000<!--claim:genre.pmc_oa.contrast.abstract_minus_body.independent_gain_on_proposal_edges.replicates_requested:,-->
replicates, seed 31,337<!--claim:genre.pmc_oa.contrast.abstract_minus_body.independent_gain_on_proposal_edges.seed:,-->. Both interval columns are percentile intervals at the conventional
ninety-five per cent level, written in words because it is a convention rather than a measurement and
the claims gate cannot tell those apart.

| Quantity | Abstract − body | Interval | Abstract − length-matched body window | Interval |
|---|---:|---:|---:|---:|
| Located gold long forms beside a bracket % | **+8.69<!--claim:genre.pmc_oa.contrast.abstract_minus_body.bracket_adjacency_of_located_gold_long_forms.difference_pct:+.2f-->** | [3.29<!--claim:genre.pmc_oa.contrast.abstract_minus_body.bracket_adjacency_of_located_gold_long_forms.difference_ci_low_pct:.2f-->, 13.85<!--claim:genre.pmc_oa.contrast.abstract_minus_body.bracket_adjacency_of_located_gold_long_forms.difference_ci_high_pct:.2f-->] | +34.54<!--claim:genre.pmc_oa.contrast.abstract_minus_body_matched.bracket_adjacency_of_located_gold_long_forms.difference_pct:+.2f--> | [21.76<!--claim:genre.pmc_oa.contrast.abstract_minus_body_matched.bracket_adjacency_of_located_gold_long_forms.difference_ci_low_pct:.2f-->, 46.69<!--claim:genre.pmc_oa.contrast.abstract_minus_body_matched.bracket_adjacency_of_located_gold_long_forms.difference_ci_high_pct:.2f-->] |
| S&H family reach of located gold long forms % | **+6.19<!--claim:genre.pmc_oa.contrast.abstract_minus_body.sh_family_recall_of_located_gold_long_forms.difference_pct:+.2f-->** | [1.67<!--claim:genre.pmc_oa.contrast.abstract_minus_body.sh_family_recall_of_located_gold_long_forms.difference_ci_low_pct:.2f-->, 10.37<!--claim:genre.pmc_oa.contrast.abstract_minus_body.sh_family_recall_of_located_gold_long_forms.difference_ci_high_pct:.2f-->] | +41.20<!--claim:genre.pmc_oa.contrast.abstract_minus_body_matched.sh_family_recall_of_located_gold_long_forms.difference_pct:+.2f--> | [28.88<!--claim:genre.pmc_oa.contrast.abstract_minus_body_matched.sh_family_recall_of_located_gold_long_forms.difference_ci_low_pct:.2f-->, 52.60<!--claim:genre.pmc_oa.contrast.abstract_minus_body_matched.sh_family_recall_of_located_gold_long_forms.difference_ci_high_pct:.2f-->] |
| Union gain from the independent proposers % | **-8.73<!--claim:genre.pmc_oa.contrast.abstract_minus_body.independent_gain_on_proposal_edges.difference_pct:.2f-->** | [-9.80<!--claim:genre.pmc_oa.contrast.abstract_minus_body.independent_gain_on_proposal_edges.difference_ci_low_pct:.2f-->, -7.70<!--claim:genre.pmc_oa.contrast.abstract_minus_body.independent_gain_on_proposal_edges.difference_ci_high_pct:.2f-->] | -12.51<!--claim:genre.pmc_oa.contrast.abstract_minus_body_matched.independent_gain_on_proposal_edges.difference_pct:.2f--> | [-16.10<!--claim:genre.pmc_oa.contrast.abstract_minus_body_matched.independent_gain_on_proposal_edges.difference_ci_low_pct:.2f-->, -9.06<!--claim:genre.pmc_oa.contrast.abstract_minus_body_matched.independent_gain_on_proposal_edges.difference_ci_high_pct:.2f-->] |

**The firing counts behind those intervals, because a difference with no denominator is not a
result.** The two gold rows rest on
157<!--claim:genre.pmc_oa.contrast.abstract_minus_body.bracket_adjacency_of_located_gold_long_forms.articles_with_evidence_left:,--> articles
carrying at least one located gold pair in the abstract and
208<!--claim:genre.pmc_oa.contrast.abstract_minus_body.bracket_adjacency_of_located_gold_long_forms.articles_with_evidence_right:,--> in the
body; the proposal row rests on
1,310<!--claim:genre.pmc_oa.contrast.abstract_minus_body.independent_gain_on_proposal_edges.articles_with_evidence_left:,--> and
1,816<!--claim:genre.pmc_oa.contrast.abstract_minus_body.independent_gain_on_proposal_edges.articles_with_evidence_right:,-->. All
2,000<!--claim:genre.pmc_oa.contrast.abstract_minus_body.independent_gain_on_proposal_edges.replicates_used:,--> replicates were usable in every
comparison; none was dropped for an empty denominator.

**The verdict: genre.** All six intervals exclude zero and all six point the way the genre account
predicts. On articles whose provenance is identical by construction, the body half is less
parenthetical, is reached less by the Schwartz & Hearst family, and hands the independent proposers
a larger share of the union — by the three differences in the table above, on both body arms. **The ordering in the table above therefore does not require
the provenance explanation, and the strong reading of the monoculture stays dead.**

**And it stays dead rather than refuted, because three things this cannot do are worth naming.**

- **It measures the genre main effect and nothing else.** The provenance main effect — whether a
  corpus pooled from these systems certifies their blind spot — is untouched, and settling it still
  needs the corpus nobody publishes. Reversal three in
  [docs/POSITIONING.md](POSITIONING.md#reversal-three-the-research-artifact-stops-resting-on-an-unprovable-claim)
  is unchanged.
- **Every same-article difference here is smaller than the MED1250-to-PLOD difference it is offered
  against, and the residue must not be read as provenance.** Set the two tables side by side and the
  gap is plain. What that gap is *not* is an estimate of a provenance effect: the two comparisons use
  different passage units — one article per passage here, one sentence in PLOD, and a longer passage
  collapses repeated `(short, long)` keys that a shorter one keeps — different corpora, different
  annotation conventions, and PLOD's gold carries a published error rate of its own. Subtracting one
  from the other would be arithmetic on incommensurable quantities. The passage-length half of that
  list is the one thing with a control: on the **proposal** row, where the window is real text and
  the truncation bias does not apply, cutting the body to the abstract's own length moves the
  difference *further* from zero rather than nearer. So passage length is not manufacturing the
  genre effect; if anything the full-body arm understates it. The `body_matched` gold rows carry the
  truncation bias and bound nothing.
- **The abstract half is not MED1250 and the two bracket-adjacency figures are not comparable
  either.** They are measured with different locators — this runner folds the long form's case,
  because an author's roster is typed in sentence case and the article writes the phrase in lower
  case, and without the fold the abstract half locates only
  141<!--claim:genre.pmc_oa.abstract.corpus.gold_pairs_located_without_the_case_fold:,--> pairs instead of
  388<!--claim:genre.pmc_oa.abstract.corpus.gold_pairs_located:,-->. A reader who lines
  84.54<!--claim:genre.pmc_oa.abstract.corpus.gold_pairs_long_form_bracket_adjacent_pct:.2f--> % up against MED1250's
  98.91<!--claim:monoculture.med1250.corpus.gold_pairs_long_form_bracket_adjacent_pct:.2f--> % and
  reads the difference as provenance at fixed genre is doing something this measurement does not
  support.

### What this does not establish

- **Only the genre half of the confound is resolved, and it is resolved in the direction that
  weakens this section's strongest reading.** "Abstracts have no figure legends" is now a measured
  effect rather than a rival story: on the same articles it moves every quantity in this section the
  way MED1250 and PLOD differ. What is *not* measured is whether a corpus pooled from these systems
  certifies their blind spot — the provenance half — and nothing here bears on it. MED1250's
  98.91<!--claim:monoculture.med1250.corpus.gold_pairs_long_form_bracket_adjacent_pct:.2f--> %
  parenthetical gold has a sufficient explanation that is not provenance.
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

## One sense per discourse: the assumption under a document-level `extract()`, measured first

A document-level resolver — one definition anywhere in a document licenses every later occurrence of
that short form — is the largest single change on the table for `extract()`. It rests on
one-sense-per-discourse, which is **an assumption and not a law**, and it is a breaking API change
that would move every recall figure on this page. So the violation rate was measured before anything
was built on it.

`bench/run_one_sense.py`, over the corpus `bench/run_genre.py` already fetched and pinned —
`[corpora.pmc_oa_same_article_genre]`, role `single_annotator_reference`, which `headline_capable()`
excludes for every task. Nothing below is a headline number. The runner is a second file rather than
an arm of `run_genre.py` because that runner's unit is the **half** — abstract against body — and
this question has no halves: a violation whose two definitions straddle the cut is exactly what
cutting the document would hide.

**What would have killed it, written down before the run.** Recorded to a scratch file first and
reproduced verbatim in the round's report, so that the direction and the magnitudes are both
falsifiable:

```
pre-registration -- written before any group was counted, not a benchmark measurement

  A2 dies outright if the genuine-ambiguity violation rate reaches 5 % of short-form
  groups (K1), or if the error on licensed occurrences reaches 10 % (K2), or if the
  error floor exceeds the error rate of the mechanism A2 replaces (K3).
  A2 must be opt-in if the genuine rate lands in [1 %, 5 %) (K4), or if the pooled
  violation rate reaches 15 % even when almost all of it is surface variation (K5).
  A2 is clean only if genuine < 1 %, ceiling < 2 % and pooled < 15 % (K6).

  Point predictions: pooled violation rate 2-7 %, central 4 %; surface variants the
  majority of violations at about 70 %; occurrence-weighted exposure 1.5x to 3x the
  type rate; between 8 and 20 rostered articles carrying a genuine ambiguity.
```

### The authors' own rosters answer a different question, and the answer is close to zero

220<!--claim:one_sense.pmc_oa.sample.articles_with_a_roster:,--> of
1,839<!--claim:one_sense.pmc_oa.sample.articles:,--> articles ship a `<def-list>` roster, declaring
2,696<!--claim:one_sense.pmc_oa.sample.roster_pairs_declared:,--> pairs. Grouped by short form that
is 2,695<!--claim:one_sense.pmc_oa.roster.admitted.case_sensitive.short_form_groups:,--> groups, and
the number carrying two distinct expansions is
1<!--claim:one_sense.pmc_oa.roster.admitted.case_sensitive.groups_with_two_or_more_expansions:,-->.
One. It is `MHB`, declared as *Mueller hinton broth* and as *Mueller-Hinton broth* in the same
glossary, which is a hyphen.

**Do not read that as the violation rate of anything.** A glossary is a curated one-to-one table.
The roster is the place an author's inconsistency gets *fixed*, not the place it shows, so this
figure answers *do authors declare two senses* — a question about declaration habits — and it is a
floor on within-document ambiguity rather than an estimate of one. One event is also not a rate, and
the pre-registration said in advance that below forty violating groups the counts would be reported
and the percentage would not be leaned on.

**Two things the roster does show, and neither was on anybody's list.**

**The admission rule this instrument inherited deletes the one genuine collision the rosters hold.**
Before `roster_pair_admissible` — the rule `bench/run_genre.py` wrote to measure the Schwartz &
Hearst blind spot — the same rosters hold
2,840<!--claim:one_sense.pmc_oa.roster.raw.case_sensitive.short_form_groups:,--> groups and
2<!--claim:one_sense.pmc_oa.roster.raw.case_sensitive.groups_with_two_or_more_expansions:,-->
collisions under the same case-sensitive key. The one that does not survive admission is `BDNF =`,
declared in one article as *brain-derived neurotrophic factor* and as *human brain-derived
neurotrophic factor gene* — a protein against a gene, which is a real second sense — dropped because
the author's `<term>` carries a trailing `=` and the rule refuses whitespace inside a term. **So the
surviving population's rate is one hyphen, and the collision with actual content was filtered out by
a rule written for another question.** A rule cannot be measured through itself, which is why
`raw_roster` re-walks the XML.

**A case-folded key manufactures ambiguity that the document does not contain.** Fold the short-form
key and the raw population becomes
2,837<!--claim:one_sense.pmc_oa.roster.raw.case_folded.short_form_groups:,--> groups with
4<!--claim:one_sense.pmc_oa.roster.raw.case_folded.groups_with_two_or_more_expansions:,-->
collisions. The two that appear only under folding are `ms` = *millisecond* against `MS` = *Multiple
Sclerosis*, and `N` = *Number of patients* against `n` = *Number of patients in a subgroup*. **Neither
is a violation of one sense per discourse.** They are two short forms each, distinguished by case
exactly as their authors intended, and a resolver that folded the key would report an ambiguity where
the document has none. Biology marks case on purpose — `Bdnf` is the mouse gene and `BDNF` the human
one, which is the same article's third declaration — so **half of the folded rate is an artefact of
the key.** That is a design constraint on the change, obtained before the change exists.

### What a document-level resolver would actually have to arbitrate

The roster cannot answer A2's question, so the second instrument reads the text. Every definition
`extract_definitions` offers over the whole document — abstract and body concatenated, `<back>`
excluded — grouped by short form. It needs no gold, because it is not a recall measurement: **it is
the population A2 must arbitrate, and a second expansion in it is a decision A2 has to take whether
or not that expansion is correct.**

Over 1,839<!--claim:one_sense.pmc_oa.resolver.biomedical.documents:,--> documents and
62,464,536<!--claim:one_sense.pmc_oa.resolver.biomedical.characters:,--> characters, `BIOMEDICAL`
offers 38,445<!--claim:one_sense.pmc_oa.resolver.biomedical.definition_pairs_offered:,--> definition
pairs. Restricted to short forms an abbreviation roster rule would admit — the same
`roster_pair_admissible` term half, so that `i.e`, `e.g`, `set` and every single letter are out —
that is 25,691<!--claim:one_sense.pmc_oa.resolver.biomedical.term_shaped.short_form_groups:,-->
groups, of which
1,471<!--claim:one_sense.pmc_oa.resolver.biomedical.term_shaped.groups_with_two_or_more_expansions:,-->
carry two or more distinct expansions:
5.73<!--claim:one_sense.pmc_oa.resolver.biomedical.term_shaped.violation_pct:.2f--> %.

**That rate is a property of the documents and not of the operating point**, which is the strongest
robustness fact here: `HIGH_PRECISION` gives
5.75<!--claim:one_sense.pmc_oa.resolver.high_precision.term_shaped.violation_pct:.2f--> % and
`GENERAL` 5.74<!--claim:one_sense.pmc_oa.resolver.general.term_shaped.violation_pct:.2f--> % over
their own populations. Drop the roster-shaped restriction and `BIOMEDICAL` rises to
6.59<!--claim:one_sense.pmc_oa.resolver.biomedical.all.violation_pct:.2f--> % over
29,619<!--claim:one_sense.pmc_oa.resolver.biomedical.all.short_form_groups:,--> groups, because the
extra 3,928 keys it admits are `i.e`, `Fig` and single letters — and A2 as specified would key those
too. 55.85<!--claim:one_sense.pmc_oa.resolver.biomedical.documents_with_a_violation_pct:.2f--> % of
documents carry at least one.

**The roster's own rate and this one differ by two orders of magnitude, and the bridge between them
is measured rather than assumed.** Of
2,694<!--claim:one_sense.pmc_oa.bridge.biomedical.singly_rostered_short_forms:,--> short forms an
author rostered exactly once, the extractor reaches
1,714<!--claim:one_sense.pmc_oa.bridge.biomedical.also_defined_in_the_text_by_the_extractor:,--> in
the same document, and
406<!--claim:one_sense.pmc_oa.bridge.biomedical.with_an_expansion_the_roster_does_not_carry:,--> of
those —
23.69<!--claim:one_sense.pmc_oa.bridge.biomedical.competing_pct_of_reached:.2f--> % — carry an
expansion the roster does not. A competitor is not proof of a second sense; the extractor has no gold.
It is proof that **the roster does not settle the question**, which is precisely what the roster's own
near-zero rate would otherwise be read as doing.

### Surface variation and genuine ambiguity are different problems, and the residual class is neither

Pooling them would be a phrasing tighter than the measurement, so every violating group is put in one
of three mechanical classes: `surface` (every expansion collapses to one string under a stated ladder
of Unicode folding, punctuation removal, a crude singulariser, a closed stop-word list, and one pass
of nested-abbreviation expansion using the document's own unambiguous definitions), `refinement` (one
expansion is a whole-word subsequence of another), and `distinct` (neither).

| class | groups, `BIOMEDICAL`, roster-shaped | share of violations |
|---|---:|---:|
| `surface` | 412<!--claim:one_sense.pmc_oa.resolver.biomedical.term_shaped.class_surface:,--> | 28.01<!--claim:one_sense.pmc_oa.resolver.biomedical.term_shaped.class_surface_pct_of_violations:.2f--> % |
| `refinement` | 321<!--claim:one_sense.pmc_oa.resolver.biomedical.term_shaped.class_refinement:,--> | 21.82<!--claim:one_sense.pmc_oa.resolver.biomedical.term_shaped.class_refinement_pct_of_violations:.2f--> % |
| `distinct` | 738<!--claim:one_sense.pmc_oa.resolver.biomedical.term_shaped.class_distinct:,--> | 50.17<!--claim:one_sense.pmc_oa.resolver.biomedical.term_shaped.class_distinct_pct_of_violations:.2f--> % |

**`distinct` is a residual and it is not "genuine ambiguity".** Half the violating population lands
there and no rule can split it further, which is above the threshold the pre-registration set for
declaring the decomposition unmeasurable by rule. So it was adjudicated by hand — by **one** annotator,
who also wrote the ladder — on a seeded sample, and the other two classes were adjudicated too,
because a ladder that folded a real second sense into `surface` would make every correctness figure
here too small and a `distinct`-only audit could not see it.

| class sampled | drawn | genuine | one concept written twice | not an expansion at all | unclear |
|---|---:|---:|---:|---:|---:|
| `distinct`, frame 738<!--claim:one_sense.pmc_oa.audit.distinct.frame_size:,--> | 120<!--claim:one_sense.pmc_oa.audit.distinct.sample_size:,--> | 5<!--claim:one_sense.pmc_oa.audit.distinct.label_genuine:,--> | 64<!--claim:one_sense.pmc_oa.audit.distinct.label_variant:,--> | 49<!--claim:one_sense.pmc_oa.audit.distinct.label_artefact:,--> | 2<!--claim:one_sense.pmc_oa.audit.distinct.label_unclear:,--> |
| `refinement`, frame 321<!--claim:one_sense.pmc_oa.audit.refinement.frame_size:,--> | 40<!--claim:one_sense.pmc_oa.audit.refinement.sample_size:,--> | 1<!--claim:one_sense.pmc_oa.audit.refinement.label_genuine:,--> | 33<!--claim:one_sense.pmc_oa.audit.refinement.label_variant:,--> | 6<!--claim:one_sense.pmc_oa.audit.refinement.label_artefact:,--> | 0<!--claim:one_sense.pmc_oa.audit.refinement.label_unclear:,--> |
| `surface`, frame 412<!--claim:one_sense.pmc_oa.audit.surface.frame_size:,--> | 40<!--claim:one_sense.pmc_oa.audit.surface.sample_size:,--> | 0<!--claim:one_sense.pmc_oa.audit.surface.label_genuine:,--> | 40<!--claim:one_sense.pmc_oa.audit.surface.label_variant:,--> | 0<!--claim:one_sense.pmc_oa.audit.surface.label_artefact:,--> | 0<!--claim:one_sense.pmc_oa.audit.surface.label_unclear:,--> |

**The ladder does not over-fold**, on the evidence available: nothing drawn from `surface` is a second
sense, and one thing drawn from `refinement` is — `MyHC` standing for the slow-twitch myosin heavy
chain gene and for the fast-twitch one in the same article.

**And the largest adjudicated share of the residual class is not ambiguity at all.**
49<!--claim:one_sense.pmc_oa.audit.distinct.label_artefact:,--> of
120<!--claim:one_sense.pmc_oa.audit.distinct.sample_size:,--> `distinct` groups contain a long form
that is not an expansion of anything — `STAT1` "defined" as a catalogue number, `SPE` as a supplier's
name, `OR` as *of urbanization*. Genuine second senses are
5<!--claim:one_sense.pmc_oa.audit.distinct.label_genuine:,-->.

### A2 priced in A2's own terms: what it buys, what it would get wrong, and against what

Model A2 as specified — commit to the first definition in document order, license every whole-token
occurrence of that short form at or after it, roster-shaped short forms only, which is the generous
reading. Then over the whole corpus at `BIOMEDICAL`:

- **What it buys.**
  247,974<!--claim:one_sense.pmc_oa.a2.biomedical.licensed_occurrences:,--> licensed occurrences, of
  which
  212,305<!--claim:one_sense.pmc_oa.a2.biomedical.licensed_occurrences_outside_every_definition_sentence:,-->
  —
  85.62<!--claim:one_sense.pmc_oa.a2.biomedical.a2_new_coverage_pct_of_licensed:.2f--> % — sit
  outside every sentence that carries a definition of their own short form. Those are the occurrences
  a sentence-scoped extractor reaches none of. A2's coverage is
  5.95<!--claim:one_sense.pmc_oa.a2.biomedical.a2_new_coverage_multiple_of_current:.2f--> times what
  the sentence-scoped model resolves.
- **What it would get wrong, over the whole violating population.** A floor of
  0.5775<!--claim:one_sense.pmc_oa.a2.biomedical.wrong_floor_correctness_pct_of_licensed:.4f--> % of
  licensed occurrences — the definition sites of the expansions A2 did *not* commit to, wrong by
  construction and needing no annotation — and a ceiling of
  9.62<!--claim:one_sense.pmc_oa.a2.biomedical.wrong_ceiling_correctness_pct_of_licensed:.2f--> %,
  which assumes every licensed occurrence of every multi-expansion short form except one carries the
  other reading. No document does that; it is a bound.
- **What it would get wrong where the ambiguity is real.** Multiply each class by its adjudicated
  genuine share and the projection is
  38.8<!--claim:one_sense.pmc_oa.a2_projected_genuine.genuine.projected_groups:.1f--> genuinely
  ambiguous groups —
  0.151<!--claim:one_sense.pmc_oa.a2_projected_genuine.genuine.projected_groups_pct_of_term_shaped_groups:.3f--> %
  of all roster-shaped groups, exact binomial interval
  0.040<!--claim:one_sense.pmc_oa.a2_projected_genuine.genuine.projected_groups_ci_low_pct_of_term_shaped_groups:.3f-->
  to
  0.577<!--claim:one_sense.pmc_oa.a2_projected_genuine.genuine.projected_groups_ci_high_pct_of_term_shaped_groups:.3f-->
  % on the adjudication draw alone. On licensed occurrences the genuine-ambiguity error floor is
  0.0214<!--claim:one_sense.pmc_oa.a2_projected_genuine.genuine.projected_wrong_floor_pct_of_licensed:.4f--> %
  and the ceiling
  0.355<!--claim:one_sense.pmc_oa.a2_projected_genuine.genuine.projected_wrong_ceiling_pct_of_licensed:.3f--> %,
  interval
  0.095<!--claim:one_sense.pmc_oa.a2_projected_genuine.genuine.projected_wrong_ceiling_ci_low_pct_of_licensed:.3f-->
  to
  1.308<!--claim:one_sense.pmc_oa.a2_projected_genuine.genuine.projected_wrong_ceiling_ci_high_pct_of_licensed:.3f--> %.
- **The rate A2 is measured against is zero, and that is the sharpest thing on this page.** The
  sentence-scoped mechanism A2 replaces does not answer *wrongly* at an out-of-sentence occurrence; it
  does not answer at all. So A2 does not trade a worse error rate for a better one. **It trades
  coverage for correctness against a comparator that is right by declining.**

### The finding was on nobody's list: A2's exposure is not ambiguity, it is amplification

One-sense-per-discourse holds on this corpus about as well as its advocates would claim. **What A2
would actually do is take the extractor's false positives and license them across a whole article.**

Projected the same way, the class whose second expansion is **not an expansion at all** covers
349.5<!--claim:one_sense.pmc_oa.a2_projected_genuine.artefact.projected_groups:.1f--> groups —
1.36<!--claim:one_sense.pmc_oa.a2_projected_genuine.artefact.projected_groups_pct_of_term_shaped_groups:.2f--> %
of roster-shaped groups, interval
0.989<!--claim:one_sense.pmc_oa.a2_projected_genuine.artefact.projected_groups_ci_low_pct_of_term_shaped_groups:.3f-->
to
1.956<!--claim:one_sense.pmc_oa.a2_projected_genuine.artefact.projected_groups_ci_high_pct_of_term_shaped_groups:.3f-->
%, and
8,311.1<!--claim:one_sense.pmc_oa.a2_projected_genuine.artefact.projected_licensed_occurrences:,.1f-->
licensed occurrences,
3.352<!--claim:one_sense.pmc_oa.a2_projected_genuine.artefact.projected_licensed_occurrences_pct:.3f--> %
of the total. **That is roughly nine times the genuinely ambiguous class on groups and nine times it
on occurrences.**

**It is exposure and not error, and the difference is stated because the measurement cannot close
it.** The label says one of a group's expansions is noise; it does not say *which* one came first, and
A2 commits to whichever did. The error is somewhere between zero and
3.211<!--claim:one_sense.pmc_oa.a2_projected_genuine.artefact.projected_wrong_ceiling_pct_of_licensed:.3f--> %
of licensed occurrences and nothing here locates it. What is not in doubt is the *shape*: today a
false definition is confined to its sentence, and under A2 it would be asserted for every later
occurrence in the article, with a provenance record saying where the licence came from. **For a
governance instrument that is a worse failure than an unresolved occurrence**, and it is the argument
against A2 that this measurement produces — not the one it was sent to look for.

### The verdict against the pre-registration, including the condition that was badly written

- **K1 does not fire.** Genuine ambiguity is
  0.151<!--claim:one_sense.pmc_oa.a2_projected_genuine.genuine.projected_groups_pct_of_term_shaped_groups:.3f--> %
  of groups against a `5` % kill line, and the interval's upper end is
  0.577<!--claim:one_sense.pmc_oa.a2_projected_genuine.genuine.projected_groups_ci_high_pct_of_term_shaped_groups:.3f--> %.
- **K2 does not fire**, on the genuine class: ceiling
  0.355<!--claim:one_sense.pmc_oa.a2_projected_genuine.genuine.projected_wrong_ceiling_pct_of_licensed:.3f--> %
  against a `10` % line. On the *whole* violating population the ceiling is
  9.62<!--claim:one_sense.pmc_oa.a2.biomedical.wrong_ceiling_correctness_pct_of_licensed:.2f--> %
  — see the bullet above for the figure that matters — and a reader who applied K2 to the pooled
  bound would find it inside a point of firing.
- **K4 and K5 do not fire.** The genuine rate is below `1` %, and the pooled violation rate is
  5.73<!--claim:one_sense.pmc_oa.resolver.biomedical.term_shaped.violation_pct:.2f--> % against a
  `15` % line.
- **K6, the clean-ship condition, is satisfied on its own terms.**
- **K3 fires, and K3 was a badly written condition.** It said A2 dies if its error floor exceeds the
  error rate of the mechanism it replaces. The mechanism it replaces turns out to have an error rate
  of exactly zero *because it declines*, so K3 fires on any error at all and could only have passed
  if A2 were perfect. **The pre-registration got the direction right and the comparator wrong**, and
  it is left standing rather than rewritten, because a kill condition edited after the run is not a
  kill condition.

**Six point predictions, graded, and three of them held.** Grading only the ones that failed would be
the same selection this page exists to refuse.

1. **The pooled rate: band held, central guess did not.** Predicted `2`–`7` % with a central guess of
   `4` %; it is
   5.73<!--claim:one_sense.pmc_oa.resolver.biomedical.term_shaped.violation_pct:.2f--> %.
2. **"One concept written twice" is the majority of violations: right, at about the predicted size.**
   Predicted `70` % of violations. The adjudicated projection puts that class at
   4.167<!--claim:one_sense.pmc_oa.a2_projected_genuine.variant.projected_groups_pct_of_term_shaped_groups:.3f--> %
   of all roster-shaped groups against a violating population of
   5.73<!--claim:one_sense.pmc_oa.resolver.biomedical.term_shaped.violation_pct:.2f--> % — about seven
   in ten. **The mechanical `surface` class alone would have said
   28.01<!--claim:one_sense.pmc_oa.resolver.biomedical.term_shaped.class_surface_pct_of_violations:.2f--> % and buried this**, which is
   the reason the ladder's residual class was adjudicated rather than reported as the answer.
3. **Occurrence weighting raises the rate, by the predicted factor: right.** Predicted strictly higher
   than the type rate by `1.5`x to `3`x. Licensed occurrences sitting under a multi-expansion short
   form are
   13.56<!--claim:one_sense.pmc_oa.a2.biomedical.licensed_occurrences_under_multi_expansion_groups_pct:.2f--> %
   of all licensed occurrences against a group rate of
   5.73<!--claim:one_sense.pmc_oa.resolver.biomedical.term_shaped.violation_pct:.2f--> %.
4. **The genuine-ambiguity error bounds: right, and by more than an order of magnitude.** Predicted
   floor below `1` % and ceiling below `6` %; measured
   0.0214<!--claim:one_sense.pmc_oa.a2_projected_genuine.genuine.projected_wrong_floor_pct_of_licensed:.4f--> %
   and
   0.355<!--claim:one_sense.pmc_oa.a2_projected_genuine.genuine.projected_wrong_ceiling_pct_of_licensed:.3f--> %.
5. **Rostered articles carrying a genuine ambiguity: wrong.** Predicted between `8` and `20` of the
   220<!--claim:one_sense.pmc_oa.sample.articles_with_a_roster:,--> rostered articles. The roster
   carries
   4<!--claim:one_sense.pmc_oa.roster.raw.case_folded.articles_with_a_violation:,--> collisions of any
   kind under its most generous keying and
   1<!--claim:one_sense.pmc_oa.roster.admitted.case_sensitive.articles_with_a_violation:,--> under the
   shipped rule.
6. **The concentration of the violating population: wrong by four times.** Predicted that the
   commonest violating short form would appear in fewer than `6` articles. Across
   1,163<!--claim:one_sense.pmc_oa.resolver.biomedical.term_shaped.distinct_violating_short_form_types:,-->
   distinct violating short forms the commonest is `OR`, in
   25<!--claim:one_sense.pmc_oa.resolver.biomedical.term_shaped.most_frequent_violating_short_form_documents:,-->
   of them.

**And the prediction the round most wanted to be right about was the furthest out.** The genuine rate
was predicted at `0.6`–`2.5` % of groups with a central guess of `1.2` %; it is
0.151<!--claim:one_sense.pmc_oa.a2_projected_genuine.genuine.projected_groups_pct_of_term_shaped_groups:.3f--> %
with an interval whose upper end is
0.577<!--claim:one_sense.pmc_oa.a2_projected_genuine.genuine.projected_groups_ci_high_pct_of_term_shaped_groups:.3f--> %,
so **the whole predicted band is excluded.** The artefact class, which is what this section ends on,
appears nowhere in the pre-registration at all.

### The instrument's own defects, measured rather than declared

**The shipped sentence splitter is quadratic in the length of the string it is handed.** This is not a
side note: A2 is a document-level feature and `Tokenizer.split_sentences` costs `O(n squared)` in
document size. Doubling the input roughly quadruples the time, at constant sentences-per-character:

```
bench/results.json, one_sense.pmc_oa.splitter_cost -- WALL CLOCK, UNARMED, one machine
CPython 3.13.4 on Windows AMD64. Per R18 the characters and sentences are the property of
the code and are gated; the seconds are the property of this runner and only the RATIO
between consecutive rows is read. A linear splitter shows a ratio near 2.

   characters   sentences   seconds   ratio to the row above
        6,700         100    0.0584   --
       13,400         200    0.2400   4.11
       26,800         400    0.9530   3.97
       53,600         800    3.8443   4.03
```

So this runner splits each **paragraph block** rather than each document, which makes the total linear
— 329,312<!--claim:one_sense.pmc_oa.sample.sentence_table.paragraph_blocks:,--> splitter calls
producing 638,975<!--claim:one_sense.pmc_oa.sample.sentence_table.sentences:,--> sentences over the
corpus — and is *also* the more faithful reading, because the extractor's own candidate window never
crosses a paragraph break either.

**That substitution was checked against the number it could move, not against an intermediate.** The
two splits never produce byte-equal span lists, by construction: chunking adds a boundary at every
blank line. What matters is whether the published coverage figure moves, so it is recomputed both ways
on a seeded sample of documents short enough for the quadratic arm to finish:
79.31<!--claim:one_sense.pmc_oa.splitter_agreement.coverage_pct_chunked_split:.2f--> % under the
chunked split against
79.26<!--claim:one_sense.pmc_oa.splitter_agreement.coverage_pct_whole_document_split:.2f--> % under
the whole-document split. **The sample is the short half of the corpus by construction** — the
whole-document arm is the one that does not finish on a long article — so nothing here says the two
agree as well on the long half.

**Turning the engine's own sentence capture on changes no pair**, on all
40<!--claim:one_sense.pmc_oa.splitter_agreement.documents_whose_pair_set_is_identical_with_capture_on:,-->
sampled documents, so the coverage figure is about the pair set that ships. The engine's attached
sentence is the one this runner assigns for
78.64<!--claim:one_sense.pmc_oa.splitter_agreement.definition_sentence_agreement_pct:.2f--> % of
definitions — the disagreement is the paragraph boundary, and the bullet above is what bounds its
effect.

### The gate that adjudicates this section, shown failing — and the hole it did not catch

R11 says a gate must be shown capable of failing where it runs. Six runs of
`python tools/check_claims.py`, one mutation at a time, each restored from bytes read before it and
md5-verified against a copy held outside the tree:

```
python tools/check_claims.py, six mutations to the section above, one at a time.
CPython 3.13.4 on win32; command output, not a benchmark measurement. Failures are
printed on stderr and carry the file and line; rc and "is the file named" do not move
with an edit above them.

  rc=0  control, unmutated                                      <file not named>
  rc=1  A  a cited value edited: 5.73 -> 9.99                    docs/EVALUATION.md named
  rc=1  B  that citation repointed at run id one_sense.nope.*    docs/EVALUATION.md named
  rc=1  C  prose line added: "... accuracy reached 99.94 % ..."  docs/EVALUATION.md named
  rc=0  D  prose line added: "Median latency ... 41 microseconds"  <file not named>
  rc=0  E  the same cited value put back inside a code span      <file not named>
  rc=1  F  a class count edited: 738 -> 739                      docs/EVALUATION.md named
```

**A, B, C and F are the gate working.** A wrong value, a dead run id, a bare accuracy percentage and
a wrong integer all turn the build red and name the line.

**D is D-060's latency blind spot, reproduced here rather than carried on that record's word.** `latency` is not in the gate's
arming vocabulary and a spelled-out `microseconds` is not in its unit vocabulary, so an invented
performance figure on this page would never be seen. That is why the splitter cost above is in a
fenced block with its provenance printed rather than in prose.

**E is not a reproduction of a known hole. It is a defect this section shipped and then found in
itself, and it is the most useful thing here.** Every figure in the section was drafted inside
backticks, because a code span looked like the tidy way to set a number. D-052 says a figure inside a
code span is invisible to the claims gate, and it is: with the spans in place, editing
`5.73` to `9.99` left the gate at **rc=0**, and a citation pointing at the wrong field entirely — the
pooled ceiling `9.62` cited against a run field holding `0.355` — was green. Eighty-eight citations
were decorative and every gate in the repository was passing. The spans were stripped, the mis-aimed
citation was repointed, and row E is what the section looked like before that. **A convention adopted
for typography silenced a gate across a whole section, and nothing but a deliberate mutation could
have told anybody.** The four figures quoted in this paragraph are code spans on purpose, which is
D-079's convention for a value quoted as a defect rather than asserted as a measurement — and it is
the same hole, used deliberately one paragraph after it was used by accident. **Counted rather than
left to be discovered: twenty-two figures in this section are still inside code spans and the gate
is silent about every one of them** — the eighteen pre-registered thresholds and predictions,
quoted from the fenced block above so that the grading below can name them, and the four values
quoted in this paragraph. Every other figure in the section cites a run
id, and a mutation to any of them reddens the build and names the line.

### What this does not establish

- **The roster is not a recall corpus and no absolute number off it is a claim about documents.**
  `bench/splits.toml` says of this corpus that every figure it backs should be a difference between
  two halves where the authors' declaration habits cancel. The roster figures here are absolute and
  they are absolute *about the roster*. The resolver figures do not use the roster at all.
- **One domain, and the convention may be the cause of the result.** Biomedicine rosters its
  abbreviations. A field whose authors have been made to compile their own abbreviation list has had
  exactly the intervention that would suppress within-document collisions. Prose nobody rosters — a
  regulation, a filing, a schema's documentation, which is what this library is *for* — has had no
  such pass, and **nothing here transfers to it.** The one-sense rate on a governed corpus is
  unmeasured and this round did not measure it.
- **The resolver instrument has no gold, and that is deliberate rather than a shortfall.** It measures
  what A2 must arbitrate, not what is true. It is also why the artefact class is visible at all: a
  gold-filtered population would have deleted the very failure this section ends on.
- **The adjudication is one annotator who wrote the ladder being adjudicated**, on
  200 groups of 1,471<!--claim:one_sense.pmc_oa.resolver.biomedical.term_shaped.groups_with_two_or_more_expansions:,-->, and every interval quoted is the sampling interval on that draw alone. It
  carries no uncertainty about the annotator and none about the extractor that supplied the
  population. A second reader would be the single largest improvement available to this section.
- **The `unclear` bucket is small and it is published rather than absorbed.**
  2<!--claim:one_sense.pmc_oa.audit.distinct.label_unclear:,--> of
  120<!--claim:one_sense.pmc_oa.audit.distinct.sample_size:,--> could not be decided from the two
  strings alone. A reader who moves both into `genuine` moves the projected genuine group count from
  38.8<!--claim:one_sense.pmc_oa.a2_projected_genuine.genuine.projected_groups:.1f--> to about
  fifty-one, which changes no verdict above.
- **Nothing here changes `extract()`.** This section measures the assumption a change would rest on
  and stops.

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

Expansion **is** measured, on the population this admission rule discards, in
[the section below](#does-a-governed-catalog-add-anything-on-a-real-schema-not-as-the-pooled-figure-asks-it).
The two must never be read as one number: this table scores cut placement with an empty catalog on
pairs that share a character stream, and that one scores catalog resolution on pairs that do not.

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

## Does a governed catalog add anything on a real schema? Not as the pooled figure asks it

Every figure in the table above is taken with an **empty** catalog, because the admission rule that
makes that table defensible forces one: a populated catalog rewrites `QTY` to `Quantity` and the two
strings stop sharing a character stream. Those figures measure cut placement and say nothing
whatever about what a governed vocabulary is worth — and that is the question
[`docs/POSITIONING.md`](POSITIONING.md#reversal-one-the-lead-is-wrong-if-a-catalog-is-worth-nothing-on-a-real-schema)'s
first reversal condition rests on. The August 2026 audit measured it once, un-gated, on a
portal-disjoint split of Socrata, found a voted catalog scoring no better than an empty one, and
recorded the structural cause as *real schemas are already spelled out*
([`docs/AUDIT-2026-08.md`](AUDIT-2026-08.md#1-does-a-governed-catalog-add-anything-on-a-real-schema)).

`bench/run_governed_catalog.py` re-runs that comparison under the current harness. **The pooled
result reproduces and the reading of it does not survive decomposition.** The voted catalog does
lose — in 79<!--claim:governed_catalog.socrata.sweep.cells_where_voted_loses_pooled:,--> of
80<!--claim:governed_catalog.socrata.sweep.cells_run:,--> catalog configurations — and it loses
*entirely* on pairs where a catalog can only do damage. On the pairs where a catalog is the only
instrument there is it cannot lose — the empty arm is zero there by construction — so the readable
figure is that it *wins* in
51<!--claim:governed_catalog.socrata.sweep.cells_where_voted_beats_empty_live:,--> of the same
80<!--claim:governed_catalog.socrata.sweep.cells_run:,--> and recovers nothing at all in the other
29<!--claim:governed_catalog.socrata.sweep.cells_where_voted_ties_live:,-->.

### Why this is a second runner, and how it is still one scorer

The gold runner's admission rule — *the caption's alphanumerics case-fold equal to the identifier's*
— is the exact complement of the population this question lives in. A pair a catalog could help is a
pair whose caption is **not** the identifier's characters re-cut, so applying that rule here admits
an empty population and the answer is `0/0`. It cannot be reused, and the runner's docstring says so
rather than quietly widening it, because a rule loosened after seeing which direction it moves the
result is not a rule.

The **scorer** is reused, and the reuse is a measurement rather than a claim. This runner compares
the case-folded tuple of alphanumeric words; the gold runner compares a set of integer cut positions
over a shared character stream. On a shared stream those are the same statement, and
`governed_catalog.socrata.scorer_agreement` re-scores every pair the gold runner admits, both ways,
to check that they are:

| Metric | Admitted pairs | exact % | Verdicts disagreeing |
|---|---:|---:|---:|
| `run_governed_gold.cuts` equality — the gated segmentation metric | 26,536<!--claim:governed_catalog.socrata.scorer_agreement.admitted_pairs:,--> | 91.37<!--claim:governed_catalog.socrata.scorer_agreement.cut_set_exact_pct:.2f--> | — |
| `run_governed_catalog.phrase_words` equality — this section's metric | 26,536<!--claim:governed_catalog.socrata.scorer_agreement.admitted_pairs:,--> | 91.37<!--claim:governed_catalog.socrata.scorer_agreement.word_tuple_exact_pct:.2f--> | 0<!--claim:governed_catalog.socrata.scorer_agreement.verdicts_disagreeing:,--> |

The second row reproduces `governed_gold.socrata.columns.all.exact_pct` to the digit. Two scorers
for one question is how a project acquires a number it later cannot compare; this is one scorer with
a published identity, and `tests/test_governed_catalog.py` pins the identity as a property rather
than as a coincidence of this corpus.

### The census: how much of a real schema needs a catalog at all

This decides how to read everything below it, and it has no arms, no thresholds and nothing chosen.
Every column pair is classified once by comparing the case-folded alphanumerics of identifier and
caption. Same corpus, same cache and same fetch as the segmentation table above.

| Population | What it is | Distinct pairs | % | Occurrences | % |
|---|---|---:|---:|---:|---:|
| `identical` | the caption re-cuts the identifier and nothing else — **a catalog can only do damage** | 59,978<!--claim:governed_catalog.socrata.census.subsets.identical.pairs:,--> | **76.53<!--claim:governed_catalog.socrata.census.subsets.identical.pairs_pct:.2f-->** | 124,046<!--claim:governed_catalog.socrata.census.subsets.identical.occurrences:,--> | 79.90<!--claim:governed_catalog.socrata.census.subsets.identical.occurrences_pct:.2f--> |
| `expansion` | the identifier's characters are a subsequence of a longer caption | 7,911<!--claim:governed_catalog.socrata.census.subsets.expansion.pairs:,--> | 10.09<!--claim:governed_catalog.socrata.census.subsets.expansion.pairs_pct:.2f--> | 13,381<!--claim:governed_catalog.socrata.census.subsets.expansion.occurrences:,--> | 8.62<!--claim:governed_catalog.socrata.census.subsets.expansion.occurrences_pct:.2f--> |
| `expansion_strict` | `expansion`, and every token is an abbreviation of its own caption word | 955<!--claim:governed_catalog.socrata.census.subsets.expansion_strict.pairs:,--> | 1.22<!--claim:governed_catalog.socrata.census.subsets.expansion_strict.pairs_pct:.2f--> | 1,718<!--claim:governed_catalog.socrata.census.subsets.expansion_strict.occurrences:,--> | 1.11<!--claim:governed_catalog.socrata.census.subsets.expansion_strict.occurrences_pct:.2f--> |
| `other` | reordered, annotated, or a caption that *abbreviates* — `unit_number` captioned `Unit Num` | 9,525<!--claim:governed_catalog.socrata.census.subsets.other.pairs:,--> | 12.15<!--claim:governed_catalog.socrata.census.subsets.other.pairs_pct:.2f--> | 16,116<!--claim:governed_catalog.socrata.census.subsets.other.occurrences:,--> | 10.38<!--claim:governed_catalog.socrata.census.subsets.other.occurrences_pct:.2f--> |
| **LIVE** | both `expansion` rows: **the only place the question is live** | **8,866<!--claim:governed_catalog.socrata.census.live_pairs:,-->** | **11.31<!--claim:governed_catalog.socrata.census.live_pairs_pct:.2f-->** | **15,099<!--claim:governed_catalog.socrata.census.live_occurrences:,-->** | **9.72<!--claim:governed_catalog.socrata.census.live_occurrences_pct:.2f-->** |
| ALL | | 78,369<!--claim:governed_catalog.socrata.census.distinct_pairs:,--> | | 155,261<!--claim:governed_catalog.socrata.census.occurrences:,--> | |

**The audit's `87.3 %` does not reproduce, and the correction goes against us.** On this corpus the
already-unabbreviated share is
76.53<!--claim:governed_catalog.socrata.census.unabbreviated_pairs_pct:.2f--> % of distinct pairs and
79.90<!--claim:governed_catalog.socrata.census.unabbreviated_occurrences_pct:.2f--> % of column
occurrences — a smaller majority than the audit recorded, so *more* of the corpus is live than that
figure implied, not less. The audit's number was taken on a different walk of a live catalog and is
not re-derivable; this one is, from the cache the segmentation table was taken from. The audit's
companion noise figure moves the same way: of the
18,391<!--claim:governed_catalog.socrata.census.non_identical_pairs:,--> pairs whose caption is not the
identifier re-cut, 82.86<!--claim:governed_catalog.socrata.census.token_word_count_mismatch_pct:.2f--> %
have a token count that does not match the caption's word count, against the audit's `78.9 %`.

Inside `expansion_strict` the alignment is well defined, which yields the atoms this question is
really about: 1,100<!--claim:governed_catalog.socrata.census.abbreviated_tokens:,--> **abbreviated
tokens** — token positions where the identifier's token differs from the caption's word, so a
catalog is the only thing that could ever produce the right answer.

### The comparison, decomposed

Portal-disjoint, by the same digest the segmentation table's robustness halves use, so no portal
casts a training vote and is then scored. Two folds, reported separately and never pooled. `E-only`
and `V-only` are the paired counts: pairs only the empty arm got right, and pairs only the voted arm
got right.

**`voted`** is the audit's catalog reconstructed — every aligned vote counts, a token must be seen
twice, a simple majority wins:

| Fold | Subset | Pairs | empty % | voted % | delta | catalog fired | E-only | V-only |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| `fold_ab` | all | 31,348<!--claim:governed_catalog.socrata.voted.fold_ab.all.pairs:,--> | **65.62<!--claim:governed_catalog.socrata.voted.fold_ab.all.empty_exact_pct:.2f-->** | **65.32<!--claim:governed_catalog.socrata.voted.fold_ab.all.voted_exact_pct:.2f-->** | -0.31<!--claim:governed_catalog.socrata.voted.fold_ab.all.delta_points:.2f--> | 168<!--claim:governed_catalog.socrata.voted.fold_ab.all.catalog_fired_pairs:,--> | 97<!--claim:governed_catalog.socrata.voted.fold_ab.all.empty_only_correct:,--> | 0<!--claim:governed_catalog.socrata.voted.fold_ab.all.voted_only_correct:,--> |
| | identical | 24,854<!--claim:governed_catalog.socrata.voted.fold_ab.identical.pairs:,--> | 82.77<!--claim:governed_catalog.socrata.voted.fold_ab.identical.empty_exact_pct:.2f--> | 82.38<!--claim:governed_catalog.socrata.voted.fold_ab.identical.voted_exact_pct:.2f--> | -0.39<!--claim:governed_catalog.socrata.voted.fold_ab.identical.delta_points:.2f--> | 105<!--claim:governed_catalog.socrata.voted.fold_ab.identical.catalog_fired_pairs:,--> | 97<!--claim:governed_catalog.socrata.voted.fold_ab.identical.empty_only_correct:,--> | 0<!--claim:governed_catalog.socrata.voted.fold_ab.identical.voted_only_correct:,--> |
| | **live** | 3,276<!--claim:governed_catalog.socrata.voted.fold_ab.live.pairs:,--> | 0.00<!--claim:governed_catalog.socrata.voted.fold_ab.live.empty_exact_pct:.2f--> | 0.00<!--claim:governed_catalog.socrata.voted.fold_ab.live.voted_exact_pct:.2f--> | 0.00<!--claim:governed_catalog.socrata.voted.fold_ab.live.delta_points:.2f--> | 23<!--claim:governed_catalog.socrata.voted.fold_ab.live.catalog_fired_pairs:,--> | 0<!--claim:governed_catalog.socrata.voted.fold_ab.live.empty_only_correct:,--> | 0<!--claim:governed_catalog.socrata.voted.fold_ab.live.voted_only_correct:,--> |
| `fold_ba` | all | 49,308<!--claim:governed_catalog.socrata.voted.fold_ba.all.pairs:,--> | **63.10<!--claim:governed_catalog.socrata.voted.fold_ba.all.empty_exact_pct:.2f-->** | **62.53<!--claim:governed_catalog.socrata.voted.fold_ba.all.voted_exact_pct:.2f-->** | -0.57<!--claim:governed_catalog.socrata.voted.fold_ba.all.delta_points:.2f--> | 2,516<!--claim:governed_catalog.socrata.voted.fold_ba.all.catalog_fired_pairs:,--> | 283<!--claim:governed_catalog.socrata.voted.fold_ba.all.empty_only_correct:,--> | 1<!--claim:governed_catalog.socrata.voted.fold_ba.all.voted_only_correct:,--> |
| | identical | 37,323<!--claim:governed_catalog.socrata.voted.fold_ba.identical.pairs:,--> | 83.37<!--claim:governed_catalog.socrata.voted.fold_ba.identical.empty_exact_pct:.2f--> | 82.61<!--claim:governed_catalog.socrata.voted.fold_ba.identical.voted_exact_pct:.2f--> | -0.76<!--claim:governed_catalog.socrata.voted.fold_ba.identical.delta_points:.2f--> | 1,953<!--claim:governed_catalog.socrata.voted.fold_ba.identical.catalog_fired_pairs:,--> | 283<!--claim:governed_catalog.socrata.voted.fold_ba.identical.empty_only_correct:,--> | 0<!--claim:governed_catalog.socrata.voted.fold_ba.identical.voted_only_correct:,--> |
| | **live** | 5,625<!--claim:governed_catalog.socrata.voted.fold_ba.live.pairs:,--> | 0.00<!--claim:governed_catalog.socrata.voted.fold_ba.live.empty_exact_pct:.2f--> | 0.02<!--claim:governed_catalog.socrata.voted.fold_ba.live.voted_exact_pct:.2f--> | 0.02<!--claim:governed_catalog.socrata.voted.fold_ba.live.delta_points:.2f--> | 434<!--claim:governed_catalog.socrata.voted.fold_ba.live.catalog_fired_pairs:,--> | 0<!--claim:governed_catalog.socrata.voted.fold_ba.live.empty_only_correct:,--> | 1<!--claim:governed_catalog.socrata.voted.fold_ba.live.voted_only_correct:,--> |

Read the `E-only` and `V-only` columns before the deltas. On `fold_ab` the catalog broke
97<!--claim:governed_catalog.socrata.voted.fold_ab.identical.empty_only_correct:,--> already-correct
pairs and fixed
0<!--claim:governed_catalog.socrata.voted.fold_ab.identical.voted_only_correct:,-->; on `fold_ba`,
283<!--claim:governed_catalog.socrata.voted.fold_ba.identical.empty_only_correct:,--> broken and
0<!--claim:governed_catalog.socrata.voted.fold_ba.identical.voted_only_correct:,--> fixed. **The whole
of the pooled loss is damage to pairs that needed no catalog.** On the live subset the same catalog
fired on only 23<!--claim:governed_catalog.socrata.voted.fold_ab.live.catalog_fired_pairs:,--> and
434<!--claim:governed_catalog.socrata.voted.fold_ba.live.catalog_fired_pairs:,--> pairs — operating rule
12's firing count, and it is what makes the live deltas of
0.00<!--claim:governed_catalog.socrata.voted.fold_ab.live.delta_points:.2f--> and
0.02<!--claim:governed_catalog.socrata.voted.fold_ba.live.delta_points:.2f--> points a measurement of
almost nothing rather than a null result.

**And the confinement of the loss is forced rather than incidental.** The empty arm's output has
the identifier's alphanumerics, so it can be exactly right only on `identical` — which means
`empty_only_correct` is structurally zero on every other subset, for **every** catalog in the grid
and not only for these two. A voted catalog cannot lose a pair outside `identical` at any setting.
That is a derivation from the classification, and it is why the pooled figure is a damage figure by
construction rather than by accident.

**`eager`** is the catalog arm at its best: of the
80<!--claim:governed_catalog.socrata.sweep.cells_run:,--> configurations swept, the one that recovers
most of the live subset. It is selected *after* seeing the sweep and the entry says so in its own
`chosen_as` field.

| Fold | Subset | Pairs | empty % | voted % | delta | catalog fired | E-only | V-only |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| `fold_ab` | all | 31,348<!--claim:governed_catalog.socrata.eager.fold_ab.all.pairs:,--> | **65.62<!--claim:governed_catalog.socrata.eager.fold_ab.all.empty_exact_pct:.2f-->** | **47.84<!--claim:governed_catalog.socrata.eager.fold_ab.all.voted_exact_pct:.2f-->** | -17.79<!--claim:governed_catalog.socrata.eager.fold_ab.all.delta_points:.2f--> | 11,171<!--claim:governed_catalog.socrata.eager.fold_ab.all.catalog_fired_pairs:,--> | 5,616<!--claim:governed_catalog.socrata.eager.fold_ab.all.empty_only_correct:,--> | 40<!--claim:governed_catalog.socrata.eager.fold_ab.all.voted_only_correct:,--> |
| | identical | 24,854<!--claim:governed_catalog.socrata.eager.fold_ab.identical.pairs:,--> | 82.77<!--claim:governed_catalog.socrata.eager.fold_ab.identical.empty_exact_pct:.2f--> | 60.18<!--claim:governed_catalog.socrata.eager.fold_ab.identical.voted_exact_pct:.2f--> | **-22.60<!--claim:governed_catalog.socrata.eager.fold_ab.identical.delta_points:.2f-->** | 8,282<!--claim:governed_catalog.socrata.eager.fold_ab.identical.catalog_fired_pairs:,--> | 5,616<!--claim:governed_catalog.socrata.eager.fold_ab.identical.empty_only_correct:,--> | 0<!--claim:governed_catalog.socrata.eager.fold_ab.identical.voted_only_correct:,--> |
| | **live** | 3,276<!--claim:governed_catalog.socrata.eager.fold_ab.live.pairs:,--> | 0.00<!--claim:governed_catalog.socrata.eager.fold_ab.live.empty_exact_pct:.2f--> | **1.22<!--claim:governed_catalog.socrata.eager.fold_ab.live.voted_exact_pct:.2f-->** | **1.22<!--claim:governed_catalog.socrata.eager.fold_ab.live.delta_points:.2f-->** | 925<!--claim:governed_catalog.socrata.eager.fold_ab.live.catalog_fired_pairs:,--> | 0<!--claim:governed_catalog.socrata.eager.fold_ab.live.empty_only_correct:,--> | 40<!--claim:governed_catalog.socrata.eager.fold_ab.live.voted_only_correct:,--> |
| | `expansion_strict` | 407<!--claim:governed_catalog.socrata.eager.fold_ab.expansion_strict.pairs:,--> | 0.00<!--claim:governed_catalog.socrata.eager.fold_ab.expansion_strict.empty_exact_pct:.2f--> | **9.83<!--claim:governed_catalog.socrata.eager.fold_ab.expansion_strict.voted_exact_pct:.2f-->** | **9.83<!--claim:governed_catalog.socrata.eager.fold_ab.expansion_strict.delta_points:.2f-->** | 153<!--claim:governed_catalog.socrata.eager.fold_ab.expansion_strict.catalog_fired_pairs:,--> | 0<!--claim:governed_catalog.socrata.eager.fold_ab.expansion_strict.empty_only_correct:,--> | 40<!--claim:governed_catalog.socrata.eager.fold_ab.expansion_strict.voted_only_correct:,--> |
| `fold_ba` | all | 49,308<!--claim:governed_catalog.socrata.eager.fold_ba.all.pairs:,--> | **63.10<!--claim:governed_catalog.socrata.eager.fold_ba.all.empty_exact_pct:.2f-->** | **50.18<!--claim:governed_catalog.socrata.eager.fold_ba.all.voted_exact_pct:.2f-->** | -12.92<!--claim:governed_catalog.socrata.eager.fold_ba.all.delta_points:.2f--> | 15,009<!--claim:governed_catalog.socrata.eager.fold_ba.all.catalog_fired_pairs:,--> | 6,408<!--claim:governed_catalog.socrata.eager.fold_ba.all.empty_only_correct:,--> | 36<!--claim:governed_catalog.socrata.eager.fold_ba.all.voted_only_correct:,--> |
| | identical | 37,323<!--claim:governed_catalog.socrata.eager.fold_ba.identical.pairs:,--> | 83.37<!--claim:governed_catalog.socrata.eager.fold_ba.identical.empty_exact_pct:.2f--> | 66.20<!--claim:governed_catalog.socrata.eager.fold_ba.identical.voted_exact_pct:.2f--> | **-17.17<!--claim:governed_catalog.socrata.eager.fold_ba.identical.delta_points:.2f-->** | 9,980<!--claim:governed_catalog.socrata.eager.fold_ba.identical.catalog_fired_pairs:,--> | 6,408<!--claim:governed_catalog.socrata.eager.fold_ba.identical.empty_only_correct:,--> | 0<!--claim:governed_catalog.socrata.eager.fold_ba.identical.voted_only_correct:,--> |
| | **live** | 5,625<!--claim:governed_catalog.socrata.eager.fold_ba.live.pairs:,--> | 0.00<!--claim:governed_catalog.socrata.eager.fold_ba.live.empty_exact_pct:.2f--> | **0.64<!--claim:governed_catalog.socrata.eager.fold_ba.live.voted_exact_pct:.2f-->** | **0.64<!--claim:governed_catalog.socrata.eager.fold_ba.live.delta_points:.2f-->** | 2,780<!--claim:governed_catalog.socrata.eager.fold_ba.live.catalog_fired_pairs:,--> | 0<!--claim:governed_catalog.socrata.eager.fold_ba.live.empty_only_correct:,--> | 36<!--claim:governed_catalog.socrata.eager.fold_ba.live.voted_only_correct:,--> |
| | `expansion_strict` | 552<!--claim:governed_catalog.socrata.eager.fold_ba.expansion_strict.pairs:,--> | 0.00<!--claim:governed_catalog.socrata.eager.fold_ba.expansion_strict.empty_exact_pct:.2f--> | **6.52<!--claim:governed_catalog.socrata.eager.fold_ba.expansion_strict.voted_exact_pct:.2f-->** | **6.52<!--claim:governed_catalog.socrata.eager.fold_ba.expansion_strict.delta_points:.2f-->** | 266<!--claim:governed_catalog.socrata.eager.fold_ba.expansion_strict.catalog_fired_pairs:,--> | 0<!--claim:governed_catalog.socrata.eager.fold_ba.expansion_strict.empty_only_correct:,--> | 36<!--claim:governed_catalog.socrata.eager.fold_ba.expansion_strict.voted_only_correct:,--> |

**The two effects live on disjoint populations and the damaged one is about seven times larger.**
A catalog aggressive enough to recover
9.83<!--claim:governed_catalog.socrata.eager.fold_ab.expansion_strict.voted_exact_pct:.2f--> % of the
cleanest live pairs moves the pairs that needed nothing by
-22.60<!--claim:governed_catalog.socrata.eager.fold_ab.identical.delta_points:.2f--> points. That, and not "a catalog adds nothing", is what the pooled figure is made of.

### The atoms: the empty catalog's zero there is a derivation, not a measurement

On the abbreviated tokens inside `expansion_strict` — the token positions where the identifier's
token differs from the caption's word — the empty catalog is right
0<!--claim:governed_catalog.socrata.eager.fold_ab.abbreviated_tokens.empty_correct:,--> times out of
486<!--claim:governed_catalog.socrata.eager.fold_ab.abbreviated_tokens.tokens:,--> on one fold and
0<!--claim:governed_catalog.socrata.eager.fold_ba.abbreviated_tokens.empty_correct:,--> out of
618<!--claim:governed_catalog.socrata.eager.fold_ba.abbreviated_tokens.tokens:,--> on the other. **That
zero is arithmetic and this page will not sell it as evidence**: an empty catalog passes every token
through, so its output's alphanumerics are the identifier's, and the gold's are not. It is printed
because it is the positive control on the harness — a run that produced a non-zero there would be
broken in a way no delta would reveal — and `tests/test_governed_catalog.py` proves it rather than
observing it.

What is *not* arithmetic is the other column:

| Fold | Abbreviated tokens | empty correct | `voted` correct | `eager` correct | `eager` % |
|---|---:|---:|---:|---:|---:|
| `fold_ab` | 486<!--claim:governed_catalog.socrata.eager.fold_ab.abbreviated_tokens.tokens:,--> | 0<!--claim:governed_catalog.socrata.eager.fold_ab.abbreviated_tokens.empty_correct:,--> | 0<!--claim:governed_catalog.socrata.voted.fold_ab.abbreviated_tokens.voted_correct:,--> | 60<!--claim:governed_catalog.socrata.eager.fold_ab.abbreviated_tokens.voted_correct:,--> | **12.35<!--claim:governed_catalog.socrata.eager.fold_ab.abbreviated_tokens.voted_correct_pct:.2f-->** |
| `fold_ba` | 618<!--claim:governed_catalog.socrata.eager.fold_ba.abbreviated_tokens.tokens:,--> | 0<!--claim:governed_catalog.socrata.eager.fold_ba.abbreviated_tokens.empty_correct:,--> | 1<!--claim:governed_catalog.socrata.voted.fold_ba.abbreviated_tokens.voted_correct:,--> | 57<!--claim:governed_catalog.socrata.eager.fold_ba.abbreviated_tokens.voted_correct:,--> | **9.22<!--claim:governed_catalog.socrata.eager.fold_ba.abbreviated_tokens.voted_correct_pct:.2f-->** |

A catalog inferred from the corpus itself recovers about a tenth of the atoms an empty catalog
cannot touch at all. That is a small number, it is a floor rather than an estimate, and it is the
first non-zero anybody has measured on the population where this question is live — the audit's
figures were pooled over a population that is mostly not live at all.

### The sweep, and the null control

Quoting a maximum out of a sweep is only honest if the whole sweep is on the record, so the whole
sweep is on the record at `governed_catalog.socrata.sweep.cells`: five harvesting rules, four
`min_votes` settings, two `min_share` settings, both folds.

```
python bench/run_governed_catalog.py            -- command output, not a benchmark measurement
                                                -- every cell is saved; these are counts over them

  sweep: 80 cells, counted on pair counts and not on a rounded delta.
    pooled : voted wins 0, loses 79, ties 1 (1 of the ties have an empty catalog)
    live   : voted wins 51, loses 0, ties 29
  null control fold_ab: delta 0.0 points, fired 0
  null control fold_ba: delta 0.0 points, fired 0
```

The direction never changes. The voted catalog beats the empty catalog on the pooled figure in
0<!--claim:governed_catalog.socrata.sweep.cells_where_voted_beats_empty_pooled:,--> of
80<!--claim:governed_catalog.socrata.sweep.cells_run:,--> cells and loses in
79<!--claim:governed_catalog.socrata.sweep.cells_where_voted_loses_pooled:,-->; the single tie is the one
cell whose catalog has no acting rows at all, which is the empty arm under another name. On the live
subset it wins 51<!--claim:governed_catalog.socrata.sweep.cells_where_voted_beats_empty_live:,--> and
loses 0<!--claim:governed_catalog.socrata.sweep.cells_where_voted_loses_live:,--> — which is
arithmetic rather than evidence, because the empty arm is zero there by construction — while
recovering nothing at all in
29<!--claim:governed_catalog.socrata.sweep.cells_where_voted_ties_live:,-->. The worst pooled cost
anywhere in the grid is
-27.90<!--claim:governed_catalog.socrata.sweep.pooled_delta_points_worst:.2f--> points and the best
token-level recovery anywhere in it is
12.35<!--claim:governed_catalog.socrata.sweep.abbreviated_tokens_voted_correct_pct_best:.2f--> %.

The null control is the harness scored against itself: an empty catalog against an empty catalog,
0.00<!--claim:governed_catalog.socrata.null_control.fold_ab.delta_points:.2f--> points and
0<!--claim:governed_catalog.socrata.null_control.fold_ab.catalog_fired_pairs:,--> firings on one fold,
0.00<!--claim:governed_catalog.socrata.null_control.fold_ba.delta_points:.2f--> and
0<!--claim:governed_catalog.socrata.null_control.fold_ba.catalog_fired_pairs:,--> on the other. A harness
that reported a difference between an arm and itself would make every number above a coincidence.

### What this settles, and what it does not

**Settled:** the audit's pooled comparison is not a measurement of what a catalog is worth. It is a
measurement of what a catalog costs on the
76.53<!--claim:governed_catalog.socrata.census.subsets.identical.pairs_pct:.2f--> % of pairs that need no
catalog, and that population outweighs the live one about seven to one. Any catalog aggressive
enough to reach the live subset destroys the pooled figure; any catalog cautious enough to protect
the pooled figure never fires on the live subset. **The pooled metric cannot answer this question at
any setting in the grid**, which is a stronger statement than the audit's and it points the other
way.

**Not settled:** whether a *real* glossary helps. Every catalog measured here is inferred by this
harness from labels of the very kind being scored, exactly as the audit's was, and the best of them
reaches about a tenth of the atoms. That is a floor on a real catalog, not an estimate of one, and
nothing public closes the gap — which is the whole content of
[`docs/POSITIONING.md`](POSITIONING.md#reversal-one-the-lead-is-wrong-if-a-catalog-is-worth-nothing-on-a-real-schema)'s
first reversal condition and the reason it asks for one organisation's glossary rather than for more
work in this repository.

### The gates that adjudicate this section, shown failing

Operating rule 11: a gate must be demonstrated capable of failing where it runs, by mutation, with
the failure captured. Seven mutations, one at a time, each file restored from bytes read before the
first mutation and md5-verified.

```
python tools/check_claims.py                 -- command output, not a benchmark measurement
python -m pytest tests/test_governed_catalog.py
CPython 3.13.4 on win32. One mutation applied at a time, the gate run, the file restored.

  rc=0  control, unmutated                                     claims gate
  rc=0  control, unmutated                                     suite
  rc=1  A  a cited value edited: 76.53 -> 99.99                docs/POSITIONING.md
  rc=1  B  that citation repointed at governed_catalog.socrata.nope    docs/POSITIONING.md
  rc=1  C  a bare accuracy percentage added to the census head docs/EVALUATION.md
  rc=1  D  scorer mutated: phrase_words stops case-folding     bench/run_governed_catalog.py
  rc=1  E  classifier mutated: nothing can reach the expansion buckets bench/run_governed_catalog.py
  rc=1  F  Cell.as_dict stops publishing the raw counts        bench/run_governed_catalog.py
  rc=1  G  identity rows emitted as catalog rows after all     bench/run_governed_catalog.py
```

**Both controls are green and every mutation is red**, which is the property the count is worth
reading for. `D` through `G` are the four judgements in this harness that a reader cannot check by
eye — the metric, the classification, the tally, and what counts as a catalog row — and each of them
turns the suite red on its own. This is a developer machine, which is exactly the environment
[`docs/GATES.md`](GATES.md) says does not satisfy rule 11; the register's in-situ count is unchanged
by this block.

### How this fails

**The gold is a publisher's caption, and on the live subset it is worse gold than on the
segmentation table.** There, the admission rule guaranteed the two strings were the same characters.
Here nothing guarantees that the caption is an *expansion* of the identifier rather than a different
name for the same column, and `expansion` is a character-subsequence test that is necessary for that
and not sufficient. `expansion_strict` is tighter and is only
1.22<!--claim:governed_catalog.socrata.census.subsets.expansion_strict.pairs_pct:.2f--> % of the corpus.

**This round selected on this corpus, and `bench/splits.toml` says the opposite.** That file declares
`socrata` `contaminated = false`, and the reason it gives is that the miss decomposition was
published but "nothing was selected on it: the runner has no thresholds, no configuration and no arms
to choose between." This runner has all three, and it quotes a maximum over a grid. Every entry it
writes carries `selection_on_this_corpus = true`. Whether the manifest entry should still read
`contaminated = false`, and whether `governed_gold.socrata.*` is still held-out evidence, is a
question for whoever owns that file. It is reported here and deliberately not fixed here.

**The catalog is circular, and the split moves the circularity rather than removing it.** Rows are
voted from labels of the same kind as the labels being scored. The portal-disjoint split means no
portal trains a catalog and is then scored by it, so the circularity is at the corpus level rather
than at the pair level — which is the most a public substitute can offer and is not the same as
being non-circular.

**The two folds are not two independent estimates of one number.** They are two different catalogs
on two different populations, reported side by side because a portal-disjoint split makes them
comparable, and never pooled. Where they disagree — `fold_ab` recovers
12.35<!--claim:governed_catalog.socrata.eager.fold_ab.abbreviated_tokens.voted_correct_pct:.2f--> % of the
atoms and `fold_ba`
9.22<!--claim:governed_catalog.socrata.eager.fold_ba.abbreviated_tokens.voted_correct_pct:.2f--> % — the
spread is the honest width of this measurement, and there are two points in it.

**Nothing here transfers to a schema written in UPPER_SNAKE.** The shape census on the segmentation
table above holds for this corpus too: it is `snake_lower` and `flat_lower`, and the shape the
package's own documentation is built around does not appear in it.

## What dominates the governed hot path: provenance, and it is not close

Mandate III lists five optimisations for the governed subsystem — memoisation, lazy provenance, an
automaton for the tokenizer, free-threading, and a streaming batch API — and then says plainly that
none of them is worth building until it is known what dominates. **This section is that measurement
and nothing else. No optimisation was made, and no line of `src/acronymkit/` was touched.**

The runner is [`bench/run_governed_perf.py`](../bench/run_governed_perf.py); the runs are
`governed_perf.*`; the tests that pin the instrument are `tests/test_governed_perf_runner.py`.

### First: the two corpus sizes this work was handed are claims, and one of them has no corpus

The brief named a Socrata corpus of
164,652<!--claim:governed_perf.inherited_counts.socrata_pairs_claimed:,--> pairs and an identifier
corpus of 107,012<!--claim:governed_perf.inherited_counts.identifier_corpus_claimed:,--> names.
Both come from [`docs/AUDIT-2026-08.md`](AUDIT-2026-08.md), neither population was ever saved, and
they were quoted onward without either being re-derived. Re-derived here, as
`governed_perf.inherited_counts`:

- **The Socrata figure does not hold on this tree, and it is short by
  9,380<!--claim:governed_perf.inherited_counts.socrata_pairs_shortfall:,--> rows.** The cached fetch
  holds 155,272<!--claim:governed_perf.inherited_counts.socrata_pairs_measured:,--> pairs, of which
  69,682<!--claim:governed_perf.inherited_counts.socrata_distinct_identifiers:,--> are distinct
  identifiers. [`docs/SOURCING.md`](SOURCING.md) and D-074 already record the same disagreement from
  the other direction — the audit's `87.3` share does not reproduce either — so this is the third
  independent re-derivation of one un-saved population, and all three land away from the audit.
- **The `107,012`-identifier corpus is not reconstructible here at all**, and that is a stronger
  statement than "the number is different". The audit says it spanned
  8<!--claim:governed_perf.inherited_counts.identifier_corpus_sources_claimed:,--> sources including
  `fhir` and `openfda`;
  2<!--claim:governed_perf.inherited_counts.identifier_corpus_sources_present:,--> of those eight are
  in this tree, there is no fetcher for the others anywhere in `tools/`, and no corpus in
  `bench/splits.toml` is declared at that size. The closest object this repository can build is the
  union of the two identifier populations it does hold —
  137,720<!--claim:governed_perf.inherited_counts.identifier_corpus_best_reconstruction:,--> distinct
  identifiers — which is **a different population, not a reconstruction of that one**.

So the measurements below are taken on the two corpora that exist, at the sizes they actually are,
and every entry records which cache file it read.

### The distinct ratio, which is the whole ceiling of the memoisation workstream

One command, and it needs no timing at all: `python bench/run_governed_perf.py --only census`. A memo
cannot be worth more than the share of work that repeats, and the share of work that repeats is a
property of the corpus rather than of the code.

| | Socrata | SEC XBRL | fixture schema |
|---|---:|---:|---:|
| identifiers | 155,272<!--claim:governed_perf.socrata.census.identifiers:,--> | 90,655<!--claim:governed_perf.sec_xbrl.census.identifiers:,--> | 20,000<!--claim:governed_perf.fixture_schema.census.identifiers:,--> |
| distinct identifiers, share | 44.88<!--claim:governed_perf.socrata.census.distinct_identifiers_pct:.2f--> % | 75.05<!--claim:governed_perf.sec_xbrl.census.distinct_identifiers_pct:.2f--> % | 100.00<!--claim:governed_perf.fixture_schema.census.distinct_identifiers_pct:.2f--> % |
| token occurrences | 423,544<!--claim:governed_perf.socrata.census.token_occurrences:,--> | 655,281<!--claim:governed_perf.sec_xbrl.census.token_occurrences:,--> | 321,384<!--claim:governed_perf.fixture_schema.census.token_occurrences:,--> |
| distinct tokens | 24,536<!--claim:governed_perf.socrata.census.distinct_tokens:,--> | 6,601<!--claim:governed_perf.sec_xbrl.census.distinct_tokens:,--> | 117<!--claim:governed_perf.fixture_schema.census.distinct_tokens:,--> |
| distinct tokens, share of occurrences | 5.79<!--claim:governed_perf.socrata.census.distinct_tokens_pct:.2f--> % | 1.01<!--claim:governed_perf.sec_xbrl.census.distinct_tokens_pct:.2f--> % | 0.04<!--claim:governed_perf.fixture_schema.census.distinct_tokens_pct:.2f--> % |
| tokens per identifier | 2.728<!--claim:governed_perf.socrata.census.tokens_per_identifier:.3f--> | 7.228<!--claim:governed_perf.sec_xbrl.census.tokens_per_identifier:.3f--> | 16.069<!--claim:governed_perf.fixture_schema.census.tokens_per_identifier:.3f--> |
| top 5 tokens, share of occurrences | 6.07<!--claim:governed_perf.socrata.census.top5_token_occurrence_pct:.2f--> % | 15.36<!--claim:governed_perf.sec_xbrl.census.top5_token_occurrence_pct:.2f--> % | 23.39<!--claim:governed_perf.fixture_schema.census.top5_token_occurrence_pct:.2f--> % |
| top 100 tokens, share of occurrences | 37.43<!--claim:governed_perf.socrata.census.top100_token_occurrence_pct:.2f--> % | 66.78<!--claim:governed_perf.sec_xbrl.census.top100_token_occurrence_pct:.2f--> % | 97.43<!--claim:governed_perf.fixture_schema.census.top100_token_occurrence_pct:.2f--> % |
| tokens seen exactly once, share of occurrences | 2.67<!--claim:governed_perf.socrata.census.token_hapax_pct_of_occurrences:.2f--> % | 0.40<!--claim:governed_perf.sec_xbrl.census.token_hapax_pct_of_occurrences:.2f--> % | 0.00<!--claim:governed_perf.fixture_schema.census.token_hapax_pct_of_occurrences:.2f--> % |

**Schema tokens are heavily repeated and the assumption about *which* tokens repeat is wrong.** The
premise this workstream was handed is that `ID`, `DT`, `TXN`, `AMT` and `CD` recur across millions of
columns. On the fixture corpus that is exactly right, because a fixture built out of a governed
catalog's own vocabulary can hardly do otherwise. **On real portal schemas it is not right.**

The commonest tokens are saved on each census entry as `top_tokens`, and they are printed here rather
than cited because the claims gate's citation mechanism renders a *number* and cannot carry a string
— which is worth noticing, since a token list is exactly the kind of evidence that would otherwise go
unadjudicated:

```
python bench/run_governed_perf.py --only census   -- command output, not a gated measurement
                                                     the same strings are saved as top_tokens

  socrata          commonest: 1,age,de,2,p,of,q,total,n,b
  sec_xbrl         commonest: of,and,stock,in,to,for,shares,from,issued,net
  fixture_schema   commonest: cd,dt,ts,nbr,am,eff,src,id,seq,chg
```

Socrata's head is ordinals, a Spanish preposition and single letters; SEC XBRL's is English function
words inside `CamelCase` element names; only the fixture's looks like the premise. The head is also
much flatter than the premise: five tokens carry
6.07<!--claim:governed_perf.socrata.census.top5_token_occurrence_pct:.2f--> % of Socrata's occurrences
against 23.39<!--claim:governed_perf.fixture_schema.census.top5_token_occurrence_pct:.2f--> % of the
fixture's.

**That does not kill P2, and the reason is worth stating exactly.** Concentration in the head and
reuse overall are different quantities, and it is the second one a memo lives on. Only
5.79<!--claim:governed_perf.socrata.census.distinct_tokens_pct:.2f--> % of Socrata's token
occurrences are the first sight of a token, so `94.21` % of them are repeats; on SEC XBRL the first
sight is 1.01<!--claim:governed_perf.sec_xbrl.census.distinct_tokens_pct:.2f--> %. The reuse is
there. It is spread over a long tail rather than piled on five tokens.

**And the tail is exactly what the shipped memo cannot hold.** `_MEMO_LIMIT` is
4,096<!--claim:governed_perf.socrata.census.memo_limit:,--> entries and the memo **clears** when it
fills — it has no eviction order, by a decision the module documents as deliberate. Socrata carries
5.99<!--claim:governed_perf.socrata.census.distinct_tokens_per_memo_limit:.2f--> times that many
distinct tokens; SEC XBRL
1.61<!--claim:governed_perf.sec_xbrl.census.distinct_tokens_per_memo_limit:.2f--> times. The commonest
4,096 Socrata tokens do carry
88.32<!--claim:governed_perf.socrata.census.tokens_within_memo_limit_occurrence_pct:.2f--> % of all
token occurrences, so **the headroom is real and the current structure cannot reach it**: a
clear-on-full map over a working set six times its size spends the pass refilling. The one arm where
the shipped memo shows a high hit rate is the fixture arm, whose entire token set is
117<!--claim:governed_perf.fixture_schema.census.distinct_tokens:,--> items — a hundred and seventeen
against a limit of four thousand.

### The cost centres, measured by ablation rather than by attribution

`expand_identifier` does four separable things. A profiler can say what each *function* cost; it
cannot say what each *centre* cost, because a frozen dataclass's generated `__init__` is a code
object called from the expansion path and attributing it by caller files provenance's cost under
assembly. So the runner times five nested stages over the same corpus and subtracts: `tokenise`,
`lookup` (tokenise + the digit rejoin + a memoised `resolve`), `phrase` (+ the long form + the join),
`class_word` (+ the one provenance field that costs a second index lookup), and `full`
(`expand_identifier` itself).

**The stages are checked against the shipped path three ways, because a stage that quietly does less
work is a fiction that looks like a finding.** On every arm: the phrase is byte-identical to
`expand_identifier(...).phrase` on every identifier
(0<!--claim:governed_perf.socrata.empty.phrase_mismatches:,--> mismatches over
155,272<!--claim:governed_perf.socrata.empty.identifiers:,--> Socrata names), the stages take the
shipped path's `resolve` count exactly
(0<!--claim:governed_perf.socrata.empty.stage_catalog_lookup_excess:,--> excess lookups), and the
class-word stage takes the shipped path's `class_word_for` count exactly
(0<!--claim:governed_perf.socrata.empty.stage_class_word_lookup_excess:,--> excess). The second check
is not decoration: the first draft of `stage_lookup` resolved every token instead of consulting a
memo first, so on the arm where the catalog answers it did *more* work than the stage above it and
the assembly centre came out at `-7.78` points. That failure was loud. The quiet version — a stage
that skips lookups while agreeing on every phrase — is what the count catches.

### The answer, in one sentence with a number behind it

**Provenance construction dominates on every arm — it is the largest cost centre on all four, and on
every one of them it is larger than the other three put together: the shipped call builds
578,816<!--claim:governed_perf.socrata.empty.provenance_records_constructed:,--> frozen records for
155,272<!--claim:governed_perf.socrata.empty.identifiers:,--> Socrata identifiers —
3.728<!--claim:governed_perf.socrata.empty.provenance_records_per_identifier:.3f--> per call — and
removing every one of them without changing a character of the phrase leaves the call roughly two to
four times faster depending on the arm, the width being what three decompositions of one corpus on
one machine disagree by.**

The counts behind it, which are properties of the code rather than of this laptop:

| work count, per identifier | Socrata, empty catalog | SEC XBRL, empty catalog | fixture schema, fixture catalog |
|---|---:|---:|---:|
| tokenizer passes | 1.000 | 1.000 | 1.000 |
| catalog lookups | 2.906<!--claim:governed_perf.socrata.empty.catalog_lookups_per_identifier:.3f--> | 7.233<!--claim:governed_perf.sec_xbrl.empty.catalog_lookups_per_identifier:.3f--> | 1.197<!--claim:governed_perf.fixture_schema.fixture.catalog_lookups_per_identifier:.3f--> |
| provenance records constructed | 3.728<!--claim:governed_perf.socrata.empty.provenance_records_per_identifier:.3f--> | 8.228<!--claim:governed_perf.sec_xbrl.empty.provenance_records_per_identifier:.3f--> | 2.127<!--claim:governed_perf.fixture_schema.fixture.provenance_records_per_identifier:.3f--> |
| Python-level calls | 139.87<!--claim:governed_perf.socrata.empty.python_calls_per_identifier:.2f--> | 322.41<!--claim:governed_perf.sec_xbrl.empty.python_calls_per_identifier:.2f--> | 186.47<!--claim:governed_perf.fixture_schema.fixture.python_calls_per_identifier:.2f--> |
| expansion-memo hit rate | 0.00<!--claim:governed_perf.socrata.empty.expansion_memo_hit_pct:.2f--> % | 0.00<!--claim:governed_perf.sec_xbrl.empty.expansion_memo_hit_pct:.2f--> % | 92.98<!--claim:governed_perf.fixture_schema.fixture.expansion_memo_hit_pct:.2f--> % |
| `resolve`-memo hit rate | 0.00<!--claim:governed_perf.socrata.empty.catalog_memo_hit_pct:.2f--> % | 0.00<!--claim:governed_perf.sec_xbrl.empty.catalog_memo_hit_pct:.2f--> % | 0.01<!--claim:governed_perf.fixture_schema.fixture.catalog_memo_hit_pct:.2f--> % |

Four of those rows are findings on their own.

**Both memo hit rates are zero on every published governed configuration, and that is a derivation
rather than an accident of these corpora.** Every governed figure this project publishes is taken
with an **empty** catalog, and `_Memo` records only what the vocabulary answered for — never a miss,
by a decision its docstring defends at length. An empty catalog answers for nothing, so both maps
stay empty for the whole pass. The memoisation workstream's benefit on the configuration every
flagship number is measured in is exactly zero, and its cost — the `get` and the `_memo(policy)`
call, 874,807<!--claim:governed_perf.socrata.empty.memo_partitions_consulted:,--> of the latter on the
Socrata pass — is paid in full.

**The `resolve` memo is close to dead on this path even when the catalog does answer.** On the
fixture arm it serves 3<!--claim:governed_perf.fixture_schema.fixture.catalog_memo_hits:,--> of
23,934<!--claim:governed_perf.fixture_schema.fixture.catalog_lookups:,--> lookups, because the
expansion memo in front of it already short-circuits every repeat. Two memos are shipped; on the
identifier path one of them does essentially all of the work. That does not make the second one
useless — `expand_token`, the compliance direction and the reverse direction all reach it without
passing the first — but it does mean an identifier-level memoisation proposal is arguing about a map
that already has a `92.98` % hit rate in front of it on the only arm where either fires.

**The digit rejoin is a sixteenth of Socrata's catalog lookups and is invisible in every
existing figure.** `_rejoin_digit_tokens` performs
27,719<!--claim:governed_perf.socrata.empty.catalog_lookups_from_digit_rejoin:,--> of the
451,263<!--claim:governed_perf.socrata.empty.catalog_lookups:,--> lookups, against
382<!--claim:governed_perf.sec_xbrl.empty.catalog_lookups_from_digit_rejoin:,--> on SEC XBRL — a
corpus-shape effect, not a code effect: Socrata field names are full of ordinals and years and SEC
element names are not.

**`_scan` still has not met real data.** The reference character-by-character reading of the
tokenisation rules ran
0<!--claim:governed_perf.socrata.empty.tokenizer_scans:,--> times across
155,272<!--claim:governed_perf.socrata.empty.identifiers:,--> Socrata identifiers and
0<!--claim:governed_perf.sec_xbrl.empty.tokenizer_scans:,--> times across
90,655<!--claim:governed_perf.sec_xbrl.empty.identifiers:,--> SEC element names, because both corpora
are entirely ASCII and `split_identifier_parts` takes the regex path. That reproduces
[`docs/AUDIT-2026-08.md`](AUDIT-2026-08.md)'s question 6 on a population this tree actually holds. An
automaton workstream aimed at the tokenizer would be optimising a branch that has never executed on
real input, and would have to displace a path that is already entirely in C.

### The wall-clock, as an unarmed note, with the machine named

Operating rule 18: allocations, catalog lookups and tokenizer passes are properties of the code and
are gated above; nanoseconds are properties of the runner and are printed here, fenced, so that no
gate ratchets on them. **This is not a formality.** Across three full runs of this runner on this
one machine, every count in the tables above was byte-identical and the Socrata arm's wall-clock
moved by `43` %. The cost-centre shares are derived from wall-clock and inherit that; the runner
therefore reports a median of three independent decompositions with the spread beside it, and the
spread is what a reader should take seriously.

**Where a wall-clock share is cited in prose below, the citation is a staleness check and not a
ratchet.** Nothing turns red if a re-run moves a share; what turns red is this page disagreeing with
`bench/results.json`. Leaving these figures only inside the fence would have silenced the gate
completely, which D-052 says is mechanically indistinguishable from hiding them, so the ones that
carry an argument are cited and the tabular presentation stays here where the machine is named.

```
python bench/run_governed_perf.py --only arms    -- command output, not a gated measurement
Python 3.13.4 on Windows AMD64; AMD64 Family 26 Model 68 Stepping 0, AuthenticAMD.
Median of 3 independent decompositions, 2 timed passes per stage, fastest taken.
The four centres sum to the whole call; medians of four separate distributions
need not sum to 100 and these do not.

  arm                                tokenise   catalog  assembly  PROVENANCE   phrase-only
  socrata,        empty catalog         9.82 %   13.88 %    6.43 %     70.15 %       3.35 x
                                 spread 8.6-11.7 10.6-14.4 4.3- 8.6   69.4-72.2   3.26-3.60
  socrata,        fixture catalog       8.15 %   15.95 %    7.74 %     67.56 %       3.08 x
  sec_xbrl,       empty catalog         6.37 %   12.81 %    7.25 %     73.55 %       3.78 x
                                 spread 5.2- 7.1  9.7-14.0 6.6-11.5   69.4-76.7   3.27-4.29
  fixture schema, fixture catalog      23.02 %   16.82 %    3.30 %     49.85 %       1.99 x

  inside the provenance centre, socrata/empty:
    the class-word lookup                                    4.82 %  (spread 2.7-12.4)
    constructing and validating the records                 65.33 %  (spread 59.8-66.7)

  throughput and per-call cost, this machine only:
    socrata,  empty catalog     91,155 identifiers/s     10,970 ns per identifier
    sec_xbrl, empty catalog     39,150 identifiers/s     25,543 ns per identifier

  the same arm across three full runs of this runner, same tree, same machine:
    run 1   8,118 ns per identifier    run 2  11,597 ns    run 3   8,895 ns
    every work count identical in all three, to the unit. That 43 % spread is
    why the nanoseconds are printed here and the counts are what is gated.
```

Three readings, and the third is the one that changes the ranking.

**The ordering is stable and the magnitudes are not.** Provenance is the largest centre on all four
arms and in all three decompositions of each; the spreads of the three small centres overlap each
other freely, and on the fixture arm a single round put the assembly centre *below zero*. A
difference of two large similar timings inherits the noise of both. **Take the ordering. Do not
quote the magnitude of any centre but provenance.**

**Provenance survives a
92.98<!--claim:governed_perf.fixture_schema.fixture.expansion_memo_hit_pct:.2f--> % memo hit rate.**
On the fixture arm — the only one where the catalog
answers and the memo fires — provenance is still
49.85<!--claim:governed_perf.fixture_schema.fixture.stage_provenance_pct:.2f--> % of the call. The
expansion memo removes the *token* records; it cannot remove the `IdentifierExpansion`, because every
identifier is distinct by construction and one record per call is the floor. Memoisation and lazy
provenance are therefore **not** substitutes: the second still has most of its win after the first
has taken all of its own.

**Tokenisation is the largest centre on exactly the arm nobody runs.** It is
23.02<!--claim:governed_perf.fixture_schema.fixture.stage_tokenise_pct:.2f--> % on the fixture arm,
whose identifiers average
16.069<!--claim:governed_perf.fixture_schema.census.tokens_per_identifier:.3f--> tokens, against
2.728<!--claim:governed_perf.socrata.census.tokens_per_identifier:.3f--> on Socrata. Any conclusion
about the tokenizer drawn from the fixture corpus is a conclusion about a corpus with six times the
tokens per name.

### The premise underneath the lazy-provenance bet, measured — and it does not hold here

"Every call builds a full record and most callers read only `.phrase`" is one sentence with two
halves. The first half is measured above. **The second half is a claim about callers, and it had
never been checked against anything.**

It cannot be checked against strangers: this project has
[zero confirmed adopters on two independent instruments](POSITIONING.md#reversal-two-adoption-seeking-unblocks-the-day-adoption-becomes-legible).
It can be checked exactly against the one caller population that exists. `--only callers` parses every
`expand_identifier` call site in the tree and records which attributes of the result are read,
recognising three shapes — the field taken straight off the call, a bound name whose attribute reads
are collected across the enclosing function, and a result that leaves the scope, which is counted
`unclassified` rather than assigned a convenient answer.

| group | call sites | classified | read only `.phrase` | share |
|---|---:|---:|---:|---:|
| `src/acronymkit` | 3<!--claim:governed_perf.caller_census.library_sites:,--> | 3<!--claim:governed_perf.caller_census.library_classified:,--> | 0<!--claim:governed_perf.caller_census.library_phrase_only:,--> | 0.00<!--claim:governed_perf.caller_census.library_phrase_only_pct:.2f--> % |
| `bench`, `tools`, `examples` | 12<!--claim:governed_perf.caller_census.harness_sites:,--> | 8<!--claim:governed_perf.caller_census.harness_classified:,--> | 6<!--claim:governed_perf.caller_census.harness_phrase_only:,--> | 75.00<!--claim:governed_perf.caller_census.harness_phrase_only_pct:.2f--> % |
| `tests` | 64<!--claim:governed_perf.caller_census.tests_sites:,--> | 55<!--claim:governed_perf.caller_census.tests_classified:,--> | 19<!--claim:governed_perf.caller_census.tests_phrase_only:,--> | 34.55<!--claim:governed_perf.caller_census.tests_phrase_only_pct:.2f--> % |

**Not one caller inside `src/acronymkit` reads only `.phrase`.** `cli.py` calls `to_dict`, which
touches every field of every record; `governed/audit.py` reads `is_fully_known` and `tokens`, and
`is_fully_known` is a property over every token's `is_known`, so it needs the whole record set and a
thunk would buy nothing. `tools/byoc_eval.py` reads the same three. **Every phrase-only call site in
this repository is in `bench/`, and every one of them is scoring segmentation** — code whose whole
purpose is to compare a phrase against a caption.

Three call sites is a tiny population and a biased one. What it is not is nothing, and it points the
opposite way from the premise: inside this library, an `IdentifierExpansion` is used as a provenance
record and the phrase is the field a benchmark wants. The runner excludes itself from this census —
it holds a phrase-only call site of its own, and counting it would push the share up in the
flattering direction.

### The pre-registered ranking, and how the measurement re-ordered it

Written before any profiler ran, to a scratch file, and reported here unedited. The ranking was
`lazy provenance > memoisation > streaming batch > automaton > free-threading`, with a numeric
falsifier attached to each.

| bet | pre-registered | measured | verdict |
|---|---|---|---|
| provenance share | `>= 35 %`, falsified below `20 %` | `70.15 %` | direction right, magnitude **under-predicted by half** |
| phrase-only speed-up | `>= 1.6x`, falsified below `1.25x` | `3.35x` | right, magnitude under-predicted by half |
| token distinct ratio | `<= 15 %`, falsified above `30 %` | `5.79 %` | right |
| top-5 token share | `>= 10 %`, falsified below `5 %` | `6.07 %` | **wrong**, and not falsified either |
| tokenisation share | `<= 25 %`, falsified above `35 %` | `9.82 %` | right |
| catalog lookup: smallest centre | `<= 10 %`, falsified above `20 %` | `13.88 %`, **second largest** | **falsified** |
| callers reading only `.phrase` | `>= 60 %`, falsified below `40 %` | `0.00 %` in the library | **falsified, badly** |

**Four things the pre-registration got wrong, and two of them re-order the list.**

1. **Catalog lookup is the second-largest centre, not the smallest.** Assembly is the smallest. The
   prediction assumed an empty catalog makes lookup nearly free; it does not, because `resolve`
   normalises its key, consults the policy memo and walks the precedence chain before it can report
   nothing — `_token_key` runs
   1,298,351<!--claim:governed_perf.socrata.empty.token_keys_folded:,--> times on the Socrata pass
   against 423,544<!--claim:governed_perf.socrata.census.token_occurrences:,--> token occurrences,
   which is three foldings of the same string per token.
2. **The phrase-only caller does not exist inside this library.** That does not kill lazy provenance
   — it means the win is available only to callers this project has never seen, and it means the
   design must keep `is_fully_known` cheap or the library's own audit path gets slower. A
   lazy-provenance proposal that does not say what happens to `audit_identifiers` is not a proposal.
3. **The Zipfian schema-token premise is the fixture's distribution, not a schema's.** Every intuition
   about `ID`/`DT`/`CD` in this project traces to a corpus built out of the fixture catalog's own
   token pool.
4. **Memoisation and lazy provenance were ranked as competitors and are not.** Provenance is still
   half the call after the memo has taken everything it can take.

The list after the measurement:

1. **Lazy provenance** — unchanged at rank one, and by a wider margin than predicted. The one new
   condition is that it must not make `is_fully_known` or `tokens` more expensive, because those are
   what this library's own callers read.
2. **Memoisation** — unchanged at rank two, with its shape changed. The token-level win is real
   (`88.32` % of Socrata occurrences are inside a 4,096-entry working set) and the shipped
   clear-on-full map cannot collect it; the ceiling is an eviction policy, not a second memo.
3. **A streaming batch API** — up from rank three only in the sense that it is now bounded rather
   than guessed: `_prepare` runs
   155,272<!--claim:governed_perf.socrata.empty.call_preparations:,--> times on the Socrata pass,
   exactly once per identifier, out of
   139.87<!--claim:governed_perf.socrata.empty.python_calls_per_identifier:.2f--> Python calls per
   identifier. That is `0.7` % of the call graph. **A streaming API cannot be worth more than that
   unless it changes what is built**, which makes it a delivery mechanism for lazy provenance rather
   than an optimisation in its own right.
4. **An automaton** — down, and close to dead. Tokenisation is
   9.82<!--claim:governed_perf.socrata.empty.stage_tokenise_pct:.2f--> % of the Socrata call, the
   path it would replace is already a regex in C, and the
   character-by-character branch it would compete with executed
   0<!--claim:governed_perf.socrata.empty.tokenizer_scans:,--> times on either real corpus.
5. **Free-threading** — unchanged at last, and this measurement says nothing about it. Nothing here
   is a serialisation point that a thread count would relieve, and the one shared mutable structure
   is the memo, which is a correctness question rather than a throughput one. Recorded as
   unmeasured.

### How this fails

**Both corpora are schema corpora, and nothing here describes a prose caller.** `extract`,
`disambiguate` and the generation path have entirely different hot paths, and no figure in this
section may be quoted about any of them. The governed subsystem is what was measured because it is
the half [`docs/POSITIONING.md`](POSITIONING.md) leads with.

**The only arm where a catalog answers is a fixture.** No public catalog exists for Socrata or SEC
XBRL — that is the standing unknown this project has carried for four phases — so the arm with a
92.98<!--claim:governed_perf.fixture_schema.fixture.expansion_memo_hit_pct:.2f--> % memo hit rate is a
synthetic corpus drawn from the fixture catalog's own token pool, and the arm with real names has a
memo hit rate of zero because the catalog is empty. **There is no measurement anywhere in this
section of the hot path a real governed vocabulary would produce**, and the distance between the two
arms is large: the fixture arm's provenance share is twenty points lower than Socrata's. A reader who
takes the fixture arm as the governed case is reading a corpus built to make the memo look good.

**The counting mechanism is a profiler and it is not free.** `cProfile` costs
3.362<!--claim:governed_perf.profiler_overhead.profiler_cost_ratio:.3f--> times wall-clock on this
machine over 20,000<!--claim:governed_perf.profiler_overhead.identifiers:,--> identifiers. It cannot
perturb a *count* — that is why the counts are what is gated and the timings are taken in a separate
unprofiled pass — but a reader should know the counts and the timings come from different passes over
the same corpus rather than from one instrumented run. `tracemalloc` was considered and rejected:
it traces live blocks rather than allocation events, so it answers a different question from "how
many allocations", and what it reports over a streaming pass is a property of the collector's
schedule.

**"Allocations" here means object constructions, counted exactly, not bytes.** The gated figure is
`__post_init__` calls — one per `TokenExpansion` and one per `IdentifierExpansion`, which is the
number a lazy-provenance design would move. Arena-level allocation counts are not measured, and a
design that reduced records while raising bytes would not be visible in these numbers.

**The four centres are a decomposition of `expand_identifier` and not of a pipeline.** A caller that
also runs `is_compliant` or `to_physical_name` pays costs nothing here measures; `bench/run_governed.py`
records those verbs as three to five times dearer than `expand_identifier` per call, and no
decomposition of them exists.

**The caller census counts call sites, not calls.** A site inside a loop over ten million columns and
a site in a one-shot CLI command weigh the same. The population is eleven classified non-test sites
in one repository, which is the whole of what can be said about callers today and is not a
measurement of demand.

**The wall-clock was taken on a shared, loaded developer machine.** Another workstream was running in
this checkout throughout, which is the likeliest cause of the `43` % swing between runs; the spreads
published above are therefore an upper bound on the noise of a quiet machine rather than an estimate
of it, and no figure in the fenced block is a ratchet.

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
