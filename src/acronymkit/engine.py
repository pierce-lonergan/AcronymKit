"""The public facade: one configured object that owns every subsystem.

:class:`AcronymEngine` is the only class most users need. It wires the
tokenizer, the NLP backend, the scorer, the forward generator, the backronym
generator, the Schwartz & Hearst extractor and the lexical disambiguator into a
single object whose methods return fully populated, JSON-serialisable results.

Construction cost
-----------------
Building an engine resolves the Tier 1 backend once (via
:func:`~acronymkit.nlp.base.resolve_backend`) and builds a
:class:`~acronymkit.tokenizer.Tokenizer`. It does **not** read the lexicon or
the character n-gram model: those are the two expensive resources, and they are
loaded the first time a call actually needs them and then cached on the
instance. A process that constructs an engine and never generates anything pays
for neither.

Injected collaborators
----------------------
:meth:`AcronymEngine.__init__` takes four keyword-only collaborators —
``backend``, ``tokenizer``, ``extractor`` and ``scorer`` — each of which
replaces the object the engine would otherwise have built. This is the socket
:class:`~acronymkit.nlp.base.NlpBackend` was always documented as: a caller with
their own tagger hands it over, rather than assigning to a private slot.

Injection is plain constructor wiring. There is no registry, no entry-point
group and no discovery, so nothing here is reachable at import time and nothing
new lands in :data:`sys.modules`.

Supplying a ``backend`` skips :func:`~acronymkit.nlp.base.resolve_backend`
entirely, so no *availability probe* runs — and the probe is the part that
tries to import spaCy or NLTK and load a model. It does not skip the adapter
modules themselves: :mod:`acronymkit.nlp` binds ``heuristic``, ``spacy_backend``
and ``nltk_backend`` eagerly in its own ``__init__``, so importing anything from
:mod:`acronymkit.nlp.base` binds all three whatever this class does. Those
modules import no optional dependency at module scope, which is why that is a
purity question already settled elsewhere rather than one injection can move.

Two consequences are worth stating outright rather than leaving to be
discovered.

**An injected backend replaces tier resolution, not just its result.**
:attr:`AcronymEngine.engine_tier` is recomputed from the supplied backend, so
the metadata never describes an annotator that did not run. Because no
resolution happens, no availability probe runs, no degradation warning is
produced, and :attr:`~acronymkit.config.Config.strict` and
:class:`~acronymkit.exceptions.TierUnavailableError` do not apply: the caller
handing over the annotator *is* the availability decision. ``requested_tier``
still records what the configuration asked for, so the two fields together
remain the honest account of what happened.

**An injected scorer re-ranks; it does not re-search.** See "Substituting a
scorer" on :class:`~acronymkit.scoring.Scorer` for the exact boundary and for
the metadata field that says when it binds.

Thread safety
-------------
An engine built with no injected collaborators is safe to share across a thread
pool or an event loop, which is exactly what
:meth:`AcronymEngine.batch_generate` and :meth:`AcronymEngine.abatch_generate`
do. That is not a property of the class. It holds because the engine *builds*
everything it holds, and everything it builds is immutable — a frozen
:class:`~acronymkit.config.Config`, a stateless backend, stateless generators.

**Injection makes the guarantee conditional, and the engine cannot check it.**
An object arriving through ``backend``, ``tokenizer``, ``extractor`` or
``scorer`` may carry per-call state, memoise into a mutable attribute, or wrap a
runtime that is not reentrant — spaCy pipelines and NLTK's model loaders both
have shapes like this — and no inspection at construction time can tell. An
engine built with such a collaborator is exactly as safe to share as that
collaborator is, and no safer. A caller who needs the unconditional guarantee
either injects nothing, or injects only objects that are themselves immutable.

The lazy resources are initialised with plain double-checked assignment and no
lock. That is correct here rather than merely convenient, for two reasons:

* the loaders behind them (:meth:`~acronymkit.lexicon.Lexicon.load`,
  :meth:`~acronymkit.phonetics.CharNGramModel.load`) are ``lru_cache``-backed
  and referentially transparent, so two threads racing on the same slot obtain
  the *same* object and the duplicated work is a wasted dictionary lookup, not a
  divergent state; and
* every derived object (:class:`~acronymkit.scoring.Scorer`,
  :class:`~acronymkit.generator.ForwardGenerator`,
  :class:`~acronymkit.backronym.BackronymGenerator`) is immutable and depends
  only on those cached resources plus the frozen config, so any instance a race
  might produce is interchangeable with any other.

The store itself is a single attribute assignment, which is atomic, so no reader
can ever observe a half-built object. A lock would serialise every first call to
buy nothing.

Import cost
-----------
:mod:`asyncio` is imported inside :meth:`AcronymEngine.agenerate` rather than at
module scope, for the reason set out under "Import cost" in
:mod:`acronymkit.batch`: it is the single most expensive import this package
would otherwise perform, and the synchronous API — which is what the CLI and
most callers use — must not pay for it.

Observability
-------------
Every method times itself with :func:`time.perf_counter` and stamps an
:class:`~acronymkit.models.EngineMetadata` onto its result:
``requested_tier`` is what the configuration asked for, ``engine_tier`` is what
was actually achieved, ``nlp_backend`` names the resolved annotator,
``library_version`` records the installed distribution version, and ``warnings``
carries every degradation notice produced while resolving the tier — on *every*
result, not just the first.

Example:
    >>> from acronymkit import AcronymEngine
    >>> engine = AcronymEngine()
    >>> engine.generate("Application Programming Interface").primary_acronym
    'API'
    >>> engine.generate("Portable Document Format").primary_acronym
    'PDF'
"""

