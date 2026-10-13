"""Builds the profile README panels (assets/*.svg), light and dark.

GitHub renders SVGs as images: no scripts, no external fonts. So the brand
fonts are subset and embedded as base64, and the portrait is inlined.

    python3 -m venv .venv && .venv/bin/pip install fonttools brotli
    .venv/bin/python tools/build.py

Fonts (OFL) are fetched from google/fonts into tools/.cache on first run.
"""

import base64
import io
import pathlib
import urllib.request
from xml.sax.saxutils import escape

from fontTools.subset import Options, Subsetter
from fontTools.ttLib import TTFont
from fontTools.varLib.instancer import instantiateVariableFont

ROOT = pathlib.Path(__file__).resolve().parent.parent
TOOLS = ROOT / "tools"
CACHE = TOOLS / ".cache"
OUT = ROOT / "assets"

FONT_URLS = {
    "HankenGrotesk.ttf": "https://github.com/google/fonts/raw/main/ofl/hankengrotesk/HankenGrotesk%5Bwght%5D.ttf",
    "SpaceMono-Regular.ttf": "https://github.com/google/fonts/raw/main/ofl/spacemono/SpaceMono-Regular.ttf",
}

# Same tokens as nickeykhem.com. Light amber is deepened to hold 3:1 on paper.
THEMES = {
    "dark": dict(bg="#17160f", band="#0f0f0a", ink="#eceee4", soft="#c9cbbf",
                 mut="#8f9183", line="#2c2b22", acc="#e8a23c", other="#4a4839"),
    "light": dict(bg="#f4f1ea", band="#ebe7dd", ink="#1b1a13", soft="#45433a",
                  mut="#6b685c", line="#dcd7ca", acc="#b26c0e", other="#c9c3b3"),
}

TEXT = "".join(chr(c) for c in range(32, 127)) + "’·→"
EASE = "cubic-bezier(.16,1,.3,1)"


# ---------- fonts ----------

def fetch_fonts():
    CACHE.mkdir(parents=True, exist_ok=True)
    for name, url in FONT_URLS.items():
        if not (CACHE / name).exists():
            urllib.request.urlretrieve(url, CACHE / name)


class Face:
    """A subset, embedded font plus enough metrics to lay text out."""

    def __init__(self, family, path, wght=None):
        font = TTFont(path)
        if wght is not None:
            font = instantiateVariableFont(font, {"wght": wght})
        opts = Options()
        opts.flavor = "woff2"
        opts.layout_features = ["kern"]
        sub = Subsetter(opts)
        sub.populate(text=TEXT)
        sub.subset(font)
        buf = io.BytesIO()
        font.flavor = "woff2"
        font.save(buf)
        self.family = family
        self.b64 = base64.b64encode(buf.getvalue()).decode()
        self.upm = font["head"].unitsPerEm
        self.cmap = font.getBestCmap()
        self.hmtx = font["hmtx"]

    def width(self, s, size, tracking=0.0):
        adv = sum(self.hmtx[self.cmap[ord(ch)]][0] for ch in s)
        return adv * size / self.upm + tracking * size * len(s)

    def face_css(self):
        return (f"@font-face{{font-family:'{self.family}';"
                f"src:url(data:font/woff2;base64,{self.b64}) format('woff2');}}")


def wrap(face, text, size, max_w):
    lines, cur = [], ""
    for word in text.split():
        trial = f"{cur} {word}".strip()
        if cur and face.width(trial, size) > max_w:
            lines.append(cur)
            cur = word
        else:
            cur = trial
    return lines + [cur]


# ---------- svg helpers ----------

