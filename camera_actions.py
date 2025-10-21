from picamera2 import Picamera2
from picamera2.previews.qt import QGlPicamera2
from camera_preview import CameraPreview
import os
import parameters as params
import cv2
import time
from presets import PresetManager
from PyQt5.QtCore import QObject, pyqtSignal

class CameraActions(CameraPreview, QObject):  # Inherit from CameraPreview and QObject
    autofocus_done = pyqtSignal()

    def __init__(self, camera_preview, save_directory="images"):
        QObject.__init__(self)

        self.camera = camera_preview.camera
        self.qpicamera2 = camera_preview.qpicamera2
        self.config = camera_preview.config
        self.save_directory = save_directory
        self.zPos = params.zPos

        # Initial zoom level (1.0 = no zoom)
        self.zoom_level = 1.0
        self.zoom_step = 0.05
        self.full_res = self.camera.camera_properties['PixelArraySize']
        self.current_size = list(self.full_res)

        # self.update_metadata()

        self.preset_manager = None
        os.makedirs(self.save_directory, exist_ok=True)

    def set_preset_manager(self, preset_manager):
        """
        Method to set the preset manager after initialization to avoid circular dependency.
        """
        self.preset_manager = preset_manager

    def apply_settings(self, brightness=None, contrast=None):
        controls = {}
        if brightness is not None:
            controls["Brightness"] = brightness
            params.brightness = brightness
        if contrast is not None:
            controls["Contrast"] = contrast
            params.contrast = contrast

        if controls:
            self.camera.set_controls(controls)  # Call set_controls from CameraPreview

        # Update the parameters in the UI
        self.update_ui_parameters()

    def update_ui_parameters(self):
        """
        Update the UI to reflect the current parameter values for brightness, contrast, etc.
        This method should update any related UI components or display elements.
        """
        if self.preset_manager:
            self.preset_manager.update_parameter_list()

    def zoom_in(self):
        self.zoom_level = min(self.zoom_level + self.zoom_step, 2.0)
        self.apply_zoom()

    def zoom_out(self):
        self.zoom_level = max(self.zoom_level - self.zoom_step, 1.0)
        self.apply_zoom()

    def apply_zoom(self):
        # Calculate the new ScalerCrop size based on the zoom factor
        self.current_size = [int(s / self.zoom_level) for s in self.full_res]
        offset = [(r - s) // 2 for r, s in zip(self.full_res, self.current_size)]

        # Apply the new ScalerCrop settings
        self.camera.set_controls({"ScalerCrop": offset + self.current_size})
        print(f"Applied ScalerCrop with offset: {offset}, size: {self.current_size}")

    def update_metadata(self):
        if self.camera.started:
            self.camera.capture_metadata()

    def capture_image(self, filename="image.jpg"):
        filepath = os.path.join(self.save_directory, filename)
        cfg = self.camera.create_still_configuration()
        self.camera.switch_mode_and_capture_file(cfg, filepath, signal_function=self.qpicamera2.signal_done)
        print(f"Image saved to {filepath}")

    def capture_image_frame(self):
        """
        Captures the current frame as a NumPy array for processing (e.g., autofocus).
        Uses the Picamera2 instance from QGlPicamera2.
        """
        try:
            # Access the Picamera2 instance from QGlPicamera2
            picamera2_instance = self.qpicamera2.picamera2
            frame = picamera2_instance.capture_array()
            grey = frame[:560, :700]

            if frame is None or frame.size == 0:
                print("Error: Unable to capture image array.")
                return None

            print("Captured image frame successfully.")
            return grey

        except Exception as e:
            print(f"Exception during frame capture: {e}")
            return None


    def set_brightness(self, brightness):
        self.camera.set_controls({"Brightness": brightness})
        params.brightness = brightness  # Update global parameter
        print(f"Brightness set to {brightness}")

    def set_contrast(self, contrast):
        self.camera.set_controls({"Contrast": contrast})
        params.contrast = contrast  # Update global parameter
        print(f"Contrast set to {contrast}")

    def set_exposure(self, exposure_time):
        self.camera.set_controls({"ExposureTime": exposure_time})
        params.exposure_time = exposure_time  # Update global parameter
        print(f"Exposure time set to {exposure_time} microseconds")