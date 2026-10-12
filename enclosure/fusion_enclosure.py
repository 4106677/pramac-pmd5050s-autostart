"""
Pramac autostart: parametric enclosure for Autodesk Fusion (Python script), v2.

Run: Fusion -> UTILITIES -> ADD-INS -> Scripts and Add-Ins (Shift+S) -> "+" -> pick this file -> Run.
It creates a new parametric design with USER PARAMETERS (Modify -> Change Parameters) and three bodies:
Base, Lid (with a skirt that wraps over a rebate on the base walls) and Cover (with a hazard emblem).
Sketches are dimensioned with the parameters, so editing a parameter rebuilds the model through the timeline.

Frame: origin = outer bottom-left corner of the base, x to the right, y up (plan view), z from the wall
side (floor) towards the lid. The PCB top edge is at the high-y side; the cable gutter is at the low-y side.

The core geometry is created first. Cosmetic steps (rounded corners, chamfers, emblem, pegs) are "optional":
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
    ('screw_clear_d', '3.4', 'M3 clearance hole'),
    ('csk_d', '6.8', 'screw head recess diameter in the lid'),
    ('csk_h', '1.7', 'screw head recess depth'),
    ('slot_z0', '4', 'wire slot: height above the floor'),
    ('slot_h', '22', 'wire slot height'),
    ('term_y', '72', 'terminal row y on the PCB (from the top edge)'),
    ('open_x0', '2.5', 'lid opening left edge on the PCB (x)'),
    ('open_x1', '93', 'lid opening right edge on the PCB (x)'),
    ('open_h', '15', 'lid opening height'),
    ('cover_w', '100', 'cover plate width'),
    ('cover_top_y', '60', 'cover top edge on the PCB (y from the PCB top)'),
    ('cover_bottom', '4.5', 'cover bottom edge above the lid edge'),
    ('cover_t', '2.4', 'cover plate thickness'),
    ('cover_r', '4', 'cover corner radius'),
    ('cover_gap', '0.25', 'cover pocket clearance'),
    ('cover_boss_d', '6.5', 'cover screw boss diameter'),
    ('cover_boss_h', '6', 'cover screw boss height (below the lid)'),
    ('peg_d', '3', 'cover peg diameter'),
    ('peg_l', '1.6', 'cover peg length'),
    ('vent_w', '2', 'vent slot width'),
    ('vent_l', '24', 'vent slot length'),
    ('vent_pitch', '10', 'vent slot pitch'),
    ('vent_z', '30', 'vent slot centre height above the floor'),
    ('ear_w', '14', 'wall-mount ear width'),
    ('ear_l', '16', 'wall-mount ear length'),
    ('ear_t', '3.2', 'wall-mount ear thickness'),
    ('ear_hole', '5.2', 'wall-mount hole diameter'),
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
]

PCB_HOLES = [(4.0, 37.0), (47.5, 76.5), (72.5, 75.0)]               # PCB mounting holes (x from left, y from top)
SLOTS = [(3.6, 13.0), (16.2, 25.6), (28.2, 37.5), (57.8, 67.2), (77.3, 91.7)]   # wire slots, PCB x ranges
VENT_N = 6

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

        step = 'base: insert holes'
        pl_top = offset_plane(root, 'base_h')
        sk = root.sketches.add(pl_top); sk.name = 'Lid insert holes'
        for cx, cy in corners:
            circle(sk, cx, cy, 'insert_d')
        extrude(root, profiles(sk), CUT, 'insert_depth', 'Lid insert holes', base, negative=True)
        pl_post = offset_plane(root, 'floor_t + standoff')
        sk = root.sketches.add(pl_post); sk.name = 'PCB insert holes'
        for px, py in PCB_HOLES:
            circle(sk, 'pcb_x0 + %s' % px, 'pcb_ytop - %s' % py, 'insert_d')
        extrude(root, profiles(sk), CUT, '5', 'PCB insert holes', base, negative=True)

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

        step = 'base: ears'
        sk = root.sketches.add(root.xYConstructionPlane); sk.name = 'Ears'
        ey = ['0.14 * outer_h', '0.86 * outer_h']
        for yexpr in ey:
            rect(sk, '-ear_l', '%s - ear_w / 2' % yexpr, 'wall', '%s + ear_w / 2' % yexpr)
            rect(sk, 'outer_w - wall', '%s - ear_w / 2' % yexpr, 'outer_w + ear_l', '%s + ear_w / 2' % yexpr)
        extrude(root, profiles(sk), JOIN, 'ear_t', 'Ears', base)
        sk = root.sketches.add(root.xYConstructionPlane); sk.name = 'Ear holes'
        for yexpr in ey:
            circle(sk, '-ear_l / 2', yexpr, 'ear_hole')
            circle(sk, 'outer_w + ear_l / 2', yexpr, 'ear_hole')
        extrude(root, profiles(sk), CUT, 'ear_t', 'Ear holes', base)

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

        step = 'lid: cover pocket and opening'
        sk = root.sketches.add(pl_lid_top); sk.name = 'Cover pocket'
        rect(sk, 'cover_x0 - cover_gap', 'cover_y0 - cover_gap',
             'cover_x0 + cover_w + cover_gap', 'cover_y1 + cover_gap')
        extrude(root, profiles(sk), CUT, 'pocket_d', 'Cover pocket', lid, negative=True)
        pl_pocket = offset_plane(root, 'base_h + lid_t - pocket_d')
        sk = root.sketches.add(pl_pocket); sk.name = 'Lid opening'
        rect(sk, 'pcb_x0 + open_x0', 'pcb_ytop - term_y - open_h / 2', 'pcb_x0 + open_x1', 'pcb_ytop - term_y + open_h / 2')
        extrude(root, profiles(sk), CUT, 'lid_t - pocket_d', 'Lid opening', lid, negative=True)

        step = 'lid: cover bosses'
        cb = [('cover_x0 + 14', 'cover_y0 + 5'), ('cover_x0 + cover_w - 14', 'cover_y0 + 5')]
        sk = root.sketches.add(pl_top); sk.name = 'Cover bosses'
        for cx, cy in cb:
            circle(sk, cx, cy, 'cover_boss_d')
        extrude(root, profiles(sk), JOIN, 'cover_boss_h', 'Cover bosses', lid, negative=True)
        pl_boss = offset_plane(root, 'base_h - cover_boss_h')
        sk = root.sketches.add(pl_boss); sk.name = 'Cover insert holes'
        for cx, cy in cb:
            circle(sk, cx, cy, 'insert_d')
        extrude(root, profiles(sk), CUT, 'cover_boss_h', 'Cover insert holes', lid)
        sk = root.sketches.add(pl_pocket); sk.name = 'Cover screw holes (lid)'
        for cx, cy in cb:
            circle(sk, cx, cy, 'screw_clear_d')
        extrude(root, profiles(sk), CUT, 'lid_t - pocket_d', 'Cover screw holes (lid)', lid, negative=True)

        pegs = [('cover_x0 + cover_w * 0.25', 'cover_y1 - 4'), ('cover_x0 + cover_w * 0.75', 'cover_y1 - 4')]

        def peg_holes():
            s2 = root.sketches.add(pl_pocket); s2.name = 'Peg holes'
            for cx, cy in pegs:
                circle(s2, cx, cy, 'peg_d + 0.4')
            extrude(root, profiles(s2), CUT, 'peg_l + 0.4', 'Peg holes', lid, negative=True)
        optional('peg holes', peg_holes)

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
        sk = root.sketches.add(pl_cov_top); sk.name = 'Cover screw holes'
        for cx, cy in cb:
            circle(sk, cx, cy, 'screw_clear_d')
        extrude(root, profiles(sk), CUT, 'cover_t', 'Cover screw holes', cover, negative=True)

        def cover_pegs():
            s2 = root.sketches.add(pl_cov); s2.name = 'Cover pegs'
            for cx, cy in pegs:
                circle(s2, cx, cy, 'peg_d')
            extrude(root, profiles(s2), JOIN, 'peg_l', 'Cover pegs', cover, negative=True)
        optional('cover pegs', cover_pegs)

        def emblem():
            """Hazard triangle (raised 0.6 mm) with a lightning bolt, centred on the cover."""
            cxm = V['cover_x0'] + V['cover_w'] / 2
            cym = V['cover_y0'] + (V['cover_y1'] - V['cover_y0']) * 0.62
            s2 = root.sketches.add(pl_cov_top); s2.name = 'Emblem'
            R = 15.0
            outer = [(0, R), (-R * 0.866, -R * 0.5), (R * 0.866, -R * 0.5)]
            k = 0.62
            inner = [(0, R * k), (-R * 0.866 * k, -R * 0.5 * k), (R * 0.866 * k, -R * 0.5 * k)]
            for tri in (outer, inner):
                for i in range(3):
                    a, b = tri[i], tri[(i + 1) % 3]
                    s2.sketchCurves.sketchLines.addByTwoPoints(P3(cxm + a[0], cym + a[1]), P3(cxm + b[0], cym + b[1]))
            bolt = [(1.2, 5.0), (-3.0, -0.4), (-0.4, -0.4), (-1.6, -5.2), (3.2, 0.9), (0.5, 0.9)]
            sc = 1.3
            for i in range(len(bolt)):
                a, b = bolt[i], bolt[(i + 1) % len(bolt)]
                s2.sketchCurves.sketchLines.addByTwoPoints(P3(cxm + a[0] * sc, cym + a[1] * sc - 1.5),
                                                          P3(cxm + b[0] * sc, cym + b[1] * sc - 1.5))
            col = adsk.core.ObjectCollection.create()
            for i in range(s2.profiles.count):
                pr = s2.profiles.item(i)
                ar = pr.areaProperties().area            # cm2
                if (pr.profileLoops.count == 2 and ar > 0.6) or (pr.profileLoops.count == 1 and ar < 0.4):
                    col.add(pr)                          # triangle ring and the bolt
            extrude(root, col, JOIN, '0.6', 'Emblem', cover)
        optional('emblem', emblem)

        msg = 'Done: bodies Base, Lid, Cover. Change Parameters (Modify) to resize.'
        if SKIPPED:
            msg += '\n\nSkipped optional steps:\n' + '\n'.join(SKIPPED)
        ui.messageBox(msg)
    except Exception:
        ui.messageBox('Failed at step "%s":\n%s' % (step, traceback.format_exc()))
