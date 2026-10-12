"""
Pramac autostart: parametric enclosure for Autodesk Fusion (Python script).

How to run: Fusion -> UTILITIES -> ADD-INS -> Scripts and Add-Ins (Shift+S) -> "+" -> pick this file -> Run.
It creates a new design with USER PARAMETERS (Modify -> Change Parameters) and three bodies:
Base, Lid and Cover. Sketches are dimensioned with the parameters, so editing a parameter
rebuilds the model through the timeline.

Frame: origin = outer bottom-left corner of the base, x to the right, y up (plan view), z from
the wall side (floor_t) towards the lid. The PCB top edge is at the high-y side; the cable gutter
is at the low-y side (bottom of the box when it hangs on the wall).

NOTE: written against the Fusion API without being run inside Fusion here; if a step fails, the
script shows the error text and the step name, and everything created up to that point remains.
"""
import traceback
import adsk.core
import adsk.fusion

# --------------------------------------------------------------------------------------------
# Parameters: (name, expression, comment). Plain numbers are millimetres.
# Expressions can reference earlier parameters. Edit the values here or later in Change Parameters.
# --------------------------------------------------------------------------------------------
PARAMS = [
    ('pcb_w', '93.3', 'PCB width'),
    ('pcb_h', '82.1', 'PCB height'),
    ('pcb_t', '1.6', 'PCB thickness'),
    ('margin_side', '6.5', 'free space left/right of the PCB'),
    ('margin_top', '6.5', 'free space above the PCB'),
    ('gutter', '24', 'cable area below the PCB'),
    ('wall', '2.6', 'wall thickness'),
    ('floor_t', '2.6', 'floor_t thickness'),
    ('standoff', '6', 'PCB standoff height (lead ends are 3.5 mm)'),
    ('comp_h', '40', 'free height above the PCB top (4700 uF caps are 36 mm)'),
    ('lid_t', '2.6', 'lid thickness'),
    ('boss_d', '7', 'post diameter'),
    ('insert_d', '4.2', 'hole for M3 brass insert'),
    ('insert_depth', '6', 'insert hole depth in the corner posts'),
    ('screw_clear_d', '3.4', 'M3 clearance hole'),
    ('slot_z0', '4', 'wire slot: height above the floor_t'),
    ('slot_h', '22', 'wire slot height'),
    ('term_y', '72', 'terminal row y on the PCB (from the top edge)'),
    ('open_x0', '2.5', 'lid opening left edge on the PCB (x)'),
    ('open_x1', '93', 'lid opening right edge on the PCB (x)'),
    ('open_h', '15', 'lid opening height'),
    ('cover_h', '24', 'cover plate height'),
    ('cover_t', '2.4', 'cover plate thickness'),
    ('cover_boss_d', '6', 'cover screw boss diameter'),
    ('cover_boss_h', '6', 'cover screw boss height (below the lid)'),
    ('vent_w', '2', 'vent slot width'),
    ('vent_l', '24', 'vent slot length'),
    ('vent_pitch', '10', 'vent slot pitch'),
    ('vent_z', '28', 'vent slot centre height above the floor_t'),
    ('ear_w', '14', 'wall-mount ear width'),
    ('ear_l', '16', 'wall-mount ear length'),
    ('ear_t', '3', 'wall-mount ear thickness'),
    ('ear_hole', '5.2', 'wall-mount hole diameter'),
    # derived
    ('inner_w', 'pcb_w + 2 * margin_side', 'derived'),
    ('inner_h', 'margin_top + pcb_h + gutter', 'derived'),
    ('inner_d', 'standoff + pcb_t + comp_h', 'derived'),
    ('outer_w', 'inner_w + 2 * wall', 'derived'),
    ('outer_h', 'inner_h + 2 * wall', 'derived'),
    ('base_h', 'floor_t + inner_d', 'derived'),
    ('pcb_x0', 'wall + margin_side', 'model x of the PCB left edge'),
    ('pcb_ytop', 'outer_h - wall - margin_top', 'model y of the PCB top edge'),
    ('cover_w', 'outer_w - 3', 'cover plate width'),
]

# PCB mounting holes (x from the left edge, y from the top edge) -> posts with brass inserts
PCB_HOLES = [(4.0, 37.0), (47.5, 76.5), (72.5, 75.0)]
# wire slots in the bottom wall, one per terminal block (J1, J4, J5, J6 contactor, J2): PCB x ranges
SLOTS = [(3.6, 13.0), (16.2, 25.6), (28.2, 37.5), (57.8, 67.2), (77.3, 91.7)]
VENT_N = 6

CM = 0.1  # API length unit is cm; parameters are in mm

app = adsk.core.Application.get()
ui = app.userInterface
VAL = {}   # name -> value in mm (for initial sketch geometry)


def P3(x, y, z=0.0):
    return adsk.core.Point3D.create(x * CM, y * CM, z * CM)


