#!/usr/bin/env python3
"""Load and validate ``bench/splits.toml``, the file the train/test rule rests on.

Why this exists
---------------
``bench/splits.toml`` declares, per corpus, what it may be used for: its
``role`` (tuning or held out), its ``task``, its ``licence``, and whether it is
contaminated. Operating rule 2 -- every MED1250 figure is a tuning figure -- is
that file. So is the licence discipline that decides what may be shipped.

For months nothing loaded it. Eleven places cited it in prose; zero parsed it.
It was not even valid TOML: a ``status`` key was written twice inside
``[corpora.plod]`` while adding a correction block, and nothing noticed, because
noticing would have required a reader. **A governance artifact no tool reads is
a habit, not a rule**, and the habit had already decayed into an invalid file.

This module is the reader. It is deliberately three things at once:

* a **typed accessor** (:class:`Manifest`, :class:`Corpus`) so a bench runner
  asks the manifest what a corpus is for instead of hard-coding the answer in a
  docstring, which is how ``[corpora.plod]`` came to call PLOS journal text a
  "non-biomedical counterweight" in one file and be corrected in another;
* a **validator** (:func:`validate`) with one implementation, driven by the CI
  step, by ``tests/test_splits_manifest.py`` and by ``bench/corpora.py``, so the
  three cannot drift apart; and
* a **script** (``--check``) that CI runs.

What the validator enforces, and why each rule is here
------------------------------------------------------
``role``/``task``/``licence``
    A corpus with no declared role is exempt from the headline rule by
    accident. A corpus with no declared licence is one nobody read the terms
    for -- which has now happened three times in this repository (SDU-21 AD,
    SDU-21 AI, and GLADIS in the August 2026 audit).

``licence_url`` and ``licence_read_on``
    Operating rule 4: **licences come from terms, never from a badge.** A
    licence string on its own records a conclusion and destroys the evidence.
    These two fields record *where the text was read* and *when*, so the
    finding is reproducible by someone who does not trust it.

    The URL is checked against :data:`BADGE_HOSTS`. GLADIS is the cautionary
    tale: its GitHub badge says CC0, Zenodo says CC BY 4.0, and the repository's
    own source table lists UMLS, which is not redistributable. Three sources,
    three answers. A badge URL is therefore not an acceptable citation, and this
    validator refuses one rather than trusting the author to remember.

``shortform_recall_ceiling_pct``
    Optional, and **required to travel with its basis** -- which is the whole
    point of the pair. Where a corpus annotates every acronym *occurrence* while
    this library reports only *defined pairs*, raw recall against it understates
    the extractor by a structural margin, and publishing the recall without the
    margin misleads.

    The basis is mandatory because the word "ceiling" is dangerous in this
    repository specifically. ``41.53`` was published as "the ceiling of the
    feature set" and the run that published it exceeded the figure four times;
    the August 2026 audit kept the finding and killed the word. So a number in
    this field is never self-explanatory: the basis must say what it is, and in
    particular whether it is a hard bound or -- as with SDU-22 AE -- the point
    past which recall is bought against the corpus's own annotation. The
    validator enforces the pairing; only a reader can enforce the honesty, and
    an empty basis denies them the chance.

Usage::

    python tools/splits.py --check      # the CI gate
    python tools/splits.py --list       # the manifest as a table
    python tools/splits.py --json       # the manifest as JSON

Nothing here is imported by the library, and nothing here touches the network.
"""

from __future__ import annotations

import argparse
import datetime as _datetime
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple
from urllib.parse import urlsplit

REPO_ROOT = Path(__file__).resolve().parent.parent
SPLITS_PATH = REPO_ROOT / "bench" / "splits.toml"

#: Roles the policy recognises. A typo silently exempts a corpus from the
#: headline rule, so the vocabulary is closed rather than free text.
ROLES = ("tuning", "held_out")

#: Tasks a corpus can be scored on. Also closed, for the same reason and one
#: more: ``bench/corpora.py`` returns a *different type* per task, and a corpus
#: filed under the wrong one is how a pair scorer comes to be pointed at a span
#: corpus and report a meaningless zero.
TASKS = ("extraction", "span_detection", "disambiguation")

