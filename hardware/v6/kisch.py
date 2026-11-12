"""Tiny KiCad schematic writer: symbols from the stock KiCad libraries (or generated ones), connections by labels.

Every connected pin gets a short wire stub and a local label with the net name, so the schematic needs no
wire routing and stays readable block by block. Plain Python, no KiCad API needed.
"""
import copy, math, re, uuid as _uuid

SYMLIB = "/Applications/KiCad/KiCad.app/Contents/SharedSupport/symbols/"
STUB = 2.54
SCALE = 1.0   # layout coordinates passed to Sheet methods are multiplied by this


# ---------------------------------------------------------------- s-expressions
class Q(str):
    """A quoted string atom."""


def parse(text):
    tok = re.compile(r'\(|\)|"(?:[^"\\]|\\.)*"|[^\s()"]+')
    stack, cur = [], []
    for m in tok.finditer(text):
        t = m.group(0)
        if t == "(":
            stack.append(cur); cur = []
        elif t == ")":
            done = cur; cur = stack.pop(); cur.append(done)
        elif t.startswith('"'):
            cur.append(Q(t[1:-1].replace('\\"', '"').replace("\\\\", "\\")))
        else:
            cur.append(t)
    return cur[0]


def dump(node, ind=0):
    if not isinstance(node, list):
        if isinstance(node, Q):
            return '"' + node.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n") + '"'
        return str(node)
    simple = all(not isinstance(x, list) for x in node)
    if simple:
        return "(" + " ".join(dump(x) for x in node) + ")"
    out = "(" + " ".join(dump(x) for x in node if not isinstance(x, list))
    for x in node:
        if isinstance(x, list):
            out += "\n" + "\t" * (ind + 1) + dump(x, ind + 1)
    return out + "\n" + "\t" * ind + ")"


def find(node, key):
    return [x for x in node if isinstance(x, list) and x and x[0] == key]


def num(v):
    return ("%.4f" % v).rstrip("0").rstrip(".") if isinstance(v, float) else str(v)


# ---------------------------------------------------------------- library symbols
_libs = {}


def _lib(name):
    if name not in _libs:
        root = parse(open(SYMLIB + name + ".kicad_sym", encoding="utf-8").read())
        _libs[name] = {x[1]: x for x in find(root, "symbol")}
    return _libs[name]


def lib_symbol(lib_id):
    """Flattened symbol node (extends resolved), named 'Lib:Name'."""
    lib, name = lib_id.split(":")
    node = copy.deepcopy(_lib(lib)[name])
    ext = find(node, "extends")
    if ext:
        parent = lib_symbol(lib + ":" + ext[0][1])
        pname = ext[0][1]
        flat = copy.deepcopy(parent)
        props = {p[1]: p for p in find(node, "property")}
        for i, x in enumerate(flat):
            if isinstance(x, list) and x[0] == "property" and x[1] in props:
                flat[i] = props.pop(x[1])
        for p in props.values():
            flat.append(p)
        for x in flat:
            if isinstance(x, list) and x[0] == "symbol":
                x[1] = Q(x[1].replace(pname + "_", name + "_", 1))
        node = flat
    node[1] = Q(lib_id)
    return node


def pins_of(symnode, unit=1):
    """{number: (x, y, angle, name)} in symbol coordinates (Y up) for a unit (unit-0 pins included)."""
    base = symnode[1].split(":")[-1]
    res = {}
    for sub in find(symnode, "symbol"):
        m = re.match(re.escape(base) + r"_(\d+)_(\d+)$", sub[1])
        if not m or int(m.group(1)) not in (0, unit):
            continue
        for p in find(sub, "pin"):
            at = find(p, "at")[0]
            nm = find(p, "name")[0][1]
            nb = find(p, "number")[0][1]
            res[str(nb)] = (float(at[1]), float(at[2]), float(at[3]) if len(at) > 3 else 0.0, str(nm))
    return res


