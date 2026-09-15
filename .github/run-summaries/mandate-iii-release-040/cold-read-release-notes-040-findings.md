# Cold read of the `0.4.0` release notes — findings

**Read as a stranger on `0.3.0`, deciding in one screen whether to upgrade.** Read-only: nothing in
the repository was edited. Every finding carries file, line, the sentence quoted as it stands, what
was run to check it, and **exact replacement text the operator can paste verbatim before tagging.**

Scanned: `CHANGELOG.md` `## [0.4.0]` section (lines `10`–`1298`, `1,289` lines), against
`docs/RELEASE_CHECKLIST.md`, `docs/POSITIONING.md`, `docs/DECISIONS.md` D-127..D-136,
`docs/DEFINITION-OF-DONE.md`, and the running code at this working tree.

**Gate state at the working tree, run by this reader, all ten green:**

```
python -m pytest tests                      6187 passed, 10 skipped, 3 xfailed  rc=0
python -m ruff check src tests tools bench  All checks passed!                  rc=0
python -m ruff format --check ...           186 files already formatted         rc=0
python -m mypy                              no issues in 124 source files       rc=0
python tools/check_claims.py                unbacked 0 | deferred 185 | vm 64   rc=0
python tools/splits.py --check              splits manifest OK                  rc=0
python tools/gates.py --check               CARRYING IN-SITU EVIDENCE 21 of 42  rc=0
python tools/second_reader.py --check       findings open 5, fixed 10           rc=0
python tools/run_summary.py --check-agent-summary  4 dirs, 3 crashes, 0 unattr  rc=0
python tools/render_figures.py --check      figures OK                          rc=0
```

**R1 note that governs every edit below.** `CHANGELOG.md` is scanned and its deferred ledger is at
`185` of `185` and **may not grow**. All `28` of its deferred items sit at lines `1387`–`1628`, in
the `0.3.0` and earlier sections; the `0.4.0` section contributes **zero**. `check_claims.prose_of()`
masks fenced blocks *and every inline code span* before claims are collected, so **a figure inside
backticks is invisible to the gate**. Every replacement below keeps every figure backticked and adds
no bare number. **Re-run `python tools/check_claims.py` after each edit anyway.**

---

## 0. BLOCKER, and it is not in the prose: the release is not committed

`git status --short` at this tree:

```
 M CHANGELOG.md
 M pyproject.toml
?? .github/run-summaries/mandate-iii-release-040/
```

`git show HEAD:pyproject.toml` reads `version = "0.3.0"`. `git show HEAD:CHANGELOG.md` opens
`## [Unreleased]` with no `0.4.0` section. **Both the version bump and the whole release section are
uncommitted.** Consequences, in the order they bite:

1. **The green tick recorded in D-127 is on `6d44002`, which is not the commit to tag.** Checklist §1
   and §3: CI does not run on tags, so the tick that matters must be on the commit being tagged, and
   that commit does not exist yet.
2. **Tagging `6d44002` as `v0.4.0` fails the `build` job's assertion** — `GITHUB_REF_NAME.lstrip("v")`
   gives `0.4.0` against a wheel built from `version = "0.3.0"`. Per §9 that uploads nothing and
   spends no version, but it spends the release attempt.
3. `dist/` already holds `acronymkit-0.4.0-py3-none-any.whl` (`679,669` B of the `786,432` budget,
   `86.4` %) and `acronymkit-0.4.0.tar.gz`, built from the **uncommitted** tree, and
   `src/acronymkit.egg-info/PKG-INFO` reads `Version: 0.4.0`. §5 says clear the residue first:
   `rm -rf dist build src/*.egg-info` before `python -m build`, or `importlib.metadata` reports a
   version you did not build.
4. `.github/run-summaries/mandate-iii-release-040/` is untracked. `run_summary.py
   --check-agent-summary` currently reads `4` directories because that directory is on disk; commit
   it with the release or CI reads `3`.

**Order:** commit the bump, the `CHANGELOG` and the run-summary directory → push to `main` → confirm
CI green **on that commit in the GitHub UI** → then `git tag -a v0.4.0`.

---

## 1. Will this break me, and can I tell?

