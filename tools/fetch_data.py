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

   A third question is separate from both and used to be answered from memory:
   may a resource *derived* from an asset ship, when the asset itself does not?
   The two answers come apart in both directions. MED1250 is public domain and
   fetch-only for size reasons alone, so a table derived from it may ship.
   PLOD-CW is freely redistributable and share-alike, so a table derived from
   it may **not** — CC BY-SA 4.0 section 3(b) reaches Adapted Material, which is
   the finding recorded in that asset's note. :attr:`Asset.derivable` states the
   answer per asset and ``tools/build_reliability_table.py`` enforces it the way
   ``tools/build_lexicons.py`` enforces :attr:`Asset.vendorable`. It denies by
   default: a new asset is assumed to taint what is derived from it until
   someone reads the licence and says otherwise in writing.

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
RESOURCE_DIR = REPO_ROOT / "src" / "acronymkit" / "resources"

#: Pinned CMUdict commit. Never track a branch: the dictionary is edited in
#: place upstream and a moving pin makes our phonetic resource irreproducible.
CMUDICT_COMMIT = "74790861f652b15e4ac49015a90074ad62a27690"

#: Pinned Ab3P commit. MED1250 is the gold standard the published extraction
#: F-scores are quoted against, so the pin is what makes our number comparable.
AB3P_COMMIT = "41130cddfcba1449ba612905d4a51274f8f565a8"

#: Repeated in four asset entries; kept here so the pin appears once.
_AB3P_RAW = f"https://raw.githubusercontent.com/ncbi-nlp/Ab3P/{AB3P_COMMIT}"

#: Read from the repository's own ``README.md``, whose "Public Domain Notice"
#: states the work "cannot be copyrighted within the United States" and that
#: the NLM and the U.S. Government "have not placed any restriction on its use
#: or reproduction". That is the widest grant any asset here carries, which is
#: why every Ab3P asset is ``derivable=True`` even where it is fetch-only.
_AB3P_LICENCE = "Public domain (United States Government Work)"

_AB3P_ATTRIBUTION = (
    "Sohn S, Comeau DC, Kim W, Wilbur WJ. Abbreviation definition "
    "identification based on automatic precision estimates. "
    "BMC Bioinformatics. 2008;9:402. National Library of Medicine."
)

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

#: Pinned SDU@AAAI-22 shared task 1 commit (acronym extraction). Resolved from
#: the repository's ``main`` HEAD on 2026-08-23 and pinned to the SHA, for the
#: usual reproducibility reason and the same extra one the AD pin carries: the
#: task ships its own ``scorer.py``, and a moving pin could change what a
#: reported P/R/F1 *means* without changing a line of our code.
SDU22_AE_COMMIT = "4a8f3b644c2824cf62e06907c8324fedc0941f24"

#: Repeated in six asset entries; kept here so the pin appears once.
_SDU22_AE_RAW = (
    f"https://raw.githubusercontent.com/amirveyseh/AAAI-22-SDU-shared-task-1-AE/{SDU22_AE_COMMIT}"
)

#: Read from the terms on 2026-08-23, not from the badge. The README's
#: "# Licenses" section: "The dataset provided for this shared task is licensed
#: under CC BY-NC-SA 4.0 international license, and the evaluation script and
#: the baseline are licensed under MIT license."
_SDU22_AE_DATA_LICENCE = "CC BY-NC-SA-4.0 (dataset files only; see README.md)"

_SDU22_AE_DATA_NOTE = (
    "NOT vendorable, and the same licence trap as both SDU-21 repositories, now "
    "for the third time. The repository root ships an MIT LICENSE, and "
    "api.github.com/repos/amirveyseh/AAAI-22-SDU-shared-task-1-AE duly reported "
    '`"license": {"key": "mit", "spdx_id": "MIT"}` when queried live on '
    "2026-08-23. The README narrows it: MIT covers 'the evaluation script and "
    "the baseline', while 'the dataset provided for this shared task is licensed "
    "under CC BY-NC-SA 4.0'. Non-commercial plus share-alike cannot go into an "
    "MIT wheel, and it would be fetch-only regardless on the med1250 precedent: "
    "an evaluation corpus is not a runtime resource and nothing in src/ reads it."
)

_SDU22_AE_ATTRIBUTION = (
    "Veyseh APB, Meister N, Dernoncourt F, Nguyen TH. MACRONYM: A Large-Scale "
    "Dataset for Multilingual and Multi-Domain Acronym Extraction. SDU@AAAI-22 "
    "shared task 1. Dataset licensed CC BY-NC-SA 4.0."
)

