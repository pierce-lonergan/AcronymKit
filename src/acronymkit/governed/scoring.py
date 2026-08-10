"""Collision scoring for the inverted governed index.

Why a score exists at all
-------------------------
A governed catalog is authored and stored in one direction: long form to short
form, one approved row per term. ``Transaction -> TXN``. ``Date -> DT``.
``Identifier -> ID``. Read that way it is a mapping with one answer per row, and
nobody authoring it has to think about ambiguity.

Expansion reads it the other way, and the inverse of a long → short catalog is
not a mapping with one answer per key. Distinct long forms shorten to the same
short form constantly — ``Identifier``, ``Identification`` and ``Idaho`` all
shorten to ``ID`` — so inverting the catalog turns those rows into a *collision
set*: one token, several candidate expansions, and no row anywhere saying which
one a bare ``ID`` in a column name stood for.

Most collisions are settled by a person, once, and recorded as
``GovernedEntry.pin``. This module is what happens when nobody has: the catalog
carries the ambiguity, no one has ruled on it, and an answer is still owed.

What the score is allowed to use
--------------------------------
Nothing external. There is no sentence around the token, no document, no corpus
and no frequency table — being context-free is the premise of the package, not a
limitation of this function. The only evidence in the room is the shape of the
candidate string and the shape of the token, so the score is a penalty table
over surface morphology and nothing more.

**Lower wins.** Penalties are additive and one candidate may attract several.
The table:

===================  ==========================================================
penalty              condition
===================  ==========================================================
+100                 a 2-letter token whose candidate is a US state name
+50                  candidate ends in ``-ing``
+40                  candidate ends in ``-ly``
+30                  candidate ends in ``-ed``, unless exempt
+20                  candidate ends in ``-s``, unless exempt
+10                  candidate is multi-word
+1 per character     length tiebreak
===================  ==========================================================

The rules write down what a schema reviewer says out loud while reading a
candidate list. A physical column name is a noun phrase, so a gerund
(``Pending``), an ``-ly`` word (``Monthly``), a past participle (``Received``)
and a plural (``Accounts``) are each a worse fit for a governed term than a
plain singular noun; a phrase is a worse fit than a single word; and between two
survivors the shorter is the likelier column word. For ``ID`` that ordering puts
``Identifier`` (10) ahead of ``Identification`` (14) ahead of ``Idaho`` (105).

Two exemption sets keep the morphology rules from firing on words that merely
look inflected: :data:`PAST_TENSE_NOUNS` for governed terms that genuinely end
in ``-ed``, and :data:`SINGULAR_LOOKING_PLURALS` for singular nouns that end in
``-s``. Without them ``Expedited`` and ``Address`` would be punished for their
spelling.

This is a rule of thumb. It is written down, it is published, and it is the same
rule of thumb every time — which is the difference between a defensible default
and a guess. :func:`score_breakdown` returns the per-rule arithmetic so a scored
resolution can be explained line by line, the way a pinned one is explained by
naming its pin. An answer nobody can explain is not an answer this package is
willing to emit.

What it is not
--------------
Not a language model, and not a claim about which expansion is more common
anywhere. It does not know that schemas say ``Identifier`` more often than
``Idaho``; it knows that a two-letter token is a poor way to write a state name
and that short singular nouns are what class words look like. When the catalog
*has* recorded an answer, the pin wins and this module is never consulted —
``ExpansionSource.SCORED`` exists precisely so a consumer can tell the two apart
and treat them differently.

Determinism
-----------
Every function here is pure: no I/O, no clock, no randomness, no dependence on
set iteration order in anything returned. Scores are a function of
``(candidate, token)`` alone, so two processes with the same inputs and no
shared state produce byte-identical audit records. :func:`rank_candidates`
breaks score ties on the candidate text itself, which makes the ordering total —
a collision set can never resolve one way today and the other way tomorrow.

Vocabulary note: worked examples use the fictional **Northwind Data Standards**
catalog (``NDS``) and generic industry tokens. Nothing here describes a real
organisation's standard.
"""

