"""Lead-acid charger block: Consonance CN3767 (PWM buck, CC / 14.8 V absorption / 13.55 V float, fixed internally).

Supply: V24 from the AC-DC module through a P-MOSFET switch the ESP32 controls (CHG_EN high or floating = charging,
so the battery keeps charging even if the ESP32 is not running). Charge current = 0.12 V / RCS = 1 A with 0.12 ohm.
Output goes to VBF (battery after the PTC fuse), so a reversed battery trips the fuse instead of the charger.
"""
import kisch

CN3767 = kisch.custom_symbol(
    "pramac_v6:CN3767",
    left=[("9", "VCC", "power_in"), ("1", "VG", "passive"), ("6", "MPPT", "input"), ("5", "COM", "passive"),
          ("2", "GND", "power_in")],
    right=[("10", "DRV", "output"), ("8", "CSP", "input"), ("7", "BAT", "input"), ("3", "~{CHRG}", "open_collector"),
           ("4", "~{DONE}", "open_collector")],
    width=15.24, ref="U", value="CN3767")

PMOS_SO8 = kisch.custom_symbol(
    "pramac_v6:PMOS_SO8",
    left=[None, ("4", "G", "input"), None],
    right=[("1", "S", "passive"), ("2", "S", "passive"), ("3", "S", "passive"), ("5", "D", "passive"),
           ("6", "D", "passive"), ("7", "D", "passive"), ("8", "D", "passive")],
    width=7.62, ref="Q", value="AO4421")


def draw(S, part, R, C, x0, y0):
    S.define(CN3767)
    S.define(PMOS_SO8)
    X = lambda dx: x0 + dx
    Y = lambda dy: y0 + dy

    # supply switch: ESP32 CHG_EN high (or floating, pull-up) -> Q22 on -> Q20 gate pulled down -> charger powered
    part("PMOS_SO8", "Q20", X(70), Y(50), {"1": "V24", "2": "V24", "3": "V24", "4": "CHG_SWG",
                                           "5": "CHG_VCC", "6": "CHG_VCC", "7": "CHG_VCC", "8": "CHG_VCC"})
    R("R60", "10k", X(35), Y(35), "V24", "CHG_SWG")
    R("R61", "10k", X(35), Y(65), "CHG_SWG", "CHG_Q")
    part("NMOS", "Q22", X(55), Y(95), {"1": "CHG_EN", "2": "GND", "3": "CHG_Q"})
    R("R62", "100k", X(25), Y(100), "3V3", "CHG_EN")
    S.note("Q20 вимикач живлення зарядника (Vgs = 12 В).\nCHG_EN: HIGH або ESP32 не працює = зарядка йде,\nLOW = зарядка вимкнена (прокрутка стартера, DIP2 OFF).", X(5), Y(118))

    C("C60", "100u_35V", X(110), Y(70), "CHG_VCC", "GND")
    C("C61", "10u_50V", X(125), Y(70), "CHG_VCC", "GND")
    C("C62", "100n", X(140), Y(70), "CHG_VCC", "GND")

    part("CN3767", "U20", X(195), Y(65), {"9": "CHG_VCC", "1": "CHG_VG", "6": "CHG_MPPT", "5": "CHG_COM", "2": "GND",
                                         "10": "CHG_DRV", "8": "CHG_CSP", "7": "VBF", "3": "CHG_STAT", "4": "CHG_DONE"})
    C("C63", "100n", X(160), Y(35), "CHG_VG", "CHG_VCC", rot=90)
    R("R63", "150k", X(160), Y(85), "CHG_VCC", "CHG_MPPT")
    R("R64", "10k", X(160), Y(110), "CHG_MPPT", "GND")
    R("R65", "120", X(185), Y(110), "CHG_COM", "CHG_COMR")
    C("C64", "220n", X(205), Y(118), "CHG_COMR", "GND")

    part("PMOS_SO8", "Q21", X(255), Y(50), {"1": "CHG_VCC", "2": "CHG_VCC", "3": "CHG_VCC", "4": "CHG_DRV",
                                            "5": "CHG_SW", "6": "CHG_SW", "7": "CHG_SW", "8": "CHG_SW"})
    part("SCHOTTKY_5A", "D22", X(290), Y(80), {"1": "CHG_SW", "2": "GND"})
    part("IND_CHG", "L20", X(310), Y(45), {"1": "CHG_SW", "2": "CHG_CSP"}, rot=90)
    part("RSENSE", "R66", X(345), Y(45), {"1": "CHG_CSP", "2": "VBF"}, rot=90)
    C("C65", "100u_35V", X(370), Y(75), "VBF", "GND")
    C("C66", "10u_50V", X(385), Y(75), "VBF", "GND")
    S.note("MPPT 150k/10k: якщо AC-DC просідає нижче ~19 В, зарядник зменшує струм.\n"
           "COM: 120 Ом + 220 нФ (компенсація). RCS 0,12 Ом = 1 А, Kelvin-доріжки до CSP/BAT.", X(225), Y(98))

    # status: open drain, low = active; read by the ESP32 and shown on LEDs
    R("R67", "10k", X(300), Y(115), "3V3", "CHG_STAT")
    R("R68", "1k", X(320), Y(110), "3V3", "CHG_LR")
    part("LED_RED", "D23", X(320), Y(130), {"2": "CHG_LR", "1": "CHG_STAT"}, value="LED CHARGING")
    R("R69", "10k", X(350), Y(115), "3V3", "CHG_DONE")
    R("R70", "1k", X(370), Y(110), "3V3", "CHG_LG")
    part("LED_GREEN", "D24", X(370), Y(130), {"2": "CHG_LG", "1": "CHG_DONE"}, value="LED CHARGED")
