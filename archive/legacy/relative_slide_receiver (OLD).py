"""Archived receiver for the old relative-movement hand tracker."""
import sys
from vex import *

brain = Brain()
slide = Motor(Ports.PORT1, GearSetting.RATIO_18_1, False)
MIN_POSITION = -700
MAX_POSITION = 700
MOTOR_SPEED_PERCENT = 100

slide.set_velocity(MOTOR_SPEED_PERCENT, PERCENT)
slide.set_stopping(HOLD)
target = max(MIN_POSITION, min(MAX_POSITION, slide.position(DEGREES)))
brain.screen.clear_screen()
brain.screen.print("Waiting for host")

while True:
    line = sys.stdin.readline()
    if not line:
        wait(20, MSEC)
        continue
    try:
        delta = int(line.strip())
    except (ValueError, TypeError):
        continue
    if abs(delta) > 100:
        continue
    target = max(MIN_POSITION, min(MAX_POSITION, target + delta))
    slide.spin_to_position(target, DEGREES, MOTOR_SPEED_PERCENT, PERCENT, False)
