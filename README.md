# acronymkit

[![CI](https://github.com/pierce-lonergan/AcronymKit/actions/workflows/ci.yml/badge.svg)](https://github.com/pierce-lonergan/AcronymKit/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/python-3.9%20%7C%203.10%20%7C%203.11%20%7C%203.12%20%7C%203.13-blue)](https://pypi.org/project/acronymkit/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![Typed](https://img.shields.io/badge/typing-py.typed-informational)](https://peps.python.org/pep-0561/)
[![OpenSSF Scorecard](https://api.securityscorecards.dev/projects/github.com/pierce-lonergan/AcronymKit/badge)](https://scorecard.dev/viewer/?uri=github.com/pierce-lonergan/AcronymKit)

**Bi-directional, multi-tiered acronym processing for production systems.**
Expand governed schema identifiers against a catalog you supply, generate acronyms from text,
synthesise backronyms, extract abbreviations already defined in a document, and resolve ambiguous
ones from context — from one typed library with a Tier 0 path that needs nothing but the standard
library.

```python
from acronymkit.governed import GovernedNamer

nds = GovernedNamer.from_mapping({"TXN": "Transaction", "APPLNT": "Applicant", "ID": "Identifier"})
nds.expand_identifier("TXN_APPLNT_ID").phrase        # 'Transaction Applicant Identifier'
nds.expand_identifier("TXN_KYC_ID").is_fully_known   # False — the catalog has no KYC
```

**Governed naming leads this README because it is the larger half of the package and the one with a
real integration story**: a little over a third of the source, close to half the public symbols,
seven of the sixteen CLI commands, and a streaming batch mode another runtime can drive. It is also
now measured, and it publishes its worst row beside its headline. Against
26,536<!--claim:governed_gold.socrata.columns.all.pairs:,--> Socrata field/caption pairs written by
the publishers themselves, it cuts the identifier exactly where the human did on
91.37<!--claim:governed_gold.socrata.columns.all.exact_pct:.2f--> % of them — and on the
959<!--claim:governed_gold.socrata.columns.unmarked.pairs:,--> pairs that carry no boundary mark at
all, on 34.93<!--claim:governed_gold.socrata.columns.unmarked.exact_pct:.2f--> %. That second number
is the price of refusing to guess, and it is in the same table as the first, along with the SEC arms
and the recall ceiling: [docs/EVALUATION.md](docs/EVALUATION.md).

**Generation is measured, and nothing else measures it.** Fed the
1,221<!--claim:generation.med1250.strict_initialism.gold_pairs:,--> human-authored
short-form/long-form pairs of the MED1250 gold standard *backwards*, `acronymkit` returns the
abbreviation the human actually chose at **rank 1 for
75.5<!--claim:generation.med1250.strict_initialism.initialism_recall_at_1:.1f--> %** of the
546<!--claim:generation.med1250.strict_initialism.initialism_n:,--> pairs an initialism
generator can address, and within the top 25 for
89.7<!--claim:generation.med1250.strict_initialism.initialism_recall_at_25:.1f--> %. MED1250 is a
**tuning split**. No competing library has a number here, because no competing library generates.

Extraction is measured too, against four other systems through one harness: precision
92.46<!--claim:extraction.med1250.acronymkit.exact_precision:.2f--> %, recall 77.31<!--claim:extraction.med1250.acronymkit.exact_recall:.2f--> %, F1 **84.21<!--claim:extraction.med1250.acronymkit.exact_f1:.2f--> %**. We are third of five there, and the table showing
exactly that is in [docs/EVALUATION.md](docs/EVALUATION.md) — including where we lose.

## Why

The open-source acronym ecosystem is split in two, with nothing in between:

| | What it does well | Where it stops |
|---|---|---|
| **Naive string utilities** — `acronymcreator`, countless gists | Fast, no dependencies | No tokenisation grammar, no phonetics, no semantics |
| **Corpus matchers** — ACRONYM (Cook, 2019) | Finds candidates that spell real words | Offline batch, static corpus, no library bindings |
| **Rule-based extractors** — Schwartz & Hearst (2003) in scispaCy, Blackstone | F₁ > 96 % on inline definitions, cheap | Strictly extractive; the definition must be present |
| **Neural disambiguators** — AcroBERT, SDU/SciAD/GLADIS | Resolves standalone acronyms from context | GPU-bound, slow cold start, research codebases |

A system that needs to *generate*, *extract* **and** *resolve* has to stitch three incompatible
codebases together. `acronymkit` is the missing single library.

Nothing in that table addresses the governed case at all: a bare column token with no sentence around
it, a catalog somebody else owns, and a requirement to **refuse** rather than guess. That is the half
of this package the rest of this README leads with.

## Install

```bash
pip install acronymkit
```

The base install is the complete Tier 0 engine — extraction, generation, backronyms, scoring, CLI-free
API — with `pydantic` as the only runtime dependency. Optional extras add higher tiers:

```bash
pip install "acronymkit[cli]"          # click-powered command line
pip install "acronymkit[nlp]"          # Tier 1: spaCy / NLTK part-of-speech evidence
pip install "acronymkit[all]"          # everything
```

CI enforces the split: a dedicated job installs the base package alone and asserts that no optional
dependency reaches `sys.modules` after a full generate + extract + backronym + disambiguate cycle.

## What it does

### Governed naming — expansion with no sentence to lean on

A schema-governance pipeline has no prose to lean on. Given a bare column token and a governed
vocabulary, return the long form — deterministically, with no context to disambiguate against, and
with a record of which catalog entry produced each word.

```python
from acronymkit.governed import GovernedNamer, load_bundle

# A real standard is a directory of files, and one line reads it:
#     nds = GovernedNamer.from_bundle("nds_standard/")
#     nds = GovernedNamer(load_bundle("nds_standard/"), policy)   # the same, unbundled
# Inline below, so this block runs with nothing on disk.
nds = GovernedNamer.from_mapping(
    {"TXN": "Transaction", "APPLNT": "Applicant", "ID": "Identifier",
     "NBR": "Number", "NUM": "Number", "DT": "Date"},
    approved_abbreviations=["TXN", "APPLNT", "ID", "NBR", "DT"],
    class_words={"ID": "Identifier", "DT": "Date"},
)

nds.expand_identifier("TXN_APPLNT_ID").phrase        # 'Transaction Applicant Identifier'
nds.expand_identifier("TXN_KYC_ID").is_fully_known   # False — the catalog has no KYC
nds.normalize("txnApplntNum")                        # 'TXN_APPLNT_NBR'
```

`GovernedNamer` binds one vocabulary and one policy and then takes the subject as its only argument;
`expand_many` and `check_many` take a whole corpus. A naming standard on disk is a catalog, three
allow-lists, a class-word map, a pin sheet and a term glossary, which is what `from_bundle` and
`load_bundle` read; `from_csv` and `from_json` read the narrower shapes.

**Nothing is dropped in silence.** A character the splitter cannot account for is reported rather
than discarded, and `is_fully_known` is true only when every token resolved *and* nothing went
unaccounted for:

```python
nds.expand_identifier("TXN_©_ID").phrase           # 'Transaction Identifier'
nds.expand_identifier("TXN_©_ID").unaccounted      # ('©',)
nds.expand_identifier("TXN_©_ID").is_fully_known   # False
```

**Your acronyms win.** `with_custom` layers an overlay above the catalog and reports it as such:

```python
result = nds.with_custom({"KYC": "Know Your Customer"}).expand_token("KYC")
result.long, result.source.value      # ('Know Your Customer', 'custom')
```

Three directions over one vocabulary — `expand_identifier` reads a physical name, `to_physical_name`
renders a logical one, `is_compliant` checks a name somebody else wrote — so a catalog change moves
all three at once. Every answer carries the rule that produced it, the catalog row behind it and the
candidates it beat.

**This is not disambiguation, and that is the design.** A column name is not a sentence: there is no
context to weigh, so the answer comes from the catalog or it does not come at all. An unknown token
is reported as unknown, with zero confidence, never approximated — because an unknown reported as
unknown is recoverable and an unknown quietly guessed is not.

**One thing here does decide something on its own, and it is now measured.** Catalog lookup is exact
by construction, which is a tautology rather than a measurement — a lookup table is exact about
whatever you put in it. Where the identifier is *cut into tokens* is the one judgement this
subsystem makes unaided, and it is scored against captions the publishers themselves wrote, on two
public corpora, decomposed and with its recall ceiling printed:
[docs/EVALUATION.md](docs/EVALUATION.md). Every one of those runs recorded its corpus as undeclared
at the time it ran, and none has been re-measured since — read them as measured-before-declared
rather than as held-out. [docs/GOVERNED_NAMING.md](docs/GOVERNED_NAMING.md) has the precedence
chain, every verb with runnable output, the four invariants and an honest limits section.

### Forward generation

```python
from acronymkit import AcronymEngine, Config
from acronymkit.enums import EngineTier, ScoringStrategy

engine = AcronymEngine(Config(
    engine_tier=EngineTier.HYBRID_NLP,
    scoring_strategy=ScoringStrategy.STRICT_INITIALISM,
    include_articles=False,
    min_word_length=2,
    max_acronym_length=6,
))

result = engine.generate("Application Programming Interface")
result.primary_acronym                    # 'API'
result.score                              # 21.297
result.primary.breakdown.explain()
# 'S = 1*30.000 + 0.25*-2.811 + 2*0.000 - 25*0.000 = 21.297'

[(c.acronym, round(c.score, 2)) for c in result.alternatives[:4]]
# [('API', 21.3), ('APIN', 15.42), ('APRI', 15.38), ('APPI', 15.29)]
```

Every candidate carries a per-character alignment trace and a term-by-term score decomposition, so a
ranking decision is always explainable.

### Backronym synthesis

Align a phrase onto a target word:

```python
result = engine.generate_backronym(
    phrase="Network Exchange Unified Security",
    target_word="NEXUS",
)
result.primary_expansion            # 'Network Exchange Unified Security'
result.candidates[0].coverage       # 1.0
[m.kind.value for m in result.candidates[0].mappings]
# ['initial', 'initial', 'contiguous', 'initial', 'initial']
```

Note the `contiguous` mapping: **E** and **X** both come from "**Ex**change". Sub-word matches are
first-class, exactly as in the ACRONYM formulation.

Or expand a word with no source phrase at all:

```python
engine.synthesize_backronym("NEXUS").candidates[0].expansion_text
# 'nag ear xenon urn sad'
```

### Extraction (Schwartz & Hearst)

```python
engine.extract_definitions(
    "The National Aeronautics and Space Administration (NASA) launched the mission."
)
# [AcronymPair(short_form='NASA', long_form='National Aeronautics and Space Administration')]
```

Both arrangements are supported — `Long Form (Short Form)` and the inverted
`Short Form (Long Form)` — with exact source spans (`text[pair.short_form_span[0]:...] == short_form`
always holds) and a confidence estimate. Prose parentheticals such as `(see Figure 3)` and
enumerations such as `(1) … (2) …` are correctly rejected.

**Measured, not asserted.** On the MED1250 gold standard
(1,221<!--claim:extraction.med1250.acronymkit.gold_pairs:,--> human-annotated pairs from the Ab3P
corpus): **precision 92.46<!--claim:extraction.med1250.acronymkit.exact_precision:.2f--> %, recall 77.31<!--claim:extraction.med1250.acronymkit.exact_recall:.2f--> %, F1 84.21<!--claim:extraction.med1250.acronymkit.exact_f1:.2f--> %**, at 5,496<!--claim:extraction.med1250.acronymkit.docs_per_second:,.0f--> documents/second. High
precision with recall the weak side is the expected shape for this algorithm — it refuses rather than
guesses. The full breakdown, including where the misses come from and one optimisation that was tried
and reverted, is in [docs/EVALUATION.md](docs/EVALUATION.md). Reproduce with:

```bash
python tools/fetch_data.py med1250 && python bench/run_extraction.py
```

### Contextual disambiguation

```python
from acronymkit.disambiguation import ExpansionDictionary

vocab = ExpansionDictionary({"MS": [
    "multiple sclerosis", "Microsoft", "mass spectrometry", "manuscript",
]})

engine.disambiguate("MS", "The patient was diagnosed with MS after an MRI showed brain lesions.",
                    dictionary=vocab).primary_expansion   # 'multiple sclerosis'
engine.disambiguate("MS", "The MS Office suite shipped a new version of Word and Excel.",
                    dictionary=vocab).primary_expansion   # 'Microsoft'
engine.disambiguate("MS", "Peak intensity in the MS spectrum identified the ionised compound.",
                    dictionary=vocab).primary_expansion   # 'mass spectrometry'
```

**The `dictionary=` argument is not optional decoration — it is the whole feature.** Without it there
is no selection happening at all. The engine looks only for a parenthetical definition **inside the
string you passed**, so the default path is an inline-definition lookup wearing a disambiguator's
name. On the SDU@AAAI-21 AD dev split it returns no candidate whatsoever on
97.45<!--claim:disambiguation.sdu21.diagnosis.default_path.no_candidate_pct:.2f--> % of instances, and
has two candidates to choose between on
1<!--claim:disambiguation.sdu21.diagnosis.default_path.two_or_more_candidates:,--> of
6,189<!--claim:disambiguation.sdu21.diagnosis.default_path.instances:,-->. There is also no cross-call
state, so `engine.disambiguate("MS", a_later_sentence)` returns `None` no matter how many earlier
calls defined `MS`. Carry the definitions yourself if you want them to persist:
`ExpansionDictionary.from_pairs(engine.extract_definitions(whole_document))`.

Every result also reports `margin`, the score gap between the top two candidates, and
`LexicalDisambiguator(config, vocab, min_margin=...)` will decline to answer below a margin you
choose. **It is off by default and it is a precision instrument, not an accuracy fix.** Raising the
gate raises accuracy among the questions still answered and lowers F1 at every step — from
41.65<!--claim:disambiguation.sdu21.abstention_curve.gate_0.00_f1:.2f--> % ungated to
15.07<!--claim:disambiguation.sdu21.abstention_curve.gate_0.20_f1:.2f--> % at the tightest gate
measured. Worse, below gate `0.10` the shared task's own most-frequent-expansion baseline is *more*
accurate on the gate's own answered subset, and on three- and four-candidate sets it still is at the
gate where the pooled numbers cross over. The full curve, its losing comparison in the same table,
and the decomposition by candidate-set size are in
[docs/EVALUATION.md](docs/EVALUATION.md#abstention-a-precision-instrument-and-where-it-is-worse-than-doing-nothing);
the run is `disambiguation.sdu21.abstention_curve` in [bench/results.json](bench/results.json), on a
**tuning split**, so no point on it is a default this library adopts.

Note that `AcronymEngine.disambiguate` above has no gate: `min_margin` is a constructor argument of
`LexicalDisambiguator`, which you build directly over your own dictionary. That gap is deliberate —
the gate needs two candidates to compare, and the facade's default path almost never has them.

### Multilingual — English complete, others experimental

Categorised stop-word taxonomies ship for English, French, Spanish and German, and generation works
for all four:

```python
from acronymkit.enums import Language
AcronymEngine(Config(language=Language.FR)).generate("Système de Gestion de Base de Données")  # SGBD
AcronymEngine(Config(language=Language.DE)).generate("Allgemeine Deutsche Automobil Club")     # ADAC
```

**But only English ships a lexicon and a character model.** For fr/es/de, Λ(A) is identically zero
(no candidate is ever reported as a dictionary word) and Φ(A) is uniform (pronounceability stops
discriminating). Positional fidelity carries generation on its own, which is why the examples above
are still correct — but treat those languages as experimental.

This is deliberate. The v0.1.0 word lists for those languages were model-authored, which made every
dictionary claim about them unverifiable, and unlike English there is no permissively licensed
replacement to swap in: the available Hunspell dictionaries are copyleft, and German's only permissive
arm grants distribution solely alongside ODF applications. Given the choice between invented data and
no data, no data is correct — invented data produces confident wrong answers a caller cannot detect.

The engine says so rather than degrading silently:

```python
result = AcronymEngine(Config(language=Language.FR)).generate("Système de Gestion de Base de Données")
result.metadata.warnings
# ["no bundled lexicon for language 'fr': Lambda(A) is always 0, ...",
#  "no bundled n-gram model for language 'fr': Phi(A) is uniform, ..."]
```

To get real coverage, install a dictionary yourself — it stays on your machine, so its licence is
your call, not ours:

```bash
python tools/fetch_data.py hunspell-fr
python tools/build_lexicons.py --language fr --output ~/fr.txt
```

```python
Config(language=Language.FR, lexicon_path=Path("~/fr.txt").expanduser())
```

## Execution tiers

| Tier | `EngineTier` | Dependencies | Latency | Use for |
|---|---|---|---|---|
| 0 | `ZERO_DEPENDENCY` | stdlib + Pydantic | **98<!--claim:micro.generate_fast.median:.0f--> µs/call**, 2.3<!--claim:micro.import.cold_import_ms:.1f--> ms to import | Edge, high-throughput indexing, hot paths |
| 1 | `STATISTICAL_NLP` | spaCy **or** NLTK | single-digit ms | POS-aware generation on messy human text |
| 1 | `HYBRID_NLP` | optional | either | Production default — degrades gracefully |
| 2 | `NEURAL` | ONNX Runtime | — | **Phase 3, not in this release** |
| — | `AUTO` | — | — | Best tier available at import time |

**The import figure is the shell, not the engine, and quoting it alone would flatter us.**
`import acronymkit` is cheap because the package resolves its re-exports lazily; `from acronymkit
import AcronymEngine` still costs
128.1<!--claim:micro.import.cold_import_engine_ms:.1f--> ms and import-plus-first-result
196.0<!--claim:micro.import.cold_first_result_ms:.1f--> ms. Laziness **moves** the Pydantic cost to
first use rather than removing it, so the win is confined to a process that imports the package
without using it. All three come from `micro.import` in
[bench/results.json](bench/results.json) and are read together in
[docs/EVALUATION.md](docs/EVALUATION.md).

Degradation is never silent in the payload: the effective tier lands in `metadata.engine_tier`, the
requested one in `metadata.requested_tier`, and the reason in `metadata.warnings`. Set
`Config(strict=True)` to turn degradation into a `TierUnavailableError` instead.

## The scoring function

Candidates are ranked by a configurable composite objective:

$$S(A, T) = \alpha \sum_{i} \omega(c_i, w_{j(i)}) \;+\; \beta \, \Phi(A) \;+\; \gamma \, \Lambda(A) \;-\; \delta \, \Psi(T, A)$$

| Term | Meaning |
|---|---|
| `ω(cᵢ, w)` | **Positional mapping weight** — 10 when `cᵢ` is the initial character of `w`, 3 when internal or terminal, 2 when it directly follows a previously matched character of the same token |
| `Φ(A)` | **Phonotactic pronounceability** — mean character-bigram log-likelihood, `(1/(k−1))·Σ log P(c_{m+1} \| c_m)` |
| `Λ(A)` | **Lexical match** — 1 when `A` is a real word in the target lexicon (a successful backronym), else 0 |
| `Ψ(T, A)` | **Information loss** — count of semantically critical tokens the acronym drops |

`Φ` behaves the way you would hope: Φ("SCALE") = −2.29, Φ("PDF") = −6.22, Φ("XKCD") = −7.46.

The syllable heuristic underpinning it is measured, not asserted: against the
117,485<!--claim:validation.syllables_cmudict.words_scored:,.0f--> CMUdict
entries it scores **84.1<!--claim:validation.syllables_cmudict.exact_match_pct:.1f--> % exact** and
**99.5<!--claim:validation.syllables_cmudict.within_one_pct:.1f--> % within one syllable** (mean
absolute error 0.16<!--claim:validation.syllables_cmudict.mean_absolute_error:.2f-->).
Reproduce with `python tools/build_lexicons.py --validate-syllables`.

### Presets

`ScoringStrategy` selects a calibrated `(α, β, γ, δ)` vector:

| Strategy | Behaviour |
|---|---|
| `STRICT_INITIALISM` | **Default.** Positional fidelity dominates; reproduces the textbook initialism |
| `BALANCED_PRONOUNCEABLE` | A real trade: pronounceability and dictionary hits can outrank the literal initialism |
| `MAX_PRONOUNCEABLE` | Phonotactics dominate — for product and project naming |
| `DICTIONARY_BACKRONYM` | A real word outweighs almost everything else |
| `CUSTOM` | You supply `ScoringWeights` |

```python
# "Structured Query Language Transaction Protocol"
STRICT_INITIALISM   -> 'SQLTP'   pronounceability 0.11
MAX_PRONOUNCEABLE   -> 'SQULTP'  pronounceability 0.65

# "Network Exchange Unified Security"
DICTIONARY_BACKRONYM -> 'NEXUS'  (dictionary word, score 92.95)
```

The defaults are calibrated rather than guessed, by a committed script
(`tools/tune_presets.py`) so the claim is falsifiable. `STRICT_INITIALISM` reproduces **all sixteen**
entries of a canonical corpus of textbook initialisms (API, PDF, NASA, HTML, RAM, CPU, GPU, SCUBA,
LASER, SQL, CRM, QA, TCP, SOAP, BIOS, ROM), and keeps doing so when β, γ or δ are perturbed by
50–100 % — a genuine plateau rather than a fitted point. `tests/test_scoring_presets.py` pins the
corpus so retuning cannot silently regress it.

`BALANCED_PRONOUNCEABLE` deliberately does *not* reproduce that corpus, and it is worth knowing why.
Against the real 76,879-word lexicon there is provably no coefficient vector that both weights
dictionary hits meaningfully and returns every textbook initialism: suppressing a vowel insertion
needs a length penalty above ~14, which then over-penalises the short acronyms instead. So the preset
honours its name — it returns `QUA` for "Quality Assurance", because "qua" is a word. See
[docs/DECISIONS.md](docs/DECISIONS.md).

> **One deliberate deviation from the published formulation.** The positional term is a *sum*, so it
> grows monotonically with length — used unmodified as a generation objective it prefers `PODOFO` to
> `PDF`. `ScoringWeights.length_penalty` (default 8.0) closes that gap, sitting between
> `contiguous_weight` (2) and `initial_weight` (10) so that covering a new token nets +2 while taking
> a second letter from a token already used nets −6. Set `length_penalty=0.0` to recover the
> unmodified objective exactly.

## Command line

```bash
pip install "acronymkit[cli]"
```

### Governed naming from the command line

Seven of the sixteen commands read a governed vocabulary. `expand-token`, `expand-identifier`,
`physical-name`, `check-name` and `normalize-name` answer one subject each — `check-name` exits 1 when the name does
not conform, so it works as a gate. Two answer a whole schema in one process:

```bash
acronymkit governed-batch --dictionary std/ --op expand < columns.txt > answers.jsonl
acronymkit governed-audit --dictionary std/ --suggest   < columns.txt
```

**`governed-batch` streams**: one record per line in, one JSON object per line out, nothing
accumulates, so a fifty-thousand-column schema costs the same memory as a hundred-column one and the
reader sees the first answer before the last question is asked. `--op` selects `expand`, `physical`,
`check`, `normalize` or `audit`; every record carries `line`, `input` and any `id` it arrived with.
An error rides on its own record and never aborts the run, the process exits 1 if any record failed,
and the one-line summary goes to stderr so every line of stdout is a record. This is the command that
makes the library usable from another language: answering one name takes microseconds and starting a
Python interpreter takes tens of milliseconds, so a pipeline that shells out per column pays almost
all of its cost outside the work.

**`governed-audit`** reduces the same corpus to one report — coverage, round-trip breaks, compliance
findings by reason code, and the unknown-token backlog ranked by how often each token appears and in
how many of them. `--suggest` proposes catalog rows to write, `--limit` controls truncation,
`--details` keeps one record per name in the JSON.

`--dictionary` takes a bundle directory, a JSON catalog or a CSV on all seven, with
`--dictionary-format`, `--columns` and `--delimiter` saying how to read it — and it refuses to guess
which way round a two-column CSV is meant to be read, because both readings are valid vocabularies
that mean different things. Every command here except `governed-batch` also takes `--format json`.

[docs/QUICKSTART_GOVERNED.md](docs/QUICKSTART_GOVERNED.md) runs all of it end to end, from a
spreadsheet export to a diff against whatever you use today. Driving `governed-batch` from another
runtime is [docs/JAVA_INTEROP.md](docs/JAVA_INTEROP.md), with a runnable Maven project in
[examples/java/](examples/java).

### Generation, extraction and scoring from the command line

```bash
acronymkit generate "Self Contained Underwater Breathing Apparatus" --top 3
```

```
Phrase:  Self Contained Underwater Breathing Apparatus
Primary: SCUBA  (score 27.264)

RANK  ACRONYM   SCORE  PRONOUNCE  DICT
----  -------  ------  ---------  ----
   1  SCUBA    27.264       0.75  yes
   2  SCOUBA   19.352       0.77  no
   3  SCUBRA   19.284       0.75  no

Score breakdown for SCUBA:
  TERM               VALUE  COEFF  CONTRIBUTION
  ----------------  ------  -----  ------------
  positional        50.000      1        50.000
  phonotactic       -2.943   0.25        -0.736
  lexical            1.000      2         2.000
  information_loss   0.000     25        -0.000
  total                                  27.264
```

Also available: `backronym`, `synthesize`, `extract`, `score`, `tokens`, `schema`, `version`. Every
command takes `--format json` for the schema-conformant payload, and `extract` reads stdin.

## Batch and async

```python
batch = engine.batch_generate(phrases, max_workers=8)
batch.succeeded          # results in submission order
batch.errors             # {index: message} — one failure never aborts the batch

results = await engine.abatch_generate(phrases, concurrency=16)
```

A single `AcronymEngine` is immutable and safe to share across threads and event loops.

## Interoperability

Results serialise to a versioned JSON Schema,
[`schemas/acronym-engine-result.schema.json`](schemas/acronym-engine-result.schema.json), shared with
the planned `acronym4j` Java port:

```python
from acronymkit.serialization import validate_result
validate_result(result.to_dict())      # raises if the payload drifts from the contract
```

## Data provenance

The bundled English lexicon is derived from **SCOWL** (size cut ≤ 60, 76,879 entries) and the syllable
validation from **CMUdict**. Both are permissively licensed and redistributed with their notices in the
resource headers. Every asset is pinned to a commit or release tarball and verified by SHA-256, because
a silent upstream edit to a word list changes Λ(A), which changes every score.

[`data/LICENSES.md`](data/LICENSES.md) is the ledger: source, licence, checksum, and — for anything not
redistributable — the reasoning for why not. `tools/build_lexicons.py` refuses to write a
non-redistributable asset into the package, so the rule is enforced by code rather than by diligence.

```bash
python tools/fetch_data.py --list        # the registry
python tools/fetch_data.py --verify      # re-check every checksum
```

## Honest scope

- **The governed subsystem's accuracy figure is about one function, and it was measured before its
  corpora were declared.** Catalog lookup is exact by construction; what is measured is where an
  identifier gets *cut*, against captions the publishers wrote. Every governed run records
  `splits_declaration = UNDECLARED`, and none has been re-measured since — so it is
  measured-before-declared, not held-out. On identifiers carrying no boundary mark at all, exact
  match falls to 34.93<!--claim:governed_gold.socrata.columns.unmarked.exact_pct:.2f--> % on Socrata
  and 0.75<!--claim:governed_gold.sec_xbrl.filer_extension.unmarked.exact_pct:.2f--> % on SEC filer
  extensions. Those rows ship in the same table as the headline, not beneath it.
- **Held-out evidence exists for span detection and for nothing else this README leads with.** PLOD
  and SDU@AAAI-21 AI are declared held out and uncontaminated in
  [`bench/splits.toml`](bench/splits.toml). MED1250 (extraction, generation) and SDU@AAAI-21 AD
  (disambiguation) are declared tuning and contaminated. SDU@AAAI-21 AD `test.json` is the one
  genuinely blind split still available, and it is deliberately unspent.
- **Extraction is evaluated on two corpora, both biomedical.** MED1250 is biomedical abstracts and
  is a *tuning* set — its miss taxonomy has been read in full. PLOD was added to close the
  domain-generalisation gap and turned out not to: it is PLOS journal text, also dominated by the
  life sciences. **No evidence exists for legal, financial or general-web text.** Treat the
  comparison as sound and the absolute level as provisional.
- **System rankings are corpus-dependent, and we have measured that.** `pyab3p` beats us on
  MED1250; we beat it on PLOD's span-detection task. Any single-corpus ranking, including ours,
  should be read with that in mind.
- **14.01<!--claim:oracle.med1250.universal_miss_pct:.2f--> % of that corpus is found by no system
  at all**, ours or anyone's. The practical ceiling is
  85.99<!--claim:oracle.med1250.oracle_union_recall:.2f--> % rather than perfect recall, and every
  figure here should be read against it.
- **English only.** French, Spanish and German ship no lexicon; those languages degrade honestly and
  say so in `metadata.warnings`.
- **Disambiguation is measured and it loses.** On SDU@AAAI-21 it scores
  41.65<!--claim:disambiguation.sdu21.acronymkit.accuracy:.2f--> % accuracy against
  72.84<!--claim:disambiguation.sdu21.most_frequent.accuracy:.2f--> % for simply always picking the
  most common expansion. It beats random, so the context
  signal is real, but on that benchmark it is worth less than memorising frequencies. Use it for
  document-local resolution, where inline definitions carry it; do not expect it to win a
  disambiguation benchmark.
- **Abstention is a precision instrument, not an accuracy fix, and there is a region where it is
  worse than doing nothing.** Raising `min_margin` lowers F1 monotonically, and below gate `0.10`
  the shared task's own most-frequent-expansion baseline beats the gated system on the gated
  system's own answered subset. Read against that baseline at **full** coverage —
  72.84<!--claim:disambiguation.sdu21.abstention_curve.gate_0.00_most_frequent_accuracy_same_subset:.2f--> % —
  no gate on the published curve wins until `0.15`, where the system answers
  16.77<!--claim:disambiguation.sdu21.abstention_curve.gate_0.15_coverage_pct:.2f--> % of the split
  at F1 20.95<!--claim:disambiguation.sdu21.abstention_curve.gate_0.15_f1:.2f-->. At the gate where
  the pooled same-subset comparison crosses over, the baseline still wins on three- and
  four-candidate sets —
  32.38<!--claim:disambiguation.sdu21.abstention_curve.instances_in_those_arities_pct:.2f--> % of
  that split. The curve, the losing comparison and the decomposition are in
  [docs/EVALUATION.md](docs/EVALUATION.md).
- **The default `disambiguate` path performs no selection.** With no `dictionary=` it is an
  inline-definition lookup: no candidate at all on
  97.45<!--claim:disambiguation.sdu21.diagnosis.default_path.no_candidate_pct:.2f--> % of that
  split's instances. If you came here for disambiguation, pass a dictionary.
- Every *measured* figure in this README is traceable to [`bench/results.json`](bench/results.json),
  and CI fails the build if a performance claim anywhere in the docs or the source cannot be traced
  back to a benchmark run. The structural counts above — share of the source, of the public symbols,
  of the CLI commands — are not benchmark results; they are re-derived from the tree, and the
  commands that derive them are in [docs/EVALUATION.md](docs/EVALUATION.md).

## Documentation

- [Architecture](docs/ARCHITECTURE.md) — subsystem map, tier policy, resource formats, extension points
- [Governed naming](docs/GOVERNED_NAMING.md) — deterministic short→long expansion against a schema
  catalog: the custom-first precedence chain, every verb with real output, the four invariants, and
  why refusing to guess is the right design for governed data
- [Governed naming in five minutes](docs/QUICKSTART_GOVERNED.md) — the same subsystem from the
  command line, from a spreadsheet export to a whole schema in one process, ending in a diff against
  the implementation you have now
- [Technical note: the governed JSON wire contract](docs/notes/governed-json-contract.md) — the exact
  JSON shape of every DTO and fixture, written so a port can be validated against the same golden
  files. No JVM artifact exists; this is what would make writing one mechanical
- [Calling this library from the JVM](docs/JAVA_INTEROP.md) — which route a Java Maven project should
  take and what each one needs on the machine: the `governed-batch` co-process, GraalPy as a Maven
  dependency, Py4J, JPype and a hand-written port, with the measurements behind the recommendation
- [`examples/java/`](examples/java) — a runnable Maven project for the recommended route: a
  co-process client, the wire format by hand, and the real output. No CI job builds it
- [Contributing](CONTRIBUTING.md) — the invariants that are easy to break by accident
- [Technical note: using a ranking function as a generation objective](docs/notes/scoring-objective.md)
- [Evaluation](docs/EVALUATION.md) — every measured number, with the losing comparison beside each
  one: governed cut placement and its flatcase rows, extraction against four other systems,
  generation recall@k, disambiguation against a trivial baseline, and the abstention curve scored
  against that same baseline on its own answered subset
- [Decisions](docs/DECISIONS.md) — what was tried and rejected, and why
- [Definition of done](docs/DEFINITION-OF-DONE.md) — the eight criteria this library is held to,
  swept and verdicted: which are met, which are not, what evidence each rests on, and the ninth
  criterion nobody had written down — that neither the flagship extraction figure nor the
  disambiguation figure has a corpus that could adjudicate it
- [Enterprise review](docs/ENTERPRISE.md) — the short answer for someone deciding whether to allow
  this package: air-gapped install, security posture with each claim's proof named, and the exact
  error text when something is missing
- [Support matrix](docs/SUPPORT_MATRIX.md) — capability by tier by "works offline" by "what it
  needs", including what English ships that fr/es/de do not
- [Offline and air-gap review](docs/OFFLINE.md) — the long form: how the no-network claim was
  measured, what the measurements cannot see, and how to reproduce them
- [Installing without PyPI](docs/INSTALL.md) — release-asset wheel, git tag, source checkout, or a
  per-platform offline bundle that installs with `--no-index` and needs no package index at all
- [Security policy](SECURITY.md) — threat model and disclosure
- [Changelog](CHANGELOG.md)

## Extending

| You want to… | Do this |
|---|---|
| Use a bigger dictionary | `Config(lexicon_path=Path("/usr/share/dict/words"))` |
| Score against a domain corpus | `CharNGramModel.train(my_words)` → JSON → `Config(ngram_model_path=…)` |
| Add a language | Add `stopwords_<lang>.json` + `lexicon_<lang>.txt`, generate `ngram_<lang>.json`, add a `Language` member |
| Change ranking | `Config(scoring_strategy=ScoringStrategy.CUSTOM, scoring_weights=ScoringWeights(...))` |
| Suppress domain noise | `Config(custom_stop_words=frozenset({"solution", "platform"}))` |
| Plug in your own tagger | Implement the `NlpBackend` protocol |

## Roadmap

- **Phase 1 — Tier 0 engine and extractive foundation.** ✅ Shipped in 0.1.0
- **Phase 2 — Statistical NLP and phonetic scoring.** ✅ Shipped in 0.1.0
- **Phase 3 — Tier 2 neural disambiguation.** Quantised sentence encoder via ONNX Runtime (no PyTorch
  runtime dependency), indexed against SciAD/GLADIS-scale expansion dictionaries.
  `LexicalDisambiguator` already implements the contract the neural backend will satisfy, and
  `EngineTier.NEURAL` is accepted today, so selecting it is forward-compatible.
- **Phase 4 — `acronym4j` on Maven Central.** API parity, byte-identical JSON, same schema.

## Licence

[MIT](LICENSE)
