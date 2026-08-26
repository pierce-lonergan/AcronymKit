# The gate register — every CI check, and the evidence that it can fail

Four defects shipped in one round and every one was the same shape: **a check that could not fail in
the environment where it ran.** The claims gate could not fail in a checkout holding every file it
scans. The suite could not fail on a machine holding `data/` and `tools/`. The type checker could not
fail against a `click` predating `match`. `tests/test_splits_manifest.py` had never once executed in
the extracted tree, hiding a module behind a green `build` job. D-058 records all four.

None of the four was found by a gate. All four were found by the one environment that differed, and
in every case that environment was CI rather than a check. A green tick was being read as evidence
while nobody had established that the tick could go red.

This page is the answer to that, and the rule it serves is operating rule 11:

> A gate must be **demonstrated capable of failing in the environment where it runs.** Not locally.
> Not in principle. In situ, by mutation, with the failure captured.

The register itself is [`.github/gates.toml`](../.github/gates.toml). It is machine-readable and it
is validated — `python tools/gates.py --check` runs in the `lint` job, and
`tests/test_gate_manifest.py` mutation-tests the validator the same way
`tests/test_splits_manifest.py` mutation-tests the splits validator. A manifest nobody validates is a
paragraph.

---

## Read this before the table

**Thirteen of the thirty-six gates now carry in-situ evidence, and none of it was new work.**

The previous version of this page opened *"the count is zero"* and *"nothing in `gate-mutation.yml`
has ever run"*. The second sentence was false when it was written. That workflow had run — once, on
`2026-08-25`, green, with all five artifact bundles uploaded — and nothing in this repository had
ever looked at it. Every one of the thirteen automated gates came back `demonstrated` on
`ubuntu-latest` under CPython `3.12`, and `--check` went on printing `0 of 36` afterwards because
nobody had written a run id into the register. **Evidence that is produced and not recorded is
evidence nobody has**, and that is a worse failure than the one this page was built to describe: the
mechanism worked, the run was green, and the count stayed at zero for a whole phase.

```
python tools/gates.py --check                                -- command output
  gate manifest: 36 gate(s) across 21 environment(s) in 5 workflow file(s)
  mutation kind: automated 13, control 2, inline 8, manual 13
  demonstrable by this harness: 13 of 36, 0 of them still owed
  CARRYING IN-SITU EVIDENCE:   13 of 36
  top of the cost ranking:     3 of 3 demonstrated  (1 claims, 2 splits_manifest, 3 suite)
  in-situ quota: debt 23, ceiling 23 | 2 round(s) | M2-P4 (the first harvest) cut 13
                 (run 32808357572 at 3173126) | quota 3 per round, top 3 of the ranking
                 must be demonstrated
```

**The evidence is dated `2026-08-25`, taken at commit `3173126`, in run `32808357572`.** Every
demonstrated gate carries all three, because a run id says a demonstration happened and only the
commit says *which gate* was demonstrated. That run is one commit behind this page's own HEAD, and
`git diff 3173126 61cf933 -- .github/ tools/gates.py bench/splits.toml tests/test_splits_manifest.py
src/acronymkit/resources/ bench/results.json docs/GATES.md` is **empty**: not one byte of any gate's
command, or of any mutation's target, changed between the run and the register that records it.

The remaining `23` are the eight `inline`, thirteen `manual` and two `control` refusals. Not one is a
gate this harness can mutate, so the next payment is not more of the same — it is the heredoc
extraction that would close three of the eight at once.

**What is still open, stated where it cannot be missed.** This round edits `tools/gates.py`, and five
of the thirteen demonstrated gates run `tools/gates.py` as their command. Their evidence therefore
describes the previous revision of that tool. `gate-mutation.yml` triggers on pushes touching
`tools/gates.py`, `.github/gates.toml`, `.github/workflows/*.yml` and `tests/test_gate_manifest.py`,
so **the commit that lands this work re-takes the evidence on its own** — but until that run
completes, five rows here are one revision stale and the register does not currently say which. That
is the honest state and it is the first thing to attack.

---

## Which gate to fix first

`CARRYING IN-SITU EVIDENCE: 0 of 36` was printed on every CI run for a phase. The line was honest and
it was useless: it told a reader with one afternoon nothing at all about **which** gate to spend it
on. A count is not a plan.

So every gate now carries a `cost_rank` — a total order over the whole register, rank `1` being the
gate whose silent failure costs this project the most. It is a field in
[`.github/gates.toml`](../.github/gates.toml), not a paragraph here, and it is **derived rather than
asserted**: each gate declares two factors and `python tools/gates.py --check` refuses an ordering
that inverts them.

| factor | what it asks | values, worst first |
|---|---|---|
| `blast_radius` | how far the damage travels | `published_numbers`, `installed_behaviour`, `release_provenance`, `distribution_contents`, `evidence_apparatus`, `repository` |
| `silence` | how the failure announces itself **to this project** | `silent`, `delayed`, `loud` |
| `redundancy` | does another registered gate cover it | `sole`, `partial`, `covered` |

**`silence` is the D-058 axis and it is why the ordering is not just about severity.** All four
defects of that record were silent here and loud somewhere else. A gate whose inertness nobody would
notice costs more than one at the same blast radius whose inertness the next person to run anything
trips over — which is why `tier_zero_purity`, a gate whose failure breaks every zero-dependency
install, ranks below `suite`, whose failure ships a wrong answer that looks right.