**Verified sound, and this is the part of the notes that works.** All three of the upgrade-relevant
facts are in the first screen, and the split is correctly described as not breaking.

| Claim | Where | Checked how | Verdict |
|---|---|---|---|
| `normalize` raises `TokenizationError` where it returned a `str` | L`18`–`28` | `normalize('TXN_©_ID', GovernedDictionary({}))` and `normalize('㎡', …)` both raise; traceback prints `acronymkit.core.exceptions.TokenizationError` | TRUE |
| `is_compliant` adds `unreadable_character` with `token=None`, no `fix`; `not_upper_snake` fix suppressed | L`29`–`36` | `is_compliant('TXN_©_ID', …).failures` → `unreadable_character` `token=None` `fix=None`; `not_upper_snake` `fix=None`; `compliant=False` as before | TRUE |
| **All `19` pre-split import paths survive and resolve to the same objects** | L`38`–`45`, L`403`–`411` | all `19` import (`acronymkit.governed` + its `13` submodules + `extractor`, `propagation`, `tokenizer`, `exceptions`, `conformal`); `governed.expand_identifier is catalog.expand_identifier` → `True`; `governed.tokenizer is catalog.tokenizer` → `True` | TRUE |
| `acronymkit.conformal` reachable as a package attribute | L`241` | `import acronymkit; acronymkit.conformal` resolves | TRUE |
| `data_packs` gone from `capabilities()`, `doctor --format json`, text `doctor`, `DATA_PACK_GROUP`; `__all__` unchanged | L`143`–`157` | `'data_packs' in capabilities()` → `False`; json keys carry none; no `data pack` line; `hasattr(diagnostics,'DATA_PACK_GROUP')` → `False`; `__all__` is `49` names, identical to the installed `0.3.0` | TRUE |
| `is_fully_known` stricter on brackets | L`502`–`510` | `value[x]` and `TXN_ID[0]` → `unaccounted=('[', ']')`; `[TXN_ID]`, `[db].[schema].[TXN_ID]`, `[my.column]` → `unaccounted=()` | TRUE |
| Digit rejoin no longer glues two numbers | L`511`–`515` | catalog `{'2020': …}`: `FY_20_20` → `'Fy 20 20'`; `FY_2020` → `'Fy Fiscal Twenty Twenty'` | TRUE |
| `AcronymPair.pattern` description covers all three values and the three bracket shapes | L`493`–`501` | `AcronymPair.model_fields['pattern'].description` names `long(short)`, `short(long)`, `short=long`, `()`/`[]`/`{}` | TRUE |
| `governed-gap` is the only governed command where `--dictionary` is optional | L`254`–`256` | `--help` on all eight governed verbs: seven say *Required*, `governed-gap` says *OPTIONAL here, and required by every other governed command* | TRUE |
| `propagate(text, pairs, *, gate=, selective=)`; `gate_disclosure`; `SelectiveRiskGate`, `StratumCertificate` | L`160`–`243` | signature and imports resolve | TRUE |

### F-1 — HIGH. "Two breaking changes" and "everything else is additive, opt-in, or documentation" are both false, and the notes label a third break themselves

`CHANGELOG.md:12`–`15`:

> Three mandates' work. **Two breaking changes, both in the governed naming subsystem, and the change
> that sounds breaking is not one.** Read the two bullets below, the paragraph after them, and the
> known-open defects under that, before you upgrade; everything else in this section is additive,
> opt-in, or documentation.

`grep -n BREAKING` over the section returns **three** items the notes call breaking, not two — the
third at `:143`, `- **BREAKING for anyone who asserts on the capability report's key set:
data_packs is gone.**`, under **Removed**. A removal is not additive, not opt-in and not
documentation. `Changed` also carries two behaviour moves a pipeline can notice (`is_fully_known`
bracket strictness at `:502`, the digit rejoin at `:511`), which the later paragraph mentions but
this sentence excludes. **A reader who stops after the first screen, as this sentence invites, has
been told there is nothing else that can break them.**

**Replacement for `CHANGELOG.md:12`–`15`:**