def custom_symbol(lib_id, left, right, width=15.24, ref="U", value=""):
    """Box symbol. left/right: lists of (number, name, type) top to bottom; None = gap."""
    name = lib_id.split(":")[1]
    n = max(len(left), len(right))
    h = (n + 1) * 2.54
    top = h / 2
    pins = []
    for side, lst in ((-1, left), (1, right)):
        for i, p in enumerate(lst):
            if p is None:
                continue
            nb, nm, tp = p
            y = top - 2.54 * (i + 1)
            x = side * (width / 2 + 2.54)
            ang = 0 if side < 0 else 180
            pins.append(["pin", tp, "line", ["at", num(x), num(round(y, 2)), str(ang)], ["length", "2.54"],
                         ["name", Q(nm), ["effects", ["font", ["size", "1.27", "1.27"]]]],
                         ["number", Q(str(nb)), ["effects", ["font", ["size", "1.27", "1.27"]]]]])
    body = ["symbol", Q(name + "_0_1"),
            ["rectangle", ["start", num(-width / 2), num(top)], ["end", num(width / 2), num(-top)],
             ["stroke", ["width", "0.254"], ["type", "default"]], ["fill", ["type", "background"]]]]
    pinsym = ["symbol", Q(name + "_1_1")] + pins
    prop = lambda k, v, y, hide=False: ["property", Q(k), Q(v), ["at", "0", num(y), "0"],
                                        ["effects", ["font", ["size", "1.27", "1.27"]]] + ([["hide", "yes"]] if hide else [])]
    return ["symbol", Q(lib_id), ["pin_names", ["offset", "1.016"]], ["exclude_from_sim", "no"], ["in_bom", "yes"],
            ["on_board", "yes"], prop("Reference", ref, top + 1.27), prop("Value", value or name, -top - 1.27),
            prop("Footprint", "", 0, True), prop("Datasheet", "", 0, True), body, pinsym]


