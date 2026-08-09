"""Pure-stdlib fallback backend: suffix-driven part-of-speech guessing.

:class:`HeuristicBackend` is always available. It exists so that Tier 0 results
carry the same :attr:`~acronymkit.models.Token.pos` field as Tier 1 results,
making downstream code (and result payloads) uniform regardless of which
runtime was resolved.

It is deliberately conservative: it **only** fills ``pos``. Role,
``is_critical``, ``is_eligible`` and ``letters`` are whatever the tokenizer and
the categorised stop-word registry already decided, because a suffix table is
not evidence strong enough to overturn them.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from types import MappingProxyType
from typing import Optional

from ..enums import Language, StopWordCategory, TokenRole
from ..exceptions import AcronymKitError
from ..models import Token
from ..stopwords import StopWordRegistry
from .base import Annotation, apply_annotations

__all__ = ["STOP_WORD_POS", "SUFFIX_POS", "HeuristicBackend", "guess_pos"]


#: Word-ending -> Universal POS. Frozen; the longest matching suffix wins.
SUFFIX_POS: Mapping[str, str] = MappingProxyType(
    {
        # -- nominalising suffixes -----------------------------------------
        "tion": "NOUN",
        "sion": "NOUN",
        "ment": "NOUN",
        "ness": "NOUN",
        "ance": "NOUN",
        "ence": "NOUN",
        "ship": "NOUN",
        "ity": "NOUN",
        "ism": "NOUN",
        "ist": "NOUN",
        "er": "NOUN",
        "or": "NOUN",
        # -- verbalising suffixes ------------------------------------------
        "ing": "VERB",
        "ate": "VERB",
        "ify": "VERB",
        "ise": "VERB",
        "ize": "VERB",
        "ed": "VERB",
        # -- adjectival suffixes -------------------------------------------
        "able": "ADJ",
        "ible": "ADJ",
        "less": "ADJ",
        "ous": "ADJ",
        "ive": "ADJ",
        "ful": "ADJ",
        "al": "ADJ",
        "ic": "ADJ",
        # -- adverbial suffix ----------------------------------------------
        "ly": "ADV",
    }
)

#: Stop-word class -> Universal POS, used before the suffix table is consulted.
STOP_WORD_POS: Mapping[StopWordCategory, str] = MappingProxyType(
    {
        StopWordCategory.ARTICLE: "DET",
        StopWordCategory.DETERMINER: "DET",
        StopWordCategory.PREPOSITION: "ADP",
        StopWordCategory.CONJUNCTION: "CCONJ",
        StopWordCategory.PRONOUN: "PRON",
        StopWordCategory.AUXILIARY: "AUX",
        StopWordCategory.PARTICLE: "PART",
        StopWordCategory.OTHER: "X",
    }
)

#: Tag used when nothing else matched; nouns dominate technical phrases.
DEFAULT_POS = "NOUN"

#: Characters that must remain in front of a suffix for it to count.
MIN_STEM_LENGTH = 2

#: Suffixes ordered longest-first (then alphabetically) for deterministic,
#: unambiguous matching when a word ends in several table entries at once
#: ("organization" ends in both "tion" and "ion"-like fragments).
_SUFFIXES_LONGEST_FIRST: tuple[str, ...] = tuple(
    sorted(SUFFIX_POS, key=lambda suffix: (-len(suffix), suffix))
)


def guess_pos(word: str) -> str:
    """Guess a Universal POS tag for ``word`` from its ending.

    The rule is deterministic and total:

    1. Non-alphabetic characters are dropped and the remainder casefolded.
    2. Suffixes are tested longest-first, so a word matching several entries
       resolves to the most specific one.
    3. A suffix only applies when at least :data:`MIN_STEM_LENGTH` characters
       precede it, which keeps short words ("or", "her", "ed") out of the
       table.
    4. Anything unmatched — including every word too short to carry a suffix —
       is reported as :data:`DEFAULT_POS`; an empty word is reported as ``"X"``.

    Args:
        word: Surface form to classify.

    Returns:
        A Universal POS tag such as ``"NOUN"``, ``"VERB"``, ``"ADJ"`` or
        ``"ADV"``.
    """
    cleaned = "".join(character for character in word.casefold() if character.isalpha())
    if not cleaned:
        return "X"
    for suffix in _SUFFIXES_LONGEST_FIRST:
        if len(cleaned) - len(suffix) < MIN_STEM_LENGTH:
            continue
        if cleaned.endswith(suffix):
            return SUFFIX_POS[suffix]
    return DEFAULT_POS


class HeuristicBackend:
    """Zero-dependency annotator built from a suffix table and stop-word classes.

    Construction is free: the stop-word registry is loaded on first use and its
    absence is not fatal (tokens already carry
    :attr:`~acronymkit.models.Token.stop_word_category` from the tokenizer, and
    the registry is only a second opinion for tokens that lack one).

    Args:
        language: Language whose stop-word resource should be consulted.
        stop_words: Pre-built registry to reuse. When ``None`` the bundled
            resource for ``language`` is loaded lazily.
    """

    name = "heuristic"

    def __init__(
        self,
        language: Language = Language.EN,
        stop_words: Optional[StopWordRegistry] = None,
    ) -> None:
        self._language: Language = (
            language if isinstance(language, Language) else Language.from_tag(str(language))
        )
        self._stop_words: Optional[StopWordRegistry] = stop_words
        self._registry_loaded: bool = stop_words is not None

    @property
    def language(self) -> Language:
        """Language this backend was configured for."""
        return self._language

    def is_available(self) -> bool:
        """Return ``True``; the heuristic backend has no optional dependencies.

        Returns:
            Always ``True``. It imports nothing outside the standard library
            and ``acronymkit`` itself, so there is no failure mode to report.
        """
        return True

    def annotate(self, text: str, tokens: Sequence[Token]) -> list[Token]:
        """Fill :attr:`~acronymkit.models.Token.pos` on every token.

        Roles, criticality and eligibility are passed through untouched: a
        suffix table is not authoritative enough to overrule the tokenizer.

        Args:
            text: Original phrase. Unused — the heuristic is context-free — and
                accepted only to satisfy the
                :class:`~acronymkit.nlp.base.NlpBackend` protocol.
            tokens: Tokens emitted by the tokenizer.

        Returns:
            A new list of new :class:`~acronymkit.models.Token` objects that
            differ from the input only in ``pos``.
        """
        del text  # context-free by construction
        if not tokens:
            return []
        annotations: list[Optional[Annotation]] = [self._annotation_for(token) for token in tokens]
        return apply_annotations(tokens, annotations, update_roles=False)

    # -- internals ---------------------------------------------------------
    def _annotation_for(self, token: Token) -> Annotation:
        """Build the POS-only annotation for a single token.

        Args:
            token: Token to classify.

        Returns:
            An :class:`~acronymkit.nlp.base.Annotation` carrying a POS tag and
            no lemma or offsets.
        """
        if token.role is TokenRole.ACRONYM:
            return Annotation(text=token.text, pos="PROPN")
        if token.role is TokenRole.NUMERAL:
            return Annotation(text=token.text, pos="NUM")

        category = token.stop_word_category
        if category is None:
            category = self._category(token.text)
        if category is not None:
            return Annotation(text=token.text, pos=STOP_WORD_POS.get(category, "X"))
        if token.role is TokenRole.SYMBOL:
            return Annotation(text=token.text, pos="SYM")
        return Annotation(text=token.text, pos=guess_pos(token.text))

    def _category(self, word: str) -> Optional[StopWordCategory]:
        """Look ``word`` up in the stop-word registry, if one is loadable.

        Args:
            word: Surface form; the registry matches case-insensitively.

        Returns:
            The word's grammatical class, or ``None`` when it is not a stop
            word or no registry could be loaded for this language.
        """
        registry = self._registry()
        if registry is None:
            return None
        return registry.category(word)

    def _registry(self) -> Optional[StopWordRegistry]:
        """Return the stop-word registry, loading it at most once.

        Returns:
            The registry for this backend's language, or ``None`` when no
            resource is bundled for it. Never raises: a missing resource simply
            means the tokenizer's own categories are the only signal available.
        """
        if self._registry_loaded:
            return self._stop_words
        self._registry_loaded = True
        try:
            self._stop_words = StopWordRegistry.load(self._language)
        except (AcronymKitError, OSError, ValueError):
            self._stop_words = None
        return self._stop_words

    def __repr__(self) -> str:  # pragma: no cover - display helper
        return f"HeuristicBackend(language={self._language.value!r})"
