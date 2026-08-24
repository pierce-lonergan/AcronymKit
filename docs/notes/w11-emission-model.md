# W11 — should the extractor emit a short form without a long form?

**Status:** scoping note. No decision, no behaviour change, nothing shipped. ·
**Promotes:** the API question [D-041](../DECISIONS.md) posed and deliberately refused to answer ·
**Ordering claim:** this must be scoped *before* W10 ·
**Reads as authority:** `docs/AUDIT-2026-08.md` section 0, then gated run ids in `bench/results.json`,
then `docs/DECISIONS.md`, then `bench/splits.toml`.

D-041 established a constraint and then found a question underneath it. The constraint is that
`AbbreviationExtractor` emits a pair, the pair is atomic, and so any filter that rejects a candidate
for its long form deletes the short form standing beside it. The question is:

> **Should `extract()` be able to emit a short form with an absent, or low-confidence, long form?**

That is the abstention thesis in the extraction half — *this is an abbreviation and I do not know
what it stands for* — and it is a product decision, not a rule. This note scopes it, costs it, and
gives it a failure mode. It does not decide it.

**A numbering note so two counters do not collide.** W11 is a *workstream* number. R7's "experiment
eleven is the next free number" is a different counter — the next experiment this project logs is
experiment eleven, whichever workstream logs it, and it may well not be this one. The two elevens are
unrelated, and any record that mentions either should say which it means.

**Every figure below is a gated field in `bench/results.json`, cited by run id, or a live
re-derivation of one.** Where a number comes from `bench/splits.toml` rather than from a runner, it
is labelled as such, because the manifest is authority 4 and a runner's `--save` is authority 2.
Arithmetic over two gated fields is marked as arithmetic. Nothing here is a new measurement of the
library, and no claim in this note is eligible for README.md or `docs/EVALUATION.md` until a runner
writes it.

## Contents

