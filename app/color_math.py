"""
Vectorized colour-space helpers used by the analyzer.

Everything here works on numpy arrays of shape (N, 3) with sRGB values
already normalised to the 0..1 range (float64). No external colour
libraries are required -- just numpy -- so the tool has no heavy
dependencies to install.
"""
from __future__ import annotations

import numpy as np

# ---------------------------------------------------------------------------
# sRGB <-> linear <-> XYZ <-> CIE L*a*b*
# ---------------------------------------------------------------------------

_SRGB_TO_XYZ = np.array([
    [0.4124564, 0.3575761, 0.1804375],
    [0.2126729, 0.7151522, 0.0721750],
    [0.0193339, 0.1191920, 0.9503041],
])

# D65 reference white
_XN, _YN, _ZN = 0.95047, 1.0, 1.08883


def srgb_to_linear(c: np.ndarray) -> np.ndarray:
    a = 0.055
    return np.where(c <= 0.04045, c / 12.92, ((c + a) / (1 + a)) ** 2.4)


def rgb_to_lab(rgb: np.ndarray) -> np.ndarray:
    """rgb: (N,3) sRGB in 0..1. Returns (N,3) Lab, L in 0..100, a/b roughly -128..127."""
    lin = srgb_to_linear(rgb)
    xyz = lin @ _SRGB_TO_XYZ.T
    x = xyz[:, 0] / _XN
    y = xyz[:, 1] / _YN
    z = xyz[:, 2] / _ZN

    delta = 6 / 29

    def f(t):
        return np.where(t > delta ** 3, np.cbrt(t), t / (3 * delta ** 2) + 4 / 29)

    fx, fy, fz = f(x), f(y), f(z)
    L = 116 * fy - 16
    a = 500 * (fx - fy)
    b = 200 * (fy - fz)
    return np.stack([L, a, b], axis=1)


# ---------------------------------------------------------------------------
# RGB <-> HSL
# ---------------------------------------------------------------------------

def rgb_to_hsl(rgb: np.ndarray) -> np.ndarray:
    """rgb: (N,3) in 0..1. Returns (N,3): H in 0..360, S in 0..1, L in 0..1."""
    r, g, b = rgb[:, 0], rgb[:, 1], rgb[:, 2]
    maxc = np.max(rgb, axis=1)
    minc = np.min(rgb, axis=1)
    L = (maxc + minc) / 2.0
    diff = maxc - minc

    S = np.zeros_like(L)
    nonzero = diff > 1e-8
    denom = np.where(L[nonzero] < 0.5, (maxc + minc)[nonzero], (2 - maxc - minc)[nonzero])
    S[nonzero] = diff[nonzero] / np.maximum(denom, 1e-8)

    H = np.zeros_like(L)
    d = np.where(diff < 1e-8, 1.0, diff)  # avoid div by zero, masked out below

    is_r = (maxc == r) & nonzero
    is_g = (maxc == g) & nonzero & ~is_r
    is_b = (maxc == b) & nonzero & ~is_r & ~is_g

    H[is_r] = (((g[is_r] - b[is_r]) / d[is_r]) % 6) * 60
    H[is_g] = (((b[is_g] - r[is_g]) / d[is_g]) + 2) * 60
    H[is_b] = (((r[is_b] - g[is_b]) / d[is_b]) + 4) * 60
    H = H % 360

    return np.stack([H, S, L], axis=1)


def circular_diff(h: np.ndarray | float, center: float) -> np.ndarray:
    """Shortest signed distance from `h` to `center` on a 0..360 circle."""
    d = (np.asarray(h, dtype=np.float64) - center + 180) % 360 - 180
    return d


def triangular_weight(h: np.ndarray, center: float, width: float) -> np.ndarray:
    """Triangular membership weight in [0,1], 1 at `center`, 0 at +-width."""
    d = np.abs(circular_diff(h, center))
    w = 1.0 - d / width
    return np.clip(w, 0.0, 1.0)


def clip(value: float, lo: float, hi: float) -> float:
    return float(max(lo, min(hi, value)))
