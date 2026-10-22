"""
Pramac autostart: parametric enclosure for Autodesk Fusion (Python script), v3.

Run: Fusion -> UTILITIES -> ADD-INS -> Scripts and Add-Ins (Shift+S) -> "+" -> pick this file -> Run.
It creates a new parametric design with USER PARAMETERS (Modify -> Change Parameters) and three bodies:
Base (with PCB support posts, ledges and guide fins, removable wall-mount Ears), Lid (with a skirt that wraps over a rebate on the base
walls) and Cover: a screwless inlay glued into the lid pocket with a hazard emblem. The Pramac logo (SVG) is on the
lid above the cover. Logo and emblem are recessed by 0.05 mm so they can be painted.
Sketches are dimensioned with the parameters, so editing a parameter rebuilds the model through the timeline.

Frame: origin = outer bottom-left corner of the base, x to the right, y up (plan view), z from the wall
side (floor) towards the lid. The PCB top edge is at the high-y side; the cable gutter is at the low-y side.

The core geometry is created first. Cosmetic steps (rounded corners, chamfers, emblems, logo) are "optional":
if one fails the script carries on and lists what was skipped at the end.

NOTE: written against the Fusion API without being run inside Fusion (no Fusion on the machine it was written
on). The STL files in this folder come from enclosure.py and are verified; this script mirrors that model.
"""
import traceback
import adsk.core
import adsk.fusion

PARAMS = [
    ('pcb_w', '93.3', 'PCB width'),
    ('pcb_h', '82.1', 'PCB height'),
    ('pcb_t', '1.6', 'PCB thickness'),
    ('margin_side', '6.5', 'free space left/right of the PCB'),
    ('margin_top', '6.5', 'free space above the PCB'),
    ('gutter', '24', 'cable area below the PCB'),
    ('wall', '3', 'wall thickness'),
    ('floor_t', '3', 'floor thickness'),
    ('standoff', '6', 'PCB standoff height (lead ends are 3.5 mm)'),
    ('comp_h', '40', 'free height above the PCB top (4700 uF caps are 36 mm)'),
    ('corner_r', '7', 'outer corner radius'),
    ('chamfer_d', '1.2', 'outer edge chamfer'),
    ('skirt_h', '6', 'lid skirt height'),
    ('skirt_t', '1.2', 'lid skirt thickness'),
    ('skirt_gap', '0.3', 'clearance skirt/base rebate'),
    ('lid_t', '4', 'lid plate thickness'),
    ('pocket_d', '2', 'cover pocket depth'),
    ('boss_d', '7', 'post diameter'),
    ('insert_d', '4.2', 'hole for M3 brass insert'),
    ('insert_depth', '6', 'insert hole depth in the corner posts'),
    ('relief_d', '3.4', 'screw relief bore below the inserts'),
    ('relief_floor', '1.2', 'height above the wall plane where the relief bore stops'),
    ('screw_clear_d', '3.4', 'M3 clearance hole'),
    ('csk_d', '6.8', 'screw head recess diameter in the lid'),
    ('csk_h', '1.7', 'screw head recess depth'),
    ('slot_z0', '4', 'wire slot: height above the floor'),
    ('slot_h', '22', 'wire slot height'),
    ('cover_w', '100', 'cover inlay width'),
    ('cover_top_y', '60', 'cover top edge on the PCB (y from the PCB top)'),
    ('cover_bottom', '12', 'cover bottom edge above the lid edge'),
    ('cover_r', '4', 'cover corner radius'),
    ('cover_gap', '0.25', 'cover pocket clearance (room for glue)'),
    ('cover_chamfer', '0.4', 'cover top edge chamfer'),
    ('inlay', '0.05', 'recess depth of logo and emblems'),
    ('logo_h', '40', 'logo height (on the lid)'),
    ('support_d', '5', 'plain PCB support post diameter'),
    ('ledge_len', '10', 'PCB edge ledge length'),
    ('ledge_under', '1.5', 'how far a ledge reaches under the PCB edge'),
    ('fin_t', '1.5', 'guide fin thickness'),
    ('fin_gap', '0.4', 'clearance between PCB edge and guide fin'),
    ('fin_above', '2', 'guide fin height above the PCB top'),
    ('vent_w', '2', 'vent slot width'),
    ('vent_l', '24', 'vent slot length'),
    ('vent_pitch', '10', 'vent slot pitch'),
    ('vent_z', '30', 'vent slot centre height above the floor'),
    ('ear_w', '14', 'wall-mount ear width'),
    ('ear_l', '16', 'wall-mount ear length'),
    ('ear_t', '3.2', 'wall-mount ear thickness'),
    ('ear_hole', '5.2', 'wall-mount hole diameter'),
    ('tab_t', '2', 'ear tab thickness (slides into a rebate under the base floor)'),
    ('tab_l', '12', 'rebate length from the side face'),
    ('tab_taper', '1.3', 'tab taper per side over its length (trapezoid)'),
    ('tab_gap', '0.25', 'tab side clearance at the rebate mouth'),
    ('tab_wedge', '0.3', 'extra taper of the rebate: the tab wedges in at the end'),
    ('tab_z_gap', '0.2', 'rebate height clearance'),
    ('cover_ledge', '3', 'lid window = cover inset by this; the cover is glued onto the ledge'),
    # derived
    ('inner_w', 'pcb_w + 2 * margin_side', 'derived'),
    ('inner_h', 'margin_top + pcb_h + gutter', 'derived'),
    ('inner_d', 'standoff + pcb_t + comp_h', 'derived'),
    ('outer_w', 'inner_w + 2 * wall', 'derived'),
    ('outer_h', 'inner_h + 2 * wall', 'derived'),
    ('base_h', 'floor_t + inner_d', 'derived'),
    ('rebate', 'skirt_t + skirt_gap', 'derived'),
    ('pcb_x0', 'wall + margin_side', 'model x of the PCB left edge'),
    ('pcb_ytop', 'outer_h - wall - margin_top', 'model y of the PCB top edge'),
    ('cover_y0', 'cover_bottom', 'derived'),
    ('cover_y1', 'pcb_ytop - cover_top_y', 'derived'),
    ('cover_x0', 'outer_w / 2 - cover_w / 2', 'derived'),
    ('cover_t', 'pocket_d', 'derived: the cover is flush with the lid'),
]

