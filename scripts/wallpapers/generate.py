"""Génère les fonds d'écran intégrés (Nature, Abstrait, Minimaliste, IT), en clair et en sombre.

Illustrations vectorielles originales, rendues en WebP haute définition.
Usage : python generate.py <dossier_sortie>   (dépendances : resvg-py, pillow, numpy)
"""

import math
import random
import sys
from io import BytesIO
from pathlib import Path

import numpy as np
import resvg_py
from PIL import Image

W, H = 2560, 1440


# ---------------------------------------------------------------- outils
def svg(defs: str, body: str) -> str:
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">'
        f"<defs>{defs}</defs>{body}</svg>"
    )


def lin(gid: str, stops: list[tuple[float, str, float]], x1=0, y1=0, x2=0, y2=1) -> str:
    s = "".join(f'<stop offset="{o}" stop-color="{c}" stop-opacity="{a}"/>' for o, c, a in stops)
    return f'<linearGradient id="{gid}" x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}">{s}</linearGradient>'


def rad(gid: str, cx: float, cy: float, r: float, stops: list[tuple[float, str, float]]) -> str:
    s = "".join(f'<stop offset="{o}" stop-color="{c}" stop-opacity="{a}"/>' for o, c, a in stops)
    return f'<radialGradient id="{gid}" cx="{cx}" cy="{cy}" r="{r}" gradientUnits="userSpaceOnUse">{s}</radialGradient>'


def blur(fid: str, sd: float) -> str:
    return f'<filter id="{fid}" x="-30%" y="-30%" width="160%" height="160%"><feGaussianBlur stdDeviation="{sd}"/></filter>'


def poly(points: list[tuple[float, float]]) -> str:
    return "M" + " L".join(f"{x:.1f},{y:.1f}" for x, y in points)


def ridge(rng: random.Random, base: float, amp: float, rough: float, n: int = 220, peaks: int = 3) -> list[tuple[float, float]]:
    """Ligne de crête : grandes ondulations + détail fractal."""
    phases = [rng.uniform(0, 6.28) for _ in range(6)]
    freqs = [rng.uniform(0.6, 1.2) * peaks, rng.uniform(2, 3.5) * peaks, rng.uniform(5, 8) * peaks]
    pts = []
    for i in range(n + 1):
        x = W * i / n
        t = x / W
        y = base
        y -= amp * (0.6 * math.sin(t * freqs[0] * 3.14 + phases[0]) + 0.4) ** 2
        y -= amp * 0.25 * math.sin(t * freqs[1] * 3.14 + phases[1])
        y -= rough * math.sin(t * freqs[2] * 3.14 + phases[2]) + rough * 0.6 * rng.uniform(-1, 1)
        pts.append((x, y))
    return pts


def area(pts: list[tuple[float, float]], bottom: float = H) -> str:
    return poly(pts) + f" L{W},{bottom} L0,{bottom} Z"


def pine(x: float, y: float, h: float, color: str, rng: random.Random, opacity: float = 1) -> str:
    """Sapin stylisé : étages de branches dentelées."""
    w = h * 0.34
    tiers = 6
    pts = [(x, y - h)]
    for k in range(1, tiers + 1):
        ty = y - h + h * k / tiers * 0.92
        tw = w * (k / tiers) * rng.uniform(0.85, 1.1)
        pts.append((x + tw, ty))
        pts.append((x + tw * 0.35, ty - h * 0.03))
    right = pts
    left = [(2 * x - px, py) for px, py in reversed(right[1:])]
    trunk = f'<rect x="{x - w * 0.05:.1f}" y="{y - h * 0.09:.1f}" width="{w * 0.1:.1f}" height="{h * 0.09:.1f}" fill="{color}"/>'
    return f'<path d="{poly(right + left)} Z" fill="{color}" opacity="{opacity}"/>' + trunk


def stars(rng: random.Random, n: int, ymax: float, color: str = "#ffffff") -> str:
    out = []
    for _ in range(n):
        x, y = rng.uniform(0, W), rng.uniform(0, ymax)
        r = rng.choice([0.8, 1, 1.2, 1.5, 2.2])
        a = rng.uniform(0.25, 0.9) * (1 - y / ymax * 0.6)
        out.append(f'<circle cx="{x:.0f}" cy="{y:.0f}" r="{r}" fill="{color}" opacity="{a:.2f}"/>')
    return "".join(out)


