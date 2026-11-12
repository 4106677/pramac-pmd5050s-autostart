#!/usr/bin/env python3
"""Pramac autostart v6: board generator (KiCad pcbnew API). Run with KiCad's python:

  .../KiCad.app/Contents/Frameworks/Python.framework/Versions/Current/bin/python3 gen_pcb.py [place|route]

place: footprints from the schematic netlist at the coordinates below, outline, holes, mains keep-out, hand-routed
       power and mains tracks; writes pramac_v6.kicad_pcb and pramac_v6.dsn for Freerouting.
route: imports pramac_v6.ses (Freerouting result), adds the GND pours and silk, saves the final board.
export: DRC report, gerbers + drill zip, CPL for JLCPCB, renders, schematic PDF.
"""
import os, subprocess, sys
import pcbnew
from pcbnew import VECTOR2I, FromMM, ToMM

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import kisch

KICAD = "/Applications/KiCad/KiCad.app/Contents"
LIB = KICAD + "/SharedSupport/footprints/"
CLI = KICAD + "/MacOS/kicad-cli"
PCB = os.path.join(HERE, "pramac_v6.kicad_pcb")
W, H = 125.0, 100.0
MAINS = {"AC_L", "AC_LF", "AC_N", "AC_D1", "AC_D2", "AC_D3", "CT_COM", "CT_NO"}
POWER = {"VBAT": 0.0, "VBF": 1.0, "VIN12": 1.0, "V5": 0.8, "3V3": 0.6, "V24": 0.8, "CHG_VCC": 1.0, "CHG_SW": 1.2,
         "CHG_CSP": 1.0, "BUCK_SW": 0.8, "BUCK5_SW": 0.8, "GND": 0.6, "ACC_OUT": 0.0, "START_OUT": 0.0, "AUX_OUT": 0.0}

# ---------------------------------------------------------------- placement: ref -> (x, y, rotation, side)
# coordinates are the footprint origin (KiCad mm, y down); side "B" = bottom layer
PLACE = {
    # corner holes
    "H1": (4, 4, 0), "H2": (W - 4, 4, 0), "H3": (4, H - 4, 0), "H4": (W - 4, H - 4, 0),
    # ---- mains zone (left)
    "PS1": (12, 9, 0),
    "F2": (6, 42, 0), "RV1": (6, 51, 0),
    "K3": (42, 50, 180),
    # mains detector under the AC-DC module: chain R40-R42, opto U6 bridges to the LV side (R43, C41)
    "R40": (20.3, 35.7, 0), "R41": (25.0, 35.7, 0), "R42": (29.7, 35.7, 0), "U6": (39, 37, 0),
    "R43": (47.3, 35.0, 180), "C41": (47.3, 38.3, 180),
    "J1": (12, 84, 0), "J2": (27, 84, 0),
    # ---- connectors (bottom edge, LV)
    "J8": (40.5, 84, 0), "J3": (54, 84, 0), "J4": (69, 84, 0), "J5": (85, 84, 0),
    # ---- relays K4/K1/K2 in a row (COM on the VBAT bus) and their drivers (band between the relays and the connectors)
    "K4": (30, 67.5, 0), "K1": (54, 67.5, 0), "K2": (77, 67.5, 0),
    "Q4": (38.6, 78.3, 0), "R16": (42.6, 77.3, 0), "R17": (42.6, 79.3, 0), "D16": (47.6, 78.3, 0), "R23": (52.1, 77.3, 0), "D17": (52.1, 79.3, 0),
    "Q1": (56, 78.3, 0), "R10": (60, 77.3, 0), "R11": (60, 79.3, 0), "D10": (65, 78.3, 0), "R20": (69.5, 77.3, 0), "D13": (69.5, 79.3, 0),
    "Q2": (79, 78.3, 0), "R12": (83, 77.3, 0), "R13": (83, 79.3, 0), "D11": (88, 78.3, 0), "R21": (92.5, 77.3, 0), "D14": (92.5, 79.3, 0),
    "Q3": (49, 50, 0), "R14": (49, 54, 0), "R15": (49, 57, 0), "D12": (48.5, 44, 90), "R22": (51.5, 41, 90), "D15": (51.5, 44.5, 90),
    # ---- input protection, battery sense
    "F1": (55, 37, 0), "D1": (62.5, 37, 0), "D2": (57, 43.5, 180), "C1": (58.5, 52, 0), "C2": (66.5, 48.5, 90),
    "R1": (66.5, 53, 90), "R2": (66.5, 57, 90), "C3": (69, 57, 90),
    # ---- bucks (top middle)
    "U2": (75, 9, 0), "R3": (70, 9, 90), "C4": (75, 4.5, 0), "L1": (82, 9, 0), "C5": (88, 8, 90), "C6": (91, 8, 90),
    "U3": (75, 21, 0), "R8": (70, 21, 90), "C7": (75, 16.5, 0), "L2": (82, 21, 0), "C8": (88, 20, 90), "C12": (91, 20, 90),
    "C13": (73, 28, 0), "D4": (82, 28, 0),
    # ---- charger (middle)
    "Q20": (70, 38, 0), "R60": (66, 33.5, 0), "R61": (66, 43, 90), "Q22": (69, 44, 0), "R62": (72.5, 44, 90),
    "C60": (79, 38, 0), "C61": (76, 44, 90), "C62": (78.5, 44, 90),
    "U20": (87.5, 38, 0), "C63": (87.5, 33.5, 0), "R63": (82, 44, 90), "R64": (84.5, 44, 90), "R65": (87, 44, 90), "C64": (89.5, 44, 90),
    "Q21": (95, 36, 0), "D22": (95, 42, 180), "L20": (96, 52.5, 0), "R66": (106, 42, 90),
    "C65": (107, 55, 90), "C66": (86, 48, 0), "C40": (65, 24, 90),
    "R67": (70, 49, 90), "R68": (72.5, 49, 90), "D23": (75, 49, 90), "R69": (77.5, 49, 90), "R70": (80, 49, 90), "D24": (82.5, 49, 90),
    # ---- ESP32 (top right), USB-C on the right edge
    "U1": (112, 16, 0), "C9": (101, 9, 90), "C10": (101, 12.5, 90), "R4": (101, 17, 90), "C11": (101, 20.5, 90),
    "SW1": (107, 30, 0), "SW2": (116.5, 30, 0), "R5": (101, 25, 90), "TP1": (95, 26, 0), "TP2": (95, 29, 0), "TP3": (95, 32, 0),
    "J6": (120, 44, 90), "U4": (111.5, 41, 90), "R6": (111.5, 46, 90), "R7": (113.5, 46, 90),
    # ---- TAHO / REMOTE (right, above J5)
    "U5": (108, 67, 0), "R30": (101, 75, 0), "D20": (100, 70, 90), "D21": (100, 64.5, 90), "C30": (106, 73, 0),
    "R31": (103, 62, 90), "R32": (106, 62, 90), "R33": (109, 62, 90), "R34": (113, 62, 90), "R35": (113, 67, 90), "C31": (113, 71, 90),
    "R36": (107, 77, 0), "C32": (111, 77, 90), "R37": (114, 77, 90),
    # ---- DIP, LEDs, spare
    "SW3": (108, 86, 0), "R50": (117, 79, 90), "D30": (117, 83, 90), "R51": (119.5, 79, 90), "D31": (119.5, 83, 90),
    "J7": (122, 58, 0),
}