from __future__ import annotations

import time
from typing import Iterable, Optional, Sequence

from .backronym import BackronymGenerator
from .batch import arun_batch, run_batch
from .config import Config
from .disambiguation import ExpansionDictionary, LexicalDisambiguator
from .enums import EngineTier
from .exceptions import EmptyPhraseError, NoCandidateError
from .extractor import AbbreviationExtractor
from .generator import ForwardGenerator
from .lexicon import Lexicon
from .models import (
    AcronymCandidate,
    AcronymPair,
    AcronymResult,
    BackronymResult,
    BatchResult,
    DisambiguationResult,
    EngineMetadata,
    ExtractionResult,
    Token,
)
from .nlp.base import NlpBackend, resolve_backend
from .phonetics import CharNGramModel
from .scoring import Scorer
from .tokenizer import Tokenizer

__all__ = ["AcronymEngine"]


#: Milliseconds per second, for ``execution_time_ms``.
_MS_PER_SECOND = 1000.0

#: Reported as ``library_version`` when the distribution metadata is absent
#: (running straight from a source checkout that was never installed).
_FALLBACK_VERSION = "0.1.0"

#: :attr:`~acronymkit.nlp.heuristic.HeuristicBackend.name`. A resolved backend
#: with this name means no Tier 1 runtime was used.
_HEURISTIC_BACKEND = "heuristic"


def _library_version() -> str:
    """Return the version string reported on every result.

    The package's own ``__version__`` is the single source of truth, so the
    engine borrows it rather than querying the distribution metadata a second
    time. The import is deferred to call time because :mod:`acronymkit` imports
    this module while it is still initialising.

    Returns:
        The installed distribution version, or :data:`_FALLBACK_VERSION` when
        the package metadata is unavailable.
    """
    try:
        from . import __version__ as package_version
    except ImportError:  # pragma: no cover - only during a partial import
        return _FALLBACK_VERSION
    return str(package_version) or _FALLBACK_VERSION


def _achieved_tier(backend_name: str) -> EngineTier:
    """Return the tier a resolved backend actually delivers.

    The mapping is deliberately about capability rather than intent: a request
    for :attr:`~acronymkit.enums.EngineTier.HYBRID_NLP`,
    :attr:`~acronymkit.enums.EngineTier.NEURAL` or
    :attr:`~acronymkit.enums.EngineTier.AUTO` is a *policy*, and what the
    caller needs to read off the metadata is which path ran. Tier 2 is not
    implemented in this release, so no backend ever reports it.

    Applied to an *injected* backend as well as a resolved one, which is the
    whole point: the name is the only capability signal a structurally typed
    collaborator carries, so a backend that calls itself ``"heuristic"`` is
    reported as Tier 0 and every other name as Tier 1. A caller who wants their
    tagger to read as Tier 0 names it accordingly.

    Args:
        backend_name: :attr:`~acronymkit.nlp.base.NlpBackend.name` of the
            backend in force, whether resolved or supplied by the caller.

    Returns:
        :attr:`~acronymkit.enums.EngineTier.ZERO_DEPENDENCY` for the heuristic
        backend, otherwise
        :attr:`~acronymkit.enums.EngineTier.STATISTICAL_NLP`.
    """
    if backend_name == _HEURISTIC_BACKEND:
        return EngineTier.ZERO_DEPENDENCY
    return EngineTier.STATISTICAL_NLP


