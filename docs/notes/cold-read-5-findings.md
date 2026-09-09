# Cold read 5 — findings, 2026-09-08

The fifth execution of [`docs/SECOND-READER.md`](../SECOND-READER.md), and the third under the
read-only rule. **The reader wrote nothing except this file.** No page was edited, no gate was
relaxed, no figure was moved into a fence or out of one, and
[`docs/cold-reads.toml`](../cold-reads.toml) was **not** written — that is
[`P-1`](#p-1--trigger-b-served-a-file-trigger-a-had-already-served-and-nothing-refuses-that),
carried from reads three and four and now failing in a second way.

**How numbers are handled on this page.** Every figure here is a property of *these documents*, of a
command's output, or of a corpus this reader re-derived — never a measurement of the library that a
runner could `--save`. So they appear fenced or code-spanned **with the command printed beside
them**, the convention [`docs/CLAIMS-LEDGER.md`](../CLAIMS-LEDGER.md) §1 and
[`cold-read-4-findings.md`](cold-read-4-findings.md) already use. D-052 is explicit that fencing
silences the claims gate completely; the command is printed with every block so a reader re-derives
rather than trusts. **A figure on this page you cannot re-derive from a command on this page is a
defect in this page.**

**Every finding below carries exact replacement text.** That hand-off has worked twice and is why
section 5 draws the report/apply line where it does. Nothing here is applied.

---

## 0. What was read, and the state it was read in

```
git rev-parse --short HEAD                34925f8   (working tree dirty, mid-round)
python tools/second_reader.py --trigger   8 user-facing file(s)
python tools/second_reader.py --check     rotation: 21 file(s); trigger B serves docs/GATES.md next
                                          findings: open 0, fixed 7, blocked 0, permanent 0 (of 7)
                                          OPEN AND AT THE LIMIT: 0 of 0
python tools/second_reader.py --open      no open findings
```

**Trigger A served eight files**, the whole of this round's user-facing diff scope: `CHANGELOG.md`,
`docs/DEFINITION-OF-DONE.md`, `docs/EVALUATION.md`, `docs/GATES.md`, `docs/GOVERNED_NAMING.md`,
`docs/OFFLINE.md`, `docs/SOURCING.md`, `docs/SUPPORT_MATRIX.md`. `docs/DECISIONS.md` is modified in
the same tree and was correctly **not** served.

**Four files were created in this tree and served by neither trigger** —
`docs/figures/{refusal-curve,monoculture-band}-{light,dark}.svg`. That is
[`F-5-4`](#f-5-4--the-round-that-ships-figures-ships-them-outside-both-triggers-and-outside-the-rotation),
and it is this round's structural finding.

**Trigger B served [`docs/GATES.md`](../GATES.md).** The two-read stall on
`docs/SUPPORT_MATRIX.md` is broken and the cursor moved, exactly as read four said it would:

```
python tools/second_reader.py --check | grep 'trigger B'
  rotation: 21 file(s); trigger B serves docs/GATES.md next

sed -n '/<!-- rotation-cursor -->/,/^```$/p' docs/SECOND-READER.md
  cursor docs/GATES.md

docs/cold-reads.toml   reads[2].cursor_after = "docs/GATES.md"   (read 2026-08-26)
```

**The cursor should move to [`docs/SECOND-READER.md`](../SECOND-READER.md)**, entry seven of
twenty-one, and somebody other than this reader has to write that. It is also the first time the
rotation reaches the policy page itself.

**The eight gates, run at the start and again at the end of the read, unchanged in between.**

```
python -m pytest tests                      rc=0
python -m ruff check src tests tools bench  rc=0   All checks passed!
python -m ruff format --check ...           rc=0   152 files already formatted
python -m mypy                              rc=0   no issues found in 97 source files
python tools/check_claims.py                rc=0   value-matched 64 of 64; deferred 189 of 189
python tools/splits.py --check              rc=0
python tools/gates.py --check               rc=0   CARRYING IN-SITU EVIDENCE: 16 of 38
python tools/second_reader.py --check       rc=0   open 0, fixed 7, of 7
and, because this round ships figures for the first time:
python tools/render_figures.py --check      rc=0   2 figure(s) x 2 theme(s) byte-identical
```

`pytest`'s summary line is suppressed by this repository's reporter; the exit code is the reading
available, and it is `0`.

**No file changed under this reader.** Every probe below is a read, a `git` query, a `gh` query, an
import, or a script run against a copy.

---

## 1. The figures, read as a reader rather than as a build artifact

This is where the round's risk was said to be, so it is read first and at length. **The short answer
is that both charts are honest about the thing they could most easily have hidden, and the hole is
one level up: nothing in the second-reader policy would have made anybody look at them.**

### 1.1 The refusal curve does not crop the losing region. It leads with it

The question put to this read was whether the chart shows the region where the trivial baseline
beats this library. It does not merely show it — it is the headline and it is the largest shaded
area on the canvas.

```
python -c "import re,pathlib; s=pathlib.Path('docs/figures/refusal-curve-light.svg')
           .read_text(encoding='utf-8'); b=s.split('</desc>')[1]
           [print(m.group(0)) for m in re.finditer(r'<rect[^>]*>', b)]"

  <rect x="254.32" y="164" width="597.68" height="268" fill="#eef0f2"/>
```

The x axis maps coverage `0..100` onto `78..852`, so `x=254.32` is coverage `22.78 %` and the shaded
band runs from there to the right edge. That is the whole region where the flat most-frequent-sense
baseline is at or above the gated system — `77 %` of the plot area — and the two labels inside it
read *"the trivial baseline wins in here"* and *"every measured point from
22.78<!--claim:disambiguation.sdu21.abstention_curve.gate_0.10_coverage_pct:.2f--> % coverage
rightward"*. The title, at 19 px, is:

> Refusing buys accuracy, and at
> 22.78<!--claim:disambiguation.sdu21.abstention_curve.gate_0.10_coverage_pct:.2f--> % coverage and
> above the trivial baseline beats every bit of it

*(Both `22.78`s above are quotations of text drawn on the canvas and both carry the run-id citation
the claims gate asks for. The citation is an HTML comment, so the rendered quotation is unaltered;
the alternative — moving the figure into a code span — is what D-052 and `docs/SECOND-READER.md`
§5.1 forbid a cold reader specifically.)*

The accent colour (`#9a4210` light, `#f0883e` dark) is on the `acronymkit` line and on two
annotations of it — one the **best** point (`74.04 %` at `11.33 %` coverage) and one the **worst**
(`41.65 %` answering everything). It marks the claimed series at both ends rather than the flattering
end. The axis is `0..100` on both dimensions; nothing is truncated to magnify a difference.

Four qualifications sit on the canvas rather than in a caption: the crossing is not interpolated; at
the reference gate the baseline still wins at candidate-set sizes 3 and 4 (`32.38 %` of instances);
both baselines are one instrument at two denominators; and the split is declared contaminated, so
*"no value on this chart is evidence of generalisation"*. **On the specific question asked, this
chart is the opposite of the failure mode.**

### 1.2 The monoculture band's accent marks the claim, not the flatterer

The accent rect is the lower band — `34.98 %`, `631` spans, *"pairs no bracket scanner offers"* —
which is the figure's title. The two flattering alternatives were available and not taken: the
`57.65 %` the S&H family reaches is drawn in the **strong grey**, and the `20.40 %` nobody reaches is
the palest segment. Three sentences on the canvas actively undercut the accent:

- *"That band is not a slice of the bar above, and drawing it as one would be wrong."*
- *"At least 263 of them are already reached by a non-S&H proposer: 631 + 396 - 764."*
- *"7 operating points across 5 implementations make up the S&H family here, and 3 of the 7 are this
  library at 3 profiles. The bar measures one algorithm about as much as it measures a field."*

The last one is this project's own headline number being talked down inside its own chart.

### 1.3 Every number on both canvases resolves, and the derived ones re-derive

`tests/test_render_figures.py::TestNoNumberOnACanvasIsUncited` reads every `<text>` element back and
refuses a numeric token the `<desc>` does not cite. Re-derived here rather than trusted, arithmetic
first:

```
20.40 = 100 - 79.60 (all_proposers_recall_pct)                         ✓
  368 = 1,804 (gold_spans) - 1,436 (reached_by_all_proposers)          ✓
 7.37 = 42.35 (unproposed_pct) - 34.98 (unproposed_alignable_pct)      ✓
  263 = 631 + 396 - 764   (inclusion-exclusion, as printed on canvas)  ✓
22.78 = lowest measured coverage with gated < 72.84 (gate_0.10)        ✓
16.77 = highest measured coverage with gated >= 72.84 (gate_0.15)      ✓
```

Contrast, since the generator's docstring asserts *"a chart unreadable in one is broken"* and nothing
checks it. WCAG 2.x relative-luminance ratio, every text-fill against the ground it is drawn on, both
themes, 28 pairs:

```
worst pair, light   #57606a on #eef0f2   5.59:1
worst pair, dark    #9198a1 on #1c222b   5.49:1
bar labels, dark    #0d1117 on #8b939d   6.09:1     #0d1117 on #f0883e   7.48:1
```

**All 28 clear AA's 4.5:1.** The dark theme uses the palette's `on_strong`/`on_accent` ink on its
lighter fills rather than the light theme's white, which is the thing that would have broken and did
not.

### 1.4 What is *not* covered, and it is not the numbers

`gates.figures` byte-diffs the drawings and the suite refuses an uncited number. **Nothing checks the
sentences.** The title, the shading choice, the accent assignment and the 626-character alt text are
prose inside an image, and the one mechanism in this repository whose job is prose —
`docs/SECOND-READER.md` — cannot see the file. That is `F-5-4`.

---

## 2. Findings

Each carries the file and line, the sentence quoted exactly, the command that refutes it, and
**exact replacement text**. Nothing below was applied.

### F-5-1 — `docs/GATES.md` keeps the one figure it says is a repository fact, and it is wrong

**File:** `docs/GATES.md`, lines `1414` and `1419`.

**Quote, line 1414, inside the blockquote that argues for keeping it:**

> The `216` is kept because it is a repository fact.

**Quote, line 1419:**

> `git ls-files --eol` reports a large minority of the `216` tracked files as `w/crlf`

**Refutation.**

```
git ls-files | wc -l                              231
git ls-tree -r --name-only 34925f8 | wc -l        231   <- the commit this round started from
git ls-tree -r --name-only 61cf933 | wc -l        200
```

`216` is not the count at HEAD, was not the count at the commit this round started from, and this
reader could not find a commit in the last two rounds where it was. The paragraph it sits in is an
argument *about* which half of `66 of 216` survives: the numerator was dropped because `w/crlf` is a
property of the reader's checkout, and **the denominator was kept on the explicit ground that it
reproduces**. It does not. This is check C4 aimed at the one number a page told you was safe.

**Why nothing caught it.** Both instances are code-spanned, and D-052 records that fencing is
invisible to the claims gate. Confirmed:

```
PYTHONIOENCODING=utf-8 python tools/check_claims.py --residue | grep GATES
  docs/GATES.md  (0 deferred, 42 unexamined)
```

**Exact replacement text, line 1414** (last sentence of the blockquote):

> The denominator is derived on every read rather than kept, because it moves too: `git ls-files |
> wc -l` returns `231` on this tree and `200` at `61cf933`, four rounds ago. The share is described
> rather than counted, which is the only honest form available: a figure that changes with who reads
> it, or with which week they read it, is not a figure.

**Exact replacement text, line 1419** (replacing the clause up to the first comma):

> `git ls-files --eol` reports a large minority of the tracked files as `w/crlf` — `56` of `231` as
> this was written, by `git ls-files --eol | grep -c 'w/crlf'`, and the point is the minority rather
> than the count — and

*(The second replacement re-introduces a reader-dependent numerator on purpose, printed beside its
command and named as reader-dependent, which is the form the rest of this page already uses. An
applier who prefers the stricter reading should drop the parenthetical and keep only "a large
minority of the tracked files".)*

### F-5-2 — two commands `docs/GATES.md` publishes exit `2` before doing anything

**File:** `docs/GATES.md`, lines `789` and `1321`.

**Quote, line 789**, as the header of a block of published output:

> `python tools/gate_packaging_mutation.py --check-drift          -- command output, 2026-09-08`

**Quote, line 1321**, in the *Running it yourself* list a reader is told to run:

> `python tools/gate_packaging_mutation.py --print-regions  re-pin the reproduced regions`

*(Line `1334` carries the same defect for `--check-drift` in the same list.)*

**Refutation.**

```
python tools/gate_packaging_mutation.py --check-drift      rc=2
python tools/gate_packaging_mutation.py --print-regions    rc=2
  usage: gate_packaging_mutation.py [-h] --out OUT [--only ONLY] [--work WORK]
                                    [--check-drift] [--print-regions]
  gate_packaging_mutation.py: error: the following arguments are required: --out

python tools/gate_packaging_mutation.py --check-drift --out /tmp/pkgout    rc=0
  reproduction check: 11 sequence fragment(s) ... 3 pinned region(s) holding 25 command
  line(s) at the declared digests; 5 divergence(s) declared ...
```

`--out` is required by the parser. The last line of the same list already spells it —
`python tools/gate_packaging_mutation.py --out DIR` — so the omission is in the two lines this round
added and not in the reader's understanding. **The output published at line 789 is correct**: with
`--out` supplied, all four counts, the three digests and the five divergences reproduce exactly. Only
the invocation is unrunnable. This is the class `docs/SECOND-READER.md` §3 calls *a procedure that
cannot execute at the moment it fires*, in the page that catalogues that class.

**Exact replacement text, line 789:**

> `python tools/gate_packaging_mutation.py --out artifacts/packaging --check-drift`
> `                                                        -- command output, 2026-09-08`

**Exact replacement text, line 1321:**

> `python tools/gate_packaging_mutation.py --out DIR --print-regions   re-pin the reproduced regions`

**Exact replacement text, line 1334:**

> `python tools/gate_packaging_mutation.py --out DIR --check-drift     is the reproduction still ci.yml's sequence?`

### F-5-3 — `gates.figures` is ranked 3 on a present-tense sentence about a tree that does not exist, and that rank is what made the top-of-ranking rule waivable

**Files:** `.github/gates.toml` lines `720`–`721`; `docs/GATES.md` line `307`; against
`tools/render_figures.py` line `68`.

**Quote, `.github/gates.toml:720`:**

> Inert, a figure carrying a number nothing measured sits on a page and reads as evidence

**Quote, `docs/GATES.md:307`:**

> Its honest factors are `(published_numbers, silent, sole)` — the same three `claims` declares

**The third description of the same gate, `tools/render_figures.py:68`, by the workstream that wrote
it:**

> Nothing here edits `README.md` or any other page, and no shipped document links to
> `docs/figures/`. That matters for more than tidiness: it is why this gate is evidence apparatus
> rather than a published-numbers gate, and the day a figure is embedded in a shipped page that rank
> becomes wrong.

**Refutation.** Check C2 — two documents describing one mechanism; here, three.

```
grep -rn "figures/" --include=*.md --include=*.toml --include=*.yml --include=*.in .
  ./.github/gates.toml:765:  { file = "docs/figures/refusal-curve-light.svg", ... }

grep -rn -i "figure" README.md CHANGELOG.md docs/*.md | grep -c "docs/figures"
  0
```

**No shipped document embeds or links a figure.** `MANIFEST.in` carries `recursive-include docs *.md`
and no rule for `docs/figures/`, so an sdist does not even carry them —
`tests/test_render_figures.py` declares a `needs_committed` skip for exactly that. The gate's
`blast_radius = "published_numbers"` describes a future, and `cost_if_inert` states that future in
the present tense.

**Why this is worth a finding rather than a quibble.** `docs/GATES.md` uses that rank, and only that
rank, to justify a permanent change to the register's one unwaivable rule:

> And a rank-3 gate with no evidence is refused, by a rule with no waiver. […] the only way to land a
> correctly-ranked new gate was to rank it dishonestly low. *That is worse than what the rule was
> preventing.*

The page names the alternative — *"declare a blast radius nobody believes so the gate sorts down into
the teens"* — and rejects it as dishonest. But `published_numbers` for a gate over numbers nothing
publishes is a blast radius nobody currently believes, pointed the other way. **The rank may still be
the right call**; what is not right is a present-tense sentence in the register asserting the
condition that makes it right. `added_gates` should be bought with an accurate field or with an
argument, not with a tense.

**Exact replacement text, `.github/gates.toml`, `gates.figures.cost_if_inert`, replacing the sentence
spanning lines 720–723:**

> Inert, a figure carrying a number nothing measured reads as evidence -- and reads BETTER than
> prose, because a chart is quoted, screenshotted and re-published without its source. D-060 records
> the same class in prose and the gate that caught it does not reach here. RANKED FOR THE STATE THIS
> REPOSITORY IS ENTERING RATHER THAN THE ONE IT IS IN: as this is written no shipped document links
> to docs/figures/ and MANIFEST.in does not carry it, so the blast radius is prospective and
> tools/render_figures.py's own docstring says so. The rank is taken deliberately at the moment the
> figures land rather than at the moment one is embedded, because the embedding is the commit that
> would otherwise arrive with the gate ranked in the teens and nobody re-reading this field.

**Exact replacement text, `docs/GATES.md:307`, replacing the sentence:**

> Its factors are `(published_numbers, silent, sole)` — the same three `claims` declares — and they
> are **prospective rather than current**: no shipped document links to `docs/figures/` yet, and
> `tools/render_figures.py`'s own docstring says the rank becomes right on the day one does. Ranking
> it now rather than on that day is a choice, stated here because the rest of this section leans on
> the rank.

### F-5-4 — the round that ships figures ships them outside both triggers and outside the rotation

**Files:** `docs/SECOND-READER.md` line `122`; `tools/second_reader.py` lines `214`–`230` and
`276`–`299`.

**Quote, `docs/SECOND-READER.md:122`:**

> And minus everything under `docs/` that is not Markdown — `docs/cold-reads.toml` is this policy's
> machine state, not a page a stranger reads, and a trigger that fired on it would make every cold
> read demand a cold read of its own findings.

**Quote, `tools/second_reader.py:219`–`221`, the same reason in the code:**

> and it reaches non-Markdown files under `docs/` -- the findings ledger itself among them -- which
> are machine state rather than prose.

**Refutation.**

```
git status --porcelain --untracked-files=all -- README.md CHANGELOG.md CONTRIBUTING.md \
    SECURITY.md pyproject.toml docs
  ...
  ?? docs/figures/monoculture-band-dark.svg
  ?? docs/figures/monoculture-band-light.svg
  ?? docs/figures/refusal-curve-dark.svg
  ?? docs/figures/refusal-curve-light.svg

python tools/second_reader.py --trigger
  trigger A: 8 user-facing file(s) changed in the working tree     <- none of the four

python -c "import importlib.util,sys; s=importlib.util.spec_from_file_location('sr',
  'tools/second_reader.py'); m=importlib.util.module_from_spec(s); s.loader.exec_module(m);
  print(m.is_user_facing('docs/figures/refusal-curve-light.svg'),
        len(m.user_facing_files()))"
  False 21
```

`git status` **does** report them; `is_user_facing` drops them; `user_facing_files()` walks
`docs/**/*.md` and returns the same `21` it returned before the figures existed. So `--check`'s
tree-reachability rule — the one added because mutation `D` got through, whose whole point is that
*a set checked only against itself agrees with itself perfectly* — cannot see four new user-facing
files. The rotation set cannot hold them, and no round will ever be told to read one.

**What is at stake, stated narrowly.** The *numbers* on those canvases are gated twice over, by
`gates.figures` and by `TestNoNumberOnACanvasIsUncited`. What is ungated is everything a cold read
exists to check: the title sentence, which region gets shaded, what the accent marks, and 626
characters of alt text. §1 above found all four sound — **by a reader who was told to look, not by a
trigger that said to.** Section 7 of the policy already names the identical hole for `src/` and calls
finding it *"luck wearing a checklist's clothes"*. This is the second instance, in a file class the
policy explicitly reasoned itself out of covering, on the round that created it.

**The cost is small here and that is the argument for doing it now.** Admitting the package's source
would take the rotation from `21` to `61`. Admitting `docs/figures/*.svg` takes it to `25`, and the
four are regenerated by one committed script, so a cold read of them is a cold read of four `<desc>`
blocks and two title sentences.

**Exact replacement text, `docs/SECOND-READER.md:122`, replacing the sentence:**

> And minus everything under `docs/` that is neither Markdown nor a committed figure —
> `docs/cold-reads.toml` is this policy's machine state, not a page a stranger reads, and a trigger
> that fired on it would make every cold read demand a cold read of its own findings.
> **`docs/figures/*.svg` is the exception and it was added because the round that created that
> directory produced four user-facing files this trigger could not see.** A chart is prose with a
> shading decision in it: `tools/check_claims.py` cannot read one (R16) and `tools/render_figures.py`
> answers that for the *numbers*, byte-diffing every drawing against `bench/results.json`. Nothing
> answered it for the title, the accent assignment or the alt text, which is what a cold reader is
> for.

**Exact replacement text, `tools/second_reader.py:217`–`221` (the `is_user_facing` docstring body),
and the code beneath it must change with it:**

> The pathspec is the coarse filter and this is the fine one. ``docs`` reaches
> ``docs/DECISIONS.md``, ``docs/AUDIT-*.md`` and ``docs/notes/*``, which the policy excludes. It also
> reaches non-Markdown files under ``docs/``, and those split two ways: ``docs/cold-reads.toml`` is
> this policy's own machine state, and ``docs/figures/*.svg`` is a **document** -- a title sentence,
> a shaded region and an alt-text paragraph that a stranger reads and that no other mechanism here
> reads at all. The second is user-facing; the first is not.

Beneath it, `is_user_facing` needs `docs/figures/*.svg` admitted alongside `docs/*.md`,
`user_facing_files()` needs a matching `docs/figures/*.svg` sweep, and the four files need entries in
section 3's rotation block — `--check` will redden naming them until they do, which is the anti-rot
rule working as designed and is why this finding is cheap to apply.

### F-5-5 — trigger B served a file trigger A had already served, and nothing refuses that

**File:** `docs/SECOND-READER.md` §3, *Trigger B — the rotation*, and `tools/second_reader.py`
`validate()`.

**Quote:**

> Each round also cold-reads **one** user-facing file the diff did *not* touch, taken from a fixed
> rotation.

**Refutation.**

```
python tools/second_reader.py --check   | grep 'trigger B'
  trigger B serves docs/GATES.md next
python tools/second_reader.py --trigger | grep GATES
  docs/GATES.md                                   <- also in trigger A, 610 lines changed

grep -n rotation_served tools/second_reader.py
  595:  is it in the rotation set
  600:  does cursor_after equal successor(rotation, rotation_served)
  608:  does it equal the previous read's cursor_after
  617:  is it empty without a note
  (no rule compares rotation_served against trigger_a())
```

`docs/GATES.md` is the second-largest diff in this round and is what the cursor points at, so the
sentence quoted above is false of this read and the gate is green anyway. **The rotation turned and
bought nothing**: its stated purpose is that *a document nobody edits is a document nobody re-reads*,
and this round's rotation file is the document most edited.

**This was predicted a round ago and is now observed.** `cold-read-4-findings.md` §0 records the same
overlap arriving for `docs/SUPPORT_MATRIX.md` and calls it *"luck, not the mechanism"*. Counting
reads three, four and five: **three consecutive reads in which trigger B decided nothing** — twice by
the stall, once by overlap.

**Exact replacement text, `docs/SECOND-READER.md` §3**, appended to the *Trigger B* paragraph:

> **And when the cursor lands on a file trigger A already served, trigger B buys nothing and the
> round should say so rather than count it.** That is not hypothetical: it happened on read four
> (`docs/SUPPORT_MATRIX.md`, noted at the time as luck rather than mechanism) and again on read five
> (`docs/GATES.md`, the round's second-largest diff). The rule is **advance to the first rotation
> entry trigger A did not serve, and record the skipped entries in `rotation_served` as a list** —
> the cursor still moves by one per skipped file, so no page is dropped, and the read that would have
> been redundant is spent on the next untouched page instead. `--check` should refuse a
> `rotation_served` whose first element is in `trigger_a()`.

*(An applier who does not want to change the mechanism this round should still change the sentence:
strike "the diff did *not* touch" and write "the rotation cursor points at, whether or not the diff
touched it", so the page stops describing a property the code does not have.)*

### F-5-6 — `tools/gate_sdist_files.py` still prints a reason the runner refuted, and no trigger reaches it

**File:** `tools/gate_sdist_files.py`, lines `20`–`23`.

**Quote:**

> `data/LICENSES.md` is the one to read twice: it is held by this list **and by nothing else in the
> repository**, measured -- the extracted-tree suite passes with it gone, because no test reads it,
> while two shipped documents cite it as evidence.

**Refutation**, from the runner rather than from a laptop:

```
gh run view 34099756605 --log | grep -E "^b "        -- ubuntu-latest, CPython 3.12, at 34925f8
  b       FAILS     FAILS             passes            data/LICENSES.md out of the sdist
                    ^^^^^ the extracted-tree suite
gh run view 33379084166 --log | grep -E "^b "        -- replicated, 2026-08-31, same commit
  b       FAILS     FAILS             passes            data/LICENSES.md out of the sdist
```

Both halves are false: it is *not* held by nothing else (`tests/test_gate_scripts.py::
TestSdistFileList` asserts `gate_sdist_files.missing(REPO_ROOT) == []`, and inside an extracted sdist
`REPO_ROOT` is the artifact), and the extracted-tree suite does *not* pass with it gone.
`.github/gates.toml:1567` already records this and explicitly leaves the string alone —
*"reported rather than edited here, because it is what the gate PRINTS when it fires"*.

**Carried here so it has a line number and replacement text**, and because it demonstrates
`docs/SECOND-READER.md` §7's other hole from a new direction: `tools/` is outside `PATHSPEC`, `tools/`
**ships in the sdist**, and this string is what a reader sees at the moment the gate fails.

**Exact replacement text, `tools/gate_sdist_files.py:20`–`23`:**

> Each entry carries the reason it is here, and the reason is printed on failure rather than being a
> comment somebody has to go and find. ``data/LICENSES.md`` is the one to read twice, and the reason
> CHANGED under it: this file used to say the extracted-tree suite passed with it gone, because no
> test read it. That stopped being true when ``tests/test_gate_scripts.py`` arrived --
> ``TestSdistFileList`` asserts ``missing(REPO_ROOT) == []`` and in an extracted tree ``REPO_ROOT``
> is the artifact, so the list is now enforced from inside the distribution too. Measured on a
> runner: run 34099756605, breakage ``b``, ``FAILS`` in the extracted tree, replicated by run
> 33379084166. Two shipped documents still cite it as evidence, which is why it is on this list.

### F-5-7 — the figure pipeline documents one allowlist and has two, and the second lives in the module under test

**Files:** `tools/render_figures.py` line `30`; `tests/test_render_figures.py` line `31`.

**Quote (both files carry the same sentence):**

> and each one must be a value the `<desc>` cites -- against one allowlist of axis ticks declared in
> the test that a new number cannot join without a visible edit.

**Refutation.** Check C6 — a prose claim about a tool's configuration; read the configuration.

```
grep -n "uncited_numbers(svg" tests/test_render_figures.py
  356:  assert uncited_numbers(svg, figs._GATES) == []
  370:  assert [token for token, _row in uncited_numbers(injected, figs._GATES)] == ["41.20"]

grep -n "^_GATES" tools/render_figures.py
  503:  _GATES: Tuple[str, ...] = ("0.00", "0.01", "0.02", "0.05", "0.10", "0.15", "0.20")

python -c "...; print(sorted(set(rf.cited_lines(svg).values())))"
  ['0.10', '100.00', '11.33', '16.77', '22.78', ... ]     <- no '0.00', no '0.20'
AXIS_TICKS = ("0","20","40","60","80","100")              <- no '0.00', no '0.20'
```

The refusal curve's subtitle draws `0.00` and `0.20`. They pass because `_GATES` is handed in as
`extra_allowed` at both call sites, and `_GATES` is a tuple of literals in the *generator*, not in the
test. **The mechanism is sound** — those strings assemble every citation key on the chart, so a wrong
one fails to resolve rather than passing quietly, and `render_figures.py:580` says exactly that. The
sentence describing it is not: there are two allowlists, one of them is not "axis ticks", and one of
them is not "declared in the test". A phrasing tighter than the measurement.

**Exact replacement text (both files, the same sentence):**

> and each one must be a value the ``<desc>`` cites -- against two allowlists and no more: the axis
> ticks declared in the test, and ``render_figures._GATES``, the threshold strings the figure's
> citation keys are assembled from, so a sweep that moved would fail to resolve rather than leave a
> subtitle describing the old one. A number can join neither without an edit a reviewer sees.

### F-5-8 (low) — "verbatim" over a paraphrased cell

**File:** `docs/GATES.md`, the packaging coverage table, header *"captured log, verbatim, abridged"*.

Row `e` reads `test_splits_manifest.py, same defect`; the captured log reads
`test_splits_manifest.py loads bench/corpora.py at module level, unguarded`. Row `d` is truncated
(`loads bench/ unguarded` for `loads bench/ at module level, unguarded`), which "abridged" covers; row
`e` is a rewrite, which it does not. Every *figure* in the table is verbatim and correct — verified
against both runs below. **Replacement:** restore row `e`'s label to the log's wording, or change the
header to `-- captured log, figures verbatim, labels abridged`.

---

## 3. What was checked and did not move

A cold read that reports only defects has not read. All of the following were re-derived on this
tree, not carried:

**Every `tools/gates.py` output block in `docs/GATES.md` reproduces byte-for-byte.** `--check`,
`--list | tail`, `--ranking` (rows 1–10 and 23, 27, 37, 38) and `--evidence-provenance`'s
`0 of 16` all match what the page prints, including `38 gate(s) across 23 environment(s) in 5
workflow file(s)` (`ls .github/workflows | wc -l` = 5).

**Both scheduled runs verified independently rather than through the page's transcription.** This is
the round's largest claim and the page itself says nothing here can read a run log, so it was read
with `gh`:

```
gh run view 34099756605 --json headSha,conclusion   34925f8, success, 2026-09-07
gh run view 33379084166 --json headSha,conclusion   34925f8, success, 2026-08-31
gh run view <both> --log | grep -c DEMONSTRATED      16 distinct gates each
                          | grep -c "INERT or UNRESTORED"  every line reads "0 INERT or UNRESTORED"
                          | grep "catches"           build/extracted tree catches 5 of 5
                          | grep "^b "               b FAILS FAILS passes   <- the corrected row
```

The sixteen names, both runs: `claims`, `splits_manifest`, `suite`, `schema_copies_match`,
`import_ceiling`, `tier_zero_purity`, `ngram_matches_lexicon`, `resource_formats`, `gate_manifest`,
`mypy`, `ruff`, `ruff_format`, `test_environment_control`, `control_always_green`,
`control_always_red`, `harness_lint_environment`. **The two runs agree case for case**, which is what
`docs/GATES.md` claims and what nothing in this repository could otherwise check.

**`docs/GOVERNED_NAMING.md`'s unaccounted-character census re-derives exactly, every cell.** Its own
block says the probe is uncommitted and re-derivable from four lines; it is, and it was:

```
python - <<'PY'   (the four lines the page publishes, over data/governed_gold/*.json)
  socrata   identifier  distinct= 69,682  hits=   325   0.4664%   rows=  2,041/155,272 = 1.3145%
  socrata   label       distinct= 75,689  hits=11,093  14.6560%   rows= 18,390/155,272 = 11.8437%
  sec_xbrl  identifier  distinct= 68,038  hits=     0   0.0000%   rows=      0/ 90,655 = 0.0000%
  sec_xbrl  label       distinct= 72,430  hits=26,080  36.0072%   rows= 31,130/ 90,655 = 34.3390%
  begins ':@computed_region_': 325 of 325 ;  non-matching sample: []
```

**All eight figures, both denominators, and both exhaustive claims survive** — *"All 325 Socrata
field-name hits are one pattern"* and *"Not one other physical identifier in either corpus carries
such a character"*. This is the strongest claim on that page and it is the strongest evidence in this
round.

**`857,517` is arithmetic and it is right.** `(69,682 + 75,689 + 68,038 + 72,430) x 3 policies =
857,517`, matching `CHANGELOG.md:192` and `docs/GOVERNED_NAMING.md:1426`.

**C3, the pasted output.** `docs/GOVERNED_NAMING.md`'s `catalog_gap` example returns exactly what is
printed beside it — `(1, 3)`, `[('applnt', 2), ('dt', 1), ('id', 1), ('txn', 1)]`, `0` — and
`acronymkit governed-gap schema.csv` runs with no `--dictionary`, writes no file and reports
`catalog lookups 0`, which is what `docs/SOURCING.md` and `docs/SUPPORT_MATRIX.md` promise.

**C3 on the breaking change.** `normalize('TXN_\xa9_ID', GovernedDictionary({}))` raises
`TokenizationError` naming `'\xa9' (U+00A9)`; `is_compliant` returns `unreadable_character` with
`token=None`, `fix=None`, `NOT_UPPER_SNAKE` carrying no fix, `compliant=False`; `to_physical_name`
fills `unaccounted=('(', ')')`. Every sentence of the `CHANGELOG.md` entry checked out.

**C5, pointers.** Every relative link and every anchor in `README.md`, `CHANGELOG.md` and ten `docs/`
pages resolves — `0` bad of the set, checked with GitHub's slug rules (spaces replaced individually,
not collapsed).

**C1 on `docs/OFFLINE.md`'s corrected count.** `grep -c '\.command(' src/acronymkit/cli.py` = `17`;
the probe's `invocations` list in `.github/workflows/ci.yml` drives `13` distinct subcommands; the
four it does not — `normalize-name`, `governed-batch`, `governed-audit`, `governed-gap` — are exactly
the four the page names. `13 of 17` is right and so is the list.

**`catalog_gap` run ids resolve to the values `docs/SOURCING.md` unfences.** `columns = 69,682`,
`unreachable_columns = 15,842`, `distinct_tokens = 24,536`, and `byoc_agreement` records
`columns_agree = True` over `69,682` pairs.

---

## 4. Defects noted elsewhere, reported and not applied

**The CRLF class is live in this working tree right now.** `docs/GATES.md` documents it, says there
is no gate on it, and says this round's own six files were repaired. Those six were. Six *others*
are not:

```
git ls-files --eol $(git diff --name-only) | grep w/crlf
  i/lf  w/crlf   bench/results.json
  i/lf  w/crlf   docs/GOVERNED_NAMING.md
  i/lf  w/crlf   docs/OFFLINE.md
  i/lf  w/crlf   docs/SOURCING.md
  i/lf  w/crlf   docs/SUPPORT_MATRIX.md
  i/lf  w/crlf   tests/test_cli.py
```

`git status` is clean about all six. `bench/results.json` is the one to care about: it is the file
every claim in this repository resolves against, and `.gitattributes` declares `*.json text eol=lf`
because of the schema-copy gate. Not this reader's to fix and not `docs/GATES.md`'s workstream's
either — recorded because the page says the class *"is still not gated"* and this is what that
sentence costs on the day it was written.

**`docs/figures/*.svg` is not in `MANIFEST.in`.** Deliberate and declared —
`tests/test_render_figures.py` carries a `needs_committed` skip naming it — so half the R16 gate
cannot run in an extracted sdist. Worth a decision rather than a fix: the day a shipped document
embeds a figure (see `F-5-3`), the link guard in `tests/test_packaging_manifest.py` will redden, and
`MANIFEST.in`'s own comment block already records that pattern happening five times.

---

## 5. What this read could not adjudicate, and why

**The `12 of 36` → `16 of 38` movement is a transcription, and this reader could only check it by
leaving the repository.** `gh` was available, so it was checked (§3), and it holds. **In a checkout
with no network it would not have been checkable at all** — which is `docs/GATES.md`'s own lead item,
written by the workstream that had just been wrong about the same thing twice in the same direction.
It is recorded here because a cold read whose verification of the round's largest claim depends on an
authenticated GitHub token is a cold read with an external dependency nobody has priced.

**No mutation was run.** §4.3 of the policy asks for one in situ, and the two shapes available this
round were both refused: the figure gate's probe edits `.github/gates.toml`, which
`docs/GATES.md`'s workstream is writing to, and `--mutate` restores from bytes read beforehand. A
restore that overwrites a concurrent write is a worse failure than a missing probe. The negative
demonstration that section 4.3 says *is* valid on a developer machine — a gate shown **blind** — was
taken instead and is `F-5-4`: `python tools/second_reader.py --trigger` returns eight files in a tree
holding four new user-facing figures, and `--check` is green.

**This read's pre-registration was written after the outcome, and it is reported as void rather than
quoted.** The round required a falsification criterion in a scratch file before the first probe; the
first probe here was `git status` against the trigger-A pathspec and no such file existed until the
findings were written. **A pre-registration that can be written after the outcome is not one** — the
same shape as *"a check that exists only in a transcript is not a check"*, which this repository has
now written four times. The reconstructed expectations are in the scratch note and are labelled
reconstructed; the honest summary is that all three of them were falsified — the charts are sound on
the axis the brief flagged, the cursor stall is broken, and `gh` was authenticated so the run logs
were checkable after all — and that **the finding this read actually produced (`F-5-4`) was on none
of the three lists.** Read four's own §0 has the same shape recorded against it. Whether that pattern
means the protocol needs a mechanism rather than an instruction is a question for the recorder, not
for this reader.
