# acronymkit support matrix

What each capability does at each tier, whether it works with no network, and what it needs
installed. [docs/ENTERPRISE.md](ENTERPRISE.md) is the short decision page;
[docs/OFFLINE.md](OFFLINE.md) is the security review. This is the detail behind both.

## How to read it, and what was measured

Every cell below was produced by running the thing on the host in
[Measurement environment](#measurement-environment), **except where a cell says otherwise, which it
does explicitly**. That host has `nltk` 3.9.1 installed with no tagger corpus and **no spaCy at
all**, so no Tier 1 runtime is usable on it. That is not a gap that was papered over — it is the
reason the two Tier 1 columns are split into what *was* measured (which backend is resolved, what is
raised, what warning is emitted, whether the annotator is consulted at all) and what was not (the
content of a real tagger's output). The distinction is marked in every cell it applies to.

The load-bearing measurement that makes most of this matrix decidable is
[which capabilities consult the annotator at all](#which-capabilities-consult-the-annotator). Four
of the eleven rows never call it, and a fifth calls it for only one of its two entry points — so for
those rows Tier 1 is not "probably the same as Tier 0". It is the same code, and the tier changes
only what the metadata envelope reports.

"Offline available" means: works with no network at any point after install. For Tier 1 it carries a
condition, always the same one — the model or corpus must already be in the image. Nothing is ever
fetched; that is measured, in [OFFLINE.md section 5](OFFLINE.md#5-the-optional-backends-nltk-does-not-download).

## The matrix

| Capability | Offline available | Tier 0 — `ZERO_DEPENDENCY` | Tier 1 — spaCy | Tier 1 — NLTK | Tier 2 — `NEURAL` | What it needs |
|---|---|---|---|---|---|---|
| **Generation** `generate()` | Yes | Yes. `heuristic` backend; annotator consulted once per call. Measured: `"Portable Document Format"` → `PDF`, score 20.445 | Available; same call path, annotator consulted once. *Tagger output not measured here — no spaCy on this host* | Available; same call path, annotator consulted once. *Tagger output not measured here — corpus absent* | **Not implemented.** `EngineTier.NEURAL` is accepted, warns, and degrades to the best available tier. `strict=True` raises; `offline=True` raises at `Config` construction | Base install. Tier 1 adds a backend **and** its model/corpus |
| **Backronym synthesis** `generate_backronym()` / `synthesize_backronym()` | Yes | Yes. `generate_backronym` consults the annotator once; `synthesize_backronym` **never** does — it draws on the lexicon, so it is tier-independent by construction. Measured: `"Network Exchange Unified Security"` + `NEXUS` → coverage 1.0 | `generate_backronym` differs only through the tags; `synthesize_backronym` is identical. *Tagger output not measured here* | As spaCy | Not implemented; degrades as above | Base install. `synthesize_backronym` in a language other than English draws on an empty lexicon and returns no candidates |
| **Extraction** `extract_definitions()` / `extract()` | Yes | Yes. **Annotator never consulted — measured, 0 calls.** Schwartz & Hearst over the raw text | Same pairs as Tier 0 — the same code runs. Only the envelope differs: `metadata.engine_tier` and `metadata.nlp_backend` name the resolved tier | Same pairs as Tier 0 | Not implemented; extraction is unaffected either way | Base install, and nothing else, at any tier |
| **Disambiguation** `disambiguate()` | Yes | Yes. **Annotator never consulted — measured, 0 calls.** Lexical scoring against a supplied `ExpansionDictionary`, or one built from the document's own inline definitions | Same candidates as Tier 0; only the metadata envelope differs | Same candidates as Tier 0 | Not implemented. `LexicalDisambiguator` already implements the contract a neural backend would satisfy, so selecting `NEURAL` is forward-compatible and today gets the lexical path plus a warning | Base install |
| **Scoring** `score()` | Yes | Yes. Annotator consulted once, then the shared `Scorer`. Measured: `score("API", "Application Programming Interface")` → 21.297 | Same path; tags can move a token between `CONTENT` and `FUNCTION`, which changes `Psi(T, A)`. *Not measured here* | As spaCy | Not implemented | Base install |
| **Tokenisation** `tokenize()` | Yes | Yes. Annotator consulted once. The heuristic backend fills `pos` from a suffix table and **only** `pos` — measured: 43 of 43 tokens got a `pos`, 0 role changes, 0 `is_critical` changes | Fills `pos` **and** `lemma`, and may re-label a token between `CONTENT` and `FUNCTION`; alignment is by character offset, so compounds line up exactly. *Not measured here* | Fills `pos`, and `lemma` when the `wordnet` corpus is present. Penn tags mapped to Universal POS; alignment is by surface form, not offsets, because NLTK reports none. *Not measured here* | Not implemented | Base install |
| **Batch** `batch_generate()` | Yes | Yes. Thread pool; one failure never aborts the batch — the slot is `None` and the message lands in `errors[index]`. Measured: two phrases → two annotator calls | Same; the engine is immutable and shared across the pool | Same | Not implemented | Base install |
| **Async** `agenerate()` / `abatch_generate()` | Yes | Yes. Measured: one and two annotator calls respectively. **On Windows these two are the only calls that create a socket** — `asyncio`'s `ProactorEventLoop` self-pipe, a loopback `socketpair` synthesised from a TCP pair on `127.0.0.1`. It never leaves the machine, and on Linux/macOS it reaches `AF_UNIX` and no INET socket appears | Same | Same | Not implemented | Base install |
| **CLI** `acronymkit …` | Yes | Yes, once `click` is present. All of `generate`, `backronym`, `synthesize`, `extract`, `score`, `tokens`, `schema`, `doctor`, `version`; every one takes `--format json`. Measured exit codes: 0 on success, 1 when the engine declines (e.g. an unavailable tier), 2 for a usage error or a missing `click` | `--tier statistical_nlp` selects it; otherwise identical | Same | `--tier neural` is accepted and warns | `pip install 'acronymkit[cli]'` — `click`, plus `colorama` on Windows. Neither carries an HTTP client |
| **Schema validation** `load_schema()` / `validate_result()` | Yes | `load_schema()` needs nothing and reads the bundled resource only. `validate_result()` needs `jsonschema` and refuses any schema carrying a remote `$ref`. Measured with `jsonschema` blocked at the import system: `load_schema()` still returns `AcronymEngineResult`, `validate_result()` raises `AcronymKitError` | Tier-independent | Tier-independent | Tier-independent | `jsonschema` for validation only; it is a development extra |
| **Capability reporting** `capabilities()` / `doctor` | Yes | Yes. Standard library only — it imports no part of `acronymkit` except `resources`, and decides backend availability with `importlib.util.find_spec`, which locates a module without executing it. Works on an installation that is otherwise broken | Reports `spacy: importable` without importing spaCy | Reports `nltk: importable` without importing NLTK. **Note the gap this leaves**: importable is weaker than usable, and the report says so — NLTK was importable on the measurement host while its tagger corpus was absent | Reports `tiers.neural: False` regardless of whether `onnxruntime` or `transformers` is installed. Both *were* importable on the measurement host and the tier still reported `False`, which is the correct answer: the tier is not implemented | Nothing. `doctor` additionally needs `click`, `capabilities()` does not |

## Which capabilities consult the annotator

Measured by wrapping the resolved backend's `annotate()` with a counter and driving each public
method once. This is what makes several rows above tier-independent as a fact rather than as an
expectation:

| Method | `annotate()` calls |
|---|---:|
| `tokenize()` | 1 |
| `generate()` | 1 |
| `score()` | 1 |
| `generate_backronym()` | 1 |
| `agenerate()` | 1 |
| `batch_generate()` (2 phrases) | 2 |
| `abatch_generate()` (2 phrases) | 2 |
| `synthesize_backronym()` | **0** |
| `extract_definitions()` | **0** |
| `extract()` | **0** |
| `disambiguate()` | **0** |

A method that never calls the annotator cannot be changed by which annotator was resolved. So
extraction and disambiguation return the same answer at every tier, and installing spaCy will not
improve them — which is worth knowing before anyone admits spaCy's dependency closure into an image
hoping it will. (Resolve that closure for your own environment with `pip install --dry-run --report -
"acronymkit[nlp]"`; it depends on the index snapshot, the platform and the interpreter, so this
document does not quote a package count for it.)

## How Tier 1 degrades, exactly

Degradation is never silent in the payload: the effective tier lands in `metadata.engine_tier`, the
requested one in `metadata.requested_tier`, and the reason in `metadata.warnings`. Measured, with no
Tier 1 runtime present:

| Requested tier | `strict=False` | `strict=True` |
|---|---|---|
| `ZERO_DEPENDENCY` | `heuristic`, no warnings | `heuristic`, no warnings |
| `STATISTICAL_NLP` | **raises** `TierUnavailableError` — this tier promises Tier 1 fidelity and must not degrade | **raises** `TierUnavailableError` |
| `HYBRID_NLP` | `heuristic` + warning: *"No Tier 1 NLP backend is installed (tried spaCy, then NLTK); degrading to the zero-dependency heuristic backend. Install one with: pip install 'acronymkit[nlp]'."* | **raises** `TierUnavailableError` |
| `NEURAL` | `heuristic` + two warnings: the Tier 2 one (*"Tier 2 neural disambiguation is not implemented in this release; the engine is degrading to the statistical (Tier 1) path."*) then the Tier 1 one above | **raises** `TierUnavailableError` — unconditionally, because `strict` forbids receiving a lower tier and spaCy being installed would not make Tier 2 available |
| `AUTO` | best available, **no warning** — degrading silently is what `AUTO` means | best available, no warning |

**What is lost when it degrades.** The heuristic backend fills `pos` from a suffix table and stops
there: over a 7-phrase, 43-token corpus it filled `pos` on 43 of 43 tokens and changed `role` on 0
and `is_critical` on 0. A real tagger *does* change roles — `apply_annotation` is called with
`update_roles=True` — and a role change propagates into `Psi(T, A)`, the information-loss term.
Measured directly on one token: the same token annotated `ADP` with `update_roles=True` becomes
`role=function, is_critical=False`, and with `update_roles=False` stays `role=content,
is_critical=True`.

So the honest summary of Tier 1's value is: it changes which tokens count as semantically critical,
on messy human text where a suffix table guesses wrong. It does not unlock a capability. Everything
in the matrix is *available* at Tier 0.

## Languages

Four languages are supported, and they are not equally supported. `acronymkit.capabilities()`
reports exactly seven bundled resources, and the split below is read off that list rather than
described:

| Language | Stop words | Word list (`Lambda(A)`) | Character model (`Phi(A)`) | Tier 1 tagger | Measured example |
|---|---|---|---|---|---|
| English (`en`) | `stopwords_en.json`, 391 words in 8 categories | **`lexicon_en.txt`, 76,879 entries** | **`ngram_en.json`** | spaCy `en_core_web_sm`, or NLTK `eng` | `"Portable Document Format"` → `PDF` |
| French (`fr`) | `stopwords_fr.json`, 320 words in 8 categories | None — lexicon size 0 | None | spaCy `fr_core_news_sm` only; NLTK has no tagger for `fr` and `NltkBackend(Language.FR).is_available()` returns `False` | `"Systeme de Gestion de Base de Donnees"` → `SGBD`, with two warnings |
| Spanish (`es`) | `stopwords_es.json`, 353 words in 8 categories | None — lexicon size 0 | None | spaCy `es_core_news_sm` only; NLTK reports unavailable | `"Organizacion de las Naciones Unidas"` → `ONU`, with two warnings |
| German (`de`) | `stopwords_de.json`, 474 words in 8 categories | None — lexicon size 0 | None | spaCy `de_core_news_sm` only; NLTK reports unavailable | `"Allgemeine Deutsche Automobil Club"` → `ADAC`, with two warnings |

**English is the only language with a bundled lexicon and character model; the other three ship stop
words and nothing else.** The consequence is not cosmetic: with no lexicon, `Lambda(A)` is
identically 0, so no candidate is ever reported as a dictionary word and `DICTIONARY_BACKRONYM`
cannot do its job; with no character model, `Phi(A)` is uniform, so pronounceability stops
discriminating between candidates and `MAX_PRONOUNCEABLE` collapses toward the initialism.
Positional fidelity carries generation on its own, which is why the three examples above are still
correct — but treat those languages as experimental.

The engine reports both gaps in `metadata.warnings` rather than degrading silently, quoted here from
a run:

```
no bundled lexicon for language 'fr': Lambda(A) is always 0, so no candidate can be reported as a
dictionary word. Supply one with Config(lexicon_path=...); see tools/build_lexicons.py.
no bundled n-gram model for language 'fr': Phi(A) is uniform, so pronounceability cannot
discriminate between candidates.
```

Supply your own with `Config(lexicon_path=...)`; `tools/build_lexicons.py` will build one from a
dictionary you fetch yourself. D-006 in [docs/DECISIONS.md](DECISIONS.md) records why no French,
Spanish or German word list ships: the permissive sources do not exist, and invented data produces
confident wrong answers a caller cannot detect.

## Bundled resources, as the report lists them

`acronymkit.capabilities()["resources"]` on this tree: seven files, and these are all of them.

| Resource | Bytes |
|---|---:|
| `acronym-engine-result.schema.json` | 6,408 |
| `lexicon_en.txt` | 730,496 |
| `ngram_en.json` | 14,357 |
| `stopwords_de.json` | 8,089 |
| `stopwords_en.json` | 6,650 |
| `stopwords_es.json` | 5,884 |
| `stopwords_fr.json` | 5,255 |

SHA-256 for each is in the same report under `resources.digests`, and in
[OFFLINE.md section 7](OFFLINE.md#7-every-bundled-resource) with provenance and licence per file.
A wheel built from this tree while writing this page was 404,651 B over 41 entries, tagged
`py3-none-any` with `Root-Is-Purelib: true` and no compiled extension. The tag and the absence of
native code are properties of the package; the byte count is a property of the tree on the day, and
the `build` job in CI re-measures it on every push against a 524,288 B budget.

## Measurement environment

| | |
|---|---|
| Host | Windows 11 Pro (26200), `sys.platform == "win32"` |
| Interpreter | CPython 3.13.4 |
| `acronymkit` | 0.2.0, source checkout (`src/` layout) |
| `pydantic` / `pydantic-core` | 2.11.7 / 2.33.2 |
| `nltk` | 3.9.1, **no `averaged_perceptron_tagger` corpus present** |
| spaCy | **not installed** |
| `click` / `jsonschema` | 8.1.8 / 4.26.0 |
| Suite | Green, **10 skipped**, identically under `tests/airgap_socket_guard.py`. The pass total is not quoted: it moved three times while this page was written, so on an unpinned tree it is a timestamp rather than a fact. The 10 is load-bearing, and the next section says why |

## What is not measured here

- **No real Tier 1 tagger ran.** Neither a spaCy model nor NLTK's tagger corpus is present on this
  host, and staging either means a download this work did not make. Every Tier 1 cell above
  therefore covers the resolution path, the failure path and the call path — all measured — and
  stops short of the tagger's output. Six assertions *do* cover a real backend:

  - `tests/test_nlp.py::test_auto_resolves_a_real_tier_one_backend`
  - `tests/test_nlp.py::test_real_backend_annotation_preserves_every_invariant`
  - `tests/test_nlp.py::test_real_backend_annotation_is_deterministic`
  - `tests/test_nlp.py::test_real_backend_fills_pos_tags`
  - `tests/test_nlp.py::test_resolve_backend_returns_a_protocol_conformant_backend`, the
    `statistical_nlp` parameter only
  - `tests/test_engine.py::test_a_tier_one_engine_reports_its_real_backend`

  All six **skipped** on this host, and once parametrisation is counted they are exactly the 10
  skips in the run above. On a machine with a backend staged they run — that is where a Tier 1 claim
  gets its evidence, and it is not here.
- **spaCy's no-download behaviour is the audit's figure, not this document's.** NLTK's was
  re-measured ([OFFLINE.md section 5](OFFLINE.md#5-the-optional-backends-nltk-does-not-download));
  spaCy's could not be, for the same reason.
- **The Tier 2 column describes a tier that does not exist.** Every cell in it is about what the
  engine does when `NEURAL` is *requested*, which is measurable and was measured. Nothing in it is
  about neural behaviour, because there is none to measure.
- **These are single runs, not distributions.** The generation and scoring figures quoted in the
  matrix are deterministic outputs, not timings. For timing and accuracy figures see
  [bench/results.json](../bench/results.json) and [docs/EVALUATION.md](EVALUATION.md), which are
  generated by benchmark runners and gated by `tools/check_claims.py`.
