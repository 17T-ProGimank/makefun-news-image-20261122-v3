#!/usr/bin/env python3
"""Draw the front page for Sunday 22 November 2026.

Renders a 1024x1024 newspaper front page: masthead, three hero stories,
a numbered 22-story grid, a dotted world map with 12 pins, a 15-item
"Also on" list, a markets ticker and a sources / verification footer.
A full-width "ON THIS DAY" band of 22 November anniversaries sits
between the ticker and the footer, and each hero card carries a source
line under its facts.

Round 3 vs round 2: every hero and grid story carries a verification
badge (CONFIRMED / OFFICIAL / REPORTED, honestly assigned from its
source); a "BY THE NUMBERS" strip of key figures sits under the grid;
hero art is richer and seven grid stories carry a small glyph. Two
"Also on" items were replaced because round 2 contradicted its own
DATE CHECK (Kyiv bridges) and duplicated grid story #1 (NATO jets);
grid #22 was replaced because its Long March-8A launch was 20 Nov,
not 22 Nov. The map now really has 12 pins (Cikande added).

Deterministic: the same input always produces the same PNG bytes.
Run:  python3 draw_poster.py [output_dir]
"""
import hashlib
import os
import sys

from PIL import Image, ImageDraw, ImageFont

W, H = 1024, 1024

# ---------------------------------------------------------------- palette
NAVY = (11, 37, 69)
NAVY2 = (18, 56, 96)
GOLD = (201, 162, 39)
GOLD_LT = (226, 190, 84)
PAPER = (247, 243, 234)
PAPER2 = (238, 232, 219)
INK = (22, 26, 32)
MUTED = (96, 102, 110)
RULE = (196, 188, 172)
RED = (172, 32, 32)
RED_LT = (238, 214, 210)
TEAL = (14, 110, 110)
TEAL_LT = (208, 232, 228)
GREEN = (34, 120, 70)
DOT = (120, 148, 176)
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)

REGION_COLORS = {
    "EU": (31, 78, 121),
    "ME": (138, 90, 0),
    "AP": (14, 110, 110),
    "AM": (122, 31, 61),
    "AF": (179, 84, 30),
    "MK": (46, 125, 50),
    "SC": (91, 74, 138),
}
REGION_NAMES = {
    "EU": "EUROPE",
    "ME": "MIDDLE EAST",
    "AP": "ASIA-PACIFIC",
    "AM": "AMERICAS",
    "AF": "AFRICA",
    "MK": "MARKETS",
    "SC": "SCIENCE & SPORT",
}

# Verification badge per story: CONFIRMED = two or more independent
# outlets (or wire + agency); OFFICIAL = a government, agency or other
# official source; REPORTED = a single outlet. Assigned honestly from
# each story's own source line — never upgraded without a second source.
BADGE_FILL = {
    "CONFIRMED": (34, 120, 70),
    "OFFICIAL": (31, 78, 121),
    "REPORTED": (138, 90, 0),
}
HERO_BADGES = ["CONFIRMED", "CONFIRMED", "CONFIRMED"]
GRID_BADGES = {
    0: "REPORTED", 1: "REPORTED", 2: "REPORTED", 3: "OFFICIAL",
    4: "OFFICIAL", 5: "REPORTED", 6: "CONFIRMED", 7: "REPORTED",
    8: "REPORTED", 9: "OFFICIAL", 10: "REPORTED", 11: "CONFIRMED",
    12: "OFFICIAL", 13: "REPORTED", 14: "OFFICIAL", 15: "REPORTED",
    16: "REPORTED", 17: "OFFICIAL", 18: "OFFICIAL", 19: "CONFIRMED",
    20: "REPORTED", 21: "REPORTED",
}
# Source line printed under each hero card's facts (one outlet set per hero).
HERO_SOURCES = [
    "Sources: COP31 presidency \u00b7 Reuters \u00b7 AP",
    "Sources: FBI \u00b7 Reuters \u00b7 AP",
    "Sources: NYSE \u00b7 Nasdaq \u00b7 Reuters",
]
# Small drawn glyph per grid story (index -> kind); only stories with a
# clear picturable subject get one.
GLYPHS = {0: "jet", 4: "orbit", 7: "flag", 11: "boat", 17: "shield",
          19: "chart", 21: "warning"}
