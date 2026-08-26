#!/usr/bin/env python3
"""Separate genre from provenance, on abstracts and bodies of the SAME articles.

The question this runner exists to settle
-----------------------------------------
``bench/run_monoculture.py`` measured a real ordering: the further a corpus's
gold authority sits from the Schwartz & Hearst family, the less of that gold the
family reaches, and the less parenthetical the gold is. MED1250 -- Ab3P's own
evaluation corpus -- annotates definitions that are ``98.91 %`` bracket-adjacent
and hands the independent proposers ``0.00 %`` of its gold pairs. PLOD-CW, whose
arbiter is each PLOS article's own author, annotates definitions that are
``61.36 %`` bracket-adjacent and hands the independent proposers ``32.04 %`` of
the proposal union.

D-065 then killed its own strong reading of that, and was right to:

    MED1250 is abstracts and PLOD is article body text. Abstracts carry no
    figure legends and no table footnotes, which is exactly where the unproposed
    class lives. So every figure is equally consistent with *the corpora were
    built by these systems* (provenance) and with *abstracts do not contain the
    hard cases* (genre).

**PMC gives both genres from the same articles.** Same authors, same journals,
same domain, same deposit -- an ``<abstract>`` and a ``<body>`` inside one JATS
file. Provenance is held constant *by construction*, so whatever difference
survives between the two halves is genre and nothing else.

The hypothesis, stated so it can lose
-------------------------------------
If figure legends, table footnotes and ``Abbreviations:`` rosters are the class
no Schwartz & Hearst descendant proposes, then they appear in **body text**
regardless of who built the corpus. So on a same-article split:

* the body half should be **less** parenthetical than the abstract half, and
* the body half should hand the independent proposers a **larger** share.

If it does, genre explains the MED1250/PLOD ordering on its own and the
monoculture's provenance reading stays dead. **If the two halves look alike,
genre does not explain the ordering and provenance is back in play.** Both
outcomes are publishable and this runner does not prefer either.

Two instruments, and they are not equally strong
------------------------------------------------
1. **Proposals and bracket structure** -- every accepted article. No gold is
   needed: the proposers of ``bench/run_monoculture.py`` run over each half
   separately and the union, the family share and the independent gain are
   recomputed per half. This is the weaker instrument in one specific way: it
   measures what the *proposers* see, so a class no proposer in the pool can
   reach is invisible to it in both halves alike.
2. **The authors' own abbreviation rosters** -- the subset of articles that ship
   a ``<def-list>`` in ``<back>``. This is the same arbiter PLOD-CW uses --
   Zilio et al. parsed each article's *Abbreviations* section -- taken at the
   source rather than through their pipeline. It lives in ``<back>``, which is
   in **neither** measured half, so it is a gold standard for the abstract and
   for the body symmetrically, and no abbreviation-detection system is anywhere
   in it.

   Admission compares **no character of the term against the definition**. That
   is not fastidiousness: filtering the roster by ``sh_alignable`` would build
   the S&H blind spot into the gold used to measure the S&H blind spot. The one
   comparison made between the two strings is whole-string equality, which is a
   de-duplication rule and not an alignment.

What this design controls, and the one thing it introduces
----------------------------------------------------------
It controls provenance, domain, author, journal, register and deposit route, all
by taking both halves from one file. It **introduces within-article
correlation**: an article whose author writes ``CT`` everywhere contributes many
correlated observations to both halves, so treating pairs as independent would
understate every interval. Every interval here is a **cluster bootstrap over
articles** -- resample articles with replacement, recompute the pooled ratio --
which is the only treatment that respects the design. Article identity is part
of every proposal key, so each article's contribution to a union is disjoint
from every other article's and a pooled share really is a ratio of per-article
sums.

Three halves, because length is the obvious attack
--------------------------------------------------
A body is roughly seventeen times the length of its abstract, so "the body half
has more of everything" is not a finding. ``body_matched`` is a contiguous
window of the body exactly as long as that article's abstract, taken at a seeded
uniform offset. Every per-half record is computed for it too, and rates per
100,000 characters are recorded beside every count.

Licence
-------
The PMC Open Access Subset is **not** uniformly CC BY and this runner does not
assume it is. Its own terms page says so in as many words -- "License terms
vary. Please refer to the license statement in each article" -- and the licence
mix on this runner's own draw is measured and recorded rather than asserted. Only
``CC BY`` and ``CC0`` articles are admitted; ND, NC, SA and text-mining-only
articles are counted and dropped. See :data:`PERMISSIVE_LICENCE_CODES` and
``data/LICENSES.md``.

Retrieval is through the **PMC Cloud Service** on AWS, which that same page names
as one of four services that "may be used for automated retrieval of PMC
content", adding that systematic retrieval by any other automated process is
prohibited. The legacy FTP mirror the August 2026 audit measured is gone: see
:data:`FTP_RETIREMENT_NOTE`.

Usage::

    python bench/run_genre.py --draw 500        # re-draw a candidate list (prints ids)
    python bench/run_genre.py --fetch           # fetch the pinned ids into data/
    python bench/run_genre.py --fetch --record  # ... and print the manifest digest
    python bench/run_genre.py --verify          # re-check what is on disk
    python bench/run_genre.py --save --interpreter C:/akbench/Scripts/python.exe

Without ``--interpreter`` the S&H family is this library's three profiles alone.
Every record names its proposers, for the reason ``bench/run_monoculture.py``
gives: a matrix computed over a subset is not the same matrix.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import re
import sys
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from bench.run_monoculture import (  # noqa: E402
    EXTERNAL_SH_SYSTEMS,
    PROFILES,
    Passage,
    Proposals,
    alignment_record,
    bracket_adjacent,
    edge_keys,
    environment,
    gold_class_record,
    gold_reach,
    locate_pair,
    normalise,
    overlap_record,
    run_acronymkit,
    run_allcaps,
    run_external,
    run_shapecue,
    save_results,
    score_spans,
    sh_family,
    vertex_keys,
)

Pair = Tuple[str, str]
CharSpan = Tuple[int, int]

# ---------------------------------------------------------------------------
# 1. The source, its terms, and the pins
# ---------------------------------------------------------------------------
#: The PMC Cloud Service bucket, served over HTTPS with no credential. This is
#: the successor to the FTP tree ``docs/AUDIT-2026-08.md`` probed on 2026-08-23.
CLOUD_BUCKET = "https://pmc-oa-opendata.s3.amazonaws.com"

#: Where the terms quoted in this module's docstring were read.
PMC_OA_TERMS_URL = "https://pmc.ncbi.nlm.nih.gov/tools/openftlist/"

#: When. Operating rule 4 needs both halves: a bare licence name is a conclusion
#: with the evidence thrown away.
PMC_OA_TERMS_READ_ON = "2026-08-25"

#: The PMC copyright notice the subset page defers to for per-article terms.
PMC_COPYRIGHT_URL = "https://pmc.ncbi.nlm.nih.gov/about/copyright/"

#: What the audit's one surviving reason to mirror PMC is worth today, measured
#: rather than carried. ``docs/AUDIT-2026-08.md`` recorded on 2026-08-23 that the
#: pinned ``oa_comm`` path was already 404 and that the content survived under
#: ``deprecated/``; D-020 item 3 recorded a retirement deadline of
#: 24 August 2026. The deadline fired.
FTP_RETIREMENT_NOTE = (
    "ftp.ncbi.nlm.nih.gov/pub/pmc/ held two files on 2026-08-25 -- PMC-ids.csv.gz "
    "and readme.txt. Every bulk path the audit probed returns 404, including the "
    "deprecated/ mirror it found up. The readme states that all legacy PMC Article "
    "Dataset files 'are in the process of being removed from the FTP Service' and "
    "that 'All files are now available via the updated PMC Cloud Service'. The "
    "5.27M-full-text mirror the audit reserved a decision about is not fetchable "
    "from the host the audit measured."
)

#: Licence codes this runner admits, as they appear in each article's metadata
#: JSON. Everything else is counted and dropped, which is a finding rather than
#: plumbing: the subset is not uniformly CC BY.
PERMISSIVE_LICENCE_CODES = ("CC BY", "CC0")

#: The sampling frame, written down because a draw with no stated frame is not a
#: sample. Uniform over PMC identifier integers in ``[DRAW_ID_LOW, DRAW_ID_HIGH)``,
#: version 1 only, seeded. It over-weights whatever identifier ranges PMC's
#: open-access coverage happens to be dense in. That is a real bias, it is not
#: corrected, and it is orthogonal to the contrast: both halves come from the
#: same articles, so any draw bias lands on both halves equally.
DRAW_SEED = 20260825
DRAW_ID_LOW = 100_000
DRAW_ID_HIGH = 12_000_000

#: Seed for the ``body_matched`` window offsets. Separate from the draw seed so
#: that re-drawing does not silently move the windows of an unchanged sample.
WINDOW_SEED = 8152

#: Seed and replicate count for every cluster bootstrap in this file.
BOOTSTRAP_SEED = 31337
BOOTSTRAP_REPLICATES = 2000

#: Where fetched articles land. Git-ignored via ``data/*``.
DATA_DIR = REPO_ROOT / "data" / "pmc_oa_genre"

#: The manifest the fetcher writes and ``--verify`` re-checks.
MANIFEST_PATH = DATA_DIR / "manifest.tsv"

#: The licence census of the draw that produced :data:`PINNED_PMCIDS_TEXT`, as
#: ``python bench/run_genre.py --draw 2000`` printed it on 2026-08-25. Every
#: probe is counted, including the ones that hit nothing, so the permissive
#: share below is a measured quantity rather than a restatement of the filter.
#: It is a constant because the Cloud Service is continuously updated and a
#: later re-draw would census a different bucket -- which is the same reason the
#: identifiers themselves are pinned.
DRAW_CENSUS_TAKEN_ON = "2026-08-25"
DRAW_PROBES = 5376
DRAW_CENSUS: Dict[str, int] = {
    "CC BY": 1999,
    "(no such article version)": 1923,
    "(not in the open-access subset)": 373,
    "CC BY-NC-ND": 312,
    "CC BY-NC": 300,
    "(no licence code)": 172,
    "(historical OCR)": 140,
    "CC BY-NC-SA": 119,
    "CC0": 14,
    "(retracted)": 12,
    "TDM": 11,
    "CC BY-ND": 1,
}

_USER_AGENT = "acronymkit-bench/0.3 (+https://github.com/pierce-lonergan/acronymkit)"

#: The drawn article identifiers, pinned. A candidate list is what makes the draw
#: reproducible independently of bucket churn: PMC adds, updates and occasionally
#: removes article versions continuously, so re-running the draw against a later
#: bucket would not return this sample, and a digest alone could not tell a
#: changed article from a changed draw.
PINNED_PMCIDS_TEXT = """
10797626 3172634 11210761 11484921 3877192 4370877 10938800 10532005 9495179 8451146 5336693
5748298 11409232 9747051 9221552 4612427 4923065 7538443 10706763 5036436 4857045 6267086
7730833 3367341 9012776 7749800 9793634 10578242 7025463 9973310 6155261 6771964 6571523
9871792 11199256 10212571 9533212 8710167 7067896 11811815 3388363 5658142 8934496 4096508
6561562 3832656 11690954 11355287 5717092 9445928 8476634 9777287 5636887 11899061 3860049
7349250 9993321 8621804 10791419 10748000 7082309 6539107 8401149 10100209 8787766 7805904
4776122 11680028 11631449 9038826 6852405 10334841 3588039 7566486 11228109 6657406 3262604
11923449 8481301 8268430 9670373 6829736 10740626 5328395 6290613 7683491 9078823 9321348
7011961 10453594 8446553 6930756 7093333 11955837 9751448 8213254 7399011 6353876 8063477
10297272 4469962 6208160 3403983 8425529 8125515 2441610 3294503 9567765 8749506 10073392
8301398 10239044 3931664 9207926 7561707 9134705 9039271 5858269 6105629 6058254 10183030
7284335 10422220 7382473 3560232 10193026 1459178 9780978 4660435 4919648 8856547 11892681
9636270 10999558 11765166 5989942 2423529 9803348 2276487 5112671 9828679 7284713 8402182
7698772 3835472 10470887 4942656 11955289 4830257 9601966 6359865 6717058 11172650 9180373
8400867 3398021 6052545 11668701 5319318 4593328 10255554 11173998 1367854 523842 7318107
5818523 10436484 4127648 10663593 5428479 5942851 5837087 8190618 3674619 6180970 4657099
6398180 10053789 3946193 5005538 4471072 6034791 9475140 4773570 3040916 9868578 7352359
8583561 7211838 3884314 10048864 10307204 6636046 11868049 7646293 9515784 8239828 3897518
3979045 11175786 3961331 10689540 11148399 8184778 10416924 3142526 5797481 6041266 8525493
4581518 6811936 11747040 10356760 4887632 10764429 7240871 7426610 3997863 10419794 2890919
6094455 11895789 7788775 9205947 9858423 7484496 7578374 7609773 8955214 6947864 4459762
10625174 2886006 3363218 5087660 8840408 9475719 4306753 5360442 4496218 4619837 8389449
9269410 7943020 9604621 10961359 7718655 11085772 5994396 8191394 3488817 3531514 7691316
3275468 3231265 9822741 10267362 4929979 11277310 6723594 7060409 5026009 9472779 8218558
4412480 2960723 4186466 9393725 4013081 10131994 10784115 6946672 11225460 4118614 11764013
4430495 10223595 4763239 11165869 9741311 10120911 6298786 6428701 4475256 7662616 10989972
8554667 9021764 4479227 8877162 7406226 11197563 3579468 8820252 4771685 5961603 8044899
7346655 7734830 6538991 10235610 4160560 9601419 5598202 6132421 3627610 3490922 8621794
9144916 4074427 9572840 9618333 10707850 6882900 10919244 9962824 6058385 10763686 3973684
11362504 7728748 11545703 10777993 8143500 10790442 11841139 3742651 8294297 11349692
2800901 9872737 8150298 11839815 7376502 11405239 4151281 6765361 8493803 6323087 4709488
4409613 7690032 7241243 10294533 4475778 3943604 11187293 4537769 9888352 8617030 5671543
11180521 6141547 6265771 10386209 8121414 9627153 5037867 2362250 6547457 8548471 6692949
4684578 6709744 10631117 4617722 8032845 9821047 3820756 2806918 4568805 2570928 9556320
11885505 10734505 5733559 9722788 7067756 11520478 10808427 11860701 11430005 9219553
8848656 11634921 6267477 8742357 6878795 5922372 8468029 9567246 10173891 10093065 7333248
8447612 5393560 4114693 3980314 10146768 11661382 10026086 7641442 11678115 4678946 10473346
4513294 4769129 10143572 4592958 10682373 11239386 11003009 6004695 9144932 8609882 3570972
10748068 4727672 8653828 7282380 10155325 5792739 8387679 4531826 10178874 9460258 7957197
6199288 8289471 8056725 11913265 10157217 6629086 7590622 3009142 7874631 8749456 7783408
9961600 8785436 6266111 3157158 11457165 3480456 8818629 8076642 10174309 8469714 11403411
9988286 10396761 8998055 8394465 4999293 7229812 10627451 2768783 10972629 10014438 9670390
10508089 11085237 6114506 7782821 7420728 10108977 11788318 6259199 5524659 9690246 10829765
11343969 9230500 1764749 10202824 4777725 4514940 8996844 11351149 8894459 10634397 10021149
5234148 11202025 11803542 5974003 11575446 5736520 3502753 5471732 11212161 8000479 11855010
2362666 5748533 9943801 9641280 9340298 10976948 9067162 11588909 7790177 8531107 9856652
4426538 4573684 7758127 9473917 7444743 10059005 11457446 11751696 7210297 8632834 8073038
7279354 6186045 3857287 8864916 10997596 7923382 9032273 4221906 7293691 3740476 10302593
3944983 9643354 6066578 6297276 3649383 3797398 5295610 3447969 5980998 11749566 4762203
10253791 10924172 11505919 4223513 11991874 4745097 7487923 8522887 4512773 6945290 4251634
6875325 4847864 1635570 8411472 8268510 6730888 9047899 9034926 6429198 2834576 4798587
10718288 8525993 10989701 10002271 5467414 10040639 10678605 4599890 5707088 9532951
10702362 8712097 4991799 4112715 6280418 5094953 10837969 4289287 3640909 11842168 8467985
9604331 8394955 6082943 7245898 5706397 6257258 6900879 8232215 7042215 7890527 9143690
8465496 7170378 11814855 6182822 11208985 8622395 6747085 9605240 9451234 10085706 5572491
8770423 8114966 6401590 3718813 9893977 4613264 8759662 3379110 8564527 11860829 11596893
11023554 5962683 11069081 10146953 11634470 9104190 5649817 7396684 9877018 4239648 3918264
6197073 9444460 5302155 3251870 11208694 6815582 8034405 5513206 3128607 10161067 6851710
2848149 8669064 4693927 7760868 7746265 9165198 4706567 9069668 9867478 10143341 7401506
11239017 9862597 3912622 7769348 5853727 4320475 11848911 8979493 6783541 7434833 10219257
7725742 10831178 4888305 8716961 4661699 10043176 10284847 10173090 8775975 11595597 5626171
11256069 8546232 8688754 7593841 3766257 5823431 3463454 5431651 6849189 11291330 8049604
10610809 10106681 4883255 5833102 11712063 9880153 8213330 10859523 6269794 8581628 10422159
3588678 8491743 6685142 9958934 5450100 8854741 5091276 4277786 8145592 4647617 10911610
5884753 4132935 8330629 11797025 6021429 7732329 9705498 5856365 10737387 7915005 6212512
9280440 4544557 8326911 4959823 10434899 7654039 3997960 3040662 4492816 9792607 7718261
10941998 3907313 6817826 11273225 2977399 9158233 5814582 9631170 9044869 6882400 7742151
2674422 4172726 7687724 11785300 9905418 11713647 5875174 6678410 11437704 4947105 8396929
6149011 7771451 2212630 7536277 10489806 7809279 5378195 10186554 7244504 7177898 4399147
7367390 2500030 10910693 8225702 6120131 9317167 11860421 11292135 10982412 3742789 8586203
11993476 9100623 3991076 11412442 11973256 9163404 10307087 3224765 11727003 6517963 9980771
11973808 7245914 9103918 6649209 11184213 9610364 3264520 7781801 5862838 3998394 4982254
9614755 11335793 10871056 11206875 4546134 4478119 10032030 9267350 8382153 10982766 9577942
7019262 4428002 3928095 7439208 9142510 7222530 10458804 5469673 7614201 5970482 7213975
7293971 10441742 10929173 11142665 7455711 9797634 10962542 5834196 6555938 8024358 3016305
3977423 9410363 5943560 5388121 4853391 6915463 10572797 8399113 6812782 8455570 9635157
9115834 6658205 3505740 3439976 8670969 8749605 10273532 5546391 7530664 10808471 8429498
10552424 9923468 3533814 5220324 3391890 4740833 6929043 9270409 9098474 11088366 8123627
8811667 5732256 11352424 9047413 4888150 9650910 11672922 3184272 3024991 8197356 9010864
3205070 7096404 10902389 10260333 7981929 11091560 10935923 3937361 9687030 8049941 3623760
4917111 10853344 6587114 3483188 4129920 6133686 11127462 4043403 11716579 11392857 4214743
6303887 7282368 7382178 5558021 9391038 7333244 4107491 2258414 9953868 4777572 9108152
9238273 7925321 8229220 7252747 7362483 6203385 9474534 10834464 8903687 11031927 8251627
11709637 7054358 9318709 10759501 4166016 3119700 5127877 3793868 8893053 6584873 5848818
9912992 1459160 5417433 9177325 7013424 8620936 10522270 2584948 5307400 11237663 7259657
7539921 5342702 5217334 10039936 10764924 6277448 10076605 8190409 8507375 3579473 5990606
10135696 9911778 6789043 9175844 10939544 7024993 3325940 3283603 3447676 3917865 7926862
5696238 5433056 4391166 11348109 10417344 10098097 7277301 9977236 10383251 2796185 10184081
11246427 4661732 7661384 5893782 2797297 7862683 5806269 11625352 11043481 11667689 5129641
10488537 3912177 4424446 8003827 6018344 8415364 5738567 8959565 6355991 11685143 7052384
8586199 7366672 3277099 7143070 7588369 3194696 9181734 2917082 6445897 8593796 10700206
10003044 7943417 5877123 6896183 7001329 3503720 6170443 10086081 11767186 6692320 10958893
11252951 11395504 8677803 6102411 10936810 7226983 9866200 6799837 3530181 6484333 9763443
4012792 10084206 10604205 10676824 10754720 10915395 8509549 4774924 6637900 5680304 9999204
7010602 7843789 6524811 5688729 3216262 10585050 5431801 6997132 8532804 8954996 11568804
5238571 11596015 5479852 10971002 10681895 7582155 6501022 10130531 4143625 10151761 8311462
5969512 8483936 5559613 10413131 8623018 8024473 5345130 10952762 10278232 6946972 10912941
7020451 10590647 6751796 4209955 6318294 9142885 9654630 10204500 4997714 3297856 6236819
8576351 3032643 11239774 11231956 10585105 7592042 8394939 5970137 7143206 9297645 3194736
11400969 11661156 7248771 7540417 4382535 9377801 11823679 11662164 10488987 10341394
9646563 11889703 5558354 5789368 9913704 4774850 4709848 6724176 4177825 10933561 3724604
9209520 7835302 10725309 2898018 10217674 7020495 4528062 6944478 11367009 7613285 7738754
9680943 1867825 7696101 8445935 4459487 9502378 7758977 10622516 11587122 6761279 8333618
7711609 9078012 11085872 11371566 4177162 3108125 7515702 5014305 6566352 8399891 5341456
9640392 11271295 8927050 9235920 5884441 10469699 9531233 11762351 6611436 5064025 9207030
10788721 9574095 8946504 3252347 6690962 10732326 2721544 6051112 5651644 8754339 6244233
11323132 8857557 6952441 4179182 11364986 10848073 6511183 11290961 4541073 10811897 5344663
5557310 10512291 9325948 3089796 5887921 4706721 11313631 10218224 11355392 10961270 7042520
2933530 6220484 9681805 6727052 11432364 7726110 9773135 9653400 10431214 7356368 3017525
8965706 9638995 9407522 11434535 8621456 8811982 7264223 11492217 2845813 11597754 10923866
3712139 6791862 9663693 6900039 7506932 10414674 3997511 7427300 8722385 9553446 10181254
6836165 4018666 5410222 2042018 4556734 11139873 10990044 9009966 1779562 10678511 3403674
5712985 3115864 6151369 9845328 10977893 3411723 2646684 5129264 4101367 5893836 11940830
5591433 8032774 8357370 6423225 9900046 10461053 3494609 10497499 10017692 11076362 6319333
6387363 7577840 11647218 4445496 8665791 8917177 9382722 10605079 10300731 3427187 11181934
7216249 5131083 8663502 11932914 4223856 6534366 8182490 8361085 10407117 8519440 8920321
8037718 11504928 11452758 10510223 5482436 8638571 2803942 10618103 10653889 11302858
9107849 3363180 10179945 11480067 10067575 10786067 8103655 11301270 10352438 8912838
7601612 7847993 10191214 10354073 11479972 11980366 8408036 5523166 8893720 7113522 7997828
7722535 7732987 9649415 5548902 10049361 8739968 5874500 11448148 11102075 10700372 8833226
3399876 6008528 4521874 9330725 2671547 11709945 8458438 3612044 9894920 3530754 4645044
6111796 9885697 11357085 2875658 8428076 3514328 11573731 7614724 8481544 3246437 8757693
9364766 11938713 4983661 4913244 6071392 7599154 3208529 9399957 9939121 5356407 3363194
10977175 4396162 3380859 6111214 7384173 10883924 11048714 11936194 9675168 11961442
11868685 6767057 10896136 8266537 7618392 6273779 3344166 11373045 4991284 6549984 8718613
7787239 8231149 4995663 11542354 11376657 6497680 6425438 6982256 2968092 11062386 11361588
6636522 4902239 7176798 4595251 1965466 5571168 11025484 5557969 4363247 6196259 8575385
8856557 3756331 10816027 6164048 7566128 6454634 9962232 4862074 10534249 8529229 3200063
4734404 11642711 6154529 7072271 5536151 11430262 10420940 3215676 8656812 7201527 8590650
6571108 4816620 10244625 9246045 10935557 7197987 9754727 10101566 7198124 9537355 5449059
9297674 4875637 10254352 3663698 3338917 8703844 9486839 11802427 8644436 11597822 7248018
10132406 11167856 5762815 1890920 11397743 4257725 8055713 5556249 9573480 9307108 2687864
5029607 10222811 9407075 8879817 5645107 8932604 7612940 5304641 7529761 11690464 4899386
6985549 7958161 9427246 6274882 8423133 9820104 10824559 5699862 9422405 5504128 11972079
10851115 4320612 8810089 11839691 4934303 9212146 6102239 11854387 5899855 11501923 5888536
6491983 5531565 10815191 3621666 4404326 11716249 8226529 6278552 3290630 8123487 11885856
1766926 8455395 7687714 11309397 3639078 3118708 9859466 6686022 5496924 8860281 3724159
8371737 9653169 3820837 11795430 8582244 10921228 5613105 10882737 11143008 7367843 11048506
10681729 2938411 5342382 8424659 7769469 9883953 6023332 10033965 9886624 8423437 2374663
11492079 9119648 6196291 4406428 9998510 9587033 10741660 8392415 9142302 11171404 7483446
10778110 3272789 9570013 9698005 8343990 6975050 6566294 9886690 2515844 2424005 11479922
3167644 2409660 10420875 8264776 7588007 5419799 10097793 7347121 10112059 4610385 10778891
11343399 10793140 6852587 5728527 6677290 7445426 9594021 10685835 8810755 9821112 11120687
8698218 11940229 8794920 7145883 7824850 3284394 8521365 10036485 6103261 6380313 6282064
9945384 7142881 9045148 9013685 10152631 7247690 5924374 10512251 10647726 7246721 11417811
4747681 10230483 9340772 6271163 5982774 6104179 11669644 3299680 2907694 7732399 7250986
4917727 10638556 3373635 7015667 8317995 7602944 11121478 2899994 11406483 6604511 8703770
9323616 6713095 4849659 9165489 1676012 4195885 4136308 4488369 6288043 9184078 8757956
8115455 8256609 2675102 8433090 9601512 6406913 10732459 8939213 10285196 11089104 10088884
4729706 3934447 11410947 11689348 2409936 10738399 4700260 8480522 6922497 3504812 10111664
10763362 9331876 10477226 8869144 3527029 9161844 8617752 4024026 8355157 6025235 9600309
7828388 6153857 7085777 10883978 6838213 11875120 7331812 9635335 7098963 4492086 3671734
7761090 6069489 3671146 3495055 8198789 10463530 7026025 9432795 4381332 3734606 4225155
8317853 7677571 11766897 6427202 8312490 5835299 11923905 7411018 4969841 3470194 5324244
5437673 9813051 9731998 8759892 9824357 11405820 11619259 4732620 8651575 5125271 4978964
9076805 5729456 10938372 9132289 6775373 8157372 11973134 9203363 10942845 6006861 11771915
9268451 4923997 9687038 6058017 3096659 9329591 11360274 9253816 7806552 3483168 5720829
7316819 11018193 9638980 9819011 8466338 9086520 2581734 6084540 8803550 9680607 9139864
6044533 8427601 11869571 5338278 11286280 10678458 11940706 8979532 4489943 8545561 8199287
8359398 3827187 6961075 7832335 8007541 5146940 10333182 3915823 5095052 10669744 7315133
7611889 5578332 9684564 6723041 5612993 7150700 9764471 9781770 2868354 5609243 9614074
4039518 6658961 11088107 2564930 2409512 4431600 10085753 8242779 7908140 11690968 3055714
7967787 9641527 4483716 11888054 8128543 5268782 7526410 4415924 8373882 5937544 7988364
5323819 7681175 8545836 11065956 9768467 9740298 9382625 8998431 11898517 2950140 3247026
7298019 8613414 8807142 10102019 3882664 4287225 7928032 11863120 11819600 7346167 3329036
6021349 10575368 4719932 7616594 5445035 9774603 9991918 6255792 7252402 6478124 9835320
8849325 7644814 11276474 9522499 9664211 4759562 11446620 8899459 11723174 9021923 7617876
3907517 10662706 11493799 6890729 5971246 11294415 4976356 10887658 9891394 1810241 9566363
3819884 3522683 3694528 9891248 4585373 10517543 5632448 7961590 9289680 9515430 10696873
8464012 10138335 9032923 5037914 10094771 11799297 9573345 9867673 10660526 7470096 11430382
3517529 11241135 7876522 10386329 3588034 11548838 10459955 6499765 9503517 9170847 9406165
7493323 5297753 8728300 9540551 2403744 10243774 9953711 11483860 5862482 4371217 8384508
9395532 10608677 9571243 11636989 5240018 6749907 10401714 5837629 4819287 1775067 6084643
10396373 5580327 5748586 9858977 8747309 7969765 11182848 11607486 5114282 4423878 11777081
7803980 10054867 5336291 11040903 10221141 6480580 4983679 9752698 8651421 4079966 10256645
5552959 8224647 9086555 11690871 6249876 11946615 3397374 8367118 6154632 9991419 8396970
6727087 9727399 8399560 6402232 8919572 6463675 5107574 10823002 11393994 9598096 8556620
4640512 6052851 4767934 3065215 7972452 11241436 10477150 11644688 8434442 10254150 8438895
9412284 6225575 7597258 10924702 7260072 4059094 10262691 3142483 8897841 8785382 7818270
7465270 8484760 2729423 11642697 6163620 4830518 11044578 11229216 9426492 7667692 8424318
2699652 2585560 10002191 10658194 8679896 11142808 8240081 6627652 9403742 4487724 10175752
4130475 4867685 2684660 3942494 10295199 11954317 6519676 6408204 7928677 9965717 10625505
4916783 10163748 8383253 4709334 7796083
"""

#: One digest over ``"{pmcid}\t{sha256}\n"`` for every pinned article, sorted by
#: identifier. Empty means "not yet recorded"; ``--fetch --record`` computes it.
PINNED_MANIFEST_SHA256 = "18f80256a40cc8c6a2fb0d01872a039bb93c710ff3415a6c7e97beda082c0928"


def pinned_pmcids() -> Tuple[int, ...]:
    """The pinned draw, parsed from :data:`PINNED_PMCIDS_TEXT`.

    Returns:
        The identifiers in draw order. Empty before the first draw is pinned.
    """
    return tuple(int(token) for token in PINNED_PMCIDS_TEXT.split())


# ---------------------------------------------------------------------------
# 2. Fetching
# ---------------------------------------------------------------------------
def _get(url: str, timeout: float = 90.0) -> bytes:
    """Fetch one object from the Cloud Service.

    Args:
        url: Absolute URL.
        timeout: Socket timeout in seconds.

    Returns:
        The response body.

    Raises:
        urllib.error.HTTPError: Propagated. A 404 is how a missing article
            version is detected, and callers handle it.
    """
    request = urllib.request.Request(url, headers={"User-Agent": _USER_AGENT})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        payload: bytes = response.read()
    return payload


def metadata_url(pmcid: int) -> str:
    """The Cloud Service key holding one article's metadata JSON."""
    return f"{CLOUD_BUCKET}/PMC{pmcid}.1/PMC{pmcid}.1.json"


