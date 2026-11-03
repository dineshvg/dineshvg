#!/usr/bin/env python3
"""Generates the animated profile SVGs into ../svg.

Pure SVG + CSS + SMIL (GitHub strips JS). Everything is inlined: fonts and
images are base64, nothing is fetched at render time.

Inputs (all next to this file):
  config.json        - personal content (name, roles, projects, ...)
  stats.json         - optional; written daily by fetch_stats.py in CI
  icons.json         - Simple Icons paths + brand colours (CC0)
  fonts/*.woff2      - subsetted Space Grotesk / JetBrains Mono (OFL)
  ../assets/*.jpg    - portrait crops
"""
import base64
import html
import json
import math
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
OUT = ROOT / "svg"

CFG = json.loads((HERE / "config.json").read_text())
ICONS = json.loads((HERE / "icons.json").read_text())
import os
STATS_FILE = Path(os.environ.get("PROFILE_STATS", HERE / "stats.json"))
STATS = json.loads(STATS_FILE.read_text()) if STATS_FILE.exists() else None

# ---- design tokens -------------------------------------------------------
BG = "#0d0e16"
CARD = "#11121c"
CYAN = "#22d3ee"
VIOLET = "#a78bfa"
PINK = "#f472b6"
TEXT = "#e6e8f2"
MUTED = "#8b90a8"
DIM = "#4b4f66"
GREEN = "#34d399"
RED = "#ef4444"


def esc(s):
    return html.escape(str(s), quote=True)


def b64(path):
    return base64.b64encode(Path(path).read_bytes()).decode()


def font_face(*which):
    files = {
        "display500": ("Display", 500, "space-grotesk-latin-500-normal.woff2"),
        "display700": ("Display", 700, "space-grotesk-latin-700-normal.woff2"),
        "mono400": ("Mono", 400, "jetbrains-mono-latin-400-normal.woff2"),
        "mono700": ("Mono", 700, "jetbrains-mono-latin-700-normal.woff2"),
    }
    out = []
    for w in which:
        fam, weight, f = files[w]
        out.append(
            f"@font-face{{font-family:'{fam}';font-weight:{weight};"
            f"src:url(data:font/woff2;base64,{b64(HERE / 'fonts' / f)}) format('woff2');}}"
        )
    return "".join(out)


BASE_CSS = f"""
.d{{font-family:'Display',ui-sans-serif,system-ui,sans-serif;}}
.m{{font-family:'Mono',ui-monospace,SFMono-Regular,Menlo,monospace;}}
.t{{fill:{TEXT};}} .mu{{fill:{MUTED};}} .dim{{fill:{DIM};}}
.cy{{fill:{CYAN};}} .vi{{fill:{VIOLET};}} .pk{{fill:{PINK};}}
.fu{{animation:fu .7s cubic-bezier(.2,.7,.2,1) both;}}
@keyframes fu{{from{{opacity:0;transform:translateY(8px);}}}}
.fi{{animation:fi .8s ease both;}}
@keyframes fi{{from{{opacity:0;}}}}
.draw{{stroke-dasharray:1;animation:draw 1s cubic-bezier(.6,.1,.2,1) both;}}
@keyframes draw{{from{{stroke-dashoffset:1;}}}}
@media (prefers-reduced-motion:reduce){{*{{animation:none!important;}}}}
"""


def common_defs(p):
    """Gradients/patterns shared by every card. `p` namespaces the ids."""
    return f"""
<linearGradient id="{p}hair" x1="0" y1="0" x2="1" y2="1">
  <stop offset="0" stop-color="{CYAN}" stop-opacity=".55"/>
  <stop offset=".5" stop-color="{VIOLET}" stop-opacity=".25"/>
  <stop offset="1" stop-color="{PINK}" stop-opacity=".55"/>
</linearGradient>
<linearGradient id="{p}aurora" x1="0" y1="0" x2="1" y2="0">
  <stop offset="0" stop-color="{CYAN}"/>
  <stop offset=".5" stop-color="{VIOLET}"/>
  <stop offset="1" stop-color="{PINK}"/>
</linearGradient>
<radialGradient id="{p}glow" cx=".15" cy="0" r=".9">
  <stop offset="0" stop-color="{VIOLET}" stop-opacity=".13"/>
  <stop offset="1" stop-color="{VIOLET}" stop-opacity="0"/>
</radialGradient>
<pattern id="{p}dots" width="16" height="16" patternUnits="userSpaceOnUse">
  <circle cx="1" cy="1" r=".8" fill="#ffffff" fill-opacity=".05"/>
</pattern>"""


def card(p, x, y, w, h, r=18):
    return f"""
<rect x="{x+.5}" y="{y+.5}" width="{w-1}" height="{h-1}" rx="{r}" fill="{CARD}"/>
<rect x="{x+.5}" y="{y+.5}" width="{w-1}" height="{h-1}" rx="{r}" fill="url(#{p}dots)"/>
<rect x="{x+.5}" y="{y+.5}" width="{w-1}" height="{h-1}" rx="{r}" fill="url(#{p}glow)"/>
<rect x="{x+.5}" y="{y+.5}" width="{w-1}" height="{h-1}" rx="{r}" fill="none" stroke="url(#{p}hair)" stroke-width="1"/>"""


def svg_doc(w, h, title, css, body, fonts=("display500", "display700", "mono400")):
    return f"""<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" viewBox="0 0 {w} {h}" width="{w}" height="{h}" role="img" aria-label="{esc(title)}">
<title>{esc(title)}</title>
<style>{font_face(*fonts)}{BASE_CSS}{css}</style>
{body}
</svg>
"""


def icon(slug, x, y, size, color=None):
    """Simple Icons path (24x24 viewBox) placed with its top-left at x,y."""
    ic = ICONS[slug]
    c = color or f"#{ic['hex']}"
    # very dark brand colours disappear on the dark card -> use text colour
    if c.lower() in ("#000000", "#181717", "#02303a"):
        c = TEXT
    s = size / 24
    return f'<path transform="translate({x:.2f} {y:.2f}) scale({s:.4f})" d="{ic["d"]}" fill="{c}"/>'


def delay(sec):
    return f'style="animation-delay:{sec:.2f}s"'