PCB_HOLES = [(4.0, 37.0), (47.5, 76.5), (72.5, 75.0)]               # PCB mounting holes (x from left, y from top)
SLOTS = [(3.6, 13.0), (16.2, 25.6), (28.2, 37.5), (57.8, 67.2), (77.3, 91.7)]   # wire slots, PCB x ranges
SUPPORTS = [(28.0, 20.5), (83.0, 26.0), (28.5, 64.5), (72.5, 67.5), (14.0, 41.0), (48.0, 37.0)]   # plain posts (PCB x, y)
LEDGES_LEFT, LEDGES_RIGHT, LEDGES_TOP = [22.0, 62.0], [24.0, 40.0], [15.0, 80.0]   # ledge centres along each PCB edge
VENT_N = 6
LOGO_SVG = 'pramac-logo-vector.svg'   # next to this script

CM = 0.1  # API length unit is cm; parameters are in mm
app = adsk.core.Application.get()
ui = app.userInterface
VAL = {}
SKIPPED = []


def is_number(s):
    try:
        float(s)
        return True
    except ValueError:
        return False


def P3(x, y, z=0.0):
    return adsk.core.Point3D.create(x * CM, y * CM, z * CM)


def ev(expr):
    return float(eval(expr, {}, VAL))


def add_params(design):
    ups = design.userParameters
    for name, expr, comment in PARAMS:
        VAL[name] = ev(expr)
        e = (expr + ' mm') if is_number(expr) else expr
        ups.add(name, adsk.core.ValueInput.createByString(e), 'mm', comment)


def offset_plane(root, expr):
    pin = root.constructionPlanes.createInput()
    pin.setByOffset(root.xYConstructionPlane, adsk.core.ValueInput.createByString(expr))
    return root.constructionPlanes.add(pin)


def dim_h(sk, p0, p1, expr, ty):
    d = sk.sketchDimensions.addDistanceDimension(
        p0, p1, adsk.fusion.DimensionOrientations.HorizontalDimensionOrientation,
        adsk.core.Point3D.create((p0.geometry.x + p1.geometry.x) / 2, ty, 0))
    d.parameter.expression = expr
    return d


