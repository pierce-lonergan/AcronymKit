"""JSON serialisation and schema validation for engine results.

``schemas/acronym-engine-result.schema.json`` is the cross-language interchange
contract: the Python package and the planned ``acronym4j`` port must both emit
payloads that validate against it. This module is the seam that makes that
contract testable from inside the library.

Locating the schema
-------------------
The ``schemas/`` directory lives at the repository root and is deliberately
*not* packaged into the wheel — it is a specification shared with other
implementations, versioned independently of either. :func:`load_schema`
therefore resolves in two steps:

1. the checkout location, ``<repo>/schemas/acronym-engine-result.schema.json``,
   found relative to this module's own path (this is :data:`SCHEMA_PATH`);
2. failing that, a copy bundled as an ``acronymkit.resources`` data file, which
   a distributor may add without touching any code.

When neither exists — the normal state of a plain wheel install —
:class:`~acronymkit.exceptions.ResourceNotFoundError` is raised naming both
locations, because "there is no schema here" is a real answer rather than a
bug: validation is a development-time and CI concern, not a runtime dependency
of generation.

Dependency policy
-----------------
``jsonschema`` is a development extra, imported inside
:func:`validate_result` and never at module scope, so importing
:mod:`acronymkit` on a production box pulls in nothing beyond ``pydantic``.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Optional

from pydantic import BaseModel

from .exceptions import AcronymKitError, ResourceNotFoundError
from .models import AcronymResult
from .resources import has_resource, read_text_resource

__all__ = [
    "SCHEMA_PATH",
    "export_model_schema",
    "load_schema",
    "to_json",
    "validate_result",
]


#: File name of the interchange schema, identical in the checkout and in any
#: bundled copy.
SCHEMA_FILENAME = "acronym-engine-result.schema.json"

#: Directory that holds the schema in a source checkout.
_SCHEMA_DIRECTORY = "schemas"

#: Directory holding this module (``<repo>/src/acronymkit`` in a checkout).
_MODULE_DIRECTORY = Path(__file__).resolve().parent

#: How many ancestors of the package directory are searched for ``schemas/``.
#: Two covers both supported checkout shapes: ``src/acronymkit`` (the layout
#: this project uses) and a flat ``acronymkit`` at the repository root.
_SEARCH_DEPTH = 2


def _ancestor(depth: int) -> Path:
    """Return the ``depth``-th ancestor of the package directory.

    Args:
        depth: ``0`` is the parent of the package directory, ``1`` its
            grandparent, and so on. Depths beyond the filesystem root clamp to
            the root rather than raising.

    Returns:
        The resolved ancestor directory.
    """
    parents = _MODULE_DIRECTORY.parents
    return parents[min(depth, len(parents) - 1)]


#: Canonical checkout location of the schema (``<repo>/schemas/...`` for the
#: ``src/`` layout this project uses). It does **not** necessarily exist: an
#: installed wheel has no ``schemas/`` directory, which is why
#: :func:`load_schema` also consults the bundled-resource fallback.
SCHEMA_PATH: Path = _ancestor(1) / _SCHEMA_DIRECTORY / SCHEMA_FILENAME

#: Message shown when ``jsonschema`` is not importable.
_JSONSCHEMA_MISSING = (
    "Schema validation requires the 'jsonschema' package, which is an optional "
    "development dependency. Install it with: pip install 'acronymkit[dev]' "
    "(or: pip install jsonschema)."
)


def _candidate_paths() -> tuple[Path, ...]:
    """Return the checkout locations searched for the schema, in order.

    Returns:
        :data:`SCHEMA_PATH` first, followed by the same file under the nearer
        ancestors of the package directory, de-duplicated and order-preserving.
    """
    candidates: list[Path] = [SCHEMA_PATH]
    for depth in range(_SEARCH_DEPTH):
        candidate = _ancestor(depth) / _SCHEMA_DIRECTORY / SCHEMA_FILENAME
        if candidate not in candidates:
            candidates.append(candidate)
    return tuple(candidates)


@lru_cache(maxsize=1)
def _schema_source() -> str:
    """Return the raw JSON text of the interchange schema.

    Cached because the value is immutable and the lookup touches the
    filesystem. Failures are not cached: :func:`functools.lru_cache` does not
    memoise exceptions, so a schema added after a failed call is picked up.

    Returns:
        The UTF-8 text of the schema document.

    Raises:
        ResourceNotFoundError: If the schema is in neither the checkout nor the
            bundled resources.
    """
    for candidate in _candidate_paths():
        try:
            if candidate.is_file():
                return candidate.read_text(encoding="utf-8")
        except OSError:  # pragma: no cover - unreadable path, try the next one
            continue
    if has_resource(SCHEMA_FILENAME):
        return read_text_resource(SCHEMA_FILENAME)
    searched = ", ".join(str(candidate) for candidate in _candidate_paths())
    raise ResourceNotFoundError(
        f"The interchange schema {SCHEMA_FILENAME!r} could not be located. It is "
        f"published in the repository under {_SCHEMA_DIRECTORY}/ and is not shipped "
        f"inside the wheel. Searched: {searched}; and the bundled resource "
        f"'acronymkit.resources/{SCHEMA_FILENAME}'. Run from a source checkout, or "
        f"copy the schema into the acronymkit/resources directory."
    )


def load_schema() -> dict[str, Any]:
    """Load the ``AcronymEngineResult`` JSON Schema.

    The source text is cached but re-parsed on every call, so callers receive a
    private, freely mutable document.

    Returns:
        The decoded JSON Schema.

    Raises:
        ResourceNotFoundError: If the schema is available neither in a source
            checkout nor as a bundled resource.

    Example:
        >>> load_schema()["title"]
        'AcronymEngineResult'
    """
    return json.loads(_schema_source())


def _as_payload(payload: Any) -> Any:
    """Coerce ``payload`` into a plain JSON-compatible object.

    Args:
        payload: A mapping already in wire form, or any Pydantic model (every
            :mod:`acronymkit` DTO qualifies).

    Returns:
        ``payload`` unchanged when it is already plain data, otherwise its
        JSON-mode dump.
    """
    if isinstance(payload, BaseModel):
        return payload.model_dump(mode="json")
    return payload


def validate_result(payload: Any) -> None:
    """Validate a generation payload against the interchange schema.

    Args:
        payload: The document to check. Either the output of
            :meth:`~acronymkit.models.AcronymResult.to_dict` or an
            :class:`~acronymkit.models.AcronymResult` itself, which is dumped
            for you.

    Returns:
        ``None``. The function is a check, not a converter: it either returns
        quietly or raises.

    Raises:
        AcronymKitError: If ``jsonschema`` is not installed.
        ResourceNotFoundError: If the schema could not be located.
        jsonschema.exceptions.ValidationError: If ``payload`` does not conform.
            The exception carries the failing JSON pointer and the violated
            keyword.

    Example:
        >>> from acronymkit import AcronymEngine
        >>> result = AcronymEngine().generate("Portable Document Format")
        >>> validate_result(result.to_dict())
    """
    try:
        import jsonschema
    except ImportError as exc:  # pragma: no cover - depends on the environment
        raise AcronymKitError(_JSONSCHEMA_MISSING) from exc
    jsonschema.validate(instance=_as_payload(payload), schema=load_schema())


def export_model_schema(model: Optional[type] = None) -> dict[str, Any]:
    """Derive a JSON Schema from a Pydantic model.

    Useful for diffing what the code actually emits against the hand-written
    interchange contract returned by :func:`load_schema`, and for publishing
    schemas of the models the contract does not cover.

    Args:
        model: The model class to describe. Defaults to
            :class:`~acronymkit.models.AcronymResult`, the payload the
            interchange schema governs.

    Returns:
        The generated schema, in serialisation mode so that it describes what
        :meth:`~acronymkit.models.AcronymResult.to_dict` produces (computed
        fields included, enums as their string values) rather than what the
        constructor accepts.

    Raises:
        TypeError: If ``model`` is not a Pydantic model class.

    Example:
        >>> export_model_schema()["title"]
        'AcronymResult'
    """
    target: Any = AcronymResult if model is None else model
    if not (isinstance(target, type) and issubclass(target, BaseModel)):
        raise TypeError(
            f"export_model_schema() expects a pydantic BaseModel subclass, got {target!r}"
        )
    return dict(target.model_json_schema(mode="serialization"))


def to_json(model: Any, indent: Optional[int] = None) -> str:
    """Serialise a model or plain payload to a JSON string.

    Args:
        model: Any :mod:`acronymkit` DTO, any other Pydantic model, or an
            already-plain object such as the ``dict`` from
            :meth:`~acronymkit.models.AcronymResult.to_dict`.
        indent: Passed through to :func:`json.dumps`. ``None`` yields the
            compact single-line form preferred for wire transfer and log lines.

    Returns:
        The JSON text. Non-ASCII characters are emitted verbatim rather than
        escaped, so accented source phrases stay readable, and key order
        follows the model's field order rather than being re-sorted.

    Raises:
        TypeError: If a plain payload holds values :mod:`json` cannot encode.

    Example:
        >>> from acronymkit.models import AcronymPair
        >>> pair = AcronymPair(short_form="API", long_form="Application Programming Interface")
        >>> to_json(pair)[:26]
        '{"short_form": "API", "lon'
    """
    return json.dumps(_as_payload(model), indent=indent, ensure_ascii=False)
