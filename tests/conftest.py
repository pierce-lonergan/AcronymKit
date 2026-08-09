"""Shared pytest configuration and fixtures.

The ``sys.path`` insertion lets the suite run straight from a checkout
(``pytest`` at the repo root) without an editable install, while remaining a
no-op once the package *is* installed — CI exercises both paths.
"""

from __future__ import annotations

import sys
import time
from functools import lru_cache
from pathlib import Path
from typing import Iterator

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SRC = REPO_ROOT / "src"
if SRC.is_dir() and str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from acronymkit import AcronymEngine, Config  # noqa: E402
from acronymkit.enums import EngineTier, Language  # noqa: E402
from acronymkit.lexicon import Lexicon  # noqa: E402
from acronymkit.phonetics import CharNGramModel  # noqa: E402

# --------------------------------------------------------------------------
# Canonical corpus
# --------------------------------------------------------------------------
#: Phrases whose textbook initialism the default configuration must return as
#: the primary result. Shared by the preset-calibration and generator tests so
#: retuning ``STRATEGY_WEIGHTS`` cannot silently regress any of them.
CANONICAL_ACRONYMS = [
    ("Application Programming Interface", "API"),
    ("Portable Document Format", "PDF"),
    ("National Aeronautics and Space Administration", "NASA"),
    ("Hyper Text Markup Language", "HTML"),
    ("Random Access Memory", "RAM"),
    ("Central Processing Unit", "CPU"),
    ("Graphics Processing Unit", "GPU"),
    ("Self Contained Underwater Breathing Apparatus", "SCUBA"),
    ("Light Amplification by Stimulated Emission of Radiation", "LASER"),
    ("Structured Query Language", "SQL"),
    ("Customer Relationship Management", "CRM"),
    ("Quality Assurance", "QA"),
    ("Transmission Control Protocol", "TCP"),
    ("Simple Object Access Protocol", "SOAP"),
    ("Basic Input Output System", "BIOS"),
    ("Read Only Memory", "ROM"),
]

#: Documents with their expected (short form, long form) extractions.
EXTRACTION_CASES = [
    (
        "The National Aeronautics and Space Administration (NASA) launched the mission.",
        [("NASA", "National Aeronautics and Space Administration")],
    ),
    ("We used a support vector machine (SVM) classifier.", [("SVM", "support vector machine")]),
    ("MRI (magnetic resonance imaging) confirmed it.", [("MRI", "magnetic resonance imaging")]),
    ("the result (see Figure 3) was clear", []),
    ("(1) first item (2) second item", []),
]


# --------------------------------------------------------------------------
# Fixtures
# --------------------------------------------------------------------------
@pytest.fixture(scope="session")
def default_config() -> Config:
    """A stock :class:`Config` with every default in force."""
    return Config()


@pytest.fixture(scope="session")
def engine() -> AcronymEngine:
    """A session-scoped Tier 0 engine. Safe to share: the engine is immutable."""
    return AcronymEngine(Config(engine_tier=EngineTier.ZERO_DEPENDENCY))


@pytest.fixture(scope="session")
def english_lexicon() -> Lexicon:
    """The bundled English lexicon."""
    return Lexicon.load(Language.EN)


@pytest.fixture(scope="session")
def english_ngram() -> CharNGramModel:
    """The bundled English character-bigram model."""
    return CharNGramModel.load(Language.EN)


@pytest.fixture
def tmp_lexicon_file(tmp_path: Path) -> Iterator[Path]:
    """A small on-disk lexicon for exercising ``Config.lexicon_path`` overrides."""
    path = tmp_path / "custom_lexicon.txt"
    path.write_text(
        "# custom test lexicon\n\nalpha\nbravo\ncharlie\ndelta\nnexus\n",
        encoding="utf-8",
    )
    yield path


# --------------------------------------------------------------------------
# Optional-dependency gating
# --------------------------------------------------------------------------
def _nlp_backend_available() -> bool:
    """Whether any Tier 1 backend can actually run here."""
    try:
        from acronymkit.nlp import NltkBackend, SpacyBackend
    except ImportError:  # pragma: no cover - package always importable
        return False
    return any(backend().is_available() for backend in (SpacyBackend, NltkBackend))


HAS_NLP_BACKEND = _nlp_backend_available()

requires_nlp = pytest.mark.skipif(
    not HAS_NLP_BACKEND,
    reason="no Tier 1 NLP backend installed (pip install 'acronymkit[nlp]')",
)


def _module_available(name: str) -> bool:
    import importlib.util

    return importlib.util.find_spec(name) is not None


# --------------------------------------------------------------------------
# Timing budgets
# --------------------------------------------------------------------------
# A hard-coded wall-clock threshold is not a measurement, it is a guess about
# somebody else's hardware -- and it is how a green suite turns red on a shared
# CI runner. Absolute performance numbers belong in the benchmark suite, where
# the environment is pinned and dispersion is reported (see docs/BENCHMARKS.md).
#
# What belongs *here* is:
#   * scaling assertions, which are machine-independent by construction -- if
#     doubling the input less than triples the time, the path is not quadratic
#     no matter how fast the box is; and
#   * hang guards, expressed as a multiple of this machine's measured speed
#     rather than as a constant.

#: Seconds taken by :func:`_reference_workload` on the development machine
#: (Python 3.13, Windows 11, x86-64). Recorded as the fastest of five runs.
#: Used only as the denominator of :func:`machine_factor`.
REFERENCE_WORKLOAD_SECONDS = 0.0421


def _reference_workload() -> float:
    """Time a fixed, allocation-free, pure-Python CPU loop.

    Deliberately boring: an integer loop tracks interpreter dispatch speed,
    which is what dominates every hot path in this library.

    Returns:
        Elapsed seconds for one run.
    """
    started = time.perf_counter()
    total = 0
    for index in range(2_000_000):
        total += index % 7
    assert total  # keep the loop from being optimised away
    return time.perf_counter() - started


@lru_cache(maxsize=1)
def machine_factor() -> float:
    """How much slower this machine is than the development baseline.

    ``1.0`` means "as fast as the dev machine"; ``3.0`` means "three times
    slower". Clamped below at ``1.0`` so a faster machine tightens nothing —
    budgets are hang guards, not a race.

    Returns:
        A multiplier ``>= 1.0``, computed once per session.
    """
    observed = min(_reference_workload() for _ in range(3))
    return max(observed / REFERENCE_WORKLOAD_SECONDS, 1.0)


def timing_budget(dev_seconds: float, *, slack: float = 4.0) -> float:
    """Scale a development-machine budget to the current machine.

    Args:
        dev_seconds: What the operation costs on the dev baseline.
        slack: Multiplier absorbing scheduler noise, cold caches and the
            general unfairness of shared CI runners. The default is
            deliberately loose: these bounds exist to catch a pathology
            (a hang, a reintroduced quadratic), not to police a percentage.

    Returns:
        The wall-clock ceiling to assert against, in seconds.
    """
    return dev_seconds * slack * machine_factor()


requires_click = pytest.mark.skipif(
    not _module_available("click"), reason="click not installed (pip install 'acronymkit[cli]')"
)
requires_jsonschema = pytest.mark.skipif(
    not _module_available("jsonschema"), reason="jsonschema not installed"
)


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    """Auto-apply the ``nlp`` marker to anything in ``test_nlp.py``."""
    for item in items:
        if item.nodeid.split("::")[0].endswith("test_nlp.py"):
            item.add_marker("nlp")
