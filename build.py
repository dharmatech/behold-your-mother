#!/usr/bin/env python3
"""Build the posters and the web page from content.yaml.

    python3 build.py      # writes poster.dot, poster-wide.dot and index.html

render.sh runs this first, then renders the .dot files with Graphviz.
Needs PyYAML (Debian/Ubuntu: python3-yaml; elsewhere: pip install pyyaml),
and the Berean Standard Bible in bsb/ for the verse text (see README.md).
"""

import html
import itertools
import re
import unicodedata
from pathlib import Path

import yaml

import scripture

HERE = Path(__file__).parent

# Poster file name → number of panels side by side.
POSTERS = {"poster": 1, "poster-wide": 2}

# The three columns of every row, left to right.
COLUMNS = {
    "type": dict(
        heading="Old Covenant", caption="the type", subgraph="old_covenant", group="ot",
        width=6.8, fill="#F1E5CF", line="#8A6440", ink="#3E2C1A", accent="#8A6440", title_pt=34,
    ),
    "parallel": dict(
        heading="The Parallel", caption="what links them", subgraph="parallels", group="par",
        width=6.6, fill="#F5E6B0", line="#B08A2E", ink="#3B2F12", accent="#9A7A22", title_pt=38,
    ),
    "fulfillment": dict(
        heading="New Covenant", caption="the fulfillment", subgraph="new_covenant", group="nt",
        width=6.8, fill="#E4ECF6", line="#2F5A8A", ink="#1C2E45", accent="#2F5A8A", title_pt=34,
    ),
}

CARD_KEYS = {"title", "subtitle", "body", "refs"}
# A body item is plain text, or one of these; any of them may also have a ref:.
BODY_KINDS = [{"text"}, {"italic"}, {"word", "reading"}, {"by"}]


# ── Reading content.yaml ─────────────────────────────────────


class ContentError(Exception):
    pass


def load(path):
    data = yaml.safe_load(path.read_text())
    sections = []
    for entry in data["contents"]:
        if "section" in entry:
            sections.append(dict(
                title=entry["section"],
                subtitle=entry.get("subtitle", ""),
                id=entry.get("id") or slug(entry["section"]),
                parallels=[],
            ))
            continue
        if not sections:
            raise ContentError("the first entry under contents: must be a section")
        missing = set(COLUMNS) - set(entry)
        extra = set(entry) - set(COLUMNS) - {"id"}
        if missing or extra:
            raise ContentError(f"a parallel in “{sections[-1]['title']}” "
                               f"is missing {sorted(missing)} or has unknown keys {sorted(extra)}")
        for role in COLUMNS:
            check_card(entry[role])
        entry.setdefault("id", slug(entry["parallel"]["title"]))
        sections[-1]["parallels"].append(entry)

    ids = [s["id"] for s in sections] + [p["id"] for s in sections for p in s["parallels"]]
    for dup in {i for i in ids if ids.count(i) > 1}:
        raise ContentError(f"two entries would both be #{dup}; give one of them an id:")

    data["sections"] = sections
    return data


def check_card(card):
    title = card.get("title", "?")
    if "title" not in card or not CARD_KEYS >= set(card):
        raise ContentError(f"card “{title}”: needs a title, and may only have {sorted(CARD_KEYS)}")
    for item in card.get("body", []):
        if not isinstance(item, str) and set(item) - {"ref"} not in BODY_KINDS:
            raise ContentError(f"card “{title}”: body item {item} should be text, text:, "
                               "italic:, word: with reading:, or by:, each with an optional ref:")


def slug(title):
    """“The New Adam” → new-adam"""
    ascii_title = unicodedata.normalize("NFKD", title).encode("ascii", "ignore").decode()
    words = re.findall(r"[a-z0-9]+", ascii_title.lower())
    if len(words) > 1 and words[0] in ("the", "a", "an"):
        words = words[1:]
    return "-".join(words)


def roman(n):
    out = ""
    for value, numeral in [(10, "X"), (9, "IX"), (5, "V"), (4, "IV"), (1, "I")]:
        while n >= value:
            out += numeral
            n -= value
    return out


