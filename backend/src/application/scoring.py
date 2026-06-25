"""Maturity band thresholds and shared roll-up helpers."""

from __future__ import annotations

from domain.enums import MaturityBand


def band_from_numeric(n: float) -> MaturityBand:
    if n < 2.5:
        return MaturityBand.SIT
    if n < 5.0:
        return MaturityBand.CRAWL
    if n < 7.5:
        return MaturityBand.WALK
    return MaturityBand.RUN