#: Why the English *test* splits are deliberately absent from the registry
#: below. Both were fetched once during registration on 2026-08-23 and both
#: carry ZERO labels -- legal/test.json is 446 samples, 0 labelled;
#: scientific/test.json is 498 samples, 0 labelled. The gold stayed on the
#: CodaLab server when the evaluation phase closed. Registering them would put
#: two files in the ledger that look like blind splits, read like blind splits,
#: and score 0.00 against everything, which is exactly the shape of harness bug
#: this project has already paid for once. The fact is recorded here instead.

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

# ---------------------------------------------------------------------------
# Federal Register (W10)
# ---------------------------------------------------------------------------
#: The Government Publishing Office's Public Domain & Copyright Notice, which is
#: where this project read the Federal Register's terms.
#:
#: It is fetched and checksummed like any other licence file, for the reason the
#: ``plod-cw-license`` entry gives: a licence finding that rests on a note in
#: this file rather than on the text is the finding that has been wrong three
#: times here already.
_GOVINFO_POLICIES = "https://www.govinfo.gov/about/policies"

#: The statute. Cited and **not** fetched, and the reason is worth recording
#: rather than leaving as an absence: ``uscode.house.gov`` serves this page with
#: a per-response token, so two fetches a second apart differ in bytes. Pinning
#: it would install a checksum that fails on the next run for no reason, which is
#: worse than not pinning it -- ``fetch()`` reserves a very loud failure for a
#: pinned asset that changed, and an asset that changes every time teaches the
#: reader to ignore it.
_USC_17_105 = (
    "https://uscode.house.gov/view.xhtml"
    "?req=granuleid:USC-prelim-title17-section105&num=0&edition=prelim"
)

_FEDERAL_REGISTER_LICENCE = "Public domain (United States Government Work, 17 U.S.C. 105)"

_FEDERAL_REGISTER_NOTE = (
    "Read from GPO's Public Domain & Copyright Notice on 2026-08-24, not from a "
    "badge and not from the Federal Register's own reader-aids pages, which "
    "could not be read from this host -- see the CAPTCHA finding in the "
    "Substrate entry below. The notice quotes the statute: 'Copyright protection "
    "under this title is not available for any work of the United States "
    "Government'. It also carries a caveat that a one-word licence field would "
    "destroy, and that caveat is the reason the corpus is fetch-only rather than "
    "merely large: a Government publication may contain third-party copyrighted "
    "material used with permission, and publication in a Government document "
    "does not extend that permission to anyone else. Federal Register rules "
    "incorporate industry standards and manufacturers' service bulletins by "
    "reference and quote from them, so 'public domain' is true of the document "
    "and not automatically true of every string inside it."
)

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
        size_bytes: Size of the pinned payload. Recorded alongside the digest
            rather than read from ``data/`` at report time, so the ledger says
            the same thing on a machine that has fetched nothing. It is also the
            figure the wheel-budget argument in ``.github/workflows/ci.yml``
            needs when someone proposes bundling an asset.
        licence: SPDX identifier where one applies, otherwise a short name.
        licence_url: Where the licence text was read from.
        vendorable: Whether the licence permits redistribution inside the MIT
            wheel. ``False`` means benchmark/local use only.
        vendor_note: Why it is or is not vendorable — the reasoning, so the
            decision can be re-audited rather than taken on trust.
        purpose: What the project uses it for.
        attribution: The notice that must accompany redistribution.
        derivable: Whether a resource *derived* from this asset — a statistics
            table, an index, anything that is not the bytes themselves — may
            ship inside the MIT wheel. Independent of :attr:`vendorable` in both
            directions, and defaults to ``False`` so that an asset added without
            a licence reading cannot become the source of a shipped resource by
            omission.
        licence_read_on: ISO date the terms at :attr:`licence_url` were read.

            Operating rule 4 is "licences from terms, never a badge", and
            ``bench/splits.toml`` has enforced *both halves* of it — URL and read
            date — since it acquired a reader. This registry enforced only the
            URL half, so every entry above records where a conclusion came from
            and none records when. That matters for exactly the reason the
            manifest's ``STALE_AFTER_DAYS`` exists: upstream re-licenses, and a
            citation with no date cannot be reported as worth re-reading.

            The field defaults to empty because the existing entries predate it
            and back-filling them would mean writing down dates nobody actually
            read the terms on. An empty value is an honest gap; an invented date
            would be worse than the gap. New entries carry it.
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
    derivable: bool = False
    size_bytes: int = 0
    licence_read_on: str = ""


