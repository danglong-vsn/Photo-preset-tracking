"""
Builds a Lightroom Classic / Adobe Camera Raw compatible .xmp preset file
from a LookSettings object produced by analyzer.py.

The output follows the same rdf:Description / crs: namespace structure
Lightroom itself writes when you export a preset, so it can be dropped into
Lightroom's "Develop Presets" folder (or imported via the Presets panel).
"""
from __future__ import annotations

import uuid
import xml.sax.saxutils as sax

from .analyzer import LookSettings, HUE_BANDS

CRS_NS = "http://ns.adobe.com/camera-raw-settings/1.0/"


def _esc(value: str) -> str:
    return sax.escape(str(value), {'"': "&quot;"})


def _num(value) -> str:
    if isinstance(value, float):
        # trim trailing zeros but keep it readable
        s = f"{value:.4f}".rstrip("0").rstrip(".")
        return s if s not in ("", "-") else "0"
    return str(value)


def build_xmp(look: LookSettings) -> str:
    v = look.values
    hsl = v["hsl"]
    cg = v["color_grade"]
    preset_uuid = str(uuid.uuid4()).upper()

    def hsl_attr(kind: str) -> str:
        """kind: 'hue' | 'sat' | 'lum' -> the 8 crs:*AdjustmentXxx attributes"""
        prefix = {"hue": "HueAdjustment", "sat": "SaturationAdjustment", "lum": "LuminanceAdjustment"}[kind]
        lines = []
        for name, _center in HUE_BANDS:
            val = hsl.get(name, {}).get(kind, 0.0)
            lines.append(f'   crs:{prefix}{name}="{_num(round(val))}"')
        return "\n".join(lines)

    vignette_block = ""
    if v["vignette_amount"] < -2:
        vignette_block = f'''
   crs:PostCropVignetteAmount="{_num(v["vignette_amount"])}"
   crs:PostCropVignetteMidpoint="50"
   crs:PostCropVignetteFeather="50"
   crs:PostCropVignetteRoundness="0"
   crs:PostCropVignetteStyle="1"
   crs:PostCropVignetteHighlightContrast="0"'''

    xmp = f'''<?xpacket begin="﻿" id="W5M0MpCehiHzreSzNTczkc9d"?>
<x:xmpmeta xmlns:x="adobe:ns:meta/" x:xmptk="PhotoLookToXMP 1.0">
 <rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">
  <rdf:Description rdf:about=""
    xmlns:crs="{CRS_NS}"
   crs:PresetType="Normal"
   crs:Cluster=""
   crs:UUID="{preset_uuid}"
   crs:SupportsAmount="false"
   crs:SupportsColor="true"
   crs:SupportsMonochrome="true"
   crs:SupportsHighDynamicRange="true"
   crs:SupportsNormalDynamicRange="true"
   crs:SupportsSceneReferred="true"
   crs:SupportsOutputReferred="true"
   crs:CameraModelRestriction=""
   crs:Copyright=""
   crs:ContactInfo=""
   crs:Version="15.4"
   crs:ProcessVersion="15.4"
   crs:WhiteBalance="Custom"
   crs:Temperature="{_num(v['temperature'])}"
   crs:Tint="{_num(v['tint'])}"
   crs:Exposure2012="{_num(v['exposure'])}"
   crs:Contrast2012="{_num(v['contrast'])}"
   crs:Highlights2012="{_num(v['highlights'])}"
   crs:Shadows2012="{_num(v['shadows'])}"
   crs:Whites2012="{_num(v['whites'])}"
   crs:Blacks2012="{_num(v['blacks'])}"
   crs:Clarity2012="{_num(v['clarity'])}"
   crs:Dehaze="0"
   crs:Texture="{_num(v['texture'])}"
   crs:Vibrance="{_num(v['vibrance'])}"
   crs:Saturation="{_num(v['saturation'])}"
   crs:ParametricShadows="0"
   crs:ParametricDarks="0"
   crs:ParametricLights="0"
   crs:ParametricHighlights="0"
   crs:ParametricShadowSplit="25"
   crs:ParametricMidtoneSplit="50"
   crs:ParametricHighlightSplit="75"
   crs:SharpenRadius="+1.0"
   crs:SharpenDetail="25"
   crs:SharpenEdgeMasking="0"
   crs:LuminanceSmoothing="0"
   crs:ColorNoiseReduction="25"
   crs:ConvertToGrayscale="False"
   crs:ToneCurveName2012="Linear"
   crs:CameraProfile="Adobe Color"
   crs:LensProfileEnable="0"
   crs:AutoLateralCA="0"
{hsl_attr('hue')}
{hsl_attr('sat')}
{hsl_attr('lum')}
   crs:SplitToningShadowHue="{_num(round(cg['shadow_hue']))}"
   crs:SplitToningShadowSaturation="{_num(round(cg['shadow_sat']))}"
   crs:SplitToningHighlightHue="{_num(round(cg['highlight_hue']))}"
   crs:SplitToningHighlightSaturation="{_num(round(cg['highlight_sat']))}"
   crs:SplitToningBalance="0"
   crs:ColorGradeShadowHue="{_num(round(cg['shadow_hue']))}"
   crs:ColorGradeShadowSat="{_num(round(cg['shadow_sat']))}"
   crs:ColorGradeShadowLum="0"
   crs:ColorGradeMidtoneHue="{_num(round(cg['midtone_hue']))}"
   crs:ColorGradeMidtoneSat="{_num(round(cg['midtone_sat']))}"
   crs:ColorGradeMidtoneLum="0"
   crs:ColorGradeHighlightHue="{_num(round(cg['highlight_hue']))}"
   crs:ColorGradeHighlightSat="{_num(round(cg['highlight_sat']))}"
   crs:ColorGradeHighlightLum="0"
   crs:ColorGradeGlobalHue="0"
   crs:ColorGradeGlobalSat="0"
   crs:ColorGradeGlobalLum="0"
   crs:ColorGradeBlending="50"{vignette_block}
   crs:HasSettings="True"
   crs:HasCrop="False"
   crs:AlreadyApplied="False">
   <crs:Name>
    <rdf:Alt>
     <rdf:li xml:lang="x-default">{_esc(look.preset_name)}</rdf:li>
    </rdf:Alt>
   </crs:Name>
   <crs:ShortName>
    <rdf:Alt>
     <rdf:li xml:lang="x-default">{_esc(look.preset_name)}</rdf:li>
    </rdf:Alt>
   </crs:ShortName>
   <crs:Group>
    <rdf:Alt>
     <rdf:li xml:lang="x-default">Extracted Looks</rdf:li>
    </rdf:Alt>
   </crs:Group>
   <crs:ToneCurvePV2012>
    <rdf:Seq>
     <rdf:li>0, 0</rdf:li>
     <rdf:li>255, 255</rdf:li>
    </rdf:Seq>
   </crs:ToneCurvePV2012>
   <crs:ToneCurvePV2012Red>
    <rdf:Seq>
     <rdf:li>0, 0</rdf:li>
     <rdf:li>255, 255</rdf:li>
    </rdf:Seq>
   </crs:ToneCurvePV2012Red>
   <crs:ToneCurvePV2012Green>
    <rdf:Seq>
     <rdf:li>0, 0</rdf:li>
     <rdf:li>255, 255</rdf:li>
    </rdf:Seq>
   </crs:ToneCurvePV2012Green>
   <crs:ToneCurvePV2012Blue>
    <rdf:Seq>
     <rdf:li>0, 0</rdf:li>
     <rdf:li>255, 255</rdf:li>
    </rdf:Seq>
   </crs:ToneCurvePV2012Blue>
  </rdf:Description>
 </rdf:RDF>
</x:xmpmeta>
<?xpacket end="w"?>
'''
    return xmp


def save_xmp(look: LookSettings, out_path: str) -> str:
    xmp = build_xmp(look)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(xmp)
    return out_path
