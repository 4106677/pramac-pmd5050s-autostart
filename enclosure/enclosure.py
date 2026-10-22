#!/usr/bin/env python3
"""Pramac autostart enclosure v3 (base + lid with skirt + glued-in cover with logo) -> STL. Units: mm.

Frame: origin at the outer bottom-left corner of the base, x to the right, y up (plan view),
z from the wall side (floor, z=0) towards the lid. The PCB top edge is at the top (high y).

Style: rounded corners, chamfered outer edges, stepped rim: the top of the base walls has a rebate
and the lid has a skirt that wraps over it, so the lid sides are flush with the base.
Needs: numpy trimesh manifold3d (pip install numpy trimesh manifold3d).
"""
import sys
import numpy as np
import trimesh
import os
from manifold3d import Manifold, CrossSection, JoinType, FillRule
from svgpath import svg_polygons

# ------------------------------------------------------------------ parameters
P = dict(
    pcb_w=93.3, pcb_h=82.1, pcb_t=1.6,
    margin_side=6.5, margin_top=6.5, gutter=24.0,      # free space around the PCB (gutter = cable area below it)
    wall=3.0, floor=3.0, standoff=6.0, comp_h=40.0,    # comp_h: free height above the PCB top (4700 uF caps are 36 mm)
    corner_r=7.0, chamfer=1.2,                          # outer corner radius, outer edge chamfer
    skirt_h=6.0, skirt_t=1.2, skirt_gap=0.3,            # lid skirt over the base rebate
    lid_t=4.0, pocket_d=2.0,                            # lid plate thickness, cover pocket depth
    boss_d=7.0, insert_d=4.2, insert_depth=6.0, screw_clear_d=3.4, csk_d=6.8, csk_h=1.7,
    pcb_holes=[(4.0, 37.0), (47.5, 76.5), (72.5, 75.0)],   # PCB mounting holes (x from left, y from top)
    # wire slots in the bottom wall, one per terminal block (J1, J4, J5, J6 contactor, J2), PCB x ranges
    slots=[(3.6, 13.0), (16.2, 25.6), (28.2, 37.5), (57.8, 67.2), (77.3, 91.7)], slot_z0=4.0, slot_h=22.0,
    cover_w=100.0, cover_top_y=60.0, cover_bottom=12.0,       # cover inlay: width, top edge (PCB y), bottom edge above the lid edge
    cover_r=4.0, cover_gap=0.25, cover_chamfer=0.4,           # glued in, no screws: cover thickness = pocket depth (flush)
    inlay=0.05, logo_h=28.0, logo_svg='pramac-logo-vector.svg',   # recess depth of logo/emblems (paint them), logo height
    emblem_s=15.0, emblem_dx=35.0,                             # hazard emblem size and its distance from the cover centre
    # extra PCB supports (the board is held by 3 screws): plain posts at free spots (PCB coords), edge ledges with guide fins
    support_d=5.0, supports=[(28.0, 20.5), (83.0, 26.0), (28.5, 64.5), (72.5, 67.5), (14.0, 41.0), (48.0, 37.0)],
    ledge_len=10.0, ledge_under=1.5, fin_t=1.5, fin_gap=0.4, fin_above=2.0,
    ledges_left=[12.0, 62.0], ledges_right=[20.0, 50.0], ledges_top=[15.0, 80.0],   # ledge centres along each PCB edge
    vent_n=6, vent_w=2.0, vent_l=24.0, vent_pitch=10.0, vent_z=30.0,
    ear_w=14.0, ear_l=16.0, ear_t=3.2, ear_hole=5.2,
)