# =========================================================================
# hero.svg
# =========================================================================
def hero():
    p = "h-"
    W, H = 840, 360
    c = CFG
    typed = c["greeting"]
    cw = 9.6  # JetBrains Mono advance at 16px
    n = len(typed)
    tdur = 0.06 * n
    widths = ";".join(f"{i*cw:.1f}" for i in range(n + 1))
    cursor_x = ";".join(f"{40 + i*cw + 2:.1f}" for i in range(n + 1))

    roles = c["roles"]
    period = 2.6
    total = period * len(roles)
    role_css = []
    role_svg = []
    for i, r in enumerate(roles):
        a = i * period / total * 100
        b = (i + 1) * period / total * 100
        role_css.append(
            f"@keyframes {p}r{i}{{0%{{opacity:0;transform:translateY(8px)}}"
            f"{a:.2f}%{{opacity:0;transform:translateY(8px)}}{a+2.5:.2f}%{{opacity:1;transform:none}}"
            f"{b-2.5:.2f}%{{opacity:1;transform:none}}{b:.2f}%{{opacity:0;transform:translateY(-8px)}}"
            f"100%{{opacity:0;transform:translateY(-8px)}}}}"
            f".{p}r{i}{{opacity:{1 if i == 0 else 0};animation:{p}r{i} {total}s linear 1.6s infinite both;}}"
        )
        role_svg.append(
            f'<text class="m {p}r{i}" x="58" y="207" font-size="15" fill="{TEXT}">{esc(r)}</text>'
        )

    pitch = c["pitch"]
    meta = c["meta"]

    # photo frame
    fx, fy, fw, fh = 556, 30, 250, 300
    img = b64(ROOT / "assets" / "hero.jpg")
    bl = 22  # bracket length
    o = 9  # bracket offset outside the photo
    brackets = [
        f"M{fx-o} {fy-o+bl} V{fy-o} H{fx-o+bl}",
        f"M{fx+fw+o-bl} {fy-o} H{fx+fw+o} V{fy-o+bl}",
        f"M{fx+fw+o} {fy+fh+o-bl} V{fy+fh+o} H{fx+fw+o-bl}",
        f"M{fx-o+bl} {fy+fh+o} H{fx-o} V{fy+fh+o-bl}",
    ]

    css = f"""
{''.join(role_css)}
.{p}kb{{transform-box:fill-box;transform-origin:50% 40%;animation:{p}kb 9s ease-in-out infinite alternate;}}
@keyframes {p}kb{{from{{transform:scale(1)}}to{{transform:scale(1.07)}}}}
.{p}sweep{{animation:{p}sweep 6s ease-in-out 1.5s infinite both;}}
@keyframes {p}sweep{{0%{{transform:translateX(-160px)}}35%,100%{{transform:translateX(420px)}}}}
.{p}blink{{animation:{p}blink 1.2s steps(1) infinite;}}
@keyframes {p}blink{{50%{{opacity:0}}}}
.{p}pulse{{transform-box:fill-box;transform-origin:center;animation:{p}pulse 2s ease-out infinite;}}
@keyframes {p}pulse{{from{{transform:scale(1);opacity:.7}}to{{transform:scale(3);opacity:0}}}}
.{p}grad{{animation:{p}grad 6s ease-in-out infinite alternate;}}
@keyframes {p}grad{{to{{transform:translateX(-300px)}}}}
.{p}cur{{animation:{p}blink 1s steps(1) {tdur+.3:.2f}s infinite;}}
"""

    meta_icons = {
        "pin": f'<path d="M6 0a6 6 0 0 0-6 6c0 4.5 6 10 6 10s6-5.5 6-10a6 6 0 0 0-6-6z" fill="none" stroke="{CYAN}" stroke-width="1.6"/><circle cx="6" cy="6" r="2" fill="{CYAN}"/>',
        "work": f'<rect x="0" y="4" width="14" height="11" rx="2" fill="none" stroke="{VIOLET}" stroke-width="1.6"/><path d="M4.5 4V2h5v2" fill="none" stroke="{VIOLET}" stroke-width="1.6"/>',
        "cert": f'<circle cx="7" cy="6" r="5" fill="none" stroke="{PINK}" stroke-width="1.6"/><path d="M4 10l-1.5 6 4.5-2 4.5 2L10 10" fill="none" stroke="{PINK}" stroke-width="1.6" stroke-linejoin="round"/>',
    }
    meta_svg = []
    mx = 40
    for i, m in enumerate(meta):
        meta_svg.append(
            f'<g class="fu" {delay(1.9 + i*.12)}><g transform="translate({mx} 298)">{meta_icons[m["icon"]]}</g>'
            f'<text class="d mu" x="{mx+22}" y="311" font-size="14" font-weight="500">{esc(m["text"])}</text></g>'
        )
        mx += 22 + len(m["text"]) * 7.6 + 26

    body = f"""
<defs>{common_defs(p)}
  <linearGradient id="{p}name" gradientUnits="userSpaceOnUse" x1="40" y1="0" x2="520" y2="0" spreadMethod="reflect">
    <stop offset="0" stop-color="{CYAN}"/><stop offset=".5" stop-color="{VIOLET}"/><stop offset="1" stop-color="{PINK}"/>
    <animateTransform attributeName="gradientTransform" type="translate" values="0 0;-480 0;0 0" dur="10s" begin="0s" repeatCount="indefinite"/>
  </linearGradient>
  <clipPath id="{p}type"><rect x="40" y="82" height="26" width="{n*cw:.1f}">
    <animate attributeName="width" values="{widths}" dur="{tdur:.2f}s" begin="0s" calcMode="discrete" fill="freeze"/>
  </rect></clipPath>
  <clipPath id="{p}rise"><rect x="30" y="112" width="520" height="66">
    <animate attributeName="y" values="178;178;112" keyTimes="0;.45;1" dur="1.5s" begin="0s" fill="freeze" calcMode="spline" keySplines="0 0 1 1;.2 .8 .2 1"/>
  </rect></clipPath>
  <clipPath id="{p}photo"><rect x="{fx}" y="{fy}" width="{fw}" height="{fh}" rx="14"/></clipPath>
  <radialGradient id="{p}fade" cx=".5" cy=".42" r=".72">
    <stop offset=".62" stop-color="#fff"/><stop offset="1" stop-color="#000"/>
  </radialGradient>
  <mask id="{p}melt" maskUnits="userSpaceOnUse" x="{fx}" y="{fy}" width="{fw}" height="{fh}">
    <rect x="{fx}" y="{fy}" width="{fw}" height="{fh}" fill="url(#{p}fade)"/>
  </mask>
  <linearGradient id="{p}light" x1="0" y1="0" x2="1" y2="0">
    <stop offset="0" stop-color="#fff" stop-opacity="0"/><stop offset=".5" stop-color="#fff" stop-opacity=".16"/>
    <stop offset="1" stop-color="#fff" stop-opacity="0"/>
  </linearGradient>
  <pattern id="{p}scan" width="4" height="3" patternUnits="userSpaceOnUse">
    <rect width="4" height="1" fill="#000" fill-opacity=".22"/>
  </pattern>
</defs>
{card(p, 0, 0, W, H)}

<!-- pill -->
<g class="fu" {delay(.1)}>
  <rect x="40.5" y="34.5" width="158" height="27" rx="13.5" fill="{GREEN}" fill-opacity=".07" stroke="{GREEN}" stroke-opacity=".45"/>
  <circle class="{p}pulse" cx="56" cy="48" r="3.5" fill="{GREEN}"/>
  <circle cx="56" cy="48" r="3.5" fill="{GREEN}"/>
  <text class="m" x="67" y="52.5" font-size="12" fill="{GREEN}">{esc(c["pill"])}</text>
</g>

<!-- typed greeting -->
<g clip-path="url(#{p}type)"><text class="m cy" x="40" y="101" font-size="16">{esc(typed)}</text></g>
<rect class="{p}cur" x="{40 + n*cw + 2:.1f}" y="86" width="8" height="18" fill="{CYAN}" fill-opacity=".85">
  <animate attributeName="x" values="{cursor_x}" dur="{tdur:.2f}s" begin="0s" calcMode="discrete" fill="freeze"/>
</rect>

<!-- name -->
<g clip-path="url(#{p}rise)">
  <text class="d" x="38" y="160" font-size="44" font-weight="700" fill="url(#{p}name)" letter-spacing="-.5">{esc(c["name"])}</text>
</g>

<!-- roles -->
<g class="fi" {delay(1.4)}><text class="m" x="40" y="207" font-size="15" fill="{PINK}">▸</text></g>
{''.join(role_svg)}

<!-- pitch -->
<g class="fu" {delay(1.7)}>
  <text class="d t" x="40" y="246" font-size="15.5" font-weight="500">{esc(pitch[0])}</text>
  <text class="d t" x="40" y="268" font-size="15.5" font-weight="500" fill-opacity=".85">{esc(pitch[1])}</text>
</g>
{''.join(meta_svg)}

<!-- photo -->
<g clip-path="url(#{p}photo)">
  <rect x="{fx}" y="{fy}" width="{fw}" height="{fh}" fill="{BG}"/>
  <g mask="url(#{p}melt)">
    <image class="{p}kb" x="{fx}" y="{fy}" width="{fw}" height="{fh}" preserveAspectRatio="xMidYMid slice" href="data:image/jpeg;base64,{img}" xlink:href="data:image/jpeg;base64,{img}"/>
  </g>
  <rect x="{fx}" y="{fy}" width="{fw}" height="{fh}" fill="url(#{p}scan)"/>
  <g class="{p}sweep"><rect x="{fx-40}" y="{fy-40}" width="70" height="{fh+80}" fill="url(#{p}light)" transform="rotate(14 {fx} {fy})"/></g>
</g>
<rect x="{fx+.5}" y="{fy+.5}" width="{fw-1}" height="{fh-1}" rx="14" fill="none" stroke="#fff" stroke-opacity=".06"/>
{''.join(f'<path class="draw" {delay(.2 + i*.12)} pathLength="1" d="{d}" fill="none" stroke="{CYAN}" stroke-width="2.2" stroke-linecap="round"/>' for i, d in enumerate(brackets))}
<g class="fi" {delay(.9)}>
  <circle class="{p}blink" cx="{fx+18}" cy="{fy+20}" r="4.5" fill="{RED}"/>
  <text class="m" x="{fx+28}" y="{fy+24}" font-size="11" font-weight="700" fill="#fff" fill-opacity=".9">REC</text>
  <text class="m" x="{fx+fw-14}" y="{fy+24}" font-size="10" fill="#fff" fill-opacity=".7" text-anchor="end">ISO 800 · f/1.8</text>
  <text class="m" x="{fx+14}" y="{fy+fh-14}" font-size="10" fill="#fff" fill-opacity=".75">{esc(c["filename"])}</text>
  <text class="m" x="{fx+fw-14}" y="{fy+fh-14}" font-size="10" fill="#fff" fill-opacity=".75" text-anchor="end">00:02:04:12</text>
  <path d="M{fx+fw/2-7} {fy+fh/2-30}h14M{fx+fw/2} {fy+fh/2-37}v14" stroke="#fff" stroke-opacity=".25" stroke-width="1"/>
</g>
"""
    return svg_doc(W, H, f"{c['name']} — {roles[0]}", css, body, fonts=("display500", "display700", "mono400", "mono700"))


