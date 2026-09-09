# Cold read six — findings

**Reader:** `cold-read-6`, Mandate III Phase D, first round. **Date:** 2026-09-09.
**Status: REPORT ONLY. Nothing in the tree was changed by this reader.** Section 5 of
[`docs/SECOND-READER.md`](../SECOND-READER.md) retired the fix clause; the applier is somebody else,
and `disposition = "fixed"` needs an `applied_by` that is not `cold-read-6`.

**This file is the reader's working paper.** The ledger rows below are drafted for whoever writes
[`docs/cold-reads.toml`](../cold-reads.toml), exactly as cold read five's were.

---

## 0. Triggers, and the gates as I found them

**Trigger A** — `python tools/second_reader.py --trigger`, 12 user-facing files:
`CHANGELOG.md`, `CONTRIBUTING.md`, `README.md`, `docs/ARCHITECTURE.md`, `docs/CLAIMS-LEDGER.md`,
`docs/DEFINITION-OF-DONE.md`, `docs/EVALUATION.md`, `docs/GATES.md`, `docs/GOVERNED_NAMING.md`,
`docs/JAVA_INTEROP.md`, `docs/RELEASE_CHECKLIST.md`, `docs/SOURCING.md`.

**Trigger B** — the cursor in `docs/cold-reads.toml` and in section 8 of the policy page both derive
to **`docs/SECOND-READER.md`**, and `--check` agrees. That is the file served, and it is followed
rather than announced. No figure is served this round.

### THE GATES ARE NOT GREEN IN THIS WORKING TREE. THREE OF THE TEN ARE RED.

`CONTRIBUTING.md` now publishes **ten** commands, not eight. Run one at a time on the working tree,
CPython 3.13.4 on win32, no sibling suite running. Command output, not a benchmark measurement.

```
  python -m pytest tests                            4 failed          rc=1   <-- RED
  python -m ruff check src tests tools bench                          rc=0
  python -m ruff format --check src tests tools bench                 rc=0
  python -m mypy                                                      rc=0
  python tools/check_claims.py                                        rc=0
  python tools/splits.py --check                                      rc=0
  python tools/gates.py --check                     1 problem(s)      rc=1   <-- RED
  python tools/second_reader.py --check                               rc=0
  python tools/run_summary.py --check                                 rc=0
  python tools/run_summary.py --check-agent-summary 1 problem(s)      rc=1   <-- RED
```

The four failures are
`tests/test_gate_manifest.py::TestTheRegisterThisRepositoryShips::test_it_validates`,
`tests/test_run_summary.py::TestThisCheckoutsExitAccounting::test_the_agent_gate_is_green_on_this_tree`,
`…::test_this_repository_carries_a_control_that_asserts_both_states` and
`tests/test_run_summary.py::TestTheAgentRegisterAndTheScriptAgree::test_the_mutation_target_exists_and_the_edit_applies`.
**All three red gates and all four failures have one cause**, and it is F-6-01 below.

**D-110's caution is honoured and it does not cover this.** D-110 records that no gate result taken
during a multi-workstream round is a statement about the finished tree, and that concurrency, not
defect, explained three earlier reports of instability. This is not that. The failure is
deterministic, it names one absent path, and the negative control separates it from the round:

```
  git worktree add --detach <tmp> 18204a1 ; python tools/gates.py --check
    CARRYING IN-SITU EVIDENCE:   20 of 40
    gate manifest OK                                                  rc=0
  the same command in the working tree
    gates.agent_summary.mutation.edits[0]:
      .github/run-summaries/_control-agent-crash/exits.toml does not exist,
      so this mutation cannot be applied and the gate has no demonstration   rc=1
```

Green at the round base, red in the round. It is this round's, whoever's round it is.

---

## 1. Findings

Ordered by severity. Every one carries the command that refutes it, run before it was written down,
and exact replacement text. Line numbers are of the working tree at the time of reading.

---

### F-6-01 — `docs/GATES.md:1562` — the register's newest gate is demonstrated against a fixture the tree does not contain, and it is what is reddening three gates

> **Quote, `docs/GATES.md:1562-1563`:** "So the demonstration is against a committed **control**,
> `.github/run-summaries/_control-agent-crash/`, and the distinction matters"

**Refutation.**

```
ls .github/run-summaries/                        ->  mandate-iii-phase-c        (only)
git ls-files .github/run-summaries               ->  three files, all under mandate-iii-phase-c
git status --porcelain --untracked-files=all -- .github
                                                 ->  M .github/gates.toml
                                                     M .github/workflows/ci.yml   (no untracked fixture)
grep -n run-summaries .gitignore                 ->  (no match; it is not ignored, it is absent)
python tools/gates.py --check                    ->  rc=1, naming
    .github/run-summaries/_control-agent-crash/exits.toml
python tools/run_summary.py --check-agent-summary
  -> "no control directory in .github/run-summaries expects ['absent', 'unreadable']"   rc=1
git show 18204a1:.github/gates.toml | grep -c _control-agent-crash   ->  0
```

