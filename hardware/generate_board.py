#!/usr/bin/env python3
"""Pramac PMD5050S carrier board generator (KiCad pcbnew API). Run with KiCad's python."""
import heapq, math, sys
import pcbnew
from pcbnew import VECTOR2I, FromMM, ToMM

LIB = "/Applications/KiCad/KiCad.app/Contents/SharedSupport/footprints/"
OUT = sys.argv[1] if len(sys.argv) > 1 else "pramac_carrier.kicad_pcb"
BW, BH = 112.0, 92.0
G = 0.25           # router grid, mm
CLR = 0.25         # routing clearance (DRC min is 0.2)
EDGE = 0.8         # keep tracks away from board edge

board = pcbnew.BOARD()
F, B = pcbnew.F_Cu, pcbnew.B_Cu
ds = board.GetDesignSettings()
nc = ds.m_NetSettings.GetDefaultNetclass()
nc.SetClearance(FromMM(0.2)); nc.SetTrackWidth(FromMM(0.3))
nc.SetViaDiameter(FromMM(0.9)); nc.SetViaDrill(FromMM(0.5))
ds.m_MinThroughDrill = FromMM(0.3)

NETS = {}
def net(name):
    if name not in NETS:
        ni = pcbnew.NETINFO_ITEM(board, name); board.Add(ni); NETS[name] = ni
    return NETS[name]

FP = {}
def place(ref, lib, name, x, y, rot=0, value=""):
    fp = pcbnew.FootprintLoad(LIB + lib + ".pretty", name)
    fp.SetReference(ref); fp.SetValue(value or name)
    fp.SetPosition(VECTOR2I(FromMM(x), FromMM(y)))
    if rot: fp.SetOrientationDegrees(rot)
    board.Add(fp); FP[ref] = fp
    return fp

def pad(ref, num):
    for p in FP[ref].Pads():
        if p.GetNumber() == str(num): return p
    raise KeyError((ref, num))

def assign(ref, num, netname):
    pad(ref, num).SetNet(net(netname))

# ---------------- board outline + mounting holes ----------------
def outline():
    for (a, b, c, d) in [(0, 0, BW, 0), (BW, 0, BW, BH), (BW, BH, 0, BH), (0, BH, 0, 0)]:
        s = pcbnew.PCB_SHAPE(board); s.SetShape(pcbnew.SHAPE_T_SEGMENT)
        s.SetLayer(pcbnew.Edge_Cuts); s.SetWidth(FromMM(0.1))
        s.SetStart(VECTOR2I(FromMM(a), FromMM(b))); s.SetEnd(VECTOR2I(FromMM(c), FromMM(d)))
        board.Add(s)
outline()
for i, (x, y) in enumerate([(4, 4), (BW - 4, 4), (4, BH - 4), (BW - 4, BH - 4)], 1):
    place("H%d" % i, "MountingHole", "MountingHole_3.2mm_M3", x, y, value="M3")

# ---------------- components ----------------
TB2 = ("TerminalBlock_Phoenix", "TerminalBlock_Phoenix_MKDS-1,5-2_1x02_P5.00mm_Horizontal")
TB3 = ("TerminalBlock_Phoenix", "TerminalBlock_Phoenix_MKDS-1,5-3_1x03_P5.00mm_Horizontal")
RV = ("Resistor_THT", "R_Axial_DIN0207_L6.3mm_D2.5mm_P2.54mm_Vertical")
D15V = ("Diode_THT", "D_DO-15_P3.81mm_Vertical_CathodeUp")
D201V = ("Diode_THT", "D_DO-201AD_P3.81mm_Vertical_CathodeUp")
D35V = ("Diode_THT", "D_DO-35_SOD27_P2.54mm_Vertical_CathodeUp")
HDR2 = ("Connector_PinHeader_2.54mm", "PinHeader_1x02_P2.54mm_Vertical")
HDR3 = ("Connector_PinHeader_2.54mm", "PinHeader_1x03_P2.54mm_Vertical")
RELAY = ("Relay_THT", "Relay_SPDT_SANYOU_SRD_Series_Form_C")
TO92 = ("Package_TO_SOT_THT", "TO-92_Inline")