**`redundancy` is declared, printed, and deliberately not part of the ordering.** As a third
lexicographic key it ranked `ngram_matches_lexicon` above the entire test suite — purely because the
suite is partly duplicated by `installed-suite` and the n-gram check is not. That is an ordering
nobody would defend, and **a factor that decides ranks nobody would defend is worse than one that
informs them.** Ties on `(blast_radius, silence)` are left free; inside a tie the order is judgement,
and each gate's `cost_if_inert` is where that judgement is written down and can be argued with.

```
python tools/gates.py --ranking                              -- command output, abridged to the
                                                                top and bottom of the order
  #  gate                             blast radius           silent?  other cover  evidence
  1  claims                           published_numbers      silent   sole         2026-08-25
  2  splits_manifest                  published_numbers      silent   sole         2026-08-25
  3  suite                            installed_behaviour    silent   partial      2026-08-25
  4  airgap_suite_under_guard         installed_behaviour    silent   sole         -  (manual)
  5  airgap_public_api_probe          installed_behaviour    silent   partial      -  (inline)
  6  schema_copies_match              installed_behaviour    silent   sole         -  (inline)
  7  ngram_matches_lexicon            installed_behaviour    silent   sole         2026-08-25
  8  import_ceiling                   installed_behaviour    silent   sole         -  (inline)
  ...
 21  claims_in_sdist                  distribution_contents  silent   partial      -  (manual)
 25  gate_manifest                    evidence_apparatus     silent   sole         2026-08-25
 35  ruff                             repository             loud     sole         2026-08-25
 36  ruff_format                      repository             loud     sole         2026-08-25
```

**Why `claims` is rank one, and why that is a positioning argument rather than a taste.**
[`docs/POSITIONING.md`](POSITIONING.md) commits this library to being a governance instrument, which
means the governed subsystem's numbers *are* the product. Every published number in this repository
is adjudicated by `tools/check_claims.py` and by nothing else; an invented figure that gets past it
reads exactly like a measured one, ships in the sdist, and is quoted onward. `splits_manifest` is
rank two for the same reason one step back — it backs the *declarations* every headline number stands
on, and a contaminated corpus wearing the `held_out` role produces a figure that looks identical to
an honest one.

**The most attackable judgement in this ordering, named rather than buried.** Every positive control
is `evidence_apparatus` and therefore ranks in the twenties, below gates whose defects reach a user.
The argument is that a rotted control is *necessary but not sufficient* for the protected defect to
ship: `airgap_namespace_control` going inert does not by itself put a network call in the package, it
removes the thing that would have caught one. A reader who holds that a control which has stopped
controlling costs exactly what the gate behind it costs is making an argument this ranking rejects
with a reason rather than by omission — and if that reader is right, `gate_manifest`, at rank `25`,
is badly under-ranked, because it is the only rule in this repository that checks the register
against the tree.

---

## The quota, and the two doors it has to close

A count with no rate attached is a backlog with better manners. `0 of 36` was printed on every CI run
and nothing about that line obliged anybody to move it, which is exactly what
[`docs/CLAIMS-LEDGER.md`](CLAIMS-LEDGER.md) says about an honest ledger with no trajectory. So the
in-situ count now has a quota, built the way `tools/check_claims.py`'s `MIGRATION_QUOTA` is built:
`IN_SITU_TRAJECTORY` in [`tools/gates.py`](../tools/gates.py) is a list of rounds, the last row must
equal the live register, and `--check` refuses the register when it does not.

**The quota is a ceiling on the debt, not a floor on the coverage, and that is the whole design.**
A floor on `in_situ` is satisfied by a round that adds five gates and demonstrates none: the floor
holds, `13 of 36` quietly becomes `13 of 41`, and the register reports health while going backwards.
A ceiling on `gates - in_situ` cannot be satisfied that way, because a gate added without evidence
raises the debt by one.

That failure mode has **two** doors and both are shut. Measured, on this tree, one mutation at a
time, with the file restored from bytes read before the first mutation and md5-verified:

```
a 37th gate is appended to .github/gates.toml, carrying no evidence     -- command output
python tools/gates.py --check                                              rc=1

  -   IN_SITU_TRAJECTORY['M2-P4 (the first harvest)']
    says the register holds 36 gate(s); it holds 37.
    Adding or removing a gate IS a round. Append an InSituRound in the same
    commit, and it may not raise the debt.
```

```
...and the round is appended to cover it, with a waiver attached          -- command output
python tools/gates.py --check                                              rc=1

  -   IN_SITU_TRAJECTORY['probe round']
    the in-situ debt ROSE from 23 to 24 (36 gates and 13 demonstrated, then 37
    and 13). A round that adds gates without adding evidence may not satisfy
    this quota: the count would go backwards while the coverage number looked
    healthy. Demonstrate the new gate, or pay for it by demonstrating another.
```

**The debt rule and the top-of-ranking rule are not waivable. The rest are.** A rule with no escape
gets deleted the first time it is inconvenient; one with a named escape gets argued with. So a round
that pays less than the per-round quota may record a waiver, and so may a round that adds an
`automated` gate it could not run in CI in the same commit — but no waiver lets the debt rise, and no
waiver excuses a gate in the top three of the ranking carrying no evidence.

**This is deliberately harsh and it will bite.** The demonstrable set is now exhausted: all thirteen
`automated` gates are demonstrated, and the twenty-three that remain cannot be mutated by this
harness at all. A future round that adds a `manual` gate — a new release check, say — has to pay for
it by extracting an inline gate into a script and demonstrating that. **The currency the quota
creates is exactly the fix this page has been naming and not doing since it was written**, and three
of the eight inline gates go together in one afternoon's work.

### The rest of the battery

Seven more mutations of the live register, one at a time, each restored:

