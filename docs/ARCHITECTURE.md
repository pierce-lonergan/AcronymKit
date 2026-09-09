# acronymkit — Architecture

## Why this library exists

Four kinds of tool exist in the open-source acronym ecosystem, and each stops somewhere:

| Tier | Representative work | What it does well | Where it stops |
|---|---|---|---|
| Naive string utilities | `acronymcreator`, countless gists | Sub-millisecond, no dependencies | No tokenisation grammar, no phonetics, no semantics |
| Corpus matchers | ACRONYM (Cook, 2019) | Finds candidates that spell real words | Offline batch, static corpus, no library bindings |
| Rule-based extractors | Schwartz & Hearst (2003) in scispaCy, Blackstone | Few false positives on inline definitions, cheap | Strictly extractive; needs the definition present in the span |
| Neural disambiguators | AcroBERT, SDU/SciAD/GLADIS models | Resolves standalone acronyms from context | GPU-bound, slow cold start, research codebases |

**Nothing in that table addresses the case this library is built around**: a bare column token with no
sentence to lean on, a catalog somebody else owns, and a requirement to refuse rather than guess. That
is the governed subsystem, it is the one acronym task here that the table has no row for, and it is
what the rest of this map is arranged around.

This section used to conclude "`acronymkit` is that missing single library: bi-directional,
multi-tiered, and typed" — an argument that spanning four tiers is worth something to somebody. It is
retired. The commitment that replaces it, what it costs, and what would reverse it are in
[docs/POSITIONING.md](POSITIONING.md). The other four subsystems below are real, are measured
wherever they can be measured at all, and do not lead.

## The package boundary, and the measurement that put it there

`acronymkit` is split into three packages, and the seam is **not** a taste about tidiness. It is a
contract collision between two tokenizers, and the collision has a size.

| | Prose tokenisation (`acronymkit.nlp`) | Identifier tokenisation (`acronymkit.catalog`) |
|---|---|---|
| Punctuation | a clause boundary; discarded | `#`, `%`, `_`, `:`, `/` are **semantic tokens** |
| Whitespace | load-bearing; words are separated by it | absent; there is none to lean on |
| Parentheticals | pulled out of running morphology | not a construct that occurs |
| Non-ASCII | tolerated, NFKC-normalised | an unaccounted character, and a refusal |
| Length | irrelevant | a physical column constraint |
| Losing a character | routine and correct | the one thing it may never do |

Run either tokenizer over the other's input and characters are destroyed. `docs/DECISIONS.md`'s B1
finding measures it as character loss on `14.6560` % of distinct Socrata captions and `36.0072` % of
distinct SEC XBRL labels, and the same block is reproduced in
[docs/GOVERNED_NAMING.md](GOVERNED_NAMING.md). **Neither copy is adjudicated by
`tools/check_claims.py`**: both sit inside fenced blocks, which D-112 records as the largest
structural hole in that gate's coverage, and there is no run id in `bench/results.json` behind
either number. They are quoted here with that provenance rather than presented as gated figures.

A tokenizer whose input its sibling damages is a **package boundary**, not a setting. Domain
adaptation inside one engine handles a vocabulary difference; it does not handle two lexers that
cannot agree what a token is.

```
                        ┌───────────────────────────────┐
                        │      acronymkit.core          │   THE LEAF
                        │  conformal risk arithmetic    │   no regular expressions
                        │  the exception hierarchy      │   no lexical assets
                        │  immutable span coordinates   │   no string normalisation
                        └───────────────┬───────────────┘
                                        │  both may depend on it
                     ┌──────────────────┴──────────────────┐
                     │                                     │
        ┌────────────▼─────────────┐         ┌─────────────▼────────────┐
        │     acronymkit.nlp       │         │   acronymkit.catalog     │
        │  chunking (tokenizer)    │    ✗    │  identifier tokenisation │
        │  candidate extraction    │◀───✗───▶│  symbol handling         │
        │  parenthetical matching  │    ✗    │  casing decomposition    │
        │  document propagation    │         │  to_physical_name        │
        │  the Tier 1 backends     │         │  dictionary conformance  │
        └──────────────────────────┘         └──────────────────────────┘
```

**`catalog` never imports `nlp`. `nlp` never imports `catalog`. `core` imports neither** — not at
run time, not inside a function, not under `typing.TYPE_CHECKING`. That is enforced by
`tests/test_architecture_boundaries.py`, which walks the **abstract syntax tree** of every module
in the package and resolves every import, relative ones included, to an absolute name. It is
registered as `gates.architecture_boundaries`.

