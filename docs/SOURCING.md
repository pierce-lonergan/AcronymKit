# Sourcing one real glossary: the ask, the targets, the envelope, and the date it expires

[`docs/POSITIONING.md`](POSITIONING.md#it-requires-a-real-proprietary-glossary-and-this-project-does-not-have-one)
names, as the **first cost** of committing this library to being a governance instrument, that it
requires a real proprietary glossary and this project does not have one. That has been a standing
unknown for four phases. Under the commitment it stopped being a nice-to-have: the governed
subsystem's numbers are now the product, every published governed figure is taken with an **empty**
catalog, and the only measurement anybody has of whether a catalog is worth anything on a real schema
went the other way.

So this page is not a wish. It is a plan with an owner, three dated actions, an acceptance checklist
tight enough to ask with, a legal envelope, and **a date on which the plan's failure re-opens the
positioning** rather than being renewed.

It also ships the thing that changes the conversation. The ask used to be *send us your proprietary
glossary*. [`tools/byoc_eval.py`](../tools/byoc_eval.py) makes it *run this inside your firewall and
send us a JSON file of counts*. That is a different question, and it is the one most likely to get a
yes.

**How numbers are handled on this page.** Figures that are measurements of this library cite a run
id. Figures about third parties (PyPI, GitHub) and figures that size the ask cannot be cited, because
no benchmark runner can or should `--save` a property of somebody else's website — so they appear as
**fenced output with the command printed above them**, which is the convention
[`docs/CLAIMS-LEDGER.md`](CLAIMS-LEDGER.md) already uses, and every one carries its source and the
date it was read. [`docs/DECISIONS.md`](DECISIONS.md) D-052 is explicit that fencing removes a number
from the claims gate entirely; the command is printed with every block so that a reader can re-derive
it instead of trusting it, and that convention is the only thing separating a fence from hiding.

---

## 0. The premise, measured: there is no inbound lead

Any plan that assumed a warm contact would be a plan built on a false premise, so the premise was
measured first, on three instruments, on 2026-08-25.

**PyPI says something happened.**

```
https://pypistats.org/api/packages/acronymkit/overall   -- read 2026-08-25
category without_mirrors, window 2026-08-11 .. 2026-08-24, total 223

  2026-08-11    95      <- release day
  2026-08-12     8
  2026-08-13     2
  2026-08-14     6
  2026-08-15     2
  2026-08-16     4
  2026-08-17     4
  2026-08-18    34      <- spike
  2026-08-20     1
  2026-08-23    17      <- spike
  2026-08-24    50      <- spike
```

**GitHub says nobody looked, on any of those days.**

```
gh api repos/pierce-lonergan/AcronymKit/traffic/views    -- command output, read 2026-08-25
  count 38, uniques 25, window 2026-08-11 .. 2026-08-24

  2026-08-11   37 views / 25 unique     <- release day
  2026-08-12    1 view  /  1 unique
  every other day in the window        0 / 0

gh api repos/pierce-lonergan/AcronymKit/traffic/popular/referrers
  github.com   8 / 2       -- the only referrer at all
```

The three download spikes fall on `2026-08-18`, `2026-08-23` and `2026-08-24`. The repository
recorded **zero** views on each of those days. A download counter cannot tell a human from a scanner,
which is exactly why
[reversal two](POSITIONING.md#reversal-two-adoption-seeking-unblocks-the-day-adoption-becomes-legible)
refuses to accept any threshold on one; here a second instrument disagrees with the people-shaped
reading of the first.

**And the instrument reversal two *does* accept reads zero.**

```
gh api repos/pierce-lonergan/AcronymKit/issues           -- command output, read 2026-08-25
  6 open items, all pull requests, all authored by dependabot[bot]
gh api repos/pierce-lonergan/AcronymKit
  stargazers 0 | forks 0 | subscribers 0 | created 2026-08-09
```

No issue, no pull request, no fork, no star from any human who did not write this library. Reversal
two has not fired.

**One caveat that cuts the other way, and it is why the clone counter is not on the list above.**
GitHub counts an Actions checkout as a clone, this repository's CI ran heavily on the two days of the
largest download spikes, and the clone series shows it — so clones are contaminated by our own
builds and settle nothing in either direction.

**Conclusion, and it governs everything below: all sourcing is cold outbound.** Nothing on this page
may assume a contact, a referral or an inbound thread.

---

## 1. What is needed, tight enough to ask for

"A glossary" is not an ask. It produces an artifact of the wrong shape, and that has already happened
once: the August 2026 audit built catalogs by reading them off the display labels it then scored
against, which is circular by construction and is why its result — a voted catalog scoring no better
than an empty one — could not be asserted
([`docs/AUDIT-2026-08.md`](AUDIT-2026-08.md#1-does-a-governed-catalog-add-anything-on-a-real-schema)).

Three artifacts, thirteen criteria. Send the counterparty this list, not a paragraph.

### A. The glossary

1. **Shape.** Two columns: the short form, and the governed long form. `token,expansion`, one row per
   entry, CSV. Not a data dictionary of column descriptions, not a business term list with
   definitions — the abbreviation-to-words mapping their standard actually rules on.
2. **Size.** There is no useful floor on entry count, and asking for one would be inventing a number.
   The floor is on **firing**: the kit reports `firing.catalog_entries_that_fired`, and a glossary
   that moves nothing on their schema has told us about the overlap and not about catalogs.
3. **Independence from the gold.** The glossary must not have been produced by reading the labels in
   artifact C. The kit measures the observable proxy — `leakage.entries_present_in_gold_pct`, the
   share of expansions that appear verbatim as a word run inside the labels being scored — and a
   value near the top means this run cannot settle the question however the numbers come out.
4. **Provenance, in one sentence.** Who governs it, and roughly when it was last revised. No document
   needed. This is the criterion no code can check, so it is asked for in prose and believed.

### B. The schema

5. **The real machine identifiers** of a production schema: column names, element names, field names,
   as deployed.
6. **The whole schema, not a sample.** A hand-picked sample is a population chosen for agreeing, and
   this project has already published one lesson about corpora drawn around the system that scores
   them ([`docs/POSITIONING.md`](POSITIONING.md#why-refusal-is-worth-more-than-a-bigger-number--and-the-half-of-that-argument-that-is-confounded)).
7. **A cheap disqualifier, run first.** The kit reports
   `population.pairs_where_label_expands`. If that is near zero, the schema is already spelled out,
   no catalog can help on it, and the run stops there — which is a real finding obtained in an
   afternoon rather than a wasted quarter. Sizing evidence for how often that happens is in
   [section 5](#5-how-big-an-ask-this-is-sized-against-real-schema-data).

### C. The gold

8. **A human label per identifier that the schema already carries** — a display name, a business
   name, a report caption. Something that existed before this conversation.
9. **Not produced by applying the glossary to the identifiers.** This is the criterion that killed
   the last attempt, and it is the reason Socrata cannot settle the question no matter how many rows
   it has: the only catalog anybody could build there was inferred from the very labels used as gold.
10. **If the only label available *was* generated from the glossary, say so.** The run still measures
    where the identifier is cut, which is a real number, and it must not be quoted as measuring the
    catalog. Half a result honestly labelled beats a whole one that is wrong.

### D. The run

11. `python byoc_eval.py --self-test` passes on their machine. It drives a positive fixture where the
    catalog must win **and** a negative control where it must not, so a kit that always reported a win
    would fail on their own hardware before it ever touched their data.
12. `paired.discordant_pairs` reaches at least `54`. Below that the kit reports the run as
    underpowered rather than as a result — see [section 4](#4-the-number-that-decides-and-where-it-comes-from).
13. **They send the JSON and nothing else.** They read it first. It contains counts, percentages, two
    file digests, a timestamp and a version string, and the kit refuses to write it if it contains
    anything else.

---

## 2. Targets, and the trade — because a one-way ask fails

Every entry below names what they get. An ask that only names what we get is a favour, and cold
outbound has no standing to request favours.

### 2.1 Data-catalog and data-governance platforms

*Open source first: OpenMetadata, DataHub, Amundsen, Marquez. Then the commercial ones: Collibra,
Alation, Atlan, Informatica, Ataccama.*

**Why they say yes.** Every one of these products ships a *business glossary* feature, and every one
of them is sold on the premise that a curated glossary improves automated understanding of a column
name. Nobody has published a measurement of that premise. An independent, reproducible,
offline-runnable number about their own glossary is an asset they cannot buy and cannot generate
credibly themselves, because a vendor measuring its own feature is the shape this repository spends
whole documents refusing.

**The trade.** Co-authored result; named in [`docs/EVALUATION.md`](EVALUATION.md) as the first
real-glossary measurement this project has; and a tool their field engineers can run at a customer
site with nothing leaving the customer's network.

**Start here, and start with the open-source four**, for three reasons that are not about size: their
sample deployments ship a glossary *and* a schema, so the first run may need no agreement at all;
their maintainers are reachable through a public tracker, so the ask is an issue rather than an
email into a void; and **an issue thread with a named person in it is exactly the evidence reversal
two requires**, which makes this the only action on the page that could move two conditions at once.

### 2.2 Public-sector schema owners

*A US state open-data office; a city chief data officer; a national statistics office; the NIEM Open
community.*

**Why they say yes.** Their schemas are already public, so the legal envelope is close to empty and
the conversation skips a month of procurement. What they get back is the artifact they cannot easily
produce: `population.unknown_token_types_catalog_arm` counts the tokens in their own schema that
their own glossary does not cover, which is a governance backlog somebody is already trying to build
by hand. (Its sibling field, `..._empty_arm`, counts every token in the schema, because an empty
catalog covers nothing — the two are only different once a glossary is loaded, and section 5's run
loaded none.)

**Read the caveat before spending anybody's goodwill.** Public-sector identifiers are largely already
spelled out — see [section 5](#5-how-big-an-ask-this-is-sized-against-real-schema-data) — so this
category has the best legal envelope and the worst population. Screen with criterion 7 first. NIEM in
particular is likely a **negative** candidate: its Naming and Design Rules require spelled-out
camelCase component names rather than abbreviations, so a catalog has almost nothing to resolve
there. Disqualifying it in an afternoon is a good outcome, not a wasted one.

> NIEM naming rules read 2026-08-25 from
> <https://reference.niem.gov/niem/specification/naming-and-design-rules/3.0/niem-ndr-3.0.html>.
> The screen is the measurement; the reading is only the reason to run it first.

### 2.3 Standards bodies with an abbreviation dictionary

*ISO 20022 (through its registration authority or a member institution); ACORD; FpML; HL7; GS1; the
EDM Council's FIBO.*

**Why they say yes.** A standards body sells conformance, and conformance tooling has to decide
whether a name somebody wrote conforms to a vocabulary somebody else owns. That is precisely what
`is_compliant` and `to_physical_name` do. Evidence about whether their standard's abbreviations are
*recoverable from an identifier alone* is an argument about their own tooling, and it is an argument
nobody has published.

**ISO 20022 is the strongest shape on this page** and it is worth naming why. Its element tags are
genuinely abbreviated — `InstdAmt` for *Instructed Amount* — unlike the SEC XBRL taxonomies this
project already scores, where the LC3 convention makes the tag the label with its spaces removed and
so measures inverting a mechanical rule rather than resolving a vocabulary. And its abbreviation
dictionary is authored **independently of any one institution's schema**, which is exactly criterion
3. The catch is that the ISO-published tags and labels stand in the same generated relationship the
SEC arms do, so the run that matters is not *ISO tags against ISO labels* — it is **a bank's internal
legacy schema, with ISO 20022's abbreviations as the catalog and the bank's own business names as
gold**. Which needs a bank, and that is the next category.

> ISO 20022 abbreviation and tag-naming conventions read 2026-08-25 from public implementer guidance;
> the specific claim that a consolidated abbreviation list is published under a licence this project
> may use is **not verified** and is the first thing to check in action 3.

### 2.4 Financial-data vendors, banks and core-banking suppliers

*A payments processor mid-ISO-20022 migration; a market-data vendor; a core-banking platform.*

**Why they say yes.** An ISO 20022 migration *is* the mapping exercise this subsystem automates: a
legacy abbreviated schema on one side, a governed vocabulary on the other, and a team doing it by
hand. The kit tells them what share a deterministic expander would have got right with no model, no
training and no data movement — and hands them the unknown-token worklist for the remainder.

**Highest value, hardest door.** Do not open it first. Open it holding a completed run from 2.1 or
2.2, because "here is the result from another organisation and here is the tool that produced it" is
a different opening than "would you consider".

### 2.5 Health informatics

*A hospital data-warehouse team; an HL7/FHIR implementer; a clinical data-warehouse vendor.*

**Why they say yes.** Legacy clinical schemas are the most heavily abbreviated schemas in existence,
so if a governed catalog wins anywhere it wins biggest here — which also makes this the category most
likely to produce a decisive result rather than an underpowered one.

**And it is the category the kit was built for.** The legal envelope is the hardest of the five, and
"no data leaves your network, here is the guard that enforces it, here is the test that proves the
guard can fail" is the only opening that survives contact with a hospital's information governance
office. Lead with the tool here; the ask is a consequence of it.

### 2.6 One named anti-target

**Anyone whose glossary *is* the product they sell** — a commercial code-set or terminology vendor.
The answer is no, the answer is correctly no, and this plan's scarcest resource is the small number
of cold approaches the maintainer will actually make before stopping. A target list with no
exclusions is a list nobody ranked.

---

## 3. The legal envelope

### Path A — nothing moves, and this is the one to lead with

The library runs offline. That is not a claim on this page; it is a build gate — the `air-gap` job
installs from a local wheelhouse with no index, patches every socket primitive to raise, and drives
the whole public API inside a routeless network namespace with a positive control that fails the job
if the namespace is not really empty ([`docs/OFFLINE.md`](OFFLINE.md)). `tools/make_offline_bundle.py`
produces an installable bundle for a host with no route to PyPI.

So the counterparty's side of the exercise is:

```
pip install acronymkit                      # or the offline bundle, on an air-gapped host
python byoc_eval.py --self-test             # positive fixture and negative control, on their machine
python byoc_eval.py --template ./example    # the two input shapes, written out
python byoc_eval.py --schema schema.csv --catalog glossary.csv --out report.json
```

They read `report.json`. They send it. Nothing else moves, ever.

**What enforces that, rather than promising it.** `redaction_problems` declares, by report path, every
place a string may appear and what shape it may take, and `main` refuses to write the file if
anything else is present. It is not a scan for known-bad content — a column name, a glossary term or
a label matches no declared path at all. The guard is mutation-tested in
`tests/test_byoc_eval.py`, including through `main` rather than only by direct call, because a guard
tested in isolation proves the guard works and not that the entry point consults it. Its first draft
did **not** work, and the test that found that is the one worth pointing a counterparty's security
reviewer at.

**No NDA is required for a number.** What still has to be agreed is publication, and three options go
out in the first message rather than being negotiated later:

| Option | What we publish |
|---|---|
| Named | the organisation, the numbers, the date |
| Sector-anonymised | "a North American payments processor", the numbers, the date |
| Not published | nothing; the result decides reversal one internally and is never quoted |

**The third option has to be genuinely on the table or the offer is dishonest**, and it still closes
the question for the maintainer, which is the entire purpose. A counterparty who can say "run it, keep
it private, tell us privately whether it worked" is a counterparty with almost nothing to lose.

### Path B — they send the artifacts, and this is the fallback

Only if path A is refused, and then:

- **Do not draft an NDA.** Use theirs. Every organisation in section 2 has one and a mutual NDA
  drafted by the party with no legal function is a document that delays rather than protects.
- If they have none, point at a standard mutual-NDA template from their own procurement office or a
  bar association's public form library. Naming a specific template here would go stale and would be
  advice this project is not qualified to give.
- **This project must not become a data controller.** Received artifacts are held outside the
  repository — not in `data/`, because git-ignored is not the same as absent — used once, deleted on
  completion, and the deletion is recorded in the log in [section 6](#6-the-log-because-a-null-result-with-no-denominator-is-not-a-result).
- Nothing received under path B is committed, vendored, or registered in `bench/splits.toml`.

### The message that goes out

Short, because a long cold email is an unread cold email. This is the text, not a description of it:

> Subject: a measurement about your glossary that nobody has taken
>
> I maintain `acronymkit`, an open-source library that expands governed identifiers — `TXN_ID` into
> "Transaction Identifier" — against a catalog the caller owns, and reports *unknown* rather than
> guessing when the catalog is silent.
>
> Every accuracy figure it publishes is taken with an **empty** catalog, because no real
> data-standards glossary is public. So the library cannot currently say whether a governed
> vocabulary is worth anything on a real schema, and it says so on its own front page.
>
> I am not asking for your glossary. I am asking whether someone on your side would run a single
> Python script inside your network. It reads your identifiers, your glossary and the labels your
> schema already carries; it scores the expander with and without your vocabulary; and it writes a
> JSON file of counts and percentages. The script refuses to write that file if it contains any
> string from your data, and it ships with a test that proves the refusal works.
>
> If you send back that file, you get: the first independent measurement of whether your glossary
> improves automated column understanding, and a worklist of every token in your schema your standard
> does not cover. You choose whether the result is published named, published anonymised by sector,
> or not published at all.
>
> The script, and the full description of what it measures and what it cannot see:
> <link to `tools/byoc_eval.py` and `docs/SOURCING.md`>

---

## 4. The number that decides, and where it comes from

The two arms are paired — same identifiers, same code path, one difference — so the comparison is
McNemar's over the **discordant** pairs, the ones exactly one arm got right. Pairs both arms get
right and pairs both arms get wrong carry no information about which arm is better, and a
percentage-point gap quoted without the discordant count is unreadable.

```
python tools/byoc_eval.py --power        -- command output, not a benchmark measurement
two-sided exact binomial (McNemar), alpha 0.05, target power 0.8
  effect   first n at target   stable n at target   power at stable n
  0.6      199                 210                  0.8202
  0.65     90                  97                   0.8338
  0.7      49                  54                   0.8368
  0.75     30                  35                   0.8579
  0.8      20                  23                   0.8402

MIN_DISCORDANT_PAIRS = 54, the stable column at effect 0.7
```

**Two columns, because the exact test's power is not monotone in `n`.** Adding one discordant pair
moves the rejection region and can lose power; at effect `0.7` the first crossing is `49` and the
test dips back below target at `50` and at `53`. A criterion set at a sample size the test does not
hold is not a criterion, so `MIN_DISCORDANT_PAIRS` is the second column.

**The row count that produces `54` discordant pairs is deliberately not stated.** It depends on how
abbreviated the schema is and how much of it the glossary covers, and this project has measured
neither on any real proprietary schema — which is the whole reason this page exists. The criterion is
on discordant pairs; the kit reports the count it got; a short run is reported as underpowered rather
than dressed as a result.

---

## 5. How big an ask this is, sized against real schema data

The sizing question is: *of a real schema's columns, how many are even the kind of pair a catalog
could help on?* One public population can answer it, and the answer sets expectations for every
conversation in section 2.

This is a property of a corpus, not a measurement of the library, and it is **not** the gated
catalog-versus-empty comparison — that is a separate runner and this must not be quoted as it.

```
# re-derive: the cached Socrata catalog fetch, plus the kit
python - <<'PY'
import csv, json
d = json.load(open("data/governed_gold/socrata_80pages_v2.json"))   # fetched_on 2026-08-23
seen = {}
for field, label, portal in d["payload"]:
    key = (field or "").strip()
    if key and (label or "").strip() and key.casefold() not in seen:
        seen[key.casefold()] = (key, label.strip())
with open("socrata_schema.csv", "w", encoding="utf-8", newline="") as h:
    w = csv.writer(h); w.writerow(["identifier", "label"])
    for _k, (field, label) in sorted(seen.items()):
        w.writerow([field, label])
PY
python tools/byoc_eval.py --schema socrata_schema.csv --out socrata_report.json
```

```
socrata_report.json           -- command output, not a benchmark measurement, run 2026-08-25
                                 no catalog supplied, so one arm only. The cache behind it holds
                                 155,272 column occurrences across 216 portals; those two counts
                                 are properties of the fetch and not of the report

  pairs_scored                        69682
  pairs_where_label_expands           15842      22.73 of every hundred
  unknown_token_types                 24536      no catalog, so this is every token
  exact, empty catalog, all pairs     64.98 of every hundred
  exact, empty catalog, expanding     6.22  of every hundred
  wall clock                          about 3 seconds
```

Three readings, and the third is the one that changes the ask.

**About one column in four is a pair a catalog could help on.** The rest are already spelled out, and
on those the empty catalog is doing the whole job. Criterion 7 exists because of this line.

**On the quarter that remains, the empty catalog is bad** — six of every hundred exactly right,
against sixty-five over the whole population. That is the headroom a real glossary would be competing
for, and it is large. A schema-owner conversation should quote this: *on the columns your labels
actually spell out, the library with no vocabulary gets almost none of them right.*

**And this is why the shipped Socrata headline cannot settle the question.**
`bench/run_governed_gold.py` admits a pair only when the caption's alphanumerics case-fold equal to
the identifier's **and** the caption contains whitespace. The first half of that rule excludes every
one of the `15,842` expanding pairs by construction, so what it scores is drawn entirely from the
population a catalog **cannot** help on. It is a subset of that population and not the whole of it —
the whitespace half throws more away — which is worth saying exactly, because "the complement" is the
tighter phrasing and it is the wrong one. The gated figure on what survives is
91.37<!--claim:governed_gold.socrata.columns.all.exact_pct:.2f--> over
26,536<!--claim:governed_gold.socrata.columns.all.pairs:,d--> pairs, falling to
34.93<!--claim:governed_gold.socrata.columns.unmarked.exact_pct:.2f--> where the identifier carries
no boundary mark at all. Both are cut-placement figures. Neither is evidence about a catalog, and the
admission rule is why.

**An apparent disagreement, and it only half resolves.** `docs/AUDIT-2026-08.md` reports `87.3` of
every hundred real Socrata field/label pairs as already unabbreviated — an un-gated figure, from an
adversarial pass, over `164,652` pairs — which would put the expanding share near `12.7` rather than
`22.73`. Part of the gap is denominator: the block above counts **distinct identifiers** after
deduplication, which strips the repeated common columns most likely to be spelled out, and on
**occurrences** the same method gives `20.1` of every hundred expanding.

**That leaves a gap the denominator does not explain, and it is stated rather than smoothed.** The
audit's rule — alphanumeric case-folded identity between the field name and the label — is exactly
the rule the block above applies, and run over the cached Socrata fetch this tree actually holds it
gives `79.9` identical rather than `87.3`, on `155,272` occurrences rather than `164,652`:

```
python - <<'PY'      -- command output, not a benchmark measurement, run 2026-08-25
import json
def key(text): return "".join(c for c in text.casefold() if c.isalnum())
for name in ("socrata_80pages.json", "socrata_80pages_v2.json"):
    rows = json.load(open("data/governed_gold/" + name))["payload"]
    pairs = [(r[0], r[1]) for r in rows if (r[0] or "").strip() and (r[1] or "").strip()]
    same = sum(1 for f, l in pairs if key(f) == key(l))
    print(name, len(pairs), same, round(same / len(pairs) * 100, 2))
PY

  socrata_80pages.json      155272   124055   79.9
  socrata_80pages_v2.json   155272   124055   79.9
```

Both cached files are the same fetch serialised twice, so there is one population here and it is not
the audit's. **`87.3` does not reproduce on anything in this tree**, and this page cannot say whether
the audit fetched a different slice of the catalog or applied the rule differently, because the audit
figure is un-gated and its population was never saved. The *direction* survives — most real portal
columns are already spelled out either way — and the magnitude does not, which matters because the
magnitude is what section 2.2's warning is calibrated on. Recorded here; the fix belongs to whoever
owns that record.

---

## 6. The log, because a null result with no denominator is not a result

Operating rule 12 applies to outreach exactly as it applies to a benchmark: before reporting that
nothing worked, report how many times the thing under test executed. **Zero approaches means nothing
was measured, and it must be said in those words rather than reported as "there was no interest".**

Every approach gets a row on the day it is made, including — especially — the ones that get no reply.

| Date | Category | Organisation | Channel | Ask | Outcome |
|---|---|---|---|---|---|
| — | — | — | — | — | **none yet; approaches made: 0** |

---

## 7. The owner, the dates, and what happens when the dates pass

**Owner: the maintainer.** There is no one else. `docs/SECOND-READER.md` records the identical fact
about review — "There is no second person on this project" — and records it as honest rather than
solved. Naming a second owner here would be the same fiction in a different file.

### The first three actions

**Action 1 — Monday 2026-08-31. One issue, on one open-source data-catalog project.** OpenMetadata or
DataHub. Ask whether their sample glossary and sample schema can be run through
`tools/byoc_eval.py`, and offer the result back. One hour. It is first because it is the cheapest
action on the page, it needs no agreement of any kind, and it is the **only** action that could fire
[reversal two](POSITIONING.md#reversal-two-adoption-seeking-unblocks-the-day-adoption-becomes-legible)
as a side effect — a public thread with a named person in it is precisely the evidence that condition
requires and a download count is not.

**Action 2 — Monday 2026-09-07. Give the kit a front door.** A short `## Bring your own catalog`
section in `README.md` pointing at this page and at `tools/byoc_eval.py`. Section 0 says nothing has
ever arrived through the README, so this is a low-probability action on its own; it is on the list
because it costs an hour and because every message in action 3 needs a link to point at.

**Action 3 — Monday 2026-09-14. Five cold approaches, one per category in section 2**, using the
message in section 3, and one row in section 6's log for each on the day it is sent. Before sending
the standards-body one, verify the ISO 20022 abbreviation-list question flagged in 2.3; if it does
not check out, the approach changes to a member institution and the category becomes 2.4.

### The date

**2026-11-23**, ninety days from this page. On that date the log in section 6 is read and one of three
things is true.

**A result came back.** Run it against the acceptance checklist in section 1 before believing it, and
read `firing`, `leakage` and `discordant_pairs` before reading the headline. Then reversal one is
decided, in whichever direction the numbers point, and `docs/POSITIONING.md` is amended to match.

**Something came back but it cannot decide.** Underpowered, or high leakage, or a schema that turned
out to be already spelled out. **This is not failure and it must not be recorded as one** — it is a
measurement of the ask's difficulty, and it changes the ask (a larger schema, a more abbreviated
domain, a different counterparty) rather than the positioning. Reset the clock once, for ninety days,
and only once.

**Nothing came back.** Then the honest move is the one
[`docs/POSITIONING.md`](POSITIONING.md#reversal-one-the-lead-is-wrong-if-a-catalog-is-worth-nothing-on-a-real-schema)
has already written down, and it is not "keep trying". Reversal one is **re-opened**: the governed
subsystem's demonstrated value is provenance and compliance — the entry id, the source, the rule that
fired, the unknown-token worklist — and **not** expansion accuracy, the README leads with that
instead, and the change is recorded as having been forced by a dated plan that ran and did not work.
A positioning kept alive by an outstanding request that nobody answered is a mood, which is the exact
failure mode the reversal conditions exist to prevent.

---

## 8. What the claims gate can and cannot see on this page

This page lives in `docs/` for the mechanical reason
[`docs/POSITIONING.md`](POSITIONING.md#where-this-file-lives-and-why) gives: `tools/check_claims.py`'s
`SCAN_GLOBS` covers `docs/*.md` and its only root-level coverage is `README.md` and `CHANGELOG.md` by
name, so a root-level `SOURCING.md` would be the one user-facing document the claims gate never
reads — and an outreach plan is exactly the document class most likely to acquire a flattering figure
about how the outreach is going. Here, this page is absent from both ledgers, which means it is
allowed **zero** uncited armed numbers: every figure in prose cites a run id from its first line or it
is not in prose.

Operating rule 11 says a gate must be shown capable of failing where it runs. Five mutations, one at
a time, the gate run against each, the file restored from bytes read before the first mutation and
md5-verified:

```
python tools/check_claims.py, six runs -- one mutation applied to this file each time, the
gate run, the file restored from bytes read before the first mutation and md5-verified. The
digest is deliberately NOT printed here: publishing it would change the file and invalidate
the digest that was published. CPython 3.13.4 on win32; command output, not a benchmark
measurement. Line numbers are the mutated file's and move with any edit above them; rc and
"is the file named" do not.

  rc=0  control, unmutated                                            <file not named>
  rc=1  A  a cited value edited: 91.37 -> 99.99                       docs/SOURCING.md:449
  rc=1  B  that citation repointed at run id governed_gold.nope.*     docs/SOURCING.md:449
  rc=1  C  prose line added: "... accuracy reached 99.94 % ..."       docs/SOURCING.md:93
  rc=0  D  prose line added: "Median latency ... 41 microseconds"     <file not named>
  rc=0  E  "15842" -> "99999" inside section 5's fenced block         <file not named>
```

**A, B and C are the gate working.** A wrong cited value, a dead run id and a bare accuracy
percentage each turn the build red and name the line.

**D and E are the two holes, and they are the same two.** `latency` is not in the gate's arming
vocabulary and a spelled-out `microseconds` is not in its unit vocabulary, so an invented latency
claim on this page would never be seen — the blind spot `docs/DECISIONS.md` D-060 found in
`README.md`, reproduced on a third page rather than carried on that record's word. And every fenced
block on this page is outside the gate entirely, which D-052 says is mechanically indistinguishable
from hiding: section 0's traffic figures, section 4's power table and section 5's sizing block could
all be edited to say anything. The command is printed above each one so a reader can re-derive it,
and **that convention is the only thing separating those blocks from hiding.**

**This battery was run on a developer machine**, which is the evidence rule 11 exists to distrust, and
it is the same limitation [`docs/GATES.md`](GATES.md) records for the whole register. What it does
establish is the shape of the gate's coverage on this specific page, which no CI run would have told
anybody either.

**And the control row earned its place, which is the reason to always run one.** Two earlier passes of
this battery reported `rc=1` for D or for E — a false demonstration, and a flattering one, because a
red build on a mutation that should be invisible would have read as the gate catching more than it
does. Both times the cause was elsewhere in the tree: another workstream had reddened
`tools/check_claims.py` for its own reasons between one run of the battery and the next. The control
row says so on its own line, and a battery published without one would have shipped the wrong finding
twice.

---

## How this fails

**Nothing here measures that anybody wants this.** Section 2's "why they say yes" is a set of guesses
about other people's incentives, written by somebody who has never spoken to one of them. It is the
number-free assertion class [`docs/SECOND-READER.md`](SECOND-READER.md) exists for, it is the
load-bearing content of this page, and no gate in this repository can read a word of it.

**The kit has been run by zero strangers.** Every execution of `tools/byoc_eval.py` so far has been on
one Windows laptop, by its author, against fixtures its author wrote and one public corpus. The
mutation battery in `tests/test_byoc_eval.py` demonstrates the guards can fail in the process that
runs them, and CI runs those tests — but the environment the kit is *for* is a stranger's machine
behind a firewall this project can never reach, so operating rule 11's strict reading is not
satisfied and cannot be until somebody outside runs it.

**The `54` is anti-conservative, and this is the most load-bearing weakness on the page.** McNemar's
test assumes the discordant pairs are independent. Columns in one schema are not: a single catalog
entry decides every identifier containing that token, together, in the same direction. Measured on the
real Socrata population above, **`56.99` of every hundred identifiers contain at least one of the
hundred commonest token types** — so the effective sample size is materially smaller than the
discordant count, and the p-value the kit prints is optimistic by an unmeasured amount. The right fix
is a clustered test with the token as the cluster; it is not built, and until it is, a result close to
the threshold must be read as undecided rather than as significant.

```
# re-derive the concentration figure, using the CSV built in section 5
python - <<'PY'
import csv, sys
sys.path.insert(0, "src")
from collections import Counter
from acronymkit.governed import GovernedDictionary, expand_identifier
empty = GovernedDictionary({})
rows = list(csv.DictReader(open("socrata_schema.csv", encoding="utf-8-sig")))
per_row = [{t.raw.casefold() for t in expand_identifier(r["identifier"], empty).tokens} for r in rows]
counts = Counter(token for tokens in per_row for token in tokens)
top = {token for token, _n in counts.most_common(100)}
touched = sum(1 for tokens in per_row if tokens & top)
print(len(rows), len(counts), touched, round(touched / len(rows) * 100, 2))
PY
```

```
                    -- command output, not a benchmark measurement, run 2026-08-25
  69682 identifiers | 24536 distinct token types | 39709 touched | 56.99 of every hundred
```

**The circularity check is a proxy and it is defeatable without anybody intending to defeat it.** It
looks for each expansion as a *contiguous word run* inside some label, so a glossary genuinely read
off the labels and then reworded slips past: map `QTY` to "Quantity Ordered" where every label reads
"Ordered Quantity" and the run never matches, though the glossary was still derived from the gold. It
catches the verbatim case and misses the paraphrased one, and criterion 4 asks in prose because of
that.

**The redaction guard protects strings, not the information in counts.** A twelve-column schema plus
an unknown-token-type count is a smaller anonymity set than it looks. For a large schema this does not
matter; for a small one it might, and nobody has bounded it.

**The ninety-day fallback is a promise about future behaviour with no mechanism behind it.** Nothing
turns red on 2026-11-23. It is the same shape as *"nobody optimises extraction again"*, which
`docs/POSITIONING.md` already names as unmechanised — and it is worse here, because the person who
would have to execute the reversal is the person whose decision it reverses.

**The whole plan has one owner and one channel.** If the maintainer does not send the messages in
action 3, every number on this page stays exactly as it is and the log in section 6 keeps reading
zero. That is not a risk this document can mitigate; it is the shape of a project with one person in
it, stated rather than designed around.

---

**See also:** [`docs/POSITIONING.md`](POSITIONING.md) — the commitment, its four costs and its three
reversal conditions · [`tools/byoc_eval.py`](../tools/byoc_eval.py) — the kit, and what it measures ·
[`docs/AUDIT-2026-08.md`](AUDIT-2026-08.md#1-does-a-governed-catalog-add-anything-on-a-real-schema) —
the unknown this page exists to close · [`docs/OFFLINE.md`](OFFLINE.md) — the air-gap evidence the
path-A offer rests on · [`docs/EVALUATION.md`](EVALUATION.md) — where a returned result gets published.