# terminals along the bottom edge (wire entry towards the edge)
TY = 84
place("J1", *TB2, 11, TY, value="BATT- / BATT+")
place("J4", *TB2, 23, TY, value="CHARGER +12V / GND")
place("J5", *TB2, 35, TY, value="ACC OUT / START OUT (relay NO)")
place("J2", *TB3, 72, TY, value="TAHO / REMOTE 1 / REMOTE 2")
# power
place("F1", "Fuse", "Fuseholder_Cylinder-5x20mm_Schurter_0031_8201_Horizontal_Open", 19.5, 42, value="Fuse 5x20 T2A")
place("C1", "Capacitor_THT", "CP_Radial_D18.0mm_P7.50mm", 10, 20, value="4700u 25V")
place("C2", "Capacitor_THT", "CP_Radial_D18.0mm_P7.50mm", 32, 20, value="4700u 25V")
place("D3", *D15V, 44, 34, value="P6KE36A (P6KE20A recommended)")
place("D1", *D201V, 52, 28, 180, value="1N5821")
place("RM1", *HDR3, 50, 12, value="Favotek RM20S-050 SIP-3: 1 +VIN, 2 GND, 3 +VOUT")
for _p in FP["RM1"].Pads():            # datasheet: pitch 2.54, hole 1.2
    _p.SetSize(VECTOR2I(FromMM(2.0), FromMM(2.0))); _p.SetDrillSize(VECTOR2I(FromMM(1.2), FromMM(1.2)))
_r = pcbnew.PCB_SHAPE(board); _r.SetShape(pcbnew.SHAPE_T_RECT); _r.SetLayer(pcbnew.F_SilkS); _r.SetWidth(FromMM(0.15))
_r.SetStart(VECTOR2I(FromMM(50 - 2.15), FromMM(14.54 - 5.75))); _r.SetEnd(VECTOR2I(FromMM(50 + 6.85), FromMM(14.54 + 5.75)))
board.Add(_r)
place("D2", *D201V, 62, 26, 180, value="1N5821")
place("SC1", *HDR2, 60, 32, value="Supercap 1F 5.5V +/-")
# ESP32 30-pin DevKit V1 sockets, row spacing 25.4 mm
place("U1A", "Connector_PinSocket_2.54mm", "PinSocket_1x15_P2.54mm_Vertical", 70, 6, value="ESP32 left")
place("U1B", "Connector_PinSocket_2.54mm", "PinSocket_1x15_P2.54mm_Vertical", 95.4, 6, value="ESP32 right")
place("J3", "Connector_PinHeader_2.54mm", "PinHeader_1x04_P2.54mm_Vertical", 102.5, 20, value="Spare relay module 5V/IN1(D18)/IN2(D19)/GND")
# relays (rot 270: COM on top, contacts at the bottom)
place("K1", *RELAY, 33, 56, 270, value="SRD-05VDC-SL-C ACC")
place("K2", *RELAY, 63, 56, 270, value="SRD-05VDC-SL-C START")
# relay drivers in the gap between the relays
place("Q1", *TO92, 43, 56, value="BC337")
place("Rb1", *RV, 43, 60, value="1k")
place("Rp1", *RV, 43, 64, value="10k")
place("D6", *D35V, 43, 68, value="1N4148")
place("Q2", *TO92, 49.5, 56, value="BC337")
place("Rb2", *RV, 49.5, 60, value="1k")
place("Rp2", *RV, 49.5, 64, value="10k")
place("D7", *D35V, 49.5, 68, value="1N4148")
# TAHO conditioning
place("R1", *RV, 74, 70, value="22k")
place("C3", "Capacitor_THT", "CP_Radial_D5.0mm_P2.00mm", 80, 70.5, value="10u 16V NP")
place("D4", *D35V, 72, 75, value="BZX55C5V1")
place("D5", *D35V, 80.5, 75, 180, value="BZX55C5V1")
place("Rb3", *RV, 86, 66, value="10k")
place("Rv1", *RV, 86, 70, value="10k")
place("Rv2", *RV, 92, 70, value="10k")
place("U3", "Package_DIP", "DIP-8_W7.62mm_Socket", 98, 62, value="LM393")
place("R4", *RV, 92, 60, value="100k")
place("R5", *RV, 92, 64, value="4.7k")
place("C5", "Capacitor_SMD", "C_0805_2012Metric", 102, 74, 90, value="100n")
place("R6", *RV, 88, 78, value="1k")
place("C6", "Capacitor_SMD", "C_0805_2012Metric", 96, 78, 90, value="100n")

