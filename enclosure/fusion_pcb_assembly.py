"""Fusion 360 script: the v5 carrier board with its components, the fasteners, and the colours of the whole assembly.

Run it in the design built by fusion_enclosure.py (Utilities > Scripts and Add-Ins, or through the Fusion MCP server).
It adds bodies to the root component (a Part Design document cannot hold sub-components), one base feature
per group, all named 'PCB asm: ...' in the timeline:
  * the board, solder, ESP32 DevKit V1 in its sockets, relays, terminal blocks, capacitors,
    diodes, resistors (with colour bands), transistors, LM393, headers, RM20S-050, fuse;
  * 'Fasteners': M3 heat-set brass inserts and M3x8 ISO 7380 button-head screws (3 for the PCB, 4 for the lid).
and colours the enclosure: base, ears and lid white ABS; the cover insert and the Pramac logo red (#C01717);
the high-voltage emblem white on the red insert.

Geometry is simplified (no text, no threads), dimensions follow the datasheets and the KiCad footprints of
hardware/pramac_carrier.kicad_pcb (coordinates below are KiCad mm: x right, y down from the board top-left corner).
Re-running the script deletes the 'PCB asm: ...' base features and builds them again.
Board v5.1: the ESP32 sits 2 mm higher than on v5 and the 1 F supercapacitor SC1 stands on its own footprint
between the module and the K1/K2 relays.
"""
import adsk.core, adsk.fusion, math

CM = 0.1
UNION = adsk.fusion.BooleanTypes.UnionBooleanType
DIFF = adsk.fusion.BooleanTypes.DifferenceBooleanType
INTER = adsk.fusion.BooleanTypes.IntersectionBooleanType