def dim_v(sk, p0, p1, expr, tx):
    d = sk.sketchDimensions.addDistanceDimension(
        p0, p1, adsk.fusion.DimensionOrientations.VerticalDimensionOrientation,
        adsk.core.Point3D.create(tx, (p0.geometry.y + p1.geometry.y) / 2, 0))
    d.parameter.expression = expr
    return d


def rect(sk, x0e, y0e, x1e, y1e):
    """Rectangle (expressions in mm, x0e < x1e, y0e < y1e); lower-left corner, width and height are
    dimensioned, so editing parameters moves/resizes it."""
    x0, y0, x1, y1 = ev(x0e), ev(y0e), ev(x1e), ev(y1e)
    lines = sk.sketchCurves.sketchLines.addTwoPointRectangle(P3(x0, y0), P3(x1, y1))
    pts = []
    for i in range(4):
        ln = lines.item(i)
        for p in (ln.startSketchPoint, ln.endSketchPoint):
            if not any(abs(q.geometry.x - p.geometry.x) < 1e-9 and abs(q.geometry.y - p.geometry.y) < 1e-9 for q in pts):
                pts.append(p)
    ll = [p for p in pts if abs(p.geometry.x - x0 * CM) < 1e-9 and abs(p.geometry.y - y0 * CM) < 1e-9][0]
    ur = [p for p in pts if abs(p.geometry.x - x1 * CM) < 1e-9 and abs(p.geometry.y - y1 * CM) < 1e-9][0]
    org = sk.originPoint
    if abs(x0) > 1e-9:
        dim_h(sk, org, ll, x0e if x0 > 0 else '-(%s)' % x0e, (y0 - 4) * CM)
    else:
        sk.geometricConstraints.addVerticalPoints(org, ll)
    if abs(y0) > 1e-9:
        dim_v(sk, org, ll, y0e if y0 > 0 else '-(%s)' % y0e, (x0 - 4) * CM)
    else:
        sk.geometricConstraints.addHorizontalPoints(org, ll)
    dim_h(sk, ll, ur, '(%s) - (%s)' % (x1e, x0e), (y0 - 2) * CM)
    dim_v(sk, ll, ur, '(%s) - (%s)' % (y1e, y0e), (x0 - 2) * CM)
    return lines


def circle(sk, cxe, cye, dexpr):
    cx, cy, d = ev(cxe), ev(cye), ev(dexpr)
    c = sk.sketchCurves.sketchCircles.addByCenterRadius(P3(cx, cy), d * CM / 2)
    org = sk.originPoint
    if abs(cx) > 1e-9:
        dim_h(sk, org, c.centerSketchPoint, cxe if cx >= 0 else '-(%s)' % cxe, (cy - 6) * CM)
    if abs(cy) > 1e-9:
        dim_v(sk, org, c.centerSketchPoint, cye if cy >= 0 else '-(%s)' % cye, (cx - 6) * CM)
    dd = sk.sketchDimensions.addDiameterDimension(c, P3(cx + d, cy + d))
    dd.parameter.expression = dexpr
    return c


def profiles(sk, loops=None):
    col = adsk.core.ObjectCollection.create()
    for i in range(sk.profiles.count):
        pr = sk.profiles.item(i)
        if loops is None or pr.profileLoops.count == loops:
            col.add(pr)
    return col


def extrude(root, prof, op, dist_expr, name, body=None, negative=False):
    ext = root.features.extrudeFeatures
    inp = ext.createInput(prof, op)
    dist = adsk.core.ValueInput.createByString(dist_expr + ' mm' if is_number(dist_expr) else dist_expr)
    d = adsk.fusion.DistanceExtentDefinition.create(dist)
    direction = (adsk.fusion.ExtentDirections.NegativeExtentDirection if negative
                 else adsk.fusion.ExtentDirections.PositiveExtentDirection)
    inp.setOneSideExtent(d, direction)
    if body is not None:
        inp.participantBodies = [body]
    f = ext.add(inp)
    f.name = name
    return f


def optional(label, fn):
    try:
        fn()
    except Exception:
        SKIPPED.append('%s: %s' % (label, traceback.format_exc().strip().splitlines()[-1]))


