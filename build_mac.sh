#!/bin/bash
# Build a standalone double-clickable Mac app (no Python required to run it).
# Run this ON A MAC, from this folder, after `pip3 install -r requirements.txt`.
set -e
pip3 install -r requirements.txt
pyinstaller --noconfirm --windowed --onefile \
  --name "PhotoLookToXMP" \
  main.py
echo ""
echo "Done. Find the app at: dist/PhotoLookToXMP"
echo "(First launch: right-click -> Open, since it isn't notarized/signed.)"