```
Three mandates' work. **Three breaking changes — two in the governed naming subsystem, one in the
capability report — and the change that sounds breaking is not one.** Read the two bullets below,
the paragraph after them, the known-open defects under that, and the one entry under **Removed**,
before you upgrade. The rest of this section is additive, opt-in, documentation, or a report that
gets stricter; **Changed** names the two stricter ones and says what each newly flags.
```

### F-2 — MEDIUM. Three "first entry under X" pointers send the reader to the wrong entry

Enumerating the sections: **Added** entry `1` is `selective=` (`:160`), entry `2` is `propagate()`
(`:196`). **Documentation** entry `1` is the module docstring (`:592`), `2` is the second-opinion
verifier (`:608`), `3` its correction (`:624`), `5` is *where `expand_identifier` spends its time*
(`:676`).

- `:69` — the `5.95` withdrawal says *"See the first entry under **Added**."* The first entry is
  `selective=` and never mentions `5.95`. The withdrawal is in entry **2**.
- `:98` — *"And A2 shipped … see the first entry under **Added**"*. `propagate()` is entry **2**.
- `:103` — *"the first three **Documentation** entries are the ones for you"* for the hot-loop and
  verifier questions. The hot-loop entry is the **fifth**; entry `1` is neither question.

**On a page whose stated job is letting a stranger find what is known-broken without reading the
source, a broken pointer is the defect, not a typo.**

**Replacements:**

`:69` — `score a document-scoped rule at article scope. See the first entry under **Added**.` →

```
  score a document-scoped rule at article scope. See the `propagate()` entry under **Added**.
```

`:98` — `document, opt-in, changing no output you already had — see the first entry under **Added**, which` →

```
document, opt-in, changing no output you already had — see the `propagate()` entry under **Added**,
which
```

`:102`–`:104` →

```
**If you call `expand_identifier` in a hot loop, or you were hoping for a second-opinion verifier
on `extract()`**, the two **Documentation** entries headed *where `expand_identifier` actually
spends its time* and *if you were waiting for `extract()` to gain a second-opinion verifier* — with
the **CORRECTION** that follows the second — are the ones for you. Neither changes any behaviour;
both change what you should expect next.
```

---

## 2. Can I find what is known-broken without reading the source?

**Five of the six the brief names are in the first screen and are accurate.** Verified:

- the `26` code points — `to_physical_name('ǰ')` → `physical='J̌'`, `unaccounted=()`, and
  `normalize` on that output raises. Matches D-130 exactly.
- `1,050` / version-keyed table — D-130's own walk reads `normalize breaks idempotence on 1,050`,
  `to_physical_name breaks idempotence on 1,076`, `union 1,076`, `disjoint True`, `1,050 + 26 = 1,076`.
  `tests/test_unicode_properties.py:395`–`404` carries `890`/`977`/`1050`/`1050`/`1048` with
  `breaking: 26` at all five. The notes reproduce all of it.
- A2's `5.95` x withdrawn — D-085 area: pre-registration required ten points, got `3.07`; `39.60 −
  36.53 = 3.07` reproduces from the two cited claim markers.
- selective risk refusing on SDU-21 — D-128: `0` of `21` thresholds at any of six alphas.
- **both headline rows still empty** — `python tools/splits.py --check` prints, verbatim, *no
  uncontaminated corpus carries role='held_out' for task='extraction'* and the same for
  `disambiguation`.
- the byte-identity proof is not re-runnable — `git ls-files` matches no such harness; D-133 and
  D-135 both record it unmeasurable here.

### F-3 — HIGHEST. A live, open, silent-data-loss defect on three public loaders is absent from the release notes entirely

`docs/DECISIONS.md:2636`–`2641` and `docs/DEFINITION-OF-DONE.md:200` both record it as **open and
unfixed**:

> **`loaders._read_pairs` discards rows with no count and says nothing.** It serves `load_csv`,
> `load_long_to_short_csv` and `load_term_index_csv`. A `5`-data-row CSV with one blank-value row and
> one blank-key row returns a `GovernedDictionary` with `3` entries and **no member anywhere saying
> two rows were dropped.**

Reproduced at this tree. A five-data-row CSV, one row with a blank value and one with a blank key:

```
load_csv(path, token_column='token', canonical_column='canonical')
  -> GovernedDictionary, len(entries) == 3
  -> warnings emitted: []
  -> no public member reports a drop
     ['abbreviate','approved_abbreviations','class_word_for','class_words','common_keywords',
      'custom','entries','from_json','from_long_to_short','from_mapping','is_approved','lookup',
      'longest_long_form_words','resolve','short_full_words','term_id_for','with_custom']