def load_netlist():
    net = os.path.join(HERE, "pramac_v6.net")
    subprocess.run([CLI, "sch", "export", "netlist", "--format", "kicadsexpr", "-o", net,
                    os.path.join(HERE, "pramac_v6.kicad_sch")], check=True, capture_output=True)
    root = kisch.parse(open(net, encoding="utf-8").read())
    comps = {}
    for c in kisch.find(kisch.find(root, "components")[0], "comp"):
        ref = str(kisch.find(c, "ref")[0][1])
        fp = str(kisch.find(c, "footprint")[0][1]) if kisch.find(c, "footprint") else ""
        val = str(kisch.find(c, "value")[0][1])
        fields = {}
        for f in kisch.find(c, "fields") and kisch.find(kisch.find(c, "fields")[0], "field") or []:
            fields[str(kisch.find(f, "name")[0][1])] = str(f[-1]) if isinstance(f[-1], str) else ""
        comps[ref] = (fp, val, fields)
    pins = {}
    for n in kisch.find(kisch.find(root, "nets")[0], "net"):
        name = str(kisch.find(n, "name")[0][1]).lstrip("/")
        for node in kisch.find(n, "node"):
            pins[(str(kisch.find(node, "ref")[0][1]), str(kisch.find(node, "pin")[0][1]))] = name
    os.remove(net)
    return comps, pins


def build():
    comps, pins = load_netlist()
    board = pcbnew.BOARD()
    ds = board.GetDesignSettings()
    nc = ds.m_NetSettings.GetDefaultNetclass()
    nc.SetClearance(FromMM(0.15)); nc.SetTrackWidth(FromMM(0.25))
    nc.SetViaDiameter(FromMM(0.6)); nc.SetViaDrill(FromMM(0.3))
    ds.m_MinThroughDrill = FromMM(0.3)
    ds.m_TrackMinWidth = FromMM(0.15)
    ds.m_MinResolvedSpokes = 1
    ds.m_MinClearance = FromMM(0.15)
    nets = {}

    def net(name):
        if name not in nets:
            ni = pcbnew.NETINFO_ITEM(board, name); board.Add(ni); nets[name] = ni
        return nets[name]

    fps = {}
    missing = []
    for ref, (fpid, val, fields) in sorted(comps.items()):
        if ref not in PLACE:
            missing.append(ref); continue
        lib, name = fpid.split(":")
        fp = pcbnew.FootprintLoad(LIB + lib + ".pretty", name)
        fp.SetReference(ref); fp.SetValue(val)
        x, y, rot = PLACE[ref][:3]
        fp.SetPosition(VECTOR2I(FromMM(x), FromMM(y)))
        if rot:
            fp.SetOrientationDegrees(rot)
        for k, v in fields.items():
            if k == "LCSC":
                fp.SetField("LCSC", v) if hasattr(fp, "SetField") else None
        board.Add(fp); fps[ref] = fp
        for p in fp.Pads():
            n = pins.get((ref, p.GetNumber()))
            if n and not n.startswith("unconnected"):
                p.SetNet(net(n))
    if missing:
        print("NOT PLACED:", " ".join(missing))
    # outline
    for (a, b, c, d) in [(0, 0, W, 0), (W, 0, W, H), (W, H, 0, H), (0, H, 0, 0)]:
        s = pcbnew.PCB_SHAPE(board); s.SetShape(pcbnew.SHAPE_T_SEGMENT); s.SetLayer(pcbnew.Edge_Cuts)
        s.SetWidth(FromMM(0.1)); s.SetStart(VECTOR2I(FromMM(a), FromMM(b))); s.SetEnd(VECTOR2I(FromMM(c), FromMM(d)))
        board.Add(s)
    return board, fps, nets


def check(board, fps):
    """Courtyard overlaps and parts outside the board."""
    boxes = {}
    for ref, fp in fps.items():
        try:
            bb = fp.GetCourtyard(pcbnew.F_CrtYd).BBox()
            if bb.GetWidth() == 0:
                bb = fp.GetBoundingBox(False)
        except Exception:
            bb = fp.GetBoundingBox(False)
        boxes[ref] = (ToMM(bb.GetLeft()), ToMM(bb.GetTop()), ToMM(bb.GetRight()), ToMM(bb.GetBottom()))
    bad = 0
    refs = sorted(boxes)
    for i, a in enumerate(refs):
        x0, y0, x1, y1 = boxes[a]
        if x0 < -0.01 or y0 < -0.01 or x1 > W + 0.01 or y1 > H + 0.01:
            if a[0] != "J":
                print("  outside:", a, [round(v, 1) for v in boxes[a]]); bad += 1
        for b in refs[i + 1:]:
            u0, v0, u1, v1 = boxes[b]
            ox, oy = min(x1, u1) - max(x0, u0), min(y1, v1) - max(y0, v0)
            if ox > 0.05 and oy > 0.05:
                print("  overlap: %s %s (%.1f x %.1f)" % (a, b, ox, oy)); bad += 1
    return bad


# ---------------------------------------------------------------- copper helpers
def P(fps, ref, num):
    for p in fps[ref].Pads():
        if p.GetNumber() == str(num):
            q = p.GetPosition(); return (ToMM(q.x), ToMM(q.y))
    raise KeyError((ref, num))


def track(board, nets, n, layer, pts, w):
    for a, b in zip(pts, pts[1:]):
        t = pcbnew.PCB_TRACK(board)
        t.SetStart(VECTOR2I(FromMM(a[0]), FromMM(a[1]))); t.SetEnd(VECTOR2I(FromMM(b[0]), FromMM(b[1])))
        t.SetWidth(FromMM(w)); t.SetLayer(layer); t.SetNet(nets[n]); board.Add(t)


def via(board, nets, n, p, d=0.8, drill=0.4):
    v = pcbnew.PCB_VIA(board)
    v.SetPosition(VECTOR2I(FromMM(p[0]), FromMM(p[1])))
    v.SetWidth(FromMM(d)); v.SetDrill(FromMM(drill)); v.SetViaType(pcbnew.VIATYPE_THROUGH)
    v.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu); v.SetNet(nets[n]); board.Add(v)