# through-hole pads: (x, y, pad size, drill)
PADS = [(6.5, 53.2, 2, 1), (6.5, 48.12, 2, 1), (53, 5, 1.7, 1), (55.54, 5, 1.7, 1), (58.08, 5, 1.7, 1),
        (60.62, 5, 1.7, 1), (63.16, 5, 1.7, 1), (65.7, 5, 1.7, 1), (68.24, 5, 1.7, 1), (70.78, 5, 1.7, 1),
        (73.32, 5, 1.7, 1), (75.86, 5, 1.7, 1), (78.4, 5, 1.7, 1), (80.94, 5, 1.7, 1), (83.48, 5, 1.7, 1),
        (86.02, 5, 1.7, 1), (88.56, 5, 1.7, 1), (44, 65.8, 1.05, 0.75), (45.27, 65.8, 1.05, 0.75),
        (46.54, 65.8, 1.05, 0.75), (9, 13, 2.4, 1.2), (16.5, 13, 2.4, 1.2), (41.9, 37.3, 1.8, 1),
        (53.7, 37.3, 1.8, 1), (79.5, 18.2, 1.6, 0.8), (82.04, 18.2, 1.6, 0.8), (62, 12.6, 1.05, 0.75),
        (63.27, 12.6, 1.05, 0.75), (64.54, 12.6, 1.05, 0.75), (79.6, 61.2, 1.6, 0.8), (82.14, 61.2, 1.6, 0.8),
        (80, 38.5, 1.6, 0.8), (80, 41.04, 1.6, 0.8), (80, 43.58, 1.6, 0.8), (80, 46.12, 1.6, 0.8),
        (87.62, 46.12, 1.6, 0.8), (87.62, 43.58, 1.6, 0.8), (87.62, 41.04, 1.6, 0.8), (87.62, 38.5, 1.6, 0.8),
        (63.5, 62.5, 3, 1.3), (69.55, 60.55, 2.5, 1), (69.55, 48.35, 3, 1.3), (57.5, 48.3, 3, 1.3),
        (57.55, 60.55, 2.5, 1), (3.5, 43.2, 2.4, 1.2), (7.31, 43.2, 2.4, 1.2), (6, 72, 2.6, 1.4),
        (11, 72, 2.6, 1.4), (89.8, 50.5, 1.7, 1), (89.8, 53.04, 1.7, 1), (89.8, 55.58, 1.7, 1),
        (89.8, 58.12, 1.7, 1), (72.5, 42, 1.6, 0.8), (75.04, 42, 1.6, 0.8), (30, 72, 2.6, 1.4), (35, 72, 2.6, 1.4),
        (79.5, 72, 2.6, 1.4), (84.5, 72, 2.6, 1.4), (89.5, 72, 2.6, 1.4), (37, 26.5, 2, 1.2), (37, 29.04, 2, 1.2),
        (37, 31.58, 2, 1.2), (79.5, 12.6, 1.6, 0.8), (82.04, 12.6, 1.6, 0.8), (53, 30.4, 1.7, 1),
        (55.54, 30.4, 1.7, 1), (58.08, 30.4, 1.7, 1), (60.62, 30.4, 1.7, 1), (63.16, 30.4, 1.7, 1),
        (65.7, 30.4, 1.7, 1), (68.24, 30.4, 1.7, 1), (70.78, 30.4, 1.7, 1), (73.32, 30.4, 1.7, 1),
        (75.86, 30.4, 1.7, 1), (78.4, 30.4, 1.7, 1), (80.94, 30.4, 1.7, 1), (83.48, 30.4, 1.7, 1),
        (86.02, 30.4, 1.7, 1), (88.56, 30.4, 1.7, 1), (27.5, 44, 3, 1.3), (21.45, 45.95, 2.5, 1),
        (21.45, 58.15, 3, 1.3), (33.5, 58.2, 3, 1.3), (33.45, 45.95, 2.5, 1), (62, 18.2, 1.05, 0.75),
        (63.27, 18.2, 1.05, 0.75), (64.54, 18.2, 1.05, 0.75), (79.6, 56.5, 1.6, 0.8), (82.14, 56.5, 1.6, 0.8),
        (18.2, 29.5, 3.2, 1.6), (14.39, 29.5, 3.2, 1.6), (29, 13, 2.4, 1.2), (36.5, 13, 2.4, 1.2),
        (27.3, 29.5, 3.2, 1.6), (23.49, 29.5, 3.2, 1.6), (73.5, 12.6, 1.6, 0.8), (76.04, 12.6, 1.6, 0.8),
        (49.5, 65.8, 1.6, 0.8), (52.04, 65.8, 1.6, 0.8), (80, 49.6, 1.6, 0.8), (82.54, 49.6, 1.6, 0.8),
        (18, 72, 2.6, 1.4), (23, 72, 2.6, 1.4), (60, 72, 2.4, 1.4), (65, 72, 2.4, 1.4), (80, 53.3, 1.6, 0.8),
        (82.54, 53.3, 1.6, 0.8), (87.9, 61.2, 1.6, 0.8), (85.36, 61.2, 1.6, 0.8), (60.8, 39.8, 1.6, 0.8),
        (62.8, 39.8, 1.6, 0.8), (66.5, 38.6, 1.6, 0.8), (69.04, 38.6, 1.6, 0.8), (44, 69.3, 1.6, 0.8),
        (46.54, 69.3, 1.6, 0.8), (66.5, 42, 1.6, 0.8), (69.04, 42, 1.6, 0.8), (72.5, 38.6, 1.6, 0.8),
        (75.04, 38.6, 1.6, 0.8), (49.5, 69.3, 1.6, 0.8), (52.04, 69.3, 1.6, 0.8), (67.5, 12.6, 1.6, 0.8),
        (70.04, 12.6, 1.6, 0.8), (45.5, 44, 3, 1.3), (39.45, 45.95, 2.5, 1), (39.45, 58.15, 3, 1.3),
        (51.5, 58.2, 3, 1.3), (51.45, 45.95, 2.5, 1), (67.5, 18.2, 1.6, 0.8), (70.04, 18.2, 1.6, 0.8),
        (73.5, 18.2, 1.6, 0.8), (76.04, 18.2, 1.6, 0.8)]
PCB_HOLES = [(4.0, 37.0), (47.5, 76.5), (72.5, 75.0)]
BW, BH = 93.2, 82.0

# appearance name -> (library appearance to copy, colour or None to keep the library colour)
LOOKS = {
    'ABS white': ('Plastic - Matte (White)', (238, 238, 234)),
    'ABS red Pramac': ('Plastic - Matte (Red)', (192, 23, 23)),
    'Solder mask green': ('Plastic - Glossy (Green)', (16, 92, 38)),
    'HASL tin': ('Nickel - Satin', None),
    'Gold': ('Gold - Polished', None),
    'Brass': ('Brass - Polished', None),
    'Stainless steel': ('Stainless Steel - Satin', None),
    'Nickel': ('Nickel - Polished', None),
    'Aluminum': ('Aluminum - Satin', None),
    'Black matte': ('Plastic - Matte (Black)', (28, 28, 28)),
    'Black glossy': ('Plastic - Glossy (Black)', (14, 14, 16)),
    'Relay blue': ('Plastic - Glossy (Blue)', (25, 80, 170)),
    'Terminal green': ('Plastic - Matte (Green)', (40, 135, 60)),
    'Resistor blue': ('Plastic - Glossy (Blue)', (125, 172, 214)),
    'Cap stripe grey': ('Plastic - Glossy (Grey)', (175, 175, 180)),
    'Ceramic tan': ('Plastic - Matte (Yellow)', (185, 150, 105)),
    'Glass orange': ('Plastic - Translucent Glossy (Red)', (235, 95, 35)),
    'Band black': ('Plastic - Glossy (Black)', (10, 10, 10)),
    'Band brown': ('Plastic - Glossy (Red)', (105, 55, 25)),
    'Band red': ('Plastic - Glossy (Red)', (205, 25, 25)),
    'Band orange': ('Plastic - Glossy (Yellow)', (240, 125, 20)),
    'Band yellow': ('Plastic - Glossy (Yellow)', (245, 210, 25)),
    'Band violet': ('Plastic - Glossy (Blue)', (125, 55, 170)),
    'LED red': ('LED (Red)', None),
    'LED blue': ('LED (Blue)', None),
}

