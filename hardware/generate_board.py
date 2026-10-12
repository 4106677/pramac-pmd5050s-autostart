#!/usr/bin/env python3
"""Pramac PMD5050S carrier board generator (KiCad pcbnew API). Run with KiCad's python."""
import heapq, math, sys
import pcbnew
from pcbnew import VECTOR2I, FromMM, ToMM

LIB = "/Applications/KiCad/KiCad.app/Contents/SharedSupport/footprints/"
OUT = sys.argv[1] if len(sys.argv) > 1 else "pramac_carrier.kicad_pcb"
BW, BH = 93.2, 82.0
G = 0.25           # router grid, mm
CLR = 0.2         # routing clearance (DRC min is 0.2)
EDGE = 0.8         # keep tracks away from board edge

board = pcbnew.BOARD()
F, B = pcbnew.F_Cu, pcbnew.B_Cu
ds = board.GetDesignSettings()
nc = ds.m_NetSettings.GetDefaultNetclass()
nc.SetClearance(FromMM(0.2)); nc.SetTrackWidth(FromMM(0.3))
nc.SetViaDiameter(FromMM(0.9)); nc.SetViaDrill(FromMM(0.5))
ds.m_MinThroughDrill = FromMM(0.3)
ds.m_MinResolvedSpokes = 1

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
for i, (x, y) in enumerate([(4, 37), (47.5, 76.5), (72.5, 75)], 1):
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

TY = 72
place("J1", *TB2, 6, TY, value="BATT- / BATT+")
place("J4", *TB2, 18, TY, value="CHARGER +12V / GND")
place("J5", *TB2, 30, TY, value="ACC OUT / START OUT (relay NO)")
place("J6", *TB2, 60, TY, value="CONTACTOR (relay K3 dry COM/NO, 230V)")
place("J2", *TB3, 79.5, TY, value="TAHO / REMOTE")
# relays (rot 270: COM on top, contacts at the bottom)
YC = 44
place("K1", *RELAY, 27.5, YC, 270, value="SRD-05VDC-SL-A ACC")
place("K2", *RELAY, 45.5, YC, 270, value="SRD-05VDC-SL-A START")
place("K3", *RELAY, 63.5, 62.5, 90, value="SRD-05VDC-SL-A CONTACTOR")
# top-left: caps and power parts (tall parts live here, outside the ESP32 module footprint)
place("C1", "Capacitor_THT", "CP_Radial_D18.0mm_P7.50mm", 9, 13, value="4700u 25V")
place("C2", "Capacitor_THT", "CP_Radial_D18.0mm_P7.50mm", 29, 13, value="4700u 25V")
place("D3", *D15V, 3.5, 29.5, value="P6KE36A (P6KE20A recommended)")
place("D1", *D201V, 21, 29.5, 180, value="1N5821")
place("D2", *D201V, 32, 29.5, 180, value="1N5821")
place("RM1", *HDR3, 37, 26.5, value="Favotek RM20S-050 SIP-3: 1 +VIN, 2 GND, 3 +VOUT")
for _p in FP["RM1"].Pads():            # datasheet: pitch 2.54, hole 1.2
    _p.SetSize(VECTOR2I(FromMM(2.0), FromMM(2.0))); _p.SetDrillSize(VECTOR2I(FromMM(1.2), FromMM(1.2)))
