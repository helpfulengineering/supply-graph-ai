"""A stand-in for mitra42/frugal-iot-hw-sensor, the repository #561 was filed on.

That repository has no licence, so none of its content is copied here. This
tree reproduces its *shape*: the file names and directory layout the reporter
described and the generator tripped on, with placeholder contents written for
this test. The facts the assertions rely on match the reporter's account:

- no release, tag or version file; "v02" appears only in file names
- the BOM is at ``BOM.csv`` and, for JLCPCB, under ``fabrication/``
- ``SCHEMATIC.pdf`` is the schematic
- nothing in it is sheet metal
"""

from pathlib import Path

README = """\
# Frugal IoT sensor board

A small ESP32 sensor board for the Frugal IoT stack. Most builds use off the
shelf modules; this board brings them together on one PCB.

Built with ESP-IDF 5.1.2. See each sensor's data sheet for wiring limits.

## Files

- `SCHEMATIC.pdf`: the circuit
- `PCB-LAYOUT.pdf`: the board layout
- `BOM.csv`: parts list for people
- `fabrication/`: gerbers and the JLCPCB BOM and placement files
"""

BOM_CSV = """\
Reference,Value,Footprint,Quantity
U1,ESP32-C3-MINI-1,RF_Module:ESP32-C3-MINI-1,1
C1,10uF,Capacitor_SMD:C_0805,2
R1,10k,Resistor_SMD:R_0603,4
J1,USB-C,Connector_USB:USB_C_Receptacle,1
"""

JLCPCB_BOM = """\
Comment,Designator,Footprint,LCSC
ESP32-C3-MINI-1,U1,ESP32-C3-MINI-1,C2838502
10uF,"C1,C2",0805,C15850
10k,"R1,R2,R3,R4",0603,C25804
"""

# A PDF header is enough: categorisation reads names and paths, not content.
PDF = b"%PDF-1.4\n%placeholder for a test fixture\n"
GERBER = "G04 placeholder for a test fixture*\nM02*\n"

BOM_ROWS = ["ESP32-C3-MINI-1", "10uF", "10k", "USB-C"]


def build(root: Path) -> Path:
    """Write the stand-in tree under ``root`` and return it."""
    files: dict[str, str | bytes] = {
        "README.md": README,
        "BOM.csv": BOM_CSV,
        "SCHEMATIC.pdf": PDF,
        "PCB-LAYOUT.pdf": PDF,
        "fabrication/BOM_JLCPCB.csv": JLCPCB_BOM,
        "fabrication/frugal_iot_v02-F_Cu.gbr": GERBER,
        "fabrication/frugal_iot_v02-B_Cu.gbr": GERBER,
        "fabrication/frugal_iot_v02-Edge_Cuts.gbr": GERBER,
    }
    for name, content in files.items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(content, bytes):
            path.write_bytes(content)
        else:
            path.write_text(content)
    return root