def moon(cx: float, cy: float, r: float) -> tuple[str, str]:
    defs = rad("moonGlow", cx, cy, r * 6, [(0, "#dfe6ff", 0.55), (0.25, "#9fb2ff", 0.18), (1, "#9fb2ff", 0)])
    defs += rad("moonFace", cx - r * 0.3, cy - r * 0.3, r * 1.4, [(0, "#ffffff", 1), (0.7, "#e7ebf7", 1), (1, "#c9d1e8", 1)])
    body = (
        f'<circle cx="{cx}" cy="{cy}" r="{r * 6}" fill="url(#moonGlow)"/>'
        f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="url(#moonFace)"/>'
        f'<circle cx="{cx + r * 0.25}" cy="{cy - r * 0.15}" r="{r * 0.18}" fill="#c3cbe2" opacity="0.5"/>'
        f'<circle cx="{cx - r * 0.3}" cy="{cy + r * 0.25}" r="{r * 0.12}" fill="#c3cbe2" opacity="0.45"/>'
        f'<circle cx="{cx - r * 0.1}" cy="{cy - r * 0.4}" r="{r * 0.09}" fill="#c3cbe2" opacity="0.4"/>'
    )
    return defs, body


def mist(rng: random.Random, y: float, color: str, opacity: float, n: int = 4, fid: str = "mist") -> str:
    out = []
    for _ in range(n):
        cx = rng.uniform(0, W)
        out.append(
            f'<ellipse cx="{cx:.0f}" cy="{y + rng.uniform(-30, 30):.0f}" rx="{rng.uniform(500, 1100):.0f}" '
            f'ry="{rng.uniform(35, 80):.0f}" fill="{color}" opacity="{opacity * rng.uniform(0.6, 1):.2f}" filter="url(#{fid})"/>'
        )
    return "".join(out)


