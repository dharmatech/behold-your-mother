"""Scripture and Catechism references, and the verse text behind them.

References are written in content.yaml the way they appear on the poster:
"Gen 2:21–22; 3:1–6", "cf. 1 Chr 15:28 (LXX)", "CCC 411, 504". parse()
splits a line of them into parts, and Bible looks up the verses in the
Berean Standard Bible, read from the USFM files in bsb/.
"""

import html
import re
from dataclasses import dataclass
from functools import cached_property
from pathlib import Path

# (USFM code, name, abbreviations), in canonical order.
BOOKS = [
    ("GEN", "Genesis", "Gen, Gn"),
    ("EXO", "Exodus", "Ex, Exod"),
    ("LEV", "Leviticus", "Lev, Lv"),
    ("NUM", "Numbers", "Num, Nm"),
    ("DEU", "Deuteronomy", "Deut, Dt"),
    ("JOS", "Joshua", "Josh, Jos"),
    ("JDG", "Judges", "Judg, Jgs"),
    ("RUT", "Ruth", "Ru"),
    ("1SA", "1 Samuel", "1 Sam, 1 Sm"),
    ("2SA", "2 Samuel", "2 Sam, 2 Sm"),
    ("1KI", "1 Kings", "1 Kgs, 1 Kg"),
    ("2KI", "2 Kings", "2 Kgs, 2 Kg"),
    ("1CH", "1 Chronicles", "1 Chr, 1 Chron"),
    ("2CH", "2 Chronicles", "2 Chr, 2 Chron"),
    ("EZR", "Ezra", "Ezr"),
    ("NEH", "Nehemiah", "Neh"),
    ("TOB", "Tobit", "Tob, Tb"),
    ("JDT", "Judith", "Jdt"),
    ("EST", "Esther", "Esth, Est"),
    ("1MA", "1 Maccabees", "1 Macc, 1 Mc"),
    ("2MA", "2 Maccabees", "2 Macc, 2 Mc"),
    ("JOB", "Job", "Jb"),
    ("PSA", "Psalms", "Ps, Pss, Psalm"),
    ("PRO", "Proverbs", "Prov, Prv"),
    ("ECC", "Ecclesiastes", "Eccl, Eccles, Qoh"),
    ("SNG", "Song of Songs", "Song, Sg, Song of Solomon"),
    ("WIS", "Wisdom", "Wis, Ws"),
    ("SIR", "Sirach", "Sir"),
    ("ISA", "Isaiah", "Isa, Is"),
    ("JER", "Jeremiah", "Jer"),
    ("LAM", "Lamentations", "Lam"),
    ("BAR", "Baruch", "Bar"),
    ("EZK", "Ezekiel", "Ezek, Ez"),
    ("DAN", "Daniel", "Dan, Dn"),
    ("HOS", "Hosea", "Hos"),
    ("JOL", "Joel", "Jl"),
    ("AMO", "Amos", "Am"),
    ("OBA", "Obadiah", "Obad, Ob"),
    ("JON", "Jonah", "Jon"),
    ("MIC", "Micah", "Mic, Mi"),
    ("NAM", "Nahum", "Nah, Na"),
    ("HAB", "Habakkuk", "Hab, Hb"),
    ("ZEP", "Zephaniah", "Zeph, Zep"),
    ("HAG", "Haggai", "Hag, Hg"),
    ("ZEC", "Zechariah", "Zech, Zec"),
    ("MAL", "Malachi", "Mal"),
    ("MAT", "Matthew", "Mt, Matt"),
    ("MRK", "Mark", "Mk"),
    ("LUK", "Luke", "Lk"),
    ("JHN", "John", "Jn"),
    ("ACT", "Acts", "Acts"),
    ("ROM", "Romans", "Rom"),
    ("1CO", "1 Corinthians", "1 Cor"),
    ("2CO", "2 Corinthians", "2 Cor"),
    ("GAL", "Galatians", "Gal"),
    ("EPH", "Ephesians", "Eph"),
    ("PHP", "Philippians", "Phil"),
    ("COL", "Colossians", "Col"),
    ("1TH", "1 Thessalonians", "1 Thess, 1 Thes"),
    ("2TH", "2 Thessalonians", "2 Thess, 2 Thes"),
    ("1TI", "1 Timothy", "1 Tim, 1 Tm"),
    ("2TI", "2 Timothy", "2 Tim, 2 Tm"),
    ("TIT", "Titus", "Ti"),
    ("PHM", "Philemon", "Phlm"),
    ("HEB", "Hebrews", "Heb"),
    ("JAS", "James", "Jas"),
    ("1PE", "1 Peter", "1 Pet, 1 Pt"),
    ("2PE", "2 Peter", "2 Pet, 2 Pt"),
    ("1JN", "1 John", "1 Jn"),
    ("2JN", "2 John", "2 Jn"),
    ("3JN", "3 John", "3 Jn"),
    ("JUD", "Jude", "Jude"),
    ("REV", "Revelation", "Rev, Rv"),
]

