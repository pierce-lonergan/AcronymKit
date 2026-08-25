#!/usr/bin/env python3
"""Build a held-out extraction reference set from the Federal Register.

What this is for
----------------
``headline_capable("extraction")`` returns nothing. D-048 established why, and
the reason is structural rather than administrative: an extraction gold record
asserts an **edge** -- this short form and that long form stand in a definition
relation -- and every held-out corpus in this repository annotates *vertices*.
PLOD and SDU-22 tag acronym occurrences and long-form occurrences and never say
which belongs to which; a system that mis-pairs three quarters of PLOD's gold
still scores a perfect span number, because the type carrying a prediction into
the span scorer has no slot for the edge. So the flagship claim is an edge claim
and nothing held out in this project contains edges.

This module is the pipeline for the corpus that would. It is **not** the corpus,
and the distinction is the whole design:

* it fetches and pins a re-derivable population of Federal Register rules;
* it pools candidate edges from three independent proposers and records, per
  candidate, which of them proposed it;
* it enumerates the surfaces *no* proposer touched and samples them uniformly,
  so the false-negative rate is estimable rather than assumed; and
* it emits a worklist for a human and reads adjudications back.

It does not adjudicate. That refusal is load-bearing and is enforced in code by
:func:`freeze`, which will not write an artifact that claims more than its
adjudicator count supports.

Why the Federal Register, and what it is not
--------------------------------------------
17 U.S.C. 105 puts the text in the public domain, the JSON API is documented and
stable, and the bodies are served as plain text by two independent hosts. Those
are the reasons. The reason it is *not* a general-text corpus is equally
important and must travel with every figure taken from it: the Federal Register
is agency rulemaking, and a random draw of rules is dominated by environmental,
aviation, fisheries and maritime-safety prose. It is **one more domain**, exactly
as ``[corpora.sdu22_ae_legal]`` is one more genre. It is not "general text", it
is not a counterweight to the biomedical corpora in any broad sense, and the
first person to describe it as one will have repeated the PLOD mistake with a
different corpus.

One premise this pipeline was funded on did not survive contact
---------------------------------------------------------------
The proposal for this work said the Federal Register's rules "routinely carry
their own abbreviation legends, so the arbiter is the agency rather than us".
That is half true and the half that fails is the operative half. Rules do carry
legends -- a ``Table of Abbreviations`` block near the top of the SUPPLEMENTARY
INFORMATION section -- and where one is present it really is agency-asserted
evidence for an edge, which is worth more than anything this project could
assert about its own output. But:

* legends are present in a **minority** of rules, not routinely, and
* their surface syntax is ``SF LF`` or ``SF--LF``, never ``SF = LF``.

The second point is the one with teeth. ``AbbreviationExtractor(legend_syntax=
True)`` reads exactly ``SF = LF``; run over this substrate it changes not one
proposal. So the legend cannot be harvested by the shipped legend reader, and a
plan that assumed it could was costing an arbiter it does not have. What the
legend *can* do is carry corroborating evidence into the worklist, which is what
:func:`legend_entries` is for -- evidence for a human to weigh, never a verdict.
The measurements behind both statements are in this workstream's report; nothing
here quotes a figure, because no runner has saved one.

The trap this module is built around
------------------------------------
``bench/splits.toml`` already records the rule: *a gold standard I partly
invented cannot adjudicate my own system.* The author of the extractor being
measured is the worst available adjudicator, and a machine pass by that author
over the pooled union is not annotation -- it is the extractor grading itself
through a slower interface. So:

* the worklist carries **no proposed verdict**, only evidence;
* :data:`VERDICTS` has an explicit ``undecidable`` value, because an adjudication
  scheme with no way to decline forces a guess and then counts it;
* :func:`freeze` refuses to emit ``role = "held_out"``, refuses the word "gold",
  and stamps ``adjudicator_count`` into the artifact where a reader trips over
  it; and
* the honest label for a one-adjudicator artifact is **single-annotator
  reference set**, which ``tools/splits.py``'s :data:`ROLES` cannot currently
  express. That gap is reported rather than papered over by filing it as
  ``held_out``.

Pinning, and why the digest is over text rather than bytes
-----------------------------------------------------------
``tools/fetch_data.py`` pins every asset by the SHA-256 of the bytes it fetched,
and that is right for a file in a git repository. It is wrong here, measured:
the Federal Register serves its bodies through a CDN that rewrites ``mailto:``
links into per-response obfuscation tokens, so two fetches of the same document
from two hosts differ in bytes while being the same document. A byte pin would
fire the loud checksum failure ``fetch_data.py`` reserves for a corpus that
actually changed.

The corpus is the *text*, so the pin is over the text: :func:`normalise_body`
unwraps the ``<pre>``, drops markup, neutralises the obfuscated addresses to a
constant, and normalises line endings; :func:`text_digest` hashes the result.
Under that pin the primary host and the mirror agree exactly, which is what makes
``--mirror-check`` a real independent verification rather than a second copy of
the same fetch.

Usage
-----
::

    python tools/build_gold_corpus.py select            # re-derive the pin table
    python tools/build_gold_corpus.py fetch             # fetch + verify the pins
    python tools/build_gold_corpus.py fetch --mirror-check
    python tools/build_gold_corpus.py pool --interpreter C:/akbench/Scripts/python.exe
    python tools/build_gold_corpus.py worklist --seed 20260824
    python tools/build_gold_corpus.py ingest data/federal_register/adjudications.jsonl
    python tools/build_gold_corpus.py freeze data/federal_register/adjudications.jsonl

Nothing here is imported by the library, and nothing here is imported by a bench
runner. The standard library is the only dependency of every stage except
``pool``, which imports ``acronymkit`` from ``src/`` for one of its three
proposers and shells out to a foreign interpreter for another.
"""

from __future__ import annotations

import argparse
import datetime as _datetime
import hashlib
import html
import json
import random
import re
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = REPO_ROOT / "data"
CORPUS_DIR = DATA_DIR / "federal_register"
BODY_DIR = CORPUS_DIR / "bodies"

USER_AGENT = "acronymkit-bench/0.3.0 (+https://github.com/pierce-lonergan/acronymkit)"

# ---------------------------------------------------------------------------
# the substrate
# ---------------------------------------------------------------------------
#: The documented JSON API. Discovery only: this endpoint answers *which*
#: documents exist, and the bodies come from the URLs it hands back.
FEDERAL_REGISTER_API = "https://www.federalregister.gov/api/v1/documents.json"

#: Body, primary host. The API returns this as ``raw_text_url``; it is templated
#: here so a pinned document can be re-fetched without a second API round trip.
FEDERAL_REGISTER_BODY = (
    "https://www.federalregister.gov/documents/full_text/text/{year}/{month}/{day}/{document}.txt"
)

#: Body, independent mirror. The Government Publishing Office serves the same
#: document from its own infrastructure. Fetching both and comparing the *text*
#: digest is the only check available here that a body was not altered in
#: transit, since neither host publishes a checksum.
GOVINFO_MIRROR = "https://www.govinfo.gov/content/pkg/FR-{date}/html/{document}.htm"

#: Operating rule 4: the licence comes from terms, never from a badge.
#:
#: Two documents, because the grant and the caveat come from different places and
#: only one of them is a statute. 17 U.S.C. 105 is the grant. GPO's Public Domain
#: & Copyright Notice is where the *operative* caveat is written down, and it is
#: the reason this entry does not simply say "public domain": Government
#: publications may reproduce third-party copyrighted material with permission,
#: and publication in a Government document does not extend that permission to
#: anyone else.
#:
#: Reading the caveat changes what this pipeline may do, which is why it is here
#: rather than in a comment. A Federal Register rule frequently incorporates
#: material by reference -- an ASTM or SAE standard, a manufacturer's service
#: bulletin -- and quotes from it. The corpus this tool builds holds short forms,
#: long forms and short evidence windows, so the exposure is small; it is not
#: zero, and it is the reason :data:`VENDORABLE` is ``False``.
LICENCE = "Public domain (United States Government Work, 17 U.S.C. 105)"
LICENCE_URL = "https://www.govinfo.gov/about/policies"
LICENCE_READ_ON = "2026-08-24"
LICENCE_STATUTE_URL = (
    "https://uscode.house.gov/view.xhtml"
    "?req=granuleid:USC-prelim-title17-section105&num=0&edition=prelim"
)

#: The API's own terms page could not be read from this host, and that is
#: recorded rather than worked around. ``federalregister.gov``'s HTML pages --
#: including ``/reader-aids/developer-resources/rest-api`` and
#: ``/reader-aids/legal-status`` -- answer an automated request with a CAPTCHA
#: interstitial headed "Request Access", explaining that programmatic access to
#: the site is limited to the API. The API itself answers normally.
#:
#: A CAPTCHA is a statement that a human should be reading this page, and it is
#: not this tool's to defeat. So the licence above is read from GPO's terms,
#: which are reachable, state the same statute, and are the terms of the host
#: that serves the mirror. Anyone who wants the Federal Register's own wording
#: should open the page in a browser and add it here with a read date.
LICENCE_UNREADABLE_FROM_THIS_HOST = (
    "https://www.federalregister.gov/reader-aids/developer-resources/rest-api"
)

#: Whether the fetched bodies may ship inside the wheel. They may not, and the
#: reason is size and irrelevance before it is licensing: no code in the library
#: reads a corpus, and every wheel would pay for the few people running
#: benchmarks. The incorporated-by-reference caveat above is the second reason.
VENDORABLE = False

#: What the text actually is. Repeated into every artifact this tool writes,
#: because a domain label that lives only in a docstring is a domain label that
#: does not travel with the number.
DOMAIN = (
    "United States agency rulemaking (Federal Register final rules). A random "
    "draw is dominated by environmental, aviation, fisheries and maritime-safety "
    "prose. One more domain, not general text."
)


