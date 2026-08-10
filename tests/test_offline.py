"""Tests for strict offline mode: ``Config.offline`` and ``ACRONYMKIT_OFFLINE``.

Offline mode is not a switch that disables network code, because there is no
network code to disable -- ``acronymkit`` authors no reachable socket path on
any tier. It is a *refusal*: at construction time, the library declines to run
under a promise it can see it cannot keep. Three things are therefore worth
pinning, and they are what this module is organised around.

**The environment can only tighten.** ``ACRONYMKIT_OFFLINE`` turns offline mode
on for every :class:`~acronymkit.config.Config` in the process and there is
deliberately no value that turns it off again. That asymmetry is the security
property: a container-wide variable that could *relax* a posture set in code
would be a worse bug than the one offline mode solves, and it is exactly the
kind of thing that survives review because the happy path still works. It is
asserted here against a spread of values rather than one, because "there is no
such value" is the claim.

**The refusals are the two things this process can see.** ``EngineTier.NEURAL``
needs a model that is not in the wheel, and a third-party ``pydantic``
entry-point plugin is foreign code that ``pydantic`` imports while building the
``Config`` itself. The second is detection, not prevention -- by the time the
check runs the plugin has already been imported -- and the subprocess test at
the bottom of this file demonstrates precisely that, because it depends on
installed distribution metadata and cannot be simulated in process.

**Nothing else changes.** An engine built from an offline config must produce
byte-identical results to one built from a default config. A "safe mode" that
quietly degrades output is a different product, and the equality assertions
below are what stop offline mode from becoming one.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

from acronymkit import AcronymEngine, Config
from acronymkit.diagnostics import OFFLINE_ENV_VAR
from acronymkit.enums import EngineTier
from acronymkit.exceptions import AcronymKitError, ConfigurationError, OfflineError
from conftest import REPO_ROOT

#: Phrases used for the "offline changes nothing" equivalence checks. Three is
#: enough: the property is about the configuration flag, not about coverage of
#: the generator, which ``test_generator.py`` owns.
EQUIVALENCE_PHRASES = [
    "Application Programming Interface",
    "Self Contained Underwater Breathing Apparatus",
    "Light Amplification by Stimulated Emission of Radiation",
]

#: Every value the environment variable is plausibly given, truthy and not.
#: Used to assert that none of them can clear a flag set in code.
ENVIRONMENT_VALUES = [
    "1",
    "0",
    "true",
    "false",
    "TRUE",
    "FALSE",
    "yes",
    "no",
    "on",
    "off",
    "",
    " ",
    "None",
    "null",
    "-1",
    "disabled",
]

#: Tiers offline mode has no reason to refuse: all of them run from the wheel.
OFFLINE_SAFE_TIERS = [
    EngineTier.ZERO_DEPENDENCY,
    EngineTier.STATISTICAL_NLP,
    EngineTier.HYBRID_NLP,
    EngineTier.AUTO,
]


@pytest.fixture(autouse=True)
def _neutral_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    """Start every test with both relevant environment variables unset.

    ``Config`` folds ``ACRONYMKIT_OFFLINE`` in at construction, so a developer
    who exports it in their shell would otherwise see the default-value tests
    fail for a reason unrelated to the code.
    """
    monkeypatch.delenv(OFFLINE_ENV_VAR, raising=False)
    monkeypatch.delenv("PYDANTIC_DISABLE_PLUGINS", raising=False)


def comparable(payload: dict[str, Any]) -> dict[str, Any]:
    """Return ``payload`` with the one non-deterministic field neutralised.

    ``metadata.execution_time_ms`` is wall-clock and differs between any two
    runs; every other field in a result is a pure function of the input and the
    configuration. Zeroing it is what lets the offline/default comparison be an
    equality rather than a field-by-field spot check.

    Args:
        payload: A result's ``to_dict()`` output. Mutated in place and returned.

    Returns:
        The same dictionary, with the timing field set to ``0.0``.
    """
    payload["metadata"]["execution_time_ms"] = 0.0
    return payload


# ---------------------------------------------------------------------------
# The flag itself
# ---------------------------------------------------------------------------
def test_offline_is_off_by_default() -> None:
    """Offline mode is opt-in: a stock ``Config`` does not refuse anything."""
    assert Config().offline is False


def test_offline_can_be_requested_in_code() -> None:
    """The flag is an ordinary field, so a library caller need not touch the environment."""
    assert Config(offline=True).offline is True


@pytest.mark.parametrize("value", ["1", "true", "yes", "on", "TRUE", " On "], ids=repr)
def test_the_environment_turns_offline_on(monkeypatch: pytest.MonkeyPatch, value: str) -> None:
    """A truthy variable makes every ``Config`` in the process offline."""
    monkeypatch.setenv(OFFLINE_ENV_VAR, value)

    assert Config().offline is True


@pytest.mark.parametrize("value", ["0", "false", "no", "off", "", " ", "maybe"], ids=repr)
def test_an_unrecognised_environment_value_is_not_a_request(
    monkeypatch: pytest.MonkeyPatch, value: str
) -> None:
    """Anything that is not one of the four documented words means "not requested"."""
    monkeypatch.setenv(OFFLINE_ENV_VAR, value)

    assert Config().offline is False


def test_the_environment_overrides_an_explicit_false(monkeypatch: pytest.MonkeyPatch) -> None:
    """``offline=False`` in code does not win against a container that asked for offline.

    The variable is a deployment-wide floor, so code that was written before
    the operator made that decision cannot opt out of it by accident.
    """
    monkeypatch.setenv(OFFLINE_ENV_VAR, "1")

    assert Config(offline=False).offline is True
    assert Config().offline is True


@pytest.mark.parametrize("value", ENVIRONMENT_VALUES, ids=repr)
def test_no_environment_value_can_turn_offline_off(
    monkeypatch: pytest.MonkeyPatch, value: str
) -> None:
    """**The security property.** Once code asks for offline, the environment cannot relax it.

    The flag is the logical OR of the two sources, so this holds by
    construction -- but "by construction" is what an accidental
    ``data["offline"] = offline_requested()`` would also look like at a glance,
    and that version silently downgrades every caller that set the flag itself.
    Asserted across the whole spread of plausible values because the claim is
    that *no* value works, not that the obvious ones do not.
    """
    monkeypatch.setenv(OFFLINE_ENV_VAR, value)

    assert Config(offline=True).offline is True


def test_deleting_the_variable_does_not_reopen_an_offline_config(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The flag is resolved at construction, so a later unset cannot loosen an object."""
    monkeypatch.setenv(OFFLINE_ENV_VAR, "1")
    config = Config()

    monkeypatch.delenv(OFFLINE_ENV_VAR)

    assert config.offline is True