NAMES = {code: name for code, name, _ in BOOKS}
CODES = {
    abbreviation: code
    for code, name, abbreviations in BOOKS
    for abbreviation in [name, *abbreviations.split(", ")]
}

_books = "|".join(map(re.escape, sorted(CODES, key=len, reverse=True)))
BIBLE_REF = re.compile(rf"(?P<cf>cf\. )?(?P<book>{_books}) (?P<spec>\d[\d:,;–\- ]*?)(?P<lxx> \(LXX\))?")
CCC_REF = re.compile(r"CCC (?P<numbers>\d[\d,–\- ]*)")
CCC_URL = "https://www.scborromeo.org/ccc/para/{}.htm"


class ReferenceError_(Exception):
    pass


@dataclass
class Passage:
    label: str      # as written, without any "cf. ", e.g. "1 Chr 15:28 (LXX)"
    book: str       # USFM code
    spec: str       # chapters and verses as written, e.g. "2:21–22; 3:1–6"
    spans: list     # [((chapter, verse), (chapter, verse))]; verse None = whole chapter
    lxx: bool       # the card means the Greek Septuagint
    cf: bool

    @property
    def heading(self):
        name = NAMES[self.book]
        if name == "Psalms" and len({c for span in self.spans for c, _ in span}) == 1:
            name = "Psalm"
        return f"{name} {self.spec}"

    def contains(self, chapter, verse):
        for (c1, v1), (c2, v2) in self.spans:
            if (c1, v1 or 0) <= (chapter, verse) <= (c2, v2 or 999):
                return True
        return False


@dataclass
class Catechism:
    numbers: list   # as written, e.g. ["411", "491–492"]

    def url(self, number):
        return CCC_URL.format(re.match(r"\d+", number)[0])


@dataclass
class Text:
    text: str


def parse(line):
    """Split a line of references, separated by " · ", into Passage, Catechism and Text parts."""
    parts = []
    for item in line.strip().split(" · "):
        if m := BIBLE_REF.fullmatch(item):
            label = item.removeprefix("cf. ")
            parts.append(Passage(label, CODES[m["book"]], m["spec"].strip(),
                                 spans(m["spec"], item), bool(m["lxx"]), bool(m["cf"])))
        elif m := CCC_REF.fullmatch(item):
            parts.append(Catechism([n.strip() for n in m["numbers"].split(",")]))
        else:
            parts.append(Text(item))
    return parts


def spans(spec, item):
    """ "2:21–22; 3:1–6" → [((2, 21), (2, 22)), ((3, 1), (3, 6))]

    After a comma a bare number is a verse in the same chapter; after a
    semicolon, or at the start, it is a whole chapter.
    """
    out = []
    chapter = None
    for sep, token in re.findall(r"(^|[,;])\s*([^,;]+)", spec.strip()):
        m = re.fullmatch(r"(?:(\d+):)?(\d+)(?:\s*[–-]\s*(?:(\d+):)?(\d+))?", token.strip())
        if not m:
            raise ReferenceError_(f"can't read the reference “{item}”")
        c1, v1, c2, v2 = (int(g) if g else None for g in m.groups())
        if c1 is None and (chapter is None or sep == ";"):
            out.append(((v1, None), (v2 or v1, None)))
            chapter = v2 or v1
            continue
        c1 = c1 or chapter
        start = (c1, v1)
        end = (c2 or c1, v2) if v2 else start
        out.append((start, end))
        chapter = end[0]
    return out


# ── Verse text ───────────────────────────────────────────────

# USFM paragraph markers that start a new block of text, and the CSS class
# each gets on the page. Anything else (headings, cross-references, psalm
# titles) is not part of the verse text and is skipped.
BLOCKS = {"m": "p", "p": "p", "pmo": "p", "pc": "p", "nb": "p",
          "q1": "q1", "q2": "q2", "qr": "q2", "li1": "li1", "li2": "li2"}
