"""
core.management.commands._flower_art - draws the seed profile pictures.

Each entry in PLANTS is one distinct flower or plant (name, background colour and a
drawing function). `render(name)` returns a 400x400 Pillow image of it.

The pictures are drawn with Pillow instead of being downloaded, so seeding works offline
and the project does not depend on third-party photos or their licences. Everything is
drawn at 3x size and scaled down afterwards, which gives smooth (anti-aliased) edges.

The leading underscore in the file name stops Django from treating this module as a
management command of its own.
"""
import math
import random
import re

from PIL import Image, ImageDraw

S = 1200          # working canvas (pixels); the final image is OUT x OUT
OUT = 400
C = S / 2         # centre of the canvas


# ---------------------------------------------------------------------------
# Small drawing helpers
# ---------------------------------------------------------------------------
def rgb(c):
    """'#aabbcc' -> (170, 187, 204); tuples pass straight through."""
    if isinstance(c, str):
        c = c.lstrip('#')
        return tuple(int(c[i:i + 2], 16) for i in (0, 2, 4))
    return tuple(c)


def mix(a, b, t):
    """Blend colour a towards colour b by t (0 = a, 1 = b)."""
    a, b = rgb(a), rgb(b)
    return tuple(round(a[i] + (b[i] - a[i]) * t) for i in range(3))


def lighter(c, t=0.3):
    return mix(c, '#ffffff', t)


def darker(c, t=0.3):
    return mix(c, '#000000', t)


def petal_pts(cx, cy, ang, length, width, prof='round', steps=22):
    """Outline of one petal/leaf starting at (cx, cy) and pointing along `ang` (radians)."""
    profiles = {
        'round': lambda t: math.sin(math.pi * t) ** 0.6,
        'pointed': lambda t: math.sin(math.pi * t ** 0.8) ** 0.95,
        'spoon': lambda t: math.sin(math.pi * t ** 1.4) ** 0.55,
        'leaf': lambda t: math.sin(math.pi * t) ** 0.85,
        'notched': lambda t: math.sin(math.pi * t * 0.85) ** 0.6,
    }
    f = profiles[prof]
    side = [(t * length, f(t) * width / 2) for t in (i / steps for i in range(steps + 1))]
    pts = side + [(x, -w) for x, w in reversed(side)]
    if prof == 'notched':                       # dent in the tip (cherry blossom)
        pts.insert(steps + 1, (length * 0.86, 0))
    ca, sa = math.cos(ang), math.sin(ang)
    return [(cx + x * ca - y * sa, cy + x * sa + y * ca) for x, y in pts]


def poly(d, pts, fill, edge=None, ew=4):
    d.polygon(pts, fill=rgb(fill))
    if edge is not None:
        d.line(list(pts) + [pts[0]], fill=rgb(edge), width=ew, joint='curve')


def circle(d, x, y, r, fill, edge=None, ew=4):
    d.ellipse([x - r, y - r, x + r, y + r], fill=rgb(fill),
              outline=rgb(edge) if edge is not None else None, width=ew)


def thick_line(d, pts, fill, width):
    """Polyline with round joints/ends."""
    d.line(pts, fill=rgb(fill), width=int(width), joint='curve')
    for x, y in (pts[0], pts[-1]):
        circle(d, x, y, width / 2, fill, ew=0)


def bezier(p0, p1, p2, n=40):
    return [((1 - t) ** 2 * p0[0] + 2 * (1 - t) * t * p1[0] + t * t * p2[0],
             (1 - t) ** 2 * p0[1] + 2 * (1 - t) * t * p1[1] + t * t * p2[1])
            for t in (i / n for i in range(n + 1))]


def heart_pts(cx, cy, size, point_dir):
    """Heart outline whose point faces `point_dir` (radians, image coordinates)."""
    rot = point_dir - math.pi / 2
    ca, sa = math.cos(rot), math.sin(rot)
    pts = []
    for i in range(120):
        t = 2 * math.pi * i / 120
        x = 16 * math.sin(t) ** 3
        y = -(13 * math.cos(t) - 5 * math.cos(2 * t) - 2 * math.cos(3 * t) - math.cos(4 * t))
        x, y = x * size, (y + 2) * size
        pts.append((cx + x * ca - y * sa, cy + x * sa + y * ca))
    return pts