_r = pcbnew.PCB_SHAPE(board); _r.SetShape(pcbnew.SHAPE_T_RECT); _r.SetLayer(pcbnew.F_SilkS); _r.SetWidth(FromMM(0.15))
_r.SetStart(VECTOR2I(FromMM(37 - 2.15), FromMM(29.04 - 5.75))); _r.SetEnd(VECTOR2I(FromMM(37 + 6.85), FromMM(29.04 + 5.75)))
board.Add(_r)
place("F1", "Fuse", "Fuse_Littelfuse_372_D8.50mm", 6.5, 50, 90, value="KLS5-102-5RT-020H 2A slow")
# ESP32 30-pin DevKit V1, rotated 90 deg: antenna left, USB right (USB hangs over the right edge)
place("U1A", "Connector_PinSocket_2.54mm", "PinSocket_1x15_P2.54mm_Vertical", 53, 32.4, 90, value="ESP32 bottom row")
place("U1B", "Connector_PinSocket_2.54mm", "PinSocket_1x15_P2.54mm_Vertical", 53, 7.0, 90, value="ESP32 top row")
# low parts under the ESP32 module: TAHO conditioning and relay drivers
# relay drivers K1/K2 under the ESP32 module (low parts)
place("Q2", *TO92, 62, 12.6, value="BC337")
place("Rb2", *RV, 67.5, 12.6, value="1k")
place("Rp2", *RV, 73.5, 12.6, value="10k")
place("D7", *D35V, 79.5, 12.6, value="1N4148")
place("Q1", *TO92, 62, 18.2, value="BC337")
place("Rb1", *RV, 67.5, 18.2, value="1k")
place("Rp1", *RV, 73.5, 18.2, value="10k")
place("D6", *D35V, 79.5, 18.2, value="1N4148")
# K3 driver in the free bottom-centre area
place("Q3", *TO92, 44, 65.8, value="BC337")
place("Rg3", *RV, 49.5, 65.8, value="1k")
place("Rp3", *RV, 49.5, 69.3, value="10k")
place("D8", *D35V, 44, 69.3, value="1N4148")
# TAHO conditioning in the region below the ESP32 module / right of the relays
place("U3", "Package_DIP", "DIP-8_W7.62mm", 80, 38.5, value="LM393 (soldered, no socket)")
place("Rb3", *RV, 66.5, 38.6, value="10k")
place("Rv2", *RV, 72.5, 38.6, value="10k")
place("Rv1", *RV, 72.5, 42, value="10k")
place("R4", *RV, 66.5, 42, value="100k")
place("R5", *RV, 80, 49.6, value="4.7k")
place("R6", *RV, 80, 53.3, value="1k")
place("C5", "Capacitor_SMD", "C_0805_2012Metric", 77.3, 40.5, 90, value="100n")
place("C6", "Capacitor_SMD", "C_0805_2012Metric", 72, 28.8, 90, value="100n")
place("R1", *RV, 79.6, 56.5, value="22k")
place("D4", *D35V, 79.6, 61.2, value="BZX55C5V1")
place("D5", *D35V, 87.9, 61.2, 180, value="BZX55C5V1")
# right strip below the module (tall parts allowed)
place("SC1", *HDR2, 56, 38, value="Supercap 1F 5.5V +/-")
place("C3", "Capacitor_THT", "CP_Radial_D5.0mm_P2.00mm", 60.8, 39.8, value="10u 16V NP")
place("J3", "Connector_PinHeader_2.54mm", "PinHeader_1x04_P2.54mm_Vertical", 89.8, 50.5, value="Spare relay module 5V/IN1(D27)/IN2(D13)/GND")

# DG128-5.0 datasheet: pitch 5.0, drill 1.4 mm
for _r in ("J1", "J4", "J5", "J2", "J6"):
    for _p in FP[_r].Pads():
        _p.SetDrillSize(VECTOR2I(FromMM(1.4), FromMM(1.4)))
        _ps = 2.4 if _r == 'J6' else 2.6
        _p.SetSize(VECTOR2I(FromMM(_ps), FromMM(_ps)))