class AcronymEngine:
    """Configured, reusable entry point to every ``acronymkit`` capability.

    Construct one per configuration and share it. An engine built from a
    configuration alone holds no per-call state and is thread-safe; see "Thread
    safety" in :mod:`acronymkit.engine` for what an injected collaborator does
    to that guarantee.

    Example:
        >>> from acronymkit import AcronymEngine, Config
        >>> engine = AcronymEngine(Config(max_candidates=3))
        >>> result = engine.generate("Portable Document Format")
        >>> result.primary_acronym
        'PDF'
        >>> result.metadata.nlp_backend
        'heuristic'
        >>> engine.extract_definitions("The World Health Organization (WHO) met.")[0].short_form
        'WHO'

    Supplying a tagger of your own, which is what
    :class:`~acronymkit.nlp.base.NlpBackend` is for:

        >>> from acronymkit import AcronymEngine, NlpBackend
        >>> class PassThrough:
        ...     name = "passthrough"
        ...     def is_available(self) -> bool:
        ...         return True
        ...     def annotate(self, text, tokens):
        ...         return tokens
        >>> isinstance(PassThrough(), NlpBackend)
        True
        >>> engine = AcronymEngine(backend=PassThrough())
        >>> engine.nlp_backend
        'passthrough'
        >>> engine.generate("Portable Document Format").primary_acronym
        'PDF'

    Args:
        config: Engine configuration. ``None`` uses the shipped defaults
            (Tier 0, English, balanced-pronounceable weights).
        backend: Annotator to use instead of resolving one. Supplying it
            replaces tier resolution outright:
            :func:`~acronymkit.nlp.base.resolve_backend` is not called, no
            availability probe runs, no degradation warning is produced, and
            ``config.strict`` cannot raise
            :class:`~acronymkit.exceptions.TierUnavailableError` — handing over
            the annotator *is* the availability decision.
            :attr:`engine_tier` is recomputed from ``backend.name`` (see
            :func:`_achieved_tier`) so the metadata still names the tier that
            actually ran, and :attr:`~acronymkit.models.EngineMetadata.requested_tier`
            still records what the configuration asked for.
            :meth:`~acronymkit.nlp.base.NlpBackend.is_available` is never
            consulted on an injected backend.
        tokenizer: Tokenizer to use instead of building one from ``config``.
            It is the token stream every method works from, including the one
            the default ``extractor`` and the disambiguator are built on.
        extractor: Definition extractor to use instead of building one. When
            omitted, the default is built from the *effective* tokenizer, so
            injecting only ``tokenizer`` propagates to extraction.
        scorer: Scorer to use instead of building one from the lexicon and the
            n-gram model. It decides the ranking of every candidate the engine
            returns and it does **not** decide which candidates the forward
            search produces; that boundary, and the metadata field that says
            when it binds, are documented under "Substituting a scorer" on
            :class:`~acronymkit.scoring.Scorer`. Supplying one also means the
            lexicon and the n-gram model are never loaded on its behalf.

    Raises:
        TierUnavailableError: If ``config`` demands a tier whose runtime is not
            installed and forbids degradation (``STATISTICAL_NLP`` with no
            spaCy/NLTK, ``NEURAL``/``HYBRID_NLP`` under ``Config.strict``).
            Never raised when ``backend`` is supplied.
    """

    __slots__ = (
        "_backend",
        "_backronym",
        "_config",
        "_engine_tier",
        "_extractor",
        "_generator",
        "_lexicon",
        "_ngram",
        "_scorer",
        "_tokenizer",
        "_version",
        "_warnings",
    )

    def __init__(
        self,
        config: Optional[Config] = None,
        *,
        backend: Optional[NlpBackend] = None,
        tokenizer: Optional[Tokenizer] = None,
        extractor: Optional[AbbreviationExtractor] = None,
        scorer: Optional[Scorer] = None,
    ) -> None:
        self._config: Config = config if config is not None else Config()
        notices: Sequence[str] = ()
        if backend is None:
            backend, notices = resolve_backend(self._config)
        self._backend: NlpBackend = backend
        self._warnings: tuple[str, ...] = tuple(notices)
        # Derived from the backend that will actually annotate, injected or
        # resolved. Reading it off the resolution result instead would report
        # the tier of a backend that never ran.
        self._engine_tier: EngineTier = _achieved_tier(backend.name)
        self._version: str = _library_version()
        self._tokenizer = tokenizer if tokenizer is not None else Tokenizer(self._config)
        # Built from the *effective* tokenizer, so injecting one propagates.
        self._extractor = (
            extractor
            if extractor is not None
            else AbbreviationExtractor(self._config, self._tokenizer)
        )
        # Lazily populated; see the module docstring for the locking rationale.
        # An injected scorer is simply the resolved value of that slot, so the
        # lexicon and the n-gram model are never loaded to build one.
        self._lexicon: Optional[Lexicon] = None
        self._ngram: Optional[CharNGramModel] = None
        self._scorer: Optional[Scorer] = scorer
        self._generator: Optional[ForwardGenerator] = None
        self._backronym: Optional[BackronymGenerator] = None

    def __repr__(self) -> str:  # pragma: no cover - display helper
        return (
            f"AcronymEngine(tier={self._engine_tier.value!r}, "
            f"backend={self._backend.name!r}, "
            f"language={self._config.language.value!r})"
        )

    # -- collaborators -----------------------------------------------------
    @property
    def config(self) -> Config:
        """The configuration this engine was built from."""
        return self._config

    @property
    def backend(self) -> NlpBackend:
        """The annotator in force — the injected one, or the resolved one."""
        return self._backend

    @property
    def nlp_backend(self) -> str:
        """Name of the annotation backend in force, e.g. ``'heuristic'``."""
        return self._backend.name

    @property
    def engine_tier(self) -> EngineTier:
        """The tier actually in force, derived from the backend that will run.

        Computed from :attr:`nlp_backend` by :func:`_achieved_tier`, for an
        injected backend exactly as for a resolved one, so this never reports
        the tier of an annotator that was replaced.
        """
        return self._engine_tier

    @property
    def warnings(self) -> tuple[str, ...]:
        """Degradation notices stamped onto every result this engine produces.

        Empty when a ``backend`` was injected: no resolution ran, so there is
        no degradation to report. Missing-resource notices raised later by
        :attr:`lexicon` and :attr:`ngram` still accumulate here.
        """
        return self._warnings

    @property
    def tokenizer(self) -> Tokenizer:
        """The tokenizer in force — the injected one, or one built from config."""
        return self._tokenizer

    @property
    def extractor(self) -> AbbreviationExtractor:
        """The Schwartz & Hearst extractor in force, injected or built."""
        return self._extractor

    @property
    def lexicon(self) -> Lexicon:
        """The language lexicon backing ``Lambda(A)``, loaded on first access.

        A language with no bundled lexicon degrades to an empty one rather than
        raising, which keeps generation working — but it makes ``Lambda(A)``
        identically zero, so a dictionary hit can never be reported. That is
        recorded in :attr:`EngineMetadata.warnings` rather than left silent:
        silently answering "not a word" for every candidate is exactly the kind
        of degradation a caller needs to know about.
        """
        lexicon = self._lexicon
        if lexicon is None:
            lexicon = Lexicon.load(self._config.language, path=self._config.lexicon_path)
            self._lexicon = lexicon
            if not len(lexicon) and self._config.lexicon_path is None:
                self._note_resource_gap(
                    f"no bundled lexicon for language {self._config.language.value!r}: "
                    "Lambda(A) is always 0, so no candidate can be reported as a "
                    "dictionary word. Supply one with Config(lexicon_path=...); see "
                    "tools/build_lexicons.py."
                )
        return lexicon

    @property
    def ngram(self) -> CharNGramModel:
        """The character n-gram model backing ``Phi(A)``, loaded on first access.

        With no bundled model the loader returns a uniform one, under which every
        transition is equally likely and ``Phi(A)`` therefore carries no
        information. Ranking still works — the positional term dominates — but
        pronounceability stops discriminating, which is recorded as a warning.
        """
        ngram = self._ngram
        if ngram is None:
            ngram = CharNGramModel.load(self._config.language, path=self._config.ngram_model_path)
            self._ngram = ngram
            if ngram.is_uniform and self._config.ngram_model_path is None:
                self._note_resource_gap(
                    f"no bundled n-gram model for language "
                    f"{self._config.language.value!r}: Phi(A) is uniform, so "
                    "pronounceability cannot discriminate between candidates."
                )
        return ngram

    def _note_resource_gap(self, message: str) -> None:
        """Record a missing-resource warning once, for every later result.

        Args:
            message: Human-readable description of what degraded and how to fix it.
        """
        if message not in self._warnings:
            self._warnings = (*self._warnings, message)

    @property
    def scorer(self) -> Scorer:
        """The shared scorer: the injected one, else built from the resources.

        When a ``scorer`` was supplied to :meth:`__init__` this returns it and
        neither :attr:`lexicon` nor :attr:`ngram` is loaded on its behalf. See
        "Substituting a scorer" on :class:`~acronymkit.scoring.Scorer` for what
        a custom scorer does and does not control.
        """
        scorer = self._scorer
        if scorer is None:
            scorer = Scorer(self._config, self.lexicon, self.ngram)
            self._scorer = scorer
        return scorer

    @property
    def generator(self) -> ForwardGenerator:
        """The forward (phrase -> acronym) generator, built on first access."""
        generator = self._generator
        if generator is None:
            generator = ForwardGenerator(self._config, self.scorer)
            self._generator = generator
        return generator

    @property
    def backronym_generator(self) -> BackronymGenerator:
        """The backronym generator, built on first access."""
        backronym = self._backronym
        if backronym is None:
            backronym = BackronymGenerator(self._config, self.scorer, self.lexicon)
            self._backronym = backronym
        return backronym

    # -- analysis ----------------------------------------------------------
    def tokenize(self, text: str) -> list[Token]:
        """Tokenise ``text`` and annotate it with the resolved NLP backend.

        This is exactly the token stream every other method works from and the
        one returned on :attr:`~acronymkit.models.AcronymResult.tokens`, so it
        is the way to inspect what the engine believes about a phrase.

        Args:
            text: Raw input text.

        Returns:
            The analysed tokens in phrase order; an empty list for blank input.
        """
        tokens = self._tokenizer.tokenize(text)
        if not tokens:
            return tokens
        return self._backend.annotate(text, tokens)

    def generate(self, phrase: str) -> AcronymResult:
        """Generate ranked acronym candidates for ``phrase``.

        The phrase is tokenised, annotated by the resolved backend and handed to
        the beam search in :class:`~acronymkit.generator.ForwardGenerator`. The
        plain initialism is always among the returned candidates (see that
        module), so conventional phrases keep their conventional acronym.

        Args:
            phrase: The text to abbreviate.

        Returns:
            An :class:`~acronymkit.models.AcronymResult` whose
            ``primary_acronym`` and ``score`` come from the best candidate and
            whose ``alternatives`` is the full ranked list with that candidate
            at index ``0``.

        Raises:
            EmptyPhraseError: If ``phrase`` is blank, whitespace-only, or
                reduced to nothing by the active stop-word, minimum-length and
                numeral filters.
            NoCandidateError: If no candidate survived the configured length,
                vowel or dictionary constraints.

        Example:
            >>> from acronymkit import AcronymEngine
            >>> AcronymEngine().generate("Portable Document Format").primary_acronym
            'PDF'
        """
        started = time.perf_counter()
        tokens = self.tokenize(phrase)
        if not tokens:
            raise EmptyPhraseError(f"phrase {phrase!r} contains no tokens to build an acronym from")
        if not any(token.is_eligible and token.letters for token in tokens):
            raise EmptyPhraseError(
                f"phrase {phrase!r} has no acronym-eligible tokens: every token was "
                "removed by the active stop-word, minimum-word-length or numeral policy"
            )
        candidates, evaluated, truncated = self.generator.generate(tokens)
        primary = candidates[0]
        return AcronymResult(
            source_phrase=phrase,
            primary_acronym=primary.acronym,
            score=primary.score,
            alternatives=candidates[: self._config.max_candidates],
            tokens=tokens,
            metadata=self._metadata(
                started,
                tokens_processed=len(tokens),
                candidates_evaluated=evaluated,
                truncated=truncated,
            ),
        )

    def score(self, acronym: str, phrase: str) -> AcronymCandidate:
        """Score an acronym the caller already has against ``phrase``.

        The acronym is aligned onto the phrase's tokens by the same k-best
        aligner :meth:`generate_backronym` uses — letters map to tokens in
        strictly increasing order, preferring word initials — and the resulting
        alignment is scored by the shared
        :class:`~acronymkit.scoring.Scorer`. The returned candidate is therefore
        directly comparable with anything :meth:`generate` produced.

        Args:
            acronym: The candidate acronym. Case and punctuation are
                normalised away: ``"p.d.f."`` is scored as ``"PDF"``.
            phrase: The phrase the acronym is meant to abbreviate.

        Returns:
            A fully populated :class:`~acronymkit.models.AcronymCandidate`,
            including the per-character
            :class:`~acronymkit.models.LetterMapping` trace and (when
            ``config.include_breakdown``) the term-by-term
            :class:`~acronymkit.models.ScoreBreakdown`.

        Raises:
            EmptyPhraseError: If ``phrase`` produces no tokens.
            NoCandidateError: If ``acronym`` holds no alphanumeric character.

        Example:
            >>> from acronymkit import AcronymEngine
            >>> candidate = AcronymEngine().score("PDF", "Portable Document Format")
            >>> [mapping.kind.value for mapping in candidate.mappings]
            ['initial', 'initial', 'initial']
        """
        tokens = self.tokenize(phrase)
        if not tokens:
            raise EmptyPhraseError(
                f"phrase {phrase!r} contains no tokens to score {acronym!r} against"
            )
        alignments = self.backronym_generator.align(acronym, tokens, limit=1)
        if not alignments:
            raise NoCandidateError(
                f"acronym {acronym!r} contains no alphanumeric character to score"
            )
        alignment = alignments[0]
        covered = {
            tokens[mapping.token_index].index
            for mapping in alignment.mappings
            if mapping.token_index is not None
        }
        return self.scorer.build_candidate(
            alignment.target_word, tokens, alignment.mappings, covered
        )

    # -- backronyms --------------------------------------------------------
    def generate_backronym(self, phrase: str, target_word: str) -> BackronymResult:
        """Fit ``target_word`` onto the words of ``phrase``.

        Args:
            phrase: The source phrase supplying the expansion words.
            target_word: The word the expansion must spell out. Case and
                punctuation are normalised away.

        Returns:
            A :class:`~acronymkit.models.BackronymResult` whose
            ``primary_expansion`` is the best alignment's ``expansion_text``.
            Letters that no token could supply are reported per candidate in
            ``unmapped_letters`` and reduce ``coverage``.

        Raises:
            EmptyPhraseError: If ``phrase`` produces no tokens.

        Example:
            >>> from acronymkit import AcronymEngine
            >>> result = AcronymEngine().generate_backronym(
            ...     phrase="Next Generation High Performance Storage System",
            ...     target_word="NEXUS",
            ... )
            >>> result.target_word
            'NEXUS'
            >>> result.candidates[0].coverage > 0.5
            True
        """
        started = time.perf_counter()
        tokens = self.tokenize(phrase)
        if not tokens:
            raise EmptyPhraseError(
                f"phrase {phrase!r} contains no tokens to build a backronym from"
            )
        candidates = self.backronym_generator.align(target_word, tokens)
        return BackronymResult(
            source_phrase=phrase,
            target_word=target_word,
            primary_expansion=candidates[0].expansion_text if candidates else "",
            score=candidates[0].score if candidates else 0.0,
            candidates=candidates,
            metadata=self._metadata(
                started,
                tokens_processed=len(tokens),
                candidates_evaluated=len(candidates),
            ),
        )

    def synthesize_backronym(
        self, target_word: str, *, vocabulary: Optional[Iterable[str]] = None
    ) -> BackronymResult:
        """Invent an expansion for ``target_word`` with no source phrase.

        Args:
            target_word: The word the expansion must spell out.
            vocabulary: Words to draw from. ``None`` uses the language lexicon,
                preferring words of 3 to 12 characters.

        Returns:
            A :class:`~acronymkit.models.BackronymResult` with an empty
            ``source_phrase``. An exhausted vocabulary yields an empty
            ``candidates`` list rather than an exception.

        Example:
            >>> from acronymkit import AcronymEngine
            >>> words = ["rapid", "agile", "modern"]
            >>> result = AcronymEngine().synthesize_backronym("RAM", vocabulary=words)
            >>> result.primary_expansion
            'rapid agile modern'
        """
        started = time.perf_counter()
        candidates = self.backronym_generator.synthesize(target_word, vocabulary=vocabulary)
        return BackronymResult(
            source_phrase="",
            target_word=target_word,
            primary_expansion=candidates[0].expansion_text if candidates else "",
            score=candidates[0].score if candidates else 0.0,
            candidates=candidates,
            metadata=self._metadata(
                started,
                tokens_processed=0,
                candidates_evaluated=len(candidates),
            ),
        )

    # -- extraction --------------------------------------------------------
    def extract_definitions(self, text: str) -> list[AcronymPair]:
        """Extract the abbreviation definitions ``text`` states explicitly.

        Implements Schwartz & Hearst (2003) over balanced ``()``, ``[]`` and
        ``{}`` regions, in both the ``Long Form (SF)`` and the inverted
        ``SF (Long Form)`` arrangements.

        Args:
            text: The document to scan.

        Returns:
            The pairs in document order, each carrying exact character spans
            into ``text``. Empty when the document defines nothing.

        Example:
            >>> from acronymkit import AcronymEngine
            >>> pairs = AcronymEngine().extract_definitions(
            ...     "The National Aeronautics and Space Administration (NASA) "
            ...     "launched the mission."
            ... )
            >>> pairs[0].short_form
            'NASA'
            >>> pairs[0].long_form
            'National Aeronautics and Space Administration'
        """
        return self._extractor.extract(text)

    def extract(self, text: str) -> ExtractionResult:
        """Extract abbreviation definitions and wrap them with engine metadata.

        The text is tokenised a second time purely to report
        ``metadata.tokens_processed``; call :meth:`extract_definitions` instead
        when only the pairs are wanted and the document is large.

        Args:
            text: The document to scan.

        Returns:
            An :class:`~acronymkit.models.ExtractionResult` holding the same
            pairs :meth:`extract_definitions` returns, plus the timing and tier
            envelope. ``metadata.candidates_evaluated`` counts the pairs found.
        """
        started = time.perf_counter()
        pairs = self._extractor.extract(text)
        tokens_processed = len(self._tokenizer.tokenize(text)) if text else 0
        return ExtractionResult(
            source_text=text,
            pairs=pairs,
            metadata=self._metadata(
                started,
                tokens_processed=tokens_processed,
                candidates_evaluated=len(pairs),
            ),
        )

    # -- disambiguation ----------------------------------------------------
    def disambiguate(
        self,
        acronym: str,
        context: str,
        dictionary: Optional[ExpansionDictionary] = None,
    ) -> DisambiguationResult:
        """Resolve a standalone ``acronym`` against the text it occurred in.

        **There are two paths here and only one of them disambiguates.**

        *Default path, no ``dictionary``.* The candidate set is built from the
        inline definitions found in **this call's** ``context`` and nothing
        else. There is no cross-call state anywhere in this engine: a term
        defined in one string is not remembered for the next one, and
        ``disambiguate("MS", later_sentence)`` returns ``None`` however many
        earlier calls defined ``MS``. To carry a definition across calls, pass
        the ``dictionary``. Within a single call the derived index is also
        *unable to add anything*: it is
        :meth:`~acronymkit.disambiguation.ExpansionDictionary.from_pairs` over
        this engine's extractor output, the disambiguator runs an extractor
        built from the same ``config`` and tokenizer over the same string, and
        it de-duplicates expansions before scoring -- so every candidate the
        derived index can supply has already been claimed at ``score = 1.0``
        with ``source == "inline"``. The one exception is an ``extractor``
        injected into this engine's constructor, which the disambiguator does
        not receive and therefore does not reproduce. The default path is
        otherwise an inline-definition lookup that performs no selection.

        **How little it does is measured, not estimated.** On the SDU@AAAI-21 AD
        dev split the default path returns *no candidate at all* on the large
        majority of instances, and has two candidates to choose between on one
        instance in the whole split -- so there is nothing to rank, nothing to
        score against the context, and no margin to gate on. The exact figures
        are ``disambiguation.sdu21.diagnosis.default_path.no_candidate_pct``,
        ``.two_or_more_candidates`` and
        ``disambiguation.sdu21.abstention_curve.default_path_margin_defined`` in
        ``bench/results.json``; ``docs/EVALUATION.md`` prints them. **If you
        came here for disambiguation, pass a ``dictionary``.**

        *Dictionary path.* Passing ``dictionary`` is what turns this into a
        choice: the blend documented on
        :meth:`~acronymkit.disambiguation.LexicalDisambiguator.disambiguate`
        scores every registered expansion against the context, and
        :attr:`~acronymkit.models.DisambiguationResult.margin` becomes
        meaningful because there is finally more than one candidate to have a
        margin between.

        Args:
            acronym: The short form to resolve, in any case or punctuation
                style.
            context: The surrounding sentence, paragraph or document.
            dictionary: Candidate expansions to consider. ``None`` derives one
                from ``context``, which as above can only reproduce that
                context's own inline definitions.

        Returns:
            A :class:`~acronymkit.models.DisambiguationResult` whose
            ``primary_expansion`` is the highest-scoring candidate, or ``None``
            when nothing could be proposed. An expansion the document itself
            defined scores ``1.0`` with ``source == "inline"``.

        Note:
            This facade has no abstention gate. ``min_margin`` is a constructor
            argument of
            :class:`~acronymkit.disambiguation.LexicalDisambiguator`, which a
            caller who wants to refuse low-margin answers should build directly
            over their dictionary. The gap is deliberate rather than pending:
            the gate needs two candidates to compare, and the default path here
            almost never has them.

        Example:
            The dictionary path, where a selection actually happens -- the same
            three-way vocabulary resolved two ways by two different sentences:

            >>> from acronymkit import AcronymEngine
            >>> from acronymkit.disambiguation import ExpansionDictionary
            >>> engine = AcronymEngine()
            >>> vocab = ExpansionDictionary(
            ...     {"MS": ["multiple sclerosis", "Microsoft", "mass spectrometry"]}
            ... )
            >>> engine.disambiguate(
            ...     "MS", "An MRI showed lesions consistent with MS.", vocab
            ... ).primary_expansion
            'multiple sclerosis'
            >>> engine.disambiguate(
            ...     "MS", "The MS suite bundles Word and Excel.", vocab
            ... ).primary_expansion
            'Microsoft'

            The default path, where none does. The answer comes from the
            sentence's own parenthetical definition, and a second call cannot
            reuse it:

            >>> engine.disambiguate(
            ...     "BP", "Blood pressure (BP) was elevated at admission."
            ... ).primary_expansion
            'Blood pressure'
            >>> engine.disambiguate("BP", "BP was elevated again today.") \\
            ...     .primary_expansion is None
            True
        """
        started = time.perf_counter()
        index = (
            dictionary
            if dictionary is not None
            else ExpansionDictionary.from_pairs(self._extractor.extract(context))
        )
        disambiguator = LexicalDisambiguator(self._config, index, self._tokenizer)
        result = disambiguator.disambiguate(acronym, context)
        return DisambiguationResult(
            acronym=result.acronym,
            context=result.context,
            primary_expansion=result.primary_expansion,
            candidates=result.candidates,
            metadata=self._metadata(
                started,
                tokens_processed=result.metadata.tokens_processed,
                candidates_evaluated=len(result.candidates),
                extra_warnings=result.metadata.warnings,
            ),
        )

    # -- batch and async ---------------------------------------------------
    def batch_generate(
        self, phrases: Sequence[str], *, max_workers: Optional[int] = None
    ) -> BatchResult:
        """Generate acronyms for many phrases on a thread pool.

        A phrase that fails never aborts the batch: its slot in ``results`` is
        ``None`` and its error message is recorded in ``errors`` under the same
        index.

        Args:
            phrases: The phrases, in submission order.
            max_workers: Thread-pool size; ``None`` sizes it automatically.

        Returns:
            A :class:`~acronymkit.models.BatchResult` positionally aligned with
            ``phrases``.

        Raises:
            ConfigurationError: If ``max_workers`` is given and is below ``1``.

        Example:
            >>> from acronymkit import AcronymEngine
            >>> batch = AcronymEngine().batch_generate(["Portable Document Format", ""])
            >>> batch.results[0].primary_acronym
            'PDF'
            >>> batch.failure_count
            1
        """
        return run_batch(self.generate, phrases, max_workers=max_workers)

    async def agenerate(self, phrase: str) -> AcronymResult:
        """Generate acronyms for ``phrase`` without blocking the event loop.

        The synchronous, CPU-bound search runs on a worker thread through
        :func:`asyncio.to_thread`.

        Args:
            phrase: The text to abbreviate.

        Returns:
            The same :class:`~acronymkit.models.AcronymResult` :meth:`generate`
            returns.

        Raises:
            EmptyPhraseError: If ``phrase`` yields no eligible tokens.
            NoCandidateError: If no candidate satisfied the constraints.
        """
        import asyncio  # deferred: see the import-cost note in acronymkit.batch

        return await asyncio.to_thread(self.generate, phrase)

    async def abatch_generate(
        self, phrases: Sequence[str], *, concurrency: Optional[int] = None
    ) -> BatchResult:
        """Generate acronyms for many phrases concurrently off the event loop.

        Args:
            phrases: The phrases, in submission order.
            concurrency: Maximum phrases in flight; ``None`` picks a bound from
                the CPU count.

        Returns:
            A :class:`~acronymkit.models.BatchResult` positionally aligned with
            ``phrases``, with per-phrase failures captured in ``errors``.

        Raises:
            ConfigurationError: If ``concurrency`` is given and is below ``1``.
        """
        return await arun_batch(self.generate, phrases, concurrency=concurrency)

    # -- internals ---------------------------------------------------------
    def _metadata(
        self,
        started: float,
        *,
        tokens_processed: int,
        candidates_evaluated: int = 0,
        truncated: bool = False,
        extra_warnings: Sequence[str] = (),
    ) -> EngineMetadata:
        """Build the observability envelope for one completed call.

        Args:
            started: :func:`time.perf_counter` reading taken when the call
                began.
            tokens_processed: Number of tokens analysed.
            candidates_evaluated: Work counter appropriate to the call —
                partial states for generation, pairs for extraction, candidates
                for disambiguation.
            truncated: Whether a search budget cut the work short.
            extra_warnings: Call-scoped warnings to append after the
                engine-scoped ones, de-duplicated and order-preserving.

        Returns:
            The populated :class:`~acronymkit.models.EngineMetadata`.
        """
        elapsed_ms = (time.perf_counter() - started) * _MS_PER_SECOND
        warnings = list(self._warnings)
        for warning in extra_warnings:
            if warning not in warnings:
                warnings.append(warning)
        return EngineMetadata(
            engine_tier=self._engine_tier,
            execution_time_ms=max(0.0, elapsed_ms),
            tokens_processed=tokens_processed,
            candidates_evaluated=candidates_evaluated,
            language=self._config.language,
            library_version=self._version,
            nlp_backend=self._backend.name,
            requested_tier=self._config.engine_tier,
            warnings=warnings,
            truncated=truncated,
        )