def xml_url(pmcid: int) -> str:
    """The Cloud Service key holding one article's JATS XML."""
    return f"{CLOUD_BUCKET}/PMC{pmcid}.1/PMC{pmcid}.1.xml"


def fetch_metadata(pmcid: int) -> Optional[dict]:
    """One article's metadata JSON, or ``None`` when version 1 does not exist.

    Args:
        pmcid: The numeric part of a PMC identifier.

    Returns:
        The parsed JSON, or ``None`` for any HTTP or decoding failure. A miss is
        the common case -- most identifiers in the frame are not in the
        open-access subset -- so it is a return value rather than an exception.
    """
    try:
        return dict(json.loads(_get(metadata_url(pmcid))))
    except (urllib.error.URLError, ValueError, OSError):
        return None


def licence_verdict(meta: Optional[dict]) -> str:
    """One bucket of the draw's licence census.

    Args:
        meta: An article's metadata JSON, or ``None`` if it does not exist.

    Returns:
        A bucket label. ``"(no such article version)"`` for a miss,
        ``"(not in the open-access subset)"``, ``"(retracted)"``,
        ``"(historical OCR)"``, ``"(no licence code)"``, or the article's own
        ``license_code`` verbatim.
    """
    if meta is None:
        return "(no such article version)"
    if not meta.get("is_pmc_openaccess"):
        return "(not in the open-access subset)"
    if meta.get("is_retracted"):
        return "(retracted)"
    if meta.get("is_historical_ocr"):
        return "(historical OCR)"
    code = meta.get("license_code")
    if not code:
        return "(no licence code)"
    return str(code)