def markup(text, target):
    """Escape text for "dot" or "web" and apply the light markup in content.yaml.

    **bold** and _italic_ become tags. On the poster every line break is kept.
    On the web page only a line ending in a backslash keeps its break; the
    others reflow to fit the screen.
    """
    lines = text.strip().split("\n")
    out = ""
    for k, line in enumerate(lines):
        line = line.rstrip()
        hard = line.endswith("\\")
        out += html.escape(line.removesuffix("\\").rstrip(), quote=False)
        if k < len(lines) - 1:
            out += "<BR/>" if target == "dot" else "<br>" if hard else " "
    b, i = ("B", "I") if target == "dot" else ("b", "i")
    out = re.sub(r"\*\*(.+?)\*\*", rf"<{b}>\1</{b}>", out, flags=re.S)
    out = re.sub(r"(?<!\w)_(.+?)_(?!\w)", rf"<{i}>\1</{i}>", out, flags=re.S)
    return out


def dot_text(text):
    return markup(text, "dot")


def web_text(text):
    return markup(text, "web")


# ── The posters (Graphviz) ───────────────────────────────────


def split(sections, panels):
    """Split the sections into runs, one per panel, as even in rows as possible."""
    panels = max(1, min(panels, len(sections)))
    rows = [len(s["parallels"]) for s in sections]
    best = None
    for cuts in itertools.combinations(range(1, len(sections)), panels - 1):
        bounds = [0, *cuts, len(sections)]
        tallest = max(sum(rows[a:b]) for a, b in itertools.pairwise(bounds))
        if best is None or tallest < best[0]:
            best = (tallest, bounds)
    return [sections[a:b] for a, b in itertools.pairwise(best[1])]


def node(role, parallel):
    return f"{COLUMNS[role]['group']}_{parallel['id'].replace('-', '_')}"


def suffix(k):
    """Panel 0 uses plain names (hdr_ot, group ot); panel 1 adds 2, and so on."""
    return "" if k == 0 else str(k + 1)


def dot_card(name, card, col, group):
    def row(s):
        return f"      <TR><TD>{s}</TD></TR>"

    rows = [row(f'<FONT POINT-SIZE="{col["title_pt"]}"><B>{dot_text(card["title"].upper())}</B></FONT>')]
    if card.get("subtitle"):
        rows.append(row(f'<FONT POINT-SIZE="22" COLOR="{col["accent"]}"><I>{dot_text(card["subtitle"])}</I></FONT>'))
    for item in card.get("body", []):
        if isinstance(item, str):
            rows.append(row(dot_text(item)))
        elif "text" in item:
            rows.append(row(dot_text(item["text"])))
        elif "italic" in item:
            rows.append(row(f"<I>{dot_text(item['italic'])}</I>"))
        elif "word" in item:
            rows.append(row(f'<FONT POINT-SIZE="22" COLOR="{col["accent"]}">{dot_text(item["word"])}'
                            f'<I>   {dot_text(item["reading"])}</I></FONT>'))
        elif "by" in item:
            rows.append(row(f'<FONT POINT-SIZE="17">— {dot_text(item["by"])}</FONT>'))
    if card.get("refs"):
        rows.append(row(f'<FONT POINT-SIZE="16">{dot_text(card["refs"]).replace(" · ", "  ·  ")}</FONT>'))
    attrs = f"group={group} " if group != col["group"] else ""
    return (f'    {name} [{attrs}label=<<TABLE BORDER="0" CELLSPACING="5">\n'
            + "\n".join(rows) + "\n    </TABLE>>]")


