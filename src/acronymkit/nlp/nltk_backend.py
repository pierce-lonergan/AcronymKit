"""NLTK-powered Tier 1 backend.

NLTK is an **optional** dependency and, unlike a normal package, having it
installed is not sufficient: its perceptron tagger ships as *downloadable
corpus data*. A machine can therefore have ``import nltk`` succeed while
:func:`nltk.pos_tag` raises ``LookupError``. :meth:`NltkBackend.is_available`
accounts for that by actually tagging a probe sentence once, and caching the
verdict.

Nothing here is imported at module scope; every NLTK reference lives inside a
function guarded by ``try/except``.
"""

from __future__ import annotations

import re
import threading
from collections.abc import Mapping, Sequence
from types import MappingProxyType
from typing import Any, Callable, Optional

from ..enums import Language
from ..models import Token
from .base import (
    Annotation,
    BackendUnavailable,
    align_positionally,
    apply_annotations,
)

__all__ = [
    "NLTK_LANGUAGE_CODES",
    "PENN_TO_UNIVERSAL",
    "NltkBackend",
    "load_tagger",
    "penn_to_universal",
]

#: Signature of the callable :func:`load_tagger` hands back.
TaggerCallable = Callable[[Sequence[str]], list[tuple[str, str]]]


#: Penn Treebank tag -> Universal POS tag. Frozen, exhaustive over the tag set
#: emitted by NLTK's averaged perceptron tagger.
PENN_TO_UNIVERSAL: Mapping[str, str] = MappingProxyType(
    {
        # -- nouns -----------------------------------------------------------
        "NN": "NOUN",
        "NNS": "NOUN",
        "NNP": "PROPN",
        "NNPS": "PROPN",
        # -- verbs -----------------------------------------------------------
        "VB": "VERB",
        "VBD": "VERB",
        "VBG": "VERB",
        "VBN": "VERB",
        "VBP": "VERB",
        "VBZ": "VERB",
        "MD": "AUX",
        # -- modifiers -------------------------------------------------------
        "JJ": "ADJ",
        "JJR": "ADJ",
        "JJS": "ADJ",
        "RB": "ADV",
        "RBR": "ADV",
        "RBS": "ADV",
        "WRB": "ADV",
        # -- function words --------------------------------------------------
        "IN": "ADP",
        "DT": "DET",
        "PDT": "DET",
        "WDT": "DET",
        "CC": "CCONJ",
        "PRP": "PRON",
        "PRP$": "PRON",
        "WP": "PRON",
        "WP$": "PRON",
        "EX": "PRON",
        "TO": "PART",
        "RP": "PART",
        "POS": "PART",
        "UH": "INTJ",
        # -- numerals, symbols, punctuation ----------------------------------
        "CD": "NUM",
        "SYM": "SYM",
        "$": "SYM",
        "#": "SYM",
        ".": "PUNCT",
        ",": "PUNCT",
        ":": "PUNCT",
        "``": "PUNCT",
        "''": "PUNCT",
        "(": "PUNCT",
        ")": "PUNCT",
        "-LRB-": "PUNCT",
        "-RRB-": "PUNCT",
        # -- residual --------------------------------------------------------
        "FW": "X",
        "LS": "X",
    }
)

#: Prefix fallbacks for tags absent from :data:`PENN_TO_UNIVERSAL`, tried
#: longest-first so that ``NNP`` never resolves through ``NN``.
_PENN_PREFIXES: tuple[tuple[str, str], ...] = (
    ("NNP", "PROPN"),
    ("WRB", "ADV"),
    ("WDT", "DET"),
    ("PRP", "PRON"),
    ("NN", "NOUN"),
    ("VB", "VERB"),
    ("JJ", "ADJ"),
    ("RB", "ADV"),
    ("WP", "PRON"),
)

#: Languages NLTK's bundled perceptron tagger supports, mapped to its codes.
NLTK_LANGUAGE_CODES: Mapping[Language, str] = MappingProxyType({Language.EN: "eng"})

#: Universal POS -> WordNet part-of-speech character, for lemmatisation.
_WORDNET_POS: Mapping[str, str] = MappingProxyType(
    {"NOUN": "n", "PROPN": "n", "VERB": "v", "ADJ": "a", "ADV": "r"}
)

#: Sentence used to prove the tagger's data files are actually present.
_PROBE_WORDS: tuple[str, ...] = ("the", "quick", "brown", "fox")

_TAGGER_CACHE: dict[str, TaggerCallable] = {}
_FAILED_TAGGERS: set[str] = set()
_LEMMATIZER_CACHE: dict[str, Any] = {}
_PROBED_LEMMATIZERS: set[str] = set()