def draw(
    target: int,
    *,
    seed: int = DRAW_SEED,
    low: int = DRAW_ID_LOW,
    high: int = DRAW_ID_HIGH,
    workers: int = 8,
    probe_cap_factor: int = 40,
) -> Tuple[List[int], Dict[str, int], int]:
    """Draw article identifiers uniformly from the frame until ``target`` pass.

    Args:
        target: How many admissible articles to accept.
        seed: Draw seed.
        low: Inclusive low end of the identifier frame.
        high: Exclusive high end.
        workers: Concurrent metadata requests. Deliberately modest: the Cloud
            Service is a public good and this is not a bulk harvest.
        probe_cap_factor: Stop after ``target * probe_cap_factor`` probes, so a
            bucket outage cannot turn a draw into an unbounded loop.

    Returns:
        ``(accepted_ids, licence_census, probes)``. ``accepted_ids`` is in draw
        order; the census counts **every** probe including the misses, which is
        what makes the permissive share a measured quantity rather than a
        restatement of the filter.
    """
    rng = random.Random(seed)
    seen: set = set()
    accepted: List[int] = []
    census: Dict[str, int] = {}
    probes = 0
    cap = target * probe_cap_factor
    with ThreadPoolExecutor(max_workers=workers) as pool:
        while len(accepted) < target and probes < cap:
            batch: List[int] = []
            while len(batch) < workers * 8 and len(seen) < (high - low):
                candidate = rng.randrange(low, high)
                if candidate in seen:
                    continue
                seen.add(candidate)
                batch.append(candidate)
            if not batch:
                break
            for pmcid, meta in zip(batch, pool.map(fetch_metadata, batch)):
                probes += 1
                verdict = licence_verdict(meta)
                census[verdict] = census.get(verdict, 0) + 1
                if verdict in PERMISSIVE_LICENCE_CODES and len(accepted) < target:
                    accepted.append(pmcid)
    return accepted, census, probes