def svg_doc(w, h, title, style, body, t):
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" '
        f'width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img" aria-label="{escape(title)}">'
        f"<title>{escape(title)}</title>"
        f"<style>{style}</style>"
        f'<defs><clipPath id="frame"><rect width="{w}" height="{h}" rx="16"/></clipPath></defs>'
        f'<g clip-path="url(#frame)"><rect width="{w}" height="{h}" fill="{t["bg"]}"/>{body}</g>'
        f'<rect x=".5" y=".5" width="{w-1}" height="{h-1}" rx="15.5" fill="none" stroke="{t["line"]}"/>'
        f"</svg>"
    )


def text(x, y, s, cls, fill, anchor="start", extra=""):
    return (f'<text x="{x:.1f}" y="{y:.1f}" class="{cls}" fill="{fill}" '
            f'text-anchor="{anchor}"{extra}>{escape(s)}</text>')


def tri(x, y, size, fill):
    """Small up-triangle, the ticker's 'rising' mark."""
    return (f'<path d="M{x:.1f} {y:.1f}l{size/2:.1f} {-size*0.86:.1f}l{size/2:.1f} {size*0.86:.1f}z" '
            f'fill="{fill}"/>')


# ---------- panels ----------

TICKER = [
    ("BUILDING NOW: AI AGENTS", False),
    ("COLLECTIVE GLOBAL: 110+ VENTURES", True),
    ("10 MARKETS", False),
    ("BSD EDUCATION: 500K YOUNG PEOPLE, 58 COUNTRIES", True),
    ("KEYNOTE: IN THE AI AGE, THE GENERALIST WINS", False),
    ("STACK: AGNOSTIC", False),
    ("IN TECH SINCE 2006", True),
    ("OPEN TO TALKS, PANELS AND WORKSHOPS", False),
]


def hero(t, mode, F, photo_b64):
    W, H, TAPE = 1000, 440, 42
    PX = 628  # photo starts here
    body = []

    # portrait, bleeding off the right edge
    body.append(
        f'<image x="{PX}" y="0" width="{W-PX}" height="{H-TAPE}" preserveAspectRatio="xMidYMin slice" '
        f'href="data:image/jpeg;base64,{photo_b64}" xlink:href="data:image/jpeg;base64,{photo_b64}"/>'
    )
    if mode == "dark":
        # the studio wall is already near-black; feather it into the canvas
        body.append(
            '<defs><linearGradient id="feather" x1="0" x2="1">'
            f'<stop offset="0" stop-color="{t["bg"]}"/><stop offset=".42" stop-color="{t["bg"]}" stop-opacity="0"/>'
            "</linearGradient></defs>"
            f'<rect x="{PX}" y="0" width="{W-PX}" height="{H-TAPE}" fill="url(#feather)"/>'
        )

    x = 52
    body.append(text(x, 80, "NICKEY KHEMCHANDANI", "mono lbl", t["mut"]))

    size, lead = 56, 56
    lines = [("I build businesses,", None), ("and the people", None), ("who ", "build them.")]
    for i, (a, b) in enumerate(lines):
        y = 150 + i * lead
        body.append(f'<text x="{x}" y="{y}" class="disp rise" style="animation-delay:{60 + i*70}ms" '
                    f'fill="{t["ink"]}">{escape(a)}'
                    + (f'<tspan fill="{t["acc"]}">{escape(b)}</tspan>' if b else "")
                    + "</text>")
        assert F["disp"].width(a + (b or ""), size) < PX - x - 30, a

    sub = ("Technologist, founder-builder and speaker. I sit beside founders "
           "and build with them, then share what I learn.")
    for i, ln in enumerate(wrap(F["body"], sub, 19, 520)):
        body.append(text(x, 302 + i * 28, ln, "body rise", t["soft"],
                         extra=f' style="animation-delay:{300 + i*40}ms"'))

    roles = [("Founder", "Collective Global"), ("Co-founder & CTO", "BSD Education")]
    rx = x
    for role, org in roles:
        s1 = f"{role}, "
        body.append(f'<text x="{rx}" y="372" class="mono role" fill="{t["mut"]}">{escape(s1)}'
                    f'<tspan fill="{t["ink"]}">{escape(org)}</tspan></text>')
        rx += F["mono"].width(s1 + org, 13, 0.02) + 28

    # ticker tape: one group, drawn twice, slid by exactly its own length
    ty = H - TAPE
    body.append(f'<rect x="0" y="{ty}" width="{W}" height="{TAPE}" fill="{t["band"]}"/>')
    body.append(f'<line x1="0" x2="{W}" y1="{ty+.5}" y2="{ty+.5}" stroke="{t["line"]}"/>')
    parts, cx = [], 0.0
    for label, up in TICKER:
        parts.append(text(cx, ty + 26, label, "mono tape", t["soft"]))
        cx += F["mono"].width(label, 13, 0.06)
        if up:
            parts.append(tri(cx + 10, ty + 25, 9, t["acc"]))
            cx += 20
        cx += 44
    group = "".join(parts)
    L = cx
    dur = L / 38
    body.append(f'<g class="tape-run" style="animation-duration:{dur:.1f}s">'
                f'<g transform="translate(24 0)">{group}</g><g transform="translate({24+L:.1f} 0)">{group}</g></g>')

    style = (
        F["disp"].face_css() + F["body"].face_css() + F["mono"].face_css()
        + f".disp{{font-family:'{F['disp'].family}';font-size:{size}px;letter-spacing:-.035em}}"
        + f".body{{font-family:'{F['body'].family}';font-size:19px}}"
        + f".mono{{font-family:'{F['mono'].family}'}}"
        + ".lbl{font-size:13px;letter-spacing:.16em}.role{font-size:13px;letter-spacing:.02em}"
        + ".tape{font-size:13px;letter-spacing:.06em}"
        + f".tape-run{{animation:tape linear infinite}}@keyframes tape{{to{{transform:translateX(-{L:.1f}px)}}}}"
        + f".rise{{animation:rise .7s {EASE} both}}"
        + "@keyframes rise{from{opacity:0;transform:translateY(10px)}to{opacity:1;transform:none}}"
        + "@media (prefers-reduced-motion:reduce){.tape-run,.rise{animation:none}}"
    )
    title = "Nickey Khemchandani. I build businesses, and the people who build them."
    return svg_doc(W, H, title, style, "".join(body), t)


