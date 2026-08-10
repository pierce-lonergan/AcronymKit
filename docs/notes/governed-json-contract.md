# The governed wire contract

**No JVM artifact exists.** There is no `acronym4j`, no Maven coordinate, no jar, and nothing in
this repository builds one. `README.md` lists a Java port as a roadmap item and that is where it
stands.

This document is the thing that would make writing one *mechanical rather than a guess*: the exact
JSON shape of every governed DTO, the exact behaviour of every algorithm behind those shapes, and the
golden replay set a port can be validated against by making the same calls on the same fixtures and
diffing the same payloads. The golden files are real and are in this repository; the port is not.
Nothing here should be read as a claim that a port works, is planned for a release, or has been
tested.

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
7. [Unicode and JVM hazards](#7-unicode-and-jvm-hazards)
8. [The golden replay set](#8-the-golden-replay-set)
9. [What is not decided](#9-what-is-not-decided)

## 1. Scope and encoding

| | |
|---|---|
| Covered | The seven DTOs of `acronymkit.governed.models`, the six enums of `acronymkit.governed.enums`, `NamingPolicy`, and the fixture file formats under `tests/fixtures/governed/` |
| Not covered | `AcronymResult` and the generation-side DTOs, which have their own published contract in [`schemas/acronym-engine-result.schema.json`](../../schemas/acronym-engine-result.schema.json) |
| Encoding | UTF-8 throughout, for both input files and emitted JSON |
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

```json
{"raw": "ID", "long": "Identifier", "is_known": true, "source": "pinned",
 "entry_id": "NDS-ID", "confidence": 1.0, "class_word": "Identifier",
 "beat": ["Identification", "Identity", "Idaho"], "kind": "ambiguous_pinned"}
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

`class_word` comes from the **trailing token only**. `is_fully_known` is `true` for an empty token
list, vacuously.

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
exclude `detail` or compare it advisorily (see section 8).

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
7. **Non-ASCII is emitted literally.** `ensure_ascii=False`; no `\uXXXX` escaping.
8. **There is no envelope.** No `$schema`, no version field, no wrapper object. A `TokenExpansion` is
   the top-level document.

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
[section 9](#9-what-is-not-decided).

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
which also strips the ends. Case folding is *not* lower-casing; see section 7.

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

### 6.3 `split_identifier`

`tokenizer.py`. Pure; no dictionary, no configuration, never raises.

Classify each character into exactly one of five classes, testing **in this order**:

```
isupper -> UPPER      islower -> LOWER      isdigit -> DIGIT
isalpha -> CASELESS   otherwise -> SEPARATOR
```

`CASELESS` is a letter with no case of its own — CJK, Hebrew, Devanagari. `SEPARATOR` is *anything*
that is neither a letter nor a digit: the five separators the design names (`_`, `-`, `.`, `/`,
whitespace) and every other punctuation mark too, because a token is about to be used as a lookup key
and no catalog entry contains punctuation.

Then walk the string. A separator closes the current token. Otherwise, when a token is already open,
open a new one if:

```
current is DIGIT     and previous is a letter class        -> boundary
previous is DIGIT    and current is a letter class         -> boundary
current is UPPER     and previous is LOWER                 -> boundary
current is UPPER     and previous is UPPER and next is LOWER -> boundary
otherwise                                                   -> no boundary
```

One character of lookahead, used only by the last rule; at end of input the lookahead is
`SEPARATOR`. `CASELESS` takes part in the letter/digit rules and creates no case boundary, so
`ETL<CJK><CJK>Stamp` stays one token.

Tokens come back with their original casing, in input order, and concatenating them recovers the
input minus its separators. Empty and separator-only input yields an empty list.

```
"TXN_APPLNT_DOB_DT"      -> ["TXN", "APPLNT", "DOB", "DT"]
"creditBureauVendorCode" -> ["credit", "Bureau", "Vendor", "Code"]
"ETLTimestamp"           -> ["ETL", "Timestamp"]
"MDMHubID"               -> ["MDM", "Hub", "ID"]
"address2line1"          -> ["address", "2", "line", "1"]
"7Code"                  -> ["7", "Code"]
"nds.risk-model / SCORE" -> ["nds", "risk", "model", "SCORE"]
"1MM"                    -> ["1", "MM"]
```

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

**`expand_identifier`**: split, rejoin digits, expand each token. Then

```
phrase          = the non-empty long forms joined with single spaces
class_word      = the last token's class_word, or null when there are no tokens
is_fully_known  = every token is_known  (true for no tokens)
```

Failure modes, and there are only two: an absent dictionary is a configuration error; an unknown
token under `REJECT` is a vocabulary error naming the token, and the first such token stops the call.

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
cannot come to different conclusions.

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

## 7. Unicode and JVM hazards

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

**Whitespace.** Python's argument-less `str.split()` and `str.strip()` use a Unicode whitespace set
that includes the C1 control `\x85` and the file/group/record/unit separators. Java's `\s` is ASCII
unless `UNICODE_CHARACTER_CLASS` is on, and `String.trim()` is stricter still — it cuts at
`U+0020`. Use `\p{IsWhite_Space}` with an explicit `strip()`.

**Map iteration order is part of the contract.** `from_long_to_short` records candidates in the
source mapping's iteration order, which for a Python `dict` is insertion order — so a catalog file
read top to bottom produces candidates in file order, and `ResolutionMode.MOST_COMMON`, which reads
element zero, sees what the file put first. A port must use an insertion-ordered map. A `HashMap`
would make the most-common answer depend on hash seeds.

**Float sums.** The seven penalties are summed in the published key order. Every value in the current
table is an integer represented exactly as a double, so no ordering effect is observable today; a
port that adds a fractional penalty inherits the ordering requirement.

## 8. The golden replay set

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

The eight files cover the verbs and the precedence chain. Three areas are covered by property and
corpus tests in `tests/test_governed.py` rather than by golden lines, and a port needs its own
equivalents:

| Area | Where it lives today |
|---|---|
| Tokenizer boundaries | `::test_split_identifier_follows_the_stated_rules`, plus four property tests asserting it never raises, never emits an empty token, keeps every letter and digit in order, and returns substrings of its input |
| The corpus invariants | `::test_the_round_trip_lands_on_the_governed_correction` and `::test_normalize_is_idempotent_under_every_policy`, both parametrised over all 40 lines of `corpus_sample.txt` |
| The scoring table | Exercised through the collision tokens rather than rule by rule. A port should add one case per penalty row, both exemption sets, and a tie the lexicographic rule settles. |

Add the Unicode cases from section 7 too. They are the ones a JVM port will get wrong first, and none
of them is in the golden set.

## 9. What is not decided

Five things a port will run into that this contract does not settle. None is a defect in the port;
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
4. **No reason code for a letterless token.** The `1` and `2` of `ADDR_LINE_1_TXT` produce no
   compliance finding at all, because no code describes an ordinal honestly. A port that invents one
   will diff against every address column in a schema.
5. **The demotion note is not on `TokenExpansion`.** It rides on the `GovernedEntry` that `resolve`
   returns. A port that adds a `notes` field to the expansion would be more useful and would no
   longer match this contract; if it is added, it should be added on both sides as a deliberate
   amendment.

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