def zone(board, nets, layer, poly, netname=None, rule=None, clearance=0.3):
    z = pcbnew.ZONE(board); z.SetLayer(layer)
    if rule:
        z.SetIsRuleArea(True)
        z.SetDoNotAllowZoneFills(True); z.SetDoNotAllowTracks(rule == "keepout"); z.SetDoNotAllowVias(rule == "keepout")
        z.SetDoNotAllowPads(False); z.SetDoNotAllowFootprints(False)
    else:
        z.SetNet(nets[netname]); z.SetLocalClearance(FromMM(clearance)); z.SetMinThickness(FromMM(0.25))
        z.SetPadConnection(pcbnew.ZONE_CONNECTION_THERMAL)
        z.SetIslandRemovalMode(pcbnew.ISLAND_REMOVAL_MODE_ALWAYS)
        z.SetThermalReliefGap(FromMM(0.4)); z.SetThermalReliefSpokeWidth(FromMM(0.5))
    o = z.Outline(); o.NewOutline()
    for (x, y) in poly:
        o.Append(FromMM(x), FromMM(y))
    board.Add(z)
    return z


F, B = pcbnew.F_Cu, pcbnew.B_Cu
# mains region (no LV copper, no GND pour); LV pour region is everything else
MAINS_POLY = [(0, 0), (34, 0), (34, 33.4), (39, 33.4), (39, 41), (46.5, 41), (46.5, 60), (26.5, 60), (26.5, 76.3),
              (36.5, 76.3), (36.5, H), (0, H)]
LV_POLY = [(34.5, 0.5), (W - 0.5, 0.5), (W - 0.5, H - 0.5), (37, H - 0.5), (37, 76.8), (27, 76.8), (27, 60.5), (47, 60.5),
           (47, 40.5), (39.5, 40.5), (39.5, 33.9), (34.5, 33.9)]


def in_mains(x, y, m=1.0):
    """Point inside the mains region or closer than m to its border."""
    import math
    poly, inside, n = MAINS_POLY, False, len(MAINS_POLY)
    for i in range(n):
        (x1, y1), (x2, y2) = poly[i], poly[(i + 1) % n]
        if (y1 > y) != (y2 > y) and x < x1 + (y - y1) * (x2 - x1) / (y2 - y1):
            inside = not inside
        L2 = (x2 - x1) ** 2 + (y2 - y1) ** 2
        u = max(0.0, min(1.0, ((x - x1) * (x2 - x1) + (y - y1) * (y2 - y1)) / L2)) if L2 else 0.0
        if math.hypot(x - x1 - u * (x2 - x1), y - y1 - u * (y2 - y1)) < m:
            return True
    return inside


def hand_route(board, fps, nets):
    p = lambda r, n: P(fps, r, n)
    MW = 1.2          # mains track width
    # ---- 230 V input: J1 -> F2 -> PS1 / varistor / detector; neutral to PS1, varistor, opto
    j1l, j1n = p("J1", 1), p("J1", 2)
    f2a, f2b = p("F2", 1), p("F2", 2)
    track(board, nets, "AC_L", F, [j1l, (j1l[0], 80), (2.5, 70.5), (2.5, 44), (4.5, f2a[1]), f2a], MW)
    ps1l, ps1n = p("PS1", 1), p("PS1", 2)
    track(board, nets, "AC_LF", F, [f2b, (17, 36), (17, 13), (ps1l[0] + 1, ps1l[1] + 1), ps1l], MW)
    rv1a, rv1b = p("RV1", 1), p("RV1", 2)
    track(board, nets, "AC_LF", F, [f2b, (f2b[0], 46), (rv1a[0] + 1.5, rv1a[1] - 1.5), rv1a], MW)
    # detector chain under the AC-DC module: AC_LF -> R40 -> R41 -> R42 -> U6 pin 1; AC_N to U6 pin 2 (via from the bottom)
    track(board, nets, "AC_LF", F, [(17, 36), p("R40", 1)], 0.6)
    for a, b, n in (("R40", "R41", "AC_D1"), ("R41", "R42", "AC_D2"), ("R42", "U6", "AC_D3")):
        track(board, nets, n, F, [p(a, 2), p(b, 1)], 0.6)
    u62 = p("U6", 2)
    track(board, nets, "AC_N", B, [j1n, (j1n[0], 77), (rv1b[0], 71), rv1b], MW)
    track(board, nets, "AC_N", B, [rv1b, (15.5, rv1b[1] - 4.5), (15.5, 32), (ps1n[0] + 1.7, ps1n[1] + 0.4), ps1n], MW)
    track(board, nets, "AC_N", B, [(15.5, 39.3), (19.5, 39.3)], 0.8)
    via(board, nets, "AC_N", (19.5, 39.3), 0.8, 0.4)
    track(board, nets, "AC_N", F, [(19.5, 39.3), (33.2, 39.3), u62], 0.6)
    # ---- contactor contacts K3 -> J2: COM on the bottom (under K3, down x 23.2), NO on the top (down x 22)
    k3com, k3no = p("K3", 1), p("K3", 3)
    j2no, j2com = p("J2", 1), p("J2", 2)
    CW = 1.0
    track(board, nets, "CT_COM", B, [k3com, (23.2, k3com[1]), (23.2, 78.5), (j2com[0], 78.5), j2com], CW)
    track(board, nets, "CT_NO", F, [k3no, (22.0, k3no[1]), (22.0, 81.5), (24.5, j2no[1]), j2no], CW)
    # ---- K3 coil: short LV stubs out of the mains region (Freerouting continues from their ends)
    track(board, nets, "V5", F, [p("K3", 2), (47.0, p("K3", 2)[1])], 0.6)
    track(board, nets, "K3_COIL", F, [p("K3", 5), (47.0, p("K3", 5)[1])], 0.6)
    # ---- battery bus to the relay COM pins K4/K1/K2 (10 A class, bottom), branch to the PTC fuse F1
    j3b, k4c, k1c, k2c = p("J3", 1), p("K4", 1), p("K1", 1), p("K2", 1)
    FX = 50.5          # where the feed from J3 joins the bus (left of the K1 coil pin)
    track(board, nets, "VBAT", B, [j3b, (j3b[0], 80.5), (FX, 77), (FX, k1c[1])], 4.0)
    track(board, nets, "VBAT", B, [k4c, (FX, k1c[1]), k1c, k2c], 4.0)
    f1a = p("F1", 1)
    track(board, nets, "VBAT", B, [(FX, k1c[1]), (FX, 36), (f1a[0], 34.6)], 1.5)
    for vx in (f1a[0] - 0.7, f1a[0] + 0.7):
        via(board, nets, "VBAT", (vx, 34.6), 1.0, 0.5)
    track(board, nets, "VBAT", F, [(f1a[0] - 0.7, 34.6), (f1a[0] + 0.7, 34.6)], 1.2)
    track(board, nets, "VBAT", F, [(f1a[0], 34.6), f1a], 1.2)
    # ---- relay outputs (bottom): K1/K2 to J4, K4 to J8
    k1no, k2no, j4a, j4b = p("K1", 3), p("K2", 3), p("J4", 1), p("J4", 2)
    track(board, nets, "ACC_OUT", B, [k1no, (j4a[0], k1no[1] + 1.5), j4a], 4.0)
    track(board, nets, "START_OUT", B, [k2no, (k2no[0], 77), (j4b[0], 77), j4b], 3.0)
    k4no, j8a = p("K4", 3), p("J8", 1)
    track(board, nets, "AUX_OUT", B, [k4no, (k4no[0], 77), (j8a[0], 77 + k4no[0] - j8a[0]), j8a], 3.0)