def dot(data, panels):
    sections = data["sections"]
    runs = split(sections, panels)
    panel_of = {s["id"]: k for k, run in enumerate(runs) for s in run}
    footer_panel = min(range(len(runs)), key=lambda k: sum(len(s["parallels"]) for s in runs[k]))

    out = [
        f"// {data['title']} — generated by build.py from content.yaml. Edit that file, not this one.",
        "",
        "digraph poster {",
        "  graph [",
        "    newrank=true",
        "    rankdir=TB",
        '    bgcolor="#FBF7EF"',
        '    fontname="P052"',
        '    pad="1.5,1.2"',
        "    nodesep=0.9",
        "    ranksep=0.6",
        "    splines=line",
        "  ]",
        "",
        "  node [",
        "    shape=box",
        '    style="rounded,filled"',
        '    fontname="P052"',
        "    fontsize=19",
        "    penwidth=3",
        '    margin="0.3,0.2"',
        "  ]",
        "",
        "  // ── Title, column headers, footer ──",
        "",
        "  subgraph frame {",
        '    node [shape=plaintext style="" margin=0]',
        "",
    ]

    epigraph = data["epigraph"]
    title_group = "group=par " if len(runs) == 1 else ""
    out += [
        f'    title [{title_group}label=<<TABLE BORDER="0" CELLSPACING="10">',
        f'      <TR><TD><FONT POINT-SIZE="96" COLOR="#3B2A16"><B>{dot_text(data["title"].upper())}</B></FONT></TD></TR>',
        f'      <TR><TD><FONT POINT-SIZE="32" COLOR="#6B5236"><I>{dot_text(data["subtitle"])}</I></FONT></TD></TR>',
        f'      <TR><TD><FONT POINT-SIZE="24" COLOR="#6B5236">{dot_text(epigraph["text"])}  — {dot_text(epigraph["by"])}</FONT></TD></TR>',
        "    </TABLE>>]",
        "",
    ]

    headers = []
    for k in range(len(runs)):
        row = []
        for col in COLUMNS.values():
            name = f"hdr_{col['group']}{suffix(k)}"
            row.append(name)
            out.append(
                f'    {name} [group={col["group"]}{suffix(k)} label=<<TABLE BORDER="0">'
                f'<TR><TD><FONT POINT-SIZE="36" COLOR="{col["accent"]}"><B>{col["heading"].upper()}</B></FONT></TD></TR>'
                f'<TR><TD><FONT POINT-SIZE="24" COLOR="{col["accent"]}"><I>{col["caption"]}</I></FONT></TD></TR>'
                "</TABLE>>]"
            )
        headers.append(row)
    gutters = [f"gutter{suffix(k)}" for k in range(1, len(runs))]
    if gutters:
        out.append("")
        out += [f"    {g} [style=invis width=1.5]" for g in gutters]

    out += [
        "",
        f'    footer [group=par{suffix(footer_panel)} label=<<TABLE BORDER="0" CELLSPACING="6">',
        *[f'      <TR><TD><FONT POINT-SIZE="18" COLOR="#6B5236">{dot_text(n).replace(" · ", "  ·  ")}</FONT></TD></TR>'
          for n in data["notes"]],
        "    </TABLE>>]",
        "  }",
    ]

    for role, col in COLUMNS.items():
        out += [
            "",
            f"  // ── {col['heading']}: {col['caption']} ──",
            "",
            f"  subgraph {col['subgraph']} {{",
            f'    node [group={col["group"]} width={col["width"]} fillcolor="{col["fill"]}" '
            f'color="{col["line"]}" fontcolor="{col["ink"]}"]',
        ]
        for s in sections:
            for p in s["parallels"]:
                group = col["group"] + suffix(panel_of[s["id"]])
                out += ["", dot_card(node(role, p), p[role], col, group)]
        out.append("  }")

    # Rows, grouped into sections.
    out += ["", "  // ── Rows, grouped into sections ──", ""]
    header_row = [name for k, row in enumerate(headers) for name in ([gutters[k - 1]] if k else []) + row]
    out.append(f"  {{ rank=same; {'; '.join(header_row)} }}")
    for n, s in enumerate(sections, 1):
        out += [
            "",
            f"  subgraph cluster_{s['id'].replace('-', '_')} {{",
            f'    label=<<FONT POINT-SIZE="30" COLOR="#6B5236"><B>{roman(n)} · {dot_text(s["title"].upper())}</B>'
            f'   <I>{dot_text(s["subtitle"])}</I></FONT>>',
            "    labeljust=l",
            '    style="rounded,dashed"',
            '    color="#CDBB98"',
            "    penwidth=2",
            "    margin=36",
            "",
        ]
        for p in s["parallels"]:
            out.append(f"    {{ rank=same; {'; '.join(node(r, p) for r in COLUMNS)} }}")
        out.append("  }")

    # Each row: type —— parallel ——▶ fulfillment.
    out += ["", "  // ── Parallels: type —— parallel ——▶ fulfillment ──", "",
            '  edge [color="#B08A2E" penwidth=5 arrowsize=1.4]', ""]
    for s in sections:
        for p in s["parallels"]:
            t, par, f = (node(r, p) for r in COLUMNS)
            out.append(f"  {t} -> {par} [arrowhead=none];  {par} -> {f}")

    # Invisible chains that keep each column straight.
    out += ["", "  // ── Invisible scaffolding: keeps the columns straight ──", "",
            "  edge [style=invis weight=100]", "",
            "  " + " -> ".join(header_row)]
    out += [f"  title -> {row[1]}" for row in headers]
    for k, run in enumerate(runs):
        if len(runs) > 1:
            out += ["", f"  // Panel {k + 1}: sections {roman(sections.index(run[0]) + 1)}–{roman(sections.index(run[-1]) + 1)}"]
        for c, role in enumerate(COLUMNS):
            chain = [headers[k][c]] + [node(role, p) for s in run for p in s["parallels"]]
            if role == "parallel" and k == footer_panel:
                chain.append("footer")
            out.append("  " + " -> ".join(chain))

    out.append("}")
    return "\n".join(out) + "\n"


