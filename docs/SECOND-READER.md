# The second reader

This project has been single-adjudicator on its corpus, single-verifier on its agent reports and
single-lineage on its adversarial passes. It has said so in every round and resolved it in none —
the sentence appears in `docs/DECISIONS.md` D-054, D-056 and D-057, each time under *How it fails*,
which is where an unowned problem goes to be acknowledged rather than fixed.

This page is the fix, and it is deliberately the cheapest of the three shapes that would work. It
defines a **cold read**: one reader, given the document and the gates and nothing else, asking what
would have to be true for the document to be wrong. It names when that happens, what the reader
does, what the reader may change, and what one round of it costs.

The first cold read was executed against the tree of 2026-08-24. Every check in the protocol below
is one that caught something in that pass, and the defect it caught is named beside it. A checklist
assembled from defects that were actually found is worth more than one assembled from imagination,
and it is also shorter.

---

## 1. Why a *cold* reader, specifically

The gates in this repository are good and they are the wrong instrument for this class of defect.
`tools/check_claims.py` adjudicates numbers; `tools/splits.py --check` adjudicates corpus roles;
`mypy`, `ruff` and `pytest` adjudicate code. **None of them can read a sentence.**

`bench/splits.toml`'s `[corpora.socrata]` entry already states the general form, having been bitten
by it inside a single day:

> a prose claim about a tool's configuration is exactly the kind of number-free assertion no ratchet
> can see. The general form is unfixed: any other sentence in this repository describing what a tool
> scans, refuses or ignores can go false the same way, silently.

D-058 recorded the same shape a second time and declined to propose a mechanism, on the grounds that
two instances is a shape rather than a coincidence. This page is that mechanism.

**And the reader has to be cold.** The author of a sentence re-reads their intention, not their
text. The measured consequence is in section 6: the single most load-bearing defect the first pass
found had been in `docs/EVALUATION.md`, unaltered, since the commit that created the file — through
six audits, two adversarial passes and four documentation sweeps, every one of them run by somebody
who already knew what the sentence was trying to say.

---

## 2. The three shapes, and why this one

In descending order of value, and the reason each is or is not adopted:

| Shape | Adopted | Cost per round | Why |
|---|---|---|---|
| A human reviewer for anything user-facing | **no** | a person, unbounded | There is no second person on this project. Recording it as the best option and not having it is honest; pretending the next two are equivalent is not |
| An adversarial pass by a differently-prompted agent with no access to the constructing agent's reasoning | **yes** | one workstream slot | This is what produced the findings below. It is available, it is repeatable, and its cost is a slot the round already spends on something less valuable than this |
| The cold-read protocol, written down and executed by whoever is here | **yes, as the floor** | see section 6 | The protocol is the same either way. The agent slot is how it gets run when a slot exists; this page is what gets run when one does not |

The second and third are the same procedure under different staffing, which is the point of writing
the procedure down rather than the staffing.

---

## 3. The trigger

Two triggers. The second one is the half the measurement bought, and it is the half a policy written
from first principles would have omitted.

**Trigger A — the diff.** Any round whose diff touches a user-facing file ends with a cold read of
exactly the user-facing files it touched, before the recorder writes the round's D-record.

```
git status --porcelain -- README.md CHANGELOG.md CONTRIBUTING.md SECURITY.md pyproject.toml docs
```

**CORRECTED IN PLACE ON THIS PAGE'S FIRST EXECUTION AS POLICY, AND THE CORRECTION IS THE PAGE'S
BEST EVIDENCE FOR ITSELF.** The command published here was
`git diff --name-only <round-base>..HEAD -- ...`, and it **returns nothing at the only moment it is
supposed to run**: section 3 places the cold read *before* the recorder commits, so `HEAD` is still
the round base and the range is empty. A reader who trusted it would have concluded the round
touched no user-facing file and stopped. Worse, `git diff` cannot see a file that does not yet
exist under either revision — and the first round to run this policy introduced its most important
page as a **new file**, which the published command would have missed even with the range repaired.
`pyproject.toml` is added to the pathspec for a third reason found the same way: its `description`
is the sentence PyPI renders, it was rewritten that round, and no trigger on this page would have
looked at it.