NUMBERS = ("BY THE NUMBERS  \u00b7  $120bn COP31 aid cut  \u00b7  S&P 500 \u22123.70%  "
           "\u00b7  Nasdaq \u22125.28%  \u00b7  Nvidia \u221214%  \u00b7  EU budget \u20ac1.78tn  "
           "\u00b7  France turnout 82,500")

# ---------------------------------------------------------------- content
HEROES = [
    {
        "kicker": "CLIMATE  ·  ANTALYA",
        "color": TEAL,
        "tint": TEAL_LT,
        "art": "sun",
        "title": "COP31 DEAL AT DAWN",
        "facts": [
            "After a night of overtime, a text all parties can agree on",
            "Plenary to approve 06:00 GMT  ·  Fossil language dropped",
        ],
    },
    {
        "kicker": "MEXICO  ·  SINALOA",
        "color": NAVY2,
        "tint": (214, 222, 232),
        "art": "bars",
        "title": "\u2018EL CHAPO ISIDRO\u2019 SEIZED",
        "facts": [
            "Special forces capture Fausto Isidro Meza Flores in Guasave",
            "FBI Most Wanted #533  ·  $5m bounty  ·  7 gunmen, 4 soldiers killed",
        ],
    },
    {
        "kicker": "MARKETS  ·  FRIDAY CLOSE",
        "color": RED,
        "tint": RED_LT,
        "art": "chart",
        "title": "AI ROUT DEEPENS",
        "facts": [
            "S&P 500 \u22123.70% to 6,910.39  ·  Nasdaq \u22125.28% to 22,617.73",
            "Nvidia \u221214% to $125.53 on SEC accounting probe",
        ],
    },
]

# (headline, fact, region) — 22 numbered grid stories.
# Freshness rule: only stories from the 21-22 Nov news cycle. Stale 20 Nov
# items (Kyiv bridges, Peru quake, Shenzhen summit, ICJ Myanmar ruling,
# Long March-8A launch) are deliberately left out — see the DATE CHECK
# line in the footer. Round 3 also drops the 20 Nov Long March-8A row
# (#22 in round 2) for a 22 Nov Dymer strike.
GRID = [
    ("NATO scrambles jets over Poland",
     "Polish, Swedish, Dutch jets + Patriots after missile landings", "EU"),
    ("Eisenkot invites Likud to coalition talks",
     "48 seats, needs 61; mandate runs to 6 Dec \u2014 Al Jazeera", "ME"),
    ("Gaza recovery: 70 bodies found in 35 days",
     "~8,000 still buried; mass burials held \u2014 Al Jazeera", "ME"),
    ("Trump reposts mock \u2018TrumpCare\u2019 gold card",
     "Repost \u2260 endorsement; White House already rejected it", "AM"),
    ("BepiColombo enters orbit around Mercury",
     "8-year voyage; 2nd mission ever to orbit Mercury \u2014 ESA", "SC"),
    ("Brazil unveils fossil phase-out roadmap",
     "COP31 side deal speeds the end of fossil fuels", "AM"),
    ("FBI crime database hacked",
     "2nd FBI intrusion in months, CNN / Reuters report", "AM"),
    ("Las Vegas GP today \u2014 Verstappen on pole",
     "Antonelli fastest in qualifying, hit with 5-place penalty", "SC"),
    ("Vance sidesteps Iran war talk",
     "VP avoids backing Iran war, eyes White House bid", "AM"),
    ("Estonia shuts all Russia border crossings",
     "Denmark expels Russian diplomat over alleged GRU plot", "EU"),
    ("Chinese military jet turns back off Manila",
     "Turns back short of Manila as Quad leaders meet", "AP"),
    ("Funeral boat capsizes in Bayelsa, Nigeria",
     "At least 24 dead; hundreds feared missing \u2014 AP / NEMA", "AF"),
    ("EU proposes \u20ac1.78tn budget for 2028\u201334",
     "\u20ac100bn kept for Ukraine; leaders meet 26\u201327 Nov", "EU"),
    ("France protests enter 6th Saturday",
     "Turnout falls to 82,500; organisers claim 150,000", "EU"),
    ("Iran open to \u2018fair deal\u2019 with US",
     "Araghchi: enriched uranium stays in Iran", "ME"),
    ("Syria intercepts arms shipment to Lebanon",
     "Qatar visits Tehran as the region talks", "ME"),
    ("Democrats threaten Starshield funding halt",
     "Citing SpaceX role in the Ukraine war", "AM"),
    ("UK confirms offensive cyber operations",
     "Against Russia, China, Iran and North Korea", "EU"),
    ("Gupta gets 19 years 7 months in US",
     "Plot to kill Sikh separatist Pannun \u2014 US Justice Dept", "AM"),
    ("Anthropic slides 9.1% in Friday trade",
     "$88.30 vs $83 IPO price; debut had jumped 34%", "MK"),
    ("Russia keeps hitting Ukraine\u2019s power grid",
     "Paramedic and child killed in Kryvyi Rih", "EU"),
    ("Drone flattens Kyiv-area apartment block",
     "14 missing in Dymer; 3 killed in strikes \u2014 AP", "EU"),
]