# ── The web page ─────────────────────────────────────────────


def word_attrs(word):
    if re.search(r"[֐-׿]", word):
        return ' lang="he" dir="rtl"'
    if re.search(r"[Ͱ-Ͽἀ-῿]", word):
        return ' lang="grc"'
    return ""


class References:
    """Turns a line of references into buttons and links for the web page.

    Each Bible reference becomes a button that unfolds its verses in a panel
    right below the line it is on. Catechism numbers link to the paragraph.
    """

    def __init__(self, bible):
        self.bible = bible
        self.count = itertools.count(1)

    def render(self, line):
        """(inline HTML, [panel HTML]) for a line of references."""
        inline, panels = [], []
        for part in scripture.parse(line):
            if isinstance(part, scripture.Passage):
                pid = f"v{next(self.count)}"
                inline.append(("cf. " if part.cf else "")
                              + f'<button type="button" class="ref" aria-expanded="false" '
                              f'aria-controls="{pid}">{html.escape(part.label)}</button>')
                panels.append(self.panel(pid, part))
            elif isinstance(part, scripture.Catechism):
                inline.append("CCC " + ", ".join(
                    f'<a href="{part.url(n)}" target="_blank" rel="noopener">{n}</a>' for n in part.numbers))
            else:
                inline.append(web_text(part.text))
        return " · ".join(inline), panels

    def panel(self, pid, passage):
        if self.bible.has(passage.book):
            verses = self.bible.render(passage)
        else:
            verses = (f'<p class="note">{scripture.NAMES[passage.book]} is not in the {self.bible.name}, '
                      "which has only the 66 books of the Protestant canon.</p>")
        note = ""
        if passage.lxx:
            note = ('<p class="note">The card points to the Greek Septuagint (LXX). '
                    f"The {self.bible.abbreviation} translates the Hebrew, so its wording may differ.</p>")
        return (f'          <div class="passage" id="{pid}" hidden>'
                f'<p class="where">{html.escape(passage.heading)}'
                f'<abbr title="{self.bible.name}">{self.bible.abbreviation}</abbr></p>'
                f'{verses}{note}'
                f'<button type="button" class="close" aria-controls="{pid}">Close</button></div>')