from __future__ import annotations

from typing import Iterable

__all__ = [
    "PAST_TENSE_NOUNS",
    "PENALTY_ADVERB",
    "PENALTY_GERUND",
    "PENALTY_MULTI_WORD",
    "PENALTY_PAST_TENSE",
    "PENALTY_PER_CHARACTER",
    "PENALTY_PLURAL",
    "PENALTY_US_STATE",
    "SINGULAR_LOOKING_PLURALS",
    "US_STATE_NAMES",
    "canonical_form_score",
    "rank_candidates",
    "score_breakdown",
]


# ---------------------------------------------------------------------------
# The penalty table
# ---------------------------------------------------------------------------

#: A 2-letter token whose candidate is a US state name. The largest penalty in
#: the table, and the only one aimed at a specific class of content rather than
#: at a word ending.
PENALTY_US_STATE = 100.0

#: Candidate ends in ``-ing``. A gerund names an activity; a column holds a
#: value.
PENALTY_GERUND = 50.0

#: Candidate ends in ``-ly``. Adverbs modify verbs, and there are no verbs in a
#: column name.
PENALTY_ADVERB = 40.0

#: Candidate ends in ``-ed`` and is not in :data:`PAST_TENSE_NOUNS`.
PENALTY_PAST_TENSE = 30.0

#: Candidate ends in ``-s`` and is not in :data:`SINGULAR_LOOKING_PLURALS`. A
#: governed term is stated in the singular; the plural is usually the table's
#: job, not the column's.
PENALTY_PLURAL = 20.0

#: Candidate is more than one whitespace-separated word. Ranked below every
#: morphology rule because plenty of governed terms are legitimately phrases
#: (``Transaction Identifier``); it is a mild preference, not a verdict.
PENALTY_MULTI_WORD = 10.0

#: Charged once per character of the candidate. This is the tiebreak that makes
#: the table useful rather than merely opinionated: most collision sets contain
#: candidates that trip no morphology rule at all, and length is then the only
#: signal left. It is charged on every candidate, not only on tied ones, so the
#: ordering is a single total sum rather than a cascade of comparisons.
PENALTY_PER_CHARACTER = 1.0


#: Governed terms that end in ``-ed`` and are nouns in a schema, not verbs.
#: Exempt from :data:`PENALTY_PAST_TENSE`.
PAST_TENSE_NOUNS = frozenset(
    {
        "expedited",
        "approved",
        "expired",
        "defaulted",
        "secured",
        "ranked",
        "sealed",
        "shared",
    }
)

#: Singular nouns that end in ``-s``, plus a few established plural-form terms
#: that a catalog stores exactly as written. Exempt from
#: :data:`PENALTY_PLURAL`; without this set ``Address`` and ``Status`` — two of
#: the most common class words there are — would be penalised for their
#: spelling.
SINGULAR_LOOKING_PLURALS = frozenset(
    {
        "address",
        "savings",
        "securities",
        "stats",
        "ops",
        "alias",
        "status",
        "process",
        "access",
        "business",
        "class",
    }
)

