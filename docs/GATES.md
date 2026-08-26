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

**Twelve of the thirty-six gates carry in-situ evidence, and the count went DOWN this round.**

The previous version of this page opened *"Thirteen of the thirty-six"*. One of the thirteen was
`gates.suite`, the highest-ranked gate this harness can mutate at all, and **its evidence has been
withdrawn.** Not because the gate was found inert — because the verdict that recorded it was
measured to be reachable with the defect uncaught, in both environments, so it could not have come
back `INERT` for any tree. A check that cannot fail, inside the harness built to catalogue checks
that cannot fail. The measurement is in *[The verdict that could not go red](#the-verdict-that-could-not-go-red)*.

What went up is the set this harness can mutate at all: three gates whose implementation was a
heredoc inside a workflow are now scripts in `tools/`, so `automated` went from 13 to 16 and
`inline` from 8 to 5.

```
python tools/gates.py --check                                -- command output
  note: evidence provenance -- 7 of 12 demonstrated gate(s) carry evidence taken before a
        change to a file the gate is made of; `--evidence-provenance` says which
  gate manifest: 36 gate(s) across 23 environment(s) in 5 workflow file(s)
  mutation kind: automated 16, control 2, inline 5, manual 13
  demonstrable by this harness: 16 of 36, 4 of them still owed
  CARRYING IN-SITU EVIDENCE:   12 of 36
  top of the cost ranking:     2 of 3 demonstrated  (1 claims, 2 splits_manifest, 3 suite)
  in-situ quota: debt 24, ceiling 24 | 3 round(s) | M3-PA (the heredoc extraction) cut -1,
                 withdrew ['suite'], owes 4 forward | quota 3 per round, top 3 of the
                 ranking must be demonstrated
```

**The proof that licensed the first harvest has expired, and it was a proof that could not stay
true.** All thirteen demonstrations rested on one sentence written here: that
`git diff 3173126 61cf933` over eight paths was *empty*. It was true when it was written. It was
false on the next commit — seven of those eight paths have moved since, `tools/gates.py` by 518
lines and `bench/results.json` by 5,303. **A proof with a one-commit lifetime is not a mechanism**,
so it is replaced by one that is computed per gate and printed on every run:

```
python tools/gates.py --evidence-provenance                  -- command output, abridged
  gate                       at        state              changed under it
  claims                     3173126   predates a change  docs/GATES.md, tools/check_claims.py
  splits_manifest            3173126   predates a change  bench/splits.toml, tools/splits.py
  ngram_matches_lexicon      3173126   describes HEAD     -
  mypy                       3173126   describes HEAD     -  [command names no file; ...]
  gate_manifest              3173126   predates a change  tools/gates.py
  control_always_red         3173126   predates a change  .github/gates.toml, tools/gates.py
  ...
  7 of 12 gate(s) carry evidence taken before a change to a file the gate is made of.
```

A gate's dependency set is its mutation's edit targets, plus the file its command runs, plus the
workflow its step lives in. Where a command names no file — `python -m pytest`, `python -m mypy` —
the set is the whole tree and the row says so, because an empty changed-list would read as *nothing
this gate depends on has moved*, which is the flattering answer and the false one.

**It is a note and never a failure.** A changed file does not establish that a gate stopped catching
anything; it establishes which evidence is worth re-taking. A rule that reddened the build on the
passage of ordinary commits would be deleted within a week.

**Was any of the twelve falsified?** Asked, rather than assumed. Every automated mutation was re-run
on this tree on 2026-08-25: ten came back `DEMONSTRATED`, two (`test_environment_control`,
`harness_lint_environment`) came back `UNRESTORED` because a developer machine cannot satisfy their
premises — which the register already predicts — and one, `suite`, exposed the confound above. **No
gate was found inert on its own declared defect.** Local re-running can falsify in-situ evidence and
cannot confirm it, and it is used here only in that direction.

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

**The debt rule used to be not waivable, and that was a defect rather than a discipline.**
It is now waivable **only against an attribution**, and the reason is that the unwaivable version
made two honest moves unsayable and one documented escape unreachable:

- **Retiring a demonstration raises the debt by one**, so *"we found our evidence is weaker than we
  thought"* was refused before any escape was consulted. That is a count that can only rise, which
  is not a measurement.
- **The top-of-ranking rule made it worse at the top**, which is where a withdrawal matters most.
- **The escape this page already advertised could never apply.** It said a round may waive *"that
  adds an `automated` gate it could not run in CI in the same commit"*. Adding such a gate raises
  the debt by one, so the unwaivable rule fired first and the waiver was dead text. **A documented
  escape no input can reach is the same defect as a check that cannot fail, pointed the other way**,
  and it sat in this file from the day the quota was written.

So a rise now needs *both* an attribution and a waiver. `withdrawn_gates` names every gate whose
evidence was retired; `owed_forward` counts gates whose demonstration the next run is expected to
take; every name is checked against the live register; a withdrawn gate still carrying a run id is
refused; and the round **after** one that owed evidence forward must show the debt fell by at least
that much or say why it did not. An *unattributed* rise is still refused, and the top-of-ranking rule
still fires unless the gate is named as withdrawn and owed forward. Nine tests drive those rules.

**This is deliberately harsh and it will bite.** The set this harness can mutate is 16 of 36 and 4 of
those are owed. The 20 that remain are 5 `inline`, 13 `manual` and 2 `control` refusals, and none can
be mutated here. A future round that adds a `manual` gate — a new release check, say — has to pay for
it by extracting an inline gate into a script and demonstrating that. **The currency the quota
creates is exactly the fix this page named and did not do for two phases**, and three of the eight
inline gates have now been spent. [What the other five would cost](#what-the-remaining-five-would-cost-so-the-quota-does-not-stall-on-an-unstated-tail)
is measured rather than guessed, because an unstated tail is how a quota stalls.

### The rest of the battery

Seven more mutations of the live register, one at a time, each restored:

```
python tools/gates.py --check, ten runs against .github/gates.toml   -- command output,
one mutation each, the file restored from bytes read first and md5-verified   re-measured 2026-08-25

  rc=0  control, unmutated
  rc=1  A  the top-ranked gate loses its in-situ evidence
  rc=1  B  a 37th gate is added and nothing is demonstrated for it
  rc=1  C  claims is ranked last and ruff_format first
  rc=1  D  a gate loses its cost_rank
  rc=1  E  a gate declares a blast radius that is not one
  rc=1  F  a gate loses its cost_if_inert
  rc=1  G  an in-situ date loses its commit
  rc=1  H  a withdrawn gate is left carrying its run id
  rc=1  I  an automated fail-mutation drops its expect_failure_matching

  register restored byte-identically after every case: True
```

The first attempt at this re-measurement is worth one line, because it is the shape this whole page
is about: **five of the ten cases were silent no-ops and reported `rc=0`.** Every search string used
`\n` and the working copy of `.github/gates.toml` had CRLF, so five "mutations" changed nothing and
five green rows would have been published as refusals. The script now asserts that each case actually
changed the file. See *[How this page fails](#how-this-page-fails)* for what the CRLF is doing there.

Case `A` is the one worth reading in full, because it fires four rules at once and each says
something different:

```
python tools/gates.py --check, gates.claims stripped of its run id and commit  -- command output
  - gates.claims.mutation: `verified_in_situ_on` with no `verified_in_situ_run`. A date with
    no run id is a claim with no evidence.
  - gates.claims.mutation: `verified_in_situ_on` with no `verified_in_situ_commit`. A run id
    says a demonstration happened; the commit says WHICH gate was demonstrated.
  -   IN_SITU_TRAJECTORY['M3-PA (the heredoc extraction)']
    says 12 gate(s) carry in-situ evidence; 11 do.
  -   gates.claims ranks 1 of 36 by cost-if-inert and carries no in-situ evidence.
    The top 3 of the ranking must be demonstrated where they run.
```

Case `H` is the one this round added, and it is the withdrawal rule closing in the other direction:
a round that says it retired `gates.suite`'s evidence, against a register that still carries the run
id, is refused — *"one of the two is wrong"*. Without it, a withdrawal would be a sentence in a
Python list with nothing checking it against the tree.

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
  automated  16    an edit this harness applies, runs the gate's own command against, and reverts
  inline      5    the gate is a heredoc inside a workflow; there is no command to invoke
  manual     13    mutable only in an environment this harness cannot create
  control     2    the step IS a positive control; mutating a control is a different task
```

Eight jobs carry no gate at all and each one says why in the register — two third-party analyses
whose rule sets this repository does not define, four upload-and-attest steps that assert nothing
about the tree, and two jobs of the mutation harness itself. Two more were added this round for the
same reason, and the reason is worth reading: `--assert-environment` checks **path globs**, and the
premise of `zero-dependency` and `import-time` is that *no optional dependency is installed* — a
property of the interpreter, not of the tree. A gate registered for a premise its own command cannot
observe would be the exact shape this page catalogues, so it is refused and the hole is written down.

**Five of the thirty-six are still refused for the architectural reason, and three that were are
not.** A gate whose implementation is a heredoc inside `ci.yml` has no command a runner can invoke,
so a mutation harness could only ever run a *copy* of it — and D-018 already settled that a pattern
describing the bug cannot be used to test for the bug. `schema_copies_match`, `tier_zero_purity` and
`import_ceiling` were the three this page named as *"one afternoon's work"*. They are extracted.
What that cost, and what the remaining five would cost, is in
*[The extraction](#the-extraction-and-what-it-fired-on-its-first-invocation)*.

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

---

## The extraction, and what it fired on its first invocation

Three heredocs became `tools/gate_schema_copies.py`, `tools/gate_tier_zero.py` and
`tools/gate_import_ceiling.py`. `ci.yml` invokes them; `tools/gates.py --mutate` runs the same files
against a declared defect. `tests/test_gate_scripts.py` pins both directions — each script must fail
on its defect **and** pass otherwise — and pins the two-copy problems the extraction creates: the
failure marker in each script must equal the one in the register, and `ci.yml` must invoke the
command the register names.

### The schema-copy gate was red on the developer machine and nothing could see it

The first invocation of the extracted script, against an **unmutated** tree:

```
python tools/gate_schema_copies.py                           -- command output, 2026-08-25
  SCHEMA COPIES DIVERGED: schemas/ and the bundled resource copy have diverged.       rc=1
  e1b2f9f2...  schemas/acronym-engine-result.schema.json
  9a8823ce...  src/acronymkit/resources/acronym-engine-result.schema.json

git ls-files --eol <both paths>
  i/lf  w/crlf  attr/text eol=lf    schemas/acronym-engine-result.schema.json
  i/lf  w/lf    attr/text eol=lf    src/acronymkit/resources/acronym-engine-result.schema.json
```

`.gitattributes` declares `*.json text eol=lf` and states in its own comment that the reason is
*"the CI job that asserts the two copies of the interchange schema are identical"*. The working copy
of one of the two had CRLF anyway, so the two differed by 161 bytes of line ending. **`git status`
was clean throughout**, because git compares normalised content — and the gate could not be run,
because it was a heredoc. Repaired by rewriting the working copy to LF, which is byte-identical to
HEAD: a working-tree repair, not a commit.

This is R11 running in the other direction. The rule says a gate must be shown able to fail where it
runs. The mirror is that a gate nothing can invoke cannot be shown to be **passing** anywhere either.

### Extraction alone did not make the third one demonstrable, which refutes this page's own costing

This page and the register both said the three go together. Measured, they do not.

```
python tools/gates.py --mutate <gate>                        -- command output, 2026-08-25, Windows
  schema_copies_match   DEMONSTRATED  mutated rc=1, restored rc=0   ambient interpreter
  tier_zero_purity      INERT         mutated rc=0                  ambient interpreter
  tier_zero_purity      DEMONSTRATED  mutated rc=1, restored rc=0   venv, `pip install -e .`
  import_ceiling        DEMONSTRATED  mutated rc=1, restored rc=0   venv, `pip install .`, with setup
```

The `INERT` row is the finding and it is not about the gate. `acronymkit` happened to be installed
**non-editably** on that machine, so `import acronymkit` resolved to site-packages and an edit to
`src/` never reached the thing the gate looks at. The harness reported a blind gate when the harness
had simply not touched it.

`ci.yml`'s `import-time` job installs non-editably **on purpose** — *"an editable install adds a path
finder of its own, and what is being measured is what a user actually installs"* — so
`gates.import_ceiling` would have had that failure mode permanently, in its own environment, by
construction. The fix is a new register field, `mutation.setup`: a command run after the edits and
before the gate, and again after the restore. For that one gate it is
`python -m pip install --quiet --no-deps --force-reinstall .`.

Two other things the extraction changed rather than moved, both registered rather than done quietly:

- **The old refusal named the wrong mutation.** It said an eager `import pydantic`. Pydantic is not
  installed in a base-only environment, so that import raises and the gate exits non-zero for a
  reason it does not describe — a false demonstration. The registered mutation is
  `from . import enums`, which the structural half rejects by name and which needs nothing installed.
- **Only the structural half of `import_ceiling` is demonstrated.** No edit to this tree reliably
  takes a cold import from where it sits to over the declared ceiling without breaking the
  structural half first, so the wall-clock half has never been shown able to fail and is not claimed
  to have been. R18 would have that half be an unarmed note with the machine named; changing it is a
  change to what CI enforces and is not this commit's business. The ceiling and its derivation
  travelled with the code into `tools/gate_import_ceiling.py`'s module docstring.

### What the remaining five would cost, so the quota does not stall on an unstated tail

```
the five gates still refused as `inline`, and what stands between each and a demonstration
  airgap_public_api_probe   rank  5   a ~150-line probe written into $RUNNER_TEMP and run inside
                                      an unprivileged network namespace. Extractable; NOT
                                      demonstrable by this harness, which cannot build that
                                      namespace. Cost: a script, and no evidence.
  wheel_resources           rank 11   needs a built wheel, which exists only between two steps of
  wheel_budget              rank 18   the `build` job. The gate's command has no meaning outside
  installed_wheel_smoke     rank 14   that window, so extraction buys testability and not a
                                      mutation -- unless `setup` is used to build the wheel, at
                                      roughly a minute per mutation.
  installed_import_resolves rank 26   needs the laid-out run directory `installed-suite` builds
                                      across three earlier steps. Same shape as the packaging
                                      gates: a sequence, not a command.
```

**Three of eight went in an afternoon and the other five will not.** The honest reading of the
original estimate is that it was right about the three it named and silent about the tail, which is
what an unstated tail does to a quota.

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

### The drift is closed for the assertions and named for the sequence

`tools/gate_packaging_mutation.py` **rebuilt `ci.yml`'s sequence rather than invoking it**, and the
register recorded that as an accepted cost beside every gate it touches. It was not only a cost, it
was the cause: the harness carried its own copy of `EXPECTED_NON_PASSING`, its own `PASS_FLOOR`, its
own log parser and its own `test -f` list, and the guard that existed to notice the drift
(`check_expected_non_passing_is_current`) printed `WARNING:` and carried on.

**Both assertions are now invoked rather than reproduced.** They were pure functions of text all
along — a log in, a verdict out; a tree in, a list of missing paths out — so they became
`tools/gate_installed_suite.py` and `tools/gate_sdist_files.py`. `ci.yml` runs them and the harness
imports them. There is nothing left for those two to drift from, and a test asserts it:

```
tests/test_gate_scripts.py::TestTheWorkflowAndTheScriptsAgree      -- what it pins
  ci.yml invokes all five extracted scripts by path
  no heredoc is left for an extracted gate (EXPECTED_NON_PASSING = {, CEILING_MS, ...)
  the harness's EXPECTED_NON_PASSING, PASS_FLOOR and file list ARE the scripts' objects
```

**The sequence around them is still reproduced, and the stronger fix is refused with a reason.** A
job's `run:` block is not addressable from outside the workflow; `installed-suite`'s sequence spans
`$RUNNER_TEMP`, `$GITHUB_WORKSPACE` and a virtual environment the workflow creates, none of which
exists off a runner. Nothing here can invoke it. So what is checkable is that every command the
harness copies still appears in the file it was copied from, and that is asserted **fatally, before
any case runs**:

```
python tools/gate_packaging_mutation.py --check-drift         -- command output, 2026-08-25
  reproduction check: 11 sequence fragment(s) still present in ci.yml; 4 divergence(s)
  declared; the two ASSERTIONS are imported from the scripts ci.yml runs, not copied
    declared divergence: installs the sdist with `--no-deps --force-reinstall` into the
      AMBIENT interpreter; installed-suite installs `${sdist}[dev]` into a fresh venv
    declared divergence: adds `-p no:cacheprovider` to the extracted-tree run
    declared divergence: runs in a temp directory rather than under $RUNNER_TEMP
    declared divergence: does not re-run build's wheel steps at all
```

A drift check that cannot fail would be the same defect a third time, so it has a control: the live
workflow passes it, and a workflow with one fragment renamed does not.

**Fatal rather than a warning, and that is the whole change in one word.** The previous guard's
reasoning was that *"a harness that refuses to start because a list moved is a harness people
delete"*. That is wrong in the one direction that matters here: this script's output is a **coverage
table**, and the table gets quoted into the register and into this page. A number about the wrong
sequence is worse than no number, which is exactly what run `32808357572` produced.

**What has still never happened is a green run of this job on a runner.** The `| tee` is fixed, the
build command matches the gate's, the drift check is fatal — and the two-of-five and four-of-five
figures below still stand on the 2026-08-24 Windows re-measurement. Nothing in this round re-derived
them anywhere.

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

### The verdict that could not go red

The section above ends *"take the evidence from the line, not from the verdict. A probe that does
not edit a file the register anchors on would fix it; that is not done."* **Neither half of that was
enough, and the measurement that shows it costs one command.**

`data/` present is the condition under which this register predicts `gates.suite` is INERT. With the
mutation applied, on this tree, restricted to the two files that can react to it:

```
gates.suite's declared mutation applied by hand, data/ PRESENT   -- command output, 2026-08-25
python -m pytest tests/test_splits_manifest.py tests/test_gate_manifest.py -q         rc=1
  FAILED tests/test_gate_manifest.py::TestTheRegisterThisRepositoryShips::test_it_validates
  (tests/test_splits_manifest.py: no failure -- the D-058 defect is NOT caught here,
   exactly as this register predicts)
the file restored, md5-verified against the bytes read before the mutation      True
```

So `rc != 0` was reachable **with the declared defect uncaught**. The probe edits
`tests/test_splits_manifest.py`, which is the anchor `gates.suite`'s own register entry names, so the
register's validator reddens the suite on its own — in *both* environments, for *any* tree. The
harness could not have returned `INERT` for this gate. **Its automated verdict carried no
information at all, and the register recorded in-situ evidence on the strength of it.**

Two consequences, and the second is the one this page has to say out loud.

**The rule changed.** `mutation.expect_failure_matching` is now required on every automated
mutation that expects a failure: a substring the gate's own output must contain before a non-zero
exit counts as a demonstration. For `gates.suite` it is the name of the test that must fail. The
rule has a positive control — the same mutation with a line the gate never prints comes back
`INERT`, and the same mutation with the right line comes back `demonstrated`:

```
tools/gates.py, one gate, two markers                        -- command output, 2026-08-25
  control  (the real marker)   demonstrated
  probe    (a line it never prints)   INERT -- "the gate exited 1, but its output does not
                                      contain 'A LINE THIS GATE NEVER PRINTS'"
```

**And the rule flips this gate's own local verdict, which is the result to read.** Same tree, same
mutation, same two full suite runs, before and after the rule:

```
python tools/gates.py --mutate suite       -- command output, 2026-08-25, data/ PRESENT
  before the rule   suite   DEMONSTRATED  mutated rc=1, restored rc=0
  after  the rule   suite   INERT         "the gate exited 1, but its output does not
                                          contain <the named test>. Something here failed; it
                                          was not this gate catching this defect, and a return
                                          code cannot tell those apart."
                                          (the only FAILURE printed is
                                           TestTheRegisterThisRepositoryShips.test_it_validates;
                                           the named test is
                                           test_the_reader_that_would_spend_the_allocated_arm_is_wired)
```

`INERT` is the **correct** answer on a machine holding `data/` — it is what this register predicted
and what the harness had stopped being able to say. The prediction that `test-gates` exists to check
is testable again.

**The evidence was withdrawn.** The captured artifact from run `32808357572` does carry the named
`FAILED` line — it is quoted in the section above — but the only record of it in this repository is
that quotation, and a failure line transcribed into a prose document is an unchecked claim in
exactly the way R16 says a figure inside an image is. Under the new rule the demonstration has to be
**re-taken**, not re-read. `gate-mutation.yml` triggers on every path this commit touches, so the run
that re-takes it is the run that lands this work, and `owed_forward` on the trajectory row is what
makes the next round check that it happened.

**What is still not done: the confound itself.** Removing it needs a probe that does not edit a file
the register anchors on, and the D-058 defect *lives* in that file. Naming the line is the fix that
works without moving the defect; it makes the verdict attributable and leaves `rc=1` over-determined.

### Retiring evidence was arithmetically impossible, and that is a defect in the quota rather than in the evidence

Withdrawing `gates.suite` should have been a one-line edit. It was not, and the reason is worth more
than the edit.

The quota is a ceiling on the debt, `gates - in_situ`, and the ceiling rule was declared **not
waivable**. Withdrawing a demonstration raises the debt by one. So the rule fired first, `continue`d
past every escape, and *"we found our evidence is weaker than we thought"* could not be expressed at
all. The top-of-ranking rule made it worse: `gates.suite` ranks 3, and the top three must carry
evidence, so a withdrawal there was doubly unsayable — **at exactly the rank where a withdrawal
matters most.**

The same ratchet had already broken something this page claimed to offer. It says a round may record
a waiver *"that adds an `automated` gate it could not run in CI in the same commit"*. Adding such a
gate raises the debt by one, so that waiver **could never apply.** A documented escape that no input
can reach is the same defect as a check that cannot fail, pointed the other way, and it had been
sitting in this file since the quota was written.

The fix is attribution rather than exemption. A rise is now permitted only when the round accounts
for it — `withdrawn_gates`, naming each gate whose evidence was retired, and `owed_forward`, counting
gates whose demonstration the next run is expected to take — **and** carries a waiver saying why.
Every name is checked against the live register, a withdrawn gate that still carries a run id is
refused, and the round *after* one that owed evidence forward must show the debt fell by at least
that much or write down why it did not. Nine tests in `tests/test_gate_manifest.py` drive those
rules, including the one that matters most: an *unattributed* rise is still refused.

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
python tools/gates.py --evidence-provenance         which evidence predates a change to its gate
python tools/gate_schema_copies.py                  the two schema copies are byte-identical
python tools/gate_tier_zero.py                      Tier 0 imports and runs with no extras
python tools/gate_import_ceiling.py                 nothing is eagerly bound; cold import is cheap
python tools/gate_sdist_files.py DIR                an extracted sdist carries what its docs cite
python tools/gate_installed_suite.py LOG            adjudicate an installed-suite pytest log
python tools/gate_packaging_mutation.py --check-drift  is the reproduction still ci.yml's sequence?
python tools/gate_packaging_mutation.py --out DIR   the five historical breakages, against a real sdist
```

`--mutate` edits the working tree and puts it back. It writes the previous bytes of every file it
touches before touching it and restores them in a `finally` block, and then re-runs the gate to
confirm a zero exit — because without that second half, a gate failing for an unrelated reason reads
as a successful demonstration. It also reports, rather than hides, a file that **changed while the
mutation was applied**: one declared mutation deletes `bench/results.json` for the duration of a run,
this repository is edited by several agents at once, and a restore from bytes read beforehand would
otherwise overwrite somebody else's write in silence.

**Two of these reinstall or rebuild.** `--mutate import_ceiling` carries a `setup` that runs
`pip install --force-reinstall .`, because `ci.yml`'s `import-time` job installs non-editably and a
source edit would otherwise never reach the gate. Run it inside a virtual environment — invoke
`tools/gates.py` **with that venv's interpreter** and the setup lands there — unless you want
`acronymkit` reinstalled into whatever Python you are holding.

---

## How this page fails

**The lead item is that the count went DOWN and four gates are owed on a promise.** Twelve of
thirty-six carry in-situ evidence, against thirteen before. `gates.suite` — rank 3, the highest-cost
gate this harness can mutate — had its evidence withdrawn because its recorded verdict was measured
to be reachable with the defect uncaught. Three newly-extracted gates carry a **local** demonstration
and nothing else, and a local demonstration is precisely what R11 says is not evidence. So the honest
statement is: `12 of 36`, four owed forward on a CI run that has not happened yet, and **nothing on
this page is evidence that the extraction works on a runner.**

**Twenty-four of the thirty-six still carry no in-situ evidence, and twenty of those cannot.** Five
`inline`, thirteen `manual`, two `control` — none mutable by this harness. The number that moved
from zero to thirteen and back to twelve is the number of gates that were *always* demonstrable, and
the honest reading is not *"a third of the way"* — it is *"all of the easy ones, and the remainder
needs a different kind of work"*. Three of that remainder were spent this round; what the other five
inline gates cost is measured above, and it is not another afternoon.

**Every number on this page about the extraction was taken on a developer machine, and one of them
had to be taken twice to be right.** `tier_zero_purity` came back `INERT` against the ambient
interpreter and `DEMONSTRATED` against a venv that mirrors the CI job, and the difference was the
install mode. Any of these three could differ on a runner for a reason nobody has thought of; that is
the whole of R11 and it applies to this round's own work first.

**The working tree writes CRLF into files git stores as LF, and it has already broken a gate.**
> **THE COUNT USED TO BE QUOTED HERE AND IS NOW DELIBERATELY NOT.** This paragraph said
> "`66` of `216`". A cold reader running the same command got `57`; the next run got `61`. The
> denominator reproduces exactly and the numerator does not, because **`w/crlf` is a property of the
> reader's working tree and checkout settings, not of the repository** — and this page ships in the
> sdist, where it would be asserting a fact about a machine the reader does not have. The `216` is
> kept because it is a repository fact. The share is described rather than counted, which is the
> only honest form available: a figure that changes with who reads it is not a figure.

`.gitattributes` declares `*.json text eol=lf` and says the reason is the schema-copy gate.
`git ls-files --eol` reports a large minority of the `216` tracked files as `w/crlf`, and
`schemas/acronym-engine-result.schema.json` was one of them — so that gate was **red in this working tree** and nothing could see it, because it
was a heredoc. `git status` stays clean throughout, because git normalises on compare. The same thing
silently no-opped five cases of this page's own mutation battery. Nothing checks it: there is no gate
on working-tree line endings, and the one gate that would notice only notices for two files out of
sixty-six.

**The previous version of this page said `gate-mutation.yml` had never run, and that was false when
it was written.** It had run — green, artifacts uploaded, `13` demonstrations captured — and this page
went on asserting a zero for a whole phase. Nothing detected the contradiction, because nothing in
this repository reads a run log. That is worth more attention than the count it corrected: **the
failure mode here is not that the mechanism does not work, it is that its output goes unread.** The
`report` job now prints how to record a run, which is a nudge and not a gate. A scheduled workflow
whose artifacts nobody harvests is indistinguishable from one that never ran, and nothing here
closes that.

**Seven of the twelve demonstrated gates carry evidence taken before a change to a file the gate is
made of, and `--evidence-provenance` is a note rather than a gate.** It says which evidence is worth
re-taking; it does not say that any of it stopped working, and nothing here could. Two of the twelve
have a dependency set that cannot be closed at all — `python -m pytest` and `python -m mypy` name no
file — so for those the honest answer is *the whole tree changed*, printed as such.

**The provenance check needs git history and CI checkouts are shallow.** `actions/checkout` fetches
depth 1 by default, so every row would read `unknown` unless the job asks for more. The `report` job
does; nothing enforces that a future job will, and a table of `unknown` is honest and useless.

**Local re-running can falsify in-situ evidence and cannot confirm it, and this page uses it only in
that direction — but that direction was exercised on a tree several agents were editing.** Two runs
of the same suite an hour apart on this machine gave `5392 passed, 10 skipped` and
`5391 passed, 11 skipped`, because another workstream's files landed in between. Every number on
this page taken from a full-suite run carries that uncertainty.

**The packaging job's ASSERTIONS are now invoked and its SEQUENCE is still reproduced.** The two
copied objects are gone — `EXPECTED_NON_PASSING`, `PASS_FLOOR`, the log parser and the `test -f` list
live in `tools/gate_installed_suite.py` and `tools/gate_sdist_files.py`, which `ci.yml` runs and the
harness imports. What is left is the multi-step sequence, and it **cannot** be invoked from outside
the workflow: a job's `run:` block is not addressable, and the sequence spans `$RUNNER_TEMP`,
`$GITHUB_WORKSPACE` and a venv the workflow creates. So the stronger fix is refused for that half and
the divergence is made checkable instead — eleven literal fragments asserted against `ci.yml`, fatally
and before any case runs, plus four declared divergences. **A fragment check is weaker than an
invocation and this page will not pretend otherwise**: it catches a rename or a flag change and it
cannot catch a reordering, an added step, or a `run:` block that means something different with the
same words in it.

**And the packaging harness has still never produced a green run on a runner.** The `| tee`, the
`--no-isolation` and the two copies are all fixed; the two-of-five and four-of-five coverage figures
this page publishes still rest on a Windows re-measurement from 2026-08-24. Nothing in this round
re-derived them anywhere, and this round did not run the harness at all — it installs into the
ambient interpreter with `--force-reinstall`, on a machine other agents were running suites on.

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

**`.github/gates.toml` IS shipped in the sdist, and this paragraph said the opposite for one
commit.** It used to read: *"`.github/gates.toml` is not shipped in the sdist, and this page is.
`MANIFEST.in` ships `recursive-include docs *.md` and `.github/workflows/*.yml`, and nothing else
from `.github/` — so a reader holding a distribution gets this page, follows its link to the register
in the second paragraph, and finds nothing."* That was true when written and false one commit later:
`387f739` added `include .github/gates.toml` and `include docs/cold-reads.toml` to `MANIFEST.in`,
**because a link-integrity guard added in that same commit found this exact dangling link**. Refuted
here against a real sdist built from this tree rather than against `MANIFEST.in`, since the manifest
is the input and the tarball is the claim.

The correction is left visible because of how it happened: the commit that **fixed** the defect did
not update the three pages that **described** it, and one of those three is in a source file no
trigger on the policy page can reach. A repository can fix a thing and go on publishing that the
thing is broken, and nothing in this register catches that. That is precisely the `data/LICENSES.md` shape: a shipped document
citing evidence the artifact omits, which `MANIFEST.in`'s own comment already enumerates four
instances of. The tests in `tests/test_gate_manifest.py` that read the register skip there on a
narrow `needs_register` mark rather than erroring, which is the right behaviour and not a fix — how
many of them there now are was not re-measured this round, for the reason given above. `MANIFEST.in`
was not this workstream's file; one line adds it, and until somebody writes that line this is the
fifth instance.

**The register is not scanned by the claims gate.** `tools/check_claims.py` scans `bench/splits.toml`
and not `.github/gates.toml`, so any number written into the register is unchecked. This page is
scanned; the register it describes is not.
