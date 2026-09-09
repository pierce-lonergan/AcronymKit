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

**The register holds forty-one gates and twenty-one of them carry in-situ evidence.** Run
`python tools/gates.py --check` rather than trusting that sentence; it is the number this page has
got wrong most often, and it was wrong here by a whole round until somebody adding the forty-first
gate noticed.

The count moved twice in two rounds and neither move is flattering. `M3-PB` registered `figures`
and `memo_identity` owing evidence forward; they were demonstrated on a runner two days later and
the register went on printing `16 of 38` until somebody ran `gh run view`. Then
[`gates.run_summary`](#the-thirty-ninth-gate-the-account-of-a-round-is-now-an-artefact-a-gate-reads)
arrived as the thirty-ninth and `gates.second_reader` as the fortieth, both demonstrated in the
session that pushed them. **`gates.second_reader` has no section on this page**, which is this
document's own version of the defect that gate was written for: the fortieth gate is in the
register, in the `lint` job and in `CONTRIBUTING.md`, and the page that explains the register does
not mention it. Named here rather than written by a round that did not build it.

The forty-first is
[`gates.agent_summary`](#the-forty-first-gate-a-crashed-agent-is-now-a-different-fact-from-a-silent-one),
added by this round and owing its own demonstration forward. **Every command output quoted in the
rest of this section was captured when it was taken and may read `38` or `39`; the transcripts are
left as they were rather than re-stamped, which is the convention this page has for every dated
block.**

The paragraph this replaces read *"Sixteen of the thirty-eight gates carry in-situ evidence. The
count went UP by four, and not one of the four was earned by this round."* Its second sentence is
still the interesting one, and it is now true twice.

The previous version of this page opened *"Twelve of the thirty-six"* and closed by saying that
`gates.suite`'s evidence had been withdrawn, that three newly-extracted gates carried a local
demonstration and nothing else, and that four gates were **owed forward** on a CI run that had not
happened yet.

**It had happened. Twice. Nobody had read it.**

```
gh run list --workflow "Gate mutation"                       -- command output, abridged
  completed  success  Gate mutation  main  schedule  34099756605  15m32s  2026-09-07T08:16:49Z
  completed  success  Gate mutation  main  schedule  33379084166  11m2s   2026-08-31T09:43:29Z
both at headSha 34925f8, which is the commit this round started from
```

Every one of the sixteen automated gates came back `demonstrated` in both runs, with zero `INERT`
and zero `UNRESTORED` — including all four that were owed. **The register went on printing
`12 of 36` for a fortnight while the evidence sat in the Actions tab.** This page had already named
that failure mode in its own words — *"a scheduled workflow whose artifacts nobody harvests is
indistinguishable from one that never ran"* — and then was the thing it described.

`gates.suite` is the verdict worth reading, because it is the one that was withdrawn:

```
run 34099756605, job "Mutate ci.yml's test job on one cell"     -- captured log, verbatim
  environments.test: holds 4 declared path(s), lacks 3 declared path(s) -- this is that environment
  suite                                  DEMONSTRATED  mutated rc=1, restored rc=0
  test_environment_control               DEMONSTRATED  mutated rc=1, restored rc=0
  2 demonstrated, 0 INERT or UNRESTORED, 0 not automated
```

**That commit is the one that shipped `expect_failure_matching`**, so `DEMONSTRATED` was reachable
only by the gate's own output containing the name of the test that must fail. The withdrawn record
rested on a return code and on a `FAILED` line transcribed into this page by hand; this one rests on
a rule the harness applied. *The evidence moved out of prose and into the mechanism*, which is the
whole of the correction, and it is why the withdrawal is not simply undone but **re-taken**.

**All twelve older stamps were re-stamped to the same run**, rather than left at
`2026-08-25`/`3173126`. The newer run demonstrates them at what was HEAD, and a stamp seven commits
behind is exactly the staleness `--evidence-provenance` exists to report.

**The register also grew by two, and that is a debt this round chose to take on.** Two other
workstreams handed over gate scripts — `tools/render_figures.py --check` (R16) and
`tools/gate_memo_identity.py` (R19) — and both are registered here with a `cost_rank`, a mutation
and no evidence, because the commit that adds a gate cannot hold the run that demonstrates it.
Debt `24` → `20` on the harvest, then `20` → `22` on the registration; still under the ceiling of
`24`, and `2` are owed forward.

```
python tools/gates.py --check                                -- command output
  note: evidence provenance -- 0 of 16 demonstrated gate(s) carry evidence taken before a
        change to a file the gate is made of; `--evidence-provenance` says which
  gate manifest: 38 gate(s) across 23 environment(s) in 5 workflow file(s)
  mutation kind: automated 18, control 2, inline 5, manual 13
  demonstrable by this harness: 18 of 38, 2 of them still owed
  CARRYING IN-SITU EVIDENCE:   16 of 38
  top of the cost ranking:     2 of 3 demonstrated  (1 claims, 2 splits_manifest, 3 figures)
  in-situ quota: debt 22, ceiling 22 | 5 round(s) | M3-PB (the two gates the siblings handed
                 over) cut -2, owes 2 forward | quota 3 per round, top 3 of the ranking must
                 be demonstrated
```

**Read the provenance line before the count.** `0 of 16` is the flattering reading and it is a
snapshot taken before this commit lands: every stamp names commit `34925f8`, and this commit moves
`.github/gates.toml`, `tools/gates.py` and `.github/workflows/ci.yml`. The moment it is committed,
every gate made of one of those files goes back to *predates a change*. That is not a defect in the
harvest, it is what a dated measurement of a moving tree looks like — and the note is a note, never
a failure.

```
python tools/gates.py --evidence-provenance                  -- command output, abridged
  gate                       at        state              changed under it
  claims                     34925f8   describes HEAD     -
  splits_manifest            34925f8   describes HEAD     -
  suite                      34925f8   describes HEAD     -  [command names no file; ...]
  schema_copies_match        34925f8   describes HEAD     -
  import_ceiling             34925f8   describes HEAD     -
  tier_zero_purity           34925f8   describes HEAD     -
  ...
  0 of 16 gate(s) carry evidence taken before a change to a file the gate is made of.
```

A gate's dependency set is its mutation's edit targets, plus the file its command runs, plus the
workflow its step lives in. Where a command names no file — `python -m pytest`, `python -m mypy` —
the set is the whole tree and the row says so, because an empty changed-list would read as *nothing
this gate depends on has moved*, which is the flattering answer and the false one.

**Was any of the sixteen falsified?** Asked in both available directions.

*Across runs:* the two scheduled runs are a week apart on one commit, against two different weekly
runner images, and they agree gate for gate. That is the only guard this register has against a
verdict that is a property of the image rather than of the code, and it is the first time it has
been exercised. **No gate was found inert on its own declared defect in either run.**

*Against this tree:* thirteen automated mutations were re-run locally on 2026-09-08, in a **mirror**
of the working tree rather than in it, because two of the probes edit files other workstreams were
writing to at the time and `--mutate` restores from bytes read beforehand.

```
python tools/gates.py --mutate <13 gates>     -- command output, 2026-09-08, Windows, a mirror
                                                 of the working tree with data/ excluded
  12 demonstrated, 1 INERT or UNRESTORED, 0 not automated
  claims   UNRESTORED   "the gate still exits 1 after the tree was put back"
```

**The one non-demonstration is `claims`, and it is `UNRESTORED` rather than `INERT`** — which is the
distinction the harness exists to draw. The gate *did* catch its probe; it also exits `1` on the
unmutated mirror, because another workstream regenerated `bench/results.json` without re-rendering
and forty-three citations in three documents this workstream does not own are stale. **A failure on
a tree that was already failing proves nothing about the mutation**, so no verdict is recorded from
it. Local re-running can falsify in-situ evidence and cannot confirm it, and this run falsified
none.

`import_ceiling` and `tier_zero_purity` were not re-run: the first carries a `setup` that
reinstalls the package into the ambient interpreter, and the second's verdict depends on the install
mode, which is the whole of the *[extraction alone did not make the third one
demonstrable](#extraction-alone-did-not-make-the-third-one-demonstrable-which-refutes-this-pages-own-costing)*
finding. Both carry runner evidence from 2026-09-07 and neither needs a laptop's opinion.

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
  1  claims                           published_numbers      silent   sole         2026-09-07
  2  splits_manifest                  published_numbers      silent   sole         2026-09-07
  3  figures                          published_numbers      silent   sole         -  (automated)
  4  suite                            installed_behaviour    silent   partial      2026-09-07
  5  airgap_suite_under_guard         installed_behaviour    silent   sole         -  (manual)
  6  airgap_public_api_probe          installed_behaviour    silent   partial      -  (inline)
  7  schema_copies_match              installed_behaviour    silent   sole         2026-09-07
  8  memo_identity                    installed_behaviour    silent   sole         -  (automated)
  9  ngram_matches_lexicon            installed_behaviour    silent   sole         2026-09-07
 10  import_ceiling                   installed_behaviour    silent   sole         2026-09-07
  ...
 23  claims_in_sdist                  distribution_contents  silent   partial      -  (manual)
 27  gate_manifest                    evidence_apparatus     silent   sole         2026-09-07
 37  ruff                             repository             loud     sole         2026-09-07
 38  ruff_format                      repository             loud     sole         2026-09-07
```

**`figures` is rank 3 and carries no evidence, which is a rule this round had to change rather than
route around.** Its factors are `(published_numbers, silent, sole)` — the same three `claims` and
`splits_manifest` declare — so the ordering validator puts it at the top, and the top-of-ranking
rule is **not waivable**. That rule is right about the thing it was built for: demonstrating
whichever gates were easiest and calling it coverage is the failure this whole register exists to
end. It was **wrong about a gate that has just arrived**, because the commit that adds a gate cannot
also hold the CI run that demonstrates it — so the only way to land a correctly-ranked new gate was
to rank it dishonestly low. *That is worse than what the rule was preventing.* See
[the escape for a gate that arrived](#the-top-of-ranking-rule-had-the-same-hole-the-debt-rule-had).

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

These two blocks are **historical**: they were taken when the register held `36` gates and `13`
demonstrations, and they are kept because they are what the rule said when it fired. Case `B` of
[the battery below](#the-rest-of-the-battery) is the same rule re-run against today's register.

```
a 37th gate is appended to .github/gates.toml, carrying no evidence  -- command output, at the
                                                                       36-gate register
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

### The top-of-ranking rule had the same hole the debt rule had

**Pointed at new work instead of at retired work, and found the same way — by a round that could not
say a true thing.**

Two gate scripts arrived this round from other workstreams. `gates.figures` is
`python tools/render_figures.py --check`: R16, the rule that a figure inside an image is an unchecked
claim, because `tools/check_claims.py` reads markdown, Python and one TOML file and **cannot read an
SVG, a PNG or a `<title>`**. Its honest factors are `(published_numbers, silent, sole)` — the same
three `claims` declares — so the ordering validator puts it at rank `3`.

And a rank-3 gate with no evidence is refused, by a rule with no waiver.

The gate cannot have evidence: the run that demonstrates it happens after the push that creates it.
So the register offered exactly two moves, and **both were worse than the thing the rule prevents**:
leave R16 unregistered, or declare a blast radius nobody believes so the gate sorts down into the
teens. *A rule whose only satisfiable answer is a dishonest field is not a discipline.*

The fix is the one the debt rule already got: **attribution plus a due date, never exemption.**
`added_gates` names each newly-added gate the round could not demonstrate; the round must also carry
`owed_forward` and a waiver; every name is checked against the live register; and — the mirror of the
withdrawal rule — **a gate named in `added_gates` that already carries a run id is refused**, because
a promise to do work already done reads as a payment next round. Four tests drive it, including both
halves of the attribution and the refusal of a name that is not a gate.

**What it does not buy.** The waiver is still a sentence somebody writes and nobody grades, and
`added_gates` makes the top-of-ranking rule waivable where it was absolute. The argument for that is
narrow and stated rather than buried: it is waivable **only** while the round is also promising the
demonstration, and the round after has to show the debt fell or say why not. A round that keeps
naming the same gate forever is visible in the trajectory as a promise renewed rather than kept —
which is a thing a reader can see and nothing here can enforce.

**This is deliberately harsh and it will bite.** The set this harness can mutate is 18 of 38 and 2 of
those are owed. The 20 that remain are 5 `inline`, 13 `manual` and 2 `control` refusals, and none can
be mutated here. A future round that adds a `manual` gate — a new release check, say — has to pay for
it by extracting an inline gate into a script and demonstrating that. **The currency the quota
creates is exactly the fix this page named and did not do for two phases**, and three of the eight
inline gates have now been spent. [What the other five would cost](#what-the-remaining-five-would-cost-so-the-quota-does-not-stall-on-an-unstated-tail)
is measured rather than guessed, because an unstated tail is how a quota stalls.

### The rest of the battery

Nine mutations of the live register, one at a time, each restored:

```
python tools/gates.py --check against .github/gates.toml    -- command output, one mutation
each, the file restored from the bytes read first and md5-verified    re-measured 2026-09-08

  rc=0  control, unmutated
  rc=1  A  the top-ranked gate loses its in-situ evidence
  rc=1  B  a 39th gate is added and nothing is demonstrated for it
  rc=1  C  claims is ranked last and ruff_format first
  rc=1  D  a gate loses its cost_rank
  rc=1  E  a gate declares a blast radius that is not one
  rc=1  F  a gate loses its cost_if_inert
  rc=1  G  an in-situ date loses its commit
  rc=1  I  an automated fail-mutation drops its expect_failure_matching
  rc=1  J  a gate named in added_gates already carries evidence

  register restored byte-identically after every case: True
```

Case `H` — *a withdrawn gate is left carrying its run id* — is **not** in this battery any more, and
the reason is the round rather than the rule: no gate is withdrawn in the live trajectory, so the
mutation has nothing to act on here. It is driven by `tests/test_gate_manifest.py` instead, which is
where every one of these rules is also tested against a synthetic register.

Case `J` is what this round added, and it is `added_gates` closing in the direction nobody would
notice: a round that names a gate as newly-added-and-owed against a register that already carries
that gate's run id is refused. Without it, `added_gates` would be a place to bank credit for work
already finished.

**THE CRLF DEFECT RECURRED WHILE THIS BATTERY WAS BEING RE-RUN, AND THAT IS THE MOST USEFUL LINE ON
THIS PAGE.** The previous round recorded that five of ten cases had been silent no-ops reporting
`rc=0`, because every search string used `\n` and the working copy of `.github/gates.toml` had CRLF.
It happened again, this round, pointed the other way: the edits that produced this round's register
used `pathlib.Path.write_text`, which on Windows translates `\n` to `\r\n` — so **every file this
round touched was silently rewritten to CRLF in the working tree.** `git status` stayed clean
throughout, because `.gitattributes` declares `text eol=lf` and git normalises on compare, and
`git ls-files --eol` reported `w/crlf` for six files that are `i/lf` in the index.

Nothing here detected it. What detected it was **case `D` of this battery refusing to run**, on the
one assertion the previous round added for exactly this reason: *a probe that did not change the
file is not a probe that found nothing.* Without that assertion, `D` through `J` would have printed
`rc=0` and been published as green rows against refusals that never fired.

The files were rewritten to LF and verified with `git ls-files --eol`. **The lesson is not "use
`newline=`".** It is that a guard written against one instance of this class caught the next
instance, in a different tool, three weeks later — and that the class is still not gated. There is
still no check on working-tree line endings, and the one gate that would notice
(`schema_copies_match`) only notices for two files.

Case `A` is the one worth reading in full, because it fires four rules at once and each says
something different:

```
python tools/gates.py --check, gates.claims stripped of its run id and commit  -- command output
  - gates.claims.mutation: `verified_in_situ_on` with no `verified_in_situ_run`. A date with
    no run id is a claim with no evidence.
  - gates.claims.mutation: `verified_in_situ_on` with no `verified_in_situ_commit`. A run id
    says a demonstration happened; the commit says WHICH gate was demonstrated.
  -   IN_SITU_TRAJECTORY['M3-PB (the two gates the siblings handed over)']
    says 16 gate(s) carry in-situ evidence; 15 do.
  -   gates.claims ranks 1 of 38 by cost-if-inert and carries no in-situ evidence.
    The top 3 of the ranking must be demonstrated where they run.
```

Case `J` is the `added_gates` rule closing in the direction nobody would notice, and case `H` — the
withdrawal rule closing the same way — is what it was modelled on: a round that says it retired
`gates.suite`'s evidence, against a register that still carries the run id, is refused, *"one of the
two is wrong"*. Both live in `tests/test_gate_manifest.py`. Without them, a withdrawal and an
addition would each be a sentence in a Python list with nothing checking it against the tree.

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
  automated  18    an edit this harness applies, runs the gate's own command against, and reverts
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

**Five of the thirty-eight are still refused for the architectural reason, and three that were are
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
run 34099756605, packaging-gates, ubuntu-latest, CPython 3.12, at 34925f8   -- captured log,
                                                                              verbatim, abridged
case    test -f   extracted tree    installed-suite   label
control passes    passes            passes            unmutated control
a       FAILS     FAILS             passes            bench/results.json out of the sdist
b       FAILS     FAILS             passes            data/LICENSES.md out of the sdist
c       passes    FAILS             FAILS             tests/fixtures/* out of the sdist
d       passes    FAILS             FAILS             test_governed_gold.py loads bench/ unguarded
e       passes    FAILS             passes            test_splits_manifest.py, same defect

build/extracted tree catches 5 of 5
installed-suite catches      2 of 5
unmutated control: green in both environments
```

**Replicated.** Run `33379084166`, 2026-08-31, same commit, a different weekly runner image: the
same six rows, case for case.

The control line is not decoration. A broken checkout produces five *caught* verdicts and reads as a
triumph — which is exactly how three of D-050's measurements came out wrong the first time, against
artifacts a stale `SOURCES.txt` had made unmutated. The script sweeps every `*.egg-info` before it
builds, for that reason and no other.

The `test -f` column is a third gate on the same step, and splitting it out is a finding rather than
tidiness: one YAML step runs a list of filenames *and* a whole pytest run, the two have different
coverage — two of five against five of five — and registering the step as one gate would have
published a single number true of neither. **The register's unit is the assertion, not the step.**

### The runner did not reproduce the published table, and the cause was this register's own last round

**`4 of 5` was the figure on this page and in `.github/gates.toml`. The runner says `5 of 5`, twice,
and the row that moved is `b`.** The Windows measurement of 2026-08-24 at commit `a62f99a` was right
when it was taken. The *tree* moved under it.

What moved is the heredoc extraction itself. It added `tests/test_gate_scripts.py`, whose
`TestSdistFileList` asserts `gate_sdist_files.missing(REPO_ROOT) == []` — and **inside an extracted
sdist, `REPO_ROOT` is the artifact**, so the required-file list is now enforced from inside the
distribution as well as from `ci.yml`'s `test -f` step. Verified in-process on 2026-09-08:
`missing()` over a tree holding every required path returns `[]`, and returns `data/LICENSES.md`
with that one path removed.

**Two other hypotheses were tested and refuted first, and they are recorded because a mechanism that
survived one guess is worth less than one that survived three.** The link-integrity guard added in
`387f739` does *not* catch it — `_LINKS_NOT_SHIPPED` exempts everything under `data/`, and re-running
that test's logic in-process with the manifest line removed left the dangling list empty. Nor does
`test_every_file_the_claims_gate_reads_is_shipped_by_the_manifest`: `check_claims.SCAN_GLOBS` does
not name `data/LICENSES.md`.

**Nobody designed this and no round claimed it.** The extraction was costed as buying testability;
it also moved a breakage's coverage, in a file nobody was looking at, and the register would have
gone on publishing `4 of 5` if the runner's table had not been read. Two sentences elsewhere are
falsified by it and are corrected here: `gates.sdist_extracted_tree_suite.blind_to` said `b` was
missed *"because nothing in the suite reads data/LICENSES.md"*, and the comment above
`test_data_licenses_is_on_the_list` said the same thing **six lines below the test that falsifies
it**. A third copy — the reason string inside `tools/gate_sdist_files.py`, which is what that gate
*prints when it fires* — is still false and is reported rather than edited, because changing what a
shipped gate prints was not this workstream's business.

**The platform limitation D-040 and D-050 both carried is over.** Every row above is measured on
ubuntu under GitHub's `bash -e`.

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

**And then it ran green, twice, and nobody read that either.** Runs `33379084166` (2026-08-31) and
`34099756605` (2026-09-07), both `ubuntu-latest`, both at `34925f8`: six sdists built, the unmutated
control green in both environments, the two runs agreeing case for case. The totals in this section
are re-derived from the second of those and no longer stand on a Windows measurement — **and the
runner refuted one of them**, which is the section above.

The last local attempt with the fixed command, before those runs were read, was refused by the
script's own control:

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

**The sequence around them is still reproduced, the stronger fix is still refused, and the refusal
now costs more than a sentence.** A job's `run:` block is not addressable from outside the workflow;
`installed-suite`'s sequence spans `$RUNNER_TEMP`, `$GITHUB_WORKSPACE` and a virtual environment the
workflow creates, none of which exists off a runner. **Nothing here can invoke it**, and that is not
a judgement call — it is what a workflow file is.

So the divergence is made checkable instead, and the previous version of this section had written
down exactly what its check could not see:

> *"A fragment check is weaker than an invocation and this page will not pretend otherwise: it
> catches a rename or a flag change and it **cannot catch a reordering, an added step, or a `run:`
> block that means something different with the same words in it**."*

**Two of those three are closed.** The check went from eleven bare substrings searched against the
whole file to three rules:

| rule | what it asserts | what it closes |
|---|---|---|
| `scope` | each fragment appears inside the `run:` blocks of **the job it was copied from** | a command that moved job, or was demoted to a comment |
| `order` | the fragments of one job appear in **the declared order** | a reordering of the steps |
| `shape` | each pinned region still holds the declared **command-line count and digest** | an added step, a deleted step, an edited command |

```
python tools/gate_packaging_mutation.py --check-drift --out DIR   -- command output, 2026-09-08
  reproduction check: 11 sequence fragment(s) present in the ci.yml JOB each was copied
  from and in the declared order; 3 pinned region(s) holding 25 command line(s) at the
  declared digests; 5 divergence(s) declared; the two ASSERTIONS are imported from the
  scripts ci.yml runs, not copied
    pinned region: installed-suite -- 21 line(s), b914d817205e495a
    pinned region: build / Build sdist and wheel -- 1 line(s), 723c5e86c09ab8df
    pinned region: build / Verify the sdist ships the files its own test suite reads
                   -- 3 line(s), c16bab555f469178
    declared divergence: ... (five, each with its reason)
```

**Why a digest and not a list of the lines.** The obvious way to catch an added step is to declare
every command line the region may hold — and *a list of every command line in a job is that job,
copied into Python*, which is the defect this whole file exists to record. Three counts and three
digests pin twenty-five lines without transcribing one of them. The trade is stated rather than
hidden: a digest cannot say **what** moved, so the failure prints the region's current lines beside
the mismatch and asks a person to re-derive the reproduction. Regenerating the pin
(`--print-regions`) is a button that silences the check — the same shape as the shrink waiver on the
quota — and what it buys is that the button has to be pressed deliberately, in a diff a reviewer
sees.

**Measured, one mutation of a copy of `ci.yml` at a time, the live file never touched.** The old
whole-file substring rule caught one of six; the rule shipped here catches six:

```
sequence_drift against six mutations of ci.yml    -- command output, 2026-09-08, Windows
case    old     new     rules fired / what moved
control passes  passes  -            unmutated
A       FAILS   FAILS   scope,shape  a fragment is renamed
B       passes  FAILS   order,shape  two commands of one step are swapped
C       passes  FAILS   shape        an unregistered step is added to installed-suite
D       passes  FAILS   scope,shape  a command is demoted to a comment
E       passes  FAILS   scope,shape  the adjudicator invocation is deleted
F       passes  FAILS   vacuity      the workflow is re-indented so the scanner sees no jobs

ci.yml untouched: True
```

Case `D` is the one that isolates the `scope` rule: the fragment is still **in the file**, so the old
search passed, and it has left the **sequence**, which is what this harness reproduces. Case `C`
isolates `shape`: every declared fragment is still present, in its own job, in order — only the
region's line count moved. Case `F` is the vacuity guard, and it is the rule this whole page is
about: the scanner keys off indentation, and a workflow it cannot read must redden rather than make
every rule above true of an empty set. All six are in `tests/test_gate_scripts.py`, so they run
inside `gates.suite`.

**The `order` rule is not independently detectable on today's regions, and that is worth one line.**
Every fragment sits inside a pinned region, so any reordering also moves a digest — case `B` fires
both. It is kept because the `shape` rule's message can only say *the digest moved*, and `order`
names the command. A diagnostic, not a second detector, and calling it a second detector would be a
phrasing tighter than the measurement.

**What is still not closed.** A `run:` block that means something different with the same words in
it passes all three rules, and no textual check of a workflow can see that. The only thing that could
is invoking the sequence, and the sequence is not addressable.

**Fatal rather than a warning, and that is the whole earlier change in one word.** The previous
guard's reasoning was that *"a harness that refuses to start because a list moved is a harness people
delete"*. That is wrong in the one direction that matters here: this script's output is a **coverage
table**, and the table gets quoted into the register and into this page. A number about the wrong
sequence is worse than no number, which is exactly what run `32808357572` produced.

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
`FAILED` line — it is quoted in the section above — but the only record of it in this repository was
that quotation, and a failure line transcribed into a prose document is an unchecked claim in
exactly the way R16 says a figure inside an image is. Under the new rule the demonstration had to be
**re-taken**, not re-read.

### And it was re-taken, on the commit that shipped the rule

```
run 34099756605, ubuntu-latest, CPython 3.12, at 34925f8      -- captured log, verbatim
  environments.test: holds 4 declared path(s), lacks 3 declared path(s) -- this is that
                     environment
  suite                                  DEMONSTRATED  mutated rc=1, restored rc=0
  test_environment_control               DEMONSTRATED  mutated rc=1, restored rc=0
  2 demonstrated, 0 INERT or UNRESTORED, 0 not automated

replicated: run 33379084166, 2026-08-31, same commit, a different weekly runner image
```

**`34925f8` is the commit that shipped `expect_failure_matching`**, so `DEMONSTRATED` here is not the
verdict that was withdrawn. It is only reachable through the marker rule: the harness had to find
`test_the_reader_that_would_spend_the_allocated_arm_is_wired` in the gate's own output before it
would call a non-zero exit a demonstration. *The evidence moved out of a prose transcription and into
the mechanism*, which is the whole of the correction.

The register's stamp for `gates.suite` is that run, and the `owed_forward` promise on the M3-PA
trajectory row is discharged by it — `paid 4`, against `owed 4`.

**What is still not done: the confound itself.** Removing it needs a probe that does not edit a file
the register anchors on, and the D-058 defect *lives* in that file. Naming the line is the fix that
works without moving the defect; it makes the verdict attributable and leaves `rc=1`
over-determined. **`rc=1` in the run above is still over-determined**; what is not over-determined
is the named line the harness required before printing the word.

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

## The claims gate's hole, closed — and what it did not close

The gate at rank one **was demonstrably partly inert**, from before it was ranked until this round.
An uncited latency figure in microseconds exited `0`; an uncited accuracy percentage in the same
position exited `1`. D-060 found it, [`docs/POSITIONING.md`](POSITIONING.md) reproduced it on a
second page, and `tests/test_claims_gate_coverage.py` pinned it so it could not quietly change. Two
vocabulary gaps caused it: `latency` was not a metric keyword, and a spelled-out `microseconds` was
not a unit.

**Both are now in the vocabulary.** `latency` and `duration` are metric keywords;
`nanoseconds`/`microseconds`/`milliseconds` are units. The refusal that had stood for five
measurements rested on a cost that was real and a premise that was circular — the seven documents (the count was published as six until a cold read found `docs/SOURCING.md` by checking the rule rather than the exit code)
below were false *only because the hole was open* — and **keeping a known blind spot open to
preserve the descriptive accuracy of the documents documenting it is debt that pays interest to
itself.** The maintainer withdrew it. All six were corrected in the same commit, and the three that
print a measured mutation battery had theirs **re-run** rather than having a digit edited.

D-052 refused to widen the arming rules, on the ground that arming on everything would relabel over a
thousand numbers nobody had adjudicated. **A narrow widening is a different object, and it was
measured before anybody argued about it** — because the deferred ledger is a ratchet that may not
grow, so a widening that armed even one new uncited number would either redden the build or force a
baseline upward, and the trajectory forbids the second.

```
tools/check_claims.py loaded by path, its arming rules replaced, every scanned file
read ONCE and both rule sets evaluated against the same bytes -- command output,
not a benchmark measurement. Re-derived immediately before the widening was taken,
because a fact nothing re-runs is the class this repository keeps finding stale.

  scanned set as read              2246 claim-shaped numbers across 72 files
    under the pre-widening rules   unarmed 1987 | unit-armed 171 | keyword-armed 88
    under the shipped rules        unarmed 1987 | unit-armed 171 | keyword-armed 88

  + latency, duration as keywords            0 numbers change class
  + microseconds/milliseconds/nanoseconds
    as units                                 0 numbers change class
  + both                                     0 numbers change class

  positive controls on that comparison, because a comparison that cannot detect a
  difference reports zero for either reason:
  + the word "the" as a keyword              726 change class
  + a unit rule matching anything           1905 change class
```

**The measured price of closing this hole was zero, and it stayed zero after it was closed.** No
build reddened, `DEFERRED_BASELINE` stayed at `189` across ten files, `VALUE_MATCHED_BASELINE` stayed
at `64` across three, and **no row was owed to `LEDGER_TRAJECTORY`** — a widening that moves the
register must record the round with its `by_citation`/`by_deletion`/`by_fencing`/`by_other` split,
and this one moved nothing to split. The totals in the block move with the tree; the committed
re-derivation is
`tests/test_claims_gate_coverage.py::test_the_measured_price_of_the_closure_is_still_zero`, which now
compares the shipped rules against the pre-widening ones and reds the first time a scanned document
acquires a latency figure the old rules could not see.

**Why it was free is more interesting than that it was free.** **Not one line of the scanned set
carrying `latency` or `duration` has a free-standing prose number within the proximity window**, and
**no prose number anywhere in the scan set is followed by a spelled-out sub-second unit**. Every
latency figure this tree publishes is either cited, written with a symbol unit the old rule already
armed, or inside a code span. The vocabulary and the figures never met. **How many lines carry the
words is deliberately not published**: it rises whenever a page describes the closure — this one
included — and it drifted twice while this section was being written. The two zeros are the
measurement, and `tests/test_claims_gate_coverage.py` re-derives them on every run.

**Which means the firing count on this tree is zero, so nothing was measured about whether the
widened rule is well calibrated.** What the block establishes is that *this tree contained no
latency-shaped claim in prose*, which is a statement about the documents and not about the rule. The
rule is demonstrated by injection instead — see the batteries in
[`docs/EVALUATION.md`](EVALUATION.md), [`docs/POSITIONING.md`](POSITIONING.md) and
[`docs/DEFINITION-OF-DONE.md`](DEFINITION-OF-DONE.md), all re-run.

### The false-positive cost, measured rather than assumed

A wider arming rule demands citations for numbers that are not claims, and that friction is how a
gate gets disabled. On the scanned set the cost is exactly zero, because nothing fired — which is a
measurement of the documents, not of the rule. So the same comparison was run over the `132` files
this project writes that the scan set does **not** cover — `tests/`, `tools/`, `bench/`,
`benchmarks/`, `examples/`, `.github/` — as a proxy for prose this repository plausibly produces:

```
same one-read/two-evaluations comparison, over everything outside SCAN_GLOBS
  4528 claim-shaped numbers across 132 files
    12 change arming class: 11 newly armed, 1 re-attributed unit -> keyword

  armed on a real duration figure, which is the rule working              7
    "that is 30 milliseconds of headroom" and two sibling fixtures        3
    the coverage module's own injected probe                             1
    the probe quoted in tools/check_claims.py's docstring                 1
    "41 microseconds, 139.60 milliseconds" in the unit rule's comment     2

  armed on a number that is not a claim -- FALSE POSITIVES               4
    2026 / 08 / 25, the three fragments of an ISO date, armed because
      the word "latency" is within 48 characters of it in an
      assertion message                                                  3
    font-weight="400", armed by "median latency" later on the line       1

  re-attributed, so no new citation demanded                             1
    41.20 in "median latency 41.20 ms": unit-armed before, keyword now   1
```

**Four false positives in `4528` numbers — `0.088` %, and worth naming rather than rounding away.**
Every one is a **proximity** artifact: the keyword rule arms a *neighbourhood*, so a date or a font
weight sitting beside the word `latency` becomes a claim. The unit rule produced none, which is the
argument for reading a number's own shape wherever a rule can. Three of the four are in a sentence
**this round wrote** — an assertion message that mentions `latency` and a date in the same breath —
which is the friction demonstrated rather than estimated: had that sentence been in a scanned file,
it would have reddened the build and demanded a citation for a calendar date.

All twelve are outside `SCAN_GLOBS`, so the gate never sees them and today's cost is zero. **This is
a bound on the friction, not an incident**, and it is measured on one repository's prose rather than
on prose in general.

### Six documents corrected, and the disposition discharged

The widening is one edit to `tools/check_claims.py`. What it cost is that six shipped files
immediately stated something false. All six were corrected in the same commit:

| file | what it said | what it says now |
|---|---|---|
| `README.md` | a latency in microseconds *"passes untouched"* | both cases fail; residue published |
| [`docs/EVALUATION.md`](EVALUATION.md) | *"an uncited latency in microseconds passes"* | battery re-run, row `D` is `rc=1` |
| [`docs/DEFINITION-OF-DONE.md`](DEFINITION-OF-DONE.md) | a battery whose latency row is `rc=0` | re-run rows appended below the originals |
| [`docs/POSITIONING.md`](POSITIONING.md) | a battery whose row `D` is `rc=0` | battery re-run, row `D` is `rc=1` |
| [`docs/SECOND-READER.md`](SECOND-READER.md) | the same injection returning zero | the finding, and the round that closed it |
| [`docs/DECISIONS.md`](DECISIONS.md) | D-060's record; D-070 and D-072 re-quote it | corrections appended, no record added or restated |

**No digit was edited.** Each battery row that inverted was produced by re-running the injection
against the same file, one mutation at a time, restored from bytes read before it and md5-verified.

### What the closure did not close

Two keywords and three units. That is the size of it, and **a closure reported as total would be the
same defect one level up**. Injected one sentence at a time into `README.md`,
[`docs/EVALUATION.md`](EVALUATION.md), [`docs/POSITIONING.md`](POSITIONING.md) and
[`docs/DECISIONS.md`](DECISIONS.md), all four files agreeing:

| still invisible | example | why |
|---|---|---|
| plurals | `Median latencies ... fell to 41.37` | `keyword_positions` matches whole words; `latencies` and `durations` are not `latency` and `duration` |
| a bare `seconds` | `A full sweep took 41.37 seconds` | refused on purpose — it would arm dates, interval lengths and any number followed by the word |
| speedup multipliers | `... is 41.37x faster` | not a free-standing number at all, so no arming rule is consulted; the fix is to the token rule, which the value ledger shares |
| memory and byte figures | `... holds 41.37 KB` | `KB`/`MB`/`bytes` were considered for the unit rule and not taken |
| unlisted metric words | `p99`, `QPS`, `overhead`, `cold start`, `time to first token` | the rule that caught `F₁ > 96 %` reads a number's shape; this one reads a vocabulary, and a vocabulary is a list somebody finishes writing |
| a metric named once in a table header | any cell under it | neither arming rule can see a column heading; `--classify` reports this as the larger population |
| anything fenced or code-spanned | this table's own examples | D-052: mechanically indistinguishable from hiding |

Each of the first four is pinned by
`tests/test_claims_gate_coverage.py::test_the_residue_the_closure_left_behind_is_still_uncaught`, so
a later widening that reaches one of them turns a row red and has to update this table.

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

## The thirty-ninth gate: the account of a round is now an artefact a gate reads

`gates.run_summary` is `python tools/run_summary.py --check`, in the `lint` environment, at
`cost_rank` 37 of 39.

**The defect it is for is not in the code, and that is why it went unguarded for three rounds.**
Eight gates check the code, the numbers, the splits, this register and the cold-read ledger.
Nothing checked that the round said what it did — and D-095, then the first attempt at Phase B,
then its second, each kept the work and lost the self-assessment, for three unrelated reasons: a
retry cap on over-long output, a budget that ran out mid-work, a budget that ran out after the work
was filed. Each time the code survived because it happened to be in the tree, which is luck.

So execution state is now separate from narrative reporting. A workstream writes
`<label>.json` into `.github/run-summaries/<round>/` as its **penultimate** tool call, before any
long prose, and an agent that then dies formatting paragraphs has already filed. The gate validates
the shape of every committed record — unknown key refused, exactly twelve sampling claims, all
eight gate keys, a `label` that matches its own filename, a dotted `run_ids` entry that resolves in
`bench/results.json` — and refuses a field list in `CONTRIBUTING.md` that has drifted from the code.

**What it deliberately does not fail on, because the omission is the design.** A workstream that
filed nothing, and one that filed a stub saying nothing, are both *printed* and neither is red. A
round in which an agent died has to stay committable exactly as it happened; if `absent` reddened
the build, the cheapest route to green would be deleting the roster entry, and the gate would
become a machine for hiding what it exists to reveal. What it does enforce is that those two states
are **different verdicts** — which is precisely the distinction `--check` could not make for the
cold-read ledger, and D-096 records what that cost across two rounds.

**The rank is an argument against the gate rather than for it.** The workstream that wrote the gate
wrote its rank, so it is placed *last* in the `evidence_apparatus` bucket: every other gate there
protects a demonstration that some other check can fail, and this one protects a narrative record,
which is one step further from any user than any of them. `ruff` and `ruff_format` move to 38 and
39 and nothing else in the ordering moves.

### It has no in-situ evidence, and the local run that is not evidence

```
python tools/gates.py --mutate run_summary        -- command output, 2026-09-09, Windows,
                                                     in a MIRROR of the working tree
  run_summary                            DEMONSTRATED  mutated rc=1, restored rc=0
  1 demonstrated, 0 INERT or UNRESTORED, 0 not automated
```

The probe puts an unreadable `status` on the one committed summary and requires the gate's own
output to contain `tools/run_summary.py`'s `FAILURE_MARKER`; the marker's two copies — the register's
and the script's — are pinned against each other by `tests/test_run_summary.py`, because a marker
that drifts turns every future demonstration into `INERT` while the register reports a gate nobody
can demonstrate.

**That run is exactly the evidence R11 says does not count**, and it was taken in a *mirror* rather
than in the working tree because several agents were editing this checkout at the time and
`--mutate` restores from bytes read beforehand — the lost-update hazard D-098 records happening to
`docs/DECISIONS.md`. The debt is `20 → 21` and one gate is owed forward; `gate-mutation.yml`
triggers on `.github/gates.toml`, `.github/workflows/*.yml` and `tools/gates.py`, all three of which
this commit touches, so the run that lands this work is the run that owes it.

### The two owed forward were paid by a log nobody had read, one round after the last time

`M3-PB` registered `figures` and `memo_identity` with no evidence and wrote that the run landing
that commit would take it. It did:

```
gh run view 34308556192, job "Mutate the lint gates, in the lint environment"   -- captured log
  claims                                 DEMONSTRATED  mutated rc=1, restored rc=0
  figures                                DEMONSTRATED  mutated rc=1, restored rc=0
  gate_manifest                          DEMONSTRATED  mutated rc=1, restored rc=0
  memo_identity                          DEMONSTRATED  mutated rc=1, restored rc=0
  mypy                                   DEMONSTRATED  mutated rc=1, restored rc=0
  ruff                                   DEMONSTRATED  mutated rc=1, restored rc=0
  ruff_format                            DEMONSTRATED  mutated rc=1, restored rc=0
  splits_manifest                        DEMONSTRATED  mutated rc=1, restored rc=0
  8 demonstrated, 0 INERT or UNRESTORED, 0 not automated
push of 4ef57c8, 2026-09-09T03:48:48Z
```

Three things a reader should not have to take on trust. **First, the overall run is RED** — on a
different job, "Reintroduce each historical breakage against a real sdist", which `017cb37` is the
fix for; the lint-environment job these verdicts come from is green on its own, and a harvest that
quoted only the green half without saying so would be the thing this page keeps finding. **Second,
the stamp is at `4ef57c8` and HEAD is `017cb37`, two commits later**; the diff between them is
`MANIFEST.in` and two test files, none of them in either gate's dependency set, so the gate
demonstrated there is the gate shipping here — and that stops being true the moment this commit
lands, because it moves `.github/gates.toml`. **Third, this is the same failure as a fortnight ago
and it is two days faster.** The evidence sat in the Actions tab while the register printed the
debt. Nothing here closes that: harvesting is still a person deciding to run `gh run view`.

### What this gate cannot do, said where a reader meets it

**It makes a lost report recoverable. It does not make a report happen.** An agent that dies before
its penultimate tool call files nothing, and no gate in this repository can tell that from an agent
that was never launched. The roster narrows it to *who was expected* and narrowing is not closing:
a roster is written by hand, before the round, by somebody who may be wrong about it — and this
round's roster was written by a workstream rather than by the launcher, so it declares itself
incomplete and `--report` prints its absences as a lower bound. **Closing it needs the launcher to
write a start record when it spawns an agent**, at which point `absent` splits into *started and
never filed* and *never started*. That is a change to whatever runs the round, and nothing inside
this repository can make it.

Two smaller holes, named rather than implied. A JSON summary an agent writes about itself is still
self-assessment — cheaper to write, not more trustworthy. And `.github/run-summaries/` is in none of
`tools/check_claims.py`'s `SCAN_GLOBS`, so a number inside a committed summary is an unbacked claim
that reddens nothing: the shape R16 was written for, one channel further out, priced and not closed
here because `SCAN_GLOBS` carries two ratchets this gate's workstream does not own.

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

## The forty-first gate: a crashed agent is now a different fact from a silent one

`gates.agent_summary` is `python tools/run_summary.py --check-agent-summary`, in the `lint`
environment, at `cost_rank` 39 of 41.

**It exists because the thirty-ninth gate's own `blind_to` says it cannot do this.** That entry
reads, in as many words: *"an agent that dies before its penultimate tool call files nothing, and
neither this gate nor anything else here can tell that from an agent that was never launched.
Closing it needs the LAUNCHER to write a start record when it spawns an agent; that is outside this
repository."* This is the reader for that record.

`round.toml` says who was **expected**. `exits.toml`, beside it, says who **finished** — a table of
label to process exit status, written by whatever ran the round. With both, `absent` splits into
three facts that were one:

| exit status | summary on disk | verdict |
|---|---|---|
| non-zero | none | **crash.** Printed with its code. Never a build failure |
| non-zero | valid | killed between the JSON and the prose. The record survives; printed |
| non-zero | half a file | killed mid-write. `unreadable`, and that is **not** `absent` |
| `0` | none, or broken | **defect. The build goes red** |
| none recorded | anything | *unattributed.* Exactly as ambiguous as before; counted |

**The one rule is the fourth row and it is the only thing this gate adds.** `invalid` and
`unreadable` already redden `gates.run_summary`, so the non-redundant delta over its neighbour is a
single state — a workstream that ran to completion and filed nothing — and the register declares
`redundancy = "partial"` rather than `sole` for that reason.

### What it is worth today, which is less than it will be

**No real round in this register carries an exit record.** Nothing in this repository writes
`exits.toml`; that is still a job for whatever spawns the agents, and it still does not do it. Both
committed rounds are therefore `UNATTRIBUTED`, the gate concludes nothing about either, and it
prints that count on every run rather than passing in silence.

So the demonstration is against a committed **control**,
`.github/run-summaries/_control-agent-crash/`, and the distinction matters: it establishes that the
code can fail, not that a round anybody ran was ever checked. The control's roster declares the
state each of its four labels must land in, including the one the whole mechanism turns on — a
writer killed mid-write is `unreadable` and a writer that never started is `absent`. Two states
collapsing into each other is invisible everywhere else in the tree, because every other consumer
treats both as "not a report" and moves on.

`--check-agent-summary` **refuses a register with no such control**, so the gate cannot be disarmed
by deleting the only input it can currently fail on. `tools/run_summary.py --check` skips
`_`-prefixed directories, because the control holds a deliberately truncated JSON file and the gate
that refuses broken files may not be the gate that reads the fixture built out of them.

### It carries in-situ evidence, taken by the push that created it

The probe flips one integer in the control's exit record: `killed-before-filing` goes from `137` to
`0`, so a workstream that filed nothing is reported as having exited cleanly. That is the narrowest
edit reaching **this** gate's own rule rather than any rule it shares with its neighbour — the
summary is still absent and the control's declared state is still `absent`; the only thing that
moved is whether the absence is somebody's bad luck. A mutation that deleted the summary instead
would fire the control-expectation rule as well, and a demonstration that fires two rules at once
does not say which one it demonstrated.

```
lint/agent-summary.log, from GitHub Actions run 34408932625 at commit 5a268cd.
Read out of the uploaded artifact, not inferred from a green tick.

  gate:      agent_summary
  command:   python tools/run_summary.py --check-agent-summary
  expect:    fail          must say: agent-summary register refused
  verdict:   demonstrated  mutated: rc=1   restored: rc=0
  captured:  2026-09-09T21:49:16+00:00     platform: linux python 3.12.14
  edits:     ['.github/run-summaries/_control-agent-crash/exits.toml:replace']

  and the captured output names WHICH rule fired:
    killed-after-filing   exit 137  CRASHED AFTER FILING (complete)
    killed-mid-write      exit 137  CRASHED MID-WRITE (unreadable, and that is not absent)
    exited 0 and filed: ['exited-clean-and-filed']
    PROBLEM: killed-before-filing: exited 0 and its summary is ABSENT.
```

**The waiver named when it would be paid and it was paid the same session.** `gate-mutation.yml`
triggers on `.github/gates.toml`, `.github/workflows/*.yml` and `tools/gates.py`, all three of which
the commit creating this gate touched, so the push that landed the work took the demonstration —
the third consecutive round to close its own debt this way, after the thirty-ninth and fortieth
gates did it at run `34352662794`. The debt went `20 → 21 → 20` inside one session and the ceiling
is unmoved. **The quota of three is still not met**, which is what the waiver on the trajectory row
is for; a round that adds one gate and demonstrates that one gate has paid its own way and nothing
else's.

### How it fails

**A vacuous summary satisfies it.** `--template` output filed unchanged is a valid schema-compliant
record, so an agent that exits `0` having said nothing passes. Refusing a stub would make the
cheapest route to green a paragraph of filler, which is the opposite of what the template is for.

**A roster that declares itself incomplete escapes the exit-record requirement.** The rule *"a
roster claiming `roster_complete = true` must carry an exit record"* is the only thing forcing the
file to exist, and both real rounds declare `false` — honestly, because a workstream genuinely
cannot enumerate its siblings. A launcher that never wants to be accountable never has to be.

**The exit record is a self-report by the launcher and nothing audits it.** A launcher writing `0`
for a process it never waited on gets a green build and a false accusation every time a summary is
missing.

---

## Running it yourself

```
python tools/gates.py --check                       validate the register (the CI gate)
python tools/gate_packaging_mutation.py --print-regions --out DIR  re-pin the reproduced regions
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
python tools/gate_packaging_mutation.py --check-drift --out DIR  is the reproduction still ci.yml's sequence?
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

**THE LEAD ITEM IS THAT THIS ROUND MEASURED ALMOST NOTHING. It read a log.** The count went from
`12 of 36` to `16 of 38` and every one of the four new demonstrations was taken by a scheduled
workflow on 2026-09-07, before this round started, at a commit this round did not write. The work
here was harvesting, re-stamping, correcting three documents against what the log said, and
registering two gates somebody else wrote. **Nothing in this round ran a mutation on a runner and
nothing in it could.** That is not a complaint about the method — R11 says a developer machine does
not count, and this machine is a developer machine — but a reader should not mistake `16 of 38` for
four gates this round demonstrated.

**And the harvest is the failure it describes.** The evidence sat in the Actions tab for a fortnight,
green, with artifacts uploaded, while `--check` printed `12 of 36` on every CI run. The previous
version of this page had already written *"a scheduled workflow whose artifacts nobody harvests is
indistinguishable from one that never ran"* — and then, for two weeks, was that. **Nothing closes it
for the next round either.** The `report` job still prints how to record a run and nothing reads one.
The whole of this round's count movement is one person running `gh run view --log`, and the next
round's depends on somebody doing it again.

**Two gates were added and neither carries evidence, one of them at rank 3.** `gates.figures` is the
highest-ranked gate in this register that has never been demonstrated anywhere except on this
machine, and it got there through a rule this round made waivable. The escape is narrow and attached
to a promise, and it is still an escape: **the top-of-ranking rule was absolute before this commit
and is not now.** If a future round renews `added_gates` instead of paying it, arithmetic will not
say so — a reader comparing two trajectory rows will.

**Every local demonstration in this round was run in a mirror of the tree, not in the tree.** The two
new gates' mutations were verified by copying the working tree to a scratch directory and running
`--mutate` there, because `gates.memo_identity`'s probe edits
`src/acronymkit/governed/dictionary.py` and another workstream was editing that file at the time.
`--mutate` restores from bytes read beforehand, and a restore that overwrites somebody else's
concurrent write is a worse failure than a weaker probe. The mirror excludes `data/`, so
`memo_identity` was demonstrated against the generated fixture corpus alone — which is what a runner
sees, and is smaller than what this page's own author sees.

**The CRLF class bit again in this round and is still not gated.** Six files were silently rewritten
to CRLF by `Path.write_text` on Windows; `git status` stayed clean; the only thing that noticed was
one assertion in a scratch battery. It is written up in
[the rest of the battery](#the-rest-of-the-battery) because it is the most repeated shape on this
page, and there is still no check on working-tree line endings.

**Twenty-two of the thirty-eight still carry no in-situ evidence, and twenty of those cannot.** Five
`inline`, thirteen `manual`, two `control` — none mutable by this harness, and two more are the
newly added gates whose demonstration is owed. The number that moved from zero to thirteen to twelve
to sixteen is the number of gates that were *always* demonstrable, plus the three the last round
extracted, and the honest reading is not *"nearly half way"* — it is *"every gate whose own command
a runner can invoke, and the remainder needs a different kind of work"*. What the five remaining
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
> sdist, where it would be asserting a fact about a machine the reader does not have. The share is
> described rather than counted, which is the only honest form available: a figure that changes with
> who reads it is not a figure.
>
> **AND THE HALF THAT WAS KEPT WAS ALSO WRONG.** This blockquote used to end "The `216` is kept
> because it is a repository fact." A cold reader checked the one number the paragraph told you was
> safe: `git ls-files | wc -l` is `231` at HEAD and `231` at the commit this round started from. The
> denominator was retained **on the explicit ground that it reproduces**, by an edit whose whole
> subject was a number that does not, and nobody re-ran it. Both instances were code-spanned, so no
> ratchet could see either. The count is now `231`, and it will go stale the same way the moment a
> file is added — which is the argument for the sentence above rather than for a fresher figure.

`.gitattributes` declares `*.json text eol=lf` and says the reason is the schema-copy gate.
`git ls-files --eol` reports a large minority of the `231` tracked files as `w/crlf`, and
`schemas/acronym-engine-result.schema.json` was one of them — so that gate was **red in this working tree** and nothing could see it, because it
was a heredoc. `git status` stays clean throughout, because git normalises on compare. The same thing
silently no-opped five cases of this page's own mutation battery — **and did it again on
2026-09-08, from the other end**, when `Path.write_text` rewrote six of this round's own files to
CRLF and one scratch assertion was the only thing that saw it. Nothing checks it: there is no gate
on working-tree line endings, and the one gate that would notice only notices for two files.

**This page has now been wrong about `gate-mutation.yml` twice, in the same direction, for the same
reason.** The first time it said the workflow had never run; it had run, green, with `13`
demonstrations captured, and this page asserted a zero for a whole phase. The second time — this
one — it said four gates were *owed forward on a CI run that has not happened yet*; that run had
happened, twice, and this page asserted a debt for a fortnight. **Neither error was detected by
anything here, because nothing in this repository reads a run log.** The `report` job prints how to
record a run, which is a nudge and not a gate. Two instances of one failure is a pattern rather than
an accident, and the pattern is that **the mechanism works and its output goes unread** — which is
worth more attention than either count it corrected.

**`--evidence-provenance` reads `0 of 16` and that number is already stale as you read it.** Every
stamp names commit `34925f8`, which was HEAD when the harvest was taken; this commit moves
`.github/gates.toml`, `tools/gates.py` and `.github/workflows/ci.yml`, so on the next run most of the
sixteen go back to *predates a change*. The flattering number is an artefact of the moment the
snapshot was taken, and it is printed here with that caveat rather than as a result. It remains a
note rather than a gate: it says which evidence is worth re-taking, never that any of it stopped
working, and nothing here could. Four of the sixteen have a dependency set that cannot be closed at
all — `python -m pytest` and `python -m mypy` name no file — so for those the honest answer is *the
whole tree changed*, printed as such.

**The provenance check needs git history and CI checkouts are shallow.** `actions/checkout` fetches
depth 1 by default, so every row would read `unknown` unless the job asks for more. The `report` job
does; nothing enforces that a future job will, and a table of `unknown` is honest and useless.

**Local re-running can falsify in-situ evidence and cannot confirm it, and this page uses it only in
that direction — but that direction was exercised on a tree several agents were editing.** Two runs
of the same suite an hour apart on this machine gave `5392 passed, 10 skipped` and
`5391 passed, 11 skipped`, because another workstream's files landed in between. Every number on
this page taken from a full-suite run carries that uncertainty.

**The packaging job's ASSERTIONS are invoked, its SEQUENCE is still reproduced, and the check on
that reproduction is still weaker than an invocation.** Scope, order and shape close the reordering
and the added step; **a `run:` block that means something different with the same words in it passes
all three**, and no textual check of a workflow can see that. The pin is also silenceable by design:
`--print-regions` regenerates it, and nothing grades the person who presses it.

**The `shape` rule is scoped, which means most of `ci.yml` is outside it.** Three regions are pinned
and `build`'s three wheel steps are deliberately not among them, because this harness does not
reproduce them. An edit there moves nothing here — correct, and also a hole with a name.

**This round did not run the packaging harness locally at all.** It installs into the ambient
interpreter with `--force-reinstall`, on a machine several agents were running suites on, and its
control was red here on the last attempt. Every figure in that section comes from run
`34099756605`'s captured log, read rather than reproduced.

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
