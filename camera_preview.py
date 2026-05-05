from PyQt5.QtCore import QThread, pyqtSignal, QMutex, QMutexLocker
from PyQt5.QtWidgets import QLabel
from PyQt5.QtGui import QImage, QPixmap
from picamera2 import Picamera2
import libcamera
import numpy as np
import time


class CameraThread(QThread):
    """Separate thread for camera operations to avoid blocking GUI"""
    frame_ready = pyqtSignal(np.ndarray)
    
    def __init__(self, camera):
        super().__init__()
        self.camera = camera
        self.running = True
        self.capture_requested = False
        self.capture_mutex = QMutex()
        self.latest_frame = None
        
    def run(self):
        """Continuously capture frames in background thread"""
        while self.running:
            try:
                if not self.camera.started:
                    print("Camera not started, waiting...")
                    time.sleep(0.5)
                    continue
                
                # Non-blocking frame capture
                array = self.camera.capture_array("main")

                with QMutexLocker(self.capture_mutex):
                    self.latest_frame = array.copy()

                # Emit signal for preview update
                self.frame_ready.emit(array)

                time.sleep(0.033)  # ~30 fps

            except RuntimeError as e:
                # Camera might be temporarily unavailable
                print(f"Camera temporarily unavailable: {e}")
                time.sleep(0.2)
            except Exception as e:
                print(f"Camera thread error: {e}")
                time.sleep(0.1)
        
    def get_latest_frame(self):
        """Thread-safe way to get the latest frame"""
        with QMutexLocker(self.capture_mutex):
            if self.latest_frame is not None:
                return self.latest_frame.copy()
            return None
    
    def stop(self):
        """Stop the camera thread"""
        self.running = False
        self.wait()


class CameraPreview(QLabel):
    """Camera preview widget using QLabel for simplicity and thread safety"""
    
    def __init__(self, camera_widget):
        super().__init__(camera_widget)
        
        # Initialize Picamera2
        self.camera = Picamera2()
        
        # Configure the camera
        self.config = self.camera.create_preview_configuration(
            main={"size": self.camera.sensor_resolution, "format": "XRGB8888"},
            transform=libcamera.Transform(vflip=True),
            buffer_count=4
        )
        self.config["controls"] = {
            "FrameRate": 30,
        }
        self.camera.configure(self.config)
        
        # Set widget size
        self.setFixedSize(700, 560)
        self.setScaledContents(True)
        
        # Start camera
        self.camera.start()
        time.sleep(0.5)  # Let camera warm up
        
        # Start camera thread
        self.camera_thread = CameraThread(self.camera)
        self.camera_thread.frame_ready.connect(self.update_preview)
        self.camera_thread.start()
        
        print("Camera preview initialized in separate thread")
    
    def update_preview(self, frame):
        """Update the preview display with new frame"""
        try:
            # Convert numpy array to QImage
            height, width = frame.shape[:2]
            
            # XRGB8888 format
            if frame.shape[2] == 4:
                qimage = QImage(frame.data, width, height, 
                               frame.strides[0], QImage.Format_RGB32)
            else:
                qimage = QImage(frame.data, width, height, 
                               frame.strides[0], QImage.Format_RGB888)
            
            # Convert to pixmap and display
            pixmap = QPixmap.fromImage(qimage)
            self.setPixmap(pixmap)
            
        except Exception as e:
            print(f"Preview update error: {e}")
    
    def get_frame(self):
        """Get the latest frame without blocking"""
        return self.camera_thread.get_latest_frame()
    
    def close(self):
        """Cleanup camera resources"""
        print("Closing camera preview...")
        self.camera_thread.stop()
        if self.camera.started:
            self.camera.stop()
        print("Camera closed")