# Calling this library from the JVM

For a Java or Kotlin team that wants `acronymkit.governed` — short→long expansion of database column
identifiers against a governed catalog, the reverse direction, and the compliance verifier — inside
a Maven build.

---

## The decision

**Run `acronymkit governed-batch` as a long-lived co-process. Do not embed a Python runtime in your
JVM.**

There is no `acronymkit` Maven artifact and this document does not propose creating one. The
recommended integration is the one that already exists and is already specified: your JVM starts one
`acronymkit governed-batch` process, writes identifiers to its standard input, and reads one JSON
object per line back. [`examples/java/`](../examples/java) is a Maven project that does exactly that,
and it runs.

The alternative that looks most attractive on paper — GraalPy, distributed as Maven artifacts, able
to run Python inside a JVM with no Python installed — **now works**, which it did not before this
subsystem stopped importing `pydantic`. It is still the wrong default, and the reason is measurement
rather than taste: in the configuration a consumer gets by default on JDK 21 it is several times
*slower* than the subprocess, it reaches its first answer roughly thirty times later, and it brings
about `143` MiB of jars to embed a library whose own wheel budget is `786,432` bytes.

The one thing that would change the answer is a hard requirement of **no Python on the machine**. If
that is your constraint, read [GraalPy](#route-2--graalpy-as-a-maven-dependency) and
[a hand-written port](#route-5--a-hand-written-java-port), in that order, and expect the decision to
be difficult.

### The five routes

| Route | Needs Python installed? | JVM artifacts | Status |
|---|---|---|---|
| **`governed-batch` co-process** | **Yes** — CPython 3.9+ with `acronymkit[cli]` | one JSON parser, or none | **Recommended.** Works today, specified, measured. |
| GraalPy as a Maven dependency | No | ~`143` MiB, plus a ~`65` MiB unpack into the user profile | Possible as of the pydantic removal. Costly. Not recommended. |
| Py4J | **Yes** | one small jar | Works, but it is the co-process route with a socket and an unspecified protocol instead of a pipe and a specified one. |
| JPype | **Yes** | — | **Not viable.** No Maven artifact exists, and it inverts control: Python becomes the host. |
| A hand-written Java port | No | none | Largest job, best end state, and the only one that cannot promise identical answers. |

### About the numbers in this document

Every figure below was produced by a command that is shown next to it. Two of them are cited from
`bench/results.json` and are therefore gated by `tools/check_claims.py`; **the rest are not**. They
have not been through a bench runner's `--save`, and they are reported as transcripts rather than as
claims because that is what they are. Re-measure before quoting any of them anywhere the gate
applies.

They also differ in how far you can trust them, and it is worth being explicit about which is which:

* **First-hand and reproducible.** Everything in [route 1](#route-1--the-governed-batch-co-process)
  came from running `examples/java/` on this machine, with the commands shown. Run it yourself.
* **First-hand and not reproducible from this tree.** The GraalPy figures were produced by a spike
  whose Maven projects and dumps lived in a scratch directory that does not survive. The
  byte-identical dumps were re-compared while writing this document and matched; nothing in this
  repository re-runs that.
* **Second-hand.** [`docs/DECISIONS.md`](DECISIONS.md) D-028 is the decision record for this
  question and marks the same GraalPy figures as second-hand for the same reason. It also carries an
  independent JDK 21 re-measurement of the co-process arm — `228.9` ms cold start and `18,022`
  identifiers/sec, medians of five — taken with a different harness from the one in `examples/java/`.
  Read the two together, not as a contradiction: see
  [what it measured here](#what-it-measured-here).

---

## Route 1 — the `governed-batch` co-process

### Why the command exists at all

The cost that decides whether this library is usable from another language is the number of
interpreter starts, not the work inside them. [`docs/DECISIONS.md`](DECISIONS.md) D-025 records the
interleaved measurement: a bare interpreter, one `expand-identifier` invocation, one
`governed-batch` over 2,000 names, and the same 2,000 names as 2,000 invocations —

```
bare interpreter, nothing imported                        50.1 ms
one expand-identifier invocation                         281.0 ms
one governed-batch over 2,000 names                      432.5 ms
the same 2,000 names as 2,000 invocations            562,000    ms   (arithmetic)
```

— a factor of roughly 1,300, of which almost none is the expansion. The answers themselves run at
96,532<!--claim:governed.throughput.identifiers_per_second:,--> identifiers per second in-process on
the schema corpus, and 22,467<!--claim:governed.throughput_novel.identifiers_per_second:,--> on a
corpus of novel tokens. So: **start one process and hold it.** Starting a process per column is the
mistake the command exists to prevent, and it is the only way to get this route badly wrong.

### What it needs on the machine

* A JDK 17 or newer. Nothing exotic; the example targets 17 and runs on 21.
* **A CPython interpreter, 3.9 or newer, with `acronymkit[cli]` installed.** The `cli` extra is not
  optional — it supplies `click`, and without it the `acronymkit` command exits saying so.
* No network at run time, no listening socket, no file the JVM and Python share. The channel is the
  child's own pipes.
* On the JVM side, one JSON parser. `examples/java/` uses `jackson-databind`, which resolves to 3
  jars totalling `2,335,056` bytes. Any JSON library will do; the wire format is JSONL.

Note that installing `acronymkit` installs `pydantic`, and therefore `pydantic_core`, a compiled Rust
extension. That is fine here — this is CPython, which is what that wheel is built for. It matters
only for [route 2](#route-2--graalpy-as-a-maven-dependency). For an air-gapped install see
[`INSTALL.md`](INSTALL.md) and [`OFFLINE.md`](OFFLINE.md).

### What it measured here

`examples/java/` on Windows 11, Maven 3.9.10 on Temurin JDK 17.0.15, CPython 3.13.4, against the
16-row synthetic catalog that ships with the example:

```console
$ cd examples/java && mvn -q clean compile exec:java
cold start, spawn to first answer: 283.6 ms
3,750 names once warm: 108.2 ms, 34,665 names/sec, 28.85 us each
summary line: op=expand records=3,765 failed=0 skipped=0 exit=0
  sent 3,765 identifiers, the co-process answered 3,765: reconciled
```

Repeated runs put the warm rate between `29,981` and `43,423` names/sec and the cold start between
`244.4` and `308.1` ms, including one run on JDK 21 rather than 17 that landed inside both ranges.
**Do not carry the warm figure into a capacity plan**, because it is set by the vocabulary and the
names rather than by the pipe. The same Java client, unchanged, pointed at this repository's 68-row
fixture catalog and its harder 40-name corpus:

```console
$ mvn -q compile exec:java "-Dexec.args=..\..\tests\fixtures\governed ..\..\tests\fixtures\governed\corpus_sample.txt 94"
3,760 names once warm: 315.6 ms, 11,913 names/sec, 83.94 us each
```

A factor of three from changing nothing on the JVM side. The in-process figures cited above move by
about four between the same two kinds of corpus, so this is the library's own behaviour arriving
across a pipe rather than an artefact of the pipe.

Two checks that the example's README records, because a benchmark that flatters itself is worse than
none: repeating a 15-name file 250 times is not what makes it fast (3,750 *distinct* generated names
land in the same band), and the pipe is not the bottleneck (feeding the same 3,760-line file
straight into `governed-batch` from Python, no JVM at all, takes `468`–`489` ms including start-up).

**On the two co-process figures in this repository.** D-028 measured the same route on the same
machine at `228.9` ms and `18,022` identifiers/sec; the run above, on the same fixture catalog and
corpus, says `305.9` ms and `11,913`. The harnesses are not the same job. D-028's counts records off
the pipe; `examples/java/` deserialises every record into typed Java objects — the whole
`IdentifierExpansion` with its per-token list — and asserts the correlation id on each one. **That
difference has not been attributed**, and it should not be waved at: the example's figure is the
conservative one and it is the one that includes work your own client will also do. If per-name cost
matters to you, measure your own deserialisation before concluding anything about the pipe.

### Four things to get right

All four are in `examples/java/src/main/java/com/example/governed/GovernedBatchClient.java` with the
reasoning attached. Summarised, because each one is a bug that survives testing:

1. **Write on a separate thread from the one that reads.** Writing every identifier and then reading
   every answer deadlocks on any batch large enough to fill a pipe buffer: the child blocks writing
   its output and stops reading its input, the parent blocks writing its input and never reaches the
   read that would drain the child. The batch size at which this happens depends on the operating
   system, which is why it passes a unit test and hangs a production run.
2. **Leave `--flush-every` at its default of `1`.** Setting it to `0` buffers the child's standard
   output — faster, and for a co-process reading the pipe as it goes, a hang. Section 7.4 of the
   contract names this exact failure as the reason the default is what it is.
3. **Write standard input as UTF-8, explicitly.** `governed-batch` decodes its input as UTF-8
   whatever the console code page says, so the parent's encoding is entirely the parent's problem. A
   default-charset writer on a Cp1252 Windows JVM corrupts every non-ASCII identifier before it
   reaches the pipe. Reading is safe either way: records are pure ASCII, with everything above
   U+007F `\u`-escaped, and a supplementary character written as a UTF-16 surrogate pair.
4. **Send the JSON object form, not the bare identifier.** The bare form is what a shell pipeline
   uses and it is not safe to generate from arbitrary data: a name beginning `{` is read as a JSON
   record, a name containing a newline cannot be one line, and the bare form is stripped of
   surrounding whitespace where the object form is not. The object form also carries `id`, which
   comes back untouched and lets the client assert the stream has not lost sync.

### Two rules about the answers

**A finding is not a failure.** Under `--op check`, a name that does not conform arrives with
`"ok": true` and `compliant` false inside the result; the process exit status is unaffected.
`ok: false` means the record could not be answered at all. Route on `ok` and on `error_type`, never
on the prose in `error` — the contract says in as many words that `error` is for a person and a port
is free to reword it.

**Reconcile the summary.** `governed-batch` writes exactly one line to standard error after its last
record: `{"op":...,"records":...,"failed":...,"skipped":...}`. It is on standard error so that every
line of standard output is a record. `records + skipped` must equal the lines you sent. Checking it
is the difference between a pipeline that silently lost forty columns and one that says so.

The full envelope is [`docs/notes/governed-json-contract.md`](notes/governed-json-contract.md)
section 7, which is normative. `examples/java/README.md` has a six-line hand-run transcript that
exercises every branch of it.

### What this route does not give you

A process boundary to supervise, and no in-process objects. If the child dies you find out on the
next read, which the example turns into an `IOException` carrying the child's exit status and its
standard error. If you want one governed answer inside a tight loop with no serialisation at all,
this is not that, and neither is anything else here short of a port.

---

## Route 2 — GraalPy as a Maven dependency

GraalVM's Python implementation ships as ordinary Maven coordinates and runs Python inside a JVM
through the Polyglot API. **It now runs `acronymkit.governed`, and it did not before.**

### What was established

A spike on this machine (Temurin JDK 21.0.7, Maven 3.9.10, GraalPy 25.2.4 and 23.1.12) established
four things, each by running it. [`docs/DECISIONS.md`](DECISIONS.md) D-028 is the decision record;
this section is the practitioner's version of it.

* **No GraalVM installation is needed.** A stock Temurin JDK plus two Maven coordinates
  (`org.graalvm.polyglot:polyglot` and `org.graalvm.polyglot:python-community`) is the whole setup.
  For a locked-down box that is the single most important fact about this route.
* **`acronymkit.governed` imports and runs.** `load_bundle`, `expand_token`, `expand_identifier`,
  `to_physical_name`, `is_compliant`, `normalize` and `to_dict()` all work through the polyglot
  boundary. Against the tree an hour earlier the import failed with
  `ModuleNotFoundError: No module named 'pydantic_core._pydantic_core'`.
* **The answers are byte-identical to CPython.** All five verbs over the 40-line fixture corpus plus
  16 hand-picked edge cases from the contract — empty string, `___`, an emoji-only name, an emoji
  inside a name, leading digits, camelCase, a decomposed accented character — dumped from each
  runtime with `ensure_ascii=True` and compared. Both dumps are `327,754` characters and `cmp`
  reports no difference — re-checked while writing this document, against artifacts that do not live
  in this repository.
* **Every hazard in contract section 8 is a non-issue on this route.** `casefold`, code-point
  counting, code-point string ordering, locale-independent upper-casing: GraalPy implements Python's
  semantics, so there is nothing to re-derive. This is the real argument for GraalPy over a port,
  and it is the argument a port cannot answer.

Two caveats on that. The spike ran **the verbs, not the test suite** — installing `pytest` into a
GraalPy environment needs a native GraalPy standalone downloaded outside Maven, which the spike
declined to fetch. And `models.py` and `policy.py` have changed in this tree since the snapshot the
byte-identical dump was taken against; both are still free of third-party imports, but the identity
result belongs to the earlier snapshot.

### What it costs

```
GraalPy 25.2.4  : 15 jars, 150,117,518 B (143.2 MiB)
GraalPy 23.1.12 : 21 jars, 261,578,656 B (249.5 MiB)
jargraal compiler, needed for the optimizing runtime on a stock JDK: 21,543,968 B (20.5 MiB)
runtime unpack into %LOCALAPPDATA%/org.graalvm.polyglot/python:      65 MB
```

`143.2` MiB of jars to embed a library whose whole wheel budget is `786,432` bytes — about `190`
times the thing being embedded. The unpack is worth flagging separately for a locked-down box:
GraalPy extracts its standard library into a user-writable cache directory on first use, and
`%LOCALAPPDATA%` may be controlled or roamed.

Cold start, measured from Java:

```
GraalPy 25.2.4, interpreted (the JDK-21 default)
  context build 1066.2 ms | python bootstrap 2268.7 ms | import acronymkit 1632.7 ms
  | import acronymkit.governed 1839.2 ms | load_bundle 241.1 ms
  TOTAL cold start to first answer                                     7047.9 ms
GraalPy 23.1.12, optimizing runtime
  TOTAL cold start to first answer                                    13033.8 ms
subprocess co-process, same machine
  spawn + import + bundle load + first record                           225.8 ms
```

A shared `Engine` makes the *second* context nearly free to create (`0.3` ms) but not to populate:
module import still costs about `1.1` s per additional context, because Python module
initialisation re-runs even when parsed code is cached. A service wanting concurrency should build
one context, load the vocabulary once, and guard it.

Steady state, the real `acronymkit.governed`, 2,000 identifiers, `expand_identifier` → `to_dict()`
→ JSON:

```
CPython 3.13, in-process (the ceiling)                        26,708 identifiers/sec
subprocess co-process from Java, steady state                 19,377
GraalPy 23.1.12 optimizing, whole corpus in one crossing      21,482
GraalPy 23.1.12 optimizing, one crossing per name             16,643
GraalPy 25.2.4 interpreted (the JDK-21 default), per name      3,513
```

Read the subprocess row against the last two and the recommendation writes itself. The best in-JVM
number is about `1.1`× the subprocess, and reaching it needs a version-pinned JDK, two experimental
VM flags and an extra `20.5` MiB jar. **In the configuration a consumer gets by default on JDK 21 it
is about `0.18`× the subprocess — five and a half times slower.**

### The version pinning, which is the part that gets missed

The GraalPy version line is pinned to a JDK major version. `25.x` needs JDK 25; on JDK 21 it falls
back to an interpreted Truffle runtime and says so:

```
[engine] WARNING: The polyglot engine uses a fallback runtime that does not support runtime
compilation to native code. ... Your Java runtime '21.0.7+6-LTS' is incompatible with optimized
Truffle runtime version '25.2.4'. The Java runtime version must be greater or equal to JDK '25'
and smaller than JDK '26'.
```

The line for JDK 21 is `23.1.x`, which is **Python 3.10.8** — not the 3.13 the test suite runs on.
Getting the optimizing runtime there needs the `jargraal` compiler jar on
`--upgrade-module-path` plus `-XX:+UnlockExperimentalVMOptions -XX:+EnableJVMCI`, carried by every
launch script you own. So this route couples three version choices that are normally independent:
your JDK, your GraalPy, and the Python language level your vendor's code is tested against.

One more practical wrinkle the spike hit: the advertised `graalpy-maven-plugin` workflow — declare
Python packages in the pom, let Maven install them — **failed here**, because creating a GraalPy
virtual environment requires a native GraalPy standalone binary downloaded from outside Maven.
Pointing GraalPy at a directory of already-installed pure-Python code with the
`python.PythonPath` context option works fine and is what everything above used. For a supply-chain
review this is a real finding: the Maven-native package workflow is not self-contained.

### The `pydantic` story, honestly

`pydantic` v2 ships `pydantic_core`, a compiled Rust extension. That was the blocker, and the
temptation is to state it as absolute. It is not: pydantic-core publishes GraalPy wheels. Running it
under GraalPy needs **four conditions at once**, and on this machine none of the first three held:

| Condition | Here |
|---|---|
| Linux or macOS — there is no Windows GraalPy wheel for pydantic-core | ✗ Windows |
| JDK 22+, so JEP 454 (Foreign Function & Memory) is final | ✗ JDK 21 |
| A GraalPy version matching both the wheel's ABI tag and the JDK major | ✗ `25.x` needs JDK 25 |
| Willingness to depend on GraalPy's own experimental C API layer | — |

On JDK 21 the failure is flat and unconditional, unchanged by `--enable-preview` or
`--enable-native-access=ALL-UNNAMED`:

```
ImportError: JEP 454 is not included on this JDK, this prevents loading native extensions modules.
```

Removing `pydantic` from the governed path removes all four conditions at once, which is why this
route exists at all now. That is the accurate framing: not "pydantic is impossible under GraalPy",
but "pydantic makes this route conditional on a combination most enterprise boxes will not have".

### The scope limit, and it is not small

**`acronymkit.governed` is embeddable. The rest of the library is not.**

```console
$ python -c "…ast sweep of every import in src/acronymkit/governed/*.py, split on sys.stdlib_module_names…"
stdlib : ['__future__', 'collections', 'copy', 'csv', 'dataclasses', 'enum', 'functools',
          'importlib', 'json', 'os', 'pathlib', 're', 'typing']
3rd-pty: []

$ grep -rn "^from pydantic\|^import pydantic" src/acronymkit/
src/acronymkit/cli.py:149:from pydantic import ValidationError
src/acronymkit/config.py:13:from pydantic import BaseModel, ConfigDict, Field, model_validator
src/acronymkit/config.py:14:from pydantic import ValidationError as PydanticValidationError
src/acronymkit/models.py:41:from pydantic import BaseModel, ConfigDict, Field, computed_field
src/acronymkit/serialization.py:56:from pydantic import BaseModel
```

The governed subsystem has **zero third-party imports** — the change [`DECISIONS.md`](DECISIONS.md)
D-027 records. Everything else — the generation engine, the extractor, the disambiguator, `Config`,
the shared models, the serialisation layer and the CLI itself — still goes through `pydantic`, and
`pydantic>=2.0.0` remains a declared runtime dependency of the distribution.

Three consequences a Java team should hold on to:

* If you want governed naming inside your JVM, GraalPy can do it.
* If you want acronym *generation* or *extraction* inside your JVM, GraalPy cannot, on any platform
  where the four conditions above do not all hold — and the co-process route is not merely preferred
  for those, it is the only one.
* The co-process route needs a full CPython install with `pydantic` regardless, because
  `governed-batch` goes through `cli.py`. That is not a cost this route adds; it is the interpreter
  you already had to have.

### When this route would be right

A hard "no Python interpreter on the machine" rule, a JDK you control, no objection to `143` MiB,
and a workload that is long-lived rather than per-request so the multi-second start-up amortises.
That is a narrow window, and it is a genuine one.

---

## Route 3 — Py4J

Both halves exist and both are cheap: `net.sf.py4j:py4j` is on Maven Central, and the Python side is
a single pure-Python wheel with no compiled extension.

It is still the subprocess route wearing different clothes. Py4J is a socket bridge between a JVM
and a **separate CPython process**, so it does not remove the Python requirement — it replaces a
pipe carrying a specified JSONL contract with a socket carrying an unspecified object protocol, and
adds a listening port to the threat surface. Against `governed-batch`, whose envelope is specified
across a `1,575`-line document and whose per-record cost is measured, that trade is negative before
any benchmark. It was not benchmarked, for that reason.

Where it would win: if you needed rich, chatty, stateful interaction with many Python objects rather
than a stream of independent per-name answers. The governed subsystem is deliberately the second
shape — context-free, one name in, one answer out — so it does not need what Py4J is good at.

---

## Route 4 — JPype (not viable)

```console
$ curl -o /dev/null -w "%{http_code}" https://repo1.maven.org/maven2/org/jpype/
404
$ python -c "…pypi.org/pypi/jpype1/json…"
jpype1 1.7.1: 44 wheels, pure-python (py3-none-any)? False
```

No Maven artifact exists, and the wheels are per-CPython-ABI compiled extensions. More decisively,
JPype starts a JVM *from* a Python process: the Python process is the host. Your Maven project would
have to invert control and become a library loaded by a Python entrypoint. That is not the
integration a Maven team is asking for.

---

## Route 5 — a hand-written Java port

The only route with no Python at run time and no large JVM artifact. It is also the largest job and
the only one that cannot promise the same answers.

Sized from the tree today: `src/acronymkit/governed/` is `9,370` lines, of which `7,373` are neither
blank nor a comment, and `5,016` of *those* are docstrings — leaving roughly **`2,400` lines of
executable logic**. Do not read that as the size of the Java, which will be longer; read it as how
much behaviour there is to get right. Against it sits an unusually complete specification:
[`docs/notes/governed-json-contract.md`](notes/governed-json-contract.md) is `1,575` lines covering
seven DTOs with declared field order, six closed enumerations with wire values, eight serialisation
rules, the full algorithm set in dependency order, and the batch envelope. Section 9 ships a golden
replay set — `8` JSONL files, `114` recorded calls with expected payloads — and a test asserts that
no golden file on disk is left undriven.

**The risk is not the line count, it is section 8.** That section catalogues the places where the
obvious Java translation is wrong, and every one of them is silent:

* Java has no `casefold`. `toLowerCase(Locale.ROOT)` leaves `ß` alone where Python folds it to `ss`,
  so `Straße` and `Strasse` are one key on one side and two on the other. For an ASCII-only catalog
  the two agree exactly; beyond that a port implements full folding from Unicode's `CaseFolding.txt`
  or states the restriction.
* `String.compareTo` orders UTF-16 code units; Python orders code points. They disagree whenever a
  supplementary character meets a BMP character above U+DFFF — which decides a `rank_candidates`
  tie-break, and would surface as one differently-resolved collision, months later, in somebody's
  audit trail.
* `Character.isDigit` is narrower than Python's `str.isdigit`, which is true for `²`.
* `Character.isUpperCase` is not Python's `isupper`, which is true for `Ⅰ` (U+2160) although
  `isalpha` is false.
* No single Java predicate equals Python's `str.isspace()`. That set decides three different things,
  including what appears in `unaccounted` and therefore what `is_fully_known` says. The contract
  lists the 29 code points and says to build the set literally.
* `String.toUpperCase()` with a Turkish default locale maps `i` to `İ` and corrupts every token key.
  Use `Locale.ROOT` everywhere, including in the ordinal `st`/`nd`/`rd`/`th` test, where nobody
  thinks to look for it.
* Candidate order is contract: `from_long_to_short` records candidates in the source mapping's
  iteration order, and `ResolutionMode.MOST_COMMON` reads element zero. A `HashMap` would make the
  most-common answer depend on hash seeds.

Honest sizing: **weeks, not days**, and the schedule risk is in that list rather than in the
translation. Note also that `tests/fixtures/` is not in the wheel — `MANIFEST.in` puts it in the
sdist, so a port takes the golden set from a checkout or an sdist, never from an installed package.

The comparison that matters: a port is the high-risk way to a JVM-native answer and GraalPy is the
low-risk way, because GraalPy runs the same algorithm and a port re-derives it.

---

## Choosing

* **Python may be installed on the machine.** Take route 1. It is the supported route, it is
  specified, and `examples/java/` is a working starting point.
* **Python may not be installed, and you need governed naming only.** GraalPy is possible today.
  Budget for `143` MiB, a multi-second start-up per JVM, and a JDK version coupled to the GraalPy
  line. Prefer it over a port unless the artifact size is itself disqualifying.
* **Python may not be installed, and you need generation or extraction too.** Neither embedding
  route covers those — they still import `pydantic`. Escalate the "no Python" constraint rather than
  engineering around it.
* **Identical answers matter more than anything else.** Route 1 and GraalPy both give you the
  reference implementation's answers. A port does not, and no amount of care makes that guarantee
  available to it.
* **You are considering a port anyway.** Start from
  [`docs/notes/governed-json-contract.md`](notes/governed-json-contract.md), build in the order
  section 6 gives, and drive the golden replay set from day one rather than at the end.

---

## What has not been measured

Stated so nobody has to infer it from silence:

* The Python test suite under GraalPy. The byte-identical result covers all five verbs over 56
  identifiers, which is strong evidence and is not the suite.
* Concurrent entry into a shared polyglot `Context`. `GovernedDictionary` is documented as safe to
  share across threads; a `Context` is a separate concern and was not tested.
* Heap and resident memory under embedding.
* Any Linux or macOS behaviour, including whether the GraalPy pydantic-core wheel actually works
  there.
* Py4J of any kind.
* GraalPy native-image and polyglot-isolate packaging — the documented answer to both the start-up
  cost and the JDK pinning, and the thing most likely to change route 2's verdict if anyone revisits
  it.
* Anything about the co-process route under load: many JVM threads, many child processes, restart
  behaviour, or a schema large enough that the identifier list does not fit in memory.

---

## See also

* [`examples/java/`](../examples/java) — the runnable Maven project, with the real output and the
  commands to reproduce it. **No CI job builds it**; its README says how to check it by hand.
* [`docs/notes/governed-json-contract.md`](notes/governed-json-contract.md) — the normative wire
  contract. Section 7 is the batch envelope, section 8 is the JVM hazard list, section 9 is the
  golden replay set.
* [`docs/DECISIONS.md`](DECISIONS.md) — D-025 for why `governed-batch` exists, D-027 for the
  `pydantic` removal that made embedding possible, D-028 for the decision this document implements.
* [`docs/GOVERNED_NAMING.md`](GOVERNED_NAMING.md) — what the subsystem does and where it stops.
* [`docs/QUICKSTART_GOVERNED.md`](QUICKSTART_GOVERNED.md) — the same subsystem end to end from a
  shell, which is the fastest way to understand what your JVM will be receiving.
* [`docs/ENTERPRISE.md`](ENTERPRISE.md), [`docs/OFFLINE.md`](OFFLINE.md),
  [`docs/INSTALL.md`](INSTALL.md) — the answers a review board asks about the Python side.