def fetch_articles(pmcids: Sequence[int], *, workers: int = 6) -> Dict[int, str]:
    """Download each article's JATS XML into ``data/pmc_oa_genre`` and digest it.

    Args:
        pmcids: The pinned draw.
        workers: Concurrent object requests.

    Returns:
        ``{pmcid: sha256}`` over the fetched bytes.

    Raises:
        SystemExit: If any pinned article cannot be fetched. A sample missing
            members is a different sample, and silently continuing would publish
            a figure over a denominator nobody chose.
    """
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    digests: Dict[int, str] = {}
    missing: List[int] = []

    def one(pmcid: int) -> Tuple[int, Optional[bytes]]:
        target = DATA_DIR / f"PMC{pmcid}.1.xml"
        if target.is_file():
            return pmcid, target.read_bytes()
        try:
            return pmcid, _get(xml_url(pmcid))
        except (urllib.error.URLError, OSError):
            return pmcid, None

    with ThreadPoolExecutor(max_workers=workers) as pool:
        for pmcid, payload in pool.map(one, pmcids):
            if payload is None:
                missing.append(pmcid)
                continue
            (DATA_DIR / f"PMC{pmcid}.1.xml").write_bytes(payload)
            digests[pmcid] = hashlib.sha256(payload).hexdigest()
    if missing:
        raise SystemExit(f"{len(missing)} pinned article(s) could not be fetched: {missing[:10]}")
    return digests


def manifest_text(digests: Dict[int, str]) -> str:
    """The canonical manifest rendering that :data:`PINNED_MANIFEST_SHA256` digests."""
    return "".join(f"PMC{pmcid}\t{digests[pmcid]}\n" for pmcid in sorted(digests))