# ---------------------------------------------------------------------------
# Radial flowers (daisy, rose, dahlia, succulent rosette, hibiscus, poppy ...)
# ---------------------------------------------------------------------------
def rings(k, L0, L1, n0, n1, wr, c0, c1, prof, edge=None, vein=None):
    """k concentric rings of petals from outermost (length L0) to innermost (L1)."""
    layers = []
    for i in range(k):
        t = i / (k - 1) if k > 1 else 0
        n = round(n0 + (n1 - n0) * t)
        L = (L0 + (L1 - L0) * t) * S
        layers.append(dict(n=n, L=L, W=L * wr, color=mix(c0, c1, t), prof=prof,
                           off=(i % 2) * 180 / n, edge=edge, vein=vein))
    return layers


def radial(d, layers, center=None, cx=C, cy=C):
    for ly in layers:
        angles = ly.get('angles')
        if angles is None:
            angles = [ly.get('off', 0) + 360 * i / ly['n'] for i in range(ly['n'])]
        for a in angles:
            a = math.radians(a)
            poly(d, petal_pts(cx, cy, a, ly['L'], ly['W'], ly.get('prof', 'round')),
                 ly['color'], ly.get('edge'), ly.get('ew', 4))
            if ly.get('vein') is not None:
                p0 = (cx + math.cos(a) * ly['L'] * 0.2, cy + math.sin(a) * ly['L'] * 0.2)
                p1 = (cx + math.cos(a) * ly['L'] * 0.8, cy + math.sin(a) * ly['L'] * 0.8)
                d.line([p0, p1], fill=rgb(ly['vein']), width=3)
    if center:
        r, col = center['r'] * S, center['color']
        circle(d, cx, cy, r, col, center.get('edge'), 5)
        if center.get('seeds'):                     # sunflower-style seed spiral
            sc = darker(col, 0.35)
            for i in range(1, 160):
                rr = r * 0.93 * math.sqrt(i / 160)
                th = i * 2.399963
                circle(d, cx + rr * math.cos(th), cy + rr * math.sin(th), r * 0.045, sc, ew=0)
        if center.get('stamens'):                   # thin filaments with tips
            n, ln, sc = center['stamens']
            for i in range(n):
                th = 2 * math.pi * i / n
                x, y = cx + math.cos(th) * ln * S, cy + math.sin(th) * ln * S
                d.line([(cx, cy), (x, y)], fill=rgb(sc), width=4)
                circle(d, x, y, 0.012 * S, sc, ew=0)
        if center.get('arm'):                       # hibiscus: one long stamen column with a dotted tip
            ex, ey = cx + 0.24 * S * math.cos(math.radians(-50)), cy + 0.24 * S * math.sin(math.radians(-50))
            thick_line(d, [(cx, cy), (ex, ey)], '#f2d9a0', 14)
            for i in range(9):
                th = 2 * math.pi * i / 9
                circle(d, ex + 0.035 * S * math.cos(th), ey + 0.035 * S * math.sin(th), 0.013 * S, '#f6c21e', ew=0)
            circle(d, ex, ey, 0.018 * S, '#c01f3d', ew=0)
        if center.get('dots'):                      # ring of dark dots (poppy)
            n, rad, dc = center['dots']
            for i in range(n):
                th = 2 * math.pi * i / n
                circle(d, cx + math.cos(th) * rad * S, cy + math.sin(th) * rad * S, 0.011 * S, dc, ew=0)


def bloom(d, kind, c, cc, **kw):
    """Convenience wrapper for the many 'face-on flower' variants."""
    edge = kw.get('edge', darker(c, 0.18))
    if kind == 'daisy':
        layers = rings(2, 0.42, 0.40, kw.get('n', 16), kw.get('n', 16), kw.get('wr', 0.28), c, kw.get('c2', c),
                       kw.get('prof', 'spoon'), edge)
        center = dict(r=kw.get('cr', 0.11), color=cc, seeds=kw.get('seeds', False),
                      edge=darker(cc, 0.2))
    elif kind == 'layered':
        layers = rings(kw.get('k', 5), kw.get('L0', 0.44), kw.get('L1', 0.12), kw.get('n0', 14), kw.get('n1', 8),
                       kw.get('wr', 0.4), c, kw.get('c2', darker(c, 0.35)), kw.get('prof', 'pointed'), edge)
        center = dict(r=kw.get('cr', 0.04), color=cc)
    elif kind == 'five':
        n = kw.get('n', 5)
        layers = [dict(n=n, L=0.42 * S, W=0.50 * S, color=c, prof='round', edge=edge, vein=darker(c, 0.15)),
                  dict(n=n, L=0.26 * S, W=0.30 * S, color=kw.get('c2', darker(c, 0.2)), prof='round',
                       off=180 / n, edge=None)]
        center = dict(r=kw.get('cr', 0.05), color=cc, stamens=kw.get('stamens'), arm=kw.get('arm'),
                      dots=(10, 0.115, '#1c1c1c') if n == 4 else None)
    else:
        raise ValueError(kind)
    radial(d, layers, center)


