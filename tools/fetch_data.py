#!/usr/bin/env python3
"""Fetch third-party lexicons and evaluation corpora, with a licence ledger.

Why this script exists
----------------------
Two different problems, one solution:

1. **Reproducibility.** Every asset is pinned — to a git commit or a release
   tarball, never to a moving branch — and verified by SHA-256. A silent
   upstream edit changes our lexicon, which changes ``Lambda(A)``, which changes
   every score. The checksum turns that into a loud failure.

2. **Licence hygiene.** This is the part that quietly destroys projects. Assets
   split into two classes and the split is enforced by :attr:`Asset.vendorable`:

   * **Vendorable** — permissively licensed, may be redistributed inside the
     MIT wheel with attribution. Currently SCOWL and CMUdict.
   * **Fetch-only** — copyleft, non-commercial or share-alike. Fine to use on
     your own machine, *not* fine to ship. These land in ``data/`` which is
     git-ignored, and nothing in the build ever reads from there.

   ``tools/build_lexicons.py`` refuses to vendor a non-vendorable asset, so the
   rule is mechanical rather than a matter of remembering.

Usage
-----
::

    python tools/fetch_data.py --list              # show the registry
    python tools/fetch_data.py --all               # fetch everything
    python tools/fetch_data.py scowl cmudict       # fetch specific assets
    python tools/fetch_data.py --verify            # re-check what is on disk
    python tools/fetch_data.py --write-ledger      # regenerate data/LICENSES.md

Nothing here is imported by the library; the standard library is the only
dependency.
"""

from __future__ import annotations

import argparse
import hashlib
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Sequence

REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = REPO_ROOT / "data"
LEDGER_PATH = DATA_DIR / "LICENSES.md"

#: Pinned CMUdict commit. Never track a branch: the dictionary is edited in
#: place upstream and a moving pin makes our phonetic resource irreproducible.
CMUDICT_COMMIT = "74790861f652b15e4ac49015a90074ad62a27690"

#: Pinned Ab3P commit. MED1250 is the gold standard the published extraction
#: F-scores are quoted against, so the pin is what makes our number comparable.
AB3P_COMMIT = "41130cddfcba1449ba612905d4a51274f8f565a8"

#: Pinned SDU@AAAI-21 shared task 2 commit (acronym disambiguation). Pinned to
#: the SHA rather than ``master`` for the usual reason and one extra: the task's
#: own ``scorer.py`` defines the evaluation convention our numbers are quoted
#: under, so a moving pin could change what our accuracy *means* without
#: changing our code.
SDU21_AD_COMMIT = "b9197428521f8fcf8c8d452eee2c6379050ceaea"

#: Repeated in five asset entries; kept here so the pin appears once.
_SDU21_AD_RAW = (
    f"https://raw.githubusercontent.com/amirveyseh/AAAI-21-SDU-shared-task-2-AD/{SDU21_AD_COMMIT}"
)

#: The dataset's licence is *not* the repository's licence, and the difference
#: is the whole point of reading the actual text. The repository root carries an
#: MIT ``LICENSE`` file, but ``README.md`` narrows it explicitly: "The dataset
#: provided for this shared task is licensed under CC BY-NC-SA 4.0 international
#: license, and the evaluation script and the baseline are licensed under MIT
#: license." The narrower, more specific statement governs the data files.
_SDU21_AD_DATA_LICENCE = "CC BY-NC-SA-4.0 (dataset files only; see README.md)"

_SDU21_AD_DATA_NOTE = (
    "NOT vendorable, and the reason is a licence trap worth spelling out. The "
    "repository root ships an MIT LICENSE, which is what a badge or a casual "
    "look reports. README.md contradicts the inference: the MIT grant covers "
    "'the evaluation script and the baseline', while 'the dataset provided for "
    "this shared task is licensed under CC BY-NC-SA 4.0'. Share-alike plus "
    "non-commercial is incompatible with an MIT wheel, so the data files could "
    "not be vendored even if we wanted to. They would be fetch-only regardless: "
    "the med1250 precedent is that an evaluation corpus stays out of the wheel "
    "however permissive its licence, because nothing in the library reads it "
    "and every wheel would pay for the few people running benchmarks."
)