#: The fifty US state names, lower-cased.
#:
#: A two-letter token that collides with a state name is the single worst case
#: this function has to handle, and it is worth being explicit about why.
#:
#: Any catalog with address or geography columns in it maps state names to their
#: two-letter postal codes, so inverting the catalog drops ``Idaho`` into the
#: candidate set for ``ID``, ``Missouri`` into ``MO``, ``Oregon`` into ``OR`` and
#: ``Indiana`` into ``IN``. Two-letter tokens are the most heavily overloaded
#: tokens in any schema — they are also where the class words live — and a state
#: name is exactly the kind of candidate the rest of this table likes: a short,
#: singular, uninflected, well-formed noun that trips no morphology rule at all.
#: On length alone ``Idaho`` (5) beats ``Identifier`` (10), and a column named
#: ``ID`` would expand to a state.
#:
#: Nothing about the string ``Idaho`` reveals the problem; only the pairing with
#: a two-letter token does. Hence a penalty keyed on that pairing, and one large
#: enough that no accumulation of ordinary length can climb back over it.
#:
#: The check is deliberately narrow. It fires only at token length exactly two,
#: because a longer token that expands to a state name (``IDAHO``, ``ST_CD``) is
#: not the failure being prevented — it is a geography column doing its job.
#: Territories, the District of Columbia and the postal codes themselves are not
#: in the set: this is the collision that has bitten, stated at the size it
#: actually has.
US_STATE_NAMES = frozenset(
    {
        "alabama",
        "alaska",
        "arizona",
        "arkansas",
        "california",
        "colorado",
        "connecticut",
        "delaware",
        "florida",
        "georgia",
        "hawaii",
        "idaho",
        "illinois",
        "indiana",
        "iowa",
        "kansas",
        "kentucky",
        "louisiana",
        "maine",
        "maryland",
        "massachusetts",
        "michigan",
        "minnesota",
        "mississippi",
        "missouri",
        "montana",
        "nebraska",
        "nevada",
        "new hampshire",
        "new jersey",
        "new mexico",
        "new york",
        "north carolina",
        "north dakota",
        "ohio",
        "oklahoma",
        "oregon",
        "pennsylvania",
        "rhode island",
        "south carolina",
        "south dakota",
        "tennessee",
        "texas",
        "utah",
        "vermont",
        "virginia",
        "washington",
        "west virginia",
        "wisconsin",
        "wyoming",
    }
)

#: Token length at which the US-state rule applies. Named rather than inlined
#: because "2" is the whole content of that rule.
_STATE_COLLISION_TOKEN_LENGTH = 2


def _normalise(candidate: str) -> str:
    """Collapse whitespace so that formatting cannot change a score.

    ``"  Transaction   Identifier "`` and ``"Transaction Identifier"`` are the
    same governed term written two ways, and a catalog loaded from a
    hand-maintained spreadsheet contains both. Since length is one of the
    penalties, leaving the difference in would let trailing spaces decide a
    collision.

    Args:
        candidate: A candidate long form, as it came from the catalog.

    Returns:
        The candidate with leading, trailing and repeated whitespace removed.
    """
    return " ".join(candidate.split())


def _final_word(text: str) -> str:
    """Return the lower-cased last whitespace-separated word of ``text``.

    The morphology rules test how a candidate *ends*, which for a phrase means
    how its last word ends. The exemption sets are therefore consulted with the
    last word too, so that both halves of a rule talk about the same string:
    ``Secured`` is exempt from the past-tense penalty, and ``Balance Secured``
    must be exempt for the same reason.

    Args:
        text: An already-normalised candidate.

    Returns:
        The final word, lower-cased; ``""`` when there is no word at all.
    """
    words = text.split()
    return words[-1].lower() if words else ""


def score_breakdown(candidate: str, token: str) -> dict[str, float]:
    """Return the penalty charged by each rule, plus the total.

    This is the explainability half of the module and the reason the score is a
    published table rather than a private heuristic. A resolution recorded as
    ``ExpansionSource.SCORED`` can be reviewed by reading its breakdown next to
    the breakdowns of the candidates it beat, and a reviewer who disagrees can
    point at the rule they disagree with.

    Keys, in table order: ``us_state``, ``gerund``, ``adverb``, ``past_tense``,
    ``plural``, ``multi_word``, ``length``, ``total``. Every rule is present
    whether or not it fired, so callers may index without guarding, and the
    seven rule values sum exactly to ``total``.

    Args:
        candidate: A candidate long form from the collision set.
        token: The short-form token being expanded. Only its length matters, and
            only for the US-state rule.

    Returns:
        Rule name to penalty, all values floats, insertion-ordered as above.

    Example:
        >>> breakdown = score_breakdown("Idaho", "ID")
        >>> breakdown["us_state"], breakdown["length"], breakdown["total"]
        (100.0, 5.0, 105.0)
        >>> score_breakdown("Identifier", "ID")["total"]
        10.0
        >>> score_breakdown("Expedited", "EXPD")["past_tense"]
        0.0
    """
    text = _normalise(candidate)
    lowered = text.lower()
    final = _final_word(text)
    stripped_token = token.strip()

    is_state_collision = (
        len(stripped_token) == _STATE_COLLISION_TOKEN_LENGTH
        and stripped_token.isalpha()
        and lowered in US_STATE_NAMES
    )

    penalties = {
        "us_state": PENALTY_US_STATE if is_state_collision else 0.0,
        "gerund": PENALTY_GERUND if lowered.endswith("ing") else 0.0,
        "adverb": PENALTY_ADVERB if lowered.endswith("ly") else 0.0,
        "past_tense": (
            PENALTY_PAST_TENSE if lowered.endswith("ed") and final not in PAST_TENSE_NOUNS else 0.0
        ),
        "plural": (
            PENALTY_PLURAL
            if lowered.endswith("s") and final not in SINGULAR_LOOKING_PLURALS
            else 0.0
        ),
        "multi_word": PENALTY_MULTI_WORD if " " in text else 0.0,
        "length": PENALTY_PER_CHARACTER * len(text),
    }
    penalties["total"] = sum(penalties.values())
    return penalties


