# Decisions, and things deliberately not done

Negative results are the easiest thing in a project to lose and often the most useful thing to keep.
This file records what was tried and abandoned, what was considered and cut, and why — so nobody
re-litigates a settled question from scratch, and so the settled questions can be re-opened on
evidence rather than on vibes.

Newest first.

---

## D-007 — `BALANCED_PRONOUNCEABLE` is not the default, and cannot reproduce the canonical corpus

**Status:** decided · **Supersedes:** the v0.1.0 default

Replacing the model-authored lexicon with real SCOWL data dropped
`BALANCED_PRONOUNCEABLE` from 16/16 to 13/16 on the canonical corpus (SQL→SQUL, QA→QUA, TCP→TCOP).
Re-running the sweep found only **8 of 768** vectors reaching 16/16, all on the edge of the grid — a
spike, not a plateau.

Diagnosing the three failures showed the problem is structural:

| case | margin | mechanism |
|---|---|---|
| QA → QUA | +14.2 | "qua" is genuinely in SCOWL, so Λ fires |
| SQL → SQUL | **+0.066** | neither is a word; inserting a vowel improves Φ by ~4 log units |
| TCP → TCOP | **+0.52** | same |

Two of the three are decided by margins indistinguishable from noise. Φ's dynamic range (≈ 6.5 log
units) is comparable to a whole initial-letter match (ω = 10), so at β = 1 the phonotactic term alone
decides the ranking.

**Tried and rejected:** raising `length_penalty` to suppress vowel insertion. At the value required
(≈ 14+) the short acronyms break instead — API, ROM and NASA all fail. Measured across
`length_penalty ∈ {10, 14, 16, 20}` at γ = 12: 15/16, 13/16, 13/16, 12/16. There is no vector that
both weights dictionary hits meaningfully *and* returns every textbook initialism.

**Decided:** the requirement was contradictory, so the *default* changed rather than the tuning.
`STRICT_INITIALISM` is now the default — 16/16, and still 16/16 when β, γ or δ are perturbed by
50–100 %, which is a genuine plateau. `BALANCED_PRONOUNCEABLE` keeps its coefficients and is
documented as the trade it is. Demanding that the pronounceability-weighting preset also produce
pure initialisms was asking it not to do its job.

`tools/tune_presets.py --check` now encodes the two different contracts: strict must reproduce the
corpus; balanced must *trade* (mean pronounceability strictly above strict's, currently 0.625 vs
0.542). A balanced preset that behaved identically to strict would be dead weight.

---

## D-006 — fr/es/de ship no lexicon rather than a copyleft or invented one

**Status:** decided

Three options for the non-English word lists:

1. **Keep the model-authored lists.** Rejected: every Λ(A) claim is unverifiable, and the failure
   mode is a confident wrong answer the caller cannot detect.
2. **Vendor Hunspell dictionaries.** Rejected on licence grounds. German is not a judgement call —
   its only permissive arm is OASIS 0.1, which grants distribution solely alongside programs whose
   primary save format is ODF, which acronymkit is not; the fallback is GPL. French (MPL) and Spanish
   (MPL-1.1 arm) are arguably vendorable, since MPL permits an MPL file inside a larger work under
   other terms — but that makes the wheel MIT-plus-MPL and obliges every downstream redistributor to
   track a second licence for one data file. Disproportionate.
3. **Ship nothing and say so.** Chosen.

The engine degrades honestly: `AcronymEngine` records a warning naming the language and the remedy
the first time a missing lexicon or n-gram model is loaded. Generation still works — French yields
SGBD, German ADAC, Spanish DNI — because positional fidelity carries it alone.

**Not done:** expanding Hunspell affix rules in `read_hunspell`. Only stems are taken; correct
expansion needs the `.aff` rules and a Hunspell implementation. For a fetch-only asset the user
installs themselves, a solid-but-not-exhaustive lexicon is the right trade.

---

## D-005 — CMUdict validates the syllable heuristic; it is not shipped as a table

**Status:** decided

CMUdict gives real pronunciations for ~134k words. Two possible uses:

- **Ship a syllable table.** Considered and cut. Roughly 1 MB of wheel for a lookup that only helps
  when a candidate acronym *is* a dictionary word — a minority of cases, since acronyms are mostly
  not words. The cost/benefit is poor and it would be the largest thing in the wheel.
