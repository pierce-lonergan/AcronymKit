"""Compatibility path. The arithmetic now lives in :mod:`acronymkit.core.conformal`.

``acronymkit.conformal`` shipped as a public module and is cited by run id in
``docs/EVALUATION.md`` and by name in ``CHANGELOG.md``, so the path stays. The
definitions moved to :mod:`acronymkit.core.conformal` when the package was split
at the lexer contract seam: conformal risk arithmetic makes no lexical
commitment of any kind -- it sorts scores and takes an order statistic -- so it
belongs in the leaf both halves may depend on rather than beside the
disambiguator that happens to produce the results it scores.

**These are the same objects, not copies**: ``acronymkit.conformal.ConformalGate
is acronymkit.core.conformal.ConformalGate``. The reason that matters here is
sharper than for the exception hierarchy -- a caller holding a
:class:`~acronymkit.core.conformal.ConformalGate` calibrated through one path
and asking a question through the other must be talking about the same class,
or the guarantee they were given is about a different object than the one
deciding.

The private helpers ``_true_label_score``, ``_marginal_group`` and
``_validated_alpha`` are deliberately **not** re-exported: they were never
public and a shim is not the place to widen a surface.

**How long this path is kept:** through the whole of the ``0.x`` line; removal
requires a major version and a deprecation cycle announced one minor release
ahead. See ``CHANGELOG.md``.
"""

from __future__ import annotations

from .core.conformal import (
    ASSUMPTION,
    ConformalDecision,
    ConformalGate,
    GroupCalibration,
    arity_group,
    group_counts,
    nonconformity,
    smallest_calibration_size,
)

__all__ = [
    "ASSUMPTION",
    "ConformalDecision",
    "ConformalGate",
    "GroupCalibration",
    "arity_group",
    "group_counts",
    "nonconformity",
    "smallest_calibration_size",
]