# ---------------------------------------------------------------------------
# selection
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class Selection:
    """The query and the draw that define which documents are in the population.

    Every field is part of the corpus's identity. Changing one produces a
    different corpus, which is why :func:`select` compares its result against
    :data:`PINNED_DOCUMENTS` and reports drift instead of quietly re-pinning.

    Attributes:
        document_type: The Federal Register ``type`` filter. ``"RULE"`` is final
            rules; proposed rules and notices are different genres with different
            house styles and are deliberately not mixed in.
        published_from: Inclusive lower bound on publication date.
        published_to: Inclusive upper bound.
        order: The API's sort. Fixed so the population list is deterministic
            before the draw is applied to it.
        seed: Seed for the uniform draw over the ordered population.
        size: How many documents the draw takes.
    """

    document_type: str
    published_from: str
    published_to: str
    order: str
    seed: int
    size: int

    def query(self) -> List[Tuple[str, str]]:
        """The API query string, as ordered pairs.

        Ordered rather than a dict so the encoded URL is byte-stable, which is
        what lets the request itself be quoted in a report.
        """
        pairs = [
            ("per_page", "100"),
            ("order", self.order),
            ("conditions[type][]", self.document_type),
            ("conditions[publication_date][gte]", self.published_from),
            ("conditions[publication_date][lte]", self.published_to),
        ]
        for name in ("document_number", "title", "publication_date", "raw_text_url", "agencies"):
            pairs.append(("fields[]", name))
        return pairs


#: The pilot population. Deliberately modest: this is a pilot, and a pilot whose
#: corpus is large enough to be tempting to adjudicate at scale is not a pilot.
SELECTION = Selection(
    document_type="RULE",
    published_from="2024-01-01",
    published_to="2024-03-31",
    order="oldest",
    seed=20260824,
    size=30,
)


@dataclass(frozen=True)
class PinnedDocument:
    """One document in the frozen population.

    Attributes:
        document_number: The Federal Register document number, e.g.
            ``"2024-04274"``. This is the stable public identifier and is what a
            reader would type into the site.
        publication_date: ISO date, needed to build both body URLs.
        text_sha256: SHA-256 of :func:`normalise_body` applied to the fetched
            body. **Not** a digest of the bytes -- see the module docstring for
            the measurement that forced that choice.
        text_length: Length of the normalised text in characters. Recorded
            beside the digest so a corpus-size argument does not require the
            corpus to be on disk.
    """

    document_number: str
    publication_date: str
    text_sha256: str
    text_length: int


#: The frozen population, re-derivable by ``select`` and verifiable by ``fetch``.
#:
#: This table -- not the query above -- is the corpus. The query says how the
#: draw was taken; the table says what it took, so a future change to the API's
#: result set is a reported drift rather than a silently different corpus.
PINNED_DOCUMENTS: Tuple[PinnedDocument, ...] = (
    PinnedDocument(
        "2023-28849",
        "2024-01-03",
        "fe0929a40b5aa0866a4d277631f927ed47482269450020d9ea732646d2fc21e2",
        15762,
    ),
    PinnedDocument(
        "2023-28855",
        "2024-01-03",
        "72575928cc944d38999a6ddc97470b6f52b8b0b7ccd839ae23f9db5091310c34",
        14805,
    ),
    PinnedDocument(
        "2024-00091",
        "2024-01-11",
        "d6fbbff7de27138f851f8e835a93dbb6d20142c08724a06405a7fd0752c3eb9d",
        240788,
    ),
    PinnedDocument(
        "2024-00300",
        "2024-01-09",
        "ffd39c56e7508504b50417b41cafe515819aedc808d66e30af10eebe504a6ca2",
        22781,
    ),
    PinnedDocument(
        "2024-00339",
        "2024-01-10",
        "d3b6d6392c93d0053f786826c1242c093e5a368d0907bd7cbed5cd88fd7c3d3c",
        7567,
    ),
    PinnedDocument(
        "2024-00428",
        "2024-01-16",
        "636c7bf6cc6651fd2429373424dc785038a9e75bbd76e068f11158cc6ceffb9b",
        87330,
    ),
    PinnedDocument(
        "2024-01218",
        "2024-01-23",
        "6f1918160243f51e23bd2e6c460e770843813f07ebb238fe811b16725f9668bf",
        16665,
    ),
    PinnedDocument(
        "2024-01337",
        "2024-01-30",
        "3201acc748d777a5cf7a304c17b6d9c4b63d9f3c1cb6492cbbf6e18a80f1c873",
        157541,
    ),
    PinnedDocument(
        "2024-01449",
        "2024-01-25",
        "500c24cb33b6119d18490fac4732d2c6528c48faa8603d1ed96d8d93f4e2d048",
        23718,
    ),
    PinnedDocument(
        "2024-01770",
        "2024-02-02",
        "fca175dc24f4c22f3c228abdd86fcba101b1398714ef0fed705fcbb2bba70067",
        304369,
    ),
    PinnedDocument(
        "2024-02008",
        "2024-02-14",
        "1932f95121672ff1d728716d1dc53768b3bdec2618d5f5b8499b2e4a286d799b",
        652096,
    ),
    PinnedDocument(
        "2024-02631",
        "2024-02-09",
        "1f4b0946cb163f614f7b96f488cd251511c36385e78ad2dd5142c8ea8e9696f7",
        69784,
    ),
    PinnedDocument(
        "2024-02659",
        "2024-02-09",
        "206d28151f49c0531446860ef266fb0c5fdea249454885c84b6cc9eb32423986",
        15969,
    ),
    PinnedDocument(
        "2024-03407",
        "2024-02-21",
        "10ff1f5194867a5994ba5d97ea744b89ef1fe21f3013ad3c925c1e756b2bed8b",
        15236,
    ),
    PinnedDocument(
        "2024-03562",
        "2024-02-22",
        "3b5d1476ad3c18e0f1dbbc6dc5e464d51d499d7d94e44717d9b58a3913fe8747",
        14537,
    ),
    PinnedDocument(
        "2024-03957",
        "2024-03-01",
        "4e5f9ee65153179ccafab6709c56cc4593f83bcf3eb748e3ab59fc5ffbdd4682",
        7339,
    ),
    PinnedDocument(
        "2024-03969",
        "2024-02-27",
        "6d82b2e31145539c1d7156d3086f7ea6044609b5ad62cbe7c17a06355681bd06",
        149025,
    ),
    PinnedDocument(
        "2024-04236",
        "2024-03-01",
        "da79f649946999e648feb2a658dac4a6b178de6502a53ac3d37a5ad90ff67b50",
        20684,
    ),
    PinnedDocument(
        "2024-04274",
        "2024-02-29",
        "a258cf80518e346b0c8a2b737320f7132a82ad240d102dc11a0e76437c431821",
        12916,
    ),
    PinnedDocument(
        "2024-04275",
        "2024-03-04",
        "7bc99cf8f6d9832ccb08768a9595839da3a682d80a458ac69971eae5bb5b0e7b",
        168037,
    ),
    PinnedDocument(
        "2024-04364",
        "2024-03-04",
        "bf3c788328789da0c0b72b199b95b374478ee927ffc8bee4077b5318d5f400a5",
        11306,
    ),
    PinnedDocument(
        "2024-04372",
        "2024-03-01",
        "b9964a644841c1f850e4a40ed3ee5f80ba8a69896354cfa80bb2ec6bde7de492",
        100249,
    ),
    PinnedDocument(
        "2024-04380",
        "2024-03-04",
        "b3c026210d8cd0a18b8c3301596b47412c0f883ff844bb9a6e2caf6a7c6a3e42",
        73770,
    ),
    PinnedDocument(
        "2024-04557",
        "2024-03-05",
        "4b519e6bfb14c294ba047a6117c07e800cabfc4efa2a6b4eef1041d85137e6bd",
        16594,
    ),
    PinnedDocument(
        "2024-04851",
        "2024-03-07",
        "23fa47e835b193c39f37a17024fdb1076e6a833a547aa9032be4d6412de802d9",
        3357,
    ),
    PinnedDocument(
        "2024-05249",
        "2024-03-13",
        "ead1cdebca62beb3d0b4d38e6e9821ea497cf82b6fde7a50a5a8473737589a99",
        5853,
    ),
    PinnedDocument(
        "2024-05267",
        "2024-03-13",
        "f41edeceb1e44a6ac30627de587d24257f739b6b76f9e6161fd9cbc662e281c7",
        45288,
    ),
    PinnedDocument(
        "2024-05475",
        "2024-03-15",
        "1bc69132e2a5a1dfd69a21f4ac66d7196daafee86ba8e7c05796438487700c1c",
        13835,
    ),
    PinnedDocument(
        "2024-05512",
        "2024-03-15",
        "38b05da9331d00556d0b1e889a3d4c0cca7cf41d264027ea074d10f2be2c1acc",
        9552,
    ),
    PinnedDocument(
        "2024-06436",
        "2024-03-27",
        "6a4e86e6e02baa89a43f28802b954f3e081e9c21155eef99c9c80d543727a695",
        13584,
    ),
)


# ---------------------------------------------------------------------------
# text
# ---------------------------------------------------------------------------
#: The obfuscated-address markup both hosts inject, and the constant it collapses
#: to. The token after ``#`` is a per-response cipher of the real address, so it
#: differs between the two hosts and would defeat any digest taken over bytes.
#: Collapsing it is not cosmetic: it is what makes the mirror check meaningful.
_CF_SPAN = re.compile(r"(?is)<span[^>]*__cf_email__[^>]*>.*?</span>")
_CF_LINK = re.compile(r"(?is)<a\s[^>]*/cdn-cgi/l/email-protection[^>]*>(.*?)</a>")
_EMAIL_PLACEHOLDER = "[email protected]"

_PRE_BLOCK = re.compile(r"(?is)<pre>(.*?)</pre>")
_ANCHOR = re.compile(r"(?is)<a\s[^>]*>(.*?)</a>")
_ANY_TAG = re.compile(r"(?s)<[^>]+>")


def _write_lf(path: Path, text: str) -> None:
    """Write ``text`` with LF endings, on every interpreter this package supports.

    ``Path.write_text`` grew a ``newline`` parameter in 3.10 and ``requires-python``
    is ``>=3.9``, so the obvious spelling type-checks, passes every local gate and
    fails only on the 3.9 matrix job -- which is how it reached CI. Endings are not
    cosmetic here: a pinned digest is taken over the normalised text, so a CRLF
    checkout writing CRLF would change every hash and make the whole corpus look
    un-refetchable.
    """
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(text)