```

**`grep -ni "load_csv|_read_pairs|rows were dropped|discards|unusable row"` over the whole `0.4.0`
section returns nothing.** `docs/DEFINITION-OF-DONE.md:200` records criterion `7` at **three live
instances**, of which the notes publish one. This is the defect class the release leads with — *a
report claiming clean while data is lost* — on the path a first-time governed user reaches first: the
catalog they load from CSV. **It is the single most expensive omission in these notes, because it
refutes `docs/POSITIONING.md` on the page a stranger reads first and it can silently drop rows of a
vocabulary somebody else owns.**

**Insert as a sixth bullet in the KNOWN-OPEN DEFECTS block, after the `26`-code-point bullet at
`:57` (adds no bare number):**

```
- **Loading a catalog from CSV can drop rows and report nothing.**
  `acronymkit.governed.loaders._read_pairs` — behind `load_csv`, `load_long_to_short_csv` and
  `load_term_index_csv` — skips a row whose key cell or value cell is blank, which is the right
  call, and then returns a `GovernedDictionary` with **no member anywhere saying rows were
  dropped**: a `5`-row file with two unusable rows hands back `3` entries and reports clean. Same
  class as the two above, different unit — rows rather than characters. **Not fixed in this
  release**, because reporting the drop is a return-type change and therefore a breaking change
  owing its own byte-identity pass. **If you build a governed catalog from a CSV export, count the
  rows yourself.** `docs/DECISIONS.md` D-099; `docs/DEFINITION-OF-DONE.md` criterion `7`.
```

Two knock-ons to the same block, both one word:

- `:47`–`:49` — *"Each has its full entry below, under **Notes** unless said otherwise"* is not true
  of the new bullet, which has no entry below. Append to `:49` after `otherwise.`:
  `The CSV-loader bullet has no entry below; the record is its only fuller account.`
- `:12` — after F-1's replacement, the count of known-open defects in the block rises from six to
  seven; no number in the intro states it, so nothing else moves.

### F-4 — MEDIUM. `PhysicalName.unaccounted` ships and two of the three governed CLI verbs still do not print it

`:484`–`:491` announces the new field and closes *"**Additive, with a default**, so existing
constructions and JSON consumers are unaffected."* True. What it omits, recorded at
`docs/DECISIONS.md:2648`–`2651`: `PhysicalName.unaccounted` **is read by nothing inside the
package**, and of the CLI only `expand-identifier` prints an `Unaccounted` row — `check-name` and
`normalize-name` do not. A reader who upgrades for the new accounting and drives the library through
the CLI gets none of it on two of the three verbs.

**Append to `:491`:**

```
  Nothing inside this package reads the field yet, and of the CLI only `expand-identifier` prints an
  `Unaccounted` row: `check-name` and `normalize-name` do not surface it. Read it off the object.
```

### F-5 — LOW, clarity only. `1,050` is the count for `normalize`; `to_physical_name` breaks idempotence on `1,076`

`:60`–`:65` states the union correctly (`1,076` on Unicode `15.1`) but only ever attaches a count to
`normalize`. D-130's table also records `to_physical_name breaks idempotence on 1,076`. A reader can
finish the bullet believing the `26` break only the round trip. **Optional**, and it adds no bare
number:

`:64`–`:65` — `are \`26\` at all five. The two classes are disjoint and their union is \`1,076\` on Unicode \`15.1\`.` →

```
  are `26` at all five. The two classes are disjoint, and on Unicode `15.1` their union — the set on
  which `to_physical_name` is not idempotent — is `1,076`.
```

### F-6 — LOW. The selective bound's honest headline is a fraction the notes do not print

