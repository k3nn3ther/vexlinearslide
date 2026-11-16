from vex import *

brain = Brain()

slide = Motor(
    Ports.PORT1,
    GearSetting.RATIO_18_1,
    False
)

brain.screen.clear_screen()
brain.screen.set_cursor(1, 1)
brain.screen.print("Motor calibration")
brain.screen.next_row()

while True:
    position = slide.position(DEGREES)

    brain.screen.set_cursor(3, 1)
    brain.screen.print("Degrees: ")
    brain.screen.print(position)

    wait(100, MSEC)