The correction is left visible rather than swapped in silently. A procedure that cannot execute at
the moment it fires is the same defect class this whole page exists to catch — a claim about a
tool's behaviour that no ratchet can see — and it shipped **inside the fix for that class**, written
by somebody who had just spent a round finding instances of it elsewhere.

Minus `docs/DECISIONS.md` and `docs/AUDIT-*.md`, which are historical records rather than
instructions to a user, and minus `docs/notes/*.md`, which are scoped technical notes read by
somebody who arrived from a link that already warned them.

**Trigger B — the rotation.** Each round also cold-reads **one** user-facing file the diff did
*not* touch, taken from a fixed rotation, oldest-read first. One file. The set turns over in as many
rounds as there are files in it.

Trigger B exists because of a count, not a hunch. Of the fifteen defects the first pass found, seven
were in files that round's diff never opened — `docs/OFFLINE.md`, `docs/SUPPORT_MATRIX.md`,
`docs/ENTERPRISE.md` and `CONTRIBUTING.md`, none of which any workstream had touched. **A
diff-scoped trigger alone would have missed just under half of what was there**, and it would have
missed it for the structural reason that a document nobody edits is a document nobody re-reads.

The rotation set, in order:

```
README.md · docs/EVALUATION.md · docs/OFFLINE.md · docs/GOVERNED_NAMING.md
docs/SUPPORT_MATRIX.md · docs/JAVA_INTEROP.md · CHANGELOG.md · docs/ENTERPRISE.md
docs/QUICKSTART_GOVERNED.md · docs/INSTALL.md · docs/ARCHITECTURE.md
CONTRIBUTING.md · SECURITY.md · docs/DEFINITION-OF-DONE.md
```

The reader records which file the rotation served at the top of their findings, so the next round
knows where the cursor is. That is the whole of the state this policy carries.

---

## 4. The protocol

### 4.1 Per document, four questions

Answer them in writing. They are ordered so that the last one is impossible to answer honestly
without having done the first three.

1. **The strongest claim it makes**, quoted exactly, with its line number.
2. **What a reader would have to believe** for that claim to be true — stated as a list of separate
   beliefs, because a compound claim usually has one weak conjunct and four strong ones.
3. **Whether each belief survives the gates.** Run them. The six local ones are listed in
   `CONTRIBUTING.md`; what CI runs, what each check is blind to, and whether it has ever been shown
   failing where it runs are in [docs/GATES.md](GATES.md).
4. **The single sentence in the document most likely to be false**, and the command that checked it.

Question 4 admits no abstention. A document with nothing to nominate has not been read.

### 4.2 The six checks, each named for the defect it caught

Every one of these is mechanical, and every one caught something on the first pass. Where a check is
listed with a finding, the finding is the reason the check is on the list.

**C1 — An exhaustive word over an enumeration. Count both sides.**
Search for *every*, *all*, *any*, *none*, *always*, *never*, *only*, *the whole*. For each, count the
things enumerated and count the population. They are frequently different.
*Caught:* `docs/OFFLINE.md` and `docs/ENTERPRISE.md` claim the air-gap job drives "every CLI
subcommand"; the probe in `.github/workflows/ci.yml` drives thirteen of the sixteen commands
`acronymkit --help` lists, omitting `governed-batch`, `governed-audit` and `normalize-name`.
`docs/OFFLINE.md` scans "all 27 shipped modules"; `find src/acronymkit -name '*.py' | wc -l` returns
forty. `docs/SUPPORT_MATRIX.md` lists "all of" nine commands on a sixteen-command CLI.

