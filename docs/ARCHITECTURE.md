# acronymkit — Architecture

## Why this library exists

The open-source acronym ecosystem is split into four tiers that do not talk to each other:

| Tier | Representative work | What it does well | Where it stops |
|---|---|---|---|
| Naive string utilities | `acronymcreator`, countless gists | Sub-millisecond, no dependencies | No tokenisation grammar, no phonetics, no semantics |
| Corpus matchers | ACRONYM (Cook, 2019) | Finds candidates that spell real words | Offline batch, static corpus, no library bindings |
| Rule-based extractors | Schwartz & Hearst (2003) in scispaCy, Blackstone | F₁ > 96 % on inline definitions, cheap | Strictly extractive; needs the definition present in the span |
| Neural disambiguators | AcroBERT, SDU/SciAD/GLADIS models | Resolves standalone acronyms from context | GPU-bound, slow cold start, research codebases |

Nothing spans them. A production system that needs to *generate* an acronym, *extract* the ones already
defined in a document, and *resolve* the ones that are not, has to stitch three incompatible codebases
together. `acronymkit` is that missing single library: bi-directional, multi-tiered, and typed.

## Subsystem map

```
                                  ┌──────────────────────────────┐
   text / phrase  ───────────────▶│        AcronymEngine         │  facade, thread-safe,
                                  │   (engine.py, batch.py)      │  constructed once
                                  └───────────────┬──────────────┘
                                                  │
        ┌──────────────────────┬──────────────────┼───────────────────┬────────────────────┐
        ▼                      ▼                  ▼                   ▼                    ▼
┌───────────────┐    ┌──────────────────┐  ┌───────────────┐  ┌───────────────┐  ┌──────────────────┐
│ ForwardGen    │    │ BackronymGen     │  │ Abbreviation  │  │ Lexical       │  │ Serialization    │
│ generator.py  │    │ backronym.py     │  │ Extractor     │  │ Disambiguator │  │ serialization.py │
│               │    │                  │  │ extractor.py  │  │ disambig.py   │  │ + JSON Schema    │
│ beam search   │    │ k-best DP        │  │ Schwartz &    │  │ context        │  │                  │
│ over tokens   │    │ alignment        │  │ Hearst 2003   │  │ overlap        │  │                  │
└───────┬───────┘    └────────┬─────────┘  └───────┬───────┘  └───────┬───────┘  └──────────────────┘
        │                     │                    │                  │
        └──────────┬──────────┘                    │                  │
                   ▼                               │                  │
          ┌─────────────────┐                      │                  │
          │  Scorer         │  S(A,T) = α·Σω + β·Φ + γ·Λ − δ·Ψ        │
          │  scoring.py     │                      │                  │
          └────┬───────┬────┘                      │                  │
               │       │                           │                  │
     ┌─────────▼──┐ ┌──▼───────────┐               │                  │
     │ Lexicon    │ │ CharNGram    │               │                  │
     │ lexicon.py │ │ phonetics.py │               │                  │
     │   Λ(A)     │ │    Φ(A)      │               │                  │
     └─────┬──────┘ └──────┬───────┘               │                  │
           │               │                       │                  │
           └───────┬───────┴───────────────────────┴──────────────────┘
                   ▼
          ┌──────────────────┐        ┌─────────────────────┐        ┌──────────────────┐
          │  Tokenizer       │◀───────│  StopWordRegistry   │◀───────│  resources/      │
          │  tokenizer.py    │        │  stopwords.py       │        │  bundled data    │
          └────────┬─────────┘        └─────────────────────┘        └──────────────────┘
                   │
                   ▼
          ┌──────────────────────────────────────────────┐
          │  NLP backend  (nlp/)                         │
          │  Heuristic (Tier 0) │ spaCy │ NLTK (Tier 1)  │
          │  fills .pos/.lemma, refines .is_critical     │
          └──────────────────────────────────────────────┘
```

Everything above `Tokenizer` consumes frozen Pydantic DTOs from `models.py`; nothing mutates state
after construction, which is what makes a single `AcronymEngine` safe to share across a thread pool or
an asyncio event loop.

## Execution tiers

| Tier | `EngineTier` | Dependencies | Typical latency | Use it for |
|---|---|---|---|---|
| 0 | `ZERO_DEPENDENCY` | stdlib + Pydantic | sub-millisecond | Edge instances, high-throughput indexing, hot paths |
| 1 | `STATISTICAL_NLP` | spaCy **or** NLTK | single-digit ms | POS-aware generation where function words must not survive |
| 1 | `HYBRID_NLP` | optional | tier 1 or tier 0 | Production default: uses NLP when present, degrades with a warning when not |
| 2 | `NEURAL` | ONNX Runtime | tens of ms | Contextual disambiguation of standalone acronyms — **Phase 3, not in this release** |
| — | `AUTO` | — | — | Resolve to the best tier available at import time |

Tier resolution happens once, in `AcronymEngine.__init__`, via `nlp.base.resolve_backend`. Degradation
is never silent in the payload: the effective tier lands in `metadata.engine_tier`, what you asked for
lands in `metadata.requested_tier`, and the reason lands in `metadata.warnings`. Set `Config.strict` to
turn degradation into a `TierUnavailableError` instead.

## The scoring function

```
S(A, T) = α · Σᵢ ω(cᵢ, w_j(i))  +  β · Φ(A)  +  γ · Λ(A)  −  δ · Ψ(T, A)
```