def numbers(t, mode, F):
    W, H = 1000, 320
    body = []
    x = 52
    body.append(text(x - 4, 166, "500,000", "huge", t["acc"]))
    cap = "young people reached by BSD Education, the company I co-founded, across 58 countries."
    for i, ln in enumerate(wrap(F["body"], cap, 19, 430)):
        body.append(text(x, 214 + i * 28, ln, "body", t["soft"]))

    vx = 566
    body.append(f'<line x1="{vx+.5}" x2="{vx+.5}" y1="48" y2="{H-48}" stroke="{t["line"]}"/>')
    rows = [
        ("110+", "ventures Collective Global has built with, across 10 markets."),
        ("20 yrs", "in tech. It started with a conversation of help that turned into my first job."),
    ]
    rx = vx + 44
    for i, (n, cap) in enumerate(rows):
        top = 46 + i * 124
        if i:
            body.append(f'<line x1="{rx}" x2="{W-52}" y1="{top-14.5}" y2="{top-14.5}" stroke="{t["line"]}"/>')
        body.append(text(rx - 2, top + 50, n, "mid", t["ink"]))
        for j, ln in enumerate(wrap(F["body"], cap, 16, W - 52 - rx)):
            body.append(text(rx, top + 78 + j * 22, ln, "small", t["soft"]))

    style = (
        F["disp"].face_css() + F["body"].face_css()
        + f".huge{{font-family:'{F['disp'].family}';font-size:124px;letter-spacing:-.045em}}"
        + f".mid{{font-family:'{F['disp'].family}';font-size:50px;letter-spacing:-.04em}}"
        + f".body{{font-family:'{F['body'].family}';font-size:19px}}"
        + f".small{{font-family:'{F['body'].family}';font-size:16px}}"
    )
    title = ("500,000 young people reached by BSD Education across 58 countries. "
             "110+ ventures with Collective Global across 10 markets. 20 years in tech.")
    return svg_doc(W, H, title, style, "".join(body), t)


