from picamera2 import Picamera2
from camera_preview import CameraPreview
import os
import parameters as params
import cv2
import time
from PyQt5.QtCore import QObject, pyqtSignal
import datetime


class CameraActions(QObject):
    def __init__(self, camera_preview, save_directory="images"):
        QObject.__init__(self)

        self.camera_preview = camera_preview
        self.camera = camera_preview.camera
        self.config = camera_preview.config
        self.save_directory = save_directory
        self.zPos = params.zPos

        # Initial zoom level (1.0 = no zoom)
        self.zoom_level = 1.0
        self.zoom_step = 0.05
        self.full_res = self.camera.camera_properties['PixelArraySize']
        self.current_size = list(self.full_res)

        self.preset_manager = None
        os.makedirs(self.save_directory, exist_ok=True)

    def set_preset_manager(self, preset_manager):
        """Set the preset manager after initialization to avoid circular dependency."""
        self.preset_manager = preset_manager

    def apply_settings(self, brightness=None, contrast=None):
        """Apply brightness and contrast settings to camera."""
        controls = {}
        if brightness is not None:
            controls["Brightness"] = brightness
            params.brightness = brightness
        if contrast is not None:
            controls["Contrast"] = contrast
            params.contrast = contrast

        if controls:
            self.camera.set_controls(controls)

        self.update_ui_parameters()

    def update_ui_parameters(self):
        """Update the UI to reflect current parameter values."""
        if self.preset_manager:
            self.preset_manager.update_parameter_list()

    def zoom_in(self):
        """Zoom in (increase magnification)."""
        self.zoom_level = min(self.zoom_level + self.zoom_step, 2.0)
        self.apply_zoom()

    def zoom_out(self):
        """Zoom out (decrease magnification)."""
        self.zoom_level = max(self.zoom_level - self.zoom_step, 1.0)
        self.apply_zoom()

    def apply_zoom(self):
        """Apply current zoom level to camera."""
        self.current_size = [int(s / self.zoom_level) for s in self.full_res]
        offset = [(r - s) // 2 for r, s in zip(self.full_res, self.current_size)]
        self.camera.set_controls({"ScalerCrop": offset + self.current_size})
        print(f"Applied zoom: {self.zoom_level:.2f}x, crop: {offset + self.current_size}")

    def update_metadata(self):
        """Capture and update camera metadata."""
        if self.camera.started:
            self.camera.capture_metadata()

    def capture_image(self, filename="image.jpg"):
        """
        Capture image using thread-safe frame capture.
        
        Parameters:
        -----------
        filename : str
            Filename for saved image
            
        Returns:
        --------
        str : Path to saved image, or None if failed
        """
        os.makedirs(self.save_directory, exist_ok=True)
        filepath = os.path.join(self.save_directory, filename)
        
        try:
            # Get frame from camera thread (non-blocking)
            frame = self.camera_preview.get_frame()
            
            if frame is None:
                print("✗ No frame available")
                return None
            
            # Convert XRGB8888 to BGR for saving
            if frame.shape[2] == 4:
                bgr = cv2.cvtColor(frame, cv2.COLOR_RGBA2BGR)
            else:
                bgr = frame
                
            cv2.imwrite(filepath, bgr)
            print(f"✓ Image saved to {filepath}")
            return filepath
            
        except Exception as e:
            print(f"✗ Failed to capture image: {e}")
            import traceback
            traceback.print_exc()
            return None

    def capture_image_frame(self):
        """
        Capture current frame as NumPy array for processing.
        
        Returns:
        --------
        numpy.ndarray : Current frame, or None if failed
        """
        try:
            frame = self.camera_preview.get_frame()
            if frame is None:
                print("Error: Unable to capture image array.")
                return None
            print("Captured image frame successfully.")
            return frame
        except Exception as e:
            print(f"Exception during frame capture: {e}")
            return None

    def set_brightness(self, brightness):
        """Set camera brightness."""
        self.camera.set_controls({"Brightness": brightness})
        params.brightness = brightness
        print(f"Brightness set to {brightness}")

    def set_contrast(self, contrast):
        """Set camera contrast."""
        self.camera.set_controls({"Contrast": contrast})
        params.contrast = contrast
        print(f"Contrast set to {contrast}")

    def set_exposure(self, exposure_time):
        """Set camera exposure time in microseconds."""
        self.camera.set_controls({"ExposureTime": exposure_time})
        params.exposure_time = exposure_time
        print(f"Exposure time set to {exposure_time} microseconds")

    # ─── Grid Imaging ─────────────────────────────────────────────────────────

    def calculate_grid_positions(self, well_center_x, well_center_y, well_diameter=6.4, grid_size=3):
        """
        Calculate XY positions for a grid of images within a well.
        
        Parameters:
        -----------
        well_center_x : float
            X coordinate of well center
        well_center_y : float
            Y coordinate of well center
        well_diameter : float
            Well diameter in mm (default 6.4mm for Greiner Bio-One)
        grid_size : int
            Grid dimension (3 for 3x3 = 9 images)
            
        Returns:
        --------
        list of tuples : [(x1, y1), (x2, y2), ...] for each grid position
        """
        # Use 80% of well diameter to avoid edges
        usable_diameter = well_diameter * 0.8
        step = usable_diameter / (grid_size - 1) if grid_size > 1 else 0
        
        positions = []
        
        # Generate grid centered on well
        for row in range(grid_size):
            for col in range(grid_size):
                x_offset = (col - (grid_size - 1) / 2) * step
                y_offset = (row - (grid_size - 1) / 2) * step
                
                x = well_center_x + x_offset
                y = well_center_y + y_offset
                
                positions.append((x, y))
        
        return positions

    def image_well_grid(self, movement_control, well_idx, grid_size=3):
        """
        Capture a grid of images for a single well.
        
        Parameters:
        -----------
        movement_control : MovementControl
            Movement control object
        well_idx : int
            Well index (0-95)
        grid_size : int
            Grid dimension (3 for 3x3 grid = 9 images)
            
        Returns:
        --------
        list : Paths to saved images
        """
        well_center_x = params.x_positions[well_idx]
        well_center_y = params.y_positions[well_idx]
        well_z = params.z_positions[well_idx]
        
        row = well_idx // 12
        col = well_idx % 12
        well_name = f"{chr(65 + row)}{col + 1}"
        
        print(f"\nImaging well {well_name} ({grid_size}x{grid_size} grid)...")
        
        # Calculate grid positions
        grid_positions = self.calculate_grid_positions(
            well_center_x, well_center_y,
            well_diameter=6.4,
            grid_size=grid_size
        )
        
        saved_images = []
        
        for idx, (x, y) in enumerate(grid_positions):
            grid_row = idx // grid_size
            grid_col = idx % grid_size
            
            print(f"  Position [{grid_row},{grid_col}]: X={x:.3f}, Y={y:.3f}, Z={well_z:.3f}")
            
            # Move to position
            movement_control.move_to(x, y, well_z)
            time.sleep(0.5)  # Wait for settling
            
            # Capture image with descriptive filename
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{well_name}_grid{grid_row}{grid_col}_{timestamp}.jpg"
            filepath = self.capture_image(filename)
            
            if filepath:
                saved_images.append(filepath)
        
        print(f"✓ Well {well_name} complete: {len(saved_images)} images captured")
        return saved_images