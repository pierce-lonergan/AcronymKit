# Governed-expansion fixtures — Northwind Data Standards (NDS)

**Every file in this directory is synthetic.** "Northwind Data Standards" is a
fictional catalog. The entry ids, term ids, column names, vendor codes and
domain labels were written for this test suite and describe no real system.
The corpus is modelled on the *shape* of a governed schema catalog — a
short-form token, one governed long form, a pin where the long forms collide,
a class word on the trailing token, an audit handle on every row — and not on
the contents of any catalog. Nothing here should be read as a description of
anyone's data.

## What this corpus is for

`acronymkit` generates acronyms from phrases and pulls definitions out of
prose. The governed package does the opposite and simpler thing: given a bare
column token such as `TXN_ID` and a governed vocabulary, return
`Transaction Identifier` — deterministically, with no sentence to disambiguate
against, and with a record of which catalog entry produced each word.

That makes the dictionary the ground truth, so these fixtures *are* the
specification of correct behaviour. Nothing downstream is allowed to infer an
answer that is not in here, and an unknown token has to come back as unknown
rather than as a guess. The corpus is built so that each of those claims has
something concrete to be checked against, including the awkward cases where a
plausible-looking heuristic gets the wrong answer.

None of these files are shipped: `MANIFEST.in` carries only `*.py` out of
`tests/`, and the wheel contains `src/acronymkit` alone. The fixture corpus
therefore has no effect on the wheel budget.

## Files

| File | What it is | What it exercises |
|---|---|---|
| `dictionary.json` | 68 `GovernedEntry` rows plus a `reserved_absent` list | Every `EntryKind` archetype; the collision sets; the reverse index |
| `ambiguity_pins.json` | The pin sheet, `token -> {candidates, _pin}` | That the pin in the dictionary and the pin sheet are the same decision; `_pin: null` for a collision governance has not decided |
| `class_words.json` | Class-word abbreviations, their spelled-out forms, trailing-token policy | `class_word_for`, `ends_in_class_word`, `append_class_word_when_missing` |
| `allowlist.json` | The three allow-list sets and the order they are consulted in | `is_approved`, the compliance reason codes, allow-list membership with no dictionary row |
| `term_glossary.csv` | 36 glossary rows | `term_index` / `term_id_for`, whole-name lookups, placeholder term ids with reduced confidence |
| `policies.json` | The four named policies, field by field | That each named constructor still produces the values written down here |
| `custom_overlay.json` | Two layers of caller-supplied acronyms | Custom precedence, `allow_override`, `with_custom` composition, last-wins layering |
| `corpus_sample.txt` | 40 UPPER_SNAKE identifiers, median length 80 characters | Idempotence and ratchet tests; long names for the length-flag invariant |

## The eight archetypes

Each archetype is a distinct code path, so each one has rows of its own — bar
`passthrough`, which is the absence of a row and is covered by held-out tokens
instead. The counts below are what is in `dictionary.json` today.

| `EntryKind` | Rows | Examples | Why it is here |
|---|---|---|---|
| `class_word_abbrev` | 20 | `DT`→Date, `CD`→Code, `NM`→Name, `AM`→Amount, `TS`→Timestamp, `IN`→Indicator | The trailing token of a governed physical name. `ID` is also a class word but is filed under `ambiguous_pinned`, so the class-word map has 21 members and this table has 20 |
| `approved_abbrev` | 13 | `TXN`, `EFF`, `DTL`, `APPLNT`, `BRTH`, `XREF`, `1MM` | `keep_as_abbrev` is true: the token is the governed physical form. Expansion still returns the long form; what changes is that the token may stand in a column name |
| `ambiguous_pinned` | 11 | `ID`, `SRC`, `PROC`, `CHG`, `SEC`, `ACT` | A collision the catalog resolved with a pin — and two rows (`CTL`, `REG`) where it deliberately did not |
| `domain_pin` | 4 | `DEP`, `PROD`, `APP`, `LN` | The pin contradicts the catalog's own default. This is the "our pin beats the catalog" case |
| `proper_noun_acronym` | 5 | `ZIP`, `ABA`, `ATM`, `NDS`, `GLX` | Must never be expanded. `ZIP` stays `ZIP`; it is not "Zone Improvement Plan" and it is not Title Cased to `Zip` either |
| `short_full_word` | 7 | `FRAUD`, `STATE`, `PHONE`, `PARTY`, `OWNER`, `MODEL`, `RISK` | Real English words that a "2–5 uppercase letters means abbreviation" rule flags as abbreviations. This is a regression guard for a false-positive class, not a nicety |
| `unapproved_expansion` | 8 | `CUSTMR`, `ACCNT`, `TRANS`, `AMNT`, `NUM`, `DTE`, `PYMNT`, `EFFCTV` | Known, expandable, and not permitted in a physical name. All carry confidence below 1.0 |
| `passthrough` | 0 | `KYC`, `WLT`, `ESCR`, `PRTFL`, `TRNCH`, `LGCY`, `WRKFLW`, `SBLDG` | Passthrough is the *absence* of a row, so it has none. The eight tokens listed under `reserved_absent` in `dictionary.json` are held out for it, and all eight appear in `corpus_sample.txt` |

