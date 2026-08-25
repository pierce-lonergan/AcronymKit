#!/usr/bin/env python3
"""Build a self-contained archive that installs ``acronymkit`` with no package index.

Why this exists
---------------
PyPI is a single point of failure that the person installing this library does
not control. It can be blocked by policy, unreachable from a segmented network,
or simply down on the afternoon someone needs it. This script produces one
archive holding the ``acronymkit`` wheel and every wheel it depends on, so an
install becomes a file copy followed by::

    pip install --no-index --find-links=. acronymkit

The obvious point, said out loud because it is the whole design: **building** a
bundle needs the network -- the dependency wheels are downloaded from an index.
**Using** one does not. One connected machine builds the archive; any number of
disconnected machines install from it, and none of them ever resolves a name
against an index.

The hard part, stated rather than hidden
----------------------------------------
A bundle is not universal, and a bundle that silently fails to install is worse
than no bundle. ``pydantic`` -- the only non-trivial runtime dependency --
delegates its validation core to ``pydantic-core``, a Rust extension module
published as *platform- and interpreter-specific* wheels: one file per
(CPython minor version x operating system x CPU architecture x libc). A wheel
named ``pydantic_core-2.46.4-cp311-cp311-manylinux_2_17_x86_64...whl`` installs
on CPython 3.11 on glibc Linux/x86-64 and on nothing else. It is not ``abi3``,
so it does not even carry across CPython minor versions.

This script therefore builds **one bundle per target**, and the target is named
in the archive's filename and stated in the README inside it. Each bundle
carries a wheel for every CPython minor version that target serves, so a single
Linux/x86-64 archive covers CPython 3.9 through 3.13; ``pip`` then picks the
matching file at install time. Nothing here guesses: after staging, the bundle
is re-resolved with ``pip install --dry-run --no-index`` once per served
interpreter, against the bundle contents alone, and the build fails if any of
those resolutions does not succeed.

For a platform not in :data:`TARGETS` -- a big-endian mainframe, a musl
distribution on ARM, an interpreter newer than this registry -- run the script
with ``--target host`` on a networked machine *of that platform*. That mode
passes no ``--platform`` to ``pip`` at all, so the running interpreter's own
tags decide what is downloaded, and the resulting archive is correct for that
machine by construction.

Two other honest limits
-----------------------
* A cross-platform ``pip download`` cannot evaluate environment markers that
  depend on the operating system, so wheels gated on ``platform_system ==
  "Windows"`` (``colorama``, pulled in by ``click``) are staged into every
  bundle. They are pure Python and inert off Windows; they are listed in the
  manifest like everything else rather than quietly dropped.
* The ``nlp`` and ``transformers`` extras are excluded by default and their
  *models* are a separate problem this script does not solve. See
  ``docs/INSTALL.md``.

Usage
-----
::

    python tools/make_offline_bundle.py --list-targets
    python tools/make_offline_bundle.py --target host
    python tools/make_offline_bundle.py --target linux-x86_64
    python tools/make_offline_bundle.py --all --output-dir dist/bundles
    python tools/make_offline_bundle.py --target windows-amd64 --extras cli,nlp

Only the standard library is imported; ``pip`` is driven as a subprocess and
``build`` is needed only when the script has to build the wheel itself (pass
``--wheel`` to reuse one that already exists).

Exit codes:
    ``0`` every requested bundle was built and re-resolved offline, ``1`` a
    build, download or offline-resolution check failed, ``2`` usage error.
"""

from __future__ import annotations

import argparse
import datetime as _datetime
import hashlib
import json
import platform
import re
import shutil
import subprocess
import sys
import sysconfig
import tempfile
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

#: ``<repo>/tools`` -- this script's own directory.
TOOLS_DIR = Path(__file__).resolve().parent

#: Repository root, located relative to ``__file__``.
REPO_ROOT = TOOLS_DIR.parent

#: Where bundles land by default. ``dist/`` is already git-ignored, which is the
#: reason for the choice: a 12 MB archive must not become committable by
#: accident.
DEFAULT_OUTPUT_DIR = REPO_ROOT / "dist"

#: CPython minor versions each registry target serves. This mirrors the
#: ``Programming Language :: Python :: 3.x`` classifiers in ``pyproject.toml``:
#: the bundle promises exactly what the project promises, no more. To serve an
#: interpreter outside this list, pass ``--python-version`` (repeatable) and
#: read the failure if the dependency has no wheel for it.
DEFAULT_PYTHON_VERSIONS = ("3.9", "3.10", "3.11", "3.12", "3.13")

#: Extras staged by default. ``cli`` is one pure-Python wheel (``click``) and it
#: is what makes ``acronymkit generate`` work, so leaving it out would ship a
#: bundle that installs a library nobody can run from a terminal. ``nlp`` and
#: ``transformers`` are opt-in: they are hundreds of megabytes and their models
#: are not solved by staging wheels.
DEFAULT_EXTRAS = ("cli",)

#: Where a released wheel can be fetched from without an index. Used in the
#: bundle README's by-hand fallback, and named by URL rather than by
#: distribution name on purpose: a PEP 508 direct reference resolves on a
#: machine whose index does not carry ``acronymkit`` at all, which is the
#: situation the whole document is about.
RELEASE_WHEEL_URL = (
    "https://github.com/pierce-lonergan/AcronymKit/releases/download/"
    "v{version}/acronymkit-{version}-py3-none-any.whl"
)

#: Fixed timestamp for every archive member. Rebuilding a bundle from the same
#: resolved wheels then differs only in ``MANIFEST.json``'s ``generated_utc``
#: field, rather than in every entry's mtime.
ZIP_TIMESTAMP = (1980, 1, 1, 0, 0, 0)

#: ``name-version[-build]-pytag-abitag-platformtag.whl``. Tag fields may be
#: compressed sets joined by ``.``, which is why the tail is taken positionally
#: rather than by counting hyphens from the left.
_WHEEL_NAME = re.compile(r"^(?P<name>.+?)-(?P<version>[^-]+)(?:-\d[^-]*)?-[^-]+-[^-]+-[^-]+\.whl$")