def web_card(role, card, refs):
    col = COLUMNS[role]
    out = [
        f'        <article class="card {role}">',
        f'          <p class="role">{col["heading"]} · {col["caption"]}</p>',
        f'          <h3>{web_text(card["title"])}</h3>',
    ]
    if card.get("subtitle"):
        out.append(f'          <p class="sub">{web_text(card["subtitle"])}</p>')
    for item in card.get("body", []):
        if isinstance(item, str):
            item = {"text": item}
        if "text" in item:
            line, attrs = web_text(item["text"]), ""
        elif "italic" in item:
            line, attrs = web_text(item["italic"]), ' class="italic"'
        elif "word" in item:
            line, attrs = (f'<span{word_attrs(item["word"])}>{web_text(item["word"])}</span> '
                           f'<i>{web_text(item["reading"])}</i>'), ' class="word"'
        else:
            line, attrs = f'— {web_text(item["by"])}', ' class="by"'
        panels = []
        if item.get("ref"):
            cite, panels = refs.render(item["ref"])
            line += f' <span class="cite">{cite}</span>'
        out.append(f"          <p{attrs}>{line}</p>")
        out += panels
    if card.get("refs"):
        line, panels = refs.render(card["refs"])
        out.append(f'          <p class="refs">{line}</p>')
        out += panels
    out.append("        </article>")
    return out


def web(data, bible):
    refs = References(bible)
    body = []
    for n, s in enumerate(data["sections"], 1):
        count = len(s["parallels"])
        body += [
            f'  <details class="section" id="{s["id"]}">',
            "    <summary>",
            f'      <span class="num">{roman(n)}</span>',
            '      <span class="heading">',
            f'        <h2>{web_text(s["title"])}</h2>',
            f'        <span class="sub">{web_text(s["subtitle"])} · {count}&nbsp;parallel{"s" if count != 1 else ""}</span>',
            "      </span>",
            "    </summary>",
        ]
        for p in s["parallels"]:
            body += [
                f'    <details class="parallel" id="{p["id"]}">',
                "      <summary>",
                '        <span class="heading">',
                f'          <span class="name">{web_text(p["parallel"]["title"])}</span>',
                f'          <span class="pair"><span class="type">{web_text(p["type"]["title"])}</span>'
                f'<span class="arrow" aria-label="to"> → </span>'
                f'<span class="fulfillment">{web_text(p["fulfillment"]["title"])}</span></span>',
                "        </span>",
                "      </summary>",
                '      <div class="cards">',
                *web_card("type", p["type"], refs),
                '        <div class="link" aria-hidden="true"></div>',
                *web_card("parallel", p["parallel"], refs),
                '        <div class="link arrow" aria-hidden="true"></div>',
                *web_card("fulfillment", p["fulfillment"], refs),
                "      </div>",
                "    </details>",
            ]
        body.append("  </details>")

    posters = " · ".join(
        f'<a href="{name}.svg">{"tall" if panels == 1 else "wide"}</a>' for name, panels in POSTERS.items()
    )
    notes = "\n".join(f"    <p>{web_text(n)}</p>" for n in data["notes"])
    epigraph = data["epigraph"]
    return (
        PAGE.replace("{{title}}", html.escape(data["title"]))
        .replace("{{description}}", html.escape(data["subtitle"]))
        .replace("{{title_html}}", web_text(data["title"]))
        .replace("{{subtitle_html}}", web_text(data["subtitle"]))
        .replace("{{epigraph}}", web_text(epigraph["text"]))
        .replace("{{epigraph_by}}", web_text(epigraph["by"]))
        .replace("{{sections}}", "\n".join(body))
        .replace("{{posters}}", posters)
        .replace("{{notes}}", notes)
    )