def derived(p):
    d = dict(p)
    d['inner_w'] = p['pcb_w'] + 2 * p['margin_side']
    d['inner_h'] = p['margin_top'] + p['pcb_h'] + p['gutter']
    d['inner_d'] = p['standoff'] + p['pcb_t'] + p['comp_h']
    d['outer_w'] = d['inner_w'] + 2 * p['wall']
    d['outer_h'] = d['inner_h'] + 2 * p['wall']
    d['base_h'] = p['floor'] + d['inner_d']
    d['pcb_x0'] = p['wall'] + p['margin_side']                  # model x of the PCB left edge
    d['pcb_ytop'] = d['outer_h'] - p['wall'] - p['margin_top']   # model y of the PCB top edge
    d['rebate'] = p['skirt_t'] + p['skirt_gap']
    return d


D = derived(P)
SEG = 64


def pcb_xy(px, py):
    """PCB coordinates (x right, y down from the top edge) -> model plan coordinates."""
    return D['pcb_x0'] + px, D['pcb_ytop'] - py


# ------------------------------------------------------------------ primitives
def rrect(x0, y0, w, h, r):
    r = max(0.01, min(r, w / 2 - 0.01, h / 2 - 0.01))
    cs = CrossSection.square([w - 2 * r, h - 2 * r]).translate([x0 + r, y0 + r])
    return cs.offset(r, JoinType.Round, 2.0, SEG)


def prism(cs, z0, z1):
    return Manifold.extrude(cs, z1 - z0).translate([0, 0, z0])


def rprism(x0, y0, w, h, r, z0, z1):
    return prism(rrect(x0, y0, w, h, r), z0, z1)


def box(x0, y0, z0, x1, y1, z1):
    return Manifold.cube([x1 - x0, y1 - y0, z1 - z0]).translate([x0, y0, z0])


def cyl(x, y, z0, h, dia, seg=48):
    return Manifold.cylinder(h, dia / 2, dia / 2, seg).translate([x, y, z0])


def cone(x, y, z0, h, d_bottom, d_top, seg=48):
    return Manifold.cylinder(h, d_bottom / 2, d_top / 2, seg).translate([x, y, z0])


def chamfered_slab(x0, y0, w, h, r, z0, z1, c, bottom=True, top=False):
    """Rounded-rectangle prism with 45 degree chamfers on the chosen outer edges (convex hull)."""
    parts = []
    lo, hi = z0 + (c if bottom else 0), z1 - (c if top else 0)
    parts.append(rprism(x0, y0, w, h, r, lo, hi))
    if bottom:
        parts.append(rprism(x0 + c, y0 + c, w - 2 * c, h - 2 * c, r - c, z0, z0 + 0.01))
    if top:
        parts.append(rprism(x0 + c, y0 + c, w - 2 * c, h - 2 * c, r - c, z1 - 0.01, z1))
    return parts[0] if len(parts) == 1 else Manifold.compose(parts).hull()


def corner_posts():
    off = D['wall'] + D['boss_d'] / 2
    W, H = D['outer_w'], D['outer_h']
    return [(off, off), (W - off, off), (off, H - off), (W - off, H - off)]


def cover_geom():
    """Cover rectangle in model coordinates: (x0, y0, w, h)."""
    y_top = pcb_xy(0, P['cover_top_y'])[1]
    y0 = P['cover_bottom']
    return (D['outer_w'] / 2 - P['cover_w'] / 2, y0, P['cover_w'], y_top - y0)