| Term | Meaning | Implementation |
|---|---|---|
| `ω(cᵢ, w)` | Positional mapping weight: **10** when `cᵢ` is the initial character of `w`, **3** when internal or terminal, **2** when it directly follows a previously matched character of the same token | `scoring.build_mappings` → `MappingKind` |
| `Φ(A)` | Phonotactic pronounceability: mean character-bigram log-likelihood, `(1/(k−1))·Σ log P(c_{m+1} \| c_m)` | `phonetics.CharNGramModel.score` |
| `Λ(A)` | Lexical match indicator: 1 when `A` is a word in the target lexicon (a successful backronym), else 0 | `lexicon.Lexicon.__contains__` |
| `Ψ(T, A)` | Information loss: count of semantically critical tokens not represented in `A` | `scoring.Scorer.information_loss` |

`α, β, γ, δ` are configurable. The four `ScoringStrategy` presets are just named weight vectors — tune
toward literal initialisation, pronounceability, or dictionary backronyms without touching code.

Every candidate carries a `ScoreBreakdown`, so a ranking decision can always be explained:

```python
candidate.breakdown.explain()
# 'S = 1*30.000 + 12*-2.914 + 25*0.000 - 8*0.000 = -4.968'
```

### `T_critical`

`Ψ` only counts tokens flagged `is_critical`. At Tier 0 that means "content word that survived
stop-word filtering". At Tier 1 the NLP backend refines it using real POS tags, so `NOUN`, `PROPN`,
`VERB`, `ADJ` and `NUM` stay critical while `DET`, `ADP`, `CCONJ`, `PRON`, `AUX` and `PART` do not.
This is the mechanism by which Tier 1 produces better acronyms than Tier 0 on messy human text.

## Bundled resource formats

All under `src/acronymkit/resources/`, validated in CI by `tools/validate_resources.py`.

**`stopwords_<lang>.json`** — function words keyed by the eight `StopWordCategory` values. A word
appears in exactly one category, lists are sorted and unique. Categorising rather than flattening is
what lets `include_articles`, `include_prepositions` and `include_conjunctions` be toggled independently.

**`lexicon_<lang>.txt`** — one lowercase word per line, sorted, unique, letters only, `#` comments
allowed at the top. Backs `Λ(A)` and trains the n-gram model. Override with `Config.lexicon_path` to
plug in SCOWL, `/usr/share/dict/words`, or a domain vocabulary.

**`ngram_<lang>.json`** — add-k smoothed character-bigram model in natural-log space, with `^`/`$`
boundary symbols and an explicit `backoff_log_prob` for unseen transitions. Generated from the lexicon
by `tools/build_ngram_model.py` and committed; CI's `--check` mode fails the build if the two drift
apart.

## Extension points

| You want to… | Do this |
|---|---|
| Use a bigger dictionary | `Config(lexicon_path=Path("/usr/share/dict/words"))` |
| Score pronounceability against a domain corpus | `CharNGramModel.train(my_words)` → write JSON → `Config(ngram_model_path=...)` |
| Add a language | Add `stopwords_<lang>.json`, `lexicon_<lang>.txt`, generate `ngram_<lang>.json`, add a `Language` member |
| Change ranking behaviour | `Config(scoring_strategy=ScoringStrategy.CUSTOM, scoring_weights=ScoringWeights(alpha=…, beta=…))` |
| Suppress domain noise | `Config(custom_stop_words=frozenset({"solution", "platform"}))` |
| Plug in your own tagger | Implement the `NlpBackend` protocol (`name`, `is_available`, `annotate`) |
| Resolve acronyms against your own vocabulary | `ExpansionDictionary` + `engine.disambiguate(...)` |

## Roadmap seams

**Phase 3 — Tier 2 neural disambiguation.** `disambiguation.LexicalDisambiguator` already implements
the `disambiguate(acronym, context) -> DisambiguationResult` contract that the neural backend will
satisfy. The plan is a quantised sentence encoder executed through ONNX Runtime (avoiding a PyTorch
runtime dependency), indexed against SciAD/GLADIS-scale expansion dictionaries loaded through
`ExpansionDictionary`. `EngineTier.NEURAL` is already accepted by the config and currently degrades
with an explicit warning, so selecting it today is forward-compatible.

**Phase 4 — `acronym4j` on Maven Central.** The Java port mirrors this package structure and must emit
byte-identical JSON for the same input and configuration. `schemas/acronym-engine-result.schema.json`
is the shared contract, and it is versioned independently of either implementation. The Java side uses
builder patterns over the same option names, immutable DTOs, and the same `ScoringWeights` defaults.

## Design decisions worth knowing

- **Frozen DTOs everywhere.** Results are cacheable and shareable with no defensive copying. The cost
  is that annotation passes rebuild tokens via `model_copy(update=...)` rather than mutating.
- **`scoring.py` has no runtime import of `lexicon.py` or `phonetics.py`.** Those types are imported
  under `TYPE_CHECKING` only, and the `Scorer` duck-types what it is handed. The dependency graph stays
  acyclic, and a caller can substitute their own `Λ`/`Φ` implementations.
- **The plain initialism is always a candidate.** Beam search is free to explore multi-character and
  skip-token branches, but the naive first-letter acronym is injected unconditionally so that
  `"Portable Document Format"` can never fail to produce `"PDF"`.
- **Extraction is span-exact.** Every `AcronymPair` carries offsets that satisfy
  `text[span[0]:span[1]] == form`, so downstream annotation and highlighting need no re-matching.
- **Pydantic is a hard dependency, but nothing else is.** "Zero-dependency" in Tier 0 means no NLP or ML
  runtime, not literally no third-party package — the typed, validating DTO layer is worth one small
  well-maintained dependency, and CI proves nothing heavier sneaks in.