#: Every corpus must declare these.
REQUIRED_FIELDS = ("role", "task", "licence", "licence_url", "licence_read_on")

#: Hosts and path fragments that serve a licence *badge* or a licence *label*
#: rather than licence *text*. Operating rule 4 exists because a badge was
#: believed three times in this repository's history, and the fix each time came
#: from a person opening the actual terms.
BADGE_HOSTS = ("shields.io", "img.shields.io", "badgen.net", "badge.fury.io")

#: Path fragments that mark a URL as metadata about a licence rather than the
#: licence itself. ``api.github.com/repos/<x>/license`` returns GitHub's
#: *guess*, which is what reported CC0 for a corpus assembled partly from UMLS.
BADGE_PATH_FRAGMENTS = ("/badge", "/license.svg", "/licence.svg")

#: A licence read this long ago is reported as worth re-reading. It is a NOTE
#: and never a failure: a gate that turns red with the passage of time fires on
#: an unrelated commit, which is the failure mode this repository already
#: refused for the entry-point purity gate.
STALE_AFTER_DAYS = 730


class SplitsError(Exception):
    """The manifest could not be read, or names something that does not exist."""


def _load_toml(path: Path) -> Dict[str, Any]:
    """Parse ``path`` as TOML on any supported interpreter.

    ``tomllib`` is 3.11+, and ``tomli`` is not a declared dev dependency, so on
    3.9 and 3.10 there may be no parser at all. That is stated as an error
    rather than papered over: a validator that silently passes because it could
    not read the file is worse than one that is absent.
    """
    if sys.version_info >= (3, 11):
        import tomllib as _toml
    else:  # pragma: no cover - 3.9/3.10 path
        try:
            import tomli as _toml  # type: ignore[no-redef]
        except ImportError as error:
            raise SplitsError(
                "no TOML parser available: tomllib is 3.11+ and tomli is not installed. "
                f"Cannot validate {path}."
            ) from error
    try:
        with path.open("rb") as handle:
            return _toml.load(handle)
    except FileNotFoundError as error:
        raise SplitsError(f"{path} does not exist") from error
    except Exception as error:  # tomllib.TOMLDecodeError, and anything it wraps
        raise SplitsError(f"{path} is not valid TOML: {error}") from error


@dataclass(frozen=True)
class Corpus:
    """One corpus declaration, typed.

    Attributes:
        name: The table key, e.g. ``"med1250"``.
        role: One of :data:`ROLES`. ``"tuning"`` means every figure measured on
            this corpus is a tuning figure and must be labelled one.
        task: One of :data:`TASKS`.
        licence: The licence as read from its terms, not as inferred.
        licence_url: Where those terms were read.
        licence_read_on: When they were read.
        status: Free text: how far the corpus has been taken.
        contaminated: Whether the corpus has been looked at closely enough that
            it can no longer adjudicate anything blind.
        contamination_reason: What was looked at. Required when
            ``contaminated`` is true, because "contaminated" with no reason is
            unfalsifiable and cannot be argued down later.
        vendorable: Whether the corpus may ship inside the wheel. ``None`` when
            the entry does not say.
        domain: What the text actually is, which is not always what the corpus
            calls itself -- see ``[corpora.sdu22_ae_legal]``.
        shortform_recall_ceiling_pct: Where short-form recall lands for a
            definition-only extractor on this corpus, or ``None``. Read
            :attr:`shortform_recall_ceiling_basis` before quoting it: whether
            the figure is a hard bound or merely the point past which recall is
            bought against the annotation is a per-corpus fact, and the field
            name is optimistic about it on purpose-built corpora.
        shortform_recall_ceiling_basis: How the figure was derived, and what
            kind of limit it is. Required whenever the figure is present.
        note: The entry's prose, carried through verbatim.
        extra: Any key this reader does not model, so an unrecognised field is
            preserved rather than silently dropped.
    """

    name: str
    role: str
    task: str
    licence: str
    licence_url: str
    licence_read_on: _datetime.date
    status: str = ""
    contaminated: bool = False
    contamination_reason: str = ""
    vendorable: Optional[bool] = None
    domain: str = ""
    shortform_recall_ceiling_pct: Optional[float] = None
    shortform_recall_ceiling_basis: str = ""
    note: str = ""
    extra: Mapping[str, Any] = field(default_factory=dict)

    @property
    def is_tuning(self) -> bool:
        """Whether every figure from this corpus is a tuning figure."""
        return self.role == "tuning"

    @property
    def is_held_out(self) -> bool:
        """Whether this corpus may back a headline number."""
        return self.role == "held_out"

    def require_role(self, expected: str) -> None:
        """Assert the declared role, so a runner cannot mislabel its own output.

        This is operating rule 2 made mechanical. A runner that prints
        "tuning split" in its header is making a claim about the manifest; this
        turns that claim into a check.

        Raises:
            SplitsError: If the declared role is not ``expected``.
        """
        if self.role != expected:
            raise SplitsError(
                f"{self.name} is declared role={self.role!r} in bench/splits.toml, not {expected!r}"
            )

    def label(self) -> str:
        """The label any figure from this corpus must carry.

        Returns:
            ``"tuning split"`` or ``"held out"``, plus ``", contaminated"`` when
            the entry says so.
        """
        base = "tuning split" if self.is_tuning else "held out"
        return f"{base}, contaminated" if self.contaminated else base


