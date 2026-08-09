# Contributing to acronymkit

Thanks for your interest. This document covers the invariants that are easy to break
accidentally — please read the "Non-negotiables" section before opening a PR.

## Development setup

```bash
git clone https://github.com/pierce-lonergan/AcronymKit.git
cd AcronymKit
python -m venv .venv && . .venv/bin/activate     # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
pytest
```

Optional tiers:

```bash
pip install -e ".[nlp]"           # Tier 1: spaCy / NLTK
python -m spacy download en_core_web_sm
python -m nltk.downloader averaged_perceptron_tagger punkt
```

## Non-negotiables

1. **Python 3.9 compatibility.** Annotations use PEP 585 builtin generics (`list[str]`) but never
   PEP 604 unions — write `Optional[X]`, not `X | None`. Every module starts with
   `from __future__ import annotations`. No `match` statements.
2. **Tier 0 purity.** `resources`, `stopwords`, `tokenizer`, `lexicon`, `phonetics`, `scoring`,
   `generator`, `backronym`, `extractor`, `disambiguation` and `serialization` may import only the
   standard library, `pydantic`, and each other. CI enforces this: the `zero-dependency` job installs
   the base package alone and asserts that no optional dependency ends up in `sys.modules` after a
   generate + extract round trip.
3. **Optional dependencies are lazily imported** inside functions, guarded by `try/except ImportError`,
   and their absence degrades gracefully (or raises `TierUnavailableError` when `Config.strict`).
4. **Determinism.** No `random`, no wall-clock-dependent behaviour, no reliance on set iteration order
   in anything that reaches the output. Candidate lists sort on a total key such as
   `(-score, len(acronym), acronym)`.
5. **Frozen models.** Every DTO in `models.py` is a frozen Pydantic model. Produce new objects with
   `model_copy(update=...)` rather than mutating.
6. **No network access** at import time or run time, in the library or in `tools/`.

## Resource files

Bundled data lives in `src/acronymkit/resources/` and its formats are frozen — see
`docs/ARCHITECTURE.md`. Two checks guard them:

```bash
python tools/validate_resources.py --require   # format, sorting, uniqueness, disjointness
python tools/build_ngram_model.py --check      # committed n-gram models match their lexicons
```

If you change a lexicon you **must** regenerate its n-gram model and commit both:

```bash
python tools/build_ngram_model.py --language en
```

Adding a language means adding `stopwords_<lang>.json`, `lexicon_<lang>.txt`, a generated
`ngram_<lang>.json`, and a `Language` enum member.

## Tests

```bash
pytest                       # everything
pytest -m "not slow"         # skip the slower search/property tests
pytest -m nlp                # Tier 1 tests (skipped when no backend is installed)
pytest --cov=acronymkit --cov-report=term-missing
```

New behaviour needs a test. Bug fixes need a regression test that fails before the fix. Tests that
require an optional dependency must be marked (`@pytest.mark.nlp`) and skip cleanly when it is absent.

## Style

`ruff` is both linter and formatter; `mypy` runs over `src/acronymkit` with
`disallow_untyped_defs`. Run all three before pushing:

```bash
ruff format src tests tools && ruff check --fix src tests tools && mypy && pytest
```

Public classes and functions need Google-style docstrings with `Args:` / `Returns:` / `Raises:`.

## Changing the scoring function

`scoring.py` implements the published objective

```
S(A, T) = α·Σ ω(cᵢ, w_j(i)) + β·Φ(A) + γ·Λ(A) − δ·Ψ(T, A)
```

Changing the *shape* of that formula is a breaking change and needs an issue first. Retuning the
coefficients is not — those live in `ScoringWeights` and the `STRATEGY_WEIGHTS` presets, and any
change there must come with before/after output for the phrases in `tests/test_generator.py`.

## Cross-language parity

`acronym4j` (Maven Central, Phase 4) must produce byte-identical JSON for the same input and config.
Anything that changes the output payload — new field, renamed field, changed default — must also
update `schemas/acronym-engine-result.schema.json` and be noted in `CHANGELOG.md` under a
**Cross-language impact** heading.

## Releasing

1. Update `CHANGELOG.md` and bump `version` in `pyproject.toml`.
2. Tag `vX.Y.Z` and publish a GitHub release; `.github/workflows/publish.yml` builds and uploads to
   PyPI via trusted publishing (no stored token).
3. Dry-run first with the `workflow_dispatch` trigger targeting `testpypi`.

## Licence

Contributions are accepted under the [MIT Licence](LICENSE).