1. [What the corpora actually say](#1-what-the-corpora-actually-say)
2. [The API question](#2-the-api-question)
3. [The measurement question](#3-the-measurement-question)
4. [The interaction with W10](#4-the-interaction-with-w10)
5. [The honest case against](#5-the-honest-case-against)
6. [How W11 fails, and the stop rule](#6-how-w11-fails-and-the-stop-rule)
7. [What W11 is not](#7-what-w11-is-not)
8. [Deliverables, in order, with the gate each must pass](#8-deliverables-in-order-with-the-gate-each-must-pass)

---

## 1. What the corpora actually say

### 1.1 Every corpus that scores the two labels separately annotates more abbreviations than definitions

Re-derived live from the pinned corpora through `bench/corpora.py`, not transcribed from D-041, and
agreeing field-for-field with the gated records named in the last column.

```
re-derived 2026-08-24 via bench.corpora.read_plod_cw / read_sdu22_ae

  corpus                split   docs   gold SF   gold LF   LF/SF     SF-LF   gated as
  plod_cw               dev      126       263       152   57.79 %     111   shortform.plod_dev.corpus
  plod_cw               test     153       270       152   56.30 %     118   shortform.plod_test.corpus
  plod_cw               all    1,351     2,869     1,804   62.88 %   1,065   shortform.plod_all.corpus
  sdu22_ae_legal        dev      445     1,213       669   55.15 %     544   shortform.sdu22_ae_legal_dev.corpus
  sdu22_ae_scientific   dev      497       970       720   74.23 %     250   shortform.sdu22_ae_scientific_dev.corpus

  the SF and LF columns are gated fields; LF/SF and SF-LF are arithmetic over them
```

**The two ceiling formulas are different and must not be swapped.** `bench/run_shortform.py` prints
the ceiling as *gold long forms / gold short forms* for SDU-22 and as *the share of gold short forms
standing in one of the two parenthetical arrangements* for PLOD. Only the SDU-22 column above is the
project's published ceiling. The PLOD ceiling is a different gated field.

```
bench/results.json
  shortform.sdu22_ae_legal_dev.corpus.ceiling_pct                            55.15
  shortform.sdu22_ae_scientific_dev.corpus.ceiling_pct                       74.23
  shortform.plod_all.corpus.short_form_spans_bracket_adjacent_pct            46.11
  shortform.plod_all.corpus.gold_short_form_spans_multi_token_pct             0.00
```

Applying the SDU-22 formula to PLOD would produce a number this project has never published and
would silently redefine a ceiling. It is written out here so the next reader does not do it.

### 1.2 The decisive table, and it is the one that argues *against* the naive version of W11

R5 requires the losing comparison beside the headline. Here the losing comparison is the headline.

```
bench/results.json, spans.plod.all.tight.*   -- PLOD-CW, HELD OUT, uncontaminated,
exact convention, native offsets, gold 2,869 SF / 1,804 LF (spans.plod.all.corpus)

  system                              sfP      sfR     sfF1  |   lfP     lfR    lfF1
  acronymkit.high_precision.native   93.66    36.53    52.56 |  83.91   52.05   64.25
  acronymkit.general.native          93.58    36.60    52.62 |  83.87   52.16   64.32
  pyab3p                             92.86    35.34    51.20 |  85.35   51.66   64.36
  scispacy                           93.39    32.49    48.20 |  83.47   46.18   59.46
  allcaps  (one-line rule)           64.45    73.37    68.62 |   0.00    0.00    0.00
  oracle_definitional (union, no allcaps)     37.50          |          53.71
  oracle              (union, all rows)       82.36          |          53.71
```

Four things to read off it, in order of how uncomfortable they are.

**`allcaps` already emits short forms with no long forms.** It is `predict_all_caps` in
`bench/run_spans.py`, it predicts no long form by construction, its long-form row is printed as zero
rather than hidden, and the span harness scores it without complaint. **The emission model W11 is
proposing already exists in this repository as a baseline.** What W11 would ship is not the
capability; it is a better rule inside it.

**And that baseline beats the shipped extractor on the short-form label.** On short-form F1, on a
held-out corpus, on both detokenisation styles and on both splits. The gap is not marginal.

```
bench/results.json, short_form.exact_f1
  split / style          acronymkit.high_precision.native      allcaps
  all   / tight                     52.56                       68.62
  all   / spaced                    52.54                       68.62
  test  / tight                     53.23                       64.37
  test  / spaced                    53.76                       64.37

  allcaps is scored in token space with no detokenisation, which spares it a cost
  the real systems pay. bench/run_spans.py states that advantage; it is small and
  it is not the explanation for a ten-to-sixteen-point gap.
```

**The union rows size the opportunity exactly.** `oracle_definitional` is the union of every
definition extractor in the table with `allcaps` removed; `oracle` is the union including it. The
band between them is the population of gold short forms that no pair-emitting system in the table
reaches and a one-line rule does.

**This is the same shape as D-044, and that is the warning.** Definition of Done 1 shipped a
mechanism for the disambiguator to decline to answer, and then the curve showed it losing to counting
words. The settled statement of that result, which is the one to use:

```
docs/DECISIONS.md D-044, from disambiguation.sdu21.abstention_curve
  the full-coverage `most_frequent` baseline at 72.84 is not beaten by ANY
  coverage level until gate 0.15, where the system answers under a sixth of the
  split, and F1 falls monotonically 41.65 -> 15.07
```

W11 is the extraction-half version of exactly that move, and it already has its trivial baseline
sitting in the results file with a better F1 than the library. **W11's product claim can therefore
never be "we can emit unpaired short forms".** It has to be "we emit unpaired short forms at a
precision materially above the all-caps rule while adding recall the pair model cannot reach" — and
that bar is already gated, on a held-out corpus, before any work starts. Section 6 turns it into a
stop rule.

### 1.3 The ceiling, printed in the same table as the recall it bounds

R9.6, and the manifest requires it for these corpora anyway.

```
bench/results.json, shortform.sdu22_ae_*_dev.*   -- BOTH SPLITS ARE TUNING AND
CONTAMINATED (bench/splits.toml). Exact convention, high_precision profile.

  corpus / variant                sfP      sfR    sfF1  |  ceiling   headroom
  legal      baseline           93.66    37.76   53.82  |  55.15      17.39
  legal      legend             94.41    44.52   60.50  |  55.15      10.63
  scientific baseline           95.90    57.84   72.15  |  74.23      16.39
  scientific legend             95.67    61.55   74.91  |  74.23      12.68

  ceiling is the gated `ceiling_pct`; headroom is arithmetic (ceiling - sfR)
```

The headroom column is what remains reachable *inside* the pair model. Everything above the ceiling
is the W11 territory, and the manifest is precise about the price a pair emitter pays to enter it:

> `bench/splits.toml`, `[corpora.sdu22_ae_legal] shortform_recall_ceiling_basis` — every point of
> short-form recall above the ceiling is bought by emitting a definition the corpus does not
> annotate, which is paid for in long-form precision.

**W11's whole technical content is that this price is an artefact of the emission model, not of the
task.** An unpaired emission gains the short-form true positive and contributes no long-form
prediction at all, so it is not paid for in long-form precision — it is free on that label, and the
entire cost moves onto short-form precision, where the all-caps baseline is waiting.

---

## 2. The API question

### 2.1 What the wire surface actually is — a correction to D-041

D-041 said this is R8 territory and named `docs/notes/governed-json-contract.md`, the golden fixtures
and a JVM port as the surfaces at risk. Checked against the repository, **none of those three is
affected**, and carrying that framing forward would price W11 far above its cost.

```
checked 2026-08-24

  docs/notes/governed-json-contract.md   §1 "Not covered: AcronymResult and the
                                         generation-side DTOs". It specifies
                                         acronymkit.governed only. AcronymPair and
                                         ExtractionResult appear nowhere in it.
  tests/fixtures/governed/golden/        8 .jsonl replay files, all governed verbs
                                         (expand_token, expand_identifier,
                                         is_compliant, to_physical_name, ...).
                                         There is NO golden fixture for extract().
  schemas/                               one file, acronym-engine-result.schema.json,
                                         title "AcronymEngineResult" -- generation.
                                         AcronymPair has no published JSON Schema.
  JVM                                    docs/JAVA_INTEROP.md: no artifact exists,
                                         and GraalPy cannot host generation or
                                         extraction on any platform, so a JVM caller
                                         has no extraction surface to break.
  governed-batch envelope                governed verbs only; extraction never
                                         crosses that pipe.
```

**What R8 does still bind is the Python wire, and it binds harder than it looks**, because the models
are frozen Pydantic with `extra="forbid"`:

```
verified 2026-08-24, PYTHONPATH=src

  AcronymPair(**{**pair.to_dict(), "long_form_present": False})
      -> pydantic ValidationError            (extra="forbid")
  AcronymPair(short_form="API", long_form=None)
      -> pydantic ValidationError            (long_form is a required str)

  emitted shape today, from `acronymkit extract --output-format json`
    {"short_form", "long_form", "short_form_span", "long_form_span",
     "confidence", "pattern", "sentence"}
```

So **any added key is a breaking change for a consumer that reconstructs the model from JSON**, and
any nullable long form is a breaking change for a consumer that reads it as a string. That is the
real R8 surface: one Python package, one CLI JSON mode, no schema, no port. It needs a design because
it is a public contract, not because it is wide.

### 2.2 The internal call sites, counted

These are the reads that a shape change has to service. Construction sites are excluded.

Symbols rather than line numbers, because two other workstreams were editing `src/acronymkit/` and
`bench/` while this was counted and the line numbers had already moved once.

```
src/acronymkit/  11 reads of the long form or its span, plus 3 doctests
  models.py         as_mapping()        -> dict[str, str]; the return type is a promise
  models.py         __str__             -> "SF = LF"
  extractor.py      _pair_anchor()      -> min(short_start, long_start)
  extractor.py      _attach_sentences() -> min(short_start, long_start)
  extractor.py      two de-duplication keys, both including long_form and its span
  disambiguation.py ExpansionDictionary.from_pairs() -> index.add(short, long)
  disambiguation.py _inline_expansions() -> content words OF THE LONG FORM
  cli.py            _render_extraction() -> two table columns

bench/           23 further reads across eight modules, including the pair scorer
                 (bench/scoring.py) -- a moving count, taken 2026-08-24
```

Two of those are load-bearing in a way that decides an option outright.

**`_pair_anchor` is `min(short_form_span[0], long_form_span[0])`, and it orders the output.** A
`(0, 0)` sentinel for an absent long form anchors every unpaired emission at offset zero, so
`_merge_in_document_order` sorts them all to the front of the document and `_attach_sentences`
attaches the *first sentence of the document* to every one of them. Both failures are silent and both
produce plausible-looking output.

**`confidence` is already a pair confidence and cannot express this.** `_confidence(short, long)` is
the initial-alignment fraction mapped into `[0.6, 1.0]`; it is a function of both forms and has no
value meaning "no long form". A second confidence field would have to be added, and it would still
require a long-form *string* to attach to.

### 2.3 The options

| | Shape | What breaks for a caller | Verdict |
|---|---|---|---|
| **A** | `long_form: Optional[str]`, `long_form_span: Optional[...]` on `AcronymPair` | Every caller reading `.long_form` as a string, in their code and under their type checker. `as_mapping()` must silently skip or emit `None`, and either is a behaviour change for callers who never asked for unpaired output. The type's name stops being true of its instances. | Viable only behind an opt-in that defaults off; the name is the lasting cost |
| **B** | A second type — `AbbreviationMention(short_form, short_form_span, sentence, …)` — carried on a new `ExtractionResult` field; `pairs` untouched | Nothing that reads `.pairs` changes at all. The break is narrow and exact: a consumer reconstructing `ExtractionResult` from a *newer* payload hits `extra="forbid"`. Two types to keep in step. | Lowest blast radius; the shape that matches what the corpora annotate |
| **C** | A confidence on the long form | Nothing, and that is the objection. A low-confidence long form is still a long-form string and still a long-form false positive, so the pair-atomicity cost is unchanged. It converts the question into a threshold on the long form alone — which D-041 lists as closed in advance. | Refused; it looks cheapest and answers nothing |
| **D** | A distinct emission mode (`Config` flag, or a separate `extract_mentions()`) | Orthogonal to A/B: it is the gate, not the shape. On its own it changes nothing. | Required *with* A or B, not instead of one |
| **E** | Sentinel `long_form=""` with span `(0, 0)` | No typing churn, and two silent corruptions: document order (`_pair_anchor`) and sentence attachment (`_attach_sentences`). `from_pairs` would index an empty expansion; `as_mapping()` would map an abbreviation to the empty string. | Refused on shipped evidence, §2.2 |

**The pairing that survives is B + D.** B keeps `AcronymPair` honest — a pair really is a pair — and
puts the new candidates somewhere a caller has to opt into reading. D keeps them off by default, which
is what D-044's status line ("met in mechanism, not met in value") says a feature in this shape has
earned until its number arrives.

**What B still costs, stated rather than waved past.** A second type means the disambiguator's
`from_pairs` gains nothing from mentions (correct — a mention has no expansion to index), so a caller
who switches to mentions gets *less* downstream capability, not more. And `ExtractionResult` grows a
field, which is the `extra="forbid"` break above. Neither is avoidable under any option, including A.

---

## 3. The measurement question

### 3.1 The harness already accepts an unpaired emitter — verified, and fragile

Both span paths drop an empty span before scoring, so a `(0, 0)` long-form span contributes no
long-form prediction and therefore no false positive:

```
bench/run_spans.py
  _distinct()             "Drop empties and repeats, order preserved."
  char_span_to_tokens()   `if end <= start: return frozenset()`
bench/run_shortform.py
  _engine_spans()         longs -> run_spans._distinct(longs)
  _tally()                per label, per convention, one-to-one via run_spans.match
```

So an unpaired emission scores today exactly as W11 would want it to. **That is a coincidence, not a
contract.** `_distinct` drops empties as a de-duplication nicety; nothing asserts it. If W11 ships, the
harness must state the rule and refuse a malformed span rather than silently discard it — otherwise a
genuine `(0, 0)` bug becomes invisible.

### 3.2 The only extraction corpus is structurally incapable of showing the benefit

R9's corpus-capability question, turned on W11 itself.

```
bench/scoring.py -- the MED1250 pair scorer, keyed on both halves
  key = f"{normalise_exact(short)}\x00{fold(long_form)}"
  gold_pairs = [(p.short_form, p.long_form) for p in document.pairs]
```

The prediction unit is the pair. An unpaired emission has no gold counterpart it can match, so on
MED1250 it is a pure false positive: **the benefit is invisible and the cost is fully charged.**
MED1250 is the only corpus registered under `task = "extraction"`, and it is `role = "tuning"`,
`contaminated = true`. There is no extraction corpus in this project that can adjudicate W11, and
building one is W10.

### 3.3 Which corpora could evaluate it, and what adopting them spends

Asked with `headline_capable(task)`, per R2, not assumed:

```
python tools/splits.py, Manifest.headline_capable
  extraction                []
  span_detection            ['plod', 'sdu21_ai']
  disambiguation            []
  identifier_segmentation   ['sec_xbrl', 'socrata']
```

**W11 is scored as `span_detection` on the `short_form` label. It needs no new task**, and that
matters: `TASKS` is a closed vocabulary because `bench/corpora.py` returns a different type per task,
and widening it is a contract decision rather than a one-word edit. W11 does not have to touch it.

| Corpus | Role | Can it score W11? | What using it spends |
|---|---|---|---|
| `plod` | held out, uncontaminated, already scored | Yes — both labels, both conventions, and the `allcaps` control is already in the table | **Scoring costs nothing. Diagnosing does.** Reading which short forms are missed and why is precisely the act that contaminated MED1250 and both SDU-22 dev splits. W11's diagnostic phase burns PLOD's blindness. |
| `sdu21_ai` | held out, uncontaminated, `reader_not_written` | Yes, once a reader exists | D-043 calls it "the only unspent capable instrument this project has for a span claim". Spending it on W11 removes the arm a D-039 default change would need. **Do not open it during scoping.** |
| `sdu22_ae_legal` / `sdu22_ae_scientific` dev | tuning, contaminated | Yes, and they already carry the ceiling in the same record | Nothing further; already spent. These are where W11's first measurements belong. |
| `sdu22_ae_*` `train.json` | tuning (declared per corpus) | Yes | **Contested and allocated elsewhere this round (R3). Not available to W11.** |
| `med1250` | tuning, contaminated | No — §3.2 | n/a |

**The budget statement W11 has to accept before it starts.** Its first numbers come from the two
SDU-22 dev splits, which are contaminated, plus PLOD scored *without* reading its miss set. The moment
W11 needs to know *why* a short form was missed, PLOD stops being blind and this project has one
held-out span arm left — the one D-043 has already argued should not be spent on a default-off flag.

**And a trap the manifest has already sprung once.** The two SDU-22 splits will disagree, and the
temptation will be to report the disagreement as a domain difference. `bench/splits.toml` refuses
that twice over: `[corpora.sdu22_ae_legal] domain_finding` records that the split named "legal" is
institutional and development-policy prose with zero occurrences of six basic terms of legal
practice, and `shortform_recall_ceiling_basis` records that most of the apparent gap between the two
splits is annotation density rather than extractor behaviour. **A W11 result decomposed by split is
decomposed by annotation density, not by domain**, and must be labelled that way.

### 3.4 The control W11 must build first, and it is cheap

There is no trivial baseline on SDU-22 AE. `predict_all_caps` exists only in token space for PLOD;
the SDU-22 reader returns `CharSpanDocument` with character offsets. Porting the same one-line rule to
character spans is a small, self-contained runner change and it is **deliverable one**, because
without it the SDU-22 short-form numbers have no floor under them and the R9 comparison cannot be run
on the corpora W11 is allowed to use.

---

## 4. The interaction with W10

**How W10 is read here.** W10 is taken to be the workstream that builds the held-out corpus the
extraction task has never had — the gap `tools/splits.py --check` prints as
`no uncontaminated corpus carries role='held_out' for task='extraction'`, and the item D-042 names as
the lead item on its adopted-library arm. If W10 is something else, this section is the part to
re-read before acting on it.

### 4.1 What W10 would have to annotate differently

```
a pairs-only corpus records            a W11-capable corpus also records
  short-form span                        every abbreviation OCCURRENCE, defined or not
  long-form span                         per occurrence: defined here / defined
  the link between them                    elsewhere in this document / never defined
                                         the guideline that decides what counts as
                                           an abbreviation occurrence at all
```

Three consequences, and the third is the expensive one.

**The extra pass is the cheap half.** D-041's own argument is that an abbreviation token is the least
ambiguous annotation these corpora carry and a long-form boundary is the most contested. So the
occurrence pass is the high-agreement, low-adjudication half of the work. The fear that W11 makes W10
much more expensive is, on this evidence, wrong — it makes it somewhat more expensive, in the half
that adjudicates fastest.

**The guideline decision cannot be deferred and is the whole precision question.** "What counts as an
abbreviation occurrence" is the operational definition W11's precision is measured against.
`allcaps` answers it with "any all-caps token of length two or more"; PLOD's annotators answered it
differently, and the difference is most of the gap in §1.2. A corpus that does not fix this in its
guidelines before annotation cannot adjudicate W11 afterwards, whatever it recorded.

**One artefact cannot declare two tasks.** `tools/splits.py` gives each corpus a single `task`, and
roles are declared per corpus — the same rigidity that makes SDU-22 `train.json` a tuning split it can
never escape. A W10 corpus registered as `extraction` returns `GoldDocument` and is scored by the pair
scorer of §3.2, which is blind to W11 by construction. Scoring W11 on the same artefact needs either a
second reader and a second registration, or an explicit manifest change to allow per-task roles. That
is a design decision about `bench/splits.toml` and `bench/corpora.py`, and it belongs in W10's plan
rather than being discovered halfway through annotation.

### 4.2 What is actually wasted if W10 is built pairs-only first

**Not the pair annotation.** Every pair a pairs-only corpus records is still correct under W11; the
occurrence pass is additive and can be run later over the same documents.

**The blindness is what is wasted, and it does not come back.** The moment a pairs-only W10 corpus is
scored, it is spent as a held-out extraction arm. Adding an occurrence pass afterwards produces a
corpus that is no longer blind for the short-form label either, because the documents and the system's
behaviour on them have already been read. The project would then hold a corpus that can adjudicate
neither task blind — which is the position it is in today, arrived at more expensively.

**That is the ordering argument, and it is narrower than "weeks of adjudication against the wrong
unit".** The adjudication is not wasted. The *blindness* is, and blindness is the thing this project
has run out of on three tasks already.

---

## 5. The honest case against

### 5.1 The corpus asymmetry is partly an annotation convention, and the code already says so

PLOD tags abbreviation tokens wherever they occur, not only where they are defined. So more gold short
forms than long forms is in part a statement about what the corpus is *for*. Reading the `2,869`
against `1,804` in §1.1 directly as a measure of work the library is missing is the same error as
reading MED1250's zero collateral in D-041 as "the rule is free" — in both cases the corpus is being
asked a question it was not built to answer.

This is not a new caution invented for this note. It is in the runner:

```
bench/run_spans.py, union_recall.__doc__
  "the gap between the two is the corpus's annotation convention rather than any
   system's ability"
```

The union rows in §1.2 are therefore the *upper* reading of the opportunity, and the docstring that
produces them says so.

### 5.2 The manifest already carries part of the discriminator, and it cuts against W11

Recorded in `bench/splits.toml` under `shortform_recall_ceiling_basis` — **corpus-structure counts
kept in the manifest, not gated through a runner**, which is the manifest's own stated reason for
holding them:

```
bench/splits.toml, [corpora.sdu22_ae_legal] and [corpora.sdu22_ae_scientific]
  legal dev        551 of 1,213 gold acronym spans (45.42 %) exceed the
                   definitions their own sample records
                   -- and only 18 of them sit in samples with ZERO annotated
                      long forms
  scientific dev   265 of 970 (27.32 %)
```

Read that carefully, and then read it more carefully still, because the obvious inference is one this
note nearly published.

**What the `18` does establish:** almost every excess acronym span sits in a sample that annotates at
least one definition. So the excess is not concentrated in passages where nothing is defined at all.

**What it does not establish, and what a first draft of this section claimed it did:** that each
excess span's *own* surface is defined in its own sample. A sample with one annotated definition and
ten excess spans of ten different acronyms satisfies the `18` count perfectly while being nine parts
genuine capability gap. **The count is over samples, and the question is over surfaces.** It is
suggestive against W11 and it is not evidence for the conclusion it invites — which is precisely why
§5.3 exists and why the discriminator has to be run per surface rather than per sample.

If the per-surface answer does come back the way the per-sample count hints, then an unpaired mention
would be reporting an abbreviation whose expansion is available in the same passage and which the
library could have paired. That is not "I do not know what it stands for". That is "I found it twice",
and it has a cheaper fix.

### 5.3 What evidence would separate convention from a genuine capability gap

None of this has been measured; it is specified so it is mechanical to run, and it is deliberately
*not* run here, because a new un-gated figure in a docs page is exactly what R1 exists to stop.

```
DISCRIMINATOR, per corpus, on the short-form label only

  partition every gold short-form span the system does not recall into:
    (a) NEVER DEFINED       -- its surface has no gold long form anywhere in the
                               document. The genuine capability gap; this is the
                               population W11 exists for.
    (b) DEFINED, MISSED     -- the document defines it and the extractor failed to
                               find the definition. NOT a W11 case: it is a rule
                               bug, and fixing it pays on both labels at once.
    (c) DEFINED, FOUND ONCE -- the document defines it, the extractor found the
                               definition, and this is a later occurrence.
                               Annotation convention. Reachable by propagating a
                               pair already emitted, which needs no new emission
                               model at all.

  W11 IS JUSTIFIED IN PROPORTION TO (a) AND NOTHING ELSE.
  If (c) dominates, the correct product is occurrence propagation inside the
  existing pair model -- cheaper, no wire change, and it reuses a definition the
  library already found.
  If (b) dominates, the correct product is better long-form rules.

  RUN IT FIRST on sdu22_ae_legal_dev and sdu22_ae_scientific_dev, which are
  already contaminated and cost nothing further. PLOD only after the SDU-22
  answer is known, and only if the answer justifies spending PLOD's blindness.
```

**The `18` in §5.2 hints at (c) and cannot settle it**, for the reason recorded there. If the SDU-22
partition does return (c)-dominant on both domains, **W11 should be closed with a record and the
occurrence-propagation feature scoped in its place** — a strictly smaller change that needs no
wire-contract decision at all.

---

## 6. How W11 fails, and the stop rule

**It repeats D-044.** Ships a mechanism, gets a status line reading "met in mechanism, not met in
value", and the trivial baseline it loses to is already in the results file with a better F1 on a
held-out corpus. This is the most likely outcome and §1.2 is the reason.

**The discriminator comes back (c)-dominant** and the whole workstream turns out to be a corpus
convention read as a product gap — §5.2 hints that way on one split without being able to show it.

**Short-form precision is the dominant risk and there is nowhere clean to measure it.** One
uncontaminated span corpus, whose blindness the diagnostic phase spends; no uncontaminated extraction
corpus at all.

**The reframing is over-read.** "The recall ceiling is really a product decision" is true for the
SDU-22 ceiling formula and is *not* the PLOD one (§1.1). A reader who takes the sentence without the
formula will quote a ceiling this project has never published.

**It is built pairs-only anyway**, because W10 is further along and the occurrence pass looks like
scope creep — and then §4.2 happens quietly.

### The stop rule, written before the work starts

```
W11 PROCEEDS ONLY IF, on the two contaminated SDU-22 dev splits:
  1. the discriminator of §5.3 returns partition (a) as a material share of the
     unrecalled short-form spans -- not (b), not (c); and
  2. a candidate unpaired rule beats the ported all-caps control on short-form
     precision at equal or better short-form recall, in the same table, both
     conventions printed.

W11 STOPS, WITH A D-RECORD, IF:
  * (c) dominates            -> scope occurrence propagation instead
  * (b) dominates            -> scope long-form rules instead
  * the rule cannot beat all-caps on precision -> there is no product here, and
    the honest deliverable is the negative result plus the ported control, which
    is worth having on its own because SDU-22 currently has no floor at all.

NOTHING IN W11 SPENDS sdu21_ai OR SDU-22 train.json. If a proposal needs either,
it needs its own record first (D-043 for the former, R3 for the latter).
```

---

## 7. What W11 is not

Named because each is on the prohibited list or already closed, and each is one bad paraphrase away
from W11.

* **Not a long-form precision filter.** D-041 closes every rule of that shape in advance. W11 is the
  escape D-041 explicitly leaves open — re-emitting the short form unpaired — and it is only outside
  the constraint if the short form genuinely survives without the long form.
* **Not the per-candidate-evidence lever**, not a strategy cascade, and not a relaxation of the digit
  rules in the short form. W11 changes what is *emitted*, not what is *scored* or *selected*.
* **Not a recall lever dressed as a product decision.** If it is adopted, short-form recall figures
  before and after are not comparable, and every table must say which emission model produced them.
* **Not a reason to re-open the abstention default.** D-043's reservation on SDU-21 AD `test.json` is
  about the disambiguator. W11 has no bearing on it and must not be used to argue its trigger has
  fired.

**Checked for a prior closure before writing this, per R9.** `docs/DECISIONS.md`,
`docs/AUDIT-2026-08.md` and `docs/EVALUATION.md` were grepped for the mechanism — unpaired emission,
short-form-only output, emitting a short form without a long form. The only hits are the two
paragraphs of D-041 that pose the question and name the escape it leaves open. **This mechanism has
not been tried and refused; it has been named and deferred.** That is recorded here so the next
reader does not have to re-run the grep.

---

## 8. Deliverables, in order, with the gate each must pass

```
1. Port the all-caps control to character spans for SDU-22 AE.
   gate: a runner writes it with --save; both labels, both conventions; the
   ceiling in the same table (R9.6).
   value even if W11 dies: SDU-22 short-form numbers get a floor.

2. Run the §5.3 discriminator on both SDU-22 dev splits, per surface, not per
   sample (§5.2).
   gate: gated through a runner; (a)/(b)/(c) reported separately and never
   pooled (R5); decomposed by split and labelled as annotation density rather
   than domain (§3.3).
   THIS IS THE DECISION POINT. Section 6's stop rule applies here.

3. Only if 2 passes: write the API design for option B + D.
   gate: R8 -- a design, not a patch. It must state the extra="forbid"
   consequence, what as_mapping() and from_pairs do, and the default (off).

4. Only if 3 lands: measure the unpaired rule against deliverable 1's control.
   gate: R6, one change one measurement; the losing comparison beside the
   headline; PLOD scored but NOT diagnosed until a record says the blindness is
   worth spending.
```

**Nothing above changes behaviour, and this note changes none.** The first three deliverables are a
benchmark control, a measurement and a document. The earliest point at which any code in
`src/acronymkit/` moves is deliverable four, and by then the decision to move it has a number behind
it or the workstream is closed.
