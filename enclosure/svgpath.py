"""Minimal SVG path -> polygon flattener (M L H V C S Q T A Z, absolute/relative). Y axis is flipped (SVG y is down)."""
import re, math
import numpy as np

_TOK = re.compile(r"[MmLlHhVvCcSsQqTtAaZz]|[-+]?(?:\d*\.\d+|\d+\.?)(?:[eE][-+]?\d+)?")


def _cubic(p0, p1, p2, p3, n=14):
    t = np.linspace(0, 1, n + 1)[1:, None]
    return ((1 - t) ** 3) * p0 + 3 * ((1 - t) ** 2) * t * p1 + 3 * (1 - t) * (t ** 2) * p2 + (t ** 3) * p3


def _quad(p0, p1, p2, n=10):
    t = np.linspace(0, 1, n + 1)[1:, None]
    return ((1 - t) ** 2) * p0 + 2 * (1 - t) * t * p1 + (t ** 2) * p2


def _arc(p0, rx, ry, phi, fa, fs, p1, n=16):
    x1, y1, x2, y2 = p0[0], p0[1], p1[0], p1[1]
    if rx == 0 or ry == 0:
        return np.array([p1])
    cp, sp = math.cos(math.radians(phi)), math.sin(math.radians(phi))
    dx, dy = (x1 - x2) / 2, (y1 - y2) / 2
    x1p, y1p = cp * dx + sp * dy, -sp * dx + cp * dy
    lam = (x1p ** 2) / (rx ** 2) + (y1p ** 2) / (ry ** 2)
    if lam > 1:
        rx, ry = rx * math.sqrt(lam), ry * math.sqrt(lam)
    num = rx * rx * ry * ry - rx * rx * y1p * y1p - ry * ry * x1p * x1p
    den = rx * rx * y1p * y1p + ry * ry * x1p * x1p
    co = math.sqrt(max(0, num / den)) * (-1 if fa == fs else 1)
    cxp, cyp = co * rx * y1p / ry, -co * ry * x1p / rx
    cx, cy = cp * cxp - sp * cyp + (x1 + x2) / 2, sp * cxp + cp * cyp + (y1 + y2) / 2
    ang = lambda ux, uy, vx, vy: math.atan2(ux * vy - uy * vx, ux * vx + uy * vy)
    t1 = ang(1, 0, (x1p - cxp) / rx, (y1p - cyp) / ry)
    dt = ang((x1p - cxp) / rx, (y1p - cyp) / ry, (-x1p - cxp) / rx, (-y1p - cyp) / ry)
    if not fs and dt > 0: dt -= 2 * math.pi
    if fs and dt < 0: dt += 2 * math.pi
    pts = []
    for k in range(1, n + 1):
        a = t1 + dt * k / n
        pts.append([cx + rx * math.cos(a) * cp - ry * math.sin(a) * sp, cy + rx * math.cos(a) * sp + ry * math.sin(a) * cp])
    return np.array(pts)


def path_polygons(d):
    toks = _TOK.findall(d)
    i, cmd, cur, start, last_c, last_q = 0, None, np.zeros(2), np.zeros(2), None, None
    polys, poly = [], []

    def num():
        nonlocal i
        v = float(toks[i]); i += 1
        return v

    def close():
        nonlocal poly
        if len(poly) > 2: polys.append(np.array(poly))
        poly = []

    while i < len(toks):
        if re.match(r"[A-Za-z]", toks[i]):
            cmd = toks[i]; i += 1
            if cmd in "Zz":
                close(); cur = start.copy(); continue
        rel = cmd.islower(); c = cmd.upper()
        base = cur if rel else np.zeros(2)
        if c == "M":
            close(); cur = base + np.array([num(), num()]); start = cur.copy(); poly = [cur.copy()]
            cmd = "l" if rel else "L"; last_c = last_q = None; continue
        if c == "L": cur = base + np.array([num(), num()]); poly.append(cur.copy()); last_c = last_q = None
        elif c == "H": cur = np.array([(cur[0] if rel else 0) + num(), cur[1]]); poly.append(cur.copy()); last_c = last_q = None
        elif c == "V": cur = np.array([cur[0], (cur[1] if rel else 0) + num()]); poly.append(cur.copy()); last_c = last_q = None
        elif c in "CS":
            if c == "C": p1 = base + np.array([num(), num()])
            else: p1 = 2 * cur - last_c if last_c is not None else cur.copy()
            p2 = base + np.array([num(), num()]); p3 = base + np.array([num(), num()])
            poly.extend(list(_cubic(cur, p1, p2, p3))); cur = p3; last_c = p2; last_q = None
        elif c in "QT":
            if c == "Q": p1 = base + np.array([num(), num()])
            else: p1 = 2 * cur - last_q if last_q is not None else cur.copy()
            p2 = base + np.array([num(), num()])
            poly.extend(list(_quad(cur, p1, p2))); cur = p2; last_q = p1; last_c = None
        elif c == "A":
            rx, ry, phi, fa, fs = num(), num(), num(), int(num()), int(num())
            p2 = base + np.array([num(), num()])
            poly.extend(list(_arc(cur, rx, ry, phi, fa, fs, p2))); cur = p2; last_c = last_q = None
        else:
            raise ValueError("unsupported path command " + cmd)
    close()
    return [np.column_stack([p[:, 0], -p[:, 1]]) for p in polys]     # flip y


def svg_polygons(path):
    txt = open(path, encoding="utf-8").read()
    polys = []
    for d in re.findall(r'<path[^>]*\sd="([^"]+)"', txt, flags=re.S):
        polys += path_polygons(d)
    return polys


if __name__ == "__main__":
    import sys
    ps = svg_polygons(sys.argv[1])
    allp = np.vstack(ps)
    print(len(ps), "contours; bbox x %.1f..%.1f y %.1f..%.1f" % (allp[:, 0].min(), allp[:, 0].max(), allp[:, 1].min(), allp[:, 1].max()))