def rose(d, c, c_in):
    layers = rings(4, 0.43, 0.14, 5, 5, 1.0, c, c_in, 'round', darker(c, 0.25))
    radial(d, layers, dict(r=0.05, color=darker(c_in, 0.15)))
    swirl = darker(c_in, 0.35)
    for r in (0.035, 0.065, 0.095):
        d.arc([C - r * S, C - r * S, C + r * S, C + r * S], 200, 340, fill=rgb(swirl), width=5)
        d.arc([C - r * S, C - r * S, C + r * S, C + r * S], 20, 120, fill=rgb(swirl), width=5)


# ---------------------------------------------------------------------------
# Other plant shapes
# ---------------------------------------------------------------------------
def tulip(d, c, leaf='#3f8f4f'):
    thick_line(d, [(C, 0.92 * S), (C, 0.52 * S)], darker(leaf, 0.1), 22)
    for a, col in ((-118, leaf), (-62, darker(leaf, 0.15))):
        poly(d, petal_pts(C, 0.9 * S, math.radians(a), 0.52 * S, 0.17 * S, 'leaf'), col, darker(col, 0.2))
    base = 0.58 * S
    for a, col in ((-106, darker(c, 0.2)), (-74, darker(c, 0.2)), (-90, c)):
        poly(d, petal_pts(C, base, math.radians(a), 0.40 * S, 0.24 * S, 'leaf'), col, darker(c, 0.35), 5)
    d.line([(C, base - 0.05 * S), (C, base - 0.34 * S)], fill=rgb(lighter(c, 0.35)), width=5)


def water_lily(d, c, pad='#3f9a67', water='#d8f0ee'):
    d.ellipse([0.08 * S, 0.60 * S, 0.92 * S, 0.92 * S], fill=rgb(pad), outline=rgb(darker(pad, 0.25)), width=5)
    d.polygon([(C, 0.76 * S), (0.98 * S, 0.62 * S), (0.98 * S, 0.80 * S)], fill=rgb(water))
    bx, by = C, 0.74 * S
    for spread, ln, shade in ((78, 0.40, 0.12), (52, 0.46, 0.08), (26, 0.50, 0.04), (0, 0.54, 0.0)):
        for sgn in ((-1, 1) if spread else (1,)):
            a = math.radians(-90 + sgn * spread)
            col = mix(c, darker(c, 0.25), shade * 2)
            poly(d, petal_pts(bx, by, a, ln * S, 0.20 * S, 'pointed'), col, darker(c, 0.3), 4)
    circle(d, bx, by - 0.03 * S, 0.035 * S, '#f5c542', ew=0)


def lavender(d, c, stem='#5d8f58'):
    tops = [(0.28, 0.14), (0.50, 0.08), (0.72, 0.14)]
    for (tx, ty), bx in zip(tops, (0.40, 0.50, 0.60)):
        pts = bezier((bx * S, 0.95 * S), (bx * S + (tx - bx) * S * 0.2, 0.55 * S), (tx * S, ty * S))
        thick_line(d, pts, stem, 12)
        for i in range(16):
            t = 0.42 + 0.58 * i / 15
            x, y = pts[int(t * 40)]
            nx, ny = pts[min(int(t * 40) + 1, 40)]
            ang = math.atan2(ny - y, nx - x)
            for sgn in (-1, 1):
                col = mix(c, lighter(c, 0.4), (i % 3) / 4)
                poly(d, petal_pts(x, y, ang + sgn * math.radians(38), 0.09 * S, 0.045 * S, 'round'),
                     col, darker(c, 0.25), 3)
        poly(d, petal_pts(*pts[-1], -math.pi / 2, 0.07 * S, 0.04 * S), c, darker(c, 0.25), 3)