def normalise_body(raw: bytes) -> str:
    """Turn a fetched Federal Register body into the text the corpus is made of.

    Both hosts serve the same thing: an HTML shell wrapping the document in a
    single ``<pre>`` block, with hyperlinks inserted into the plain text and
    e-mail addresses replaced by CDN-obfuscated markup. This unwraps it back to
    what the agency wrote.

    Args:
        raw: The response body, as fetched.

    Returns:
        The document text, with markup removed, entities resolved, obfuscated
        addresses collapsed to a constant, and line endings normalised to ``\\n``.

    Note:
        The address placeholder is a deliberate, visible lie: it says an address
        was here without saying which. Preserving the real address would put a
        person's contact details into a benchmark corpus for no benefit, and
        preserving the cipher would make the corpus's identity depend on which
        host answered.
    """
    text = raw.decode("utf-8", "replace")
    match = _PRE_BLOCK.search(text)
    body = match.group(1) if match else text
    body = _CF_SPAN.sub(_EMAIL_PLACEHOLDER, body)
    body = _CF_LINK.sub(_EMAIL_PLACEHOLDER, body)
    body = _ANCHOR.sub(r"\1", body)
    body = _ANY_TAG.sub("", body)
    body = html.unescape(body)
    return body.replace("\r\n", "\n").replace("\r", "\n")


def text_digest(text: str) -> str:
    """SHA-256 of the normalised text, UTF-8 encoded."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# fetching
# ---------------------------------------------------------------------------
def _download(url: str, timeout: float = 180.0) -> bytes:
    """Fetch ``url``, following redirects.

    Raises:
        RuntimeError: On any transport or HTTP failure, with the URL included.
    """
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return bytes(response.read())
    except urllib.error.HTTPError as error:
        raise RuntimeError(f"HTTP {error.code} fetching {url}") from error
    except Exception as error:  # reported with its URL, never swallowed
        raise RuntimeError(f"{type(error).__name__} fetching {url}") from error


def body_url(document_number: str, publication_date: str) -> str:
    """Primary-host URL for one document's body."""
    year, month, day = publication_date.split("-")
    return FEDERAL_REGISTER_BODY.format(year=year, month=month, day=day, document=document_number)


def mirror_url(document_number: str, publication_date: str) -> str:
    """Mirror URL for one document's body, on the Government Publishing Office."""
    return GOVINFO_MIRROR.format(date=publication_date, document=document_number)


def api_url(selection: Selection, page: int) -> str:
    """One page of the discovery query."""
    pairs = [*selection.query(), ("page", str(page))]
    return FEDERAL_REGISTER_API + "?" + urllib.parse.urlencode(pairs)


def discover(selection: Selection, *, pause: float = 0.5) -> List[Dict[str, Any]]:
    """Page the API for every document matching ``selection``.

    Args:
        selection: The frozen query.
        pause: Seconds between pages. The API is free and unauthenticated; the
            pause is politeness toward a service this project does not pay for.

    Returns:
        Every result row, in the API's own order.
    """
    results: List[Dict[str, Any]] = []
    page = 1
    while True:
        payload = json.loads(_download(api_url(selection, page)))
        results.extend(payload.get("results", []))
        if not payload.get("next_page_url"):
            return results
        page += 1
        time.sleep(pause)


def draw(rows: Sequence[Dict[str, Any]], selection: Selection) -> List[Dict[str, Any]]:
    """Take the seeded uniform sample that defines the population.

    The rows are sorted by document number before the draw, not left in the
    API's order. The API's order is stable *today*; sorting makes the draw
    depend on the set of documents rather than on the server's pagination, which
    is one fewer thing that can move under the pin.

    Args:
        rows: Every document the query matched.
        selection: Supplies the seed and the size.

    Returns:
        The drawn rows, sorted by document number.
    """
    ordered = sorted(rows, key=lambda row: str(row["document_number"]))
    if len(ordered) < selection.size:
        raise SystemExit(
            f"query returned {len(ordered)} documents, fewer than the pinned draw size "
            f"{selection.size}. The population moved; do not shrink the draw to fit."
        )
    sample = random.Random(selection.seed).sample(ordered, selection.size)
    return sorted(sample, key=lambda row: str(row["document_number"]))


def fetch_body(pin: PinnedDocument, *, cache_dir: Path = BODY_DIR, refresh: bool = False) -> str:
    """Return one document's normalised text, fetching and caching it if needed.

    Args:
        pin: The pinned document.
        cache_dir: Where bodies are cached. Inside the git-ignored ``data/``.
        refresh: Re-fetch even when a cached copy is present.

    Returns:
        The normalised text.
    """
    cache_dir.mkdir(parents=True, exist_ok=True)
    cached = cache_dir / f"{pin.document_number}.txt"
    if cached.is_file() and not refresh:
        return cached.read_text(encoding="utf-8")
    text = normalise_body(_download(body_url(pin.document_number, pin.publication_date)))
    _write_lf(cached, text)
    return text


def load_corpus(*, cache_dir: Path = BODY_DIR) -> Dict[str, str]:
    """Every pinned document's text, keyed by document number.

    Raises:
        SystemExit: If any pinned body is missing, or if any body on disk does
            not match its pinned digest. The second case is the one worth
            stopping for: a corpus that has drifted under its pin scores
            differently for a reason nothing in a results file would record.
    """
    texts: Dict[str, str] = {}
    missing: List[str] = []
    drifted: List[str] = []
    for pin in PINNED_DOCUMENTS:
        cached = cache_dir / f"{pin.document_number}.txt"
        if not cached.is_file():
            missing.append(pin.document_number)
            continue
        text = cached.read_text(encoding="utf-8")
        if pin.text_sha256 not in ("", "PENDING") and text_digest(text) != pin.text_sha256:
            drifted.append(pin.document_number)
            continue
        texts[pin.document_number] = text
    if missing:
        raise SystemExit(
            f"{len(missing)} pinned document(s) not cached: {', '.join(missing[:5])}"
            f"{' ...' if len(missing) > 5 else ''}\n"
            "Run: python tools/build_gold_corpus.py fetch"
        )
    if drifted:
        raise SystemExit(
            f"{len(drifted)} cached body/bodies do not match their pinned text digest: "
            f"{', '.join(drifted)}\n"
            "Do not 'fix' this by re-pinning until you have established what changed. "
            "The digest is over normalised text, so a CDN rewrite cannot cause it."
        )
    return texts


# ---------------------------------------------------------------------------
# proposers
# ---------------------------------------------------------------------------
#: The three independent proposers, and what each one is for.
#:
#: They are not three opinions about the same question. ``acronymkit`` and the
#: external tool both propose *edges* and disagree only at the margin, because
#: every widely used abbreviation extractor is a descendant of the same
#: parenthesis-scanning algorithm. ``all_caps`` proposes *vertices* -- short
#: forms with no long form attached -- and its entire job in this pool is to
#: surface abbreviations the edge proposers never looked at, so that a human is
#: asked about them.
#:
#: Publishing the recipe means publishing that asymmetry. A pool of three
#: parenthesis scanners is a pool of one algorithm with three implementations,
#: and reporting its union as "three independent systems agreed" would overstate
#: what agreement is worth here by a wide margin.
PROPOSERS = ("acronymkit_high_recall", "all_caps", "external")

#: External systems this pipeline knows how to drive, in decreasing order of
#: algorithmic independence from ``acronymkit``.
#:
#: ``pyab3p`` is the default because it is the only one that is not a Schwartz &
#: Hearst variant: Ab3P applies a cascade of match strategies with per-strategy
#: reliability estimates. ``abbreviations`` and ``abbreviation_extractor`` are
#: both faithful S&H implementations, so pooling either with ``acronymkit`` buys
#: agreement rather than coverage.
EXTERNAL_SYSTEMS = ("pyab3p", "abbreviation_extractor", "abbreviations")

#: Run under the foreign interpreter, because two of the three baselines cannot
#: be imported alongside this project -- ``pyab3p`` publishes wheels only up to
#: CPython 3.12. Results go to a **file**, not to stdout, and that is not
#: fastidiousness: ``pyab3p`` writes the document it is processing to stdout,
#: which would corrupt any JSON-on-stdout contract on a corpus this size.
_EXTERNAL_PROGRAM = """
import json, sys
system, source, sink = sys.argv[1], sys.argv[2], sys.argv[3]
texts = json.load(open(source, encoding="utf-8"))
if system == "abbreviations":
    from abbreviations import schwartz_hearst
    def run(text):
        found = schwartz_hearst.extract_abbreviation_definition_pairs(doc_text=text)
        return list(found.items())
elif system == "abbreviation_extractor":
    import abbreviation_extractor
    def run(text):
        found = abbreviation_extractor.extract_abbreviation_definition_pairs(text)
        return [(item.abbreviation, item.definition) for item in found]
elif system == "pyab3p":
    import pyab3p
    engine = pyab3p.Ab3p()
    def run(text):
        return [(item.short_form, item.long_form) for item in engine.get_abbrs(text)]
else:
    raise SystemExit("unknown system " + system)
out = {uid: run(text) for uid, text in texts.items()}
with open(sink, "w", encoding="utf-8") as handle:
    json.dump(out, handle)
"""


def propose_acronymkit(texts: Mapping[str, str]) -> Dict[str, List[Tuple[str, str]]]:
    """This library's extractor, configured for recall rather than precision.

    The recall configuration is the shipped ``BIOMEDICAL`` profile's admission
    bounds -- one character minimum, fourteen maximum, no uppercase requirement
    -- and not a private loosening invented for this pipeline. Using a shipped
    configuration matters because the pool's coverage is a property someone will
    want to reproduce, and "we turned the knobs up" is not reproducible.

    ``legend_syntax`` is left **off**, and that is a measurement rather than a
    default. The flag reads ``SF = LF``; the Federal Register writes its legends
    as ``SF LF`` and ``SF--LF``. Turning it on over this substrate changes no
    proposal at all, so turning it on would buy nothing and would put a
    non-default flag into the recipe for free.

    Args:
        texts: ``{document number: text}``.

    Returns:
        ``{document number: [(short form, long form), ...]}``.
    """
    sys.path.insert(0, str(REPO_ROOT / "src"))
    from acronymkit.config import Config
    from acronymkit.extractor import AbbreviationExtractor

    extractor = AbbreviationExtractor(
        Config(
            extraction_min_short_form_length=1,
            extraction_max_short_form_length=14,
            extraction_require_uppercase=False,
            extraction_capture_sentences=False,
        )
    )
    return {
        uid: [(pair.short_form, pair.long_form) for pair in extractor.extract(text)]
        for uid, text in texts.items()
    }


#: What the all-caps one-liner counts as a short form. Two or more characters,
#: equal to its own uppercase, containing at least one letter -- the same rule
#: ``bench/run_spans.py::predict_all_caps`` uses, kept identical on purpose so
#: this pool's floor is the floor that repository already publishes against.
_ALL_CAPS_TOKEN = re.compile(r"[A-Za-z][A-Za-z0-9./&-]*")


