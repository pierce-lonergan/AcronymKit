"""Phonotactic modelling: the ``Phi(A)`` term of the composite objective.

The scoring function ranks a candidate acronym ``A`` partly on how *word-like*
its character sequence is::

    Phi(A) = (1 / (k - 1)) * SUM_{m=1}^{k-1} log P(c_{m+1} | c_m)      k = len(A)

that is, the **mean natural-log conditional probability** of the ``k - 1``
character bigram transitions inside ``A``. :class:`CharNGramModel` owns that
distribution; :meth:`CharNGramModel.score` implements the formula verbatim.

The module also exposes cheap orthographic heuristics (:func:`has_vowel`,
:func:`vowel_ratio`, :func:`syllable_count`, :func:`longest_consonant_run`)
used both by the generator's filters and by
:meth:`CharNGramModel.normalized_score`.

Design notes:

* **Tier 0 pure.** Only the standard library, plus sibling ``acronymkit``
  modules, is imported.
* **Deterministic.** No randomness, no clock, no set-iteration-order leakage
  into any returned value.
* **Thread-safe.** A :class:`CharNGramModel` is immutable in practice: the
  transition table is copied at construction, wrapped in read-only mapping
  proxies and never mutated afterwards, so a single instance may be shared
  freely between threads (and is, via the memoised :meth:`CharNGramModel.load`).
* **Accent-aware.** The vowel/consonant helpers compare on the *base* letter
  after canonical decomposition, so ``"é"`` counts as a vowel and ``"ç"`` as a
  consonant. This keeps the French/Spanish/German resources usable.
"""

from __future__ import annotations

import gzip
import json
import math
import unicodedata
from functools import cache, lru_cache
from pathlib import Path
from types import MappingProxyType
from typing import Any, Iterable, Mapping, Optional

from .enums import Language
from .exceptions import ResourceNotFoundError
from .resources import has_resource, read_json_resource

__all__ = [
    "CharNGramModel",
    "has_vowel",
    "longest_consonant_run",
    "pronounceability",
    "syllable_count",
    "vowel_ratio",
]

#: Canonical vowel letters.
VOWELS = "aeiou"

#: Semi-vowels. Only ``y`` is treated as a syllable nucleus by this module;
#: ``w`` never forms one on its own in the supported languages, so it is
#: classified as a consonant everywhere below.
SEMI_VOWELS = "yw"

#: Letters accepted as a vowel nucleus (``VOWELS`` plus the semi-vowel ``y``).
_VOWEL_LETTERS = frozenset(VOWELS + "y")

#: Multiplier applied by :meth:`CharNGramModel.normalized_score` when a
#: candidate contains no vowel at all ("TXT", "PDF"). Such strings are spellable
#: but not pronounceable, so they keep roughly a third of their raw score.
NO_VOWEL_PENALTY = 0.35

#: Multiplier applied when a candidate contains a consonant run longer than
#: :data:`MAX_CONSONANT_RUN` ("SCHTR..."). Long clusters are legal in German but
#: hurt pronounceability in every supported language, hence a milder penalty
#: than :data:`NO_VOWEL_PENALTY`.
CONSONANT_RUN_PENALTY = 0.6

#: Longest consonant run tolerated before :data:`CONSONANT_RUN_PENALTY` applies.
MAX_CONSONANT_RUN = 3

#: Neutral pronounceability reported by an information-free (uniform) model.
#: Mirrors the ``ngram=None`` convention documented for ``scoring.Scorer``.
_UNIFORM_NEUTRAL_SCORE = 0.5

#: Bigram order implemented by :class:`CharNGramModel`.
_ORDER = 2

_LATIN_BASIC = "abcdefghijklmnopqrstuvwxyz"