@dataclass(frozen=True)
class Policy:
    """The ``[policy]`` table.

    Attributes:
        headline_requires: The role a headline number must come from.
        label_tuning_numbers: Whether tuning figures must be labelled as such.
    """

    headline_requires: str = "held_out"
    label_tuning_numbers: bool = True


@dataclass(frozen=True)
class Manifest:
    """The whole of ``bench/splits.toml``, parsed."""

    path: Path
    policy: Policy
    corpora: Mapping[str, Corpus]

    @property
    def names(self) -> Tuple[str, ...]:
        """Every declared corpus name, sorted."""
        return tuple(sorted(self.corpora))

    def corpus(self, name: str) -> Corpus:
        """Look up one corpus, or say what is available.

        Raises:
            SplitsError: If ``name`` is not declared. This is the point of the
                accessor: a corpus that is measured but never declared is
                exactly the gap the manifest exists to close, and a
                ``KeyError`` would not say so.
        """
        try:
            return self.corpora[name]
        except KeyError:
            raise SplitsError(
                f"{name!r} is not declared in {self.path.name}. "
                f"Declared corpora: {', '.join(self.names)}. "
                "A corpus that is measured but not declared is exempt from the "
                "train/test rule by omission; add an entry rather than skipping it."
            ) from None

    def with_role(self, role: str) -> Tuple[Corpus, ...]:
        """Every corpus carrying ``role``, sorted by name."""
        return tuple(self.corpora[name] for name in self.names if self.corpora[name].role == role)

    def headline_capable(self) -> Tuple[Corpus, ...]:
        """Every corpus a headline number may legitimately come from."""
        return tuple(
            corpus
            for corpus in self.with_role(self.policy.headline_requires)
            if not corpus.contaminated
        )


def _as_bool(value: Any) -> Optional[bool]:
    """Coerce a TOML value to ``bool``, or ``None`` when it is absent."""
    return bool(value) if isinstance(value, bool) else None


def _as_date(value: Any) -> Optional[_datetime.date]:
    """Coerce a TOML value to a date.

    TOML has a native date type, so a bare ``2026-08-23`` parses to
    :class:`datetime.date` already; a quoted ``"2026-08-23"`` arrives as a
    string. Both are accepted and anything else is rejected by the validator.
    """
    if isinstance(value, _datetime.datetime):
        return value.date()
    if isinstance(value, _datetime.date):
        return value
    if isinstance(value, str):
        try:
            return _datetime.date.fromisoformat(value.strip())
        except ValueError:
            return None
    return None


