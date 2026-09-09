# Cold read 6 — findings

Read of the working tree of `2026-09-09`, against `017cb37`. Fourth execution under the read-only
rule of `docs/SECOND-READER.md` section 5. **This reader changed nothing but this file.** Every
`refutation` below is a command whose output I saw in this session; none is carried from a record.

**Trigger A** — `git status --porcelain --untracked-files=all -- README.md CHANGELOG.md
CONTRIBUTING.md SECURITY.md pyproject.toml docs`, minus `docs/DECISIONS.md`, `docs/AUDIT-*.md`,
`docs/notes/*.md` — served nine files: `CHANGELOG.md`, `CONTRIBUTING.md`, `README.md`,
`docs/CLAIMS-LEDGER.md`, `docs/DEFINITION-OF-DONE.md`, `docs/EVALUATION.md`, `docs/GATES.md`,
`docs/POSITIONING.md`, `docs/SECOND-READER.md`.

**Trigger B** — `python tools/second_reader.py --check` prints *"trigger B serves
docs/SECOND-READER.md next"*, and the ledger's `cursor_after` for read `2026-09-08` is
`docs/SECOND-READER.md`. The cursor is derivable and agrees with the page.

**Trigger B served a file trigger A had already served.** That is `F-5-7`'s sibling `F-5-5`,
reproduced on the first read after it was raised: the rotation's one turn per round was spent on a
document the diff already forced me through, so no untouched file was covered by mechanism this
round. The rotation is `25` files and this is the second consecutive read to lose its turn to an
overlap.

**The eight gates, run at the start and again at the end, unchanged in between.**

```
python -m pytest tests                              5798 passed, 10 skipped, 1 xfailed
python -m ruff check src tests tools bench          rc=0  All checks passed!
python -m ruff format --check src tests tools bench rc=0  156 files already formatted
python -m mypy                                      rc=0  99 source files
python tools/check_claims.py                        rc=0  value-matched 64/64, deferred 189/189
python tools/splits.py --check                      rc=0
python tools/gates.py --check                       rc=0  in-situ 18 of 39
python tools/second_reader.py --check               rc=0  open 5, fixed 10, of 15
```

Green — but see `F-6-7`: `pytest` was **red in five of the seven runs I took**, always for the same
reason and never for a reason about this tree.

---

## F-6-1 — the sixth document was corrected and the seventh was not

**Severity: high.** This is the failure shape the brief named, found where the brief did not look.

`file` = `docs/SOURCING.md`, lines `625` and `632`–`633`.

**Quoted exactly**, line `632`–`633`:

> **D and E are the two holes, and they are the same two.** `latency` is not in the gate's arming
> vocabulary and a spelled-out `microseconds` is not in its unit vocabulary, so an invented latency
> claim on this page would never be seen

and line `625`, inside the battery block:

> `  rc=0  D  prose line added: "Median latency ... 41 microseconds"     <file not named>`

**Refutation.** Both halves of the sentence are now false, and the page states them in the present
tense:

```
python - <<'EOF'   # tools/check_claims.py loaded by path, nothing mutated
'latency'  in _KEYWORDS           -> True
'duration' in _KEYWORDS           -> True
_UNIT_AFTER_NUMBER matches ' microseconds ...' -> True
SCAN_GLOBS -> ('README.md', 'CHANGELOG.md', 'docs/*.md', 'docs/notes/*.md',
               'src/acronymkit/*.py', 'src/acronymkit/**/*.py', 'bench/splits.toml')
keyword_positions('Median latency for a governed expansion fell to 41 microseconds
                   in this release.')                 -> [7]
iter_claim_numbers(...) + arming_of(...)              -> (48, '41') armed by 'keyword'
EOF
```

`docs/*.md` is in `SCAN_GLOBS`, so this page is scanned; `latency` arms the number at offset `48`
from the keyword at offset `7`. The sentence's claim that such a figure *"would never be seen"* on
this page is refuted at the level of the rule, not merely of an exit code — which is stronger than
re-running the battery, and does not require mutating a file on a shared checkout.

**The count is wrong wherever it is published.** `docs/GATES.md` line `1243` heads a table *"Six
documents corrected, and the disposition discharged"* and says *"six shipped files immediately
stated something false. All six were corrected in the same commit."* The same six are enumerated in
`tests/test_claims_gate_coverage.py` lines `46`–`50`, asserted again in `docs/SECOND-READER.md`
(*"all six documents were corrected in the same commit"*) and again in `docs/DEFINITION-OF-DONE.md`
(*"Keeping the hole open so that six documents describing it stayed accurate"*). **Seven files
stated it. Six were corrected.** `docs/SOURCING.md` is the seventh, and it is the page that calls
itself *"reproduced on a third page rather than carried on that record's word"* — the third
independent reproduction of the blind spot, which makes it load-bearing rather than incidental.

