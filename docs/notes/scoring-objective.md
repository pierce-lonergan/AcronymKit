# On using a ranking function as a generation objective

Two results about the acronym-scoring objective, both falsifiable, both
reproducible from `tools/tune_presets.py`. The first is a defect and its fix.
The second is an impossibility, and it has a design consequence this library now
acts on.

The objective under discussion:

$$S(A, T) = \alpha \sum_{i} \omega(c_i, w_{j(i)}) \;+\; \beta\,\Phi(A) \;+\; \gamma\,\Lambda(A) \;-\; \delta\,\Psi(T, A)$$

where `ω` is a positional mapping weight (10 for a word-initial character, 3 for
an internal one, 2 for a character continuing a matched run), `Φ` is a mean
character-bigram log-likelihood, `Λ` is a binary dictionary-membership
indicator, and `Ψ` counts semantically critical source tokens the acronym drops.

---

## 1. The positional term is monotone in length, so the objective is degenerate as a generator

`α·Σω` is a **sum over the characters of `A`**. Every additional character
contributes a non-negative `ω` and subtracts nothing. So for any candidate `A`
and any extension `A'` that maps its extra character to some source token,

$$\sum_i \omega(A'_i) \;\ge\; \sum_i \omega(A_i)$$

with equality only when the extra character is unmapped. The remaining terms do
not reliably oppose this: `Φ` is a *mean*, so it does not shrink with length, and
`Λ` and `Ψ` are indifferent to it.

The consequence is not subtle. Under the unmodified objective, `"Portable
Document Format"` ranks `PODOFO` above `PDF`, and `"Application Programming
Interface"` ranks `APPRIN` above `API`. Both are correct maximisations of a
function that has no reason to stop.

**This is not an error in the formulation.** It is a *ranking* function, designed
to score a given candidate against a phrase — the ACRONYM-style task of choosing
among real words of a fixed length. Used that way it is well-behaved, because
length is held constant and the monotonicity never binds. It only misbehaves when
promoted to a *generation* objective, where length is a free variable. The
failure is one of reuse, not of design.

### The fix, and why the constant is what it is

Add a length term:

$$S'(A, T) = S(A, T) \;-\; \texttt{length\_penalty} \cdot \max(0,\ |A| - \texttt{preferred\_length})$$

The value is chosen from marginal economics, not taste. Let `L` be
`length_penalty`. At the margin a candidate can either cover one more source
token (gaining `initial_weight`, i.e. 10) or take a second character from a token
it already used (gaining `contiguous_weight`, i.e. 2). Both cost `L`. So:

| | net change | wanted |
|---|---:|---|
| cover one more token | `10 − L` | positive |
| second letter from a used token | `2 − L` | negative |

Any `L` strictly between `contiguous_weight` and `initial_weight` makes
"one letter per token, cover everything" the optimum **by construction** rather
than by tuning. The shipped default is `8`, giving `+2` and `−6`.

Setting `length_penalty = 0.0` recovers the published objective exactly, and a
test pins that equivalence so the claim cannot rot.

---

## 2. With a real lexicon, no meaningfully-balanced weight vector reproduces conventional initialisms

This one was discovered by being wrong in public.

The v0.1.0 coefficients were tuned against a 9,282-word lexicon that a language
model had invented. Against that lexicon the `BALANCED_PRONOUNCEABLE` preset
reproduced all sixteen entries of a canonical corpus of textbook initialisms
(API, PDF, NASA, HTML, RAM, CPU, GPU, SCUBA, LASER, SQL, CRM, QA, TCP, SOAP,
BIOS, ROM). Replacing it with 76,879 real SCOWL entries dropped that to thirteen.
Re-running the sweep found only 8 of 768 vectors reaching all sixteen, every one
of them on the boundary of the grid — a spike, not a plateau.

### Why, mechanically

Three cases fail, and they fail for two different reasons.

**QA → QUA** is a genuine dictionary hit: `qua` is in SCOWL, so `Λ` fires and
`γ` pays for it. A larger dictionary makes this class strictly more common — that
is what a larger dictionary *is*.

**SQL → SQUL** and **TCP → TCOP** win by margins of **+0.066** and **+0.52**.
Neither is a word. Inserting a vowel simply improves `Φ`, and here is the crux:

> `Φ` has a dynamic range of roughly 6.5 log units across plausible candidates
> (measured on the bundled model: `Φ("SCALE") = −2.29`, `Φ("XKCD") = −7.46`),
> which is comparable to `initial_weight = 10`, the value of an entire
> word-initial match.

At `β = 1` the phonotactic term alone decides the ranking. The two "failures"
that motivated retuning are noise against that scale.

### Why it cannot be fixed by retuning

The obvious repair is to raise `length_penalty` until vowel insertion stops
paying. Measured, at `γ = 12`, over the canonical corpus:

| `length_penalty` | 10 | 14 | 16 | 20 |
|---|---:|---:|---:|---:|
| corpus entries reproduced | 15/16 | 13/16 | 13/16 | 12/16 |

It gets *worse*. Suppressing a one-character insertion needs `L ≳ 14`, but at
that value the short acronyms are over-penalised and API, ROM and NASA break
instead. The two requirements pull `L` in opposite directions:

- to keep a dictionary hit from buying an extra character: `L > γ·ΔΛ + contiguous_weight`
- to keep a 3-character initialism from being crushed: `L · (|A| − \texttt{preferred\_length})` must stay small

With `γ` large enough to be *meaningful*, no `L` satisfies both. **The
requirement is contradictory**, not merely hard.

### The design consequence

Demanding that a pronounceability-weighting preset also produce pure initialisms
is asking it not to do its job. So the *default* moved rather than the tuning:
`STRICT_INITIALISM` is now the default and reproduces all sixteen, and it does so
across a broad plateau — still all sixteen when `β`, `γ` or `δ` are perturbed by
50–100 %. `BALANCED_PRONOUNCEABLE` keeps its coefficients and is documented as
the trade it is: it returns `QUA` for "Quality Assurance", and that is correct
behaviour for a preset named after pronounceability.

The generation evaluation independently confirms the presets are doing what the
labels say. Over 546<!--claim:generation.med1250.coverage.ceiling.initialism_n--> initialism-bucket pairs from MED1250, `recall@1` is
75.5<!--claim:generation.med1250.strict_initialism.initialism_recall_at_1:.1f--> % for `STRICT_INITIALISM` and 10.3<!--claim:generation.med1250.max_pronounceable.initialism_recall_at_1:.1f--> % for `MAX_PRONOUNCEABLE` — but
`recall@25` converges to 89.7<!--claim:generation.med1250.strict_initialism.initialism_recall_at_25:.1f--> % and 89.2<!--claim:generation.med1250.max_pronounceable.initialism_recall_at_25:.1f--> %. They re-rank a shared candidate pool; they do not
search differently.

---

## 3. What this argues for: stop pretending a preset is a point

A preset is a single `(α, β, γ, δ, L)` vector, and section 2 shows the vector
cannot satisfy every reasonable requirement at once. Presenting one as *the*
answer hides a trade-off inside a constant.

The honest presentation is the **Pareto frontier**: the set of non-dominated
operating points over (initialism fidelity, pronounceability), returned to the
caller with the trade documented rather than chosen on their behalf. A caller
naming products wants a different point from a caller indexing a document store,
and neither is wrong.

That API does not exist yet. It is the natural successor to this note and is
recorded as such in [`DECISIONS.md`](../DECISIONS.md).

---

## Reproducing all of it

```bash
python tools/tune_presets.py            # the sweep, the plateau extent, the centroid
python tools/tune_presets.py --check    # the two shipped contracts
python bench/run_generation.py --all-presets --save
```

`tests/test_scoring_presets.py` pins the canonical corpus, so a future retune
cannot quietly regress result 2 back into the repository.