# =========================================================================
# about-life.svg
# =========================================================================
def about_life():
    p = "a-"
    W, H = 840, 330
    LW = 508
    RX = LW + 14
    RW = W - RX
    c = CFG

    rows = []
    for i, b in enumerate(c["build"]):
        y = 112 + i * 66
        rows.append(f"""
<g class="fu" {delay(.5 + i*.18)}>
  <rect x="34.5" y="{y+.5}" width="47" height="47" rx="12" fill="#ffffff" fill-opacity=".04" stroke="url(#{p}hair)"/>
  {icon(b["icon"], 46, y+12, 24)}
  <text class="d t" x="98" y="{y+20}" font-size="15.5" font-weight="700">{esc(b["title"])}</text>
  <text class="d mu" x="98" y="{y+40}" font-size="13" font-weight="500">{esc(b["text"])}</text>
</g>""")

    slides = c["life"]
    n = len(slides)
    per = 4.0
    total = per * n
    seg_w = (RW - 48 - (n - 1) * 6) / n
    seg_css, seg_svg, sl_css, sl_svg = [], [], [], []
    for i, s in enumerate(slides):
        a = i / n * 100
        b = (i + 1) / n * 100
        seg_css.append(
            f"@keyframes {p}s{i}{{0%,{a:.2f}%{{transform:scaleX(0)}}{b:.2f}%,99.5%{{transform:scaleX(1)}}100%{{transform:scaleX(0)}}}}"
            f".{p}s{i}{{transform-box:fill-box;transform-origin:left;transform:scaleX({1 if i == 0 else 0});"
            f"animation:{p}s{i} {total}s linear infinite;}}"
        )
        sx = RX + 24 + i * (seg_w + 6)
        seg_svg.append(
            f'<rect x="{sx:.1f}" y="22" width="{seg_w:.1f}" height="3" rx="1.5" fill="#fff" fill-opacity=".12"/>'
            f'<rect class="{p}s{i}" x="{sx:.1f}" y="22" width="{seg_w:.1f}" height="3" rx="1.5" fill="#fff" fill-opacity=".85"/>'
        )
        fade = 2.2
        sl_css.append(
            f"@keyframes {p}l{i}{{0%{{opacity:{1 if i == 0 else 0}}}"
            + (f"{a:.2f}%{{opacity:0}}{a+fade:.2f}%{{opacity:1}}" if i else f"0%{{opacity:1}}")
            + f"{b-fade:.2f}%{{opacity:1}}{b:.2f}%{{opacity:0}}"
            + (f"{100-fade:.2f}%{{opacity:0}}100%{{opacity:1}}" if i == 0 else "100%{opacity:0}")
            + f"}}.{p}l{i}{{opacity:{1 if i == 0 else 0};animation:{p}l{i} {total}s linear infinite;}}"
        )
        sl_svg.append(f'<g class="{p}l{i}">{life_art(s["art"], RX + RW/2, 128)}'
                      f'<text class="d t" x="{RX + RW/2}" y="214" font-size="17" font-weight="700" text-anchor="middle">{esc(s["title"])}</text>'
                      f'<text class="d mu" x="{RX + RW/2}" y="235" font-size="12.5" font-weight="500" text-anchor="middle">{esc(s["caption"])}</text></g>')

    rings = c["rings"]
    ring_svg, ring_css = [], []
    cols = [CYAN, PINK, VIOLET]
    rcx, rcy = RX + 58, 284
    for i, r in enumerate(rings):
        rad = 27 - i * 8
        circ = 2 * math.pi * rad
        target = circ * (1 - r["value"])
        ring_css.append(
            f"@keyframes {p}g{i}{{0%{{stroke-dashoffset:{circ:.1f}}}12%,94%{{stroke-dashoffset:{target:.1f}}}100%{{stroke-dashoffset:{circ:.1f}}}}}"
            f".{p}g{i}{{stroke-dasharray:{circ:.1f};stroke-dashoffset:{target:.1f};animation:{p}g{i} {total}s cubic-bezier(.3,.6,.2,1) infinite;}}"
        )
        ring_svg.append(
            f'<circle cx="{rcx}" cy="{rcy}" r="{rad}" fill="none" stroke="{cols[i]}" stroke-opacity=".15" stroke-width="5.5"/>'
            f'<circle class="{p}g{i}" cx="{rcx}" cy="{rcy}" r="{rad}" fill="none" stroke="{cols[i]}" stroke-width="5.5" stroke-linecap="round" transform="rotate(-90 {rcx} {rcy})"/>'
            f'<circle cx="{RX+112}" cy="{262 + i*21}" r="3.5" fill="{cols[i]}"/>'
            f'<text class="d t" x="{RX+122}" y="{266.5 + i*21}" font-size="12.5" font-weight="500">{esc(r["label"])}</text>'
        )

    css = f"""
{''.join(seg_css)}{''.join(sl_css)}{''.join(ring_css)}
.{p}cur{{animation:{p}blink 1.1s steps(1) infinite;}}
@keyframes {p}blink{{50%{{opacity:0}}}}
.{p}beat{{transform-box:fill-box;transform-origin:center;animation:{p}beat 1.4s ease-in-out infinite;}}
@keyframes {p}beat{{0%,100%{{transform:scale(1)}}15%{{transform:scale(1.12)}}30%{{transform:scale(1)}}45%{{transform:scale(1.08)}}}}
.{p}tw{{animation:{p}tw 2.4s ease-in-out infinite;}}
@keyframes {p}tw{{50%{{opacity:.15}}}}
.{p}node{{animation:{p}node 2s ease-in-out infinite;}}
@keyframes {p}node{{50%{{fill:{PINK}}}}}
"""
    url = c["browser_url"]
    body = f"""
<defs>{common_defs(p)}</defs>
{card(p, 0, 0, LW, H)}
<!-- browser chrome -->
<g class="fi">
  <circle cx="30" cy="30" r="5" fill="#ff5f57"/><circle cx="47" cy="30" r="5" fill="#febc2e"/><circle cx="64" cy="30" r="5" fill="#28c840"/>
  <rect x="86.5" y="18.5" width="{LW-112}" height="23" rx="11.5" fill="#ffffff" fill-opacity=".04" stroke="#ffffff" stroke-opacity=".08"/>
  <path d="M100 26.5v-2a3 3 0 0 1 6 0v2" fill="none" stroke="{MUTED}" stroke-width="1.3"/><rect x="98.5" y="26.5" width="9" height="7" rx="1.5" fill="{MUTED}"/>
  <text class="m mu" x="116" y="34" font-size="11.5">{esc(url)}</text>
  <rect class="{p}cur" x="{116 + len(url)*6.9 + 3:.1f}" y="23.5" width="1.6" height="13" fill="{CYAN}"/>
  <line x1="1" y1="56.5" x2="{LW-1}" y2="56.5" stroke="#ffffff" stroke-opacity=".07"/>
</g>
<text class="m pk fu" {delay(.25)} x="34" y="88" font-size="11.5" letter-spacing="1.5">// WHAT I BUILD</text>
{''.join(rows)}

{card(p, RX, 0, RW, H)}
{''.join(seg_svg)}
<text class="m mu" x="{RX+24}" y="50" font-size="11" letter-spacing="1.5">LIFE OUTSIDE THE IDE</text>
{''.join(sl_svg)}
<line x1="{RX+24}" y1="250.5" x2="{W-24}" y2="250.5" stroke="#ffffff" stroke-opacity=".07"/>
{''.join(ring_svg)}
<text class="m dim" x="{W-24}" y="318" font-size="9.5" text-anchor="end">daily rings</text>
"""
    return svg_doc(W, H, "What I build and life outside the IDE", css, body, fonts=("display500", "display700", "mono400"))


