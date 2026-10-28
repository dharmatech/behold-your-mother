# Theology poster

Parallels in Catholic theology, written once and published in three forms:

- `index.html`: a web page for reading on a phone. Sections fold open, and each parallel opens into its three cards.
- `poster.svg`: a tall poster with one panel (~26 × 72 in)
- `poster-wide.svg`: a wide poster with two panels side by side (~49 × 47 in)

All three are built from **`content.yaml`**, the one place where the content lives.

```bash
./render.sh        # rebuild everything; poster PNGs at 150 dpi
./render.sh 300    # the same, with PNGs at 300 dpi for print
```

`render.sh` runs `build.py`, which reads `content.yaml` and writes `index.html` and the Graphviz files `poster.dot` and `poster-wide.dot`. Graphviz then renders each `.dot` file to an `.svg` and a `.png`. The `.dot` and `.png` files are not kept in git. `build.py` needs PyYAML (`python3-yaml` on Debian/Ubuntu, otherwise `pip install pyyaml`).

## Layout

Each row is one parallel:

| left | center | right |
|---|---|---|
| Old Covenant **type** (tan) | the **parallel** (gold) | New Covenant **fulfillment** (blue) |

Rows are grouped into numbered sections. Sections are numbered in the order they appear in `content.yaml`. The wide poster splits the sections into two panels, choosing the split that makes the panels closest in height.

## Writing content.yaml

Under `contents:` is a list of sections and parallels. Each parallel belongs to the section above it.

```yaml
- section: In the Beginning
  subtitle: the first man and woman

- type:
    title: Adam
    body:
      - |
        the first man, formed
        from the dust of the ground
      - italic: |
          “by one man's disobedience
          many were made sinners”
    refs: Gen 2:7 · Rom 5:12, 19
  parallel:
    title: The New Adam
    ...
  fulfillment:
    title: Jesus Christ
    ...
```

A card has a `title`, an optional `subtitle`, a `body` and `refs`. Write titles in normal case; the poster puts them in capitals. Each body item is one of these:

- plain text
- `italic:` text
- `word:` with `reading:`, for a Hebrew or Greek word and its transliteration
- `by:` for the attribution under a quote

**Line breaks.** Graphviz does not wrap text, so break the lines yourself, as they should appear on the poster. Multi-line text goes after `|`. On the web page those lines run together and wrap to fit the screen. If a break should stay on the web page as well, as in a list, end the line with `\`.

**Markup.** Use `**bold**` and `_italic_`.

**YAML quirks.** If text contains a colon followed by a space, or starts with `*`, either put it after `|` or wrap it in double quotes.

**Links.** Every section and parallel gets an address on the web page made from its title, for example `index.html#new-ark`. To keep an address stable when you change a title, give the section or parallel an `id:`.