`:173` reads *"At `alpha=0.01` and `0.02` **nothing certifies and the gate answers `0.00` %.**"* —
true of the pooled arm. D-128's own verdict is the fraction over every cell: **`CELLS 18 | CARRY A
BOUND 8 | ANSWER 0.00 % 10`**, and *"the honest headline is the fraction rather than the best cell."*
Separately, `:176`–`:178` says *"the lowest selective risk **any** threshold can reach there is
`17.53` %"*; D-128 qualifies it as the lowest *at `50` or more accepted*. Neither is false as
written; both are tighter than the measurement. **Replacement for `:172`–`:173`:**

```
    `alpha`. At `alpha=0.01` and `0.02` **nothing certifies and the gate answers `0.00` %** — and
    across every arm-by-alpha cell on both corpora, `8` of `18` carry a bound and all `10` that fail
    answer `0.00` %. **The fraction is the headline, not the best cell.**
```

and `:177`, `lowest selective risk *any* threshold can reach there is \`17.53\` %, over a base disambiguator` →

```
    lowest selective risk any threshold reaches at `50` or more accepted units is `17.53` %, over a
    base disambiguator
```

---

## 3. Does anything describe work that was not done?

**Four findings. Two are numbers the same release invalidated; one is a self-refuting paragraph; one
is a page described in the present tense as it was three mandates ago.**

### F-7 — HIGH. `seven of the sixteen CLI commands` is false on the tree this release ships, and the notes print the command that falsifies it

`CHANGELOG.md:853`–`854`:

> - **The README now leads with governed naming.** It is a little over a third of the source, close to
>   half the public symbols, seven of the sixteen CLI commands, and the only half with a streaming batch
>   mode another runtime can drive.

`acronymkit --help` at this tree lists **seventeen** commands, of which **eight** read a governed
vocabulary: `check-name`, `expand-identifier`, `expand-token`, `governed-audit`, `governed-batch`,
`governed-gap`, `normalize-name`, `physical-name`. **The eighth is `governed-gap`, which this very
release adds** — announced at `:245`. The count was true before the entry three sections above it.
`README.md:543` and `:738` carry the same stale pair, and `:738` prints `acronymkit --help` beside
it as the re-derivation command, which is the claim the notes make at `:826`–`:828` about naming
structural counts with their commands.

**Replacement for `:853`–`:854`:**

```
- **The README now leads with governed naming.** It is a little over a third of the source, close to
  half the public symbols, eight of the seventeen CLI commands — `governed-gap`, added in this
  release, is the eighth — and the only half with a streaming batch
```

**The operator should fix `README.md:543` and `:738` in the same commit**, or the release ships a
front page whose own stated command disproves it. `README.md` is at `0` value-matched claims and
these figures are spelled words, not digits, so the claims gate is silent either way — re-run it.

### F-8 — HIGH. The closed self-audit series is published at six rounds; D-132 closes it at seven, and the paragraph congratulates itself for catching exactly this defect one round earlier

`CHANGELOG.md:1269`–`1280`:

> **The measured not-true rate of this project's own reporting is `15.97` % pooled over `SIX` rounds
> — `23` of `144`, Wilson `[10.89, 22.83]` — and that series is now closed.** … **Read the round
> count carefully, because the tree briefly disagreed with itself about it.** The series was declared
> closed at `16.67` % over five rounds while a sixth round was already in flight under the same
> rules; closing a series prospectively does not un-run a round performed under it, so the closing
> figure is the six-round one.

`docs/DECISIONS.md` D-132, whose title is *"Round seven ran under the closed frame's rule and its own
unit, and by D-122's rule it belongs to the series it declined to join"*, records:

```
  SIX rounds   5,5,6,2,2,3     23 of 144 = 15.97 %   Wilson [10.89, 22.83]  half-width 5.971
  SEVEN rounds 5,5,6,2,2,3,2   25 of 168 = 14.88 %   Wilson [10.29, 21.04]  half-width 5.379
```

> **The record's verdict: the submitted-sentence series is CLOSED AT `25` of `168` = `14.88` %,
> Wilson `[10.29, 21.04]`, over SEVEN rounds.** … `CLOSED_SERIES` is one round short again and this
> record does not rewrite it a second time in one phase — that is named here, in `CHANGELOG.md` and
> in D-135's criterion `13` verdict.