def gnd_vias(board, fps, nets):
    """A via into the bottom GND pour next to every SMD GND pad, so GND is never left to the autorouter."""
    import math
    obst = []
    for fp in fps.values():
        for p in fp.Pads():
            q = p.GetPosition(); bb = p.GetBoundingBox()
            obst.append((ToMM(q.x), ToMM(q.y), max(ToMM(bb.GetWidth()), ToMM(bb.GetHeight())) / 2, p.GetNetname()))
    for t in board.GetTracks():
        if t.GetClass() == "PCB_TRACK":
            a_, b_ = t.GetStart(), t.GetEnd()
            for k in range(11):
                obst.append((ToMM(a_.x) + (ToMM(b_.x) - ToMM(a_.x)) * k / 10, ToMM(a_.y) + (ToMM(b_.y) - ToMM(a_.y)) * k / 10,
                             ToMM(t.GetWidth()) / 2, t.GetNetname()))
    placed = []
    def free(x, y):
        if not (1.5 < x < W - 1.5 and 1.5 < y < H - 1.5):
            return False
        if in_mains(x, y, 1.0):
            return False
        for (ox, oy, r, n) in obst:
            if n != "GND" and math.hypot(ox - x, oy - y) < r + 0.3 + 0.2:
                return False
        return all(math.hypot(px - x, py - y) > 0.9 for px, py in placed)
    n_ok = n_bad = 0
    for ref, fp in fps.items():
        if fp.GetAttributes() & pcbnew.FP_THROUGH_HOLE:
            continue
        c = fp.GetPosition(); cx, cy = ToMM(c.x), ToMM(c.y)
        done_pads = set()
        for p in fp.Pads():
            if p.GetNetname() != "GND" or not p.IsOnLayer(F):
                continue
            q = p.GetPosition(); x0, y0 = ToMM(q.x), ToMM(q.y)
            key = (round(x0, 1), round(y0, 1))
            if key in done_pads:
                continue
            done_pads.add(key)
            bb = p.GetBoundingBox(); hw, hh = ToMM(bb.GetWidth()) / 2, ToMM(bb.GetHeight()) / 2
            if ref == "U1" and p.GetNumber() == "61":     # exposed pad: via in the pad
                via(board, nets, "GND", (x0, y0), 0.6, 0.3); placed.append((x0, y0)); continue
            dx, dy = x0 - cx, y0 - cy
            base = math.atan2(dy, dx) if (dx or dy) else 0.0
            ok = False
            for da in (0, 0.5, -0.5, 1.0, -1.0, 1.6, -1.6, 3.14):
                ang = base + da
                for dist in (1.0, 1.4, 1.9):
                    ex = abs(math.cos(ang)) * hw + abs(math.sin(ang)) * hh
                    x, y = x0 + math.cos(ang) * (ex + dist * 0.6), y0 + math.sin(ang) * (ex + dist * 0.6)
                    if free(x, y):
                        via(board, nets, "GND", (x, y), 0.6, 0.3)
                        track(board, nets, "GND", F, [(x0, y0), (x, y)], 0.4)
                        placed.append((x, y)); ok = True; break
                if ok:
                    break
            n_ok += ok; n_bad += (not ok)
            if not ok:
                print("  no GND via for", ref, p.GetNumber())
    print("GND vias:", n_ok, "failed:", n_bad)


def export_dsn(board, path):
    """DSN for Freerouting with a temporary keep-out over the mains region and per-net track widths."""
    kz = [zone(board, None, l, MAINS_POLY, rule="keepout") for l in (F, B)]
    pcbnew.ExportSpecctraDSN(board, path)
    for z in kz:
        board.Remove(z)
    txt = open(path, encoding="utf-8").read()
    import re
    m = re.search(r"\(class kicad_default (.*?)\(circuit", txt, re.S)
    names = m.group(1).split()
    groups = {}
    for n in names:
        w = POWER.get(n)
        if w:
            groups.setdefault(w, []).append(n)
    keep = [n for n in names if not POWER.get(n)]
    new = "(class kicad_default " + " ".join(keep) + "\n      (circuit"
    txt = txt[:m.start()] + new + txt[m.end():]
    extra = ""
    for w, lst in sorted(groups.items()):
        extra += ('    (class pwr%d %s\n      (circuit\n        (use_via "Via[0-1]_600:300_um")\n      )\n'
                  '      (rule\n        (width %d)\n        (clearance 200)\n      )\n    )\n') % (int(w * 1000), " ".join(lst), int(w * 1000))
    i = txt.index("(class kicad_default")
    txt = txt[:i] + extra.lstrip() + "    " + txt[i:]
    txt = re.sub(r"\(net GND\s*\(pins[^)]*\)\s*\)", "", txt)
    txt = re.sub(r"(\(class pwr\d+[^(]*?)\bGND\b", r"\1", txt)
    open(path, "w", encoding="utf-8").write(txt)


def finish(board, nets):
    """GND pours on the LV region (both layers), mains region kept free of pour."""
    for l in (F, B):
        zone(board, nets, l, LV_POLY, "GND")
        zone(board, nets, l, MAINS_POLY, rule="nofill")
    pcbnew.ZONE_FILLER(board).Fill(board.Zones())


def copper(board, layer=None):
    """(x, y, radius, net, layers) samples of all copper, for simple clearance checks."""
    import math
    out = []
    for fp in board.GetFootprints():
        for pd in fp.Pads():
            q = pd.GetPosition(); bb = pd.GetBoundingBox()
            ls = [l for l in (F, B) if pd.IsOnLayer(l)]
            r = min(ToMM(bb.GetWidth()), ToMM(bb.GetHeight())) / 2
            # long pads: sample along the long axis
            wdt, hgt = ToMM(bb.GetWidth()), ToMM(bb.GetHeight())
            n = max(1, int(abs(wdt - hgt) / r)) if r > 0 else 1
            for k in range(n + 1):
                fx = (k / n - 0.5) * (wdt - 2 * r) if wdt > hgt else 0
                fy = (k / n - 0.5) * (hgt - 2 * r) if hgt > wdt else 0
                out.append((ToMM(q.x) + fx, ToMM(q.y) + fy, r, pd.GetNetname(), ls))
    for t in board.GetTracks():
        a_, b_ = t.GetStart(), t.GetEnd()
        ls = [F, B] if t.GetClass() == "PCB_VIA" else [t.GetLayer()]
        L = ToMM((a_ - b_).EuclideanNorm())
        n = max(1, int(L / 0.2))
        for k in range(n + 1):
            out.append((ToMM(a_.x) + (ToMM(b_.x) - ToMM(a_.x)) * k / n, ToMM(a_.y) + (ToMM(b_.y) - ToMM(a_.y)) * k / n,
                        ToMM(t.GetWidth()) / 2, t.GetNetname(), ls))
    return out


