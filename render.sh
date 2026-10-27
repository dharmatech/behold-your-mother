#!/usr/bin/env bash
# Render every .dot file here to NAME.svg (zoomable) and NAME.png (raster).
#
#   ./render.sh          # PNGs at 150 dpi
#   ./render.sh 300      # PNGs at 300 dpi (print quality)

set -euo pipefail
cd "$(dirname "$0")"

dpi="${1:-150}"

for src in *.dot; do
  name="${src%.dot}"

  # SVG: add fallback fonts so it still looks right on machines without P052.
  dot -Tsvg "$src" \
    | sed 's/font-family="P052"/font-family="P052, Palatino Linotype, Palatino, Book Antiqua, serif"/g' \
    > "$name.svg"

  dot -Tpng:cairo -Gdpi="$dpi" "$src" -o "$name.png"

  echo "$name.svg"
  echo "$name.png  ($dpi dpi)"
done
