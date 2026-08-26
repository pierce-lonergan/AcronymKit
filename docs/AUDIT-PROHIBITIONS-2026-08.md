# The do-not list, re-derived: an error rate for the claims that close directions

D-068 measured this project's reporting error rate for the first time. `20.8` % of a seeded sample of
incidental claims were not true. This page turns that instrument backwards onto the prohibitions.

**RETIRED IN PLACE, AND IT IS THE CLAUSE THAT CHOSE THIS PAGE'S FRAME.** The paragraph above used to
end *"and the subset that needed **a derivation** rather than a lookup failed at `36.4` %"*. D-082
re-took that decomposition on a second round and it did **not** replicate: the same split measured
`25.0` % against `18.8` %, so the ratio went from `4.7x` to `0.75x` and inverted, and a sensitivity
check on the grader's boundary did not rescue it. **The headline rate stands; the decomposition does
not.** `36.4` % is not a baseline anything may be compared against, which is why the comparator column
in [section 3](#3-the-rate) is struck as well. Nothing this page measured on its own population
changes — the retirement is of a comparator, not of a finding. The census behind it, and what a third
round would need to establish the decomposition, are in
[docs/CLAIMS-LEDGER.md](CLAIMS-LEDGER.md) section 6.

**The reason to do that is not symmetry.** A live claim is read by somebody. A prohibition is read by
nobody, because the direction it closes is closed, and the whole point of closing a direction is that
work stops flowing to it. So a wrong reason survives longer inside a do-not list than anywhere else in
the tree — and **a wrongly-closed direction costs more than an open one**, because an open one has
somebody looking at it.

Three audit premises have already been refuted this way (`docs/AUDIT-2026-08.md` section 0). This is
the first pass that states a denominator before looking.

**The headline, and it is one number.** Across the audit's do-not list — a **census**, not a sample —
`13` of `35` figures are either **not true of this tree today** or **cannot be re-derived at all**.
That is `37.1` %. Split by kind of check, the figures settled by one lookup fail at `3.2` % and the
figures requiring a derivation fail or vanish at `52.0` %.

**Nothing reopens.** Not one prohibition's *conclusion* falls. Nine *stated reasons* need correcting,
and two prohibitions came out **stronger** than they were written. That distinction — lift the
prohibition, or fix the reason while the prohibition stands — is the whole result, and conflating it
would be the worst error available here, so it is [given its own
section](#6-what-should-be-lifted-and-what-merely-needs-its-reason-corrected).

---

## 1. The population, before the sample

**An audit whose denominator is unstated is a spot-check.** So the enumeration is mechanical, its
rules are published, and both hand edits to it are published beside them. The tool is
`tools/prohibitions.py`; `tests/test_prohibitions.py` pins the extraction rules and shows `--check`
going red.

```
python tools/prohibitions.py --list   # command output, not a benchmark measurement.
                                      # docs/AUDIT-2026-08.md and docs/DECISIONS.md unmodified
                                      # at 61cf9332a43c10b08c2e9302f177c9f201bf61dc throughout.
                                      # CPython 3.13.4 on win32. The four summary lines,
                                      # verbatim; the 55 per-prohibition rows between them elided.

  stratum A: 13 prohibition(s)
  stratum B: 35 prohibition(s)
  stratum C: 7 prohibition(s)  (census, never sampled)
  population: 55 prohibitions across 3 strata
```

| stratum | what is in it | rule | prohibitions | figures in frame |
|---|---|---|---:|---:|
| **A** | the audit's do-not items | the bold lead `**Do not `, plus every row of *Five proposals that should not be built*, plus every bold-lead paragraph under *D. What should stay closed* | `13` | `35` |
| **B** | closed-direction decision records, **evidence text only** — title, status block, fenced blocks | a closure word in the title or in the status block's first segment | `35` | `564` |
| **P** | the same `35` records, **prose only** — the exact complement of B | as above | `35` | `738` |
| **C** | the live instructions: Mandate II Phase IV's *PROHIBITED* list and `docs/POSITIONING.md`'s retirements | enumerated by hand, in full | `7` | not numeric |

**What a figure is.** Inside a span, every free-standing number: one whose neighbouring characters are
not alphanumeric and not `-_./`. That drops `D-012`, `MED1250`, `2026-08-23` and `0.3.0` — identifiers
and dates — and keeps numbers inside code spans and fenced blocks, because in this repository that is
where measurements are written. The rule has a **known gap and it is pinned in a test rather than
patched after the draw**: `@` and `+` are not excluded neighbours, so `R@25` and `U+2081` are admitted
as figures. One `U+2081` reached the sample and is graded like anything else.

**The two hand edits to stratum B, published because a denominator trimmed by taste is the failure
this page measures.** Six records were added whose closure is worded in a way the marker list misses
(`D-001`, `D-005`, `D-006`, `D-007`, `D-056`, `D-063`). Two were removed — `D-024` and `D-042` — and
only because each says in its own status that it is **open**; a record that merely reads like a fix
kept its place. Both lists are `MANUAL_STRATUM_B` and `MANUAL_STRATUM_B_EXCLUSIONS` in the tool.

**Stratum B is over-inclusive and this page does not pretend otherwise.** Matching a closure word in a
*title* pulls in records such as `D-046` (the phrase is "revert criterion") and `D-052` ("declining to
look"), which are rules and fixes rather than closures. Over-inclusion dilutes toward general claims,
which is the conservative direction, and it is visible in the published list.

---

## 2. The sample

Stratum A is a **census**: `35` figures is few enough to check every one, and a census has no sampling
error to argue about. Strata B and P are seeded draws. Stratum C is a census of `7` prohibitions
rather than of figures, because its members are instructions and not measurements.

```
python tools/prohibitions.py --sample                                   # command output
python tools/prohibitions.py --sample --stratum-b-span=prose --draw-a 0 --draw-b 8

  seed 20260825; allocation A=35, B=13
  stratum A: 35 of  35 (100.0 % sampling fraction)
  stratum B: 13 of 564 (  2.3 % sampling fraction)
  stratum P:  8 of 738 (  1.1 % sampling fraction)
```

The method is `random.Random(f"{seed}:{stratum}").sample` over the frame sorted by claim id. The seed
`20260825` is the date, in the same form D-068 used. `n = 13` in stratum B because one failure there
moves that stratum `7.7` points; the `48`-item main pass moves `2.1` points per failure, against
D-068's `24` items.

**Stratum P was drawn after stratum B came back clean, and saying so is the point.** The stratum B
span rule selects the *most* checkable text in a record — the fenced blocks, which by house style
carry `bench/results.json, <run id>` above them. A clean result there says nothing about the prose
around it. So an eight-item prose probe was drawn from the complement of the same records, with the
ordering disclosed here rather than presented as if it had been planned.

Every verdict below was re-derived **from source** — the command run, the file read, the statistic
recomputed — never from the record that states it. Where the original derivation could not be
reproduced, the verdict is `UNREPRODUCIBLE`, which **is not** `TRUE`.

---

## 3. The rate

```
56 claims checked -- stratum A census (35) + stratum B sample (13) + stratum P probe (8)

  TRUE                42
  FALSE                5      8.9 %
  UNREPRODUCIBLE       9     16.1 %
  not true OR unreproducible  14     25.0 %
```

**Read the pooled row as a convenience and not as a population estimate.** The three strata were
sampled at `100.0` %, `2.3` % and `1.1` %, so pooling them weights the audit's do-not list far above
its share of the population on purpose. The per-stratum rows are the ones that mean something.

| stratum | n | TRUE | FALSE | UNREPRODUCIBLE | not true | not true or unreproducible |
|---|---:|---:|---:|---:|---:|---:|
| **A** — the audit's do-not list (census) | `35` | `22` | `5` | `8` | `14.3` % | **`37.1` %** |
| **B** — closed records, fenced evidence | `13` | `13` | `0` | `0` | `0.0` % | `0.0` % |
| **P** — closed records, prose | `8` | `7` | `0` | `1` | `0.0` % | `12.5` % |

### The kind-of-check split, on this page's own population

**By kind of check.** This is the finding.

| kind | n | not true | unreproducible | either |
|---|---:|---:|---:|---:|
| settled by one lookup | `31` | `1` — `3.2` % | `0` | `3.2` % |
| needing a derivation | `25` | `4` — `16.0` % | `9` — `36.0` % | **`52.0` %** |

**THE `D-068's rate` COLUMN IS STRUCK, AND THE HEADING ABOVE IT WITH IT.** The column carried `7.7` %
and `36.4` %, and the sentence under this table opened *"The single-lookup rate reproduces D-068's
within noise. The derivation-requiring rate does **not**"*. That comparison is withdrawn: D-082
re-took D-068's decomposition and it did not replicate, `25.0` % against `18.8` %, the ratio inverting
from `4.7x` to `0.75x`. Both compared cells moved, and D-082 records that the first round's boundary
between a lookup and a derivation was never written down — so the comparison was never known to be
between the same two cells.

**The rows above stand, and they are not a third round of R15.** This is a census of the do-not list
rather than a seeded sample of a round's incidental reporting, on a different population, graded on a
three-valued scale R15's two rounds never used. Reading them as a third observation of the same ratio
is the error the struck column invited. What they do say, unchanged: D-068 recorded `0` of `24`
unchecked items, and this pass records `9` of `25` derivation-requiring figures that cannot be
re-derived at all. **That gap is structural rather than accidental, and it is
the most useful thing on this page.** A prohibition is very often justified by a measurement taken
against a resource the project then deliberately did not acquire — the PMC Open Access collection,
`SecureFinAI-Lab/Regulations_abbreviation`, Ab3P's `31` MB `SingTermFreq.dat`. The refusal to acquire
the resource is the *result*; it is also what makes the number backing it permanently uncheckable by
anybody standing in this checkout. **A figure about a thing you decided not to obtain is a figure
nobody can re-derive.**

**By failure mode.** Of the `5` FALSE verdicts, `4` are **staleness** — true when written, not true of
this tree now — and `1` is a **hard error** in arithmetic, wrong on the day it was published.
Excluding staleness the not-true rate over the whole pass is `1` of `56`, `1.8` %; counting it,
`8.9` % stands, and this page counts it, because a prohibition is read in the present tense by whoever
is deciding not to do something.

**A second comparator is struck here.** The sentence read *"D-068 found `3` of `5` staleness"*. That
is the other decomposition D-082 re-took, and it did not replicate either: the second round found
staleness in `1` of `5`, with the dominant failure mode a premise asserted as fact and never
measured.

---

## 4. Every verdict

Stratum A is complete — this is the census, not a selection from it. `run id` means the figure resolves
in `bench/results.json`; `re-derived` means a command was run or a file parsed.

### Stratum A — the audit's do-not list, all `35` figures

| id | figure | claim | check | verdict |
|---|---|---|---|---|
| A01.001 | `1` | the *do not* list is at the end of question `1` | read | TRUE |
| A02.001 | `80` | mirroring PMC is `80` GB | external, no source, no date | UNREPRODUCIBLE |
| A02.002 | `4.72` | measured sense coverage of the target inventory | PMC sample absent | UNREPRODUCIBLE |
| A03.001 | `1.124` | `Regulations_abbreviation` covers `1.124` % of real token occurrences | no corpus, no command, no date, one occurrence in the tree | UNREPRODUCIBLE |
| A04.001 | `1` | auditor `1`'s bracket fix breaks `[db].[schema].[TXN_ID]` | re-derived | TRUE |
| A07.001 | `131` | `greedy_wrong` | run id | TRUE |
| A07.002 | `44` | `wrong_gold_not_a_start_boundary` | run id | TRUE |
| A07.003 | `65` | `wrong_gold_explained_by_no_strategy` | run id | TRUE |
| A07.004 | `5` | `already_unique_under_per_rule_score` | run id | TRUE |
| A07.005 | `22` | `addressable_by_per_candidate_score` | run id | TRUE |
| A07.006 | `1,221` | `gold_pairs` | run id | TRUE |
| A07.007 | `85.44` | `oracle_selector_exact_f1` | run id | TRUE |
| A07.008 | `83.85` | "against a baseline of `83.85`" | run id — but the shipped baseline is now `84.21` | TRUE, comparator superseded |
| A07.009 | `2,474,596` | `SingTermFreq.dat` unigram rows | file absent (`31` MB, never vendored) | UNREPRODUCIBLE |
| A07.010 | `94,718` | the word set it compiles to | same file | UNREPRODUCIBLE |
| A07.011 | `88.49` | D-011's headroom figure, to be retired | read — D-011 still states it twice | TRUE, disposition not executed |
| A08.001 | `83.85` | `relaxation.med1250_all.baseline` | run id | TRUE |
| A08.002 | `82.22` | `drop_all_digits` | run id | TRUE |
| A08.003 | `83.34` | `drop_trailing_digits` | run id | TRUE |
| A09.001 | `0.00` | `register` varies in `0.00` % of instances | re-derived from `diction.json` | TRUE |
| A10.001 | `37.2` | governed is `37.2` % of source | re-derived at the audit's own commit: `37.17` %. Today `36.32` % | FALSE — stale |
| A10.002 | `42` | `42` governed public symbols | re-derived: `governed.__all__` is `42`, then and now | TRUE |
| A10.003 | `87` | of `87` public symbols | seven readings tried at the audit's commit; none is `87` | UNREPRODUCIBLE |
| A10.004 | `7` | `7` governed CLI commands | re-derived by classifying every command | TRUE |
| A10.005 | `16` | of `16` CLI commands | re-derived: `16`, then and now | TRUE |
| A11.001 | `404` | the pinned PMC path is already `404` | verified live `2026-08-25` | TRUE |
| A11.002 | `4.72` | as A02.002 | as A02.002 | UNREPRODUCIBLE |
| A11.003 | `565,730` | the wheel measures `565,730` B | rebuilt at the audit's commit: `564,515` B. At HEAD: `596,222` B | FALSE — stale |
| A11.004 | `786,432` | `ci.yml` `BUDGET_BYTES` | read — current | TRUE |
| A11.005 | `220,702` | headroom | exact against its own inputs; today `190,210` B | FALSE — stale |
| A11.006 | `113,269` | «D-020 says "Headroom today is `113,269` bytes"» | read — D-020 was corrected and now says the opposite | FALSE — stale, fix landed |
| A11.007 | `455` | `455` MB "clears either figure by four orders of magnitude" | recomputed: every pairing is `10^2.76` to `10^3.72` | **FALSE — hard error** |
| A11.008 | `5.27` | `5.27` M CC BY / CC0 full texts | external, no source, no date | UNREPRODUCIBLE |
| A12.001 | `30` | `30` parameterised rules | re-derived: `len(STRATEGIES)` is `30` | TRUE |
| A12.002 | `1.0` | the cascade confirms the `OMB` truncation at confidence `1.0` | re-derived through the shipped cascade | TRUE |

### Stratum B — closed records, fenced evidence, `13` of `564`

| id | figure | check | verdict |
|---|---|---|---|
| D-016.005 | `3` | re-derived: term statistics built from the MED1250 dev half | TRUE |
| D-020.006 | `867` | re-derived from the corpus | TRUE |
| D-026.006 | `38.60` | `governed.is_compliant.median` | TRUE |
| D-030.011 | `0.05` | `disambiguation.sdu21.abstention_curve`, all four columns | TRUE |
| D-030.064 | `10` | `by_arity` at the reference gate, all six rows | TRUE |
| D-032.001 | `43` | `shortform.plod_all.corpus` | TRUE |
| D-043.002 | `1,804` | `shortform.plod_all.legend_exposure` | TRUE |
| D-045.027 | `97.78` | `…scientific_dev.general.legend_cost` | TRUE |
| D-045.053 | `98.25` | `shortform.med1250_all.legend_firing` | TRUE |
| D-045.055 | `5` | same run | TRUE |
| D-062.001 | `3.9` | the evidence command runs; the pinned mypy accepts `--python-version 3.9` | TRUE |
| D-064.001 | `28` | counted: exactly `28` run ids under that prefix | TRUE |
| D-064.005 | `0.53` | `…legal_train.high_precision.legend_cost`; the whole table reproduces | TRUE |

### Stratum P — closed records, prose, `8` of `738`

| id | figure | check | verdict |
|---|---|---|---|
| D-007.003 | `14.2` | re-derived through the shipped engine: margin `14.1458` | TRUE |
| D-015.018 | `40.98` | `disambiguation.sdu21.random.macro_f1`; the whole row reproduces | TRUE |
| D-016.041 | `615` | re-derived: `reachability(test)` returns `(615, 525, 488, 477)` | TRUE |
| D-023.001 | `11` | host is Windows `11` Pro `26200`, CPython `3.13.4`, pydantic `2.11.7` | TRUE |
| D-023.029 | `2.65` | `67.50 / 25.50` = `2.647`; exact against its own quoted inputs | TRUE |
| D-023.041 | `236.70` | `model_construct` appears nowhere in `src`, `bench`, `tools` or `tests`; no run id | UNREPRODUCIBLE |
| D-052.002 | `2081` | `U+2081` is SUBSCRIPT ONE; `_KEYWORDS` holds the ASCII `f1` | TRUE |
| D-070.009 | `93.55` | `monoculture.plod_all.proposals.edges_sh_only.share_pct_acronymkit/biomedical` | TRUE |

---

## 5. The four re-derivations worth showing

Everything above is a verdict; these four are the arithmetic, because a verdict a reader cannot
re-run is the thing this page exists to complain about.

### A11.007 — "four orders of magnitude" is three, in every reading

The only **hard error** in the pass. The claim appears twice: in the *Five proposals* table row
("the table is four orders of magnitude over the wheel budget") and in the PMC prose.

```
python, arithmetic only -- every pairing the sentence could have meant
                                          ratio      log10
  455 MB vs headroom       220,702 B      2,061.6     3.31
  455 MB vs BUDGET_BYTES   786,432 B        578.6     2.76
  455 MB vs the stale      113,269 B      4,017.0     3.60
  600 MB vs headroom       220,702 B      2,718.6     3.43
  600 MB vs BUDGET_BYTES   786,432 B        762.9     2.88
  600 MB vs the stale      113,269 B      5,297.1     3.72
```

No pairing reaches `10^4`. The most generous reachable figure is `10^3.72`. **The prohibition is
completely unaffected** — three orders of magnitude is as decisive as four — which is exactly why
nobody caught it.

### A11.003 / A11.005 — the wheel figure drifted, and D-020 carries the drift

The audit's wheel figures were re-derived by building the wheel twice: once from the audit's own
commit and once from HEAD.

```
python -m build --wheel --no-isolation   -- twice, on one host, CPython 3.13.4 on win32
                             wheel B     headroom B    % of budget
  audit, 2026-08-23          565,730       220,702        71.94
  rebuilt at 6a3e000         564,515       221,917        71.78
  rebuilt at HEAD            596,222       190,210        75.81
```

At the audit's own commit the rebuild lands `1,215` B — `0.21` % — under the published figure, which
is build-environment noise rather than an error: a wheel is a zip and its size moves with the
packaging toolchain. At HEAD the wheel has grown `30,492` B and headroom has fallen to `190,210` B.

**The part that matters is not in the audit at all.** `docs/DECISIONS.md` D-020 item 1 — the *binding
constraint* keeping the frequency-prior direction closed — now states `220,702` and `565,730` as
current. They are not. That record carries a footnote about this precise failure mode, describing how
"Headroom today is `113,269` bytes" went stale under a replaced budget and was re-quoted by two
independent auditors. **It has recurred inside the record that documents it.** The conclusion is
untouched: `455` MB clears `190,210` B by three orders of magnitude.

### A10.003 — `42` reproduces, `87` does not

`42` is exact: `acronymkit.governed.__all__` holds `42` names at the audit's commit and at HEAD. The
denominator `87` has no stated derivation, and seven readings at the audit's own commit produce none:

```
python, at git archive 6a3e000 -- "public symbols", every reading tried
  dir(acronymkit) | dir(acronymkit.governed), public                 113
  sum of every __all__ in the package                                269
  len(acronymkit.__all__) + len(governed.__all__)                     90
  the same, union with acronymkit.nlp.__all__                         89
  public non-module attributes of both, union                         86
  acronymkit.__all__ union governed.__all__                           83
  dir(acronymkit), public                                             70
```

**The ratio's force survives every one of them**: `42/83`, `42/86` and `42/90` are all "about half".
The prohibition — do not split the package into two distributions yet — does not depend on the
denominator, and its real reason is stated in the same sentence and is not numeric: nobody knows which
audience is showing up.

### A09.001 — the strongest derivation in the sample, and it holds exactly

`register` varying in `0.00` % of instances is one of the load-bearing figures named in this phase's
brief. It re-derives from the shipped corpus file:

```
python, data/sdu21_ad_diction.json -- the file the claim names
  acronyms                                                    732
  expansions                                                2,308
  expansions differing from their own lowercase                 0
  acronyms whose candidate set carries more than one register   0   of 732
```

The stated *mechanism* — "because every expansion in `diction.json` is lower-cased" — is exactly right,
and the same read independently confirms the `732`-acronym inventory the PMC section cites.

---

## 6. What should be lifted, and what merely needs its reason corrected

**These are different outcomes and this section keeps them apart.**

### Lift: nothing

No sampled figure overturns any prohibition's conclusion. Where a figure fell, the conclusion it
supports was reached with margin to spare, twice by three orders of magnitude. **A reader looking for a
reopening in this pass will not find one, and that is the result rather than a disappointment.**

Two prohibitions came out **stronger** than they were written:

- **A07** — do not take the per-candidate-evidence lever. The audit compared a perfect selector's
  `85.44` against a `83.85` baseline: `1.59` points. `balanced_trim` shipped since, the baseline is
  `84.21`, and the whole prize is now `1.23` points.
- **A11** — do not mirror PMC. The audit recorded the deprecated mirror as up. Re-checked live on
  `2026-08-25`, `ftp.ncbi.nlm.nih.gov/pub/pmc/deprecated/oa_bulk/oa_comm/txt/` returns `404`, as does
  `/pub/pmc/deprecated/`, while `/pub/pmc/` returns `200`. The route the audit priced no longer exists
  at that host.

### Correct the reason; the prohibition stands

Nine, in the order a reader should take them. **None of these is a change this pass is authorised to
make** — the records and the mandate text belong to the recorder and the maintainer.

1. **"Four orders of magnitude" is three.** Two occurrences, `docs/AUDIT-2026-08.md` lines `133` and
   `543`. Pure arithmetic, wrong on the day it was written.
2. **D-020 item 1's binding constraint is stale.** `220,702` B of headroom against a `565,730` B wheel
   is now `190,210` B against `596,222` B. The record's own footnote is about this exact recurrence.
3. **The audit's claim that D-020 says `113,269`** is no longer true; that fix landed. The audit line
   describing a live defect describes a closed one.
4. **`87` public symbols has no reproducible derivation.** State the definition or state the ratio
   without a denominator.
5. **`1.124` % is the weakest-evidenced figure on the do-not list.** No corpus named, no command, no
   date, one occurrence in the whole tree, and it is the entire quantitative case for refusing to
   vendor a governed catalogue. R4 is not satisfied by it.
6. **`2,474,596` rows and `94,718` words cannot be re-derived here**, and the derivation as coded —
   `bench/run_shortform.py::_load_word_data` — accumulates into a `dict` keyed by word, so its printed
   figure is **distinct keys**, which the audit reports as **rows**. Those are the same number only if
   the file has no duplicate keys, which nothing in the tree checks.
7. **`4.72` %, `80` GB, `455` MB and `5.27` M are external figures with no source and no read-date.**
   `4.72` % does survive one independent consistency check: it is the only integer numerator over the
   `2,308`-sense denominator re-derived above that rounds to it, `109/2308` = `4.7227`.
8. **The audit's instruction to retire D-011's `88.49`** was never carried out. D-011 still tells every
   future selection experiment to report against `88.49`, and the audit's reason for retiring it —
   that it counts spans no matching rule can produce — reproduces in
   `analysis.med1250.selection_ceiling`: `65` of the `131` wrong answers have a start boundary and no
   strategy that can reach them.
9. **A07.008's comparator `83.85` is superseded** by the shipped `84.21`. True about the run, stale as
   a statement about the library.

**Applied `2026-08-25`. Ten of them landed, not nine, and one of the nine did not.** The eight of
these that live in `docs/AUDIT-2026-08.md` are corrected in place there, beside the sentences they
retire; `2` — D-020 item `1` — is in a decision record and was reported to its owner instead; and two
further corrections were added, because this list left two of this page's own `FALSE` verdicts with
no correction pointing at the document that carries them. Section `12` is the account, including
three things this page got wrong about its own corrections.

---

## 7. Stratum C — the live prohibitions, a census of `7`

These are instructions rather than figures, so each was checked against the thing it constrains.

| # | prohibition | premise re-derived | verdict |
|---|---|---|---|
| C1 | no more Schwartz & Hearst descendants in any proposer pool | `monoculture.plod_all.proposals.edges_sh_only` gives one implementation `93.55` % of the family's proposals | stands |
| C2 | no re-funding Federal Register legend extraction | the FR set is `role = "single_annotator_reference"`, `contaminated = true`, `task = "extraction"`; `headline_capable("extraction")` returns `[]` | stands |
| C3 | no registering the FR set under `held_out` or `tuning` | `bench/splits.toml` line `187`; and the never-headline filter's firing count reproduces exactly — `16` evaluations, `0` returns of `False` | stands |
| C4 | no re-recording `micro.import` against a foreign environment | `micro.import` exists with `3` timings and `iterations` `9`; the **only** environment stamp is the file-level one | stands, **unenforced** |
| C5 | no growing `EXPECTED_NON_PASSING` | `6` node-keyed entries, `0` file-keyed, matching `ci.yml`'s own comment | stands, **enforced by the job itself** |
| C6 | the three retired breadth sentences do not return | `pyproject.toml`'s description is rewritten; `README.md` and `docs/ARCHITECTURE.md` quote them only as retired; `src/acronymkit/__init__.py` lines `1` and `3` still carry two of them | stands, disclosed exception confirmed |
| C7 | nobody optimises the MED1250 extraction figure again | `extraction.med1250.acronymkit.exact_f1` is `84.21`, still third behind `88.87` and `84.44` | stands, **unenforced** |

**Two of the seven have no mechanism.** C4 is unenforceable by inspection: nothing in
`bench/results.json` records which machine any individual run used, so a foreign re-record of
`micro.import` would leave no trace. C7 is the one `docs/POSITIONING.md` already admits has no
mechanism — "nothing turns red if a later round tunes the extractor" — and that reproduces: no gate in
the seven would redden. C5 is the counter-example that shows the shape a mechanism takes.

---

## 8. Three prohibitions the frame cannot see, and one checked anyway

`A05`, `A06` and `A13` contribute **zero** figures to the frame, because their reasons contain no
free-standing numbers. Spelled-out quantities escape too: `A01`'s "closed three times over" and
`A13`'s "closed at four independent points" are both checkable and both invisible to the rule.

`A13` was checked by hand, because a prohibition with no numeric evidence at all is the case the
sampler is worst at:

```
PYTHONPATH=src python -- "Adding a language", all four stated closure points
  1  class L2(Language): IT = "it"    -> TypeError: cannot extend <enum 'Language'>
  2  Config(language="it")            -> ConfigurationError: expected 'en', 'fr', 'es' or 'de'
  3  Language.from_tag("it")          -> ValueError: 'it' is not a valid Language
  4  available_languages              -> {'lexicon': ['en'], 'ngram': ['en']}
```

All four reproduce, and the record's further claim that `fr`, `es` and `de` are themselves only
half-supported reproduces with them. **`A13` is the best-evidenced prohibition in stratum A and the
frame scored it zero**, which is a fact about the instrument rather than about the prohibition.

---

## 9. The auditor's own error rate

R15 says the sampler's verdicts are claims too, and D-068 closed by noting that the error rate of the
error-rate measurement is unmeasured. This pass cannot measure its own either. What it can do is
report the near-misses it caught, because all three were within one command of being published as
refutations.

- **`OMB` at confidence `1.0`.** Fed `"OMB"` and mixed-case words to a matcher whose docstring says
  *case-folded*, got `0` of `30` strategies matching, and had a written refutation of A12.002 before
  re-reading the signature. Case-folded, the alignment is found at confidence `1.0` and the claim is
  **TRUE**.
- **MED1250's `615` gold pairs.** Counted raw pairs and got `629` against D-016's `615`. The record's
  own function deduplicates to `(short form, normalised long form)` keys per document; on that
  definition all four ceilings reproduce as `615, 525, 488, 477`.
- **The never-headline firing count.** Monkey-patched `may_back_a_headline` as a method when it is a
  **property**, measured `0` evaluations, and nearly reported D-063's firing count as broken. Patched
  as a property it is `16` evaluations and `0` returns of `False`, exactly as recorded.

**Three attempted refutations, three of them mine.** Every one failed the same way — the harness was
misconfigured relative to the thing being tested, and the first result agreed with the hypothesis. That
is the shape the mandate warns about, arriving from inside the audit rather than from outside it.

---

## 10. How this fails

**Stratum B's `0` of `13` is a result about fenced blocks, not about closed records.** The span rule
was chosen before the draw and it selects exactly the text this project writes under a run id. A
reader who concludes "the decision records are sound" is over-reading; the honest statement is that
**the fenced evidence in closed records is essentially perfectly citable, and `13` consecutive
successes is what that looks like**. The prose probe was added for this reason and it is `8` items,
which is too few to separate `0` % from `10` %.

**The stratum A census is `35` figures and `10` prohibitions, so it is not `35` independent
observations.** `A07` alone contributes `11` and `A11` contributes `8`. Both fell in clusters — three
of the five FALSE verdicts are `A11`'s wheel arithmetic, which is one number restated three ways. On a
per-prohibition reading the failure count is `2` prohibitions of `13`, not `5` figures of `35`, and
both readings are published because neither dominates.

**The `UNREPRODUCIBLE` verdict is doing a lot of work and it is partly a statement about this
environment.** Four of the nine could in principle be re-derived by fetching an external resource —
Ab3P's `31` MB `SingTermFreq.dat`, the Hugging Face dataset, a PMC sample. This pass did not fetch
them: downloading a file is not an action it is authorised to take, and the network checks it did make
were status reads that transfer no file. A better-resourced reader would convert some of those nine
into TRUE or FALSE, and **that is exactly the work item this page is pointing at**.

**The frame is a rule and the rule has a taste.** Stratum B reads fenced blocks and not prose; that
narrows the denominator, and it was a judgement made before the draw rather than after it. The
number rule admits `R@25` and `U+2081`. The stratum B closure markers over-include fixes and rules.
Each of these is published, none was adjusted after seeing a verdict, and a reader who disagrees can
re-run with `--stratum-b-span=all` and get a different denominator honestly.

**The tree moved while this ran, again, and for a while it moved the gates.** At the start of this
pass `git status` was clean and all seven gates were green at
`61cf9332a43c10b08c2e9302f177c9f201bf61dc`. During it, concurrent workstreams modified `21` tracked
files and added `12` untracked ones beside this pass's `3`. **Four separate red gate states were observed and
none of them was this pass's**: `bench/run_genre.py` reddened `ruff check`, `ruff format` and `mypy`
in turn, and `tests/test_genre.py` failed five ways — all owned by the workstream that added them,
all resolved by that workstream before this pass finished. The final state is seven of seven green,
and the three files this pass owns were clean under every gate at every intermediate state, checked
alone.

`docs/AUDIT-2026-08.md` and `docs/DECISIONS.md` — the two documents the frame is built from — were
untouched throughout, so the denominator is stable. Every stored figure quoted above was re-verified
against `bench/results.json` at md5 `3fa19ff1979a5f71eec74b9cb58b24da` after the last concurrent edit
landed: `24` of `24` still resolve.

**A concurrency defect, found by being bitten by it and reported rather than fixed.** Several
full-suite runs failed on artefacts of *other* processes running the suite against this same
checkout. `tests/test_claims_gate_coverage.py` injects a probe line into `README.md` **in place** and
restores it; a second concurrent run sees the injected line and aborts with "a second process is
running it against this checkout right now", and an interrupted run leaves an invented performance
figure on the front page. Separately, a gate-mutation harness left `docs/zz-gate-mutation-probe.md` in
`docs/`, which failed three second-reader tests until its owner cleaned it up. Both are in files this
pass does not own.

**That flakiness produced a false positive inside this audit and it is worth naming.** An A/B run —
the module twice without this document, once with — appeared to show that this document was the cause.
Four consecutive runs with it present then passed three times, and the mechanical check settles it:
`tools/check_claims.py`'s own scanner finds **`0`** claim-shaped numbers in this file under both the
stock and the widened vocabularies, so it cannot move that measurement in either direction. **A two-run
A/B against a tree three other processes are writing is not a controlled experiment**, which is the
same lesson as the three near-misses in section `9`, arriving through a different door.

**And the sample cannot see the prohibitions that were never written down.** Every stratum here is a
population of *recorded* refusals. A direction abandoned without a record — the largest class of
prohibition in any project — has no denominator at all, and nothing in this pass estimates its size.

---

## 11. What the claims gate can see on this page, demonstrated rather than asserted

This document is inside `SCAN_GLOBS` (`docs/*.md`) and absent from both baselines, so it is allowed
**zero** value-matched and **zero** deferred numbers. `--residue` confirms it carries `0` deferred.
R11 says a gate must be shown capable of failing where it runs, so it was:

```
python tools/check_claims.py, five runs -- one mutation applied to this file each time, the
gate run, then the file restored from the bytes read before the first mutation and the md5
re-checked against that read. No md5 is quoted here: a file cannot state its own digest,
and quoting the pre-edit one would be a figure that does not match anything a reader holds.
CPython 3.13.4 on win32; command output.

  rc=0  control, unmutated                                        <file not named>
  rc=1  A  prose line added: "... accuracy reached 99.94 % ..."    file named
  rc=1  B  a citation repointed at run id analysis.med1250.nope.*  file named
  rc=1  C  a cited value edited: 85.44 -> 99.99                    file named
  rc=0  control again                                             <file not named>
```

**Everything numeric on this page is code-spanned or fenced**, which D-052 says is mechanically
indistinguishable from hiding. The convention that separates them is printing the command beside each
block, and that convention is followed here — but it is a convention, not a check, and the tables in
sections `4` and `7` are large enough that a reader is trusting it rather than verifying it.

---

## 12. The corrections, applied — and three things this page got wrong about them

Written `2026-08-25`, one round after section `6`. Every figure below was re-derived from source for
this section rather than carried across from the tables above, and doing that changed three of them.

### What landed, and where

`docs/AUDIT-2026-08.md` now carries a *Corrections to the do-not list* section, a front-matter pointer
to it, and **seven** in-place markers beside the sentences they retire — five blockquotes and two
table-cell notes, counted rather than remembered. **Nothing above those markers was rewritten.** The retired
sentence and its correction are readable side by side, which is the only form in which a correction is
also evidence.

| # | the reason corrected | where it is now marked | outcome |
|---|---|---|---|
| C1 | "four orders of magnitude" is three | the PMC row, and the PMC prose | conclusion untouched |
| C2 | this page's own wheel and headroom figures are stale | beside that block | conclusion untouched |
| C3 | the D-020 quotation describes a defect since fixed | beside it | conclusion untouched |
| C4 | the vendoring coverage figure has no derivation | the vendoring row | conclusion untouched |
| C5 | "rows" is a count of distinct dictionary keys | the per-candidate paragraph | conclusion untouched |
| C6 | four external figures carry no source and no read date | the PMC section | conclusion untouched |
| C7 | the instruction to retire D-011's figure was never executed | the per-candidate paragraph | nothing on that page changes |
| C8 | the comparator is superseded, and the prize is smaller | the per-candidate paragraph | **stronger** |
| C9 | the governed share of source is stale | the split-the-package paragraph | conclusion untouched |
| C10 | the public-symbol denominator has no derivation | the split-the-package paragraph | conclusion untouched |

**Nothing lifted, and nothing was proposed for lifting.** The margin under every corrected figure was
re-checked rather than assumed: the largest live ratio anywhere in the PMC arithmetic is `10^3.50`,
and the whole per-candidate prize is `1.23` points against a shipped `84.21`.

### Two of this page's own `FALSE` verdicts had no correction attached

C9 and C2 are new here. `A10.001` — the governed share of source — was graded `FALSE — stale` in
section `4` and appears in none of the nine. `A11.003` and `A11.005` were graded `FALSE — stale` and
correction `2` points at **D-020's** copy of those figures rather than at the audit's own block, which
is where a reader of the do-not list meets them. Both gaps are the same shape: a verdict was recorded
and the recommendation that should have followed it was not written. **The correction list was
audited against the verdict table for this section, which is a check the list itself did not get.**

### Nothing is proposed for lifting — and the one item a maintainer should still look at

**No prohibition was lifted and none is recommended for lifting**, which is the same line section `6`
took and the same line this pass is authorised to take. Reporting one anyway, because the point of
keeping the two outcomes apart is that the weaker one gets said out loud:

**`A03`, vendoring `SecureFinAI-Lab/Regulations_abbreviation`, now rests on a qualitative claim
alone.** Its quantitative half — `1.124` % of real token occurrences — has no corpus, no command, no
date and one occurrence in the tree, so after C4 the refusal stands entirely on *the matches are
homographs*: `POP`, `CAR`, `CT`, `IT` would make a refuse-to-guess subsystem guess. That reason is
sound and, for this library's positioning, decisive on its own. **It is also unmeasured.** Nobody has
counted how many of that catalogue's entries are homographs against a real schema's vocabulary, and
the figure that was supposed to carry the case cannot be re-derived by anybody here.

**So the recommendation is to measure it, not to lift it.** `A03` is the one item on the do-not list
whose evidence is thin enough that a future round could be tempted to reopen it on the grounds that
the reason was wrong — and that would be the exact confusion this page exists to prevent, because the
reason is not wrong, it is unquantified. The decision is the maintainer's and this pass did not take
it.

### Three things this page got wrong about its own corrections

**One — the `10^3.72` ceiling is superseded, and by this page's own correction `3`.** Section `5`
reports the most generous reachable ratio as `10^3.72`, which is `600` MB against `113,269` B. That
denominator is the figure correction `3` says nobody holds any more. Over the figures a reader holds
today the ceiling is `10^3.50`. The direction of the slip flatters the refutation rather than the
project, which is why it survived.

**Two — `87` has drifted into being true, and this page could not have known it.** `A10.003` is graded
`UNREPRODUCIBLE` on seven readings taken at the audit's own commit, and that verdict is exactly right
at that commit. At HEAD one of the seven now returns the published denominator:

```
python -- "public symbols", this page's own seven readings, re-run at both commits
                                                      6a3e000     HEAD
  dir(acronymkit) | dir(acronymkit.governed), public      113      114
  sum of every __all__ in the package                     269      269
  len(acronymkit.__all__) + len(governed.__all__)          90       91
  the same, union with acronymkit.nlp.__all__              89       89
  public non-module attributes of both, union              86       87   <--
  acronymkit.__all__ union governed.__all__                83       84
  dir(acronymkit), public                                  70       71
```

One public name — `NlpBackend` — was added between the two commits. **A figure with no derivation has
become arithmetically true by drift**, and that is a worse state than staleness: a reader spot-checking
`87` today finds agreement and stops. It is still not a derivation, because under the reading that
returns `87` the governed count is `46` rather than `42`. And one of the seven readings is not a
function of the tree at all — `dir(acronymkit)` returns `70` or `72` at the same commit depending on
which submodules have already been imported, which means this page published a reading whose value
depends on the harness that took it.

**Three — the wheel figure is not a stable quantity, and D-077's contest has a cause.** D-077 records
this page's successor correction contested at `593,682` B against `596,222` B under the same command.
Re-run at HEAD, twice from an identical tree and once from a line-ending-normalised export of the same
commit:

```
python -m build --wheel --no-isolation -- one host, CPython 3.13.4 on win32, build 1.3.0
                                          wheel B    headroom B   % of budget
  HEAD 387f739, CRLF working checkout      596,613      189,819        75.86
  HEAD 387f739, the same tree, again       596,613      189,819        75.86
  HEAD 387f739, LF git-archive export      595,242      191,190        75.69
```

Same tree twice gives the same size and *different* digests, because a zip stores mtimes. The
line-ending difference alone is `1,371` B on a checkout carrying `45,917` CRLF pairs across `67`
tracked files. **A wheel byte count published without naming its checkout is unreproducible by
construction**, and the two contested figures are therefore both correct and neither citable.

**And the population this page measured has moved.** `tools/prohibitions.py --list` now enumerates
`36` closed records and `566` stratum B figures where this page published `35` and `564`, because
records were added to `docs/DECISIONS.md` after the draw. The stratum A census is unchanged — every
marker inserted into the audit carries no free-standing number, deliberately, so that the frame this
page drew from is still the frame a re-run draws. That was a constraint on how the corrections could
be phrased, and phrasing chosen to protect a denominator is worth disclosing.

### Is this class mechanically checkable? Asked mechanically

Section `7` found two of seven live prohibitions with no mechanism. This asks the harder version: is
there a gate for *the reason under a prohibition going stale*, in the way `tools/check_external.py` is
the gate for an uncited appeal to somebody else's figure?

Two checks in this tree have a shape that could apply. `tools/check_claims.py` resolves a figure
against `bench/results.json` by run id. `tools/check_external.py` arms a sentence that appeals to a
published outside figure. Both were run against all `35` figures on the do-not list.

```
a probe over the frame tools/prohibitions.py --frame produces, run against
bench/results.json and tools/check_external.py. DERIVED -- no judgement applied.
The probe is a scratch script and is NOT committed: tools/ was not this pass's
to add to, so this block is re-derivable from its description and not by a
command a reader can type, which is a weaker standing than the blocks above it.

  R1  value-in-results  -- the figure equals a value under a run id named
                           inside its own fenced block                      10 of 35
  R2  external-appeal   -- tools/check_external.py arms the sentence         0 of 35
      neither                                                               25 of 35

  restricted to the 13 figures this page graded not-true or unreproducible:
      routable by R1 or R2                                                   0 of 13     derived
```

The next split is **judged, not derived** — no rule can decide "could a committed script re-derive
this", so it is one reader's classification of the same thirteen and it is labelled rather than
folded into the block above:

```
JUDGED, one reader, the same 13 figures. Not a measurement.
  re-derivable in this checkout by a committed script                        5 of 13
      A10.001, A10.003, A11.003, A11.005, A11.006
  not re-derivable because the resource was deliberately refused             7 of 13
      A02.001, A02.002, A03.001, A07.009, A07.010, A11.002, A11.008
  prose arithmetic with no machine-readable claim in it                      1 of 13
      A11.007
```

**`R2`'s zero is a real negative and not a vacuous one, which R11 says has to be shown rather than
claimed.** `docs/AUDIT-2026-08.md` is inside `tools/check_external.py`'s `SCAN_GLOBS`, so the gate does
run over the do-not list; it simply finds nothing there to arm:

```
python tools/check_external.py -- one mutation applied to the do-not list, the gate run,
the file restored from the bytes read before the mutation and the md5 re-checked.
CPython 3.13.4 on win32; command output.

  rc=0  control, unmutated                                        do-not list not named
  rc=1  one armed appeal injected into section 0                  do-not list named
  rc=0  control again, restored byte-identically                  do-not list not named
```

**The answer is that no gate is available for this class, and the probe says why rather than
asserting it.** The `10` routable figures are `A07`'s and `A08`'s — the two prohibitions that write
their evidence under a run id — and **every one of them was already `TRUE`**. Every figure that failed
was invisible to both checks. `R2` scores zero because `check_external`'s arming vocabulary is built
for *appeals* — "the published figures", "as reported by" — and the do-not list states its external
numbers bare: `80` GB of PMC, `5.27` M full texts. Widening that vocabulary to catch a bare external
number is the prose linter its own module docstring says nobody would leave switched on.

**What is available is not a gate but a convention with a measured effect.** The single property that
separates the surviving figures from the failing ones is being written under a run id — which is
`R4` and operating rule `1` already, applied to a do-not list rather than to a README. Five of the
thirteen failures would additionally be re-derivable here by a committed script, in `R16`'s shape: a
figure ships with the command that regenerates it, and CI diffs the output. The other `8` are
uncheckable from this checkout permanently, and `7` of those `8` are uncheckable **because of the
prohibition itself** — the resource was refused, so the number about it cannot be re-derived by
anybody standing here.

The register entry for this is standing unknown `U-3` in
[`docs/DEFINITION-OF-DONE.md`](DEFINITION-OF-DONE.md), carrying "no gate is available" as the finding
rather than as a to-do.

### The pre-registration, and the falsifier that fired

Nine falsifiers were written down before any command was run. **One fired.**

- **It fired on `87`.** The pre-registration said: *if any principled reading of "public symbols" at
  HEAD yields exactly `87`, then `A10.003`'s `UNREPRODUCIBLE` is wrong.* One does. The verdict at the
  audit's commit survives and the correction survives — the ratio still mixes two definitions — but
  the prediction was wrong on its own terms and the finding it produced is the most useful thing in
  this section. It is reported here because a pre-registration whose failures are quietly absorbed is
  a decoration.
- **It did not fire on a lifted conclusion.** No corrected figure moved any prohibition's conclusion,
  which is what section `6` predicted and what re-derivation confirmed.
- **It half-fired on the wheel.** The threshold was *within `200` B of `596,222`*; the rebuild landed
  `391` B away, so the literal falsifier did not fire — but the tree had moved two commits, so the
  test was not the one the threshold was written for, and the diagnosis above is the real answer.
- **Also pre-registered, and it happened:** *I expect to find at least one item where this page's
  correction is itself stale or over-tight; finding zero would be evidence I read it credulously.*
  Three were found.

### How this addendum fails

**It is an auditor grading its own corrections.** Section `9` says the verdicts on this page are claims
too and their error rate is unmeasured; the same is now true one level up. Nobody has re-derived the
ten corrections, and three of the three errors found in this page were found by the same person who
wrote this section — which is the shape section `9` warns about, arriving from inside again.

**The gate probe's two routes are the two that exist, not the two that could exist.** `0 of 13` is a
statement about this repository's current checks and not a proof that no check could work. A reader
who builds a third route and catches something has refuted the "no gate available" finding, and that
is the outcome `U-3` is written to invite.

**And the corrections are prose.** They will go stale exactly the way the sentences they replace did.
`C2`'s wheel figures are already dated by the commit they name; `C9`'s share of source moves with every
commit that touches `src/`. The difference is that each now prints the command that re-derives it,
which is a convention rather than a check — the same convention section `11` says a reader of the
large tables above is trusting rather than verifying.

---

**See also:** [`docs/AUDIT-2026-08.md`](AUDIT-2026-08.md) — the do-not list this page audits ·
[`docs/DECISIONS.md`](DECISIONS.md) — D-068, the first measured error rate, and the closed records in
stratum B · [`docs/POSITIONING.md`](POSITIONING.md) — the commitment whose reversal conditions
stratum C guards · [`docs/CLAIMS-LEDGER.md`](CLAIMS-LEDGER.md) — the ledger this page adds no debt to.