def path_clear(cu, pts, w, net, layer, clr=0.22):
    import math
    for a, b in zip(pts, pts[1:]):
        L = math.hypot(b[0] - a[0], b[1] - a[1]); n = max(1, int(L / 0.1))
        for k in range(n + 1):
            x, y = a[0] + (b[0] - a[0]) * k / n, a[1] + (b[1] - a[1]) * k / n
            for ox, oy, r, on, ls in cu:
                if on != net and layer in ls and math.hypot(ox - x, oy - y) < r + w / 2 + clr:
                    return False
    return True


STITCHED = []


def drop_dead_stitches(board):
    """Remove stitching vias that do not land in the filled GND pour on both layers."""
    zs = [z for z in board.Zones() if not z.GetIsRuleArea() and z.GetNetname() == "GND"]
    dead = []
    for t in list(board.GetTracks()):
        if t.GetClass() != "PCB_VIA" or t.GetNetname() != "GND":
            continue
        q = t.GetPosition(); xy = (round(ToMM(q.x), 3), round(ToMM(q.y), 3))
        if not any(abs(xy[0] - a) < 0.01 and abs(xy[1] - b) < 0.01 for a, b in STITCHED):
            continue
        ok = all(any(z.GetLayer() == l and z.HitTestFilledArea(l, q) for z in zs) for l in (F, B))
        if not ok:
            dead.append(t)
    for t in dead:
        board.Remove(t)
    print("removed dead stitching vias:", len(dead))
    return len(dead)


def stitch(board, nets):
    """GND stitching vias on a 5 mm grid wherever both layers are free (joins the top and bottom pours)."""
    import math
    cu = copper(board)
    n = 0
    y = 3.0
    while y < H - 3:
        x = 3.0
        while x < W - 3:
            if not in_mains(x, y, 1.5):
                if all(math.hypot(ox - x, oy - y) >= r + 0.3 + 0.6 for ox, oy, r, on, ls in cu if on != "GND"):
                    via(board, nets, "GND", (x, y), 0.6, 0.3); cu.append((x, y, 0.3, "GND", [F, B])); n += 1
                    STITCHED.append((x, y))
            x += 5.0
        y += 5.0
    print("stitching vias:", n)


def repair(board):
    """After routing: K3 coil stub, USB-C GND pins, stitching vias, and a via for every GND pad still unconnected."""
    import math, re
    nets = {n: board.FindNet(n) for n in ("GND", "K3_COIL")}
    fps = {fp.GetReference(): fp for fp in board.GetFootprints()}
    cu = copper(board)
    k3 = P(fps, "K3", 5)
    d12 = P(fps, "D12", 2)
    vpos = (d12[0], d12[1] - 1.05)
    bottom = [k3, (46.3, k3[1]), (46.3, 43.0), vpos]
    if path_clear(cu, bottom, 0.4, "K3_COIL", B) and path_clear(cu, [vpos, d12], 0.4, "K3_COIL", F) \
            and path_clear(cu, [vpos, vpos], 0.6, "K3_COIL", F) and path_clear(cu, [vpos, vpos], 0.6, "K3_COIL", B):
        track(board, nets, "K3_COIL", B, bottom, 0.4); via(board, nets, "K3_COIL", vpos, 0.6, 0.3)
        track(board, nets, "K3_COIL", F, [vpos, d12], 0.4); print("K3 coil joined to D12 on the bottom layer")
    else:
        print("  K3 coil: no clear path")
    for a_, b_ in (("A12", "SH"), ("B12", "SH"), ("A1", "SH"), ("B1", "SH")):
        pa = [pd for pd in fps["J6"].Pads() if pd.GetNumber() == a_][0].GetPosition()
        shs = [pd.GetPosition() for pd in fps["J6"].Pads() if pd.GetNumber() == "SH"]
        sh = min(shs, key=lambda q: (q - pa).EuclideanNorm())
        A, Bp = (ToMM(pa.x), ToMM(pa.y)), (ToMM(sh.x), ToMM(sh.y))
        if math.hypot(A[0] - Bp[0], A[1] - Bp[1]) < 2.5 and path_clear(cu, [A, Bp], 0.3, "GND", F, 0.15):
            track(board, nets, "GND", F, [A, Bp], 0.3)
    stitch(board, nets)
    for it in range(3):
        for z in board.Zones():
            if not z.GetIsRuleArea():
                z.UnFill()
        pcbnew.ZONE_FILLER(board).Fill(board.Zones())
        if drop_dead_stitches(board):
            for z in board.Zones():
                if not z.GetIsRuleArea():
                    z.UnFill()
            pcbnew.ZONE_FILLER(board).Fill(board.Zones())
        tmp = PCB + ".tmp.kicad_pcb"
        pcbnew.SaveBoard(tmp, board)
        rpt = tmp + ".rpt"
        subprocess.run([CLI, "pcb", "drc", "--severity-error", "-o", rpt, tmp], capture_output=True)
        txt = open(rpt, encoding="utf-8").read()
        for f_ in (tmp, rpt):
            os.remove(f_)
        for ext in (".kicad_pro", ".kicad_prl"):
            if os.path.exists(tmp[:-len(".kicad_pcb")] + ext):
                os.remove(tmp[:-len(".kicad_pcb")] + ext)
        bad = sorted(set(re.findall(r"(?:Конт\. пл\.|Pad) (\S+) \[GND\] (?:от|of) (\S+) на F\.Cu", txt)))
        print("repair pass", it, "unconnected GND pads:", len(bad))
        if not bad:
            break
        cu = copper(board)
        for num, ref in bad:
            pd = [q for q in fps[ref].Pads() if q.GetNumber() == num][0]
            q = pd.GetPosition(); x0, y0 = ToMM(q.x), ToMM(q.y)
            done = False
            # 1) a via next to the pad
            for r in (1.0, 1.3, 1.6, 2.0, 2.5, 3.0):
                for k in range(24):
                    ang = k * math.pi / 12
                    x, y = x0 + r * math.cos(ang), y0 + r * math.sin(ang)
                    if in_mains(x, y, 1.0) or not (1.5 < x < W - 1.5 and 1.5 < y < H - 1.5):
                        continue
                    if all(math.hypot(ox - x, oy - y) >= rr + 0.3 + 0.25 for ox, oy, rr, on, ls in cu if on != "GND") \
                            and path_clear(cu, [(x0, y0), (x, y)], 0.3, "GND", F):
                        via(board, nets, "GND", (x, y), 0.6, 0.3); track(board, nets, "GND", F, [(x0, y0), (x, y)], 0.3)
                        cu.append((x, y, 0.3, "GND", [F, B])); done = True; break
                if done:
                    break
            # 2) a straight track to the nearest other GND copper on the top layer
            if not done:
                cands = sorted(((math.hypot(ox - x0, oy - y0), ox, oy) for ox, oy, rr, on, ls in cu
                                if on == "GND" and F in ls and 0.8 < math.hypot(ox - x0, oy - y0) < 5), key=lambda c: c[0])
                for d, ox, oy in cands[:40]:
                    if path_clear(cu, [(x0, y0), (ox, oy)], 0.3, "GND", F):
                        track(board, nets, "GND", F, [(x0, y0), (ox, oy)], 0.3); done = True; break
            if not done:
                print("  could not fix", ref, num)