def life_art(kind, cx, cy):
    """Small hand-drawn style illustrations, ~100px, centred at cx,cy."""
    if kind == "heart":
        return f"""
<g class="a-beat"><path transform="translate({cx-34} {cy-30})" d="M34 60S0 40 0 18A17 17 0 0 1 34 10a17 17 0 0 1 34 8C68 40 34 60 34 60z" fill="{PINK}" fill-opacity=".18" stroke="{PINK}" stroke-width="2.4" stroke-linejoin="round"/></g>
<circle class="a-tw" cx="{cx-46}" cy="{cy-28}" r="2.5" fill="{CYAN}"/><circle class="a-tw" style="animation-delay:.8s" cx="{cx+48}" cy="{cy-18}" r="2" fill="{VIOLET}"/>
<circle class="a-tw" style="animation-delay:1.6s" cx="{cx+40}" cy="{cy+32}" r="2.5" fill="{PINK}"/>"""
    if kind == "night":
        return f"""
<path d="M{cx+20} {cy-46}a24 24 0 1 0 22 32a19 19 0 1 1-22-32z" fill="{VIOLET}" fill-opacity=".2" stroke="{VIOLET}" stroke-width="2"/>
<rect x="{cx-48}" y="{cy-6}" width="74" height="46" rx="5" fill="{BG}" stroke="{CYAN}" stroke-width="2"/>
<path d="M{cx-60} {cy+44}h98l-6 6h-86z" fill="{CYAN}" fill-opacity=".3" stroke="{CYAN}" stroke-width="2" stroke-linejoin="round"/>
<path d="M{cx-38} {cy+6}h22M{cx-38} {cy+16}h34M{cx-32} {cy+26}h18" stroke="{PINK}" stroke-width="2.4" stroke-linecap="round"/>
<circle class="a-tw" cx="{cx+46}" cy="{cy+2}" r="2" fill="#fff"/><circle class="a-tw" style="animation-delay:1s" cx="{cx-18}" cy="{cy-36}" r="1.6" fill="#fff"/>"""
    if kind == "medium":
        return f"""
<rect x="{cx-44}" y="{cy-44}" width="88" height="88" rx="22" fill="#fff" fill-opacity=".05" stroke="url(#a-hair)" stroke-width="1.5"/>
{icon("medium", cx-26, cy-26, 52, TEXT)}"""
    if kind == "ml":
        layers = [[-30, 0, 30], [-40, -13, 13, 40], [-18, 18]]
        xs = [cx - 52, cx, cx + 52]
        out = []
        for li in range(2):
            for a in layers[li]:
                for b in layers[li + 1]:
                    out.append(f'<line x1="{xs[li]}" y1="{cy+a}" x2="{xs[li+1]}" y2="{cy+b}" stroke="{VIOLET}" stroke-opacity=".35" stroke-width="1.2"/>')
        k = 0
        for li, ys in enumerate(layers):
            for a in ys:
                out.append(f'<circle class="a-node" style="animation-delay:{k*.18:.2f}s" cx="{xs[li]}" cy="{cy+a}" r="7" fill="{CYAN}" stroke="{BG}" stroke-width="2"/>')
                k += 1
        return "".join(out)
    raise ValueError(kind)


