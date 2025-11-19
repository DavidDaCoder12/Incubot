import numpy as np
import parameters as params


class TiltCalibration:
    """
    Handles tilt calibration for the 96-well plate by measuring Z positions
    at corner wells and computing a plane fit.
    """

    def __init__(self):
        self.corner_indices = [0, 11, 84, 95]  # A1, A12, H1, H12
        self.calibrated = False
        
    def get_corner_indices(self):
        """Returns the well indices for the four corners of the 96-well plate."""
        return self.corner_indices

    @staticmethod
    def calibrate_z(x_arr, y_arr, z_arr, plate_size=(8, 12)):
        """
        Calibrate Z positions across the entire plate based on 4 corner measurements.
        
        Uses bilinear interpolation to fit a plane through the corner points.
        
        Parameters:
        -----------
        x_arr : list of 4 floats
            X coordinates of corners [top-left, top-right, bottom-left, bottom-right]
        y_arr : list of 4 floats
            Y coordinates of corners [top-left, top-right, bottom-left, bottom-right]
        z_arr : list of 4 floats
            Measured Z positions at corners [top-left, top-right, bottom-left, bottom-right]
        plate_size : tuple
            (rows, cols) dimensions of the well plate
            
        Returns:
        --------
        np.ndarray : Flattened array of 96 corrected Z positions
        """
        
        # Validate inputs
        if len(x_arr) != 4 or len(y_arr) != 4 or len(z_arr) != 4:
            raise ValueError("Must provide exactly 4 corner positions")
        
        if any(z is None for z in z_arr):
            raise ValueError("All Z positions must be measured (no None values)")
        
        # Unpack corner positions
        # Assuming order: [top-left, top-right, bottom-left, bottom-right]
        x1, x2, x3, x4 = x_arr  # TL, TR, BL, BR
        y1, y2, y3, y4 = y_arr  # TL, TR, BL, BR
        z1, z2, z3, z4 = z_arr  # TL, TR, BL, BR
        
        # Fit plane: z = a*x + b*y + c
        # Using least squares to find best-fit plane through 4 points
        
        # Create design matrix for plane fitting
        A = np.array([
            [x1, y1, 1],
            [x2, y2, 1],
            [x3, y3, 1],
            [x4, y4, 1]
        ])
        
        z_vector = np.array([z1, z2, z3, z4])
        
        # Solve for plane coefficients using least squares
        # This is more robust than manual gradient calculation
        coeffs, residuals, rank, s = np.linalg.lstsq(A, z_vector, rcond=None)
        a, b, c = coeffs
        
        print(f"Plane fit coefficients: a={a:.6f}, b={b:.6f}, c={c:.6f}")
        print(f"Residuals: {residuals}")
        
        # Apply plane equation to all 96 well positions
        x_vals = np.array(params.x_positions)
        y_vals = np.array(params.y_positions)
        
        z_corrected = a * x_vals + b * y_vals + c
        
        # Calculate tilt angles for user information
        tilt_x = np.arctan(a) * 180 / np.pi  # degrees
        tilt_y = np.arctan(b) * 180 / np.pi  # degrees
        
        print(f"Estimated tilt: X={tilt_x:.3f}°, Y={tilt_y:.3f}°")
        
        # Calculate Z range across plate
        z_min, z_max = z_corrected.min(), z_corrected.max()
        z_range = z_max - z_min
        print(f"Z range across plate: {z_range:.3f} mm (from {z_min:.3f} to {z_max:.3f})")
        
        return z_corrected

    @staticmethod
    def apply_calibration(z_corrected):
        """
        Apply the calibrated Z positions to the global parameters.
        
        Parameters:
        -----------
        z_corrected : np.ndarray or list
            Array of 96 calibrated Z positions
        """
        if len(z_corrected) != 96:
            raise ValueError(f"Expected 96 Z positions, got {len(z_corrected)}")
        
        params.z_positions = list(z_corrected)
        print("✓ Calibrated Z positions applied to params.z_positions")
        
    @staticmethod
    def save_calibration(filename="z_calibration.npy"):
        """
        Save the current calibrated Z positions to a file.
        
        Parameters:
        -----------
        filename : str
            Path to save the calibration data
        """
        try:
            np.save(filename, np.array(params.z_positions))
            print(f"✓ Calibration saved to {filename}")
        except Exception as e:
            print(f"✗ Failed to save calibration: {e}")
    
    @staticmethod
    def load_calibration(filename="z_calibration.npy"):
        """
        Load previously saved Z calibration from file.
        
        Parameters:
        -----------
        filename : str
            Path to load the calibration data from
            
        Returns:
        --------
        bool : True if successful, False otherwise
        """
        try:
            z_loaded = np.load(filename)
            if len(z_loaded) == 96:
                params.z_positions = list(z_loaded)
                print(f"✓ Calibration loaded from {filename}")
                return True
            else:
                print(f"✗ Invalid calibration file (expected 96 values, got {len(z_loaded)})")
                return False
        except FileNotFoundError:
            print(f"✗ Calibration file not found: {filename}")
            return False
        except Exception as e:
            print(f"✗ Failed to load calibration: {e}")
            return False

    @staticmethod
    def validate_corner_measurements(z_arr, max_tilt_mm=10.0):
        """
        Validate that corner Z measurements are reasonable.
        
        Parameters:
        -----------
        z_arr : list of 4 floats
            Measured Z positions at corners
        max_tilt_mm : float
            Maximum expected tilt range in mm (default: 10.0)
            
        Returns:
        --------
        tuple : (is_valid, message)
        """
        if any(z is None for z in z_arr):
            return False, "Not all corners have been measured"
        
        z_range = max(z_arr) - min(z_arr)
        
        if z_range > max_tilt_mm:
            return False, f"Tilt range ({z_range:.2f} mm) exceeds maximum ({max_tilt_mm} mm). Check measurements."
        
        if z_range < 0.01:
            return False, "Tilt range too small. Plate may already be level or measurements are identical."
        
        return True, f"Measurements valid (range: {z_range:.3f} mm)"