# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Security

- **Audit result, stated plainly: `acronymkit` authors no network-reachable code path.** Nothing in
  `src/` opens a socket, resolves a name or issues a request. The audit found two paths it had
  *inherited* rather than written, and both are closed below. The base runtime dependency set is
  exactly `pydantic` + `typing-extensions`, five packages resolved. NLTK and spaCy raise rather than
  downloading when their data is missing — measured, not assumed. `docs/OFFLINE.md` is the long form,
  written for a security reviewer.
- **`load_schema()` loaded JSON Schema documents from directories this package does not own.** It
  searched `schemas/` under two ancestors of the package directory before falling back to the bundled
  copy — in an installed wheel, `<venv>/Lib/schemas/` and `<site-packages>/schemas/`. Neither is
  owned by this distribution, neither carries a hash in any `RECORD`, and either can be created by an
  unrelated dependency that ships a top-level `schemas` package. Since a JSON Schema may carry a
  remote `$ref` and `jsonschema` resolves those by fetching them, the audit ran the chain end to end:
  a planted schema was preferred over the bundled copy, `jsonschema` made a real outbound HTTP GET,
  and `validate_result` reported the attacker's document as valid. The search is gone —
  `load_schema()` reads the bundled resource and nothing else. `SCHEMA_PATH` still names the checkout
  copy for tooling, but no load path consults it. See `docs/DECISIONS.md` D-018.
- **`validate_result` now refuses a schema containing a remote `$ref`**, rather than relying on the
  fact that ours contains none. "Our document happens to be safe" is an accident, and this is where
  the accident would have become a request.
- **Strict offline mode.** `Config(offline=True)` and the `ACRONYMKIT_OFFLINE` environment variable
  put the library in a state where anything that could reach a network raises `OfflineError` instead.
  The environment variable can only *tighten* the setting, never loosen it, so an operator's
  hardening cannot be undone by a caller's argument.
- **CI now proves the offline claim rather than asserting it.** A new `air-gap` job installs the
  wheel from a local wheelhouse with `--no-index`, runs the whole suite under
  `tests/airgap_socket_guard.py` — which fails any test that constructs a socket — and exercises the
  public API under `unshare -n`. The guard documents one exemption: on Windows, `agenerate()` and
  `abatch_generate()` create loopback AF_INET sockets, because that is how asyncio's
  `ProactorEventLoop` builds its self-pipe.

### Added

- **Governed naming** (`acronymkit.governed`). Deterministic short→long expansion of a database
  identifier against a governed catalog, with the two reverse directions over the same vocabulary:
  `expand_token`, `expand_identifier`, `to_physical_name`, `is_compliant`, `normalize`. It is a
  lookup table with an audit trail around it — nothing is inferred, an unknown token comes back
  `is_known=False` at zero confidence, and **no accuracy figure is attached to it anywhere**, because
  reproducing a lookup table is a tautology rather than a result. `docs/GOVERNED_NAMING.md` is the
  contract; `docs/QUICKSTART_GOVERNED.md` is the same thing from the command line.
- **`GovernedNamer`** — the facade. Binds a dictionary and a policy once and exposes
  `expand_token` / `expand_identifier` / `to_physical_name` / `is_compliant` / `normalize` with the
  subject as their only argument, plus `expand_many` / `check_many` over a corpus and
  `with_custom` / `with_policy` for a variant. Constructors: `from_bundle`, `from_csv`, `from_json`,
  `from_long_to_short_csv`, `from_mapping`.
- **Loaders for a whole standard, not just a catalog.** `load_bundle`, `load_csv`,
  `load_long_to_short_csv`, `load_term_index_csv` and `BUNDLE_FILES`. A naming standard is a catalog,
  three allow-lists, a class-word map, a pin sheet and a term glossary; each bundle section accepts
  several conventional filenames, two files claiming one section is an error rather than a coin toss,
  and every section is optional.