def write_manifest(digests: Dict[int, str]) -> str:
    """Write ``data/pmc_oa_genre/manifest.tsv`` and return its digest."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    body = manifest_text(digests)
    with MANIFEST_PATH.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(body)
    return hashlib.sha256(body.encode("utf-8")).hexdigest()


def verify() -> int:
    """Re-digest every pinned article on disk against the recorded manifest.

    Returns:
        Process exit code: 0 when every pinned article is present and matches.
    """
    ids = pinned_pmcids()
    if not ids:
        print("no draw is pinned; run --draw first")
        return 1
    digests: Dict[int, str] = {}
    problems: List[str] = []
    for pmcid in ids:
        path = DATA_DIR / f"PMC{pmcid}.1.xml"
        if not path.is_file():
            problems.append(f"missing: {path.name}")
            continue
        digests[pmcid] = hashlib.sha256(path.read_bytes()).hexdigest()
    computed = hashlib.sha256(manifest_text(digests).encode("utf-8")).hexdigest()
    print(f"{len(digests)} of {len(ids)} pinned article(s) present")
    print(f"manifest sha256 {computed}")
    if PINNED_MANIFEST_SHA256 and computed != PINNED_MANIFEST_SHA256:
        problems.append(f"manifest digest differs from the pin {PINNED_MANIFEST_SHA256}")
    for problem in problems:
        print(f"  PROBLEM {problem}")
    return 1 if problems else 0


# ---------------------------------------------------------------------------
# 3. Reading JATS into two halves and a roster
# ---------------------------------------------------------------------------
#: Elements whose text is dropped before either half is rendered.
#:
#: ``xref`` is the load-bearing one and it is not tidiness. A body cites and an
#: abstract does not, so leaving ``[<xref>12</xref>]`` in place would put a
#: bracket beside a body token roughly once a sentence and inflate the body
#: half's bracket-adjacency -- against the hypothesis under test, but by an
#: artefact rather than by prose. The empty ``[]`` the removal leaves behind is
#: swept by :data:`_EMPTY_BRACKETS`, and the sweep's firing count is recorded.
_DROP_TAGS = frozenset(
    {
        "xref",
        "disp-formula",
        "inline-formula",
        "tex-math",
        "graphic",
        "inline-graphic",
        "media",
        "object-id",
        "alternatives",
        "ext-link",
    }
)

#: Elements after which a newline is emitted, so that a table cell and the cell
#: below it do not render as one word.
_BLOCK_TAGS = frozenset(
    {
        "abstract",
        "ack",
        "body",
        "boxed-text",
        "caption",
        "def",
        "def-item",
        "def-list",
        "disp-quote",
        "fig",
        "label",
        "list",
        "list-item",
        "p",
        "sec",
        "statement",
        "table",
        "table-wrap",
        "table-wrap-foot",
        "tbody",
        "td",
        "term",
        "th",
        "thead",
        "title",
        "tr",
    }
)

#: What a removed ``xref`` leaves behind.
_EMPTY_BRACKETS = re.compile(r"[(\[]\s*[,;\u2013\u2014-]*\s*[)\]]")

_BLANKS = re.compile(r"[ \t]+")
_NEWLINES = re.compile(r"\n{3,}")


def _local(tag: str) -> str:
    """The local name of a possibly namespaced ElementTree tag."""
    return tag.rsplit("}", 1)[-1] if tag.startswith("{") else tag


def _render(element: ET.Element, out: List[str]) -> None:
    """Append ``element``'s renderable text to ``out``, block by block."""
    name = _local(element.tag)
    if name in _DROP_TAGS or element.tag.startswith("{http://www.w3.org/1998/Math/MathML}"):
        return
    block = name in _BLOCK_TAGS
    if block:
        out.append("\n")
    if element.text:
        out.append(element.text)
    for child in element:
        _render(child, out)
        if child.tail:
            out.append(child.tail)
    if block:
        out.append("\n")


def render(element: Optional[ET.Element]) -> Tuple[str, int]:
    """Render one JATS element to plain text.

    Args:
        element: The element, or ``None``.

    Returns:
        ``(text, empty_bracket_pairs_removed)``. The second value is the firing
        count of the citation sweep, recorded because a cleaner that silently
        rewrites the very characters the measurement is about has to say how
        often it acted.
    """
    if element is None:
        return "", 0
    parts: List[str] = []
    _render(element, parts)
    text = "".join(parts)
    text, removed = _EMPTY_BRACKETS.subn(" ", text)
    text = _BLANKS.sub(" ", text)
    text = _NEWLINES.sub("\n\n", text)
    return text.strip(), removed


def roster_pair_admissible(term: str, definition: str) -> bool:
    """Is this ``<def-item>`` an abbreviation roster entry?

    Every condition is a property of one string on its own, except the last,
    which is whole-string equality and therefore a de-duplication rule rather
    than an alignment. **No character of ``term`` is compared against any
    character of ``definition``**, because a gold standard filtered by the
    Schwartz & Hearst alignment could not be used to measure what that alignment
    misses.

    Args:
        term: The ``<term>`` text.
        definition: The ``<def>`` text, whitespace-collapsed.

    Returns:
        True when the pair is admitted as gold.
    """
    if not 2 <= len(term) <= 15 or any(character.isspace() for character in term):
        return False
    if not any(character.isalpha() for character in term):
        return False
    if not any(character.isupper() for character in term):
        return False
    if not 3 <= len(definition) <= 120:
        return False
    if not any(character.isalpha() for character in definition):
        return False
    return term.casefold() != definition.casefold()


class Article:
    """One PMC open-access article, split into the units this runner measures.

    Attributes:
        pmcid: Numeric identifier.
        licence_code: The metadata JSON's ``license_code``.
        licence_ref: The ``ali:license_ref`` URL from the article's own
            ``<permissions>`` block, which is the per-article licence read from
            the article rather than from the index. Empty when absent.
        abstract: Rendered ``<abstract>`` text from ``<front>``.
        body: Rendered ``<body>`` text. Excludes ``<back>``, so it excludes the
            roster below.
        roster: Author-declared ``(short form, long form)`` pairs from
            ``<back>``.
        roster_in_body: How many ``<def-list>`` elements sit inside ``<body>``.
            Recorded rather than used: a roster inside the body would make the
            arbiter part of the measured text, and this counts how often the
            design would have been compromised had ``<back>`` not been the
            source.
        empty_brackets_removed: Citation-sweep firing count, per half.
    """

    __slots__ = (
        "abstract",
        "body",
        "empty_brackets_removed",
        "licence_code",
        "licence_ref",
        "pmcid",
        "roster",
        "roster_in_body",
    )

    def __init__(
        self,
        pmcid: int,
        licence_code: str,
        licence_ref: str,
        abstract: str,
        body: str,
        roster: Sequence[Pair],
        roster_in_body: int,
        empty_brackets_removed: Dict[str, int],
    ) -> None:
        self.pmcid = pmcid
        self.licence_code = licence_code
        self.licence_ref = licence_ref
        self.abstract = abstract
        self.body = body
        self.roster = tuple(roster)
        self.roster_in_body = roster_in_body
        self.empty_brackets_removed = dict(empty_brackets_removed)

    @property
    def uid(self) -> str:
        """The passage identifier, shared by every half of this article."""
        return f"PMC{self.pmcid}"

    def half(self, name: str, rng: random.Random) -> str:
        """The text of one half.

        Args:
            name: ``abstract``, ``body`` or ``body_matched``.
            rng: Source of the ``body_matched`` window offset.

        Returns:
            The half's text. ``body_matched`` is a contiguous body window of the
            same length as this article's abstract, at a uniform offset; when the
            body is no longer than the abstract it is the whole body.

        Raises:
            ValueError: For an unknown half.
        """
        if name == "abstract":
            return self.abstract
        if name == "body":
            return self.body
        if name != "body_matched":
            raise ValueError(f"unknown half {name!r}")
        width = len(self.abstract)
        if width >= len(self.body):
            return self.body
        start = rng.randrange(0, len(self.body) - width + 1)
        return self.body[start : start + width]


def parse_article(pmcid: int, payload: bytes, licence_code: str) -> Optional[Article]:
    """Read one JATS file into an :class:`Article`.

    Only the article element's **direct** ``front``, ``body`` and ``back``
    children are read, so a ``<sub-article>`` -- a peer review report, an author
    response -- contributes nothing to either half.

    Args:
        pmcid: Numeric identifier.
        payload: The fetched XML bytes.
        licence_code: The metadata JSON's ``license_code``.

    Returns:
        The article, or ``None`` when the XML does not parse or one of the two
        halves is empty. An article with no body is not a same-article contrast.
    """
    try:
        root = ET.fromstring(payload)
    except ET.ParseError:
        return None
    front = root.find("front")
    body_element = root.find("body")
    back = root.find("back")

    abstract_parts: List[str] = []
    abstract_removed = 0
    if front is not None:
        for abstract in front.iter():
            if _local(abstract.tag) != "abstract":
                continue
            text, removed = render(abstract)
            abstract_removed += removed
            if text:
                abstract_parts.append(text)
    abstract_text = "\n\n".join(abstract_parts)
    body_text, body_removed = render(body_element)
    if body_element is None or not abstract_text or not body_text:
        return None

    licence_ref = ""
    for element in root.iter():
        if _local(element.tag) == "license_ref" and element.text:
            licence_ref = element.text.strip()
            break

    roster: List[Pair] = []
    if back is not None:
        for def_list in back.iter():
            if _local(def_list.tag) != "def-list":
                continue
            for item in def_list.iter():
                if _local(item.tag) != "def-item":
                    continue
                term_element = next((c for c in item if _local(c.tag) == "term"), None)
                def_element = next((c for c in item if _local(c.tag) == "def"), None)
                if term_element is None or def_element is None:
                    continue
                term = " ".join("".join(term_element.itertext()).split())
                definition = " ".join("".join(def_element.itertext()).split())
                if roster_pair_admissible(term, definition):
                    roster.append((term, definition))
    seen: set = set()
    unique_roster: List[Pair] = []
    for short, long_form in roster:
        key = (normalise(short), normalise(long_form))
        if key in seen:
            continue
        seen.add(key)
        unique_roster.append((short, long_form))

    roster_in_body = sum(1 for e in body_element.iter() if _local(e.tag) == "def-list")
    return Article(
        pmcid=pmcid,
        licence_code=licence_code,
        licence_ref=licence_ref,
        abstract=abstract_text,
        body=body_text,
        roster=unique_roster,
        roster_in_body=roster_in_body,
        empty_brackets_removed={"abstract": abstract_removed, "body": body_removed},
    )