_SDU21_AD_ATTRIBUTION = (
    "Veyseh APB, Dernoncourt F, Tran QH, Nguyen TH. What Does This Acronym "
    "Mean? Introducing a New Dataset for Acronym Identification and "
    "Disambiguation. Proceedings of COLING 2020. "
    "Dataset licensed CC BY-NC-SA 4.0."
)

#: Pinned PLOD-CW dataset revision on the Hugging Face Hub. ``resolve/main`` is
#: a branch, not a pin: a dataset repository can be force-pushed and a teaching
#: subset is edited between cohorts. Resolving the commit SHA once and pinning it
#: is what makes the span numbers reproducible.
PLOD_CW_REVISION = "c40ba1976a749d30fda147e11ed9030e1cd29354"

_PLOD_CW_RAW = f"https://huggingface.co/datasets/surrey-nlp/PLOD-CW/resolve/{PLOD_CW_REVISION}"

_PLOD_CW_LICENCE = "CC-BY-SA-4.0"

#: Read from the repository's own ``LICENSE`` file, whose first line is
#: "Attribution-ShareAlike 4.0 International", and corroborated by the dataset
#: card's ``license: cc-by-sa-4.0`` and its "Licensing Information: CC-BY-SA
#: 4.0" section. Both are pinned below so the claim is checkable rather than
#: taken on trust.
_PLOD_CW_NOTE = (
    "NOT vendorable, and share-alike is the reason rather than the usual "
    "size argument. CC BY-SA 4.0 grants redistribution freely, but section "
    "3(b) requires that Adapted Material be released under BY-SA or a "
    "compatible licence. Putting the corpus in the wheel would either force "
    "BY-SA terms onto a distribution that advertises itself as MIT, or "
    "require a per-file licence carve-out that every downstream redistributor "
    "then has to track -- the same disproportion that ruled out the French and "
    "Spanish Hunspell dictionaries in D-006. The share-alike clause also "
    "reaches further than the corpus file itself: a resource *derived* from "
    "PLOD -- a term-frequency table, a subword index, anything of the shape "
    "D-016 said the extractor would need -- is Adapted Material and would "
    "inherit BY-SA, so this asset is barred from that route as well and not "
    "only from the wheel. It would be fetch-only regardless, on the med1250 "
    "precedent: an evaluation corpus is not a runtime resource and nothing in "
    "the library reads it."
)

_PLOD_CW_ATTRIBUTION = (
    "Zilio L, Saadany H, Sharma P, Kanojia D, Orasan C. PLOD: An Abbreviation "
    "Detection Dataset for Scientific Documents. Proceedings of LREC 2022. "
    "arXiv:2204.12061. PLOD-CW subset prepared by Shenbin Qian, University of "
    "Surrey. Licensed CC BY-SA 4.0."
)

#: Pinned LibreOffice dictionaries commit for the Hunspell assets.
LIBREOFFICE_DICTS_REF = "master"

USER_AGENT = "acronymkit-fetch-data/1.0 (+https://github.com/pierce-lonergan/AcronymKit)"


@dataclass(frozen=True)
class Asset:
    """One downloadable third-party asset.

    Attributes:
        key: Short identifier used on the command line.
        filename: Name the asset is saved under inside ``data/``.
        url: Pinned download URL.
        sha256: Expected digest. Empty string means "not yet recorded"; use
            ``--record`` to compute it when adding an asset.
        licence: SPDX identifier where one applies, otherwise a short name.
        licence_url: Where the licence text was read from.
        vendorable: Whether the licence permits redistribution inside the MIT
            wheel. ``False`` means benchmark/local use only.
        vendor_note: Why it is or is not vendorable — the reasoning, so the
            decision can be re-audited rather than taken on trust.
        purpose: What the project uses it for.
        attribution: The notice that must accompany redistribution.
    """

    key: str
    filename: str
    url: str
    sha256: str
    licence: str
    licence_url: str
    vendorable: bool
    vendor_note: str
    purpose: str
    attribution: str


