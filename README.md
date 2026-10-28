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

### Verse text

On the web page, every Bible reference is a button that unfolds its verses inside the card. The verses are built into the page, so it works offline. They come from the [Berean Standard Bible](https://berean.bible), which is in the public domain. `build.py` reads it from the USFM files in `bsb/`. That folder is not kept in git, so on a new machine copy it in first:

```bash
git clone https://github.com/dharmatech/bsb-usfm.git /tmp/bsb-usfm
cp -r /tmp/bsb-usfm/usfm bsb
```

The BSB has only the 66 books of the Protestant canon. A reference to a deuterocanonical book, such as 2 Maccabees, unfolds a note saying so. A reference ending in `(LXX)` unfolds the BSB verse with a note that the card means the Greek Septuagint.

Catechism numbers (`CCC 411`) link to that paragraph at scborromeo.org. Other references, like encyclicals, stay plain text. `scripture.py` reads the references and looks up the verses.

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

- plain text, or `text:` text
- `italic:` text
- `word:` with `reading:`, for a Hebrew or Greek word and its transliteration
- `by:` for the attribution under a quote

**References.** `refs:` lists the card's references, separated by ` · `. Write them as they should appear, for example `Gen 2:21–22; 3:1–6`, `Rom 5:12, 19`, `cf. 1 Chr 15:28 (LXX)` or `CCC 411, 504`. Any body item may also have its own `ref:`, so a quote names the verse it comes from. On the web page that reference sits right after the quote; the posters leave it out.

```yaml
      - italic: |
          “by one man's disobedience
          many were made sinners”
        ref: Rom 5:19
```

`build.py` stops with an error if a reference points to a verse that doesn't exist.

**Line breaks.** Graphviz does not wrap text, so break the lines yourself, as they should appear on the poster. Multi-line text goes after `|`. On the web page those lines run together and wrap to fit the screen. If a break should stay on the web page as well, as in a list, end the line with `\`.

**Markup.** Use `**bold**` and `_italic_`.

**YAML quirks.** If text contains a colon followed by a space, or starts with `*`, either put it after `|` or wrap it in double quotes.

**Links.** Every section and parallel gets an address on the web page made from its title, for example `index.html#new-ark`. To keep an address stable when you change a title, give the section or parallel an `id:`.