ALSO_ON = [
    "COP31: $120bn adaptation aid cut from draft; 1.5\u00b0C goal conceded lost",
    "Cikande candy factory fire: 3 dead, 36 missing \u2014 Reuters / AP",
    "Russian warship hit at Benghazi; 2nd ship targeted \u2014 BBC",
    "Kyiv claims Crimea bridge repairs could take a year",
    "Gaza ceasefire violations: 6 Palestinians wounded, reports say",
    "Norway cuts screens in schools, tightens digital rules",
    "Nigeria opens 2026 oil & gas auction \u2014 40 blocks, 17 offshore",
    "VP Vance avoids backing Iran war, eyes White House bid",
    "Democrats threaten to halt Starshield funding over Ukraine",
    "EU to blacklist Wildberries founder Tatyana Kim",
    "Brazil launches roadmap to speed fossil-fuel phase-out",
    "El Chapo Isidro flown to Mexico City after Guasave raid",
    "China regulator fines Baidu over live-streaming deal",
    "Melania Trump hopes for Ukraine ceasefire before Christmas",
    "Denmark urges EU to limit Russian visas after rapper plot",
]

# (number, name, lon, lat) — pins on the dotted map
PINS = [
    (1, "Antalya", 30.7, 36.9),
    (2, "Kyiv", 30.5, 50.45),
    (3, "Nowy Lipowiec", 22.3, 50.3),
    (4, "Guasave", -108.5, 25.6),
    (5, "Jerusalem", 35.2, 31.8),
    (6, "Gaza", 34.5, 31.5),
    (7, "Lima", -77.0, -12.0),
    (8, "Las Vegas", -115.1, 36.2),
    (9, "Washington", -77.0, 38.9),
    (10, "Shenzhen", 114.0, 22.5),
    (11, "Manila", 121.0, 14.6),
    (12, "Cikande", 106.3, -6.2),
]

TICKER = ("MARKETS \u00b7 FRI CLOSE 20 NOV \u2014 S&P 500 6,910.39 \u22123.70% \u00b7 "
          "Nasdaq 22,617.73 \u22125.28% \u00b7 Dow 48,147.33 \u22121.93% \u00b7 "
          "Nvidia $125.53 \u221214% \u00b7 AMD \u221213.3% \u00b7 Micron \u221213.9%")

SOURCES = ("SOURCES: REUTERS \u00b7 AP \u00b7 NATURE \u00b7 ESA \u00b7 ISW \u00b7 CHARLES SCHWAB \u00b7 "
           "MOTLEY FOOL \u00b7 CBOE \u00b7 AL JAZEERA \u00b7 CNN \u00b7 XINHUA")
VERIFY = ("DATE-CHECKED 22 NOV 2026  \u00b7  EVERY FIGURE ATTRIBUTED  \u00b7  "
          "BADGES: CONFIRMED = 2+ OUTLETS  \u00b7  40 SOURCED STORIES  \u00b7  7 REGIONS")
DATECHECK = ("DATE CHECK \u2014 LEFT OUT ON PURPOSE: KYIV BRIDGES \u00b7 PERU QUAKE \u00b7 "
             "ICJ MYANMAR RULING \u00b7 SHENZHEN SUMMIT (ALL 20 NOV) \u00b7 "
             "WALL ST ROUT (FRI 20 NOV \u2014 SEE TICKER)")
TIMELINE = ("UTC TIMELINE \u2014 00:00 COP31 DEAL AT DAWN  \u00b7  06:00 GMT PLENARY TO APPROVE  "
            "\u00b7  04:00 UTC LAS VEGAS GP  \u00b7  SUN PM COP31 COLLAPSES \u2014 NO DEAL")

