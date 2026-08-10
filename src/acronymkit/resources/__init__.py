"""Access to the data resources bundled inside the ``acronymkit`` distribution.

The package ships categorised stop-word lists (``stopwords_<lang>.json``),
word lexicons (``lexicon_<lang>.txt``) and character n-gram models
(``ngram_<lang>.json``). This module is the single seam through which every
other subsystem reads them, so the rest of the library never touches
:mod:`importlib.resources` or ``__file__`` directly.

Two deployment shapes must both work:

* a **source checkout**, where the files sit next to this module on disk; and
* an **installed wheel**, which may be imported from a zip archive and
  therefore has no real filesystem path.

Resolution therefore prefers :func:`importlib.resources.files` (available on
Python 3.9+) and falls back to a :mod:`pathlib` lookup relative to
``__file__``. :func:`resource_path` materialises zipped resources into a
temporary file that is removed at interpreter exit.

Caching contract:
    Only immutable return values are memoised with :func:`functools.lru_cache`.
    :func:`read_lines_resource` and :func:`available_languages` cache an
    internal ``tuple`` and hand back a **fresh** ``list`` on every call, and
    :func:`read_json_resource` re-parses the cached source text so that callers
    always receive their own mutable object. :func:`has_resource` is
    deliberately *not* cached, so a negative answer never becomes permanent.
"""

from __future__ import annotations

import atexit
import gzip
import json
from contextlib import ExitStack
from functools import cache, lru_cache
from pathlib import Path
from typing import Any

from ..exceptions import ResourceNotFoundError

__all__ = [
    "available_languages",
    "bundled_resources",
    "has_resource",
    "read_binary_resource",
    "read_json_resource",
    "read_lines_resource",
    "read_text_resource",
    "resource_path",
]

#: Recognised resource families and their ``(prefix, suffix)`` naming scheme.
_KINDS: dict[str, tuple[str, str]] = {
    "stopwords": ("stopwords_", ".json"),
    "lexicon": ("lexicon_", ".txt"),
    "ngram": ("ngram_", ".json"),
}

#: Extension marking a gzip-compressed resource.
_GZIP_SUFFIX = ".gz"

#: Byte-order mark stripped from decoded text resources.
_BOM = chr(0xFEFF)

#: Holds temporary files extracted from zipped installs; emptied at exit.
_EXTRACTED_FILES = ExitStack()
atexit.register(_EXTRACTED_FILES.close)


# ---------------------------------------------------------------------------
# internal helpers
# ---------------------------------------------------------------------------
def _check_name(name: str) -> str:
    """Validate ``name`` as a flat resource name.

    Args:
        name: Candidate resource file name, e.g. ``"lexicon_en.txt"``.

    Returns:
        The validated name, unchanged.

    Raises:
        ResourceNotFoundError: If the name is empty or attempts to escape the
            resource directory (contains a path separator or ``..``).
    """
    if not isinstance(name, str) or not name:
        raise ResourceNotFoundError("Resource name must be a non-empty string")
    if "/" in name or "\\" in name or name in {".", ".."} or ".." in Path(name).parts:
        raise ResourceNotFoundError(
            f"Resource name {name!r} must be a plain file name without path components"
        )
    return name


@lru_cache(maxsize=1)
def _filesystem_root() -> Path:
    """Return the on-disk directory containing this module."""
    return Path(__file__).resolve().parent


@lru_cache(maxsize=1)
def _package_root() -> Any:
    """Return a traversable handle on the resource directory.

    Uses :func:`importlib.resources.files` when it is importable (Python 3.9+),
    which keeps the package zip-safe, and degrades to a plain
    :class:`pathlib.Path` otherwise.

    Returns:
        Either an ``importlib.abc.Traversable`` or a :class:`pathlib.Path`.
        Both expose the ``joinpath`` / ``is_file`` / ``read_bytes`` / ``iterdir``
        subset used by this module.
    """
    try:
        from importlib.resources import files as _files
    except ImportError:  # pragma: no cover - Python < 3.9 only
        return _filesystem_root()
    package = __package__ or "acronymkit.resources"
    try:
        return _files(package)
    except (ImportError, TypeError, AttributeError, ValueError):  # pragma: no cover
        return _filesystem_root()


def _is_file(candidate: Any) -> bool:
    """Return whether ``candidate`` resolves to a readable file."""
    try:
        return bool(candidate.is_file())
    except (OSError, AttributeError, ValueError):  # pragma: no cover - defensive
        return False


