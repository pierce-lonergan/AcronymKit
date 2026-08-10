"""Machine-readable inventory of what this installation can actually do.

The module is ``acronymkit.diagnostics`` while its headline function is
:func:`capabilities`, re-exported as ``acronymkit.capabilities()``. Naming the
module ``capabilities`` too would have made ``acronymkit.capabilities`` resolve
to the function and silently break ``import acronymkit.capabilities``.

An enterprise does not want to read a README to find out whether the copy of
``acronymkit`` on the build agent has a lexicon, which tiers are reachable, and
whether anything on the box can reach the network. They want to assert it, in
their own CI, and fail their own build if the answer changed. That is what
:func:`capabilities` is for: a plain dictionary of facts, stable enough to pin.

Deliberately stdlib-only
------------------------
This module imports nothing beyond the standard library — not ``pydantic``, not
any other part of ``acronymkit`` except :mod:`acronymkit.resources`. Two
reasons, and both are load-bearing:

* It has to work when the installation is *broken*. A capability report whose
  own import fails on the machine you are diagnosing is worthless.
* Importing it must not perturb what it measures. Reporting "spaCy is
  available" by importing spaCy would make the report the reason spaCy is
  resident, and this project already runs a CI job asserting that a Tier 0
  install pulls nothing optional into :data:`sys.modules`.

So availability is decided with :func:`importlib.util.find_spec`, which locates
a module without executing it.

What "available" means here
---------------------------
Available means *importable*, which is weaker than *usable* and is reported as
such. NLTK is importable long before it has the corpora ``nltk.pos_tag`` needs;
spaCy is importable without a model. Both then raise rather than downloading —
that behaviour is measured, not assumed, and is written down in
``docs/OFFLINE.md``. Where the distinction matters, this module reports the
distribution and lets the backend's own ``is_available()`` answer the harder
question, because that call is the one that touches data files.
"""

from __future__ import annotations

import hashlib
import importlib.util
import os
import platform
import sys
from typing import Any, Optional

from .resources import bundled_resources, read_binary_resource

__all__ = [
    "DATA_PACK_GROUP",
    "OFFLINE_ENV_VAR",
    "capabilities",
    "format_report",
    "offline_requested",
    "pydantic_plugins",
]


#: Environment variable that forces strict offline mode on.
#:
#: It can only *tighten*: a truthy value turns offline mode on for every
#: :class:`~acronymkit.config.Config` in the process, and there is deliberately
#: no value that turns it off. A container-wide setting that could silently
#: *relax* a security posture would be a worse bug than the one it solves, and
#: it is one of only two environment variables this package reads, the other
#: being PYDANTIC_DISABLE_PLUGINS in :func:`pydantic_plugins` -- which is
#: also read only to report what someone else's machinery will do.
OFFLINE_ENV_VAR = "ACRONYMKIT_OFFLINE"

#: Values of :data:`OFFLINE_ENV_VAR` that mean "on". Anything else, including
#: the empty string, means "not requested" rather than "off" — see above.
_TRUTHY = frozenset({"1", "true", "yes", "on"})

#: Entry-point group ``pydantic`` scans on every model build. Third-party code
#: advertised here is imported by ``pydantic`` itself, without asking us.
_PYDANTIC_PLUGIN_GROUP = "pydantic"

#: Entry-point group an optional data pack advertises itself under. Nothing
#: ships one yet; the group is named here so a pack can be discovered without
#: the base package knowing its name in advance, and never downloaded.
DATA_PACK_GROUP = "acronymkit.data"

#: Optional backends, as ``{distribution: what it provides}``.
_OPTIONAL_BACKENDS = {
    "click": "cli",
    "spacy": "tier 1 (statistical NLP)",
    "nltk": "tier 1 (statistical NLP)",
    "transformers": "tier 2 (neural) -- not implemented",
    "onnxruntime": "tier 2 (neural) -- not implemented",
    "jsonschema": "schema validation (development)",
}