# DG128-5.0 datasheet: pitch 5.0, drill 1.4 mm
for _r in ("J1", "J4", "J5", "J2"):
    for _p in FP[_r].Pads():
        _p.SetDrillSize(VECTOR2I(FromMM(1.4), FromMM(1.4)))
        _p.SetSize(VECTOR2I(FromMM(max(2.6, ToMM(_p.GetSizeX()))), FromMM(max(2.6, ToMM(_p.GetSizeY())))))

# ---------------- netlist ----------------
for ref, n in [("J1", {1: "GND", 2: "VBATT"}), ("J4", {1: "VBATT", 2: "GND"}),
               ("F1", {1: "VBATT", 2: "VBF"}),
               ("D3", {1: "VBF", 2: "GND"}),            # TVS cathode on +
               ("D1", {2: "VBF", 1: "NODE_A"}),         # anode VBF, cathode NODE_A
               ("C1", {1: "NODE_A", 2: "GND"}), ("C2", {1: "NODE_A", 2: "GND"}),
               ("RM1", {1: "NODE_A", 2: "GND", 3: "VBUCK"}),   # SIP-3 Vin GND Vout (provisional)
               ("D2", {2: "VBUCK", 1: "NODE_B"}),
               ("SC1", {1: "NODE_B", 2: "GND"}),
               ("J3", {1: "NODE_B", 2: "EXT1", 3: "EXT2", 4: "GND"}),
               ("K1", {1: "VBATT", 2: "NODE_B", 3: "ACC_OUT", 5: "COIL_ACC"}),
               ("K2", {1: "VBATT", 5: "NODE_B", 3: "START_OUT", 2: "COIL_START"}),
               ("J5", {1: "ACC_OUT", 2: "START_OUT"}),
               ("Q1", {1: "COIL_ACC", 2: "BASE_ACC", 3: "GND"}), ("Rb1", {1: "ACC", 2: "BASE_ACC"}), ("Rp1", {1: "BASE_ACC", 2: "GND"}),
               ("D6", {1: "NODE_B", 2: "COIL_ACC"}),
               ("Q2", {1: "COIL_START", 2: "BASE_START", 3: "GND"}), ("Rb2", {1: "START", 2: "BASE_START"}), ("Rp2", {1: "BASE_START", 2: "GND"}),
               ("D7", {1: "NODE_B", 2: "COIL_START"}),
               ("J2", {1: "TAHO_IN", 2: "CONTACT", 3: "GND"}),
               ("R1", {1: "TAHO_IN", 2: "TAHO_CL"}),
               ("D4", {1: "TAHO_CL", 2: "ZMID"}), ("D5", {1: "GND", 2: "ZMID"}),
               ("C3", {1: "TAHO_CL", 2: "TAHO_AC"}),
               ("Rb3", {1: "TAHO_AC", 2: "VB"}),
               ("Rv2", {1: "VB", 2: "GND"}), ("Rv1", {1: "VB", 2: "3V3"}),
               ("U3", {1: "CMP_OUT", 2: "TAHO_AC", 3: "VB", 4: "GND", 5: "UNUSED_IN", 6: "UNUSED_IN", 8: "3V3"}),
               ("R4", {1: "CMP_OUT", 2: "VB"}), ("R5", {1: "CMP_OUT", 2: "3V3"}),
               ("C5", {1: "3V3", 2: "GND"}),
               ("R6", {1: "CONTACT", 2: "D25"}), ("C6", {1: "D25", 2: "GND"}),
               ("U1A", {8: "D25", 11: "CMP_OUT", 14: "GND", 15: "NODE_B"}),
               ("U1B", {6: "EXT2", 7: "EXT1", 11: "START", 12: "ACC", 14: "GND", 15: "3V3"}),
               ]:
    for k, v in n.items():
        assign(ref, k, v)

# ---------------- router ----------------
NX, NY = int(BW / G) + 1, int(BH / G) + 1
POWER = {"VBF", "NODE_A", "NODE_B", "VBUCK"}
WIDTH = {n: 1.5 for n in POWER}

DEFW = 0.4
obst = {F: [], B: []}     # (xmin,ymin,xmax,ymax,netname)

def pad_layers(p):
    ls = []
    if p.IsOnLayer(F): ls.append(F)
    if p.IsOnLayer(B): ls.append(B)
    return ls

for fp in FP.values():
    for p in fp.Pads():
        bb = p.GetBoundingBox()
        r = (ToMM(bb.GetLeft()), ToMM(bb.GetTop()), ToMM(bb.GetRight()), ToMM(bb.GetBottom()), p.GetNetname() or "")
        for l in pad_layers(p): obst[l].append(r)