# ---------------------------------------------------------------- Nature
def nature(dark: bool) -> str:
    rng = random.Random(11)
    if dark:
        sky = [(0, "#081232", 1), (0.45, "#15285a", 1), (0.62, "#25396e", 1), (1, "#2c3f74", 1)]
        ranges = ["#2a3d73", "#1e2f60", "#16244d", "#0f1b3c"]
        water = [(0, "#2a3e73", 1), (1, "#0d1738", 1)]
        mist_c, mist_a, ground, tree = "#8ea4dd", 0.18, "#0b1430", "#070d22"
    else:
        sky = [(0, "#7fa3e0", 1), (0.32, "#b8c5ec", 1), (0.5, "#f1d3d4", 1), (0.6, "#fbd9b0", 1), (1, "#fbd9b0", 1)]
        ranges = ["#9aa6d2", "#7d8fc2", "#58708f", "#3e5a5a"]
        water = [(0, "#c9cbe6", 1), (0.5, "#a3b1dc", 1), (1, "#7d92c8", 1)]
        mist_c, mist_a, ground, tree = "#ffffff", 0.5, "#5d6b3a", "#2c3f33"
    horizon = 760
    defs = lin("sky", sky) + lin("water", water) + blur("mist", 38) + blur("soft", 6) + blur("glow", 60)
    body = f'<rect width="{W}" height="{H}" fill="url(#sky)"/>'
    if dark:
        body += stars(rng, 260, 700)
        d, b = moon(1880, 260, 62)
        defs += d
        body += b
    else:
        defs += rad("sun", 1780, horizon - 90, 900, [(0, "#fff6d8", 1), (0.06, "#ffe3a3", 0.95), (0.25, "#ffc98a", 0.35), (1, "#ffc98a", 0)])
        body += f'<rect width="{W}" height="{H}" fill="url(#sun)"/>'
        body += f'<circle cx="1780" cy="{horizon - 90}" r="46" fill="#fffbe9"/>'
        for k in range(5):  # nuages fins
            body += (f'<ellipse cx="{rng.uniform(200, 2400):.0f}" cy="{rng.uniform(120, 420):.0f}" rx="{rng.uniform(260, 520):.0f}" '
                     f'ry="{rng.uniform(14, 30):.0f}" fill="#ffffff" opacity="0.35" filter="url(#soft)"/>')
    # Chaînes de montagnes, de la plus lointaine à la plus proche
    bases = [horizon - 40, horizon + 10, horizon + 70, horizon + 120]
    amps = [300, 230, 170, 120]
    for i, (base, amp, col) in enumerate(zip(bases, amps, ranges, strict=True)):
        pts = ridge(rng, base, amp, 6 + i * 3, peaks=2 + i)
        body += f'<path d="{area(pts)}" fill="{col}" opacity="{0.85 if i == 0 else 1}"/>'
        body += mist(rng, base + 20, mist_c, mist_a * (0.9 - i * 0.12), n=4)
    # Lac
    lake_top = horizon + 150
    body += (f'<path d="M0,{lake_top + 60} C600,{lake_top - 10} 1300,{lake_top + 40} 2000,{lake_top} '
             f'S2560,{lake_top + 30} 2560,{lake_top + 30} L2560,{H} L0,{H} Z" fill="url(#water)"/>')
    refl = "#fff2c8" if not dark else "#dfe6ff"
    rx = 1780 if not dark else 1880
    for k in range(9):
        body += (f'<rect x="{rx - 120 + rng.uniform(-40, 40):.0f}" y="{lake_top + 40 + k * 34}" width="{rng.uniform(120, 260):.0f}" '
                 f'height="5" rx="2.5" fill="{refl}" opacity="{0.55 - k * 0.05:.2f}" filter="url(#soft)"/>')
    if dark:  # quelques lumières de village sur la rive
        for _ in range(9):
            x = rng.uniform(1500, 2300)
            body += f'<circle cx="{x:.0f}" cy="{lake_top + rng.uniform(0, 20):.0f}" r="3" fill="#ffc46b" opacity="0.9"/>'
    body += mist(rng, lake_top + 50, mist_c, mist_a * 0.7, n=5)
    # Rive boisée à droite (presqu'île)
    shore_top, shore_bot = ("#4d6e57", "#2a4233") if not dark else ("#17244a", "#0b1430")
    defs += lin("shore", [(0, shore_top, 1), (1, shore_bot, 1)])
    body += (f'<path d="M1180,{H} C1250,{lake_top + 300} 1500,{lake_top + 190} 1850,{lake_top + 150} '
             f'C2150,{lake_top + 118} 2400,{lake_top + 95} 2560,{lake_top + 88} L2560,{H} Z" fill="url(#shore)"/>')
    for _ in range(90):
        x = rng.uniform(1320, 2560)
        t = (x - 1320) / 1240
        y = lake_top + 300 - t * 200 + rng.uniform(0, 60)
        body += pine(x, y, rng.uniform(80, 170) * (1.2 - t * 0.4), tree, rng, 0.95)
    # Premier plan : prairie en pente, rochers ombrés, grands sapins
    g_top, g_bot = ("#d9c35c", "#6f7d35") if not dark else ("#1d2b55", "#0a1330")
    defs += lin("grass", [(0, g_top, 1), (1, g_bot, 1)])
    body += (f'<path d="M0,{H - 380} C260,{H - 360} 520,{H - 300} 820,{H - 210} C1040,{H - 140} 1220,{H - 60} 1340,{H} '
             f'L0,{H} Z" fill="url(#grass)"/>')
    r_top, r_bot = ("#c9ccd3", "#6d727d") if not dark else ("#3a4a7a", "#141d3d")
    defs += lin("rock", [(0, r_top, 1), (1, r_bot, 1)])
    hl = "#e4e6ec" if not dark else "#5a6ca3"
    for cx, cy, rx, ry in [(430, H - 175, 170, 85), (650, H - 120, 120, 62), (250, H - 95, 95, 48), (900, H - 60, 90, 40)]:
        # Rocher anguleux : demi-contour irrégulier + facette éclairée
        n = 9
        pts = []
        for k in range(n + 1):
            a = math.pi * k / n
            jitter = rng.uniform(0.78, 1.08)
            pts.append((cx - rx * math.cos(a) * jitter, cy + ry * 0.55 - ry * 1.35 * math.sin(a) * jitter))
        body += f'<path d="{poly(pts)} Z" fill="url(#rock)"/>'
        facet = [pts[1], pts[2], pts[3], pts[4], (cx - rx * 0.05, cy - ry * 0.1), (cx - rx * 0.55, cy + ry * 0.15)]
        body += f'<path d="{poly(facet)} Z" fill="{hl}" opacity="0.45"/>'
    for x, y, h in [(110, H - 330, 420), (250, H - 310, 330), (2380, H - 40, 470), (2510, H - 20, 380), (2240, H - 10, 300)]:
        body += pine(x, y, h, tree, rng)
    return svg(defs, body)