SKIP = {"s1", "s2", "r", "d", "qa", "ms", "mr", "sp", "h", "id", "toc1", "toc2", "mt1"}


@dataclass
class Segment:
    chapter: int
    verse: int
    block: int      # segments with the same block number share a line or paragraph
    kind: str       # CSS class of the block
    stanza: bool    # the block follows a blank line
    html: str


class Bible:
    name = "Berean Standard Bible"
    abbreviation = "BSB"

    def __init__(self, folder):
        self.folder = Path(folder)
        if not self.folder.is_dir():
            raise ReferenceError_(f"{self.folder} is missing; see README.md for where to get the BSB")
        self.files = {}
        for path in self.folder.glob("*.SFM"):
            first = path.read_text(encoding="utf-8-sig").split("\n", 1)[0]
            self.files[first.split()[1]] = path
        self._books = {}

    def has(self, book):
        return book in self.files

    def segments(self, book):
        if book not in self._books:
            self._books[book] = parse_usfm(self.files[book].read_text(encoding="utf-8-sig"))
        return self._books[book]

    def text(self, passage):
        """The passage's verses as plain text, for checking quotes against."""
        return html.unescape(" ".join(
            re.sub(r"<[^>]+>", "", s.html) for s in self.segments(passage.book)
            if s.verse and passage.contains(s.chapter, s.verse)))

    def render(self, passage):
        """The passage as HTML: blocks of text with verse numbers, and … where verses are skipped."""
        segments = self.segments(passage.book)
        order = {}
        for s in segments:
            order.setdefault((s.chapter, s.verse), len(order))
        for start, end in passage.spans:
            for c, v in (start, end):
                if v is not None and (c, v) not in order:
                    raise ReferenceError_(f"“{passage.label}”: the {self.abbreviation} has no {c}:{v}")
        chosen = [s for s in segments if s.verse and passage.contains(s.chapter, s.verse)]
        if not chosen:
            raise ReferenceError_(f"“{passage.label}”: no verses found")

        several_chapters = len({s.chapter for s in chosen}) > 1
        out = []
        block = last = None
        shown_chapter = None
        for s in chosen:
            here = (s.chapter, s.verse)
            new_verse = here != last
            if new_verse and last is not None and order[here] != order[last] + 1:
                out.append("</p>")
                out.append('<p class="gap">…</p>')
                block = None
            if s.block != block:
                if block is not None:
                    out.append("</p>")
                classes = s.kind + (" stanza" if s.stanza and block is not None else "")
                out.append(f'<p class="{classes}">')
                block = s.block
            else:
                out.append(" ")
            if new_verse:
                number = s.verse
                if several_chapters and s.chapter != shown_chapter:
                    number = f"{s.chapter}:{s.verse}"
                    shown_chapter = s.chapter
                out.append(f"<sup>{number}</sup>")
            out.append(s.html)
            last = here
        out.append("</p>")
        return "".join(out)


def parse_usfm(text):
    segments = []
    chapter = verse = 0
    block = 0
    kind = "p"
    stanza = False
    for line in text.splitlines():
        m = re.match(r"\\(\w+)\s?(.*)", line.strip())
        if not m:
            continue
        marker, rest = m[1], m[2]
        if marker == "c":
            chapter, verse = int(rest.split()[0]), 0
            block += 1
            continue
        if marker == "b":
            block += 1
            stanza = True
            continue
        if marker in SKIP:
            block += 1
            continue
        if marker in BLOCKS:
            block += 1
            kind = BLOCKS[marker]
        elif marker == "v":
            rest = line.strip()
        else:
            continue
        for k, part in enumerate(re.split(r"\\v (\d+)\s*", rest)):
            if k % 2:
                verse = int(part)
                continue
            cleaned = clean(part)
            if cleaned:
                segments.append(Segment(chapter, verse, block, kind, stanza, cleaned))
                stanza = False
    return segments


def clean(text):
    """USFM text → HTML, without footnotes or cross-references."""
    text = re.sub(r"\\f .*?\\f\*", "", text)
    text = re.sub(r"\\x .*?\\x\*", "", text)
    text = html.escape(text, quote=False)
    text = text.replace("\\it*", "</i>").replace("\\it ", "<i>")
    text = re.sub(r"\\[a-z0-9]+\*?\s?", "", text)
    return re.sub(r"\s+", " ", text).strip()
