"""Tests for :mod:`acronymkit.diagnostics`, the machine-readable capability report.

The point of :func:`acronymkit.diagnostics.capabilities` is that somebody else's
CI asserts on it. That makes three properties load-bearing, and each has its own
section below:

* **The shape is stable and serialisable.** A report that cannot survive
  ``json.dumps`` cannot be pinned in another project's fixture file, and a key
  that disappears breaks an assertion written against a previous release. The
  shape tests use superset comparisons, matching the contract the module
  documents -- fields may be added, existing ones may not change meaning.
* **The digests describe the files that actually shipped.** They are recomputed
  here straight from the resource directory with :mod:`hashlib`, not read back
  through the same code path that produced them, so a bug in
  ``read_binary_resource`` cannot make the report agree with itself.
* **Measuring the installation must not change it.** ``_is_importable`` uses
  :func:`importlib.util.find_spec`, which locates a module without executing it.
  If that ever became a real import, a Tier 0 process would start paying for
  spaCy the moment it asked what it could do. Checked in-process as a
  ``sys.modules`` delta and again in a fresh interpreter, because several other
  tests in this session import optional backends on purpose.

The file is pure ASCII, as is the report it checks.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

import acronymkit
from acronymkit import diagnostics as diagnostics_module
from acronymkit import resources as resources_module
from acronymkit.diagnostics import (
    DATA_PACK_GROUP,
    OFFLINE_ENV_VAR,
    capabilities,
    format_report,
    offline_requested,
    pydantic_plugins,
)
from acronymkit.resources import bundled_resources, read_binary_resource
from conftest import REPO_ROOT

#: Directory the bundled data files live in. Taken from the module's own
#: ``__file__`` rather than from ``resource_path()``, so that the digest tests
#: below do not read the resources through the machinery they are checking.
RESOURCE_DIRECTORY = Path(resources_module.__file__).resolve().parent

#: Keys the module documents at the top level of a report. The assertion is
#: ``set(report) >= DOCUMENTED_TOP_LEVEL_KEYS`` -- the report must carry at
#: least these -- because the docstring promises that fields may be added under
#: a patch release but that an existing one will not vanish or change meaning.
#: That check fails on a removal or a rename and stays quiet on an addition.
DOCUMENTED_TOP_LEVEL_KEYS = {
    "acronymkit_version",
    "python_version",
    "python_implementation",
    "platform",
    "offline",
    "network",
    "tiers",
    "backends",
    "data_packs",
    "resources",
}

#: Optional distributions the report is expected to describe.
DOCUMENTED_BACKENDS = {"click", "spacy", "nltk", "transformers", "onnxruntime", "jsonschema"}

#: Backends whose presence in ``sys.modules`` would prove ``_is_importable``
#: executed the module rather than merely locating it.
WATCHED_BACKENDS = ("spacy", "nltk", "click", "transformers", "onnxruntime")

RESOURCE_NAMES = list(bundled_resources())


def report_line(text: str, label: str) -> str:
    """Return the one line of a rendered report containing ``label``.

    Used instead of asserting a fully aligned literal, so that re-tabulating a
    column is not a test failure while the value in it still is.

    Args:
        text: A rendered report.
        label: Substring identifying the row.

    Returns:
        The matching line, stripped of trailing whitespace.

    Raises:
        AssertionError: If the label appears on no line, or on more than one.
    """
    matches = [line.rstrip() for line in text.splitlines() if label in line]
    assert len(matches) == 1, f"{label!r} matched {len(matches)} lines"
    return matches[0]


@pytest.fixture(autouse=True)
def _neutral_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    """Run every test with the two environment variables this module reads unset.

    Otherwise a developer who exports ``ACRONYMKIT_OFFLINE=1`` in their shell to
    reproduce a bug gets a red suite that has nothing to do with the bug.
    """
    monkeypatch.delenv(OFFLINE_ENV_VAR, raising=False)
    monkeypatch.delenv("PYDANTIC_DISABLE_PLUGINS", raising=False)


def run_in_subprocess(script: str, tmp_path: Path, name: str) -> subprocess.CompletedProcess:
    """Execute ``script`` in a fresh interpreter and return the completed process.

    A twin of the helper in ``test_package.py``. Kept local so that this module
    has no test-to-test import dependency.

    Args:
        script: Python source to run.
        tmp_path: Directory the script file is written to.
        name: File name for the script, for readable failure output.

    Returns:
        The :class:`subprocess.CompletedProcess`, never checked for you.
    """
    path = tmp_path / name
    path.write_text(script, encoding="utf-8")
    environment = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    environment.pop(OFFLINE_ENV_VAR, None)
    return subprocess.run(
        [sys.executable, str(path)],
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
        env=environment,
        check=False,
    )


# ---------------------------------------------------------------------------
# Report shape
# ---------------------------------------------------------------------------
def test_capabilities_reports_every_documented_key() -> None:
    """No documented top-level key may disappear; new ones are permitted."""
    report = capabilities()

    assert set(report) >= DOCUMENTED_TOP_LEVEL_KEYS
    assert set(report["offline"]) >= {"env_var", "requested_by_environment"}
    assert set(report["network"]) >= {
        "performs_network_io",
        "downloads_models",
        "telemetry",
        "third_party_import_hooks",
    }
    assert set(report["network"]["third_party_import_hooks"]) >= {
        "pydantic_entry_point_plugins",
        "note",
    }
    assert set(report["tiers"]) >= {"zero_dependency", "standard", "statistical_nlp", "neural"}
    assert set(report["resources"]) >= {"count", "names", "digests"}


def test_capabilities_round_trips_through_json() -> None:
    """The report is a fixture other projects pin, so it must be plain JSON.

    Equality after a ``dumps``/``loads`` cycle is stronger than "``dumps`` did
    not raise": it also rules out a tuple or a set that survives encoding but
    comes back as a different type and breaks the caller's comparison.
    """
    report = capabilities()

    assert json.loads(json.dumps(report)) == report


def test_capabilities_identifies_this_installation() -> None:
    """The version and interpreter fields describe the process that produced them."""
    report = capabilities(include_checksums=False)

    assert report["acronymkit_version"] == acronymkit.__version__
    assert report["python_version"] == ".".join(str(part) for part in sys.version_info[:3])
    assert report["python_implementation"] in {"CPython", "PyPy", "Jython", "IronPython"}
    assert report["platform"] == sys.platform


def test_capabilities_states_that_no_network_io_happens() -> None:
    """The three network claims are ``False``, and stated as facts rather than guesses.

    ``performs_network_io`` is the headline of the whole report: an air-gapped
    operator reads this one field. It is asserted here as an exact ``False``
    rather than a falsey value so that ``None`` -- "we did not check" -- can
    never be mistaken for "no".
    """
    network = capabilities(include_checksums=False)["network"]

    assert network["performs_network_io"] is False
    assert network["downloads_models"] is False
    assert network["telemetry"] is False


def test_capabilities_reports_third_party_import_hooks() -> None:
    """The one thing the package cannot prevent is disclosed rather than omitted."""
    hooks = capabilities(include_checksums=False)["network"]["third_party_import_hooks"]

    assert hooks["pydantic_entry_point_plugins"] == list(pydantic_plugins())
    assert isinstance(hooks["pydantic_entry_point_plugins"], list)
    assert "PYDANTIC_DISABLE_PLUGINS" in hooks["note"]


def test_capabilities_reports_sane_tiers() -> None:
    """Tier 0 is always available, Tier 2 never is, and Tier 1 follows the backends."""
    report = capabilities(include_checksums=False)
    tiers = report["tiers"]
    backends = report["backends"]

    assert all(isinstance(value, bool) for value in tiers.values())
    assert tiers["zero_dependency"] is True
    assert tiers["neural"] is False, "the neural tier is not implemented in this release"
    expected = backends["spacy"]["importable"] or backends["nltk"]["importable"]
    assert tiers["statistical_nlp"] is expected
    assert tiers["standard"] is expected


def test_capabilities_describes_every_optional_backend() -> None:
    """Each optional distribution gets an importability flag and a purpose."""
    backends = capabilities(include_checksums=False)["backends"]

    assert set(backends) >= DOCUMENTED_BACKENDS
    for name, entry in backends.items():
        assert isinstance(entry["importable"], bool), name
        assert isinstance(entry["provides"], str) and entry["provides"], name


@pytest.mark.parametrize("name", sorted(DOCUMENTED_BACKENDS))
def test_backend_importability_matches_this_interpreter(name: str) -> None:
    """The report tells the truth about what is on this machine's import path."""
    expected = importlib.util.find_spec(name) is not None

    assert capabilities(include_checksums=False)["backends"][name]["importable"] is expected