# =========================================================================
# stack.svg
# =========================================================================
def stack():
    p = "s-"
    W, H = 840, 380
    cx, cy = 222, 190
    orbits = CFG["orbits"]  # [{tilt, a, b, period, icons:[...]}]
    paths, icons_svg = [], []
    moons_for = set(CFG.get("moons", []))
    for oi, o in enumerate(orbits):
        a, b = o["a"], o["b"]
        phi = math.radians(o["tilt"])

        def pt(t):
            x = cx + a * math.cos(t) * math.cos(phi) - b * math.sin(t) * math.sin(phi)
            y = cy + a * math.cos(t) * math.sin(phi) + b * math.sin(t) * math.cos(phi)
            return x, y

        steps = 72
        ell = " ".join(("M" if i == 0 else "L") + f"{x:.1f} {y:.1f}" for i, (x, y) in enumerate(pt(2 * math.pi * i / steps) for i in range(steps + 1)))
        paths.append(f'<path d="{ell}Z" fill="none" stroke="url(#{p}hair)" stroke-width="1.2" stroke-dasharray="2 5"/>')
        k = len(o["icons"])
        for ii, slug in enumerate(o["icons"]):
            t0 = 2 * math.pi * ii / k + oi * 0.7
            sx, sy = pt(t0)
            rel = []
            for s in range(steps + 1):
                x, y = pt(t0 + 2 * math.pi * s / steps)
                rel.append(("M" if s == 0 else "L") + f"{x - sx:.1f} {y - sy:.1f}")
            moon = ""
            if slug in moons_for:
                moon = f"""<g><circle cx="0" cy="-27" r="3" fill="{PINK}"/><circle cx="0" cy="27" r="2.2" fill="{CYAN}"/>
  <animateTransform attributeName="transform" type="rotate" from="0" to="360" dur="4s" repeatCount="indefinite"/></g>"""
            icons_svg.append(f"""
<g transform="translate({sx:.1f} {sy:.1f})"><g>
  <animateMotion dur="{o['period']}s" repeatCount="indefinite" path="{' '.join(rel)}"/>
  {moon}
  <circle r="19" fill="#161827" stroke="url(#{p}hair)" stroke-width="1.2"/>
  {icon(slug, -10.5, -10.5, 21)}
</g></g>""")

    chips_svg, chip_css = [], []
    gx, gy = 452, 44
    allchips = [(g["title"], chip) for g in CFG["chips"] for chip in g["items"]]
    N = len(allchips)
    step = 0.32
    total = N * step
    idx = 0
    y = gy
    for gi, g in enumerate(CFG["chips"]):
        chips_svg.append(f'<text class="m vi fu" {delay(.2 + gi*.1)} x="{gx}" y="{y}" font-size="11" letter-spacing="1.5">{esc(g["title"].upper())}</text>')
        y += 12
        x = gx
        for item in g["items"]:
            w = len(item) * 7.1 + 22
            if x + w > W - 24:
                x = gx
                y += 32
            a = idx / N * 100
            b = (idx + 2.2) / N * 100
            chip_css.append(
                f"@keyframes {p}c{idx}{{0%,{a:.2f}%,{min(b,100):.2f}%,100%{{stroke:#2a2d42;fill:#ffffff;fill-opacity:.03}}"
                f"{(a+b)/2:.2f}%{{stroke:{CYAN};fill:{CYAN};fill-opacity:.1}}}}"
                f".{p}c{idx}{{animation:{p}c{idx} {total:.2f}s ease-in-out 1.2s infinite;}}"
            )
            chips_svg.append(
                f'<g class="fu" {delay(.3 + idx*.03)}><rect class="{p}c{idx}" x="{x+.5:.1f}" y="{y+.5}" width="{w:.1f}" height="25" rx="12.5" fill="#ffffff" fill-opacity=".03" stroke="#2a2d42"/>'
                f'<text class="d t" x="{x + w/2:.1f}" y="{y+17}" font-size="12.5" font-weight="500" text-anchor="middle">{esc(item)}</text></g>'
            )
            x += w + 8
            idx += 1
        y += 50

    css = f"""
{''.join(chip_css)}
.{p}core{{transform-box:fill-box;transform-origin:center;animation:{p}core 3s ease-in-out infinite;}}
@keyframes {p}core{{50%{{transform:scale(1.18);opacity:.55}}}}
"""
    body = f"""
<defs>{common_defs(p)}
  <radialGradient id="{p}corefill"><stop offset="0" stop-color="#fff"/><stop offset=".35" stop-color="{CYAN}"/><stop offset="1" stop-color="{VIOLET}" stop-opacity="0"/></radialGradient>
</defs>
{card(p, 0, 0, W, H)}
<text class="m pk" x="28" y="36" font-size="11.5" letter-spacing="1.5">// TECH ORBIT</text>
{''.join(paths)}
<circle class="{p}core" cx="{cx}" cy="{cy}" r="44" fill="url(#{p}corefill)" opacity=".35"/>
<circle cx="{cx}" cy="{cy}" r="24" fill="#161827" stroke="{CYAN}" stroke-width="1.5"/>
<text class="m cy" x="{cx}" y="{cy+5}" font-size="14" font-weight="700" text-anchor="middle">&lt;/&gt;</text>
{''.join(icons_svg)}
<line x1="432.5" y1="28" x2="432.5" y2="{H-28}" stroke="#ffffff" stroke-opacity=".06"/>
{''.join(chips_svg)}
"""
    return svg_doc(W, H, "Tech stack", css, body, fonts=("display500", "mono400", "mono700"))