@dataclass(frozen=True)
class Target:
    """One installation target a bundle can serve.

    Attributes:
        name: Registry key, and the string that appears in the archive filename.
        platforms: ``pip --platform`` tags, most preferred first. Empty means
            "do not pass ``--platform`` at all", which is what ``--target host``
            uses so that the running interpreter's own tags decide.
        python_versions: CPython minor versions this target serves. One wheel
            per version is staged for every compiled dependency.
        summary: One line naming the target, for the README table.
        requirement: What a machine must actually be for this bundle to install,
            written for someone deciding whether it is theirs.
    """

    name: str
    platforms: Tuple[str, ...]
    python_versions: Tuple[str, ...]
    summary: str
    requirement: str


#: The declared target list. Each entry's ``platforms`` is ordered
#: least-demanding first, because ``pip`` treats the order as a preference and
#: the wheel with the lowest platform floor runs on the most machines.
#:
#: ``windows-arm64`` serves a shorter interpreter list than the others, and the
#: reason is upstream rather than a policy here: ``pydantic-core`` publishes no
#: ``win_arm64`` wheel for CPython 3.9 or 3.10. Requesting one does not fail
#: loudly -- ``pip download pydantic-core --platform win_arm64 --python-version
#: 3.9`` resolves all the way back to a 0.0.1 placeholder release -- so the
#: narrowing is written down here instead of being discovered by whoever
#: installs the result.
TARGETS: Dict[str, Target] = {
    "linux-x86_64": Target(
        name="linux-x86_64",
        platforms=(
            "manylinux_2_17_x86_64",
            "manylinux2014_x86_64",
            "manylinux_2_28_x86_64",
            "manylinux_2_34_x86_64",
        ),
        python_versions=DEFAULT_PYTHON_VERSIONS,
        summary="Linux, 64-bit Intel/AMD (x86-64), glibc",
        requirement=(
            "A glibc Linux distribution on x86-64 with glibc 2.17 or newer -- "
            "RHEL/CentOS 7+, Debian 8+, Ubuntu 14.04+, and anything more recent. "
            "Not Alpine or another musl distribution: use linux-musl-x86_64."
        ),
    ),
    "linux-aarch64": Target(
        name="linux-aarch64",
        platforms=(
            "manylinux_2_17_aarch64",
            "manylinux2014_aarch64",
            "manylinux_2_28_aarch64",
            "manylinux_2_34_aarch64",
        ),
        python_versions=DEFAULT_PYTHON_VERSIONS,
        summary="Linux, 64-bit ARM (aarch64), glibc",
        requirement=(
            "A glibc Linux distribution on 64-bit ARM with glibc 2.17 or newer -- "
            "AWS Graviton, Ampere, Raspberry Pi OS 64-bit, and similar. "
            "Not Alpine or another musl distribution."
        ),
    ),
    "linux-musl-x86_64": Target(
        name="linux-musl-x86_64",
        platforms=("musllinux_1_1_x86_64", "musllinux_1_2_x86_64"),
        python_versions=DEFAULT_PYTHON_VERSIONS,
        summary="Linux, 64-bit Intel/AMD (x86-64), musl",
        requirement=(
            "A musl Linux distribution on x86-64 -- Alpine 3.13 or newer, and "
            "the python:*-alpine container images. Not a glibc distribution."
        ),
    ),
    "macos-arm64": Target(
        name="macos-arm64",
        platforms=(
            "macosx_11_0_arm64",
            "macosx_12_0_arm64",
            "macosx_13_0_arm64",
            "macosx_14_0_arm64",
            "macosx_10_12_universal2",
            "macosx_11_0_universal2",
        ),
        python_versions=DEFAULT_PYTHON_VERSIONS,
        summary="macOS, Apple silicon (arm64)",
        requirement=(
            "macOS 11 Big Sur or newer on an M-series Mac, running a native "
            "arm64 CPython. A Rosetta/x86-64 CPython on the same Mac needs the "
            "macos-x86_64 bundle instead -- check with "
            '`python -c "import platform; print(platform.machine())"`.'
        ),
    ),
    "macos-x86_64": Target(
        name="macos-x86_64",
        platforms=(
            "macosx_10_12_x86_64",
            "macosx_11_0_x86_64",
            "macosx_12_0_x86_64",
            "macosx_10_12_universal2",
            "macosx_11_0_universal2",
        ),
        python_versions=DEFAULT_PYTHON_VERSIONS,
        summary="macOS, Intel (x86-64)",
        requirement=(
            "macOS 10.12 Sierra or newer on an Intel Mac, or a Rosetta/x86-64 "
            "CPython on an M-series Mac."
        ),
    ),
    "windows-amd64": Target(
        name="windows-amd64",
        platforms=("win_amd64",),
        python_versions=DEFAULT_PYTHON_VERSIONS,
        summary="Windows, 64-bit Intel/AMD (AMD64)",
        requirement=(
            "64-bit Windows running a 64-bit CPython. A 32-bit CPython on the "
            "same machine is not served -- check with "
            '`python -c "import sysconfig; print(sysconfig.get_platform())"`, '
            "which must print win-amd64."
        ),
    ),
    "windows-arm64": Target(
        name="windows-arm64",
        platforms=("win_arm64",),
        python_versions=("3.11", "3.12", "3.13"),
        summary="Windows, 64-bit ARM (ARM64)",
        requirement=(
            "Windows on ARM running a native ARM64 CPython 3.11, 3.12 or 3.13. "
            "CPython 3.9 and 3.10 are not served because pydantic-core "
            "publishes no win_arm64 wheel for them."
        ),
    ),
}


def host_target() -> Target:
    """Describe the machine this script is running on as a bundle target.

    Passing no ``--platform`` to ``pip`` is not a weaker version of naming one:
    it is the only way to be certain, because the running interpreter's own tag
    set is the ground truth that a hand-written platform tag can only
    approximate. This is therefore the escape hatch for any machine
    :data:`TARGETS` does not cover.

    Returns:
        A target whose ``platforms`` is empty and whose ``python_versions`` is
        the single running interpreter version.
    """
    version = f"{sys.version_info.major}.{sys.version_info.minor}"
    tag = sysconfig.get_platform().replace("-", "_").replace(".", "_")
    return Target(
        name=f"host-{tag}",
        platforms=(),
        python_versions=(version,),
        summary=(
            f"{platform.system()} {platform.machine()}, "
            f"{platform.python_implementation()} {version}"
        ),
        requirement=(
            f"A machine matching the one this bundle was built on: "
            f"{platform.platform()}, {platform.python_implementation()} "
            f"{platform.python_version()} ({sysconfig.get_platform()}). It was "
            f"built without a --platform override, so it is exactly as portable "
            f"as that interpreter's own wheel tags and no more."
        ),
    )