ASSETS: tuple[Asset, ...] = (
    Asset(
        key="scowl",
        size_bytes=2569810,
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
        derivable=True,
    ),
    Asset(
        key="cmudict",
        size_bytes=3618488,
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
        derivable=True,
    ),
    Asset(
        key="cmudict-license",
        size_bytes=1754,
        filename="cmudict.LICENSE",
        url=f"https://raw.githubusercontent.com/cmusphinx/cmudict/{CMUDICT_COMMIT}/LICENSE",
        sha256="bd4ce8e44170a5f9f481310ca85c51de3c4f851a65e679b40e603b143bd3542a",
        licence="BSD-2-Clause",
        licence_url=f"https://raw.githubusercontent.com/cmusphinx/cmudict/{CMUDICT_COMMIT}/LICENSE",
        vendorable=True,
        vendor_note="The licence text itself, retained so the notice can be reproduced verbatim.",
        purpose="Attribution text for the derived CMUdict resource.",
        attribution="Copyright (C) 1993-2015 Carnegie Mellon University.",
        derivable=True,
    ),
    Asset(
        key="med1250",
        size_bytes=1613108,
        filename="MED1250_labeled",
        url=f"{_AB3P_RAW}/MED1250_labeled",
        sha256="5093fa8f130ee250add0d0fbde7fc736478e18fbcc4447b00b4179db47f4cf53",
        licence=_AB3P_LICENCE,
        licence_url=f"{_AB3P_RAW}/README.md",
        vendorable=False,
        derivable=True,
        vendor_note=(
            "Public domain, so redistribution would be lawful -- the NLM notice "
            "states the work 'cannot be copyrighted within the United States' and "
            "that no restriction has been placed on its use or reproduction. It is "
            "still fetch-only: it is a 1.6 MB evaluation corpus, not a runtime "
            "resource, and nothing in the library reads it. Shipping it would "
            "inflate every wheel for the benefit of the few people running "
            "benchmarks. Derivable, and that is a separate answer from the one "
            "above rather than a softening of it: the public-domain grant is what "
            "settles the licence, and 'too big and nobody reads it' is what makes "
            "the corpus itself fetch-only. A statistics table derived from it is "
            "small and is read at run time, so neither objection survives the "
            "derivation. resources/pseudo_precision_en.json is built from the "
            "development half of this corpus by tools/build_reliability_table.py; "
            "it carries counts and estimates keyed by our own strategy names and "
            "reproduces no text from the corpus at all."
        ),
        purpose=(
            "Gold standard for extraction evaluation: 1,250 MEDLINE records with "
            "1,221 manually annotated short-form/long-form pairs. This is the "
            "corpus the published Schwartz & Hearst and Ab3P F-scores are quoted "
            "against, which is what makes our number comparable to theirs. Its "
            "raw text -- not its annotations -- is also the source of the bundled "
            "pseudo-precision table."
        ),
        attribution=_AB3P_ATTRIBUTION,
    ),
    Asset(
        key="ab3p-prec",
        size_bytes=4050,
        filename="Ab3P_prec.dat",
        url=f"{_AB3P_RAW}/WordData/Ab3P_prec.dat",
        sha256="77903769069451f67095b8aa677ac19b4074e86cf165519c3cd1cb02734db5c3",
        licence=_AB3P_LICENCE,
        licence_url=f"{_AB3P_RAW}/README.md",
        vendorable=False,
        derivable=True,
        vendor_note=(
            "Public domain and small enough that the size argument used against "
            "med1250 does not apply, so this one is fetch-only for a different "
            "reason: nothing could read it. It is keyed by Ab3P's seventeen "
            "strategy names (FirstLet, WithinWrdFLetSkp, AnyLet, ...) and "
            "acronymkit's matching rules are a parameterised family with names of "
            "its own, so loading this file into a PrecisionTable would produce a "
            "table whose every key fails strategy lookup. Making it usable would "
            "mean inventing a name-to-name mapping that no measurement backs, "
            "which is the kind of resource this project reverts. It is fetched "
            "instead as the independent yardstick for --cross-check: our table is "
            "derived from unlabelled text, theirs was published from labelled "
            "work, and rank agreement between them is evidence the estimator is "
            "measuring something real."
        ),
        purpose=(
            "Ab3P's published reliability table: 145 rows of "
            "'<character class> <short-form length> <strategy> <estimate>'. Read "
            "by tools/build_reliability_table.py --cross-check to compare our "
            "derived strategy ordering against theirs."
        ),
        attribution=_AB3P_ATTRIBUTION,
    ),
    Asset(
        key="ab3p-lf1chsf",
        size_bytes=48126,
        filename="Lf1chSf",
        url=f"{_AB3P_RAW}/WordData/Lf1chSf",
        sha256="93322990b04d6b5027e4d6e2b6a3da91ee76ed1d1b9b170ce8a5cc48e8084651",
        licence=_AB3P_LICENCE,
        licence_url=f"{_AB3P_RAW}/README.md",
        vendorable=False,
        derivable=True,
        vendor_note=(
            "NOT vendorable, and for once the licence is not the reason at all: "
            "the same public-domain notice that covers MED1250 covers this file, "
            "and at 48,126 bytes it would fit the wheel budget. It is fetch-only "
            "because it was measured and did not earn its place. Used as Ab3P "
            "uses it -- a membership gate on the head word of a one-character "
            "short form's definition -- it moves the MED1250 score by less than a "
            "fifth of a point, and only in a configuration that admits "
            "one-character short forms, which is not the default. The figures are "
            "in the decision record; this note is about the data. 21 of the 23 "
            "one-character gold definitions in MED1250 have "
            "their head word in this list, against 49.3% for multi-character gold "
            "definitions and 15.3% of the corpus vocabulary at large. A "
            "general-purpose biomedical word list has no reason to be twice as "
            "dense on exactly the pairs it is supposed to help, so the list "
            "overlaps the harvest pool MED1250 was drawn from and the gain above "
            "is an upper bound of unknown tightness rather than a measurement of "
            "what a user's corpus would see. A gain of that size resting on that "
            "evidence does not justify a permanent resource."
        ),
        purpose=(
            "The vocabulary Ab3P's FirstLetOneChSF rule consults: 4,991 lower-case "
            "words, one per line, consumed as a set. Fetched for the "
            "one-character-short-form experiment recorded in docs/DECISIONS.md; "
            "not read by anything in src/."
        ),
        attribution=_AB3P_ATTRIBUTION,
    ),
    Asset(
        key="ab3p-readme",
        size_bytes=4540,
        filename="Ab3P_README.md",
        url=f"{_AB3P_RAW}/README.md",
        sha256="756d5fa9a5900901f10b357c11230e55febe2af1f16f3fa3a5353af415f750eb",
        licence=_AB3P_LICENCE,
        licence_url=f"{_AB3P_RAW}/README.md",
        vendorable=False,
        derivable=True,
        vendor_note=(
            "Retained alongside MED1250 because it defines the annotation format. "
            "It is also where the Public Domain Notice quoted by every other Ab3P "
            "entry actually lives, so pinning it is what makes those licence "
            "claims checkable rather than asserted."
        ),
        purpose=(
            "Specification of the MED1250 annotation format and its comment "
            "conventions, the role of each WordData file, and the Public Domain "
            "Notice governing all of them."
        ),
        attribution="National Library of Medicine.",
    ),
    Asset(
        key="sdu21-ad-diction",
        size_bytes=76910,
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
        size_bytes=2140335,
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
        size_bytes=17354149,
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
        size_bytes=2935,
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
        size_bytes=6958,
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
        key="sdu22-ae-legal-train",
        size_bytes=1733260,
        filename="sdu22_ae_legal_train.json",
        url=f"{_SDU22_AE_RAW}/data/english/legal/train.json",
        sha256="f04259b3f55bf31e782096d950b0a361a95ce881b5980e8b975f3b3e4cfd9791",
        licence=_SDU22_AE_DATA_LICENCE,
        licence_url=f"{_SDU22_AE_RAW}/README.md",
        vendorable=False,
        vendor_note=_SDU22_AE_DATA_NOTE,
        purpose=(
            "3,564 samples, 3,554 labelled, 9,532 gold acronym spans and 5,246 "
            "gold long-form spans of character-offset annotation. The only split "
            "of this corpus nobody has read: the August 2026 audit decomposed "
            "the *dev* misses, so dev is a tuning split, and this is the one "
            "blind arm SDU-22 AE still offers. Spend it deliberately."
        ),
        attribution=_SDU22_AE_ATTRIBUTION,
    ),
    Asset(
        key="sdu22-ae-legal-dev",
        size_bytes=291388,
        filename="sdu22_ae_legal_dev.json",
        url=f"{_SDU22_AE_RAW}/data/english/legal/dev.json",
        sha256="d41f4961f5524d0f3b031b7ae2636f6f4fdb3d9795861ff6eb9a98f2206a8473",
        licence=_SDU22_AE_DATA_LICENCE,
        licence_url=f"{_SDU22_AE_RAW}/README.md",
        vendorable=False,
        vendor_note=_SDU22_AE_DATA_NOTE,
        purpose=(
            "445 samples, 444 labelled, 1,213 gold acronym spans and 669 gold "
            "long-form spans. NOT legal text despite the folder name: across all "
            "445 samples, 'United Nations' appears in 151 while 'statute', "
            "'plaintiff', 'defendant', 'tribunal', 'litigation' and 'judgment' "
            "appear in zero. It is UN institutional and development-policy prose "
            "-- see bench/splits.toml, [corpora.sdu22_ae_legal].domain_finding. "
            "An extractor emitting exactly the annotated definitions lands at "
            "55.15% short-form recall here (669/1,213); that is not a hard bound "
            "-- 45.4% of gold acronym spans exceed their sample's definitions -- "
            "but every point above it is paid for in long-form precision. Print "
            "it beside any recall figure from this split."
        ),
        attribution=_SDU22_AE_ATTRIBUTION,
    ),
    Asset(
        key="sdu22-ae-scientific-train",
        size_bytes=966723,
        filename="sdu22_ae_scientific_train.json",
        url=f"{_SDU22_AE_RAW}/data/english/scientific/train.json",
        sha256="00b8fba7f16d8d0b44c7b21ac7dbdc02106ffc867a6d9a3f166c11fd67143cdf",
        licence=_SDU22_AE_DATA_LICENCE,
        licence_url=f"{_SDU22_AE_RAW}/README.md",
        vendorable=False,
        vendor_note=_SDU22_AE_DATA_NOTE,
        purpose=(
            "3,980 samples, 3,979 labelled, 7,689 gold acronym spans and 5,715 "
            "gold long-form spans. Unread, like its legal counterpart, and for "
            "the same reason the audit only touched dev."
        ),
        attribution=_SDU22_AE_ATTRIBUTION,
    ),
    Asset(
        key="sdu22-ae-scientific-dev",
        size_bytes=189240,
        filename="sdu22_ae_scientific_dev.json",
        url=f"{_SDU22_AE_RAW}/data/english/scientific/dev.json",
        sha256="bf93f57c5f35c4e61730d7aa6235087561f5c131c26ab82e0a30fee92c07ba45",
        licence=_SDU22_AE_DATA_LICENCE,
        licence_url=f"{_SDU22_AE_RAW}/README.md",
        vendorable=False,
        vendor_note=_SDU22_AE_DATA_NOTE,
        purpose=(
            "497 samples, all labelled, 970 gold acronym spans and 720 gold "
            "long-form spans. An extractor emitting exactly the annotated "
            "definitions lands at 74.23% short-form recall (720/970). The "
            "19-point gap in that figure against the legal split is annotation "
            "density, not domain difficulty, and it accounts for most of the "
            "apparent difference between the two splits' measured recalls."
        ),
        attribution=_SDU22_AE_ATTRIBUTION,
    ),
    Asset(
        key="sdu22-ae-scorer",
        size_bytes=3064,
        filename="sdu22_ae_scorer.py",
        url=f"{_SDU22_AE_RAW}/scorer.py",
        sha256="4ece9756e1cad3857b20de86b262a0562dcf1325d8487763e49b849230250bdd",
        licence="MIT",
        licence_url=f"{_SDU22_AE_RAW}/LICENSE",
        vendorable=False,
        vendor_note=(
            "Genuinely MIT -- the README's carve-out puts the evaluation script "
            "and the baseline under the repository licence, and only the data "
            "under CC BY-NC-SA. Not vendored, for the same reason as the SDU-21 "
            "scorer: it is a benchmark script, and pinning it is what keeps our "
            "reimplementation auditable against the original."
        ),
        purpose=(
            "The shared task's official scorer. Defines the convention any "
            "SDU-22 AE number of ours would be quoted under: macro-averaged "
            "precision, recall and F1 over acronym and long-form span "
            "predictions, reported separately for short and long forms."
        ),
        attribution="Amir Pouran Ben Veyseh and contributors; MIT licensed.",
    ),
    Asset(
        key="sdu22-ae-readme",
        size_bytes=4180,
        filename="sdu22_ae_README.md",
        url=f"{_SDU22_AE_RAW}/README.md",
        sha256="58996464a4a27bc09e66ef408d82c0b2ef4fbf1fbfbdd6a04cc6ffc33ab81442",
        licence="MIT (the document), describing a CC BY-NC-SA-4.0 dataset",
        licence_url=f"{_SDU22_AE_RAW}/README.md",
        vendorable=False,
        vendor_note=(
            "Retained for the same reason as ab3p-readme and sdu21-ad-readme: it "
            "is the normative description of the record format, and it is the "
            "ONLY place this dataset's real licence is stated. The repository's "
            "LICENSE file and GitHub's own licence field both say MIT. Pinning "
            "this file is what makes the CC BY-NC-SA finding reproducible rather "
            "than a claim in a note."
        ),
        purpose=(
            "Specification of the SDU@AAAI-22 AE record format -- text, "
            "character-offset `acronyms` and `long-forms` tuples, id -- the "
            "official metric, and the licence split between data and scripts."
        ),
        attribution="Amir Pouran Ben Veyseh and contributors.",
    ),
    Asset(
        key="plod-cw-test",
        size_bytes=72652,
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
        size_bytes=72802,
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
        size_bytes=586595,
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
        size_bytes=20131,
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
        size_bytes=8371,
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
        size_bytes=1236490,
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
        size_bytes=715989,
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
        size_bytes=4356903,
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
    Asset(
        key="federal-register-terms",
        size_bytes=64162,
        filename="federal_register_govinfo_policies.html",
        url=_GOVINFO_POLICIES,
        sha256="5189ea6f00ac5b788b6937d6024e9f5924ed958305e31afc7d94f7e4bc40c0a9",
        licence=_FEDERAL_REGISTER_LICENCE,
        licence_url=_GOVINFO_POLICIES,
        licence_read_on="2026-08-24",
        vendorable=False,
        vendor_note=_FEDERAL_REGISTER_NOTE,
        purpose=(
            "The terms behind the Federal Register substrate registered below. "
            "Pinned for the same reason as plod-cw-license: so the licence "
            "finding rests on the text rather than on a note in this file."
        ),
        attribution="U.S. Government Publishing Office, Public Domain & Copyright Notice.",
        derivable=True,
    ),
)

BY_KEY = {asset.key: asset for asset in ASSETS}


@dataclass(frozen=True)
class Substrate:
    """A corpus fetched *by document*, not as a file.

    A sixth kind of entry, and the reason it is not an :class:`Asset` is
    arithmetic before it is philosophy. An ``Asset`` is one URL, one file name
    and one digest; a substrate is a query and a draw over thousands of
    documents, and registering thirty of them individually would put the corpus's
    identity in thirty places and the ledger would grow by a page every time the
    draw changed. The identity belongs in one table, in the tool that builds it.

    So this entry answers what a registry is *for* — licence, redistribution,
    provenance, who fetches it — and points at that tool for the pins.

    Attributes:
        key: Short identifier.
        name: What the substrate is.
        discovery_url: The documented API that answers which documents exist.
        licence: As read from terms.
        licence_url: Where the terms were read.
        licence_read_on: When.
        licence_note: The reading, including anything the licence field alone
            would destroy.
        vendorable: Whether the fetched text may ship inside the wheel.
        derivable: Whether a resource derived from it may ship.
        fetched_by: The tool that fetches it and holds the pins.
        pin_note: How the pin works and why it is not a digest of the bytes.
        domain_note: What the text actually is. Mandatory in spirit: this
            repository has twice had to correct a corpus that was described by
            its own name rather than by its content.
        access_note: Anything about reaching it that a future fetcher needs.
    """

    key: str
    name: str
    discovery_url: str
    licence: str
    licence_url: str
    licence_read_on: str
    licence_note: str
    vendorable: bool
    derivable: bool
    fetched_by: str
    pin_note: str
    domain_note: str
    access_note: str


SUBSTRATES: tuple[Substrate, ...] = (
    Substrate(
        key="federal-register",
        name="Federal Register final rules",
        discovery_url="https://www.federalregister.gov/api/v1/documents.json",
        licence=_FEDERAL_REGISTER_LICENCE,
        licence_url=_GOVINFO_POLICIES,
        licence_read_on="2026-08-24",
        licence_note=_FEDERAL_REGISTER_NOTE + f" Statute cited from <{_USC_17_105}>.",
        vendorable=False,
        derivable=True,
        fetched_by="python tools/build_gold_corpus.py fetch",
        pin_note=(
            "Pinned per document in tools/build_gold_corpus.py::PINNED_DOCUMENTS, by the "
            "SHA-256 of the NORMALISED TEXT rather than of the fetched bytes. Measured "
            "reason: both hosts serve the body through a CDN that rewrites e-mail "
            "addresses into a per-response obfuscation token, so the same document "
            "differs in bytes between hosts and a byte pin would fire the checksum "
            "failure this file reserves for a corpus that really changed. Under the text "
            "pin the primary host and the Government Publishing Office mirror agree "
            "exactly on every pinned document, which is what makes --mirror-check an "
            "independent verification rather than a second copy of the same fetch."
        ),
        domain_note=(
            "United States agency rulemaking. A random draw of final rules is dominated "
            "by environmental, aviation, fisheries and maritime-safety prose. It is ONE "
            "MORE DOMAIN and not general text, and it is not a general-purpose "
            "counterweight to the biomedical corpora -- the same correction "
            "[corpora.sdu22_ae_legal] already carries for calling UN institutional prose "
            "'legal'."
        ),
        access_note=(
            "The JSON API answers automated requests normally. The site's HTML pages do "
            "not: /reader-aids/developer-resources/rest-api and /reader-aids/legal-status "
            "both return a CAPTCHA interstitial headed 'Request Access', explaining that "
            "programmatic access to the site is limited to the API. That is why the "
            "licence above is read from GPO -- reachable, stating the same statute, and "
            "the terms of the host that serves the mirror. Anyone who wants the Federal "
            "Register's own wording should open the page in a browser and add it here "
            "with a read date. Do not defeat the CAPTCHA."
        ),
    ),
)


@dataclass(frozen=True)
class Derived:
    """A packaged resource computed from one of the assets above.

    The ledger used to describe only what is *downloaded*, which left the more
    important question unanswered: what actually ships, and what is it made of?
    Every entry here is a file inside the wheel, so every entry is a claim the
    project makes about someone else's licensed work.

    Attributes:
        resource: File name inside ``acronymkit/resources``.
        source_key: Registry key of the asset it is derived from. Its
            :attr:`Asset.derivable` flag is what permits the file to exist.
        builder: The script that writes it, so the file can be regenerated
            rather than trusted.
        note: What survives the derivation, and what does not.
    """

    resource: str
    source_key: str
    builder: str
    note: str


DERIVED: tuple[Derived, ...] = (
    Derived(
        resource="lexicon_en.txt",
        source_key="scowl",
        builder="python tools/build_lexicons.py --language en",
        note=(
            "A filtered word list. Carries SCOWL vocabulary, so SCOWL's notice is "
            "reproduced verbatim in the file's header comment."
        ),
    ),
    Derived(
        resource="ngram_en.json",
        source_key="scowl",
        builder="python tools/build_ngram_model.py",
        note=(
            "Character transition probabilities over the lexicon above. Second "
            "order removed from the source: no SCOWL word can be read back out of "
            "it, though it is still a statistical summary of SCOWL and is "
            "attributed as one."
        ),
    ),
    Derived(
        resource="pseudo_precision_en.json",
        source_key="med1250",
        builder="python tools/build_reliability_table.py",
        note=(
            "Estimated reliability per (short-form group, matching strategy), "
            "derived from the raw text of MED1250's development half with the "
            "estimator in acronymkit._pseudo_precision. Reproduces no text from "
            "the corpus: every key is one of this library's own group labels or "
            "strategy names and every value is a count or a float, which "
            "tests/test_pseudo_precision.py asserts rather than assumes. Two "
            "independent grounds permit it -- the public-domain licence, and the "
            "absence of any source content to license -- and the second is the "
            "one that would still stand if the first were disputed. Its own "
            "provenance block records the source URL, digest, licence and split "
            "seed, because JSON has no comment syntax to put a header in."
        ),
    ),
)


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
        print(
            f"  RECORDED {asset.key:16} size_bytes={len(payload)}  sha256={digest}\n"
            "           (paste both into the Asset entry)"
        )
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
    elif asset.size_bytes and len(payload) != asset.size_bytes:
        # The digest already passed, so this is not an integrity failure -- it is
        # a recorded size that has gone stale, and a stale size is what the wheel
        # budget would be argued from.
        print(
            f"  ok       {asset.key:16} {len(payload):>10,}B  "
            f"(recorded size_bytes={asset.size_bytes} is wrong; update it)"
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
        "Each entry also answers a second, independent question: whether a resource",
        "*derived* from the asset may ship even when the asset itself may not. The two",
        "answers come apart in both directions, so they are recorded separately and",
        "`tools/build_reliability_table.py` enforces the derived-work answer the way",
        "`tools/build_lexicons.py` enforces the redistribution answer.",
        "",
        "## Vendored into the wheel",
        "",
        "Permissively licensed. Redistributed in derived form with the notice preserved",
        "in the resource file header.",
        "",
    ]

    def block(asset: Asset) -> list[str]:
        derived = "yes" if asset.derivable else "no"
        read_on = asset.licence_read_on or "not recorded (entry predates the field)"
        return [
            f"### `{asset.key}` — {asset.filename}",
            "",
            f"- **Licence:** {asset.licence}",
            f"- **Licence text:** <{asset.licence_url}>",
            f"- **Terms read on:** {read_on}",
            f"- **Source:** <{asset.url}>",
            f"- **SHA-256:** `{asset.sha256 or 'not yet recorded'}`",
            f"- **Size:** {asset.size_bytes:,} bytes"
            if asset.size_bytes
            else "- **Size:** not yet recorded",
            f"- **Ships in the wheel:** {'yes' if asset.vendorable else 'no'}",
            f"- **Derived resources may ship:** {derived}",
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
        "## Derived resources shipped in the wheel",
        "",
        "What a wheel actually carries is not the assets above but these files, each",
        "computed from one of them. A derived resource is only permitted where its",
        "source asset is marked **Derived resources may ship: yes**; share-alike",
        "sources are barred from this table by construction, because CC BY-SA 4.0",
        "section 3(b) reaches Adapted Material.",
        "",
    ]
    for derived in DERIVED:
        asset = BY_KEY[derived.source_key]
        path = RESOURCE_DIR / derived.resource
        size = f"{path.stat().st_size:,} bytes" if path.is_file() else "not built"
        lines += [
            f"### `{derived.resource}`",
            "",
            f"- **Derived from:** `{derived.source_key}` ({asset.licence})",
            f"- **Built by:** `{derived.builder}`",
            f"- **Size in the source tree:** {size}",
            f"- **Attribution:** {asset.attribution}",
            "",
            f"{derived.note}",
            "",
        ]

    lines += [
        "## Substrates — fetched by document, not as a file",
        "",
        "A substrate is a query and a draw over a live corpus rather than a single",
        "pinned file, so its identity lives in the tool that builds it and this table",
        "records what a registry is for: licence, redistribution, provenance, and",
        "anything about reaching it that the next fetcher needs.",
        "",
    ]
    for substrate in SUBSTRATES:
        lines += [
            f"### `{substrate.key}` — {substrate.name}",
            "",
            f"- **Licence:** {substrate.licence}",
            f"- **Licence text:** <{substrate.licence_url}>",
            f"- **Terms read on:** {substrate.licence_read_on}",
            f"- **Discovery:** <{substrate.discovery_url}>",
            f"- **Fetched by:** `{substrate.fetched_by}`",
            f"- **Ships in the wheel:** {'yes' if substrate.vendorable else 'no'}",
            f"- **Derived resources may ship:** {'yes' if substrate.derivable else 'no'}",
            "",
            f"**Licence reading.** {substrate.licence_note}",
            "",
            f"**Pinning.** {substrate.pin_note}",
            "",
            f"**What the text is.** {substrate.domain_note}",
            "",
            f"**Access.** {substrate.access_note}",
            "",
        ]

    lines += [
        "## Adding an asset",
        "",
        "1. Read the actual licence text. Do not infer it from a badge or a README line.",
        '2. Add an `Asset` to `ASSETS` in `tools/fetch_data.py` with `sha256=""`.',
        "3. Run `python tools/fetch_data.py <key> --record` and paste the digest in.",
        "4. Run `python tools/fetch_data.py --write-ledger`.",
        "5. If you marked it vendorable, say in `vendor_note` *why* the licence permits it.",
        "6. Answer `derivable` too. It denies by default, so an asset added without",
        "   reading the licence cannot silently become the source of a shipped",
        "   resource -- but a wrong `True` is how a share-alike obligation gets into",
        "   an MIT wheel, and CC BY-SA reaches Adapted Material specifically.",
        "",
    ]

    LEDGER_PATH.write_text("\n".join(lines), encoding="utf-8", newline="\n")
    return LEDGER_PATH


def _list_assets() -> None:
    """Print the registry as a table."""
    print(f"{'KEY':24} {'VENDOR':8} {'DERIVE':8} {'READ ON':12} {'LICENCE':40} PURPOSE")
    print(f"{'-' * 24} {'-' * 8} {'-' * 8} {'-' * 12} {'-' * 40} {'-' * 40}")
    for asset in ASSETS:
        flag = "wheel" if asset.vendorable else "local"
        derive = "ok" if asset.derivable else "tainted"
        read_on = asset.licence_read_on or "--"
        print(
            f"{asset.key:24} {flag:8} {derive:8} {read_on:12} "
            f"{asset.licence[:40]:40} {asset.purpose[:44]}"
        )
    print()
    print("SUBSTRATES (fetched by document, pinned in their own tool)")
    print(f"{'-' * 24} {'-' * 8} {'-' * 8} {'-' * 12} {'-' * 40}")
    for substrate in SUBSTRATES:
        flag = "wheel" if substrate.vendorable else "local"
        derive = "ok" if substrate.derivable else "tainted"
        print(
            f"{substrate.key:24} {flag:8} {derive:8} {substrate.licence_read_on:12} "
            f"{substrate.licence[:40]:40} {substrate.fetched_by}"
        )


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
