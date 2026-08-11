# The governed wire contract

**No JVM artifact exists.** There is no `acronym4j`, no Maven coordinate, no jar, and nothing in
this repository builds one. `README.md` lists a Java port as a roadmap item and that is where it
stands.

This document is the thing that would make writing one *mechanical rather than a guess*: the exact
JSON shape of every governed DTO, the exact behaviour of every algorithm behind those shapes, the
record envelope the batch command puts on a pipe, and the golden replay set a port can be validated
against by making the same calls on the same fixtures and diffing the same payloads. The golden files
are real and are in this repository; the port is not. Nothing here should be read as a claim that a
port works, is planned for a release, or has been tested.

It is written for someone implementing `acronymkit.governed` on the JVM, but every rule in it is
language-agnostic, so it serves equally as the answer to "what exactly does this emit" for a
consumer in any language.

**Reference implementation:** `src/acronymkit/governed/` in this repository. Where this document and
the source disagree, the source is right and this document is a bug.

## Contents

1. [Scope and encoding](#1-scope-and-encoding)
2. [The closed vocabularies](#2-the-closed-vocabularies)
3. [The DTOs](#3-the-dtos)
4. [Serialisation rules](#4-serialisation-rules)
5. [The input files](#5-the-input-files)
6. [The algorithms, in the order a port should build them](#6-the-algorithms-in-the-order-a-port-should-build-them)
7. [The batch envelope](#7-the-batch-envelope)
8. [Unicode and JVM hazards](#8-unicode-and-jvm-hazards)
9. [The golden replay set](#9-the-golden-replay-set)
10. [What is not decided](#10-what-is-not-decided)

## 1. Scope and encoding

| | |
|---|---|
| Covered | The seven DTOs of `acronymkit.governed.models`, the six enums of `acronymkit.governed.enums`, `NamingPolicy`, the fixture file formats under `tests/fixtures/governed/`, and the `governed-batch` record envelope |
| Partly covered | `IdentifierAudit`, from `acronymkit.governed.audit`, because it is what `governed-batch --op audit` puts on the wire. The rest of that module's DTOs — `CorpusAudit`, `UnknownToken`, `FindingTally`, `RoundTripBreak`, `CatalogSuggestion` — are a published surface with no specification here |
| Not covered | `AcronymResult` and the generation-side DTOs, which have their own published contract in [`schemas/acronym-engine-result.schema.json`](../../schemas/acronym-engine-result.schema.json) |
| Encoding | UTF-8 throughout, for both input files and emitted JSON. The one exception is the batch record stream, which is ASCII with `\u` escapes; see [section 7](#7-the-batch-envelope) |
| Emitted JSON | `to_dict()` produces a JSON-compatible mapping; `to_json(indent=None)` produces text |

**There is no JSON Schema for the governed DTOs.** The generation side has one and this side does
not, which is a real gap: a port has nothing machine-readable to validate against, and this document
is the substitute. If a schema is written later it should be generated from, and diffed against,
section 3.

## 2. The closed vocabularies

Every value below is the wire form. A port must accept and emit these exact strings; they are what
appears in an audit record, and a typo in one is indistinguishable from a real value.

Declared in `src/acronymkit/governed/enums.py`.

**`EntryKind`** — what kind of catalog record an entry is.

| Member | Wire value |
|---|---|
| `CLASS_WORD_ABBREV` | `"class_word_abbrev"` |
| `APPROVED_ABBREV` | `"approved_abbrev"` |
| `AMBIGUOUS_PINNED` | `"ambiguous_pinned"` |
| `DOMAIN_PIN` | `"domain_pin"` |
| `PROPER_NOUN_ACRONYM` | `"proper_noun_acronym"` |
| `SHORT_FULL_WORD` | `"short_full_word"` |
| `UNAPPROVED_EXPANSION` | `"unapproved_expansion"` |
| `PASSTHROUGH` | `"passthrough"` |

`PASSTHROUGH` appears only on a `TokenExpansion`, never on a `GovernedEntry` loaded from a catalog.

**`ExpansionSource`** — which resolution rule produced an answer. Declared in strict precedence
order, highest first; the declaration order *is* the algorithm.

| Member | Wire value |
|---|---|
| `CUSTOM` | `"custom"` |
| `PINNED` | `"pinned"` |
| `APPROVED` | `"approved"` |
| `GOVERNED` | `"governed"` |
| `SCORED` | `"scored"` |
| `PASSTHROUGH` | `"passthrough"` |

**`Verdict`** — `PASS` → `"pass"`, `FAIL` → `"fail"`.

**`ComplianceReasonCode`**

| Member | Wire value | Usually paired with |
|---|---|---|
| `CUSTOM_ABBREV` | `"custom_abbrev"` | pass |
| `APPROVED_ABBREV` | `"approved_abbrev"` | pass |
| `COMMON_KEYWORD` | `"common_keyword"` | pass |
| `SHORT_FULL_WORD` | `"short_full_word"` | pass |
| `PROPER_NOUN_ACRONYM` | `"proper_noun_acronym"` | pass |
| `UNAPPROVED_ABBREV` | `"unapproved_abbrev"` | fail |
| `MISSING_CLASS_WORD` | `"missing_class_word"` | fail |
| `NOT_UPPER_SNAKE` | `"not_upper_snake"` | fail |
| `EXCEEDS_MAX_LENGTH` | `"exceeds_max_length"` | fail |
| `EMPTY_NAME` | `"empty_name"` | fail |

The pairing is a convention, not a structural rule: the verdict is carried on the finding and it is
the verdict that decides.

**`UnknownPolicy`** — `PASSTHROUGH_TITLECASE` → `"passthrough_titlecase"`, `NEURAL` → `"neural"`,
`REJECT` → `"reject"`.

**`ResolutionMode`** — `GOVERNED` → `"governed"`, `MOST_COMMON` → `"most_common"`.

All six accept a plain string on input as well as the enum, through the package-wide `coerce`
contract in `acronymkit/enums.py`.

## 3. The DTOs

Declared in `src/acronymkit/governed/models.py`. Every model is frozen and forbids unknown fields.

**Reading these tables.** *Order* is both the declaration order and the emitted key order. *Required*
means the constructor demands it; a required field may still be nullable, which is the distinction
between "you must decide" and "the answer may be nothing". *Default* applies only to optional
fields. Sequence fields are Python tuples and serialise as JSON arrays.

### `GovernedEntry`

One record in a governed vocabulary: a token and what it officially means.

| # | Field | JSON type | Required | Default |
|---|---|---|---|---|
| 1 | `token` | string | yes | |
| 2 | `canonical` | string | yes | |
| 3 | `candidates` | array of string | no | `[]` |
| 4 | `pin` | string or null | no | `null` |
| 5 | `kind` | `EntryKind` | yes | |
| 6 | `keep_as_abbrev` | boolean | no | `false` |
| 7 | `class_word` | string or null | no | `null` |
| 8 | `entry_id` | string or null | no | `null` |
| 9 | `source` | `ExpansionSource` | yes | |
| 10 | `confidence` | number, `0.0 ≤ x ≤ 1.0` | no | `1.0` |
| 11 | `notes` | string or null | no | `null` |

`token` is the upper-cased lookup key. `candidates` is in the source catalog's own order, including
the canonical form; the order is load-bearing twice, because `ResolutionMode.MOST_COMMON` takes
element zero and the audit trail reports the rest as beaten. An absent `pin` reads as "never
ambiguous", never as "collision left unresolved". `notes` is free text and nothing should branch on
it.

### `TokenExpansion`

The unit of the whole subsystem.

| # | Field | JSON type | Required | Default |
|---|---|---|---|---|
| 1 | `raw` | string | yes | |
| 2 | `long` | string | yes | |
| 3 | `is_known` | boolean | yes | |
| 4 | `source` | `ExpansionSource` | yes | |
| 5 | `entry_id` | string or null | **yes**, nullable | |
| 6 | `confidence` | number, `0.0 ≤ x ≤ 1.0` | yes | |
| 7 | `class_word` | string or null | no | `null` |
| 8 | `beat` | array of string | no | `[]` |
| 9 | `kind` | `EntryKind` or null | no | `null` |

`expand_token("ID", …)` against the fixture catalog, verbatim:

```json
{"raw": "ID", "long": "Identifier", "is_known": true, "source": "pinned",
 "entry_id": "NDS-ID", "confidence": 1.0, "class_word": "Identifier",
 "beat": ["Identity", "Identification", "Identities", "Identified",
          "Identifying", "Internal Document", "Idaho"],
 "kind": "ambiguous_pinned"}
```

`raw` is the token exactly as it appeared, before upper-casing or splitting. `long` is `""` for empty
input. A passthrough carries `is_known: false`, `confidence: 0.0`, `entry_id: null` and
`source: "passthrough"` — four fields saying the same thing, deliberately, because a consumer may
read only one.

There is **no `notes` field**, which matters for one case: when `allow_override=false` refuses a
contradicting overlay, the explanation rides on the `GovernedEntry` that `resolve` returns and is not
visible here. A port must reproduce that, gap included, or the two implementations disagree about
what an expansion carries.

### `IdentifierExpansion`

| # | Field | JSON type | Required | Default |
|---|---|---|---|---|
| 1 | `identifier` | string | yes | |
| 2 | `phrase` | string | yes | |
| 3 | `tokens` | array of `TokenExpansion` | yes | |
| 4 | `class_word` | string or null | **yes**, nullable | |
| 5 | `is_fully_known` | boolean | yes | |
| 6 | `unaccounted` | array of string | no | `[]` |

`class_word` comes from the **trailing token only**.

`unaccounted` was **appended** to this model, after `is_fully_known`, with a default of `[]`. It is
appended rather than inserted so the existing numbering stands and a consumer that never heard of it
keeps parsing; it is optional on input for the same reason. It holds every character of `identifier`
that ended up in no token and is not one of the separators the splitter accounts for — one entry per
occurrence, in input order — and [section 6.3](#63-split_identifier-and-split_identifier_parts)
specifies exactly which characters those are. It is written by `expand_identifier` and by nothing
else.

**`is_fully_known` changed meaning, and this is the change most likely to break a port quietly.** It
is now

```
is_fully_known = unaccounted is empty AND every token is_known
```

where it used to be the second conjunct alone. Nothing about the shape of the payload says so: a
port that keeps the old rule emits the same `phrase`, the same `tokens` and the same `class_word`,
and disagrees on one boolean — on inputs a corpus of clean names never contains, which is exactly
when the disagreement will not be noticed. The behaviour it exists to prevent is `TXN_😀_ID`
answering "Transaction Identifier" with `is_fully_known: true`, which is a confident description of
a name nobody wrote.

`true` for an empty token list is still vacuously right, but only when nothing was reported either.
Both cases are real and a port needs both:

```json
{"identifier": "___", "phrase": "", "tokens": [], "class_word": null,
 "is_fully_known": true, "unaccounted": []}

{"identifier": "😀😀", "phrase": "", "tokens": [], "class_word": null,
 "is_fully_known": false, "unaccounted": ["😀", "😀"]}
```

The full payload for a name carrying one unreadable character, verbatim, with the token list elided
to its shape:

```json
{"identifier": "TXN_😀_ID", "phrase": "Transaction Identifier",
 "tokens": [{"raw": "TXN", …}, {"raw": "ID", …}],
 "class_word": "Identifier", "is_fully_known": false, "unaccounted": ["😀"]}
```

**No other DTO carries it**, and the asymmetry is deliberate rather than an omission. `is_compliant`,
`normalize` and `to_physical_name` split with `split_identifier`, which reports nothing, so an
unaccounted character reaches them only as the token boundary it created. In practice it surfaces in
a compliance check as a whole-name `not_upper_snake` finding — the raw name holds a character that
is neither a digit nor a non-lower-case letter — and it is simply absent from the corrected name:

```json
{"name": "TXN_😀_ID", "compliant": false,
 "reasons": [{"token": "TXN", "verdict": "pass", "code": "approved_abbrev", …},
             {"token": "ID",  "verdict": "pass", "code": "approved_abbrev", …},
             {"token": null,  "verdict": "fail", "code": "not_upper_snake",
              "detail": "…", "fix": "TXN_ID"}],
 "ends_in_class_word": true, "class_word": "Identifier"}
```

`normalize("TXN_😀_ID")` is `"TXN_ID"` and `to_physical_name("TXN_😀_ID").physical` is `"TXN_ID"`. A
port must reproduce the asymmetry, not tidy it up: the two directions answer different questions, and
only the forward one is in a position to report what it could not read.

### `PhysicalToken`

| # | Field | JSON type | Required | Default |
|---|---|---|---|---|
| 1 | `word` | string | yes | |
| 2 | `abbrev` | string | yes | |
| 3 | `source` | `ExpansionSource` | yes | |
| 4 | `entry_id` | string or null | **yes**, nullable | |

`source` here is only ever `custom`, `approved`, `governed` or `passthrough`. `pinned` and `scored`
are unreachable: both name a decision about which long form a token means, and the reverse direction
starts from the long form.

### `PhysicalName`

| # | Field | JSON type | Required | Default |
|---|---|---|---|---|
| 1 | `logical` | string | yes | |
| 2 | `physical` | string | yes | |
| 3 | `tokens` | array of `PhysicalToken` | yes | |
| 4 | `term_id` | string or null | no | `null` |
| 5 | `confidence` | number, `0.0 ≤ x ≤ 1.0` | no | `1.0` |
| 6 | `truncated` | boolean | no | `false` |

```json
{"logical": "Customer Account Open Date", "physical": "CUST_ACCT_OPEN_DT",
 "tokens": [{"word": "Customer", "abbrev": "CUST", "source": "approved", "entry_id": "NDS-CUST"},
            {"word": "Account",  "abbrev": "ACCT", "source": "approved", "entry_id": "NDS-ACCT"},
            {"word": "Open",     "abbrev": "OPEN", "source": "approved", "entry_id": null},
            {"word": "Date",     "abbrev": "DT",   "source": "governed", "entry_id": "NDS-DT"}],
 "term_id": "TRM-400001", "confidence": 1.0, "truncated": false}
```

`truncated` is written `false` unconditionally and is deliberately **not** validated to `false`: a
field that cannot hold another value is a constant rather than evidence. A port must emit it, must
always emit `false`, and must not reject `true` on input — the field exists so a consumer can assert
on it. `confidence` is the minimum across the tokens, `0.0` for an empty name.

### `ComplianceReason`

| # | Field | JSON type | Required | Default |
|---|---|---|---|---|
| 1 | `token` | string or null | **yes**, nullable | |
| 2 | `verdict` | `Verdict` | yes | |
| 3 | `code` | `ComplianceReasonCode` | yes | |
| 4 | `detail` | string | yes | |
| 5 | `fix` | string or null | no | `null` |

`token` is `null` for a whole-name finding. **`detail` is prose for a person and is not part of the
contract** — it may be reworded between releases, and a port is not required to reproduce it byte for
byte. `code` is the stable half; filter, count and route on that. Golden-file comparison should
exclude `detail` or compare it advisorily (see [section 9](#9-the-golden-replay-set)). The same rule
covers the batch envelope's `error`, for the same reason.

### `ComplianceResult`

| # | Field | JSON type | Required | Default |
|---|---|---|---|---|
| 1 | `name` | string | yes | |
| 2 | `compliant` | boolean | yes | |
| 3 | `reasons` | array of `ComplianceReason` | yes | |
| 4 | `ends_in_class_word` | boolean | yes | |
| 5 | `class_word` | string or null | **yes**, nullable | |

`reasons` order is fixed: per-token findings in token order, then the whole-name findings in the
order `not_upper_snake`, `missing_class_word`, `exceeds_max_length`. `compliant` is `true` when no
finding carries `"fail"`.

### `NamingPolicy`

Not a result DTO, but it crosses the wire as configuration and `tests/fixtures/governed/policies.json`
stores it in exactly this shape.

| # | Field | JSON type | Default | Constraint |
|---|---|---|---|---|
| 1 | `mode` | `ResolutionMode` | `"governed"` | |
| 2 | `allow_override` | boolean | `true` | |
| 3 | `unknown` | `UnknownPolicy` | `"passthrough_titlecase"` | |
| 4 | `neural_fallback` | boolean | `false` | |
| 5 | `governed_hit_is_final` | boolean | `true` | |
| 6 | `enforce_name_length` | boolean | `false` | |
| 7 | `max_name_length` | integer | `30` | `≥ 1` |
| 8 | `require_trailing_class_word` | boolean | `true` | |
| 9 | `append_class_word_when_missing` | boolean | `true` | |

The four named presets, field by field, are in
[docs/GOVERNED_NAMING.md](../GOVERNED_NAMING.md#policies) and are stored in `policies.json`.

## 4. Serialisation rules

A port that gets the DTO shapes right and these rules wrong will produce documents that parse
equivalently and diff badly. All eight are observable in the reference implementation.

1. **Key order is field declaration order** — the numbering in section 3. Jackson needs
   `@JsonPropertyOrder`; a plain `HashMap` will not do.
2. **Every field is emitted, including nulls.** There is no "omit if absent". `"class_word": null`
   appears in every expansion that has none.
3. **Enums serialise as their string value**, never as a name, an ordinal or an object.
4. **Sequences are JSON arrays.** The Python types are tuples; nothing about that survives
   serialisation.
5. **Floats are emitted as floats.** `confidence` of one renders `1.0`, not `1`. A port using an
   integral type where the value happens to be whole will diff.
6. **`to_json()` with no indent is not minimal JSON.** It uses Python's default separators, so key
   and value are parted by `": "` and members by `", "`:
   `{"raw": "txn", "long": "Transaction", "is_known": true, ...}`. With `indent=n` it is
   `json.dumps` indentation. If a port compares text rather than parsed documents, match this or
   normalise both sides.
7. **Non-ASCII is emitted literally.** `ensure_ascii=False`; no `\uXXXX` escaping. **This rule is
   reversed in the batch record stream**, which escapes so a record survives any console encoding on
   the far side; see [section 7](#7-the-batch-envelope). It is the only place the two disagree, and a
   port has to pick per stream rather than once.
8. **There is no envelope.** No `$schema`, no version field, no wrapper object. A `TokenExpansion` is
   the top-level document. `governed-batch` does wrap each payload, and that wrapper is specified in
   section 7 — but it is a property of the command, not of the DTOs.

## 5. The input files

The fixture corpus under `tests/fixtures/governed/` is the golden input set. It is **not shipped in
the wheel** — `MANIFEST.in` carries only `*.py` out of `tests/` — so a port consumes it from a
repository checkout. Everything in it is synthetic: "Northwind Data Standards" (`NDS`) is a fictional
catalog and the corpus is modelled on the *shape* of a governed schema catalog, not on the contents
of any real one.

A convention that runs through all of them: **a key beginning with `_` is metadata for a person and
must be skipped by a loader.** `_meta`, `_notes`, `_exercises`, and the `_pin` key inside the pin
sheet. The catalog loader drops underscore-prefixed keys from an entry row before construction, so a
comment written next to a row does not fail the file.

### `dictionary.json`

Two layouts are accepted and a port must accept both.

```
[ {entry}, {entry}, ... ]                                   # bare array

{ "_meta": {...},                                           # object form
  "reserved_absent": ["KYC", "WLT", ...],
  "entries": [ {entry}, ... ] }
```

Keys other than `"entries"` are ignored by the loader. In the object form a missing `"entries"` key
is an error. Each element must be a JSON object; a row that is not, or that carries a field the model
does not have, or that omits a required one, is an error naming the row's zero-based position.

Entry objects use the `GovernedEntry` field names from section 3 and omit any field taking its model
default. The fixture carries 68 rows and 8 tokens held out under `reserved_absent` for the
passthrough path.

### `allowlist.json`

```
{ "_meta": {...},
  "consult_order": ["approved_abbreviations", "common_keywords", "short_full_words"],
  "approved_abbreviations": [...],   "common_keywords": [...],   "short_full_words": [...],
  "_notes": {...} }
```

All three arrays are sorted and upper-case. `consult_order` is the order a compliance check must
consult them in, and it decides the reason code for a token that sits in more than one. The fixture
holds 51, 37 and 22 entries respectively.

### `class_words.json`

```
{ "_meta": {...},
  "abbreviations": {"DT": "Date", "CD": "Code", ...},
  "full_words": ["Date", "Code", ...],
  "trailing_token_policy": {...} }
```

The dictionary constructor takes the `abbreviations` sub-object, **not the whole file**. The fixture
has 21 abbreviations and the 21 matching full words. `full_words` is redundant with the values of
`abbreviations` and is there for a reader.

`trailing_token_policy` is currently **consumed by nothing**. It records `default_class_word: "VAL"`,
which is the one setting the implementation needs and has no field for — see
[section 10](#10-what-is-not-decided).

### `ambiguity_pins.json`

A flat map, `token -> {"candidates": [...], "_pin": <candidate or null>}`, with a leading `"_meta"`.
The pin sheet is a cross-check on the catalog rather than a second input: every token in it also has
a `dictionary.json` row, and the two must agree. The fixture pins 15 tokens, two of them (`CTL`,
`REG`) with `"_pin": null` for a collision governance has deliberately not ruled on.

### `policies.json`

```
{ "_meta": {...},
  "policies": {"governed_default": {<the 9 NamingPolicy fields>}, ...},
  "notes": {"governed_default": "...", ...} }
```

Commentary is kept in a sibling object rather than inside the policy objects, because the model
forbids unknown fields and `NamingPolicy(**data["policies"][name])` has to work. All four preset
objects match what the named constructors produce, field for field.

### `custom_overlay.json`

```
{ "_meta": {...},
  "layer_order": ["house_style", "project_local"],
  "layers": {"house_style": {token: <string or entry object>}, ...},
  "_exercises": {...} }
```

Layers are applied in `layer_order` and the last one wins on any token both mention. Overlay entry
objects carry `source: "custom"` and `LOCAL-*` entry ids, never `NDS-`, so provenance shows at a
glance that an answer did not come from the catalog.

**One trap worth carrying into a port.** A value that is an entry *object* parses as a map, and the
reference implementation's overlay index treats any non-`GovernedEntry` value as a long form and
stringifies it — so a JSON-loaded overlay produces an expansion whose long form is the printed form
of a map. The caller must construct the entry before layering; `tests/test_governed.py`'s
`_overlay_values` is the two-line conversion, and every consumer of this file needs it. A port has a
choice: reproduce the behaviour, or accept a map and construct the entry itself. Whichever it picks,
it should say so, because the two disagree on this file.

### `term_glossary.csv`

Eight columns, header row present, UTF-8:

```
logical_name,physical_name,term_id,class_word,domain,confidentiality,source,confidence
```

The first seven are the specified ones in the specified order; `confidence` is an eighth, because
placeholder term ids in the `TRM-9000xx` block must carry a confidence below one and the seven-column
form has nowhere to record it. Read by column name and the addition is invisible. The fixture has 36
rows. The term index a dictionary is built with is `logical_name -> term_id`.

### `corpus_sample.txt`

One identifier per line, no comments, no blank lines. The fixture has 40 lines, the shortest 6
characters and the longest 94.

## 6. The algorithms, in the order a port should build them

This is the part that cannot be inferred from the JSON. Build in this order; each step depends only
on the ones above it.

### 6.1 Key normalisation

Three functions, in `dictionary.py`, and everything downstream keys on them.

| | Rule |
|---|---|
| **token key** | `token.strip().upper()`, or `""` when the token is absent or empty |
| **phrase key** | whitespace-collapsed, then **case-folded**: `" ".join(text.split()).casefold()` |
| **allow-list key** | the token key, with blanks dropped |

"Whitespace-collapsed" means split on runs of Unicode whitespace and rejoin with a single space,
which also strips the ends. Case folding is *not* lower-casing; see
[section 8](#8-unicode-and-jvm-hazards), which also names the exact whitespace set "Unicode
whitespace" means here.

### 6.2 Index construction

Built once, never mutated. An instance is safe to share across threads.

- **Rows.** Keyed by token key; a later row with the same key replaces an earlier one; the stored
  entry's `token` is rewritten to the key. A row whose token key is empty is skipped.
- **Overlay.** Keyed by token key. A string value becomes an entry with `kind: "approved_abbrev"`,
  `source: "custom"` and every other field defaulted. An entry value is copied with `token` set to
  the key and `source` forced to `"custom"`. A blank long form is dropped rather than stored —
  applying it would produce a confident answer that is not an answer.
- **Allow-lists.** Three sets of token keys.
- **Class words.** Two maps: abbreviation key → spelled-out form, and spelled-out-form key →
  spelled-out form. The second is why a name ending in `DATE` is recognised like one ending in `DT`.
  Entries with a blank key or blank word are skipped; the second map keeps the *first* spelling seen
  for a given key.
- **Term index.** Phrase key → term id, skipping blank keys and falsy ids.
- **Reverse index.** Long-form phrase key → entry, over catalog rows; a second, separate reverse
  index over the overlay, consulted first.

**Reverse-index tie-break.** Every entry claims its `canonical` and every member of its `candidates`.
For each contested long form, order the claims by `(rank, token length, token)` and take the
smallest, where `rank` is `0` when the long form is that entry's `canonical` and `1` when it is only
a candidate. Token length is in code points; the final comparison is on the token string. All three
rules are needed: the fixture's `Number` is claimed by `NBR` and `NUM`, which tie on the first two.

### 6.3 `split_identifier` and `split_identifier_parts`

`tokenizer.py`. Pure; no dictionary, no configuration, never raises.

Two public functions over one set of rules. `split_identifier(s)` returns the tokens.
`split_identifier_parts(s)` returns the same tokens **and** the characters that ended up in none of
them, as `IdentifierParts(tokens, unaccounted)`. A port needs both: the second is what
`expand_identifier` calls and what the counting guarantee below is stated in terms of, and
`split_identifier(s) == split_identifier_parts(s).tokens` holds for every `s`.

**Character classes.** Six, not five. Classify each character into exactly one, testing **in this
order**:

```
isupper                             -> UPPER
islower                             -> LOWER
isdigit                             -> DIGIT
isalpha                             -> CASELESS
in ACCOUNTED_SEPARATORS or isspace  -> SEPARATOR
otherwise                           -> UNACCOUNTED
```

`CASELESS` is a letter with no case of its own — CJK, Hebrew, Devanagari. The last two classes behave
identically as boundaries: both close the current token, and neither can ever be part of one, because
a token is about to be used as a lookup key and no catalog entry contains punctuation. What separates
them is that a `SEPARATOR` vanishes and an `UNACCOUNTED` character is **reported**.

#### The accounted set, exactly

A port that draws this line anywhere else produces different `unaccounted` arrays on the same input,
which is a divergence no amount of clean-corpus testing will surface. The set is published as
`acronymkit.governed.tokenizer.ACCOUNTED_SEPARATORS` and pinned by
`tests/test_governed_edge_cases.py::test_the_accounted_separators_are_the_published_ones`.

**Nine punctuation characters**, and there is no tenth:

```
_   -   .   /            the four separators a physical name is built out of
"   '   `   [   ]        the identifier quoting of the four common SQL dialects
```

The first four are structure — a caller who wrote `TXN_ID` does not need to be told it contained an
underscore. The other five are so that a name that made a round trip through a catalog query reads as
the bare one: `"TXN_ID"`, `[TXN_ID]` and a backtick-quoted name all tokenise to `("TXN", "ID")` with
nothing reported, which is what keeps a schema read out of `information_schema` from arriving with
every row flagged.

**Plus every Unicode whitespace character**, meaning every character Python's `str.isspace()` accepts.
That is not listable in the constant and it is not the same set as any single Java predicate, so it is
written out here. In CPython 3.13 it is these 29 code points — the 25 with the Unicode `White_Space`
property, plus the four ASCII information separators:

```
U+0009 U+000A U+000B U+000C U+000D   U+001C U+001D U+001E U+001F   U+0020
U+0085 U+00A0 U+1680
U+2000 U+2001 U+2002 U+2003 U+2004 U+2005 U+2006 U+2007 U+2008 U+2009 U+200A
U+2028 U+2029 U+202F U+205F U+3000
```

Note what is *not* in it. U+200B ZERO WIDTH SPACE, U+180E MONGOLIAN VOWEL SEPARATOR and U+FEFF are
format characters rather than whitespace to Python, so each of them is **reported as unaccounted** —
which is the right answer for a zero-width character a spreadsheet left in a column name, and is the
opposite of what "it looks like a space" would give. `TXN<U+200B>ID` tokenises to `("TXN", "ID")`
with one entry on `unaccounted`; `TXN<U+00A0>ID`, a no-break space, is the same two tokens with
nothing reported.
[Section 8](#8-unicode-and-jvm-hazards) lists the three Java predicates a port will reach for here and
what each of them gets wrong.

**Everything else is unaccounted.** An emoji pasted out of a spreadsheet, a currency sign, a stray
comma from a hand-edited CSV of column names, a combining accent left behind by a decomposed Unicode
spelling, a control character from a bad export. Each occurrence is appended to `unaccounted` in input
order, one entry per occurrence — the list is not de-duplicated. Within ASCII that is 47 characters:
the 23 printable ones `!#$%&()*+,:;<=>?@\^{|}~`, and the 24 control characters that are not
whitespace (U+0000–U+0008, U+000E–U+001B, U+007F).

An unaccounted character is deliberately **not** made into a token of its own. A token is a lookup
key: it goes to the catalog and comes back `is_known=false` when the catalog is silent, and that miss
is a row somebody owes. "This name contains a character I could not read" is a different fact, no
catalog row can settle it, and a token list is also what `normalize` rebuilds a corrected name out of.

#### The counting guarantee, formally

For every input string `s` and every character `c`, with `T` the concatenation of the returned tokens
and `U` the `unaccounted` list:

```
c ∈ ACCOUNTED_SEPARATORS  or  c is Unicode whitespace
    =>  count(c, T) + count(c, U) == 0

otherwise
    =>  count(c, T) + count(c, U) == count(c, s)
```

Nothing is invented, nothing is duplicated, and nothing leaves without being either kept or reported.
It is stated as counts rather than as a rejoin because the token list does not record *where* the
separators stood, so `s` is not reconstructible character by character; the honest guarantee is the
one that can be checked. Two corollaries a port should assert directly, both property-tested here
over arbitrary text:

- no member of `unaccounted` is a letter or a digit — anything that could have been part of a word is
  in a token instead;
- the two functions return identical tokens.

The tests are `tests/test_governed_edge_cases.py::test_nothing_leaves_without_being_kept_or_reported`,
`::test_the_reported_characters_are_never_ones_that_could_have_been_a_token` and
`::test_the_two_splitters_return_the_same_tokens`.

#### Boundaries

Then walk the string. A `SEPARATOR` or an `UNACCOUNTED` character closes the current token, and the
second is also appended to `unaccounted`. Otherwise, when a token is already open, open a new one if:

```
current is DIGIT     and previous is a letter class          -> boundary
previous is DIGIT    and current is a letter class           -> boundary, unless the ordinal
                                                                exception below fires
current is UPPER     and previous is LOWER                   -> boundary
current is UPPER     and previous is UPPER and next is LOWER -> boundary
otherwise                                                    -> no boundary
```

One character of lookahead, used only by the last rule; at end of input the lookahead is
`SEPARATOR`. `CASELESS` takes part in the letter/digit rules and creates no case boundary, so
`ETL<CJK><CJK>Stamp` stays one token.

Tokens come back with their original casing, in input order. Empty input and separator-only input
both yield an empty token list and an empty `unaccounted`; input made only of unaccounted characters
yields an empty token list and reports every one of them.

```
"TXN_APPLNT_DOB_DT"      -> ["TXN", "APPLNT", "DOB", "DT"]
"creditBureauVendorCode" -> ["credit", "Bureau", "Vendor", "Code"]
"ETLTimestamp"           -> ["ETL", "Timestamp"]
"MDMHubID"               -> ["MDM", "Hub", "ID"]
"address2line1"          -> ["address", "2", "line", "1"]
"7Code"                  -> ["7", "Code"]
"nds.risk-model / SCORE" -> ["nds", "risk", "model", "SCORE"]
"1MM"                    -> ["1", "MM"]
'"TXN_ID"'               -> ["TXN", "ID"]              unaccounted []
"[TXN_ID]"               -> ["TXN", "ID"]              unaccounted []
"TXN,ID"                 -> ["TXN", "ID"]              unaccounted [","]
"PAY€AMT"                -> ["PAY", "AMT"]             unaccounted ["€"]
"TXN_😀_ID"              -> ["TXN", "ID"]              unaccounted ["😀"]
"😀😀"                   -> []                         unaccounted ["😀", "😀"]
"CLIÉNT_NM"  NFC         -> ["CLIÉNT", "NM"]           unaccounted []
"CLIE<U+0301>NT_NM"      -> ["CLIE", "NT", "NM"]       unaccounted ["<U+0301>"]
```

The last pair is worth reading twice. The same name in NFC and NFD is two different names to this
splitter, because a combining mark is not a letter and cannot join a token. Nothing here applies NFKC,
case folding or accent stripping — a normalising splitter would return tokens that are not substrings
of the identifier, `raw` would stop showing the token as the schema spelled it, and the counting
guarantee would have nothing left to count. A caller whose source emits decomposed spellings should
normalise upstream, where the change is visible.

#### The ordinal exception

At a **digit→letter** boundary, and nowhere else, the boundary is suppressed when all three hold:

1. the two characters starting at this position, lower-cased, are one of `st`, `nd`, `rd`, `th`;
2. the character after those two is absent, or is not a letter — a digit, a separator or an
   unaccounted character all satisfy this;
3. the two characters are **not** written lowercase-then-uppercase. A capital after a lowercase
   letter is a camelCase boundary, and that rule wins: `1sT` is `("1", "s", "T")`. See below.

So `1ST_TXN_DT` is `("1ST", "TXN", "DT")` rather than `("1", "ST", …)`, which asked the catalog about
`ST` — a token no standard carries in that position — and produced the phrase "1 St".

The suffix set is **closed** and there is no morphology behind it. It is **English-only** and says so:
a catalog whose ordinals are written `1ER` or `1E` gets the letter/digit boundary and nothing else.
Condition 2 is what keeps the rule from inventing a break: `1STATE_CD` is `("1", "STATE", "CD")` and
`1STDay` is `("1", "ST", "Day")`, because there the letters run on past the suffix and nothing says
where the writer meant the word to break. The rule does not reach across a separator either, so
`ADDR_1_ST` keeps the two tokens somebody wrote separately. Matching is case-insensitive on both
letters, and the digits may be any run: `21ST_TXN_DT` is `("21ST", "TXN", "DT")`.

```
"1ST_TXN_DT"   -> ["1ST", "TXN", "DT"]      "1STATE_CD" -> ["1", "STATE", "CD"]
"2ND_QTR_DT"   -> ["2ND", "QTR", "DT"]      "1STDay"    -> ["1", "ST", "Day"]
"3RD_PARTY_ID" -> ["3RD", "PARTY", "ID"]    "ADDR_1_ST" -> ["ADDR", "1", "ST"]
"4TH_QTR_DT"   -> ["4TH", "QTR", "DT"]      "1MM"       -> ["1", "MM"]
"21ST_TXN_DT"  -> ["21ST", "TXN", "DT"]     "7Code"     -> ["7", "Code"]
"1st_txn_dt"   -> ["1st", "txn", "dt"]      "ISO8601Date" -> ["ISO", "8601", "Date"]
"ADDR1ST"      -> ["ADDR", "1ST"]
```

The ordinal is a token, not an exemption: unless the vocabulary has a row or an allow-list entry for
`1ST`, it passes through and `is_fully_known` is `false`. That is the point of the rule — the miss is
reported as `1ST`, which is a row somebody can write, rather than as `ST`, which is a word the column
does not contain. It also means the token now bears a letter, so a compliance check produces a finding
for it where the old split produced none for the bare `1`; see
[section 10](#10-what-is-not-decided), item 4.

#### `1sT` is `("1", "s", "T")`, and condition 3 is why

Condition 3 is the camelCase rule outranking the ordinal rule, and it is the only place in the
splitter where one rule is written down as beating another, so it is worth the paragraph:

```
"1ST" -> ["1ST"]     "1st" -> ["1st"]     "1St" -> ["1St"]     "1sT" -> ["1", "s", "T"]
```

The ordinal rule exists because `1ST` is one *word*. A capital after a lowercase letter is the writer
saying a new word starts there — everywhere else in this module that signal is what a boundary is —
so a suffix written `sT` is not one word and the rule has no business joining it to the digits.

**Two other answers are available and both are worse.** Applying the ordinal rule and then letting
the camelCase rule cut inside the token it just formed gives `("1s", "T")`; that is what the reference
implementation used to answer, and the token `1s` does not survive `str.upper` — `"1S"` splits back
into `("1", "S")`, which made `normalize` non-idempotent on any name containing one. Reading the rule
as "the suffix is welded to its digits" and stopping there gives `("1sT",)`, which is what a port
implementing it "cleanly" would answer; that keeps the token stable but reads a case change as no
boundary at all, which no other rule here does.

Nobody writes an ordinal as `1sT`, so this is contract about the *order the rules run in* rather than
about this string. Pinned by
`tests/test_governed_perf.py::test_a_lower_then_upper_ordinal_suffix_is_not_an_ordinal` and
`tests/test_governed_edge_cases.py::test_a_lower_then_upper_ordinal_suffix_is_not_one`; the property
that made the old answer untenable is
`::test_an_ascii_token_upper_cased_splits_back_to_exactly_itself`, which asserts over arbitrary ASCII
text that a token upper-cased splits back to exactly itself. A port whose `normalize` is expected to
be idempotent needs that property too, however it spells the rule.

#### `strip_qualifier`

Also exported, also pure, and applied by no verb. Returns the last `.`-separated segment of the input
whose content is not entirely whitespace, verbatim and with no normalisation. `None` and `""` return
`""`; an input with no such segment comes back **unchanged** rather than empty, because losing a whole
name to a punctuation accident is the failure this package exists to avoid.

```
"db.schema.TXN_ID" -> "TXN_ID"     "TXN_ID." -> "TXN_ID"     "..." -> "..."
"[db].[TXN_ID]"    -> "[TXN_ID]"   "TXN_ID"  -> "TXN_ID"     null  -> ""
```

Nothing calls it on the caller's behalf, and a port should keep it that way: `.` is an ordinary
separator in a physical name, `nds.risk-model` is one name with a dot in it, and deciding which of the
two a string is would be guessing about somebody's naming convention.

### 6.4 The digit rejoin, second pass

`1MM` must split — nothing in the string distinguishes it from `7Code` — and some catalogs carry it
as one token. The repair is a dictionary-aware second pass over the splitter's output, not a rule
inside the splitter, so the splitter stays a function of its input:

```
i = 0
while i < len(tokens):
    if tokens[i] is all digits and i + 1 < len(tokens):
        joined = tokens[i] + tokens[i + 1]
        if dictionary.resolve(joined, policy) is not None:
            emit joined; i += 2; continue
    emit tokens[i]; i += 1
```

The pass runs in `expand_identifier`, `to_physical_name`, `is_compliant` and `normalize` — all four,
identically. "All digits" is the Unicode digit test, not an ASCII one.

Consequence a port must reproduce: the token sequence no longer records whether a separator stood
between two tokens, so `TXN_1_MM` and `TXN_1MM` both yield `1MM`.

### 6.5 `canonical_form_score` and `rank_candidates`

`scoring.py`. Pure, context-free, deterministic. **Lower wins.**

Collapse the candidate's whitespace first, so formatting cannot move a score. Then:

| key | penalty | condition |
|---|---|---|
| `us_state` | `100.0` | the token, stripped, is exactly 2 characters, is alphabetic, and the whole lower-cased candidate is one of the 50 US state names |
| `gerund` | `50.0` | lower-cased candidate ends `ing` |
| `adverb` | `40.0` | ends `ly` |
| `past_tense` | `30.0` | ends `ed`, and the **final word**, lower-cased, is not in `PAST_TENSE_NOUNS` |
| `plural` | `20.0` | ends `s`, and the final word is not in `SINGULAR_LOOKING_PLURALS` |
| `multi_word` | `10.0` | the collapsed candidate contains a space |
| `length` | `1.0` per character | code points of the collapsed candidate |
| `total` | | the sum of the seven above, in that order |

The exemption sets are tested against the candidate's **final word**, not the whole string, so
`Balance Secured` is exempt exactly as `Secured` is.

```
PAST_TENSE_NOUNS = {expedited, approved, expired, defaulted, secured, ranked, sealed, shared}
SINGULAR_LOOKING_PLURALS = {address, savings, securities, stats, ops, alias,
                            status, process, access, business, class}
US_STATE_NAMES = the 50 states, lower-cased, two of them containing a space
```

All three sets are lower-cased and compared against lower-cased text. The state set excludes
territories, the District of Columbia and the postal codes themselves.

`score_breakdown` returns all eight keys in the table's order, every rule present whether or not it
fired, and the seven rule values summing exactly to `total`.

**`rank_candidates(candidates, token)`** is what the resolver calls:

1. drop candidates that are empty or whitespace-only — they score zero, and an empty cell in a
   spreadsheet-sourced catalog would otherwise win every collision it appeared in;
2. collapse exact duplicates;
3. sort by `(score, candidate string)`, ascending.

The tie-break on the candidate text is what makes the order **total**, so a collision cannot resolve
one way today and another tomorrow because a catalog file was re-sorted. The winner is element zero;
the remainder is what `TokenExpansion.beat` records.

### 6.6 Resolution: the precedence chain

`GovernedDictionary.lookup(token)` returns the overlay entry if there is one, else the catalog row,
else nothing. No pin, no score, no allow-list; it always reports the overlay, because the row exists
whatever a policy thinks of it.

`GovernedDictionary.resolve(token, policy)` is the chain:

```
key = token key; if empty -> nothing
overlay = overlay index[key];  row = catalog rows[key]

if overlay exists and (row is absent or policy.allow_override):
    return overlay                                              # rule 1

note = none
if overlay exists and row exists:                               # the demotion
    governed = governed_choice(row, key)
    if phrase_key(overlay.canonical) == phrase_key(governed):
        return overlay                                          # a restatement is not a contradiction
    note = the demotion note

if row exists:
    return resolved(row, key, policy, note)                     # rules 2, 3, 5
return allow_list_entry(key)                                    # rule 4, or nothing -> rule 6
```

**`governed_choice(row, token)`** — what the catalog says, ignoring policy. This is what an overlay
is measured against, and it is deliberately independent of the policy, because whether a caller may
overrule the standard is a separate question from what the standard said:

```
row.pin if set, else rank_candidates(row.candidates, token)[0] if more than one candidate,
else row.canonical
```

**`resolved(row, token, policy, note)`** returns the row with three fields rewritten — `canonical`
becomes the chosen long form, `source` becomes the rule that chose it, `notes` gains a sentence when
something happened a reviewer would otherwise have to reconstruct. Everything else is carried
through:

```
if policy.mode == MOST_COMMON:
    winner = row.candidates[0] if any else row.canonical
    source = APPROVED if (row.keep_as_abbrev and winner == row.canonical) else GOVERNED
    if winner != governed_choice(row, token): append the mode note
elif row.pin:                     winner = row.pin;                     source = PINNED
elif len(row.candidates) > 1:     winner = rank_candidates(...)[0];     source = SCORED
else:                             winner = row.canonical
                                  source = APPROVED if row.keep_as_abbrev else GOVERNED
if note: append it
```

Notes are joined with a single space, existing text first.

**`allow_list_entry(key)`** synthesises rule 4:

```
if key in approved_abbreviations or key in common_keywords: kind = APPROVED_ABBREV
elif key in short_full_words:                               kind = SHORT_FULL_WORD
else:                                                       return nothing
GovernedEntry(token=key, canonical=key, kind=kind, keep_as_abbrev=true,
              class_word=class_word_for(key), source=APPROVED, notes=the allow-list note)
```

The canonical is the **upper-cased token, not Title Cased**. An approved token is the governed
physical form and re-casing it would be correcting the standard.

**`is_approved(token)`** — true when the token is in the overlay, or has a catalog row with
`keep_as_abbrev`, or is in any of the three lists. Note it consults the *catalog rows* directly for
the second test, not `lookup`.

**`class_word_for(token)`** — in order: the `class_word` of whatever `lookup` returns, then the
abbreviation map, then the spelled-out-form map.

**`abbreviate(word)`** — the overlay reverse index, then the catalog reverse index, keyed on the
phrase key.

### 6.7 `expand_token` and `expand_identifier`

```
expand_token(token, dictionary, policy, custom):
    dictionary must not be absent -> configuration error
    layer custom for this call only
    text = token.strip() if token else ""
    if text is empty: return the empty expansion
    return expand(text)
```

**The empty expansion** and **the passthrough expansion are not the same object**, and a port must
keep them distinct:

| field | empty input | unknown token |
|---|---|---|
| `long` | `""` | Title Cased token |
| `class_word` | `null` | whatever `class_word_for` says |
| `kind` | `null` | `"passthrough"` |
| `is_known`, `confidence`, `entry_id`, `source`, `beat` | `false`, `0.0`, `null`, `"passthrough"`, `[]` | same |

`UnknownPolicy.REJECT` is **not** consulted for empty input: that policy is about a token the catalog
does not recognise, and absent input is not a token at all.

**Title case** is `first character upper + the rest lower`. Not the platform's title-casing routine,
which re-capitalises after a digit and would turn `address2line` into `Address2Line`.

**`expand(text)`**: resolve; if nothing, passthrough. Otherwise:

```
long       = entry.canonical                    (already the resolved winner)
is_known   = true
source     = entry.source
entry_id   = entry.entry_id
confidence = entry.confidence
class_word = entry.class_word, or class_word_for(text) when the entry has none
beat       = every candidate not equal to the winner, in declared order
kind       = entry.kind
```

**`expand_identifier`**: split **with `split_identifier_parts`**, rejoin digits, expand each token.
Then

```
phrase          = the non-empty long forms joined with single spaces
class_word      = the last token's class_word, or null when there are no tokens
unaccounted     = the splitter's unaccounted characters, unchanged and in input order
is_fully_known  = unaccounted is empty AND every token is_known
```

The digit rejoin runs over the tokens only and never touches `unaccounted`. `is_fully_known` is
`true` for no tokens *and* nothing reported; see the [`IdentifierExpansion`](#identifierexpansion)
notes in section 3 for why the second conjunct is there and what a port that omits it emits instead.

Failure modes, and there are only two: an absent dictionary is a configuration error; an unknown
token under `REJECT` is a vocabulary error naming the token, and the first such token stops the call.
An unaccounted character is neither. `REJECT` is about a token the catalog does not recognise, and a
character that could not become a token is not a token — it is reported on a returned payload, never
raised.

### 6.8 `to_physical_name`

Split and rejoin the logical name the same way, then render left to right:

```
at position `start`:
  1. if the word is already a governed token, emit it verbatim and advance one word;
  2. else try the longest run of remaining words the reverse index knows, then shorter runs,
     down to the single word; on a hit emit one token for the whole run and advance past it;
  3. else upper-case the single word and advance one.
```

**Step 1, "already governed", is checked first and its signal is that the word is written in
capitals** — and contains at least one letter. Then: a `lookup` hit renders from that entry; failing
that, an `is_approved` hit renders the word as its own abbreviation with no entry id and full
confidence; failing both, fall through to step 2.

The capitalisation signal is deliberately narrow. Matching any word that happens to equal a token
would read the "in" of "Loan in Default" as the `IN` indicator class word. A word a writer
capitalised is a word they meant as an abbreviation; a word in title case is a word.

**Step 2's provenance:** `custom` when the entry's source is custom, else `approved` when
`keep_as_abbrev`, else `governed`. Under `allow_override=false`, an overlay entry found by the
reverse index is replaced by what the base dictionary would have said, when the base says anything.

**Step 2's window may be capped at the wordiest long form the reverse indexes hold**, rather than
starting from the end of the name. A run longer than the longest key cannot match anything, so the
cap cannot change a single answer; it turns a scan that is quadratic in the words of the name into
one linear in the name and bounded by the vocabulary, which is the right shape because names get
longer and catalog terms do not. The reference implementation does this, with a floor of one word so
that a name is always made progress on even against a vocabulary holding no long form at all. It is
an optimisation, not a rule — a port that scans from the full remaining length is equally correct.

**Step 3** emits `word.upper()` either way; what it decides is only what the audit record may claim.
If the upper-cased form is approved, `source` is `approved` with confidence one; otherwise
`passthrough` with confidence zero. Nothing is ever clipped.

**The appended class word.** After rendering, if `append_class_word_when_missing` is on, at least one
token was rendered, the last token's abbreviation is *not* a class word, and the vocabulary
designates `VAL` as a class word, append it — from the catalog row for `VAL` when there is one, else
as a token with no entry id and full confidence. Any of those four conditions failing means nothing
is appended.

**Assembly:** `physical` is the abbreviations joined with `_`; `term_id` is the term index looked up
on the whole logical name as supplied; `confidence` is the minimum across tokens, zero for an empty
name; `truncated` is `false`, unconditionally, under every policy.

`enforce_name_length` is **not read here at all**.

### 6.9 `is_compliant` and `normalize`

Both split, rejoin digits, and run one shared per-token ladder, so the check and the correction
cannot come to different conclusions. Both split with `split_identifier`, not with
`split_identifier_parts`: neither result has a field for an unaccounted character, so neither asks
for one. Such a character reaches a compliance check as the whole-name `not_upper_snake` finding it
causes, or as nothing at all, and it is absent from `normalize`'s output — the asymmetry is worked
through under [`IdentifierExpansion`](#identifierexpansion) in section 3.

**Per token**, in this order — a token containing no letter at all is passed through with **no
finding**:

| # | Test | Verdict | Code |
|---|---|---|---|
| 1 | `resolve` returns an entry whose source is `custom` | pass | `custom_abbrev` |
| 2 | in `approved_abbreviations` | pass | `approved_abbrev` |
| 3 | in `common_keywords` | pass | `common_keyword` |
| 4 | in `short_full_words` | pass | `short_full_word` |
| 5 | entry kind is `proper_noun_acronym` / `short_full_word` / `class_word_abbrev` | pass | the matching code / `short_full_word` / `approved_abbrev` |
| 6 | entry has `keep_as_abbrev` | pass | `approved_abbrev` |
| 7 | `is_approved` | pass | `approved_abbrev` |
| 8 | otherwise | **fail** | `unapproved_abbrev` |

Rules 2–4 read the three sets **directly**, not through `is_approved`, because the reason code has to
know *which* list matched. Rule 5 comes after the lists so a proper-noun acronym the catalog carries
but no list mentions reports the specific code rather than the bland one. Class-word entries pass:
a standard that requires every name to end in `DT` and then flags `DT` as unapproved is arguing with
itself.

**The suggested fix**, on a failure, goes through the long form: the entry says what the token means,
the reverse index says which token the standard approves for that meaning. It is proposed **only when
that replacement is itself approved** — which is what makes `normalize` idempotent, and is also the
honest rule, since rewriting one unapproved token to another has fixed nothing. No entry, no fix.

**The corrected name** is built in the same loop: each token contributes its `fix` if it has one,
else its upper-cased self; a letterless token contributes itself unchanged; joined with `_`. That is
`normalize`'s entire return value.

That construction is where idempotence is actually decided, and it carries an unstated premise a port
has to hold too: **the splitter must read its own upper-cased output the way it read the input.** A
token whose upper-cased form splits into two makes a name that moves on every pass. It holds for all
ASCII, asserted as a property, and the ordinal rule was written the wrong way round once and broke it
— see [`1sT`](#1st-is-1-s-t-and-condition-3-is-why). It is **false in general outside ASCII**, because
`str.upper` is not length-preserving and can produce characters that are not letters: `U+0390` upper-
cases to a capital iota and two combining marks, the marks are unaccounted, and the second pass drops
them. Java's `toUpperCase` has the same property with a different set of characters, so a port should
expect its own exceptions here rather than the reference implementation's.

**Whole-name findings**, appended in this order and **only when they fail**:

| Code | Condition | `fix` |
|---|---|---|
| `not_upper_snake` | the name as supplied is not upper-snake | the tokens upper-cased and `_`-joined |
| `missing_class_word` | `require_trailing_class_word` and the trailing token is not a class word | that same join plus `_VAL`, or nothing when `VAL` is not a governed class word |
| `exceeds_max_length` | `enforce_name_length` and the name is longer than the limit | the governed rewrite, but only when it differs from the input **and** fits |

"Upper-snake" means: non-empty, `_`-separated, no empty run (so no leading, trailing or doubled
underscore), and every character is a digit or a letter that is not lower-case. **Letters with no
case pass** — refusing a name for containing a CJK character would be enforcing an alphabet rather
than a convention.

An empty or separator-only name short-circuits to a single `empty_name` finding with
`compliant: false`, `ends_in_class_word: false` and `class_word: null`. `normalize` returns `""` for
the same input.

`ends_in_class_word` and `class_word` come from the trailing token: `class_word_for` first, then the
`class_word` of whatever the reverse index returns for it.

## 7. The batch envelope

Everything above this section is a shape a library returns. This is the one that actually crosses a
process boundary, which is what this document is for, so it is contract in the same sense the DTOs
are — a consumer parses these bytes, and a port that answers correctly inside a differently-shaped
envelope is not a drop-in.

```
acronymkit governed-batch [FILE] --dictionary <vocabulary>
                                 [--op expand|physical|check|normalize|audit]
                                 [--flush-every N]
```

One record per line in, on standard input (or `FILE`, or `-`); one JSON object per line out, on
standard output; read and answered and written one at a time with nothing accumulating. `FILE` may
be omitted only when standard input is not a terminal.

### 7.1 Input lines

Each line is **stripped of leading and trailing whitespace first** — Python's whitespace set, the 29
code points of [section 6.3](#the-accounted-set-exactly). Then:

| The line, after stripping | Read as |
|---|---|
| empty | **skipped**: no record is written, `skipped` is incremented, and the line number is still consumed |
| begins with `{` | a JSON object |
| anything else | the subject itself, verbatim |

The rule between the second and third is decidable rather than heuristic: no physical name begins
with `{`. Note it is the **first character only**, not "looks like JSON" — a line beginning `[` is a
subject, and `["TXN_ID"]` is answered as a name whose brackets are accounted separators rather than
rejected as an array.

A blank line consuming a line number rather than being deleted is what keeps `line` a usable
coordinate into the caller's file. A caller reconciling counts should expect
`records + skipped == lines read`.

The object form:

| Key | Required | Type | |
|---|---|---|---|
| `identifier` | yes | string | The subject. **Not** stripped, unlike the bare form — leading and trailing whitespace inside the string is passed to the verb and echoed on `input`. |
| `id` | no | string, number or boolean | Round-tripped onto the answer untouched. `null` is treated as absent and no `id` key is emitted. |

Any other key is ignored. Four things make a line unreadable, and each produces a failed **record**
rather than ending the run: it is not valid JSON; it parses to something other than an object; `id`
is present and is not one of those scalar types; `identifier` is absent or is not a string. An
`identifier` of `""` is readable and is answered — the verbs all accept empty input.

### 7.2 Output records

One JSON object per line, on standard output, with the keys in this order:

| # | Key | Present | |
|---|---|---|---|
| 1 | `line` | always | 1-based input line number, counting the blank lines that were skipped |
| 2 | `id` | only when the record supplied a non-null one | echoed untouched, including on a failed record |
| 3 | `input` | always | the subject as read; the **raw line** when the line could not be read |
| 4 | `ok` | always | boolean |
| 5 | `result` | when `ok` is true | |
| 5 | `error` | when `ok` is false | one sentence, prose for a person |
| 6 | `error_type` | when `ok` is false | |

`result` is the verb's own `to_dict()` payload and nothing else. The batch adds an envelope and no
opinions, so section 3 specifies `result` in full:

| `--op` | `result` | |
|---|---|---|
| `expand` (default) | `IdentifierExpansion` | |
| `physical` | `PhysicalName` | input lines are **logical** names; the JSON key is still `identifier` |
| `check` | `ComplianceResult` | |
| `normalize` | `{"name": <subject>, "normalized": <string>}` | not a DTO — two keys, in that order |
| `audit` | `IdentifierAudit` | section 7.5 |

`error_type` is the exception's class name for anything raised while answering — `LexiconError` under
`UnknownPolicy.REJECT` is the one documented case. For a line that could not be read it is the
literal string **`"InputError"`**, which names no class in this library and exists so the two
failures can be told apart without parsing prose. A port should emit the same literal.

Every exception is caught and reported on its record, including ones this library does not expect:
the right response to a bug on record 812 is to answer the other 49,999 and put the type on the
record. `error` is never empty — an exception with no message contributes its type name instead.

A real transcript, `--op expand` against the fixture catalog, showing every branch, with the long
`result` payloads elided to `…`. Lines 3 and 4 of the input were blank and produced no record, which
is why the line numbers jump:

```
{"line":1,"input":"TXN_APPLNT_DOB_DT","ok":true,"result":{"identifier":"TXN_APPLNT_DOB_DT","phrase":"Transaction Applicant Dob Date","tokens":[…],"class_word":"Date","is_fully_known":false,"unaccounted":[]}}
{"line":2,"id":4711,"input":"APPLNT_VERIF_DT","ok":true,"result":{…}}
{"line":5,"id":"row-9","input":"TXN_\ud83d\ude00_ID","ok":true,"result":{…,"is_fully_known":false,"unaccounted":["\ud83d\ude00"]}}
{"line":6,"id":12,"input":"{\"id\": 12}","ok":false,"error":"a JSON record must carry a string 'identifier'; it is absent. A line that is not a JSON object is read as the identifier itself.","error_type":"InputError"}
{"line":7,"input":"{not json","ok":false,"error":"line is not valid JSON: Expecting property name enclosed in double quotes: line 1 column 2 (char 1)","error_type":"InputError"}
{"line":8,"input":"[\"TXN_ID\"]","ok":true,"result":{…,"is_fully_known":true,"unaccounted":[]}}
{"line":9,"input":"CUST_ACCT_OPEN_DT","ok":true,"result":{…}}
```

and one raised while answering, under a policy whose `unknown` is `reject`:

```
{"line":1,"input":"TXN_DOB_DT","ok":false,"error":"Token 'DOB' is not in the governed vocabulary and NamingPolicy.unknown is REJECT. …","error_type":"LexiconError"}
```

Like `ComplianceReason.detail`, **`error` is prose and is not part of the contract**. Route on
`error_type` and on `ok`; a port is not required to reproduce the wording.

### 7.3 The summary, and the exit status

Exactly one line on **standard error**, after the last record, so that every line of standard output
is a record and a consumer can parse the stream without knowing to skip anything:

```
{"op":"expand","records":7,"failed":2,"skipped":2}
```

`records` counts records written, `failed` how many of those carry an error, `skipped` blank lines.
The summary is there so a caller can confirm it received every record it sent.

| Status | |
|---|---|
| `0` | every record was answered |
| `1` | **any record failed** — every record is still written first |
| `2` | usage error: an unusable `--dictionary` or `--custom`, no readable record stream, a bad flag |

**A finding is not a failure**, and a port must not conflate the two. Under `--op check` a name that
does not conform comes back `"ok": true` with `compliant` false inside the result, and the exit
status is unaffected; reporting that is the job the command was given. `governed-audit` follows the
same rule with a different trigger — it exits `1` when an input line could not be read, never because
the schema it was handed is imperfect.

### 7.4 Encoding of the stream

Three rules, and the first is the one that will bite a port that reuses its DTO serialiser:

1. **The record stream is ASCII.** `ensure_ascii=True`, so every non-ASCII character is `\u`-escaped
   and a record survives any console encoding on the far side. A character outside the Basic
   Multilingual Plane is written as a **UTF-16 surrogate pair of two `\u` escapes**, which is what
   the transcript above shows for U+1F600. This is the exact reverse of
   [section 4](#4-serialisation-rules)'s rule 7, which governs `to_json`. A port that emits the
   literal character produces valid JSON that parses equal and diffs differently; if text-level
   comparison matters, match the escaping.
2. **Records are compact.** Separators are `","` and `":"` with no spaces — again unlike `to_json`,
   whose no-indent form uses Python's spaced defaults. Key order inside `result` is still section 3's.
3. **Input is decoded as UTF-8** whatever the console code page says, with a BOM stripped from a named
   file and any undecodable byte replaced by U+FFFD rather than raising. The replacement reaches that
   one record's `input`, so the damage is visible and local instead of ending the run.

`--flush-every N` flushes standard output every `N` records, defaulting to `1`; `0` leaves flushing to
the interpreter's buffer, which is faster and wrong for a caller reading the pipe as it goes. It
changes when bytes arrive and nothing about what they are, so it is not something a port has to match
— but a co-process on the far side of a pipe will hang waiting on a buffered stream, which is the
failure the default exists to avoid.

### 7.5 `IdentifierAudit`, the `--op audit` payload

Declared in `src/acronymkit/governed/audit.py`, frozen and extra-forbidding like the models of
section 3, and specified here because this is where it crosses the wire.

| # | Field | JSON type | Required | Default |
|---|---|---|---|---|
| 1 | `identifier` | string | yes | |
| 2 | `occurrences` | integer | yes | |
| 3 | `is_fully_known` | boolean | yes | |
| 4 | `compliant` | boolean | yes | |
| 5 | `unknown_tokens` | array of string | no | `[]` |
| 6 | `codes` | array of `ComplianceReasonCode` | no | `[]` |
| 7 | `round_trip` | string or null | no | `null` |
| 8 | `governed_form` | string or null | no | `null` |

`occurrences` is always `1` from `governed-batch`, which audits one name at a time; it means something
only in a corpus audit. `unknown_tokens` are upper-cased, in identifier order, de-duplicated, and
include ordinals. `codes` are the distinct **failing** codes in the order the check produced them, and
the findings themselves are not carried — they hold a sentence per token and re-running `is_compliant`
on one name is cheap. `round_trip` is filled in only when the trip did not land on the identifier
itself, and `governed_form` only when `round_trip` is filled in; a clean name carries `null` twice.

```
{"line":1,"input":"APPLNT_BRTH_DT","ok":true,"result":{"identifier":"APPLNT_BRTH_DT","occurrences":1,"is_fully_known":true,"compliant":true,"unknown_tokens":[],"codes":[],"round_trip":null,"governed_form":null}}
{"line":2,"input":"applntBirthDate","ok":true,"result":{"identifier":"applntBirthDate","occurrences":1,"is_fully_known":false,"compliant":false,"unknown_tokens":["BIRTH","DATE"],"codes":["unapproved_abbrev","not_upper_snake"],"round_trip":"APPLNT_BRTH_DT","governed_form":"APPLNT_BIRTH_DATE"}}
```

Producing one of these runs `expand_identifier`, `is_compliant` and `to_physical_name` — the last on
the *phrase*, not on the identifier, which is what makes it a round trip — plus `normalize` as a
fourth call only when the round trip moved. `expand` runs one verb. That ratio is why `audit` is
opt-in rather than the default, and a port should keep the same shape so the two commands stay
comparable.

### 7.6 What `governed-audit` shares, and what it does not

`acronymkit governed-audit [FILE]` reads its input by exactly the rules of section 7.1 — same two line
forms, same brace test, blank lines skipped — and then reduces the whole corpus to one `CorpusAudit`
rather than answering line by line. An unreadable line is dropped from the audit with a message on
standard error naming its line number, and the command exits `1` when there was at least one.

**Its report shape is not specified in this document.** `CorpusAudit` and the four DTOs it contains
are a published surface that no port has been written against yet, and writing down a shape nobody has
implemented against would be recording a guess in a document whose whole value is that it does not.
Read `src/acronymkit/governed/audit.py` and treat it as the source of truth until this section grows.

## 8. Unicode and JVM hazards

Each of these is a place where the obvious Java translation is wrong. The Python behaviours below
were measured against CPython 3.13 on the reference implementation.

**Locale-sensitive case mapping.** `String.toUpperCase()` with a default locale of `tr` maps `i` to
`İ`, which would corrupt every token key on a Turkish-locale JVM. Python's `str.upper()` is
locale-independent. Use `Locale.ROOT` explicitly, everywhere, and never the no-argument overload.

**Case mapping that changes length.** Python's `"ß".upper()` is `"SS"`, two characters.
`String.toUpperCase(Locale.ROOT)` agrees; `Character.toUpperCase` does not. Use the string form.

**Case folding is not lower-casing.** The phrase key uses `casefold`, which applies full Unicode case
folding: `"ß".casefold()` is `"ss"`, so `Straße` and `Strasse` are one key. Java has no equivalent —
`toLowerCase(Locale.ROOT)` leaves `ß` alone. For an ASCII-only catalog the two agree exactly; beyond
that a port must implement full folding from Unicode's `CaseFolding.txt` (statuses C and F) or state
the restriction. This affects the reverse index, the term index and the overlay-contradiction test.

**Code points, not UTF-16 units.** Three places count characters, and all three mean code points:
the length penalty, the reverse-index token-length tie-break, and the `exceeds_max_length` check.
`String.length()` is wrong for any string outside the Basic Multilingual Plane; use
`codePointCount`.

**String ordering.** Python compares strings by code point. `String.compareTo` compares UTF-16 code
units, and the two disagree whenever a supplementary character meets a BMP character above U+DFFF:
Python orders `"�"` before `"\U0001F600"`, Java orders them the other way, because the emoji's
leading surrogate `\uD83D` sorts below `�`. This decides the `rank_candidates` tie-break and
the reverse-index tie-break. Use a code-point comparator, and never a `Collator` — a locale-aware
collation would make the audit trail depend on the machine.

**The digit test is wider than ASCII.** Python's `str.isdigit()` is true for `²`, so `TXN²ID` splits
into three tokens and a lone `²` counts as a digit token in the rejoin pass. `Character.isDigit` is
narrower — it covers `Nd` only. Match Python's test (`Nd` plus `Numeric_Type=Digit`) or document the
divergence.

**Upper-case is a property, not a category.** Python classifies `Ⅰ` (U+2160 ROMAN NUMERAL ONE) as
upper-case although it is not a letter — `isalpha()` is false, `isupper()` is true — so the tokenizer
puts it in the `UPPER` class. Check the derived `Uppercase` property, not `Character.isUpperCase`
alone, and pin the behaviour with a test.

**Whitespace, and it now decides three different things.** Python's argument-less `str.split()` and
`str.strip()` use a Unicode whitespace set that includes the C1 control `\x85` and the
file/group/record/unit separators. Java's `\s` is ASCII unless `UNICODE_CHARACTER_CLASS` is on, and
`String.trim()` is stricter still — it cuts at `U+0020`.

One set, `str.isspace()`, is the phrase key's word separator (6.1), the batch reader's line strip
(7.1) and — this is the new one — half of the tokenizer's **accounted** set (6.3), where it decides
what appears in `unaccounted` and therefore what `is_fully_known` says. It is the 29 code points
listed in 6.3, and **no single Java predicate is that set**:

| | Relative to `str.isspace()` |
|---|---|
| `Character.isWhitespace` | drops `U+0085`, and the three non-breaking spaces `U+00A0`, `U+2007`, `U+202F` |
| `Character.isSpaceChar` | keeps only the separator categories: drops `U+0009`–`U+000D`, `U+0085` and `U+001C`–`U+001F` |
| `\p{IsWhite_Space}` | the Unicode property alone: drops `U+001C`–`U+001F` |

`\p{IsWhite_Space}` is the closest and is what the strip and split sites should use; for the
tokenizer's accounted set, build the 29-element set literally instead. Reach for any of the three as
a drop-in and a name containing one of the differing characters reports an `unaccounted` entry the
reference implementation does not, or drops one it does — and `is_fully_known` disagrees with it.

**The ordinal rule is orthography, not Unicode.** `st`/`nd`/`rd`/`th` compared case-insensitively is
the whole rule, and the comparison must be `Locale.ROOT`: on a Turkish-locale JVM, lower-casing the
`T` of `1ST` yields `ı`, `"sı"` is not in the set, and every ordinal in the schema splits differently.
The same hazard as the token key, in a place nobody thinks to look for it.

**Map iteration order is part of the contract.** `from_long_to_short` records candidates in the
source mapping's iteration order, which for a Python `dict` is insertion order — so a catalog file
read top to bottom produces candidates in file order, and `ResolutionMode.MOST_COMMON`, which reads
element zero, sees what the file put first. A port must use an insertion-ordered map. A `HashMap`
would make the most-common answer depend on hash seeds.

**Float sums.** The seven penalties are summed in the published key order. Every value in the current
table is an integer represented exactly as a double, so no ordering effect is observable today; a
port that adds a fractional penalty inherits the ordering requirement.

## 9. The golden replay set

**This part exists.** `tests/fixtures/governed/golden/` holds eight JSONL files, 114 lines between
them, each line recording one call, the payload it expects, and a sentence saying what it proves.
They are driven by `tests/test_governed.py`, and `::test_every_golden_file_is_driven_by_a_test`
asserts that no file on disk is left unread — a golden file nobody loads is a specification nobody
checks, and it fails silently.

This is the artifact a port should be validated against. Read the same files, make the same calls,
diff the same payloads: a divergence then shows up on the first run, at the case that broke, with a
sentence next to it saying what that case was for.

| File | Lines | What it pins |
|---|---|---|
| `expand_token.jsonl` | 16 | One token per resolution rule, with full payloads |
| `expand_identifier.jsonl` | 12 | Whole identifiers, the trailing-class-word rule, partial knowledge |
| `to_physical_name.jsonl` | 11 | The reverse direction, glossary hits, words that are never clipped |
| `is_compliant.jsonl` | 9 | The reason-code ladder, including the short-word false-positive guard |
| `provenance.jsonl` | 11 | `source`, `entry_id`, `confidence` and `beat` — the audit fields |
| `custom_precedence.jsonl` | 23 | Rule 1, the demotion in both directions, layering, per-call overlays |
| `policy_contrast.jsonl` | 10 | The same input under several policies, including the governed-hit invariant |
| `edge_cases.jsonl` | 22 | Null, empty, whitespace, separators only, and the empty vocabulary |

### Line format

One JSON object per line. Three top-level keys, all required:

```json
{"input": {"verb": "expand_token", "arg": "ID", "custom": {"ID": "Identity"}},
 "expected": {"long": "Identity", "source": "custom", "entry_id": null},
 "proves": "Rule 1. A caller's overlay outranks a governed pin..."}
```

**`input`** describes the call:

| Key | Meaning |
|---|---|
| `verb` | `expand_token`, `expand_identifier`, `to_physical_name`, `is_compliant` or `normalize` |
| `arg` | The subject — a token, an identifier, a logical name or a physical name. May be `null`. |
| `policy` | Absent for the verb's own default, the **name** of a preset, or an inline object of field overrides. The object form is what lets a line vary one flag without dragging in the three other changes a preset would make. |
| `policies` | *(`policy_contrast.jsonl` only.)* A list of preset names; `expected` is then keyed by preset name. |
| `custom` | An inline overlay mapping, layered for that call only |
| `custom_layer` | A layer name from `custom_overlay.json`, instead of an inline mapping |
| `dictionary` | `"empty"` selects an empty vocabulary; absent selects the fixture catalog |
| `dictionary_layers` | Overlay layer names composed onto the dictionary in order, later winning — as distinct from `custom`, which is call-scoped |

**`expected`** is matched against `to_dict()` of the result — except `normalize`, whose bare string is
wrapped as `{"normalized": ...}` so that every file compares one shape.

**`proves`** is a sentence for a person, and the driver asserts it is non-empty. A golden line whose
purpose nobody wrote down is a line nobody can safely change.

### Partial matching, and why it is not laziness

A line names the fields it is *about* and stays silent on the rest. Objects are matched key by key,
so an expectation may carry three of a payload's nine fields; arrays are matched element by element
**and on length**, because a missing or extra token is exactly the regression these files exist to
catch. A port replaying them needs the same rule, or the lines that deliberately omit a field will
fail against it.

Two fields to leave out of equality unless the case is about them:

- **`ComplianceReason.detail`** — prose for a person, explicitly not contractual, free to be reworded.
- **`notes`** — compare it only where the line is about a note, which means the overlay demotion and
  the most-common mode note. The wording of the load-time inversion note is not contractual.

Compare **parsed documents**, not text. Section 4's separator and float rules make text comparison
possible but brittle, and a port has no reason to inherit Python's `json.dumps` defaults.

### What a port should add

The eight files cover the verbs and the precedence chain, and they are the *older* half of this
contract: **no golden line mentions `unaccounted`, the ordinal rule or the batch envelope.** Those are
pinned by named tests instead, and a port replaying only the golden set will pass while diverging on
every one of them. Each row below is an area a port needs its own equivalents for:

| Area | Where it lives today |
|---|---|
| The losslessness guarantee | `tests/test_governed_edge_cases.py::test_nothing_leaves_without_being_kept_or_reported`, plus the two corollary property tests named in 6.3, and `::test_a_fully_known_identifier_accounted_for_all_of_itself` for the `is_fully_known` half |
| The accounted set | `tests/test_governed_edge_cases.py::test_the_accounted_separators_are_the_published_ones` and `::test_a_quoted_identifier_reads_as_the_bare_one`, which is what stops a schema read out of `information_schema` arriving with every row flagged |
| Ordinals | `tests/test_governed_edge_cases.py::test_an_ordinal_suffix_stays_with_its_digits`, `::test_the_ordinal_rule_does_not_reach_past_the_suffix`, `::test_a_separator_still_keeps_an_ordinal_apart`, `::test_a_lower_then_upper_ordinal_suffix_is_not_one`, and the same pin in `tests/test_governed_perf.py` |
| Token stability under upper-casing | `tests/test_governed_edge_cases.py::test_an_ascii_token_upper_cased_splits_back_to_exactly_itself`. This is what `normalize`'s idempotence rests on and it is not implied by any golden line; the ordinal rule was written the wrong way round once and this is what would have caught it. Its Unicode exception is pinned beside it by `::test_normalize_is_not_idempotent_when_upper_casing_creates_a_combining_mark` |
| Tokenizer boundaries | `tests/test_governed.py::test_split_identifier_follows_the_stated_rules`, plus four property tests asserting it never raises, never emits an empty token, keeps every letter and digit in order, and returns substrings of its input |
| The corpus invariants | `tests/test_governed.py::test_the_round_trip_lands_on_the_governed_correction` and `::test_normalize_is_idempotent_under_every_policy`, both parametrised over all 40 lines of `corpus_sample.txt` |
| The scoring table | Exercised through the collision tokens rather than rule by rule. A port should add one case per penalty row, both exemption sets, and a tie the lexicographic rule settles. |
| The batch envelope | `tests/test_cli.py`. Section 7 is the specification; a port should replay a file containing a bare line, an object line with an `id`, a blank line, and each of the four unreadable shapes, and assert the record keys, the summary and the exit status |

Add the Unicode cases from [section 8](#8-unicode-and-jvm-hazards) too. They are the ones a JVM port
will get wrong first, and none of them is in the golden set either.

## 10. What is not decided

Six things a port will run into that this contract does not settle. None is a defect in the port;
each is a hole in the specification, recorded so two implementations do not fill it two ways.

1. **No `EntryKind` for an unpinned collision.** Rows with several candidates and no pin are filed
   as `ambiguous_pinned` with `"pin": null`; the kind names the archetype and the `pin` field alone
   says whether a decision exists. An `AMBIGUOUS_UNPINNED` member would say it correctly. Until then,
   **`pin` is the field to branch on, never the kind.**
2. **No `EntryKind` for a common keyword.** An allow-list-only token from `common_keywords` is
   synthesised as `approved_abbrev`, which names how it behaves rather than what it is. A port must
   read the three allow-list sets, not the kind, to produce the right compliance reason code.
3. **No field naming the class word to append.** `NamingPolicy` has
   `append_class_word_when_missing` and nothing saying *which*. The reference implementation names a
   module constant, `VAL`, and appends it only when the caller's own vocabulary designates it — so a
   catalog whose neutral class word is something else gets nothing appended. `class_words.json`
   records `default_class_word` in an object nothing consumes. A `NamingPolicy.default_class_word`
   field would settle it, and a port should be written so that adding one is a one-line change.
4. **No reason code for a letterless token.** The `1` of `ADDR_LINE_1_TXT` produces no compliance
   finding at all, because no code describes a bare position marker honestly. A port that invents one
   will diff against every address column in a schema. The ordinal rule narrowed this rather than
   closing it: `1ST` bears letters, so it *is* judged, and against a catalog with no row for it the
   finding is `unapproved_abbrev` with no `fix` — which is at least a row somebody can write, where
   the old split produced a finding about `ST`, a word the column does not contain.
5. **The demotion note is not on `TokenExpansion`.** It rides on the `GovernedEntry` that `resolve`
   returns. A port that adds a `notes` field to the expansion would be more useful and would no
   longer match this contract; if it is added, it should be added on both sides as a deliberate
   amendment.
6. **Nothing records *where* an unaccounted character was.** `unaccounted` is a multiset in input
   order, not a list of offsets, so `TXN_😀_ID` and `😀TXN_ID` report the same one entry. That is
   enough to say "this name holds a character nobody accounted for", which is the question the field
   was added to answer, and not enough to point at it in an editor. Offsets would settle it and would
   also fix the shape of the field for anyone already parsing it, so a port should not add them
   unilaterally. The counting guarantee in 6.3 is stated in a form that survives the change.

Two naming notes, recorded so a port does not have to rediscover them. The verb is `normalize` inside
`acronymkit.governed` and `normalize_name` when re-exported from the top-level package — one object,
two spellings, because `acronymkit.tokenizer.normalize` already exists and does something else. And
`rank_candidates`, `DERIVED_ENTRY_CONFIDENCE` and `DEFAULT_CLASS_WORD` are implementation decisions
rather than contract items: a port may name them whatever is idiomatic, but their *behaviour* is
specified above and is not optional.

## See also

- [docs/GOVERNED_NAMING.md](../GOVERNED_NAMING.md) — the integration guide, with the precedence chain
  worked through and the honest limits.
- [`tests/fixtures/governed/README.md`](../../tests/fixtures/governed/README.md) — what each fixture
  file exercises, and the divergences its authors found.
- [`schemas/acronym-engine-result.schema.json`](../../schemas/acronym-engine-result.schema.json) —
  the generation side's contract, which *is* machine-readable, and the model this side should follow
  if a schema is ever written for it.