```
python tools/gates.py --check, eight runs against .github/gates.toml   -- command output
one mutation each, the file restored from bytes read first and md5-verified

  rc=0  control, unmutated
  rc=1  A  the top-ranked gate loses its in-situ evidence
  rc=1  B  a 37th gate is added and nothing is demonstrated for it
  rc=1  C  claims is ranked last and ruff_format first
  rc=1  D  a gate loses its cost_rank
  rc=1  E  a gate declares a blast radius that is not one
  rc=1  F  a gate loses its cost_if_inert
  rc=1  G  an in-situ date loses its commit
```

Case `A` is the one worth reading in full, because it fires three rules at once and each says
something different:

```
  -   IN_SITU_TRAJECTORY['M2-P4 (the first harvest)']
    says 13 gate(s) carry in-situ evidence; 12 do.
  -   gates.claims ranks 1 of 36 by cost-if-inert and carries no in-situ evidence.
    The top 3 of the ranking must be demonstrated where they run.
  -   1 gate(s) this harness can mutate carry no in-situ evidence: ['claims'].
    Their own commands are runnable on a runner today, so this is a debt and not a limit.
```

Case `C` is the ordering rule: swapping the ranks of `claims` and `ruff_format` is refused not
because somebody dislikes it but because it inverts the declared factors —
*"(published_numbers, silent) against (repository, loud)"*. Moving a gate up this list costs an
argument in a field rather than a nudged integer.

**Where this battery was run, and what that costs.** On a developer machine, which is precisely the
evidence rule 11 says does not count. Every rule above is also mutation-tested in
`tests/test_gate_manifest.py`, which runs inside `gates.suite` — and `gates.suite` *does* carry
in-situ evidence, so the tests have a runner behind them even though this table does not. The
validator rules themselves have never executed on a runner in the form shipped here. The push that
lands this work is what fixes that, and until it completes this section is a local demonstration
wearing an in-situ page's clothes.

---

## What the register holds

Per gate: the environment it runs in, the workflow and step it *is*, what it detects, what it is
blind to, and its mutation — either an edit this harness can apply and revert, or a refusal carrying
a disposition. Per environment: what that place **holds** and **lacks**, written as path globs rather
than prose, so `python tools/gates.py --assert-environment <name>` can check them.

The two-direction check on that is the cheapest evidence on this page:

```
python tools/gates.py --assert-environment test              -- command output, one tree, twice
  data/ present   3 premise(s) do not hold here          rc=1
  data/ absent    holds 4 declared path(s), lacks 3 -- this is that environment   rc=0
```

That last point is the one that had never been done here. Every gate rests on an unstated premise
about where it runs, and D-058 is three defects that came from the premise being wrong: the developer
machine had `data/`, had `tools/`, and resolved an older `click`. The `air-gap` job has opened with
*"Prove the network namespace really has no route"* since it was written — because, in its own words,
a runner where `unshare` silently did nothing would turn every later step into a tautology that
passes. **That was the only positive control in the repository.** It is now generalised, and the
`test` job carries the second one.

### The counts, by disposition

```
python tools/gates.py --list | tail                          -- command output
  automated  13    an edit this harness applies, runs the gate's own command against, and reverts
  inline      8    the gate is a heredoc inside a workflow; there is no command to invoke
  manual     13    mutable only in an environment this harness cannot create
  control     2    the step IS a positive control; mutating a control is a different task
```

Eight jobs carry no gate at all and each one says why in the register — two third-party analyses
whose rule sets this repository does not define, four upload-and-attest steps that assert nothing
about the tree, and two jobs of the mutation harness itself.

**Eight of the thirty-six are refused for one architectural reason and it is worth naming.** A gate
whose implementation is a heredoc inside `ci.yml` has no command a runner can invoke, so a mutation
harness could only ever run a *copy* of it — and D-018 already settled that a pattern describing the
bug cannot be used to test for the bug. The fix is to extract those heredocs into scripts the way
`tools/splits.py` was extracted, and it is not done. Three of the eight — the schema-copy digest,
Tier 0 purity and the import ceiling — would be closed by the same afternoon's work.

**Ten of the thirteen automated mutations have been run, and every one was demonstrated.** They are
the ones a developer machine can reproduce:

```
python tools/gates.py --mutate-environment lint              -- command output, on a laptop
  claims           DEMONSTRATED  mutated rc=1, restored rc=0
  gate_manifest    DEMONSTRATED  mutated rc=1, restored rc=0
  mypy             DEMONSTRATED  mutated rc=1, restored rc=0
  ruff             DEMONSTRATED  mutated rc=1, restored rc=0
  ruff_format      DEMONSTRATED  mutated rc=1, restored rc=0
  splits_manifest  DEMONSTRATED  mutated rc=1, restored rc=0

python tools/gates.py --mutate-environment resources
  ngram_matches_lexicon  DEMONSTRATED  mutated rc=1, restored rc=0
  resource_formats       DEMONSTRATED  mutated rc=1, restored rc=0
  schema_copies_match    SKIPPED (inline)

python tools/gates.py --mutate control_always_red   /   --mutate control_always_green
  control_always_red     DEMONSTRATED  mutated rc=1, restored rc=0
  control_always_green   DEMONSTRATED  mutated rc=0, restored rc=0
```

The mypy row is the one to read twice: the probe is not synthetic. It is
`Path.write_text(newline=...)`, which is 3.10-only and which shipped through this gate while
`python_version` was set to `"3.10"`. It fails only while the 3.9 floor is really in force, so it
demonstrates the gate *and* the setting the gate depends on — the part that had silently changed.

**The three that were not run are the three that cannot be run here**, and that is the register
working rather than a hole in it: `suite` and `test_environment_control` both turn on `data/` being
absent, and `harness_lint_environment` asserts a premise a developer machine does not satisfy. Two of
the three were measured another way, in the two sections below.