def test_offline_may_be_turned_off_in_code_when_the_environment_is_silent() -> None:
    """The one-way ratchet is the *environment*, not the field.

    A caller that set ``offline=True`` may unset it again through
    ``with_overrides``; that is an explicit decision in code, made by the same
    party that made the first one. Worth pinning so the boundary between "the
    environment cannot relax this" and "the field is immutable" is written down
    rather than inferred.
    """
    assert Config(offline=True).with_overrides(offline=False).offline is False


def test_a_copy_cannot_clear_offline_while_the_environment_asks_for_it(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The ratchet holds through the copy constructors, which is where it would be lost.

    ``with_overrides`` and the presets rebuild through ``Config(**...)``, so the
    environment is folded in again on the copy. That is a consequence of *how*
    the copy is made rather than something the offline code arranged, and it
    would disappear the day ``with_overrides`` switched to
    ``model_copy(update=...)`` for speed -- a change that would look like a pure
    optimisation and would quietly hand every caller a way to opt out of a
    container-wide posture.
    """
    monkeypatch.setenv(OFFLINE_ENV_VAR, "1")

    assert Config(offline=True).with_overrides(offline=False).offline is True
    assert Config.fast(offline=False).offline is True


# ---------------------------------------------------------------------------
# Refusals
# ---------------------------------------------------------------------------
def test_offline_refuses_the_neural_tier() -> None:
    """The neural tier needs a model the wheel does not carry, so offline refuses it."""
    with pytest.raises(OfflineError) as excinfo:
        Config(offline=True, engine_tier=EngineTier.NEURAL)

    assert "NEURAL" in str(excinfo.value)


def test_the_offline_refusal_honours_the_single_except_contract() -> None:
    """One ``except AcronymKitError`` catches it, and so does ``except ValueError``.

    ``OfflineError`` is raised where a configuration is rejected, so it is a
    ``ConfigurationError`` and therefore a ``ValueError``; integrators who
    installed a single boundary clause against ``AcronymKitError`` must not
    have to add a second one for this release.
    """
    with pytest.raises(OfflineError) as excinfo:
        Config(offline=True, engine_tier=EngineTier.NEURAL)

    assert isinstance(excinfo.value, ConfigurationError)
    assert isinstance(excinfo.value, ValueError)
    assert isinstance(excinfo.value, AcronymKitError)


def test_the_offline_refusal_carries_a_reason_and_a_remedy() -> None:
    """The exception is machine-readable: what failed, and what to do instead.

    An operator reading this at start-up in a container log needs the second
    half. A message that only says "cannot be honoured" moves the problem to a
    support ticket.
    """
    with pytest.raises(OfflineError) as excinfo:
        Config(offline=True, engine_tier=EngineTier.NEURAL)
    error = excinfo.value

    assert error.reason and isinstance(error.reason, str)
    assert error.remedy and isinstance(error.remedy, str)
    assert error.reason in str(error)
    assert error.remedy in str(error)
    assert "ZERO_DEPENDENCY" in error.remedy


def test_the_environment_alone_is_enough_to_trigger_the_refusal(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The container's variable reaches the enforcement, not merely the flag.

    This is the deployment that matters: nobody edited the code, the operator
    set one variable, and the process refuses at start-up rather than emitting
    quietly degraded output for a week.
    """
    monkeypatch.setenv(OFFLINE_ENV_VAR, "1")

    with pytest.raises(OfflineError):
        Config(engine_tier=EngineTier.NEURAL)


def test_the_neural_tier_is_still_accepted_when_offline_is_not_requested() -> None:
    """Without offline mode the neural tier is a degradation, not an error.

    The contrast matters: offline mode moves an existing runtime degradation
    forward to construction. It does not invent a new prohibition, and this
    test is what would fail if the check leaked out of the ``if self.offline``
    branch.
    """
    assert Config(engine_tier=EngineTier.NEURAL).engine_tier is EngineTier.NEURAL


@pytest.mark.parametrize("tier", OFFLINE_SAFE_TIERS, ids=lambda tier: tier.value)
def test_offline_accepts_every_tier_that_runs_from_the_wheel(tier: EngineTier) -> None:
    """Only the neural tier is refused; the rest need nothing that is not shipped."""
    config = Config(offline=True, engine_tier=tier)

    assert config.offline is True
    assert config.engine_tier is tier


# ---------------------------------------------------------------------------
# Round trips
# ---------------------------------------------------------------------------
def test_offline_survives_with_overrides() -> None:
    """A derived config inherits the posture; it is not silently dropped on copy."""
    derived = Config(offline=True).with_overrides(max_candidates=3, case_style="lower")

    assert derived.offline is True
    assert derived.max_candidates == 3


def test_offline_survives_a_model_dump_round_trip() -> None:
    """``Config(**config.model_dump())`` behaves identically, offline included.

    Folding the environment in at construction rather than at each use site is
    what makes this true: ``config.offline`` is the *effective* value, so a
    config serialised in an offline container and rebuilt from that dump is
    still offline even if the rebuild happens somewhere the variable is unset.
    """
    original = Config(offline=True, max_candidates=4)

    dumped = original.model_dump()
    rebuilt = Config(**dumped)

    assert dumped["offline"] is True
    assert rebuilt.offline is True
    assert rebuilt == original


def test_an_offline_dump_stays_offline_where_the_variable_is_unset() -> None:
    """The dump carries the posture, not a reference to the environment that set it."""
    assert Config(**Config(offline=True).model_dump()).offline is True


def test_offline_is_part_of_config_equality() -> None:
    """Two configs differing only in posture are not the same config."""
    assert Config(offline=True) != Config(offline=False)


def test_a_config_stays_frozen_under_offline_mode() -> None:
    """Offline mode does not reach for a mutable escape hatch to record itself."""
    config = Config(offline=True)

    with pytest.raises(ValueError):
        config.offline = False  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Offline mode does not change what the engine produces
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("phrase", EQUIVALENCE_PHRASES, ids=EQUIVALENCE_PHRASES)
def test_an_offline_engine_generates_identical_results(phrase: str) -> None:
    """Offline mode is a refusal at start-up, not a reduced-quality mode.

    Asserted as equality of the whole payload rather than as "no exception was
    raised", because the failure this guards against is silent: an offline
    branch that skipped the lexicon or the n-gram model would still return a
    plausible acronym, and only a comparison notices.
    """
    offline = AcronymEngine(Config(offline=True)).generate(phrase)
    default = AcronymEngine(Config()).generate(phrase)

    assert comparable(offline.to_dict()) == comparable(default.to_dict())


def test_an_offline_engine_extracts_identically() -> None:
    """Extraction reads only bundled resources, and offline mode must not change that."""
    text = "The National Aeronautics and Space Administration (NASA) launched the mission."

    offline = AcronymEngine(Config(offline=True)).extract(text)
    default = AcronymEngine(Config()).extract(text)

    assert comparable(offline.to_dict()) == comparable(default.to_dict())
    assert offline.as_mapping() == {"NASA": "National Aeronautics and Space Administration"}


def test_an_offline_engine_scores_identically() -> None:
    """The objective function is unchanged, term by term."""
    offline = AcronymEngine(Config(offline=True)).score("PDF", "Portable Document Format")
    default = AcronymEngine(Config()).score("PDF", "Portable Document Format")

    assert offline.to_dict() == default.to_dict()


def test_an_offline_engine_resolves_the_same_tier() -> None:
    """Tier resolution is untouched: offline mode refuses, it does not downgrade."""
    offline = AcronymEngine(Config(offline=True, engine_tier=EngineTier.AUTO))
    default = AcronymEngine(Config(engine_tier=EngineTier.AUTO))

    assert offline.engine_tier is default.engine_tier
    assert offline.nlp_backend == default.nlp_backend


# ---------------------------------------------------------------------------
# The plugin refusal
# ---------------------------------------------------------------------------
# This one needs a subprocess. ``pydantic`` discovers plugins through installed
# distribution metadata, which ``importlib.metadata`` scans off ``sys.path``,
# and it caches the result on the first model build -- so a plugin planted
# inside the running pytest interpreter would be discovered too late, or not at
# all, and would then leak into every subsequent test in the session. Planting a
# ``.dist-info`` directory on a fresh interpreter's path is the only faithful
# simulation of the thing being defended against: a distribution that arrives
# through one line in a requirements file.
#
# The plugin object is deliberately *well-formed*. A bare ``plugin = None``
# makes pydantic raise ``AttributeError`` out of its own loader, which is a
# different -- and much louder -- finding than the one under test. What is being
# demonstrated here is the quiet case: foreign code that pydantic imports
# successfully, that works, and that acronymkit can therefore only report.

_PLUGIN_MODULE = '''\
"""A minimal, well-formed pydantic plugin, planted by the offline tests."""


class _Plugin:
    """Accepts every schema build and installs no event handlers."""

    def new_schema_validator(self, *args, **kwargs):
        """Return the (on_enter, on_success, on_error) triple pydantic expects."""
        return None, None, None


plugin = _Plugin()
'''

_PLUGIN_METADATA = """\
Metadata-Version: 2.1
Name: evil-plugin
Version: 9.9.9
Summary: Planted by acronymkit's offline tests; not a real distribution.
"""

_PLUGIN_ENTRY_POINTS = """\
[pydantic]
evil = evil_plugin:plugin
"""

_PLUGIN_PROBE = """\
import json
import sys

sys.path.insert(0, {src!r})
sys.path.insert(0, {plugin_root!r})

from acronymkit import Config
from acronymkit.diagnostics import pydantic_plugins
from acronymkit.exceptions import OfflineError

observed = {{"plugins": list(pydantic_plugins())}}

Config()
observed["default_config_built"] = True
observed["plugin_was_imported"] = "evil_plugin" in sys.modules

try:
    Config(offline=True)
except OfflineError as exc:
    observed["error_type"] = type(exc).__name__
    observed["reason"] = exc.reason
    observed["remedy"] = exc.remedy
else:
    observed["error_type"] = None

print(json.dumps(observed))
"""


@pytest.fixture
def planted_pydantic_plugin(tmp_path: Path) -> Path:
    """Build a directory that looks, to ``importlib.metadata``, like an installed plugin.

    Args:
        tmp_path: Per-test temporary directory.

    Returns:
        A directory to put on a subprocess's ``sys.path``. It contains the
        importable module and the ``.dist-info`` that advertises it under the
        ``pydantic`` entry-point group.
    """
    root = tmp_path / "plugin_root"
    dist_info = root / "evil_plugin-9.9.9.dist-info"
    dist_info.mkdir(parents=True)
    (root / "evil_plugin.py").write_text(_PLUGIN_MODULE, encoding="utf-8")
    (dist_info / "METADATA").write_text(_PLUGIN_METADATA, encoding="utf-8")
    (dist_info / "entry_points.txt").write_text(_PLUGIN_ENTRY_POINTS, encoding="utf-8")
    return root


def run_probe(
    script: str, tmp_path: Path, name: str, **environment_overrides: str
) -> dict[str, Any]:
    """Run ``script`` in a fresh interpreter and decode the JSON it prints.

    Args:
        script: Python source whose last line of output is a JSON document.
        tmp_path: Directory the script file is written to.
        name: File name for the script, for readable failure output.
        **environment_overrides: Extra environment variables for the child.

    Returns:
        The decoded document.

    Raises:
        AssertionError: If the child exited non-zero; its stderr is the message.
    """
    path = tmp_path / name
    path.write_text(script, encoding="utf-8")
    environment = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    environment.pop(OFFLINE_ENV_VAR, None)
    environment.pop("PYDANTIC_DISABLE_PLUGINS", None)
    environment.update(environment_overrides)
    completed = subprocess.run(
        [sys.executable, str(path)],
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
        env=environment,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    return json.loads(completed.stdout.strip().splitlines()[-1])


def test_offline_refuses_to_run_beside_a_third_party_pydantic_plugin(
    planted_pydantic_plugin: Path, tmp_path: Path
) -> None:
    """A planted plugin is seen, does not break normal use, and blocks offline mode.

    Three assertions in one subprocess because they describe one situation:

    * ``pydantic_plugins()`` reports the plugin, so the capability report is
      honest about foreign code it cannot control;
    * an ordinary ``Config()`` still builds, because this is a posture check
      and not a new runtime requirement; and
    * ``Config(offline=True)`` refuses, naming the plugin, because the promise
      "this process will not reach the network" is one acronymkit can no longer
      make on behalf of code it did not write.

    ``plugin_was_imported`` is asserted as well, and it is the uncomfortable
    part: the plugin is already resident by the time the refusal happens.
    Offline mode stops the process from continuing under a broken promise; it
    cannot un-break it. That is why the remedy names
    ``PYDANTIC_DISABLE_PLUGINS`` rather than something the library does itself.
    """
    script = _PLUGIN_PROBE.format(
        src=str(REPO_ROOT / "src"), plugin_root=str(planted_pydantic_plugin)
    )

    observed = run_probe(script, tmp_path, "plugin_refusal.py")

    assert observed["plugins"] == ["evil"]
    assert observed["default_config_built"] is True
    assert observed["plugin_was_imported"] is True
    assert observed["error_type"] == "OfflineError"
    assert "evil" in observed["reason"]
    assert "PYDANTIC_DISABLE_PLUGINS" in observed["remedy"]


def test_the_documented_remedy_actually_lets_offline_mode_start(
    planted_pydantic_plugin: Path, tmp_path: Path
) -> None:
    """``PYDANTIC_DISABLE_PLUGINS=1`` is the remedy, so it must work.

    With the same plugin planted, setting the variable the error message
    recommends makes ``pydantic_plugins()`` empty, leaves the plugin module
    unimported, and lets ``Config(offline=True)`` build. Without this test the
    remedy is advice; with it, it is a checked instruction.
    """
    script = _PLUGIN_PROBE.format(
        src=str(REPO_ROOT / "src"), plugin_root=str(planted_pydantic_plugin)
    )

    observed = run_probe(script, tmp_path, "plugin_remedy.py", PYDANTIC_DISABLE_PLUGINS="1")

    assert observed["plugins"] == []
    assert observed["plugin_was_imported"] is False
    assert observed["error_type"] is None


def test_every_engine_tier_named_in_the_source_actually_exists() -> None:
    """No message may name an ``EngineTier`` member that is not real.

    The ``OfflineError`` remedy once read "Use EngineTier.ZERO_DEPENDENCY or
    EngineTier.STANDARD". There is no ``STANDARD``. An operator following that
    advice gets an ``AttributeError`` at the exact moment they are already
    blocked, which is worse than offering no remedy at all — and no test could
    see it, because the string was only ever compared against itself.

    Scanning the source rather than the exception keeps this honest: a member
    invented inside any docstring, comment or message is caught, not just the
    one that happened to be wrong.
    """
    import re

    from acronymkit import enums

    package = Path(enums.__file__).parent
    real = {member.name for member in EngineTier}
    invented: dict[str, set[str]] = {}
    for module in sorted(package.rglob("*.py")):
        named = set(re.findall(r"\bEngineTier\.([A-Z_]+)\b", module.read_text(encoding="utf-8")))
        bogus = named - real
        if bogus:
            invented[module.name] = bogus

    assert not invented, f"source names EngineTier members that do not exist: {invented}"
