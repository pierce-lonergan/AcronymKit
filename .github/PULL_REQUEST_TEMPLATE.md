## What and why

<!-- What changes, and what problem it solves. Link the issue if there is one. -->

## Checks

- [ ] `pytest` passes
- [ ] `ruff check` and `ruff format --check` pass
- [ ] `mypy` passes
- [ ] New behaviour has a test; a bug fix has a regression test that fails without the fix

## If this touches the scoring function or the bundled data

- [ ] `python tools/tune_presets.py --check` passes
- [ ] `python tools/validate_resources.py --require` passes
- [ ] `python tools/build_ngram_model.py --check` passes
- [ ] Before/after output included for the canonical corpus

## If this changes the output payload

- [ ] `schemas/acronym-engine-result.schema.json` updated
- [ ] `CHANGELOG.md` notes the **Cross-language impact** (the `acronym4j` port shares this contract)

## Claims

Every performance or accuracy number in the diff traces to a committed test or tool that reproduces
it. Anything unreproducible has been removed rather than softened.
