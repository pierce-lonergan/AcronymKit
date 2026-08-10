"""JSON serialisation and schema validation for engine results.

``schemas/acronym-engine-result.schema.json`` is the cross-language interchange
contract: the Python package and the planned ``acronym4j`` port must both emit
payloads that validate against it. This module is the seam that makes that
contract testable from inside the library.

Locating the schema
-------------------
**The bundled resource is the only source, and that is a security property
rather than a convenience.**

This module used to search the filesystem first: ``<repo>/schemas/`` and the
same directory under each of two ancestors of the package directory, falling
back to the bundled copy only if none existed. In an installed wheel those
ancestors are ``<site-packages>/schemas/`` and ``<venv>/Lib/schemas/`` — paths
this package does not own, that carry no ``RECORD`` hash, and that any other
distribution can create. ``schemas`` is a real, installable name on PyPI, so
claiming that directory does not even require write access to the machine:
it requires one line in a requirements file.

An audit demonstrated the full chain. A planted document was returned by
:func:`load_schema` in preference to the bundled one, and because a JSON Schema
may contain a remote ``$ref``, ``jsonschema`` then issued a real outbound HTTP
GET to fetch it — turning a library with no network code of its own into one
that makes a request, on a machine chosen by whoever owned that directory,
while :func:`validate_result` reported the attacker's document as valid.

So the search is gone. The schema ships inside the wheel as an
``acronymkit.resources`` data file, hashed in ``RECORD`` like every other
module, and that copy is the one that is read — in a checkout, in a wheel, in
an sdist, identically. :data:`SCHEMA_PATH` still names the checkout copy
because tooling and the cross-language port need to point at it, but nothing
in the load path consults it.

Two invariants keep it honest, both enforced by tests: the checkout copy and
the bundled copy must agree, and the schema must contain no remote ``$ref``.
The second is checked at validation time as well, because "our schema happens
to contain no remote reference today" is an accident, and
:func:`validate_result` is where an accident would become a request.

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


#: Checkout location of the schema, for tooling and for the cross-language
#: port that shares this contract. **Not consulted when loading** — see the
#: module docstring. In an installed wheel this path does not exist, and that
#: is now unremarkable rather than the reason for a filesystem search.
SCHEMA_PATH: Path = _MODULE_DIRECTORY.parents[1] / _SCHEMA_DIRECTORY / SCHEMA_FILENAME

#: Message shown when ``jsonschema`` is not importable.
_JSONSCHEMA_MISSING = (
    "Schema validation requires the 'jsonschema' package, which is an optional "
    "development dependency. Install it with: pip install 'acronymkit[dev]' "
    "(or: pip install jsonschema)."
)


#: URI schemes that would make resolving a ``$ref`` a network operation.
_REMOTE_REF_SCHEMES = ("http://", "https://", "ftp://", "ftps://", "file://")


def _remote_refs(node: Any, pointer: str = "#") -> list[str]:
    """Return every ``$ref`` in ``node`` that would need to be fetched.

    A ``$ref`` is local when it is a fragment (``#/$defs/Foo``) or a bare
    relative name resolved against a base URI the caller already holds. It is
    remote when it names a scheme, and resolving one is an outbound request.

    Args:
        node: Any decoded-JSON value; dictionaries and lists are walked.
        pointer: JSON Pointer of ``node``, used to report where a hit is.

    Returns:
        ``["<pointer> -> <uri>", ...]``, empty when the document is local-only.
    """
    found: list[str] = []
    if isinstance(node, dict):
        for key, value in node.items():
            if key == "$ref" and isinstance(value, str):
                if value.lower().startswith(_REMOTE_REF_SCHEMES):
                    found.append(f"{pointer} -> {value}")
            else:
                found.extend(_remote_refs(value, f"{pointer}/{key}"))
    elif isinstance(node, list):
        for position, value in enumerate(node):
            found.extend(_remote_refs(value, f"{pointer}/{position}"))
    return found


@lru_cache(maxsize=1)
def _schema_source() -> str:
    """Return the raw JSON text of the interchange schema.

    Read from the bundled ``acronymkit.resources`` copy and nowhere else. The
    filesystem search this function used to perform is gone; the module
    docstring records why, and :data:`SCHEMA_PATH` is no longer consulted.

    Cached because the value is immutable. Failures are not cached:
    :func:`functools.lru_cache` does not memoise exceptions.

    Returns:
        The UTF-8 text of the schema document.

    Raises:
        ResourceNotFoundError: If the bundled resource is missing, which means
            the installation is damaged rather than merely unusual.
    """
    if has_resource(SCHEMA_FILENAME):
        return read_text_resource(SCHEMA_FILENAME)
    raise ResourceNotFoundError(
        f"The interchange schema {SCHEMA_FILENAME!r} is missing from the installed "
        f"package. It ships inside the wheel as 'acronymkit.resources/"
        f"{SCHEMA_FILENAME}' and is listed in RECORD, so its absence means the "
        f"installation is damaged — reinstall acronymkit. A copy in "
        f"{_SCHEMA_DIRECTORY}/ next to a checkout is deliberately not consulted."
    )


def load_schema() -> dict[str, Any]:
    """Load the ``AcronymEngineResult`` JSON Schema.

    Read from the bundled resource, which is hashed in the wheel's ``RECORD``.
    A ``schemas/`` directory next to the installation is never consulted; see
    the module docstring for the hijack that established the rule.

    The source text is cached but re-parsed on every call, so callers receive a
    private, freely mutable document.

    Returns:
        The decoded JSON Schema.

    Raises:
        ResourceNotFoundError: If the bundled resource is missing.

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
        AcronymKitError: If ``jsonschema`` is not installed, or if the schema
            contains a remote ``$ref`` — see below.
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
    schema = load_schema()
    # This is the only place in the package where a document we did not write
    # could become an outbound request: `jsonschema` resolves remote `$ref`s
    # by fetching them, and it still does so in current versions. Loading the
    # schema from the bundled resource already removes the realistic way a
    # foreign document gets here, but "our schema happens to have no remote
    # ref" is a property of today's file rather than a guarantee, and this is
    # the line where that accident would turn into a socket. Check, and say so.
    remote = _remote_refs(schema)
    if remote:
        raise AcronymKitError(
            "Refusing to validate: the interchange schema contains "
            f"{len(remote)} remote $ref(s), which jsonschema resolves by "
            f"fetching them over the network. Found: {'; '.join(remote)}. "
            "acronymkit performs no network I/O, and validation is not an "
            "exception to that."
        )
    jsonschema.validate(instance=_as_payload(payload), schema=schema)


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