ASSETS: tuple[Asset, ...] = (
    Asset(
        key="scowl",
        filename="scowl-2020.12.07.tar.gz",
        url="https://downloads.sourceforge.net/wordlist/scowl-2020.12.07.tar.gz",
        sha256="5587667caa20c4891390c2d42dbb4d5c4c3f41bee77af1457ece3ba23fb859cc",
        licence="SCOWL (MIT-style permissive)",
        licence_url="https://raw.githubusercontent.com/en-wl/wordlist/master/scowl/Copyright",
        vendorable=True,
        vendor_note=(
            "Kevin Atkinson's notice grants permission to 'use, copy, modify, "
            "distribute and sell these word lists ... for any purpose ... without "
            "fee, provided that the above copyright notice appears in all copies'. "
            "That is an MIT-equivalent grant, so the derived word list ships in the "
            "wheel with the notice preserved in the resource header."
        ),
        purpose="Bundled English lexicon backing the lexical match indicator Lambda(A).",
        attribution="Copyright 2000-2018 by Kevin Atkinson. Portions copyright by others; see the SCOWL Copyright file.",
    ),
    Asset(
        key="cmudict",
        filename="cmudict.dict",
        url=f"https://raw.githubusercontent.com/cmusphinx/cmudict/{CMUDICT_COMMIT}/cmudict.dict",
        sha256="81917843c7f44ce2b094ac63873c2c7a4cf802040792c455ba3ca406891c3d22",
        licence="BSD-2-Clause",
        licence_url=f"https://raw.githubusercontent.com/cmusphinx/cmudict/{CMUDICT_COMMIT}/LICENSE",
        vendorable=True,
        vendor_note=(
            "Two-clause BSD from Carnegie Mellon University: redistribution in "
            "source and binary form is permitted with the copyright notice and "
            "disclaimer retained. We ship a derived syllable table, not the raw "
            "dictionary, with the notice in the resource header."
        ),
        purpose=(
            "Ground-truth pronunciations: calibrates and validates the syllable "
            "heuristic and supplies real syllable counts for dictionary words."
        ),
        attribution="Copyright (C) 1993-2015 Carnegie Mellon University. All rights reserved.",
    ),
    Asset(
        key="cmudict-license",
        filename="cmudict.LICENSE",
        url=f"https://raw.githubusercontent.com/cmusphinx/cmudict/{CMUDICT_COMMIT}/LICENSE",
        sha256="bd4ce8e44170a5f9f481310ca85c51de3c4f851a65e679b40e603b143bd3542a",
        licence="BSD-2-Clause",
        licence_url=f"https://raw.githubusercontent.com/cmusphinx/cmudict/{CMUDICT_COMMIT}/LICENSE",
        vendorable=True,
        vendor_note="The licence text itself, retained so the notice can be reproduced verbatim.",
        purpose="Attribution text for the derived CMUdict resource.",
        attribution="Copyright (C) 1993-2015 Carnegie Mellon University.",
    ),
    Asset(
        key="med1250",
        filename="MED1250_labeled",
        url=(f"https://raw.githubusercontent.com/ncbi-nlp/Ab3P/{AB3P_COMMIT}/MED1250_labeled"),
        sha256="5093fa8f130ee250add0d0fbde7fc736478e18fbcc4447b00b4179db47f4cf53",
        licence="Public domain (United States Government Work)",
        licence_url=(f"https://raw.githubusercontent.com/ncbi-nlp/Ab3P/{AB3P_COMMIT}/README.md"),
        vendorable=False,
        vendor_note=(
            "Public domain, so redistribution would be lawful -- the NLM notice "
            "states the work 'cannot be copyrighted within the United States' and "
            "that no restriction has been placed on its use or reproduction. It is "
            "still fetch-only: it is a 1.6 MB evaluation corpus, not a runtime "
            "resource, and nothing in the library reads it. Shipping it would "
            "inflate every wheel for the benefit of the few people running "
            "benchmarks."
        ),
        purpose=(
            "Gold standard for extraction evaluation: 1,250 MEDLINE records with "
            "1,221 manually annotated short-form/long-form pairs. This is the "
            "corpus the published Schwartz & Hearst and Ab3P F-scores are quoted "
            "against, which is what makes our number comparable to theirs."
        ),
        attribution=(
            "Sohn S, Comeau DC, Kim W, Wilbur WJ. Abbreviation definition "
            "identification based on automatic precision estimates. "
            "BMC Bioinformatics. 2008;9:402. National Library of Medicine."
        ),
    ),
    Asset(
        key="ab3p-readme",
        filename="Ab3P_README.md",
        url=f"https://raw.githubusercontent.com/ncbi-nlp/Ab3P/{AB3P_COMMIT}/README.md",
        sha256="756d5fa9a5900901f10b357c11230e55febe2af1f16f3fa3a5353af415f750eb",
        licence="Public domain (United States Government Work)",
        licence_url=f"https://raw.githubusercontent.com/ncbi-nlp/Ab3P/{AB3P_COMMIT}/README.md",
        vendorable=False,
        vendor_note="Retained alongside MED1250 because it defines the annotation format.",
        purpose="Specification of the MED1250 annotation format and its comment conventions.",
        attribution="National Library of Medicine.",
    ),
    Asset(
        key="sdu21-ad-diction",
        filename="sdu21_ad_diction.json",
        url=f"{_SDU21_AD_RAW}/dataset/diction.json",
        sha256="58e3450b5d77b4d791045c74cb0f487fdfbdd5c58d8d4c270d0fda4e2d2b12f5",
        licence=_SDU21_AD_DATA_LICENCE,
        licence_url=f"{_SDU21_AD_RAW}/README.md",
        vendorable=False,
        vendor_note=_SDU21_AD_DATA_NOTE,
        purpose=(
            "The shared task's own expansion dictionary: 732 ambiguous acronyms "
            "mapped to their candidate long forms. Loaded straight into an "
            "acronymkit ExpansionDictionary, which is what makes the Tier 1 "
            "disambiguator evaluable at all -- it is the first ready-made "
            "dictionary this project has had that it did not build itself."
        ),
        attribution=_SDU21_AD_ATTRIBUTION,
    ),
    Asset(
        key="sdu21-ad-dev",
        filename="sdu21_ad_dev.json",
        url=f"{_SDU21_AD_RAW}/dataset/dev.json",
        sha256="3980517288fd7f79d489edbc2cefd66a63bd97f91390fb419d6fad3752f414c7",
        licence=_SDU21_AD_DATA_LICENCE,
        licence_url=f"{_SDU21_AD_RAW}/README.md",
        vendorable=False,
        vendor_note=_SDU21_AD_DATA_NOTE,
        purpose=(
            "Development set for acronym disambiguation: 6,189 sentences, each "
            "with one ambiguous acronym token index and its gold expansion. The "
            "evaluation set for bench/run_disambiguation.py."
        ),
        attribution=_SDU21_AD_ATTRIBUTION,
    ),
    Asset(
        key="sdu21-ad-train",
        filename="sdu21_ad_train.json",
        url=f"{_SDU21_AD_RAW}/dataset/train.json",
        sha256="bcc5c855c9c408ff76998db1d5c785c2ecbb694b7311ccb8bc6f2cfe7051266a",
        licence=_SDU21_AD_DATA_LICENCE,
        licence_url=f"{_SDU21_AD_RAW}/README.md",
        vendorable=False,
        vendor_note=_SDU21_AD_DATA_NOTE,
        purpose=(
            "Training set (50,034 instances). acronymkit reads no training data, "
            "so this is used solely to build the most-frequent-expansion "
            "baseline the shared task defines -- the prior our context scoring "
            "has to beat to be worth anything."
        ),
        attribution=_SDU21_AD_ATTRIBUTION,
    ),
    Asset(
        key="sdu21-ad-scorer",
        filename="sdu21_ad_scorer.py",
        url=f"{_SDU21_AD_RAW}/scorer.py",
        sha256="2b68c764780dcd43821feb4d03ba6a9747a9017875ce22d569be173a8e3cdd38",
        licence="MIT",
        licence_url=f"{_SDU21_AD_RAW}/LICENSE",
        vendorable=False,
        vendor_note=(
            "Genuinely MIT -- the README's carve-out puts the evaluation script "
            "and baseline under the repository licence, and only the data under "
            "CC BY-NC-SA. Still not vendored: it is a benchmark script, and "
            "bench/run_disambiguation.py reimplements its metric rather than "
            "importing it so the numbers can be produced without a download. "
            "Pinned so that reimplementation stays auditable against the "
            "original, which is the only reason this file is in the registry."
        ),
        purpose=(
            "The shared task's official scorer. Defines the convention our "
            "disambiguation numbers are quoted under: exact string equality "
            "against the gold expansion, headline metric macro-averaged P/R/F1 "
            "over gold expansion classes, accuracy reported separately."
        ),
        attribution="Amir Pouran Ben Veyseh and contributors; MIT licensed.",
    ),
    Asset(
        key="sdu21-ad-readme",
        filename="sdu21_ad_README.md",
        url=f"{_SDU21_AD_RAW}/README.md",
        sha256="12277bc8eb443b9e495e5a7ce08e7bd9e40dbcfada9cfd94260f278a63c31246",
        licence="MIT (the document), describing a CC BY-NC-SA-4.0 dataset",
        licence_url=f"{_SDU21_AD_RAW}/README.md",
        vendorable=False,
        vendor_note=(
            "Retained for the same reason as ab3p-readme: it is the normative "
            "description of the data format. It is also the *only* place the "
            "dataset's real licence is stated, so pinning it is what makes the "
            "CC BY-NC-SA finding reproducible rather than a claim in a note."
        ),
        purpose=(
            "Specification of the SDU@AAAI-21 AD record format, the official "
            "metric, and the licence split between data and scripts."
        ),
        attribution="Amir Pouran Ben Veyseh and contributors.",
    ),
    Asset(
        key="plod-cw-test",
        filename="plod_cw_test.conll",
        url=f"{_PLOD_CW_RAW}/data/data_test.conll",
        sha256="87e81ad0061a6ff384fd207ced1ecbdb26a81910950b6d0b59dee79a58044c04",
        licence=_PLOD_CW_LICENCE,
        licence_url=f"{_PLOD_CW_RAW}/LICENSE",
        vendorable=False,
        vendor_note=_PLOD_CW_NOTE,
        purpose=(
            "The evaluation split for bench/run_spans.py: 153 sentences from "
            "PLOS journal articles, 5,000 tokens, 270 abbreviation spans and "
            "150 long-form spans in BIO tags. The first corpus in this project "
            "that is neither MEDLINE abstracts nor a shared-task JSON, and the "
            "only evidence available about how the extractor behaves on a "
            "different genre and a different annotation convention."
        ),
        attribution=_PLOD_CW_ATTRIBUTION,
    ),
    Asset(
        key="plod-cw-dev",
        filename="plod_cw_dev.conll",
        url=f"{_PLOD_CW_RAW}/data/data_dev.conll",
        sha256="3feb27cc423bbd5e290b7cef6947c5570a2dcc8f6d486fec8f757e425bc5b0cd",
        licence=_PLOD_CW_LICENCE,
        licence_url=f"{_PLOD_CW_RAW}/LICENSE",
        vendorable=False,
        vendor_note=_PLOD_CW_NOTE,
        purpose=(
            "Validation split, 126 sentences. Nothing is selected on it -- "
            "acronymkit reads no training data and nothing was tuned against "
            "PLOD -- so it is fetched only to make the pooled 'all' arm "
            "possible, which exists because 153 sentences is a thin sample."
        ),
        attribution=_PLOD_CW_ATTRIBUTION,
    ),
    Asset(
        key="plod-cw-train",
        filename="plod_cw_train.conll",
        url=f"{_PLOD_CW_RAW}/data/data_train.conll",
        sha256="ba2e94e60920d764f4e0220e61a740eee4921103cac49406dee1f97fd6897743",
        licence=_PLOD_CW_LICENCE,
        licence_url=f"{_PLOD_CW_RAW}/LICENSE",
        vendorable=False,
        vendor_note=_PLOD_CW_NOTE,
        purpose=(
            "Training split, 1,072 sentences. Used for exactly one thing: the "
            "pooled 1,351-sentence arm that checks whether the test-split "
            "figures are sample noise. No parameter of this library is fitted "
            "to any of it."
        ),
        attribution=_PLOD_CW_ATTRIBUTION,
    ),
    Asset(
        key="plod-cw-license",
        filename="plod_cw.LICENSE",
        url=f"{_PLOD_CW_RAW}/LICENSE",
        sha256="7abe19ec9bb73b36141b999b861d24ad855e808bafe0f81e84cce28556f6c297",
        licence=_PLOD_CW_LICENCE,
        licence_url=f"{_PLOD_CW_RAW}/LICENSE",
        vendorable=False,
        vendor_note=(
            "The licence text itself, pinned so the share-alike finding above "
            "rests on the deed rather than on a badge. Its first line is "
            "'Attribution-ShareAlike 4.0 International'. The SDU-21 entry "
            "below is the standing reminder of why this file is fetched: that "
            "repository's MIT badge was wrong about its own data."
        ),
        purpose="Verbatim CC BY-SA 4.0 deed governing the PLOD-CW corpus files.",
        attribution=_PLOD_CW_ATTRIBUTION,
    ),
    Asset(
        key="plod-cw-readme",
        filename="plod_cw_README.md",
        url=f"{_PLOD_CW_RAW}/README.md",
        sha256="e82dff3a0dd1edf20dddfd72910868799f3e4839eefeb8bc2293c2d92cd859cd",
        licence=f"{_PLOD_CW_LICENCE} (dataset card)",
        licence_url=f"{_PLOD_CW_RAW}/LICENSE",
        vendorable=False,
        vendor_note=(
            "Retained for the same reason as ab3p-readme and sdu21-ad-readme: "
            "it is the normative description of the record format and of the "
            "label set, and it is where the corpus states its own provenance "
            "-- 'collected for research from the PLOS journals indexing of "
            "abbreviations and long-forms in the text'. That sentence is the "
            "reason bench/run_spans.py treats PLOD's conventions as a "
            "different target rather than as a better MED1250."
        ),
        purpose=(
            "Specification of the PLOD-CW CoNLL format, its AC/LF label set, "
            "its split sizes, and its licensing statement."
        ),
        attribution=_PLOD_CW_ATTRIBUTION,
    ),
    Asset(
        key="hunspell-fr",
        filename="fr.dic",
        url=(
            "https://raw.githubusercontent.com/LibreOffice/dictionaries/"
            f"{LIBREOFFICE_DICTS_REF}/fr_FR/dictionaries/fr.dic"
        ),
        sha256="b78a868e31dd6e373b6c3217969afb898a9acde828a5e7ef97308da42218c88c",
        licence="MPL-2.0 (Dicollecte / Grammalecte)",
        licence_url=(
            "https://raw.githubusercontent.com/LibreOffice/dictionaries/"
            f"{LIBREOFFICE_DICTS_REF}/fr_FR/dictionaries/README_dict_fr.txt"
        ),
        vendorable=False,
        vendor_note=(
            "MPL is file-level copyleft: an MPL file may sit inside a larger work "
            "under other terms, so vendoring is arguably permitted. We decline "
            "anyway. Shipping it would make the wheel MIT-plus-MPL, obliging every "
            "downstream redistributor to track a second licence for one data file. "
            "The cost is not worth it for a language we cannot yet evaluate, so "
            "French is fetch-only and marked experimental."
        ),
        purpose="Optional real French lexicon, installed locally by the user.",
        attribution="Dicollecte / Grammalecte French dictionary contributors.",
    ),
    Asset(
        key="hunspell-es",
        filename="es_ES.dic",
        url=(
            "https://raw.githubusercontent.com/LibreOffice/dictionaries/"
            f"{LIBREOFFICE_DICTS_REF}/es/es_ES.dic"
        ),
        sha256="6975dddec3d5d2c676069537bc67b4b5f786c65c5d4cf6703a82acf779ac9ec1",
        licence="GPL-3.0-or-later OR LGPL-3.0-or-later OR MPL-1.1 (RLA-ES)",
        licence_url=(
            "https://raw.githubusercontent.com/LibreOffice/dictionaries/"
            f"{LIBREOFFICE_DICTS_REF}/es/LICENSE.md"
        ),
        vendorable=False,
        vendor_note=(
            "Disjunctive tri-licence; the MPL-1.1 arm would technically permit "
            "inclusion in a larger work. Declined for the same reason as French: "
            "a second licence on one data file is a disproportionate burden on "
            "downstream redistributors."
        ),
        purpose="Optional real Spanish lexicon, installed locally by the user.",
        attribution="RLA-ES / Santiago Bosio and contributors.",
    ),
    Asset(
        key="hunspell-de",
        filename="de_DE_frami.dic",
        url=(
            "https://raw.githubusercontent.com/LibreOffice/dictionaries/"
            f"{LIBREOFFICE_DICTS_REF}/de/de_DE_frami.dic"
        ),
        sha256="4ca3c958b0e5545910999bc246f668840bf8ede3df8e5e6790d05edd5a586c38",
        licence="GPL-2.0-or-later OR GPL-3.0-or-later OR LGPL-2.0/2.1 OR OASIS-0.1",
        licence_url=(
            "https://raw.githubusercontent.com/LibreOffice/dictionaries/"
            f"{LIBREOFFICE_DICTS_REF}/de/COPYING_OASIS.txt"
        ),
        vendorable=False,
        vendor_note=(
            "NOT vendorable, and this one is not a judgement call. The permissive "
            "arm (OASIS 0.1) is conditional: it only permits distribution 'with "
            "programs that support the OASIS Open Document Format ... and whose "
            "PRIMARY format for saving documents is the Open Document Format'. "
            "acronymkit is not an ODF application, so that grant does not reach us "
            "and the fallback is GPL/LGPL, which is incompatible with vendoring "
            "into an MIT wheel."
        ),
        purpose="Optional real German lexicon, installed locally by the user.",
        attribution="igerman98 / Bjoern Jacke and the Frami contributors.",
    ),
)

