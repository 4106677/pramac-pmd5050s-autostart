"""Parts table for board v6: key -> (value, KiCad footprint, LCSC number, KiCad symbol).

LCSC numbers checked against the JLCPCB parts library on 2026-11-12 (Basic parts where they exist).
"""
R0805 = "Resistor_SMD:R_0805_2012Metric"
R1206 = "Resistor_SMD:R_1206_3216Metric"
C0805 = "Capacitor_SMD:C_0805_2012Metric"
C1206 = "Capacitor_SMD:C_1206_3216Metric"

P = {}

# resistors 0805 1 % 150 V (JLCPCB Basic)
for val, lcsc in [("100", "C17408"), ("120", "C17437"), ("1k", "C17513"), ("4k7", "C17673"), ("5k1", "C27834"),
                  ("10k", "C17414"), ("22k", "C17560"), ("47k", "C17713"), ("100k", "C149504"), ("150k", "C17470"), ("2k2", "C17520")]:
    P["R0805_" + val] = (val, R0805, lcsc, "Device:R")
# 1206 200 V: TAHO input and the mains detector chain
for val, lcsc in [("22k", "C25830"), ("47k", "C25833")]:
    P["R1206_" + val] = (val, R1206, lcsc, "Device:R")

# capacitors
for key, val, fp, lcsc in [("100n", "100n 50V X7R", C0805, "C49678"), ("220n", "220n 50V X7R", C0805, "C5378"),
                           ("1u", "1u 25V X7R", C0805, "C89190"), ("10u", "10u 25V X5R", C0805, "C15850"),
                           ("22u", "22u 10V X5R", C0805, "C380338"), ("10u_50V", "10u 50V X5R", C1206, "C13585"),
                           ("10u_25V_NP", "10u 25V X7R", C1206, "C70462")]:
    P["C_" + key] = (val, fp, lcsc, "Device:C")
P["C_100u_35V"] = ("100u 35V", "Capacitor_SMD:CP_Elec_6.3x7.7", "C2836442", "Device:C_Polarized")

