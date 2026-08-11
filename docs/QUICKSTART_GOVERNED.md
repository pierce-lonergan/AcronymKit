# Governed naming in five minutes

For somebody who has a data standard in a spreadsheet, a schema in a database and a pipeline in a
language that is not Python. By the end of this page you will have expanded one column name, run a
whole schema through one process, found out what your catalog is missing, and diffed the answers
against whatever you are using today.

Nothing here needs Python knowledge. Every command below was run, in the order shown, and its output
is pasted as it came back.

```bash
pip install 'acronymkit[cli]'
```

> The transcripts on this page come from a source checkout, where the console script is not
> installed and the command is spelled `python -m acronymkit.cli`. With the package installed it is
> `acronymkit`, which is what the commands say. The shell is bash; on PowerShell, create the input
> files with an editor instead of the `cat > … <<'…'` here-document blocks.

- [1. Your catalog, as it already is](#1-your-catalog-as-it-already-is)
- [2. A whole schema in one process](#2-a-whole-schema-in-one-process)
- [3. What your catalog is missing](#3-what-your-catalog-is-missing)
- [4. The other two thirds of a standard](#4-the-other-two-thirds-of-a-standard)
- [5. Your own acronyms](#5-your-own-acronyms)
- [6. Running beside what you have now](#6-running-beside-what-you-have-now)

## 1. Your catalog, as it already is

A governed catalog is authored long form first: somebody wrote down that *Transaction* is
abbreviated `TXN`. Export that sheet to CSV — two columns, any headers.

```bash
cat > nds_catalog.csv <<'CSV'
long_form,abbreviation
Transaction,TXN
Applicant,APPLNT
Customer,CUST
Account,ACCT
Balance,BAL
Number,NBR
Identifier,ID
Date,DT
Code,CD
Amount,AM
Status,STS
Name,NM
CSV
```

Expand a column name against it:

```bash
acronymkit expand-identifier CUST_ACCT_ID \
    --dictionary nds_catalog.csv \
    --dictionary-format long_to_short_csv \
    --columns long_form,abbreviation
```

```
Identifier:  CUST_ACCT_ID
Phrase:      Customer Account Identifier
Class word:  -
Fully known: yes
Unaccounted: -

TOKEN  EXPANSION   KNOWN  SOURCE    CONF  ENTRY  BEAT
-----  ----------  -----  --------  ----  -----  ----
CUST   Customer    yes    governed  1.00  -      -
ACCT   Account     yes    governed  1.00  -      -
ID     Identifier  yes    governed  1.00  -      -
```

That is the whole first step. Three things in the output are worth knowing now:

- **`SOURCE`** says where each answer came from. `governed` means a catalog row; the other values
  are `approved`, `pinned`, `scored`, `custom` and `passthrough`, and they are how a consumer tells
  a decision from a default without being told.
- **`Fully known`** is the one bit a pipeline gates on. It is false when any token failed to resolve
  *or* the name held a character the splitter could not account for.
- **`Class word`** is empty, and it should not be. That is the first thing a CSV cannot tell this
  library; [step 4](#4-the-other-two-thirds-of-a-standard) fixes it.

### Both flags are required, and neither is bureaucracy

Leave them off and the command refuses rather than guessing:

```bash
acronymkit expand-identifier CUST_ACCT_ID --dictionary nds_catalog.csv
```

```
Usage: acronymkit expand-identifier [OPTIONS] IDENTIFIER
Try 'acronymkit expand-identifier -h' for help.

Error: --dictionary 'nds_catalog.csv' is a CSV, and which way round it reads cannot be decided by looking at it: the same two columns are a valid vocabulary read either way and mean different things. Pass --dictionary-format csv for token,long form, or long_to_short_csv for long form,token, with --columns naming the two headers.
```

Your file read the other way round is also a valid vocabulary, meaning something else entirely, and
there is no conventional header name for "the long form" — a real export says `Long Name`, or
`Business Term`, or `Data Element Name`. Both facts are yours to state, so the tool asks.

### When your catalog disagrees with itself

Read backwards, a long → short catalog stops being one answer per row. Add a second long form that
shortens to `ID`:

```bash
cp nds_catalog.csv collision_demo.csv
echo "Identity,ID" >> collision_demo.csv
acronymkit expand-token ID \
    --dictionary collision_demo.csv \
    --dictionary-format long_to_short_csv \
    --columns long_form,abbreviation
```

```
Token:      ID
Expansion:  Identity
Known:      yes
Source:     scored
Kind:       ambiguous_pinned
Entry:      -
Confidence: 0.50
Class word: -
Beat:       Identifier
```

The ambiguity was always in your catalog; reading it backwards is what surfaced it. `scored` and
`0.50` say a published rule of thumb picked between them and that nobody has ruled, and `Beat` says
what it chose over. Every row that comes back this way is a decision somebody owes — record a pin,
and the answer becomes `pinned` at full confidence. The rules are in
[GOVERNED_NAMING.md](GOVERNED_NAMING.md#when-nobody-pinned-the-collision).

## 2. A whole schema in one process

This is the part that decides whether the library is usable from another language. Answering one
name takes microseconds; starting a Python interpreter takes tens of milliseconds. A pipeline that
invokes the command once per column pays the second cost fifty thousand times and none of the work
is the answer. `governed-batch` pays it once.

Write your column list, one name per line — a `SELECT column_name FROM information_schema.columns`
dump is exactly the right shape:

```bash
cat > columns.txt <<'TXT'
CUST_ACCT_ID
TXN_AM
APPLNT_BRTH_DT
KYC_REVIEW_DT
CUSTOMER_ACCOUNT_ID
customerAccountBalance
TXN_STS_CD
LGCY_ACCT_NUM
TXT
```

One JSON object comes back per line. Here is a single record, pretty-printed so the shape is
readable:

```bash
echo TXN_AM | acronymkit governed-batch \
    --dictionary nds_catalog.csv \
    --dictionary-format long_to_short_csv \
    --columns long_form,abbreviation 2>/dev/null | python -m json.tool
```

```json
{
    "line": 1,
    "input": "TXN_AM",
    "ok": true,
    "result": {
        "identifier": "TXN_AM",
        "phrase": "Transaction Amount",
        "tokens": [
            {
                "raw": "TXN",
                "long": "Transaction",
                "is_known": true,
                "source": "governed",
                "entry_id": null,
                "confidence": 1.0,
                "class_word": null,
                "beat": [],
                "kind": "approved_abbrev"
            },
            {
                "raw": "AM",
                "long": "Amount",
                "is_known": true,
                "source": "governed",
                "entry_id": null,
                "confidence": 1.0,
                "class_word": null,
                "beat": [],
                "kind": "approved_abbrev"
            }
        ],
        "class_word": null,
        "is_fully_known": true,
        "unaccounted": []
    }
}
```

`result` is exactly what the single-name command returns — the batch adds an envelope and no
opinions. The envelope is `line`, `input`, `ok`, and either `result` or the pair `error` /
`error_type`, plus `id` when the input record carried one.

`--op` chooses what happens to each record. `normalize` has the smallest payload, so it makes the
clearest transcript:

```bash
acronymkit governed-batch \
    --dictionary nds_catalog.csv \
    --dictionary-format long_to_short_csv \
    --columns long_form,abbreviation \
    --op normalize < columns.txt
```

```
{"line":1,"input":"CUST_ACCT_ID","ok":true,"result":{"name":"CUST_ACCT_ID","normalized":"CUST_ACCT_ID"}}
{"line":2,"input":"TXN_AM","ok":true,"result":{"name":"TXN_AM","normalized":"TXN_AM"}}
{"line":3,"input":"APPLNT_BRTH_DT","ok":true,"result":{"name":"APPLNT_BRTH_DT","normalized":"APPLNT_BRTH_DT"}}
{"line":4,"input":"KYC_REVIEW_DT","ok":true,"result":{"name":"KYC_REVIEW_DT","normalized":"KYC_REVIEW_DT"}}
{"line":5,"input":"CUSTOMER_ACCOUNT_ID","ok":true,"result":{"name":"CUSTOMER_ACCOUNT_ID","normalized":"CUSTOMER_ACCOUNT_ID"}}
{"line":6,"input":"customerAccountBalance","ok":true,"result":{"name":"customerAccountBalance","normalized":"CUSTOMER_ACCOUNT_BALANCE"}}
{"line":7,"input":"TXN_STS_CD","ok":true,"result":{"name":"TXN_STS_CD","normalized":"TXN_STS_CD"}}
{"line":8,"input":"LGCY_ACCT_NUM","ok":true,"result":{"name":"LGCY_ACCT_NUM","normalized":"LGCY_ACCT_NUM"}}
{"op":"normalize","records":8,"failed":0,"skipped":0}
```

The last line is on **standard error**, not standard output. Every line of stdout is a record, so a
consumer can parse the stream without knowing to skip anything; the summary is there so it can check
it received all eight.

The five operations:

| `--op` | Each record answers | `result` is |
|---|---|---|
| `expand` (default) | what does this column name mean? | `IdentifierExpansion` |
| `physical` | what is the governed name for this logical name? | `PhysicalName` |
| `check` | does this name conform? | `ComplianceResult` |
| `normalize` | what would the standard write instead? | `{name, normalized}` |
| `audit` | everything a governance table needs about this one name | `IdentifierAudit` |

`--op physical` is the reverse direction, so its input lines are logical names ("Customer Account
Open Date") rather than physical ones. The JSON field is still called `identifier`.

### Errors go on the record, not on the run

Losing 49,999 answers to one bad line is a worse outcome than any error message. Send a correlation
key with a record and it comes back untouched; send a broken one and only it fails:

```bash
printf '{"id": "col-7", "identifier": "TXN_STS_CD"}\n{"identifier": 7}\ncustomerAccountBalance\n' \
    | acronymkit governed-batch \
        --dictionary nds_catalog.csv \
        --dictionary-format long_to_short_csv \
        --columns long_form,abbreviation \
        --op normalize
```

```
{"line":1,"id":"col-7","input":"TXN_STS_CD","ok":true,"result":{"name":"TXN_STS_CD","normalized":"TXN_STS_CD"}}
{"line":2,"input":"{\"identifier\": 7}","ok":false,"error":"a JSON record must carry a string 'identifier'; it is int. A line that is not a JSON object is read as the identifier itself.","error_type":"InputError"}
{"line":3,"input":"customerAccountBalance","ok":true,"result":{"name":"customerAccountBalance","normalized":"CUSTOMER_ACCOUNT_BALANCE"}}
{"op":"normalize","records":3,"failed":1,"skipped":0}
```

The process exits `1`, so it is still usable as a gate. What it does **not** exit non-zero for is a
finding: under `--op check`, a name that does not conform is `"ok": true` with `compliant` false
inside the result, because reporting that is the job the command was given.

Three more things worth knowing before you wire this in:

- **Two input shapes.** A line beginning with `{` is a JSON object and must carry a string
  `identifier`; it may also carry `id`, echoed back for correlation. Anything else is the column
  name itself. No physical name begins with a brace, so the two cannot be confused.
- **It streams.** Records are read, answered and written one at a time and nothing accumulates, so a
  fifty-thousand-column schema costs the same memory as a hundred-column one and your reader sees
  the first answer before the last question is asked. `--flush-every 0` buffers, which is faster and
  wrong if you are reading the pipe as it goes; the default flushes every record.
- **The stream is ASCII.** Non-ASCII characters are `\u`-escaped, so a record survives any console
  encoding on the far side. Input is decoded as UTF-8 whatever the console code page says, and a byte
  that is not valid UTF-8 becomes a replacement character on that one record's `input` rather than
  ending the run — so the damage is visible and local.

Finally, **time it on your own hardware** before you design around it:

```bash
time acronymkit governed-batch --dictionary <your standard> < your_columns.txt > /dev/null
time acronymkit expand-identifier ONE_NAME --dictionary <your standard>
```

The first tells you what a whole schema costs. The second, multiplied by the number of columns, tells
you what the alternative costs — and that gap is the entire argument for this command. Measure it
rather than trusting a figure from somebody else's machine.

## 3. What your catalog is missing

The same corpus, reduced to one report. This is the first thing to run against a real schema.

```bash
acronymkit governed-audit \
    --dictionary nds_catalog.csv \
    --dictionary-format long_to_short_csv \
    --columns long_form,abbreviation \
    --suggest < columns.txt
```

```
Governed naming audit
=====================

Coverage
  identifiers      8 (8 distinct)
  fully known      3
  partially known  5
  compliant        0
  not compliant    8
  empty            0

Round trip
  unchanged            6
  governed correction  0
  inconsistent         2

Unknown tokens -- the catalog backlog
  8 distinct, 10 occurrences
  occ  ids  token     example
    2    2  ACCOUNT   CUSTOMER_ACCOUNT_ID
    2    2  CUSTOMER  CUSTOMER_ACCOUNT_ID
    1    1  BALANCE   customerAccountBalance
    1    1  BRTH      APPLNT_BRTH_DT
    1    1  KYC       KYC_REVIEW_DT
    1    1  LGCY      LGCY_ACCT_NUM
    1    1  NUM       LGCY_ACCT_NUM
    1    1  REVIEW    KYC_REVIEW_DT

Compliance findings by reason code
  occ  ids  code                example
   23    8  unapproved_abbrev   CUST_ACCT_ID
    8    8  missing_class_word  CUST_ACCT_ID
    1    1  not_upper_snake     customerAccountBalance

Round-trip inconsistencies
  CUSTOMER_ACCOUNT_ID
    came back as CUST_ACCT_ID
    governed form CUSTOMER_ACCOUNT_ID
  customerAccountBalance
    came back as CUST_ACCT_BAL
    governed form CUSTOMER_ACCOUNT_BALANCE

Catalog suggestions (8)

OCC  IDS  TOKEN     EXAMPLE
---  ---  --------  ----------------------
  2    2  ACCOUNT   CUSTOMER_ACCOUNT_ID
  2    2  CUSTOMER  CUSTOMER_ACCOUNT_ID
  1    1  BALANCE   customerAccountBalance
  1    1  BRTH      APPLNT_BRTH_DT
  1    1  KYC       KYC_REVIEW_DT
  1    1  LGCY      LGCY_ACCT_NUM
  1    1  NUM       LGCY_ACCT_NUM
  1    1  REVIEW    KYC_REVIEW_DT
```

The **unknown-token table is the point**. It is your catalog's backlog in priority order: how often
each token appears, in how many of your identifiers, and one column to go and look at. It turns "our
catalog is incomplete" into a finite list of rows to write.

`compliant 0` is not a disaster, it is a diagnosis. A CSV of long forms and abbreviations says what
words mean. It says nothing about *which tokens may stand in a physical name* or *which of them say
what kind of value a column holds* — so nothing is approved, no name ends in a class word, and every
name fails. Those are two more files, and they are the next step.

Add `--format json` for the same content as a payload, `--limit 0` to stop truncating the ranked
tables, and `--details` to keep one record per distinct name in the JSON.

## 4. The other two thirds of a standard

A standard is not one file. It is a catalog, three allow-lists, a class-word map, a pin sheet
recording collisions somebody has ruled on, and a term glossary. Put them in one directory and pass
the directory:

| File | What it settles |
|---|---|
| `dictionary.json` | what each token means |
| `allowlist.json` | which tokens may stand, as written, in a physical name |
| `class_words.json` | which tokens say what *kind* of value a column holds (`DT` → Date) |
| `ambiguity_pins.json` | the collisions somebody has already ruled on |
| `term_glossary.csv` | which whole logical names are governed terms |

The repository carries a complete worked example of that layout — a fictional catalog, **Northwind
Data Standards**, 68 rows with synthetic ids. Copy it and point at it:

```bash
cp -r /path/to/acronymkit/tests/fixtures/governed ./nds_std
acronymkit governed-audit --dictionary nds_std --suggest < columns.txt
```

```
Governed naming audit
=====================

Coverage
  identifiers      8 (8 distinct)
  fully known      4
  partially known  4
  compliant        4
  not compliant    4
  empty            0

Round trip
  unchanged            5
  governed correction  1
  inconsistent         2

Unknown tokens -- the catalog backlog
  5 distinct, 7 occurrences
  occ  ids  token     governed  example
    2    2  ACCOUNT   ACCT      CUSTOMER_ACCOUNT_ID
    2    2  CUSTOMER  CUST      CUSTOMER_ACCOUNT_ID
    1    1  BALANCE   BAL       customerAccountBalance
    1    1  KYC                 KYC_REVIEW_DT
    1    1  LGCY                LGCY_ACCT_NUM

Compliance findings by reason code
  occ  ids  code                example
    8    4  unapproved_abbrev   KYC_REVIEW_DT
    2    2  missing_class_word  customerAccountBalance
    1    1  not_upper_snake     customerAccountBalance

Round-trip inconsistencies
  CUSTOMER_ACCOUNT_ID
    came back as CUST_ACCT_ID
    governed form CUSTOMER_ACCOUNT_ID
  customerAccountBalance
    came back as CUST_ACCT_BAL
    governed form CUSTOMER_ACCOUNT_BALANCE

Catalog suggestions (5)

OCC  IDS  TOKEN     WRITE  MEANING   EXAMPLE
---  ---  --------  -----  --------  ----------------------
  2    2  ACCOUNT   ACCT   Account   CUSTOMER_ACCOUNT_ID
  2    2  CUSTOMER  CUST   Customer  CUSTOMER_ACCOUNT_ID
  1    1  BALANCE   BAL    Balance   customerAccountBalance
  1    1  KYC       -      -         KYC_REVIEW_DT
  1    1  LGCY      -      -         LGCY_ACCT_NUM
```

Same eight columns, same three directions, and now the report is actionable. Two changes are worth
naming:

- The backlog has a **`governed`** column. `CUSTOMER` is a word this catalog already governs, with an
  approved short form `CUST`, so those columns do not need a catalog row — they need an edit. `KYC`
  and `LGCY` have no wording proposed for them at all, and that is deliberate: a suggestion is a
  request for a decision from whoever owns the catalog, never an answer this library invented.
- **Round-trip inconsistencies** are the names whose expansion, rendered back, is neither the name as
  written nor what `normalize` would write. Three names moved; one of them is the governed correction
  the standard is supposed to make, and only the other two are worth anybody's time.

Each section accepts more than the one file name above — the catalog may be `dictionary`, `catalog`
or `entries`, the allow-lists `allowlist`, `allowlists` or `allow_lists`, the glossary
`term_glossary`, `terms` or `glossary` — so a standard exported by somebody who never read this page
usually loads unchanged. Two files claiming one section is an error rather than a coin toss, and
every section is optional.

## 5. Your own acronyms

Every organisation has terms its catalog has not caught up with. Put them in a file:

```bash
cat > house_acronyms.json <<'JSON'
{
  "KYC": "Know Your Customer",
  "LGCY": {
    "canonical": "Legacy",
    "kind": "approved_abbrev",
    "keep_as_abbrev": true,
    "entry_id": "LOCAL-LGCY-0001",
    "confidence": 0.8
  }
}
JSON
acronymkit expand-identifier KYC_REVIEW_DT --dictionary nds_std --custom house_acronyms.json
```

```
Identifier:  KYC_REVIEW_DT
Phrase:      Know Your Customer REVIEW Date
Class word:  Date
Fully known: yes
Unaccounted: -

TOKEN   EXPANSION           KNOWN  SOURCE    CONF  ENTRY   BEAT
------  ------------------  -----  --------  ----  ------  ----
KYC     Know Your Customer  yes    custom    1.00  -       -
REVIEW  REVIEW              yes    approved  1.00  -       -
DT      Date                yes    governed  1.00  NDS-DT  -
```

`--custom` takes the same file on every command, `governed-batch` and `governed-audit` included, and
it is layered once for the whole run. A value may be a bare long form or a whole entry, and the entry
form is how your overlay carries its own provenance:

```bash
acronymkit expand-token LGCY --dictionary nds_std --custom house_acronyms.json
```

```
Token:      LGCY
Expansion:  Legacy
Known:      yes
Source:     custom
Kind:       approved_abbrev
Entry:      LOCAL-LGCY-0001
Confidence: 0.80
Class word: -
Beat:       -
```

`Source: custom` and `Entry: LOCAL-LGCY-0001` are the payoff: a downstream consumer can tell "the
standard says so" from "a project said so, at eight tenths" without being told. Use an id prefix of
your own so the distinction is legible at a glance.

`REVIEW` staying upper case in the phrase above is not a bug — it is an allow-listed token, which
means it is the governed physical form, and re-casing it would be correcting the standard.

## 6. Running beside what you have now

Nobody sane cuts over without a diff. Run both implementations over the same column list, reduce
each to two columns, and compare. `legacy.tsv` below is yours to produce — the same `name<TAB>answer`
pairs, out of whatever you run today.

```bash
cat > to_tsv.py <<'PY'
"""Reduce a governed-batch record stream to two tab-separated columns."""
import json
import sys

for line in sys.stdin:
    record = json.loads(line)
    result = record["result"] if record["ok"] else {}
    answer = result.get("normalized") or result.get("physical") or result.get("phrase")
    print(record["input"], answer or f"ERROR: {record.get('error', '')}", sep="\t")
PY

acronymkit governed-batch --dictionary nds_std --op normalize < columns.txt 2>/dev/null \
    | python to_tsv.py > acronymkit.tsv
diff legacy.tsv acronymkit.tsv
```

```
5,6c5,6
< CUSTOMER_ACCOUNT_ID	CUST_ACCT_ID
< customerAccountBalance	CUST_ACCT_BAL
---
> CUSTOMER_ACCOUNT_ID	CUSTOMER_ACCOUNT_ID
> customerAccountBalance	CUSTOMER_ACCOUNT_BALANCE
```

Six of the eight names agree, and the two that do not are a real difference of opinion rather than a
bug in either tool:

- the incumbent rewrites `CUSTOMER_ACCOUNT_ID` to `CUST_ACCT_ID`, abbreviating words that were
  spelled out;
- `normalize` does not, because it applies only corrections the catalog can justify for the token in
  front of it, and it never appends or re-abbreviates on its own account.

Both behaviours are defensible and the difference is a decision your governance function should make
rather than a tool should. The useful part is that the audit already told you about both names, in
its round-trip section — the diff and the report agree with each other, which is what you want from a
second opinion.

Three things to do with that diff:

1. **Start with `--op normalize`**, which is the narrowest comparison: one string in, one string out,
   no schema to align. Move to `--op check` once the names agree, because that compares *reasons* and
   is where an incumbent usually turns out to be enforcing a rule nobody wrote down.
2. **Run both for a while.** The batch is cheap enough to run on every schema change beside the
   incumbent, and a disagreement log is the only honest input to a cut-over date.
3. **Read the disagreements as catalog work, not tool work.** Most of them will be a token the
   catalog is silent about, and [step 3](#3-what-your-catalog-is-missing) already ranked those.

If the two files come out of tools on different platforms, `diff --strip-trailing-cr` saves an hour
of reading a diff in which every line changed and none of them did.

## Where next

- [docs/GOVERNED_NAMING.md](GOVERNED_NAMING.md) — the full contract: precedence, the four invariants,
  the policies, and an honest limits section.
- [docs/notes/governed-json-contract.md](notes/governed-json-contract.md) — the wire shape of every
  payload on this page, written so a port can be validated against the same golden files.
- [tests/fixtures/governed/README.md](../tests/fixtures/governed/README.md) — the worked standard you
  copied in step 4, and what each of its files is for.
- The Python API, if your pipeline is Python after all:
  `GovernedNamer.from_bundle("nds_std")` binds the vocabulary and policy once and exposes the same
  five verbs with the subject as their only argument.