# board edge
for l in (F, B):
    obst[l] += [(-5, -5, BW + 5, EDGE - 0.0, "#edge"), (-5, BH - EDGE, BW + 5, BH + 5, "#edge"),
                (-5, -5, EDGE, BH + 5, "#edge"), (BW - EDGE, -5, BW + 5, BH + 5, "#edge")]

def mask(layer, netname, w):
    m = [bytearray(NY) for _ in range(NX)]
    mar = CLR + w / 2.0
    for (x0, y0, x1, y1, n) in obst[layer]:
        if n == netname and n != "": continue
        i0 = max(0, int(math.floor((x0 - mar) / G))); i1 = min(NX - 1, int(math.ceil((x1 + mar) / G)))
        j0 = max(0, int(math.floor((y0 - mar) / G))); j1 = min(NY - 1, int(math.ceil((y1 + mar) / G)))
        ln = j1 - j0 + 1
        for ii in range(i0, i1 + 1):
            m[ii][j0:j1 + 1] = b'\x01' * ln
    return m

def cell(x, y): return (int(round(x / G)), int(round(y / G)))
def xy(c): return (c[0] * G, c[1] * G)

tracks_by_net = {}   # net -> list of (layer, (x0,y0),(x1,y1))
vias = []

def add_track(n, layer, a, b, w):
    if a == b: return
    t = pcbnew.PCB_TRACK(board)
    t.SetStart(VECTOR2I(FromMM(a[0]), FromMM(a[1]))); t.SetEnd(VECTOR2I(FromMM(b[0]), FromMM(b[1])))
    t.SetWidth(FromMM(w)); t.SetLayer(layer); t.SetNet(net(n)); board.Add(t)
    tracks_by_net.setdefault(n, []).append((layer, a, b))
    h = w / 2
    obst[layer].append((min(a[0], b[0]) - h, min(a[1], b[1]) - h, max(a[0], b[0]) + h, max(a[1], b[1]) + h, n))

def add_via(n, p):
    v = pcbnew.PCB_VIA(board)
    v.SetPosition(VECTOR2I(FromMM(p[0]), FromMM(p[1])))
    v.SetWidth(FromMM(0.9)); v.SetDrill(FromMM(0.5)); v.SetViaType(pcbnew.VIATYPE_THROUGH)
    v.SetLayerPair(F, B); v.SetNet(net(n)); board.Add(v)
    h = 0.45
    for l in (F, B): obst[l].append((p[0] - h, p[1] - h, p[0] + h, p[1] + h, n))
    vias.append((n, p))

