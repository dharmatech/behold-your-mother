# Theology poster

A poster of parallels in Catholic theology, written as a [Graphviz](https://graphviz.org) diagram.

- `poster.dot`: the source; edit this file
- `render.sh`: builds the outputs
- `poster.svg`: zoomable vector version; open it in a browser
- `poster.png`: raster version; ignored by git because it is large, so rebuild it with `render.sh`

```bash
./render.sh        # PNG at 150 dpi (~26 × 35 in)
./render.sh 300    # PNG at 300 dpi, print quality
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