#: Fallback alphabets used by :meth:`CharNGramModel.uniform` when no trained
#: resource is available. Sorted, de-duplicated, lowercase.
_DEFAULT_ALPHABETS: dict[Language, str] = {
    Language.EN: _LATIN_BASIC,
    Language.FR: "".join(sorted(set(_LATIN_BASIC + "àâæçéèêëîïôùûüœÿ"))),
    Language.ES: "".join(sorted(set(_LATIN_BASIC + "áéíñóúü"))),
    Language.DE: "".join(sorted(set(_LATIN_BASIC + "äöüß"))),
}


def _as_language(value: object) -> Language:
    """Coerce ``value`` to a :class:`~acronymkit.enums.Language` member.

    Args:
        value: A ``Language`` member or its string value/name.

    Returns:
        The matching member.

    Raises:
        ValueError: If ``value`` names no known language.
    """
    return Language.coerce(value)


# ---------------------------------------------------------------------------
# orthographic helpers
# ---------------------------------------------------------------------------
@lru_cache(maxsize=1024)
def _base_letter(char: str) -> str:
    """Return ``char`` case-folded and stripped of combining marks.

    Args:
        char: A single character.

    Returns:
        The lowercase base letter (``"É"`` -> ``"e"``), or ``""`` when the
        character decomposes to nothing but combining marks.
    """
    decomposed = unicodedata.normalize("NFD", char.casefold())
    return "".join(c for c in decomposed if not unicodedata.combining(c))


def _is_vowel(char: str) -> bool:
    """Return whether ``char`` is a vowel nucleus (``y`` included, ``w`` not)."""
    base = _base_letter(char)
    return bool(base) and base[0] in _VOWEL_LETTERS


def _is_consonant(char: str) -> bool:
    """Return whether ``char`` is an alphabetic non-vowel."""
    return char.isalpha() and not _is_vowel(char)


def has_vowel(word: str) -> bool:
    """Return whether ``word`` contains at least one vowel.

    ``y`` counts as a vowel (``"SYNC"`` is pronounceable); ``w`` does not.
    Accented vowels count via canonical decomposition (``"É"`` -> ``"e"``).

    Args:
        word: Any string; case and accents are irrelevant.

    Returns:
        ``True`` when a vowel nucleus is present, else ``False``. The empty
        string returns ``False``.
    """
    return any(_is_vowel(char) for char in word)


def vowel_ratio(word: str) -> float:
    """Return the fraction of ``word``'s letters that are vowels.

    Uses the same vowel definition as :func:`has_vowel` (``y`` included).
    Non-alphabetic characters (digits, punctuation) are ignored entirely, so
    ``"3D"`` is measured over ``"D"`` alone.

    Args:
        word: Any string.

    Returns:
        A value in ``[0.0, 1.0]``; ``0.0`` when ``word`` holds no letters.
    """
    letters = [char for char in word if char.isalpha()]
    if not letters:
        return 0.0
    vowels = sum(1 for char in letters if _is_vowel(char))
    return vowels / len(letters)


def syllable_count(word: str) -> int:
    """Estimate the number of syllables in ``word``.

    Heuristic: count maximal runs of vowel letters (each run is one nucleus),
    then subtract one for a silent trailing ``e``. The ``e`` is treated as
    silent when the word is longer than two letters, ends in ``e``, the
    preceding character is a consonant, and the word does not end in ``le``
    (``"table"`` keeps its second syllable). The result is never below ``1`` for
    a word containing at least one letter.

    Args:
        word: Any string; non-alphabetic characters are ignored.

    Returns:
        A syllable estimate ``>= 1``, or ``0`` for a string with no letters.
    """
    letters = [char for char in word if char.isalpha()]
    if not letters:
        return 0
    groups = 0
    previous_was_vowel = False
    for char in letters:
        current_is_vowel = _is_vowel(char)
        if current_is_vowel and not previous_was_vowel:
            groups += 1
        previous_was_vowel = current_is_vowel
    cleaned = "".join(_base_letter(char) or char.casefold() for char in letters)
    if (
        len(cleaned) > 2
        and cleaned.endswith("e")
        and not cleaned.endswith("le")
        and _is_consonant(cleaned[-2])
    ):
        groups -= 1
    return max(1, groups)