_CACHE_LOCK = threading.Lock()

#: NLTK decorates its lookup banner with ANSI colour codes.
_ANSI_ESCAPE = re.compile(r"\x1b\[[0-9;]*m")


def _summarise(exc: BaseException) -> str:
    """Condense a third-party exception to one short line.

    NLTK's ``LookupError`` carries a multi-line banner listing every search
    path; embedding it verbatim in our own message is unreadable.

    Args:
        exc: Exception raised by NLTK.

    Returns:
        The exception type plus its first non-empty line, truncated.
    """
    for line in str(exc).splitlines():
        stripped = _ANSI_ESCAPE.sub("", line).strip()
        if any(character.isalnum() for character in stripped):
            return f"{type(exc).__name__}: {stripped[:120]}"
    return type(exc).__name__


def penn_to_universal(tag: str) -> str:
    """Translate a Penn Treebank tag to a Universal POS tag.

    Args:
        tag: Penn Treebank tag such as ``"NNS"``, ``"VBG"`` or ``"PRP$"``.

    Returns:
        The Universal POS tag. Unknown tags are resolved by longest-prefix
        match (``NNPX`` -> ``PROPN``) and, failing that, reported as ``"X"``.
    """
    normalised = tag.upper()
    mapped = PENN_TO_UNIVERSAL.get(normalised)
    if mapped is not None:
        return mapped
    for prefix, universal in _PENN_PREFIXES:
        if normalised.startswith(prefix):
            return universal
    return "X"


def load_tagger(language_code: str) -> TaggerCallable:
    """Load (and memoise) a callable that Penn-tags a list of words.

    The returned callable is verified against :data:`_PROBE_WORDS` before it is
    cached, which is the only reliable way to detect that the
    ``averaged_perceptron_tagger`` corpus was never downloaded: NLTK defers
    that failure to the first tagging call.

    Args:
        language_code: NLTK language code, e.g. ``"eng"``.

    Returns:
        A callable mapping a word sequence to ``(word, penn_tag)`` pairs.

    Raises:
        BackendUnavailable: If NLTK is not importable, or its tagger data is
            missing or unusable.
    """
    with _CACHE_LOCK:
        cached = _TAGGER_CACHE.get(language_code)
        if cached is not None:
            return cached
        if language_code in _FAILED_TAGGERS:
            raise BackendUnavailable(
                f"NLTK tagger data for {language_code!r} is unavailable; download it "
                f"with: python -m nltk.downloader averaged_perceptron_tagger"
            )

    try:
        from nltk import pos_tag
    except ImportError as exc:
        raise BackendUnavailable(
            "NLTK is not installed; install it with: pip install 'acronymkit[nlp]'"
        ) from exc

    def tagger(words: Sequence[str]) -> list[tuple[str, str]]:
        """Tag ``words`` with Penn Treebank tags."""
        return list(pos_tag(list(words), lang=language_code))

    try:
        tagger(_PROBE_WORDS)
    except Exception as exc:
        # LookupError for missing corpora, but also OSError/ValueError for a
        # corrupted or version-mismatched pickle: all mean "unusable".
        with _CACHE_LOCK:
            _FAILED_TAGGERS.add(language_code)
        raise BackendUnavailable(
            f"NLTK tagger data for {language_code!r} is unavailable "
            f"[{_summarise(exc)}]; download it with: "
            f"python -m nltk.downloader averaged_perceptron_tagger"
        ) from exc

    with _CACHE_LOCK:
        _TAGGER_CACHE.setdefault(language_code, tagger)
        return _TAGGER_CACHE[language_code]


def _load_lemmatizer(language_code: str) -> Optional[Any]:
    """Load (and memoise) a WordNet lemmatiser, if its corpus is present.

    Lemmas are a bonus, not a requirement: the backend stays available when
    the ``wordnet`` corpus is missing and simply leaves
    :attr:`~acronymkit.models.Token.lemma` alone.

    Args:
        language_code: NLTK language code; only ``"eng"`` is supported.

    Returns:
        A ``WordNetLemmatizer`` instance, or ``None`` when lemmatisation is
        unavailable. Never raises.
    """
    with _CACHE_LOCK:
        if language_code in _PROBED_LEMMATIZERS:
            return _LEMMATIZER_CACHE.get(language_code)
    lemmatizer: Optional[Any] = None
    if language_code == "eng":
        try:
            from nltk.stem import WordNetLemmatizer

            candidate = WordNetLemmatizer()
            candidate.lemmatize("tests", "n")
            lemmatizer = candidate
        except Exception:
            # Missing 'wordnet'/'omw-1.4' data, or any other loader failure.
            lemmatizer = None
    with _CACHE_LOCK:
        _PROBED_LEMMATIZERS.add(language_code)
        if lemmatizer is not None:
            _LEMMATIZER_CACHE.setdefault(language_code, lemmatizer)
        return _LEMMATIZER_CACHE.get(language_code)