# ---------------------------------------------------------------- Abstrait
def ribbon(y0: float, amp: float, wl: float, ph: float, thick: float, tph: float, n: int = 240) -> str:
    top, bot = [], []
    for i in range(n + 1):
        x = -100 + (W + 200) * i / n
        y = y0 + amp * math.sin(2 * math.pi * x / wl + ph)
        t = thick * (0.15 + 0.85 * abs(math.sin(2 * math.pi * x / (wl * 1.3) + tph)))
        top.append((x, y))
        bot.append((x, y + t))
    return poly(top + list(reversed(bot))) + " Z", poly(top)


def abstract(dark: bool) -> str:
    if dark:
        bg = [(0, "#050a2a", 1), (0.5, "#0b1660", 1), (1, "#101a52", 1)]
        cols = ["#3b5bff", "#6d4dff", "#2f8bff", "#a05cff", "#4a6dff"]
        edge, edge_a, fill_a = "#9fb6ff", 0.7, 0.42
    else:
        bg = [(0, "#9ec0f6", 1), (0.55, "#c8c6f4", 1), (1, "#e6c9f2", 1)]
        cols = ["#ffffff", "#c4b1ff", "#a6c4ff", "#ffc2e4", "#ffffff"]
        edge, edge_a, fill_a = "#ffffff", 0.9, 0.5
    defs = lin("bg", bg, 0, 0, 1, 1) + blur("bloom", 26) + blur("soft", 4) + blur("far", 14)
    glow1 = "#7a5cff" if dark else "#ffffff"
    glow2 = "#3fa0ff" if dark else "#ffd6ec"
    defs += rad("g1", 1800, 300, 900, [(0, glow1, 0.45), (1, glow1, 0)])
    defs += rad("g2", 500, 1200, 900, [(0, glow2, 0.4), (1, glow2, 0)])
    body = f'<rect width="{W}" height="{H}" fill="url(#bg)"/><rect width="{W}" height="{H}" fill="url(#g1)"/><rect width="{W}" height="{H}" fill="url(#g2)"/>'
    specs = [
        (520, 220, 2300, 0.4, 260, 0.3, "far"),
        (760, 260, 2600, 1.6, 300, 1.2, None),
        (900, 300, 3000, 2.6, 220, 2.1, None),
        (640, 180, 2000, 3.4, 160, 0.8, "soft"),
        (1050, 240, 2700, 4.4, 260, 2.8, None),
    ]
    for i, (y0, amp, wl, ph, th, tph, flt) in enumerate(specs):
        col = cols[i % len(cols)]
        defs += lin(f"r{i}", [(0, col, fill_a * 0.2), (0.45, col, fill_a), (1, col, fill_a * 0.1)], 0, 0, 1, 0.3)
        area_d, edge_d = ribbon(y0, amp, wl, ph, th, tph)
        f = f' filter="url(#{flt})"' if flt else ""
        body += f'<path d="{area_d}" fill="url(#r{i})"{f}/>'
        if dark:
            body += f'<path d="{edge_d}" fill="none" stroke="{col}" stroke-width="10" opacity="0.5" filter="url(#bloom)"/>'
        body += f'<path d="{edge_d}" fill="none" stroke="{edge}" stroke-width="2.2" opacity="{edge_a}"{f}/>'
    return svg(defs, body)


# ---------------------------------------------------------------- Minimaliste (dunes)
def dune(rng: random.Random, base: float, amp: float, wl: float, ph: float, skew: float) -> list[tuple[float, float]]:
    pts = []
    for i in range(241):
        x = -50 + (W + 100) * i / 240
        s = math.sin(2 * math.pi * x / wl + ph)
        y = base - amp * (s + skew * math.sin(4 * math.pi * x / wl + ph)) * 0.5 - amp * 0.5
        pts.append((x, y))
    return pts


