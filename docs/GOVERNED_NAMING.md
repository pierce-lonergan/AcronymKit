# Governed naming

For the person wiring `acronymkit.governed` into a schema-governance pipeline. It answers one
question — *given the bare column token `TXN_ID` and our data standard, what does it mean?* — and it
answers it out of the standard, never out of a model.

```python
from acronymkit.governed import GovernedDictionary, expand_identifier

nds = GovernedDictionary.from_long_to_short({"Transaction": "TXN", "Identifier": "ID"})
expand_identifier("TXN_ID", nds).phrase          # 'Transaction Identifier'
```

Three directions over one vocabulary: expand a physical name into words, render a logical name back
into a physical one, and check a name somebody else wrote. They live in one package so that they
cannot disagree — a catalog change that moves an abbreviation moves all three at once.

The eight names an integration needs are also on the top-level package, so
`from acronymkit import expand_identifier, GovernedDictionary` works too. `normalize` is the one
that changes spelling on the way out — it is `acronymkit.normalize_name`, because
`acronymkit.tokenizer.normalize` already exists and does something else. Either import path resolves
lazily and costs nothing until it is used.

**If your standard is in a spreadsheet and your pipeline is in another language**, start with
[docs/QUICKSTART_GOVERNED.md](QUICKSTART_GOVERNED.md) instead — it goes from a CSV to a whole schema
answered in one process, at the command line, in five minutes. This page is the contract behind it.

