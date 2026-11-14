#!/usr/bin/env python3
"""v6.1 from the routed v6.0 board: only the TAHO input changes, the rest of the routing is kept as is.

Run with KiCad's python (see gen_pcb.py):
  patch_v61.py prep <v6.0 board>  -> new netlist + parts R38/C33/D25, TAHO_AC/VB tracks removed, GND vias for the
                                     new GND pads, everything else locked; writes pramac_v6.kicad_pcb and pramac_v6.dsn
  (Freerouting: pramac_v6.dsn -> pramac_v6.ses, routes only the unrouted TAHO connections)
  patch_v61.py finish             -> imports pramac_v6.ses, GND pours, saves. Then: gen_pcb.py export
"""
import math, os, sys
import pcbnew
from pcbnew import VECTOR2I, FromMM, ToMM

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import gen_pcb as g

NEW_PARTS = ("R38", "C33", "D25")
REROUTE = ("TAHO_AC", "VB", "TAHO_F")
GND_VIA_REFS = ("R31", "C33", "D25", "U5")
KEEP = []


def rules(board):
    """The v6.0 design rules (gen_pcb.build): a board loaded from elsewhere would get KiCad defaults."""
    ds = board.GetDesignSettings()
    nc = ds.m_NetSettings.GetDefaultNetclass()
    nc.SetClearance(FromMM(0.15)); nc.SetTrackWidth(FromMM(0.25))
    nc.SetViaDiameter(FromMM(0.6)); nc.SetViaDrill(FromMM(0.3))
    ds.m_MinThroughDrill = FromMM(0.3)
    ds.m_TrackMinWidth = FromMM(0.15)
    ds.m_MinResolvedSpokes = 1
    ds.m_MinClearance = FromMM(0.15)


def prep(src):
    comps, pins = g.load_netlist()
    board = pcbnew.LoadBoard(src)
    rules(board)
    KEEP.extend(z for z in board.Zones() if not z.GetIsRuleArea())   # keep Python refs: pcbnew crashes otherwise
    for z in KEEP:
        board.Remove(z)
    nets = {}

    def net(name):
        ni = board.FindNet(name)
        if ni is None:
            ni = pcbnew.NETINFO_ITEM(board, name); board.Add(ni)
        nets[name] = ni
        return ni

    fps = {fp.GetReference(): fp for fp in board.GetFootprints()}
    for ref in NEW_PARTS:
        fpid, val, fields = comps[ref]
        lib, name = fpid.split(":")
        fp = pcbnew.FootprintLoad(g.LIB + lib + ".pretty", name)
        fp.SetReference(ref); fp.SetValue(val)
        x, y, rot = g.PLACE[ref][:3]
        fp.SetPosition(VECTOR2I(FromMM(x), FromMM(y)))
        if rot:
            fp.SetOrientationDegrees(rot)
        board.Add(fp); fps[ref] = fp
        if ref in ("R38", "C33"):        # no room for the reference next to D20/D21
            fp.Reference().SetVisible(False)
    for ref, fp in fps.items():
        if ref in comps:
            fp.SetValue(comps[ref][1])
        for p in fp.Pads():
            n = pins.get((ref, p.GetNumber()))
            if n and not n.startswith("unconnected"):
                p.SetNet(net(n))
    for t in list(board.GetTracks()):
        if t.GetNetname() in REROUTE:
            board.Remove(t); KEEP.append(t)
    net("GND")
    # a via into the bottom pour next to each new GND pad (GND is not given to Freerouting)
    obst = []
    for fp in fps.values():
        for p in fp.Pads():
            q = p.GetPosition(); bb = p.GetBoundingBox()
            obst.append((ToMM(q.x), ToMM(q.y), max(ToMM(bb.GetWidth()), ToMM(bb.GetHeight())) / 2, p.GetNetname()))
    for t in board.GetTracks():
        a_, b_ = t.GetStart(), t.GetEnd()
        L = math.hypot(ToMM(b_.x) - ToMM(a_.x), ToMM(b_.y) - ToMM(a_.y))
        n_ = max(1, int(L / 0.1))
        w_ = ToMM(t.GetWidth(pcbnew.F_Cu) if t.GetClass() == "PCB_VIA" else t.GetWidth()) / 2
        for k in range(n_ + 1):
            obst.append((ToMM(a_.x) + (ToMM(b_.x) - ToMM(a_.x)) * k / n_, ToMM(a_.y) + (ToMM(b_.y) - ToMM(a_.y)) * k / n_,
                         w_, t.GetNetname()))
    for ref in GND_VIA_REFS:
        for p in fps[ref].Pads():
            if p.GetNetname() != "GND":
                continue
            q = p.GetPosition(); x0, y0 = ToMM(q.x), ToMM(q.y)
            done = False
            for dist in (1.3, 1.7, 2.1, 2.6):
                for k in range(16):
                    a = k * math.pi / 8
                    x, y = x0 + dist * math.cos(a), y0 + dist * math.sin(a)
                    if all(n == "GND" or math.hypot(ox - x, oy - y) >= r + 0.3 + 0.25 for ox, oy, r, n in obst):
                        g.via(board, nets, "GND", (x, y), 0.6, 0.3)
                        g.track(board, nets, "GND", g.F, [(x0, y0), (x, y)], 0.4)
                        obst.append((x, y, 0.3, "GND"))
                        print("GND via", ref, p.GetNumber(), round(x, 2), round(y, 2))
                        done = True
                        break
                if done:
                    break
            if not done:
                print("NO GND via for", ref, p.GetNumber())
    for t in board.GetTracks():
        t.SetLocked(True)
    pcbnew.SaveBoard(g.PCB, board)
    g.export_dsn(board, g.PCB.replace(".kicad_pcb", ".dsn"))
    print("saved", g.PCB, "+ dsn")


def finish():
    board = pcbnew.LoadBoard(g.PCB)
    rules(board)
    ses = g.PCB.replace(".kicad_pcb", ".ses")
    print("import ses:", pcbnew.ImportSpecctraSES(board, ses))
    nets = {"GND": board.FindNet("GND")}
    g.finish(board, nets)
    pcbnew.ZONE_FILLER(board).Fill(board.Zones())
    # Freerouting leftovers on the re-routed nets: a via with tracks on one layer only is not needed
    layers = {}
    for t in board.GetTracks():
        if t.GetClass() == "PCB_TRACK" and t.GetNetname() in REROUTE:
            for q in (t.GetStart(), t.GetEnd()):
                layers.setdefault((q.x, q.y), set()).add(t.GetLayer())
    dead = [t for t in board.GetTracks() if t.GetClass() == "PCB_VIA" and t.GetNetname() in REROUTE
            and len(layers.get((t.GetPosition().x, t.GetPosition().y), ())) < 2]
    for t in dead:
        print("dangling via removed:", t.GetNetname(), round(ToMM(t.GetPosition().x), 2), round(ToMM(t.GetPosition().y), 2))
        board.Remove(t); KEEP.append(t)
    for t in board.GetTracks():
        t.SetLocked(False)
    pcbnew.ZONE_FILLER(board).Fill(board.Zones())
    pcbnew.SaveBoard(g.PCB, board)
    open(g.PCB.replace(".kicad_pcb", ".kicad_dru"), "w").write(g.DRU)
    print("saved", g.PCB)


if __name__ == "__main__":
    if sys.argv[1] == "prep":
        prep(sys.argv[2])
    else:
        finish()