- **Corpus audit.** `audit_identifiers`, `render_audit` and `suggest_catalog_additions`, with the
  `CorpusAudit`, `IdentifierAudit`, `UnknownToken`, `CatalogSuggestion`, `FindingTally` and
  `RoundTripBreak` records. The unknown-token table is the deliverable: it turns "our catalog is
  incomplete" into a ranked, finite list of rows to write. A suggestion is a request for a decision
  from whoever owns the catalog, never a wording this library invented.
- **`acronymkit governed-batch [FILE]`** — a whole schema in one process. JSONL in, JSONL out,
  streaming, so memory is flat in the size of the corpus. `--op expand|physical|check|normalize|audit`
  chooses the verb and `--flush-every` trades latency for throughput. Every record carries `line`,
  `input` and any `id` it arrived with; an error rides on its own record and never aborts the run;
  the process exits 1 if any record failed, and the one-line summary goes to standard error so every
  line of stdout is a record.
- **`acronymkit governed-audit [FILE]`** — the corpus report, with `--suggest`, `--limit` and
  `--details`.
- **`--dictionary` now accepts a bundle directory or a CSV** on every governed command, via
  `--dictionary-format auto|bundle|catalog|short_to_long|long_to_short|csv|long_to_short_csv` with
  `--columns` and `--delimiter`. `auto` reads a directory as a bundle and **refuses** to guess a
  CSV's direction: the same two columns are a valid vocabulary read either way and mean different
  things.
- **The tokenizer surface is public**: `split_identifier_parts`, `strip_qualifier`,
  `IdentifierParts` and `ACCOUNTED_SEPARATORS`, exported from `acronymkit.governed` alongside
  everything above. `import acronymkit.governed` still binds no submodule — every name resolves
  lazily on first access.
- **First disambiguation evaluation.** SDU@AAAI-21 task 2, scored with a faithful reimplementation
  of the shared task's own `scorer.py`. `acronymkit` scores 41.65 % accuracy against 72.84 % for
  always picking the most common expansion. It beats random, so the context signal is real, but on
  that benchmark it is worth less than memorising frequencies. A third of the public API had no
  evidence behind it for three releases; it now has a number, and the number is bad.
- **Oracle ceiling analysis** (`bench/run_oracle.py`). 14.01 % of MED1250 is found by no system at
  all, so the practical ceiling is 85.99 %, not 100 %. We find 7 pairs no other system
  does and are therefore not strictly dominated.
- **Generation coverage diagnosis** (`bench/run_generation.py --coverage`). 82.3 % of the
  ceiling is configuration defaults rather than the algorithm, and a search budget four orders of
  magnitude larger moves recall@25 by 0.00. The ceiling is tokenisation.
- `bench/run_micro.py`, `bench/run_rerank.py`, `bench/run_termfreq.py`, `bench/run_profiles.py`.
- **`acronymkit.capabilities()` and `acronymkit doctor`.** A stdlib-only report of which tier
  resolved, which optional backends are importable, which bundled resources are present with their
  digests, whether offline mode is in force, and which `pydantic` entry-point plugins are installed.
  `doctor --format json` makes it machine-readable for an install-time check.
- **A bundled pseudo-precision table**, so the estimator is usable with no corpus. New public
  surface: `bundled_table()`, `bundled_table_provenance()`, `BUNDLED_TABLE_RESOURCE`, and a `table=`
  argument on `best_alignment`. `estimate_precisions()` is unchanged and remains the documented route
  for anyone with their own text. The table is derived from the development half of MED1250 — a US
  Government Work — and it is a **prior on English biomedical prose, not a calibration**; how far it
  transfers to other domains has not been measured, and the docstring, the JSON provenance block and
  `bundled_table_provenance()` all say so.
- **`tools/build_reliability_table.py`.** Builds that resource, with `--check` to prove the shipped
  bytes match a fresh build and `--cross-check` to compare our derived spread per bucket against
  Ab3P's published table.
