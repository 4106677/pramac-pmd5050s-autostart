#!/usr/bin/env python3
"""Pramac autostart board v6: schematic generator (writes pramac_v6.kicad_sch).

Blocks: 12 V input and protection, 5 V buck + supercap + 3.3 V LDO, ESP32-S3-MINI-1U (external antenna), USB-C,
three relays (ACC, START, contactor), TAHO and REMOTE inputs, battery voltage sense, 230 V input with mains
detection and a 24 V AC-DC module, lead-acid charger, DIP mode switch, LEDs, connectors.
Part numbers (LCSC) come from parts.py; footprints are KiCad library footprints matching those parts.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kisch
from parts import P

kisch.SCALE = 0.7
S = kisch.Sheet("pramac_v6", paper="A2", title="Pramac PMD5050S autostart v6", rev="6.0")


def part(key, ref, x, y, nets, rot=0, value=None, **kw):
    v, fp, lcsc, lib = P[key]
    return S.place(lib, ref, value or v, x, y, nets, rot=rot, footprint=fp, lcsc=lcsc, **kw)


def R(ref, val, x, y, a, b, rot=0, size="R0805"):
    v, fp, lcsc, lib = P[size + "_" + val]
    return S.place(lib, ref, v, x, y, {"1": a, "2": b}, rot=rot, footprint=fp, lcsc=lcsc)


def C(ref, val, x, y, a, b, rot=0):
    v, fp, lcsc, lib = P["C_" + val]
    return S.place(lib, ref, v, x, y, {"1": a, "2": b}, rot=rot, footprint=fp, lcsc=lcsc)


def block(title, x0, y0, x1, y1):
    S.box(x0, y0, x1, y1)
    S.text(title, x0 + 2, y0 + 5, 2.2)


# ======================================================================= 12 V input
block("1. Вхід 12 В: запобіжник, TVS, захист від переплутаної полярності", 15, 15, 205, 115)
part("FUSE_12V", "F1", 40, 45, {"1": "VBAT", "2": "VBF"}, rot=90)
part("TVS_12V", "D1", 60, 62, {"1": "VBF", "2": "GND"})
part("SCHOTTKY_5A", "D2", 80, 45, {"1": "VIN12", "2": "VBF"}, rot=90)
part("CAP_BULK", "C1", 100, 62, {"1": "VIN12", "2": "GND"})
C("C2", "10u_50V", 118, 62, "VIN12", "GND")
R("R1", "100k", 145, 50, "VBF", "VBAT_SENSE")
R("R2", "22k", 145, 80, "VBAT_SENSE", "GND")
C("C3", "100n", 155, 75, "VBAT_SENSE", "GND")
S.note("Шина VBAT (до запобіжника) іде на COM реле K1/K2/K4 широкою доріжкою.\n"
       "На дроті від АКБ потрібен зовнішній запобіжник ~15 А.\n"
       "VBAT_SENSE: 15,5 В -> 2,8 В на АЦП (дільник 100k/22k).", 20, 90)

# ======================================================================= 3.3 V and 5 V
block("2. Живлення: 3,3 В для ESP32 і окремі 5 В для котушок реле (обидва buck прямо від АКБ)", 215, 15, 455, 115)
part("BUCK_3V3", "U2", 255, 40, {"3": "VIN12", "2": "BUCK_EN", "4": "GND", "5": "BUCK_SW", "6": "BUCK_BST", "1": "3V3"})
R("R3", "100k", 232, 32, "VIN12", "BUCK_EN")
C("C4", "100n", 282, 28, "BUCK_BST", "BUCK_SW", rot=90)
part("IND_BUCK", "L1", 318, 40, {"1": "BUCK_SW", "2": "3V3"}, rot=90)
C("C5", "22u", 345, 48, "3V3", "GND")
C("C6", "22u", 362, 48, "3V3", "GND")
part("BUCK_5V", "U3", 255, 78, {"3": "VIN12", "2": "BUCK5_EN", "4": "GND", "5": "BUCK5_SW", "6": "BUCK5_BST", "1": "V5"})
R("R8", "100k", 232, 70, "VIN12", "BUCK5_EN")
C("C7", "100n", 282, 66, "BUCK5_BST", "BUCK5_SW", rot=90)
part("IND_BUCK", "L2", 318, 78, {"1": "BUCK5_SW", "2": "V5"}, rot=90)
C("C8", "22u", 345, 86, "V5", "GND")
C("C12", "22u", 362, 86, "V5", "GND")
C("C13", "10u_50V", 285, 98, "VIN12", "GND")
part("SCHOTTKY_3A", "D4", 395, 38, {"1": "VIN12", "2": "VBUS"}, rot=90)
S.note("Режим LDO AP6320x: коли АКБ < 5 В,\nвихід 5 В іде слідом за входом;\nSRD-05 тримається до ~2 В.\n"
       "ESP32 працює від АКБ 3,8 В.\nІоністор не потрібен.\nD4: живлення від USB.", 380, 62)

# ======================================================================= ESP32-S3
block("3. ESP32-S3-MINI-1U (зовнішня антена U.FL -> SMA на корпусі)", 465, 15, 655, 250)
esp = {"1": "GND", "2": "GND", "3": "3V3", "4": "IO0_BOOT", "45": "EN",
       "5": "VBAT_SENSE", "6": "CHG_DONE", "8": "TAHO", "9": "REMOTE", "10": "MAINS_OK", "11": "CHG_EN", "12": "CHG_STAT",
       "13": "LED_STAT", "14": "K1_DRV", "15": "K2_DRV", "16": "K3_DRV",
       "17": "DIP1", "18": "DIP2", "19": "DIP3", "20": "DIP4", "21": "EXT1", "22": "EXT2", "25": "K4_DRV",
       "23": "USB_DN", "24": "USB_DP", "39": "TXD0", "40": "RXD0"}
for n in range(42, 66):
    if n not in (44, 45):
        esp[str(n)] = "GND"
nc = [str(n) for n in (7, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 41, 44)]
part("ESP32S3", "U1", 545, 120, esp, nc=nc)
C("C9", "22u", 600, 40, "3V3", "GND")
C("C10", "100n", 615, 40, "3V3", "GND")
R("R4", "10k", 480, 40, "3V3", "EN")
C("C11", "1u", 495, 40, "EN", "GND")
part("TACT", "SW1", 480, 215, {"1": "EN", "2": "GND"}, value="RESET")
R("R5", "10k", 510, 205, "3V3", "IO0_BOOT")
part("TACT", "SW2", 525, 215, {"1": "IO0_BOOT", "2": "GND"}, value="BOOT")
part("TESTPOINT", "TP1", 575, 205, {"1": "TXD0"}, value="TXD0")
part("TESTPOINT", "TP2", 590, 205, {"1": "RXD0"}, value="RXD0")
part("TESTPOINT", "TP3", 605, 205, {"1": "GND"}, value="GND")
S.note("IO1 VBAT_SENSE (ADC1)   IO2 CHG_DONE   IO4 TAHO   IO5 REMOTE   IO6 MAINS_OK   IO7 CHG_EN   IO8 CHG_STAT\n"
       "IO9 LED   IO10/11/12 реле K1/K2/K3   IO21 реле K4 AUX   IO13-16 DIP1-4   IO17/18 резерв J7\n"
       "IO0 BOOT, EN RESET; IO3/IO45/IO46 (strapping) і IO26/33-37 не використовуються.", 470, 228)

# ======================================================================= USB-C
block("4. USB-C: прошивка і лог (вбудований USB ESP32-S3)", 665, 15, 830, 115)
part("USB_C", "J6", 690, 60, {"A4": "VBUS", "A9": "VBUS", "B4": "VBUS", "B9": "VBUS", "A1": "GND", "A12": "GND",
                               "B1": "GND", "B12": "GND", "SH": "GND", "A5": "USB_CC1", "B5": "USB_CC2",
                               "A6": "USB_DP", "B6": "USB_DP", "A7": "USB_DN", "B7": "USB_DN"}, nc=["A8", "B8"])
R("R6", "5k1", 735, 75, "USB_CC1", "GND")
R("R7", "5k1", 748, 75, "USB_CC2", "GND")
part("ESD_USB", "U4", 790, 55, {"1": "USB_DP", "6": "USB_DP", "3": "USB_DN", "4": "USB_DN", "2": "GND", "5": "VBUS"})

# ======================================================================= relays
block("5. Реле: K1 ACC, K2 START, K4 AUX (COM = VBAT), K3 контактор (сухі контакти 230 В)", 15, 125, 455, 270)
# key, driver net, COM, NO, label, refs: (Q, R gate, R pull-down, flyback D, R LED, LED)
RELAYS = [("K1", "K1_DRV", "VBAT", "ACC_OUT", "ACC", ("Q1", "R10", "R11", "D10", "R20", "D13")),
          ("K2", "K2_DRV", "VBAT", "START_OUT", "START", ("Q2", "R12", "R13", "D11", "R21", "D14")),
          ("K4", "K4_DRV", "VBAT", "AUX_OUT", "AUX", ("Q4", "R16", "R17", "D16", "R23", "D17")),
          ("K3", "K3_DRV", "CT_COM", "CT_NO", "CONTACTOR", ("Q3", "R14", "R15", "D12", "R22", "D15"))]
for i, (k, drv, com, no, lab, (q, rg, rpd, dfb, rled, led)) in enumerate(RELAYS):
    x0 = 30 + i * 105
    coil = "%s_COIL" % k
    part("RELAY", k, x0 + 70, 190, {"1": com, "3": no, "2": "V5", "5": coil}, nc=["4"])
    part("NMOS", q, x0 + 40, 215, {"1": "%s_G" % k, "2": "GND", "3": coil})
    R(rg, "100", x0 + 15, 215, drv, "%s_G" % k, rot=90)
    R(rpd, "100k", x0 + 25, 240, "%s_G" % k, "GND")
    part("DIODE_SIG", dfb, x0 + 40, 170, {"1": "V5", "2": coil})
    R(rled, "2k2", x0 + 20, 160, "V5", "%s_LED" % k)
    part("LED_RED", led, x0 + 20, 180, {"2": "%s_LED" % k, "1": coil}, value="LED " + lab)
S.note("Реле SRD-05VDC: котушка 5 В / 72 мА від окремого buck 5 В, ключ AO3400A, діод на котушці, світлодіод стану.\n"
       "Затвор притягнутий до GND (100k): поки ESP32 завантажується, реле вимкнені.", 20, 255)

# ======================================================================= inputs
block("6. Входи: TAHO (LM393), REMOTE", 465, 260, 830, 400)
R("R30", "22k", 490, 300, "TAHO_IN", "TAHO_CL", rot=90, size="R1206")
part("ZENER_5V1", "D20", 510, 320, {"1": "TAHO_CL", "2": "ZMID"})
part("ZENER_5V1", "D21", 510, 345, {"1": "GND", "2": "ZMID"})
C("C30", "10u_25V_NP", 530, 300, "TAHO_CL", "TAHO_AC", rot=90)
R("R31", "10k", 550, 320, "TAHO_AC", "VB")
R("R32", "10k", 570, 290, "3V3", "VB")
R("R33", "10k", 570, 345, "VB", "GND")
part("COMPARATOR", "U5", 610, 315, {"1": "TAHO", "2": "TAHO_AC", "3": "VB"}, unit=1)
part("COMPARATOR", "U5", 610, 360, {"6": "3V3", "5": "GND"}, unit=2, nc=["7"])
part("COMPARATOR", "U5", 650, 360, {"8": "3V3", "4": "GND"}, unit=3)
R("R34", "100k", 640, 295, "TAHO", "VB", rot=90)
R("R35", "4k7", 660, 315, "3V3", "TAHO")
C("C31", "100n", 675, 360, "3V3", "GND")
S.note("TAHO: 22k -> два стабілітрони 5,1 В -> 10 мкФ -> LM393, зсув 1,65 В, гістерезис 100k.\n"
       "Живий дріт TAHO не можна садити на масу.", 470, 380)
R("R36", "1k", 720, 300, "REMOTE_IN", "REMOTE", rot=90)
C("C32", "100n", 740, 320, "REMOTE", "GND")
R("R37", "10k", 755, 300, "3V3", "REMOTE")
S.note("REMOTE: сухий контакт на GND, замкнено = запуск.", 700, 340)

# ======================================================================= mains
block("7. 230 В: запобіжник, варистор, AC-DC 24 В, детектор мережі (зазор >= 8 мм до низьковольтної частини)", 15, 280, 455, 400)
part("FUSE_AC", "F2", 45, 315, {"1": "AC_L", "2": "AC_LF"}, rot=90)
part("VARISTOR", "RV1", 70, 335, {"1": "AC_LF", "2": "AC_N"})
part("ACDC_24V", "PS1", 120, 330, {"1": "AC_LF", "2": "AC_N", "4": "V24", "3": "GND"})
C("C40", "100u_35V", 165, 345, "V24", "GND")
R("R40", "47k", 200, 310, "AC_LF", "AC_D1", rot=90, size="R1206")
R("R41", "47k", 240, 310, "AC_D1", "AC_D2", rot=90, size="R1206")
R("R42", "47k", 280, 310, "AC_D2", "AC_D3", rot=90, size="R1206")
part("OPTO_AC", "U6", 330, 330, {"1": "AC_D3", "2": "AC_N", "4": "MAINS_OK", "3": "GND"})
R("R43", "47k", 370, 315, "3V3", "MAINS_OK")
C("C41", "1u", 390, 345, "MAINS_OK", "GND")
S.note("Детектор: 3 x 47k (1206) -> оптопара з двома світлодіодами (AC). Мережа є = MAINS_OK низький.\n"
       "1 мкФ згладжує провали біля нуля синусоїди. PS1: ізоляція всередині модуля, -Vout = GND плати.", 20, 375)

# ======================================================================= charger (filled in by charger.py)
block("8. Зарядник свинцевої АКБ (CN3767): 14,8 В заряд / 13,55 В підтримка, 1 А", 15, 410, 455, 560)
import charger
charger.draw(S, part, R, C, x0=15, y0=410)

# ======================================================================= DIP, LEDs, connectors, holes
block("9. DIP, світлодіоди, роз'єми, кріплення", 465, 410, 830, 560)
part("DIP4", "SW3", 500, 450, {"1": "DIP1", "2": "DIP2", "3": "DIP3", "4": "DIP4",
                               "5": "GND", "6": "GND", "7": "GND", "8": "GND"})
S.note("DIP (замкнено = ON, внутрішні підтяжки ESP32):\n1 режим: OFF = REMOTE, ON = пропала мережа\n"
       "2 зарядка дозволена\n3 затримка запуску 10 / 60 с\n4 AUX: OFF = підігрів до пуску, ON = декомпресія під час прокрутки", 485, 470)
R("R50", "1k", 560, 440, "3V3", "LED_PWR")
part("LED_GREEN", "D30", 560, 460, {"2": "LED_PWR", "1": "GND"}, value="LED POWER")
R("R51", "1k", 580, 440, "LED_STAT", "LED_ST_A")
part("LED_GREEN", "D31", 580, 460, {"2": "LED_ST_A", "1": "GND"}, value="LED STATUS")
part("TB2", "J1", 640, 440, {"1": "AC_L", "2": "AC_N"}, value="AC IN 230V (L N)")
part("TB2", "J2", 640, 470, {"1": "CT_NO", "2": "CT_COM"}, value="CONTACTOR (NO COM)")
part("TB2", "J3", 700, 440, {"1": "VBAT", "2": "GND"}, value="BATTERY (+ -)")
part("TB2", "J4", 700, 470, {"1": "ACC_OUT", "2": "START_OUT"}, value="ACC START")
part("TB2", "J8", 700, 500, {"1": "AUX_OUT", "2": "GND"}, value="AUX (OUT GND)")
part("TB3", "J5", 760, 445, {"1": "TAHO_IN", "2": "REMOTE_IN", "3": "GND"}, value="TAHO REMOTE REMOTE")
part("HDR4", "J7", 760, 490, {"1": "3V3", "2": "EXT1", "3": "EXT2", "4": "GND"}, value="SPARE 3V3 IO17 IO18 GND")
for i in range(4):
    part("HOLE", "H%d" % (i + 1), 640 + 15 * i, 520, {})
S.note("H1-H4: кріплення M3 по кутах плати.", 640, 530)

# ======================================================================= power flags
for i, n in enumerate(["VBAT", "VIN12", "AC_N", "AC_LF", "3V3", "V5", "CHG_VCC"]):
    S.pwr_flag(n, 30 + i * 18, 575)

HERE = os.path.dirname(os.path.abspath(__file__))
out = os.path.join(HERE, "pramac_v6.kicad_sch")
S.save(out)
# project symbol library with the generated symbols + library table, so KiCad finds 'pramac_v6:...'
import copy
lib = ["kicad_symbol_lib", ["version", "20241209"], ["generator", kisch.Q("pramac_v6_gen")]]
for lid, node in S.libsyms.items():
    if lid.startswith("pramac_v6:"):
        n = copy.deepcopy(node); n[1] = kisch.Q(lid.split(":")[1]); lib.append(n)
open(os.path.join(HERE, "pramac_v6.kicad_sym"), "w", encoding="utf-8").write(kisch.dump(lib) + "\n")
open(os.path.join(HERE, "sym-lib-table"), "w").write(
    '(sym_lib_table\n  (version 7)\n  (lib (name "pramac_v6")(type "KiCad")(uri "${KIPRJMOD}/pramac_v6.kicad_sym")(options "")(descr "Board v6 symbols"))\n)\n')
# JLCPCB-style BOM (Comment, Designator, Footprint, LCSC); parts without an LCSC number are not assembled
import csv, re as _re
from parts import LOOSE
groups = {}
for ref, val, fp, lcsc, fields in S.parts:
    if not lcsc:
        continue
    groups.setdefault((val, fp.split(":")[-1], lcsc), []).append(ref)
keyf = lambda r: (_re.sub(r"\d+", "", r), int(_re.sub(r"\D", "", r) or 0))
with open(os.path.join(HERE, "pramac_v6_bom.csv"), "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["Comment", "Designator", "Footprint", "LCSC", "Qty"])
    for (val, fp, lcsc), refs in sorted(groups.items(), key=lambda g: keyf(sorted(g[1], key=keyf)[0])):
        refs = sorted(refs, key=keyf)
        w.writerow([val, ",".join(refs), fp, lcsc, len(refs)])
    for mpn, desc, lcsc, qty in LOOSE:
        w.writerow([mpn + " (loose, not soldered: " + desc + ")", "", "", lcsc, qty])
if not os.path.exists(os.path.join(HERE, "pramac_v6.kicad_pro")):
    open(os.path.join(HERE, "pramac_v6.kicad_pro"), "w").write('{"meta": {"filename": "pramac_v6.kicad_pro", "version": 1}}\n')
print("saved", out, "parts:", len(S.parts))