PAGE = """\
<!doctype html>
<!-- Generated by build.py from content.yaml. Edit that file, not this one. -->
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{{title}}</title>
<meta name="description" content="{{description}}">
<style>
  :root {
    color-scheme: light dark;
    --serif: P052, "Palatino Linotype", Palatino, "Book Antiqua", Georgia, serif;
    --bg: #FBF7EF;
    --panel: #FFFDF8;
    --ink: #3B2A16;
    --muted: #6B5236;
    --rule: #E2D6BF;
    --link: #B08A2E;
    --type-fill: #F1E5CF;  --type-line: #8A6440;  --type-ink: #3E2C1A;  --type-accent: #7A5636;
    --par-fill: #F5E6B0;   --par-line: #B08A2E;   --par-ink: #3B2F12;   --par-accent: #7A5E12;
    --ful-fill: #E4ECF6;   --ful-line: #2F5A8A;   --ful-ink: #1C2E45;   --ful-accent: #2F5A8A;
  }
  @media (prefers-color-scheme: dark) {
    :root {
      --bg: #191510;
      --panel: #211C15;
      --ink: #EFE6D6;
      --muted: #BBA98C;
      --rule: #3A3226;
      --link: #B8962F;
      --type-fill: #2B2219;  --type-line: #9C7A55;  --type-ink: #F1E5CF;  --type-accent: #D2B48C;
      --par-fill: #30280F;   --par-line: #B8962F;   --par-ink: #F5E6B0;   --par-accent: #E2C163;
      --ful-fill: #172130;   --ful-line: #4F7AAE;   --ful-ink: #E4ECF6;   --ful-accent: #9DBCE3;
    }
  }

  * { box-sizing: border-box; }
  body {
    margin: 0;
    background: var(--bg);
    color: var(--ink);
    font: 18px/1.5 var(--serif);
    -webkit-text-size-adjust: 100%;
  }
  .page { max-width: 1180px; margin: 0 auto; padding: 36px 16px 56px; }
  a { color: inherit; }

  /* Masthead */
  header { text-align: center; margin-bottom: 28px; }
  h1 {
    margin: 0 0 10px;
    font-size: clamp(30px, 7.5vw, 58px);
    line-height: 1.1;
    letter-spacing: 0.04em;
    text-transform: uppercase;
    text-wrap: balance;
  }
  .subtitle {
    margin: 0 auto 18px;
    max-width: 34em;
    color: var(--muted);
    font-size: clamp(18px, 3.6vw, 23px);
    font-style: italic;
    text-wrap: balance;
  }
  blockquote { margin: 0 auto; max-width: 32em; color: var(--muted); font-size: 16px; text-wrap: balance; }
  blockquote footer { margin-top: 2px; font-size: 15px; }
  .tools { display: flex; justify-content: center; gap: 8px; margin-top: 22px; }
  .tools button {
    font: inherit;
    font-size: 15px;
    color: var(--muted);
    background: transparent;
    border: 1px solid var(--rule);
    border-radius: 999px;
    padding: 6px 16px;
    cursor: pointer;
  }
  .tools button:hover { border-color: var(--muted); }

  /* Folding: sections, and the parallels inside them */
  summary { list-style: none; cursor: pointer; display: flex; align-items: center; gap: 14px; }
  summary::-webkit-details-marker { display: none; }
  summary::after {
    content: "";
    flex: none;
    margin-left: auto;
    width: 9px;
    height: 9px;
    border-right: 2px solid var(--muted);
    border-bottom: 2px solid var(--muted);
    transform: translateY(-3px) rotate(45deg);
    transition: transform 0.15s;
  }
  details[open] > summary::after { transform: translateY(2px) rotate(225deg); }
  summary:focus-visible { outline: 2px solid var(--link); outline-offset: 2px; border-radius: 10px; }
  .heading { display: flex; flex-direction: column; min-width: 0; }

  .section {
    background: var(--panel);
    border: 1px solid var(--rule);
    border-radius: 16px;
    margin-bottom: 12px;
  }
  .section > summary { padding: 16px 18px; }
  .section .num {
    flex: none;
    min-width: 1.6em;
    color: var(--par-accent);
    font-weight: 700;
    font-size: 20px;
  }
  .section h2 { margin: 0; font-size: 21px; line-height: 1.25; letter-spacing: 0.02em; }
  .section .sub { color: var(--muted); font-size: 16px; font-style: italic; }
  .section[open] > summary { border-bottom: 1px solid var(--rule); }

  .parallel { border-bottom: 1px solid var(--rule); }
  .parallel:last-child { border-bottom: 0; }
  .parallel > summary { padding: 12px 18px; }
  .parallel .name { color: var(--par-accent); font-weight: 700; font-size: 18px; line-height: 1.3; }
  .parallel .pair { font-size: 16px; }
  .pair .type { color: var(--type-accent); }
  .pair .fulfillment { color: var(--ful-accent); }
  .pair .arrow { color: var(--link); }
  .parallel[open] > summary { background: color-mix(in srgb, var(--par-fill) 40%, transparent); }

  /* The three cards of a parallel: stacked on a phone, side by side when there is room */
  .cards { display: grid; padding: 14px 12px 18px; }
  .link { justify-self: center; width: 4px; height: 26px; background: var(--link); position: relative; }
  .link.arrow { height: 22px; margin-bottom: 8px; }
  .link.arrow::after {
    content: "";
    position: absolute;
    left: 50%;
    top: 100%;
    transform: translateX(-50%);
    border: 8px solid transparent;
    border-top: 10px solid var(--link);
    border-bottom: 0;
  }

  .card {
    border: 2px solid var(--line);
    border-radius: 14px;
    background: var(--fill);
    color: var(--ink);
    padding: 14px 18px 14px;
    text-align: center;
  }
  .card.type        { --fill: var(--type-fill); --line: var(--type-line); --ink: var(--type-ink); --accent: var(--type-accent); }
  .card.parallel    { --fill: var(--par-fill);  --line: var(--par-line);  --ink: var(--par-ink);  --accent: var(--par-accent); }
  .card.fulfillment { --fill: var(--ful-fill);  --line: var(--ful-line);  --ink: var(--ful-ink);  --accent: var(--ful-accent); }
  .card p { margin: 10px 0 0; text-wrap: pretty; }
  .card .role { margin: 0 0 4px; font-size: 12.5px; letter-spacing: 0.12em; text-transform: uppercase; color: var(--accent); }
  .card h3 { margin: 0; font-size: 22px; line-height: 1.25; letter-spacing: 0.05em; text-transform: uppercase; text-wrap: balance; }
  .card.parallel h3 { font-size: 24px; }
  .card .sub { margin-top: 2px; color: var(--accent); font-style: italic; }
  .card .italic { font-style: italic; }
  .card .word { color: var(--accent); font-size: 19px; }
  .card .by { margin-top: 2px; font-size: 15px; }
  .card .refs {
    margin-top: 12px;
    padding-top: 8px;
    border-top: 1px solid color-mix(in srgb, var(--accent) 35%, transparent);
    font-size: 14.5px;
  }

  /* References: a Bible reference unfolds its verses; a Catechism number is a link */
  .cite { margin-left: 0.2em; color: var(--accent); font-size: 14.5px; font-style: normal; }
  .refs a, .cite a { color: inherit; text-underline-offset: 3px; }
  button.ref {
    font: inherit;
    color: inherit;
    background: none;
    border: 0;
    margin: -4px -2px;
    padding: 4px 2px;
    cursor: pointer;
    text-decoration: underline dotted;
    text-decoration-thickness: 1px;
    text-underline-offset: 3px;
    white-space: nowrap;
  }
  button.ref[aria-expanded="true"] { font-weight: 700; text-decoration-style: solid; }

  .passage {
    margin: 10px -4px 0;
    padding: 12px 14px 6px;
    border: 1px solid color-mix(in srgb, var(--line) 45%, transparent);
    border-radius: 10px;
    background: color-mix(in srgb, var(--bg) 65%, var(--fill));
    text-align: left;
    font-size: 16.5px;
    line-height: 1.55;
  }
  .card .passage p { margin: 0 0 8px; }
  .card .passage .where { margin-bottom: 6px; font-size: 15px; font-weight: 700; }
  .passage abbr {
    margin-left: 0.5em;
    font-size: 12px;
    font-weight: 400;
    letter-spacing: 0.1em;
    color: var(--accent);
    text-decoration: none;
  }
  .passage sup { margin-right: 3px; font-size: 11px; font-weight: 700; color: var(--accent); }
  .card .passage :is(.q1, .q2, .li1, .li2) { margin: 0; }
  .passage .q2, .passage .li2 { padding-left: 1.5em; }
  .passage .li1 { padding-left: 0.75em; }
  .card .passage .stanza { margin-top: 8px; }
  .card .passage :is(.q1, .q2, .li1, .li2):has(+ :not(.q1, .q2, .li1, .li2)) { margin-bottom: 8px; }
  .card .passage .gap { margin: -2px 0 6px; text-align: center; color: var(--accent); }
  .card .passage .note { font-size: 14px; font-style: italic; color: var(--accent); }
  .passage .close {
    display: block;
    margin: 0 -4px 0 auto;
    padding: 4px;
    font: inherit;
    font-size: 14px;
    color: var(--accent);
    background: none;
    border: 0;
    cursor: pointer;
  }

  @media (min-width: 900px) {
    .cards { grid-template-columns: 1fr 34px 1fr 34px 1fr; padding: 18px; }
    .link, .link.arrow { justify-self: stretch; align-self: center; width: auto; height: 4px; margin: 0; }
    .link.arrow { margin-right: 10px; }
    .link.arrow::after {
      left: 100%;
      top: 50%;
      transform: translateY(-50%);
      border: 8px solid transparent;
      border-left: 10px solid var(--link);
      border-right: 0;
    }
  }

  /* Footer */
  .notes { margin-top: 32px; text-align: center; color: var(--muted); font-size: 14.5px; }
  .notes p { margin: 4px 0; text-wrap: pretty; }
  .notes .posters { margin-bottom: 14px; font-size: 16px; }
</style>
</head>
<body>
<div class="page">
<header>
  <h1>{{title_html}}</h1>
  <p class="subtitle">{{subtitle_html}}</p>
  <blockquote>
    <p>{{epigraph}}</p>
    <footer>— {{epigraph_by}}</footer>
  </blockquote>
  <div class="tools">
    <button type="button" id="open-all">Open all</button>
    <button type="button" id="close-all">Close all</button>
  </div>
</header>
<main>
{{sections}}
</main>
<footer class="notes">
  <p class="posters">See it all as a poster: {{posters}}</p>
{{notes}}
    <p>Tap a Bible reference to read its verses, from the
      <a href="https://berean.bible" target="_blank" rel="noopener">Berean Standard Bible</a> (public domain).
      Catechism numbers link to the text at scborromeo.org.</p>
</footer>
</div>
<script>
  const all = () => document.querySelectorAll("details");
  document.getElementById("open-all").onclick = () => all().forEach(d => (d.open = true));
  document.getElementById("close-all").onclick = () => all().forEach(d => (d.open = false));

  // Open whatever the address points at, e.g. index.html#new-ark.
  function reveal() {
    const target = document.getElementById(decodeURIComponent(location.hash.slice(1)));
    if (!target) return;
    for (let d = target.closest("details"); d; d = d.parentElement.closest("details")) d.open = true;
    target.scrollIntoView();
  }
  addEventListener("hashchange", reveal);
  reveal();

  // Point the address at whatever was just opened, so it can be shared.
  document.addEventListener("click", e => {
    const summary = e.target.closest("summary");
    if (summary && !summary.parentElement.open) history.replaceState(null, "", "#" + summary.parentElement.id);
  });

  // A Bible reference unfolds its verses; tapping it again, or Close, folds them away.
  document.addEventListener("click", e => {
    const button = e.target.closest("button.ref, button.close");
    if (!button) return;
    const panel = document.getElementById(button.getAttribute("aria-controls"));
    const ref = document.querySelector(`button.ref[aria-controls="${panel.id}"]`);
    const open = button.classList.contains("ref") && panel.hidden;
    panel.hidden = !open;
    ref.setAttribute("aria-expanded", open);
    if (!open && button !== ref) ref.scrollIntoView({ block: "nearest" });
  });
</script>
</body>
</html>
"""


# ── Main ─────────────────────────────────────────────────────


def main():
    try:
        data = load(HERE / "content.yaml")
        page = web(data, scripture.Bible(HERE / "bsb"))
    except (ContentError, scripture.ReferenceError_) as e:
        raise SystemExit(f"content.yaml: {e}")
    for name, panels in POSTERS.items():
        (HERE / f"{name}.dot").write_text(dot(data, panels))
        print(f"{name}.dot")
    (HERE / "index.html").write_text(page)
    print("index.html")


if __name__ == "__main__":
    main()