An AST walk rather than a grep, and the difference is measured rather than asserted: five shapes
write the same forbidden edge, and a grep for `from acronymkit.catalog` finds three of them and
misses two outright — `import acronymkit.catalog as _c` and `importlib.import_module` on a literal.
The test re-derives that `3` of `5` on every run.

### What the rule cannot see, stated here rather than discovered later

**The facade layer is exempt, and that is the loophole.** `engine.py`, `cli.py`,
`disambiguation.py`, `models.py` and the package `__init__` are in no layer and may import both
halves, because composing them is what a facade is for. Nothing stops a prose-tokenizer result
being handed to the identifier tokenizer inside `engine.py`: the collision would be back, one module
further out, with every rule green. **The rule is about a dependency graph and a dependency graph
cannot see a data flow.**

**Two of its three edges are tautologies on the tree it shipped against.** `catalog -> nlp` and
`nlp -> catalog` were never present — that is exactly why the split came out byte-identical — so
those two rules found nothing and could not have. The edge that became newly *possible* is
`core -> {nlp, catalog}`, because `core` did not exist before. A green run today is a statement
about one edge and a silence about two, and the registered mutation is the only evidence any of
the three can fail.

**And a computed import name defeats it.** `importlib.import_module(name)` where `name` is a
variable is invisible to every static instrument, this one included. That limit is pinned as a
deliberately-failing-to-fire test rather than left to be rediscovered.

### `core` is a leaf, and it is bare

`acronymkit.core` imports **nothing** from anywhere else in the package at run time. Its single
in-package edge is `acronymkit.core.conformal` naming `DisambiguationResult` under `TYPE_CHECKING`
for annotations; every use is duck-typed attribute access, so `import acronymkit.core` binds no
sibling and no Pydantic DTO. That is checked twice, statically and at run time — one test imports
`acronymkit.core` in a fresh interpreter, touches every name in its `__all__`, and asserts neither
sibling is in `sys.modules`.

The three absences that define it — no regular expression, no lexical asset, no string
normalisation — were a docstring claim until the same gate started reading them off the syntax
tree.

### The compatibility decision, and how long it holds

Every public import path that existed before the split still resolves, and resolves to **the same
objects**:

| Old path | Now defined in |
|---|---|
| `acronymkit.governed`, and all thirteen submodules | `acronymkit.catalog` |
| `acronymkit.extractor` | `acronymkit.nlp.extractor` |
| `acronymkit.propagation` | `acronymkit.nlp.propagation` |
| `acronymkit.tokenizer` | `acronymkit.nlp.tokenizer` |
| `acronymkit.exceptions` | `acronymkit.core.exceptions` |
| `acronymkit.conformal` | `acronymkit.core.conformal` |

Identity, not equality: `acronymkit.governed.expand_identifier is acronymkit.catalog.expand_identifier`,
and `acronymkit.governed.tokenizer is acronymkit.catalog.tokenizer`. A shim that rebound names to
fresh classes would satisfy every `==` in the suite and fail the first time somebody wrote `except`
or `isinstance` across the two paths — which is the moment a compatibility shim exists for. All
nineteen paths are asserted, per path, in `tests/test_architecture_boundaries.py`.

**Why a shim rather than a clean break.** `acronymkit.governed` is named in `README.md`, in
[docs/GOVERNED_NAMING.md](GOVERNED_NAMING.md), in the CLI, and in `docs/DECISIONS.md` — and the
last of those is a file only the recorder may edit. Breaking the path would leave this project's
own decision record citing an import that no longer exists, which is a worse outcome for a
governance instrument than carrying a shim.

**How long: through the whole of the `0.x` line.** Removal requires a major version and a
`DeprecationWarning` announced in a minor release at least one release ahead of it. No warning is
emitted today, deliberately — nothing inside this package imports through the old paths any more,
so the only emitter would be a caller who cannot act on it until that cycle opens.

**What did change:** `__module__` on every moved class. An uncaught traceback now prints
`acronymkit.core.exceptions.ConfigurationError` where it printed `acronymkit.exceptions.ConfigurationError`.
One doctest in the tree pinned the old spelling and was updated; nothing in this package matches on
that string.

**What did NOT change: any output.** The split was verified byte-identical over `3,619,227` records —
every field of every record including `entry_id`, `source`, `confidence`, `beat`, `class_word`,
`is_known`, `is_fully_known` and `unaccounted`, plus the `repr` of every object. See `CHANGELOG.md`.

**Read the scope of that exactly, because an earlier draft of this sentence did not.** The `3,610,791`
**catalog** records were taken over the two governed corpora, Socrata and SEC XBRL. The `4,215`
extraction and `4,215` propagation records were taken over **MED1250 and PLOD-CW**; the harness runs
no extraction on the governed corpora at all. This paragraph previously read *"every catalog,
extraction and propagation output on Socrata and SEC XBRL"*, which claims a demonstration for all
three families on governed data that was never performed. `CHANGELOG.md` had it right throughout.
The harness itself is **not committed**, so no second party can re-run any of it — see D-120.