@dataclass(frozen=True)
class WheelFile:
    """A staged wheel, identified the way ``pip`` identifies one.

    Attributes:
        path: Location on disk.
        name: Canonical (PEP 503) distribution name.
        version: Version string exactly as it appears in the filename.
        digest: Lowercase hex SHA-256 of the file.
    """

    path: Path
    name: str
    version: str
    digest: str


def write_text(path: Path, text: str) -> None:
    """Write a text file into the bundle with LF endings, whatever the host.

    ``Path.write_text`` translates ``\\n`` to ``\\r\\n`` on Windows, and the
    bundle's own README tells the reader to run ``sha256sum -c SHA256SUMS`` --
    which fails on every line of a CRLF file, reporting each name as missing.
    A bundle built on Windows would therefore have shipped with a verification
    command that could not work on the machine it was aimed at. The bundle is an
    artefact for other people's machines, so its line endings are a property of
    the artefact rather than of the machine that produced it.

    Args:
        path: File to write.
        text: Contents, using ``\\n`` throughout.
    """
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(text)


def canonical_name(name: str) -> str:
    """Normalise a distribution name to its PEP 503 form.

    Wheel filenames escape the name (``typing_extensions``) while requirement
    strings use the published form (``typing-extensions``); comparing the two
    without normalising is a bug that only shows up on the packages whose names
    contain a separator.

    Args:
        name: Raw distribution name from a filename or a requirement.

    Returns:
        Lowercase name with runs of ``-``, ``_`` and ``.`` collapsed to ``-``.
    """
    return re.sub(r"[-_.]+", "-", name).lower()


def read_wheel(path: Path) -> WheelFile:
    """Parse a wheel filename and hash the file.

    Args:
        path: Path to a ``.whl``.

    Returns:
        The parsed :class:`WheelFile`.

    Raises:
        ValueError: If the filename is not a well-formed wheel name. This is
            never a user error in practice -- it means something other than a
            wheel reached the staging directory, which is exactly the case that
            must not be waved through.
    """
    match = _WHEEL_NAME.match(path.name)
    if match is None:
        raise ValueError(f"not a wheel filename: {path.name}")
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    return WheelFile(
        path=path,
        name=canonical_name(match.group("name")),
        version=match.group("version"),
        digest=digest,
    )


def run_pip(arguments: Sequence[str], *, what: str) -> None:
    """Run one ``pip`` subcommand, surfacing its output only when it fails.

    A successful download prints a page of progress bars that hides the one line
    worth reading. A failed one prints the resolver's explanation, which is the
    single most useful artefact this script can hand back.

    Args:
        arguments: Arguments after ``python -m pip``.
        what: Short description used in the error message.

    Raises:
        SystemExit: With status 1 if ``pip`` exits non-zero.
    """
    command = [sys.executable, "-m", "pip", "--disable-pip-version-check", *arguments]
    done = subprocess.run(command, capture_output=True, text=True)
    if done.returncode != 0:
        sys.stderr.write(done.stdout)
        sys.stderr.write(done.stderr)
        sys.stderr.write(f"\nERROR: {what} failed (pip exited {done.returncode})\n")
        raise SystemExit(1)


def pip_version() -> str:
    """Return the version of the ``pip`` doing the downloading.

    Recorded in the manifest because ``pip``'s tag handling and resolver are
    what decide which wheels a bundle ends up containing.

    Returns:
        The version string, or ``"unknown"`` if ``pip`` cannot be questioned.
    """
    done = subprocess.run(
        [sys.executable, "-m", "pip", "--version"], capture_output=True, text=True
    )
    if done.returncode != 0:
        return "unknown"
    parts = done.stdout.split()
    return parts[1] if len(parts) > 1 else "unknown"


def build_project_wheel(output_dir: Path) -> Path:
    """Build the ``acronymkit`` wheel from this checkout.

    Args:
        output_dir: Directory the wheel is written to.

    Returns:
        Path to the built wheel.

    Raises:
        SystemExit: With status 1 if the build fails or produces no wheel.
    """
    done = subprocess.run(
        [sys.executable, "-m", "build", "--wheel", "--outdir", str(output_dir), str(REPO_ROOT)],
        capture_output=True,
        text=True,
    )
    if done.returncode != 0:
        sys.stderr.write(done.stdout)
        sys.stderr.write(done.stderr)
        sys.stderr.write("\nERROR: `python -m build --wheel` failed\n")
        raise SystemExit(1)
    wheels = sorted(output_dir.glob("acronymkit-*.whl"))
    if not wheels:
        sys.stderr.write("ERROR: the build produced no acronymkit wheel\n")
        raise SystemExit(1)
    return wheels[-1]


def stage_downloads(
    target: Target,
    python_version: str,
    requirement: str,
    find_links: Path,
    destination: Path,
) -> None:
    """Download the dependency closure for one interpreter of one target.

    ``--only-binary=:all:`` is load-bearing rather than a preference. A source
    distribution would have to be *built* during the offline install, a build
    needs build dependencies, and fetching those needs an index -- so admitting
    one sdist would quietly reintroduce the requirement this bundle exists to
    remove. If this ever fails because no wheel exists, that is the finding.

    Args:
        target: Target being built; its ``platforms`` become ``--platform``.
        python_version: CPython minor version, as ``"3.11"``.
        requirement: Root requirement, e.g. ``acronymkit[cli]==0.2.0``.
        find_links: Directory holding the locally built ``acronymkit`` wheel.
        destination: Directory the wheels are downloaded into.
    """
    arguments = [
        "download",
        "--only-binary=:all:",
        "--dest",
        str(destination),
        "--find-links",
        str(find_links),
    ]
    if target.platforms:
        # --platform disables pip's automatic tag-compatibility expansion, so
        # every acceptable tag has to be named. It also forces --implementation
        # and --python-version to be explicit, since there is no interpreter to
        # ask.
        arguments += ["--python-version", python_version, "--implementation", "cp"]
        for tag in target.platforms:
            arguments += ["--platform", tag]
    arguments.append(requirement)
    run_pip(arguments, what=f"downloading {target.name} wheels for CPython {python_version}")