`tools/sample_claims.py:291`–`298` ships `rounds: 6, draws: 144, not_true: 23`. **D-132 says the
defect is named in `CHANGELOG.md`; it is not.** The `CHANGELOG` names the five→six instance and
presents the six-round figure as the closing one. So the release notes ship a superseded figure as
current, in the one paragraph in the document that exists to warn about that exact error. A reader
who quotes this release's stated self-audit rate quotes the wrong one.

**Replacement for `:1269`–`:1279`** (adds no bare number; every figure is backticked and every one
appears in D-132):

```
- **The measured not-true rate of this project's own reporting is `14.88` % pooled over `SEVEN`
  rounds — `25` of `168`, Wilson `[10.29, 21.04]` — and that series is closed there.** A sixth
  seeded sample of `24` claims returned `3` not true and a seventh returned `2`. **Read the round
  count carefully, because the tree has twice disagreed with itself about it.** The series was
  declared closed at `16.67` % over five rounds while a sixth was in flight under the same rules,
  and then at `15.97` % over six while a seventh was already graded under the same population
  definition; closing a series prospectively does not un-run a round performed under it, so the
  closing figure is the seven-round one. **`tools/sample_claims.py`'s `CLOSED_SERIES` still ships
  the six-round arithmetic**, which is the same defect one round on and is named as the next
  round's to close. A replacement sampling frame draws from a different population and **starts at
  `n = 0`**; no pooled figure spans the two. A seventh round moved the estimate `1.09` points and
  the half-width `0.59`, so **the interval is still moving about as fast as it is shrinking**.
  Quote it as seven graders' pooled rate and not as this project's. **Nothing about the library's
```

(then continue with the existing `measured behaviour is implicated` sentence and swap the trailing
citation to `docs/DECISIONS.md` D-115, D-131 and D-132.)

### F-9 — MEDIUM. The definition-of-done entries stop at the ninth sweep and at fourteen criteria; the tree carries twenty and a tenth sweep

Three entries in the section, and a fourth in `README.md`, disagree with the page they describe:

- `:826`–`:827` — *"the definition-of-done link says fourteen criteria rather than eight"*, offered
  as one of five README corrections. `README.md:785` does say *"the fourteen criteria"*, and
  `docs/DEFINITION-OF-DONE.md` carries **twenty**. So the notes present as a fix a value that is now
  short by six, and the release ships a README link that misstates its destination.
- `:1284` — *"the ninth sweep moved exactly one verdict"*, with `11` of `20` met. `docs/DECISIONS.md`
  D-135 is the **tenth** sweep: one verdict moved again (criterion `13`), six evidence cells
  corrected, and **criterion `7` gained the `26`-code-point class as a further live instance**. The
  met-count is unchanged at `11` of `20`, so no number here is wrong — but the sweep a reader is
  shown as latest is not the latest, and the tenth sweep's finding is the one the release's own
  headline defect belongs to.

**Replacement for `:826`–`:827`:**

```
  catalog is in the published figures; the definition-of-done link was corrected from eight criteria
  to fourteen, and **that page now carries twenty, so the link is stale again and is named here
  rather than quietly fixed**;
```

**Replacement for `:1283`–`:1284`** (first two lines of that entry):

```
- **The definition of done stands at twenty criteria, `11` of them met. The ninth sweep moved
  exactly one verdict — by narrowing it rather than by progress — and the tenth moved one again, on
  a payment rather than a re-reading, with six evidence cells corrected and no change to the
  met-count. Criterion `7` gained a further live instance at the tenth sweep: the `26`-code-point
  round-trip class above.** The deferred-ledger criterion is
```