app = adsk.core.Application.get()
tbm = adsk.fusion.TemporaryBRepManager.get()
X0 = Y0 = ZT = 0.0
GROUP_PREFIX = 'PCB asm: '   # set in run(): model position of the PCB top-left corner and of the PCB top face


def pt(x, y, z):
    return adsk.core.Point3D.create(x * CM, y * CM, z * CM)


def abox(x0, y0, z0, x1, y1, z1):
    x0, x1 = min(x0, x1), max(x0, x1); y0, y1 = min(y0, y1), max(y0, y1); z0, z1 = min(z0, z1), max(z0, z1)
    obb = adsk.core.OrientedBoundingBox3D.create(pt((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2),
                                                 adsk.core.Vector3D.create(1, 0, 0), adsk.core.Vector3D.create(0, 1, 0),
                                                 (x1 - x0) * CM, (y1 - y0) * CM, (z1 - z0) * CM)
    return tbm.createBox(obb)


def acyl(x, y, z0, z1, r, r2=None):
    return tbm.createCylinderOrCone(pt(x, y, z0), r * CM, pt(x, y, z1), (r if r2 is None else r2) * CM)


def kp(kx, ky, h):
    """KiCad x/y + height above the PCB top -> model point."""
    return pt(X0 + kx, Y0 - ky, ZT + h)


def kbox(kx0, ky0, kx1, ky1, h0, h1):
    return abox(X0 + kx0, Y0 - ky0, ZT + h0, X0 + kx1, Y0 - ky1, ZT + h1)


def kcyl(kx, ky, h0, h1, r, r2=None):
    return acyl(X0 + kx, Y0 - ky, ZT + h0, ZT + h1, r, r2)


def ksph(p, r):
    return tbm.createSphere(kp(*p), r * CM)


def U(*bodies):
    bodies = [b for b in bodies if b is not None]
    t = bodies[0]
    for b in bodies[1:]:
        tbm.booleanOperation(t, b, UNION)
    return t


def D(t, *tools):
    for b in tools:
        tbm.booleanOperation(t, b, DIFF)
    return t


def I(t, b):
    tbm.booleanOperation(t, b, INTER)
    return t


def wire(points, r):
    """Bent lead through (kx, ky, h) points."""
    parts = [tbm.createCylinderOrCone(kp(*a), r * CM, kp(*b), r * CM) for a, b in zip(points, points[1:])]
    parts += [ksph(p, r) for p in points[1:-1]]
    return U(*parts)


def hex_prism(x, y, z0, z1, af):
    t = None
    for a in (0, 60, 120):
        ca, sa = math.cos(math.radians(a)), math.sin(math.radians(a))
        obb = adsk.core.OrientedBoundingBox3D.create(pt(x, y, (z0 + z1) / 2), adsk.core.Vector3D.create(ca, sa, 0),
                                                     adsk.core.Vector3D.create(-sa, ca, 0), af * CM, 3 * af * CM, (z1 - z0) * CM)
        b = tbm.createBox(obb)
        t = b if t is None else I(t, b)
    return t


class Parts:
    def __init__(self):
        self.groups = {}

    def add(self, comp, name, body, look):
        self.groups.setdefault(comp, []).append((name, body, look))


# ------------------------------------------------------------------ components
def board(P):
    b = kbox(0, 0, BW, BH, -1.6, 0)
    D(b, *[kcyl(x, y, -2, 1, 1.6) for x, y in PCB_HOLES])
    P.add('PCB', 'Board 93.2x82 FR4', b, 'Solder mask green')
    P.add('PCB', 'Pads (HASL)', U(*[D(kcyl(x, y, 0, 0.04, s / 2), kcyl(x, y, -1, 1, dr / 2)) for x, y, s, dr in PADS]), 'HASL tin')
    P.add('PCB', 'Solder joints', U(*[kcyl(x, y, -1.6, -2.8, min(s / 2, 1.3) * 0.9, 0.3) for x, y, s, dr in PADS]), 'HASL tin')


def esp32(P):
    C = 'ESP32 DevKit V1'
    rows = (5.0, 30.4)                                  # board v5.1 (v5: 7.0, 32.4)
    pins = [53.0 + 2.54 * i for i in range(15)]
    P.add(C, 'U1A/U1B sockets 1x15', U(*[D(kbox(51.73, y - 1.27, 89.83, y + 1.27, 0, 8.5),
                                            *[kbox(x - 0.5, y - 0.5, x + 0.5, y + 0.5, 6.5, 9) for x in pins]) for y in rows]), 'Black matte')
    P.add(C, 'Header spacers', U(*[kbox(51.73, y - 1.27, 89.83, y + 1.27, 8.5, 11.0) for y in rows]), 'Black matte')
    P.add(C, 'ESP32 header pins', U(*[kbox(x - 0.32, y - 0.32, x + 0.32, y + 0.32, 6.5, 13.4) for y in rows for x in pins]), 'Gold')
    P.add(C, 'Pin solder', U(*[kcyl(x, y, 12.6, 13.2, 0.85, 0.4) for y in rows for x in pins]), 'HASL tin')
    x0, x1, yc = 45.03, 96.53, 17.7
    P.add(C, 'DevKit PCB', kbox(x0, yc - 14.15, x1, yc + 14.15, 11.0, 12.6), 'Black glossy')
    # ESP-WROOM-32: 25.5 x 18, antenna at the left end
    P.add(C, 'WROOM-32 PCB', kbox(x0, yc - 9, x0 + 25.5, yc + 9, 12.6, 13.4), 'Black glossy')
    P.add(C, 'WROOM-32 shield', kbox(x0 + 6.4, yc - 8.6, x0 + 25.1, yc + 8.6, 13.4, 15.9), 'Nickel')
    ant = []
    xs = [x0 + 0.8 + 1.1 * i for i in range(5)]
    for i, x in enumerate(xs):
        ant.append(kbox(x - 0.25, yc - 7.5, x + 0.25, yc + 7.5, 13.4, 13.45))
        if i < len(xs) - 1:
            y = yc - 7.5 if i % 2 else yc + 7.5
            ant.append(kbox(x - 0.25, y - 0.25, xs[i + 1] + 0.25, y + 0.25, 13.4, 13.45))
    P.add(C, 'Antenna trace', U(*ant), 'Gold')
    usb = D(kbox(x1 - 4.7, yc - 3.75, x1 + 1.0, yc + 3.75, 12.6, 15.2), kbox(x1 + 0.2, yc - 3.1, x1 + 1.1, yc + 3.1, 13.1, 14.7))
    P.add(C, 'Micro-USB', usb, 'Nickel')
    P.add(C, 'Buttons EN/BOOT', U(*[kbox(89.5, y - 1.75, 95.5, y + 1.75, 12.6, 14.1) for y in (yc - 8.0, yc + 8.0)]), 'Nickel')
    P.add(C, 'Button caps', U(*[kbox(91.5, y - 0.8, 93.5, y + 0.8, 14.1, 14.7) for y in (yc - 8.0, yc + 8.0)]), 'Black matte')
    P.add(C, 'CP2102 + AMS1117', U(kbox(79.0, 12.0, 84.0, 17.0, 12.6, 13.5), kbox(72.0, 20.5, 75.5, 27.0, 12.6, 14.2)), 'Black matte')
    P.add(C, 'AMS1117 tab', kbox(75.5, 23.5, 76.6, 28.0, 12.6, 12.9), 'HASL tin')
    P.add(C, 'LED power', kbox(85.4, 23.4, 86.6, 25.4, 12.6, 13.2), 'LED red')
    P.add(C, 'LED GPIO2', kbox(85.4, 26.4, 86.6, 28.4, 12.6, 13.2), 'LED blue')


def relays(P):
    for ref, bb in (('K1', (19.8, 42.7, 35.2, 62.3)), ('K2', (37.8, 42.7, 53.2, 62.3)), ('K3', (55.8, 44.2, 71.2, 63.8))):
        b = kbox(bb[0], bb[1], bb[2], bb[3], 0, 15.3)
        P.add('Relays SRD-05VDC', '%s SRD-05VDC-SL-A' % ref, b, 'Relay blue')


def terminals(P):
    C = 'Terminal blocks DG128'
    cages, screws = [], []
    for ref, xs in (('J1', (6, 11)), ('J4', (18, 23)), ('J5', (30, 35)), ('J6', (60, 65)), ('J2', (79.5, 84.5, 89.5))):
        b = kbox(xs[0] - 2.5, 66.8, xs[-1] + 2.5, 76.6, 0, 10.0)
        # stepped profile: lower front lip where the wires go in
        D(b, kbox(xs[0] - 3, 75.2, xs[-1] + 3, 77, 7.2, 11))
        for x in xs:
            D(b, kbox(x - 1.7, 70.4, x + 1.7, 77, 1.8, 5.4),       # wire entry
              kcyl(x, 72.6, 6.0, 11, 1.9))                     # screw well
            cages.append(D(kbox(x - 1.6, 70.5, x + 1.6, 76.3, 1.9, 5.3), kbox(x - 1.3, 70.8, x + 1.3, 77, 2.2, 5.0)))
            screws.append(D(kcyl(x, 72.6, 6.0, 7.0, 1.75), kbox(x - 0.3, 72.6 - 2, x + 0.3, 72.6 + 2, 6.4, 7.1)))
        P.add(C, '%s DG128-5.0-%02dP' % (ref, len(xs)), b, 'Terminal green')
    P.add(C, 'Clamp cages', U(*cages), 'HASL tin')
    P.add(C, 'Clamp screws', U(*screws), 'Nickel')


def capacitors(P):
    C = 'Capacitors'
    for ref, cx in (('C1', 12.75), ('C2', 32.75)):
        cy, r, h = 13.0, 9.0, 36.0
        stripe_box = kbox(cx + 7.4, cy - 10, cx + 10, cy + 10, -1, h + 1)
        sleeve = D(kcyl(cx, cy, 0, h, r), kcyl(cx, cy, h - 0.6, h + 1, r - 1.0))
        stripe = I(tbm.copy(sleeve), stripe_box)
        D(sleeve, kbox(cx + 7.4, cy - 10, cx + 10, cy + 10, -1, h + 1))
        top = D(kcyl(cx, cy, h - 0.6, h - 0.3, r - 1.0), kbox(cx - 6, cy - 0.2, cx + 6, cy + 0.2, h - 0.45, h),
                kbox(cx - 0.2, cy - 6, cx + 0.2, cy + 6, h - 0.45, h))
        P.add(C, '%s 4700uF 25V sleeve' % ref, sleeve, 'Black glossy')
        P.add(C, '%s minus stripe' % ref, stripe, 'Cap stripe grey')
        P.add(C, '%s top' % ref, top, 'Aluminum')
    P.add(C, 'C3 10uF NP sleeve', D(kcyl(61.8, 39.8, 0, 11, 2.5), kcyl(61.8, 39.8, 10.7, 12, 2.1)), 'Black glossy')
    P.add(C, 'C3 top', kcyl(61.8, 39.8, 10.7, 10.85, 2.1), 'Aluminum')
    for ref, x, y in (('C5', 77.3, 40.5), ('C6', 72.0, 26.3)):
        P.add(C, '%s 100nF 0805' % ref, kbox(x - 0.62, y - 0.6, x + 0.62, y + 0.6, 0, 0.85), 'Ceramic tan')
        P.add(C, '%s terminals' % ref, U(kbox(x - 0.64, y - 1.0, x + 0.64, y - 0.6, 0, 0.87), kbox(x - 0.64, y + 0.6, x + 0.64, y + 1.0, 0, 0.87)), 'HASL tin')


def vertical_axial(body_xy, lead_xy, d, L, lead_r, lift=1.0, bend=1.0):
    """Axial part standing on body_xy, upper lead bent over to lead_xy. Returns (body, lead, top height)."""
    (bx, by), (lx, ly) = body_xy, lead_xy
    top = lift + L
    body = kcyl(bx, by, lift, top, d / 2)
    hb = top + bend
    lead = U(wire([(bx, by, top - 0.1), (bx, by, hb), (lx, ly, hb), (lx, ly, 0)], lead_r), kcyl(bx, by, 0, lift + 0.1, lead_r))
    return body, lead, top


def diodes(P):
    C = 'Diodes'
    leads, glass, black, bands_dark, bands_grey = [], [], [], [], []
    # (ref, pad1 = bent cathode lead, pad2 = body, diameter, length, lead r, kind)
    for ref, p1, p2, dd, L, lr, kind in (
            ('D1', (18.2, 29.5), (14.39, 29.5), 5.3, 9.5, 0.65, 'power'),
            ('D2', (27.3, 29.5), (23.49, 29.5), 5.3, 9.5, 0.65, 'power'),
            ('D3', (3.5, 43.2), (7.31, 43.2), 3.6, 7.6, 0.45, 'power'),
            ('D4', (79.6, 61.2), (82.14, 61.2), 1.9, 4.0, 0.26, 'glass'),
            ('D5', (87.9, 61.2), (85.36, 61.2), 1.9, 4.0, 0.26, 'glass'),
            ('D6', (79.5, 18.2), (82.04, 18.2), 1.9, 4.0, 0.26, 'glass'),
            ('D7', (79.5, 12.6), (82.04, 12.6), 1.9, 4.0, 0.26, 'glass'),
            ('D8', (44.0, 69.3), (46.54, 69.3), 1.9, 4.0, 0.26, 'glass')):
        body, lead, top = vertical_axial(p2, p1, dd, L, lr)
        leads.append(lead)
        band = kcyl(p2[0], p2[1], top - L * 0.22, top - L * 0.08, dd / 2 + 0.03)   # cathode band at the top
        if kind == 'power':
            P.add(C, '%s %s' % (ref, '1N5821' if dd > 5 else 'P6KE36A'), body, 'Black matte')
            bands_grey.append(band)
        else:
            P.add(C, '%s %s' % (ref, 'BZX55C5V1' if ref in ('D4', 'D5') else '1N4148'), body, 'Glass orange')
            bands_dark.append(band)
    P.add(C, 'Diode leads', U(*leads), 'HASL tin')
    P.add(C, 'Cathode bands (glass)', U(*bands_dark), 'Band black')
    P.add(C, 'Cathode bands (power)', U(*bands_grey), 'Cap stripe grey')


def resistors(P):
    C = 'Resistors'
    code = {'1k': ('brown', 'black', 'black', 'brown'), '10k': ('brown', 'black', 'black', 'red'),
            '100k': ('brown', 'black', 'black', 'orange'), '4.7k': ('yellow', 'violet', 'black', 'brown'),
            '22k': ('red', 'red', 'black', 'red')}
    bands, leads = {}, []
    for ref, x, y, val in (('Rb1', 67.5, 18.2, '1k'), ('Rb2', 67.5, 12.6, '1k'), ('Rg3', 49.5, 65.8, '1k'), ('R6', 80.0, 53.3, '1k'),
                           ('Rp1', 73.5, 18.2, '10k'), ('Rp2', 73.5, 12.6, '10k'), ('Rp3', 49.5, 69.3, '10k'),
                           ('Rb3', 66.5, 38.6, '10k'), ('Rv1', 72.5, 42.0, '10k'), ('Rv2', 72.5, 38.6, '10k'),
                           ('R4', 66.5, 42.0, '100k'), ('R5', 80.0, 49.6, '4.7k'), ('R1', 79.6, 56.5, '22k')):
        body, lead, top = vertical_axial((x, y), (x + 2.54, y), 2.5, 6.3, 0.3)
        P.add(C, '%s %s' % (ref, val), body, 'Resistor blue')
        leads.append(lead)
        bot = top - 6.3
        for colour, z in zip(code[val] + ('brown',), (5.3, 4.5, 3.7, 2.9, 1.0)):   # 5-band 1 %, tolerance band at the bottom
            bands.setdefault(colour, []).append(kcyl(x, y, bot + z - 0.25, bot + z + 0.25, 1.29))
    for colour, bl in bands.items():
        P.add(C, 'Bands %s' % colour, U(*bl), 'Band %s' % colour)
    P.add(C, 'Resistor leads', U(*leads), 'HASL tin')


def semis(P):
    C = 'Transistors and LM393'
    legs = []
    for ref, x, y in (('Q1', 62.0, 18.2), ('Q2', 62.0, 12.6), ('Q3', 44.0, 65.8)):
        b = I(kcyl(x + 1.27, y - 0.2, 2.5, 7.1, 2.3), kbox(x - 2, y - 3, x + 4.6, y + 1.75, 2, 8))
        P.add(C, '%s BC337' % ref, b, 'Black matte')
        legs += [kbox(x + dx - 0.22, y - 0.2, x + dx + 0.22, y + 0.2, 0, 2.6) for dx in (0, 1.27, 2.54)]
    cx, cy = 83.81, 42.31
    dip = D(kbox(cx - 3.2, cy - 4.9, cx + 3.2, cy + 4.9, 0.6, 3.9), kcyl(cx, cy - 4.9, 3.6, 4.0, 0.8), kcyl(cx - 1.9, cy - 3.7, 3.82, 4.0, 0.4))
    P.add(C, 'U3 LM393 DIP-8', dip, 'Black matte')
    for i in range(4):
        y = 38.5 + 2.54 * i
        for px, edge in ((80.0, cx - 3.2), (87.62, cx + 3.2)):
            legs.append(kbox(px - 0.13, y - 0.25, px + 0.13, y + 0.25, 0, 2.2))
            legs.append(kbox(min(px - 0.13, edge), y - 0.75, max(px + 0.13, edge), y + 0.75, 1.9, 2.2))
    P.add(C, 'Q1-Q3/U3 legs', U(*legs), 'HASL tin')


def misc(P):
    C = 'Headers, DC-DC, fuse'
    P.add(C, 'J3 header 1x4 (spare relay module)', kbox(88.53, 49.23, 91.07, 59.39, 0, 2.5), 'Black matte')
    pins = [(89.8, 50.5 + 2.54 * i) for i in range(4)]
    P.add(C, 'J3 header pins', U(*[kbox(x - 0.32, y - 0.32, x + 0.32, y + 0.32, -4.6, 8.4) for x, y in pins]), 'Gold')
    # Favotek RM20S-050: 11.5 x 9.0 x 17.5 mm SIP-3, body on the D2 side of the pins (as fitted on a real board;
    # pad 1 at the top is +VIN)
    P.add(C, 'RM1 RM20S-050 DC-DC', kbox(30.15, 23.29, 39.15, 34.79, 0, 17.5), 'Black matte')
    P.add(C, 'F1 2A slow fuse', kcyl(6.5, 50.66, 0.3, 7.5, 4.25), 'Black glossy')


# SC1 supercapacitor: JEC SMD05R5S0001DARZ, 1 F 5.5 V, oval 16 x 8 mm, 14 mm tall, both leads down, pitch 11.8, d 0.6.
# Board v5.1 has its own footprint for it: pad 1 (+) at (41.9, 37.3), pad 2 (-) 11.8 mm to the right, in the band
# between the ESP32 module edge (y 31.85) and the K1/K2 relays (y 42.4).
SC = dict(cx=47.8, cy=37.3, w=16.0, d=8.0, h=14.0, pitch=11.8, seat=0.5, lead=0.6)


def stadium(cx, cy, w, d, h0, h1):
    r = d / 2
    return U(kbox(cx - w / 2 + r, cy - r, cx + w / 2 - r, cy + r, h0, h1), kcyl(cx - w / 2 + r, cy, h0, h1, r), kcyl(cx + w / 2 - r, cy, h0, h1, r))


def supercap(P):
    C = 'SC1 supercap'
    cx, cy, z0 = SC['cx'], SC['cy'], SC['seat']
    P.add(C, 'SC1 JEC 1F 5.5V', stadium(cx, cy, SC['w'], SC['d'], z0, z0 + SC['h']), 'Black glossy')
    r = SC['lead'] / 2
    P.add(C, 'SC1 leads', U(*[kcyl(x, cy, -2.6, z0 + 0.5, r) for x in (cx - SC['pitch'] / 2, cx + SC['pitch'] / 2)]), 'HASL tin')


def fasteners(P, holes_pcb, holes_lid, z_pcb_top, z_insert_pcb, z_lid_seat, z_lid_insert_top):
    C = 'Fasteners'
    def insert(x, y, z0, z1):
        b = D(acyl(x, y, z0, z1, 2.1), acyl(x, y, z0 - 1, z1 + 1, 1.5))
        for zg in (z0 + (z1 - z0) * 0.3, z0 + (z1 - z0) * 0.7):
            D(b, D(acyl(x, y, zg - 0.3, zg + 0.3, 2.3), acyl(x, y, zg - 1, zg + 1, 1.9)))
        return b

    def screw(x, y, z_seat, length):
        rr, hh = 2.85, 1.65                       # ISO 7380 M3: head d 5.7, k 1.65, hex socket 2
        R = (rr * rr + hh * hh) / (2 * hh)
        head = I(tbm.createSphere(pt(x, y, z_seat + hh - R), R * CM), acyl(x, y, z_seat, z_seat + hh, rr))
        D(head, hex_prism(x, y, z_seat + hh - 1.1, z_seat + hh + 1, 2.0))
        return U(head, acyl(x, y, z_seat - length, z_seat + 0.1, 1.45))

    P.add(C, 'Inserts M3 (PCB)', U(*[insert(x, y, z_insert_pcb - 5, z_insert_pcb) for x, y in holes_pcb]), 'Brass')
    P.add(C, 'Inserts M3 (lid)', U(*[insert(x, y, z_lid_insert_top - 5.7, z_lid_insert_top) for x, y in holes_lid]), 'Brass')
    P.add(C, 'Screws M3x8 ISO 7380 (PCB)', U(*[screw(x, y, z_pcb_top, 8) for x, y in holes_pcb]), 'Stainless steel')
    P.add(C, 'Screws M3x8 ISO 7380 (lid)', U(*[screw(x, y, z_lid_seat, 8) for x, y in holes_lid]), 'Stainless steel')


# ------------------------------------------------------------------ enclosure colours
def colour_enclosure(design, looks):
    root = design.rootComponent
    up = design.userParameters
    v = lambda n: up.itemByName(n).value          # cm
    for name in ('Base', 'Ear (print 4)', 'Lid', 'Cover'):
        b = root.bRepBodies.itemByName(name)
        if b:
            b.appearance = looks['ABS white']
    cov = root.bRepBodies.itemByName('Cover')
    tol = 1e-4
    g = 0.7 * v('cover_gap')                      # the cover side walls lean into the glue gap
    cx0, cx1 = v('cover_x0') - g, v('cover_x0') + v('cover_w') + g
    cy0, cy1 = v('cover_y0') - g, v('cover_y1') + g
    top = cov.boundingBox.maxPoint.z
    zc = top - v('pocket_d') - tol
    inlay = v('inlay')
    n_red = n_logo = 0
    for f in cov.faces:
        bb = f.boundingBox
        in_cover = bb.minPoint.x >= cx0 and bb.maxPoint.x <= cx1 and bb.minPoint.y >= cy0 and bb.maxPoint.y <= cy1
        at_top = bb.minPoint.z > top - tol and bb.maxPoint.z > top - tol
        recess = bb.minPoint.z > top - inlay - tol and not at_top
        if in_cover and bb.minPoint.z >= zc:
            if recess:
                continue                               # emblem stays white on the red insert
            f.appearance = looks['ABS red Pramac']; n_red += 1
        elif recess:
            f.appearance = looks['ABS red Pramac']; n_logo += 1
    return n_red, n_logo


# ------------------------------------------------------------------ main
def make_looks(design):
    lib = app.materialLibraries.itemByName('Fusion Appearance Library')
    out = {}
    for name, (base, rgb) in LOOKS.items():
        a = design.appearances.itemByName(name)
        if not a:
            a = design.appearances.addByCopy(lib.appearances.itemByName(base), name)
            if rgb:
                p = a.appearanceProperties.itemById('opaque_albedo')
                if p:
                    adsk.core.ColorProperty.cast(p).value = adsk.core.Color.create(rgb[0], rgb[1], rgb[2], 255)
        out[name] = a
    return out


def build(root, P, looks):
    """One base feature per group in the root component (a Part Design document cannot hold sub-components)."""
    n = 0
    for cname, items in P.groups.items():
        bf = root.features.baseFeatures.add()
        bf.startEdit()
        for name, body, look in items:
            b = root.bRepBodies.add(body, bf)
            b.name = name
            b.appearance = looks[look]
            n += 1
        bf.finishEdit()
        bf.name = GROUP_PREFIX + cname
    return n


def run(_context):
    global X0, Y0, ZT
    design = adsk.fusion.Design.cast(app.activeProduct)
    root = design.rootComponent
    up = design.userParameters
    mm = lambda n: up.itemByName(n).value * 10
    X0 = mm('pcb_x0')
    Y0 = mm('pcb_ytop')
    ZT = mm('floor_t') + mm('standoff') + mm('pcb_t')

    tl = design.timeline                                 # re-run: drop what an earlier run added
    for i in reversed(range(tl.count)):
        e = tl.item(i).entity
        if e and e.objectType == adsk.fusion.BaseFeature.classType() and e.name.startswith(GROUP_PREFIX):
            e.deleteMe()

    looks = make_looks(design)
    P = Parts()
    board(P); esp32(P); relays(P); terminals(P); capacitors(P); diodes(P); resistors(P); semis(P); misc(P); supercap(P)

    # fastener positions from the enclosure sketches
    def centers(sk_name):
        s = root.sketches.itemByName(sk_name)
        return [(c.centerSketchPoint.worldGeometry.x * 10, c.centerSketchPoint.worldGeometry.y * 10) for c in s.sketchCurves.sketchCircles]
    lid_seat = root.sketches.itemByName('Lid screw head recess').origin.z * 10 - mm('csk_h')
    base_top = mm('base_h')
    fasteners(P, centers('PCB insert holes'), centers('Lid screw holes'), ZT, ZT - mm('pcb_t'), lid_seat, base_top)

    n = build(root, P, looks)
    n_red, n_logo = colour_enclosure(design, looks)
    print('bodies:', n, 'red insert faces:', n_red, 'logo faces:', n_logo)
