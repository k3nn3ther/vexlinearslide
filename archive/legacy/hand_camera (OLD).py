import cv2
import mediapipe as mp
import serial
import time


SERIAL_PORT = "/dev/cu.usbmodem103"
BAUD_RATE = 115200
SMOOTHING = 0.25
DEAD_ZONE = 0.004
SENSITIVITY = 500
SEND_INTERVAL = 0.03  # around 33 commands per second


ser = serial.Serial(
    SERIAL_PORT,
    BAUD_RATE,
    timeout=0.1
)


time.sleep(2)
ser.reset_input_buffer()


mp_hands = mp.solutions.hands
mp_draw = mp.solutions.drawing_utils

hands = mp_hands.Hands(
    static_image_mode=False,
    max_num_hands=1,
    model_complexity=0,
    min_detection_confidence=0.6,
    min_tracking_confidence=0.6
)

cap = cv2.VideoCapture(0)

if not cap.isOpened():
    ser.close()
    raise RuntimeError("Could not open camera")

smoothed_x = None
previous_x = None
last_send_time = 0

print("Tracking started. Press Q to quit.")

try:
    while True:
        success, frame = cap.read()

        if not success:
            print("Could not read camera frame")
            break


        frame = cv2.flip(frame, 1)

        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = hands.process(rgb)

        if results.multi_hand_landmarks:
            hand = results.multi_hand_landmarks[0]


            tip = hand.landmark[
                mp_hands.HandLandmark.INDEX_FINGER_TIP
            ]

            x = tip.x

            if smoothed_x is None:
                smoothed_x = x
                previous_x = x
            else:

                smoothed_x += SMOOTHING * (
                    x - smoothed_x
                )

                delta_x = smoothed_x - previous_x
                previous_x = smoothed_x

                now = time.monotonic()

                if (
                    abs(delta_x) >= DEAD_ZONE
                    and now - last_send_time >= SEND_INTERVAL
                ):
                    delta_degrees = round(
                        delta_x * SENSITIVITY
                    )

                    if delta_degrees != 0:
                        command = f"{delta_degrees}\n"
                        ser.write(command.encode("utf-8"))
                        last_send_time = now

            # Draw hand landmarks
            mp_draw.draw_landmarks(
                frame,
                hand,
                mp_hands.HAND_CONNECTIONS
            )

            cv2.circle(
                frame,
                (
                    int(tip.x * frame.shape[1]),
                    int(tip.y * frame.shape[0])
                ),
                10,
                (0, 255, 0),
                -1
            )

            cv2.putText(
                frame,
                f"Finger X: {smoothed_x:.3f}",
                (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (0, 255, 0),
                2
            )

        cv2.imshow("VEX Linear Slide Control", frame)

        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

finally:
    cap.release()
    hands.close()
    cv2.destroyAllWindows()
    ser.close()
    print("Tracking stopped. Serial port closed.")