(and add `and D-135` to that entry's closing citation.)

### F-10 — MEDIUM. `docs/GATES.md` is described in the present tense as it was three mandates ago, and the real figure is far less alarming than the one printed

`CHANGELOG.md:901`–`904`:

> [`docs/GATES.md`](docs/GATES.md) lists every CI gate, what it checks, and — the point of the page —
> what it is blind to; it **opens by reporting** that `0` of `36` gates carry recorded evidence of
> having actually failed on purpose in the environment they guard.

`docs/GATES.md:26` opens: *"The register holds forty-one gates and twenty-one of them carry in-situ
evidence."* `python tools/gates.py --check` at this tree: **`42` gates, `CARRYING IN-SITU EVIDENCE
21 of 42`.** A reader who follows the link finds neither `0` nor `36`. Present tense on a figure that
moved by twenty-one gates is a claim about a document, and it is wrong. Related and smaller: `:1237`
describes `run_summary.py --check` as *"registered as the thirty-ninth CI gate"* — true of its
registration order, now three gates behind the register; leave it, it is a historical fact about an
event, not a present-tense description of a page.

**Replacement for `:901`–`:904`:**

```
  [`docs/GATES.md`](docs/GATES.md) lists every CI gate, what it checks, and — the point of the page —
  what it is blind to; when it shipped it opened by reporting that `0` of `36` gates carried recorded
  evidence of having actually failed on purpose in the environment they guard. **Run
  `python tools/gates.py --check` rather than quoting either figure**: the register and the share
  carrying in-situ evidence have both moved several times since, and the page says so itself.
```

### Cleared, having been checked

- `:624`–`:651` — the CORRECTION about reusing a definition across a document is marked
  **SUPERSEDED IN THIS SAME RELEASE** and says `propagate()` ships. Correct handling of the exact
  error §4 of the checklist warns about, and the pattern the other entries should follow.
- `:1180`–`:1198` — the adjudicated pair corpus, filed as *"no corpus was registered"* and
  superseded on the registration half. `tools/splits.py --check` confirms
  `federal_register_rules_2024q1` at `role='single_annotator_reference'`, in `NEVER_HEADLINE_ROLES`,
  with the reason printed. TRUE.
- `:1160`–`:1166` — the stale MED1250 headline note, retired in place with *"Done, and that is why
  this release could be cut."* TRUE.
- `:1167`–`:1170` — *"The governed accuracy runs still record `splits_declaration = UNDECLARED`."*
  TRUE: `7` of `12` `splits_declaration` fields read `UNDECLARED (socrata …)` / `UNDECLARED
  (sec_xbrl …)`, while `[corpora.socrata]` and `[corpora.sec_xbrl]` are both declared in
  `bench/splits.toml`. Exactly as described.
- `:455`–`:457` — `0.4664` % distinct / `1.3145` % per row / `325` Socrata hits, `0.0000` % SEC:
  match `docs/DECISIONS.md:2572`, `:2618` and `docs/GOVERNED_NAMING.md:1440`, `:1446`.
- `:473` — `857,517` records across both corpora and three policies: matches
  `docs/DECISIONS.md:2591` and the derivation at `:2605`.
- `:389`–`:392` — `14.6560` % / `36.0072` %, and the notes' own statement that **neither figure is
  gated** because both live in fenced blocks. Confirmed: `tools/check_claims.py` is silent on them.
  Declaring an ungated figure ungated is the honest form.
- `:234`–`:238` — the `4.38` x multiple now carries *"up to … the multiple at the tightest of five
  alphas, falling to `0.97` at the loosest"*. `docs/DECISIONS.md:1777`–`1790` records the unqualified
  form as a defect; this text has the qualifier. Fixed.
- **Positioning**: `pyproject.toml:11` `description` now reads *"Governed acronym expansion against a
  catalog you supply…"*, and `src/acronymkit/__init__.py`'s docstring now opens *"a governance
  instrument for names somebody else owns"* with the refusing example and the `.phrase` foot-gun
  named. Both entries TRUE. **Note for the operator:**
  `docs/POSITIONING.md:113`–`115` still says that docstring is *"still shipping … Reported, not
  fixed"* — the positioning page is stale against the release, in the opposite direction from a
  falsehood. Outside the `CHANGELOG`, worth one line before tagging.

---

## 4. The three that must agree

| Thing | Value at this tree | Verdict |
|---|---|---|
| `pyproject.toml` `[project] version` | `0.4.0` (line `10`) | agrees — **uncommitted, see finding 0** |
| `CHANGELOG.md` release heading | `## [0.4.0] — 2026-09-15`, em dash, today's date | agrees |
| `## [Unreleased]` | present at line `8` and **empty** (blank line, then the `0.4.0` heading) | correct |
| Footer, `:1727` | `[Unreleased]: https://github.com/pierce-lonergan/AcronymKit/compare/v0.4.0...HEAD` | correct |
| Footer, `:1728` | `[0.4.0]: https://github.com/pierce-lonergan/AcronymKit/releases/tag/v0.4.0` | correct |
| Footer host/owner/repo | matches `pyproject.toml:105` `Repository` (`pierce-lonergan/AcronymKit`) | agrees |

**The tag I cannot check, stated exactly.** It must be **`v0.4.0`** — lower-case `v`, no prefix, no
suffix, no `release-` form. The `build` job compares `GITHUB_REF_NAME.lstrip("v")` against the
version parsed from the wheel filename, so `v0.4.0` → `0.4.0` → OK; `0.4.0` also passes but the
footer links assume the `v` form; `v0.4.1`, `V0.4.0` and `release-0.4.0` all fail. The assertion runs
**only on a `release` event**, so a `workflow_dispatch` with `target: pypi` skips it entirely — §4 and
§10 both say do not use it.

```
git tag -a v0.4.0 -m "acronymkit 0.4.0"
git push origin v0.4.0
```

**And the one-way door:** publishing the GitHub release *is* the upload. Get CI green on the commit
that carries the bump and this `CHANGELOG`, in the GitHub UI, before the tag exists.

---

## Summary, in the order the operator should act

| # | Severity | What | Where |
|---|---|---|---|
| 0 | **BLOCKER** | version bump and whole release section uncommitted; `dist/` and `egg-info` residue from the uncommitted tree | `pyproject.toml`, `CHANGELOG.md`, `dist/`, `src/acronymkit.egg-info` |
| F-3 | **HIGHEST prose** | open silent-row-drop defect on `load_csv` and two siblings absent from the notes | insert at `CHANGELOG.md:57` |
| F-1 | HIGH | "two breaking changes" / "everything else is additive" — three are labelled breaking | `CHANGELOG.md:12`–`15` |
| F-7 | HIGH | `seven of the sixteen CLI commands` — the tree has `17` and `8`, the eighth added by this release | `CHANGELOG.md:853`–`854`; `README.md:543`, `:738` |
| F-8 | HIGH | closed self-audit series published at six rounds; D-132 closes it at seven | `CHANGELOG.md:1269`–`1280` |
| F-2 | MEDIUM | three "first entry under X" pointers resolve to the wrong entry | `CHANGELOG.md:69`, `:98`, `:103` |
| F-9 | MEDIUM | ninth sweep shown as latest; `fourteen criteria` link stale against a twenty-criterion page | `CHANGELOG.md:826`–`827`, `:1283`–`1284`; `README.md:785` |
| F-10 | MEDIUM | `docs/GATES.md` described in present tense as `0` of `36`; it is `21` of `42` | `CHANGELOG.md:903` |
| F-4 | MEDIUM | new `unaccounted` field unread by the package and absent from two of three governed CLI verbs | `CHANGELOG.md:491` |
| F-5 | LOW | `1,076` is `to_physical_name`'s idempotence-break count and is only shown as a union | `CHANGELOG.md:64`–`65` |
| F-6 | LOW | selective bound's honest headline (`8` of `18`) and the `17.53` % qualifier | `CHANGELOG.md:172`–`173`, `:177` |

**What this read could not do.** It applied nothing and mutated nothing, so *"could a gate have
caught any of these?"* is unanswered by method — though F-7, F-8, F-9 and F-10 are all
cross-document staleness, which `tools/check_claims.py` is structurally blind to: every one of those
figures is either a spelled-out word or sits inside a code span that `prose_of()` masks before the
collector sees it. **The claims gate is green over all four.** It could not adjudicate the
`3,619,227`-record byte-identity claim either — third consecutive party unable to — because the
harness is uncommitted and the corpora are not in the repository.