def longest_consonant_run(word: str) -> int:
    """Return the length of the longest uninterrupted consonant cluster.

    Consonants are alphabetic characters that are not vowels under
    :func:`has_vowel`'s definition, so ``y`` breaks a run and ``w`` extends one.
    Non-alphabetic characters terminate the current run without contributing.

    Args:
        word: Any string.

    Returns:
        The maximum cluster length; ``0`` when ``word`` has no consonants.
    """
    longest = 0
    current = 0
    for char in word:
        if _is_consonant(char):
            current += 1
            if current > longest:
                longest = current
        else:
            current = 0
    return longest


def _clamp_unit(value: float) -> float:
    """Clamp ``value`` into ``[0.0, 1.0]``."""
    if value <= 0.0:
        return 0.0
    if value >= 1.0:
        return 1.0
    return value


# ---------------------------------------------------------------------------
# the model
# ---------------------------------------------------------------------------
class CharNGramModel:
    """An add-k smoothed character bigram model over one language.

    The model stores natural-log conditional probabilities
    ``log P(next | prev)`` for every ``(prev, next)`` symbol pair it knows
    about. Two sentinel symbols delimit a word: :attr:`BOUNDARY_START` precedes
    the first character and :attr:`BOUNDARY_END` follows the last, which lets
    :meth:`score_with_boundaries` reward plausible word beginnings and endings.

    Instances are **immutable in practice and safe to share across threads**:
    the transition table is deep-copied into read-only mapping proxies at
    construction and no method ever mutates instance state.

    Args:
        transitions: Mapping ``prev -> {next: log_prob}``. Copied, not aliased.
        backoff_log_prob: Log-probability returned for any transition absent
            from ``transitions``. Must be finite and ``<= 0``.
        alphabet: The letters the model was trained on, ideally sorted and
            de-duplicated. Boundary symbols are *not* part of it.
        language: Language the model describes.
        vocabulary_size: Number of training words, retained for provenance.

    Raises:
        ValueError: If ``backoff_log_prob`` is not a finite, non-positive
            number, or if a transition value is not a finite number.
    """

    BOUNDARY_START = "^"
    BOUNDARY_END = "$"

    def __init__(
        self,
        transitions: Mapping[str, Mapping[str, float]],
        *,
        backoff_log_prob: float,
        alphabet: str,
        language: Language = Language.EN,
        vocabulary_size: int = 0,
    ) -> None:
        backoff = float(backoff_log_prob)
        if not math.isfinite(backoff) or backoff > 0.0:
            raise ValueError(
                f"backoff_log_prob must be a finite log-probability <= 0, got {backoff!r}"
            )
        table: dict[str, Mapping[str, float]] = {}
        for prev, row in transitions.items():
            converted: dict[str, float] = {}
            for nxt, value in row.items():
                number = float(value)
                if not math.isfinite(number):
                    raise ValueError(
                        f"transition {prev!r} -> {nxt!r} is not a finite log-probability"
                    )
                converted[str(nxt)] = number
            table[str(prev)] = MappingProxyType(converted)
        self._transitions: Mapping[str, Mapping[str, float]] = MappingProxyType(table)
        self._backoff_log_prob = backoff
        self._alphabet = str(alphabet)
        self._language = _as_language(language)
        self._vocabulary_size = int(vocabulary_size)

    # -- introspection ----------------------------------------------------
    @property
    def language(self) -> Language:
        """Language this model was trained on."""
        return self._language

    @property
    def alphabet(self) -> str:
        """Letters covered by the model, excluding the boundary symbols."""
        return self._alphabet

    @property
    def backoff_log_prob(self) -> float:
        """Log-probability of a transition the model has never seen.

        Derivation (see :meth:`train`): with add-k smoothing over a symbol set
        of size ``V``, the probability of an unseen transition out of context
        ``p`` is ``k / (N_p + k * V)`` where ``N_p`` is the number of training
        transitions observed out of ``p``. That quantity is smallest for the
        *most frequent* context, so the model reports

            ``backoff = log(k) - log(max_p N_p + k * V)``

        which is a true global floor: every stored value satisfies
        ``log P(next | prev) >= backoff``. :meth:`normalized_score` relies on
        that property to rescale scores into ``[0, 1]``.
        """
        return self._backoff_log_prob

    @property
    def vocabulary_size(self) -> int:
        """Number of training words behind the model (``0`` when unknown)."""
        return self._vocabulary_size

    @property
    def order(self) -> int:
        """N-gram order; always ``2`` (character bigrams)."""
        return _ORDER

    @property
    def transitions(self) -> Mapping[str, Mapping[str, float]]:
        """Read-only view of the ``prev -> {next: log_prob}`` table."""
        return self._transitions

    @property
    def is_uniform(self) -> bool:
        """Whether the model carries no observed transitions at all.

        A uniform model assigns :attr:`backoff_log_prob` to every transition; it
        is what :meth:`uniform` builds and what :meth:`load` degrades to when no
        resource is bundled for a language.
        """
        return not self._transitions

    def __repr__(self) -> str:  # pragma: no cover - display helper
        return (
            f"CharNGramModel(language={self._language.value!r}, "
            f"alphabet_size={len(self._alphabet)}, "
            f"contexts={len(self._transitions)}, "
            f"backoff_log_prob={self._backoff_log_prob:.6f})"
        )

    # -- construction -----------------------------------------------------
    @classmethod
    def load(
        cls, language: Language = Language.EN, *, path: Optional[Path] = None
    ) -> CharNGramModel:
        """Return a shared model for ``language``, memoised per ``(language, path)``.

        A missing *bundled* model is not an error: the call degrades to
        :meth:`uniform` so that ``Phi(A)`` stays defined (and constant) instead
        of crashing the engine. An explicit ``path`` that cannot be read *is* an
        error, because the caller asked for that specific file.

        Args:
            language: Language whose bundled model is wanted.
            path: Optional override pointing at a model JSON (``.json`` or
                ``.json.gz``).

        Returns:
            A cached, thread-safe :class:`CharNGramModel`.

        Raises:
            ResourceNotFoundError: If ``path`` is given but unreadable or not
                valid JSON.
            ValueError: If ``language`` is not a known language.
        """
        resolved = _as_language(language)
        return _load_model(resolved, Path(path) if path is not None else None)

    @classmethod
    def bundled(cls, language: Language = Language.EN) -> CharNGramModel:
        """Load the model shipped inside the package for ``language``.

        Args:
            language: Language whose bundled resource is wanted.

        Returns:
            The parsed :class:`CharNGramModel`.

        Raises:
            ResourceNotFoundError: If no ``ngram_<lang>.json`` is bundled, or it
                is malformed. Callers that prefer graceful degradation should
                use :meth:`load`.
            ValueError: If ``language`` is not a known language.
        """
        resolved = _as_language(language)
        for name in (f"ngram_{resolved.value}.json", f"ngram_{resolved.value}.json.gz"):
            if has_resource(name):
                payload = read_json_resource(name)
                try:
                    return cls.from_dict(payload)
                except ValueError as exc:
                    raise ResourceNotFoundError(
                        f"Bundled resource {name!r} is not a valid n-gram model: {exc}"
                    ) from exc
        raise ResourceNotFoundError(
            f"No bundled n-gram model for language {resolved.value!r} "
            f"(expected resource 'ngram_{resolved.value}.json')"
        )

    @classmethod
    def from_path(cls, path: Path) -> CharNGramModel:
        """Read a model from a JSON file on disk.

        Args:
            path: File to read. A ``.gz`` suffix is transparently decompressed.

        Returns:
            The parsed :class:`CharNGramModel`.

        Raises:
            ResourceNotFoundError: If the file is missing, unreadable, not valid
                UTF-8/JSON, or not a well-formed model payload.
        """
        target = Path(path)
        try:
            raw = target.read_bytes()
            if target.name.endswith(".gz"):
                raw = gzip.decompress(raw)
            payload = json.loads(raw.decode("utf-8"))
        except (OSError, EOFError, UnicodeDecodeError, ValueError) as exc:
            raise ResourceNotFoundError(
                f"N-gram model {str(target)!r} could not be read: {exc}"
            ) from exc
        try:
            return cls.from_dict(payload)
        except ValueError as exc:
            raise ResourceNotFoundError(
                f"N-gram model {str(target)!r} is malformed: {exc}"
            ) from exc

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> CharNGramModel:
        """Build a model from a decoded ``ngram_<lang>.json`` document.

        Boundary symbols declared in the payload are re-mapped onto
        :attr:`BOUNDARY_START` / :attr:`BOUNDARY_END`, so a file written with
        different sentinels still loads correctly.

        Args:
            payload: Mapping with at least ``transitions``, ``alphabet`` and
                ``backoff_log_prob``; ``language``, ``order``, ``boundary_start``,
                ``boundary_end`` and ``vocabulary_size`` are optional.

        Returns:
            The constructed :class:`CharNGramModel`.

        Raises:
            ValueError: If a required key is missing or a value has the wrong
                shape or type.
        """
        if not isinstance(payload, Mapping):
            raise ValueError(f"n-gram payload must be a mapping, got {type(payload).__name__}")
        for key in ("transitions", "alphabet", "backoff_log_prob"):
            if key not in payload:
                raise ValueError(f"n-gram payload is missing required key {key!r}")
        order = int(payload.get("order", _ORDER))
        if order != _ORDER:
            raise ValueError(f"only bigram models (order 2) are supported, got order {order}")
        raw_transitions = payload["transitions"]
        if not isinstance(raw_transitions, Mapping):
            raise ValueError("'transitions' must be a mapping of prev -> {next: log_prob}")
        start = str(payload.get("boundary_start", cls.BOUNDARY_START)) or cls.BOUNDARY_START
        end = str(payload.get("boundary_end", cls.BOUNDARY_END)) or cls.BOUNDARY_END
        table: dict[str, dict[str, float]] = {}
        for prev, row in raw_transitions.items():
            if not isinstance(row, Mapping):
                raise ValueError(f"transition row for {prev!r} must be a mapping")
            key = cls.BOUNDARY_START if prev == start else str(prev)
            target = table.setdefault(key, {})
            for nxt, value in row.items():
                if not isinstance(value, (int, float)) or isinstance(value, bool):
                    raise ValueError(
                        f"transition {prev!r} -> {nxt!r} must be a number, "
                        f"got {type(value).__name__}"
                    )
                target[cls.BOUNDARY_END if nxt == end else str(nxt)] = float(value)
        try:
            language = _as_language(payload.get("language", Language.EN))
        except ValueError as exc:
            raise ValueError(f"n-gram payload declares an unknown language: {exc}") from exc
        return cls(
            table,
            backoff_log_prob=float(payload["backoff_log_prob"]),
            alphabet=str(payload["alphabet"]),
            language=language,
            vocabulary_size=int(payload.get("vocabulary_size", 0)),
        )

    @classmethod
    def train(
        cls,
        words: Iterable[str],
        *,
        language: Language = Language.EN,
        smoothing: float = 0.5,
    ) -> CharNGramModel:
        """Fit an add-k (Lidstone) smoothed bigram model to ``words``.

        The alphabet is *derived from the data* — the sorted set of alphabetic
        characters appearing in the case-folded training words — rather than
        hardcoded, so accented French/Spanish letters and German umlauts survive
        training. Each word is case-folded and reduced to characters present in
        that alphabet, then framed as
        ``BOUNDARY_START + word + BOUNDARY_END`` before its bigrams are counted.

        Smoothing runs over the symbol set ``alphabet + {BOUNDARY_START,
        BOUNDARY_END}`` of size ``V = len(alphabet) + 2``::

            log P(next | prev) = log(count(prev, next) + k) - log(N_prev + k * V)

        with ``N_prev`` the number of transitions observed out of ``prev``. The
        table is stored densely over the legal pairs — every context in
        ``alphabet + {BOUNDARY_START}`` crossed with every successor in
        ``alphabet + {BOUNDARY_END}`` — so probabilities are exact rather than
        approximated by the backoff. ``BOUNDARY_START`` is never a successor and
        ``BOUNDARY_END`` never a context, and the residual mass of each row is
        exactly the unemitted ``P(BOUNDARY_START | prev)`` term.

        Args:
            words: Training words; blanks and words with no alphabetic content
                are ignored.
            language: Language tag recorded on the model.
            smoothing: The Lidstone ``k``; must be strictly positive.

        Returns:
            The trained model, or :meth:`uniform` when ``words`` yields no
            usable training material.

        Raises:
            ValueError: If ``smoothing`` is not a finite positive number, or if
                ``language`` is not a known language.
        """
        resolved = _as_language(language)
        k = float(smoothing)
        if not math.isfinite(k) or k <= 0.0:
            raise ValueError(f"smoothing must be a finite positive float, got {smoothing!r}")

        folded_words: list[str] = []
        symbols: set[str] = set()
        for word in words:
            if not word:
                continue
            folded = word.strip().casefold()
            if not folded:
                continue
            folded_words.append(folded)
            symbols.update(char for char in folded if char.isalpha())
        alphabet = "".join(sorted(symbols))
        if not alphabet:
            return cls.uniform(language=resolved)

        allowed = frozenset(alphabet)
        counts: dict[str, dict[str, int]] = {}
        totals: dict[str, int] = {}
        trained_words = 0
        for folded in folded_words:
            filtered = "".join(char for char in folded if char in allowed)
            if not filtered:
                continue
            trained_words += 1
            sequence = cls.BOUNDARY_START + filtered + cls.BOUNDARY_END
            for index in range(len(sequence) - 1):
                prev = sequence[index]
                nxt = sequence[index + 1]
                row = counts.setdefault(prev, {})
                row[nxt] = row.get(nxt, 0) + 1
                totals[prev] = totals.get(prev, 0) + 1
        if not totals:
            return cls.uniform(language=resolved)

        vocabulary = len(alphabet) + 2
        prior = k * vocabulary
        backoff = math.log(k) - math.log(max(totals.values()) + prior)
        successors = [*sorted(alphabet), cls.BOUNDARY_END]
        transitions: dict[str, dict[str, float]] = {}
        for prev in [*sorted(alphabet), cls.BOUNDARY_START]:
            observed = counts.get(prev, {})
            denominator = math.log(totals.get(prev, 0) + prior)
            transitions[prev] = {
                nxt: math.log(observed.get(nxt, 0) + k) - denominator for nxt in successors
            }
        return cls(
            transitions,
            backoff_log_prob=backoff,
            alphabet=alphabet,
            language=resolved,
            vocabulary_size=trained_words,
        )

    @classmethod
    def uniform(cls, language: Language = Language.EN) -> CharNGramModel:
        """Build a usable, information-free model needing no resource file.

        Every transition evaluates to :attr:`backoff_log_prob`, which is set to
        ``-log(V)`` for a symbol set of size ``V = len(alphabet) + 2`` — exactly
        the uniform distribution over that set. ``Phi(A)`` is therefore a
        constant and contributes no ranking signal, and
        :meth:`normalized_score` reports the neutral value ``0.5`` (modulated by
        the vowel/consonant penalties) rather than a misleading ``0.0``.

        Args:
            language: Language whose default alphabet to use.

        Returns:
            A uniform :class:`CharNGramModel`.

        Raises:
            ValueError: If ``language`` is not a known language.
        """
        resolved = _as_language(language)
        alphabet = _DEFAULT_ALPHABETS.get(resolved, _LATIN_BASIC)
        return cls(
            {},
            backoff_log_prob=-math.log(len(alphabet) + 2),
            alphabet=alphabet,
            language=resolved,
            vocabulary_size=0,
        )

    # -- serialisation ----------------------------------------------------
    def to_dict(self) -> dict[str, Any]:
        """Return the JSON-compatible payload described by the resource format.

        Returns:
            A freshly built ``dict`` (safe for the caller to mutate) with the
            keys ``language``, ``order``, ``alphabet``, ``boundary_start``,
            ``boundary_end``, ``backoff_log_prob``, ``vocabulary_size`` and
            ``transitions``. Values are unrounded; ``tools/build_ngram_model.py``
            applies the 6-decimal rounding used in committed files.
        """
        return {
            "language": self._language.value,
            "order": _ORDER,
            "alphabet": self._alphabet,
            "boundary_start": self.BOUNDARY_START,
            "boundary_end": self.BOUNDARY_END,
            "backoff_log_prob": self._backoff_log_prob,
            "vocabulary_size": self._vocabulary_size,
            "transitions": {prev: dict(row) for prev, row in self._transitions.items()},
        }

    # -- querying ---------------------------------------------------------
    def log_prob(self, prev: str, nxt: str) -> float:
        """Return ``log P(nxt | prev)``, falling back to :attr:`backoff_log_prob`.

        Both symbols are case-folded before lookup, so callers may pass the
        uppercase characters of a candidate acronym directly. Boundary symbols
        pass through unchanged.

        Args:
            prev: The conditioning symbol.
            nxt: The successor symbol.

        Returns:
            A natural-log probability ``<= 0``; :attr:`backoff_log_prob` when
            the pair is unknown to the model.
        """
        row = self._transitions.get(prev.casefold())
        if row is None:
            return self._backoff_log_prob
        return row.get(nxt.casefold(), self._backoff_log_prob)

    def score(self, acronym: str) -> float:
        """Return ``Phi(A)``: the mean bigram log-likelihood of ``acronym``.

        Implements the reference formula exactly::

            Phi(A) = (1 / (k - 1)) * SUM_{m=1}^{k-1} log P(c_{m+1} | c_m)

        where ``k = len(A)`` and the logarithm is natural. Boundary symbols are
        *not* involved; use :meth:`score_with_boundaries` for those.

        **Convention:** a string shorter than two characters has no internal
        transition and therefore no defined mean, so this method returns
        :attr:`backoff_log_prob` — the model's floor — for ``len(acronym) < 2``.
        That keeps ``Phi`` on the same scale for every candidate length and
        makes one-character acronyms maximally unattractive rather than
        accidentally optimal.

        Args:
            acronym: The candidate string; case-folded internally.

        Returns:
            A natural-log score in ``[backoff_log_prob, 0]``.
        """
        chars = acronym.casefold()
        k = len(chars)
        if k < 2:
            return self._backoff_log_prob
        total = 0.0
        for index in range(k - 1):
            total += self.log_prob(chars[index], chars[index + 1])
        return total / (k - 1)

    def score_with_boundaries(self, acronym: str) -> float:
        """Return the mean bigram log-likelihood including word boundaries.

        Extends :meth:`score` with the ``BOUNDARY_START -> c_1`` and
        ``c_k -> BOUNDARY_END`` transitions, giving ``k + 1`` terms::

            (1 / (k + 1)) * [ log P(c_1 | ^) + SUM_{m=1}^{k-1} log P(c_{m+1} | c_m)
                              + log P($ | c_k) ]

        Defined for every ``k >= 1``; the empty string returns
        :attr:`backoff_log_prob`.

        Args:
            acronym: The candidate string; case-folded internally.

        Returns:
            A natural-log score in ``[backoff_log_prob, 0]``.
        """
        chars = acronym.casefold()
        k = len(chars)
        if k == 0:
            return self._backoff_log_prob
        total = self.log_prob(self.BOUNDARY_START, chars[0])
        for index in range(k - 1):
            total += self.log_prob(chars[index], chars[index + 1])
        total += self.log_prob(chars[-1], self.BOUNDARY_END)
        return total / (k + 1)

    def normalized_score(self, acronym: str) -> float:
        """Return a deterministic pronounceability score in ``[0.0, 1.0]``.

        Three documented steps:

        1. **Rescale.** :meth:`score_with_boundaries` is linearly mapped from
           ``[backoff_log_prob, 0]`` onto ``[0, 1]``::

               base = (raw - floor) / (0 - floor)      floor = backoff_log_prob

           and clamped. ``backoff_log_prob`` is a true global floor of the
           model (see its docstring), so ``base`` is meaningful for every input.
           A :attr:`is_uniform` model carries no information and would otherwise
           score every string at the floor, so it reports a neutral
           ``base = 0.5`` instead — matching the ``ngram=None`` convention used
           by ``scoring.Scorer``.
        2. **Vowel penalty.** ``base *= 0.35`` (:data:`NO_VOWEL_PENALTY`) when
           :func:`has_vowel` is ``False``; a vowel-free string cannot be
           pronounced as a word regardless of its bigram statistics.
        3. **Cluster penalty.** ``base *= 0.6``
           (:data:`CONSONANT_RUN_PENALTY`) when
           :func:`longest_consonant_run` exceeds
           :data:`MAX_CONSONANT_RUN` (``3``).

        The result is clamped into ``[0.0, 1.0]`` a final time and depends only
        on ``acronym`` and the model, never on iteration order or the clock.

        Args:
            acronym: The candidate string.

        Returns:
            ``0.0`` (unpronounceable) through ``1.0`` (maximally word-like).
        """
        if self.is_uniform:
            base = _UNIFORM_NEUTRAL_SCORE
        else:
            floor = self._backoff_log_prob
            span = -floor
            if span <= 0.0:  # pragma: no cover - defensive; floor is always < 0
                base = 1.0
            else:
                base = _clamp_unit((self.score_with_boundaries(acronym) - floor) / span)
        if not has_vowel(acronym):
            base *= NO_VOWEL_PENALTY
        if longest_consonant_run(acronym) > MAX_CONSONANT_RUN:
            base *= CONSONANT_RUN_PENALTY
        return _clamp_unit(base)


@cache
def _load_model(language: Language, path: Optional[Path]) -> CharNGramModel:
    """Memoised backing store for :meth:`CharNGramModel.load`.

    Args:
        language: Already-coerced language.
        path: Explicit model file, or ``None`` for the bundled resource.

    Returns:
        A shared :class:`CharNGramModel`.

    Raises:
        ResourceNotFoundError: If ``path`` is given and unreadable.
    """
    if path is not None:
        return CharNGramModel.from_path(path)
    try:
        return CharNGramModel.bundled(language)
    except ResourceNotFoundError:
        return CharNGramModel.uniform(language=language)


def pronounceability(word: str, model: Optional[CharNGramModel] = None) -> float:
    """Convenience wrapper returning a pronounceability score in ``[0, 1]``.

    Args:
        word: The string to assess.
        model: Model to score against. When omitted, the shared English model
            from :meth:`CharNGramModel.load` is used (itself degrading to
            :meth:`CharNGramModel.uniform` if no resource is bundled).

    Returns:
        The value of :meth:`CharNGramModel.normalized_score`.
    """
    resolved = model if model is not None else CharNGramModel.load(Language.EN)
    return resolved.normalized_score(word)