def test_capabilities_reports_the_data_pack_group_as_empty() -> None:
    """Nothing ships a data pack yet, and the report must not invent one."""
    assert DATA_PACK_GROUP == "acronymkit.data"
    assert capabilities(include_checksums=False)["data_packs"] == []


def test_capabilities_resources_section_matches_the_bundled_inventory() -> None:
    """The resource listing is the inventory, not a hand-maintained copy of it."""
    resources = capabilities(include_checksums=False)["resources"]

    assert resources["names"] == list(bundled_resources())
    assert resources["count"] == len(resources["names"])
    assert resources["names"] == sorted(resources["names"])
    assert resources["names"], "the distribution ships data files"


def test_capabilities_names_the_offline_environment_variable() -> None:
    """The report says which variable to set, so nobody has to grep for it."""
    offline = capabilities(include_checksums=False)["offline"]

    assert OFFLINE_ENV_VAR == "ACRONYMKIT_OFFLINE"
    assert offline["env_var"] == OFFLINE_ENV_VAR
    assert offline["requested_by_environment"] is False


def test_capabilities_reflects_an_offline_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    """Setting the variable is visible in the report, which is how it is audited."""
    monkeypatch.setenv(OFFLINE_ENV_VAR, "1")

    assert capabilities(include_checksums=False)["offline"]["requested_by_environment"] is True