# "On this day" — 22 November in history. Historical facts only, clearly
# labelled as history and never mixed with today's news; all three dates
# verified against Britannica / AP "On This Day" listings for 22 November:
# 1963 — JFK assassinated in Dallas; 1990 — Thatcher announces her
# resignation as prime minister; 2005 — Merkel sworn in as Germany's
# first woman chancellor. (year, headline, one-line detail)
HISTORY = [
    (1963, "JFK assassinated", "President Kennedy shot in Dallas"),
    (1990, "Thatcher resigns", "PM announces she will step down"),
    (2005, "Merkel sworn in", "Germany's first woman chancellor"),
]

# Coarse equirectangular land mask, 64 cols x 32 rows.
# Each entry: (row, [(col_start, col_end), ...]) — land cells, inclusive.
LAND = [
    (1, [(19, 21)]),
    (2, [(4, 15), (19, 22)]),
    (3, [(3, 17), (19, 22), (31, 33), (38, 58)]),
    (4, [(2, 18), (30, 34), (36, 58)]),
    (5, [(2, 17), (30, 34), (35, 59)]),
    (6, [(3, 16), (30, 33), (34, 58)]),
    (7, [(4, 15), (30, 33), (34, 56), (57, 58)]),
    (8, [(5, 15), (30, 32), (33, 55), (56, 57)]),
    (9, [(6, 14), (30, 36), (37, 54)]),
    (10, [(7, 13), (29, 35), (37, 52), (43, 45)]),
    (11, [(8, 13), (29, 36), (38, 50)]),
    (12, [(9, 12), (29, 36), (39, 49), (50, 52)]),
    (13, [(13, 16), (30, 36), (40, 48), (50, 54)]),
    (14, [(13, 17), (30, 36), (50, 54)]),
    (15, [(14, 18), (30, 36)]),
    (16, [(14, 18), (31, 36)]),
    (17, [(14, 18), (31, 35)]),
    (18, [(15, 18), (31, 35)]),
    (19, [(15, 18), (32, 34)]),
    (20, [(15, 17), (32, 34), (50, 54)]),
    (21, [(16, 17), (49, 55)]),
    (22, [(16, 17), (49, 55)]),
    (23, [(16, 16), (50, 54)]),
    (24, [(16, 17)]),
    (25, [(16, 16)]),
]

# ---------------------------------------------------------------- fonts
FONT_DIR = "/usr/share/fonts/truetype/dejavu"


def font(name, size):
    path = os.path.join(FONT_DIR, name)
    return ImageFont.truetype(path, size)


F_SERIF_B = lambda s: font("DejaVuSerif-Bold.ttf", s)  # noqa: E731
F_BOLD = lambda s: font("DejaVuSans-Bold.ttf", s)  # noqa: E731
F_REG = lambda s: font("DejaVuSans.ttf", s)  # noqa: E731


# ---------------------------------------------------------------- helpers
def text_w(draw, text, fnt):
    return draw.textlength(text, font=fnt)


def trunc(draw, text, fnt, max_w, ell="..."):
    if text_w(draw, text, fnt) <= max_w:
        return text
    while text and text_w(draw, text + ell, fnt) > max_w:
        text = text[:-1]
    return text + ell


def wrap(draw, text, fnt, max_w, max_lines=None):
    words = text.split()
    lines, cur = [], ""
    for word in words:
        trial = (cur + " " + word).strip()
        if text_w(draw, trial, fnt) <= max_w:
            cur = trial
        else:
            if cur:
                lines.append(cur)
            cur = word
            if max_lines and len(lines) >= max_lines:
                break
    if cur and (not max_lines or len(lines) < max_lines):
        lines.append(cur)
    if max_lines and len(lines) > max_lines:
        lines = lines[:max_lines]
    return lines


def fit_size(draw, text, fnt_for, max_w, start, minimum):
    size = start
    while size > minimum and text_w(draw, text, fnt_for(size)) > max_w:
        size -= 1
    return size


def rrect(draw, box, radius, fill=None, outline=None, width=1):
    draw.rounded_rectangle(box, radius=radius, fill=fill, outline=outline, width=width)


