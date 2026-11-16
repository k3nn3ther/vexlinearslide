import sys
from vex import *

brain = Brain()
slide = Motor(Ports.PORT1, GearSetting.RATIO_18_1, False)

# set the slide speed, safe gap from each end, and calibration checks #
MOTOR_SPEED = 100
CALIBRATION_SPEED = 25
CALIBRATION_TORQUE = 30
END_MARGIN = 10
STALL_VELOCITY = 3
STALL_CURRENT_AMPS = 0.15
STALL_POSITION_CHANGE_DEGREES = 0.5
STALL_CONFIRM_MS = 200
CALIBRATION_STARTUP_MS = 300
CALIBRATION_CHECK_MS = 50
CALIBRATION_MAX_TIME_MS = 15000
COMMAND_MAX = 1000

# move gently toward one end and record where the slide stops #
def find_stop(direction): 
    slide.set_max_torque(CALIBRATION_TORQUE, PERCENT)
    slide.spin(direction, CALIBRATION_SPEED, PERCENT)

    elapsed_ms = 0
    stalled_ms = 0
    previous_position = slide.position(DEGREES)
    while elapsed_ms < CALIBRATION_MAX_TIME_MS:
        wait(CALIBRATION_CHECK_MS, MSEC)
        elapsed_ms += CALIBRATION_CHECK_MS

        position = slide.position(DEGREES)
        position_change = abs(position - previous_position)
        velocity = abs(slide.velocity(PERCENT))
        current = slide.current(CurrentUnits.AMP)

        if (
            elapsed_ms >= CALIBRATION_STARTUP_MS
            and position_change <= STALL_POSITION_CHANGE_DEGREES
            and velocity <= STALL_VELOCITY
            and current >= STALL_CURRENT_AMPS
        ):
            stalled_ms += CALIBRATION_CHECK_MS
            if stalled_ms >= STALL_CONFIRM_MS:
                break
        else:
            stalled_ms = 0

        previous_position = position
    else:
        slide.stop()
        slide.set_max_torque(100, PERCENT)
        raise RuntimeError("Calibration timed out before the slide reached a stop")

    slide.stop()
    position = slide.position(DEGREES)
    slide.set_max_torque(100, PERCENT)
    return position


def calibrate_travel():
# find both ends and leave a small safe gap inside the hard stops 
    brain.screen.clear_screen()
    brain.screen.print("Finding reverse stop")
    end_a = find_stop(REVERSE)

    brain.screen.clear_screen()
    brain.screen.print("Finding forward stop")
    end_b = find_stop(FORWARD)
    low = min(end_a, end_b) + END_MARGIN
    high = max(end_a, end_b) - END_MARGIN
    travel = high - low
    if travel <= 0:
        raise RuntimeError("Slide travel is too short to use")
    return low, travel


def main():
    # calibrate the slide first, then wait for position commands from the computer 
    brain.screen.clear_screen()
    brain.screen.print("Calibrating slide...")

    try:
        low, travel = calibrate_travel()
    except RuntimeError as error:
        brain.screen.clear_screen()
        brain.screen.print("Calibration failed")
        brain.screen.next_row()
        brain.screen.print(str(error))
        return

    slide.set_velocity(MOTOR_SPEED, PERCENT)
    slide.set_stopping(HOLD)

    brain.screen.clear_screen()
    brain.screen.print("Travel: %d deg" % travel)
    brain.screen.next_row()
    brain.screen.print("Waiting for host")
    print("SLIDE_READY")

    received_count = 0
    while True:
        # read the next position, keep it within range and move the slide 
        line = sys.stdin.readline()
        if not line:
            wait(20, MSEC)
            continue

        try:
            command = int(line.strip())
        except (ValueError, TypeError):
            continue

        command = max(0, min(COMMAND_MAX, command))
        received_count += 1
        target = low + travel * command / COMMAND_MAX
        brain.screen.set_cursor(3, 1)
        brain.screen.print("Target: %d%%   " % (command / 10))
        brain.screen.set_cursor(4, 1)
        brain.screen.print("Received: %d   " % received_count)
        slide.spin_to_position(target, DEGREES, MOTOR_SPEED, PERCENT, False)


main()