# ---------------- netlist ----------------
for ref, n in [("J1", {1: "GND", 2: "VBATT"}), ("J4", {1: "VBATT", 2: "GND"}),
               ("F1", {1: "VBATT", 2: "VBF"}),
               ("D3", {1: "VBF", 2: "GND"}), ("D1", {2: "VBF", 1: "NODE_A"}),
               ("C1", {1: "NODE_A", 2: "GND"}), ("C2", {1: "NODE_A", 2: "GND"}),
               ("RM1", {1: "NODE_A", 2: "GND", 3: "VBUCK"}),
               ("D2", {2: "VBUCK", 1: "NODE_B"}),
               ("SC1", {1: "NODE_B", 2: "GND"}),
               ("J3", {1: "NODE_B", 2: "EXT1", 3: "EXT2", 4: "GND"}),
               ("K1", {1: "VBATT", 2: "NODE_B", 3: "ACC_OUT", 5: "COIL_ACC"}),
               ("K2", {1: "VBATT", 5: "NODE_B", 3: "START_OUT", 2: "COIL_START"}),
               ("K3", {1: "CT_COM", 3: "CT_NO", 5: "COIL_CONT", 2: "NODE_B"}), ("J6", {1: "CT_COM", 2: "CT_NO"}),
               ("J5", {1: "ACC_OUT", 2: "START_OUT"}),
               ("Q1", {1: "COIL_ACC", 2: "BASE_ACC", 3: "GND"}), ("Rb1", {1: "ACC", 2: "BASE_ACC"}), ("Rp1", {1: "BASE_ACC", 2: "GND"}), ("D6", {1: "NODE_B", 2: "COIL_ACC"}),
               ("Q2", {1: "COIL_START", 2: "BASE_START", 3: "GND"}), ("Rb2", {1: "START", 2: "BASE_START"}), ("Rp2", {1: "BASE_START", 2: "GND"}), ("D7", {1: "NODE_B", 2: "COIL_START"}),
               ("Q3", {1: "COIL_CONT", 2: "BASE_CONT", 3: "GND"}), ("Rg3", {1: "CONT", 2: "BASE_CONT"}), ("Rp3", {1: "BASE_CONT", 2: "GND"}), ("D8", {1: "NODE_B", 2: "COIL_CONT"}),
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
               ("U1A", {8: "D25", 9: "CONT", 10: "EXT1", 11: "CMP_OUT", 13: "EXT2", 14: "GND", 15: "NODE_B"}),
               ("U1B", {11: "START", 12: "ACC", 15: "3V3"}),   # pin 14 (GND) is tied to U1A.14 inside the module
               ]:
    for k, v in n.items():
        assign(ref, k, v)

# ---------------- router ----------------
NX, NY = int(BW / G) + 1, int(BH / G) + 1
POWER = {"VBF", "NODE_A", "NODE_B", "VBUCK"}
WIDTH = {n: 1.5 for n in POWER}
WIDTH["NODE_B"] = 1.0; WIDTH["VBF"] = 1.0

DEFW = 0.3
obst = {F: [], B: []}     # (xmin,ymin,xmax,ymax,netname)
MAINS = {'CT_COM', 'CT_NO'}
EXTRA = 2.6   # mains clearance 2.5 mm instead of 0.25

def pad_layers(p):
    ls = []
    if p.IsOnLayer(F): ls.append(F)
    if p.IsOnLayer(B): ls.append(B)
    return ls

for fp in FP.values():
    for p in fp.Pads():
        bb = p.GetBoundingBox()
        _e = EXTRA if (p.GetNetname() in MAINS) else 0
        r = (ToMM(bb.GetLeft()) - _e, ToMM(bb.GetTop()) - _e, ToMM(bb.GetRight()) + _e, ToMM(bb.GetBottom()) + _e, p.GetNetname() or "")
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
    h = w / 2 + (EXTRA if n in MAINS else 0)
    obst[layer].append((min(a[0], b[0]) - h, min(a[1], b[1]) - h, max(a[0], b[0]) + h, max(a[1], b[1]) + h, n))

def add_via(n, p):
    v = pcbnew.PCB_VIA(board)
    v.SetPosition(VECTOR2I(FromMM(p[0]), FromMM(p[1])))
    v.SetWidth(FromMM(0.8)); v.SetDrill(FromMM(0.4)); v.SetViaType(pcbnew.VIATYPE_THROUGH)
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

# ESP32 antenna keep-out (module overhangs the left end of the sockets): no copper on any layer
ANT = (45.6, 3.4, 52.0, 36.6)
for _l in (F, B): obst[_l].append((ANT[0], ANT[1], ANT[2], ANT[3], "#antenna"))
# ---- manual thick copper (relay power path, 10 A class) ----
def P(ref, num):
    q = pad(ref, num).GetPosition(); return (ToMM(q.x), ToMM(q.y))