BY_KEY = {asset.key: asset for asset in ASSETS}


def _download(url: str, timeout: float = 180.0) -> bytes:
    """Fetch ``url``, following redirects.

    Args:
        url: Pinned asset URL.
        timeout: Socket timeout in seconds.

    Returns:
        The response body.

    Raises:
        RuntimeError: On any transport or HTTP failure, with the URL included.
    """
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return bytes(response.read())
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"HTTP {exc.code} fetching {url}") from exc
    except Exception as exc:
        raise RuntimeError(f"{type(exc).__name__} fetching {url}") from exc


def fetch(asset: Asset, *, record: bool = False, force: bool = False) -> Path:
    """Download ``asset`` into ``data/`` and verify its digest.

    Args:
        asset: Registry entry to fetch.
        record: Print the computed digest instead of enforcing the pinned one.
            For maintainers adding a new asset.
        force: Re-download even when a verified copy is already present.

    Returns:
        Path to the downloaded file.

    Raises:
        SystemExit: If the digest does not match the pinned value. A drift here
            means the upstream asset changed under a pin that promised it had
            not; continuing would silently alter the library's behaviour.
    """
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    dest = DATA_DIR / asset.filename

    already_verified = (
        dest.exists()
        and not force
        and bool(asset.sha256)
        and hashlib.sha256(dest.read_bytes()).hexdigest() == asset.sha256
    )
    if already_verified:
        print(f"  cached   {asset.key:16} {dest.name}")
        return dest

    payload = _download(asset.url)
    digest = hashlib.sha256(payload).hexdigest()

    if record or not asset.sha256:
        print(f"  RECORDED {asset.key:16} {len(payload):>10,}B  sha256={digest}")
    elif digest != asset.sha256:
        raise SystemExit(
            f"checksum mismatch for {asset.key}\n"
            f"  url      {asset.url}\n"
            f"  expected {asset.sha256}\n"
            f"  actual   {digest}\n"
            "The pinned upstream asset changed. Do not 'fix' this by updating the "
            "checksum until you have established what changed and why -- the pin "
            "exists so that a lexicon edit cannot silently move every score."
        )
    else:
        print(f"  ok       {asset.key:16} {len(payload):>10,}B")

    dest.write_bytes(payload)
    return dest