# =========================================================================
# id-dashboard.svg
# =========================================================================
def fmt_num(n):
    return f"{n/1000:.1f}k" if n >= 10000 else str(n)


def odometer(p, x, y, value, size=26, color=TEXT, start_delay=0.6):
    """Rolling digits; base (static) state shows the final value."""
    s = fmt_num(value) if isinstance(value, int) else str(value)
    cw = size * 0.6
    lh = size * 1.6
    out = [f'<g clip-path="url(#{p}odo)" transform="translate({x} {y})">']
    for i, ch in enumerate(s):
        if ch.isdigit():
            d = int(ch)
            col = "".join(f'<text x="{i*cw:.1f}" y="{k*lh:.1f}">{k}</text>' for k in range(10))
            out.append(
                f'<g class="{p}roll" style="transform:translateY({-d*lh:.1f}px);animation-delay:{start_delay + i*.08:.2f}s">{col}</g>'
            )
        else:
            out.append(f'<text x="{i*cw:.1f}" y="0">{esc(ch)}</text>')
    out.append("</g>")
    return "".join(out)


def id_dashboard():
    p = "i-"
    W, H = 840, 400
    c = CFG
    img = b64(ROOT / "assets" / "badge.jpg")

    # ---- badge --------------------------------------------------------
    bx, bw, bh, by = 62, 220, 292, 92
    pcx = bx + bw / 2  # pivot x
    bars = []
    xx = bx + 112
    seed = 7
    while xx < bx + bw - 22:
        seed = (seed * 37 + 11) % 97
        w = 1 + seed % 3
        bars.append(f'<rect x="{xx}" y="{by+246}" width="{w}" height="22" fill="{TEXT}" fill-opacity=".8"/>')
        xx += w + 1 + (seed % 2)
    strap_txt = (c["strap"] + " · ") * 3
    badge = f"""
<g class="{p}swing"><g class="{p}sway">
  <path d="M{pcx-22} -4 L{pcx-14} {by-10} L{pcx+14} {by-10} L{pcx+22} -4 Z" fill="url(#{p}strap)"/>
  <text class="m" transform="translate({pcx+4} 4) rotate(90)" font-size="8.5" font-weight="700" fill="#0d0e16" letter-spacing="1">{esc(strap_txt[:22])}</text>
  <rect x="{pcx-16}" y="{by-14}" width="32" height="16" rx="4" fill="url(#{p}metal)"/>
  <rect x="{pcx-8}" y="{by-6}" width="16" height="12" rx="3" fill="none" stroke="url(#{p}metal)" stroke-width="3"/>
  <g clip-path="url(#{p}badge)">
    <rect x="{bx}" y="{by}" width="{bw}" height="{bh}" fill="#151726"/>
    <rect x="{bx}" y="{by}" width="{bw}" height="{bh}" fill="url(#{p}dots)"/>
    <rect x="{bx}" y="{by}" width="{bw}" height="34" fill="url(#{p}aurora)" opacity=".9"/>
    <text class="m" x="{bx+14}" y="{by+22}" font-size="11" font-weight="700" fill="#0d0e16" letter-spacing="1.5">DEV ID</text>
    <text class="m" x="{bx+bw-14}" y="{by+22}" font-size="10" font-weight="700" fill="#0d0e16" text-anchor="end">{esc(c["badge_tag"])}</text>
    <image x="{pcx-60}" y="{by+48}" width="120" height="120" preserveAspectRatio="xMidYMid slice" clip-path="url(#{p}face)" href="data:image/jpeg;base64,{img}" xlink:href="data:image/jpeg;base64,{img}"/>
    <rect x="{pcx-60}" y="{by+48}" width="120" height="120" rx="14" fill="none" stroke="#fff" stroke-opacity=".08" stroke-width="2"/>
    <rect class="{p}trail" x="{pcx-60}" y="{by+48}" width="120" height="120" rx="14" fill="none" stroke="{CYAN}" stroke-width="2.4" stroke-linecap="round" pathLength="100"/>
    <text class="d t" x="{pcx}" y="{by+196}" font-size="16.5" font-weight="700" text-anchor="middle">{esc(c["name"])}</text>
    <text class="d mu" x="{pcx}" y="{by+215}" font-size="12" font-weight="500" text-anchor="middle">{esc(c["badge_role"])}</text>
    <rect x="{bx+18}" y="{by+244}" width="34" height="26" rx="5" fill="url(#{p}gold)"/>
    <path d="M{bx+18} {by+253}h34M{bx+18} {by+261}h34M{bx+30} {by+244}v26M{bx+40} {by+244}v26" stroke="#7a5a12" stroke-opacity=".55" stroke-width=".8"/>
    <text class="m dim" x="{bx+62}" y="{by+262}" font-size="8">NFC</text>
    {''.join(bars)}
    <text class="m dim" x="{bx+bw-18}" y="{by+282}" font-size="8" text-anchor="end">{esc(c["badge_id"])}</text>
    <g class="{p}holo"><rect x="{bx-120}" y="{by-40}" width="90" height="{bh+80}" fill="url(#{p}foil)" transform="rotate(22 {bx} {by})"/></g>
  </g>
  <rect x="{bx+.5}" y="{by+.5}" width="{bw-1}" height="{bh-1}" rx="16" fill="none" stroke="url(#{p}hair)"/>
</g></g>"""

    # ---- dashboard ----------------------------------------------------
    DX = 300
    DW = W - DX
    st = STATS or {}
    kpis = [
        ("PUBLIC REPOS", st.get("public_repos")),
        ("STARS EARNED", st.get("stars")),
        ("FOLLOWERS", st.get("followers")),
        ("CONTRIBS / YR", st.get("contributions")),
    ]
    tile_w = (DW - 48 - 3 * 10) / 4
    tiles = []
    accents = [CYAN, VIOLET, PINK, GREEN]
    for i, (label, val) in enumerate(kpis):
        tx = DX + 24 + i * (tile_w + 10)
        v = odometer(p, tx + 14, 108, val, 26, TEXT, .6 + i * .15) if isinstance(val, int) else \
            f'<text class="m dim" x="{tx+14}" y="108" font-size="26">—</text>'
        tiles.append(f"""
<g class="fu" {delay(.2 + i*.1)}>
  <rect x="{tx+.5:.1f}" y="52.5" width="{tile_w-1:.1f}" height="74" rx="12" fill="#ffffff" fill-opacity=".03" stroke="#ffffff" stroke-opacity=".07"/>
  <rect x="{tx+14:.1f}" y="62" width="16" height="2.5" rx="1.25" fill="{accents[i]}"/>
  <text class="m mu" x="{tx+14:.1f}" y="80" font-size="9.5" letter-spacing="1">{label}</text>
  <g class="m" font-size="26" font-weight="700" fill="{TEXT}">{v}</g>
</g>""")

    top = st.get("top_repos") or []
    chart = []
    cy0 = 168
    if top:
        mx = max(r["stars"] for r in top) or 1
        bar_max = DW - 48 - 170 - 50
        for i, r in enumerate(top[:5]):
            yy = cy0 + i * 25
            bw_ = max(4, bar_max * r["stars"] / mx)
            chart.append(f"""
<g class="fu" {delay(.9 + i*.1)}>
  <text class="d t" x="{DX+24}" y="{yy+12}" font-size="12.5" font-weight="500">{esc(r["name"][:22])}</text>
  <rect x="{DX+190}" y="{yy+2}" width="{bar_max:.1f}" height="12" rx="6" fill="#ffffff" fill-opacity=".04"/>
  <rect class="{p}bar" style="animation-delay:{1.1 + i*.12:.2f}s" x="{DX+190}" y="{yy+2}" width="{bw_:.1f}" height="12" rx="6" fill="url(#{p}barfill)"/>
  <text class="m mu" x="{W-24}" y="{yy+12}" font-size="11.5" text-anchor="end">★ {r["stars"]}</text>
</g>""")
    else:
        chart.append(f'<text class="m dim" x="{DX+24}" y="{cy0+40}" font-size="12">stats appear after the first workflow run</text>')

    now_lines = "".join(
        f'<g class="fu" {delay(1.5 + i*.12)}><circle cx="{DX+30}" cy="{322 + i*22}" r="2.5" fill="{PINK}"/>'
        f'<text class="d t" x="{DX+42}" y="{326 + i*22}" font-size="13" font-weight="500">{esc(t)}</text></g>'
        for i, t in enumerate(c["now"])
    )
    updated = st.get("updated", "")
    upd_label = ("updated " + updated) if updated else "refreshed daily"

    css = f"""
.{p}swing{{transform-box:view-box;transform-origin:{pcx}px 0px;animation:{p}swing 4.2s cubic-bezier(.3,0,.3,1) both;}}
@keyframes {p}swing{{0%{{transform:rotate(-12deg)}}14%{{transform:rotate(8deg)}}28%{{transform:rotate(-5.5deg)}}42%{{transform:rotate(3.5deg)}}
56%{{transform:rotate(-2deg)}}70%{{transform:rotate(1deg)}}84%{{transform:rotate(-.4deg)}}100%{{transform:rotate(0)}}}}
.{p}sway{{transform-box:view-box;transform-origin:{pcx}px 0px;animation:{p}sway 7s ease-in-out 4.2s infinite;}}
@keyframes {p}sway{{0%,100%{{transform:rotate(0)}}25%{{transform:rotate(1.3deg)}}75%{{transform:rotate(-1.3deg)}}}}
.{p}trail{{stroke-dasharray:16 84;animation:{p}trail 3.2s linear infinite;}}
@keyframes {p}trail{{from{{stroke-dashoffset:100}}to{{stroke-dashoffset:0}}}}
.{p}holo{{mix-blend-mode:screen;animation:{p}holo 5s ease-in-out 1s infinite both;}}
@keyframes {p}holo{{0%{{transform:translateX(0)}}45%,100%{{transform:translateX(470px)}}}}
.{p}roll{{animation:{p}roll 1.6s cubic-bezier(.2,.8,.2,1) both;}}
@keyframes {p}roll{{from{{transform:translateY(0)}}}}
.{p}bar{{transform-box:fill-box;transform-origin:left;animation:{p}bar 1s cubic-bezier(.2,.8,.2,1) both;}}
@keyframes {p}bar{{from{{transform:scaleX(0)}}}}
.{p}live{{animation:{p}live 1.6s ease-in-out infinite;}}
@keyframes {p}live{{50%{{opacity:.25}}}}
"""
    body = f"""
<defs>{common_defs(p)}
  <clipPath id="{p}badge"><rect x="{bx}" y="{by}" width="{bw}" height="{bh}" rx="16"/></clipPath>
  <clipPath id="{p}face"><rect x="{pcx-60}" y="{by+48}" width="120" height="120" rx="14"/></clipPath>
  <clipPath id="{p}odo"><rect x="-4" y="-24" width="120" height="30"/></clipPath>
  <linearGradient id="{p}strap" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="{VIOLET}"/><stop offset="1" stop-color="{PINK}"/></linearGradient>
  <linearGradient id="{p}metal" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#e5e7ef"/><stop offset=".5" stop-color="#8b90a8"/><stop offset="1" stop-color="#d4d6e0"/></linearGradient>
  <linearGradient id="{p}gold" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#fde68a"/><stop offset=".5" stop-color="#d4a017"/><stop offset="1" stop-color="#fbbf24"/></linearGradient>
  <linearGradient id="{p}foil" x1="0" y1="0" x2="1" y2="0">
    <stop offset="0" stop-color="{CYAN}" stop-opacity="0"/><stop offset=".3" stop-color="{CYAN}" stop-opacity=".22"/>
    <stop offset=".55" stop-color="{VIOLET}" stop-opacity=".22"/><stop offset=".8" stop-color="{PINK}" stop-opacity=".22"/><stop offset="1" stop-color="{PINK}" stop-opacity="0"/>
  </linearGradient>
  <linearGradient id="{p}barfill" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="{CYAN}" stop-opacity=".55"/><stop offset="1" stop-color="{CYAN}"/></linearGradient>
</defs>
<rect width="{W}" height="{H}" fill="none"/>
{card(p, DX, 0, DW, H)}
<text class="m pk" x="{DX+24}" y="34" font-size="11.5" letter-spacing="1.5">// DASHBOARD</text>
<g class="fi" {delay(.4)}><circle class="{p}live" cx="{W-24-len(upd_label)*6-10:.1f}" cy="30.5" r="3.5" fill="{GREEN}"/>
<text class="m mu" x="{W-24}" y="34" font-size="10" text-anchor="end">{esc(upd_label)}</text></g>
{''.join(tiles)}
<text class="m mu" x="{DX+24}" y="156" font-size="10" letter-spacing="1">TOP REPOS BY STARS</text>
{''.join(chart)}
<line x1="{DX+24}" y1="296.5" x2="{W-24}" y2="296.5" stroke="#ffffff" stroke-opacity=".07"/>
<text class="m pk" x="{DX+24}" y="312" font-size="10" letter-spacing="1"><tspan>NOW</tspan></text>
{now_lines}
{badge}
"""
    return svg_doc(W, H, f"{c['name']} — ID badge and GitHub dashboard", css, body,
                   fonts=("display500", "display700", "mono400", "mono700"))


