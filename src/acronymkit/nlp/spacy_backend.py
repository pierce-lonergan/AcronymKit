"""spaCy-powered Tier 1 backend.

spaCy is an **optional** dependency. Nothing in this module imports it at
import time; every reference lives inside a function guarded by
``try/except``, so ``import acronymkit.nlp.spacy_backend`` succeeds on a
machine that has never heard of spaCy.

Pipelines are loaded once and shared: :data:`PIPELINE_CACHE` is a module-level
``{model_name: pipeline}`` dictionary protected by a lock, because a single
:class:`~acronymkit.engine.AcronymEngine` is documented as thread-safe.
"""

from __future__ import annotations

import threading
from collections.abc import Mapping, Sequence
from types import MappingProxyType
from typing import Any, Optional

from ..enums import Language
from ..models import Token
from .base import Annotation, BackendUnavailable, align_by_offsets, apply_annotations

__all__ = ["MODEL_BY_LANGUAGE", "SpacyBackend", "load_pipeline"]


#: Small, CPU-friendly pipeline per supported language.
MODEL_BY_LANGUAGE: Mapping[Language, str] = MappingProxyType(
    {
        Language.EN: "en_core_web_sm",
        Language.FR: "fr_core_news_sm",
        Language.ES: "es_core_news_sm",
        Language.DE: "de_core_news_sm",
    }
)

#: Components disabled at load time; we need tagging and lemmas, nothing else.
#: (The tagger, attribute ruler and lemmatizer must stay enabled.)
DISABLED_PIPES: tuple[str, ...] = ("parser", "ner")

#: ``{model_name: loaded pipeline}``. Populated lazily, never evicted.
PIPELINE_CACHE: dict[str, Any] = {}

#: Model names already known to be unloadable, so we probe them only once.
_FAILED_MODELS: set[str] = set()

_CACHE_LOCK = threading.Lock()


def _blank_pipeline(spacy_module: Any, language_code: str) -> Optional[Any]:
    """Try to build a blank pipeline with a usable tagger.

    A blank spaCy pipeline ships no weights, so the tagger it can add is
    untrained and would label every token with the empty string. Such a
    pipeline is rejected here rather than returned, since annotating with it
    would be strictly worse than the heuristic backend.

    Args:
        spacy_module: The already-imported ``spacy`` module.
        language_code: Two-letter code accepted by ``spacy.blank``.

    Returns:
        The pipeline when a *trained* tagger is available, else ``None``.
    """
    try:
        pipeline = spacy_module.blank(language_code)
        tagger = pipeline.add_pipe("tagger")
        if not getattr(tagger, "labels", ()):
            return None
        return pipeline
    except Exception:
        # Any spaCy failure here simply means "no usable blank pipeline".
        return None


def load_pipeline(model_name: str, language_code: str) -> Any:
    """Load (and memoise) a spaCy pipeline.

    Args:
        model_name: Installed model package, e.g. ``"en_core_web_sm"``.
        language_code: Two-letter code used for the blank-pipeline fallback.

    Returns:
        The cached ``spacy.language.Language`` pipeline.

    Raises:
        BackendUnavailable: If spaCy is not importable, or neither the model
            nor a trained blank pipeline could be produced.
    """
    with _CACHE_LOCK:
        cached = PIPELINE_CACHE.get(model_name)
        if cached is not None:
            return cached
        if model_name in _FAILED_MODELS:
            raise BackendUnavailable(
                f"spaCy model {model_name!r} is not loadable; install it with "
                f"python -m spacy download {model_name}"
            )

    try:
        import spacy
    except ImportError as exc:
        raise BackendUnavailable(
            "spaCy is not installed; install it with: pip install 'acronymkit[nlp]'"
        ) from exc

    pipeline: Optional[Any]
    try:
        pipeline = spacy.load(model_name, disable=list(DISABLED_PIPES))
    except Exception:
        # Missing model package, spaCy/model version mismatch, broken data
        # directory -- all handled identically by trying the blank fallback.
        pipeline = _blank_pipeline(spacy, language_code)

    if pipeline is None:
        with _CACHE_LOCK:
            _FAILED_MODELS.add(model_name)
        raise BackendUnavailable(
            f"spaCy model {model_name!r} is not installed; install it with "
            f"python -m spacy download {model_name}"
        )

    with _CACHE_LOCK:
        PIPELINE_CACHE.setdefault(model_name, pipeline)
        return PIPELINE_CACHE[model_name]


