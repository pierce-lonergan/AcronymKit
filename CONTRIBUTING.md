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
6. **No network access in the library**, at import time or run time — the claim `docs/OFFLINE.md`
   is built on, and the `air-gap` job is what holds it. `tools/` is a different rule and this line
   used to state it wrongly: `tools/fetch_data.py` exists to fetch corpora and calls
   `urllib.request.urlopen`, and `tools/build_gold_corpus.py` and `tools/make_offline_bundle.py`
   reach the network too. The rule for `tools/` is that nothing in it is imported by the package,
   every fetch is pinned by SHA-256, and no fetched byte is written into `src/acronymkit/resources/`
   without a redistributable licence — enforced by `tools/build_lexicons.py`, not by this sentence.

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

`ruff` is both linter and formatter; `mypy` runs over `src/acronymkit`, `tools` and `bench` — the
value of `files` in `[tool.mypy]` — with `disallow_untyped_defs`, at a `python_version` pinned to
the package floor rather than to your interpreter.

## The gates

Seven commands. All seven must be green before you push, and CI runs all seven:

```bash
python -m pytest tests
python -m ruff check src tests tools bench
python -m ruff format --check src tests tools bench
python -m mypy
python tools/check_claims.py
python tools/splits.py --check
python tools/gates.py --check
```

**That block said six, and had done since `tools/gates.py` shipped.** `python tools/gates.py --check`
runs in the `lint` job, in the step named *Every CI gate is registered, and says whether it has ever
failed on purpose*, and both this file and `docs/SECOND-READER.md` told a reader there were six. A
list of the gates is exactly the kind of prose no gate reads — so this one is now read:
`tests/test_second_reader_policy.py` parses the block above, requires each command's script to exist,
runs `--help` on it, and requires the flag named here to be a flag it accepts.

The last three are the ones most often missed, and they are the three that fail on a *document*
rather than on code. `tools/check_claims.py` refuses a new performance or accuracy figure that does
not cite a run id in `bench/results.json`; `tools/splits.py --check` refuses a corpus with no
declared role, task or licence, and refuses a read of a reserved corpus arm; `tools/gates.py --check`
refuses a CI job that no gate register accounts for. On Windows, set `PYTHONIOENCODING=utf-8` before
the report modes of `check_claims.py`.

Two of those gates carry ratchets that **may not grow** — the value-matched register and the
deferred register. If your change raises either, the fix is to cite the figure, not to raise the
baseline.

Public classes and functions need Google-style docstrings with `Args:` / `Returns:` / `Raises:`.

## Changing a user-facing document

`README.md`, `CHANGELOG.md`, `SECURITY.md`, this file and everything in `docs/` except
`DECISIONS.md`, `AUDIT-*.md` and `notes/` are read by people deciding whether to trust this library.
They are held to one extra step, and it is a step rather than an aspiration:

**A change to any of them ends with a cold read, by somebody who did not write the change.**
The procedure, the two triggers, the hand-off and what one round of it costs are in
[docs/SECOND-READER.md](docs/SECOND-READER.md). The short version:

1. Ask whether a cold read is due, and do not answer from memory:

   ```bash
   python tools/second_reader.py --trigger   # the user-facing files in your working tree
   python tools/second_reader.py --open      # findings nobody has applied yet
   python tools/second_reader.py --check     # the gate over the ledger and the policy page
   ```

   `--trigger` reads the **working tree**, not committed history, because the cold read happens
   before the commit. The command it published for its first year read `<round-base>..HEAD` and
   returned an empty list at the only moment it fires.

2. Cold-read the files `--trigger` names — given the document and the gates only, ask what would have
   to be true for it to be wrong.
3. Cold-read the one file the rotation cursor points at. Just under half of the first pass's findings
   were in files nobody had edited, which is why this half of the trigger exists.
4. **Write every finding into [`docs/cold-reads.toml`](docs/cold-reads.toml). Do not fix anything.**
   The reader reports and somebody else applies: `disposition = "fixed"` requires an `applied_by`,
   and the gate refuses an `applied_by` equal to the reader who raised the finding. Each entry
   carries the file, the line, the sentence quoted exactly, the command that refutes it, an owner and
   one of **open**, **fixed**, **blocked on a named decision**, or **permanent, and here is why**.
5. **Re-affirm every finding still open**, by pointing its `reviewed_in` at your read. A finding may
   be open across two cold reads; on the third the gate refuses it and it has to be applied, blocked
   or made permanent. That rule exists because a finding this project had already located, written
   down and published stayed unaltered in three files for a full round.

The four highest-yield checks, if you read nothing else: run every pasted output block, run every
command a number is published beside, follow every "see X" pointer into X, and count both sides of
every *all* / *every* / *only*. Each of those caught a live defect on the first pass.

`python tools/second_reader.py --check` enforces the *state* — the cursor, the rotation's coverage,
the shape of every finding. **Nothing in CI enforces that a cold read happened**, and
`docs/SECOND-READER.md` says so under its own *How this fails* rather than in a footnote.

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
