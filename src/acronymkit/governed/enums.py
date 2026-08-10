"""Closed vocabularies used by governed short-form expansion.

Every one of these enums names something that is written into an audit record:
what kind of catalog entry produced an answer, which resolution rule fired, and
— when a name is checked rather than expanded — why it passed or failed. They
are enums rather than bare strings for exactly that reason. A typo in a free
string that ends up in an audit trail is indistinguishable from a real value,
and the whole point of this subsystem is that its output can be trusted without
re-deriving it.

All members derive from the package-wide ``_StrEnum`` in
:mod:`acronymkit.enums`, so each is a :class:`str`, serialises to its own value,
and may be supplied as a plain string by a caller who does not want to import
the enum types::

    NamingPolicy(mode="most_common") == NamingPolicy(mode=ResolutionMode.MOST_COMMON)

The base class is imported rather than re-declared. Two ``_StrEnum`` classes
would mean two ``coerce`` implementations that can drift, and coercion is what
makes the string-or-enum equivalence above true.

Vocabulary note: the worked examples throughout this package use a fictional
catalog, **Northwind Data Standards** (``NDS``), and generic industry tokens
(``TXN``, ``APPLNT``, ``DT``). Nothing here describes a real organisation's
standard.
"""

from __future__ import annotations

from ..enums import _StrEnum

__all__ = [
    "ComplianceReasonCode",
    "EntryKind",
    "ExpansionSource",
    "ResolutionMode",
    "UnknownPolicy",
    "Verdict",
]


class EntryKind(_StrEnum):
    """What kind of catalog record an entry is, and therefore how it behaves.

    The kind is not decoration. It is the difference between a token that must
    be expanded, a token that must be left exactly as it stands, and a token the
    catalog carries only so that a check can reject it by name.

    ``CLASS_WORD_ABBREV``
        A *class word*: the trailing noun that says what kind of value a column
        holds — ``ID``, ``DT``, ``CD``, ``AMT``, ``NM``. Governed naming
        standards generally require one at the end of every physical name, which
        is why this kind is singled out. It is the only kind whose *position*
        inside an identifier carries meaning.
    ``APPROVED_ABBREV``
        A short form the catalog approves. Expanding it is the right answer in
        the short → long direction, and abbreviating *to* it is the right answer
        in the reverse direction.
    ``AMBIGUOUS_PINNED``
        The source catalog offers more than one long form for this token, and a
        pin names the governed one. The losing candidates are kept rather than
        discarded; they are what a resolved expansion reports as having been
        beaten, and they are the reason a reviewer can tell a decision from a
        coincidence.
    ``DOMAIN_PIN``
        The same shape as ``AMBIGUOUS_PINNED``, but the pin was chosen for one
        subject area rather than for the catalog as a whole. Recorded separately
        so an audit can distinguish "the standard says so" from "this domain
        says so" — those two carry different weight in a review, and collapsing
        them would throw that away.
    ``PROPER_NOUN_ACRONYM``
        The token stands for a name: an organisation, a published standard, a
        product. Its expansion is fixed text and re-casing it would be wrong.
    ``SHORT_FULL_WORD``
        Not an abbreviation at all — a whole word short enough to be mistaken
        for one (``RISK``, ``RATE``, ``CITY``). It earns a kind of its own so
        that a compliance check answers "this is a word" rather than "this is an
        unapproved abbreviation", and so that expansion leaves it alone instead
        of inventing a long form for it.
    ``UNAPPROVED_EXPANSION``
        An abbreviation that is genuinely in use and that the catalog does not
        approve. Carrying it deliberately is what lets a compliance check name
        the problem and point at the approved form, instead of reporting the far
        less useful "unknown token".
    ``PASSTHROUGH``
        No catalog record exists for this token. The kind is recorded on the
        synthetic entry that stands in for one, so that an unknown is a stated
        outcome in the payload rather than an absence a consumer has to infer.
    """

    CLASS_WORD_ABBREV = "class_word_abbrev"
    APPROVED_ABBREV = "approved_abbrev"
    AMBIGUOUS_PINNED = "ambiguous_pinned"
    DOMAIN_PIN = "domain_pin"
    PROPER_NOUN_ACRONYM = "proper_noun_acronym"
    SHORT_FULL_WORD = "short_full_word"
    UNAPPROVED_EXPANSION = "unapproved_expansion"
    PASSTHROUGH = "passthrough"


