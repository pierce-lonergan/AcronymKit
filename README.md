# acronymkit

[![CI](https://github.com/pierce-lonergan/AcronymKit/actions/workflows/ci.yml/badge.svg)](https://github.com/pierce-lonergan/AcronymKit/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/python-3.9%20%7C%203.10%20%7C%203.11%20%7C%203.12%20%7C%203.13-blue)](https://pypi.org/project/acronymkit/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![Typed](https://img.shields.io/badge/typing-py.typed-informational)](https://peps.python.org/pep-0561/)

**Bi-directional, multi-tiered acronym processing for production systems.**
Generate acronyms from text, synthesise backronyms, extract abbreviations already defined in a
document, and resolve ambiguous ones from context — from one typed library with a Tier 0 path that
needs nothing but the standard library.

```python
from acronymkit import AcronymEngine

engine = AcronymEngine()
engine.generate("Application Programming Interface").primary_acronym   # 'API'
engine.generate("Portable Document Format").primary_acronym            # 'PDF'
```

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

### Forward generation

```python
from acronymkit import AcronymEngine, Config
from acronymkit.enums import EngineTier, ScoringStrategy

engine = AcronymEngine(Config(
    engine_tier=EngineTier.HYBRID_NLP,
    scoring_strategy=ScoringStrategy.BALANCED_PRONOUNCEABLE,
    include_articles=False,
    min_word_length=2,
    max_acronym_length=6,
))

result = engine.generate("Application Programming Interface")
result.primary_acronym                    # 'API'
result.score                              # 20.912
result.primary.breakdown.explain()
# 'S = 1*30.000 + 1*-3.088 + 12*0.000 - 15*0.000 = 20.912'

[(c.acronym, round(c.score, 2)) for c in result.alternatives[:4]]
# [('API', 20.91), ('APRI', 17.46), ('APIN', 17.42), ('APPI', 16.84)]
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

With no dictionary supplied, the engine builds one from the document's own inline definitions, so a
term defined once on first use resolves everywhere afterwards.

### Multilingual

Categorised stop-word taxonomies, lexicons and character models ship for English, French, Spanish and
German:

```python
from acronymkit.enums import Language
AcronymEngine(Config(language=Language.FR)).generate("Système de Gestion de Base de Données")  # SGBD
AcronymEngine(Config(language=Language.DE)).generate("Allgemeine Deutsche Automobil Club")     # ADAC
```

## Execution tiers

| Tier | `EngineTier` | Dependencies | Latency | Use for |
|---|---|---|---|---|
| 0 | `ZERO_DEPENDENCY` | stdlib + Pydantic | **~95 µs/call** | Edge, high-throughput indexing, hot paths |
| 1 | `STATISTICAL_NLP` | spaCy **or** NLTK | single-digit ms | POS-aware generation on messy human text |
| 1 | `HYBRID_NLP` | optional | either | Production default — degrades gracefully |
| 2 | `NEURAL` | ONNX Runtime | — | **Phase 3, not in this release** |
| — | `AUTO` | — | — | Best tier available at import time |

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

`Φ` behaves the way you would hope: Φ("SCALE") = −2.36, Φ("PDF") = −6.74, Φ("XKCD") = −7.28.

### Presets

`ScoringStrategy` selects a calibrated `(α, β, γ, δ)` vector:

| Strategy | Behaviour |
|---|---|
| `STRICT_INITIALISM` | Positional fidelity dominates |
| `BALANCED_PRONOUNCEABLE` | **Default.** Coverage first; pronounceability and dictionary hits break ties |
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

The defaults are calibrated rather than guessed: they were grid-searched against a corpus of textbook
initialisms (API, PDF, NASA, HTML, RAM, CPU, GPU, SCUBA, LASER, SQL, CRM, QA, TCP, SOAP, BIOS, ROM)
and reproduce **all sixteen** as the primary result. The winning region is a broad plateau — 266 of
640 sampled vectors satisfy every case — and `tests/test_scoring_presets.py` pins the corpus so
retuning cannot silently regress it.

> **One deliberate deviation from the published formulation.** The positional term is a *sum*, so it
> grows monotonically with length — used unmodified as a generation objective it prefers `PODOFO` to
> `PDF`. `ScoringWeights.length_penalty` (default 6.0) closes that gap, sitting between
> `contiguous_weight` (2) and `initial_weight` (10) so that covering a new token nets +4 while taking
> a second letter from a token already used nets −4. Set `length_penalty=0.0` to recover the
> unmodified objective exactly.

## Command line

```bash
pip install "acronymkit[cli]"
```

```bash
acronymkit generate "Self Contained Underwater Breathing Apparatus" --top 3
```

```
Phrase:  Self Contained Underwater Breathing Apparatus
Primary: SCUBA  (score 41.023)

RANK  ACRONYM   SCORE  PRONOUNCE  DICT
----  -------  ------  ---------  ----
   1  SCUBA    41.023       0.70  yes
   2  SCOUBA   25.353       0.72  no
   3  SECUBA   25.213       0.71  no

Score breakdown for SCUBA:
  TERM               VALUE  COEFF  CONTRIBUTION
  ----------------  ------  -----  ------------
  positional        50.000      1        50.000
  phonotactic       -2.977      1        -2.977
  lexical            1.000     12        12.000
  information_loss   0.000     15        -0.000
  total                                  41.023
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

## Documentation

- [Architecture](docs/ARCHITECTURE.md) — subsystem map, tier policy, resource formats, extension points
- [Contributing](CONTRIBUTING.md) — the invariants that are easy to break by accident
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