# ---------------------------------------------------------------- schematic
class Sheet:
    def __init__(self, project, paper="A1", title="", rev=""):
        self.project = project
        self.uuid = str(_uuid.uuid4())
        self.paper, self.title, self.rev = paper, title, rev
        self.libsyms = {}
        self.items = []
        self.refs = {}
        self.parts = []     # (ref, value, footprint, lcsc, fields) for the BOM
        self.pwr_n = 0

    def _sym(self, lib_id, node=None):
        if lib_id not in self.libsyms:
            self.libsyms[lib_id] = node if node is not None else lib_symbol(lib_id)
        return self.libsyms[lib_id]

    def define(self, node):
        self.libsyms[node[1]] = node

    @staticmethod
    def _xf(x, y, rot, mirror):
        if mirror == "y":
            x = -x
        a = math.radians(rot)
        xr, yr = x * math.cos(a) - y * math.sin(a), x * math.sin(a) + y * math.cos(a)
        return xr, -yr

    def place(self, lib_id, ref, value, x, y, nets, rot=0, unit=1, footprint="", lcsc="", fields=None,
              mirror=None, hide_value=False, in_bom=True, nc=()):
        """nets: {pin number: net name}. Pins listed in nc get a no-connect flag."""
        sym = self._sym(lib_id)
        pins = pins_of(sym, unit)
        x, y = x * SCALE, y * SCALE
        x, y = round(round(x / 1.27) * 1.27, 2), round(round(y / 1.27) * 1.27, 2)   # keep pins on the 50 mil grid
        props = [("Reference", ref), ("Value", value), ("Footprint", footprint), ("Datasheet", "")]
        if lcsc:
            props.append(("LCSC", lcsc))
        for k, v in (fields or {}).items():
            props.append((k, v))
        node = ["symbol", ["lib_id", Q(lib_id)], ["at", num(x), num(y), str(rot)]]
        if mirror:
            node.append(["mirror", mirror])
        node += [["unit", str(unit)], ["exclude_from_sim", "no"], ["in_bom", "yes" if in_bom else "no"],
                 ["on_board", "yes"], ["dnp", "no"], ["uuid", Q(str(_uuid.uuid4()))]]
        # property positions: reference above, value below the symbol's pin extent
        ys = [-p[1] for p in pins.values()] or [0]
        for i, (k, v) in enumerate(props):
            hide = k not in ("Reference", "Value") or (k == "Value" and hide_value)
            py = y + (min(ys) - 2.0 if k == "Reference" else max(ys) + 2.0) if rot in (0, 180) else y
            px = x if rot in (0, 180) else x + (3.0 if k == "Reference" else -3.0)
            eff = ["effects", ["font", ["size", "1.27", "1.27"]]]
            if hide:
                eff.append(["hide", "yes"])
            node.append(["property", Q(k), Q(v), ["at", num(round(px, 2)), num(round(py, 2)), "0"], eff])
        for nb in pins:
            node.append(["pin", Q(nb), ["uuid", Q(str(_uuid.uuid4()))]])
        node.append(["instances", ["project", Q(self.project),
                                   ["path", Q("/" + self.uuid), ["reference", Q(ref)], ["unit", str(unit)]]]])
        self.items.append(node)
        for nb, (px, py, pa, pname) in pins.items():
            dx, dy = self._xf(px, py, rot, mirror)
            cx, cy = round(x + dx, 3), round(y + dy, 3)
            # pin angle (direction from the connection point to the body), in sheet orientation
            ang = pa + rot
            if mirror == "y":
                ang = 180 - ang
            ang %= 360
            if nb in nets and nets[nb]:
                self.label(nets[nb], cx, cy, (ang + 180) % 360)
            elif nb in nc:
                self.items.append(["no_connect", ["at", num(cx), num(cy)], ["uuid", Q(str(_uuid.uuid4()))]])
        if in_bom and unit == 1 and not ref.startswith("#"):
            self.parts.append((ref, value, footprint, lcsc, fields or {}))
        return node

    def label(self, net, x, y, ang):
        """Wire stub from (x, y) in direction ang, local label at its end."""
        a = math.radians(ang)
        ex, ey = round(x + STUB * math.cos(a), 3), round(y - STUB * math.sin(a), 3)
        self.items.append(["wire", ["pts", ["xy", num(x), num(y)], ["xy", num(ex), num(ey)]],
                           ["stroke", ["width", "0"], ["type", "default"]], ["uuid", Q(str(_uuid.uuid4()))]])
        lang = int(round(ang)) % 360
        just = "left" if lang in (0, 90) else "right"
        if lang in (90, 270):
            ltxt_ang = 90
            just = "left" if lang == 90 else "right"
        else:
            ltxt_ang = 0
        self.items.append(["label", Q(net), ["at", num(ex), num(ey), str(ltxt_ang)],
                           ["effects", ["font", ["size", "1.0", "1.0"]], ["justify", just, "bottom"]],
                           ["uuid", Q(str(_uuid.uuid4()))]])

    def pwr_flag(self, net, x, y):
        self.pwr_n += 1
        self.place("power:PWR_FLAG", "#FLG%02d" % self.pwr_n, "PWR_FLAG", x, y, {"1": net}, in_bom=False)

    def text(self, s, x, y, size=2.0):
        x, y = x * SCALE, y * SCALE
        self.items.append(["text", Q(s), ["exclude_from_sim", "no"], ["at", num(x), num(y), "0"],
                           ["effects", ["font", ["size", num(size), num(size)], ["bold", "yes"]], ["justify", "left", "bottom"]],
                           ["uuid", Q(str(_uuid.uuid4()))]])

    def note(self, s, x, y, size=1.27):
        x, y = x * SCALE, y * SCALE
        self.items.append(["text", Q(s), ["exclude_from_sim", "no"], ["at", num(x), num(y), "0"],
                           ["effects", ["font", ["size", num(size), num(size)]], ["justify", "left", "top"]],
                           ["uuid", Q(str(_uuid.uuid4()))]])

    def box(self, x0, y0, x1, y1):
        x0, y0, x1, y1 = x0 * SCALE, y0 * SCALE, x1 * SCALE, y1 * SCALE
        self.items.append(["rectangle", ["start", num(x0), num(y0)], ["end", num(x1), num(y1)],
                           ["stroke", ["width", "0.3"], ["type", "dash"]], ["fill", ["type", "none"]],
                           ["uuid", Q(str(_uuid.uuid4()))]])

    def save(self, path):
        root = ["kicad_sch", ["version", "20250114"], ["generator", Q("eeschema")], ["generator_version", Q("10.0")],
                ["uuid", Q(self.uuid)], ["paper", Q(self.paper)],
                ["title_block", ["title", Q(self.title)], ["rev", Q(self.rev)]],
                ["lib_symbols"] + list(self.libsyms.values())]
        root += self.items
        root += [["sheet_instances", ["path", Q("/"), ["page", Q("1")]]], ["embedded_fonts", "no"]]
        open(path, "w", encoding="utf-8").write(dump(root) + "\n")