The register entry at `.github/gates.toml:1156` is **new in this working tree** and points at a
directory that exists nowhere — not tracked, not untracked, not ignored. The prose describes it as
*committed*. The mutation transcript at `docs/GATES.md:1578-1582` publishes
`agent_summary  DEMONSTRATED  mutated rc=1, restored rc=0`, dated 2026-09-09, for an edit that
`tools/gates.py` itself reports as inapplicable.

**This is `017cb37` again, one channel over.** That commit's message is *"the gate register shipped
pointing at a figure the sdist did not carry, through a reference channel the link guard cannot
see."* This is a register pointing at a **fixture** the tree does not carry. The class is the same
and the newer instance is worse, because this one reddens the build rather than hiding.

**Replacement.** There is no wording fix. The fixture is the fix: commit
`.github/run-summaries/_control-agent-crash/` with the roster whose `control` key declares
`absent` and `unreadable`, and the `exits.toml` carrying `killed-before-filing = 137` that the
register's `find` string names. Until it lands, `docs/GATES.md:1562` must not say *committed*, and
the mutation block at `1578` must not be published as a run that happened on this tree.
If the fixture is landing in the same commit as this prose, this finding closes itself and the
correct disposition is `fixed`; **if it is not, the three red gates are what ships.**

**Owner:** the workstream that holds `.github/gates.toml` and `tools/run_summary.py`.

---

### F-6-02 — `docs/CLAIMS-LEDGER.md:528` — a published `--frame` transcript that the shipped tool does not produce, in either its figures or its shape

The brief for this round names the ledger's series closure as a risk area. **The closure itself is
correct** (see §3 below). The block that prices its successor is not.

> **Quote, `docs/CLAIMS-LEDGER.md:528-540`:** "`$ python tools/sample_claims.py --frame`  # on a
> quiet checkout at 18204a1 … `frame: 2180` … `round varies varies 12` … `recent 1751 80.3 % 8` …
> `cold 429 19.7 % 4`"

**Refutation.** Same tree, same command, the whole output:

```
python tools/sample_claims.py --frame
  frame: 2187 unbacked claim-shaped number(s) in the scan set
  round    N   671  ( 30.7 % of the frame)  draw 12
  recent   N  1175  ( 53.7 % of the frame)  draw 8
  cold     N   341  ( 15.6 % of the frame)  draw 4
  design effect at equal rates: 1.20
```

Six differences, and the hedge on the block — *"Re-run it; it moves with the tree"* — covers exactly
one of them:

| published | the tool, now | can drift explain it |
|---|---|---|
| `frame: 2180` | `2187` | yes, `+7` |
| `round  varies  varies` | `round N 671 (30.7 %)` | **no** — that is a different output *shape* |
| `recent 1751  80.3 %` | `recent 1175  53.7 %` | **no** — `-576` |
| `cold    429  19.7 %` | `cold    341  15.6 %` | **no** — `-88` |
| percentages over a `2180` base of `recent + cold` | three disjoint strata summing to the frame | **no** — a different partition |
| `2.03` at the shipped default (line 551) | `1.20` | **no** — allocation and shares only |

And the window sub-block and the two prose figures beside it, each re-derived:

```
  --recent-commits  5   cold  819 of 2188      published:  918 of 2180
  --recent-commits 20   cold  341 of 2187      published:  429 of 2180
  --recent-commits 40   cold    2 of 2187      published:   16 of 2180
  --base HEAD~3         round 1093 of 2187     published: 1102 of 2180
  design effect over those four runs: 1.33, 1.20, 1.60, 1.02  ->  range 1.02-1.60
```

`docs/CLAIMS-LEDGER.md:550-552` says the design effect "measures `1.01` to `2.78` on this tree
depending on the window, and `2.03` at the shipped default". **Neither endpoint and neither value is
reachable**: the widest spread I could produce across the four windows the page itself names is
`1.02`-`1.60`.

**And "on a quiet checkout at 18204a1" cannot be literally true.** `git log -- tools/sample_claims.py`
returns nothing: the tool is untracked and did not exist at `18204a1`. The charitable reading is *a
tree whose HEAD is `18204a1`*, which is the tree I ran on and which does not reproduce the block.

**Why this matters more than a stale number.** This is the section that closes a five-round series on
the ground that its interval moves faster than it shrinks, and replaces it with a design whose whole
declared cost is the design effect. **`2.03` is the price the section quotes for the change and
`1.20` is the price the tool charges.** The argument is not overturned — `1.20 > 1.00`, so the
direction survives — but the magnitude a reader is asked to accept is `69` % too large, and the
sentence "the tool refuses to print the pooled rate without it" invites the reader to check.