_MODELLED = frozenset(
    {
        "role",
        "task",
        "licence",
        "licence_url",
        "licence_read_on",
        "status",
        "contaminated",
        "contamination_reason",
        "vendorable",
        "domain",
        "shortform_recall_ceiling_pct",
        "shortform_recall_ceiling_basis",
        "note",
    }
)


def _corpus_from(name: str, spec: Mapping[str, Any]) -> Corpus:
    """Build a :class:`Corpus` from one raw table, coercing nothing away.

    Fields that fail to coerce become their falsy defaults so the *validator*
    reports them, rather than this constructor raising. Two different error
    reports for one malformed file is how a check ends up with two behaviours.
    """
    ceiling = spec.get("shortform_recall_ceiling_pct")
    return Corpus(
        name=name,
        role=str(spec.get("role", "") or ""),
        task=str(spec.get("task", "") or ""),
        licence=str(spec.get("licence", "") or ""),
        licence_url=str(spec.get("licence_url", "") or ""),
        licence_read_on=_as_date(spec.get("licence_read_on")) or _datetime.date.min,
        status=str(spec.get("status", "") or ""),
        contaminated=bool(spec.get("contaminated", False)),
        contamination_reason=str(spec.get("contamination_reason", "") or ""),
        vendorable=_as_bool(spec.get("vendorable")),
        domain=str(spec.get("domain", "") or ""),
        shortform_recall_ceiling_pct=(
            float(ceiling)
            if isinstance(ceiling, (int, float)) and not isinstance(ceiling, bool)
            else None
        ),
        shortform_recall_ceiling_basis=str(spec.get("shortform_recall_ceiling_basis", "") or ""),
        note=str(spec.get("note", "") or ""),
        extra={key: value for key, value in spec.items() if key not in _MODELLED},
    )


def load(path: Optional[Path] = None) -> Manifest:
    """Parse the manifest into typed objects.

    Args:
        path: Override the default ``bench/splits.toml`` location, so tests can
            drive the same code against a fixture rather than against whatever
            the repository happens to hold today.

    Returns:
        The parsed manifest.

    Raises:
        SplitsError: If the file is missing, unparseable, or has no ``corpora``
            table at all. Everything softer than that is a *validation* finding
            and is reported by :func:`validate`, so one bad field does not stop
            the report that would have listed the other nine.
    """
    location = Path(path) if path is not None else SPLITS_PATH
    document = _load_toml(location)

    raw_corpora = document.get("corpora")
    if not isinstance(raw_corpora, dict) or not raw_corpora:
        raise SplitsError(f"{location} declares no corpora; the manifest guards nothing")

    raw_policy = document.get("policy") or {}
    policy = Policy(
        headline_requires=str(raw_policy.get("headline_requires", "held_out")),
        label_tuning_numbers=bool(raw_policy.get("label_tuning_numbers", True)),
    )
    corpora = {
        name: _corpus_from(name, spec)
        for name, spec in raw_corpora.items()
        if isinstance(spec, dict)
    }
    return Manifest(path=location, policy=policy, corpora=corpora)


def _licence_url_problem(url: str) -> Optional[str]:
    """Why ``url`` is not an acceptable citation for licence terms, if it is not."""
    parts = urlsplit(url)
    if parts.scheme not in ("http", "https") or not parts.netloc:
        return f"licence_url={url!r} is not an http(s) URL"
    host = parts.netloc.lower()
    if any(host == badge or host.endswith("." + badge) for badge in BADGE_HOSTS):
        return (
            f"licence_url={url!r} points at a badge host. Operating rule 4: read the terms. "
            "GLADIS's badge said CC0 while its own source table listed UMLS."
        )
    lowered = parts.path.lower()
    if any(fragment in lowered for fragment in BADGE_PATH_FRAGMENTS):
        return f"licence_url={url!r} points at a badge image, not licence text"
    if host == "api.github.com" and lowered.endswith("/license"):
        return (
            f"licence_url={url!r} is GitHub's licence *guess* for a repository, not the terms. "
            "It reported MIT for three corpora in this project whose data is CC BY-NC-SA."
        )
    return None