def load_articles(pmcids: Sequence[int]) -> Tuple[List[Article], Dict[str, int]]:
    """Read every pinned article from ``data/pmc_oa_genre``.

    Args:
        pmcids: The pinned draw.

    Returns:
        ``(articles, attrition)``. ``articles`` are those that parsed and carry
        both halves, in draw order. ``attrition`` counts what the draw lost and
        why, because a sample reported without its attrition is a denominator
        somebody chose silently.

    Raises:
        SystemExit: When a pinned article has not been fetched, or nothing has.
    """
    articles: List[Article] = []
    attrition = {"drawn": len(pmcids), "unparseable": 0, "no_abstract_or_no_body": 0}
    absent = 0
    for pmcid in pmcids:
        path = DATA_DIR / f"PMC{pmcid}.1.xml"
        if not path.is_file():
            absent += 1
            continue
        payload = path.read_bytes()
        try:
            ET.fromstring(payload)
        except ET.ParseError:
            attrition["unparseable"] += 1
            continue
        article = parse_article(pmcid, payload, "")
        if article is None:
            attrition["no_abstract_or_no_body"] += 1
            continue
        articles.append(article)
    if absent:
        raise SystemExit(f"{absent} pinned article(s) are not in {DATA_DIR}; run --fetch first")
    if not articles:
        raise SystemExit(f"no articles under {DATA_DIR}; run --fetch first")
    attrition["kept"] = len(articles)
    return articles, attrition


# ---------------------------------------------------------------------------
# 4. Passages, and the located gold
# ---------------------------------------------------------------------------
HALVES = ("abstract", "body", "body_matched")

_WHITESPACE = re.compile(r"\s+")


def _occurrences(text: str, needle: str, *, fold: bool) -> List[CharSpan]:
    """Every place ``needle`` appears, verbatim first then whitespace-flexibly.

    A transcription of ``bench/run_monoculture.py``'s function of the same name,
    with one parameter added. ``tests/test_genre.py`` asserts the two agree
    wherever case already agrees, because a transcription that drifts is worse
    than an import.

    Args:
        text: The haystack.
        needle: The string to find.
        fold: Case-fold both sides.

    Returns:
        Character spans over ``text``, leftmost first.
    """
    if not needle:
        return []
    haystack = text.casefold() if fold else text
    target = needle.casefold() if fold else needle
    found: List[CharSpan] = []
    start = haystack.find(target)
    while start != -1:
        found.append((start, start + len(target)))
        start = haystack.find(target, start + 1)
    if found:
        return found
    parts = [part for part in _WHITESPACE.split(needle.strip()) if part]
    if not parts:
        return []
    pattern = r"\s*".join(re.escape(part) for part in parts)
    flags = re.IGNORECASE if fold else 0
    return [(m.start(), m.end()) for m in re.finditer(pattern, text, flags)]


def locate_pair_folded(
    text: str, short: str, long_form: str
) -> Optional[Tuple[CharSpan, CharSpan]]:
    """Locate a roster pair, folding the **long form's** case and not the short form's.

    This is the one place this runner departs from
    ``bench/run_monoculture.py``'s ``locate_pair``, and the departure is forced
    rather than stylistic. MED1250's gold pairs are lifted verbatim out of the
    text they annotate, so a case-sensitive search finds them. **An author's
    roster is not lifted from anything** -- it is typed into a glossary in
    sentence case, ``Magnetic resonance imaging``, while the same phrase appears
    mid-sentence in the article as ``magnetic resonance imaging``. Case-sensitive
    location therefore drops real definitions, and it drops them **unevenly
    between the two halves**, which would be a genre-correlated artefact inside
    the very contrast this runner exists to measure.

    Measured on the whole pinned draw, and both halves of the count are in
    ``bench/results.json`` as ``gold_pairs_located_without_the_case_fold`` and
    ``gold_pairs_located``: the abstract half locates ``141`` pairs
    case-sensitively and ``388`` folded, the body half ``998`` and ``1,892``. A
    ``2.75x`` recovery on one side and a ``1.90x`` recovery on the other is not
    a rounding difference, and the asymmetry between those two multipliers is
    exactly the genre-correlated artefact the fold removes.

    The **short** form is deliberately left case-sensitive. Measured on the
    first 600 articles of the draw, folding it as well recovered only
    ``157 -> 173`` and ``709 -> 715``, and it would let ``CT`` match inside
    ``fact``: ``_occurrences`` is a substring search with no word boundary,
    which is ``run_monoculture``'s convention and is kept so that the short-form
    half of a located pair means the same thing in both runners.

    Args:
        text: One half of one article.
        short: The roster term.
        long_form: The roster definition.

    Returns:
        ``(short span, long span)`` for the co-occurrence that best explains the
        two as one definition -- the pair with the smallest gap, ties leftmost --
        or ``None`` when either string is absent.
    """
    shorts = _occurrences(text, short, fold=False)
    longs = _occurrences(text, long_form, fold=True)
    if not shorts or not longs:
        return None
    ranked = [
        (max(0, max(s[0], lf[0]) - min(s[1], lf[1])), s[0], lf[0], s, lf)
        for s in shorts
        for lf in longs
    ]
    _, _, _, best_short, best_long = min(ranked)
    return best_short, best_long


def passages_for(articles: Sequence[Article], half: str) -> List[Passage]:
    """Build one :class:`Passage` per article for one half.

    Gold spans are the author-declared roster pairs **located in this half**: a
    pair is located when both of its strings occur, by
    :func:`locate_pair_folded` -- ``bench/run_monoculture.py``'s convention for
    MED1250 with the long form's case folded, and that function documents why
    the fold is forced rather than convenient. A pair the author declared but
    never wrote out in this half is not gold about this half, so it is counted
    in ``roster_pairs_declared`` and excluded from every reach denominator.

    Args:
        articles: The sample.
        half: One of :data:`HALVES`.

    Returns:
        One passage per article, with ``gold_short``, ``gold_long`` and
        ``gold_pairs`` populated from the located roster.
    """
    rng = random.Random(WINDOW_SEED)
    passages: List[Passage] = []
    for article in articles:
        text = article.half(half, rng)
        shorts: List[CharSpan] = []
        longs: List[CharSpan] = []
        pairs: List[Pair] = []
        for short, long_form in article.roster:
            found = locate_pair_folded(text, short, long_form)
            if found is None:
                continue
            shorts.append(found[0])
            longs.append(found[1])
            pairs.append((short, long_form))
        passages.append(Passage(article.uid, text, shorts, longs, pairs))
    return passages


def corpus_record(
    articles: Sequence[Article], passages: Sequence[Passage], half: str, context: dict
) -> dict:
    """What one half is, before any proposer touches it.

    The load-bearing column is ``gold_pairs_long_form_bracket_adjacent_pct``: it
    is the same quantity ``monoculture.*.corpus`` reports, so this half's figure
    sits in the same units as MED1250's ``98.91`` and PLOD's ``61.36``.

    Two fields are article-level rather than half-level and are named here
    rather than left to be misread. ``def_lists_inside_body`` is a property of
    the article whichever half is being described. ``empty_bracket_pairs_removed``
    counts the sweeps that happened while rendering this half's **source** text,
    so for ``body_matched`` it is the whole body's count and not the window's --
    the window is cut from text the sweep has already passed over. Neither is
    quoted anywhere; both are here so a reader can see the cleaner's activity.

    Args:
        articles: The sample.
        passages: This half's passages.
        half: One of :data:`HALVES`.
        context: Fields copied into the record.

    Returns:
        The record.
    """
    characters = sum(len(passage.text) for passage in passages)
    declared = sum(len(article.roster) for article in articles)
    located = sum(len(passage.gold_pairs) for passage in passages)
    short_bracketed = 0
    long_bracketed = 0
    open_brackets = 0
    for passage in passages:
        open_brackets += sum(passage.text.count(bracket) for bracket in "([{")
        for short_span, long_span in zip(passage.gold_short, passage.gold_long):
            short_bracketed += bracket_adjacent(passage.text, short_span)
            long_bracketed += bracket_adjacent(passage.text, long_span)
    record: dict = dict(context)
    record["half"] = half
    record["articles"] = len(articles)
    record["articles_with_a_roster"] = sum(1 for article in articles if article.roster)
    record["characters"] = characters
    record["mean_characters_per_article"] = round(characters / max(len(articles), 1), 1)
    record["roster_pairs_declared"] = declared
    record["gold_pairs_located"] = located
    # The fold's firing count, in the record rather than in a docstring: a
    # locator that silently recovers most of a denominator has to say how much.
    case_sensitive = 0
    for article, passage in zip(articles, passages):
        for short, long_form in article.roster:
            if locate_pair(passage.text, short, long_form) is not None:
                case_sensitive += 1
    record["gold_pairs_located_without_the_case_fold"] = case_sensitive
    record["gold_pairs_recovered_by_the_case_fold"] = located - case_sensitive
    record["gold_pairs_located_pct_of_declared"] = round(100 * located / max(declared, 1), 2)
    record["gold_pairs_short_form_bracket_adjacent"] = short_bracketed
    record["gold_pairs_short_form_bracket_adjacent_pct"] = round(
        100 * short_bracketed / max(located, 1), 2
    )
    record["gold_pairs_long_form_bracket_adjacent"] = long_bracketed
    record["gold_pairs_long_form_bracket_adjacent_pct"] = round(
        100 * long_bracketed / max(located, 1), 2
    )
    record["open_brackets"] = open_brackets
    record["open_brackets_per_100k_characters"] = round(
        100_000 * open_brackets / max(characters, 1), 1
    )
    record["empty_bracket_pairs_removed"] = sum(
        article.empty_brackets_removed.get("body" if half.startswith("body") else half, 0)
        for article in articles
    )
    record["def_lists_inside_body"] = sum(article.roster_in_body for article in articles)
    return record


