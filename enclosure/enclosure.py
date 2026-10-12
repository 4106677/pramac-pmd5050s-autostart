#!/usr/bin/env python3
"""Pramac autostart enclosure (base + lid + cable cover) -> STL. Units: mm.
Model frame: origin at the outer bottom-left corner of the base, x to the right, y up (plan view),
z from the wall side (floor, z=0) towards the lid. PCB top edge is at the top (high y)."""
import sys, numpy as np, trimesh
from manifold3d import Manifold

# ------------------------------------------------------------------ parameters
P = dict(
    pcb_w=93.3, pcb_h=82.1, pcb_t=1.6,
    margin_side=6.5, margin_top=6.5, gutter=24.0,      # free space around the PCB (gutter = cable area below it)
    wall=2.6, floor=2.6, standoff=6.0, comp_h=40.0,    # comp_h: free height above the PCB top (4700 uF caps are 36 mm)
    lid_t=2.6,
    boss_d=7.0, insert_d=4.2, insert_depth=6.0, screw_clear_d=3.4,
    pcb_holes=[(4.0, 37.0), (47.5, 76.5), (72.5, 75.0)],   # PCB mounting holes (x from left, y from top)
    # wire slots in the bottom wall, one per terminal block (J1, J4, J5, J6 contactor, J2), PCB x ranges
    slots=[(3.6, 13.0), (16.2, 25.6), (28.2, 37.5), (57.8, 67.2), (77.3, 91.7)], slot_z0=4.0, slot_h=22.0,
    term_y=72.0, opening_x=(2.5, 93.0), opening_h=15.0,      # lid opening above the terminal screws
    cover_w=None, cover_h=24.0, cover_t=2.4, cover_boss_d=6.0, cover_boss_h=6.0,
    vent_n=6, vent_w=2.0, vent_l=24.0, vent_pitch=10.0, vent_z=28.0,
    ear_w=14.0, ear_l=16.0, ear_t=3.0, ear_hole=5.2,
)
def derived(p):
    d = dict(p)
    d['inner_w'] = p['pcb_w'] + 2 * p['margin_side']
    d['inner_h'] = p['margin_top'] + p['pcb_h'] + p['gutter']
    d['inner_d'] = p['standoff'] + p['pcb_t'] + p['comp_h']
    d['outer_w'] = d['inner_w'] + 2 * p['wall']
    d['outer_h'] = d['inner_h'] + 2 * p['wall']
    d['base_h'] = p['floor'] + d['inner_d']
    d['pcb_x0'] = p['wall'] + p['margin_side']                 # model x of the PCB left edge
    d['pcb_ytop'] = d['outer_h'] - p['wall'] - p['margin_top']  # model y of the PCB top edge
    d['pcb_z'] = p['floor'] + p['standoff']                    # PCB bottom face
    if d['cover_w'] is None: d['cover_w'] = d['outer_w'] - 3.0
    return d
D = derived(P)

def box(x0, y0, z0, x1, y1, z1):
    return Manifold.cube([x1 - x0, y1 - y0, z1 - z0]).translate([x0, y0, z0])
def cyl(x, y, z0, h, dia, seg=48):
    return Manifold.cylinder(h, dia / 2, dia / 2, seg).translate([x, y, z0])
def pcb_xy(px, py):                                            # PCB coords (x right, y down) -> model
    return D['pcb_x0'] + px, D['pcb_ytop'] - py

def corner_posts():
    w, h, off = D['wall'], D['outer_h'], D['wall'] + D['boss_d'] / 2
    return [(off, off), (D['outer_w'] - off, off), (off, h - off), (D['outer_w'] - off, h - off)]