`tests/test_claims_gate_coverage.py`'s own docstring predicted this exactly: *"A third copy in a
file nobody listed here is invisible to it."* Its `_RETIRED_OVERCLAIMS` check runs over `README.md`
and `docs/EVALUATION.md` only.

**Exact replacement text.** `docs/SOURCING.md` line `625`, in the battery block — this row must be
**re-run**, not edited, per the convention the other three batteries held to this round. When it is
re-run it will read:

```
  rc=1  D  prose line added: "Median latency ... 41 microseconds"     docs/SOURCING.md named
```

`docs/SOURCING.md` lines `632`–`637`, replacing the paragraph beginning **"D and E are the two
holes"**:

> **D used to be a hole and is now the correction; E is still a hole.** `latency` was not in the
> gate's arming vocabulary and a spelled-out `microseconds` was not in its unit vocabulary, so an
> invented latency claim on this page was never seen — the blind spot `docs/DECISIONS.md` D-060
> found in `README.md` and this page reproduced on a third page rather than carrying on that
> record's word. It is closed: `latency` and `duration` are metric keywords and the spelled-out
> sub-second units are units, and the row above is the **re-run**, not an edited digit. What the
> closure did not reach is published in `docs/GATES.md` — the plurals `latencies` and `durations`,
> a bare `seconds`, a speedup written `41.37x`, and byte figures. And every fenced block on this
> page is outside the gate entirely, which D-052 says is mechanically indistinguishable from
> hiding: section 0's traffic figures, section 4's power table and section 5's sizing block could
> all be edited to say anything. The command is printed above each one so a reader can re-derive
> it, and **that convention is the only thing separating those blocks from hiding.**

And **the count**, in all four places, becomes **seven**: `docs/GATES.md` line `1243` heading
*"Seven documents corrected, and the disposition discharged"* with a `docs/SOURCING.md` row reading
`| `docs/SOURCING.md` | a battery whose row `D` is `rc=0`, on a third page | battery re-run, row `D`
is `rc=1` |`; the same in `tests/test_claims_gate_coverage.py` lines `46`–`50`, in
`docs/SECOND-READER.md` and in `docs/DEFINITION-OF-DONE.md`.

---

## F-6-2 — `4.38 times alpha` is true at one of five measured alphas and is stated unconditionally

**Severity: medium.** Two shipped surfaces, one of them the API docstring.

`file` = `src/acronymkit/propagation.py` line `397`, and `CHANGELOG.md` line `122`.

**Quoted exactly**, `propagate()`'s docstring:

> it does not bound the share of the gate's answers that are wrong -- measured at ``4.38`` times
> ``alpha`` on ``conformal.sdu21.exchangeable``

and `CHANGELOG.md`:

> It does not bound the share of the gate's answers that are wrong, which is that rate divided by
> the answer rate and was measured at `4.38` times `alpha` on `conformal.sdu21.exchangeable`.

**Refutation.** `selective_error_over_alpha` is a recorded field of that run at five alphas, and it
is monotone decreasing:

```
python - <<'EOF'   # bench/results.json, runs['conformal.sdu21.exchangeable']
alpha  selective_err%  selective_error_over_alpha  answered/eval
0.05   21.92           4.38                        292/3095
0.10   28.85           2.88                        520/3095
0.20   37.02           1.85                        859/3095
0.30   41.02           1.37                       1192/3095
0.50   48.42           0.97                       1743/3095
EOF
```

`4.38` is the **maximum over the five**, at the smallest alpha. At `alpha = 0.50` the multiple is
`0.97` — below `alpha`, not above it. A caller who reads *"measured at `4.38` times `alpha`"* and
sets `alpha = 0.20` predicts `87.6` % and gets `37.02` %.

**This is an overstatement of the danger, not of the guarantee**, so it is not the overclaim the
brief feared reproduced; it is the reciprocal error, and it is still a number-bearing sentence that
is false as written on the surface with the widest audience. The four correctly-scoped uses —
`propagation.py` lines `67` and `127`, `docs/EVALUATION.md` lines `901` (cited) and `2601` — all
attach the multiple to `alpha = 0.05`. Only the two above float free.