def offline_requested() -> bool:
    """Return whether the environment asks for strict offline mode.

    Returns:
        ``True`` if :data:`OFFLINE_ENV_VAR` holds a truthy value.

    Example:
        >>> import os
        >>> os.environ.pop("ACRONYMKIT_OFFLINE", None) and None
        >>> offline_requested()
        False
    """
    return os.environ.get(OFFLINE_ENV_VAR, "").strip().lower() in _TRUTHY


def _entry_point_names(group: str) -> tuple[str, ...]:
    """Return the names of every installed entry point in ``group``.

    Args:
        group: Entry-point group to enumerate.

    Returns:
        Sorted names, empty when nothing advertises the group.
    """
    from importlib import metadata

    # Bound through an ``Any`` rather than called directly, and deliberately.
    # ``entry_points(group=...)`` exists from 3.10; on 3.9 the function takes no
    # arguments and returns a mapping. A ``type: ignore`` for the 3.9 typeshed
    # is reported as *unused* against a newer one, so the comment that silences
    # one checker fails the other. Erasing the call site is the only form that
    # is correct under both, and the TypeError branch is the real 3.9 path.
    select: Any = metadata.entry_points
    found: Any
    try:
        found = select(group=group)
    except TypeError:  # pragma: no cover - Python 3.9 returns a plain mapping
        found = select().get(group, [])
    return tuple(sorted(str(entry.name) for entry in found))


def pydantic_plugins() -> tuple[str, ...]:
    """Return the names of third-party ``pydantic`` plugins installed here.

    ``pydantic`` scans the ``pydantic`` entry-point group and imports whatever
    it finds, on the path that builds any model — which for this library is the
    path that builds a :class:`~acronymkit.config.Config`. Nothing in
    ``acronymkit`` asks for that and nothing can prevent it from inside the
    process, so the honest move is to report it. Strict offline mode refuses to
    run when this is non-empty; see
    :class:`~acronymkit.exceptions.OfflineError`.

    Returns:
        Sorted plugin names, empty when nothing advertises the group or when
        ``PYDANTIC_DISABLE_PLUGINS`` has switched the mechanism off.
    """
    if os.environ.get("PYDANTIC_DISABLE_PLUGINS", "").strip() in {"__all__", "1", "true"}:
        return ()
    return _entry_point_names(_PYDANTIC_PLUGIN_GROUP)


def _data_packs() -> tuple[str, ...]:
    """Return installed ``acronymkit`` data packs, by entry-point name."""
    return _entry_point_names(DATA_PACK_GROUP)


def _is_importable(distribution: str) -> bool:
    """Return whether ``distribution`` can be imported, without importing it.

    :func:`importlib.util.find_spec` locates a top-level module without
    executing it, which is the difference between reporting on the environment
    and changing it.
    """
    try:
        return importlib.util.find_spec(distribution) is not None
    except (ImportError, ValueError):  # pragma: no cover - broken installation
        return False


def _resource_digests() -> dict[str, dict[str, Any]]:
    """Return ``{resource name: {bytes, sha256}}`` for every bundled file.

    SHA-256 throughout. Nothing in this package uses MD5, which matters
    because :func:`hashlib.md5` raises on a FIPS-enabled host — a checksum
    routine is exactly where that lands if it is going to.
    """
    digests: dict[str, dict[str, Any]] = {}
    for name in bundled_resources():
        try:
            payload = read_binary_resource(name)
        except Exception:  # pragma: no cover - a damaged install still reports
            digests[name] = {"bytes": None, "sha256": None, "error": "unreadable"}
            continue
        digests[name] = {
            "bytes": len(payload),
            "sha256": hashlib.sha256(payload).hexdigest(),
        }
    return digests