- **`tools/make_offline_bundle.py`.** Self-contained offline install bundles, one per platform target,
  each carrying the wheel, every runtime dependency wheel, a hash-pinned `requirements.txt`,
  `SHA256SUMS`, a manifest and a stdlib-only `verify.py`. Install is
  `pip install --no-index --find-links=. acronymkit`. Seven targets are served, and every bundle is
  re-resolved offline once per served interpreter before the build will pass.
- **`docs/INSTALL.md`.** Four routes that do not go through PyPI — release-asset wheel, git at a tag
  or full SHA, source checkout, offline bundle — plus the spaCy/NLTK model problem a wheel bundle does
  not solve, and three kinds of verification.
- **`docs/ENTERPRISE.md` and `docs/SUPPORT_MATRIX.md`.** The decision page for someone approving the
  package, and capability × tier × "works offline" × "what it needs" for the engineer who has to
  live with the answer. Linked from the README.
- **`docs/notes/pydantic-cost.md`.** What the pydantic dependency costs, measured four ways.
- **The wheel has a size budget in CI**, currently 524,288 bytes, so a resource cannot be added
  without someone noticing what it costs.
- **`.github/workflows/publish.yml` now builds the release's whole artifact set**: bundles for every
  target, a CycloneDX SBOM and an SPDX SBOM (both checked to actually describe this distribution), one
  `SHA256SUMS` over everything, and a build-provenance attestation over that file. Signing and writing
  are separate jobs, so neither holds the other's powers.
- `tools/fetch_data.py` assets gain `derivable` — may a resource *derived* from this asset ship, when
  the asset itself may not — and `size_bytes`. `derivable` denies by default and is enforced by a
  guard, mirroring the vendoring guard in `tools/build_lexicons.py`.

### Changed

- **Governed naming is faster on a corpus, and every optimisation changes no answer.** Against the
  figure recorded before the work, on the `schema` benchmark arm: `expand_identifier` 62.30 → 10.70
  µs, `to_physical_name` 99.90 → 41.50 µs, `is_compliant` 62.40 → 38.60 µs, corpus throughput
  15,607 → 96,532 identifiers/second. The wins are an ASCII fast path in the splitter, a
  per-(dictionary, policy) memo of resolved entries whose key space is the vocabulary rather than
  caller input, a length rejection in `abbreviate`, memoised (and frozen, therefore shareable)
  `NamingPolicy` presets, and bounding the longest-match scan in `to_physical_name` by the catalog's
  wordiest term instead of by the length of the name. Only the "after" column is in
  `bench/results.json`; see `docs/DECISIONS.md` D-026 for why a baseline cannot be, and for the
  `novel` arm that exists so a per-token memo cannot be reported only where it flatters.
- **`import acronymkit` costs 2.3 ms**, down from 149.3 ms, via lazy PEP 562 re-exports.
  Note honestly: `from acronymkit import AcronymEngine` still costs 128.1 ms and
  time-to-first-result is 196.0 ms — this moves the Pydantic cost to first use rather than
  removing it.
- README leads with generation, states scope limits explicitly, and the competitive table gains a
  Python-support column.
- `best_alignment` no longer requires a `PrecisionTable` argument; called without one it uses the
  bundled table.
- `data/LICENSES.md` is regenerated with source URL, pinned commit, licence, SHA-256, size and
  vendor-or-derive reasoning for all 20 registered assets, plus a section covering the derived
  resources that actually ship in the wheel.

### Fixed

