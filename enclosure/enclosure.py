#!/usr/bin/env python3
"""Pramac autostart enclosure v2 (base + lid with skirt + cable cover) -> STL. Units: mm.

Frame: origin at the outer bottom-left corner of the base, x to the right, y up (plan view),
z from the wall side (floor, z=0) towards the lid. The PCB top edge is at the top (high y).

Style: rounded corners, chamfered outer edges, stepped rim: the top of the base walls has a rebate
and the lid has a skirt that wraps over it, so the lid sides are flush with the base.
Needs: numpy trimesh manifold3d (pip install numpy trimesh manifold3d).
"""
import sys
import numpy as np
import trimesh
from manifold3d import Manifold, CrossSection, JoinType

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
    term_y=72.0, opening_x=(2.5, 93.0), opening_h=15.0,      # lid opening above the terminal screws (PCB coords)
    cover_w=100.0, cover_top_y=60.0, cover_bottom=12.0,       # cover: width, top edge (PCB y), bottom edge above the lid edge
    cover_t=2.4, cover_r=4.0, cover_gap=0.25, cover_boss_d=6.5, cover_boss_h=6.0, peg_d=3.0, peg_l=1.6,
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


def cover_boss_xy():
    x0, y0, w, h = cover_geom()
    return [(x0 + 14.0, y0 + 5.0), (x0 + w - 14.0, y0 + 5.0)]      # clear of the lid corner posts


def cover_pegs_xy():
    x0, y0, w, h = cover_geom()
    return [(x0 + w * 0.25, y0 + h - 4.0), (x0 + w * 0.75, y0 + h - 4.0)]


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
    # cover pocket + opening above the terminal screws
    x0, y0, w, h = cover_geom()
    g = P['cover_gap']
    m = m - rprism(x0 - g, y0 - g, w + 2 * g, h + 2 * g, P['cover_r'] + g, t - P['pocket_d'], t + 1)
    (a, b), oh, ty = P['opening_x'], P['opening_h'], P['term_y']
    ox0, oy0 = pcb_xy(a, ty + oh / 2)
    ox1, oy1 = pcb_xy(b, ty - oh / 2)
    m = m - rprism(ox0, oy0, ox1 - ox0, oy1 - oy0, 2.0, -1, t + 1)
    # bosses under the lid for the cover screws, peg holes at the top edge of the pocket
    for (cx, cy) in cover_boss_xy():
        m = m + cyl(cx, cy, -P['cover_boss_h'], P['cover_boss_h'] + 0.01, P['cover_boss_d'])
        m = m - cyl(cx, cy, -P['cover_boss_h'] - 1, P['cover_boss_h'] + 1, P['insert_d'], 32)
        m = m - cyl(cx, cy, -0.5, t + 1, P['screw_clear_d'], 32)
    for (cx, cy) in cover_pegs_xy():
        m = m - cyl(cx, cy, t - P['pocket_d'] - 0.01, P['peg_l'] + 0.4, P['peg_d'] + 0.4, 24)
    return m


# ------------------------------------------------------------------ cover with hazard emblem
def make_cover():
    x0, y0, w, h = cover_geom()
    ct, c = P['cover_t'], 0.6
    m = chamfered_slab(x0, y0, w, h, P['cover_r'], 0, ct, c, bottom=False, top=True)
    for (cx, cy) in cover_boss_xy():
        m = m - cyl(cx, cy, -1, ct + 2, P['screw_clear_d'], 32)
        m = m - cone(cx, cy, ct - 1.3, 1.31, P['screw_clear_d'], P['csk_d'] - 0.6, 32)
    for (cx, cy) in cover_pegs_xy():                      # pegs on the underside
        m = m + cyl(cx, cy, -P['peg_l'], P['peg_l'] + 0.01, P['peg_d'], 24)
    # hazard emblem (raised 0.6 mm): rounded triangle ring + lightning bolt
    s = 19.0
    tri = np.array([[0, s * 0.62], [-s * 0.62 * 0.866 * 1.15, -s * 0.31], [s * 0.62 * 0.866 * 1.15, -s * 0.31]])
    ring = CrossSection([tri]).offset(1.4, JoinType.Round, 2.0, 32) - CrossSection([tri]).offset(-1.4, JoinType.Round, 2.0, 32)
    bolt = np.array([[1.2, 5.2], [-3.2, -0.4], [-0.4, -0.4], [-1.6, -5.4], [3.4, 0.9], [0.5, 0.9]]) * 1.2
    cx, cy = x0 + w / 2, y0 + h * 0.52
    emb = prism(ring, 0, 0.6) + prism(CrossSection([bolt]), 0, 0.6)
    m = m + emb.translate([cx, cy, ct - 0.01])
    return m


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
