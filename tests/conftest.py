"""Shared pytest configuration and fixtures.

The ``sys.path`` insertion lets the suite run straight from a checkout
(``pytest`` at the repo root) without an editable install, while remaining a
no-op once the package *is* installed — CI exercises both paths.
"""

from __future__ import annotations

import sys
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