def hydrangea(d, palette, name):
    rnd = random.Random(name)
    for a in (35, 145, 270):                           # leaves peeking out behind the ball
        poly(d, petal_pts(C, C, math.radians(a), 0.52 * S, 0.26 * S, 'leaf'), '#3f8a58', '#2c6b42')
    step = 0.115 * S
    for gy in range(-4, 5):
        for gx in range(-4, 5):
            x = C + gx * step + (step / 2 if gy % 2 else 0)
            y = C + gy * step * 0.88
            if math.hypot(x - C, y - C) > 0.37 * S:
                continue
            col = mix(rnd.choice(palette), '#ffffff', rnd.random() * 0.25)
            for k in range(4):
                a = math.radians(45 + 90 * k)
                poly(d, petal_pts(x, y, a, 0.075 * S, 0.075 * S, 'round'), col, darker(col, 0.2), 3)
            circle(d, x, y, 0.012 * S, lighter(col, 0.6), ew=0)


def rosette(d, c0, c1, tip=None):
    """Echeveria-style succulent: rings of thick pointed leaves."""
    layers = rings(5, 0.45, 0.10, 8, 6, 0.5, c0, c1, 'pointed', darker(c0, 0.3))
    radial(d, layers, None)
    if tip:                                              # coloured tips on the outer leaves
        for ly in layers[:2]:
            for i in range(ly['n']):
                a = math.radians(ly['off'] + 360 * i / ly['n'])
                x, y = C + math.cos(a) * ly['L'] * 0.92, C + math.sin(a) * ly['L'] * 0.92
                circle(d, x, y, 0.016 * S, tip, ew=0)


def aloe(d):
    pot_top = 0.80 * S
    for a, ln in ((-150, .50), (-30, .50), (-125, .62), (-55, .62), (-105, .68), (-75, .68), (-90, .72)):
        col = mix('#5aa86a', '#2f7a4a', abs(a + 90) / 70)
        poly(d, petal_pts(C, pot_top, math.radians(a), ln * S, 0.13 * S, 'pointed'), col, darker(col, 0.3))
        for j in range(5):
            t = 0.3 + 0.12 * j
            x, y = C + math.cos(math.radians(a)) * ln * S * t, pot_top + math.sin(math.radians(a)) * ln * S * t
            circle(d, x, y, 0.008 * S, '#d4efd3', ew=0)
    pot(d, 0.80, 0.90)


def pot(d, y0, y1, color='#c9764a'):
    d.polygon([(0.34 * S, y0 * S), (0.66 * S, y0 * S), (0.61 * S, y1 * S), (0.39 * S, y1 * S)], fill=rgb(color))
    d.rounded_rectangle([0.31 * S, (y0 - 0.025) * S, 0.69 * S, (y0 + 0.03) * S], 12, fill=rgb(darker(color, 0.12)))


def saguaro(d, flower='#f07fa8'):
    g, gd = '#4f9a62', '#2f7048'
    d.rounded_rectangle([0.27 * S, 0.50 * S, 0.50 * S, 0.60 * S], 40, fill=rgb(g))
    d.rounded_rectangle([0.27 * S, 0.34 * S, 0.36 * S, 0.60 * S], 40, fill=rgb(g))
    d.rounded_rectangle([0.50 * S, 0.44 * S, 0.73 * S, 0.54 * S], 40, fill=rgb(g))
    d.rounded_rectangle([0.64 * S, 0.28 * S, 0.73 * S, 0.54 * S], 40, fill=rgb(g))
    d.rounded_rectangle([0.41 * S, 0.18 * S, 0.59 * S, 0.80 * S], 70, fill=rgb(g))
    for x in (0.455, 0.5, 0.545):
        d.line([(x * S, 0.24 * S), (x * S, 0.78 * S)], fill=rgb(gd), width=5)
    for x in (0.315, 0.685):
        d.line([(x * S, 0.38 * S), (x * S, 0.56 * S if x < .5 else 0.50 * S)], fill=rgb(gd), width=5)
    rnd = random.Random(7)
    for _ in range(46):
        x, y = rnd.uniform(0.43, 0.57) * S, rnd.uniform(0.24, 0.78) * S
        d.line([(x, y), (x + rnd.uniform(-14, 14), y - 16)], fill=rgb('#f4f0cf'), width=3)
    for dx in (-0.025, 0.025):
        poly(d, petal_pts(C + dx * S, 0.19 * S, math.radians(-90 + dx * 1600), 0.09 * S, 0.06 * S, 'round'),
             flower, darker(flower, 0.25), 3)
    pot(d, 0.78, 0.90)