SECTORS = [
    ("FinTech", 14), ("HealthTech", 10), ("AI", 9), ("Cleantech", 8), ("Marketplaces", 8),
    ("SaaS", 8), ("Supply chain", 8), ("PropTech", 7), ("HR Tech", 6),
]
OTHER = ("13 more sectors", 32)


def ventures(t, mode, F):
    W = 1000
    x0, lab_x = 192, 174
    cell, gap, row_h, top = 16, 4, 30, 132
    rows = SECTORS + [OTHER]
    H = top + len(rows) * row_h + 30
    assert sum(n for _, n in rows) == 110

    body = [
        text(52, 66, "110 ventures, by sector", "h", t["ink"]),
        text(52, 96, "Each square is one venture the Collective Global team has built with.",
             "body", t["soft"]),
    ]
    for r, (name, n) in enumerate(rows):
        y = top + r * row_h
        is_other = (name, n) == OTHER
        if is_other:
            body.append(f'<line x1="52" x2="{W-52}" y1="{y-8.5}" y2="{y-8.5}" stroke="{t["line"]}"/>')
        body.append(text(lab_x, y + 13, name, "mono lab", t["mut"] if is_other else t["soft"], "end"))
        fill = t["other"] if is_other else t["acc"]
        cells = "".join(
            f'<rect x="{x0 + i*(cell+gap)}" y="{y}" width="{cell}" height="{cell}" rx="3" fill="{fill}"/>'
            for i in range(n)
        )
        body.append(f'<g class="row" style="animation-delay:{r*70}ms">{cells}</g>')
        body.append(text(x0 + n * (cell + gap) + 8, y + 14, str(n), "val", t["ink"]))

    style = (
        F["disp"].face_css() + F["body"].face_css() + F["mono"].face_css()
        + f".h{{font-family:'{F['disp'].family}';font-size:28px;letter-spacing:-.02em}}"
        + f".body{{font-family:'{F['body'].family}';font-size:17px}}"
        + f".val{{font-family:'{F['body'].family}';font-size:16px}}"
        + f".mono{{font-family:'{F['mono'].family}'}}.lab{{font-size:13px;letter-spacing:.02em}}"
        + f".row{{animation:fill .6s {EASE} both}}"
        + "@keyframes fill{from{opacity:0;transform:translateX(-8px)}to{opacity:1;transform:none}}"
        + "@media (prefers-reduced-motion:reduce){.row{animation:none}}"
    )
    title = "110 Collective Global ventures by sector: " + ", ".join(f"{a} {b}" for a, b in rows) + "."
    return svg_doc(W, H, title, style, "".join(body), t)


def main():
    fetch_fonts()
    hk = CACHE / "HankenGrotesk.ttf"
    F = {
        "disp": Face("HG800", hk, 800),
        "body": Face("HG500", hk, 500),
        "mono": Face("SpaceMono", CACHE / "SpaceMono-Regular.ttf"),
    }
    photo = base64.b64encode((TOOLS / "portrait.jpg").read_bytes()).decode()
    OUT.mkdir(exist_ok=True)
    for mode, t in THEMES.items():
        for name, svg in [
            ("hero", hero(t, mode, F, photo)),
            ("numbers", numbers(t, mode, F)),
            ("ventures", ventures(t, mode, F)),
        ]:
            path = OUT / f"{name}-{mode}.svg"
            path.write_text(svg, encoding="utf-8")
            print(f"{path.relative_to(ROOT)}  {len(svg)//1024} KB")


if __name__ == "__main__":
    main()