None of the ten is in-situ evidence. They were taken on the machine rule 11 exists to distrust. The
resource pair was run against the real bundled files, and both were restored byte-identically —
checked by digest, not by the harness's own word.

---

## How many known defects each gate actually catches

This is the shape of record every gate should carry, and the reason it is a table rather than a
sentence: D-050 retired an AST guard on the premise that `installed-suite` subsumed it *by
construction*, and the premise was false on that record's own printed table.

Five real breakages, each with a real fix commit. Every one was reintroduced on a clean
`git archive HEAD` export, a real sdist was built from it, and both environments were run through
their literal command sequences. **These numbers were re-measured for this page, not copied.**

```
python tools/gate_packaging_mutation.py --out artifacts/packaging     -- command output, abridged
case    test -f   extracted tree    installed-suite   label
control passes    passes            passes            unmutated control
a       FAILS     FAILS             passes            bench/results.json out of the sdist
b       FAILS     passes            passes            data/LICENSES.md out of the sdist
c       passes    FAILS             FAILS             tests/fixtures/* out of the sdist
d       passes    FAILS             FAILS             test_governed_gold.py loads bench/ unguarded
e       passes    FAILS             passes            test_splits_manifest.py, same defect

build/extracted tree catches 4 of 5
installed-suite catches      2 of 5
unmutated control: green in both environments
```

The control line is not decoration. A broken checkout produces five *caught* verdicts and reads as a
triumph — which is exactly how three of D-050's measurements came out wrong the first time, against
artifacts a stale `SOURCES.txt` had made unmutated. The script sweeps every `*.egg-info` before it
builds, for that reason and no other.

The `test -f` column is a third gate on the same step, and splitting it out is a finding rather than
tidiness: one YAML step runs a list of filenames *and* a whole pytest run, the two have different
coverage — two of five against four of five — and registering the step as one gate would have
published a single number true of neither. **The register's unit is the assertion, not the step.**

**D-050's two-of-five and four-of-five reproduce exactly.** Re-measured on 2026-08-24 against commit
`a62f99a`, Windows, CPython 3.13 — the same platform limitation D-040 and D-050 both carried, and
`gate-mutation.yml`'s `packaging-gates` job is what ends it.

### It did not end it. The job ran, measured nothing, and was green

The worst finding of this round, and it is in the harness rather than in the gates it watches.

```
run 32808357572, packaging-gates, ubuntu-latest        -- captured artifact, verbatim
case    test -f   extracted tree    installed-suite   label
control SDIST BUILD FAILED
a       SDIST BUILD FAILED
b       SDIST BUILD FAILED
c       SDIST BUILD FAILED
d       SDIST BUILD FAILED
e       SDIST BUILD FAILED

build/extracted tree catches 0 of 5
installed-suite catches      0 of 5
unmutated control: NOT GREEN -- every verdict above is void

  pyproject_hooks._impl.BackendUnavailable: Cannot import 'setuptools.build_meta'
```

**Every build failed, the script returned `1`, and GitHub marked the job successful.** Two causes,
each of which alone is the shape this page exists to catalogue:

- **`tools/gate_packaging_mutation.py` passed `--no-isolation`.** `ci.yml`'s `build` job and its
  `installed-suite` job both run a plain `python -m build`, with isolation. So the reproduction had
  drifted from the gate it reproduces — the exact cost this register records beside
  `gates.installed_expected_non_passing` and `gates.sdist_file_list`, realised. A developer machine
  has `setuptools` in site-packages and a runner on `3.12` does not, which is why it had never
  failed here. That is D-058's cause two with a different dependency.
- **`gate-mutation.yml` piped the script through `| tee`.** GitHub's default shell for `run:` on
  Linux is `bash -e {0}` — `-e` is set, `pipefail` is **not** — so the pipeline's exit status was
  `tee`'s. A non-zero return was discarded by a line added to keep a copy of the output.

Both are fixed here: the build command is now the gate's own command, and the step captures the
status explicitly (`|| status=$?`, because a bare `status=$?` on the next line never runs under
`-e`). The script also now refuses any run in which a case produced no sdist, separately from the
control check, because **a case that could not be built is not a case that was measured** — the table
above was not merely wrong, it was a number about a build that did not happen.

**The totals in this section have therefore still never been re-derived on a runner.** They stand on
the 2026-08-24 Windows re-measurement, and one attempt to re-derive them locally with the fixed
command was refused by the script's own control:

```
python tools/gate_packaging_mutation.py --only a          -- command output, 2026-08-25, Windows
case    test -f   extracted tree    installed-suite   label
control passes    passes            FAILS             unmutated control
a       FAILS     FAILS             FAILS             bench/results.json out of the sdist
unmutated control: NOT GREEN -- every verdict above is void        rc=1

  unexpected non-passing:
    tests/test_generator.py::test_output_is_identical_across_hash_seeds
```

That test passes in a checkout on this machine and passes on ubuntu in CI, which was green on the
same commit. It is **one observation on one platform on a machine several agents were running suites
on at the time**, so it is reported and not diagnosed. What it demonstrates cleanly is the control
doing its job: no coverage number was published from that run, because the run had no right to
publish one.

### One reason changed, and the reason is the finding

`installed-suite` still misses breakage `e`, and **it misses it for a different reason than D-050
recorded.**

D-050 attributed the miss to the file-keyed `EXPECTED_NON_PASSING` entry: while a *file* sits on that
list the job cannot see a second defect anywhere in it. D-058 deleted both file-keyed entries and
replaced them with narrow module-level skips, and closed by calling that *"the argument for shrinking
the list"*. The list did shrink. Here is what the installed-suite log says with `e` reintroduced:

```
installed-suite, breakage e reintroduced                     -- command output
  SKIPPED [1] tests/test_splits_manifest.py:133: tools/ is not part of an
              installed distribution; these tests belong to a checkout
  ... same pass, skip, failure and error counts as a clean run
```

The skip fires at line 133. The unguarded load is at line 143. The module never reaches it. **The
blind spot moved from a list of names in `ci.yml` into a skip condition in the test file.** Same
shape — one absorbing condition upstream of the defect — and, as with the original instance, the run
is byte-for-byte indistinguishable from a clean one in its counts.

That is not an argument against the narrow skips. They are strictly better than the file-keyed
entries, because any *other* error in that file now reaches the job. It is an argument against
reading *"the list shrank"* as *"the coverage grew"*. It did not grow. It was two of five before and
it is two of five after.

---

## The one measurement that shows what R11 is actually about

Every other number on this page is coverage. This one is the rule itself, in two runs of one command
on one tree, differing only in whether a directory is present.

`gates.suite`'s declared mutation restores D-058's cause one exactly: a control that asserts on the
path `_sdu22_ae_source` *returns*, rather than on the filename both of its outcomes name. The
docstring above that control already said the refusal fires *"before the path is resolved"*; the code
underneath needed the corpus on disk.

```
one clean export of HEAD, one mutation, two environments        -- command output
python -m pytest tests/test_splits_manifest.py
  data/ present   (a developer machine)   88 passed
  data/ absent    (a CI runner)           1 failed, 87 passed
                  FAILED TestTheRealManifest::test_the_reader_that_would_spend_the_allocated_arm_is_wired
```

**Same tree, same suite, same defect, opposite verdicts.** On a developer machine the gate is inert
against this defect and reports success; on a runner it fires. Nobody was wrong about the code, and
no local gate could have said so — that is the whole of rule 11 in one table, and it is why a
mutation demonstrated on a laptop is not evidence about a gate that runs on a runner.

This measurement is also the prediction `gate-mutation.yml`'s `test-gates` job exists to check: it is
written into the register in advance that `gates.suite` must come back `demonstrated` there and
`INERT` locally. **A run in which the two agree is the finding**, in whichever direction it goes.

### The prediction was checked. It held, and the run found something it did not cover

```
run 32808357572, ubuntu-latest, CPython 3.12.14, data/ absent, mutation applied
                                                             -- captured artifact
  2 failed, 4861 passed, 11 skipped, 1 xfailed in 60.57s        mutated,  rc=1
                                                                restored, rc=0
  FAILED tests/test_splits_manifest.py::TestTheRealManifest::
         test_the_reader_that_would_spend_the_allocated_arm_is_wired
         SystemExit: missing .../data/sdu22_ae_legal_dev.json
```

That is the predicted failure, by name, in the predicted environment. **The second failure in that
run is not predicted anywhere, and it makes the demonstration confounded:**

```
  FAILED tests/test_gate_manifest.py::TestTheRegisterThisRepositoryShips::
         test_it_validates -- assert ['gates.suite...ne described'] == []
```

The probe edits `tests/test_splits_manifest.py` — which is the very file `gates.suite`'s register
entry anchors on — so the register's own validator correctly reports that the anchor no longer
matches. The suite would have gone red on that test **even if the D-058 defect had not been
restored**, so `rc=1` on its own does not establish that this gate catches this defect. What
establishes it is the named `FAILED` line above. *Take the evidence from the line, not from the
verdict.* A probe that does not edit a file the register anchors on would fix it; that is not done.

---

## The two ad-hoc checks, promoted and withdrawn

D-058 closes by naming two checks that existed only in a transcript: the suite run with `data/` moved
aside, and the suite run with `tools/` moved aside. *"Making either a gate is not done."* Both were
measured before deciding what to do with them, and they went different ways.

### `data/` moved aside — promoted, but not as a new job

```
suite run in a clean export, one directory moved aside at a time    -- command output
  full tree           4734 passed, 10 skipped, 1 xfailed     rc=0
  data/ aside         4734 passed, 10 skipped, 1 xfailed     rc=0     identical
  tools/ aside           2 failed, 4445 passed, 14 skipped   rc=1
  bench/ aside           2 failed, 4528 passed, 214 skipped  rc=1
  tools/ + bench/ aside  1 failed, 4348 passed, 112 skipped  rc=1
```

`data/` is fetched and never committed — only `data/LICENSES.md` is tracked — so **every one of the
fifteen `test` matrix cells is already a suite run with the corpora absent.** The transcript check was
a local *reproduction* of a CI condition, not a missing CI gate, and adding a job for it would have
been a check that cannot fail independently of the one beside it, which is the sin this whole page is
about.

What was genuinely missing was the assertion that the condition holds. That is now a step:

```yaml
      - name: This runner is the environment the register says it is
        run: python tools/gates.py --assert-environment test
```

It runs in eleven of the fifteen cells. It is skipped on 3.9 and 3.10 because `tools/gates.py` needs
a TOML parser, `tomllib` is 3.11+, and `tomli` is not a declared dev dependency — one line in
`pyproject.toml` closes that, and `pyproject.toml` was not this workstream's file. The hole is
registered rather than left to be discovered.

### `tools/` moved aside — the claim is withdrawn

A checkout minus `tools/` is **not an environment anything ships to.** The real environment is
`installed-suite`, whose run directory lacks `tools/` *and* `bench/` *and* `src/` *and* `MANIFEST.in`,
and that job is now covered by `gate-mutation.yml`'s packaging job. Measured on the current tree, a
checkout minus `tools/` is red for two reasons that are both checkout-property artefacts rather than
defects.

