# Calling `acronymkit.governed` from Java

A runnable Maven project that expands a schema's physical column names against a governed
vocabulary, by driving `acronymkit governed-batch` as a long-lived co-process.

This is the route [`docs/JAVA_INTEROP.md`](../../docs/JAVA_INTEROP.md) recommends. That document
covers the alternatives — GraalPy as a Maven dependency, Py4J, JPype, a hand-written Java port —
and what each one costs. If you are choosing between them, read that first. If you have already
chosen, copy this directory.

---

## What you need on the machine

| | |
|---|---|
| A JDK | 17 or newer. Built and run here on Temurin 17.0.15 and 21.0.7. |
| Maven | 3.9.10 here. Nothing exotic is used. |
| **A Python interpreter, 3.9 or newer** | This is the requirement that decides whether this route is available to you. |
| `acronymkit[cli]` installed into that interpreter | The `cli` extra is not optional here — it pulls `click`, which is what provides the `acronymkit` command. Installing bare `acronymkit` gives you a command that prints `This command needs the CLI extra`. |
| One Maven dependency | `jackson-databind`, for parsing. 3 jars, 2,335,056 bytes total. Any JSON library would do; the wire format is JSONL. |

Nothing is downloaded at run time and nothing listens on a socket. The JVM starts one child
process and talks to it over its own pipes.

```console
$ python -m pip install "acronymkit[cli]"
$ acronymkit governed-batch --help
```

---

## Run it

```console
$ cd examples/java
$ mvn -q compile exec:java
```

If `acronymkit` is not on `PATH` — it usually is not, when it lives in a virtual environment —
point at it directly:

```console
$ mvn -q compile exec:java -Dacronymkit.command=/path/to/venv/Scripts/acronymkit
```

`mvn -o -q compile` works once the three Jackson jars are in your local repository, which matters
if the build machine has no network.

### The real output

Captured from `mvn -q clean compile exec:java` on Windows 11, Maven 3.9.10 on Temurin JDK 17.0.15,
CPython 3.13.4, against the 16-row catalog in `vocabulary/`. The `acronymkit command` line has been
shortened; nothing else is edited.

```console
$ mvn -q clean compile exec:java -Dacronymkit.command=.../akvenv/Scripts/acronymkit.exe
acronymkit command : .../akvenv/Scripts/acronymkit.exe
vocabulary         : C:\...\acronymkit\examples\java\vocabulary
identifiers        : 15 from identifiers.txt

cold start, spawn to first answer: 283.6 ms

  CUST_ACCT_OPEN_DT    Customer Account OPEN Date         fully governed
  TXN_APPLNT_DOB_DT    Transaction Applicant Dob Date     not in catalog: [DOB]
  PYMT_AM              Payment Amount                     fully governed
  ORIG_BAL_AM          Original Balance Amount            fully governed
  EFF_DT               Effective Date                     fully governed
  CUST_STS_CD          Customer Status Code               fully governed
  SRC_SYS_CD           Source Sys Code                    not in catalog: [SYS]
  TXN_ID               Transaction Identifier             fully governed
  APPLNT_NM            Applicant Name                     fully governed
  ACCT_CLOSE_DT        Account CLOSE Date                 fully governed
  WDGT_FRBL_CD         Wdgt Frbl Code                     not in catalog: [WDGT, FRBL]
  CUST_ACCT_NET_BAL_AM Customer Account NET Balance Amount fully governed
  TXN_RVSL_FLG         Transaction Rvsl Flag              not in catalog: [RVSL]
  PYMT_TERM_CD         Payment TERM Code                  fully governed
  RISK_SCR_VAL         RISK Scr Val                       not in catalog: [SCR, VAL]

tokens this vocabulary does not cover: [DOB, SYS, WDGT, FRBL, RVSL, SCR, VAL]
  Each one is a catalog row somebody has to write, or a column somebody has to rename.
  The library will not invent an expansion for them, which is the point of it.

3,750 names once warm: 108.2 ms, 34,665 names/sec, 28.85 us each

summary line: op=expand records=3,765 failed=0 skipped=0 exit=0
  sent 3,765 identifiers, the co-process answered 3,765: reconciled

--- the same schema under --unknown reject ---
  TXN_APPLNT_DOB_DT    [LexiconError] Token 'DOB' is not in the governed vocabulary and NamingPolicy.unknown is REJECT.
  SRC_SYS_CD           [LexiconError] Token 'SYS' is not in the governed vocabulary and NamingPolicy.unknown is REJECT.
  WDGT_FRBL_CD         [LexiconError] Token 'WDGT' is not in the governed vocabulary and NamingPolicy.unknown is REJECT.
  TXN_RVSL_FLG         [LexiconError] Token 'RVSL' is not in the governed vocabulary and NamingPolicy.unknown is REJECT.
  RISK_SCR_VAL         [LexiconError] Token 'SCR' is not in the governed vocabulary and NamingPolicy.unknown is REJECT.
  5 of 15 records failed; exit status 1
```

