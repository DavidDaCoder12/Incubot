# from PyQt5.QtGui import QImage
# from PyQt5.QtCore import QTimer
# from picamera2.previews.qt import QGlPicamera2
# from picamera2 import Picamera2

# class CameraPreview(QGlPicamera2):
#     def __init__(self, parent=None):
#         # Initialize Picamera2
#         self.camera = Picamera2()
        
#         # Initialize QGlPicamera2 with Picamera2 instance and parent widget
#         super().__init__(self.camera, parent)

#         # Set a fixed size for the OpenGL widget
#         self.setFixedSize(700, 560)  # Adjust these dimensions as needed

#         # Configure the camera for full frame, adjusting the ROI to ensure no cropping
#         config = self.camera.create_preview_configuration(main={"size": self.camera.sensor_resolution})
#         config["controls"] = {"FrameRate": 10}
#         self.camera.configure(config)
#         self.camera.start()

#         # Timer for refreshing the frame
#         self.timer = QTimer(self)
#         self.timer.timeout.connect(self.update)
#         self.timer.start(100)  # Refresh rate in milliseconds (adjust if needed)

#     def close(self):
#         # Cleanup camera resources
#         self.camera.stop()
#         self.timer.stop()

import threading
import time
from PyQt5.QtCore import QTimer
from picamera2.previews.qt import QGlPicamera2
from picamera2 import Picamera2
import libcamera

class CameraPreview(QGlPicamera2):
    def __init__(self, camera_widget):
        # Initialize Picamera2
        self.camera = Picamera2()
        self.camera_widget = camera_widget
        
        # Initialize QGlPicamera2 with Picamera2 instance and parent widget
        super().__init__(self.camera, self.camera_widget)

        # Set a fixed size for the OpenGL widget
        self.setFixedSize(700, 560)

        # Configure the camera with reduced resolution for preview to save resources
        self.config = self.camera.create_preview_configuration(main={"size": self.camera.sensor_resolution, "format": "YUV420"}, transform=libcamera.Transform(vflip=True))
        self.config["controls"] = {"FrameRate": 15, "ScalerCrop": (0, 0, self.camera.sensor_resolution[0], self.camera.sensor_resolution[1])}
        # self.config["controls"]["Saturation"] = 0.0
        self.camera.configure(self.config)

        self.qpicamera2 = QGlPicamera2(self.camera, width=640, height=480, keep_ar=True)

        # Connect the camera's done_signal to the capture_done callback
        self.qpicamera2.done_signal.connect(self.capture_done)

        # Start the camera in the background
        self.camera.start(show_preview=True)

        # Timer for updating preview display at a reduced rate
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update)
        self.timer.start(200)  # Lower refresh rate, e.g., 200 ms

    def capture_done(self, job):
        # Handle capture completion
        result = self.camera.wait(job)
        print("Capture completed:", result)

    def close(self, event):
        # Cleanup camera resources
        self.camera.stop()
        self.timer.stop()
        event.accept()