def island_fix(board):
    """Top-layer GND pour islands with no via get one (placed where the bottom layer is free or GND)."""
    import math
    nets = {"GND": board.FindNet("GND")}
    cu = copper(board)
    vias = [t.GetPosition() for t in board.GetTracks() if t.GetClass() == "PCB_VIA" and t.GetNetname() == "GND"]
    thp = [p_.GetPosition() for fp in board.GetFootprints() for p_ in fp.Pads()
           if p_.GetNetname() == "GND" and p_.IsOnLayer(B) and p_.IsOnLayer(F)]
    added = 0
    for z in board.Zones():
        if z.GetIsRuleArea() or z.GetLayer() != F:
            continue
        polys = z.GetFilledPolysList(F)
        for i in range(polys.OutlineCount()):
            if any(polys.Contains(v, i) for v in vias + thp):
                continue
            bb = polys.Outline(i).BBox()
            x0, y0, x1, y1 = ToMM(bb.GetLeft()), ToMM(bb.GetTop()), ToMM(bb.GetRight()), ToMM(bb.GetBottom())
            done = False
            step = 0.25
            y = y0 + 0.4
            while y < y1 - 0.4 and not done:
                x = x0 + 0.4
                while x < x1 - 0.4:
                    q = VECTOR2I(FromMM(x), FromMM(y))
                    if polys.Contains(q, i) and all(math.hypot(ox - x, oy - y) >= r + 0.3 + 0.2
                                                    for ox, oy, r, on, ls in cu if on != "GND"):
                        # the via must sit well inside the island
                        if all(polys.Contains(VECTOR2I(FromMM(x + dx), FromMM(y + dy)), i)
                               for dx, dy in ((0.35, 0), (-0.35, 0), (0, 0.35), (0, -0.35))):
                            via(board, nets, "GND", (x, y), 0.6, 0.3); cu.append((x, y, 0.3, "GND", [F, B]))
                            added += 1; done = True; break
                    x += step
                y += step
            if not done:
                print("  island without room for a via near", round(x0, 1), round(y0, 1))
    print("island vias:", added)
    for z in board.Zones():
        if not z.GetIsRuleArea():
            z.UnFill()
    pcbnew.ZONE_FILLER(board).Fill(board.Zones())


def gnd_components(board):
    """Connected components of the GND pours: nodes (layer, island index); joined by GND vias and THT pads."""
    zs = {z.GetLayer(): z for z in board.Zones() if not z.GetIsRuleArea() and z.GetNetname() == "GND"}
    polys = {l: zs[l].GetFilledPolysList(l) for l in (F, B)}
    links = [t.GetPosition() for t in board.GetTracks() if t.GetClass() == "PCB_VIA" and t.GetNetname() == "GND"]
    links += [p_.GetPosition() for fp in board.GetFootprints() for p_ in fp.Pads()
              if p_.GetNetname() == "GND" and p_.IsOnLayer(F) and p_.IsOnLayer(B)]
    parent = {}
    def find_(a):
        while parent.setdefault(a, a) != a:
            a = parent[a]
        return a
    for l in (F, B):
        for i in range(polys[l].OutlineCount()):
            find_((l, i))
    for q in links:
        hit = [(l, i) for l in (F, B) for i in range(polys[l].OutlineCount()) if polys[l].Contains(q, i)]
        for h in hit[1:]:
            parent[find_(h)] = find_(hit[0])
    comps = {}
    for node in list(parent):
        comps.setdefault(find_(node), []).append(node)
    return polys, list(comps.values())


def local_gnd_route(board, start, start_layers, main, polys, half=10.0, G=0.1, w=0.3, clr=0.25):
    """Grid search (both layers, vias allowed) from a GND point to the pour of the main component."""
    import heapq, math
    cu = copper(board)
    x0, y0 = start[0] - half, start[1] - half
    N = int(2 * half / G) + 1
    blocked = {F: bytearray(N * N), B: bytearray(N * N)}
    for ox, oy, r, on, ls in cu:
        if on == "GND":
            continue
        rr = r + w / 2 + clr
        i0, i1 = int((ox - rr - x0) / G), int((ox + rr - x0) / G) + 1
        j0, j1 = int((oy - rr - y0) / G), int((oy + rr - y0) / G) + 1
        for l in ls:
            if l not in blocked:
                continue
            bl = blocked[l]
            for i in range(max(0, i0), min(N, i1 + 1)):
                dx = x0 + i * G - ox
                for j in range(max(0, j0), min(N, j1 + 1)):
                    dy = y0 + j * G - oy
                    if dx * dx + dy * dy < rr * rr:
                        bl[i * N + j] = 1
    # via needs room on both layers (via radius 0.3 instead of half track width)
    def via_ok(i, j):
        k = int((0.3 - w / 2) / G) + 1
        for l in (F, B):
            for di in range(-k, k + 1):
                for dj in range(-k, k + 1):
                    ii, jj = i + di, j + dj
                    if 0 <= ii < N and 0 <= jj < N and blocked[l][ii * N + jj]:
                        return False
        return True
    def is_target(l, i, j):
        q = VECTOR2I(FromMM(x0 + i * G), FromMM(y0 + j * G))
        return any(ll == l and polys[l].Contains(q, k) for ll, k in main)
    si, sj = int(round((start[0] - x0) / G)), int(round((start[1] - y0) / G))
    pq, dist, prev = [], {}, {}
    for l in start_layers:
        dist[(l, si, sj)] = 0; heapq.heappush(pq, (0, (l, si, sj)))
    found = None
    while pq:
        d, u = heapq.heappop(pq)
        if d > dist.get(u, 1e9):
            continue
        l, i, j = u
        if d > 3 and is_target(l, i, j):
            found = u; break
        for di, dj, c in ((1, 0, 1), (-1, 0, 1), (0, 1, 1), (0, -1, 1), (1, 1, 1.41), (1, -1, 1.41), (-1, 1, 1.41), (-1, -1, 1.41)):
            ii, jj = i + di, j + dj
            if 0 <= ii < N and 0 <= jj < N and (not blocked[l][ii * N + jj] or d < 2):
                v = (l, ii, jj); nd = d + c
                if nd < dist.get(v, 1e9):
                    dist[v] = nd; prev[v] = u; heapq.heappush(pq, (nd, v))
        ol = B if l == F else F
        v = (ol, i, j)
        if d + 40 < dist.get(v, 1e9) and via_ok(i, j):
            dist[v] = d + 40; prev[v] = u; heapq.heappush(pq, (d + 40, v))
    if not found:
        return False
    path = [found]
    while path[-1] in prev:
        path.append(prev[path[-1]])
    path.reverse()
    nets = {"GND": board.FindNet("GND")}
    seg = [path[0]]
    for a_, b_ in zip(path, path[1:]):
        if a_[0] != b_[0]:
            pts = [(x0 + q[1] * G, y0 + q[2] * G) for q in seg]
            if len(pts) > 1:
                track(board, nets, "GND", a_[0], pts, w)
            via(board, nets, "GND", (x0 + a_[1] * G, y0 + a_[2] * G), 0.6, 0.3)
            seg = [b_]
        else:
            seg.append(b_)
    pts = [(x0 + q[1] * G, y0 + q[2] * G) for q in seg]
    if len(pts) > 1:
        track(board, nets, "GND", seg[0][0], pts, w)
    return True