**C2 — Two documents describing one mechanism. Diff the descriptions.**
When two pages describe the same job, gate or invariant, put the sentences side by side. One of them
is usually older than the mechanism.
*Caught:* `README.md` says the `zero-dependency` CI job asserts purity "after a full generate +
extract + backronym + disambiguate cycle"; `CONTRIBUTING.md` says "after a generate + extract round
trip"; the job does generate and `extract_definitions` and nothing else. The two documents disagreed
and the shorter one was right.

**C3 — A pasted output. Run it.**
Any block whose comment shows what the library returns is a claim with an executable refutation.
Paste it into the interpreter.
*Caught:* `README.md`'s `synthesize_backronym("NEXUS")` example. Under both the engine the section
builds and a stock `Config()`, the shipped library returns `'nab ear xis ugh sac'`, not the
`'nag ear xenon urn sad'` printed beside it. This is the defect class D-055 found in
`docs/GOVERNED_NAMING.md` and fixed there; nothing checked the other pages.

**C4 — A number published beside the command that derives it. Run the command.**
This is the highest-yield check per second spent, because the document has already told you how to
falsify it.
*Caught:* `docs/EVALUATION.md` publishes a source-line total "re-counted for this revision with
`find src/acronymkit -name '*.py' | xargs wc -l`, because the previous figure here had gone stale".
The named command does not produce the published total — on the current tree or on the commit that
introduced the sentence. The numerator beside it is exact.

**C5 — A pointer. Follow it.**
"the commands that derive them are in X", "the full breakdown is in Y", "see Z". Open the target and
find the thing.
*Caught:* `README.md` sends the reader to `docs/EVALUATION.md` for the commands deriving three
structural counts; one of the three is there. `README.md` describes `docs/EVALUATION.md` as "every
measured number"; `bench/results.json` holds five hundred and thirty-six saved runs and that page
cites ninety-nine of them by run id.

**C6 — A prose claim about a tool's configuration. Read the configuration.**
No ratchet counts words. Every sentence saying what a tool scans, checks, refuses or ignores is
unguarded by construction.
*Caught:* `CONTRIBUTING.md` said `mypy` runs over `src/acronymkit`; `pyproject.toml` sets
`files = ["src/acronymkit", "tools", "bench"]`. `CONTRIBUTING.md` non-negotiable 6 forbade network
access in `tools/`; `tools/fetch_data.py` calls `urllib.request.urlopen`, which is its entire job.
Both are corrected in this commit.

### 4.3 One mutation, in situ

Before trusting any gate a document leans on, make it fail where it runs (R11). Not locally in
principle — in the tree, with the failure captured, and reverted in the same sitting.

One asymmetry is worth stating, because [docs/GATES.md](GATES.md) records that no gate here carries
in-situ evidence yet and a developer machine is the environment R11 says does not count. That is
true of a mutation showing a gate *catches* something. It is the other way round for a mutation
showing a gate is *blind*: a developer checkout has every file the gate scans and every dependency
it needs, so it is the most favourable environment the gate will ever see. A blind spot demonstrated
there is a blind spot everywhere.

*Caught:* both `README.md` and `docs/EVALUATION.md` claim CI fails the build when a performance
figure "anywhere in the docs or the source" is not traceable to a benchmark run. Injecting one
sentence of invented latency into `README.md` and running `python tools/check_claims.py` returns
zero and reports every number backed. The gate's own docstring says the honest claim is that nothing
is dropped silently rather than that everything is checked; two user-facing pages state the stronger
version. The positive control was run in the same sitting — an armed uncited figure in the same
position fails with exit 1 — so the finding is that the arming vocabulary does not reach the claim,
not that the gate is broken.

---

## 5. What the second reader may change, and what they may not

- **Fix** an outright falsehood in user-facing prose, and name each one in the report as a fix rather
  than leaving it in a diff. A pasted output that the library no longer produces is a falsehood. A
  count that the document's own command contradicts is a falsehood.
- **Report** everything else, including every defect in a file the round assigned to somebody else.
  A cold reader who starts editing another workstream's page stops being cold and starts being a
  seventh author of it.
