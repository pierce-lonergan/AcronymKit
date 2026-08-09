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