def capabilities(*, include_checksums: bool = True) -> dict[str, Any]:
    """Return a machine-readable report of what this installation can do.

    Args:
        include_checksums: Hash every bundled resource. On by default because
            an enterprise pinning this report wants the resources fixed too;
            turn it off for a cheap liveness check.

    Returns:
        A nested, JSON-serialisable dictionary. Keys are stable: fields may be
        added, but the meaning of an existing one will not change under a
        patch release, because the point of this function is to be asserted on.

    Example:
        >>> report = capabilities(include_checksums=False)
        >>> report["network"]["performs_network_io"]
        False
        >>> report["tiers"]["zero_dependency"]
        True
    """
    from . import __version__

    plugins = pydantic_plugins()
    backends = {name: _is_importable(name) for name in sorted(_OPTIONAL_BACKENDS)}

    report: dict[str, Any] = {
        "acronymkit_version": __version__,
        "python_version": platform.python_version(),
        "python_implementation": platform.python_implementation(),
        "platform": sys.platform,
        "offline": {
            # Whether the *environment* asks for it. A Config carries its own
            # flag, and the effective value is the OR of the two; see
            # acronymkit.config.Config.
            "env_var": OFFLINE_ENV_VAR,
            "requested_by_environment": offline_requested(),
        },
        "network": {
            # Stated as a fact because it is tested as one: the air-gap CI job
            # runs this package's entire test suite with every socket
            # primitive patched to raise, in a network namespace with no
            # route. docs/OFFLINE.md names the job and the test.
            "performs_network_io": False,
            "downloads_models": False,
            "telemetry": False,
            # ...with the one caveat this package cannot close from inside.
            "third_party_import_hooks": {
                "pydantic_entry_point_plugins": list(plugins),
                "note": (
                    "pydantic imports anything advertising the 'pydantic' entry-point "
                    "group while building a model. Set PYDANTIC_DISABLE_PLUGINS=1 to "
                    "stop it. Strict offline mode refuses to run when this list is "
                    "non-empty."
                ),
            },
        },
        "tiers": {
            "zero_dependency": True,
            "standard": backends["spacy"] or backends["nltk"],
            "statistical_nlp": backends["spacy"] or backends["nltk"],
            "neural": False,
        },
        "backends": {
            name: {"importable": available, "provides": _OPTIONAL_BACKENDS[name]}
            for name, available in backends.items()
        },
        "data_packs": list(_data_packs()),
        "resources": {
            "count": len(bundled_resources()),
            "names": list(bundled_resources()),
        },
    }
    if include_checksums:
        report["resources"]["digests"] = _resource_digests()
    return report


def format_report(report: Optional[dict[str, Any]] = None) -> str:
    """Render :func:`capabilities` as aligned text for a terminal.

    Args:
        report: A report to render. One is generated when omitted.

    Returns:
        A multi-line string. No colour and no Unicode box drawing: this is
        read in container logs, where both are liabilities.
    """
    data = capabilities() if report is None else report
    lines = [
        f"acronymkit {data['acronymkit_version']} on Python {data['python_version']} "
        f"({data['python_implementation']}, {data['platform']})",
        "",
        "network",
        f"  performs network I/O          : {data['network']['performs_network_io']}",
        f"  downloads models              : {data['network']['downloads_models']}",
        f"  telemetry                     : {data['network']['telemetry']}",
    ]
    plugins = data["network"]["third_party_import_hooks"]["pydantic_entry_point_plugins"]
    lines.append("  third-party pydantic plugins  : " + (", ".join(plugins) if plugins else "none"))
    lines += [
        "",
        "offline",
        f"  {data['offline']['env_var']:<30}: "
        f"{'set' if data['offline']['requested_by_environment'] else 'unset'}",
        "",
        "tiers",
    ]
    for tier, available in data["tiers"].items():
        lines.append(f"  {tier:<30}: {'available' if available else 'unavailable'}")
    lines += ["", "optional backends"]
    for name, info in data["backends"].items():
        state = "importable" if info["importable"] else "absent"
        lines.append(f"  {name:<30}: {state:<11} ({info['provides']})")
    packs = data["data_packs"]
    lines += ["", f"data packs                      : {', '.join(packs) if packs else 'none'}"]
    lines += ["", f"bundled resources               : {data['resources']['count']}"]
    for name in data["resources"]["names"]:
        digest = data["resources"].get("digests", {}).get(name)
        if digest and digest.get("sha256"):
            lines.append(f"  {name:<30}: {digest['bytes']:>8} B  sha256:{digest['sha256'][:16]}")
        else:
            lines.append(f"  {name}")
    return "\n".join(lines)