**Replacement, lines 526-552.** Do **not** retype the table. Delete the transcription and paste the
tool's own `--frame` output, re-run at the moment the commit is made, with the four windows the page
already argues from (`--recent-commits 5 / 20 / 40` and `--base HEAD~3`) below it. The output as it
stood when this read ran is the first fenced block in this finding; it will have moved by the time
anybody applies this, which is the whole reason to paste rather than transcribe.

*(This replacement is given as an instruction rather than as text because writing the figures out
here a second time would arm four of them under `tools/check_claims.py`'s unit rule and grow the
deferred ledger, which R-rule forbids. The figures are above, inside a fence, where the same gate
cannot read them — an asymmetry worth noticing, and D-052's point exactly.)*

and at lines 543-545:

> **This repository has almost no cold text, which is the premise the change rests on and it is weak
> here.** Widen the window to `40` commits and `2` of `2187` numbers sit in a file nobody has
> touched; one round's own diff (`HEAD~3..HEAD`) covers files carrying `1093` of `2187`.
> De-weighting cold text saves little when there is little.

and at lines 549-552:

> **The price is a number and it is printed on every draw.** The design effect of the `12`/`8`/`4`
> allocation — the ratio of the design-weighted estimator's variance to a uniform draw's, under the
> null that every stratum carries the same rate — measures `1.02` to `1.60` on this tree depending on
> the window, and `1.20` at the shipped default.

**Owner:** the workstream that holds `tools/sample_claims.py` and section 6.

---

### F-6-03 — `docs/SECOND-READER.md:529` — the split moved the module count from 40 to 64, and section 7's live cost argument still says 40

This is the trigger-B file, and this is the finding the package split caused in it.

> **Quote, `docs/SECOND-READER.md:529-531`:** "`find src/acronymkit -name '*.py' | wc -l` returns
> `40`. Admitting the package's source would take the rotation from `21` entries to `61`, so the set
> would turn over in sixty-one rounds instead of twenty-one"

**Refutation.**

```
find src/acronymkit -name '*.py' | wc -l                  ->  64
python -c "import sys;sys.path.insert(0,'tools');import second_reader;
           print(len(second_reader.user_facing_files()))"  ->  25
python tools/second_reader.py --check
  -> rotation: 25 file(s); trigger B serves docs/SECOND-READER.md next
```

`64` not `40`; `25 + 64 = 89` not `61`; eighty-nine rounds, not sixty-one. The number is the
load-bearing half of a *disposition*: section 7 declines to admit `src/` into the rotation on a cost
argument, and the cost it quotes is `56` % of the real one. The conclusion survives — `89` is worse
than `61` — but the page is arguing a case with a figure the split falsified in the same tree that
published it.

**Replacement, `docs/SECOND-READER.md:528-531`:**

> `--check` refuses any file `user_facing_files()` enumerates that the rotation cannot reach, and
> `find src/acronymkit -name '*.py' | wc -l` returns `64` — it returned `40` before the package was
> split into `core`, `nlp` and `catalog`, and the compatibility shim is thirteen of the difference.
> Admitting the package's source would take the rotation from `25` entries to `89`, so the set would
> turn over in eighty-nine rounds instead of twenty-five.

**Also stale in the same file for the same reason, and cheap to fix in the same edit:**
`docs/SECOND-READER.md:245-246`, the C1 *Caught* record, publishes "`find src/acronymkit -name
'*.py' | wc -l` returns forty" in the present tense against a historical finding. Add the date, or
say *returned forty when this was found*.

**Owner:** unowned — this is the round's, per section 5.2.

---

### F-6-04 — `docs/SECOND-READER.md:511` and `:121` — the page describes an `is_user_facing` the tree replaced last round, and contradicts itself one section earlier

Two sentences, one cause: F-5-4 admitted `docs/**/*.svg` and the prose describing the rule was not
followed through.

> **Quote A, `docs/SECOND-READER.md:511-512`:** "`user_facing_files()` enumerates root files and
> `docs/*.md` and returns `21`, none of them source."

> **Quote B, `docs/SECOND-READER.md:121-123`:** "And minus everything under `docs/` that is not
> Markdown — `docs/cold-reads.toml` is this policy's machine state"

**Refutation.**

```
python -c "...; u=second_reader.user_facing_files(); print(len(u));
           print([f for f in u if not f.endswith('.md')])"
  ->  25
  ->  ['docs/figures/monoculture-band-dark.svg', 'docs/figures/monoculture-band-light.svg',
       'docs/figures/refusal-curve-dark.svg', 'docs/figures/refusal-curve-light.svg',
       'pyproject.toml']

tools/second_reader.py:238   if not norm.startswith("docs/") or not norm.endswith((".md", ".svg")):
```

Quote B is refuted by **its own section**: `docs/SECOND-READER.md:166-167` says, forty-five lines
later, *"`.svg` is in, `.toml` is still out."* Section 3 now tells a reader the trigger drops every
non-Markdown file under `docs/` and then tells the same reader it does not. **This is C2 — two
descriptions of one mechanism — with both descriptions inside one section of one page**, which is the
narrowest form of it this repository has recorded.

**Replacement, `docs/SECOND-READER.md:121-123`:**

> Minus `docs/DECISIONS.md` and `docs/AUDIT-*.md`, which are historical records rather than
> instructions to a user, and minus `docs/notes/*.md`, which are scoped technical notes read by
> somebody who arrived from a link that already warned them. And minus every extension under `docs/`
> **except `.md` and `.svg`** — `docs/cold-reads.toml` is this policy's machine state, not a page a
> stranger reads, and a trigger that fired on it would make every cold read demand a cold read of its
> own findings; a figure, by contrast, is prose, and the paragraph below is why.

**Replacement, `docs/SECOND-READER.md:511-512`:**

> `PATHSPEC` is six entries and `src/` is not one of them; `user_facing_files()` enumerates root
> files, `docs/*.md` and `docs/**/*.svg`, and returns `25`, none of them source.

**Owner:** unowned.

---

### F-6-05 — `docs/SECOND-READER.md:439` and `:446-448` — the eighth gate is in CI, and the page still says twice that it is not

> **Quote A, `:439`:** "`0.09s  exit=0  python tools/second_reader.py --check  <- new, and NOT in CI
> yet`"
> **Quote B, `:446-448`:** "`python tools/second_reader.py --check` is listed here because a cold
> reader should run it, **not** because CI does — no job invokes it yet"

**Refutation.**

```
grep -n second_reader .github/workflows/ci.yml
  115:      - name: The cold-read ledger is consistent with the policy page
  118:        # `tools/second_reader.py --check` adjudicates the second-reader policy:
  129:        run: python tools/second_reader.py --check
grep -n "^\[gates\.second_reader\]" .github/gates.toml   ->  2366
```

The step's own comment reads *"THE EIGHTH GATE, WHICH WAS RUN EVERY ROUND AND NEVER BY CI"* — it was
registered and wired by `fbf7c45`, whose subject line says so. Two sentences on this page still
describe the world before that commit, and **one of them is inside the block that begins "Two
corrections in that block, and one of them is a gate"** — a paragraph written to correct a gate count
now carries a gate-registration claim of its own that has gone false.

**Do not confuse this with the job section 7 is still blocked on.** That one — `--trigger` against the
push, failing when the list is non-empty and the head commit carries no `Second-reader:` trailer — is
genuinely absent (`grep -rn "Second-reader:" .github/` returns nothing), and section 7's disposition
is correct as written. Only the `--check` claims are stale.

**Replacement, `:439`:** `0.09s  exit=0  python tools/second_reader.py --check  <- the eighth, and in the lint job since fbf7c45`

**Replacement, `:446-448`:**

> And `python tools/second_reader.py --check` was listed here as *not in CI* for as long as that was
> true. It is the eighth gate, `fbf7c45` put it in the `lint` job and in `.github/gates.toml`, and a
> cold read is what found that it had never run there. What remains uninvoked is the *trigger* job
> [section 7](#7-how-this-fails) is blocked on, which is a different command.

**Owner:** unowned.

---

### F-6-06 — `docs/SECOND-READER.md:592`, `:603`, `:617`, `:636`, `:408` — five sentences narrating a ledger state that two cold reads have moved past

The cursor block itself is correct and `--check` agrees with it. Everything around it is one to three
reads old.

**Refutation, one command:**

```
python tools/second_reader.py --check
  cold reads: 4 recorded; newest 2026-09-08
  rotation: 25 file(s); trigger B serves docs/SECOND-READER.md next
  findings: open 5, fixed 10, blocked 0, permanent 0  (of 15)
  OPEN AND AT THE LIMIT: 0 of 5
grep -n 'disposition' docs/cold-reads.toml
  ->  F-2026-08-24-01/-02/-03 and F-2026-08-25-01 all "fixed"
```

| line | says | is |
|---|---|---|
| `:592` | the last read was `2026-08-26` and served `docs/SUPPORT_MATRIX.md`, "entry five of the twenty-one" | the last read is `2026-09-08` and served `docs/GATES.md`, entry six of **twenty-five** |
| `:603-605` | "The cursor points at a page that already has a finding against it. `F-2026-08-24-05` is `docs/SUPPORT_MATRIX.md:39`" | the cursor points at **this page**, and `F-2026-08-24-05` is `fixed` |
| `:617` | `rotation: 21 file(s); trigger B serves docs/SUPPORT_MATRIX.md next` — published as `--check` output | `rotation: 25 file(s); trigger B serves docs/SECOND-READER.md next` |
| `:710` | "The count is derived, `rotation: 21 file(s)`" | `25` |
| `:636` | `F-2026-08-24-01`, `-02`, `-03` are "open and one cold read from being refused as open" | all three `fixed`, applied `2026-08-26` |
| `:406-418` | `F-2026-08-25-01`'s "row still reads `disposition = "blocked"`" and "The next cold read owes this row three fields" | `disposition = "fixed"`, `applied_by = "operator, mandate III phase A salvage"`, `applied_in = "2026-08-26"`. **The debt was paid; the paragraph describing the debt was not.** `blocked` is `0` on the whole ledger |

**Replacement, `:617` and `:710`:** re-run the command and paste it. **Replacement, `:591-593`:**

> Read that as: the last cold read (2026-09-08) served [`docs/GATES.md`](GATES.md), which is entry six
> of the twenty-five in section 3, so trigger B serves entry seven next — this page.

**Replacement, `:603-607`:** the paragraph's point was that the ledger and the rotation arrived at one
page from opposite directions. That is still true and the page is now this one:

> **The cursor points at the policy page itself, and it has an open finding against it.**
> `F-5-5` says a rotation entry can be spent on a document trigger A already served, and this is the
> first read where the rotation serves the page that carries the rule. Trigger B and the ledger
> arriving at the same document from opposite directions is the evidence either mechanism works.

**Replacement, `:636`, third table row:**

> | "Report everything else" produced no fix — the C1 finding was unaltered in all three places one round later | **Fixed, two reads later, and the mechanism is why.** `F-2026-08-24-01`, `-02` and `-03` were carried as `open` past their re-affirmation and applied on `2026-08-26` with a second name against each. The bound section 5.3 promises is two cold reads; these took two |

**Replacement, `:406-418`:** the whole paragraph should be deleted and replaced with its outcome —
it is now a description of a hole that the mechanism closed, presented as a hole that is open.

**Owner:** unowned. **Note for the ledger:** `F-5-5` is `open` and this read is its second; section
5.3 refuses `open` after two cold reads, so the next read must move it or the gate reddens.

---

### F-6-07 — `src/acronymkit/governed/__init__.py:5-8` and `docs/ARCHITECTURE.md:135-136` — the shim's justification lists five places the old path is named; two of them do not name it, and the two copies of the list disagree

This is the shape the brief predicted: *one sentence in two places*.

> **Quote A, the shim docstring:** "``acronymkit.governed`` is a **public import path with a
> documented API**. It is named in ``README.md``, in ``docs/GOVERNED_NAMING.md``, in
> ``docs/QUICKSTART_GOVERNED.md``, in the CLI's own help, and in ``docs/DECISIONS.md``"

> **Quote B, `docs/ARCHITECTURE.md:135-137`:** "`acronymkit.governed` is named in `README.md`, in
> [docs/GOVERNED_NAMING.md](GOVERNED_NAMING.md), in the CLI, and in `docs/DECISIONS.md`"

**Refutation.**

```
grep -c "acronymkit\.governed" docs/QUICKSTART_GOVERNED.md   ->  0
grep -c "acronymkit\.governed" src/acronymkit/cli.py         ->  0
python -m acronymkit.cli --help                              ->  17 commands, zero import paths
grep -rn "acronymkit\.governed" src --include=*.py | grep -v "^src/acronymkit/governed/"
  ->  two hits, both in src/acronymkit/__init__.py, both inside a comment about lazy binding
```

`docs/QUICKSTART_GOVERNED.md` names no import path at all — it is a CLI-only page, 33 occurrences of
the word *governed*, all of them subcommand verbs and fixture directories. The CLI's `--help` prints
`Usage`, `Options` and seventeen command lines; the only `acronymkit.catalog` in `cli.py` is a
`:mod:` role in a module docstring that `--help` never renders.

**The shim survives the correction** — `README.md`, `docs/GOVERNED_NAMING.md` and `docs/DECISIONS.md`
do name the path, and `docs/DECISIONS.md` alone carries the argument, because nobody may edit it. But
the justification for keeping a second public API forever is stated on five legs and stands on three,
and the page a caller reads (`ARCHITECTURE.md`) already quietly dropped one of the two bad legs
without saying so, which is how a divergence starts.

**Replacement, both places, one sentence:**

> `acronymkit.governed` is a public import path with a documented API. It is named in `README.md`,
> in `docs/GOVERNED_NAMING.md`, and in `docs/DECISIONS.md` — and the last of those is a file only the
> recorder may edit, so breaking the path would leave this project's own decision record citing an
> import that no longer exists.

**Owner:** the workstream that holds the split.

---

### F-6-08 — `docs/GATES.md:1648` and `:1699` — two counts in the newest gate entry that the tree does not produce

> **Quote A, `:1648`:** "Run by hand on the mutated tree it gives `3 failed, 135 passed`"
> **Quote B, `:1699`:** "a failure in the cheap lint job that names the seam rather than one red case
> among 5,884"

**Refutation.**

```
python -m pytest tests/test_architecture_boundaries.py --collect-only -q | tail -1
  ->  tests/test_architecture_boundaries.py: 140
python -m pytest tests/test_architecture_boundaries.py -q     ->  140 dots, no skips, no xfails
python -m pytest tests --collect-only -q | awk -F': ' '/^tests\/.*: [0-9]+$/{s+=$2} END{print s}'
  ->  6035
```

`3 + 135 = 138`, and the file collects `140` with nothing skipped: on this tree the mutated run must
read `3 failed, 137 passed`. And `5,884` is neither the round base (`5798 passed, 10 skipped,
1 xfailed` at `18204a1`) nor this tree (`6035` collected). **I could not re-run the mutation** — it
edits `src/acronymkit/core/spans.py` and this reader changes nothing — so the honest reading is that
the transcript was taken two tests ago rather than that it is wrong about what fails. Both numbers are
un-gated prose: `tools/check_claims.py` returns `0` with them in place, because neither carries arming
vocabulary.

**Replacement, `:1648`:** re-run `python tools/gates.py --mutate architecture_boundaries` and paste
the counts it prints, or drop the totals and keep the three failure lines, which are the evidence.
**Replacement, `:1699`:** "…rather than one red case among six thousand", or cite the count with the
command that derives it.

**Owner:** the workstream that holds the split.

---

### F-6-09 — `docs/DEFINITION-OF-DONE.md:580` and `bench/run_micro.py:271` — a published benchmark row labels itself with an import that raises

> **Quote, `docs/DEFINITION-OF-DONE.md:580`, the row's label:** "`from acronymkit import Engine`" —
> followed on the same line, inside the same fenced block, by five medians, the recorded figure and a
> direction. The label is the whole of the finding; the timings are not in dispute and are not
> retyped here, because doing so would arm one of them under the unit rule.

**Refutation.**

```
python -c "from acronymkit import Engine"
  ->  ImportError: cannot import name 'Engine' from 'acronymkit'
python -c "import acronymkit; print([n for n in acronymkit.__all__ if 'ngine' in n])"
  ->  ['AcronymEngine', 'EngineMetadata', 'EngineTier']
grep -n "cold_import_engine_ms" bench/run_micro.py
  98:    "cold_import_engine_ms": "from acronymkit import AcronymEngine",
  271:        print(f"from acronymkit import Engine   : {cold['cold_import_engine_ms']:8.1f} ms")
```

**The measurement is right and its label is wrong.** `run_micro.py:98` times the correct statement;
`run_micro.py:271` prints a label naming a statement that raises, and `docs/DEFINITION-OF-DONE.md`
faithfully transcribes what the tool printed. `docs/EVALUATION.md:235` describes the same figure
correctly as `from acronymkit import AcronymEngine`, so two user-facing pages spell one measured
quantity two ways and only one of them can be executed. This is C3 applied to a label rather than to
a return value, and it is the cheapest defect in this document to fix.

**Replacement, `bench/run_micro.py:271`:**
`print(f"from acronymkit import AcronymEngine : {cold['cold_import_engine_ms']:8.1f} ms")`
and re-transcribe `docs/DEFINITION-OF-DONE.md:578-582` from the corrected output.

**Owner:** the workstream that holds `bench/run_micro.py`.

---

### F-6-10 — `docs/SECOND-READER.md:477` — a cost figure that agrees with nothing, including the block above it

> **Quote:** "| Trigger B — cold-read one untouched file from the rotation | one file, median 3,792
> words |"

**Refutation.** `python tools/second_reader.py --cost` reports the median at `3,470` words
(`docs/INSTALL.md`); the `--cost` block published thirty lines earlier at `:455` reports `4,362`
(`docs/POSITIONING.md`). **Three values for one quantity on one page**, and `3,792` appears nowhere
else in the tree — it is not a stale copy of either. Low severity, no argument turns on it, but it is
a number with no derivation inside a table whose neighbours all have one.

**Replacement:** "| Trigger B — cold-read one untouched file from the rotation | one file; `--cost`
prints the current median |". Do not type a third number.

**Owner:** unowned.

---

## 2. Question 4, per document. No abstentions.

Section 4.1 admits none, so each of the thirteen documents read gets a nomination even where I found
nothing wrong.

| document | the sentence most likely to be false | checked how |
|---|---|---|
| `docs/SECOND-READER.md` *(trigger B)* | `:529` "`find src/acronymkit -name '*.py' \| wc -l` returns `40`" | ran it: `64`. **F-6-03** |
| `docs/GATES.md` | `:1562` "the demonstration is against a committed **control**" | `ls`, `git ls-files`, `gates.py --check`. **F-6-01** |
| `docs/CLAIMS-LEDGER.md` | `:551` "`2.03` at the shipped default" | ran `--frame`: `1.20`. **F-6-02** |
| `docs/ARCHITECTURE.md` | `:135` "named in … the CLI" | `--help` output; `grep` on `cli.py`. **F-6-07** |
| `docs/DEFINITION-OF-DONE.md` | `:580` "`from acronymkit import Engine`" | executed it; `ImportError`. **F-6-09** |
| `CHANGELOG.md` | `:298-303` "**Every old path is kept, and returns the SAME OBJECTS.**" | executed all 19; identity holds. **Survives** |
| `README.md` | `:19-23` the `GovernedNamer` example's two printed values | executed; `'Transaction Applicant Identifier'` and `False`. **Survives** |
| `docs/GOVERNED_NAMING.md` | `:8-11` the `expand_identifier` example | executed; `'Transaction Identifier'`. **Survives** |
| `CONTRIBUTING.md` | "Ten commands … CI runs all ten" | all ten located in `.github/workflows/ci.yml`. **Survives** — but three of the ten are red on this tree (§0) |
| `docs/EVALUATION.md` | `:2461` "`acronymkit.nlp.propagation.propagate()`" | imported; resolves. **Survives** |
| `docs/JAVA_INTEROP.md` | `:210` "`acronymkit.catalog` imports and runs" | import resolves; GraalPy not installed here, so the *runs* half is **unchecked** |
| `docs/RELEASE_CHECKLIST.md` | `:373` "`acronymkit.catalog` only" | `git grep`; consistent. **Survives** |
| `docs/SOURCING.md` | `:695` `from acronymkit.catalog import GovernedDictionary, expand_identifier` | executed. **Survives** |

---

## 3. What I expected to find and did not. Each of these could have failed here.

Reported because a checklist that only prints hits is indistinguishable from one that was not run.

**The compatibility decision is consistent across all five surfaces.** `README.md:31-33`,
`CHANGELOG.md:305-310`, `docs/ARCHITECTURE.md:143-146`, `docs/GOVERNED_NAMING.md:29` and the shim's
own docstring each state: kept **through the whole of the `0.x` line**, removal needs a **major
version**, preceded by a `DeprecationWarning` **announced in a minor release at least one release
ahead**, and **no warning is emitted today**. Every page that takes a position says **not breaking**;
none implies a warning exists. The shim's docstring even names `CHANGELOG.md` as where the commitment
is written down, and it is there. This was the brief's second named risk and the tree passes it. The
only defect in the neighbourhood is F-6-07, which is about the *list of pages*, not the lifetime.

**The nineteen legacy paths are asserted per path, and they resolve.** `LEGACY` in
`tests/test_architecture_boundaries.py:561-579` holds exactly nineteen entries — `governed` plus its
thirteen submodules, `extractor`, `propagation`, `tokenizer`, `exceptions`, `conformal` — and I
executed all of them: `__all__` matches element-for-element (`48` names),
`governed.expand_identifier is catalog.expand_identifier`, and
`governed.tokenizer is catalog.tokenizer`.

**Every documented import in the user-facing corpus executes.** I extracted every `from acronymkit…
import …` and `import acronymkit…` from `README.md`, `CHANGELOG.md`, `CONTRIBUTING.md`, `SECURITY.md`
and all nineteen `docs/*.md`, resolved each to a `(module, name)` pair, and imported it: **40 pairs,
`0` failures**, once `F-6-09`'s prose row is excluded. **The split did not leave a single raising
import in the documentation.** That was the brief's first named risk and it is the strongest negative
result in this read.

**The series closure is correctly stated and its arithmetic reproduces.**
`docs/CLAIMS-LEDGER.md:470` says CLOSED in the heading, `:493` says "The series is **CLOSED** at those
numbers", `:509` says "the new series starts at `n = 0`", and the tool prints
`IT DOES NOT CARRY ACROSS` on every `--frame`. I re-derived the Wilson intervals independently:
`20/120` gives `[11.06 %, 24.35 %]`, half-width `6.64`; `18/96` gives `18.75 %`, half-width `7.75`;
the deltas `2.08` and `1.11` are right; and `n ≈ 600` does put the half-width at `2.98` points, so
"`25` rounds of `24` **in total**, so `20` more" is right including the trap it flags. **Nothing on
that page continues the old series into the new one.** The brief's third risk area is clean; only the
frame block beneath it (F-6-02) is not.

**The sixteen-to-seventeen command growth was caught everywhere it mattered.** `governed-gap` took
the CLI from `16` to `17` (`grep -c '\.command('  ->  17`, and `--help` lists 17). I expected
`docs/SUPPORT_MATRIX.md:39` and `docs/OFFLINE.md:25,150` to still say sixteen — the `F-2026-08-24-01`
to `-05` cluster was fixed at sixteen. **All three say `17`, and all three name the four undriven
subcommands including `governed-gap`.** The fix outran the finding.

**`core` really is a leaf.** `grep` for `import re`, `regex`, `unicodedata` and `normalize` across
`src/acronymkit/core/*.py` returns nothing; the one in-package edge is `..models` under
`TYPE_CHECKING`, and `models.py` is facade rather than `nlp` or `catalog`, so
`docs/ARCHITECTURE.md:68-70`'s "not under `typing.TYPE_CHECKING`" and `:104-106`'s "single in-package
edge … under `TYPE_CHECKING`" are **not** in contradiction. I checked this expecting a contradiction
and there is none.

**Two `docs/OFFLINE.md` lines I would raise if this were its round.** `:407` and `:457` still say
"all 27 modules" under an exhaustive word while `:53` and `:70` were corrected to say *the 27 that
existed when the scan ran, against 40 today* — and `40` is now `64`. `docs/OFFLINE.md` is served by
neither trigger this round. Recorded here so the next reader served it does not have to re-find it.

---

## 4. What this read could not check

- **The `3,619,227`-record byte-identity claim (R19).** `CHANGELOG.md:314-323`,
  `docs/ARCHITECTURE.md:154-158` and the shim docstring all rest on it. The harness that produced it
  is not in the tree under a name I could find, and the governed corpora are not present in this
  checkout. **Unmeasurable here, and that is the honest answer.** It is carried on the split
  workstream's word, exactly as D-110 carried C1's `4,260`-document digest, and it deserves the same
  second party.
- **The `--mutate` transcripts.** Both `agent_summary` and `architecture_boundaries` publish mutation
  output. Running either edits the tree, which section 5 forbids this reader. F-6-01 is refuted
  without running one, because `--check` refuses the edit as inapplicable; F-6-08's arithmetic gap is
  reported as a gap rather than as a re-run.
- **`docs/JAVA_INTEROP.md`'s GraalPy timings.** No GraalPy on this machine. The import-path half of
  its claims was checked; the *runs* half was not.
- **Whether the three red gates are somebody's uncommitted work in flight.** I read one snapshot. The
  negative control at `18204a1` is what makes the finding safe to publish regardless.

**One environment hazard, recorded because it would produce a false finding.** `import acronymkit` on
this machine resolves to a **non-editable** copy in
`AppData/Roaming/Python/Python313/site-packages/acronymkit`, which has no `catalog` package. Every
probe in this document was run with `PYTHONPATH=src`. A reader who forgets that reports
`ModuleNotFoundError: No module named 'acronymkit.catalog'` and concludes the split is broken.
`docs/GATES.md:585` records this exact hazard biting before.

---

## 5. Drafted ledger rows

For whoever writes [`docs/cold-reads.toml`](../cold-reads.toml). `applied_by` must not be
`cold-read-6`.

```toml
[[reads]]
id = "2026-09-09"
reader = "cold-read-6"
rotation_served = "docs/SECOND-READER.md"
cursor_after = "docs/CLAIMS-LEDGER.md"
covered = [
  "CHANGELOG.md", "CONTRIBUTING.md", "README.md", "docs/ARCHITECTURE.md",
  "docs/CLAIMS-LEDGER.md", "docs/DEFINITION-OF-DONE.md", "docs/EVALUATION.md",
  "docs/GATES.md", "docs/GOVERNED_NAMING.md", "docs/JAVA_INTEROP.md",
  "docs/RELEASE_CHECKLIST.md", "docs/SOURCING.md", "docs/SECOND-READER.md",
]
```

`cursor_after` is entry eight of the twenty-five, `docs/CLAIMS-LEDGER.md`, by rotation order —
**not** by anything this reader chose. `F-5-3`, `F-5-5`, `F-5-6`, `F-5-7` and `F-5-8` each need
`reviewed_in = "2026-09-09"` or the gate reddens, and **all five reach their two-read limit at the
next read**, so `OPEN AND AT THE LIMIT` goes from `0 of 5` to `5 of 5` after this one is filed.

Ten findings, `F-6-01` to `F-6-10`. Proposed dispositions: all `open`, all `owner` as named per
finding. F-6-01 should be `fixed` if and only if the control fixture lands in the same commit as the
prose describing it.