`EntryKind.PASSTHROUGH` therefore only ever appears on a `TokenExpansion`,
never on a `GovernedEntry`.

## How the three resolution mechanisms disagree

Candidates are ordered by corpus frequency, most frequent first, because
`NamingPolicy.frequency_baseline()` reads position 0 and ignores the pin. The
table below is what each mechanism selects. It was produced by running the
penalty table from the contract over these candidate sets; a test should assert
it rather than trust it.

| token | `frequency_baseline` takes | `canonical_form_score` takes | the pin says |
|---|---|---|---|
| `ID` | Identity | Identity | **Identifier** |
| `SRC` | Sourcing | Source | Source |
| `PROC` | Processed | Process | Process |
| `MO` | Monthly | Month | Month |
| `REC` | Receipt | Record | Record |
| `CHG` | Change | Change | **Charge** |
| `SEC` | Securities | Section | **Security** |
| `ACT` | Active | Action | **Activity** |
| `ORIG` | Original | Original | **Origination** |
| `DEP` | Department | Deposit | Deposit |
| `PROD` | Production | Product | Product |
| `APP` | Approval | Approval | **Application** |
| `LN` | Line | Line | **Loan** |
| `CTL` | Controlling | Control | *(unpinned)* |
| `REG` | Registration | Regional | *(unpinned)* |

Seven tokens have a pin that neither of the other two mechanisms would reach.
That is the point of the corpus: in a governed setting the dictionary is the
answer, and these rows are where a scorer or a most-frequent rule visibly is
not.

`ID` carries eight candidates and covers every penalty row except `-ly`: a
plural (`Identities`), a past participle (`Identified`), a gerund
(`Identifying`), a multi-word form (`Internal Document`) and a US state
(`Idaho`). The `-ly` penalty is covered by `MO`, which is also the second state
case. `SEC` is the row that exercises both exception sets at once. `Securities` is in
`SINGULAR_LOOKING_PLURALS` and `Secured` is in `PAST_TENSE_NOUNS`, so both
escape the penalty that would otherwise have settled the row: `Secured` and
`Section` tie at 7.0, and `Section` takes it lexicographically. (An earlier
draft of this table said `Secured` won that tie. It does not — `Section` sorts
first — and the correction is left visible because the row exists precisely to
make a change in the tiebreak observable.)

`CHG`, `SEC`, `ACT`, `LN` and `REG` all resolve through the lexicographic
tiebreak, so a change to that rule shows up here immediately.

`frequency_baseline` is a contrast arm on this fixture data and nothing more.
It is not a benchmark and says nothing about any real corpus.

## The reverse index, and where it is not an inverse

`abbreviate(word)` is built from `canonical` plus every `candidate`, so several
words claim the same token and two tokens sometimes claim the same word. The
documented tie-break is: prefer the entry whose `canonical` matches exactly,
then the shortest token, then lexicographic order.

Eight long forms are claimed by two tokens each, and in every case the approved
abbreviation is the one that wins:

| long form | claimed by | winner | decided by |
|---|---|---|---|
| Account | `ACCNT`, `ACCT` | `ACCT` | token length |
| Amount | `AM`, `AMNT` | `AM` | token length |
| Customer | `CUST`, `CUSTMR` | `CUST` | token length |
| Date | `DT`, `DTE` | `DT` | token length |
| Effective | `EFF`, `EFFCTV` | `EFF` | token length |
| Payment | `PYMNT`, `PYMT` | `PYMT` | token length |
| Transaction | `TRANS`, `TXN` | `TXN` | token length |
| Number | `NBR`, `NUM` | `NBR` | lexicographic — the tokens are the same length |

`Number` is the row that needs the third rule. If the tie-break order ever
changes, `Number` breaks first.

**Round-trip asymmetry.** Expansion and abbreviation are not inverses, and the
corpus contains the cases where that is visible. Any non-canonical candidate
reverses to its token, and expanding that token gives the pin instead:
`abbreviate("Line")` is `LN`, but `expand("LN")` is `Loan`. The same holds for
`Change`→`CHG`→Charge, `Department`→`DEP`→Deposit, `Identity`→`ID`→Identifier,
`Approval`→`APP`→Application and about forty more. This is a property of the
design, not a fault in the fixtures: a governed catalog records what a token
*means*, and several words can legitimately point at the same token. A
round-trip test should assert the asymmetry rather than assume it away.

`term_glossary.csv` deliberately avoids every one of these words, so each
glossary row does round-trip cleanly and a mismatch there is a real failure.

## Allow lists

`consult_order` is `approved_abbreviations`, then `common_keywords`, then
`short_full_words`. `TOTAL` is in two sets on purpose: both readings are
defensible, so the order has to decide, and a test can see that it did.

Membership without a dictionary row is its own path — the token is approved and
its expansion is the token itself. `MGMT`, `MSG` and `SVC` cover it for
approved abbreviations; fifteen of the short full words and every common keyword
cover it too.