Two things in there are the whole product. `RISK_SCR_VAL` expands to `RISK Scr Val` and says
`[SCR, VAL]` are not in the catalog — it did not invent "Score" or "Value", it reported the gap.
And the last block is the same catalog with the opposite stance: `--unknown reject` turns each gap
into a failed record and exit status 1, which is what you want in a schema-review build step. The
default stance is what you want in a reporting pass. Same library, same data, one flag.

---

## What the numbers do and do not mean

`34,665 names/sec` is one run against a **16-row catalog** of short names. Do not carry it into a
capacity plan. Repeated runs on this machine, same corpus, spread 29,981 to 43,423 names/sec, and the
cold start spread 244.4 to 308.1 ms. One of those runs was on Temurin JDK 21.0.7 instead of 17.0.15
and landed inside both ranges, so the JDK is not what is being measured here.

The rate is set by the vocabulary and the names, not by the pipe. Pointed at this repository's own
68-row fixture catalog and its 40-name corpus — a harder workload with more collisions and more
novel tokens — the identical Java client measured 11,913 / 11,555 / 12,163 names/sec over three
runs. That is a factor of three from changing nothing on the JVM side:

```console
$ mvn -q compile exec:java -Dacronymkit.command=... \
      "-Dexec.args=..\..\tests\fixtures\governed ..\..\tests\fixtures\governed\corpus_sample.txt 94"
identifiers        : 40 from ..\..\tests\fixtures\governed\corpus_sample.txt
cold start, spawn to first answer: 305.9 ms
3,760 names once warm: 315.6 ms, 11,913 names/sec, 83.94 us each
```

Two checks worth knowing about, because a benchmark that flatters itself is worse than none:

* **The repetition is not what makes it fast.** The demo repeats a 15-name file 250 times, which
  would be an obvious place for a cache to inflate the number. Re-run against 3,750 *distinct*
  generated names and the rate is 32,914 / 39,152 / 41,067 names/sec — the same band.
* **The pipe is not the bottleneck.** Feeding the same 3,760-line fixture file straight into
  `governed-batch` from Python, no JVM involved at all, takes 468–489 ms including start-up. The
  Java client is in the same territory, so what you are measuring is mostly the expansion work.

None of these figures is in `bench/results.json`, so none of them is gate-backed by
`tools/check_claims.py`, and none may be copied into `README.md` or `docs/`. They are here, in an
example's own README, because they were measured here and you can re-measure them.

---

## The wire format, without Java in the way

Everything the Java code does is visible from a shell. This is `--op check` against `vocabulary/`,
run by hand, and it exercises every branch of section 7 of the contract in six lines:

```console
$ printf 'TXN_ID\n{"id":"col-91","identifier":"CUST_ACCT_OPEN_DT"}\n\nWDGT_CD\n{"id":7,"oops":true}\n{not json\n' \
    | acronymkit governed-batch --dictionary vocabulary --op check
{"line":1,"input":"TXN_ID","ok":true,"result":{"name":"TXN_ID","compliant":true,"reasons":[...],"ends_in_class_word":true,"class_word":"Identifier"}}
{"line":2,"id":"col-91","input":"CUST_ACCT_OPEN_DT","ok":true,"result":{...,"compliant":true,...}}
{"line":4,"input":"WDGT_CD","ok":true,"result":{"name":"WDGT_CD","compliant":false,"reasons":[{"token":"WDGT","verdict":"fail","code":"unapproved_abbrev",...}],...}}
{"line":5,"id":7,"input":"{\"id\":7,\"oops\":true}","ok":false,"error":"a JSON record must carry a string 'identifier'; it is absent. ...","error_type":"InputError"}
{"line":6,"input":"{not json","ok":false,"error":"line is not valid JSON: Expecting property name enclosed in double quotes: line 1 column 2 (char 1)","error_type":"InputError"}
{"op":"check","records":5,"failed":2,"skipped":1}     # <- standard error
$ echo $?
1
```

Read off it:

