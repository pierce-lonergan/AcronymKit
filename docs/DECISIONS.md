# Decisions, and things deliberately not done

Negative results are the easiest thing in a project to lose and often the most useful thing to keep.
This file records what was tried and abandoned, what was considered and cut, and why — so nobody
re-litigates a settled question from scratch, and so the settled questions can be re-opened on
evidence rather than on vibes.

Newest first.

---

## D-010 — Pseudo-precision estimator: shipped. Cascade built on it: not shipped.

**Status:** estimator kept, cascade rejected · **Evidence:** `bench/run_cascade.py`, `bench/results.json`

Phase B was to close the 5-point gap to Ab3P by doing what Ab3P does: apply many matching strategies,
ordered by estimated reliability, and take the first that fits. Half of it worked.

### The estimator works, and it is the part worth having

`acronymkit._pseudo_precision` estimates each strategy's precision from **raw text with no
annotation at all**, following Sohn et al. (2008): measure how often a rule fires on real candidates,
subtract how often it fires on short forms paired with windows that cannot define them, and the
remainder is the rate at which it fires for a reason.

Three independent checks that it is doing something real:

1. **The derived ordering matches Ab3P's published one.** Word-initial anchoring with word-initial
   placement estimates at 1.000 on three-letter alphabetic short forms; the loosest rule
   (any anchor, any placement, any skipping) estimates at 0.534. Ab3P's own table runs `FirstLet`
   0.999 to `AnyLet` 0.681. Same shape, derived independently, no labels.
2. **Reliability falls with shorter short forms** — max 0.962 at length 3 against 0.833 at length 2 —
   which is the structure Ab3P's per-length table encodes.
3. **The confidence is calibrated.** Sweeping the abstention threshold on held-out data moves
   precision monotonically 85.43 -> 86.83 -> 88.97 -> 90.94 -> 91.62 while recall falls only
   74.56 -> 72.97. Higher-confidence pairs really are more often right, which is the property that
   makes abstention meaningful.

That estimator is usable on any domain where no gold standard exists and never will — legal,
financial, internal documentation. Nothing else in this library can be tuned that way.

### The cascade does not beat the single greedy rule

Held out (MED1250 test half, frozen split seed 20260809, estimated on the dev half):

| System | P % | R % | F1 % |
|---|---:|---:|---:|
| **Tier 0, Schwartz & Hearst** | **92.32** | **76.47** | **83.65** |
| Tier 1 cascade, no abstention | 85.43 | 74.56 | 79.63 |
| Tier 1 cascade, abstain < 0.90 | 91.62 | 72.97 | 81.24 |

Tier 0 dominates at every threshold — better precision *and* better recall. Not shipped.

### Why, and it is the same mistake as D-008

The first cascade preferred the **earliest** valid long-form start, on the theory that S&H's
truncation is the thing to fix. It is not, or at least not by that route:

    ARC   got "and arcuate nucleus"                              want "arcuate nucleus"
    MPO   got "male rats following infusion into the medial ..." want "medial preoptic nucleus"

`ARC` aligned its `a` to "**a**nd". Preferring longer spans buys a few genuine recoveries and pays
for them many times over — which is exactly what the hyphen-boundary experiment in D-008 found.
Switching to latest-start improved every abstention threshold — the shipped table below is
that variant, the better of the two — and it still lost.

The lesson is consistent across two independent attempts: **the greedy shortest-match rule is a much
stronger baseline than its visible truncation suggests.** Beating it is not a matter of choosing
better boundaries. Ab3P's advantage must come from somewhere else in its design — most likely its
much larger curated resources (`SingTermFreq.dat` is 31 MB of subword-frequency data, `Lf1chSf`
48 KB of long forms for one-character short forms), not from the cascade structure alone. That is
testable and is the obvious next experiment.

---

## D-009 — A preset is a point on a frontier, not an answer

**Status:** open · **Evidence:** [`notes/scoring-objective.md`](notes/scoring-objective.md)

Section 2 of the technical note shows that no single coefficient vector can both
weight dictionary hits meaningfully and reproduce conventional initialisms, once the lexicon is
real. That is not a tuning problem to be solved; it is a trade-off to be exposed.

Presenting one vector as *the* balanced answer hides that trade inside a constant. The successor API
returns the **Pareto frontier** — the non-dominated operating points over (initialism fidelity,
pronounceability) — and lets the caller pick. Someone naming a product wants a different point from
someone indexing a document store, and neither is wrong.

Not built yet. Recorded here so the design consequence of a proved result does not evaporate.

The same reframing applies to the extraction configuration: we sit at 92.07 precision / 76.99 recall,
which is precision to spend, and the knobs that cost 17.6 % of the misses are operating points rather
than defects. An `ExtractionProfile` enum with published per-corpus numbers is the same idea applied
to the other half of the library.

---

## D-008 — Boundary-maximising long-form selection: tried, measured, reverted

**Status:** rejected · **Evidence:** `docs/EVALUATION.md`

The largest single category of extraction misses (28.7 %) is the reference matcher truncating the
long form: it walks right-to-left and accepts the first alignment it reaches, which is the shortest
one. `IIEF` yields `"Index of Erectile Function"` rather than `"International Index of Erectile
Function"`, because the second `I` and the `E` are consumed from inside `"Erectile"`. Each such case
costs a false negative *and* a false positive.

Tried: enumerate every plausible starting boundary, keep those the reference matcher validates from
their first character, and pick the one maximising word-initial alignment.

| Variant | Exact F1 on MED1250 |
|---|---:|
| Reference algorithm (kept) | **84.78** |
| Maximise initial alignment, word + hyphen starts | 83.36 |
| Same, count rather than fraction | 83.36 (identical — monotonically related) |
| Same, hyphen starts restricted to alphabetic prefixes | 84.69 |

Reverted: nothing beat the baseline.

The diagnosis is worth more than the attempt. Hyphen-boundary starts fixed 3 pairs (`HDL →
high-density lipoprotein`, where `non-` is a qualifier rather than part of the term) and broke 18,
almost all chemical nomenclature (`2,6-diaminopurine → diaminopurine`). Locants belong to the
compound's name; a `non-` prefix does not. Restricting hyphen starts to alphabetic prefixes separates
those cases and recovers nearly all the loss — but "nearly" is not "beats", so it did not ship.

Conclusion: the greedy match is a stronger baseline than its visible truncation suggests, and beating
it probably needs what Ab3P actually did — per-candidate precision estimates learned from data — not
a better boundary heuristic.

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
