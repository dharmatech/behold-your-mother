# Theology poster

A poster of parallels in Catholic theology, written as a [Graphviz](https://graphviz.org) diagram.

There are two layouts of the same cards, kept side by side while we compare them:

- `poster.dot`: tall, one panel (~26 × 72 in)
- `poster-wide.dot`: wide, two panels side by side, sections I–II left and III–IV right (~49 × 47 in)

Until one layout is chosen, a change to a card must be made in both files.

- `render.sh`: builds every `.dot` file here into `NAME.svg` and `NAME.png`
- `*.svg`: zoomable vector versions; open them in a browser
- `*.png`: raster versions; ignored by git because they are large, so rebuild them with `render.sh`

```bash
./render.sh        # PNGs at 150 dpi
./render.sh 300    # PNGs at 300 dpi, print quality
```

## Layout

Each row is one parallel:

| left | center | right |
|---|---|---|
| Old Covenant **type** (tan) | the **parallel** (gold) | New Covenant **fulfillment** (blue) |

Rows are grouped into numbered sections, which are Graphviz `cluster_*` subgraphs.

## Adding a parallel

1. Add a card to each of the three column subgraphs (`old_covenant`, `parallels`, `new_covenant`).
   Copy an existing card; the column sets the colors.
2. Add a row `{ rank=same; ot; par; nt }` inside a section cluster.
3. Add the two edges, `ot -> par [arrowhead=none]; par -> nt`.
4. Add the three nodes to the invisible column chains at the bottom of the file, in row order.

Graphviz does not wrap text, so break lines yourself with `<BR/>`.