* Line 3 was blank. It produced **no record**, `skipped` counted it, and the line numbers jump from
  2 to 4 — so `line` stays a usable coordinate into your file.
* `WDGT_CD` is **not compliant** and arrives with `"ok": true`. A finding is not a failure. The
  exit status of 1 comes from the two `InputError` records, not from the non-compliant name.
* The summary is the only line on **standard error**, so every line of standard output is a record
  and you can parse the stream without knowing to skip a header.

The full specification is [`docs/notes/governed-json-contract.md`](../../docs/notes/governed-json-contract.md),
section 7.

---

## The files

| | |
|---|---|
| `pom.xml` | One dependency, `jackson-databind`. Targets Java 17. |
| `src/main/java/com/example/governed/GovernedBatchClient.java` | The reusable part. Starts the co-process, streams identifiers in, parses records out, reconciles the summary. |
| `.../BatchRecord.java` | The envelope: `line`, `id`, `input`, `ok`, and either `result` or `error`/`error_type`. |
| `.../IdentifierExpansion.java`, `.../TokenExpansion.java` | The `--op expand` payload, transcribed from section 3 of the contract. |
| `.../Main.java` | The demonstration. Not the reusable part. |
| `vocabulary/` | A 16-row synthetic catalog in the bundle layout `--dictionary` reads from a directory. **Northwind Data Standards is fictional.** Copy the structure, not the content. |
| `identifiers.txt` | A slice of a schema export, one column name per line. |

### Four things `GovernedBatchClient` gets right that a first draft usually does not

1. **It writes on a separate thread.** Write every identifier, then read every answer, and you
   deadlock on any batch large enough to fill a pipe buffer: the child blocks writing its output
   and stops reading its input, the parent blocks writing its input and never reaches the read that
   would drain the child. It survives testing, because the buffer is bigger than a test.
2. **It leaves `--flush-every` at its default of `1`.** Setting it to `0` buffers the child's
   output, which is faster and, for a co-process reading the pipe as it goes, hangs. Section 7.4 of
   the contract names this as the reason the default is what it is.
3. **It writes standard input as UTF-8 explicitly.** `governed-batch` decodes its input as UTF-8
   whatever the console code page says, so the parent's encoding is the parent's problem. A
   default-charset writer on a Cp1252 Windows JVM corrupts every non-ASCII identifier before it
   reaches the pipe. (Reading is safe either way: the records are pure ASCII, with non-ASCII
   `\u`-escaped.)
4. **It sends the JSON object form, not the bare identifier.** The bare form is what a shell
   pipeline uses, but it is not safe to generate from arbitrary data: a name beginning `{` is read
   as a JSON record, a name containing a newline cannot be one line, and the bare form is stripped
   of surrounding whitespace where the object form is not. The object form also carries the `id`
   that lets the client assert the stream has not lost sync — which it does, on every record.

### Diagnostics

A vocabulary that cannot be read does not fail at `start()`. The process starts, exits 2, and the
diagnosis arrives at the first call with the child's own standard error attached:

```console
$ mvn -q compile exec:java -Dacronymkit.command=... -Dexec.args=nosuchvocabulary
[ERROR] ... the co-process stopped after 0 of 1 (exit 2)
[ERROR] Usage: acronymkit governed-batch [OPTIONS] [FILE]
[ERROR] Error: Invalid value for '--dictionary': Path 'nosuchvocabulary' does not exist.
```

---

## CI does not run this

**No continuous integration job builds or runs this example.** It is not in the wheel, not in the
sdist (`MANIFEST.in` does not include `examples/`), and no test imports it. Nothing here can turn
the repository's gates red, and equally nothing will tell you when it has rotted.

Check it by hand, which takes about a minute:

```console
$ cd examples/java
$ mvn -q clean compile exec:java -Dacronymkit.command=<your acronymkit>
```

It is working if the reconciliation line says `reconciled` and the last line reads
`5 of 15 records failed; exit status 1`. Both are assertions about the wire, not about formatting:
the first proves no record was lost, the second proves `--unknown reject` still turns an ungoverned
token into a failed record and a non-zero exit.

The thing most likely to break it is a change to the batch envelope — section 7 of the contract —
because `BatchRecord`, `IdentifierExpansion` and `TokenExpansion` are hand-transcribed from
sections 7.2 and 3 and nothing checks the transcription. The failure mode is quiet: Jackson leaves
a renamed field null rather than complaining, so a field that moved shows up as a null in the
output above, not as an exception. If you change the envelope, change these records.