# ---------------------------------------------------------------------------
# 5. The cluster bootstrap
# ---------------------------------------------------------------------------
def _ratio(rows: Sequence[Tuple[float, float]], indices: Sequence[int]) -> float:
    """A pooled percentage over the selected rows, or ``nan`` on an empty denominator."""
    numerator = 0.0
    denominator = 0.0
    for index in indices:
        numerator += rows[index][0]
        denominator += rows[index][1]
    if denominator <= 0:
        return float("nan")
    return 100 * numerator / denominator


def cluster_bootstrap(
    left: Sequence[Tuple[float, float]],
    right: Sequence[Tuple[float, float]],
    *,
    replicates: int = BOOTSTRAP_REPLICATES,
    seed: int = BOOTSTRAP_SEED,
) -> dict:
    """A paired cluster bootstrap on the difference between two pooled ratios.

    The cluster is the **article**, and the same resampled articles are used for
    both halves in every replicate. That is what makes this a paired interval:
    an article that contributes many correlated observations to the body half
    contributes its correlated abstract-half observations in the same replicate
    or in none.

    Args:
        left: Per-article ``(numerator, denominator)`` for the first half.
        right: The same for the second, in the same article order.
        replicates: Bootstrap replicates.
        seed: Bootstrap seed.

    Returns:
        A record with the two point estimates, the difference, a percentile
        interval on the difference, and the counts a reader needs to know
        whether the interval means anything: how many articles carry a non-zero
        denominator in each half.

    Raises:
        ValueError: If the two sequences are not the same length.
    """
    if len(left) != len(right):
        raise ValueError("paired bootstrap needs one row per article in both halves")
    count = len(left)
    everything = list(range(count))
    point_left = _ratio(left, everything)
    point_right = _ratio(right, everything)
    rng = random.Random(seed)
    differences: List[float] = []
    for _ in range(replicates):
        indices = [rng.randrange(count) for _ in range(count)] if count else []
        a = _ratio(left, indices)
        b = _ratio(right, indices)
        # `x == x` is false for NaN, which is how a replicate with an empty
        # denominator in either half is dropped rather than propagated.
        if a == a and b == b:
            differences.append(a - b)
    differences.sort()
    record: dict = {
        "articles": count,
        "articles_with_evidence_left": sum(1 for _, den in left if den > 0),
        "articles_with_evidence_right": sum(1 for _, den in right if den > 0),
        "denominator_left": sum(den for _, den in left),
        "denominator_right": sum(den for _, den in right),
        "left_pct": round(point_left, 2) if point_left == point_left else None,
        "right_pct": round(point_right, 2) if point_right == point_right else None,
        "difference_pct": (
            round(point_left - point_right, 2)
            if point_left == point_left and point_right == point_right
            else None
        ),
        "replicates_used": len(differences),
        "replicates_requested": replicates,
        "seed": seed,
    }
    if differences:
        low = differences[int(0.025 * (len(differences) - 1))]
        high = differences[int(0.975 * (len(differences) - 1))]
        record["difference_ci_low_pct"] = round(low, 2)
        record["difference_ci_high_pct"] = round(high, 2)
        record["difference_ci_width_pct"] = round(high - low, 2)
        record["ci_excludes_zero"] = bool(low > 0 or high < 0)
    return record


def per_article_bracket_rows(passages: Sequence[Passage]) -> List[Tuple[float, float]]:
    """``(bracket-adjacent located long forms, located long forms)`` per article."""
    rows: List[Tuple[float, float]] = []
    for passage in passages:
        adjacent = sum(1 for span in passage.gold_long if bracket_adjacent(passage.text, span))
        rows.append((float(adjacent), float(len(passage.gold_long))))
    return rows


def per_article_reach_rows(
    passages: Sequence[Passage], proposals: Dict[str, Proposals], label: str
) -> List[Tuple[float, float]]:
    """``(gold spans the S&H family reached, gold spans)`` per article."""
    reach = gold_reach(passages, proposals, label, "overlap")
    family: set = set()
    for name in sh_family(sorted(proposals)):
        family |= reach[name]
    rows: List[Tuple[float, float]] = []
    for passage in passages:
        gold = passage.gold_short if label == "short_form" else passage.gold_long
        hit = sum(1 for index in range(len(gold)) if (passage.uid, index) in family)
        rows.append((float(hit), float(len(gold))))
    return rows


def per_article_independent_gain_rows(
    passages: Sequence[Passage], proposals: Dict[str, Proposals]
) -> List[Tuple[float, float]]:
    """``(edges only an independent proposer offers, union edges)`` per article.

    Every edge key carries its passage identifier, so the per-article unions are
    disjoint and the pooled independent gain really is a ratio of sums over
    articles. That is the fact that makes a cluster bootstrap legitimate here
    rather than an approximation.
    """
    names = sorted(proposals)
    family = set(sh_family(names))
    by_article: Dict[str, Dict[str, set]] = {}
    for name in names:
        for key in edge_keys(proposals[name]):
            by_article.setdefault(key[0], {}).setdefault(name, set()).add(key)
    rows: List[Tuple[float, float]] = []
    for passage in passages:
        buckets = by_article.get(passage.uid, {})
        union: set = set()
        family_union: set = set()
        for name, keys in buckets.items():
            union |= keys
            if name in family:
                family_union |= keys
        rows.append((float(len(union - family_union)), float(len(union))))
    return rows


# ---------------------------------------------------------------------------
# 6. Running the pool over one half
# ---------------------------------------------------------------------------
def run_pool(
    passages: Sequence[Passage], externals: Sequence[str], interpreter: Optional[str]
) -> Dict[str, Proposals]:
    """Every proposer of ``bench/run_monoculture.py``, over one half.

    No proposer is added here and none is re-implemented: the S&H family is
    exactly the one that runner already drives, which is the whole point -- a
    new descendant would change the pool the contrast is measured against.

    Args:
        passages: One half.
        externals: External S&H systems to include.
        interpreter: The interpreter that has them.

    Returns:
        ``{proposer name: Proposals}``.
    """
    proposals: Dict[str, Proposals] = {}
    for profile in PROFILES:
        proposals[f"acronymkit/{profile}"] = run_acronymkit(passages, profile)
    for system in externals:
        if interpreter is None:
            continue
        proposals[system] = run_external(passages, system, interpreter)
    proposals["allcaps"] = run_allcaps(passages)
    proposals["shapecue"] = run_shapecue(passages)
    return proposals


def half_records(
    articles: Sequence[Article],
    half: str,
    passages: Sequence[Passage],
    proposals: Dict[str, Proposals],
    context: dict,
) -> Dict[str, dict]:
    """Every record for one half, keyed by run id."""
    prefix = f"genre.pmc_oa.{half}"
    records: Dict[str, dict] = {}
    records[f"{prefix}.corpus"] = corpus_record(articles, passages, half, context)
    records[f"{prefix}.independence"] = alignment_record(proposals, passages, context)
    edges = {name: edge_keys(proposal) for name, proposal in proposals.items()}
    records[f"{prefix}.proposals.edges"] = overlap_record(
        edges, "distinct (article, short form, long form)", context
    )
    records[f"{prefix}.proposals.edges_sh_only"] = overlap_record(
        {name: edges[name] for name in sh_family(sorted(edges))},
        "distinct (article, short form, long form), S&H descendants only",
        context,
    )
    records[f"{prefix}.proposals.vertices"] = overlap_record(
        {name: vertex_keys(proposal, passages) for name, proposal in proposals.items()},
        "distinct (article, short form)",
        context,
    )
    characters = max(sum(len(passage.text) for passage in passages), 1)
    for name, proposal in sorted(proposals.items()):
        slug = name.replace("/", "_")
        scores: Dict[str, float] = {}
        for label in ("short_form", "long_form"):
            if any((p.gold_short if label == "short_form" else p.gold_long) for p in passages):
                scores.update(score_spans(passages, proposal, label, "overlap"))
        records[f"{prefix}.proposer.{slug}"] = {
            **context,
            "half": half,
            "system": name,
            "short_form_spans": sum(len(v) for v in proposal.short_spans.values()),
            "long_form_spans": sum(len(v) for v in proposal.long_spans.values()),
            "edges_per_100k_characters": round(
                100_000 * sum(len(v) for v in proposal.edges.values()) / characters, 2
            ),
            **scores,
            **proposal.notes,
        }
    for label in ("short_form", "long_form"):
        if not any((p.gold_short if label == "short_form" else p.gold_long) for p in passages):
            continue
        records[f"{prefix}.gold.{label}.overlap.class"] = gold_class_record(
            passages, proposals, label, "overlap", context
        )
    return records


# ---------------------------------------------------------------------------
# 7. The contrast, and the verdict
# ---------------------------------------------------------------------------
def contrast_record(
    passages: Dict[str, List[Passage]],
    proposals: Dict[str, Dict[str, Proposals]],
    context: dict,
) -> dict:
    """The paired abstract-versus-body differences, with cluster-bootstrap intervals.

    Three quantities, each chosen because ``monoculture.*`` already reports it
    across corpora, so the same-article difference lands in the same units as
    the cross-corpus ordering it is testing:

    * ``bracket_adjacency`` -- the share of located gold long forms sitting
      beside a bracket. MED1250 ``98.91``, PLOD ``61.36``.
    * ``sh_family_recall`` -- the share of located gold long forms the S&H
      family reaches.
    * ``independent_gain`` -- the share of proposal edges only a non-S&H
      proposer offers. MED1250 ``0.23``, PLOD ``32.04``.

    Args:
        passages: ``{half: passages}``.
        proposals: ``{half: {proposer: Proposals}}``.
        context: Fields copied into the record.

    Returns:
        The record, including a ``verdict`` field that names which way the
        evidence went.
    """
    record: dict = dict(context)
    record["comparisons"] = []
    for right in ("body", "body_matched"):
        if right not in passages:
            continue
        for label, left_rows, right_rows in (
            (
                "bracket_adjacency_of_located_gold_long_forms",
                per_article_bracket_rows(passages["abstract"]),
                per_article_bracket_rows(passages[right]),
            ),
            (
                "sh_family_recall_of_located_gold_long_forms",
                per_article_reach_rows(passages["abstract"], proposals["abstract"], "long_form"),
                per_article_reach_rows(passages[right], proposals[right], "long_form"),
            ),
            (
                "independent_gain_on_proposal_edges",
                per_article_independent_gain_rows(passages["abstract"], proposals["abstract"]),
                per_article_independent_gain_rows(passages[right], proposals[right]),
            ),
        ):
            key = f"abstract_minus_{right}.{label}"
            record[key] = cluster_bootstrap(left_rows, right_rows)
            record["comparisons"].append(key)
    return record


