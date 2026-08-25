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

**No gate in this repository carries in-situ evidence today. The count is zero.** Every mutation
recorded below was run on a developer machine, which is exactly the evidence rule 11 says does not
count — three of the four defects that motivated this whole exercise were invisible on a developer
machine. The workstream that built this could not run GitHub Actions, so it could not produce the one
kind of evidence it exists to produce.

What ships instead is the mechanism that produces it, and a count printed on **every** CI run so the
absence is visible rather than implied:

```
python tools/gates.py --check                                -- command output
  gate manifest: 36 gate(s) across 21 environment(s) in 5 workflow file(s)
  mutation kind: automated 13, control 2, inline 8, manual 13
  demonstrable by this harness: 13 of 36
  CARRYING IN-SITU EVIDENCE:   0 of 36   <- R11 is not satisfied for any gate here
```

The first scheduled run of `.github/workflows/gate-mutation.yml` is what changes that line. Until it
does, this page's own claim is the one to attack.

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

**The lead item is at the top and it is not a footnote: zero gates carry in-situ evidence.** Everything
here is a mechanism plus a promise. A reader who holds that a register with no in-situ rows is exactly
the thing it was built to replace — a document asserting coverage that nothing has demonstrated — is
reading it correctly, and the answer is the count printed on every CI run rather than an argument.

**Nothing in `gate-mutation.yml` has ever run.** It was written by a workstream that could not push,
could not dispatch a workflow, and could not read a run log. Every YAML file in this repository that
has ever been wrong was wrong in exactly that state. The failure modes to expect on the first run are
ordinary ones — a step name with a character YAML reads as structure, a path that exists on Windows
and not on the runner, a job that needs a dependency the mirrored setup does not install — and the
harness is deliberately noisy rather than tolerant so they surface as red rather than as a skipped
step.

**The packaging job reproduces two gates rather than invoking them.** `build`'s sdist step and the
whole `installed-suite` job are multi-step sequences with no single command, so
`tools/gate_packaging_mutation.py` rebuilds the sequence. A reproduction is not the gate: somebody
edits `ci.yml` and not the script, and the two drift with nothing to say so. One piece of that is
guarded — the script re-reads `EXPECTED_NON_PASSING` out of `ci.yml` and reports drift from its own
copy — and the rest is not.

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
instances of. Seven of the fifty-one tests in `tests/test_gate_manifest.py` skip there on a narrow
mark rather than erroring, which is the right behaviour and not a fix. `MANIFEST.in` was not this
workstream's file; one line adds it, and until somebody writes that line this is the fifth
instance.

**The register is not scanned by the claims gate.** `tools/check_claims.py` scans `bench/splits.toml`
and not `.github/gates.toml`, so any number written into the register is unchecked. This page is
scanned; the register it describes is not.