# =========================================================================
# connect.svg + link cards
# =========================================================================
def connect():
    p = "c-"
    W, H = 840, 190
    img = b64(ROOT / "assets" / "avatar.jpg")
    acx, acy, ar = 104, 95, 58
    sparkles = [(196, 40, 0), (178, 150, .7), (64, 28, 1.3), (40, 150, 2)]
    css = f"""
.{p}ring{{transform-box:fill-box;transform-origin:center;animation:{p}spin 14s linear infinite;}}
@keyframes {p}spin{{to{{transform:rotate(360deg)}}}}
.{p}neon{{animation:{p}neon 5s linear infinite;}}
@keyframes {p}neon{{0%,18%,22%,62%,64%,100%{{opacity:1}}20%,63%{{opacity:.45}}}}
.{p}nudge{{animation:{p}nudge 1.4s ease-in-out infinite;}}
@keyframes {p}nudge{{50%{{transform:translateX(10px)}}}}
.{p}tw{{transform-box:fill-box;transform-origin:center;animation:{p}tw 2.2s ease-in-out infinite;}}
@keyframes {p}tw{{50%{{transform:scale(.3);opacity:.2}}}}
.{p}point{{transform-box:fill-box;transform-origin:left center;animation:{p}point 1.4s ease-in-out infinite;}}
@keyframes {p}point{{50%{{transform:translateX(6px)}}}}
"""
    spark = "".join(
        f'<path class="{p}tw" style="animation-delay:{d}s" d="M{x} {y-7}Q{x} {y} {x+7} {y}Q{x} {y} {x} {y+7}Q{x} {y} {x-7} {y}Q{x} {y} {x} {y-7}Z" fill="{PINK if i % 2 else CYAN}"/>'
        for i, (x, y, d) in enumerate(sparkles)
    )
    body = f"""
<defs>{common_defs(p)}
  <clipPath id="{p}av"><circle cx="{acx}" cy="{acy}" r="{ar-6}"/></clipPath>
  <filter id="{p}glowf" x="-20%" y="-50%" width="140%" height="200%"><feGaussianBlur stdDeviation="4" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>
</defs>
{card(p, 0, 0, W, H)}
<circle class="{p}ring" cx="{acx}" cy="{acy}" r="{ar}" fill="none" stroke="url(#{p}aurora)" stroke-width="2.5" stroke-dasharray="18 9" stroke-linecap="round"/>
<image x="{acx-ar+6}" y="{acy-ar+6}" width="{2*ar-12}" height="{2*ar-12}" preserveAspectRatio="xMidYMid slice" clip-path="url(#{p}av)" href="data:image/jpeg;base64,{img}" xlink:href="data:image/jpeg;base64,{img}"/>
{spark}
<g class="fu" {delay(.2)}>
  <text class="m pk" x="210" y="58" font-size="11.5" letter-spacing="1.5">// CONNECT</text>
  <text class="d t" x="210" y="92" font-size="24" font-weight="700">{esc(CFG["connect_line"])}</text>
  <text class="d mu" x="210" y="118" font-size="14" font-weight="500">{esc(CFG["connect_sub"])}</text>
</g>
<g class="fi" {delay(.6)}>
  <text class="d {p}neon" x="{W-40}" y="102" font-size="30" font-weight="700" text-anchor="end" fill="{PINK}" filter="url(#{p}glowf)" transform="rotate(-4 {W-120} 96)">@{esc(CFG["username"])}</text>
  <g class="{p}nudge"><text class="m cy" x="210" y="152" font-size="14">→ → →</text></g>
  <text class="m mu" x="290" y="152" font-size="12">links below</text>
</g>
"""
    return svg_doc(W, H, "Connect with me", css, body, fonts=("display500", "display700", "mono400"))


