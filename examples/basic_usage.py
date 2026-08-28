"""Minimal example: connect, home, aspirate, dispense, eject.

Set PORT to your serial port, press a tip on manually, and run.
"""

from dorna_pipette import DornaPipette

PORT = "/dev/ttyUSB0"   # e.g. 'COM3' on Windows
ADDR = 1

# steps_per_ul depends on the barrel size:
#   1 mL barrel with a 5000-step full stroke = 5 steps/µL.
with DornaPipette(PORT, addr=ADDR, steps_per_ul=5.0) as pip:
    print("Homing:", pip.initialize())
    print("Tip on:", pip.has_tip())

    print("Aspirate 50 µL:", pip.aspirate(50))
    print("Dispense 50 µL:", pip.dispense(50, blowout=True))

    print("Eject tip:", pip.eject_tip())