def vertical_edges(body, length_mm, tol=0.05):
    """Edges parallel to Z with the given length (mm)."""
    out = adsk.core.ObjectCollection.create()
    for e in body.edges:
        g = e.geometry
        if isinstance(g, adsk.core.Line3D):
            dz = abs(g.endPoint.z - g.startPoint.z)
            dxy = abs(g.endPoint.x - g.startPoint.x) + abs(g.endPoint.y - g.startPoint.y)
            if dxy < 1e-6 and abs(dz / CM - length_mm) < tol:
                out.add(e)
    return out


def fillet_edges(root, edges, radius_expr, name):
    fil = root.features.filletFeatures
    inp = fil.createInput()
    inp.addConstantRadiusEdgeSet(edges, adsk.core.ValueInput.createByString(radius_expr), True)
    f = fil.add(inp)
    f.name = name
    return f


def face_edges_at_z(body, z_mm, normal_z, tol=0.01):
    """Outer edges of the planar face at height z with the given normal sign (+1 up, -1 down)."""
    out = adsk.core.ObjectCollection.create()
    for fc in body.faces:
        if fc.geometry.surfaceType != adsk.core.SurfaceTypes.PlaneSurfaceType:
            continue
        n = fc.geometry.normal
        if abs(abs(n.z) - 1) < 1e-6 and n.z * normal_z > 0 and abs(fc.centroid.z / CM - z_mm) < tol:
            for e in fc.edges:
                out.add(e)
    return out


def chamfer_edges(root, edges, dist_expr, name):
    ch = root.features.chamferFeatures
    inp = ch.createInput2()
    inp.chamferEdgeSets.addEqualDistanceChamferEdgeSet(edges, adsk.core.ValueInput.createByString(dist_expr), True)
    f = ch.add(inp)
    f.name = name
    return f