- **BEHAVIOUR CHANGE — governed identifier expansion silently discarded characters it could not read,
  and then reported the answer as complete.** The splitter sorted everything that was neither a
  letter nor a digit into one bucket, *separator*, and separators disappear. So a column name holding
  an emoji pasted out of a spreadsheet, a stray comma from a hand-edited CSV, a currency sign or a
  combining accent expanded to the phrase a clean name would have produced — `TXN_<emoji>_ID` came
  back as "Transaction Identifier" with `is_fully_known=True`. The phrase was never the problem; the
  flag was. `is_fully_known` is the one bit a pipeline gates on, and it was saying a governed catalog
  had accounted for the whole of a name it had not read the whole of.

  Now: the separators the design names — the underscore, hyphen, dot and slash, the four SQL quoting
  characters, the two square brackets, and every Unicode whitespace character — still vanish without
  comment, because that is what a physical name is made of and it is what keeps `"TXN_ID"`,
  `[TXN_ID]` and a backtick-quoted name reading as the bare one. **Every other character is reported**,
  one entry per occurrence in input order, in a new `IdentifierExpansion.unaccounted` field, and
  `is_fully_known` is `True` only when every token resolved **and** `unaccounted` is empty.

  **What existing callers must know:** `is_fully_known` is narrower than it was, so a gate on it will
  now reject names it previously waved through — which is the intent. `unaccounted` defaults to
  empty, so a consumer that has never heard of the field reads the same payload as before. The
  accounting is written by `expand_identifier` only: `ComplianceResult` and `PhysicalName` carry no
  equivalent, which is a recorded gap rather than a decision.

  An unaccounted character is deliberately *not* turned into a token. A token is a lookup key and a
  work item — a token that misses is a catalog row somebody owes — and "this name holds a character I
  could not read" is a different fact that no catalog row can settle. The vaguer "lossless" claim is
  replaced by a counting guarantee, Hypothesis-tested: for any character outside the accounted
  separators and outside whitespace, its multiplicity in the input equals its multiplicity across the
  returned tokens plus its multiplicity in `unaccounted`. See `docs/DECISIONS.md` D-024.
- **Governed expansion cut English ordinals in half.** `1ST_TXN_DT` split to `1|ST|TXN|DT` and
  expanded to "1 St Transaction Date", where `ST` is a token no catalog carries. An ordinal suffix now
  stays welded to its digits — `1ST_TXN_DT` → `1ST|TXN|DT`, "1st Transaction Date". The suffix set is
  closed (`st`, `nd`, `rd`, `th`), matched without regard to case, English-only, and applies only when
  those two letters end the token, so `1STATE` still splits and `ADDR_1_ST` keeps the two tokens
  somebody wrote separately. The rule also does not fire across a camelCase boundary, so `1sT` is
  `('1', 's', 'T')`: a capital after a lowercase letter is the writer saying a new word starts there,
  which is what that signal means everywhere else in the splitter. A port that implements the rule
  without that condition answers `('1sT',)` and diverges.
- **`normalize` was not idempotent for a name containing an ordinal written `1sT`.** The first
  reading of the rule above joined the digit to the lowercase letter and let the camelCase rule cut
  the result, giving the token `1s` — and `'1s'.upper()` is `'1S'`, which splits back into two. Since
  `normalize` returns the tokens upper-cased and `_`-joined, `normalize('1sT')` was `'1S_T'` and
  `normalize('1S_T')` was `'1_S_T'`, so a documented invariant was false for every name carrying one.
  The corpus the idempotence test runs over contains no such name. Fixed by the narrowing above, and
  the premise the invariant rests on — a token upper-cased splits back to exactly itself — is now
  asserted as a property over arbitrary ASCII text instead of left implicit. See `docs/DECISIONS.md`
  D-024.
- **The CLI printed a traceback and exited `120` when its reader hung up.** `acronymkit
  governed-batch … | head -1` is a normal thing to type. `main` caught `BrokenPipeError` but two
  things were missing: on Windows a closed pipe surfaces as a plain `OSError` with `EINVAL` and no
  `BrokenPipeError` at all, and even where it was caught the interpreter's own flush of `sys.stdout`
  on the way out failed again against the same pipe, which is what produced the `120`. Standard
  output is now pointed at the null device on the way out, and the exit status is `0` — a consumer
  that has seen enough is the command working.
- `bench/splits.toml` recorded SDU-21 AD as MIT. It is not: the MIT licence covers the scorer and
  baseline, while the dataset is CC BY-NC-SA 4.0. Corrected, and the upstream README is pinned as an
  asset so the finding stays checkable.