# ------------------------------------------------------------------ PCB supports
def supports():
    f, sd = P['floor'], P['standoff']
    z_top = f + sd                                           # underside of the PCB
    parts = []
    for (px, py) in P['supports']:                           # plain posts with a wider foot
        x, y = pcb_xy(px, py)
        parts.append(cyl(x, y, f - 0.01, sd + 0.01, P['support_d']))
        parts.append(cone(x, y, f - 0.01, 2.0, P['support_d'] + 4.0, P['support_d']))
    x0, x1 = D['pcb_x0'], D['pcb_x0'] + P['pcb_w']
    y1, y0 = D['pcb_ytop'], D['pcb_ytop'] - P['pcb_h']
    w, L, u, ft, fg = P['wall'], P['ledge_len'], P['ledge_under'], P['fin_t'], P['fin_gap']
    zf = z_top + P['pcb_t'] + P['fin_above']
    for py in P['ledges_left']:                              # ledge under the PCB edge + guide fin just outside it
        y = pcb_xy(0, py)[1]
        parts.append(box(w - 0.01, y - L / 2, f - 0.01, x0 + u, y + L / 2, z_top))
        parts.append(box(x0 - fg - ft, y - L / 2, f - 0.01, x0 - fg, y + L / 2, zf))
    for py in P['ledges_right']:
        y = pcb_xy(0, py)[1]
        parts.append(box(x1 - u, y - L / 2, f - 0.01, D['outer_w'] - w + 0.01, y + L / 2, z_top))
        parts.append(box(x1 + fg, y - L / 2, f - 0.01, x1 + fg + ft, y + L / 2, zf))
    for px in P['ledges_top']:
        x = pcb_xy(px, 0)[0]
        parts.append(box(x - L / 2, y1 - u, f - 0.01, x + L / 2, D['outer_h'] - w + 0.01, z_top))
        parts.append(box(x - L / 2, y1 + fg, f - 0.01, x + L / 2, y1 + fg + ft, zf))
    return Manifold.compose(parts)


# ------------------------------------------------------------------ base
def make_base():
    W, H, w, f, r, c = D['outer_w'], D['outer_h'], P['wall'], P['floor'], P['corner_r'], P['chamfer']
    top, rb, sh = D['base_h'], D['rebate'], P['skirt_h']
    lower = chamfered_slab(0, 0, W, H, r, 0, top - sh, c, bottom=True)
    upper = rprism(rb, rb, W - 2 * rb, H - 2 * rb, r - rb, top - sh - 0.01, top)
    m = lower + upper
    m = m - rprism(w, w, W - 2 * w, H - 2 * w, r - w if r > w else 0.5, f, top + 1)       # cavity
    for (cx, cy) in corner_posts():                                                       # lid screw posts
        m = m + cyl(cx, cy, f - 0.01, top - f + 0.01, P['boss_d'])
    for (px, py) in P['pcb_holes']:                                                       # PCB posts
        x, y = pcb_xy(px, py)
        m = m + cyl(x, y, f - 0.01, P['standoff'] + 0.01, P['boss_d'])
    m = m + supports()
    for (cx, cy) in corner_posts():
        m = m - cyl(cx, cy, top - P['insert_depth'], P['insert_depth'] + 1, P['insert_d'], 32)
    for (px, py) in P['pcb_holes']:
        x, y = pcb_xy(px, py)
        m = m - cyl(x, y, f + P['standoff'] - 5.0, 6.0, P['insert_d'], 32)
    for (a, b) in P['slots']:                                                             # wire slots (bottom wall)
        x0, _ = pcb_xy(a, 0)
        x1, _ = pcb_xy(b, 0)
        m = m - box(x0, -1, f + P['slot_z0'], x1, w + 1, f + P['slot_z0'] + P['slot_h'])
    n = P['vent_n']                                                                       # vent slots (top wall)
    cx0 = W / 2 - (n - 1) * P['vent_pitch'] / 2
    for i in range(n):
        x = cx0 + i * P['vent_pitch']
        m = m - box(x - P['vent_w'] / 2, H - w - 1, P['vent_z'] - P['vent_l'] / 2,
                    x + P['vent_w'] / 2, H + 1, P['vent_z'] + P['vent_l'] / 2)
    for sx in (-1, 1):                                                                    # wall-mount ears
        for ey in (0.14 * H, 0.86 * H):
            if sx < 0:
                x0, x1 = -P['ear_l'], w + 0.5
                hx = x0 + P['ear_l'] / 2
            else:
                x0, x1 = W - w - 0.5, W + P['ear_l']
                hx = x1 - P['ear_l'] / 2
            ear = rprism(x0, ey - P['ear_w'] / 2, x1 - x0, P['ear_w'], 3.0, 0, P['ear_t'])
            m = m + (ear - cyl(hx, ey, -1, P['ear_t'] + 2, P['ear_hole'], 32))
    return m