**The guard pins the loose form.** `tests/test_propagation.py` line `538` asserts `"4.38" in body`
of `propagation.py` and asserts nothing about the alpha it belongs to, so the rule that exists to
keep the factor at the call site is satisfied by the version that omits its condition.

**Exact replacement text.** `src/acronymkit/propagation.py` line `396`–`398`:

>     gate's answers that are wrong -- measured at ``4.38`` times ``alpha`` at
>     ``alpha = 0.05`` on ``conformal.sdu21.exchangeable``, and at ``1.85`` times
>     ``alpha`` at ``alpha = 0.20``; the multiple falls as ``alpha`` rises --

`CHANGELOG.md` line `121`–`123`:

> It does not bound the share of the gate's answers that are wrong, which is that rate divided by
> the answer rate and was measured at `4.38` times `alpha` at `alpha` of `0.05` on
> `conformal.sdu21.exchangeable`, falling to `1.85` times `alpha` at `0.20`.

And `tests/test_propagation.py` line `538` should assert the pair, not the number:
`assert "4.38" in body and "alpha = 0.05" in body`.

---

## F-6-3 — `80 pre-existing records` is `40` records and `80` field-values

**Severity: medium.** A machine-independent count, wrong by exactly two.

`file` = `docs/EVALUATION.md` line `2556`.

**Quoted exactly:**

> `elapsed_seconds` and `docs_per_second` moved on `80` pre-existing records; both are wall clock,
> neither is cited anywhere, and R18 leaves them unarmed notes.

**Refutation.** Diffing `git show HEAD:bench/results.json` against the working tree, flattened to
leaf fields:

```
run ids: old 700, new 717, added 17, removed 0
pre-existing run ids with NON-wall-clock movement: 0        <- the paper's other claim, TRUE
field-level changes by leaf name:
  elapsed_seconds: 40 value(s) across 40 run id(s)
  docs_per_second: 40 value(s) across 40 run id(s)
  total changed field-values: 80 ; changed run ids: 40, all in the `spans` family
environment block changed: False
```