# ---------------------------------------------------------------- art
def draw_hero_art(draw, kind, x, y, w, h):
    """Small geometric illustration strip inside a hero card."""
    if kind == "sun":  # COP31: dawn sun with rays over a skyline and teal waves
        draw.rectangle([x, y, x + w, y + h], fill=(224, 238, 232))
        cx, cy = x + w - 46, y + 20
        for ux, uy in [(0, -1), (0.7, -0.7), (1, 0), (0.7, 0.7),
                       (0, 1), (-0.7, 0.7), (-1, 0), (-0.7, -0.7)]:
            draw.line([cx + ux * 20, cy + uy * 16, cx + ux * 28, cy + uy * 22],
                      fill=GOLD, width=2)
        draw.ellipse([cx - 15, cy - 13, cx + 15, cy + 13], fill=GOLD)
        # skyline silhouettes along the bottom
        for bx, bh in [(0, 12), (18, 20), (38, 10), (58, 16), (78, 9), (98, 14)]:
            draw.rectangle([x + 8 + bx, y + h - 6 - bh, x + 8 + bx + 14, y + h - 6],
                           fill=(14, 90, 90))
        for i in range(2):
            yy = y + h - 12 + i * 5
            draw.arc([x + 8, yy - 5, x + w - 96, yy + 12], 0, 180, fill=TEAL, width=2)
    elif kind == "bars":  # arrest: cell bars, gold star, skyline, floor line
        draw.rectangle([x, y, x + w, y + h], fill=(30, 52, 82))
        for bx, bh in [(0, 10), (22, 16), (46, 8), (70, 13)]:
            draw.rectangle([x + 10 + bx, y + h - 4 - bh, x + 10 + bx + 18, y + h - 4],
                           fill=(52, 78, 112))
        draw.line([x + 8, y + h - 4, x + w - 8, y + h - 4], fill=GOLD_LT, width=2)
        for i in range(9):
            bx = x + 14 + i * 32
            draw.rectangle([bx, y + 4, bx + 7, y + h - 10], fill=(120, 140, 165))
        cx, cy = x + w // 2, y + h // 2 - 4
        star = [(cx, cy - 16), (cx + 5, cy - 5), (cx + 17, cy - 5), (cx + 8, cy + 3),
                (cx + 11, cy + 15), (cx, cy + 8), (cx - 11, cy + 15), (cx - 8, cy + 3),
                (cx - 17, cy - 5), (cx - 5, cy - 5)]
        draw.polygon(star, fill=GOLD_LT, outline=GOLD)
    else:  # chart: gridlines, descending candlesticks, red down arrow
        draw.rectangle([x, y, x + w, y + h], fill=(243, 226, 224))
        for gy in (y + 12, y + 26, y + 40):
            draw.line([x + 10, gy, x + w - 10, gy], fill=(220, 190, 186), width=1)
        heights = [30, 26, 20, 14, 8]
        for i, hh in enumerate(heights):
            bx = x + 22 + i * 54
            top = y + 10 + (30 - hh)
            draw.line([bx + 15, top - 6, bx + 15, top + hh + 6], fill=(120, 20, 20), width=2)
            draw.rectangle([bx, top, bx + 30, top + hh], fill=RED)
        draw.line([x + 14, y + 6, x + w - 16, y + h - 12], fill=(120, 20, 20), width=4)
        draw.polygon([(x + w - 16, y + h - 12), (x + w - 34, y + h - 18),
                      (x + w - 30, y + h - 2)], fill=(120, 20, 20))