def verdict(record: dict) -> str:
    """Read the contrast record and say which way it went, in one sentence.

    Args:
        record: The output of :func:`contrast_record`.

    Returns:
        ``genre`` when both headline differences favour the genre account with
        intervals excluding zero, ``provenance-back-in-play`` when neither does,
        and ``split`` otherwise. The wording is deliberately blunt: a verdict
        that could be read either way is not a verdict.
    """
    bracket = record.get("abstract_minus_body.bracket_adjacency_of_located_gold_long_forms", {})
    gain = record.get("abstract_minus_body.independent_gain_on_proposal_edges", {})
    genre_on_brackets = (
        bool(bracket.get("ci_excludes_zero")) and (bracket.get("difference_pct") or 0) > 0
    )
    genre_on_gain = bool(gain.get("ci_excludes_zero")) and (gain.get("difference_pct") or 0) < 0
    if genre_on_brackets and genre_on_gain:
        return "genre"
    if not genre_on_brackets and not genre_on_gain:
        return "provenance-back-in-play"
    return "split"


# ---------------------------------------------------------------------------
# 8. Entry point
# ---------------------------------------------------------------------------
def sample_record(articles: Sequence[Article], attrition: Dict[str, int], context: dict) -> dict:
    """What the draw is, including the licences it refused and the articles it lost."""
    record: dict = dict(context)
    for key, value in attrition.items():
        record[f"attrition_{key}"] = value
    record["frame"] = (
        f"uniform over PMC identifier integers in [{DRAW_ID_LOW}, {DRAW_ID_HIGH}), "
        f"version 1 only, seed {DRAW_SEED}"
    )
    record["cloud_bucket"] = CLOUD_BUCKET
    record["terms_url"] = PMC_OA_TERMS_URL
    record["terms_read_on"] = PMC_OA_TERMS_READ_ON
    record["copyright_url"] = PMC_COPYRIGHT_URL
    record["permissive_licence_codes"] = list(PERMISSIVE_LICENCE_CODES)
    record["draw_census_taken_on"] = DRAW_CENSUS_TAKEN_ON
    record["draw_probes"] = DRAW_PROBES
    for label, count in DRAW_CENSUS.items():
        record[f"draw_census.{label}"] = count
    licensed = sum(count for label, count in DRAW_CENSUS.items() if not label.startswith("("))
    permissive = sum(DRAW_CENSUS.get(code, 0) for code in PERMISSIVE_LICENCE_CODES)
    record["draw_articles_carrying_a_licence_code"] = licensed
    record["draw_articles_permissively_licensed"] = permissive
    record["draw_permissive_pct_of_licensed"] = round(100 * permissive / max(licensed, 1), 2)
    record["draw_non_permissive_pct_of_licensed"] = round(
        100 * (licensed - permissive) / max(licensed, 1), 2
    )
    existing = DRAW_PROBES - DRAW_CENSUS.get("(no such article version)", 0)
    record["draw_article_versions_that_exist"] = existing
    record["draw_permissive_pct_of_existing"] = round(100 * permissive / max(existing, 1), 2)
    record["ftp_retirement"] = FTP_RETIREMENT_NOTE
    record["articles"] = len(articles)
    record["articles_with_a_roster"] = sum(1 for article in articles if article.roster)
    record["roster_pairs_declared"] = sum(len(article.roster) for article in articles)
    refs: Dict[str, int] = {}
    for article in articles:
        refs[article.licence_ref or "(no ali:license_ref in the article)"] = (
            refs.get(article.licence_ref or "(no ali:license_ref in the article)", 0) + 1
        )
    record["per_article_licence_ref_urls"] = dict(sorted(refs.items(), key=lambda kv: -kv[1]))
    return record


def main(argv: Optional[Sequence[str]] = None) -> int:
    """Command-line entry point."""
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--draw", type=int, help="draw this many admissible articles and print them"
    )
    parser.add_argument("--fetch", action="store_true", help="fetch the pinned draw into data/")
    parser.add_argument("--record", action="store_true", help="print the manifest digest to pin")
    parser.add_argument("--verify", action="store_true", help="re-digest the fetched articles")
    parser.add_argument("--save", action="store_true", help="record into bench/results.json")
    parser.add_argument("--interpreter", help="a Python that has the external baselines")
    parser.add_argument(
        "--system",
        action="append",
        choices=sorted(EXTERNAL_SH_SYSTEMS),
        help="external S&H descendant to include; repeatable, needs --interpreter",
    )
    parser.add_argument(
        "--half",
        action="append",
        choices=list(HALVES),
        help="restrict to these halves; default is all three",
    )
    args = parser.parse_args(argv)

    if args.draw:
        accepted, census, probes = draw(args.draw)
        print(f"probed {probes}, accepted {len(accepted)}")
        for verdict_name, count in sorted(census.items(), key=lambda kv: -kv[1]):
            print(f"  {count:>6}  {round(100 * count / max(probes, 1), 2):>6.2f} %  {verdict_name}")
        print()
        print(" ".join(str(pmcid) for pmcid in accepted))
        return 0

    if args.fetch:
        ids = pinned_pmcids()
        if not ids:
            raise SystemExit(
                "no draw is pinned; run --draw first and paste into PINNED_PMCIDS_TEXT"
            )
        digests = fetch_articles(ids)
        computed = write_manifest(digests)
        print(f"fetched {len(digests)} article(s) into {DATA_DIR}")
        if args.record or not PINNED_MANIFEST_SHA256:
            print(f"PINNED_MANIFEST_SHA256 = {computed!r}")
        elif computed != PINNED_MANIFEST_SHA256:
            raise SystemExit(f"manifest digest {computed} differs from the pin")
        return 0

    if args.verify:
        return verify()

    externals = list(args.system or (EXTERNAL_SH_SYSTEMS if args.interpreter else ()))
    if externals and not args.interpreter:
        raise SystemExit("--system needs --interpreter")

    articles, attrition = load_articles(pinned_pmcids())
    context = {
        "corpus": "pmc_oa_same_article_genre",
        "provenance": "held constant: both halves are taken from one JATS file",
        "gold_provenance": "each article's own <def-list> abbreviation roster, from <back>",
        "pooled_gold": False,
        "role": "single_annotator_reference",
    }
    halves = list(args.half or HALVES)
    all_passages: Dict[str, List[Passage]] = {}
    all_proposals: Dict[str, Dict[str, Proposals]] = {}
    recorded: Dict[str, dict] = {"genre.pmc_oa.sample": sample_record(articles, attrition, context)}

    for half in halves:
        passages = passages_for(articles, half)
        proposals = run_pool(passages, externals, args.interpreter)
        all_passages[half] = passages
        all_proposals[half] = proposals
        recorded.update(half_records(articles, half, passages, proposals, context))
        described = recorded[f"genre.pmc_oa.{half}.corpus"]
        print(f"=== {half} ===")
        print(
            f"  {described['articles']:,} articles, {described['characters']:,} characters, "
            f"{described['gold_pairs_located']:,} of {described['roster_pairs_declared']:,} "
            f"declared roster pairs located"
        )
        print(
            f"  located gold long forms beside a bracket: "
            f"{described['gold_pairs_long_form_bracket_adjacent_pct']:.2f} %"
        )
        edge_record = recorded[f"genre.pmc_oa.{half}.proposals.edges"]
        print(
            f"  proposal edges {edge_record['union_total']:,}, "
            f"S&H family share {edge_record.get('sh_family_share_pct', float('nan')):.2f} %, "
            f"independent gain {edge_record.get('independent_gain_pct', float('nan')):.2f} %"
        )
        klass = recorded.get(f"genre.pmc_oa.{half}.gold.long_form.overlap.class")
        if klass:
            print(
                f"  S&H family reaches {klass['sh_family_recall_pct']:.2f} % of located gold "
                f"long forms; unreached yet alignable "
                f"{klass['unproposed_alignable_from_gold_short_form_pct_of_gold']:.2f} %"
            )
        print()

    if "abstract" in all_passages and len(all_passages) > 1:
        contrast = contrast_record(all_passages, all_proposals, context)
        contrast["verdict"] = verdict(contrast)
        recorded["genre.pmc_oa.contrast"] = contrast
        print("=== abstract minus body, cluster bootstrap over articles ===")
        for key in contrast["comparisons"]:
            cell = contrast[key]
            print(
                f"  {key:<64} {cell['left_pct']} - {cell['right_pct']} = "
                f"{cell['difference_pct']}  "
                f"[{cell.get('difference_ci_low_pct')}, {cell.get('difference_ci_high_pct')}]"
            )
        print(f"  verdict: {contrast['verdict']}")
        print()

    if args.save:
        path = save_results(recorded)
        print(f"saved {len(recorded)} run(s) to {path.relative_to(REPO_ROOT)}")
    print(environment())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