def link_card(item, i):
    p = f"l{i}-"
    W, H = 270, 76
    accent = [CYAN, VIOLET, PINK, GREEN][i % 4]
    if item["icon"] == "linkedin":
        glyph = f'<rect x="24" y="22" width="32" height="32" rx="7" fill="{accent}" fill-opacity=".15" stroke="{accent}" stroke-width="1.2"/><text class="d" x="40" y="44" font-size="16" font-weight="700" text-anchor="middle" fill="{accent}">in</text>'
    elif item["icon"] == "web":
        glyph = f'<circle cx="40" cy="38" r="15" fill="none" stroke="{accent}" stroke-width="1.6"/><ellipse cx="40" cy="38" rx="6.5" ry="15" fill="none" stroke="{accent}" stroke-width="1.4"/><path d="M25 38h30M28 30h24M28 46h24" stroke="{accent}" stroke-width="1.2"/>'
    else:
        glyph = icon(item["icon"], 26, 24, 28, TEXT)
    css = f""".{p}n{{animation:{p}n 1.6s ease-in-out {i*.2:.1f}s infinite;}}@keyframes {p}n{{50%{{transform:translate(4px,-4px)}}}}"""
    body = f"""<defs>{common_defs(p)}</defs>{card(p, 0, 0, W, H, 16)}
{glyph}
<text class="d t" x="70" y="35" font-size="15" font-weight="700">{esc(item["label"])}</text>
<text class="m mu" x="70" y="55" font-size="11.5">{esc(item["handle"])}</text>
<g class="{p}n"><path d="M{W-38} 46l12-12M{W-36} 34h10v10" fill="none" stroke="{accent}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></g>"""
    return svg_doc(W, H, item["label"], css, body, fonts=("display700", "mono400"))


def main():
    OUT.mkdir(exist_ok=True)
    files = {
        "hero.svg": hero(),
        "about-life.svg": about_life(),
        "stack.svg": stack(),
        "id-dashboard.svg": id_dashboard(),
        "connect.svg": connect(),
    }
    for i, item in enumerate(CFG["links"]):
        files[f"link-{item['id']}.svg"] = link_card(item, i)
    for name, content in files.items():
        (OUT / name).write_text(content)
        print(f"{name:22s} {len(content.encode())/1024:6.1f} KB")


if __name__ == "__main__":
    main()