# ------------------------------------------------------------------ base
def make_base():
    W, H, w, f = D['outer_w'], D['outer_h'], P['wall'], P['floor']
    m = box(0, 0, 0, W, H, D['base_h']) - box(w, w, f, W - w, H - w, D['base_h'] + 1)
    for (cx, cy) in corner_posts():                            # lid screw posts
        m = m + cyl(cx, cy, f - 0.01, D['base_h'] - f + 0.01, P['boss_d'])
    for (px, py) in P['pcb_holes']:                            # PCB posts
        x, y = pcb_xy(px, py)
        m = m + cyl(x, y, f - 0.01, P['standoff'] + 0.01, P['boss_d'])
    for (cx, cy) in corner_posts():
        m = m - cyl(cx, cy, D['base_h'] - P['insert_depth'], P['insert_depth'] + 1, P['insert_d'], 32)
    for (px, py) in P['pcb_holes']:
        x, y = pcb_xy(px, py)
        m = m - cyl(x, y, f + P['standoff'] - 5.0, 6.0, P['insert_d'], 32)
    for (a, b) in P['slots']:                                  # wire slots in the bottom wall
        x0, _ = pcb_xy(a, 0); x1, _ = pcb_xy(b, 0)
        m = m - box(x0, -1, f + P['slot_z0'], x1, w + 1, f + P['slot_z0'] + P['slot_h'])
    n = P['vent_n']; cx0 = W / 2 - (n - 1) * P['vent_pitch'] / 2   # vent slots in the top wall
    for i in range(n):
        x = cx0 + i * P['vent_pitch']
        m = m - box(x - P['vent_w'] / 2, H - w - 1, D['vent_z'] - P['vent_l'] / 2, x + P['vent_w'] / 2, H + 1, D['vent_z'] + P['vent_l'] / 2)
    for sx in (-1, 1):                                         # wall-mount ears
        for ey in (0.14 * H, 0.86 * H):
            if sx < 0: x0, x1 = -P['ear_l'], 0.01
            else: x0, x1 = W - 0.01, W + P['ear_l']
            ear = box(x0, ey - P['ear_w'] / 2, 0, x1, ey + P['ear_w'] / 2, P['ear_t'])
            hx = x0 + P['ear_l'] / 2 if sx < 0 else x1 - P['ear_l'] / 2
            m = m + (ear - cyl(hx, ey, -1, P['ear_t'] + 2, P['ear_hole'], 32))
    return m

# ------------------------------------------------------------------ lid
def cover_boss_xy():
    y = pcb_xy(0, P['term_y'])[1]
    off = P['wall'] + P['cover_boss_d'] / 2 + 0.0
    return [(P['wall'] + 3.0, y), (D['outer_w'] - P['wall'] - 3.0, y)]

def make_lid():
    W, H, t = D['outer_w'], D['outer_h'], P['lid_t']
    m = box(0, 0, 0, W, H, t)
    for (cx, cy) in corner_posts():
        m = m - cyl(cx, cy, -1, t + 2, P['screw_clear_d'], 32)
    # cover bosses (underside) and screw holes
    for (cx, cy) in cover_boss_xy():
        m = m + cyl(cx, cy, -P['cover_boss_h'], P['cover_boss_h'] + 0.01, P['cover_boss_d'])
    for (cx, cy) in cover_boss_xy():
        m = m - cyl(cx, cy, -P['cover_boss_h'] - 1, P['cover_boss_h'] + 1, P['insert_d'], 32)
        m = m - cyl(cx, cy, -0.5, t + 1, P['screw_clear_d'], 32)
    # opening above the terminal screws
    (a, b), oh, ty = P['opening_x'], P['opening_h'], P['term_y']
    x0, y0 = pcb_xy(a, ty + oh / 2); x1, y1 = pcb_xy(b, ty - oh / 2)
    m = m - box(x0, y0, -1, x1, y1, t + 1)
    return m

def make_cover():
    cw, ch, ct = D['cover_w'], P['cover_h'], P['cover_t']
    yc = pcb_xy(0, P['term_y'])[1]; xc = D['outer_w'] / 2
    m = box(xc - cw / 2, yc - ch / 2, 0, xc + cw / 2, yc + ch / 2, ct)
    for (cx, cy) in cover_boss_xy():
        m = m - cyl(cx, cy, -1, ct + 2, P['screw_clear_d'], 32)
    return m

def to_trimesh(m):
    me = m.to_mesh()
    return trimesh.Trimesh(vertices=np.array(me.vert_properties)[:, :3], faces=np.array(me.tri_verts), process=False)

if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else "."
    for name, fn in (("base", make_base), ("lid", make_lid), ("cover", make_cover)):
        t = to_trimesh(fn()); t.export(f"{out}/{name}.stl")
        e = t.bounds[1] - t.bounds[0]
        print(f"{name}: {e[0]:.1f} x {e[1]:.1f} x {e[2]:.1f} mm, volume {t.volume/1000:.1f} cm3, watertight={t.is_watertight}")
    print("derived:", {k: round(v, 2) for k, v in D.items() if isinstance(v, float)})