`ZIP`, `ABA`, `ATM`, `NDS` and `GLX` are approved but appear in none of the
three sets. They are approved through their `keep_as_abbrev` rows, which leaves
their compliance verdict free to carry the proper-noun reason code instead of
the generic approved-abbreviation one.

Class-word abbreviations carry `keep_as_abbrev: false` and are listed in
`approved_abbreviations`. Expanding `DT` therefore reports `source=governed`,
which is what it is, while `is_approved("DT")` is still true through the allow
list. The alternative — `keep_as_abbrev: true` — would have reported
`source=approved` for a token that does expand, which reads as though `DT` were
left alone.

## Custom overlay

Two layers, applied in `layer_order`, later wins.

| token | form | in the catalog? | what it shows |
|---|---|---|---|
| `ID` | bare string | yes, pinned to Identifier | An override that contradicts a governed pin. Refused under `allow_override=false` |
| `DEP` | full entry object | yes, domain-pinned to Deposit | Same, with its own `entry_id` and a confidence below 1.0 so overlay provenance is visible |
| `TXN` | bare string | yes, an approved abbreviation | An override introduced by the second layer only |
| `KYC` | bare string, in both layers | no — it is in `reserved_absent` | Overriding nothing is not an override, so it applies even under `allow_override=false`. Different long form in each layer |
| `WLT` | full entry object, in both layers | no | Whole-entry replacement across layers, not a field-by-field merge |

Applying `house_style` then `project_local` gives `KYC` → Know Your
Counterparty and `WLT` → Wallet Account (`LOCAL-WLT-0002`). Applying them in
the opposite order gives Know Your Customer and Wallet (`LOCAL-WLT-0001`).
Overlay entry ids use the `LOCAL-` prefix, never `NDS-`, so provenance shows at
a glance that an answer did not come from the catalog.

## Glossary

`term_glossary.csv` holds 36 rows. Term ids come from a synthetic block
starting at `TRM-400001`. Three rows use the `TRM-9000xx` placeholder block for
terms that are proposed rather than approved, and every one of those carries a
confidence below 1.0.

Each row's `physical_name` is exactly what a word-by-word reverse mapping of
`logical_name` produces, every token in it is approved, and the trailing token
equals the `class_word` column. That is checked, not assumed.

## Corpus sample

40 UPPER_SNAKE identifiers, median length 80 characters, longest 94, with three
short names kept in so the length distribution is not artificial. Most run past
`strict_length`'s 30-character limit, which is what gives the "flag but never
truncate" invariant something to be asserted against.

The corpus uses eleven tokens with no governed answer: the eight `reserved_absent`
tokens plus `DISBURSEMENT`, `ISSUER` and `TERMINAL`, which are ordinary English
words the catalog has simply never recorded. Everything else resolves. One
identifier carries both `LINE_1` and `LINE_2` for the letter/digit split, and
another carries `1MM`, the digit-leading token that has to survive as one token
rather than being split into `1` and `MM`.

## Divergences from the contract, and open questions

These were resolved the obvious way and are flagged rather than hidden.

1. **`dictionary.json` is an object, not a bare array.** The entry list is
   under `entries`, alongside `_meta` and `reserved_absent`. `from_json` should
   accept both shapes. The contract does not fix the on-disk layout.
2. **`term_glossary.csv` carries an eighth column, `confidence`.** The seven
   specified columns have nowhere to record it, and §10 of the contract
   requires placeholder term ids to carry a confidence below 1.0. The first
   seven columns are in the specified order, so a reader that selects by name
   is unaffected.
3. **There is no `EntryKind` for an unpinned collision.** `CTL` and `REG` are
   filed as `ambiguous_pinned` with `pin: null` and `source: scored`. The kind
   names the archetype; the `pin` field alone says whether a pin exists. An
   `AMBIGUOUS_UNPINNED` member would say it better.
4. **Nothing consumes `class_words.json`'s `trailing_token_policy`.**
   `GovernedDictionary` takes only an abbrev→full mapping, and `NamingPolicy`
   has `append_class_word_when_missing` but no field for *which* class word to
   append. The fixture records `default_class_word: "VAL"`; some field has to
   own it.
5. **A multi-word canonical cannot be reached word by word.** `XREF` expands to
   `Cross Reference` and `1MM` to `One Million`, but §8 describes
   `to_physical_name` as abbreviating each word, which turns "Cross Reference
   Identifier" into `CROSS_REFERENCE_ID` and never into `XREF_ID`. Both tokens
   are kept in the dictionary — they are what a real catalog looks like, and
   `Internal Document` among `ID`'s candidates is what exercises the multi-word
   scoring penalty — and both are kept out of the glossary until the mapping
   direction is settled.
6. **Rule 4 results have no stated `is_known`.** An allow-list member with no
   dictionary row resolves to `APPROVED` with the token as its own expansion.
   These fixtures assume `is_known` is true for it, since only rule 6 —
   passthrough — is described as unknown.