def barrel_cactus(d, flower='#f6c445'):
    g, gd = '#69a85c', '#3d7a3f'
    d.ellipse([0.26 * S, 0.30 * S, 0.74 * S, 0.80 * S], fill=rgb(g), outline=rgb(gd), width=6)
    for k in (-0.17, -0.09, 0.0, 0.09, 0.17):
        d.line([((0.5 + k * 0.4) * S, 0.31 * S), ((0.5 + k * 1.35) * S, 0.55 * S), ((0.5 + k * 0.4) * S, 0.79 * S)],
               fill=rgb(gd), width=5, joint='curve')
        for j in range(5):
            x = (0.5 + k * (0.4 + 0.95 * math.sin(math.pi * (0.2 + j * 0.15)))) * S
            y = (0.35 + j * 0.09) * S
            d.line([(x - 12, y), (x + 12, y)], fill=rgb('#f4f0cf'), width=4)
            d.line([(x, y - 12), (x, y + 12)], fill=rgb('#f4f0cf'), width=4)
    for a in range(0, 360, 45):
        poly(d, petal_pts(C, 0.30 * S, math.radians(a), 0.07 * S, 0.045 * S, 'pointed'), flower, darker(flower, 0.25), 3)
    pot(d, 0.76, 0.90)


def fern(d, c0, c1, bend=0.0, flip=False):
    x0, y0 = 0.5 * S, 0.92 * S
    rach = bezier((x0, y0), (x0 + (-0.30 + bend) * S, 0.50 * S), (x0 + (0.14 + bend / 2) * S, 0.10 * S), 60)
    if flip:
        rach = [(S - x, y) for x, y in rach]
    thick_line(d, rach, darker(c0, 0.25), 10)
    for i in range(4, 58, 3):
        t = i / 60
        x, y = rach[i]
        nx, ny = rach[i + 1]
        ang = math.atan2(ny - y, nx - x)
        ln = (0.04 + 0.22 * (1 - t) ** 0.7) * S
        col = mix(c0, c1, t)
        for sgn in (-1, 1):
            poly(d, petal_pts(x, y, ang + sgn * math.radians(62), ln, ln * 0.30, 'leaf', 12), col, darker(col, 0.2), 3)


def monstera(d, bg):
    g, gd = '#2f8a4f', '#1f6338'
    cx, cy = C, 0.55 * S
    poly(d, heart_pts(cx, cy, 0.026 * S, math.pi / 2), g, gd, 6)
    d.line([(cx, cy - 0.12 * S), (cx, 0.90 * S)], fill=rgb(lighter(g, 0.35)), width=8)
    for a in (-38, -6, 24, 56):                       # the splits characteristic of monstera
        for flip in (False, True):
            ang = math.radians(180 - a if flip else a)
            p0 = (cx + math.cos(ang) * 0.10 * S, cy + 0.02 * S + math.sin(ang) * 0.10 * S)
            p1 = (cx + math.cos(ang) * 0.62 * S, cy + 0.02 * S + math.sin(ang) * 0.62 * S)
            d.line([p0, p1], fill=rgb(bg), width=26)
            d.line([p0, (cx + math.cos(ang) * 0.35 * S, cy + 0.02 * S + math.sin(ang) * 0.35 * S)],
                   fill=rgb(lighter(g, 0.2)), width=3)
    for hx, hy in ((0.40, 0.46), (0.60, 0.46), (0.45, 0.60), (0.55, 0.60)):
        d.ellipse([hx * S - 16, hy * S - 22, hx * S + 16, hy * S + 22], fill=rgb(bg))
    thick_line(d, bezier((cx, cy - 0.14 * S), (cx + 0.02 * S, 0.22 * S), (0.60 * S, 0.12 * S)), gd, 14)


def bamboo(d):
    g, gd = '#79b35a', '#4d8a3b'
    stalks = [(0.34, 0.14), (0.52, 0.08), (0.68, 0.18)]
    for sx, top in stalks:
        for i in range(4):
            y = (top + 0.16 + i * 0.17) * S
            if i < 3:
                for sgn in (-1, 1):
                    poly(d, petal_pts(sx * S, y, math.radians(-90 + sgn * 62), 0.19 * S, 0.045 * S, 'pointed'),
                         '#5aa04a', '#3d7a34', 3)
    for sx, top in stalks:
        d.rounded_rectangle([sx * S - 24, top * S, sx * S + 24, 0.92 * S], 22, fill=rgb(g))
        d.line([(sx * S - 10, top * S + 10), (sx * S - 10, 0.90 * S)], fill=rgb(lighter(g, 0.3)), width=6)
        for i in range(5):
            y = (top + 0.16 + i * 0.17) * S
            if y < 0.9 * S:
                d.rounded_rectangle([sx * S - 28, y - 7, sx * S + 28, y + 7], 6, fill=rgb(gd))