def poly(n, pts, w, layer=F):
    for a, b in zip(pts, pts[1:]): add_track(n, layer, a, b, w)
j1p, j4p = P("J1", 2), P("J4", 1)
bar_y = TY - 3.0
BUS_Y = YC - 4.0
poly("VBATT", [j1p, (j1p[0], bar_y)], 3.0)
poly("VBATT", [j4p, (j4p[0], bar_y)], 3.0)
poly("VBATT", [(j1p[0], bar_y), (j4p[0], bar_y)], 4.0)
bx = (j1p[0] + j4p[0]) / 2.0
poly("VBATT", [(bx, bar_y), (bx, BUS_Y)], 5.0)
k1c, k2c = P("K1", 1), P("K2", 1)
poly("VBATT", [(bx - 2.5, BUS_Y), (k2c[0], BUS_Y)], 5.0)
poly("VBATT", [(k1c[0], BUS_Y), k1c], 3.0)
poly("VBATT", [(k2c[0], BUS_Y), k2c], 3.0)
f1 = P("F1", 1)
poly("VBATT", [(bx, f1[1]), f1], 1.5)
poly("VBATT", [(bx, BUS_Y), (bx, f1[1])], 3.0)
# relay NO -> output terminals
k1no, k2no = P("K1", 3), P("K2", 3)
j51, j52 = P("J5", 1), P("J5", 2)
HY = YC + 19.5
poly("ACC_OUT", [k1no, (k1no[0], HY), (j51[0], HY), j51], 4.0)
poly("START_OUT", [k2no, (k2no[0], HY), (j52[0], HY), j52], 4.0)
# contactor relay K3: dry COM/NO to J6 (230 V class, 2.5 mm clearance)
k3c, k3n = P("K3", 1), P("K3", 3)
j61, j62 = P("J6", 1), P("J6", 2)
poly("CT_COM", [k3c, (k3c[0], TY - 6.5), (j61[0], TY - 6.5), j61], 1.5)
poly("CT_NO", [k3n, (74.2, k3n[1]), (74.2, TY - 2.0), (j62[0], TY - 2.0), j62], 1.5)

# routing order: signals first, power later
order = [
    ("VBF", [("F1", 2), ("D3", 1), ("D1", 2)], (F, B)),
    ("NODE_A", [("D1", 1), ("C2", 1), ("C1", 1), ("RM1", 1)], (F, B)),
    ("VBUCK", [("RM1", 3), ("D2", 2)], (F, B)),
    ("NODE_B", [("D2", 1), ("U1A", 15), ("J3", 1), ("SC1", 1), ("K1", 2), ("K2", 5), ("K3", 2), ("D6", 1), ("D7", 1), ("D8", 1)], (F, B)),
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
    ("COIL_CONT", [("K3", 5), ("Q3", 1), ("D8", 2)], (F, B)),
    ("BASE_ACC", [("Rb1", 2), ("Q1", 2), ("Rp1", 1)], (F, B)),
    ("BASE_START", [("Rb2", 2), ("Q2", 2), ("Rp2", 1)], (F, B)),
    ("BASE_CONT", [("Rg3", 2), ("Q3", 2), ("Rp3", 1)], (F, B)),
    ("ACC", [("U1B", 12), ("Rb1", 1)], (F, B)),
    ("START", [("U1B", 11), ("Rb2", 1)], (F, B)),
    ("CONT", [("U1A", 9), ("Rg3", 1)], (F, B)),
    ("EXT1", [("U1A", 10), ("J3", 2)], (F, B)),
    ("GND", [("U1A", 14), ("C6", 2)], (F, B)),
    ("EXT2", [("U1A", 13), ("J3", 3)], (F, B)),
    ("3V3", [("U1B", 15), ("Rv1", 2), ("R5", 2), ("U3", 8), ("C5", 1)], (F, B)),
]
import os, random
_seed = os.environ.get("ORDER_SEED")
if _seed:
    _pw = [o for o in order if o[0] in ("VBF", "NODE_A", "VBUCK", "NODE_B")]
    _sg = [o for o in order if o[0] not in ("VBF", "NODE_A", "VBUCK", "NODE_B")]
    random.Random(int(_seed)).shuffle(_sg)
    order = _pw + [("GND", [("U3", 4), ("C5", 2)], (F, B))] + _sg
