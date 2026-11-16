VEX Linear Slide

The computer folder contains the hand tracker. The diagnostics folder contains the motor testing and brain display I was playing around with. src contains the main for the V5 brain.


Required software
Python 3.9
OpenCV (opencv-python) version 4.11.0.86
MediaPipe version 0.10.21
pyserial version 3.5

Setup
From the project folder, run these commands to create the Python environment and install the required packages.

python3 -m venv .venv-host
source .venv-host/bin/activate
pip install -r requirements-host.txt

Load and run src/main.py on the V5 Brain. Connect the slide motor to Smart Port 1, then connect the Brain to the Mac with a data-capable USB cable. Keep the slide clear while it calibrates against both ends.

Run the tracker:
python computer/hand_tracker.py

The tracker uses /dev/cu.usbmodem103 by default. To use a different Brain User Port on macOS, set VEX_USER_PORT, for example:
VEX_USER_PORT=/dev/cu.usbmodem101 python computer/hand_tracker.py

Press Q in the camera window to quit.