def minimal(dark: bool) -> str:
    rng = random.Random(5)
    if dark:
        sky = [(0, "#0a1230", 1), (0.6, "#1b2a5a", 1), (1, "#25356a", 1)]
        layers = [("#2a3a70", "#1a2652"), ("#24336a", "#141f47"), ("#1d2b5e", "#0f193d"), ("#17234f", "#0b1433"), ("#121c42", "#08102a")]
        crest, crest_a = "#a9bdf2", 0.55
    else:
        sky = [(0, "#f6e7dd", 1), (0.45, "#fbe9d8", 1), (0.62, "#fde6cf", 1), (1, "#f3dccb", 1)]
        layers = [("#f4e6d8", "#e2cdb9"), ("#f1e0cf", "#dac1aa"), ("#eed9c4", "#d0b398"), ("#ebd2ba", "#c5a487"), ("#e8cbb0", "#b99677")]
        crest, crest_a = "#fffaf3", 0.85
    defs = lin("sky", sky) + blur("soft", 3) + blur("haze", 30)
    body = f'<rect width="{W}" height="{H}" fill="url(#sky)"/>'
    if dark:
        body += stars(rng, 220, 760)
        d, b = moon(2020, 230, 58)
        defs += d
        body += b
    else:
        defs += rad("sun", 1550, 700, 1000, [(0, "#fff8e8", 1), (0.08, "#ffeccc", 0.85), (0.35, "#ffdcb8", 0.3), (1, "#ffdcb8", 0)])
        body += f'<rect width="{W}" height="{H}" fill="url(#sun)"/><circle cx="1550" cy="700" r="34" fill="#fffdf6" opacity="0.95"/>'
    specs = [(760, 120, 2600, 0.5, 0.35), (860, 160, 2200, 2.1, 0.4), (980, 200, 2900, 3.9, 0.3), (1130, 220, 2400, 1.2, 0.45), (1300, 240, 3100, 5.0, 0.35)]
    for i, ((top, bottom), (base, amp, wl, ph, skew)) in enumerate(zip(layers, specs, strict=True)):
        pts = dune(rng, base, amp, wl, ph, skew)
        defs += lin(f"d{i}", [(0, top, 1), (1, bottom, 1)])
        body += f'<path d="{area(pts)}" fill="url(#d{i})"/>'
        body += f'<path d="{poly(pts)}" fill="none" stroke="{crest}" stroke-width="{2 + i * 0.6:.1f}" opacity="{crest_a - i * 0.06:.2f}" filter="url(#soft)"/>'
        if i < 2:
            body += f'<rect y="{base - amp - 40}" width="{W}" height="160" fill="{layers[0][0]}" opacity="0.35" filter="url(#haze)"/>'
    return svg(defs, body)


