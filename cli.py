#!/usr/bin/env python3
"""
Command-line version, useful for batch processing or if you'd rather not
use the GUI.

Usage:
    python cli.py path/to/photo.jpg
    python cli.py path/to/photo.jpg -o my_preset.xmp -n "Sunset Look"
"""
from __future__ import annotations

import argparse
from pathlib import Path

from app.analyzer import analyze_image
from app.xmp_writer import save_xmp


def main():
    parser = argparse.ArgumentParser(description="Extract a photo's color look as a Lightroom .xmp preset")
    parser.add_argument("photo", help="Path to the source photo (jpg/png/tiff/bmp/webp)")
    parser.add_argument("-o", "--output", help="Output .xmp path (default: <photo>_look.xmp next to the photo)")
    parser.add_argument("-n", "--name", help="Preset name stored inside the XMP (default: derived from filename)")
    args = parser.parse_args()

    photo_path = Path(args.photo)
    if not photo_path.exists():
        raise SystemExit(f"File not found: {photo_path}")

    out_path = Path(args.output) if args.output else photo_path.with_name(photo_path.stem + "_look.xmp")

    look = analyze_image(str(photo_path), preset_name=args.name)
    save_xmp(look, str(out_path))
    print(f"Saved preset '{look.preset_name}' -> {out_path}")


if __name__ == "__main__":
    main()