P.update({
    "FUSE_12V":    ("PTC 2A hold 1812", "Fuse:Fuse_1812_4532Metric", "C434887", "Device:Polyfuse"),
    "TVS_12V":     ("SMBJ18A", "Diode_SMD:D_SMB", "C353379", "Device:D_Zener"),
    "SCHOTTKY_5A": ("SS54", "Diode_SMD:D_SMA", "C22452", "Device:D_Schottky"),
    "SCHOTTKY_3A": ("SS34", "Diode_SMD:D_SMA", "C8678", "Device:D_Schottky"),
    "CAP_BULK":    ("470u 35V", "Capacitor_SMD:CP_Elec_10x10.5", "C2836436", "Device:C_Polarized"),
    "BUCK_3V3":    ("AP63203WU-7", "Package_TO_SOT_SMD:TSOT-23-6", "C780769", "Regulator_Switching:AP63203WU"),
    "BUCK_5V":     ("AP63205WU-7", "Package_TO_SOT_SMD:TSOT-23-6", "C2071056", "Regulator_Switching:AP63205WU"),
    "IND_BUCK":    ("4.7u 5A FXL0530", "Inductor_SMD:L_Changjiang_FXL0530", "C177246", "Device:L"),
    "ESP32S3":     ("ESP32-S3-MINI-1U-N8", "RF_Module:ESP32-S2-MINI-1U", "C2980299", "RF_Module:ESP32-S3-MINI-1U"),
    "TACT":        ("TS-1187A-B-A-B", "Button_Switch_SMD:SW_Push_1P1T_XKB_TS-1187A", "C318884", "Switch:SW_Push"),
    "TESTPOINT":   ("TP", "TestPoint:TestPoint_Pad_D1.5mm", "", "Connector:TestPoint"),
    "USB_C":       ("TYPE-C-31-M-12", "Connector_USB:USB_C_Receptacle_HRO_TYPE-C-31-M-12", "C165948", "Connector:USB_C_Receptacle_USB2.0_16P"),
    "ESD_USB":     ("USBLC6-2SC6", "Package_TO_SOT_SMD:SOT-23-6", "C7519", "Power_Protection:USBLC6-2SC6"),
    "RELAY":       ("SRD-05VDC-SL-C", "Relay_THT:Relay_SPDT_SANYOU_SRD_Series_Form_C", "C35449", "Relay:SANYOU_SRD_Form_C"),
    "NMOS":        ("AO3400A", "Package_TO_SOT_SMD:SOT-23", "C20917", "Transistor_FET:AO3400A"),
    "DIODE_SIG":   ("1N4148W", "Diode_SMD:D_SOD-123", "C81598", "Device:D"),
    "ZENER_5V1":   ("BZT52C5V1", "Diode_SMD:D_SOD-123", "C2117", "Device:D_Zener"),
    "COMPARATOR":  ("LM393DR2G", "Package_SO:SOIC-8_3.9x4.9mm_P1.27mm", "C7955", "Comparator:LM393"),
    "LED_RED":     ("LED red", "LED_SMD:LED_0805_2012Metric", "C84256", "Device:LED"),
    "LED_GREEN":   ("LED green", "LED_SMD:LED_0805_2012Metric", "C2297", "Device:LED"),
    "FUSE_AC":     ("T1A 250VAC TR5", "Fuse:Fuse_Littelfuse_372_D8.50mm", "C142808", "Device:Fuse"),
    "VARISTOR":    ("07D471K", "Varistor:RV_Disc_D7mm_W3.4mm_P5mm", "C28756", "Device:Varistor"),
    "ACDC_24V":    ("IRM-20-24", "Converter_ACDC:Converter_ACDC_MeanWell_IRM-20-xx_THT", "C194964", "Converter_ACDC:IRM-20-24"),
    "OPTO_AC":     ("LTV-814S-TA1-A", "Package_DIP:SMDIP-4_W9.53mm", "C108051", "Isolator:EL814"),
    "DIP4":        ("DIP switch 4P", "Button_Switch_SMD:SW_DIP_SPSTx04_Slide_6.7x11.72mm_W8.61mm_P2.54mm_LowProfile", "C6331176", "Switch:SW_DIP_x04"),
    "TB2":         ("WJ2EDGRC-5.08-02P", "Connector_Phoenix_MSTB:PhoenixContact_MSTBA_2,5_2-G-5,08_1x02_P5.08mm_Horizontal", "C3697", "Connector_Generic:Conn_01x02"),
    "TB3":         ("WJ2EDGRC-5.08-03P", "Connector_Phoenix_MSTB:PhoenixContact_MSTBA_2,5_3-G-5,08_1x03_P5.08mm_Horizontal", "C8377", "Connector_Generic:Conn_01x03"),
    "HDR4":        ("PZ254V-11-04P", "Connector_PinHeader_2.54mm:PinHeader_1x04_P2.54mm_Vertical", "C2691448", "Connector_Generic:Conn_01x04"),
    "HOLE":        ("M3", "MountingHole:MountingHole_3.2mm_M3", "", "Mechanical:MountingHole"),
    # charger
    "CN3767":      ("CN3767", "Package_SO:SSOP-10_3.9x4.9mm_P1.00mm", "C81968", "pramac_v6:CN3767"),
    "PMOS_SO8":    ("AO4421", "Package_SO:SOIC-8_3.9x4.9mm_P1.27mm", "C33484", "pramac_v6:PMOS_SO8"),
    "IND_CHG":     ("47u 2.5A SMDRI127", "Inductor_SMD:L_12x12mm_H8mm", "C9906", "Device:L"),
    "RSENSE":      ("0.12 1% 1206", R1206, "C2907346", "Device:R"),
})

# loose parts JLCPCB ships with the order (not soldered): terminal block plugs
LOOSE = [("WJ2EDGK-5.08-02P-14-00A", "plug 2P for J1-J4, J8", "C71370", 5),
         ("WJ2EDGK-5.08-03P-14-00A", "plug 3P for J5", "C71371", 1)]
