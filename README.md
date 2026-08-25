# acronymkit

[![CI](https://github.com/pierce-lonergan/AcronymKit/actions/workflows/ci.yml/badge.svg)](https://github.com/pierce-lonergan/AcronymKit/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/python-3.9%20%7C%203.10%20%7C%203.11%20%7C%203.12%20%7C%203.13-blue)](https://pypi.org/project/acronymkit/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![Typed](https://img.shields.io/badge/typing-py.typed-informational)](https://peps.python.org/pep-0561/)
[![OpenSSF Scorecard](https://api.securityscorecards.dev/projects/github.com/pierce-lonergan/AcronymKit/badge)](https://scorecard.dev/viewer/?uri=github.com/pierce-lonergan/AcronymKit)

**A governance instrument for names somebody else owns.**
Expand governed schema identifiers against a catalog you supply, and report what the catalog cannot
account for as *unknown* rather than approximating it. Generation, backronym synthesis, extraction
and contextual disambiguation ship in the same typed library, are measured beside it wherever they
can be measured at all, and do not lead.

**[What this library is for](docs/POSITIONING.md)** — the commitment, what it costs, the two
questions this project cannot answer at all, and what would reverse the decision.

```python
from acronymkit.governed import GovernedNamer

nds = GovernedNamer.from_mapping({"TXN": "Transaction", "APPLNT": "Applicant", "ID": "Identifier"})
nds.expand_identifier("TXN_APPLNT_ID").phrase        # 'Transaction Applicant Identifier'
nds.expand_identifier("TXN_KYC_ID").is_fully_known   # False — the catalog has no KYC
```

**Governed naming leads this README for two reasons, and neither is that it is the larger half of the
package.** It leads because nothing in the ecosystem table below addresses it — a bare column token,
a catalog somebody else owns, and a requirement to refuse rather than guess — so it is the one thing
here that no row of that table is aimed at. And it leads because it is the half the refuse-to-guess
property is *about*: everywhere else in this package refusing is a tuning knob, and here it is the
design. "It is bigger" was the reason this sentence used to give, and size is not an argument for
anything.

It is measured, and it publishes its worst row beside its headline. Against
26,536<!--claim:governed_gold.socrata.columns.all.pairs:,--> Socrata field/caption pairs written by
the publishers themselves, it cuts the identifier exactly where the human did on
91.37<!--claim:governed_gold.socrata.columns.all.exact_pct:.2f--> % of them — and on the
959<!--claim:governed_gold.socrata.columns.unmarked.pairs:,--> pairs that carry no boundary mark at
all, on 34.93<!--claim:governed_gold.socrata.columns.unmarked.exact_pct:.2f--> %. That second number
is the price of refusing to guess, and it is in the same table as the first, along with the SEC arms
and the recall ceiling: [docs/EVALUATION.md](docs/EVALUATION.md).

**What that number does not cover, stated here rather than one link away.** It measures *cut
placement* — where the identifier is divided — through the public entry point with an **empty**
catalog, and the empty catalog is forced by the metric rather than chosen: a populated one rewrites
`TXN` to `Transaction`, which changes the character stream both strings have to share. So catalog
resolution, class-word detection, compliance and naming are **not** in it. Those are lookups against
data you supply; this is the judgement the package makes on its own, which is the only part of it we
can put a number on without your catalog. `bench/run_governed_gold.py` says so at length and has
since it was written — it is repeated here because this is the figure the rest of this README now
leans on, and a scope disclosure that lives only in the runner is a scope disclosure the reader of
the front page does not get.

**Generation is measured, and nothing else measures it.** Fed the
1,221<!--claim:generation.med1250.strict_initialism.gold_pairs:,--> human-authored
short-form/long-form pairs of the MED1250 gold standard *backwards*, `acronymkit` returns the
abbreviation the human actually chose at **rank 1 for
75.5<!--claim:generation.med1250.strict_initialism.initialism_recall_at_1:.1f--> %** of the
546<!--claim:generation.med1250.strict_initialism.initialism_n:,--> pairs an initialism
generator can address, and within the top 25 for
89.7<!--claim:generation.med1250.strict_initialism.initialism_recall_at_25:.1f--> %. MED1250 is a
**tuning split**. No competing library has a number here, because no competing library generates.

**Extraction is measured too, and it is a supporting number nobody optimises again.** Against four
other systems through one harness: precision
92.46<!--claim:extraction.med1250.acronymkit.exact_precision:.2f--> %, recall 77.31<!--claim:extraction.med1250.acronymkit.exact_recall:.2f--> %, F1 **84.21<!--claim:extraction.med1250.acronymkit.exact_f1:.2f--> %** — third of five, behind
`pyab3p` at 88.87<!--claim:extraction.med1250.pyab3p.exact_f1:.2f--> and `abbreviation_extractor` at
84.44<!--claim:extraction.med1250.abbreviation_extractor.exact_f1:.2f-->, both of which are compiled.
Demoting it is not hiding it: the table showing exactly where it loses is in
[docs/EVALUATION.md](docs/EVALUATION.md), and why this project stopped treating that figure as
something to improve is in [docs/POSITIONING.md](docs/POSITIONING.md).

## Why

Four kinds of tool exist in the open-source acronym ecosystem, and each stops somewhere:

| | What it does well | Where it stops |
|---|---|---|
| **Naive string utilities** — `acronymcreator`, countless gists | Fast, no dependencies | No tokenisation grammar, no phonetics, no semantics |
| **Corpus matchers** — ACRONYM (Cook, 2019) | Finds candidates that spell real words | Offline batch, static corpus, no library bindings |
| **Rule-based extractors** — Schwartz & Hearst (2003) in scispaCy, Blackstone | Few false positives on inline definitions, cheap | Strictly extractive; the definition must be present |
| **Neural disambiguators** — AcroBERT, SDU/SciAD/GLADIS | Resolves standalone acronyms from context | GPU-bound, slow cold start, research codebases |

**Nothing in that table addresses the governed case at all**: a bare column token with no sentence
around it, a catalog somebody else owns, and a requirement to **refuse** rather than guess. That is
the half of this package the rest of this README leads with, and it is the one acronym task here
that the table above has no row for. This README used to conclude the table with "`acronymkit`
is the missing single library", which is an argument about convenience, and convenience is not what
this project has evidence for.

**And the third row is less plural than it looks.** Scored through one harness on PLOD-CW, five
Schwartz & Hearst descendants at seven operating points turn out to be one algorithm — this library
is the fifth of the five, and contributes three of the seven points. A single implementation — this
library's `BIOMEDICAL` profile — accounts for
93.55<!--claim:monoculture.plod_all.proposals.edges_sh_only.share_pct_acronymkit/biomedical:.2f--> %
of everything the whole family proposes, and
93.99<!--claim:monoculture.sdu22_scientific_dev.proposals.edges_sh_only.share_pct_acronymkit/biomedical:.2f--> %
on SDU-22 scientific. All seven together reach
57.65<!--claim:monoculture.plod_all.gold.long_form.overlap.class.sh_family_recall_pct:.2f--> % of
PLOD's gold long-form spans, and
34.98<!--claim:monoculture.plod_all.gold.long_form.overlap.class.unproposed_alignable_from_gold_short_form_pct_of_gold:.2f--> %
of gold long forms go unreached **while cleanly alignable with a gold short form in the same
passage** — not hard pairs, just pairs no bracket scanner offers. Adding the two proposers that make
neither Schwartz & Hearst commitment — a trivial all-caps rule and `shapecue` — lifts family reach to
79.60<!--claim:monoculture.plod_all.gold.long_form.overlap.class.all_proposers_recall_pct:.2f--> %.
Run ids `monoculture.*`, decomposed in
[docs/EVALUATION.md](docs/EVALUATION.md#the-extraction-monoculture-and-what-it-does-to-the-corpora).

**The strong reading of that is confounded, and this README does not get to publish only the first
half.** The tempting conclusion — that the benchmarks were drawn around the pool and therefore
certify its blind spot — cannot be separated from **genre**. MED1250 is abstracts and PLOD is article
body text; abstracts carry no figure legends and no table footnotes, which is exactly where the
unproposed class lives. The control reads the same either way: on MED1250 the independent proposer's
gain over gold is 0.00<!--claim:monoculture.med1250.gold.pairs.independent_gain_pct:.2f--> %, which
is what provenance predicts and also what genre predicts. Separating them needs article body text
whose gold was pooled from these systems, and nobody publishes one on purpose.

So the argument for this library is not that it does more things than the rows above. It is that a
system which reports what it cannot see is worth more, to somebody governing data, than one that
reports a bigger number over the same blind spot. **That last step is a claim about users this
project has never measured**, and [docs/POSITIONING.md](docs/POSITIONING.md) says so in its own
words, along with what would reverse the decision.

## Install

```bash
pip install acronymkit
```

The base install is the complete Tier 0 engine — extraction, generation, backronyms, scoring, CLI-free
API — with `pydantic` as the only runtime dependency. Optional extras add higher tiers:

```bash
pip install "acronymkit[cli]"          # click-powered command line
pip install "acronymkit[nlp]"          # Tier 1: spaCy / NLTK part-of-speech evidence
pip install "acronymkit[all]"          # everything
```

CI enforces the split: a dedicated job installs the base package alone and asserts that no optional
dependency reaches `sys.modules` after a generate + extract cycle.

## What it does

### Governed naming — expansion with no sentence to lean on

A schema-governance pipeline has no prose to lean on. Given a bare column token and a governed
vocabulary, return the long form — deterministically, with no context to disambiguate against, and
with a record of which catalog entry produced each word.

```python
from acronymkit.governed import GovernedNamer, load_bundle

# A real standard is a directory of files, and one line reads it:
#     nds = GovernedNamer.from_bundle("nds_standard/")
#     nds = GovernedNamer(load_bundle("nds_standard/"), policy)   # the same, unbundled
# Inline below, so this block runs with nothing on disk.
nds = GovernedNamer.from_mapping(
    {"TXN": "Transaction", "APPLNT": "Applicant", "ID": "Identifier",
     "NBR": "Number", "NUM": "Number", "DT": "Date"},
    approved_abbreviations=["TXN", "APPLNT", "ID", "NBR", "DT"],
    class_words={"ID": "Identifier", "DT": "Date"},
)

nds.expand_identifier("TXN_APPLNT_ID").phrase        # 'Transaction Applicant Identifier'
nds.expand_identifier("TXN_KYC_ID").is_fully_known   # False — the catalog has no KYC
nds.normalize("txnApplntNum")                        # 'TXN_APPLNT_NBR'
```

`GovernedNamer` binds one vocabulary and one policy and then takes the subject as its only argument;
`expand_many` and `check_many` take a whole corpus. A naming standard on disk is a catalog, three
allow-lists, a class-word map, a pin sheet and a term glossary, which is what `from_bundle` and
`load_bundle` read; `from_csv` and `from_json` read the narrower shapes.

**Nothing is dropped in silence.** A character the splitter cannot account for is reported rather
than discarded, and `is_fully_known` is true only when every token resolved *and* nothing went
unaccounted for:

```python
nds.expand_identifier("TXN_©_ID").phrase           # 'Transaction Identifier'
nds.expand_identifier("TXN_©_ID").unaccounted      # ('©',)
nds.expand_identifier("TXN_©_ID").is_fully_known   # False
```

**Your acronyms win.** `with_custom` layers an overlay above the catalog and reports it as such:

```python
result = nds.with_custom({"KYC": "Know Your Customer"}).expand_token("KYC")
result.long, result.source.value      # ('Know Your Customer', 'custom')
```

Three directions over one vocabulary — `expand_identifier` reads a physical name, `to_physical_name`
renders a logical one, `is_compliant` checks a name somebody else wrote — so a catalog change moves
all three at once. Every answer carries the rule that produced it, the catalog row behind it and the
candidates it beat.

**This is not disambiguation, and that is the design.** A column name is not a sentence: there is no
context to weigh, so the answer comes from the catalog or it does not come at all. An unknown token
is reported as unknown, with zero confidence, never approximated — because an unknown reported as
unknown is recoverable and an unknown quietly guessed is not.

**One thing here does decide something on its own, and it is now measured.** Catalog lookup is exact
by construction, which is a tautology rather than a measurement — a lookup table is exact about
whatever you put in it. Where the identifier is *cut into tokens* is the one judgement this
subsystem makes unaided, and it is scored against captions the publishers themselves wrote, on two
public corpora, decomposed and with its recall ceiling printed:
[docs/EVALUATION.md](docs/EVALUATION.md). Every one of those runs recorded its corpus as undeclared
at the time it ran, and none has been re-measured since — read them as measured-before-declared
rather than as held-out. [docs/GOVERNED_NAMING.md](docs/GOVERNED_NAMING.md) has the precedence
chain, every verb with runnable output, the four invariants and an honest limits section.

### Forward generation

```python
from acronymkit import AcronymEngine, Config
from acronymkit.enums import EngineTier, ScoringStrategy

engine = AcronymEngine(Config(
    engine_tier=EngineTier.HYBRID_NLP,
    scoring_strategy=ScoringStrategy.STRICT_INITIALISM,
    include_articles=False,
    min_word_length=2,
    max_acronym_length=6,
))

result = engine.generate("Application Programming Interface")
result.primary_acronym                    # 'API'
result.score                              # 21.297
result.primary.breakdown.explain()
# 'S = 1*30.000 + 0.25*-2.811 + 2*0.000 - 25*0.000 = 21.297'

[(c.acronym, round(c.score, 2)) for c in result.alternatives[:4]]
# [('API', 21.3), ('APIN', 15.42), ('APRI', 15.38), ('APPI', 15.29)]
```

Every candidate carries a per-character alignment trace and a term-by-term score decomposition, so a
ranking decision is always explainable.

### Backronym synthesis

Align a phrase onto a target word:

```python
result = engine.generate_backronym(
    phrase="Network Exchange Unified Security",
    target_word="NEXUS",
)
result.primary_expansion            # 'Network Exchange Unified Security'
result.candidates[0].coverage       # 1.0
[m.kind.value for m in result.candidates[0].mappings]
# ['initial', 'initial', 'contiguous', 'initial', 'initial']
```

Note the `contiguous` mapping: **E** and **X** both come from "**Ex**change". Sub-word matches are
first-class, exactly as in the ACRONYM formulation.

Or expand a word with no source phrase at all:

```python
engine.synthesize_backronym("NEXUS").candidates[0].expansion_text
# 'nab ear xis ugh sac'
```

### Extraction (Schwartz & Hearst)

```python
engine.extract_definitions(
    "The National Aeronautics and Space Administration (NASA) launched the mission."
)
# [AcronymPair(short_form='NASA', long_form='National Aeronautics and Space Administration')]
```

Both arrangements are supported — `Long Form (Short Form)` and the inverted
`Short Form (Long Form)` — with exact source spans (`text[pair.short_form_span[0]:...] == short_form`
always holds) and a confidence estimate. Prose parentheticals such as `(see Figure 3)` and
enumerations such as `(1) … (2) …` are correctly rejected.

**Measured, not asserted.** On the MED1250 gold standard
(1,221<!--claim:extraction.med1250.acronymkit.gold_pairs:,--> human-annotated pairs from the Ab3P
corpus): **precision 92.46<!--claim:extraction.med1250.acronymkit.exact_precision:.2f--> %, recall 77.31<!--claim:extraction.med1250.acronymkit.exact_recall:.2f--> %, F1 84.21<!--claim:extraction.med1250.acronymkit.exact_f1:.2f--> %**, at 5,496<!--claim:extraction.med1250.acronymkit.docs_per_second:,.0f--> documents/second. High
precision with recall the weak side is the expected shape for this algorithm — it refuses rather than
guesses. The full breakdown, including where the misses come from and one optimisation that was tried
and reverted, is in [docs/EVALUATION.md](docs/EVALUATION.md). Reproduce with:

```bash
python tools/fetch_data.py med1250 && python bench/run_extraction.py
```

### Contextual disambiguation

```python
from acronymkit.disambiguation import ExpansionDictionary

vocab = ExpansionDictionary({"MS": [
    "multiple sclerosis", "Microsoft", "mass spectrometry", "manuscript",
]})

engine.disambiguate("MS", "The patient was diagnosed with MS after an MRI showed brain lesions.",
                    dictionary=vocab).primary_expansion   # 'multiple sclerosis'
engine.disambiguate("MS", "The MS Office suite shipped a new version of Word and Excel.",
                    dictionary=vocab).primary_expansion   # 'Microsoft'
engine.disambiguate("MS", "Peak intensity in the MS spectrum identified the ionised compound.",
                    dictionary=vocab).primary_expansion   # 'mass spectrometry'
```

**The `dictionary=` argument is not optional decoration — it is the whole feature.** Without it there
is no selection happening at all. The engine looks only for a parenthetical definition **inside the
string you passed**, so the default path is an inline-definition lookup wearing a disambiguator's
name. On the SDU@AAAI-21 AD dev split it returns no candidate whatsoever on
97.45<!--claim:disambiguation.sdu21.diagnosis.default_path.no_candidate_pct:.2f--> % of instances, and
has two candidates to choose between on
1<!--claim:disambiguation.sdu21.diagnosis.default_path.two_or_more_candidates:,--> of
6,189<!--claim:disambiguation.sdu21.diagnosis.default_path.instances:,-->. There is also no cross-call
state, so `engine.disambiguate("MS", a_later_sentence)` returns `None` no matter how many earlier
calls defined `MS`. Carry the definitions yourself if you want them to persist:
`ExpansionDictionary.from_pairs(engine.extract_definitions(whole_document))`.

Every result also reports `margin`, the score gap between the top two candidates, and
`LexicalDisambiguator(config, vocab, min_margin=...)` will decline to answer below a margin you
choose. **It is off by default and it is a precision instrument, not an accuracy fix.** Raising the
gate raises accuracy among the questions still answered and lowers F1 at every step — from
41.65<!--claim:disambiguation.sdu21.abstention_curve.gate_0.00_f1:.2f--> % ungated to
15.07<!--claim:disambiguation.sdu21.abstention_curve.gate_0.20_f1:.2f--> % at the tightest gate
measured. Worse, below gate `0.10` the shared task's own most-frequent-expansion baseline is *more*
accurate on the gate's own answered subset, and on three- and four-candidate sets it still is at the
gate where the pooled numbers cross over. The full curve, its losing comparison in the same table,
and the decomposition by candidate-set size are in
[docs/EVALUATION.md](docs/EVALUATION.md#abstention-a-precision-instrument-and-where-it-is-worse-than-doing-nothing);
the run is `disambiguation.sdu21.abstention_curve` in [bench/results.json](bench/results.json), on a
**tuning split**, so no point on it is a default this library adopts.

Note that `AcronymEngine.disambiguate` above has no gate: `min_margin` is a constructor argument of
`LexicalDisambiguator`, which you build directly over your own dictionary. That gap is deliberate —
the gate needs two candidates to compare, and the facade's default path almost never has them.

### Multilingual — English complete, others experimental

Categorised stop-word taxonomies ship for English, French, Spanish and German, and generation works
for all four:

```python
from acronymkit.enums import Language
AcronymEngine(Config(language=Language.FR)).generate("Système de Gestion de Base de Données")  # SGBD
AcronymEngine(Config(language=Language.DE)).generate("Allgemeine Deutsche Automobil Club")     # ADAC
```

**But only English ships a lexicon and a character model.** For fr/es/de, Λ(A) is identically zero
(no candidate is ever reported as a dictionary word) and Φ(A) is uniform (pronounceability stops
discriminating). Positional fidelity carries generation on its own, which is why the examples above
are still correct — but treat those languages as experimental.

This is deliberate. The v0.1.0 word lists for those languages were model-authored, which made every
dictionary claim about them unverifiable, and unlike English there is no permissively licensed
replacement to swap in: the available Hunspell dictionaries are copyleft, and German's only permissive
arm grants distribution solely alongside ODF applications. Given the choice between invented data and
no data, no data is correct — invented data produces confident wrong answers a caller cannot detect.

The engine says so rather than degrading silently:

```python
result = AcronymEngine(Config(language=Language.FR)).generate("Système de Gestion de Base de Données")
result.metadata.warnings
# ["no bundled lexicon for language 'fr': Lambda(A) is always 0, ...",
#  "no bundled n-gram model for language 'fr': Phi(A) is uniform, ..."]
```

To get real coverage, install a dictionary yourself — it stays on your machine, so its licence is
your call, not ours:

```bash
python tools/fetch_data.py hunspell-fr
python tools/build_lexicons.py --language fr --output ~/fr.txt
```

```python
Config(language=Language.FR, lexicon_path=Path("~/fr.txt").expanduser())
```

## Execution tiers

| Tier | `EngineTier` | Dependencies | Latency | Use for |
|---|---|---|---|---|
| 0 | `ZERO_DEPENDENCY` | stdlib + Pydantic | **98<!--claim:micro.generate_fast.median:.0f--> µs/call**, 2.3<!--claim:micro.import.cold_import_ms:.1f--> ms to import | Edge, high-throughput indexing, hot paths |
| 1 | `STATISTICAL_NLP` | spaCy **or** NLTK | single-digit ms | POS-aware generation on messy human text |
| 1 | `HYBRID_NLP` | optional | either | Production default — degrades gracefully |
| 2 | `NEURAL` | ONNX Runtime | — | **Phase 3, not in this release** |
| — | `AUTO` | — | — | Best tier available at import time |

**The import figure is the shell, not the engine, and quoting it alone would flatter us.**
`import acronymkit` is cheap because the package resolves its re-exports lazily; `from acronymkit
import AcronymEngine` still costs
128.1<!--claim:micro.import.cold_import_engine_ms:.1f--> ms and import-plus-first-result
196.0<!--claim:micro.import.cold_first_result_ms:.1f--> ms. Laziness **moves** the Pydantic cost to
first use rather than removing it, so the win is confined to a process that imports the package
without using it. All three come from `micro.import` in
[bench/results.json](bench/results.json) and are read together in
[docs/EVALUATION.md](docs/EVALUATION.md).

Degradation is never silent in the payload: the effective tier lands in `metadata.engine_tier`, the
requested one in `metadata.requested_tier`, and the reason in `metadata.warnings`. Set
`Config(strict=True)` to turn degradation into a `TierUnavailableError` instead.

## The scoring function

Candidates are ranked by a configurable composite objective:

$$S(A, T) = \alpha \sum_{i} \omega(c_i, w_{j(i)}) \;+\; \beta \, \Phi(A) \;+\; \gamma \, \Lambda(A) \;-\; \delta \, \Psi(T, A)$$

| Term | Meaning |
|---|---|
| `ω(cᵢ, w)` | **Positional mapping weight** — 10 when `cᵢ` is the initial character of `w`, 3 when internal or terminal, 2 when it directly follows a previously matched character of the same token |
| `Φ(A)` | **Phonotactic pronounceability** — mean character-bigram log-likelihood, `(1/(k−1))·Σ log P(c_{m+1} \| c_m)` |
| `Λ(A)` | **Lexical match** — 1 when `A` is a real word in the target lexicon (a successful backronym), else 0 |
| `Ψ(T, A)` | **Information loss** — count of semantically critical tokens the acronym drops |

`Φ` behaves the way you would hope: Φ("SCALE") = −2.29, Φ("PDF") = −6.22, Φ("XKCD") = −7.46.

The syllable heuristic underpinning it is measured, not asserted: against the
117,485<!--claim:validation.syllables_cmudict.words_scored:,.0f--> CMUdict
entries it scores **84.1<!--claim:validation.syllables_cmudict.exact_match_pct:.1f--> % exact** and
**99.5<!--claim:validation.syllables_cmudict.within_one_pct:.1f--> % within one syllable** (mean
absolute error 0.16<!--claim:validation.syllables_cmudict.mean_absolute_error:.2f-->).
Reproduce with `python tools/build_lexicons.py --validate-syllables`.

### Presets

`ScoringStrategy` selects a calibrated `(α, β, γ, δ)` vector:

| Strategy | Behaviour |
|---|---|
| `STRICT_INITIALISM` | **Default.** Positional fidelity dominates; reproduces the textbook initialism |
| `BALANCED_PRONOUNCEABLE` | A real trade: pronounceability and dictionary hits can outrank the literal initialism |
| `MAX_PRONOUNCEABLE` | Phonotactics dominate — for product and project naming |
| `DICTIONARY_BACKRONYM` | A real word outweighs almost everything else |
| `CUSTOM` | You supply `ScoringWeights` |

```python
# "Structured Query Language Transaction Protocol"
STRICT_INITIALISM   -> 'SQLTP'   pronounceability 0.11
MAX_PRONOUNCEABLE   -> 'SQULTP'  pronounceability 0.65

# "Network Exchange Unified Security"
DICTIONARY_BACKRONYM -> 'NEXUS'  (dictionary word, score 92.95)
```

The defaults are calibrated rather than guessed, by a committed script
(`tools/tune_presets.py`) so the claim is falsifiable. `STRICT_INITIALISM` reproduces **all sixteen**
entries of a canonical corpus of textbook initialisms (API, PDF, NASA, HTML, RAM, CPU, GPU, SCUBA,
LASER, SQL, CRM, QA, TCP, SOAP, BIOS, ROM), and keeps doing so when β, γ or δ are perturbed by
50–100 % — a genuine plateau rather than a fitted point. `tests/test_scoring_presets.py` pins the
corpus so retuning cannot silently regress it.

`BALANCED_PRONOUNCEABLE` deliberately does *not* reproduce that corpus, and it is worth knowing why.
Against the real 76,879-word lexicon there is provably no coefficient vector that both weights
dictionary hits meaningfully and returns every textbook initialism: suppressing a vowel insertion
needs a length penalty above ~14, which then over-penalises the short acronyms instead. So the preset
honours its name — it returns `QUA` for "Quality Assurance", because "qua" is a word. See
[docs/DECISIONS.md](docs/DECISIONS.md).

> **One deliberate deviation from the published formulation.** The positional term is a *sum*, so it
> grows monotonically with length — used unmodified as a generation objective it prefers `PODOFO` to
> `PDF`. `ScoringWeights.length_penalty` (default 8.0) closes that gap, sitting between
> `contiguous_weight` (2) and `initial_weight` (10) so that covering a new token nets +2 while taking
> a second letter from a token already used nets −6. Set `length_penalty=0.0` to recover the
> unmodified objective exactly.

## Command line

```bash
pip install "acronymkit[cli]"
```

### Governed naming from the command line

Seven of the sixteen commands read a governed vocabulary. `expand-token`, `expand-identifier`,
`physical-name`, `check-name` and `normalize-name` answer one subject each — `check-name` exits 1 when the name does
not conform, so it works as a gate. Two answer a whole schema in one process:

```bash
acronymkit governed-batch --dictionary std/ --op expand < columns.txt > answers.jsonl
acronymkit governed-audit --dictionary std/ --suggest   < columns.txt
```

**`governed-batch` streams**: one record per line in, one JSON object per line out, nothing
accumulates, so a fifty-thousand-column schema costs the same memory as a hundred-column one and the
reader sees the first answer before the last question is asked. `--op` selects `expand`, `physical`,
`check`, `normalize` or `audit`; every record carries `line`, `input` and any `id` it arrived with.
An error rides on its own record and never aborts the run, the process exits 1 if any record failed,
and the one-line summary goes to stderr so every line of stdout is a record. This is the command that
makes the library usable from another language: answering one name takes microseconds and starting a
Python interpreter takes tens of milliseconds, so a pipeline that shells out per column pays almost
all of its cost outside the work.

**`governed-audit`** reduces the same corpus to one report — coverage, round-trip breaks, compliance
findings by reason code, and the unknown-token backlog ranked by how often each token appears and in
how many of them. `--suggest` proposes catalog rows to write, `--limit` controls truncation,
`--details` keeps one record per name in the JSON.

`--dictionary` takes a bundle directory, a JSON catalog or a CSV on all seven, with
`--dictionary-format`, `--columns` and `--delimiter` saying how to read it — and it refuses to guess
which way round a two-column CSV is meant to be read, because both readings are valid vocabularies
that mean different things. Every command here except `governed-batch` also takes `--format json`.

[docs/QUICKSTART_GOVERNED.md](docs/QUICKSTART_GOVERNED.md) runs all of it end to end, from a
spreadsheet export to a diff against whatever you use today. Driving `governed-batch` from another
runtime is [docs/JAVA_INTEROP.md](docs/JAVA_INTEROP.md), with a runnable Maven project in
[examples/java/](examples/java).

### Generation, extraction and scoring from the command line

```bash
acronymkit generate "Self Contained Underwater Breathing Apparatus" --top 3
```

```
Phrase:  Self Contained Underwater Breathing Apparatus
Primary: SCUBA  (score 27.264)

RANK  ACRONYM   SCORE  PRONOUNCE  DICT
----  -------  ------  ---------  ----
   1  SCUBA    27.264       0.75  yes
   2  SCOUBA   19.352       0.77  no
   3  SCUBRA   19.284       0.75  no

Score breakdown for SCUBA:
  TERM               VALUE  COEFF  CONTRIBUTION
  ----------------  ------  -----  ------------
  positional        50.000      1        50.000
  phonotactic       -2.943   0.25        -0.736
  lexical            1.000      2         2.000
  information_loss   0.000     25        -0.000
  total                                  27.264
```

Also available: `backronym`, `synthesize`, `extract`, `score`, `tokens`, `schema`, `version`. Every
command takes `--format json` for the schema-conformant payload, and `extract` reads stdin.

## Batch and async

```python
batch = engine.batch_generate(phrases, max_workers=8)
batch.succeeded          # results in submission order
batch.errors             # {index: message} — one failure never aborts the batch

results = await engine.abatch_generate(phrases, concurrency=16)
```

A single `AcronymEngine` is immutable and safe to share across threads and event loops.

## Interoperability

Results serialise to a versioned JSON Schema,
[`schemas/acronym-engine-result.schema.json`](schemas/acronym-engine-result.schema.json), shared with
the planned `acronym4j` Java port:

```python
from acronymkit.serialization import validate_result
validate_result(result.to_dict())      # raises if the payload drifts from the contract
```

## Data provenance

The bundled English lexicon is derived from **SCOWL** (size cut ≤ 60, 76,879 entries) and the syllable
validation from **CMUdict**. Both are permissively licensed and redistributed with their notices in the
resource headers. Every asset is pinned to a commit or release tarball and verified by SHA-256, because
a silent upstream edit to a word list changes Λ(A), which changes every score.

[`data/LICENSES.md`](data/LICENSES.md) is the ledger: source, licence, checksum, and — for anything not
redistributable — the reasoning for why not. `tools/build_lexicons.py` refuses to write a
non-redistributable asset into the package, so the rule is enforced by code rather than by diligence.

```bash
python tools/fetch_data.py --list        # the registry
python tools/fetch_data.py --verify      # re-check every checksum
```

## Honest scope

- **The governed subsystem's accuracy figure is about one function, and it was measured before its
  corpora were declared.** Catalog lookup is exact by construction; what is measured is where an
  identifier gets *cut*, against captions the publishers wrote. Every governed run records
  `splits_declaration = UNDECLARED`, and none has been re-measured since — so it is
  measured-before-declared, not held-out. On identifiers carrying no boundary mark at all, exact
  match falls to 34.93<!--claim:governed_gold.socrata.columns.unmarked.exact_pct:.2f--> % on Socrata
  and 0.75<!--claim:governed_gold.sec_xbrl.filer_extension.unmarked.exact_pct:.2f--> % on SEC filer
  extensions. Those rows ship in the same table as the headline, not beneath it.
- **No catalog is in that figure, and no real governed catalog has ever been measured.**
  `bench/run_governed_gold.py` scores every governed row through
  `expand_identifier(identifier, GovernedDictionary({}))` — an **empty** catalog, which the corpus
  admission rule forces, because a populated one would rewrite the identifier and the two strings
  would stop sharing a character stream. So the number above is about the splitter with the catalog
  switched off. Socrata captions and SEC filer extensions are **public substitutes** for a data
  standard, not a standard anybody governs a schema with, and the one experiment that did build a
  catalog — over real Socrata schemas, portal-disjoint — found it scoring no better than an empty
  one. That is the standing unknown this project cannot close from inside itself, and it is
  [reversal one](docs/POSITIONING.md#reversal-one-the-lead-is-wrong-if-a-catalog-is-worth-nothing-on-a-real-schema).
- **Two of the four tasks the split manifest recognises have no corpus that could adjudicate them,
  and that is a standing property rather than an emergency.**
  `headline_capable('extraction')` and `headline_capable('disambiguation')` both return an empty
  list, enforced in code and printed by `python tools/splits.py --check` on every run. Read "two"
  with its denominator: `TASKS` holds four names, and **generation and backronym alignment are not
  among them**, so for those two the question is never asked at all — their corpora are declared
  tuning and contaminated, which is a weaker statement than an empty row and looks like a stronger
  one. Filling the first needs a second adjudicator who
  authored none of the pooled systems — a person, not an afternoon. Filling the second costs this
  project its last blind split, which is already allocated elsewhere. Both are costed in
  [docs/POSITIONING.md](docs/POSITIONING.md#the-two-rows-that-are-empty-and-what-filling-each-costs).
- **Held-out evidence exists for span detection and for nothing else this README leads with.** PLOD
  and SDU@AAAI-21 AI are declared held out and uncontaminated in
  [`bench/splits.toml`](bench/splits.toml). MED1250 (extraction, generation) and SDU@AAAI-21 AD
  (disambiguation) are declared tuning and contaminated. SDU@AAAI-21 AD `test.json` is the one
  genuinely blind split still available, and it is deliberately unspent.
- **Extraction is evaluated on two corpora, both biomedical.** MED1250 is biomedical abstracts and
  is a *tuning* set — its miss taxonomy has been read in full. PLOD was added to close the
  domain-generalisation gap and turned out not to: it is PLOS journal text, also dominated by the
  life sciences. **No evidence exists for legal, financial or general-web text.** Treat the
  comparison as sound and the absolute level as provisional.
- **System rankings are corpus-dependent, and we have measured that.** `pyab3p` beats us on
  MED1250; we beat it on PLOD's span-detection task. Any single-corpus ranking, including ours,
  should be read with that in mind.
- **14.01<!--claim:oracle.med1250.universal_miss_pct:.2f--> % of that corpus is found by no system
  at all**, ours or anyone's. The practical ceiling is
  85.99<!--claim:oracle.med1250.oracle_union_recall:.2f--> % rather than perfect recall, and every
  figure here should be read against it.
- **English only.** French, Spanish and German ship no lexicon; those languages degrade honestly and
  say so in `metadata.warnings`.
- **Disambiguation is measured and it loses.** On SDU@AAAI-21 it scores
  41.65<!--claim:disambiguation.sdu21.acronymkit.accuracy:.2f--> % accuracy against
  72.84<!--claim:disambiguation.sdu21.most_frequent.accuracy:.2f--> % for simply always picking the
  most common expansion. It beats random, so the context
  signal is real, but on that benchmark it is worth less than memorising frequencies. Use it for
  document-local resolution, where inline definitions carry it; do not expect it to win a
  disambiguation benchmark.
- **Abstention is a precision instrument, not an accuracy fix, and there is a region where it is
  worse than doing nothing.** Raising `min_margin` lowers F1 monotonically, and below gate `0.10`
  the shared task's own most-frequent-expansion baseline beats the gated system on the gated
  system's own answered subset. Read against that baseline at **full** coverage —
  72.84<!--claim:disambiguation.sdu21.abstention_curve.gate_0.00_most_frequent_accuracy_same_subset:.2f--> % —
  no gate on the published curve wins until `0.15`, where the system answers
  16.77<!--claim:disambiguation.sdu21.abstention_curve.gate_0.15_coverage_pct:.2f--> % of the split
  at F1 20.95<!--claim:disambiguation.sdu21.abstention_curve.gate_0.15_f1:.2f-->. At the gate where
  the pooled same-subset comparison crosses over, the baseline still wins on three- and
  four-candidate sets —
  32.38<!--claim:disambiguation.sdu21.abstention_curve.instances_in_those_arities_pct:.2f--> % of
  that split. The curve, the losing comparison and the decomposition are in
  [docs/EVALUATION.md](docs/EVALUATION.md).
- **The default `disambiguate` path performs no selection.** With no `dictionary=` it is an
  inline-definition lookup: no candidate at all on
  97.45<!--claim:disambiguation.sdu21.diagnosis.default_path.no_candidate_pct:.2f--> % of that
  split's instances. If you came here for disambiguation, pass a dictionary.
- Every *measured* figure in this README is traceable to [`bench/results.json`](bench/results.json),
  and CI fails the build if a performance claim **that the gate can recognise** cannot be traced back
  to a benchmark run. The word matters and it used to say *anywhere*, which was false: the gate arms
  a number when a metric keyword sits near it or a unit follows it, so a sentence naming a median
  latency in microseconds passes untouched while one naming an accuracy percentage in the same
  position fails the build. Both were injected to check it, and the test that pins the difference is
  `tests/test_claims_gate_coverage.py`. What the gate cannot recognise it
  **counts and publishes** rather than ignoring — `python tools/check_claims.py` prints the
  unrecognised residue on every run, and `--residue` names it line by line. **Three structural counts
  are left in this README**, none of them a benchmark result and each re-derivable from the tree:
  seven of the sixteen CLI commands read a governed vocabulary (`acronymkit --help`); the bundled
  English lexicon's entry count (`grep -cv '^#\|^$' src/acronymkit/resources/lexicon_en.txt`); and
  the size of the textbook-initialism corpus the default preset reproduces
  (`len(conftest.CANONICAL_ACRONYMS)`). **The claims gate arms none of the three**, so none of them
  would turn the build red on going stale — the lexicon figure was replaced with an invented value
  in this tree and `python tools/check_claims.py` exited zero without naming the file. The two that
  used to sit beside the CLI count, share of the source and share of the public symbols, are gone
  with the argument they were making: "governed naming leads because it is bigger" was the wrong
  reason, and the sentence that sent a reader to [docs/EVALUATION.md](docs/EVALUATION.md) for all
  three derivations only ever resolved for one of them.

## Documentation

- [What this library is for](docs/POSITIONING.md) — the positioning taken and the two that were not,
  what committing to it costs, the monoculture measurement that is the argument for it and the genre
  confound that limits how far it can be pushed, the two rows no corpus can adjudicate with each
  filling instrument costed, and the three conditions that would reverse the decision
- [Architecture](docs/ARCHITECTURE.md) — subsystem map, tier policy, resource formats, extension points
- [Governed naming](docs/GOVERNED_NAMING.md) — deterministic short→long expansion against a schema
  catalog: the custom-first precedence chain, every verb with real output, the four invariants, and
  why refusing to guess is the right design for governed data
- [Governed naming in five minutes](docs/QUICKSTART_GOVERNED.md) — the same subsystem from the
  command line, from a spreadsheet export to a whole schema in one process, ending in a diff against
  the implementation you have now
- [Technical note: the governed JSON wire contract](docs/notes/governed-json-contract.md) — the exact
  JSON shape of every DTO and fixture, written so a port can be validated against the same golden
  files. No JVM artifact exists; this is what would make writing one mechanical
- [Calling this library from the JVM](docs/JAVA_INTEROP.md) — which route a Java Maven project should
  take and what each one needs on the machine: the `governed-batch` co-process, GraalPy as a Maven
  dependency, Py4J, JPype and a hand-written port, with the measurements behind the recommendation
- [`examples/java/`](examples/java) — a runnable Maven project for the recommended route: a
  co-process client, the wire format by hand, and the real output. No CI job builds it
- [Contributing](CONTRIBUTING.md) — the invariants that are easy to break by accident
- [Technical note: using a ranking function as a generation objective](docs/notes/scoring-objective.md)
- [Technical note: should `extract()` report an abbreviation whose expansion it does not
  know?](docs/notes/w11-emission-model.md) — the emission-model question scoped and costed. Nothing
  is decided and no behaviour changed. A one-line all-caps rule does beat this library's short-form
  score on the one held-out corpus that can see it — but only against the whole gold, which counts
  every occurrence of an abbreviation rather than every definition. Restricted to the gold spans a
  definition extractor can stand in front of at all, the result reverses; the decomposition, and
  what the span scorer can and cannot see about a pairing, are in
  [docs/EVALUATION.md](docs/EVALUATION.md)
- [Evaluation](docs/EVALUATION.md) — every measured number, with the losing comparison beside each
  one: governed cut placement and its flatcase rows, extraction against four other systems,
  generation recall@k, disambiguation against a trivial baseline, and the abstention curve scored
  against that same baseline on its own answered subset
- [Decisions](docs/DECISIONS.md) — what was tried and rejected, and why
- [Definition of done](docs/DEFINITION-OF-DONE.md) — the fourteen criteria this library is held to,
  swept and verdicted: which are met, which are not, what evidence each rests on, and the criterion
  renumbered this round from the ninth to the tenth — that neither the flagship extraction figure
  nor the disambiguation figure has a corpus that could adjudicate it
- [Enterprise review](docs/ENTERPRISE.md) — the short answer for someone deciding whether to allow
  this package: air-gapped install, security posture with each claim's proof named, and the exact
  error text when something is missing
- [Support matrix](docs/SUPPORT_MATRIX.md) — capability by tier by "works offline" by "what it
  needs", including what English ships that fr/es/de do not
- [Offline and air-gap review](docs/OFFLINE.md) — the long form: how the no-network claim was
  measured, what the measurements cannot see, and how to reproduce them
- [Installing without PyPI](docs/INSTALL.md) — release-asset wheel, git tag, source checkout, or a
  per-platform offline bundle that installs with `--no-index` and needs no package index at all
- [Security policy](SECURITY.md) — threat model and disclosure
- [Changelog](CHANGELOG.md)

## Extending

| You want to… | Do this |
|---|---|
| Use a bigger dictionary | `Config(lexicon_path=Path("/usr/share/dict/words"))` |
| Score against a domain corpus | `CharNGramModel.train(my_words)` → JSON → `Config(ngram_model_path=…)` |
| Add a language | Add `stopwords_<lang>.json` + `lexicon_<lang>.txt`, generate `ngram_<lang>.json`, add a `Language` member |
| Change ranking | `Config(scoring_strategy=ScoringStrategy.CUSTOM, scoring_weights=ScoringWeights(...))` |
| Suppress domain noise | `Config(custom_stop_words=frozenset({"solution", "platform"}))` |
| Plug in your own tagger | Implement the `NlpBackend` protocol |

## Roadmap

- **Phase 1 — Tier 0 engine and extractive foundation.** ✅ Shipped in 0.1.0
- **Phase 2 — Statistical NLP and phonetic scoring.** ✅ Shipped in 0.1.0
- **Phase 3 — Tier 2 neural disambiguation.** Quantised sentence encoder via ONNX Runtime (no PyTorch
  runtime dependency), indexed against SciAD/GLADIS-scale expansion dictionaries.
  `LexicalDisambiguator` already implements the contract the neural backend will satisfy, and
  `EngineTier.NEURAL` is accepted today, so selecting it is forward-compatible.
- **Phase 4 — `acronym4j` on Maven Central.** API parity, byte-identical JSON, same schema.

## Licence

[MIT](LICENSE)
