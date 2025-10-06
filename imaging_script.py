import parameters as params  # Import parameters dynamically
import serial
import time

class ImagingScript:
    def __init__(self, movement_control, camera_actions):
        """
        Initializes the imaging process with required components.

        :param movement_control: Object for controlling the CNC movement (e.g., MovementControl class).
        :param camera_actions: Object for handling the camera operations (e.g., CameraActions class).
        """
        self.movement_control = movement_control
        self.camera_actions = camera_actions

    def send_gcode(self, command):
        """Send G-code command to the CNC machine."""
        command = command.strip() + '\n'  # G-code commands need to end with newline
        self.ser.write(command.encode())  # Send command via serial
        response = self.ser.readline().decode('utf-8').strip()  # Wait for response
        return response

    def move_to_position(self, x, y, z):
        """
        Move the machine head to the given (x, y, z) position.

        :param x: Target x-coordinate.
        :param y: Target y-coordinate.
        :param z: Target z-coordinate.
        """
        self.movement_control.move_to(x, y, z)
        time.sleep(3)

    def capture_image(self, position_index):
        """
        Capture an image at the current machine position.

        :param position_index: Index of the current position for naming the image file.
        """
        # Generate the filename for the image (optional: include position details in the filename)
        filename = f"{params.save_directory}/image_position_{position_index + 1}.jpg"
        self.camera_actions.capture_image(filename)
        params.image_counter += 1  # Update the image counter in parameters

    def run_imaging_sequence(self):
        """
        Run the imaging sequence by iterating over all predefined positions.
        Moves to each position, captures an image, and then moves to the next.
        """
        for i, (location_name, coordinates) in enumerate(self.locations.items()):
            x, y, z = coordinates
            print(f"Moving to {location_name} at position ({x}, {y}, {z})")

            # Move to the current position
            self.move_to_position(x, y, z)

            # # Capture the image at the current position
            # self.capture_image(i)

    def stop(self):
        """
        Stop the imaging sequence if interrupted or manually stopped.
        """
        print("Imaging process stopped.")