And it rotted, which is the point:

```
suite with tools/ and bench/ both moved aside     -- command output, two commits
  at 4f812e1   4348 passed, 112 skipped, 1 xfailed   rc=0     zero failures
  at a62f99a   1 failed, 4348 passed, 112 skipped    rc=1
```

D-058 recorded that configuration as `4348` passed, `112` skipped, zero collection errors — and that
is **exactly right**, to the digit, at the commit it was taken on. One commit later it is red, and
nothing noticed, because the check exists only in a transcript. The failing test is
`tests/test_packaging_manifest.py::test_every_file_the_claims_gate_reads_is_shipped_by_the_manifest`,
added in `a62f99a` — the very commit that fixed the previous instance of *a check that cannot fail
where it runs*. It expands `check_claims.SCAN_GLOBS` against the tree and treats a glob matching
nothing as an error, which is correct behaviour in a checkout and a false positive in a tree with
`bench/` removed. The fix is the same narrow guard D-058 used, in a file this workstream did not own.

---

## The claims gate's hole: measured, costed, and not closed

The gate at rank one is **demonstrably partly inert**, and has been since before it was ranked. An
uncited latency figure in microseconds exits `0`; an uncited accuracy percentage in the same position
exits `1`. D-060 found it, [`docs/POSITIONING.md`](POSITIONING.md) reproduced it on a second page,
and `tests/test_claims_gate_coverage.py` pins it so it cannot quietly change. Two vocabulary gaps
cause it: `latency` is not a metric keyword, and a spelled-out `microseconds` is not a unit.

D-052 refused to widen the arming rules, on the ground that arming on everything would relabel over a
thousand numbers nobody had adjudicated. **A narrow widening is a different object, and it was
measured before anybody argued about it** — because the deferred ledger is a ratchet that may not
grow, so a widening that armed even one new uncited number would either redden the build or force a
baseline upward, and the trajectory forbids the second.

```
tools/check_claims.py loaded by path, its arming rules replaced, collect_claims
re-run over all 64 scanned files -- command output, not a benchmark measurement

  control (shipped rules)     1828 claim-shaped numbers
                              unarmed 1549 | unit-armed 191 | keyword-armed 88
                              unexamined 1549 | deferred 213 | value-matched 64 | allowlisted 2

  + latency, duration as keywords            0 numbers change class
  + microseconds/milliseconds/nanoseconds
    as units                                 0 numbers change class
  + both                                     0 numbers change class

  positive controls on that comparison, because a comparison that cannot detect a
  difference reports zero for either reason:
  + the word "the" as a keyword             617 change class
  + a unit rule matching anything          1526 change class
```

**The measured price of closing this hole is zero.** It would fail no build and grow no ledger.

**And the firing count of the new vocabulary on this tree is zero, which means I measured nothing
about whether the widened rule is well calibrated.** Not one prose number in any scanned file sits
within the proximity window of `latency` or `duration`, and not one is followed by a spelled-out time
unit. What the measurement establishes is that *this tree contains no latency-shaped claim*; it
establishes nothing about how the widened rule would behave on a tree that did.

### So it is refused, and here is the disposition

**Blocked on ownership of six documents.** The widening is one edit to `tools/check_claims.py`. What
it costs is that six shipped files immediately state something false:

| file | what it says today |
|---|---|
| `README.md` | *"latency in microseconds passes untouched while one naming an accuracy percentage in the same position"* fails |
| [`docs/EVALUATION.md`](EVALUATION.md) | *"an uncited latency in microseconds passes and an uncited accuracy"* percentage does not |
| [`docs/DEFINITION-OF-DONE.md`](DEFINITION-OF-DONE.md) | prints a battery whose latency row is `rc=0` |
| [`docs/POSITIONING.md`](POSITIONING.md) | prints a battery whose row `D` is `rc=0` |
| [`docs/SECOND-READER.md`](SECOND-READER.md) | describes the same injection returning zero |
| [`docs/DECISIONS.md`](DECISIONS.md) | D-060 is the record of the blind spot; D-070 and D-072 re-quote it |

Three of those print a **measured** mutation battery whose `rc=0` row would invert. None of the six
belongs to this workstream, and correcting a published measurement in a file assigned to somebody
else is how two copies of one sentence end up disagreeing — the shape this repository has now hit
five times. Widening without correcting them would leave six documents making a false claim about a
gate, which is precisely the class D-060 exists to record.

**What ships instead is the measurement, pinned so the refusal cannot go stale.**
`tests/test_claims_gate_coverage.py` now re-derives the zero on every run, with its own positive
control beside it. If a later round writes a latency figure into a scanned document, the widening
stops being free, that test goes red, and the decision is re-taken rather than inherited.

### The blind spot, observed in anger rather than by injection

While the measurement above was being taken, it reported **one** number moving, in `README.md` at
line `716`:

```
Median latency for a governed expansion fell to 41 microseconds in this release.
```

That sentence is `tests/test_claims_gate_coverage.py`'s own probe, left in the working tree by two
runs of that module interleaving — each restoring bytes it had read while the other's injection was
live. It sat on the front page of this library, and:

```
python tools/check_claims.py                                 -- command output, 2026-08-25
  rc=0
  every checked number is backed by bench/results.json, a citation, or the allowlist
  ... and README.md is not named anywhere in the output
```

**Every gate in this repository was green with an invented performance figure on its front page.**
It was found by a widening measurement noticing an extra armed number, not by anything watching for
it, and it was removed by the other process's restore before it could be committed. Three guards were
added to that helper in response — it refuses to start when a marker is already present, it checks
its own marker is gone afterwards, and a standalone test asserts the front page carries no leftover —
and none of them is the real fix. The real fix is the widening above, which is blocked.