- The D-011 selection headroom was overstated. Measuring the full chain gives 615 gold, 525 among
  enumerated starts, 488 admissible, 477 already returned — so the realistic prize is far smaller
  than the 121 pairs first reported.
- `PrecisionTable.ordered()` raised a bare `KeyError` from inside a sort key when the table named a
  strategy the current strategy family no longer defines. That could not happen while every table was
  built in the process that consumed it; it became reachable the moment a table could arrive from a
  file, so tables and the strategy family are now versioned separately.

### Notes

- **`normalize`'s idempotence is stated for ASCII names, and the limit outside it is now written
  down.** It rebuilds a name from the tokens the splitter found, upper-cased, and `str.upper` is not
  length-preserving in Unicode: `"ΐ"` upper-cases to a capital iota and two combining marks, a
  combining mark is not part of any token, and the second pass reports it as unaccounted and drops
  it. Repairing that would mean either applying Unicode normalisation — which rewrites text, and the
  splitter deliberately does not — or declining to upper-case a word. Both are worse than a stated
  limit, so the exception is pinned by a test of its own beside the property.
- **Memoising unknown governed tokens was measured, faster, and reverted.** A real schema repeats the
  tokens its catalog is silent about as thoroughly as the ones it governs, so caching the passthrough
  path wins on such a corpus. It was rejected on what it does to the key space: a passthrough is not
  an answer the vocabulary gave, so the memo becomes keyed by whatever names the caller happens to
  have. Clearing on full cost about 44 % on a corpus with no repetition, where the bookkeeping is
  paid on every token and returns nothing; stopping on full leaves a long-running service holding the
  first few thousand names it ever saw and learning nothing after. The correctness argument is the
  stronger one: `UnknownPolicy.REJECT` raises on an unknown token, and a cache must never answer a
  question that was supposed to stop the pipeline. The rule that replaced it — the memo remembers
  what the catalog said, and the catalog saying nothing is not something to remember. See
  `docs/DECISIONS.md` D-026.
- **The adoption problem for governed naming was a process boundary, not an API.** The consumer is a
  schema-governance pipeline in another language, and the only shape on offer was one interpreter
  start per column name. Measured on one machine, answering 2,000 names in one `governed-batch`
  process is roughly 1,300 times cheaper than 2,000 invocations, and the answers themselves are
  0.021 s of it. `GovernedNamer`, the loaders, the audit and the two batch commands exist for that
  reason; D-025 records the contract decisions inside them and what is still only hypothetical.
- Four further experiments were run and reverted: a pseudo-precision cascade, a pseudo-precision
  re-ranker, derived term statistics, and a hyphen-boundary rule. Seven attempts have now failed to
  close the extraction gap, with converging diagnoses recorded in `docs/DECISIONS.md`. The most
  useful of them: pseudo-precision rates the matching *rule*, not the *span*, so for 96.5 % of
  brackets the correct span ties with the top score.
- **Ab3P's `Lf1chSf` word list was measured and refused.** Used the way Ab3P uses it — a membership
  gate on the head word of a one-character definition — it moves the MED1250 score by less than a
  fifth of a point, and only in a configuration that admits one-character short forms, which is not
  the default. It was rejected on the control measurement rather than the gain: the list is far
  denser on MED1250's one-character gold definitions than on the rest of the corpus, and Ab3P's gold
  standard *is* MED1250, so the improvement is an upper bound of unknown tightness. Registered,
  pinned and fetch-only. The licence was never the objection; it is public domain and would have fit
  the budget. See `docs/DECISIONS.md` D-019.
- **No permissively-licensed source of acronym expansion *frequency counts* exists.** Ten were
  checked; each fails on licence, on redistribution, or on not actually holding counts. Nothing was
  shipped and nothing was invented, which is the deliverable. One route does clear the licence bar —
  deriving counts from the PMC Open Access commercial-use collection — and it is costed in D-020,
  where the binding constraint turns out to be the wheel budget rather than the licence.