def _locate(name: str) -> Any:
    """Return a traversable for ``name``.

    Args:
        name: Flat resource file name.

    Returns:
        A ``Traversable`` or :class:`pathlib.Path` pointing at the resource.

    Raises:
        ResourceNotFoundError: If no such resource is bundled.
    """
    _check_name(name)
    direct = _filesystem_root() / name
    if direct.is_file():
        return direct
    child = _package_root().joinpath(name)
    if _is_file(child):
        return child
    raise ResourceNotFoundError(
        f"Bundled resource {name!r} was not found in the acronymkit.resources package"
    )


@cache
def _read_bytes(name: str) -> bytes:
    """Return the raw (still compressed) bytes of a bundled resource.

    Args:
        name: Flat resource file name.

    Returns:
        The resource contents as ``bytes``.

    Raises:
        ResourceNotFoundError: If the resource is missing or unreadable.
    """
    handle = _locate(name)
    try:
        return bytes(handle.read_bytes())
    except OSError as exc:
        raise ResourceNotFoundError(f"Bundled resource {name!r} could not be read: {exc}") from exc


@cache
def _read_lines_tuple(name: str) -> tuple[str, ...]:
    """Return the cached, comment-free lines of a text resource."""
    lines: list[str] = []
    for raw in read_text_resource(name).splitlines():
        line = raw.rstrip()
        stripped = line.lstrip()
        if not stripped or stripped.startswith("#"):
            continue
        lines.append(line)
    return tuple(lines)


@cache
def _available_languages_tuple(kind: str) -> tuple[str, ...]:
    """Return the cached, sorted language codes bundled for ``kind``."""
    if kind not in _KINDS:
        raise ValueError(f"Unknown resource kind {kind!r}; expected one of {sorted(_KINDS)}")
    prefix, suffix = _KINDS[kind]
    codes: set[str] = set()
    for entry_name in _iter_resource_names():
        stem = entry_name
        if stem.endswith(_GZIP_SUFFIX):
            stem = stem[: -len(_GZIP_SUFFIX)]
        if not stem.startswith(prefix) or not stem.endswith(suffix):
            continue
        code = stem[len(prefix) : len(stem) - len(suffix)]
        if code and code.isalpha():
            codes.add(code.lower())
    return tuple(sorted(codes))


def _iter_resource_names() -> tuple[str, ...]:
    """Return the names of every entry in the resource directory.

    Never raises: an unreadable or absent directory yields an empty tuple so
    that :func:`available_languages` degrades to "nothing bundled".
    """
    names: set[str] = set()
    for root in (_filesystem_root(), _package_root()):
        try:
            for entry in root.iterdir():
                names.add(entry.name)
        except (OSError, AttributeError, ValueError, NotADirectoryError):
            continue
    return tuple(sorted(names))


#: Names that live in the resource directory but are not data: the package
#: machinery itself. Everything else is a shipped data file.
_NON_DATA = ("__init__.py", "__pycache__", "py.typed")


@cache
def bundled_resources() -> tuple[str, ...]:
    """Return the names of every bundled *data* resource, sorted.

    Excludes the package machinery (``__init__.py`` and friends), so what
    comes back is the list of files this distribution ships as content. Used
    by :func:`acronymkit.capabilities.capabilities` to report — and checksum —
    exactly what an installation is carrying.

    Returns:
        Flat file names, e.g. ``("lexicon_en.txt", "ngram_en.json", ...)``.

    Example:
        >>> "stopwords_en.json" in bundled_resources()
        True
    """
    return tuple(
        name
        for name in _iter_resource_names()
        if name not in _NON_DATA and not name.endswith((".py", ".pyc"))
    )


def read_binary_resource(name: str) -> bytes:
    """Return the raw bytes of a bundled resource, exactly as shipped.

    No decompression and no decoding: a ``.gz`` resource comes back
    compressed. That is the point — these are the bytes a wheel's ``RECORD``
    hashes, so a checksum taken here is comparable with one taken by ``pip``
    or by a security scanner that never imported Python.

    Args:
        name: Flat resource file name.

    Returns:
        The resource contents.

    Raises:
        ResourceNotFoundError: If the resource is missing or unreadable.
    """
    return _read_bytes(_check_name(name))