def resolve_offline(
    target: Target,
    python_version: str,
    requirement: str,
    bundle_dir: Path,
    extra_arguments: Sequence[str] = (),
) -> None:
    """Prove that the staged bundle resolves for one interpreter, with no index.

    This is the check that distinguishes a bundle from a directory of wheels
    somebody hoped were the right ones. ``--dry-run`` performs the whole
    resolution and installs nothing, ``--no-index`` removes any index as a
    source, and ``--find-links`` pointed at the bundle makes the bundle the only
    source there is. If a wheel is missing for this interpreter, the resolver
    says so here rather than on the air-gapped machine.

    Args:
        target: Target being checked.
        python_version: CPython minor version, as ``"3.11"``.
        requirement: Root requirement, or ``""`` when ``extra_arguments``
            supplies ``-r requirements.txt`` instead.
        bundle_dir: The staged bundle directory.
        extra_arguments: Additional ``pip install`` arguments.
    """
    with tempfile.TemporaryDirectory() as scratch:
        arguments = [
            "install",
            "--dry-run",
            "--ignore-installed",
            "--no-index",
            "--only-binary=:all:",
            "--find-links",
            str(bundle_dir),
            # --platform requires one of --target/--no-deps/--dry-run; --target
            # is passed as well so the combination is accepted by every pip that
            # supports --dry-run at all. --dry-run writes nothing into it.
            "--target",
            str(Path(scratch) / "unused"),
        ]
        if target.platforms:
            arguments += ["--python-version", python_version, "--implementation", "cp"]
            for tag in target.platforms:
                arguments += ["--platform", tag]
        arguments += list(extra_arguments)
        if requirement:
            arguments.append(requirement)
        run_pip(
            arguments,
            what=(
                f"offline re-resolution of the {target.name} bundle for CPython {python_version}"
            ),
        )


def requirements_text(
    root_requirement: str,
    root: WheelFile,
    resolved: Dict[str, Dict[str, str]],
    wheels: Dict[Tuple[str, str], List[WheelFile]],
    only: Optional[str] = None,
) -> str:
    """Render a hash-pinned ``requirements.txt`` for the whole bundle.

    Two shapes of complication, both real and both handled rather than papered
    over:

    * One distribution may be present at several *versions* in one bundle,
      because a dependency that dropped an old interpreter resolves differently
      for CPython 3.9 than for 3.13. Those lines are split by a
      ``python_version`` marker, which ``pip`` evaluates and which makes the
      duplicate names legal in a single file.
    * One (name, version) may be present as several *files*, one per served
      interpreter. ``pip`` accepts several ``--hash`` values for one requirement
      and treats a match against any of them as success, which is exactly the
      semantics wanted here.

    Args:
        root_requirement: The root requirement with extras, e.g.
            ``acronymkit[cli]==0.2.0``.
        root: The bundled ``acronymkit`` wheel.
        resolved: ``{python_version: {canonical name: version}}``.
        wheels: ``{(canonical name, version): [wheel files]}``.
        only: Render the pins for this interpreter alone, with no markers. Used
            by the build's own verification pass, for a reason worth writing
            down: ``pip`` evaluates markers in a requirements file against the
            *running* interpreter even when ``--python-version`` names another
            one, so a marker-carrying file cannot be dry-run against a target it
            is not currently on. Pre-selecting the lines removes markers from
            the question and leaves the pins, hashes and resolvability -- the
            parts that can be checked from here -- genuinely checked.

    Returns:
        The file contents, ending in a newline.
    """
    by_name: Dict[str, Dict[str, List[str]]] = {}
    selected = resolved if only is None else {only: resolved[only]}
    for python_version, versions in sorted(selected.items()):
        for name, version in versions.items():
            by_name.setdefault(name, {}).setdefault(version, []).append(python_version)

    if only is not None:
        lines = [f"# Pins for CPython {only} alone, markers pre-evaluated.", ""]
    else:
        lines = [
            "# Hash-pinned requirements for this offline bundle.",
            "#",
            "# Install with hash checking, from the bundle directory:",
            "#",
            "#     pip install --no-index --find-links=. --require-hashes -r requirements.txt",
            "#",
            "# A requirement listed more than once carries a python_version marker:",
            "# a dependency that dropped an older interpreter resolves to a different",
            "# version there, and pip evaluates the marker and ignores the rest.",
            "",
        ]

    def render(requirement: str, files: List[WheelFile], marker: str) -> List[str]:
        head = f"{requirement} ; {marker}" if marker else requirement
        rendered = [f"{head} \\"]
        digests = sorted({wheel.digest for wheel in files})
        for index, digest in enumerate(digests):
            suffix = "" if index == len(digests) - 1 else " \\"
            rendered.append(f"    --hash=sha256:{digest}{suffix}")
        return rendered

    lines += render(root_requirement, [root], "")
    for name in sorted(by_name):
        if name == root.name:
            continue
        served = by_name[name]
        for version in sorted(served):
            marker = ""
            if only is None and len(served) > 1:
                marker = " or ".join(
                    f'python_version == "{value}"' for value in sorted(served[version])
                )
            lines += render(f"{name}=={version}", wheels[(name, version)], marker)
    return "\n".join(lines) + "\n"


def sha256sums_text(directory: Path) -> str:
    """Render a ``sha256sum``-compatible manifest of every file in a directory.

    The two-space separator and the relative filename are not cosmetic: they are
    what let ``sha256sum -c SHA256SUMS`` verify the bundle on any Linux box
    without this project's tooling being present.

    Args:
        directory: Bundle directory. ``SHA256SUMS`` itself is skipped if present.

    Returns:
        One ``<hex>  <filename>`` line per file, sorted by filename.
    """
    lines = []
    # Sorted by name rather than by Path, because Path comparison is
    # case-insensitive on Windows and case-sensitive elsewhere: sorting the
    # objects would put MANIFEST.json in a different place depending on which
    # machine built the bundle, for no reason a reader could see.
    for path in sorted(directory.iterdir(), key=lambda item: item.name):
        if not path.is_file() or path.name == "SHA256SUMS":
            continue
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        lines.append(f"{digest}  {path.name}")
    return "\n".join(lines) + "\n"