def propose_all_caps(texts: Mapping[str, str]) -> Dict[str, List[str]]:
    """The trivial baseline: every all-caps token is a short-form candidate.

    It proposes no long forms, by construction, so it contributes *vertices* to
    a pool whose other two members contribute edges. That is the point. Every
    edge proposer here starts from a bracket, so a pool of edge proposers alone
    can only ever contain abbreviations that were defined in brackets -- and the
    forms this project has repeatedly found itself missing are exactly the ones
    that were not.

    Args:
        texts: ``{document number: text}``.

    Returns:
        ``{document number: [short form, ...]}``, distinct and sorted.
    """
    proposals: Dict[str, List[str]] = {}
    for uid, text in texts.items():
        found = {
            token.group(0)
            for token in _ALL_CAPS_TOKEN.finditer(text)
            if len(token.group(0)) >= 2
            and token.group(0) == token.group(0).upper()
            and any(character.isalpha() for character in token.group(0))
        }
        proposals[uid] = sorted(found)
    return proposals


def propose_external(
    texts: Mapping[str, str], *, system: str, interpreter: str, scratch: Path
) -> Dict[str, List[Tuple[str, str]]]:
    """Run one external extractor under ``interpreter`` and read its JSON back.

    Args:
        texts: ``{document number: text}``.
        system: One of :data:`EXTERNAL_SYSTEMS`.
        interpreter: Path to a Python that has ``system`` installed.
        scratch: Directory for the two JSON files the bridge exchanges.

    Returns:
        ``{document number: [(short form, long form), ...]}``.

    Raises:
        SystemExit: If the subprocess fails, with its stderr attached.
    """
    if system not in EXTERNAL_SYSTEMS:
        raise SystemExit(f"unknown external system {system!r}; known: {list(EXTERNAL_SYSTEMS)}")
    scratch.mkdir(parents=True, exist_ok=True)
    source = scratch / "external_in.json"
    sink = scratch / f"external_out_{system}.json"
    source.write_text(json.dumps(dict(texts)), encoding="utf-8")
    completed = subprocess.run(
        [interpreter, "-c", _EXTERNAL_PROGRAM, system, str(source), str(sink)],
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0 or not sink.is_file():
        raise SystemExit(f"{system} failed under {interpreter}:\n{completed.stderr[-2000:]}")
    payload = json.loads(sink.read_text(encoding="utf-8"))
    return {uid: [(row[0], row[1]) for row in rows] for uid, rows in payload.items()}


# ---------------------------------------------------------------------------
# candidates and strata
# ---------------------------------------------------------------------------
#: Every stratum a candidate can belong to, and what each one is evidence about.
#:
#: The strata exist so the pilot's estimates can be re-weighted. Sampling a fixed
#: number from each and then reporting a pooled rate would be worse than useless
#: -- it would report the sampler's design as if it were the corpus's shape --
#: so :func:`pilot_report` carries every stratum's exact population size beside
#: its sample.
#:
#: ``unproposed_*`` is the half that makes the false-negative rate estimable.
#: Without it, every candidate in the corpus descends from a
#: parenthesis-or-uppercase heuristic, and a corpus built from the union alone
#: under-represents precisely the forms all three proposers miss. That is not a
#: budget line to drop when the pilot runs long: a corpus without it certifies
#: the blind spot instead of measuring it.
STRATA = (
    "proposed_by_several",
    "proposed_by_one",
    "unpaired_short_form",
    "unproposed_parenthetical",
    "unproposed_legend_row",
)

#: The verdicts an adjudicator may return.
#:
#: ``undecidable`` is not a convenience. An adjudication scheme with no way to
#: decline forces a guess on the hard cases and then counts the guess as data,
#: which is how a disagreement rate comes to look lower than it is. Every
#: ``undecidable`` is a case a second annotator would have to resolve, and
#: :func:`pilot_report` reports them as exactly that.
VERDICTS = (
    "definition",
    "not_a_definition",
    "wrong_long_form",
    "undecidable",
)

#: Why a candidate was what it was, for every item including the easy ones.
#:
#: This vocabulary is not a design; it is the shape of the *substrate* as the
#: pilot found it, written down so the next adjudicator inherits the categories
#: rather than re-deriving them. It is expected to grow, and a new value is a
#: finding rather than an error -- which is why :func:`load_adjudications`
#: reports an unknown category without refusing it.
#:
#: The first six were declared before the pilot ran. The rest were **added
#: because the pilot needed them**, and each names a property of Federal Register
#: text rather than a property of abbreviations in general:
#:
#: ``column_interleaved``
#:     Rules render tables as fixed-width columns, so text from adjacent columns
#:     interleaves in the linear body. Any extractor reading this substrate sees
#:     sentences that were never written.
#: ``line_wrap_hyphen``
#:     The typesetting hyphenates across line breaks, so ``CPI-U`` arrives as
#:     ``CPI-`` plus ``U`` and a long form arrives as ``Patient- Reported``.
#: ``undefined_in_document``
#:     A real abbreviation, used throughout and defined nowhere. This is the
#:     class that makes a *vertex* corpus and an *edge* corpus different objects,
#:     and it is why the all-caps proposer contributes vertices.
#: ``code_or_title_gloss``
#:     A parenthetical that names rather than abbreviates -- an executive order
#:     number glossed by its title, a job-series code by its family, a plant by
#:     its botanical binomial.
#: ``defined_term_not_initialism``
#:     The document introduces a short name for a long one and the short name is
#:     not built from the long one's letters. Legal drafting is full of these.
#: ``aside_not_definition``
#:     An ordinary parenthetical aside that a bracket scanner reaches for.
#: ``evidence_misanchored``
#:     Not a property of the corpus: the item is decidable but the window shown
#:     pointed somewhere else. Kept in the vocabulary because an adjudicator must
#:     be able to say so rather than answering the question they were shown.
HARD_CASE_CATEGORIES = (
    "boundary",  # the edge is real; where the long form starts or ends is a judgement
    "reference_not_definition",  # a citation or cross-reference shaped like a definition
    "restatement",  # the parenthetical restates rather than names, e.g. a unit conversion
    "legend_only",  # defined only in the agency's abbreviation table, never in prose
    "nested",  # a definition inside another definition's parenthetical
    "not_an_abbreviation",  # the short form is a code, a docket number or an identifier
    "clear",  # no judgement required
    "column_interleaved",  # added by the pilot
    "line_wrap_hyphen",  # added by the pilot
    "undefined_in_document",  # added by the pilot
    "code_or_title_gloss",  # added by the pilot
    "defined_term_not_initialism",  # added by the pilot
    "aside_not_definition",  # added by the pilot
    "evidence_misanchored",  # added by the pilot
)

#: The categories where a second annotator could reasonably have decided
#: differently, and therefore the only ones that cost a second annotator time.
#:
#: The distinction is the whole value of the taxonomy for costing, and it was
#: missing from the first report this module produced. That report counted every
#: item whose category was not ``clear`` as a "hard case", which put
#: ``not_an_abbreviation`` -- a subsection marker like ``(b)``, decidable at a
#: glance -- in the same column as ``boundary``, where two careful people
#: genuinely disagree about where a long form ends. It made the unproposed
#: parenthetical stratum look entirely hard when it is almost entirely trivial,
#: and it would have inflated the cost of the corpus by a wide margin.
#:
#: ``legend_only`` is in this list for one specific reason rather than because
#: legend rows are difficult: a legend contains rows like ``Sec.`` for
#: ``Section``, which is a contraction and not an initialism, and whether such a
#: row belongs in an abbreviation corpus at all is a scope question an annotation
#: guideline has to answer before a second annotator can agree with the first.
CONTESTED_CATEGORIES = (
    "boundary",
    "legend_only",
    "code_or_title_gloss",
    "defined_term_not_initialism",
    "line_wrap_hyphen",
    "column_interleaved",
)


@dataclass(frozen=True)
class Candidate:
    """One thing an adjudicator is asked about.

    Attributes:
        document: Federal Register document number.
        short_form: The abbreviation, as it appears.
        long_form: The expansion, as proposed, or ``None`` for a candidate that
            proposes a short form with no edge attached. The distinction is the
            reason this type has an optional field rather than two types: an
            adjudicator answering "is this a definition" needs to be able to
            answer "yes, and here is the long form nobody proposed".
        stratum: One of :data:`STRATA`.
        proposers: Which of :data:`PROPOSERS` put it forward, sorted. Empty for
            the ``unproposed_*`` strata, which is what they mean.
        evidence: A window of surrounding text, for the adjudicator to read.
        offset: Where the evidence window starts in the document.
        legend_support: Whether the document's own abbreviation table lists this
            short form. Agency-asserted corroboration, carried as **evidence**
            and never as a verdict -- see :func:`legend_entries`.
    """

    document: str
    short_form: str
    long_form: Optional[str]
    stratum: str
    proposers: Tuple[str, ...] = ()
    evidence: str = ""
    offset: int = -1
    legend_support: bool = False

    def key(self) -> Tuple[str, str, str]:
        """Stable identity: document, short form, normalised long form."""
        long_form = " ".join((self.long_form or "").split()).casefold()
        return (self.document, " ".join(self.short_form.split()), long_form)


def _collapse(value: str) -> str:
    """Whitespace-collapsed, for comparison only."""
    return " ".join(value.split())


#: The Federal Register's typewriter quoting, and the ordinary quotes it stands
#: in for. A quoted short form is written ```` ``NAECA'' ```` in this substrate,
#: which is neither a straight quote nor a curly one.
_QUOTE_CHARACTERS = "`'" + '"' + "\u201c\u201d\u2018\u2019" + " \t"


def _surface_key(value: str) -> str:
    """Comparison key for "did any proposer already touch this surface?".

    Quoting is stripped, and that is a correction rather than a nicety. The
    pilot drew ```` (``NAECA'') ```` into the *unproposed* stratum for a document
    in which ``acronymkit`` had proposed exactly ``NAECA`` paired with
    ``National Appliance Energy Conservation Act of 1987``. The comparison was
    against the raw inner text, so the four quote characters made a proposed
    surface look untouched.

    Left unfixed this biases the headline estimate of the whole exercise. Every
    such item adjudicates as a definition, is counted in the unproposed stratum,
    and is re-weighted by that stratum's population into a **false-negative rate
    for definitions the systems did in fact find**.

    The size of the bias on the pinned population is a figure and no runner has
    saved one, so it is not written here -- operating rule 1 applies to a
    docstring in this file exactly as it applies to README. ``pool`` prints the
    stratum populations, and running it with this fix reverted is how to
    re-derive the difference.

    Args:
        value: A surface as it appears in the text.

    Returns:
        A casefolded, whitespace-collapsed, quote-stripped key.
    """
    return _collapse(value).strip(_QUOTE_CHARACTERS).casefold()


#: How far after a long form the short form may sit and still make that
#: occurrence the one worth showing.
#:
#: Tight, and the first draft was not. At 160 characters the window landed on
#: mastheads: ``DEPARTMENT OF TRANSPORTATION / Federal Aviation Administration /
#: 14 CFR Part 39 / [Docket No. FAA-2024-0027 ...]`` puts the long form and the
#: short form within a hundred characters of each other while defining nothing,
#: and the adjudicator is shown a page header. In the definitional arrangement
#: the short form follows immediately -- ``Type Certificate Data Sheet (TCDS)``,
#: ``Municipal Securities Rulemaking Board's (MSRB)`` -- so the window only has to
#: tolerate a trailing word or a quote.
_ADJACENCY = 40


def _defining_occurrence(text: str, short_form: str, long_form: str) -> int:
    """Where to point the adjudicator's eye, given a proposed edge.

    **This is not an assertion about which occurrence is the definition.** It
    chooses a window to read. The distinction matters because D-048 established
    that localising a pair to a span is a *choice* on five MED1250 records in
    six, and a function that quietly made that choice while looking like a
    formatting helper would be gold derivation wearing a disguise. Nothing
    downstream reads the offset as evidence of anything; the human reads the
    text.

    The heuristic: prefer the first occurrence of the long form that has the
    short form within :data:`_ADJACENCY` characters after it, since that is the
    arrangement a definition takes. Fall back to the first occurrence of the long
    form, then of the short form, then to the start of the document.

    Args:
        text: The document.
        short_form: The proposed abbreviation.
        long_form: The proposed expansion.

    Returns:
        A character offset, or ``0`` when nothing matched.
    """
    start = 0
    while True:
        index = text.find(long_form, start)
        if index < 0:
            break
        tail = text[index + len(long_form) : index + len(long_form) + _ADJACENCY]
        if short_form in tail:
            return index
        start = index + 1
    for surface in (long_form, short_form):
        index = text.find(surface)
        if index >= 0:
            return index
    return 0


def evidence_window(text: str, start: int, end: int, *, radius: int = 220) -> Tuple[str, int]:
    """A readable window around ``[start, end)``, and where it begins.

    Args:
        text: The document.
        start: Start of the thing being shown.
        end: End of it.
        radius: Characters of context on each side.

    Returns:
        ``(window, offset)``. Newlines are collapsed, because the adjudicator is
        reading a sentence, not a page layout.
    """
    left = max(0, start - radius)
    right = min(len(text), end + radius)
    return " ".join(text[left:right].split()), left


# ---------------------------------------------------------------------------
# the agency's own legend
# ---------------------------------------------------------------------------
#: The heading that opens an abbreviation legend in a Federal Register rule.
#: Numbered (``I. Table of Abbreviations``) or bare, and always on its own line.
_LEGEND_HEADING = re.compile(
    r"(?im)^[ \t]*(?:[IVXLC]+\.[ \t]*)?(?:Table of Abbreviations|List of Abbreviations"
    r"|Abbreviations(?:[ \t]+used[ \t]+in[ \t]+this[ \t]+\w+)?)[ \t]*$"
)

#: One legend row. Two surface forms are attested in this substrate and neither
#: is the ``SF = LF`` the library's legend reader understands:
#:
#: * ``CFR Code of Federal Regulations``  -- separated by a single space run
#: * ``CFR--Code of Federal Regulations`` -- separated by a double hyphen
#:
#: Two patterns rather than one alternation, and the pilot is why. A single
#: pattern with ``(?:--|[ \t]+)`` splits ``CPI-U--Consumer Price Index for All
#: Urban Consumers`` at the *space*, because a short-form class that admits
#: ``-`` will happily swallow ``CPI-U--Consumer`` first. The double-hyphen form
#: is therefore tried first and its short form is forbidden to contain a hyphen
#: run. That defect reached a worklist; it is the clearest argument in this
#: module for piloting before adjudicating at scale.
#: The dashed short form may contain a space -- ``IMMACT 90--Immigration Act of
#: 1990`` and ``Pub. L.--Public Law`` are both real rows -- so it is bounded by
#: length and by laziness rather than by a character class. Also from the pilot:
#: forbidding the space split those two rows one token early and silently.
_LEGEND_ROW_DASHED = re.compile(r"^(?P<short>[^\s-][^\n]{0,14}?)--(?P<long>[A-Z0-9][^\n]{2,90})$")
_LEGEND_ROW_SPACED = re.compile(
    r"^(?P<short>[A-Za-z][A-Za-z0-9./&]{0,14})[ \t]+(?P<long>[A-Z0-9][^\n]{2,90})$"
)

#: A numbered or lettered section heading, which ends a legend whether or not a
#: blank line does. ``II. Background Information and Regulatory History`` sits
#: directly under the last legend row in the Coast Guard house style, and a
#: parser that stops only on blank lines reads it as ``II.`` defined as
#: ``Background Information and Regulatory History``. Also from the pilot.
_SECTION_HEADING = re.compile(r"^(?:[IVXLC]+|[A-Z]|\d+)\.[ \t]+[A-Z]")


def _legend_row(line: str) -> Optional[Tuple[str, str]]:
    """Parse one legend row, dashed form first. ``None`` when it is not one."""
    for pattern in (_LEGEND_ROW_DASHED, _LEGEND_ROW_SPACED):
        match = pattern.match(line)
        if match is not None:
            return match.group("short").strip(), _collapse(match.group("long"))
    return None


def legend_entries(text: str) -> Dict[str, str]:
    """The abbreviation legend the agency published in this document, if any.

    This is the closest thing in the substrate to an arbiter that is not the
    author of the system under test: where an agency writes ``LWD Low Water
    Datum based on IGLD85`` at the top of its own rule, that edge is asserted by
    the publisher, not inferred by us.

    It is deliberately **not** used to label anything. A legend row is carried
    into the worklist as :attr:`Candidate.legend_support` so an adjudicator can
    weigh it, and that is all. Two reasons, both observed here rather than
    imagined: a legend lists abbreviations the document *uses*, which is not the
    same set as the abbreviations it *defines in prose*; and the row parse below
    is a heuristic over a whitespace-delimited table, so treating its output as
    gold would put a regex in the arbiter's chair.

    Args:
        text: A normalised document.

    Returns:
        ``{short form: long form}``, empty when the document carries no legend.
    """
    return {short: long_form for short, long_form, _ in legend_rows(text)}


def legend_rows(text: str) -> List[Tuple[str, str, int]]:
    """The legend, with each row's offset in the document.

    The offset exists so a legend candidate's evidence window can be anchored at
    the row itself. It was not there at first, and the pilot is what surfaced the
    cost: anchoring on ``text.find(short_form)`` puts the window at the *first*
    mention of ``CFR`` in a document, which is the page header, so an adjudicator
    was shown a masthead and asked whether it defined ``CFR``. Evidence that does
    not contain the thing being adjudicated is worse than no evidence, because it
    looks like evidence.

    Args:
        text: A normalised document.

    Returns:
        ``[(short form, long form, offset), ...]`` in document order.
    """
    heading = _LEGEND_HEADING.search(text)
    if heading is None:
        return []
    rows: List[Tuple[str, str, int]] = []
    cursor = heading.end()
    blank_run = 0
    for line in text[heading.end() :].split("\n"):
        start, cursor = cursor, cursor + len(line) + 1
        stripped = line.strip()
        if not stripped:
            blank_run += 1
            # One blank line separates the heading from the table and may separate
            # rows; two ends it. Reading past the end is how a legend parser comes
            # to report the first sentence of the next section as a definition.
            if blank_run >= 2 and rows:
                break
            continue
        blank_run = 0
        if _SECTION_HEADING.match(stripped):
            break
        row = _legend_row(stripped)
        if row is None:
            if rows:
                break
            continue
        rows.append((row[0], row[1], start + line.index(stripped)))
    return rows


# ---------------------------------------------------------------------------
# pooling
# ---------------------------------------------------------------------------
@dataclass
class Pool:
    """The pooled candidate set, with everything needed to re-derive it.

    Attributes:
        candidates: Every candidate, across every stratum.
        population: Exact size of each stratum's population, before sampling.
            The sampled strata are much larger than any pilot can adjudicate, and
            an estimate drawn from them is meaningless without its denominator.
        proposer_counts: How many edges each proposer put forward, and how many
            it alone put forward. This is the pooling recipe's own evidence: it
            says what the second and third proposer actually bought.
        recipe: Free text: the exact configuration each proposer ran under.
    """

    candidates: List[Candidate] = field(default_factory=list)
    population: Dict[str, int] = field(default_factory=dict)
    proposer_counts: Dict[str, Dict[str, int]] = field(default_factory=dict)
    recipe: Dict[str, str] = field(default_factory=dict)


#: A parenthetical worth showing a human: balanced, on one line, holding at least
#: one letter, and short enough to read. The length bound is the only judgement
#: in it and it is generous.
_PARENTHETICAL = re.compile(r"\(([^()\n]{1,140})\)")


def build_pool(
    texts: Mapping[str, str],
    *,
    external_system: str,
    interpreter: Optional[str],
    scratch: Path,
) -> Pool:
    """Pool candidates from three proposers and enumerate what none of them saw.

    Args:
        texts: ``{document number: text}``.
        external_system: Which of :data:`EXTERNAL_SYSTEMS` to run.
        interpreter: Python that has it installed, or ``None`` to skip the
            external proposer -- which is reported in the recipe rather than
            silently tolerated, because a two-proposer pool is a different
            recipe from a three-proposer one.
        scratch: Working directory for the external bridge.

    Returns:
        The pool.
    """
    pool = Pool()
    edges: Dict[str, Dict[Tuple[str, str], set]] = {uid: {} for uid in texts}

    kit = propose_acronymkit(texts)
    for uid, pairs in kit.items():
        for short, long_form in pairs:
            edges[uid].setdefault((_collapse(short), _collapse(long_form)), set()).add(
                "acronymkit_high_recall"
            )
    pool.recipe["acronymkit_high_recall"] = (
        "AbbreviationExtractor(Config(extraction_min_short_form_length=1, "
        "extraction_max_short_form_length=14, extraction_require_uppercase=False, "
        "extraction_capture_sentences=False)), legend_syntax off"
    )

    external: Dict[str, List[Tuple[str, str]]] = {}
    if interpreter:
        external = propose_external(
            texts, system=external_system, interpreter=interpreter, scratch=scratch
        )
        for uid, pairs in external.items():
            for short, long_form in pairs:
                edges[uid].setdefault((_collapse(short), _collapse(long_form)), set()).add(
                    "external"
                )
        pool.recipe["external"] = f"{external_system} under {interpreter}, default settings"
    else:
        pool.recipe["external"] = "NOT RUN -- no --interpreter given; this is a two-proposer pool"

    caps = propose_all_caps(texts)
    pool.recipe["all_caps"] = (
        "every token of length 2+ equal to its own uppercase and holding a letter; "
        "proposes short forms only, exactly as bench/run_spans.py::predict_all_caps does"
    )

    for uid, text in texts.items():
        rows = legend_rows(text)
        legend = {short: long_form for short, long_form, _ in rows}
        proposed_shorts = {_surface_key(short) for short, _ in edges[uid]}
        used_surfaces = {_surface_key(short) for short, _ in edges[uid]}
        used_surfaces |= {_surface_key(long_form) for _, long_form in edges[uid]}

        for (short, long_form), proposers in sorted(edges[uid].items()):
            stratum = "proposed_by_several" if len(proposers) > 1 else "proposed_by_one"
            index = _defining_occurrence(text, short, long_form)
            window, offset = evidence_window(text, max(index, 0), max(index, 0) + len(long_form))
            pool.candidates.append(
                Candidate(
                    document=uid,
                    short_form=short,
                    long_form=long_form,
                    stratum=stratum,
                    proposers=tuple(sorted(proposers)),
                    evidence=window,
                    offset=offset,
                    legend_support=short in legend,
                )
            )

        for short in caps[uid]:
            if _surface_key(short) in proposed_shorts:
                continue
            index = text.find(short)
            window, offset = evidence_window(text, max(index, 0), max(index, 0) + len(short))
            pool.candidates.append(
                Candidate(
                    document=uid,
                    short_form=short,
                    long_form=None,
                    stratum="unpaired_short_form",
                    proposers=("all_caps",),
                    evidence=window,
                    offset=offset,
                    legend_support=short in legend,
                )
            )

        for match in _PARENTHETICAL.finditer(text):
            inner = _collapse(match.group(1))
            if not any(character.isalpha() for character in inner):
                continue
            if _surface_key(inner) in used_surfaces:
                continue
            window, offset = evidence_window(text, match.start(), match.end())
            pool.candidates.append(
                Candidate(
                    document=uid,
                    short_form=inner,
                    long_form=None,
                    stratum="unproposed_parenthetical",
                    evidence=window,
                    offset=offset,
                    legend_support=inner in legend,
                )
            )

        for short, long_form, index in rows:
            if (short, long_form) in edges[uid]:
                continue
            window, offset = evidence_window(text, index, index + len(short) + len(long_form))
            pool.candidates.append(
                Candidate(
                    document=uid,
                    short_form=short,
                    long_form=long_form,
                    stratum="unproposed_legend_row",
                    evidence=window,
                    offset=offset,
                    legend_support=True,
                )
            )

    for stratum in STRATA:
        pool.population[stratum] = sum(1 for c in pool.candidates if c.stratum == stratum)

    kit_edges = {(uid, short, long_form) for uid, v in kit.items() for short, long_form in v}
    ext_edges = {(uid, short, long_form) for uid, v in external.items() for short, long_form in v}
    pool.proposer_counts = {
        "acronymkit_high_recall": {
            "proposed": len(kit_edges),
            "unique_to_it": len(kit_edges - ext_edges),
        },
        "external": {"proposed": len(ext_edges), "unique_to_it": len(ext_edges - kit_edges)},
        "all_caps": {
            "proposed": sum(len(v) for v in caps.values()),
            "unique_to_it": pool.population.get("unpaired_short_form", 0),
        },
    }
    return pool


# ---------------------------------------------------------------------------
# the worklist
# ---------------------------------------------------------------------------
#: How many candidates the pilot draws from each stratum.
#:
#: Modest on purpose. A pilot exists to establish the adjudication rate and the
#: shape of the hard cases; a pilot large enough that finishing it feels like
#: finishing the corpus is the failure this whole module is arranged against.
#:
#: The allocation is not proportional to population and must not be read as
#: though it were: ``unproposed_parenthetical`` is by far the largest stratum and
#: is sampled at a tiny rate, which is exactly why :func:`pilot_report` carries
#: the population beside every count.
PILOT_ALLOCATION = {
    "proposed_by_several": 30,
    "proposed_by_one": 30,
    "unpaired_short_form": 20,
    "unproposed_parenthetical": 30,
    "unproposed_legend_row": 10,
}


def draw_worklist(pool: Pool, *, seed: int, allocation: Mapping[str, int]) -> List[Candidate]:
    """Sample uniformly within each stratum, with a fixed seed.

    Uniform *within stratum* and never across strata. Sampling the union would
    make the sample overwhelmingly parentheticals -- they outnumber everything
    else -- and would leave the proposed strata too thin to say anything about
    the pool's precision.

    Args:
        pool: The pooled candidates.
        seed: Draw seed, recorded in the worklist header.
        allocation: ``{stratum: how many}``.

    Returns:
        The drawn candidates, ordered by stratum then document then short form,
        so the adjudicator reads related items together.
    """
    rng = random.Random(seed)
    drawn: List[Candidate] = []
    for stratum in STRATA:
        wanted = allocation.get(stratum, 0)
        available = sorted(
            (c for c in pool.candidates if c.stratum == stratum),
            key=lambda c: (c.document, c.short_form, c.long_form or ""),
        )
        if not available or wanted <= 0:
            continue
        drawn.extend(rng.sample(available, min(wanted, len(available))))
    return sorted(
        drawn, key=lambda c: (STRATA.index(c.stratum), c.document, c.short_form, c.long_form or "")
    )


def write_worklist(path: Path, pool: Pool, drawn: Sequence[Candidate], *, seed: int) -> Path:
    """Write the adjudication worklist as JSONL.

    The first record is a header carrying the pin, the recipe, the strata
    populations and the seed, so a worklist that has travelled away from this
    repository still says what it is.

    **No record carries a proposed verdict.** The adjudicator gets the evidence
    window, the proposers and the agency's legend support, and nothing that reads
    as a suggestion. Pre-filling a verdict would turn adjudication into review of
    the extractor's own output, which is the exact failure this pipeline exists
    to avoid.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    header = {
        "record": "header",
        "substrate": "federal_register",
        "domain": DOMAIN,
        "licence": LICENCE,
        "licence_url": LICENCE_URL,
        "licence_read_on": LICENCE_READ_ON,
        "selection": asdict(SELECTION),
        "documents": [pin.document_number for pin in PINNED_DOCUMENTS],
        "recipe": pool.recipe,
        "population": pool.population,
        "proposer_counts": pool.proposer_counts,
        "seed": seed,
        "verdicts": list(VERDICTS),
        "hard_case_categories": list(HARD_CASE_CATEGORIES),
        "instruction": (
            "For each item decide whether the document defines short_form as long_form. "
            "A definition is an assertion by the document that the two name the same thing. "
            "A citation, a cross-reference, a units restatement and a docket code are not "
            "definitions. Where long_form is null, supply it if the document defines one, "
            "otherwise answer not_a_definition. Answer undecidable rather than guessing; an "
            "undecidable item is a real finding about the corpus. Record a hard_case category "
            "on every item, including 'clear'."
        ),
        "warning": (
            "This worklist is not a gold standard and does not become one by being filled in. "
            "One adjudicator produces a single-annotator reference set. If the adjudicator is "
            "also the author of a system this corpus will be used to score, that fact must be "
            "carried in the artifact and no headline may be quoted off it."
        ),
    }
    lines = [json.dumps(header)]
    for candidate in drawn:
        row = asdict(candidate)
        row["record"] = "item"
        row["key"] = list(candidate.key())
        row["verdict"] = None
        row["hard_case"] = None
        row["adjudicated_long_form"] = None
        row["note"] = ""
        lines.append(json.dumps(row))
    _write_lf(path, "\n".join(lines) + "\n")
    return path


# ---------------------------------------------------------------------------
# reading adjudications back
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class Adjudication:
    """One decided item.

    Attributes:
        candidate: What was asked about.
        verdict: One of :data:`VERDICTS`.
        hard_case: One of :data:`HARD_CASE_CATEGORIES`, or a new value, which is
            reported rather than refused.
        long_form: The long form the adjudicator settled on. Differs from
            ``candidate.long_form`` exactly when the verdict is
            ``wrong_long_form`` or when a short form arrived unpaired.
        note: Free text.
        adjudicator: Who decided. The artifact's honesty rests on this being
            populated, so an empty value is refused.
    """

    candidate: Candidate
    verdict: str
    hard_case: str
    long_form: Optional[str]
    note: str
    adjudicator: str


@dataclass
class AdjudicationSession:
    """A filled-in worklist, plus the header it arrived with."""

    header: Dict[str, Any] = field(default_factory=dict)
    decided: List[Adjudication] = field(default_factory=list)
    undecided: int = 0
    unknown_categories: List[str] = field(default_factory=list)
    started_at: str = ""
    finished_at: str = ""


def load_adjudications(path: Path) -> AdjudicationSession:
    """Read a filled worklist.

    Args:
        path: JSONL written by :func:`write_worklist` and filled in.

    Returns:
        The session.

    Raises:
        SystemExit: If an item carries a verdict outside :data:`VERDICTS`, or a
            verdict with no adjudicator. Both are refusals rather than warnings:
            an unattributed verdict is exactly the thing that later gets read as
            though a second annotator had produced it.
    """
    session = AdjudicationSession()
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        row = json.loads(line)
        if row.get("record") == "header":
            session.header = row
            session.started_at = str(row.get("started_at", ""))
            session.finished_at = str(row.get("finished_at", ""))
            continue
        verdict = row.get("verdict")
        if verdict is None:
            session.undecided += 1
            continue
        if verdict not in VERDICTS:
            raise SystemExit(f"{path}:{number}: verdict {verdict!r} is not one of {list(VERDICTS)}")
        adjudicator = str(row.get("adjudicator") or "").strip()
        if not adjudicator:
            raise SystemExit(
                f"{path}:{number}: a verdict with no adjudicator. Who decided this is part of "
                "what the artifact claims; it is not an optional field."
            )
        hard_case = str(row.get("hard_case") or "clear")
        if hard_case not in HARD_CASE_CATEGORIES:
            session.unknown_categories.append(hard_case)
        session.decided.append(
            Adjudication(
                candidate=Candidate(
                    document=str(row["document"]),
                    short_form=str(row["short_form"]),
                    long_form=row.get("long_form"),
                    stratum=str(row["stratum"]),
                    proposers=tuple(row.get("proposers") or ()),
                    evidence=str(row.get("evidence", "")),
                    offset=int(row.get("offset", -1)),
                    legend_support=bool(row.get("legend_support", False)),
                ),
                verdict=verdict,
                hard_case=hard_case,
                long_form=row.get("adjudicated_long_form") or row.get("long_form"),
                note=str(row.get("note", "")),
                adjudicator=adjudicator,
            )
        )
    return session


def _rule_of_three_upper(found: int, sampled: int) -> float:
    """A crude upper bound on a stratum's rate, so a zero is never read as zero.

    The unproposed strata are the ones that decide whether this corpus certifies
    its blind spot or measures it, and a pilot draws a few dozen items from a
    population of thousands. If such a draw returns no definitions, the honest
    report is not "there are none" -- it is "the sample cannot distinguish none
    from several hundred", and the difference between those two sentences is the
    entire argument for enlarging the sample.

    For a zero numerator this is the rule of three: the 95 % upper bound on a
    proportion observed as ``0/n`` is about ``3/n``. For a non-zero numerator it
    falls back to a normal-approximation upper limit, which is rough and is
    labelled rough; nothing here is a substitute for a real interval, and no
    figure produced by this function may be published as a measurement.

    Args:
        found: Positives observed.
        sampled: Items drawn.

    Returns:
        An upper bound on the rate, clamped to ``[0, 1]``.
    """
    if sampled <= 0:
        return 0.0
    if found == 0:
        return min(3.0 / sampled, 1.0)
    rate = found / sampled
    spread = 1.96 * (rate * (1.0 - rate) / sampled) ** 0.5
    return max(0.0, min(rate + spread, 1.0))


def pilot_report(session: AdjudicationSession) -> Dict[str, Any]:
    """Everything the pilot measured, as a JSON-safe mapping.

    Three things, and the third is the one that decides whether the corpus is
    worth building:

    * **rate** -- items per minute, from the session's own timestamps. Reported
      with the adjudicator count, because a rate produced by one person is a
      costing for one person's pass and not for an annotated corpus.
    * **outcome by stratum** -- with the population beside every count, so the
      proposed strata give the pool's precision and the unproposed strata give
      the false-negative estimate.
    * **hard cases** -- the categories, and the ``undecidable`` count, which is
      the direct measure of what a second annotator would have to resolve.
    """
    by_stratum: Dict[str, Dict[str, Any]] = {}
    for stratum in STRATA:
        items = [a for a in session.decided if a.candidate.stratum == stratum]
        if not items:
            continue
        counts = {verdict: sum(1 for a in items if a.verdict == verdict) for verdict in VERDICTS}
        population = int((session.header.get("population") or {}).get(stratum, 0))
        contested = sum(
            1 for a in items if a.hard_case in CONTESTED_CATEGORIES or a.verdict == "undecidable"
        )
        found = counts["definition"]
        by_stratum[stratum] = {
            "sampled": len(items),
            "population": population,
            "verdicts": counts,
            "definitions_found": found,
            "not_clear": sum(1 for a in items if a.hard_case != "clear"),
            "contested": contested,
            # Re-weighting the sample to the stratum, so a rate is never read off
            # a sample size the allocation chose. Reported as an interval endpoint
            # too: with a handful of items per stratum the point estimate is not
            # the interesting number, the width is.
            "definitions_per_stratum_point": (
                round(population * found / len(items)) if items else 0
            ),
            "definitions_per_stratum_upper95": (
                round(population * _rule_of_three_upper(found, len(items)))
            ),
        }

    hard: Dict[str, int] = {}
    for adjudication in session.decided:
        hard[adjudication.hard_case] = hard.get(adjudication.hard_case, 0) + 1

    minutes = 0.0
    if session.started_at and session.finished_at:
        try:
            start = _datetime.datetime.fromisoformat(session.started_at)
            finish = _datetime.datetime.fromisoformat(session.finished_at)
            minutes = max((finish - start).total_seconds() / 60.0, 0.0)
        except ValueError:
            minutes = 0.0

    adjudicators = sorted({a.adjudicator for a in session.decided})
    return {
        "adjudicators": adjudicators,
        "adjudicator_count": len(adjudicators),
        "is_gold_standard": len(adjudicators) >= 2,
        "artifact_kind": (
            "gold standard candidate"
            if len(adjudicators) >= 2
            else "single-annotator reference set"
        ),
        "decided": len(session.decided),
        "undecided_left_blank": session.undecided,
        "elapsed_minutes": round(minutes, 2),
        "items_per_minute": round(len(session.decided) / minutes, 2) if minutes else None,
        "rate_caveat": (
            "items_per_minute is wall clock over one pass by one person who wrote the "
            "extractor being pooled. It is an upper bound on speed and not a costing for "
            "an annotated corpus: no guideline was written, no second annotator was "
            "reconciled, and the reader already knew what the extractor would say."
        ),
        # What the two timestamps actually bracket. Without it a reader assumes
        # they bracket reading, and a rate is only as honest as its endpoints.
        "rate_window": str(session.header.get("rate_window_note", "endpoints not described")),
        "by_stratum": by_stratum,
        "hard_case_categories": hard,
        "contested": sum(
            1
            for a in session.decided
            if a.hard_case in CONTESTED_CATEGORIES or a.verdict == "undecidable"
        ),
        "contested_note": (
            "Items where a second annotator could reasonably have decided differently. "
            "This, not the non-clear count, is what a second annotator costs."
        ),
        "undecidable": sum(1 for a in session.decided if a.verdict == "undecidable"),
        "unknown_categories": sorted(set(session.unknown_categories)),
        "domain": DOMAIN,
    }


# ---------------------------------------------------------------------------
# freezing
# ---------------------------------------------------------------------------
#: The role a one-adjudicator artifact needs, and the reason it cannot be filed.
#:
#: ``tools/splits.py``'s ``ROLES`` is ``("tuning", "held_out")``. Neither fits.
#: The artifact is not tuning -- nothing is fitted to it -- and calling it
#: ``held_out`` would make it eligible for a headline through
#: ``Manifest.headline_capable``, which is the one thing a single-annotator set
#: produced by the system's own author must never be.
#:
#: So this constant is the *request*, not a value the manifest will accept today.
#: :func:`freeze` writes it into the artifact and says so out loud rather than
#: choosing the closest wrong answer, because the closest wrong answer here is
#: silently load-bearing.
REQUESTED_ROLE = "single_annotator_reference"


def freeze(
    session: AdjudicationSession,
    pool: Pool,
    *,
    path: Path,
    frozen_on: Optional[str] = None,
) -> Path:
    """Write the frozen reference set, labelled for exactly what it is.

    Args:
        session: The adjudications.
        pool: The pool they were drawn from, for provenance.
        path: Where to write.
        frozen_on: ISO date; defaults to today. The freeze date is part of the
            artifact: freezing *before* anyone touches a knob is what makes the
            set held out in the only sense that matters, and a set whose freeze
            date is later than the tuning it adjudicates is not held out at all.

    Returns:
        The path written.

    Raises:
        SystemExit: If no adjudication carries an adjudicator, or if the caller
            has somehow arranged for a role other than the one the adjudicator
            count supports. The refusal is the point of this function.
    """
    report = pilot_report(session)
    if not report["adjudicators"]:
        raise SystemExit("nothing adjudicated; there is no artifact to freeze")

    # ``wrong_long_form`` belongs in the payload and its exclusion was a defect.
    #
    # The verdict means the edge is real and the *proposed* long form was wrong,
    # and the adjudicator supplied the right one. Keeping only ``definition``
    # therefore drops every pair a proposer got the boundary wrong on -- which is
    # not a random sample of the corpus, it is precisely the hard cases. A gold
    # standard assembled that way contains only the pairs the systems already got
    # right, and every system measured on it scores higher than it should for a
    # reason nothing in the artifact would record.
    #
    # Found by ``tests/test_build_gold_corpus.py`` before the artifact was used
    # for anything. How many edges it costs on a given run is in that run's own
    # report, not written here: no runner saves it, and operating rule 1 reaches
    # a comment in this file as surely as it reaches README.
    admitted = ("definition", "wrong_long_form")
    pairs: Dict[str, List[List[str]]] = {}
    for adjudication in session.decided:
        if adjudication.verdict not in admitted or not adjudication.long_form:
            continue
        pairs.setdefault(adjudication.candidate.document, []).append(
            [adjudication.candidate.short_form, adjudication.long_form]
        )

    # Whether any document is annotated EXHAUSTIVELY, which decides whether the
    # artifact can be scored against at all.
    #
    # This is the property a pilot cannot have and the one most easily assumed.
    # The worklist is a *sample*: a document's pair list holds the sampled
    # candidates that adjudicated as definitions, not every definition in the
    # document. Against a partial annotation both metrics are wrong and they are
    # wrong in opposite directions -- recall is undefined, because the
    # denominator is unknown; and precision is *understated*, because a correct
    # pair that was never sampled scores as a false positive.
    #
    # Nothing in the envelope's shape reveals this. It looks exactly like a
    # complete pair corpus, which is why the flag is computed and written rather
    # than left to a reader's judgement: a document is exhaustive only when every
    # pooled candidate belonging to it was adjudicated.
    # ``all()`` over an empty sequence is ``True``, and getting that wrong here
    # marks a document exhaustive precisely when the pool holds nothing for it --
    # which is what happens when the pool was never built or belongs to a
    # different run. The criterion is therefore "has candidates AND every one of
    # them was adjudicated", never "has no unadjudicated candidate". This
    # repository has paid for a vacuous criterion before; see D-051.
    adjudicated = {
        (a.candidate.document, a.candidate.stratum, a.candidate.short_form, a.candidate.long_form)
        for a in session.decided
    }
    by_document: Dict[str, List[Candidate]] = {}
    for candidate in pool.candidates:
        by_document.setdefault(candidate.document, []).append(candidate)
    exhaustive = sorted(
        document
        for document in pairs
        if by_document.get(document)
        and all(
            (candidate.document, candidate.stratum, candidate.short_form, candidate.long_form)
            in adjudicated
            for candidate in by_document[document]
        )
    )

    envelope = {
        "artifact_kind": report["artifact_kind"],
        "is_gold_standard": report["is_gold_standard"],
        "exhaustively_annotated_documents": exhaustive,
        "scorable": bool(exhaustive),
        "scorable_note": (
            "A document may be scored against only if it is listed in "
            "exhaustively_annotated_documents. Elsewhere the pair list is a SAMPLE: "
            "recall is undefined because the denominator is unknown, and precision is "
            "understated because a correct pair that was never sampled scores as a "
            "false positive. A pilot produces no exhaustively annotated document by "
            "construction."
        ),
        "requested_role": REQUESTED_ROLE,
        "role_note": (
            "tools/splits.py ROLES is ('tuning', 'held_out') and neither is honest here. "
            "Filing this as held_out would make it headline-eligible through "
            "Manifest.headline_capable. Do not register it until ROLES can express "
            f"{REQUESTED_ROLE!r}."
        ),
        "headline_eligible": False,
        "adjudicators": report["adjudicators"],
        "adjudicator_count": report["adjudicator_count"],
        "frozen_on": frozen_on or _datetime.date.today().isoformat(),
        "substrate": "federal_register",
        "domain": DOMAIN,
        "licence": LICENCE,
        "licence_url": LICENCE_URL,
        "licence_read_on": LICENCE_READ_ON,
        "licence_statute_url": LICENCE_STATUTE_URL,
        "vendorable": VENDORABLE,
        "selection": asdict(SELECTION),
        "documents": [asdict(pin) for pin in PINNED_DOCUMENTS],
        "recipe": pool.recipe,
        "population": pool.population,
        "proposer_counts": pool.proposer_counts,
        "pilot": report,
        "payload": pairs,
    }
    if envelope["is_gold_standard"]:  # pragma: no cover - needs two adjudicators
        envelope["role_note"] = (
            "Two or more adjudicators. Agreement between them must be computed and "
            "published before this is called a gold standard; adjudicator count alone "
            "is a necessary and not a sufficient condition."
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    _write_lf(path, json.dumps(envelope, indent=1) + "\n")
    return path


# ---------------------------------------------------------------------------
# command line
# ---------------------------------------------------------------------------
def _cmd_select(args: argparse.Namespace) -> int:
    """Re-derive the draw and compare it against the pin table."""
    rows = discover(SELECTION)
    drawn = draw(rows, SELECTION)
    derived = [str(row["document_number"]) for row in drawn]
    pinned = [pin.document_number for pin in PINNED_DOCUMENTS]
    print(f"population {len(rows)} documents matching {SELECTION.document_type}")
    print(f"draw       {len(derived)} documents, seed {SELECTION.seed}")
    if pinned == derived:
        print("pin        matches PINNED_DOCUMENTS")
        return 0
    print("pin        DRIFT -- the re-derived draw is not the pinned one")
    print(f"  only pinned:  {sorted(set(pinned) - set(derived))}")
    print(f"  only derived: {sorted(set(derived) - set(pinned))}")
    if args.emit:
        for row in drawn:
            print(
                f'    PinnedDocument("{row["document_number"]}", '
                f'"{row["publication_date"]}", "PENDING", 0),'
            )
    return 1


def _cmd_fetch(args: argparse.Namespace) -> int:
    """Fetch every pinned body, verify the text digest, optionally cross-check."""
    BODY_DIR.mkdir(parents=True, exist_ok=True)
    problems = 0
    for pin in PINNED_DOCUMENTS:
        text = fetch_body(pin, refresh=args.refresh)
        digest = text_digest(text)
        if pin.text_sha256 in ("", "PENDING"):
            print(
                f'    PinnedDocument("{pin.document_number}", "{pin.publication_date}", '
                f'"{digest}", {len(text)}),'
            )
            continue
        if digest != pin.text_sha256:
            print(f"  MISMATCH {pin.document_number} expected {pin.text_sha256} got {digest}")
            problems += 1
            continue
        if args.mirror_check:
            mirror = normalise_body(
                _download(mirror_url(pin.document_number, pin.publication_date))
            )
            agree = text_digest(mirror) == digest
            print(
                f"  ok       {pin.document_number} {len(text):>8} chars  mirror={'=' if agree else 'DIFFERS'}"
            )
            if not agree:
                problems += 1
            time.sleep(args.pause)
        else:
            print(f"  ok       {pin.document_number} {len(text):>8} chars")
    return 1 if problems else 0


def _pool_cache() -> Path:
    return CORPUS_DIR / "pool.json"


def _cmd_pool(args: argparse.Namespace) -> int:
    """Build the candidate pool and cache it."""
    texts = load_corpus()
    pool = build_pool(
        texts,
        external_system=args.external,
        interpreter=args.interpreter,
        scratch=CORPUS_DIR / "scratch",
    )
    payload = {
        "recipe": pool.recipe,
        "population": pool.population,
        "proposer_counts": pool.proposer_counts,
        "candidates": [asdict(candidate) for candidate in pool.candidates],
    }
    _pool_cache().parent.mkdir(parents=True, exist_ok=True)
    _write_lf(_pool_cache(), json.dumps(payload))
    print(f"documents  {len(texts)}")
    print(f"characters {sum(len(text) for text in texts.values())}")
    for name, counts in sorted(pool.proposer_counts.items()):
        print(f"  {name:24} proposed {counts['proposed']:>6}  unique {counts['unique_to_it']:>6}")
    for stratum in STRATA:
        print(f"  {stratum:28} {pool.population.get(stratum, 0):>6}")
    print(f"wrote {_pool_cache()}")
    return 0


def read_pool(path: Optional[Path] = None) -> Pool:
    """Read a cached pool back."""
    source = path or _pool_cache()
    if not source.is_file():
        raise SystemExit(f"no pool at {source}\nRun: python tools/build_gold_corpus.py pool")
    payload = json.loads(source.read_text(encoding="utf-8"))
    pool = Pool(
        recipe=payload.get("recipe", {}),
        population=payload.get("population", {}),
        proposer_counts=payload.get("proposer_counts", {}),
    )
    for row in payload.get("candidates", []):
        pool.candidates.append(
            Candidate(
                document=row["document"],
                short_form=row["short_form"],
                long_form=row.get("long_form"),
                stratum=row["stratum"],
                proposers=tuple(row.get("proposers") or ()),
                evidence=row.get("evidence", ""),
                offset=int(row.get("offset", -1)),
                legend_support=bool(row.get("legend_support", False)),
            )
        )
    return pool


def _cmd_worklist(args: argparse.Namespace) -> int:
    """Draw the pilot sample and write the worklist."""
    pool = read_pool()
    drawn = draw_worklist(pool, seed=args.seed, allocation=PILOT_ALLOCATION)
    path = Path(args.out) if args.out else CORPUS_DIR / "worklist.jsonl"
    write_worklist(path, pool, drawn, seed=args.seed)
    print(f"wrote {path} -- {len(drawn)} items, seed {args.seed}")
    for stratum in STRATA:
        drawn_here = sum(1 for c in drawn if c.stratum == stratum)
        print(f"  {stratum:28} {drawn_here:>4} of {pool.population.get(stratum, 0):>6}")
    print("No item carries a proposed verdict. Fill verdict, hard_case and adjudicator.")
    return 0


def _cmd_ingest(args: argparse.Namespace) -> int:
    """Read a filled worklist and print the pilot report."""
    session = load_adjudications(Path(args.worklist))
    print(json.dumps(pilot_report(session), indent=1))
    return 0


def _cmd_freeze(args: argparse.Namespace) -> int:
    """Freeze the reference set."""
    session = load_adjudications(Path(args.worklist))
    pool = read_pool()
    path = Path(args.out) if args.out else CORPUS_DIR / "reference_set.json"
    freeze(session, pool, path=path, frozen_on=args.frozen_on)
    report = pilot_report(session)
    print(f"wrote {path}")
    print(f"artifact_kind      {report['artifact_kind']}")
    print(f"adjudicator_count  {report['adjudicator_count']}")
    print("headline_eligible  False")
    print(
        f"requested role     {REQUESTED_ROLE!r} -- tools/splits.py ROLES cannot express it; "
        "do not register this as held_out"
    )
    return 0


def main(argv: Optional[Sequence[str]] = None) -> int:
    """Command-line entry point."""
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    sub = parser.add_subparsers(dest="command", required=True)

    select = sub.add_parser("select", help="re-derive the draw and compare with the pin table")
    select.add_argument("--emit", action="store_true", help="print a PinnedDocument block on drift")
    select.set_defaults(func=_cmd_select)

    fetch = sub.add_parser("fetch", help="fetch pinned bodies and verify their text digests")
    fetch.add_argument("--refresh", action="store_true", help="re-download cached bodies")
    fetch.add_argument("--mirror-check", action="store_true", help="cross-check against govinfo")
    fetch.add_argument("--pause", type=float, default=0.3, help="seconds between mirror fetches")
    fetch.set_defaults(func=_cmd_fetch)

    pool = sub.add_parser("pool", help="pool candidates from three proposers")
    pool.add_argument("--external", default=EXTERNAL_SYSTEMS[0], choices=list(EXTERNAL_SYSTEMS))
    pool.add_argument("--interpreter", help="Python that has the external system installed")
    pool.set_defaults(func=_cmd_pool)

    worklist = sub.add_parser("worklist", help="draw the pilot sample and emit a worklist")
    worklist.add_argument("--seed", type=int, default=SELECTION.seed)
    worklist.add_argument("--out")
    worklist.set_defaults(func=_cmd_worklist)

    ingest = sub.add_parser("ingest", help="read a filled worklist and report")
    ingest.add_argument("worklist")
    ingest.set_defaults(func=_cmd_ingest)

    frozen = sub.add_parser("freeze", help="write the frozen reference set")
    frozen.add_argument("worklist")
    frozen.add_argument("--out")
    frozen.add_argument("--frozen-on")
    frozen.set_defaults(func=_cmd_freeze)

    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