**And the same confound as `gates.suite`'s, found here for the third time in one round.** Those two
injection tests read the claims gate's whole-process exit code as a statement about one injected
sentence. That inference holds only while the *unmutated* tree exits zero. It did not, twice, on
`2026-08-25`: an unrelated workstream added a decision record, `RECORD_FILE_PIN` went stale, the gate
exited `1`, and the blind-spot test announced *"the claims gate now catches an uncited
latency-in-microseconds figure"*. It does not. Both tests now take an unmutated control first and
**skip** when it is red — the `UNRESTORED` verdict of `tools/gates.py`, applied to a test — and they
skip again when the injected sentence is no longer on disk when the gate finishes, because then the
exit code is about somebody else's tree. **An exit code standing in for a specific claim is this
round's most repeated defect: once in `gates.suite`'s in-situ demonstration, twice here.**

The widening measurement above was rewritten for the same reason and does not use exit codes at all:
it reads each scanned file **once** and evaluates both rule sets against the same bytes, so there is
no window in which the tree can move between the two halves. It also compares *arming* rather than
*backing*, which is the tighter statement — a rule that arms nothing new cannot move anything into
any backing class. What none of this fixes is two copies of the injection test running at once
against one checkout: the guards turn that into a skip rather than a false red most of the time, and
`bash`-level serialisation is not attempted. On a runner there is one process and the question does
not arise.

---

## This page's own deliverables, run in the environments they will run in

The four defects that started this were all *new work that had never executed where it would run*.
So the new work here was executed there first, before being claimed.

```
one export of HEAD plus this workstream's files, nothing else   -- command output
  new tests collected     51
  checkout                4784 passed, 11 skipped, 1 xfailed   = 4734 + 50; the 11th skip is
                                                               the optional PyYAML cross-check
  extracted sdist tree    4647 passed, 148 skipped             43 of the 51 run there; 8 skip
  installed-suite         4339 passed, 117 skipped,
                          4 failed, 2 errors                   exactly the six on
                                                               EXPECTED_NON_PASSING, and no more
```

The isolation is deliberate: `git archive HEAD` plus this workstream's seven files, so the counts
attribute to this work and not to the four other workstreams editing the same tree in the same
session — the weakness D-057 named about its own second sweep.

**Those counts are one round old and this round did not re-take them.** `tests/test_gate_manifest.py`
now collects `79` rather than `51`, and `tests/test_claims_gate_coverage.py` collects `8` rather than
`5`; the extracted-tree and installed-suite splits below were not re-measured against the new files,
because the only local instrument for that is `tools/gate_packaging_mutation.py` and its control
would not go green on this machine — see the packaging section above. Every sentence in this section
that names a number is therefore a statement about the previous round's files, and is marked here
rather than quietly carried.

Three things that had to be checked rather than reasoned about:

* **`tests/test_gate_manifest.py` skips at module level in `installed-suite`,** on one named
  condition, placed *before* the load — because a `skipif` mark is consulted at collection and a
  module body runs at import, which is the lesson of the fourth and fifth historical breakages.
  `EXPECTED_NON_PASSING` was **not** grown, and the run above is the evidence.
* **Eight of its fifty-one tests skip in the extracted tree and forty-three run** — seven on the
  narrow `needs_register` mark, one on the optional PyYAML cross-check, and nothing else. A
  module-wide blanket is what hid seventy-four tests in `tests/test_splits_manifest.py` for as long
  as that file existed; the mark here is narrow for that reason, and the split was measured rather
  than intended.
* **The two harness controls behave in opposite directions**, which is the only thing standing
  between the whole register and a harness that reports success for everything:

```
python tools/gates.py --mutate control_always_red      -- command output
  control_always_red     DEMONSTRATED   mutated rc=1, restored rc=0
python tools/gates.py --mutate control_always_green
  control_always_green   DEMONSTRATED   mutated rc=0, restored rc=0
```

---

## Where the regress stops, and why there

A register of mutation artifacts is itself a check, and it will rot the same way everything else here
rotted — by passing where it cannot fail. So:

* **Level 0** — the gates. Registered, each with what it detects and what it is blind to.
* **Level 1** — a mutation per gate, run in that gate's environment by `gate-mutation.yml`, with the
  captured failure uploaded as a workflow artifact. `INERT` is the finding: the gate ran against a
  tree carrying the defect it exists to catch and did not fail.
* **Level 2** — the register's own mutation. `gates.gate_manifest` appends an **unregistered job** to
  `ci.yml` and requires `--check` to refuse it. That is deliberately the rule that checks this file
  against the *tree* rather than against itself; every other rule in it could rot together and still
  agree with itself.
* **Level 3** — two synthetic controls on the harness's detector, run first on every scheduled run.
  `control_always_red` must come back `demonstrated`; `control_always_green` mutates a comment and
  must come back `INERT`. A harness that has rotted into reporting success for everything passes the
  first and fails the second.

**It stops at level 3, and the judgement is this: that is the first level where the alarm reaches a
person.** A failed control reddens the scheduled run, and a red run is visible in the Actions tab to
anyone who looks. Another check above it would only move the question one step further from the human
who has to act on it.

**The regress is not closed and this page does not pretend it is.** A scheduled workflow that stops
running altogether raises nothing — GitHub disables `schedule` triggers after sixty days of repository
inactivity, and no check here would notice. `--check` prints the age of the newest in-situ
verification as a *note*, never a failure, for the reason `tools/splits.py` gives about its own
staleness window: a gate that turns red with the passage of time fires on an unrelated commit.

---

