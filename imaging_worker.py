from PyQt5.QtCore import QThread, pyqtSignal
import parameters as params
import numpy as np
from scipy.ndimage import gaussian_filter
import cv2
import time

class ImagingWorker(QThread):
    finished = pyqtSignal()
    autofocus_done = pyqtSignal()

    def __init__(self, imaging_script):
        super().__init__()
        self.imaging_script = imaging_script
        self._is_running = False
        self._cancel_requested = False
        self._current_index = 0

    def run(self):
        self._is_running = True
        print("Worker thread running...")
        while self._is_running and not self._cancel_requested:
            self._current_index = 0
            self.process_next_position()
            pass
        
        if self._cancel_requested:
            print("Imaging script canceled.")
    
    def cancel(self):
        self._cancel_requested = True
        self._is_running = False
        print("Canceling imaging process...")
        
        # Stop all movements safely
        try:
            self.imaging_script.movement_control.stopMovement()
            print("Movement stopped.")
        except Exception as e:
            print(f"Error while stopping movement: {e}")
        
        
        self.quit()
        print("Quit signal sent.")
        
        # force stop
        if not self.wait(3000):
            print("Warning: Worker thread did not stop in time.")
            self.terminate()  # Force stop if thread hangs
            print("Worker thread terminated.")
        else:
            print("Worker fully stopped.")


    def process_next_position(self):
        if not self._is_running or self._current_index >= 96:
            self.finished.emit()
            return

        if self._cancel_requested or self._current_index >= 96:
            self.finished.emit()
            return

        # Move to the next position
        x_target = params.x_positions[self._current_index]
        y_target = params.y_positions[self._current_index]
        z_target = params.zPos

        print(f"Moving to position {self._current_index}: X={x_target}, Y={y_target}, Z={z_target}")
        self.imaging_script.move_to_position(x_target, y_target, z_target)
        time.sleep(2)

        # Start autofocus with an interrupt check
        self.autofocus()

    # def autofocus(self, standalone=False, cancel_check=None):
    #     print("[Autofocus] Starting hybrid autofocus...")

    #     if self.is_canceled():
    #         return

    #     # Parameters for the autofocus process
    #     initial_range = 0.7  # Broad sweep range
    #     step_size = 0.05     # Broad sweep step size
    #     validation_range = 0.1  # Narrow range for peak validation
    #     grid_step = 0.01      # Narrow grid search step size

    #     low_z, high_z = params.zPos - initial_range, params.zPos + initial_range

    #     # Step 1: Perform a broad sweep
    #     z_positions = [low_z + i * step_size for i in range(int((high_z - low_z) / step_size) + 1)]
    #     sharpness_values = list([self.measure_sharpness_at(z) for z in z_positions])
    #     print(f'ARRAY OF SHARPNESS VALUES {sharpness_values}')
    #     print(type(sharpness_values))

    #     # Smooth sharpness values
    #     sharpness_values = self.smooth_sharpness(sharpness_values)

    #     # Filter out invalid sharpness measurements
    #     filtered_values = [(z, s) for z, s in zip(z_positions, sharpness_values) if s is not None]
    #     if not filtered_values:
    #         print("[Autofocus] No valid sharpness measurements. Aborting.")
    #         return

    #     # Find the Z position with the highest sharpness
    #     peak_z = max(filtered_values, key=lambda x: x[1])[0]
    #     print(f"[Broad Sweep] Peak Z = {peak_z:.2f}")

    #     # Step 2: Validate the peak
    #     print("[Autofocus] Validating peak sharpness...")
    #     validated_peak_z = self.refine_peak(peak_z, validation_range)
    #     print(f"[Validation] Refined peak Z = {validated_peak_z:.2f}")

    #     # Step 3: Narrow Grid Search
    #     print("[Autofocus] Performing narrow grid search...")
    #     search_low = max(low_z, validated_peak_z - grid_step * 10)
    #     search_high = min(high_z, validated_peak_z + grid_step * 10)

    #     best_z = self.narrow_grid_search(search_low, search_high, grid_step)
    #     print(f"[Autofocus] Best Z = {best_z:.2f}")

    #     # Move to the best Z position
    #     self.imaging_script.movement_control.moveZTo(best_z)
    #     params.zPos = best_z

    #     if standalone:
    #         print("[Autofocus] Complete in standalone mode.")
    #     else:
    #         self.proceed_to_next_step()

    def autofocus(self):
        """
        Perform autofocus by analyzing sharpness across a Z-stack with median filtering and ROI.
        """
        # Parameters
        initial_range = 0.4
        z_step = 0.03
        capture_delay = 2

        z_start, z_end = params.zPos - initial_range, params.zPos + initial_range

        z_positions = []
        sharpness_values = []

        z_pos = z_start
        while z_pos <= z_end:
            # Move to the current Z position
            self.imaging_script.movement_control.moveZTo(z_pos)

            # Delay to stabilize before capturing
            time.sleep(capture_delay)

            # Capture image and process it
            frame = self.imaging_script.camera_actions.capture_image_frame()  # Returns the current frame
            if frame is None:
                print(f"Failed to capture image at Z = {z_pos}")
                break

            # Convert image to grayscale
            gray_frame = frame # cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

            # Apply Gaussian filter
            smoothed = gaussian_filter(gray_frame, sigma=1)

            # Apply Laplacian filter
            laplacian = cv2.Laplacian(smoothed, cv2.CV_64F)

            # Compute sharpness with Laplacian variance in ROI
            sharpness = np.var(laplacian)

            # Record Z position and sharpness value
            z_positions.append(z_pos)
            sharpness_values.append(sharpness)

            print(f"[Sharpness] Z = {z_pos:.2f}, Sharpness = {sharpness:.2f}")
            
            # Increment Z position
            z_pos += z_step

        # Find the Z position with the maximum sharpness
        max_sharpness_index = np.argmax(sharpness_values)
        optimal_z = z_positions[max_sharpness_index]

        print(f"Optimal focus found at Z = {optimal_z:.2f} with Sharpness = {sharpness_values[max_sharpness_index]:.2f}")
        time.sleep(1)
        # Move to the best Z position
        self.imaging_script.movement_control.moveZTo(optimal_z)
        params.zPos = optimal_z

        time.sleep(2)
        self.proceed_to_next_step()


    # Supporting Methods
    def is_canceled(self):
        """Check if the autofocus process has been canceled."""
        if not self._is_running or self._cancel_requested:
            print("Autofocus interrupted. Exiting.")
            return True
        return False

    def broad_sweep(self, low_z, high_z, step_size):
        """Perform a broad sweep to identify the approximate focus peak."""
        z_positions = [low_z + i * step_size for i in range(int((high_z - low_z) / step_size) + 1)]
        sharpness_values = [self.measure_sharpness_at(z) for z in z_positions]
        return z_positions, sharpness_values

    def refine_peak(self, peak_z, range_width):
        """Validate and refine the peak Z position within a narrow range."""
        validation_positions = np.linspace(peak_z - range_width, peak_z + range_width, 5)
        validation_sharpness = [self.measure_sharpness_at(z) for z in validation_positions]

        # Find the position with the maximum sharpness
        refined_idx = validation_sharpness.index(max(validation_sharpness))
        return validation_positions[refined_idx]
    
    def smooth_sharpness(self, values, window_size=3):
        """
        Apply a simple moving average to smooth sharpness values.
        """
        try:
            values = list(values)
        except TypeError:
            raise ValueError("Input to smooth_sharpness must be an iterable.")
        smoothed = []
        for i in range(len(values)):
            start = max(0, i - window_size // 2)
            end = min(len(values), i + window_size // 2 + 1)
            smoothed.append(sum(values[start:end]) / (end - start))
        return smoothed


    # Supporting Methods
    def narrow_grid_search(self, low_z, high_z, step_size):
        """Perform a narrow grid search to fine-tune the focus."""
        z_positions = [low_z + i * step_size for i in range(int((high_z - low_z) / step_size) + 1)]
        sharpness_values = [self.measure_sharpness_at(z) for z in z_positions]

        # Filter out invalid sharpness measurements
        filtered_values = [(z, s) for z, s in zip(z_positions, sharpness_values) if s is not None]
        if not filtered_values:
            print("[Grid Search] No valid sharpness measurements. Aborting.")
            return None

        best_position = max(filtered_values, key=lambda x: x[1])[0]
        print(f"[Grid Search] Best position: Z = {best_position:.2f}")
        return best_position

    def measure_sharpness_at(self, z_position):
        """Move to a Z position, capture an image, and measure its sharpness."""
        if self.is_canceled():
            return None

        self.imaging_script.movement_control.moveZTo(z_position)
        time.sleep(3)  # Wait for movement to stabilize

        # Take multiple sharpness measurements to reduce noise
        sharpness_values = []
        for _ in range(3):
            frame = self.imaging_script.camera_actions.capture_image_frame()
            if frame is None:
                print(f"Error capturing frame at Z: {z_position:.2f}.")
                sharpness_values.append(float('-inf'))
            else:
                sharpness_values.append(self.measure_sharpness(frame))

        sharpness = np.median(sharpness_values)  # Use median to reduce noise
        print(f"[Sharpness] Z = {z_position:.2f}, Sharpness = {sharpness:.2f} (Median of {sharpness_values})")
        return sharpness

    def measure_sharpness(self, frame):
        """Calculate the sharpness of an image frame."""
        gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        sharpness = cv2.Laplacian(gray_frame, cv2.CV_64F).var()
        return sharpness
    
    def proceed_to_next_step(self):
        if not self._is_running:
            self.finished.emit()
            return
        if self._cancel_requested:
            return

        self.imaging_script.capture_image(self._current_index)
        self._current_index += 1
        self.msleep(1000)  # delay for stabilization

        # Move to the next position
        self.process_next_position()