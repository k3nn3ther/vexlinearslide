import argparse
import os
import time

import cv2
import mediapipe as mp
import serial

BRAIN_PORT = os.environ.get("VEX_USER_PORT", "/dev/cu.usbmodem103")
SERIAL_SPEED = 115200

# set the camera size, hand box, and slide movement limits 
CAMERA_NUMBER = 0
CAMERA_WIDTH = 1280
CAMERA_HEIGHT = 720
SMALL_IMAGE_WIDTH = 640
EDGE_GAP = 2
HAND_SMOOTHING = 0.5
SEND_DELAY = 0.50
MIN_SLIDE_CHANGE = 4
MAX_SLIDE_GOAL = 1000
WINDOW_WIDTH = 960
WINDOW_HEIGHT = 540
WINDOW_TITLE = "VEX Linear Slide Control"
HAND_BOX_SIZE = 30
GREEN = (0, 255, 0)
BLUE = (255, 0, 0)



class BrainConnection:
    # send commands to the v5 brain over USB 

    def __init__(self):
        self.port = serial.Serial(BRAIN_PORT, SERIAL_SPEED, timeout=0)

    def send_position(self, slide_goal):
        self.port.write(f"{slide_goal}\n".encode("ascii"))

    def close(self):
        self.port.close()


def open_brain_connection():
    return BrainConnection()


def main():
    # preview mode shows hand tracking without sending commands to the brain 
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--preview",
        action="store_true",
        help="run camera tracking without connecting to a VEX Brain",
    )
    args = parser.parse_args()

    # open the brain connection when not in preview, then start the camera 
    brain_connection = None if args.preview else open_brain_connection()
    webcam = cv2.VideoCapture(CAMERA_NUMBER)
    webcam.set(cv2.CAP_PROP_FRAME_WIDTH, CAMERA_WIDTH)
    webcam.set(cv2.CAP_PROP_FRAME_HEIGHT, CAMERA_HEIGHT)
    webcam.set(cv2.CAP_PROP_BUFFERSIZE, 1)

    if not webcam.isOpened():
        webcam.release()
        if brain_connection is not None:
            brain_connection.close()
        raise RuntimeError("Could not open camera")

    hand_tools = mp.solutions.hands 
    hand_finder = hand_tools.Hands(
        static_image_mode=False,
        max_num_hands=1,
        model_complexity=0,
        min_detection_confidence=0.6,
        min_tracking_confidence=0.5,
    )
    got_image, first_image = webcam.read()
    if not got_image:
        webcam.release()
        hand_finder.close()
        if brain_connection is not None:
            brain_connection.close()
        raise RuntimeError("Could not read camera frame")

    image_height, image_width = first_image.shape[:2]
    display_scale = min(WINDOW_WIDTH / image_width, WINDOW_HEIGHT / image_height)
    window_width = int(image_width * display_scale)
    window_height = int(image_height * display_scale)
    small_image_height = int(image_height * SMALL_IMAGE_WIDTH / image_width)
    # use the inside edges of the blue box as the hand movement range 
    left_edge = EDGE_GAP / window_width
    right_edge = 1.0 - left_edge

    cv2.namedWindow(WINDOW_TITLE, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(WINDOW_TITLE, window_width, window_height)

    smooth_slide_goal = None
    last_slide_goal = None
    last_send_time = 0.0
    if args.preview:
        print("Preview mode: no Brain connected; motor commands will not be sent. Press Q to quit.")
    else:
        print("Tracking started over direct Brain USB. Press Q to quit.")

    try:
        while True:
            # read each camera frame and check whether a hand is visible 
            got_image, image = webcam.read()
            if not got_image:
                print("Could not read camera frame")
                break

            image = cv2.flip(image, 1)
            small_image = cv2.resize(
                image, (SMALL_IMAGE_WIDTH, small_image_height)
            )
            hand_result = hand_finder.process(
                cv2.cvtColor(small_image, cv2.COLOR_BGR2RGB)
            )
            window_image = cv2.resize(image, (window_width, window_height))
            cv2.rectangle(
                window_image,
                (EDGE_GAP, EDGE_GAP),
                (
                    window_width - 1 - EDGE_GAP,
                    window_height - 1 - EDGE_GAP,
                ),
                BLUE,
                2,
            )

            if hand_result.multi_hand_landmarks:
                # follow the middle of the palm so a moving finger does not shift the target 
                hand_points = hand_result.multi_hand_landmarks[0].landmark
                palm_points = (
                   hand_tools.HandLandmark.WRIST,
                    hand_tools.HandLandmark.INDEX_FINGER_MCP,
                    hand_tools.HandLandmark.MIDDLE_FINGER_MCP,
                     hand_tools.HandLandmark.RING_FINGER_MCP,
                    hand_tools.HandLandmark.PINKY_MCP,
                )
                hand_x = sum(hand_points[point].x for point in palm_points) / len(palm_points)
                hand_y = sum(hand_points[point].y for point in palm_points) / len(palm_points)
                range_fraction = (hand_x - left_edge) / (right_edge - left_edge)
                range_fraction = max(0.0, min(1.0, range_fraction))
                new_slide_goal = round(range_fraction * MAX_SLIDE_GOAL)
                # smooth hand movement and send updates only when the target has changed enough 
                smooth_slide_goal = (
                    new_slide_goal
                    if smooth_slide_goal is None
                    else smooth_slide_goal + HAND_SMOOTHING *
                    (new_slide_goal - smooth_slide_goal)
                )
                slide_goal = round(smooth_slide_goal)

                current_time = time.monotonic()
                moved_enough = (
                    last_slide_goal is None
                    or abs(slide_goal - last_slide_goal) >= MIN_SLIDE_CHANGE
                )
                at_limit = slide_goal in (0, MAX_SLIDE_GOAL) and slide_goal != last_slide_goal
                if (moved_enough or at_limit) and current_time - last_send_time >= SEND_DELAY:
                    if brain_connection is not None:
                        try:
                            brain_connection.send_position(slide_goal)
                        except Exception as error:
                            print(f"Brain connection lost while sending a target: {error}")
                            break
                    last_slide_goal = slide_goal
                    last_send_time = current_time

                # draw the green hand marker and show the current slide goal 
                hand_pixel_x = int(hand_x * window_width)
                hand_pixel_y = int(hand_y * window_height)
                cv2.rectangle(
                    window_image,
                    (hand_pixel_x - HAND_BOX_SIZE // 2, hand_pixel_y - HAND_BOX_SIZE // 2),
                   (hand_pixel_x + HAND_BOX_SIZE // 2, hand_pixel_y + HAND_BOX_SIZE // 2),
                    GREEN,
                    -1,
                )
                cv2.putText(
                    window_image,
                    f"Slide: {slide_goal / 10:.0f}%",
                    (30, 70),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    1.8,
                    GREEN,
                    4,
                )

            if args.preview:
                cv2.putText(
                    window_image,
                    "PREVIEW - no Brain connected",
                    (30, window_height - 30),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.8,
                    (0, 165, 255),
                    2,
                )

            cv2.imshow(WINDOW_TITLE, window_image)
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break
    finally:
        webcam.release()
        hand_finder.close()
        cv2.destroyAllWindows()
        if brain_connection is not None:
            brain_connection.close()
        print("Tracking stopped.")


if __name__ == "__main__":
    main()
