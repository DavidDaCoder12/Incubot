import serial
import time
import parameters as params

# XYZ Movement Functions
class MovementControl:
    def __init__(self, port='/dev/ttyACM0', baudrate=115200):
        # Initialize serial connection
        self.ser = serial.Serial(port, baudrate, timeout=1)
        self.ser.dtr = False
        self.ser.rts = False
        time.sleep(0.5)
        self.ser.dtr = True
        self.ser.rts = True
        time.sleep(3)

        # Flush input to clear any startup message
        self.ser.flushInput()
        print("Connected to CNC")

        self.ser.write(b'\x18')  # Soft reset
        self.ser.write(b'$X\n')
        self.ser.write(b'$H\n')
        self.ser.write(b'G92X3.2Y3.2Z0\n')
        self.ser.write(b'G90G1X3.2Y3.2Z-0.7F1000\n')
        print(f"X: {params.xPos} Y: {params.yPos} Z: {params.zPos}")
        time.sleep(1)


        # Base Strings
        self.xBase = "G90G1X"
        self.yBase = "G90G1Y"
        self.zBase = "G90G1Z"
        self.commTerm = "F1000\n"
        

    
    # Move to specific x, y, z coordinates
    def move_to(self, x, y, z):
        # Update the global positions
        params.xPos = x
        params.yPos = y
        params.zPos = z

        print(f"Moving to X: {params.xPos}, Y: {params.yPos}, Z: {params.zPos}")

        command = f"G90G1 X{params.xPos} Y{params.yPos} Z{params.zPos} F2000\n"

        # Send the command to move to the specified (x, y, z) position
        self.ser.write(command.encode('utf-8'))

        time.sleep(3)

    def move_to_well(self, well_index):
        """
        Moves the machine to the (x, y, z) coordinates for the specified well index.
        """
        if well_index < 0 or well_index >= 96:
            print("Invalid well index. Must be between 0 and 95.")
            return

        # Retrieve coordinates from parameters
        x_target = params.x_positions[well_index]
        y_target = params.y_positions[well_index]
        z_target = params.z_positions[well_index]


        # Update global positions
        params.xPos = x_target
        params.yPos = y_target
        params.zPos = z_target

        print(f"{params.xPos}, {params.yPos}, {params.zPos}")


        print(f"Moving to Well {well_index + 1}: X={x_target}, Y={y_target}, Z={z_target}")

        # G-code command to move the CNC machine
        # self.ser.write(b'G90G1X10Y20F1000\n')
        command = b'G90G1X' + str(x_target).encode('utf-8') + b'Y' + str(y_target).encode('utf-8') + b'Z' + str(z_target).encode('utf-8') + b'F1000\n'
        self.ser.write(command)

        time.sleep(3)  # Wait for movement to complete

    
    def moveZTo(self, z):
        """Move to a specific Z position."""
        params.zPos = z  # Update the global zPos
        zString = self.zBase + str(params.zPos) + self.commTerm
        self.ser.write(zString.encode('utf-8'))
        print(f"Moving Z to: {params.zPos}")


    def XNegFine(self):
        params.xPos += 0.2
        jog_command = "$J=G91 X-0.2 F1000\n"
        self.ser.write(jog_command.encode('utf-8'))
        print(params.xPos)


    def YNegFine(self):
        params.yPos -= 0.2
        jog_command = "$J=G91 Y-0.2 F1000\n"
        self.ser.write(jog_command.encode('utf-8'))
        print(params.yPos)


    def ZNegFine(self):
        params.zPos -= 0.2
        jog_command = "$J=G91 Z-0.2 F1000\n"

        self.ser.write(jog_command.encode('utf-8'))
        print(params.zPos)


    def XPosFine(self):
        params.xPos += 0.2
        jog_command = "$J=G91 X+0.2 F1000\n"
        self.ser.write(jog_command.encode('utf-8'))
        print(params.xPos)

    def YPosFine(self):
        params.yPos += 0.2
        jog_command = "$J=G91 Y+0.2 F1000\n"
        self.ser.write(jog_command.encode('utf-8'))
        print(params.yPos)

    def ZPosFine(self):
        params.zPos += 0.01
        jog_command = "$J=G91 Z+0.01 F1000\n"
        self.ser.write(jog_command.encode('utf-8'))
        print(params.zPos)

    def ZPosRough(self):
        params.zPos += 0.1
        jog_command = "$J=G91 Z+0.1 F1000\n"
        self.ser.write(jog_command.encode('utf-8'))
        print(params.zPos)


    def ZNegFine(self):
        params.zPos -= 0.01
        jog_command = "$J=G91 Z-0.01 F1000\n"
        self.ser.write(jog_command.encode('utf-8'))
        print(params.zPos)
        
    def ZNegRough(self):
        params.zPos -= 0.1
        jog_command = "$J=G91 Z-0.1 F1000\n"
        self.ser.write(jog_command.encode('utf-8'))
        print(params.zPos)


    def stopMovement(self):
        stop = "M0" + self.commTerm
        self.ser.write(stop.encode('utf-8'))

    def retrieve_coord(self, i):
        return params.x_positions[i], params.y_positions[i], params.z_positions[i]

    def goHome(self):
        self.ser.write(b'\x18')
        self.ser.write(b'$X\n')
        homePosition = "$H\n" + self.commTerm
        time.sleep(0.5)
        self.ser.write(homePosition.encode('utf-8'))
        self.ser.write(b'G92X3.2Y3.2Z0\n')
        print(f"X: {params.xPos} Y: {params.yPos} Z: {params.zPos}")

    def close(self):
        self.ser.close()  # Close the serial connection