def run(context):
    step = 'init'
    try:
        app.documents.add(adsk.core.DocumentTypes.FusionDesignDocumentType)
        design = adsk.fusion.Design.cast(app.activeProduct)
        design.designType = adsk.fusion.DesignTypes.ParametricDesignType
        root = design.rootComponent
        step = 'parameters'
        add_params(design)
        NEW = adsk.fusion.FeatureOperations.NewBodyFeatureOperation
        JOIN = adsk.fusion.FeatureOperations.JoinFeatureOperation
        CUT = adsk.fusion.FeatureOperations.CutFeatureOperation
        V = VAL

        corners = [('wall + boss_d / 2', 'wall + boss_d / 2'),
                   ('outer_w - wall - boss_d / 2', 'wall + boss_d / 2'),
                   ('wall + boss_d / 2', 'outer_h - wall - boss_d / 2'),
                   ('outer_w - wall - boss_d / 2', 'outer_h - wall - boss_d / 2')]

        # ================================================================ BASE
        step = 'base: lower body'
        sk = root.sketches.add(root.xYConstructionPlane); sk.name = 'Base outline'
        rect(sk, '0', '0', 'outer_w', 'outer_h')
        base = extrude(root, profiles(sk), NEW, 'base_h - skirt_h', 'Base lower').bodies.item(0)
        base.name = 'Base'

        step = 'base: rebate step'
        pl_step = offset_plane(root, 'base_h - skirt_h')
        sk = root.sketches.add(pl_step); sk.name = 'Rebate step'
        rect(sk, 'rebate', 'rebate', 'outer_w - rebate', 'outer_h - rebate')
        extrude(root, profiles(sk), JOIN, 'skirt_h', 'Base upper (rebate)', base)

        optional('base outer corner fillets', lambda: (
            fillet_edges(root, vertical_edges(base, V['base_h'] - V['skirt_h']), 'corner_r', 'Base corners'),
            fillet_edges(root, vertical_edges(base, V['skirt_h']), 'corner_r - rebate', 'Base rebate corners')))

        step = 'base: cavity'
        pl_floor = offset_plane(root, 'floor_t')
        sk = root.sketches.add(pl_floor); sk.name = 'Cavity'
        rect(sk, 'wall', 'wall', 'outer_w - wall', 'outer_h - wall')
        extrude(root, profiles(sk), CUT, 'inner_d', 'Cavity cut', base)
        optional('base inner corner fillets', lambda: fillet_edges(
            root, vertical_edges(base, V['inner_d']), 'corner_r - wall', 'Cavity corners'))

        step = 'base: corner posts'
        sk = root.sketches.add(pl_floor); sk.name = 'Corner posts'
        for cx, cy in corners:
            circle(sk, cx, cy, 'boss_d')
        extrude(root, profiles(sk), JOIN, 'inner_d', 'Corner posts', base)

        step = 'base: pcb posts'
        sk = root.sketches.add(pl_floor); sk.name = 'PCB posts'
        for px, py in PCB_HOLES:
            circle(sk, 'pcb_x0 + %s' % px, 'pcb_ytop - %s' % py, 'boss_d')
        extrude(root, profiles(sk), JOIN, 'standoff', 'PCB posts', base)

        step = 'base: pcb supports'
        sk = root.sketches.add(pl_floor); sk.name = 'Support posts'
        for px, py in SUPPORTS:
            circle(sk, 'pcb_x0 + %s' % px, 'pcb_ytop - %s' % py, 'support_d')
        extrude(root, profiles(sk), JOIN, 'standoff', 'Support posts', base)
        sk = root.sketches.add(pl_floor); sk.name = 'PCB ledges'
        for py in LEDGES_LEFT:
            yc = 'pcb_ytop - %s' % py
            rect(sk, 'wall', '%s - ledge_len / 2' % yc, 'pcb_x0 + ledge_under', '%s + ledge_len / 2' % yc)
        for py in LEDGES_RIGHT:
            yc = 'pcb_ytop - %s' % py
            rect(sk, 'pcb_x0 + pcb_w - ledge_under', '%s - ledge_len / 2' % yc, 'outer_w - wall', '%s + ledge_len / 2' % yc)
        for px in LEDGES_TOP:
            xc = 'pcb_x0 + %s' % px
            rect(sk, '%s - ledge_len / 2' % xc, 'pcb_ytop - ledge_under', '%s + ledge_len / 2' % xc, 'outer_h - wall')
        extrude(root, profiles(sk), JOIN, 'standoff', 'PCB ledges', base)

        def guide_fins():
            s2 = root.sketches.add(pl_floor); s2.name = 'Guide fins'
            for py in LEDGES_LEFT:
                yc = 'pcb_ytop - %s' % py
                rect(s2, 'pcb_x0 - fin_gap - fin_t', '%s - ledge_len / 2' % yc, 'pcb_x0 - fin_gap', '%s + ledge_len / 2' % yc)
            for py in LEDGES_RIGHT:
                yc = 'pcb_ytop - %s' % py
                rect(s2, 'pcb_x0 + pcb_w + fin_gap', '%s - ledge_len / 2' % yc, 'pcb_x0 + pcb_w + fin_gap + fin_t', '%s + ledge_len / 2' % yc)
            for px in LEDGES_TOP:
                xc = 'pcb_x0 + %s' % px
                rect(s2, '%s - ledge_len / 2' % xc, 'pcb_ytop + fin_gap', '%s + ledge_len / 2' % xc, 'pcb_ytop + fin_gap + fin_t')
            extrude(root, profiles(s2), JOIN, 'standoff + pcb_t + fin_above', 'Guide fins', base)
        optional('guide fins', guide_fins)

        step = 'base: insert holes'
        pl_top = offset_plane(root, 'base_h')
        sk = root.sketches.add(pl_top); sk.name = 'Lid insert holes'
        for cx, cy in corners:
            circle(sk, cx, cy, 'insert_d')
        extrude(root, profiles(sk), CUT, 'insert_depth', 'Lid insert holes', base, negative=True)
        pl_rel_c = offset_plane(root, 'base_h - insert_depth')
        sk = root.sketches.add(pl_rel_c); sk.name = 'Lid screw relief'
        for cx, cy in corners:
            circle(sk, cx, cy, 'relief_d')
        extrude(root, profiles(sk), CUT, 'base_h - insert_depth - relief_floor', 'Lid screw relief', base, negative=True)
        pl_post = offset_plane(root, 'floor_t + standoff')
        sk = root.sketches.add(pl_post); sk.name = 'PCB insert holes'
        for px, py in PCB_HOLES:
            circle(sk, 'pcb_x0 + %s' % px, 'pcb_ytop - %s' % py, 'insert_d')
        extrude(root, profiles(sk), CUT, '5', 'PCB insert holes', base, negative=True)
        pl_rel_p = offset_plane(root, 'floor_t + standoff - 5')
        sk = root.sketches.add(pl_rel_p); sk.name = 'PCB screw relief'
        for px, py in PCB_HOLES:
            circle(sk, 'pcb_x0 + %s' % px, 'pcb_ytop - %s' % py, 'relief_d')
        extrude(root, profiles(sk), CUT, 'floor_t + standoff - 5 - relief_floor', 'PCB screw relief', base, negative=True)

        step = 'base: wire slots'
        pl_slot = offset_plane(root, 'floor_t + slot_z0')
        sk = root.sketches.add(pl_slot); sk.name = 'Wire slots'
        for a, b in SLOTS:
            rect(sk, 'pcb_x0 + %s' % a, '0', 'pcb_x0 + %s' % b, 'wall')
        extrude(root, profiles(sk), CUT, 'slot_h', 'Wire slots', base)

        step = 'base: vent slots'
        pl_vent = offset_plane(root, 'vent_z - vent_l / 2')
        sk = root.sketches.add(pl_vent); sk.name = 'Vent slots'
        for i in range(VENT_N):
            cx = 'outer_w / 2 + (%.1f) * vent_pitch' % (i - (VENT_N - 1) / 2.0)
            rect(sk, '%s - vent_w / 2' % cx, 'outer_h - wall', '%s + vent_w / 2' % cx, 'outer_h')
        extrude(root, profiles(sk), CUT, 'vent_l', 'Vent slots', base)

        step = 'base: ear rebates'
        ey = ['0.14 * outer_h', '0.86 * outer_h']

        def trapezoid(sk2, yc, half, xa, xb, mirror):
            """Plan-view trapezoid (numeric points: re-run the script after changing the tab parameters)."""
            pts = [(xa, yc - half(max(xa, 0))), (xb, yc - half(xb)), (xb, yc + half(xb)), (xa, yc + half(max(xa, 0)))]
            if mirror:
                pts = [(V['outer_w'] - x, y) for x, y in pts]
            for k in range(4):
                a, b = pts[k], pts[(k + 1) % 4]
                sk2.sketchCurves.sketchLines.addByTwoPoints(P3(a[0], a[1]), P3(b[0], b[1]))

        def slot_half(x):
            return V['ear_w'] / 2 + V['tab_gap'] - (V['tab_taper'] + V['tab_wedge']) * x / V['tab_l']

        def tab_half(x):
            return V['ear_w'] / 2 - V['tab_taper'] * x / V['tab_l']

        sk = root.sketches.add(root.xYConstructionPlane); sk.name = 'Ear rebates'
        for yexpr in ey:
            yc = ev(yexpr)
            trapezoid(sk, yc, slot_half, -1.0, V['tab_l'], False)
            trapezoid(sk, yc, slot_half, -1.0, V['tab_l'], True)
        extrude(root, profiles(sk), CUT, 'tab_t + tab_z_gap', 'Ear rebates', base)

        # ---- removable ear (separate body, printed flat; left-hand version, rotate 180 deg for the right side)
        step = 'ear'
        pl_ear = root.xYConstructionPlane
        sk = root.sketches.add(pl_ear); sk.name = 'Ear plate'
        rect(sk, '-ear_l', '-(ear_w + 12)', '0', '-12')
        ear = extrude(root, profiles(sk), NEW, 'ear_t', 'Ear plate').bodies.item(0)
        ear.name = 'Ear (print 4)'
        yc = -(V['ear_w'] / 2 + 12)
        sk = root.sketches.add(pl_ear); sk.name = 'Ear tab'
        trapezoid(sk, yc, tab_half, -0.01, V['tab_l'] - 0.2, False)
        extrude(root, profiles(sk), JOIN, 'tab_t', 'Ear tab', ear)
        sk = root.sketches.add(pl_ear); sk.name = 'Ear hole'
        circle(sk, '-ear_l / 2', '-(ear_w / 2 + 12)', 'ear_hole')
        extrude(root, profiles(sk), CUT, 'ear_t', 'Ear hole', ear)
        optional('ear corner fillets', lambda: fillet_edges(
            root, vertical_edges(ear, V['ear_t']), '3', 'Ear corners'))

        optional('base bottom chamfer', lambda: chamfer_edges(
            root, face_edges_at_z(base, 0.0, -1), 'chamfer_d', 'Base bottom chamfer'))

        # ================================================================ LID
        step = 'lid: plate'
        sk = root.sketches.add(pl_top); sk.name = 'Lid outline'
        rect(sk, '0', '0', 'outer_w', 'outer_h')
        lid = extrude(root, profiles(sk), NEW, 'lid_t', 'Lid plate').bodies.item(0)
        lid.name = 'Lid'

        step = 'lid: skirt'
        sk = root.sketches.add(pl_top); sk.name = 'Lid skirt'
        rect(sk, '0', '0', 'outer_w', 'outer_h')
        rect(sk, 'skirt_t', 'skirt_t', 'outer_w - skirt_t', 'outer_h - skirt_t')
        extrude(root, profiles(sk, loops=2), JOIN, 'skirt_h', 'Lid skirt', lid, negative=True)
        optional('lid corner fillets', lambda: (
            fillet_edges(root, vertical_edges(lid, V['lid_t'] + V['skirt_h']), 'corner_r', 'Lid corners'),
            fillet_edges(root, vertical_edges(lid, V['skirt_h']), 'corner_r - skirt_t', 'Lid skirt inner corners')))

        pl_lid_top = offset_plane(root, 'base_h + lid_t')
        step = 'lid: screw holes'
        sk = root.sketches.add(pl_lid_top); sk.name = 'Lid screw holes'
        for cx, cy in corners:
            circle(sk, cx, cy, 'screw_clear_d')
        extrude(root, profiles(sk), CUT, 'lid_t', 'Lid screw holes', lid, negative=True)
        sk = root.sketches.add(pl_lid_top); sk.name = 'Lid screw head recess'
        for cx, cy in corners:
            circle(sk, cx, cy, 'csk_d')
        extrude(root, profiles(sk), CUT, 'csk_h', 'Lid screw head recess', lid, negative=True)

        step = 'lid: cover pocket and window'
        sk = root.sketches.add(pl_lid_top); sk.name = 'Cover pocket'
        rect(sk, 'cover_x0 - cover_gap', 'cover_y0 - cover_gap',
             'cover_x0 + cover_w + cover_gap', 'cover_y1 + cover_gap')
        extrude(root, profiles(sk), CUT, 'pocket_d', 'Cover pocket', lid, negative=True)
        sk = root.sketches.add(pl_lid_top); sk.name = 'Cover window'
        rect(sk, 'cover_x0 + cover_ledge', 'cover_y0 + cover_ledge',
             'cover_x0 + cover_w - cover_ledge', 'cover_y1 - cover_ledge')
        extrude(root, profiles(sk), CUT, 'lid_t', 'Cover window (through)', lid, negative=True)
        pl_pocket = offset_plane(root, 'base_h + lid_t - pocket_d')

        def logo():
            """Imports the SVG, scales it to logo_h, centres it in the free area of the lid above the cover and recesses it by `inlay`."""
            import os
            svg = os.path.join(os.path.dirname(os.path.abspath(__file__)), LOGO_SVG)
            s2 = root.sketches.add(pl_lid_top); s2.name = 'Logo'
            s2.importSVG(svg, 0, 0, 1.0)
            ents = adsk.core.ObjectCollection.create()
            for c in s2.sketchCurves:
                ents.add(c)
            bb = s2.boundingBox
            k = V['logo_h'] * CM / (bb.maxPoint.y - bb.minPoint.y)
            s2.scale(ents, s2.originPoint, k)
            bb = s2.boundingBox
            mv = adsk.core.Matrix3D.create()
            mv.translation = adsk.core.Vector3D.create((V['outer_w'] / 2) * CM - (bb.minPoint.x + bb.maxPoint.x) / 2,
                                                       ((V['cover_y1'] + V['outer_h']) / 2) * CM - (bb.minPoint.y + bb.maxPoint.y) / 2, 0)
            s2.move(ents, mv)
            profs = [s2.profiles.item(i) for i in range(s2.profiles.count)]
            holes_of = [p for p in profs if p.profileLoops.count >= 2]   # letters with counters (P, R, A)
            col = adsk.core.ObjectCollection.create()
            for p in profs:
                pb = p.boundingBox
                inside = p.profileLoops.count == 1 and any(
                    h.boundingBox.minPoint.x < pb.minPoint.x and h.boundingBox.minPoint.y < pb.minPoint.y and
                    h.boundingBox.maxPoint.x > pb.maxPoint.x and h.boundingBox.maxPoint.y > pb.maxPoint.y
                    for h in holes_of)
                if not inside:                           # skip the counters, they are not part of the logo
                    col.add(p)
            extrude(root, col, CUT, 'inlay', 'Logo recess', lid, negative=True)
        optional('logo (SVG import)', logo)

        optional('lid top chamfer', lambda: chamfer_edges(
            root, face_edges_at_z(lid, V['base_h'] + V['lid_t'], +1), 'chamfer_d', 'Lid top chamfer'))

        # ================================================================ COVER
        step = 'cover: plate'
        pl_cov = offset_plane(root, 'base_h + lid_t - pocket_d')
        sk = root.sketches.add(pl_cov); sk.name = 'Cover outline'
        rect(sk, 'cover_x0', 'cover_y0', 'cover_x0 + cover_w', 'cover_y1')
        cover = extrude(root, profiles(sk), NEW, 'cover_t', 'Cover plate').bodies.item(0)
        cover.name = 'Cover'
        optional('cover corner fillets', lambda: fillet_edges(
            root, vertical_edges(cover, V['cover_t']), 'cover_r', 'Cover corners'))
        pl_cov_top = offset_plane(root, 'base_h + lid_t - pocket_d + cover_t')
        cxm = V['cover_x0'] + V['cover_w'] / 2
        cym = V['cover_y0'] + (V['cover_y1'] - V['cover_y0']) / 2

        def emblem():
            """Hazard triangle with a lightning bolt, recessed by `inlay` into the cover top."""
            cx = cxm
            s2 = root.sketches.add(pl_cov_top); s2.name = 'Emblem'
            R = 12.0
            outer = [(0, R), (-R * 0.866, -R * 0.5), (R * 0.866, -R * 0.5)]
            k = 0.62
            inner = [(0, R * k), (-R * 0.866 * k, -R * 0.5 * k), (R * 0.866 * k, -R * 0.5 * k)]
            for tri in (outer, inner):
                for i in range(3):
                    a, b = tri[i], tri[(i + 1) % 3]
                    s2.sketchCurves.sketchLines.addByTwoPoints(P3(cx + a[0], cym + a[1]), P3(cx + b[0], cym + b[1]))
            bolt = [(1.2, 5.0), (-3.0, -0.4), (-0.4, -0.4), (-1.6, -5.2), (3.2, 0.9), (0.5, 0.9)]
            sc = 1.05
            for i in range(len(bolt)):
                a, b = bolt[i], bolt[(i + 1) % len(bolt)]
                s2.sketchCurves.sketchLines.addByTwoPoints(P3(cx + a[0] * sc, cym + a[1] * sc - 1.5),
                                                          P3(cx + b[0] * sc, cym + b[1] * sc - 1.5))
            col = adsk.core.ObjectCollection.create()
            for i in range(s2.profiles.count):
                pr = s2.profiles.item(i)
                ar = pr.areaProperties().area            # cm2
                if (pr.profileLoops.count == 2 and ar > 0.6) or (pr.profileLoops.count == 1 and ar < 0.4):
                    col.add(pr)                          # triangle ring and the bolt
            extrude(root, col, CUT, 'inlay', 'Emblem recess', cover, negative=True)
        optional('emblem', emblem)


        msg = 'Done: bodies Base, Lid, Cover. Change Parameters (Modify) to resize.'
        if SKIPPED:
            msg += '\n\nSkipped optional steps:\n' + '\n'.join(SKIPPED)
        ui.messageBox(msg)
    except Exception:
        ui.messageBox('Failed at step "%s":\n%s' % (step, traceback.format_exc()))