allok = True
for n, pl, ly in order:
    print("route", n, flush=True)
    allok &= route_net(n, pl, ly)

# ---------------- GND pours ----------------
def zone(layer):
    z = pcbnew.ZONE(board); z.SetLayer(layer); z.SetNet(net("GND"))
    z.SetLocalClearance(FromMM(0.3)); z.SetMinThickness(FromMM(0.3))
    z.SetPadConnection(pcbnew.ZONE_CONNECTION_THERMAL)
    z.SetIslandRemovalMode(pcbnew.ISLAND_REMOVAL_MODE_ALWAYS)
    z.SetThermalReliefGap(FromMM(0.4)); z.SetThermalReliefSpokeWidth(FromMM(0.6))
    o = z.Outline(); o.NewOutline()
    for (x, y) in [(0.5, 0.5), (BW - 0.5, 0.5), (BW - 0.5, BH - 0.5), (0.5, BH - 0.5)]:
        o.Append(FromMM(x), FromMM(y))
    board.Add(z)
# GND stitching vias (join F.Cu/B.Cu pour fragments)
_mF = mask(F, "#stitch", 0.9); _mB = mask(B, "#stitch", 0.9)
_y = 3.0
while _y < BH - 3:
    _x = 3.0
    while _x < BW - 3:
        _c = cell(_x, _y)
        if not _mF[_c[0]][_c[1]] and not _mB[_c[0]][_c[1]]:
            add_via("GND", xy(_c))
            for _dx in range(-8, 9):
                for _dy in range(-8, 9):
                    if 0 <= _c[0] + _dx < NX and 0 <= _c[1] + _dy < NY:
                        _mF[_c[0] + _dx][_c[1] + _dy] = 1; _mB[_c[0] + _dx][_c[1] + _dy] = 1
        _x += 5.0
    _y += 5.0
def keepout(layer, x0, y0, x1, y1):
    z = pcbnew.ZONE(board); z.SetLayer(layer); z.SetIsRuleArea(True)
    z.SetDoNotAllowZoneFills(True); z.SetDoNotAllowTracks(False); z.SetDoNotAllowVias(False); z.SetDoNotAllowPads(False); z.SetDoNotAllowFootprints(False)
    o = z.Outline(); o.NewOutline()
    for (x, y) in [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]: o.Append(FromMM(x), FromMM(y))
    board.Add(z)
for t in board.GetTracks():
    if t.GetClass() == "PCB_TRACK" and t.GetNetname() in MAINS:
        h = ToMM(t.GetWidth()) / 2 + 2.6
        a_, b_ = t.GetStart(), t.GetEnd()
        x0 = min(ToMM(a_.x), ToMM(b_.x)) - h; x1 = max(ToMM(a_.x), ToMM(b_.x)) + h
        y0 = min(ToMM(a_.y), ToMM(b_.y)) - h; y1 = max(ToMM(a_.y), ToMM(b_.y)) + h
        for l in (F, B): keepout(l, x0, y0, x1, y1)
for ref_ in ("K3", "J6"):
    for p_ in FP[ref_].Pads():
        if p_.GetNetname() in MAINS:
            c_ = p_.GetPosition()
            for l in (F, B): keepout(l, ToMM(c_.x) - 4.1, ToMM(c_.y) - 4.1, ToMM(c_.x) + 4.1, ToMM(c_.y) + 4.1)
def ant_zone(layer):
    z = pcbnew.ZONE(board); z.SetLayer(layer); z.SetIsRuleArea(True)
    z.SetDoNotAllowZoneFills(True); z.SetDoNotAllowTracks(True); z.SetDoNotAllowVias(True); z.SetDoNotAllowPads(False); z.SetDoNotAllowFootprints(False)
    o = z.Outline(); o.NewOutline()
    for (x, y) in [(ANT[0], ANT[1]), (ANT[2], ANT[1]), (ANT[2], ANT[3]), (ANT[0], ANT[3])]: o.Append(FromMM(x), FromMM(y))
    board.Add(z)
