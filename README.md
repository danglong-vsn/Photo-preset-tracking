# Photo Look → XMP

A small offline desktop tool: give it a photo, it analyzes that photo's
color characteristics (white balance cast, contrast, tonal balance,
per-color saturation/luminance, shadow/highlight color) and writes out a
**Lightroom Classic / Camera Raw `.xmp` preset** that reproduces that look,
so you can apply it to other photos with one click.

Everything runs locally on your own Mac or PC — no internet connection,
no upload, no cloud service involved.

## Important: what "match exact color" actually means here

A single photo doesn't contain enough information to derive a
mathematically exact, pixel-for-pixel reverse color transform — that would
require both the original unedited file *and* the edited file to diff
against. What this tool does instead is measure the photo's own color
signature and encode it as Lightroom develop settings (white balance,
tone sliders, 8-band HSL, color grading, an optional vignette). Applied to
another photo, that preset pushes the colors strongly toward the same
look — very close in practice, but each photo's own content still shows
through, so it's a faithful **look/style match**, not a literal pixel copy.

If you ever need a literal pixel copy of a specific photo's colors, that's
a different problem (image compositing, not a Lightroom preset) — ask and
this tool can be extended for that instead.

## Setup

Requires Python 3.10+ (get it from [python.org](https://www.python.org/downloads/)
if you don't have it — on Windows, tick "Add Python to PATH" during install).

```bash
# from inside this folder
pip install -r requirements.txt
```

## Running it

**GUI (recommended):**

```bash
python main.py
```

Drag a photo onto the window (or click Browse), give the preset a name,
click **Generate XMP…**, and choose where to save the `.xmp` file.

**Command line** (handy for batch scripts):

```bash
python cli.py photo.jpg
python cli.py photo.jpg -o my_preset.xmp -n "Golden Hour Look"
```

## Building a standalone app (no Python needed to run it afterward)

PyInstaller can't cross-compile, so build on the machine type you want an
app for:

- On a Mac: `bash build_mac.sh` → produces `dist/PhotoLookToXMP`
- On Windows: `build_windows.bat` → produces `dist\PhotoLookToXMP.exe`

## Using the .xmp file in Lightroom

1. In Lightroom Classic, open the **Presets** panel (Develop module) →
   click **+** → **Import Presets…** → select the `.xmp` file.
2. Or, copy it into your Lightroom presets folder so it shows up
   automatically:
   - Mac: `~/Library/Application Support/Adobe/CameraRaw/Settings/`
   - Windows: `C:\Users\<you>\AppData\Roaming\Adobe\CameraRaw\Settings\`
3. Apply it to any photo from the Presets panel, then fine-tune sliders
   as you like — it's a normal preset once imported.

It also works as a Camera Raw preset in Photoshop/Bridge the same way.

## Supported input formats

JPEG, PNG, TIFF, BMP, WEBP (anything Pillow can open). RAW camera files
(.CR2/.NEF/.ARW/etc.) aren't supported directly — export a JPEG/TIFF
version first, or ask to have RAW support added (it needs the extra
`rawpy` library).

## How the analysis works, briefly

- **White balance / tint** — from the photo's average color cast in Lab
  color space.
- **Exposure / contrast / highlights / shadows / whites / blacks** — from
  the brightness histogram (mean, spread, and 1st/99th percentiles).
- **Vibrance** — from average saturation vs. a typical-photo baseline.
- **Clarity / texture** — from local contrast (edge strength).
- **8-band HSL (Red/Orange/Yellow/Green/Aqua/Blue/Purple/Magenta)** — each
  band's saturation, luminance, and hue compared to the photo's own
  overall average.
- **Color grading (shadows/midtones/highlights)** — the average color cast
  found specifically in the darkest third, middle third, and brightest
  third of the photo (this is what captures a "teal shadows, warm
  highlights" type of look).
- **Vignette** — only added if the corners are noticeably darker than the
  center.

All of the scaling constants are heuristic (tuned to give a reasonable,
non-extreme starting preset) rather than derived from a formal color
science model — treat the result as a strong starting point you can
nudge further in Lightroom, not a locked-in scientific measurement.

## Project files

```
main.py            GUI entry point
cli.py              command-line entry point
app/analyzer.py    photo -> develop-settings analysis
app/color_math.py  sRGB/Lab/HSL math (numpy only, no heavy deps)
app/xmp_writer.py  writes the Lightroom-compatible .xmp file
app/gui.py         tkinter drag-and-drop window
```