- **The pydantic dependency is measured and a migration is recommended, not executed.** It accounts
  for the large majority of `from acronymkit import AcronymEngine`, and a frozen-dataclass shadow of
  the DTO layer emits an identical payload while running the warm path faster. No code has changed;
  D-023 records the decision, what it would break, and the order to do it in. The portability
  argument often made for such a migration is refuted there rather than used.

## [0.2.0] — 2026-08-09

Evidence release. v0.1.0 shipped a library; this one ships the measurements that
say whether it works.

### Headline numbers

- **Extraction, MED1250 gold standard:** precision 92.07 %, recall 76.99 %,
  F1 **83.85 %** — measured against four competing systems through one harness.
  `pyab3p` leads at 88.87 F1; we sit third of five and ahead of the other pure-Python
  Schwartz & Hearst implementation.
- **Generation, first evaluation ever:** recall@1 **75.5 %** over
  546 human-authored pairs, recall@25 89.7 %.
- **Calibrated confidence with no labels:** abstention sweeps precision
  85.43 → 91.62 monotonically.

### Changed

- **BREAKING — default `scoring_strategy` is now `STRICT_INITIALISM`** (was
  `BALANCED_PRONOUNCEABLE`). Pass the old value explicitly to restore v0.1.0 ranking. Generated
  acronyms may change for any caller using the default.
- **BREAKING — French, Spanish and German no longer ship a lexicon or n-gram model.** Λ(A) is
  identically zero and Φ(A) uniform for those languages; generation, extraction and disambiguation
  still work. Restore full behaviour with `tools/fetch_data.py` + `tools/build_lexicons.py` and
  `Config(lexicon_path=...)`.
- The bundled English lexicon is now derived from SCOWL (76,879 entries, size cut ≤ 60) instead of
  being model-authored. Every Λ(A) claim is now verifiable against a checksummed, permissively
  licensed source.
- `ScoringWeights` defaults follow the new default preset: β 1.0 → 0.25, γ 12.0 → 2.0, δ 15.0 → 25.0,
  `length_penalty` 6.0 → 8.0.

### Added

- `tools/fetch_data.py` — pinned, checksum-verified asset acquisition with a generated licence ledger
  (`data/LICENSES.md`). Assets are classified vendorable or fetch-only, with the reasoning recorded.
- `tools/build_lexicons.py` — builds lexicons from SCOWL/Hunspell and refuses to write a
  non-redistributable asset into the package. Also scores the syllable heuristic against CMUdict:
  **84.1 % exact, 99.5 % within one syllable** over 117,485 entries.
- `tools/tune_presets.py` — the coefficient sweep, committed so the calibration is reproducible.
- `AcronymEngine` now records a warning when a language has no bundled lexicon or n-gram model,
  instead of degrading silently.
- `docs/DECISIONS.md` — what was tried and rejected, and why.

### Fixed

- Timing assertions in the correctness suite were absolute wall-clock ceilings and failed on shared
  CI runners while the code was correct. They now assert scaling, with hang guards scaled by a
  measured machine factor.
- `.gitignore` used `data/` with a `!data/LICENSES.md` negation, which silently ignored the ledger:
  git cannot re-include a file whose parent directory is excluded.

### Notes

- The preset weights did not survive the lexicon swap, which is the expected outcome of tuning
  against invented data: `BALANCED_PRONOUNCEABLE` scored 16/16 on the canonical corpus against 9,282
  invented words and 13/16 against 76,879 real ones. Against a real dictionary there is provably no
  vector that both weights dictionary hits meaningfully and returns every textbook initialism, so the
  default moved rather than the tuning. See `docs/DECISIONS.md` D-007.

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

[Unreleased]: https://github.com/pierce-lonergan/AcronymKit/compare/v0.2.0...HEAD
[0.2.0]: https://github.com/pierce-lonergan/AcronymKit/releases/tag/v0.2.0
[0.1.0]: https://github.com/pierce-lonergan/AcronymKit/releases/tag/v0.1.0