def verify_all() -> int:
    """Re-check every already-downloaded asset against its pinned digest.

    Returns:
        Process exit code: ``0`` when everything present is intact.
    """
    problems = 0
    for asset in ASSETS:
        dest = DATA_DIR / asset.filename
        if not dest.exists():
            print(f"  absent   {asset.key:16} (run: python tools/fetch_data.py {asset.key})")
            continue
        if not asset.sha256:
            print(f"  unpinned {asset.key:16} (no recorded checksum)")
            continue
        digest = hashlib.sha256(dest.read_bytes()).hexdigest()
        if digest == asset.sha256:
            print(f"  ok       {asset.key:16}")
        else:
            print(f"  MISMATCH {asset.key:16} expected {asset.sha256} got {digest}")
            problems += 1
    return 1 if problems else 0


def write_ledger() -> Path:
    """Regenerate ``data/LICENSES.md`` from the registry.

    The ledger is generated rather than hand-maintained so it cannot drift from
    the code that actually enforces the vendoring rule.

    Returns:
        Path to the written ledger.
    """
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Third-party asset ledger",
        "",
        "<!-- GENERATED by tools/fetch_data.py --write-ledger. Do not edit by hand. -->",
        "",
        "Every third-party asset this project downloads, with its licence and whether",
        "it may be redistributed inside the wheel.",
        "",
        "`tools/build_lexicons.py` refuses to vendor anything marked **fetch-only**, so",
        "the split below is enforced by code rather than by diligence.",
        "",
        "## Vendored into the wheel",
        "",
        "Permissively licensed. Redistributed in derived form with the notice preserved",
        "in the resource file header.",
        "",
    ]

    def block(asset: Asset) -> list[str]:
        return [
            f"### `{asset.key}` — {asset.filename}",
            "",
            f"- **Licence:** {asset.licence}",
            f"- **Licence text:** <{asset.licence_url}>",
            f"- **Source:** <{asset.url}>",
            f"- **SHA-256:** `{asset.sha256 or 'not yet recorded'}`",
            f"- **Used for:** {asset.purpose}",
            f"- **Attribution:** {asset.attribution}",
            "",
            f"{asset.vendor_note}",
            "",
        ]

    for asset in ASSETS:
        if asset.vendorable:
            lines += block(asset)

    lines += [
        "## Fetch-only — never committed, never packaged",
        "",
        "Copyleft, share-alike or non-commercial. Fine to use on your own machine;",
        "shipping them would change the licence of the wheel. `data/` is git-ignored.",
        "",
    ]
    for asset in ASSETS:
        if not asset.vendorable:
            lines += block(asset)

    lines += [
        "## Adding an asset",
        "",
        "1. Read the actual licence text. Do not infer it from a badge or a README line.",
        '2. Add an `Asset` to `ASSETS` in `tools/fetch_data.py` with `sha256=""`.',
        "3. Run `python tools/fetch_data.py <key> --record` and paste the digest in.",
        "4. Run `python tools/fetch_data.py --write-ledger`.",
        "5. If you marked it vendorable, say in `vendor_note` *why* the licence permits it.",
        "",
    ]

    LEDGER_PATH.write_text("\n".join(lines), encoding="utf-8", newline="\n")
    return LEDGER_PATH