def ev(expr):
    return float(eval(expr, {}, VAL))


def is_number(s):
    try:
        float(s)
        return True
    except ValueError:
        return False


def add_params(design):
    ups = design.userParameters
    for name, expr, comment in PARAMS:
        val = ev(expr)
        VAL[name] = val
        e = (expr + ' mm') if is_number(expr) else expr
        ups.add(name, adsk.core.ValueInput.createByString(e), 'mm', comment)


def offset_plane(root, expr):
    planes = root.constructionPlanes
    pin = planes.createInput()
    pin.setByOffset(root.xYConstructionPlane, adsk.core.ValueInput.createByString(expr))
    return planes.add(pin)


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
    """Rectangle from (x0e, y0e) to (x1e, y1e) (expressions in mm, x0e < x1e, y0e < y1e).
    The lower-left corner is dimensioned from the sketch origin, width/height are dimensioned too,
    so editing parameters moves/resizes the rectangle."""
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


def all_profiles(sk):
    col = adsk.core.ObjectCollection.create()
    for i in range(sk.profiles.count):
        col.add(sk.profiles.item(i))
    return col


def extrude(root, sk, op, dist_expr, name, body=None, negative=False):
    ext = root.features.extrudeFeatures
    inp = ext.createInput(all_profiles(sk), op)
    dist = adsk.core.ValueInput.createByString(dist_expr + ' mm' if is_number(dist_expr) else dist_expr)
    d = adsk.fusion.DistanceExtentDefinition.create(dist)
    direction = adsk.fusion.ExtentDirections.NegativeExtentDirection if negative else adsk.fusion.ExtentDirections.PositiveExtentDirection
    inp.setOneSideExtent(d, direction)
    if body is not None:
        inp.participantBodies = [body]
    f = ext.add(inp)
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

        # ---------------------------------------------------------------- base shell
        step = 'base shell'
        sk = root.sketches.add(root.xYConstructionPlane); sk.name = 'Base outline'
        rect(sk, '0', '0', 'outer_w', 'outer_h')
        base = extrude(root, sk, NEW, 'base_h', 'Base body').bodies.item(0)
        base.name = 'Base'

        step = 'base cavity'
        pl_floor = offset_plane(root, 'floor_t')
        sk = root.sketches.add(pl_floor); sk.name = 'Cavity'
        rect(sk, 'wall', 'wall', 'outer_w - wall', 'outer_h - wall')
        extrude(root, sk, CUT, 'inner_d', 'Cavity cut', base)

        # corner posts for the lid screws
        step = 'corner posts'
        corners = [('wall + boss_d / 2', 'wall + boss_d / 2'),
                   ('outer_w - wall - boss_d / 2', 'wall + boss_d / 2'),
                   ('wall + boss_d / 2', 'outer_h - wall - boss_d / 2'),
                   ('outer_w - wall - boss_d / 2', 'outer_h - wall - boss_d / 2')]
        sk = root.sketches.add(pl_floor); sk.name = 'Corner posts'
        for cx, cy in corners:
            circle(sk, cx, cy, 'boss_d')
        extrude(root, sk, JOIN, 'inner_d', 'Corner posts', base)

        # PCB posts
        step = 'pcb posts'
        sk = root.sketches.add(pl_floor); sk.name = 'PCB posts'
        for px, py in PCB_HOLES:
            circle(sk, 'pcb_x0 + %s' % px, 'pcb_ytop - %s' % py, 'boss_d')
        extrude(root, sk, JOIN, 'standoff', 'PCB posts', base)

        # insert holes (corner posts from the top, PCB posts from their top face)
        step = 'insert holes'
        pl_top = offset_plane(root, 'base_h')
        sk = root.sketches.add(pl_top); sk.name = 'Lid insert holes'
        for cx, cy in corners:
            circle(sk, cx, cy, 'insert_d')
        extrude(root, sk, CUT, 'insert_depth', 'Lid insert holes', base, negative=True)
        pl_post = offset_plane(root, 'floor_t + standoff')
        sk = root.sketches.add(pl_post); sk.name = 'PCB insert holes'
        for px, py in PCB_HOLES:
            circle(sk, 'pcb_x0 + %s' % px, 'pcb_ytop - %s' % py, 'insert_d')
        extrude(root, sk, CUT, '5', 'PCB insert holes', base, negative=True)

        # wire slots in the bottom wall (rectangles in plan, cut upward)
        step = 'wire slots'
        pl_slot = offset_plane(root, 'floor_t + slot_z0')
        sk = root.sketches.add(pl_slot); sk.name = 'Wire slots'
        for a, b in SLOTS:
            rect(sk, 'pcb_x0 + %s' % a, '0', 'pcb_x0 + %s' % b, 'wall')
        extrude(root, sk, CUT, 'slot_h', 'Wire slots', base)

        # vent slots in the top wall
        step = 'vent slots'
        pl_vent = offset_plane(root, 'vent_z - vent_l / 2')
        sk = root.sketches.add(pl_vent); sk.name = 'Vent slots'
        n = VENT_N
        for i in range(n):
            off = '(%.1f) * vent_pitch' % (i - (n - 1) / 2.0)
            cx = 'outer_w / 2 + %s' % off
            rect(sk, '%s - vent_w / 2' % cx, 'outer_h - wall', '%s + vent_w / 2' % cx, 'outer_h')
        extrude(root, sk, CUT, 'vent_l', 'Vent slots', base)

        # wall-mount ears
        step = 'ears'
        sk = root.sketches.add(root.xYConstructionPlane); sk.name = 'Ears'
        ey = ['0.14 * outer_h', '0.86 * outer_h']
        for yexpr in ey:
            rect(sk, '-ear_l', '%s - ear_w / 2' % yexpr, 'wall', '%s + ear_w / 2' % yexpr)
            rect(sk, 'outer_w - wall', '%s - ear_w / 2' % yexpr, 'outer_w + ear_l', '%s + ear_w / 2' % yexpr)
        extrude(root, sk, JOIN, 'ear_t', 'Ears', base)
        sk = root.sketches.add(root.xYConstructionPlane); sk.name = 'Ear holes'
        for yexpr in ey:
            circle(sk, '-ear_l / 2', yexpr, 'ear_hole')
            circle(sk, 'outer_w + ear_l / 2', yexpr, 'ear_hole')
        extrude(root, sk, CUT, 'ear_t', 'Ear holes', base)

        # ---------------------------------------------------------------- lid
        step = 'lid'
        sk = root.sketches.add(pl_top); sk.name = 'Lid outline'
        rect(sk, '0', '0', 'outer_w', 'outer_h')
        lid = extrude(root, sk, NEW, 'lid_t', 'Lid body').bodies.item(0)
        lid.name = 'Lid'
        pl_lid_top = offset_plane(root, 'base_h + lid_t')
        sk = root.sketches.add(pl_lid_top); sk.name = 'Lid screw holes'
        for cx, cy in corners:
            circle(sk, cx, cy, 'screw_clear_d')
        extrude(root, sk, CUT, 'lid_t', 'Lid screw holes', lid, negative=True)

        step = 'lid cover bosses'
        cb = [('wall + 3', 'pcb_ytop - term_y'), ('outer_w - wall - 3', 'pcb_ytop - term_y')]
        sk = root.sketches.add(pl_top); sk.name = 'Cover bosses'
        for cx, cy in cb:
            circle(sk, cx, cy, 'cover_boss_d')
        extrude(root, sk, JOIN, 'cover_boss_h', 'Cover bosses', lid, negative=True)
        pl_boss = offset_plane(root, 'base_h - cover_boss_h')
        sk = root.sketches.add(pl_boss); sk.name = 'Cover insert holes'
        for cx, cy in cb:
            circle(sk, cx, cy, 'insert_d')
        extrude(root, sk, CUT, 'cover_boss_h', 'Cover insert holes', lid)
        sk = root.sketches.add(pl_lid_top); sk.name = 'Cover screw holes'
        for cx, cy in cb:
            circle(sk, cx, cy, 'screw_clear_d')
        extrude(root, sk, CUT, 'lid_t', 'Cover screw holes', lid, negative=True)

        step = 'lid opening'
        sk = root.sketches.add(pl_lid_top); sk.name = 'Lid opening'
        rect(sk, 'pcb_x0 + open_x0', 'pcb_ytop - term_y - open_h / 2', 'pcb_x0 + open_x1', 'pcb_ytop - term_y + open_h / 2')
        extrude(root, sk, CUT, 'lid_t', 'Lid opening', lid, negative=True)

        # ---------------------------------------------------------------- cover plate
        step = 'cover'
        sk = root.sketches.add(pl_lid_top); sk.name = 'Cover outline'
        rect(sk, 'outer_w / 2 - cover_w / 2', 'pcb_ytop - term_y - cover_h / 2',
             'outer_w / 2 + cover_w / 2', 'pcb_ytop - term_y + cover_h / 2')
        cover = extrude(root, sk, NEW, 'cover_t', 'Cover body').bodies.item(0)
        cover.name = 'Cover'
        pl_cov_top = offset_plane(root, 'base_h + lid_t + cover_t')
        sk = root.sketches.add(pl_cov_top); sk.name = 'Cover holes'
        for cx, cy in cb:
            circle(sk, cx, cy, 'screw_clear_d')
        extrude(root, sk, CUT, 'cover_t', 'Cover holes', cover, negative=True)

        ui.messageBox('Done: bodies Base, Lid, Cover. Change Parameters (Modify) to resize.')
    except Exception:
        ui.messageBox('Failed at step "%s":\n%s' % (step, traceback.format_exc()))