def clover(d):
    g = '#43a352'
    thick_line(d, bezier((C, 0.52 * S), (C + 0.05 * S, 0.76 * S), (C - 0.04 * S, 0.93 * S)), '#2f7d3c', 14)
    for a, col in ((-135, g), (-45, lighter(g, 0.12)), (45, darker(g, 0.1)), (135, lighter(g, 0.05))):
        ar = math.radians(a)
        x, y = C + math.cos(ar) * 0.19 * S, C + math.sin(ar) * 0.19 * S
        poly(d, heart_pts(x, y, 0.0125 * S, ar + math.pi), col, darker(col, 0.3), 5)
        d.line([(C + math.cos(ar) * 0.04 * S, C + math.sin(ar) * 0.04 * S),
                (C + math.cos(ar) * 0.34 * S, C + math.sin(ar) * 0.34 * S)], fill=rgb(lighter(col, 0.35)), width=4)


def ginkgo(d):
    gold, gd = '#f0c53c', '#c99a1c'
    bx, by, R = C, 0.76 * S, 0.62 * S
    pts = [(bx, by)]
    for i in range(0, 101):
        th = math.radians(-140 + 100 * i / 100)
        r = R * (1 - 0.30 * math.exp(-((th + math.pi / 2) / 0.09) ** 2))
        pts.append((bx + r * math.cos(th), by + r * math.sin(th)))
    poly(d, pts, gold, gd, 6)
    for i in range(0, 14):
        th = math.radians(-140 + 100 * i / 13)
        d.line([(bx, by), (bx + 0.85 * R * math.cos(th), by + 0.85 * R * math.sin(th))], fill=rgb(gd), width=3)
    thick_line(d, bezier((bx, by), (bx - 0.01 * S, by + 0.08 * S), (bx + 0.03 * S, by + 0.15 * S)), '#9c7a2a', 12)


def seedling(d):
    g1, g2 = '#7bc66b', '#4c9e4a'
    d.ellipse([0.22 * S, 0.66 * S, 0.78 * S, 0.88 * S], fill=rgb('#7a5236'))
    d.ellipse([0.28 * S, 0.66 * S, 0.72 * S, 0.74 * S], fill=rgb('#936443'))
    thick_line(d, bezier((C, 0.72 * S), (C - 0.02 * S, 0.62 * S), (C, 0.48 * S)), '#4c9e4a', 16)
    for a, col in ((-160, g1), (-20, g2)):
        poly(d, petal_pts(C, 0.50 * S, math.radians(a), 0.36 * S, 0.22 * S, 'leaf'), col, darker(col, 0.25), 5)
        d.line([(C + math.cos(math.radians(a)) * 0.05 * S, 0.50 * S + math.sin(math.radians(a)) * 0.05 * S),
                (C + math.cos(math.radians(a)) * 0.30 * S, 0.50 * S + math.sin(math.radians(a)) * 0.30 * S)],
               fill=rgb(lighter(col, 0.4)), width=4)


def dandelion(d):
    thick_line(d, bezier((C, 0.95 * S), (C + 0.04 * S, 0.70 * S), (C, 0.50 * S)), '#5d9a4c', 12)
    cx, cy = C, 0.38 * S
    for i in range(48):
        a = 2 * math.pi * i / 48
        x, y = cx + math.cos(a) * 0.26 * S, cy + math.sin(a) * 0.26 * S
        d.line([(cx, cy), (x, y)], fill=rgb('#f4f1e8'), width=3)
        for j in range(5):                                  # little feathery bristles
            bx, by = cx + math.cos(a) * (0.21 + j * 0.012) * S, cy + math.sin(a) * (0.21 + j * 0.012) * S
            circle(d, bx, by, 0.007 * S, '#ffffff', ew=0)
        circle(d, x, y, 0.016 * S, '#ffffff', '#cfcab8', 2)
    circle(d, cx, cy, 0.045 * S, '#8a7a55', ew=0)


def sunflower(d):
    radial(d, rings(2, 0.46, 0.40, 22, 22, 0.20, '#f7bc1c', '#f4a512', 'pointed', '#c98608'),
           dict(r=0.20, color='#6a4326', seeds=True))


def cherry_blossom(d):
    radial(d, [dict(n=5, L=0.42 * S, W=0.36 * S, color='#f9c6d4', prof='notched', edge='#e07b9c', vein='#f09db5')],
           dict(r=0.04, color='#e0638a', stamens=(12, 0.13, '#d94f78')))