# ---------------------------------------------------------------------------
# Checksums
# ---------------------------------------------------------------------------
def test_include_checksums_false_omits_the_digests() -> None:
    """Turning checksums off drops the digests and changes nothing else."""
    cheap = capabilities(include_checksums=False)
    full = capabilities(include_checksums=True)

    assert "digests" not in cheap["resources"]
    assert "digests" in full["resources"]
    assert cheap["resources"]["names"] == full["resources"]["names"]
    assert {key: value for key, value in full.items() if key != "resources"} == {
        key: value for key, value in cheap.items() if key != "resources"
    }


def test_include_checksums_false_reads_no_resource_bytes(monkeypatch: pytest.MonkeyPatch) -> None:
    """The cheap report is cheap because it does no hashing, not because it is quick.

    Asserted as work avoided rather than as a wall-clock comparison. A timing
    assertion here would be a claim about somebody else's CPU, and it would be
    a dishonest one besides: ``_read_bytes`` is memoised, so on the second call
    the expensive version is nearly free and the test would pass for the wrong
    reason. Counting the reads pins the property the flag actually has.
    """
    reads: list[str] = []

    def counting_reader(name: str) -> bytes:
        reads.append(name)
        return read_binary_resource(name)

    monkeypatch.setattr(diagnostics_module, "read_binary_resource", counting_reader)

    capabilities(include_checksums=False)
    assert reads == []

    capabilities(include_checksums=True)
    assert sorted(reads) == sorted(bundled_resources())