- **Never** edit `docs/DECISIONS.md`. Report what the record should say.
- **Never** relax a gate to make a finding go away, and never move a figure inside a code span or a
  fence for the same purpose. D-052 established that fencing is indistinguishable from hiding; a
  cold reader doing it is the one case where it is certainly hiding.

The report is a list. Each entry carries: the file and line, the sentence quoted exactly, the
command or reading that refutes it, and one of three dispositions — **fixed**, **blocked on a named
decision**, or **permanent, and here is why** (R14).

---

## 6. What it costs

Measured on the first execution rather than estimated. The gate figures are from one timed pass over
the tree of 2026-08-24; the reading figures are counts of the corpus the protocol has to cover.

```
python - <<'PY'   (subprocess timing of the six gates, one pass)
   41.11s  exit=0  python -m pytest tests
    0.08s  exit=0  python -m ruff check src tests tools bench
    0.07s  exit=0  python -m ruff format --check src tests tools bench
    1.16s  exit=0  python -m mypy
    1.33s  exit=0  python tools/check_claims.py
    0.07s  exit=0  python tools/splits.py --check
   43.82s  TOTAL
```

```
for f in <the rotation set>; do wc -w "$f"; done   -- command output
  the full user-facing corpus            about 72,000 words across 13 files
  the largest single file                docs/EVALUATION.md, about 20,700 words
  the median file                        about 3,500 words
```

So the recurring cost of one round, with both triggers firing:

| Component | Cost |
|---|---|
| Gates, run once at the start and once at the end | under two minutes of wall clock, dominated by `pytest` |
| Trigger A — cold-read the user-facing files this round touched | proportional to the round; the first pass covered two large files this way |
| Trigger B — cold-read one untouched file from the rotation | one file, median about 3,500 words |
| Verification probes | the first pass ran about thirty shell probes, each a few seconds |
| Writing the report | the list above, one entry per finding |

**One agent slot, or roughly ninety minutes of a person's attention.** That is the number this
policy stands or falls on, and it is stated so that a round which cannot afford it can say so
explicitly rather than skip the step quietly.

The yield of the first pass, for whoever is deciding whether to spend that again: fifteen findings,
of which six are material errors of fact in user-facing prose, three were fixed in the same commit,
and one had survived unaltered in `docs/EVALUATION.md` since the commit that created the file.

---

## 7. How this fails

**It is still one reader.** A second reader is not an independent one — this page reduces the
lineage from one to two and does not make it plural. Everything the first pass found, it found
because it was a *different* reader; nothing establishes that a third would find nothing, and the
first pass's own estimate is that six checks over thirteen documents in one sitting is a sample.

**It reads documents, not code.** Every check above compares prose against something else — a
command's output, a config file, another page. A document that is internally consistent and
consistently wrong about the world passes all six. `docs/OFFLINE.md`'s air-gap findings, for
example, were checked for *coverage* and not re-derived; the second reader confirmed which modules
the scan omits and did not re-run the scan.

**Trigger B's latency is the size of the rotation.** With one untouched file per round, a defect in
a file nobody edits waits, on average, half a turn of the set before anybody looks at it. The
`docs/OFFLINE.md` module count and the `docs/SUPPORT_MATRIX.md` command list had both been wrong for
longer than that, so the rotation is an improvement on nothing and not a bound.

**Nothing enforces it.** This is the largest weakness and it is the same one `docs/DEFINITION-OF-DONE.md`
records against its own nine criteria: no job in `.github/workflows/ci.yml` asserts that a cold read
happened. A policy in a document is what this repository has already learned to distrust — eleven
places cited `bench/splits.toml` in prose, none parsed it, and the file had been invalid TOML for
months.