VERIFY_SCRIPT = '''#!/usr/bin/env python3
"""Check this bundle before installing from it.

Two different questions, and a bundle can pass one while failing the other:

1. **Is it intact?** Every file named in ``SHA256SUMS`` is hashed and compared,
   and any unlisted ``.whl`` sitting in the directory is reported. That second
   half matters more than it looks: the install command points ``pip`` at this
   directory with ``--find-links``, so a wheel dropped in here is a wheel pip
   will happily consider.

2. **Does it serve this machine?** The compiled wheels are tagged for particular
   interpreters and platforms. This compares those tags against the running
   interpreter, so the answer arrives now rather than as a resolver error.

Usage::

    python verify.py

Exit codes: ``0`` intact and usable here, ``1`` a hash mismatch, a missing file
or an unlisted wheel, ``2`` intact but this interpreter or platform is not one
this bundle serves.
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent


def compatible_tags():
    """Return this interpreter's wheel tag set, or None if it cannot be built.

    ``packaging`` is not in the standard library, so on a bare interpreter the
    only copy available is the one vendored inside pip. Both are tried, and a
    failure to find either is reported rather than guessed around -- a wrong
    compatibility verdict would be worse than an absent one.
    """
    try:
        from packaging.tags import sys_tags
    except Exception:
        try:
            from pip._vendor.packaging.tags import sys_tags
        except Exception:
            return None
    try:
        return {str(tag) for tag in sys_tags()}
    except Exception:
        return None


def wheel_tags(filename):
    """Expand the compressed tag set in a wheel filename into individual tags."""
    stem = filename[: -len(".whl")]
    parts = stem.split("-")
    if len(parts) < 5:
        return set()
    pythons, abis, platforms = parts[-3], parts[-2], parts[-1]
    return {
        "%s-%s-%s" % (python, abi, plat)
        for python in pythons.split(".")
        for abi in abis.split(".")
        for plat in platforms.split(".")
    }


def check_hashes():
    """Verify every listed file, and report anything unlisted. Returns problems."""
    problems = []
    sums = HERE / "SHA256SUMS"
    if not sums.is_file():
        return ["SHA256SUMS is missing, so nothing in this bundle can be verified"]
    listed = set()
    checked = 0
    for line in sums.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        digest, _, name = line.partition("  ")
        name = name.lstrip("*").strip()
        listed.add(name)
        path = HERE / name
        if not path.is_file():
            problems.append("missing: %s" % name)
            continue
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        if actual != digest:
            problems.append("CHANGED: %s (expected %s, got %s)" % (name, digest, actual))
        else:
            checked += 1
    for path in sorted(HERE.iterdir()):
        if not path.is_file() or path.name in ("SHA256SUMS",) or path.name in listed:
            continue
        if path.suffix == ".whl":
            problems.append("unlisted wheel, pip would consider it: %s" % path.name)
        else:
            print("note: unlisted file %s" % path.name)
    print("verified %d of %d listed files" % (checked, len(listed)))
    return problems


def check_compatibility():
    """Compare the bundle's wheels against this interpreter. Returns problems."""
    manifest_path = HERE / "MANIFEST.json"
    if not manifest_path.is_file():
        return ["MANIFEST.json is missing, so the target cannot be identified"]
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    problems = []

    running = "%d.%d" % sys.version_info[:2]
    served = manifest.get("python_versions", [])
    if running not in served:
        problems.append(
            "this is CPython %s; the bundle serves %s" % (running, ", ".join(served))
        )
    print("bundle target: %s (%s)" % (manifest.get("target"), manifest.get("summary")))

    tags = compatible_tags()
    if tags is None:
        print(
            "note: neither packaging nor pip's vendored copy is importable here, "
            "so platform tags were not checked; the README states the target"
        )
        return problems

    binary = {}
    for entry in manifest.get("files", []):
        name = entry.get("name", "")
        if not name.endswith(".whl"):
            continue
        expanded = wheel_tags(name)
        if all(tag.endswith("-any") for tag in expanded):
            continue
        binary.setdefault(entry.get("distribution", name), []).append((name, expanded))
    for distribution, candidates in sorted(binary.items()):
        usable = [name for name, expanded in candidates if expanded & tags]
        if usable:
            print("compiled wheel for this machine: %s" % usable[0])
        else:
            problems.append(
                "no %s wheel here matches this interpreter (%d candidates)"
                % (distribution, len(candidates))
            )
    return problems


def main():
    integrity = check_hashes()
    for problem in integrity:
        print("FAIL: %s" % problem)
    if integrity:
        print("\\nThis bundle is not intact. Do not install from it.")
        return 1
    compatibility = check_compatibility()
    for problem in compatibility:
        print("UNSUPPORTED: %s" % problem)
    if compatibility:
        print(
            "\\nThe bundle is intact but was not built for this machine. "
            "See README.md, section 'If this bundle is not for your machine'."
        )
        return 2
    print("\\nOK: intact, and it serves this interpreter.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
'''