def canonical_form_score(candidate: str, token: str) -> float:
    """Score ``candidate`` as the expansion of ``token``. Lower wins.

    The sum of every penalty in the module table. See the module docstring for
    the table itself and for why each rule is in it.

    Args:
        candidate: A candidate long form from the collision set. Whitespace is
            collapsed before scoring, so incidental formatting cannot move a
            score.
        token: The short-form token being expanded, e.g. ``"ID"``. Only its
            length is consulted, and only by the US-state rule; the score is
            otherwise a function of the candidate alone.

    Returns:
        A non-negative penalty total. Zero is reachable only by the empty
        candidate, which is why :func:`rank_candidates` discards blank
        candidates rather than crowning one.

    Example:
        >>> canonical_form_score("Identifier", "ID")
        10.0
        >>> canonical_form_score("Idaho", "ID")
        105.0
        >>> canonical_form_score("Idaho", "ST_CD")
        5.0
        >>> canonical_form_score("Processing", "PROC")  # gerund, plus ten characters
        60.0
        >>> canonical_form_score("Process", "PROC")  # exempt from the -s rule
        7.0
    """
    return score_breakdown(candidate, token)["total"]


def rank_candidates(candidates: Iterable[str], token: str) -> tuple[str, ...]:
    """Order a collision set best-first, deterministically and totally.

    Two candidates can score identically — ``"Detail"`` and ``"Debtor"`` both
    cost six — so a bare sort on the score is not a total order, and one that
    falls back on input order would make the answer depend on how the catalog
    file happened to be sorted. Ties therefore break on the candidate text
    itself. Two deployments loading the same collision set in different orders
    resolve it the same way, which is the property an audit trail needs.

    The winner is ``rank_candidates(...)[0]``; the remainder is exactly the
    losing set that ``TokenExpansion.beat`` records.

    Blank and whitespace-only candidates are dropped. They score zero — no rule
    can charge a penalty against no characters — so keeping them would let a
    stray empty cell in a catalog spreadsheet win every collision it appeared
    in. Exact duplicates collapse to one entry, since a long form claimed twice
    by the same token is one candidate recorded twice.

    Args:
        candidates: The collision set for ``token``, in any order.
        token: The short-form token being expanded.

    Returns:
        The candidates, lowest score first, ties broken lexicographically by the
        candidate string. ``()`` when nothing usable was supplied.

    Example:
        >>> rank_candidates(["Idaho", "Identification", "Identifier"], "ID")
        ('Identifier', 'Identification', 'Idaho')
        >>> rank_candidates(["Dated", "Detail", "Date"], "DT")
        ('Date', 'Detail', 'Dated')
        >>> rank_candidates(["", "   "], "ID")
        ()
    """
    usable = {candidate for candidate in candidates if candidate and candidate.strip()}
    return tuple(sorted(usable, key=lambda item: (canonical_form_score(item, token), item)))