def join_gnd(board):
    import math
    nets = {"GND": board.FindNet("GND")}
    for it in range(4):
        polys, comps = gnd_components(board)
        area = lambda c: sum(polys[l].Outline(i).Area() for l, i in c)
        comps.sort(key=area, reverse=True)
        if len(comps) <= 1:
            break
        main = comps[0]
        cu = copper(board)
        added = 0
        for comp in comps[1:]:
            done = False
            for (l, i) in comp:
                other = B if l == F else F
                bb = polys[l].Outline(i).BBox()
                x0, y0, x1, y1 = ToMM(bb.GetLeft()), ToMM(bb.GetTop()), ToMM(bb.GetRight()), ToMM(bb.GetBottom())
                y = y0 + 0.3
                while y < y1 and not done:
                    x = x0 + 0.3
                    while x < x1:
                        q = VECTOR2I(FromMM(x), FromMM(y))
                        ring = [VECTOR2I(FromMM(x + dx), FromMM(y + dy)) for dx, dy in ((0.35, 0), (-0.35, 0), (0, 0.35), (0, -0.35))]
                        if all(polys[l].Contains(r, i) for r in ring + [q]):
                            mains = [j for (ll, j) in main if ll == other and all(polys[other].Contains(r, j) for r in ring + [q])]
                            if mains and all(math.hypot(ox - x, oy - y) >= rr + 0.3 + 0.2 for ox, oy, rr, on, ls in cu if on != "GND"):
                                via(board, nets, "GND", (x, y), 0.6, 0.3); cu.append((x, y, 0.3, "GND", [F, B]))
                                added += 1; done = True; break
                        x += 0.25
                    y += 0.25
                if done:
                    break
        # fallback: a short grid-routed GND connection from the component to the main pour
        if not added:
            gitems = [(t.GetPosition(), [F, B]) for t in board.GetTracks() if t.GetClass() == "PCB_VIA" and t.GetNetname() == "GND"]
            gitems += [(p_.GetPosition(), [l for l in (F, B) if p_.IsOnLayer(l)]) for fp in board.GetFootprints()
                       for p_ in fp.Pads() if p_.GetNetname() == "GND"]
            for comp in comps[1:]:
                def near(q, tol=0.8):
                    pts = [q] + [VECTOR2I(q.x + FromMM(dx), q.y + FromMM(dy)) for dx in (-tol, 0, tol) for dy in (-tol, 0, tol)]
                    return any(polys[l].Contains(pp, i) for l, i in comp for pp in pts)
                for q, ls in [g for g in gitems if near(g[0])][:3]:
                    if local_gnd_route(board, (ToMM(q.x), ToMM(q.y)), ls, main, polys):
                        added += 1; break
            for z in board.Zones():
                if not z.GetIsRuleArea():
                    z.UnFill()
            pcbnew.ZONE_FILLER(board).Fill(board.Zones())
        print("join pass", it, "components:", len(comps), "links added:", added)
        for z in board.Zones():
            if not z.GetIsRuleArea():
                z.UnFill()
        pcbnew.ZONE_FILLER(board).Fill(board.Zones())
        if not added:
            break


def prune(board):
    """Remove Freerouting leftovers: vias used on one layer only and track ends that touch nothing."""
    def key(v):
        return (round(ToMM(v.x), 3), round(ToMM(v.y), 3))
    removed = 0
    for it in range(20):
        ends = {}
        pads = {}
        for fp in board.GetFootprints():
            for pd in fp.Pads():
                pads.setdefault(pd.GetNetname(), []).append(pd)
        tracks = [t for t in board.GetTracks() if t.GetClass() == "PCB_TRACK"]
        vias_ = [t for t in board.GetTracks() if t.GetClass() == "PCB_VIA"]
        def touches_pad(net, pt, layer):
            return any(pd.IsOnLayer(layer) and pd.HitTest(pt) for pd in pads.get(net, []))
        dead = []
        HAND = {"GND", "VBAT", "ACC_OUT", "START_OUT", "AUX_OUT"} | MAINS
        for t in tracks:
            if t.GetNetname() in HAND:
                continue
            for pt in (t.GetStart(), t.GetEnd()):
                hit = touches_pad(t.GetNetname(), pt, t.GetLayer())
                if not hit:
                    hit = any(o is not t and o.GetNetname() == t.GetNetname() and
                              ((o.GetClass() == "PCB_TRACK" and o.GetLayer() == t.GetLayer() and
                                (key(o.GetStart()) == key(pt) or key(o.GetEnd()) == key(pt) or o.HitTest(pt, 0))) or
                               (o.GetClass() == "PCB_VIA" and o.HitTest(pt)))
                              for o in tracks + vias_)
                if not hit:
                    dead.append(t); break
        for v in vias_:
            if v.GetNetname() in HAND:
                continue
            layers = set(t.GetLayer() for t in tracks if t.GetNetname() == v.GetNetname()
                         and (v.HitTest(t.GetStart()) or v.HitTest(t.GetEnd())))
            if len(layers) < 2 and not touches_pad(v.GetNetname(), v.GetPosition(), F):
                dead.append(v)
        if not dead:
            break
        for t in dead:
            board.Remove(t)
        removed += len(dead)
    print("pruned:", removed)