def readme_text(
    version: str,
    target: Target,
    extras: Sequence[str],
    root_requirement: str,
    wheel_names: Sequence[str],
    generated: str,
) -> str:
    """Render the README that ships inside the bundle.

    Whoever opens this archive may have found it on a USB stick with no context.
    The README therefore has to answer, in order: what is this, does it fit my
    machine, how do I install it, how do I check it, and what do I do if it does
    not fit. Anything else is decoration.

    Args:
        version: ``acronymkit`` version in the bundle.
        target: Target the bundle was built for.
        extras: Extras staged into the bundle.
        root_requirement: The requirement string install commands should use.
        wheel_names: Filenames of every wheel in the bundle, sorted.
        generated: UTC timestamp the bundle was built at.

    Returns:
        Markdown, ending in a newline.
    """
    served = ", ".join(f"CPython {value}" for value in target.python_versions)
    extras_note = ", ".join(extras) if extras else "none"
    lines = [
        f"# acronymkit {version} -- offline install bundle ({target.name})",
        "",
        "Everything needed to install `acronymkit` on a machine that cannot reach PyPI.",
        "No index is contacted at install time; the wheels below are the only source.",
        "",
        "## Does this bundle fit your machine?",
        "",
        "| | |",
        "|---|---|",
        f"| Target | `{target.name}` |",
        f"| Platform | {target.summary} |",
        f"| Interpreters | {served} |",
        f"| Extras included | {extras_note} |",
        f"| acronymkit | {version} |",
        f"| Built (UTC) | {generated} |",
        "",
        f"{target.requirement}",
        "",
        "The check is not a formality. `pydantic-core` is a compiled Rust extension with one",
        "wheel per interpreter, operating system and CPU architecture, so a bundle built for a",
        "different target will fail to resolve rather than install something subtly wrong.",
        "Run the verifier first and it will tell you before pip does:",
        "",
        "```",
        "python verify.py",
        "```",
        "",
        "It exits `0` if the bundle is intact and serves this interpreter, `1` if a file has",
        "changed or is missing, and `2` if the bundle is fine but was built for another machine.",
        "",
        "## Install",
        "",
        "From this directory, with no network and no index:",
        "",
        "```",
        "pip install --no-index --find-links=. acronymkit",
        "```",
    ]
    if extras:
        lines += [
            "",
            f"The `{extras_note}` extra is staged here too, so this works as well "
            "(the quotes are for zsh and fish, which treat brackets as globs):",
            "",
            "```",
            f'pip install --no-index --find-links=. "{root_requirement.split("==")[0]}"',
            "```",
        ]
    lines += [
        "",
        "To have pip check every file against a pinned SHA-256 as it installs, which is the",
        "stronger form and the one to use if the archive travelled through anything you do not",
        "control:",
        "",
        "```",
        "pip install --no-index --find-links=. --require-hashes -r requirements.txt",
        "```",
        "",
        "## Verify",
        "",
        "`SHA256SUMS` covers every other file in this directory. Any of these works:",
        "",
        "```",
        "python verify.py                 # anywhere Python runs; also checks the target",
        "sha256sum -c SHA256SUMS          # Linux, macOS (as shasum -a 256 -c)",
        "```",
        "",
        "On Windows PowerShell:",
        "",
        "```",
        "Get-Content SHA256SUMS | ForEach-Object {",
        "  $fields = $_ -split '\\s+', 2",
        "  $actual = (Get-FileHash -Algorithm SHA256 $fields[1].Trim()).Hash.ToLower()",
        '  if ($actual -ne $fields[0]) { Write-Error "CHANGED: $($fields[1])" }',
        "}",
        "```",
        "",
        "`SHA256SUMS` proves the bundle is internally consistent, not that it came from this",
        "project. For that, compare this archive's own SHA-256 against the one published beside",
        "it on the GitHub release page, over a channel that is not this archive.",
        "",
        "## If this bundle is not for your machine",
        "",
        "Other targets are published beside this one on the same release page -- look for the",
        "archive whose name carries your platform. If none of them matches, build one on any",
        "networked machine *of your platform*, from a checkout of this project:",
        "",
        "```",
        "python tools/make_offline_bundle.py --target host",
        "```",
        "",
        "That mode passes no platform override to pip, so the running interpreter's own wheel",
        "tags decide what is downloaded and the result is correct for that machine by",
        "construction. The equivalent by hand, if you would rather not run the script -- the",
        "requirement names the release wheel by URL rather than by name, so it does not depend",
        "on `acronymkit` being present on whatever index you have:",
        "",
        "```",
        "pip download --only-binary=:all: --dest bundle \\",
        f'  "{root_requirement.split("==")[0]} @ {RELEASE_WHEEL_URL.format(version=version)}"',
        f'cd bundle && pip install --no-index --find-links=. "{root_requirement.split("==")[0]}"',
        "```",
        "",
        "## What is not in here",
        "",
        "* **spaCy and NLTK models.** The `nlp` extra installs the libraries; their language",
        "  models are separate downloads with their own licences and are not wheels, so no",
        "  amount of wheel staging solves them. `acronymkit` never downloads them either: on a",
        "  host where the library is installed and its data is not, it raises rather than",
        "  fetching. See `docs/INSTALL.md` in the project for the offline model route.",
        "* **Extras not listed above.** Rebuild with",
        "  `python tools/make_offline_bundle.py --target <name> --extras cli,nlp` to stage them.",
        "* **Anything for a target other than the one named above.**",
        "",
        "## Contents",
        "",
        "```",
    ]
    lines += list(wheel_names)
    lines += [
        "```",
        "",
        "`MANIFEST.json` records the same list with sizes, digests and the exact pip",
        "invocation's platform tags, for tooling that would rather not parse this file.",
        "",
        "Built by `tools/make_offline_bundle.py` from the acronymkit repository.",
    ]
    return "\n".join(lines) + "\n"


