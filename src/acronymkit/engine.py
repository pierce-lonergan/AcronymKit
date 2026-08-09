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

Thread safety
-------------
Everything the engine stores after construction is immutable — a frozen
:class:`~acronymkit.config.Config`, a stateless backend, stateless generators —
so a single engine is safe to share across a thread pool or an event loop, which
is exactly what :meth:`AcronymEngine.batch_generate` and
:meth:`AcronymEngine.abatch_generate` do.

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

    Args:
        backend_name: :attr:`~acronymkit.nlp.base.NlpBackend.name` of the
            resolved annotator.

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

    Construct one per configuration and share it: instances are thread-safe and
    hold no per-call state.

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

    Args:
        config: Engine configuration. ``None`` uses the shipped defaults
            (Tier 0, English, balanced-pronounceable weights).

    Raises:
        TierUnavailableError: If ``config`` demands a tier whose runtime is not
            installed and forbids degradation (``STATISTICAL_NLP`` with no
            spaCy/NLTK, ``NEURAL``/``HYBRID_NLP`` under ``Config.strict``).
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

    def __init__(self, config: Optional[Config] = None) -> None:
        self._config: Config = config if config is not None else Config()
        backend, warnings = resolve_backend(self._config)
        self._backend: NlpBackend = backend
        self._warnings: tuple[str, ...] = tuple(warnings)
        self._engine_tier: EngineTier = _achieved_tier(backend.name)
        self._version: str = _library_version()
        self._tokenizer = Tokenizer(self._config)
        self._extractor = AbbreviationExtractor(self._config, self._tokenizer)
        # Lazily populated; see the module docstring for the locking rationale.
        self._lexicon: Optional[Lexicon] = None
        self._ngram: Optional[CharNGramModel] = None
        self._scorer: Optional[Scorer] = None
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
    def nlp_backend(self) -> str:
        """Name of the resolved annotation backend, e.g. ``'heuristic'``."""
        return self._backend.name

    @property
    def engine_tier(self) -> EngineTier:
        """The tier actually in force, after availability resolution."""
        return self._engine_tier

    @property
    def warnings(self) -> tuple[str, ...]:
        """Degradation notices stamped onto every result this engine produces."""
        return self._warnings

    @property
    def tokenizer(self) -> Tokenizer:
        """The configured tokenizer."""
        return self._tokenizer

    @property
    def extractor(self) -> AbbreviationExtractor:
        """The configured Schwartz & Hearst extractor."""
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
        """The shared scorer, built on first access from the lazy resources."""
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

        When no ``dictionary`` is supplied the engine builds one from the
        context's own inline definitions (via
        :meth:`~acronymkit.disambiguation.ExpansionDictionary.from_pairs`), so a
        document that defines its abbreviations anywhere can resolve them
        everywhere without the caller assembling a vocabulary.

        Args:
            acronym: The short form to resolve, in any case or punctuation
                style.
            context: The surrounding sentence, paragraph or document.
            dictionary: Candidate expansions to consider. ``None`` derives one
                from ``context``.

        Returns:
            A :class:`~acronymkit.models.DisambiguationResult` whose
            ``primary_expansion`` is the highest-scoring candidate, or ``None``
            when nothing could be proposed. An expansion the document itself
            defined scores ``1.0`` with ``source == "inline"``.

        Example:
            >>> from acronymkit import AcronymEngine
            >>> result = AcronymEngine().disambiguate(
            ...     "BP", "Blood pressure (BP) was elevated at admission."
            ... )
            >>> result.primary_expansion
            'Blood pressure'
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
