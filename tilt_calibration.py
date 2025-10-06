import PIL
import math
import numpy as np
import parameters as params
from movement_control import MovementControl

class TiltCalibration:

    def __init__(self):
        self.z_positions = params.z_positions
        self.x_positions = params.x_positions
        self.y_positions = params.y_positions
        self.movement_control = MovementControl()
        pass

    # Initial Z measurement
    # Final Z measurment
    # Divide difference by num wells

    def calibrate_z(self, x_arr, y_arr, z_arr, plate_size=(8, 12)):
        # Unpack the known corner positions
        x1, x2 = x_arr[0], x_arr[1]  # top-left, top-right
        y1, y2 = y_arr[0], y_arr[2]  # top-left, bottom-left

        z1 = z_arr[0]  # top-left
        z2 = z_arr[1]  # top-right
        z3 = z_arr[2]  # bottom-left
        z4 = z_arr[3]  # bottom-right

        # Compute gradients (a and b) and offset (c)
        a = ((z2 - z1) + (z4 - z3)) / (2 * (x2 - x1))  # dz/dx
        b = ((z3 - z1) + (z4 - z2)) / (2 * (y2 - y1))  # dz/dy
        c = z1  # base offset at top-left

        # Generate full plate x and y coordinate grid
        x_vals = np.array(params.x_positions).reshape(plate_size)
        y_vals = np.array(params.y_positions).reshape(plate_size)

        # Apply plane equation to generate z values
        z_corrected = a * x_vals + b * y_vals + c

        return z_corrected.flatten()



    def measure_coords(self):
        return params.z_pos, params.x_pos, params.y_pos

    # def calibration_main(self):
    #     rows, cols = 8, 12 # 96 well dimensions
    #     corners = [0, cols - 1, (rows-1) * cols, rows * cols - 1]

    #     x_pos = []
    #     y_pos = []
    #     z_pos = []

    #     for i in range(corners):
    #         self.movement_control.move_to_well(i)

    #         x_pos += params.x_positions
    #         y_pos += params.y_positions

    #         # Prompt user to measure z value with most focus
    #         # Wait for user to confirm z axis value
    #         # Need front end interaction
    #         z_pos += params.z_positions

    #         # Calibrate z accodingly
        
    #     self.calibrate_z(x_pos, y_pos, z_pos)
        


    

    