class ExpansionSource(_StrEnum):
    """Which resolution rule produced an expansion — the provenance field.

    Members are declared in strict precedence order, highest first, and that
    order is the resolution algorithm. Reading the list top to bottom is reading
    what the resolver tries::

        CUSTOM  >  PINNED  >  APPROVED  >  GOVERNED  >  SCORED  >  PASSTHROUGH

    ``CUSTOM``
        A caller-supplied overlay entry won. Highest precedence, because a
        caller who has layered an override has said something the catalog could
        not know. Subject to ``NamingPolicy.allow_override``: with overrides
        disallowed, an overlay entry that *contradicts* a governed entry is not
        applied and the result says so. An overlay entry for a token the catalog
        has never heard of is still applied — overriding nothing is not an
        override.
    ``PINNED``
        The token had more than one candidate long form and the entry's ``pin``
        named the governed one. This is a decision the catalog already made; the
        library merely reports it.
    ``APPROVED``
        The token *is* the governed form. Either it is a ``keep_as_abbrev``
        entry, or it is a member of one of the allow-lists with no entry of its
        own. Its "expansion" is itself, and correcting it would be the bug.
    ``GOVERNED``
        The single unambiguous long form from the catalog. The ordinary case,
        and the one the whole design exists to serve.
    ``SCORED``
        The token collided and no pin resolved it, so
        ``canonical_form_score`` chose. This is the only member that involves a
        rule of thumb rather than a recorded decision, which is why it is
        reported separately and why the penalty breakdown behind it is
        published: a scored answer is a defensible guess, and it should be
        legible as one.
    ``PASSTHROUGH``
        Nothing matched. The token is Title Cased so the output stays readable,
        ``is_known`` is ``False`` and confidence is zero. This is the library
        declining to guess, and it is a feature: an unknown token reported as
        unknown is recoverable, an unknown token silently approximated is not.
    """

    CUSTOM = "custom"
    PINNED = "pinned"
    APPROVED = "approved"
    GOVERNED = "governed"
    SCORED = "scored"
    PASSTHROUGH = "passthrough"


class Verdict(_StrEnum):
    """Outcome carried by a single compliance finding.

    Findings are per-token (plus a few whole-name ones), and a ``PASS`` finding
    is recorded just as a ``FAIL`` one is. That is deliberate: a compliance
    result that listed only problems would let a reviewer see *that* a name was
    accepted without seeing *why*, and "why" is the part that survives an audit.
    """

    PASS = "pass"
    FAIL = "fail"