def silk(board):
    """Hide footprint texts; label connectors, LEDs, switches; title and mains warning."""
    fps = {fp.GetReference(): fp for fp in board.GetFootprints()}
    for fp in fps.values():
        for f_ in fp.GetFields():
            f_.SetVisible(False)
    def text(s_, x, y, size=1.0, layer=pcbnew.F_SilkS, rot=0):
        t = pcbnew.PCB_TEXT(board); t.SetText(s_); t.SetPosition(VECTOR2I(FromMM(x), FromMM(y)))
        t.SetLayer(layer); t.SetTextSize(VECTOR2I(FromMM(size), FromMM(size))); t.SetTextThickness(FromMM(size * 0.15))
        if rot:
            t.SetTextAngleDegrees(rot)
        if layer == pcbnew.B_SilkS:
            t.SetMirrored(True)
        board.Add(t)
    pin = lambda r, n: P(fps, r, n)
    LY = H - 2.5
    for ref, n, lab in [("J1", 1, "L"), ("J1", 2, "N"), ("J2", 1, "NO"), ("J2", 2, "COM"), ("J3", 1, "BAT+"), ("J3", 2, "BAT-"),
                        ("J4", 1, "ACC"), ("J4", 2, "START"), ("J8", 1, "AUX"), ("J8", 2, "GND"), ("J5", 1, "TAHO")]:
        text(lab, pin(ref, n)[0], LY, 1.0)
    # REMOTE: dry contact across J5 pins 2 and 3 (polarity does not matter), one label with a bracket over both pins
    r2, r3 = pin("J5", 2)[0], pin("J5", 3)[0]
    for a_, b_ in (((r2, LY - 2.0), (r2, LY - 1.4)), ((r2, LY - 2.0), (r3, LY - 2.0)), ((r3, LY - 2.0), (r3, LY - 1.4))):
        s = pcbnew.PCB_SHAPE(board); s.SetShape(pcbnew.SHAPE_T_SEGMENT); s.SetLayer(pcbnew.F_SilkS); s.SetWidth(FromMM(0.15))
        s.SetStart(VECTOR2I(FromMM(a_[0]), FromMM(a_[1]))); s.SetEnd(VECTOR2I(FromMM(b_[0]), FromMM(b_[1]))); board.Add(s)
    text("REMOTE", (r2 + r3) / 2, LY, 1.0)
    text("AC IN 230V", (pin("J1", 1)[0] + pin("J1", 2)[0]) / 2, 77.5, 1.0)
    text("CONTACTOR", (pin("J2", 1)[0] + pin("J2", 2)[0]) / 2, 77.5, 1.0)
    text("! 230V AC !", 13, 62, 1.5)
    text("Pramac autostart v6", 80, 2.2, 1.2)
    for ref, lab, dx, dy in [("D13", "ACC", -2, 1.8), ("D14", "START", 0, 1.8), ("D17", "AUX", 0, 1.8), ("D15", "CONT", 2.2, 0), ("D23", "CHG", 0, 2.6),
                             ("D24", "FULL", 0, 2.6), ("D30", "PWR", -0.6, 2.8), ("D31", "STAT", 1.4, 2.8),
                             ("SW1", "RESET", 0, -3.6), ("SW2", "BOOT", 0, -3.6), ("SW3", "MODE CHG DLY AUX", 0, 7.4),
                             ("J6", "USB", -5.5, 0), ("J7", "3V3 IO17 IO18 GND", -2.4, 3.8), ("U1", "ESP32-S3 (U.FL ANT)", 0, -9.2)]:
        q = fps[ref].GetPosition()
        text(lab, ToMM(q.x) + dx, ToMM(q.y) + dy, 0.8, rot={"J6": 90, "J7": 270}.get(ref, 0))
    text("github.com/4106677/pramac-pmd5050s-autostart", 85, H - 8, 1.0, pcbnew.B_SilkS)


DRU = """(version 1)
(rule "mains_to_lv"
  (condition "(A.NetName == 'AC_L' || A.NetName == 'AC_LF' || A.NetName == 'AC_N' || A.NetName == 'AC_D1' || A.NetName == 'AC_D2' || A.NetName == 'AC_D3' || A.NetName == 'CT_COM' || A.NetName == 'CT_NO') && !(B.NetName == 'AC_L' || B.NetName == 'AC_LF' || B.NetName == 'AC_N' || B.NetName == 'AC_D1' || B.NetName == 'AC_D2' || B.NetName == 'AC_D3' || B.NetName == 'CT_COM' || B.NetName == 'CT_NO')")
  (constraint clearance (min 2.5mm)))
"""


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "place"
    if mode == "place":
        board, fps, nets = build()
        n = check(board, fps)
        print("placement issues:", n)
        hand_route(board, fps, nets)
        gnd_vias(board, fps, nets)
        pcbnew.SaveBoard(PCB, board)
        export_dsn(board, PCB.replace(".kicad_pcb", ".dsn"))
        print("saved", PCB, "+ dsn")
    elif mode == "route":
        board = pcbnew.LoadBoard(PCB)
        ses = PCB.replace(".kicad_pcb", ".ses")
        print("import ses:", pcbnew.ImportSpecctraSES(board, ses))
        nets = {n: board.FindNet(n) for n in ("GND",)}
        finish(board, nets)
        board.GetDesignSettings().m_MinResolvedSpokes = 1
        repair(board)
        island_fix(board)
        join_gnd(board)
        prune(board)
        seen, dup = set(), []
        for t_ in board.GetTracks():
            if t_.GetClass() == "PCB_VIA":
                k_ = (t_.GetPosition().x, t_.GetPosition().y, t_.GetNetname())
                if k_ in seen:
                    dup.append(t_)
                seen.add(k_)
        for t_ in dup:
            board.Remove(t_)
        print("duplicate vias removed:", len(dup))
        silk(board)
        for z in board.Zones():
            if not z.GetIsRuleArea():
                z.UnFill()
        pcbnew.ZONE_FILLER(board).Fill(board.Zones())
        pcbnew.SaveBoard(PCB, board)
        open(PCB.replace(".kicad_pcb", ".kicad_dru"), "w").write(DRU)
        print("saved", PCB)
    elif mode == "export":
        import csv, shutil, tempfile, zipfile
        run = lambda *a: subprocess.run([CLI] + list(a), check=True, capture_output=True)
        run("pcb", "drc", "-o", os.path.join(HERE, "drc.rpt"), PCB)
        tmp = tempfile.mkdtemp()
        run("pcb", "export", "gerbers", "--layers", "F.Cu,B.Cu,F.Mask,B.Mask,F.Paste,F.Silkscreen,B.Silkscreen,Edge.Cuts",
            "--subtract-soldermask", "-o", tmp + "/", PCB)
        run("pcb", "export", "drill", "--excellon-separate-th", "-o", tmp + "/", PCB)
        with zipfile.ZipFile(os.path.join(HERE, "pramac_v6_gerbers.zip"), "w", zipfile.ZIP_DEFLATED) as z:
            for f_ in sorted(os.listdir(tmp)):
                z.write(os.path.join(tmp, f_), f_)
        pos = os.path.join(tmp, "pos.csv")
        run("pcb", "export", "pos", "--format", "csv", "--units", "mm", "--side", "both", "-o", pos, PCB)
        skip = lambda r: r.startswith(("H", "TP"))     # holes and bare test pads: nothing to place
        with open(pos, encoding="utf-8") as fi, open(os.path.join(HERE, "pramac_v6_cpl.csv"), "w", newline="", encoding="utf-8") as fo:
            w = csv.writer(fo)
            w.writerow(["Designator", "Mid X", "Mid Y", "Layer", "Rotation"])
            for r in csv.DictReader(fi):
                if not skip(r["Ref"]):
                    w.writerow([r["Ref"], r["PosX"] + "mm", r["PosY"] + "mm", r["Side"].capitalize(), r["Rot"]])
        shutil.rmtree(tmp)
        for s_ in ("top", "bottom"):
            run("pcb", "render", "--side", s_, "--width", "1848", "--height", "1488", "--background", "opaque",
                "-o", os.path.join(HERE, "pcb-%s.png" % s_), PCB)
        run("sch", "export", "pdf", "-o", os.path.join(HERE, "pramac_v6_schematic.pdf"), os.path.join(HERE, "pramac_v6.kicad_sch"))
        print("exported gerbers, drill, CPL, renders, schematic PDF")