## Running it yourself

```
python tools/gates.py --check                       validate the register (the CI gate)
python tools/gates.py --list                        the register as a table
python tools/gates.py --ranking                     cost if inert, worst first
python tools/gates.py --json                        the register as JSON
python tools/gates.py --assert-environment lint     is this machine that environment?
python tools/gates.py --mutate mypy                 one mutation, applied and reverted
python tools/gates.py --mutate-environment lint     every automated mutation of one environment
python tools/gate_packaging_mutation.py --out DIR   the five historical breakages, against a real sdist
```

`--mutate` edits the working tree and puts it back. It writes the previous bytes of every file it
touches before touching it and restores them in a `finally` block, and then re-runs the gate to
confirm a zero exit — because without that second half, a gate failing for an unrelated reason reads
as a successful demonstration.

---

## How this page fails

**The lead item is at the top and it is not a footnote: twenty-three of the thirty-six gates carry no
in-situ evidence, and none of them can.** Every one is an `inline`, `manual` or `control` refusal that
this harness cannot mutate. So the number that just moved from zero to thirteen is the number of
gates that were *always* demonstrable, and the honest reading of `13 of 36` is not *"a third of the
way"* — it is *"all of the easy ones, and the remainder needs a different kind of work"*. The quota is
built so that remainder is the only currency left, which is a mechanism and not yet a payment.

**The previous version of this page said `gate-mutation.yml` had never run, and that was false when
it was written.** It had run — green, artifacts uploaded, `13` demonstrations captured — and this page
went on asserting a zero for a whole phase. Nothing detected the contradiction, because nothing in
this repository reads a run log. That is worth more attention than the count it corrected: **the
failure mode here is not that the mechanism does not work, it is that its output goes unread.** The
`report` job now prints how to record a run, which is a nudge and not a gate. A scheduled workflow
whose artifacts nobody harvests is indistinguishable from one that never ran, and nothing here
closes that.

**Five of the thirteen demonstrated gates run `tools/gates.py`, and this round edited it.** Their
evidence describes the previous revision of that tool. The workflow's `paths:` trigger re-takes it on
the landing commit, and until that run completes those five rows are one revision stale — with no
field in the register saying so and no check that could notice.

**The packaging job reproduces two gates rather than invoking them, and that drift has now cost a
whole run.** `build`'s sdist step and the whole `installed-suite` job are multi-step sequences with no
single command, so `tools/gate_packaging_mutation.py` rebuilds the sequence. A reproduction is not
the gate: somebody edits `ci.yml` and not the script, and the two drift with nothing to say so. This
page used to list that as a risk. It is now an incident — `--no-isolation` against `ci.yml`'s plain
`python -m build`, invisible on a developer machine, fatal on a runner. One piece is guarded, the
script re-reads `EXPECTED_NON_PASSING` out of `ci.yml` and reports drift from its own copy; the build
command is now identical to the gate's by inspection and by nothing else. **A third divergence of the
same kind would be found the same way: by somebody reading a log.**

**The ranking is a judgement with a validator attached, not a measurement.** `cost_rank` is refused
when it inverts its declared factors, and the factors themselves are asserted rather than measured.
Nobody has counted what a silent `ngram_matches_lexicon` failure actually costs against a silent
`import_ceiling` one, and no data in this repository could settle the order of ranks `6` through `9`.
What the mechanism buys is that moving a gate costs an argument in a field; what it does not buy is
that the argument is right.

**The quota can be paid by deleting checks, and arithmetic cannot tell that from progress.** Removing
an undemonstrated `inline` gate lowers `gates - in_situ` exactly as demonstrating one does. A shrinking
register now needs a waiver naming the gate that left and why — which is a sentence somebody writes,
graded by nobody. It converts a silent repudiation into a visible one and does no more than that.

**Eleven gates are `manual` and four of those are release-only.** They are declared, and declaring a
gate is not demonstrating it. The version guard has failed in anger once (`48baa86`), so it is not
undemonstrated so much as undemonstrated-on-a-schedule; the SBOM and checksum gates have no such
record and are taken on faith.

**The workflow scanner is a scanner, not a YAML parser.** It keys off indentation — two-space job
keys, `- name:` at six spaces. A workflow written another way would scan to nothing and make every
rule built on it vacuously true, which is the exact defect being catalogued. `validate()` refuses a
workflow that scans to zero jobs. There is a second anchor and it is opportunistic rather than
guaranteed: when PyYAML happens to be installed, a test compares the scanner's job set against a real
parser's on all five workflow files, and they agree today. PyYAML is not a dev dependency and adding
one so a validator can read four files is a worse trade than a scanner that says what it is — so on a
runner without it, that anchor is a skip.

**`.github/gates.toml` is not shipped in the sdist, and this page is.** `MANIFEST.in` ships
`recursive-include docs *.md` and `.github/workflows/*.yml`, and nothing else from `.github/` — so a
reader holding a distribution gets this page, follows its link to the register in the second
paragraph, and finds nothing. That is precisely the `data/LICENSES.md` shape: a shipped document
citing evidence the artifact omits, which `MANIFEST.in`'s own comment already enumerates four
instances of. The tests in `tests/test_gate_manifest.py` that read the register skip there on a
narrow `needs_register` mark rather than erroring, which is the right behaviour and not a fix — how
many of them there now are was not re-measured this round, for the reason given above. `MANIFEST.in`
was not this workstream's file; one line adds it, and until somebody writes that line this is the
fifth instance.

**The register is not scanned by the claims gate.** `tools/check_claims.py` scans `bench/splits.toml`
and not `.github/gates.toml`, so any number written into the register is unchecked. This page is
scanned; the register it describes is not.