@pytest.mark.parametrize("name", RESOURCE_NAMES)
def test_digest_is_a_lowercase_sha256_of_the_shipped_bytes(name: str) -> None:
    """Every bundled file gets a 64-hex SHA-256 and a byte count that agree with it."""
    digest = capabilities()["resources"]["digests"][name]
    payload = read_binary_resource(name)

    assert digest["bytes"] == len(payload)
    assert len(digest["sha256"]) == 64
    assert set(digest["sha256"]) <= set("0123456789abcdef")
    assert digest["sha256"] == hashlib.sha256(payload).hexdigest()


@pytest.mark.parametrize("name", RESOURCE_NAMES)
def test_digest_matches_the_file_on_disk(name: str) -> None:
    """The digest describes the shipped file, computed without the resource loader.

    Reading the bytes straight off the filesystem is what makes this a check
    rather than a tautology: if ``read_binary_resource`` ever started decoding,
    normalising newlines or decompressing, the report would still agree with
    itself and only this test would notice. It is also the comparison a
    security scanner makes -- these are the bytes a wheel's ``RECORD`` hashes.
    """
    expected = hashlib.sha256((RESOURCE_DIRECTORY / name).read_bytes()).hexdigest()

    assert capabilities()["resources"]["digests"][name]["sha256"] == expected


@pytest.mark.parametrize("name", RESOURCE_NAMES)
def test_read_binary_resource_returns_the_raw_shipped_bytes(name: str) -> None:
    """``read_binary_resource`` decodes nothing, so a checksum here is comparable to ``pip``'s.

    The stronger half of this property -- that a ``.gz`` resource comes back
    still compressed -- cannot be exercised against the real inventory, because
    this distribution currently bundles no ``.gz`` file (the resource directory
    holds one schema, one lexicon, one n-gram model and four stop-word lists,
    all uncompressed). Rather than plant a fake one, the byte-for-byte identity
    below is asserted for every file that does ship: no decoding, no newline
    translation, no BOM stripping. ``tests/test_resources.py`` covers the gzip
    path on the *text* reader, where a synthetic resource is already the
    established technique.
    """
    assert not name.endswith(".gz"), "a .gz resource now ships; assert it stays compressed here"
    assert read_binary_resource(name) == (RESOURCE_DIRECTORY / name).read_bytes()


def test_bundled_resources_excludes_the_package_machinery() -> None:
    """``bundled_resources()`` lists shipped content, not the module that serves it."""
    names = bundled_resources()

    assert "__init__.py" not in names
    assert "__pycache__" not in names
    assert not any(name.endswith((".py", ".pyc")) for name in names)
    assert (RESOURCE_DIRECTORY / "__init__.py").is_file(), "the exclusion is not vacuous"
    assert names == tuple(sorted(names))


# ---------------------------------------------------------------------------
# format_report
# ---------------------------------------------------------------------------
def test_format_report_is_pure_ascii() -> None:
    """The report must encode as ASCII, because it is printed into container logs.

    A ``UnicodeEncodeError`` raised while *printing* a capability report is the
    worst possible failure mode this module has: the operator is running it
    precisely because something is already wrong, and the diagnostic itself
    would be what crashes. Windows consoles and ``LANG=C`` containers both make
    that a real possibility for any box-drawing character or fancy dash, so no
    non-ASCII character may appear.
    """
    report = format_report()

    report.encode("ascii")  # raises UnicodeEncodeError if anything non-ASCII crept in
    assert report.strip()


def test_format_report_renders_the_report_it_is_given() -> None:
    """Passing a report renders that report rather than generating a fresh one."""
    data = capabilities()
    data["acronymkit_version"] = "0.0.0-sentinel"

    text = format_report(data)

    assert text.splitlines()[0].startswith("acronymkit 0.0.0-sentinel on Python ")