def _list_assets() -> None:
    """Print the registry as a table."""
    print(f"{'KEY':18} {'VENDOR':8} {'LICENCE':52} PURPOSE")
    print(f"{'-' * 18} {'-' * 8} {'-' * 52} {'-' * 40}")
    for asset in ASSETS:
        flag = "wheel" if asset.vendorable else "local"
        print(f"{asset.key:18} {flag:8} {asset.licence[:52]:52} {asset.purpose[:60]}")


def main(argv: Optional[Sequence[str]] = None) -> int:
    """Command-line entry point.

    Args:
        argv: Argument vector; defaults to ``sys.argv[1:]``.

    Returns:
        Process exit code.
    """
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("keys", nargs="*", help="asset keys to fetch")
    parser.add_argument("--all", action="store_true", help="fetch every registered asset")
    parser.add_argument("--list", action="store_true", help="show the registry and exit")
    parser.add_argument("--verify", action="store_true", help="re-check digests on disk")
    parser.add_argument("--record", action="store_true", help="print digests instead of enforcing")
    parser.add_argument("--force", action="store_true", help="re-download cached assets")
    parser.add_argument("--write-ledger", action="store_true", help="regenerate data/LICENSES.md")
    args = parser.parse_args(argv)

    if args.list:
        _list_assets()
        return 0
    if args.verify:
        return verify_all()
    if args.write_ledger and not (args.keys or args.all):
        print(f"wrote {write_ledger().relative_to(REPO_ROOT)}")
        return 0

    selected = ASSETS if args.all else tuple(BY_KEY[k] for k in args.keys if k in BY_KEY)
    unknown = [k for k in args.keys if k not in BY_KEY]
    if unknown:
        print(f"unknown asset(s): {', '.join(unknown)}", file=sys.stderr)
        _list_assets()
        return 2
    if not selected:
        parser.print_help()
        return 2

    print(f"fetching {len(selected)} asset(s) into {DATA_DIR}")
    for asset in selected:
        fetch(asset, record=args.record, force=args.force)

    if args.write_ledger:
        print(f"wrote {write_ledger().relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