# ---------------------------------------------------------------------------
# public API
# ---------------------------------------------------------------------------
@cache
def resource_path(name: str) -> Path:
    """Return a real filesystem path for a bundled resource.

    When the package is installed as a zip (or any other non-filesystem
    loader), the resource is extracted to a temporary file whose lifetime lasts
    until interpreter shutdown.

    Args:
        name: Flat resource file name, e.g. ``"stopwords_en.json"``.

    Returns:
        An existing :class:`pathlib.Path` pointing at the resource.

    Raises:
        ResourceNotFoundError: If the resource is not bundled, or cannot be
            materialised on the filesystem.
    """
    handle = _locate(name)
    if isinstance(handle, Path):
        return handle
    try:
        from importlib.resources import as_file
    except ImportError as exc:  # pragma: no cover - Python < 3.9 only
        raise ResourceNotFoundError(
            f"Resource {name!r} is not available as a filesystem path"
        ) from exc
    try:
        return Path(_EXTRACTED_FILES.enter_context(as_file(handle)))
    except (OSError, ValueError) as exc:  # pragma: no cover - defensive
        raise ResourceNotFoundError(
            f"Resource {name!r} could not be materialised on the filesystem: {exc}"
        ) from exc


def has_resource(name: str) -> bool:
    """Return whether a resource is bundled with the package.

    Deliberately uncached so that resources written after the first query (for
    example by ``tools/build_ngram_model.py``) are still discovered.

    Args:
        name: Flat resource file name.

    Returns:
        ``True`` when the resource exists and is readable, else ``False``.
        Invalid names return ``False`` rather than raising.
    """
    try:
        _locate(name)
    except ResourceNotFoundError:
        return False
    return True


def read_text_resource(name: str) -> str:
    """Return the UTF-8 text of a bundled resource.

    Names ending in ``.gz`` are transparently decompressed with :mod:`gzip`.

    Args:
        name: Flat resource file name.

    Returns:
        The decoded text, with any leading byte-order mark removed.

    Raises:
        ResourceNotFoundError: If the resource is missing, unreadable, not
            valid UTF-8, or (for ``*.gz``) not valid gzip data.
    """
    return _read_text_cached(name)


@cache
def _read_text_cached(name: str) -> str:
    """Cached implementation of :func:`read_text_resource` (``str`` is immutable)."""
    payload = _read_bytes(name)
    if name.endswith(_GZIP_SUFFIX):
        try:
            payload = gzip.decompress(payload)
        except (OSError, EOFError) as exc:
            raise ResourceNotFoundError(f"Resource {name!r} is not valid gzip data: {exc}") from exc
    try:
        text = payload.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ResourceNotFoundError(f"Resource {name!r} is not valid UTF-8: {exc}") from exc
    if text.startswith(_BOM):
        text = text[1:]
    return text


def read_json_resource(name: str) -> Any:
    """Parse a bundled JSON resource.

    The decoded source text is cached, but the JSON is re-parsed on every call
    so that callers receive a private, freely mutable object.

    Args:
        name: Flat resource file name, e.g. ``"ngram_en.json"``.

    Returns:
        The decoded JSON document (typically a ``dict``).

    Raises:
        ResourceNotFoundError: If the resource is missing or is not valid JSON.
    """
    text = read_text_resource(name)
    try:
        return json.loads(text)
    except ValueError as exc:
        raise ResourceNotFoundError(f"Resource {name!r} is not valid JSON: {exc}") from exc


def read_lines_resource(name: str) -> list[str]:
    """Return the meaningful lines of a bundled text resource.

    Trailing whitespace is stripped from every line; blank lines and lines
    whose first non-whitespace character is ``#`` are dropped.

    Args:
        name: Flat resource file name, e.g. ``"lexicon_en.txt"``.

    Returns:
        A fresh ``list`` of lines, in file order.

    Raises:
        ResourceNotFoundError: If the resource is missing or undecodable.
    """
    return list(_read_lines_tuple(name))


def available_languages(kind: str) -> list[str]:
    """List the language codes for which a resource family is bundled.

    Args:
        kind: One of ``"stopwords"``, ``"lexicon"`` or ``"ngram"``.

    Returns:
        A fresh, ascending list of lowercase language codes. Empty when the
        family has no bundled files.

    Raises:
        ValueError: If ``kind`` is not a recognised resource family.
    """
    return list(_available_languages_tuple(kind))


def _clear_caches() -> None:
    """Drop every memoised lookup.

    Intended for tests and for tooling that regenerates resource files inside a
    live interpreter; not part of the public API.
    """
    _filesystem_root.cache_clear()
    _package_root.cache_clear()
    _read_bytes.cache_clear()
    _read_text_cached.cache_clear()
    _read_lines_tuple.cache_clear()
    _available_languages_tuple.cache_clear()
    resource_path.cache_clear()