def test_format_report_defaults_to_a_freshly_generated_report() -> None:
    """Called with no argument it describes this installation."""
    text = format_report()

    assert text.splitlines()[0].startswith(f"acronymkit {acronymkit.__version__} on Python ")
    assert report_line(text, "performs network I/O").endswith(": False")
    assert report_line(text, "downloads models").endswith(": False")
    assert report_line(text, "telemetry").endswith(": False")
    for name in bundled_resources():
        assert name in text


def test_format_report_survives_a_report_without_digests() -> None:
    """The cheap report renders too: resource lines degrade to bare names."""
    text = format_report(capabilities(include_checksums=False))

    text.encode("ascii")
    assert "sha256:" not in text
    for name in bundled_resources():
        assert name in text


def test_format_report_says_none_when_nothing_is_installed() -> None:
    """An empty list reads as ``none`` rather than as a blank column.

    A blank value in a log line is ambiguous -- it reads as "the field is
    missing" as easily as "the list is empty" -- and this is the field an
    auditor scans for.
    """
    text = format_report(capabilities(include_checksums=False))

    assert report_line(text, "pydantic plugins").endswith(": none")
    assert report_line(text, "data packs").endswith(": none")


# ---------------------------------------------------------------------------
# Measuring must not perturb: _is_importable executes nothing
# ---------------------------------------------------------------------------
def test_capabilities_does_not_import_the_backends_it_reports_on() -> None:
    """Asking what is available must not make it resident.

    This is the Tier 0 purity property at unit level. It is expressed as a
    delta because other tests in this session import ``click`` and probe for
    NLTK on purpose, so an absolute ``"nltk" not in sys.modules`` would fail
    for a reason that has nothing to do with this module. The absolute form is
    pinned in a fresh interpreter by the next test.
    """
    absent_before = {name for name in WATCHED_BACKENDS if name not in sys.modules}

    capabilities()

    newly_imported = {name for name in absent_before if name in sys.modules}
    assert newly_imported == set(), f"capabilities() executed {sorted(newly_imported)}"


def test_capabilities_stays_tier_zero_pure_in_a_fresh_interpreter(tmp_path: Path) -> None:
    """In a clean process, generating and rendering a report imports nothing optional."""
    script = (
        "import json\n"
        "import sys\n"
        f"sys.path.insert(0, {str(REPO_ROOT / 'src')!r})\n"
        "from acronymkit import capabilities, format_report\n"
        "format_report(capabilities())\n"
        f"watched = {list(WATCHED_BACKENDS)!r}\n"
        "print(json.dumps(sorted(n for n in watched if n in sys.modules)))\n"
    )

    completed = run_in_subprocess(script, tmp_path, "capabilities_purity.py")

    assert completed.returncode == 0, completed.stderr
    leaked = json.loads(completed.stdout.strip().splitlines()[-1])
    assert leaked == [], f"capabilities() pulled in {leaked}"


# ---------------------------------------------------------------------------
# offline_requested
# ---------------------------------------------------------------------------
def test_offline_requested_is_false_when_the_variable_is_unset() -> None:
    """An absent variable means "not requested", which is the shipped default."""
    assert OFFLINE_ENV_VAR not in os.environ
    assert offline_requested() is False


@pytest.mark.parametrize(
    "value",
    ["1", "true", "yes", "on", "TRUE", "Yes", "ON", "True", " 1 ", "\ttrue\n", "  on  ", "yes "],
    ids=repr,
)
def test_offline_requested_accepts_truthy_values(
    monkeypatch: pytest.MonkeyPatch, value: str
) -> None:
    """Case and surrounding whitespace are forgiven: containers set these by hand.

    The padded values are the ones that earn their place. A variable written
    into a Compose file or a Dockerfile ``ENV`` line picks up a trailing space
    often enough that dropping the ``.strip()`` would look like a harmless
    tidy-up, and the failure that causes is silent: the operator asked for
    offline mode, the value is not recognised, and the process runs on without
    it.
    """
    monkeypatch.setenv(OFFLINE_ENV_VAR, value)

    assert offline_requested() is True


