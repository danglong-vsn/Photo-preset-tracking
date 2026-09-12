"""
Core analysis: load a photo, measure its colour characteristics, and turn
those measurements into a dict of Lightroom / Camera Raw develop-setting
values that approximate the photo's "look".

IMPORTANT HONESTY NOTE (also explained in the README):
A single photo does not contain enough information to derive a pixel-exact
reverse colour transform -- that would require the original unedited file
plus the edited file to diff against. What this tool does instead is
measure the photo's own colour signature (white-balance cast, contrast,
tonal balance, per-hue saturation/luminance, shadow/highlight colour) and
encode that signature as a Lightroom preset (white balance, tone sliders,
HSL, colour grading). Applied to another photo, that preset pushes the
colours strongly toward the same look -- very close, but not a
mathematically exact match, because the two photos have different starting
content.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
from PIL import Image

from . import color_math as cm

HUE_BANDS = [
    ("Red", 0),
    ("Orange", 30),
    ("Yellow", 60),
    ("Green", 120),
    ("Aqua", 180),
    ("Blue", 240),
    ("Purple", 275),
    ("Magenta", 315),
]

# Empirically reasonable "typical photo" baselines used only as a reference
# point so we can describe a given photo as "more/less than usual" on each
# axis. These are heuristics, not physical constants.
REF_MEAN_L = 50.0
REF_STD_L = 18.0
REF_MEAN_SAT = 0.32
REF_LOCAL_CONTRAST = 3.0
REF_BAND_WEIGHT_MIN = 40  # minimum summed pixel weight before we trust a hue band


@dataclass
class LookSettings:
    source_path: str
    preset_name: str
    values: dict = field(default_factory=dict)


def _load_pixels(path: str, max_dim: int = 1200) -> np.ndarray:
    img = Image.open(path)
    img = img.convert("RGB")
    img.thumbnail((max_dim, max_dim), Image.LANCZOS)
    arr = np.asarray(img).astype(np.float64) / 255.0
    h, w, _ = arr.shape
    return arr.reshape(-1, 3), (w, h)


def analyze_image(path: str, preset_name: str | None = None) -> LookSettings:
    flat, (w, h) = _load_pixels(path)

    lab = cm.rgb_to_lab(flat)
    hsl = cm.rgb_to_hsl(flat)

    L, a, b = lab[:, 0], lab[:, 1], lab[:, 2]
    H, S, Lh = hsl[:, 0], hsl[:, 1], hsl[:, 2]

    mean_L = float(np.mean(L))
    std_L = float(np.std(L))
    p1, p50, p99 = (float(x) for x in np.percentile(L, [1, 50, 99]))
    mean_a = float(np.mean(a))
    mean_b = float(np.mean(b))
    mean_S = float(np.mean(S))
    mean_Lh = float(np.mean(Lh))

    # ---- exposure / tone ----
    exposure = cm.clip((mean_L - REF_MEAN_L) / REF_MEAN_L * 1.2, -2.5, 2.5)
    contrast = cm.clip((std_L - REF_STD_L) / REF_STD_L * 90, -100, 100)
    highlights = cm.clip((95.0 - p99) * 2.5, -100, 100)
    shadows = cm.clip((p1 - 5.0) * 2.5, -100, 100)
    whites = cm.clip((p99 - 99.0) * 6, -100, 100)
    blacks = cm.clip((0.5 - p1) * 6, -100, 100)

    # ---- white balance cast ----
    # b* > 0 => yellow cast => warmer look => higher Kelvin
    # a* > 0 => red/magenta cast => Lightroom Tint negative brings back green,
    # so a positive magenta cast is represented as a positive Tint value.
    temperature = cm.clip(5500 + mean_b * 140, 2000, 50000)
    tint = cm.clip(mean_a * 3.2, -150, 150)

    # ---- local contrast (clarity / texture proxy) ----
    Lg = L.reshape(h, w)
    gx = np.diff(Lg, axis=1)
    gy = np.diff(Lg, axis=0)
    local_contrast = float((np.mean(np.abs(gx)) + np.mean(np.abs(gy))) / 2)
    clarity = cm.clip((local_contrast - REF_LOCAL_CONTRAST) * 18, -100, 100)
    texture = cm.clip((local_contrast - REF_LOCAL_CONTRAST) * 10, -100, 100)

    # ---- vibrance ----
    vibrance = cm.clip((mean_S - REF_MEAN_SAT) / max(REF_MEAN_SAT, 0.05) * 90, -100, 100)

    # ---- per-hue HSL bands ----
    hsl_adjustments = {}
    for name, center in HUE_BANDS:
        weights = cm.triangular_weight(H, center, 45)
        total_w = float(np.sum(weights))
        if total_w < REF_BAND_WEIGHT_MIN:
            hsl_adjustments[name] = {"hue": 0.0, "sat": 0.0, "lum": 0.0}
            continue
        band_S = float(np.sum(S * weights) / total_w)
        band_L = float(np.sum(Lh * weights) / total_w)
        # circular weighted mean hue within the band
        rad = np.deg2rad(H)
        sin_mean = float(np.sum(np.sin(rad) * weights) / total_w)
        cos_mean = float(np.sum(np.cos(rad) * weights) / total_w)
        band_H = (np.degrees(np.arctan2(sin_mean, cos_mean))) % 360

        sat_adj = cm.clip((band_S - mean_S) / max(mean_S, 0.05) * 70, -100, 100)
        lum_adj = cm.clip((band_L - mean_Lh) / max(mean_Lh, 0.05) * 70, -100, 100)
        hue_adj = cm.clip(cm.circular_diff(band_H, center) * 1.4, -100, 100)
        hsl_adjustments[name] = {"hue": hue_adj, "sat": sat_adj, "lum": lum_adj}

    # ---- shadow / midtone / highlight colour (split toning / colour grading) ----
    p33, p66 = (float(x) for x in np.percentile(L, [33, 66]))
    shadow_mask = L <= p33
    mid_mask = (L > p33) & (L <= p66)
    high_mask = L > p66

    def region_hue_chroma(mask):
        if not np.any(mask):
            return 0.0, 0.0
        ra, rb = float(np.mean(a[mask])), float(np.mean(b[mask]))
        hue = float(np.degrees(np.arctan2(rb, ra)) % 360)
        chroma = float(np.hypot(ra, rb))
        return hue, chroma

    sh_hue, sh_chroma = region_hue_chroma(shadow_mask)
    mid_hue, mid_chroma = region_hue_chroma(mid_mask)
    hi_hue, hi_chroma = region_hue_chroma(high_mask)

    def chroma_to_sat(c):
        return cm.clip(c * 6.0, 0, 100)

    color_grade = {
        "shadow_hue": sh_hue, "shadow_sat": chroma_to_sat(sh_chroma),
        "midtone_hue": mid_hue, "midtone_sat": chroma_to_sat(mid_chroma),
        "highlight_hue": hi_hue, "highlight_sat": chroma_to_sat(hi_chroma),
    }

    # ---- vignette proxy: center vs corner luminance ----
    Lg2d = Lg
    ch, cw = h, w
    cy0, cy1 = int(ch * 0.35), int(ch * 0.65)
    cx0, cx1 = int(cw * 0.35), int(cw * 0.65)
    center_L = float(np.mean(Lg2d[cy0:cy1, cx0:cx1])) if cy1 > cy0 and cx1 > cx0 else mean_L
    corner_size_y, corner_size_x = max(1, ch // 6), max(1, cw // 6)
    corners = np.concatenate([
        Lg2d[:corner_size_y, :corner_size_x].ravel(),
        Lg2d[:corner_size_y, -corner_size_x:].ravel(),
        Lg2d[-corner_size_y:, :corner_size_x].ravel(),
        Lg2d[-corner_size_y:, -corner_size_x:].ravel(),
    ])
    corner_L = float(np.mean(corners))
    vignette_amount = cm.clip((corner_L - center_L) * 2.2, -60, 0)  # negative = darkened corners

    values = {
        "temperature": round(temperature),
        "tint": round(tint, 1),
        "exposure": round(exposure, 2),
        "contrast": round(contrast),
        "highlights": round(highlights),
        "shadows": round(shadows),
        "whites": round(whites),
        "blacks": round(blacks),
        "clarity": round(clarity),
        "texture": round(texture),
        "vibrance": round(vibrance),
        "saturation": 0,
        "hsl": hsl_adjustments,
        "color_grade": color_grade,
        "vignette_amount": round(vignette_amount),
    }

    name = preset_name or Path(path).stem + " Look"
    return LookSettings(source_path=str(path), preset_name=name, values=values)