**What is still called `governed`, and stays that way:** every type name
(`GovernedDictionary`, `GovernedEntry`, `GovernedNamer`), the documentation page, the CLI verbs,
and — most importantly — every `governed_*` run id in `bench/results.json`. A run id is the
identity of a measurement; renaming one silently re-points every citation of it. "Governed" is the
posture (refuse rather than guess); "catalog" is the thing this half is *about*.

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

Everything above `Tokenizer` consumes frozen Pydantic DTOs from `models.py`; nothing the engine builds
mutates state after construction, which is what makes a single `AcronymEngine` safe to share across a
thread pool or an asyncio event loop.

That guarantee is about what the engine *builds*. Four of those collaborators can instead be supplied
by the caller (see **Extension points**), and an injected object may hold whatever state it likes — so
an engine constructed with `backend=`, `tokenizer=`, `extractor=` or `scorer=` is exactly as
thread-safe as the object passed in, and no more. An engine constructed from a `Config` alone keeps
the unconditional guarantee.

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

Passing `backend=` replaces resolution rather than its result: `resolve_backend` is not called, no
availability probe runs, no degradation warning is produced, and `Config.strict` therefore has nothing
to raise about — supplying the annotator *is* the availability decision. `metadata.engine_tier` is
recomputed from the supplied backend's `name` (`"heuristic"` reads as Tier 0, anything else as Tier 1),
so it still names the tier that actually ran, and `metadata.requested_tier` still records what the
configuration asked for.

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
| Plug in your own tagger | Implement `acronymkit.NlpBackend` (`name`, `is_available`, `annotate`), then `AcronymEngine(config, backend=MyTagger())` |
| Replace the tokenizer or the definition extractor | `AcronymEngine(config, tokenizer=..., extractor=...)` |
| Add a scoring term | Subclass `Scorer`, override `score`, then `AcronymEngine(config, scorer=MyScorer(config))` — read the limit below first |
| Resolve acronyms against your own vocabulary | `ExpansionDictionary` + `engine.disambiguate(...)` |

The four collaborators are keyword-only, replace exactly the object the engine would otherwise have
built, and are plain constructor arguments: no registry, no entry-point group, no discovery, nothing
resolved at import time.

**What a custom `Scorer` does and does not control.** It owns the ranking of every candidate the engine
returns. It does not own the search that produced them: `ForwardGenerator._beam_bound` re-derives the
objective in closed form from `ScoringWeights` and never calls the scorer, so a custom term re-ranks the
states the search retained and cannot make it retain one it would otherwise have cut. That limit binds
only when the search discards something, and the result usually says whether it did —
`metadata.truncated is False` means no cut and no budget discarded anything, so the custom scorer ranked
every candidate the search reached. The one exception is `allow_token_skipping=False` with a
`max_acronym_length` every remaining branch overflows: the search abandons its frontier unscored and
returns the plain initialism alone, with `truncated` still `False`. Raising `Config.max_search_nodes`
until the whole space fits removes
the frontier cut entirely (the *exhaustive* regime described in `generator.py`), which is the supported
way to make a custom objective decisive on a phrase where it currently is not. See "Substituting a
scorer" in `scoring.py` for the full statement.

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
  under `TYPE_CHECKING` only, and the `Scorer` duck-types what it is handed — a `Λ` needs only
  `contains(word) -> bool`, a `Φ` only `score(acronym)` and `normalized_score(acronym)`. The dependency
  graph stays acyclic, and a caller can substitute their own implementations *at run time*. They are not
  yet substitutable under a type checker: the constructor is annotated with the concrete `Lexicon` and
  `CharNGramModel`, so mypy rejects a substitute that the code accepts. Naming those two duck-types as
  exported protocols would close the gap and is not done here.
- **The plain initialism is always a candidate.** Beam search is free to explore multi-character and
  skip-token branches, but the naive first-letter acronym is injected unconditionally so that
  `"Portable Document Format"` can never fail to produce `"PDF"`.
- **Extraction is span-exact.** Every `AcronymPair` carries offsets that satisfy
  `text[span[0]:span[1]] == form`, so downstream annotation and highlighting need no re-matching.
- **Pydantic is a hard dependency, but nothing else is.** "Zero-dependency" in Tier 0 means no NLP or ML
  runtime, not literally no third-party package — the typed, validating DTO layer is worth one small
  well-maintained dependency, and CI proves nothing heavier sneaks in.