@pytest.mark.parametrize(
    "value",
    ["", " ", "\t", "0", "false", "no", "off", "FALSE", "None", "null", "2", "enabled"],
    ids=repr,
)
def test_offline_requested_rejects_everything_else(
    monkeypatch: pytest.MonkeyPatch, value: str
) -> None:
    """Only the four documented words count; everything else means "not requested".

    The wording matters more than it looks. This variable can only tighten, so
    an unrecognised value such as ``"enabled"`` or ``"2"`` is not read as "off"
    either -- it says nothing, and the flag stays wherever the caller's code put
    it. ``"0"`` and ``"false"`` are in the list for the same reason: they read
    like an instruction to disable offline mode, and this function must not
    honour one. That the whole set comes back ``False`` is asserted literally
    rather than recomputed from the value, so the test states the expectation
    instead of restating the implementation.
    """
    monkeypatch.setenv(OFFLINE_ENV_VAR, value)

    assert offline_requested() is False


# ---------------------------------------------------------------------------
# pydantic_plugins
# ---------------------------------------------------------------------------
def test_pydantic_plugins_is_empty_on_a_clean_installation() -> None:
    """Nothing in this project's dependency tree advertises the ``pydantic`` group."""
    plugins = pydantic_plugins()

    assert plugins == ()
    assert isinstance(plugins, tuple)


@pytest.mark.parametrize("value", ["__all__", "1", "true"], ids=repr)
def test_pydantic_plugins_is_empty_when_the_mechanism_is_disabled(
    monkeypatch: pytest.MonkeyPatch, value: str
) -> None:
    """With ``PYDANTIC_DISABLE_PLUGINS`` set, no plugin can run, so none is reported.

    Reporting a plugin that pydantic has been told to ignore would make strict
    offline mode refuse to start for a risk that is already neutralised.
    """
    monkeypatch.setenv("PYDANTIC_DISABLE_PLUGINS", value)

    assert pydantic_plugins() == ()


# ---------------------------------------------------------------------------
# Public re-exports
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("name", ["capabilities", "format_report"])
def test_top_level_re_exports_are_the_diagnostics_functions(name: str) -> None:
    """``acronymkit.capabilities()`` is the documented entry point, not a copy."""
    assert getattr(acronymkit, name) is getattr(diagnostics_module, name)


def test_diagnostics_is_importable_without_the_rest_of_the_package(tmp_path: Path) -> None:
    """The module is stdlib-only so that it still works on a broken installation.

    A capability report whose own import fails on the machine being diagnosed
    is worthless, so ``acronymkit.diagnostics`` imports nothing beyond the
    standard library and ``acronymkit.resources`` -- in particular not
    ``pydantic``, which is the one hard runtime dependency and therefore the one
    that can be missing while everything else is present.
    """
    script = (
        "import json\n"
        "import sys\n"
        f"sys.path.insert(0, {str(REPO_ROOT / 'src')!r})\n"
        "import acronymkit.diagnostics as diagnostics\n"
        "diagnostics.capabilities(include_checksums=False)\n"
        "print(json.dumps('pydantic' in sys.modules))\n"
    )

    completed = run_in_subprocess(script, tmp_path, "diagnostics_stdlib_only.py")

    assert completed.returncode == 0, completed.stderr
    assert json.loads(completed.stdout.strip().splitlines()[-1]) is False


# ---------------------------------------------------------------------------
# Report stability
# ---------------------------------------------------------------------------
def test_capabilities_hands_out_a_private_document() -> None:
    """Callers may edit a report without corrupting the next one."""
    first: dict[str, Any] = capabilities(include_checksums=False)
    first["network"]["performs_network_io"] = True

    assert capabilities(include_checksums=False)["network"]["performs_network_io"] is False


def test_capabilities_is_deterministic_within_a_process() -> None:
    """Two calls with the same environment produce the same document."""
    assert capabilities() == capabilities()