ant_zone(F); ant_zone(B)
zone(F); zone(B)
pcbnew.ZONE_FILLER(board).Fill(board.Zones())

# ---------------- silk ----------------
import re, math
def text(s_, x, y, size=1.0, layer=pcbnew.F_SilkS, mirror=False, thick=0.15):
    t = pcbnew.PCB_TEXT(board); t.SetText(s_); t.SetPosition(VECTOR2I(FromMM(x), FromMM(y)))
    t.SetLayer(layer); t.SetTextSize(VECTOR2I(FromMM(size), FromMM(size))); t.SetTextThickness(FromMM(thick))
    if mirror: t.SetMirrored(True)
    board.Add(t)
def sline(a, b, layer=pcbnew.F_SilkS, w=0.15):
    l = pcbnew.PCB_SHAPE(board); l.SetShape(pcbnew.SHAPE_T_SEGMENT); l.SetLayer(layer); l.SetWidth(FromMM(w))
    l.SetStart(VECTOR2I(FromMM(a[0]), FromMM(a[1]))); l.SetEnd(VECTOR2I(FromMM(b[0]), FromMM(b[1]))); board.Add(l)

# terminal labels: one per pin, centred under the pin; two-pin functions get a bracket
LY = TY + 8.0
pinx = lambda ref, k: ToMM(pad(ref, k).GetPosition().x)
for ref, k, lab in [("J1", 1, "BATT-"), ("J1", 2, "BATT+"), ("J4", 1, "CHG+"), ("J4", 2, "CHG-"),
                    ("J5", 1, "ACC"), ("J5", 2, "START"), ("J2", 1, "TAHO")]:
    text(lab, pinx(ref, k), LY, 1.0)
for ref, a, b, lab in [("J2", 2, 3, "REMOTE"), ("J6", 1, 2, "CONTACTOR")]:
    xa, xb = pinx(ref, a), pinx(ref, b)
    sline((xa - 1.2, LY - 1.6), (xb + 1.2, LY - 1.6)); sline((xa - 1.2, LY - 1.6), (xa - 1.2, LY - 2.4)); sline((xb + 1.2, LY - 1.6), (xb + 1.2, LY - 2.4))
    text(lab, (xa + xb) / 2.0, LY, 1.0)
text("K1 ACC", 27.5, YC - 4.5, 0.9); text("K2 START", 45.5, YC - 4.5, 0.9)
text("J3 SPARE", 89.5, 47.8, 0.8)
for k, lab in enumerate(["5V", "D27", "D13", "GND"]): text(lab, 86.3, 50.5 + 2.54 * k, 0.8)
text("Pramac autostart v5", 24, 2.0, 0.9); text("ANTENNA", 48.8, 17.0, 0.8); text("KEEP-OUT", 48.8, 19.2, 0.8)

# ---- back side: QR code (light modules printed, dark = bare mask), GitHub mark, nick ----
BS = pcbnew.B_SilkS
rows = [l.strip() for l in open("qr.txt") if l.strip()]
core = [r_[1:-1] for r_ in rows[1:-1]]          # drop 1-module border of CoreImage output
NQ = len(core); BORDER = 2; TOT = NQ + 2 * BORDER; M = 0.45
qx0, qy0 = 3.2, 53.5
def dark(c, r_):
    c -= BORDER; r_ -= BORDER
    return 0 <= c < NQ and 0 <= r_ < NQ and core[r_][c] == "1"
for r_ in range(TOT):
    c = 0
    while c < TOT:
        if dark(c, r_): c += 1; continue
        c0 = c
        while c < TOT and not dark(c, r_): c += 1
        c1 = c - 1
        x_a = qx0 + (TOT - 1 - c1) * M; x_b = qx0 + (TOT - c0) * M          # mirrored for the back side
        y_a = qy0 + r_ * M; y_b = qy0 + (r_ + 1) * M
        rc = pcbnew.PCB_SHAPE(board); rc.SetShape(pcbnew.SHAPE_T_RECT); rc.SetLayer(BS); rc.SetWidth(0); rc.SetFilled(True)
        rc.SetStart(VECTOR2I(FromMM(x_a), FromMM(y_a))); rc.SetEnd(VECTOR2I(FromMM(x_b), FromMM(y_b))); board.Add(rc)