def route_net(n, pads_list, layers_allowed):
    w = WIDTH.get(n, DEFW)
    pts = []
    for (ref, num) in pads_list:
        p = pad(ref, num); pos = p.GetPosition()
        pts.append(((ToMM(pos.x), ToMM(pos.y)), pad_layers(p), ref + "." + str(num)))
    if len(pts) < 2: return True
    masks = {l: mask(l, n, w) for l in layers_allowed}
    tree = set()   # (layer, ci, cj)
    def addcell(l, c): tree.add((l, c[0], c[1]))
    first = pts[0]
    for l in first[1]:
        if l in layers_allowed: addcell(l, cell(*first[0]))
    remaining = pts[1:]
    ok = True
    while remaining:
        # nearest remaining pad to tree (by pad centre distance to first-pad for simplicity)
        remaining.sort(key=lambda q: min(abs(q[0][0] - t[1] * G) + abs(q[0][1] - t[2] * G) for t in tree))
        q = remaining.pop(0)
        src = [(l, *cell(*q[0])) for l in q[1] if l in layers_allowed]
        for s in src: masks[s[0]][s[1]][s[2]] = 0
        for t in tree: masks[t[0]][t[1]][t[2]] = 0
        dist = {}; prev = {}; pq = []
        for s in src:
            dist[s] = 0; heapq.heappush(pq, (0, s, None))
        found = None
        while pq:
            d, u, dirn = heapq.heappop(pq)
            if d > dist.get(u, 1e18): continue
            if u in tree: found = u; break
            l, i, j = u
            for (di, dj) in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                ni, nj = i + di, j + dj
                if not (0 <= ni < NX and 0 <= nj < NY): continue
                if masks[l][ni][nj]: continue
                nd = d + 1 + (0.6 if dirn is not None and dirn != (di, dj) else 0)
                v = (l, ni, nj)
                if nd < dist.get(v, 1e18):
                    dist[v] = nd; prev[v] = u; heapq.heappush(pq, (nd, v, (di, dj)))
            if len(layers_allowed) > 1:
                ol = B if l == F else F
                if ol in masks and not masks[ol][i][j]:
                    # via needs a free 0.9 pad area on both layers: approximated by cell freedom
                    nd = d + 25
                    v = (ol, i, j)
                    if nd < dist.get(v, 1e18):
                        dist[v] = nd; prev[v] = u; heapq.heappush(pq, (nd, v, None))
        if not found:
            print("  !! FAILED", n, q[2]); ok = False; continue
        # backtrack
        path = [found]
        while path[-1] in prev: path.append(prev[path[-1]])
        # path from found(tree) back to src
        # stub from exact pad centre to first path cell
        # build segments
        segs = []; cur = path[0]; start = cur
        for k in range(1, len(path)):
            nxt = path[k]
            if nxt[0] != cur[0]:      # via
                add_via(n, xy((cur[1], cur[2])))
            cur = nxt
        # emit straight segments per layer
        i = 0
        while i < len(path) - 1:
            a = path[i]
            if path[i + 1][0] != a[0]:
                i += 1; continue
            j = i + 1
            dx = path[j][1] - a[1]; dy = path[j][2] - a[2]
            while j + 1 < len(path) and path[j + 1][0] == a[0] and (path[j + 1][1] - path[j][1], path[j + 1][2] - path[j][2]) == (dx, dy):
                j += 1
            add_track(n, a[0], xy((a[1], a[2])), xy((path[j][1], path[j][2])), w)
            i = j
        # stub from pad centre to snapped start cell (last in path)
        last = path[-1]
        add_track(n, last[0], q[0], xy((last[1], last[2])), w)
        for c in path: tree.add(c)
        # mark pad copper cells in tree for this pad
        for l in q[1]:
            if l in layers_allowed: addcell(l, cell(*q[0]))
        # refresh masks with newly added copper of other nets? (own net ignored) - other nets see via obst on next mask build
    return ok

# ---- manual thick copper (relay power path, 10 A class) ----
def P(ref, num):
    q = pad(ref, num).GetPosition(); return (ToMM(q.x), ToMM(q.y))
def poly(n, pts, w, layer=F):
    for a, b in zip(pts, pts[1:]): add_track(n, layer, a, b, w)
j1p, j4p = P("J1", 2), P("J4", 1)
bar_y = 80.0
poly("VBATT", [j1p, (j1p[0], bar_y)], 3.0)
poly("VBATT", [j4p, (j4p[0], bar_y)], 3.0)
poly("VBATT", [(j1p[0], bar_y), (j4p[0], bar_y)], 5.0)
bx = (j1p[0] + j4p[0]) / 2.0
poly("VBATT", [(bx, bar_y), (bx, 51.0)], 5.0)
k1c, k2c = P("K1", 1), P("K2", 1)
poly("VBATT", [(bx - 2.5, 51.0), (k2c[0], 51.0)], 5.0)
poly("VBATT", [(k1c[0], 51.0), k1c], 3.0)
poly("VBATT", [(k2c[0], 51.0), k2c], 3.0)
f1 = P("F1", 1)
poly("VBATT", [(bx, 51.0), (bx, f1[1])], 3.0)
# relay NO -> output terminals
k1no, k2no = P("K1", 3), P("K2", 3)
j51, j52 = P("J5", 1), P("J5", 2)
poly("ACC_OUT", [k1no, (k1no[0], 76.0), (j51[0], 76.0), j51], 4.0)
poly("START_OUT", [k2no, (k2no[0], 76.0), (j52[0], 76.0), j52], 4.0)

