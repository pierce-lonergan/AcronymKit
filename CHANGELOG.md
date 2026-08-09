# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.0] — Unreleased

Initial public release. Delivers roadmap **Phase 1** (Tier 0 engine and extractive foundation) and
**Phase 2** (statistical NLP and phonetic scoring).

### Added

#### Forward generation
- `AcronymEngine.generate()` — beam-searched candidate enumeration over tokenised input, ranked by the
  composite objective `S(A, T) = α·Σω + β·Φ(A) + γ·Λ(A) − δ·Ψ(T, A)`.
- Positional mapping weights `ω` with the 10 / 3 / 2 schedule for initial, internal-or-terminal, and
  contiguous character matches, recorded per character in `AcronymCandidate.mappings` so every score is
  auditable.
- Phonotactic pronounceability index `Φ(A)` from a character-bigram language model, plus a normalised
  `pronounceability_score` in `[0, 1]` with no-vowel and consonant-run penalties.
- Lexical match indicator `Λ(A)` against a bundled or user-supplied dictionary.
- Information-loss penalty `Ψ(T, A)` over semantically critical tokens.
- Four scoring presets via `ScoringStrategy`: strict initialism, balanced pronounceable,
  max pronounceable, dictionary backronym — plus fully custom `ScoringWeights`.

#### Backronym synthesis
- `AcronymEngine.generate_backronym()` — k-best positional alignment of a source phrase onto a fixed
  target word.
- `AcronymEngine.synthesize_backronym()` — expansion of a target word from a vocabulary with no source
  phrase required.

#### Extraction and disambiguation
- `AcronymEngine.extract_definitions()` — Schwartz & Hearst (2003) right-to-left matching for inline
  parenthetical definitions, covering both `Long Form (Short Form)` and the inverted
  `Short Form (Long Form)` arrangement, with exact source spans and a confidence estimate.
- `AcronymEngine.disambiguate()` — lexical contextual resolution of standalone acronyms against an
  `ExpansionDictionary`, preferring document-local inline definitions. This is the seam the Phase 3
  neural backend plugs into.

#### Runtime tiers
- `EngineTier.ZERO_DEPENDENCY` (Tier 0) — pure standard library plus Pydantic.
- `EngineTier.STATISTICAL_NLP` / `HYBRID_NLP` (Tier 1) — spaCy or NLTK part-of-speech evidence, with
  `HYBRID_NLP` degrading to Tier 0 and recording a warning when no backend is installed.
- `EngineTier.AUTO` — resolve to the best available tier.
- `EngineTier.NEURAL` (Tier 2) — accepted and degraded with an explicit warning; the ONNX backend
  lands in Phase 3.

#### Tokenisation
- Unicode-aware tokeniser handling hyphenated and slashed compounds, camelCase and PascalCase splitting,
  numerals and ordinals, Latin elision, existing all-caps acronyms, and exact character offsets.
- Configurable `HyphenPolicy` and `NumeralPolicy`.
- Categorised stop-word taxonomies for English, French, Spanish and German, letting articles,
  prepositions, conjunctions, pronouns and auxiliaries be toggled independently.

#### Packaging and interoperability
- `schemas/acronym-engine-result.schema.json` — the cross-language JSON Schema contract shared with the
  planned `acronym4j` port.
- Fully typed, `py.typed`-marked distribution; frozen Pydantic v2 DTOs.
- Synchronous, thread-pool and `asyncio` batch APIs.
- `acronymkit` CLI (`generate`, `backronym`, `synthesize`, `extract`, `score`, `tokens`, `schema`).
- `tools/validate_resources.py` and `tools/build_ngram_model.py` for reproducible bundled data.

### Notes
- `requires-python` is `>=3.9` rather than the `>=3.8` in the original design note: Python 3.8 reached
  end of life in October 2024 and current Pydantic v2 releases no longer support it.
- **One deliberate deviation from the published objective function.** The positional term
  `α·Σω` is a sum, so it increases monotonically with acronym length; used unmodified as a
  *generation* objective it ranks `PODOFO` above `PDF`, because each extra character adds
  `contiguous_weight` and subtracts nothing. (The published formulation is a *ranking* function over
  candidates of a given length, so it never had to address this.) `ScoringWeights.length_penalty`
  adds `− length_penalty · max(0, |A| − preferred_length)`. Its default of `6.0` sits between
  `contiguous_weight` (2) and `initial_weight` (10), making "one letter per token, cover everything"
  the optimum by construction. Set `length_penalty=0.0` to recover the published objective exactly.
- The preset coefficient vectors were grid-searched against a corpus of sixteen textbook initialisms
  rather than chosen by hand; see `tests/test_scoring_presets.py`.
- `frozen=True` on the DTOs blocks attribute rebinding but does not deep-freeze `list`/`dict` fields,
  and the models are consequently not hashable. Treat results as read-only; see the `models` module
  docstring. Converting those fields to immutable sequences is deferred because it is a breaking
  change to the type annotations.
- The Tier 2 neural disambiguation engine (Phase 3) and the `acronym4j` Java port (Phase 4) are not
  part of this release.

[Unreleased]: https://github.com/pierce-lonergan/AcronymKit/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/pierce-lonergan/AcronymKit/releases/tag/v0.1.0