class ComplianceReasonCode(_StrEnum):
    """Why one finding reached its verdict — the stable, machine-readable half.

    ``ComplianceReason`` pairs a code with free-text detail. The detail is for a
    person and may be reworded; the code is for a program and may not. Anything
    that filters, counts or routes findings should key on the code.

    The first five codes accompany a ``PASS`` verdict and the last five a
    ``FAIL``, but nothing enforces that pairing structurally — the verdict is
    carried on the finding, and it is the verdict that decides.

    Passing codes
        ``CUSTOM_ABBREV``
            The token is approved by the caller's overlay rather than by the
            catalog. Distinguished from ``APPROVED_ABBREV`` so a review can see
            which approvals came from the governed standard and which came from
            the caller.
        ``APPROVED_ABBREV``
            The token is on the catalog's approved short-form list.
        ``COMMON_KEYWORD``
            The token is on the common-keyword allow-list: vocabulary a naming
            standard permits everywhere without approving it as an abbreviation.
        ``SHORT_FULL_WORD``
            The token is a whole word, not an abbreviation, and therefore needs
            no approval to appear.
        ``PROPER_NOUN_ACRONYM``
            The token is a name-derived acronym the catalog recognises.

    Failing codes
        ``UNAPPROVED_ABBREV``
            The token looks like an abbreviation and no allow-list, entry or
            overlay covers it. The most common real finding, and the one whose
            suggested fix is worth the most.
        ``MISSING_CLASS_WORD``
            The name does not end in a class word. A whole-name finding, so its
            token field is empty.
        ``NOT_UPPER_SNAKE``
            The name is not in ``UPPER_SNAKE`` form. Whole-name.
        ``EXCEEDS_MAX_LENGTH``
            The name is longer than ``NamingPolicy.max_name_length`` while
            ``enforce_name_length`` is on. Whole-name, and it is *only* ever a
            finding: nothing in this package shortens a name to make it fit.
        ``EMPTY_NAME``
            There was no name to check. Reported rather than raised, because a
            batch of names being checked should not stop at the first blank row.
    """

    CUSTOM_ABBREV = "custom_abbrev"
    APPROVED_ABBREV = "approved_abbrev"
    COMMON_KEYWORD = "common_keyword"
    SHORT_FULL_WORD = "short_full_word"
    PROPER_NOUN_ACRONYM = "proper_noun_acronym"
    UNAPPROVED_ABBREV = "unapproved_abbrev"
    MISSING_CLASS_WORD = "missing_class_word"
    NOT_UPPER_SNAKE = "not_upper_snake"
    EXCEEDS_MAX_LENGTH = "exceeds_max_length"
    EMPTY_NAME = "empty_name"


class UnknownPolicy(_StrEnum):
    """What to do with a token the governed vocabulary does not contain.

    There is no good universal answer, so the choice is named and handed to the
    caller rather than buried in a constant.

    ``PASSTHROUGH_TITLECASE``
        **Default.** Title Case the token, mark it ``is_known=False`` and give
        it zero confidence. The reading is "I do not know this, here is
        something legible in the meantime, do not trust it". A pipeline can
        filter on ``is_known`` and route the misses to whoever owns the catalog,
        which is how an unknown token is supposed to be fixed: by adding it.
    ``NEURAL``
        Opt in to the statistical tier for unknown tokens only. Off by default
        and deliberately awkward to reach, because a governed pipeline that
        quietly starts guessing has lost the property it was chosen for. Two
        limits hold whatever this is set to: the statistical tier is never
        consulted for a token the catalog *does* know while
        ``NamingPolicy.governed_hit_is_final`` is on, and a neural answer never
        reports ``ExpansionSource.GOVERNED``.
    ``REJECT``
        Refuse the input instead of answering. For pipelines where an
        unrecognised token means the catalog is out of date and processing
        should stop rather than continue on a name nobody has approved.
    """

    PASSTHROUGH_TITLECASE = "passthrough_titlecase"
    NEURAL = "neural"
    REJECT = "reject"


class ResolutionMode(_StrEnum):
    """How a token with several candidate long forms is resolved.

    ``GOVERNED``
        **Default.** Honour the catalog: an overlay first, then the entry's pin,
        then its canonical form, and only then a score. The dictionary is the
        ground truth and nothing is inferred.
    ``MOST_COMMON``
        Ignore the pin and take the first candidate in the entry's declared
        ``candidates`` order, which fixture data orders by corpus frequency.
        This is the contrast arm — it exists to be beaten, so that "the governed
        answer differs from the most-common answer" is a demonstrable claim
        rather than an assertion. It is a comparison on fixture tokens chosen to
        make the two rules disagree, and it is not evidence about any corpus.
    """

    GOVERNED = "governed"
    MOST_COMMON = "most_common"