# routing order: signals first, power later
order = [
    ("CMP_OUT", [("U3", 1), ("R4", 1), ("R5", 1), ("U1A", 11)], (F, B)),
    ("VB", [("U3", 3), ("R4", 2), ("Rb3", 2), ("Rv2", 1), ("Rv1", 1)], (F, B)),
    ("TAHO_AC", [("C3", 2), ("Rb3", 1), ("U3", 2)], (F, B)),
    ("TAHO_CL", [("R1", 2), ("C3", 1), ("D4", 1)], (F, B)),
    ("TAHO_IN", [("J2", 1), ("R1", 1)], (F, B)),
    ("ZMID", [("D4", 2), ("D5", 2)], (F, B)),
    ("UNUSED_IN", [("U3", 5), ("U3", 6)], (F, B)),
    ("CONTACT", [("J2", 2), ("R6", 1)], (F, B)),
    ("D25", [("R6", 2), ("C6", 1), ("U1A", 8)], (F, B)),
    ("COIL_ACC", [("K1", 5), ("Q1", 1), ("D6", 2)], (F, B)),
    ("COIL_START", [("K2", 2), ("Q2", 1), ("D7", 2)], (F, B)),
    ("BASE_ACC", [("Rb1", 2), ("Q1", 2), ("Rp1", 1)], (F, B)),
    ("BASE_START", [("Rb2", 2), ("Q2", 2), ("Rp2", 1)], (F, B)),
    ("ACC", [("U1B", 12), ("Rb1", 1)], (F, B)),
    ("START", [("U1B", 11), ("Rb2", 1)], (F, B)),
    ("EXT1", [("U1B", 7), ("J3", 2)], (F, B)),
    ("EXT2", [("U1B", 6), ("J3", 3)], (F, B)),
    ("3V3", [("U1B", 15), ("Rv1", 2), ("R5", 2), ("U3", 8), ("C5", 1)], (F, B)),
    ("VBF", [("F1", 2), ("D3", 1), ("D1", 2)], (F,)),
    ("NODE_A", [("D1", 1), ("C2", 1), ("C1", 1), ("RM1", 1)], (F,)),
    ("VBUCK", [("RM1", 3), ("D2", 2)], (F,)),
    ("NODE_B", [("D2", 1), ("U1A", 15), ("J3", 1), ("SC1", 1), ("K1", 2), ("K2", 5), ("D6", 1), ("D7", 1)], (F, B)),
]
allok = True
for n, pl, ly in order:
    print("route", n, flush=True)
    allok &= route_net(n, pl, ly)

# ---------------- GND pours ----------------
def zone(layer):
    z = pcbnew.ZONE(board); z.SetLayer(layer); z.SetNet(net("GND"))
    z.SetLocalClearance(FromMM(0.3)); z.SetMinThickness(FromMM(0.3))
    z.SetPadConnection(pcbnew.ZONE_CONNECTION_THERMAL)
    z.SetThermalReliefGap(FromMM(0.4)); z.SetThermalReliefSpokeWidth(FromMM(0.6))
    o = z.Outline(); o.NewOutline()
    for (x, y) in [(0.5, 0.5), (BW - 0.5, 0.5), (BW - 0.5, BH - 0.5), (0.5, BH - 0.5)]:
        o.Append(FromMM(x), FromMM(y))
    board.Add(z)
zone(F); zone(B)
pcbnew.ZONE_FILLER(board).Fill(board.Zones())

# ---------------- silk labels ----------------
def text(s, x, y, size=1.0):
    t = pcbnew.PCB_TEXT(board); t.SetText(s); t.SetPosition(VECTOR2I(FromMM(x), FromMM(y)))
    t.SetLayer(pcbnew.F_SilkS); t.SetTextSize(VECTOR2I(FromMM(size), FromMM(size)))
    board.Add(t)
text("BATT- BATT+", 13.5, 90.6, 0.8); text("CHG+ CHG-", 25.5, 90.6, 0.8); text("ACC  START", 37.5, 90.6, 0.8)
text("TAHO  REMOTE1  REMOTE2", 77, 90.6, 0.8)
text("RM20S", 54, 14, 0.8)
text("J3 SPARE", 104.5, 29.8, 0.8); text("5V D18 D19 GND", 104.5, 31.6, 0.8)
text("Pramac autostart v3", 26, 3.4, 1.0)
text("K1 ACC", 33, 77.2, 0.8); text("K2 START", 63, 77.2, 0.8)
for r in ("K1","K2","J5","Q1","Q2","Rb1","Rb2","Rp1","Rp2","D6","D7","RM1","Rv1","Rv2","F1","C1","C2","D1","D2","D3","H1","H2","H3","H4","J1","J2","J3","J4","P1","P2","SC1","R1","R4","R5","R6","Rb1","Rb2","Rb3","C3","C5","C6","D4","D5","U3"):
    if r in FP: FP[r].Reference().SetVisible(False)
for fp in FP.values(): fp.Value().SetVisible(False)
pcbnew.SaveBoard(OUT, board)
print("saved", OUT, "all routed:", allok)