- **Validate the heuristic.** Chosen. Counting stress-marked phonemes gives ground-truth syllable
  counts, which turns "the heuristic seems about right" into a number: **84.1 % exact, 99.5 % within
  one syllable, MAE 0.16** across 117,485 entries. Reproduce with
  `python tools/build_lexicons.py --validate-syllables`.

Revisit if a feature ever needs exact syllable counts for arbitrary words.

---

## D-004 — SCOWL size cut ≤ 60, ASCII only

**Status:** decided

SCOWL grades entries 10 (most common) to 95 (obscure). Cut at **60** (76,879 entries after
filtering) because Λ(A) is a *claim* that a generated acronym is a real word, and a false positive
is worse than a false negative: at 80+ the list admits strings no reader would recognise, which would
make the dictionary-backronym strategy confidently propose nonsense.

Proper names, abbreviations, contractions and all-caps entries are excluded — otherwise "NASA" would
count as a dictionary word and every initialism would trivially satisfy Λ(A).

The 157 accented loanwords (abbé, appliqué, attaché) are dropped too. They cannot help: candidates
take uppercased token initials, so an accented character reaches an English acronym only if an
English token starts with one. They do measurably hurt: keeping them widens the n-gram alphabet from
26 to 39 symbols that never appear in a candidate, spreading smoothing mass over dead entries.

---

## D-003 — Timing assertions live in the benchmark suite, not the correctness suite

**Status:** decided

Four CI matrix cells failed on the first push while the code was correct: two tests asserted fixed
wall-clock ceilings (0.1 s, 2.0 s) that hold on the development machine and not on a shared runner.

A hard-coded threshold is a claim about somebody else's CPU. The correctness suite now asserts
**scaling** — doubling the input must not triple the time, which decides linear-versus-quadratic on
any hardware — with residual hang guards scaled by `conftest.machine_factor()`, calibrated against a
fixed interpreter-bound loop.

---

## D-002 — `length_penalty` is a deliberate deviation from the published objective

**Status:** decided · **Writeup:** pending (Phase 5.3)

The published positional term `α·Σω` is a sum, so it grows monotonically with acronym length. Used
unmodified as a *generation* objective it is degenerate: "Portable Document Format" scores `PODOFO`
above `PDF`, because every extra character adds `contiguous_weight` and subtracts nothing. The
published formulation is a *ranking* function over candidates of a given length, so it never had to
address this.

`ScoringWeights.length_penalty` (default 8.0) sits between `contiguous_weight` (2) and
`initial_weight` (10), so covering a new token nets +2 while taking a second letter from a token
already used nets −6. Set it to `0.0` to recover the published objective exactly; a test pins that
equivalence.

---

## D-001 — Scope deliberately cut from the v0.1.0 → v0.2.0 mandate

**Status:** decided

Ranked by credibility-per-unit-effort, and cut because doing them shallowly is worse than not doing
them. Each violates "never assert a number you did not measure" if rushed.

| Cut | Why | Revisit when |
|---|---|---|
| PyPI publishing | Requires credential/account operations, and claiming a global namespace is irreversible. Trusted-publishing workflow is wired and ready. | The maintainer runs it |
| Rust/Cython native core | The rule is *only after the pure-Python work plateaus*. It has not; no profile exists yet. | `docs/PERFORMANCE.md` shows a plateau with a clear hot kernel |
| `acronym4j` Java port | Its own project. The JSON Schema interop contract exists so it stays possible. | Python side is stable at 1.0 |
| Tier 2 neural disambiguation | Needs the SDU corpora (CC BY-NC-SA — benchmark only, never vendored) and a training loop. The `LexicalDisambiguator` contract is the seam. | An eval harness exists to measure it against |
| WASM/Pyodide playground | Strongest adoption lever, but pure packaging work with no correctness content | After v0.2.0 ships |
| MCP server | Thin wrapper; cheap once the API is stable | After 1.0 |
| Full 4-corpus × 3-baseline eval harness | One honest number beats four unfinished ones | Next, and it is the highest-value remaining item |

**The single most valuable thing not yet done:** a real extraction F1 against a real gold corpus
(Ab3P, PLOD). The published Schwartz & Hearst figures are ~86–89 % F1 on Ab3P with recall the weak
side. Landing materially below that would mean a bug; landing at it converts "faithful transcription"
from a claim into a measurement.