class NltkBackend:
    """Tier 1 annotator backed by NLTK's averaged perceptron tagger.

    The tagger is fed our own token surfaces rather than NLTK's tokenisation.
    That keeps alignment trivially one-to-one *and* avoids depending on the
    ``punkt`` corpus, so the backend needs a single downloadable resource.

    Construction is free; the tagger loads on first
    :meth:`is_available`/:meth:`annotate` call and is cached process-wide.

    Args:
        language: Language to tag. Only those in
            :data:`NLTK_LANGUAGE_CODES` are supported; the backend reports
            itself unavailable for the rest.
    """

    name = "nltk"

    def __init__(self, language: Language = Language.EN) -> None:
        self._language: Language = (
            language if isinstance(language, Language) else Language.from_tag(str(language))
        )
        self._code: Optional[str] = NLTK_LANGUAGE_CODES.get(self._language)

    @property
    def language(self) -> Language:
        """Language this backend was configured for."""
        return self._language

    @property
    def language_code(self) -> Optional[str]:
        """NLTK language code, or ``None`` when the language is unsupported."""
        return self._code

    def is_available(self) -> bool:
        """Return whether NLTK *and* its tagger data can be used.

        Every failure mode reports ``False`` instead of raising: NLTK not
        installed, the configured language having no NLTK tagger, the
        ``averaged_perceptron_tagger`` corpus never downloaded (which surfaces
        as ``LookupError`` on first use, not at import), a corrupted or
        version-mismatched pickle, or any other exception raised while
        loading. The result is cached, so repeated probes are cheap.

        Returns:
            ``True`` only if a probe sentence was successfully tagged.
        """
        if self._code is None:
            return False
        try:
            load_tagger(self._code)
        except Exception:
            # Availability probes never raise, whatever NLTK threw.
            return False
        return True

    def annotate(self, text: str, tokens: Sequence[Token]) -> list[Token]:
        """Annotate ``tokens`` with Penn tags mapped to Universal POS.

        Args:
            text: Original phrase. Unused: the tagger consumes the token
                surfaces directly so that no re-tokenisation can desynchronise
                the two sequences.
            tokens: Tokens emitted by the tokenizer.

        Returns:
            A new list of new :class:`~acronymkit.models.Token` objects with
            ``pos`` (and ``lemma``, when the WordNet corpus is installed)
            filled and roles refreshed. Any token whose surface form the tagger
            did not echo back is returned untouched.

        Raises:
            BackendUnavailable: If NLTK or its tagger data is missing. Callers
                should consult :meth:`is_available` first.
        """
        del text  # the tagger is fed token surfaces, not raw text
        if not tokens:
            return []
        if self._code is None:
            raise BackendUnavailable(f"NLTK has no tagger for language {self._language.value!r}")
        tagger = load_tagger(self._code)
        lemmatizer = _load_lemmatizer(self._code)

        surfaces = [token.text for token in tokens]
        annotations: list[Annotation] = []
        for word, tag in tagger(surfaces):
            universal = penn_to_universal(tag)
            annotations.append(
                Annotation(
                    text=word,
                    pos=universal,
                    lemma=self._lemma(lemmatizer, word, universal),
                )
            )
        aligned = align_positionally(tokens, annotations)
        return apply_annotations(tokens, aligned, update_roles=True)

    # -- internals ---------------------------------------------------------
    @staticmethod
    def _lemma(lemmatizer: Optional[Any], word: str, universal_pos: str) -> Optional[str]:
        """Lemmatise ``word``, tolerating every WordNet failure mode.

        Args:
            lemmatizer: Loaded lemmatiser, or ``None``.
            word: Surface form to lemmatise.
            universal_pos: Universal POS tag guiding the WordNet lookup.

        Returns:
            The lemma, or ``None`` when no lemmatiser is available, the POS is
            not lemmatisable, or the lookup failed.
        """
        if lemmatizer is None:
            return None
        wordnet_pos = _WORDNET_POS.get(universal_pos)
        if wordnet_pos is None:
            return None
        try:
            lemma = lemmatizer.lemmatize(word.lower(), wordnet_pos)
        except Exception:
            # A missing corpus can surface lazily on the first real lookup.
            return None
        return str(lemma) or None

    def __repr__(self) -> str:  # pragma: no cover - display helper
        return f"NltkBackend(language={self._language.value!r})"