def _is_absent(corpus: Corpus, declared: str) -> bool:
    """Whether ``corpus`` failed to declare ``declared``.

    A date needs its own emptiness test: :func:`_corpus_from` writes
    :attr:`datetime.date.min` when the field is missing *or* unparseable, and
    that value is truthy, so a plain falsiness check would pass a corpus whose
    ``licence_read_on`` reads ``"last Tuesday"``.
    """
    if declared == "licence_read_on":
        return corpus.licence_read_on == _datetime.date.min
    return not getattr(corpus, declared)


def validate(manifest: Manifest, *, today: Optional[_datetime.date] = None) -> List[str]:
    """Every way this manifest fails the rules it exists to encode.

    Args:
        manifest: A loaded manifest.
        today: The date to judge ``licence_read_on`` against. Injectable so the
            test suite does not depend on the wall clock.

    Returns:
        Problems, one string each, in corpus order. Empty means valid.
    """
    now = today or _datetime.date.today()
    problems: List[str] = []

    if manifest.policy.headline_requires not in ROLES:
        problems.append(
            f"[policy] headline_requires={manifest.policy.headline_requires!r} "
            f"is not one of {list(ROLES)}"
        )

    for name in manifest.names:
        corpus = manifest.corpora[name]
        where = f"[corpora.{name}]"

        missing = [declared for declared in REQUIRED_FIELDS if _is_absent(corpus, declared)]
        if missing:
            problems.append(f"{where} is missing or empty: {', '.join(missing)}")

        if corpus.role and corpus.role not in ROLES:
            problems.append(f"{where} role={corpus.role!r} is not one of {list(ROLES)}")
        if corpus.task and corpus.task not in TASKS:
            problems.append(f"{where} task={corpus.task!r} is not one of {list(TASKS)}")

        if corpus.licence_url:
            problem = _licence_url_problem(corpus.licence_url)
            if problem:
                problems.append(f"{where} {problem}")

        if corpus.licence_read_on != _datetime.date.min and corpus.licence_read_on > now:
            problems.append(
                f"{where} licence_read_on={corpus.licence_read_on.isoformat()} is in the future"
            )

        if corpus.contaminated and not corpus.contamination_reason.strip():
            problems.append(
                f"{where} is contaminated=true with no contamination_reason. "
                "An unexplained contamination flag can never be argued down."
            )

        if corpus.contaminated and corpus.role == manifest.policy.headline_requires:
            problems.append(
                f"{where} is contaminated=true and role={corpus.role!r}, which is the role "
                "[policy] headline_requires. A corpus whose misses have been read adjudicates "
                "nothing blind, so it cannot be the one a headline number comes from. This is "
                "the MED1250 story: it was a test set until its miss taxonomy was analysed, and "
                "it could not be un-tuned afterwards."
            )

        ceiling = corpus.shortform_recall_ceiling_pct
        if ceiling is not None:
            if not 0.0 < ceiling <= 100.0:
                problems.append(f"{where} shortform_recall_ceiling_pct={ceiling} is not a percent")
            if not corpus.shortform_recall_ceiling_basis.strip():
                problems.append(
                    f"{where} declares a recall ceiling with no "
                    "shortform_recall_ceiling_basis. A ceiling whose derivation is "
                    "not written down cannot be checked, and it would be quoted."
                )
    return problems


def notes(manifest: Manifest, *, today: Optional[_datetime.date] = None) -> List[str]:
    """Advisories that must never fail a build.

    A licence read long ago is worth re-reading, and a project with no
    uncontaminated held-out corpus should be reminded of it. Neither is a defect
    in the commit being tested, so neither reds the build -- the gate that fires
    on an unrelated commit is the gate people learn to ignore.
    """
    now = today or _datetime.date.today()
    out: List[str] = []
    for name in manifest.names:
        corpus = manifest.corpora[name]
        if corpus.licence_read_on == _datetime.date.min:
            continue
        age = (now - corpus.licence_read_on).days
        if age > STALE_AFTER_DAYS:
            out.append(
                f"[corpora.{name}] licence last read {age} days ago "
                f"({corpus.licence_read_on.isoformat()}); worth re-reading"
            )
    if not manifest.headline_capable():
        out.append(
            f"no uncontaminated corpus carries role={manifest.policy.headline_requires!r}, "
            "so no number in this project currently satisfies the headline rule"
        )
    return out


