import cv2
import mediapipe as mp
import serial
import time
import tkinter as tk

SERIAL_PORT = "/dev/cu.usbmodem103"
BAUD_RATE = 115200

X_MIN, X_MAX = 0.20, 0.80   # part of the image width that maps to full slide travel

SMOOTHING = 0.5
SEND_INTERVAL = 0.03
MIN_CHANGE = 4

# How much of the screen the window may use (leaves room for menu bar and dock)
FIT_W, FIT_H = 0.95, 0.85

# Get screen size automatically
root = tk.Tk()
SCREEN_W = root.winfo_screenwidth()
SCREEN_H = root.winfo_screenheight()
root.destroy()

WINDOW_NAME = "VEX Linear Slide Control"

ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=0)
time.sleep(2)
ser.reset_input_buffer()

mp_hands = mp.solutions.hands
mp_draw = mp.solutions.drawing_utils
hands = mp_hands.Hands(
    static_image_mode=False,
    max_num_hands=1,
    model_complexity=0,
    min_detection_confidence=0.6,
    min_tracking_confidence=0.5,
)

cap = cv2.VideoCapture(0)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
if not cap.isOpened():
    ser.close()
    raise RuntimeError("Could not open camera")

# Read one frame to learn the camera's real size
ok, frame = cap.read()
if not ok:
    ser.close()
    raise RuntimeError("Could not read camera frame")
cam_h, cam_w = frame.shape[:2]

# Scale to fit the screen while keeping the aspect ratio
scale = min(SCREEN_W * FIT_W / cam_w, SCREEN_H * FIT_H / cam_h)
DISPLAY_W, DISPLAY_H = int(cam_w * scale), int(cam_h * scale)

# Small copy for tracking (same aspect ratio)
SMALL_W = 640
SMALL_H = int(cam_h * SMALL_W / cam_w)

# Normal window, sized to fit and centered
cv2.namedWindow(WINDOW_NAME, cv2.WINDOW_NORMAL)
cv2.resizeWindow(WINDOW_NAME, DISPLAY_W, DISPLAY_H)
cv2.moveWindow(WINDOW_NAME,
               (SCREEN_W - DISPLAY_W) // 2,
               max(0, (SCREEN_H - DISPLAY_H) // 2 - 20))

smoothed = None
last_sent = None
last_send_time = 0

print("Tracking started. Press Q to quit.")
try:
    while True:
        ok, frame = cap.read()
        if not ok:
            print("Could not read camera frame")
            break

        frame = cv2.flip(frame, 1)

        # Track on a small copy for speed
        small = cv2.resize(frame, (SMALL_W, SMALL_H))
        results = hands.process(cv2.cvtColor(small, cv2.COLOR_BGR2RGB))

        # Display frame, same aspect ratio as the camera
        display = cv2.resize(frame, (DISPLAY_W, DISPLAY_H))

        if results.multi_hand_landmarks:
            hand = results.multi_hand_landmarks[0]
            tip = hand.landmark[mp_hands.HandLandmark.INDEX_FINGER_TIP]

            norm = (tip.x - X_MIN) / (X_MAX - X_MIN)
            norm = max(0.0, min(1.0, norm))

            smoothed = norm if smoothed is None else smoothed + SMOOTHING * (norm - smoothed)
            pos = round(smoothed * 1000)

            now = time.monotonic()
            at_edge = pos in (0, 1000) and pos != last_sent
            changed = last_sent is None or abs(pos - last_sent) >= MIN_CHANGE
            if (changed or at_edge) and now - last_send_time >= SEND_INTERVAL:
                ser.write(f"{pos}\n".encode())
                last_sent = pos
                last_send_time = now

            mp_draw.draw_landmarks(display, hand, mp_hands.HAND_CONNECTIONS)
            cv2.putText(display, f"Slide: {pos / 10:.0f}%", (30, 70),
                        cv2.FONT_HERSHEY_SIMPLEX, 1.8, (0, 255, 0), 4)

        # Active zone lines
        x1, x2 = int(X_MIN * DISPLAY_W), int(X_MAX * DISPLAY_W)
        cv2.line(display, (x1, 0), (x1, DISPLAY_H), (255, 0, 0), 2)
        cv2.line(display, (x2, 0), (x2, DISPLAY_H), (255, 0, 0), 2)

        cv2.imshow(WINDOW_NAME, display)
        if cv2.waitKey(1) & 0xFF == ord("q"):
            break
finally:
    cap.release()
    hands.close()
if results.multi_hand_landmarks:
    hand = results.multi_hand_landmarks[0]
    landmarks = hand.landmark

    # Estimate center of palm using wrist and palm knuckles
    palm_points = [
        landmarks[mp_hands.HandLandmark.WRIST],
        landmarks[mp_hands.HandLandmark.INDEX_FINGER_MCP],
        landmarks[mp_hands.HandLandmark.MIDDLE_FINGER_MCP],
        landmarks[mp_hands.HandLandmark.RING_FINGER_MCP],
        landmarks[mp_hands.HandLandmark.PINKY_MCP]
    ]

    center_x = sum(p.x for p in palm_points) / len(palm_points)
    center_y = sum(p.y for p in palm_points) / len(palm_points)

    # Convert palm center into slide position
    norm = (center_x - X_MIN) / (X_MAX - X_MIN)
    norm = max(0.0, min(1.0, norm))

    smoothed = (
        norm if smoothed is None
        else smoothed + SMOOTHING * (norm - smoothed)
    )

    pos = round(smoothed * 1000)

    # Send position to VEX Brain
    now = time.monotonic()

    at_edge = pos in (0, 1000) and pos != last_sent
    changed = last_sent is None or abs(pos - last_sent) >= MIN_CHANGE

    if (changed or at_edge) and now - last_send_time >= SEND_INTERVAL:
        ser.write(f"{pos}\n".encode())
        last_sent = pos
        last_send_time = now

    # Draw filled lime-green square at palm center
    center_px = int(center_x * DISPLAY_W)
    center_py = int(center_y * DISPLAY_H)

    BOX_SIZE = 30

    cv2.rectangle(
        display,
        (center_px - BOX_SIZE // 2, center_py - BOX_SIZE // 2),
        (center_px + BOX_SIZE // 2, center_py + BOX_SIZE // 2),
        (0, 255, 0),
        -1
    )

    cv2.putText(
        display,
        f"Slide: {pos / 10:.0f}%",
        (30, 70),
        cv2.FONT_HERSHEY_SIMPLEX,
        1.8,
        (0, 255, 0),
        4
    )

    cv2.destroyAllWindows()
    ser.close()
    print("Tracking stopped.")