class SpacyBackend:
    """Tier 1 annotator backed by a small spaCy pipeline.

    Construction is free — no import and no model load happens until
    :meth:`is_available` or :meth:`annotate` is called — so a backend may be
    instantiated purely to probe availability.

    Args:
        language: Language deciding which model is loaded; see
            :data:`MODEL_BY_LANGUAGE`.
        model: Explicit model name overriding the per-language default.
    """

    name = "spacy"

    def __init__(
        self,
        language: Language = Language.EN,
        model: Optional[str] = None,
    ) -> None:
        self._language: Language = (
            language if isinstance(language, Language) else Language.from_tag(str(language))
        )
        self._model: Optional[str] = model or MODEL_BY_LANGUAGE.get(self._language)

    @property
    def language(self) -> Language:
        """Language this backend was configured for."""
        return self._language

    @property
    def model_name(self) -> Optional[str]:
        """Model this backend will load, or ``None`` for an unsupported language."""
        return self._model

    def is_available(self) -> bool:
        """Return whether spaCy *and* the required model can be used.

        Every failure mode reports ``False`` instead of raising: spaCy not
        installed, the language having no mapped model, the model package
        missing, a model/spaCy version mismatch, corrupted model data, or any
        other exception raised while loading. The exception type is not
        inspected deliberately — third-party loaders raise a wide and unstable
        range of errors, and an availability probe must never propagate.

        Returns:
            ``True`` only if a pipeline was successfully loaded and cached.
        """
        if self._model is None:
            return False
        try:
            load_pipeline(self._model, self._language.value)
        except Exception:
            # Availability probes never raise, whatever spaCy threw.
            return False
        return True

    def annotate(self, text: str, tokens: Sequence[Token]) -> list[Token]:
        """Annotate ``tokens`` with spaCy POS tags and lemmas.

        spaCy reports character offsets into ``text``, so alignment is exact
        (see :func:`~acronymkit.nlp.base.align_by_offsets`) even when our
        tokenizer and spaCy's disagree about compounds. Tokens no spaCy token
        overlapped are returned untouched.

        Args:
            text: The original phrase, passed to the pipeline verbatim so that
                offsets line up with :attr:`~acronymkit.models.Token.start`.
            tokens: Tokens emitted by the tokenizer.

        Returns:
            A new list of new :class:`~acronymkit.models.Token` objects with
            ``pos``/``lemma`` filled and roles refreshed.

        Raises:
            BackendUnavailable: If the pipeline cannot be loaded. Callers
                should consult :meth:`is_available` first.
        """
        if not tokens:
            return []
        if self._model is None:
            raise BackendUnavailable(
                f"No spaCy model is mapped for language {self._language.value!r}"
            )
        pipeline = load_pipeline(self._model, self._language.value)
        document = pipeline(text)
        annotations: list[Annotation] = []
        for spacy_token in document:
            if spacy_token.is_space:
                continue
            annotations.append(
                Annotation(
                    text=spacy_token.text,
                    pos=(spacy_token.pos_ or None),
                    lemma=(spacy_token.lemma_ or None),
                    start=spacy_token.idx,
                    end=spacy_token.idx + len(spacy_token.text),
                )
            )
        aligned = align_by_offsets(tokens, annotations)
        return apply_annotations(tokens, aligned, update_roles=True)

    def __repr__(self) -> str:  # pragma: no cover - display helper
        return f"SpacyBackend(language={self._language.value!r}, model={self._model!r})"