def as_dict(manifest: Manifest) -> Dict[str, Any]:
    """The manifest as plain JSON-safe data, for ``--json`` and for tests."""
    return {
        "policy": {
            "headline_requires": manifest.policy.headline_requires,
            "label_tuning_numbers": manifest.policy.label_tuning_numbers,
        },
        "corpora": {
            name: {
                "role": corpus.role,
                "task": corpus.task,
                "licence": corpus.licence,
                "licence_url": corpus.licence_url,
                "licence_read_on": corpus.licence_read_on.isoformat(),
                "status": corpus.status,
                "contaminated": corpus.contaminated,
                "domain": corpus.domain,
                "vendorable": corpus.vendorable,
                "shortform_recall_ceiling_pct": corpus.shortform_recall_ceiling_pct,
                "label": corpus.label(),
            }
            for name, corpus in ((n, manifest.corpora[n]) for n in manifest.names)
        },
    }


def _render_table(manifest: Manifest) -> str:
    """The manifest as a table a person can read at a glance."""
    lines = [
        f"{'CORPUS':22} {'ROLE':9} {'TASK':16} {'READ':11} {'CEILING':>8}  LICENCE",
        f"{'-' * 22} {'-' * 9} {'-' * 16} {'-' * 11} {'-' * 8}  {'-' * 40}",
    ]
    for name in manifest.names:
        corpus = manifest.corpora[name]
        read = (
            "never"
            if corpus.licence_read_on == _datetime.date.min
            else corpus.licence_read_on.isoformat()
        )
        ceiling = (
            f"{corpus.shortform_recall_ceiling_pct:.2f}%"
            if corpus.shortform_recall_ceiling_pct is not None
            else "-"
        )
        role = corpus.role + ("*" if corpus.contaminated else "")
        lines.append(
            f"{name:22} {role:9} {corpus.task:16} {read:11} {ceiling:>8}  {corpus.licence}"
        )
    lines.append("")
    lines.append(
        "* contaminated: the corpus has been read closely enough that it adjudicates nothing blind."
    )
    return "\n".join(lines)


def main(argv: Optional[Sequence[str]] = None) -> int:
    """Command-line entry point.

    Returns:
        ``0`` when the manifest parses and validates, ``1`` otherwise.
    """
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--check", action="store_true", help="validate and exit non-zero on error")
    parser.add_argument("--list", action="store_true", help="print the manifest as a table")
    parser.add_argument("--json", action="store_true", help="print the manifest as JSON")
    parser.add_argument(
        "--path",
        type=Path,
        default=SPLITS_PATH,
        help="manifest to read (default: bench/splits.toml)",
    )
    args = parser.parse_args(argv)

    try:
        manifest = load(args.path)
    except SplitsError as error:
        print(f"error: {error}", file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps(as_dict(manifest), indent=2, sort_keys=True))
        return 0
    if args.list:
        print(_render_table(manifest))
        return 0

    problems = validate(manifest)
    print(f"{args.path}: {len(manifest.corpora)} corpora, {len(problems)} problem(s)")
    for note in notes(manifest):
        print(f"  note: {note}")
    if not problems:
        print(
            "splits manifest OK: every corpus declares a role, a task, and a licence read "
            "from its terms at a recorded URL on a recorded date"
        )
        return 0
    print(f"\n{len(problems)} problem(s):\n", file=sys.stderr)
    for problem in problems:
        print(f"  {problem}", file=sys.stderr)
    print(
        "\nbench/splits.toml is the file operating rules 2 and 4 rest on. Every corpus must\n"
        "declare role, task, licence, licence_url and licence_read_on -- the last two because\n"
        "a licence string on its own records a conclusion and destroys the evidence for it.",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