def pansy(d):
    radial(d, [dict(angles=[-122, -58], L=0.40 * S, W=0.46 * S, color='#5b2fa0', prof='round', edge='#3d1c75'),
               dict(angles=[168, 12], L=0.38 * S, W=0.42 * S, color='#7a4cc4', prof='round', edge='#3d1c75'),
               dict(angles=[90], L=0.40 * S, W=0.50 * S, color='#f6c91c', prof='round', edge='#b8860b')],
           dict(r=0.045, color='#f8e27a', stamens=(8, 0.10, '#3d1c75')))


# ---------------------------------------------------------------------------
# Registry: 53 distinct pictures
# ---------------------------------------------------------------------------
def _plant(name, bg, fn, *a, **kw):
    return dict(name=name, bg=bg, fn=lambda d: fn(d, *a, **kw))


PLANTS = [
    _plant('Daisy', '#cfe8d8', bloom, 'daisy', '#ffffff', '#f6c91c', edge='#d5dad8'),
    _plant('Red Rose', '#f1dcd6', rose, '#d62839', '#8e1423'),
    _plant('Red Tulip', '#dde8f3', tulip, '#e03a3e'),
    _plant('Shapla (Water Lily)', '#cfe9ee', water_lily, '#fbfbf5'),
    _plant('Lavender', '#e6e0f0', lavender, '#9a7cc8'),
    _plant('Sunflower', '#cfe6f2', sunflower),
    _plant('Cherry Blossom', '#e2edf5', cherry_blossom),
    _plant('Hibiscus', '#f6e6d4', bloom, 'five', '#e8334f', '#7a1020', c2='#c01f3d', cr=0.04, arm=True),
    _plant('Pink Cosmos', '#e3efe0', bloom, 'daisy', '#f27fb1', '#f6c91c', n=8, wr=0.55, prof='spoon', c2='#f7a3c6'),
    _plant('Yellow Marigold', '#dfe9f5', bloom, 'layered', '#f9b11a', '#e8800f', k=6, n0=18, n1=10, wr=0.34,
           prof='round', c2='#ec7f10', L0=0.44, L1=0.12),
    _plant('Purple Aster', '#e9f1dd', bloom, 'daisy', '#a678d8', '#f6c91c', n=26, wr=0.15, c2='#c4a2ec', cr=0.09),
    _plant('Pink Rose', '#e7efe3', rose, '#f08fb0', '#c2487a'),
    _plant('Yellow Tulip', '#f0e4ea', tulip, '#f6c21e'),
    _plant('Pink Lotus', '#e4efe9', water_lily, '#f27fae', pad='#4a9f6b'),
    _plant('Salvia', '#efe9dc', lavender, '#4f6fd0', stem='#4f8f58'),
    _plant('Red Poppy', '#e5ecd9', bloom, 'five', '#e43426', '#1c1c1c', n=4, c2='#f04d3b', cr=0.07),
    _plant('Echeveria', '#efe5d6', rosette, '#8fc9a8', '#d6efe0'),
    _plant('Saguaro Cactus', '#f6e5cf', saguaro),
    _plant('Boston Fern', '#e6efe0', fern, '#2e8b4e', '#8ed08a'),
    _plant('Monstera', '#e4eef2', monstera, '#e4eef2'),
    _plant('Orange Gerbera', '#e0ecf4', bloom, 'daisy', '#fb7c1c', '#3a2a22', n=24, wr=0.14, c2='#fda24a', cr=0.09),
    _plant('Gold Chrysanthemum', '#e4ebf5', bloom, 'layered', '#f1d23a', '#c9bb1c', k=6, n0=26, n1=12, wr=0.16,
           prof='spoon', c2='#a5c03a', L0=0.46, L1=0.14),
    _plant('Bamboo', '#e8f0dc', bamboo),
    _plant('White Rose', '#e3e9f3', rose, '#fbf7f0', '#e1d7c4'),
    _plant('Purple Tulip', '#e9f0e0', tulip, '#8e4bc4'),
    _plant('Blue Water Lily', '#e0eef2', water_lily, '#6a8fe0', pad='#3f9a67'),
    _plant('Orange Poppy', '#e4ecf2', bloom, 'five', '#fb8a1c', '#1c1c1c', n=4, c2='#fda64a', cr=0.07),
    _plant('Pink Hibiscus', '#e6efe3', bloom, 'five', '#f78fb8', '#a8184f', c2='#e0508a', cr=0.04),
    _plant('Pink Echeveria', '#e5ecf3', rosette, '#c7a7c9', '#f0d3d9', tip='#e0507f'),
    _plant('Barrel Cactus', '#f3e9d3', barrel_cactus),
    _plant('Sword Fern', '#efe9d9', fern, '#4a9a3c', '#b9dc78', bend=0.16, flip=True),
    _plant('Four-Leaf Clover', '#e6efe9', clover),
    _plant('Magenta Coneflower', '#e7efe0', bloom, 'daisy', '#d6438e', '#c75a17', n=14, wr=0.22, prof='pointed',
           c2='#ea78b0', cr=0.15, seeds=True),
    _plant('Deep Red Dahlia', '#e6ecdf', bloom, 'layered', '#b3122d', '#6a0a1a', k=7, n0=16, n1=8, wr=0.40,
           prof='pointed', c2='#e8426a', L0=0.45, L1=0.10),
    _plant('Yellow Rose', '#e0e8f4', rose, '#f7d23c', '#df9a14'),
    _plant('Blue Hydrangea', '#efe7dc', hydrangea, ['#5b7fd6', '#7a9be6', '#9bb6f0', '#6a6fd0'], 'blue'),
    _plant('Ginkgo Leaf', '#e1e9f0', ginkgo),
    _plant('Black-eyed Susan', '#e0eaf1', bloom, 'daisy', '#f7b91a', '#2e1d14', n=14, wr=0.26, c2='#fbd048', cr=0.17,
           seeds=True),
    _plant('Jasmine (Beli)', '#d9e8dc', bloom, 'layered', '#fbfaf2', '#f2c63c', k=2, n0=10, n1=10, wr=0.34,
           prof='pointed', c2='#f0efe2', L0=0.42, L1=0.36, cr=0.05),
    _plant('Peach Rose', '#e6edf3', rose, '#f7a98a', '#e0705a'),
    _plant('Red Zinnia', '#e5ecdc', bloom, 'layered', '#e33a3a', '#f0c030', k=4, n0=14, n1=10, wr=0.5, prof='round',
           c2='#f47a5a', L0=0.44, L1=0.20, cr=0.05),
    _plant('Pink Hydrangea', '#e3ece6', hydrangea, ['#e987b5', '#f2a8c9', '#d86aa0', '#f6c2d8'], 'pink'),
    _plant('Pansy', '#e8efdc', pansy),
    _plant('Forget-me-not', '#ece6d8', bloom, 'five', '#7aa8ec', '#f7d83c', c2='#a9c6f4', cr=0.07),
    _plant('Frangipani (Champa)', '#d8e9ea', bloom, 'five', '#fdf6e3', '#f6c21e', c2='#f9d35a', cr=0.06),
    _plant('Periwinkle (Nayantara)', '#e5ecde', bloom, 'five', '#e86aa6', '#8c1d52', c2='#f3a0c9', cr=0.06),
    _plant('Dandelion', '#d8e8ec', dandelion),
    _plant('Sprouting Seedling', '#e4edf2', seedling),
    _plant('Lavender Rose', '#eaf0e2', rose, '#c9a2e6', '#8e5cc2'),
    _plant('Yellow Hibiscus', '#e1ebf3', bloom, 'five', '#fbd432', '#b3162c', c2='#f5a81c', cr=0.05),
    _plant('Aloe Vera', '#f0e6d8', aloe),
]
assert len(PLANTS) >= 51
NAMES = [p['name'] for p in PLANTS]


def render(index):
    """Draw PLANTS[index] and return a 400x400 RGB image."""
    plant = PLANTS[index]
    img = Image.new('RGB', (S, S), rgb(plant['bg']))
    d = ImageDraw.Draw(img)
    plant['fn'](d)
    return img.resize((OUT, OUT), Image.LANCZOS)


def filename(index):
    """File name for PLANTS[index], e.g. 'Shapla (Water Lily)' -> 'shapla-water-lily.png'."""
    return re.sub(r'[^a-z0-9]+', '-', PLANTS[index]['name'].lower()).strip('-') + '.png'


def plant_for_position(position):
    """Which picture the user at `position` (0, 1, 2, ... in id order) gets.

    Stepping through the list in strides of 7 (7 and 51 share no factors) means the first 51 users
    all get a DIFFERENT picture, while neighbouring users - e.g. the eight doctors - don't end up
    with neighbouring entries of the list (all roses, say).
    """
    return (position * 7) % len(PLANTS)
