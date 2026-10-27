#!/usr/bin/env bash
# Render poster.dot to poster.svg (zoomable) and poster.png (raster).
#
#   ./render.sh          # PNG at 150 dpi
#   ./render.sh 300      # PNG at 300 dpi (print quality)

set -euo pipefail
cd "$(dirname "$0")"

dpi="${1:-150}"

# SVG: add fallback fonts so it still looks right on machines without P052.
dot -Tsvg poster.dot \
  | sed 's/font-family="P052"/font-family="P052, Palatino Linotype, Palatino, Book Antiqua, serif"/g' \
  > poster.svg

dot -Tpng:cairo -Gdpi="$dpi" poster.dot -o poster.png

echo "poster.svg"
echo "poster.png  ($dpi dpi)"