`80` is the count of changed **field-values**; the count of **records** is `40`. This repository
uses "run record" for one entry keyed by run id (`docs/DECISIONS.md` line `5298`, *"the run
record's own"*), and the sentence names two fields and then a record count, so the natural reading
is `80` records each moving two fields — `160` values. The measurement is `40` and `80`.

The neighbouring claims in the same bullet are **true and were checked**: `0` non-wall-clock fields
moved on any pre-existing run id, and the two `run_spans.py` invocations added exactly `16` run ids
(the seventeenth, `extraction.med1250.acronymkit_propagated`, is `run_extraction.py`'s, and the
sentence correctly does not attribute it).

**Exact replacement text**, `docs/EVALUATION.md` line `2556`:

> `elapsed_seconds` and `docs_per_second` moved on `40` pre-existing records, `80` values in all;
> both are wall clock, neither is cited anywhere, and R18 leaves them unarmed notes.

---

## F-6-4 — `some forty points` is `32.52` points

**Severity: medium.**

`file` = `docs/EVALUATION.md` line `2528`.

**Quoted exactly:**

> the scope was worth about three points of a ceiling that sits some forty points below the trivial
> all-caps rule's recall on the same corpus.

**Refutation.**

```
python - <<'EOF'   # bench/results.json, short_form.exact_recall, PLOD-CW all/tight
spans.plod.all.tight.allcaps                        73.37
spans.plod.all.tight.oracle_definitional            37.50   -> gap 35.87
spans.plod.all.tight.oracle_definitional_propagated 40.85   -> gap 32.52
EOF
```

The gap is `32.52` points from the ceiling the sentence is about, or `35.87` from the pre-A2
ceiling. Neither is *"some forty"*. **The likely mechanism is worth naming**: the propagated
ceiling's own value is `40.85`, so a value has been read as a distance. That is the same
substitution class as `F-5-1`'s retained denominator, and it is invisible to the claims gate because
"forty" is spelled out — the residue class `docs/GATES.md` publishes as *"a metric named in a word
nobody put on the list"*, here in its numeral form.

**Exact replacement text**, `docs/EVALUATION.md` line `2527`–`2529`:

```
the scope was worth about three points of a ceiling that still sits some thirty-three points
below the trivial all-caps rule's recall on the same corpus --
73.37<!--claim:spans.plod.all.tight.allcaps.short_form.exact_recall:.2f--> % against the
40.85<!--claim:spans.plod.all.tight.oracle_definitional_propagated.short_form.exact_recall:.2f--> %
above.
```

(Fenced here so the citations are inert in this file and carry the house convention — no backticks
around a cited number — when they are copied across.)

---

## F-6-5 — `CONTRIBUTING.md`'s eight commands and its eight keys are different sets of eight

**Severity: medium.** The contradiction is six lines wide on one page.

`file` = `CONTRIBUTING.md`, gate block at lines `90`–`99` and sentence at line `161`.

**Quoted exactly**, line `161`:

> `status` is `complete` or `partial`; `gates` reports all eight commands above by key
> (`pytest`, `ruff`, `ruff_format`, `mypy`, `claims`, `splits`, `gates`, `second_reader`);

**Refutation.** The eight commands above are `pytest`, `ruff check`, `ruff format --check`, `mypy`,
`check_claims.py`, `splits.py --check`, `gates.py --check`, **`run_summary.py --check`**. The eight
keys are those seven plus **`second_reader`** and minus `run_summary`. The sets differ in two
places, so *"all eight commands above by key"* is false about its own page.

```
grep -n 'second_reader' .github/workflows/ci.yml     -> no match
grep -n 'second_reader' .github/gates.toml           -> no match
grep -n 'run: python tools/' .github/workflows/*.yml -> splits, check_claims, gates,
                                                        render_figures, gate_memo_identity,
                                                        run_summary, ... ; no second_reader
grep -n 'run: python -m'    .github/workflows/ci.yml -> ruff check, ruff format --check, mypy,
                                                        pytest
```

So **`python tools/second_reader.py --check` runs in no CI job and is in no gate register**, while
being a required key of every round summary and one of the eight gates every agent brief names.
`tools/gates.py --check` cannot see this: it refuses *a CI job that no gate register accounts for*,
which is the job→register direction; a documented gate with no job is outside it.

**In fairness to the round, half of this is deliberate and says so.** `tools/run_summary.py` lines
`194`–`200` state that the `run_summary` key is omitted on purpose because adding a ninth key
mid-round would invalidate every summary written to the standing brief, and that *"the key lands
when the brief lists nine."* That reasoning is sound and I am not asking for it to be reversed. What
it never reconciles is the other half: the comment asserts the key list is the brief's eight, and
does not notice that `CONTRIBUTING.md`'s block is a **different** eight. `CI runs all eight` of the
block's commands is **true** and was checked.

**Exact replacement text**, `CONTRIBUTING.md` line `88` and the fenced block:

> Nine commands. All nine must be green before you push, and CI runs eight of them —
> `tools/second_reader.py --check` is a gate this project runs by hand and by brief, and it is in
> no CI job:
>
> ```bash
> python -m pytest tests
> python -m ruff check src tests tools bench
> python -m ruff format --check src tests tools bench
> python -m mypy
> python tools/check_claims.py
> python tools/splits.py --check
> python tools/gates.py --check
> python tools/second_reader.py --check
> python tools/run_summary.py --check
> ```

and line `161`:

> `status` is `complete` or `partial`; `gates` reports eight of the nine commands above by key
> (`pytest`, `ruff`, `ruff_format`, `mypy`, `claims`, `splits`, `gates`, `second_reader`) — there
> is no `run_summary` key, and `tools/run_summary.py` says at `GATE_KEYS` why it lands only when
> the brief lists nine;

---

## F-6-6 — the guard against a stale gate list has a stale floor and a stale message

**Severity: medium.** Same class as `F-6-5`, one level down.

`file` = `tests/test_second_reader_policy.py` line `1003`.

**Quoted exactly:**

> `assert len(commands) >= 7, f"the gate block lists {len(commands)} commands; CI runs seven"`

**Refutation.** `CONTRIBUTING.md` now publishes eight commands and CI runs eight. The floor is `>= 7`
and the message says seven, so:

* a gate **deleted** from the block passes, as long as seven remain — the failure this test was
  written to catch;
* the assertion message is now wrong prose sitting inside the test whose stated purpose is that *"a
  list of the gates is exactly the kind of prose no gate reads — so this one is now read"*;
* the only by-name completeness check in the test is
  `assert any("tools/gates.py --check" in c for c in commands)`. Nothing checks for
  `tools/second_reader.py --check`, in the test module named after that policy.

Could this check have failed here? No: `len(commands)` is `8`, and `8 >= 7`. It could not have
detected `F-6-5`, and it cannot detect a regression to seven.

**Exact replacement text**, `tests/test_second_reader_policy.py` line `1003`:

> ```python
>     assert len(commands) == 9, (
>         f"the gate block lists {len(commands)} commands; this project has nine gates, "
>         "eight of them in CI. A gate deleted from the block is the defect this asserts against, "
>         "so this is an equality and not a floor -- adding a gate is a deliberate edit here."
>     )
>     for required in ("tools/gates.py --check", "tools/second_reader.py --check",
>                      "tools/run_summary.py --check"):
>         assert any(required in c for c in commands), f"{required} belongs in this list"
> ```

---

## F-6-7 — the injection harness fails the build on a condition it calls normal

**Severity: medium, process.** Not a false sentence; a gate that reds for a reason about somebody
else's tree.

`file` = `tests/test_claims_gate_coverage.py` lines `192`–`198`.

**Quoted exactly**, from `_run_gate_with_injection`'s docstring:

> when a second process is running the same module against the same checkout -- **which is the
> normal state of this repository** -- one restore writes back bytes captured while the other's
> injection was live

and the guard for exactly that condition, twelve lines below:

> `raise AssertionError("README.md already carries a claims-gate probe marker. ...")`

**Refutation.** I ran the suite seven times. Five were red; every red was this assertion, and the
failing parametrisation differed each time — `[memory in KB]`, `[bare seconds]` and `[speedup
multiplier]`, `[plural keyword]`, `test_the_positive_control_fails_the_build`,
`test_the_measured_price_of_the_closure_is_still_zero`. `README.md` carried no marker before or
after any run.

```
Get-CimInstance Win32_Process -Filter "Name like '%python%'"
  -> C:\Python313\python.exe -m pytest tests/ -q -p no:randomly --no-header ...   (PID 30304)
  ... and later 4400, then 28576/35336, then 37816/30216/36296/35228
```

Another workstream's suite was running against this checkout throughout, which is the documented
normal state. The module handles the **other** ordering correctly — `_or_skip` turns "another
process overwrote my injection" into a `pytest.skip`, and `test_no_probe_survived_an_earlier_run`
waits `10` seconds precisely to tell a live injection from debris. The start-of-injection guard
does neither: it fails immediately, with no wait, on the same condition its sibling waits out.

The consequence is that `python -m pytest tests` — gate one of eight — is **not a statement about
this tree** on a shared checkout. It went green for me only once both other suites happened to be
between injections: `5798 passed, 10 skipped, 1 xfailed`.

**Exact replacement text**, `tests/test_claims_gate_coverage.py` line `191`:

> ```python
>     deadline = time.monotonic() + 10.0
>     while _readme_debris() and time.monotonic() < deadline:
>         time.sleep(0.5)
>     if _readme_debris():
>         raise AssertionError(
>             "README.md has carried a claims-gate probe marker for ten seconds, so it is a "
>             "leftover rather than another process's live injection. Either a previous run of "
>             "this module died between injection and restore, or a second process is running it "
>             "against this checkout right now. Both leave an invented performance figure on the "
>             "front page that no gate here can see -- remove the marked line before re-running."
>         )
> ```
>
> — the same ten-second wait `test_no_probe_survived_an_earlier_run` already uses, for the same
> reason it uses it. A marker seen once is an overlap; a marker still there ten seconds later is
> debris. A gate that reds on an overlap is a gate that gets deleted.

---

## What I checked that came back clean, including the thing the brief expected to be wrong

**A2's conformal prose does not make the selective promise, on any surface I could find.** The brief
said this was the most expensive thing the round could ship, and I pre-registered that I expected
the brief to be right and that expecting it made confirmation cheap. It is not there. Every surface
that describes `gate=` names the bound **joint** and denies the selective reading explicitly:
`propagation.py`'s module docstring (*"What that buys is a **joint** bound and not a selective one.
Read the next two paragraphs before relying on it, because the natural reading is the wrong one and
its wrongness has a measured size"*), `JOINT_NOT_SELECTIVE`, `PROPAGATION_GAP`, `gate_disclosure()`
which concatenates `guarantee()` + both gaps so none can be quoted alone, `propagate()`'s docstring,
`CHANGELOG.md`, and `docs/EVALUATION.md`'s *"The gate, and the guarantee it is not"*. The second gap
— that nothing conformal says reaches the licensed occurrences — is stated on all seven too.
`README.md`, `docs/POSITIONING.md`, `docs/GATES.md`, `docs/DEFINITION-OF-DONE.md`,
`docs/ARCHITECTURE.md` and `docs/CLAIMS-LEDGER.md` do not mention propagation at all, so there is no
surface where a caller meets the gate without the disclosure. `F-6-2` is the only defect I found in
this subsystem's prose and it is a scoping error on a factor, not a promise about answers.

`tests/test_propagation.py::TestTheClaim` is a mutation-tested prose rule over `CLAIM_FILES` —
`propagation.py`, `docs/EVALUATION.md`, `README.md`, `CHANGELOG.md` — with a blocklist, a
paragraph-level "name it joint" rule and a sentence-level "name the selective rate only while
disowning it" rule. It is the right shape. **Its weakness is `F-6-1`'s weakness**: `CLAIM_FILES` is
a fixed list of four, two of which (`README.md`, and any future page) say nothing about propagation
at all, so the rule is vacuous on them and blind to a fifth surface.

**The figures did not move, and that is what the documents say.**
`python tools/render_figures.py --check` exits `0` with *"2 figure(s) x 2 theme(s) are
byte-identical to what bench/results.json renders, and every run id they cite resolves"*, and
`git status --porcelain -- docs/figures` is empty. `docs/EVALUATION.md`'s claim that all four SVGs
came back byte-identical is true. Trigger B did not serve a figure this round.

**The round's central "freeness" claim re-derives.** I re-derived both zeros independently, through
the gate's own `iter_prose_numbers`: over `95` files and `2,330` free-standing prose numbers,
**`0`** are armed by `latency` or `duration`, and **`0`** are followed by a spelled-out sub-second
unit. Arming distribution `unarmed 2065 | unit 175 | keyword 90`.

**A caution about that derivation, recorded because I got it wrong first.** My first attempt applied
`prose_of` line by line and reported `16` and `14` hits — every one of them inside a fenced battery
block. `prose_of(text, suffix)` strips fences over the **whole text** and cannot be applied per
line. The round's zeros are right and my first refutation was wrong; it is in here so that the next
reader who reaches for the same shortcut does not publish it.

**A2's arithmetic checks.** Verified against `bench/results.json` and not carried from the prose:
recall `36.53`→`39.60` (`+3.07`), precision `93.66`→`93.73`, `88` new gold spans, `0` lost, `96`
offered; `test` split gains `7`; oracle ceiling `37.50`→`40.85`, `1076`→`1172`; `1351` PLOD-CW
documents at about `37` tokens each; `5.95` is
`one_sense.pmc_oa.a2.*.a2_new_coverage_multiple_of_current` at all three profiles;
`extraction.med1250.acronymkit_propagated` differs from `extraction.med1250.acronymkit` on exactly
three of `19` fields — `system`, `elapsed_seconds`, `docs_per_second` — so *"agrees on all `16`
compared fields"* is exact. `41` is value-matched (`9` measurements equal it), so
`docs/EVALUATION.md`'s account of row `D` failing as a **ratchet** failure rather than an
unbacked-claim failure is consistent.

**Not verified, and named rather than assumed.** The R19 byte-identity pass — `4,260` documents,
`10,625` pairs, three profiles, `sha256` over every field of every pair — rests on a scratch script
not in the tree. I did not re-run it: it would take minutes of CPU on a checkout three other suites
are already using, and a digest I cannot reproduce is worth less than saying so. The control arm is
present and the design is right; the counts are unchecked by me. Likewise *"the whole span table
reproduced exactly on a second machine"* names no machine and I cannot check it (R18).

---

## Ledger entries these findings should become

`F-6-1` through `F-6-7`, `raised_in = "2026-09-09"`, `reader = "cold-read-6"`, all
`disposition = "open"` — none may be closed by me, and `applied_by` must not be this reader.
`reads` gains `id = "2026-09-09"`, `rotation_served = "docs/SECOND-READER.md"`,
`cursor_after = "docs/SOURCING.md"`, `covered = ["CHANGELOG.md", "CONTRIBUTING.md", "README.md",
"docs/CLAIMS-LEDGER.md", "docs/DEFINITION-OF-DONE.md", "docs/EVALUATION.md", "docs/GATES.md",
"docs/POSITIONING.md", "docs/SECOND-READER.md", "docs/SOURCING.md",
"src/acronymkit/propagation.py"]`.

`docs/SOURCING.md` is listed under `covered` although **neither trigger sent me there**. Trigger A
did not touch it and trigger B spent its turn on a file trigger A had already served. I reached it
by grepping every occurrence of `latency` in the tree — which is to say, by the method, not by the
mechanism. That is the fourth consecutive read in which the round's most expensive finding arrived
outside the rotation, and it is the argument for `F-5-5`.