def write_archive(source_dir: Path, archive_path: Path) -> int:
    """Zip a staged bundle directory reproducibly.

    Zip rather than tar because ``python -m zipfile -e bundle.zip .`` unpacks it
    on every platform with no tool beyond the interpreter the user is about to
    install into -- which, on a locked-down Windows host, is a materially
    shorter list of prerequisites than ``tar``.

    Entry mtimes are pinned so two builds from the same resolved wheels differ
    only where they genuinely differ. Wheels are stored rather than deflated:
    they are already zip archives of compressed members, so re-compressing costs
    seconds and saves almost nothing.

    Args:
        source_dir: Directory to archive; its own name becomes the single root
            entry inside the archive, so unpacking cannot scatter files.
        archive_path: ``.zip`` to write.

    Returns:
        Size of the written archive in bytes.
    """
    paths = sorted(
        (path for path in source_dir.rglob("*") if path.is_file()),
        key=lambda path: path.relative_to(source_dir).as_posix(),
    )
    with zipfile.ZipFile(archive_path, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in paths:
            arcname = f"{source_dir.name}/{path.relative_to(source_dir).as_posix()}"
            info = zipfile.ZipInfo(arcname, date_time=ZIP_TIMESTAMP)
            info.external_attr = 0o644 << 16
            info.compress_type = (
                zipfile.ZIP_STORED if path.suffix == ".whl" else zipfile.ZIP_DEFLATED
            )
            archive.writestr(info, path.read_bytes())
    return archive_path.stat().st_size


def copy_into(source: Path, destination: Path) -> None:
    """Copy a staged wheel into the bundle, explaining the Windows failure mode.

    Wheel filenames for compiled dependencies are long (a manylinux
    ``pydantic_core`` name is 76 characters) and the bundle directory name adds
    another 45. On Windows without long-path support that clears the 260-
    character limit from inside a moderately deep working directory, and the
    error the API raises for it -- ``[WinError 3] The system cannot find the
    path specified`` -- names the wrong problem.

    Args:
        source: File to copy.
        destination: Full destination path.

    Raises:
        SystemExit: With status 1, carrying a message that names the real cause.
    """
    try:
        shutil.copy2(source, destination)
    except OSError as error:
        sys.stderr.write(f"ERROR: could not write {destination}\n  {error}\n")
        if sys.platform == "win32" and len(str(destination)) > 240:
            sys.stderr.write(
                "  That path is "
                f"{len(str(destination))} characters. Windows refuses paths over 260 "
                "unless long-path support is enabled, so pass --output-dir with a "
                "short path such as C:\\bundles.\n"
            )
        raise SystemExit(1) from error


def build_bundle(
    target: Target,
    project_wheel: Path,
    extras: Sequence[str],
    output_dir: Path,
    keep_tree: bool,
) -> Path:
    """Stage, check and archive one bundle.

    Args:
        target: Target to build for.
        project_wheel: The locally built ``acronymkit`` wheel.
        extras: Extras to stage.
        output_dir: Where the archive (and, with ``keep_tree``, the directory)
            is written.
        keep_tree: Leave the unarchived directory in place for inspection.

    Returns:
        Path to the written archive.

    Raises:
        SystemExit: With status 1 if a download or an offline re-resolution
            fails, or if two staged files share a name but not a digest.
    """
    root = read_wheel(project_wheel)
    version = root.version
    extras_suffix = f"[{','.join(extras)}]" if extras else ""
    root_requirement = f"acronymkit{extras_suffix}=={version}"

    # Sorted numerically so that `--python-version 3.13 --python-version 3.9`
    # names the archive the same way as the other order, rather than claiming to
    # span cp313 to cp39.
    pythons = tuple(
        sorted(target.python_versions, key=lambda value: tuple(int(p) for p in value.split(".")))
    )
    target = Target(
        name=target.name,
        platforms=target.platforms,
        python_versions=pythons,
        summary=target.summary,
        requirement=target.requirement,
    )
    tags = [f"cp{value.replace('.', '')}" for value in pythons]
    span = tags[0] if len(tags) == 1 else f"{tags[0]}-{tags[-1]}"
    stem = f"acronymkit-{version}-offline-{target.name}-{span}"
    bundle_dir = output_dir / stem
    if bundle_dir.exists():
        shutil.rmtree(bundle_dir)
    bundle_dir.mkdir(parents=True)

    print(f"[{target.name}] staging {root_requirement} for CPython {', '.join(pythons)}")
    resolved: Dict[str, Dict[str, str]] = {}
    staged: Dict[str, WheelFile] = {}
    with tempfile.TemporaryDirectory() as scratch:
        for python_version in pythons:
            destination = Path(scratch) / python_version
            destination.mkdir()
            stage_downloads(
                target, python_version, root_requirement, project_wheel.parent, destination
            )
            versions: Dict[str, str] = {}
            for path in sorted(destination.iterdir()):
                if path.suffix != ".whl":
                    # --only-binary=:all: should make this unreachable. If it is
                    # ever reached, an sdist in the bundle would need a compiler
                    # and an index on the target machine, so it is fatal.
                    sys.stderr.write(f"ERROR: {path.name} is not a wheel\n")
                    raise SystemExit(1)
                wheel = read_wheel(path)
                if wheel.name == root.name:
                    # pip may have taken a same-version copy of acronymkit off
                    # an index while resolving the self-referential extra.
                    # Dropping it leaves the locally built wheel as the only
                    # possible source, which removes the ambiguity entirely.
                    continue
                versions[wheel.name] = wheel.version
                previous = staged.get(path.name)
                if previous is not None and previous.digest != wheel.digest:
                    sys.stderr.write(
                        f"ERROR: two different files named {path.name} were downloaded\n"
                    )
                    raise SystemExit(1)
                if previous is None:
                    copy_into(path, bundle_dir / path.name)
                    staged[path.name] = read_wheel(bundle_dir / path.name)
            versions[root.name] = version
            resolved[python_version] = versions
            print(f"[{target.name}]   CPython {python_version}: {len(versions)} distributions")

    copy_into(project_wheel, bundle_dir / project_wheel.name)
    bundled_root = read_wheel(bundle_dir / project_wheel.name)
    staged[project_wheel.name] = bundled_root

    by_key: Dict[Tuple[str, str], List[WheelFile]] = {}
    for wheel in staged.values():
        by_key.setdefault((wheel.name, wheel.version), []).append(wheel)

    write_text(
        bundle_dir / "requirements.txt",
        requirements_text(root_requirement, bundled_root, resolved, by_key),
    )
    write_text(bundle_dir / "verify.py", VERIFY_SCRIPT)

    generated = _datetime.datetime.now(_datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    manifest = {
        "bundle": stem,
        "acronymkit": version,
        "target": target.name,
        "summary": target.summary,
        "requirement": target.requirement,
        "platform_tags": list(target.platforms),
        "python_versions": list(pythons),
        "extras": list(extras),
        "install": "pip install --no-index --find-links=. acronymkit",
        "generated_utc": generated,
        "generator": {
            "tool": "tools/make_offline_bundle.py",
            "pip": pip_version(),
            "built_on": f"{platform.system()} {platform.machine()}",
            "built_with": f"{platform.python_implementation()} {platform.python_version()}",
        },
        "resolved": {key: dict(sorted(value.items())) for key, value in sorted(resolved.items())},
        "files": [
            {
                "name": wheel.path.name,
                "distribution": wheel.name,
                "version": wheel.version,
                "size_bytes": wheel.path.stat().st_size,
                "sha256": wheel.digest,
            }
            for wheel in sorted(staged.values(), key=lambda item: item.path.name)
        ],
    }
    write_text(bundle_dir / "MANIFEST.json", json.dumps(manifest, indent=2, sort_keys=False) + "\n")
    write_text(
        bundle_dir / "README.md",
        readme_text(version, target, extras, root_requirement, sorted(staged), generated),
    )
    # Last, because it hashes everything else in the directory.
    write_text(bundle_dir / "SHA256SUMS", sha256sums_text(bundle_dir))

    running = f"{sys.version_info.major}.{sys.version_info.minor}"
    with tempfile.TemporaryDirectory() as scratch:
        for python_version in pythons:
            # 1. The documented install command, resolved against the bundle and
            #    nothing else.
            resolve_offline(target, python_version, root_requirement, bundle_dir)
            # 2. The same, from the pins and hashes, with this interpreter's
            #    markers already applied (see requirements_text's `only`).
            pinned = Path(scratch) / f"requirements-cp{python_version.replace('.', '')}.txt"
            write_text(
                pinned,
                requirements_text(
                    root_requirement, bundled_root, resolved, by_key, only=python_version
                ),
            )
            resolve_offline(
                target,
                python_version,
                "",
                bundle_dir,
                extra_arguments=("--require-hashes", "-r", str(pinned)),
            )
            note = ""
            if python_version == running:
                # 3. Only when the running interpreter is the one being checked
                #    can the shipped file's markers be exercised, because that is
                #    the only case where pip evaluates them against the version
                #    under test.
                resolve_offline(
                    target,
                    python_version,
                    "",
                    bundle_dir,
                    extra_arguments=(
                        "--require-hashes",
                        "-r",
                        str(bundle_dir / "requirements.txt"),
                    ),
                )
                note = ", markers as shipped"
            print(
                f"[{target.name}]   CPython {python_version}: resolves offline, hashes match{note}"
            )

    archive_path = output_dir / f"{stem}.zip"
    size = write_archive(bundle_dir, archive_path)
    if not keep_tree:
        shutil.rmtree(bundle_dir)
    print(f"[{target.name}] wrote {archive_path.name} ({size:,} B)")
    return archive_path


def parse_extras(value: str) -> Tuple[str, ...]:
    """Turn ``--extras`` into a tuple, treating ``none`` as empty.

    Args:
        value: Comma-separated extras, or ``none``.

    Returns:
        The extras, in the order given, with blanks dropped.
    """
    if value.strip().lower() in {"none", ""}:
        return ()
    return tuple(part.strip() for part in value.split(",") if part.strip())


def main(argv: Optional[Sequence[str]] = None) -> int:
    """Entry point.

    Args:
        argv: Argument list, defaulting to ``sys.argv[1:]``.

    Returns:
        Process exit status.
    """
    parser = argparse.ArgumentParser(
        prog="make_offline_bundle.py",
        description=__doc__.split("\n\n")[0] if __doc__ else None,
    )
    parser.add_argument(
        "--target",
        action="append",
        default=None,
        metavar="NAME",
        help="target to build for; repeatable. 'host' builds for this machine.",
    )
    parser.add_argument("--all", action="store_true", help="build every registry target")
    parser.add_argument("--list-targets", action="store_true", help="print the registry and exit")
    parser.add_argument(
        "--python-version",
        action="append",
        default=None,
        metavar="X.Y",
        help="override the interpreter list for every requested target; repeatable",
    )
    parser.add_argument(
        "--extras",
        default=",".join(DEFAULT_EXTRAS),
        metavar="LIST",
        help=f"comma-separated extras to stage, or 'none' (default: {','.join(DEFAULT_EXTRAS)})",
    )
    parser.add_argument(
        "--wheel",
        type=Path,
        default=None,
        metavar="PATH",
        help="use this prebuilt acronymkit wheel instead of building one",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        metavar="DIR",
        help=f"where bundles are written (default: {DEFAULT_OUTPUT_DIR})",
    )
    parser.add_argument(
        "--keep-tree",
        action="store_true",
        help="leave the unarchived bundle directory beside the archive",
    )
    arguments = parser.parse_args(argv)

    if arguments.list_targets:
        print(f"{'target':<20} {'interpreters':<26} platform")
        for target in TARGETS.values():
            pythons = ", ".join(target.python_versions)
            print(f"{target.name:<20} {pythons:<26} {target.summary}")
        print(f"{'host':<20} {'this interpreter only':<26} this machine, no --platform override")
        return 0

    if arguments.all and arguments.target:
        parser.error("--all and --target are mutually exclusive")
    if not arguments.all and not arguments.target:
        parser.error("pass --target NAME (repeatable), --all, or --list-targets")

    targets: List[Target] = []
    if arguments.all:
        targets = list(TARGETS.values())
    else:
        for name in arguments.target:
            if name == "host":
                targets.append(host_target())
            elif name in TARGETS:
                targets.append(TARGETS[name])
            else:
                parser.error(f"unknown target {name!r}; try --list-targets")

    if arguments.python_version:
        overrides = tuple(arguments.python_version)
        for target in targets:
            # `host` downloads with no --python-version, so every requested
            # version would resolve to the running interpreter's wheels. The
            # bundle would then claim to serve interpreters whose wheels it does
            # not contain, which is the one failure mode this script exists to
            # prevent. Refuse rather than produce it.
            if not target.platforms:
                parser.error(
                    "--python-version cannot be used with --target host: that mode takes its "
                    "tags from the running interpreter, so it can only ever serve "
                    f"CPython {target.python_versions[0]}. Run it under the interpreter you "
                    "want served, or name a platform target."
                )
        targets = [
            Target(
                name=target.name,
                platforms=target.platforms,
                python_versions=overrides,
                summary=target.summary,
                requirement=target.requirement,
            )
            for target in targets
        ]

    extras = parse_extras(arguments.extras)
    output_dir: Path = arguments.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    if arguments.wheel is not None:
        project_wheel = arguments.wheel.resolve()
        if not project_wheel.is_file():
            sys.stderr.write(f"ERROR: no such wheel: {project_wheel}\n")
            return 2
    else:
        print("building the acronymkit wheel")
        project_wheel = build_project_wheel(output_dir)
    print(f"using {project_wheel.name}")

    written = [
        build_bundle(target, project_wheel, extras, output_dir, arguments.keep_tree)
        for target in targets
    ]
    print(f"\n{len(written)} bundle(s) in {output_dir}:")
    for path in written:
        print(f"  {path.name}  {path.stat().st_size:,} B")
    return 0


if __name__ == "__main__":
    sys.exit(main())