# ---------------------------------------------------------------- IT
def it(dark: bool) -> str:
    rng = random.Random(23)
    if dark:
        bg = [(0, "#06102a", 1), (0.6, "#0d1f4a", 1), (1, "#0a1838", 1)]
        rack, rack_a, led_cols, node, line, line_a = "#0c1a3c", 0.95, ["#3d8bff", "#5fb0ff", "#2f6bff", "#ffb347"], "#7cc4ff", "#3f8cff", 0.55
    else:
        bg = [(0, "#e3e6f6", 1), (0.5, "#dfe3f6", 1), (1, "#c9d4f0", 1)]
        rack, rack_a, led_cols, node, line, line_a = "#5f6f99", 0.35, ["#3f7bff", "#5c95ff", "#ff9f3a"], "#ffffff", "#8ea6ea", 0.8
    defs = lin("bg", bg) + blur("glow", 8) + blur("fog", 40) + blur("rackblur", 1.4) + blur("bloom", 18)
    warm = "#ffe2c4" if not dark else "#2b5cff"
    defs += rad("warm", 900, 760, 1100, [(0, warm, 0.55 if not dark else 0.25), (1, warm, 0)])
    body = f'<rect width="{W}" height="{H}" fill="url(#bg)"/><rect width="{W}" height="{H}" fill="url(#warm)"/>'
    # Baies de serveurs en perspective (côté droit)
    r_top, r_bot = ("#8796c8", "#6474aa") if not dark else ("#10224b", "#071430")
    defs += lin("rack", [(0, r_top, 1), (1, r_bot, 1)], 0, 0, 1, 0)
    for k in range(6):
        x = 1480 + k * 182
        top = 110 + k * 12
        hgt = 1010 - k * 24
        g = f'<g opacity="{0.9 if not dark else 1}" filter="url(#rackblur)">'
        g += f'<rect x="{x}" y="{top}" width="156" height="{hgt}" rx="6" fill="url(#rack)"/>'
        g += f'<rect x="{x}" y="{top}" width="3" height="{hgt}" fill="{"#ffffff" if not dark else "#3d6fe0"}" opacity="0.45"/>'
        for r in range(int((hgt - 50) / 26)):
            for c in range(3):
                if rng.random() < 0.55:
                    col = rng.choice(led_cols)
                    g += f'<rect x="{x + 18 + c * 42}" y="{top + 30 + r * 26}" width="{rng.choice([6, 10, 18])}" height="5" rx="2.5" fill="{col}" opacity="{rng.uniform(0.6, 1):.2f}"/>'
        g += "</g>"
        body += g
        if dark:  # reflet des voyants au sol
            body += f'<rect x="{x}" y="{top + hgt + 10}" width="156" height="120" fill="#2f6bff" opacity="0.12" filter="url(#fog)"/>'
    # Brume qui fond les baies vers la gauche
    fog_c = "#e4e8f7" if not dark else "#0a1636"
    defs += lin("fogx", [(0, fog_c, 0), (0.4, fog_c, 0.75), (1, fog_c, 0)], 0, 0, 1, 0)
    body += f'<rect x="1150" y="0" width="1000" height="{H}" fill="url(#fogx)" opacity="{0.8 if not dark else 0.55}"/>'
    # Courbes lumineuses
    for i, (y0, amp, wl, ph) in enumerate([(960, 120, 2400, 0.5), (1020, 90, 1900, 2.0), (1080, 140, 2800, 3.5)]):
        _, edge_d = ribbon(y0, amp, wl, ph, 0, 0)
        if dark:
            body += f'<path d="{edge_d}" fill="none" stroke="{line}" stroke-width="10" opacity="0.35" filter="url(#bloom)"/>'
        body += f'<path d="{edge_d}" fill="none" stroke="{line}" stroke-width="2.5" opacity="{0.8 - i * 0.15:.2f}"/>'
    # Réseau de nœuds
    nodes = [(rng.uniform(0, W), rng.uniform(650, 1350)) for _ in range(70)]
    nodes += [(rng.uniform(0, 1400), rng.uniform(450, 700)) for _ in range(14)]
    for i, (x1, y1) in enumerate(nodes):
        for x2, y2 in nodes[i + 1 :]:
            dd = math.hypot(x2 - x1, y2 - y1)
            if dd < 300:
                body += f'<line x1="{x1:.0f}" y1="{y1:.0f}" x2="{x2:.0f}" y2="{y2:.0f}" stroke="{line}" stroke-width="1.4" opacity="{line_a * (1 - dd / 300):.2f}"/>'
    halo = line if not dark else node
    for x, y in nodes:
        r = rng.choice([3, 4, 5, 6])
        body += f'<circle cx="{x:.0f}" cy="{y:.0f}" r="{r * 3}" fill="{halo}" opacity="0.45" filter="url(#glow)"/>'
        body += f'<circle cx="{x:.0f}" cy="{y:.0f}" r="{r}" fill="{node}" opacity="0.95"/>'
    if dark:  # reflet au sol
        body += f'<rect y="{H - 260}" width="{W}" height="260" fill="#1b3f8f" opacity="0.25" filter="url(#fog)"/>'
    return svg(defs, body)


# ---------------------------------------------------------------- rendu
def render(svg_text: str, out: Path, thumb: Path) -> None:
    png = bytes(resvg_py.svg_to_bytes(svg_string=svg_text))
    img = Image.open(BytesIO(png)).convert("RGB")
    a = np.asarray(img).astype(np.float32)
    a += np.random.default_rng(3).normal(0, 1.6, a.shape[:2])[..., None]  # grain léger anti-paliers
    img = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))
    img.save(out, "WEBP", quality=86, method=6)
    img.resize((480, 270), Image.LANCZOS).save(thumb, "WEBP", quality=82, method=6)


def main() -> None:
    out = Path(sys.argv[1])
    (out / "thumbs").mkdir(parents=True, exist_ok=True)
    for name, fn in {"nature": nature, "abstract": abstract, "minimal": minimal, "it": it}.items():
        for mode in ("light", "dark"):
            render(fn(mode == "dark"), out / f"{name}-{mode}.webp", out / "thumbs" / f"{name}-{mode}.webp")
            print("ok", name, mode)


if __name__ == "__main__":
    main()
