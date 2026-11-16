from vex import *

brain = Brain()
motor = Motor(Ports.PORT1, GearSetting.RATIO_18_1, False)

motor.set_velocity(100, PERCENT)

while True:
    if brain.screen.pressing():
        if brain.screen.x_position() < 240:
            motor.spin(REVERSE)
        else:
            motor.spin(FORWARD)
    else:
        motor.stop()

    wait(20, MSEC)
        