**Disposition: blocked on a named decision**, not permanent, and the decision is small. The check
is specifiable in one paragraph: a job that computes the trigger-A file list from the push's diff
and fails when that list is non-empty and the head commit carries no `Second-reader:` trailer naming
the reader and the rotation cursor. Two things stop it being written here — it belongs in
`.github/workflows/ci.yml` and in `tools/`, neither of which this page's author was assigned, and a
gate that has never been demonstrated failing in the environment where it runs is exactly the defect
class D-058 counted four instances of in one round. Whoever writes it owes a mutation: a push
touching `README.md` with no trailer, red, captured.

**And the protocol can be satisfied without being performed.** Six checks and four questions produce
a report of the right shape whether or not anybody ran the commands. The only defence is that every
finding carries the command that refutes it, so a fabricated finding is refutable by the same
mechanism as a fabricated claim — which is the property this whole repository is built around, and
it is a weaker defence than a gate.

---

## 8. The rotation cursor, and what the first execution as policy found out about the policy

This section is the state section 3 says this page carries. It is appended by each cold reader,
newest last.

### 2026-08-25 — second execution, first one run as policy rather than as a one-off

**Trigger B served [`docs/GOVERNED_NAMING.md`](GOVERNED_NAMING.md). The cursor now stands at
[`docs/SUPPORT_MATRIX.md`](SUPPORT_MATRIX.md).**

**Rotation set amended.** [`docs/POSITIONING.md`](POSITIONING.md) is appended to the section 3 list,
which now runs to fifteen files. That page asked for it in its own words — *a positioning statement
nobody re-reads is how a commitment becomes a slogan* — and it was the one user-facing page no
trigger could ever reach. The amendment is recorded here rather than made quietly, because the
rotation set is the only thing in this policy a later reader has to take on trust.

```
README.md · docs/EVALUATION.md · docs/OFFLINE.md · docs/GOVERNED_NAMING.md
docs/SUPPORT_MATRIX.md · docs/JAVA_INTEROP.md · CHANGELOG.md · docs/ENTERPRISE.md
docs/QUICKSTART_GOVERNED.md · docs/INSTALL.md · docs/ARCHITECTURE.md
CONTRIBUTING.md · SECURITY.md · docs/DEFINITION-OF-DONE.md · docs/POSITIONING.md
```

### Three things about the policy itself, found by executing it

**Trigger A's command returns nothing when the trigger fires.** Section 3 says the cold read happens
*before the recorder writes the round's D-record*, and section 3's command reads committed history:

```
git diff --name-only <round-base>..HEAD -- README.md CHANGELOG.md CONTRIBUTING.md SECURITY.md docs
```

At the moment a cold read is due, the round is still in the working tree and `<round-base>` **is**
`HEAD`, so the command printed an empty list on a round that had rewritten the front page. The real
list came from `git status --porcelain` and `git diff --name-only` with no revision range, plus the
untracked entries — a new file is invisible to `git diff` either way, and this round's headline
document was a new file. Either the command changes to read the working tree, or the trigger moves
after the commit and stops being able to block it.

**Trigger A's pathspec cannot see the most-read sentence this project ships.** It scans `README.md`,
`CHANGELOG.md`, `CONTRIBUTING.md`, `SECURITY.md` and `docs`. `pyproject.toml`'s `description` is the
line PyPI renders under the package name; it was rewritten this round, and no trigger on this page
would have looked at it. Add it, or say in section 3 that packaging metadata is out of scope and why.

**"Report everything else" did not produce a fix.** Section 4.2's C1 finding — that
`docs/OFFLINE.md` and `docs/ENTERPRISE.md` claim the air-gap job drives "every CLI subcommand" while
the probe in `.github/workflows/ci.yml` drives thirteen of the sixteen `acronymkit --help` lists —
is still true in all three places, unaltered, one round later. Re-derive with:

```
git grep -n "every CLI subcommand" -- docs .github
```

Section 5 draws the report/fix line to keep the reader cold. The measured consequence of drawing it
there is that a defect in a file nobody owns waits for a rotation slot even after somebody has
already found it and written down where it is. That is a cost of the design, not an argument against
it, and it should be priced in section 6 rather than discovered again.
