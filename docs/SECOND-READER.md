# The second reader

This project has been single-adjudicator on its corpus, single-verifier on its agent reports and
single-lineage on its adversarial passes. It has said so in every round and resolved it in none —
the sentence appears in `docs/DECISIONS.md` D-054, D-056 and D-057, each time under *How it fails*,
which is where an unowned problem goes to be acknowledged rather than fixed.

This page is the fix, and it is deliberately the cheapest of the three shapes that would work. It
defines a **cold read**: one reader, given the document and the gates and nothing else, asking what
would have to be true for the document to be wrong. It names when that happens, what the reader
does, **what happens to what the reader finds**, and what one round of it costs.

**The reader changes nothing.** That is the one thing on this page that used to be a sentence and is
now a mechanism, and [section 5](#5-what-the-second-reader-may-change-and-what-they-may-not) is where
it lives. The reader's whole output is [`docs/cold-reads.toml`](cold-reads.toml).

**The parts of this page that run, run.** Its trigger is `tools/second_reader.py`; its state is the
ledger; `python tools/second_reader.py --check` is the gate over both; and
`tests/test_second_reader_policy.py` mutation-tests every rule of it. That is not decoration. The
first execution of this policy found three defects in the policy, two of which were commands this
page published and nobody had run — which is precisely the class the page exists to catch, shipped
inside the fix for it.

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

**Trigger A — the working tree.** Any round that changes a user-facing file ends with a cold read of
exactly the user-facing files it changed, before the recorder writes the round's D-record.

**The trigger is `tools/second_reader.py`, and the command below is what it runs.** Run the tool;
the command is published so that the tool can be checked rather than believed:

<!-- trigger-a-command -->
```
python tools/second_reader.py --trigger        # this is the trigger

git status --porcelain --untracked-files=all -- README.md CHANGELOG.md CONTRIBUTING.md SECURITY.md pyproject.toml docs
```

The tool adds `-z` to that command — a parsing detail, because the un-zed form quotes any path with
a space in it — and then drops the paths the next paragraph excludes. `python tools/second_reader.py
--check` **fails if the pathspec on this page and the pathspec in the tool ever disagree**, which is
the check the last correction to this section needed and did not have.

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

**And a corrected command in a document is the same artifact as the wrong one** — prose, unexecuted,
trusted. That is why the correction is now a function with a test rather than a paragraph.
`tests/test_second_reader_policy.py` pins three states: a working tree carrying a modified
user-facing file **and** a new untracked one returns both; a tree where only the excluded files
changed returns nothing; and the superseded `git diff --name-only <base>..HEAD` command returns
nothing **in the same dirty tree where the trigger returns two files**, so the defect that motivated
this rewrite is a red test rather than a sentence somebody has to keep believing. The in-situ half is
in [section 9](#9-the-trigger-demonstrated-in-situ).

Minus `docs/DECISIONS.md` and `docs/AUDIT-*.md`, which are historical records rather than
instructions to a user, and minus `docs/notes/*.md`, which are scoped technical notes read by
somebody who arrived from a link that already warned them. And minus everything under `docs/` that
is not Markdown — `docs/cold-reads.toml` is this policy's machine state, not a page a stranger reads,
and a trigger that fired on it would make every cold read demand a cold read of its own findings.

**Trigger B — the rotation.** Each round also cold-reads **one** user-facing file the diff did
*not* touch, taken from a fixed rotation. One file. The set turns over in as many rounds as there
are files in it.

**In rotation order, wrapping — not "oldest-read first", which is what this page used to say.**
D-072 recorded that oldest-read-first is *uncomputable here*: no per-file read dates exist anywhere,
the first pass left none, and the reader silently substituted rotation order. Both executed reads
followed rotation order. A rule two readers already obeyed and a machine can check beats a rule
neither could evaluate, so the cursor after serving file *n* is file *n+1*, and
`tools/second_reader.py --check` refuses a recorded cursor that is not that, and refuses a read whose
trigger-B file is not the one the previous cursor pointed at. **The cursor is followed, not
announced.**

Trigger B exists because of a count, not a hunch. Of the fifteen defects the first pass found, seven
were in files that round's diff never opened — `docs/OFFLINE.md`, `docs/SUPPORT_MATRIX.md`,
`docs/ENTERPRISE.md` and `CONTRIBUTING.md`, none of which any workstream had touched. **A
diff-scoped trigger alone would have missed just under half of what was there**, and it would have
missed it for the structural reason that a document nobody edits is a document nobody re-reads.

The rotation set, in order. **This block is the only copy.** It used to be restated in section 8,
and the two copies had already diverged: section 8 recorded the amendment that appended
`docs/POSITIONING.md`, section 3 was never updated, and this page told a reader the set held
fourteen files while its own section 8 said fifteen. `python tools/second_reader.py --check` parses
this block and refuses a second copy of the marker.

<!-- rotation-set -->
```
README.md · docs/EVALUATION.md · docs/OFFLINE.md · docs/GOVERNED_NAMING.md
docs/SUPPORT_MATRIX.md · docs/GATES.md · docs/SECOND-READER.md · docs/CLAIMS-LEDGER.md
docs/SOURCING.md · pyproject.toml · docs/RELEASE_CHECKLIST.md · docs/JAVA_INTEROP.md
CHANGELOG.md · docs/ENTERPRISE.md · docs/QUICKSTART_GOVERNED.md · docs/INSTALL.md
docs/ARCHITECTURE.md · CONTRIBUTING.md · SECURITY.md · docs/DEFINITION-OF-DONE.md
docs/POSITIONING.md
```

**Fifteen to twenty-one, and the six new entries are not a widening for its own sake.** The check now
runs the other way round: `--check` enumerates every user-facing file in the tree and **refuses any
that the rotation cannot reach**. That rule was written because of a mutation that got through — see
[section 9](#9-the-trigger-demonstrated-in-situ), state D. Deleting an entry from this block was
invisible to the validator *and* to the suite, because every remaining entry still existed, none
repeated, and the cursor still resolved. A set checked only against itself agrees with itself
perfectly, which is the property D-061 already named: **shrinking a list is not the same as growing
coverage.**

The six that no trigger could ever reach were `docs/GATES.md`, `docs/CLAIMS-LEDGER.md`,
`docs/SOURCING.md`, `docs/RELEASE_CHECKLIST.md`, `pyproject.toml` and — worth saying out loud —
**`docs/SECOND-READER.md` itself**. This page has now been wrong about its own trigger, its own
rotation count and its own gate count, and it was the one document in the tree that could not be
assigned to a cold reader. They are inserted immediately after the current cursor rather than
appended, because appending would leave every never-read page at the back of a twenty-one-round
queue. **The cost is stated rather than absorbed: the set turns over in twenty-one rounds instead of
fifteen**, so trigger B's latency is two fifths longer than it was. That is the price of the
coverage, and section 7 already names that latency as a weakness rather than a bound.

**One consequence, and it is deliberate: publishing a new user-facing page now reddens this gate
until the page is in this block.** That is the anti-rot rule `.github/gates.toml` already runs on
jobs — *every job in every workflow must appear here, so a job added tomorrow reddens `--check`
until somebody says what it checks* — applied to documents. **It fired for real inside the round that
wrote it.** `docs/SOURCING.md` was created by another workstream while this page was being edited;
`python tools/second_reader.py --check` went red naming it, and it is in the block above because of
that, not because anybody remembered. `docs/AUDIT-PROHIBITIONS-2026-08.md` appeared in the same
window and was correctly *not* named, because `docs/AUDIT-*.md` is excluded — the two halves of the
rule, both exercised on files nobody wrote for the test.

The reader records which file the rotation served in [`docs/cold-reads.toml`](cold-reads.toml), and
the cursor is derived from it rather than typed. That is the whole of the state this policy carries,
and [section 8](#8-the-rotation-cursor) is where it is restated for a human.

---

## 4. The protocol

### 4.1 Per document, four questions

Answer them in writing. They are ordered so that the last one is impossible to answer honestly
without having done the first three.

1. **The strongest claim it makes**, quoted exactly, with its line number.
2. **What a reader would have to believe** for that claim to be true — stated as a list of separate
   beliefs, because a compound claim usually has one weak conjunct and four strong ones.
3. **Whether each belief survives the gates.** Run them. They are listed in `CONTRIBUTING.md`; what
   CI runs, what each check is blind to, and whether it has ever been shown failing where it runs
   are in [docs/GATES.md](GATES.md). **That sentence said "the six local ones" and was wrong by one**
   — `python tools/gates.py --check` has run in the `lint` job since the register shipped
   (`.github/workflows/ci.yml`, the step named *Every CI gate is registered*), and `CONTRIBUTING.md`
   said six as well. Counting the gates a policy tells you to run is exactly check C6 below, aimed at
   this page.
4. **The single sentence in the document most likely to be false**, and the command that checked it.

Question 4 admits no abstention. A document with nothing to nominate has not been read.

**The output of all four is a row in [`docs/cold-reads.toml`](cold-reads.toml), not a diff.** See
[section 5](#5-what-the-second-reader-may-change-and-what-they-may-not).

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
cited ninety-nine of them by run id.

**Re-derived at `61cf933`, and the second half had moved by one.** `len(json["runs"])` is still
`536`; resolving every `claim:` path in that page to the longest run id it matches gives **`100`**,
not ninety-nine. That is a citation added between the pass and this commit rather than an error in
the pass, and it is left as a correction with its command rather than as a re-stamped figure —
because a count published without the derivation beside it is the thing C4 exists to catch, one
check down this same list:

```
python -c "import json,re,subprocess;
d=json.loads(subprocess.run(['git','show','61cf933:bench/results.json'],capture_output=True).stdout);
ev=subprocess.run(['git','show','61cf933:docs/EVALUATION.md'],capture_output=True).stdout.decode();
k=set(d['runs']); print(len(k), len({'.'.join(m.split('.')[:n]) for m in
re.findall(r'claim:([A-Za-z0-9_.\-/]+)', ev) for n in range(len(m.split('.')),0,-1)
if '.'.join(m.split('.')[:n]) in k}))"
  536 100
```

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

**The cold reader reports. Somebody else applies.** That is not a new principle — the old version of
this section already said a cold reader who starts editing another workstream's page *"stops being
cold and starts being a seventh author of it"*. What is new is that it is no longer a sentence.

**Because a sentence did not hold it.** On this page's first execution as policy the reader made four
edits to `docs/POSITIONING.md`, a page another workstream had written that same round, and flagged
itself for doing so. D-072 ruled three of the four inside the then-current fix clause and the fourth
authoring. The instinct was right and the mechanism was wrong: a rule whose only enforcement is that
the reader remembers it is a rule that gets remembered exactly as often as the reader is not busy.

### 5.1 The boundary, and where it actually lives

- **Report everything.** The reader's whole output is a row in
  [`docs/cold-reads.toml`](cold-reads.toml). Not a diff, not a page edit, not a fix "while I was in
  there".
- **The fix clause is retired.** It used to permit fixing an outright falsehood in user-facing prose.
  It is gone, and the reason is measured rather than principled: the falsehoods it was written for
  were in pages other workstreams had just written, so the clause fired precisely where the coldness
  mattered most.
- **Never** edit `docs/DECISIONS.md`. Report what the record should say.
- **Never** relax a gate to make a finding go away, and never move a figure inside a code span or a
  fence for the same purpose. D-052 established that fencing is indistinguishable from hiding; a
  cold reader doing it is the one case where it is certainly hiding.

**The structural half, and it is one rule.** `disposition = "fixed"` requires an `applied_by`, and
`python tools/second_reader.py --check` **refuses an `applied_by` equal to the reader who raised the
finding.** A reader cannot close its own finding by editing prose, because closing takes a second
name. That is as structural as a policy in a repository with one contributor can be made, and it is
worth saying plainly what it is not: it is not a filesystem permission. A reader determined to edit a
page can still edit it. What it removes is the *quiet* route — the fix that lands in a diff and is
recorded nowhere.

### 5.2 The shape of a finding, and who applies it

Each entry carries the file and line, the sentence quoted exactly, the command or reading that
refutes it, an `owner`, and a disposition. That was already the list. It is now a schema, so a
missing half is a red build rather than a habit — `refutation` may not be empty, because a finding
with no command behind it is an opinion, and [section 7](#7-how-this-fails) names that command as the
only defence this policy has.

**The applier is the workstream that holds the file, named in `owner`.** When no workstream holds it,
`owner = "unowned"` and the finding belongs to *the round*: whoever runs the next cold read must
either see it applied or move it off `open`. Applying a written finding is not authoring — the
finding already carries the sentence, the line and the command, so what is left is an edit somebody
else specified.

### 5.3 What happens to a finding nobody applies

**This is the load-bearing part, and it is load-bearing because a read-only reviewer whose findings
rot is worse than one who fixes things.** The measurement is on this page: the first pass's C1
finding was unaltered in all three places one round later, *after* somebody had found it and written
down where it is. So:

| | |
|---|---|
| A finding is born | `open` |
| At **every** cold read | its `reviewed_in` must name the newest read, or the gate is red. One field. It cannot be forgotten quietly |
| After **two** cold reads | `open` is refused. It becomes `fixed` (with a second name), `blocked` (naming the decision), or `permanent` (naming the reason) — R14 |
| `--check` prints, every run | `OPEN AND AT THE LIMIT: n of m`, so the round before the deadline sees it coming |

Nothing here forces anybody to apply anything, and that is deliberate: a reader who could assign work
to strangers would be authoring by another route. What is enforced is that no finding rots without a
name against it.

---

## 6. What it costs

Measured on the first execution rather than estimated. The gate figures are from one timed pass over
the tree of 2026-08-24; the reading figures are counts of the corpus the protocol has to cover.

```
python - <<'PY'   (subprocess timing, one pass, 2026-08-25, CPython 3.13.4 on
                   win32, in a clean worktree of HEAD carrying only this
                   round's cold-read changes)

   51.79s  exit=0  python -m pytest tests          4980 passed, 10 skipped, 1 xfailed
    0.09s  exit=0  python -m ruff check src tests tools bench
    0.10s  exit=0  python -m ruff format --check src tests tools bench
    1.93s  exit=0  python -m mypy
    1.38s  exit=0  python tools/check_claims.py
    0.09s  exit=0  python tools/splits.py --check
    0.09s  exit=0  python tools/gates.py --check          <- the seventh; the block below said six
    0.09s  exit=0  python tools/second_reader.py --check  <- new, and NOT in CI yet
   55.56s  TOTAL
```

**Two corrections in that block, and one of them is a gate.** The previous version timed **six**
commands and called them "the six gates"; `python tools/gates.py --check` has run in the `lint` job
since the register shipped, so the number a reader was told to run has been one short in this file
and in `CONTRIBUTING.md`. And `python tools/second_reader.py --check` is listed here because a cold
reader should run it, **not** because CI does — no job invokes it yet, which is
[section 7](#7-how-this-fails)'s disposition and not a footnote.

```
python tools/second_reader.py --cost           -- command output, 2026-08-25,
                                                  mid-round and moving; re-run it
  the full user-facing corpus   128,816 words across 21 files
  the largest single file        25,677 words   docs/EVALUATION.md
  the median file                 4,362 words   docs/POSITIONING.md
  the smallest                      770 words   SECURITY.md
```

**THIS BLOCK IS DERIVED NOW, AND THE REASON IS THAT ITS PREVIOUS VERSION WAS WRONG IN EVERY FIGURE.**
It read *"about 72,000 words across 13 files"*, *"about 20,700"* and *"about 3,500"* — a corpus
count taken before `docs/POSITIONING.md` existed and before the rotation was twice amended. A costing
is exactly the class of number a page publishes once and never re-runs, and it sits inside a fence,
where D-052 says the claims gate cannot see it. Both of those are why it drifted, and neither is
fixed by typing better numbers into the same fence.

So the numbers moved into `--cost` and the page publishes the command. **The output above is a
snapshot taken while five workstreams were editing this tree, and it was already moving as it was
taken**: `wc -w docs/EVALUATION.md` returned `21,191` at `61cf933`, `22,455` earlier in this session
and `25,677` above. Three values, one round, one file. Quote the command, not the figures.

So the recurring cost of one round, with both triggers firing:

| Component | Cost |
|---|---|
| Gates, run once at the start and once at the end | under two minutes of wall clock, dominated by `pytest` |
| Trigger A — cold-read the user-facing files this round touched | proportional to the round; the first pass covered two large files this way |
| Trigger B — cold-read one untouched file from the rotation | one file, median 3,792 words |
| Verification probes | the first pass ran about thirty shell probes, each a few seconds |
| Writing the report | one row per finding in [`docs/cold-reads.toml`](cold-reads.toml) |
| Re-affirming the open findings | one field each, and `python tools/second_reader.py --open` prints the list. Seconds, and it is the step the whole hand-off rests on |

**One agent slot, or roughly ninety minutes of a person's attention.** That is the number this
policy stands or falls on, and it is stated so that a round which cannot afford it can say so
explicitly rather than skip the step quietly.

The yield of the first pass, for whoever is deciding whether to spend that again: fifteen findings,
of which six are material errors of fact in user-facing prose, three were fixed in the same commit,
and one had survived unaltered in `docs/EVALUATION.md` since the commit that created the file.

**And the cost D-072 asked to have priced here, now that there is a mechanism to price it against.**
Section 5 draws the report/apply line to keep the reader cold, and the measured consequence is that
an unowned defect waits. The ledger does not remove that wait; it bounds it at two cold reads and
makes the boundary visible in a printed count. That is the trade, stated as a trade.

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

**Nothing asserts that a cold read HAPPENED, and that is still true.** What changed is narrower than
it looks and worth stating exactly. `python tools/second_reader.py --check` adjudicates the *state*:
the cursor is derivable and agrees with this page, the published pathspec agrees with the code, every
finding carries a disposition, and no finding is rotting. It does **not** know whether anybody read
anything. A round that changes `README.md`, writes no finding and runs the gate gets a green tick.

**Disposition: blocked on ownership**, not on design, and the missing piece is one CI job. It is
specifiable in one paragraph and now has a function to call: a job that runs
`python tools/second_reader.py --trigger` against the push and fails when the list is non-empty and
the head commit carries no `Second-reader:` trailer naming the reader. `.github/workflows/ci.yml` and
`.github/gates.toml` belong to other workstreams, and R11 says whoever writes it owes a mutation in
the environment it runs in: a push touching `README.md` with no trailer, red, captured. The register
entry it needs is drafted and handed over rather than written here.

**The gate that does exist has a hole with a known shape.** `MANIFEST.in` ships `docs/*.md`, so
`docs/cold-reads.toml` is absent from an sdist exactly as `.github/gates.toml` is. `--check` fails
loudly there rather than passing vacuously, which means this gate belongs to a checkout environment
and must be registered in one. That is the D-058 fourth-instance shape — a gate that cannot fail
where every file it scans is present by construction — named in advance this time rather than found
by a red release job.

**And the protocol can be satisfied without being performed.** Six checks and four questions produce
a report of the right shape whether or not anybody ran the commands, and the ledger's schema checks
that a `refutation` field is non-empty, not that the command in it was ever executed. The only
defence is that every finding carries the command that refutes it, so a fabricated finding is
refutable by the same mechanism as a fabricated claim. **That defence has now been exercised and it
worked**: the second read published two commands beside its question-4 nomination, the recorder ran
them, and neither refuted the sentence it was published beside. The finding survived; its evidence
did not. See `F-2026-08-25-02` in the ledger for the corrected command.

---

## 8. The rotation cursor

**The state lives in [`docs/cold-reads.toml`](cold-reads.toml), not in this sentence.** That is the
change this section exists to record. A policy whose only memory is a sentence in a document has
exactly one failure mode, and D-072 had already found it twice on this page: the rotation set was
restated in two places that disagreed, and the cursor rule — *oldest-read first* — was uncomputable
because no per-file read dates existed anywhere.

So the cursor is **derived** from the ledger's newest `rotation_served` by rotation order, restated
here for a human, and `python tools/second_reader.py --check` refuses a disagreement between the two:

<!-- rotation-cursor -->
```
cursor docs/SUPPORT_MATRIX.md
```

Read that as: the last cold read (2026-08-25) served
[`docs/GOVERNED_NAMING.md`](GOVERNED_NAMING.md), which is entry four of the fifteen in section 3, so
trigger B serves entry five next. The next reader changes the ledger; this line is checked against
it, and the check is the only reason to trust either.

**The cursor points at a page that already has a finding against it.** `F-2026-08-24-05` is
`docs/SUPPORT_MATRIX.md:39`, where nine commands are named under an exhaustive word on a
sixteen-command CLI — and the seven the sentence does not reach are the governed half, which
`docs/POSITIONING.md` commits this library to leading with. That is trigger B and the ledger arriving
at the same page from opposite directions, which is the first evidence either mechanism works.

**Rotation set amended, 2026-08-25.** [`docs/POSITIONING.md`](POSITIONING.md) was appended, taking
the set to fifteen. That page asked for it in its own words — *a positioning statement nobody
re-reads is how a commitment becomes a slogan* — and it was the one user-facing page no trigger could
ever reach. **The amendment landed in this section and never reached section 3**, which is how the
page came to tell a reader the set held fourteen files while its own section 8 said fifteen. The
duplicate is deleted; section 3 is the only copy and the tool parses it.

### The three defects the first execution as policy found in the policy, and where each stands

| Found | Disposition |
|---|---|
| Trigger A's command returned nothing at the moment it fires — it read committed history while the read happens before the commit, and `git diff` cannot see a new file under any range | **Fixed, and the fix is tested.** Section 3 publishes `git status`; `tools/second_reader.py` runs it; `tests/test_second_reader_policy.py` pins all three states and pins the old command's failure in the same dirty tree. In-situ evidence in [section 9](#9-the-trigger-demonstrated-in-situ) |
| Trigger A's pathspec could not see `pyproject.toml`, whose `description` is the line PyPI renders | **Fixed, and the fix is checked.** It is in the pathspec, and `--check` refuses a disagreement between the pathspec on this page and the one in the tool |
| "Report everything else" produced no fix — the C1 finding was unaltered in all three places one round later | **Not fixed. That is what sections 5.2 and 5.3 are, and the three places are `F-2026-08-24-01`, `-02` and `-03` in the ledger, open and one cold read from being refused as open** |

The last row is the honest one. A hand-off mechanism does not repair a document; it makes the
document's continuing disrepair loud, dated and attributable. Whether that is worth anything is
settled by the next cold read, not by this page.

---

## 9. The trigger, demonstrated in situ

R11: a gate must be demonstrated capable of failing **in the environment where it runs**, by
mutation, with the failure captured. Trigger A runs in one place — an uncommitted working tree of
this repository — and that is where it was mutated. Not a fixture, not a temporary directory: this
checkout, mid-round, with another workstream's edit to `README.md` already in it.

```
python tools/second_reader.py --trigger, and the two commands it replaces.
CPython 3.13.4 on win32, git 2.45.1.windows.1, HEAD 61cf933, mid-round with
five workstreams' edits in the tree. Command output, not a benchmark
measurement. <pathspec> is the six entries section 3 publishes.

STATE 1 -- clean worktree of this repository at the same commit
           (git worktree add --detach <tmp> HEAD)
  git status --porcelain -- <pathspec>              (empty)   rc=0
  trigger A                                        0 file(s)

STATE 2 -- this checkout, mid-round, with docs/TRIGGER-PROBE.md created as
           an untracked user-facing page and deleted in the same sitting
  git diff --name-only HEAD..HEAD -- <pathspec>    0 file(s)  <- the published command
  git diff --name-only -- <pathspec>               5 file(s)  <- range dropped; probe NOT among them
  trigger A                                        6 file(s)  <- probe among them
```

**State 1 is the demonstration that this trigger can return nothing.** A trigger that always fires is
not a trigger, and the negative control is a real worktree of this repository rather than an argument
that it would be empty.

**State 2 is the defect, reproduced rather than described, and it is two defects rather than one.**
The published command returns **zero** files in a tree where six user-facing files have changed.
Dropping the revision range — the obvious repair, and the one an earlier draft of this page proposed
— recovers five of the six and is *still blind to the new page*, because `git diff` never sees a file
that exists under neither revision. That is the half that mattered: the round which found this
introduced its headline document as a new file.

### What the mutations found, including the one that got through

Eight mutations, one at a time, each reverted and each file md5-verified against bytes read before
the first. `pytest` is `tests/test_second_reader_policy.py`; `--check` is
`python tools/second_reader.py --check`.

```
mutation                                                     pytest   --check
  control, unmutated                                          rc=0     rc=0
  A  the trigger stops looking for untracked files             rc=1     rc=0
  B  pyproject.toml leaves the pathspec                        rc=1     rc=1
  C  the page's cursor moves off the derived value             rc=1     rc=1
  D  the rotation set quietly loses one entry                  rc=1     rc=1   <- see below
  E  an open finding stops being re-affirmed                   rc=1     rc=1
  F  a blocked finding loses its named decision                rc=1     rc=1
  G  the trigger goes back to reading committed history        rc=1     rc=0
  H  the docs/DECISIONS.md exclusion is dropped                rc=1     rc=1
```

**D got through on the first run, and the fix is why the rotation set is twenty files.** On the first
pass D printed `rc=0 rc=0`: deleting an entry from the rotation block was invisible to both the suite
and the gate, because every surviving entry existed, none repeated and the cursor still resolved. **A
set checked only against itself agrees with itself perfectly.** The rule added in response reads the
tree instead — every user-facing file must be reachable by the rotation — and it took the set from
fifteen to twenty because five pages, this one included, were unreachable. D fails now. The row is
left in the table with its history rather than shown only in its repaired state.

**A and G are the honest asymmetry, not a hole.** Both redden `pytest` and leave `--check` green,
and that is correct: `--check` validates the *state* of the policy — cursor, coverage, dispositions —
and knows nothing about how the trigger reads git. The suite is what covers the trigger. Reporting
them as `rc=0` rather than quietly dropping the column is the point of printing both.

**F needed two attempts, and the first one was the failure this repository keeps cataloguing.** The
probe was written to blank a `blocked_on` field and instead deleted its first line, leaving the field
non-empty; the gate stayed green and the honest first reading was "the rule does not fire". It fires.
**The refutation was broken, not the thing it was aimed at** — which is exactly what D-072 found when
it re-ran the second read's published commands, one page ago, and it is the reason a mutation is only
evidence once its probe has been checked.

**All of this is in `tests/test_second_reader_policy.py`**, because a check that exists only in a
transcript is not a check — this repository has written that sentence three times and acted on it
twice. What the tests add beyond the transcript is the direction a mid-round transcript cannot reach
without destroying the round: a tree in which *only* `docs/DECISIONS.md`, `docs/AUDIT-*.md`,
`docs/notes/*` and `docs/cold-reads.toml` changed, where the trigger must return nothing and does.