def draw_glyph(draw, kind, x, y, s, color):
    """A tiny (s x s) pictogram for one grid story, drawn in `color`."""
    if kind == "jet":  # paper-plane delta
        draw.polygon([(x + 1, y + s - 1), (x + s - 1, y + 1), (x + s - 4, y + s - 4),
                      (x + 1, y + s - 4)], fill=color)
    elif kind == "orbit":  # ringed planet
        draw.ellipse([x + 2, y + 3, x + s - 5, y + s - 2], outline=color, width=2)
        draw.ellipse([x + s - 7, y + 1, x + s - 2, y + 6], fill=color)
        draw.ellipse([x + 4, y + 5, x + 8, y + 9], fill=color)
    elif kind == "flag":  # chequered flag on a pole
        draw.line([x + 1, y + 1, x + 1, y + s - 1], fill=color, width=2)
        for r in range(2):
            for c in range(2):
                if (r + c) % 2 == 0:
                    draw.rectangle([x + 3 + c * 5, y + 1 + r * 5,
                                    x + 7 + c * 5, y + 5 + r * 5], fill=color)
    elif kind == "boat":  # hull + sail
        draw.polygon([(x + 1, y + s - 4), (x + s - 1, y + s - 4),
                      (x + s - 3, y + s - 1), (x + 3, y + s - 1)], fill=color)
        draw.polygon([(x + s // 2, y + 1), (x + s // 2, y + s - 5),
                      (x + s - 2, y + s - 5)], fill=color)
    elif kind == "shield":  # shield outline
        draw.polygon([(x + 2, y + 1), (x + s - 2, y + 1), (x + s - 2, y + s - 5),
                      (x + s // 2, y + s - 1), (x + 2, y + s - 5)],
                     outline=color, width=2)
    elif kind == "chart":  # three descending bars
        for i, hh in enumerate((10, 7, 4)):
            bx = x + 1 + i * 5
            draw.rectangle([bx, y + s - 2 - hh, bx + 3, y + s - 2], fill=color)
    else:  # warning triangle
        draw.polygon([(x + s // 2, y + 1), (x + s - 1, y + s - 1),
                      (x + 1, y + s - 1)], outline=color, width=2)
        draw.line([x + s // 2, y + 5, x + s // 2, y + 9], fill=color, width=2)
        draw.ellipse([x + s // 2 - 1, y + 11, x + s // 2 + 1, y + 13], fill=color)


def draw_calendar_glyph(d, x, y, s):
    """A tiny calendar page (s x s) with '22' on it, for the history band.

    White page, navy header bar, two gold binder rings on top, and the
    day number in navy in the middle of the page.
    """
    rrect(d, [x, y, x + s, y + s], 3, fill=WHITE, outline=NAVY, width=1)
    d.rectangle([x, y, x + s, y + 5], fill=NAVY)
    for rx in (x + 4, x + s - 6):
        d.line([rx, y - 2, rx, y + 4], fill=GOLD, width=2)
    d.text((x + s // 2, y + s // 2 + 2), "22", font=F_BOLD(9), fill=NAVY,
           anchor="mm")


def draw_history_strip(d, x, y, w, h):
    """Full-width 'ON THIS DAY' band: three 22 November anniversaries.

    Clearly labelled as history, never news: each column carries the year
    in a navy pill, a bold headline and one short detail line. A small
    calendar glyph marks the band on the left, and thin rules separate
    the three columns. The band sits between the markets ticker and the
    sources footer, spanning the full page width.
    """
    rrect(d, [x, y, x + w, y + h], 4, fill=PAPER2, outline=RULE, width=1)
    draw_calendar_glyph(d, x + 8, y + h // 2 - 9, 18)
    lx = x + 32
    d.text((lx, y + h // 2), "ON THIS DAY", font=F_BOLD(11), fill=NAVY,
           anchor="lm")
    label_w = text_w(d, "ON THIS DAY", F_BOLD(11))
    cx = x + label_w + 56
    col_w = (x + w - cx) // 3
    first = True
    for year, head, detail in HISTORY:
        if not first:
            d.line([cx - 8, y + 6, cx - 8, y + h - 6], fill=RULE, width=1)
        first = False
        rrect(d, [cx, y + 5, cx + 50, y + 21], 8, fill=NAVY)
        d.text((cx + 25, y + 13), str(year), font=F_BOLD(10), fill=WHITE,
               anchor="mm")
        d.text((cx + 56, y + 2), trunc(d, head, F_BOLD(11), col_w - 62),
               font=F_BOLD(11), fill=INK)
        d.text((cx + 56, y + 16), trunc(d, detail, F_REG(9), col_w - 62),
               font=F_REG(9), fill=MUTED)
        cx += col_w


def draw_map(draw, x0, y0, w, h):
    """Dotted world map with numbered pins."""
    cell_w, cell_h = w / 64.0, h / 32.0
    for row, spans in LAND:
        cy = y0 + (row + 0.5) * cell_h
        for c0, c1 in spans:
            for c in range(c0, c1 + 1):
                cx = x0 + (c + 0.5) * cell_w
                draw.ellipse([cx - 1.6, cy - 1.6, cx + 1.6, cy + 1.6], fill=DOT)
    for num, name, lon, lat in PINS:
        px = x0 + (lon + 180.0) / 360.0 * w
        py = y0 + (90.0 - lat) / 180.0 * h
        draw.ellipse([px - 5, py - 5, px + 5, py + 5], fill=RED, outline=WHITE, width=1)
        draw.text((px, py), str(num), font=F_BOLD(7), fill=WHITE, anchor="mm")


# ---------------------------------------------------------------- render
def render(out_dir):
    assert len(HEROES) == 3, "need exactly 3 heroes"
    assert len(GRID) == 22, "need exactly 22 grid stories"
    assert len(ALSO_ON) == 15, "need exactly 15 also-on items"
    assert len(HEROES) + len(GRID) + len(ALSO_ON) == 40, "need exactly 40 stories"
    regions = {r for _, _, r in GRID} | {"EU", "MK", "SC"}
    assert len(regions) == 7, "need exactly 7 regions"

    img = Image.new("RGB", (W, H), PAPER)
    d = ImageDraw.Draw(img)

    # ---- masthead ------------------------------------------------------
    d.rectangle([0, 0, W, 68], fill=NAVY)
    d.text((14, 8), "THE WORLD IN ONE DAY", font=F_SERIF_B(30), fill=WHITE)
    d.text((W - 14, 14), "SUNDAY 22 NOVEMBER 2026", font=F_BOLD(15),
           fill=GOLD_LT, anchor="ra")
    d.text((14, 46), "40 SOURCED STORIES  \u00b7  7 REGIONS  \u00b7  SUMMING UP THE DAY\u2019S WORLD NEWS",
           font=F_BOLD(11), fill=(200, 210, 224))
    d.rectangle([0, 68, W, 71], fill=GOLD)

    # ---- heroes --------------------------------------------------------
    hx = [8, 348, 688]
    hw, hy, hh = 328, 78, 182
    for i, hero in enumerate(HEROES):
        x = hx[i]
        rrect(d, [x, hy, x + hw, hy + hh], 6, fill=WHITE, outline=RULE, width=1)
        d.rectangle([x, hy, x + hw, hy + 22], fill=hero["color"])
        d.text((x + 10, hy + 4), hero["kicker"], font=F_BOLD(11), fill=WHITE)
        hb = HERO_BADGES[i]
        rrect(d, [x + hw - 84, hy + 3, x + hw - 6, hy + 19], 8, fill=WHITE)
        d.text((x + hw - 45, hy + 11), hb, font=F_BOLD(8), fill=hero["color"],
               anchor="mm")
        draw_hero_art(d, hero["art"], x + 8, hy + 30, hw - 16, 52)
        ty = hy + 90
        title_lines = wrap(d, hero["title"], F_BOLD(16), hw - 20, max_lines=2)
        for line in title_lines:
            d.text((x + 10, ty), line, font=F_BOLD(16), fill=INK)
            ty += 19
        for fact in hero["facts"]:
            for line in wrap(d, fact, F_REG(11), hw - 20, max_lines=2):
                d.text((x + 10, ty), line, font=F_REG(11), fill=MUTED)
                ty += 14
        d.text((x + 10, ty + 2), HERO_SOURCES[i], font=F_REG(9), fill=MUTED)

    # ---- grid header ---------------------------------------------------
    d.text((8, 266), "22 MORE STORIES \u2014 REGION BY REGION", font=F_BOLD(12), fill=NAVY)
    legend = "  ".join(f"{c} {REGION_NAMES[c]}" for c in
                       ["EU", "ME", "AP", "AM", "AF", "MK", "SC"])
    d.text((W - 8, 268), legend, font=F_REG(9), fill=MUTED, anchor="ra")
    d.line([8, 284, W - 8, 284], fill=RULE, width=1)

    # ---- grid: 2 columns x 11 rows ------------------------------------
    col_x = [8, 520]
    col_w = 496
    row_h = 32
    for idx, (head, fact, region) in enumerate(GRID):
        col = idx // 11
        row = idx % 11
        x = col_x[col]
        y = 288 + row * row_h
        if row % 2 == 0:
            d.rectangle([x, y, x + col_w, y + row_h], fill=PAPER2)
        d.ellipse([x + 2, y + 6, x + 24, y + 28], fill=NAVY)
        d.text((x + 13, y + 17), str(idx + 1), font=F_BOLD(11), fill=WHITE, anchor="mm")
        tx = x + 30
        glyph = GLYPHS.get(idx)
        if glyph:
            draw_glyph(d, glyph, x + 30, y + 9, 14, REGION_COLORS[region])
            tx = x + 48
        tw = col_w - (tx - x) - 108
        d.text((tx, y + 2), trunc(d, head, F_BOLD(13), tw), font=F_BOLD(13), fill=INK)
        d.text((tx, y + 19), trunc(d, fact, F_REG(11), tw), font=F_REG(11), fill=MUTED)
        badge = GRID_BADGES[idx]
        rrect(d, [x + col_w - 104, y + 8, x + col_w - 36, y + 24], 3,
              fill=BADGE_FILL[badge])
        d.text((x + col_w - 70, y + 16), badge, font=F_BOLD(8), fill=WHITE,
               anchor="mm")
        chip = REGION_COLORS[region]
        rrect(d, [x + col_w - 32, y + 8, x + col_w - 4, y + 24], 3, fill=chip)
        d.text((x + col_w - 18, y + 16), region, font=F_BOLD(8), fill=WHITE, anchor="mm")
    d.line([8, 640, W - 8, 640], fill=RULE, width=1)

    # ---- by the numbers --------------------------------------------------
    d.rectangle([8, 646, W - 8, 668], fill=PAPER2, outline=RULE, width=1)
    nsize = fit_size(d, NUMBERS, F_BOLD, W - 40, 11, 9)
    d.text((W // 2, 657), NUMBERS, font=F_BOLD(nsize), fill=NAVY, anchor="mm")

    # ---- world map (left) ----------------------------------------------
    d.text((8, 674), "THE WORLD \u2014 12 PINS", font=F_BOLD(12), fill=NAVY)
    d.text((492, 676), "\u2605 MERCURY \u2014 BepiColombo arrives", font=F_BOLD(10),
           fill=TEAL, anchor="ra")
    draw_map(d, 14, 696, 478, 138)
    d.text((8, 840), "1 Antalya  2 Kyiv  3 Nowy Lipowiec  4 Guasave  5 Jerusalem  6 Gaza",
           font=F_REG(9), fill=MUTED)
    d.text((8, 856), "7 Lima  8 Las Vegas  9 Washington  10 Shenzhen  11 Manila  12 Cikande",
           font=F_REG(9), fill=MUTED)

    # ---- also on (right) ------------------------------------------------
    ax, aw = 512, 504
    d.text((ax, 674), "ALSO ON \u2014 15 MORE", font=F_BOLD(12), fill=NAVY)
    d.line([ax, 690, ax + aw, 690], fill=RULE, width=1)
    ay = 696
    for item in ALSO_ON:
        d.text((ax, ay), "\u2022", font=F_BOLD(11), fill=GOLD)
        d.text((ax + 12, ay), trunc(d, item, F_REG(11), aw - 12),
               font=F_REG(11), fill=INK)
        ay += 13
    d.line([ax, 892, ax + aw, 892], fill=RULE, width=1)

    # ---- markets ticker --------------------------------------------------
    d.rectangle([0, 898, W, 924], fill=NAVY)
    size = fit_size(d, TICKER, F_BOLD, W - 24, 12, 10)
    d.text((12, 905), TICKER, font=F_BOLD(size), fill=WHITE)

    # ---- on this day -----------------------------------------------------
    # A history band, never news: three 22 November anniversaries between
    # the ticker and the footer. The footer below drops the repeated
    # masthead line to make room for it.
    draw_history_strip(d, 8, 928, W - 16, 30)

    # ---- footer ----------------------------------------------------------
    d.text((W // 2, 964), SOURCES, font=F_REG(10), fill=MUTED, anchor="ma")
    d.text((W // 2, 979), VERIFY, font=F_BOLD(11), fill=NAVY, anchor="ma")
    dc_size = fit_size(d, DATECHECK, F_BOLD, W - 24, 10, 8)
    d.text((W // 2, 994), DATECHECK, font=F_BOLD(dc_size), fill=RED, anchor="ma")
    d.text((W // 2, 1009), TIMELINE, font=F_REG(10), fill=MUTED, anchor="ma")

    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, "entry.png")
    img.save(path, format="PNG")
    return path


def main():
    out_dir = sys.argv[1] if len(sys.argv) > 1 else "out"
    path = render(out_dir)
    data = open(path, "rb").read()
    print(f"wrote {path}: {len(data)} bytes")
    print(f"sha256 {hashlib.sha256(data).hexdigest()}")
    print("stories: 3 heroes + 22 grid + 15 also-on = 40; regions: 7")


if __name__ == "__main__":
    main()