# ------------------------------------------------------------------ lid
def make_lid():
    W, H, r, c = D['outer_w'], D['outer_h'], P['corner_r'], P['chamfer']
    t, sh, st = P['lid_t'], P['skirt_h'], P['skirt_t']
    plate = chamfered_slab(0, 0, W, H, r, 0, t, c, bottom=False, top=True)
    skirt = rprism(0, 0, W, H, r, -sh, 0.01) - rprism(st, st, W - 2 * st, H - 2 * st, r - st, -sh - 1, 1)
    m = plate + skirt
    # lid screws: through hole + countersink at the corner posts
    for (cx, cy) in corner_posts():
        m = m - cyl(cx, cy, -1, t + 2, P['screw_clear_d'], 32)
        m = m - cone(cx, cy, t - P['csk_h'], P['csk_h'] + 0.01, P['screw_clear_d'], P['csk_d'], 32)
    # shallow pocket for the glued-in cover (no opening: the terminals are reached by taking the lid off)
    x0, y0, w, h = cover_geom()
    g = P['cover_gap']
    m = m - rprism(x0 - g, y0 - g, w + 2 * g, h + 2 * g, P['cover_r'] + g, t - P['pocket_d'], t + 1)
    return m


# ------------------------------------------------------------------ cover with hazard emblem
def logo_section():
    """Pramac logo (SVG), scaled to logo_h, centred on the origin."""
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), P['logo_svg'])
    cs = CrossSection(svg_polygons(path), FillRule.EvenOdd)
    bx0, by0, bx1, by1 = cs.bounds()
    k = P['logo_h'] / (by1 - by0)
    return cs.translate([-(bx0 + bx1) / 2, -(by0 + by1) / 2]).scale([k, k])


def emblem_section():
    """High-voltage hazard sign: rounded triangle ring + lightning bolt, centred on the origin."""
    s = P['emblem_s']
    tri = np.array([[0, s * 0.62], [-s * 0.62 * 0.866 * 1.15, -s * 0.31], [s * 0.62 * 0.866 * 1.15, -s * 0.31]])
    ring = CrossSection([tri]).offset(s * 0.07, JoinType.Round, 2.0, 32) - CrossSection([tri]).offset(-s * 0.07, JoinType.Round, 2.0, 32)
    bolt = np.array([[1.2, 5.2], [-3.2, -0.4], [-0.4, -0.4], [-1.6, -5.4], [3.4, 0.9], [0.5, 0.9]]) * 1.2 * s / 19.0
    return ring + CrossSection([bolt])


def make_cover():
    """Flush inlay: as thick as the lid pocket is deep. Logo and emblems are recessed by `inlay` mm for painting."""
    x0, y0, w, h = cover_geom()
    ct = P['pocket_d']
    m = chamfered_slab(x0, y0, w, h, P['cover_r'], 0, ct, P['cover_chamfer'], bottom=False, top=True)
    cx, cy = x0 + w / 2, y0 + h / 2
    d = P['inlay']
    cut = prism(logo_section(), 0, d + 1).translate([cx, cy, ct - d])
    for sx in (-1, 1):
        cut = cut + prism(emblem_section(), 0, d + 1).translate([cx + sx * P['emblem_dx'], cy, ct - d])
    return m - cut


def to_trimesh(m):
    me = m.to_mesh()
    return trimesh.Trimesh(vertices=np.array(me.vert_properties)[:, :3], faces=np.array(me.tri_verts), process=False)


if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else "."
    for name, fn in (("base", make_base), ("lid", make_lid), ("cover", make_cover)):
        t = to_trimesh(fn())
        t.export(f"{out}/{name}.stl")
        e = t.bounds[1] - t.bounds[0]
        print(f"{name}: {e[0]:.1f} x {e[1]:.1f} x {e[2]:.1f} mm, volume {t.volume/1000:.1f} cm3, watertight={t.is_watertight}")
    print("outer %.1f x %.1f, base_h %.1f" % (D['outer_w'], D['outer_h'], D['base_h']))