LOGO = "M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27.68 0 1.36.09 2 .27 1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.013 8.013 0 0016 8c0-4.42-3.58-8-8-8z"
def logo_points(d):
    toks = re.findall(r"[MCcAz]|-?\d*\.?\d+", d)
    pts = []; i = 0; cur = (0.0, 0.0); cmd = None
    def num():
        nonlocal i; v = float(toks[i]); i += 1; return v
    while i < len(toks):
        if re.match(r"[MCcAz]", toks[i]): cmd = toks[i]; i += 1
        if cmd == "M": cur = (num(), num()); pts.append(cur)
        elif cmd in ("C", "c"):
            if cmd == "C": c1 = (num(), num()); c2 = (num(), num()); e = (num(), num())
            else:
                c1 = (cur[0] + num(), cur[1] + num()); c2 = (cur[0] + num(), cur[1] + num()); e = (cur[0] + num(), cur[1] + num())
            for t in [k / 8.0 for k in range(1, 9)]:
                u = 1 - t
                pts.append((u**3*cur[0] + 3*u*u*t*c1[0] + 3*u*t*t*c2[0] + t**3*e[0], u**3*cur[1] + 3*u*u*t*c1[1] + 3*u*t*t*c2[1] + t**3*e[1]))
            cur = e
        elif cmd == "A":
            rx = num(); ry = num(); rot = num(); ft = toks[i]; i += 1
            if len(ft) > 2: ex = float(ft[2:])
            elif len(ft) == 2: ex = num()
            else: i += 1; ex = num()
            ey = num()
            a0 = math.atan2(cur[1] - 8, cur[0] - 8); a1 = math.atan2(ey - 8, ex - 8)
            if a1 > a0: a1 -= 2 * math.pi
            for k in range(1, 13): pts.append((8 + rx * math.cos(a0 + (a1 - a0) * k / 12.0), 8 + rx * math.sin(a0 + (a1 - a0) * k / 12.0)))
            cur = (ex, ey)
        elif cmd == "z": break
    return pts
lp = logo_points(LOGO)
LS = 5.5 / 16.0; lx0, ly0 = 3.6, 4.2
poly = pcbnew.PCB_SHAPE(board); poly.SetShape(pcbnew.SHAPE_T_POLY); poly.SetLayer(BS); poly.SetFilled(True); poly.SetWidth(0)
poly.SetPolyPoints([VECTOR2I(FromMM(lx0 + (16 - px) * LS), FromMM(ly0 + py * LS)) for px, py in lp]); board.Add(poly)
text("4106677", 17.0, 7.0, 1.4, BS, True, 0.22)

for r in ("K1","K2","K3","J5","J6","Q1","Q2","Q3","Rb1","Rb2","Rg3","Rp1","Rp2","Rp3","D6","D7","D8","RM1","Rv1","Rv2","F1","C1","C2","D1","D2","D3","H1","H2","H3","H4","J1","J2","J3","J4","SC1","R1","R4","R5","R6","Rb3","C3","C5","C6","D4","D5","U3"):
    if r in FP: FP[r].Reference().SetVisible(False)
for fp in FP.values():
    fp.Value().SetVisible(False); fp.Reference().SetVisible(False)
pcbnew.SaveBoard(OUT, board)
open(OUT.replace(".kicad_pcb", ".kicad_dru"), "w").write("""(version 1)
(rule "mains_clearance"
  (condition "A.NetName == 'CT_COM' || A.NetName == 'CT_NO' || B.NetName == 'CT_COM' || B.NetName == 'CT_NO'")
  (constraint clearance (min 2.5mm)))
""")
print("saved", OUT, "all routed:", allok)