- [What this is not](#what-this-is-not-and-why-that-is-the-design)
- [A catalog to work against](#a-catalog-to-work-against)
- [Precedence: the caller's overlay comes first](#precedence-the-callers-overlay-comes-first)
- [The verbs](#the-verbs)
- [Binding it once: `GovernedNamer`](#binding-it-once-governednamer)
- [Building a vocabulary](#building-a-vocabulary)
- [Auditing a whole schema](#auditing-a-whole-schema)
- [From another process](#from-another-process)
- [What the splitter accounts for](#what-the-splitter-accounts-for)
- [Policies](#policies)
- [The four invariants](#the-four-invariants)
- [Limits](#limits)

## What this is not, and why that is the design

**It is not disambiguation.** `acronymkit`'s `LexicalDisambiguator` answers "which of these
expansions does this *sentence* mean?" and needs the sentence. A column name is not a sentence.
There is no surrounding prose, no document, no corpus — there is one token, and no amount of
modelling can extract from `TXN_ID` a signal that is not in it.

So the answer has to come from somewhere else, and in a governed setting it already has: somebody
wrote the standard down. That changes what "correct" means. The catalog is not evidence about the
right answer, it *is* the right answer, and a model that agreed with it most of the time would still
disagree with it some of the time, nobody could say in advance where, and every disagreement would
be a library overruling a decision a data-governance function already made and signed off.

The three properties every design choice here serves:

| Property | What it means in practice |
|---|---|
| **The dictionary is the ground truth** | Nothing is inferred, learned or approximated. An unknown token comes back marked unknown, with zero confidence, and the fix is a catalog row. |
| **Context-free** | The input is one token or one identifier. The same token resolves the same way in every row of a million-row table, because there is no context that could have changed it. |
| **Auditable** | Every expanded token carries where its answer came from, which catalog row produced it, how far the catalog stands behind it, and what it was chosen over. |

The willingness to say "I do not know" is the feature. An unknown token reported as unknown is
recoverable: a pipeline filters on `is_known`, routes the misses to whoever owns the catalog, and
somebody adds a row. An unknown token quietly approximated is not recoverable, because nothing
downstream can tell it from an answer.

**This is not a language model, a frequency table or a fuzzy matcher**, and it will not become one.
The single place any judgement is exercised is
[`canonical_form_score`](#when-nobody-pinned-the-collision), which settles a collision the catalog
left unresolved — and it says so in the output, with the arithmetic attached.

## A catalog to work against

Every example below runs against this vocabulary. It is a fictional catalog, **Northwind Data
Standards** (`NDS`), with synthetic entry ids; it describes no real organisation's standard. Paste
it into a file and the rest of this page is executable.

```python
from acronymkit.governed import (
    EntryKind, ExpansionSource, GovernedDictionary, GovernedEntry,
)

def entry(token, canonical, kind, **kw):
    kw.setdefault("source", ExpansionSource.GOVERNED)
    kw.setdefault("entry_id", f"NDS-{token}")
    return GovernedEntry(token=token, canonical=canonical, kind=kind, **kw)

CATALOG = [
    entry("TXN",    "Transaction", EntryKind.APPROVED_ABBREV, keep_as_abbrev=True),
    entry("APPLNT", "Applicant",   EntryKind.APPROVED_ABBREV, keep_as_abbrev=True),
    entry("CUST",   "Customer",    EntryKind.APPROVED_ABBREV, keep_as_abbrev=True),
    entry("ACCT",   "Account",     EntryKind.APPROVED_ABBREV, keep_as_abbrev=True),
    entry("NBR",    "Number",      EntryKind.APPROVED_ABBREV, keep_as_abbrev=True),
    entry("ID", "Identifier", EntryKind.AMBIGUOUS_PINNED,
          candidates=("Identification", "Identity", "Identifier", "Idaho"),
          pin="Identifier", class_word="Identifier",
          source=ExpansionSource.PINNED),
    entry("DT",  "Date",  EntryKind.CLASS_WORD_ABBREV, class_word="Date"),
    entry("CD",  "Code",  EntryKind.CLASS_WORD_ABBREV, class_word="Code"),
    entry("VAL", "Value", EntryKind.CLASS_WORD_ABBREV, class_word="Value"),
    entry("ZIP",   "ZIP",   EntryKind.PROPER_NOUN_ACRONYM, keep_as_abbrev=True),
    entry("FRAUD", "Fraud", EntryKind.SHORT_FULL_WORD,     keep_as_abbrev=True),
    entry("CUSTMR", "Customer", EntryKind.UNAPPROVED_EXPANSION, confidence=0.6),
    entry("NUM",    "Number",   EntryKind.UNAPPROVED_EXPANSION, confidence=0.6),
    entry("CTL", "Control", EntryKind.AMBIGUOUS_PINNED,
          candidates=("Controlling", "Control", "Controller"),
          source=ExpansionSource.SCORED, confidence=0.5),
]

nds = GovernedDictionary(
    CATALOG,
    approved_abbreviations=["TXN", "APPLNT", "CUST", "ACCT", "NBR", "ID", "DT", "CD", "VAL"],
    common_keywords=["TOTAL", "OPEN", "PRIMARY", "OWNER", "PARTY", "VERIFICATION", "STAT"],
    short_full_words=["FRAUD", "RISK", "SCORE", "MODEL"],
    class_words={"ID": "Identifier", "DT": "Date", "CD": "Code",
                 "VAL": "Value", "NBR": "Number"},
    term_index={"Customer Account Open Date": "TRM-400001"},
)
```

Six kinds of thing go in, and each answers a different question:

| Argument | The question it answers |
|---|---|
| `entries` | What does this token mean? |
| `approved_abbreviations`, `common_keywords`, `short_full_words` | May this token stand, as written, in a physical name? |
| `class_words` | Does this token say what *kind* of value the column holds? |
| `term_index` | Is this whole logical name a governed term in the glossary? |
| `custom` | What has the caller declared that the catalog could not know? |

A larger worked corpus — 68 catalog rows, three allow-lists, a pin sheet, a 36-row glossary, a
two-layer overlay and 40 identifiers — lives under `tests/fixtures/governed/`, with its own README,
alongside a golden replay set under `golden/` in which every line records the call it makes, the
payload it expects and a sentence saying what it proves. It is not shipped in the wheel; clone the
repository to use it.

## Precedence: the caller's overlay comes first

One order, highest first, applied to every token. This is the part to get right, and it is what
`ExpansionSource` reports back:

| # | Rule | `source` | Beaten by |
|---|---|---|---|
| 1 | the caller's `custom` overlay | `custom` | nothing (see the demotion below) |
| 2 | the entry's `pin` | `pinned` | an overlay |
| 3 | the entry's `canonical` | `approved` when `keep_as_abbrev`, else `governed` | an overlay |
| 4 | allow-list membership with no catalog row | `approved` | any catalog row |
| 5 | a collision with no pin, settled by score | `scored` | a pin, an overlay |
| 6 | nothing matched | `passthrough` | everything |

Rules 3 and 5 never compete for the same row: rule 5 is a different *shape* of row — several
candidates, no pin — and every other shape takes `canonical`. Their relative position arbitrates
nothing.

### Your acronyms win

Pass `custom=` to any verb and it is layered for that call only. The dictionary you hold is not
modified.

```python
from acronymkit.governed import expand_token

expand_token("KYC", nds).to_dict()
# {'raw': 'KYC', 'long': 'Kyc', 'is_known': False, 'source': 'passthrough',
#  'entry_id': None, 'confidence': 0.0, 'class_word': None, 'beat': [], 'kind': 'passthrough'}

expand_token("KYC", nds, custom={"KYC": "Know Your Customer"}).to_dict()
# {'raw': 'KYC', 'long': 'Know Your Customer', 'is_known': True, 'source': 'custom',
#  'entry_id': None, 'confidence': 1.0, 'class_word': None, 'beat': [],
#  'kind': 'approved_abbrev'}
```

`source` comes back `custom`, which is the point: a downstream consumer can tell an answer that came
from the standard from an answer that came from the caller, without being told.

An overlay value may be a bare string or a whole `GovernedEntry`, and the entry form is how an
overlay carries its own provenance:

```python
wallet = GovernedEntry(
    token="WLT", canonical="Wallet Account", kind=EntryKind.APPROVED_ABBREV,
    keep_as_abbrev=True, entry_id="LOCAL-WLT-0002",
    source=ExpansionSource.CUSTOM, confidence=0.8,
)
expand_token("WLT", nds, custom={"WLT": wallet}).to_dict()
# {'raw': 'WLT', 'long': 'Wallet Account', 'is_known': True, 'source': 'custom',
#  'entry_id': 'LOCAL-WLT-0002', 'confidence': 0.8, 'class_word': None, 'beat': [],
#  'kind': 'approved_abbrev'}
```

`entry_id` and `confidence` survive, so an audit trail distinguishes "the catalog says so" from "a
project said so, at eight tenths". Use a prefix of your own for overlay ids — the fixture corpus uses
`LOCAL-` against the catalog's `NDS-` — so that provenance is legible at a glance.

To hold an overlay for longer than one call, layer it into a dictionary:

```python
house   = nds.with_custom({"KYC": "Know Your Customer"})
project = house.with_custom({"KYC": "Know Your Counterparty"})

house.resolve("KYC").canonical            # 'Know Your Customer'
project.resolve("KYC").canonical          # 'Know Your Counterparty'
nds.resolve("KYC")                        # None — the receiver is unchanged
```

Layers compose and the last one wins on any token both mention, while an earlier layer stays in
force on every token the later one is silent about. `with_custom` shares the catalog rows, the
allow-lists and the reverse index by reference and rebuilds only the overlay, so it is cheap enough
to sit inside a loop over a schema.

### When an override is refused

`NamingPolicy(allow_override=False)` does not switch the overlay off. It refuses exactly one thing:
an overlay that **contradicts** what the catalog already says.

```python
from acronymkit.governed import NamingPolicy

overlaid = nds.with_custom({"ID": "Identity"})
strict   = NamingPolicy(allow_override=False)

overlaid.resolve("ID").canonical                  # 'Identity'   (source 'custom')
overlaid.resolve("ID", strict).canonical          # 'Identifier' (source 'pinned')
overlaid.resolve("ID", strict).notes
# "Custom override refused: the overlay long form 'Identity' contradicts the governed
#  entry 'Identifier' and policy.allow_override is False, so the catalog answer stands."
```

An overlay for a token the catalog has never heard of is applied under **every** policy, because
overriding nothing is not an override — there is no governed decision to overrule, and refusing it
would leave the caller holding an unknown token with no way to fix it:

```python
nds.with_custom({"KYC": "Know Your Customer"}).resolve("KYC", strict).source.value
# 'custom'
```

> **The refusal note is visible on the entry, not on the expansion.** `TokenExpansion` has no
> `notes` field and forbids extra ones, so `expand_token` returns the governed answer with no
> explanation attached; `GovernedDictionary.resolve` is where the refusal is legible. That is a gap
> in the DTO surface rather than a decision, and it is recorded here so it is not mistaken for one.

### An overlay loaded from JSON needs no construction step

A `GovernedEntry` written into a JSON file parses back as a `dict`, and a `dict` is not a
`GovernedEntry`. `with_custom` takes it anyway: an overlay value may be a string, a `GovernedEntry`,
or a mapping that describes one, and the third is built into an entry rather than stringified. Keys
beginning with `_` are skipped, so a `_comment` field survives the round trip through a file that has
no comment syntax.

```python
import json

# exactly what Path("house_overlay.json").read_text(encoding="utf-8") would hand you
payload = json.loads("""
{"layers": {"house": {
    "_comment": "house overlay, reviewed 2026-08",
    "KYC": {"canonical": "Know Your Customer", "kind": "approved_abbrev",
            "entry_id": "HOUSE-1", "confidence": 0.8},
    "WLT": "Wallet Account"}}}
""")

catalog = nds.with_custom(payload["layers"]["house"])
expand_token("KYC", catalog).long     # 'Know Your Customer'   source 'custom', entry_id 'HOUSE-1'
expand_token("WLT", catalog).long     # 'Wallet Account'       source 'custom', entry_id None
```

**A malformed mapping raises rather than quietly becoming text**, which is the whole reason the
branch exists. `{"BAD": {"kind": "approved_abbrev"}}` raises `LexiconError` naming the token and the
missing field — *Custom overlay entry 'BAD' is not a valid governed entry: canonical: Field required*
— because falling through to the string branch would hand back an "expansion" that was the repr of a
dict, reported as known with full confidence. That is the one outcome this package exists to prevent,
and it is worth knowing that **this page told you to convert the dicts yourself until this round**:
the workaround was written against an implementation that no longer behaves that way, and a reader
who still has it in their pipeline can delete it.

## The verbs

Five functions, one shape: `verb(subject, dictionary, policy=None, *, custom=None)`.

- `policy=None` means `NamingPolicy.governed_default()`.
- `dictionary=None` raises `ConfigurationError`. A governed verb with no governed vocabulary is a
  contradiction; the coherent reading of "no dictionary" — expand nothing, pass everything through —
  is spelled `GovernedDictionary()`, and does exactly that.
- `custom=` is layered for that call only.

### `expand_token`

One token, looked up whole. No splitting, no stripping of separators.

```python
expand_token("txn", nds).to_dict()
# {'raw': 'txn', 'long': 'Transaction', 'is_known': True, 'source': 'approved',
#  'entry_id': 'NDS-TXN', 'confidence': 1.0, 'class_word': None, 'beat': [],
#  'kind': 'approved_abbrev'}
```

`raw` is the token exactly as it arrived, so a result can be aligned back onto the caller's own row.
`beat` is the explainability payoff — it is what separates a token that was never ambiguous from one
whose ambiguity was resolved:

```python
expand_token("ID", nds).to_dict()
# {'raw': 'ID', 'long': 'Identifier', 'is_known': True, 'source': 'pinned',
#  'entry_id': 'NDS-ID', 'confidence': 1.0, 'class_word': 'Identifier',
#  'beat': ['Identification', 'Identity', 'Idaho'], 'kind': 'ambiguous_pinned'}
```

"`ID` means Identifier" is a claim. "`ID` means Identifier, and the catalog had also seen
Identification, Identity and Idaho" is a decision a reviewer can check.

An unknown token is Title Cased so the phrase stays readable, and marked so no program mistakes it
for an answer — `is_known` false, `confidence` zero, `source` `passthrough`, `entry_id` null. All
four say the same thing, deliberately, because a consumer might only read one of them.

### `expand_identifier`

A whole physical name, token by token.

```python
from acronymkit.governed import expand_identifier

result = expand_identifier("TXN_APPLNT_ID", nds)
result.phrase           # 'Transaction Applicant Identifier'
result.class_word       # 'Identifier'
result.is_fully_known   # True
```

`class_word` is read from the **trailing token and nowhere else**. Position is the whole rule:
`APPLNT_VERIF_DT` names a date and `DT_APPLNT_VERIF` does not. Each token still reports the class
word *it* designates, so the per-token records are not lying about `DT`; it is the identifier-level
field that reads only the last one.

`is_fully_known` is the one bit a pipeline gates on, and `unknown_tokens` is its actionable half:

```python
partial = expand_identifier("CUST_ACCT_KYC_ID", nds)
partial.phrase                                  # 'Customer Account Kyc Identifier'
partial.is_fully_known                          # False
[token.raw for token in partial.unknown_tokens] # ['KYC']
```

Splitting understands the conventions physical names are written in — separators, camelCase,
acronym runs and letter/digit boundaries — and is available on its own:

```python
from acronymkit.governed import split_identifier

split_identifier("TXN_APPLNT_DOB_DT")       # ('TXN', 'APPLNT', 'DOB', 'DT')
split_identifier("creditBureauVendorCode")  # ('credit', 'Bureau', 'Vendor', 'Code')
split_identifier("ETLTimestamp")            # ('ETL', 'Timestamp')
split_identifier("address2line1")           # ('address', '2', 'line', '1')
split_identifier("nds.risk-model / SCORE")  # ('nds', 'risk', 'model', 'SCORE')
split_identifier("1MM")                     # ('1', 'MM')
split_identifier(None)                      # ()
```

`1MM` splitting is not a bug. Nothing in the string says it should not split — it has exactly the
shape of `7Code`, which must. `expand_identifier` makes a second, dictionary-aware pass that puts
the token back **only where the catalog vouches for it**, which keeps the splitter a function of its
input rather than of somebody's vocabulary. That pass restores a digit-*leading* token and nothing
else: a join whose result is itself all digits is refused, so a catalog carrying `911` does not turn
`9_1_1` into it. See [Idempotence](#idempotence) for why that refusal is load-bearing rather than
fastidious.

An unknown token is one half of `is_fully_known`. The other is `unaccounted`, the characters the
splitter could not read as part of any token — see
[What the splitter accounts for](#what-the-splitter-accounts-for).

### `to_physical_name`

The reverse direction: a logical name rendered as `UPPER_SNAKE`, word by word, through the
dictionary's reverse index.

```python
from acronymkit.governed import to_physical_name

name = to_physical_name("Customer Account Open Date", nds)
name.physical      # 'CUST_ACCT_OPEN_DT'
name.term_id       # 'TRM-400001'
name.confidence    # 1.0
name.truncated     # False
[t.to_dict() for t in name.tokens]
# [{'word': 'Customer', 'abbrev': 'CUST',  'source': 'approved', 'entry_id': 'NDS-CUST'},
#  {'word': 'Account',  'abbrev': 'ACCT',  'source': 'approved', 'entry_id': 'NDS-ACCT'},
#  {'word': 'Open',     'abbrev': 'OPEN',  'source': 'approved', 'entry_id': None},
#  {'word': 'Date',     'abbrev': 'DT',    'source': 'governed', 'entry_id': 'NDS-DT'}]
```

`term_id` says the *name* is a governed term, which is a different claim from its words being
governed. `Open` carries no `entry_id` because it is approved by an allow-list with no catalog row
behind it — approval and expansion are separate facts.

A word the catalog does not abbreviate is upper-cased exactly as it stands and **never clipped**.
Shortening a word the standard has not abbreviated would be inventing an abbreviation, which is the
one thing this package will not do:

```python
to_physical_name("Fraud Model Risk Score", nds).physical
# 'FRAUD_MODEL_RISK_SCORE_VAL'
```

The trailing `VAL` is `append_class_word_when_missing` doing its job. It fires only when the
caller's own vocabulary designates `VAL` as a class word; a catalog whose neutral class word is
`IND` or `CD` gets nothing appended, and the shortfall is reported by `is_compliant` instead. No
name ever gains a token the caller's standard does not govern. See
[the class-word gap](#the-class-word-to-append-is-not-in-the-policy) for why this is a module
constant rather than a policy field.

### `is_compliant`

Never a bare boolean. `False` is not actionable: a name fails because of *something*, and the
something is usually one token out of six.

```python
from acronymkit.governed import is_compliant

is_compliant("TXN_APPLNT_ID", nds).compliant     # True
```

A passing check still records its reasons, so a review can see *why* a name was accepted:

```python
[(r.token, r.verdict.value, r.code.value) for r in is_compliant("TXN_APPLNT_ID", nds).reasons]
# [('TXN', 'pass', 'approved_abbrev'),
#  ('APPLNT', 'pass', 'approved_abbrev'),
#  ('ID', 'pass', 'approved_abbrev')]
```

A failing one names the token, the machine-readable code and the concrete thing to write instead:

```python
result = is_compliant("custmr_acct_num", nds)
result.compliant            # False
result.ends_in_class_word   # False
[(r.token, r.verdict.value, r.code.value, r.fix) for r in result.reasons]
# [('custmr', 'fail', 'unapproved_abbrev',  'CUST'),
#  ('acct',   'pass', 'approved_abbrev',    None),
#  ('num',    'fail', 'unapproved_abbrev',  'NBR'),
#  (None,     'fail', 'not_upper_snake',    'CUSTMR_ACCT_NUM'),
#  (None,     'fail', 'missing_class_word', 'CUSTMR_ACCT_NUM_VAL')]
```

Findings with `token=None` are about the whole name. Each `fix` is the smallest edit that clears
*its own* finding and nothing else, so a caller can apply one without silently accepting another —
the casing fix re-cases and does not touch the tokens; the class-word fix appends and does not
re-case.

**The false positive this ladder exists to avoid.** The naive rule for "is this an unapproved
abbreviation" is *two to five capital letters*, and it is wrong on `FRAUD`, `RISK`, `MODEL`, `SCORE`,
`OWNER`, `PARTY` and every other short English word a schema uses. The allow-lists are consulted
before any correction is proposed, and `short_full_word` and `common_keyword` are reason codes of
their own, because a reviewer reading "`FRAUD`: short full word, accepted" learns something and a
reviewer reading "`FRAUD`: unapproved abbreviation, did you mean `FRD`?" learns something false.

### `normalize`

Applies the corrections the vocabulary justifies, in one pass.

```python
from acronymkit.governed import normalize

normalize("custmr_acct_num", nds)            # 'CUST_ACCT_NBR'
normalize("custmrAcctNum", nds)              # 'CUST_ACCT_NBR'
is_compliant(normalize("custmr_acct_num", nds), nds).compliant   # True
```

It rebuilds the name from its tokens, so a name written without separators gains them
(`ADDRESS2LINE1` becomes `ADDRESS_2_LINE_1`) — the same boundary judgement every other verb makes.

**It is not a promise of compliance.** It does not append a missing class word, because the contract
assigns that to `to_physical_name` and a verifier that quietly extended a name it was asked to check
would be editing the caller's schema. And it never shortens a name. Run `is_compliant` on the result
to see what is left.

`normalize` and `is_compliant` share one decision ladder — `normalize` applies precisely the `fix`
that `is_compliant` reports — so the check and the correction cannot drift into two opinions about
the same name.

### When nobody pinned the collision

Most collisions are settled by a person, once, and recorded as a pin. `canonical_form_score` is what
happens when nobody has. It is a published penalty table over surface morphology, **lower wins**, and
it uses nothing external — no corpus, no frequency table, no model:

| penalty | condition |
|---|---|
| +100 | a 2-letter token whose candidate is a US state name |
| +50 | candidate ends in `-ing` |
| +40 | candidate ends in `-ly` |
| +30 | candidate ends in `-ed`, unless in `PAST_TENSE_NOUNS` |
| +20 | candidate ends in `-s`, unless in `SINGULAR_LOOKING_PLURALS` |
| +10 | candidate is more than one word |
| +1 per character | length tiebreak |

```python
from acronymkit.governed import score_breakdown
from acronymkit.governed.scoring import rank_candidates

score_breakdown("Idaho", "ID")
# {'us_state': 100.0, 'gerund': 0.0, 'adverb': 0.0, 'past_tense': 0.0,
#  'plural': 0.0, 'multi_word': 0.0, 'length': 5.0, 'total': 105.0}
score_breakdown("Identifier", "ID")["total"]        # 10.0
score_breakdown("Processing", "PROC")["gerund"]     # 50.0
score_breakdown("Cross Reference", "XREF")["total"] # 25.0

rank_candidates(("Identification", "Identity", "Identifier", "Idaho"), "ID")
# ('Identity', 'Identifier', 'Identification', 'Idaho')
```

The US-state rule is the one that has to be that large. Any catalog with address columns maps state
names to their postal codes, so inverting it drops `Idaho` into the candidate set for `ID` — and
`Idaho` is exactly the kind of candidate the rest of the table likes: short, singular, uninflected,
tripping no morphology rule. On length alone it beats `Identifier`, and a column named `ID` expands
to a state.

`rank_candidates` is what the resolver calls; the winner is element zero and the remainder is exactly
what `TokenExpansion.beat` records. Ties break on the candidate text, so a collision cannot resolve
one way today and the other way tomorrow because a catalog file was re-sorted.

This is a rule of thumb. It is written down, it is published, it is the same rule of thumb every
time, and every answer it produces reports `source: "scored"` so a consumer can treat it differently
from a recorded decision. That is the whole difference between a defensible default and a guess.

## Binding it once: `GovernedNamer`

`verb(subject, dictionary, policy=None, *, custom=None)` is the right shape for the functions and
the wrong one for the caller. A pipeline holds one vocabulary and one policy for its whole run, and
repeating both at every call site buys a flexibility nobody uses in exchange for three arguments
that can drift — one call site left on the default policy while the rest moved to a strict one is a
bug no type checker sees.

```python
from acronymkit.governed.namer import GovernedNamer

namer = GovernedNamer(nds, custom={"KYC": "Know Your Customer"})

namer.expand_identifier("CUST_ACCT_KYC_ID").phrase   # 'Customer Account Know Your Customer Identifier'
namer.is_compliant("CUSTMR_ACCT_NUM").compliant      # False
namer.normalize("custmr_acct_num")                   # 'CUST_ACCT_NBR'
namer.policy.mode.value                              # 'governed'
```

Every method forwards to the free function of the same name with the bound arguments filled in and
returns exactly what it returns. This class holds **no naming logic at all**, on purpose, so there
is no second place a governed decision can be made.

It is immutable, holds no cache and reads no clock, so one namer can be a module-level constant
shared by every thread of a service. `with_policy` and `with_custom` return new namers and leave the
receiver alone:

```python
strict = namer.with_policy(NamingPolicy.strict_length())
strict.policy.enforce_name_length     # True
namer.policy.enforce_name_length      # False
```

`expand_many` and `check_many` take the batch, which is the call shape a schema pipeline wants —
particularly across a process boundary, where the cost that matters is the number of round trips:

```python
tuple(e.phrase for e in namer.expand_many(["TXN_ID", "CUST_ACCT_ID"]))
# ('Transaction Identifier', 'Customer Account Identifier')
```

**They are the loop, and they say so.** Neither is faster per identifier than calling the single
verb in a comprehension. They earn their place by fixing two properties a future parallel
implementation would have to keep — result *i* is the answer for input *i*, and nothing is carried
from one item to the next — and not by being quick. Nothing is memoised: a memo keyed on the
identifier was prototyped, measured and left out, because what it buys is proportional to how often
a caller's schema repeats and nobody here has measured a real one. Wrap `expand_identifier` in
`functools.lru_cache` if yours does.

The five `from_*` constructors mirror the loaders below, so
`GovernedNamer.from_bundle("std", NamingPolicy.strict_length())` is the whole of the setup for most
callers.

## Building a vocabulary

Three loaders, in increasing order of how much a real catalog gives you.

**`from_mapping({token: long form})`** — the smallest useful vocabulary, and the shape to reach for
when trying the library out. A mapping cannot express a collision, so no entry gets a candidate set,
no entry gets a pin, and nothing is ever settled by score. Entries carry no `entry_id`, because a
mapping has no rows to point at and minting an identifier would make the audit trail claim a
provenance that does not exist.

**`from_long_to_short({long form: token})`** — the loader that matters, because it is the direction a
governed catalog is actually authored and stored in. Somebody writes down that *Transaction* is
abbreviated `TXN`. Read that way it is one answer per row and nobody authoring it has to think about
ambiguity. Inverting it is what makes the ambiguity visible:

```python
inverted = GovernedDictionary.from_long_to_short(
    {"Idaho": "ID", "Identification": "ID", "Identifier": "ID", "Transaction": "TXN"}
)
inverted.lookup("ID").to_dict()
# {'token': 'ID', 'canonical': 'Identifier',
#  'candidates': ['Idaho', 'Identification', 'Identifier'], 'pin': None,
#  'kind': 'ambiguous_pinned', 'keep_as_abbrev': False, 'class_word': None,
#  'entry_id': None, 'source': 'scored', 'confidence': 0.5,
#  'notes': "Derived by inverting a long-to-short catalog: 3 long forms shorten to this
#            token and none is pinned, so canonical_form_score chose 'Identifier' over
#            'Idaho', 'Identification'. Recording a pin replaces this rule of thumb with
#            a decision."}
```

The ambiguity was always in the catalog; reading it backwards is what surfaces it. A derived entry
reports `source: "scored"`, keeps its confidence below `1.0`, and records in `notes` what it chose
and what it beat. Recording a pin replaces the rule of thumb with a decision.

**`from_json(path_or_obj)`** — a path to a UTF-8 JSON file, or an already-parsed document. A `str`
argument is a **path**, never JSON text. Both on-disk layouts are accepted: a bare array of rows, or
an object carrying them under `"entries"` alongside whatever else the file records about itself. Keys
beginning with `_` are dropped from a row before construction, so a comment next to a row does not
fail the file. A malformed row raises `LexiconError` naming its position.

All three loaders take the same keyword-only extras as the constructor — allow-lists, class words,
glossary — because a governed standard keeps those in separate files from the catalog.

### Reading a standard off disk

Nobody hands out a JSON array of `GovernedEntry` rows. A governance function keeps its standard in a
workbook: a sheet of long form and preferred abbreviation, a sheet of tokens that may stand in a
physical name, a sheet of class words, a pin sheet, and a term glossary. `acronymkit.governed.loaders`
reads those, so the script that used to open five files and merge them lives in one place instead of
in every caller's repository.

```python
from acronymkit.governed.loaders import load_bundle

bundle = load_bundle("tests/fixtures/governed")
len(bundle.entries)                                # 68
len(bundle.approved_abbreviations)                 # 51
bundle.term_id_for("Customer Account Open Date")   # 'TRM-400001'
```

**Deliberately not called `nds`.** That is a different, larger catalog — the 68 rows above against
this page's 14 — and binding it to `nds` would silently re-point every example after this one,
including the audit below, whose unknown-token list and finding counts would then differ from what is
printed beside them. This is the only block on the page that builds a second
vocabulary, and until this round it did bind it to `nds`.

| Function | Reads |
|---|---|
| `load_bundle(path)` | a whole standard: a directory of the five files, or one JSON object carrying the same sections |
| `load_csv(path, token_column=…, canonical_column=…)` | a short → long CSV |
| `load_long_to_short_csv(path, long_column=…, short_column=…)` | a long → short CSV, inverted — the direction a real catalog is stored in |
| `load_term_index_csv(path, name_column=…, term_id_column=…)` | a glossary, as a plain mapping |

Four things these refuse to do, each for the same reason the rest of the package refuses to guess:

- **The column names have no defaults.** There is no conventional header for "the long form" — a
  real export says `Long Name`, or `Business Term`, or `Data Element Name` — so picking one would be
  this package guessing about a file it has never seen. The bundle is the single exception, and only
  because its layout is a convention this module *defines*; its file names and glossary columns are
  written down in `BUNDLE_FILES` and `DEFAULT_TERM_COLUMNS`, and both can be overridden.
- **Encoding is explicit at every read**, defaulting to `utf-8-sig` — plain UTF-8 with a tolerance
  for the byte-order mark Excel writes, which is the single most common reason a column "does not
  exist". Nothing consults the locale, so a container running under `LANG=C` reads the same bytes
  the same way a developer laptop does.
- **A half-filled row is skipped, not completed.** A row whose key or value cell is blank is a gap
  in the catalog, and turning it into an entry would claim to know something the file did not say.
- **The pin sheet fills gaps and never overwrites.** It supplies a pin or a candidate set only where
  the catalog row has none, and the merged row records in `notes` that it did. A token the two files
  pin *differently* raises, because choosing between two recorded decisions is not a loading
  question.

Duplicate keys resolve one way everywhere: **the last row wins**, which is what a Python mapping
does with a repeated key and what `GovernedDictionary` already documents for two catalog rows
carrying one token. Every failure raises `LexiconError` naming the file, and for a CSV the column
and the header row it actually found.

A caller overlay is deliberately *not* part of a bundle, even when a file beside it holds one. An
overlay is the caller's, not the standard's, and a loader that quietly applied one would return a
vocabulary that disagrees with the catalog with nothing at the call site to say so. Pass it as
`custom=`.

### What the dictionary answers

| Method | Question | Notes |
|---|---|---|
| `lookup(token)` | What row do you have? | Overlay outranks catalog. No pin, no score, no allow-list. |
| `resolve(token, policy)` | What does it mean under these rules? | The precedence chain lives here. |
| `is_approved(token)` | May it stand as written in a physical name? | Overlay, or `keep_as_abbrev`, or any of the three lists. |
| `class_word_for(token)` | Does it say what kind of value the column holds? | Matches both `DT` and `Date`. |
| `abbreviate(word)` | Which token is this word's governed short form? | The reverse index. |
| `term_id_for(name)` | Is this whole logical name a glossary term? | |

Approval is not the same as being known, and the pair is what makes a useful compliance message
possible: `NUM` has a row, expands to `Number`, and is not approved, because the standard's approved
form is `NBR`. That is why the check can say "write `NBR`" instead of "unknown token".

The reverse index resolves a long form claimed by two tokens with a written-down tie-break: prefer
the entry whose `canonical` is that long form, then the shortest token, then the token that sorts
first. `Number` is claimed by both `NBR` and `NUM`, which are the same length, so the third rule
decides it — `nds.abbreviate("Number").token` is `'NBR'`.

## Auditing a whole schema

The verbs answer one name at a time. A team adopting a standard has a different question on the
first day — *what will this do to our schema, and what is our catalog missing?* — and answering it
means calling `expand_identifier` once per column and reducing the results. That reduction is
mechanical, every team would write it slightly differently, and the differences would all be in the
same two places: what counts as an unknown token worth acting on, and what a round trip that does
not return its input actually means. So it is written once, in `acronymkit.governed.audit`.

```python
from acronymkit.governed.audit import audit_identifiers, render_audit, suggest_catalog_additions

corpus = ["CUST_ACCT_KYC_ID", "CUSTOMER_ACCOUNT_ID", "TXN_APPLNT_ID",
          "CUSTMR_ACCT_NUM", "KYC_REVIEW_DT"]
audit = audit_identifiers(corpus, nds)

audit.total, audit.distinct, audit.fully_known, audit.compliant     # (5, 5, 2, 1)
[(t.token, t.occurrences, t.identifier_count) for t in audit.unknown_tokens]
# [('KYC', 2, 2), ('ACCOUNT', 1, 1), ('CUSTOMER', 1, 1), ('REVIEW', 1, 1)]
[(f.code.value, f.occurrences) for f in audit.findings]
# [('unapproved_abbrev', 7), ('missing_class_word', 1)]
```

**The ranked unknown-token list is the part to look at first.** It is the catalog's backlog in
priority order — every token the vocabulary does not cover, how often it appears, in how many of the
corpus's identifiers, and an example column to look at — and it is the one output that turns "our
catalog is incomplete" into a finite list of rows to write. Ranking is total in both tables
(occurrences descending, then token or code ascending), so two runs over one corpus cannot order the
backlog differently.

The corpus is consumed exactly once, so a generator reading a schema export line by line is a
supported argument and is the shape to reach for on a large one. Identifiers are de-duplicated as
they stream — one warehouse repeats `LAST_CHG_TS` across every table it has — while the counts stay
over the corpus *as supplied*, because the question is how much of a schema is affected and not how
many distinct strings it contains.

### The round trip is reported three ways, not two

`to_physical_name(expand_identifier(x).phrase).physical != x` is the sharpest signal a corpus gives
about a catalog, and as a bare count it is misleading, because most of the names it flags are working
as designed:

| Bucket | Meaning |
|---|---|
| `round_trip_stable` | the name came back as it was written |
| `round_trip_corrected` | it came back as `normalize` would have rewritten it — the governed correction, and expected |
| `round_trip_inconsistent` | it came back as neither, which is the case worth investigating |

Only the third keeps its identifiers, on `round_trip_breaks`. One policy setting is taken out of the
comparison and only one, `append_class_word_when_missing`: rendering appends a class word and
`normalize` never does, so leaving it on would report every name that predates the standard as
evidence of a catalog disagreeing with itself. That shortfall is already reported once, by
`MISSING_CLASS_WORD`.

**Expect the middle bucket to hold nearly everything on a legacy schema, and `round_trip_inconsistent`
to read zero, and read that as the standard doing its job rather than as the trip coming back clean**
— a schema written before the standard existed is a schema full of unapproved tokens, every one of
them has an approved form the catalog names, and `corrected` is the bucket that says so.

### One inference, with a fence around it

Every number in this module is a count of something a verb already said. Exactly one thing is not.
When an unknown token is itself a **word the catalog governs** — a schema spelling out `CUSTOMER`
where the standard says `CUST` — the reverse index already knows it, and saying so is reading the
catalog rather than guessing at it:

```python
[(s.token, s.proposed_abbreviation, s.proposed_long_form, s.is_governed)
 for s in suggest_catalog_additions(audit)]
# [('KYC', None, None, False), ('ACCOUNT', 'ACCT', 'Account', False),
#  ('CUSTOMER', 'CUST', 'Customer', False), ('REVIEW', None, None, False)]
```

Three conditions fence it: the row's `canonical` must **be** that word rather than merely list it as
a candidate, the short form it names must itself be approved, and it must differ from the token.
Without the first, `LINE` reaches the `LN` row, whose canonical is *Loan*, and the audit proposes
rewriting a line number as a loan.

Everything else is left alone. `proposed_long_form` is `None` for every token the catalog is silent
about, which is most of them and is the point, and `CatalogSuggestion` has deliberately **no
confidence field**: a suggestion is a request for a decision, never an answer, and a number next to
it would invite somebody to accept the ones above a threshold.

`render_audit(audit, limit=…)` prints the whole thing as ASCII with fixed-width columns, so it
survives a log file, a CI pane and a Windows console equally, and a process that captured it can
paste it into a ticket. It is a view rather than a summary: every corpus-level count appears
somewhere in it, and the only things truncated are the two ranked tables, which say so when they are.

## From another process

The consumer this subsystem was built for is a schema-governance pipeline written in another
language. Answering one name takes microseconds and starting a Python interpreter takes tens of
milliseconds, so a pipeline that invokes a command per column pays the second cost tens of thousands
of times and almost none of the work is the answer. That ratio, not the per-name cost, is what
decides whether this library is adoptable across a process boundary.

```bash
acronymkit governed-batch --dictionary std/ --op expand < columns.txt > answers.jsonl
acronymkit governed-audit --dictionary std/            < columns.txt
```

`governed-batch` reads one record per line and writes one JSON object per line, streaming: records
are read, answered and written one at a time and nothing accumulates, so memory is flat in the size
of the corpus and a caller reading the pipe sees the first answer before the last question is asked.

| Envelope field | |
|---|---|
| `line` | 1-based input line number |
| `id` | present only when the input record carried one, echoed untouched |
| `input` | the subject as read, so a caller can correlate without relying on order |
| `ok` | whether this record was answered |
| `result` | the verb's own payload — the batch adds an envelope and no opinions |
| `error`, `error_type` | present instead of `result` when `ok` is false |

`--op` chooses the verb: `expand`, `physical`, `check`, `normalize`, or `audit`, which returns the
`IdentifierAudit` record for that one name. Input lines are either a bare identifier or a JSON object
carrying a string `identifier` and optionally an `id`; the rule between them is the first character,
which is decidable rather than heuristic, because no physical name begins with `{`.

Three properties are the contract:

- **A bad record is a record, not an exit.** One malformed line reports its own failure and the run
  continues; losing forty-nine thousand answers to one unparseable line is a worse outcome than any
  error message. The process still exits non-zero when any record failed, so it remains usable as a
  gate.
- **A finding is not a failure.** Under `--op check`, a name that does not conform comes back
  `"ok": true` with `compliant` false inside the result, and the exit status is unaffected.
  Reporting that is the job the command was given.
- **The record stream is ASCII and stdout carries nothing else.** Non-ASCII characters are
  `\u`-escaped so a record survives any console encoding on the far side, and the one-line summary
  (`{"op":…,"records":…,"failed":…,"skipped":…}`) goes to standard error, so every line of stdout is
  a record.

`--dictionary` accepts a bundle directory, a JSON catalog or a CSV on every governed command, with
`--dictionary-format`, `--columns` and `--delimiter` saying how to read it. `auto` takes a directory
as a bundle and refuses to guess a CSV's direction, for the same reason it never guesses
`long_to_short`.

`--policy` names one of the four presets and `--unknown [passthrough_titlecase|reject]` overrides
that policy's `unknown` field and nothing else, so `--policy strict_length --unknown reject` is still
a sentence a reviewer can read. Omitted, the preset decides — which matters because `neural_optin` is
the one preset that sets the field to anything else. Under `--unknown reject` a `governed-batch`
record whose identifier holds an unknown token comes back `"ok": false` with `"error_type":
"LexiconError"`, the run continues, and the process exits 1; see
[the batch's error record](notes/governed-json-contract.md) for the shape.

[docs/QUICKSTART_GOVERNED.md](QUICKSTART_GOVERNED.md) is the worked version of all of this, including
the migration seam: how to run this beside an existing implementation and diff the two.

## What the splitter accounts for

`split_identifier` classifies each character as an upper-case letter, a lower-case letter, a letter
with no case of its own, a digit, a separator, or none of those. The caseless class is its own thing
rather than folded into one of the cased ones: a CJK ideograph, a Hebrew or Devanagari letter takes
part in the letter/digit rules and in no case rule at all, because a case boundary means nothing next
to a character that has no case to change. The separator set is closed and written down, and
everything outside it is reported rather than dropped:

```python
from acronymkit.governed.tokenizer import ACCOUNTED_SEPARATORS, split_identifier_parts

sorted(ACCOUNTED_SEPARATORS)      # ['"', "'", '-', '.', '/', '[', ']', '_', '`']
```

— those nine characters, plus every character `str.isspace()` accepts. A separator and an
unaccounted character end the current token identically; the difference is that an unaccounted one is
also reported.

Seven of the nine are accounted for unconditionally. **The two square brackets are accounted for per
occurrence**, because a bracket is directional and is also the ordinary spelling of a subscript: it
is discarded where it is *doing* the quoting — an unnested matched pair, opening where a name could
open and closing where a name could close — and reported everywhere else.

```python
split_identifier_parts("[TXN_ID]").unaccounted                # ()
split_identifier_parts("[db].[schema].[TXN_ID]").unaccounted  # ()
split_identifier_parts("[my.column]").unaccounted             # ()
split_identifier_parts("value[x]").unaccounted                # ('[', ']')
split_identifier_parts("TXN_ID[0]").unaccounted               # ('[', ']')
split_identifier_parts("[a][b]").unaccounted                  # ('[', ']', '[', ']')
```

`[db].[schema].[TXN_ID]` is the row that rules out the obvious fix. Discard brackets only when they
wrap the *whole* identifier and the qualified-path case — the one the rule exists for — stops
reading. The test is on the character before an opener and the character after a closer, which are
the same tests the splitter already applies to decide a token has ended; `.` is not privileged, which
is why `[my.column]` reads as a quoted name rather than as two broken halves.

**The tokens do not move.** A bracket separates whichever branch it takes, so `value[x]` is
`('value', 'x')` as it always was, and what changed is that the answer no longer claims to have read
the whole name. Whether `x` should be a token of its own is a larger question — it is the "is a dot a
path separator" question in different clothes — and this package does not answer it.

```python
split_identifier_parts("TXN©ID")
# IdentifierParts(tokens=('TXN', 'ID'), unaccounted=('©',))

expand_identifier("TXN©ID", nds).phrase            # 'Transaction Identifier'
expand_identifier("TXN©ID", nds).unaccounted       # ('©',)
expand_identifier("TXN©ID", nds).is_fully_known    # False
```

The phrase is the same one a clean `TXN_ID` produces, and that is exactly the problem the field
exists for: answering "Transaction Identifier, fully known" for a column whose name also held a
character that was quietly discarded is a confident description of a name nobody wrote.
`is_fully_known` is `True` only when every token resolved **and** `unaccounted` is empty, so the one
bit a pipeline gates on still summarises the whole answer.

`unaccounted` is separate from `unknown_tokens` because the two are different work: an unknown token
is a catalog row somebody owes, and an unaccounted character is a question about the name itself that
no catalog row can settle.

Two smaller rules in the same family:

```python
from acronymkit.governed.tokenizer import split_identifier, strip_qualifier

split_identifier("1ST_TXN_DT")           # ('1ST', 'TXN', 'DT')
split_identifier("1STATE")               # ('1', 'STATE')
split_identifier('"TXN_ID"')             # ('TXN', 'ID')
strip_qualifier("nds.risk.SCORE_VAL")    # 'SCORE_VAL'
```

An ordinal suffix stays welded to its digit — `st`, `nd`, `rd`, `th`, matched on two characters, only
when no letter follows, and only when the two are not written lowercase-then-uppercase — so
`1ST_TXN_DT` names a first transaction date while `1STATE` still splits, because there the letters
are a word, and `1sT` splits to `('1', 's', 'T')`, because a capital after a lowercase letter is the
writer saying a new word starts there. `strip_qualifier` drops a leading `schema.table.`
qualifier from a fully qualified name, which is the shape an information-schema export arrives in.

`ACCOUNTED_SEPARATORS`, `IdentifierParts`, `split_identifier_parts` and `strip_qualifier` are defined
in `acronymkit.governed.tokenizer` and re-exported from `acronymkit.governed` alongside
`split_identifier`, so the shorter import works too and resolves lazily like every other name on that
package. None of the five reaches the top-level `acronymkit`, which carries only the eight names an
integration needs. A port has to reproduce the separator set and the ordinal suffixes exactly; the
rest of the splitter's implementation is not contract, and
[docs/notes/governed-json-contract.md](notes/governed-json-contract.md) says which is which.

**One divergence to know about before porting.** That contract note's character-class table still
classifies `[` and `]` as separators unconditionally and carries no `value[x]` row, so a port built
from it reports an empty `unaccounted` where this implementation reports `('[', ']')`. **This section
is the correct reading**, re-derived above against the shipped tokenizer; the note is the half that is
behind. The positional rule is wire-visible, D-034 in [docs/DECISIONS.md](DECISIONS.md) is its design
record, and applying it to the contract note is an open follow-up that is deliberately not being done
as a patch.

## Policies

The dictionary says what a token means. The policy says what to do with that. Four named presets,
and the field values are what the constructors actually produce:

| field | `governed_default` | `frequency_baseline` | `neural_optin` | `strict_length` |
|---|---|---|---|---|
| `mode` | `governed` | `most_common` | `governed` | `governed` |
| `allow_override` | `True` | `False` | `True` | `True` |
| `unknown` | `passthrough_titlecase` | `passthrough_titlecase` | `neural` | `passthrough_titlecase` |
| `neural_fallback` | `False` | `False` | `True` | `False` |
| `governed_hit_is_final` | `True` | `True` | `True` | `True` |
| `enforce_name_length` | `False` | `False` | `False` | `True` |
| `max_name_length` | `30` | `30` | `30` | `30` |
| `require_trailing_class_word` | `True` | `False` | `True` | `True` |
| `append_class_word_when_missing` | `True` | `True` | `True` | `True` |

A named policy is auditable and a loose bag of booleans is not: "this pipeline runs under
`governed_default`" is a reviewable sentence.

`governed_hit_is_final` is `True` in all four and no preset turns it off. That is the line the
neural opt-in does not cross: the statistical tier may fill a gap and may never overrule a governed
answer. In this release `UnknownPolicy.NEURAL` behaves as passthrough — this package contains no
statistical tier and importing one would break the Tier 0 promise the distribution makes — so the
opt-in is a declaration of intent that nothing yet acts on. `UnknownPolicy.REJECT` is the other
direction: an unrecognised token raises `LexiconError`, for pipelines where it means the catalog is
out of date and processing should stop.

No preset sets `REJECT`, because refusing unknown tokens is orthogonal to everything the four presets
distinguish — a caller who wants a stale catalog to stop their run wants it under whichever preset
they were already on. It is reached by copying the policy, or by `--unknown reject` on any governed
command:

```python
from acronymkit.governed import UnknownPolicy

strict_unknown = NamingPolicy.governed_default().model_copy(
    update={"unknown": UnknownPolicy.REJECT}
)
expand_identifier("TXN_KYC_ID", nds, strict_unknown)   # raises LexiconError, naming 'KYC'
```

**Only the expansion verbs read the field.** `is_compliant` and `normalize` never raise on an
unrecognised token, whatever `unknown` says, because reporting it is the answer they were asked for —
a check that stopped at the token it was asked to describe would have nothing left to describe. So
one policy shared across a pipeline raises out of `expand_identifier` and returns a finding out of
`is_compliant`, and that asymmetry is the contract rather than a gap in it. `audit_identifiers`
refuses `REJECT` outright, with a message saying so: listing the tokens a catalog is silent about is
the whole of what an audit does.

### `frequency_baseline` is a contrast arm, not a benchmark

It exists to be beaten. It ignores the pin and takes the first declared candidate — "most common",
implemented as a position rather than a hidden count, so the rule is inspectable:

```python
expand_token("ID", nds, NamingPolicy.frequency_baseline()).long   # 'Identification'
rank_candidates(nds.lookup("ID").candidates, "ID")[0]             # 'Identity'
expand_token("ID", nds).long                                      # 'Identifier'
```

Three mechanisms, three different answers, and only one of them is the standard. The result carries
a note saying the governed choice was not applied, so the audit record does not read as though the
catalog had agreed.

That is a comparison on fixture tokens chosen to make the rules disagree. It is **not** evidence
about any corpus and nothing measured on it transfers to one.

## The four invariants

Four claims, each with the test that carries it. Every example below was run against
`src/acronymkit/governed/` and the fixture corpus, and its output is pasted as it came.

| Invariant | The statement | Test that carries it, in `tests/test_governed.py` |
|---|---|---|
| **Round trip** | Expanding an identifier and rendering the phrase back yields the identifier's governed normal form. | `::test_the_round_trip_lands_on_the_governed_correction`, guarded by `::test_the_corpus_exercises_both_halves_of_the_round_trip` |
| **Idempotence** | `normalize(normalize(x)) == normalize(x)`, for every ASCII `x`, every policy **and every catalog**. Two premises hold it up — a token upper-cased splits back to itself, and a rejoined token splits back to the pieces it was joined from — and the first is false outside ASCII. The section below says where, and why the catalog is a dimension of the claim rather than a detail of the fixture. | `::test_normalize_is_idempotent_under_every_policy` and `::test_normalize_is_idempotent_over_catalog_shapes`, with `tests/test_governed_edge_cases.py::test_an_ascii_token_upper_cased_splits_back_to_exactly_itself` carrying the first premise and `::test_a_join_that_would_make_one_longer_number_is_refused` the second |
| **Length is a flag** | No policy, argument or code path shortens a name or drops a token. | `::test_no_policy_produces_a_shorter_token_list_than_any_other`, `::test_an_over_long_name_is_flagged_and_returned_whole`, `::test_an_unabbreviated_word_is_upper_cased_and_never_clipped` |
| **Governed hit is final** | A token the vocabulary contains resolves from the vocabulary under every policy. | `::test_policy_contrast_golden`, over `tests/fixtures/governed/golden/policy_contrast.jsonl`; the unknown half is `::test_a_held_out_token_is_reported_unknown_rather_than_approximated` |

### Round trip

Stated generously it is false, and stated exactly it is useful. For an identifier `x`:

```
to_physical_name(expand_identifier(x, catalog).phrase, catalog).physical == x
```

holds whenever every token of `x` resolves, the reverse index maps each token's long form **back to
that same token**, and the identifier already ends in a class word. The second condition is the whole
of the difficulty: expansion and abbreviation are not inverses and cannot be made so. Inverting a
long → short catalog produces a many-to-one map in *both* directions.

- **Two tokens claim one long form.** `DT` and `DTE` both mean "Date"; the reverse index sends
  "Date" to `DT`. So `DTE` → "Date" → `DT` — the trip does not return `DTE`, it *corrects* it.
- **A token's long form is not the one the index reversed.** `nds.abbreviate("Identity").token` is
  `'ID'`, and `expand_token("ID", nds).long` is `'Identifier'`, because *Identity* is a candidate the
  catalog carried and *Identifier* is the one it pinned.
- **A word nobody governs** passes through in both directions, so it round-trips on the strength of
  nothing.

None of these is a fault to patch. The sharper statement is the one worth testing, because it says
something true about the names where the identity does not hold instead of excluding them:

```
to_physical_name(expand_identifier(x, c).phrase, c).physical == normalize(x, c)
```

Over the 40 identifiers of the fixture corpus: 36 return themselves unchanged, and all 40 equal
`normalize`. The four that move are the ones carrying an unapproved token, and each comes back with
that token replaced by the approved one — which is the same rewrite `normalize` would have made.

```python
for ident in ["TXN_APPLNT_ID", "CUSTMR_ACCT_NUM"]:
    phrase = expand_identifier(ident, nds).phrase
    print(ident, "->", repr(phrase), "->", to_physical_name(phrase, nds).physical)
# TXN_APPLNT_ID   -> 'Transaction Applicant Identifier' -> TXN_APPLNT_ID
# CUSTMR_ACCT_NUM -> 'Customer Account Number'          -> CUST_ACCT_NBR
```

### Idempotence

```python
normalize(normalize("custmr_acct_num", nds), nds)   # 'CUST_ACCT_NBR'
```

It holds by construction rather than by luck. A rewrite is proposed **only when its target is itself
approved**, so the second pass finds an approved token, has nothing to propose, and returns it
unchanged; when the catalog offers nothing approved the token is left exactly as it was, which is
also a fixed point. Both branches terminate after one step, so no cycle of "unapproved A rewrites to
unapproved B rewrites to A" can exist. Verified on every identifier of the fixture corpus.

There is a second premise under that argument, and it is worth stating because leaving it implicit is
how it got broken once. `normalize` returns the tokens the splitter found, upper-cased and `_`-joined,
and the second pass splits that string again — so the argument is only sound while **a token, upper-
cased, splits back to exactly itself.** That holds for all ASCII and is asserted as a property over
arbitrary ASCII text; an earlier reading of the ordinal rule emitted the token `1s`, whose upper-cased
form `1S` splits into two, and `normalize("1sT")` moved on every pass until the rule was narrowed.

There is a third, and it is a premise about the **catalog** rather than about a name — which is why
it survived a test parametrised over every identifier in the corpus and every policy. Between the
split and the judgement sits the dictionary-aware digit rejoin, so what the second pass sees depends
on which rows exist. A joined token is safe only while splitting it returns the pieces it was joined
from: `1MM` does, because `split_identifier` reads it back as `('1', 'MM')` and the pass rejoins it
every time. `911` does not — a digit run has no internal boundary, so it reads back as one token —
and a catalog holding both `11` and `911`, which a municipal standard plausibly does, moved a name on
every pass and changed what the name said while it did:

```
# with catalog = GovernedDictionary.from_mapping({"11": "Eleven", "911": "Emergency"})
normalize("E_9_1_1", catalog)          # was 'E_9_11', then 'E_911';  now 'E_9_1_1'
expand_identifier("E_9_1_1", catalog)  # was 'E 9 Eleven' and then 'E Emergency';  now 'E 9 1 1'
```

The pass now refuses a join whose result is itself all digits, which is the only shape that does not
survive its own output. Two digit tokens can only be adjacent because something separated them —
consecutive digits are one run — so nothing that refusal removes was ever a repair of a split this
package introduced. The invariant is tested over catalog shapes as well as over names, with the
nesting catalog above among them.

It is **false outside ASCII**, and that limit is real rather than an oversight. `str.upper` is not
length-preserving and can produce characters that are not letters at all:

```python
normalize("ΐ", nds)                    # 'Ϊ́'  — one letter upper-cases to a letter and two marks
normalize(normalize("ΐ", nds), nds)    # 'Ι'  — the marks are unaccounted, so the second pass drops them
```

Fixing it would mean either applying Unicode normalisation, which rewrites text and is exactly what
the splitter refuses to do, or declining to upper-case a word. Both are worse than saying where the
invariant stops, so the exception is pinned by a test of its own next to the property.

### Length is a flag, never a truncation

`enforce_name_length` may only ever cause a *finding*. A pipeline that silently trimmed a name to
fit a platform limit would be inventing an identifier nobody governs, at the exact moment the caller
most needs to be told.

```python
long_name = "CUST_ACCT_PRIMARY_OWNER_PARTY_VERIFICATION_STAT_CD"   # 50 characters
result = is_compliant(long_name, nds, NamingPolicy.strict_length())
[(r.code.value, r.verdict.value) for r in result.reasons if r.token is None]
# [('exceeds_max_length', 'fail')]
normalize(long_name, nds, NamingPolicy.strict_length())
# 'CUST_ACCT_PRIMARY_OWNER_PARTY_VERIFICATION_STAT_CD'
to_physical_name("Customer Account Identifier", nds).truncated
# False
```

The corrected name comes back with every token still in it, and the same length it went in at. The
policy changed what was *reported*, and nothing else.

`PhysicalName.truncated` exists so the invariant can be read off the payload instead of inferred from
its absence. It is deliberately not validated to `False`: a field that cannot hold another value is a
constant rather than evidence. This package writes it, and this package writes it `False`.

The `EXCEEDS_MAX_LENGTH` finding offers the governed rewrite as its `fix`, and only when that rewrite
happens to fit. It never offers a name with a token removed, because no code path here can produce
one.

### Governed hit is final

A token the vocabulary contains resolves from the vocabulary, whatever the policy says:

```python
for preset in (NamingPolicy.governed_default, NamingPolicy.frequency_baseline,
               NamingPolicy.neural_optin, NamingPolicy.strict_length):
    r = expand_token("DT", nds, preset())
    print(preset.__name__, r.long, r.source.value, r.entry_id)
# governed_default   Date governed NDS-DT
# frequency_baseline Date governed NDS-DT
# neural_optin       Date governed NDS-DT
# strict_length      Date governed NDS-DT
```

Run across every one of the fixture catalog's 68 tokens under all four presets — 272 resolutions —
none comes back unknown and none comes back as a passthrough. Under `neural_optin` an *unknown*
token still passes through with `is_known` false and zero confidence, which is the shape of the
opt-in: it may fill a gap, and it may not overrule.

**This is true by construction and it is not a measurement.** A lookup table returns what is in the
lookup table. There is no percentage attached to it anywhere in this project, and there should not
be — see [Limits](#no-figure-belongs-next-to-this).

## Limits

### It is only as good as the dictionary it is given

Everything above is a property of the *machinery*. The answers are a property of the catalog. A
catalog with a wrong pin produces a wrong expansion, confidently, with a full audit trail pointing at
the row that made it wrong — which is the failure mode you want, but it is still a failure.
`confidence`, `entry_id` and `notes` exist so that the row can be found; none of them can tell you
the row is mistaken.

Two consequences worth planning for:

- **A derived entry is not a governed one.** `from_long_to_short` writes `confidence` below `1.0` on
  every collision it settles by score. Filter on an exact `1.0` when you want only what the standard
  confirms, and treat everything below it as a queue of decisions somebody still owes.
- **The catalog's silence is reported, not filled.** `is_fully_known` false on a schema-wide sweep is
  a work list, not an error.

### The reverse index can be ambiguous, and here is how it is resolved

Two tokens can legitimately claim one long form — an approved abbreviation and the unapproved one
people actually type, or two abbreviations from different eras of the same standard. The reverse
index picks one, by a rule written down rather than by file order:

1. prefer the entry whose `canonical` **is** that long form, over one that merely lists it as a
   candidate;
2. then the shortest token, because the shorter of two approved forms is the one a physical name
   wants;
3. then the token that sorts first — which decides nothing on merit, and is there so the rule is
   total.

Rule 3 is load-bearing more often than it looks: `NBR` and `NUM` are the same length, so `Number`
reaches `NBR` only because `'NBR' < 'NUM'`. If the tie-break order ever changes, that pair breaks
first. When you care which token wins, do not rely on the tie-break — mark the loser's row as the
unapproved expansion it is, and the first rule settles it.

### `canonical_form_score` is a heuristic tuned on English morphology

It will mis-rank words, and the mis-rankings are predictable:

- **It is English-only.** `-ing`, `-ly`, `-ed`, `-s` are English suffixes. A catalog with German,
  French or Spanish long forms gets the length tiebreak and nothing else, and the two exemption sets
  are lists of English words.
- **The exemption sets are lists, not morphology.** `Secured` and `Address` are exempt because they
  are written down; a governed term that is a noun ending in `-ed` or `-s` and is *not* on the list
  is penalised for its spelling.
- **Length is a proxy and sometimes the wrong one.** In the running catalog `Identity` (8 characters)
  outscores `Identifier` (10), so a schema whose `ID` really does mean *Identifier* gets the wrong
  answer from the score — which is exactly why the catalog's pin is consulted first and why the
  score fires only where nobody has ruled.
- **The US-state rule fires at token length exactly two.** A longer token that expands to a state
  name is a geography column doing its job, and is not penalised. Territories, the District of
  Columbia and the postal codes themselves are not in the set.

Every scored answer reports `source: "scored"` and its arithmetic is available from
`score_breakdown`. Treat those rows as the ones to review, not the ones to trust.

### The class word to append is not in the policy

`NamingPolicy.append_class_word_when_missing` says a rendered name lacking a class word should gain
one, and neither `NamingPolicy` nor `GovernedDictionary` carries a field naming *which*. The
`naming` module names a default, `DEFAULT_CLASS_WORD = "VAL"`, and appends it only when the caller's
own vocabulary designates that token — so a catalog whose neutral class word is something else gets
nothing appended, and `is_compliant` reports the shortfall instead. That is a documented gap, not a
design: a `NamingPolicy.default_class_word` field would settle it in one line.

### An allow-listed token keeps its shape inside a phrase

Rule 4 answers an allow-list member with the token itself, upper-cased and deliberately not Title
Cased, because an approved token is the governed physical form and re-casing it would be correcting
the standard. The visible consequence is a phrase that mixes cases:

```python
expand_identifier("CUST_ACCT_OPEN_DT", nds).phrase
# 'Customer Account OPEN Date'
```

If the phrase should say "Open", give `OPEN` a catalog row rather than only an allow-list entry.

### Empty and absent inputs

Nothing here raises on a blank cell, because a batch over a schema export should not stop on one.
`expand_token(None, ...)` returns an expansion whose `long` is `""`; `expand_identifier("", ...)`
returns empty tokens and an `is_fully_known` of `True`, vacuously, since no token failed — the empty
`tokens` tuple is what says nothing was expanded. `is_compliant("")` is the exception that reports
rather than raises: it fails with `EMPTY_NAME`.

### Two tokens with no honest reason code

A token holding no letters — the `1` and `2` of `ADDR_LINE_1_TXT` — gets **no compliance finding at
all**. `ComplianceReasonCode` has no member that describes an ordinal, and forcing it into
`SHORT_FULL_WORD` would be false while `UNAPPROVED_ABBREV` would fail every address line in a
schema. Reported as a gap rather than papered over.

Likewise, `EntryKind` has no member for a collision nobody pinned; such rows are filed as
`AMBIGUOUS_PINNED` with an empty `pin`, and the `pin` field alone says whether a decision exists.

### An unaccounted character is visible in one direction only

`IdentifierExpansion.unaccounted` is written by `expand_identifier` and by nothing else.
`ComplianceResult` and `PhysicalName` carry no equivalent, so a character the splitter could not
account for reaches `is_compliant` as a `NOT_UPPER_SNAKE` finding — or as nothing at all, when the
rest of the name is well formed — and reaches `to_physical_name` as nothing. A pipeline that gates
only on `compliant` will not see it; a pipeline that gates on `is_fully_known` will. That is a gap in
the DTO surface rather than a decision, and it is recorded here so it is not mistaken for one.

### A CSV catalog is a third of a standard

`load_csv` and `load_long_to_short_csv` read one sheet, and one sheet says what words *mean*. It says
nothing about which tokens may stand in a physical name and nothing about which of them say what kind
of value a column holds — so on a vocabulary built from a CSV alone, `is_approved` is false for every
token, no name ends in a class word, and `is_compliant` fails everything. Expansion works; compliance
does not, and `normalize` proposes nothing, because a rewrite is offered only when its target is
itself approved.

This is not a defect in the loader. It is the shape of the input, and the fix is the other two files
— `approved_abbreviations` and `class_words`, passed as keyword arguments or carried in a bundle. The
audit makes the shortfall obvious rather than leaving it to be discovered downstream: a corpus that
reports `compliant 0` under a CSV-only vocabulary is reporting the missing sheets.

### What the batch catches, and what that hides

`governed-batch` catches **every** exception a record raises, not a named set, and reports it as that
record's `error_type`. A `LexiconError` from a policy that rejects unknown tokens is a documented
outcome; anything else is a bug in this library. The batch keeps going either way, because the right
response to a bug on record 812 is still to answer the other forty-nine thousand — but the
consequence is that a systematic failure arrives as forty-nine thousand error records rather than as
one loud crash. The summary line's `failed` count and the non-zero exit status are what a caller
should watch; a run that answered nothing would otherwise look like a run that answered everything
badly.

`--op audit` costs four verb calls and a pile of model construction per record where `--op expand`
costs one, because it runs the corpus audit over a single name. It is opt-in for that reason, and a
schema-wide sweep is cheaper as one `governed-audit` than as fifty thousand `--op audit` records.

### An audit describes the corpus it was given

Every count in a `CorpusAudit` is over the names that were passed in. A corpus with no broken round
trips says the catalog is internally consistent over *those* names; it says nothing about the names
it does not contain, and nothing about a table that was not in the export. Neither does an empty
backlog mean a complete catalog — it means the corpus exercised no token the catalog is silent about.
The audit is a measurement of a schema against a standard, not of a standard.

### No figure belongs next to the lookup, and one now belongs beside the cut

Two things are easy to run together here, and only one of them is measurable at all.

**The lookup is exact by construction, which is a tautology rather than a result.** This project puts
no percentage anywhere near it: a lookup table returns what is in the lookup table. A reader who
takes "perfect accuracy on in-dictionary tokens" for a measurement has been misled about what was
measured, which is nothing — no baseline was run, and there is no experiment the figure could have
come from. The claim is written as an invariant, tested as an invariant, and carries no number.

**Where the cut falls is not a tautology, and it is now scored.** Every verb on this page has to
decide where one token ends and the next begins *before* any lookup happens, and that decision can
disagree with a human who segmented the same name. Two corpora of publisher-written captions — SEC
XBRL taxonomies and Socrata column labels — adjudicate it, and
[docs/EVALUATION.md](EVALUATION.md#the-governed-subsystem-its-first-accuracy-figures) carries the
table. Read its flatcase row and its headline row together or not at all: on a name carrying no
boundary mark there is nothing to cut on, the splitter refuses to invent one, and the flatcase row is
what that refusal costs. It is the price of the paragraph above, quoted in the same table.

The contrast with the rest of the library is the point, and *that* part is measured.
`acronymkit`'s contextual disambiguator scores 41.65<!--claim:disambiguation.sdu21.acronymkit.accuracy--> %
on SDU@AAAI-21 against 72.84<!--claim:disambiguation.sdu21.most_frequent.accuracy--> % for simply
always picking the most common expansion — it loses to the majority-class prior, badly, and
[docs/EVALUATION.md](EVALUATION.md) says so in full. In a governed setting that comparison does not
apply, because there is no distribution to have a majority in: there is a standard, and reproducing
it is the only defensible answer. Lookup is not merely better than a model here. It is the answer the
question has.

Nothing on **this page** is a benchmark result, and that is a statement about where the numbers live
rather than about whether any exist. `NamingPolicy.frequency_baseline()` is a contrast arm on fixture
tokens chosen to make two rules disagree, and the corpus counts quoted under
[the invariants](#the-four-invariants) describe that fixture corpus and nothing else. The cut-placement
figures are in `docs/EVALUATION.md`, gated through `bench/run_governed_gold.py --save`, and cited by
run id wherever they are quoted.

## See also

- [docs/QUICKSTART_GOVERNED.md](QUICKSTART_GOVERNED.md) — the same subsystem from the command line,
  from a CSV catalog to a whole schema in one process, with a migration diff at the end.
- [`tests/fixtures/governed/README.md`](../tests/fixtures/governed/README.md) — the worked corpus:
  the eight entry archetypes, the collision table, where the reverse index is not an inverse, and the
  open questions the fixtures found.
- [docs/notes/governed-json-contract.md](notes/governed-json-contract.md) — the JSON wire shape of
  every DTO and every fixture, written so a port can be validated against the same golden files.
- [docs/EVALUATION.md](EVALUATION.md) — what *is* measured in this library, including where it loses.
- [docs/DECISIONS.md](DECISIONS.md) — what was tried and rejected.
